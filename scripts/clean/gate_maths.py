#!/usr/bin/env python3
"""G2 maths correctness: deterministic sympy checks on a generated item's answers (no model calls).

    .venv/bin/python scripts/clean/gate_maths.py ITEM.json [...]      # print results only

Each part may carry `answers` and `checks`. Every expression is a plain maths string parsed by sympy:
implicit multiplication (`2x`, `3 sin 2x`), `^` for powers, decimals read as exact rationals (0.3 = 3/10),
`e` = Euler's number, `log` = `ln` = natural log (`log(x, b)` for base b), `pi`, `oo`, `sqrt`, `abs`,
trig/inverse trig (`cosec`, `arcsin` accepted), `exp`, `binomial`, `factorial`. Equations use one `=`.

  answers  [{"name": "x", "expr": "3/2", "form": "exact"|"dp-N"|"sf-N"|..., "exact": "...", "check": "...",
             "degrees": false}]
           expr must parse. form "exact": no decimals in expr. form dp-N / sf-N: expr is a decimal written to
           exactly N decimal places / significant figures and, if `exact` is given, is its correct rounding.
           No form but `exact` given: expr must equal it (a decimal expr: its rounding to the places written).
           `check`: an equation the answers satisfy, e.g. "2x^2 - 3x = 0"; each answer whose name is a plain
           identifier is substituted (its `exact` if given). A rounded answer (a decimal, or dp-N / sf-N, with
           no `exact`) passes if the equation holds for some value within half a unit of its last written place
           (a sign change of lhs - rhs across that box, at most 4 rounded answers).
           Every answer must be verified: by `exact`, by its `check`, by a check with "answer": its name, or by
           equalling the `result` of some check in the part.
  checks   [{"type": ..., ...}]; any check may add "degrees": true (trig arguments in degrees, inverse trig
           returns degrees: arcsin(1/2) = 30). Numbers may be JSON numbers or strings ("0.30"). A `result`
           may be omitted when `"answer": "<answer name in this part>"` is given (that answer's expr and form).
           Comparing a value with a result: with a `form` (dp-N / sf-N) the result must be written to that
           accuracy and be the correct rounding; a decimal result with no form must be the correct rounding
           to the places written; anything else must be exactly equal (simplify, then random points).
    equals      lhs, rhs [, domain [a, b] for the random points]       lhs == rhs identically
    derivative  f, var ("x"), order (1), result                        d^n f / d var^n == result
    integral    f, var, [lower, upper], result [, form]                definite: value; indefinite: d(result) == f
    solutions   equation, var, result [...], interval [a, b], closed [true, true], form
                the full real solution set in the interval: a missing and an extra root both fail (roots at a
                closed end are found by evaluating the equation there exactly).
                No interval: polynomial / rational equations (or ones sympy solves to a finite set) only.
    system      equations [...], vars [...], result {var: value}       result is one solution of the system
                (result omitted: taken from the part's answers with those names)
    substitute  expr, at {var: value}, result [, form]
    numeric     expr, result [, form]                                  rounding check on a computed value
    binomial_cdf n (<= 1000), p, k, tail "le"|"lt"|"ge"|"gt"|"eq", result [, form]    X ~ B(n, p), exact sum
    normal      mean, sd (or var); either lower and/or upper -> P(lower < X < upper) = result,
                or prob, tail "le"|"lt" (lower tail) or "ge"|"gt" (upper tail) -> result is the x with that
                tail probability
Pass: every answer parses, meets its form and is verified; every check holds; there is at least one answer or
check; and every part verifies something, except a part whose command is explain / state / sketch /
write-down / comment, or a show-that / prove part with no answers and at least one check.
The input comes from a model, so parsing is locked down: a character allowlist, no `__`, attribute access,
keywords or unknown functions, no builtins in the eval namespace; work is bounded while parsing (constants
up to 10^400, power towers up to 6 deep, factorial / binomial arguments up to 1000); and every answer and
check runs in a worker subprocess with a wall-clock limit (TIME_LIMIT s), so the limit holds in any
thread. A time-out fails the item.
"""
import atexit
import json
import keyword
import math
import os
import random
import re
import select
import subprocess
import sys
import threading
import time
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (_token_splittable, convert_xor, function_exponentiation,
                                        implicit_application, implicit_multiplication, parse_expr, rationalize,
                                        split_symbols_custom, standard_transformations)

