# PMT (Physics & Maths Tutor) URL Patterns

## Base URL
`https://pmt.physicsandmathstutor.com/download/Maths/A-level/Papers/Edexcel/`

## A Level (9MA0) — Pure Mathematics
Papers 1 and 2 are both Pure Mathematics. Paper 3 (Stats/Mech) not yet scraped.

```
Paper-{N}/{QP|MS}/{Session} {Year} {QP|MS}.pdf
```

- N = 1 or 2
- Session = "June" or "October" (use "Oct" failed — "October" also failed for A Level, only "June" works in filenames; Oct papers use "Oct" in our local naming but the PMT filenames on the A Level page used the format the website listed)
- Available sittings: June 2018, June 2019, Oct 2020, Oct 2021, June 2022, June 2023, June 2024

**Viewer URL for linking in pages:**
```
https://www.physicsandmathstutor.com/pdf-pages/?pdf=https%3A%2F%2Fpmt.physicsandmathstutor.com%2Fdownload%2FMaths%2FA-level%2FPapers%2FEdexcel%2FPaper-{N}%2F{QP|MS}%2F{Session}%20{Year}%20{QP|MS}.pdf
```

## AS Level (8MA0)

### Paper 1 (Pure Mathematics)
```
AS-Paper-1/{QP|MS|MA}/{Session} {Year} {QP|MS|MA}.pdf
```
- Available: June 2018, June 2019, June 2020, November 2021, June 2022, June 2023, June 2024
- Note: "November" not "Nov" in the URL

### Paper 2 (Statistics & Mechanics)
**2018 (combined paper):**
```
AS-Paper-2/{QP|MS}/{Session} {Year} {QP|MS}.pdf
```

**2019 onwards (separate booklets):**
```
AS-Paper-2/{QP|MS}/{Session} {Year} {QP|MS} (Stats).pdf
AS-Paper-2/{QP|MS}/{Session} {Year} {QP|MS} (Mech).pdf
```
- Available: June 2019, June 2020, November 2021, June 2022, June 2023, June 2024

## Discovery Method
To find exact URLs for a new exam board/level:
```bash
curl -sk "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers-as/" | grep -oi 'href="[^"]*download[^"]*"' | sort -u
```
This scrapes the page for all download links and reveals the exact path structure.

## Local File Naming Convention
- A Level: `P{N}_{Session}{Year}_{QP|MS}.{pdf|txt}` (e.g. `P1_June2022_QP.txt`)
- AS Paper 1: `ASP1_{Session}{Year}_{QP|MS}.{pdf|txt}`
- AS Paper 2: `ASP2_{Session}{Year}_{stats|mech}_{QP|MS}.{pdf|txt}`
- 2018 combined: `ASP2_June2018_{QP|MS}.{pdf|txt}`

