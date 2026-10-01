#!/usr/bin/env python3
"""Question-type playbooks (docs/market-research-product-strategy.md §4.2, feature 4): one page per question type,
written by the model from a FACTS block built out of our own fact files, then checked deterministically.

    .venv/bin/python scripts/clean/make_playbooks.py --list                       # types, counts, practice items
    .venv/bin/python scripts/clean/make_playbooks.py --dry --types ap-gp-in-context   # print the FACTS block
    .venv/bin/python scripts/clean/make_playbooks.py --types a,b,c [--force]      # generate these types
    .venv/bin/python scripts/clean/make_playbooks.py --limit 5 --parallel 5        # first N types without a file

The model sees only our own material: the FACTS block (ids, counts and codes from content/facts/, rendered with
our titles and definitions from content/clean/tags.json and content/error_codes.json), our marking vocabulary
(content/boards/edexcel-9ma0.json) and our house-style prompt (content/prompts/playbook_system.md). **No Pearson
text goes into any prompt.** Every playbook then passes through deterministic checks:
  (a) copy check over every text field (gates.g7_novelty on the local corpus: we see pass/fail/flags only),
  (b) KaTeX render of every $...$ span (gate_style),
  (c) banned phrases (check_provenance.BANNED plus board names, examiner(s), past paper),
  (d) every error code is a real id listed in this type's FACTS,
  (e) "common" / "often" / "many students" only for codes with >= FREQUENT_NOTES matched notes,
  (f) mark codes written M1 / A1 / dM1 / A1ft / A1*, abbreviations lowercase (gate_style's regexes),
plus id checks on skills and related types (unknown ids are dropped and flagged). A failing playbook is regenerated
once with our own failure messages as feedback. Passing playbooks go to content/clean/playbooks/<type>.json,
failing ones to content/clean/playbooks/_failed/. Costs are logged by claude_oneshot (step names "playbook*").
"""
import argparse
import json
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_provenance  # noqa: E402
import gate_style  # noqa: E402
import gates  # noqa: E402
from gate_marking import FREQUENT_NOTES  # noqa: E402  (one threshold for pitfalls and playbooks)
from chatbot import marks  # noqa: E402

MODEL = "claude-sonnet-5-5"
STEP = "playbook"
PLAYBOOKS = ROOT / "content" / "clean" / "playbooks"
FAILED = PLAYBOOKS / "_failed"
PROMPT = ROOT / "content" / "prompts" / "playbook_system.md"
TAGS = ROOT / "content" / "clean" / "tags.json"
AGGREGATES = ROOT / "content" / "facts" / "aggregates.json"
PARTS = ROOT / "content" / "facts" / "parts.json"
ERROR_FREQ = ROOT / "content" / "facts" / "error_frequency.json"
ERROR_CODES = ROOT / "content" / "error_codes.json"
ITEMS = ROOT / "content" / "clean" / "items"
ALL_GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
TOP_PATTERNS, TOP_SKILLS, TOP_ERRORS, TOP_RELATED = 8, 10, 8, 8
LOSES_FAMILY = {"M": "method", "A": "accuracy", "B": "independent"}

STR = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "title": STR, "what_it_asks": STR, "typical_structure": STR, "mark_pattern": STR,
        "where_marks_leak": {"type": "array", "items": {"type": "object", "properties": {
            "error_code": STR, "mark_family": {"type": "string", "enum": ["method", "accuracy", "independent"]},
            "text": STR}, "required": ["error_code", "mark_family", "text"]}},
        "write_to_earn": {"type": "array", "items": STR},
        "check_before_you_leave": {"type": "array", "items": STR},
        "skills": {"type": "array", "items": STR},
        "related_types": {"type": "array", "items": STR},
    },
    "required": ["title", "what_it_asks", "typical_structure", "mark_pattern", "where_marks_leak", "write_to_earn",
                 "check_before_you_leave", "skills", "related_types"],
}

# (c) banned words on top of the licence gate's phrases
EXTRA_BANNED = re.compile(r"\b(pearson|edexcel|aqa|ocr|examiners?|past\s+papers?)\b", re.I)
# (e) frequency words: any of these in a leak entry needs a frequent code; the strict ones are banned elsewhere
FREQ_WORDS = re.compile(r"\b(common(?:ly)?|frequent(?:ly)?|often|many students|most students|lots of students|regularly)\b",
                        re.I)
