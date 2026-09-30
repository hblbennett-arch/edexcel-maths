#!/usr/bin/env python3
"""G4 mark-scheme unit tests and G5 pitfall validity (docs/handoff-clean-room.md §6).

    .venv/bin/python scripts/clean/gate_marking.py content/clean/items/*.json [--dry]

G4, two `claude -p` calls on Sonnet 5.5:
  1. Script writer: sees the whole item and writes 4-6 student responses, each with the mark vector it was
     designed to earn: fully correct; one per pitfall (the wrong working that error code implies); a correct
     alternative method if the scheme has one; a partial attempt.
  2. Marker: sees only the question, OUR mark scheme and the responses (not the designed vectors), and
     awards each mark: the prototype of "mark my working".
  Pass: the awarded vector equals the designed vector for every response.
G5 (deterministic, uses G4's responses): every pitfall names a real solution step and one of the
blueprint's error codes, uses the question's own numbers (numerical parts) or its context (explain / state
parts), says "common" only when flagged
`says_common`, and is demonstrated by a response that loses marks and that the marker scored as designed.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_oneshot  # noqa: E402
sys.path.insert(0, str(ROOT))
from chatbot.text import latex_to_plain  # noqa: E402

MODEL = "claude-sonnet-5-5"
SECOND_MARKER = "claude-opus-5-5"  # only for scripts where the first marker and the design disagree
WORDED_COMMANDS = {"explain", "state", "comment", "suggest", "interpret", "describe", "criticise", "write-down"}
FREQUENT_NOTES = 10  # an error code may be called "common" at >= this many matched notes (calibrate: checklist §28)
WRITER_SYSTEM = """You test a new A level Mathematics mark scheme. Given a question, its mark scheme, worked solution and
list of pitfalls, write realistic student responses (as a student would write them: working lines, LaTeX in $...$)
that test whether the mark scheme awards marks correctly. Write: (1) one fully correct response using the main
method; (2) one response per pitfall, containing exactly the mistake the pitfall describes and otherwise sensible
working (continue the working after the mistake, as a real student would, so follow-through marks can be tested);
(3) if the scheme lists an alternative method, one fully correct response using it; (4) one partial attempt that
stops part-way. For each response give the designed mark vector: for every part, the list of the scheme's mark codes
in order, each written as awarded or not (e.g. ["M1", "A0", "dM1", "A1ft"]; use "M0"/"A0"/"B0" for a mark not earned,
keep "ft"/"*" suffixes). Apply the mark scheme exactly as written, including dependencies (A and dM marks need the M
before them) and follow-through."""
MARKER_SYSTEM = """You are an A level Mathematics examiner. Mark each student response strictly by the mark scheme
provided: award each mark only when its description is met, respect dependencies (A marks need the preceding M mark;
dM needs the previous M), allow follow-through (ft) marks as the scheme describes, and apply cao/cso/awrt/oe/isw as
stated. For every response and every part, return the scheme's codes in order, each as awarded (e.g. "M1") or not
(e.g. "M0"), keeping "ft"/"*" suffixes, plus a one-line reason for each mark not awarded."""
VEC = {"type": "array", "items": {"type": "object", "properties": {
    "part": {"type": ["string", "null"]}, "marks": {"type": "array", "items": {"type": "string"}}},
    "required": ["part", "marks"]}}
WRITER_SCHEMA = {"type": "object", "properties": {"responses": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "kind": {"type": "string", "enum": ["correct", "pitfall", "alternative", "partial"]},
    "error_code": {"type": ["string", "null"]}, "work": {"type": "string"}, "designed": VEC},
    "required": ["id", "kind", "work", "designed"]}}}, "required": ["responses"]}
MARKER_SCHEMA = {"type": "object", "properties": {"results": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "string"}, "awarded": VEC, "reasons": {"type": "array", "items": {"type": "string"}}},
    "required": ["id", "awarded"]}}}, "required": ["results"]}


def scheme_text(item: dict, with_alternatives: bool = True) -> str:
    lines = []
    for p in item["parts"]:
        lines.append(f"Part {p.get('label') or '-'} ({p['marks']} marks)")
        lines += [f"  {m['code']}: {m['for']}" + (f" [{m['notes']}]" if m.get("notes") else "") for m in p["mark_scheme"]]
        for alt in (p.get("alternatives") or []) if with_alternatives else []:
            lines.append(f"  {alt.get('name', 'Alternative')}:")
            lines += [f"    {m['code']}: {m['for']}" + (f" [{m['notes']}]" if m.get("notes") else "") for m in alt["marks"]]
    return "\n".join(lines)


def question_text(item: dict) -> str:
    lines = [item.get("stem") or ""] + [(f"({p['label']}) " if p.get("label") else "") + p["text"] for p in item["parts"]]
    return "\n\n".join(l for l in lines if l)


def norm_label(label) -> str:
    """'(a)', 'Part a', 'a' -> 'a'; '(b)(i)' -> 'bi'; None / '-' -> '-'."""
    t = re.sub(r"(?i)^part\s*", "", str(label or "-"))
    return re.sub(r"[()\s]", "", t).lower() or "-"


def _mark(code: str) -> str:
    """A mark as awarded or not, ignoring suffixes the marker may drop: 'A1*', 'A1ft', 'A1cso' -> 'A1'."""
    m = re.match(r"\s*(ddM|dM|dB|DM|M|A|B)(\d)", code or "")
    return f"{m.group(1).replace('DM', 'dM')}{m.group(2)}" if m else (code or "").strip()


def _norm(vec: list[dict]) -> dict:
    return {norm_label(v.get("part")): [_mark(m) for m in v.get("marks", [])] for v in vec}


def g4_marking(item: dict) -> dict:
    solution = "\n".join(f"Part {p.get('label') or '-'}: " + " | ".join(s["working"] for s in p.get("solution") or [])
                         for p in item["parts"])
    pitfalls = "\n".join(f"- [{pf.get('error_code')}] part {pf.get('part') or '-'}: {pf['text']}" for pf in item.get("pitfalls") or [])
    w = claude_oneshot.run(WRITER_SYSTEM, [claude_oneshot.text_block(
        f"# Question\n{question_text(item)}\n\n# Mark scheme\n{scheme_text(item)}\n\n# Worked solution\n{solution}\n\n# Pitfalls\n{pitfalls}")],
        schema=WRITER_SCHEMA, model=MODEL, max_usd=1.0, thinking_tokens=6000, step="clean-g4-write", ref=item["id"])
    responses = w["result"]["responses"]
    body = "\n\n".join(f"## Response {r['id']}\n{r['work']}" for r in responses)
    m = claude_oneshot.run(MARKER_SYSTEM, [claude_oneshot.text_block(
        f"# Question\n{question_text(item)}\n\n# Mark scheme\n{scheme_text(item)}\n\n# Student responses\n{body}")],
        schema=MARKER_SCHEMA, model=MODEL, max_usd=1.0, thinking_tokens=6000, step="clean-g4-mark", ref=item["id"])
    first = m["result"]["results"]
    out = score_g4(item, responses, first)
    cost = (w["cost_usd"] or 0) + (m["cost_usd"] or 0)
    mismatched = [r for r in responses if r["id"] in out["mismatched"]]
    if mismatched:  # a second, different marker settles whether the scheme or the script's design is at fault
        body2 = "\n\n".join(f"## Response {r['id']}\n{r['work']}" for r in mismatched)
        m2 = claude_oneshot.run(MARKER_SYSTEM, [claude_oneshot.text_block(
            f"# Question\n{question_text(item)}\n\n# Mark scheme\n{scheme_text(item)}\n\n# Student responses\n{body2}")],
            schema=MARKER_SCHEMA, model=SECOND_MARKER, max_usd=1.0, thinking_tokens=6000, step="clean-g4-mark2",
            ref=item["id"])
        cost += m2["cost_usd"] or 0
        out = score_g4(item, responses, first, second=m2["result"]["results"])
    out["cost_usd"] = round(cost, 4)
    return out


def score_g4(item: dict, responses: list[dict], results: list[dict], second: list[dict] | None = None) -> dict:
    """Compare designed and awarded vectors (no model calls: re-runnable on stored G4 output). With a second
    marker's results for the mismatched responses: both markers agree -> the scheme is applied consistently and
    the script's design was off (a flag, and the markers' vector is what the script earns); the second marker
    agrees with the design -> first-marker noise (a flag); the markers disagree -> the scheme is ambiguous (fail)."""
    awarded = {r["id"]: r for r in results}
    again = {r["id"]: r for r in second or []}
    errors, agreed, flags, mismatched, consistent = [], [], [], [], {}
    for r in responses:
        a = awarded.get(r["id"])
        if not a:
            errors.append(f"response {r['id']}: not marked")
            continue
        want, got = _norm(r["designed"]), _norm(a["awarded"])
        tag = f"response {r['id']} ({r['kind']}{' ' + r['error_code'] if r.get('error_code') else ''})"
        if want == got:
            agreed.append(r["id"])
            continue
        diff = {k: (want.get(k), got.get(k)) for k in set(want) | set(got) if want.get(k) != got.get(k)}
        b2 = again.get(r["id"])
        if b2 is None:
            mismatched.append(r["id"])
            errors.append(f"{tag}: designed vs awarded {diff}; marker: {'; '.join(a.get('reasons') or [])[:300]}")
            continue
        got2 = _norm(b2["awarded"])
        if got2 == got:
            consistent[r["id"]] = a["awarded"]
            flags.append(f"{tag}: both markers award {got}, not the designed {want} (script design off; scheme consistent)")
        elif got2 == want:
            agreed.append(r["id"])
            flags.append(f"{tag}: second marker agrees with the design; first marker gave {got}")
        else:
            errors.append(f"{tag}: markers disagree ({got} vs {got2}; designed {want}): the mark scheme is ambiguous here")
    # the designed vectors must follow the scheme (same codes in order, main scheme or an alternative) and the
    # correct / alternative responses must score full marks: otherwise agreement proves nothing
    schemes = {norm_label(p.get("label")): [[_mark(m["code"]) for m in p["mark_scheme"]]]
               + [[_mark(m["code"]) for m in alt.get("marks", [])] for alt in p.get("alternatives") or []]
               for p in item["parts"]}
    for r in responses:
        for part, marks in _norm(r["designed"]).items():
            ok_shapes = schemes.get(part)
            if ok_shapes is None:
                errors.append(f"response {r['id']}: designed marks for unknown part {part}")
                continue
            if not any(len(marks) == len(sh) and all(m[:-1] == c[:-1] and m[-1] in ("0", c[-1]) for m, c in zip(marks, sh))
                       for sh in ok_shapes):
                errors.append(f"response {r['id']}: designed marks {marks} for part {part} don't follow the scheme {ok_shapes[0]}")
            elif r["kind"] in ("correct", "alternative") and any(m.endswith("0") for m in marks):
                errors.append(f"response {r['id']} ({r['kind']}): designed to lose marks in part {part}")
    kinds = {r["kind"] for r in responses}
    if "correct" not in kinds:
        errors.append("no fully correct response was written")
    return {"pass": not errors, "errors": errors, "flags": flags, "flag": bool(flags), "n_responses": len(responses),
            "agreed": agreed, "consistent": consistent, "mismatched": mismatched, "model": MODEL,
            "responses": responses, "awarded": results, "awarded_second": second or []}


def g5_pitfalls(item: dict, g4: dict, blueprint: dict | None) -> dict:
    errors = []
    allowed = {e["code"] for p in (blueprint or {}).get("parts", []) for e in p.get("error_codes", [])}
    frequency = {e["code"]: max(e.get("n_notes", 0), 0) for p in (blueprint or {}).get("parts", [])
                 for e in p.get("error_codes", [])}
    text = " ".join([item.get("stem") or ""] + [p["text"] for p in item["parts"]])
    by_code = {}
    for r in g4.get("responses", []):
        if r.get("kind") == "pitfall" and r.get("error_code"):
            by_code[r["error_code"]] = r
    for pf in item.get("pitfalls") or []:
        w = f"pitfall [{pf.get('error_code')}] part {pf.get('part') or '-'}"
        part = next((p for p in item["parts"] if norm_label(p.get("label")) == norm_label(pf.get("part"))), None)
        if part is None:
            errors.append(f"{w}: no such part")
            continue
        steps = {s.get("step") for s in part.get("solution") or []}
        if pf.get("step") is not None and pf["step"] not in steps:
            errors.append(f"{w}: step {pf['step']} is not a solution step")
        if allowed and pf.get("error_code") not in allowed:
            errors.append(f"{w}: error code not one of the blueprint's")
        nums = lambda t: set(re.findall(r"\d+(?:\.\d+)?", latex_to_plain(t or "")))
        own = nums(text) | nums(" ".join(s["working"] for s in part.get("solution") or []))
        if part.get("command") in WORDED_COMMANDS:  # explain / state ...: it must refer to this question's context
            context = {x.lower() for x in re.findall(r"[A-Za-z]{5,}", text)}
            if not {x.lower() for x in re.findall(r"[A-Za-z]{5,}", pf["text"])} & context:
                errors.append(f"{w}: doesn't refer to this question's context")
        elif own and not nums(pf["text"]) & own:  # otherwise it must use this question's own numbers
            errors.append(f"{w}: doesn't use the question's own numbers")
        if re.search(r"\bcommon(ly)?\b|\bmany students\b|\boften\b", pf["text"], re.I) and not pf.get("says_common"):
            errors.append(f"{w}: says it's common without the frequency flag")
        if pf.get("says_common") and frequency.get(pf.get("error_code"), 0) < FREQUENT_NOTES:
            errors.append(f"{w}: flagged as common, but its error code has {frequency.get(pf.get('error_code'), 0)} "
                          f"matched notes (needs {FREQUENT_NOTES})")
        r = by_code.get(pf.get("error_code"))
        if r is None:
            errors.append(f"{w}: no G4 response demonstrates it")
        elif r["id"] in g4.get("consistent", {}):  # both markers agree on what it earns: use their vector
            if not any(_mark(m).endswith("0") for v in g4["consistent"][r["id"]] for m in v["marks"]):
                errors.append(f"{w}: its G4 response loses no marks (both markers)")
        else:
            if not any(_mark(m).endswith("0") for v in r["designed"] for m in v["marks"]):
                errors.append(f"{w}: its G4 response loses no marks")
            if r["id"] not in g4.get("agreed", []):
                errors.append(f"{w}: the marker didn't score its response as designed")
    return {"pass": not errors, "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    bps = {}
    for f in ("exam.jsonl", "drills.jsonl", "mocks.jsonl"):
        for line in (ROOT / "content" / "blueprints" / f).read_text().splitlines():
            if line.strip():
                bp = json.loads(line)
                bps[bp["id"]] = bp
    total = 0.0
    for f in map(Path, args.items):
        item = json.loads(f.read_text())
        g4 = g4_marking(item)
        g5 = g5_pitfalls(item, g4, bps.get(item.get("blueprint_id")))
        total += g4["cost_usd"]
        print(f"{item['id']}: G4 {'PASS' if g4['pass'] else 'FAIL'} ({len(g4['agreed'])}/{g4['n_responses']} scripts as designed)"
              f"  G5 {'PASS' if g5['pass'] else 'FAIL'}  ${g4['cost_usd']:.3f}")
        for e in (g4["errors"] + g5["errors"])[:6]:
            print("    ", e[:220])
        if not args.dry:
            item.setdefault("gate_results", {}).update({"G4": g4, "G5": g5})
            f.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
    print(f"total ${total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
