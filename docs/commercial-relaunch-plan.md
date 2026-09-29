# Commercial relaunch plan: a copyright-clean A Level Maths mark-scheme tutor

*Researched 29 Sept 2026. Research, not legal advice: get a UK IP solicitor to review §9 before taking money. Sources are listed at the end, and confidence is marked where it matters.*

## 1. Bottom line

You can sell a product with the same heart **without Pearson's permission**, as long as it contains **none of Pearson's expression**. The "heart" is:
- explaining exactly how marks are awarded, step by step (M1/A1/B1);
- warning where students lose marks;
- finding the right practice for the exact skills a student is weak at.

Copyright protects the wording, the specific choices in a question and the selection of mark-scheme alternatives. It does not protect:
- the mathematics;
- the skills in the specification;
- question *types*;
- the M/A/B marking system;
- facts about papers (which skills Q11 tests, mark totals, grade boundaries).

So the relaunch keeps the engine (your code, your 246-skill taxonomy, the search and recommendations) and **replaces the content**: your own questions, your own mark schemes, your own pitfall notes.

This is the model the successful businesses use. Corbettmaths, Dr Frost, Sparx, Up Learn and Save My Exams all write their own questions. Save My Exams keeps real past papers in a separate section it says is "used with permission". No exception in UK law lets a paid product store or show Pearson papers, mark schemes or examiner reports. The government confirmed in March 2026 that it won't add a commercial text-and-data-mining exception, and that material stored for an AI to look up and quote "will need to be licensed".

The market gap is real. Research found **no product that explains M1/A1 method marking step by step for A Level maths**. Save My Exams' "Smart Mark" *marks* answers but doesn't teach the marking.

## 2. Urgent, whatever you decide (do this first)

The GitHub repo **github.com/hblbennett-arch/edexcel-maths is public** (verified). It currently publishes Pearson material, which is already infringement. It contains:
- 3,103 files under `data/processed`: transcribed questions, mark schemes and 21,764 examiner-report quotes that carry "© Pearson Education Ltd";
- 8 AQA examiner-report PDFs and an AQA data sheet at the repo root. AQA forbids putting its material "on any website" and bans any AI use;
- the GitHub Pages topic pages (`output/`, `output-as/`), with worked examples from real papers and links to PMT's copies. Linking for profit to copies whose licensing is unknown carries risk under GS Media.

Steps (I can do 2–4 for you):
1. Make the repo **private** (GitHub → Settings → General → Danger Zone → Change visibility). GitHub Pages on a free account then stops, which is fine for now.
2. Remove `data/processed/`, the AQA PDFs and the real-question topic pages from git, and purge them from **history** (`git filter-repo`). Making the repo private first means old clones and forks are the only remaining exposure.
3. Fix `.gitignore` so `data/` really is excluded, as CLAUDE.md already says it should be.
4. Keep the Pearson knowledge base **only on your own machine, for personal study**. It must never be in the product, its prompts or its servers.

## 3. What is and isn't allowed (summary of the legal research)

| Activity | Risk | Why |
|---|---|---|
| Storing Pearson questions, mark schemes or examiner reports in a paid product, or in its AI lookup store | **High** | Copying needs a licence; no exception fits commercial use (CDPA s.17, s.29, s.29A, s.178; Government AI report 2026 para 118) |
| Showing past questions or mark schemes to paying users | **High** | Pearson's policy bars charging; a substantial part is reproduced |
| Paraphrasing whole mark schemes | **High** | Close paraphrase of the selection and arrangement still infringes (Designers Guild; SAS v WPL) |
| Feeding past papers into an AI prompt to make "variants" | **Med–High** | A copy is made on every call; outputs come out too close; Anthropic's IP indemnity excludes what you put in |
| Close variants (same scenario and parts, new numbers) | **Medium** | "Altered copying" of the setter's choices |
| Student uploads their own question for the AI to explain ("bring your own question") | **Low–Med** | You are the one copying; mitigate by processing then deleting, keeping nothing, and clear terms of use |
| **Original questions written from the DfE subject content** | **Low** | Ideas, skills and maths are free (Baigent; SAS; Navitaire) |
| **Your skill index of past papers** ("P2 June 2019 Q11: implicit differentiation, 11 marks") | **Low** | Facts about the papers, not Pearson's wording |
| Links to Pearson's own free PDFs (new tab, no framing) | **Low** | Svensson / BestWater, still UK law |
| "For Pearson Edexcel A Level Mathematics (9MA0)" in plain text, with a disclaimer | **Low** | Referential use allowed (Trade Marks Act 1994 s.11(2)) |
| "Edexcel" in the product or domain name, or Pearson logos | **High** | Implies a connection that doesn't exist |
| Launching to under-18s without the ICO Children's Code work done | **High** | Age Appropriate Design Code; Data (Use and Access) Act 2025 s.81 |

