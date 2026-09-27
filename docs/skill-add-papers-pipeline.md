# Skill: Adding Papers to the Chatbot Knowledge Base (any subject)

## When to Use
Adding exam papers to the RAG knowledge base: a new sitting of an existing paper (e.g. 9MA0 June 2025), a new paper of an existing subject (Paper 3 Stats/Mech), a new qualification (Further Maths 9FM0, AS 8MA0) or a new board/subject (AQA Physics 7408). This is the hub. Each step links to its detailed spec.

The first build (A Level Pure, 14 papers, Sept 2026) ran these steps as separate expensive passes and learned what goes wrong. Following this order, **a new sitting of an existing paper costs roughly a fifth of the original per-paper cost.**

## The pipeline at a glance

| # | Step | Tool / spec | Cost | Human? |
|---|---|---|---|---|
| 1 | Find & download QP, MS, examiner report | `scripts/build_sources.py`, `docs/pmt-url-patterns.md` | tiny (scripts) | – |
| 2 | Extract questions **in final form** (parts, verbatim, LaTeX) | `docs/question-extraction-spec.md` | **high** (one agent per paper) | – |
| 3 | Cheap scripted checks | `build_db.py`, `check_notation.js --questions`, `split_parts.py`, `find_figures.py` | tiny | – |
| 4 | Audit vs official PDFs | `docs/ms-audit-spec.md`, `scripts/apply_ms_audit.py` | medium (one agent per paper) | spot-check report |
| 5 | Examiner-report notes | `docs/skill-examiner-report-extraction.md` | medium (one agent per paper) | spot-check |
| 6 | Tag question type + part skills | `docs/tagging-spec.md`, `scripts/check_tags.py` | low (2–3 papers per agent) | only if new skills proposed |
| 7 | Rebuild + review checklist | `build_db.py` | tiny | yes |

Steps 4 and 5 are independent, so run them in parallel.

## Step 1: Sources
- **Pearson (preferred; every Edexcel qualification, 2005 to now):** `scripts/scrape_pearson.py --catalogue`, then `--download`. It queries Pearson's own past-papers search index, downloads QP/MS/ER into `data/raw/pearson/<qualification>/<sitting>/`, checks each is a real PDF, runs pdftotext, and writes `manifest.json` plus the completeness table `docs/pearson-coverage.md`. Then run `scripts/build_sources.py` to merge the papers into `sources.json`. Details: `docs/pmt-url-patterns.md` → "Pearson past papers".
- **Existing subject:** rerun `.venv/bin/python scripts/build_sources.py --verify`. It re-scrapes PMT's listing pages and lists new sittings automatically. Then download the PDFs for the new `paper_id`s into `data/raw/papers/` and `data/raw/markschemes/`. Convert with `pdftotext` (use `-raw` for examiner reports).
- **Examiner reports:** Pearson hosts them, not PMT. Filenames: `docs/pmt-url-patterns.md` → "Examiner Reports". Add each confirmed file to `PEARSON_ER_FILES` in `build_sources.py`.
- **[adapt] New subject or board:** add its listing page to `LISTING_PAGES` and extend `URL_RE` for its filename pattern. PMT's physics pages use e.g. `.../Physics/A-level/Past-Papers/AQA/Paper-1/QP/June 2019 QP.pdf`. Probe a few URLs with `curl -sI` first, and record the pattern in `docs/pmt-url-patterns.md`. AQA publishes examiner reports on aqa.org.uk (the user has already uploaded some 74081 WRE PDFs to the repo root).
- **Formula booklet / data sheet:** download the **official PDF** and confirm with `file` that it really is a PDF. The 9MA0 "booklet" sat in the repo for months as a saved 404 page, and the site's formula badges were set without it. 8 turned out wrong. **[adapt]** AQA Physics uses the "Data and Formulae Booklet".

## Step 2: Extraction (the expensive step: do it once, properly)
- Follow `docs/question-extraction-spec.md`: **one agent per paper**, reading the PDFs. The output is already split into parts, word for word, with no asides, and in LaTeX.
- Tell each agent to keep scratch files in its own folder, `scratchpad/<step>_<paper_id>/`. Parallel agents overwrote each other's `dump.py` in 2026.
- At most 5 agents at once. Top up as each finishes.
- **Pilot one paper first** for any new subject or board, review it, adjust the spec, then fan out. The examiner-report pilot caught a text-conversion problem that would have cost 13 re-runs.

