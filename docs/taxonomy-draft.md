# Tagging vocabulary — DRAFT for review

*45 question types · 31 skill groups · 141 skills · covers all 210 questions / 478 parts of the 14 Pure papers (9MA0 P1 & P2). Machine-readable version: `data/processed/_taxonomy_draft.json`. Nothing has been tagged yet.*

## How it works

Every **whole question** gets exactly one *question type*, so "give me more questions like this one" returns questions with the same overall shape (e.g. two 3D-shape optimisation questions). Every **part** gets several *skills* (typically 3–6), so "I struggled with the differentiating in part (b)" can find parts from any topic that practise that skill, easiest first. Each skill sits in a *group*, which the bot falls back to when a skill is rare.

How to review: skim the type table first (is each question in a sensible bucket?), then the skills (is anything missing, too broad or too fine?), then the "Decisions for you" list at the end.

## Question types

| Type | Topic | Definition | Questions |
|---|---|---|---|
| **Optimise a 3D shape under a constraint**<br>`optimisation-constrained-shape` | Calculus — Optimisation | A solid or container with a fixed volume: show a surface-area formula in one variable, then use calculus to find and justify the optimum. | **2**: P1 June2022 Q15, P2 June2019 Q13 |
| **Maximise a quantity given by a model**<br>`optimisation-modelled-quantity` | Calculus — Optimisation | A context model (speed, growth rate, bounce height) whose maximum is found by differentiating the model itself, often needing a product/chain rule and interpretation. | **3**: P1 June2022 Q8, P2 June2018 Q14, P1 June2019 Q12 |
| **Stationary points, nature & concavity**<br>`stationary-points-and-nature` | Differentiation | Differentiate a given curve (once or twice) to find or verify stationary points, classify them, or find where the curve is concave/convex or has an inflection. | **5**: P1 June2018 Q2, P1 Oct2020 Q9, P2 June2023 Q1, P2 Oct2021 Q5, P2 June2024 Q1 |
| **Differentiate to a given form, then use it**<br>`differentiate-to-given-form` | Differentiation | Quotient/product/chain rule on a single function to reach a printed form, often followed by increasing/decreasing or a condition on a constant. | **6**: P1 June2018 Q5, P1 June2019 Q3, P1 June2024 Q5, P1 Oct2021 Q14, P2 June2022 Q12, P2 Oct2020 Q13 |
| **Differentiation from first principles**<br>`first-principles` | Differentiation | Prove a derivative (polynomial or sin/cos) from the gradient of a chord and a limit as h -> 0. | **4**: P1 June2023 Q12, P1 June2024 Q4, P2 June2018 Q9, P2 June2022 Q4 |
| **Implicit differentiation with tangents/normals**<br>`implicit-differentiation-tangents` | Differentiation | Find dy/dx for an implicitly defined curve (or x = f(y)), then use it for a normal, tangent, extreme point or inflection. | **6**: P1 June2018 Q9, P1 June2019 Q14, P1 Oct2020 Q15, P2 June2023 Q7, P2 June2024 Q15, P2 Oct2021 Q8 |
| **Turning point located by iteration**<br>`turning-point-by-iteration` | Numerical Methods | Differentiate, set the derivative to zero, rearrange into x = g(x), then iterate and/or confirm the root with a sign change. | **5**: P1 June2023 Q15, P1 Oct2021 Q4, P2 Oct2020 Q7, P2 June2024 Q6, P2 June2019 Q11 |
| **Locate a root and apply Newton-Raphson/cobweb**<br>`locate-root-and-newton-raphson` | Numerical Methods | Show a root lies in an interval by sign change, then apply Newton-Raphson or judge an iteration from a cobweb diagram. | **4**: P1 June2018 Q4, P1 June2024 Q3, P2 June2018 Q5, P2 June2022 Q6 |
| **Trapezium rule estimate**<br>`trapezium-rule-estimate` | Numerical Methods | Apply the trapezium rule to a table of values, then reuse, judge or compare the estimate (sometimes with the exact integral). | **5**: P1 June2023 Q5, P1 Oct2021 Q11, P2 June2019 Q2, P2 June2022 Q5, P2 Oct2020 Q1 |
| **Exponential model in context**<br>`exponential-model-in-context` | Exponentials & Logarithms | Find the constants of an exponential model from data, then predict, differentiate for a rate, compare two models or evaluate/adapt the model. | **6**: P1 June2018 Q12, P1 June2019 Q7, P2 Oct2020 Q9, P1 June2022 Q10, P1 Oct2021 Q8, P2 June2023 Q4 |
| **Straight-line log graph model**<br>`log-linear-graph-model` | Exponentials & Logarithms | A straight-line graph of log y against x or log x is used to find the constants in y = ab^x or y = kx^n, then interpret or use the model. | **4**: P1 June2023 Q11, P2 June2019 Q9, P2 Oct2021 Q10, P2 June2024 Q13 |
| **Log laws and log equations**<br>`log-laws-and-equations` | Exponentials & Logarithms | Manipulate or solve equations using the laws of logarithms, usually removing logs and rejecting invalid roots. | **5**: P1 June2019 Q9, P1 June2023 Q6, P2 June2023 Q3, P2 Oct2020 Q3, P2 Oct2021 Q3 |
| **Exponential and index equations**<br>`exponential-equations` | Exponentials & Logarithms | Solve an equation with the unknown in the power (by a common base, logs, or a hidden quadratic), sometimes with a sketch of y = a^x. | **4**: P2 June2019 Q1, P1 Oct2020 Q2, P2 Oct2020 Q5, P2 June2022 Q2 |
| **Find a curve from its gradient function**<br>`find-curve-from-gradient` | Integration | Integrate powers of x (indefinite), using a point, turning point or factor to find the constant(s) of integration. | **3**: P1 June2023 Q1, P2 June2023 Q5, P2 Oct2020 Q8 |
| **Area bounded by a polynomial curve (and a line)**<br>`area-between-curve-and-line` | Integration | Algebraic integration of polynomial/fractional powers to find an exact area bounded by a curve, the axis and/or a tangent or straight line. | **4**: P1 June2019 Q8, P1 June2024 Q10, P2 Oct2021 Q7, P2 June2022 Q8 |
| **Definite integrals of standard forms**<br>`definite-integrals-standard-forms` | Integration | A short definite integral of a standard form (1/(ax + b), (ax + b)^-2, x^(1/2)), sometimes written as the limit of a sum, simplified exactly. | **3**: P1 June2018 Q7, P1 June2022 Q4, P2 June2019 Q5 |
| **Integration by parts (exact answer)**<br>`integration-by-parts` | Integration | An exact definite integral or area needing integration by parts (possibly twice or combined with a normal). | **3**: P1 June2022 Q12, P2 June2024 Q11, P2 June2018 Q13 |
| **Integration by a given substitution**<br>`integration-by-substitution` | Integration | Use a given substitution (including trigonometric) to transform and evaluate an integral exactly, changing the limits. | **4**: P1 June2018 Q13, P1 June2024 Q13, P2 Oct2021 Q12, P1 Oct2020 Q10 |
| **Partial fractions, then integrate or differentiate**<br>`partial-fractions-then-calculus` | Partial Fractions | Express a rational function in partial fractions (or divide an improper fraction), then integrate exactly or differentiate. | **4**: P1 June2019 Q13, P2 June2018 Q11, P2 Oct2020 Q6, P2 June2023 Q10 |
| **Area under a parametric curve**<br>`parametric-area` | Parametric Equations | Set up the integral of y(dx/dt) dt for a parametric region, simplify with trig identities and evaluate exactly. | **2**: P1 June2022 Q16, P2 Oct2020 Q12 |
| **Form and solve a differential equation from a description**<br>`de-formulate-from-rates` | Differential Equations | A worded rate statement (proportional to..., constant volume rate, flow in/out) is turned into a DE, sometimes via connected rates, then solved and interpreted. | **6**: P2 June2018 Q10, P1 June2024 Q14, P1 Oct2020 Q14, P2 June2023 Q11, P2 Oct2021 Q14, P1 Oct2020 Q8 |
| **Solve a given separable differential equation**<br>`de-given-separable` | Differential Equations | The DE is given; separate variables (possibly after partial fractions or a substitution), use conditions, rearrange and interpret. | **5**: P1 June2018 Q10, P1 June2024 Q7, P2 June2019 Q14, P2 June2022 Q14, P2 June2024 Q12 |
| **Binomial expansion, validity & approximation**<br>`binomial-expansion-and-approximation` | Binomial Expansion | Expand (a + bx)^n, state validity and use it to approximate a value, sometimes combined with partial fractions or integration. | **8**: P1 June2018 Q11, P1 June2019 Q4, P1 June2024 Q2, P1 Oct2020 Q1, P2 June2022 Q7, P2 Oct2020 Q4, P1 Oct2021 Q9, P2 June2023 Q13 |
| **Vector lengths, angles and shapes**<br>`vectors-lengths-and-shapes` | Vectors | Use magnitudes of vectors (Pythagoras in 3D) for lengths, distances, areas or angles, often to classify or measure a shape. | **5**: P1 June2022 Q9, P1 June2023 Q3, P1 Oct2021 Q6, P2 June2018 Q2, P2 June2023 Q6 |
| **Parallel vectors, collinearity and ratios**<br>`vectors-parallel-and-ratios` | Vectors | Use scalar multiples to show parallel/collinear results or to locate a point dividing a line in a ratio. | **5**: P1 Oct2020 Q3, P2 June2019 Q10, P2 June2022 Q13, P2 June2024 Q7, P2 Oct2020 Q2 |
| **Proof by contradiction**<br>`proof-by-contradiction` | Proof | Prove a statement by assuming its negation (parity, factor pairs, trig inequality) and reaching a contradiction. | **5**: P1 June2022 Q7, P1 Oct2020 Q16, P1 June2024 Q15, P1 Oct2021 Q15, P2 June2023 Q15 |
| **Algebraic proof by cases / counterexample**<br>`proof-by-cases-and-counterexample` | Proof | Prove a number property by writing n in general forms (2k, 2k+1, 3k+r) and checking every case, or disprove a claim with a counterexample. | **5**: P1 June2019 Q10, P1 June2023 Q14, P2 June2022 Q11, P2 Oct2020 Q16, P2 June2018 Q3 |
| **Circle meets a line: tangency and intersections**<br>`circle-line-tangency` | Coordinate Geometry — Circles | Find a circle's centre/radius or equation, then substitute a line and use the discriminant (or the tangent-radius property) for tangents or two intersections. | **4**: P1 June2018 Q6, P1 June2023 Q10, P1 Oct2021 Q7, P2 Oct2020 Q14 |
| **Circle centre/radius with distances**<br>`circle-centre-radius-and-distances` | Coordinate Geometry — Circles | Complete the square for the centre and radius, then use distances from the centre (furthest point, two circles intersecting). | **2**: P1 June2022 Q3, P2 June2024 Q14 |
| **Small angle approximations**<br>`small-angle-approximations` | Trigonometry | Replace sin, cos and tan by their small-angle approximations to estimate a value, a root or an expression. | **5**: P1 June2018 Q1, P1 June2019 Q2, P1 June2023 Q4, P2 June2024 Q5, P2 Oct2021 Q4 |
| **Arcs, sectors and composite circular regions**<br>`radians-sectors-and-regions` | Trigonometry | Use radian arc-length and sector-area formulae (with triangles/segments) to find angles, lengths, areas or perimeters. | **6**: P1 June2018 Q3, P1 June2023 Q8, P1 June2024 Q11, P1 Oct2020 Q11, P2 June2019 Q3, P2 Oct2021 Q6 |
| **Trig identity, then solve an equation**<br>`trig-identity-then-solve` | Trigonometry | Prove or use an identity (double/compound angle, reciprocal, Pythagorean) and then solve a related trig equation in an interval. | **10**: P1 June2022 Q14, P1 Oct2020 Q12, P1 Oct2021 Q10, P2 June2018 Q12, P2 June2019 Q12, P2 June2023 Q14, P2 June2024 Q8, P2 Oct2020 Q10, P1 June2019 Q6, P2 June2018 Q7 |
| **Harmonic form and trig models in context**<br>`harmonic-form-and-trig-models` | Trigonometry | Write a cos x + b sin x as R cos(x +- alpha) and/or use a sinusoidal model to find maximum/minimum values and the times they occur. | **6**: P1 Oct2020 Q6, P1 June2024 Q12, P2 Oct2021 Q15, P2 June2023 Q8, P1 June2018 Q8, P2 June2022 Q9 |
| **Parametric differentiation and tangents**<br>`parametric-differentiation-tangents` | Parametric Equations | Find dy/dx parametrically and use it for a tangent or gradient at a point (sometimes after converting to Cartesian form). | **3**: P2 June2024 Q10, P2 Oct2021 Q13, P2 June2023 Q9 |
| **Parametric to Cartesian, with intersections**<br>`parametric-to-cartesian-and-intersections` | Parametric Equations | Convert parametric equations to Cartesian form (usually by a trig identity), then use the parameter range and/or find intersections or a range of k. | **4**: P1 June2018 Q14, P1 Oct2021 Q13, P2 June2019 Q4, P2 June2022 Q16 |
| **Factor theorem: find the constant**<br>`factor-theorem-find-constant` | Algebra & Factor Theorem | Given a linear factor of a polynomial with an unknown coefficient, set f(a) = 0 and solve for the constant. | **4**: P1 June2019 Q1, P1 June2022 Q2, P1 June2024 Q1, P1 Oct2021 Q1 |
| **Factorise a polynomial and solve**<br>`polynomial-factorise-and-solve` | Algebra & Factor Theorem | Use a known root/factor to factorise a cubic, then solve exactly, find intersections, or count real roots of a related equation. | **3**: P1 June2023 Q2, P1 June2022 Q11, P2 June2018 Q6 |
| **Quadratic and cubic graphs from features**<br>`quadratic-and-polynomial-graphs` | Algebra & Factor Theorem | Complete the square or use roots/turning points to sketch a quadratic or cubic, read off features, or define a region with inequalities. | **4**: P1 June2019 Q5, P1 Oct2021 Q2, P1 Oct2020 Q7, P1 June2022 Q6 |
| **Linear and quadratic models in context**<br>`linear-and-quadratic-models` | Algebra & Factor Theorem | Fit a linear or quadratic model to a context (trajectory, cost, growth) from given conditions, then use it, evaluate it or state a limitation. | **6**: P1 June2022 Q5, P2 June2019 Q7, P2 June2018 Q8, P2 June2024 Q9, P1 Oct2021 Q12, P1 June2023 Q13 |
| **Composite and inverse functions**<br>`composite-and-inverse-functions` | Functions | Evaluate or form composite functions, find inverses with their domains, and state ranges. | **7**: P1 June2023 Q7, P1 June2024 Q8, P1 Oct2020 Q4, P2 June2018 Q1, P2 June2019 Q6, P2 June2022 Q10, P2 Oct2021 Q2 |
| **Modulus graphs and transformations**<br>`modulus-and-transformations` | Functions | Work with y = a|x - b| + c or |f(x)|: find the vertex, solve modulus equations/inequalities, find k for intersections, or map points under transformations. | **7**: P1 June2024 Q6, P2 June2022 Q1, P2 June2023 Q12, P2 Oct2020 Q11, P2 Oct2021 Q11, P1 June2022 Q1, P2 June2024 Q3 |
| **Arithmetic and geometric sequences in context**<br>`ap-gp-in-context` | Sequences & Series | Use nth-term and sum formulae for an AP or GP (often a savings, speed, profit or race context), including forming and solving a quadratic in n. | **6**: P2 Oct2021 Q1, P1 Oct2020 Q5, P1 Oct2021 Q5, P1 June2019 Q11, P2 June2024 Q2, P1 June2022 Q13 |
| **Geometric series with unknowns**<br>`geometric-series-with-unknowns` | Sequences & Series | Terms or sums of a GP are given in terms of an unknown; form and solve an equation (ratio property or sum formula), then use S_infinity. | **4**: P1 June2023 Q9, P1 June2024 Q9, P2 June2022 Q15, P2 Oct2020 Q15 |
| **Sums in sigma notation**<br>`sigma-notation-sums` | Sequences & Series | Evaluate a sigma-notation sum by splitting into AP/GP parts, adjusting the starting index, or telescoping. | **3**: P2 June2018 Q4, P2 June2019 Q8, P2 Oct2021 Q9 |
| **Recurrence relations and periodic sequences**<br>`recurrence-and-periodic-sequences` | Sequences & Series | Generate terms from u_(n+1) = f(u_n), find an unknown constant, and/or sum a periodic sequence. | **5**: P1 Oct2021 Q3, P1 Oct2020 Q13, P2 June2022 Q3, P2 June2023 Q2, P2 June2024 Q4 |

