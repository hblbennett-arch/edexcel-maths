#!/usr/bin/env python3
"""GL solution levels (docs/learn-layer-spec.md §1): deterministic checks on `parts[i].solution_levels`.
No model calls.

    .venv/bin/python scripts/clean/gate_levels.py ITEM.json [...]          # run, print, store gate_results.GL
    .venv/bin/python scripts/clean/gate_levels.py --dry ITEM.json           # run and print only

    from gate_levels import gate_levels, part_errors
    gate_levels(item) -> {"pass", "errors", "warnings", "parts_checked"}
    part_errors(item, part) -> (errors, warnings)          # one part (used by enrich_solutions.py for retries)

  Shape     brisk and every_step are non-empty lists; steps numbered 1..n; every `working` non-empty.
  KaTeX     every $...$ / $$...$$ in working, why and check renders (scripts/clean/katex_render.js); no
            unbalanced $, no \\( \\) delimiters, no LaTeX command outside a $ span.
  Codes     every `secures` code (brisk lists, every_step strings) is a code of the part's mark scheme
            (chatbot.marks.parse; compared by letter and digit, ignoring ft / * / cso / cao suffixes);
            brisk secures each scheme code exactly once, in scheme order.
  Answers   the last `working` of each level holds an expression sympy finds equal to each closed-form answer
            of the part ($...$ fragments, split at =, \\approx, \\Rightarrow, commas and "or"; exact answers
            need equality, dp-N / sf-N answers accept any value that rounds to the answer; a trailing unit is
            ignored). An answer found only in an earlier line of the level warns (intermediate results such
            as a constant of integration are listed in `answers` too). Parts whose
            command is explain / state / comment / suggest / interpret / describe / criticise / write-down, and
            parts with no answers, are skipped.
  Why       every every_step `why` is non-empty; every_step has at least as many lines as `solution`.
  Copy      G7 novelty (gates.py) on all level text: 8-gram hits against the private corpus fail.
  Words     no Pearson / Edexcel / AQA / OCR / examiner / past paper in any level text.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_maths as gm  # noqa: E402
from gate_style import LATEX_CMD, OTHER_DELIMS, katex_errors, spans  # noqa: E402
from chatbot import marks  # noqa: E402

SKIP_COMMANDS = {"explain", "state", "comment", "suggest", "interpret", "describe", "criticise", "write-down"}
BANNED = re.compile(r"\b(pearson|edexcel|aqa|ocr|examiners?|past\s+papers?)\b", re.I)
SPLIT_RE = re.compile(r"=|\\approx|\\Rightarrow|\\implies|\\therefore|\\to|\\iff|\\leqslant|\\geqslant|<|>|\\le\b|\\ge\b|\\neq")
LIST_RE = re.compile(r",|\\text\{\s*or\s*\}|\\quad|\\qquad|\\;|\bor\b|\\mathrm\{\s*or\s*\}")


# ---- LaTeX -> plain maths for sympy --------------------------------------------------------------
def _brace_arg(s: str, i: int) -> tuple[str, int]:
    """s[i] == '{': the balanced content and the index after the closing brace."""
    depth, j = 0, i
    while j < len(s):
        depth += s[j] == "{"
        depth -= s[j] == "}"
        if depth == 0:
            return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _replace_cmd(s: str, cmd: str, nargs: int, fmt) -> str:
    out, i = "", 0
    while True:
        k = s.find(cmd, i)
        if k < 0 or not (k + len(cmd) >= len(s) or not s[k + len(cmd)].isalpha()):
            if k < 0:
                return out + s[i:]
            out += s[i:k + len(cmd)]
            i = k + len(cmd)
            continue
        out += s[i:k]
        j, args = k + len(cmd), []
        while j < len(s) and s[j] == " ":
            j += 1
        for _ in range(nargs):
            if j < len(s) and s[j] == "{":
                a, j = _brace_arg(s, j)
            elif j < len(s):
                a, j = s[j], j + 1
            else:
                a = ""
            args.append(a)
        out += fmt(*args)
        i = j


def latex_to_maths(tex: str) -> str:
    """A LaTeX fragment as the plain maths gate_maths.parse reads (best effort; failures just don't match)."""
    s = tex
    s = re.sub(r"\\(left|right|,|;|!|quad|qquad|displaystyle)\b", " ", s)
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = re.sub(r"\\(d|t)?frac", r"\\frac", s)
    for _ in range(6):
        new = _replace_cmd(s, r"\frac", 2, lambda a, b: f"(({a})/({b}))")
        if new == s:
            break
        s = new
    s = _replace_cmd(s, r"\sqrt", 1, lambda a: f"sqrt({a})")
    s = _replace_cmd(s, r"\mathrm", 1, lambda a: a)
    s = _replace_cmd(s, r"\text", 1, lambda a: " ")
    s = _replace_cmd(s, r"\operatorname", 1, lambda a: a)
    s = re.sub(r"\^\s*\{", "^(", s)   # x^{3/2} -> x^(3/2 ...  (matching brace handled below)
    # convert remaining braces to parentheses (they only group now)
    s = s.replace("{", "(").replace("}", ")")
    words = {r"\pi": " pi ", r"\cdot": "*", r"\times": "*", r"\ln": " log", r"\log": " log", r"\arctan": " atan",
             r"\arcsin": " asin", r"\arccos": " acos", r"\sin": " sin", r"\cos": " cos", r"\tan": " tan",
             r"\sec": " sec", r"\cot": " cot", r"\csc": " csc", r"\exp": " exp", r"\div": "/", r"\infty": " oo ",
             r"\mathrm": "", r"\,": " ", r"\;": " ", r"\ ": " ", r"\%": ""}
    for k, v in sorted(words.items(), key=lambda kv: -len(kv[0])):
        s = s.replace(k, v)
    s = re.sub(r"\\[A-Za-z]+", " ", s)   # anything else: drop the command
    s = s.replace("e^", "exp1^")  # placeholder so the implicit-multiplication splitter keeps 'e'
    s = s.replace("exp1^", "e^")
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)   # "1 000" -> 1000
    s = re.sub(r"\s+", " ", s).strip(" .,;:")
    return s


