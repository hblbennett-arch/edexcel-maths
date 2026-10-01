"""Self-test for chatbot/examiner.py ("Be the examiner"): the exercises built from the G4 scripts, the deterministic
reveal, the event recording and the sequencing.

    .venv/bin/python -m eval.examiner_selftest

No model calls, no network. Reads only content/clean/items and content/boards.
"""
import collections
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, examiner, marks  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


items = examiner.load_items()
exs = examiner.exercises(items)
kinds = collections.Counter(e["kind"] for e in exs)
n_items = len({e["item_id"] for e in exs})
check(len(exs) >= 60, f"only {len(exs)} exercises (need >= 60)")
check(n_items >= 20, f"exercises span only {n_items} items (need >= 20)")
check(set(kinds) >= {"correct", "pitfall", "partial"}, f"kinds {dict(kinds)}")
check(len({e["key"] for e in exs}) == len(exs), "exercise keys not unique")

# every exercise: reference aligned to scheme lines, parseable codes, work text present, no giveaways leak
for e in exs:
    check(e["work"].strip() and e["question"].strip(), f"{e['key']}: empty work or question")
    for p in e["parts"]:
        check(len(p["reference"]) == len(p["lines"]) > 0, f"{e['key']} part {p['label']}: reference/lines length")
        check(all(marks.try_parse(ln["code"]) for ln in p["lines"]), f"{e['key']} part {p['label']}: bad code")
        check(all(ln["for"] for ln in p["lines"]), f"{e['key']} part {p['label']}: empty 'for'")
    if e["kind"] in ("correct", "alternative"):
        check(all(all(p["reference"]) for p in e["parts"]), f"{e['key']}: {e['kind']} script loses marks")
    if e["kind"] == "pitfall":
        check(e["error_code"], f"{e['key']}: pitfall without error code")
    pv = examiner.public_view(e)
    check(all("reference" not in p for p in pv["parts"]) and not {"kind", "pitfalls", "error_code"} & set(pv),
          f"{e['key']}: public view leaks")

# reveal: all-correct judgements score 100 %, all-wrong 0 %
for e in exs:
    right = [list(p["reference"]) for p in e["parts"]]
    wrong = [[not x for x in p["reference"]] for p in e["parts"]]
    fb = examiner.reveal(e, right)
    check(fb["score"]["rate"] == 1.0 and fb["lesson"] is None, f"{e['key']}: all-correct reveal {fb['score']}")
    check(all(r["correct"] for p in fb["parts"] for r in p["rows"]), f"{e['key']}: all-correct rows")
    fb2 = examiner.reveal(e, wrong)
    check(fb2["score"]["rate"] == 0.0 and fb2["lesson"] is not None, f"{e['key']}: all-wrong reveal {fb2['score']}")
    check(fb2["score"]["total"] == sum(len(p["lines"]) for p in e["parts"]), f"{e['key']}: score total")
    check(fb2["script_score"]["total"] == e["total_marks"], f"{e['key']}: script total {fb2['script_score']} vs {e['total_marks']}")
    check(all(r["explanation"] for p in fb2["parts"] for r in p["rows"]), f"{e['key']}: empty explanation")
try:
    examiner.reveal(exs[0], [[True]])
    check(len(exs[0]["parts"][0]["lines"]) == 1, "bad shape accepted")
except ValueError:
    pass

# a pitfall exercise's reveal carries the pitfall text once, at the first lost mark
pit = next(e for e in exs if e["kind"] == "pitfall" and e["pitfalls"] and not all(all(p["reference"]) for p in e["parts"]))
fb = examiner.reveal(pit, [[True] * len(p["lines"]) for p in pit["parts"]])
rows = [r for p in fb["parts"] for r in p["rows"]]
with_pf = [r for r in rows if r.get("pitfall")]
check(len(with_pf) == 1, f"{pit['key']}: pitfall attached {len(with_pf)} times")
check(with_pf and with_pf[0]["pitfall"] in {pf["text"] for pf in pit["pitfalls"]}, f"{pit['key']}: pitfall text")
check(with_pf and with_pf[0] is next(r for r in rows if not r["reference"]), f"{pit['key']}: pitfall not at first lost mark")
n_pit_with_text = sum(1 for e in exs if e["kind"] == "pitfall" and e["pitfalls"])
check(n_pit_with_text == kinds["pitfall"], f"{kinds['pitfall'] - n_pit_with_text} pitfall scripts have no matching pitfall text")

