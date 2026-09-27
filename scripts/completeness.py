#!/usr/bin/env python3
"""End-of-run completeness report: nothing may go missing silently.

For every paper matching the regex, check the chain: downloaded QP+MS -> staging file -> passes
check_questions -> questions/ file -> examiner notes (when a report exists and questions were kept).
Prints one line per gap and a summary; exit code 1 if anything is missing.

    .venv/bin/python scripts/completeness.py '^IAL2018_'
"""
import json
import re
import sys
from pathlib import Path

import check_questions

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"


def main() -> int:
    rx = re.compile(sys.argv[1] if len(sys.argv) > 1 else ".")
    man = json.loads((ROOT / "data" / "raw" / "pearson" / "manifest.json").read_text())
    have: dict[str, set] = {}
    from scope import in_processing_scope
    for d in man:
        if d["unit"] != "ALL" and in_processing_scope(d["paper_id"], d["unit"]) and rx.search(d["paper_id"]):
            have.setdefault(d["paper_id"], set())
            if d.get("local_pdf"):
                have[d["paper_id"]].add(d["doc_type"])
    gaps, n_ok = [], 0
    for pid, docs in sorted(have.items()):
        if not {"QP", "MS"} <= docs:
            continue                                     # not processable (locked / not published): see pearson-coverage.md
        st = PROC / "_staging" / f"{pid}.json"
        if not st.exists():
            gaps.append((pid, "no staging file (not extracted)")); continue
        errs = [e for e in check_questions.check(st) if not e.startswith("NOTICE")]
        if errs:
            gaps.append((pid, f"fails check_questions ({len(errs)}): {errs[0][:90]}")); continue
        qf = PROC / "questions" / f"{pid}.json"
        if not qf.exists():
            gaps.append((pid, "passes checks but not in questions/ (run apply_spec_filter.py)")); continue
        kept = json.loads(qf.read_text())["questions"]
        if kept and "ER" in docs and not (PROC / "examiner_notes" / f"{pid}.json").exists():
            gaps.append((pid, "kept questions + a report, but no examiner notes")); continue
        n_ok += 1
    for pid, why in gaps:
        print(f"GAP  {pid}: {why}")
    print(f"{n_ok} papers complete, {len(gaps)} gaps")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
