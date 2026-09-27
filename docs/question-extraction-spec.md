# Question Extraction Spec (single pass, v2)

How to turn a question paper (QP) and its mark scheme (MS) into `data/processed/questions/<paper_id>.json` **in its final form in one pass**: split into parts, verbatim wording, LaTeX notation. The first build (2026) did extraction, part-splitting, auditing and notation as four separate passes over every paper. Each pass re-read everything, and the audit still found 106 errors. This spec folds the lessons of all four into the extraction itself. The later steps then become cheap scripted checks plus one audit.

Subject-neutral: it works for Edexcel Maths/Further Maths/Stats/Mech and AQA Physics. Subject-specific details are marked **[adapt]**.

## Inputs
- `data/raw/papers/<paper_id>_QP.pdf` (+ `.txt` from `pdftotext`)
- `data/raw/markschemes/<paper_id>_MS.pdf` (+ `.txt`)

**Read the PDFs, not just the .txt.** pdftotext drops signs, powers, roots, modulus bars, fraction bars, δ, degree signs and whole symbol-font expressions. Use the Read tool with `pages` for every page with maths on it. The .txt is only a convenience for copying prose.

## Output format
```json
{ "_paper": "P1", "_sitting": "June2025",
  "questions": [ {
    "id": "P1_June2025_Q7", "spec": "9MA0", "paper": "P1", "sitting": "June2025", "q_num": "7",
    "total_marks": 8,
    "stem": "Shared preamble before the first part label, verbatim.",
    "parts": [ { "label": "a", "marks": 3, "text": "(a) ... (3)", "mark_scheme": "(a) M1: ... A1: ..." } ],
    "question_text": "<stem + newline + each part text joined by newline>",
    "mark_scheme_text": "<each part mark_scheme joined by newline>",
    "source_qp_file": "papers/P1_June2025_QP.txt", "source_ms_file": "markschemes/P1_June2025_MS.txt",
    "low_confidence": false, "notes": "", "notation": "latex" } ] }
```
- `question_text` / `mark_scheme_text` are **derived**: build them by joining `stem` and the parts, never by typing them separately.
- A single-part question has one part with `"label": null`, and `stem` = that part's `text`.
- **The stem is only the shared preamble printed before the first part label.** Never copy a part's wording into the stem, and never repeat the stem's sentences inside a part. Text between parts goes at the start of the next part. (Tier 2 had 58 duplications of this kind, all fixed and now caught by `check_questions.py`.)

## Parts [adapt]
- A part is the smallest unit with its own marks **on the question paper**. "(a)(i) … (ii) … (3)" is one part `"a"`; "(b)(i) … (2) (ii) … (1)" is two parts, `"b(i)"` and `"b(ii)"`.
- Labels are lowercase: `a`, `b(i)`, `ii`, `ii(a)` (for letters under a roman numeral).
- Question text between parts ("Using the iteration formula … with x₁ = 2,") belongs to the **next** part. Mark-scheme notes between parts belong to the **previous** part.
- Part marks must sum to `total_marks`, and the whole paper must sum to its printed total (100 for Edexcel A Level Pure).
- **[adapt] AQA** numbers parts `01.1`, `01.2`; use those strings as labels. The QP shows marks as `[2 marks]`, and there is no "(Total for Question N is M marks)" line.

## Verbatim, not paraphrase
The 2026 audit's errors were almost all paraphrase that drifted from the source:
- **Question text: copy it exactly as printed.** Keep every condition (`x ∈ ℝ`, `k ∈ ℤ⁺`, `n ∈ ℕ`), relation symbol (`=`, `≡`, `≈`, `<` vs `≤`), modulus bar, domain and the given form of a function. Found errors included:
  - a missing modulus in H = |A sin(bt+α)|;
  - a reversed domain;
  - ≤ where the paper has <;
  - a function replaced by its simplified form (which gives away working);
  - a sentence moved away from where the paper has it.
