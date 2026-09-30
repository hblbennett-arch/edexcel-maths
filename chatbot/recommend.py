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
    perf = ({(r["question_id"], r["part_label"]): r for r in db.rows("SELECT * FROM question_performance")}
            if db.has_table("question_performance") else {})  # clean packs have no performance data
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
    year = lambda s: int("".join(ch for ch in s if ch.isdigit()) or 0)  # (our own items: no sitting year)
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


def _target(question_id: str, part_label: str | None) -> dict:
    """The part's catalogue entry; with no part chosen on a multi-part question, the whole question
    (all its parts' skills, as broad() uses)."""
    parts, _, _ = _catalogue()
    key = db.part_key(question_id, part_label)
    if key in parts:
        return parts[key]
    mine = [p for p in parts.values() if p["question_id"] == question_id]
    return {"skills": set().union(*(p["skills"] for p in mine)),
            "core_skills": set().union(*(p["core_skills"] for p in mine))}


def similar_parts(question_id: str, part_label: str | None, limit: int = 5) -> list[dict]:
    """Parts elsewhere that share the most (weighted) skills with this part."""
    parts, weight, _ = _catalogue()
    target = _target(question_id, part_label)["skills"]
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
    target = _target(question_id, part_label)
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
# Lead-ins of multi-topic requests ("can you find a question that use the following topics of …").
_LEAD = _re.compile(r"\b(?:(?:can|could) you )?find\b|\b(?:is there|are there|i need|(?:i.?m |i am )?looking(?: for)?|any)\b|\b(?:that|which) (?:uses?|has|have|tests?|covers?|combines?|links?|"
                    r"involves?|includes?|mixes)\b|\b(?:(?:the )?following|these|both|all of)\b|"
                    r"\b(?:topics?|skills?|techniques?)(?: of| like| such as)?\b|:|\b(?:combining|linking|covering|"
                    r"mixing|in it|where i (?:have|need) to|i (?:have|need) to)\b", _re.I)
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
    for rx in [_YEAR] + [rx for rx, _ in _QUAL_WORDS]:     # filters, not content ("from 2019", "IAL")
        positive = rx.sub(" ", positive)
    core = _re.sub(r"\s+", " ", _LEAD.sub(" ", _FLUFF.sub(" ", positive))).strip(" ?.!,")
    core = _re.sub(r"^(?:and|,)\s*|\s*(?:and|,)$", "", core).strip()
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


# ---- three channels for "find me a question …" (2026-09-27) -------------------------------------------
# 1. exact maths    expression_hits(): the request's expression appears in the question (listed first)
# 2. description    keyword search over whole questions ("dentists and 10% of customers arriving late"):
#                   used when no skill matches the request well, or when one question clearly wins
# 3. skill tags     one technique -> tagged parts (unchanged); several topics/skills ("differentiation,
#                   partial fractions and stationary points") -> questions covering as many as possible
# Thresholds calibrated on eval/practice_search_eval.py (calibrate half, confirmed on the held-out half).
STRONG_SKILL = 0.75        # a skill matched this well is a technique request whatever else it says
WEAK_SKILL = 0.65          # between WEAK and STRONG (technique requests go down to 0.685, typos and all;
                           #   scenarios up to 0.707) it's a technique request if its words are mostly maths
MATHS_SHARE = 0.75         #   vocabulary (technique requests: 100%; scenarios: median 0%, max 75%). Tried and
                           #   dropped: "the top description hits carry the skill" (scenario words find
                           #   same-topic questions, so it sent 5% of descriptions down the skill route)
CONCEPT_MIN = 0.70         # a comma/"and" segment is a topic only if it matches a skill or group this well
MERGE_EPS = 0.06           # "differentiate exponentials and logarithms" stays one topic when the whole
                           #   matches this much better than either half (see split_concepts). Calibrate half,
                           #   topics top-1: 0.0 -> 79%, 0.02 -> 91%, 0.06..0.15 -> 97% (plateau)
GROUP_DELTA = 0.03         # a segment means a whole group ("stationary points") when the group matches
                           #   within this of the best single skill
