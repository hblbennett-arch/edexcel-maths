#!/usr/bin/env python3
"""Step 2b (spec filter): split an extracted paper into kept and dropped questions.

Extraction agents write data/processed/_staging/<paper_id>.json with every question
on the paper; each part carries spec_refs, and parts using a topic or method that is
not in the 9MA0 specification carry an out_of_spec entry. The user's rule: if ANY
part of a question is out of spec, the whole question is dropped.

    .venv/bin/python scripts/apply_spec_filter.py IAL2018_WST01_Jan2020   # one paper
    .venv/bin/python scripts/apply_spec_filter.py --all                   # every staging file
    .venv/bin/python scripts/apply_spec_filter.py --summary               # counts only

Writes data/processed/questions/<paper_id>.json (kept questions only, with an
"excluded_questions" list so the paper's numbering and totals stay explainable) and
data/processed/_excluded/<paper_id>.json (dropped questions, full content + reasons).
The staging file must pass scripts/check_questions.py first.
"""
import json
import sys
from pathlib import Path

import check_questions

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
STAGING, QUESTIONS, EXCLUDED = PROC / "_staging", PROC / "questions", PROC / "_excluded"


def prune_downstream(pid: str, dropped: set[str]) -> None:
    """A question dropped AFTER notes/tags were made (e.g. by concept_screen.py): move its examiner notes,
    performance rows and tags out of the chatbot data into _excluded/<pid>_downstream.json (kept, not
    deleted), so nothing about it can reach or influence the chatbot."""
    if not dropped:
        return
    saved = {}
    nf = PROC / "examiner_notes" / f"{pid}.json"
    if nf.exists():
        d = json.loads(nf.read_text())
        gone = [n for n in d["notes"] if n.get("question_id") in dropped]
        if gone:
            d["notes"] = [n for n in d["notes"] if n.get("question_id") not in dropped]
            perf_gone = [p for p in d.get("performance", []) if p["question_id"] in dropped]
            d["performance"] = [p for p in d.get("performance", []) if p["question_id"] not in dropped]
            nf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
            saved["examiner_notes"], saved["performance"] = gone, perf_gone
    tf = PROC / "tags_assigned" / f"{pid}.json"
    if tf.exists():
        d = json.loads(tf.read_text())
        gone = {k: v for k, v in d["questions"].items() if k in dropped}
        if gone:
            d["questions"] = {k: v for k, v in d["questions"].items() if k not in dropped}
            tf.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
            saved["tags"] = gone
    if saved:
        out = EXCLUDED / f"{pid}_downstream.json"
        old = json.loads(out.read_text()) if out.exists() else {}
        for k, v in saved.items():
            old[k] = (old.get(k) or ([] if isinstance(v, list) else {}))
            old[k] = old[k] + v if isinstance(v, list) else {**old[k], **v}
        out.write_text(json.dumps(old, indent=2, ensure_ascii=False) + "\n")


def split(pid: str, write: bool = True) -> tuple[int, int]:
    src = STAGING / f"{pid}.json"
    errs = [e for e in check_questions.check(src) if not e.startswith("NOTICE")]
    if errs:
        raise SystemExit(f"{pid}: staging file fails check_questions.py ({len(errs)} problems) — fix it first")
    d = json.loads(src.read_text())
    keep, drop = [], []
    triaged = d.get("excluded_questions", [])              # dropped at triage: never transcribed
    for q in d["questions"]:
        oos = [{"label": p["label"], **p["out_of_spec"]} for p in q["parts"] if p.get("out_of_spec")]
        if oos:
            drop.append({**q, "excluded_because": oos})
        else:
            keep.append(q)
    if write:
        summary = [{"q_num": q["q_num"], "total_marks": q["total_marks"],
                    "parts": [{"label": p["label"], "marks": p["marks"],
                               "technique": (p.get("out_of_spec") or {}).get("technique", "in spec"),
                               "reason": (p.get("out_of_spec") or {}).get("reason", "question dropped: other parts out of spec")}
                              for p in q["parts"]]}
                   for q in drop]
        excluded = sorted(triaged + summary, key=lambda x: int(x["q_num"]))
        # The user's rule (2026-09-26): dropped questions must not reach or influence the chatbot, so
        # questions/ holds kept questions only; every trace of the dropped ones lives in _excluded/.
        kept = {k: v for k, v in d.items() if k != "excluded_questions"} | {"questions": keep}
        # Figure pages are derived here, every time, so rebuilding questions/ can't lose them
        # (it did once: Tier 2's questions all lost has_figure / figure_pages).
        import find_figures
        find_figures.process_paper(kept)
        QUESTIONS.mkdir(exist_ok=True)
        EXCLUDED.mkdir(exist_ok=True)
        (QUESTIONS / f"{pid}.json").write_text(json.dumps(kept, indent=2, ensure_ascii=False) + "\n")
        prune_downstream(pid, {q["id"] for q in drop} | {f"{pid}_Q{x['q_num']}" for x in triaged})
        out = EXCLUDED / f"{pid}.json"
        if drop or triaged:
            out.write_text(json.dumps({"_paper_id": pid, "summary": excluded, "questions": drop},
                                      indent=2, ensure_ascii=False) + "\n")
        else:
            out.unlink(missing_ok=True)
    return len(keep), len(drop) + len(triaged)


def main() -> None:
    args = sys.argv[1:]
    summary = "--summary" in args
    pids = [p.stem for p in sorted(STAGING.glob("*.json"))] if ("--all" in args or summary) else \
        [a for a in args if not a.startswith("--")]
    tk = td = 0
    for pid in pids:
        try:
            k, dr = split(pid, write=not summary)
        except SystemExit as e:
            print(f"{pid:32s} SKIPPED: {e}")
            continue
        tk, td = tk + k, td + dr
        print(f"{pid:32s} kept {k:3d}  dropped {dr:3d}")
    print(f"TOTAL kept {tk}, dropped {td}")


if __name__ == "__main__":
    main()
