#!/usr/bin/env python3
"""The tutor on a commercial pack, end to end with no model call, on a throwaway pack built from the
three original fixture items (eval/fixtures/original_items.json).

    .venv/bin/python -m eval.clean_pack_smoke

Builds content/_selftest/ (pack.json, pack.db via scripts/clean/build_pack.load_item, embeddings via
scripts/build_embeddings.py), then with CONTENT_PACK=_selftest checks that the tutor's requests carry our
mark scheme and pitfalls and no examiner / Pearson wording, that replies are validated against our mark
scheme and pitfalls table, and that the practice finder and the offline / dry-run chat work.
content/_selftest/ is deleted at the end. In memory only, the fixtures get an "accept" review and passing
G1-G8 results (the licence gate needs both), and one pitfall is marked says_common to test that wording.
"""
import copy
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = "_selftest"
PACK_DIR = ROOT / "content" / PACK
FIXTURES = ROOT / "eval" / "fixtures" / "original_items.json"
os.environ["CONTENT_PACK"] = PACK  # before anything imports chatbot (pack.current() is cached)
sys.path.insert(0, str(ROOT))
BANNED = re.compile(r"examiner|official mark scheme|pearson", re.I)
FAKE_GATES = {f"G{i}": {"pass": True, "note": "faked by eval/clean_pack_smoke.py"} for i in range(1, 9)}
COMMON = ("fixture-stationary-cubic", 1)  # (item, pitfall index) marked says_common in memory

failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global failed
    failed += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f"\n     {detail}" if detail and not ok else ""))


def build() -> list[dict]:
    """content/_selftest/: the fixtures loaded the way scripts/clean/build_pack.py loads reviewed items."""
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    (PACK_DIR / "pack.json").write_text(json.dumps(
        {"db": "pack.db", "embeddings_dir": ".", "tags": "../clean/tags.json", "commercial": True}, indent=2) + "\n")
    sys.path.insert(0, str(ROOT / "scripts" / "clean"))
    import build_pack
    from chatbot import pack
    items = copy.deepcopy(json.loads(FIXTURES.read_text())["items"])
    for item in items:
        item["review"] = {"by": "eval/clean_pack_smoke.py", "at": "selftest", "decision": "accept", "notes": "self-test"}
        item["gate_results"] = FAKE_GATES
    next(i for i in items if i["id"] == COMMON[0])["pitfalls"][COMMON[1]]["says_common"] = True
    p = pack.load(PACK)
    conn = sqlite3.connect(p.db)
    pack.create_schema(conn)
    type_ids, skill_ids = build_pack.build_db.load_vocabulary(conn, p.tags)
    for item in items:
        build_pack.load_item(conn, item, type_ids, skill_ids)
    conn.commit()
    conn.close()
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_embeddings.py")], capture_output=True, text=True,
                         cwd=ROOT, env=dict(os.environ, CONTENT_PACK=PACK), timeout=600)
    print(out.stdout.strip() or out.stderr.strip()[-500:])
    return items


