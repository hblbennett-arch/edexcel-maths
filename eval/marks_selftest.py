"""Self-test for chatbot/marks.py (the mark-code ontology) and chatbot/events.py (the marking-event store).

    .venv/bin/python -m eval.marks_selftest

No model calls, no network. Also checks that every mark code in every clean item parses, and that the
board profile's convention texts contain no board name (they must be our own words).
"""
import glob
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, marks  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


b = marks.profile()
check(b.id == "edexcel-9ma0", "default profile")

# parsing
m = marks.parse("dM1")
check(m.kind == "DEPENDENT_METHOD" and m.awarded and m.worth == 1 and m.depth == 1, "dM1")
check(marks.parse("A0ft").awarded is False and marks.parse("A0ft").ft, "A0ft")
check(marks.parse("A1*").show_that, "A1*")
check(marks.parse("B1").family == "independent", "B1 family")
check(marks.parse("ddM1").depth == 2, "ddM1 depth")
check(marks.parse("DM1").kind == "DEPENDENT_METHOD", "DM1 tolerated")
check(marks.parse("M1FT").ft, "M1FT tolerated")
check(marks.parse("A1 cso").cso, "A1 cso tolerated")
check(marks.try_parse("Q7") is None, "junk -> None")
for c in ("M1", "A1", "B1", "dM1", "ddM1", "A1ft", "A1*", "M0", "A0ft", "dB1"):
    check(marks.render(marks.parse(c)) == c, f"round trip {c}")
check(marks.withheld("A1ft") == "A0ft" and marks.withheld("dM1") == "dM0", "withheld")

# chains
ch = marks.chain(["M1", "A1", "M1", "dM1", "A1*"])
check([l["depends_on"] for l in ch] == [[], [0], [], [2], [3]], f"chain {ch}")
# losing the second M1 implies losing the dM1 and the final A1*, not the first A1
check(marks.implied_losses(["M1", "A1", "M1", "dM1", "A1*"], [True, True, False, False, False]) == [3, 4], "implied")
# an ft mark survives an earlier loss
check(marks.implied_losses(["M1", "A1", "A1ft"], [True, False, True]) == [], "ft survives")
vs = marks.vector_summary(["M1", "A1", "M1", "dM1", "A1*"], ["M1", "A1", "M0", "dM0", "A0"])
check(vs["earned"] == 2 and vs["lost_by_family"] == {"method": 2, "accuracy": 1}, f"summary {vs}")

# conventions in our words: no board names, and every notation letter explained
text = json.dumps(b.conventions)
check(not re.search(r"Pearson|Edexcel|AQA|OCR", text), "convention texts name a board")
for letter in ("M", "A", "B", "dM", "ddM", "ft", "cso", "cao", "awrt", "oe", "isw", "show_that", "dependency", "bald_answer"):
    check(all(b.convention(letter).get(k) for k in ("name", "short", "explain", "write_to_earn")), f"convention {letter}")
check("dependent" in marks.explain("dM1").lower(), "explain dM1")
check("follow" in marks.explain("A1ft").lower(), "explain A1ft mentions follow-through")

# every code in every clean item parses
n = 0
for f in glob.glob(str(ROOT / "content" / "clean" / "items" / "*.json")):
    item = json.loads(Path(f).read_text())
    for p in item["parts"]:
        for mk in p["mark_scheme"]:
            check(marks.try_parse(mk["code"]) is not None, f"{item['id']}: code {mk['code']!r}")
            n += 1
        for alt in p.get("alternatives") or []:
            for mk in alt.get("marks", []):
                check(marks.try_parse(mk["code"]) is not None, f"{item['id']}: alt code {mk['code']!r}")
check(n > 0, "no item codes found")

# events store
with tempfile.TemporaryDirectory() as td:
    conn = events.connect(Path(td) / "events.db")
    dec = [dict(marks.parse(c).as_dict(), user_judgement=uj, error_code=ec, skill="integrate-powers-of-x")
           for c, uj, ec in (("M1", True, None), ("A0", True, "arithmetic-slip"), ("dM1", False, None))]
    events.record("u1", "be-the-examiner", "cr-x", None, dec, script_id="r2", conn=conn)
    dec2 = [dict(marks.parse(c).as_dict(), error_code=ec, skill="integrate-powers-of-x")
            for c, ec in (("M1", None), ("A0", "premature-rounding"), ("dM1", None), ("A0", "premature-rounding"))]
    events.record("u1", "mark-my-working", "cr-y", "a", dec2, model="test", cost_usd=0.01, transcript_confirmed=True, conn=conn)
    prof = events.leakage_profile("u1", conn=conn)
    check(prof["examiner_accuracy"] == {"judged": 3, "correct": 1, "rate": 0.333}, f"examiner accuracy {prof['examiner_accuracy']}")
    check(prof["by_family"] == {"method": {"available": 2, "lost": 0}, "accuracy": {"available": 2, "lost": 2}}, f"by_family {prof['by_family']}")
    check(prof["by_error_code"] == {"premature-rounding": 2}, f"by_error_code {prof['by_error_code']}")
    check(prof["total_lost"] == 2, "total lost")
    conn.close()

print(f"marks/events self-test: {'PASS' if not fails else 'FAIL'} ({n} item codes parsed)")
for f in fails:
    print("   ", f)
sys.exit(1 if fails else 0)