The one real precedent is **Pearson v Chegg**, filed in the US in 2021 over paid answers to Pearson textbook questions, "copied or paraphrased". It settled in Dec 2024 on confidential terms. Pearson does sue paid Q&A services.

## 4. The redesigned product: same heart, clean content

| Heart feature | Today (Pearson-derived) | Clean version |
|---|---|---|
| **Mark-by-mark explanations** | Official mark schemes | **Your own mark schemes** for your own questions, in the standard notation (M1, dM1, A1, B1, ft, oe, cao, awrt). That notation is generic across boards; explain it in your own "How marks are awarded" guide, not Pearson's General Marking Guidance text. `validate.py` checks the tutor against *your* scheme exactly as it does now. |
| **Where students lose marks** | 21,764 verbatim examiner quotes | **Your pitfall library**: about 3–5 pitfalls per skill, in your own words, from your expertise. Don't rework examiner reports item by item. Over time, **your users' own mistakes** (which step they got wrong, per skill) become better data than examiner reports, and nobody else has it. |
| **"How students did"** | Examiner-report mean marks | **Your own users' success rates** per part, after launch. Before that, use difficulty tiers you set yourself. |
| **Find questions by skill / description / skill combination** | Search over Pearson text | **The same code** over your own bank. The tagging is exact, because you design each question to its tags. |
| **Build-up practice ladders, "hardest part" refocus** | Over Pearson parts | Unchanged code, over your parts |
| **Real past papers** | Stored and shown | **Past-paper map**: your own skill index of real papers (tags, marks, question types). It links out to the paper on Pearson's own website and stores no Pearson text. "Find a real past-paper question on implicit differentiation" still works, and the student opens it on Pearson's site. |
| **Explain a question I'm stuck on** | Matched to the stored question | **Bring your own question**: the student pastes or photographs it. The tutor explains it with *estimated* marks ("likely M1"); your current new-question path already does this. The upload is processed, never stored or shown to anyone else, with no official mark scheme. |
| **Mark my answer (new)** | — | The student submits working for one of *your* questions; the AI marks it against *your* scheme and explains each lost mark. This competes with Save My Exams Smart Mark and teaches as well as marking. |
| **Mock papers (new)** | — | Your own full papers following the public 9MA0 structure (P1, P2 and P3 at 100 marks, 2 hours each; paper structure is a fact). |

Branding: a new name without "Edexcel", then "Built for Pearson Edexcel A Level Mathematics (9MA0) · Independent: not affiliated with, endorsed or licensed by Pearson."

## 5. Making the question bank without copying: the clean-room pipeline

**Inputs allowed:**
- the DfE "GCE AS and A level subject content for mathematics" and Ofqual's maths conditions (both OGL v3.0: commercial reuse allowed with attribution);
- your 246-skill taxonomy and 73 question types (your own work);
- your own "blueprints";
- the general exam style you know from experience.

**Inputs banned:** any Pearson question, mark-scheme or examiner-report text, in prompts or in the store. Reading past papers yourself is fine; reading isn't copying.

A **blueprint** is an abstract design you write, for example: "3 parts, 9 marks; (a) partial fractions (3), (b) integrate to logs (4), (c) exact area (2); context: none; difficulty: core". The pipeline, per item:
1. **Generate** the question, a full worked solution and a mark scheme in M/A/B notation from the blueprint, with random new contexts and numbers. No past paper goes in the prompt.
2. **Check automatically** (deterministic, in the spirit of your current evals):
   - sympy verifies every final answer and intermediate value;
   - a second model solves the question *blind* and must match;
   - the marks add up and each mark is a checkable step;
   - notation checks (`check_notation.js`);
   - the tags match the blueprint.
3. **Check for novelty.** A model can **regurgitate a memorised past paper**, so this matters. Options, to settle with the solicitor:
   - (a) a fingerprint index (hashed word sequences plus the numbers used) built once from the Pearson papers, with the text then deleted. Low–medium legal risk: building it involves copying once;
   - (b) comparison against a local Pearson copy that never leaves your machine. Technically copying, low exposure;
   - (c) no automatic check; rely on your review plus random contexts.
   Reject anything too similar to a real question.
4. **Review by you.** Accept, edit or reject. Keep a record of who reviewed what. Human creative choices also give *you* solid copyright in the bank. Don't rely on s.9(3) "computer-generated works": the government proposed removing it in March 2026.

Size and cost (estimates):

| Content | Amount |
|---|---|
| Short single-skill items (about 5 per skill, starter/core/stretch) | ~1,200 |
| Multi-part exam-style questions (the "differentiation + partial fractions + stationary points" kind) | ~300 |
| Full mock sets | 6 (2 × P1/P2/P3) |
| Pitfall notes | ~250 skills × 3–5 |