## Skills by group

Booklet column: checked against the official 9MA0 Formulae Book (`data/formula-booklet-9MA0.pdf`, pp. 9–11). **yes (partly)** = only some of the skill's formulae are printed (details in `formula_booklet_note` in the JSON). The earlier file at that path was a saved 404 page; the real booklet was downloaded 2026-09-25. ~parts = estimated number of parts across the 14 papers that test the skill.

### Algebraic manipulation (`algebraic-manipulation`) — Algebra & Factor Theorem

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Rewrite expressions using index laws**<br>`rewrite-using-index-laws` | Turn roots, reciprocals and products into powers of x (e.g. 1/sqrt(x) = x^(-1/2)) or into a common base before differentiating, integrating or solving. | no | 8 | P1 June2023 Q1, P2 June2022 Q8, P2 June2019 Q1, P1 June2024 Q9(a) |
| **Combine and simplify algebraic fractions**<br>`simplify-algebraic-fractions` | Put fractions over a common denominator, multiply through by denominators and cancel common factors. | no | 24 | P1 Oct2020 Q4(b), P2 June2024 Q8(a), P1 June2019 Q3(a), P1 Oct2021 Q13 |
| **Rearrange a formula to change its subject**<br>`rearrange-to-make-subject` | Collect the terms containing the required letter, factorise it out and divide, keeping the order of operations correct. | no | 12 | P1 June2019 Q9(a), P1 June2018 Q9(a), P1 June2023 Q15(b), P2 June2019 Q1 |
| **Solve two linear simultaneous equations**<br>`solve-simultaneous-linear-equations` | Form two equations from two pieces of information and solve them together to find two unknown constants. | no | 12 | P1 June2022 Q5(a), P2 June2019 Q7(b), P1 June2023 Q5(b), P2 Oct2020 Q9(a) |
| **Simplify surds and rationalise denominators**<br>`exact-surd-manipulation` | Write answers as simplified surds (e.g. 3sqrt(2)) and rationalise denominators where required. | no | 17 | P1 Oct2021 Q7(a), P2 June2022 Q15(c), P2 June2022 Q13(b), P1 June2018 Q3 |
| **Solve an equation of the form x^n = k**<br>`solve-power-equation` | Isolate the power (e.g. r^3 = 1050, p^7 = 1.5625, r^(3/2) = 118) and take the appropriate root or power. | no | 7 | P1 June2022 Q15(b), P2 June2019 Q13(b), P1 June2018 Q12(a), P1 June2024 Q14(c) |
| **Substitute to find intersections**<br>`substitute-to-find-intersections` | Substitute one equation into another (a line into a curve or circle, or parametric x(t), y(t) into a Cartesian equation) to get a single equation to solve. | no | 15 | P1 June2023 Q10(b), P1 June2022 Q11(b), P2 June2019 Q4, P2 June2024 Q15(c) |