- **Mark scheme: keep the official content and order.** For each mark give the code (`M1`, `dM1`, `A1*`, `B1ft`, `A1cso` …) and the official criterion. Keep these:
  - official **alternative methods** ("Way 2", "Alt"), labelled as such, never merged into one method;
  - **special cases** (SC), `awrt`/`cao`/`oe`/`isw` qualifiers, and conditions such as "dependent on …" or "ft their …";
  - **notes that change what earns a mark** (e.g. "M0 if they …").
- **No extractor commentary.** No "(i.e. …)", "(since …)", worked arithmetic the MS doesn't show, explanations of why a step works, and never "wait/hmm/actually" asides. If an explanation really helps, put it in `notes`, not in the text.
- **Check the maths.** Recompute each final answer from your transcription. Several 2026 errors were caught only because the transcribed working didn't give the MS's answer, e.g. r = −1/3 where it should be −1/√3, or 10^x where the MS means ¹⁰√x.

## Notation
Follow `docs/notation-spec.md`:
- all maths in `$…$`;
- `\frac`, `\sqrt[n]{}`, `^{…}`;
- upright function names `\mathrm{f}(x)`;
- `\leqslant`/`\geqslant`, `^\circ`;
- mark codes and part labels stay as plain text.

**[adapt] Physics:** units in `\text{}` with a thin space, e.g. `$9.81\,\text{m s}^{-2}$`. Keep significant figures exactly as printed.

## Figures
Don't describe figures in the text. The pipeline records figure pages (`scripts/find_figures.py`) and sends the page image to the model. Keep references like "Figure 3 shows …" exactly as printed.

## Uncertainty
If anything can't be settled from the PDF, set `low_confidence: true` and write exactly what's uncertain in `notes`. Never guess silently.

## Validate (run all; fix until clean)
```bash
.venv/bin/python scripts/build_db.py                 # parts sum to totals, labels valid, JSON shape
node scripts/check_notation.js --questions           # every $…$ renders in KaTeX
.venv/bin/python scripts/split_parts.py              # dry run: should report 0 to split, 0 failures
```
Then run the audit pass (`docs/ms-audit-spec.md`) as an independent check.

---

# v3 additions: Statistics, Mechanics, IAL and legacy papers (from 2026-09-25)

Everything above still applies. These rules add the fields needed for Paper 3 (Stats/Mech) and for the International A Level (IAL) and old UK GCE papers used as extra question sources. Paper files come from Pearson (`scripts/scrape_pearson.py`); see `docs/pearson-coverage.md`.

## Inputs
- `data/raw/pearson/<qualification>/<sitting>/<paper_id>_QP.pdf` / `_MS.pdf` (+ `.txt` from `pdftotext -layout`).
- **Some PDFs have no text layer** (scanned; e.g. 9MA0 June 2019 Paper 3). The `.txt` is then empty, so read every page from the PDF.
- `data/processed/spec_9ma0.json`: the 9MA0 content statements (`ref`, `text`, `guidance`). This is the only list for `spec_refs` and for spec judgements. **Never judge from memory of the syllabus.**
- `data/formula-booklet-9MA0.pdf` when a method's inclusion depends on the booklet.

