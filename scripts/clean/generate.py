#!/usr/bin/env python3
"""Generate clean items from blueprints: one `claude -p` call per blueprint on the Claude Code login.

    .venv/bin/python scripts/clean/generate.py --select pilot --dry        # show the selection and one prompt
    .venv/bin/python scripts/clean/generate.py --select pilot --limit 3    # smoke test: 3 items
    .venv/bin/python scripts/clean/generate.py --ids bp-pure-...-001 dr-chain-rule-core
    .venv/bin/python scripts/clean/generate.py --select pilot --parallel 5

The model sees only our own material: the blueprint (ids and codes from the fact layer, rendered with
our skill titles and descriptions), our error-code definitions and our house-style prompt
(content/prompts/). **No Pearson text goes into any prompt.** Each item is written to
content/clean/items/<id>.json with its provenance. The deterministic gates (scripts/clean/gates.py) then
run; an item that fails is regenerated once, with the gate errors as feedback (G7 feedback never
names the source question). Costs come from `claude -p` and are logged to logs/llm_calls.jsonl.
"""
import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_oneshot  # noqa: E402
import gates  # noqa: E402

MODEL = "claude-opus-5-5"
BLUEPRINTS = ROOT / "content" / "blueprints"
ITEMS = ROOT / "content" / "clean" / "items"
PROMPTS = ROOT / "content" / "prompts"
from gate_marking import FREQUENT_NOTES  # noqa: E402  (one threshold for the prompt and for G5)
PILOT_GROUPS = {
    "pure": {"basic-differentiation", "chain-product-quotient-rules", "implicit-and-parametric-differentiation",
             "tangents-and-normals", "stationary-points", "optimisation", "basic-integration", "areas-by-integration",
             "integration-techniques", "differential-equations"},
    "stats": {"binomial-distribution", "hypothesis-testing"},
}
PILOT_SIZE = {"pure": 28, "stats": 12, "drills": 20}

STR = {"type": "string"}
MARK = {"type": "object", "properties": {"code": STR, "for": STR, "notes": STR, "depends_on": STR, "ft_of": STR},
        "required": ["code", "for"]}
ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "stem": {"type": ["string", "null"], "description": "shared information before the parts, or null"},
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": ["string", "null"]}, "marks": {"type": "integer"},
            "text": {"type": "string", "description": "the part, ending with its marks in brackets, e.g. (3)"},
            "command": STR, "forms": {"type": "array", "items": STR}, "skills": {"type": "array", "items": STR},
            "mark_scheme": {"type": "array", "items": MARK},
            "alternatives": {"type": "array", "items": {"type": "object", "properties": {
                "name": STR, "marks": {"type": "array", "items": MARK}}, "required": ["name", "marks"]}},
            "solution": {"type": "array", "items": {"type": "object", "properties": {
                "step": {"type": "integer"}, "working": STR, "mark": STR}, "required": ["step", "working"]}},
            "answers": {"type": "array", "items": {"type": "object", "properties": {
                "name": STR, "expr": STR, "form": STR}, "required": ["name", "expr"]}},
            "checks": {"type": "array", "items": STR, "description": "each a JSON object encoded as a string"},
            "hints": {"type": "array", "items": STR}},
            "required": ["label", "marks", "text", "command", "mark_scheme", "solution", "answers", "checks", "hints"]}},
        "pitfalls": {"type": "array", "items": {"type": "object", "properties": {
            "part": {"type": ["string", "null"]}, "step": {"type": "integer"}, "error_code": STR, "text": STR,
            "says_common": {"type": "boolean"}}, "required": ["part", "error_code", "text", "says_common"]}},
    },
    "required": ["stem", "parts", "pitfalls"],
}


def load_blueprints() -> dict[str, dict]:
    out = {}
    for f in ("exam.jsonl", "drills.jsonl", "mocks.jsonl"):
        for line in (BLUEPRINTS / f).read_text().splitlines():
            if line.strip():
                bp = json.loads(line)
                out[bp["id"]] = bp
    return out


