#!/usr/bin/env python3
"""Build the clean (commercial) content pack database from our own files only.

    .venv/bin/python scripts/clean/build_pack.py            # -> content/clean/pack.db, then the licence gate

Inputs (all original work, nothing Pearson-written):
    content/clean/tags.json          skill / question-type vocabulary (our taxonomy)
    content/clean/items/*.json       reviewed, generated items (format: docs/clean-room-pipeline.md)
Only items whose review decision is accept/edit are loaded. The build fails if the licence gate
(scripts/clean/check_provenance.py) finds any problem.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_db  # noqa: E402
import check_provenance  # noqa: E402
from chatbot import pack as packs  # noqa: E402

PROV_FIELDS = ("provenance", "blueprint_id", "generator_model", "generated_at", "gate_results",
               "reviewed_by", "reviewed_at", "review_decision", "review_notes")


def _prov(item: dict) -> dict:
    review = item.get("review") or {}
    return {"provenance": item.get("provenance"), "blueprint_id": item.get("blueprint_id"),
            "generator_model": item.get("generator_model"), "generated_at": item.get("generated_at"),
            "gate_results": json.dumps(item.get("gate_results") or {}),
            "reviewed_by": review.get("by"), "reviewed_at": review.get("at"),
            "review_decision": review.get("decision"), "review_notes": review.get("notes")}


def load_item(conn: sqlite3.Connection, item: dict, type_ids: set[str], skill_ids: set[str]) -> None:
    qid, prov = item["id"], _prov(item)
    if item["question_type"] not in type_ids:
        raise ValueError(f"{qid}: unknown question_type {item['question_type']!r}")
    parts = item["parts"]
    total = sum(p["marks"] for p in parts)
    ms_text = "\n".join(f"({p['label']}) " * bool(p.get("label")) + "\n".join(
        f"{m['code']} {m['for']}" + (f" [{m['notes']}]" if m.get("notes") else "") for m in p["mark_scheme"])
        for p in parts)
    q_text = "\n".join(filter(None, [item.get("stem")] + [p["text"] for p in parts]))
    conn.execute(
        f"INSERT INTO questions (id, spec, paper, sitting, paper_id, qualification, unit, component, status, "
        f"q_num, total_marks, question_text, mark_scheme_text, stem, has_figure, figure_pages, {', '.join(PROV_FIELDS)}) "
        f"VALUES (?, '9MA0', ?, 'original', ?, 'original', NULL, ?, 'current', ?, ?, ?, ?, ?, ?, '[]', "
        f"{', '.join('?' * len(PROV_FIELDS))})",
        (qid, item.get("paper", "bank"), item.get("set", "bank"), item["component"], item.get("q_num", qid), total,
         q_text, ms_text, item.get("stem"), int(bool(item.get("figure_svg"))), *prov.values()))
    conn.execute("INSERT INTO question_tags (question_id, part_label, tag_type, tag_value) VALUES (?, NULL, "
                 "'question_type', ?)", (qid, item["question_type"]))
    for i, p in enumerate(parts):
        unknown = [s for s in p["skills"] if s not in skill_ids]
        if unknown:
            raise ValueError(f"{qid}:{p.get('label')}: unknown skill(s) {unknown}")
        ms = "\n".join(f"{m['code']} {m['for']}" + (f" [{m['notes']}]" if m.get("notes") else "")
                       for m in p["mark_scheme"])
        conn.execute(f"INSERT INTO question_parts (question_id, part_index, label, marks, text, mark_scheme, "
                     f"{', '.join(PROV_FIELDS)}) VALUES (?, ?, ?, ?, ?, ?, {', '.join('?' * len(PROV_FIELDS))})",
                     (qid, i, p.get("label"), p["marks"], p["text"], ms, *prov.values()))
        conn.executemany("INSERT INTO question_tags (question_id, part_label, tag_type, tag_value) "
                         "VALUES (?, ?, 'skill', ?)", [(qid, p.get("label"), s) for s in p["skills"]])
    for j, pf in enumerate(item.get("pitfalls", [])):
        conn.execute(f"INSERT INTO pitfalls (id, question_id, part_label, step, error_code, text, says_common, "
                     f"{', '.join(PROV_FIELDS)}) VALUES (?, ?, ?, ?, ?, ?, ?, {', '.join('?' * len(PROV_FIELDS))})",
                     (f"{qid}_p{j + 1}", qid, pf.get("part"), pf.get("step"), pf.get("error_code"), pf["text"],
                      int(bool(pf.get("says_common"))), *prov.values()))


def main() -> int:
    p = packs.load("clean")
    p.db.unlink(missing_ok=True)
    conn = sqlite3.connect(p.db)
    packs.create_schema(conn)
    type_ids, skill_ids = build_db.load_vocabulary(conn, p.tags)
    n = skipped = 0
    for path in sorted((p.dir / "items").glob("*.json")):
        item = json.loads(path.read_text())
        if (item.get("review") or {}).get("decision") not in ("accept", "edit"):
            skipped += 1
            continue
        load_item(conn, item, type_ids, skill_ids)
        n += 1
    conn.commit()
    conn.close()
    print(f"built {p.db.relative_to(ROOT)}: {len(skill_ids)} skills, {len(type_ids)} question types, "
          f"{n} item(s) loaded, {skipped} not (yet) accepted")
    problems = check_provenance.check(p)
    print("licence gate:", "PASS" if not problems else f"FAIL ({len(problems)})")
    for line in problems[:20]:
        print("   ", line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
