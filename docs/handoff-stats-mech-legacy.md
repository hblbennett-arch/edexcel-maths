# Handoff: Add Statistics, Mechanics and Legacy/International Papers to the Tutor

**For:** a new Claude Code session working in `~/edexcel-maths`.
**From:** the session of 2026-09-25 that built Phases 2–5 of the RAG tutor chatbot for A Level Pure.
**Read this whole document before doing anything.** Then read the docs in §2.

---

## 0. The task (the user's words, condensed)
1. Scrape **all Edexcel Statistics and Mechanics papers** for the current specification, as was done for Pure.
2. **Also** scrape the **legacy** Pure, Statistics and Mechanics papers (the user gave this example: International Advanced Level, spec code `ial-maths`, January 2020). They are *only* a way to get more questions into the project.
3. **Current spec only.** Anything that uses topics or methods **not in the current 9MA0 specification is dropped.** Check against the **specification document itself**, never from memory.
4. **Make sure every current-spec paper is covered.** The user supplied this list of dates:
   `Jan 2019, Jun 2019, Oct 2019, Jan 2020, Oct 2020, Jan 2021, Jun 2021, Oct 2021, Jan 2022, Jun 2022, Oct 2022, Jan 2023, Jun 2023, Oct 2023, Jan 2024, Jun 2024, Oct 2024, Jan 2025, Jun 2025, Oct 2025, Jan 2026, Jun 2026`
5. For **every** paper scraped, also get its **mark scheme and examiner report**.
6. **Tag legacy questions with their own spec code,** so current and legacy can always be told apart.
7. **Do all scraping from the Edexcel/Pearson website** (qualifications.pearson.com).
8. Then process everything through the same phases as Pure, so it's usable by the bot.

---

## 1. ⚠️ Confirm scope with the user first (one short question)
The dates list above is **not** the UK A Level 9MA0 calendar:
- 9MA0 has **no January sittings**. Its sittings are June 2018, June 2019, October 2020, October 2021, and June 2022 onwards.
- The list (Jan/Jun/Oct, from January 2019 to June 2026) matches the **Pearson Edexcel International Advanced Level (IAL) Mathematics, 2018 specification** exactly. Its first exams were in January 2019.
- The example URL the user gave (`Specification-Code=…ial-maths`) is the **older IAL 2013 specification**. Its units include `WMA01` (C12), `WMA02` (C34), `WFM01` (FP1), `WME01` (M1), `WST01` (S1) and `WDM01` (D1).

The Maths qualifications Pearson publishes:

| Family | Spec | Units / papers | Status for this project | Suggested `qualification` tag |
|---|---|---|---|---|
| UK A Level | **9MA0** (2017 spec, first exams 2018) | Paper 1, Paper 2 (Pure), Paper 3 (Statistics + Mechanics sections) | **Current**: the chatbot's specification | `9MA0` |
| UK AS Level | 8MA0 | Paper 1 (Pure), Paper 2 (Stats + Mech) | Current (AS subset) | `8MA0` |
| IAL | **2018 spec** (first exams Jan 2019) | WMA11–14 (Pure 1–4), WST11–13 (S1–S3), WME11–13 (M1–M3), WFM11–13, WDM11 | International, not UK; much overlaps 9MA0 | `IAL-2018` |
| IAL | 2013 spec (`ial-maths`) | WMA01/02, WST01–03, WME01–03, WFM01–03, WDM01 | Legacy | `IAL-2013` |
| UK GCE (pre-2017) | 2008 spec | 6663–6666 (C1–C4), 6683/6684/6691 (S1–S3), 6677/6678/6679 (M1–M3) | Legacy | `GCE-2008` |

