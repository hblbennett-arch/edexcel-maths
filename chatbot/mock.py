"""Timed mocks (docs/market-research-product-strategy.md §4.2, feature 5): a paper assembled from gate-passed clean
items, marked part by part with chatbot/marker.py, with the marks broken down by mark family and by skill and mapped
to the published 2026 grade boundaries scaled to the paper's marks.

    from chatbot import mock
    mock.papers()                       # [{id, title, marks, minutes, n_questions, source}]  (no model)
    mock.paper("practice-pure-50")      # the paper with question texts (stem + parts)         (no model)
    mock.submit(user, paper_id, {item_id: {"a": "...", "-": "..."}}, elapsed_seconds)   # one marker call per answered part

Papers come from content/clean/mocks/*.json ({"id","title","marks","minutes","questions":[{"q_num","item_id",...}]};
only questions whose item exists and passes G1-G8 are kept) plus a synthetic "Practice set" chosen from the gate-passed
pure items to follow the measured 9MA0 mix bands (content/facts/aggregates.json mix_9ma0.pure) at about 50 marks.
Marking events are recorded with source "mock"; unanswered parts score 0 and are flagged not attempted (no event).
Reads only content/clean, content/blueprints, content/facts and content/boards: no Pearson text is involved.
"""
from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

from . import events, examiner, marker, marks, working

ROOT = Path(__file__).resolve().parent.parent
MOCKS_DIR = ROOT / "content" / "clean" / "mocks"
BLUEPRINTS_DIR = ROOT / "content" / "blueprints"
AGGREGATES_PATH = ROOT / "content" / "facts" / "aggregates.json"
SOURCE = "mock"
PRACTICE_ID = "practice-pure-50"
PRACTICE_TARGET = 50
MINUTES_PER_MARK = 1.2  # 9MA0: 100 marks in 120 minutes
SEED = 9
WORKERS = 3
BANDS = ("single-topic-short", "single-topic-long", "two-topics", "three-plus-topics")
# Published 2026 9MA0 boundaries out of 300 (docs/market-research-product-strategy.md §2); D and E continue the
# B->C step linearly below C.
BOUNDARIES_300 = {"A*": 254, "A": 210, "B": 173, "C": 136}
GRADE_ORDER = ("A*", "A", "B", "C", "D", "E", "U")


# ------------------------------------------------------------------------------------------------- catalogue

@lru_cache(maxsize=1)
def _items() -> dict:
    return {it["id"]: it for it in examiner.load_items()}


@lru_cache(maxsize=1)
def _bands() -> dict:
    """blueprint id -> mix band, from content/blueprints/*.jsonl."""
    out = {}
    for f in sorted(BLUEPRINTS_DIR.glob("*.jsonl")) if BLUEPRINTS_DIR.exists() else []:
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("id") and d.get("band"):
                out[d["id"]] = d["band"]
    return out


def _item_marks(item: dict) -> int:
    return sum(int(p.get("marks") or 0) for p in item.get("parts") or [])


def _skill_groups(item: dict) -> int:
    return len({s.split("-")[0] for p in item.get("parts") or [] for s in p.get("skills") or []})


def band_of(item: dict) -> str:
    """The blueprint's band when we have it, else by the number of distinct skill groups and length."""
    b = _bands().get(item.get("blueprint_id") or "")
    if b in BANDS:
        return b
    n = _skill_groups(item)
    if n >= 3:
        return "three-plus-topics"
    if n == 2:
        return "two-topics"
    return "single-topic-long" if _item_marks(item) >= 6 else "single-topic-short"


@lru_cache(maxsize=1)
def mix_targets() -> dict:
    """Share of marks per band in the measured 9MA0 pure papers."""
    try:
        mix = json.loads(AGGREGATES_PATH.read_text())["mix_9ma0"]["pure"]
    except (OSError, KeyError, json.JSONDecodeError):
        mix = {b: {"marks": 1} for b in BANDS}
    total = sum(v.get("marks", 0) for v in mix.values()) or 1
    return {b: mix.get(b, {}).get("marks", 0) / total for b in BANDS}


