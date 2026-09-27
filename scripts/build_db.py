#!/usr/bin/env python3
"""Build/refresh the RAG knowledge base SQLite DB from the JSON source files.

Layout — content and tags are deliberately kept in separate files, since a
question can carry multiple topic tags and content must not be duplicated:

    data/processed/tags.json                       controlled vocabulary
    data/processed/questions/<paper>_<sitting>.json  question CONTENT, one file per paper
    data/processed/topics/<topic-id>.json            {_topic, question_ids} — topic tag assignments
    data/processed/techniques/<technique-id>.json    technique content + question_ids using it
    data/processed/examiner_notes/<paper>_<sitting>.json  verbatim examiner-report quotes +
                                                     per-question performance (see
                                                     docs/examiner-notes-extraction.md)

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
EXAMINER_NOTES_DIR = PROCESSED_DIR / "examiner_notes"
TAGS_ASSIGNED_DIR = PROCESSED_DIR / "tags_assigned"
SOURCES_PATH = PROCESSED_DIR / "sources.json"
RAW_DIR = PROCESSED_DIR.parent / "raw"
DB_PATH = PROCESSED_DIR / "questions.db"


def load_valid_tags() -> set[str]:
    tags = json.loads(TAGS_PATH.read_text())
    return {t["id"] for t in tags["topics"]} | {t["id"] for t in tags["techniques"]}


def load_vocabulary(conn: sqlite3.Connection) -> tuple[set[str], set[str]]:
    """Insert question types, skill groups and skills from tags.json; return (type ids, skill ids)."""
    tags = json.loads(TAGS_PATH.read_text())
    groups = {g["id"] for g in tags.get("skill_groups", [])}
    conn.executemany("INSERT INTO skill_groups (id, title) VALUES (?, ?)",
                     [(g["id"], g["title"]) for g in tags.get("skill_groups", [])])
    for sk in tags.get("skills", []):
        if sk["group"] not in groups:
            raise ValueError(f"tags.json: skill {sk['id']} has unknown group '{sk['group']}'")
    conn.executemany(
        "INSERT INTO skills (id, title, group_id, description, formula_booklet) VALUES (?, ?, ?, ?, ?)",
        [(sk["id"], sk["title"], sk["group"], sk.get("description"), int(sk.get("formula_booklet", False)))
         for sk in tags.get("skills", [])])
    conn.executemany("INSERT INTO question_types (id, title, topic, definition) VALUES (?, ?, ?, ?)",
                     [(t["id"], t["title"], t.get("topic"), t.get("definition"))
                      for t in tags.get("question_types", [])])
    return {t["id"] for t in tags.get("question_types", [])}, {sk["id"] for sk in tags.get("skills", [])}


def load_tag_assignments(conn: sqlite3.Connection, type_ids: set[str], skill_ids: set[str]) -> tuple[int, int, int]:
    """Load data/processed/tags_assigned/<paper>_<sitting>.json:
        {"_paper", "_sitting", "questions": {"<qid>": {"question_type": "...",
                                                       "parts": {"<label or ->": ["skill", ...]}}}}
    Every question in the paper needs a type and an entry for every part."""
    n_types = n_skill_tags = n_parts = 0
    for path in sorted(TAGS_ASSIGNED_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        paper_qids = {r[0] for r in conn.execute(
            "SELECT id FROM questions WHERE paper_id = ?", (paper_id_of(data),))}
        missing = paper_qids - data["questions"].keys()
        if missing:
            raise ValueError(f"{path.name}: no tags for {sorted(missing)}")
        for qid, entry in data["questions"].items():
            if qid not in paper_qids:
                raise ValueError(f"{path.name}: unknown question {qid}")
            if entry["question_type"] not in type_ids:
                raise ValueError(f"{path.name}: {qid} has unknown question_type '{entry['question_type']}'")
            conn.execute("INSERT INTO question_tags (question_id, part_label, tag_type, tag_value) "
                         "VALUES (?, NULL, 'question_type', ?)", (qid, entry["question_type"]))
            n_types += 1
            labels = ["-" if l is None else l for l in part_labels_for(conn, qid)]
            if sorted(entry["parts"]) != sorted(labels):
                raise ValueError(f"{path.name}: {qid} part keys {sorted(entry['parts'])} != parts {sorted(labels)}")
            for label, skills in entry["parts"].items():
                unknown = [s for s in skills if s not in skill_ids]
                if unknown:
                    raise ValueError(f"{path.name}: {qid}:{label} unknown skill(s) {unknown}")
                if len(set(skills)) != len(skills):
                    raise ValueError(f"{path.name}: {qid}:{label} repeats a skill")
                conn.executemany(
                    "INSERT INTO question_tags (question_id, part_label, tag_type, tag_value) VALUES (?, ?, 'skill', ?)",
                    [(qid, None if label == "-" else label, sk) for sk in skills])
                n_skill_tags += len(skills)
                n_parts += 1
    return n_types, n_skill_tags, n_parts


def paper_id_of(data: dict) -> str:
    """Files for new papers carry _paper_id (e.g. P3_June2019_stats, IAL2018_WST01_Jan2020);
    the original Pure files are named <_paper>_<_sitting>."""
    return data.get("_paper_id") or f"{data['_paper']}_{data['_sitting']}"


# Defaults for the original A Level Pure files, which predate the qualification fields.
PURE_UNIT = {"P1": "9MA0-01", "P2": "9MA0-02"}


def normalise(text: str) -> str:
    """Collapse whitespace and unify typographic quotes/dashes so a quote
    wrapped across lines by pdftotext still matches."""
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        text = text.replace(a, b)
    return " ".join(text.split())


def find_quote_page(quote: str, pages: list[str]) -> int | None:
    """Return the 1-based page where `quote` starts, or None if it isn't in the report."""
    joined, starts = "", []
    for page in pages:
        starts.append(len(joined))
        joined += normalise(page) + " "
    pos = joined.find(normalise(quote))
    if pos == -1:
        return None
    return max(i for i, s in enumerate(starts) if s <= pos) + 1


