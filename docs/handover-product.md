# Handover: the independent A Level Maths mark-scheme tutor (state at 30 Sept 2026)

**Branch:** `commercial-clean-room` in `~/edexcel-maths`. 5 local commits on top of `main` (latest `95f92a5`). **Nothing has been pushed.**
**Read in this order:**
1. this file;
2. `docs/handoff-clean-room.md` (the design and the legal firewall, which is still the rulebook);
3. `docs/clean-room-pipeline.md` (commands, file formats, lessons learned);
4. `docs/review-checklist.md` §27–28 (the user's open decisions);
5. `docs/commercial-relaunch-plan.md` (legal and market research, with sources).

---

## 1. What we're building

A paid revision product for **Pearson Edexcel A Level Mathematics (9MA0)** students. It combines AI with the user's own expertise to help students get the best mark on every question.

1. **Mark-by-mark teaching.** For each question, the student learns exactly how marks are awarded (M1, A1, B1, dM1, ft, awrt, cso) and how to write answers the way examiners mark them.
2. **Question-specific pitfalls,** using the question's own numbers, e.g. "if you divide by cos x you lose the solutions where cos x = 0, so the final A1 is lost".
3. **Practice finding:**
   - by skill, by a mix of skills or topics, by description, or by the part the student found hardest;
   - practice ladders from easy to exam level;
   - a map of real past-paper questions that links out to Pearson's own site and holds no Pearson text.
4. **Mark my working (the flagship, not built yet).** The student submits working for one of *our* questions, and the AI marks it against *our* mark scheme, explaining each lost mark.
5. **Problem solving first.** Most of the bank is exam-style questions that combine skills in the same proportions as real current-spec papers, with short skill drills alongside. It also includes full mock papers.

**It must be legally sellable in the UK with no permission from Pearson.** The product holds **no Pearson expression**: no Pearson question, mark scheme or examiner-report text, and no close paraphrase. Pearson material is used only to learn *facts*, such as which skills are tested, the marks, the mark-code patterns and how often each kind of mistake happens. That happens through local scripts only (the "abstraction firewall", `handoff-clean-room.md` §3).

## 2. Standing decisions from the user (don't reopen these)

| Decision | Date |
|---|---|
| **Independent of Pearson.** No licence, no permission request, no contact with Pearson. Build a product that needs none. | 30 Sept 2026 |
| **Build everything on the user's Claude Code Enterprise login** (`claude -p`, `TUTOR_BACKEND=claude-code`). There's no other account; don't suggest an API key. | 30 Sept 2026 |
| **GitHub only, never GitLab** (remote `origin` = github.com/hblbennett-arch/edexcel-maths). No GitLab remotes, pushes or tools. | 30 Sept 2026 |
| **The bank mirrors the 9MA0 question mix** and emphasises multi-skill problem solving, with drills alongside. | 30 Sept 2026 |
| **Phase 0 clean-up deferred:** no history purge yet; the user will make the repo private later. | 29 Sept 2026 |

How to work with the user:
- **Git:** commit only when the user asks in that session, and never push while the repo is public.
- **The user is new to dev tooling.** Give step-by-step instructions, and suggest `! <command>` for anything they must run themselves.
- **Log every item that needs the user's judgement** in `docs/review-checklist.md` (add §29 onwards), and say how many you added.
- **Record lessons** in `docs/clean-room-pipeline.md` (Lessons).
- **Prefer deterministic checks.** Measure before and after, and don't adopt a change that regresses the evals.
- **At most 5 parallel agents or model calls.** Estimate model spend before a run, pilot small first, and report actual spend (every call is logged in `logs/llm_calls.jsonl`).
- **Firewall rule for sessions:** never print Pearson text into your own context. Work with ids, counts and codes; anything a human needs to read goes to `data/clean_private/`, which is gitignored. Subagents get the same rule in their prompt.

## 3. Where we are

| Phase | Status |
|---|---|
| **0 Clean-up** | **Not done, by the user's choice.** The repo is still public, and `main`'s history holds Pearson material (3,103 files under `data/processed/`, AQA PDFs, real-question topic pages, `units.json` and more; list in checklist §28). The history purge and the employment-contract check are pending. |
| **1 Foundations** | **Done.** Content packs with provenance columns; licence gate; fact layer (`content/facts/`) and its check; 267 seed error codes; error-code frequencies; all eight deterministic and model gates; tutor pack-aware. All `pearson-private` evals are byte-identical to before. |
| **2 Pilot** | **Generated; waiting for the user's review.** 60 items (40 exam-style in the 9MA0 mix, 28 pure calculus-centred and 12 stats; 20 drills). **25 pass G1–G8** (18 exam-style, 7 drills). Spend **$39.96** over three rounds, about **$1.60 per passing item**. The review screen is built. |
| **3 Scale** | **Ready to start after review.** All blueprints exist: 601 exam-style, 452 drills, 84 mock-paper questions (6 papers × 100 marks). |
| **4 Product** | **Partly started.** The tutor runs on the clean pack. Not built: mark my working, weakness tracking, mock mode, caching, production backend, brand and legal pages. |
| **5 Pilot students and launch** | Not started. |

## 4. How it works (data flow)

```
pearson-private pack (data/processed/, local only; never shipped, never shown to a model)
   │  local scripts only: regex, counting, local bge embeddings
   ▼
content/facts/*.json       ids, numbers and codes only (check_facts.py): marks, skills, mark-code sequences,
   │                       command words, answer forms, difficulty, skill co-occurrence, the 9MA0 question mix
   ▼
content/blueprints/*.jsonl  abstract designs (make_blueprints.py + check_blueprints.py): per part skills, marks,
   │                        code pattern, command, forms, target error codes; >= 3 real source ids; no text
   ▼
generate.py  one `claude -p` call per blueprint (Opus 5.5) with OUR prompt (content/prompts/): writes the question,
   │         our mark scheme, worked solution, hints, pitfalls and sympy-checkable answers
   ▼
gates G1-G8  deterministic (G1, G2, G7, G8) then model gates (G3 blind solve, G4 mark-scheme tests, G5 pitfalls,
   │         G6 tags); a failing item is regenerated once with feedback that never quotes Pearson text
   ▼
review_server.py  the user accepts / edits / rejects (G9); an edited item must pass the gates again (--regate)
   ▼
build_pack.py → content/clean/pack.db   licence gate (check_provenance.py): only original, accepted, gate-passed rows
   ▼
chatbot/ (CONTENT_PACK=clean)  tutor, practice finder, ladders, over our own questions
```

## 5. How to carry on (in order)

### Step 1: the user reviews the pilot (G9)
- Start the review screen: `! .venv/bin/python scripts/clean/review_server.py` → http://127.0.0.1:8766.
  - The queue is ordered by risk, copy-check flags first.
  - Keys: `a` accept, `r` reject with a reason code, `e` edit.
  - A timer records minutes per item.
- Edited items: `.venv/bin/python scripts/clean/generate.py --regate`.
- Then report: `.venv/bin/python -m eval.clean_gates_report` gives pass rates, reasons, cost, and review decisions and minutes.
- **Decide from this:**
  - Is quality good enough? The handoff sets ≥ 95% acceptance before sampling review.
  - How many minutes per item does review take? That decides the user's hours for the full bank.
  - Which reject reasons come up most? Fix those at the cause: prompt, blueprint or gate.

### Step 2: raise the pass rate before scaling (it's the main cost driver)
Where items still fail (round 3):
- **G7, 15 items:** mostly stock phrasing still missing from `content/novelty_whitelist.json`, plus a few genuine mark-scheme idioms. Grow the whitelist only with generic, functional phrases, and put each addition on the user's review list.
- **G8, 10 items:** marks outside a small type's range, and lowercase notation in notes.
- **G2, 8 items:** the checks format (e.g. `solutions` needs a list).
- **G6, 4 items:** the topic of the retagged skills differs.

Ideas that aren't built yet:
- Allow a second regeneration (today: 1 retry).
- Feed G2/G8 errors back with the exact field names.
- Let the generator adjust mark codes when the maths needs it (the user noticed an A1 where Edexcel would give M1).

Measure every change with `eval.clean_gates_report` on a batch of 20–30 before adopting it.

### Step 3: scale in batches
- **Command:** `.venv/bin/python scripts/clean/generate.py --ids <batch> --full --parallel 5 --skip-existing`. Choose batches of about 50–100 blueprint ids from `content/blueprints/exam.jsonl` / `drills.jsonl`. Select across components so each batch keeps the 9MA0 mix.
- **Budget:** about $1.60 per passing item today, so **~$1,200–1,800** for the ~1,130 remaining. This should fall as the pass rate rises. Report spend after every batch.
- **Stop rule:** if a batch's pass rate drops more than 10 points below the previous one, stop and investigate.
- **Mock papers:** generate the 84 `mk-*` blueprints (`content/blueprints/mocks.jsonl`, papers `mock-1-P1` … `mock-6-P3`). They need their own review, and a paper view in the review UI (not built yet).
- **Audits (G10):** a blind audit of a random 100 accepted items per 500; target ≤ 1% maths or mark-scheme errors.

### Step 4: build the clean pack and re-baseline the engine
- `.venv/bin/python scripts/clean/build_pack.py`: builds `content/clean/pack.db` from accepted items, then runs the licence gate.
- `CONTENT_PACK=clean .venv/bin/python scripts/build_embeddings.py`, then `CONTENT_PACK=clean .venv/bin/python -m eval.practice_eval`, `-m eval.practice_search_eval` and `-m eval.retrieval`. Re-baseline these on the clean pack (the handoff's targets: practice precision ≥ 99%).
- The tutor's smoke test: `.venv/bin/python -m eval.clean_pack_smoke`.

### Step 5: product features (priority order)
1. **Mark my working.** Reuse the G4 marker (`gate_marking.MARKER_SYSTEM`) as the product marker, and unit-test it with the stored G4 scripts (every item keeps them under `gate_results.G4.responses`).
2. **Weakness tracking** per skill (privacy-first; Children's Code).
3. **Mock mode:** timed, with a per-skill breakdown.
4. **Bring your own question:** estimated marks ("likely M1"); process, then delete.
5. **Caching** explanations, to fix the ~37 s wait.

Also still to do:
- **Brand name** without "Edexcel" or "Pearson", plus the line "Built for Pearson Edexcel A Level Mathematics (9MA0) · Independent: not affiliated with, endorsed or licensed by Pearson".
- **Product copy:** remove the remaining "past-paper" wording (welcome message; "official 9MA0 booklet").
- **Diagrams:** our own SVG or JSXGraph; they don't exist yet.

### Step 6: compliance before taking money
- **Solicitor review:** questions 1–7 in `commercial-relaunch-plan.md` §9. Question 7 is about the generic exam phrasing we allow.
- **Children's Code:** a DPIA and the ICO fee (£52).
- **Consumer law:** terms, a privacy notice, 14-day cancellation and easy cancellation.
- **Pilot:** about 100 free students (G11) before the paid launch.

## 6. The gates (what each checks)

| Gate | File | How it checks | Pass rule |
|---|---|---|---|
| **Licence** | `check_provenance.py` | Every commercial-pack row is original or ogl, accepted, and has passed G1–G8. No Pearson tables. No banned phrases ("examiner report", "Pearson Education", PMT…). | Run by every build and every eval on a commercial pack. |
| **G1** structure | `gates.py` + `generate.blueprint_conformance` | Marks add up; codes are valid; dM and A come after an M; ft names what it follows; A1* only in show-that parts; labels in order; the same parts, marks and command as the blueprint. | 100% |
| **G2** maths | `gate_maths.py` (sympy, run in a worker process with a time limit) | Every answer is verified by a check. Check types: derivative, integral, solution sets (missing or extra roots), binomial, normal, rounding. | 100% |
| **G3** blind solve | `gate_solve.py` | Sonnet 5.5 solves from the question text alone; answers compared with sympy (units stripped, 1 in the last figure allowed). A judge call decides format mismatches. | No "blocker" problems (minor ones are flags) |
| **G4** mark-scheme tests | `gate_marking.py` | Sonnet 5.5 writes 4–6 scripted answers with designed mark vectors; a marker applies OUR scheme. On a disagreement, a second marker (Opus 5.5) decides whether the scheme is ambiguous (fail) or the script was mis-designed (flag). | All scripts consistent |
| **G5** pitfalls | `gate_marking.py` | Each pitfall points to a step, uses a blueprint error code and the question's own numbers (or context), is shown by a script that loses marks, and says "common" only if its code has ≥ 10 matched notes. | 100% |
| **G6** tags | `gate_tags.py` | Haiku 4.5 retags blind. A different topic fails; a different skill in the same topic is a flag. | Bank target ≥ 95% skill-level agreement |
| **G7** copy check | `gates.py` (local only, against the Pearson corpus) | No 8-word run shared with Pearson outside the whitelist or maths-only runs; 5-gram Jaccard ≤ 0.15; < 3 distinctive shared numbers. Cosine > 0.97 rejects; cosine > 0.85 rejects only with the same marks per part plus 5-gram overlap ≥ 0.08; cosine ≥ 0.75 is a flag. | Self-test: rejects 40/40 copies and 40/40 number-changed variants; 3/3 originals pass |
| **G8** style | `gate_style.py` + `katex_render.js` | KaTeX renders; `$` delimiters only; marks in brackets; exact command words; answer forms asked for in the text; marks within the type's range; no board names or board rubric. | 100% |
| **Bank-level G8** | `check_blueprints.py` | The distance from the 9MA0 mix for the topic mix, marks per question and parts per question (TVD). | < 0.15 per component (now: pure 0.001 / 0.132 / 0.015; stats 0.000 / 0.033 / 0.033; mech 0.005 / 0.041 / 0.008) |

**Self-tests:**
- `.venv/bin/python -m eval.gates_selftest` (G1 and G7);
- `.venv/bin/python -m eval.gates_maths_style_selftest` (G2 and G8);
- `.venv/bin/python -m eval.clean_pack_smoke` (the tutor on a clean pack).

## 7. Key numbers

**The 9MA0 question mix** (298 current-spec questions, `content/facts/aggregates.json` → `mix_9ma0`):
- 18% one topic, ≤ 5 marks;
- 15% one topic, 6+ marks;
- 29% two topics;
- 38% three or more topics.

Stats and mechanics are over 85% multi-topic.

**Bank targets:** ~600 exam-style questions (pure ~420, stats ~90, mech ~90), 6 mocks and ~490 drills.

**Pilot costs:** $39.96 in total; about $0.35–0.45 per generation call and $0.05–0.15 for model gates per item. Generation takes about 1–3 minutes per item; about 16 minutes per 35 items at 5 in parallel.

**Knowledge base** (local only): 2,702 questions, 7,055 parts, 21,764 examiner notes; 246 skills; 73 question types.

## 8. Market and competitor findings

### alevelmathsrevision.com (researched 30 Sept 2026)
- **Who runs it:** John Armstrong, a qualified A Level Maths teacher and tutor (PGCE/QTS 2013, MSc Applied Maths, 15+ years of tutoring, claims exam-board marking experience). I found no registered company, so he's probably a sole trader. No accounts are published, so profit is unknown.
- **How it makes money:**
  - one-to-one tutoring at **£150/hour**, probably the main income;
  - **Easter revision courses** at universities (York, Surrey);
  - **ads** on the free pages;
  - the **"Ultimate Study Tool"** subscription: **£4.99/week, £9.99/month, £49.99/6 months, £83.99/year**, with a 30-day money-back guarantee, plus a schools version at bespoke prices. It offers 100+ hours of video, "thousands of exam-style questions" with worked solutions, **AI marking** of end-of-lesson tests against "the genuine A-Level mark scheme", 500 AI credits a month, and no ads.
- **Real questions?**
  - The **free** part hosts real past papers and mark schemes (AQA, Edexcel, OCR, MEI, Pearson IAL, CIE) as PDFs on its own domain, with no Pearson credit visible and no stated licence.
  - The **paid** tool's question source isn't stated. It says "exam-style questions", and his course page mentions thousands of worksheet questions he wrote.
  - No exam-board agreement or endorsement is claimed anywhere.
- **What Pearson's public policy allows:** only approved centres may copy past papers, for use inside the centre, never publicly and never for sale. So public hosting relies on unstated permission or on the boards not enforcing.
- **Reviews:**
  - **Google:** 61 reviews, all 5★, May–Sept 2023, all about the **tutoring and Easter courses**.
  - **Trustpilot:** no profile.
  - **The Student Room:** occasional praise for the **free** site; nothing about the paid tool.
  - **The paid tool's own pages:** no testimonials.
  - **Reddit:** not checked (my tools can't access it).
  - **Conclusion:** there are no independent reviews of the paid tool. It's small or recent; its AI features look new.
- **Lessons for us:**
  - His paid product sells *his own* "exam-style" questions and keeps real papers in the free section. That's the same split we're making, but we go further: no Pearson papers even in a free section, and past-paper links go to Pearson's own site.
  - No one has cornered mark-by-mark teaching or AI marking of working. The market is open.
  - Trust comes from a real teacher's expertise. Collect reviews from our ~100 pilot students; that would already be more public social proof than his paid tool shows.
  - His prices set the benchmark: £9.99 a month and about £84 a year.

### From the earlier research (`commercial-relaunch-plan.md`)
- **Save My Exams:** writes its own questions, and keeps real past papers in a section it says is "used with permission". Its "Smart Mark" *marks* answers but doesn't *teach* the marking. About £48 a year.
- **Dr Frost** (£650 + VAT per school a year), **Sparx** (from £600), **Seneca** (£646): the school market is about £600–650 per school per year. **Up Learn:** £320–420 a year, with a grade guarantee.
- **Corbettmaths, Dr Frost, Sparx and Up Learn** all write their own questions.
- **Physics & Maths Tutor** hosts past papers publicly; whether it has a licence is unverified. The paid product must not link to it.
- **Pearson v Chegg** (US, 2021, settled Dec 2024): Pearson does sue paid Q&A services over "copied or paraphrased" content.
- **Profit expectations:** most revision businesses have thin margins (Sparx lost £4.6m on £3.0m turnover in FY2022). A realistic outlook for us is £0–2k a month in year one, and £5–15k a month by years two or three if it works.

## 9. Open decisions for the user
All are in `docs/review-checklist.md` §28 (23 open items). The most important:
1. **Review the 25 passing pilot items** in the review screen. This is the go/no-go for scaling.
2. **Approve the generic-phrase whitelist** (`content/novelty_whitelist.json`, ~77 phrases such as "the finite region R is bounded by the curve C and the line l"), and take it to the solicitor (question 7).
3. **Review the 267 seed error codes** (`content/error_codes.json`).
4. **Mark the error-match samples** in `data/clean_private/error_match_samples.md`. They set the match threshold and the "common" threshold (`FREQUENT_NOTES` = 10).
5. **Approve the gate-rule changes** made on measured evidence (G3 severities, G6 topic rule, G7 cosine and shape rule, the distinctive-number threshold).
6. **Make the repo private,** and later approve the history purge.
7. **Check the Verisk employment contract** (IP and side-business clauses).
8. **Choose a product name.**

## 10. Known issues and cautions
- **The repo is public,** and `main`'s history holds Pearson and AQA material. **Never push this branch while the repo is public.**
- **Tracked data on `main`:** `data/processed/*.json` is tracked there. Untracking it on this branch only would delete those files from disk when switching branches. Only untrack as part of the full purge, after a backup (`handoff-clean-room.md` §2).
- **G6 is a weak check.** Many blueprint parts carry 3–6 skills, so "any overlap" passes easily. Consider requiring the main skill.
- **Mech sources lean on older IAL/GCE questions** (fewer 9MA0 sources). Watch that mech items don't feel old-spec.
- **Some mark-code patterns come from the blueprint consensus** and may not match how Edexcel would code that step (e.g. A1 where the board gives M1). The prompt allows adjustments, but the reviewer should watch for this.
- **The review UI:**
  - the `review.edited_before` and `review_history` fields exist;
  - the licence gate refuses items with `review.regate_needed`;
  - there's no mock-paper view yet.
- **The G2 worker** uses `select` on pipes, so it works on macOS and Linux, not Windows.
- **Pre-existing bug fixed:** the dry-run ladder crash on multi-part questions.
- **Tie-sorting:** recommendations with tied skill weights sort differently from run to run; use `PYTHONHASHSEED=0` when comparing runs.

## 11. Where things are
| What | Where |
|---|---|
| Design, legal firewall, gate specs | `docs/handoff-clean-room.md` |
| Commands, formats, lessons | `docs/clean-room-pipeline.md` |
| Legal and market research | `docs/commercial-relaunch-plan.md` |
| User's open decisions | `docs/review-checklist.md` §27–28 |
| Engine | `chatbot/` (`pack.py` is the content-pack switch) |
| Clean pipeline | `scripts/clean/` |
| Our content | `content/`: facts, blueprints, prompts, `error_codes.json`, `novelty_whitelist.json`, `clean/items/` |
| Set-aside pilot items | `content/clean/_rejected_round*/` (gitignored) |
| Evals and self-tests | `eval/` |
| Cost log | `logs/llm_calls.jsonl` (gitignored); pilot reports `logs/pilot_round1_report.txt`, `logs/pilot_round3_report.txt` |
| Pearson knowledge base (local only) | `data/processed/` (never shipped, never shown to a model) |

## Sources (market research)
- [alevelmathsrevision.com](https://alevelmathsrevision.com/)
- [About the author](https://alevelmathsrevision.com/a-level-maths-tutor/about-me/)
- [Ultimate Study Tool: students](https://alevelmathsrevision.com/ust/students/)
- [Pricing](https://alevelmathsrevision.com/ust/students/pricing/)
- [Schools](https://alevelmathsrevision.com/ust/schools/)
- [IAL past papers page](https://alevelmathsrevision.com/edexcel-ial-past-papers/)
- [Google reviews via Trustindex](https://www.trustindex.io/reviews/alevelmathsrevision.com-a-level-maths-tutor)
- [The Student Room thread](https://www.thestudentroom.co.uk/showthread.php?t=7019692)
- [Pearson copyright policy](https://qualifications.pearson.com/en/support/support-topics/exams/past-papers/pearson-copyright-policy.html)
- Earlier sources: `docs/commercial-relaunch-plan.md` (Sources)
