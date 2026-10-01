#!/usr/bin/env python3
"""Interactive scene descriptions for clean items (docs/learn-layer-spec.md §2), written by the model from our own
item files and checked deterministically before saving. Scenes go to content/clean/scenes/<item-id>.json (a separate
folder: the item files are not touched).

    .venv/bin/python scripts/clean/make_scenes.py --dry --items cr-area-between-curve-and-line-core
    .venv/bin/python scripts/clean/make_scenes.py --items 'content/clean/items/cr-pure-de-*.json' --parallel 5
    .venv/bin/python scripts/clean/make_scenes.py --items all --parallel 5 --max-usd 40 [--force]

Only gate-passed items (G1..G8 all pass) are used. The model sees only our own material: the item's question, mark
codes and `for` texts, standard solution and pitfalls, and our prompt (content/prompts/scene_system.md, byte-identical
across calls). Output is JSON-schema constrained. Structural checks (a lightweight version of the spec's gates, since
scripts/clean/gate_scene.py is being written separately):
  expressions parse with sympy after ^ -> ** with free symbols in {x, t} plus param ids and no implicit multiplication;
  ids unique and every referenced id exists; element types and colour tokens from the table; board ranges ordered;
  params sane; functions finite at 9 sample points; 2 to 5 steps; at least one slider or glider; links.marks are codes
  of the part's scheme (suffix-tolerant via chatbot.marks.parse); links.pitfalls are the item's error codes;
  links.solution_steps exist; KaTeX renders every $...$; no banned words.
A failing scene set is regenerated once with our own error messages fed back (same model), then once more with
claude-opus-5-5. Costs are logged by claude_oneshot (step names "scene*").
"""
import argparse
import glob
import json
import math
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sympy as sp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_scene  # noqa: E402
import gate_style  # noqa: E402
from chatbot import marks  # noqa: E402

MODEL = "claude-sonnet-5-5"
FALLBACK_MODEL = "claude-opus-5-5"
STEP = "scene"
ITEMS = ROOT / "content" / "clean" / "items"
SCENES = ROOT / "content" / "clean" / "scenes"
PROMPT = ROOT / "content" / "prompts" / "scene_system.md"
TAGS = ROOT / "content" / "clean" / "tags.json"
LOG = ROOT / "logs" / "llm_calls.jsonl"
ALL_GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")

ELEMENT_TYPES = {"function", "parametric", "point", "glider", "segment", "line", "tangent", "normal", "integral",
                 "vector", "circle", "polygon", "text", "vline", "hline"}
COLOURS = {"primary", "secondary", "success", "warning", "muted", "mark"}
APPROACHES = {"graphical", "algebraic-check", "model"}
BANNED = re.compile(r"\b(pearson|edexcel|aqa|ocr|examiners?|past\s+papers?|mark\s+schemes?\s+(say|says|said)|pmt)\b", re.I)
IMPLICIT = re.compile(r"[\d)]\s*[A-Za-z(]")
IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
SPECIAL = re.compile(r"^(area|x|y)\(([A-Za-z][A-Za-z0-9_]*)\)$")
ON_TYPES = {"function", "parametric", "segment", "circle"}