SUBSCRIPT_RE = re.compile(r"^[A-Za-z]+\d+$")  # x1, t2, ab12: one symbol, not x*1 (which raised NameError: Number)


def _splittable(name: str) -> bool:
    """sympy's default splits 'xy' -> x*y; keep that, but never split letter(s)+digits subscripted names."""
    return not SUBSCRIPT_RE.match(name) and _token_splittable(name)


# = implicit_multiplication_application, with its split_symbols step using our predicate
TRANSFORMS = standard_transformations + (convert_xor, split_symbols_custom(_splittable), implicit_multiplication,
                                         implicit_application, function_exponentiation, rationalize)
FUNCS = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "sec": sp.sec, "csc": sp.csc, "cosec": sp.csc,
         "cot": sp.cot, "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "arcsin": sp.asin,
         "arccos": sp.acos, "arctan": sp.atan, "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
         "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "abs": sp.Abs, "Abs": sp.Abs,
         "floor": sp.floor, "ceiling": sp.ceiling}
CONSTS = {"pi": sp.pi, "e": sp.E, "E": sp.E, "oo": sp.oo}
GLOBALS = {"__builtins__": {}, "Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float,
           "Rational": sp.Rational, "Function": sp.Function,
           "Add": sp.Add, "Mul": sp.Mul, "Pow": sp.Pow}  # the last three for parse_expr(evaluate=False)
SAFE_CHARS = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]*$")
BAD_DOT = re.compile(r"[A-Za-z_)]\s*\.|\.(?!\d)")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DEC_RE = re.compile(r"^\s*-?(\d*)(?:\.(\d+))?\s*$")
FORM_RE = re.compile(r"^(dp|sf)-(\d+)$")
MAX_LEN, MAX_POW, MAX_FACT, MAX_SIZE, MAX_DEPTH, TIME_LIMIT = 400, 1000, 1000, 400, 6, 10
EXEMPT_COMMANDS = {"explain", "state", "sketch", "write-down", "comment"}


def _capped(fn):
    """factorial / binomial that refuse huge numeric arguments (they evaluate while parsing)."""
    def call(*args, **kw):
        if any(sp.sympify(a).is_number and abs(complex(sp.sympify(a).evalf(15))) > MAX_FACT for a in args):
            raise ValueError(f"{fn.__name__} argument too large")
        return fn(*args, **kw)
    return call


FUNCS.update(factorial=_capped(sp.factorial), binomial=_capped(sp.binomial))
TRIG, INV_TRIG = {"sin", "cos", "tan", "sec", "csc", "cosec", "cot"}, {"asin", "acos", "atan", "arcsin", "arccos", "arctan"}


def _in_degrees(name: str, fn):
    if name in TRIG:
        return lambda a, **kw: fn(a * sp.pi / 180, **kw)
    return lambda a, **kw: fn(a, **kw) * 180 / sp.pi


DEG_FUNCS = {**FUNCS, **{n: _in_degrees(n, f) for n, f in FUNCS.items() if n in TRIG | INV_TRIG}}


# ---- safe parsing ----------------------------------------------------------------------------
def _guard(s: str) -> None:
    if not isinstance(s, str) or not s.strip():
        raise ValueError(f"not an expression: {s!r}")
    if len(s) > MAX_LEN or not SAFE_CHARS.match(s) or "__" in s or BAD_DOT.search(s) or re.search(r"\d{16,}", s):
        raise ValueError(f"not a plain maths expression: {s[:60]!r}")
    for name in NAME_RE.findall(s):
        if name.startswith("_") or keyword.iskeyword(name) or len(name) > 12:
            raise ValueError(f"name {name!r} not allowed in {s[:60]!r}")


