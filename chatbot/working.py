""""Mark my working, explained" for the web UI: a thin orchestration layer over chatbot/marker.py.

    from chatbot import working
    working.catalogue()                                   # gate-passed items for the picker (no model)
    working.submit(user_id, item_id, "a", "x^2-7x+6=0\\nx=1, 6")   # transcribe -> facts -> one marking call
                                                          #   -> events.record (one event per part) -> JSON-safe dict

Reads only content/clean (via examiner.load_items), content/clean/tags.json, content/error_codes.json and
content/boards. The only model call is marker.mark (step "marker-v2"). Model failures come back as
{"error": "..."} so the page can show a friendly message instead of hanging.
"""
from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path

from . import events, examiner, marker, marks

ROOT = Path(__file__).resolve().parent.parent
TAGS_PATH = ROOT / "content" / "clean" / "tags.json"
ERROR_CODES_PATH = ROOT / "content" / "error_codes.json"
SOURCE = "mark-my-working"
FRIENDLY_ERROR = ("We couldn't mark this just now (the marker did not answer). Your working has not been lost: "
                  "try again in a moment.")
PHOTO_ERROR = ("We couldn't read that photo just now (the transcriber did not answer). Try again in a moment, or type "
               "your working instead.")
MAX_IMAGE_BYTES = 6 * 1024 * 1024
IMAGE_EXTS = {"jpg": ".jpg", "jpeg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif"}
_UNSET = object()


# ------------------------------------------------------------------------------------------------ catalogue