STR = {"type": "string"}
NUM = {"type": "number"}
PAIR = {"type": "array", "items": STR, "minItems": 2, "maxItems": 2}
STR_LIST = {"type": "array", "items": STR}
SCHEMA = {
    "type": "object",
    "properties": {
        "applicable": {"type": "boolean"},
        "reason": STR,
        "scenes": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": STR, "part": {"type": ["string", "null"]}, "title": STR, "purpose": STR,
                "approach": {"type": "string", "enum": sorted(APPROACHES)},
                "board": {"type": "object", "properties": {
                    "x": {"type": "array", "items": NUM, "minItems": 2, "maxItems": 2},
                    "y": {"type": "array", "items": NUM, "minItems": 2, "maxItems": 2},
                    "axis": {"type": "boolean"}, "grid": {"type": "boolean"},
                    "aspect": {"type": "string", "enum": ["auto", "equal"]}},
                    "required": ["x", "y", "axis", "grid", "aspect"]},
                "params": {"type": "array", "items": {"type": "object", "properties": {
                    "id": STR, "label": STR, "min": NUM, "max": NUM, "step": NUM, "value": NUM},
                    "required": ["id", "label", "min", "max", "step", "value"]}},
                "elements": {"type": "array", "items": {"type": "object", "properties": {
                    "type": {"type": "string", "enum": sorted(ELEMENT_TYPES)}, "id": STR,
                    "expr": STR, "x_expr": STR, "y_expr": STR, "x": STR, "y": STR, "on": STR, "at": STR, "of": STR,
                    "from": {"anyOf": [STR, PAIR]}, "to": {"anyOf": [STR, PAIR]}, "between": PAIR,
                    "centre": PAIR, "radius": STR, "domain": PAIR, "t_range": PAIR,
                    "points": {"type": "array", "items": {"anyOf": [STR, PAIR]}},
                    "value": STR, "label": STR, "color": {"type": "string", "enum": sorted(COLOURS)},
                    "dash": {"type": "boolean"}, "draggable": {"type": "boolean"}, "opacity": NUM},
                    "required": ["type", "id"]}},
                "steps": {"type": "array", "items": {"type": "object", "properties": {
                    "n": {"type": "integer"}, "text": STR,
                    "set": {"type": "object", "additionalProperties": NUM},
                    "show": STR_LIST, "hide": STR_LIST, "highlight": STR_LIST},
                    "required": ["n", "text"]}},
                "links": {"type": "object", "properties": {
                    "solution_steps": {"type": "array", "items": {"type": "integer"}},
                    "marks": STR_LIST, "pitfalls": STR_LIST},
                    "required": ["solution_steps", "marks", "pitfalls"]},
            },
            "required": ["id", "part", "title", "purpose", "approach", "board", "params", "elements", "steps", "links"],
        }},
    },
    "required": ["applicable", "reason", "scenes"],
}


# ---- item side --------------------------------------------------------------------------------
def gate_passed(item: dict) -> bool:
    g = item.get("gate_results") or {}
    return all((g.get(k) or {}).get("pass") for k in ALL_GATES)


def load_items(spec: str) -> list[dict]:
    if spec == "all":
        paths = sorted(ITEMS.glob("*.json"))
    else:
        paths = []
        for s in spec.split(","):
            s = s.strip()
            if any(c in s for c in "*?/"):
                paths += [Path(p) for p in sorted(glob.glob(s))]
            else:
                paths.append(ITEMS / (s if s.endswith(".json") else s + ".json"))
    items = []
    for p in paths:
        if not p.exists():
            print(f"  no such item: {p}", file=sys.stderr)
            continue
        d = json.loads(p.read_text())
        if gate_passed(d):
            items.append(d)
        else:
            print(f"  skipped (gates not all passed): {d.get('id')}", file=sys.stderr)
    return items


def type_title(qtype: str) -> str:
    try:
        for q in json.loads(TAGS.read_text()).get("question_types", []):
            if q.get("id") == qtype:
                return f"{q.get('title')} ({qtype}): {q.get('definition', '')}"
    except Exception:
        pass
    return qtype or "?"


def user_message(item: dict) -> str:
    lines = [f"ITEM {item['id']}", f"Question type: {type_title(item.get('question_type'))}",
             f"Component: {item.get('component')}; tier: {item.get('tier')}", ""]
    if item.get("stem"):
        lines += ["STEM", item["stem"], ""]
    for p in item.get("parts") or []:
        lab = p.get("label") or "-"
        lines += [f"PART {lab} ({p.get('marks')} marks, command: {p.get('command')})", p.get("text", ""), "",
                  "Mark scheme codes (use these exact codes in links.marks):"]
        lines += [f"  {m.get('code')}: {m.get('for')}" for m in p.get("mark_scheme") or []]
        lines += ["Standard solution (step numbers for links.solution_steps):"]
        lines += [f"  {s.get('step')}. {s.get('working')}" + (f"  [{s['mark']}]" if s.get("mark") else "")
                  for s in p.get("solution") or []]
        lines.append("")
    pits = item.get("pitfalls") or []
    if pits:
        lines.append("Pitfalls (error codes for links.pitfalls):")
        lines += [f"  part {x.get('part') or '-'} step {x.get('step')} [{x.get('error_code')}]: {x.get('text')}" for x in pits]
    lines += ["", "Decide `applicable` and `approach`; if applicable write 1 scene (2 if two parts need different "
              "pictures) following the format, grammar and gates in your instructions."]
    return "\n".join(lines)