def _size(e: sp.Basic, depth: int = 0) -> float:
    """Upper bound on |log10 |value|| of an unevaluated constant subtree (symbols count as 1); raises
    ValueError when evaluating it would build a number beyond 10^MAX_SIZE or a power tower too deep."""
    if depth > MAX_DEPTH:
        raise ValueError("powers nested too deeply")
    if e.is_Rational:
        s = max(abs(e.p).bit_length(), abs(e.q).bit_length()) * 0.30103
        if s > MAX_SIZE:  # e.g. factorial(1000), evaluated while parsing
            raise ValueError("number too large")
        return s
    if not e.args:
        return 1.0
    if isinstance(e, sp.Pow):
        b, x = e.args
        sb, sx = _size(b, depth + 1), _size(x, depth + 1)
        if x.free_symbols:
            return sb + 1
        if sx > 6:
            raise ValueError("exponent too large")
        xv = abs(complex(x.evalf(15)))
        if b.free_symbols and xv > MAX_POW:
            raise ValueError("exponent too large")
        s = xv * sb
    elif isinstance(e, sp.exp) and not e.free_symbols and _size(e.args[0], depth + 1) <= 6:
        s = abs(complex(e.args[0].evalf(15))) / 2.3
    else:
        kids = [_size(a, depth) for a in e.args]
        s = sum(kids) if isinstance(e, sp.Mul) else max(kids) + 1
    if s > MAX_SIZE:
        raise ValueError("number too large")
    return s


def parse(s, degrees: bool = False) -> sp.Expr:
    """A pure maths expression; raises ValueError for anything else."""
    s = str(s) if isinstance(s, (int, float)) and not isinstance(s, bool) else s
    _guard(s)
    kw = dict(local_dict={**(DEG_FUNCS if degrees else FUNCS), **CONSTS}, global_dict=dict(GLOBALS),
              transformations=TRANSFORMS)
    try:
        _size(parse_expr(s, evaluate=False, **kw))  # refuse 9^9^9 or (9999^999)^999 before evaluating
        e = parse_expr(s, **kw)
    except ValueError:
        raise
    except Exception as ex:  # SyntaxError, TypeError, TokenError ...
        raise ValueError(f"does not parse: {s[:60]!r} ({type(ex).__name__})") from None
    if not isinstance(e, sp.Expr) or e.atoms(sp.core.function.AppliedUndef):
        raise ValueError(f"not a plain maths expression (unknown function?): {s[:60]!r}")
    return e


def _int(v) -> int:
    e = parse(v)
    if not e.is_Integer:
        raise ValueError(f"{v!r} is not an integer")
    return int(e)


def parse_eq(s: str, degrees: bool = False) -> sp.Expr:
    """'lhs = rhs' (or an expression meaning = 0) -> lhs - rhs."""
    if not isinstance(s, str) or s.count("=") > 1:
        raise ValueError(f"an equation needs at most one '=': {s!r}")
    lhs, _, rhs = s.partition("=")
    return parse(lhs, degrees) - (parse(rhs, degrees) if rhs.strip() else 0)


# ---- values, rounding, equality --------------------------------------------------------------
def _dec(v: sp.Expr) -> Decimal:
    z = complex(sp.N(v, 50))
    if abs(z.imag) > 1e-12 * max(1.0, abs(z.real)):
        raise ValueError(f"value {v} is not real")
    return Decimal(str(sp.Float(sp.re(sp.N(v, 50)), 50)))


def round_to(v: sp.Expr, form: str) -> Decimal:
    kind, n = FORM_RE.match(form).groups()
    d, n = _dec(v), int(n)
    if kind == "sf":
        if d == 0:
            return Decimal(0)
        n = n - d.adjusted() - 1
    return d.quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP)


def written_to(lit: str, form: str) -> bool:
    """Is the decimal literal written to exactly this many dp / sf?"""
    m = DEC_RE.match(lit or "")
    if not m or not (m.group(1) or m.group(2)):
        return False
    kind, n = FORM_RE.match(form).groups()
    whole, frac, n = m.group(1), m.group(2) or "", int(n)
    if kind == "dp":
        return len(frac) == n
    digits = (whole + frac).lstrip("0")
    if frac:
        return len(digits) == n or (not digits and len(frac) == n)  # 0.000 counts its zeros
    return len(digits.rstrip("0")) <= n <= len(digits)  # 1500 could be 2, 3 or 4 sf


def is_decimal(lit) -> bool:
    return isinstance(lit, (str, float)) and "." in str(lit) and bool(DEC_RE.match(str(lit)))


