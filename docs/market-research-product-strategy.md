# Market research and product recommendation (30 Sept 2026)

*Research run on 30 Sept 2026 across six parallel sweeps: consumer competitors, AI marking and AI tutors, student demand, schools and tutors, scalability across boards and subjects, and a deep-dive on the closest AI-first rivals. About 30 products were examined; roughly 200 pages were read. Every figure below was read on a vendor, regulator or exam-board page unless marked* (inferred) *or* (snippet) *for search-snippet-only evidence. This is research, not legal advice. Companion documents: `handover-product.md` (current build), `handoff-clean-room.md` (design and firewall), `commercial-relaunch-plan.md` (earlier legal and market research).*

---

## 1. The answer in one page

**The gap is not "AI marks my working". It is "nobody teaches students how marking works."**

Since the earlier research (29–30 Sept), the picture has moved. AI marking of maths working against a scheme is now a checkbox feature: Maths Genie does it **free** on real 9MA0 papers, ExamSolutions sells it for £89.99 a year, alevelmathsrevision.com for £9.99 a month, Medly for £24.99 a month, and MarkIt and GradeOrbit sell it to teachers. All of them are criticised for the same things: vague or inaccurate marking, and "mark schemes that don't match". None publishes an accuracy figure. None explains *why* a mark was lost in terms a student can reuse. None teaches the conventions (M1, A1, dM1, ft, cso, awrt, isw) as a skill. And none finds practice at skill level inside multi-topic questions.

Across about 30 products, **not one teaches mark-scheme literacy as a core, assessed feature**. It exists only as blog posts and a Pearson FAQ for teachers. Meanwhile the most-asked maths question on The Student Room for 15 years is some version of "what do M1 and A1 mean, and do I get full marks with half the working?", and the hardest questions on 9MA0 are the multi-skill ones (mean 1.9/9 on 2022 P1 Q16), not the hardest single topics.

**Recommended product: an "examiner literacy" trainer for Pearson Edexcel A Level Maths**, positioned as *"learn to write answers the way examiners mark them"*, in which AI marking is the measuring instrument, not the headline. Its five parts, in priority order:

1. **Be the examiner.** The student marks a scripted answer against our scheme, mark by mark, then sees the verdict and the reason. This is the feature nobody has. It costs nothing per use (no model call), it teaches the conventions directly, it produces calibration data, and we already generate 4–6 scripted answers with designed mark vectors per item for gate G4.
2. **Mark my working, explained.** Per-mark decision, quoted evidence from the student's own line, the convention that applied, and the one-line rewrite that would have secured the mark ("state the method line before substituting, and dM1 is safe even if the arithmetic fails"). Published accuracy figures, which nobody else publishes.
3. **Mark-leakage profile.** Tracking by *mark type* and *error code*, not only by topic: "you lose A marks to accuracy and final-form errors, not M marks; you lost 11 marks this month to premature rounding and missing conclusions." No competitor tracks by mark type. Our 267-code error taxonomy and the frequencies mined from 10,605 examiner pitfall notes make this credible from day one.
4. **Playbooks for the 73 question types.** For each type: how it is normally structured, the usual mark pattern, where the marks leak, and the pitfalls with the question's own numbers. Facts-only content derived from the knowledge base; cheap to produce; strong for search traffic.
5. **The synoptic practice finder.** Original exam-style questions in the measured 9MA0 mix (18% short single-topic, 15% long single-topic, 29% two-topic, 38% three-plus), tagged at skill level, with ladders from drill to exam. Solves the "I've run out of past papers" and "teacher keeps sending questions I've done" complaints from strong students.

**Go to market:** direct to students and tutors first at about £8–10 a month, £49–59 a year, or a £39 exam-season pass; a free daily "Be the examiner" question as the top of the funnel; free teacher accounts that create classes, converting to £600–900 department licences in the spring 2027 budget round. Say loudly that the bank is 100% original with no exam-board text: every rival either hosts Pearson papers without a stated licence or ships AI-generated schemes that students call inaccurate.

**Scale:** 8MA0 AS is a free subset; Edexcel Further Maths and Edexcel IAL come next (same board, same notation, same legal posture); OCR before AQA, because AQA explicitly bans using any of its material to train AI. Design the mark-code ontology and a board profile now so those are configuration, not rewrites.

The rest of this document gives the evidence.

---

## 2. What students need (evidence)

### 2.1 Top five unmet needs, ranked by how often and how intensely they appear

| # | Need, in the students' words | Evidence |
|---|---|---|
| 1 | "Tell me exactly which line earns which mark." | TSR threads asking what M1/A1/B1/dM1/ft/cao/cso mean recur from 2009 to 2025; students argue with each other because nobody has a reliable model ("A = accuracy, M = method, B = no idea!"). Examiner-report themes every year: missing conclusions on "show that", calculator-only answers scoring zero, decimals where exact was required, units omitted. |
| 2 | "I know the maths but I can't start the question." | Exam-day reactions to 2024 P1 ("harder compared to all past papers I did", "nothing was working"). The lowest-scoring 9MA0 questions are the multi-skill ones: 2022 P1 Q16 (parametrics + differentiation + integration) mean 1.9/9; 2019 P1 Q10 (proof) mean 1.7/6. |
| 3 | "Mark my working like a real examiner would." | Students already paste working into ChatGPT to mark it; 72% of surveyed students say AI is usually wrong at maths (Warwick); existing markers are called vague, strict or scheme-mismatched (MarkMe, Medly, Save My Exams reviews). |
| 4 | "Where do I lose the last two or three marks?" | Rounding and accuracy anxiety, show-that conclusions, notation. Amplified by grade boundaries: A* was 254/300 in 2026 and 258 in 2025, so there is almost no slack. |
| 5 | "I've run out of real past papers." | Only about eight real 9MA0 sittings exist (no 2020/21). Strong students say Maths Genie is "not the most exam-style accurate" and MadAsMaths "more challenging than they would be in exams"; teachers resend questions already done. |