## Step 2b: Spec filter (legacy and IAL papers)
Extraction agents write `data/processed/_staging/<paper_id>.json` with `spec_refs` on every part, plus `out_of_spec` on any part whose topic or method isn't in `data/processed/spec_9ma0.json` (transcribed from the official spec, checked by `scripts/check_spec.py`). `scripts/apply_spec_filter.py <paper_id>` then drops whole questions with any out-of-spec part into `_excluded/` and writes the rest to `questions/`. `--summary` gives the counts for the user.
- Generate agent prompts with `scripts/make_prompts.py extract --todo --limit 5`; never hand-type paper fields.
- Each agent self-checks with `scripts/check_questions.py <paper_id>`. It checks fields, ids, marks against the QP's printed totals, derived texts, spec refs, KaTeX and asides.

## Step 3: Scripted checks (free, always run)
```bash
.venv/bin/python scripts/split_parts.py          # 0 to split, 0 failures (fill_gaps keeps parts contiguous)
.venv/bin/python scripts/find_figures.py --write # qp_pages, has_figure, figure_pages
node scripts/check_notation.js --questions       # every $…$ renders
.venv/bin/python scripts/build_db.py             # marks sum, labels, IDs, sources, examiner-note quotes
```
**[adapt]** `split_parts.py` and `find_figures.py` assume Edexcel layout: "(a)" labels, "(3)" / "(3 marks)" mark tokens, and "(Total for Question N is M marks)" lines. For AQA (`01.1` labels, `[2 marks]`, no Total line), add a label/marks pattern per board rather than forking the scripts.

## Step 4: Audit (never skip)
Follow `docs/ms-audit-spec.md`, covering both `question_text` and `mark_scheme_text`. Agents write change lists to `data/processed/_ms_audit/<paper_id>.json`. `apply_ms_audit.py --check`, then `--apply`, validates and applies them, so nothing is edited by hand. `--report` produces `docs/ms-audit-report.md` for the human spot-check. With v2 extraction this should find far fewer errors; if it finds many, the extraction spec needs tightening.

## Step 5: Examiner reports
Follow `docs/skill-examiner-report-extraction.md`. Quotes must be verbatim, and `build_db.py` fails otherwise. Run it in parallel with step 4.

## Step 6: Tagging
- **Same subject:** follow `docs/tagging-spec.md` with the existing vocabulary (`data/processed/_vocab_compact.md`). Batch **2–3 papers per agent**, so the vocabulary is read once per agent rather than once per paper.
- **Question types for new papers:** the tagging agent picks from the existing 45 and proposes a new one only if nothing fits.
- **New skills:** tagging agents list "Suggested new skills". Add them to `tags.json` only after a human glance, then regenerate `_vocab_compact.md`.
- **[adapt] A new subject needs its own vocabulary.** Examples are Mechanics (SUVAT, moments, friction …), Statistics (binomial/normal distributions, hypothesis testing …), Further Maths (complex numbers, matrices …) and Physics (a skill layer and a separate "required practical" layer). That's a **one-off taxonomy build** per subject: one agent reads that subject's parts plus the spec, drafts types, groups and skills, and a human reviews before tagging.
  - **Cost:** it's the single most expensive step (Pure: ~340k tokens), so scope it to the new subject's parts only.
  - **Shared skills:** cross-subject skills (algebra, exam technique, `show-that-given-answer`, `accuracy-units-and-rounding`) should be **reused, not duplicated**. Keep one `tags.json` with a `subjects` field on groups, or one vocabulary file per subject that imports a shared core. Decide this when the second subject is added.

## Step 7: Rebuild and review
Run `build_db.py`, then `scripts/build_embeddings.py` (the search index refuses stale embeddings), then `python -m eval.retrieval` to confirm retrieval still meets its targets `python -m eval.chat_smoke` to replay the conversation regression cases, and `python -m eval.practice_eval` to check "give me a question on X" only returns questions tagged with X (target: ≥ 98% precision). After that, refresh the review checklists:
- `docs/examiner-notes-review.md`
- `docs/ms-audit-report.md`
- the taxonomy draft, if the vocabulary changed.

Human review comes before the bot shows new content to students.

