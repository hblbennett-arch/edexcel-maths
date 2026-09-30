# Clean-room pipeline (branch `commercial-clean-room`)

How the copyright-clean product content is built. The rules and the reasons for them are in
`docs/handoff-clean-room.md` (§3, the abstraction firewall); this file covers what exists and how to run it.
Status: **Phase 1 done and Phase 2 pilot tooling built, 2026-09-30.** Everything runs on the Claude Code Enterprise login (`claude -p`).

## The firewall in one line
Pearson text is read only by **local, deterministic scripts** (regex, counting, the local bge embedding
model). What crosses to the clean side is ids, numbers and codes (`content/facts/`), checked by
`check_facts.py`. **Sessions working on the clean side never print Pearson text into their own context**
(work with ids, counts and codes; anything a human must read goes to `data/clean_private/`, gitignored).

## Content packs
The engine (`chatbot/`) reads everything through one pack: `chatbot/pack.py`, `CONTENT_PACK=<name>` in
the environment or `.env` (default `pearson-private`).

| Pack | Manifest | Data | Use |
|---|---|---|---|
| `pearson-private` | `content/pearson-private/pack.json` | `data/processed/questions.db`, embeddings, `tags.json` | Local study; building the fact layer. Never shipped. |
| `clean` | `content/clean/pack.json` | `content/clean/pack.db` (built), `content/clean/tags.json` | The product. |

Every pack database is `content/schema.sql` plus a `pitfalls` table plus provenance columns
(`provenance`, `blueprint_id`, `generator_model`, `generated_at`, `gate_results`, `reviewed_by`,
`reviewed_at`, `review_decision`, `review_notes`) on `questions`, `question_parts` and `pitfalls`
(`chatbot/pack.create_schema`). `scripts/build_db.py` builds the Pearson pack with provenance
`pearson-private` on every row.

## Commands

| What | Command |
|---|---|
| Build the clean pack (then runs the licence gate) | `.venv/bin/python scripts/clean/build_pack.py` |
| Licence gate (every commercial pack) | `.venv/bin/python scripts/clean/check_provenance.py` |
| Gate self-test: must FAIL | `.venv/bin/python scripts/clean/check_provenance.py --pack pearson-private` |
| Fact layer | `.venv/bin/python scripts/clean/build_facts.py` |
| Fact-layer check | `.venv/bin/python scripts/clean/check_facts.py` |
| Error-code frequencies (+ private sample sheet) | `.venv/bin/python scripts/clean/match_errors.py [--threshold 0.70] [--samples]` |
| Run gates G1 and G7 on items | `.venv/bin/python scripts/clean/gates.py [--dry] content/clean/items/*.json` |
| Blueprints (exam-style in the 9MA0 mix, drills, 6 mocks) | `.venv/bin/python scripts/clean/make_blueprints.py` then `scripts/clean/check_blueprints.py` |
| Generate items (Opus 5.5 via `claude -p`) | `.venv/bin/python scripts/clean/generate.py --select pilot [--limit N] [--full] [--parallel 5] [--skip-existing]` (`--dry` prints one prompt) |
| Model gates on existing items | `scripts/clean/gate_solve.py` (G3), `gate_marking.py` (G4 + G5), `gate_tags.py` (G6), each taking item files |
| G2 / G8 self-test | `.venv/bin/python -m eval.gates_maths_style_selftest` |
| Pass rates, reasons, cost per item | `.venv/bin/python -m eval.clean_gates_report` |
| Review UI (G9): queue by risk, accept / edit / reject | `.venv/bin/python scripts/clean/review_server.py [--items DIR] [--port 8766]` → http://127.0.0.1:8766 |
| Gate self-test | `.venv/bin/python -m eval.gates_selftest` (about 20 s) |
| Engine evals on the clean pack | `CONTENT_PACK=clean .venv/bin/python -m eval.practice_eval` (every eval runs the licence gate first on a commercial pack) |

## Files

