# Manual Review Log

**Running log:** Claude adds every item that needs a human check here as work goes on, in every phase. Nothing needs doing now; it's a record for later. Items are roughly in priority order within each section.

Everything that needs a human eye before the chatbot shows this content to students. Each item says what to look at and roughly how long it takes. Tick items off here, or just tell Claude "item 3.2 is wrong, it should be …" and it will make the fix.

PDFs: question papers `data/raw/papers/`, mark schemes `data/raw/markschemes/`, examiner reports `data/raw/examiner-reports/`, formula booklet `data/formula-booklet-9MA0.pdf`.

---

## 1. Corrections to our question and mark-scheme data (~20 min)
`docs/ms-audit-report.md` lists all **106 corrections** made against the official PDFs, each with its page reference, e.g. the missing modulus in P2 June 2022 Q9, the reversed domain in P1 June 2018 Q5, and cos 4θ → cos 2θ in P2 June 2019 Q12. There are 4 more fixed during the notation step: P1 June 2024 Q9 3^(2(k−1)); P2 June 2022 Q15(c) r = −1/√3; P1 June 2023 Q11(b) ¹⁰√…; P2 June 2018 Q2/Q3/Q4 "wait" asides.
- [ ] Spot-check **8–10** corrections against the PDFs. If all are right, trust the rest.

## 2. The 10 low-confidence questions (~10 min, mostly confirming)
| Question | Original doubt | Status now |
|---|---|---|
| P1 June 2018 Q14 | inequality signs for k = 7, 37/4 | **Resolved by audit** (MS PDF p.26): range is 7 ≤ k < 37/4; A1 structure corrected |
| P1 June 2019 Q8 | garbled wording of the (c) explanation | **Resolved by audit** (MS pp.17–18): official B1 statement restored |
| P2 June 2018 Q3 | mark split (b)(i)/(ii) | **Resolved**: hand-split checked the QP PDF, a = 2, b = 3 (combined); transcription aside removed |
| P2 June 2022 Q16 | domain −π/4 ≤ t ≤ π/3 reconstructed | Question-text audit compared with the QP PDF and found no error. [ ] Confirm on QP p.44 |
| P2 June 2023 Q11 | √h dropped by OCR | Question-text audit found no error; MS λ fixes applied. [ ] Confirm on QP p.30 |
| P2 Oct 2021 Q12 | u = 1 + √x reconstructed | Question-text audit found no error. [ ] Confirm on QP p.34 |
| P1 Oct 2021 Q15 | which value of m the MS special case uses | Not checked by the audit. [ ] Check MS (last question) |
| P1 Oct 2020 Q7, P2 June 2018 Q8, P2 June 2024 Q9 | "don't fit any of the 16 topics" | **Resolved by the new question types** (`quadratic-and-polynomial-graphs`, `linear-and-quadratic-models`). Nothing to check, unless you want a separate "quadratic trajectory" type (taxonomy Decision 2) |

Once you're happy, tell Claude to clear these `low_confidence` flags.

## 3. Question types and skills (~20 min)
`docs/taxonomy-draft.md` (45 types, 141 skills) is **already used for tagging** (1,523 skill tags on 478 parts). Changing it later is fine; tags are cheap to redo per paper.
- [ ] Skim the question-type table: is each question in a sensible bucket?
- [ ] Read "Decisions for you" (10 items), especially 2 (the quadratic-model types), 3 (one exponential type or two) and 9 (exam-technique skills are very common).
- [ ] **Suggested new skills from tagging.** Each is currently tagged with the nearest existing skill. Add any you want:
  - `inequalities-to-define-region` (P1 Oct 2020 Q7)
  - `trig-signs-in-quadrants` (P2 June 2023 Q15)
  - `refine-model` (P2 Oct 2021 Q15(d), P2 June 2022 Q9(b))
  - `angle-facts-in-radians` (P1 June 2023 Q8(b))
  - `period-of-trig-function-root-count` (P2 June 2018 Q6(c))
  - `maximise-quadratic-in-model-variable` (P2 June 2018 Q14(c))
  - `periodic-sequence-order` (P2 June 2022 Q3(a))
  - `area-from-vectors-or-diagonals` (P1 June 2022 Q9(b))
  - `unit-conversion-rates` (P2 June 2023 Q6(b))
  - `stopping-distance-context` (P2 June 2019 Q9(c))
- [ ] One type change was reverted: a tagger moved P1 June 2022 Q8 (car max speed) to `turning-point-by-iteration`. It's back in `optimisation-modelled-quantity`, as in your example, and part (c) still carries `fixed-point-iteration`.

## 4. Examiner notes (~30 min)
`docs/examiner-notes-review.md`: 10 random notes, 10 maths repairs, and the flagged report errors and rating calls.
- [ ] Work through sections 1–3 there.

## 5. Revision-site fixes found along the way (site, not chatbot)
- [ ] **8 wrong formula-booklet badges** on the topic pages. The old booklet file was a saved 404 page, so the badges were never checked against the real booklet:
  - Arc length and sector area are **not** in the booklet (the site says they are).
  - These **are** in the booklet (the site says "Learn this"): arithmetic series sum, geometric series sum, sum to infinity, binomial series, quotient rule, derivatives of tan/sec/cot/cosec.
- [ ] **Optimisation page:** it lists "P1 Oct 2020 Q7", which should be **Q9**.
- [ ] Optional: the optimisation page also lists P1 June 2018 Q2 and P2 Oct 2021 Q5, which are stationary-point questions rather than optimisation.

## 6. Housekeeping decisions
- [ ] The old 20 "techniques" (`data/processed/techniques/`) are now covered by skills (each is recorded in `merges_technique` in `tags.json`). Keep them as extra write-ups, or retire them?
- [ ] `node_modules/` belongs to root. When convenient, run `! sudo rm -rf ~/edexcel-maths/node_modules`, then `npm install`, so KaTeX installs inside the repo. Until then the checker uses a copy in `~/.cache/edexcel-maths-devtools`.

## 7. Smaller judgement calls logged by agents (low priority; skim when convenient)
**Question types that fit loosely** (kept as drafted):
- [ ] P2 June 2023 Q1 and P2 June 2024 Q1 → `stationary-points-and-nature`, although they only find f″ and concavity.
- [ ] P2 June 2024 Q6 → `turning-point-by-iteration`, although the equation comes from f′ = g′, not a turning point.
- [ ] P2 June 2022 Q9 (Ferris wheel, |A sin(bt+α)|) → `harmonic-form-and-trig-models`, although it has no R cos(x ± α) step.
- [ ] P2 June 2019 Q1 → `exponential-equations`, although it's really index laws.
- [ ] P1 Oct 2021 Q15 and P1 June 2022 Q7 → `proof-by-contradiction`, although each has one part using another proof method.
- [ ] P1 June 2023 Q13 → `linear-and-quadratic-models`, although part (c) is a cosine model.

