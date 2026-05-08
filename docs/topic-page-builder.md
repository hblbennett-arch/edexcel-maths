# Topic Page Builder Workflow

## End-to-End Pipeline

### 1. Download Papers from PMT
```bash
# Discover URL patterns by scraping the PMT page
curl -sk "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers-{slug}/" | grep -oi 'href="[^"]*download[^"]*"' | sort -u

# Download all papers/mark schemes using discovered patterns
curl -o "filename.pdf" "https://pmt.physicsandmathstutor.com/download/Maths/A-level/Papers/Edexcel/{path}"
```
- See `pmt-url-patterns.md` for exact URL formats
- Check file sizes after download: `find dir/ -size -1k -delete` removes 404 error pages saved as files

### 2. Convert PDFs to Text
```bash
brew install poppler  # if not already installed
for f in *.pdf; do pdftotext "$f" "${f%.pdf}.txt"; done
```
- pdftotext produces lossy maths (unicode pi, garbled fractions) — sufficient for topic identification but not display
- Always use the original PDF via PMT viewer links for student reference

### 3. Categorise Questions by Topic
Use a research agent to read all QP + MS text files and produce a categorisation like:
```
Topic: [name]
Papers: P1_June2022 Q8 (7 marks), P2_Oct2020 Q12 (10 marks), ...
Key patterns: [what the questions test]
```

Strategy:
- Launch 1-2 Explore agents that read ALL paper text files
- Ask them to list every question number, its topic, and mark allocation
- Group by topic to decide which pages to build

### 4. Build Topic Pages (Parallel Agent Strategy)

**Critical pattern: batch 5 agents max at a time, each fully independent.**

Each agent prompt must include:
1. The template file path to read (e.g. `output/topics/calculus-optimisation.html`)
2. Which paper/MS text files to read for source questions
3. The exact output file path
4. Clear instructions on what topic to cover

Agent prompt template:
```
Read the template at [path] for HTML structure, CSS, and JS patterns.
Read the following paper files: [list].
Read the following mark scheme files: [list].

Build a complete self-contained HTML page for the topic "[Topic Name]" covering:
- [specific sub-topics]

Requirements:
- Use EXACTLY the same HTML structure, CSS, JS as the template
- Include 3-5 worked examples from actual exam questions
- Each example needs: question text, step-by-step reveal, mark scheme info
- Use KaTeX for all maths (\( inline \) and \[ display \])
- Include PMT viewer links to original papers
- Include motivation/thinking blocks showing examiner perspective
- Write to: [output path]
```

### 5. Update Index Page
After all topic pages are built, edit the index.html:
- Change class from `"coming"` to `"ready"` on each card
- Change badge text from "Coming soon" to "Live"
- Replace disabled `<span>` with working `<a href="topics/filename.html">`

## Template Structure (CSS Classes)

### Required Layout
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <!-- KaTeX CDN v0.16.9 (CSS + JS + auto-render) -->
  <style>/* All CSS inline */</style>
</head>
<body>
  <header> <!-- Topic title, spec reference, nav link back to index --> </header>
  <main>
    <section class="topic-intro"> <!-- Overview, key formulas --> </section>
    <section class="worked-example"> <!-- One per exam question --> </section>
  </main>
  <script>/* KaTeX auto-render + step reveal logic */</script>
</body>
</html>
```

### Key CSS Classes
| Class | Purpose |
|-------|---------|
| `.worked-example` | Container for one exam question |
| `.step-reveal` | Collapsible step container |
| `.step-reveal-header` | Clickable header (shows ▶/▼) |
| `.step-reveal-content` | Hidden content revealed on click |
| `.motivation` | "Thinking:" block showing reasoning |
| `.mark-award` | Badge showing marks earned |
| `.examiner-note` | Tip from examiner's perspective |
| `.algebra-chain` | Sequential algebra steps |
| `.formula-box` | Highlighted key formula |
| `.topic-intro` | Opening section with overview |

### KaTeX Usage
- Inline: `\( expression \)` (auto-rendered)
- Display: `\[ expression \]` (auto-rendered)
- Auto-render config: `{delimiters: [{left:"\\(",right:"\\)",display:false},{left:"\\[",right:"\\]",display:true}]}`

### Step Reveal JS Pattern
```javascript
document.querySelectorAll('.step-reveal-header').forEach(header => {
  header.addEventListener('click', () => {
    const content = header.nextElementSibling;
    const isOpen = content.style.display === 'block';
    content.style.display = isOpen ? 'none' : 'block';
    header.querySelector('.arrow').textContent = isOpen ? '▶' : '▼';
  });
});
```

## Common Pitfalls

1. **PMT URLs are fragile** — always verify with curl before bulk download. "October" vs "Oct" vs "November" varies by level.
2. **AS Paper 2 split** — 2018 was combined (Stats+Mech), 2019+ has separate "(Stats)" and "(Mech)" booklets with different filenames.
3. **Agent file reads** — agents have full file access but giving them too many files makes output worse. 3-5 paper files + 3-5 MS files is optimal.
4. **KaTeX escaping in HTML** — backslashes need doubling in some contexts. Use `\(` not `\\(` in the HTML source (auto-render handles it).
5. **Large agent batches** — more than 5 simultaneous agents causes quality issues. Wait for a batch to finish before launching the next.
6. **Index page edits** — each card edit must be unique (use surrounding topic name for context). Don't try to do all 14+ edits in one Edit call.

## Scaling to New Exam Boards / Levels

1. Find the PMT page URL (e.g. `physicsandmathstutor.com/maths-revision/[board]-[level]/`)
2. Scrape for download links to discover URL patterns
3. Download + convert to text
4. Categorise with Explore agents
5. Build topic pages with parallel agents using existing template
6. Create index page with filter buttons matching paper structure
7. Cross-link to other index pages

## File Naming Conventions

| Level | Papers | Mark Schemes |
|-------|--------|--------------|
| A Level | `P{N}_{Session}{Year}_QP.txt` | `P{N}_{Session}{Year}_MS.txt` |
| AS Paper 1 | `ASP1_{Session}{Year}_QP.txt` | `ASP1_{Session}{Year}_MS.txt` |
| AS Paper 2 | `ASP2_{Session}{Year}_{stats\|mech}_QP.txt` | `ASP2_{Session}{Year}_{stats\|mech}_MS.txt` |
| AS Paper 2 (2018) | `ASP2_June2018_QP.txt` | `ASP2_June2018_MS.txt` |
