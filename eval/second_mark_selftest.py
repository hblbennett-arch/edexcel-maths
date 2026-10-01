"""Self-test for the blind second-marking tool (no model calls, no network).

    .venv/bin/python eval/second_mark_selftest.py

Checks: the queue has >= 100 scripts and is ordered (v2-vs-reference disagreements, then pitfalls, then the rest);
the blind payload for every queued script carries no reference or marker-v2 fields; one fake submission written
through the server's own function to a temp jsonl comes back with a comparison; the report runs on that file.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
sys.path.insert(0, str(ROOT / "eval"))  # the report module lives beside this test
import second_mark_server as sm  # noqa: E402
import second_marking_report as rep  # noqa: E402

FAILS = []


def check(cond: bool, msg: str) -> None:
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def keys_in(obj, found: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.add(k)
            keys_in(v, found)
    elif isinstance(obj, list):
        for v in obj:
            keys_in(v, found)


def main() -> int:
    queue = sm.build_queue()
    check(len(queue) >= 100, f"queue has {len(queue)} scripts (>= 100)")
    prios = [r["priority"] for r in queue]
    check(prios == sorted(prios), "queue ordered: v2/reference disagreements, then pitfalls, then the rest")
    n0 = sum(p == 0 for p in prios)
    n1 = sum(p == 1 for p in prios)
    print(f"     {n0} disagreement scripts first, then {n1} pitfall scripts, then {len(queue) - n0 - n1} others; "
          f"{len({r['item_id'] for r in queue})} items")
    check(all(r["v2_disagrees_with_reference"] for r in queue if r["priority"] == 0), "priority-0 rows all disagree")
    check(all(r["kind"] == "pitfall" for r in queue if r["priority"] == 1), "priority-1 rows are pitfall scripts")
    same_queue = sm.build_queue()
    check([(r["item_id"], r["script_id"]) for r in queue] == [(r["item_id"], r["script_id"]) for r in same_queue],
          "queue order is deterministic (seeded)")
    neighbours_same = sum(1 for a, b in zip(queue, queue[1:]) if a["item_id"] == b["item_id"])
    print(f"     {neighbours_same} adjacent pairs from the same item")

    # Blind rows and payloads: no leaked keys
    blind_rows = [sm.blind_row(r, set()) for r in queue]
    found: set = set()
    keys_in(blind_rows, found)
    check(not (found & sm.FORBIDDEN_BLIND_KEYS), f"queue rows carry no vector fields (keys: {sorted(found)})")
    leaked = set()
    for r in queue:
        p = sm.blind_payload(r["item_id"], r["script_id"])
        f: set = set()
        keys_in(p, f)
        leaked |= f & sm.FORBIDDEN_BLIND_KEYS
        check_text = json.dumps(p)
        if '"awarded"' in check_text or '"vectors"' in check_text:
            leaked.add("text")
    check(not leaked, f"blind payloads for all {len(queue)} scripts carry no reference/v2 fields "
                      f"(leaked: {sorted(leaked) or 'none'})")
    p0 = sm.blind_payload(queue[0]["item_id"], queue[0]["script_id"])
    check(bool(p0.get("work")) and all(pt["scheme"] for pt in p0["parts"]), "payload has the script and scheme lines")

    # Fake submission through the server's own function, to a temp jsonl
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "second_marking.jsonl"
        item = sm.load_item(queue[0]["item_id"])
        human = {}
        for ln in sm.scheme_lines(item):
            human.setdefault(ln["part"], []).append(ln["position"] % 2 == 0)  # alternate award/withhold
        res = sm.record_submission({"item_id": queue[0]["item_id"], "script_id": queue[0]["script_id"],
                                    "human": human, "seconds": 42.5}, out=out, by="selftest")
        lines = [json.loads(l) for l in out.read_text().splitlines()]
        check(len(lines) == len(human), f"one jsonl line per part written ({len(lines)})")
        check(all(set(l) == {"at", "by", "item_id", "script_id", "part", "human", "seconds"} for l in lines),
              "jsonl lines have exactly {at, by, item_id, script_id, part, human, seconds}")
        check(res["v2_available"] and len(res["marks"]) == sum(len(v) for v in human.values()),
              f"comparison returned for {len(res['marks'])} marks with v2 vector")
        check(all(m["human"] is not None for m in res["marks"]), "comparison carries the human decision per mark")
        check(res["progress"]["scripts"] == 1, "progress counts the submission")
        try:
            sm.record_submission({"item_id": queue[0]["item_id"], "script_id": queue[0]["script_id"],
                                  "human": {"zz": [True]}}, out=out)
            check(False, "bad part set is refused")
        except ValueError:
            check(True, "bad part set is refused")
        text = rep.report(out)
        check("human vs marker v2" in text and "CAVEAT" in text, "report runs on the temp log")
        print("----- report on the fake submission -----")
        print(text)
        print("-----------------------------------------")
    print(f"\n{'PASS' if not FAILS else 'FAIL'}: {len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
