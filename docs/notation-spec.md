# Notation Spec (Phase 2e): plain text → KaTeX LaTeX

The question and mark-scheme text was transcribed with mixed notation, e.g. `R sin(x + alpha)` next to `K cos(θ + α)`, and `r^2`, `sqrt(38)`, `e^(-x/4)`, `(1/2)x`. This step converts all of it to **one convention**, so answers render cleanly with KaTeX (the same library the revision site uses).

## What gets converted
Units, not whole fields. For each question in `data/processed/questions/<paper>_<sitting>.json`:
- `<question_id>|stem`: the stem (if non-empty), except for a single-part question whose stem is identical to its part text, which is converted once as the part
- `<question_id>|<label>|text`: each part's `text`
- `<question_id>|<label>|ms`: each part's `mark_scheme`

For a single-part question (label `null`), use the label `-`. After conversion the full `question_text` / `mark_scheme_text` fields are rebuilt from the units, so they stay in sync automatically.

## Output
Write **only** `data/processed/_latex/<paper>_<sitting>.json`:
```json
{ "_paper": "P1", "_sitting": "June2022",
  "units": { "P1_June2022_Q15|stem": "...", "P1_June2022_Q15|a|text": "...", "P1_June2022_Q15|a|ms": "..." } }
```
Every unit must be present, including ones that need no change (copy them as they are).

## The convention
- **All maths goes inside inline `$…$`.** Prose stays outside. Keep whole expressions and equations in one span: `$S = 0.8r^2 + \frac{1680}{r}$`, not `$S$ = $0.8r^2$ + …`.
- Powers: `$x^2$`, `$e^{-x/4}$`, `$3^{2(k-1)}$`. Always use braces for multi-character exponents.
- Roots: `$\sqrt{38}$`, `$\sqrt[3]{1050}$`.
- Fractions: use `\frac{a}{b}` for displayed fractions like `(1/2)x` → `$\frac{1}{2}x$`. Inline slashes inside exponents are fine (`$e^{-x/4}$`).
- Greek letters: `\alpha \beta \theta \pi \lambda \mu \delta`, both for Unicode `θ` and for spelled-out `theta` / `alpha` / `pi` in maths contexts.
- Functions: `\sin \cos \tan \sec \csc \cot \ln \log`, e.g. `$\sin^2 x$`, `$\cos(2\theta)$`, `$\log_{10} V$`.
- Degrees: `$30t°$` → `$30t^\circ$`. For trig of degrees use `$\sin(30t)^\circ$` as on the paper.
- Operators and relations: `\times`, `\pm`, `\leqslant`/`\geqslant` (Edexcel style), `<`, `>`, `\neq`, `\approx`, `\equiv`, `\in \mathbb{R}`, `\mathbb{Z}^+`, `\mathbb{N}`.
- Calculus: `$\frac{dy}{dx}$`, `$\frac{d^2S}{dr^2}$`, `$\int_{0}^{\pi/2} 60\sin t\cos^2 t \, dt$`, `$\sum_{r=1}^{16}$`.
- Modulus: `$|x+3|$`. Vectors: `$\overrightarrow{AB}$`, and `$\mathbf{i}$`, `$\mathbf{j}$`, `$\mathbf{k}$`. Column vectors: `$\begin{pmatrix}2\\3\\-4\end{pmatrix}$`.
- Multiplication: drop `*` (`2*sin(30*t)` → `$2\sin(30t)$`) and use `\times` only where the original needs an explicit times sign.
- Subscripts: `$u_{n+1}$`, `$x_1$`.

## Don't change
- **Words, meaning, order, and every number.** The checker compares the numbers in each unit before and after.
- **Mark codes stay as plain text outside `$…$`:** `M1`, `dM1`, `A1*`, `B1ft`, `awrt`, `cao`, `oe`, `SC`.
- **Part labels stay as plain text:** `(a)`, `(b)(i)`, `(ii)`. Mark totals `(4 marks)` / `(3)` too.
- **`[editor: …]` markers stay exactly as they are,** and their inner text gets converted like any other.
- No new content, no corrections. If you spot a maths error, list it in your final reply instead of fixing it.

## Validate
```bash
node scripts/check_notation.js <paper>_<sitting>
```
It fails on:
- KaTeX render errors;
- unbalanced `$`;
- any change to the numbers in a unit;
- a changed `[editor:]` count;
- lost part labels;
- missing or unexpected units.

Fix until OK.