### Quadratics & the discriminant (`quadratics`) — Algebra & Factor Theorem, Coordinate Geometry — Circles, Functions

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Solve a quadratic equation**<br>`solve-quadratic-equation` | Solve a three-term quadratic by factorising, the quadratic formula or completing the square, giving exact roots when asked. | no | 21 | P1 June2022 Q13(ii(b)), P2 June2024 Q2(c), P1 Oct2021 Q3(b), P2 June2018 Q8(b) |
| **Complete the square**<br>`complete-the-square` | Write ax^2 + bx + c as a(x + p)^2 + q to read off turning points, show an expression is always positive, or find a circle centre. | no | 10 | P1 June2019 Q5(a), P1 Oct2021 Q2(a), P1 June2024 Q15(i), P2 June2023 Q9(a) |
| **Use the discriminant b^2 - 4ac**<br>`discriminant-condition` | Choose the right condition (> 0 two roots, = 0 tangent/repeated root, < 0 no real roots) and solve for the unknown constant. | no | 10 | P1 June2024 Q8(d), P2 June2022 Q12(b), P2 Oct2020 Q14(b), P1 Oct2021 Q7(b) |
| **Solve a quadratic (or other) inequality**<br>`solve-quadratic-inequality` | Find the critical values, then use a sketch or sign analysis to choose the inside or outside region. | no | 9 | P1 June2024 Q5(b), P1 June2023 Q10(b), P2 June2023 Q12(c), P2 Oct2021 Q11(b) |
| **Spot and solve a quadratic in disguise**<br>`solve-hidden-quadratic` | Recognise a quadratic in e^x, 2^x, r^5, y^2 or similar, substitute u for it, solve, then convert back and reject impossible values.<br>*absorbs technique:* `quadratic-in-disguise-exponential` | no | 4 | P1 June2022 Q10(c), P2 Oct2020 Q15(b), P2 June2018 Q6(b), P2 Oct2020 Q5 |

### Polynomials & factor theorem (`polynomials`) — Algebra & Factor Theorem

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Use the factor theorem**<br>`factor-theorem` | If (x - a) is a factor then f(a) = 0: substitute to find an unknown constant or to confirm a factor. | no | 8 | P1 June2019 Q1, P1 June2024 Q1, P1 June2023 Q2(a), P2 Oct2020 Q8 |
| **Factorise a cubic using a known factor**<br>`factorise-polynomial-by-division` | Divide (by long division or inspection) by a known linear factor to get a quadratic factor, then solve or analyse it. | no | 5 | P1 June2022 Q11(b), P2 June2018 Q6(a), P2 June2024 Q15(c), P1 June2019 Q8(b) |
| **Find a quadratic or cubic from its features**<br>`find-polynomial-from-features` | Use roots, repeated roots, a turning point, an intercept or given points (from a graph or a context) to find the equation, e.g. y = ax(x - 6)^2, H = ax^2 + bx + c. | no | 6 | P1 June2022 Q6(c), P1 Oct2020 Q7, P2 June2018 Q8(a), P2 June2024 Q9(a) |

### Graphs, modulus & transformations (`graphs-and-transformations`) — Functions

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Apply graph transformations**<br>`graph-transformations` | Map points or curves under y = af(x), f(x + a), f(ax), -f(x), f(-x) and combinations, or describe a transformation fully. | no | 8 | P1 June2022 Q1(c), P2 June2024 Q3, P1 June2019 Q5(c), P2 Oct2021 Q11(c) |
| **Sketch a curve showing key features**<br>`sketch-curve-key-features` | Draw the correct shape (including exponential, modulus and polynomial curves) and label intercepts, turning points, asymptotes and end behaviour. | no | 8 | P1 June2019 Q5(b), P2 June2022 Q2(a), P1 June2018 Q14(b), P1 June2019 Q12(b) |
| **Sketch modulus graphs and find the vertex**<br>`modulus-graph-vertex` | Sketch y = a|x - b| + c or y = |f(x)| and read off the vertex and intercepts. | no | 7 | P1 June2024 Q6(a), P2 Oct2020 Q11(a), P2 Oct2021 Q11(a), P1 June2022 Q1(b) |
| **Solve modulus equations and inequalities**<br>`solve-modulus-equation-or-inequality` | Remove the modulus by taking the relevant branch(es) (or cases), solve, and check each solution against the graph.<br>*absorbs technique:* `solve-modulus-equation-by-cases` | no | 6 | P2 June2022 Q1, P1 June2024 Q6(b), P2 Oct2020 Q11(b), P2 June2023 Q12(c) |
| **Find the values of k for which a line meets a graph**<br>`line-meets-graph-critical-cases` | Use the graph to find critical cases (through a vertex or endpoint, parallel to a branch, tangent) and combine them into a range of k.<br>*absorbs technique:* `discriminant-and-domain-check-for-line-intersecting-curve` | no | 5 | P1 June2024 Q6(c), P2 Oct2020 Q11(c), P1 June2022 Q6(b), P2 June2022 Q16(c) |
| **Use a graph to justify the number of roots**<br>`graphical-root-counting` | Rearrange an equation into two graphs you can sketch and count the intersections to explain how many roots there are. | no | 3 | P1 June2019 Q2(a), P2 June2018 Q6(b) |

### Functions (composite, inverse, range) (`functions`) — Functions

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Evaluate and form composite functions**<br>`composite-functions` | Work out fg(x) by applying g first and then f (choosing the right branch of a piecewise function); evaluate at a value or simplify fully. | no | 9 | P2 June2018 Q1(a), P1 June2024 Q8(c), P1 Oct2020 Q4(b), P2 June2019 Q6(a) |
| **Find and use inverse functions**<br>`inverse-functions` | Swap x and y and rearrange to find f^(-1)(x), state its domain from the range of f, and know when an inverse exists (one-one). | no | 9 | P1 June2023 Q7(b), P1 June2024 Q8(b), P2 June2019 Q6(c), P2 Oct2021 Q2(c) |
| **State domains and ranges**<br>`domain-and-range` | Use the graph, turning point or asymptote of a function to state its range (or the domain of its inverse) with correct notation. | no | 11 | P2 June2018 Q1(b), P1 June2023 Q7(a), P1 Oct2020 Q9(c), P2 June2022 Q10(c) |

### Straight lines & coordinates (`straight-lines-coordinates`) — Coordinate Geometry — Circles

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find the equation of a straight line**<br>`equation-of-straight-line` | Use y - y1 = m(x - x1) with a gradient and a point, and give the answer in the form asked for. | no | 9 | P1 June2018 Q6(a), P1 Oct2020 Q7, P2 Oct2021 Q7(a), P2 June2023 Q7(b) |
| **Use perpendicular gradients**<br>`perpendicular-gradients` | A perpendicular line (a normal, or a radius meeting a tangent) has gradient equal to the negative reciprocal: m1 x m2 = -1. | no | 7 | P1 June2018 Q6(a), P2 June2018 Q13, P2 June2023 Q7(b), P2 Oct2021 Q8(b) |
| **Find distances between points**<br>`distance-between-points` | Use Pythagoras on the coordinate differences to find a length or a distance between centres. | no | 3 | P1 June2018 Q6(b), P1 June2022 Q3(b), P2 June2024 Q14(b) |