STRICT_FREQ_WORDS = re.compile(r"\b(common(?:ly)?|frequent(?:ly)?|many students|most students|lots of students)\b", re.I)
# outside a leak entry a frequency word is a claim about students only when the sentence is about a mistake
# ("a common shape", "the common ratio" and "the most frequent pattern" are facts, not error claims)
ERROR_WORDS = re.compile(r"\b(mistakes?|errors?|slips?|lose|loses|lost|losing|drop|dropped|forget|forgets|omit|omits|"
                         r"wrong|miss|misses|missed|fail|fails|students?)\b", re.I)
CODE_BASES = ("M", "A", "B", "dM", "ddM", "dB")
CONTENT_KEYS = ("title", "what_it_asks", "typical_structure", "mark_pattern", "where_marks_leak", "write_to_earn",
                "check_before_you_leave", "skills", "related_types")
IN_SPAN_CODE = re.compile(r"(?<![A-Za-z\\_^{])(?:dd|d)?[MAB][1-9](?:ft|\*|cso|cao)?(?![A-Za-z0-9_])")
GLUED_SUFFIX = re.compile(r"\b(?:dd|d)?[MAB][1-9](cso|cao)\b")
SENT_RE = re.compile(r"(?<=[.!?])\s+")
CHECK_LOCK = threading.Lock()   # the corpus, the embedding model and node are shared


# ---- facts -----------------------------------------------------------------------------------
def _hist_stats(hist: dict) -> tuple[int, int, int]:
    """(median, min, max) of a {value: count} histogram."""
    vals = sorted((int(k), v) for k, v in hist.items())
    n = sum(v for _, v in vals)
    acc = 0
    med = vals[-1][0]
    for k, v in vals:
        acc += v
        if acc * 2 >= n:
            med = k
            break
    return med, vals[0][0], vals[-1][0]


def _hist_words(hist: dict, total: int, unit: str) -> str:
    return ", ".join(f"{k} {unit}: {v} ({100 * v / total:.0f}%)" for k, v in sorted(hist.items(), key=lambda kv: int(kv[0])))


