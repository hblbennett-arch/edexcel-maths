"""Practice recommendations.

narrow(qid)              — other questions of the same question type ("more like this").
broad(qid, part)         — for each skill the part tests, other parts that practise it,
                           easiest first (the "I struggled with the differentiating" case).
ladder(qid, part)        — one build-up path: single-skill starters -> core -> stretch,
                           then a full question of the same type.
refocus(qid, hardest)    — broad() + ladder() for the part the student found hardest.

Difficulty of a part combines its marks, the examiner report's rating / mean mark,
and how many (non exam-technique) skills it combines. Skill matches are weighted
by rarity (IDF), and exam-technique skills (show-that, accuracy…) count far less,
since they say little about what a part is about.
"""
import math
from functools import lru_cache

from . import db
from .identify import summary

EXAM_TECHNIQUE_WEIGHT = 0.25
RATING_SHIFT = {"well_answered": -1.5, "mixed": 0.0, "poorly_answered": 1.5}


@lru_cache(maxsize=1)
def _catalogue():
    """Per-part skills, per-skill weights and per-part difficulty, computed once."""
    groups = {r["id"]: r["group_id"] for r in db.rows("SELECT id, group_id FROM skills")}
    parts = {}
    for p in db.rows("SELECT qp.question_id, qp.label, qp.marks, q.paper, q.sitting, q.qualification, q.status "
                     "FROM question_parts qp JOIN questions q ON q.id = qp.question_id"):
        parts[db.part_key(p["question_id"], p["label"])] = {"question_id": p["question_id"], "label": p["label"],
                                                          "marks": p["marks"], "skills": set(),
                                                          "qualification": p["qualification"],
                                                          "current": p["status"] == "current"}
    for r in db.rows("SELECT question_id, part_label, tag_value FROM question_tags WHERE tag_type = 'skill'"):
        parts[db.part_key(r["question_id"], r["part_label"])]["skills"].add(r["tag_value"])
    df: dict[str, int] = {}
    for p in parts.values():
        for s in p["skills"]:
            df[s] = df.get(s, 0) + 1
    n = len(parts)
    weight = {s: math.log(1 + n / c) * (EXAM_TECHNIQUE_WEIGHT if groups[s] == db.EXAM_TECHNIQUE_GROUP else 1.0)
              for s, c in df.items()}
    perf = {(r["question_id"], r["part_label"]): r for r in db.rows("SELECT * FROM question_performance")}
    for key, p in parts.items():
        row = perf.get((p["question_id"], p["label"])) or perf.get((p["question_id"], None))
        d = p["marks"] * 0.6 + 0.5 * sum(1 for s in p["skills"] if groups[s] != db.EXAM_TECHNIQUE_GROUP)
        if row is not None:
            d += RATING_SHIFT.get(row["rating"], 0.0)
            if row["mean_mark"] is not None and row["max_mark"]:
                d += (0.5 - row["mean_mark"] / row["max_mark"]) * 3
        p["difficulty"] = round(d, 2)
        p["core_skills"] = {s for s in p["skills"] if groups[s] != db.EXAM_TECHNIQUE_GROUP}
    return parts, weight, groups


def tier(difficulty: float) -> str:
    return "starter" if difficulty < 2.5 else "core" if difficulty < 4.5 else "stretch"


LEGACY_NOTE = {"IAL-2018": "from the International A Level (2018 spec)",
               "IAL-2013": "from the International A Level (2013 spec)",
               "GCE-2008": "from the old UK A Level (pre-2017 spec)"}
TIERS = ("starter", "core", "stretch")


def _describe(key: str, reason: str) -> dict:
    parts, _, _ = _catalogue()
    p = parts[key]
    return {"question_id": p["question_id"], "part_label": p["label"], "marks": p["marks"],
            "difficulty": p["difficulty"], "tier": tier(p["difficulty"]), "reason": reason,
            "summary": summary(p["question_id"]), "qualification": p["qualification"],
            "source_note": LEGACY_NOTE.get(p["qualification"])}


def _order(parts: dict, k: str) -> tuple:
    """Easiest tier first; within a tier, current 9MA0 questions before legacy/IAL ones (the handoff's
    rule: keep 9MA0 first unless the user decides otherwise); then single-focus parts, then difficulty."""
    p = parts[k]
    return (TIERS.index(tier(p["difficulty"])), not p["current"], len(p["core_skills"]) > 3, p["difficulty"])


def parts_with_skill(skill_id: str, exclude_question: str | None = None, limit: int = 5) -> list[dict]:
    """Parts practising one skill, easiest first; prefers parts where it's a main skill."""
    parts, _, _ = _catalogue()
    keys = [k for k, p in parts.items() if skill_id in p["skills"] and p["question_id"] != exclude_question]
    keys.sort(key=lambda k: _order(parts, k))
    return [_describe(k, f"practises {skill_id}") for k in keys[:limit]]


