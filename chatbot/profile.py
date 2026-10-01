"""The mark-leakage profile page (docs/market-research-product-strategy.md §4.2, feature 3): lost marks by mark
family, error code and skill, a weekly trend, the student's examiner accuracy, and drills by error code.

    from chatbot import profile
    v = profile.view(user_id)          # JSON-safe dict for chatbot/static/profile.html
    profile.plain_summary(v)           # two or three plain sentences, deterministic from the numbers

Reads chatbot/events.py (the event store), content/error_codes.json (definitions, `loses`), content/clean/tags.json
(skill and question-type titles), the gate-passed items (chatbot/examiner.py), the "Be the examiner" exercises and
content/clean/playbooks/*.json. No model calls. Nothing here is content; the numbers are the student's own.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

from . import events, examiner, learn, marks

ROOT = Path(__file__).resolve().parent.parent
ERROR_CODES_PATH = ROOT / "content" / "error_codes.json"
PLAYBOOKS_DIR = ROOT / "content" / "clean" / "playbooks"
TOP_CODES, TOP_SKILLS, TREND_WEEKS = 5, 8, 8
DRILL_ITEMS, DRILL_EXERCISES = 3, 2
FAMILY_LABEL = {"method": "method marks", "accuracy": "accuracy marks", "independent": "independent (B) marks",
                "reasoning": "reasoning marks", "communication": "communication marks", "point": "marking points",
                "level": "level-band marks"}
FAMILY_ORDER = ("method", "accuracy", "independent", "reasoning", "communication", "point", "level")
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


# ------------------------------------------------------------------------------------------------- reference

@lru_cache(maxsize=1)
def error_codes() -> dict:
    """id -> {definition, loses (letter), loses_family}."""
    try:
        d = json.loads(ERROR_CODES_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for c in d.get("codes", []):
        if not c.get("id"):
            continue
        letter = c.get("loses") or ""
        m = marks.try_parse(f"{letter}1") if letter else None
        out[c["id"]] = {"definition": c.get("definition", ""), "loses": letter, "loses_family": m.family if m else letter.lower()}
    return out


@lru_cache(maxsize=1)
def _playbooks_by_code() -> dict:
    """error_code -> [{id, title, url}] from every playbook's where_marks_leak."""
    types = learn.question_types()
    out: dict[str, list[dict]] = {}
    for f in sorted(PLAYBOOKS_DIR.glob("*.json")):
        try:
            pb = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(pb, dict):
            continue
        pid = pb.get("id") or f.stem
        title = pb.get("title") or types.get(pid, {}).get("title") or pid.replace("-", " ").capitalize()
        seen = set()
        for leak in pb.get("where_marks_leak") or []:
            code = leak.get("error_code")
            if code and code not in seen:
                seen.add(code)
                out.setdefault(code, []).append({"id": pid, "title": title, "url": f"/playbooks?type={pid}"})
    return out


@lru_cache(maxsize=1)
def _items_by_code() -> dict:
    """error_code -> [{item_id, title, learn_url, mark_url}] for gate-passed items whose pitfalls carry the code."""
    types = learn.question_types()
    out: dict[str, list[dict]] = {}
    for it in examiner.load_items():
        qt = it.get("question_type") or ""
        title = types.get(qt, {}).get("title") or qt.replace("-", " ").capitalize() or it["id"]
        for code in sorted({pf.get("error_code") for pf in it.get("pitfalls") or [] if pf.get("error_code")}):
            out.setdefault(code, []).append({"item_id": it["id"], "title": title, "component": it.get("component"),
                                              "learn_url": f"/learn?item={it['id']}", "mark_url": f"/mark?item={it['id']}"})
    return out


def _exercises_for(code: str) -> list[dict]:
    out = []
    for ex in examiner.all_exercises():
        if ex.get("error_code") == code:
            out.append({"key": ex["key"], "item_id": ex["item_id"], "script_id": ex["script_id"],
                        "url": f"/examiner?exercise={ex['key']}"})
        if len(out) >= DRILL_EXERCISES:
            break
    return out


def drills_for(code: str) -> dict:
    return {"items": _items_by_code().get(code, [])[:DRILL_ITEMS], "exercises": _exercises_for(code),
            "playbooks": _playbooks_by_code().get(code, [])}


def exercise(key: str) -> dict | None:
    """The public view of one "Be the examiner" exercise by key item_id::script_id (for /examiner?exercise=)."""
    if "::" not in (key or ""):
        return None
    item_id, script_id = key.split("::", 1)
    ex = examiner.find(item_id, script_id)
    return examiner.public_view(ex) if ex else None


# ------------------------------------------------------------------------------------------------------ view

def _pct(part: int, whole: int) -> int | None:
    return round(100 * part / whole) if whole else None


def _week_start(day: dt.date) -> dt.date:
    return day - dt.timedelta(days=day.weekday())


def _details(user_id: str, conn) -> tuple[dict, list]:
    """(error_code -> {skill -> lost}) and [(at, worth, awarded)] for the student's own marked working."""
    rows = conn.execute(
        "SELECT e.at, d.worth, d.awarded, d.error_code, d.skill FROM mark_decisions d JOIN marking_events e ON e.id = d.event_id "
        "WHERE e.user_id = ? AND e.source != 'be-the-examiner'", (user_id,)).fetchall()
    code_skills: dict[str, dict[str, int]] = {}
    timeline = []
    for r in rows:
        timeline.append((r["at"], int(r["worth"]), int(r["awarded"])))
        if not r["awarded"] and r["error_code"] and r["skill"]:
            s = code_skills.setdefault(r["error_code"], {})
            s[r["skill"]] = s.get(r["skill"], 0) + int(r["worth"])
    return code_skills, timeline


