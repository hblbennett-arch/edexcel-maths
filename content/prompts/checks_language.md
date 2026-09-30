Expressions are plain maths strings:
- `^` or `**` for powers, and implicit multiplication (`2x`, `x(x+1)`).
- `e` is Euler's number; `log` and `ln` are both the natural log; `log(x, 10)` is base 10.
- Allowed functions: `pi`, `sqrt`, `abs`, `exp`, `sin cos tan sec cosec cot`, `arcsin arccos arctan`, `binomial`, `factorial`.
- Use numbers, not `g`, in mechanics checks (g = 9.8).
- An `equation` has one `=`; with no `=` it means "= 0".

**answers** (per part): `{"name": "x", "expr": "3/2", "form": "exact" | "dp-N" | "sf-N", "exact": optional exact value, "check": optional equation}`
- `form: "exact"`: no decimals in `expr`.
- `dp-N` / `sf-N`: `expr` is written to exactly N decimal places / significant figures and is the correct rounding of `exact` if given.
- `check`: an equation the named answers satisfy, e.g. `"2*9.8 - T = 2*a"`; answers with those names are substituted.

**Every answer must be verified** by a check: one with `"answer": "<name>"`, one whose `result` (or `equals` side) is that answer, or the answer's own `exact` / `check`. A decimal answer needs `exact` or a check that computes it. Use `$...$` only for maths in text (never `\(` or `\[`).

**checks** (per part): each is one JSON object, encoded as a string. Any check may use `"answer": "<name>"` instead of `result`, to verify that answer directly. Add `"degrees": true` for trig in degrees.

| type | fields | passes when |
|---|---|---|
| `equals` | `lhs`, `rhs`, `domain`? (`[a, b]` for the test points, or `"positive"`) | the two are identical |
| `derivative` | `f`, `var`, `order`? (1), `result` | the derivative equals `result` |
| `integral` | `f`, `var`, `lower` and `upper` (or neither), `result`, `form`? | definite: the value matches; indefinite: d(result)/d(var) = f |
| `solutions` | `equation`, `var`, `result: [...]`, `interval: [a, b]`?, `closed: [true, true]`?, `form`? | `result` is exactly the real solution set in the interval (a missing or extra root fails) |
| `system` | `equations: [...]`, `vars: [...]`, `result: {var: value}` | `result` is a solution |
| `substitute` | `expr`, `at: {var: value}`, `result`, `form`? | the value matches |
| `numeric` | `expr`, `result`, `form`? | `result` is the correct rounding |
| `binomial_cdf` | `n`, `p`, `k`, `tail` (le, lt, ge, gt or eq), `result`, `form`? | P for X ~ B(n, p) matches |
| `normal` | `mean`, `sd` (or `var`), `lower`?, `upper`?, `result`, `form`? | P(lower < X < upper) matches |
| `normal` (inverse) | `mean`, `sd`, `prob`, `tail` (le or ge), `result`, `form`? | `result` is the x with that tail probability |

Examples (each is one string in `checks`):
- `{"type": "derivative", "f": "2x^3 - 15x^2 + 36x - 20", "var": "x", "result": "6x^2 - 30x + 36"}`
- `{"type": "solutions", "equation": "6x^2 - 30x + 36 = 0", "var": "x", "result": ["2", "3"]}`
- `{"type": "binomial_cdf", "n": 25, "p": 0.3, "k": 3, "tail": "le", "result": "0.0332", "form": "sf-3"}`
- `{"type": "solutions", "equation": "2 sin(x) = 1", "var": "x", "interval": [0, 360], "degrees": true, "result": ["30", "150"]}`
