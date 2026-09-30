#!/usr/bin/env python3
"""G8 style (item level): deterministic house-style checks on a generated item. No model calls.

    .venv/bin/python scripts/clean/gate_style.py ITEM.json [...]      # print results only

  Notation   maths goes in $...$ or $$...$$ only (the product renders nothing else): every such span in the
             stem, part text, mark scheme (`for`, `notes`, alternatives too), solution working, hints and pitfalls
             renders with KaTeX (throwOnError; one node process per item, scripts/clean/katex_render.js); no
             unbalanced $ (\\$ is a dollar sign), no \\( \\) or \\[ \\] delimiters, and no LaTeX command
             (\\frac, \\sqrt, \\mathrm, ...) outside a $ span.
  Marks      each part's text ends "(N)" with N = its marks.
  Command    `command` is a code from build_facts.COMMANDS and the part text contains that wording (same regex).
  Forms      `forms` codes are build_facts.FORMS codes or dp-N / sf-N; exact, dp-N, sf-N and in-the-form must
             be asked for in the part text (build_facts.forms_of: "3 significant figures" or "three ...").
  Shape      marks per part, total marks and number of parts lie within the range seen for the item's
             `question_type` (content/facts/aggregates.json by_question_type: marks_per_part, question_marks,
             parts_per_question), allowing 1 either side of the observed min / max. Unknown type: error. A type
             seen in fewer than MIN_TYPE_QUESTIONS real questions gives warnings, not errors (its range is too
             thin to be a house style).
  Mark scheme codes M1 A1 B1 dM1 ddM1 dB1 with an optional ft or *; code-like words in the notes in that form
             too (DM1, M1FT are errors); awrt, oe, cao, isw, cso as lowercase words. A cso/cao code suffix warns.
  Branding   no "Pearson", "Edexcel", "examiner(s)" or "PMT" in any string of the item.
  Calculator a part whose forms include no-calc-tech has a rubric sentence in its text (mentions a calculator
             and showing working / reasoning / method) in our own words: the exam-board sentence "Solutions
             relying entirely on calculator technology are not acceptable" is rejected anywhere in the item.
"""
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_facts import COMMANDS, FORMS, forms_of  # noqa: E402

AGGREGATES = ROOT / "content" / "facts" / "aggregates.json"
KATEX_JS = Path(__file__).resolve().parent / "katex_render.js"
MIN_TYPE_QUESTIONS = 5
SPAN_RE = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.S)
OTHER_DELIMS = re.compile(r"\\[()\[\]]")
LATEX_CMD = re.compile(r"\\[A-Za-z]+")
ASKED_FORMS = ("exact", "in-the-form")
CODE_STYLE = re.compile(r"^(ddM|dM|dB|M|A|B)[1-9](ft|\*|cso|cao)?$")
CODE_WORD = re.compile(r"(?<![A-Za-z0-9])((?:dd|d)?[mab])([1-9])(ft|\*)?(?![A-Za-z0-9])", re.I)
ABBREV = re.compile(r"\b(awrt|oe|cao|isw|cso)\b", re.I)
BANNED = re.compile(r"\b(pearson|edexcel|examiners?|pmt)\b", re.I)
BOARD_RUBRIC = re.compile(r"relying\s+entirely\s+on\s+calculator|calculator\s+technology\s+(is|are)\s+not\s+acceptable",
                          re.I)
OUR_RUBRIC = (re.compile(r"calculator", re.I), re.compile(r"\b(show|reasoning|working|method)", re.I))
FORM_CODE = re.compile(r"^(dp|sf)-\d+$")