- Model cost: ~$0.10–0.30 per item including the blind solve, so **~$300–600** in total.
- **Your review time is the real cost: ~3–6 minutes per item, 80–150 hours.**
- Start with 2 skill groups to measure pass rates before scaling.

## 6. Changes to this codebase

- **Split engine from content.** `chatbot/` stays the engine. Content moves to swappable "content packs" with the same database shape (questions, parts, mark schemes, tags), plus a **`provenance`** column (`original` / `ogl` / `pearson-private`), `author` and `reviewed_at`.
- **Deterministic licence check** (`scripts/check_provenance.py`), run in the build. A commercial build **fails** if any row isn't `original`/`ogl`, if any examiner notes are present, or if any text matches the novelty fingerprints.
- **Prompts** (`chatbot/prompts.py`): replace "official mark scheme" and "verbatim examiner-report notes" with "our mark scheme" and "our pitfall notes". Keep the "likely M1" behaviour for bring-your-own-question.
- **Past-paper map:** a table of references, tags, marks and question type, plus a link to Pearson's official PDF page, and no text. Remove every PMT link.
- **Model backend:** switch to your own Anthropic API account under the Commercial Terms, which say you own the outputs. Don't use the Claude Code Enterprise login; that belongs to your employer.
- **Evals:** keep them all, re-pointed at the clean pack. `practice_eval` and `practice_search_eval` work unchanged on any pack.

## 7. Other compliance before launch

- **Children's Code** (ICO), because users are under 18:
  - a data protection impact assessment (DPIA);
  - high-privacy defaults, and profiling off unless it's core and explained (skill tracking is core, so explain it plainly);
  - no nudge techniques, and child-friendly privacy information.
- **ICO data protection fee:** £52 a year (tier 1).
- **Online Safety Act:** a one-to-one tutor with no sharing between users and no live web search appears to be outside scope today. The Crime and Policing Act 2026 lets ministers extend duties to AI services, so avoid sharing features for now.
- **Anthropic's rules for services used by minors:** safeguards and clear disclosure that the tutor is an AI.
- **Consumer law:** 14-day cancellation (Consumer Contracts Regulations). The DMCCA subscription rules are expected from spring 2027, so build easy cancellation and renewal reminders in now.
- **VAT:** register once turnover passes £90k a year.
- **Your employment contract** (Verisk): check its IP and side-business clauses before launch.

## 8. Market positioning and pricing

- **Pitch:** "Learn to write answers the way examiners mark them." That means step-by-step M1/A1 explanations, marking of *your* working, and practice aimed at the exact skill you drop marks on.
- **Student price:** £5–10 a month or £40–60 a year. Save My Exams is about £48 a year; Up Learn A Level is £320–420 a year with a grade guarantee.
- **Schools:** about £600–650 per school per year is the going rate (Dr Frost £650 + VAT, Sparx from £600, Seneca £646). This is the most predictable revenue.
- **Growth:** free reach first (short videos on "why you lost this mark", a free skill finder), then trials with schools and academy trusts. Up Learn's "pay one, fund one" scheme is a good model.
- **Honest expectations:** most revision businesses make thin profits. Sparx lost £4.6m on £3.0m turnover in FY2022. Save My Exams and Seneca only recently appear profitable (inferred from reserve movements in their Companies House filings). The earlier estimate still stands: roughly £0–2k profit a month in year one, and £5–15k a month by years two or three if it works.

## 9. Questions for a solicitor (a fixed-fee IP review before launch)

1. Is our blueprint-based clean-room process, with human review, sufficient? Should we keep written records of provenance?
2. Novelty checking: which of options (a), (b) or (c) in §5 is acceptable?
3. Bring-your-own-question terms: the user warrants they have rights, uploads are deleted after processing, and there's a takedown route. Is that enough, and are there limits on repeating the question back?
4. The past-paper map: any risk from Pearson's database right or its terms of use?
5. Wording for the trade mark reference and the "not affiliated" disclaimer.
6. Cleaning up the public repo: anything more needed beyond making it private and purging history?

## 10. Phased plan

| Phase | What | Time | Cost |
|---|---|---|---|
| 0 | Make the repo private and purge history (§2); check your employment contract; open an Anthropic API account | this week | £0 |
| 1 | Engine/content split, provenance check, clean prompts; pipeline prototype on 2 skill groups; measure pass rates and review time | 2–3 weeks part-time | ~$20 |
| 2 | Build the bank (§5) and write the pitfall library | 8–12 weeks part-time | ~$300–600 + your review time |
| 3 | Solicitor review; Children's Code DPIA; terms and privacy notice; ICO fee; free pilot with ~100 students | 4 weeks | ~£500–2,000 legal (estimate) + £52 |
| 4 | Paid launch (annual "exam pass"); approach 3–5 schools for trials | from exam season | — |

