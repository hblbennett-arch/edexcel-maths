"""Work out what the student is asking about.

    identify("2022 paper 1 question 15b")          -> reference      P1_June2022_Q15, part b
    identify("<pasted question text>")             -> pasted_match   the stored question it matches
    identify("<a question we don't have>")         -> new_question   (answered without an official MS)
    identify("how do I integrate x e^x?")          -> generic        (search skills / parts / notes)

The bot should always confirm a match with the student before teaching
("Is this P1 June 2022 Q15, the cheese-shaped toy?"), using `summary()`.
"""
import re
from dataclasses import dataclass, field

from . import db
from .search import get_index
from .text import latex_to_plain

# Pasted-question decision, calibrated on eval/retrieval.py (30 real pastes, 6 questions we
# don't have): keyword score per query token and lead over the runner-up separate them best.
CONFIDENT_PER_TOKEN = 2.0      # BM25 score / number of query tokens
CONFIDENT_LEAD = 1.10          # top BM25 score / second-best
CONFIDENT_SEMANTIC = 0.90      # ...or a near-identical meaning
CONFIDENT_MIN_SEMANTIC = 0.85  # keyword overlap alone isn't enough: "sum of three consecutive integers is a multiple
                               # of 3" scored high on keywords against "…consecutive primes…multiple of 5" (0.825)
CLEAR_LEAD = 1.05              # ...as long as no other stored question scores almost as well
POSSIBLE_SEMANTIC = 0.85       # below confident but plausible -> ask the student to confirm
POSSIBLE_PER_TOKEN = 1.6


@dataclass
class Identification:
    kind: str  # "reference" | "ambiguous" (ask which) | "pasted_match" | "possible_match" (ask first)
    #            | "new_question" | "generic"
    question_id: str | None = None
    part_label: str | None = None
    confidence: float = 0.0
    candidates: list[tuple[str, float]] = field(default_factory=list)
    message: str = ""              # explains a problem, e.g. "no June 2020 paper exists"


# ---- references to a paper ------------------------------------------------------------------
# What students call each paper -> (qualification filter, units). Longest/most specific first.
# "paper 1"/"P1" means 9MA0 unless the student says IAL/international (or 9MA0 has no such sitting).
UNIT_NAMES = [
    (r"\b9ma0\s*/?\s*31\b|\bpaper\s*31\b|\b(?:paper|p)\s*3\s*(?:stats|statistics|s)\b|\bstat(?:istic)?s paper\b", None, {"9MA0-31", "9MA0-03"}),
    (r"\b9ma0\s*/?\s*32\b|\bpaper\s*32\b|\b(?:paper|p)\s*3\s*(?:mech|mechanics|m)\b|\bmech(?:anics)? paper\b", None, {"9MA0-32", "9MA0-03"}),
    (r"\b9ma0\s*/?\s*0?3\b", None, {"9MA0-31", "9MA0-32", "9MA0-03"}),
    (r"\b9ma0\s*/?\s*0?1\b", None, {"9MA0-01"}),
    (r"\b9ma0\s*/?\s*0?2\b", None, {"9MA0-02"}),
    (r"\bwma\s*1\s*([1-4])\b", "IAL", "WMA1{0}"),
    (r"\bwma\s*0\s*1\b|\bc\s*12\b", "IAL", {"WMA01"}),
    (r"\bwma\s*0\s*2\b|\bc\s*34\b", "IAL", {"WMA02"}),
    (r"\bwst\s*0?\s*1\b", "IAL", {"WST01"}),                 # an explicit IAL code is IAL only
    (r"\bwme\s*0?\s*1\b", "IAL", {"WME01"}),
    (r"\bs\s*1\b|\bstat(?:istic)?s\s*1\b", None, {"WST01", "6683"}),
    (r"\bm\s*1\b|\bmech(?:anics)?\s*1\b", None, {"WME01", "6677"}),
    (r"\b666([3-6])a?\b", None, "666{0}"),
    (r"\b6683\b", None, {"6683"}), (r"\b6677\b", None, {"6677"}),
    (r"\bc\s*([1-4])\b|\bcore\s*(?:maths?|mathematics)?\s*([1-4])\b", None, "C{0}"),
    (r"\b(?:paper|p|pure)\s*0?([1-4])\b", None, "P{0}"),
]
C_UNITS = {"1": "6663", "2": "6664", "3": "6665", "4": "6666"}
# Units that exist but aren't in the chatbot (user scope, 2026-09-26: legacy Stats/Mech = S1/M1 only; no Further Maths).
NOT_COVERED = re.compile(r"\b(?:s|m|stat(?:istic)?s|mech(?:anics)?)\s*[23]\b|\bw(?:st|me)\s*0?\s*[23]\b|\bfp?\s*[1-3]\b|"
                         r"\bfurther (?:pure|maths?|mathematics|stat|mech)|\bd\s*[12]\b|\bdecision\b|\b9fm0\b|\bwfm")
