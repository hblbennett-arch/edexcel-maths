#!/usr/bin/env python3
"""Solution levels (docs/learn-layer-spec.md §1): write `brisk` and `every_step` for each part of a clean item.

    .venv/bin/python scripts/clean/enrich_solutions.py --items 'content/clean/items/*.json' --parallel 5
    .venv/bin/python scripts/clean/enrich_solutions.py --items cr-chain-rule-starter --dry        # print the prompt
    .venv/bin/python scripts/clean/enrich_solutions.py --items ... --force --max-usd 40

One Sonnet 5.5 call per part (JSON-schema constrained), system prompt content/prompts/levels_system.md
(byte-identical across calls). Only our own item text enters the prompt. The result is gated with
gate_levels.part_errors; on failure it is regenerated once with our gate messages fed back. The part gets
`solution_levels` and `levels_meta` {model, generated_at, cost_usd, attempts, errors}; the item gets
`gate_results.GL`. Files are written atomically (temp file + rename). Parts with levels are skipped unless
--force. Only items passing G1..G8 are processed unless --any-item.
"""
import argparse
import glob
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_oneshot  # noqa: E402
import gate_levels  # noqa: E402

MODEL = "claude-sonnet-5-5"
ITEMS_DIR = ROOT / "content" / "clean" / "items"
SYSTEM = (ROOT / "content" / "prompts" / "levels_system.md").read_text()
SCHEMA = {"type": "object", "properties": {
    "brisk": {"type": "array", "items": {"type": "object", "properties": {
        "step": {"type": "integer"}, "working": {"type": "string"},
        "secures": {"type": "array", "items": {"type": "string"}}},
        "required": ["step", "working", "secures"]}},
    "every_step": {"type": "array", "items": {"type": "object", "properties": {
        "step": {"type": "integer"}, "working": {"type": "string"}, "why": {"type": "string"},
        "secures": {"type": ["string", "null"]}, "check": {"type": ["string", "null"]}},
        "required": ["step", "working", "why", "secures", "check"]}}},
    "required": ["brisk", "every_step"]}
WRITE_LOCK = threading.Lock()
GATE_LOCK = threading.Lock()   # the G7 corpus / embedder are shared; one gate at a time
SPENT = {"usd": 0.0}
SPENT_LOCK = threading.Lock()


def _scrub(x):
    """Stored gate messages must not name a board (G8 scans every string in the item)."""
    if isinstance(x, str):
        return x.replace("Pearson corpus", "reference corpus").replace("Pearson", "reference")
    if isinstance(x, list):
        return [_scrub(v) for v in x]
    return x


def passes_g1_g8(item: dict) -> bool:
    gr = item.get("gate_results") or {}
    return all((gr.get(f"G{n}") or {}).get("pass") for n in range(1, 9))


