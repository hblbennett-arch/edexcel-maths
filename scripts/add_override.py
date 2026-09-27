#!/usr/bin/env python3
"""Record a VERIFIED checker exception in a staging file, after looking at the rendered PDF page.

    .venv/bin/python scripts/add_override.py GCE2008_6663_Jan2008 "GCE2008_6663_Jan2008_Q8(a): numbers ['32']" \
        "QP p.12 prints 'k^2+4k-32<0' as an image; the text layer drops it"

`match` is a prefix of the checker's error line (so only that error is waived); the override is written with
today's verifier stamp. Never use it to waive a check you haven't confirmed on the page.
"""
import json
import sys
from pathlib import Path

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    pid, match, evidence = sys.argv[1:]
    f = PROC / "_staging" / f"{pid}.json"
    d = json.loads(f.read_text())
    ov = d.setdefault("check_overrides", [])
    if any(o["match"] == match for o in ov):
        raise SystemExit(f"{pid}: override already recorded")
    ov.append({"match": match, "evidence": evidence, "verified_by": "Claude, reading the rendered PDF page"})
    f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    print(f"{pid}: override added ({match})")


if __name__ == "__main__":
    main()