def equal(a: sp.Expr, b: sp.Expr, domain=(0.3, 2.7)) -> bool:
    d = a - b
    try:
        if sp.simplify(d) == 0:
            return True
    except Exception:
        pass
    syms = sorted(d.free_symbols, key=str)
    if d.is_Rational:
        return d == 0
    if not syms:  # other constants: 50 digits, no loose tolerance
        dv, av = complex(sp.N(d, 50)), complex(sp.N(a, 50))
        return all(map(math.isfinite, (dv.real, dv.imag))) and abs(dv) <= 1e-30 * (1 + abs(av))
    rng, ok = random.Random(0), 0
    for _ in range(12):
        sub = {s: sp.Rational(rng.uniform(*domain)).limit_denominator(10**6) for s in syms}
        try:
            dv, av = complex(sp.N(d.subs(sub), 30)), complex(sp.N(a.subs(sub), 30))
        except (TypeError, ValueError):
            continue
        if not all(map(math.isfinite, (dv.real, dv.imag, av.real, av.imag))):
            continue
        if abs(dv) > 1e-9 * (1 + abs(av)):
            return False
        ok += 1
    return ok >= 3


def matches(value: sp.Expr, result, form: str | None = None, degrees: bool = False) -> str | None:
    """None if `result` is the right value (rounded per `form`, or to the places written), else why not."""
    lit = str(result).strip() if result is not None else ""
    if not lit:
        return "no result given"
    if form and FORM_RE.match(form):
        if not written_to(lit, form):
            return f"result {lit} is not written to {form}"
        want = round_to(value, form)
        return None if Decimal(lit) == want else f"result {lit}, but {sp.N(value, 8)} to {form} is {want}"
    if is_decimal(lit):
        form = f"dp-{len(lit.split('.')[1])}"
        want = round_to(value, form)
        return None if Decimal(lit) == want else f"result {lit}, but {sp.N(value, 8)} to {form} is {want}"
    return None if equal(value, parse(lit, degrees)) else f"result {lit} != computed {_short(value)}"


def _short(v) -> str:
    t = str(sp.simplify(v))
    return t if len(t) <= 80 else f"{sp.N(v, 12)} (approx.)" if not getattr(v, "free_symbols", None) else t[:80] + "..."


# ---- checks ----------------------------------------------------------------------------------
def _sym(c: dict, key: str = "var") -> sp.Symbol:
    v = c.get(key, "x")
    if not isinstance(v, str) or not IDENT_RE.match(v):
        raise ValueError(f"bad variable {v!r}")
    return sp.Symbol(v)


def _real_roots(f: sp.Expr, x: sp.Symbol, lo, hi, closed) -> list[float] | None:
    """Real roots of f in [lo, hi] (None, None: all reals). Exact for polynomial / rational f, else a
    dense numeric scan (sign changes plus touching roots) refined by bisection / golden section."""
    num, den = sp.fraction(sp.together(f))
    roots = None
    if num.is_polynomial(x) and den.is_polynomial(x) and not (num.free_symbols | den.free_symbols) - {x}:
        if sp.expand(num) == 0:
            raise ValueError("equation is an identity")
        roots = [float(r) for r in sp.Poly(num, x).real_roots() if den.subs(x, r) != 0] if num.has(x) else []
    elif lo is None:
        sol = sp.solveset(f, x, sp.S.Reals)
        if not isinstance(sol, sp.FiniteSet):
            raise ValueError("cannot list all solutions without an interval")
        roots = [float(r) for r in sol]
    if roots is None:
        roots = _scan(f, x, float(lo), float(hi))
    if lo is not None:
        for end, shut in ((lo, closed[0]), (hi, closed[1])):  # the scan can miss a root exactly at an end
            try:
                v = complex(sp.N(f.subs(x, end), 30))
            except Exception:
                continue
            if shut and math.isfinite(abs(v)) and abs(v) < 1e-10:
                roots.append(float(end))
        eps = 1e-9 * max(1.0, abs(float(hi) - float(lo)))
        a, b = float(lo), float(hi)
        roots = [r for r in roots if (a - eps <= r <= b + eps)
                 and not (not closed[0] and abs(r - a) <= eps) and not (not closed[1] and abs(r - b) <= eps)]
    out = []
    for r in sorted(roots):
        if not out or abs(r - out[-1]) > 1e-7 * max(1.0, abs(r)):
            out.append(r)
    return out


