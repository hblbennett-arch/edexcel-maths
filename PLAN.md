# Edexcel A Level Maths — Interactive Question Analyser: Full Project Plan

## Overview

Six phases: **Setup → Scrape → Extract & Classify → Generate Content → Build Web App → Polish**

The end product is a self-contained web app, organised by topic, where each topic page shows: the common question patterns (with frequency data across years), examiner pitfalls, step-by-step interactive worked examples, and animations for visually-rich concepts.

---

## Phase 0 — Environment Setup

### MCP Servers to install

**1. Playwright MCP** (web scraping)
```bash
npm install -g @playwright/mcp
npx playwright install chromium
```

In your Claude Code `settings.json` (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/i1003721/edexcel-maths"
      ]
    }
  }
}
```

**2. Filesystem MCP** — gives persistent read/write access to the project directory across sessions without needing to re-confirm every file operation.

**3. PDF extraction tool** — install locally in the project:
```bash
mkdir ~/edexcel-maths && cd ~/edexcel-maths
npm init -y
npm install pdf-parse node-fetch
```

### Project directory structure

```
edexcel-maths/
├── config.json                  # Spec config (years, papers, topics)
├── scripts/
│   ├── scrape.js                # Download all PDFs via Playwright
│   ├── extract.js               # Parse PDFs → structured JSON
│   ├── classify.js              # Tag each question by topic
│   └── build.js                 # Generate final HTML output
├── data/
│   ├── raw/
│   │   ├── papers/              # e.g. 9MA0_01_2023_qp.pdf
│   │   ├── markschemes/         # e.g. 9MA0_01_2023_ms.pdf
│   │   └── examiner-reports/    # e.g. 9MA0_2023_er.pdf
│   ├── extracted/
│   │   ├── questions.json       # All questions, structured
│   │   ├── solutions.json       # Mark scheme steps per question
│   │   └── examiner-insights.json
│   └── question-bank/
│       ├── by-topic/            # e.g. calculus-optimisation.json
│       └── by-year/
├── output/
│   ├── index.html               # Topic navigator homepage
│   ├── topics/
│   │   ├── calculus-optimisation.html
│   │   ├── integration-by-parts.html
│   │   └── ...one per topic
│   └── assets/
│       ├── style.css
│       ├── interactive.js       # Hint reveal, step navigation
│       ├── animations/          # SVG + JS animation files
│       └── libs/
│           ├── katex.min.js     # Math rendering
│           ├── jsxgraph.js      # Interactive graphs
│           └── alpine.min.js    # Reactive UI
└── README.md
```

---

## Phase 1 — Scraping

### Target sources

| Source | What it provides |
|---|---|
| **Physics & Maths Tutor (PMT)** | Best-organised; direct PDF links by year and paper code |
| **Edexcel / Pearson** (`qualifications.pearson.com`) | Official; examiner reports live here |

### Papers to scrape (Edexcel 9MA0, new spec 2018–2024)

| Paper | Content |
|---|---|
| 9MA0/01 | Pure Mathematics 1 |
| 9MA0/02 | Pure Mathematics 2 |
| 9MA0/31 | Statistics & Mechanics (Section A: Stats) |
| 9MA0/32 | Statistics & Mechanics (Section B: Mechanics) |

For each paper × each year: question paper + mark scheme + examiner report.

### What the scraper will do

1. Navigate PMT's maths past papers page via Playwright
2. Find all links matching `9MA0` PDFs
3. Download each with a standardised filename: `{code}_{year}_{type}.pdf`
4. Store in `data/raw/`
5. Log a manifest (`data/manifest.json`) so re-runs skip already-downloaded files

---

## Phase 2 — Extraction & Classification

### PDF extraction pipeline

Each question paper PDF goes through:

1. **Text extraction** via `pdf-parse` — pulls raw text per page
2. **Question segmentation** — detect question boundaries using mark allocations `(3)`, `(2 marks)` etc. and question numbering
3. **LaTeX detection** — mathematical expressions are identified and preserved as best as possible from PDF encoding; where extraction is lossy I flag for manual review
4. **Mark scheme alignment** — match each question to its mark scheme steps by question number

Each extracted question becomes a JSON record:
```json
{
  "id": "9MA0_01_2023_Q7b",
  "year": 2023,
  "paper": "01",
  "question_number": "7b",
  "marks": 4,
  "raw_text": "...",
  "mark_scheme_steps": ["...", "..."],
  "topic_tags": [],        // filled in classification phase
  "examiner_notes": []     // filled in examiner phase
}
```

### Classification

A classification pass over every question tags:

- **Primary topic** (e.g. `integration`)
- **Subtopic** (e.g. `integration-by-substitution`)
- **Question pattern** (e.g. `find-area-between-curves`, `show-that`, `optimisation`)
- **Difficulty tier** (1–3, inferred from marks + typical exam position)

### Topic taxonomy

**Pure:**
- `algebra` — partial fractions, modulus, composite/inverse functions, completing the square
- `coordinate-geometry` — circles, lines, parametric curves
- `sequences-series` — arithmetic, geometric, binomial expansion, sigma notation
- `trigonometry` — identities, equations, radians, small angle, reciprocal trig
- `exponentials-logs` — equations, natural log, growth/decay modelling
- `differentiation` — chain/product/quotient rule, implicit, parametric, rates of change
- `calculus-optimisation` — stationary points, max/min problems, second derivative test
- `integration` — standard integrals, by parts, substitution, definite, area/volume
- `differential-equations` — separable, modelling (e.g. Newton's cooling)
- `numerical-methods` — Newton-Raphson, iteration, trapezium rule
- `vectors` — 3D vectors, dot product, lines, angle between vectors
- `proof` — by contradiction, by induction, disproof by counter-example
- `functions-graphs` — transformations, domain/range, modulus graphs

**Statistics:**
- `statistical-sampling` — sampling methods, bias
- `data-presentation` — histograms, box plots, outliers
- `probability` — conditional probability, Venn diagrams, tree diagrams
- `binomial-distribution` — B(n,p), cumulative, hypothesis test
- `normal-distribution` — Z-scores, standardising, inverse normal
- `hypothesis-testing` — one/two-tail, critical regions, p-values

**Mechanics:**
- `kinematics-suvat` — constant acceleration equations
- `kinematics-calculus` — variable acceleration, v=dx/dt
- `forces-newtons-laws` — F=ma, connected particles, pulleys
- `moments` — equilibrium, laminas
- `projectiles` — horizontal/vertical components
- `friction` — F=μR, limiting equilibrium

---

## Phase 3 — Examiner Report Analysis

Examiner reports are processed separately. For each report:

1. **Topic sections** — match to the taxonomy above
2. **Common errors** — things candidates consistently got wrong
3. **Good practice notes** — what high-scoring candidates did
4. **Specific traps** — e.g. "forgetting +C", "not checking second derivative sign", "using degrees instead of radians"

Stored in `examiner-insights.json` keyed by topic, then merged into each question record and into the topic pages.

Example output:
```json
{
  "topic": "calculus-optimisation",
  "pitfalls": [
    "Failing to verify it is a maximum/minimum using the second derivative",
    "Not stating the value of x AND the optimised quantity — both required for full marks",
    "Forgetting to check boundary conditions in closed-interval problems"
  ],
  "good_practice": [
    "Clear labelling of dA/dx = 0 step before solving",
    "Showing d²A/dx² < 0 explicitly with a conclusion statement"
  ],
  "frequency": 14
}
```

---

## Phase 4 — Content Generation

For each topic with ≥5 question instances across years:

### 1. Topic summary
- What Edexcel tests in this topic (patterns observed from data)
- Mark allocation trends (e.g. "optimisation questions are typically 6–9 marks")
- Frequency chart: how many times this topic appeared per year per paper

### 2. Guided approach template
A generalised step-by-step method for the most common question pattern, e.g. for `calculus-optimisation`:

> **Step 1** — Identify the quantity to optimise (usually area, volume, cost, distance). Write it as a function of one variable only. You'll need a constraint equation to eliminate a second variable.
>
> **Step 2** — Differentiate and set equal to zero. Solve for x.
>
> **Step 3** — Verify nature using second derivative. State conclusion clearly.
>
> **Step 4** — Find the optimal value and answer the question in context with units.

### 3. Worked examples (interactive)
For 3–5 representative questions per topic:
- Full question text with rendered LaTeX
- Mark-scheme-aligned solution broken into steps
- Each step hidden behind a "Show hint" / "Show step" button
- Examiner notes for any step where reports flagged errors

### 4. Examiner pitfall panel
A dedicated callout box per topic, pulled from examiner insights, listing the 3–5 most cited errors with advice on how to avoid them.

---

## Phase 5 — Web App Build

### Homepage (`index.html`)

A visual grid of all topics, each card showing:
- Topic name
- Number of past paper questions in the bank
- Frequency badge (how often it appears)
- Difficulty indicator
- Link to topic page

### Per-topic page structure

```
[Topic Name]  e.g. Calculus — Optimisation
─────────────────────────────────────────
 Overview           What Edexcel tests here
 Appears in         Paper 1 ████████ 14x | Paper 2 ██ 3x
 Typical marks      6–9 marks, position Q7–Q11

 ┌─ Guided Approach ──────────────────────────┐
 │  Step 1: Set up the function               │
 │  Step 2: Apply constraint                  │
 │  Step 3: Differentiate & solve             │
 │  Step 4: Verify & conclude                 │
 └────────────────────────────────────────────┘

 ⚠ Examiner Pitfalls
   • Not verifying nature of stationary point
   • Missing units in final answer
   • [...]

 ┌─ Worked Examples ──────────────────────────┐
 │  Example 1 — 2023 Paper 1 Q8 (7 marks)    │
 │  [Question text]                           │
 │  [Animation: graph with sliding tangent]   │
 │                                            │
 │  [Show Step 1]  [Show Step 2]  [Full Sol.] │
 └────────────────────────────────────────────┘

 ┌─ All Past Paper Questions ─────────────────┐
 │  Filter: [All Years ▾] [All Patterns ▾]   │
 │  2022 P1 Q9  •  2021 P1 Q7b  •  ...       │
 └────────────────────────────────────────────┘
