"""Gather everything the tutor needs about a question, or about a generic query.

question_bundle(qid)  -> stem, parts (+ mark scheme, skills, examiner notes,
                         performance), question type, links, figures, and
                         pitfalls from *other* questions that test the same skills.
generic_bundle(text)  -> the skills, example parts, examiner notes and question
                         types that best match a free-text query.
On a commercial pack (pack.current().commercial) there are no examiner notes, performance data
or paper links: our own `pitfalls` rows take the notes' place (keys "pitfalls", "general_pitfalls").
Everything is plain dicts (JSON-serialisable) so the later FastAPI layer can
return it unchanged.
"""
import json
import sys

from . import db, pack
from .identify import summary
from .search import get_index

MAX_RELATED_NOTES_PER_PART = 3
RELEVANCE_MARGIN = 0.06  # topic search: keep skills within this cosine distance of the best match


def _skills() -> dict[str, dict]:
    return {r["id"]: dict(r) for r in db.rows(
        "SELECT s.id, s.title, s.group_id, s.description, s.formula_booklet, g.title AS group_title "
        "FROM skills s JOIN skill_groups g ON g.id = s.group_id")}


def part_skills(question_id: str) -> dict[str | None, list[str]]:
    out: dict[str | None, list[str]] = {}
    for r in db.rows("SELECT part_label, tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'skill'",
                     (question_id,)):
        out.setdefault(r["part_label"], []).append(r["tag_value"])
    return out


def _owning_part(note_label: str | None, labels: list[str | None]) -> str | None:
    """Map a note's label to the part it belongs to: "a(ii)" -> part "a"; "b" -> "b(i)" parts' parent."""
    if note_label is None:
        return None
    if note_label in labels:
        return note_label
    for l in labels:
        if l and note_label.startswith(l + "("):
            return l
    return None  # parent of several parts ("b" when parts are b(i), b(ii)) -> treat as question-level


def _note(r) -> dict:
    return {"id": r["id"], "kind": r["kind"], "text": r["display"] or r["quote"], "page": r["page"],
            "source": r["source_file"]}


def _pitfall(r) -> dict:
    return {"id": r["id"], "kind": "pitfall", "text": r["text"], "step": r["step"], "error_code": r["error_code"],
            "says_common": bool(r["says_common"])}


def _pitfalls(question_id: str) -> list:
    return (db.rows("SELECT * FROM pitfalls WHERE question_id = ? ORDER BY rowid", (question_id,))
            if db.has_table("pitfalls") else [])


def _performance(question_id: str) -> dict[str | None, dict]:
    out = {}
    for r in db.rows("SELECT p.*, COALESCE(n.display, n.quote) AS evidence FROM question_performance p "
                     "LEFT JOIN examiner_notes n ON n.id = p.evidence_note_id WHERE p.question_id = ?", (question_id,)):
        out[r["part_label"]] = {k: r[k] for k in ("mean_mark", "max_mark", "full_marks_pct", "rating", "evidence")
                                if r[k] is not None}
    return out


def related_notes(question_id: str, skill_ids: list[str], kinds=("pitfall",), limit=MAX_RELATED_NOTES_PER_PART) -> list[dict]:
    """Examiner notes on *other* questions' parts that test the same (non exam-technique) skills,
    ranked by how many skills they share."""
    skills = _skills()
    focus = [s for s in skill_ids if skills[s]["group_id"] != db.EXAM_TECHNIQUE_GROUP]
    if not focus:
        return []
    marks = ",".join("?" * len(focus))
    kind_marks = ",".join("?" * len(kinds))
    rows = db.rows(
        f"""SELECT n.*, count(DISTINCT t.tag_value) AS shared, group_concat(DISTINCT t.tag_value) AS via
            FROM examiner_notes n
            JOIN question_tags t ON t.question_id = n.question_id AND t.tag_type = 'skill'
                 AND t.tag_value IN ({marks})
                 AND (n.part_label IS NULL OR COALESCE(t.part_label, '') = n.part_label
                      OR n.part_label LIKE t.part_label || '(%')
            WHERE n.question_id != ? AND n.kind IN ({kind_marks}) AND n.part_label IS NOT NULL
            GROUP BY n.id ORDER BY shared DESC, n.question_id DESC LIMIT ?""",
        (*focus, question_id, *kinds, limit))
    return [dict(_note(r), question_id=r["question_id"], part_label=r["part_label"],
                 via_skills=r["via"].split(",")) for r in rows]