def run(items: list[dict]) -> None:
    from eval import licence_gate
    licence_gate()  # the fixtures (with faked gates) must pass the commercial licence gate
    from chatbot import controller, pack, recommend, tutor, validate
    check("pack is the commercial self-test pack", pack.current().name == PACK and pack.current().commercial)

    sent = []
    build_request = tutor.build_request
    tutor.build_request = lambda *a, **k: sent.append(build_request(*a, **k)) or sent[-1]

    for item in items:
        qid = item["id"]
        r = tutor.explain(question_id=qid, dry_run=True)
        request = json.dumps(r.request, ensure_ascii=False)
        context = r.request["messages"][-1]["content"][-1]["text"]
        bad = BANNED.findall(request)
        check(f"{qid}: request has no examiner / official mark scheme / Pearson wording", not bad, f"found {bad}")
        missing = [f"{m['code']} {m['for']}" for p in item["parts"] for m in p["mark_scheme"]
                   if f"{m['code']} {m['for']}" not in context]
        check(f"{qid}: request carries our mark scheme", not missing and "Our mark scheme:" in context, f"missing {missing}")
        missing = [pf["text"] for pf in item.get("pitfalls", []) if pf["text"] not in context]
        check(f"{qid}: request carries its pitfalls ({len(item.get('pitfalls', []))})", not missing, f"missing {missing}")
        check(f"{qid}: bundle has no paper links, examiner notes or performance",
              r.bundle["links"] == {} and "performance" not in r.bundle
              and not any("examiner_notes" in p for p in r.bundle["parts"]))
        check(f"{qid}: schema asks for pitfalls by pitfall_id",
              "pitfalls" in r.request["output_config"]["format"]["schema"]["properties"])
    common_id, other_id = f"{COMMON[0]}_p{COMMON[1] + 1}", f"{COMMON[0]}_p1"  # (build_pack ids: <item>_p<n>)
    context = tutor.explain(question_id=COMMON[0], dry_run=True).request["messages"][-1]["content"][-1]["text"]
    check("a says_common pitfall is tagged common, the others watch out",
          f"[{common_id}] (common" in context and f"[{other_id}] (watch out" in context)

    r = tutor.explain(text="The curve y = x^3 - 12x + 5. Find the coordinates of the stationary points and "
                           "determine their nature. (6 marks)", dry_run=True)
    request = json.dumps(r.request, ensure_ascii=False)
    check("bring-your-own question: estimated marks, no official wording",
          not BANNED.findall(request) and "'likely ...'" in request and "not an exam board's mark scheme" in request,
          f"banned {BANNED.findall(request)}")
    tutor.explain_topic("how do I find stationary points?", dry_run=True)
    tutor.follow_up([], "why do we set dy/dx to zero?", dry_run=True, question_id=items[0]["id"])
    check("topic question and follow-up requests are clean", not BANNED.findall(json.dumps(sent[-2:])),
          f"banned {BANNED.findall(json.dumps(sent[-2:]))}")

    found = recommend.find_practice("a question on stationary points")
    ids = [it["question_id"] for it in found["items"]]
    check("find_practice('a question on stationary points') returns the fixture",
          ids[:1] == ["fixture-stationary-cubic"], f"got {ids}")

    for item in items:
        res = tutor.explain_offline(item["id"])
        check(f"{item['id']}: offline reply passes our mark-scheme checks", not res.warnings, f"warnings {res.warnings}")
    qid = "fixture-stationary-cubic"
    good = [{"pitfall_id": f"{qid}_p1", "part_label": "b", "comment": "Watch out for this."}]
    reply = {"intro": "", "follow_up": "", "pitfalls": good + [{"pitfall_id": "no-such-item_p9", "part_label": "b", "comment": ""}],
             "parts": [{"label": "a", "marks": 2, "how_to_start": "", "final_answer": "", "final_answer_sympy": "",
                        "steps": [{"text": "", "marks_awarded": ["M1"]}, {"text": "", "marks_awarded": ["B1"]}]},
                       {"label": "b", "marks": 4, "how_to_start": "", "final_answer": "", "final_answer_sympy": "",
                        "steps": [{"text": "", "marks_awarded": ["M1", "A1"]}]}]}
    cleaned, warnings = validate.validate(reply, qid, tutor._allowed_notes(tutor.question_bundle(qid)))
    want = ["mark codes ['B1'] are not in its mark scheme", "steps award 2 marks, the part is worth 4",
            "parts missing from the reply: ['c']", "dropped pitfall with unknown pitfall_id no-such-item_p9"]
    check("validation: wrong codes, totals and unknown pitfall ids are caught",
          all(any(w in x for x in warnings) for w in want), f"warnings {warnings}")
    check("validation: a cited pitfall gets our text attached",
          [p["pitfall_id"] for p in cleaned["pitfalls"]] == [f"{qid}_p1"]
          and cleaned["pitfalls"][0]["quote"] == items[0]["pitfalls"][0]["text"])

    for mode, script, opened in (("offline", ["a question on stationary points", "1", "show all", "hardest", "hardest b"], 1),
                                 ("dry-run", ["a question on stationary points", "1", "a question on a pulley", "1"], 2)):
        conv, shown, error = controller.Conversation(mode=mode), [], None
        try:
            for msg in script:
                shown += conv.handle(msg)
        except Exception as e:  # noqa: BLE001  (a crash is a failed check, not a traceback)
            error = f"{type(e).__name__}: {e}"
        text = json.dumps(shown, ensure_ascii=False)
        questions = [m for m in shown if m["type"] == "question"]
        check(f"{mode} chat: opens questions with no paper link, no examiner / official wording",
              error is None and len(questions) == opened and not any("link" in m for m in questions) and not BANNED.findall(text),
              error or f"questions {len(questions)}, banned {BANNED.findall(text)}")
        if mode == "offline":
            intros = [i for m in shown if m["type"] == "part_intro" for i in m["insights"]]
            check("offline chat: pitfalls shown as ours ('Watch out' / 'A common mistake ...')",
                  bool(intros) and all(i.get("who") in ("Watch out", "A common mistake on questions like this")
                                       for i in intros))
            check("offline chat: 'hardest' with no part on a multi-part question gives a practice list",
                  shown[-2]["type"] == "list" and shown[-1]["type"] == "list")

    try:  # the known dry-run bug: opening a multi-part question with no part chosen (recommend.ladder KeyError)
        shown, error = controller.Conversation(mode="dry-run")._open("fixture-stationary-cubic", None), None
    except KeyError as e:
        shown, error = [], f"KeyError: {e}"
    check("dry-run chat: opening a multi-part question with no part chosen", error is None and shown[-1]["type"] == "list",
          error or "")
    out = subprocess.run([sys.executable, "-m", "chatbot.chat", "--offline"], cwd=ROOT, capture_output=True, text=True,
                         input="a question on stationary points\n1\nshow all\nquit\n", timeout=600,
                         env=dict(os.environ, CONTENT_PACK=PACK)).stdout
    check("terminal chat (--offline): no paper link, pitfalls labelled as ours",
          "══ Question fixture-stationary-cubic (8 marks) ══\n" in out and "Watch out" in out
          and not BANNED.findall(out) and "(paper:" not in out, f"banned {BANNED.findall(out)}")


def main() -> int:
    if PACK_DIR.exists():
        shutil.rmtree(PACK_DIR)
    try:
        run(build())
    finally:
        shutil.rmtree(PACK_DIR, ignore_errors=True)
    print(f"\n{'all checks passed' if not failed else f'{failed} check(s) failed'}; removed {PACK_DIR.relative_to(ROOT)}/")
    return 1 if failed else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)  # onnxruntime can abort during interpreter teardown
