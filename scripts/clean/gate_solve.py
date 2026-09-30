#!/usr/bin/env python3
"""G3 blind solve: a different model solves the question from its text alone (docs/handoff-clean-room.md §6).

    .venv/bin/python scripts/clean/gate_solve.py content/clean/items/*.json [--dry]

One `claude -p` call per item on Sonnet 5.5 (the generator is Opus 5.5). The solver sees only the stem and
part texts: no mark scheme, solution or answers. It returns its final answers per part as sympy-style
expressions, whether each printed ("show that") result is correct, and any ambiguity or error it finds.
Pass rule: every part's expected answers are matched by one of the solver's (numerically, allowing the
stated rounding or 1 in the last figure; when they don't line up, a judge call decides whether it's the same
mathematics in another form), no show-that result is disputed, and no "blocker" problem is reported ("minor" ones are
flags for the reviewer).
Stores the result under gate_results.G3 (so the item file is rewritten unless --dry).
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_oneshot  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_maths as gm  # noqa: E402

MODEL = "claude-sonnet-5-5"
SYSTEM = """You are an expert A level Mathematics teacher checking a new exam question before it is used. Solve it
yourself, carefully and independently, then report. For each part give your final answers as plain sympy-style
expressions (e.g. 3/2, 2*sqrt(3) - 1, log(5)/2, 0.0332, [pi/6, 5*pi/6] as separate answers). For a part that asks you
to show a printed result, say whether the printed result is correct. Then list every problem a careful student or
teacher would raise: ambiguity (more than one reasonable reading, missing information, unclear interval or units),
mathematical errors in the question, impossible or unrealistic values, or marks that don't fit the work. Give each problem
a severity: "blocker" if a careful student could not answer it, could reasonably reach a different answer, or the
question or its printed result is wrong; otherwise "minor" (worth a reviewer's look, but the question works). Report
real problems only, not style preferences. Reply in the requested JSON."""
SCHEMA = {"type": "object", "properties": {
    "parts": {"type": "array", "items": {"type": "object", "properties": {
        "label": {"type": ["string", "null"]},
        "answers": {"type": "array", "items": {"type": "string"}},
        "printed_result_correct": {"type": ["boolean", "null"], "description": "show-that parts only, else null"},
        "working_summary": {"type": "string"}}, "required": ["label", "answers", "printed_result_correct"]}},
    "problems": {"type": "array", "items": {"type": "object", "properties": {
        "part": {"type": ["string", "null"]}, "kind": {"type": "string", "enum": ["ambiguity", "error", "unrealistic", "marks"]},
        "severity": {"type": "string", "enum": ["blocker", "minor"]},
        "detail": {"type": "string"}}, "required": ["kind", "severity", "detail"]}}},
    "required": ["parts", "problems"]}

def norm_label(label) -> str:
    return re.sub(r"(?i)^part|[()\s]", "", str(label or "")).lower()


def solver_expr(answer: str):
    """The solver's answer as a sympy expression (G2's safe parser), or None. Prose such as
    "P(X<=3)=0.0601 > 0.05, so do not reject H0" gives the value after the last "=" (0.0601)."""
    text = str(answer or "").strip()
    cands = [text]
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?(?:e-?\d+)?)\s*[a-zA-Z%°][\w/^%°\s-]*$", text)  # "0.0278 cm/s" -> 0.0278
    if m:
        cands.append(m.group(1))
    if "=" in text:
        cands.append(re.split(r"[<>,;]|\bso\b|\band\b|\bwhich\b", text.rsplit("=", 1)[1])[0])
    for c in cands:
        try:
            return gm.parse(c.strip())
        except Exception:  # noqa: BLE001 - unparsable answers don't match
            continue
    return None


def _half_ulp(lit: str) -> float:
    """One unit in the last written decimal place of a literal (0 if it isn't a decimal). A full unit, not
    half: a calculator value and one worked from rounded intermediate values can differ by 1 in the last figure
    (0.0677 vs 0.0678), and both would score as "awrt"."""
    m = re.fullmatch(r"\s*-?\d+\.(\d+)\s*", str(lit))
    return 1.0 * 10 ** -len(m.group(1)) if m else 0.0


def matches(want_expr: str, form: str | None, got_expr, got_lit: str) -> bool:
    """Does the solver's value equal ours? Numbers: within the rounding either side wrote (a stated dp-N /
    sf-N form, or the decimal places in the literal). Expressions: symbolically equal."""
    import sympy as sp
    want = gm.parse(want_expr)
    if want.free_symbols or got_expr.free_symbols:
        return bool(gm.equal(want, got_expr))
    try:
        a, b = float(sp.N(got_expr)), float(sp.N(want))
    except (TypeError, ValueError):
        return False
    tol = max(_half_ulp(want_expr), _half_ulp(got_lit), 1e-9 * max(1.0, abs(b)))
    if form and form.startswith("dp-"):
        tol = max(tol, 0.5 * 10 ** -int(form[3:]))
    elif form and form.startswith("sf-"):
        tol = max(tol, 0.5 * 10 ** (math.floor(math.log10(abs(b) or 1)) - int(form[3:]) + 1))
    return abs(a - b) <= tol * 1.01


JUDGE_MODEL = "claude-sonnet-5-5"
JUDGE_SYSTEM = """You compare two sets of answers to the same A level Mathematics question part: the question
setter's and an independent solver's. Decide whether they give the same mathematical results, allowing for
equivalent forms (factorised or expanded, exact or decimal to sensible accuracy, constants named differently,
the solver giving a coefficient where the setter gives the whole expression, units written or not). They
disagree if any value or conclusion actually differs, or if the solver missed or added a solution. Reply in JSON."""
JUDGE_SCHEMA = {"type": "object", "properties": {"parts": {"type": "array", "items": {"type": "object", "properties": {
    "label": {"type": ["string", "null"]}, "same": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["label", "same", "reason"]}}}, "required": ["parts"]}


def judge(item: dict, disputed: dict, res: dict) -> tuple[dict, float]:
    """One call for all disputed parts: {label: (same, reason)}. Not blind: it sees both sets of answers."""
    body = [f"# Question\n{question_text(item)}"]
    for lab, p in disputed.items():
        solver = [x for x in res.get("parts", []) if norm_label(x.get("label")).startswith(norm_label(lab))]
        body.append(f"# Part {lab}\nSetter's answers: {[(a.get('name'), a.get('expr')) for a in p.get('answers') or []]}\n"
                    f"Solver's answers: {[a for x in solver for a in x.get('answers', [])]}\n"
                    f"Solver's working: {' | '.join(x.get('working_summary', '') for x in solver)[:1500]}")
    out = claude_oneshot.run(JUDGE_SYSTEM, [claude_oneshot.text_block("\n\n".join(body))], schema=JUDGE_SCHEMA,
                             model=JUDGE_MODEL, max_usd=0.3, thinking_tokens=3000, step="clean-g3-judge", ref=item["id"])
    verdicts = {norm_label(v.get("label")): (bool(v["same"]), v.get("reason", "")) for v in out["result"]["parts"]}
    return verdicts, out["cost_usd"] or 0


def question_text(item: dict) -> str:
    lines = [item.get("stem") or ""]
    for p in item["parts"]:
        lines.append(f"({p['label']}) {p['text']}" if p.get("label") else p["text"])
    return "\n\n".join(l for l in lines if l)


def g3_blind_solve(item: dict) -> dict:
    out = claude_oneshot.run(SYSTEM, [claude_oneshot.text_block(question_text(item))], schema=SCHEMA, model=MODEL,
                             max_usd=1.0, thinking_tokens=8000, step="clean-g3", ref=item["id"], timeout=900)
    res = out["result"]
    errors, flags, disputed, pending = [], [], {}, []
    for p in item["parts"]:
        # the solver may split a part into sub-parts: (b) collects "b(i)", "b(ii)", but (a)(i) never collects (a)(ii)
        lab = norm_label(p.get("label"))
        subs = [x for x in res.get("parts", []) if not lab or norm_label(x.get("label")) == lab
                or (re.fullmatch(r"[a-z]", lab) and re.fullmatch(lab + r"(i|ii|iii|iv|v|vi)", norm_label(x.get("label"))))]
        if not subs:
            errors.append(f"part {p.get('label') or '-'}: solver gave no answer")
            continue
        if p.get("command") == "show-that" and any(x.get("printed_result_correct") is False for x in subs):
            errors.append(f"part {p.get('label') or '-'}: solver disputes the printed result")
        answers = [x for sub in subs for x in sub.get("answers", [])]
        got = [(solver_expr(x), x) for x in answers]
        got = [(e, lit) for e, lit in got if e is not None]
        used = set()
        for a in p.get("answers") or []:
            try:
                hit = [i for i, (e, lit) in enumerate(got) if matches(a.get("expr", ""), a.get("form"), e, lit)]
            except Exception:  # noqa: BLE001 - our own answer must parse (G2 checks it too)
                errors.append(f"part {p.get('label') or '-'}: our answer {a.get('name')} = {a.get('expr')!r} doesn't parse")
                continue
            if not hit:
                disputed.setdefault(p.get("label") or "-", p)
                pending.append((p.get("label") or "-",
                                f"part {p.get('label') or '-'}: expected {a.get('name')} = {a.get('expr')}, solver got {answers}"))
            used.update(hit)
        # the other direction: a value the solver found that we don't have (e.g. a missing root) is a flag
        if p.get("answers"):
            extra = [lit for i, (e, lit) in enumerate(got) if i not in used and not e.free_symbols]
            if extra:
                flags.append(f"part {p.get('label') or '-'}: solver also gave {extra}")
    judge_cost = 0.0
    if pending:  # numbers didn't line up: a judge decides whether it's the same mathematics in another form
        verdicts, judge_cost = judge(item, disputed, res)
        for lab, msg in pending:
            same, reason = verdicts.get(norm_label(lab), (False, "no verdict"))
            (flags if same else errors).append(msg + (f" [judge: same - {reason}]" if same else f" [judge: differs - {reason}]"))
    for pr in res.get("problems", []):
        (errors if pr.get("severity") != "minor" else flags).append(
            f"{pr['kind']} (part {pr.get('part') or '-'}): {pr['detail']}")
    return {"pass": not errors, "errors": errors, "flags": flags, "flag": bool(flags), "model": MODEL,
            "cost_usd": round((out["cost_usd"] or 0) + judge_cost, 4), "solver": res}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    total = 0.0
    for f in map(Path, args.items):
        item = json.loads(f.read_text())
        r = g3_blind_solve(item)
        total += r["cost_usd"] or 0
        print(f"{item['id']}: G3 {'PASS' if r['pass'] else 'FAIL'} (${r['cost_usd']:.3f})")
        for e in r["errors"][:6]:
            print("    ", e[:200])
        if not args.dry:
            item.setdefault("gate_results", {})["G3"] = r
            f.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
    print(f"total ${total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
