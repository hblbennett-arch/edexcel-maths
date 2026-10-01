#!/usr/bin/env python3
"""Solution levels report (docs/learn-layer-spec.md §1). No model calls.

    .venv/bin/python eval/levels_check.py [--no-novelty] [ITEM.json ...]

Runs gate_levels over every clean item that has solution_levels (default: content/clean/items/*.json) and
prints: items and parts with levels, pass / fail per check, average lines per level against the standard
solution, and the total cost (from levels_meta in the files, and from logs/llm_calls.jsonl steps levels*).
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import gate_levels  # noqa: E402

ITEMS = sorted((ROOT / "content" / "clean" / "items").glob("*.json"))
LOG = ROOT / "logs" / "llm_calls.jsonl"
CHECKS = [("katex", r"KaTeX error|unbalanced \$|LaTeX outside|not \\\\\(|use \$\.\.\.\$"),
          ("copy (G7)", r"copy check"),
          ("codes", r"secures|scheme codes"),
          ("answers", r"last working|no maths expression"),
          ("why", r"empty why"),
          ("length", r"fewer than the standard"),
          ("banned", r"banned word"),
          ("shape", r"empty or not a list|empty working|not an object|no solution_levels")]


def classify(err: str) -> str:
    for name, rx in CHECKS:
        if re.search(rx, err):
            return name
    return "other"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="*")
    ap.add_argument("--no-novelty", action="store_true")
    args = ap.parse_args()
    paths = [Path(p) for p in args.items] or ITEMS
    n_items = n_parts_with = n_parts_total = 0
    parts_pass = parts_fail = 0
    fails = Counter()
    warns = Counter()
    std_lines = brisk_lines = every_lines = 0
    cost_files = 0.0
    attempts = Counter()
    rows = []
    for path in paths:
        item = json.loads(path.read_text())
        parts = item.get("parts") or []
        n_parts_total += len(parts)
        with_levels = [p for p in parts if p.get("solution_levels")]
        if not with_levels:
            continue
        n_items += 1
        item_ok = True
        for p in parts:
            if not p.get("solution_levels"):
                continue
            n_parts_with += 1
            errs, ws = gate_levels.part_errors(item, p, novelty=not args.no_novelty)
            lv = p["solution_levels"]
            std_lines += len(p.get("solution") or [])
            brisk_lines += len(lv.get("brisk") or [])
            every_lines += len(lv.get("every_step") or [])
            meta = p.get("levels_meta") or {}
            cost_files += meta.get("cost_usd") or 0.0
            attempts[meta.get("attempts")] += 1
            if errs:
                parts_fail += 1
                item_ok = False
                for e in errs:
                    fails[classify(e)] += 1
            else:
                parts_pass += 1
            for w in ws:
                warns[classify(w) if classify(w) != "other" else ("length-aim" if "aim for" in w else "other")] += 1
            rows.append((item["id"], p.get("label") or "-", "PASS" if not errs else "FAIL", len(p.get("solution") or []),
                         len(lv.get("brisk") or []), len(lv.get("every_step") or []), meta.get("attempts"),
                         meta.get("cost_usd"), errs))
        stored = ((item.get("gate_results") or {}).get("GL") or {}).get("pass")
        if stored is not None and stored != item_ok:
            print(f"note: {item['id']} stored GL pass={stored} but recomputed {item_ok}")
    cost_log, n_calls = 0.0, 0
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(r.get("step", "")).startswith("levels"):
                cost_log += r.get("cost_usd") or 0.0
                n_calls += 1

    print(f"{'item':48} {'part':4} {'GL':4} {'std':>3} {'brisk':>5} {'every':>5} {'att':>3} {'cost':>7}")
    for r in rows:
        print(f"{r[0]:48} {r[1]:4} {r[2]:4} {r[3]:3} {r[4]:5} {r[5]:5} {str(r[6]):>3} {('$%.3f' % r[7]) if r[7] is not None else '':>7}")
        for e in r[8]:
            print(f"    error: {e}")
    print()
    print(f"items with levels: {n_items} / {len(paths)}    parts with levels: {n_parts_with} / {n_parts_total}")
    print(f"parts passing GL: {parts_pass}    failing: {parts_fail}")
    print("failures per check:")
    for name, _ in CHECKS + [("other", "")]:
        print(f"  {name:12} {fails.get(name, 0)}")
    print(f"warnings: {dict(warns)}")
    if n_parts_with:
        print(f"average lines: standard {std_lines / n_parts_with:.1f}  brisk {brisk_lines / n_parts_with:.1f}  "
              f"every_step {every_lines / n_parts_with:.1f}  (every_step / standard = "
              f"{every_lines / max(std_lines, 1):.2f})")
    print(f"attempts: {dict(attempts)}")
    print(f"cost: ${cost_files:.2f} from the item files; ${cost_log:.2f} from {n_calls} levels* calls in the log")
    return 1 if parts_fail else 0


if __name__ == "__main__":
    sys.exit(main())