def _candidates(working: str) -> list[str]:
    """Plain-maths candidate expressions in a working line: every $...$ span, each segment between = and
    relation signs, and each comma / 'or' separated piece of a segment."""
    found, _ = spans(working)
    cands: list[str] = []
    for tex, _display in found:
        segs = [tex] + [p for p in SPLIT_RE.split(tex) if p.strip()]
        for seg in segs:
            cands.append(seg)
            cands += [p for p in LIST_RE.split(seg) if p.strip()]
    out, seen = [], set()
    for c in list(cands):
        m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*(?:\\[,;! ]|\\mathrm|\\text|[A-Za-z%])", c)   # "0.0278 cm/s" -> 0.0278
        if m:
            cands.append(m.group(1))
    for c in cands:
        m = latex_to_maths(c)
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _parsed(cands: list[str]) -> list:
    out = []
    for c in cands:
        try:
            out.append(gm.parse(c))
        except Exception:
            # "y = 3x^2 + 4/x - 5" style leftovers: try trailing number-ish token
            continue
    return out


def answer_found(working: str, ans: dict) -> str | None:
    """None when some expression in the working equals the answer (per its form), else why not."""
    expr, form = ans.get("expr"), ans.get("form")
    try:
        target = gm.parse(str(expr), bool(ans.get("degrees")))
    except Exception:
        return None  # an answer sympy cannot read is not this gate's business (G2 covers it)
    vals = _parsed(_candidates(working))
    if not vals:
        return f"no maths expression found in the last working {working[:80]!r}"
    lit = str(expr).strip()
    for v in vals:
        try:
            if form and gm.FORM_RE.match(form):
                if gm.matches(v, lit, form) is None:
                    return None
                # the answer written as-is (0.283) also counts
                if gm.equal(v, target):
                    return None
            elif gm.is_decimal(lit) and gm.matches(v, lit) is None:
                return None
            elif gm.equal(v, target):
                return None
        except Exception:
            continue
    return f"last working does not contain a value equal to answer {ans.get('name') or ''} = {expr}" + \
        (f" (to {form})" if form else "")


# ---- codes ---------------------------------------------------------------------------------------
def _key(code: str) -> tuple | None:
    m = marks.try_parse(str(code or ""))
    return (m.kind, m.worth) if m else None


