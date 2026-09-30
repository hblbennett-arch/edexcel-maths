# Handoff: build the copyright-clean, sellable version of the tutor (written 2026-09-29)

> **Current state and next steps: `docs/handover-product.md` (30 Sept 2026).** This file remains the design and legal rulebook. One part of it no longer applies: the user's own API account (§2 Model backend was updated). Everything runs on the Enterprise login.

**For:** a fresh Claude Code session on branch **`commercial-clean-room`** in `~/edexcel-maths`.

**Read in this order:**
1. this file;
2. `CLAUDE.md`;
3. `docs/commercial-relaunch-plan.md` (the legal and market research, with sources);
4. the top "Status" sections of `docs/rag-chatbot-plan.md`.

The current Pearson-based chatbot is preserved on **`main`** (last commit `49d7e1c`). This branch is where the commercial product is built.

**Status (2026-09-29, second session):**
- **Phase 0 not started, by the user's choice:** no purge yet, the repo is still public, and they'll make it private later.
- **Phase 1 partly done** (uncommitted):
  - content packs;
  - provenance columns and the licence gate;
  - the fact layer and its check;
  - a seed error taxonomy (267 codes) and error-frequency matching;
  - gates G1 and G7 with a self-test.
- **All engine evals are identical** before and after the pack abstraction.
- **Details, commands and lessons:** `docs/clean-room-pipeline.md`. **Open decisions:** `docs/review-checklist.md` §28.
- **Still to do in Phase 1:** G2, G8, clean prompts and the blueprint builder.
- **New firewall rule:** clean-side sessions never print Pearson text into their own context. Work with ids, counts and codes.
- **Phase 2 pilot, 2026-09-30:** 60 items generated (40 exam-style in the 9MA0 mix, 20 drills). 25 pass G1–G8, which awaits the user's review (G9). Spend $39.96, about $1.60 per passing item. Blueprints for the full bank (601 exam-style, 452 drills, 6 mocks) are ready. Next: the user reviews, then scale in batches. See `docs/clean-room-pipeline.md` (Lessons) and checklist §28.
- **User decisions, 2026-09-30:**
  - build everything on the Claude Code Enterprise login (§2, Model backend);
  - the bank focuses on problem-solving exam-style questions in the measured 9MA0 mix (§5.3, `mix_9ma0`), with drills alongside;
  - GitHub only, never GitLab.

---

## 0. What the user wants (keep this in front of you)

The user is building **a product to sell for profit**. It merges AI with their expert A Level Maths knowledge to help students get **the best possible mark on every question**:

1. **Explain exactly how marks are awarded:** step by step, mark by mark (M1, A1, B1, dM1, ft), in authentic Edexcel style. Students should learn to *write answers the way examiners mark them*.
2. **Warn about the specific mistakes students make** on *this* question and *these* skills, as specifically as possible ("if you get x = −3 here, reject it: a length can't be negative").
3. **Find the right practice fast:**
   - by skill;
   - by combination of skills or topics ("a question using differentiation, partial fractions and stationary points");
   - by description;
   - by weakness ("the part I found hardest");
   and build practice ladders from easy to exam-level.
4. **Focus on problem solving.** Most of the bank is exam-style questions that combine skills in the same proportions as current 9MA0 papers (§5.3), with single-skill drills alongside for targeted practice.
5. **Be faithful to the Edexcel 9MA0 style** (question wording, part structure, mark allocation, mark-scheme conventions), so it's a genuinely effective revision resource for Pearson Edexcel A Level Maths students.
6. **Be legally sellable in the UK without Pearson's permission.** The product must contain **no Pearson expression**: no Pearson question, mark-scheme or examiner-report text, and no close paraphrase of any. **Heavy inspiration** from the existing Pearson bank is wanted, but only through the **abstraction firewall** in §3. Nothing Pearson-written crosses it.

Commercial context (researched; details in `docs/commercial-relaunch-plan.md`):
- **The market gap:** no competitor explains A Level method marking step by step. Save My Exams' "Smart Mark" marks answers but doesn't teach the marking.
- **Prices:** students about £5–10 a month or £40–60 a year; schools about £600–650 per school per year.
- **Realistic profit:** £0–2k a month in year one; £5–15k a month by years two or three if it works.
- **Where the value lies:**
  - the quality and trustworthiness of the questions and mark schemes;
  - "mark my working";
  - first-party data on where real users lose marks, which becomes the long-term moat.

