# Skill: Writing Worked Examples (Style Guide)

## When to Use
When writing or reviewing worked examples in topic pages. These are the standards the user expects.

## Core Principles

1. **Follow the mark scheme method** — not shortcuts, not alternative approaches
2. **Name every formula/technique before using it** — don't just apply, explain what you're applying
3. **Show intermediate algebraic steps** — never skip a line that might confuse a student
4. **Use consistent notation** — pick one form and stick with it throughout
5. **Only use formulas from the correct formula booklet** (8MA0 for AS, 9MA0 for A Level)

## Structure of a Good Step

```html
<div class="step-reveal">
    <div class="step-reveal-header" onclick="toggleStep(this)">
        <span><span class="part-label">Part (b)</span> Step 3: [Descriptive title]</span>
        <span class="arrow">&#9654;</span>
    </div>
    <div class="step-reveal-content">
        <div class="motivation">
            [WHY we're doing this step. What do we know? What formula/technique applies?
             State the formula explicitly: "When we know a gradient and a point, we use
             y - y₁ = m(x - x₁)"]
        </div>
        <p>[Set up: "Using [formula] with [values]:""]</p>
        <div class="algebra-chain">
            <p>$$[first line]$$</p>
            <p class="reason">[what we did to get to next line]</p>
            <p>$$[intermediate step - don't skip!]$$</p>
            <p>$$[result]$$</p>
        </div>
        <div class="mark-award">M1 — [what this mark is for]</div>
        <div class="mark-award">A1 — [correct answer]</div>
    </div>
</div>
```

## Specific Rules

### Clarify standard forms
- ❌ "Rearrange into gradient form"
- ✅ "Rearrange into gradient form \(y = mx + c\)"

### State what you're using
- ❌ Just write `y - 4 = 2(x - 5)` without explanation
- ✅ "Using \(y - y_1 = m(x - x_1)\) with \(m = 2\) and \((x_1, y_1) = (5, 4)\):"

### Show intermediate algebra
- ❌ `y - 4 = 2(x - 5)` → `y = 2x - 6`
- ✅ `y - 4 = 2(x - 5)` → `y - 4 = 2x - 10` → `y = 2x - 6`

### Notation consistency
- ❌ Use `(a, b)` for centre in one place and `(-g, -f)` in another
- ✅ Use `(a, b)` throughout; if showing expanded form, connect it back with a concrete example

### Mark scheme alignment
- Read the actual MS file to see which method earns M marks
- Structure the solution to hit each mark point
- Label marks with the MS notation (B1, M1, A1, dM1)

## Motivation Block Examples

Good motivations explain the *strategy*, not just restate the question:
- "The shortest distance from the circle to the line is along the perpendicular from the centre to the line, minus the radius."
- "For TWO distinct intersection points, the discriminant must be strictly positive."
- "We know a gradient and a point, so we can find the line equation."

Bad motivations (too vague):
- "We need to find the equation"
- "Now solve"
- "Apply the formula"
