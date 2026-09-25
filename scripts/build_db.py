#!/usr/bin/env python3
"""Build/refresh the RAG knowledge base SQLite DB from the JSON source files.

Layout — content and tags are deliberately kept in separate files, since a
question can carry multiple topic tags and content must not be duplicated:

    data/processed/tags.json                       controlled vocabulary
    data/processed/questions/<paper>_<sitting>.json  question CONTENT, one file per paper
    data/processed/topics/<topic-id>.json            {_topic, question_ids} — topic tag assignments
    data/processed/techniques/<technique-id>.json    technique content + question_ids using it

Rerunning this script is safe — it drops and recreates the DB from the
current JSON/schema files each time, so the JSON files (not questions.db)
are the source of truth. To add new papers/topics, extend the JSON files
(see scripts/merge_staged.py if starting from raw per-paper extractions)
and rerun this script.
"""
import json
import sqlite3
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
SCHEMA_PATH = PROCESSED_DIR / "schema.sql"
TAGS_PATH = PROCESSED_DIR / "tags.json"
QUESTIONS_DIR = PROCESSED_DIR / "questions"
TOPICS_DIR = PROCESSED_DIR / "topics"
TECHNIQUES_DIR = PROCESSED_DIR / "techniques"
DB_PATH = PROCESSED_DIR / "questions.db"


def load_valid_tags() -> set[str]:
    tags = json.loads(TAGS_PATH.read_text())
    return {t["id"] for t in tags["topics"]} | {t["id"] for t in tags["techniques"]}


def main() -> None:
    valid_tags = load_valid_tags()
    known_question_ids: set[str] = set()

    DB_PATH.unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    # --- questions: one file per paper, content only ---------------------
    n_questions = 0
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        paper_data = json.loads(path.read_text())
        expected_stem = f"{paper_data['_paper']}_{paper_data['_sitting']}"
        if path.stem != expected_stem:
            raise ValueError(f"{path.name}: filename must match {expected_stem}.json")

        rows = [
            {
                "id": q["id"], "spec": q["spec"], "paper": q["paper"], "sitting": q["sitting"],
                "q_num": q["q_num"], "total_marks": q["total_marks"],
                "question_text": q["question_text"], "mark_scheme_text": q["mark_scheme_text"],
                "source_qp_file": q["source_qp_file"], "source_ms_file": q["source_ms_file"],
                "low_confidence": int(q.get("low_confidence", False)),
                "notes": q.get("notes", ""),
            }
            for q in paper_data["questions"]
        ]
        conn.executemany(
            """INSERT INTO questions
               (id, spec, paper, sitting, q_num, total_marks, question_text,
                mark_scheme_text, source_qp_file, source_ms_file, low_confidence, notes)
               VALUES (:id, :spec, :paper, :sitting, :q_num, :total_marks,
                       :question_text, :mark_scheme_text, :source_qp_file, :source_ms_file,
                       :low_confidence, :notes)""",
            rows,
        )
        known_question_ids.update(r["id"] for r in rows)
        n_questions += len(rows)
    print(f"  loaded {n_questions} question(s) from {len(list(QUESTIONS_DIR.glob('*.json')))} paper file(s)")

    # --- topics: {_topic, question_ids} — topic-type question_tags rows --
    n_topic_tags = 0
    for path in sorted(TOPICS_DIR.glob("*.json")):
        topic_data = json.loads(path.read_text())
        topic_id = topic_data["_topic"]
        if path.stem != topic_id:
            raise ValueError(f"{path.name}: _topic '{topic_id}' must match filename")
        if topic_id not in valid_tags:
            raise ValueError(f"{path.name}: topic '{topic_id}' not declared in tags.json")

        rows = []
        for qid in topic_data["question_ids"]:
            if qid not in known_question_ids:
                raise ValueError(f"{path.name}: references unknown question_id '{qid}'")
            rows.append({"question_id": qid, "tag_type": "topic", "tag_value": topic_id})
        conn.executemany(
            "INSERT INTO question_tags (question_id, tag_type, tag_value) "
            "VALUES (:question_id, :tag_type, :tag_value)",
            rows,
        )
        n_topic_tags += len(rows)
    print(f"  loaded {n_topic_tags} topic tag(s) from {len(list(TOPICS_DIR.glob('*.json')))} topic file(s)")

    # --- techniques: content + question_ids using it ----------------------
    n_techniques = 0
    n_technique_tags = 0
    for path in sorted(TECHNIQUES_DIR.glob("*.json")):
        tech = json.loads(path.read_text())
        if tech["id"] != path.stem:
            raise ValueError(f"{path.name}: id '{tech['id']}' must match filename")
        if tech["id"] not in valid_tags:
            raise ValueError(f"{path.name}: id '{tech['id']}' not declared in tags.json")

        conn.execute(
            "INSERT INTO techniques (id, title, content, contrast_with) "
            "VALUES (:id, :title, :content, :contrast_with)",
            {"id": tech["id"], "title": tech["title"], "content": tech["content"],
             "contrast_with": tech.get("contrast_with", "")},
        )
        n_techniques += 1

        rows = []
        for qid in tech.get("question_ids", []):
            if qid not in known_question_ids:
                raise ValueError(f"{path.name}: references unknown question_id '{qid}'")
            rows.append({"question_id": qid, "tag_type": "technique", "tag_value": tech["id"]})
        conn.executemany(
            "INSERT INTO question_tags (question_id, tag_type, tag_value) "
            "VALUES (:question_id, :tag_type, :tag_value)",
            rows,
        )
        n_technique_tags += len(rows)
    print(f"  loaded {n_techniques} technique(s), {n_technique_tags} technique tag(s)")

    conn.commit()
    conn.close()
    print(f"\nBuilt {DB_PATH.relative_to(PROCESSED_DIR.parent.parent)} — "
          f"{n_questions} question(s), {n_techniques} technique(s), "
          f"{n_topic_tags + n_technique_tags} tag(s) total.")


if __name__ == "__main__":
    main()