def select_pilot(bps: dict[str, dict]) -> list[str]:
    """~40 exam-style blueprints around calculus (pure) and binomial / hypothesis testing (stats), in each
    component's 9MA0 band mix, plus ~20 drills on those skills. Deterministic."""
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    group = {s["id"]: s["group"] for s in tags["skills"]}
    agg = json.loads((ROOT / "content" / "facts" / "aggregates.json").read_text())["mix_9ma0"]
    chosen = []
    for comp, groups in PILOT_GROUPS.items():
        pool = [b for b in bps.values() if b["kind"] == "exam" and b["component"] == comp
                and groups & {group[s] for p in b["parts"] for s in p["skills"]}]
        n_comp = sum(v["questions"] for v in agg[comp].values())
        for band, v in agg[comp].items():
            want = round(PILOT_SIZE[comp] * v["questions"] / n_comp)
            picks = sorted((b for b in pool if b["band"] == band), key=lambda b: b["id"])
            seen_types: Counter = Counter()
            for b in picks:  # spread across question types: at most 2 of each per band
                if sum(1 for c in chosen if bps[c]["component"] == comp and bps[c]["band"] == band) >= want:
                    break
                if seen_types[b["question_type"]] < 2:
                    seen_types[b["question_type"]] += 1
                    chosen.append(b["id"])
        # top up from any band if a band had too few blueprints on these skills
        extra = sorted((b for b in pool if b["id"] not in chosen), key=lambda b: b["id"])
        while sum(1 for c in chosen if bps[c]["component"] == comp) < PILOT_SIZE[comp] and extra:
            chosen.append(extra.pop(0)["id"])
    drill_groups = set().union(*PILOT_GROUPS.values())
    drills = sorted(b["id"] for b in bps.values() if b["kind"] == "drill"
                    and group[b["parts"][0]["skills"][0]] in drill_groups)
    step = max(1, len(drills) // PILOT_SIZE["drills"])
    chosen += drills[::step][:PILOT_SIZE["drills"]]
    return chosen


def render(bp: dict, tags: dict, codes: dict, checks_language: str) -> str:
    skills = {s["id"]: s for s in tags["skills"]}
    qtypes = {t["id"]: t for t in tags["question_types"]}
    qt = qtypes[bp["question_type"]]
    lines = ["# Blueprint", "",
             f"- Question type: {qt['title']}: {qt.get('definition') or ''}",
             f"- Component: {bp['component']} | total marks: {bp['total_marks']} | difficulty: {bp['difficulty']}",
             f"- Context theme: {bp['context_theme']}" + (" (no real-world context needed)" if bp["context_theme"] == "none" else
                                                          " (invent an original scenario in this theme)"),
             f"- Calculator: allowed" + ("; one or more parts must say that a calculator answer alone won't earn the marks"
                                          if bp.get("no_calc_tech") else ""),
             f"- Kind: {'a short single-skill practice question' if bp['kind'] == 'drill' else 'an exam-style question'}",
             "", "## Parts"]
    for p in bp["parts"]:
        lines += ["", f"### Part {p['label'] or '(single part, label null)'}: {p['marks']} marks",
                  f"- Command word: {p['command']}" + (f"; answer form: {', '.join(p['forms'])}" if p["forms"] else ""),
                  f"- Target mark codes: {p['codes']}",
                  "- Skills (use these ids in `skills`):"]
        lines += [f"  - `{s}`: {skills[s]['title']}. {skills[s].get('description') or ''}" for s in p["skills"]]
        if p.get("error_codes"):
            lines.append("- Error codes to write pitfalls for:")
            for e in p["error_codes"]:
                c = codes[e["code"]]
                lines.append(f"  - `{e['code']}` (usually loses {e['loses']}; frequent: "
                             f"{'yes' if e.get('n_notes', 0) >= FREQUENT_NOTES else 'no'}): {c['definition']}")
    lines += ["", "# Checks language (for `checks`)", "", checks_language]
    return "\n".join(lines)


def _decode_check(c):
    """A check string -> dict, keeping decimals as strings; a malformed one stays a string for G2 to report."""
    if not isinstance(c, str):
        return c
    try:
        return json.loads(c, parse_float=str)
    except json.JSONDecodeError:
        return c


def to_item(bp: dict, out: dict, meta: dict) -> dict:
    parts = out["parts"]
    if len(parts) == len(bp["parts"]):  # same shape: take the blueprint's labels and keep skills to its list
        for p, bpp in zip(parts, bp["parts"]):
            p["label"] = bpp["label"]
            p.setdefault("forms", bpp["forms"])
            p["skills"] = [s for s in p.get("skills") or [] if s in bpp["skills"]] or bpp["skills"]
    else:  # keep what the model wrote; blueprint_conformance() fails it
        allowed = {s for bpp in bp["parts"] for s in bpp["skills"]}
        for p in parts:
            p["skills"] = [s for s in p.get("skills") or [] if s in allowed] or sorted(allowed)[:1]
    import gate_marking
    labels = {gate_marking.norm_label(p["label"]): p["label"] for p in parts}
    for pf in out.get("pitfalls") or []:  # "(a)" -> "a": pitfalls point at the part's own label
        pf["part"] = labels.get(gate_marking.norm_label(pf.get("part")), pf.get("part"))
    return {"id": "cr-" + bp["id"][3:], "blueprint_id": bp["id"], "question_type": bp["question_type"],
            "component": bp["component"], "tier": bp["difficulty"], "kind": bp["kind"], "stem": out.get("stem"),
            "parts": parts, "pitfalls": out.get("pitfalls") or [], "provenance": "original",
            "generator_model": MODEL, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "generation": meta, "gate_results": {}, "review": {"by": None, "at": None, "decision": None, "notes": None}}


def feedback(results: dict) -> str:
    lines = ["Your previous attempt failed these automatic checks. Write a new version that fixes them:"]
    for g, r in results.items():
        if not r.get("pass"):
            if g == "G7":
                where = ", ".join(r.get("hit_fields") or []) or "the question"
                lines.append("- G7 originality: wording in these fields matches published exam material: " + where +
                             ". Rewrite those fields in fresh wording of your own (don't reuse stock phrases from "
                             "published mark schemes). If it's the whole question, also change the scenario, "
                             "functions and numbers.")
            else:
                lines += [f"- {g}: {e}" for e in (r.get("errors") or [])[:8]]
    return "\n".join(lines)


def blueprint_conformance(item: dict, bp: dict) -> list[str]:
    """The item must have the blueprint's shape: same parts, marks per part and command word."""
    if not bp:
        return ["no blueprint"]
    if len(item["parts"]) != len(bp["parts"]):
        return [f"has {len(item['parts'])} part(s), the blueprint has {len(bp['parts'])}"]
    errs = []
    for p, bpp in zip(item["parts"], bp["parts"]):
        if p.get("marks") != bpp["marks"]:
            errs.append(f"part {bpp['label'] or '-'}: {p.get('marks')} marks, the blueprint has {bpp['marks']}")
        if p.get("command") != bpp["command"]:
            errs.append(f"part {bpp['label'] or '-'}: command {p.get('command')!r}, the blueprint has {bpp['command']!r}")
    return errs


def run_gates(item: dict, bp: dict | None = None) -> dict:
    res = gates.run(item)
    if bp is not None:  # shape against the blueprint belongs with structure (G1)
        conf = blueprint_conformance(item, bp)
        res["G1"]["errors"] += conf
        res["G1"]["pass"] = res["G1"]["pass"] and not conf
    for mod, fn in (("gate_maths", "g2_maths"), ("gate_style", "g8_style")):
        try:
            m = __import__(mod)
            res[{"g2_maths": "G2", "g8_style": "G8"}[fn]] = getattr(m, fn)(item)
        except ImportError:
            pass
    return res


def model_gates(item: dict, bp: dict, tags: dict, skill_lists: dict) -> None:
    """G3 blind solve, G4 mark-scheme tests + G5 pitfalls, G6 tags (model calls; only after G1/G2/G7/G8 pass).
    Stops at the first failing gate, so a failed item doesn't spend on the later ones."""
    import gate_marking
    import gate_solve
    import gate_tags
    res = item["gate_results"]
    res["G3"] = gate_solve.g3_blind_solve(item)
    if not res["G3"]["pass"]:
        return
    res["G4"] = gate_marking.g4_marking(item)
    res["G5"] = gate_marking.g5_pitfalls(item, res["G4"], bp)
    if not res["G4"]["pass"]:
        return
    res["G6"] = gate_tags.g6_tags(item, tags, skill_lists[item["component"]])


def generate_one(bp: dict, system: str, tags: dict, codes: dict, checks_language: str, retries: int = 1,
                 full: bool = False, skill_lists: dict | None = None) -> dict:
    user = render(bp, tags, codes, checks_language)
    cost, attempts, results = 0.0, 0, {}
    msg = user
    for attempts in range(1, retries + 2):
        out = claude_oneshot.run(system, [claude_oneshot.text_block(msg)], schema=ITEM_SCHEMA, model=MODEL,
                                 max_usd=1.5, thinking_tokens=8000, step="clean-generate", ref=bp["id"], timeout=1200)
        cost += out["cost_usd"] or 0
        res = out["result"]
        for p in res.get("parts", []):  # checks arrive as JSON strings (decimals kept as written: "0.30")
            p["checks"] = [_decode_check(c) for c in p.get("checks") or []]
        item = to_item(bp, res, {"attempts": attempts, "cost_usd": round(cost, 4)})
        results = run_gates(item, bp)
        item["gate_results"] = results
        if all(r.get("pass") for r in results.values()):
            break
        msg = user + "\n\n" + feedback(results)
    item["generation"] = {"attempts": attempts, "cost_usd": round(cost, 4)}
    if full and all(r.get("pass") for r in results.values()):
        model_gates(item, bp, tags, skill_lists)
    ITEMS.mkdir(parents=True, exist_ok=True)
    (ITEMS / f"{item['id']}.json").write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
    return item


def regate(bps: dict) -> int:
    """Items edited in review (review.regate_needed): run G1-G8 again; clear the flag only if all pass."""
    import gate_tags
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    facts = json.loads((ROOT / "content" / "facts" / "parts.json").read_text())["parts"]
    lists = {c: gate_tags.skill_list(c, tags, facts) for c in ("pure", "stats", "mech")}
    for f in sorted(ITEMS.glob("*.json")):
        item = json.loads(f.read_text())
        if not (item.get("review") or {}).get("regate_needed"):
            continue
        item["gate_results"] = run_gates(item, bps.get(item["blueprint_id"]))
        if all(r.get("pass") for r in item["gate_results"].values()):
            model_gates(item, bps.get(item["blueprint_id"], {}), tags, lists)
        ok = all(item["gate_results"].get(g, {}).get("pass") for g in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"))
        item["review"]["regate_needed"] = not ok
        f.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
        print(f"  {item['id']}: {'PASS' if ok else 'FAIL'} after edit")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", choices=["pilot"])
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--full", action="store_true", help="also run the model gates G3-G6 on items that pass G1/G2/G7/G8")
    ap.add_argument("--regate", action="store_true", help="re-run every gate on items edited in the review UI")
    args = ap.parse_args()
    bps = load_blueprints()
    if args.regate:
        return regate(bps)
    ids = args.ids or (select_pilot(bps) if args.select == "pilot" else [])
    if args.skip_existing:
        ids = [i for i in ids if not (ITEMS / f"cr-{i[3:]}.json").exists()]
    ids = ids[:args.limit] if args.limit else ids
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    codes = {c["id"]: c for c in json.loads((ROOT / "content" / "error_codes.json").read_text())["codes"]}
    system = (PROMPTS / "generate_system.md").read_text()
    checks_path = PROMPTS / "checks_language.md"
    checks_language = checks_path.read_text() if checks_path.exists() else "(none yet: give `checks: []`)"
    mix = Counter((bps[i]["component"], bps[i]["kind"], bps[i]["band"]) for i in ids)
    print(f"{len(ids)} blueprint(s): " + ", ".join(f"{c}/{k}/{b} {n}" for (c, k, b), n in sorted(mix.items())))
    if args.dry:
        print("\n" + render(bps[ids[0]], tags, codes, checks_language))
        return 0
    import gate_tags
    facts = json.loads((ROOT / "content" / "facts" / "parts.json").read_text())["parts"]
    skill_lists = {c: gate_tags.skill_list(c, tags, facts) for c in ("pure", "stats", "mech")}
    t0, spent, passed = time.time(), 0.0, 0
    with ThreadPoolExecutor(max_workers=min(5, args.parallel)) as ex:
        futures = {ex.submit(generate_one, bps[i], system, tags, codes, checks_language, 1, args.full, skill_lists): i
                   for i in ids}
        for fut in futures:
            i = futures[fut]
            try:
                item = fut.result()
            except Exception as e:  # noqa: BLE001 - report and carry on with the batch
                print(f"  {i}: ERROR {str(e)[:200]}")
                continue
            ok = all(r.get("pass") for r in item["gate_results"].values())
            passed += ok
            spent += item["generation"]["cost_usd"] + sum((item["gate_results"].get(g) or {}).get("cost_usd") or 0
                                                          for g in ("G3", "G4", "G6"))
            print(f"  {item['id']}: {'PASS' if ok else 'FAIL'} "
                  + " ".join(f"{g}{'+' if r.get('pass') else '-'}" for g, r in item["gate_results"].items())
                  + f"  attempts {item['generation']['attempts']}  ${item['generation']['cost_usd']:.3f}")
    print(f"done: {passed}/{len(ids)} passed every gate run | ${spent:.2f} | {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