## 1. Standing instructions from the user (carry these over)

**Git:**
- **Never commit or push unless the user asks in that session.**
- **GitHub only, never GitLab**: no GitLab remotes, pushes or GitLab tools in this project. When pushing: remote `origin` = github.com/hblbennett-arch/edexcel-maths; identity `hblbennett-arch <hblbennett@gmail.com>`.
- Never store a token the user gives you. Use it for one push with `git -c credential.helper= -c "http.https://github.com/.extraheader=AUTHORIZATION: basic <base64 of x-access-token:TOKEN>" push origin <branch>`, then remind them to revoke it.
- **Do not push this branch while the repo is public** (§2).

**Working with the user:**
- The user is new to dev tooling. Give step-by-step instructions for anything they must do themselves; for commands, suggest they type `! <command>`.
- **Log every human-review item** in `docs/review-checklist.md` (§27 holds the relaunch to-dos; add new sections from §28) and say how many you added.

**How to work:**
- **Record lessons** in the skill docs: `.claude/skills/add-exam-papers/SKILL.md` for the data pipeline, `docs/rag-chatbot-plan.md` for the chatbot, and this file plus new docs for the clean-room pipeline.
- **Prefer deterministic checks and evals** over trusting a model.
- **Measure before and after** every change, and don't adopt one that regresses the evals.
- Max 5 parallel agents at a time for bulk work (CLAUDE.md).
- Model calls cost the user money. Estimate before large runs, pilot small first, and report actual spend.

## 2. Current state (what exists, what's wrong)

**Branches:**
- `main`: the working Pearson-based tutor.
- `commercial-clean-room` (this one): so far only this file, `docs/commercial-relaunch-plan.md` and a CLAUDE.md pointer have been added.

**⚠️ The repo is public.** Verified via the GitHub API on 2026-09-29. `main`'s history publishes Pearson material:
- 3,103 tracked files under `data/processed/`: question and mark-scheme transcriptions, and examiner-report quotes carrying "© Pearson Education Ltd";
- 8 AQA examiner-report PDFs plus an AQA physics data sheet at the repo root (from an unrelated AQA Physics project; AQA forbids putting its material on any website and bans all AI use of it);
- GitHub Pages topic pages (`output/`, `output-as/`) with worked examples from real papers, linking to physicsandmathstutor.com copies.

This is already infringement. **Phase 0 fixes it; confirm with the user before doing any of it:**
1. The user makes the repo private (GitHub → Settings → General → Danger Zone → Change visibility).
2. Back up the working folder (`data/` included).
3. Purge `data/processed/`, the AQA PDFs and the real-question pages from **all** history with `git filter-repo`. This rewrites history, so confirm first and keep the backup.
4. Fix `.gitignore`.

**Pitfall:** `data/processed/*.json` is tracked on `main`. If you `git rm --cached` it on this branch only, then switching from `main` to this branch **deletes those files from disk**. Only untrack as part of the full purge, after a backup.

**The Pearson knowledge base (local, stays local).**
- **Source JSON:** `data/processed/` (questions/, examiner_notes/, tags_assigned/ etc.).
- **Built database:** `data/processed/questions.db` (gitignored; build with `.venv/bin/python scripts/build_db.py`). What it holds:
  - 2,702 in-spec questions (9MA0 P1/P2 210, Paper 3 88, IAL 2018 770, IAL 2013 587, UK GCE pre-2017 1,046);
  - 7,055 parts;
  - 21,764 examiner notes (10,703 pitfall, 5,693 did-well, 5,368 general);
  - question_performance on 2,799 parts/questions (mean marks, % full marks, a well/mixed/poorly-answered rating);
  - 20,867 skill tags and 2,702 question-type tags.