```

### Interactivity (Alpine.js + vanilla JS)

- Step-by-step reveal with "Show hint", "Show step", "Show full solution" buttons
- Collapsible examiner notes per step
- Year/pattern filter on the question index
- Progress tracking (localStorage) — tick off questions you've reviewed
- KaTeX rendering of all mathematical expressions

### Animations (JSXGraph + SVG/GSAP)

| Topic | Animation |
|---|---|
| `calculus-optimisation` | Interactive graph: drag a slider to show f'(x)=0 at turning point, shaded regions |
| `integration` (area) | Area under curve building up as definite integral bounds adjust |
| `newton-raphson` | Animated convergence: tangent lines stepping toward root |
| `trigonometry` (unit circle) | Rotating point on unit circle mapping to sin/cos graph |
| `vectors` | 3D interactive vector diagram with dot product display |
| `normal-distribution` | Bell curve with draggable bounds, shaded probability area |
| `kinematics` (suvat) | Velocity-time graph with acceleration shading |
| `projectiles` | Animated parabolic path with horizontal/vertical component decomposition |

---

## Phase 6 — Polish & Quality Pass

1. **Cross-reference check** — verify every examiner pitfall maps to at least one question example that demonstrates it
2. **Coverage audit** — flag any topic with fewer than 3 examples (may need to pull from specimen papers or IAL papers)
3. **LaTeX review** — manually verify any questions where PDF extraction produced garbled maths
4. **Navigation** — add breadcrumbs, "related topics" links (e.g. optimisation → differentiation → chain rule)
5. **Print-friendly CSS** — each topic page should print cleanly as a revision sheet

---

## Subagents run in parallel

| Agent | Task |
|---|---|
| **Scraper A** | Pure 1 papers + mark schemes (9MA0/01) |
| **Scraper B** | Pure 2 papers + mark schemes (9MA0/02) |
| **Scraper C** | Stats & Mechanics + all examiner reports |
| **Classifier A–D** | One per year range (2018–19, 20–21, 22–23, 24+) |
| **Examiner analyst** | All examiner reports → insights JSON |
| **Content gen A** | Pure topics (algebra through proof) |
| **Content gen B** | Stats & Mechanics topics |
| **UI builder** | Homepage + shared assets + animations |

---

## Prerequisites before starting

1. **Install Playwright MCP and Filesystem MCP** as shown in Phase 0
2. **Create the project directory**: `mkdir ~/edexcel-maths`
3. **Restart Claude Code** so it picks up the new MCP config
4. **Confirm the output format** — plan targets a self-contained static web app (no server needed, opens in browser)
5. **Optionally**: if PMT or Edexcel require a login for any resources, handle authentication in the scraper

Once those are in place, say "ready to start" and Phase 0 (project structure + scripts) and Phase 1 (scraping) begin simultaneously.