**Ask the user, as a single multiple-choice question:** *"Your dates match the International A Level 2018 spec. Do you want: (a) 9MA0 Paper 3 for current Stats/Mech **plus** IAL 2018 **and** IAL 2013 as extra (non-9MA0) question sources, all filtered to 9MA0 content [recommended]; (b) also the old UK GCE 2008 papers; or (c) something else?"*
- **Recommended default:** 9MA0 (all sittings, including Paper 3) as current; IAL 2018 + IAL 2013 as extra sources, each tagged with its own `qualification`; everything filtered to 9MA0 content.
- Also check with the user whether **June 2026** papers are wanted. Pearson may not have published them publicly yet (check the site; don't assume).
- Further Maths (WFM) and Decision (WDM) units are **out of scope**: their content isn't in 9MA0. Don't scrape them unless the user asks.

---

## 2. Read these first (in this order)
| Doc | Why |
|---|---|
| `CLAUDE.md` | Project overview. Note: its "don't commit `data/`" line is out of date; `data/processed/` is tracked. |
| `docs/rag-chatbot-plan.md` | The plan and status of every phase |
| **`docs/skill-add-papers-pipeline.md`** | **The hub:** the 7-step pipeline for adding papers, the cost rules, and what to adapt per subject |
| `docs/question-extraction-spec.md` | Single-pass extraction into final form (parts, verbatim, LaTeX) |
| `docs/ms-audit-spec.md` | Auditing question and mark-scheme text against the PDFs |
| `docs/skill-examiner-report-extraction.md` + `docs/examiner-notes-extraction.md` | Examiner-report notes (verbatim, with a quote check) |
| `docs/notation-spec.md` | LaTeX conventions |
| `docs/tagging-spec.md` | Question types and part skills |
| `docs/pmt-url-patterns.md` | URL patterns found so far, plus `sources.json` |
| `docs/review-checklist.md` | The **running manual-review log**. Add every new human-review item here as you go. |
| `docs/ms-audit-report.md`, `docs/examiner-notes-review.md`, `docs/taxonomy-draft.md` | Examples of the review outputs to produce again |

---

## 3. Standing rules (user preferences, learned the hard way)
- **Never commit or push, and don't ask to.** The user will say when. The push is also blocked pending a new GitHub token.
- **Log every human-review item** in `docs/review-checklist.md` as it comes up, and tell the user how many were added.
- **Verify against official documents, never memory.** That covers the specification, formula booklet, mark schemes, question papers and examiner reports. The 2026 audit found 106 real transcription errors in text that had passed every structural check. Among them were "wait…" asides, dropped roots and modulus bars, reversed ranges, and mixed-up mark-scheme methods.
- **Never invent examiner commentary.** Quotes must be verbatim, and `build_db.py` enforces this.
- **User background:** new to dev tooling, so give step-by-step instructions. They want fully explained derivations, and to review changes before any commit.
- **The LLM runs on the user's Verisk Claude Enterprise login via Claude Code** (`TUTOR_BACKEND=claude-code`, model `claude-haiku-4-5`). There's no API key. Each tutor answer costs about $0.05 and takes 45–70 s.
- **Agents:**
  - at most **5 in parallel**;
  - give each its own scratch subfolder (they overwrote each other's `dump.py` once);
  - agents write **change lists** and scripts apply them;
  - every agent step has a checker the agent must run until it passes.
- **Cost:** follow the "Keeping it cheap" rules in the pipeline hub. Batch 2–3 papers per agent for tagging and auditing, and use 1 paper per agent for extraction. Pilot one paper before fanning out.

---

## 4. Scraping from Pearson (method proven 2026-09-25)
The past-papers page (`https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html?...`) is an Angular app, so its PDF links **aren't in the raw HTML**. What was tried:
- `/content/dam/pdf/past-papers.json` and `past-papers-qf.json` contain filter options only, not documents.
- The search service `/services/pearson/algolia/GET.servlet` answered, but the parameter format wasn't found (guessed queries returned empty).
- ✅ **Headless Chrome with `--dump-dom` works.** It renders the page, and the PDF `href`s can be read straight from the DOM:

```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
U='https://qualifications.pearson.com/en/support/support-topics/exams/past-papers.html?Qualification-Family=International-Advanced-Level&Qualification-Subject=Mathematics&Status=Pearson-UK:Status%2FLive&Specification-Code=Pearson-UK:Specification-Code%2Fial-maths&Exam-Series=January-2020'
perl -e 'alarm 150; exec @ARGV' "$CH" --headless=new --disable-gpu --user-data-dir=<scratch>/chrome-prof \
  --virtual-time-budget=40000 --dump-dom "$U" > page.html     # (macOS has no `timeout`; perl alarm instead)
grep -o -E 'href="[^"]+\.pdf"' page.html | sort -u           # -> 18 links for that page
```

Links look like:
```
/content/dam/pdf/International Advanced Level/Mathematics/2013/Exam materials/WMA01_01_que_20200305.pdf   (question paper)
/content/dam/pdf/International Advanced Level/Mathematics/2013/Exam materials/WMA01_01_rms_20200305.pdf   (mark scheme)
/content/dam/pdf/International Advanced Level/Mathematics/2013/Exam materials/WMA01_01_pef_20200305.pdf   (examiner report)
/content/dam/pdf/International Advanced Level/Mathematics/2013/Exam materials/P61129A_IAL_Core_Maths_C34_WMA02_01_JAN_20.pdf  (older naming: a question paper)
```
Prefix with `https://qualifications.pearson.com` and URL-encode the spaces.

**File types:** `_que_` is the question paper, `_rms_` or `_msc_` the mark scheme, and `_pef_` the examiner report (Principal Examiner Feedback). Older files use descriptive names; classify these by title text and by opening the first page (`pdftotext -l 1`), never by guessing. Other files may appear too, such as insert booklets and data sheets; keep the ones questions need.

**Filter parameters observed:** `Qualification-Family` (`International-Advanced-Level`, `A-Level`), `Qualification-Subject=Mathematics`, `Status=Pearson-UK:Status/Live`, `Specification-Code=Pearson-UK:Specification-Code/<code>`, `Exam-Series=<Month>-<Year>`. Only `ial-maths` (IAL 2013) has been seen so far.
- **To discover the codes for 9MA0 and IAL 2018:** open the page without a `Specification-Code`, dump the DOM, and read the specification dropdown's options. Or open the qualification's own page (e.g. "Pearson Edexcel International Advanced Level in Mathematics (2018)" → Past papers) and copy the filter URL. Record them in `docs/pmt-url-patterns.md`.
- **Known 9MA0 filenames:** mark schemes `9ma0-0N-rms-YYYYMMDD.pdf`, examiner reports `9ma0-0N-pef-YYYYMMDD` / `9MA0_0N_pef_YYYYMMDD` under `/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/`. The table is in `docs/pmt-url-patterns.md`.

**Build `scripts/scrape_pearson.py`:**
- For each (qualification, series), dump the DOM and collect PDF links.
- Classify them (qualification, unit code, series, doc type).
- Download to `data/raw/pearson/<qualification>/<series>/` (gitignored), and check each with `file` that it's a PDF. A 404 page saved as `.pdf` has happened before.
- Run `pdftotext` (`-layout` for question papers and mark schemes, `-raw` for examiner reports; see the examiner-report skill for why).
- Write `data/raw/pearson/manifest.json` with url, local path, qualification, unit, series, doc type and sha1.
- Be polite: run sequentially, wait about 2 s between pages, and reuse the Chrome profile.

**Completeness check (required):** for each (qualification, unit, series), a question paper, mark scheme and examiner report must all exist. Print a table of gaps. Report missing examiner reports to the user instead of silently skipping, since Pearson didn't publish every one.

**Cross-check 9MA0 coverage** with `scripts/build_sources.py --verify` (the PMT listing). It already lists Paper 3 Stats/Mech for June 2018, 2019, Oct 2020, Oct 2021 and June 2022–2025. Pearson must be the download source; PMT is only a cross-check.

Python HTTPS on this network needs `truststore` (`import truststore; truststore.inject_into_ssl()`), or use `curl`. Both are covered in `scripts/build_sources.py` and `chatbot/search.py`.

---

## 5. Keeping only current-spec content (the main new rule)
1. **Download the official 9MA0 specification PDF** from Pearson (the Mathematics 2017 qualification page, "Specification"). Check with `file` that it really is a PDF.
2. **Build `data/processed/spec_9ma0.json`:** every content statement with its section and number (Pure topics 1–10; Statistics sections 1–5; Mechanics sections 6–9, as numbered in the document), transcribed from the PDF. Human-review it, and log that in the review checklist.
3. **Classify every question by content,** in the same pass as extraction (§6), using an agent with the spec list. Each part gets `spec_refs: ["S4.1", …]`. A part that uses **any** method or topic **not** in 9MA0 gets flagged `out_of_spec` with the reason and the offending technique.
4. **Keep or drop whole questions** (the user said "don't keep them"). If any part is out of spec, drop the question. Record every dropped question in `data/processed/_excluded/<paper_id>.json` with the reasons, and summarise the counts for the user. Nothing dropped reaches `questions/`.
5. **Watch for syllabus differences.** Legacy and IAL units contain topics 9MA0 lacks (and vice versa), and some shared topics differ in depth or method. Check each against the spec, never from memory. The **formula booklet** also differs by qualification. Booklet flags must come from the **9MA0 booklet** (`data/formula-booklet-9MA0.pdf`, the real one since 2026-09-25; it includes Statistics and Mechanics sections and statistical tables), not the source paper's booklet.
6. **Methods count too, not just topics.** A question within 9MA0 topics whose mark scheme *requires* a non-9MA0 method (e.g. a Further Maths technique) is out of spec. If an allowed alternative method exists, keep the question and follow the in-spec method.
7. **Question style:** 9MA0 Statistics uses a large data set (LDS) and hypothesis-test wording, while IAL papers don't use the 9MA0 LDS. Questions *about the 9MA0 LDS* only come from 9MA0 papers, and IAL questions shouldn't be presented as LDS questions.

---

## 6. Processing into the bot (same phases as Pure; see the hub doc)
Run these per qualification, piloting one paper first for each new qualification or component.

| Step | What | Tools / spec | Notes for Stats/Mech/legacy |
|---|---|---|---|
| **2. Extract** (final form, one pass) | Stem, parts, verbatim text, verbatim mark scheme, LaTeX | `docs/question-extraction-spec.md` | Add fields `qualification`, `unit` (e.g. `WST11`), `component` (`pure` \| `stats` \| `mech`), `status` (`current` \| `legacy`), `spec_refs` per part. **Adapt:** IAL papers print marks as "(N)" and have "(Total for Question N is M marks)" like 9MA0, but check older 2013/GCE layouts. Statistical tables and data inserts may be separate PDFs. |
| **2b. Spec filter** | Keep or drop per §5 | new | Drops go to `_excluded/`; counts go to the user |
| **3. Scripted checks** | parts/marks, figures, notation, build | `split_parts.py`, `find_figures.py`, `check_notation.js --questions`, `build_db.py` | `find_figures.py` finds "Figure N"; statistics questions also have tables and diagrams, so check the render step covers them. **Extend `build_db.py`** for the new fields, and make IDs unique across qualifications (`<qualification>_<unit>_<series>_Q<n>`, e.g. `IAL2018_WST11_Jan2020_Q3`). Current 9MA0 IDs stay as they are (`P1_June2022_Q15`); 9MA0 Paper 3 uses `P3_June2019_stats_Q2` to match `sources.json`. |
| **4. Audit** | question text + mark scheme vs PDFs | `docs/ms-audit-spec.md`, `scripts/apply_ms_audit.py` | Needed even with v2 extraction; batch 2–3 papers per agent |
| **5. Examiner notes** | verbatim notes + performance | `docs/examiner-notes-extraction.md`, `scripts/check_examiner_notes.py` | IAL/9MA0 "pef" reports have the same style as Pure. Older reports may differ. |
| **6. Taxonomy + tags** | question types and skills | `docs/tagging-spec.md`, `scripts/check_tags.py` | **Stats and Mech need their own vocabulary** (a one-off build: one agent drafts types, groups and skills from the Stats/Mech parts plus the 9MA0 spec, and the **user reviews before tagging**). Reuse the shared exam-technique and algebra skills. Legacy papers use the **same** vocabulary; they're tagged by content, and that's how "current vs legacy" questions get recommended together. |
| **Links** | `sources.json` | `scripts/build_sources.py` | Extend for Pearson-hosted papers and IAL/legacy (the PMT listing only covers 9MA0/8MA0). Add a `qualification` field. |
| **7. Rebuild + evaluate** | DB, embeddings, retrieval eval, conversation tests | `build_db.py`, `build_embeddings.py`, `python -m eval.retrieval`, `python -m eval.chat_smoke` | Add retrieval test cases for Stats/Mech. The bot must **label legacy/IAL questions** in answers and recommendations ("from the International A Level, 2018 spec"). Keep 9MA0 first in recommendations unless the user decides otherwise. |

**Tutor code touch-points** once the data lands:
- `chatbot/identify.py`: references like "S1 January 2020", "WST11", "paper 3 statistics 2019" are needed. Today's parser only knows P1/P2 + year.
- `chatbot/recommend.py`: add a qualification preference.
- `chatbot/prompts.py`: Stats/Mech explanation rules, e.g. hypothesis-test conclusion wording in context, and g = 9.8 m s⁻² with answers to 2–3 s.f. in Mechanics. Take these from the mark schemes, not memory.
- `chatbot/validate.py`: numeric checks work for most Stats/Mech answers, but probabilities from tables and rounding conventions need care.

Add an `eval/chat_smoke.py` case for each new reference style.

---

## 7. Useful facts and gotchas (from this session)
- **Environment:** `.venv/` (Python 3.14), `requirements.txt`, and `pdftotext`/`pdftoppm` (poppler).
  - `node_modules/` is **root-owned**, so KaTeX is used from `~/.cache/edexcel-maths-devtools/node_modules` (`check_notation.js` falls back to it automatically). The user may later run `sudo rm -rf node_modules && npm install`.
  - Embeddings use the local model **bge-small-en-v1.5** via fastembed, cached in `~/.cache/edexcel-maths-devtools/fastembed`. Rebuild with `scripts/build_embeddings.py` after any data change; the search refuses stale files.
  - Scripts that load onnxruntime end with `os._exit(0)` after flushing stdout, because it can abort at interpreter exit.
- **Claude Code backend:** `claude -p` with `--input-format stream-json --output-format stream-json --verbose` (needed for images), plus `--json-schema`, `--tools ""`, `--strict-mcp-config`, `--no-session-persistence`, `--max-budget-usd`, and env `MAX_THINKING_TOKENS`, run from an empty working folder. **Don't use `--bare`**: it ignores the Enterprise login.
- **Part labels:** the JSON schema enumerates each question's labels, since Haiku once wrote "(a)" instead of "a".
- **Try the tutor:**
  - `python -m chatbot.web` (local UI at http://127.0.0.1:8765, add `--offline` to skip the model);
  - `python -m chatbot.chat` (terminal);
  - `python -m chatbot "<msg>"` (retrieval dump).
- **Formula booklet:** the real 9MA0 booklet is at `data/formula-booklet-9MA0.pdf` (48 pages; A Level Pure is on PDF pp. 9–11, and Statistics and Mechanics sections follow). **8 of the revision site's formula badges are wrong** (logged in the review checklist).

---

## 8. Deliverables for the new session
1. A scope confirmation from the user (§1).
2. `scripts/scrape_pearson.py` + `data/raw/pearson/manifest.json` + a completeness table (question paper / mark scheme / examiner report per paper), with gaps reported.
3. `data/processed/spec_9ma0.json` from the official specification (human-review item logged).
4. Processed questions for 9MA0 Paper 3 (Stats + Mech) and the chosen IAL/legacy units, each tagged `qualification` / `unit` / `component` / `status` / `spec_refs`. Out-of-spec questions go to `_excluded/`, with counts.
5. A Stats/Mech taxonomy draft, **reviewed by the user**, and then tags.
6. Audit, examiner-note and tagging outputs, each with its review report.
7. The DB, embeddings, retrieval eval and conversation tests all passing. New review items logged.
8. Updates to `docs/rag-chatbot-plan.md`, `docs/skill-add-papers-pipeline.md` (the Pearson scraping method, the spec filter, and the Stats/Mech adaptations) and `docs/pmt-url-patterns.md`.
