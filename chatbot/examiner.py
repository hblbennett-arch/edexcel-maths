""""Be the examiner" (docs/market-research-product-strategy.md §4.2, feature 1): the student marks one of our
scripted answers mark by mark, then sees our verdict and the convention behind each mark.

Everything here is deterministic and uses no model. The exercises are the G4 scripted answers stored on each
clean item (`gate_results.G4.responses`): a response is usable when the G4 marker agreed with its designed vector
(`agreed`) or both markers agreed on a different vector (`consistent`); `mismatched` responses are skipped.

    from chatbot import examiner
    items = examiner.load_items()                 # clean items passing G1..G8 (pack.db first, item files otherwise)
    exs = examiner.exercises(items)               # one exercise per usable script
    ex = examiner.pick_next(exs, done_ids=set())  # deterministic, varied
    fb = examiner.reveal(ex, judgements)          # per-mark verdicts, score, summary, lesson
    examiner.record(user_id, ex, judgements)      # -> events.db, one event per part

Reads only content/clean/items/*.json (or content/clean/pack.db) and content/boards/*.json: our own content.
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
from functools import lru_cache
from pathlib import Path

from . import events, marks

ROOT = Path(__file__).resolve().parent.parent
ITEMS_DIR = ROOT / "content" / "clean" / "items"
PACK_DB = ROOT / "content" / "clean" / "pack.db"
GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
KINDS = ("correct", "pitfall", "alternative", "partial")
# The order kinds are offered in when the student has no preference: pitfalls are most of the bank, so they
# appear most often, but a fully correct script or a partial attempt turns up regularly to stop "always withhold"
ROTATION = ("pitfall", "correct", "pitfall", "partial", "pitfall", "alternative")
# Which convention a slip is blamed on when several apply (a lost dM1 is about dependency before it is about M)
LESSON_PRIORITY = ("dependency", "ft", "show_that", "cso", "cao", "dM", "ddM", "A", "M", "B", "dB", "bald_answer")


# ---------------------------------------------------------------------------------------------------- items

def norm_label(label) -> str:
    """'(a)', 'Part a', 'a' -> 'a'; '(b)(i)' -> 'bi'; None / '-' -> '-'.  (Same rule as the G4 gate.)"""
    t = re.sub(r"(?i)^part\s*", "", str(label or "-"))
    return re.sub(r"[()\s]", "", t).lower() or "-"


def passes_all_gates(gate_results: dict | None) -> bool:
    gr = gate_results or {}
    return all((gr.get(g) or {}).get("pass") is True for g in GATES)


def question_text(item: dict) -> str:
    lines = [item.get("stem") or ""] + [(f"({p['label']}) " if p.get("label") else "") + p["text"] for p in item["parts"]]
    return "\n\n".join(l for l in lines if l)


def _parse_scheme_text(text: str) -> list[dict]:
    """Inverse of build_pack's 'CODE for [notes]' lines, for items that exist only in a pack."""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(\S+)\s+(.*?)\s*$", line)
        if not m or marks.try_parse(m.group(1)) is None:
            continue
        code, rest, notes = m.group(1), m.group(2), ""
        if rest.endswith("]") and " [" in rest:
            rest, notes = rest.rsplit(" [", 1)
            notes = notes[:-1]
        out.append({"code": code, "for": rest, "notes": notes})
    return out


