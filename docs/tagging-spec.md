# Tagging Spec (Phase 2f): question types + part skills

Each question gets **one question type** (narrow: "the same kind of question"). Each **part** gets **every skill it tests** (broad), usually 3–6. The bot uses skills to recommend practice for the exact step a student struggled with, ordered easiest first, so thorough skill tags matter more than anything else here.

## Inputs
- **Vocabulary:** `data/processed/_vocab_compact.md` (141 skills in 31 groups, plus 45 question types). This is the only list you may use. The full definitions live in `data/processed/tags.json`.
- **Draft question types:** `data/processed/_draft_question_types.json` (`question_id → type`). Use these as given. If one is clearly wrong, you may change it, but list every change in your final reply with a reason.
- **Questions:** `data/processed/questions/<paper>_<sitting>.json`. Tag from each part's `text` **and** `mark_scheme`; the M/A/B marks show what's actually rewarded.

## Output
Write `data/processed/tags_assigned/<paper>_<sitting>.json`:
```json
{ "_paper": "P1", "_sitting": "June2022",
  "questions": {
    "P1_June2022_Q15": { "question_type": "optimisation-constrained-shape",
      "parts": { "a": ["sector-area", "mensuration-formulae", "eliminate-variable-using-constraint", "show-that-given-answer"],
                 "b": ["differentiate-negative-and-fractional-powers", "set-derivative-zero-and-solve", "solve-power-equation"],
                 "c": ["second-derivative", "second-derivative-test", "explain-with-reason"] } } } }
```
- Part keys are the part labels exactly as in the question file (`"a"`, `"b(i)"`, `"ii"`). A single-part question (label `null`) uses the key `"-"`.
- Every question in the paper and every part must be present.

## Rules
- **Tag every skill a part genuinely tests**, including the "small" ones. For example, a part that differentiates with the product rule then solves gets `product-rule`, the relevant `differentiate-…` skills, and `set-derivative-zero-and-solve` if it solves f′ = 0.
- **Include cross-cutting exam skills when the mark scheme rewards them:** `show-that-given-answer` for "show that" / given answers; `use-hence-previous-result` for "hence"; `reject-invalid-solutions`, `exact-form-answers`, `set-notation-answers`, `accuracy-units-and-rounding` and `explain-with-reason` when a mark depends on them.
- **Don't tag skills the part doesn't need,** e.g. a later step's method.
- **Aim for ≥ 2 skills per part.** One is fine for a genuinely one-step part (e.g. a 1-mark "state the value").
- **No invented skills.** If something important isn't covered, add it under "Suggested new skills" in your final reply (name + parts), and tag the closest existing skill.
- The order within a part's list doesn't matter; no duplicates.

## Validate
```bash
.venv/bin/python scripts/check_tags.py <paper>_<sitting>
```
This checks:
- every question and part is present;
- every tag exists in `tags.json`;
- there are no duplicates.

It also prints skills per part and lists thin parts. Fix until OK. Never run `scripts/build_db.py` while other taggers are working.
