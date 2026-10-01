"""Self-test for chatbot/profile.py (the mark-leakage profile page).

    .venv/bin/python -m eval.profile_selftest

No model calls, no network. Seeds a temporary events DB with a few be-the-examiner and mark-my-working events
(the pattern of eval/marks_selftest.py), then checks totals, top error codes, that drills resolve to real
gate-passed items, exercises and playbooks, that the plain summary names the top family, and the empty state.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, examiner, marks, profile  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


items = {it["id"]: it for it in examiner.load_items()}
check(items, "no gate-passed items")
# pick a real error code that has pitfalls, exercises and a playbook, so the drills have something to resolve to
codes_with_items = {pf["error_code"] for it in items.values() for pf in it.get("pitfalls") or [] if pf.get("error_code")}
codes_with_ex = {e["error_code"] for e in examiner.all_exercises() if e.get("error_code")}
codes_with_pb = set(profile._playbooks_by_code())
rich = sorted(codes_with_items & codes_with_ex & codes_with_pb) or sorted(codes_with_items & codes_with_ex)
check(rich, "no error code with items, exercises and a playbook")
top_code = rich[0]
second_code = "premature-rounding"
skill = next(iter(items.values()))["parts"][0].get("skills", ["integrate-powers-of-x"])[0]

with tempfile.TemporaryDirectory() as td:
    conn = events.connect(Path(td) / "events.db")
    # be-the-examiner: 4 judgements, 3 agree with the reference
    dec = [dict(marks.parse(c).as_dict(), user_judgement=uj, error_code=ec, skill=skill)
           for c, uj, ec in (("M1", True, None), ("A0", False, top_code), ("dM1", True, None), ("A0", True, None))]
    events.record("u1", "be-the-examiner", "cr-x", None, dec, script_id="r2", conn=conn)
    # mark-my-working: 10 marks available, method kept, 4 accuracy lost (3 to top_code, 1 to second_code)
    dec2 = [dict(marks.parse(c).as_dict(), error_code=ec, skill=skill)
            for c, ec in (("M1", None), ("A0", top_code), ("dM1", None), ("A0", top_code), ("B1", None))]
    events.record("u1", "mark-my-working", "cr-y", "a", dec2, model="test", cost_usd=0.01, conn=conn)
    dec3 = [dict(marks.parse(c).as_dict(), error_code=ec, skill=skill)
            for c, ec in (("M1", None), ("A0", top_code), ("M1", None), ("A0", second_code), ("A1", None))]
    events.record("u1", "mock", "cr-z", None, dec3, conn=conn)

    v = profile.view("u1", conn=conn)
    json.dumps(v)  # JSON-safe
    check(v["totals"] == {"available": 10, "lost": 4, "kept": 6, "lost_pct": 40}, f"totals {v['totals']}")
    fam = {f["family"]: f for f in v["by_family"]}
    check(fam["method"]["lost"] == 0 and fam["method"]["available"] == 4, f"method family {fam.get('method')}")
    check(fam["accuracy"]["lost"] == 4 and fam["accuracy"]["share_of_lost"] == 100, f"accuracy family {fam.get('accuracy')}")
    check([c["code"] for c in v["top_error_codes"]] == [top_code, second_code], f"top codes {[c['code'] for c in v['top_error_codes']]}")
    top = v["top_error_codes"][0]
    check(top["lost"] == 3 and top["definition"] and top["loses_family"] in ("method", "accuracy", "independent"), f"top code {top}")
    check(top["skills"] and top["skills"][0]["id"] == skill and top["skills"][0]["lost"] == 3, f"skills hit {top['skills']}")
    d = top["drills"]
    check(d["items"] and all(x["item_id"] in items for x in d["items"]), f"drill items {d['items']}")
    check(all(x["learn_url"] == f"/learn?item={x['item_id']}" and x["mark_url"] == f"/mark?item={x['item_id']}" for x in d["items"]), "drill urls")
    check(all(any(pf.get("error_code") == top_code for pf in items[x["item_id"]]["pitfalls"]) for x in d["items"]), "drill items carry the code")
    check(d["exercises"] and all(examiner.find(x["item_id"], x["script_id"]) for x in d["exercises"]), f"drill exercises {d['exercises']}")
    check(all(profile.exercise(x["key"]) for x in d["exercises"]), "exercise() resolves drill keys")
    check(all((ROOT / "content" / "clean" / "playbooks" / f"{p['id']}.json").exists() for p in d["playbooks"]), "playbooks exist")
    if top_code in codes_with_pb:
        check(d["playbooks"], "playbook drills for a code that has one")
    check(v["top_skills"] and v["top_skills"][0]["id"] == skill and v["top_skills"][0]["lost"] == 4, f"top skills {v['top_skills']}")
    check(len(v["trend"]) == 8 and v["trend"][-1]["available"] == 10 and v["trend"][-1]["lost_share"] == 40, f"trend {v['trend'][-1]}")
    check(v["examiner_accuracy"] == {"judged": 4, "correct": 3, "rate": 0.75}, f"examiner accuracy {v['examiner_accuracy']}")
    s = profile.plain_summary(v)
    check(s and "accuracy" in s and "method" in s, f"summary {s!r}")
    check(s == v["summary"], "summary stored on the view")
    check(len([x for x in s.split(". ") if x]) in (2, 3), f"summary sentence count {s!r}")
    print("example summary:", s)

    # empty user
    e = profile.view("nobody", conn=conn)
    json.dumps(e)
    check(e["empty"] and e["totals"]["available"] == 0 and e["top_error_codes"] == [] and e["top_skills"] == [], f"empty {e['totals']}")
    check("Nothing to profile yet" in e["summary"], f"empty summary {e['summary']!r}")
    check(len(e["trend"]) == 8, "empty trend still 8 weeks")
    conn.close()

check(profile.exercise("no::such") is None and profile.exercise("junk") is None, "exercise() on junk")

print(f"profile self-test: {'PASS' if not fails else 'FAIL'} ({len(items)} items, top code {top_code})")
for f in fails:
    print("   ", f)
sys.exit(1 if fails else 0)