def related_pitfalls(question_id: str, skill_ids: list[str], limit=MAX_RELATED_NOTES_PER_PART) -> list[dict]:
    """Our pitfalls on *other* questions' parts that test the same (non exam-technique) skills,
    ranked by how many skills they share (related_notes() for a commercial pack)."""
    skills = _skills()
    focus = [s for s in skill_ids if skills[s]["group_id"] != db.EXAM_TECHNIQUE_GROUP]
    if not focus or not db.has_table("pitfalls"):
        return []
    marks = ",".join("?" * len(focus))
    rows = db.rows(
        f"""SELECT f.*, count(DISTINCT t.tag_value) AS shared, group_concat(DISTINCT t.tag_value) AS via
            FROM pitfalls f
            JOIN question_tags t ON t.question_id = f.question_id AND t.tag_type = 'skill'
                 AND t.tag_value IN ({marks})
                 AND (f.part_label IS NULL OR COALESCE(t.part_label, '') = f.part_label)
            WHERE f.question_id != ?
            GROUP BY f.id ORDER BY shared DESC, f.question_id DESC LIMIT ?""",
        (*focus, question_id, limit))
    return [dict(_pitfall(r), question_id=r["question_id"], part_label=r["part_label"],
                 via_skills=r["via"].split(",")) for r in rows]


def question_bundle(question_id: str, with_related: bool = True) -> dict:
    q = db.one("SELECT * FROM questions WHERE id = ?", (question_id,))
    if q is None:
        raise KeyError(question_id)
    skills = _skills()
    clean = pack.current().commercial
    src = None if clean else db.one("SELECT * FROM sources WHERE paper_id = ?", (q["paper_id"],))
    qtype = db.one("SELECT t.id, t.title, t.definition FROM question_tags g JOIN question_types t ON t.id = g.tag_value "
                   "WHERE g.question_id = ? AND g.tag_type = 'question_type'", (question_id,))
    topics = [r["tag_value"] for r in db.rows(
        "SELECT tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'topic'", (question_id,))]
    perf = {} if clean else _performance(question_id)
    pskills = part_skills(question_id)
    parts_rows = db.rows("SELECT * FROM question_parts WHERE question_id = ? ORDER BY part_index", (question_id,))
    labels = [p["label"] for p in parts_rows]
    notes_by_part: dict[str | None, list[dict]] = {}
    note_rows = _pitfalls(question_id) if clean else db.rows(
        "SELECT * FROM examiner_notes WHERE question_id = ? ORDER BY rowid", (question_id,))
    for r in note_rows:
        notes_by_part.setdefault(_owning_part(r["part_label"], labels), []).append(_pitfall(r) if clean else _note(r))

    parts = []
    for p in parts_rows:
        sk = pskills.get(p["label"], [])
        part = {
            "label": p["label"], "marks": p["marks"], "text": p["text"], "mark_scheme": p["mark_scheme"],
            "skills": [{"id": s, "title": skills[s]["title"], "group": skills[s]["group_title"],
                        "formula_booklet": bool(skills[s]["formula_booklet"])} for s in sk],
        }
        if clean:
            part.update(pitfalls=notes_by_part.get(p["label"], []),
                        related_pitfalls=related_pitfalls(question_id, sk) if with_related else [])
        else:
            part.update(examiner_notes=notes_by_part.get(p["label"], []), performance=perf.get(p["label"], {}),
                        related_pitfalls=related_notes(question_id, sk) if with_related else [])
        parts.append(part)
    first_page = q["qp_first_page"]
    bundle = {
        "question_id": question_id, "summary": summary(question_id),
        "paper": q["paper"], "sitting": q["sitting"], "q_num": q["q_num"], "total_marks": q["total_marks"],
        "stem": q["stem"], "question_type": dict(qtype) if qtype else None, "topics": topics,
    }
    if clean:  # our own items: no paper to link to (a single-part question's pitfalls are already on its part)
        return dict(bundle, general_pitfalls=notes_by_part.get(None, []) if labels != [None] else [], parts=parts,
                    has_figure=bool(q["has_figure"]), figure_pages=json.loads(q["figure_pages"] or "[]"), links={})
    return {
        **bundle,
        "performance": perf.get(None, {}),
        "general_examiner_notes": notes_by_part.get(None, []),
        "parts": parts,
        "has_figure": bool(q["has_figure"]), "figure_pages": json.loads(q["figure_pages"] or "[]"),
        "links": {
            "question_paper": src["qp_viewer_url"],
            "question_paper_page": f"{src['qp_url']}#page={first_page}" if first_page else src["qp_url"],
            "mark_scheme": src["ms_viewer_url"],
            "examiner_report": src["er_url"],
        },
    }