## Keeping it cheap (token rules learned in 2026)
1. **Scripts before agents.** Anything deterministic (splitting, page finding, link scraping, validation, applying changes) is a script, and agents only do judgement work.
2. **Agents write change lists, scripts apply them** (audit, notation, tags). Change lists can be validated, repeated and reviewed, and parallel agents never edit the same file.
3. **Validators make agents self-correct.** Every agent step has a checker the agent must run until OK (`check_notation.js`, `apply_ms_audit.py --check`, `check_tags.py`, `check_examiner_notes.py`). That's cheaper than a human or orchestrator catching errors later.
4. **Compact inputs.** Give agents compact dumps (`_vocab_compact.md`, one line per part) instead of full JSON or long review docs.
5. **Batch where the context is shared.** Tagging and auditing need the same reference material for every paper, so batch 2–3 papers per agent. Extraction reads different PDFs each time, so use one paper per agent.
6. **Do it right in one pass.** The v2 extraction spec exists because four passes over the same text cost about 4× and still left errors.
7. **Pilot, then fan out,** for anything new.
8. **Don't re-read what a script can summarise.** The orchestrator should read agents' final reports and check counts, not re-open their files.
9. **A completeness pass is cheaper than a re-extraction.** When an audit shows content missing (not wrong), one call per paper that returns ADDITIONS only, guarded by verbatim/number/duplicate checks against the source text, costs ~$0.30/paper at Opus and leaves the checked transcription untouched.
10. **Each new deterministic check: run it on everything already built, straight away.** The GCE part-mark check found 2 real errors in files that had passed for weeks. Treat a new check's hits on old data as real until the PDF says otherwise.

## Subject-specific notes [adapt]
| Subject | Differences to plan for |
|---|---|
| Edexcel Paper 3 / AS Paper 2 | Split into Stats and Mech components. `paper_id` gets `_stats` / `_mech` (already done in `sources.json`). Stats uses statistical tables from the booklet. |
| Further Maths 9FM0 | Many optional papers (FP1, FS1, FM1, D1 …). `paper_id` needs the option code. Its formula booklet section is separate from the A Level Maths one. |
| AQA Physics 7408 | Part labels `01.1`, marks `[n marks]`, "levels of response" 6-markers (mark bands, not M/A codes), required practicals, and data-sheet constants. Units and significant figures are marked strictly, so the extraction spec's physics notes apply. |

## Measured costs (fill in as runs complete)
Tokens are the `subagent_tokens` in each agent's completion notification. Use them to estimate before any fan-out.

| Step | Model | Unit | Tokens (each) | Notes |
|---|---|---|---|---|
| Spec transcription (one-off) | sonnet | whole 9MA0 spec | 197k | 89 statements; 15 min |
| Extraction (pilot) | sonnet | P3_June2022_stats (6 Q, 50 marks, 13-page QP) | 113k | 2.7 min; OK first time; Q2 verified by hand |
| Extraction (pilot) | sonnet | P3_June2022_mech (5 Q, 50 marks, many MS alternatives) | 127k | 3.8 min; OK first time |
| Extraction (pilot) | sonnet | GCE2008_6684_June2012 (S2, 8 Q, 75 marks) | 127k | 4 min; 6/8 questions dropped (Poisson, continuous uniform, CRV pdfs, sampling distributions). Most of the cost went on transcribing dropped questions, which led to the triage-first rule |
| Extraction (pilot) | sonnet | IAL2013_WME02_June2017 (M2, 7 Q, 75 marks) | 132k | 4.6 min; 5/7 questions dropped (impulse, power, work–energy, centre of mass, collisions) |
| Extraction (pilot) | sonnet | IAL2018_WST02_Jan2022 (S2, 7 Q, 75 marks) | 144k | 5 min; 0/7 kept. Legacy papers now use triage-first (drops listed, not transcribed) |
| Extraction, Tier 1 workflow | sonnet agents | 13 × 9MA0 P3 papers | 1.68M total (~129k each) | 8.3 min wall-clock at 5 parallel; 13/13 passed the checker as then written, and the stricter checks added afterwards found 6 real errors in 3 papers (fixed with `fix_parts.py`) |

**Measured in dollars (Claude Code reports `total_cost_usd`; every call is logged to `logs/llm_calls.jsonl`), 2026-09-26, same paper IAL2018_WST01_Jan2023 (S1, 75 marks):**

| Method | Calls | Cost | Result |
|---|---|---|---|
| Agent (`claude -p` with tools, the v3 prompt) | 24 turns | **$0.99** | kept Q1,2,4,5; dropped Q3 (E/Var of a discrete RV) and Q6 (regression / PMCC formula), both correctly |
| Single-call, spec judged inside extraction | 2 (one retry) | $0.65 | wrongly kept Q6. Leniency seen twice, so the judgement was moved to triage |
| **Triage (`triage_spec.py`, text only) + single-call extraction of kept questions** | 2 | **$0.15 + $0.22 = $0.37** | same decisions as the agent; checker OK first time |
| Paper where triage keeps nothing (IAL2018_WST02_Jan2022) | 1 | **$0.15** | no extraction call at all |