### 2.2 The audience and its money

| Fact | Value | Source |
|---|---|---|
| UK A Level Maths entries | 107,427 (2024), ~112,000 (2025), 115,380 (2026) | JCQ, MEI |
| Pearson share of A Level Maths certificates (England, 2024–25) | 72.4% (73,010 certificates), up from 70.5% | Ofqual market report |
| 9MA0 as a share of all A Level certificates | 9.1%, the largest single A Level qualification in England | Ofqual |
| A*/A share | ~42% | Ofqual |
| AS Maths (8MA0) entries | ~17,000, flat | JCQ |
| Further Maths entries | 21,032 (2026), +7–8% a year; Pearson share 69.8% | JCQ, Ofqual |
| Tutoring | £26–70 an hour online; 20–25 sessions a year is typical, so £900–1,800 | MyTutor, Tutorful, thetutor.link |
| Easter courses | £95–345 (PMT), £490–1,350 (colleges) | vendor pages |
| Subscription tolerance | £4–15 a month is accepted; £18–20 a month called "absurd" in reviews | Trustpilot reviews of Save My Exams, MarkMe |
| AI use | 93% of UK GCSE/A Level students have used AI for revision; 87% use ChatGPT; 70% weekly (snippet, Save My Exams survey of 1,533) | Save My Exams |
| Seasonality* | Peak Feb–June; a secondary bump for mocks Nov–Jan | inferred from course dates and forum activity |

Channels that reach them: YouTube explainers (TLMaths 153k subscribers, Bicen Maths ~117k), The Student Room search traffic on mark-scheme questions, teachers' resource lists, and tutors who need something to set between sessions. TikTok has no dominant A Level maths account.

---

## 3. The competitive landscape

### 3.1 Consumer products for A Level Maths

| Product | Price | Questions | AI marking of maths working | Teaches how marks work | Skill-level finder | Traction / complaints |
|---|---|---|---|---|---|---|
| **Save My Exams** | £12/mo, £30/qtr, £48/yr | Own-written plus hosted real papers ("used with permission") | Smart Mark "does not mark MCQ or calculation questions"; A Level Smart Mark is AQA sciences and psychology only | No | Topic-level target tests | Trustpilot 4.6 (2,008). Complaints: AI slow/inaccurate, price tiers |
| **Maths Genie** (free) | Free | Real Edexcel 9MA0 papers 2018–2025 | **Yes, free**: "write your working straight onto the paper and Genie marks it question by question against the mark scheme" | A GCSE blog post on M/A/B marks only | No | "1m+ students, 4,000+ schools" (self-reported) |
| **ExamSolutions (Axi)** | Free 5 markings/mo; £14.99/mo; £89.99/yr | Real past papers plus own | "Marks your working like an examiner, shows exactly where marks were lost" | No | "Learns what you find hard" | Trustpilot 3.4 (29): access failures, "as helpful as ChatGPT" |
| **alevelmathsrevision.com (Ultimate Study Tool)** | £9.99/mo, £49.99/6mo, £83.99/yr | Own exam-style; real papers on the free side | Yes, handwritten, "against real A-Level mark schemes", marks won/lost with method/accuracy-flavoured comments | Partial (output only) | Topic-level mastered/shaky | No reviews of the paid tool found |
| **Medly AI** | £24.99/mo, £180/yr | Own, 6,000+; disclaims board involvement | Yes, handwriting canvas; own GCSE benchmark (examiner-level agreement with a generic prompt) | No | Adaptive engine | "400,000+ students"; Trustpilot 4.2 (416). Top complaints: marking "not very accurate", "inaccurate mark schemes", price |
| **Revision Genie** | £14.99/mo or £71.88 once | Own | "Scribble your working… shows you every mark" earned or missed | No | Adaptive | 150k learners, 1,500 schools (self-reported) |
| **Up Learn** | £74.99/mo or £319.99 to 2027; Master £419.99 | Own | AI diagnostics; Master tier adds two papers marked by human examiners | No (help docs never mention mark schemes) | Adaptive path | Trustpilot 4.3 (912): "regurgitating", "not ready for real exam demands", guarantee needs 90% Up Score |
| **Seneca** | ~£9.99–19.99/mo (conflicting); guarantee add-on £5.99 | Own "by examiners and teachers" | AI-marked free text; maths depth undocumented | No | Smart learning mode | Trustpilot 4.1 (688): errors, A Level maths "light" |
| **MME Revise** | Papers £20–25; Premium £29/mo or £149/yr | Own predicted papers | Long-form only | No | No | Trustpilot 2.0 (38): papers "too easy", "copy-pasted", schemes "almost useless" |
| **MasteryMind** | £9.99 / £14.99 | Unspecified | "Suggested marks", photo on Premium | No | Spaced repetition | Small |
| **Study Rocket/Adapt, Study Mind, Cognito, Revisely, MyEdSpace, Bicen membership, TLMaths** | £9.99–80/mo | Mixed | None for maths working | No (walkthroughs at best) | No | — |
| **Pearson** | Revise Online £2.50/mo (GCSE only) | Own | AI Exam Practice Assistant is GCSE History, Languages, AQA English Language only (Amazon Bedrock, May 2025) | No | No | No A Level maths AI product |
| **Tutopiya "AI Buddy"** (Singapore) | Undisclosed | Unspecified | Claims "mark scheme matching based on actual Edexcel marking schemes" and "examiner report insights" | No | No | Targets UAE, South Asia, UK. Probably built on Pearson text* |

### 3.2 Teacher-facing markers and school products

