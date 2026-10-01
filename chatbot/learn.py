""""Learn" layer views (docs/learn-layer-spec.md): one question read three ways, plus the playbooks.

Everything here is deterministic and uses no model. It reads our own content only:
    content/clean/items/*.json (or pack.db)   gate-passed items, with optional parts[i].solution_levels / scenes
    content/clean/scenes/<item_id>.json       optional interactive scenes (written by a separate pipeline)
    content/clean/playbooks/*.json            one playbook per question type
    content/clean/tags.json, content/error_codes.json, content/boards/<id>.json

    from chatbot import learn
    learn.catalogue()          # gate-passed items grouped by component
    learn.item_view(item_id)   # everything the /learn?item= page shows
    learn.playbook_index()     # [{id, title, topic, component, n_leaks, has_items}]
    learn.playbook(type_id)    # the playbook file plus resolved titles, definitions and practice items

Items are re-read on every call (no cache): other pipelines add solution_levels and scenes to the files while the
server runs, and the page should pick them up on refresh.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import examiner, marks

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "content" / "clean" / "scenes"
PLAYBOOKS_DIR = ROOT / "content" / "clean" / "playbooks"
TAGS_PATH = ROOT / "content" / "clean" / "tags.json"
ERROR_CODES_PATH = ROOT / "content" / "error_codes.json"
COMPONENT_ORDER = ("pure", "stats", "statistics", "mech", "mechanics")
THIN_TYPE_QUESTIONS = 5  # a playbook built from fewer source questions than this is marked "indicative"


# ------------------------------------------------------------------------------------------------ lookups

def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _tags() -> dict:
    return _read_json(TAGS_PATH) or {}


def question_types() -> dict:
    """id -> {id, title, topic, topic_title, component, definition}."""
    tags = _tags()
    topics = {t["id"]: t for t in tags.get("topics", []) if t.get("id")}
    out = {}
    for q in tags.get("question_types", []):
        if not q.get("id"):
            continue
        topic = topics.get(q.get("topic") or "", {})
        out[q["id"]] = {"id": q["id"], "title": q.get("title") or q["id"].replace("-", " ").capitalize(),
                        "topic": q.get("topic"), "topic_title": topic.get("title") or (q.get("topic") or "").replace("-", " ").title(),
                        "component": topic.get("component"), "definition": q.get("definition") or ""}
    return out


def skill_titles() -> dict:
    return {s["id"]: s.get("title") or s["id"] for s in _tags().get("skills", []) if s.get("id")}


def error_code_definitions() -> dict:
    d = _read_json(ERROR_CODES_PATH) or {}
    return {c["id"]: c.get("definition", "") for c in d.get("codes", []) if c.get("id")}


def _type_title(type_id: str | None, types: dict | None = None) -> str:
    t = (types if types is not None else question_types()).get(type_id or "")
    return t["title"] if t else (type_id or "").replace("-", " ").capitalize()


def _convention_short(code: str) -> str:
    try:
        return marks.explain(code, part="short")
    except Exception:  # an unparseable code should not break the page
        return ""


def _items() -> list[dict]:
    return examiner.load_items()


def find_item(item_id: str) -> dict | None:
    return next((it for it in _items() if it.get("id") == item_id), None)


# -------------------------------------------------------------------------------------------------- scenes

def _scene_list(obj) -> tuple[list[dict], bool]:
    """Scenes from a scenes file or an item field: a list, a single scene, or {'applicable', 'scenes'}.
    Returns (scenes, applicable)."""
    if obj is None:
        return [], True
    if isinstance(obj, list):
        return [s for s in obj if isinstance(s, dict)], True
    if isinstance(obj, dict):
        if "scenes" in obj or "applicable" in obj:
            applicable = obj.get("applicable", True) is not False
            scenes = obj.get("scenes") or []
            return ([s for s in scenes if isinstance(s, dict)] if isinstance(scenes, list) else []), applicable
        if "elements" in obj or "steps" in obj:
            return [obj], True
    return [], True


def load_scenes(item: dict) -> tuple[list[dict], bool, str]:
    """All scenes for an item: content/clean/scenes/<id>.json first, then item-level and part-level fields.
    Returns (scenes, applicable, approach_summary). Scenes that failed a gate (`gate.pass` False) are dropped."""
    scenes: list[dict] = []
    applicable = True
    file_obj = _read_json(SCENES_DIR / f"{item['id']}.json") if SCENES_DIR.exists() else None
    if file_obj is not None:
        scenes, applicable = _scene_list(file_obj)
    if not scenes:
        s, a = _scene_list(item.get("scenes"))
        scenes += s
        applicable = applicable and a
        for p in item.get("parts") or []:
            s, _ = _scene_list(p.get("scenes"))
            for sc in s:
                sc.setdefault("part", p.get("label"))
            scenes += s
    scenes = [s for s in scenes if (s.get("gate") or {}).get("pass") is not False and (s.get("elements") or s.get("steps"))]
    if not applicable:
        scenes = []
    approaches = [s.get("approach") for s in scenes if s.get("approach")]
    labels = {"graphical": "the picture is the argument", "algebraic-check": "the picture checks the algebra",
              "model": "an interactive model of the situation"}
    summary = "; ".join(f"{a}: {labels.get(a, '')}".rstrip(": ") for a in dict.fromkeys(approaches))
    return scenes, applicable, summary


# ----------------------------------------------------------------------------------------------- item view

def _levels(part: dict) -> dict | None:
    lv = part.get("solution_levels")
    if not isinstance(lv, dict):
        return None
    out = {}
    if isinstance(lv.get("brisk"), list) and lv["brisk"]:
        out["brisk"] = [{"step": s.get("step", i + 1), "working": s.get("working") or "",
                         "secures": [c for c in (s.get("secures") or []) if c] if isinstance(s.get("secures"), list)
                         else [s["secures"]] if s.get("secures") else []}
                        for i, s in enumerate(lv["brisk"]) if isinstance(s, dict)]
    if isinstance(lv.get("every_step"), list) and lv["every_step"]:
        out["every_step"] = [{"step": s.get("step", i + 1), "working": s.get("working") or "", "why": s.get("why") or "",
                              "secures": s.get("secures") or None, "check": s.get("check") or None}
                             for i, s in enumerate(lv["every_step"]) if isinstance(s, dict)]
    return out or None


def _part_view(part: dict, item: dict, skills: dict, defs: dict, index: int) -> dict:
    label = part.get("label")
    scheme = [{"code": m.get("code") or "", "for": m.get("for") or "", "notes": m.get("notes") or "",
               "convention_short": _convention_short(m.get("code") or "")}
              for m in part.get("mark_scheme") or []]
    steps = [{"step": s.get("step", i + 1), "working": s.get("working") or "", "mark": s.get("mark")}
             for i, s in enumerate(part.get("solution") or [])]
    norm = examiner.norm_label(label)
    pitfalls = [{"error_code": p.get("error_code"), "text": p.get("text") or "", "step": p.get("step"),
                 "says_common": bool(p.get("says_common")), "definition": defs.get(p.get("error_code") or "", "")}
                for p in item.get("pitfalls") or []
                if examiner.norm_label(p.get("part")) == norm or (p.get("part") in (None, "", "-") and index == 0)]
    return {"index": index, "label": label, "marks": part.get("marks"), "text": part.get("text") or "",
            "command": part.get("command"), "mark_scheme": scheme, "steps": steps, "solution_levels": _levels(part),
            "hints": list(part.get("hints") or []), "pitfalls": pitfalls,
            "skills": [{"id": s, "title": skills.get(s, s)} for s in part.get("skills") or []],
            "alternatives": [{"name": a.get("name") or "Alternative method",
                              "marks": [{"code": m.get("code") or "", "for": m.get("for") or ""} for m in a.get("marks") or []]}
                             for a in part.get("alternatives") or []]}


def item_view(item_id: str) -> dict | None:
    """Everything the /learn?item= page shows, JSON-safe. None when the item is not gate-passed or missing."""
    item = find_item(item_id)
    if not item:
        return None
    types, skills, defs = question_types(), skill_titles(), error_code_definitions()
    qt = types.get(item.get("question_type") or "")
    parts = [_part_view(p, item, skills, defs, i) for i, p in enumerate(item.get("parts") or [])]
    scenes, applicable, approach = load_scenes(item)
    b = marks.profile()
    return {"item_id": item["id"], "title": _type_title(item.get("question_type"), types),
            "component": item.get("component"), "tier": item.get("tier"), "kind": item.get("kind"),
            "question_type": {"id": item.get("question_type"), "title": qt["title"] if qt else _type_title(item.get("question_type"), types),
                              "topic": qt["topic"] if qt else None, "topic_title": qt["topic_title"] if qt else None,
                              "has_playbook": (PLAYBOOKS_DIR / f"{item.get('question_type')}.json").exists()},
            "stem": item.get("stem") or "", "question_text": examiner.question_text(item),
            "total_marks": sum(int(p.get("marks") or 0) for p in item.get("parts") or []),
            "parts": parts,
            "skills": [{"id": s, "title": skills.get(s, s)} for s in dict.fromkeys(s for p in item.get("parts") or [] for s in p.get("skills") or [])],
            "has_levels": any(p["solution_levels"] for p in parts),
            "scenes": scenes, "scenes_applicable": applicable, "approach": approach,
            "board": b.qualification, "disclaimer": b.disclaimer}


# ----------------------------------------------------------------------------------------------- catalogue

def catalogue() -> dict:
    """Gate-passed items grouped by component: {components: [{component, items: [...]}], n_items, n_levels, n_scenes}."""
    types = question_types()
    groups: dict[str, list] = {}
    for it in _items():
        has_levels = any(_levels(p) for p in it.get("parts") or [])
        scenes, applicable, _ = load_scenes(it)
        entry = {"item_id": it["id"], "title": _type_title(it.get("question_type"), types),
                 "question_type": it.get("question_type"), "component": it.get("component"), "tier": it.get("tier"),
                 "kind": it.get("kind"), "marks": sum(int(p.get("marks") or 0) for p in it.get("parts") or []),
                 "n_parts": len(it.get("parts") or []), "has_levels": has_levels, "has_scenes": bool(scenes)}
        groups.setdefault(it.get("component") or "other", []).append(entry)
    order = {c: i for i, c in enumerate(COMPONENT_ORDER)}
    comps = [{"component": c, "items": sorted(v, key=lambda e: (e["title"], e["item_id"]))}
             for c, v in sorted(groups.items(), key=lambda kv: (order.get(kv[0], 99), kv[0]))]
    flat = [e for c in comps for e in c["items"]]
    b = marks.profile()
    return {"components": comps, "n_items": len(flat), "n_levels": sum(e["has_levels"] for e in flat),
            "n_scenes": sum(e["has_scenes"] for e in flat), "board": b.qualification, "disclaimer": b.disclaimer}


# ----------------------------------------------------------------------------------------------- playbooks

def _playbook_files() -> list[Path]:
    return sorted(PLAYBOOKS_DIR.glob("*.json")) if PLAYBOOKS_DIR.exists() else []


def _items_of_type(type_id: str, items: list[dict] | None = None) -> list[dict]:
    types = question_types()
    return [{"item_id": it["id"], "title": _type_title(it.get("question_type"), types), "tier": it.get("tier"),
             "marks": sum(int(p.get("marks") or 0) for p in it.get("parts") or [])}
            for it in (items if items is not None else _items()) if it.get("question_type") == type_id]


def _is_thin(pb: dict) -> bool:
    n = (pb.get("facts") or {}).get("n_questions")
    return isinstance(n, int) and n < THIN_TYPE_QUESTIONS


def playbook_index() -> list[dict]:
    """[{id, title, topic, topic_title, component, n_leaks, has_items, n_items, thin}] sorted by topic then title."""
    types = question_types()
    items = _items()
    by_type: dict[str, int] = {}
    for it in items:
        by_type[it.get("question_type") or ""] = by_type.get(it.get("question_type") or "", 0) + 1
    out = []
    for f in _playbook_files():
        pb = _read_json(f)
        if not isinstance(pb, dict):
            continue
        pid = pb.get("id") or f.stem
        qt = types.get(pb.get("question_type") or pid, {})
        out.append({"id": pid, "title": pb.get("title") or qt.get("title") or pid.replace("-", " ").capitalize(),
                    "topic": qt.get("topic"), "topic_title": qt.get("topic_title") or "Other",
                    "component": pb.get("component") or qt.get("component"),
                    "n_leaks": len(pb.get("where_marks_leak") or []), "has_items": by_type.get(pid, 0) > 0,
                    "n_items": by_type.get(pid, 0), "thin": _is_thin(pb)})
    out.sort(key=lambda p: (p["topic_title"], p["title"]))
    return out


def playbook(type_id: str) -> dict | None:
    """The playbook file plus resolved skill titles, error-code definitions, related-type titles and the
    gate-passed practice items of that type. None when there is no such playbook."""
    if not type_id or "/" in type_id or "\\" in type_id or type_id.startswith("."):
        return None
    pb = _read_json(PLAYBOOKS_DIR / f"{type_id}.json")
    if not isinstance(pb, dict):
        return None
    types, skills, defs = question_types(), skill_titles(), error_code_definitions()
    qt = types.get(pb.get("question_type") or type_id, {})
    items = _items()
    related = []
    for rid in pb.get("related_types") or []:
        rt = types.get(rid, {})
        related.append({"id": rid, "title": rt.get("title") or rid.replace("-", " ").capitalize(),
                        "has_playbook": (PLAYBOOKS_DIR / f"{rid}.json").exists(),
                        "n_items": sum(1 for it in items if it.get("question_type") == rid)})
    leaks = [{"error_code": l.get("error_code"), "mark_family": l.get("mark_family"), "text": l.get("text") or "",
              "definition": defs.get(l.get("error_code") or "", "")} for l in pb.get("where_marks_leak") or []]
    b = marks.profile()
    return {"id": pb.get("id") or type_id, "question_type": pb.get("question_type") or type_id,
            "title": pb.get("title") or qt.get("title") or type_id, "component": pb.get("component") or qt.get("component"),
            "topic": qt.get("topic"), "topic_title": qt.get("topic_title"), "definition": qt.get("definition", ""),
            "what_it_asks": pb.get("what_it_asks") or "", "typical_structure": pb.get("typical_structure") or "",
            "mark_pattern": pb.get("mark_pattern") or "", "where_marks_leak": leaks,
            "write_to_earn": list(pb.get("write_to_earn") or []),
            "check_before_you_leave": list(pb.get("check_before_you_leave") or []),
            "skills": [{"id": s, "title": skills.get(s, s)} for s in pb.get("skills") or []],
            "related_types": related, "practice_items": _items_of_type(type_id, items),
            "thin": _is_thin(pb), "n_questions": (pb.get("facts") or {}).get("n_questions"),
            "board": b.qualification, "disclaimer": b.disclaimer}
