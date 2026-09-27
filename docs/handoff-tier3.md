# Handoff: MS completeness pass + Tier 3 + audit (written 2026-09-26)

> **DONE 2026-09-27.** All steps below are complete: see `docs/review-checklist.md` §23–24 for results and the review items. Kept for the record.

**For:** a new Claude Code session in `~/edexcel-maths`. **Read this first, then** `.claude/skills/add-exam-papers/SKILL.md` (the runbook), then skim `docs/review-checklist.md` §12–22 (what's been done and found) and `docs/skill-add-papers-pipeline.md` → "Measured costs".

## Standing instructions from the user (all still apply)
- **Never commit or push, and don't ask to.** Nothing is committed since `41193df`.
- **Log every human-review item** in `docs/review-checklist.md` as it comes up (next section: §23), and say how many were added.
- **Record every optimisation or lesson in the skills** (`.claude/skills/add-exam-papers/SKILL.md`, `docs/skill-add-papers-pipeline.md`, including measured costs), and **add deterministic checks wherever you can think of one** (in `scripts/check_questions.py` or a new script), so validation doesn't rely on the model.
- **Accuracy must stay as close as possible to the original agent workflow.** Measure new methods against a known answer before using them at scale.
- **After extraction, run a blind Opus 5.5 audit on a subset** (as for Tier 2: `docs/prompts/audit-paper.txt`, symbol-focused, one agent per paper, workflow with ≤5 in parallel).
- **Scope:** 9MA0 (current) + IAL 2018 + IAL 2013 + UK GCE (pre-2017), filtered to `data/processed/spec_9ma0.json`. **Legacy Stats/Mech: S1 and M1 only** (`scripts/scope.py`); S2/S3/M2/M3 stay scraped but unprocessed, and the already-processed ones are parked in `data/processed/_parked/`. No Further Maths.
- **Out-of-spec questions never reach or influence the chatbot** (the build guard enforces this); their record stays in `data/processed/_excluded/`, and the raw PDFs in `data/raw/pearson/`.
- The user is new to dev tooling: give step-by-step instructions. They opted in to **workflows** for fan-out. At most 5 agents or calls in parallel.
- LLM calls run on the user's Verisk Claude Enterprise login via `claude -p` (`scripts/claude_oneshot.py` logs the real cost of every call to `logs/llm_calls.jsonl`).

## State right now
- The chatbot DB has **1,068 questions** (210 original Pure, 88 9MA0 Paper 3, IAL 2018 Pure/S1/M1), 11,235 verbatim examiner notes, all tagged (Opus), with figure pages. All checks pass: `check_questions.py` (165 staging files OK), `check_examiner_notes.py`, `check_tags.py`, `completeness.py` (0 gaps), `eval.retrieval` (24/24 references, 100% pasted), `eval.chat_smoke` (10/10).
- Start the UI: `cd ~/edexcel-maths && .venv/bin/python -m chatbot.web` → http://127.0.0.1:8765
- **`scripts/ms_complete.py` is written but has NEVER BEEN RUN.** Review it before use. It adds missing official mark-scheme content per part, one Sonnet call per paper, with a verbatim guard against the MS text layer, and writes an "Official notes (completeness pass):" block.

## Next steps, in order
1. **Pilot `ms_complete.py`** on the 6 audited Tier 2 papers, to a copy, not staging:
   `cd scripts && ../.venv/bin/python ms_complete.py IAL2018_WMA11_June2019 IAL2018_WMA11_Jan2022 IAL2018_WST01_Oct2023 IAL2018_WME01_Jan2025 IAL2018_WME01_June2025 IAL2018_WST01_Jan2024 --out ../data/processed/_ms_complete_trial`
   - **Score it against the audit's 27 known omissions** (`data/processed/_audit_t2/audit/*.json`, field `omissions`): how many does it recover, how many additions are rejected by the verbatim guard, and are any accepted additions wrong or duplicated? Log the cost.
   - If recall is poor, try Opus (as with tagging: Sonnet got 75%, Opus 93%). Only adopt it if it's measured to help.
   - Then decide the model and run it on staging for Tier 1/2: `--todo --only '^(P3|IAL2018)_'`, then `apply_spec_filter.py --all`, `park_units.py --park`, rebuild. Don't overwrite a paper twice: it skips files that already have `ms_complete_method`.
2. **Add `ms_complete.py` to `scripts/run_tier.sh`**, after extraction and before the spec filter. Also add `page_map.py` for scanned papers (no usable text and not a shifted font) before the spec filter, so figures get pages.
3. **Tier 3:** `scripts/run_tier.sh '^(IAL2013|GCE2008)_' > logs/tier3.log 2>&1` (in the background). That's 206 papers (GCE C1–C4/M1/S1; IAL 2013 C12/C34/M1/S1 + Jan 2014 C1–C4), estimated ~$110–140. It runs extract (with triage) → spec filter → concept screen → notes → tags → review list → completeness.
   - Pilot 1–2 papers of each new layout first (a GCE C-unit, an old GCE S1/M1 with "(Total N marks)", an IAL 2013 C12). GCE layouts differ from IAL.
   - 22 Tier 3 question papers use the scrambled font. The checker now decodes it (`decode_shifted`); watch these papers.
   - Every FAIL: look at the PDF page before fixing. Fix false alarms in the checker, and real errors with `scripts/fix_parts.py` (merge / split / marks / replace). A verified exception goes in `check_overrides` (match + evidence + verified_by).
4. **Blind Opus audit of a Tier 3 sample** (~6–8 papers across GCE and IAL 2013, Pure/S1/M1). Compare the error rates with Tier 2's (1 symbol error in ~1,010 expressions; ~4.5 missing MS notes per paper before the completeness pass).
5. Rebuild (`build_sources.py`, `build_db.py`, `build_embeddings.py`), run `eval.retrieval` + `eval.chat_smoke`, add Tier 3 reference cases (e.g. "C1 June 2012 Q3", "S1 January 2013 Q2"), and update review checklist §23 + the skills + `docs/rag-chatbot-plan.md`.

## Lessons that matter for Tier 3 (details in the checklist)
- The model can **reconstruct** text from the MS when a QP page is missing, so `FABRICATION_RE` hard-fails it. Page trimming must keep all pages for scanned or scrambled PDFs (now does).
- **Stem/part duplication** (58 in Tier 2) is now prevented and checked.
- **Spec-filter misses:** triage let Further Maths vector/volume questions through. `concept_screen.py` (model + precise text check, one paper per call) is now in `run_tier.sh`, and the verified concept list is in the triage prompt. GCE C4 has vector equations of lines, the scalar product and volumes of revolution, so expect many drops there.
- **Tagging uses Opus 5.5** (measured parity with the agents). Stats/Mech vocab includes all Pure skills.
- A minus-sign text check was tried and dropped (it can't tell subtraction from a negative sign).
- zsh doesn't word-split `$IDS`: use `xargs`.
- The review items waiting on the user are in the checklist, notably `docs/taxonomy-draft-stats-mech.md` (Mech approved, Stats as drafted), `docs/spec-triage-review.md` (section B), `docs/tag-suggestions.md`, and the spot-checks of figures and questions.

## Suggested first message for the new session
> Read docs/handoff-tier3.md and follow it: pilot ms_complete.py first and report the score against the audit's omissions before running it anywhere else.
