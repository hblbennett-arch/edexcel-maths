# Plan: Edexcel Maths RAG Tutor Chatbot

## Context

The knowledge base (210 A Level Pure questions, 14 papers, marks verified to 100 per paper) is committed locally (`41193df`; push waits for your new GitHub token).

**Objective, in your words (summarised).** A student names or pastes a question they're stuck on. The bot then:
1. explains, part by part, where marks are awarded and the best way to start, in a scaffolded, accessible way;
2. backs this up with what students did well and the common pitfalls, **from real examiner reports**;
3. recommends similar questions for each technique in the question, then asks which part was hardest and refines the recommendations towards it;
4. handles generic questions ("how do I integrate x·eˣ?") via semantic search over techniques and questions;
5. later: stored, reviewed "how to get started" knowledge per part.

It is for both students and tutors.

**Audit problems that block this:**
- Only 22/210 questions have a technique tag. Recommendations need techniques on every part.
- `calculus-optimisation` is under-tagged (2 questions).
- 64 questions reference figures the bot can't see.
- Mark-scheme text mixes official wording with extractor commentary.
- Notation is inconsistent.
- There is no examiner-report data. This is now **core**, not backlog.

**Your decisions:**
- Restore the optimisation page and keep the tag.
- Split questions into parts.
- No API key yet: everything up to the model call is built and tested first.
- Web backend (FastAPI) comes much later; the front-end design is yours.

**Standing rules:**
- Never invent examiner commentary; every insight cites a real report.
- Verify booklet claims against `data/formula-booklet-9MA0.pdf`.
- Follow the mark-scheme method (`docs/skill-worked-example-style.md`).
- No Further Maths.
- Ask before every commit; no push until the token is ready.

## Amendments I suggest to the objective
1. **Hints first by default.** Each part opens with "how to start". The student asks for the next step or the full working. Tutor mode shows everything at once. This is the scaffolding, and v1 needs it (the model writes hints live from the mark scheme). Stored, reviewed hints (your "later" item) replace the live ones in Phase 7.
2. **Checkable citations.** Each examiner insight must quote a stored note by ID (e.g. *"Examiners, P1 June 2022 Q15(c): …"*). A validator drops any insight without a real note ID. If the question has no report note, the bot uses notes on *similar* questions, labelled as such, or says none exist.
3. **Confirm the question.** When a student names or pastes a question, the bot confirms the match ("Is this P1 June 2022 Q15, the cheese-shaped toy?") before teaching.
4. **Use examiner comments on difficulty in recommendations.** Parts the reports call "poorly answered" rank higher for practising that technique.
5. **Questions not in the DB** get the same flow, with no mark-scheme claims and a clear "no official mark scheme for this question" note.

## Execution order (agreed 2026-09-25)
1. Save this plan to the repo as `docs/rag-chatbot-plan.md`.
2. **Phase 3 (examiner reports) first:**
   - download all 14 PDFs;
   - extract notes with the quote check;
   - store `part_label` as plain text for now, and check it against `question_parts` once 2b lands;
   - you review before any commit.
3. Then Phase 2 → 4 → 5 → 6 as written.

---

## Status (2026-09-27): knowledge base = 2,702 questions
9MA0 (P1/P2 210, Paper 3 88) + IAL 2018 (770) + IAL 2013 (587) + UK GCE pre-2017 (1,046), in-spec only; 21,764 examiner notes; all tagged. Pipeline: `scripts/run_tier.sh` (triage → extract → MS completeness → MS visual verification → page map → spec filter → concept screen → notes → tags → completeness). See `docs/review-checklist.md` §22–24.

