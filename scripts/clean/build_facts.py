#!/usr/bin/env python3
"""Fact layer: the "Edexcel style fingerprint" (docs/handoff-clean-room.md §5.1).

    .venv/bin/python scripts/clean/build_facts.py        # reads pearson-private, writes content/facts/

Local and deterministic: regex and counting over the pearson-private pack, no model calls. Only
unprotected facts cross into content/facts/: ids, numbers and codes from the fixed vocabularies below
(scripts/clean/check_facts.py enforces this). No question, mark-scheme or examiner-report text.

Outputs
  parts.json       one record per question part: marks, skills, question type, mark-code sequence,
                   command words, answer forms, figure / no-calculator-technology flags, difficulty
  aggregates.json  distributions per question type and per skill; skill co-occurrence
  papers.json      paper-level facts for 9MA0 (questions, marks, question types per paper)
"""
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chatbot import pack as packs  # noqa: E402

OUT = ROOT / "content" / "facts"

# ---- mark codes ------------------------------------------------------------------------------
# A mark: M/A/B (dM, ddM, dB = dependent), a value 1-9, and an optional flag. "A0"/"M0" are notes
# about marks withheld, so value 0 is ignored.
CODE_RE = re.compile(r"(?<![A-Za-z])(ddM|dM|DM|dB|DB|M|A|B)([1-9])(\*|ft|cso|cao)?(?![0-9])")
# A notes line explains a mark: "M1: attempts ...", "(b) B1: ...".
NOTE_LINE_RE = re.compile(r"^\s*(?:\(?[a-z]{1,4}\)\s*)?(?:ddM|dM|DM|dB|DB|M|A|B)[1-9](?:\*|ft)?\s*:")
CODE_BASES = ("M", "dM", "ddM", "A", "B", "dB")
CODE_FLAGS = ("", "*", "ft", "cso", "cao")


def canon(m: re.Match) -> str:
    base = {"DM": "dM", "DB": "dB"}.get(m.group(1), m.group(1))
    return f"{base}{m.group(2)}{m.group(3) or ''}"


def _prefix_to_marks(matches: list[re.Match], marks: int) -> list[str] | None:
    """Shortest prefix of the codes whose values add up to the part's marks (later codes are
    alternative methods or notes repeating the same marks)."""
    total = 0
    for i, m in enumerate(matches):
        total += int(m.group(2))
        if total == marks:
            return [canon(x) for x in matches[:i + 1]]
        if total > marks:
            return None
    return None


def well_formed(codes: list[str]) -> bool:
    """Every A and dM mark comes after an M mark (the usual method-then-accuracy structure)."""
    seen_m = False
    for c in codes:
        if c.startswith(("A", "dM", "ddM")) and not seen_m:
            return False
        seen_m |= c.startswith(("M", "dM", "ddM"))
    return True


def mark_codes(ms: str, marks: int) -> tuple[list[str] | None, str]:
    """(codes in order, where they came from). Candidates: the mark lines, the notes lines ("M1: ..."),
    all codes. Each must add up exactly to the part's marks; the first well-formed one wins, else the
    first that adds up (source suffixed "-irregular"), else (None, "unresolved")."""
    lines = ms.split("\n")
    main = [m for ln in lines if not NOTE_LINE_RE.match(ln) for m in CODE_RE.finditer(ln)]
    notes = [m for ln in lines if NOTE_LINE_RE.match(ln) for m in CODE_RE.finditer(ln.split(":")[0])]
    found = [(src, codes) for src, cand in (("mark-lines", main), ("note-lines", notes),
                                            ("all", list(CODE_RE.finditer(ms))))
             if (codes := _prefix_to_marks(cand, marks))]
    for src, codes in found:
        if well_formed(codes):
            return codes, src
    if found:
        return found[0][1], found[0][0] + "-irregular"
    return None, "unresolved"


