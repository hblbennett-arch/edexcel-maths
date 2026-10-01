"""Deterministic gate for interactive scenes (docs/learn-layer-spec.md §2, "Gates"). No model calls.

    from scripts.clean.gate_scene import gate_scene
    gate_scene(scene, item) -> {"pass": bool, "errors": [...], "warnings": [...]}

    .venv/bin/python scripts/clean/gate_scene.py scene.json [scene2.json ...] [--item ITEM_ID] [--no-g7]
        A file holds a scene, a list of scenes, or the generator's envelope {"item_id", "scenes": [...]}. The item
        id defaults to the envelope's item_id, else the part of scene["id"] before "::"; items are read from
        content/clean/items/.

Checks: every expression parses with sympy (^ -> **) and its free symbols lie in {x, t} plus the param ids, with
the same whitelist tokeniser rules as the browser compiler (no implicit multiplication, only the listed functions);
ids exist and are unique, types are from the table; board ranges finite and ordered; params sane; functions finite
at 9 sample points; 2 to 5 steps; KaTeX renders every $...$; G7 copy check on all text; no banned phrases;
links.marks are codes of the part's scheme (suffix-tolerant); links.pitfalls are error codes of the item.
Guide (spec §2 "Guide", when scene["guide"] is present, or required with --require-guide / require_guide=True):
legend ids exist; every labelled/integral/glider/draggable-point/tangent/normal/vector element has a legend entry;
every param, glider and draggable point has an interact entry of the right kind with a concrete do and watch;
question_link.part matches the scene's part and its marks are codes of the part's scheme; one read_off line per
live text element; KaTeX, banned words and the G7 copy check run over every guide text.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))

from chatbot import marks  # noqa: E402
import gate_style  # noqa: E402
from check_provenance import BANNED  # noqa: E402

ITEMS_DIR = ROOT / "content" / "clean" / "items"

FUNCS = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
         "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh, "exp": sp.exp, "ln": sp.log,
         "log": lambda a: sp.log(a, 10), "sqrt": sp.sqrt, "abs": sp.Abs, "floor": sp.floor}
CONSTS = {"pi": sp.pi, "e": sp.E}


# ---- statistics helpers (spec §2 grammar; mirror SCENE_STATS in chatbot/static/scene_compile.js) ---------------
# sympy has no binomial CDF of symbolic arguments, so each helper is a sympy Function that collapses to a Float as
# soon as every argument is numeric (after the default params are substituted) and is otherwise left symbolic, so
# the free-symbol check still works. lambdify evaluates them through NUMERIC (see sample_finite).
MAX_BINOM_N = 100000


def _binom_ok(n, p) -> bool:
    return math.isfinite(n) and 0 <= n <= MAX_BINOM_N and math.isfinite(p) and 0 <= p <= 1


def _binom_pmf(n, p, k):
    n, k = int(round(n)), int(round(k))
    if not _binom_ok(n, p):
        return math.nan
    if k < 0 or k > n:
        return 0.0
    if p == 0:
        return 1.0 if k == 0 else 0.0
    if p == 1:
        return 1.0 if k == n else 0.0
    return math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p))


def _binom_sum(n, p, a, b):
    return min(1.0, max(0.0, sum(_binom_pmf(n, p, i) for i in range(a, b + 1))))


def _binom_le(n, p, k):
    n, k = int(round(n)), int(round(k))
    if not _binom_ok(n, p):
        return math.nan
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return _binom_sum(n, p, 0, k) if k <= n / 2 else 1 - _binom_sum(n, p, k + 1, n)


def _binom_ge(n, p, k):
    n, k = int(round(n)), int(round(k))
    if not _binom_ok(n, p):
        return math.nan
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return _binom_sum(n, p, k, n) if k > n / 2 else 1 - _binom_sum(n, p, 0, k - 1)


def _norm_ok(x, mu, sigma) -> bool:
    return all(math.isfinite(v) for v in (x, mu, sigma)) and sigma > 0


def _norm_cdf(x, mu, sigma):
    return 0.5 * math.erfc(-(x - mu) / (sigma * math.sqrt(2))) if _norm_ok(x, mu, sigma) else math.nan


def _norm_pdf(x, mu, sigma):
    if not _norm_ok(x, mu, sigma):
        return math.nan
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))


def _norm_inv(q, mu, sigma):
    if not _norm_ok(q, mu, sigma) or not 0 < q < 1:
        return math.nan
    return statistics.NormalDist(mu, sigma).inv_cdf(q)


NUMERIC = {"binom_pmf": _binom_pmf, "binom_le": _binom_le, "binom_ge": _binom_ge,
           "norm_cdf": _norm_cdf, "norm_pdf": _norm_pdf, "norm_inv": _norm_inv}
LAMBDIFY_MODULES = [NUMERIC, "math"]


def _stat_function(name: str, impl):
    def eval_(cls, *args):
        try:
            vals = [float(a) for a in args]
        except (TypeError, ValueError):
            return None             # symbolic argument: stay unevaluated
        return sp.Float(impl(*vals))
    return type(name, (sp.Function,), {"nargs": 3, "eval": classmethod(eval_), "__module__": __name__})


STAT_FUNCS = {name: _stat_function(name, impl) for name, impl in NUMERIC.items()}
FUNCS.update(STAT_FUNCS)
ARITY = {name: 3 for name in STAT_FUNCS}      # every other function takes one argument
VARS = {"x", "t"}
RESERVED = set(FUNCS) | set(CONSTS) | VARS

TYPES = {"function", "parametric", "point", "glider", "segment", "line", "tangent", "normal", "integral", "vector",
         "circle", "polygon", "text", "vline", "hline"}
GLIDER_HOSTS = {"function", "parametric", "segment", "circle", "line"}
POINT_TYPES = {"point", "glider"}
COLOURS = {"primary", "secondary", "success", "warning", "muted", "mark"}
APPROACHES = {"graphical", "algebraic-check", "model"}

TOKEN_RE = re.compile(r"\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|([-+*/^(),])|(.))")
IMPLICIT_RE = re.compile(r"(\d|\))\s*([A-Za-z(])")
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")
SPECIAL_RE = re.compile(r"^(area|x|y)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$")
ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAMPLE_POINTS = 9


class ExprError(ValueError):
    pass


def tokenise(src: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    src = str(src)
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1) is not None:
            out.append(("num", m.group(1)))
        elif m.group(2) is not None:
            out.append(("id", m.group(2)))
        elif m.group(3) is not None:
            out.append(("op", m.group(3)))
        elif m.group(4) is not None:
            if m.group(4).strip():
                raise ExprError(f"character not allowed: {m.group(4)!r}")
    return out


def check_expr(expr, params: set[str], allow: set[str]) -> sp.Expr:
    """Tokenise + whitelist (mirrors scene_compile.js), implicit-multiplication regex, sympy parse with ^ -> **,
    free symbols within `allow` (a subset of {x, t} plus params). Returns the sympy expression."""
    if isinstance(expr, bool) or expr is None:
        raise ExprError("expression missing")
    if isinstance(expr, (int, float)):
        if not math.isfinite(expr):
            raise ExprError("number is not finite")
        return sp.Float(expr) if isinstance(expr, float) else sp.Integer(expr)
    if not isinstance(expr, str) or not expr.strip():
        raise ExprError("expression must be a non-empty string")
    m = IMPLICIT_RE.search(expr)
    if m:
        raise ExprError(f"implicit multiplication is not allowed: {m.group(0)!r}")
    toks = tokenise(expr)
    stack: list[list] = []      # one [function name or None, argument count] per open bracket
    for i, (kind, val) in enumerate(toks):
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if kind == "id":
            if val in FUNCS:
                if not (nxt and nxt == ("op", "(")):
                    raise ExprError(f"function {val} must be followed by (")
            elif val in CONSTS or val in VARS or val in params:
                if nxt and nxt == ("op", "("):
                    raise ExprError(f"implicit multiplication is not allowed: {val}(")
            else:
                raise ExprError(f"unknown identifier {val!r}")
        ends_value = kind == "num" or (kind == "op" and val == ")") or (kind == "id" and val not in FUNCS)
        starts_value = nxt is not None and (nxt[0] in ("num", "id") or nxt == ("op", "("))
        if ends_value and starts_value:
            raise ExprError(f"implicit multiplication is not allowed: {val}{nxt[1]}")
        # commas only between the arguments of a function, and each function gets exactly its arity
        if kind == "op" and val == "(":
            prv = toks[i - 1] if i else None
            stack.append([prv[1] if prv and prv[0] == "id" and prv[1] in FUNCS else None, 1])
        elif kind == "op" and val == ")":
            if not stack:
                raise ExprError("unbalanced )")
            fn, got = stack.pop()
            want = ARITY.get(fn, 1)
            if fn and got != want:
                raise ExprError(f"function {fn} takes {want} argument{'' if want == 1 else 's'} (got {got})")
        elif kind == "op" and val == ",":
            if not stack or not stack[-1][0]:
                raise ExprError("commas are only allowed between the arguments of a function")
            stack[-1][1] += 1
    if stack:
        raise ExprError("unbalanced (")
    local = dict(FUNCS)
    local.update(CONSTS)
    for p in params | VARS:
        local[p] = sp.Symbol(p)
    try:
        e = parse_expr(expr.replace("^", "**"), local_dict=local, transformations=standard_transformations, evaluate=True)
    except Exception as ex:  # SyntaxError, TokenError, TypeError ...
        raise ExprError(f"does not parse: {type(ex).__name__}: {str(ex).splitlines()[0] if str(ex) else ''}")
    if not isinstance(e, sp.Basic):
        raise ExprError("does not parse to an expression")
    free = {str(s) for s in e.free_symbols}
    bad = free - allow
    if bad:
        raise ExprError(f"free symbol(s) not allowed here: {sorted(bad)}")
    return e


def _finite(v) -> bool:
    try:
        c = complex(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(c.real) and abs(c.imag) < 1e-9


def sample_finite(e: sp.Expr, var: str, lo: float, hi: float, subs: dict) -> str | None:
    """None if e is finite and real at 9 points across [lo, hi] (params at their defaults), else a message."""
    e = e.subs(subs)
    s = sp.Symbol(var)
    try:
        f = sp.lambdify(s, e, modules=LAMBDIFY_MODULES)
    except Exception:
        f = None
    for i in range(SAMPLE_POINTS):
        xv = lo + (hi - lo) * i / (SAMPLE_POINTS - 1)
        try:
            v = f(xv) if f is not None else e.subs(s, xv).evalf()
        except Exception:
            v = None
        if v is None or not _finite(v):
            return f"not finite/real at {var} = {xv:g}"
    return None


def scalar_value(e: sp.Expr, subs: dict):
    v = e.subs(subs).evalf()
    return complex(v) if _finite(v) else None


def _texts_of(scene: dict) -> list[tuple[str, str]]:
    out = [("title", scene.get("title") or ""), ("purpose", scene.get("purpose") or "")]
    for i, s in enumerate(scene.get("steps") or []):
        out.append((f"steps[{i}].text", (s or {}).get("text") or ""))
    for el in scene.get("elements") or []:
        if isinstance(el, dict):
            if el.get("type") == "text":
                out.append((f"element {el.get('id')}.value", str(el.get("value") or "")))
            if el.get("label"):
                out.append((f"element {el.get('id')}.label", str(el.get("label"))))
    return out


def _scheme_codes(item: dict, part_label) -> list[str]:
    parts = item.get("parts") or []
    if part_label is not None:
        parts = [p for p in parts if p.get("label") == part_label] or parts
    codes = []
    for p in parts:
        codes += [m.get("code") for m in p.get("mark_scheme") or [] if m.get("code")]
        for alt in p.get("alternatives") or []:
            codes += [m.get("code") for m in alt.get("marks") or [] if m.get("code")]
    return codes


def _endpoint(spec, where, params, ids, point_ids, errors, subs, need_point=True):
    """from/to/centre: [x, y] of expressions, or a point id. Returns True when valid."""
    if isinstance(spec, str) and spec in ids:
        if need_point and spec not in point_ids:
            errors.append(f"{where}: {spec!r} is not a point or glider")
        return
    if isinstance(spec, str) and ID_RE.match(spec) and spec not in params and spec not in RESERVED:
        errors.append(f"{where}: unknown point id {spec!r}")
        return
    if not (isinstance(spec, list) and len(spec) == 2):
        errors.append(f"{where}: expected [x, y] or a point id")
        return
    for k, ex in zip("xy", spec):
        try:
            e = check_expr(ex, params, set(params))
            if scalar_value(e, subs) is None:
                errors.append(f"{where}.{k}: not finite at the default params")
        except ExprError as er:
            errors.append(f"{where}.{k} {ex!r}: {er}")


def gate_scene(scene: dict, item: dict | None, g7: bool = True, require_guide: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    item = item or {}
    if not isinstance(scene, dict):
        return {"pass": False, "errors": ["scene is not an object"], "warnings": []}

    # ---- board -------------------------------------------------------------------------------------------
    board = scene.get("board") or {}
    xr, yr = board.get("x"), board.get("y")
    for name, r in (("x", xr), ("y", yr)):
        if not (isinstance(r, list) and len(r) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in r)):
            errors.append(f"board.{name} must be [min, max] numbers")
        elif not all(math.isfinite(v) for v in r):
            errors.append(f"board.{name} must be finite")
        elif not r[0] < r[1]:
            errors.append(f"board.{name} must be ordered: {r}")
    if board.get("aspect") not in (None, "auto", "equal"):
        errors.append(f"board.aspect must be 'auto' or 'equal', not {board.get('aspect')!r}")
    x_ok = not any(e.startswith("board.x") for e in errors)
    xlo, xhi = (xr if x_ok else (-10, 10))

    # ---- params ------------------------------------------------------------------------------------------
    params: set[str] = set()
    subs: dict = {}
    ids: dict[str, str] = {}
    for i, p in enumerate(scene.get("params") or []):
        pid = p.get("id") if isinstance(p, dict) else None
        if not isinstance(pid, str) or not ID_RE.match(pid):
            errors.append(f"params[{i}]: bad id {pid!r}")
            continue
        if pid in RESERVED:
            errors.append(f"params[{i}]: id {pid!r} is reserved")
        if pid in ids:
            errors.append(f"duplicate id {pid!r}")
        ids[pid] = "param"
        params.add(pid)
        try:
            lo, hi, st, val = (float(p[k]) for k in ("min", "max", "step", "value"))
        except (KeyError, TypeError, ValueError):
            errors.append(f"param {pid}: needs numeric min, max, step, value")
            continue
        if not all(math.isfinite(v) for v in (lo, hi, st, val)):
            errors.append(f"param {pid}: values must be finite")
        if not lo < hi:
            errors.append(f"param {pid}: min < max required ({lo}, {hi})")
        if not st > 0:
            errors.append(f"param {pid}: step > 0 required")
        if not lo <= val <= hi:
            errors.append(f"param {pid}: value {val} outside [{lo}, {hi}]")
        subs[sp.Symbol(pid)] = val
        if not p.get("label"):
            warnings.append(f"param {pid}: no label")

    # ---- elements: ids and types first -------------------------------------------------------------------
    elements = scene.get("elements") or []
    if not isinstance(elements, list) or not elements:
        errors.append("elements must be a non-empty list")
        elements = []
    etype: dict[str, str] = {}
    for i, el in enumerate(elements):
        if not isinstance(el, dict):
            errors.append(f"elements[{i}] is not an object")
            continue
        eid = el.get("id")
        if not isinstance(eid, str) or not ID_RE.match(eid):
            errors.append(f"elements[{i}]: bad id {eid!r}")
            continue
        if eid in ids:
            errors.append(f"duplicate id {eid!r}")
        ids[eid] = el.get("type")
        if el.get("type") not in TYPES:
            errors.append(f"element {eid}: unknown type {el.get('type')!r}")
        else:
            etype[eid] = el["type"]
        if el.get("color") is not None and el.get("color") not in COLOURS:
            errors.append(f"element {eid}: unknown colour token {el.get('color')!r}")
    point_ids = {k for k, v in etype.items() if v in POINT_TYPES}
    func_ids = {k for k, v in etype.items() if v == "function"}
    func_expr: dict[str, sp.Expr] = {}

    def ref(eid, field, allowed_types, where):
        target = (el.get(field))
        if not isinstance(target, str) or target not in ids:
            errors.append(f"{where}.{field}: unknown id {target!r}")
            return None
        if allowed_types and etype.get(target) not in allowed_types:
            errors.append(f"{where}.{field}: {target!r} must be one of {sorted(allowed_types)}")
        return target

    # ---- elements: expressions -----------------------------------------------------------------------------
    for el in elements:
        if not isinstance(el, dict) or el.get("id") not in etype:
            continue
        eid, typ = el["id"], etype[el["id"]]
        where = f"element {eid} ({typ})"

        def expr_here(field, var: str | None, required=True):
            val = el.get(field)
            if val is None:
                if required:
                    errors.append(f"{where}: missing {field}")
                return None
            allow = set(params) | ({var} if var else set())
            try:
                return check_expr(val, params, allow)
            except ExprError as er:
                errors.append(f"{where}.{field} {val!r}: {er}")
                return None

        if typ == "function":
            e = expr_here("expr", "x")
            lo, hi = xlo, xhi
            dom = el.get("domain")
            if dom is not None:
                if not (isinstance(dom, list) and len(dom) == 2):
                    errors.append(f"{where}.domain must be [a, b]")
                else:
                    vals = []
                    for d in dom:
                        try:
                            v = scalar_value(check_expr(d, params, set(params)), subs)
                            vals.append(v.real if v is not None else None)
                        except ExprError as er:
                            errors.append(f"{where}.domain {d!r}: {er}")
                            vals.append(None)
                    if all(v is not None for v in vals):
                        if vals[0] >= vals[1]:
                            errors.append(f"{where}.domain must be ordered")
                        else:
                            lo, hi = vals
            if e is not None:
                func_expr[eid] = e
                msg = sample_finite(e, "x", lo, hi, subs)
                if msg:
                    errors.append(f"{where}.expr: {msg}")
        elif typ == "parametric":
            ex, ey = expr_here("x_expr", "t"), expr_here("y_expr", "t")
            tr = el.get("t_range")
            if not (isinstance(tr, list) and len(tr) == 2):
                errors.append(f"{where}: t_range must be [a, b]")
            else:
                tv = []
                for d in tr:
                    try:
                        v = scalar_value(check_expr(d, params, set(params)), subs)
                        tv.append(v.real if v is not None else None)
                    except ExprError as er:
                        errors.append(f"{where}.t_range {d!r}: {er}")
                        tv.append(None)
                if all(v is not None for v in tv):
                    if tv[0] >= tv[1]:
                        errors.append(f"{where}.t_range must be ordered")
                    else:
                        for nm, e in (("x_expr", ex), ("y_expr", ey)):
                            if e is not None:
                                msg = sample_finite(e, "t", tv[0], tv[1], subs)
                                if msg:
                                    errors.append(f"{where}.{nm}: {msg}")
        elif typ == "point":
            for f in ("x", "y"):
                e = expr_here(f, None)
                if e is not None and scalar_value(e, subs) is None:
                    errors.append(f"{where}.{f}: not finite at the default params")
        elif typ == "glider":
            ref(eid, "on", GLIDER_HOSTS, where)
            e = expr_here("x", None, required=False)
            if e is not None and scalar_value(e, subs) is None:
                errors.append(f"{where}.x: not finite at the default params")
        elif typ in ("segment", "line", "vector"):
            for f in ("from", "to"):
                if el.get(f) is None:
                    errors.append(f"{where}: missing {f}")
                else:
                    _endpoint(el[f], f"{where}.{f}", params, ids, point_ids, errors, subs)
        elif typ in ("tangent", "normal"):
            ref(eid, "at", POINT_TYPES, where)
            ref(eid, "of", {"function"}, where)
        elif typ == "integral":
            if el.get("between") is not None:
                b = el["between"]
                if not (isinstance(b, list) and len(b) == 2):
                    errors.append(f"{where}.between must be [f, g]")
                else:
                    for fid in b:
                        if fid not in func_ids:
                            errors.append(f"{where}.between: {fid!r} is not a function element")
            elif el.get("of") is not None:
                ref(eid, "of", {"function"}, where)
            else:
                errors.append(f"{where}: needs 'of' or 'between'")
            vals = []
            for f in ("from", "to"):
                e = expr_here(f, None)
                v = scalar_value(e, subs) if e is not None else None
                if e is not None and v is None:
                    errors.append(f"{where}.{f}: not finite at the default params")
                vals.append(v.real if v is not None else None)
            if all(v is not None for v in vals) and vals[0] == vals[1]:
                warnings.append(f"{where}: from == to at the default params (zero area)")
            op = el.get("opacity")
            if op is not None and not (isinstance(op, (int, float)) and 0 <= op <= 1):
                errors.append(f"{where}.opacity must be in [0, 1]")
        elif typ == "circle":
            if el.get("centre") is None:
                errors.append(f"{where}: missing centre")
            else:
                _endpoint(el["centre"], f"{where}.centre", params, ids, point_ids, errors, subs)
            e = expr_here("radius", None)
            v = scalar_value(e, subs) if e is not None else None
            if e is not None and (v is None or v.real <= 0):
                errors.append(f"{where}.radius must be positive and finite at the default params")
        elif typ == "polygon":
            pts = el.get("points")
            if not (isinstance(pts, list) and len(pts) >= 3):
                errors.append(f"{where}: points needs at least 3 entries")
            else:
                for j, p in enumerate(pts):
                    _endpoint(p, f"{where}.points[{j}]", params, ids, point_ids, errors, subs)
        elif typ == "text":
            for f in ("x", "y"):
                e = expr_here(f, None)
                if e is not None and scalar_value(e, subs) is None:
                    errors.append(f"{where}.{f}: not finite at the default params")
            value = el.get("value")
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: value must be a non-empty string")
            else:
                # placeholders live outside $...$ (TeX braces are not placeholders)
                for m in PLACEHOLDER_RE.finditer(gate_style.spans(value)[1]):
                    inner = m.group(1).strip()
                    sm = SPECIAL_RE.match(inner)
                    if sm:
                        kind, tid = sm.groups()
                        if tid not in ids:
                            errors.append(f"{where}.value: unknown id in {{{inner}}}")
                        elif kind == "area" and etype.get(tid) != "integral":
                            errors.append(f"{where}.value: {{area({tid})}} needs an integral element")
                        elif kind in ("x", "y") and etype.get(tid) not in POINT_TYPES:
                            errors.append(f"{where}.value: {{{kind}({tid})}} needs a point or glider")
                    else:
                        try:
                            pe = check_expr(inner, params, set(params))
                            if scalar_value(pe, subs) is None:
                                errors.append(f"{where}.value placeholder {{{inner}}}: not finite at the default params")
                        except ExprError as er:
                            errors.append(f"{where}.value placeholder {{{inner}}}: {er}")
        elif typ in ("vline", "hline"):
            e = expr_here("at", None)
            if e is not None and scalar_value(e, subs) is None:
                errors.append(f"{where}.at: not finite at the default params")

    # ---- steps -------------------------------------------------------------------------------------------
    steps = scene.get("steps")
    if not isinstance(steps, list) or not 2 <= len(steps) <= 5:
        errors.append(f"steps must have 2 to 5 entries (has {len(steps) if isinstance(steps, list) else 'none'})")
        steps = steps if isinstance(steps, list) else []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errors.append(f"steps[{i}] is not an object")
            continue
        if not isinstance(s.get("text"), str) or not s["text"].strip():
            errors.append(f"steps[{i}]: text missing")
        if s.get("n") not in (None, i + 1):
            warnings.append(f"steps[{i}].n is {s.get('n')}, expected {i + 1}")
        for f in ("show", "hide", "highlight"):
            for tid in s.get(f) or []:
                if tid not in ids or ids[tid] == "param":
                    errors.append(f"steps[{i}].{f}: unknown element id {tid!r}")
        for k, v in (s.get("set") or {}).items():
            if k not in params:
                errors.append(f"steps[{i}].set: unknown param {k!r}")
                continue
            p = next(p for p in scene["params"] if p.get("id") == k)
            try:
                if not (float(p["min"]) <= float(v) <= float(p["max"])):
                    errors.append(f"steps[{i}].set.{k} = {v} outside [{p['min']}, {p['max']}]")
            except (TypeError, ValueError, KeyError):
                errors.append(f"steps[{i}].set.{k}: not a number")

    # ---- text: KaTeX, banned phrases, G7 -------------------------------------------------------------------
    texts = _texts_of(scene)
    guide = scene.get("guide")
    if guide is not None:
        texts += _guide_texts(guide)
    elif require_guide:
        errors.append("guide: missing (every scene must explain itself)")
    if not scene.get("title"):
        warnings.append("no title")
    if not scene.get("purpose"):
        warnings.append("no purpose")
    if scene.get("approach") not in APPROACHES:
        errors.append(f"approach must be one of {sorted(APPROACHES)}")
    batch, owners = [], []
    for name, t in texts:
        found, _outside = gate_style.spans(t)
        for tex, disp in found:
            batch.append((tex, disp))
            owners.append((name, tex))
        m = BANNED.search(t)
        if m:
            errors.append(f"{name}: banned phrase {m.group(0)!r}")
        if t.count("$") % 2:
            errors.append(f"{name}: unbalanced $")
    for (name, tex), err in zip(owners, gate_style.katex_errors(batch)):
        if err:
            errors.append(f"{name}: KaTeX cannot render ${tex}$: {err}")
    if g7 and not any(t.strip() for _n, t in texts):
        errors.append("G7 copy check: no text to check")
    elif g7:
        try:
            import gates  # noqa: WPS433  (loads the local corpus; ~3 s the first time)
            pseudo = {"stem": " ".join(t for n, t in texts if n in ("title", "purpose")),
                      "parts": [{"label": "scene", "marks": 0, "text": " ".join(t for n, t in texts if n.startswith("steps"))}],
                      "pitfalls": [{"text": " ".join(t for n, t in texts if n.startswith(("element", "guide")))}]}
            r = gates.g7_novelty(pseudo)
            if not r.get("pass"):
                errors.append("G7 copy check: " + "; ".join(r.get("reasons") or ["failed"])
                              + ("; reword these phrases: " + " | ".join(repr(g) for g in r["hits8"]) if r.get("hits8") else ""))
            for fl in r.get("flags") or []:
                warnings.append(f"G7 flag: {fl}")
        except Exception as ex:  # corpus missing: fail closed, as the other gates do
            errors.append(f"G7 copy check unavailable ({type(ex).__name__}: {str(ex).splitlines()[0] if str(ex) else ''})")

    # ---- links -------------------------------------------------------------------------------------------
    links = scene.get("links") or {}
    part_label = scene.get("part")
    if item:
        labels = [p.get("label") for p in item.get("parts") or []]
        if part_label is not None and part_label not in labels:
            errors.append(f"scene.part {part_label!r} is not a part of the item ({labels})")
        scheme = list(dict.fromkeys(_scheme_codes(item, part_label)))
        scheme_kinds = set()
        for c in scheme:
            m = marks.try_parse(c)
            if m:
                scheme_kinds.add((m.kind, m.worth))
        for c in links.get("marks") or []:
            m = marks.try_parse(str(c))
            if m is None:
                errors.append(f"links.marks: {c!r} is not a mark code")
            elif (m.kind, m.worth) not in scheme_kinds:
                errors.append(f"links.marks: {c!r} is not in the part's scheme {scheme}")
        codes = {pf.get("error_code") for pf in item.get("pitfalls") or []}
        for c in links.get("pitfalls") or []:
            if c not in codes:
                errors.append(f"links.pitfalls: {c!r} is not an error code of the item ({sorted(x for x in codes if x)})")
        parts = [p for p in item.get("parts") or [] if part_label is None or p.get("label") == part_label]
        n_steps = max([len(p.get("solution") or []) for p in parts] or [0])
        for s in links.get("solution_steps") or []:
            if not (isinstance(s, int) and 1 <= s <= n_steps):
                warnings.append(f"links.solution_steps: {s!r} is not a solution step number (1..{n_steps})")
        sid = scene.get("id") or ""
        if item.get("id") and not str(sid).startswith(str(item["id"])):
            warnings.append(f"scene.id {sid!r} does not start with the item id")
    elif links:
        warnings.append("links not checked: no item given")

    # ---- guide (spec §2 "Guide"): ids exist, coverage, part and marks match --------------------------------
    if guide is not None:
        scheme = list(dict.fromkeys(_scheme_codes(item, part_label))) if item else []
        check_guide(guide, elements, etype, params, scheme, part_label, bool(item), errors, warnings)

    return {"pass": not errors, "errors": errors, "warnings": warnings}


# ---- guide ------------------------------------------------------------------------------------------------
LEGEND_TYPES = {"integral", "glider", "tangent", "normal", "vector"}
INTERACT_KINDS = {"slider", "glider", "point"}


def _guide_texts(guide) -> list[tuple[str, str]]:
    """(name, text) pairs of every prose field of a guide block, for KaTeX, banned-word and G7 checks."""
    out: list[tuple[str, str]] = []
    if not isinstance(guide, dict):
        return out
    out.append(("guide.what_you_see", str(guide.get("what_you_see") or "")))
    for i, e in enumerate(guide.get("legend") or []):
        if isinstance(e, dict):
            out.append((f"guide.legend[{i}].meaning", str(e.get("meaning") or "")))
    for i, e in enumerate(guide.get("interact") or []):
        if isinstance(e, dict):
            out.append((f"guide.interact[{i}].do", str(e.get("do") or "")))
            out.append((f"guide.interact[{i}].watch", str(e.get("watch") or "")))
    ql = guide.get("question_link")
    if isinstance(ql, dict):
        out.append(("guide.question_link.text", str(ql.get("text") or "")))
    for i, line in enumerate(guide.get("read_off") or []):
        out.append((f"guide.read_off[{i}]", str(line or "")))
    return out


def guide_requirements(scene: dict) -> dict:
    """What a guide must cover for this scene (also fed to the annotator's user message):
    legend_ids: elements with a label or of a type whose meaning is not obvious (integral, glider, tangent, normal,
    vector) or a draggable point; controls: {id: kind} for every param (slider), glider and draggable point;
    live_texts: ids of text elements whose value has a live {...} placeholder."""
    legend, controls, live = [], {}, []
    for p in scene.get("params") or []:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            controls[p["id"]] = "slider"
    for el in scene.get("elements") or []:
        if not isinstance(el, dict) or not isinstance(el.get("id"), str):
            continue
        eid, typ = el["id"], el.get("type")
        draggable = typ == "point" and bool(el.get("draggable"))
        if el.get("label") or typ in LEGEND_TYPES or draggable:
            legend.append(eid)
        if typ == "glider":
            controls[eid] = "glider"
        elif draggable:
            controls[eid] = "point"
        if typ == "text" and PLACEHOLDER_RE.search(gate_style.spans(str(el.get("value") or ""))[1]):
            live.append(eid)
    return {"legend_ids": legend, "controls": controls, "live_texts": live}


def check_guide(guide, elements, etype: dict, params: set, scheme: list[str], part_label, have_item: bool,
                errors: list, warnings: list) -> None:
    if not isinstance(guide, dict):
        errors.append("guide: must be an object")
        return
    req = guide_requirements({"params": [{"id": p} for p in params], "elements": elements})
    if not isinstance(guide.get("what_you_see"), str) or len(guide["what_you_see"].strip()) < 20:
        errors.append("guide.what_you_see: missing or too short (one or two sentences)")
    # legend
    legend = guide.get("legend")
    if not isinstance(legend, list):
        errors.append("guide.legend: must be a list of {id, meaning}")
        legend = []
    seen: set[str] = set()
    for i, e in enumerate(legend):
        if not isinstance(e, dict):
            errors.append(f"guide.legend[{i}]: not an object")
            continue
        lid = e.get("id")
        if lid not in etype:
            errors.append(f"guide.legend[{i}].id: unknown element id {lid!r} (element ids: {sorted(etype)})")
        elif lid in seen:
            warnings.append(f"guide.legend: {lid!r} appears twice")
        seen.add(lid)
        if not isinstance(e.get("meaning"), str) or not e["meaning"].strip():
            errors.append(f"guide.legend[{i}] ({lid}): meaning missing")
    for lid in req["legend_ids"]:
        if lid not in seen:
            errors.append(f"guide.legend: no entry for element {lid!r} ({etype.get(lid)}), which needs one "
                          "(it has a label or is an integral/glider/draggable point/tangent/normal/vector)")
    # interact
    interact = guide.get("interact")
    if not isinstance(interact, list):
        errors.append("guide.interact: must be a list of {control, kind, do, watch}")
        interact = []
    covered: set[str] = set()
    for i, e in enumerate(interact):
        if not isinstance(e, dict):
            errors.append(f"guide.interact[{i}]: not an object")
            continue
        cid, kind = e.get("control"), e.get("kind")
        if cid not in req["controls"]:
            errors.append(f"guide.interact[{i}].control: {cid!r} is not a control of this scene "
                          f"(controls: {req['controls']})")
        else:
            covered.add(cid)
            if kind != req["controls"][cid]:
                errors.append(f"guide.interact[{i}] ({cid}): kind should be {req['controls'][cid]!r}, not {kind!r}")
        if kind not in INTERACT_KINDS:
            errors.append(f"guide.interact[{i}].kind: {kind!r} not in {sorted(INTERACT_KINDS)}")
        for f in ("do", "watch"):
            if not isinstance(e.get(f), str) or len(e[f].strip()) < 10:
                errors.append(f"guide.interact[{i}] ({cid}).{f}: missing or too short (say concretely what to do / what changes)")
    for cid, kind in req["controls"].items():
        if cid not in covered:
            errors.append(f"guide.interact: no entry for {kind} {cid!r}")
    # question_link
    ql = guide.get("question_link")
    if not isinstance(ql, dict):
        errors.append("guide.question_link: must be an object {part, marks, text}")
    else:
        if ql.get("part") != part_label:
            errors.append(f"guide.question_link.part: {ql.get('part')!r} does not match the scene's part {part_label!r}")
        if not isinstance(ql.get("text"), str) or len(ql["text"].strip()) < 20:
            errors.append("guide.question_link.text: missing or too short (say which object in the picture is which object in the question)")
        mk = ql.get("marks")
        if not isinstance(mk, list) or not mk:
            errors.append("guide.question_link.marks: list at least one code of the part's scheme")
            mk = []
        if have_item:
            kinds = {(m.kind, m.worth) for m in (marks.try_parse(c) for c in scheme) if m}
            for c in mk:
                m = marks.try_parse(str(c))
                if m is None:
                    errors.append(f"guide.question_link.marks: {c!r} is not a mark code")
                elif (m.kind, m.worth) not in kinds:
                    errors.append(f"guide.question_link.marks: {c!r} is not in the part's scheme {scheme}")
    # read_off
    ro = guide.get("read_off")
    if ro is None:
        ro = []
    if not isinstance(ro, list) or not all(isinstance(s, str) for s in ro):
        errors.append("guide.read_off: must be a list of strings")
        ro = []
    if len([s for s in ro if s.strip()]) < len(req["live_texts"]):
        errors.append(f"guide.read_off: {len(ro)} line(s) but the scene has {len(req['live_texts'])} live text "
                      f"element(s) {req['live_texts']}; give one line per live label")


def load_item(item_id: str) -> dict | None:
    p = ITEMS_DIR / f"{item_id}.json"
    return json.loads(p.read_text()) if p.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scenes", nargs="+", help="scene JSON files (a file may hold one scene or a list)")
    ap.add_argument("--item", help="item id for all scenes (default: the file's item_id, else scene.id before '::')")
    ap.add_argument("--no-g7", action="store_true", help="skip the G7 copy check (no corpus needed)")
    ap.add_argument("--require-guide", action="store_true", help="fail scenes that have no guide block")
    a = ap.parse_args()
    failed = 0
    for path in a.scenes:
        data = json.loads(Path(path).read_text())
        # a bare scene, a list of scenes, or the generator's envelope {"item_id", "scenes": [...]}
        envelope_item = data.get("item_id") if isinstance(data, dict) else None
        scenes = data["scenes"] if isinstance(data, dict) and "scenes" in data else data
        if isinstance(data, dict) and "scenes" in data and not scenes:
            print(f"SKIP  {path}  no scenes (applicable={data.get('applicable')})")
        for scene in (scenes if isinstance(scenes, list) else [scenes]):
            item_id = a.item or envelope_item or str(scene.get("id") or "").split("::")[0]
            item = load_item(item_id) if item_id else None
            if item_id and item is None:
                print(f"{path}: item {item_id!r} not found in {ITEMS_DIR}")
            r = gate_scene(scene, item, g7=not a.no_g7, require_guide=a.require_guide)
            status = "PASS" if r["pass"] else "FAIL"
            print(f"{status}  {path}  {scene.get('id')}  guide={'yes' if scene.get('guide') else 'no'}")
            for e in r["errors"]:
                print(f"   error: {e}")
            for w in r["warnings"]:
                print(f"   warn:  {w}")
            failed += not r["pass"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