| Product | Price | What it does |
|---|---|---|
| **MarkIt** | Free 10 papers/mo; £5.99/30; £24.99/150 credits | Marks scanned scripts with M1/A1/ft against uploaded schemes; "98.6% within ±1 mark" of teacher marks; nothing reaches students until the teacher releases it |
| **GradeOrbit** | Teachers £50–250/yr; students £5–25/mo in credits | Same model with a per-mark tick/cross and rationale; "We don't auto-mark. We assist." Has a student upload mode (bring your own scheme) |
| **marking.ai, Excelas ExamGPT (GCSE only), Top Marks (essays)** | School licences | Criterion-level marking for teachers |
| **Dr Frost** | £650 + VAT per school (charity); free to individuals; tutors pay the school rate | Skill-tagged bank of real board questions, auto-marks final answers, not working |
| **Integral (MEI)** | Portal pricing; ~£30 per extra student; individuals ~£75/yr | Teaching content and self-marking tests |
| **Exampro (AQA)** | £215/yr for A Level Maths | Real questions, schemes, examiner commentary, auto-marked tests. **AQA only. There is no Edexcel equivalent.** |
| **Pearson Mocks Service** | £15–16 per A Level paper per student | Pearson examiners mark real mocks; item-level analysis in ResultsPlus. A class of 20 × 3 papers ≈ £900–960 a sitting |
| **Pinpoint Learning** | £500/school | Question-level analysis of mocks into personalised booklets (mainly GCSE) |
| **Seneca Sync / Premium AI+** | Free 12 months, then £646 | Generic across subjects |
| **Up Learn schools** | Quote | Claims 685+ schools |
| **Pearson ActiveLearn** | Tiered | Retires 31 Dec 2026 (snippet): a churn moment for departments |

Not A Level: Sparx, Century, GCSEPod, Third Space, Smartgrade.

### 3.3 What is and is not a gap

| Claimed differentiator in the current plan | Status after research |
|---|---|
| Mark-by-mark explanations in Edexcel style | **Open.** No product teaches the conventions or explains a lost mark in reusable terms. |
| Question-specific pitfalls with the question's own numbers | **Open.** Nobody tags recurring pitfalls; "examiner tips" where they exist are generic. |
| Skill-level finder over multi-topic questions, ladders, "hardest part" | **Open.** All adaptive systems work at topic level; Dr Frost skill-tags but is a bank, not a finder for synoptic questions. |
| AI "mark my working" | **Commodity.** Free at Maths Genie on real papers; £90–300 a year elsewhere. Only the *explanation*, *calibration* and *what it feeds* can differentiate. |
| Bank in the 9MA0 mix with mocks | **Partly open.** Rivals have banks, but MME's "too easy, copy-pasted" reviews and Medly's "inaccurate mark schemes" show fidelity is the hard part, and our gates are built for exactly that. |
| Legally clean, no exam-board text | **Open as a message.** No consumer product claims a Pearson licence; most host papers under unstated norms; Medly disclaims. A vendor that can say "100% original" is unusual, and Pearson has litigated over reproduced question text (Chegg, settled Dec 2024). |

### 3.4 The real substitute is free general AI

A student can photograph their working and the PMT mark scheme and ask ChatGPT. Study modes (ChatGPT Study Mode, Gemini Guided Learning, Claude Learning Mode, all since July–August 2025) guide but do not grade against board schemes. The research is clear that a frontier model handed the official scheme already agrees with examiners about as well as examiners agree with each other on GCSE maths (Medly benchmark, June 2026: quadratic weighted kappa 0.86 vs 0.84 examiner-to-examiner, with a generic prompt). So the marker itself is not a moat.

What ChatGPT cannot easily replicate: (1) a fresh question the student has never seen with a scheme the student does not have; (2) a marker calibrated on A Level multi-step items with published agreement figures; (3) first-party data on where A Level students actually lose marks, by skill and error code; (4) the conventions taught explicitly; (5) the workflow (handwriting-first, timed mocks, mark-type trends).

### 3.5 Regulators and boards

- **Ofqual (14 Jan 2026):** AI as sole marker does not comply with its rules; AI is acceptable for quality assurance and marker training; per-mark decisions must be explainable. Boards are years from student-facing marking, so the gap stays open. Cambridge International uses AI-assisted marking only for digital mocks; AQA and King's College London are building an examiner *assistant* for essays; Pearson has announced nothing.
- **Pearson:** copyright reserved, no AI clause, open non-exclusive endorsement policy (v1.9, June 2026) that forbids claiming official status or "examiner tips". Lowest hostility of any board to an independent original-question vendor.
- **AQA:** explicitly bans using any AQA material, including papers and schemes, to train AI. Highest hostility.
- **OCR:** no AI clause, open fee-based endorsement.
- **Research on marking reliability:** 87% of residual errors in handwritten-maths grading are transcription failures, not rubric misapplication (arXiv 2605.19043); strict rubric prompting over-penalises partial reasoning (arXiv 2607.01247); structured and numerical items are gradable, essays are not (arXiv 2603.14732).

---

## 4. The recommended product

### 4.1 Positioning

**Name the category, not the feature.** Rivals sell "AI marking". We sell **examiner literacy**: *learn to write answers the way examiners mark them, then prove it on questions you've never seen.* The line "Stop losing marks you already know how to get" tests well against the evidence in §2.

Working strapline for the footer: "Built for Pearson Edexcel A Level Mathematics (9MA0) · Independent: not affiliated with, endorsed or licensed by Pearson · Every question and mark scheme is our own."

### 4.2 Features, in build order