def figure_images(question_id: str) -> list[str]:
    """Paths of rendered figure pages (rendering on first use) to attach to the model call."""
    if pack.current().commercial:
        return []  # renders from the Pearson PDFs in data/; our own items' SVG figures aren't attached yet
    sys.path.insert(0, str(db.ROOT / "scripts"))
    import render_figure
    return [str(p) for p in render_figure.render(render_figure.load_question(question_id))]


def rank_skills(text: str, k: int = 5, part_votes: int = 0) -> list[str]:
    """Skills for a free-text query (semantic search over skill descriptions).

    part_votes > 0 also fuses in votes from the skills tagged on the best-matching exam parts.
    Evaluated 2026-09-25 (eval/retrieval.py): it fixes "integrate x e^x" but lowers MRR overall
    (0.86 vs 0.94) and recall@5 (95% vs 100%), so it is off by default."""
    ix = get_index()
    hits = ix.search(text, "skill", k=30)
    groups = {r["id"]: r["group_id"] for r in db.rows("SELECT id, group_id FROM skills")}
    # Topic questions are about maths content: skip exam-technique skills ("show that", "hence"...)
    # and anything clearly less relevant than the best match, rather than always padding to k.
    top = hits[0].semantic if hits else 0.0
    direct = [h.doc_id.split(":", 1)[1] for h in hits
              if groups[h.doc_id.split(":", 1)[1]] != db.EXAM_TECHNIQUE_GROUP and h.semantic >= top - RELEVANCE_MARGIN]
    if not part_votes:
        return direct[:k]
    votes: dict[str, float] = {}
    for rank, h in enumerate(ix.search(text, "part", k=part_votes)):
        qid, label = db.split_part_key(h.doc_id.split(":", 1)[1])
        for sk in part_skills(qid).get(label, []):
            votes[sk] = votes.get(sk, 0.0) + 1.0 / (rank + 1)
    voted = sorted(votes, key=lambda s: -votes[s])
    fused: dict[str, float] = {}
    for ranking in (direct, voted):
        for r, sk in enumerate(ranking):
            fused[sk] = fused.get(sk, 0.0) + 1.0 / (60 + r + 1)
    return sorted(fused, key=lambda s: -fused[s])[:k]


def generic_bundle(text: str, k_skills: int = 4, k_parts: int = 3, k_notes: int = 5) -> dict:
    """For a free-text query: matching skills (each with a few example parts, easiest first),
    examiner notes and question types."""
    from .recommend import parts_with_skill  # avoid a circular import at module load
    ix = get_index()
    skills = _skills()
    skill_ids = rank_skills(text, k=k_skills)
    out = {
        "query": text,
        "skills": [{
            "id": sid, "title": skills[sid]["title"], "description": skills[sid]["description"],
            "formula_booklet": bool(skills[sid]["formula_booklet"]),
            "example_parts": parts_with_skill(sid, limit=k_parts),
        } for sid in skill_ids],
    }
    if pack.current().commercial:  # our pitfalls are indexed as kind "note" (search.documents)
        rows = (db.one("SELECT * FROM pitfalls WHERE id = ?", (h.doc_id.split(":", 1)[1],))
                for h in ix.search(text, "note", k=k_notes))
        return dict(out, pitfalls=[dict(_pitfall(r), question_id=r["question_id"], part_label=r["part_label"])
                                   for r in rows],
                    question_types=[h.doc_id.split(":", 1)[1] for h in ix.search(text, "qtype", k=3)])
    return {
        **out,
        "examiner_notes": [dict(_note(r), question_id=r["question_id"], part_label=r["part_label"])
                           for r in (db.one("SELECT * FROM examiner_notes WHERE id = ?", (h.doc_id.split(":", 1)[1],))
                                     for h in ix.search(text, "note", k=k_notes))],
        "question_types": [h.doc_id.split(":", 1)[1] for h in ix.search(text, "qtype", k=3)],
    }