- **Tables:** `questions`, `question_parts`, `question_tags`, `skills` (246), `skill_groups` (47), `question_types` (73), `techniques`, `examiner_notes`, `question_performance`, `sources`.
- **Embeddings:** `data/processed/embeddings_baai-bge-small-en-v1-5.npz`, from the local model `BAAI/bge-small-en-v1.5`; nothing is sent anywhere.
- **Specification transcription:** `data/processed/spec_9ma0.json` is a word-for-word copy of Pearson's specification tables. It's Pearson copyright, so use the DfE subject content instead (§3).

**Your own IP, reusable as-is:**
- the `chatbot/` engine;
- the 246-skill taxonomy, with descriptions and group titles in your own words;
- the 73 question-type definitions;
- `techniques` write-ups;
- all `eval/` harnesses and the pipeline tooling in `scripts/` (tagging, notation checks, validation patterns).

Check the skill and type text once for any phrase lifted from a Pearson document before you ship it.

**Engine state:**
- **Practice finder** (`chatbot/recommend.py::find_practice`) has three channels: exact maths, description (stemmed BM25 over whole questions), and skill tags. Several topics or skills go through `split_concepts`, which ranks by coverage; `named_groups` handles whole-topic names. Filters: component, year, qualification.
- **Benchmark:** `eval/practice_search_eval.py`. Before → after: description recall@5 1% → 100%; topics top-1 27% → 95%; skills 48% → 93%; hand cases 9/9.
- **`eval/practice_eval.py`:** 228/228 skills resolve, precision 1103/1106, routing checks pass.
- **`eval.retrieval`:** references 31/31, 0 wrong pasted.

All of these must keep working on the clean content pack.