### Circles (`circles`) — Coordinate Geometry — Circles

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find a circle's centre and radius (or write its equation)**<br>`circle-centre-and-radius` | Complete the square on x and y to get (x - a)^2 + (y - b)^2 = r^2 and read off the centre and radius, or write the equation from a known centre and radius. | no | 6 | P1 June2022 Q3(a), P1 Oct2021 Q7(a), P2 Oct2020 Q14(a), P1 June2018 Q6(b) |
| **Solve problems with two circles or distances to a circle**<br>`two-circles-and-distance-to-circle` | Use the distance between centres (and the radii) to decide how circles intersect, or find the furthest/nearest point. | no | 3 | P1 June2022 Q3(b), P2 June2024 Q14(b), P1 Oct2020 Q11(a) |

### Sequences & series (`sequences-and-series`) — Sequences & Series

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Use the nth term of an arithmetic sequence**<br>`arithmetic-sequence-nth-term` | Use u_n = a + (n - 1)d to find a term, the common difference or the number of terms. | no | 6 | P2 Oct2021 Q1(a), P1 Oct2020 Q5(a), P2 June2024 Q2(a) |
| **Sum an arithmetic series**<br>`arithmetic-series-sum` | Use S_n = n/2[2a + (n - 1)d] (or n/2(a + l)), often setting it equal to a total to form a quadratic in n. | yes | 5 | P2 Oct2021 Q1(b), P1 June2022 Q13(ii(a)), P2 June2024 Q2(b), P2 June2018 Q4(i) |
| **Use the nth term of a geometric sequence**<br>`geometric-sequence-nth-term` | Use u_n = ar^(n - 1) to find a term or the common ratio, including percentage-growth contexts. | no | 11 | P1 Oct2020 Q5(b), P1 Oct2021 Q5(b), P1 June2019 Q11(b), P1 June2024 Q9(b) |
| **Sum a finite geometric series**<br>`geometric-series-sum` | Use S_n = a(1 - r^n)/(1 - r) with the correct first term and number of terms. | yes | 4 | P1 June2019 Q11(c), P1 Oct2021 Q5(c), P2 June2018 Q4(i), P2 Oct2020 Q15(b) |
| **Use the sum to infinity and the convergence condition**<br>`sum-to-infinity-and-convergence` | A geometric series converges only if |r| < 1; then S_infinity = a/(1 - r). | yes | 5 | P1 June2023 Q9(b), P1 June2024 Q9(b), P2 June2022 Q15(c), P2 Oct2021 Q9 |
| **Form an equation using the common ratio**<br>`geometric-ratio-equation` | For three consecutive terms, set term2/term1 = term3/term2 and simplify to an equation in the unknown. | no | 3 | P1 June2023 Q9(a), P1 June2024 Q9(a), P2 June2022 Q15(a) |
| **Prove the arithmetic or geometric series formula**<br>`prove-series-sum-formula` | Write S_n forwards and backwards and add (arithmetic), or multiply by r and subtract (geometric).<br>*absorbs technique:* `reverse-and-add-arithmetic-series-proof` | no | 2 | P1 June2022 Q13(i), P2 Oct2020 Q15(a) |
| **Generate terms from a recurrence relation**<br>`recurrence-relation-terms` | Substitute repeatedly into u_(n+1) = f(u_n) to find terms, often in terms of an unknown constant, and form an equation. | no | 8 | P1 Oct2021 Q3(a), P2 June2024 Q4(a), P1 Oct2020 Q13(a), P2 June2023 Q2(a) |
| **Sum a periodic sequence**<br>`periodic-sequence-sum` | Identify the repeating block and its order, then sum complete blocks plus any leftover terms.<br>*absorbs technique:* `sum-periodic-sequence-by-blocks` | no | 5 | P2 June2022 Q3(b), P1 Oct2020 Q13(c), P2 June2023 Q2(b), P2 June2018 Q4(ii) |
| **Evaluate sums in sigma notation**<br>`sigma-notation-sums` | Split a sigma sum into standard parts, adjust for a starting index other than 1, or spot a telescoping pattern.<br>*absorbs technique:* `adjust-gp-sum-for-shifted-start,telescoping-sum-with-logs` | no | 4 | P2 June2018 Q4(i), P2 June2019 Q8(i), P2 Oct2021 Q9 |

### Binomial expansion (`binomial-expansion`) — Binomial Expansion

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Take out a factor before expanding (a + bx)^n**<br>`binomial-take-out-factor` | Rewrite (a + bx)^n as a^n(1 + bx/a)^n before using the expansion. | no | 4 | P1 June2019 Q4(a), P2 June2022 Q7(a), P2 June2023 Q13(a), P1 Oct2021 Q9(b) |
| **State the range of validity of an expansion**<br>`binomial-validity` | The expansion of (1 + ax)^n is valid for |ax| < 1; use this to decide which x values may be substituted. | yes (partly) | 4 | P1 June2018 Q11(b), P1 June2019 Q4(b(i)), P1 June2024 Q2(b), P1 Oct2021 Q9(b) |
| **Use an expansion to approximate a value**<br>`binomial-approximation` | Choose a suitable x, substitute into both the expression and the expansion, and comment on accuracy or over/underestimate. | no | 4 | P1 June2018 Q11(c), P1 Oct2020 Q1(b), P1 June2019 Q4(b(ii)), P2 June2022 Q7(b) |
| **Multiply series and truncate at a power**<br>`multiply-series-and-truncate` | Multiply two expansions (or an expansion by a polynomial) keeping only terms up to the required power.<br>*absorbs technique:* `multiply-binomial-expansions-truncate-at-power` | no | 3 | P1 June2018 Q11(a), P2 June2023 Q13(b), P1 Oct2021 Q9(b) |
| **Write out binomial expansion terms**<br>`binomial-expansion-terms` | Expand (1 + ax)^n for fractional or negative n (1 + nx + n(n-1)/2! (ax)^2 + ...), or find a coefficient in (a + bx)^n with nCr, bracketing (ax)^k correctly. | yes | 8 | P1 June2024 Q2(a), P1 Oct2020 Q1(a), P2 June2023 Q13(a), P2 Oct2020 Q4 |

### Exponentials & logarithms (`exponentials-and-logarithms`) — Exponentials & Logarithms

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Apply the laws of logarithms**<br>`laws-of-logarithms` | Use the addition, subtraction and power laws (and log_a a = 1) to combine or split logarithms. | yes (partly) | 23 | P1 June2023 Q6(c), P2 June2023 Q3(a), P2 Oct2021 Q3, P1 June2019 Q9(a) |
| **Solve exponential equations using logarithms**<br>`solve-exponential-equation` | Isolate the exponential term (or set two exponential models equal), then take logs to bring the power down and solve. | no | 13 | P1 Oct2020 Q2, P2 June2022 Q2(b), P1 Oct2021 Q8(c), P1 June2024 Q7(b) |
| **Convert a log equation into an equation without logs**<br>`remove-logarithms` | Combine into a single log, then use log_a x = b <=> x = a^b (or e^(ln x) = x) to remove the logs. | no | 13 | P2 Oct2020 Q3(a), P2 Oct2021 Q3, P2 June2023 Q3(a), P2 June2024 Q12(c) |

### Exponential & log modelling (`exponential-modelling`) — Exponentials & Logarithms

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find the constants in an exponential model**<br>`form-exponential-model` | Substitute given data (usually t = 0 first) into V = Ae^(kt), V = Ap^t or theta = A - Be^(-kt) and solve for the constants. | no | 6 | P1 June2019 Q7(a), P1 Oct2021 Q8(a), P2 Oct2020 Q9(a), P1 June2018 Q12(a) |
| **Use a straight-line log graph to find model constants**<br>`log-linear-graph-model` | Take logs of y = ab^x or y = kx^n to get a straight line; match the gradient and intercept to find the constants.<br>*absorbs technique:* `log-linearise-power-law-model` | no | 7 | P2 June2019 Q9(a), P2 Oct2021 Q10(b), P1 June2023 Q11(b), P2 June2024 Q13(a) |
| **Differentiate a model to find a rate of change**<br>`rate-of-change-of-model` | Differentiate the model with respect to time and substitute a value, or use a given rate to find a constant. | no | 6 | P1 June2022 Q10(b), P1 Oct2021 Q8(b), P2 June2023 Q4(b) |

### Modelling in context (`modelling-in-context`) — Exponentials & Logarithms, Differential Equations, Trigonometry, Algebra & Factor Theorem

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Translate a context into a mathematical model**<br>`translate-context-into-model` | Turn a worded description into an equation: linear cost, quadratic path, arithmetic/geometric growth, or a proportional rate. | no | 12 | P2 June2019 Q7(a), P1 Oct2021 Q12(a), P1 Oct2020 Q8, P1 June2024 Q14(a) |
| **Use a model to make a prediction**<br>`use-model-to-predict` | Substitute a value into a model (or solve for the input), including an optimum found by calculus, and answer in context with units. | no | 32 | P1 June2018 Q8(a), P2 June2019 Q9(c), P2 June2019 Q13(c), P2 June2024 Q13(c) |
| **Evaluate a model against real data**<br>`evaluate-model-against-data` | Compare a model prediction with a given true value and conclude whether the model is reliable, with a reason. | no | 6 | P1 June2019 Q7(b), P1 June2022 Q5(b), P1 June2023 Q11(c), P2 Oct2020 Q9(b) |
| **Interpret constants in a model**<br>`interpret-model-parameters` | Explain what a constant means in context (initial value, growth factor per year, cost per item). | no | 4 | P1 June2018 Q12(b), P2 June2019 Q7(c), P2 Oct2021 Q10(c), P2 June2024 Q13(b) |
| **State a limitation of a model**<br>`state-model-limitation` | Give a specific reason the model may break down (negative values, unrealistic assumptions, outside the data range). | no | 12 | P2 June2018 Q8(c), P1 June2024 Q14(d), P2 June2023 Q12(d), P1 June2019 Q12(d) |
| **Find the long-term (limiting) value of a model**<br>`long-term-behaviour-of-model` | Let t tend to infinity (e^(-kt) -> 0) or set the rate to zero to find a limiting value, and interpret it.<br>*absorbs technique:* `exponential-model-long-run-limit` | no | 7 | P1 June2024 Q7(c), P2 Oct2021 Q14(c), P2 June2024 Q12(d), P2 June2022 Q14(c) |

