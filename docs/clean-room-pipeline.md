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
- **Pilot round 1 (60 items, 2026-09-30): 10 passed everything; $2.14 per passing item.** Causes, in order:
  - **G7, 26 items: stock exam phrasing.** Rubric wording ("giving your answer to 3 significant figures", "where
    a and b are rational numbers") and set-up wording ("the finite region R is bounded by…"). Whitelisted for user
    review, which took G7 from 34 to 46 of 60 passing, with copies and variants still 40/40 rejected. A few were
    genuine mark-scheme idioms the model remembered; the prompt now forbids those, and a G7 retry is told which
    fields overlapped, never the matched text.
  - **G8, 18 items: command wording and answer forms.** The model paraphrased the blueprint's command ("Using your
    answer…" for "Hence"), or listed a form the text never asks for. The prompt now gives the exact words to use.
  - **G1, 8 items: marks and parts changed from the blueprint.** The prompt now says both are fixed.
  - **G3/G4 on the rest: mostly format, not maths.** Units in the solver's answer, coefficients against a whole
    expression, and 1-in-the-last-figure rounding. G3 now strips units, allows 1 unit in the last figure, and
    sends mismatches to a judge call that sees both answer sets.
  - **G4 script-versus-marker disagreements.** A second marker (Opus 5.5) marks the disputed scripts. If both
    markers agree, the scheme is consistent and the script's design was off: a flag. If they disagree, the scheme
    is ambiguous: a fail.
- **Keep every model gate's raw output in the item** (the solver's answers, the scripted responses and awarded
  vectors), so a comparison fix can be re-scored offline without new calls.
- **Checking an embedding-match threshold without reading the notes:** only look at score distributions,
  and write the samples to a private file for the user to mark.

## Next
1. The user's decisions from `docs/review-checklist.md` §28.
2. Pilot: `generate.py --select pilot --full` (60 items: 28 pure and 12 stats exam-style in the 9MA0 mix, plus 20 drills), then `eval.clean_gates_report`; fix the commonest failure causes; review UI (G9).
3. Tutor on the clean pack (pack-aware prompts and retrieval), then scale in batches (≤ 5 parallel calls).

## Product layer (added 2026-09-30, after the market research)

The strategy in `docs/market-research-product-strategy.md` moves the headline from "mark my working" to
**examiner literacy**. These modules are the shared foundations; they are board-agnostic so a new board is a
profile file, not a rewrite.

| What | Where | Notes |
|---|---|---|
| Board profile | `content/boards/edexcel-9ma0.json` | Notation (M/A/B/dM/ddM/dB, ft, *), dependency rules, the conventions glossary in **our own words** (M, A, B, dM, ddM, ft, cso, cao, awrt, oe, isw, show-that, dependency, bald answer: each with `name`, `short`, `explain`, `write_to_earn`), answer forms, paper structure, legal profile. `BOARD_PROFILE=<id>` overrides the default. |
| Mark-code ontology | `chatbot/marks.py` | `parse("dM1")` -> canonical `Mark(kind, worth, awarded, ft, show_that, cso, cao)`; `render`, `withheld`, `chain` (which marks depend on which), `implied_losses` (losses the dependency rules force), `explain(code, part=short|explain|write_to_earn)`, `glossary`, `vector_summary`. Canonical kinds: METHOD, ACCURACY, INDEPENDENT, DEPENDENT_METHOD, DOUBLY_DEPENDENT_METHOD, DEPENDENT_INDEPENDENT, REASONING, EXPLANATION, PROCESS, COMMUNICATION, MARKING_POINT, LEVEL_BAND (the last six are for other boards and subjects). |
| Marking events | `chatbot/events.py` | SQLite at `data/users/events.db` (gitignored under `data/*`). `record(user_id, source, item_id, part, decisions)` for `be-the-examiner`, `mark-my-working` and `mock`; `leakage_profile(user_id)`: lost marks by family, error code and skill, plus examiner accuracy. Opaque user ids only. |
| Self-test | `.venv/bin/python -m eval.marks_selftest` | Parses every code in every clean item (408 today), checks chains, implied losses, round trips, convention texts (no board names) and the events aggregation. |

Design rules carried from the research: every mark decision is stored with its **mark type and error code**
(so the leakage profile exists from the first user); a marker returns **per-mark decision + quoted evidence +
confidence**, with transcription as its own confirmable stage; strict rubric prompting over-penalises, so the
marker is told to give partial credit as the scheme allows.