# ---- notation --------------------------------------------------------------------------------
def texts(item: dict) -> list[tuple[str, str]]:
    """(where, text) for every field that may hold LaTeX."""
    out = [("stem", item.get("stem") or "")]
    for p in item.get("parts") or []:
        w = f"part {p.get('label') or '-'}"
        out.append((f"{w} text", p.get("text") or ""))
        schemes = [("", p.get("mark_scheme") or [])] + [(f" {a.get('name', 'alt')}", a.get("marks") or [])
                                                       for a in p.get("alternatives") or []]
        for alt, marks in schemes:
            for i, m in enumerate(marks, 1):
                out += [(f"{w}{alt} mark {i} {k}", m.get(k) or "") for k in ("for", "notes")]
        for i, s in enumerate(p.get("solution") or [], 1):
            out.append((f"{w} solution {i}", s.get("working", "") if isinstance(s, dict) else str(s)))
        out += [(f"{w} hint {i}", h) for i, h in enumerate(p.get("hints") or [], 1)]
    out += [(f"pitfall {i}", pf.get("text") or "") for i, pf in enumerate(item.get("pitfalls") or [], 1)]
    return [(w, t if isinstance(t, str) else str(t)) for w, t in out if t]


def spans(text: str) -> tuple[list[tuple[str, bool]], str]:
    """(LaTeX spans with display flag, the text left outside them); an escaped \\$ is not a delimiter."""
    text = text.replace(r"\$", "")
    found = [(m.group(1) or m.group(2), bool(m.group(1))) for m in SPAN_RE.finditer(text)]
    return found, SPAN_RE.sub(" ", text)