SERIES_WORDS = {"june": "June", "jun": "June", "summer": "June", "may": "June",
                "january": "Jan", "jan": "Jan", "winter": "Jan",
                "october": "Oct", "oct": "Oct", "autumn": "Oct", "november": "Oct", "nov": "Oct"}


def _papers() -> list[dict]:
    return [dict(r) for r in db.rows(
        "SELECT paper_id, qualification, unit, paper, sitting, component FROM questions GROUP BY paper_id")]


def _units_for(t: str) -> tuple[set[str] | None, str | None, bool]:
    """Units the text names (None = no unit named), a qualification filter, and whether the name was
    the generic 'paper N' (which prefers 9MA0)."""
    for rx, qual, units in UNIT_NAMES:
        m = re.search(rx, t)
        if not m:
            continue
        if isinstance(units, set):
            return units, qual, False
        d = next(g for g in m.groups() if g)
        if units == "WMA1{0}":
            return {f"WMA1{d}"}, "IAL", False
        if units == "666{0}":
            return {f"666{d}"}, None, False
        if units == "C{0}":
            return {C_UNITS[d]}, None, False
        if units == "P{0}":                               # 9MA0 Paper N, or IAL Pure N (WMA1N)
            s = {f"9MA0-0{d}", f"WMA1{d}"} if d in "12" else ({"9MA0-31", "9MA0-32", "9MA0-03", "WMA13"} if d == "3" else {"WMA14"})
            return s, None, True
    return None, None, False


