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
