#!/usr/bin/env python3
"""Practice-request precision: does "give me a question on X" return questions that are
really tagged with X?

    .venv/bin/python -m eval.practice_eval

1. Every skill tagged on >= 3 parts (exam-technique skills excluded): the request
   "give me a question on <skill in words>" must resolve to that skill, and every returned
   question's part must carry it (precision).
2. Hand-written cases from real user reports: required skill/type, forbidden skills,
   and questions that must not be returned (already seen).
3. Specific-expression requests (user report 2026-09-27): the question containing the
   expression must be listed first, and every expression hit must really contain it.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chatbot import db  # noqa: E402
from chatbot.recommend import find_practice  # noqa: E402

CASES = [  # (request, exclude, required skill (any of), forbidden skills)
    ("give me a question including the 2nd derivative test", set(), {"second-derivative-test"}, set()),
    ("Hi give me a stats question on hypothesis testing with the normal districutuon", set(),
     {"state-hypotheses-normal-mean-test", "sample-mean-distribution"}, {"state-hypotheses-binomial-test"}),
    ("Okay nice, but I asked for a question with normal distribution hypothesis testing, not a binomial",
     {"P3_June2023_stats_Q4"}, {"state-hypotheses-normal-mean-test", "sample-mean-distribution"},
     {"state-hypotheses-binomial-test", "binomial-test-probability", "find-binomial-critical-region"}),
    ("give me a mechanics question on projectiles", set(),
     {"projectile-horizontal-motion", "projectile-time-of-flight-and-range", "projectile-greatest-height",
      "projectile-vertical-motion", "equation-of-trajectory"}, set()),
    ("a question on integration by parts please", set(), {"integration-by-parts"}, set()),
    ("binomial hypothesis test", set(), {"state-hypotheses-binomial-test", "binomial-test-probability",
                                         "find-binomial-critical-region"}, set()),
]


EXPR_CASES = [  # (request, question that must come first)
    ("Find me a question on differentiating x^x", "P2_June2019_Q11"),
]


def part_skills(qid: str, label: str | None) -> set[str]:
    return {r["tag_value"] for r in db.rows(
        "SELECT tag_value FROM question_tags WHERE question_id = ? AND tag_type = 'skill' "
        "AND COALESCE(part_label, '') = COALESCE(?, '')", (qid, label))}


def main() -> None:
    skills = db.rows("""SELECT s.id, count(*) AS n FROM skills s JOIN question_tags t ON t.tag_value = s.id
                        AND t.tag_type = 'skill' WHERE s.group_id != ? GROUP BY s.id HAVING n >= 3""",
                     (db.EXAM_TECHNIQUE_GROUP,))
    resolved = good = total = 0
    misses = []
    for r in skills:
        words = r["id"].replace("-", " ")
        res = find_practice(f"give me a question on {words}")
        resolved += bool(res["skills"]) and res["skills"][0] == r["id"]
        hits = [part_skills(i["question_id"], i["part_label"]) for i in res["items"]]
        ok = sum(r["id"] in h for h in hits)
        good += ok
        total += len(hits)
        if ok < len(hits) or not hits:
            misses.append((r["id"], res["skills"][:2], f"{ok}/{len(hits)}"))
    print(f"skills tested: {len(skills)} | request resolves to the skill: {resolved}/{len(skills)} "
          f"| precision (returned parts tagged with it): {good}/{total} = {good / max(total, 1):.0%}")
    for m in misses[:15]:
        print(f"   miss: {m[0]} -> resolved to {m[1]}, tagged {m[2]}")

    failed = 0
    for text, exclude, required, forbidden in CASES:
        res = find_practice(text, exclude_questions=exclude)
        problems = []
        for it in res["items"]:
            sk = part_skills(it["question_id"], it["part_label"])
            if it["question_id"] in exclude:
                problems.append(f"{it['question_id']} was already seen")
            if not sk & required:
                problems.append(f"{it['question_id']}({it['part_label']}) lacks {sorted(required)[:2]}")
            if sk & forbidden:
                problems.append(f"{it['question_id']}({it['part_label']}) has forbidden {sorted(sk & forbidden)}")
        if not res["items"]:
            problems.append("no questions returned")
        failed += bool(problems)
        print(f"{'OK  ' if not problems else 'FAIL'} {text[:70]}" + "".join(f"\n     {p}" for p in problems[:4]))
    from chatbot.recommend import _norm_math
    for text, first in EXPR_CASES:
        res = find_practice(text)
        ids = [i["question_id"] for i in res["items"]]
        expr = res.get("expression")
        bad = [i["question_id"] for i in res["items"] if i["reason"].startswith("contains") and expr not in
               _norm_math(db.one("SELECT question_text FROM questions WHERE id = ?", (i["question_id"],))["question_text"])]
        problems = ([] if ids[:1] == [first] else [f"first is {ids[:1]}, expected {first}"]) + \
                   [f"{b} doesn't contain {expr}" for b in bad]
        failed += bool(problems)
        print(f"{'OK  ' if not problems else 'FAIL'} {text[:70]}" + "".join(f"\n     {p}" for p in problems))
    sys.stdout.flush()
    os._exit(1 if failed else 0)


if __name__ == "__main__":
    main()
