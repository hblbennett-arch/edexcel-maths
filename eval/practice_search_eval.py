#!/usr/bin/env python3
"""Practice-search benchmark: does "find me a question …" find the question the student means?

    .venv/bin/python -m eval.practice_search_eval            # print the numbers
    .venv/bin/python -m eval.practice_search_eval --save X   # also append them to practice_search_results.txt
    .venv/bin/python -m eval.practice_search_eval --misses   # print failing queries

Deterministic (seeded, no model calls). Four sections:

1. description  ~300 generated "described scenario" requests (random.Random(11)). Each is built from a
                question's most distinctive non-maths words (IDF over all question texts; 1 in 4 changed
                to another form, e.g. dentist -> dentists) plus one of its numbers, wrapped in a template. Metric: recall@1 / recall@5 of the source question,
                overall and by qualification / component. Queries alternate between a "calibrate" half and a
                "held-out" half, so thresholds tuned on one half are confirmed on the other.
2. topics       ~150 generated multi-topic requests ("a question that uses differentiation, partial
                fractions and stationary points"), 2-3 everyday topic names that one question covers between
                its parts. Metric: the returned question covers every named topic (top-1, and the share of
                the top 5 that do).
3. skills       ~150 generated multi-skill requests from skill titles ("a question combining integrate by
                parts and use the trapezium rule"). Same metric, at skill level.
4. hand         real user reports and hand-written cases; every one must pass.
"""
import math
import os
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from chatbot import db  # noqa: E402
from chatbot.recommend import find_practice  # noqa: E402
from chatbot.text import latex_to_plain, tokens  # noqa: E402

RESULTS = ROOT / "eval" / "practice_search_results.txt"
MAX_DF = 12   # a word in more questions than this is ordinary exam English ("acceptable", "metres", "attached")

# Everyday topic names a student would type -> the skill groups that count as covering it.
TOPICS = {
    "differentiation": {"basic-differentiation", "chain-product-quotient-rules", "implicit-and-parametric-differentiation"},
    "integration": {"basic-integration", "integration-techniques", "areas-by-integration"},
    "partial fractions": {"partial-fractions"},
    "stationary points": {"stationary-points"},
    "tangents and normals": {"tangents-and-normals"},
    "the chain rule": {"chain-product-quotient-rules"},
    "implicit differentiation": {"implicit-and-parametric-differentiation"},
    "integration by parts or substitution": {"integration-techniques"},
    "area under a curve": {"areas-by-integration"},
    "differential equations": {"differential-equations"},
    "numerical methods": {"numerical-methods"},
    "parametric equations": {"parametric-equations"},
    "vectors": {"vectors"},
    "proof": {"proof"},
    "binomial expansion": {"binomial-expansion"},
    "sequences and series": {"sequences-and-series"},
    "logarithms": {"exponentials-and-logarithms"},
    "exponential models": {"exponential-modelling"},
    "trig identities": {"trig-identities"},
    "trig equations": {"trig-equations-and-models"},
    "radians": {"radians-and-circular-measure"},
    "circles": {"circles"},
    "straight lines": {"straight-lines-coordinates"},
    "quadratics": {"quadratics"},
    "polynomials and the factor theorem": {"polynomials"},
    "functions": {"functions"},
    "graph transformations": {"graphs-and-transformations"},
    "modelling": {"modelling-in-context"},
    "sampling": {"sampling"},
    "summary statistics": {"summary-statistics"},
    "correlation and regression": {"bivariate-data"},
    "probability": {"probability"},
    "discrete random variables": {"discrete-distributions"},
    "the binomial distribution": {"binomial-distribution"},
    "the normal distribution": {"normal-distribution"},
    "hypothesis testing": {"hypothesis-testing"},
    "suvat": {"kinematics-constant-acceleration"},
    "kinematics with calculus": {"kinematics-calculus"},
    "projectiles": {"projectiles"},
    "forces and newton's laws": {"forces-and-newtons-laws"},
    "friction": {"friction"},
    "moments": {"moments"},
}
TOPIC_TEMPLATES = ["can you find a question that uses {list}", "find me a question on {list}",
                   "give me a question combining {list}", "a question with {list} in it",
                   "i want a question that tests {list}"]
