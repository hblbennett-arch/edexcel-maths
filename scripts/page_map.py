#!/usr/bin/env python3
"""For papers with no usable text layer (scans), find each question's pages and figure pages from
low-resolution page images in one small call, and write them into the staging file as qp_pages /
figure_pages, so figures can be attached to tutor answers. (find_figures.py uses the text layer
when it can; this is the fallback for scans.)

    .venv/bin/python scripts/page_map.py P3_June2019_mech P3_June2019_stats
"""
import json
import sys
from pathlib import Path

import extract_single as ex
from claude_oneshot import run, text_block

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"],
          "properties": {"questions": {"type": "array", "items": {
              "type": "object", "additionalProperties": False,
              "required": ["q_num", "first_page", "last_page", "figure_pages"],
              "properties": {"q_num": {"type": "string"}, "first_page": {"type": "integer"},
                             "last_page": {"type": "integer"},
                             "figure_pages": {"type": "array", "items": {"type": "integer"}}}}}}}


def main() -> None:
    for pid in sys.argv[1:]:
        x = ex.manifest_entry(pid)
        pdf = ex.ROOT / "data" / "raw" / "pearson" / x["qualification"] / x["sitting"] / f"{pid}_QP.pdf"
        imgs = []
        for i, img in enumerate(ex.page_images(pdf, 50), 1):
            imgs += [text_block(f"PAGE {i}"), img]
        r = run("You map exam question papers: for each numbered question, give the first and last page it occupies "
                "(including its answer space) and the pages that show a labelled Figure/diagram for it.",
                imgs + [text_block("Return the page map JSON (page numbers as labelled).")],
                schema=SCHEMA, step="page-map", ref=pid, thinking_tokens=1024)
        m = {q["q_num"].lstrip("Q"): q for q in r["result"]["questions"]}
        f = PROC / "_staging" / f"{pid}.json"
        d = json.loads(f.read_text())
        for q in d["questions"]:
            pm = m.get(q["q_num"])
            if pm:
                q["qp_pages"] = [pm["first_page"], pm["last_page"]]
                q["figure_pages"] = sorted(pm["figure_pages"])
                q["page_map_source"] = "page_map.py (scanned PDF)"
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print(pid, {k: (v["first_page"], v["last_page"], v["figure_pages"]) for k, v in m.items()}, f"${r['cost_usd']:.3f}")


if __name__ == "__main__":
    main()