def narrow(question_id: str, limit: int = 5) -> list[dict]:
    """Other questions of the same question type, most recent first."""
    qtype = db.one("SELECT tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'question_type'",
                   (question_id,))
    if not qtype:
        return []
    rows = db.rows("SELECT t.question_id, q.total_marks, q.sitting, q.status, q.qualification FROM question_tags t "
                   "JOIN questions q ON q.id = t.question_id "
                   "WHERE t.tag_type = 'question_type' AND t.tag_value = ? AND t.question_id != ?",
                   (qtype["tag_value"], question_id))
    year = lambda s: int("".join(ch for ch in s if ch.isdigit()))
    rows = sorted(rows, key=lambda r: (r["status"] != "current", -year(r["sitting"])))   # 9MA0 first, newest first
    return [{"question_id": r["question_id"], "part_label": None, "marks": r["total_marks"],
             "summary": summary(r["question_id"]), "reason": f"same question type ({qtype['tag_value']})",
             "qualification": r["qualification"], "source_note": LEGACY_NOTE.get(r["qualification"])}
            for r in rows[:limit]]


def broad(question_id: str, part_label: str | None = None, per_skill: int = 3) -> list[dict]:
    """For each core skill of the part (or of the whole question), up to `per_skill` other
    parts practising it, easiest first. Skills are ordered rarest (most specific) first."""
    parts, weight, _ = _catalogue()
    targets = [p for p in parts.values() if p["question_id"] == question_id
               and (part_label is None or p["label"] == part_label)]
    skills = sorted({s for p in targets for s in p["core_skills"]}, key=lambda s: -weight[s])
    return [{"skill": s, "parts": parts_with_skill(s, exclude_question=question_id, limit=per_skill)} for s in skills]


def similar_parts(question_id: str, part_label: str | None, limit: int = 5) -> list[dict]:
    """Parts elsewhere that share the most (weighted) skills with this part."""
    parts, weight, _ = _catalogue()
    target = parts[db.part_key(question_id, part_label)]["skills"]
    scored = []
    for key, p in parts.items():
        if p["question_id"] == question_id:
            continue
        shared = target & p["skills"]
        if shared:
            score = sum(weight[s] for s in shared) / math.sqrt(sum(weight[s] for s in p["skills"]) or 1)
            scored.append((score, key, shared))
    scored.sort(key=lambda t: -t[0])
    return [dict(_describe(key, "shares " + ", ".join(sorted(shared))), score=round(score, 2))
            for score, key, shared in scored[:limit]]


def ladder(question_id: str, part_label: str | None) -> list[dict]:
    """Build-up path for one part: a starter for each of its two most specific skills,
    a core part combining them, then a full question of the same type."""
    parts, weight, _ = _catalogue()
    target = parts[db.part_key(question_id, part_label)]
    main = sorted(target["core_skills"], key=lambda s: -weight[s])[:2]
    steps, used = [], set()
    for s in main:
        cands = [c for c in parts_with_skill(s, exclude_question=question_id, limit=10)
                 if db.part_key(c["question_id"], c["part_label"]) not in used]
        starters = [c for c in cands if c["tier"] == "starter"]
        pick = starters[0] if starters else (min(cands, key=lambda c: c["difficulty"]) if cands else None)
        if pick:  # no easy part for a rare skill -> the easiest part that practises it
            steps.append(dict(pick, step="starter" if starters else "warm-up"))
            used.add(db.part_key(pick["question_id"], pick["part_label"]))
    # Core: the most similar part overall (whatever its tier) that isn't already a starter.
    core = [c for c in similar_parts(question_id, part_label, limit=10)
            if db.part_key(c["question_id"], c["part_label"]) not in used]
    if core:
        steps.append(dict(core[0], step="core"))
    full = narrow(question_id, limit=1)
    if full:
        steps.append(dict(full[0], step="full question"))
    return steps


def refocus(question_id: str, hardest_part: str | None) -> dict:
    """What to recommend once the student says which part was hardest."""
    return {"hardest_part": hardest_part,
            "by_skill": broad(question_id, hardest_part),
            "ladder": ladder(question_id, hardest_part),
            "similar_parts": similar_parts(question_id, hardest_part),
            "same_type": narrow(question_id)}


# ---------- practice requests ("give me a question on X") ----------

import re as _re

_FLUFF = _re.compile(r"\b(hi|hello|hey|please|can you|could you|give me|find me|show me|i want|i'd like|suggest|"
                     r"recommend|some|another|more|a|an|the|stats|statistics|mechanics|mech|pure|questions?|"
                     r"on|about|including|involving|with|to do with|that (uses|has|tests)|practice|practise|okay|ok|nice|"
                     r"but|i asked for|for)\b", _re.I)