Practice lookup ("find me a question on X", `recommend.find_practice`, rebuilt 2026-09-27) has three channels:
1. **Exact maths** (`expression_hits`): an expression in the request ("x^x") found in the question LaTeX is listed first.
2. **Description** (`description_hits`): BM25 over whole questions with light stemming (dentists = dentist), used when no skill matches well ("dentists and 10% of customers arriving late"). The part to open is the part whose own text clearly matches best (`best_part`), else the whole question. Padded with the semantically closest questions, not with the weak skill's.
3. **Skill tags**: one technique → today's tagged-part ranking (unchanged). Several topics or skills ("differentiation, partial fractions and stationary points", "integration by parts and the trapezium rule") → `split_concepts` splits on commas/"and", resolves each piece to skills or a whole topic, and ranks questions by how many pieces they cover ("covers 2 of 3: …"). A single topic name ("vectors") counts all that topic's skills (`named_groups`).
Filters apply to every channel: component, already seen, "not a …", a year ("from 2019", "a 2019 question") and qualification ("IAL", "old spec"). The chat's `PRACTICE_RE` now also catches "can you find a question that…", "is there a question combining…".

Benchmark `eval/practice_search_eval.py` (seeded, no model; results in `eval/practice_search_results.txt`), before → after:
description recall@5 1% → **100%** (recall@1 0% → 96%); multi-topic "top result covers every topic" 27% → **95%**; multi-skill "top result has both skills" 48% → **93%**; hand cases 4/9 → **9/9**. `eval/practice_eval.py` unchanged (228/228 skills resolve, was 227; precision 1103/1106); retrieval 31/31, 0 wrong pasted.

Lessons (keep for later changes):
- **Calibrate thresholds on half the benchmark and confirm on the other half.** The calibrate/held-out numbers above agree within ~3 points, except multi-skill (97% vs 89%).
- **Skill similarity alone can't tell a technique from a scenario.** Technique requests go down to 0.685 (typos), scenarios up to 0.707. The tie-breaker is how much of the request is maths vocabulary (`maths_share`): 100% for techniques, median 0% for scenarios. Rejected: "the description hits carry the skill". Scenario words find same-topic questions, so it sent 5% of descriptions down the skill route.
- **BM25 beats embeddings for described scenarios** (top-1 97% vs 69%), because the distinctive words are rare nouns.
- **Multi-topic splitting:** re-join pieces only when one isn't a topic by itself, both mean the same area, the joined phrase is a skill's own name, or it matches ≥ 0.06 better. A looser join (0.0) swallowed "suvat" into "projectiles" (79% vs 97%). Give a skill near two topics to the closer one only. A topic name counts only that topic's skills ("quadratics" must not bring in trig quadratics).

## Status (2026-09-25): Phases 2 and 3 complete
| Step | Result |
|---|---|
| 2.0 Housekeeping | Optimisation page restored, notebook fixed, `requirements.txt`, `package.json` now has only KaTeX (dev) |
| 2a Optimisation re-tag | Merged into 2f: 5 questions in the two optimisation types |
| 2b Parts | 478 parts; marks verified; text between parts kept (`scripts/split_parts.py`) |
| 2c Figures & pages | 57 figure questions; `qp_pages` for every question (`scripts/find_figures.py`, `scripts/render_figure.py`) |
| 2d Audit | 106 corrections + 127 editorial wraps, all checked against the PDFs (`docs/ms-audit-report.md`) |
| 2e Notation | All 210 questions in KaTeX LaTeX (6,376 spans render); upright function names |
| 2f Tags | 45 question types, 141 skills in 31 groups; 1,523 part-skill tags (3.2 per part); formula-booklet flags checked against the real booklet |
| 2g Review | `docs/review-checklist.md` |
| 3 Examiner reports | 2,795 verbatim notes, 399 performance rows |
| Sources | `sources.json`: 64 papers with verified QP/MS/ER links |

Reusable procedures for future papers or subjects: `docs/skill-add-papers-pipeline.md` (hub), `docs/question-extraction-spec.md`, `docs/ms-audit-spec.md`, `docs/notation-spec.md`, `docs/tagging-spec.md`, `docs/skill-examiner-report-extraction.md`.

