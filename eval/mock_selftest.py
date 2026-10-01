"""Self-test for chatbot/mock.py (timed mocks): the practice set follows the 9MA0 pure mix at about 50 marks, paper()
carries question texts, and submit() with a monkeypatched marker returns totals, family/skill breakdowns, a grade and
records "mock" events into a temporary database.

    .venv/bin/python -m eval.mock_selftest

No model calls, no network. Reads only content/clean, content/blueprints, content/facts and content/boards.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, marker, marks, mock  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- papers() / paper() -------------------------------------------------------------------------------------
ps = mock.papers()
check(any(p["id"] == mock.PRACTICE_ID for p in ps), "no practice set in papers()")
pr = mock.paper(mock.PRACTICE_ID)
check(pr is not None, "paper(practice) is None")
check(40 <= pr["marks"] <= 56, f"practice set has {pr['marks']} marks (want ~50)")
check(pr["minutes"] == round(pr["marks"] * mock.MINUTES_PER_MARK), "minutes not 1.2 per mark")
check(all(q["component"] == "pure" for q in pr["questions"]), "practice set has a non-pure item")
check(len({q["item_id"] for q in pr["questions"]}) == len(pr["questions"]), "duplicate item in practice set")
check(all(q["parts"] and all(pt["text"] for pt in q["parts"]) for q in pr["questions"]), "a question has no part text")
check([q["q_num"] for q in pr["questions"]] == list(range(1, len(pr["questions"]) + 1)), "q_num not 1..n")
mix = pr.get("mix") or {}
check(set(mix) == set(mock.BANDS), f"mix bands {sorted(mix)}")
tot = sum(mix.values()) or 1
targets = mock.mix_targets()
tvd = 0.5 * sum(abs(mix[b] / tot - targets[b]) for b in mock.BANDS)
check(tvd < 0.25, f"practice mix TVD from 9MA0 pure mix is {tvd:.2f} (want < 0.25): {mix}")
check(mock.paper(mock.PRACTICE_ID)["questions"] == pr["questions"], "practice set is not deterministic")
check(mock.paper("no-such-paper") is None, "unknown paper should be None")
for p in ps:  # file papers, if the other agent has written any, must also resolve
    check(mock.paper(p["id"]) is not None, f"paper({p['id']}) missing")

# ---- grades -----------------------------------------------------------------------------------------------
b = mock.boundaries_for(300)
check(b == {"A*": 254, "A": 210, "B": 173, "C": 136, "D": 99, "E": 62}, f"boundaries out of 300: {b}")
check(mock.boundaries_for(100)["A*"] == 85 and mock.boundaries_for(100)["C"] == 45, "scaling to 100")
check(mock.estimate_grade(254, 300)["grade"] == "A*", "254/300 should be A*")
check(mock.estimate_grade(253, 300)["grade"] == "A", "253/300 should be A")
check(mock.estimate_grade(0, 300)["grade"] == "U", "0/300 should be U")
check(mock.estimate_grade(135, 300)["next_grade"] == "C" and mock.estimate_grade(135, 300)["marks_to_next"] == 1, "next grade")

# ---- submit() with a fake marker -----------------------------------------------------------------------------
calls = []


def fake_mark(item, part_label, working, **kw):
    """Awards every mark except the last one of each part, coding the loss."""
    parts = marker.select_parts(item, part_label)
    decisions, summary, vectors = [], {}, {}
    for p in parts:
        codes = [m["code"] for m in p["mark_scheme"]]
        decs = []
        for i, c in enumerate(codes):
            awarded = i < len(codes) - 1
            m = marks.parse(c)
            decs.append({"part": p.get("label"), "position": i, "code": c if awarded else marks.withheld(c), "scheme_code": c,
                         "awarded": awarded, "evidence": working["lines"][0] if working["lines"] else "none",
                         "reason": "fake", "confidence": 0.9, "error_code": None if awarded else "arithmetic-slip",
                         "rewrite_to_earn": None if awarded else "finish the line", "skill": (p.get("skills") or [None])[0],
                         "overridden": False, "self_contradiction": False, "missing": False, "convention": None})
        vec = [d["code"] for d in decs]
        label = marker.norm_label(p.get("label"))
        vectors[label] = vec
        summary[label] = marks.vector_summary(codes, vec)
        decisions += decs
    calls.append((item["id"], part_label))
    return {"decisions": decisions, "summary": summary, "vectors": vectors, "facts": ["fake fact"], "model": "fake",
            "cost_usd": 0.01, "seconds": 0.1, "overrides": 0,
            "total": sum(s["total"] for s in summary.values()), "earned": sum(s["earned"] for s in summary.values()), "lines": working["lines"]}


real_mark = marker.mark
marker.mark = fake_mark
try:
    with tempfile.TemporaryDirectory() as td:
        conn = events.connect(Path(td) / "events.db")
        q1, q2 = pr["questions"][0], pr["questions"][-1]
        answers = {q1["item_id"]: {q1["parts"][0]["key"]: "x = 1\n$y = 2$"},
                   q2["item_id"]: {q2["parts"][0]["key"]: "some working", q2["parts"][-1]["key"]: "   "}}  # blank = not attempted
        out = mock.submit("selftest-user", mock.PRACTICE_ID, answers, 1234, conn=conn)
        check("error" not in out, f"submit error: {out.get('error')}")
        check(out["marks"] == pr["marks"], "submit total marks differ from paper")
        check(len(calls) == 2, f"expected 2 marker calls, got {len(calls)}")
        want = (q1["parts"][0]["marks"] - 1) + (q2["parts"][0]["marks"] - 1)
        check(out["earned"] == want, f"earned {out['earned']} want {want}")
        check(out["parts_attempted"] == 2, f"parts_attempted {out['parts_attempted']}")
        check(out["parts_total"] == sum(len(q["parts"]) for q in pr["questions"]), "parts_total")
        q1o = out["questions"][0]
        check(q1o["attempted"] and q1o["earned"] == want - (q2["parts"][0]["marks"] - 1), "question 1 earned")
        check(q1o["parts"][0]["decisions"] and q1o["parts"][0]["decisions"][-1]["error_code"] == "arithmetic-slip", "decision views")
        check(all(pt["not_attempted"] and pt["earned"] == 0 for q in out["questions"][1:-1] for pt in q["parts"]), "middle questions not flagged")
        check(out["questions"][-1]["parts"][-1]["not_attempted"], "blank part should be not attempted")
        fam = out["by_family"]
        check(sum(v["available"] for v in fam.values()) == pr["marks"], f"family available != paper marks: {fam}")
        check(sum(v["lost"] for v in fam.values()) == pr["marks"] - want, "family lost != marks lost")
        check(sum(v["not_attempted"] for v in fam.values()) == pr["marks"] - q1["parts"][0]["marks"] - q2["parts"][0]["marks"], "not_attempted marks")
        check(out["by_skill"] and all("title" in v and "lost" in v for v in out["by_skill"].values()), "by_skill shape")
        check(out["top_error_codes"] and out["top_error_codes"][0]["code"] == "arithmetic-slip" and out["top_error_codes"][0]["marks"] == 2, "top error codes")
        g = out["grade"]
        check(g["grade"] in mock.GRADE_ORDER and g["out_of"] == pr["marks"] and g["boundaries"] == mock.boundaries_for(pr["marks"]), "grade shape")
        check(g["grade"] == mock.estimate_grade(want, pr["marks"])["grade"], "grade mismatch")
        rows = conn.execute("SELECT source, item_id, part_label, meta FROM marking_events").fetchall()
        check(len(rows) == 2 and all(r["source"] == "mock" for r in rows), f"expected 2 mock events, got {[tuple(r)[:3] for r in rows]}")
        check(all('"paper_id": "practice-pure-50"' in r["meta"] for r in rows), "event meta lacks paper_id")
        n_dec = conn.execute("SELECT COUNT(*) FROM mark_decisions").fetchone()[0]
        check(n_dec == q1["parts"][0]["marks"] + q2["parts"][0]["marks"], f"decisions recorded {n_dec}")
        prof = events.leakage_profile("selftest-user", conn=conn)
        check(prof["total_lost"] == 2 and prof["by_error_code"].get("arithmetic-slip") == 2, f"leakage profile {prof}")
        check(out["profile"] and out["profile"]["total_lost"] == 2, "profile in result")
        # a failing marker must not raise
        marker.mark = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        out2 = mock.submit("selftest-user", mock.PRACTICE_ID, {q1["item_id"]: {q1["parts"][0]["key"]: "x"}}, 5, conn=conn)
        check(out2["earned"] == 0 and out2["questions"][0]["parts"][0]["error"] and out2["questions"][0]["parts"][0]["attempted"], "marker failure handling")
        check(mock.submit("u", "nope", {}, 0).get("error"), "unknown paper on submit")
        conn.close()
finally:
    marker.mark = real_mark

print(f"practice set: {pr['marks']} marks, {pr['minutes']} min, {len(pr['questions'])} questions, mix {mix}, TVD {tvd:.2f}")
print(f"papers: {[p['id'] for p in ps]}")
if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
print("OK: all mock self-test checks passed")