def practice_set(target: int = PRACTICE_TARGET, seed: int = SEED) -> list[dict]:
    """Greedy, seeded: repeatedly take an item from the band furthest below its target share of marks, preferring
    unseen question types, until the total reaches about `target` marks. Pure items only."""
    pool = [it for it in _items().values() if it.get("component") == "pure" and _item_marks(it) > 0]
    rng = random.Random(seed)
    rng.shuffle(pool)
    shares = mix_targets()
    chosen, got, seen_types = [], {b: 0 for b in BANDS}, set()
    total = 0
    while pool and total < target - 1:
        room = target + 3 - total
        best = None
        for it in pool:
            m = _item_marks(it)
            if m > room:
                continue
            b = band_of(it)
            deficit = shares[b] * target - got[b]
            score = (deficit - (5 if it.get("question_type") in seen_types else 0), -m)
            if best is None or score > best[0]:
                best = (score, it)
        if best is None:
            break
        it = best[1]
        pool.remove(it)
        chosen.append(it)
        got[band_of(it)] += _item_marks(it)
        seen_types.add(it.get("question_type"))
        total += _item_marks(it)
    chosen.sort(key=lambda it: (_item_marks(it), it["id"]))  # short questions first, as on the real paper
    return chosen


def _question(q_num: int, item: dict, extra: dict | None = None) -> dict:
    return {"q_num": q_num, "item_id": item["id"], "marks": _item_marks(item), "title": working._title(item),
            "question_type": item.get("question_type"), "band": band_of(item), "component": item.get("component"),
            "stem": item.get("stem") or "",
            "parts": [{"label": p.get("label"), "key": p.get("label") or "-", "marks": int(p.get("marks") or 0),
                       "text": p.get("text") or ""} for p in item.get("parts") or []],
            **{k: v for k, v in (extra or {}).items() if k not in ("q_num", "item_id", "marks")}}


def _file_papers() -> list[dict]:
    out = []
    for f in sorted(MOCKS_DIR.glob("*.json")) if MOCKS_DIR.exists() else []:
        try:
            d = json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        qs, dropped = [], 0
        for q in d.get("questions") or []:
            it = _items().get(str(q.get("item_id") or ""))
            if it is None:
                dropped += 1
                continue
            qs.append(_question(len(qs) + 1, it, q))
        if not qs:
            continue
        m = sum(q["marks"] for q in qs)
        out.append({"id": str(d.get("id") or f.stem), "title": str(d.get("title") or f.stem), "marks": m,
                    "declared_marks": d.get("marks"),  # a partly available paper gets time in proportion to its marks
                    "minutes": int(d.get("minutes")) if d.get("minutes") and not dropped else int(round(m * MINUTES_PER_MARK)),
                    "questions": qs, "dropped": dropped, "source": "file"})
    return out


def _practice_paper() -> dict | None:
    qs = [_question(i + 1, it) for i, it in enumerate(practice_set())]
    if not qs:
        return None
    m = sum(q["marks"] for q in qs)
    return {"id": PRACTICE_ID, "title": "Practice set (pure, 9MA0 mix)", "marks": m, "minutes": int(round(m * MINUTES_PER_MARK)),
            "questions": qs, "dropped": 0, "source": "synthetic",
            "mix": {b: sum(q["marks"] for q in qs if q["band"] == b) for b in BANDS}}


def _all_papers() -> list[dict]:
    ps = _file_papers()
    pr = _practice_paper()
    if pr:
        ps.append(pr)
    return ps


def papers() -> list[dict]:
    """Available papers, without question texts."""
    b = marks.profile()
    return [{"id": p["id"], "title": p["title"], "marks": p["marks"], "minutes": p["minutes"], "source": p["source"],
             "n_questions": len(p["questions"]), "dropped": p["dropped"], "board": b.qualification,
             "boundaries": boundaries_for(p["marks"])} for p in _all_papers()]


def paper(paper_id: str) -> dict | None:
    """One paper with question texts (stem + parts), or None."""
    for p in _all_papers():
        if p["id"] == paper_id:
            b = marks.profile()
            return {**p, "board": b.qualification, "disclaimer": b.disclaimer, "boundaries": boundaries_for(p["marks"]),
                    "rule": "Type your working, one line per step (use $...$ for maths). Every part is marked "
                            "against the scheme when you submit; blank parts score 0."}
    return None


# ---------------------------------------------------------------------------------------------------- grades

def boundaries_for(paper_marks: int) -> dict:
    """The 2026 boundaries scaled from 300 to this paper's marks; D and E one B->C step each below C."""
    step = BOUNDARIES_300["B"] - BOUNDARIES_300["C"]
    b300 = {**BOUNDARIES_300, "D": BOUNDARIES_300["C"] - step, "E": BOUNDARIES_300["C"] - 2 * step}
    scale = paper_marks / 300 if paper_marks else 0
    return {g: max(0, int(round(b300[g] * scale))) for g in GRADE_ORDER if g != "U"}


