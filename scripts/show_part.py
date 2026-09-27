#!/usr/bin/env python3
"""Triage a check_questions.py FAIL fast: print one part's transcription beside the QP/MS text-layer lines
around a search word, and the PDF page it's on (to render with pdftoppm if the text layer can't settle it).

    .venv/bin/python scripts/show_part.py GCE2008_6665_June2016 Q3 a            # text vs QP
    .venv/bin/python scripts/show_part.py GCE2008_6665_June2016 Q3 a --ms 360   # mark scheme vs MS, near '360'
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import check_questions as cq

ROOT = Path(__file__).resolve().parent.parent


def pages_with(pdf: Path, needle: str) -> list[int]:
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))
    return [p for p in range(1, n + 1) if needle.lower() in subprocess.run(
        ["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(pdf), "-"], capture_output=True, text=True).stdout.lower()]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pid, qn, lab = args[0], args[1].lstrip("Q"), (None if args[2] in ("-", "None") else args[2])
    kind = "MS" if "--ms" in sys.argv else "QP"
    near = sys.argv[sys.argv.index("--ms") + 1] if "--ms" in sys.argv else (args[3] if len(args) > 3 else None)
    d = json.loads((ROOT / "data/processed/_staging" / f"{pid}.json").read_text())
    q = next(q for q in d["questions"] if str(q["q_num"]) == qn)
    p = next(p for p in q["parts"] if p["label"] == lab)
    print("== transcription", "mark_scheme" if kind == "MS" else "stem + text")
    print(p["mark_scheme"] if kind == "MS" else (q.get("stem", "") + "\n---\n" + p["text"]))
    src = cq.RAW / d["source_ms_file" if kind == "MS" else "source_qp_file"]
    t = src.read_text(errors="ignore")
    if cq.shifted_font(t):
        t = cq.decode_shifted(t)
    lines = t.splitlines()
    words = re.findall(r"[A-Za-z]{3,}", re.sub(r"\$[^$]*\$", " ", p["text"]))
    key = near or " ".join(words[:2])
    pat = re.compile(r"\W+".join(map(re.escape, key.split())), re.I)
    hits = [i for i, ln in enumerate(lines) if key and pat.search(ln)]
    print(f"\n== {kind} text layer near {key!r} (lines {hits[:5]})")
    for i in hits[:2]:
        print("\n".join(lines[max(0, i - 6):i + 8]), "\n  ...")
    pdf = src.with_suffix(".pdf")
    if key:
        print(f"\n== PDF pages containing {key.split()[0]!r}: {pages_with(pdf, key.split()[0])}   ({pdf})")


if __name__ == "__main__":
    main()