def _scan(f: sp.Expr, x: sp.Symbol, a: float, b: float, n: int = 20001) -> list[float]:
    fn = sp.lambdify(x, f, "numpy")

    def ev(t):
        with np.errstate(all="ignore"):
            y = np.asarray(fn(t), dtype=complex) * np.ones_like(t, dtype=float)
        return np.where(np.abs(y.imag) < 1e-9, y.real, np.nan)
    xs = np.linspace(a, b, n)
    ys = ev(xs)
    tol = 1e-8 * max(1.0, float(np.nanmedian(np.abs(ys))) if np.isfinite(ys).any() else 1.0)
    one = lambda t: float(ev(np.array([t]))[0])
    roots = [float(t) for t, y in zip(xs, ys) if y == 0]
    for i in range(n - 1):
        y0, y1 = ys[i], ys[i + 1]
        if np.isfinite(y0) and np.isfinite(y1) and y0 * y1 < 0:  # sign change: bisect, reject poles
            l, r = xs[i], xs[i + 1]
            for _ in range(80):
                m = (l + r) / 2
                if one(l) * one(m) <= 0:
                    r = m
                else:
                    l = m
            if abs(one((l + r) / 2)) < 1e-6 * max(1.0, abs(y0), abs(y1)):
                roots.append((l + r) / 2)
        if 0 < i and all(np.isfinite([ys[i - 1], y0, y1])) and abs(y0) < min(abs(ys[i - 1]), abs(y1)) \
                and ys[i - 1] * y0 > 0 and y0 * y1 > 0 and abs(y0) < 1e-2:  # touching root: minimise |f|
            l, r, g = xs[i - 1], xs[i + 1], (math.sqrt(5) - 1) / 2
            for _ in range(100):
                c, d = r - g * (r - l), l + g * (r - l)
                if abs(one(c)) < abs(one(d)):
                    r = d
                else:
                    l = c
            if abs(one((l + r) / 2)) < tol:
                roots.append((l + r) / 2)
    return roots


def _check_solutions(c: dict) -> str | None:
    deg, x = bool(c.get("degrees")), _sym(c)
    f = parse_eq(c.get("equation"), deg)
    iv = c.get("interval")
    lo, hi = (parse(iv[0]), parse(iv[1])) if iv else (None, None)
    closed = c.get("closed") if isinstance(c.get("closed"), list) and len(c["closed"]) == 2 else [True, True]
    got = _real_roots(f, x, lo, hi, [bool(v) for v in closed])
    want = c.get("result")
    if not isinstance(want, list):
        return "result must be a list of solutions"
    unmatched, extra = list(got), []
    for w in want:
        dec = is_decimal(w)
        near = lambda g: (matches(sp.Float(g, 15), w, c.get("form")) is None if dec
                          else abs(float(parse(w)) - g) < 1e-6 * max(1.0, abs(g)))
        hit = next((g for g in unmatched if near(g)), None)
        if hit is None:
            extra.append(str(w))
        else:
            unmatched.remove(hit)
    errs = ([f"missing solution(s) {', '.join(f'{g:.6g}' for g in unmatched)}"] if unmatched else []) + \
           ([f"extra or wrong solution(s) {', '.join(extra)}"] if extra else [])
    return "; ".join(errs) or None