| # | Feature | Why it wins | What we already have |
|---|---|---|---|
| 1 | **Be the examiner.** Show a scripted answer to one of our questions; the student awards or withholds each mark with a reason; reveal our verdict, the convention, and the mark-scheme grammar ("this is a dM1: it depends on the M1 above, so once the method was wrong this mark was gone"). Daily free question as the funnel. | Unique in the market; zero model cost per use; teaches conventions directly; builds a calibration set from thousands of student judgements. MarkScheme.app proves demand for "think like an examiner" even as a manual tool. | The G4 gate already generates 4–6 scripted answers per item with designed mark vectors, stored under `gate_results.G4.responses`. Turn them into content. |
| 2 | **Mark my working, explained.** Photo or typed; transcription as a separate, visible step with a confidence check ("is this what you wrote?"); sympy equivalence before any model judgement; per-mark decision with the quoted line, the convention applied, and the rewrite that would have earned it. Publish agreement figures against human second-marking. | Turns a commodity into a teaching tool; addresses the "vague / strict / mismatched" complaints; published calibration is a trust signal nobody else offers. | `gate_marking.MARKER_SYSTEM`, the stored G4 scripts as unit tests, the sympy check library from G2. |
| 3 | **Mark-leakage profile.** Track lost marks by mark type (M, A, B, dM, ft) and by error code, per skill, over time. "You don't lose method marks. You lose 60% of your dropped marks to final-form and accuracy errors." Suggest drills by error code. | Nobody tracks by mark type. Directly answers need #4 (§2.1). Becomes the first-party data moat. | 267-code error taxonomy; frequencies from 10,605 examiner pitfall notes (4,882 matched, 224 codes with counts); `loses` field on each code. |
| 4 | **Question-type playbooks (73).** One page per type: structure, usual mark pattern, where marks leak, worked example, pitfalls. Many pages free for search traffic; full set for subscribers. | Cheap, facts-only content that captures the TSR search intent ("show that question marks", "what does cso mean"). | 73 question-type definitions, code-pattern frequencies (e.g. "M1 A1" in 1,223 parts), per-type mark distributions in `aggregates.json`. |
| 5 | **Synoptic practice finder and ladders.** By skill, skill combination, description, or "the part I found hardest"; exam-style questions in the measured 9MA0 mix; six full mocks with a per-skill and per-mark-type breakdown mapped to the latest grade boundaries. | Answers needs #2 and #5. Fidelity is guaranteed by the gates rather than by hope, which is where MME and Medly fall down. | The finder, ladders and `split_concepts` engine; 601 exam and 452 drill blueprints; 84 mock questions; bank-level mix check (TVD < 0.15). |
| 6 | **Past-paper map (facts only).** "Find a real 2023 question on implicit differentiation" opens Pearson's own page; we show the skills, marks and difficulty tier. | Keeps the free ecosystem's strength (real papers) without hosting a word of Pearson text. | Skill tags and performance facts on 2,702 questions, 7,055 parts. Needs solicitor question 4 (database right). |
| 7 | **Bring your own question.** Estimated marks, process then delete. | Requested in every AI-tutor review; keep it behind terms. | Existing new-question path. |
| 8 | **Teacher and tutor layer.** Class creation, set by skill or mini-mock, photo submission, M/A/B lines with teacher override, class heatmap by skill and error code, CSV export, printable set plus our scheme. | Converts free teacher use into department licences; fills the "Exampro for Edexcel" hole. | Everything above plus a dashboard. |

### 4.3 How this makes the best use of the data we hold

The Pearson knowledge base cannot ship, but its *facts* are the most valuable asset in the project and nobody else has them at this granularity:

- **Error frequencies by code and skill** (from 21,764 examiner notes) drive the "common" labels on pitfalls, the drill recommendations, and the mark-leakage categories. This is the moat until first-party student data overtakes it.
- **Skill co-occurrence** (2,375 skill pairs, 341 group pairs) is what makes the synoptic blueprints realistic rather than random, and what powers "a question that combines integration and parametric equations".
- **Mark-code patterns per skill and per question type** teach the grammar of schemes ("integration by parts is almost always M1 A1 then dM1 A1") and let the marker predict the code sequence for a new question.
- **Question performance on 1,052 questions** calibrates difficulty tiers and ladders.
- **The 246-skill taxonomy and 73 question types** are the spine of the finder, the playbooks and the leakage profile.
- **The 9MA0 mix** keeps the bank honest against the "too easy" failure mode.

Two things the current plan should change to exploit this: store the G4 scripted answers as first-class content (they are the "Be the examiner" exercises), and add mark type and error code to every marking event so the leakage profile exists from the first user.

### 4.4 Pricing and packaging

| Tier | Price | Notes |
|---|---|---|
| Free | £0 | Daily "Be the examiner" question; a handful of playbooks; 3 markings a month; past-paper map |
| Student | **£8.99/mo, £54.99/yr** | Everything, unlimited marking within fair use. Sits between Save My Exams (£4/mo annual) and Medly (£24.99). Below the £18–20 "absurd" line. |
| Exam-season pass | **£39** for Feb–June | Matches the spending peak and the parent's mental comparison (one tutoring hour) |
| Tutor | **£19/mo** for up to 15 tutees | No rival has a tutor tier; Dr Frost charges tutors the £650 school rate |
| Department | **£600–900/yr**, capped seats plus £4–6 per extra student | Anchors: Dr Frost £650, Seneca £646, Pinpoint £500. Value line: one Pearson-marked mock set for 20 students costs £900–960 per sitting |

Model cost per marking is roughly £0.05–0.15 today, so a heavy student at 60 markings a month costs about £6; cache explanations, use sympy before any model call, and rate-limit fair use.

### 4.5 Go to market

1. **Free top of funnel with zero marginal cost:** the daily "Be the examiner" question and the playbooks (search terms like "what does dM1 mean", "show that question marks", "cso vs cao").
2. **YouTube shorts** in the "why you lost this mark" format; approach TLMaths and Bicen Maths for a collaboration once the free tool exists.
3. **Tutors** as the second channel: about 1,800 A Level maths tutors on MyTutor alone, none with a tool for setting marked work between sessions.
4. **Teachers** get free accounts from launch; conversions happen in the spring 2027 budget round. Arrive with a DPIA, a data processing agreement, UK hosting, "no training on pupil data", and a mapping to the DfE's 13 generative-AI product safety standards. The ICO's September 2026 audit found 70% of edtech data agreements deficient, so a clean pack is a selling point.
5. **Proof:** publish marker agreement figures, and collect reviews from the free pilot of about 100 students. That is already more public proof than alevelmathsrevision.com's paid tool shows.

### 4.6 What to stop or change in the current plan