### "Be the examiner" (built 2026-09-30, no model calls)

| What | Where |
|---|---|
| Exercise builder and feedback | `chatbot/examiner.py`: `load_items()` (pack.db when it has rows, else gate-passed item files), `exercises()`, `public_view()`, `reveal()`, `to_decisions()`, `record()`, `pick_next()` |
| Page and API | `GET /examiner` (`chatbot/static/examiner.html`); `GET /api/examiner/glossary`, `GET /api/examiner/next?user=&done=&kind=`, `POST /api/examiner/submit`, `GET /api/examiner/profile?user=` (all in `chatbot/web.py`) |
| Self-test | `.venv/bin/python -m eval.examiner_selftest` |
| Try it | `.venv/bin/python -m chatbot.web --offline --no-browser --port 8765` then open http://127.0.0.1:8765/examiner |

Every usable G4 scripted answer becomes an exercise: the student sees the question, the script and the scheme
lines, awards or withholds each mark, then sees the reference verdict with an explanation built from the scheme
line, the conventions glossary, the dependency chain ("unavailable because the M1 before it was lost") and, for
pitfall scripts, the item's pitfall text. Today: **182 exercises over the 25 gate-passed pilot items** (123 pitfall,
25 correct, 25 partial, 9 alternative method). Each submission is one `be-the-examiner` event per part.

Lessons:
- G4 vectors drop suffixes on lost marks (`A0` for an `A1*` or `A1ft` line, 33 cases): align by position and use
  `awarded` only; never compare code strings.
- All alternative-method scripts have vectors the same length as the main scheme, so "which Way" is decided by the
  script's kind, not by length.
- Two pitfalls can share one error code on an item; a G4 response links to the code only. The earliest-step pitfall
  of the same part is attached. A `pitfall_index` on each G4 response would remove the guess (generator change).
- `marks.chain()` treats a dM as depending on the nearest M only. Where a scheme says "depends on both M marks", a
  `depends_on` position list on the scheme line would make the chain exact (item-format change to consider).
- `pack.db` stores schemes as flattened text without alternatives, so `examiner.py` prefers the item file whenever
  one exists for a pack id. When the pack becomes the only source, store the structured scheme JSON in the pack too.

### Marker v2: "Mark my working, explained" (built and measured 2026-09-30)

| What | Where |
|---|---|
| Marker | `chatbot/marker.py`: `transcribe(text)` (typed), `transcribe_image(path)` (photo -> LaTeX lines with per-line confidence, `needs_confirmation=True`), `final_answer_facts(item, part, lines)` (sympy pre-checks via `gate_maths`, never raise), `mark(item, part_label, working)` (one `claude -p` call on Sonnet 5.5, step `marker-v2`), `enforce_dependencies`, `to_decisions` (rows for `chatbot.events.record`) |
| Prompt | `content/prompts/marker_system.md` (ours; byte-identical across calls). Liberal partial credit, dependencies, ft/cso/cao/awrt/oe/isw, sympy facts as evidence not verdicts; per mark: code, quoted evidence, reason, convention, error code, `rewrite_to_earn`, confidence |
| Eval | `.venv/bin/python -m eval.marker_eval` (baseline / pilot / full / consistency / report; cache in `logs/marker_eval_cache.json`; $40 cap read from the call log). Output `logs/marker_eval_20260930.json` |
| Self-test (no calls) | `.venv/bin/python -m eval.marker_selftest` |