Quality of single-call extraction vs agents, on 5 papers: identical questions, parts and marks; question text the same apart from formatting (`•` vs `$\bullet$`); mark schemes **more complete** (keeps the official "Notes" rules: allow / condone / M0 if …) but sometimes drops the scheme column's working line. The spec now asks for both.

**Cost levers and what they measured to be:** 110-dpi PNG pages are ~22% fewer tokens than PDF document blocks. `DISABLE_PROMPT_CACHING=1` drops input from ~$4 (1-hour cache writes) to ~$2.5 per million tokens. Trimming answer-space and marking-guidance pages removes 30–50% of pages. A retry doesn't hit the cache (it pays the full input again), so free deterministic `autofix` runs first, and the retry returns only the changed questions.

**Examiner notes, same paper (P3_June2022_stats):**

| Method | Cost | Notes | Report covered | Ratings |
|---|---|---|---|---|
| Agent (old prompt) | $0.95 | 103 | 90% | 13 |
| v1 single call, model copies quotes | $0.42 | 74 | 78% | 2, not adopted |
| Haiku, same v1 | $0.35 | 4 usable | n/a | 0, rejected (wrong question labels, 12 non-verbatim quotes) |
| **v2 "classify, don't copy"** (script splits sentences, model classifies; display repairs on flagged pages only) | **$0.18** | 84 | **92%** | 15 |
All 15 9MA0 Paper 3 reports with v2: $2.15 total, 1,093 notes, 0 non-verbatim.

**Blind audit, 3 papers × 2 methods:** agents 0 corrections / 4 omissions, single-call 0 / 3. Parity, but the audits were lenient (see review checklist §15).

**MS completeness pass (`ms_complete.py`, one call per paper), 6 audited Tier 2 papers, 2026-09-26:**

| Model | Cost (6 papers) | Recall of the audit's 20 MS omissions | Notes |
|---|---|---|---|
| Sonnet 5 | $0.63 | 3/20 | most of its output was for out-of-spec questions (correctly rejected) |
| **Opus 5.5** | $1.08 first run (uncached); $0.25 on repeat runs (input cache hits) | **20/20** (final script) | ~30 extra official lines beyond the audit; 0 wrong in the spot-check. Budget ~$0.18/paper |
Run-to-run variation is real: an earlier Opus run missed Jan 2022 Q3(ii)'s alternative method, and the next run found it.

**Tier 3 pilot (6 papers: GCE C1, C4, S1, M1 scan; IAL 2013 C12, S1 scrambled font), full chain via `run_tier.sh`:** $7.51 in total. Per step: triage $0.92 + re-asks $0.47 (mostly false alarms, since fixed), extraction $2.50 + retries $0.91, MS completeness $0.93, notes $0.96, tags $0.70, concept screen $0.11, page map $0.02. Old GCE mark schemes are sparse, so the completeness pass added 0–6 lines there (vs 18–28 on IAL 2013).

**Tier 3 full run (206 papers, GCE + IAL 2013), 2026-09-27, per step:** triage $33.00 + re-asks $2.17 (14, after the `neutral()` fix), extraction $72.91 + retries $29.09 (100 papers; most were checker false alarms since fixed, so expect far fewer), MS completeness $39.56, MS visual verification $42.11, concept screen $3.81, notes $25.08, tags $23.84 (Opus, 3 papers/call), page map $0.25 → **$271.81, ≈$1.32/paper**. Blind 6-paper Opus audit: 6 workflow agents, 653k subagent tokens, ~4 min.

**`ms_verify.py` pilot** (6 audited papers, pre-audit copies): 5/5 of the audit's MS maths errors found, 1 false positive (a correct "A1ft" → "A1"), which led to the mark-code guard; $0.99. Full Tier 3: 118 corrections, 6 rejected by the decimals guard, $41.12; 15/15 spot-checked correct.

**Triage v1 → v2:** v1 set `in_spec` before writing its reason and once contradicted itself (M1 Jan 2024 Q8). v2 puts the reason first, adds a script contradiction check that re-asks, and routes borderline cases to the human list instead of "when in doubt, OUT". It matches the agents' decisions on the 4 comparison papers.