### Radians, sectors & triangle trig (`radians-and-circular-measure`) — Trigonometry

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find arc lengths (radians)**<br>`arc-length` | Use s = r theta with theta in radians, including perimeters of sectors and composite shapes. | no | 4 | P1 June2018 Q3, P1 June2023 Q8(a), P2 Oct2021 Q6(c), P1 Oct2020 Q11(b) |
| **Find sector areas (radians)**<br>`sector-area` | Use A = (1/2) r^2 theta with theta in radians. | no | 7 | P1 June2018 Q3, P1 June2023 Q8(c), P2 June2019 Q3(b), P1 June2022 Q15(a) |
| **Find areas and perimeters of composite circular regions**<br>`composite-circular-regions` | Build a region from sectors, triangles and segments (e.g. overlapping circles, logos), adding and subtracting pieces.<br>*absorbs technique:* `perimeter-of-overlapping-circles-region` | no | 7 | P1 June2024 Q11, P1 Oct2020 Q11(b), P1 June2023 Q8(c), P2 Oct2021 Q6(b) |
| **Use sine rule, cosine rule and (1/2)ab sin C**<br>`triangle-trigonometry` | Find sides, angles or areas of non-right-angled triangles. | no | 4 | P1 Oct2021 Q6(b), P1 Oct2020 Q11(a), P1 June2023 Q8(c), P1 June2024 Q11 |
| **Use exact trig values**<br>`exact-trig-values` | Use exact values of sin, cos and tan at 0, pi/6, pi/4, pi/3, pi/2 (and related angles) to keep answers exact. | no | 7 | P1 June2022 Q14(a), P2 June2022 Q15(c), P1 June2022 Q16(b), P1 June2024 Q11 |
| **Use small angle approximations**<br>`small-angle-approximations` | Replace sin x ~ x, tan x ~ x and cos x ~ 1 - x^2/2 (x in radians, watch the argument, e.g. cos 3x ~ 1 - 9x^2/2). | yes | 6 | P1 June2018 Q1, P2 June2024 Q5, P1 June2019 Q2(b), P1 June2023 Q4(a) |

### Trig identities (`trig-identities`) — Trigonometry

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Use sec, cosec and cot**<br>`reciprocal-trig-functions` | Rewrite sec, cosec and cot as 1/cos, 1/sin and cos/sin (and tan as sin/cos) to simplify. | no | 13 | P1 Oct2020 Q12(a), P2 June2024 Q8(a), P2 June2018 Q7(i), P2 June2019 Q12(b) |
| **Use Pythagorean identities**<br>`pythagorean-identities` | Use sin^2 + cos^2 = 1, 1 + tan^2 = sec^2 and 1 + cot^2 = cosec^2 to change the form of an expression. | no | 12 | P1 Oct2020 Q15(a), P2 June2018 Q12(b), P2 June2024 Q8(a), P1 June2019 Q14(c) |
| **Use double angle formulae**<br>`double-angle-formulae` | Use sin 2A = 2 sin A cos A and the three forms of cos 2A, choosing the form that simplifies the expression. | no | 14 | P1 Oct2021 Q10(a), P2 June2018 Q7(i), P1 June2018 Q14(a), P2 June2018 Q12(a) |
| **Use compound angle formulae**<br>`compound-angle-formulae` | Expand sin(A +- B), cos(A +- B), tan(A +- B), e.g. to find cos 3A or to rewrite a shifted trig function. | yes | 5 | P1 June2022 Q14(a), P2 Oct2020 Q10(a), P2 June2019 Q12(a), P1 June2023 Q12 |
| **Prove a trigonometric identity**<br>`prove-trig-identity` | Start from one side, convert to sin and cos, use identities and algebra step by step until you reach the other side. | no | 6 | P2 June2018 Q12(a), P1 Oct2021 Q10(a), P2 June2024 Q8(a), P1 Oct2020 Q12(a) |
| **Write a cos x + b sin x as R cos(x +- alpha) or R sin(x +- alpha)**<br>`harmonic-form` | Find R = sqrt(a^2 + b^2) and alpha from tan alpha, matching the signs to the required form. | no | 9 | P1 Oct2020 Q6(a), P1 June2024 Q12(a), P2 Oct2021 Q15(a), P2 June2023 Q8(a) |

### Trig equations & trig models (`trig-equations-and-models`) — Trigonometry

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Solve a trig equation in a given interval**<br>`solve-trig-equation-in-interval` | Find the principal value, then use the symmetry/period of the graph to list every solution in the interval (degrees or radians). | no | 15 | P1 June2019 Q6(a), P2 June2018 Q7(ii), P1 Oct2021 Q10(b), P2 Oct2020 Q10(b) |
| **Solve trig equations with a transformed argument**<br>`solve-trig-with-transformed-argument` | For sin(2x + 30) = k etc., adjust the interval for the new argument, solve, then undo the transformation. | no | 15 | P1 June2022 Q14(b), P1 June2019 Q6(b), P2 June2019 Q12(b), P2 June2024 Q8(b) |
| **Solve a quadratic in a trig function**<br>`solve-trig-quadratic` | Use identities to get a quadratic in one trig function, solve it, and reject values outside [-1, 1]. | no | 4 | P2 June2018 Q12(b), P2 June2023 Q14(b), P2 June2022 Q15(b), P2 Oct2020 Q10(b) |
| **Factorise rather than divide to avoid losing solutions**<br>`factorise-not-divide-trig` | When a common factor such as sin x or sin 2x appears, factorise it out and solve each factor, instead of cancelling it. | no | 6 | P1 June2019 Q6(a), P2 June2018 Q12(b), P1 Oct2021 Q10(b), P2 June2023 Q14(b) |
| **Use a trig model to find maximum, minimum and times**<br>`trig-model-max-min-and-times` | Use the maximum/minimum of sin or cos (+-1, or R for harmonic form) to find extreme values and the times they occur in context. | no | 10 | P1 Oct2020 Q6(c), P1 June2024 Q12(d), P1 June2018 Q8(b), P1 June2018 Q10(b) |
| **Find the parameters of a trig model**<br>`trig-model-parameters` | Use the maximum, minimum, period and starting value to find the constants in a sinusoidal model. | no | 3 | P2 June2022 Q9(a), P1 June2023 Q13(c), P1 June2024 Q12(b) |

