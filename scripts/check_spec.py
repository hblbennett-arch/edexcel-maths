#!/usr/bin/env python3
"""Validate data/processed/spec_9ma0.json, the 9MA0 content list transcribed from
the official specification PDF (data/spec/9MA0-specification-issue4.pdf).

Checks:
- shape: every statement has ref, component (pure|stats|mech), section, topic, text;
- refs are unique and follow the document's numbering (P1.1-P10.x, S1.1-S5.x, M6.1-M9.x);
- sections are contiguous and every section has statements;
- verbatim-ness: each statement's words (and its guidance's words) must appear, in
  order, in the specification text. A subsequence test is used because the PDF's
  two-column layout (content | guidance) interleaves lines in pdftotext output.

    .venv/bin/python scripts/check_spec.py
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_JSON = ROOT / "data" / "processed" / "spec_9ma0.json"
SPEC_TXT = ROOT / "data" / "spec" / "9MA0-specification-issue4.txt"
PREFIX = {"pure": ("P", range(1, 11)), "stats": ("S", range(1, 6)), "mech": ("M", range(6, 10))}


def words(t: str, strip_math: bool = False) -> list[str]:
    if strip_math:                              # LaTeX command names (\sum, \frac{dx}{dt}) aren't in the PDF text
        t = re.sub(r"\$[^$]*\$", " ", t)
    t = unicodedata.normalize("NFKC", t).lower()
    t = t.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    return re.findall(r"[a-z]{2,}", t)          # letters only: maths symbols garble in pdftotext


def is_subsequence(needle: list[str], hay: list[str], start_hint: int = 0) -> bool:
    it = iter(hay[start_hint:])
    return all(any(w == h for h in it) for w in needle)


def main() -> int:
    d = json.loads(SPEC_JSON.read_text())
    hay = words(SPEC_TXT.read_text())
    errs, refs = [], set()
    stmts = d.get("statements", [])
    by_section = {}
    for s in stmts:
        for k in ("ref", "component", "section", "section_title", "text"):
            if not s.get(k):
                errs.append(f"{s.get('ref')}: missing {k}")
        comp = s.get("component")
        if comp not in PREFIX:
            errs.append(f"{s.get('ref')}: bad component {comp!r}")
            continue
        p, rng = PREFIX[comp]
        m = re.fullmatch(rf"{p}(\d+)\.(\d+)", s.get("ref", ""))
        if not m or int(m.group(1)) not in rng or int(m.group(1)) != s.get("section"):
            errs.append(f"{s.get('ref')}: ref does not match component/section numbering")
        if s.get("ref") in refs:
            errs.append(f"duplicate ref {s['ref']}")
        refs.add(s.get("ref"))
        by_section.setdefault((comp, s.get("section")), []).append(s)
        for field in ("text", "guidance"):
            w = words(s.get(field) or "", strip_math=True)
            if w and not is_subsequence(w, hay):
                # report the first word that breaks the sequence, to help fixing
                it, seen = iter(hay), []
                for x in w:
                    if not any(x == h for h in it):
                        break
                    seen.append(x)
                errs.append(f"{s['ref']} {field}: not verbatim near '{' '.join(seen[-4:])} >>{x}<<'")
    for comp, (p, rng) in PREFIX.items():
        for n in rng:
            if (comp, n) not in by_section:
                errs.append(f"no statements for {p}{n}")
    for e in errs:
        print("ERR", e)
    n_by = {c: sum(1 for s in stmts if s.get("component") == c) for c in PREFIX}
    print(f"{len(stmts)} statements ({n_by}); {len(errs)} errors")
    if not errs:
        print("OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
