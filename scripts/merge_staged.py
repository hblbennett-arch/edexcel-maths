#!/usr/bin/env python3
"""One-time (but re-runnable) merge: takes the raw per-paper extraction output
in data/processed/_agent_staging/*.json and restructures it into the final
layout:

    data/processed/questions/<paper>_<sitting>.json   -- pure content, per paper
    data/processed/topics/<topic-id>.json              -- {_topic, question_ids}
    data/processed/techniques/<technique-id>.json      -- {id, title, content, contrast_with, question_ids}

Content lives exactly once (per paper). Topic/technique files are just lists
of question ids — this is how a question can carry multiple topic tags
without duplicating its content across multiple files.

tags.json must already contain the full controlled vocabulary before running
this (topics + techniques) — the merge validates every tag against it.

Run again whenever new staged extractions are added; it's idempotent (it
recomputes topics/*.json and techniques/*.json from scratch each time, and
overwrites the questions/*.json for any paper present in staging).

WARNING (retired after the initial 14-paper extraction): topics/*.json and
techniques/*.json are rebuilt ONLY from papers currently in staging, so a
rerun with a partial staging folder would wipe the tags of every other paper
and any hand corrections. It therefore refuses to run over existing tag files
unless --force is passed. For small changes, edit the JSON files directly and
rerun scripts/build_db.py instead.
"""
import json
import sys
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
STAGING_DIR = PROCESSED_DIR / "_agent_staging"
TAGS_PATH = PROCESSED_DIR / "tags.json"
QUESTIONS_DIR = PROCESSED_DIR / "questions"
TOPICS_DIR = PROCESSED_DIR / "topics"
TECHNIQUES_DIR = PROCESSED_DIR / "techniques"

# Rename map for techniques that turned out to be duplicates across papers
# (same method, proposed independently by different extraction passes).
TECHNIQUE_ID_ALIASES = {
    "linearise-power-law-with-logs": "log-linearise-power-law-model",
}


def main() -> None:
    if any(TOPICS_DIR.glob("*.json")) and "--force" not in sys.argv:
        raise SystemExit(
            f"{TOPICS_DIR} already has tag files; rerunning would overwrite them "
            "(including hand corrections). Pass --force if that is really intended."
        )

    tags = json.loads(TAGS_PATH.read_text())
    valid_topics = {t["id"] for t in tags["topics"]}
    valid_techniques = {t["id"]: t for t in tags["techniques"]}

    QUESTIONS_DIR.mkdir(exist_ok=True)
    TOPICS_DIR.mkdir(exist_ok=True)
    TECHNIQUES_DIR.mkdir(exist_ok=True)

    topic_question_ids = {tid: [] for tid in valid_topics}
    technique_question_ids = {tid: [] for tid in valid_techniques}
    technique_content = {}  # id -> {title, content, contrast_with} from any paper that proposed it

    staged_files = sorted(STAGING_DIR.glob("*.json"))
    if not staged_files:
        raise SystemExit(f"No staged files found in {STAGING_DIR}")

    for path in staged_files:
        data = json.loads(path.read_text())
        paper, sitting, spec = data["paper"], data["sitting"], data["spec"]

        content_questions = []
        for q in data["questions"]:
            qid = f"{paper}_{sitting}_Q{q['q_num']}"
            content_questions.append({
                "id": qid,
                "spec": spec,
                "paper": paper,
                "sitting": sitting,
                "q_num": q["q_num"],
                "total_marks": q["total_marks"],
                "question_text": q["question_text"],
                "mark_scheme_text": q["mark_scheme_text"],
                "source_qp_file": data["source_qp_file"],
                "source_ms_file": data["source_ms_file"],
                "low_confidence": q.get("low_confidence", False),
                "notes": q.get("notes", ""),
            })

            for topic_id in q["topics"]:
                if topic_id not in valid_topics:
                    raise ValueError(f"{path.name} / {qid}: unknown topic '{topic_id}'")
                topic_question_ids[topic_id].append(qid)

            for tech_id in q.get("techniques", []):
                tech_id = TECHNIQUE_ID_ALIASES.get(tech_id, tech_id)
                if tech_id not in valid_techniques:
                    raise ValueError(f"{path.name} / {qid}: unknown technique '{tech_id}'")
                technique_question_ids[tech_id].append(qid)

        # techniques this paper proposed (their content — id already aliased if a dup)
        for prop in data.get("proposed_new_techniques", []):
            tid = TECHNIQUE_ID_ALIASES.get(prop["id"], prop["id"])
            if tid not in valid_techniques:
                raise ValueError(
                    f"{path.name}: proposed technique '{tid}' not present in tags.json — "
                    f"add it to tags.json before merging."
                )
            technique_content[tid] = {
                "title": prop["title"],
                "content": prop["content"],
                "contrast_with": prop.get("contrast_with", ""),
            }

        out_path = QUESTIONS_DIR / f"{paper}_{sitting}.json"
        out_path.write_text(json.dumps({
            "_paper": paper,
            "_sitting": sitting,
            "spec": spec,
            "source_qp_file": data["source_qp_file"],
            "source_ms_file": data["source_ms_file"],
            "questions": content_questions,
        }, indent=2))
        print(f"  wrote {out_path.relative_to(PROCESSED_DIR.parent.parent)} "
              f"({len(content_questions)} questions)")

    # --- write topic files (only for topics that actually have questions) ---
    n_topic_files = 0
    for topic_id, qids in topic_question_ids.items():
        if not qids:
            continue
        out_path = TOPICS_DIR / f"{topic_id}.json"
        out_path.write_text(json.dumps({
            "_topic": topic_id,
            "question_ids": qids,
        }, indent=2))
        n_topic_files += 1
    print(f"\n  wrote {n_topic_files} topic file(s) to {TOPICS_DIR.relative_to(PROCESSED_DIR.parent.parent)}/")

    # --- write technique files (only for techniques that have questions AND known content) ---
    n_tech_files = 0
    for tech_id, qids in technique_question_ids.items():
        if not qids:
            continue
        meta = valid_techniques[tech_id]
        content = technique_content.get(tech_id)
        if content is None:
            # one of the three original seed techniques - content already on disk, leave it
            existing_path = TECHNIQUES_DIR / f"{tech_id}.json"
            if not existing_path.exists():
                raise ValueError(
                    f"Technique '{tech_id}' is used by questions but has no content "
                    f"(no proposed_new_techniques entry and no existing file)."
                )
            existing = json.loads(existing_path.read_text())
            existing["question_ids"] = qids
            existing_path.write_text(json.dumps(existing, indent=2))
        else:
            out_path = TECHNIQUES_DIR / f"{tech_id}.json"
            out_path.write_text(json.dumps({
                "id": tech_id,
                "title": content["title"],
                "content": content["content"],
                "contrast_with": content["contrast_with"],
                "question_ids": qids,
            }, indent=2))
        n_tech_files += 1
    print(f"  wrote/updated {n_tech_files} technique file(s) to {TECHNIQUES_DIR.relative_to(PROCESSED_DIR.parent.parent)}/")

    total_questions = sum(len(json.loads(p.read_text())["questions"]) for p in QUESTIONS_DIR.glob("*.json"))
    print(f"\nMerge complete: {len(staged_files)} papers, {total_questions} questions total.")


if __name__ == "__main__":
    main()
