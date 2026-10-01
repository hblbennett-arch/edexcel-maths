#!/usr/bin/env python3
"""Write the `guide` block of every interactive scene (docs/learn-layer-spec.md §2, "Guide"): what you see, a legend,
how to interact, the link to the question, and read-off lines. One Sonnet call per scene, JSON-schema constrained,
checked by the extended deterministic gate (scripts/clean/gate_scene.py) and written back into the same scene file.

    .venv/bin/python scripts/clean/annotate_scenes.py --dry --items cr-area-between-curve-and-line-core
    .venv/bin/python scripts/clean/annotate_scenes.py --items id1,id2 --parallel 3
    .venv/bin/python scripts/clean/annotate_scenes.py --items all --parallel 5 --max-usd 10 [--force]

The model sees only our own material: the item's question and the part's mark codes and `for` texts, the scene
JSON, the coverage the gate will demand (legend ids, controls, live labels) and our prompt
(content/prompts/guide_system.md, byte-identical across calls). A failing guide is regenerated once with our own
error messages fed back. Each scene gets `guide` and `guide_meta: {model, cost_usd, attempts, gate}`; scenes that
already have a guide are skipped unless --force. Costs are logged by claude_oneshot (step names "guide*").
"""
import argparse
import glob
import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_scene import gate_scene, guide_requirements, load_item, _guide_texts  # noqa: E402
import make_scenes as ms  # noqa: E402

MODEL = "claude-sonnet-5-5"
STEP = "guide"
SCENES = ms.SCENES
PROMPT = ROOT / "content" / "prompts" / "guide_system.md"
LOG = ms.LOG

STR = {"type": "string"}
STR_LIST = {"type": "array", "items": STR}
SCHEMA = {
    "type": "object",
    "properties": {
        "what_you_see": STR,
        "legend": {"type": "array", "items": {"type": "object", "properties": {"id": STR, "meaning": STR},
                                              "required": ["id", "meaning"]}},
        "interact": {"type": "array", "items": {"type": "object", "properties": {
            "control": STR, "kind": {"type": "string", "enum": ["slider", "glider", "point"]}, "do": STR, "watch": STR},
            "required": ["control", "kind", "do", "watch"]}},
        "question_link": {"type": "object", "properties": {
            "part": {"type": ["string", "null"]}, "marks": STR_LIST, "text": STR},
            "required": ["part", "marks", "text"]},
        "read_off": STR_LIST,
    },
    "required": ["what_you_see", "legend", "interact", "question_link", "read_off"],
}

SCENE_KEYS = ("id", "part", "title", "purpose", "approach", "board", "params", "elements", "steps", "links")


def user_message(item: dict, scene: dict) -> str:
    part_label = scene.get("part")
    parts = item.get("parts") or []
    part = next((p for p in parts if p.get("label") == part_label), None) or (parts[0] if parts else {})
    req = guide_requirements(scene)
    lines = [f"ITEM {item['id']}", f"SCENE {scene.get('id')}  (part: {json.dumps(part_label)})", ""]
    if item.get("stem"):
        lines += ["QUESTION STEM", item["stem"], ""]
    lines += [f"PART {part.get('label') or '-'} ({part.get('marks')} marks)", part.get("text", ""), "",
              "MARK CODES of this part (use these exact codes in question_link.marks):"]
    lines += [f"  {m.get('code')}: {m.get('for')}" for m in part.get("mark_scheme") or []]
    lines += ["", "SCENE JSON (do not change it; describe it):",
              json.dumps({k: scene[k] for k in SCENE_KEYS if k in scene}, ensure_ascii=False), "",
              "REQUIRED LEGEND IDS (one legend entry each, plus any other element whose meaning is not obvious): "
              + (", ".join(req["legend_ids"]) or "none"),
              "CONTROLS (one interact entry each, with this kind): "
              + (", ".join(f"{k} ({v})" for k, v in req["controls"].items()) or "none"),
              "LIVE TEXT LABELS (one read_off line each): "
              + (", ".join(f"{eid}: {el.get('value')}" for eid in req["live_texts"]
                           for el in scene.get("elements") or [] if el.get("id") == eid) or "none"),
              f"question_link.part must be {json.dumps(part_label)}.",
              "", "Write the guide block following your instructions."]
    return "\n".join(lines)


def g7_phrases(guide: dict) -> list[str]:
    """Name the word 8-grams of the guide that the G7 copy check found in the reference corpus, so the retry knows
    which phrase to reword (the gate's own message only counts them)."""
    try:
        import gates
        c = gates.corpus()
    except Exception:
        return []
    out = []
    for name, t in _guide_texts(guide):
        hits = [g for g in gates._grams(gates.words(t), 8) & c.grams8 if not gates._whitelisted(g, c.whitelist)]
        for g in hits:
            out.append(f"{name}: reword the phrase {g!r} (it also appears in a published source; say it your own way)")
    return out


