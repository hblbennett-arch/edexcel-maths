"""Per-mark agreement between human second marking and marker v2 (no model calls).

    .venv/bin/python eval/second_marking_report.py                      # data/clean_private/second_marking.jsonl
    .venv/bin/python eval/second_marking_report.py --log PATH [--items DIR] [--cache PATH]

Reads the jsonl written by scripts/clean/second_mark_server.py (one line per (item, script, part):
{at, by, item_id, script_id, part, human: [bools], seconds}), joins each line to the marker v2 vector
(logs/marker_eval_cache.json) and the G4 reference (the item's gate_results.G4), and prints per-mark agreement
with 95% Wilson intervals, overall and by mark family / script kind, then every disagreement.
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
from chatbot import marks  # noqa: E402
import second_mark_server as sm  # noqa: E402

CAVEAT = ("CAVEAT: the scripts are scripted answers written by the generator (correct, partial, pitfall and "
          "alternative-method scripts), not real student scripts. Agreement on real, handwritten-then-typed "
          "student work is the figure to publish; add real scripts to the queue before quoting these numbers.")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def fmt(k: int, n: int) -> str:
    if n == 0:
        return "n/a (0 marks)"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:5.1f}%  ({k}/{n}; 95% Wilson {100 * lo:.1f}-{100 * hi:.1f}%)"


def join(log_rows: list[dict], items_dir: Path | None, cache_path: Path | None) -> list[dict]:
    """One row per mark: {item_id, script_id, part, position, code, family, kind, human, v2, reference, reason}."""
    cache = sm.load_cache(cache_path)
    items: dict[str, dict] = {}
    latest: dict[tuple, dict] = {}
    for r in log_rows:  # the latest submission per (item, script, part) wins
        latest[(r.get("item_id"), r.get("script_id"), sm.part_key(r.get("part")))] = r
    out = []
    for (iid, sid, part), r in latest.items():
        if iid not in items:
            items[iid] = sm.load_item(iid, items_dir) or {}
        item = items[iid]
        if not item:
            continue
        g4 = (item.get("gate_results") or {}).get("G4") or {}
        resp = next((x for x in g4.get("responses") or [] if x.get("id") == sid), {})
        v2 = sm.v2_record(cache, iid, sid)
        ref = sm.reference_vector(item, sid)
        codes = [ln["code"] for ln in sm.scheme_lines(item) if ln["part"] == part]
        v2b = sm.bools(v2["vectors"].get(part, [])) if v2 else []
        refb = sm.bools(ref.get(part, [])) if ref else []
        reasons = {d.get("position"): d.get("reason") for d in (v2 or {}).get("decisions") or []
                   if sm.part_key(d.get("part")) == part}
        for i, h in enumerate(r.get("human") or []):
            code = codes[i] if i < len(codes) else "?"
            m = marks.try_parse(code)
            out.append({"item_id": iid, "script_id": sid, "part": part, "position": i, "code": code,
                        "family": m.family if m else "other", "kind": resp.get("kind") or "unknown",
                        "error_code": resp.get("error_code"), "human": bool(h),
                        "v2": v2b[i] if i < len(v2b) else None, "reference": refb[i] if i < len(refb) else None,
                        "reason": reasons.get(i)})
    return out


def agreement(rows: list[dict], a: str, b: str) -> tuple[int, int]:
    pairs = [(r[a], r[b]) for r in rows if r.get(a) is not None and r.get(b) is not None]
    return sum(x == y for x, y in pairs), len(pairs)


def report(log_path: Path, items_dir: Path | None = None, cache_path: Path | None = None) -> str:
    log_rows = sm.read_log(log_path)
    rows = join(log_rows, items_dir, cache_path)
    lines = [f"Second marking report — {log_path}"]
    scripts = {(r["item_id"], r["script_id"]) for r in rows}
    markers = sorted({r.get("by") or "?" for r in log_rows})
    lines.append(f"scripts: {len(scripts)}   marks: {len(rows)}   items: {len({r['item_id'] for r in rows})}   "
                 f"marked by: {', '.join(markers) or '-'}")
    secs = [r.get("seconds") for r in log_rows if isinstance(r.get("seconds"), (int, float))]
    if secs:
        lines.append(f"median time per screen: {sorted(secs)[len(secs) // 2]:.0f}s")
    lines.append("")
    lines.append("Per-mark agreement")
    lines.append(f"  human vs marker v2      : {fmt(*agreement(rows, 'human', 'v2'))}")
    lines.append(f"  human vs G4 reference   : {fmt(*agreement(rows, 'human', 'reference'))}")
    lines.append(f"  marker v2 vs reference  : {fmt(*agreement(rows, 'v2', 'reference'))}   (same scripts)")

    def breakdown(title: str, key: str) -> None:
        lines.append("")
        lines.append(f"By {title} (human vs v2 | human vs reference)")
        groups: dict[str, list] = defaultdict(list)
        for r in rows:
            groups[str(r[key])].append(r)
        for g in sorted(groups):
            lines.append(f"  {g:<14} {fmt(*agreement(groups[g], 'human', 'v2'))}  |  "
                         f"{fmt(*agreement(groups[g], 'human', 'reference'))}")

    breakdown("mark family", "family")
    breakdown("script kind", "kind")
    lines.append("")
    dis = [r for r in rows if (r["v2"] is not None and r["v2"] != r["human"])
           or (r["reference"] is not None and r["reference"] != r["human"])]
    lines.append(f"Disagreements with the human ({len(dis)})")
    if not dis:
        lines.append("  none")
    yn = lambda v: "-" if v is None else ("1" if v else "0")  # noqa: E731
    for r in dis:
        who = []
        if r["v2"] is not None and r["v2"] != r["human"]:
            who.append("v2")
        if r["reference"] is not None and r["reference"] != r["human"]:
            who.append("ref")
        lines.append(f"  {r['item_id']} {r['script_id']} part={r['part']} pos={r['position']} {r['code']:<6} "
                     f"human={yn(r['human'])} v2={yn(r['v2'])} ref={yn(r['reference'])}  [{'+'.join(who)}]"
                     f"{' ' + r['error_code'] if r.get('error_code') else ''}")
        if r.get("reason"):
            lines.append(f"      v2: {r['reason']}")
    lines.append("")
    lines.append(CAVEAT)
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=str(sm.OUT))
    ap.add_argument("--items", default=None)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    log = Path(a.log)
    if not log.exists():
        raise SystemExit(f"no second-marking log at {log} (run scripts/clean/second_mark_server.py first)")
    print(report(log, Path(a.items) if a.items else None, Path(a.cache) if a.cache else None))


if __name__ == "__main__":
    main()
