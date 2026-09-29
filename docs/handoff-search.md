# Handoff: better "find me a question on…" search (written 2026-09-27)

**For:** a fresh Claude Code session in `~/edexcel-maths`. Read this file first, then `CLAUDE.md`, then
`docs/rag-chatbot-plan.md` (top "Status" sections only). The task needs **no model calls and costs nothing**:
it's local code, the local search index and local evals (except the optional `eval.chat_smoke`, ~$0.50).

## Standing instructions from the user
- **Never commit or push unless the user asks in that session.** If they ask: GitHub only (never GitLab),
  remote `origin` = github.com/hblbennett-arch/edexcel-maths, identity `hblbennett-arch <hblbennett@gmail.com>`;
  don't store any token they give you (pass it for one push with `git -c credential.helper= -c
  "http.https://github.com/.extraheader=AUTHORIZATION: basic <base64 of x-access-token:TOKEN>" push origin main`),
  and remind them to revoke it.
- The user is new to dev tooling: give step-by-step instructions for anything they must do themselves.
- **Log every human-review item** in `docs/review-checklist.md` (current last section: §24; add §25) and say how many.
- **Record lessons/optimisations in the skill docs** (`.claude/skills/add-exam-papers/SKILL.md` for the data
  pipeline, `docs/rag-chatbot-plan.md` for the chatbot), and **add deterministic checks/evals** rather than
  relying on the model.
- **Measure before and after** every change with the evals below; don't adopt a change that regresses them.
- Don't edit anything in `data/` for this task. It's search code only.

## The problem (two real user reports)
Practice requests ("find me / give me a question on …") go through `chatbot/recommend.py::find_practice`,
which until 2026-09-27 used **skill tags only**: the request is embedded, matched to the nearest skill titles
(`_targets`), and only questions tagged with that skill are returned. That fails whenever the request names
something that isn't a technique:

1. **Specific expression:** "Find me a question on differentiating x^x" → matched the skill "differentiate
   polynomials", missed **P2_June2019_Q11** ("y = x^x … by firstly taking logarithms"). **Already fixed**:
   `expression_hits()` in `recommend.py` searches the question LaTeX for normalised maths in the request
   (powers grouped, `e^{2x}` ≠ `e^{2x+1}`, expressions in >25 questions ignored), and exact matches are listed
   first as "contains x^x". A regression case is in `eval/practice_eval.py` (`EXPR_CASES`).
2. **Described scenario (THE TASK):** "Find me a stats question to do with dentists and 10% of customers
   arriving late" → best skill similarity only **0.46** (a real skill request is ~0.8+), so it returned
   unrelated "standardise to find μ or σ" questions and missed **P3_June2022_stats_Q4** ("A dentist knows from
   past records that 10% of customers arrive late…"). The existing question index already gets it right:
   `get_index().search(text, "question", mode=...)` ranks P3_June2022_stats_Q4 **#1 in bm25, semantic and
   hybrid** modes, and the part search returns its parts top-4. The practice route simply never asks it.

## What to build: search three ways, merge by rule
In `find_practice` (keep the signature and return shape: `{"request", "expression", "skills",
"question_type", "excluded_skills", "items": [{"question_id", "part_label", "reason"}]}`; the controller and
evals depend on it):

1. **Exact maths**: `expression_hits` (done). Keep it first.
2. **Description search (new)**: hybrid search over `question` docs (and `part` docs, to choose which part to
   open) using the request's positive text (`parse_request(text)["positive"]`, which already strips "find me a
   question on" fluff and negations).
3. **Skill tags**: the current logic, unchanged for technique requests.

Merge rules to implement, then **calibrate the thresholds on the benchmark** (don't guess them):
- If the top skill similarity is strong (≥ ~0.75, see `_targets`), keep today's ranking, so technique
  requests ("integration by parts", "2nd derivative test") must not change (the evals enforce this).
- If the skill match is weak, **or** the description search has a clear winner (e.g. BM25 top/second ratio ≥
  ~1.3, or semantic ≥ ~0.7 with a clear lead), list the description hits first with reason "matches your
  description", then fill with skill results. Tune the lead/threshold values on the benchmark.
- Apply the same filters as today to every channel: component ("stats"/"mechanics" → `req["component"]`),
  `exclude_questions` (already seen), and negative skills/types ("not a binomial").
- For a description hit, set `part_label` to the best-matching part (from the `part` search, doc ids
  `part:<question_id>:<label>`, e.g. `part:P3_June2022_stats_Q4:d`; single-part questions end in `:`; see `db.part_key`) or `None` for the whole question.
- Current-spec (9MA0) questions still first **within** the skill channel only. For a description match, the
  right question matters more than its spec (the user wanted P3 June 2022 whatever else exists).

## How to measure it (build this first, run before and after)
1. **New benchmark** `eval/practice_search_eval.py` (deterministic, seeded, no model):
   - Pick ~300 questions at random (`random.Random(11)`) from `questions.db`.
   - For each, build a "description" query from its **most distinctive words**: plain text via
     `chatbot.text.latex_to_plain`, tokens via `chatbot.text.tokens`, rank by IDF over all question texts, take
     the top 3–5 context words plus one number if present, and wrap them in a phrasing template
     ("find me a question about {w1} and {w2}", "a {component} question to do with {w1}, {w2} and {num}").
     Skip questions whose distinctive words are all maths-generic.
   - Metric: **recall@1 and recall@5** of the source question in `find_practice(query)["items"]`, reported
     overall and by qualification (9MA0 / IAL / GCE) and component.
   - Also include a small hand list of real reports as must-pass cases: the dentist request →
     `P3_June2022_stats_Q4` first; the x^x request → `P2_June2019_Q11` first.
   - Record the baseline (today's code) in the eval's output file, like `eval/retrieval_results.txt`.
2. **Existing evals must not regress:**
   - `.venv/bin/python eval/practice_eval.py`: currently **227/228 skills resolve, precision 1103/1106 =
     100%**, and all hand cases OK (including x^x). Technique requests must still return tagged parts.
   - `.venv/bin/python -m eval.retrieval`: references **31/31**, pasted "wrong question" **0**.
   - Optional at the end: `.venv/bin/python -m eval.chat_smoke` (live tutor calls, ~$0.50): all OK.

## Where things are
| What | Where |
|---|---|
| Practice finder (edit here) | `chatbot/recommend.py`: `parse_request`, `_targets` (skill/type semantic match, `SKILL_MARGIN`, `STRONG_QTYPE`), `expression_hits`, `find_practice` |
| Search index | `chatbot/search.py`: `get_index()`, `Index.search(query, kind, k, mode)` → `Hit(doc_id, kind, score, semantic, text)`; `Index.bm25_scores(query, kind)`; kinds `question`, `part`, `skill`, `note`, `qtype`; modes `bm25` / `semantic` / `hybrid` (RRF, `RRF_K = 60`); docs built by `documents()` (part docs include the stem and the part's skill titles) |
| Embeddings | `data/processed/embeddings_baai-bge-small-en-v1-5.npz` (local model `BAAI/bge-small-en-v1.5`, cached in `~/.cache/edexcel-maths-devtools/fastembed`) |
| How requests are routed | `chatbot/controller.py`: `PRACTICE_RE` decides a practice request; `_practice_questions()` calls `find_practice` and excludes seen questions |
| Reference / pasted-question matching (don't break) | `chatbot/identify.py` (`parse_reference`, `match_pasted`, `number_agreement`) |
| Database | `data/processed/questions.db` (SQLite; tables `questions`, `question_parts`, `question_tags`, `skills`, `question_types`, `examiner_notes`); helper `chatbot/db.py` (`db.rows`, `db.one`, `db.part_key`) |
| Evals | `eval/practice_eval.py`, `eval/retrieval.py` (+ `retrieval_queries.json`, `retrieval_results.txt`), `eval/chat_smoke.py` |
| Rebuild (only if you change `search.documents()`) | `.venv/bin/python scripts/build_db.py` then `.venv/bin/python scripts/build_embeddings.py` (~8 min, local) |
| Knowledge base facts | 2,702 in-spec questions: 9MA0 P1/P2 210, Paper 3 88, IAL 2018 770, IAL 2013 587, UK GCE pre-2017 1,046 |

## Suggested order of work
1. Read `find_practice` and `_targets`; reproduce both reports:
   `.venv/bin/python -c "from chatbot import recommend as R; print(R.find_practice('Find me a stats question to do with dentists and 10% of customers arriving late'))"`
2. Write `eval/practice_search_eval.py` and record the **baseline** numbers.
3. Implement the description channel and merge rules in `find_practice`.
4. Calibrate the thresholds on the benchmark (keep a held-out half of the ~300 queries to confirm, so the
   thresholds aren't fitted to the test).
5. Run all evals; fix regressions. Aim: dentist + x^x first; recall@5 clearly up; `practice_eval` unchanged.
6. Restart the chat UI and try it (below), then update docs: `docs/rag-chatbot-plan.md` (practice lookup
   now has three channels, with the benchmark numbers), `docs/review-checklist.md` §25 (anything the user
   should try, e.g. "try 5 niche requests and note misses"), and tell the user what changed and the numbers.

## Running the chat UI (for testing and for the user)
```bash
cd ~/edexcel-maths
lsof -ti tcp:8765 | xargs kill 2>/dev/null     # stop a running copy (it caches code; restart after edits)
.venv/bin/python -m chatbot.web                # then open http://127.0.0.1:8765
```
Run it in the background from Claude Code so the session isn't blocked. Try: "Find me a stats question to do
with dentists and 10% of customers arriving late", "a mechanics question about a ladder against a wall",
"Find me a question on differentiating x^x", "a question on integration by parts please".

## Pitfalls
- `Index` and `_question_maths()` are cached (`lru_cache`), so restart Python/the UI after changing data.
- `parse_request` lower-cases and strips fluff; test on its `positive` output, not the raw message.
- Keyword search favours long questions with many matching words; guard the "clear winner" rule with a lead
  ratio, not a raw score.
- Old GCE/IAL papers reuse a scenario with new numbers (near-duplicates), so when two description hits are
  close, list both rather than picking one (see `identify.number_agreement` for a tie-break idea: prefer the
  one containing the request's numbers, e.g. "10%").