**Skills that fit loosely** (the nearest existing skill was used):
- [ ] P1 June 2019 Q8(b): quartic factorisation tagged `factorise-polynomial-by-division` (described as cubics).
- [ ] P1 June 2019 Q13(a): constants from an asymptote, with no good skill.
- [ ] P1 June 2023 Q3(b) and Q7(d): simple a² > 18 / a² = 24 tagged as quadratic inequality / power equation.
- [ ] P1 Oct 2020 Q11(a): two-circle intersection, tagged via substitution and triangle trig.
- [ ] P2 Oct 2020 Q13(c): rational inequality in ln a, tagged `solve-quadratic-inequality`.

**Errors in Pearson's own documents** (our data keeps the official wording; decide if the bot should add a note):
- [ ] P2 Oct 2021 Q14(c) MS: "0.1h = 4.8 ⇒ h = 4.8" (should be 0.48).
- [ ] P1 Oct 2021 Q8(c) MS: "'0.339'", where k ≈ 0.139.
- [ ] P2 Oct 2020 Q12(b) MS: "allow awrt 2.40 m, 2.4 m — not awrt 2.4 m" contradicts itself.
- [ ] P2 June 2019 Q12(b) MS: uses ≤ although the question has a strict range.
- [ ] P1 June 2019 Q11(c) MS: "173 minutes and 3 seconds" (the calculation gives 2.5 s, which is borderline rounding).
- [ ] P2 Oct 2021 Q15(c) MS: "k < 1" (strictly |k| < 1).
- [ ] Examiner-report errors are listed in `docs/examiner-notes-review.md` §3.

**Official content missing from our transcriptions** (nothing wrong, just incomplete):
- [ ] Some official alternative methods and special cases aren't transcribed, e.g. the P2 Oct 2020 Q8 alternative, the Q10(a) right-to-left proof and the EPEN labels on Q9/Q12; P2 June 2023 Q9 "Way 4" and Q13(c) third bullet; P2 Oct 2021 Q8(b) alternative and Q15(c) special cases. That matters if a student uses one of these methods.