### Basic differentiation (`basic-differentiation`) — Differentiation

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Differentiate polynomials**<br>`differentiate-polynomials` | Use d/dx(x^n) = nx^(n-1) term by term on polynomials. | no | 5 | P2 June2024 Q1(a), P2 June2023 Q1(a), P2 Oct2021 Q5(a), P2 Oct2021 Q7(a) |
| **Differentiate negative and fractional powers**<br>`differentiate-negative-and-fractional-powers` | Rewrite roots and reciprocals as powers, then use nx^(n-1) carefully with negative and fractional indices. | no | 6 | P1 June2022 Q15(b), P2 June2019 Q13(b), P1 June2018 Q2(a), P2 Oct2020 Q7(a) |
| **Differentiate exponentials and logarithms**<br>`differentiate-exponentials-and-logs` | Use d/dx(e^(kx)) = ke^(kx) and d/dx(ln x) = 1/x (and ln(f(x)) -> f'(x)/f(x)). | no | 16 | P1 June2022 Q10(b), P1 Oct2021 Q8(b), P2 June2024 Q6(a), P1 Oct2021 Q4(a) |
| **Differentiate trig functions**<br>`differentiate-trig-functions` | Differentiate sin(kx), cos(kx), tan(kx) and the reciprocal trig functions, including with the chain rule. | yes (partly) | 6 | P1 June2024 Q3(b), P2 June2022 Q6(a), P1 June2019 Q14(a), P2 Oct2021 Q13(a) |
| **Find the second derivative**<br>`second-derivative` | Differentiate the first derivative again (including quotient-rule second derivatives). | no | 10 | P1 June2018 Q2(a), P2 June2024 Q1(a), P2 Oct2021 Q5(a), P1 Oct2020 Q15(b) |
| **Differentiate from first principles**<br>`differentiate-from-first-principles` | Write the gradient of the chord (f(x + h) - f(x))/h, simplify, and take the limit as h -> 0 with correct notation. | yes | 4 | P1 June2024 Q4, P2 June2022 Q4, P1 June2023 Q12, P2 June2018 Q9 |

### Chain, product & quotient rules (`chain-product-quotient-rules`) — Differentiation

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Differentiate using the chain rule**<br>`chain-rule` | Differentiate a function of a function: d/dx f(g(x)) = f'(g(x)) g'(x), e.g. (3 + 7e^(-0.25t))^(-1). | no | 9 | P2 June2018 Q14(b), P2 June2018 Q11(b), P1 June2023 Q15(a), P2 June2024 Q6(a) |
| **Differentiate using the product rule**<br>`product-rule` | Use d/dx(uv) = u v' + v u' for products such as x ln x or e^(-2x)(x^2 - 2). | no | 8 | P1 Oct2020 Q9(a), P1 June2022 Q8(b), P1 June2019 Q12(a), P2 June2018 Q13 |
| **Differentiate using the quotient rule**<br>`quotient-rule` | Use d/dx(u/v) = (v u' - u v')/v^2, then simplify the numerator. | yes | 8 | P1 June2024 Q5(a), P2 June2022 Q12(a), P1 Oct2021 Q14, P2 Oct2020 Q13(b) |
| **Simplify a derivative to a given form**<br>`simplify-derivative-to-given-form` | Factorise and cancel common factors (e.g. e^(-2x), (x + 1)) so the derivative matches the printed form exactly. | no | 12 | P1 June2019 Q3(a), P1 Oct2020 Q9(a), P1 June2023 Q15(a), P1 June2018 Q5 |

### Implicit, parametric & connected-rates differentiation (`implicit-and-parametric-differentiation`) — Differentiation, Parametric Equations, Differential Equations

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Differentiate implicitly**<br>`implicit-differentiation` | Differentiate each term with respect to x, using y^n -> ny^(n-1) dy/dx and the product rule on xy terms, then make dy/dx the subject.<br>*absorbs technique:* `logarithmic-differentiation` | no | 8 | P1 June2018 Q9(a), P2 June2023 Q7(a), P2 Oct2021 Q8(a), P2 June2024 Q15(a) |
| **Differentiate parametric equations**<br>`parametric-differentiation` | Use dy/dx = (dy/dt)/(dx/dt), then substitute the parameter value for the point. | no | 3 | P2 June2024 Q10(a), P2 Oct2021 Q13(a), P2 June2022 Q16(a) |
| **Find the parameter value at a given point**<br>`find-parameter-at-point` | Solve x(t) = a or y(t) = b (checking the other coordinate) to find the parameter at a point, then use it. | no | 4 | P2 June2024 Q10(a), P2 Oct2021 Q13(b), P2 Oct2020 Q12(b), P2 June2022 Q16(a) |
| **Link rates of change with the chain rule**<br>`connected-rates-of-change` | Combine rates such as dV/dt = (dV/dr)(dr/dt) or dh/dt = (dh/dV)(dV/dt) using a volume formula. | no | 3 | P1 Oct2020 Q14(a), P2 June2023 Q11(a), P2 Oct2021 Q14(a) |

### Tangents & normals (`tangents-and-normals`) — Differentiation, Coordinate Geometry — Circles

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find the equation of a tangent**<br>`tangent-at-a-point` | Differentiate, substitute the x-coordinate for the gradient, and use y - y1 = m(x - x1). | no | 5 | P1 June2024 Q10(b), P2 Oct2021 Q7(a), P2 June2024 Q10(a), P1 June2023 Q4(b) |
| **Find the equation of a normal**<br>`normal-at-a-point` | Find the tangent gradient, take the negative reciprocal, and use the point to write the normal. | no | 5 | P2 June2023 Q7(b), P2 June2024 Q15(b), P2 June2022 Q16(a), P2 June2018 Q13 |
| **Use gradient conditions (horizontal/vertical tangents, equal gradients)**<br>`gradient-conditions-on-curves` | Interpret dy/dx = 0, dy/dx undefined, or f'(x) = g'(x) geometrically to set up the equation to solve. | no | 3 | P1 June2018 Q9(b), P2 June2024 Q6(b) |

### Stationary points & nature (`stationary-points`) — Differentiation, Calculus — Optimisation

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Set the derivative equal to zero and solve**<br>`set-derivative-zero-and-solve` | Stationary points occur where dy/dx = 0: set the derivative to zero, solve, and find the coordinates.<br>*absorbs technique:* `differentiate-then-solve-stationary-point` | no | 18 | P1 June2022 Q15(b), P1 Oct2020 Q9(b), P2 June2022 Q6(a), P1 June2019 Q12(a) |
| **Verify a stationary point at a given x**<br>`verify-stationary-point` | Substitute the given x into dy/dx, show it equals 0 and make a conclusion. | no | 3 | P1 June2018 Q2(b), P2 Oct2021 Q5(b), P2 June2023 Q5(a) |
| **Determine the nature of a stationary point**<br>`second-derivative-test` | Substitute into the second derivative (positive: minimum, negative: maximum) or check the gradient either side (needed for a stationary point of inflection); state the sign and conclude.<br>*absorbs technique:* `second-derivative-test-for-max-min` | no | 3 | P1 June2022 Q15(c), P1 June2018 Q2(c), P2 Oct2021 Q5(b) |
| **Use the derivative to find increasing/decreasing intervals**<br>`increasing-decreasing-functions` | f is increasing where f'(x) > 0 and decreasing where f'(x) < 0; solve the inequality or prove the sign. | no | 5 | P1 June2024 Q5(b), P1 June2019 Q3(b), P2 June2018 Q11(b), P2 Oct2020 Q13(b) |
| **Use concavity and points of inflection**<br>`concavity-and-inflection` | Concave where f''(x) <= 0, convex where f''(x) >= 0; at a point of inflection f''(x) changes sign. | no | 3 | P2 June2023 Q1(b), P1 Oct2020 Q15(b), P2 Oct2021 Q5(b) |

### Optimisation set-up (`optimisation`) — Calculus — Optimisation

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Eliminate a variable using a constraint**<br>`eliminate-variable-using-constraint` | Use the fixed quantity (e.g. volume) to express one variable in terms of the other and substitute into the quantity to be optimised.<br>*absorbs technique:* `eliminate-variable-using-constraint` | no | 3 | P1 June2022 Q15(a), P2 June2019 Q13(a), P1 June2018 Q3 |
| **Use area and volume formulae for 3D shapes**<br>`mensuration-formulae` | Write surface areas and volumes of prisms, cylinders, spheres/hemispheres and cuboids. | yes (partly) | 5 | P1 June2022 Q15(a), P2 June2019 Q13(a), P1 Oct2020 Q14(a), P2 June2023 Q11(a) |

### Basic integration (`basic-integration`) — Integration

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Integrate powers of x**<br>`integrate-powers-of-x` | Use the integral of x^n = x^(n+1)/(n+1) term by term, including negative and fractional powers after rewriting. | no | 15 | P1 June2023 Q1, P2 June2022 Q8, P1 June2019 Q8(a), P2 June2023 Q5(b) |
| **Evaluate a definite integral**<br>`evaluate-definite-integral` | Substitute the limits into the integrated expression and subtract (upper minus lower), simplifying exactly; recognise lim (delta x -> 0) of sum f(x) delta x as the integral of f(x). | no | 25 | P1 June2018 Q7(a), P1 June2022 Q4(a), P2 June2019 Q5, P2 Oct2020 Q6(b) |
| **Find the constant of integration from a point**<br>`constant-of-integration-from-point` | After integrating, substitute a known point (or initial condition) to find c. | no | 3 | P2 June2023 Q5(b), P2 Oct2020 Q8, P1 June2024 Q7(a) |
| **Use standard integrals (e^(kx), 1/x, trig)**<br>`standard-integrals` | Integrate e^(kx), 1/(ax + b), sin(kx), cos(kx) and sec^2(kx) directly, remembering the 1/k factor. | yes (partly) | 10 | P1 June2022 Q4(b), P1 June2018 Q7(a), P1 June2024 Q7(a), P2 Oct2020 Q6(b) |
| **Integrate by reverse chain rule (recognition)**<br>`reverse-chain-rule` | Recognise integrands of the form f'(x)[f(x)]^n or (ax + b)^n and integrate by inspection. | no | 3 | P1 June2018 Q7(b), P2 Oct2020 Q12(a(ii)), P1 June2022 Q16(b) |

### Areas by integration (`areas-by-integration`) — Integration, Parametric Equations

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find the area under a curve**<br>`area-under-curve` | Integrate between the x-intercepts or given limits; where the curve is below the x-axis the integral is negative, so split at roots and use magnitudes. | no | 5 | P1 June2019 Q8(a), P2 June2022 Q8, P2 June2018 Q13 |
| **Find the area between a curve and a line**<br>`area-between-curve-and-line` | Integrate (top - bottom), or combine the area under the curve with triangle/trapezium areas. | no | 3 | P1 June2024 Q10(c), P2 Oct2021 Q7(c), P2 June2018 Q13 |
| **Find the area under a parametric curve**<br>`area-under-parametric-curve` | Use Area = integral of y (dx/dt) dt with the limits changed to parameter values.<br>*absorbs technique:* `area-under-parametric-curve` | no | 2 | P1 June2022 Q16(a), P2 Oct2020 Q12(a(i)) |

### Integration techniques (parts, substitution, identities) (`integration-techniques`) — Integration, Partial Fractions

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Integrate by parts**<br>`integration-by-parts` | Choose u (often ln x or a polynomial) and dv/dx, apply the formula (twice if needed) and simplify. | yes | 4 | P1 June2022 Q12, P2 June2024 Q11, P1 Oct2021 Q11(b), P2 June2018 Q13 |
| **Integrate by substitution**<br>`integration-by-substitution` | Use the given substitution to rewrite the whole integral (including dx) in terms of the new variable, then integrate.<br>*absorbs technique:* `substitution-for-root-in-denominator,trig-substitution-for-sqrt-x-a-minus-x` | no | 6 | P1 June2018 Q13, P2 Oct2021 Q12(a), P1 June2024 Q13(a), P2 June2019 Q14(a) |
| **Change the limits when substituting**<br>`change-limits-in-substitution` | Convert x-limits into limits for the new variable (u or theta) so you never need to substitute back. | no | 5 | P1 Oct2020 Q10(a), P2 Oct2021 Q12(a), P1 June2018 Q13, P1 June2022 Q16(a) |
| **Use trig identities to integrate**<br>`integrate-using-trig-identities` | Rewrite sin^2, cos^2 or products using double angle identities before integrating. | no | 4 | P1 June2024 Q13(b), P1 June2022 Q16(a), P2 Oct2020 Q12(a(i)) |
| **Integrate partial fractions to logarithms**<br>`integrate-partial-fractions-to-logs` | Integrate A/(ax + b) to (A/a) ln|ax + b| for each fraction, then combine logs into a single exact form. | no | 5 | P1 June2019 Q13(b), P1 Oct2020 Q10(b), P2 June2023 Q10(b), P2 June2022 Q14(b) |

### Partial fractions (`partial-fractions`) — Partial Fractions

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Divide out an improper algebraic fraction**<br>`algebraic-division-improper` | When the numerator degree >= denominator degree, divide first to get a polynomial plus a proper fraction (e.g. 4 - 7/(2x + 3)). | no | 3 | P2 Oct2020 Q6(a), P2 June2022 Q10(b), P2 June2018 Q11(a) |
| **Split a fraction into partial fractions**<br>`partial-fractions` | Write A/(ax + b) + B/(cx + d) (or with a repeated factor B/(ax + b)^2), multiply through, and find the constants by substitution or comparing coefficients. | no | 7 | P2 June2022 Q14(a), P2 June2023 Q10(a), P1 Oct2021 Q9(a), P1 June2019 Q13(b) |

### Differential equations (`differential-equations`) — Differential Equations

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Form a differential equation from a description**<br>`form-differential-equation` | Translate "rate of change is proportional to..." into dy/dt = k(...) with the correct sign. | no | 6 | P1 June2024 Q14(a), P2 June2018 Q10(a), P1 Oct2020 Q8, P2 Oct2021 Q14(a) |
| **Separate the variables and integrate**<br>`separate-variables-and-integrate` | Rearrange to f(y) dy = g(x) dx, integrate both sides and include one constant of integration. | no | 9 | P1 June2018 Q10(a), P1 Oct2020 Q14(b), P2 June2024 Q12(b), P2 June2023 Q11(b) |
| **Use initial/boundary conditions to find constants**<br>`find-constants-from-conditions` | Substitute given (t, y) values to find the constant of integration and any proportionality constant. | no | 10 | P2 June2018 Q10(a), P1 Oct2020 Q14(b), P1 June2024 Q14(b), P2 Oct2021 Q14(b) |
| **Rearrange a DE solution into the required form**<br>`rearrange-solution-explicitly` | Remove logs (exponentiate) and make the dependent variable the subject, e.g. V = A/(e^(-kt) + B) or h = A + Be^(-kt). | no | 4 | P1 June2018 Q10(a), P2 June2024 Q12(c), P2 Oct2021 Q14(b), P2 June2022 Q14(b) |

### Numerical methods (`numerical-methods`) — Numerical Methods

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Show a root lies in an interval (change of sign)**<br>`change-of-sign-root-location` | Evaluate f at both ends, show a sign change, state f is continuous, and conclude; use a tight interval to confirm a root to given accuracy. | no | 6 | P1 June2018 Q4(a), P1 June2024 Q3(a), P1 Oct2021 Q4(c), P1 June2023 Q15(e) |
| **Use an iteration formula**<br>`fixed-point-iteration` | Substitute repeatedly into x_(n+1) = g(x_n), giving values to the required accuracy. | no | 6 | P1 June2022 Q8(c), P1 Oct2021 Q4(b), P2 Oct2020 Q7(c), P2 June2024 Q6(c) |
| **Draw cobweb/staircase diagrams and judge convergence**<br>`iteration-diagrams-and-convergence` | Draw a cobweb or staircase from x_1 and decide whether (and to which root) the iteration converges. | no | 3 | P1 June2018 Q4(b), P1 June2023 Q15(c), P2 June2019 Q11(d) |
| **Apply the Newton-Raphson method**<br>`newton-raphson` | Use x_(n+1) = x_n - f(x_n)/f'(x_n) and know when it fails (e.g. f'(x_n) = 0 at a stationary point). | yes | 5 | P1 June2024 Q3(c), P2 June2022 Q6(c), P2 June2018 Q5(a) |
| **Rearrange an equation into a given iterative form**<br>`rearrange-to-iterative-form` | Manipulate f(x) = 0 or f'(x) = 0 algebraically into x = g(x) exactly as printed. | no | 3 | P1 June2022 Q8(b), P1 June2023 Q15(b), P2 Oct2020 Q7(b) |
| **Estimate an integral with the trapezium rule**<br>`trapezium-rule` | Use (h/2)[y0 + yn + 2(y1 + ... + y(n-1))] with the correct strip width h. | yes | 5 | P1 Oct2021 Q11(a), P2 Oct2020 Q1(a), P2 June2022 Q5(a), P2 June2019 Q2(a) |
| **Judge or reuse a trapezium estimate**<br>`trapezium-accuracy-and-reuse` | Explain over/underestimates from the curve shape, comment on accuracy, or scale a previous estimate using log laws or constant factors. | no | 4 | P2 June2019 Q2(b), P2 Oct2020 Q1(b), P2 June2022 Q5(b) |