## Sources

- CDPA 1988: [s.3](https://www.legislation.gov.uk/ukpga/1988/48/section/3), [s.9](https://www.legislation.gov.uk/ukpga/1988/48/section/9), [s.28A](https://www.legislation.gov.uk/ukpga/1988/48/section/28A), [s.29](https://www.legislation.gov.uk/ukpga/1988/48/section/29), [s.29A](https://www.legislation.gov.uk/ukpga/1988/48/section/29A), [s.30](https://www.legislation.gov.uk/ukpga/1988/48/section/30), [s.32](https://www.legislation.gov.uk/ukpga/1988/48/section/32)
- Cases:
  - [University of London Press v University Tutorial Press (1916)](https://www.cipil.law.cam.ac.uk/virtual-museum/university-london-press-v-university-tutorial-1916-2-ch-601): maths exam papers are copyright works
  - [THJ v Sheridan (2023)](https://caselaw.nationalarchives.gov.uk/ewca/civ/2023/1354)
  - [Designers Guild (2000)](https://www.bailii.org/uk/cases/UKHL/2000/58.html)
  - [Baigent v Random House (2007)](https://caselaw.nationalarchives.gov.uk/ewca/civ/2007/247)
  - [SAS v WPL (2013)](https://caselaw.nationalarchives.gov.uk/ewca/civ/2013/1482)
  - [Infopaq](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62008CJ0005)
  - [Svensson](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62012CJ0466)
  - [GS Media](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62015CJ0160)
  - [TuneIn v Warner (2021)](https://caselaw.nationalarchives.gov.uk/ewca/civ/2021/441)
  - [Getty v Stability AI (2025)](https://caselaw.nationalarchives.gov.uk/ewhc/ch/2025/2863) (appeal status unverified)
- Database Regulations 1997: [reg.13](https://www.legislation.gov.uk/uksi/1997/3032/regulation/13), [reg.16](https://www.legislation.gov.uk/uksi/1997/3032/regulation/16); [Trade Marks Act 1994 s.11](https://www.legislation.gov.uk/ukpga/1994/26/section/11)
- [UK Government Report on Copyright and AI, 18 Mar 2026](https://assets.publishing.service.gov.uk/media/69ba692226909a14239612e4/CP2602959_-_Report_on_Copyright_and_Artificial_Intelligence_web.pdf) (paras 47, 118, 120)
- Board policies:
  - [Pearson copyright policy](https://qualifications.pearson.com/en/support/support-topics/exams/past-papers/pearson-copyright-policy.html) (permission: copyrightPQS@pearson.com)
  - [Pearson publication policy](https://qualifications.pearson.com/content/dam/pdf/Support/policies-for-centres-learners-and-employees/qualification-assessment-publication-policy.pdf)
  - [AQA](https://www.aqa.org.uk/about-us/who-we-are/our-standards/copyright-and-intellectual-property-policy)
  - [OCR](https://www.ocr.org.uk/about/our-policies/copyright/)
- Open content: [DfE A level maths subject content (OGL)](https://www.gov.uk/government/publications/gce-as-and-a-level-mathematics); [Ofqual maths conditions (OGL)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/517726/gce-subject-level-conditions-and-requirements-for-mathematics.pdf); [Oak National Academy (OGL, KS1–4 only)](https://www.thenational.academy/legal/terms-and-conditions-api-version)
- Precedents:
  - [Pearson v Chegg](https://copyright.byu.edu/blog/three-closed-cases)
  - [Save My Exams on its question sources](https://www.savemyexams.com/learning-hub/support/are-save-my-exams-questions-from-past-papers/)
  - [Save My Exams Smart Mark](https://www.savemyexams.com/study-tools/smart-mark/)
  - [Dr Frost pricing](https://www.drfrost.org/pricing)
  - [Up Learn pricing](https://uplearn.co.uk/pricing)
- Compliance:
  - [ICO Children's Code](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/age-appropriate-design-a-code-of-practice-for-online-services/)
  - [DUAA 2025 s.81](https://www.legislation.gov.uk/ukpga/2025/18/section/81)
  - [Ofcom on generative AI](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/open-letter-to-uk-online-service-providers-regarding-generative-ai-and-chatbots)
  - [Crime and Policing Act 2026 s.248](https://www.legislation.gov.uk/ukpga/2026/20/section/248)
  - [ICO fee](https://ico.org.uk/for-organisations/data-protection-fee/)
  - [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
  - [Anthropic guidelines for services used by minors](https://support.claude.com/en/articles/9307344-responsible-use-of-anthropic-s-models-guidelines-for-organizations-serving-minors)
- Not verified: the UK trade mark register entries for EDEXCEL and PEARSON; the Getty appeal status; whether Physics & Maths Tutor is licensed.
