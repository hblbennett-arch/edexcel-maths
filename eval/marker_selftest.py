"""Self-test for chatbot/marker.py (the product marker). No model calls, no network: claude_oneshot.run is
monkeypatched, so the tests cover transcribe(), transcribe_image()'s request, final_answer_facts() on a real
item, the dependency override in mark(), and to_decisions().

    .venv/bin/python -m eval.marker_selftest
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, marker, marks  # noqa: E402
import claude_oneshot  # noqa: E402  (chatbot.marker puts scripts/ on the path)

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- transcribe -----------------------------------------------------------------------------------
t = marker.transcribe("  $x^2 - 7x + 6 = 0$ \r\n\n   x = 1,   6  \n")
check(t["lines"] == ["$x^2 - 7x + 6 = 0$", "x = 1, 6"], f"transcribe lines {t['lines']}")
check(t["confidence"] == 1.0 and t["needs_confirmation"] is False, "transcribe flags")
check(marker.transcribe("") == {"lines": [], "confidence": 1.0, "needs_confirmation": False, "source": "typed"}, "empty")
check(marker.numbered(["a", "b"]) == "L1: a\nL2: b", "numbered")

# ---- transcribe_image: builds a valid image request (monkeypatched model) --------------------------
seen = {}


def fake_run(system, content, *, schema=None, model="", max_usd=0, thinking_tokens=0, step="", ref="", timeout=0):
    seen.update(system=system, content=content, schema=schema, model=model, step=step, ref=ref)
    if step.endswith("transcribe"):
        return {"result": {"lines": [{"text": " $x^2-7x+6=0$ ", "confidence": 0.95}, {"text": "x = 1, 6", "confidence": 0.7},
                                     {"text": "  ", "confidence": 1}]}, "cost_usd": 0.01, "usage": {}, "seconds": 1}
    return {"result": fake_run.reply, "cost_usd": 0.02, "usage": {}, "seconds": 2}


real_run, claude_oneshot.run = claude_oneshot.run, fake_run
try:
    with tempfile.TemporaryDirectory() as td:
        img = Path(td) / "working.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        ti = marker.transcribe_image(img, ref="t1")
        blk = seen["content"][0]
        check(blk["type"] == "image" and blk["source"]["type"] == "base64" and blk["source"]["media_type"] == "image/png",
              f"image block {json.dumps(blk)[:120]}")
        check(blk["source"]["data"].startswith("iVBORw0KGgo"), "image base64 payload")
        check(seen["content"][1]["type"] == "text" and seen["schema"] is marker.TRANSCRIBE_SCHEMA, "transcribe request shape")
        check(seen["step"] == "marker-v2-transcribe" and seen["model"] == marker.DEFAULT_MODEL, f"transcribe step {seen['step']}")
        check(ti["lines"] == ["$x^2-7x+6=0$", "x = 1, 6"] and ti["needs_confirmation"] is True, f"transcribe_image {ti}")
        check(ti["confidence"] == 0.7 and ti["line_confidence"] == [0.95, 0.7], f"confidences {ti}")
        jpg = Path(td) / "w.JPG"
        jpg.write_bytes(b"\xff\xd8\xff")
        marker.transcribe_image(jpg)
        check(seen["content"][0]["source"]["media_type"] == "image/jpeg", "jpeg media type")
        try:
            marker.transcribe_image(Path(td) / "w.txt")
            check(False, "unsupported extension accepted")
        except (ValueError, FileNotFoundError) as ex:
            check(isinstance(ex, ValueError), "unsupported extension -> ValueError")

    # ---- final_answer_facts on a real item ------------------------------------------------------------
    item = json.loads((ROOT / "content" / "clean" / "items" / "cr-area-between-curve-and-line-core.json").read_text())
    part = item["parts"][0]
    correct = next(r for r in item["gate_results"]["G4"]["responses"] if r["kind"] == "correct")
    f = marker.final_answer_facts(item, part, marker.transcribe(correct["work"])["lines"])
    check(len(f) == 1 and "appears" in f[0] and "125/6" in f[0], f"facts on correct script: {f}")
    f = marker.final_answer_facts(item, part, ["Area $=\\int_1^6(-x^2+7x-6)\\,dx$", "Area $\\approx 20.83$"])
    check(len(f) == 1 and "no exact expression" in f[0] and "20.83" in f[0], f"decimal script must not match exact: {f}")
    f = marker.final_answer_facts(item, part, ["$x^2-7x+6=0$", "$x = 1, 6$"])
    check("no expression equivalent" in f[0] and "last numeric value seen 6" in f[0], f"partial script: {f}")
    f = marker.final_answer_facts(item, part, ["Area $= \\frac{130}{3} - \\frac{45}{2}$"])
    check("appears" in f[0], f"equivalent unsimplified form: {f}")
    check(marker.final_answer_facts(item, {"answers": []}, ["x"]) == [], "no answers -> no facts")
    f = marker.final_answer_facts(item, {"answers": [{"name": "z", "expr": "1/0"}]}, ["$z = 3$"])
    check(len(f) == 1 and f[0].startswith("sympy:"), f"bad answer expr never raises: {f}")
    f = marker.final_answer_facts(item, part, ["$" * 5000, "9^9^9^9^9^9^9"])
    check(len(f) == 1 and f[0].startswith("sympy:"), f"hostile working never raises: {f}")
    # a rounded answer with an exact value: a longer correct decimal counts, a wrong one does not
    item2 = json.loads((ROOT / "content" / "clean" / "items" / "cr-pure-de-given-separable-004.json").read_text())
    pc = item2["parts"][2]
    check("appears" in marker.final_answer_facts(item2, pc, ["$y = 4.33$"])[0], "sf-3 literal")
    check("appears" in marker.final_answer_facts(item2, pc, ["$y = 4.3335$"])[0], "correct rounding of the exact value")
    check("no expression" in marker.final_answer_facts(item2, pc, ["$y = 4.35$"])[0], "wrong decimal")

    # ---- mark(): alignment, dependency override, summary -------------------------------------------
    scheme = [m["code"] for m in part["mark_scheme"]]  # M1 A1 M1 dM1 A1*
    check(marker.candidate_error_codes(item, [part])[:2] == ["area-between-wrong-subtraction", "region-part-missed"], "pitfall codes first")
    check("arithmetic-slip" in marker.candidate_error_codes(item, [part]), "generic codes present")
    check(marker.system_prompt() == (ROOT / "content" / "prompts" / "marker_system.md").read_text(), "prompt loaded verbatim")

    def reply(codes, **over):
        return {"parts": [{"part": None, "marks": [dict({"code": c, "evidence": f"L{i + 1}: line", "reason": "r", "convention": "M",
                                                          "error_code": None if c[-1] != "0" and not c.endswith("0*") else "arithmetic-slip",
                                                          "rewrite_to_earn": None if "0" not in c else "write it", "confidence": 0.9}, **over)
                                                    for i, c in enumerate(codes)]}]}

    # the model awards dM1 and A1* although the second M was withheld: both must be overridden
    fake_run.reply = reply(["M1", "A1", "M0", "dM1", "A1*"])
    out = marker.mark(item, None, correct["work"], facts=["f"], ref="selftest")
    vec = out["vectors"]["-"]
    check(vec == ["M1", "A1", "M0", "dM0", "A0*"], f"dependency override vector {vec}")
    check(out["overrides"] == 2 and out["decisions"][3]["overridden"] and out["decisions"][4]["overridden"], "override flags")
    check(out["decisions"][3]["reason"] == "dependency: M0 before it was not earned", f"override reason {out['decisions'][3]['reason']}")
    check(out["decisions"][3]["convention"] == "dependency", "override convention")
    check(all(d["rewrite_to_earn"] for d in out["decisions"] if not d["awarded"]), "every withheld mark has a rewrite")
    check(all(d["rewrite_to_earn"] is None for d in out["decisions"] if d["awarded"]), "awarded marks carry no rewrite")
    check(out["summary"]["-"]["earned"] == 2 and out["summary"]["-"]["lost_by_family"] == {"method": 2, "accuracy": 1}, f"summary {out['summary']}")
    check(out["earned"] == 2 and out["total"] == 5 and out["cost_usd"] == 0.02 and out["model"] == marker.DEFAULT_MODEL, "totals")
    check(seen["step"] == "marker-v2" and seen["system"] == marker.system_prompt() and seen["schema"] is marker.MARK_SCHEMA, "mark request")
    check("# Sympy facts\n- f" in seen["content"][0]["text"] and "L1:" in seen["content"][0]["text"], "user message carries facts and lines")
    # an ft mark survives an earlier loss; a mark the model spells oddly is still read; a missing mark is withheld
    fake_run.reply = reply(["M0", "A1 FT"])
    item_ft = {"id": "t", "parts": [{"label": "a", "marks": 2, "text": "t", "mark_scheme": [{"code": "M1", "for": "m"}, {"code": "A1ft", "for": "a"}],
                                     "skills": ["s1"], "answers": []}], "pitfalls": []}
    out = marker.mark(item_ft, "a", "x", facts=[])
    check(out["vectors"]["a"] == ["M0", "A1ft"] and out["overrides"] == 0, f"ft survives {out['vectors']}")
    fake_run.reply = reply(["M1"])
    out = marker.mark(item_ft, "a", "x", facts=[])
    check(out["vectors"]["a"] == ["M1", "A0ft"] and out["decisions"][1].get("missing") and out["decisions"][1]["confidence"] == 0.0,
          f"missing mark -> withheld, confidence 0 {out['vectors']}")
    # an error code outside the candidate list is dropped
    fake_run.reply = reply(["M0", "A0ft"], error_code="made-up-code")
    out = marker.mark(item_ft, "a", "x", facts=[])
    check(all(d["error_code"] is None for d in out["decisions"]), "unknown error code dropped")
    try:
        marker.mark(item_ft, "z", "x", facts=[])
        check(False, "unknown part accepted")
    except ValueError:
        pass

    # ---- to_decisions -> events.record ------------------------------------------------------------------
    fake_run.reply = reply(["M1", "A1", "M0", "dM1", "A1*"])
    out = marker.mark(item, None, correct["work"], facts=["f"])
    rows = marker.to_decisions(out, part)
    check(len(rows) == 5 and rows[0] == {"code": "M1", "kind": "METHOD", "family": "method", "worth": 1, "awarded": True, "error_code": None,
                                         "skill": "area-between-curve-and-line", "evidence": "L1: line", "reason": "r"}, f"to_decisions {rows[0]}")
    check(rows[2]["awarded"] is False and rows[2]["error_code"] == "arithmetic-slip" and rows[3]["awarded"] is False, "withheld rows")
    check([r["code"] for r in rows] == scheme, "rows carry the scheme codes")
    with tempfile.TemporaryDirectory() as td:
        conn = events.connect(Path(td) / "e.db")
        events.record("u", "mark-my-working", item["id"], None, rows, model=out["model"], cost_usd=out["cost_usd"], conn=conn)
        prof = events.leakage_profile("u", conn=conn)
        check(prof["by_family"] == {"method": {"available": 3, "lost": 2}, "accuracy": {"available": 2, "lost": 1}}, f"profile {prof['by_family']}")
        check(prof["by_error_code"] == {"arithmetic-slip": 3}, f"profile codes (chain losses carry the root cause) {prof['by_error_code']}")
        conn.close()
finally:
    claude_oneshot.run = real_run

print(f"marker self-test: {'PASS' if not fails else 'FAIL'}")
for f in fails:
    print("   ", f)
sys.exit(1 if fails else 0)