GROUP_MARGIN = 0.0         # only the best group (0.02/0.04 were 1 case worse on the calibrate half)
# A single request naming a whole topic ("vectors", "stationary points", "differentiation": every word is in
# the topic's title) counts every skill of the topic(s). A qualifier ("hypothesis testing with the normal
# distribution", "parametric to cartesian") keeps the specific skill.
LEXICAL_GROUPS = True      # a topic phrase that is a group's name (named_groups) means that group
DESC_CLEAR_RATIO = 2.0     # BM25 top / second at least this -> the description has a clear winner
_SPLIT = _re.compile(r"\s*(?:,|;|\+|&|\band\b|\bplus\b|\bas well as\b|\balong with\b|\btogether with\b|"
                     r"\bcombined with\b|\bfollowed by\b|\bthen\b)\s*")
_YEAR = _re.compile(r"\b(?:from|in|june|jan(?:uary)?|oct(?:ober)?|nov(?:ember)?|may|summer|winter)\s+(?:the\s+)?((?:19|20)\d\d)\b|"
                    r"\b((?:19|20)\d\d)(?:'s)?(?=\s+(?:\w+\s+)?(?:paper|exam|question))", _re.I)
_QUAL_WORDS = [(_re.compile(r"\b(?:from )?(?:the )?(?:ial|international)(?: a level)?\b", _re.I), {"IAL-2018", "IAL-2013"}),
               (_re.compile(r"\b(?:from )?(?:the )?(?:(?:old|legacy|pre-?2017)\s*(?:spec|specification|papers?|a level)|gce)\b", _re.I),
                {"GCE-2008"}),
               (_re.compile(r"\b(?:from )?(?:the )?(?:(?:new|current)\s*(?:spec|specification)|9ma0)\b", _re.I), {"9MA0"})]


@lru_cache(maxsize=1)
def _maths_vocab() -> frozenset[str]:
    """Stemmed words used by the skill, group and question-type definitions."""
    words = set()
    for sql in ("SELECT id || ' ' || title || ' ' || COALESCE(description, '') AS t FROM skills",
                "SELECT id || ' ' || title || ' ' || COALESCE(definition, '') AS t FROM question_types",
                "SELECT title AS t FROM skill_groups"):
        for r in db.rows(sql):
            words |= set(_stems(r["t"].replace("-", " ")))
    return frozenset(words)


def maths_share(text: str) -> float:
    words = [w for w in _stems(text) if w.isalpha()]
    return sum(w in _maths_vocab() for w in words) / len(words) if words else 0.0