def resolve_items(specs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for s in specs:
        if any(ch in s for ch in "*?[") or s.endswith(".json"):
            paths += [Path(p) for p in sorted(glob.glob(s))]
        else:
            paths.append(ITEMS_DIR / f"{s}.json")
    return [p for p in paths if p.exists()]


def part_prompt(item: dict, part: dict, previous: dict | None = None, errors: list[str] | None = None) -> str:
    lab = part.get("label")
    lines = ["Write the brisk and every_step solution levels for the part of the maths question below, as the "
             "system prompt describes. This is a revision exercise for A level Mathematics students.", "", "# Question"]
    if item.get("stem"):
        lines += [item["stem"], ""]
    earlier = [p for p in item["parts"] if p is not part and item["parts"].index(p) < item["parts"].index(part)]
    if earlier:
        lines.append("Earlier parts (for context only; do not solve them):")
        for p in earlier:
            lines.append(f"({p.get('label')}) {p.get('text')}")
            for a in p.get("answers") or []:
                lines.append(f"    answer {a.get('name') or ''}: {a.get('expr')}")
        lines.append("")
    lines += [f"## This part{f' ({lab})' if lab else ''}, {part.get('marks')} mark(s), command: {part.get('command')}",
              part.get("text", ""), "", "# Mark scheme for this part (codes in order)"]
    for m in part.get("mark_scheme") or []:
        lines.append(f"- {m.get('code')}: {m.get('for')}" + (f"  [notes: {m.get('notes')}]" if m.get("notes") else ""))
    lines += ["", "Scheme codes, in order: " + ", ".join(m.get("code", "") for m in part.get("mark_scheme") or []),
              "", "# Standard solution"]
    for s in part.get("solution") or []:
        lines.append(f"{s.get('step')}. {s.get('working')}" + (f"   ({s.get('mark')})" if s.get("mark") else ""))
    lines += ["", "# Final answers"]
    if part.get("answers"):
        for a in part["answers"]:
            lines.append(f"- {a.get('name') or 'answer'} = {a.get('expr')}" + (f" (form: {a.get('form')})" if a.get("form") else ""))
    else:
        lines.append("(none: a show-that, explain or state part)")
    if previous is not None and errors:
        lines += ["", "# Your previous attempt failed these checks; fix every one and return the corrected levels",
                  *[f"- {e}" for e in errors], "", "Previous attempt:", json.dumps(previous, ensure_ascii=False)]
    return "\n".join(lines)


def _write_part(path: Path, part_index: int, levels: dict, meta: dict) -> dict:
    with WRITE_LOCK:
        item = json.loads(path.read_text())
        item["parts"][part_index]["solution_levels"] = levels
        item["parts"][part_index]["levels_meta"] = meta
        with GATE_LOCK:
            item["gate_results"] = {**(item.get("gate_results") or {}), "GL": gate_levels.gate_levels(item)}
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
        tmp.replace(path)
        return item["gate_results"]["GL"]


def enrich_part(path: Path, item: dict, part_index: int, max_usd: float) -> dict:
    part = item["parts"][part_index]
    ref = f"{item['id']}/{part.get('label') or '-'}"
    cost, attempts, previous, errors = 0.0, 0, None, []
    result, history = None, []
    for attempt in range(2):
        with SPENT_LOCK:
            if SPENT["usd"] >= max_usd:
                return {"ref": ref, "skipped": "spend cap reached"}
        attempts += 1
        content = [claude_oneshot.text_block(part_prompt(item, part, previous, errors))]
        step = "levels" if attempt == 0 else "levels-retry"
        try:
            out = claude_oneshot.run(SYSTEM, content, schema=SCHEMA, model=MODEL, max_usd=1.0, thinking_tokens=4000,
                                     step=step, ref=ref, timeout=600)
        except RuntimeError:   # transient API failure (e.g. a safeguard false positive): one more try
            time.sleep(3)
            out = claude_oneshot.run(SYSTEM, content, schema=SCHEMA, model=MODEL, max_usd=1.0, thinking_tokens=4000,
                                     step=step + "-again", ref=ref, timeout=600)
        cost += out.get("cost_usd") or 0.0
        with SPENT_LOCK:
            SPENT["usd"] += out.get("cost_usd") or 0.0
        result = out["result"]
        trial = {**part, "solution_levels": result}
        with GATE_LOCK:
            errors, warns = gate_levels.part_errors(item, trial)
        if not errors:
            break
        history.append(errors)
        previous = result
    meta = {"model": MODEL, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cost_usd": round(cost, 4), "attempts": attempts, "errors": _scrub(errors), "attempt_errors": _scrub(history)}
    gl = _write_part(path, part_index, result, meta)
    return {"ref": ref, "cost_usd": cost, "attempts": attempts, "errors": errors, "history": history, "warnings": warns,
            "gl_pass": gl["pass"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", nargs="+", required=True, help="item ids, paths or globs")
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="regenerate parts that already have levels")
    ap.add_argument("--dry", action="store_true", help="print the prompts, make no calls")
    ap.add_argument("--max-usd", type=float, default=40.0)
    ap.add_argument("--any-item", action="store_true", help="don't require G1..G8 to pass")
    ap.add_argument("--redo-failed", action="store_true", help="also regenerate parts whose levels failed the gate")
    ap.add_argument("--limit-parts", type=int, default=0, help="stop after this many parts (0 = all)")
    args = ap.parse_args()
    args.parallel = max(1, min(5, args.parallel))

    jobs: list[tuple[Path, dict, int]] = []
    for path in resolve_items(args.items):
        item = json.loads(path.read_text())
        if not args.any_item and not passes_g1_g8(item):
            print(f"skip {path.name}: G1..G8 not all passed")
            continue
        for i, p in enumerate(item.get("parts") or []):
            done = bool(p.get("solution_levels"))
            failed = bool((p.get("levels_meta") or {}).get("errors"))
            if done and not args.force and not (args.redo_failed and failed):
                continue
            jobs.append((path, item, i))
    if args.limit_parts:
        jobs = jobs[:args.limit_parts]
    print(f"{len(jobs)} part(s) to do")
    if args.dry:
        for path, item, i in jobs:
            print(f"\n===== {item['id']} part {item['parts'][i].get('label') or '-'} =====\n--- system ({len(SYSTEM)} chars): "
                  f"content/prompts/levels_system.md\n--- user:\n{part_prompt(item, item['parts'][i])}")
        return 0
    t0, results = time.time(), []
    with ThreadPoolExecutor(max_workers=args.parallel) as ex:
        futs = {ex.submit(enrich_part, path, item, i, args.max_usd): (path, i) for path, item, i in jobs}
        for f in as_completed(futs):
            try:
                r = f.result()
            except Exception as e:
                path, i = futs[f]
                r = {"ref": f"{path.stem}/{i}", "error": f"{type(e).__name__}: {str(e)[:200]}"}
            results.append(r)
            if r.get("error"):
                print(f"FAILED {r['ref']}: {r['error']}")
            elif r.get("skipped"):
                print(f"skipped {r['ref']}: {r['skipped']}")
            else:
                print(f"{r['ref']}: {'PASS' if not r['errors'] else 'FAIL'} attempts={r['attempts']} "
                      f"${r['cost_usd']:.3f} (item GL {'pass' if r['gl_pass'] else 'fail'})")
                for e in r["errors"]:
                    print(f"    error: {e}")
                for i, hist in enumerate(r.get("history") or [], 1):
                    for e in hist:
                        print(f"    attempt {i} failed: {e}")
    print(f"\n{len(results)} part(s), ${SPENT['usd']:.2f}, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
