# Skill: Examiner Report Extraction (Pearson Edexcel)

> This is step 5 of the end-to-end pipeline in `docs/skill-add-papers-pipeline.md`; start there when adding papers.

## When to Use
When adding examiner-report data to the RAG knowledge base for papers whose questions are already in `data/processed/questions/`. Examples: a new sitting (June 2025), Paper 3 (Stats/Mech), or AS 8MA0. The result is verbatim "did well", "pitfall" and "general" notes per question and part, plus per-question performance (mean marks, % full marks, and difficulty ratings backed by quotes).

First used 2026-09-25 for all 14 A Level Pure papers (2018–2024), producing 2,795 notes. The per-paper rules that agents follow live in `docs/examiner-notes-extraction.md`. This file covers the end-to-end procedure around those rules.

## Prerequisites
- The question JSON for the paper already exists: `data/processed/questions/<paper>_<sitting>.json`. The notes reference its question IDs, and `build_db.py` rejects unknown ones.
- `.venv/` exists, and poppler is installed (`pdftotext`, `pdftoppm`).
- `data/processed/schema.sql` has the `examiner_notes` and `question_performance` tables.
- The scripts `scripts/build_db.py` (including `load_examiner_notes`) and `scripts/check_examiner_notes.py` exist.

## The Non-Negotiable Rule
**Examiner commentary is never invented, paraphrased or summarised.** Every `quote` must be a verbatim slice of the report text. This is enforced by code, not by trust: `find_quote_page()` in `build_db.py` normalises whitespace and typographic quotes/dashes, then requires the quote to be a substring of the report `.txt`. If it isn't, the build fails. Never weaken this check to make a file pass.

---

## Step 1: Find and download the reports

**Source:** Pearson hosts them, not PMT. PMT's `MA` folders are PMT's own model answers, not examiner reports.
```
https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/<file>.pdf
```
Filenames are listed in `docs/pmt-url-patterns.md` → "Examiner Reports". The format changed in 2022:
- 2018–2021: `9MA0_0N_pef_YYYYMMDD` (uppercase, underscores)
- 2022+: `9ma0-0N-pef-YYYYMMDD` (lowercase, hyphens)
- The date is the results-release date, so P1 and P2 share it. Autumn 2021 reports are titled "November 2021" but belong to our `Oct2021` sitting.

**For a new sitting, find the filename first.** Search the web (e.g. `Pearson Edexcel 9MA0 01 examiner report pdf June 2025`), or guess from the pattern and probe it:
```bash
B="https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials"
curl -sk -o /dev/null -A "Mozilla/5.0" -w "%{http_code} %{content_type}\n" "$B/9ma0-01-pef-20250814.pdf"
```
You want `200 application/pdf`. A `302 text/html` means the wrong name. Always send a browser-like User-Agent.

**Download and convert.** Use `-raw`, not `-layout`:
```bash
cd ~/edexcel-maths && D=data/raw/examiner-reports && mkdir -p $D
while read loc f; do
  curl -sk -A "Mozilla/5.0" -o "$D/${loc}_ER.pdf" "$B/$f.pdf"
  pdftotext -raw "$D/${loc}_ER.pdf" "$D/${loc}_ER.txt"
  printf "%-14s %s | %s\n" "$loc" "$(file -b $D/${loc}_ER.pdf | cut -c1-12)" \
    "$(grep -m3 -E 'Summer|October|November|Paper 0' $D/${loc}_ER.txt | tr -s ' ' | tr '\n' ' ')"
done <<'EOF'
P1_June2025 9ma0-01-pef-20250814
P2_June2025 9ma0-02-pef-20250814
EOF
```

**Verify each file:**
- It is a PDF.
- The header names the right sitting and paper. The 2018/2019 headers say "Pure Mathematics Paper 1 (9MA0/01)" further down.
- `grep -c -E '^\s*Question [0-9]+'` roughly matches the paper's question count.

**Survey the reports before extracting:**
```bash
for f in $D/*_ER.txt; do printf "%-18s mean:%-3s pages:%-3s runtogether:%s\n" $(basename $f) \
  "$(grep -c -i 'mean mark' $f)" "$(grep -c $'\f' $f)" "$(grep -o -E '\b[a-z]{18,}\b' $f | wc -l | tr -d ' ')"; done
```
- `mean` > 0 means the report has "Question N (Mean mark X out of Y)" headings (only P1 2019 and P1 2022 did).
- `runtogether` > 0 means pdftotext dropped spaces, and agents must restore them in `display`.

Raw PDFs and `.txt` files stay local (gitignored under `data/*`).

