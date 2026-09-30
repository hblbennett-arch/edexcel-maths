#!/usr/bin/env python3
"""Self-test for G2 maths (scripts/clean/gate_maths.py) and G8 style (scripts/clean/gate_style.py).

    .venv/bin/python -m eval.gates_maths_style_selftest

The originals in eval/fixtures/original_items.json must pass both gates; each planted fault (a broken copy
of an original) must fail the gate it targets. Reads no Pearson text (G8 reads only content/facts/).
"""
import copy
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import gate_maths  # noqa: E402
from gate_maths import g2_maths  # noqa: E402
from gate_style import g8_style  # noqa: E402

FIXTURES = ROOT / "eval" / "fixtures" / "original_items.json"
OUR_RUBRIC = "You must show detailed reasoning; answers from a calculator alone will not score marks."


def edit(item: dict, fn) -> dict:
    x = copy.deepcopy(item)
    fn(x)
    return x


def g2_faults(cubic: dict, binom: dict, pulley: dict) -> list[tuple[str, dict]]:
    a, b = (lambda x: x["parts"][0]), (lambda x: x["parts"][1])
    trig = {"type": "solutions", "equation": "2 sin(x) = 1", "var": "x", "interval": ["0", "360"], "degrees": True}
    return [
        ("wrong derivative", edit(cubic, lambda x: a(x)["checks"].__setitem__(0, {
            "type": "derivative", "f": "2x^3 - 15x^2 + 36x - 20", "var": "x", "result": "6x^2 - 30x + 30"}))),
        ("answer disagrees with its linked check", edit(cubic, lambda x: a(x)["answers"][0].update(expr="6x^2 - 30x"))),
        ("missing root", edit(cubic, lambda x: b(x)["checks"][0].update(result=["2"]))),
        ("extra root", edit(cubic, lambda x: b(x)["checks"][0].update(result=["2", "3", "5"]))),
        ("missing root in a trig interval", edit(cubic, lambda x: b(x)["checks"].append({**trig, "result": ["30"]}))),
        ("extra root in a trig interval", edit(cubic, lambda x: b(x)["checks"].append({**trig, "result": ["30", "150", "210"]}))),
        ("wrong substitution", edit(cubic, lambda x: b(x)["answers"][1].update(expr="9"))),
        ("wrong rounding", edit(pulley, lambda x: a(x)["answers"][0].update(expr="2.46"))),
        ("not written to its form", edit(pulley, lambda x: a(x)["answers"][0].update(expr="2.450"))),
        ("numeric rounded wrongly", edit(pulley, lambda x: a(x)["checks"].append(
            {"type": "numeric", "expr": "sqrt(6)", "result": "2.44", "form": "sf-3"}))),
        ("system result wrong", edit(pulley, lambda x: a(x)["checks"][0]["result"].update(T="15.7"))),
        ("answer fails its check equation", edit(pulley, lambda x: b(x)["answers"][0].update(check="2 * 9.8 - T = 3 * 2.45"))),
        ("wrong binomial probability", edit(binom, lambda x: b(x)["answers"][0].update(expr="0.0322"))),
        ("binomial wrong tail", edit(binom, lambda x: b(x)["checks"][0].update(tail="lt"))),
        ("wrong normal probability", edit(binom, lambda x: b(x)["checks"].append(
            {"type": "normal", "mean": "50", "sd": "4", "upper": "54", "result": "0.8512", "form": "dp-4"}))),
        ("wrong definite integral", edit(cubic, lambda x: a(x)["checks"].append(
            {"type": "integral", "f": "3x^2", "var": "x", "lower": "0", "upper": "2", "result": "6"}))),
        ("exact answer given as a decimal", edit(cubic, lambda x: b(x)["answers"][0].update(expr="2.0"))),
        ("injection in an answer", edit(cubic, lambda x: a(x)["answers"][0].update(expr="__import__('os')"))),
        ("injection in a check", edit(cubic, lambda x: a(x)["checks"].append(
            {"type": "equals", "lhs": "x.__class__.__base__", "rhs": "1"}))),
        ("huge power", edit(cubic, lambda x: a(x)["checks"].append({"type": "numeric", "expr": "9^9^9", "result": "1"}))),
        ("no answers or checks", edit(cubic, lambda x: [p.pop(k, None) for p in x["parts"] for k in ("answers", "checks")])),
        ("unverified answer", edit(cubic, lambda x: a(x)["answers"].append({"name": "z", "expr": "7/3"}))),
        ("find part with nothing verified", edit(cubic, lambda x: [a(x).pop(k) for k in ("answers", "checks")])),
        ("factorial(10000)^500", edit(cubic, lambda x: a(x)["checks"].append(
            {"type": "numeric", "expr": "factorial(10000)^500", "result": "1"}))),
        ("power tower ((9999^999)^999)^999", edit(cubic, lambda x: a(x)["checks"].append(
            {"type": "numeric", "expr": "((9999^999)^999)^999", "result": "1"}))),
        ("closed-interval endpoint root omitted", edit(cubic, lambda x: b(x)["checks"].append(
            {**trig, "equation": "sin(x) = 0", "result": ["0", "180"]}))),
        ("rounded answer fails its check (99.7^2 = 10000)", edit(pulley, lambda x: b(x)["answers"].append(
            {"name": "x", "expr": "99.7", "form": "sf-3", "check": "x^2 = 10000"}))),
        ("degrees arcsin given in radians", edit(cubic, lambda x: a(x)["checks"].append(
            {"type": "numeric", "expr": "arcsin(1/2)", "degrees": True, "result": "0.524"}))),
        ("inverse normal with an unknown tail", edit(binom, lambda x: b(x)["checks"].append(
            {"type": "normal", "mean": "50", "sd": "4", "prob": "0.05", "tail": "upper", "result": "56.58", "form": "dp-2"}))),
        ("string numbers, wrong binomial value", edit(binom, lambda x: b(x)["checks"].append(
            {"type": "binomial_cdf", "n": "25", "p": "0.30", "k": "3", "tail": "le", "result": "0.0350", "form": "sf-3"}))),
    ]


