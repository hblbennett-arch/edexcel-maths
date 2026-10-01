#!/usr/bin/env python3
"""Re-run the scene structural checks over content/clean/scenes/*.json (no model calls) and print a summary.

    .venv/bin/python eval/scenes_check.py [--verbose]

Prints: items, applicable count by approach, scenes, element type counts, sliders and gliders per scene, pass/fail
per check family, total cost from the scene files and from logs/llm_calls.jsonl (step names "scene*"), then guide
coverage (scenes with a guide, legend and interact entries against what the gate demands) and the guide gate
results (scripts/clean/gate_scene.py with require_guide, G7 included; cost from the log, step names "guide*").
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import make_scenes as ms  # noqa: E402
from gate_scene import gate_scene, guide_requirements  # noqa: E402

FAMILIES = [
    ("expressions", re.compile(r"implicit multiplication|does not parse|not a plain maths|unknown symbol|unknown identifier|free symbol|takes \d+ argument|commas are only allowed|character not allowed|unbalanced|missing or empty expression|expected \[|not numeric|not finite|cannot evaluate")),
    ("ids", re.compile(r"unknown element id|unknown id|not unique|is a \w+, need one of|must be an identifier|duplicate scene id|scene id .* must start")),
    ("types_colours", re.compile(r"not in the table|is not a token|approach must be")),
    ("board_params", re.compile(r"board\.|param .*: need|param id|step too small|must all be numbers|never used|is outside")),
    ("steps", re.compile(r"steps; need 2 to 5|text missing or too short|is not a param id|\.set:")),
    ("interactivity", re.compile(r"no interactive affordance")),
    ("links", re.compile(r"links\.")),
    ("text", re.compile(r"mentions|KaTeX")),
    ("applicability", re.compile(r"applicable|reason is required|at most 2|part .* is not a part")),
]


def family(err: str) -> str:
    for name, rx in FAMILIES:
        if rx.search(err):
            return name
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    files = sorted(ms.SCENES.glob("*.json"))
    items_by_id = {}
    for p in ms.ITEMS.glob("*.json"):
        d = json.loads(p.read_text())
        items_by_id[d["id"]] = d
    n_app, approaches, scenes, el_types = 0, Counter(), 0, Counter()
    per_scene, fam_fail, fam_pass = [], Counter(), Counter()
    cost_files, attempts, models, not_app = 0.0, Counter(), Counter(), []
    failing = {}
    for f in files:
        rec = json.loads(f.read_text())
        item = items_by_id.get(rec["item_id"])
        cost_files += rec.get("cost_usd") or 0
        attempts[rec.get("attempts")] += 1
        models[rec.get("model")] += 1
        if item is None:
            failing[rec["item_id"]] = ["item file missing"]
            continue
        chk = ms.check_output({"applicable": rec.get("applicable"), "reason": rec.get("reason"), "scenes": rec.get("scenes")}, item)
        fams = {family(e) for e in chk["errors"]}
        for name, _ in FAMILIES:
            (fam_fail if name in fams else fam_pass)[name] += 1
        if chk["errors"]:
            failing[rec["item_id"]] = chk["errors"]
        if rec.get("applicable"):
            n_app += 1
        else:
            not_app.append((rec["item_id"], rec.get("reason", "")))
        for sc in rec.get("scenes") or []:
            scenes += 1
            approaches[sc.get("approach")] += 1
            types = Counter(el.get("type") for el in sc.get("elements") or [])
            el_types.update(types)
            per_scene.append((sc.get("id"), len(sc.get("params") or []), types.get("glider", 0),
                              len(sc.get("steps") or [])))
    log_cost, log_calls = 0.0, 0
    if ms.LOG.exists():
        for line in ms.LOG.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if str(r.get("step", "")).startswith("scene"):
                log_calls += 1
                log_cost += r.get("cost_usd") or 0
    print(f"scene files: {len(files)}   applicable: {n_app}   not applicable: {len(not_app)}   scenes: {scenes}")
    print("approach:", dict(approaches))
    print("element types:", dict(el_types.most_common()))
    print("sliders / gliders / steps per scene:")
    for sid, np_, ng, ns in per_scene:
        print(f"  {sid}: {np_} slider(s), {ng} glider(s), {ns} steps")
    print("checks (files passing / failing per family):")
    for name, _ in FAMILIES:
        print(f"  {name:14s} pass {fam_pass[name]:3d}  fail {fam_fail[name]:3d}")
    print(f"files passing all checks: {len(files) - len(failing)} / {len(files)}")
    print(f"attempts: {dict(sorted(attempts.items(), key=lambda kv: str(kv[0])))}   models: {dict(models)}")
    print(f"cost: ${cost_files:.2f} from files; ${log_cost:.2f} from the log ({log_calls} scene calls)")
    if not_app:
        print("not applicable:")
        for i, r in not_app:
            print(f"  {i}: {r}")
    if failing:
        print("failing:")
        for i, errs in failing.items():
            print(f"  {i}:")
            for e in errs if a.verbose else errs[:5]:
                print(f"    {e}")
    guide_failing = guide_report(files, items_by_id, a.verbose)
    return 1 if (failing or guide_failing) else 0


def guide_report(files, items_by_id, verbose: bool) -> dict:
    """Guide coverage and the guide gate (gate_scene with require_guide=True) per scene."""
    n_scenes = with_guide = 0
    legend_have = legend_need = interact_have = interact_need = readoff_have = readoff_need = 0
    gate_pass, failing, attempts, cost = 0, {}, Counter(), 0.0
    err_fams = Counter()
    for f in files:
        rec = json.loads(f.read_text())
        item = items_by_id.get(rec["item_id"])
        for sc in rec.get("scenes") or []:
            n_scenes += 1
            req = guide_requirements(sc)
            legend_need += len(req["legend_ids"])
            interact_need += len(req["controls"])
            readoff_need += len(req["live_texts"])
            g = sc.get("guide")
            if g:
                with_guide += 1
                legend_have += len(g.get("legend") or [])
                interact_have += len(g.get("interact") or [])
                readoff_have += len(g.get("read_off") or [])
            meta = sc.get("guide_meta") or {}
            attempts[meta.get("attempts")] += 1
            cost += meta.get("cost_usd") or 0
            r = gate_scene(sc, item, require_guide=True)
            if r["pass"]:
                gate_pass += 1
            else:
                failing[sc.get("id")] = r["errors"]
                for e in r["errors"]:
                    err_fams[e.split(":")[0] if e.startswith("guide") else "scene"] += 1
    log_cost, log_calls = 0.0, 0
    if ms.LOG.exists():
        for line in ms.LOG.open():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if str(r.get("step", "")).startswith("guide"):
                log_calls += 1
                log_cost += r.get("cost_usd") or 0
    print()
    print(f"guide coverage: {with_guide} / {n_scenes} scenes have a guide")
    print(f"  legend entries   {legend_have:3d}  (gate requires {legend_need}: labelled/integral/glider/draggable/tangent/normal/vector elements)")
    print(f"  interact entries {interact_have:3d}  (gate requires {interact_need}: sliders, gliders, draggable points)")
    print(f"  read_off lines   {readoff_have:3d}  (gate requires {readoff_need}: live text labels)")
    print(f"guide gate (gate_scene --require-guide, G7 on): {gate_pass} / {n_scenes} scenes pass")
    print(f"  attempts: {dict(sorted(attempts.items(), key=lambda kv: str(kv[0])))}   "
          f"cost: ${cost:.2f} from guide_meta; ${log_cost:.2f} from the log ({log_calls} guide calls)")
    if err_fams:
        print("  errors by field:", dict(err_fams.most_common()))
    if failing:
        print("guide gate failing:")
        for sid, errs in failing.items():
            print(f"  {sid}:")
            for e in errs if verbose else errs[:5]:
                print(f"    {e}")
    return failing


if __name__ == "__main__":
    sys.exit(main())