def scene_files(spec: str) -> list[Path]:
    if spec == "all":
        return sorted(SCENES.glob("*.json"))
    paths = []
    for s in spec.split(","):
        s = s.strip()
        if any(c in s for c in "*?/"):
            paths += [Path(p) for p in sorted(glob.glob(s))]
        else:
            paths.append(SCENES / (s if s.endswith(".json") else s + ".json"))
    return [p for p in paths if p.exists() or print(f"  no such scene file: {p}", file=sys.stderr)]


def atomic_write(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


_lock = threading.Lock()
_spent = [0.0]
_file_locks: dict[str, threading.Lock] = {}


def annotate(path: Path, scene_index: int, system: str, max_usd: float, dry: bool = False) -> dict | None:
    from claude_oneshot import run, text_block
    rec = json.loads(path.read_text())
    scene = rec["scenes"][scene_index]
    item = load_item(rec.get("item_id") or str(scene.get("id", "")).split("::")[0]) or {}
    msg = user_message(item, scene)
    if dry:
        print(msg)
        return None
    attempts, cost, last_errs, guide, gate = 0, 0.0, [], None, None
    for step in (STEP, STEP + "-retry"):
        with _lock:
            if _spent[0] >= max_usd:
                print(f"  {scene['id']}: spend cap reached, stopping", file=sys.stderr)
                break
        content = [text_block(msg)]
        if last_errs:
            content.append(text_block("Your previous guide failed these checks; fix every one and return the full "
                                      "corrected JSON:\n- " + "\n- ".join(last_errs[:25])))
        attempts += 1
        try:
            r = run(system, content, schema=SCHEMA, model=MODEL, max_usd=1.5, thinking_tokens=2000, step=step,
                    ref=scene["id"])
        except Exception as ex:
            last_errs = [f"call failed: {ex}"]
            print(f"  {scene['id']}: attempt {attempts} call failed: {str(ex)[:200]}", file=sys.stderr)
            continue
        cost += r.get("cost_usd") or 0.0
        with _lock:
            _spent[0] += r.get("cost_usd") or 0.0
        guide = r["result"]
        trial = dict(scene, guide=guide)
        gate = gate_scene(trial, item, require_guide=True)
        guide_errs = [e for e in gate["errors"] if e.startswith("guide") or "guide." in e]
        if gate["pass"]:
            last_errs = []
            break
        last_errs = guide_errs or gate["errors"]
        last_errs += g7_phrases(guide)
        print(f"  {scene['id']}: attempt {attempts} failed {len(gate['errors'])} checks: "
              + "; ".join(e[:120] for e in gate["errors"][:4]), file=sys.stderr)
    if guide is None:
        return None
    meta = {"model": MODEL, "cost_usd": round(cost, 4), "attempts": attempts, "gate": {"pass": gate["pass"],
            "errors": gate["errors"]}, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with _file_locks.setdefault(str(path), threading.Lock()):
        rec = json.loads(path.read_text())          # re-read: another scene of this file may have been written
        rec["scenes"][scene_index]["guide"] = guide
        rec["scenes"][scene_index]["guide_meta"] = meta
        atomic_write(path, rec)
    print(f"  {scene['id']}: guide {'PASS' if gate['pass'] else 'FAIL'}, {len(guide.get('legend') or [])} legend, "
          f"{len(guide.get('interact') or [])} interact, {attempts} attempt(s), ${cost:.3f}")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="all", help="'all', comma-separated item ids, or a glob of scene files")
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="rewrite guides that already exist")
    ap.add_argument("--dry", action="store_true", help="print the user message for the first scene, no call")
    ap.add_argument("--max-usd", type=float, default=10.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after this many scenes (pilot)")
    a = ap.parse_args()
    system = PROMPT.read_text()
    jobs = []
    for p in scene_files(a.items):
        rec = json.loads(p.read_text())
        for i, sc in enumerate(rec.get("scenes") or []):
            if sc.get("guide") and not a.force and not a.dry:
                continue
            jobs.append((p, i))
    if a.limit:
        jobs = jobs[:a.limit]
    print(f"{len(jobs)} scene(s) to do")
    if a.dry:
        for p, i in jobs[:1]:
            annotate(p, i, system, a.max_usd, dry=True)
        return 0
    before = ms.log_lines()
    with ThreadPoolExecutor(max_workers=max(1, min(5, a.parallel))) as ex:
        metas = [m for m in ex.map(lambda j: annotate(j[0], j[1], system, a.max_usd), jobs) if m]
    n_pass = sum(1 for m in metas if m["gate"]["pass"])
    print(f"done: {len(metas)} guide(s), {n_pass} pass the gate, spent ${_spent[0]:.2f} "
          f"({ms.log_lines() - before} log lines)")
    return 0 if n_pass == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