**Tutor:**
- `chatbot/tutor.py` makes one structured model call per question. `chatbot/validate.py` checks the reply against the mark scheme and retries once on serious failures. Prompts are in `chatbot/prompts.py`; they currently say "official mark scheme" and "verbatim examiner notes", which must change.
- The web UI (`.venv/bin/python -m chatbot.web`, http://127.0.0.1:8765) shows the question at once and fetches the explanation via `POST /api/resume`.
- Latency is about 37 s per explanation: ~3 s `claude -p` start-up plus ~33 s generating ~5,000 tokens, ~3,000 of them thinking.
- Speed backlog (see `docs/rag-chatbot-plan.md` Phase 7): cache explanations; A/B test a lower thinking budget; generate part-by-part.

**Model backend:** everything is built on the user's **Claude Code Enterprise login** (`TUTOR_BACKEND=claude-code`, i.e. `claude -p`): the tutor, content generation (§5.4) and every model-based gate. It is the project's only account (user decision, 2026-09-30); don't plan around any other. Use current models: Opus 5.5 `claude-opus-5-5` to generate, Sonnet 5.5 `claude-sonnet-5-5` for the blind solve and the marker (G3/G4), Haiku 4.5 `claude-haiku-4-5` for retagging (G6).

**Known bug:** `--dry-run` mode crashes when opening a multi-part question with no part chosen (`recommend.ladder` gets a part key that doesn't exist). This predates this work; see review-checklist §26.

## 3. The legal ground rules: the abstraction firewall

This is research, not legal advice; a UK IP solicitor should sign off before launch (questions in `commercial-relaunch-plan.md` §9). Summary of the findings:
- Exam papers, mark schemes and examiner reports are Pearson-owned literary works (University of London Press v University Tutorial Press 1916; CDPA s.3; THJ v Sheridan 2023).
- No exception covers a paid product: s.28A, s.29/s.178, s.29A, s.30, s.32 and s.36 were all checked. The government's 18 Mar 2026 Report on Copyright and AI confirms no commercial text-and-data-mining exception is coming, and says copies stored for an AI to look up "will need to be licensed" (para 118).
- **Free to use:** facts, ideas and functionality (Baigent, Navitaire, SAS v WPL, Designers Guild on commonplace ideas). **Protected:** the expression, including close paraphrase and "altered copying" of a setter's specific choices (Designers Guild, SAS v WPL [83]–[85], Infopaq).
- Pearson v Chegg (US, 2021; settled Dec 2024) shows Pearson does sue paid Q&A services over "copied or paraphrased" content.

**The firewall.** Pearson text may be *read* only by **local, deterministic scripts** (regex, counting, the local embedding model already built). Nothing Pearson-written goes into a model prompt, the product, its databases or its servers.

What may cross into the clean side is **only unprotected facts**, stored as IDs, numbers and codes from a fixed vocabulary:
- which skills a question tests, per part;
- marks per part;
- the sequence of mark *codes* (M1 A1 dM1 B1 A1ft…);
- command words used ("Show that", "Hence", "exact", "in the form", "3 s.f.");
- whether a part is "show that" or "hence";
- answer-form requirements;
- the question type;
- whether a figure is used;
- difficulty facts (mean mark, % full marks, well/poorly answered);
- **error-type codes and how often they occur** (§5.2).

**Allowed:**
- Anything a human expert does by *reading*: the user reading papers and writing their own ideas, taxonomy or error codes. Reading isn't copying.
- Aggregate statistics about Edexcel style (distributions), used to steer and to check generation.
- Blueprints built from the fact layer, preferably aggregated over **≥3 source questions of the same type**. A blueprint from a single source is allowed only with a different context, a different function family and different values, plus the stricter novelty threshold and a human confirming "different question, same skills".
- The generic marking system (M/A/B/dM/ft/oe/cao/awrt/isw, "Way 1/Way 2", "Notes"), explained in **your own words**. Never copy Pearson's "General Marking Guidance" text.
- Plain referential use: "Built for Pearson Edexcel A Level Mathematics (9MA0)", plus "Independent: not affiliated with, endorsed or licensed by Pearson" (Trade Marks Act 1994 s.11(2)).
- Linking to Pearson's own free past-paper PDFs on qualifications.pearson.com, in a new tab, never framed.
- The DfE "GCE AS and A level subject content for mathematics" and Ofqual's maths conditions, which are OGL v3.0 and commercially reusable with attribution. Use these instead of Pearson's specification wording.

**Banned (a gate check must enforce each):**
- Any Pearson text, or close paraphrase, in prompts, content, pitfalls, UI or marketing.
- "Variants": the same scenario or context plus the same part sequence with new numbers.
- Line-by-line paraphrase of any mark scheme or examiner report.
- Claiming "examiners said" or "the examiner report says". Your pitfall notes are your own; phrase them as "a common mistake on questions like this", and only when the frequency data (§5.2) supports "common".
- "Edexcel" or "Pearson" in the product or domain name; their logos or visual styling.
- Links to third-party copies of papers (e.g. PMT) from the paid product.

**Being honest about "definitively".** No plan can guarantee zero legal risk, and the user should be told this plainly. The firewall keeps the residual risk to the internal, local processing of copies the user already holds. The riskiest remaining step is the local similarity check against the Pearson corpus (§6, G7); the research rated it low–medium. Get the solicitor to confirm options (a), (b) or (c) in `commercial-relaunch-plan.md` §5 before launch. Keep a written provenance record for every item, because it is the evidence of independent creation.

## 4. Product architecture on this branch

- **Engine:** `chatbot/`, unchanged in shape. Every data access goes through a **content pack**: `content/<pack>/pack.db` with the same schema as `questions.db` plus provenance columns (below).
  - `pearson-private` points at the existing `data/processed/questions.db`. It is for local personal study and for building the fact layer only, and is never shipped.
  - `clean` is the product pack: tracked in git once the repo is private.
- **Provenance columns** on questions, parts and pitfalls:
  - `provenance` (`original` / `ogl` / `pearson-private`);
  - `blueprint_id`, `generator_model`, `generated_at`;
  - `gate_results` (JSON);
  - `reviewed_by`, `reviewed_at`, `review_decision`, `review_notes`.
- **Deterministic licence gate** (`scripts/check_provenance.py`, run by every build and eval): a commercial build **fails** if any row isn't `original`/`ogl`, if any Pearson table (examiner_notes, question_performance) is present, if any text fails the novelty gate, or if any string contains "examiner report", "Pearson says" or similar.
- **Past-paper map** (`content/pastpaper_map.json`), which contains facts only. For each real question: the reference (paper, sitting, question number), marks, skills per part, question type, difficulty facts, and a link to Pearson's own PDF. No text. A deterministic check enforces: no field longer than about 40 characters except URLs, and a vocabulary whitelist. This keeps "find a real past-paper question on X" working in the product.
- **Prompts** (`chatbot/prompts.py`): "our mark scheme" and "our common-mistakes notes". Remove "verbatim examiner notes" and "note_id quotes". For a question the student brings themselves: "likely M1", clearly estimated.
- **Bring your own question:** the student pastes or photographs a question. It is processed then deleted: never stored, never reused, never shown to others. The terms of use say the user must have the right to upload it, and there's a takedown contact. Show no official mark scheme; the tutor estimates the marks.

## 5. Building the content: four layers

### 5.1 Fact layer: the "Edexcel style fingerprint" (local, deterministic, no model calls)

Scripts in `scripts/clean/`. Output goes to `content/facts/`, which holds numbers and codes only.

- **Per question/part:**
  - marks;
  - skill tags (already in `question_tags`);
  - question type;
  - mark-code sequence, extracted by regex from `question_parts.mark_scheme`. Tested 2026-09-29: only 26 of 7,055 parts have no codes. Totals: M 15,235, A 15,371, B 5,340, dM 2,053, A1ft 635, B1ft 413. Top part patterns: "M1 A1" 676, "M1 A1 M1 A1" 438, "B1" 425, "M1 A1 A1" 258, "B1 B1" 248;
  - command words / answer forms (regex over part text). Tested counts: Show that 1,008; Given that 626; Hence 497; exact 441; in the form 432; decimal places 366; Sketch 220; significant figures 201; Prove 106;
  - figure yes/no;
  - calculator rubric yes/no;
  - difficulty facts from `question_performance`.
- **Aggregates per question type and per skill:**
  - distributions of part counts, marks per part, mark-code patterns, command words and difficulty;
  - how often skills occur together (which skills co-occur in one question), which drives realistic multi-skill blueprints.
- **Paper-level facts:** 9MA0 P1 and P2 (pure) are 2 hours and 100 marks each; P3 is statistics (50) plus mechanics (50), 2 hours, 100 marks. Record the mix of question types and marks per paper from the 9MA0 data.
- **Check:** `check_facts.py` fails if any string field isn't an ID, a code from the whitelist, a number or a URL.

### 5.2 Error taxonomy: specific pitfalls without copying examiner reports

Goal: pitfalls as specific to *the question* as possible, grounded in real frequencies, written in new words.

1. **Seed list of error codes.** The next session drafts it from general maths-teaching knowledge, *not* from the reports: about 150–250 codes such as `sign-error-differentiating-negative-power`, `fails-to-reject-invalid-root`, `premature-rounding`, `wrong-limits-after-substitution`, `missing-constant-of-integration`, `degrees-not-radians`, `show-that-missing-step`, `ft-not-carried`. Each code has a one-line definition in your own words, and skills it applies to. **The user reviews and extends the list.** A human writing their own list is fine.
2. **Frequency per skill** (local, deterministic):
   - embed each code definition with the local bge model;
   - match every `pitfall` note (the local embeddings already exist) to its nearest code by cosine similarity, above a threshold;
   - count per skill and question type, weighted by `question_performance`.
   The output is `(skill, error_code, frequency, n_notes)`. Numbers only, no text, and nothing is sent to a model.
3. **Unmatched clusters:** cluster notes that match no code, locally. The **user** reads a few samples per cluster and writes a new code in their own words. Never send Pearson note text to a model.
4. **At generation time** (§5.4), the model receives only the blueprint and the top error codes, with frequencies, for each part's skills. It writes **new, question-specific** pitfalls using the new question's numbers ("If you divide by $\cos x$ here you lose the solutions where $\cos x = 0$: $x = 90°$"). "Common" is used only when the frequency is at least a set threshold.

### 5.3 Blueprints

A blueprint is an abstract design, stored as JSON in `content/blueprints/`. It holds:
- the question type;
- per part: skills, marks, target mark-code pattern, command word, answer form, show-that or hence;
- a difficulty tier;
- a context class (none, or one of your own context families such as "population model", "particle on a slope", "survey"), with **no Pearson scenario words**;
- constraints on numbers (nice roots, exact forms, calculator allowed or not);
- the error codes to target;
- `source_fact_ids`: the ≥3 real questions whose facts shaped it.

**The bank's focus is problem solving: exam-style questions that combine skills the way current 9MA0 papers do** (user decision, 2026-09-30). Measured on all 298 current-spec 9MA0 questions (`content/facts/aggregates.json` → `mix_9ma0`). "Topics" are skill groups, not counting the supporting ones (algebraic manipulation, quadratics, exam technique, modelling):

| 9MA0 question kind | Pure (210) | Stats (45) | Mech (43) | All (298) |
|---|---|---|---|---|
| One topic, ≤ 5 marks | 24% | 2% | 2% | 18% of questions, 10% of marks |
| One topic, 6+ marks | 18% | 9% | 7% | 15%, 16% of marks |
| Two topics | 25% | 40% | 35% | 29%, 28% of marks |
| Three or more topics | 32% | 49% | 56% | 38%, 47% of marks |

About two-thirds of real questions (three-quarters of the marks) combine topics. So the bank is:

| Content | Target | How it is built |
|---|---|---|
| **Exam-style questions** | **~600**: pure ~420, stats ~90, mech ~90 (the 9MA0 component shares) | Blueprints sampled so each component matches the table above, plus the 9MA0 distributions of marks per question, parts per question and hence/show-that chains. Topic combinations are drawn from real skill co-occurrence. G8 checks the bank-level mix (total variation distance < 0.15 per component). |
| **Mock papers** | 6: 2 × (P1, P2, P3), fresh questions not in the bank | Each paper copies a real paper's shape (`papers.json`: number of questions, marks each, types), not its questions |
| **Skill drills** | ~2 per skill (starter, core), ~490 | Targeted practice and the lower rungs of practice ladders; exam-style questions are the top rungs |

### 5.4 Generation (Claude Code Enterprise login, `claude -p`)

One call per blueprint. The model sees the blueprint, the relevant **DfE/own** skill descriptions, the fact-layer style targets and the error codes. **It never sees Pearson text.**

Outputs, all structured JSON:
- the question, in Edexcel conventions: marks in brackets at the end of each part, "(Total for Question n is N marks)", command words, answer-form requirements, calculator rubric in **your own wording**, and diagrams as your own SVG/JSXGraph (see `docs/skill-jsxgraph-diagrams.md`);
- a **mark scheme** in Edexcel-style notation: each mark with its code and what earns it, "oe/cao/awrt/isw", alternative methods ("Way 2"), and "Notes" on what to accept or not;
- a fully worked solution;
- the common-mistakes notes per step;
- how-to-start hints;
- the answer-check data for sympy (final answers and key intermediate values, as expressions).

Use a **different model** for the blind solve in G3. Pilot before scaling (about 60 items: ~40 exam-style questions in the 9MA0 mix, built around calculus in pure and the binomial distribution / hypothesis testing in stats, plus ~20 drills), and report the cost per accepted item.

## 6. Validation plan: every question, mark scheme and pitfall must pass

Store every gate result in `gate_results`. Nothing enters the `clean` pack without passing G1–G8 and a human decision (G9). Reject and regenerate rather than hand-patching, except for small edits in review.

| Gate | What it checks | How | Pass rule |
|---|---|---|---|
| **G1 Structure** | Marks per part add up to the total; mark codes are valid; dM follows an M; A marks depend on an M; ft names what it follows; every part has ≥1 mark; labels are in order | Deterministic script | 100% |
| **G2 Maths correctness** | Every final answer and listed intermediate value | sympy: symbolic simplify-equals, numerical checks at random points, exact forms, s.f./d.p. rules, units | 100% |
| **G3 Blind solve** | The question is solvable and unambiguous; the answer matches | A *different* model solves from the question alone; answers compared by sympy; a separate "find any ambiguity or error" pass | Answers match and no ambiguity is found |
| **G4 Mark-scheme unit tests** | The mark scheme awards marks correctly | Generate 4–6 scripted responses per question: fully correct; one per targeted error code (the wrong working it implies); a correct alternative method; a partial answer. A marker model applies *our* mark scheme to each; every response has a designed expected mark vector (e.g. "sign error at step 2 → M1 A0 A1ft") | Awarded marks equal the expected vector for 100% of scripts |
| **G5 Pitfall validity** | Each pitfall is real and specific to this question | Each must point to a step, be demonstrated by a G4 script that loses marks, use the question's actual numbers, and meet the frequency threshold if it says "common" | 100% |
| **G6 Tag accuracy** | The skill tags are right | Retag blindly with the existing tagging approach (`scripts/tag_single.py` pattern) and compare with the blueprint | ≥95% part-level agreement; review the rest |
| **G7 Novelty (copyright)** | Not a copy or close variant of any Pearson question, mark scheme or examiner note | Local only: word 8-gram overlap (a whitelist of stock phrases like "find the exact value of"); 5-gram Jaccard; matching sets of distinctive numbers; rare scenario-word overlap; bge cosine similarity against all 2,702 questions, 7,055 parts and 21,764 notes | Reject if any 8-gram matches outside the whitelist, Jaccard > 0.15, cosine > 0.85, or ≥3 distinctive numbers match one source; flag between 0.75 and 0.85 for human review |
| **G8 Style conformance** | It looks and reads like Edexcel | Deterministic: notation (`node scripts/check_notation.js`), LaTeX renders, command words from the list, answer-form phrasing, marks per part within the fact-layer range for the type. Bank level: the distributions of mark patterns, command words and difficulty sit close to the 9MA0 aggregates (e.g. total variation distance < 0.15, reported per type) | Item level 100%; bank level reported and tuned |
| **G9 Human review** (the user as domain expert) | Is it a good, authentic, fair exam question with a correct, fair mark scheme? | Local review UI (reuse the `chatbot/web.py` pattern): side by side with gate results; accept / edit / reject with a reason code; items queued by risk (G7 flags, G3 disagreements first). 100% of the first 200 items, then 100% of multi-part and mock items and ≥30% of single-skill items once acceptance is ≥95% | Recorded decision per item |
| **G10 Audits** | The bank's real error rate | A blind audit (a strong model plus the user) of a random 100 accepted items per 500; ideally a teacher colleague checks 5% independently | ≤1% maths/mark-scheme errors; otherwise fix the cause and re-audit |
| **G11 Pilot** | Real-world quality | ~100 students: flag buttons ("wrong", "unclear", "unfair marks"), success rates per part, time per part | < 1 confirmed error per 200 items served; per-part difficulty close to the tier |

**Engine evals on the clean pack:** `eval/practice_eval.py` (precision ≥99%), `eval/practice_search_eval.py` (re-baselined on the clean pack; keep hand cases for multi-topic requests) and `eval.retrieval`. Add `eval/clean_gates_report.py`, which prints the pass rate per gate, the rejection reasons, the cost per accepted item and the review minutes per item.

**Tutor on clean items:** `chatbot/validate.py` checks tutor replies against *our* mark scheme. Target: the verified rate is at least the current rate on Pearson items. Run `eval.chat_smoke` (~$0.50) on 10 clean items.

## 7. Product functionality to build (priority order)

1. **Mark-by-mark tutor** on the clean bank: the existing flow, with prompts rewritten to use our mark scheme and pitfalls.
2. **"Mark my working":** the student types or photographs their working for one of *our* questions. The AI marks it against our mark scheme, mark by mark, and explains each lost mark and how to get it. Unit-test the marker with the G4 scripts. This is the flagship feature.
3. **Practice finder and ladders:** the existing `find_practice`, `ladder`, `refocus` and `broad` over the clean pack and the past-paper map. "Find a real past-paper question on X" returns references and links.
4. **Weakness tracking:** skill-level results from each student's attempts, feeding recommendations. Privacy-first: explain it plainly and follow the Children's Code, §9.
5. **Mock papers:** timed, with a mark breakdown per skill afterwards.
6. **Bring your own question**, with the conditions in §4.
7. **Caching and speed:** cache tutor explanations per question (instant repeats), and A/B test the thinking budget (see `rag-chatbot-plan.md` Phase 7).

## 8. Phases (with deliverables and checks)

| Phase | Work | Done when | Cost |
|---|---|---|---|
| **0 Clean-up** (needs user approval) | Repo private; back up; `git filter-repo` purge (§2); fix `.gitignore`; take the real-question topic pages off GitHub Pages; check the Verisk employment contract (IP and side-business clauses) | Repo private; no Pearson or AQA files in any commit | £0 |
| **1 Foundations** | Content-pack abstraction plus provenance columns; `check_provenance.py`; fact layer (§5.1) plus `check_facts.py`; seed error taxonomy for user review (§5.2); frequency matching; blueprint schema; gate scripts G1, G2, G7, G8; clean prompts | All existing evals pass on the `pearson-private` pack through the new abstraction (no regressions); fact layer passes its check | ~£0 |
| **2 Pilot** | Blueprints and generation for 2 skill groups (~60 items, including 10 multi-part); G3–G6; review UI; `clean_gates_report.py` | Pass rates, cost per accepted item and review minutes per item measured; the user signs off on style and quality | ~$30–50 of usage |
| **3 Scale** | Full bank (§5.3 targets) in batches of ≤5 parallel agents; pitfall notes; mock papers; G10 audits | Coverage targets met; the bank's question mix matches 9MA0 (G8); audit ≤1% errors; engine evals re-baselined on the clean pack | ~$500–1,100 of usage + ~90–130 h of review |
| **4 Product** | "Mark my working", weakness tracking, mock mode, caching; production model backend; new brand name and disclaimers; terms, privacy notice, Children's Code DPIA; ICO fee (£52); solicitor review | Solicitor sign-off; compliance items done | ~£500–2,000 legal (estimate) |
| **5 Pilot and launch** | ~100 free pilot students (G11), then a paid annual "exam pass"; 3–5 school trials | G11 targets met | — |

## 9. Compliance checklist (details and sources in `commercial-relaunch-plan.md` §7)

- **ICO Children's Code:** DPIA, high-privacy defaults, profiling explained, no nudge techniques. Also Data (Use and Access) Act 2025 s.81 ("children's higher protection matters"), and the ICO fee (£52).
- **Anthropic's rules for services used by minors:** safeguards, and tell students they're talking to an AI.
- **Online Safety Act:** keep the tutor one-to-one, with no sharing between users and no live web search. Watch for regulations under the Crime and Policing Act 2026 s.248 (new OSA s.216A).
- **Consumer law:** 14-day cancellation; build easy cancellation and renewal reminders now (DMCCA subscription rules are expected from spring 2027).
- **VAT:** register at £90k turnover.
- **Unverified items to recheck:** the UK trade mark register entries for EDEXCEL and PEARSON; the Getty v Stability appeal status; whether Physics & Maths Tutor is licensed.

## 10. Where things are

| What | Where |
|---|---|
| Legal and market research with sources | `docs/commercial-relaunch-plan.md` |
| Engine | `chatbot/`: `recommend.py` (finder, ladders), `search.py` (BM25 + bge), `tutor.py`, `validate.py`, `prompts.py`, `controller.py`, `web.py` + `static/index.html` |
| Evals | `eval/practice_eval.py`, `eval/practice_search_eval.py` (+ `practice_search_results.txt`), `eval/retrieval.py`, `eval/chat_smoke.py` |
| Pipeline tooling worth reusing (patterns, not Pearson data) | `scripts/tag_single.py`, `scripts/check_tags.py`, `scripts/check_notation.js`, `scripts/ms_verify.py` (a pattern for visual/structured checks), `scripts/build_db.py`, `scripts/build_embeddings.py`, `docs/notation-spec.md`, `docs/tagging-spec.md`, `docs/skill-worked-example-style.md` |
| Human-review log | `docs/review-checklist.md` (§27 = relaunch to-dos; add from §28) |
| Chat UI | `lsof -ti tcp:8765 \| xargs kill; .venv/bin/python -m chatbot.web` → http://127.0.0.1:8765 |

## 11. First actions for the next session

1. Read the files listed at the top. Summarise the plan back to the user in plain words.
2. Ask the user to approve Phase 0: make the repo private (step-by-step instructions), the backup and history purge (explain that it rewrites history) and the employment-contract check. Don't rewrite history without explicit approval.
3. Start Phase 1 with the content-pack abstraction and the fact layer. Measure: all existing evals must pass unchanged on `pearson-private` through the new abstraction.
4. Draft the seed error taxonomy for the user to review. Add it as a review item in `docs/review-checklist.md` §28.
