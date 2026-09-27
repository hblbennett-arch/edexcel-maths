#!/usr/bin/env python3
"""Validate examiner-notes JSON files without rebuilding questions.db.

Runs the same checks build_db.py applies (verbatim quotes, known question
IDs, evidence links) against an in-memory DB, so several extractions can be
checked in parallel. Usage:

    .venv/bin/python scripts/check_examiner_notes.py [P1_June2022 ...]

With no arguments, checks every file in data/processed/examiner_notes/.
"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import build_db


def main() -> None:
    import os
    notes_dir = Path(os.environ.get("NOTES_DIR", build_db.EXAMINER_NOTES_DIR))   # override for comparison runs
    stems = sys.argv[1:] or [p.stem for p in sorted(notes_dir.glob("*.json"))]
    questions = [{**q, "_pid": build_db.paper_id_of(d)} for path in sorted(build_db.QUESTIONS_DIR.glob("*.json"))
                 for d in [json.loads(path.read_text())] for q in d["questions"]]
    known_question_ids = {q["id"] for q in questions}

    failed = False
    for stem in stems:
        with tempfile.TemporaryDirectory() as tmp:
            # Point the loader at a folder holding just this one file.
            single = Path(tmp) / f"{stem}.json"
            single.write_text((notes_dir / f"{stem}.json").read_text())
            build_db.EXAMINER_NOTES_DIR = Path(tmp)
            conn = sqlite3.connect(":memory:")
            conn.executescript(build_db.SCHEMA_PATH.read_text())
            for q in questions:
                conn.execute(
                    "INSERT INTO questions (id, spec, paper, sitting, paper_id, qualification, component, status, "
                    "q_num, question_text, mark_scheme_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (q["id"], q["spec"], q["paper"], q["sitting"], q["_pid"], q.get("qualification", q["spec"]),
                     q.get("component", "pure"), q.get("status", "current"), q["q_num"],
                     q["question_text"], q["mark_scheme_text"]))
                if q.get("parts"):
                    build_db.load_parts(conn, q, q["id"])
            try:
                n_notes, n_perf = build_db.load_examiner_notes(conn, known_question_ids)
                kinds = dict(conn.execute("SELECT kind, count(*) FROM examiner_notes GROUP BY kind").fetchall())
                n_display = conn.execute("SELECT count(*) FROM examiner_notes WHERE display IS NOT NULL").fetchone()[0]
                print(f"OK   {stem}: {n_notes} notes {kinds}, {n_display} with display, {n_perf} performance rows")
            except (ValueError, KeyError, sqlite3.Error) as e:
                failed = True
                print(f"FAIL {stem}: {e}")
            finally:
                conn.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