# ---- structural checks --------------------------------------------------------------------------
def _parse(expr, allowed: set[str], where: str, errs: list[str]):
    """Parse one expression string; report and return None on any problem."""
    if isinstance(expr, (int, float)) and not isinstance(expr, bool):
        expr = str(expr)
    if not isinstance(expr, str) or not expr.strip():
        errs.append(f"{where}: missing or empty expression")
        return None
    if IMPLICIT.search(expr):
        errs.append(f"{where}: implicit multiplication in {expr!r} (write 2*x, not 2x; (x+1)*(x-2), not (x+1)(x-2))")
        return None
    try:   # the scene grammar (whitelist, arity of the statistics helpers, free symbols), same code as the gate
        return gate_scene.check_expr(expr, set(allowed) - gate_scene.VARS, set(allowed))
    except gate_scene.ExprError as ex:
        errs.append(f"{where}: {ex} in {expr!r}; allowed symbols: {sorted(allowed)}")
        return None


def _pair(v, allowed, where, errs, ids=None, id_ok=False):
    if id_ok and isinstance(v, str):
        if v not in (ids or {}):
            errs.append(f"{where}: refers to unknown id {v!r}")
        return
    if not (isinstance(v, list) and len(v) == 2):
        errs.append(f"{where}: expected [x, y]" + (" or a point id" if id_ok else ""))
        return
    _parse(v[0], allowed, f"{where}[0]", errs)
    _parse(v[1], allowed, f"{where}[1]", errs)


def _finite(e, var: sp.Symbol, lo: float, hi: float, subs: dict, where: str, errs: list[str]) -> None:
    try:
        f = sp.lambdify(var, e.subs(subs), gate_scene.LAMBDIFY_MODULES)
    except Exception as ex:
        errs.append(f"{where}: cannot evaluate ({type(ex).__name__})")
        return
    bad = []
    for i in range(9):
        xv = lo + (hi - lo) * (i + 0.5) / 9
        try:
            v = f(xv)
            if isinstance(v, complex) or not math.isfinite(float(v)):
                bad.append(round(xv, 3))
        except Exception:
            bad.append(round(xv, 3))
    if bad:
        errs.append(f"{where}: not finite at x = {bad} (restrict `domain` or change the board range)")


