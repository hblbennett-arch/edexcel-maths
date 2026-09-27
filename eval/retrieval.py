#!/usr/bin/env python3
"""Phase 4 retrieval evaluation.

    .venv/bin/python -m eval.retrieval                                  # default model
    .venv/bin/python -m eval.retrieval --model BAAI/bge-base-en-v1.5    # compare another model

Measures:
  references    reference parsing (question + part) accuracy
  pasted        pasted-question identification: top-1 accuracy (generated from the data:
                whole question, truncated question, and a single later part pasted alone)
  new           questions NOT in the knowledge base must not be falsely matched
  generic       free-text queries: expected skill in the top 5 (recall@5) and MRR
  recommend     property checks over every part: recommendations exclude the question
                itself, each broad list really practises its skill, every part gets a ladder
Pasted and generic are scored for hybrid / semantic / bm25 search, to justify the mode.
Targets (plan): pasted top-1 >= 90%, generic recall@5 >= 80%.
"""
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from chatbot import db, identify as ident, recommend, search  # noqa: E402
from chatbot.text import latex_to_plain  # noqa: E402

QUERIES = json.loads((ROOT / "eval" / "retrieval_queries.json").read_text())


def pasted_cases(n: int = 30, seed: int = 7) -> list[tuple[str, str, str]]:
    """(style, text, expected question id): how students actually paste questions."""
    rng = random.Random(seed)
    qs = db.rows("SELECT id, question_text FROM questions ORDER BY id")
    picked = rng.sample(list(qs), n)
    cases = []
    for i, q in enumerate(picked):
        plain = latex_to_plain(q["question_text"])
        style = ("whole", "truncated", "one-part")[i % 3]
        if style == "truncated":
            words = plain.split()
            plain = " ".join(words[: max(20, int(len(words) * 0.5))])
        elif style == "one-part":
            parts = db.rows("SELECT text FROM question_parts WHERE question_id = ? ORDER BY part_index", (q["id"],))
            plain = latex_to_plain(parts[-1]["text"]) if len(parts) > 1 else plain
            if len(plain.split()) < 20:
                style, plain = "whole", latex_to_plain(q["question_text"])
        cases.append((style, plain.lower(), q["id"]))
    return cases


def eval_references() -> tuple[int, int, list]:
    ok, fails = 0, []
    for c in QUERIES["references"]:
        r = ident.parse_reference(c["text"])
        if c.get("expect_message"):
            good = r is not None and r.question_id is None and bool(r.message)
        else:
            good = r is not None and r.question_id == c["qid"] and r.part_label == c["part"]
        ok += good
        if not good:
            fails.append((c["text"], r and (r.question_id, r.part_label, r.message)))
    return ok, len(QUERIES["references"]), fails


def eval_pasted(ix: search.Index, mode: str) -> tuple[float, dict, list]:
    by_style, fails = {}, []
    for style, text, qid in pasted_cases():
        hits = ix.search(text, "question", k=3, mode=mode)
        top = hits[0].doc_id.split(":", 1)[1]
        s = by_style.setdefault(style, [0, 0])
        s[0] += top == qid
        s[1] += 1
        if top != qid:
            fails.append((style, qid, top, text[:70]))
    total = sum(v[0] for v in by_style.values()) / sum(v[1] for v in by_style.values())
    return total, {k: f"{v[0]}/{v[1]}" for k, v in by_style.items()}, fails


def eval_identify_decisions() -> dict:
    """End-to-end identify(): pasted cases should be matched, new questions should not."""
    pos = [ident.identify(t) for _, t, _ in pasted_cases()]
    exp = [qid for _, _, qid in pasted_cases()]
    confident = sum(r.kind == "pasted_match" and r.question_id == q for r, q in zip(pos, exp))
    asked = sum(r.kind == "possible_match" and r.question_id == q for r, q in zip(pos, exp))
    wrong = sum(r.question_id not in (None, q) for r, q in zip(pos, exp))
    neg = [ident.identify(t) for t in QUERIES["new_questions"]]
    return {"pasted: confident & right": f"{confident}/{len(exp)}", "pasted: asks to confirm, right": asked,
            "pasted: wrong question": wrong,
            "new: correctly treated as new": f"{sum(r.kind == 'new_question' for r in neg)}/{len(neg)}",
            "new: bot asks to confirm": sum(r.kind == "possible_match" for r in neg),
            "new: FALSE confident match": [(r.question_id) for r in neg if r.kind == "pasted_match"]}