def g2_passes(cubic: dict, binom: dict, pulley: dict) -> list[tuple[str, dict]]:
    """Regressions: correct items that an earlier version rejected."""
    a, b = (lambda x: x["parts"][0]), (lambda x: x["parts"][1])
    return [
        ("show-that part verified by a derivative check only", edit(cubic, lambda x: (
            a(x).update(command="show-that", checks=[{"type": "derivative", "f": "2x^3 - 15x^2 + 36x - 20", "var": "x",
                                                     "result": "6x^2 - 30x + 36"}]), a(x).pop("answers")))),
        ("roots at both closed ends", edit(cubic, lambda x: b(x)["checks"].append(
            {"type": "solutions", "equation": "sin(x) = 0", "var": "x", "interval": ["0", "360"], "degrees": True,
             "result": ["0", "180", "360"]}))),
        ("open end excludes its root", edit(cubic, lambda x: b(x)["checks"].append(
            {"type": "solutions", "equation": "sin(x) = 0", "var": "x", "interval": [0, 360], "closed": [True, False],
             "degrees": True, "result": ["0", "180"]}))),
        ("rounded answer within its rounding (1.41^2 = 2)", edit(pulley, lambda x: b(x)["answers"].append(
            {"name": "x", "expr": "1.41", "form": "sf-3", "check": "x^2 - 2 = 0"}))),
        ("degrees arcsin(1/2) = 30 (check and answer)", edit(cubic, lambda x: (
            a(x)["checks"].append({"type": "numeric", "expr": "arcsin(1/2)", "degrees": True, "result": "30"}),
            a(x)["answers"].append({"name": "t", "expr": "arcsin(0.5)", "degrees": True, "exact": "30"})))),
        ("inverse normal upper tail as gt", edit(binom, lambda x: b(x)["checks"].append(
            {"type": "normal", "mean": "50", "sd": "4", "prob": "0.05", "tail": "gt", "result": "56.58", "form": "dp-2"}))),
        ("numbers as strings (\"0.30\" to dp-2)", edit(binom, lambda x: (
            b(x)["checks"].append({"type": "binomial_cdf", "n": "25", "p": "0.30", "k": "3", "tail": "le",
                                   "result": "0.0332", "form": "sf-3"}),
            b(x)["answers"].append({"name": "p1", "expr": "0.30", "form": "dp-2", "exact": "3/10"})))),
        ("answer verified by equalling a check result", edit(cubic, lambda x: b(x)["checks"][0].update(
            result=["2", "3"]))),
        ("show-that part with only an equals check", edit(cubic, lambda x: (
            a(x).update(command="show-that", checks=[{"type": "equals", "lhs": "(x - 2)(x - 3)", "rhs": "x^2 - 5x + 6"}]),
            a(x).pop("answers")))),
        ("write-down part with nothing to verify", edit(binom, lambda x: a(x).pop("answers"))),
    ]