def _trend(timeline: list, today: dt.date | None = None) -> list[dict]:
    today = today or dt.datetime.now(dt.timezone.utc).date()
    this_week = _week_start(today)
    weeks = [this_week - dt.timedelta(weeks=i) for i in range(TREND_WEEKS - 1, -1, -1)]
    buckets = {w: {"available": 0, "lost": 0} for w in weeks}
    for at, worth, awarded in timeline:
        try:
            w = _week_start(dt.date.fromisoformat(str(at)[:10]))
        except ValueError:
            continue
        if w in buckets:
            buckets[w]["available"] += worth
            buckets[w]["lost"] += 0 if awarded else worth
    return [{"week_start": w.isoformat(), "available": b["available"], "lost": b["lost"],
             "lost_share": _pct(b["lost"], b["available"])} for w, b in buckets.items()]


def view(user_id: str, *, conn=None) -> dict:
    own = conn is None
    c = conn or events.connect()
    prof = events.leakage_profile(user_id, conn=c)
    code_skills, timeline = _details(user_id, c)
    if own:
        c.close()

    fams = prof.get("by_family") or {}
    available = sum(f["available"] for f in fams.values())
    lost = sum(f["lost"] for f in fams.values())
    order = {f: i for i, f in enumerate(FAMILY_ORDER)}
    by_family = [{"family": f, "label": FAMILY_LABEL.get(f, f), "available": v["available"], "lost": v["lost"],
                  "lost_pct": _pct(v["lost"], v["available"]), "share_of_lost": _pct(v["lost"], lost)}
                 for f, v in sorted(fams.items(), key=lambda kv: (order.get(kv[0], 99), kv[0]))]

    defs, skills = error_codes(), learn.skill_titles()
    codes = []
    for i, (code, n) in enumerate(list((prof.get("by_error_code") or {}).items())[:TOP_CODES]):
        d = defs.get(code, {})
        hit = sorted(code_skills.get(code, {}).items(), key=lambda kv: -kv[1])
        codes.append({"code": code, "label": code.replace("-", " "), "definition": d.get("definition", ""),
                      "loses": d.get("loses", ""), "loses_family": d.get("loses_family", ""), "lost": n,
                      "share_of_lost": _pct(n, lost),
                      "skills": [{"id": s, "title": skills.get(s, s), "lost": k} for s, k in hit],
                      "drills": drills_for(code) if i < 3 else None})

    top_skills = [{"id": s, "title": skills.get(s, s), "available": v["available"], "lost": v["lost"],
                   "lost_pct": _pct(v["lost"], v["available"])}
                  for s, v in sorted((prof.get("by_skill") or {}).items(), key=lambda kv: (-kv[1]["lost"], kv[0]))
                  if v["lost"]][:TOP_SKILLS]

    b = marks.profile()
    out = {"user": user_id, "empty": available == 0 and not (prof["examiner_accuracy"]["judged"]),
           "totals": {"available": available, "lost": lost, "kept": available - lost, "lost_pct": _pct(lost, available)},
           "by_family": by_family, "top_error_codes": codes, "top_skills": top_skills,
           "trend": _trend(timeline), "examiner_accuracy": prof["examiner_accuracy"],
           "board": b.qualification, "disclaimer": b.disclaimer,
           "privacy": ("Your profile is stored under an opaque id in this browser and on this server only; no name or email. "
                       "Deleting it is not yet available (privacy work pending).")}
    out["summary"] = plain_summary(out)
    return out


# --------------------------------------------------------------------------------------------- plain summary

def _share_phrase(pct: int) -> str:
    if pct >= 95:
        return "Almost all"
    if pct >= 80:
        return "Four in five"
    if pct >= 70:
        return "Three quarters"
    if pct >= 60:
        return "Two thirds"
    if pct >= 45:
        return "About half"
    if pct >= 30:
        return "A third"
    if pct >= 20:
        return "A quarter"
    return "A small share"


def _join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def plain_summary(v: dict) -> str:
    """Two or three plain sentences in our voice, deterministic from the numbers."""
    t = v.get("totals") or {}
    acc = v.get("examiner_accuracy") or {}
    if v.get("empty") or not t.get("available"):
        s = "Nothing to profile yet: mark some working, or judge a few scripts in Be the examiner, and this page fills in."
        if acc.get("judged"):
            s = (f"You have judged {acc['judged']} marks as an examiner and agreed with the reference on "
                 f"{acc['correct']} ({round(acc['rate'] * 100)}%). Mark some of your own working and the leakage profile fills in.")
        return s
    lost, available = t["lost"], t["available"]
    if not lost:
        return (f"You have kept every one of the {available} marks available so far. "
                "Keep going: the profile only becomes useful once it has something to show you.")
    fams = [f for f in v.get("by_family") or [] if f["lost"]]
    kept = [f for f in v.get("by_family") or [] if not f["lost"] and f["available"] >= 3]
    top = max(fams, key=lambda f: f["lost"])
    codes = v.get("top_error_codes") or []
    first = f"You have dropped {lost} of {available} marks ({t['lost_pct']}%)."
    if kept:
        first = f"You keep your {_join([k['label'] for k in kept[:2]])}. "
    else:
        first += " "
    if len(fams) == 1:
        second = f"Every mark you drop is one of the {top['label']}"
    else:
        second = f"{_share_phrase(top['share_of_lost'])} of the marks you drop are {top['label']}"
    if codes:
        names = [c["label"] for c in codes[:2]]
        second += f", mostly {_join(names)}."
    else:
        second += "."
    third = ""
    if acc.get("judged"):
        third = f" As an examiner you agree with the reference on {round(acc['rate'] * 100)}% of the marks you judge."
    return (first + second + third).strip()
