#!/usr/bin/env python3
"""Self-test for the deterministic gates (scripts/clean/gates.py). No model calls.

    .venv/bin/python -m eval.gates_selftest

1. Originals: hand-written items (eval/fixtures/original_items.json, written from scratch) must pass G1
   and G7.
2. G1 planted faults: each broken copy of an original must fail G1.
3. G7 copies: N random real questions from the pearson-private pack, turned into items, must fail G7;
   so must "variants" (the same text with every number changed). The Pearson text stays inside this
   process: only ids and pass/fail counts are printed.
"""
import copy
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import gates  # noqa: E402
from chatbot import pack as packs  # noqa: E402

FIXTURES = ROOT / "eval" / "fixtures" / "original_items.json"
N_COPIES = 40


def planted(item: dict) -> list[tuple[str, dict]]:
    out = []
    x = copy.deepcopy(item); x["parts"][0]["marks"] += 1; out.append(("marks don't add up", x))
    x = copy.deepcopy(item); x["parts"][0]["mark_scheme"][0]["code"] = "A1"; out.append(("A before any M", x))
    x = copy.deepcopy(item); x["parts"][0]["mark_scheme"].insert(0, {"code": "dM1", "for": "x"}); x["parts"][0]["marks"] += 1
    out.append(("dM with no M", x))
    x = copy.deepcopy(item); x["parts"][-1]["mark_scheme"][-1]["code"] = "A1ft"; x["parts"][-1]["mark_scheme"][-1].pop("ft_of", None)
    out.append(("ft without ft_of", x))
    x = copy.deepcopy(item); x["parts"] = list(reversed(x["parts"])); out.append(("labels out of order", x))
    x = copy.deepcopy(item); x["parts"][0]["mark_scheme"][0]["code"] = "Q1"; out.append(("invalid code", x))
    return out


def pearson_items(n: int, seed: int = 5) -> list[dict]:
    conn = sqlite3.connect(f"file:{packs.load('pearson-private').db}?mode=ro", uri=True)
    ids = [r[0] for r in conn.execute("SELECT id FROM questions ORDER BY id")]
    out = []
    for qid in random.Random(seed).sample(ids, n):
        stem = conn.execute("SELECT stem FROM questions WHERE id = ?", (qid,)).fetchone()[0]
        parts = [{"label": lab, "marks": m, "text": t, "mark_scheme": [{"code": "B1", "for": ms}]}
                 for lab, m, t, ms in conn.execute("SELECT label, marks, text, mark_scheme FROM question_parts "
                                                    "WHERE question_id = ? ORDER BY part_index", (qid,))]
        out.append({"id": qid, "stem": stem, "parts": parts})
    return out


def change_numbers(item: dict) -> dict:
    x = copy.deepcopy(item)
    bump = lambda s: re.sub(r"\d+", lambda m: str(int(m.group(0)) + 3), s or "")
    x["stem"] = bump(x.get("stem"))
    for p in x["parts"]:
        p["text"] = bump(p["text"])
        for mk in p["mark_scheme"]:
            mk["for"] = bump(mk["for"])
    return x


def main() -> None:
    originals = json.loads(FIXTURES.read_text())["items"]
    ok = True
    for it in originals:
        res = gates.run(it)
        good = res["G1"]["pass"] and res["G7"]["pass"]
        ok &= good
        print(f"{'OK  ' if good else 'FAIL'} original {it['id']}: G1 {res['G1']['pass']} {res['G1']['errors'][:2]} | "
              f"G7 {res['G7']['pass']} {res['G7']['reasons']} flags {res['G7']['flags']} "
              f"cos {res['G7']['max_cosine']} jac {res['G7']['max_jaccard']}")
    for name, bad in planted(originals[0]):
        caught = not gates.g1_structure(bad)["pass"]
        ok &= caught
        print(f"{'OK  ' if caught else 'FAIL'} G1 catches: {name}")
    copies = pearson_items(N_COPIES)
    for label, items in (("verbatim copies", copies), ("number-changed variants", [change_numbers(i) for i in copies])):
        res = [gates.g7_novelty(i) for i in items]
        caught = sum(not r["pass"] for r in res)
        by = {k: sum(any(k in s for s in r["reasons"]) for r in res) for k in ("8-gram", "Jaccard", "cosine", "numbers")}
        ok &= caught == len(items)
        print(f"{'OK  ' if caught == len(items) else 'FAIL'} G7 rejects {label}: {caught}/{len(items)} (by rule: {by})"
              + ("" if caught == len(items) else f" missed: {[i['id'] for i, r in zip(items, res) if r['pass']]}"))
    print("ALL PASS" if ok else "SOME CHECKS FAILED")


if __name__ == "__main__":
    main()