def katex_errors(batch: list[str | bool]) -> list[str | None]:
    if not batch:
        return []
    try:
        r = subprocess.run(["node", str(KATEX_JS)], input=json.dumps([{"tex": t, "display": d} for t, d in batch]),
                           capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except Exception as ex:  # no node / katex: fail closed
        return [f"KaTeX check unavailable ({type(ex).__name__})"] * len(batch)


def notation_errors(item: dict) -> list[str]:
    errs, batch, where = [], [], []
    for w, t in texts(item):
        found, outside = spans(t)
        if "$" in outside:
            errs.append(f"{w}: unbalanced $")
        if OTHER_DELIMS.search(t):
            errs.append(f"{w}: use $...$ or $$...$$ for maths, not \\( \\) or \\[ \\]")
        elif cmds := sorted(set(LATEX_CMD.findall(outside))):
            errs.append(f"{w}: LaTeX outside a $ span: {' '.join(cmds[:5])}")
        batch += found
        where += [w] * len(found)
    for w, (tex, _), e in zip(where, batch, katex_errors(batch)):
        if e:
            errs.append(f"{w}: KaTeX error in ${tex[:60]}$: {e}")
    return errs


# ---- structure and wording -------------------------------------------------------------------
@lru_cache(maxsize=1)
def by_type() -> dict:
    return json.loads(AGGREGATES.read_text())["by_question_type"]


def _in_range(value: int, hist: dict, what: str) -> str | None:
    seen = [int(k) for k in hist]
    lo, hi = min(seen) - 1, max(seen) + 1
    return None if lo <= value <= hi else f"{what} {value} outside {lo}-{hi} (seen {min(seen)}-{max(seen)}, +-1)"


def shape_issues(item: dict) -> tuple[list[str], list[str]]:
    qt, parts = item.get("question_type"), item.get("parts") or []
    facts = by_type().get(qt)
    if not facts:
        return [f"unknown question_type {qt!r}"], []
    issues = [_in_range(p.get("marks"), facts["marks_per_part"], f"part {p.get('label') or '-'} marks")
              for p in parts if isinstance(p.get("marks"), int)]
    issues += [_in_range(sum(p.get("marks") or 0 for p in parts), facts["question_marks"], "total marks"),
               _in_range(len(parts), facts["parts_per_question"], "number of parts")]
    issues = [f"{qt}: {i}" for i in issues if i]
    if facts["n_questions"] < MIN_TYPE_QUESTIONS:
        return [], [f"{i} (only {facts['n_questions']} real questions of this type)" for i in issues]
    return issues, []


def part_errors(p: dict) -> list[str]:
    w, text, errs = f"part {p.get('label') or '-'}", p.get("text") or "", []
    m = re.search(r"\((\d+)\)\s*$", text)
    if not m:
        errs.append(f"{w}: text does not end with its marks in brackets, ({p.get('marks')})")
    elif int(m.group(1)) != p.get("marks"):
        errs.append(f"{w}: text ends ({m.group(1)}) but the part is worth {p.get('marks')}")
    cmd = p.get("command")
    if cmd not in COMMANDS:
        errs.append(f"{w}: command {cmd!r} is not a command code")
    elif not re.search(COMMANDS[cmd], text.lower(), re.M):
        errs.append(f"{w}: command {cmd!r} but the text does not use that wording")
    asked = forms_of(text)
    for f in p.get("forms") or []:
        if f not in FORMS and not FORM_CODE.match(str(f)):
            errs.append(f"{w}: unknown form {f!r}")
        elif (f in ASKED_FORMS or FORM_CODE.match(str(f))) and f not in asked:
            errs.append(f"{w}: form {f!r} but the text does not ask for it")
    if "no-calc-tech" in (p.get("forms") or []) and not all(rx.search(text) for rx in OUR_RUBRIC):
        errs.append(f"{w}: no-calc-tech part without a calculator rubric sentence in its text")
    return errs


def mark_scheme_issues(p: dict) -> tuple[list[str], list[str]]:
    w, errs, warns = f"part {p.get('label') or '-'}", [], []
    marks = list(p.get("mark_scheme") or []) + [m for a in p.get("alternatives") or [] for m in a.get("marks") or []]
    for m in marks:
        code = m.get("code", "")
        if not CODE_STYLE.match(code):
            errs.append(f"{w}: mark code {code!r} not in the form M1 / A1 / B1 / dM1 / A1ft / A1*")
        elif code.endswith(("cso", "cao")):
            warns.append(f"{w}: write {code} as {code[:-3]} with '{code[-3:]}' in its notes")
        for k in ("for", "notes"):
            _, outside = spans(m.get(k) or "")
            for c in CODE_WORD.finditer(outside):
                base, flag = c.group(1), c.group(3) or ""
                if base.islower() and len(base) == 1:
                    continue  # "a1" / "m1" in prose is more likely maths than a code
                if base not in ("M", "A", "B", "dM", "ddM", "dB") or flag not in ("", "ft", "*"):
                    errs.append(f"{w} {code} {k}: mark code written {c.group(0)!r}")
            errs += [f"{w} {code} {k}: write {a.group(0)!r} in lowercase" for a in ABBREV.finditer(outside)
                     if a.group(0) != a.group(0).lower()]
    return errs, warns


def all_strings(x, path="item"):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            if k not in ("gate_results", "review"):
                yield from all_strings(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from all_strings(v, f"{path}[{i}]")


def g8_style(item: dict) -> dict:
    errs, warns = notation_errors(item), []
    e, w = shape_issues(item)
    errs, warns = errs + e, warns + w
    for p in item.get("parts") or []:
        errs += part_errors(p)
        e, w = mark_scheme_issues(p)
        errs, warns = errs + e, warns + w
        if "forms" not in p:
            warns.append(f"part {p.get('label') or '-'}: no forms list (use [] for none)")
    for path, s in all_strings(item):
        errs += [f"{path}: mentions {m.group(0)!r}" for m in BANNED.finditer(s)]
        if BOARD_RUBRIC.search(s):
            errs.append(f"{path}: uses the exam board's calculator rubric wording; word it our own way")
    return {"pass": not errs, "errors": errs, "warnings": warns}


if __name__ == "__main__":
    bad = 0
    for path in sys.argv[1:]:
        r = g8_style(json.loads(Path(path).read_text()))
        bad += not r["pass"]
        print(f"{Path(path).name}: G8 {'PASS' if r['pass'] else 'FAIL'}")
        for e in r["errors"]:
            print(f"    error: {e}")
        for e in r["warnings"]:
            print(f"    warning: {e}")
    sys.exit(1 if bad else 0)