class Facts:
    """Everything the FACTS block draws on: our own fact files and taxonomy, nothing else."""

    def __init__(self):
        tags = json.loads(TAGS.read_text())
        self.qtypes = {t["id"]: t for t in tags["question_types"]}
        self.skills = {s["id"]: s for s in tags["skills"]}
        self.groups = {g["id"]: g for g in tags["skill_groups"]}
        self.topics = {t["id"]: t for t in tags["topics"]}
        self.agg = json.loads(AGGREGATES.read_text())["by_question_type"]
        self.parts_by_type: dict[str, list[dict]] = defaultdict(list)
        for p in json.loads(PARTS.read_text())["parts"]:
            self.parts_by_type[p["question_type"]].append(p)
        self.errors_by_type: dict[str, list[tuple[str, float, int]]] = defaultdict(list)
        for qt, code, weighted, n in json.loads(ERROR_FREQ.read_text())["type_error"]:
            self.errors_by_type[qt].append((code, weighted, n))
        for rows in self.errors_by_type.values():
            rows.sort(key=lambda r: (-r[2], -r[1], r[0]))
        self.codes = {c["id"]: c for c in json.loads(ERROR_CODES.read_text())["codes"]}
        self.items_by_type: dict[str, list[str]] = defaultdict(list)
        if ITEMS.exists():
            for f in sorted(ITEMS.glob("*.json")):
                it = json.loads(f.read_text())
                gr = it.get("gate_results") or {}
                if all((gr.get(g) or {}).get("pass") for g in ALL_GATES):
                    self.items_by_type[it["question_type"]].append(it["id"])

    def component(self, qt: str) -> str:
        c = Counter(p["component"] for p in self.parts_by_type[qt])
        return c.most_common(1)[0][0] if c else self.topics.get(self.qtypes[qt].get("topic"), {}).get("component", "pure")

    def top_skills(self, qt: str, n: int = TOP_SKILLS) -> list[tuple[str, int]]:
        c = Counter(s for p in self.parts_by_type[qt] for s in p["skills"] if s in self.skills)
        return c.most_common(n)

    def related_types(self, qt: str, n: int = TOP_RELATED) -> list[str]:
        """Same topic first, then types sharing at least two of this type's six most-tested skills."""
        t = self.qtypes[qt]
        same_topic = [x for x in self.qtypes if x != qt and self.qtypes[x].get("topic") == t.get("topic")]
        mine = {s for s, _ in self.top_skills(qt, 6)}
        overlap = []
        for x in self.qtypes:
            if x == qt or x in same_topic:
                continue
            shared = len(mine & {s for s, _ in self.top_skills(x, 6)})
            if shared >= 2:
                overlap.append((shared, x))
        overlap.sort(key=lambda kv: (-kv[0], kv[1]))
        return (same_topic + [x for _, x in overlap])[:n]

    def error_rows(self, qt: str, n: int = TOP_ERRORS) -> list[tuple[str, float, int]]:
        return [r for r in self.errors_by_type[qt] if r[0] in self.codes][:n]

    def context(self, qt: str) -> dict:
        """What the checks need to know about a type: allowed codes and their counts, allowed ids."""
        rows = self.error_rows(qt)
        return {"type": qt, "component": self.component(qt), "codes": {c: n for c, _, n in rows},
                "frequent": {c for c, _, n in rows if n >= FREQUENT_NOTES},
                "skills": {s for s, _ in self.top_skills(qt)}, "related": set(self.related_types(qt)),
                "n_questions": self.agg.get(qt, {}).get("n_questions", 0), "practice": self.items_by_type[qt]}

    def block(self, qt: str) -> str:
        t, a, parts = self.qtypes[qt], self.agg[qt], self.parts_by_type[qt]
        topic = self.topics.get(t.get("topic"), {})
        nq, npart = a["n_questions"], a["n_parts"]
        qm, qlo, qhi = _hist_stats(a["question_marks"])
        pm, plo, phi = _hist_stats(a["parts_per_question"])
        lines = ["# FACTS", "",
                 f"- Question type id: `{qt}`", f"- Title: {t['title']}", f"- Definition: {t.get('definition') or ''}",
                 f"- Topic: {topic.get('title', t.get('topic'))} | component: {self.component(qt)}",
                 f"- Real questions counted: {nq} (with {npart} parts)"
                 + (" (few questions: treat the distributions below as indicative only)" if nq < 5 else ""),
                 "", "## Shape",
                 f"- Marks per question: median {qm}, range {qlo}-{qhi}. Distribution: {_hist_words(a['question_marks'], nq, 'marks')}",
                 f"- Parts per question: median {pm}, range {plo}-{phi}. Distribution: {_hist_words(a['parts_per_question'], nq, 'parts')}",
                 f"- Marks per part: {_hist_words(a['marks_per_part'], npart, 'marks')}",
                 f"- Share of questions with a diagram: {100 * a.get('figure_share', 0):.0f}%",
                 "", "## Mark-code patterns (per part, most common first; share of all parts of this type)"]
        pats = sorted(a.get("code_patterns", {}).items(), key=lambda kv: -kv[1])[:TOP_PATTERNS]
        lines += [f"- `{pat}`: {n} parts ({100 * n / npart:.0f}%)" for pat, n in pats]
        codes = sorted(a.get("codes", {}).items(), key=lambda kv: -kv[1])
        lines += ["- Individual codes: " + ", ".join(f"{c} x{n}" for c, n in codes),
                  "", "## Skills most often tested (id: title; parts)"]
        for s, n in self.top_skills(qt):
            sk = self.skills[s]
            lines.append(f"- `{s}`: {sk['title']} ({self.groups.get(sk.get('group'), {}).get('title', sk.get('group'))}); "
                         f"{n} parts. {sk.get('description') or ''}")
        cmds = sorted(a.get("commands", {}).items(), key=lambda kv: -kv[1])[:8]
        forms = sorted(a.get("forms", {}).items(), key=lambda kv: -kv[1])[:6]
        lines += ["", "## Command words and answer forms (parts)",
                  "- Command words: " + ", ".join(f"{c} x{n}" for c, n in cmds),
                  "- Answer forms asked for: " + (", ".join(f"{f} x{n}" for f, n in forms) or "none recorded")]
        d = a.get("difficulty") or {}
        if d.get("n_rated"):
            r = d.get("ratings", {})
            lines += ["", "## Performance facts",
                      f"- Of {d['n_rated']} rated questions: {r.get('well_answered', 0)} well answered, "
                      f"{r.get('poorly_answered', 0)} poorly answered, {r.get('mixed', 0)} mixed"
                      + (f"; mean share of full marks {d['full_marks_pct_mean']:.0f}%" if d.get("full_marks_pct_mean") else "")]
        rows = self.error_rows(qt)
        lines += ["", f"## Error codes matched to this type (count = matched notes; frequent = count >= {FREQUENT_NOTES})"]
        if not rows:
            lines.append("- none recorded for this type")
        for code, weighted, n in rows:
            c = self.codes[code]
            lines.append(f"- `{code}` (count {n}; usually loses {LOSES_FAMILY.get(c['loses'], c['loses'])} marks; "
                         f"frequent: {'yes' if n >= FREQUENT_NOTES else 'no'}): {c['definition']}")
        lines += ["", "## Related types (id: title)"]
        lines += [f"- `{x}`: {self.qtypes[x]['title']}" for x in self.related_types(qt)]
        practice = self.items_by_type[qt]
        lines += ["", f"## Our practice items of this type that pass every gate: {len(practice)}"
                  + (" (" + ", ".join(practice) + ")" if practice else "")]
        return "\n".join(lines)