def _check(c: dict, answers: dict) -> str | None:
    t, deg = c.get("type"), bool(c.get("degrees"))
    if "answer" in c:
        a = answers.get(c["answer"])
        if a is None:
            return f"names answer {c['answer']!r}, not in this part"
        if t != "system":
            c = {"form": a.get("form"), **c, "result": c.get("result", a.get("expr"))}
            if c["result"] != a.get("expr"):
                return f"result {c['result']} differs from answer {c['answer']} = {a.get('expr')}"
    form = c.get("form") if FORM_RE.match(str(c.get("form"))) else None
    P = lambda k: parse(c.get(k), deg)
    if t == "equals":
        d = c.get("domain")  # [a, b], or the words "positive" / "negative"
        dom = (-2.7, -0.3) if d == "negative" else tuple(float(parse(v)) for v in d) \
            if isinstance(d, list) and len(d) == 2 else (0.3, 2.7)
        return None if equal(P("lhs"), P("rhs"), dom) else f"{c['lhs']} != {c['rhs']}"
    if t == "derivative":
        d = sp.diff(P("f"), _sym(c), _int(c.get("order", 1)))
        return None if equal(d, P("result")) else f"derivative is {_short(d)}, not {c.get('result')}"
    if t == "integral":
        f, x = P("f"), _sym(c)
        if c.get("lower") is None and c.get("upper") is None:
            return None if equal(sp.diff(P("result"), x), f) else f"d/d{x} of {c.get('result')} is not {f}"
        v = sp.integrate(f, (x, P("lower"), P("upper")))
        if v.has(sp.Integral):
            v = sp.Integral(f, (x, P("lower"), P("upper"))).evalf(30)
        return matches(v, c.get("result"), form, deg)
    if t == "solutions":
        return _check_solutions(c)
    if t == "system":
        vs = [sp.Symbol(v) for v in c.get("vars") or [] if IDENT_RE.match(v)]
        want = c.get("result") or {v: answers[v]["expr"] for v in c.get("vars") or [] if v in answers}
        if not vs or len(vs) != len(c.get("vars")) or set(want) != set(c["vars"]):
            return "system needs vars and a result (or answers) for each"
        sols = sp.solve([parse_eq(e, deg) for e in c.get("equations") or []], vs, dict=True)
        for s in sols:
            if all(s.get(v) is not None and matches(s[v], want[str(v)], form, deg) is None for v in vs):
                return None
        return f"no solution of the system matches {want} (solutions: {sols})"
    if t == "substitute":
        at = {_sym({"var": k}): parse(v, deg) for k, v in (c.get("at") or {}).items()}
        return matches(P("expr").subs(at), c.get("result"), form, deg)
    if t == "numeric":
        return matches(P("expr"), c.get("result"), form, deg)
    if t == "binomial_cdf":
        n, k, p = _int(c["n"]), _int(c["k"]), parse(c["p"])
        ks = {"le": range(0, k + 1), "lt": range(0, k), "ge": range(k, n + 1), "gt": range(k + 1, n + 1),
              "eq": [k]}.get(c.get("tail", "le"))
        if ks is None or not 0 <= k <= n or n > 1000:
            return "bad n, k or tail"
        return matches(sum(sp.binomial(n, i) * p**i * (1 - p)**(n - i) for i in ks), c.get("result"), form)
    if t == "normal":
        mu = parse(c["mean"])
        sd = parse(c["sd"]) if c.get("sd") is not None else sp.sqrt(parse(c["var"]))
        phi = lambda z: (1 + sp.erf((z - mu) / (sd * sp.sqrt(2)))) / 2
        if c.get("prob") is not None:
            tail = c.get("tail", "le")
            if tail not in ("le", "lt", "ge", "gt"):
                return f"tail {tail!r}: use le / lt (lower tail) or ge / gt (upper tail)"
            q = parse(c["prob"]) if tail in ("le", "lt") else 1 - parse(c["prob"])
            return matches(mu + sd * sp.sqrt(2) * sp.erfinv(2 * q - 1), c.get("result"), form)
        lo = phi(P("lower")) if c.get("lower") is not None else 0
        hi = phi(P("upper")) if c.get("upper") is not None else 1
        return matches(hi - lo, c.get("result"), form)
    return f"unknown check type {t!r}"


def _half_unit(lit: str, form: str | None) -> sp.Rational:
    """Half a unit in the last place a rounded answer is written to (1500 to 2 sf: 50)."""
    m = FORM_RE.match(form or "")
    if m and m.group(1) == "sf" and "." not in lit:
        return sp.Rational(1, 2) * sp.Integer(10) ** (Decimal(lit).adjusted() - int(m.group(2)) + 1)
    return sp.Rational(1, 2) / sp.Integer(10) ** len(lit.partition(".")[2])