def _items_from_pack(path: Path, items_dir: Path) -> list[dict] | None:
    """Items whose gate results live in a pack DB. The item file (which also holds the alternatives) is used for
    the fields when it exists; otherwise the item is rebuilt from questions / question_parts / question_tags /
    pitfalls. Returns None when the pack has no questions, so the caller falls back to item files."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    conn.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"questions", "question_parts"} <= tables:
            return None
        cols = {r[1] for r in conn.execute("PRAGMA table_info(questions)")}
        if "gate_results" not in cols or not conn.execute("SELECT 1 FROM questions LIMIT 1").fetchone():
            return None
        out = []
        for q in conn.execute("SELECT * FROM questions WHERE gate_results IS NOT NULL ORDER BY id"):
            try:
                gr = json.loads(q["gate_results"] or "{}")
            except json.JSONDecodeError:
                continue
            f = items_dir / f"{q['id']}.json"
            if f.exists():
                item = json.loads(f.read_text())
                item["gate_results"] = gr
                out.append(item)
                continue
            parts = []
            for p in conn.execute("SELECT * FROM question_parts WHERE question_id = ? ORDER BY part_index", (q["id"],)):
                skills = [r[0] for r in conn.execute(
                    "SELECT tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'skill' AND "
                    "COALESCE(part_label, '') = COALESCE(?, '')", (q["id"], p["label"]))] if "question_tags" in tables else []
                parts.append({"label": p["label"], "marks": p["marks"], "text": p["text"],
                              "mark_scheme": _parse_scheme_text(p["mark_scheme"]), "alternatives": [], "skills": skills})
            pitfalls = [{"part": r["part_label"], "step": r["step"], "error_code": r["error_code"], "text": r["text"],
                         "says_common": bool(r["says_common"])}
                        for r in conn.execute("SELECT * FROM pitfalls WHERE question_id = ?", (q["id"],))] if "pitfalls" in tables else []
            out.append({"id": q["id"], "stem": q["stem"], "component": q["component"], "parts": parts,
                        "pitfalls": pitfalls, "gate_results": gr,
                        "question_type": next((r[0] for r in conn.execute(
                            "SELECT tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'question_type'",
                            (q["id"],))), None) if "question_tags" in tables else None})
        return out
    finally:
        conn.close()


def load_items(items_dir: Path | None = None, pack_db: Path | None = None) -> list[dict]:
    """Clean items whose gates G1..G8 all pass. A pack DB with questions is preferred; the item files are the
    fallback (and what exists today)."""
    items_dir = items_dir or ITEMS_DIR
    pack_db = PACK_DB if pack_db is None else pack_db
    items = _items_from_pack(pack_db, items_dir) if pack_db and pack_db.exists() else None
    if items is None:
        items = []
        for f in sorted(items_dir.glob("*.json")):
            try:
                items.append(json.loads(f.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
    return [it for it in items if it.get("parts") and passes_all_gates(it.get("gate_results"))]


# ------------------------------------------------------------------------------------------------ exercises

def exercise_key(item_id: str, script_id: str) -> str:
    return f"{item_id}::{script_id}"


def _reference_vector(g4: dict, response: dict) -> list[dict] | None:
    rid = response.get("id")
    if rid in (g4.get("agreed") or []):
        return response.get("designed")
    if rid in (g4.get("consistent") or {}):
        return g4["consistent"][rid]
    return None  # mismatched, or never marked


def _scheme_for(part: dict, vec_codes: list[str], kind: str) -> tuple[list[dict], str | None] | None:
    """The scheme lines the vector was marked against: an alternative 'Way' for an alternative-method script
    whose vector fits it, otherwise the main scheme; None when nothing has the vector's length."""
    main = part.get("mark_scheme") or []
    alts = [a for a in part.get("alternatives") or [] if len(a.get("marks") or []) == len(vec_codes)]
    if kind == "alternative" and alts:
        return alts[0]["marks"], alts[0].get("name") or "Alternative method"
    if len(main) == len(vec_codes):
        return main, None
    if alts:
        return alts[0]["marks"], alts[0].get("name") or "Alternative method"
    return None


def _pitfall_texts(item: dict, error_code: str | None) -> list[dict]:
    if not error_code:
        return []
    matching = [pf for pf in item.get("pitfalls") or [] if pf.get("error_code") == error_code and pf.get("text")]
    # An item may describe two slips under one error code; the script is linked to the code only, so the pitfall
    # at the earliest solution step is treated as the one the first lost mark shows (sorted first)
    matching.sort(key=lambda pf: (pf.get("step") if isinstance(pf.get("step"), int) else 99))
    return [{"part": norm_label(pf.get("part")), "step": pf.get("step"), "text": pf["text"]} for pf in matching]


def exercises(items: list[dict]) -> list[dict]:
    """One exercise per usable G4 script, with the reference vector aligned to the scheme lines of each part."""
    out = []
    for item in items:
        g4 = (item.get("gate_results") or {}).get("G4") or {}
        parts_by_label = {norm_label(p.get("label")): p for p in item["parts"]}
        for r in g4.get("responses") or []:
            vec = _reference_vector(g4, r)
            if not vec or not r.get("work") or r.get("kind") not in KINDS:
                continue
            by_label = {norm_label(v.get("part")): [str(m) for m in v.get("marks") or []] for v in vec}
            if set(by_label) != set(parts_by_label):
                continue
            parts, ok = [], True
            for p in item["parts"]:
                codes = by_label[norm_label(p.get("label"))]
                found = _scheme_for(p, codes, r["kind"])
                if found is None:
                    ok = False
                    break
                lines, way = found
                try:
                    reference = [marks.parse(c).awarded for c in codes]
                except ValueError:
                    ok = False
                    break
                parts.append({"label": norm_label(p.get("label")), "marks": p["marks"], "text": p["text"],
                              "way": way, "skills": list(p.get("skills") or []),
                              "lines": [{"code": ln["code"], "for": ln.get("for", ""), "notes": ln.get("notes") or ""}
                                        for ln in lines],
                              "reference": reference})
            if not ok:
                continue
            out.append({"key": exercise_key(item["id"], r["id"]), "item_id": item["id"], "script_id": r["id"],
                        "kind": r["kind"], "error_code": r.get("error_code") if r["kind"] == "pitfall" else None,
                        "component": item.get("component"), "question_type": item.get("question_type"),
                        "tier": item.get("tier"), "stem": item.get("stem") or "", "question": question_text(item),
                        "work": r["work"], "parts": parts,
                        "pitfalls": _pitfall_texts(item, r.get("error_code")) if r["kind"] == "pitfall" else [],
                        "total_marks": sum(p["marks"] for p in item["parts"])})
    return out


