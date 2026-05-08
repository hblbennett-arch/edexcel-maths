# Edexcel Maths Revision Site

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

### PMT Paper Links
Papers are linked via PMT viewer URL format:
```
https://www.physicsandmathstutor.com/pdf-pages/?pdf=https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FMaths%2FA-level%2FPapers%2FEdexcel%2F{path}
```

## DO NOTs
- Do NOT commit files from `data/` (PDFs are large, text extracts are working files)
- Do NOT use any work/corporate MCP servers or credentials
- Do NOT add build tooling — the site is intentionally zero-build static HTML

## GitHub
- Repo: github.com/hblbennett-arch/edexcel-maths
- GitHub Pages enabled from `main` branch root
- Owner: hblbennett-arch