SKILL_TEMPLATES = ["find me a question that tests {list}", "a question combining {list}",
                   "give me a question where i have to {list}", "question linking {list} please"]
DESC_TEMPLATES = ["find me a question about {w}", "a {c} question to do with {w}", "the question with {w}",
                  "find me the {c} question about {w}", "give me that question on {w}"]
COMPONENT_WORD = {"pure": "pure", "stats": "stats", "mech": "mechanics"}

# Hand cases: (request, check, expected). check "first" = expected question listed first;
# "top5" = in the first five; "covers" = first item's question covers every topic in the list.
HAND = [
    ("Find me a stats question to do with dentists and 10% of customers arriving late", "first", "P3_June2022_stats_Q4"),
    ("Find me a question on differentiating x^x", "first", "P2_June2019_Q11"),
    ("can you find a question that use the following topics of differentiation, partial fractions, stationary points",
     "covers", ["differentiation", "partial fractions", "stationary points"]),
    ("a question that uses integration, partial fractions and differential equations", "covers",
     ["integration", "partial fractions", "differential equations"]),
    ("a mechanics question about a ladder against a wall", "text", "ladder"),
    ("give me a question with projectiles and vectors", "covers", ["projectiles", "vectors"]),
    ("find me a question with friction and moments", "covers", ["friction", "moments"]),
    ("a question linking the binomial distribution and hypothesis testing", "covers",
     ["the binomial distribution", "hypothesis testing"]),
    ("give me a question combining the chain rule, tangents and normals", "covers", ["the chain rule", "tangents and normals"]),
]


def _plain_words(text: str) -> list[str]:
    return [t for t in tokens(latex_to_plain(text)) if t.isalpha() and len(t) >= 4]


def _maths_vocab() -> set[str]:
    """Words that describe maths rather than a scenario (skill / type / group docs + common exam words)."""
    words = set()
    for sql in ("SELECT id || ' ' || title || ' ' || COALESCE(description, '') AS t FROM skills",
                "SELECT id || ' ' || title || ' ' || COALESCE(definition, '') AS t FROM question_types",
                "SELECT title AS t FROM skill_groups"):
        for r in db.rows(sql):
            words |= set(_plain_words(r["t"].replace("-", " ")))
    words |= set("""figure diagram shows sketch curve line point points value values exact answer answers
    given state explain write find determine calculate express prove show hence deduce estimate model
    constant constants positive negative integer integers real correct places significant figures decimal
    term terms equation equations expression form region shaded function graph axis axes coordinates
    solution solutions where such that range simplest therefore also between each same first second
    third following table total number shown using written work working marks question part parts
    frac sqrt xsqrt asqrt bsqrt ksqrt abcd just also into only then than there here they them very much
    many more most other being does done make made take given gives giving uses used both either
    """.split())
    return words


def _inflect(w: str, rng: random.Random) -> str:
    """Students don't quote the paper's exact word forms: 1 in 4 words changes number or tense."""
    if rng.random() >= 0.25:
        return w
    if w.endswith("ing") and len(w) > 6:
        return w[:-3] + "ed"
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w + ("es" if w.endswith(("x", "sh", "ch", "ss")) else "s")


def _questions():
    return db.rows("SELECT id, question_text, qualification, component FROM questions ORDER BY id")


