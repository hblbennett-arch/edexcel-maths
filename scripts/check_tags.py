#!/usr/bin/env python3
"""Validate tag-assignment files (Phase 2f) without rebuilding questions.db.

Runs build_db.load_tag_assignments against an in-memory DB, one paper at a
time, so parallel tagging agents can check their own file. Also reports
coverage: parts with fewer than MIN_SKILLS skills are listed.

    .venv/bin/python scripts/check_tags.py P1_June2022     # one paper
    .venv/bin/python scripts/check_tags.py                 # all files in data/processed/tags_assigned/
"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

import build_db

MIN_SKILLS = 2


def main() -> None:
    tags_dir = build_db.TAGS_ASSIGNED_DIR
    stems = sys.argv[1:] or [p.stem for p in sorted(tags_dir.glob("*.json"))]
    failed = False
    for stem in stems:
        data = json.loads((tags_dir / f"{stem}.json").read_text())
        pid = build_db.paper_id_of(data)
        paper = json.loads((build_db.QUESTIONS_DIR / f"{pid}.json").read_text())
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA_PATH.read_text())
        for q in paper["questions"]:
            conn.execute("INSERT INTO questions (id, spec, paper, sitting, paper_id, qualification, component, status, "
                         "q_num, question_text, mark_scheme_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (q["id"], q["spec"], q["paper"], q["sitting"], pid, q.get("qualification", q["spec"]),
                          q.get("component", "pure"), q.get("status", "current"), q["q_num"],
                          q["question_text"], q["mark_scheme_text"]))
            build_db.load_parts(conn, q, q["id"])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f"{stem}.json").write_text(json.dumps(data))
            build_db.TAGS_ASSIGNED_DIR = Path(tmp)
            try:
                type_ids, skill_ids = build_db.load_vocabulary(conn)
                n_types, n_tags, n_parts = build_db.load_tag_assignments(conn, type_ids, skill_ids)
            except (ValueError, KeyError) as e:
                failed = True
                print(f"FAIL {stem}: {e}")
                continue
            finally:
                build_db.TAGS_ASSIGNED_DIR = tags_dir
        thin = [(qid, lab, len(sk)) for qid, e in data["questions"].items()
                for lab, sk in e["parts"].items() if len(sk) < MIN_SKILLS]
        print(f"OK   {stem}: {n_types} question(s) typed, {n_tags} skill tag(s) on {n_parts} part(s), "
              f"{n_tags / max(n_parts, 1):.1f} per part" + (f"; {len(thin)} part(s) with <{MIN_SKILLS} skills: "
                                                          f"{thin[:8]}" if thin else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