## Examiner Reports (Pearson, not PMT)
PMT does not host Edexcel maths examiner reports (its `MA` folders are PMT's own model answers). The official "Principal Examiner Feedback" PDFs are on Pearson's site:

```
https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/<file>.pdf
```

Filenames change format in 2022 (use a browser-like User-Agent with curl):

| Sitting | Paper 1 | Paper 2 |
|---------|---------|---------|
| June 2018 | `9MA0_01_pef_20180815` | `9MA0_02_pef_20180815` |
| June 2019 | `9MA0_01_pef_20190815` | `9MA0_02_pef_20190815` |
| Oct 2020 | `9MA0_01_pef_20201217` | `9MA0_02_pef_20201217` |
| Oct 2021 (report titled "November 2021") | `9MA0_01_pef_20211216` | `9MA0_02_pef_20211216` |
| June 2022 | `9ma0-01-pef-20220818` | `9ma0-02-pef-20220818` |
| June 2023 | `9ma0-01-pef-20230817` | `9ma0-02-pef-20230817` |
| June 2024 | `9ma0-01-pef-20240815` | `9ma0-02-pef-20240815` |

Local copies: `data/raw/examiner-reports/<paper>_<sitting>_ER.{pdf,txt}` (text via `pdftotext -raw`, which keeps prose in reading order; `-layout` scrambles inline maths into sentences). Mean marks per question only appear in P1 June 2019 and P1 June 2022. Extraction rules: `docs/examiner-notes-extraction.md`.

## Link Catalogue (`data/processed/sources.json`)
Every official paper PMT lists is catalogued with verified links, for citing in chatbot answers. That covers A Level P1–P3 and AS P1–P2, from 2018 to June 2025 plus Specimen/Sample; 64 papers as of 2026-09-25. Each entry has:
- question paper: download URL + PMT viewer URL
- mark scheme: download URL + PMT viewer URL
- Pearson examiner report, where confirmed
- PMT's unofficial model answers, labelled as such

The URLs are scraped from PMT's listing pages, not constructed. Regenerate with:

```bash
.venv/bin/python scripts/build_sources.py --verify   # scrape PMT listings, HEAD-check every link (~2 min)
.venv/bin/python scripts/build_db.py                 # loads it into the `sources` table
```

`build_db.py` fails if any knowledge-base paper has no catalogue entry. Questions join on `sources.paper_id = questions.paper || '_' || questions.sitting`. To add examiner reports for more papers, extend `PEARSON_ER_FILES` in `scripts/build_sources.py`. The script fetches through `curl`, because Python's bundled certificates reject the TLS chain on some networks.

## Pearson past papers (all qualifications): `scripts/scrape_pearson.py` (2026-09-25)
Pearson's past-papers page is an Angular app. Its document list comes from Pearson's **public Algolia search index**; the page embeds the app ID, the search-only key and the index name as hidden inputs (`.algoliaAppId`, `.algoliaAPIKey`, `.algoliaIndexName`). Querying that index directly returns every document's URL, title and tags. That's faster and more complete than rendering the page with headless Chrome (which also works: `--dump-dom`).

- Tags look like `Pearson-UK:Qualification-Family/International-Advanced-Level`, `Pearson-UK:Specification-Code/ial18-mathematics`, `Pearson-UK:Exam-Series/January-2020`, `Pearson-UK:Document-Type/Question-paper` (**case varies**: `Mark-Scheme` as well as `Mark-scheme`), `Pearson-UK:Unit/Paper-S1`.
- **Specification codes:** 9MA0/8MA0 = `maths-2017-as-al` (units `9MA0-01`, `9MA0-02`, `9MA0-31` Stats, `9MA0-32` Mech; June 2018 was a combined `9MA0-03`); IAL 2018 = `ial18-mathematics`; IAL 2013 = `ial-maths`; old UK GCE = `9371` (units tagged e.g. `Unit-S1-(6683)`).
- **IAL unit codes:** the 2018 spec renamed only Pure (WMA11–14). **Statistics and Mechanics kept WST01–03 / WME01–03**, so those codes appear under both specs; the spec tag decides. IAL 2018 WST/WME papers start in Oct 2020, and earlier sittings are tagged 2013.
- **Filenames:** `wma11-01-que-20240110.pdf` / `WMA11_01_que_20200305.pdf` (`que` question paper, `msc`/`rms` mark scheme, where rms is revised, `pef` examiner report), `6663_01R_msc_20130815.pdf`, `9ma0-31-rms-20220818.pdf`; older GCE files are descriptive (`13_M1_January_2006.pdf`, `Question-paper-Unit-C1-(6663)-Paper-1R-June-2014.pdf`). Variants: `01R` (R papers, June 2013/2014), `01A` (IAL time-zone papers from 2025), `UNUSED` (Jan 2022 contingency papers).
- **Locked papers:** documents under `/content/dam/secure/` redirect to the Edexcel Online login (Pearson locks the last ~9 months for mock exams: Oct 2025, Jan 2026 and June 2026 as of 2026-09-25). They are catalogued as 🔒 and not downloaded.
- **Combined documents:** GCE 2005–2009 have "Multiple units" examiner reports / mark schemes (paper id `GCE2008_ALL_<sitting>`).
- Downloads: `https://qualifications.pearson.com` + the URL-encoded `url`. Plain `curl -A "Mozilla/5.0"` works; transient TLS resets happen, so the script retries.

```bash
.venv/bin/python scripts/scrape_pearson.py --catalogue            # query the index, write the manifest
.venv/bin/python scripts/scrape_pearson.py --download [--only RE] # download + pdftotext + sha1, then report
```
Output: `data/raw/pearson/<qualification>/<sitting>/<paper_id>_{QP,MS,ER}.{pdf,txt}`, `data/raw/pearson/manifest.json`, and the completeness table `docs/pearson-coverage.md`. `scripts/build_sources.py` merges the manifest into `sources.json`.