# ---- prompt ----------------------------------------------------------------------------------
def glossary_text() -> str:
    b = marks.profile()
    lines = ["# Marking vocabulary (our own definitions; use these meanings)", ""]
    for g in marks.glossary(b):
        lines.append(f"- **{g.get('name', g['key'])}** (`{g['key']}`): {g.get('short', '')} {g.get('explain', '')} "
                     f"How to earn it: {g.get('write_to_earn', '')}")
    lines += ["", "# Answer forms", ""]
    lines += [f"- `{k}`: {v}" for k, v in b.answer_forms.items()]
    lines += ["", f"Bald answers: {b.bald_answer_policy}"]
    return "\n".join(lines)


def system_prompt() -> str:
    return PROMPT.read_text() + "\n\n" + glossary_text() + "\n"


def user_message(block: str) -> str:
    return block + "\n\nWrite the playbook for this question type as JSON in the schema given."


# ---- checks ----------------------------------------------------------------------------------
def text_fields(pb: dict) -> list[tuple[str, str]]:
    out = [(k, pb.get(k) or "") for k in ("title", "what_it_asks", "typical_structure", "mark_pattern")]
    out += [(f"where_marks_leak.{i}", e.get("text") or "") for i, e in enumerate(pb.get("where_marks_leak") or [])]
    out += [(f"write_to_earn.{i}", s) for i, s in enumerate(pb.get("write_to_earn") or [])]
    out += [(f"check_before_you_leave.{i}", s) for i, s in enumerate(pb.get("check_before_you_leave") or [])]
    return [(w, t if isinstance(t, str) else str(t)) for w, t in out if t]


def check_copy(fields: list[tuple[str, str]]) -> dict:
    """(a) The G7 novelty check over the playbook's prose. Each field becomes one 'part' of a pseudo-item, so the
    8-gram, Jaccard, number, rare-word and cosine checks all run and hit_fields name our fields."""
    pseudo = {"stem": None, "parts": [{"label": w, "text": t, "marks": None} for w, t in fields], "pitfalls": []}
    r = gates.g7_novelty(pseudo)
    hits = [re.sub(r"^part (.*) text$", r"\1", h) for h in r.get("hit_fields") or []]
    sentences = {}
    for w, t in fields:  # which of OUR sentences carry the overlap (our text; the corpus stays unread)
        if w in hits:
            sents = [x for x in SENT_RE.split(t) if x.strip()]
            bad = [x for x in sents if len(sents) > 1 and gates.g7_novelty(
                {"stem": None, "parts": [{"label": w, "text": x, "marks": None}], "pitfalls": []})["n_8gram_hits"]]
            sentences[w] = bad
    reasons = [x.replace("Pearson corpus", "local corpus") for x in r["reasons"]]  # our message; keeps files board-free
    return {"pass": r["pass"], "flag": r.get("flag", False), "reasons": reasons, "flags": r["flags"],
            "hit_fields": hits, "hit_sentences": sentences,
            "n_8gram_hits": r["n_8gram_hits"], "max_jaccard": r["max_jaccard"],
            "shared_numbers": r["shared_numbers"], "max_cosine": r["max_cosine"], "cosine_source": r["cosine_source"]}