## Output: `data/processed/_staging/<paper_id>.json`
Write to `_staging/`, never to `questions/`. `scripts/apply_spec_filter.py` moves kept questions to `questions/` and dropped ones to `_excluded/`.
```json
{ "_paper_id": "IAL2018_WST01_Jan2020", "_paper": "WST01", "_sitting": "Jan2020",
  "qualification": "IAL-2018", "unit": "WST01", "component": "stats", "status": "legacy",
  "paper_total": 75,
  "source_qp_file": "pearson/IAL-2018/Jan2020/IAL2018_WST01_Jan2020_QP.txt",
  "source_ms_file": "pearson/IAL-2018/Jan2020/IAL2018_WST01_Jan2020_MS.txt",
  "questions": [ {
    "id": "IAL2018_WST01_Jan2020_Q3", "paper_id": "IAL2018_WST01_Jan2020",
    "spec": "IAL-2018", "qualification": "IAL-2018", "unit": "WST01", "component": "stats", "status": "legacy",
    "paper": "WST01", "sitting": "Jan2020", "q_num": "3", "total_marks": 9,
    "uses_large_data_set": false,
    "stem": "…", "parts": [ { "label": "a", "marks": 2, "text": "(a) … (2)", "mark_scheme": "(a) M1: … A1: …",
                              "spec_refs": ["S2.1"] } ],
    "question_text": "…", "mark_scheme_text": "…",
    "source_qp_file": "…", "source_ms_file": "…", "low_confidence": false, "notes": "", "notation": "latex" } ] }
```
- `paper_id` naming: 9MA0 is `P3_June2019_stats`, `P3_June2019_mech`, `P3_June2018` (the combined 2018 paper), `P1_June2025`. Others are `<IAL2018|IAL2013|GCE2008>_<unit><variant>_<sitting>`, e.g. `IAL2018_WMA11_Jan2020`, `IAL2018_WMA11A_June2025`, `GCE2008_6663R_June2014`, `IAL2018_WST03U_Jan2022` (U = an unused contingency paper Pearson published). For 9MA0, `_paper`/`paper` is `P1`–`P3`; for the rest, the unit code. `sitting` never carries the `_stats`/`_mech` suffix.
- Copy the paper-level fields from `data/raw/pearson/manifest.json` (the orchestrator puts them in your prompt). `status` is `current` for 9MA0 and `legacy` for everything else.
- `component` per question: `pure` | `stats` | `mech`. The combined June 2018 Paper 3 has Section A (stats) and Section B (mech). A Section B heading doesn't restart the numbering.
- `paper_total` = the printed paper total (e.g. "TOTAL FOR PAPER: 75 MARKS"). For 9MA0 Paper 3 use the component booklet's printed total (e.g. 50).
- `uses_large_data_set`: true only for 9MA0 questions that rely on the Large Data Set (they name it or its weather stations). Always false for IAL and GCE.

## `spec_refs`: tag every part with the 9MA0 content it uses
- List every `spec_9ma0.json` statement the part needs, usually 1–4, in the part's own component (a Mech part can also need Pure refs, e.g. calculus in kinematics). Tag from the part's text **and** its mark scheme.
- Assumed GCSE knowledge needs no ref, but a part must still have at least one ref unless it's `out_of_spec`.
- **Also tag the modelling and judgement statements when marks reward them,** not just the obvious distribution. For example, the P3 June 2022 Stats pilot tagged "expected profit per 500 rods" as `S4.2` + `S3.3` and "is the manufacturer likely to achieve its aim" as `S4.1` + `S4.3`.
- **Mechanics refs that overlap:** take moments → `M9.1`; resolve for a particle or body in equilibrium → `M8.4`; F = ma along a line → `M8.2`; resultant or vector forces → `M8.5`; friction and μ → `M8.6`. A part that does several of these gets all of them, e.g. "rod in limiting equilibrium, show μ = 8/19" → `M8.6` + `M9.1` (+ `M8.4` if it resolves).
- **Mark scheme content per part:** the scheme column's working lines with their codes (e.g. "$\mathrm{P}(X>110) \approx \mathrm{P}(Y>110.5) = …$ M1") **and** the official Notes that change what earns a mark (allow / condone / "M0 if …" / "no continuity correction gives 0.897 which is M0"). Pilots kept one and dropped the other.
- **Mechanics mark schemes often give several full alternative routes** (other resolving directions, moments about another point). Keep every official alternative, labelled. They are long, and that's expected.
- **Large Data Set conventions** (e.g. "how is a value of 0 < r ≤ 0.05 recorded?", answer "tr") have no numbered statement. Tag `S2.4` (data cleaning / recording) and add a `notes` line "LDS convention (spec other_requirements: large data set)".