def _holds(check: str, answers: dict, deg: bool) -> str | None:
    """None if the answers satisfy `check` (exactly, or within their rounding), else why not."""
    exact, boxes = {}, {}
    for n, x in answers.items():
        if not IDENT_RE.match(n) or x.get("expr") is None:
            continue
        lit, d = str(x.get("expr")).strip(), deg or bool(x.get("degrees"))
        if x.get("exact") is not None:
            exact[sp.Symbol(n)] = parse(x["exact"], d)
        elif is_decimal(lit) or FORM_RE.match(str(x.get("form"))):
            boxes[sp.Symbol(n)] = (parse(lit), _half_unit(lit, x.get("form")))
        else:
            exact[sp.Symbol(n)] = parse(lit, d)
    g = parse_eq(check, deg).subs(exact)
    if g.free_symbols - set(boxes):
        return f"check {check!r} still has unknowns {sorted(map(str, g.free_symbols - set(boxes)))}"
    boxes = {v: b for v, b in boxes.items() if v in g.free_symbols}
    if not boxes:
        return None if equal(g, sp.Integer(0)) else f"answers do not satisfy {check!r}"
    if len(boxes) > 4:
        return f"check {check!r}: more than 4 rounded answers; give exact values"
    pts = [{v: c for v, (c, _) in boxes.items()}]
    for signs in range(2 ** len(boxes)):
        pts.append({v: c + (h if signs >> i & 1 else -h) for i, (v, (c, h)) in enumerate(boxes.items())})
    vals = [complex(sp.N(g.subs(pt), 30)) for pt in pts]
    real = [v.real for v in vals if abs(v.imag) < 1e-12 and math.isfinite(v.real)]
    if real and (min(real) <= 0 <= max(real)):
        return None
    return f"answers do not satisfy {check!r}, even allowing for their rounding (give exact values)"


def _results(c: dict) -> list:
    """Values a check establishes: its result(s), or either side of an `equals` check (which it proves)."""
    if c.get("type") == "equals":
        return [x for x in (c.get("lhs"), c.get("rhs")) if x is not None]
    r = c.get("result")
    return list(r) if isinstance(r, list) else list(r.values()) if isinstance(r, dict) else [r] if r is not None else []


def _same(a, b) -> bool:
    x, y = str(a).strip(), str(b).strip()
    if x == y:
        return True
    try:
        if is_decimal(x) or is_decimal(y):
            return Decimal(x) == Decimal(y)
        return equal(parse(x), parse(y))
    except Exception:
        return False


def _check_answer(a: dict, answers: dict, checks: list | None = None) -> tuple[list[str], bool]:
    """(errors, verified) for one answer."""
    errs, s, form, deg = [], a.get("expr"), a.get("form"), bool(a.get("degrees"))
    try:
        parse(s, deg)
    except ValueError as ex:
        return [str(ex)], False
    if form == "exact" and re.search(r"\d?\.\d", str(s)):
        errs.append(f"form exact, but {s} is a decimal")
    if form and FORM_RE.match(form) and not written_to(str(s), form):
        errs.append(f"{s} is not written to {form}")
    if a.get("exact") is not None:
        why = matches(parse(a["exact"], deg), s, form if form and FORM_RE.match(form) else None, deg)
        if why:
            errs.append(f"not the value of exact {a['exact']}: {why}")
    if a.get("check"):
        why = _holds(str(a["check"]), answers, deg)
        if why:
            errs.append(why)
    checks = [c for c in checks or [] if isinstance(c, dict)]
    verified = a.get("exact") is not None or bool(a.get("check")) \
        or any(c.get("answer") == a.get("name") for c in checks) \
        or any(_same(s, r) for c in checks for r in _results(c))
    return errs, verified


# ---- isolation: every answer / check runs in a worker subprocess with a wall-clock limit -------------
def _job(kind: str, payload: dict, answers: dict, checks: list) -> tuple[list[str], bool]:
    try:
        if kind == "answer":
            return _check_answer(payload, answers, checks)
        why = _check(payload, answers) if isinstance(payload, dict) else "not an object"
        return ([why] if why else []), True
    except Exception as ex:
        return [f"{type(ex).__name__}: {ex}"], False


