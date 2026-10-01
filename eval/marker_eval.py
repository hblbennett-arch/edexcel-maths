"""Measure the product marker (chatbot/marker.py) against the G4 reference scripts before adopting it.

    .venv/bin/python -m eval.marker_eval --baseline            # no model calls
    .venv/bin/python -m eval.marker_eval --pilot               # v2 on 3 items, prints cost per response
    .venv/bin/python -m eval.marker_eval --full                # v2 on every reference response (cached)
    .venv/bin/python -m eval.marker_eval --consistency 6       # re-mark 6 items' responses a second time
    .venv/bin/python -m eval.marker_eval --report              # table + logs/marker_eval_<YYYYMMDD>.json

Items: content/clean/items/*.json with G1..G8 all passing. Reference set per item: the G4 responses in `agreed`
(reference vector = the designed vector) or `consistent` (reference = both G4 markers' vector); `mismatched`
responses are skipped.
  BASELINE  the stored G4 first-marker vectors (gate_marking.MARKER_SYSTEM, Sonnet 5.5, all responses in one
            call) against the reference.
  V2        chatbot.marker.mark, one call per response, against the same reference.
CAVEAT (printed with every report): the reference was itself produced with the G4 marker, so where a script's
designed vector and the first marker agreed, or both G4 markers agreed, the baseline is being compared with
vectors it helped define. Baseline agreement is therefore optimistic; v2 is the independent measurement.

Every model call uses step names starting "marker-v2" and is cached in logs/marker_eval_cache.json, so a rerun
never re-spends. Spend is read from logs/llm_calls.jsonl (the only source of truth) and capped (--cap, $40).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import glob
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
from chatbot import marker, marks  # noqa: E402
import gate_marking  # noqa: E402  (its _norm / _mark: the same comparison G4 used; no calls are made)

ITEMS_DIR = ROOT / "content" / "clean" / "items"
LOG = ROOT / "logs" / "llm_calls.jsonl"
CACHE = ROOT / "logs" / "marker_eval_cache.json"
GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
PILOT_ITEMS = ("cr-area-between-curve-and-line-core", "cr-pure-de-given-separable-004",
               "cr-stats-binomial-probabilities-in-context-001")
CONSISTENCY_ITEMS = ("cr-area-between-curve-and-line-core", "cr-pure-de-given-separable-004",
                     "cr-stats-binomial-probabilities-in-context-001", "cr-integrate-using-trig-identities-core",
                     "cr-pure-de-formulate-from-rates-001", "cr-stats-normal-unknown-parameters-009")
CAVEAT = ("CAVEAT: the reference vectors were produced with the G4 marker (Sonnet 5.5): 'agreed' scripts are those where "
          "the first G4 marker (or the Opus second marker) matched the designed vector, and 'consistent' scripts take the "
          "G4 markers' own vector. Baseline agreement is therefore optimistic, not an independent accuracy figure.")
MAX_PARALLEL = 5
_lock = threading.Lock()


# ---- data --------------------------------------------------------------------------------------------
def passing_items() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(ITEMS_DIR / "*.json"))):
        item = json.loads(Path(f).read_text())
        gr = item.get("gate_results") or {}
        if all((gr.get(g) or {}).get("pass") for g in GATES):
            out.append(item)
    return out


def reference_set(item: dict) -> list[dict]:
    """[{id, kind, error_code, work, reference (vector list), first (G4 first-marker vector list)}]"""
    g4 = item["gate_results"]["G4"]
    first = {r["id"]: r.get("awarded") for r in g4.get("awarded", [])}
    consistent = g4.get("consistent") or {}
    out = []
    for r in g4["responses"]:
        if r["id"] in g4.get("agreed", []):
            ref = r["designed"]
        elif r["id"] in consistent:
            ref = consistent[r["id"]]
        else:
            continue
        out.append({"id": r["id"], "kind": r["kind"], "error_code": r.get("error_code"), "work": r["work"],
                    "reference": ref, "first": first.get(r["id"]) or [], "how": "agreed" if r["id"] in g4.get("agreed", []) else "consistent"})
    return out


def scheme_families(item: dict) -> dict:
    fam = {}
    for p in item["parts"]:
        fam[gate_marking.norm_label(p.get("label"))] = [marks.parse(m["code"]).family for m in p["mark_scheme"]]
    return fam


# ---- comparison ---------------------------------------------------------------------------------------
def compare(item: dict, ref_vec: list[dict], got_vec: list[dict]) -> dict:
    """Per-mark agreement of two vectors (normalised as G4 did), by family; exact = every part identical."""
    fam = scheme_families(item)
    want, got = gate_marking._norm(ref_vec), gate_marking._norm(got_vec)
    per_mark, by_family = [], {}
    for part, codes in want.items():
        g = got.get(part) or []
        for i, c in enumerate(codes):
            ok = i < len(g) and g[i] == c
            f = fam.get(part, [])[i] if i < len(fam.get(part, [])) else "other"
            per_mark.append(ok)
            by_family.setdefault(f, []).append(ok)
    return {"n": len(per_mark), "agree": sum(per_mark), "exact": want == got, "by_family": by_family,
            "want": want, "got": got}


def aggregate(rows: list[dict]) -> dict:
    n = sum(r["n"] for r in rows)
    agree = sum(r["agree"] for r in rows)
    fam: dict[str, list] = {}
    for r in rows:
        for f, oks in r["by_family"].items():
            fam.setdefault(f, []).extend(oks)
    return {"responses": len(rows), "marks": n, "per_mark_pct": round(100 * agree / n, 1) if n else None,
            "exact_vector_pct": round(100 * sum(r["exact"] for r in rows) / len(rows), 1) if rows else None,
            "by_family": {f: {"marks": len(o), "pct": round(100 * sum(o) / len(o), 1)} for f, o in sorted(fam.items())}}


# ---- spend -------------------------------------------------------------------------------------------
def spend(prefix: str = "marker-v2") -> dict:
    by_step: dict[str, dict] = {}
    if not LOG.exists():
        return {}
    for line in LOG.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if str(r.get("step", "")).startswith(prefix):
            s = by_step.setdefault(r["step"], {"calls": 0, "usd": 0.0, "failed": 0})
            s["calls"] += 1
            s["usd"] += r.get("cost_usd") or 0
            s["failed"] += 0 if r.get("ok") else 1
    for s in by_step.values():
        s["usd"] = round(s["usd"], 4)
    return by_step


def total_spend() -> float:
    return round(sum(s["usd"] for s in spend().values()), 4)


# ---- cache -------------------------------------------------------------------------------------------
def load_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def save_cache(cache: dict) -> None:
    tmp = CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=0, ensure_ascii=False))
    tmp.replace(CACHE)


def vec_of(result: dict, item: dict) -> list[dict]:
    return [{"part": p.get("label"), "marks": result["vectors"][gate_marking.norm_label(p.get("label"))]} for p in item["parts"]]


def run_v2(items: list[dict], run: str, cap: float, per_call_ceiling: float = 0.5) -> dict:
    """Mark every reference response of `items` with marker.mark (cached under `run`), max 5 in parallel, stopping
    before the cap. Returns the cache slice for `run`."""
    cache = load_cache()
    slot = cache.setdefault(run, {})
    jobs = [(it, r) for it in items for r in reference_set(it) if r["id"] not in slot.get(it["id"], {})]
    print(f"[{run}] {len(jobs)} responses to mark ({sum(len(reference_set(it)) for it in items) - len(jobs)} cached); "
          f"spend so far ${total_spend():.2f} of ${cap:.2f}")
    stop = threading.Event()

    def one(job):
        it, r = job
        if stop.is_set():
            return None
        if total_spend() + per_call_ceiling > cap:
            stop.set()
            print(f"STOP: spend ${total_spend():.2f} + ${per_call_ceiling:.2f} would exceed the ${cap:.2f} cap")
            return None
        t0 = time.time()
        try:
            res = marker.mark(it, None, r["work"], ref=f"{run}:{it['id']}/{r['id']}")
        except Exception as ex:  # a failed call is logged (cost) by claude_oneshot; record and carry on
            res = {"error": f"{type(ex).__name__}: {str(ex)[:300]}", "cost_usd": None}
        with _lock:
            slot.setdefault(it["id"], {})[r["id"]] = {"result": {k: v for k, v in res.items() if k != "lines"},
                                                     "seconds": round(time.time() - t0, 1)}
            save_cache(cache)
        return res

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        done = 0
        for res in pool.map(one, jobs):
            if res is None:
                continue
            done += 1
            if done % 10 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} marked, spend ${total_spend():.2f}", flush=True)
    return slot


# ---- metrics -----------------------------------------------------------------------------------------
def evaluate_run(items: list[dict], slot: dict) -> dict:
    rows, per_response, conf, overrides, withheld, with_code, with_rewrite, with_reason, errors = [], [], [], 0, 0, 0, 0, 0, 0
    cost, n_calls, secs = 0.0, 0, 0.0
    for it in items:
        for r in reference_set(it):
            entry = (slot.get(it["id"]) or {}).get(r["id"])
            if not entry:
                continue
            res = entry["result"]
            if "error" in res:
                errors += 1
                continue
            n_calls += 1
            cost += res.get("cost_usd") or 0
            secs += entry.get("seconds") or 0
            got = vec_of(res, it)
            c = compare(it, r["reference"], got)
            rows.append(c)
            overrides += res.get("overrides", 0)
            for d in res["decisions"]:
                conf.append(d.get("confidence", 0))
                if not d["awarded"]:
                    withheld += 1
                    with_code += bool(d.get("error_code"))
                    with_rewrite += bool(d.get("rewrite_to_earn"))
                    with_reason += bool(d.get("reason"))
            per_response.append({"item": it["id"], "response": r["id"], "kind": r["kind"], "error_code": r["error_code"],
                                 "how": r["how"], "reference": c["want"], "v2": c["got"], "exact": c["exact"],
                                 "agree": f"{c['agree']}/{c['n']}", "cost_usd": res.get("cost_usd")})
    agg = aggregate(rows)
    agg.update({"calls": n_calls, "errors": errors, "cost_usd": round(cost, 4),
                "cost_per_response": round(cost / n_calls, 4) if n_calls else None,
                "seconds_per_response": round(secs / n_calls, 1) if n_calls else None,
                "dependency_overrides": overrides, "avg_confidence": round(sum(conf) / len(conf), 3) if conf else None,
                "withheld": withheld, "withheld_with_error_code_pct": round(100 * with_code / withheld, 1) if withheld else None,
                "withheld_with_rewrite_pct": round(100 * with_rewrite / withheld, 1) if withheld else None,
                "withheld_with_reason_pct": round(100 * with_reason / withheld, 1) if withheld else None})
    return {"metrics": agg, "per_response": per_response}


def evaluate_baseline(items: list[dict]) -> dict:
    rows, per_response = [], []
    for it in items:
        for r in reference_set(it):
            c = compare(it, r["reference"], r["first"])
            rows.append(c)
            per_response.append({"item": it["id"], "response": r["id"], "kind": r["kind"], "how": r["how"],
                                 "reference": c["want"], "baseline": c["got"], "exact": c["exact"], "agree": f"{c['agree']}/{c['n']}"})
    return {"metrics": aggregate(rows), "per_response": per_response}


def evaluate_consistency(items: list[dict], first: dict, second: dict) -> dict:
    same = flips = n = pairs = 0
    detail = []
    for it in items:
        for r in reference_set(it):
            a, b = (first.get(it["id"]) or {}).get(r["id"]), (second.get(it["id"]) or {}).get(r["id"])
            if not a or not b or "error" in a["result"] or "error" in b["result"]:
                continue
            va, vb = gate_marking._norm(vec_of(a["result"], it)), gate_marking._norm(vec_of(b["result"], it))
            pairs += 1
            same += va == vb
            for part, codes in va.items():
                for i, c in enumerate(codes):
                    n += 1
                    flips += not (i < len(vb.get(part, [])) and vb[part][i] == c)
            if va != vb:
                detail.append({"item": it["id"], "response": r["id"], "run1": va, "run2": vb})
    return {"pairs": pairs, "identical_vector_pct": round(100 * same / pairs, 1) if pairs else None,
            "marks": n, "per_mark_flip_pct": round(100 * flips / n, 1) if n else None, "differences": detail}


def withheld_examples(items: list[dict], slot: dict, n: int = 6) -> list[dict]:
    out = []
    for it in items:
        for r in reference_set(it):
            entry = (slot.get(it["id"]) or {}).get(r["id"])
            if not entry or "error" in entry["result"]:
                continue
            ref = gate_marking._norm(r["reference"])
            for d in entry["result"]["decisions"]:
                part = gate_marking.norm_label(d.get("part"))
                if not d["awarded"] and not d.get("overridden") and ref.get(part, [None] * 9)[d["position"]:d["position"] + 1] == [gate_marking._mark(d["code"])]:
                    out.append({"item": it["id"], "response": r["id"], "part": d.get("part"), "code": d["code"],
                                "evidence": d["evidence"], "reason": d["reason"], "rewrite_to_earn": d["rewrite_to_earn"],
                                "error_code": d.get("error_code"), "convention": d.get("convention"), "confidence": d.get("confidence")})
    # spread across items
    seen, picked = set(), []
    for e in out:
        if e["item"] not in seen:
            picked.append(e)
            seen.add(e["item"])
        if len(picked) >= n:
            break
    return picked


def fmt_table(baseline: dict, v2: dict, cons: dict | None) -> str:
    b, v = baseline["metrics"], v2["metrics"]
    fams = sorted(set(b["by_family"]) | set(v["by_family"]))
    lines = ["", f"{'metric':<38}{'baseline (G4 marker)':>22}{'v2 (chatbot.marker)':>22}",
             f"{'responses compared':<38}{b['responses']:>22}{v['responses']:>22}",
             f"{'marks compared':<38}{b['marks']:>22}{v['marks']:>22}",
             f"{'per-mark agreement %':<38}{b['per_mark_pct']!s:>22}{v['per_mark_pct']!s:>22}",
             f"{'exact-vector agreement %':<38}{b['exact_vector_pct']!s:>22}{v['exact_vector_pct']!s:>22}"]
    for f in fams:
        bf, vf = b["by_family"].get(f, {}), v["by_family"].get(f, {})
        lines.append(f"{'  ' + f + ' marks %':<38}{(str(bf.get('pct')) + ' (n=' + str(bf.get('marks', 0)) + ')') if bf else '-':>22}"
                     f"{(str(vf.get('pct')) + ' (n=' + str(vf.get('marks', 0)) + ')') if vf else '-':>22}")
    lines += [f"{'dependency overrides':<38}{'-':>22}{v['dependency_overrides']:>22}",
              f"{'average confidence':<38}{'-':>22}{v['avg_confidence']!s:>22}",
              f"{'withheld marks':<38}{'-':>22}{v['withheld']:>22}",
              f"{'  with error_code %':<38}{'-':>22}{v['withheld_with_error_code_pct']!s:>22}",
              f"{'  with rewrite_to_earn %':<38}{'-':>22}{v['withheld_with_rewrite_pct']!s:>22}",
              f"{'  with reason %':<38}{'-':>22}{v['withheld_with_reason_pct']!s:>22}",
              f"{'calls / errors':<38}{'0':>22}{str(v['calls']) + ' / ' + str(v['errors']):>22}",
              f"{'cost total $ / per response $':<38}{'0':>22}{str(v['cost_usd']) + ' / ' + str(v['cost_per_response']):>22}"]
    if cons:
        lines += [f"{'consistency: identical vectors %':<38}{'-':>22}{cons['identical_vector_pct']!s:>22}",
                  f"{'consistency: per-mark flip %':<38}{'-':>22}{cons['per_mark_flip_pct']!s:>22}",
                  f"{'consistency: pairs / marks':<38}{'-':>22}{str(cons['pairs']) + ' / ' + str(cons['marks']):>22}"]
    return "\n".join(lines)


def verdict(baseline: dict, v2: dict) -> dict:
    b, v = baseline["metrics"]["per_mark_pct"], v2["metrics"]["per_mark_pct"]
    rule_a = v is not None and b is not None and v >= b - 2
    rule_b = v2["metrics"]["withheld_with_reason_pct"] == 100.0 and v2["metrics"]["withheld_with_rewrite_pct"] == 100.0
    return {"adopt": bool(rule_a and rule_b),
            "rule": "adopt if v2 per-mark agreement >= baseline - 2 points AND every withheld mark has a reason and a rewrite_to_earn",
            "per_mark_rule_met": rule_a, "explanation_rule_met": rule_b, "baseline_per_mark_pct": b, "v2_per_mark_pct": v}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--consistency", type=int, default=0, help="re-mark this many items' responses a second time")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--cap", type=float, default=40.0)
    args = ap.parse_args()
    items = passing_items()
    print(f"{len(items)} items pass G1..G8; {sum(len(reference_set(it)) for it in items)} reference responses; "
          f"marker-v2 spend so far ${total_spend():.2f}")
    if args.baseline or args.report:
        base = evaluate_baseline(items)
        print(CAVEAT)
        print("baseline:", json.dumps(base["metrics"]))
    if args.pilot:
        pilot = [it for it in items if it["id"] in PILOT_ITEMS]
        slot = run_v2(pilot, "v2", args.cap)
        ev = evaluate_run(pilot, slot)
        base_p = evaluate_baseline(pilot)
        print(fmt_table(base_p, ev, None))
        n_all = sum(len(reference_set(it)) for it in items)
        cpr = ev["metrics"]["cost_per_response"] or 0
        print(f"\npilot: {ev['metrics']['calls']} calls, ${ev['metrics']['cost_usd']:.3f}, ${cpr:.4f} per response; "
              f"extrapolated full run ({n_all} responses) ${cpr * n_all:.2f}; consistency (6 items) about "
              f"${cpr * sum(len(reference_set(it)) for it in items if it['id'] in CONSISTENCY_ITEMS):.2f}")
        print("spend by step:", json.dumps(spend()))
    if args.full:
        run_v2(items, "v2", args.cap)
    if args.consistency:
        chosen = [it for it in items if it["id"] in CONSISTENCY_ITEMS][:args.consistency]
        run_v2(chosen, "v2-repeat", args.cap)
    if args.report:
        cache = load_cache()
        v2 = evaluate_run(items, cache.get("v2", {}))
        chosen = [it for it in items if it["id"] in CONSISTENCY_ITEMS]
        cons = evaluate_consistency(chosen, cache.get("v2", {}), cache.get("v2-repeat", {})) if cache.get("v2-repeat") else None
        print(fmt_table(base, v2, cons))
        ver = verdict(base, v2)
        print("\nVERDICT:", "ADOPT v2" if ver["adopt"] else "DO NOT ADOPT v2 yet", json.dumps(ver))
        print("spend by step:", json.dumps(spend()), f"total ${total_spend():.2f}")
        examples = withheld_examples(items, cache.get("v2", {}))
        for e in examples[:3]:
            print(f"\n- {e['item']} {e['response']} part {e['part'] or '-'} {e['code']} [{e['convention']}, {e['error_code']}]\n"
                  f"  evidence: {e['evidence']}\n  reason: {e['reason']}\n  rewrite: {e['rewrite_to_earn']}")
        out = ROOT / "logs" / f"marker_eval_{time.strftime('%Y%m%d')}.json"
        out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "caveat": CAVEAT, "items": [it["id"] for it in items],
                                   "baseline": base, "v2": v2, "consistency": cons, "verdict": ver, "spend_by_step": spend(),
                                   "total_spend_usd": total_spend(), "withheld_examples": examples,
                                   "marker_prompt_sha": __import__("hashlib").sha256(marker.system_prompt().encode()).hexdigest()[:12]},
                                  indent=1, ensure_ascii=False))
        print(f"\nwritten {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