- **Don't call the flagship "mark my working".** Build it, but lead with examiner literacy and the leakage profile.
- **Elevate "Be the examiner"** from nothing to feature #1. It is the cheapest and most distinctive thing we can ship.
- **Separate transcription from marking** and show the transcript to the student before marking. The research says transcription is the dominant error source.
- **Prompt the marker for partial credit** and follow-through explicitly; strict rubric prompting over-penalises.
- **Publish accuracy.** Second-mark a sample of real pilot scripts by hand and publish the agreement figure with its method.
- **Add mark type and error code to every marking event** so the leakage profile is populated from the first user.
- **Keep the fidelity gates.** The two failure modes that sink rivals (too-easy questions, schemes that do not match) are exactly what G1–G8 and human review exist to prevent.

---

## 5. Scaling to other qualifications and subjects

### 5.1 Recommended order

| Step | Qualification | Why | What changes |
|---|---|---|---|
| 1 | **8MA0 AS Maths** | Same papers' subset; ~17k entries; zero notation or legal change | Blueprint subset only |
| 2 | **9FM0 Edexcel Further Maths** | 21k entries growing 7–8% a year; Pearson has 70%; identical scheme; weak interactive competition | New taxonomy (Core Pure plus options); sympy already covers matrices, complex numbers, hyperbolics |
| 3 | **Edexcel IAL Maths** | Same board, notation and legal posture; three series a year; at least 16k full-A Level sits in the June series alone, before AS and unit entries; high-spend international schools; thin free competition. **Best size-to-effort ratio of any expansion.** | Unit-paper blueprints (75 marks); ~10–15% taxonomy change in statistics |
| 4 | **OCR A and OCR MEI** | 13k certificates; DfE content is common so the taxonomy is reused; no AI clause | Board profile: E marks, dep*, FT, comprehension paper |
| 5 | **AQA A Level Maths** | 14.6k certificates; adds R and E marks | **Only after a legal answer on AQA's no-AI-training clause.** Facts would have to come from human-written summaries or a licence. |
| 6 | **Edexcel GCSE Maths Higher (1MA1)** | 542k Pearson certificates, by far the biggest prize | Saturated by Sparx and Dr Frost; the only wedge is examiner-grade marking of working. Adds P and C mark types and tiering |
| 7 | **A Level Physics (Edexcel 9PH0 first)** | 45.8k entries, but AQA has 55% and Pearson 11% | New MARKING_POINT code type, unit and significant-figure penalty engine, ecf, levels-of-response for 6-markers |
| 8 | **Chemistry, then Economics** | Chemistry needs equation balancing; Economics is levels-based so the proposition weakens | Rubric-band judging, where the research says AI validity is poor |

Where the proposition transfers cleanly: every A Level maths board, Further Maths, IAL, GCSE maths. Where it holds with work: physics and chemistry calculations. Where it weakens: extended-response science items and all levels-based humanities.

### 5.2 Design now so expansion is configuration

- **A canonical mark-code ontology** with per-board rendering: METHOD, ACCURACY, INDEPENDENT, DEPENDENT_METHOD (with an explicit antecedent), FOLLOW_THROUGH, REASONING, EXPLANATION, PROCESS, COMMUNICATION, MARKING_POINT, LEVEL_BAND. Items store the canonical code; the board profile renders "dM1", "M1 dep*" or "(1)".
- **A board profile object:** notation renderer, dependency semantics, follow-through rules, accuracy conventions (cao, awrt, isw, cso), unit and significant-figure penalties, show-that rules, bald-answer policy, paper blueprint, and a legal profile (may learn facts, may quote, AI-training prohibited, endorsement route).
- **A skill taxonomy keyed to content**, with per-board specification aliases and a subject axis.
- **Pluggable verifier gates:** sympy equivalence, numerics with units and significant figures, equation balancing, rubric-band judging; the item's answer type selects the gate.
- **A marker contract:** per-mark decision, quoted evidence, confidence; transcription as its own stage with its own confidence.
- **A series field** in the fact store now, because IAL and IGCSE sit in January, June and October.

---

## 6. Risks and honest caveats

- **Medly or Save My Exams add the pedagogy.** Medly has $8m of fresh funding (Aug 2026), a DfE pilot, 90,000 monthly actives and a published GCSE benchmark, and it shipped dependent marking and photo upload in the last week of September; Save My Exams has the audience and could lift its "no calculation questions" restriction. Our defence is speed on the distinctive features, Edexcel-only depth, the error-frequency data, and published per-mark calibration. See §7.
- **Free general AI keeps improving.** It will always be able to mark a real past paper with a public scheme. It cannot mark a question it has never seen against a scheme it does not have, and it does not teach.
- **Content fidelity.** Reviews of MME and Medly show that generated banks fail on realism and scheme accuracy. Our gates and human review are the answer, and they cost about $1.60 per passing item today, so roughly $1,200–1,800 for the remaining bank.
- **A solo founder's time.** Review minutes per item, measured in the pilot, decide the calendar more than money does.
- **Legal.** Solicitor questions 1–7 in `commercial-relaunch-plan.md` §9 stand, plus one new one: the Pearson endorsement policy forbids implying "examiner tips" or official status, so if endorsement is ever sought the "examiner literacy" language must be framed as our own teaching about a public marking system.
- **Profit expectations** stay as before: £0–2k a month in year one, £5–15k a month by years two or three if it works. The direct-to-student market is seasonal; the tutor and department tiers smooth it.

---

## 7. Deep-dive: Medly AI, MarkIt, GradeOrbit, Tutopiya

### 7.1 Medly AI: the competitor to watch