**Notation choices:**
- [ ] Recurring decimals are written as "4.4 recurring" rather than dot notation (the number check can't compare dots).
- [ ] P1 June 2023 Q15 domain now reads "x > ln(2^(1/3))", as printed, rather than (1/3) ln 2.

**Structure:**
- [ ] P2 June 2024 Q3 is one part covering (i)–(iii), because the paper gives a single (4) for all three.
- [ ] Figure images are whole question-paper pages, not cropped figures. Only 2 of 57 were spot-checked.

## 8. Admin and security
- [ ] **Revoke the old GitHub token** (github.com/settings/tokens). It was stored in plain text in the git remote URL; it's since been removed from the URL and no longer works.
- [ ] **New token or login** for pushing: `! gh auth login`, then `! gh auth setup-git`.
- [ ] **Commit identity:** this repo now commits as `hblbennett-arch <hblbennett@gmail.com>`. Earlier commits used your Verisk email; they're unchanged unless you want history rewritten.
- [ ] **`CLAUDE.md` is out of date:** it says "Do NOT commit files from `data/`", but `data/processed/` is now tracked by your decision. It also doesn't list the new docs and skills. Approve an update when convenient.
- [ ] **Uncommitted work:** everything since commit `41193df` (Phases 2–3) is local only.
- [ ] **AQA physics PDFs** you uploaded to the repo root (`AQA-74081-WRE-*.PDF`, `Data Sheet aqa physics.pdf`) are committed at the top level. Consider moving them under `data/raw/` for the physics project.

## 9. Older items carried forward
- [ ] **The 20 original technique write-ups** are general maths knowledge, not from Pearson. They need a subject-expert pass if kept (see §6).
- [ ] **June 2025 papers** (all components) are listed in `sources.json` but not ingested. Keep them back as the unseen test set for Phase 6.
- [ ] **The chatbot's answer quality** will need your hand-marking of about 5 answers when Phase 6 runs (grader calibration).

## 10. Phase 4: retrieval and recommendations (added 2026-09-25)
Results are in `eval/retrieval_results.txt` and the test set is in `eval/retrieval_queries.json`. Try things yourself with `.venv/bin/python -m chatbot "<message>" [--hardest b]`.
- [ ] **Generic test queries:** check the 20 queries and their expected skills in `eval/retrieval_queries.json`, and add real student phrasings you've seen. The set is small, so 100% recall on 20 queries is encouraging, not proof.
- [ ] **Pasted-question thresholds** (`chatbot/identify.py`) were tuned on the same 30 pastes and 6 made-up questions they're scored on. Re-check them once real student pastes exist; a larger test set should come before trusting "confident" matches.
- [ ] **Known weak spot:** "integrate x eˣ" ranks integration by parts 3rd (behind powers-of-x and standard integrals). Mixing in votes from similar exam parts fixed this case but made the average worse, so it's off.
- [ ] **Difficulty scores** (starter / core / stretch in `chatbot/recommend.py`) are a hand-set formula: 0.6 × marks + 0.5 × skills, ±1.5 for the examiner rating, and a mean-mark adjustment. Spot-check some ladders: does the order feel easy → hard to you as a teacher?
- [ ] **"Possible match" wording:** when the bot isn't sure, it asks "Is this P1 June 2023 Q4?" before teaching. Decide how that should read in the UI.
- [ ] **Where the embedding model lives:** `~/.cache/edexcel-maths-devtools/fastembed` (bge-small, about 130 MB), outside the repo. Python uses the Mac trust store (`truststore`) because of the TLS-inspecting network.
- [ ] The larger bge-base model was tested and was no better (`embeddings_baai-bge-base-en-v1-5.npz` is gitignored and can be deleted).

## 11. Phase 5: tutor conversation (added 2026-09-25)
Try it with no key: `.venv/bin/python -m chatbot.chat --offline` (mark scheme walkthrough) or `--dry-run` (shows exactly what would be sent).
- [ ] **Where the tutor runs:** it uses your **Verisk Claude Enterprise login through Claude Code** (`TUTOR_BACKEND=claude-code`, the default; decided 2026-09-25). There's no API key; usage counts against your Enterprise seat. For an API key instead, set `TUTOR_BACKEND=api` plus `ANTHROPIC_API_KEY` in `.env`.
- [ ] **Measured cost and speed (Haiku 4.5 via Claude Code):** about **$0.04–0.05 per question** when it passes first time; a retry doubles it. It takes **45–70 seconds** per question, which is slow for a student waiting. There's a cap of $0.50 per call (`TUTOR_MAX_USD_PER_CALL`). The first two real answers (P1 June 2022 Q15, P2 June 2019 Q13) followed the official mark schemes and passed every check.
- [ ] **Claude Code route limits:** each call starts a fresh `claude -p` process with no tools, no connected services and an empty working folder (`~/.cache/edexcel-maths-devtools/claude-code-cwd`). Follow-ups replay the conversation as text, so long conversations cost more per turn. The tutor's instructions replace Claude Code's own.
- [ ] **Model: Claude Haiku 4.5** (`claude-haiku-4-5`), your choice (2026-09-25). It's the cheapest current model ($1/$5 per million tokens, about 5× cheaper than Opus 5), estimated at roughly $0.02–0.05 per question until measured. It uses a fixed 4,000-token thinking budget (`TUTOR_THINKING_BUDGET`). Phase 6 measures whether its maths is accurate enough; if not, `TUTOR_MODEL=claude-sonnet-5` or `claude-opus-5` in `.env` switches with no code change.
- [ ] **Safety fallback** only applies to Opus 5 / Fable 5.1, so it's off for Haiku.
- [ ] **Read the tutor's instructions** in `chatbot/prompts.py`: the tone, the scaffolding rules and "student" vs "tutor" detail. This is the main place to shape how it teaches.
- [ ] **No prompt caching on Haiku 4.5:** it only caches prompts of 4,096 tokens or more, and the fixed instructions are about 940 (a lost saving, not an error). It becomes worthwhile if the instructions grow, e.g. with worked-example style samples.
- [ ] **Automatic checks** (`chatbot/validate.py`) catch mark codes not in the mark scheme, marks that don't add up, final answers matching no mark-scheme value, and invented examiner quotes. They can't judge whether an explanation is clear or pedagogically sound; that's the Phase 6 grader plus your hand-marking. Proofs, sketches and explanations have no automatic answer check.
- [ ] **Where hints are shown:** the "how to start" hint and the examiner warnings appear together at the start of each part. Decide whether warnings should wait until after the student has tried.
- [ ] **Answers are logged** to `logs/answers.jsonl` (gitignored), including the full reply, check results and token usage, so weak answers can be reviewed. Student messages are logged too; bear that in mind before anyone else uses it.
- [ ] **Understanding what the student types is rule-based** (patterns in `chatbot/chat.py` and `chatbot/identify.py`). Your first test exposed 4 gaps, now fixed and covered by `eval/chat_smoke.py`. Other phrasings will still slip through. When you find one, note the exact wording here; each becomes a new smoke-test case. Once live mode is running, a cheap model call could interpret unclear messages instead.
- [ ] **"Give me a question on X"** now lists real past-paper questions found from their wording. Check a few topics you know well: are the top 5 the ones you'd pick?
- [ ] **Follow-up answers aren't automatically checked.** Only the main structured explanation is. In your first live test a follow-up wrongly said sector area is in the formula booklet. Follow-ups now get the question's booklet facts explicitly (fixed and re-tested), but other factual slips are possible, especially from Haiku. Spot-check follow-ups; Phase 6 should include some.
- [ ] **Cost varies per answer:** measured at $0.047–0.07 for Q15 and Q13 without retries; follow-ups cost about $0.004–0.03 and grow as the conversation replays. A validator false alarm (formula answers in "show that" parts) caused an unnecessary retry; that's fixed.
- [ ] **Local web UI** (`python -m chatbot.web`, added 2026-09-25) is a *testing harness*, not the product UI you plan to design. It runs on this laptop only (127.0.0.1). It loads KaTeX 0.16.9 and marked from the jsdelivr CDN (as the revision site does), so it needs internet for maths to render. The terminal chat and the web page share `chatbot/controller.py`, so fixes apply to both. Handy test links: `http://127.0.0.1:8765/?try=2022 paper 1 question 15|y|next` types messages automatically.

## 12. Next piece of work: Stats, Mechanics and legacy/international papers (added 2026-09-25)
The handoff for a new session is `docs/handoff-stats-mech-legacy.md`.
- [x] **Scope (answered 2026-09-25):** 9MA0 (current) plus IAL 2018, IAL 2013 and the old UK GCE (C1–C4, S1–S3, M1–M3) as extra question sources, all filtered to 9MA0 content. June 2026 is included if public.
- [ ] **June 2026, January 2026 and October 2025 papers are locked.** Pearson lists them, but they redirect to the Edexcel Online login (teachers only; Pearson locks the last ~9 months for mock exams). They are recorded as 🔒 gaps in `docs/pearson-coverage.md` and weren't downloaded. With a teacher login they could be added by hand later; otherwise rerun `scripts/scrape_pearson.py --download` once Pearson unlocks them.
- [ ] **The 9MA0 specification content list** `data/processed/spec_9ma0.json` (89 statements: 62 Pure, 14 Stats, 13 Mech), transcribed from `data/spec/9MA0-specification-issue4.pdf`. It decides what's kept, so please skim it against the PDF (pp. 11–38). The words are machine-checked against the PDF text (`scripts/check_spec.py`); the maths is written with Unicode symbols (√, ≤, θ), not LaTeX.
  - [ ] `as_common` (bold = shared with AS) is a judgement call where a cell is partly bold: P1.1, P3.2, P4.1, P5.1, P5.3, P7.3, P8.3, M6.1, M7.3, M8.2–M8.4 were marked true; P2.5, P2.7, P7.1, P7.2, S2.3, S2.4 are null (mixed).
- [ ] **Six question papers have no text layer** (scanned images): 9MA0 June 2019 Paper 3 (Stats and Mech), GCE C1–C3 January 2007, GCE C1–C2 June 2019. Agents read them from the page images; the scripted checks against printed totals can't run on them, so spot-check one.
- [ ] **Pearson's Jan 2022 "UNUSED" contingency papers** (WMA14, WME03, WST03) were published alongside the sat papers. They're treated as extra papers (`…U_Jan2022`).

## 13. Stats/Mech Tier 1: 9MA0 Paper 3 (added 2026-09-26)
15 papers extracted (June 2018 combined, then Stats + Mech for June 2019, Oct 2020, Oct 2021 and June 2022–2025): 92 questions kept. Every file passes `scripts/check_questions.py`, which now also checks against the question paper's own text: printed part marks in order, verbatim prose, numbers, mark-code counts, figure references, spec refs vs component, Unicode maths.
- [ ] **Errors the new checks caught and fixed** (logged in each question's `notes` as `[fix_parts]`). Spot-check two against the PDFs:
  - P3 Oct 2021 Stats Q4: (b)(i)/(ii) and (c)(i)/(ii) had been split although the paper prints one mark total for each; merged.
  - P3 June 2023 Stats Q6(e): (i) and (ii) have separate printed marks (1)+(2) but had been merged; split.
  - P3 June 2025 Stats: no printed mark tokens in the part texts (added); Q1(c) had "at least one of **the two** beads", where the paper says "of the beads"; Q6(b) MS "0.2380952", where the MS says "0.238095"; Q4(c), Q4(f), Q5(a) over-split and merged.
  - P3 June 2019 Stats Q2(a): "½" changed to LaTeX.
- [ ] **June 2019 Paper 3 PDFs are scans:** their questions have no `qp_pages` / `figure_pages`, so **Mechanics diagrams for June 2019 can't be attached to tutor answers yet.** Fix: record pages by hand, or have the single-call method return pages for scanned papers.
- [ ] **Judgement calls to confirm:** Large Data Set "how is it recorded" parts are tagged S2.4 plus a note (no numbered statement fits); Mechanics "state a limitation / refine the model" parts are tagged with the technique's own statement (M8.4, M9.1, M7.5).
- [ ] **Oddities agents found in Pearson's own mark schemes** (kept verbatim): June 2023 Stats Q1(c) "on epen this is labelled M1 but treat it as A1"; June 2018 Q6 a garbled glyph before 30 (should be −30); June 2024 Stats Q3 notes table wording; June 2019 Stats Q3(a) contradictory "Accept H0, therefore positive correlation" line (scores A0).
- [ ] **Retrieval eval after adding the 92 questions:** pasted-question identification is 29/30, and one case now falls outside the tracked categories. Re-check after Stats/Mech tagging.
- [ ] **Follow-up worth doing (cheap, scripts only):** run the new text/number/mark-sequence checks over the 14 original Pure papers too. They predate the v3 fields, so they need a small adapter.

## 14. Pearson downloads (added 2026-09-26)
- [ ] **25 dead links on Pearson's site** (listed, but the file is missing; no working copy under another name). All are IAL-2018 papers from 2020–2022, e.g. WMA12 Jan 2020 QP, WMA12 Oct 2021 QP/MS/ER. The full list is under Gaps in `docs/pearson-coverage.md` (✗). These papers can't be processed unless you get the files another way.
- [ ] **42 downloaded files have no usable text** (scanned, or a font pdftotext can't map; e.g. GCE S2 June 2012 comes out as shifted letters with no digits). Agents read them from page images, but the automatic checks against printed marks and text can't run on them, so spot-check a few.
- [ ] **Out-of-spec questions (your rule, 2026-09-26):** they never enter questions/, notes, tags, the database or the search index (`build_db.py` refuses to build if one leaks in). Their record is kept in `data/processed/_excluded/` (full transcription for the pilot papers, and from now on just marks + reasons), and the raw PDFs/text stay in `data/raw/pearson/`.

## 15. Cheaper pipeline: accuracy vs the agent method (added 2026-09-26)
Measured on the same papers, old method vs new (full numbers in `docs/skill-add-papers-pipeline.md` → Measured costs):
- **Blind audit** (auditors didn't know which method made the file), 3 papers: agents 0 factual errors + 4 omissions; single-call 0 + 3. [ ] Caveat: those audits were lenient. My own comparison found official Notes missing from an agent file that its auditor passed, so the scripted checks remain the main safeguard.
- **Examiner notes** (P3 June 2022 Stats): agent $0.95 / 90% of the report covered / 13 ratings; new "classify sentences" method $0.18 / 92% / 15. Same question 100%, same part 86%, same kind 86%. [ ] Spot-check 5 notes from a new-method paper (e.g. `examiner_notes/P3_June2024_mech.json`) against the report.
- [ ] **Report error found:** P3 June 2022 Stats report says "part (d) was a conditional probability question"; on the paper that's part (f), P(F | H). Notes are filed by content (f).
- **26 Paper 3 notes** had a part label the question doesn't have (report wording); they're kept at question level, not guessed.

## 16. Stats/Mech taxonomy: your review is needed before tagging (added 2026-09-26)
- [ ] Read **`docs/taxonomy-draft-stats-mech.md`** (~20 min): 10 topics, 28 question types (each listing its questions), 105 skills in 16 groups (shared exam-technique/algebra/calculus skills reused), and 9 decisions for you. Formula-booklet flags were checked by Claude against the real booklet (11 in the booklet, 4 not). **Nothing is tagged until you reply.**

## 17. Spec triage of legacy papers (added 2026-09-26)
- [ ] **`docs/spec-triage-review.md`** lists every medium/low-confidence keep/drop decision (regenerated after each run). Overrule any with "keep <paper> Q<n>" / "drop <paper> Q<n>".
- Triage v1 dropped M1 Jan 2024 Q8 (connected particles on an inclined plane) with high confidence, although its own reason said it was in spec (M8.4's guidance covers it). Fixed in v2: the reason is written before the decision, a script check catches reason/decision contradictions, and borderline cases go to you rather than being dropped. v2 gives the same decisions as the agents on the 4 comparison papers.
- The 4 IAL Jan 2014 C1–C4 papers (unit codes 6663A–6666A) are now tagged **IAL-2013**, not GCE-2008: they're headed "International Advanced Level" and Pearson lists them under the IAL 2013 spec (you spotted this).

## 18. Tier 2: IAL 2018 (added 2026-09-26)
144 papers → **848 kept questions** (645 Pure, 131 Mech, 72 Stats) and 393 dropped (top reasons: Poisson, Spearman's rank, continuous uniform / pdfs, centre of mass, two-sample tests, work–energy). All 148 IAL-2018 papers pass `check_questions.py` and `completeness.py` shows 0 gaps. Cost **$104.67** (triage $34, extraction $58, notes $12.50), with every call logged in `logs/llm_calls.jsonl`.
- [ ] **`docs/spec-triage-review.md`** now lists only decisions that could change what the chatbot contains: **A** (181 kept questions with an uncertain part: could out-of-spec content get in?) and **B** (25 questions dropped only on uncertain grounds: could good material be lost?). Group B is the quicker, higher-value read. Look out for scalar product, volumes of revolution (both Further Maths, so correctly dropped?) and logarithmic differentiation (borderline).
- [ ] **The 15 papers that first failed were fixed by script**: 4 over-split parts merged; 1 crash (the model wrote "Q1"); 9 were checker false alarms, now fixed in the checker (LaTeX environment names, number grouping, one reordered caption, `dddM1`, Pearson's `M(A)1`). One verified override: WMA13 Oct 2024 Q1 (109.5°, 250.5° are on MS p.7 but missing from its text layer).
- [ ] **A flaw found in my own autofix:** it added a made-up "(2)" to an over-split sub-part, which hid the error. Fixed: it no longer touches sub-parts.
- [ ] **24 question papers have a partly scrambled font** (letters shifted, digits lost; 2 in Tier 2, 22 in Tier 3). The text checks are skipped for them (NOTICE). They should be decoded before Tier 3.
- [ ] **Identifying pasted questions is harder now:** IAL papers reuse near-identical questions across sittings, so the bot now asks "is this X?" unless one stored question clearly leads (new thresholds in `chatbot/identify.py`: semantic ≥ 0.85, lead ≥ 1.05). Eval: 25/30 confident-and-right, 4 ask-to-confirm, 1 asks about the near-duplicate twin, 0 false confident matches (was 1). [ ] If a student says "no", the bot should offer the runner-up; check that this works in `chatbot/controller.py`.
- [ ] 49 papers' notes were missed silently by the Tier 2 run (cause not pinned down) and filled afterwards. `scripts/completeness.py` now ends every run, so a gap can't go unnoticed again.

## 19. Scope change: S1/M1 only for legacy Stats/Mech (your decision, 2026-09-26)
- Going forward only **S1 and M1** are processed for legacy Stats/Mech (plus all Pure units and all of 9MA0). No Further Maths, which was never scraped. The rule is in `scripts/scope.py`; extraction, prompts and the completeness check all read it.
- **155 S2/S3/M2/M3 papers** came off the Tier 3 queue; their files stay in `data/raw/pearson/`. The Tier 3 queue is now 206 papers (GCE C1–C4/M1/S1; IAL 2013 C12/C34/M1/S1 + Jan 2014 C1–C4).
- **Already-processed S2/S3/M2/M3 work is parked, not deleted:** 55 papers / 65 questions (and their examiner notes) moved to `data/processed/_parked/`, which the chatbot build doesn't read. To bring them back: `scripts/park_units.py --unpark`, then rebuild. Their staging and triage files stay in place.
- After parking: 1,085 questions in the chatbot; retrieval eval 100% pasted top-1, 0 wrong matches; all conversation tests pass.

## 20. Diagrams for the new questions (added 2026-09-26)
How it works: each question stores the **page numbers** of its figure(s) in the question paper (`has_figure`, `figure_pages`). When the tutor explains the question, `scripts/render_figure.py` renders those pages of the Pearson PDF to images (cached in `data/cache/figures/`, local only) and sends them to the model.
- **Bug found and fixed:** the Tier 1/Tier 2 question files had lost their figure pages, because `apply_spec_filter.py` rebuilt them from staging and dropped those fields. Now the spec filter computes figure pages every time it writes a file, so they can't be lost again. Pure files are unchanged (checked: 0 differences).
- Fallbacks: where the text layer can't locate a figure (scans, scrambled fonts, odd layouts), the whole question's pages are attached, from the extraction's recorded pages. The two scanned June 2019 Paper 3 papers were page-mapped by `scripts/page_map.py` ($0.04; Mech Q4 → p.10 checked by eye).
- Statistics diagrams often have no "Figure N" label (scatter diagrams, box plots, histograms, Venn/tree diagrams): those questions now get their pages attached too. Result: 47/95 Stats, 78/134 Mech, 244/856 Pure questions have figures; 0 figure questions without pages.
- [ ] Spot-check 3 figure attachments: run `.venv/bin/python scripts/render_figure.py IAL2018_WST01_Jan2023_Q1` (and two Mech questions), open the PNG paths it prints and confirm each shows the right diagram.

## 21. Tagging, spec gaps found by tagging, and chatbot updates (added 2026-09-26)
- **Stats/Mech vocabulary merged into `tags.json`** (Mech approved by you; Stats as drafted): 73 question types, 246 skills in 47 groups.
- **Tagging method measured against the agents** on 3 agent-tagged Pure papers: Sonnet single call recovered ~75% of the agents' skills (a "what's missing" 2nd pass didn't help); **Opus 5.5 single call recovered 93% at the same 91% precision**, so it's the tagger ($0.17/paper; $13 for 109 papers, then $5 to re-tag Stats/Mech with the full skill list). All 1,068 questions typed, 8,549 skill tags, 88% of parts with ≥2 skills.
- [ ] **`docs/tag-suggestions.md`**: 139 distinct skills/types the tagger thought missing (each part was tagged with the nearest existing skill). The recurring ones are the best candidates: define-region-with-inequalities, remainder-theorem, stem-and-leaf-reading, midpoint-of-segment. Say which to add.
- **Spec-filter misses found and fixed:** tagging flagged Further Maths content in **18 kept IAL P4 questions** (vector equations of lines, the scalar product, volumes of revolution). The 9MA0 statements mention none of these (checked by script). My loosening of triage's "when in doubt, out" wording let them through. Fixed with `scripts/concept_screen.py` (a model screen plus a precise text check, since the model alone missed one), and the verified concept list is now in triage for Tier 3. The 18 questions and their 201 notes/tags moved to `_excluded/`. [ ] Glance at `data/processed/_concept_screen/` hits if you like; all 18 are IAL WMA14.
- **Chatbot:** understands "S1 January 2020", "WST01 Jan 23", "M1 June 2012", "C34 June 2016", "IAL P3 Jan 2024", "paper 3 stats 2019", "9MA0/32 …", and asks when two papers fit; says "not in the knowledge base" for S2/S3/M2/M3/Further Maths; legacy questions are labelled ("International A Level (2018 spec) S1 (WST01) Jan 2023"); recommendations put 9MA0 first within each difficulty tier; the tutor has Stats/Mech conventions taken from the Paper 3 mark schemes (g = 9.8 → 2–3 s.f., model notation, hypothesis-test conclusions in context). Tests: 24/24 references, 10/10 conversations.
- [ ] **Handoff for the next session:** `docs/handoff-tier3.md`.
- [ ] **Try it:** `.venv/bin/python -m chatbot.web` then open http://127.0.0.1:8765 and ask e.g. "P3 June 2022 mechanics Q4" or "WST01 Jan 2023 q2". Each live answer costs ~$0.05.

## 22. Pre-Tier-3 accuracy checks (added 2026-09-26)
- **Blind, symbol-focused audit of 6 random Tier 2 papers** (Opus, ~1,010 maths expressions compared with the PDFs): **1 symbol error** (a "…" inside the wrong bracket, fixed), 3 dropped words (fixed), and 27 pieces of official mark-scheme content missing (about 4.5 per paper, mostly scheme working lines and notes such as "send to review if…"). The "missing questions" the auditors reported were all correctly dropped as out of spec. [ ] The missing MS notes are the main remaining quality gap. They're listed per paper in `data/processed/_audit_t2/audit/*.json` (`omissions`), if you want them added.
- **Found by the audit and fixed across all files:** 58 questions with duplicated wording (the stem repeating a part's text, or a part repeating the stem). Now fixed, prevented in the extraction prompt, and caught by `check_questions.py`.
- **A real transcription failure:** in IAL WMA12 Oct 2019, page trimming dropped the page holding Q3/Q5 (scrambled font), and the model **reconstructed** those questions from the mark scheme. It's re-extracted from the paper now (Q5 reads "Given 0 < a < 1, sketch the curve y = aˣ …", not the reconstructed "sketch y = (½)ˣ"). The checker now hard-fails any text that says it was reconstructed or inferred; the old version is in `_superseded/`.
- **Scrambled fonts are now decoded fully**, digits included (a shifted space is \x03, a shifted "4" is \x17), so those papers get the normal wording and number checks. Tier 3 has 22 such question papers.
- A minus-sign cross-check was tried and **dropped**: text layers can't tell subtraction from a negative number, so it only produced false alarms. The audit above is the measure of symbol accuracy.

## 23. Mark-scheme completeness pass: pilot (added 2026-09-26)
- **`scripts/ms_complete.py` piloted** on the 6 audited Tier 2 papers, written to copies (`data/processed/_ms_complete_trial*`), **not to staging**. Scored against the audit's 27 omissions: 5 were whole questions correctly dropped as out of spec, and 2 were question-text gaps (below), which leaves **20 missing pieces of official MS content**.
  - **Sonnet: 3/20 recovered.** **Opus 5.5: 20/20** on the final script, with 0 rejected by the verbatim or number guards and 0 wrong additions in the ones I checked by hand against the MS text. Opus also added ~30 official lines the audit hadn't listed (e.g. Jan 2022 Q5(a) "They may work in degrees which is acceptable"). The default is now Opus.
  - **Fixed 3 bugs before any real use:** (1) the "already present" check compared words only, so maths-only working lines ("$0.42/0.512=0.8203…$ awrt 0.820") were wrongly dropped; it now compares numbers and normalised LaTeX too. (2) Notes for a whole multi-part question ("Allow column vectors throughout…") were rejected; they now go on the first part, prefixed "(Whole question)". (3) Maths-only lines skipped the verbatim guard; a decimals-in-MS guard now covers them.
- [ ] **Question-text gaps the pass can't fix** (it only adds MS content): IAL WST01 Oct 2023 Q2(c) doesn't describe Figure 1's February box plot values (whiskers 28 and 80, Q1 42, median 50, Q3 58), which part (d) needs; Q3(i)(a) doesn't describe the Venn diagram's regions (w = O only, x = O and C, y = C only, z = outside). Say whether to add them as `[editor: …]` descriptions.
- [ ] **Spot-check 2 completeness-pass additions** once it's run on staging: open `data/processed/_ms_complete/IAL2018_WMA11_June2019.json` and compare two `accepted` lines with MS pp.8–10.
- **Run on Tier 1/2 staging (145 papers, Opus): $33.51, 2,836 official lines added, 104 rejected** (84 already present, 14 by the number guard, 6 by the verbatim guard). Some papers had lost nearly all their official Notes at extraction (WMA14 Oct 2024: 95 added; WMA12 Jan 2022: 84), a bigger gap than the 6-paper audit showed. About 8 guard rejections were over-cautious (numbers the PDF text layer drops, e.g. WMA13 Oct 2024 θ = 109.5°), so those lines are still missing; that's the safe direction.
- **Repairs after the run:** 34 Unicode symbols (±, ×, θ, ½ …) in added lines converted to LaTeX by script; the "repeated item" check was made to accept repeats the official MS itself prints (Mech: "A1: Correct equation" once per equation).
- **2 real over-split parts found by a new check and fixed** with `fix_parts.py`: IAL WMA12 June 2019 Q10(c) and WST02 Oct 2020 Q3(a). In each, the model invented "(1)/(2)" mark brackets from the MS where the QP prints one bracket for (i)+(ii). Tags merged to match. [ ] Glance at WMA12 June 2019 Q10(c) on QP p.28 if you like.
- **Tier 3 pilots (6 papers) matched Tier 2's accuracy:** no reconstructed text; 1 real error (IAL C12 Jan 2015 Q4(b): the model wrote "$2.025$ raised to the power $10$" for 2.025¹⁰ in the question and MS, fixed); 3 checker false alarms fixed in the checker (the "fi" ligature in the scrambled font, two-digit merged superscripts, the missing-MS crash).
- [ ] **13 Tier 3 papers can't be processed: Pearson publishes no mark scheme for them**: GCE C1–C4/M1/S1 June 2007 and June 2009, and IAL C34 (WMA02) Jan 2020. If you have the mark schemes from elsewhere (e.g. a teacher login), put them in `data/raw/pearson/…` as `<id>_MS.pdf` and they'll be picked up.


## 24. Tier 3: GCE (pre-2017 UK A Level) + IAL 2013, added 2026-09-27
- **Added:** 206 papers (GCE C1–C4/M1/S1, IAL 2013 C12/C34/M1/S1 + Jan 2014 C1–C4) → 1,634 in-spec questions. The chatbot now has **2,702 questions**, 21,764 examiner notes, 20,867 skill tags. All checks pass; completeness 316 papers, 0 gaps; retrieval references 31/31, pasted-question matching 0 wrong; chat smoke tests all OK; practice lookup 227/228 skills, 100% precision.
- **Cost:** Tier 3 $271.81 (≈$1.32/paper incl. the visual MS check); whole session $307.54 (you approved going over $300 for the visual check).
- **Blind Opus audit, 6 papers (~1,090 expressions):** 18 corrections, 4 omissions (≈0.7/paper, vs 4.5 in Tier 2 before the completeness pass). 11 corrections were stray "(N)" marks after lead-in lines, fixed across **126 parts in all tiers** by script. 5 were MS maths errors (root span, dropped root, wrong fraction values, x for x/3), so `ms_verify.py` (visual Opus check) ran on every Tier 3 paper: **118 corrections**; 15 of them spot-checked on the page, all right. Question text had 0 maths errors in the audit.
- **Real errors found and fixed by the checks during extraction:** 6 (a paraphrased power, a dropped M1, an over-split part, two wrong digits, a missing recurring dot), plus 2 over-split parts in Tier 2 and 1 wrongly dropped in-spec Mechanics question (IAL M1 Jan 2016 Q6, position-vector kinematics is 9MA0 M7.3; restored, concept screen fixed).
- [ ] **Spot-check 3 of the 118 visual MS corrections** yourself: `data/processed/_ms_verify/*.json` (`accepted`), e.g. GCE C2 June 2011 Q9(b) (+64/3), GCE S1 June 2016 Q4(d) (recurring dots), IAL C12 Jan 2015 Q15(b).
- [ ] **Pearson's own mark-scheme errors, kept as printed:** IAL S1 Jan 2014 Q6(c) "0.17194 < σ < 0.17195" (should be 0.01719…); GCE C1 June 2016 Q9(d) "the 450 or 450"; GCE C3 June 2006 Q5(b) QP "4 decimals places" (transcribed "decimal places"). Say if the tutor should flag these to students.
- [ ] **4 audit omissions not added** (official content still missing): GCE C1 June 2008 Q3(a) sketch example "scores B0B1B0"; IAL C12 Jan 2018 Q4(b) accepted answer forms and Q14(b) Way 2 lines; IAL S1 Jan 2014 Q5(a) alternative Venn form. Listed in `data/processed/_audit_t3/audit_orig/*.json`.
- [ ] **Mark labels ("1st A1" vs "2nd A1") can't be checked by script** (alternative methods restart the numbering); the audit found 2 wrong in one part (fixed). Low impact for tutoring.
- [ ] **13 papers with no published mark scheme** (GCE June 2007/2009, IAL C34 Jan 2020) aren't in the chatbot. See §23.
- [ ] **New questions pasted by a student now always get "is this the question?"** (6/6 in the eval, was 3/6): with 2.5× more questions, more new questions look like a stored one. It's the safe direction (0 false confident matches). Say if it feels too cautious in use.
- [ ] **Scanned papers** (9 in Tier 3, text checks skipped): spot-check one, e.g. `GCE2008_6677_Jan2007` (page map + transcription) against its PDF.
- [x] **"Find me a question on differentiating x^x" missed P2 June 2019 Q11** (your test, 2026-09-27): practice lookup only used skill tags, and "x^x" matched the skill "differentiate polynomials". It now also searches the question LaTeX for a specific expression in the request (normalised on both sides; powers grouped so e^{2x} doesn't match e^{2x+1}; expressions in >25 questions, like x^2, are left to the skill search). Exact matches are listed first ("contains x^x"). Regression case added to `eval/practice_eval.py`. [ ] Try a few of your own niche expressions and note any misses here.
- [ ] **Try it:** `.venv/bin/python -m chatbot.web`, then e.g. "C1 June 2012 Q3", "UK M1 June 2014 Q5 (c)", "IAL C12 January 2015 question 4b".

## 25. Practice search: descriptions, several topics, several skills (added 2026-09-27)
- [x] **"Find me a stats question to do with dentists and 10% of customers arriving late" missed P3 June 2022 Q4** (your report): the practice lookup only used skill tags. It now also searches the question wording when no skill matches well, so that question comes first. It also finds questions covering **several topics or skills at once** ("can you find a question that uses differentiation, partial fractions and stationary points" → P2 June 2018 Q11, which covers all three). Numbers from the new benchmark `eval/practice_search_eval.py`, before → after: described questions found in the top 5 **1% → 100%**; the top result covers every requested topic **27% → 95%**; has both requested skills **48% → 93%**; the old practice eval is unchanged. Details: `docs/rag-chatbot-plan.md` (Status).
- [ ] **Try 5 niche requests of your own and note any misses here**: a remembered scenario ("the one with the roller coaster"), a topic mix ("vectors and proof"), a skill mix ("integration by parts and the trapezium rule"). Run `.venv/bin/python -m chatbot.web` and open http://127.0.0.1:8765.
- [ ] **Vague topic words are guesses:** "functions", "modelling" and "graphs" can mean several topics. "modelling" counts exponential models, modelling in context *and* mechanics modelling. Say if a mix involving one of these gives the wrong kind of question.
- [ ] **When no question covers everything,** the list shows the best partial matches, labelled "covers 2 of 3: …". Check that's more useful to you than "no question has all of these".
- [ ] **Described questions ignore the spec order:** the question that matches your description comes first even if it's IAL or pre-2017 (the old rule "9MA0 first" still applies to technique requests). Check you're happy with this.
- [ ] **A single topic name now means the whole topic:** "a question on vectors" draws on every Vectors skill (before, it picked the one skill "suvat with i-j vectors"). "Differentiation" means basic plus implicit/parametric differentiation. Check the mix looks right.
- [ ] **New filters:** a year ("a 2019 question on vectors", "from 2022") and a qualification ("an IAL question on moments", "from the old spec") narrow the results. Try one or two.
- [ ] **More messages count as practice requests** ("can you find a question that…", "is there a question combining…", "I'm looking for a question…"). Follow-ups about the open question ("how do I find x in this question") are checked not to match, but tell me if a follow-up ever gets a question list instead of an answer.
- [ ] **Multi-skill requests using long skill titles** that contain "and" (e.g. "separate the variables and integrate and form a differential equation") are the weakest case: 89% on the held-out half. Short everyday names work better.
- [ ] **Optional live check not run:** `.venv/bin/python -m eval.chat_smoke` (~$0.50 of API calls). Run it or ask me to.

## 26. Tutor speed: question shown first (added 2026-09-27)
- [x] **Opening a question used to show nothing for ~30–60 s** (measured: ~3 s starting Claude Code + ~33 s writing the explanation). The web UI now shows the question at once (0.1 s) with a timer, and the explanation appears below it when it's ready. The total time is the same. The terminal chat is unchanged.
- [ ] **Try it:** open a question (e.g. "2024 paper 2 question 1" → yes). The question should appear straight away with "Writing the explanation… (N s)". Say if the wait message or layout should change.
- [ ] **Later speed-ups, not done yet** (details in `docs/rag-chatbot-plan.md` Phase 7): cache explanations so reopening is instant; test a lower thinking budget (~$1 test); generate part (a) first. Say when you want these.
- [ ] **Old bug found, not fixed:** `--dry-run` mode crashes when opening a multi-part question (the recommendations look up a part that doesn't exist). Live and offline modes are unaffected. Say if you want it fixed.

## 27. Commercial clean-room relaunch (added 2026-09-29, branch `commercial-clean-room`)
- [ ] **Make the GitHub repo private now:** it's public and publishes Pearson questions, mark schemes and examiner quotes plus 8 AQA PDFs. GitHub → your repo → Settings → General → Danger Zone → Change visibility → Private.
- [ ] **Approve the history clean-up** (backup, then `git filter-repo` to remove `data/processed`, the AQA PDFs and the real-question topic pages from every commit). It rewrites history, so the next session will ask first.
- [ ] **Check your employment contract** for intellectual-property and side-business clauses before selling anything.
- [ ] **Book a fixed-fee UK IP solicitor review** before launch. The questions to ask are in `docs/commercial-relaunch-plan.md` §9.
- [ ] **Pick a product name** without "Edexcel" or "Pearson", and check the domain is free.

## 28. Clean-room Phase 1 foundations (added 2026-09-29, branch `commercial-clean-room`)
What was built and how to run it: `docs/clean-room-pipeline.md`.
- [ ] **Review the seed error-code list** `content/error_codes.json`: 267 codes, each a one-line definition in my own words, the skill groups it applies to, and the mark type usually lost (M/A/B). I wrote it from general maths-teaching knowledge, not from the examiner reports. Delete, merge, reword or add codes. Your changes make it your list.
- [ ] **Mark the match samples** in `data/clean_private/error_match_samples.md` (private: it contains Pearson note text, so never commit it or paste it into an AI chat). Tick ✓ or ✗ for about 15 notes per score band. Your ticks set the match threshold, which is 0.70 for now: 46% of 10,605 pitfall notes match at 0.70, 72% at 0.65, 19% at 0.75. Until then, treat the frequencies as rough: some general codes absorb a lot of notes (`wrong-final-accuracy` 1,140, `rationalising-error` 365).
- [ ] **Read the unmatched clusters** (bottom of the same file: 60 clusters, 4 sample notes each). Where a cluster is a real, recurring mistake, write a new code in your own words in `content/error_codes.json`, then rerun `.venv/bin/python scripts/clean/match_errors.py --samples`.
- [ ] **Approve the stock-phrase whitelist** `content/novelty_whitelist.json` (25 commonplace phrases, e.g. "the coefficient of friction between"). The copy detector doesn't count these as copying. Keep entries generic, with no scenario words. I deliberately left Pearson's calculator rubric off, because the product must word that in its own way.
- [ ] **Approve a change to the copy-detector rule (G7)**, made on measured evidence. The plan rejected any item with embedding similarity > 0.85. But my three from-scratch test questions scored 0.84–0.92, because similarity measures *topic*, not copying. Copies and number-changed variants are caught anyway by shared 8-word runs (40/40 each; variants share at least 5 and typically 95). High similarity now **rejects** only when the item also has the same marks per part as that real question, or when it is above 0.97. Otherwise it **flags** the item for your review, first in the queue.
- [ ] **Check the three test questions** in `eval/fixtures/original_items.json`: a stationary-points cubic, a binomial test, and a table-and-pulley question. They are the item-format examples and the "must pass" controls. Are they fair, authentic-looking questions with correct mark schemes?
- [ ] **Taxonomy text check** (copied to `content/clean/tags.json` for the product). An 8-word overlap scan against every Pearson question, mark scheme and note found 7 hits, all standard formulae (circle equation, arithmetic-series term, sector area, compound angles). Confirm the skill descriptions and question-type definitions are your own words. Also check whether the technique title "Use the substitution x = a sin² θ" is a generic method name or one exam's wording.
- [ ] **Technique write-ups:** one (`check-log-equation-roots-for-validity`) shares a maths expression with a real question. Check that no technique's worked example reuses a real paper's numbers before shipping it.
- [ ] **Firewall record (provenance evidence).** During the repo audit and while building the mark-code regex, this session showed about 6 mark-scheme excerpts and about 25 short overlapping phrases in its working context. No examiner notes were read in full. The error codes and test questions were written afterwards, from general knowledge, and the scans above show no copied text. From now on, clean-side sessions work only with ids, counts and codes, and never print Pearson text.
- [ ] **Add to the history purge (when you approve it)** these tracked files that also contain Pearson text: `units.json` (full question and mark-scheme text), `notebooks/explore_kb.ipynb` (saved outputs), `docs/examiner-notes-review.md`, `docs/ms-audit-report.md`. About ten other docs each hold one or two short phrases; I'll reword those on this branch instead. The schema and taxonomy now also live in `content/`, so the purge won't lose them.
- [ ] **Mark-code sequences:** 7,030 of 7,055 parts give a sequence that adds up exactly to the part's marks and has a sensible M-before-A order. 17 add up but look irregular; 8 couldn't be resolved. Nothing to do unless you want those 25 checked.
- [ ] **Reminder: the repo is still public** (§27, first item). Nothing from this branch has been pushed.
- [ ] **Check the new bank targets** (handoff §5.3, set 2026-09-30 from your request). They mirror current 9MA0 papers: 18% of real questions are short one-topic, 15% longer one-topic, 29% combine two topics, 38% three or more. The plan is ~600 exam-style questions in that mix (pure ~420, stats ~90, mech ~90), 6 fresh mock papers, and ~490 short skill drills (2 per skill). Say if you want more or fewer drills, or a heavier tilt towards multi-topic questions than the real papers have.

## 13. Practice lookup (fixed 2026-09-26, from your testing)
- [x] **"Give me a question on X" ignored the skill tags.** It matched question wording only, so "2nd derivative test" opened a question without one, and "normal-distribution hypothesis testing" gave a binomial test. It now uses the tags: only questions **tagged** with the requested skill are suggested, opened at that part. It understands "not a binomial" and "stats/mechanics" hints, never re-suggests a question you've already opened, and lists current 9MA0 questions first. Checked by `eval/practice_eval.py`: **226 skills, 100% of suggestions tagged with the requested skill** (1085/1089), plus your two conversations as regression tests.
- [ ] **Skill titles vs everyday names:** some skill titles don't use students' words (e.g. "Determine the nature of a stationary point" = the second-derivative test). The search now also uses each skill's short name. If a request still maps to the wrong skill, note the wording here.
- [ ] **Hypothesis tests are tagged mostly on the "state hypotheses" part**, so the suggestion opens at that part. Check this is where you'd want a student to start.
- [ ] **Retrieval results changed with the new Stats/Mech/IAL data** (`python -m eval.retrieval`): pasted-question matching is now 25/30 confident + 5 confirm, 0 wrong (was 27+3). `P3_June2022_stats…` has no same-type partner question. That's worth a look by the session that added the data.