| Path | Contents | Crosses the firewall? |
|---|---|---|
| `content/facts/parts.json` | Per part: marks, skills, question type, mark-code sequence, command words, answer forms, figure, difficulty | Yes: ids, numbers and codes only |
| `content/facts/aggregates.json` | Distributions per question type, skill and qualification; skill and group co-occurrence (≥ 3 questions); `mix_9ma0`: how many topics real 9MA0 questions combine, per component (the bank's target mix) | Yes |
| `content/facts/papers.json` | 9MA0 paper-level facts: per paper, each question's number, marks, part count and type | Yes |
| `content/facts/error_frequency.json` | (skill, error code, weighted count, notes) and (question type, code, ...); unmatched cluster sizes | Yes |
| `content/error_codes.json` | Seed error taxonomy: 267 codes in our words (draft, for user review) | Our own work |
| `content/novelty_whitelist.json` | Stock phrases G7 ignores (draft, for user review) | Our own work |
| `content/blueprints/exam.jsonl`, `drills.jsonl`, `mocks.jsonl` | 601 exam-style, 452 drill and 84 mock-question blueprints: ids, codes and numbers only (`check_blueprints.py`) | Yes |
| `content/prompts/generate_system.md`, `checks_language.md` | The generator's house-style prompt and the G2 checks language, in our words | Our own work |
| `data/clean_private/error_match_samples.md` | Pearson notes next to their matched code, for the user to mark | **No**: private, gitignored |

## Item format (`content/clean/items/<id>.json`)
One generated item per file: the question, our mark scheme, worked solution, hints and pitfalls, plus
provenance. See `eval/fixtures/original_items.json` for three complete examples.
```json
{
 "id": "cr-0001", "blueprint_id": "bp-...", "question_type": "<tags.json question type>",
 "component": "pure|stats|mech", "tier": "starter|core|stretch|exam", "stem": "LaTeX or null",
 "parts": [{
   "label": "a", "marks": 3, "text": "... (3)", "command": "find|show-that|hence|...",
   "skills": ["<tags.json skill ids>"], "forms": ["exact", "sf-3"],
   "mark_scheme": [{"code": "M1", "for": "what earns it", "notes": "accept/reject notes",
                    "depends_on": "<earlier part label, for an A mark with no M in this part>",
                    "ft_of": "<what an ft mark follows>"}],
   "alternatives": [{"name": "Way 2", "marks": [ ...same shape... ]}],
   "solution": [{"step": 1, "working": "..."}], "answers": [{"name": "x", "expr": "3/2"}],
   "hints": ["..."]}],
 "pitfalls": [{"part": "a", "step": 2, "error_code": "<error_codes.json id>", "text": "...", "says_common": false}],
 "provenance": "original", "generator_model": "...", "generated_at": "...",
 "gate_results": {"G1": {"pass": true}, "...": {}},
 "review": {"by": "...", "at": "...", "decision": "accept|edit|reject", "reason_code": "...", "notes": "...",
            "minutes": 2.5, "edited_fields": ["parts.0.text"], "regate_needed": true}
}
```
`build_pack.py` loads only items whose review decision is accept or edit. The licence gate also needs
G1 to G8 all passed.

## Blueprint format (`content/blueprints/*.jsonl`, one per line)
```json
{"id": "bp-pure-<type>-001", "kind": "exam|drill|mock", "question_type": "...", "component": "pure",
 "total_marks": 8, "band": "two-topics", "difficulty": "accessible|standard|challenging|starter|core",
 "context_theme": "none|<our theme>", "no_calc_tech": false, "marks_rule": "median|max|min|skill-mode",
 "parts": [{"label": "a", "skills": ["..."], "marks": 4, "codes": "M1 A1 dM1 A1", "command": "hence",
            "forms": ["exact"], "error_codes": [{"code": "...", "loses": "M", "n_notes": 12}]}],
 "source_fact_ids": ["<3 real question ids>"], "source_rule": "same-type-same-shape[+union]|shared-skills|skill-parts"}
```
A blueprint is built from `content/facts/` only (`make_blueprints.py`). An exam-style blueprint blends 3 real
questions of the same type and shape: per part, the median marks (or the max in pure / min in stats and mech, to
match 9MA0 totals), the skills shared by 2 of the 3 (or by any of them, the "+union" blends, used only where a mix
band needs more topics), the majority command word and a mark pattern that adds up. Error codes per part are
ranked by how well their definitions match the part's skills (local embeddings of our own texts), then by
frequency. The set is chosen greedily so each component matches 9MA0: topic-mix band, marks per question and
parts per question (TVD < 0.15). Measured 2026-09-30: pure 0.001 / 0.132 / 0.015, stats 0.000 / 0.033 / 0.033,
mech 0.005 / 0.041 / 0.008. Mock papers copy the slot shape (marks, parts, type per question) of a recent real
paper, with fresh blueprints adjusted to the exact marks. No single-source blueprints are used.

## Gates: status

| Gate | Status | Self-test (2026-09-29) |
|---|---|---|
| Licence (`check_provenance.py`) | Built | Empty clean pack passes; pearson-private fails; each planted fault caught (banned phrase, Pearson provenance, a failed gate, a rejected item, examiner_notes rows) |
| G1 structure | Built (`gates.py`) | 6/6 planted faults caught; 3/3 originals pass |
| G7 novelty | Built (`gates.py`) | Rejects 40/40 verbatim copies and 40/40 number-changed variants; 3/3 originals pass (flagged for review) |
| G2 maths (`gate_maths.py`) | Built | Fixtures pass; 21 planted faults fail (wrong derivative, missing/extra roots, rounding, binomial, injection, …) |
| G8 style (`gate_style.py` + `katex_render.js`) | Built | Fixtures pass; 16 planted faults fail. Marks-range breaches only warn for types with < 5 real questions |
| G3 blind solve (`gate_solve.py`, Sonnet 5.5) | Built | Measured in the pilot |
| G4 mark-scheme tests + G5 pitfalls (`gate_marking.py`, Sonnet 5.5) | Built | Measured in the pilot |
| G6 tags (`gate_tags.py`, Haiku 4.5) | Built | Measured in the pilot |
| Bank-level G8 (`check_blueprints.py`) | Built | Blueprint set matches the 9MA0 mix (TVDs above) |

## Lessons (keep for later changes)
- **Mark-code extraction:** try the mark lines, then the "M1: ..." notes lines, then all codes. Take the
  shortest prefix whose values add up to the part's marks (later codes are alternative methods or notes),
  and prefer a candidate where every A and dM follows an M. Commentary such as "1st A1 for 7" otherwise
  gets read as mark lines. Result: 7,030/7,055 clean, 17 irregular, 8 unresolved.
- **Embedding similarity measures topic, not copying.** From-scratch originals on common topics reach
  cosine 0.92 against real questions; number-changed variants range from 0.86 upwards. Shared 8-word
  runs separate them cleanly: variants share at least 5 (median 95), originals share 0 once the stock
  phrases are whitelisted. So G7 rejects on 8-grams, Jaccard and shared numbers, and uses cosine only
  with a structural match (same marks per part) or above 0.97.
- **Maths-only 8-grams are not expression:** "x a 2 y b 2 r 2" is the circle equation. An 8-gram with ≥ 6
  maths tokens is ignored.
- **`np.load` on an `.npz` re-reads the file on every `data["vecs"]` access.** Load the array once.
- **Most first-run gate failures were harness bugs, not bad questions** (smoke test, 2026-09-30). Models write
  labels as "(a)", "Part a" or split "b(i)/b(ii)"; they drop "*" and "ft" from mark codes; a blind solver writes
  answers as prose ("P(X<=3)=0.0601 > 0.05, so ..."). Normalise labels (`gate_marking.norm_label`), compare marks by
  code and value (`_mark`), and pull numbers out of prose answers (`gate_solve.values_in`) before comparing.
- **Model gates need a severity:** the blind solver lists "tight but workable" points too. Only "blocker" problems
  fail G3; "minor" ones become review flags. Likewise G6 fails only when the retagger picks a different topic;
  same-topic, different-skill tags are flags (the handoff's rule is >= 95% agreement at bank level).
- **Stock maths phrasing trips 8-gram checks:** chain-rule lines ("ds/dt = ds/dr x dr/dt"), units and set-up
  phrases ("circular cylinder of radius r cm and height"). Derivative tokens and units count as maths tokens, and
  the stock phrases are on the whitelist. "Distinctive" numbers are those in at most 2% of real questions (14 and
  500 aren't); the numbers rule is a weak signal next to the 8-grams.
- **Keep every model gate's raw output in the item** (the solver's answers, the scripted responses and awarded
  vectors), so a comparison fix can be re-scored offline without new calls.
- **Checking an embedding-match threshold without reading the notes:** only look at score distributions,
  and write the samples to a private file for the user to mark.

## Next
1. The user's decisions from `docs/review-checklist.md` §28.
2. Pilot: `generate.py --select pilot --full` (60 items: 28 pure and 12 stats exam-style in the 9MA0 mix, plus 20 drills), then `eval.clean_gates_report`; fix the commonest failure causes; review UI (G9).
3. Tutor on the clean pack (pack-aware prompts and retrieval), then scale in batches (≤ 5 parallel calls).
