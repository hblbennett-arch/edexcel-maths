#!/usr/bin/env python3
"""Park / unpark processed papers: keep all the processing work, but take it out of the chatbot.

User decision (2026-09-26): S2/S3/M2/M3 papers already processed stay on disk but must not be used
by the chatbot for now. build_db.py reads only data/processed/questions/ and examiner_notes/ (and
tags_assigned/), so parking moves a paper's files to data/processed/_parked/<same folder>/.
The staging file (_staging/) and triage (_triage/) stay where they are.

    .venv/bin/python scripts/park_units.py --park            # park every paper whose unit is out of scope.py
    .venv/bin/python scripts/park_units.py --unpark          # bring them all back
    .venv/bin/python scripts/park_units.py --list
Rebuild afterwards: build_db.py, build_embeddings.py.
"""
import json
import shutil
import sys
from pathlib import Path

from scope import NOT_PROCESSED_UNITS

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
FOLDERS = ["questions", "examiner_notes", "tags_assigned"]
PARK = PROC / "_parked"


def unit_of_file(f: Path) -> str | None:
    d = json.loads(f.read_text())
    if d.get("unit"):
        return d["unit"]
    q = (d.get("questions") or [{}])
    return q[0].get("unit") if isinstance(q, list) and q else None


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--list"
    moved = []
    if mode in ("--park", "--list"):
        for f in sorted((PROC / "questions").glob("*.json")):
            if unit_of_file(f) in NOT_PROCESSED_UNITS:
                moved.append(f.stem)
        if mode == "--park":
            for pid in moved:
                for folder in FOLDERS:
                    src = PROC / folder / f"{pid}.json"
                    if src.exists():
                        (PARK / folder).mkdir(parents=True, exist_ok=True)
                        shutil.move(str(src), PARK / folder / src.name)
    elif mode == "--unpark":
        for folder in FOLDERS:
            for f in sorted((PARK / folder).glob("*.json")):
                shutil.move(str(f), PROC / folder / f.name)
                if folder == "questions":
                    moved.append(f.stem)
    n_q = sum(len(json.loads(((PARK if mode == "--park" else PROC) / "questions" / f"{p}.json").read_text())["questions"])
              for p in moved if ((PARK if mode == "--park" else PROC) / "questions" / f"{p}.json").exists())
    print(f"{mode}: {len(moved)} papers, {n_q} questions: {', '.join(moved)}")


if __name__ == "__main__":
    main()