def check_katex(fields: list[tuple[str, str]]) -> dict:
    """(b) Every $...$ span renders; no other delimiters, no LaTeX outside a span, no unbalanced $."""
    errs, batch, where = [], [], []
    for w, t in fields:
        found, outside = gate_style.spans(t)
        if "$" in outside:
            errs.append(f"{w}: unbalanced $")
        if gate_style.OTHER_DELIMS.search(t):
            errs.append(f"{w}: use $...$ for maths, not \\( \\) or \\[ \\]")
        elif cmds := sorted(set(gate_style.LATEX_CMD.findall(outside))):
            errs.append(f"{w}: LaTeX outside a $ span: {' '.join(cmds[:5])}")
        batch += found
        where += [w] * len(found)
    for w, (tex, _), e in zip(where, batch, gate_style.katex_errors(batch)):
        if e:
            errs.append(f"{w}: KaTeX error in ${tex[:60]}$: {e}")
    return {"pass": not errs, "errors": errs, "n_spans": len(batch)}


def check_banned(pb: dict) -> dict:
    """(c) Licence-gate phrases plus board names, examiner(s), past paper, in any string of the playbook."""
    errs = []
    content = {k: pb.get(k) for k in CONTENT_KEYS if k in pb}
    for path, s in gate_style.all_strings(content, "playbook"):
        errs += [f"{path}: banned phrase {m.group(0)!r}" for m in check_provenance.BANNED.finditer(s)]
        errs += [f"{path}: banned word {m.group(0)!r}" for m in EXTRA_BANNED.finditer(s)]
    return {"pass": not errs, "errors": errs}


def check_error_codes(pb: dict, ctx: dict, codes: dict) -> dict:
    """(d) Every error_code is a real id listed in this type's FACTS. Count, duplicates and a mark_family that
    differs from the code's usual loss are flags."""
    errs, flags = [], []
    leaks = pb.get("where_marks_leak") or []
    seen: Counter = Counter()
    for i, e in enumerate(leaks):
        code = e.get("error_code")
        seen[code] += 1
        if code not in codes:
            errs.append(f"where_marks_leak.{i}: {code!r} is not an error code")
        elif code not in ctx["codes"]:
            errs.append(f"where_marks_leak.{i}: {code!r} is not among the codes listed for this type")
        elif LOSES_FAMILY.get(codes[code].get("loses")) not in (None, e.get("mark_family")):
            flags.append(f"where_marks_leak.{i}: mark_family {e.get('mark_family')!r} but {code} usually loses "
                         f"{LOSES_FAMILY[codes[code]['loses']]} marks")
    if not 3 <= len(leaks) <= 5:
        flags.append(f"{len(leaks)} where_marks_leak entries (wanted 3-5)")
    flags += [f"error code {c!r} used {n} times" for c, n in seen.items() if n > 1]
    return {"pass": not errs, "errors": errs, "flags": flags}


def check_frequency_words(pb: dict, ctx: dict) -> dict:
    """(e) 'common' / 'often' / 'many students' about an error only for codes with count >= FREQUENT_NOTES."""
    errs = []
    for i, e in enumerate(pb.get("where_marks_leak") or []):
        m = FREQ_WORDS.search(e.get("text") or "")
        if m and e.get("error_code") not in ctx["frequent"]:
            errs.append(f"where_marks_leak.{i}: says {m.group(0)!r} but {e.get('error_code')} has "
                        f"{ctx['codes'].get(e.get('error_code'), 0)} matched notes (needs {FREQUENT_NOTES})")
    for w, t in text_fields(pb):
        if w.startswith("where_marks_leak"):
            continue
        for sent in SENT_RE.split(t):
            m = STRICT_FREQ_WORDS.search(sent)
            if m and ERROR_WORDS.search(sent):
                errs.append(f"{w}: {m.group(0)!r} is a frequency claim about a mistake; only where_marks_leak entries "
                            "for frequent codes may make one")
    return {"pass": not errs, "errors": errs}


