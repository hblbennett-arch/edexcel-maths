#!/usr/bin/env python3
"""Clean-bank gate report: pass rate per gate, rejection reasons, cost per accepted item, review status.

    .venv/bin/python -m eval.clean_gates_report [content/clean/items/*.json]

Reads the gate_results stored in each item (scripts/clean/generate.py, gate_solve.py, gate_marking.py,
gate_tags.py) and the llm cost log. "Gate-ready" means G1-G8 all passed, so the item can go to human review
(G9). Review minutes are recorded by the review UI in review.minutes (when it exists).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")


def reason_key(text: str) -> str:
    """Group similar errors: drop part labels, numbers and quoted details."""
    t = re.sub(r"part [\w()-]+:?", "", text)
    t = re.sub(r"'[^']*'|\"[^\"]*\"|\{.*\}|\[.*\]", "…", t)
    t = re.sub(r"\d+(\.\d+)?", "N", t)
    return t.strip()[:90]


def main() -> None:
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "clean" / "items").glob("*.json"))
    items = [json.loads(f.read_text()) for f in files]
    if not items:
        print("no items")
        return
    print(f"items: {len(items)}  ({dict(Counter(i.get('kind', '?') for i in items))})")
    ran = {g: [i for i in items if g in (i.get("gate_results") or {})] for g in GATES}
    print("gate  ran  passed")
    reasons: dict[str, Counter] = {g: Counter() for g in GATES}
    for g in GATES:
        rs = [i["gate_results"][g] for i in ran[g]]
        ok = sum(r.get("pass") for r in rs)
        print(f"{g:4s} {len(rs):4d}  {ok:4d} ({ok / len(rs):.0%})" if rs else f"{g:4s}    0     -")
        for r in rs:
            for e in (r.get("errors") or []) + (r.get("reasons") or []):
                reasons[g][reason_key(e)] += 1
    ready = [i for i in items if all((i.get("gate_results") or {}).get(g, {}).get("pass") for g in GATES)]
    gen_cost = sum((i.get("generation") or {}).get("cost_usd") or 0 for i in items)
    gate_cost = sum((i.get("gate_results") or {}).get(g, {}).get("cost_usd") or 0 for i in items for g in ("G3", "G4", "G6"))
    attempts = Counter((i.get("generation") or {}).get("attempts") for i in items)
    print(f"\ngate-ready (G1-G8 all pass): {len(ready)}/{len(items)}")
    print(f"cost: generation ${gen_cost:.2f} + model gates ${gate_cost:.2f} = ${gen_cost + gate_cost:.2f}"
          + (f" | per gate-ready item ${(gen_cost + gate_cost) / len(ready):.2f}" if ready else ""))
    print(f"generation attempts: {dict(attempts)}")
    reviewed = [i for i in items if (i.get("review") or {}).get("decision")]
    if reviewed:
        mins = [i["review"].get("minutes") for i in reviewed if i["review"].get("minutes")]
        print(f"reviewed: {len(reviewed)} {dict(Counter(i['review']['decision'] for i in reviewed))}"
              + (f" | {sum(mins) / len(mins):.1f} min per item" if mins else ""))
    print("\ntop failure reasons per gate:")
    for g in GATES:
        for r, n in reasons[g].most_common(4):
            print(f"  {g} x{n}: {r}")
    mix = Counter((i["component"], i.get("kind")) for i in items)
    print("\nby component/kind:", dict(mix))


if __name__ == "__main__":
    main()