### Why `-raw`
The pilot used `-layout`. It spliced inline maths from neighbouring lines into the middle of sentences (e.g. "which 2 y x( x − 6) without any appreciation of gained only the first mark"), which left about 40 repairs per paper. `-raw` keeps prose in reading order and only garbles the maths itself. The trade-off: in some reports `-raw` runs words together ("verystraightforward"). That's handled by `display`.

---

## Step 2: Extract one paper per agent

**Parallelism:** run at most 5 agents at once (CLAUDE.md), one paper each. Top up as each finishes rather than waiting for a whole batch. Agents run in the background; don't poll them.

**Agents must NOT run `scripts/build_db.py`.** It deletes and recreates `questions.db`, and one agent's broken file would fail everyone's build. They validate with the per-file checker instead:
```bash
.venv/bin/python scripts/check_examiner_notes.py <paper>_<sitting>
```
This runs the same `load_examiner_notes` checks against an in-memory DB.

**Agent prompt template** (fill in `<PAPER>` e.g. `P1` and `<SITTING>` e.g. `June2025`; `<STEM>` = `<PAPER>_<SITTING>`):
```
You are extracting examiner-report notes for an A Level maths revision chatbot in the repo /Users/i1003721/edexcel-maths.

Read and follow EXACTLY the spec at /Users/i1003721/edexcel-maths/docs/examiner-notes-extraction.md.

Paper: <PAPER> <SITTING>.
- Report text: /Users/i1003721/edexcel-maths/data/raw/examiner-reports/<STEM>_ER.txt (read all of it)
- Report PDF (reference for garbled maths; use the Read tool with `pages`): /Users/i1003721/edexcel-maths/data/raw/examiner-reports/<STEM>_ER.pdf
- Question JSON (question numbers, marks, part labels): /Users/i1003721/edexcel-maths/data/processed/questions/<STEM>.json
- Output: /Users/i1003721/edexcel-maths/data/processed/examiner_notes/<STEM>.json

Extra rule on ratings: if the report's introduction and the question's own section characterise difficulty differently, base the rating on the question's own section (it is more specific), and mention the disagreement in your final reply. Also: if the report quotes a function/expression that differs from the question JSON's text, list it in your final reply (it may reveal a transcription error in our data).

Rules: quotes must be copied verbatim from the .txt (building them programmatically from the text file via a script in <SCRATCHPAD> is fine and recommended). Never paraphrase or invent. Only write the single output file — do not edit any other repo file and do NOT run scripts/build_db.py (other agents run in parallel). Validate with: `cd /Users/i1003721/edexcel-maths && .venv/bin/python scripts/check_examiner_notes.py <STEM>` and fix until OK.

Final reply (concise): notes by kind, performance rows (how many with mean_mark / rating), numbering mismatches or questions with no report section, count of non-null `display`, the list of unresolved garbled-maths notes, and any judgement calls you were unsure about.
```

**Why "build quotes programmatically":** the agents that did best wrote a small scratchpad script that slices each quote out of the whitespace-collapsed `.txt` using start and end anchors. Retyping quotes by hand causes near-miss failures.

**For a new kind of paper** (Stats/Mech, AS, a different board), extract **one pilot paper first**. Review it (Step 3) and adjust `docs/examiner-notes-extraction.md` before fanning out. The pilot here caught the `-layout` problem, which saved re-doing 13 papers.

---

## Step 3: Review each agent's report as it lands

Read every hand-back for four things, and act on them:

1. **Checker status.** It must say `OK`. If the agent reports a failure it couldn't fix, the fix happens in the JSON, never in the checker.
2. **Suspected transcription errors in our question data.** This is the highest-value by-product. For each one:
   - Compare our JSON with the mark scheme text.
   - If it's still unclear, render the question-paper page and look at it:
     ```bash
     for p in $(seq 1 48); do pdftotext -f $p -l $p data/raw/papers/<STEM>_QP.pdf - 2>/dev/null | grep -q -i "<phrase from question>" && echo $p; done
     pdftoppm -f <page> -l <page> -r 110 -png data/raw/papers/<STEM>_QP.pdf <scratchpad>/qp
     ```
     Then Read the PNG.
   - Many "mismatches" are false alarms. The report may quote the inverse function or the factorised form, or the report may have a typo. Fix our data only when the PDF confirms the error.
   - When you fix one, keep the JSON diff minimal. Re-serialise with the file's original escaping (`json.dumps(d, indent=2)`; the question files use `\u` escapes) and append a provenance line to that question's `notes`.
   - Example: P1_June2024_Q9 had `3^(2k-1)` where the PDF shows `3^(2(k-1))`. The marks still summed to 100, so only this cross-check caught it.
3. **Errors in the report itself** (e.g. "θ ≈ 2θ", "Q13(b)" inside the Q12 section). Keep them verbatim and add them to the review file. The bot's display policy for these is a human decision.
4. **Rating judgement calls.** Collect the borderline ones for the review file.