def _code_keys(codes: list[str]) -> list[tuple]:
    return [_key(c) or ("?", c) for c in codes]


def _texts(levels: dict) -> list[tuple[str, str]]:
    out = []
    for lvl in ("brisk", "every_step"):
        for i, e in enumerate(levels.get(lvl) or [], 1):
            if not isinstance(e, dict):
                continue
            for k in ("working", "why", "check"):
                if isinstance(e.get(k), str) and e[k]:
                    out.append((f"{lvl} {i} {k}", e[k]))
    return out


def part_errors(item: dict, part: dict, *, novelty: bool = True) -> tuple[list[str], list[str]]:
    w = f"part {part.get('label') or '-'}"
    errs, warns = [], []
    levels = part.get("solution_levels")
    if not isinstance(levels, dict):
        return [f"{w}: no solution_levels"], []
    brisk, every = levels.get("brisk"), levels.get("every_step")
    for name, lvl in (("brisk", brisk), ("every_step", every)):
        if not isinstance(lvl, list) or not lvl:
            errs.append(f"{w}: {name} is empty or not a list")
            continue
        for i, e in enumerate(lvl, 1):
            if not isinstance(e, dict):
                errs.append(f"{w}: {name} {i} is not an object")
                continue
            if e.get("step") != i:
                warns.append(f"{w}: {name} {i} numbered {e.get('step')!r}")
            if not (isinstance(e.get("working"), str) and e["working"].strip()):
                errs.append(f"{w}: {name} {i} has an empty working")
    if errs:
        return errs, warns

    # notation
    batch, where = [], []
    for wh, t in _texts(levels):
        found, outside = spans(t)
        if "$" in outside:
            errs.append(f"{w} {wh}: unbalanced $")
        if OTHER_DELIMS.search(t):
            errs.append(f"{w} {wh}: use $...$ for maths, not \\( \\) or \\[ \\]")
        elif cmds := sorted(set(LATEX_CMD.findall(outside))):
            errs.append(f"{w} {wh}: LaTeX outside a $ span: {' '.join(cmds[:5])}")
        batch += found
        where += [wh] * len(found)
        for m in BANNED.finditer(t):
            errs.append(f"{w} {wh}: banned word {m.group(0)!r}")
    for wh, (tex, _), e in zip(where, batch, katex_errors(batch)):
        if e:
            errs.append(f"{w} {wh}: KaTeX error in ${tex[:60]}$: {e}")

    # codes
    scheme = [m.get("code", "") for m in part.get("mark_scheme") or []]
    scheme_keys = _code_keys(scheme)
    brisk_codes: list[str] = []
    for i, e in enumerate(brisk, 1):
        sec = e.get("secures")
        if isinstance(sec, str):
            sec = [sec]
        if not isinstance(sec, list):
            errs.append(f"{w}: brisk {i} secures must be a list of scheme codes")
            continue
        brisk_codes += [str(c) for c in sec]
    brisk_keys = _code_keys(brisk_codes)
    for c, k in zip(brisk_codes, brisk_keys):
        if k not in scheme_keys:
            errs.append(f"{w}: brisk secures {c!r}, which is not a code of this part's scheme {scheme}")
    if brisk_keys != scheme_keys:
        if sorted(map(str, brisk_keys)) == sorted(map(str, scheme_keys)):
            errs.append(f"{w}: brisk secures the scheme codes out of order: {brisk_codes} vs scheme {scheme}")
        else:
            missing = [c for c, k in zip(scheme, scheme_keys) if brisk_keys.count(k) < scheme_keys.count(k)]
            extra = [c for c, k in zip(brisk_codes, brisk_keys) if brisk_keys.count(k) > scheme_keys.count(k)]
            errs.append(f"{w}: brisk must secure each scheme code exactly once in order {scheme}; "
                        f"missing {missing}, duplicated or extra {extra}")
    every_codes = []
    for i, e in enumerate(every, 1):
        sec = e.get("secures")
        if sec in (None, "", []):
            continue
        if isinstance(sec, list):
            if len(sec) != 1:
                errs.append(f"{w}: every_step {i} secures must be one code or null")
                continue
            sec = sec[0]
        if _key(str(sec)) not in scheme_keys:
            errs.append(f"{w}: every_step {i} secures {sec!r}, not a code of this part's scheme {scheme}")
        every_codes.append(str(sec))
        if not (isinstance(e.get("why"), str) and e["why"].strip()):
            pass
    every_keys = _code_keys(every_codes)
    if sorted(map(str, every_keys)) != sorted(map(str, scheme_keys)):
        warns.append(f"{w}: every_step secures {every_codes}, scheme is {scheme}")
    elif every_keys != scheme_keys:
        warns.append(f"{w}: every_step secures the codes out of scheme order: {every_codes}")

    # why, length
    for i, e in enumerate(every, 1):
        if not (isinstance(e.get("why"), str) and e["why"].strip()):
            errs.append(f"{w}: every_step {i} has an empty why")
    n_std = len(part.get("solution") or [])
    if len(every) < n_std:
        errs.append(f"{w}: every_step has {len(every)} lines, fewer than the standard solution's {n_std}")
    if n_std and len(every) < 2 * n_std:
        warns.append(f"{w}: every_step has {len(every)} lines for a {n_std}-line standard solution (aim for 2 to 4 times)")

    # answers: in the last working; an answer that is only an intermediate result (e.g. a constant of
    # integration listed in `answers` for G2) may sit in an earlier line, which warns instead
    if part.get("command") not in SKIP_COMMANDS:
        for name, lvl in (("brisk", brisk), ("every_step", every)):
            last = lvl[-1].get("working", "")
            for ans in part.get("answers") or []:
                if not isinstance(ans, dict) or not ans.get("expr"):
                    continue
                if (why := answer_found(last, ans)):
                    if any(answer_found(e.get("working", ""), ans) is None for e in lvl[:-1]):
                        warns.append(f"{w}: {name}: answer {ans.get('name') or ''} = {ans['expr']} appears in an earlier "
                                     f"line but not the last working")
                    else:
                        errs.append(f"{w}: {name}: {why}")

    # copy check
    if novelty:
        try:
            import gates
            pseudo = {"id": item.get("id"), "stem": "", "parts": [{
                "label": part.get("label"), "marks": part.get("marks"), "text": "",
                "solution": [{"working": t} for _, t in _texts(levels)]}]}
            r = gates.g7_novelty(pseudo)
            errs += [f"{w}: copy check: {x}" for x in r.get("reasons", [])]
            if r.get("hits8"):  # name the phrases to reword, so a retry fixes them first time
                errs.append(f"{w}: reword these phrases: " + " | ".join(repr(g) for g in r["hits8"]))
            warns += [f"{w}: copy check flag: {x}" for x in r.get("flags", [])]
        except Exception as ex:  # corpus unavailable: fail closed
            errs.append(f"{w}: copy check unavailable ({type(ex).__name__}: {ex})")
    return errs, warns


