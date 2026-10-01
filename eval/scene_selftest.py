"""Self-test for the interactive-scene gate and compiler (docs/learn-layer-spec.md §2).

    .venv/bin/python -m eval.scene_selftest

No model calls. (a) scripts/clean/gate_scene.py passes eval/fixtures/scene_example.json against its item and
fails each planted fault; (b) node runs chatbot/static/scene_compile.js on a few expressions and rejections;
(c) the compiler sections of scene.js and scene_compile.js are byte-identical. Needs node (as katex_render.js does).
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
from scripts.clean.gate_scene import gate_scene, load_item  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- (a) the gate ------------------------------------------------------------------------------------------
scene = json.loads((ROOT / "eval" / "fixtures" / "scene_example.json").read_text())
item = load_item("cr-area-between-curve-and-line-core")
check(item is not None, "item cr-area-between-curve-and-line-core exists")
r = gate_scene(scene, item)
check(r["pass"], f"example scene passes: {r['errors']}")
print(f"example: {'PASS' if r['pass'] else 'FAIL'}; warnings: {r['warnings']}")


# TeX braces inside $...$ are not placeholders (a regression: {125} must not be read as an expression)
s_tex = copy.deepcopy(scene)
s_tex["elements"][6]["value"] = "Area so far = {area(R)}; the full area is $\\frac{125}{6}$ with $\\{a, b\\}$"
r_tex = gate_scene(s_tex, item, g7=False)
check(r_tex["pass"], f"TeX braces inside $...$ are not placeholders: {r_tex['errors']}")


def planted(name, mutate, needle):
    s = copy.deepcopy(scene)
    mutate(s)
    res = gate_scene(s, item, g7=False)
    hit = any(needle in e for e in res["errors"])
    check(not res["pass"] and hit, f"planted fault {name!r} not caught (errors: {res['errors']})")
    print(f"  fault {name:<28} {'caught' if (not res['pass'] and hit) else 'MISSED'}: {res['errors'][:1]}")


def set_expr(s):
    s["elements"][0]["expr"] = "-x^2 + 8x - 5"


def unknown_id(s):
    s["elements"][4]["between"] = ["C", "nope"]


def unknown_func(s):
    s["elements"][1]["expr"] = "foo(x) + 1"


def param_range(s):
    s["params"][0]["value"] = 9


def one_step(s):
    s["steps"] = s["steps"][:1]


def banned(s):
    s["steps"][0]["text"] = "Examiners noted that the shaded region grows as $k$ increases."


def bad_mark(s):
    s["links"]["marks"] = ["M1", "B1"]


def bad_pitfall(s):
    s["links"]["pitfalls"] = ["not-a-code"]


def free_symbol(s):
    s["elements"][2]["x"] = "x + 1"          # a point's coordinate may not depend on x


def dup_id(s):
    s["elements"][3]["id"] = "A"


def bad_board(s):
    s["board"]["x"] = [8, -1]


def blow_up(s):
    s["elements"][1]["expr"] = "1/(x - 3.5)"     # infinite at a sample point of [-1, 8]


def bad_katex(s):
    s["steps"][1]["text"] = "The area is $\\frac{125}{6$."


def bad_type(s):
    s["elements"][5]["type"] = "ray"


def step_show_unknown(s):
    s["steps"][0]["show"] = ["ghost"]


def eval_attempt(s):
    s["elements"][6]["value"] = "Area = {alert(1)}"


def step_set_out_of_range(s):
    s["steps"][1]["set"] = {"k": 60}


def unknown_placeholder_func(s):
    s["elements"][6]["value"] = "P = {foo(k)}"


def helper_arity(s):
    s["elements"][6]["value"] = "P = {norm_cdf(k)}"


def helper_not_finite(s):
    s["elements"][6]["value"] = "P = {norm_cdf(k, 230, 0)}"       # sigma = 0 -> NaN


# statistics helpers in a live placeholder pass the gate (evaluated numerically at the default params)
s_stat = copy.deepcopy(scene)
s_stat["elements"][6]["value"] = "P(X $\\leqslant$ {k}) = {norm_cdf(k, 230, 18)}; tail {binom_ge(14, 0.12, k)}"
s_stat["elements"].append({"type": "point", "id": "Q90", "x": "norm_inv(0.9, 3, 1)", "y": "binom_pmf(10, 0.3, k)"})
r_stat = gate_scene(s_stat, item, g7=False)
check(r_stat["pass"], f"scene using statistics helpers passes: {r_stat['errors']}")
print(f"statistics helpers in placeholders/points: {'PASS' if r_stat['pass'] else 'FAIL'}")


GUIDE = {
    "what_you_see": "The curve $C$ and the line $l$ from the question, with the shaded region $R$ between them.",
    "legend": [{"id": "C", "meaning": "The curve $y=-x^2+8x-5$."}, {"id": "l", "meaning": "The line $y=x+1$."},
               {"id": "A", "meaning": "The first crossing, $(1, 2)$."}, {"id": "B", "meaning": "The second crossing, $(6, 7)$."},
               {"id": "R", "meaning": "The region between $C$ and $l$ from $x=1$ to $k$."},
               {"id": "Q", "meaning": "A point you drag along $C$."}],
    "interact": [{"control": "k", "kind": "slider", "do": "Drag the slider from $1$ to $6$.",
                  "watch": "The shaded region grows; at $k=6$ the reading is $\\frac{125}{6}\\approx 20.8$."},
                 {"control": "Q", "kind": "glider", "do": "Drag $Q$ along the curve between the crossings.",
                  "watch": "$Q$ stays above the line for $1<x<6$."}],
    "question_link": {"part": None, "marks": ["M1", "dM1"],
                      "text": "The shaded region is $R$ from the question; its area is the integral the M1 and dM1 set up and evaluate."},
    "read_off": ["'Area so far' is the integral from $1$ to $k$.", "The label by $Q$ shows its coordinates."],
}
s_guide = copy.deepcopy(scene)
s_guide["guide"] = GUIDE
r_guide = gate_scene(s_guide, item, g7=False, require_guide=True)
check(r_guide["pass"], f"example scene with a guide passes: {r_guide['errors']}")
s_noguide = copy.deepcopy(scene)
s_noguide.pop("guide", None)
r_noguide = gate_scene(s_noguide, item, g7=False, require_guide=True)
check(not r_noguide["pass"] and any("guide: missing" in e for e in r_noguide["errors"]), "--require-guide fails a scene without a guide")
print(f"example with guide: {'PASS' if r_guide['pass'] else 'FAIL'}; without guide under require_guide: {'FAIL' if not r_noguide['pass'] else 'PASS'}")


def guide_missing_legend(s):
    s["guide"] = copy.deepcopy(GUIDE)
    s["guide"]["legend"] = [e for e in s["guide"]["legend"] if e["id"] != "l"]     # l is labelled


def guide_unknown_control(s):
    s["guide"] = copy.deepcopy(GUIDE)
    s["guide"]["interact"].append({"control": "m", "kind": "slider", "do": "Drag the slider to the right.", "watch": "Nothing here changes."})


def guide_bad_mark(s):
    s["guide"] = copy.deepcopy(GUIDE)
    s["guide"]["question_link"]["marks"] = ["M1", "B1"]


for name, fn, needle in [
    ("implicit multiplication 2x", set_expr, "implicit multiplication"),
    ("guide: legend misses label l", guide_missing_legend, "guide.legend: no entry for element 'l'"),
    ("guide: unknown control", guide_unknown_control, "is not a control of this scene"),
    ("guide: marks code not in scheme", guide_bad_mark, "guide.question_link.marks: 'B1' is not in the part's scheme"),
    ("unknown id", unknown_id, "not a function element"),
    ("unknown function foo(x)", unknown_func, "unknown identifier 'foo'"),
    ("param value out of range", param_range, "outside"),
    ("1 step", one_step, "2 to 5"),
    ("banned word", banned, "banned phrase"),
    ("marks code not in scheme", bad_mark, "not in the part's scheme"),
    ("pitfall code unknown", bad_pitfall, "not an error code"),
    ("free symbol x in a point", free_symbol, "free symbol"),
    ("duplicate id", dup_id, "duplicate id"),
    ("board range unordered", bad_board, "ordered"),
    ("function blows up", blow_up, "not finite"),
    ("KaTeX error", bad_katex, "KaTeX cannot render"),
    ("unknown element type", bad_type, "unknown type"),
    ("step shows unknown id", step_show_unknown, "unknown element id"),
    ("placeholder alert(1)", eval_attempt, "unknown identifier 'alert'"),
    ("step set out of range", step_set_out_of_range, "outside"),
    ("placeholder foo(k)", unknown_placeholder_func, "unknown identifier 'foo'"),
    ("helper arity norm_cdf(k)", helper_arity, "takes 3 arguments (got 1)"),
    ("helper NaN (sigma = 0)", helper_not_finite, "not finite"),
]:
    planted(name, fn, needle)

# ---- (b) the JS compiler under node -----------------------------------------------------------------------
cases = [
    {"expr": "-x^2 + 8*x - 5", "vars": {"x": 2}},
    {"expr": "sin(pi/2)"},
    {"expr": "k - 1", "vars": {"k": 6}, "params": ["k"]},
    {"expr": "2^3^2"},
    {"expr": "2x"},
    {"expr": "alert(1)"},
    {"expr": "x; y"},
    {"expr": "window"},
    {"expr": "x(2)", "vars": {"x": 1}},
    {"expr": "constructor"},
    {"expr": "k", "params": []},
    {"expr": "binom_le(10, 0.5, 5)"},                                  # 11: 0.623
    {"expr": "norm_cdf(1.96, 0, 1)"},                                  # 12: 0.975
    {"expr": "norm_inv(0.975, 0, 1)"},                                 # 13: 1.96
    {"expr": "norm_cdf(1)"},                                           # 14: arity
    {"expr": "binom_pmf(14, 0.12, k) + norm_pdf(0, 0, 1)", "vars": {"k": 2}, "params": ["k"]},   # 15
    {"expr": "sin(1, 2)"},                                             # 16: arity of a one-argument function
    {"expr": "(1, 2)"},                                                # 17: comma outside a call
    {"expr": "binom_ge(14, 0.12, 3)"},                                 # 18
]
try:
    p = subprocess.run(["node", str(ROOT / "chatbot" / "static" / "scene_compile.js")], input=json.dumps(cases),
                       capture_output=True, text=True, timeout=30)
    out = json.loads(p.stdout)
except Exception as ex:
    out = []
    fails.append(f"node compile run failed: {type(ex).__name__}: {ex}")
if out:
    def ok(i, value):
        check(out[i]["ok"] and abs(out[i]["value"] - value) < 1e-9, f"compile {cases[i]['expr']!r} -> {out[i]}")

    def rejected(i, token=None):
        check(not out[i]["ok"], f"compile should reject {cases[i]['expr']!r}: {out[i]}")
        if token is not None and not out[i]["ok"]:
            check(out[i].get("token") == token, f"rejection of {cases[i]['expr']!r} should name {token!r}: {out[i]}")

    ok(0, 7)
    ok(1, 1)
    ok(2, 5)
    ok(3, 512)
    rejected(4, "2x")
    rejected(5, "alert")
    rejected(6, ";")
    rejected(7, "window")
    rejected(8, "x(")
    rejected(9, "constructor")
    rejected(10, "k")

    def approx(i, value, tol):
        check(out[i]["ok"] and abs(out[i]["value"] - value) < tol, f"compile {cases[i]['expr']!r} ~ {value}: {out[i]}")

    approx(11, 0.623046875, 1e-9)
    approx(12, 0.9750021048517795, 1e-7)
    approx(13, 1.959963984540054, 1e-6)
    rejected(14, "norm_cdf")
    check(not out[14]["ok"] and "takes 3 arguments (got 1)" in out[14].get("error", ""), f"arity error message: {out[14]}")
    approx(15, 0.28261548258873126 + 0.3989422804014327, 1e-9)
    rejected(16, "sin")
    rejected(17, ",")
    approx(18, 0.23152053757618563, 1e-9)
    for js in (o.get("js", "") for o in out if o["ok"]):
        check(all(tok not in js for tok in ("window", "document", "alert", ";")), f"compiled JS has stray tokens: {js}")
    print(f"node compile: {sum(o['ok'] for o in out)} compiled, {sum(not o['ok'] for o in out)} rejected")

# ---- (c) compiler sections identical -----------------------------------------------------------------------
BEGIN, END = "// ---- SCENE COMPILER BEGIN ----", "// ---- SCENE COMPILER END ----"


def section(path: Path) -> str:
    s = path.read_text()
    check(BEGIN in s and END in s, f"{path.name}: compiler markers present")
    return s[s.index(BEGIN):s.index(END) + len(END)] if BEGIN in s and END in s else ""


a = section(ROOT / "chatbot" / "static" / "scene.js")
b = section(ROOT / "chatbot" / "static" / "scene_compile.js")
check(a and a == b, "compiler sections of scene.js and scene_compile.js are byte-identical")
print(f"compiler sections identical: {a == b and bool(a)} ({len(b)} bytes)")

# scene.js loads in node with a stub window and exposes the API
try:
    p = subprocess.run(["node", "-e", "global.window={}; new Function(require('fs').readFileSync(process.argv[1],'utf8'))();"
                        "console.log(JSON.stringify([typeof window.renderScene, typeof window.renderSceneWhenVisible]))",
                        str(ROOT / "chatbot" / "static" / "scene.js")], capture_output=True, text=True, timeout=30)
    check(json.loads(p.stdout) == ["function", "function"], f"scene.js exposes renderScene/renderSceneWhenVisible: {p.stdout} {p.stderr[:200]}")
except Exception as ex:
    fails.append(f"scene.js load under node failed: {ex}")

print(f"scene self-test: {'PASS' if not fails else 'FAIL'}")
for f in fails:
    print("   ", f)
sys.exit(1 if fails else 0)