# ---- command words and answer forms (our own regexes over the part text) ------------------------
COMMANDS = {  # code -> pattern (case-insensitive)
    "find": r"\bfind\b", "show-that": r"\bshow that\b", "given-that": r"\bgiven that\b",
    "hence-or-otherwise": r"\bhence,? or otherwise\b", "hence": r"\bhence\b(?!,? or otherwise)",
    "use": r"(^|[.)]\s*)use\b", "state": r"\bstate\b", "solve": r"\bsolve\b", "sketch": r"\bsketch\b",
    "calculate": r"\bcalculate\b", "write-down": r"\bwrite down\b", "estimate": r"\bestimate\b",
    "simplify": r"\bsimplif(y|ied|ying)\b", "express": r"\bexpress\b", "prove": r"\bprove\b",
    "explain": r"\bexplain\b", "determine": r"\bdetermine\b", "test": r"\btest\b", "deduce": r"\bdeduce\b",
    "comment": r"\bcomment\b", "evaluate": r"\bevaluate\b", "verify": r"\bverify\b", "suggest": r"\bsuggest\b",
    "interpret": r"\binterpret\b", "criticise": r"\bcriti[cz]ise\b", "differentiate": r"\bdifferentiate\b",
    "integrate": r"\bintegrate\b", "expand": r"\bexpand\b", "factorise": r"\bfactori[sz]e\b",
    "describe": r"\bdescribe\b", "draw": r"\bdraw\b", "complete": r"\bcomplete\b", "label": r"\blabel\b",
}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
FORMS = {  # code -> pattern; dp-N / sf-N are built from the captured number
    "exact": r"\bexact\b", "in-the-form": r"\bin the form\b", "simplest-form": r"\bsimplest form\b",
    "in-terms-of": r"\bin terms of\b", "nearest": r"\bto the nearest\b", "degrees": r"\bdegrees?\b|°",
    "radians": r"\bradians?\b", "surd": r"\bsurds?\b", "fraction": r"\bas a (single )?fraction\b",
    "no-calc-tech": r"calculator technology",
}
DP_RE = re.compile(r"\b(\d|one|two|three|four|five|six)\s+decimal places?", re.I)
SF_RE = re.compile(r"\b(\d|one|two|three|four|five|six)\s+significant figures?", re.I)


def commands_of(text: str) -> list[str]:
    t = text.lower()
    return [c for c, pat in COMMANDS.items() if re.search(pat, t, re.M)]


def forms_of(text: str) -> list[str]:
    t = text.lower()
    out = [f for f, pat in FORMS.items() if re.search(pat, t)]
    for rx, tag in ((DP_RE, "dp"), (SF_RE, "sf")):
        for m in rx.finditer(t):
            n = NUMBER_WORDS.get(m.group(1), m.group(1))
            if f"{tag}-{n}" not in out:
                out.append(f"{tag}-{n}")
    return out


# ---- question mix --------------------------------------------------------------------------
# Skill groups that support almost every question (tools, not topics); left out when counting how
# many topics a question combines.
SUPPORT_GROUPS = {"exam-technique", "algebraic-manipulation", "quadratics", "modelling-in-context",
                  "mechanics-modelling"}
MIX_BANDS = ("single-topic-short", "single-topic-long", "two-topics", "three-plus-topics")


# ---- build ---------------------------------------------------------------------------------
def hist(values) -> dict:
    return {str(k): v for k, v in sorted(Counter(values).items(), key=lambda kv: (str(type(kv[0])), kv[0]))}


def top(counter: Counter, n: int) -> dict:
    return dict(counter.most_common(n))