def parse_reference(text: str) -> Identification | None:
    """Recognise references to a stored paper + question, e.g. "P1 June 2022 Q15(b)", "2022 paper 1
    question 15 part b", "9MA0/02 June 22 Q15", "S1 January 2020 Q3", "WST01 Jan 20 q3", "M1 June 2012
    question 4", "C34 June 2016 Q7", "IAL P3 January 2024 Q2", "paper 3 stats 2019 Q2".
    Returns None if there's no question number + year. Asks (kind "ambiguous") when several stored
    papers fit, e.g. an IAL and a UK S1 from the same series, or the A/R versions of a paper."""
    t = text.lower()
    t = re.sub(r"[_\-]", " ", t)
    t = re.sub(r"(?<=[a-z])(?=\d{4})|(?<=\d)(?=[a-z]{3,})", " ", t)   # "june2023" / "2023june"
    ial = bool(re.search(r"\bial\b|\binternational\b|\bias?\s*level\b(?=.*international)", t))
    gce = bool(re.search(r"\bgce\b|\bold (?:uk )?spec|\blegacy\b|\buk\b|\bbritish\b|\bpre[- ]?2017\b", t))
    t2 = re.sub(r"\b(?:q|qu|question|no\.?)\s*\d{1,2}(?!\d)(?:\s*(?:part\s*)?\(?[a-h]\)?)?", " ", t)  # drop "question 5(b)"
    if NOT_COVERED.search(t2):
        return Identification("reference", message=(
            "That paper isn't in the knowledge base: for Statistics and Mechanics it covers A Level Paper 3 "
            "and the S1/M1 units (not S2, S3, M2, M3 or Further Maths)."))
    question = re.search(r"\b(?:q|qu|question|no\.?)\s*(\d{1,2})(?!\d)\s*(?:part\s*)?(?:\(?([a-h])\b\)?)?\s*(?:\(?(iv|i{1,3})\b\)?)?", t)
    year = re.search(r"\b(20(?:0[5-9]|1\d|2\d))\b", t)
    yy = None if year else re.search(r"\b(?:june|jun|summer|may|oct|october|autumn|nov|november|jan|january|winter)\s*'?(0[5-9]|1\d|2\d)\b|'(0[5-9]|1\d|2\d)\b", t)
    if not (question and (year or yy)):
        return None
    y = int(year.group(1)) if year else 2000 + int(yy.group(1) or yy.group(2))
    series = next((SERIES_WORDS[w] for w in re.findall(r"[a-z]+", t) if w in SERIES_WORDS), None)
    units, qual, generic = _units_for(t2)
    papers = _papers()
    in_year = [p for p in papers if p["sitting"].endswith(str(y)) and (series is None or p["sitting"].startswith(series))]
    if units is None:                                     # "question 9 from the 2024 paper" -> 9MA0 Pure
        units, generic = {"9MA0-01", "9MA0-02"}, True
    cands = [p for p in in_year if p["unit"] in units]
    # "P3 June 2019 statistics Q4": a component word anywhere picks Paper 3 Stats or Mech
    if re.search(r"\bstat(?:istic)?s\b", t2) and any(p["component"] == "stats" for p in cands):
        cands = [p for p in cands if p["component"] == "stats" or p["unit"] == "9MA0-03"]
    elif re.search(r"\bmech(?:anics)?\b", t2) and any(p["component"] == "mech" for p in cands):
        cands = [p for p in cands if p["component"] == "mech" or p["unit"] == "9MA0-03"]
    if qual == "IAL" or ial:
        cands = [p for p in cands if p["qualification"].startswith("IAL")]
    elif gce:
        cands = [p for p in cands if p["qualification"] == "GCE-2008"]
    elif generic and any(p["qualification"] == "9MA0" for p in cands):
        cands = [p for p in cands if p["qualification"] == "9MA0"]
    qn = int(question.group(1))
    have = [p for p in cands if db.one("SELECT 1 FROM questions WHERE id = ?", (f"{p['paper_id']}_Q{qn}",))]
    if not have:
        if not cands:
            unit_papers = sorted({p["sitting"] for p in papers if p["unit"] in units}, key=lambda s: (s[-4:], s))
            return Identification("reference", message=(
                f"I don't have that paper from {series + ' ' if series else ''}{y}. "
                + (f"Available sittings: {', '.join(unit_papers)}." if unit_papers else "")))
        p = cands[0]
        n = db.one("SELECT count(*) AS n FROM questions WHERE paper_id = ?", (p["paper_id"],))["n"]
        return Identification("reference", message=f"{paper_label(p['paper_id'])} has {n} questions in the knowledge "
                                                   f"base; there is no Q{qn} (some questions are excluded as outside 9MA0).")
    if len(have) > 1:
        options = [(f"{p['paper_id']}_Q{qn}", 1.0) for p in have]
        return Identification("ambiguous", None, None, 0.0, options,
                              message="Which paper? " + " or ".join(summary(q) for q, _ in options))
    qid = f"{have[0]['paper_id']}_Q{qn}"
    label = None
    if question.group(2):
        label = question.group(2) + (f"({question.group(3)})" if question.group(3) else "")
        labels = [r["label"] for r in db.rows("SELECT label FROM question_parts WHERE question_id = ?", (qid,))]
        if label not in labels:
            parent = question.group(2)
            label = parent if any(l and l.startswith(parent) for l in labels) else None
    return Identification("reference", qid, label, 1.0)


QUAL_LABEL = {"9MA0": "A Level", "IAL-2018": "International A Level (2018 spec)",
              "IAL-2013": "International A Level (2013 spec)", "GCE-2008": "old UK A Level (pre-2017 spec)"}
UNIT_LABEL = {"9MA0-01": "Paper 1", "9MA0-02": "Paper 2", "9MA0-31": "Paper 3 Statistics", "9MA0-32": "Paper 3 Mechanics",
              "9MA0-03": "Paper 3", "WMA11": "P1", "WMA12": "P2", "WMA13": "P3", "WMA14": "P4", "WMA01": "C12",
              "WMA02": "C34", "WST01": "S1", "WME01": "M1", "6663": "C1", "6664": "C2", "6665": "C3", "6666": "C4",
              "6683": "S1", "6677": "M1"}


def paper_label(paper_id: str) -> str:
    """'IAL2018_WST01_Jan2020' -> 'International A Level (2018 spec) S1 (WST01) Jan 2020'."""
    r = db.one("SELECT qualification, unit, paper, sitting FROM questions WHERE paper_id = ? LIMIT 1", (paper_id,))
    if not r:
        return paper_id
    sit = re.sub(r"(\D+)(\d{4})", r"\1 \2", r["sitting"])
    unit = UNIT_LABEL.get(r["unit"], r["unit"])
    code = "" if r["qualification"] == "9MA0" else f" ({r['paper']})"
    return f"{QUAL_LABEL.get(r['qualification'], r['qualification'])} {unit}{code} {sit}"