def load_parts(conn: sqlite3.Connection, q: dict, filename: str) -> None:
    """Load a question's parts. Every question must be split (scripts/split_parts.py)."""
    parts = q.get("parts")
    if not parts:
        raise ValueError(f"{filename}: {q['id']} has no parts — run scripts/split_parts.py or split by hand")
    labels = [p["label"] for p in parts]
    if len(set(labels)) != len(labels):
        raise ValueError(f"{filename}: {q['id']} has duplicate part labels {labels}")
    if None in labels and len(parts) > 1:
        raise ValueError(f"{filename}: {q['id']} mixes a NULL (whole-question) label with other parts")
    if sum(p["marks"] for p in parts) != q["total_marks"]:
        raise ValueError(f"{filename}: {q['id']} part marks sum to {sum(p['marks'] for p in parts)}, "
                         f"total_marks is {q['total_marks']}")
    conn.executemany(
        "INSERT INTO question_parts (question_id, part_index, label, marks, text, mark_scheme, spec_refs) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(q["id"], i, p["label"], p["marks"], p["text"], p["mark_scheme"],
          json.dumps(p["spec_refs"]) if p.get("spec_refs") is not None else None)
         for i, p in enumerate(parts)],
    )


def part_label_matches(label: str | None, part_labels: list[str | None]) -> bool:
    """A note/tag label is valid if it names a part, a sub-part of a part ("a(ii)" when
    the part is "a"), or a parent of parts ("b" when the parts are "b(i)", "b(ii)")."""
    if label is None:
        return True
    return any(p is not None and (label == p or label.startswith(p + "(") or p.startswith(label + "("))
               for p in part_labels)


def note_label_ok(conn: sqlite3.Connection, question_id: str, label: str | None) -> bool:
    """Labels must name a part, except inside a single-part question whose one marks
    total spans sub-parts ("(i) … (ii) … (iii) … (4)"): there a sub-label printed in
    the question text is fine."""
    part_labels = part_labels_for(conn, question_id)
    if part_label_matches(label, part_labels):
        return True
    if part_labels == [None]:
        text = conn.execute("SELECT question_text FROM questions WHERE id = ?", (question_id,)).fetchone()[0]
        return f"({label})" in text
    return False


def part_labels_for(conn: sqlite3.Connection, question_id: str) -> list[str | None]:
    return [r[0] for r in conn.execute(
        "SELECT label FROM question_parts WHERE question_id = ? ORDER BY part_index", (question_id,))]


