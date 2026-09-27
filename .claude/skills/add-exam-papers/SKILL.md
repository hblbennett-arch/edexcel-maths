---
name: add-exam-papers
description: Orchestrator runbook for adding Edexcel/Pearson exam papers (new sittings, Stats/Mech, IAL or legacy GCE) to the edexcel-maths tutor knowledge base — scrape from Pearson, extract, spec-filter, audit, examiner notes, tag, rebuild. Use when asked to add, scrape, ingest or process past papers.
---

# Adding exam papers (orchestrator runbook)

The detailed specs live in `docs/`; this is the order of operations and the cheap way to run them. The hub is `docs/skill-add-papers-pipeline.md`. Read it once if you haven't this session.

## Standing rules (the user's)
- Never commit or push, and don't ask to. Log every human-review item in `docs/review-checklist.md`, and tell the user how many you added.
- Verify against official PDFs and the spec (`data/processed/spec_9ma0.json`), never memory. Examiner quotes stay verbatim.
- At most **5 agents** in parallel, each with its own scratch folder. Agents write one output file, and scripts apply and validate.
- The user is new to dev tooling, so give step-by-step instructions for anything they must do.

## 1. Sources (scripts only, no agents)
```bash
.venv/bin/python scripts/scrape_pearson.py --catalogue           # Pearson's Algolia index -> manifest
.venv/bin/python scripts/scrape_pearson.py --download [--only RE] # sequential; ~12 files/min
.venv/bin/python scripts/build_sources.py                        # merge into sources.json
```
- Read `docs/pearson-coverage.md` for gaps: 🔒 = teacher-login only (the last ~9 months), — = not published. Report gaps to the user; don't retry them.
- Scope lives in `UNITS` in `scrape_pearson.py`. Add a unit code there to widen it.
- A `.txt` under 2 KB means a scanned PDF. Agents must read it visually, and the printed-totals check can't run.

