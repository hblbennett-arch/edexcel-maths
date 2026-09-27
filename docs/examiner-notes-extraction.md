# Examiner Notes Extraction Spec

How to turn a Pearson "Principal Examiner Feedback" report into
`data/processed/examiner_notes/<paper>_<sitting>.json`.

## Sources
- Report text: `data/raw/examiner-reports/<paper>_<sitting>_ER.txt` (from `pdftotext -raw`; the PDFs sit alongside and are the reference for any garbled maths).
- Downloaded from `https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/`. See `docs/pmt-url-patterns.md` for the filenames.
- Question content (for mapping question numbers and part labels): `data/processed/questions/<paper>_<sitting>.json`.

## The one hard rule
**Every `quote` must be copied verbatim from the report text.** `scripts/build_db.py` fails the build if a quote (after whitespace/quote-mark normalisation) is not found in the source `.txt`. Never paraphrase, summarise, merge sentences from different places, or add words. If the report doesn't say something, it doesn't go in.

## JSON format
```json
{
  "_paper": "P1",
  "_sitting": "June2022",
  "source_file": "examiner-reports/P1_June2022_ER.txt",
  "notes": [
    {
      "id": "P1_June2022_Q15_n1",
      "question_id": "P1_June2022_Q15",
      "part_label": "a",
      "kind": "pitfall",
      "quote": "Unfortunately some solutions featured the volume of a sphere, which proved a costly error, from which there was no return.",
      "display": null
    }
  ],
  "performance": [
    {
      "question_id": "P1_June2022_Q15",
      "part_label": null,
      "mean_mark": 5.6,
      "max_mark": 10,
      "rating": "mixed",
      "evidence_note_id": "P1_June2022_Q15_n0"
    }
  ]
}
```

## Field rules
- **`id`:** `<question_id>_n<k>`, numbered from 1 in report order. Paper-level notes use `<paper>_<sitting>_G_n<k>`, with `question_id: null`.
- **`part_label`:**
  - Use the lowercase label as it appears in the question (`"a"`, `"b"`, `"b(i)"`, `"c(ii)"`).
  - Use `null` when the sentence is about the whole question.
  - Only assign a part if the report names it or the context makes it unambiguous.
- **`kind`:**
  - `did_well`: what candidates did successfully ("Part (a) was frequently correct…").
  - `pitfall`: a mistake, misconception, omission or lost-marks behaviour ("…applied it to both coordinates").
  - `general`: advice, context or overall comments that are neither ("As with other 'show' questions, sufficient detail has to be written…"). Advice that implies a common failing can be `pitfall` if the report says candidates actually did it.
- **`quote` length:** 1–3 consecutive sentences, as short as possible while still making sense alone. Split a paragraph into separate notes when it covers several points. A quote may start or end mid-sentence only if the rest is irrelevant.
- **`display`:**
  - Only use it when pdftotext garbled maths inside the quote (e.g. `3 1050` for ∛1050, `8x2` for 8x², or a dropped √, δ or fraction bar).
  - **Derive the repair by looking at the PDF page** (`data/raw/examiner-reports/<paper>_<sitting>_ER.pdf`; read it with the Read tool's `pages` parameter). Don't guess from the text alone.
  - Give the same sentence with *only* the maths repaired, written in LaTeX `$…$`; the words stay exactly the same.
  - Also use `display` when pdftotext ran words together (e.g. `verystraightforward`). Restore the spaces only; don't change any letters.
  - If the page is still unclear, set `display: null` and name the note under "unresolved" in your summary.
  - Otherwise `null`. Non-null `display` values are spot-checked by a human.
- **`performance`:** at most one row per (question, part).
  - `mean_mark`/`max_mark`: only if the report states them (e.g. "Question 15 (Mean mark 5.6 out of 10)").
  - `rating`: `well_answered` | `mixed` | `poorly_answered`. Only when the report explicitly characterises performance ("well answered", "most challenging", "few candidates scored full marks", "25% of the cohort achieved full marks"). `evidence_note_id` must point to the note quoting that statement; add a `general` note for it if needed. If nothing is explicit, omit the rating (use `null`) and don't infer it from the volume of criticism.
  - Include a row with just `mean_mark`/`max_mark` when a mean is given but there's no rating.
  - `full_marks_pct` + `full_marks_pct_note_id`: only when the report states the % of candidates scoring full marks for a question (e.g. the P1 June 2022 intro table). The note id points to the quote containing that figure. Don't create one-line notes for bare table rows; quote the whole table once as a paper-level note.
  - If the report's introduction and the question's own section disagree about difficulty, rate from the question's own section.
  - Rating guide:
    - `well_answered`: "accessible", "well answered", "most scored full marks";
    - `poorly_answered`: "challenging", "few candidates", "poorly answered";
    - `mixed`: the report explicitly says both, or calls the question "discriminating", or gives full/zero-mark percentages without a clear lean.
- Bullet-list fragments (e.g. a list of common errors) are fine as quotes. Keep the list's lead-in sentence as its own `general` note only if it adds meaning.

## Mapping report questions to our IDs
- Report "Question N" → `<paper>_<sitting>_Q<N>`. Check the topic and marks against the question JSON. If the numbering disagrees, or a question has no section in the report, say so in your final summary; don't guess.
- Some headings wrap or have trailing punctuation ("Question 1."). The intro paragraph may mention questions too: those notes belong to the question they describe, and use the right id.

## Coverage expectations
- Every substantive sentence about a question should end up in some note. Skip boilerplate (Pearson's "About Pearson" pages, copyright, grade-boundary blurbs).
- Typical density: 3–8 notes per question.

## After writing
Run `.venv/bin/python scripts/check_examiner_notes.py <paper>_<sitting>` from the repo root, and fix your file until it prints `OK`. This checks one file without touching `questions.db`, so parallel extractions don't collide. It proves every quote is verbatim and every ID resolves. The full `scripts/build_db.py` runs the same checks.
