# Edexcel Maths Revision Site

> **Branch `commercial-clean-room`:** building the copyright-clean product to sell. Read
> `docs/handoff-clean-room.md` first. The Pearson-based tutor stays on `main`. No Pearson text may
> enter prompts, the product or its content packs (see the abstraction firewall, §3 of the handoff).

## Project Overview
Interactive revision tool for Edexcel A Level (9MA0) and AS Level (8MA0) Mathematics. Self-contained HTML pages per topic with worked examples from real exam papers, step-by-step reveals, KaTeX maths rendering, and links to original papers via PMT.

## Live Site
https://hblbennett-arch.github.io/edexcel-maths/output/index.html (A Level)
https://hblbennett-arch.github.io/edexcel-maths/output-as/index.html (AS Level)

## Project Structure
```
edexcel-maths/
├── output/                  # A Level (9MA0) site
│   ├── index.html           # Topic navigator (16 topics)
│   └── topics/              # One HTML file per topic
├── output-as/               # AS Level (8MA0) site
│   ├── index.html           # Topic navigator (23 topics)
│   └── topics/              # One HTML file per topic
├── data/raw/                # NOT in git (see .gitignore)
│   ├── papers/              # A Level PDFs + .txt extracts
│   ├── markschemes/         # A Level mark schemes
│   ├── as-papers/           # AS Level PDFs + .txt extracts
│   └── as-markschemes/      # AS Level mark schemes
├── docs/                    # Workflow documentation
│   ├── topic-page-builder.md    # How to build topic pages at scale
│   └── pmt-url-patterns.md     # PMT download URL formats
├── PLAN.md                  # Original project plan
└── CLAUDE.md                # This file
```

## Tech Stack
- **KaTeX CDN v0.16.9** — maths rendering (inline `\( \)` and display `\[ \]`)
- **JSXGraph CDN v1.8.0** — interactive mathematical diagrams (see `docs/skill-jsxgraph-diagrams.md`)
- **Vanilla JS** — step reveals, tab switching, no framework
- **Single self-contained HTML per topic** — no build step, all CSS inline
- **pdftotext (poppler)** — PDF → text extraction (install: `brew install poppler`)

## Key Conventions

### HTML Template Pattern
Every topic page follows the same structure. Use any existing page (e.g. `output/topics/calculus-optimisation.html`) as the template. Key CSS classes:
- `.worked-example` — container for one exam question
- `.step-reveal` / `.step-reveal-header` / `.step-reveal-content` — collapsible steps
- `.motivation` — "Thinking:" reasoning block
- `.mark-award` — marks earned badge
- `.examiner-note` — examiner tip
- `.algebra-chain` — sequential algebra steps
- `.formula-box` — highlighted key formula

### Building New Topic Pages
See `docs/topic-page-builder.md` for the full workflow. In short:
1. Download papers from PMT (see `docs/pmt-url-patterns.md` for URLs)
2. Convert to text: `pdftotext file.pdf file.txt`
3. Read template + paper text files, write new topic HTML
4. Use parallel agents (max 5 at a time) for bulk page creation
5. Update index.html cards from "coming" to "ready"

### Formula Booklet Tags
All Key Formulae sections use colour-coded tags to distinguish what's given vs what must be memorised:
- `<span class="formula-tag booklet">In formula booklet</span>` — green badge
- `<span class="formula-tag learn">Learn this</span>` — amber badge

**IMPORTANT: Always verify classifications against the actual formula booklet PDF before publishing.**
LLM training knowledge of booklet contents can be wrong. Download the official booklet from Pearson (for 9MA0/8MA0) or the relevant exam board, and check each formula group manually.

CSS for the tags lives inline in each page's `<style>` block (search for `.formula-tag`).

### JSXGraph Diagrams
See `docs/skill-jsxgraph-diagrams.md` for the full pattern. Key rule: **never initialise a JSXGraph board while its container is hidden** (`display:none`). Use lazy initialisation — hook into the tab-switching function and init the board on first reveal with a `setTimeout(..., 50)`.

### PMT Paper Links
Papers are linked via PMT viewer URL format:
```
https://www.physicsandmathstutor.com/pdf-pages/?pdf=https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FMaths%2FA-level%2FPapers%2FEdexcel%2F{path}
```

## Skill Files (Reusable for New Projects)
These docs cover patterns that transfer directly to any similar revision site (e.g. AQA Physics):

| File | Contents |
|------|----------|
| `docs/skill-jsxgraph-diagrams.md` | JSXGraph lazy-init, colour scheme, common element types |
| `docs/skill-formula-audit.md` | Level-appropriate formula checking, mark scheme verification |
| `docs/skill-local-preview.md` | Start/stop local preview server commands |
| `docs/skill-worked-example-style.md` | Worked example style guide (motivation blocks, algebra chains, etc.) |
| `docs/topic-page-builder.md` | End-to-end pipeline: PMT download → PDF extract → topic pages |
| `docs/pmt-url-patterns.md` | PMT download URL formats (Edexcel Maths — use as pattern for other subjects) |

## DO NOTs
- Do NOT commit files from `data/` (PDFs are large, text extracts are working files)
- Do NOT use any work/corporate MCP servers or credentials
- Do NOT add build tooling — the site is intentionally zero-build static HTML

## GitHub
- Repo: github.com/hblbennett-arch/edexcel-maths
- GitHub Pages enabled from `main` branch root
- Owner: hblbennett-arch