def check_mark_codes(fields: list[tuple[str, str]]) -> dict:
    """(f) Mark codes in prose written M1 / A1 / B1 / dM1 / A1ft / A1*; awrt, oe, cao, cso, isw lowercase."""
    errs = []
    for w, t in fields:
        found, outside = gate_style.spans(t)
        errs += [f"{w}: mark code inside a $ span: ${tex[:40]}$ (codes are plain text)" for tex, _ in found
                 if IN_SPAN_CODE.search(tex)]
        errs += [f"{w}: write {g.group(0)!r} as the code followed by '{g.group(1)}' as a separate word"
                 for g in GLUED_SUFFIX.finditer(outside)]
        for c in gate_style.CODE_WORD.finditer(outside):
            base, flag = c.group(1), c.group(3) or ""
            if base.islower() and len(base) == 1:
                continue  # "a1" in prose is more likely maths than a code
            if base not in CODE_BASES or flag not in ("", "ft", "*"):
                errs.append(f"{w}: mark code written {c.group(0)!r}")
        errs += [f"{w}: write {a.group(0)!r} in lowercase" for a in gate_style.ABBREV.finditer(outside)
                 if a.group(0) != a.group(0).lower()]
    return {"pass": not errs, "errors": errs}


def check_ids(pb: dict, ctx: dict, facts: "Facts") -> dict:
    """Skills and related types must be ids we know; unknown ones are dropped from the playbook and flagged."""
    flags = []
    skills = [s for s in pb.get("skills") or [] if s in facts.skills]
    flags += [f"unknown skill id {s!r} dropped" for s in pb.get("skills") or [] if s not in facts.skills]
    flags += [f"skill {s!r} is not among this type's most-tested skills" for s in skills if s not in ctx["skills"]]
    rel = [r for r in pb.get("related_types") or [] if r in facts.qtypes and r != ctx["type"]]
    flags += [f"unknown related type {r!r} dropped" for r in pb.get("related_types") or []
              if r not in facts.qtypes or r == ctx["type"]]
    flags += [f"related type {r!r} is not in the FACTS list" for r in rel if r not in ctx["related"]]
    pb["skills"], pb["related_types"] = skills, rel
    return {"pass": True, "flags": flags}


def run_checks(pb: dict, ctx: dict, facts: "Facts") -> dict:
    fields = text_fields(pb)
    with CHECK_LOCK:
        res = {"copy": check_copy(fields), "katex": check_katex(fields), "banned": check_banned(pb),
               "error_codes": check_error_codes(pb, ctx, facts.codes), "frequency_words": check_frequency_words(pb, ctx),
               "mark_codes": check_mark_codes(fields), "ids": check_ids(pb, ctx, facts)}
    res["pass"] = all(r["pass"] for r in res.values())
    res["flags"] = [f"{k}: {f}" for k, r in res.items() if isinstance(r, dict) for f in r.get("flags") or []]
    return res


def feedback(res: dict, ctx: dict) -> str:
    """Our own messages only: field names, our error lines and the model's own words; never corpus text."""
    lines = ["Your previous playbook failed these automatic checks. Write a new version that fixes them:"]
    if not res["copy"]["pass"]:
        where = ", ".join(res["copy"]["hit_fields"]) or "several fields"
        lines.append(f"- Originality: wording in these fields matches published exam material: {where}. Rewrite them "
                     "in fresh wording of your own; do not reuse stock mark-scheme idioms. Change the sentence "
                     "structure, not just a word or two.")
        for w, sents in (res["copy"].get("hit_sentences") or {}).items():
            for x in sents:
                lines.append(f"  - your sentence in {w} that overlaps: \"{x}\"")
        if any(not v for v in (res["copy"].get("hit_sentences") or {}).values()):
            lines.append("  - the overlap runs across sentence boundaries, so rewrite the whole field")
    for k in ("katex", "banned", "error_codes", "frequency_words", "mark_codes"):
        lines += [f"- {k}: {e}" for e in (res[k].get("errors") or [])[:8]]
    if not res["error_codes"]["pass"]:
        lines.append("- Use only these error codes: " + ", ".join(f"`{c}`" for c in ctx["codes"]))
    return "\n".join(lines)