---

## Step 4: Rebuild and run cross-paper checks

```bash
.venv/bin/python scripts/check_examiner_notes.py      # all files
.venv/bin/python scripts/build_db.py                  # full rebuild, same checks
```
Then query `questions.db` for problems the per-file check can't see:

| Check | Query idea | Action |
|---|---|---|
| Every question has notes | `questions` rows not in `examiner_notes.question_id` | Find out why (a missing report section?) |
| Bare fragments | notes under 6 words, e.g. `'2 69%'` | See the table rule below |
| Run-together words with no display | quotes with `display IS NULL` matching `[A-Za-z]{19,}` | Add a spacing-only display (below) |
| Part labels are well formed | `part_label NOT GLOB '[a-z]*'` | Fix the label |
| Rating coverage | whole-question rows with a rating | Only a sanity check. Unrated is fine when the report is silent. |
| Density | notes per question, avg/max | Informational (about 13 on average here) |

**Tables in reports** (e.g. "% of candidates scoring full marks"):
- Don't keep one-line notes per row.
- Quote the whole table once as a paper-level `general` note.
- Put the numbers in `question_performance.full_marks_pct`, with `full_marks_pct_note_id` pointing to that note.

**Spacing-only `display` fixes** must pass this guard, which proves no letters changed:
```python
sq = lambda t: "".join(t.split())
assert sq(display) == sq(quote)
```

---

## Step 5: Write the human review checklist

Generate or refresh `docs/examiner-notes-review.md`. Use a fixed random seed so the sample can be reproduced. It should contain:
1. **10 random notes**, each with id, part, kind and PDF page (the `page` column is computed at build time from `\f` page breaks). The reviewer checks the question/part/kind assignment against the PDF.
2. **10 random `display` repairs**, showing the quote and display side by side for comparison with the PDF.
3. **Flagged items:**
   - data errors found and fixed;
   - report errors;
   - unresolved garbled maths;
   - rating-policy inconsistencies;
   - borderline ratings.
4. **A coverage summary table.**

The user ticks the boxes. Don't mark human-review items as done yourself.

---

## Step 6: Commit (only with the user's approval)

- **Commit:**
  - `data/processed/examiner_notes/*.json`
  - any corrected `data/processed/questions/*.json`
  - schema and script changes
  - updated docs
- **Don't commit:**
  - `data/raw/` (the reports and their text)
  - `questions.db` (regenerated)
  - `scripts/__pycache__/`
- Show the diff summary and ask before committing. Never push without the user's go-ahead.

---

## Lessons Learned (2026-09-25 run)
- **Only 2 of 14 reports give mean marks.** Difficulty mostly has to come from wording ("most challenging", "accessible"), so every rating must cite its evidence note.
- **The "question's own section beats the intro" rule arrived late.** P2_June2019 was rated from the intro. Give agents this rule from the start.
- **Agents split paragraphs finely**, giving 8–20 notes per question rather than 3–8. That's acceptable for retrieval, but expect about 150–300 notes per paper.
- **Agents with the PDF resolved almost all garbled maths.** Only 1 of about 1,000 repairs was left unresolved.
- **Some reports print the question's functions differently** (factorised, or the inverse). Always check before "fixing" our data.
- **The Agent tool once rejected parallel calls silently** (in the question-extraction pass). If that happens again, fall back to running the extraction in the main session.

## Files
| File | Role |
|---|---|
| `docs/examiner-notes-extraction.md` | Per-paper rules for agents (JSON format, `kind`/`display`/rating rules) |
| `docs/pmt-url-patterns.md` | Pearson report URL formats |
| `scripts/build_db.py` | `normalise()`, `find_quote_page()`, `load_examiner_notes()`: the verbatim and ID checks |
| `scripts/check_examiner_notes.py` | Per-file validation for parallel extraction |
| `data/processed/schema.sql` | `examiner_notes`, `question_performance` |
| `docs/examiner-notes-review.md` | Human review checklist (regenerate per run) |

## Other subjects and boards [adapt]
- **Pearson (Further Maths, Stats/Mech components):** same "Principal Examiner Feedback" format under `.../Exam-materials/`. Filenames use the paper code, e.g. `9fm0-3a-pef-…`. Find them with a web search and probe with curl before writing the list.
- **AQA (e.g. Physics 7408):** examiner reports are "Report on the Examination" PDFs from aqa.org.uk, and the user already has `AQA-74081-WRE-*.PDF` in the repo root. They use `01.1`-style question numbers, and there are no mean marks, though some list "% of students scoring full marks". Map `01.1` → `part_label` "01.1". The verbatim-quote check works unchanged.