def g8_faults(cubic: dict, binom: dict, pulley: dict) -> list[tuple[str, dict]]:
    a, c = (lambda x: x["parts"][0]), (lambda x: x["parts"][2])
    return [
        ("unrendered LaTeX", edit(cubic, lambda x: x["pitfalls"][0].update(text=r"Setting $\frac{1}{$ is wrong."))),
        ("unbalanced $", edit(cubic, lambda x: a(x).update(text=r"Find $\frac{\mathrm{d}y}{\mathrm{d}x}. (2)"))),
        ("marks bracket mismatch", edit(cubic, lambda x: a(x).update(text=a(x)["text"].replace("(2)", "(3)")))),
        ("no marks bracket", edit(cubic, lambda x: a(x).update(text=a(x)["text"].replace(" (2)", "")))),
        ("command not in the text", edit(cubic, lambda x: a(x).update(command="solve"))),
        ("command not a code", edit(cubic, lambda x: a(x).update(command="work-out"))),
        ("marks out of range for the type", edit(cubic, lambda x: c(x).update(
            marks=12, text=c(x)["text"].replace("(2)", "(12)")))),
        ("too many parts for the type", edit(pulley, lambda x: x["parts"].extend(
            copy.deepcopy(x["parts"][1]) | {"label": lab} for lab in "cdefgh"))),
        ("unknown question type", edit(cubic, lambda x: x.update(question_type="made-up-type"))),
        ("examiner in a pitfall", edit(cubic, lambda x: x["pitfalls"][1].update(
            text="Examiners see this often: give $y$ as well."))),
        ("Pearson in the stem", edit(binom, lambda x: x.update(stem=x["stem"] + " (Pearson style.)"))),
        ("board calculator rubric", edit(cubic, lambda x: a(x).update(forms=["no-calc-tech"], text=a(x)["text"].replace(
            " (2)", " Solutions relying entirely on calculator technology are not acceptable. (2)")))),
        ("no-calc-tech without a rubric", edit(cubic, lambda x: a(x).update(forms=["no-calc-tech"]))),
        ("bad mark code in notes", edit(cubic, lambda x: a(x)["mark_scheme"][1].update(notes="Allow DM1 for an attempt"))),
        ("uppercase AWRT", edit(binom, lambda x: x["parts"][1]["mark_scheme"][1].update(notes="AWRT 0.033"))),
        ("unknown form", edit(cubic, lambda x: a(x).update(forms=["four-sig-figs"]))),
        ("\\( \\) delimiters in a hint", edit(cubic, lambda x: a(x).update(hints=[r"Bring the power down: \(x^3 \to 3x^2\)."]))),
        ("\\[ \\] delimiters in a solution", edit(cubic, lambda x: a(x).update(solution=[{"step": 1, "working": r"\[y' = 6x^2\]"}]))),
        ("LaTeX command outside $", edit(cubic, lambda x: x["pitfalls"][0].update(text=r"Halve it: \frac{1}{2} of $y$."))),
        ("sf-3 form the text does not ask for", edit(pulley, lambda x: a(x).update(forms=["sf-3"]))),
        ("exact form the text does not ask for", edit(cubic, lambda x: a(x).update(forms=["exact"]))),
    ]


