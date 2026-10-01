#!/usr/bin/env python3
"""Re-run the deterministic playbook checks (a)-(f) over content/clean/playbooks/*.json and print a table. No model calls.

    .venv/bin/python -m eval.playbooks_check [--failed] [--verbose] [FILE ...]

  --failed   include content/clean/playbooks/_failed/*.json
  --verbose  print every error and flag
The checks are those of scripts/clean/make_playbooks.py (the copy check reads the local corpus in-process; only
pass/fail and flags are shown). Cost is the sum of cost_usd stored in the files, next to the total of every
"playbook*" step in logs/llm_calls.jsonl.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import make_playbooks as mp  # noqa: E402

CHECKS = ("copy", "katex", "banned", "error_codes", "frequency_words", "mark_codes", "ids")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--failed", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    files = [Path(f) for f in args.files] or sorted(mp.PLAYBOOKS.glob("*.json"))
    if args.failed and not args.files:
        files += sorted(mp.FAILED.glob("*.json"))
    if not files:
        print("no playbooks")
        return 0
    facts = mp.Facts()
    passing: Counter = Counter()
    flagged, all_pass, cost, by_component = 0, 0, 0.0, Counter()
    rows = []
    for f in files:
        pb = json.loads(f.read_text())
        qt = pb["question_type"]
        res = mp.run_checks(pb, facts.context(qt), facts)
        cost += pb.get("cost_usd") or 0
        by_component[pb.get("component", "?")] += 1
        for k in CHECKS:
            passing[k] += bool(res[k]["pass"])
        all_pass += res["pass"]
        flagged += bool(res["flags"])
        rows.append((f.name, res))
        if args.verbose or not res["pass"]:
            bad = [k for k in CHECKS if not res[k]["pass"]]
            print(f"{f.name}: {'PASS' if res['pass'] else 'FAIL ' + ','.join(bad)}"
                  + (f"  copy-flag" if res["copy"].get("flag") else "") + f"  flags {len(res['flags'])}")
            for k in CHECKS:
                for e in res[k].get("errors") or res[k].get("reasons") or []:
                    print(f"    {k}: {e}")
            if args.verbose:
                for fl in res["flags"]:
                    print(f"    flag: {fl}")
    n = len(files)
    print()
    print(f"playbooks: {n}  ({dict(by_component)})")
    print(f"{'check':18} {'pass':>5} {'fail':>5}")
    for k in CHECKS:
        print(f"{k:18} {passing[k]:5} {n - passing[k]:5}")
    print(f"{'all checks':18} {all_pass:5} {n - all_pass:5}")
    print(f"copy-check flags (cosine / rare words, for review): {sum(1 for _, r in rows if r['copy'].get('flag'))}")
    print(f"playbooks with any flag: {flagged}")
    print(f"cost stored in files: ${cost:.2f}")
    log = ROOT / "logs" / "llm_calls.jsonl"
    if log.exists():
        steps: Counter = Counter()
        totals: Counter = Counter()
        for line in log.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if str(r.get("step", "")).startswith("playbook"):
                    steps[r["step"]] += 1
                    totals[r["step"]] += r.get("cost_usd") or 0
        print("llm_calls.jsonl playbook* steps: " + ", ".join(f"{s} x{steps[s]} ${totals[s]:.2f}" for s in sorted(steps))
              + f" | total ${sum(totals.values()):.2f}")
    return 0 if all_pass == n else 1


if __name__ == "__main__":
    sys.exit(main())
