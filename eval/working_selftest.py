"""Self-test for chatbot/working.py ("Mark my working" orchestration): the catalogue, and submit() with the marker
monkeypatched so no model is called. Events go to a temporary database.

    .venv/bin/python -m eval.working_selftest

No model calls, no network. Reads only content/clean, content/boards and content/error_codes.json.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, marker, working  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- catalogue --------------------------------------------------------------------------------------
cat = working.catalogue()
check(len(cat) >= 20, f"only {len(cat)} items in the catalogue (need >= 20)")
check(all(c["title"] and c["item_id"] and c["parts"] for c in cat), "every entry needs a title, id and parts")
check(all(c["marks"] == sum(p["marks"] for p in c["parts"]) for c in cat), "marks = sum of parts")
check(all(p["text"] for c in cat for p in c["parts"]), "every part has text")
check(len({c["item_id"] for c in cat}) == len(cat), "item ids unique")
titles = working.question_type_titles()
check(sum(1 for c in cat if c["question_type"] in titles) >= 20, "titles should come from tags.json question_types")
check(working.error_code_definitions().get("arithmetic-slip"), "error code definitions loaded")
check(working.find_item(cat[0]["item_id"]) is not None and working.find_item("nope") is None, "find_item")

# ---- submit with a monkeypatched marker ------------------------------------------------------------
item_id = "cr-area-between-curve-and-line-core"
item = working.find_item(item_id)
check(item is not None, f"{item_id} must pass the gates")
part = item["parts"][0]
scheme = [m["code"] for m in part["mark_scheme"]]  # M1 A1 M1 dM1 A1*
codes = ["M1", "A1", "M0", "dM0", "A0*"]
seen = {}


def fake_mark(it, part_label, working_, *, facts=None, model=marker.DEFAULT_MODEL, max_usd=0.5, thinking_tokens=4000, ref=""):
    seen.update(item=it["id"], part_label=part_label, working=working_, ref=ref)
    decs = []
    for i, (sc, c) in enumerate(zip(scheme, codes)):
        aw = "0" not in c
        decs.append({"scheme_code": sc, "code": c, "awarded": aw, "evidence": f"L{i + 1}: line {i + 1}",
                     "reason": "earned" if aw else "the integrand was subtracted the wrong way round",
                     "convention": "dependency" if i == 3 else "M" if sc.startswith("M") else "A",
                     "error_code": None if aw else "area-between-wrong-subtraction",
                     "rewrite_to_earn": None if aw else "Write (top curve) - (bottom line) before integrating.",
                     "confidence": 0.9 if i != 4 else 0.3, "overridden": i == 3, "part": None, "position": i,
                     "skill": (part.get("skills") or [None])[0]})
    from chatbot import marks
    summary = {"-": marks.vector_summary(scheme, codes)}
    return {"decisions": decs, "summary": summary, "vectors": {"-": codes}, "facts": ["sympy: fact"], "model": model,
            "cost_usd": 0.031, "seconds": 9.5, "overrides": 1, "total": 5, "earned": 2, "lines": marker._lines_of(working_)}


real_mark, marker.mark = marker.mark, fake_mark
try:
    with tempfile.TemporaryDirectory() as td:
        conn = events.connect(Path(td) / "events.db")
        out = working.submit("u-test", item_id, None, "$x^2-7x+6=0$\n\n  $x = 1, 6$  \nArea = 125/6", conn=conn)
        check("error" not in out, f"submit error {out.get('error')} {out.get('detail')}")
        check(seen.get("item") == item_id and seen.get("part_label") is None, f"marker called with {seen}")
        check(isinstance(seen.get("working"), dict) and seen["working"]["lines"] == ["$x^2-7x+6=0$", "$x = 1, 6$", "Area = 125/6"],
              f"transcript passed to marker {seen.get('working')}")
        check(out["transcript"]["lines"] == ["$x^2-7x+6=0$", "$x = 1, 6$", "Area = 125/6"], f"transcript {out['transcript']}")
        check(out["facts"] == ["sympy: fact"], "facts passed through")
        d = out["decisions"]
        check(len(d) == 5 and [x["code"] for x in d] == codes, f"decision codes {[x['code'] for x in d]}")
        want = {"code", "scheme_code", "awarded", "evidence", "reason", "convention", "convention_short", "error_code",
                "rewrite_to_earn", "confidence", "overridden", "self_contradiction", "for", "check_this", "position"}
        check(all(want <= set(x) for x in d), f"decision keys missing {want - set(d[0])}")
        check(all(x["for"] == m["for"] for x, m in zip(d, part["mark_scheme"])), "scheme 'for' lines attached")
        check(all(x["convention_short"] for x in d), "convention_short filled")
        check(d[2]["error_definition"] and "area-between" in d[2]["error_code"], "error definition attached")
        check(d[3]["check_this"] and d[4]["check_this"] and not d[0]["check_this"], "check_this: overridden, low confidence")
        check(d[0]["rewrite_to_earn"] is None and d[2]["rewrite_to_earn"], "rewrite only on withheld marks")
        p = out["parts"][0]
        check(len(out["parts"]) == 1 and p["earned"] == 2 and p["total"] == 5, f"part summary {p}")
        check(p["lost_by_family"] == {"method": 2, "accuracy": 1} and p["implied_positions"] == [3, 4], f"part summary {p}")
        check(out["summary"] == {"earned": 2, "total": 5, "lost_by_family": {"method": 2, "accuracy": 1}, "implied": 2, "check_this": 2},
              f"summary {out['summary']}")
        check(out["cost_usd"] == 0.031 and out["model"] == marker.DEFAULT_MODEL, "cost and model passed through")
        check(len(out["event_ids"]) == 1 and out["event_ids"][0], f"one event per part {out['event_ids']}")
        rows = conn.execute("SELECT * FROM marking_events").fetchall()
        check(len(rows) == 1 and rows[0]["source"] == "mark-my-working" and rows[0]["item_id"] == item_id
              and rows[0]["part_label"] is None and rows[0]["transcript_confirmed"] == 1 and rows[0]["cost_usd"] == 0.031
              and rows[0]["model"] == marker.DEFAULT_MODEL, f"event row {dict(rows[0]) if rows else None}")
        decs = conn.execute("SELECT * FROM mark_decisions ORDER BY position").fetchall()
        check(len(decs) == 5 and [r["awarded"] for r in decs] == [1, 1, 0, 0, 0], "decision rows")
        check(decs[2]["error_code"] == "area-between-wrong-subtraction" and decs[2]["skill"] == "area-between-curve-and-line", "decision row fields")
        prof = out["profile"]
        check(prof and prof["total_lost"] == 3 and prof["by_family"] == {"method": {"available": 3, "lost": 2}, "accuracy": {"available": 2, "lost": 1}},
              f"profile {prof and prof['by_family']}")
        check(prof["by_error_code"] == {"area-between-wrong-subtraction": 3}, f"profile codes {prof['by_error_code']}")
        check(prof["error_code_definitions"].get("area-between-wrong-subtraction") and prof["skill_titles"].get("area-between-curve-and-line"),
              "profile carries definitions and skill titles")
        check(working.profile("u-test", conn=conn)["total_lost"] == 3, "profile()")
        # JSON-safe
        import json
        json.dumps(out)
        # friendly errors
        check(working.submit("u-test", "no-such-item", None, "x", conn=conn).get("error"), "unknown item -> error")
        check(working.submit("u-test", item_id, None, "  \n ", conn=conn).get("error"), "empty text -> error")
        check(working.submit("u-test", item_id, "z", "x", conn=conn).get("error"), "unknown part -> error")

        def boom(*a, **k):
            raise RuntimeError("claude exited 1")
        marker.mark = boom
        e = working.submit("u-test", item_id, None, "x", conn=conn)
        check(e.get("error") == working.FRIENDLY_ERROR and "RuntimeError" in e.get("detail", ""), f"model failure wrapped {e}")
        check(conn.execute("SELECT count(*) FROM marking_events").fetchone()[0] == 1, "failed calls record nothing")
        # multi-part item marked whole: one event per part
        marker.mark = fake_mark
        multi = next(c for c in cat if len(c["parts"]) > 1)
        mitem = working.find_item(multi["item_id"])

        def fake_multi(it, part_label, working_, **kw):
            from chatbot import marks
            decs, summary, vectors = [], {}, {}
            for p in it["parts"]:
                sc = [m["code"] for m in p["mark_scheme"]]
                lab = marker.norm_label(p["label"])
                vectors[lab] = list(sc)
                summary[lab] = marks.vector_summary(sc, sc)
                decs += [{"scheme_code": c, "code": c, "awarded": True, "evidence": "L1: x", "reason": "ok", "convention": "M",
                          "error_code": None, "rewrite_to_earn": None, "confidence": 1.0, "overridden": False, "part": p["label"],
                          "position": i, "skill": None} for i, c in enumerate(sc)]
            return {"decisions": decs, "summary": summary, "vectors": vectors, "facts": [], "model": "m", "cost_usd": 0.02,
                    "seconds": 1, "overrides": 0, "total": sum(s["total"] for s in summary.values()),
                    "earned": sum(s["total"] for s in summary.values()), "lines": ["x"]}
        marker.mark = fake_multi
        out2 = working.submit("u-test", multi["item_id"], None, "x", conn=conn)
        check(len(out2["event_ids"]) == len(mitem["parts"]) and len(out2["parts"]) == len(mitem["parts"]), "one event per part on a whole-question marking")
        costs = [r[0] for r in conn.execute("SELECT cost_usd FROM marking_events WHERE item_id = ? ORDER BY at", (multi["item_id"],))]
        check(sum(costs) == 0.02, f"cost recorded once per call {costs}")
        out3 = working.submit("u-test", multi["item_id"], mitem["parts"][0]["label"], "x", conn=conn)
        check(seen.get("item") == item_id or True, "noop")
        check(len(out3["parts"]) == 1 and out3["part_label"] == mitem["parts"][0]["label"], f"single part marking {out3.get('part_label')}")
        conn.close()
finally:
    marker.mark = real_mark

print(f"working self-test: {'PASS' if not fails else 'FAIL'} ({len(cat)} items in the catalogue)")
for f in fails[:40]:
    print("   ", f)
sys.exit(1 if fails else 0)