@lru_cache(maxsize=1)
def all_exercises() -> tuple[dict, ...]:
    return tuple(exercises(load_items()))


def find(item_id: str, script_id: str) -> dict | None:
    key = exercise_key(item_id, script_id)
    return next((e for e in all_exercises() if e["key"] == key), None)


def public_view(exercise: dict) -> dict:
    """What the browser may see before the student has marked: no reference, no verdicts, no giveaways."""
    hide = {"reference"}
    return {**{k: v for k, v in exercise.items() if k not in ("kind", "error_code", "pitfalls")},
            "parts": [{k: v for k, v in p.items() if k not in hide} for p in exercise["parts"]]}


# --------------------------------------------------------------------------------------------------- reveal

def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return " ".join(parts[:n]).strip()


def _name(m: marks.Mark) -> str:
    conv = marks.profile().convention(m.convention_key)
    return (conv.get("name") or m.kind.replace("_", " ").title()).lower()


def _check_shape(exercise: dict, judgements: list[list[bool]]) -> None:
    if not isinstance(judgements, list) or len(judgements) != len(exercise["parts"]):
        raise ValueError(f"expected judgements for {len(exercise['parts'])} part(s)")
    for p, j in zip(exercise["parts"], judgements):
        if not isinstance(j, list) or len(j) != len(p["lines"]) or any(not isinstance(x, bool) for x in j):
            raise ValueError(f"part {p['label']}: expected {len(p['lines'])} true/false judgements")


def reveal(exercise: dict, judgements: list[list[bool]]) -> dict:
    """Our verdict on the student's marking: per part per mark, plus a summary, a score and one lesson line."""
    _check_shape(exercise, judgements)
    b = marks.profile()
    parts_out, summaries = [], []
    n_correct = n_total = 0
    lesson_counts: dict[str, int] = {}
    pitfall_pending = bool(exercise.get("kind") == "pitfall" and exercise.get("pitfalls"))
    for p, judged_part in zip(exercise["parts"], judgements):
        codes = [ln["code"] for ln in p["lines"]]
        ref = p["reference"]
        implied = set(marks.implied_losses(codes, ref, b))
        links = marks.chain(codes, b)
        rows = []
        for i, (ln, code, r, j) in enumerate(zip(p["lines"], codes, ref, judged_part)):
            m = marks.parse(code, b)
            correct = (j == r)
            n_total += 1
            n_correct += int(correct)
            name = _name(m)
            deps = links[i]["depends_on"]
            dep_text = ""
            if i in implied and deps:
                lost_dep = next((d for d in deps if not ref[d]), deps[0])
                dep_text = (f"This mark was unavailable because the {codes[lost_dep]} before it (mark {lost_dep + 1}) "
                            f"was lost, and a {b.notation.get(m.kind, m.kind)} mark depends on it.")
            if correct and r:
                text = f"Agreed: the {name} was earned. The scheme gives it for: {ln['for']}"
            elif correct and not r:
                text = f"Agreed: the {name} was not earned. It needed: {ln['for']}"
                if dep_text:
                    text += f" {dep_text}"
            elif j and not r:  # the student awarded a mark the script did not earn
                text = f"Not earned. The scheme gives this {code} for: {ln['for']}"
                if ln.get("notes"):
                    text += f" ({ln['notes'].rstrip('.')})"
                text += f". Convention: {marks.explain(code, b, part='short')}"
                if dep_text:
                    text += f" {dep_text}"
            else:  # the student withheld a mark the script did earn
                text = (f"Earned: the condition for this {code} was met ({ln['for']}). "
                        f"{_first_sentences(marks.explain(code, b, part='explain'))}")
            row = {"code": code, "kind": m.kind, "family": m.family, "for": ln["for"], "notes": ln.get("notes", ""),
                   "reference": r, "judged": j, "correct": correct, "implied": i in implied, "explanation": text}
            if pitfall_pending and not r:
                same_part = [pf for pf in exercise["pitfalls"] if pf["part"] == p["label"]]
                row["pitfall"] = (same_part or exercise["pitfalls"])[0]["text"]
                pitfall_pending = False
            if not correct:
                keys = [m.convention_key]
                if i in implied:
                    keys.append("dependency")
                if m.ft:
                    keys.append("ft")
                if m.show_that:
                    keys.append("show_that")
                if m.cso:
                    keys.append("cso")
                if m.cao:
                    keys.append("cao")
                for k in keys:
                    lesson_counts[k] = lesson_counts.get(k, 0) + 1
            rows.append(row)
        awarded_codes = [c if r else marks.withheld(c, b) for c, r in zip(codes, ref)]
        summaries.append({"label": p["label"], "way": p.get("way"), **marks.vector_summary(codes, awarded_codes, b)})
        parts_out.append({"label": p["label"], "marks": p["marks"], "way": p.get("way"), "rows": rows})
    lesson = None
    if lesson_counts:
        key = max(lesson_counts, key=lambda k: (lesson_counts[k], -LESSON_PRIORITY.index(k) if k in LESSON_PRIORITY else -99))
        conv = b.convention(key)
        lesson = {"key": key, "name": conv.get("name", key), "short": conv.get("short", ""),
                  "write_to_earn": conv.get("write_to_earn", ""),
                  "text": f"{conv.get('name', key)}: {conv.get('short', '')}".strip()}
    earned = sum(s["earned"] for s in summaries)
    total = sum(s["total"] for s in summaries)
    return {"item_id": exercise["item_id"], "script_id": exercise["script_id"], "kind": exercise["kind"],
            "error_code": exercise.get("error_code"), "parts": parts_out, "summary": summaries,
            "script_score": {"earned": earned, "total": total},
            "score": {"correct": n_correct, "total": n_total, "rate": round(n_correct / n_total, 3) if n_total else None},
            "lesson": lesson}


