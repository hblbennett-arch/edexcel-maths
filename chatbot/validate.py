"""Check a tutor reply against the knowledge base before a student sees it.

- Examiner insights: drop any note_id that isn't in the database (or isn't among the notes
  the model was given), and attach the verbatim quote from the database, so a quote can
  never be invented or altered.
- Mark labels: every mark code a step uses (M1, dM1, A1*, B1ft ...) must appear in that
  part's official mark scheme, and the marks across a part's steps should add up to the
  part's marks.
- Final answers: evaluate `final_answer_sympy` and check it matches a number in the part's
  mark scheme (to the precision the mark scheme gives).
- Structure: every part of the question is present.
Problems are returned as warnings; the caller decides whether to retry or flag "unverified".
"""
import re

import sympy

from . import db

MARK_CODE_RE = re.compile(r"\b(dd?M\d|M\d|A\d\*?|B\d\*?)(?:ft|cso|cao)?\b")


def _codes(text: str) -> list[str]:
    return [m.group(1) for m in MARK_CODE_RE.finditer(text)]


def _value(code: str) -> int:
    return int(re.search(r"\d", code).group())


def _numbers(text: str) -> list[float]:
    """Every value the mark scheme states: plain numbers, plus each side of the equations in
    its $...$ spans evaluated exactly (so \\frac{32}{15}(2+\\sqrt{2}) counts as 7.2836...)."""
    text = MARK_CODE_RE.sub(" ", text)
    text = re.sub(r"\((?:[a-h]|i{1,3}|iv|v)\)|\(\d+ marks?\)", " ", text)  # part labels, mark totals
    values = [float(n) for n in re.findall(r"(?<![A-Za-z_\d.^{])-?\d+(?:\.\d+)?(?![\d]*[A-Za-z(])", text)]
    for span in re.findall(r"\$([^$]+)\$", text):
        for side in re.split(r"=|\\approx|\\Rightarrow|<|>|\\leqslant|\\geqslant|,", span):
            v = _latex_value(side)
            if v is not None:
                values.append(v)
    return values


def _latex_value(tex: str) -> float | None:
    tex = tex.strip()
    if not tex or not re.search(r"\d", tex):
        return None
    try:
        from sympy.parsing.latex import parse_latex
        expr = parse_latex(tex).subs({sympy.Symbol("pi"): sympy.pi, sympy.Symbol("e"): sympy.E})
        if expr.free_symbols:
            return None
        v = complex(sympy.N(expr))
        return v.real if abs(v.imag) < 1e-12 else None
    except Exception:  # unparseable LaTeX fragments are simply skipped
        return None


def _matches(value: float, candidates: list[float]) -> bool:
    for c in candidates:
        if c == 0:
            if abs(value) < 1e-9:
                return True
            continue
        decimals = len(str(c).split(".")[1]) if "." in str(c) else 0
        tol = max(0.5 * 10 ** -decimals, abs(c) * 1e-6)
        if abs(value - c) <= tol + 1e-9:
            return True
    return False


def check_final_answer(expr: str, mark_scheme: str) -> str | None:
    """None if ok or not checkable; otherwise a warning."""
    if not expr.strip():
        return None
    try:
        value = sympy.sympify(expr, rational=True)
    except (sympy.SympifyError, TypeError, ValueError, SyntaxError):
        return f"final_answer_sympy '{expr}' did not parse"
    if value.free_symbols:
        return None  # a formula (e.g. a "show that" result), not a number: nothing to compare numerically
    try:
        numeric = complex(sympy.N(value))
    except (TypeError, ValueError):
        return None
    if abs(numeric.imag) > 1e-9:
        return None  # not a single real value; can't compare
    candidates = _numbers(mark_scheme)
    if not candidates:
        return None
    if _matches(numeric.real, candidates):
        return None
    # exact-form answers: compare against exact values the MS writes, e.g. \frac{32}{15}
    return f"final answer {expr} = {numeric.real:.6g} matches no value in the mark scheme"


def normalise_label(label: str | None) -> str:
    if not label or label.strip().lower() in ("-", "none", "whole", "whole question"):
        return "-"
    t = re.sub(r"^\s*part\s*", "", label.strip().lower())
    t = re.sub(r"^\(([a-z])\)", r"\1", t)            # "(a)(ii)" -> "a(ii)"
    t = re.sub(r"^\((iv|v|i{1,3})\)$", r"\1", t)      # "(ii)" -> "ii"
    return t.replace(" ", "")


def validate(reply: dict, question_id: str | None, allowed_note_ids: set[str]) -> tuple[dict, list[str]]:
    """Return (cleaned reply, warnings). The reply's insights gain a verbatim `quote`."""
    warnings: list[str] = []
    for part in reply["parts"]:  # tidy "(a)", "Part a", "a " -> "a" (the schema enum should prevent these)
        part["label"] = normalise_label(part["label"])
    for ins in reply["examiner_insights"]:
        ins["part_label"] = normalise_label(ins["part_label"])
    parts_db = {}
    if question_id:
        parts_db = {(p["label"] or "-"): p for p in db.rows(
            "SELECT label, marks, mark_scheme FROM question_parts WHERE question_id = ?", (question_id,))}
        got = [p["label"] for p in reply["parts"]]
        missing = [l for l in parts_db if l not in got]
        extra = [l for l in got if l not in parts_db]
        if missing:
            warnings.append(f"parts missing from the reply: {missing}")
        if extra:
            warnings.append(f"reply has parts not in the question: {extra}")

    for part in reply["parts"]:
        official = parts_db.get(part["label"])
        if official is None:
            continue
        ms_codes = set(_codes(official["mark_scheme"]))
        used = [c for step in part["steps"] for award in step["marks_awarded"] for c in _codes(award)
                if "likely" not in award.lower()]
        unknown = sorted({c for c in used if c not in ms_codes})
        if unknown:
            warnings.append(f"part {part['label']}: mark codes {unknown} are not in its mark scheme")
        total = sum(_value(c) for c in used)
        if used and total != official["marks"]:
            warnings.append(f"part {part['label']}: steps award {total} marks, the part is worth {official['marks']}")
        w = check_final_answer(part.get("final_answer_sympy", ""), official["mark_scheme"])
        if w:
            warnings.append(f"part {part['label']}: {w}")

    kept = []
    for ins in reply["examiner_insights"]:
        row = db.one("SELECT quote, display, kind, question_id, part_label FROM examiner_notes WHERE id = ?",
                     (ins["note_id"],))
        if row is None or (allowed_note_ids and ins["note_id"] not in allowed_note_ids):
            warnings.append(f"dropped examiner insight with unknown note_id {ins['note_id']}")
            continue
        kept.append(dict(ins, quote=row["display"] or row["quote"], kind=row["kind"],
                         from_question=row["question_id"]))
    reply = dict(reply, examiner_insights=kept)
    return reply, warnings