# ---- generation ------------------------------------------------------------------------------
def generate_one(qt: str, facts: Facts, system: str, retries: int = 1) -> dict:
    import claude_oneshot
    block, ctx = facts.block(qt), facts.context(qt)
    msg = user_message(block)
    cost, res, pb = 0.0, {}, {}
    for attempt in range(1, retries + 2):
        out = claude_oneshot.run(system, [claude_oneshot.text_block(msg)], schema=SCHEMA, model=MODEL, max_usd=1.0,
                                 thinking_tokens=4000, step=STEP if attempt == 1 else f"{STEP}-retry", ref=qt,
                                 timeout=900)
        cost += out["cost_usd"] or 0
        pb = out["result"]
        res = run_checks(pb, ctx, facts)
        if res["pass"]:
            break
        msg = user_message(block) + "\n\n" + feedback(res, ctx)
    record = {"id": qt, "question_type": qt, "component": ctx["component"], **pb, "provenance": "original",
              "model": MODEL, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "cost_usd": round(cost, 4),
              "attempts": attempt,
              "facts": {"n_questions": ctx["n_questions"], "codes_listed": ctx["codes"],
                        "frequent_codes": sorted(ctx["frequent"]), "practice_items": ctx["practice"]},
              "checks": res, "review": {"by": None, "at": None, "decision": None, "notes": None}}
    folder = PLAYBOOKS if res["pass"] else FAILED
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{qt}.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", help="comma-separated question-type ids (default: every type)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--parallel", type=int, default=3)
    ap.add_argument("--dry", action="store_true", help="print the FACTS block for the first selected type; no calls")
    ap.add_argument("--list", action="store_true", help="list types with counts; no calls")
    ap.add_argument("--force", action="store_true", help="regenerate types that already have a playbook")
    ap.add_argument("--max-usd", type=float, default=60.0, help="stop submitting new calls past this run spend")
    args = ap.parse_args()
    facts = Facts()
    ids = [t.strip() for t in args.types.split(",") if t.strip()] if args.types else list(facts.qtypes)
    unknown = [t for t in ids if t not in facts.qtypes]
    if unknown:
        print(f"unknown type(s): {unknown}")
        return 2
    if args.list:
        print(f"{'type':45} {'comp':5} {'n_q':>4} {'n_err':>5} {'freq':>4} {'items':>5} playbook")
        for t in ids:
            c = facts.context(t)
            print(f"{t:45} {c['component']:5} {c['n_questions']:4} {len(c['codes']):5} {len(c['frequent']):4} "
                  f"{len(c['practice']):5} {'yes' if (PLAYBOOKS / f'{t}.json').exists() else '-'}")
        return 0
    if not args.force:
        ids = [t for t in ids if not (PLAYBOOKS / f"{t}.json").exists()]
    ids = ids[:args.limit] if args.limit else ids
    system = system_prompt()
    if args.dry:
        print(f"{len(ids)} type(s) selected; system prompt {len(system)} chars, model {MODEL}\n")
        if ids:
            print(facts.block(ids[0]))
        return 0
    if not ids:
        print("nothing to do (every selected type has a playbook; use --force)")
        return 0
    print(f"{len(ids)} type(s), {min(5, args.parallel)} parallel, cap ${args.max_usd:.0f}")
    gates.corpus()  # load the corpus once, before the threads start
    t0, spent, passed, failed = time.time(), 0.0, 0, 0
    width = min(5, max(1, args.parallel))
    for start in range(0, len(ids), width):
        if spent >= args.max_usd:
            print(f"stopping: ${spent:.2f} spent, cap ${args.max_usd:.2f}; {len(ids) - start} type(s) not run")
            break
        batch = ids[start:start + width]
        with ThreadPoolExecutor(max_workers=width) as ex:
            futures = {ex.submit(generate_one, t, facts, system): t for t in batch}
            for fut in futures:
                t = futures[fut]
                try:
                    rec = fut.result()
                except Exception as e:  # noqa: BLE001 - report and carry on with the batch
                    print(f"  {t}: ERROR {str(e)[:200]}")
                    failed += 1
                    continue
                spent += rec["cost_usd"]
                ok = rec["checks"]["pass"]
                passed += ok
                failed += not ok
                bad = [k for k, r in rec["checks"].items() if isinstance(r, dict) and not r.get("pass")]
                print(f"  {t}: {'PASS' if ok else 'FAIL ' + ','.join(bad)}  attempts {rec['attempts']}  "
                      f"${rec['cost_usd']:.3f}  flags {len(rec['checks']['flags'])}")
    print(f"done: {passed} passed, {failed} failed | ${spent:.2f} | {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