@lru_cache(maxsize=1)
def _tags() -> dict:
    try:
        return json.loads(TAGS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


@lru_cache(maxsize=1)
def question_type_titles() -> dict:
    return {q["id"]: q.get("title") or q["id"] for q in _tags().get("question_types", []) if q.get("id")}


@lru_cache(maxsize=1)
def skill_titles() -> dict:
    return {s["id"]: s.get("title") or s["id"] for s in _tags().get("skills", []) if s.get("id")}


@lru_cache(maxsize=1)
def error_code_definitions() -> dict:
    try:
        d = json.loads(ERROR_CODES_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return {c["id"]: c.get("definition", "") for c in d.get("codes", []) if c.get("id")}


@lru_cache(maxsize=1)
def _items() -> dict:
    return {it["id"]: it for it in examiner.load_items()}


def find_item(item_id: str) -> dict | None:
    return _items().get(item_id)


def _title(item: dict) -> str:
    qt = item.get("question_type") or ""
    return question_type_titles().get(qt) or qt.replace("-", " ").capitalize() or item["id"]


def catalogue() -> list[dict]:
    """Gate-passed items for the picker: {item_id, title, component, tier, marks, stem, parts: [{label, marks, text}]}."""
    out = []
    for item in _items().values():
        parts = [{"label": p.get("label"), "marks": p["marks"], "text": p["text"]} for p in item["parts"]]
        out.append({"item_id": item["id"], "title": _title(item), "question_type": item.get("question_type"),
                    "component": item.get("component"), "tier": item.get("tier"),
                    "marks": sum(p["marks"] for p in parts), "stem": item.get("stem") or "", "parts": parts})
    out.sort(key=lambda c: (c["title"], c["item_id"]))
    return out


# ---------------------------------------------------------------------------------------------------- photo

def transcribe_upload(image_bytes: bytes, ext: str) -> dict:
    """Photo bytes -> {"lines", "line_confidence", "confidence", "needs_confirmation": True, "cost_usd"} via
    marker.transcribe_image (one model call, step marker-v2-transcribe). The image is written to a temp file for
    the call and deleted afterwards whatever happens. HEIC and other unsupported types, empty and oversize uploads
    come back as a friendly {"error"}; so does a transcriber failure (never raises into the server)."""
    e = (ext or "").lower().lstrip(".").split("/")[-1].strip()
    if e in ("heic", "heif"):
        return {"error": "That photo is in HEIC format, which we can't read yet. On iPhone, choose the photo from "
                         "your library (it converts to JPEG) or set Camera > Formats to Most Compatible."}
    suffix = IMAGE_EXTS.get(e)
    if not suffix:
        return {"error": "Please upload a JPEG, PNG or WebP photo of your working."}
    if not image_bytes:
        return {"error": "That upload was empty: choose a photo of your working."}
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return {"error": f"That photo is too large ({len(image_bytes) / 1048576:.1f} MB). Please keep it under 6 MB."}
    fd, tmp = tempfile.mkstemp(prefix="mmw-photo-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image_bytes)
        try:
            t = marker.transcribe_image(Path(tmp), ref="web/photo")
        except Exception as ex:  # subprocess failure, budget exceeded, unparseable reply
            return {"error": PHOTO_ERROR, "detail": f"{type(ex).__name__}: {ex}"[:300]}
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    lines = list(t.get("lines") or [])
    confs = [float(c) for c in (t.get("line_confidence") or [])]
    return {"lines": lines, "line_confidence": confs, "confidence": t.get("confidence", 0.0),
            "needs_confirmation": True, "source": "image", "cost_usd": t.get("cost_usd"), "model": t.get("model"),
            "empty": not lines}


# --------------------------------------------------------------------------------------------------- submit

def _scheme_lines(part: dict) -> list[dict]:
    return [{"for": m.get("for", ""), "notes": m.get("notes") or ""} for m in part.get("mark_scheme") or []]


def _decision_view(d: dict, scheme_line: dict) -> dict:
    """One scheme mark, JSON-safe, with everything the page renders."""
    conf = float(d.get("confidence") or 0)
    error_code = d.get("error_code")
    return {"part": d.get("part"), "position": d["position"], "code": d["code"], "scheme_code": d["scheme_code"],
            "awarded": bool(d["awarded"]), "for": scheme_line.get("for", ""), "notes": scheme_line.get("notes", ""),
            "evidence": d.get("evidence") or "none", "reason": d.get("reason") or "",
            "convention": d.get("convention"), "convention_short": marks.explain(d["scheme_code"], part="short"),
            "error_code": error_code, "error_definition": error_code_definitions().get(error_code) if error_code else None,
            "rewrite_to_earn": d.get("rewrite_to_earn"), "confidence": round(conf, 3),
            "overridden": bool(d.get("overridden")), "self_contradiction": bool(d.get("self_contradiction")),
            "missing": bool(d.get("missing")),
            "check_this": bool(d.get("self_contradiction") or d.get("overridden") or conf < 0.5)}


def submit(user_id: str, item_id: str, part_label, text: str, *, transcript_confirmed=_UNSET, source: str | None = None,
           conn=None) -> dict:
    """Mark working for one part (or every part when part_label is None), record it, return the view.

    `transcript_confirmed`: leave unset for typed text (recorded as today); pass True when the student confirmed
    (and possibly edited) a photo transcript, or None/False to record that explicitly. `source` labels the input in
    the event meta ("typed" by default, "image" for a confirmed photo transcript)."""
    item = find_item(str(item_id or ""))
    if item is None:
        return {"error": "That question is not in the bank."}
    transcript = marker.transcribe(text or "")
    if source:
        transcript["source"] = source
    if not transcript["lines"]:
        return {"error": "Type some working first: one line per step."}
    confirmed = True if transcript_confirmed is _UNSET else (None if transcript_confirmed is None else bool(transcript_confirmed))
    if part_label in ("", "all"):
        part_label = None
    try:
        parts = marker.select_parts(item, part_label)
    except ValueError:
        return {"error": f"This question has no part {part_label!r}."}
    try:
        out = marker.mark(item, part_label, transcript, ref=f"web/{item['id']}/{part_label or 'all'}")
    except Exception as ex:  # subprocess failure, budget exceeded, unparseable reply: never raise into the server
        return {"error": FRIENDLY_ERROR, "detail": f"{type(ex).__name__}: {ex}"[:300]}

    by_part = {marker.norm_label(p.get("label")): p for p in parts}
    decisions, parts_out, event_ids = [], [], []
    for i, p in enumerate(parts):
        label = marker.norm_label(p.get("label"))
        lines = _scheme_lines(p)
        decs = [d for d in out["decisions"] if marker.norm_label(d.get("part")) == label]
        views = [_decision_view(d, lines[d["position"]] if d["position"] < len(lines) else {}) for d in decs]
        decisions += views
        s = out["summary"].get(label) or {}
        parts_out.append({"label": p.get("label"), "marks": p["marks"], "text": p["text"],
                          "earned": s.get("earned", 0), "total": s.get("total", p["marks"]),
                          "lost_by_family": s.get("lost_by_family", {}), "implied_positions": s.get("implied_positions", []),
                          "vector": out["vectors"].get(label, [])})
        try:
            event_ids.append(events.record(
                user_id, SOURCE, item["id"], None if label == "-" else p.get("label"), marker.to_decisions(out, p),
                board=marks.profile().id, model=out.get("model"), cost_usd=out.get("cost_usd") if i == 0 else 0.0,
                transcript_confirmed=confirmed,
                meta={"input": transcript.get("source", "typed"), "seconds": out.get("seconds"),
                      "overrides": out.get("overrides", 0), "parts_in_call": len(parts), "lines": len(transcript["lines"])},
                conn=conn))
        except Exception as ex:  # a storage problem must not hide the marking
            event_ids.append(None)
            parts_out[-1]["record_error"] = f"{type(ex).__name__}: {ex}"[:200]
    try:
        profile = events.leakage_profile(user_id, conn=conn)
    except Exception:
        profile = None
    lost_by_family: dict[str, int] = {}
    for p in parts_out:
        for k, v in p["lost_by_family"].items():
            lost_by_family[k] = lost_by_family.get(k, 0) + v
    return {"item_id": item["id"], "title": _title(item), "part_label": part_label,
            "transcript": {"lines": transcript["lines"], "confidence": transcript["confidence"],
                           "needs_confirmation": transcript["needs_confirmation"], "source": transcript.get("source", "typed")},
            "facts": list(out.get("facts") or []), "decisions": decisions, "parts": parts_out,
            "summary": {"earned": out.get("earned", 0), "total": out.get("total", 0), "lost_by_family": lost_by_family,
                        "implied": sum(len(p["implied_positions"]) for p in parts_out),
                        "check_this": sum(1 for d in decisions if d["check_this"])},
            "model": out.get("model"), "cost_usd": out.get("cost_usd"), "seconds": out.get("seconds"),
            "event_ids": event_ids, "profile": profile_view(profile) if profile else None}


def profile_view(profile: dict) -> dict:
    """The leakage profile plus the titles/definitions the page needs to label it."""
    codes = profile.get("by_error_code") or {}
    skills = profile.get("by_skill") or {}
    return {**profile,
            "error_code_definitions": {c: error_code_definitions().get(c, "") for c in codes},
            "skill_titles": {s: skill_titles().get(s, s) for s in skills}}


def profile(user_id: str, *, conn=None) -> dict:
    return profile_view(events.leakage_profile(user_id, conn=conn))
