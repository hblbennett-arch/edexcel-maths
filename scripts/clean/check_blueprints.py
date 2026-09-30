#!/usr/bin/env python3
"""Check blueprints and report how closely the set matches 9MA0 (bank-level G8). Deterministic.

    .venv/bin/python scripts/clean/check_blueprints.py [content/blueprints/*.jsonl]

Per blueprint (fails the run):
  - ids exist: question type, skills, error codes; component and band are known values;
  - every part has a maths skill, positive marks, and a mark-code pattern that adds up to its marks with
    A and dM marks after an M (A1* only in show-that parts); total_marks is the sum of the parts;
  - at least 3 source question ids (facts), all real ids;
  - no free text: every string is an id, a code, a number or one of our theme names (check_facts.ok).
Bank level (reported; the exam set fails if the mix is off): per component, the total variation
distance (TVD) from the 9MA0 distributions of the topic-mix band, marks per question and parts per
question. Target TVD < 0.15.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_facts  # noqa: E402
from build_facts import MIX_BANDS  # noqa: E402
from make_blueprints import THEMES, value, well_formed  # noqa: E402

FACTS = ROOT / "content" / "facts"
TVD_MAX = 0.15
LABEL = re.compile(r"^[a-z](\((i|ii|iii|iv|v|vi)\))?$|^(i|ii|iii|iv|v|vi)$")
EXTRA_VOCAB = {"exam", "drill", "none", "accessible", "standard", "challenging", "starter", "core", "stretch",
               "same-type-same-shape", "shared-skills", "same-type-same-shape+union", "shared-skills+union",
               "skill-parts", "M", "A", "B", "median", "max", "min", "skill-mode", "mock", "q_num", "P1", "P2", "P3", "marks_rule", "id", "kind", "total_marks", "band", "context_theme", "no_calc_tech",
               "source_fact_ids", "source_rule", "label", "command", "error_codes", "code", "loses", "n_notes"} \
    | {t for ts in THEMES.values() for t in ts} | set(MIX_BANDS)


def tvd(a: Counter, b: Counter) -> float:
    na, nb = sum(a.values()) or 1, sum(b.values()) or 1
    return 0.5 * sum(abs(a[k] / na - b[k] / nb) for k in set(a) | set(b))


def check_one(bp: dict, vocab: set, qids: set, types: set, skills: set, errors: set, group: dict) -> list[str]:
    e = []
    if bp.get("question_type") not in types:
        e.append(f"unknown question type {bp.get('question_type')}")
    if bp.get("component") not in ("pure", "stats", "mech"):
        e.append("bad component")
    if bp.get("band") not in MIX_BANDS:
        e.append("bad band")
    parts = bp.get("parts") or []
    if not parts:
        e.append("no parts")
    for p in parts:
        w = f"part {p.get('label') or '-'}"
        bad = [s for s in p.get("skills", []) if s not in skills]
        if bad:
            e.append(f"{w}: unknown skills {bad}")
        if not p.get("skills") or all(group.get(s) == "exam-technique" for s in p["skills"]):
            e.append(f"{w}: no maths skill")
        codes = (p.get("codes") or "").split()
        if not isinstance(p.get("marks"), int) or p["marks"] < 1:
            e.append(f"{w}: bad marks")
        elif sum(map(value, codes)) != p["marks"]:
            e.append(f"{w}: codes {p.get('codes')!r} don't add up to {p['marks']}")
        if not well_formed(codes):
            e.append(f"{w}: codes {p.get('codes')!r} not well formed")
        if any(c.endswith("*") for c in codes) and p.get("command") != "show-that":
            e.append(f"{w}: A1* outside a show-that part")
        bad = [x["code"] for x in p.get("error_codes", []) if x["code"] not in errors]
        if bad:
            e.append(f"{w}: unknown error codes {bad}")
    if bp.get("total_marks") != sum(p.get("marks", 0) for p in parts):
        e.append("total_marks is not the sum of the parts")
    srcs = bp.get("source_fact_ids") or []
    if len(srcs) < 3 or any(q not in qids for q in srcs):
        e.append(f"needs >= 3 real source ids, has {srcs}")

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(k)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and not (check_facts.ok(o, vocab) or o.startswith(("bp-", "dr-", "mk-", "mock-"))
                                         or LABEL.match(o)):
            e.append(f"free text not allowed: {o[:50]!r}")
    walk(bp)
    return e


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "blueprints").glob("*.jsonl"))
    vocab = check_facts.vocabulary() | EXTRA_VOCAB
    parts = json.loads((FACTS / "parts.json").read_text())["parts"]
    agg = json.loads((FACTS / "aggregates.json").read_text())
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    types = {t["id"] for t in tags["question_types"]}
    skills = {s["id"] for s in tags["skills"]}
    group = {s["id"]: s["group"] for s in tags["skills"]}
    errors = {c["id"] for c in json.loads((ROOT / "content" / "error_codes.json").read_text())["codes"]}
    qids = {p["question"] for p in parts}
    real = {}
    for p in parts:
        if p["qualification"] == "9MA0":
            real.setdefault(p["question"], {"component": p["component"], "marks": 0, "n": 0})
            real[p["question"]]["marks"] += p["marks"]
            real[p["question"]]["n"] += 1
    failed = False
    for f in files:
        bps = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        bad = {bp.get("id"): check_one(bp, vocab, qids, types, skills, errors, group) for bp in bps}
        bad = {k: v for k, v in bad.items() if v}
        ids = [bp.get("id") for bp in bps]
        dup = [i for i, n in Counter(ids).items() if n > 1]
        print(f"{f.name}: {len(bps)} blueprints, {len(bad)} with problems" + (f", duplicate ids {dup[:3]}" if dup else ""))
        for k, v in list(bad.items())[:10]:
            print(f"    {k}: {v[:3]}")
        failed |= bool(bad) or bool(dup)
        if bps and bps[0].get("kind") == "exam":
            print("    component  n    TVD(topic mix)  TVD(marks/q)  TVD(parts/q)")
            for comp in ("pure", "stats", "mech"):
                mine = [bp for bp in bps if bp["component"] == comp]
                ref = [r for r in real.values() if r["component"] == comp]
                t_mix = tvd(Counter(bp["band"] for bp in mine),
                            Counter({b: v["questions"] for b, v in agg["mix_9ma0"][comp].items()}))
                # marks in bands of 3 (3-5, 6-8, ...): the bank is too small for single-mark bins
                t_marks = tvd(Counter(bp["total_marks"] // 3 for bp in mine), Counter(r["marks"] // 3 for r in ref))
                t_parts = tvd(Counter(min(len(bp["parts"]), 5) for bp in mine), Counter(min(r["n"], 5) for r in ref))
                ok = max(t_mix, t_marks, t_parts) < TVD_MAX
                failed |= not ok
                print(f"    {comp:9s} {len(mine):4d}  {t_mix:10.3f}  {t_marks:12.3f}  {t_parts:12.3f}   {'OK' if ok else 'OFF'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