**Measured 2026-09-30** on the 25 gate-passed items (182 reference scripts, 1,408 marks; reference = the G4
design where the G4 marker agreed, else the G4 markers' vector):

| Metric | G4 marker (baseline) | Marker v2 |
|---|---|---|
| Per-mark agreement | 99.9% | 98.0% |
| Exact-vector agreement | 99.5% | 90.7% |
| Method / accuracy / independent marks | 99.8 / 100 / 100 | 97.6 / 98.2 / 98.9 |
| Withheld marks with reason / rewrite / error code | – | 100% / 100% / 95.3% (363 withheld) |
| Re-marking consistency (6 items, 48 scripts) | – | 93.8% identical vectors, 1.5% per-mark flips |
| Cost, time per script | – | $0.025, ~9 s |

**Caveat, always print it with the numbers:** the reference was produced by the G4 marker (Sonnet 5.5), so the
baseline is near-tautological and optimistic; v2 is the independent measurement. Every disagreement is on a
pitfall script (correct, alternative and partial scripts: 100%). Of 28 disagreeing marks, 18 are v2 stricter and
13 of those sit on one item where G4 scripts state printed answers bald in a show-that part not under test; the
scheme's own note supports v2 there. The true accuracy figure still needs human second-marking of real student
scripts before it is published (strategy §4.6).

**Adopted** (rule: v2 >= baseline - 2 points, and every withheld mark explained), marginally. Spend: 230 calls, $5.42.

**Extended 2026-10-01 00:05** to the 10 items that passed G1-G8 that evening (72 more scripts): combined 35 items, 254 scripts,
1,824 marks: v2 per-mark **97.9%** (baseline 98.4), exact-vector 89.8 (91.3); method / accuracy / independent 97.0 / 98.4 / 99.1;
new items only 97.4 (their baseline was 93.0, because several "agreed" scripts were agreed via the Opus second marker). Every
withheld mark still has a reason and a rewrite; 95.5% carry an error code. The adopt rule holds exactly on the line. All 9
new-item disagreements are v2 more lenient on a method mark, so look at those G4 M0 designs. Report `logs/marker_eval_20261001.json`;
spend $1.59 ($0.022 a script).

Lessons:
- The G4 reference is not an independent accuracy standard. G4 scripts should not state printed answers bald in
  parts not under test (writer-prompt change), or those parts should be excluded from the reference.
- 0.3% of decisions had a reason contradicting the code. `marker._contradicts` now flags them
  (`self_contradiction: true`, confidence capped at 0.5) so the UI can say "check this one".
- Error-code coverage is 95%: the gaps are method marks with no fitting candidate and dependency losses. Consider a
  generic "method-not-shown" code; the dependency override already inherits the root cause's code.
- Sympy facts are cheap (< 0.1 s) and decisive for "decimal given, exact form required".
- One call per script at $0.025 is cheaper and cleaner than batching a whole item.

### "Mark my working" page (built 2026-09-30)

| What | Where |
|---|---|
| Orchestration | `chatbot/working.py`: `catalogue()` (gate-passed items with our type titles), `submit(user, item_id, part_label, text)` (transcribe -> `marker.mark` -> one `mark-my-working` event per part), `profile_view()` (leakage profile with error-code definitions and skill titles) |
| Page and API | `GET /mark` (`chatbot/static/mark.html`); `GET /api/mark/catalogue`, `POST /api/mark/submit`, `GET /api/mark/profile?user=` |
| Self-test (no calls) | `.venv/bin/python -m eval.working_selftest` |

The page shows the transcript ("this is what we read"), then one row per scheme mark: awarded or withheld code,
the scheme line, the quoted evidence, the reason, the convention in one line and, for a withheld mark, "Write this
to earn it". A "check this one" badge appears when confidence < 0.5, the mark was overridden by the dependency rule
or the reason contradicts the code. The same browser id is shared with `/examiner`, so one leakage profile covers
both. Smoke test: a correct script scored 5/5; the same script with the integrand's sign flipped scored 2/5 with
error code `area-between-wrong-subtraction` and a rewrite line; $0.02 to $0.025 a marking.

Lessons: `reason` text can be cut mid-sentence by the model (render as-is, consider a larger output budget);
`cost_usd` is per call, so a whole-question marking stores it on the first part's event only.

### Question-type playbooks (built 2026-09-30, 73/73)

| What | Where |
|---|---|
| Generator | `.venv/bin/python scripts/clean/make_playbooks.py [--dry] [--list] [--types a,b] [--limit N] [--parallel 5] [--force] [--max-usd 60]` (Sonnet 5.5, steps `playbook`, `playbook-retry`) |
| Prompt | `content/prompts/playbook_system.md` (ours), with the conventions glossary appended at runtime |
| Output | `content/clean/playbooks/<question-type>.json`: title, what_it_asks, typical_structure, mark_pattern, where_marks_leak (error code, mark family, text), write_to_earn, check_before_you_leave, skills, related_types; plus provenance, model, cost, attempts, facts summary, checks, `review.decision: null` |
| Checks (no calls) | `.venv/bin/python -m eval.playbooks_check`: G7 copy check per text field, KaTeX render, banned words (board names, examiner(s), past paper), error codes real and in the type's facts, frequency words only for codes with >= 10 matched notes, mark codes in the M1/A1/dM1 form |

Facts in the prompt come only from `content/facts/*`, `content/clean/tags.json`, `content/error_codes.json` and the
board file. Measured: 73 written, 0 failing; 46 first time, 27 after one retry; $5.64 in total ($0.076 a type).
Every playbook carries a cosine flag (0.81 to 0.91 against some corpus item): topic similarity, expected for prose
about a question type, so that flag is uninformative here. Seven thin types (< 5 real questions: the two
hypothesis-test types, log-coded regression, three projectile types, distribution-model-vs-data) have indicative
distributions only, and the file says so. Practice-item links exist for 11 types today; they fill in as the bank grows.

Lessons:
- G7 works on prose when each field is treated as a pseudo-part; the one copy failure (a stock mark-scheme idiom)
  was localised by re-running G7 per sentence of our own text and fed back without quoting anything.
- Frequency-word checks must be sentence-scoped and require an error word, or "common ratio" trips them.
- The banned-word scan must cover content fields only; stored gate reasons legitimately mention the corpus.
- Codes inside `$...$` and glued suffixes (`A1cso`) needed extra style rules.
- Keep first-attempt check results too, so retry causes stay recoverable.
- Error-code matching is noisy at low counts (`wrong-final-accuracy` tops 67/73 types). The leak lists need the
  user's eye (checklist §32).

## Learn layer: solution levels and interactive scenes (built 2026-09-30, 22:40 to 00:45, unsupervised)

Spec: `docs/learn-layer-spec.md`. Purpose: a student chooses how slowly a solution is explained, and, where a
picture helps, sees and manipulates the idea the question tests. Everything is generated from our own items with
our own prompts, gated deterministically, and stored on the item or beside it.

### Solution levels (`parts[i].solution_levels`: brisk / standard / every_step)

| What | Where |
|---|---|
| Generator | `.venv/bin/python scripts/clean/enrich_solutions.py --items all [--parallel 5] [--force] [--dry] [--max-usd 40]` (Sonnet 5.5, one call per part, steps `levels`, `levels-retry`) |
| Prompt | `content/prompts/levels_system.md` |
| Gate (deterministic) | `scripts/clean/gate_levels.py` (`gate_levels(item)`; result stored as `gate_results.GL`): KaTeX render, G7 copy check, `secures` codes in the scheme and brisk covers each code exactly once in order, every answer found (sympy) in the last line of each level, non-empty `why`, every_step at least as long as standard, banned words |
| Check (no calls) | `.venv/bin/python -m eval.levels_check` |

Measured: 25 items, 49/49 parts, all pass GL; 37 first time, 12 after one retry; $1.80 (about $0.035 a part).
Average lines: standard 3.6, brisk 3.2, every_step 14.0. A part's `levels_meta` records model, cost, attempts and
our gate messages (scrubbed of any board name, because G8 scans every string in the item).

Lessons: `answers` also holds intermediate constants used by G2, so "every answer on the last line" is a warning when
the answer sits a line or two earlier; ask the model to put numbers before units and to restate every answer on the
last line (that removed most retries); schema-constrained one-shots got sporadic safeguard flags on innocuous maths
(a trig substitution, resistors), cleared by one task sentence at the top of the user turn; G7 cosine flags on
solution text are noise (48/49), only the 8-gram reject matters.

### Interactive scenes (`content/clean/scenes/<item-id>.json`, rendered with JSXGraph)

| What | Where |
|---|---|
| Generator | `.venv/bin/python scripts/clean/make_scenes.py --items all [--parallel 5] [--force] [--dry] [--max-usd 40]` (Sonnet 5.5; retry with our messages; then one Opus 5.5 attempt; steps `scene`, `scene-retry`, `scene-opus`) |
| Guide annotator | `.venv/bin/python scripts/clean/annotate_scenes.py --items all` (adds the `guide` block: legend, how to interact, link to the question; steps `guide*`) |
| Prompts | `content/prompts/scene_system.md`, `content/prompts/guide_system.md` |
| Gate (deterministic) | `scripts/clean/gate_scene.py FILE... [--require-guide]` (`gate_scene(scene, item)`): expression grammar via sympy (free symbols, no implicit multiplication, finite at 9 sample points), ids, types, board and param sanity, 2 to 5 steps, links to scheme codes and error codes, KaTeX, banned words, G7, and the guide's coverage rules |
| Renderer | `chatbot/static/scene.js` (`renderScene`, `renderSceneWhenVisible`); whitelist compiler shared with `chatbot/static/scene_compile.js` (Node-testable; the self-test checks the two copies are byte-identical). The model never writes code. |
| Checks (no calls) | `.venv/bin/python -m eval.scene_selftest` (17 planted faults caught; Node compile and reject tests), `.venv/bin/python -m eval.scenes_check` |
| Standalone page | `chatbot/static/scene_test.html` (open via file://, needs the CDN) |

Measured: 25 items, 24 applicable (the refusal is a pure symbol-manipulation show-that), 31 scenes, approach
graphical 15 / model 13 / algebraic-check 3; every scene has a slider, 5 also a glider; all pass the gate; $1.96
(15 first time, 7 after a retry, 3 needed Opus). The area readout was checked by hand in the browser (7.33 for the
integral from 1 to 3; 20.8 at 6), and the normal-distribution and differential-equation scenes render correctly.

Lessons: JSXGraph fills curves at opacity 1 by default when a fill colour is set, so the base attributes now set
`fillOpacity: 0` (whole parabolas were painted before the fix); the renderer's title is optional (`showTitle:false`)
because the viewer prints it; statistics scenes need live-value helpers the grammar lacks (a binomial cumulative
probability has no legal placeholder; Opus worked round it with a `floor` sum), so `{binom_le(n, p, k)}` or a
`value` on polygon bars is the next grammar addition; models sometimes name colours in step text, so hue tokens must
stay stable; keep an `errors_history` on the scene record so retry causes stay recoverable.

Statistics helpers (added 30 Sept, 23:30): the grammar now has `binom_pmf(n, p, k)`, `binom_le(n, p, k)`,
`binom_ge(n, p, k)` and `norm_cdf(x, mu, sigma)`, `norm_pdf(x, mu, sigma)`, `norm_inv(q, mu, sigma)`, all
three-argument (`SCENE_ARITY` in the compiler). They live in the identical compiler sections of
`chatbot/static/scene_compile.js` and `chatbot/static/scene.js`, in `scripts/clean/gate_scene.py` (sympy side),
`content/prompts/scene_system.md` and `docs/learn-layer-spec.md`. The binomial scene was regenerated to use them
($0.15); the `floor` workaround above is no longer needed.

### Pages

| Page | Route | Notes |
|---|---|---|
| Learn (catalogue and viewer) | `/learn`, `/learn?item=ID&tab=solution|graphical|scheme|pitfalls` | Depth selector Brisk / Standard / Every step, plus **Walk me through it** (one line at a time, the `why` behind a "Why?" disclosure so the student tries first, Next line / Show all / Start again, right arrow or `n`, part headings, a completion note that points to the brisk version; depth and walk-through remembered in localStorage); Graphical tab renders scenes lazily (never while hidden); Mark scheme lines with the convention in one line; Pitfalls; Practise footer to `/mark?item=`, `/examiner` and the type's playbook. `chatbot/learn.py`, `chatbot/static/learn.html`. |
| Playbooks | `/playbooks`, `/playbooks?type=ID` | Index by topic with search; leak cards with error-code definitions; checklist ticks kept per type in localStorage; thin types badged "indicative". `chatbot/static/playbooks.html`. |
| Static files | `/static/<file>` | Only files in `chatbot/static`, single segment, whitelisted extensions. |
| Timed mock | `/mock`, `/api/mock/papers`, `/api/mock/paper?id=`, `POST /api/mock/submit` | `chatbot/mock.py` (`papers()`, `paper(id)`, `submit(user_id, paper_id, answers, elapsed_seconds)`), `chatbot/static/mock.html`. Papers: the files `content/clean/mocks/<paper>.json` (`{"id","title","marks","minutes","questions":[{"q_num","item_id","marks","gates_passed"}]}`; `mock-1-P1` so far, 15 questions, 100 marks, 120 minutes; counts of generated and gate-passed questions: see `eval.clean_gates_report` and the review UI's Papers overlay) plus `practice-pure-50`, assembled at load time from gate-passed pure items by the 9MA0 mix bands (TVD from the pure mix 0.11 at build; the self-test requires < 0.25). Page: countdown, auto-submit at zero, resume from localStorage, results by question / mark family / skill, a grade estimate (2026 boundaries A* 254 / A 210 / B 173 / C 136 of 300 scaled to the paper's marks; D and E extrapolated one B→C step each below C) and a "See the marking" link per question. Submit marks each part with marker v2 (one call per part; smoke test $0.034). Self-test: `.venv/bin/python -m eval.mock_selftest`. |
| Mark-leakage profile | `/profile`, `/api/profile?user=`, `/api/profile/exercise?key=` | `chatbot/profile.py` (`view(user_id)`: totals, by family, top error codes each with drills (gate-passed items whose pitfalls carry the code), "Be the examiner" exercises (`/examiner?exercise=item::script`) and the playbooks that mention the code; top skills; 8-week trend; examiner accuracy; `plain_summary(v)`, two or three deterministic sentences), `chatbot/static/profile.html`. "My profile" links on `/mark` and `/examiner`. Self-test: `.venv/bin/python -m eval.profile_selftest`. |
| Start page | `/start` | `chatbot/static/start.html`: six feature cards, "how it works", the independence disclaimer. The name is the constant `PRODUCT_NAME = "[Product name]"` at the top of the script; replace it once the brand is chosen. |
| How marks are awarded | `/marks`, `/api/marks/glossary` | `chatbot/static/marks.html`: an interactive dependency-chain diagram for `M1 A1 M1 dM1 A1*` (withhold a mark and the marks that depend on it go too), the papers table, one card per convention from the board profile's glossary (`chatbot/marks.py`). Self-test for both static pages: `.venv/bin/python -m eval.start_selftest`. |
| Photo upload on Mark my working | `POST /api/mark/photo` | `working.transcribe_upload` -> `marker.transcribe_image`; the student confirms or edits the transcript (low-confidence lines amber) before marking; `transcript_confirmed` recorded on the event. HEIC is rejected (iPhone users choose "Most Compatible"). Smoke test: a rendered image transcribed at 0.93 and marked 5/5 for $0.03. |
| Self-tests | `eval.learn_selftest`, `eval.photo_selftest`, and the integration runner `.venv/bin/python -m eval.learn_layer_check` (all self-tests, G1/G8 re-run on every gate-passed item, gate_levels, gate_scene, item field integrity, pack rebuild and licence gate) |

The pack: `questions.item_json` now carries the whole item (scheme with alternatives, levels, G4 scripts), scanned by
the licence gate like any text column (`chatbot/pack.py`, `scripts/clean/build_pack.py`). Scenes stay in their own
files until the pack build copies them in (to do).

### Scene guides (every diagram explains itself; built 23:05 to 23:20)

Each scene carries a `guide` (spec §2, "Guide"): `what_you_see`, a `legend` entry per drawn thing, an `interact`
entry per slider and draggable point with a concrete "do" and "watch", a `question_link` naming the part and the mark
codes and saying which drawn object is which object in the question, and `read_off` lines for live labels.
`annotate_scenes.py` wrote them for all 31 scenes ($0.88, about $0.026 a scene; 30 first time, 1 retry);
`gate_scene.py --require-guide` enforces coverage, KaTeX, banned words and G7, and `eval.learn_layer_check` requires
a guide on every scene. The renderer shows the guide around the board: kicker line above, slider instructions and a
"drag" cue that fades after the first interaction, dashed halos and tooltips on draggable points, id labels on
unlabelled regions, then Legend / How to use this / How this links to the question (mark chips) / Read off, and the
step text says what each step changed ("sets k = 3; shows R; hides Rfull"). Without a guide the renderer builds
defaults from the elements. Browser-checked 23:22: renders correctly, no console errors.

Lessons: tell the model the exact coverage set the gate will demand (ids, controls, live labels) and retries almost
vanish; when G7 fails, feed back the offending 8-gram itself, not just a count (that fixed the last scene for $0.014;
adopt in `make_scenes.py` and `enrich_solutions.py` retries too); models over-cover legends (169 entries for 114
required), which is good; point labels that are coordinates ("(1, 2)") appear as the legend name, so prefer letter
labels with the coordinates in the meaning.

### Second marking (marker accuracy; built 30 Sept, 23:30, no model calls)

The published 98.0% for marker v2 was measured against the G4 marker's own reference, so it is not independent.
The harness lets a human blind-mark the same 182 G4 scripts and prints an honest agreement figure.

| What | Where |
|---|---|
| Hand-marking UI | `.venv/bin/python scripts/clean/second_mark_server.py [--no-browser] [--port 8767]` → http://127.0.0.1:8767 (`scripts/clean/second_mark.html`). Blind: question, scheme lines and the script only, no vectors. Keys 1–9 toggle mark n, Enter submits; after each submit it shows human vs marker v2 vs the G4 reference with v2's reason per mark. Queue: the 17 scripts where marker v2 disagreed with the reference first, then the remaining pitfall scripts, then the rest, interleaved across items. |
| Output | `data/clean_private/second_marking.jsonl` (gitignored), one line per (item, script, part): `{at, by, item_id, script_id, part, human: [bools], seconds}` |
| Report | `.venv/bin/python eval/second_marking_report.py [--log PATH] [--items DIR] [--cache PATH]`: per-mark agreement human vs v2 and human vs reference with 95% Wilson intervals, overall and by mark family and script kind (correct / partial / pitfall / alternative), then every disagreement. It prints the caveat that these are scripted answers, not real students; the figure for real handwritten-then-typed scripts is still to be measured. |
| Self-test | `.venv/bin/python -m eval.second_mark_selftest` |

Rule: publish no marker accuracy figure until the human agreement exists, and quote it with its interval and the
caveat. About 30 minutes of marking gives roughly 60 scripts.

### Review UI additions (30 Sept evening)

`scripts/clean/review_server.py` and `review.html` now show, per item, collapsible **Solution levels** (brisk and
every-step line counts), **Interactive scenes** (with the guide) and the type's **Playbook** section, so G9 review
covers the learn layer too. A **Papers** button opens an overlay listing the six mock papers with generated /
gate-passed / accepted counts (`/api/mocks`, `/api/mock?id=`; read from `content/clean/mocks/*.json`, else
assembled from the items' `paper` and `q_num` fields); **Review this paper** filters the queue to that paper in
question order (`?paper=`, `/api/items?paper=`).

### Evening build order for new items (no step skipped)

Each step reads the previous step's output from the item file; run them in this order after a generation batch.

1. Generate: `.venv/bin/python scripts/clean/generate.py --select <selection> --parallel 5 --skip-existing` (`--ids ...` for named blueprints).
2. Gates: `.venv/bin/python scripts/clean/gates.py content/clean/items/*.json` (G1, G2, G7, G8), then `.venv/bin/python scripts/clean/gate_solve.py content/clean/items/*.json`, the same for `gate_marking.py` (G4 + G5) and `gate_tags.py` (G6); `.venv/bin/python -m eval.clean_gates_report` for the counts.
3. Solution levels: `.venv/bin/python scripts/clean/enrich_solutions.py --items all --parallel 5 --max-usd 40` (gate-passed items only; skips parts that already have levels unless `--force`).
4. Scenes: `.venv/bin/python scripts/clean/make_scenes.py --items all --parallel 5 --max-usd 40`.
5. Guides: `.venv/bin/python scripts/clean/annotate_scenes.py --items all --parallel 5 --max-usd 10`.
6. Check everything with no model calls: `.venv/bin/python -m eval.learn_layer_check` (self-tests, G1/G8 re-run, gate_levels, gate_scene --require-guide, field integrity, pack rebuild and licence gate), then review in the UI (G9).

### Gate fixes from the evening batch (2026-10-01)

- **G2 and subscripted names:** sympy's `implicit_multiplication_application` includes `split_symbols`, which turned `x1` into
  `x*1` and raised NameError. `gate_maths.TRANSFORMS` now uses the four constituent transforms with a custom splitter that
  keeps `^[A-Za-z]+\d+$` names whole. `scripts/clean/rerun_g2.py [--dry] <items>` re-runs G2 and writes `gate_results.G2`
  back atomically. Three batch items flipped to pass; none regressed.
- **G7 whitelist growth:** `gates.g7_novelty` now returns `hits8` (our own text's matching 8-grams), and the gates that
  wrap it name those phrases in their error messages so retries reword them. A private proposals file
  (`data/clean_private/whitelist_proposals_<date>.md`) lists the phrases from every failing item for the user's decision;
  the whitelist itself changes only on approval (checklist §35).
- **Stop rule in practice:** a 60-item batch spread across all three components passed 6/30 (20%) on its first half
  against the pilot's 42% (calculus-heavy), so the second half was not generated. G7 (13/30) and G2 (12/30, four of them
  the parse bug) dominated. Raise the pass rate on these two before scaling (handover §5 step 2).