def description_cases(n: int = 300, seed: int = 11) -> list[dict]:
    rng = random.Random(seed)
    qs = _questions()
    df = Counter()
    doc_words = {}
    for q in qs:
        w = set(_plain_words(q["question_text"]))
        doc_words[q["id"]] = w
        df.update(w)
    idf = {w: math.log(len(qs) / c) for w, c in df.items()}
    generic = _maths_vocab()
    cases = []
    for q in rng.sample(list(qs), len(qs)):
        # scenario words: rare across the whole bank (in <= MAX_DF questions) and not maths vocabulary
        ctx = sorted((w for w in doc_words[q["id"]] if w not in generic and df[w] <= MAX_DF), key=lambda w: (-idf[w], w))
        if len(ctx) < 3:
            continue                                   # all maths-generic: nothing to describe it by
        words = [_inflect(w, rng) for w in rng.sample(ctx[:6], min(len(ctx), rng.choice([3, 3, 4])))]
        nums = [t for t in re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.])", latex_to_plain(q["question_text"]))
                if t.rstrip("%") not in {"0", "1", "2", "3"} and not re.fullmatch(r"(19|20)\d\d", t)]
        if nums and rng.random() < 0.6:
            words.append(rng.choice(nums))
        w = ", ".join(words[:-1]) + " and " + words[-1]
        t = rng.choice(DESC_TEMPLATES)
        cases.append({"query": t.format(w=w, c=COMPONENT_WORD[q["component"]]), "qid": q["id"],
                      "qualification": q["qualification"], "component": q["component"],
                      "half": "calibrate" if len(cases) % 2 == 0 else "held-out"})
        if len(cases) == n:
            break
    return cases


def _question_groups_and_skills() -> tuple[dict, dict]:
    group_of = {r["id"]: r["group_id"] for r in db.rows("SELECT id, group_id FROM skills")}
    skills, groups = {}, {}
    for r in db.rows("SELECT question_id, tag_value FROM question_tags WHERE tag_type = 'skill'"):
        skills.setdefault(r["question_id"], set()).add(r["tag_value"])
        groups.setdefault(r["question_id"], set()).add(group_of[r["tag_value"]])
    return groups, skills


def covers_topics(qid: str, topics: list[str], groups: dict) -> bool:
    return all(TOPICS[t] & groups.get(qid, set()) for t in topics)


def _join(items: list[str], rng: random.Random) -> str:
    sep = rng.choice([", ", ", ", " and "])
    return (sep.join(items[:-1]) + (" and " if sep == ", " else sep) + items[-1]) if len(items) > 1 else items[0]


def topic_cases(n: int = 150, seed: int = 12) -> list[dict]:
    rng = random.Random(seed)
    groups, _ = _question_groups_and_skills()
    ids = sorted(groups)
    cases, seen = [], set()
    for qid in rng.sample(ids, len(ids)):
        have = sorted(t for t, g in TOPICS.items() if g & groups[qid])
        # a broad name and one of its own sub-topics ("differentiation" + "the chain rule") isn't a real request
        have = [t for t in have if not any(TOPICS[t] < TOPICS[o] or (TOPICS[t] == TOPICS[o] and t > o) for o in have)]
        if len(have) < 2:
            continue
        pick = rng.sample(have, rng.choice([2, 2, 3]) if len(have) >= 3 else 2)
        key = tuple(sorted(pick))
        if key in seen:
            continue
        seen.add(key)
        cases.append({"query": rng.choice(TOPIC_TEMPLATES).format(list=_join(pick, rng)), "topics": pick, "qid": qid,
                      "half": "calibrate" if len(cases) % 2 == 0 else "held-out"})
        if len(cases) == n:
            break
    return cases


def skill_cases(n: int = 150, seed: int = 13) -> list[dict]:
    rng = random.Random(seed)
    _, skills = _question_groups_and_skills()
    info = {r["id"]: r for r in db.rows("SELECT id, title, group_id FROM skills")}
    df = Counter(s for v in skills.values() for s in v)
    cases, seen = [], set()
    for qid in rng.sample(sorted(skills), len(skills)):
        core = sorted(s for s in skills[qid] if info[s]["group_id"] != db.EXAM_TECHNIQUE_GROUP and df[s] >= 3)
        if len(core) < 2:
            continue
        pick = rng.sample(core, 2)
        key = tuple(sorted(pick))
        if key in seen:
            continue
        seen.add(key)
        names = [info[s]["title"].lower() if rng.random() < 0.5 else s.replace("-", " ") for s in pick]
        cases.append({"query": rng.choice(SKILL_TEMPLATES).format(list=_join(names, rng)), "skills": pick, "qid": qid,
                      "half": "calibrate" if len(cases) % 2 == 0 else "held-out"})
        if len(cases) == n:
            break
    return cases