def check_scene(scene: dict, item: dict, all_ids: set[str]) -> list[str]:
    errs: list[str] = []
    sid = scene.get("id") or "?"
    parts = {(p.get("label") or None): p for p in item.get("parts") or []}
    part = scene.get("part")
    if part not in parts:
        errs.append(f"{sid}: part {part!r} is not a part of this item ({sorted(str(k) for k in parts)})")
        p = next(iter(parts.values()), {})
    else:
        p = parts[part]
    if scene.get("approach") not in APPROACHES:
        errs.append(f"{sid}: approach must be one of {sorted(APPROACHES)}")
    # board
    b = scene.get("board") or {}
    ranges = {}
    for ax in ("x", "y"):
        r = b.get(ax)
        if not (isinstance(r, list) and len(r) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in r)
                and r[0] < r[1]):
            errs.append(f"{sid}: board.{ax} must be two finite numbers in increasing order")
        else:
            ranges[ax] = r
    # params
    params = {}
    for q in scene.get("params") or []:
        pid = q.get("id")
        if not isinstance(pid, str) or not IDENT.match(pid) or pid in ("x", "t", "e", "pi", "E") or len(pid) > 12:
            errs.append(f"{sid}: param id {pid!r} must be a short identifier other than x, t, e, pi")
            continue
        if pid in params or pid in all_ids:
            errs.append(f"{sid}: param id {pid!r} is not unique")
        params[pid] = q
        try:
            lo, hi, st, val = (float(q[k]) for k in ("min", "max", "step", "value"))
            if not (lo < hi and st > 0 and lo <= val <= hi):
                errs.append(f"{sid}: param {pid}: need min < max, step > 0 and min <= value <= max")
            elif (hi - lo) / st > 10000:
                errs.append(f"{sid}: param {pid}: step too small for the range")
        except (KeyError, TypeError, ValueError):
            errs.append(f"{sid}: param {pid}: min, max, step, value must all be numbers")
    subs = {sp.Symbol(k): sp.Float(q.get("value", 0)) for k, q in params.items()}
    pset = set(params)
    # elements
    els = {}
    for el in scene.get("elements") or []:
        eid = el.get("id")
        if not isinstance(eid, str) or not IDENT.match(eid):
            errs.append(f"{sid}: element id {eid!r} must be an identifier")
            continue
        if eid in els or eid in params:
            errs.append(f"{sid}: element id {eid!r} is not unique")
        els[eid] = el
        if el.get("type") not in ELEMENT_TYPES:
            errs.append(f"{sid}: element {eid}: type {el.get('type')!r} not in the table")
        if "color" in el and el["color"] not in COLOURS:
            errs.append(f"{sid}: element {eid}: colour {el['color']!r} is not a token {sorted(COLOURS)}")
    ids = set(els) | pset
    used_param = set()

    def track(e):
        if e is not None:
            used_param.update(str(s) for s in e.free_symbols if str(s) in pset)

    def ref(eid, kinds, where):
        if eid not in els:
            errs.append(f"{where}: refers to unknown element id {eid!r}")
            return None
        if kinds and els[eid].get("type") not in kinds:
            errs.append(f"{where}: {eid!r} is a {els[eid].get('type')}, need one of {sorted(kinds)}")
        return els[eid]

    xr = ranges.get("x", [-1.0, 1.0])
    for eid, el in els.items():
        t, w = el.get("type"), f"{sid}: element {eid}"
        if t == "function":
            e = _parse(el.get("expr"), {"x"} | pset, f"{w}.expr", errs)
            track(e)
            lo, hi = xr
            if el.get("domain") is not None:
                d = el["domain"]
                a = _parse(d[0], pset, f"{w}.domain[0]", errs) if isinstance(d, list) and len(d) == 2 else None
                c = _parse(d[1], pset, f"{w}.domain[1]", errs) if isinstance(d, list) and len(d) == 2 else None
                if a is None or c is None:
                    errs.append(f"{w}.domain: expected [a, b]") if not isinstance(d, list) else None
                else:
                    try:
                        lo, hi = float(a.subs(subs)), float(c.subs(subs))
                        if not lo < hi:
                            errs.append(f"{w}.domain: a < b needed")
                    except Exception:
                        errs.append(f"{w}.domain: not numeric")
            if e is not None and lo < hi:
                _finite(e, sp.Symbol("x"), lo, hi, subs, f"{w}.expr", errs)
        elif t == "parametric":
            ex = _parse(el.get("x_expr"), {"t"} | pset, f"{w}.x_expr", errs)
            ey = _parse(el.get("y_expr"), {"t"} | pset, f"{w}.y_expr", errs)
            track(ex), track(ey)
            tr = el.get("t_range")
            if not (isinstance(tr, list) and len(tr) == 2):
                errs.append(f"{w}.t_range: expected [a, b]")
            else:
                a = _parse(tr[0], pset, f"{w}.t_range[0]", errs)
                c = _parse(tr[1], pset, f"{w}.t_range[1]", errs)
                if a is not None and c is not None:
                    try:
                        lo, hi = float(a.subs(subs)), float(c.subs(subs))
                        if not lo < hi:
                            errs.append(f"{w}.t_range: a < b needed")
                        else:
                            for e in (ex, ey):
                                if e is not None:
                                    _finite(e, sp.Symbol("t"), lo, hi, subs, f"{w} parametric", errs)
                    except Exception:
                        errs.append(f"{w}.t_range: not numeric")
        elif t == "point":
            track(_parse(el.get("x"), pset, f"{w}.x", errs))
            track(_parse(el.get("y"), pset, f"{w}.y", errs))
        elif t == "glider":
            ref(el.get("on"), ON_TYPES, f"{w}.on")
            track(_parse(el.get("x", "0"), pset, f"{w}.x", errs))
        elif t in ("segment", "line", "vector"):
            for k in ("from", "to"):
                v = el.get(k)
                if isinstance(v, str):
                    ref(v, {"point", "glider"}, f"{w}.{k}")
                else:
                    _pair(v, pset, f"{w}.{k}", errs)
                    if isinstance(v, list) and len(v) == 2:
                        track(_parse(v[0], pset, f"{w}.{k}[0]", []))
                        track(_parse(v[1], pset, f"{w}.{k}[1]", []))
        elif t in ("tangent", "normal"):
            ref(el.get("at"), {"point", "glider"}, f"{w}.at")
            ref(el.get("of"), {"function"}, f"{w}.of")
        elif t == "integral":
            if el.get("between") is not None:
                bt = el["between"]
                if not (isinstance(bt, list) and len(bt) == 2):
                    errs.append(f"{w}.between: expected [f, g]")
                else:
                    for f in bt:
                        ref(f, {"function"}, f"{w}.between")
            elif el.get("of") is not None:
                ref(el["of"], {"function"}, f"{w}.of")
            else:
                errs.append(f"{w}: integral needs `of` or `between`")
            for k in ("from", "to"):
                track(_parse(el.get(k), pset, f"{w}.{k}", errs))
        elif t == "circle":
            _pair(el.get("centre"), pset, f"{w}.centre", errs)
            track(_parse(el.get("radius"), pset, f"{w}.radius", errs))
        elif t == "polygon":
            pts = el.get("points")
            if not (isinstance(pts, list) and len(pts) >= 3):
                errs.append(f"{w}.points: need at least 3 points")
            else:
                for i, v in enumerate(pts):
                    if isinstance(v, str):
                        ref(v, {"point", "glider"}, f"{w}.points[{i}]")
                    else:
                        _pair(v, pset, f"{w}.points[{i}]", errs)
                        if isinstance(v, list) and len(v) == 2:
                            track(_parse(v[0], pset, "", [])), track(_parse(v[1], pset, "", []))
        elif t == "text":
            _parse(el.get("x"), pset, f"{w}.x", errs)
            _parse(el.get("y"), pset, f"{w}.y", errs)
            val = el.get("value")
            if not isinstance(val, str) or not val.strip():
                errs.append(f"{w}.value: missing")
            else:
                for m in PLACEHOLDER.finditer(val):
                    inner = m.group(1).strip()
                    sm = SPECIAL.match(inner)
                    if sm:
                        kind, rid = sm.groups()
                        want = {"integral"} if kind == "area" else {"point", "glider"}
                        ref(rid, want, f"{w}.value {{{inner}}}")
                    elif inner and not inner.startswith("\\"):
                        track(_parse(inner, pset, f"{w}.value {{{inner}}}", errs))
        elif t in ("vline", "hline"):
            track(_parse(el.get("at"), pset, f"{w}.at", errs))
    # steps
    steps = scene.get("steps") or []
    if not 2 <= len(steps) <= 5:
        errs.append(f"{sid}: {len(steps)} steps; need 2 to 5")
    for i, s in enumerate(steps, 1):
        w = f"{sid}: step {i}"
        if not isinstance(s.get("text"), str) or len(s["text"].strip()) < 15:
            errs.append(f"{w}: text missing or too short")
        for k, v in (s.get("set") or {}).items():
            if k not in params:
                errs.append(f"{w}.set: {k!r} is not a param id")
            else:
                try:
                    if not float(params[k]["min"]) <= float(v) <= float(params[k]["max"]):
                        errs.append(f"{w}.set: {k} = {v} is outside [{params[k]['min']}, {params[k]['max']}]")
                except (TypeError, ValueError, KeyError):
                    pass
            used_param.add(k)
        for k in ("show", "hide", "highlight"):
            for eid in s.get(k) or []:
                if eid not in els:
                    errs.append(f"{w}.{k}: unknown element id {eid!r}")
    # interactivity
    has_glider = any(el.get("type") == "glider" for el in els.values())
    has_draggable = any(el.get("type") == "point" and el.get("draggable") for el in els.values())
    if not (has_glider or (params and used_param)):
        errs.append(f"{sid}: no interactive affordance (a param slider that some element or step uses, or a glider)")
    for pid in pset - used_param:
        errs.append(f"{sid}: param {pid!r} is never used by an element or a step")
    del has_draggable
    # links
    links = scene.get("links") or {}
    codes = [m.get("code") for m in p.get("mark_scheme") or []]
    for alt in p.get("alternatives") or []:
        codes += [m.get("code") for m in alt.get("marks") or []]
    canon = set()
    for c in codes:
        canon.add(c)
        m = marks.try_parse(c or "")
        if m:
            canon.add((m.kind, m.worth))
    for c in links.get("marks") or []:
        m = marks.try_parse(c or "")
        if c not in canon and not (m and (m.kind, m.worth) in canon):
            errs.append(f"{sid}: links.marks {c!r} is not a code of part {part or '-'} ({[x for x in codes if isinstance(x, str)]})")
    ecodes = {x.get("error_code") for x in item.get("pitfalls") or []}
    for c in links.get("pitfalls") or []:
        if c not in ecodes:
            errs.append(f"{sid}: links.pitfalls {c!r} is not an error code on this item ({sorted(x for x in ecodes if x)})")
    nsteps = {s.get("step") for s in p.get("solution") or []}
    for n in links.get("solution_steps") or []:
        if n not in nsteps:
            errs.append(f"{sid}: links.solution_steps {n} is not a step of part {part or '-'} ({sorted(nsteps)})")
    if not (links.get("marks") or links.get("solution_steps")):
        errs.append(f"{sid}: links must name at least one mark code or solution step")
    # text: banned words and KaTeX
    texts = [("title", scene.get("title", "")), ("purpose", scene.get("purpose", "")), ("reason", "")]
    texts += [(f"step {i}", s.get("text", "")) for i, s in enumerate(steps, 1)]
    texts += [(f"element {e}.value", el.get("value", "")) for e, el in els.items() if el.get("type") == "text"]
    texts += [(f"element {e}.label", el.get("label", "")) for e, el in els.items() if el.get("label")]
    batch, where = [], []
    for w, s in texts:
        if not isinstance(s, str):
            continue
        for m in BANNED.finditer(s):
            errs.append(f"{sid}: {w} mentions {m.group(0)!r}")
        found, _ = gate_style.spans(s)
        for tex, disp in found:
            batch.append((tex, disp))
            where.append(w)
    if batch:
        for w, (tex, _), e in zip(where, batch, gate_style.katex_errors(batch)):
            if e:
                errs.append(f"{sid}: {w}: KaTeX cannot render ${tex[:60]}$: {e}")
    return errs