def estimate_grade(earned: int, paper_marks: int) -> dict:
    bs = boundaries_for(paper_marks)
    grade = "U"
    for g in GRADE_ORDER[:-1]:
        if earned >= bs[g]:
            grade = g
            break
    higher = [g for g in GRADE_ORDER[:-1] if bs[g] > earned]
    nxt = higher[-1] if higher else None
    return {"grade": grade, "boundaries": bs, "out_of": paper_marks, "basis": "2026 9MA0 boundaries (A* 254, A 210, B 173, C 136 of 300) scaled to this paper; D and E extrapolated",
            "next_grade": nxt, "marks_to_next": (bs[nxt] - earned) if nxt else 0,
            "scaled_300": int(round(earned * 300 / paper_marks)) if paper_marks else 0}


# ---------------------------------------------------------------------------------------------------- submit

def _scheme_rows(part: dict) -> list[dict]:
    """Every scheme mark of a part as {code, family, worth, skill} (what is available whether attempted or not)."""
    rows = []
    for m in part.get("mark_scheme") or []:
        mk = marks.try_parse(m.get("code") or "")
        rows.append({"code": m.get("code"), "family": mk.family if mk else "other", "worth": mk.worth if mk else 1,
                     "skill": (part.get("skills") or [None])[0]})
    return rows


def _mark_part(paper_id: str, item: dict, part: dict, text: str) -> dict:
    """One marker call for one part. No recording here (sqlite is not thread-safe): returns `rows` for events.record."""
    label = part.get("label")
    transcript = marker.transcribe(text)
    transcript["source"] = "typed"
    if not transcript["lines"]:
        return {"attempted": False}
    try:
        out = marker.mark(item, label, transcript, ref=f"mock/{paper_id}/{item['id']}/{label or '-'}")
    except Exception as ex:  # budget, subprocess or parse failure: the paper still comes back
        return {"attempted": True, "marked": False, "error": working.FRIENDLY_ERROR, "detail": f"{type(ex).__name__}: {ex}"[:300],
                "lines": transcript["lines"]}
    lines = working._scheme_lines(part)
    decs = [d for d in out["decisions"] if marker.norm_label(d.get("part")) == marker.norm_label(label)]
    views = [working._decision_view(d, lines[d["position"]] if d["position"] < len(lines) else {}) for d in decs]
    s = out["summary"].get(marker.norm_label(label)) or {}
    return {"attempted": True, "marked": True, "earned": int(s.get("earned", 0)), "decisions": views,
            "lost_by_family": s.get("lost_by_family", {}), "implied_positions": s.get("implied_positions", []),
            "lines": transcript["lines"], "facts": list(out.get("facts") or []), "cost_usd": out.get("cost_usd"),
            "model": out.get("model"), "seconds": out.get("seconds"), "rows": marker.to_decisions(out, part)}