| Aspect | Finding |
|---|---|
| Company | Medly AI Limited (no. 15110302), incorporated Sept 2023 by two ex-NHS doctors. Seed £1.7m (Eka Ventures, Ada Ventures, Feb 2025), then **$8m seed led by Felix Capital, 18–19 Aug 2026**, plus a ~£300k government contract. Selected (8 of 53 bids) for the DfE / i.AI "AI Tutoring Tools Pioneer Programme", July 2026: a research contract, not an endorsement. |
| Traction | Self-reported "400,000+ students", "90,000 active users every month", 38 minutes a day. App Store 4.7 (4.9k ratings), Trustpilot 4.2 (416). Independent randomised trial exists for **GCSE science only** (644 completers, effect size 0.33). |
| Product for A Level Maths | Handwriting canvas and typed input; **photo answers added 24 Sept 2026**; "instant AI marking based on exam style mark schemes" with a marks breakdown and per-answer annotation; changelog shows "improved recognition of working and method marks" (Dec 2025), proof marking tightened after marking proofs "too generously" (Nov 2025), and **"error carried forward and dependent marking for multi-part problems" (24 Sept 2026)**. An "Ask Medly" prompt offers "show me what a full-mark answer needs". |
| What is missing | **No public material uses Edexcel scheme vocabulary** (M1, A1, B1, dM1, ft, cao, cso) or shows a per-mark "why you lost this mark" tied to scheme codes. No A Level Maths accuracy evidence: the arXiv benchmark is GCSE only, on Medly's own mock items, with a single integer mark per response and two raters. Maths is its weakest subject by user consensus ("works really well for sciences, maths not so much"). Documented complaints: handwriting not recognised, "the AI didn't even have the right mark scheme" (May 2026), "questions often have no relevance to official exam board mark schemes", inconsistent re-marking (the same essay scored 27 to 35 out of 35 on resubmission in a YouTube test), off-spec content, billing failures. 21 A Level subjects across four boards and five countries, so 9MA0 depth is thin by construction. |
| Questions and copyright | "6,000+ exam-style questions" across all subjects, own-written and teacher-reviewed. Separately it **hosts official Pearson papers and mark schemes for free download and markets AI marking of them**, while disclaiming any Pearson involvement. No licence claimed. |
| Price | £24.99/month, £180/year (in-app £29.99 and £209.99). Freemium since March 2026 with a daily cap on practice and marking (reviewers say three questions a day). Free for verified UK teachers, with a homework builder that accepts uploaded papers and schemes and auto-marks with teacher override. |
| Mocks | "Medly Mocks 2026", 26–31 Oct 2026, free, 1,000 places, Maths included for AQA/Edexcel/OCR; "marks your papers like a human examiner", topic breakdown, national percentile. Earlier rounds drew complaints about off-spec content and odd marks. |
| Expansion | 30 new subjects including Further Maths (Sept 2026); IB, IGCSE, National 5; SAT live, AP and ACT planned; Australia, Malaysia, Brazil; a university product. |

**Read-across:** Medly has the money, the audience and the marking technology. It does not have the pedagogy, the Edexcel-specific depth, the error data or the legal cleanliness, and its maths reputation is poor. It will keep improving the marker, so competing on marking alone is a losing race; competing on *teaching how marking works*, on fidelity to 9MA0, on published per-mark accuracy and on a single-subject price is not.

### 7.2 MarkIt and GradeOrbit: teacher-facing, and the best code explanations in the market

- **MarkIt** (founded 2026, maths only, all boards): marks against schemes the teacher uploads; handles M1 "for any complete method that could lead to the answer", A1, B, dM1, ft "recalculating with each student's own wrong value", cao, cso, oe, isw, awrt, soi; flags unusual valid methods for the teacher. Students see nothing until a three-stage teacher release; **no direct-to-student mode**. "98.6% within ±1 mark" on an internal set with no sample size, and explicitly "not an autonomous exam-board marking claim". Runs on Google Vertex AI outside the UK. No company number or ICO number on its pages. Its terms take a perpetual licence to uploaded schemes and push copyright liability onto the uploader. Publishes a teacher-facing glossary of scheme codes, including an Edexcel A Level guide: the best public explanation of the codes we found, and search content we can outdo for students.
- **GradeOrbit** (sole trader, ICO registered, UK only): Google Cloud Vision transcription plus Gemini; awards method and answer marks independently, gate by gate, with a rationale per mark ("method mark awarded for a complete expansion; the answer mark is withheld because the like terms were never collected"). It **does have a student mode**: upload work and optionally your own scheme, £5 for 30 credits, £12 for 80, £25 for 180 a month, "not an official or certifying grade". No accuracy validation. Teacher plans £50–250 a year; schools £10 per teacher a month.

**Read-across:** GradeOrbit's per-mark rationale is the closest thing to "why this mark was withheld" and shows the format students respond to. Both tools depend on the user supplying the official scheme, which we never need because the scheme is ours.

### 7.3 Tutopiya "AI Buddy" and Save My Exams

- **Tutopiya** is a Singapore tutoring company selling a portal to international schools (Cambridge IGCSE, Edexcel IAL, IB) in Singapore, Malaysia, Hong Kong, UAE, India, Pakistan and the UK. Its Edexcel maths codes are IAL (XMA01–YMA01), not 9MA0. It claims both to mark "against the actual Edexcel mark scheme" and to offer "200,000+ AI-generated practice questions", which is inconsistent provenance. About £55 a year. Not a UK 9MA0 competitor, but a marker of how the IAL market will be fought.
- **Save My Exams** topic questions for Edexcel A Level Maths are own-written with static model answers; whether they carry M1/A1 allocations could not be verified because the pages render only via JavaScript. It also hosts Pearson papers and schemes. September 2026 reviews complain of "£18 for the lowest plan" and "£20 a month", so its pricing appears to have risen above the £12 a month recorded earlier.

### 7.4 What beats Medly for a 9MA0 student

