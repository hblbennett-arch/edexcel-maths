"""Marking events: every mark decision the product makes or asks a student to make, stored so the mark-leakage
profile exists from the first user (docs/market-research-product-strategy.md §4.2, feature 3).

Two sources write here:
  be-the-examiner   the student judged a scripted answer mark by mark; we store their judgement next to the
                    reference (what the mark really earned) -> "examiner accuracy"
  mark-my-working   our marker judged the student's own working -> lost marks by mark family, error code, skill

    from chatbot import events
    eid = events.record(user_id, source, item_id, part_label, decisions=[{...}], model=None, cost_usd=0)
    events.leakage_profile(user_id)   # {"by_family": ..., "by_error_code": ..., "by_skill": ..., "examiner_accuracy": ...}

Each decision: {"position", "code", "kind", "family", "worth", "awarded", "user_judgement" (be-the-examiner only),
"error_code", "skill", "evidence", "reason"}. The database is data/users/events.db (gitignored user data; nothing
here is content). Privacy: user_id is an opaque id the caller chooses; no names or emails are stored.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "users" / "events.db"
SOURCES = ("be-the-examiner", "mark-my-working", "mock")

DDL = """
CREATE TABLE IF NOT EXISTS marking_events (
    id TEXT PRIMARY KEY,
    at TEXT NOT NULL,                 -- ISO timestamp (UTC)
    user_id TEXT NOT NULL,            -- opaque id chosen by the caller
    source TEXT NOT NULL CHECK (source IN ('be-the-examiner', 'mark-my-working', 'mock')),
    item_id TEXT NOT NULL,            -- our question id
    part_label TEXT,                  -- NULL = single-part question
    script_id TEXT,                   -- be-the-examiner: which scripted answer (G4 response id)
    board TEXT NOT NULL,              -- board profile id, e.g. edexcel-9ma0
    model TEXT,                       -- mark-my-working: the marker model
    cost_usd REAL,
    transcript_confirmed INTEGER,     -- mark-my-working: 1 if the student confirmed the transcript first
    meta TEXT                         -- JSON: anything else (timings, input kind)
);
CREATE TABLE IF NOT EXISTS mark_decisions (
    event_id TEXT NOT NULL REFERENCES marking_events(id),
    position INTEGER NOT NULL,        -- 0-based position in the part's scheme
    code TEXT NOT NULL,               -- rendered scheme code, e.g. 'dM1'
    kind TEXT NOT NULL,               -- canonical kind (chatbot/marks.py KINDS)
    family TEXT NOT NULL,             -- method | accuracy | independent | reasoning | ...
    worth INTEGER NOT NULL,
    awarded INTEGER NOT NULL,         -- what the script/working really earned (reference or marker verdict)
    user_judgement INTEGER,           -- be-the-examiner: what the student awarded (NULL otherwise)
    error_code TEXT,                  -- content/error_codes.json id behind a lost mark, if known
    skill TEXT,                       -- skill id the mark tests, if known
    evidence TEXT,                    -- the line of working the decision rests on
    reason TEXT,                      -- one line: why awarded / withheld
    PRIMARY KEY (event_id, position)
);
CREATE INDEX IF NOT EXISTS idx_events_user ON marking_events(user_id, at);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL)
    return conn


def record(user_id: str, source: str, item_id: str, part_label: str | None, decisions: list[dict], *,
           board: str = "edexcel-9ma0", script_id: str | None = None, model: str | None = None,
           cost_usd: float | None = None, transcript_confirmed: bool | None = None, meta: dict | None = None,
           conn: sqlite3.Connection | None = None) -> str:
    assert source in SOURCES, source
    own = conn is None
    c = conn or connect()
    eid = str(uuid.uuid4())
    c.execute("INSERT INTO marking_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (eid, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), user_id, source, item_id, part_label,
               script_id, board, model, cost_usd, None if transcript_confirmed is None else int(transcript_confirmed),
               json.dumps(meta or {})))
    c.executemany("INSERT INTO mark_decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  [(eid, i, d["code"], d["kind"], d["family"], int(d.get("worth", 1)), int(bool(d["awarded"])),
                    None if d.get("user_judgement") is None else int(bool(d["user_judgement"])),
                    d.get("error_code"), d.get("skill"), d.get("evidence"), d.get("reason"))
                   for i, d in enumerate(decisions)])
    c.commit()
    if own:
        c.close()
    return eid


def leakage_profile(user_id: str, *, conn: sqlite3.Connection | None = None, since: str | None = None) -> dict:
    """Lost marks by family, error code and skill (mark-my-working and mock events), plus the student's accuracy
    as an examiner (be-the-examiner events). `since`: ISO timestamp lower bound."""
    own = conn is None
    c = conn or connect()
    where = "e.user_id = ?" + (" AND e.at >= ?" if since else "")
    args: tuple = (user_id, since) if since else (user_id,)
    rows = c.execute(f"SELECT e.source, d.family, d.worth, d.awarded, d.user_judgement, d.error_code, d.skill "
                     f"FROM mark_decisions d JOIN marking_events e ON e.id = d.event_id WHERE {where}", args).fetchall()
    by_family: dict[str, dict] = {}
    by_code: dict[str, int] = {}
    by_skill: dict[str, dict] = {}
    judged = correct = 0
    for r in rows:
        if r["source"] == "be-the-examiner":
            if r["user_judgement"] is not None:
                judged += 1
                correct += int(r["user_judgement"] == r["awarded"])
            continue
        f = by_family.setdefault(r["family"], {"available": 0, "lost": 0})
        f["available"] += r["worth"]
        if not r["awarded"]:
            f["lost"] += r["worth"]
            if r["error_code"]:
                by_code[r["error_code"]] = by_code.get(r["error_code"], 0) + r["worth"]
        if r["skill"]:
            s = by_skill.setdefault(r["skill"], {"available": 0, "lost": 0})
            s["available"] += r["worth"]
            s["lost"] += 0 if r["awarded"] else r["worth"]
    if own:
        c.close()
    total_lost = sum(f["lost"] for f in by_family.values())
    return {"by_family": by_family, "by_error_code": dict(sorted(by_code.items(), key=lambda kv: -kv[1])),
            "by_skill": by_skill, "total_lost": total_lost,
            "examiner_accuracy": {"judged": judged, "correct": correct,
                                  "rate": round(correct / judged, 3) if judged else None}}


def recent(user_id: str, limit: int = 20, *, conn: sqlite3.Connection | None = None) -> list[dict]:
    own = conn is None
    c = conn or connect()
    rows = c.execute("SELECT * FROM marking_events WHERE user_id = ? ORDER BY at DESC LIMIT ?", (user_id, limit)).fetchall()
    out = [dict(r) for r in rows]
    if own:
        c.close()
    return out