_NEGATION = _re.compile(r"\b(?:not|no|without|instead of|rather than|other than)\s+(?:a|an|the|any)?\s*"
                        r"([a-z][a-z0-9 '\-]{2,40}?)(?=\s*(?:[,.;!?]|$|\bbut\b|\band\b|\bquestion))", _re.I)
_COMPONENT_WORDS = {"stats": "stats", "statistics": "stats", "statistical": "stats", "mechanics": "mech",
                    "mech": "mech", "pure": "pure"}
SKILL_MARGIN = 0.03        # skills within this of the best match also count
STRONG_QTYPE = 0.78        # a question type matched at least this well is itself a target


def _normalise_request(text: str) -> str:
    t = _re.sub(r"\b2nd\b", "second", text.lower())
    t = _re.sub(r"\b1st\b", "first", t)
    return t


def parse_request(text: str) -> dict:
    """Split a practice request into positive text, excluded phrases and a component hint."""
    t = _normalise_request(text)
    negatives = [m.group(1).strip() for m in _NEGATION.finditer(t)]
    positive = _NEGATION.sub(" ", t)
    component = next((_COMPONENT_WORDS[w] for w in _re.findall(r"[a-z]+", t) if w in _COMPONENT_WORDS), None)
    core = _re.sub(r"\s+", " ", _FLUFF.sub(" ", positive)).strip(" ?.!,")
    return {"positive": core or positive, "negatives": negatives, "component": component}


def _targets(text: str) -> tuple[list[tuple[str, float]], tuple[str, float] | None]:
    """Skills (non exam-technique) and a question type that best match the text."""
    from .search import get_index
    ix = get_index()
    _, _, groups = _catalogue()
    hits = [(h.doc_id.split(":", 1)[1], h.semantic) for h in ix.search(text, "skill", k=15, mode="semantic")]
    hits = [(s, v) for s, v in hits if groups.get(s) != db.EXAM_TECHNIQUE_GROUP]
    top = hits[0][1] if hits else 0.0
    skills = [(s, v) for s, v in hits if v >= top - SKILL_MARGIN][:3]
    qt = ix.search(text, "qtype", k=1, mode="semantic")
    qtype = (qt[0].doc_id.split(":", 1)[1], qt[0].semantic) if qt else None
    return skills, qtype


# ---- specific-expression requests ("a question on differentiating x^x") ------------------------------
# Skill tags describe techniques, so a request naming a particular expression can map to the wrong skill
# (x^x -> "differentiate polynomials", 2026-09-27). If the request contains maths, look for that expression in
# the stored questions' LaTeX first. Deterministic: both sides are normalised the same way.
MAX_EXPR_HITS = 25          # an expression in more questions than this (x^2, sin x) is too common to be a request
_MATH_TOKEN = _re.compile(r"(?<![a-z])(?:[a-z0-9()]+\^\s*\{?[a-z0-9+\-()/.]+\}?|\\?(?:sin|cos|tan|sec|cosec|cot|ln|log|e)\s*\^?\{?[\-a-z0-9()+/.]*\}?\s*\(?[0-9]*[a-z]\)?|[0-9]*[a-z]\s*/\s*[0-9]*[a-z])")


def _norm_math(t: str, typed: bool = False) -> str:
    """Canonical form for matching: no spacing/sizing, powers as explicit groups ("x^x" -> "x^(x)",
    "e^{2x}" -> "e^(2x)"). A student's typed "e^2x" means e^{2x}; in LaTeX "e^2x" means e^2 x."""
    t = t.lower().replace("$", "")
    t = _re.sub(r"\\(left|right|big|bigg|displaystyle|mathrm|text|operatorname)\b|\\[,;:! ]", "", t)
    t = _re.sub(r"\\(d|t)frac", r"\\frac", t)
    t = _re.sub(r"\s+", "", t)
    t = _re.sub(r"\^\{([^{}]*)\}", r"^(\1)", t)
    t = _re.sub(r"\^([0-9]*[a-z]|[0-9]+)" if typed else r"\^([a-z0-9])", r"^(\1)", t)
    return t.replace("{", "").replace("}", "")


def request_expressions(text: str) -> list[str]:
    """Maths-looking fragments in a request, normalised (words like 'differentiating' are dropped)."""
    out = []
    for m in _MATH_TOKEN.finditer(text.lower()):
        e = _norm_math(m.group(0), typed=True).strip("(")
        e = e[:-1] if e.count(")") > e.count("(") else e
        if len(e) >= 3 and _re.search(r"[\^/(]|\\|\d", e) and e not in out:
            out.append(e)
    return out


@lru_cache(maxsize=1)
def _question_maths() -> dict[str, str]:
    return {r["id"]: _norm_math(r["question_text"]) for r in db.rows("SELECT id, question_text FROM questions")}