def to_decisions(exercise: dict, judgements: list[list[bool]]) -> list[dict]:
    """Flat list of decisions for events.record (each carries its part label; record() groups by part)."""
    _check_shape(exercise, judgements)
    out = []
    for p, judged_part in zip(exercise["parts"], judgements):
        skill = (p.get("skills") or [None])[0]
        for ln, r, j in zip(p["lines"], p["reference"], judged_part):
            m = marks.parse(ln["code"])
            out.append({**m.as_dict(), "awarded": r, "user_judgement": j,
                        "error_code": exercise.get("error_code") if not r else None, "skill": skill,
                        "evidence": None, "reason": ln["for"], "part": p["label"]})
    return out


def record(user_id: str, exercise: dict, judgements: list[list[bool]], *, conn=None) -> list[str]:
    """Store the student's marking: one be-the-examiner event per part. Returns the event ids."""
    decisions = to_decisions(exercise, judgements)
    ids = []
    for p in exercise["parts"]:
        decs = [{k: v for k, v in d.items() if k != "part"} for d in decisions if d["part"] == p["label"]]
        ids.append(events.record(user_id, "be-the-examiner", exercise["item_id"],
                                 None if p["label"] == "-" else p["label"], decs,
                                 board=marks.profile().id, script_id=exercise["script_id"],
                                 meta={"kind": exercise["kind"], "error_code": exercise.get("error_code")}, conn=conn))
    return ids


# ------------------------------------------------------------------------------------------------ sequencing

def pick_next(exercises: list[dict] | tuple[dict, ...], done_ids: set, prefer_kind: str | None = None) -> dict | None:
    """The next exercise: deterministic for a given set of done keys, alternating kinds and avoiding items the
    student has already seen while any unseen item remains. None when everything is done."""
    remaining = [e for e in exercises if e["key"] not in done_ids]
    if not remaining:
        return None
    n_done = len(done_ids)
    rng = random.Random(n_done * 7919 + len(remaining))
    kind = prefer_kind if prefer_kind in KINDS else ROTATION[n_done % len(ROTATION)]
    pool = [e for e in remaining if e["kind"] == kind] or remaining
    done_items = {k.split("::", 1)[0] for k in done_ids}
    fresh = [e for e in pool if e["item_id"] not in done_items]
    if not fresh:  # every item of that kind seen: prefer any unseen item at all, then anything
        fresh = [e for e in remaining if e["item_id"] not in done_items] or pool
    return rng.choice(sorted(fresh, key=lambda e: e["key"]))