# an over-awarded implied loss is explained by the chain
imp = next((e for e in exs for p in e["parts"]
            if marks.implied_losses([ln["code"] for ln in p["lines"]], p["reference"])), None)
check(imp is not None, "no exercise with an implied loss")
if imp:
    fb = examiner.reveal(imp, [[True] * len(p["lines"]) for p in imp["parts"]])
    check(any("unavailable because" in r["explanation"] for p in fb["parts"] for r in p["rows"]), "implied loss not explained")
    check(fb["lesson"] and fb["lesson"]["key"] in marks.profile().conventions, f"lesson key {fb['lesson']}")
# a withheld earned mark quotes the convention
cor = next(e for e in exs if e["kind"] == "correct")
fb = examiner.reveal(cor, [[False] * len(p["lines"]) for p in cor["parts"]])
check(all("Earned" in r["explanation"] and len(r["explanation"]) > 40 for p in fb["parts"] for r in p["rows"]), "withheld explanation")

# decisions + events: flipping one judgement gives (n-1)/n accuracy
multi = next((e for e in exs if len(e["parts"]) > 1), exs[0])
judg = [list(p["reference"]) for p in multi["parts"]]
judg[0][0] = not judg[0][0]
n = sum(len(p["lines"]) for p in multi["parts"])
decs = examiner.to_decisions(multi, judg)
check(len(decs) == n and all(d["awarded"] == r for d, r in zip(decs, [r for p in multi["parts"] for r in p["reference"]])), "decisions")
check(all(d["skill"] for d in decs) and all("code" in d and "family" in d for d in decs), "decision fields")
with tempfile.TemporaryDirectory() as td:
    conn = events.connect(Path(td) / "events.db")
    ids = examiner.record("u-test", multi, judg, conn=conn)
    check(len(ids) == len(multi["parts"]), "one event per part")
    prof = events.leakage_profile("u-test", conn=conn)
    check(prof["examiner_accuracy"] == {"judged": n, "correct": n - 1, "rate": round((n - 1) / n, 3)},
          f"examiner accuracy {prof['examiner_accuracy']} (expected {n - 1}/{n})")
    check(prof["by_family"] == {} and prof["total_lost"] == 0, "examiner events must not count as lost marks")
    conn.close()

# pick_next never repeats until everything is done, and varies kinds and items
done, seen_kinds, first_items = set(), [], []
for i in range(len(exs) + 1):
    nxt = examiner.pick_next(exs, done)
    if i == len(exs):
        check(nxt is None, "pick_next after all done should be None")
        break
    check(nxt is not None and nxt["key"] not in done, f"pick_next repeated or stopped early at {i}")
    if nxt is None:
        break
    check(examiner.pick_next(exs, set(done)) is nxt, "pick_next not deterministic")
    done.add(nxt["key"])
    seen_kinds.append(nxt["kind"])
    if i < 10:
        first_items.append(nxt["item_id"])
check(len(set(seen_kinds[:6])) >= 3, f"first six kinds not varied: {seen_kinds[:6]}")
check(len(set(first_items)) == len(first_items), f"items repeated within the first ten: {first_items}")
check(examiner.pick_next(exs, set(), prefer_kind="correct")["kind"] == "correct", "prefer_kind")

print(f"examiner self-test: {'PASS' if not fails else 'FAIL'} ({len(exs)} exercises over {n_items} items; "
      + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ")")
for f in fails[:40]:
    print("   ", f)
sys.exit(1 if fails else 0)
