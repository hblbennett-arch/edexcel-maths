# Skill: Formula & Method Audit for Topic Pages

## When to Use
When building new topic pages or reviewing existing ones to ensure:
- Only formula-booklet-appropriate methods are used
- Solutions follow the mark scheme approach (not shortcuts)
- Notation is consistent throughout

## Audit Checklist

### Level-Appropriate Formulas

**AS Level (8MA0) — must NOT use:**
- Perpendicular distance formula: `|ax + by + c| / √(a² + b²)` (Further Maths)
- Cross product or vector product (Further Maths)
- Inverse trig integration: `∫ 1/(1+x²) dx = arctan(x)` (not standard A Level either)
- Matrix methods for simultaneous equations
- Any result requiring knowledge beyond the 8MA0 spec

**A Level (9MA0) — must NOT use:**
- Cross product / vector product (Further Maths)
- Inverse trig as standard integrals (not in formula booklet)
- Hyperbolic functions
- Any Further Maths techniques

### What IS allowed
- Everything in the Edexcel formula booklet for that level
- Standard "learned results" taught at that level (e.g. differentiation rules, completing the square)
- The quadratic formula, discriminant conditions
- Perpendicular gradient = negative reciprocal
- Distance formula (Pythagoras)
- Midpoint formula

## Mark Scheme Verification Process

1. **Read the actual mark scheme** text file for the question
2. **Identify the expected method** from the M marks (method marks)
3. **Follow that method** in the worked solution — don't use a shortcut even if it gives the same answer
4. **Match the mark allocation** — if MS gives B1 for a particular fact, state that fact explicitly

### Example (Circles shortest distance)
- ❌ Wrong: Use `|ax + by + c| / √(a² + b²)` (Further Maths formula)
- ✅ Right: Find perpendicular gradient → equation of perpendicular through centre → solve simultaneously → Pythagoras → subtract radius

## Notation Consistency Rules

1. **Don't switch notation mid-page** — if you introduce centre as `(a, b)`, don't suddenly use `(-g, -f)`
2. **Use concrete examples** instead of abstract general forms where possible
3. **Name every formula before using it** — e.g. "Using y - y₁ = m(x - x₁):" before applying it
4. **Clarify standard names** — "gradient form (y = mx + c)" not just "gradient form"
5. **Show intermediate steps** — don't jump from y - 4 = 2(x - 5) straight to y = 2x - 6

## Running the Audit at Scale

Launch 3 parallel agents splitting the workload:
```
Agent A: Read all 12 AS Pure pages, check each formula against 8MA0 booklet
Agent B: Read all 11 AS Stats+Mech pages, check methods against 8MA0 booklet
Agent C: Read all 16 A Level pages, check each formula against 9MA0 booklet
```

Each agent should flag:
- Formula not in booklet for that level
- Method that doesn't match mark scheme approach
- Notation inconsistencies
- Missing intermediate steps in derivations

## Fixes Applied (May 2026)
- `output-as/topics/coordinate-geometry-circles.html` — replaced perpendicular distance formula with MS approach
- `output/topics/vectors.html` — removed "cross product" mention from examiner note
- `output/topics/integration.html` — removed "inverse trig" from LIATE mnemonic (changed to LATE)