def match_pasted(text: str, k: int = 5) -> Identification:
    """Match pasted question text against the stored questions (see the thresholds above)."""
    import numpy as np
    from .text import tokens
    ix = get_index()
    ids, kw = ix.bm25_scores(text, "question")
    order = np.argsort(-kw)[:k]
    candidates = [(ids[i].split(":", 1)[1], round(float(kw[i]), 1)) for i in order]
    n_tok = max(len(tokens(text)), 1)
    per_token = kw[order[0]] / n_tok
    lead = kw[order[0]] / max(kw[order[1]], 1e-9)
    top_id = f"question:{candidates[0][0]}"
    sem = next((h.semantic for h in ix.search(text, "question", k=k, mode="semantic") if h.doc_id == top_id), 0.0)
    # Near-duplicates are common across IAL/GCE sittings (the same question reused with new numbers), so a
    # strong semantic match only counts when the runner-up isn't close (lead >= CLEAR_LEAD); otherwise the
    # bot asks the student which paper they mean.
    # Number agreement: GCE/IAL reuse a question with new numbers, and with ~2,700 questions the keyword lead
    # alone can pick the wrong sitting (eval 2026-09-27: "a_{n+1}=5a_n+3" matched the R paper's "4a_n-3").
    # Among close candidates, prefer the one containing the pasted numbers; be confident only if exactly one does.
    agree = {cid: number_agreement(text, cid) for cid, score in candidates[:3] if score >= kw[order[0]] / CONFIDENT_LEAD}
    if len(agree) > 1:
        best = max(agree.values())
        winners = [cid for cid, a in agree.items() if a == best]
        if winners[0] != candidates[0][0] or len(winners) > 1 or best < 1.0:
            top = winners[0]
            cands = [c for c in candidates if c[0] == top] + [c for c in candidates if c[0] != top]
            if len(winners) == 1 and best == 1.0 and sem >= CONFIDENT_MIN_SEMANTIC:
                return Identification("pasted_match", top, None, round(sem, 3), cands)
            return Identification("possible_match", top, None, round(sem, 3), cands,
                                  message="Not certain — confirm with the student before using this question's mark scheme.")
    if per_token >= CONFIDENT_PER_TOKEN and sem >= CONFIDENT_MIN_SEMANTIC and \
            (lead >= CONFIDENT_LEAD or (sem >= CONFIDENT_SEMANTIC and lead >= CLEAR_LEAD)):
        return Identification("pasted_match", candidates[0][0], None, round(sem, 3), candidates)
    if sem >= POSSIBLE_SEMANTIC or per_token >= POSSIBLE_PER_TOKEN:
        return Identification("possible_match", candidates[0][0], None, round(sem, 3), candidates,
                              message="Not certain — confirm with the student before using this question's mark scheme.")
    return Identification("new_question", None, None, round(sem, 3), candidates)


def number_agreement(text: str, question_id: str) -> float:
    """Share of the numbers in the pasted text that also appear in the stored question (1.0 if none pasted)."""
    nums = set(re.findall(r"\d+(?:\.\d+)?", text))
    if not nums:
        return 1.0
    q = db.one("SELECT question_text FROM questions WHERE id = ?", (question_id,))
    have = set(re.findall(r"\d+(?:\.\d+)?", latex_to_plain(q["question_text"]).lower()))
    return len(nums & have) / len(nums)


def looks_like_full_question(text: str) -> bool:
    words = len(latex_to_plain(text).split())
    return words >= 20 or bool(re.search(r"\((a|i)\)|\(\d+ marks?\)|show that|given that", text.lower()))


def identify(text: str) -> Identification:
    ref = parse_reference(text)
    if ref:
        return ref
    if looks_like_full_question(text):
        return match_pasted(text)
    return Identification("generic")


def summary(question_id: str) -> str:
    """One-line description for confirming a match with the student."""
    q = db.one("SELECT paper, paper_id, qualification, sitting, q_num, total_marks, question_text FROM questions WHERE id = ?",
               (question_id,))
    first = latex_to_plain(q["question_text"]).split(". ")[0][:110]
    if q["qualification"] != "9MA0":                      # legacy / IAL: always say which qualification
        return f"{paper_label(q['paper_id'])} Q{q['q_num']} ({q['total_marks']} marks): {first}…"
    sitting = re.sub(r"(\D+)(\d+)", r"\1 \2", q["sitting"]).replace("Oct", "October")
    paper = {"P3": "P3 " + ("Statistics" if q["paper_id"].endswith("_stats") else "Mechanics" if q["paper_id"].endswith("_mech") else "")}.get(q["paper"], q["paper"]).strip()
    return f"{paper} {sitting} Q{q['q_num']} ({q['total_marks']} marks): {first}…"