def submit(user_id: str, paper_id: str, answers: dict, elapsed_seconds: float = 0, *, conn=None, workers: int = WORKERS) -> dict:
    """Mark every answered part (one marker call each, at most `workers` at a time), record "mock" events and return
    per-question marks, the total, breakdowns by mark family and by skill, the top error codes and a grade estimate."""
    p = paper(paper_id)
    if p is None:
        return {"error": "No such paper."}
    answers = answers if isinstance(answers, dict) else {}
    elapsed = float(elapsed_seconds or 0)
    tasks = []  # (q_index, part_index, item, part, text)
    for qi, q in enumerate(p["questions"]):
        item = _items().get(q["item_id"])
        given = answers.get(q["item_id"]) or {}
        for pi, part in enumerate(item.get("parts") or []):
            key = part.get("label") or "-"
            text = str(given.get(key) or "") if isinstance(given, dict) else ""
            if text.strip():
                tasks.append((qi, pi, item, part, text[:20000]))
    results: dict[tuple, dict] = {}
    if tasks:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(tasks)))) as pool:
            futs = {pool.submit(_mark_part, paper_id, t[2], t[3], t[4]): (t[0], t[1]) for t in tasks}
            for f, key in futs.items():
                results[key] = f.result()
    for (qi, pi), r in results.items():  # record serially, on this thread
        if not r.get("marked"):
            continue
        item = _items()[p["questions"][qi]["item_id"]]
        part = item["parts"][pi]
        try:
            r["event_id"] = events.record(user_id, SOURCE, item["id"], part.get("label"), r.pop("rows"), board=marks.profile().id,
                                          model=r.get("model"), cost_usd=r.get("cost_usd"), transcript_confirmed=True,
                                          meta={"paper_id": paper_id, "elapsed_seconds": elapsed, "input": "typed",
                                                "seconds": r.get("seconds"), "lines": len(r.get("lines") or [])}, conn=conn)
        except Exception as ex:  # a storage problem must not hide the marking
            r["event_id"], r["record_error"] = None, f"{type(ex).__name__}: {ex}"[:200]

    by_family: dict[str, dict] = {}
    by_skill: dict[str, dict] = {}
    by_code: dict[str, int] = {}
    questions_out, total_earned, cost, calls = [], 0, 0.0, 0
    for qi, q in enumerate(p["questions"]):
        item = _items()[q["item_id"]]
        parts_out, q_earned, q_lost = [], 0, {}
        for pi, part in enumerate(item.get("parts") or []):
            r = results.get((qi, pi)) or {"attempted": False}
            rows = _scheme_rows(part)
            earned = int(r.get("earned") or 0) if r.get("marked") else 0
            decs = r.get("decisions") or []
            awarded_at = {d["position"]: d["awarded"] for d in decs}
            for i, row in enumerate(rows):
                f = by_family.setdefault(row["family"], {"available": 0, "lost": 0, "not_attempted": 0})
                f["available"] += row["worth"]
                if row["skill"]:
                    s = by_skill.setdefault(row["skill"], {"available": 0, "lost": 0, "not_attempted": 0})
                    s["available"] += row["worth"]
                got = awarded_at.get(i, False) if r.get("marked") else False
                if not got:
                    f["lost"] += row["worth"]
                    if row["skill"]:
                        by_skill[row["skill"]]["lost"] += row["worth"]
                    if not r.get("attempted"):
                        f["not_attempted"] += row["worth"]
                        if row["skill"]:
                            by_skill[row["skill"]]["not_attempted"] += row["worth"]
            for d in decs:
                if d.get("error_code") and not d["awarded"]:
                    by_code[d["error_code"]] = by_code.get(d["error_code"], 0) + 1
            lost_fam = r.get("lost_by_family") or ({} if r.get("marked") else {"not attempted": int(part.get("marks") or 0)})
            for k, v in lost_fam.items():
                q_lost[k] = q_lost.get(k, 0) + v
            q_earned += earned
            if r.get("cost_usd"):
                cost += float(r["cost_usd"])
            calls += int(bool(r.get("marked")) or bool(r.get("error")))
            parts_out.append({"label": part.get("label"), "key": part.get("label") or "-", "marks": int(part.get("marks") or 0),
                              "text": part.get("text") or "", "earned": earned, "attempted": bool(r.get("attempted")),
                              "not_attempted": not r.get("attempted"), "marked": bool(r.get("marked")),
                              "error": r.get("error"), "detail": r.get("detail"), "lines": r.get("lines") or [],
                              "facts": r.get("facts") or [], "decisions": decs, "lost_by_family": lost_fam,
                              "implied_positions": r.get("implied_positions") or [], "skill": (part.get("skills") or [None])[0],
                              "event_id": r.get("event_id"), "record_error": r.get("record_error")})
        total_earned += q_earned
        questions_out.append({"q_num": q["q_num"], "item_id": q["item_id"], "title": q["title"], "band": q["band"],
                              "marks": q["marks"], "earned": q_earned, "lost_by_family": q_lost,
                              "attempted": any(pp["attempted"] for pp in parts_out), "parts": parts_out,
                              "learn_url": f"/learn?item={q['item_id']}"})
    defs = working.error_code_definitions()
    top_codes = sorted(by_code.items(), key=lambda kv: -kv[1])
    try:
        profile = working.profile(user_id, conn=conn)
    except Exception:
        profile = None
    return {"paper_id": p["id"], "title": p["title"], "marks": p["marks"], "minutes": p["minutes"], "earned": total_earned,
            "elapsed_seconds": elapsed, "grade": estimate_grade(total_earned, p["marks"]), "questions": questions_out,
            "by_family": by_family, "by_skill": {s: {**v, "title": working.skill_titles().get(s, s)} for s, v in by_skill.items()},
            "top_error_codes": [{"code": c, "marks": n, "definition": defs.get(c, "")} for c, n in top_codes[:8]],
            "parts_total": sum(len(q["parts"]) for q in questions_out),
            "parts_attempted": sum(1 for q in questions_out for pp in q["parts"] if pp["attempted"]),
            "marker_calls": calls, "cost_usd": round(cost, 4), "profile": profile,
            "board": marks.profile().qualification, "disclaimer": marks.profile().disclaimer}