def check_output(out: dict, item: dict) -> dict:
    """Structural checks over a model output; returns {"pass", "errors", "n_scenes"}."""
    errs: list[str] = []
    scenes = out.get("scenes") or []
    if not isinstance(out.get("applicable"), bool):
        errs.append("applicable must be true or false")
    if out.get("applicable") and not scenes:
        errs.append("applicable is true but no scenes were given")
    if not out.get("applicable") and scenes:
        errs.append("applicable is false but scenes were given")
    if not out.get("applicable") and not (out.get("reason") or "").strip():
        errs.append("reason is required when not applicable")
    if len(scenes) > 2:
        errs.append(f"{len(scenes)} scenes; at most 2")
    if BANNED.search(out.get("reason") or ""):
        errs.append("reason mentions a banned word")
    seen = set()
    for sc in scenes:
        sid = sc.get("id")
        if not isinstance(sid, str) or not sid.startswith(item["id"] + "::"):
            errs.append(f"scene id {sid!r} must start with {item['id']}::")
        if sid in seen:
            errs.append(f"duplicate scene id {sid!r}")
        seen.add(sid)
        errs += check_scene(sc, item, set())
    return {"pass": not errs, "errors": errs, "n_scenes": len(scenes)}


# ---- generation -------------------------------------------------------------------------------------------
_lock = threading.Lock()
_spent = [0.0]


