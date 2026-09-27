# Mark Scheme Audit Spec (Phase 2d)

Compares our transcribed mark schemes (`mark_scheme_text` in `data/processed/questions/<paper>_<sitting>.json`) against the official mark scheme text (`data/raw/markschemes/<paper>_<sitting>_MS.txt`, PDF alongside). It separates **official content** from **extractor commentary**, and catches **transcription errors**.

The transcriptions were written from garbled pdftotext output by LLM agents. They are mostly faithful paraphrases, but some contain explanatory asides the extractor added, and a few contain mistakes. Known examples, already fixed:
- "(wait: (a-2)^2=8 directly gives …)" and "a^2 - 4a + 4 = 0" where the official line is a² − 4a − 4 = 0.
- A mix-up between two official methods ("Way 1" gives 728, "Way 2" gives 48 + 680).

## What to produce
Write **only** `data/processed/_ms_audit/<paper>_<sitting>.json`. Never edit the question files; the orchestrator applies your changes with a script.

```json
{
  "_paper": "P1", "_sitting": "June2022",
  "changes": [
    {
      "question_id": "P1_June2022_Q15",
      "type": "editorial",
      "old": "(i.e. the two sector faces plus the three rectangular faces)",
      "new": "[editor: i.e. the two sector faces plus the three rectangular faces]",
      "reason": "Not in official MS; extractor's explanation of the surface-area terms."
    },
    {
      "question_id": "P1_June2022_Q10",
      "type": "correction",
      "old": "k = 0.21",
      "new": "k = 0.12",
      "reason": "Official MS p.14 (MS.txt line 812): 'k = 0.12'.",
      "evidence": "MS.txt line 812 / PDF page 14"
    }
  ],
  "checked": ["P1_June2022_Q1", "P1_June2022_Q2"]
}
```

## Change types
- **`editorial`:** text that isn't in the official mark scheme, i.e. the extractor's explanation, justification, worked arithmetic or commentary. Wrap it, never delete it: `new` = `[editor: <the same text>]`, with the words unchanged apart from the wrapper. Typical signs are "(i.e. …)", "(since …)", "(this is because …)", "note that…", and a derivation spelled out further than the official scheme does.
  - Keep: faithful paraphrase of official content (e.g. "M1: attempts to differentiate using the product rule"), mark codes (M1, A1*, dM1, B1ft, awrt, o.e., cao), official alternative methods ("Way 2", "Alt"), and official guidance notes. Paraphrase is fine; the test is "does the official MS say this?", not "is it word for word?".
- **`correction`:** a factual mismatch with the official scheme, such as a wrong number, sign, expression, mark code, mark allocation, or methods mixed up. Give the fix in `new` and cite `evidence` (MS.txt line number and/or PDF page). **Look at the PDF** (`data/raw/markschemes/<paper>_<sitting>_MS.pdf`, Read tool with `pages`) whenever the .txt is garbled. Signs and powers are often dropped. Only propose a correction you've confirmed.
- Leftover asides like "wait", "hmm" or "actually" should be removed or corrected (type `correction`), with reason "transcription aside".

## Rules for `old`
- `old` must appear **exactly once** in that question's `mark_scheme_text` (or `question_text` when `"field": "question_text"`), copied character for character (escapes as in the JSON: `−` is "−", etc.). The apply script rejects anything that isn't found exactly once.
- Keep `old` as short as possible while still being unique.
- Changes within one question must not overlap.

## Question text too
Apply the same two change types to `question_text`, comparing against the question paper (`data/raw/papers/<paper>_<sitting>_QP.txt` / `.pdf`), and add `"field": "question_text"` to those changes (the default field is `mark_scheme_text`). Question text matters even more, because students see it as the question. Typical extractor additions are "(equivalently …)", "(each chosen because …)", or hints and reformulations that aren't on the paper. Wrap them as `[editor: …]`, or remove them via `correction` if they are plainly wrong.

## Coverage
- Audit **every** question in the paper, and list each one in `checked`.
- Scope: `mark_scheme_text` and `question_text`.
- Maths in our transcription is ASCII (`sqrt`, `^`, `*`); notation isn't changed in this step (that's Phase 2e), so don't propose notation-only changes.

## Validate
```bash
.venv/bin/python scripts/apply_ms_audit.py --check <paper>_<sitting>
```
This checks every `old` is found exactly once and that `editorial` changes only add the `[editor: …]` wrapper. Fix until it prints OK.