## Triage first (legacy papers): don't transcribe what will be dropped
Pilots found most S2/S3/M2/M3 questions are outside 9MA0 (Poisson, continuous random variables, work–energy, impulse, centre of mass …). Transcribing them wasted most of each agent's budget. So, for IAL and GCE papers:
1. **Triage.** Read the whole QP and MS once, and decide each part in or out of spec against `spec_9ma0.json` (rules below).
2. **Transcribe only questions with every part in spec** into `questions` (full v3 format).
3. **List every other question in `excluded_questions`**, with marks and reasons only and no text:
   ```json
   "excluded_questions": [ { "q_num": "4", "total_marks": 14,
       "parts": [ { "label": "a", "marks": 3, "technique": "Poisson distribution",
                    "reason": "No Poisson statement in spec_9ma0.json (S4.1 covers binomial/discrete uniform only)" },
                  { "label": "b", "marks": 5, "technique": "binomial with a Poisson-derived p", "reason": "depends on (a)" } ] } ]
   ```
   Every part gets an entry with its printed marks; an in-spec part of a dropped question uses `"technique": "in spec"` plus `"reason": "question dropped: other parts out of spec"`. The checker requires the marks to sum to the printed totals.

## `out_of_spec`: legacy papers only
For IAL and GCE papers, a part whose question **or required method** is not in the 9MA0 spec gets:
```json
"out_of_spec": { "reason": "Poisson distribution is not in the 9MA0 specification (spec_9ma0.json has no Poisson statement; S4 covers binomial and normal only)",
                 "technique": "Poisson distribution", "spec_note": "closest: S4.1 — binomial" }
```
- Judge from `spec_9ma0.json`: quote or name the statement(s) you checked. The test is whether the spec's content and guidance cover it at this depth.
- **Methods count as well as topics.** If the mark scheme's only route needs a non-9MA0 method, the part is out of spec. If the MS gives an alternative in-spec method **that can earn full marks**, the part is in spec: keep it, and add a `notes` line naming the in-spec method. A special case (SC) capped below full marks (e.g. a Normal approximation worth 5/7 in a Poisson test) doesn't count.
- 9MA0 papers never carry `out_of_spec`.
- With triage, out-of-spec questions go straight to `excluded_questions`. The per-part `out_of_spec` field is for a question you did transcribe and then found out of spec; the script drops it too. Out-of-spec parts need no `spec_refs`.
- When unsure, set `low_confidence: true` and explain in `notes`. Don't guess silently.
- **A part that depends on an out-of-spec part's answer** (e.g. (b) uses the speed found by work–energy in (a)) needs no separate judgement: the whole question is dropped anyway. Tag it by its own method.
- **Unreadable symbols:** the `.txt` often garbles symbols (e.g. "í" for a minus sign), so read the PDF page image. If a symbol is still unreadable, transcribe what you can, set `low_confidence: true` and say exactly what's unclear in `notes`. **Never paraphrase or "describe" an official method in place of transcribing it.**

## Layout differences [adapt]
- **IAL** papers have the same layout as 9MA0: "(N)" marks and "(Total for Question N is M marks)".
- **GCE 2008–2019** prints "(Total N marks)" after each question, and older papers (2005–2007) often have no totals line; use the MS mark counts then.
- **Statistical tables and data inserts** are separate booklets and aren't transcribed. A question's own data table **is** transcribed, as a KaTeX array inside `$…$`:
  `$\begin{array}{|c|c|c|c|}\hline x & 1 & 2 & 3\\ \hline \mathrm{P}(X=x) & 0.2 & 0.5 & 0.3\\ \hline\end{array}$`
- **Diagrams:** keep "Figure N" references as printed, and don't describe figures. Mechanics diagrams (pulleys, inclined planes, forces) are sent to the model as page images.
- **Mechanics:** keep units and g exactly as printed (e.g. "Take $g = 9.8\,\mathrm{m\,s^{-2}}$", or the paper's own rubric), and put units in `\mathrm{}`.
- **Statistics:** keep hypothesis-test wording (H₀/H₁, significance level, one-/two-tailed) exactly, e.g. `$\mathrm{H_0}: p = 0.3$`, `$\mathrm{P}(X \leqslant 3)$`, `$X \sim \mathrm{B}(20, 0.3)$`, `$\mathrm{N}(\mu, \sigma^2)$`.

## Validate (run until OK)
```bash
.venv/bin/python scripts/check_questions.py <paper_id>
```
This checks the fields, ids, marks against the QP's printed totals, the derived texts, `spec_refs` and `out_of_spec`, KaTeX rendering and stray asides. Don't run `build_db.py`; other agents run in parallel.