class _Worker:
    """`python gate_maths.py --worker`: one JSON line per job on stdin, one JSON line back. A plain
    subprocess (not multiprocessing), so it never re-imports the caller's main module."""

    def __init__(self):
        self.proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.buf = b""
        try:
            ok = self.read(120) == "ready"
        except (TimeoutError, EOFError):
            ok = False
        if not ok:
            self.kill()
            raise RuntimeError("G2 worker process did not start")

    def ask(self, job: tuple, timeout: float):
        self.proc.stdin.write(json.dumps(job).encode() + b"\n")
        self.proc.stdin.flush()
        return self.read(timeout)

    def read(self, timeout: float):
        deadline, fd = time.monotonic() + timeout, self.proc.stdout.fileno()
        while b"\n" not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([fd], [], [], left)[0]:
                raise TimeoutError
            chunk = os.read(fd, 1 << 16)
            if not chunk:
                raise EOFError
            self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return json.loads(line)

    def kill(self) -> None:
        self.proc.kill()
        self.proc.wait()


def _serve() -> None:
    out, sys.stdout = sys.stdout, sys.stderr  # stray prints must not corrupt the channel
    out.write('"ready"\n')
    out.flush()
    for line in sys.stdin:
        out.write(json.dumps(_job(*json.loads(line))) + "\n")
        out.flush()


_IDLE: list[_Worker] = []
_LOCK = threading.Lock()
atexit.register(lambda: [w.kill() for w in _IDLE])


def run_job(job: tuple, isolate: bool = True) -> tuple[list[str], bool]:
    if not isolate:
        return _job(*job)
    with _LOCK:
        w = _IDLE.pop() if _IDLE else None
    if w is None or w.proc.poll() is not None:
        w = _Worker()
    try:
        errs, ok = w.ask(job, TIME_LIMIT)
    except TimeoutError:
        w.kill()
        return [f"timed out after {TIME_LIMIT} s"], False
    except (EOFError, OSError, ValueError):
        w.kill()
        return ["G2 worker process died"], False
    with _LOCK:
        _IDLE.append(w)
    return errs, ok


def g2_maths(item: dict, isolate: bool = True) -> dict:
    """isolate=False runs in this process with no time limit (debugging only)."""
    errs, n_checks, n_answers, unverified = [], 0, 0, []
    for p in item.get("parts") or []:
        where, label = f"part {p.get('label') or '-'}", p.get("label") or "-"
        ans_list = [a for a in p.get("answers") or [] if isinstance(a, dict)]
        checks = list(p.get("checks") or [])
        answers = {str(a.get("name")): a for a in ans_list}
        n_answers += len(p.get("answers") or [])
        n_checks += len(checks)
        n_verified = 0
        for a in ans_list:
            e, ok = run_job(("answer", a, answers, checks), isolate)
            errs += [f"{where} answer {a.get('name')}: {x}" for x in e]
            if not ok and not e:
                errs.append(f"{where} answer {a.get('name')}: not verified (give exact, a check, or a check with "
                            f"\"answer\": \"{a.get('name')}\")")
            n_verified += ok
        for i, c in enumerate(checks, 1):
            e, _ = run_job(("check", c, answers, checks), isolate)
            errs += [f"{where} check {i} ({c.get('type') if isinstance(c, dict) else '?'}): {x}" for x in e]
        cmd = p.get("command")
        proof = not ans_list and cmd in ("show-that", "prove") and any(isinstance(c, dict) for c in checks)
        if not n_verified and not proof:
            unverified.append(label)
            if cmd not in EXEMPT_COMMANDS and not ans_list:
                errs.append(f"{where}: nothing verified (no answers; a {cmd or 'part'} part needs answers, or for "
                            "show-that / prove at least one check)")
    if not (n_checks or n_answers):
        errs.append("no verifiable answers")
    return {"pass": not errs, "errors": errs, "n_checks": n_checks, "n_answers": n_answers,
            "unverified_parts": unverified}


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    _serve()
elif __name__ == "__main__":
    bad = 0
    for path in sys.argv[1:]:
        r = g2_maths(json.loads(Path(path).read_text(), parse_float=str))
        bad += not r["pass"]
        print(f"{Path(path).name}: G2 {'PASS' if r['pass'] else 'FAIL'} ({r['n_answers']} answers, {r['n_checks']} checks)")
        for e in r["errors"]:
            print(f"    {e}")
    sys.exit(1 if bad else 0)