1. **Price for one subject:** roughly £5–9 a month or £40–60 a year against £180, with the literacy content free as the hook. Medly's forum reputation is "good but overpriced, weak at maths".
2. **Depth in Edexcel's own grammar:** every lost mark explained through dM1 chains, cso in proofs, awrt, ft on "their" value, isw; plus drills on how to write to bank the method mark. Nobody does this.
3. **Trust:** publish an A Level-specific, per-mark agreement figure against experienced markers, and a consistency test (same script twice gives the same marks), which is exactly where Medly was caught out. Avoid "examiner-accurate" wording given Ofqual's January 2026 position.
4. **Fidelity:** the measured 9MA0 mix, formula-booklet awareness, calculator conventions. A specialist beats a 21-subject generalist here.
5. **Cleanliness:** "100% original questions and schemes, no exam-board text" is true of us and of none of them. The code vocabulary (M1, A1, ft, cao) is convention, not protectable text; Pearson's general marking guidance prose is, so the firewall stays.

---

## Sources

Consolidated from the six sweeps. Grouped by theme; all read on 30 Sept 2026.

**Student demand and forums**
- The Student Room threads on mark schemes: https://www.thestudentroom.co.uk/showthread.php?t=7225745 · ?t=640595 · ?t=1511244 · ?t=923288 · ?t=4805592 · ?t=4562526 · ?t=7636892 · ?t=7216157 · ?t=7206183 · ?t=7469422 · ?t=7589882
- Exam-day reactions 2024 P1: https://www.thestudentroom.co.uk/revision/alevel-gcse-exams/exams-archive/students-react-after-a-level-maths-paper-1-on-4-june-2024
- Mumsnet on lost working marks: https://www.mumsnet.com/talk/secondary/2848830-Is-it-normal-to-lose-marks-in-a-maths-exam-if-you-got-a-question-right-bu-didnt-show-workings
- Hardest 9MA0 questions: https://thinkstudent.co.uk/hardest-a-level-maths-questions/ · https://cognito.org/blog/hardest-a-level-maths-topics · https://mathswithsophie.com/blog/develop-exam-ready-problem-solving-skills-for-a-le
- Warwick students on AI and maths: https://warwick.ac.uk/fac/cross_fac/academy/funding/2023-24-int-projects/ai-in-maths/project-outputs/students-conversations
- Save My Exams AI survey: https://www.savemyexams.com/learning-hub/insights/ai-in-education-statistics/

**Entries, shares, boundaries**
- MEI 2026 entries: https://mei.org.uk/insight/summary-of-2026-as-a-level-mathematics-and-further-mathematics-entries-and-results/
- JCQ 2025 press notice: https://www.jcq.org.uk/wp-content/uploads/2025/08/UK-JCQ-Press-notice-Level-3-2025.pdf · trends: https://www.jcq.org.uk/wp-content/uploads/sites/2/2026/02/A-and-AS-level-trends-June-2025.pdf
- Ofqual results 2026: https://ofqual.blog.gov.uk/2026/08/13/a-level-and-level-3-results-2026-at-a-glance-key-trends-and-context-for-teachers/
- Ofqual annual qualifications market report 2024–25: https://www.gov.uk/government/statistics/annual-qualifications-market-report-academic-year-2024-to-2025
- Grade boundaries: https://www.mathsgenie.co.uk/edexcel-a-level-grade-boundaries.php
- Pearson IAL grade statistics June 2024: https://qualifications.pearson.com/content/dam/pdf/Support/Grade-statistics/International-A-level/grade-statistics-june-2024-final-international-advanced-level.pdf
- IB statistical bulletin May 2025: https://ibo.org/globalassets/new-structure/about-the-ib/pdfs/dpcp-provisional-statistical-bulletin-may-2025_en.pdf

**Consumer competitors**
- Save My Exams: https://www.savemyexams.com/study-tools/smart-mark/ · https://www.trustpilot.com/review/www.savemyexams.com
- Maths Genie: https://www.mathsgenie.co.uk/a-level/maths/edexcel/papers · https://mathsgenie.co.uk/blog/maths-genie-vs-save-my-exams-free-paid-maths-revision · https://mathsgenie.co.uk/paper-marker
- ExamSolutions: https://www.examsolutions.net/pricing · https://uk.trustpilot.com/review/examsolutions.net
- alevelmathsrevision.com: https://alevelmathsrevision.com/ust/students/ · https://alevelmathsrevision.com/ust/students/pricing/
- Medly: https://www.medlyai.com/uk · https://www.medlyai.com/uk/changelog · https://www.medlyai.com/uk/past-papers · https://www.medlyai.com/uk/blog/medly_mocks_2026 · https://www.medlyai.com/uk/blog/medly_freemium_2026 · https://uk.trustpilot.com/review/medlyai.com · https://apps.apple.com/gb/app/medly/id6670685314 · https://find-and-update.company-information.service.gov.uk/company/15110302/filing-history · https://thenextweb.com/news/medly-ai-8m-seed-felix-capital-gcse-tutoring · https://shlc-tutor.co.uk/blogs/gcse-and-11-exam-tips-revision-guides/medley-ai-review-why-this-viral-study-app-is-failing-students · https://arxiv.org/abs/2606.24973
- Revision Genie: https://revisiongenie.com/ · MasteryMind: https://masterymind.co.uk/pricing
- Up Learn: https://uplearn.co.uk/pricing · https://uk.trustpilot.com/review/uplearn.co.uk · https://help.uplearn.co.uk/en/articles/3746011
- Seneca: https://help.senecalearning.com/en/articles/3746290-how-much-is-premium · https://uk.trustpilot.com/review/senecalearning.com
- MME: https://mmerevise.co.uk/mme-premium/ · https://uk.trustpilot.com/review/mathsmadeeasy.co.uk
- Cognito, Study Rocket, Study Mind, MyEdSpace, Revisely, Bicen, TLMaths: https://cognito.org/ · https://getadapt.co.uk/purchase · https://studymind.co.uk/online-courses/a-level-maths-online-course/ · https://myedspace.co.uk/courses/a-level/maths-year-13 · https://revisely.com/alevel/maths/aqa · https://bicenmaths.uk/ · https://tlmaths.com/
- MarkScheme.app: https://markscheme.app/blog/save-my-exams-free-alternative
- Tutopiya: https://www.tutopiya.com/blog/pearson-edexcel-ai-tutor/ · https://www.tutopiya.com/tools/for-schools · https://www.tutopiya.com/learning-portal/
- Pearson Revise and AI assistant: https://plc.pearson.com/en-GB/news-and-insights/news/study-smarter-new-ai-powered-gcse-exam-practice-assistant-delivers · https://www.pearson.com/en-gb/schools/secondary/parents-learners/revision/gcse-revision/pearson-revise.html