**Phase 4 done (2026-09-25):**
- `chatbot/` package: `identify`, `search`, `retrieve`, `recommend`, plus the demo `python -m chatbot`.
- Hybrid search with bge-small (local, no key): BM25 for recognising pasted questions, semantic for skills.
- `eval/retrieval.py`: references 16/16, pastes 30/30 (27 confident, 3 confirm), 0 false matches, generic recall@5 100%, recommendation checks 0 problems.

**Phase 5 done (2026-09-25), code complete; waiting on an API key for live answers:**
- `chatbot/tutor.py`: one structured Claude call per question (model **`claude-haiku-4-5`**, the user's choice, with a 4k thinking budget; JSON schema output; figure images). Opus 5 / Sonnet 5 remain a one-line switch (`TUTOR_MODEL`), with adaptive thinking, effort and refusal fallback applied automatically for them.
- `chatbot/validate.py`: checks mark codes, mark totals, final answers (sympy vs the MS, including exact LaTeX forms) and examiner note ids. The verbatim quote is inserted by code, with one targeted retry on failures.
- `chatbot/chat.py`: interactive loop (hints first, step reveal, part jump, hardest part → ladder, /tutor mode, follow-ups).
- `--offline` and `--dry-run` modes need no key. Tested with a simulated model (retry fixes planted errors) and with a fake key (the real API accepts the request shape).

**How to start:** `.venv/bin/python -m chatbot.chat`. The default backend is **Claude Code on the user's Verisk Enterprise login** (`claude -p`, Haiku 4.5, no API key). `TUTOR_BACKEND=api` plus a key uses the API instead. First real answers (2026-09-25): P1 June 2022 Q15 and P2 June 2019 Q13 both verified, about $0.05 and 45–70 s each.

**Local web UI for testing (2026-09-25):** `.venv/bin/python -m chatbot.web` (add `--offline` for no model) opens http://127.0.0.1:8765 with KaTeX-rendered chat, question and figure cards, and step/mark chips. `chatbot/controller.py` holds the conversation logic, shared with the terminal chat.

**Next:**
- Phase 6 (answer-quality testing), runnable now on the Claude Code backend (about $0.05 per question).
- Adding Stats/Mech and legacy/IAL papers, handed off to a new session: see `docs/handoff-stats-mech-legacy.md`.

## Phase 2 — Data fixes (≈3–4 sessions)
Each step ends with: `build_db.py` passes, notebook re-run, diff shown to you, commit on approval.

- **2.0 Housekeeping.**
  - `git restore output/topics/calculus-optimisation.html`.
  - Fix the stale `seed_questions.json` reference in `notebooks/explore_kb.ipynb`.
  - Ask you about the stray `package.json`/`node_modules`.
  - Add `requirements.txt`.
- **2a. Optimisation re-tag: merged into 2f (decided 2026-09-25).** Optimisation becomes a *question type* (narrow), and its component skills become part-level *skill* tags (broad); see 2f. Site error found: `output/topics/calculus-optimisation.html` lists "P1 Oct 2020 Q7" for the exponential stationary-point question, but it's Q9.
- **2b. Split into parts.**
  - Each question gains `stem` + `parts: [{label, marks, text, mark_scheme}]`, with labels like `"b(i)"` for sub-parts. The full texts are kept.
  - `scripts/split_parts.py` does a regex first pass on the `(a) … (N marks)` pattern; ambiguous cases go to a manual list.
  - `schema.sql` + `build_db.py`: new `question_parts` table; `question_tags.part_label` (NULL = whole question); the build fails if part marks ≠ total. Schema and build are updated together (earlier column-parity bug).
- **2c. Figures.**
  - `has_figure`, `figure_pages` found from the `\f` page breaks in `data/raw/papers/*_QP.txt` (`scripts/find_figures.py`).
  - `scripts/render_figure.py` uses `pdftoppm` to create PNGs in a gitignored cache, to attach as images.
  - Check: all 64 are found; 5 renders spot-checked.
- **2d. Separate official mark-scheme text from commentary.**
  - Subagents in batches compare each part's `mark_scheme` against `data/raw/markschemes/*_MS.txt`.
  - Unsupported additions get wrapped `[editor: …]`; nothing is deleted.
  - Output: `docs/ms-audit-report.md`, for your review.
- **2e. Notation → KaTeX LaTeX.**
  - One convention (`\alpha`, `\sqrt{}`, `\frac{}{}`, `e^{…}`), documented in CLAUDE.md.
  - Guards in `scripts/check_notation.js`: every `$…$` must render with `throwOnError`, and the set of numbers in each field must be unchanged before and after. Failures are fixed by hand.
- **2f. Two-layer tagging: question types (narrow) + skills (broad).** Decided 2026-09-25.
  - **Question type:** one per whole question, meaning "the exact same kind of question". Examples: `optimisation-constrained-shape` (cheese toy, storage tank) and `optimisation-modelled-quantity` (car's max speed, mice growth rate, ball's max height). Expect about 25–40 types.
  - **Skills:** several per *part* (typically 3–6), covering every skill the part tests. Examples: Q15(b) → `differentiate-negative-powers`, `set-derivative-zero-and-solve`, `solve-cubic-power-equation`. Expect about 100–150 skills, each with a parent group (about 30, e.g. *basic differentiation*), so the bot can fall back to the group when a skill is rare.
  - **Topics:** the 16 topics stay as the top-level grouping.
  - **Recommendations:**
    - "More like this" → the same question type.
    - "Struggled with part (b)" → parts sharing that part's skills, from any topic, ordered easiest first.
    - Difficulty uses part marks, the examiner rating, and how many skills the part combines. This lets a student build up from single-skill parts to full 10-mark questions.
  - **Examiner notes** are filed by part, so each pitfall inherits that part's skills. That enables "pitfalls for this skill across all papers".
  - **Process:**
    1. Draft `docs/taxonomy-draft.md` (question types + skills + parent groups), using the site topic pages and mark schemes.
    2. **You review it before any tagging.**
    3. Merge the existing 20 techniques into skills.
    4. Tag via subagents using only the approved lists; new ideas go to a "suggested" list.
    5. Targets: every question has a type; ≥95% of parts have ≥2 skills.
  - **Storage:** `tags.json` gains `question_types` and `skills` (with `group`). Tag assignments are stored per question/part in `data/processed/tags_assigned/<paper>_<sitting>.json`. `question_tags` gains `part_label` and the tag types `question_type` / `skill`. `build_db.py` validates everything against `tags.json`.
- **2g. Your review queue.** `docs/review-checklist.md`: the 10 `low_confidence` questions with PDF filename and page, plus the 2a/2d/2f reviews.

## Phase 3 — Examiner reports (≈2 sessions, core)
- **3a. Download (source confirmed 2026-09-25).**
  - PMT has no Edexcel maths ERs; its "MA" files are PMT's own model answers.
  - Pearson hosts the official "Principal Examiner Feedback" PDFs at `https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/<file>`.
  - Filename formats (verified, HTTP 200):
    - 2018–2021: `9MA0_0{1,2}_pef_YYYYMMDD.pdf` (e.g. `9MA0_01_pef_20180815`, `…20190815`, `…20201217`, `…20211216`);
    - 2022+: `9ma0-0{1,2}-pef-YYYYMMDD.pdf` (`…20220818`, `…20230817`, `…20240815`).
  - P2 uses the same dates as P1; all 14 files confirmed (HTTP 200).
  - Recorded in `docs/pmt-url-patterns.md`. Files saved to `data/raw/examiner-reports/<paper>_<sitting>_ER.pdf` and converted with `pdftotext -raw`. (A pilot showed that `-layout` scrambles inline maths into sentences. `-raw` keeps reading order, but in 4 reports it runs some words together; `display` restores the spacing.)
  - Structure (checked on P1 June 2022): a `Question N (Mean mark X out of Y)` heading, then paragraphs by part covering what went well and common errors. That gives the `performance` field (mean/max) directly, which is the difficulty signal for recommendations.
- **3b. Extract.**
  - Extend `examiner_notes`: `question_id`, `part_label`, `kind` (`did_well` | `pitfall` | `general`), `quote` (verbatim), `source_file`, `page`, `performance` (only if the report states it, e.g. "poorly answered").
  - Source JSON: `data/processed/examiner_notes/<paper>_<sitting>.json`.
  - Subagents extract per paper, quotes only, no paraphrase.
- **3c. Automatic check against invented quotes.** `build_db.py` fails if a `quote` (whitespace-normalised) isn't found in its source ER text file.
  - `scripts/check_examiner_notes.py <paper>_<sitting>` runs the same checks on a single file without rebuilding the DB, so extractions can run in parallel.
  - Garbled maths in a quote is repaired in `display` by reading the PDF page; `quote` itself stays verbatim.
  - Extraction rules: `docs/examiner-notes-extraction.md`.
  - Only P1 June 2019 and P1 June 2022 state mean marks. Elsewhere, difficulty is a rating that must cite the note it's based on.
- **3d.** You spot-check 10 notes against the PDFs.

## Source links (done 2026-09-25)
- `data/processed/sources.json` (generated by `scripts/build_sources.py --verify`) is loaded into the `sources` table.
- It catalogues 64 papers (A Level P1–P3 and AS, 2018 to June 2025 plus Specimen/Sample), with verified question-paper, mark-scheme and examiner-report links.
- Phase 5 answers cite these; e.g. every recommended question gets "open paper" / "open mark scheme" links.
- The June 2025 papers are listed but not yet in the knowledge base. They're the natural unseen test set (Phase 7).

## Phase 4 — Retrieval: tags + semantic search + recommendations (≈2 sessions, no API key needed)
- **Semantic index.**
  - A local embedding model (sentence-transformers, choice benchmarked at build time) runs free, offline and needs no key.
  - What gets embedded:
    - each part (text + its technique titles);
    - each technique write-up;
    - each examiner note.
  - Vectors go in a rebuildable `data/processed/embeddings.npz` (gitignored), with brute-force cosine search; ~1–2k vectors needs no vector DB.
  - Combined with keyword search (`rank_bm25`), because maths symbols embed poorly.
- **`chatbot/identify.py`.**
  - Parse references ("2022 paper 1 question 15", "P1 June 22 Q15").
  - Or match pasted text to a stored question by near-duplicate score, above a threshold.
  - Otherwise treat it as a new question or a generic query.
- **`chatbot/retrieve.py`.**
  - Given a question → its parts, mark schemes, techniques, examiner notes, and notes on similar parts (shared technique).
  - Given a generic query → top techniques plus example parts.
- **`chatbot/recommend.py`.** For each technique in the question: other parts using it.
  - The current question is excluded.
  - Ranking: technique overlap, then report-flagged difficulty, then recency, then a mix of papers.
  - Re-ranked towards the hardest part's techniques once the student answers.
- **Retrieval test (`eval/retrieval_queries.json`, you review it).** About 40 cases:
  - 15 generic queries → expected techniques (recall@5);
  - 15 lightly reworded pasted questions → correct question ID first (top-1 accuracy);
  - 10 "hardest part" cases → recommendations share that part's technique.
  - Run with `python -m eval.retrieval`.

## Phase 5 — Tutor conversation (≈2 sessions; code complete and dry-runnable without a key)
- **`chatbot/session.py`:** state = current question, detail level (student/tutor), revealed steps, hardest part.
- **`chatbot/tutor.py`:** prompt built from `docs/skill-worked-example-style.md`, plus the retrieved mark scheme, techniques and notes. Figure PNGs are attached when `has_figure`. Structured JSON output so your later UI can render it:
  `{parts:[{label, marks, how_to_start, steps:[{text, marks_awarded:["M1: …"]}]}], examiner_insights:[{note_id, kind, text}], recommendations:[{technique, items:[qid+part]}], follow_up:"Which part did you find hardest?"}`
- **`chatbot/validate.py`:**
  - drops insights whose `note_id` doesn't exist;
  - checks mark labels against the part's mark scheme;
  - uses sympy to check final numeric answers (e.g. r³ = 1050 → r ≈ 10.2); on a mismatch, regenerate once, then flag "unverified".
- **Interfaces:**
  - `python -m chatbot`: an interactive chat loop in the terminal (hints first, "more" reveals the next step, `/tutor` toggles to everything at once);
  - a notebook cell;
  - `--dry-run` prints the full prompt and context without calling the API.
  - Answers are logged to `logs/answers.jsonl` (gitignored).
- **`config.py`:** `ANTHROPIC_API_KEY` from `.env` (gitignored).
  - When you create the personal key, set a spending cap in the Anthropic console.
  - Current models and pricing are checked via the claude-api reference at build time.

## Phase 6 — Answer-quality testing (needs the key)
- **Test set** (`eval/test_set.json`, ~20, you approve): every topic, 4 figure questions, proofs, "show that", modelling.
- **Track A (questions in the DB, mark scheme provided):**
  - a grader call scores mark faithfulness per part and whether the method matches the mark scheme;
  - citation validity is automatic (must be 100%);
  - you rate the scaffolding on 5 answers.
- **Track B (question left out of retrieval, simulating new questions):** the grader awards marks against the hidden mark scheme.
- **Grader calibration:** ≥80% agreement with your hand-marking of 5 answers.
- **Choosing the model:** 2 models are tested; `eval/report.py` produces a score-by-topic table and you choose.

## Phase 7 — Later
- **Stored "how to get started" hints** per part: drafted by the model, reviewed by you, saved as `parts[].starter_hint`, and used in place of the live ones.
- **FastAPI backend** (`POST /ask`, `/feedback`) returning the Phase 5 JSON, for your own front-end.
- **More papers:** June 2025 (a truly unseen test), Paper 3, AS 8MA0.
- **GitHub push:** `gh auth login` → `gh auth setup-git` → push; revoke the old token.
- **Tutor speed (measured 2026-09-27; to come back to).** One explanation (P2 June 2024 Q1) took ~37 s: ~3 s to start `claude -p`, ~33 s generating ~5,000 output tokens (~3,000 of them thinking, budget 4,000). Search and question lookup take < 0.5 s. Past logs: 3,000–11,000 output tokens per question, and a validation retry (a second full call) on 2 of the last 12. **Done:** the web UI shows the question at once (0.1 s) and fetches the explanation separately (`Conversation.defer_explanations` / `resume()`, `POST /api/resume`). Still to do:
  1. **Cache explanations** per (question, detail level). Replies are already in `logs/answers.jsonl`; reuse a verified one when the question is opened again, with a way to force a fresh one. Repeats become instant at no cost. Optional: pre-generate the 298 current 9MA0 questions once (~$10 at ~$0.03 each).
  2. **Lower `TUTOR_THINKING_BUDGET`** from 4,000 to ~1,500 (maybe saves 10–15 s a question). Only adopt it after an A/B test on ~30 questions (~$1): the mark-scheme validation pass rate (`verified`) and the retry rate must not get worse.
  3. **Generate one part at a time:** part (a) first, the rest in the background. Most complex, and it adds calls (each ~3 s start-up on `claude -p`), so try only if 1–2 aren't enough. (Moving to the Anthropic API backend would also save ~3 s a call and allow streaming text, but it needs a paid key.)

---

## Critical files
- **Modify:**
  - `scripts/build_db.py`, `data/processed/schema.sql`;
  - `data/processed/{questions,topics,techniques}/*.json`, `tags.json`;
  - `notebooks/explore_kb.ipynb`, `.gitignore`, `CLAUDE.md`, `docs/pmt-url-patterns.md`.
- **New:**
  - `data/processed/examiner_notes/*.json`;
  - `scripts/{split_parts,find_figures,render_figure,build_embeddings}.py`, `scripts/check_notation.js`;
  - `chatbot/{identify,retrieve,recommend,session,tutor,validate,config}.py`;
  - `eval/{retrieval_queries.json,test_set.json,retrieval.py,grade.py,report.py}`;
  - `docs/{review-checklist,technique-list-draft,ms-audit-report}.md`;
  - `requirements.txt`.
- **Reuse:**
  - the `build_db.py` pattern of failing loudly on bad data (extended to quotes and part marks);
  - `docs/skill-worked-example-style.md`, `docs/skill-formula-audit.md`;
  - poppler `pdftotext`/`pdftoppm`.

## Verification
1. **Phase 2:**
   - `build_db.py` passes;
   - marks = 100 per paper and parts add up to question totals;
   - technique coverage ≥95%;
   - `node scripts/check_notation.js` shows 0 errors;
   - notebook runs.
2. **Phase 3:** every `quote` is found in its report text file (checked by the build); your 10-note spot-check passes.
3. **Phase 4:** `python -m eval.retrieval` meets the agreed targets (proposed: question ID top-1 ≥ 90%, technique recall@5 ≥ 80%).
4. **Phase 5:** `python -m chatbot --dry-run`, walking P1_June2022_Q15:
   - the prompt contains the part mark schemes, techniques and report notes;
   - recommendations exclude Q15 itself;
   - the hardest-part answer changes the ranking.
5. **Phase 6 (with key):**
   - grader calibration ≥80%;
   - Track A and B reports produced;
   - live check: Q15 → hints first, mark-labelled steps reaching r ≈ 10.2, sympy confirms, cited examiner notes, recommendations, then the hardest-part question.

## Stats/Mech + legacy papers: agreed plan (2026-09-25/26)
- **Scope (user):** 9MA0 (current) + IAL 2018 + IAL 2013 + UK GCE (C1–C4, S1–S3, M1–M3) as extra sources, filtered to `spec_9ma0.json`. Scraped from Pearson (`scripts/scrape_pearson.py`, `docs/pearson-coverage.md`). Oct 2025 / Jan 2026 / June 2026 are locked (teacher login). Pure P1/P2 June 2025 stays held back as the unseen test set.
- **Tiers (user):** 1 = 9MA0 Paper 3 (agent extraction, `extract-papers` workflow); 2 = IAL-2018; 3 = IAL-2013 + GCE. Examiner notes for legacy papers only on kept questions.
- **Cost levers A–D (user approved; start after Tier 1):**
  - A. Single-call extraction (`claude -p`, PDFs in, JSON out, script-validated, one retry with the errors) instead of multi-turn agents. Pilot it on 3 already-extracted papers and diff against the agent output before switching.
  - B. Haiku text-only triage for S2/S3/M2/M3; full extraction only where questions survive.
  - C. Sample-audit about 10% of papers, widening only if the error rate is high.
  - D. Examiner notes from the .txt on Haiku (the quote check is script-enforced); tagging 3 papers per call.
- **Provenance (user):** every staging/question file records `extraction_method` (`agent-v3` | `single-call-v1`), and audit/notes/tag files record their method too, so the two approaches can be compared later.
- **Scope change (user, 2026-09-26):** legacy Stats/Mech is limited to **S1 and M1** (`scripts/scope.py`); S2/S3/M2/M3 stay scraped but unprocessed, and the already-processed ones are parked in `data/processed/_parked/` (not in the chatbot; `scripts/park_units.py --unpark` restores them). No Further Maths.
