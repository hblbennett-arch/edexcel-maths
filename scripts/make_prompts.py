#!/usr/bin/env python3
"""Fill agent prompt templates (docs/prompts/*.txt) from data/raw/pearson/manifest.json,
so an orchestrating session never retypes paper fields by hand (and never gets them wrong).

    .venv/bin/python scripts/make_prompts.py extract P3_June2022_stats IAL2018_WST02_Jan2022
    .venv/bin/python scripts/make_prompts.py extract --todo --limit 5    # next papers with no _staging file
    .venv/bin/python scripts/make_prompts.py extract --todo --only '^IAL2018_WST'

Writes <scratch>/prompts/<step>_<paper_id>.txt and prints the paths. Each agent is then
launched with the one-line prompt: "Your complete task instructions are in <path> — read
that file first and follow it exactly. Work in /Users/i1003721/edexcel-maths."
Only papers whose QP and MS are both downloaded are eligible.
"""
import argparse
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "raw" / "pearson" / "manifest.json"
PROMPTS = ROOT / "docs" / "prompts"
STAGING = ROOT / "data" / "processed" / "_staging"

SPEC_RULE = {
    "current": ("This is a current 9MA0 paper: every question is in spec by definition — tag spec_refs on "
                "every part and never add out_of_spec. Set uses_large_data_set where the question relies on "
                "the Large Data Set."),
    "legacy": ("This is a LEGACY paper used only as an extra question source: follow 'Triage first' in the v3 "
               "section: decide every part in/out of spec against spec_9ma0.json (topic OR required method; "
               "check the statements' text and guidance, including stated exclusions, never memory), transcribe "
               "ONLY questions whose every part is in spec, and list every other question in excluded_questions "
               "(marks + technique + reason per part, no text)."),
}


def papers() -> dict[str, dict]:
    out = {}
    for d in json.loads(MANIFEST.read_text()):
        if d["unit"] == "ALL":
            continue
        p = out.setdefault(d["paper_id"], {**d, "docs": {}})
        p["docs"][d["doc_type"]] = bool(d.get("local_pdf"))
        if d["doc_type"] == "QP":
            p["title"] = d["title"]
    return {k: v for k, v in out.items() if v["docs"].get("QP") and v["docs"].get("MS")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", help="template name in docs/prompts/, e.g. extract (-> extract-paper.txt)")
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--todo", action="store_true", help="papers with no _staging file yet")
    ap.add_argument("--only", help="regex on paper_id")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--scratch", default=os.environ.get("SCRATCH", "/tmp/edexcel-scratch"))
    a = ap.parse_args()
    template = (PROMPTS / f"{a.step}-paper.txt").read_text()
    avail = papers()
    ids = a.paper_ids or sorted(avail)
    if a.todo:
        from scope import in_processing_scope
        ids = [i for i in ids if not (STAGING / f"{i}.json").exists() and in_processing_scope(i, avail[i]["unit"])]
    if a.only:
        ids = [i for i in ids if re.search(a.only, i)]
    ids = ids[: a.limit] if a.limit else ids
    outdir = Path(a.scratch) / "prompts"
    outdir.mkdir(parents=True, exist_ok=True)
    for pid in ids:
        x = avail[pid]
        text = template.format(
            PID=pid, PAPER="P3" if x["qualification"] == "9MA0" and x["unit"].startswith("9MA0-3") else
            (x["unit_name"] if x["qualification"] == "9MA0" else x["unit"] + x["variant"]),
            SITTING=x["sitting"], QUAL=x["qualification"], UNIT=x["unit"], COMP=x["component"],
            STATUS=x["status"], TITLE=x["title"], SPEC_RULE=SPEC_RULE[x["status"]], SCRATCH=a.scratch)
        path = outdir / f"{a.step}_{pid}.txt"
        path.write_text(text)
        print(path)


if __name__ == "__main__":
    main()