def run_description(misses: list) -> list[str]:
    cases = description_cases()
    buckets: dict[str, list[int]] = {}
    for c in cases:
        got = [i["question_id"] for i in find_practice(c["query"])["items"]]
        r1, r5 = got[:1] == [c["qid"]], c["qid"] in got[:5]
        for b in ("all", c["half"], c["qualification"], c["component"]):
            s = buckets.setdefault(b, [0, 0, 0])
            s[0] += r1
            s[1] += r5
            s[2] += 1
        if not r5:
            misses.append(("description", c["query"], c["qid"], got[:3]))
    order = ["all", "calibrate", "held-out", "9MA0", "IAL-2018", "IAL-2013", "GCE-2008", "pure", "stats", "mech"]
    return [f"descr. {b:9} n={v[2]:3}  recall@1 {v[0] / v[2]:5.1%}  recall@5 {v[1] / v[2]:5.1%}"
            for b in order if (v := buckets.get(b))]


def _run_multi(name: str, cases: list[dict], ok_fn, label: str, misses: list) -> list[str]:
    buckets: dict[str, list[float]] = {}
    for c in cases:
        got = [i["question_id"] for i in find_practice(c["query"])["items"]][:5]
        ok = [ok_fn(q, c) for q in got]
        for b in ("all", c["half"]):
            v = buckets.setdefault(b, [0, 0.0, 0])
            v[0] += bool(ok) and ok[0]
            v[1] += sum(ok) / 5
            v[2] += 1
        if not (ok and ok[0]):
            misses.append((name, c["query"], c.get("topics") or c.get("skills"), got[:3]))
    return [f"{name:6} {b:9} n={v[2]:3}  top-1 {label} {v[0] / v[2]:5.1%}  top-5 share {v[1] / v[2]:5.1%}"
            for b, v in buckets.items()]


def run_topics(misses: list) -> list[str]:
    groups, _ = _question_groups_and_skills()
    return _run_multi("topics", topic_cases(), lambda q, c: covers_topics(q, c["topics"], groups),
                      "covers every topic", misses)


def run_skills(misses: list) -> list[str]:
    _, skills = _question_groups_and_skills()
    return _run_multi("skills", skill_cases(), lambda q, c: set(c["skills"]) <= skills.get(q, set()),
                      "has both skills   ", misses)


def run_hand(misses: list) -> list[str]:
    groups, _ = _question_groups_and_skills()
    out, passed = [], 0
    for text, check, expected in HAND:
        got = [i["question_id"] for i in find_practice(text)["items"]]
        if check == "first":
            ok = got[:1] == [expected]
        elif check == "top5":
            ok = expected in got[:5]
        elif check == "text":
            ok = bool(got) and expected in db.one("SELECT question_text FROM questions WHERE id = ?", (got[0],))[0].lower()
        else:
            ok = bool(got) and covers_topics(got[0], expected, groups)
        passed += ok
        out.append(f"  {'OK  ' if ok else 'FAIL'} {text[:80]}  -> {got[:2]}")
    return [f"hand   {passed}/{len(HAND)} pass"] + out


def main() -> None:
    misses: list = []
    lines = run_description(misses) + run_topics(misses) + run_skills(misses) + run_hand(misses)
    print("\n".join(lines))
    if "--misses" in sys.argv:
        print("\nmisses:", *misses, sep="\n  ")
    if "--save" in sys.argv:
        label = sys.argv[sys.argv.index("--save") + 1]
        with RESULTS.open("a") as f:
            f.write(f"== {label}\n" + "\n".join(lines) + "\n\n")
    sys.stdout.flush()
    os._exit(0)  # onnxruntime can abort during interpreter teardown


if __name__ == "__main__":
    main()