def log_lines() -> int:
    return sum(1 for _ in LOG.open()) if LOG.exists() else 0


def generate(item: dict, system: str, max_usd: float, dry: bool = False) -> dict | None:
    from claude_oneshot import run, text_block
    msg = user_message(item)
    if dry:
        print(msg)
        return None
    attempts, cost, last_errs, out, model = 0, 0.0, [], None, MODEL
    plan = [(MODEL, STEP), (MODEL, STEP + "-retry"), (FALLBACK_MODEL, STEP + "-opus")]
    for model, step in plan:
        with _lock:
            if _spent[0] >= max_usd:
                print(f"  {item['id']}: spend cap reached, stopping", file=sys.stderr)
                break
        content = [text_block(msg)]
        if last_errs:
            content.append(text_block("Your previous answer failed these structural checks; fix every one and return "
                                      "the full corrected JSON:\n- " + "\n- ".join(last_errs[:25])))
        attempts += 1
        try:
            r = run(system, content, schema=SCHEMA, model=model, max_usd=3.0, thinking_tokens=4000, step=step,
                    ref=item["id"])
        except Exception as ex:
            last_errs = [f"call failed: {ex}"]
            print(f"  {item['id']}: attempt {attempts} call failed: {str(ex)[:200]}", file=sys.stderr)
            continue
        cost += r.get("cost_usd") or 0.0
        with _lock:
            _spent[0] += r.get("cost_usd") or 0.0
        out = r["result"]
        chk = check_output(out, item)
        if chk["pass"]:
            last_errs = []
            break
        last_errs = chk["errors"]
        print(f"  {item['id']}: attempt {attempts} ({model}) failed {len(last_errs)} checks: "
              + "; ".join(e[:120] for e in last_errs[:4]), file=sys.stderr)
    if out is None:
        return None
    chk = check_output(out, item)
    rec = {"item_id": item["id"], "applicable": out.get("applicable"), "reason": out.get("reason", ""),
           "scenes": out.get("scenes") or [], "model": model, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "cost_usd": round(cost, 4), "attempts": attempts, "checks": chk}
    SCENES.mkdir(parents=True, exist_ok=True)
    (SCENES / f"{item['id']}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    app = "applicable" if rec["applicable"] else "not applicable"
    print(f"  {item['id']}: {app}, {chk['n_scenes']} scene(s), checks {'PASS' if chk['pass'] else 'FAIL'}, "
          f"{attempts} attempt(s), ${cost:.3f}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="all", help="'all', comma-separated ids, or a glob")
    ap.add_argument("--parallel", type=int, default=5)
    ap.add_argument("--force", action="store_true", help="regenerate items that already have a scene file")
    ap.add_argument("--dry", action="store_true", help="print the user message, no call")
    ap.add_argument("--max-usd", type=float, default=40.0)
    a = ap.parse_args()
    system = PROMPT.read_text()
    items = load_items(a.items)
    if not a.force and not a.dry:
        items = [i for i in items if not (SCENES / f"{i['id']}.json").exists()]
    print(f"{len(items)} item(s) to do")
    if a.dry:
        for it in items[:1]:
            generate(it, system, a.max_usd, dry=True)
        return 0
    before = log_lines()
    with ThreadPoolExecutor(max_workers=max(1, min(5, a.parallel))) as ex:
        recs = [r for r in ex.map(lambda it: generate(it, system, a.max_usd), items) if r]
    n_app = sum(1 for r in recs if r["applicable"])
    n_pass = sum(1 for r in recs if r["checks"]["pass"])
    print(f"done: {len(recs)} files, {n_app} applicable, {n_pass} pass checks, spent ${_spent[0]:.2f} "
          f"({log_lines() - before} log lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