def load_examiner_notes(conn: sqlite3.Connection, known_question_ids: set[str]) -> tuple[int, int]:
    n_notes = n_perf = 0
    for path in sorted(EXAMINER_NOTES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        expected_stem = paper_id_of(data)
        if path.stem != expected_stem:
            raise ValueError(f"{path.name}: filename must match {expected_stem}.json")
        source_file = data["source_file"]
        pages = (RAW_DIR / source_file).read_text().split("\f")

        note_ids: set[str] = set()
        for note in data["notes"]:
            qid = note.get("question_id")
            if qid is not None and qid not in known_question_ids:
                raise ValueError(f"{path.name}: note {note['id']} references unknown question_id '{qid}'")
            if note["id"] in note_ids:
                raise ValueError(f"{path.name}: duplicate note id {note['id']}")
            if qid is not None and not note_label_ok(conn, qid, note.get("part_label")):
                raise ValueError(f"{path.name}: note {note['id']} part_label '{note.get('part_label')}' "
                                 f"is not a part of {qid} (parts: {part_labels_for(conn, qid)})")
            page = find_quote_page(note["quote"], pages)
            if page is None:
                raise ValueError(
                    f"{path.name}: note {note['id']} quote not found verbatim in {source_file}:\n"
                    f"    {note['quote'][:120]}"
                )
            conn.execute(
                "INSERT INTO examiner_notes (id, question_id, part_label, kind, quote, display, source_file, page) "
                "VALUES (:id, :question_id, :part_label, :kind, :quote, :display, :source_file, :page)",
                {"id": note["id"], "question_id": qid, "part_label": note.get("part_label"),
                 "kind": note["kind"], "quote": note["quote"], "display": note.get("display"),
                 "source_file": source_file, "page": page},
            )
            note_ids.add(note["id"])
            n_notes += 1

        seen_perf: set[tuple] = set()
        for perf in data.get("performance", []):
            key = (perf["question_id"], perf.get("part_label"))
            if perf["question_id"] not in known_question_ids:
                raise ValueError(f"{path.name}: performance references unknown question_id '{key[0]}'")
            if key in seen_perf:
                raise ValueError(f"{path.name}: duplicate performance row {key}")
            evidence = perf.get("evidence_note_id")
            if evidence is not None and evidence not in note_ids:
                raise ValueError(f"{path.name}: performance {key} cites unknown note '{evidence}'")
            pct_note = perf.get("full_marks_pct_note_id")
            if perf.get("full_marks_pct") is not None and pct_note not in note_ids:
                raise ValueError(f"{path.name}: performance {key} full_marks_pct needs a valid full_marks_pct_note_id")
            if perf.get("rating") is not None and evidence is None:
                raise ValueError(f"{path.name}: performance {key} has a rating but no evidence_note_id")
            conn.execute(
                "INSERT INTO question_performance "
                "(question_id, part_label, mean_mark, max_mark, full_marks_pct, full_marks_pct_note_id, "
                " rating, evidence_note_id) "
                "VALUES (:question_id, :part_label, :mean_mark, :max_mark, :full_marks_pct, "
                "        :full_marks_pct_note_id, :rating, :evidence_note_id)",
                {"question_id": key[0], "part_label": key[1], "mean_mark": perf.get("mean_mark"),
                 "max_mark": perf.get("max_mark"), "full_marks_pct": perf.get("full_marks_pct"),
                 "full_marks_pct_note_id": pct_note, "rating": perf.get("rating"),
                 "evidence_note_id": evidence},
            )
            seen_perf.add(key)
            n_perf += 1
    return n_notes, n_perf


def load_sources(conn: sqlite3.Connection) -> int:
    papers = json.loads(SOURCES_PATH.read_text())["papers"]
    link = lambda e, key, field="url": (e.get(key) or {}).get(field)
    conn.executemany(
        "INSERT INTO sources (paper_id, spec, paper, sitting, component, official, in_knowledge_base, "
        " qp_url, qp_viewer_url, ms_url, ms_viewer_url, er_url, pmt_model_answers_url) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(e["paper_id"], e["spec"], e["paper"], e["sitting"], e["component"], int(e["official"]),
          int(e["in_knowledge_base"]), link(e, "question_paper"), link(e, "question_paper", "viewer_url"),
          link(e, "mark_scheme"), link(e, "mark_scheme", "viewer_url"), link(e, "examiner_report"),
          link(e, "pmt_model_answers")) for e in papers],
    )
    unlinked = conn.execute(
        "SELECT DISTINCT paper_id FROM questions "
        "WHERE paper_id NOT IN (SELECT paper_id FROM sources)").fetchall()
    if unlinked:
        raise ValueError(f"sources.json has no entry for paper(s) {[r[0] for r in unlinked]} "
                         "— rerun scripts/build_sources.py")
    return len(papers)


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
        expected_stem = paper_id_of(paper_data)
        if path.stem != expected_stem:
            raise ValueError(f"{path.name}: filename must match {expected_stem}.json")

        rows = [
            {
                "id": q["id"], "spec": q["spec"], "paper": q["paper"], "sitting": q["sitting"],
                "paper_id": expected_stem,
                "qualification": q.get("qualification", q["spec"]),
                "unit": q.get("unit", PURE_UNIT.get(q["paper"])),
                "component": q.get("component", "pure"),
                "status": q.get("status", "current" if q["spec"] == "9MA0" else "legacy"),
                "uses_large_data_set": int(q.get("uses_large_data_set", False)),
                "q_num": q["q_num"], "total_marks": q["total_marks"],
                "question_text": q["question_text"], "mark_scheme_text": q["mark_scheme_text"],
                "source_qp_file": q["source_qp_file"], "source_ms_file": q["source_ms_file"],
                "low_confidence": int(q.get("low_confidence", False)),
                "notes": q.get("notes", ""), "stem": q.get("stem"),
                "qp_first_page": (q.get("qp_pages") or [None])[0],
                "qp_last_page": (q.get("qp_pages") or [None, None])[-1],
                "has_figure": int(q.get("has_figure", False)),
                "figure_pages": json.dumps(q.get("figure_pages", [])),
            }
            for q in paper_data["questions"]
        ]
        conn.executemany(
            """INSERT INTO questions
               (id, spec, paper, sitting, paper_id, qualification, unit, component, status,
                uses_large_data_set, q_num, total_marks, question_text,
                mark_scheme_text, source_qp_file, source_ms_file, low_confidence, notes, stem,
                qp_first_page, qp_last_page, has_figure, figure_pages)
               VALUES (:id, :spec, :paper, :sitting, :paper_id, :qualification, :unit, :component,
                       :status, :uses_large_data_set, :q_num, :total_marks,
                       :question_text, :mark_scheme_text, :source_qp_file, :source_ms_file,
                       :low_confidence, :notes, :stem,
                       :qp_first_page, :qp_last_page, :has_figure, :figure_pages)""",
            rows,
        )
        for q in paper_data["questions"]:
            load_parts(conn, q, path.name)
        known_question_ids.update(r["id"] for r in rows)
        n_questions += len(rows)
    print(f"  loaded {n_questions} question(s) from {len(list(QUESTIONS_DIR.glob('*.json')))} paper file(s)")
    # Out-of-spec questions (data/processed/_excluded/) must never reach the chatbot.
    excluded_ids = {q["id"] for p in (PROCESSED_DIR / "_excluded").glob("*.json")
                    for q in json.loads(p.read_text()).get("questions", [])} | \
                   {f"{p.stem}_Q{x['q_num']}" for p in (PROCESSED_DIR / "_excluded").glob("*.json")
                    for x in json.loads(p.read_text()).get("summary", [])}
    leaked = excluded_ids & known_question_ids
    if leaked:
        raise ValueError(f"out-of-spec (excluded) questions found in questions/: {sorted(leaked)[:10]}")

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

    # --- sources: links to QP / MS / examiner report for each paper ---------
    n_sources = load_sources(conn)
    print(f"  loaded {n_sources} paper source link set(s)")

    # --- two-layer tags: question types (narrow) + part skills (broad) -----
    type_ids, skill_ids = load_vocabulary(conn)
    n_qt, n_sk, n_tagged_parts = load_tag_assignments(conn, type_ids, skill_ids)
    if n_qt:
        thin = conn.execute(
            "SELECT count(*) FROM question_parts qp WHERE (SELECT count(*) FROM question_tags t "
            "WHERE t.question_id = qp.question_id AND t.tag_type = 'skill' "
            "AND COALESCE(t.part_label, '') = COALESCE(qp.label, '')) < 2").fetchone()[0]
        total_parts = conn.execute("SELECT count(*) FROM question_parts").fetchone()[0]
        print(f"  loaded {len(type_ids)} question type(s), {len(skill_ids)} skill(s); "
              f"{n_qt} question(s) typed, {n_sk} skill tag(s) on {n_tagged_parts} part(s); "
              f"{total_parts - thin}/{total_parts} parts have >=2 skills")

    # --- examiner notes: verbatim quotes, checked against the source report --
    n_notes, n_perf = load_examiner_notes(conn, known_question_ids)
    print(f"  loaded {n_notes} examiner note(s), {n_perf} performance row(s)")

    conn.commit()
    conn.close()
    print(f"\nBuilt {DB_PATH.relative_to(PROCESSED_DIR.parent.parent)} — "
          f"{n_questions} question(s), {n_techniques} technique(s), "
          f"{n_topic_tags + n_technique_tags} tag(s) total.")


if __name__ == "__main__":
    main()