def _stem(w: str) -> str:
    """Crude suffix stripping so 'dentists'/'dentist' and 'arriving'/'arrive' match."""
    for suf in ("ies", "ing", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3 and not (suf == "s" and w.endswith("ss")):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def _stems(text: str) -> list[str]:
    from .text import tokens
    return [_stem(t) for t in tokens(text)]


@lru_cache(maxsize=1)
def _question_bm25():
    """BM25 over whole questions with stemmed tokens (the shared index keeps exact tokens for pasted text)."""
    from rank_bm25 import BM25Okapi
    from .text import latex_to_plain
    qs = db.rows("SELECT id, question_text FROM questions ORDER BY id")
    return [q["id"] for q in qs], BM25Okapi([_stems(latex_to_plain(q["question_text"])) or ["_"] for q in qs])


@lru_cache(maxsize=1)
def _part_bm25():
    from rank_bm25 import BM25Okapi
    from .text import latex_to_plain
    ps = db.rows("SELECT question_id, label, text FROM question_parts ORDER BY question_id, part_index")
    by_question: dict[str, list[int]] = {}
    for i, p in enumerate(ps):
        by_question.setdefault(p["question_id"], []).append(i)
    return ([p["label"] for p in ps], by_question,
            BM25Okapi([_stems(latex_to_plain(p["text"])) or ["_"] for p in ps]))


def description_hits(text: str, allowed) -> tuple[list[tuple[str, float]], bool]:
    """Questions whose wording matches the request, best first, as (question id, BM25 score), and whether
    the top one is a clear winner. Only questions passing allowed(qid) are ranked."""
    ids, bm25 = _question_bm25()
    q = _stems(text)
    if not q:
        return [], False
    sc = bm25.get_scores(q)
    ranked = sorted(((ids[i], float(sc[i])) for i in range(len(ids)) if sc[i] > 0 and allowed(ids[i])),
                    key=lambda t: -t[1])[:20]
    clear = bool(ranked) and (len(ranked) == 1 or ranked[0][1] >= DESC_CLEAR_RATIO * ranked[1][1])
    return ranked, clear


def best_part(text: str, question_id: str) -> str | None:
    """The part whose own text matches the request clearly best, else None (open the whole question)."""
    labels, by_question, bm25 = _part_bm25()
    idx = by_question.get(question_id, [])
    if len(idx) < 2:
        return None
    sc = sorted(zip(bm25.get_batch_scores(_stems(text), idx), idx), reverse=True)
    return labels[sc[0][1]] if sc[0][0] > 0 and sc[0][0] >= 1.3 * sc[1][0] else None


@lru_cache(maxsize=1)
def _group_vectors():
    from .search import embed
    gs = db.rows("SELECT id, title FROM skill_groups WHERE id != ?", (db.EXAM_TECHNIQUE_GROUP,))
    members: dict[str, list] = {}
    for r in db.rows("SELECT id, title, group_id FROM skills"):
        members.setdefault(r["group_id"], []).append(r)
    texts = [f"{g['title']}: " + "; ".join(m["title"] for m in members.get(g["id"], [])) for g in gs]
    return [g["id"] for g in gs], embed(texts), {g: {m["id"] for m in v} for g, v in members.items()}


def resolve_concept(text: str) -> dict:
    """What one topic/skill phrase means as a set of skills: the best skills (within SKILL_MARGIN) and, when
    the phrase names a whole area ("stationary points", "differentiation"), every skill of the best groups."""
    from .search import get_index, embed_query
    ix = get_index()
    _, _, groups = _catalogue()
    ids, _, sem = ix.scores(text, "skill")
    hits = sorted(((i.split(":", 1)[1], float(v)) for i, v in zip(ids, sem)), key=lambda t: -t[1])
    hits = [(s, v) for s, v in hits if groups.get(s) != db.EXAM_TECHNIQUE_GROUP]
    top = hits[0][1] if hits else 0.0
    weights = {s: v for s, v in hits[:3] if v >= top - SKILL_MARGIN}   # skill -> how well it matches
    gids, gvecs, members = _group_vectors()
    gs = sorted(zip(gids, (gvecs @ embed_query(text)).tolist()), key=lambda t: -t[1])
    gtop = gs[0][1]
    used_groups = []
    named = named_groups(text) if LEXICAL_GROUPS else set()
    if named:                                   # "logarithms", "functions": the topics with that name, and
        used_groups = [(g, v) for g, v in gs if g in named]   # only their skills ("quadratics" must not
        weights = {s: v for s, v in weights.items() if groups.get(s) in named}  # bring in trig quadratics)
        gtop = max(gtop, top)
    elif gtop >= top - GROUP_DELTA:
        used_groups = [(g, v) for g, v in gs[:3] if v >= gtop - GROUP_MARGIN]
    for g, v in used_groups:
        for s in members.get(g, set()):
            weights[s] = max(weights.get(s, 0.0), v)
    return {"text": text, "sim": max(top, gtop), "skills": set(weights), "weights": weights,
            "groups": {g for g, _ in used_groups}, "best": hits[0][0] if hits else None}


@lru_cache(maxsize=1)
def _group_title_stems() -> dict[str, set[str]]:
    return {g["id"]: set(_stems(g["title"] + " " + g["id"].replace("-", " ")))
            for g in db.rows("SELECT id, title FROM skill_groups WHERE id != ?", (db.EXAM_TECHNIQUE_GROUP,))}


@lru_cache(maxsize=1)
def _skill_name_stems() -> set[frozenset[str]]:
    return {frozenset(_stems(r["id"].replace("-", " "))) for r in db.rows("SELECT id FROM skills")} | \
           {frozenset(_stems(r["title"])) for r in db.rows("SELECT title FROM skills")}


def named_groups(text: str) -> set[str]:
    """Topics whose title contains every word of the text ("differentiation" -> basic and implicit/parametric),
    unless the text is exactly a skill's name ("chain rule", "composite functions")."""
    words = set(_stems(text))
    if not words or frozenset(words) in _skill_name_stems():
        return set()
    return {g for g, t in _group_title_stems().items() if words <= t}


def _same_topic(a: dict, b: dict) -> bool:
    return a["best"] in b["skills"] or b["best"] in a["skills"] or bool(a["groups"] & b["groups"])


def split_concepts(text: str) -> list[dict]:
    """Split "differentiation, partial fractions and stationary points" into topics. Adjacent pieces are
    joined back while the joined phrase matches at least as well ("interpolation and extrapolation").
    Returns [] unless at least two distinct topics are found."""
    atoms = [a.strip() for a in _SPLIT.split(text) if a and a.strip() and len(a.strip()) > 1]
    if len(atoms) < 2:
        return []
    segs = [resolve_concept(a) for a in atoms]
    # Join neighbours when one isn't a topic on its own ("increasing" + "decreasing functions"), when both
    # mean the same area ("tangents" + "normals", "polynomials" + "factor theorem"), when the joined phrase
    # is a skill's name ("differentiate exponentials and logarithms"), or is clearly a better match.
    while len(segs) > 1:
        cands = []
        for i in range(len(segs) - 1):
            a, b = segs[i], segs[i + 1]
            m = resolve_concept(a["text"] + " and " + b["text"])
            if (min(a["sim"], b["sim"]) < CONCEPT_MIN <= m["sim"] or _same_topic(a, b)
                    or frozenset(_stems(m["text"])) in _skill_name_stems()   # a skill's own name
                    or m["sim"] >= max(a["sim"], b["sim"]) + MERGE_EPS):
                cands.append((m["sim"], i, m))
        if not cands:
            break
        _, i, m = max(cands, key=lambda t: t[0])
        segs[i:i + 2] = [m]
    out = [c for c in segs if c["sim"] >= CONCEPT_MIN]
    if len(out) < 2:
        return []
    # A skill near two topics ("suvat" also brings in projectile skills) counts only for the closer one,
    # so one part can't cover two topics with the same skill.
    for c in out:
        c["skills"] = {s for s in c["skills"] if s == c["best"]
                       or all(c["weights"][s] >= o["weights"].get(s, 0.0) for o in out if o is not c)}
    return out


def _legacy_note(info) -> str:
    return f" · {info['qualification']} (legacy/international)" if info["status"] != "current" else ""


def find_practice(text: str, exclude_questions: set[str] = frozenset(), k: int = 5) -> dict:
    """Questions for a practice request ("find me a question on …"), from three channels (see above).

    Single technique: a question qualifies only if it is tagged with the best-matching skill (or one within
    SKILL_MARGIN of it), or is of a strongly matching question type; current-spec (9MA0) first.
    Several topics/skills: questions covering the most of them, whole question (a part if one covers all).
    Described scenario (no skill matches well): the questions whose wording matches best.
    Every channel skips questions already seen, the wrong component, and excluded skills/types ("not a
    binomial"); a year ("from 2019") or qualification ("IAL", "old spec") in the request filters too."""
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
    year = lambda q: int((_re.search(r"\d{4}", qinfo[q]["sitting"]) or [0])[0])  # 0: our own items have no year
    ym = _YEAR.search(text)
    want_year = int(ym.group(1) or ym.group(2)) if ym else None
    want_quals = next((q for rx, q in _QUAL_WORDS if rx.search(text)), None)
    if want_year and not any(year(q) == want_year for q in qinfo):
        want_year = None
    q_parts: dict[str, list[str]] = {}
    for key, p in parts.items():
        q_parts.setdefault(p["question_id"], []).append(key)

    def allowed(qid: str, strict_neg: bool = True) -> bool:
        info = qinfo.get(qid)
        if info is None or qid in exclude_questions:
            return False
        if req["component"] and info["component"] != req["component"]:
            return False
        if (want_year and year(qid) != want_year) or (want_quals and info["qualification"] not in want_quals):
            return False
        if qtypes.get(qid) in neg_types:
            return False
        return not (strict_neg and neg_skills and any(parts[k]["skills"] & neg_skills for k in q_parts.get(qid, [])))

    titles = {r["id"]: r["title"] for r in db.rows("SELECT id, title FROM skills")}
    type_titles = {r["id"]: r["title"] for r in db.rows("SELECT id, title FROM question_types")}
    items: list[dict] = []
    taken: set[str] = set()

    def add(qid: str, label: str | None, why: str) -> None:
        if qid not in taken and len(items) < k:
            taken.add(qid)
            items.append({"question_id": qid, "part_label": label, "reason": why + _legacy_note(qinfo[qid])})

    # 1. exact expression matches first, current spec first, newest first
    expr, expr_ids = expression_hits(req["positive"])
    if expr_ids:
        expr_ids = sorted((q for q in expr_ids if allowed(q)), key=lambda q: (qinfo[q]["status"] != "current", -year(q)))
        shown = _re.sub(r"\^\(([^()]*)\)", lambda m: "^" + (m.group(1) if len(m.group(1)) == 1 else "{" + m.group(1) + "}"), expr)
        for qid in expr_ids:
            add(qid, None, "contains " + shown)

    # 2. description search
    desc, desc_clear = description_hits(req["positive"], allowed)
    desc_rank = {q: i for i, (q, _) in enumerate(desc)}
    strong = bool(skills) and (skills[0][1] >= STRONG_SKILL or
                               (skills[0][1] >= WEAK_SKILL and maths_share(req["positive"]) >= MATHS_SHARE))

    concepts = split_concepts(req["positive"]) if not expr_ids else []
    covering: list[tuple] = []
    if concepts:
        # 3b. several topics/skills: questions covering the most of them
        for qid, keys in q_parts.items():
            if not allowed(qid):
                continue
            got = [c for c in concepts if any(parts[key]["skills"] & c["skills"] for key in keys)]
            if len(got) < 2:
                continue
            one = [key for key in keys if all(parts[key]["skills"] & c["skills"] for c in got)]
            covering.append((len(got), qid, parts[one[0]]["label"] if one and len(keys) > 1 else None, got))
        covering.sort(key=lambda t: (-t[0], qinfo[t[1]]["status"] != "current", desc_rank.get(t[1], 99), -year(t[1])))
    if covering:
        if desc_clear and any(desc[0][0] == t[1] and t[0] == covering[0][0] for t in covering):
            covering.sort(key=lambda t: t[1] != desc[0][0])  # the described question first, if it covers as much
        for n_got, qid, label, got in covering:
            names = ", ".join(c["text"] for c in got)
            add(qid, label, f"covers {names}" if n_got == len(concepts) else f"covers {n_got} of {len(concepts)}: {names}")
    elif not strong:
        # 2. no skill matches: the description decides, best keyword match first (legacy papers reuse a
        #    scenario with new numbers, so near-duplicates are all listed; numbers count as words, so the
        #    variant with the request's "10%" ranks first), then the questions closest in meaning
        for qid, _ in desc:
            add(qid, best_part(req["positive"], qid), "matches your description")
        if len(items) < k:
            from .search import get_index
            ids, _, sem = get_index().scores(req["positive"], "question")
            for i in sorted(range(len(ids)), key=lambda i: -sem[i]):
                qid = ids[i].split(":", 1)[1]
                if len(items) >= k:
                    break
                if allowed(qid):
                    add(qid, None, "similar to your description")

    # 3a. one technique: tagged parts (today's ranking). A request naming a whole topic ("vectors",
    #     named_groups) counts every skill of that topic.
    weight = {s: (1.0 if i == 0 else 0.6) for i, (s, _) in enumerate(skills)}
    topic = named_groups(req["positive"]) if strong and not concepts else set()
    if topic:
        members = _group_vectors()[2]
        group_skills = sorted({s for g in topic for s in members.get(g, set())}, key=lambda s: s not in weight)
        weight = {s: 1.0 for s in group_skills}
        skills = [(s, skills[0][1]) for s in group_skills]
    best: dict[str, tuple] = {}
    for key, p in parts.items():
        qid = p["question_id"]
        if not allowed(qid, strict_neg=False) or (p["skills"] & neg_skills):
            continue
        hit = [s for s in weight if s in p["skills"]]
        type_hit = use_qtype is not None and qtypes.get(qid) == use_qtype[0]
        # The tagged skill is required; a matching question type only ranks (it admits a question
        # on its own only when no skill matched the request at all).
        if not hit and (skills or not type_hit):
            continue
        # (a whole topic: any of its skills qualifies; a few together rank only slightly higher)
        base = 1.0 + 0.1 * min(len(hit) - 1, 2) if topic and hit else sum(weight[s] for s in hit)
        score = base + (1.5 if type_hit else 0.0) + (0.4 if qinfo[qid]["status"] == "current" else 0.0)
        if qid not in best or score > best[qid][0]:
            best[qid] = (score, p["label"], hit, type_hit)
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0], -year(kv[0])))
    if strong and desc_clear and desc[0][0] in best and not covering:
        ranked.sort(key=lambda kv: kv[0] != desc[0][0])  # a tagged question the description clearly picks
    for qid, (score, label, hit, type_hit) in ranked:
        why = ", ".join(titles[s] for s in hit) or (type_titles.get(use_qtype[0], "") if use_qtype else "")
        add(qid, label, why)
    return {"request": req, "expression": expr, "skills": [s for s, _ in skills],
            "question_type": use_qtype[0] if use_qtype else None, "excluded_skills": sorted(neg_skills),
            "concepts": [{"text": c["text"], "skills": sorted(c["skills"])} for c in concepts],
            "description_clear": desc_clear, "items": items}