def g8_passes(cubic: dict, binom: dict, pulley: dict) -> list[tuple[str, dict]]:
    a = lambda x: x["parts"][0]
    ask = lambda words: lambda x: a(x).update(forms=["sf-3"], text=a(x)["text"].replace(
        " (5)", f" Give your answer to {words} significant figures. (5)"))
    return [
        ("no-calc-tech part with our wording", edit(cubic, lambda x: a(x).update(
            forms=["no-calc-tech"], text=a(x)["text"].replace(" (2)", f" {OUR_RUBRIC} (2)")))),
        ("sf-3 asked for as '3 significant figures'", edit(pulley, ask("3"))),
        ("sf-3 asked for as 'three significant figures'", edit(pulley, ask("three"))),
        ("display maths $$...$$ and an escaped \\$", edit(cubic, lambda x: a(x).update(
            hints=[r"It costs \$5 to learn: $$\frac{\mathrm{d}}{\mathrm{d}x}x^n = nx^{n-1}$$"]))),
    ]


def main() -> int:
    items = json.loads(FIXTURES.read_text(), parse_float=str)["items"]  # as scripts/clean/generate.py reads them
    cubic, binom, pulley = items
    ok = True

    def report(name: str, passed: bool, want: bool, detail: str = "") -> None:
        nonlocal ok
        good = passed == want
        ok &= good
        print(f"{'OK  ' if good else 'FAIL'} {name}: {'passes' if passed else 'fails'}"
              + (f"  [{detail[:110]}]" if detail and (not good or not passed) else ""))

    print("Originals")
    for it in items:
        r2, r8 = g2_maths(it), g8_style(it)
        report(f"{it['id']} G2 ({r2['n_answers']} answers, {r2['n_checks']} checks)", r2["pass"], True, "; ".join(r2["errors"]))
        report(f"{it['id']} G8" + (f" ({len(r8['warnings'])} warning)" if r8["warnings"] else ""), r8["pass"], True,
               "; ".join(r8["errors"]))
    print("G2 must pass")
    for name, x in g2_passes(cubic, binom, pulley):
        r = g2_maths(x)
        report(name, r["pass"], True, "; ".join(r["errors"]))
    print("G8 must pass")
    for name, x in g8_passes(cubic, binom, pulley):
        r = g8_style(x)
        report(name, r["pass"], True, "; ".join(r["errors"]))
    print("G2 time limit in a worker thread (as generate.py runs gates)")
    slow = edit(cubic, lambda x: x["parts"][0]["checks"].append({"type": "integral", "var": "x", "lower": "1", "upper": "2",
                                                                 "f": "exp(sin(x)) * log(x) * tan(x)^3", "result": "1"}))
    old, gate_maths.TIME_LIMIT = gate_maths.TIME_LIMIT, 2
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as ex:
        r = ex.submit(g2_maths, slow).result()
    gate_maths.TIME_LIMIT = old
    took = time.monotonic() - t0
    report(f"slow integral times out ({took:.1f} s)", r["pass"] or took > 8 or not any("timed out" in e for e in r["errors"]),
           False, "; ".join(r["errors"]))
    with ThreadPoolExecutor(max_workers=3) as ex:
        rs = list(ex.map(g2_maths, items))
    report("fixtures in 3 threads at once", all(r["pass"] for r in rs), True, "; ".join(e for r in rs for e in r["errors"]))
    print("G2 planted faults")
    for name, x in g2_faults(cubic, binom, pulley):
        r = g2_maths(x)
        report(name, r["pass"], False, "; ".join(r["errors"]))
    print("G8 planted faults")
    for name, x in g8_faults(cubic, binom, pulley):
        r = g8_style(x)
        report(name, r["pass"], False, "; ".join(r["errors"]))
    print("ALL PASS" if ok else "SOME CASES FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