def main() -> int:
    p = packs.load("pearson-private")
    conn = sqlite3.connect(f"file:{p.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    qs = {r["id"]: r for r in conn.execute("SELECT * FROM questions")}
    qtype = {r["question_id"]: r["tag_value"] for r in
             conn.execute("SELECT question_id, tag_value FROM question_tags WHERE tag_type = 'question_type'")}
    skills: dict[tuple, list[str]] = defaultdict(list)
    for r in conn.execute("SELECT question_id, part_label, tag_value FROM question_tags WHERE tag_type = 'skill' "
                          "ORDER BY rowid"):
        skills[(r["question_id"], r["part_label"])].append(r["tag_value"])
    group_of = {r["id"]: r["group_id"] for r in conn.execute("SELECT id, group_id FROM skills")}
    perf = {(r["question_id"], r["part_label"]): r for r in conn.execute("SELECT * FROM question_performance")}
    n_parts = Counter(r[0] for r in conn.execute("SELECT question_id FROM question_parts"))

    parts, unresolved = [], 0
    for r in conn.execute("SELECT * FROM question_parts ORDER BY question_id, part_index"):
        q = qs[r["question_id"]]
        codes, src = mark_codes(r["mark_scheme"], r["marks"])
        unresolved += codes is None
        pf = perf.get((q["id"], r["label"]))
        text = r["text"]
        parts.append({
            "part": f"{q['id']}:{r['label'] or ''}", "question": q["id"], "qualification": q["qualification"],
            "unit": q["unit"], "paper": q["paper"], "component": q["component"], "sitting": q["sitting"],
            "index": r["part_index"], "n_parts": n_parts[q["id"]], "marks": r["marks"],
            "question_marks": q["total_marks"], "question_type": qtype.get(q["id"]),
            "skills": skills.get((q["id"], r["label"]), []), "codes": codes, "code_source": src,
            "commands": commands_of(text), "forms": forms_of(text),
            "figure": bool(q["has_figure"]),
            "perf": None if pf is None else {
                "mean_mark": pf["mean_mark"], "max_mark": pf["max_mark"],
                "full_marks_pct": pf["full_marks_pct"], "rating": pf["rating"]},
        })
    # Whole-question performance rows (part_label NULL) for multi-part questions.
    q_perf = {q: {"mean_mark": r["mean_mark"], "max_mark": r["max_mark"], "full_marks_pct": r["full_marks_pct"],
                  "rating": r["rating"]} for (q, lab), r in perf.items() if lab is None and n_parts[q] > 1}

    # ---- aggregates --------------------------------------------------------------------------
    def summarise(rows: list[dict]) -> dict:
        qids = sorted({r["question"] for r in rows})
        pats = Counter(" ".join(r["codes"]) for r in rows if r["codes"])
        rated = [r["perf"] for r in rows if r["perf"]]
        pct = [x["mean_mark"] / x["max_mark"] for x in rated if x["mean_mark"] is not None and x["max_mark"]]
        return {
            "n_questions": len(qids), "n_parts": len(rows),
            "parts_per_question": hist(n_parts[q] for q in qids),
            "question_marks": hist(qs[q]["total_marks"] for q in qids),
            "marks_per_part": hist(r["marks"] for r in rows),
            "code_patterns": top(pats, 15),
            "codes": top(Counter(c for r in rows if r["codes"] for c in r["codes"]), 20),
            "commands": top(Counter(c for r in rows for c in r["commands"]), 20),
            "forms": top(Counter(f for r in rows for f in r["forms"]), 15),
            "figure_share": round(sum(r["figure"] for r in rows) / len(rows), 3),
            "difficulty": {"n_rated": len(rated), "ratings": top(Counter(x["rating"] for x in rated if x["rating"]), 3),
                           "mean_pct_mean": round(sum(pct) / len(pct), 3) if pct else None,
                           "full_marks_pct_mean": (lambda v: round(sum(v) / len(v), 1) if v else None)(
                               [x["full_marks_pct"] for x in rated if x["full_marks_pct"] is not None])},
        }

    by_type, by_skill, by_qual = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in parts:
        by_type[r["question_type"]].append(r)
        by_qual[r["qualification"]].append(r)
        for s in r["skills"]:
            by_skill[s].append(r)
    q_skills = defaultdict(set)
    for r in parts:
        q_skills[r["question"]].update(s for s in r["skills"] if group_of.get(s) != "exam-technique")
    same_q, same_part = Counter(), Counter()
    for r in parts:
        ss = sorted({s for s in r["skills"] if group_of.get(s) != "exam-technique"})
        same_part.update((a, b) for i, a in enumerate(ss) for b in ss[i + 1:])
    for ss in q_skills.values():
        ss = sorted(ss)
        same_q.update((a, b) for i, a in enumerate(ss) for b in ss[i + 1:])
    group_q = Counter()
    for ss in q_skills.values():
        gs = sorted({group_of[s] for s in ss})
        group_q.update((a, b) for i, a in enumerate(gs) for b in gs[i + 1:])
    # ---- 9MA0 question mix: how often real questions combine topics (drives the bank's mix, §5.3) --
    by_q = defaultdict(list)
    for r in parts:
        if r["qualification"] == "9MA0":
            by_q[r["question"]].append(r)
    mix = defaultdict(lambda: defaultdict(lambda: {"questions": 0, "marks": 0}))
    for q, rows in by_q.items():
        comp, marks = rows[0]["component"], sum(r["marks"] for r in rows)
        topics = {group_of[s] for r in rows for s in r["skills"]} - SUPPORT_GROUPS
        band = MIX_BANDS[0] if len(topics) <= 1 and marks <= 5 else MIX_BANDS[1] if len(topics) <= 1 \
            else MIX_BANDS[2] if len(topics) == 2 else MIX_BANDS[3]
        for key in (comp, "all"):
            mix[key][band]["questions"] += 1
            mix[key][band]["marks"] += marks

    aggregates = {
        "mix_9ma0": {k: dict(v) for k, v in mix.items()},
        "overall": summarise(parts),
        "by_qualification": {k: summarise(v) for k, v in sorted(by_qual.items())},
        "by_question_type": {k: summarise(v) for k, v in sorted(by_type.items()) if k},
        "by_skill": {k: summarise(v) for k, v in sorted(by_skill.items())},
        "skill_cooccurrence": [[a, b, n, same_part[(a, b)]] for (a, b), n in same_q.most_common() if n >= 3],
        "group_cooccurrence": [[a, b, n] for (a, b), n in group_q.most_common() if n >= 3],
    }

    # ---- 9MA0 paper-level facts ------------------------------------------------------------
    papers = defaultdict(list)
    for q in qs.values():
        if q["qualification"] == "9MA0":
            papers[q["paper_id"]].append(q)
    paper_facts = {
        pid: {"paper": rows[0]["paper"], "sitting": rows[0]["sitting"], "component": rows[0]["component"],
              "n_questions": len(rows), "total_marks": sum(r["total_marks"] or 0 for r in rows),
              "questions": [[r["q_num"], r["total_marks"], n_parts[r["id"]], qtype.get(r["id"])]
                            for r in sorted(rows, key=lambda r: int(re.sub(r"\D", "", r["q_num"]) or 0))]}
        for pid, rows in sorted(papers.items())}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parts.json").write_text(json.dumps({"parts": parts, "question_perf": q_perf}, indent=0))
    (OUT / "aggregates.json").write_text(json.dumps(aggregates, indent=1))
    (OUT / "papers.json").write_text(json.dumps(paper_facts, indent=1))
    print(f"parts: {len(parts)} ({len(parts) - unresolved} with a mark-code sequence adding up to the marks, "
          f"{unresolved} unresolved) | question types {len(by_type)} | skills {len(by_skill)} | "
          f"co-occurring skill pairs (>=3 questions) {len(aggregates['skill_cooccurrence'])} | 9MA0 papers {len(paper_facts)}")
    src = Counter(r["code_source"] for r in parts)
    print("code source:", dict(src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