### Parametric equations (`parametric-equations`) — Parametric Equations

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Convert parametric equations to Cartesian form**<br>`parametric-to-cartesian` | Eliminate the parameter by rearranging or by using a trig identity (sin^2 + cos^2 = 1, cos 2t = 1 - 2 sin^2 t, sec^2 = 1 + tan^2). | no | 4 | P1 June2018 Q14(a), P1 Oct2021 Q13, P2 June2023 Q9(a), P2 June2022 Q16(b) |
| **Use the parameter range to find domain restrictions and endpoints**<br>`parametric-domain-and-endpoints` | Use the allowed values of t to find the end points of the curve and the restricted x or y values. | no | 4 | P1 June2018 Q14(b), P2 June2022 Q16(c), P2 June2024 Q10(b) |

### Vectors (`vectors`) — Vectors

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Find the vector between two points**<br>`vector-between-points` | Use AB = OB - OA (or add vectors along a path) in i, j, k form. | no | 11 | P1 Oct2020 Q3(a), P1 Oct2021 Q6(a), P2 June2024 Q7(a), P2 June2018 Q2(a) |
| **Find the magnitude of a vector**<br>`vector-magnitude` | Use |ai + bj + ck| = sqrt(a^2 + b^2 + c^2) for lengths and distances. | no | 8 | P1 June2023 Q3(a), P1 June2022 Q9(a), P2 June2018 Q2(b), P2 June2022 Q13(b) |
| **Use parallel and collinear vectors**<br>`parallel-and-collinear-vectors` | Vectors are parallel if one is a scalar multiple of the other; collinear points share a parallel vector and a point. | no | 5 | P1 Oct2020 Q3(b), P2 June2022 Q13(a), P2 June2023 Q6(a), P2 June2019 Q10(c) |
| **Use vector ratios to locate points and prove geometric results**<br>`vector-ratios-and-geometric-proof` | Write a position vector using a ratio or scalar lambda, compare coefficients of non-parallel vectors, and prove ratios or shapes. | no | 4 | P2 June2019 Q10(b), P2 Oct2020 Q2, P2 June2024 Q7(b) |