def eval_generic(ix: search.Index, mode: str) -> tuple[float, float, list]:
    hits_at5, rr, fails = 0, 0.0, []
    for c in QUERIES["generic"]:
        got = [h.doc_id.split(":", 1)[1] for h in ix.search(c["text"], "skill", k=5, mode=mode)]
        ranks = [got.index(s) + 1 for s in c["skills"] if s in got]
        hits_at5 += bool(ranks)
        rr += 1 / min(ranks) if ranks else 0
        if not ranks:
            fails.append((c["text"], c["skills"], got[:3]))
    n = len(QUERIES["generic"])
    return hits_at5 / n, rr / n, fails


def eval_recommend() -> dict:
    parts, _, _ = recommend._catalogue()
    problems, ladders = [], 0
    for key, p in parts.items():
        qid, label = p["question_id"], p["label"]
        for group in recommend.broad(qid, label):
            for rec in group["parts"]:
                rk = db.part_key(rec["question_id"], rec["part_label"])
                if rec["question_id"] == qid:
                    problems.append(f"{key}: recommends its own question")
                if group["skill"] not in parts[rk]["skills"]:
                    problems.append(f"{key}: {rk} doesn't practise {group['skill']}")
        ladders += bool(recommend.ladder(qid, label))
    no_type = [q["id"] for q in db.rows("SELECT id FROM questions") if not recommend.narrow(q["id"])]
    return {"parts": len(parts), "problems": problems[:5], "n_problems": len(problems),
            "parts_with_ladder": f"{ladders}/{len(parts)}", "questions_without_same_type": no_type}


def main() -> None:
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else search.DEFAULT_MODEL
    ix = search.Index(model)
    search.get_index.cache_clear()
    search.get_index = lambda m=model: ix  # identify() uses the same index
    ident.get_index = search.get_index
    print(f"model: {model}\n")
    ok, n, fails = eval_references()
    print(f"references      {ok}/{n}" + (f"  fails: {fails}" if fails else ""))
    for mode in ("hybrid", "semantic", "bm25"):
        acc, styles, pfails = eval_pasted(ix, mode)
        r5, mrr, gfails = eval_generic(ix, mode)
        print(f"{mode:8} pasted top-1 {acc:5.0%} {styles}   generic recall@5 {r5:4.0%} MRR {mrr:.2f}")
        if mode == "hybrid":
            hybrid_fails = (pfails, gfails)
    from chatbot.retrieve import rank_skills
    got_all = [(c, rank_skills(c["text"], k=5, part_votes=10)) for c in QUERIES["generic"]]
    rr = [1 / min(g.index(s) + 1 for s in c["skills"] if s in g) if any(s in g for s in c["skills"]) else 0 for c, g in got_all]
    print(f"rank_skills with part votes (not used by default): recall@5 {sum(r > 0 for r in rr) / len(rr):.0%} MRR {sum(rr) / len(rr):.2f}")
    print(f"\nidentify() end to end: {eval_identify_decisions()}")
    print(f"recommendations: {eval_recommend()}")
    pfails, gfails = hybrid_fails
    if pfails:
        print("\nhybrid pasted misses:", *pfails, sep="\n  ")
    if gfails:
        print("\nhybrid generic misses (query, expected, got top-3):", *gfails, sep="\n  ")
    sys.stdout.flush()
    os._exit(0)  # onnxruntime can abort during interpreter teardown


if __name__ == "__main__":
    main()