## 2. Extraction: single-call pipeline (default from 2026-09-26; measured ~60% cheaper than agents)
```bash
.venv/bin/python scripts/triage_spec.py <legacy ids> --report      # in/out per part + confidence (~$0.15/paper)
.venv/bin/python scripts/extract_single.py --todo --only '<regex>' --parallel 3   # ~$0.2-0.5/paper
```
- Legacy papers are triaged first (the spec judgement has its own focused call with the spec's explicit-exclusions checklist), and extraction transcribes only the kept questions. 9MA0 papers skip triage.
- Medium/low-confidence triage decisions are listed in `docs/spec-triage-review.md` for the user.
- Each file records `extraction_method` (`single-call-v1` | `agent-v3`) and `triage_method`.
- **Whole tier in one go:** `scripts/run_tier.sh '^IAL2018_' > logs/tierN.log 2>&1` (run in the background). It does extraction → **MS completeness pass (Opus)** → **page map for scans** → spec filter → concept screen → notes → tags → triage review list → `completeness.py`, and the final completeness report must show 0 gaps.
- After a run: every FAIL needs a look at the actual PDF page before fixing. Tier 2 showed ~60% of failures were checker false alarms (fix the checker) and ~40% real (fix with `fix_parts.py`). Record a verified exception as `check_overrides` (match + evidence + verified_by) in the staging file, never by weakening a check.
- **Figures:** `apply_spec_filter.py` fills in `qp_pages` / `has_figure` / `figure_pages` (via `find_figures.process_paper`). Never write question files any other way, or the figure pages are lost (this happened in Tier 2). For scanned PDFs run `scripts/page_map.py <ids>` before the spec filter. After a run, check `select count(*) from questions where has_figure=1 and figure_pages='[]'` is 0.
- **Accuracy benchmark before a big tier:** a blind Opus audit of ~6 random papers with `docs/prompts/audit-paper.txt` (symbol-focused). Tier 2's result: 1 symbol error in ~1,010 expressions, ~4.5 missing MS notes per paper. Re-run it on a Tier 3 sample.
- **MS completeness pass** after extraction, before the spec filter: `cd scripts && ../.venv/bin/python ms_complete.py --todo --only '<regex>'` (Opus by default: measured 20/20 recall of audited omissions vs Sonnet's 3/20, at ~$0.18/paper). Pilot with `--out <dir>` first; logs go to `<dir>/_log`. Guards: prose must be verbatim in the MS text, decimals must be in the MS, and duplicates are judged on prose, numbers and normalised LaTeX (prose alone wrongly drops working lines). It adds MS content only; question-text gaps (undescribed figures) need a separate fix.
- **Expect the completeness pass to add a lot on some papers** (Tier 2: up to 84 lines on WMA12 Jan 2022, where extraction had kept the scheme column and dropped all the official Notes). That's a real gap being filled, not noise: spot-check a few lines against the MS, don't cap it.
- **Unicode maths in model output:** `extract_single.unicode_prose_to_latex` converts it (used by extraction's autofix and by `ms_complete.py`). It leaves `$…$` and `$$…$$` alone and turns each run of neighbouring symbols into ONE span. Never "fix" touching spans with `.replace("$$", "")`: `$$…$$` is real display maths in ~35 staging files. If the checker reports a new symbol, add it to `UNICODE_TO_LATEX` rather than hand-editing.
- **Don't edit staging while a batch job is running on it** (`ms_complete.py`, `extract_single.py`): each job reads a file, calls the model, then writes, so a concurrent edit is lost. Queue fixes, then apply them with `fix_parts.py` after the job ends. A running job also keeps the code it started with, so fixes to scripts only apply to files processed later: re-check and repair the earlier ones afterwards.
- **Old "(Total N marks)" layout** (GCE, and some IAL 2018 papers): the checker now also runs its in-order part-mark check on this layout. On its first run it found 2 real Tier 2 over-splits (the model invented "(1)"/"(2)" brackets from MS marks where the QP prints one bracket for (i)+(ii)). The fix is `fix_parts.py merge`, then set the merged part's trailing mark to the printed total, and merge the part labels in `tags_assigned/<pid>.json` too.
- **Pick pilots from papers `--todo` will actually process** (QP *and* MS on disk). 13 Tier 3 papers have no published MS (GCE June 2007/2009, IAL C34 Jan 2020) and are skipped; `extract_single.py` now says so instead of crashing in `trim_pdf`.
- **Pilot the whole chain, not just extraction:** `scripts/run_tier.sh '^(ID1|ID2|…)$'` on the pilot IDs runs every step (all steps skip finished work), so the notes/tags/completeness steps meet the new layouts too. Tier 3's 6 pilots: $7.51 (~$1.25/paper; the 125-mark IAL C12/C34 ~$1.85). Budget from the pilot's per-paper figure, not the handoff's estimate.
- **Merged superscripts:** pdftotext writes 2.025¹⁰ as "2.02510". The model then tends to paraphrase ("$2.025$ raised to the power $10$"), which the verbatim check catches: fix it to `$2.025^{10}$` with `fix_parts.py replace`. The number check allows 1–2 merged superscript digits.
- **Scrambled font ligature:** the shifted font maps "fi" to "¿" ("signi¿cant ¿gures"). `decode_shifted` now converts it.
- **Triage's contradiction re-ask** used to fire on ~35% of papers because of phrases about OTHER content ("only binomial and Normal are covered", "no excluded concept", "even though X is in spec"). `triage_spec.neutral()` strips those first: 51 → 10 flagged on the Tier 2 files, and real contradictions are still caught. Each false re-ask cost ~$0.14.
- **Verified exceptions:** `scripts/add_override.py <pid> "<error-line prefix>" "<evidence with page>"` records a check_override after you've looked at the rendered page (`pdftoppm -f N -l N -r 75 -png <pdf> <out>`, then Read the PNG). Find the page with `pdftotext -f N -l N` + grep, not by guessing.
- **GCE false-alarm families (checker now handles them):** "aM1/bA1" method-prefixed mark codes; decimals grouped in threes after the point with a short last group ("0.354 030 19"); undecodable scrambled font (letters shifted by 29 with no control characters, e.g. "VLJQLILFDQW" = "significant"), where the Figure check now uses the letter stream; GCE C3/C4 mark schemes of ~2011–13 draw equations as vector graphics with no text (`pdfimages` finds nothing), so when ≥4 and >25% of a paper's MS decimals are missing the decimal check becomes a NOTICE listing the values. Real errors still found in GCE: a mark code dropped when the text layer shifts it a line (C1 June 2011 Q5(c)), and inline-image inequalities (C1 Jan 2008 Q8, transcription correct, override).
- **Triage a FAIL in one command:** `scripts/show_part.py <pid> Q7 a [word]` (or `--ms "<word>"`) prints the part's transcription, the matching text-layer lines, and the PDF pages containing the word, so you can go straight to `pdftoppm` for that page. Crop with `-x/-y/-W/-H` to read a small region at higher dpi.
- **Source text containing "$":** some fonts map letters to "$" in the text layer (29 source files). `prose_words(t, source=True)` must be used for PDF text so nothing between two "$" glyphs is dropped (it was, and made GCE M1 June 2017 Q7 look non-verbatim).
- **More GCE mark notation:** "A(2,1,0)" = one A mark worth up to 2; the checker counts it.
- **More number-layout variants now handled:** integer powers merged into the base ("3600" = 3^600, "812" = 81^(3/2)); letter-spaced digits ("1 .5 6 9 6"). A FAIL that disappears on re-check was a file caught mid-retry: always re-run `check_questions.py` on the paper before investigating.
- **Queue staging fixes while a batch step runs** (write them to a small script in the scratchpad) and apply them the moment that step ends: Tier 3's fixes went in between the completeness pass and the spec filter, so no paper was skipped. Steps that only touch scans (`page_map.py`) don't conflict.
- **Completeness-pass notation fixes now automatic:** "√52"/"3√11" become `$\sqrt{52}$`/`$3\sqrt{11}$` (√ with a number or single letter only); a quote right after a superscript (`'4\pi^2'`, which KaTeX reads as a prime) closes with `\text{'}`.
- **Comma lists vs thousands separators:** "180+19.47,180" is a list; only whole numbers (1–3 digits then groups of 3) are joined now. A wrong digit in a long decimal is a real error class (IAL C4 Jan 2014: 19.47180 for 19.47122): the MS-decimal check is what catches it, so never override one without reading the page.
- **Over-split sub-parts keep happening** (4 so far across Tiers 2–3): the model splits (i)/(ii) using the MS's marks where the QP prints one bracket. The in-order part-mark check catches it on every layout now; fix with `fix_parts.py merge` then `replace` the trailing mark.
- **Long runs survive sleep:** a laptop sleeping overnight just pauses `claude -p` calls; check `ls -la logs/*.log` times and `ps -o etime` on the `claude -p` processes before assuming a hang.
- **Tier 3 blind audit (6 papers, ~1,090 expressions) → a check for every finding type:**
  - *Lead-in lines between parts* ("Given that x₃ = 7,") were stuck after the previous part's "(N)" and autofix added a second "(N)": 11 of 18 corrections, and 126 parts across all tiers. Check: "text continues after its printed mark". Fix: `fix_parts.py --all-leadins` (a non-last part's lead-in moves to the next part; a last part's closing instruction stays before its mark). Extraction's autofix now does this itself.
  - *An instruction copied into more parts than the QP prints it*: check `repeated_beyond_qp` (counts the sentence in the QP text layer, so boilerplate the paper itself repeats is fine). 1 more case found in existing data.
  - *MS maths/value errors* (root span, dropped root, wrong fraction values, x for x/3: ~5 in 1,090, all in mark schemes, none in question text): text layers can't settle fraction/root structure, so `scripts/ms_verify.py` (Opus, one call per paper, MS page images at 130 dpi) returns corrections only, behind guards: `old` unique in the part, new wording and decimals in the MS text, new integer fractions visible in the MS layout (else held for review), and mark-code-only changes rejected when the existing code is in the text layer (the pilot's one false positive). Pilot: 5/5 of the audit's maths errors, $0.17/paper. It's in `run_tier.sh` after the completeness pass. The checker lists MS fractions not visible in the layout as a NOTICE.
  - *Mark labels* ("1st A1" vs "2nd A1"): no reliable deterministic signal (alternative methods restart the numbering), so none added.
  - *Pearson's own MS errors* (e.g. IAL S1 Jan 2014 Q6(c) σ range): kept as printed; log them for the user.
- Watch for **reconstructed text** (the checker's FABRICATION_RE) and **stem/part duplication**; both are hard failures now.
- In zsh, `$IDS` doesn't split into words: pass ID lists with `xargs` or `${=IDS}`.
- Tier 2 (IAL-2018, 144 papers): $104.67, 5 at a time, ~2 h wall-clock.
- The agent route below is still the fallback for papers the single call can't handle.

## 2 (fallback). Extraction by agents: one paper per agent
```bash
export SCRATCH=<session scratchpad>
.venv/bin/python scripts/make_prompts.py extract --todo --only '<regex>' --limit 5
```
**Preferred for more than 5 papers:** run the saved workflow `extract-papers` (`.claude/workflows/extract-papers.js`), which needs the user's opt-in to workflows, with `args: {prompt_dir: "<scratch>/prompts", papers: [...]}`. It keeps at most 5 Sonnet agents running and returns one structured result per paper (check_ok, counts, low_confidence, Pearson errors, spec feedback), so the orchestrator never reads transcripts. Otherwise, launch each agent by hand with **model: sonnet** and the one-line prompt: "Your complete task instructions are in `<printed path>`. Read that file first and follow it exactly. Work in /Users/i1003721/edexcel-maths."
- Template: `docs/prompts/extract-paper.txt`. Rules: `docs/question-extraction-spec.md` (v3 section).
- Top up to 5 as each one finishes, and don't poll. Read only each agent's final report, then run:
```bash
.venv/bin/python scripts/check_questions.py <paper_id>      # must print OK
.venv/bin/python scripts/apply_spec_filter.py <paper_id>    # kept -> questions/, dropped -> _excluded/
```
- `check_questions.py` compares every part against the question paper's own text: printed part marks **in order** (catches split/merged parts), verbatim prose, numbers in the text and mark scheme, mark-code counts, figure references, spec refs vs component and Unicode maths. On Tier 1 it caught 6 real errors that looked structurally fine. **Fix failures with `scripts/fix_parts.py` (merge / split / marks / replace), never by hand.** Each fix is logged in the question's `notes`.
- Papers with no usable text layer print a NOTICE (the text checks were skipped); log them for a human spot-check.
- **Out-of-spec questions never go downstream** (notes, tags, taxonomy, DB, embeddings). They live only in `data/processed/_excluded/`, and `build_db.py` refuses to build if one leaks in.
- **Pilot one paper for any new qualification or component** before fanning out. Fix the spec/template from its feedback, not individual files.

## 3–7. Checks, audit, examiner notes, tags, rebuild
Follow the hub doc (steps 3–7). Batch 2–3 papers per agent for the audit and for tagging. Examiner notes are one paper per agent. Stats/Mech need their own vocabulary, which the user reviews before any tagging.

## Cost notes (measured)
- Record each agent's `subagent_tokens` from its completion notification in `docs/skill-add-papers-pipeline.md` → "Measured costs", so future estimates are real numbers.