### Proof methods (`proof`) — Proof

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Prove by contradiction**<br>`proof-by-contradiction` | Assume the negation, reason algebraically (e.g. factorise and check every integer factor pair) to something impossible, and conclude the original statement.<br>*absorbs technique:* `difference-of-squares-factor-pairs` | no | 5 | P1 June2022 Q7(i), P1 Oct2020 Q16, P1 June2024 Q15(ii), P2 June2023 Q15 |
| **Prove results using general odd/even/multiple forms**<br>`algebraic-proof-odd-even-multiples` | Represent numbers as 2k, 2k + 1, 3k + 1, etc., expand, and factor to show the required form. | no | 6 | P1 June2023 Q14, P2 June2022 Q11, P2 Oct2020 Q16, P1 June2019 Q10(i) |
| **Prove an inequality or that an expression is always positive**<br>`prove-inequality-or-positivity` | Complete the square (square >= 0), or manipulate an inequality carefully, reversing the sign when multiplying/dividing by a negative. | no | 4 | P1 June2024 Q15(i), P1 June2022 Q7(ii), P2 June2018 Q3(b), P2 June2023 Q15 |
| **Prove by exhaustion or disprove by counterexample**<br>`proof-by-exhaustion-or-counterexample` | Split into a complete set of cases (or check every value) and show the result in each; or disprove a claim with one specific counterexample. | no | 8 | P1 Oct2021 Q15(i), P1 June2019 Q10(i), P2 June2018 Q3(a), P1 June2023 Q14 |

### Exam technique (cross-cutting) (`exam-technique`) — all topics

| Skill | Description | Booklet? | ~parts | Examples |
|---|---|---|---|---|
| **Present a full "show that" argument**<br>`show-that-given-answer` | When the answer is printed, show every step (including key intermediate lines) with no errors, and finish at exactly the given result. | no | 150 | P1 June2022 Q15(a), P1 June2019 Q9(a), P2 Oct2021 Q14(a), P2 June2024 Q2(b) |
| **Use a previous part ("hence")**<br>`use-hence-previous-result` | Spot how an earlier result (identity, factor, expansion, derivative) transforms the new problem, and use it explicitly. | no | 46 | P1 June2022 Q14(b), P2 June2019 Q12(b), P1 June2019 Q6(b), P1 Oct2020 Q12(b) |
| **Reject solutions that are invalid**<br>`reject-invalid-solutions` | Check each solution against the domain, the context or the original equation (log of a negative, negative length, |r| >= 1, outside the interval) and reject with a reason.<br>*absorbs technique:* `check-log-equation-roots-for-validity` | no | 25 | P2 Oct2020 Q3(b), P2 June2023 Q3(b), P1 June2022 Q11(b), P2 June2024 Q2(c) |
| **Give exact (calculator-free) answers**<br>`exact-form-answers` | Keep surds, pi, e and ln in exact form and combine logs, when told to show working or give an exact answer. | no | 64 | P1 June2022 Q12, P2 Oct2020 Q5, P1 June2022 Q16(b), P2 June2022 Q8 |
| **Write answers in set notation**<br>`set-notation-answers` | Express ranges of values using correct set notation, including unions and intersections of intervals. | no | 6 | P1 June2022 Q6(b), P1 June2018 Q14(c), P2 June2023 Q12(c), P2 Oct2021 Q11(b) |
| **Give answers to the required accuracy and units**<br>`accuracy-units-and-rounding` | Round only at the end to the stated accuracy (s.f., d.p., nearest minute/metre) and include units; convert time formats. | no | 70 | P1 June2018 Q8(b), P2 June2018 Q10(b), P1 June2024 Q14(c), P1 June2024 Q7(b) |
| **Explain or justify with a reason and conclusion**<br>`explain-with-reason` | Give a clear mathematical reason plus a minimal conclusion when asked to explain, justify or give a reason. | no | 58 | P2 June2019 Q6(c), P1 Oct2020 Q13(b), P1 June2019 Q9(b), P2 June2018 Q5(c) |

## Decisions for you

1. **Formula-booklet flags: resolved (2026-09-25).** The old `data/formula-booklet-9MA0.pdf` was a saved 404 page. The real Pearson booklet is now downloaded, and every skill's flag was set from its A Level Pure pages (PDF pp. 9–11). 16 of 141 skills use a printed formula, 5 of them only partly.

   **This exposes 8 wrong badges on the revision site.** The site says the opposite of the booklet for:
   - **Arc length** (s = rθ) and **sector area** (½r²θ): marked "In formula booklet", but they are **not printed**.
   - **Arithmetic series sum**, **geometric series sum**, **sum to infinity**, the **binomial series**, the **quotient rule** and the **derivatives of tan/sec/cot/cosec**: marked "Learn this", but they **are printed**.

   The site's badges need fixing. That's a revision-site job, separate from the chatbot.
2. **The three known gaps.** *P1 Oct 2020 Q7* (a straight line and a quadratic curve, then a region defined by inequalities) is in **Quadratic and cubic graphs from features**, with P1 June 2019 Q5, P1 Oct 2021 Q2 and P1 June 2022 Q6. Its skills are `find-polynomial-from-features` and `equation-of-straight-line`. *P2 June 2018 Q8* and *P2 June 2024 Q9* (quadratic trajectory models) are in **Linear and quadratic models in context**, with P1 Oct 2021 Q12 (golf ball), P1 June 2023 Q13 (roller coaster), P1 June 2022 Q5 (tree) and P2 June 2019 Q7 (soap costs). Another option is a 4-question "quadratic trajectory" type, leaving a 2-question "linear/other model" type.
3. **Exponential models: one type or two?** I merged "fit and interpret the model" (car value ×2, ethanol) with "differentiate the model for a rate / compare two models" (bees, bacteria, coffee) into one type of 6. Splitting gives two types of 3.
4. **Two large types that could be split.** *Trig identity, then solve* has 10 questions. Two of them (P1 June 2019 Q6 and P2 June 2018 Q7) solve directly without proving an identity first. *Binomial expansion* has 8 questions, including two multi-topic ones: P1 Oct 2021 Q9 (partial fractions then binomial) and P2 June 2023 Q13 (binomial then integration). It also includes the only positive-integer-power question (P2 Oct 2020 Q4).
5. **Mixed questions went to their biggest part.** Each of these could reasonably sit elsewhere:
   - P2 June 2022 Q16 (parametric normal, then range of k) → parametric-to-Cartesian
   - P1 Oct 2021 Q11 (trapezium, then by parts) → trapezium
   - P2 June 2018 Q13 (normal, then area by parts) → by parts
   - P2 June 2019 Q14 (substitution, then differential equation) → DE
   - P2 June 2023 Q8 (R cos, then arithmetic series S9) → harmonic form
   - P1 June 2019 Q14 (x = 4 sin 2y) → implicit differentiation
   - P2 June 2018 Q11 (partial fractions, then decreasing) → partial fractions
6. **Two-question types kept, no singletons.** The 2-question types are *optimisation-constrained-shape* (from your example), *parametric-area* and *circle-centre-radius-and-distances*. There are no singletons. P1 June 2022 Q1 and P2 June 2024 Q3 (point transformations) were folded into *Modulus graphs and transformations* rather than forming a 2-question type.
7. **Rare skills I merged.** Each of these appeared in fewer than 3 parts:
   - circle equation from properties → circle centre and radius
   - areas below the axis → area under a curve
   - counterexample → proof by exhaustion
   - factor pairs → proof by contradiction (still carries that technique)
   - limit of a sum → evaluate a definite integral
   - fitting a quadratic model + polynomial from a graph → `find-polynomial-from-features`
   - optimum in context → use a model to predict
   - positive-integer binomial → binomial expansion terms

   Two skills with only 2 parts are kept on purpose, because each carries one of your techniques and is a standard spec item: `prove-series-sum-formula` and `area-under-parametric-curve`.
8. **Names compared with your example.** For P1 June 2022 Q15 I used these names:
   - `prism-volume` → `mensuration-formulae`
   - `show-that-algebra` → `show-that-given-answer`
   - `differentiate-negative-powers` → `differentiate-negative-and-fractional-powers`
   - `solve-cubic-power-equation` → `solve-power-equation` (covers r^3 = k, p^7 = k and r^(3/2) = k)

   `sector-area`, `eliminate-variable-using-constraint`, `set-derivative-zero-and-solve` and `second-derivative-test` are unchanged. Rename any you prefer.
9. **Exam-technique skills are very common.** Show-that appears in about 150 parts, exact form in about 64 and accuracy/units in about 70. The bot may want to down-weight them when ranking "similar parts", or only use them when a student asks about presentation.
10. **Part counts are estimates.** They come from one first pass over all 478 parts, cross-checked with keyword searches of the mark schemes (treat them as ±30%). That first pass averaged about 2.7 skills per part, below your 3–6 target, mainly because it applied exam-technique skills sparingly. The real tagging pass should add those.

### Other notes

- **Site correction:** the optimisation page lists "P1 Oct 2020 Q7 — exponential curve, find stationary points". That question is actually **P1 Oct 2020 Q9** (f(x) = 4(x^2 - 2)e^(-2x)). Q7 is the straight-line/quadratic region question. The same page also lists P1 June 2018 Q2 and P2 Oct 2021 Q5. I typed those as *stationary points and nature*, not optimisation, because neither optimises a quantity.
- `tags.json` lists 20 techniques, but `data/processed/techniques/` has only 19 JSON files. `multiply-binomial-expansions-truncate-at-power` has no file. It is still merged into `multiply-series-and-truncate`.
- Every one of the 20 existing technique ids is absorbed by exactly one skill. The skill tables show which, under "absorbs technique".