def expression_hits(text: str) -> tuple[str | None, list[str]]:
    """(expression, question ids containing it) for the most specific expression in the request."""
    qm = _question_maths()
    for e in sorted(request_expressions(text), key=len, reverse=True):
        pat = _re.compile(_re.escape(e) + r"(?![a-z0-9^])")
        ids = [q for q, t in qm.items() if pat.search(t)]
        if 0 < len(ids) <= MAX_EXPR_HITS:
            return e, ids
    return None, []


def find_practice(text: str, exclude_questions: set[str] = frozenset(), k: int = 5) -> dict:
    """Questions that genuinely practise what the student asked for, using the tags.

    A question qualifies only if it is tagged with the best-matching skill (or one within
    SKILL_MARGIN of it), or is of a strongly matching question type. Questions already seen,
    and those whose matching part uses an excluded skill ("not a binomial"), are skipped.
    Current-spec (9MA0) questions come first, then by how many target skills they cover."""
    req = parse_request(text)
    skills, qtype = _targets(req["positive"])
    use_qtype = qtype if qtype and (qtype[1] >= STRONG_QTYPE or (skills and qtype[1] >= skills[0][1])) else None
    neg_skills, neg_types = set(), set()
    for phrase in req["negatives"]:
        s2, q2 = _targets(phrase)
        neg_skills |= {s for s, _ in s2}
        if q2 and q2[1] >= 0.72:
            neg_types.add(q2[0])
    neg_skills -= {s for s, _ in skills}  # never exclude what was asked for

    parts, _, _ = _catalogue()
    qinfo = {r["id"]: r for r in db.rows("SELECT id, component, status, qualification, sitting FROM questions")}
    qtypes = {r["question_id"]: r["tag_value"] for r in db.rows(
        "SELECT question_id, tag_value FROM question_tags WHERE tag_type = 'question_type'")}
    weight = {s: (1.0 if i == 0 else 0.6) for i, (s, _) in enumerate(skills)}
    best: dict[str, tuple] = {}
    for key, p in parts.items():
        qid = p["question_id"]
        info = qinfo.get(qid)
        if qid in exclude_questions or info is None:
            continue
        if req["component"] and info["component"] != req["component"]:
            continue
        if qtypes.get(qid) in neg_types or (p["skills"] & neg_skills):
            continue
        hit = [s for s in weight if s in p["skills"]]
        type_hit = use_qtype is not None and qtypes.get(qid) == use_qtype[0]
        # The tagged skill is required; a matching question type only ranks (it admits a question
        # on its own only when no skill matched the request at all).
        if not hit and (skills or not type_hit):
            continue
        score = sum(weight[s] for s in hit) + (1.5 if type_hit else 0.0) + (0.4 if info["status"] == "current" else 0.0)
        if qid not in best or score > best[qid][0]:
            best[qid] = (score, p["label"], hit, type_hit)
    year = lambda q: int(_re.search(r"\d{4}", qinfo[q]["sitting"]).group())
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], -year(kv[0])))[:k]
    titles = {r["id"]: r["title"] for r in db.rows("SELECT id, title FROM skills")}
    type_titles = {r["id"]: r["title"] for r in db.rows("SELECT id, title FROM question_types")}
    items = []
    expr, expr_ids = expression_hits(req["positive"])
    if expr_ids:                                   # exact expression matches first, current spec first, newest first
        expr_ids = [q for q in expr_ids if q in qinfo and q not in exclude_questions
                    and not (req["component"] and qinfo[q]["component"] != req["component"])]
        expr_ids.sort(key=lambda q: (qinfo[q]["status"] != "current", -year(q)))
        for qid in expr_ids[:k]:
            why = "contains " + _re.sub(r"\^\(([^()]*)\)", lambda m: "^" + (m.group(1) if len(m.group(1)) == 1 else "{" + m.group(1) + "}"), expr)
            if qinfo[qid]["status"] != "current":
                why += f" · {qinfo[qid]['qualification']} (legacy/international)"
            items.append({"question_id": qid, "part_label": None, "reason": why})
        ranked = [kv for kv in ranked if kv[0] not in expr_ids][:max(0, k - len(items))]
    for qid, (score, label, hit, type_hit) in ranked:
        why = ", ".join(titles[s] for s in hit) or (type_titles.get(use_qtype[0], "") if use_qtype else "")
        if qinfo[qid]["status"] != "current":
            why += f" · {qinfo[qid]['qualification']} (legacy/international)"
        items.append({"question_id": qid, "part_label": label, "reason": why})
    return {"request": req, "expression": expr, "skills": [s for s, _ in skills], "question_type": use_qtype[0] if use_qtype else None,
            "excluded_skills": sorted(neg_skills), "items": items}