**Teacher-facing markers and school products**
- MarkIt: https://www.markitapp.co.uk/ · https://www.markitapp.co.uk/mark-schemes/edexcel-a-level-maths · https://www.markitapp.co.uk/resources/ai-marking-accuracy-benchmarks · https://www.markitapp.co.uk/terms · GradeOrbit: https://www.gradeorbit.co.uk/ · https://www.gradeorbit.co.uk/students · https://www.gradeorbit.co.uk/pricing · marking.ai: https://marking.ai/ · Excelas: https://excelas.ai/services/ai-mock-exam-marking
- Dr Frost: https://www.drfrost.org/pricing · https://support.drfrost.org/hc/en-gb/articles/4604077203231-I-m-a-tutor-or-parent-can-I-sign-up-to-Dr-Frost
- Integral: https://integralmaths.org/pricing/uk-and-international-a-levels-for-educators/ · https://amsp.org.uk/integral/
- Exampro: https://exampro.co.uk/sec/maths-exampro.asp
- Pearson Mocks Service and examWizard: https://qualifications.pearson.com/en/support/Services/pearson-edexcel-mocks-service.html · https://qualifications.pearson.com/content/dam/pdf/Support/services/mocks-services/mock-services.pdf · https://qualifications.pearson.com/content/dam/pdf/Support/services/examwizard/examwizard-userguide.pdf
- Pinpoint: https://www.pinpointlearning.co.uk/indexschool.php · Smartgrade: https://www.smartgrade.co.uk/solutions/secondary-mocks
- Seneca schools: https://help.senecalearning.com/en/articles/13413714-seneca-for-schools-benefits-pricing-plans · Up Learn schools: https://uplearn.co.uk/schools
- Teacher pain: https://www.tes.com/magazine/teaching-learning/secondary/marking-mocks-have-you-tried-it-way · https://mhorley.wordpress.com/2017/03/22/qlas-are-they-worth-it/ · https://colleenyoung.org/2025/04/27/maths-revision-2025-updates/
- Procurement: https://www.gov.uk/guidance/data-protection-in-schools/procuring-educational-technology-edtech · https://www.freeths.co.uk/insights-events/legal-articles/2026/ico-publishes-findings-on-data-protection-practices-in-edtech-sector/ · https://thirdspacelearning.com/blog/dfe-generative-ai-product-safety-standards/ · https://allschools.co.uk/resources/understanding-school-budget-cycles · https://www.lended.org.uk/
- Tutors: https://www.mytutor.co.uk/view-tutors/Maths/A-Level/ · https://tutorful.co.uk/blog/a-level-tutor-prices · https://thetutor.link/how-much-is-a-maths-tutor/ · https://www.suttontrust.com/wp-content/uploads/2026/02/Private-Tutoring-2026.pdf

**Boards, regulators, research**
- Ofqual principles of AI in marking: https://www.gov.uk/government/publications/principles-of-ai-use-in-marking/principles-of-ai-use-in-marking · https://ofqual.blog.gov.uk/2026/01/14/using-ai-in-marking-why-technical-capability-fairness-and-transparency-all-matter/
- Cambridge International AI-assisted marking: https://www.cambridgeinternational.org/programmes-and-qualifications/developing-digital-exams/digital-mocks-service/continuing-our-ai-assisted-marking-development-for-digital-mock-exams/
- AQA and KCL: https://aqaglobal.com/ai-assisted-exam-marking
- Pearson copyright and endorsement: https://qualifications.pearson.com/en/support/support-topics/exams/past-papers/pearson-copyright-policy.html · https://qualifications.pearson.com/content/dam/pdf/Support/policies-for-centres-learners-and-employees/endorsement-of-resources-supporting-pearson-qualifications-policy.pdf
- AQA copyright (AI clause): https://www.aqa.org.uk/about-us/who-we-are/our-standards/copyright-and-intellectual-property-policy/copyright-policy-for-centres
- OCR copyright and endorsement: https://www.ocr.org.uk/about/our-policies/copyright/ · https://www.ocr.org.uk/Images/600903-cambridge-ocr-endorsed-resources-statement-of-policy.pdf
- Cambridge International on republishing papers: https://help.cambridgeinternational.org/hc/en-gb/articles/203544371-Can-I-reproduce-Cambridge-past-examination-papers-on-the-school-s-website-my-website
- Mark-scheme notation: AQA https://filestore.aqa.org.uk/resources/mathematics/AQA-7366-7357-7366-7367-NG-MARKING-GUIDANCE.PDF · OCR https://www.ocr.org.uk/Images/726795-mark-scheme-pure-mathematics.pdf · MarkIt guide https://www.markitapp.co.uk/mark-schemes
- Pearson v Chegg settlement: https://copyright.byu.edu/blog/three-closed-cases · Pearson H1 2026 6-K: https://www.sec.gov/Archives/edgar/data/0000938323/000165495426007081/a6516o.htm
- AI grading research: https://arxiv.org/abs/2606.24973 · https://arxiv.org/abs/2605.19043 · https://arxiv.org/abs/2607.01247 · https://arxiv.org/abs/2603.14732
- Marking-tool comparisons: https://www.topmarks.ai/best-ai-marking-software · https://getdeepmark.com/blog/best-ai-marking-tools-gcse-2027 · https://remarkableai.co.uk/articles/free-ai-marking-tools

**Not verified or not reachable:** Reddit (blocked); Save My Exams pages render only via JavaScript (prices confirmed by two third parties); Seneca student pricing (conflicting third-party figures); Integral school bands (portal only); Medly's method-mark explanation depth (needs an account); IAL 2025 statistics; Kognity.