def gate_levels(item: dict, *, novelty: bool = True) -> dict:
    errs, warns, n = [], [], 0
    for p in item.get("parts") or []:
        if "solution_levels" not in p:
            warns.append(f"part {p.get('label') or '-'}: no solution_levels yet")
            continue
        n += 1
        e, w = part_errors(item, p, novelty=novelty)
        errs, warns = errs + e, warns + w
    if n == 0:
        errs.append("no part has solution_levels")
    return {"pass": not errs, "errors": errs, "warnings": warns, "parts_checked": n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--dry", action="store_true", help="don't write gate_results.GL back into the item files")
    ap.add_argument("--no-novelty", action="store_true", help="skip the G7 copy check (fast local run)")
    args = ap.parse_args()
    failed = 0
    for path in map(Path, args.items):
        item = json.loads(path.read_text())
        r = gate_levels(item, novelty=not args.no_novelty)
        failed += not r["pass"]
        print(f"{path.name}: GL {'PASS' if r['pass'] else 'FAIL'} ({r['parts_checked']} part(s))")
        for e in r["errors"]:
            print(f"    error: {e}")
        for e in r["warnings"]:
            print(f"    warning: {e}")
        if not args.dry:
            item["gate_results"] = {**(item.get("gate_results") or {}), "GL": r}
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
            tmp.replace(path)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
