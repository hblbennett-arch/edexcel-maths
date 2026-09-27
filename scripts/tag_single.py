#!/usr/bin/env python3
"""Step 6 (tagging) with single calls: question type + part skills for up to 3 papers per call.

The model sees the approved vocabulary for the questions' component (Pure, or Stats+Mech plus the
shared skills), and every part's text and mark scheme. The output schema only ALLOWS vocabulary
ids (enums), so it can't invent tags; it lists anything it thinks is missing as a suggestion.
The script writes data/processed/tags_assigned/<paper_id>.json and validates with check_tags.py.
Rules: docs/tagging-spec.md.

    .venv/bin/python scripts/tag_single.py --todo --only '^P3_'          # untagged papers, 3 per call
    .venv/bin/python scripts/tag_single.py IAL2018_WST01_Jan2023 ...

Files record "tag_method": "single-call-v1" (the Pure papers were tagged by agents).
Suggested new skills/types are appended to logs/tag_suggestions.jsonl for the human review list.
"""
import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
METHOD = "single-call-v1"
SHARED_GROUPS = {"exam-technique", "algebraic-manipulation", "quadratics", "modelling-in-context",
                 "basic-differentiation", "basic-integration", "vectors", "trig-identities",
                 "exponentials-and-logarithms", "straight-lines-coordinates"}


def vocab(component: str) -> tuple[str, list[str], list[str]]:
    """Compact vocabulary text + allowed type ids + allowed skill ids for one component family."""
    T = json.loads((PROC / "tags.json").read_text())
    comp_of_group = {g["id"]: g.get("component", "pure") for g in T["skill_groups"]}
    comp_of_topic = {t["id"]: t.get("component", "pure") for t in T["topics"]}
    fam = "pure" if component == "pure" else "statsmech"
    in_fam = lambda c: (c == "pure") if fam == "pure" else (c in ("stats", "mech", "stats+mech"))
    # Stats/Mech parts can use ANY Pure skill (an arithmetic series in a probability question, integration by
    # parts in a pdf-style model), so their vocabulary is Stats/Mech + all of Pure. Pure questions don't get
    # Stats/Mech skills. (First run offered only a few shared groups; the tagger flagged the gap.)
    groups = [g for g in T["skill_groups"] if in_fam(g.get("component", "pure")) or fam == "statsmech"]
    gids = {g["id"] for g in groups}
    skills = [s for s in T["skills"] if s["group"] in gids]
    types = [t for t in T["question_types"] if in_fam(comp_of_topic.get(t["topic"], "pure"))]
    lines = ["QUESTION TYPES (pick exactly one per question):"]
    lines += [f"- {t['id']} [{t['topic']}]: {t['title']}. {t.get('definition', '')}" for t in types]
    lines += ["", "SKILLS by group (tag every skill each part tests):"]
    for g in groups:
        lines.append(f"## {g['title']} ({g['id']})")
        lines += [f"- {s['id']}: {s['title']}. {s.get('description', '')}" for s in skills if s["group"] == g["id"]]
    return "\n".join(lines), [t["id"] for t in types], [s["id"] for s in skills]


def schema(types: list[str], skills: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["questions", "suggestions"],
            "properties": {
                "questions": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["question_id", "question_type", "parts"],
                    "properties": {"question_id": {"type": "string"}, "question_type": {"enum": types},
                                   "parts": {"type": "array", "items": {
                                       "type": "object", "additionalProperties": False, "required": ["label", "skills"],
                                       "properties": {"label": {"type": "string", "description": "part label, or '-' for a single-part question"},
                                                      "skills": {"type": "array", "items": {"enum": skills}}}}}}}},
                "suggestions": {"type": "array", "items": {"type": "string"},
                                "description": "skills or question types you think are missing: 'name — where (question/part)'"}}}


def question_dump(pid: str) -> tuple[str, dict]:
    d = json.loads((PROC / "questions" / f"{pid}.json").read_text())
    lines, parts = [], {}
    draft = {}
    df = PROC / "_taxonomy_draft_stats-mech.json"
    if df.exists():
        draft = {x["question_id"]: x["question_type"] for x in json.loads(df.read_text())["draft_types"]}
    for q in d["questions"]:
        parts[q["id"]] = ["-" if p["label"] is None else p["label"] for p in q["parts"]]
        hint = f" [reviewed draft type: {draft[q['id']]}]" if q["id"] in draft else ""
        lines.append(f"### {q['id']} ({q['total_marks']} marks){hint}\nStem: {' '.join((q['stem'] or '').split())[:400]}")
        for p in q["parts"]:
            lab = "-" if p["label"] is None else p["label"]
            lines.append(f"- part {lab} ({p['marks']}m): {' '.join(p['text'].split())[:500]}\n  MS: {' '.join(p['mark_scheme'].split())[:700]}")
    return "\n".join(lines), parts


def tag_batch(pids: list[str], model: str, out_dir: Path | None = None, complete: bool = False) -> list[dict]:
    out_dir = out_dir or PROC / "tags_assigned"
    comps = {json.loads((PROC / "questions" / f"{p}.json").read_text())["questions"][0].get("component", "pure") for p in pids}
    fam = "pure" if comps == {"pure"} else "statsmech"
    vtxt, types, skills = vocab("pure" if fam == "pure" else "stats")
    spec = (ROOT / "docs" / "tagging-spec.md").read_text()
    system = f"""You tag Edexcel maths exam questions for a tutor chatbot that recommends practice.
Follow these rules (ignore their instructions about files and scripts; return the schema instead):
<tagging_spec>
{spec}
</tagging_spec>
Use ONLY the vocabulary below. A question marked with a reviewed draft type should keep it unless it is clearly wrong.
Tag from each part's text AND mark scheme. Every question and every part must appear.
Be THOROUGH with skills: a part usually tests 3-6 of them. Walk through the mark scheme mark by mark (each M/A/B mark
rewards a step) and tag the skill behind every step, including the "small" ones: the algebra used (rearranging,
solving a quadratic or simultaneous equations, index laws), the calculus rules, and the cross-cutting exam skills
when a mark depends on them (show-that-given-answer, use-hence-previous-result, exact-form-answers,
accuracy-units-and-rounding, explain-with-reason, reject-invalid-solutions …; use only ids that are in the vocabulary).
A 1-mark "state"/"write down" part may have just 1-2.
<vocabulary>
{vtxt}
</vocabulary>"""
    dumps, allparts = [], {}
    for p in pids:
        t, parts = question_dump(p)
        dumps.append(t)
        allparts.update(parts)
    r = run(system, [text_block("\n\n".join(dumps) + "\n\nReturn the tags JSON.")], schema=schema(types, skills),
            model=model, step="tags", ref="+".join(pids), thinking_tokens=4000)
    cost = r["cost_usd"] or 0
    if complete:
        # Completeness pass: the same model sees its own first-pass tags and may only ADD skills
        # (measured: the first pass alone recovers ~70-80% of the agents' skills at ~90% precision).
        first = json.dumps(r["result"]["questions"], ensure_ascii=False)
        add_schema = {"type": "object", "additionalProperties": False, "required": ["additions"],
                      "properties": {"additions": {"type": "array", "items": {
                          "type": "object", "additionalProperties": False,
                          "required": ["question_id", "label", "skills"],
                          "properties": {"question_id": {"type": "string"}, "label": {"type": "string"},
                                         "skills": {"type": "array", "items": {"enum": skills}}}}}}}
        r2 = run(system, [text_block("\n\n".join(dumps)),
                          text_block("First-pass tags:\n" + first + "\n\nGo through each part's mark scheme mark by mark. "
                                     "For every part, list any vocabulary skills the part genuinely tests that are MISSING "
                                     "above (a step a mark rewards, an algebra or calculus technique used, or an exam skill a "
                                     "mark depends on). Only additions; empty list if nothing is missing.")],
                 schema=add_schema, model=model, step="tags-complete", ref="+".join(pids), thinking_tokens=4000)
        cost += r2["cost_usd"] or 0
        from triage_spec import norm_label
        by = {q["question_id"]: q for q in r["result"]["questions"]}
        for ad in r2["result"]["additions"]:
            q = by.get(ad["question_id"])
            if not q:
                continue
            lab = norm_label(ad["label"]) if ad["label"].strip() not in ("-", "") else "-"
            for part in q["parts"]:
                pl = norm_label(part["label"]) if part["label"].strip() not in ("-", "") else "-"
                if pl == lab:
                    part["skills"] = list(dict.fromkeys(part["skills"] + ad["skills"]))
    got = {q["question_id"]: q for q in r["result"]["questions"]}
    results = []
    for p in pids:
        qs = {}
        d = json.loads((PROC / "questions" / f"{p}.json").read_text())
        for q in d["questions"]:
            g = got.get(q["id"])
            if not g:
                continue
            from triage_spec import norm_label
            labs = {(norm_label(x["label"]) if x["label"].strip() not in ("-", "") else "-"): list(dict.fromkeys(x["skills"]))
                    for x in g["parts"]}
            qs[q["id"]] = {"question_type": g["question_type"],
                           "parts": {lab: labs.get(lab, []) for lab in allparts[q["id"]]}}
        out = {"_paper_id": p, "_paper": d["_paper"], "_sitting": d["_sitting"], "tag_method": METHOD + ("+complete" if complete else ""),
               "tag_model": model, "questions": qs}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{p}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        if out_dir != PROC / "tags_assigned":
            results.append({"paper_id": p, "ok": None, "note": f"comparison copy in {out_dir}"}); continue
        chk = subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "scripts" / "check_tags.py"), p],
                             capture_output=True, text=True, cwd=ROOT / "scripts")
        results.append({"paper_id": p, "ok": chk.returncode == 0, "check": chk.stdout.strip()[:200],
                        "missing_questions": len(d["questions"]) - len(qs)})
    with (ROOT / "logs" / "tag_suggestions.jsonl").open("a") as f:
        for s in r["result"]["suggestions"]:
            f.write(json.dumps({"papers": pids, "suggestion": s}) + "\n")
    for x in results:
        x["cost_usd_batch"] = round(cost, 3)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--only")
    # Measured 2026-09-26 on 3 agent-tagged Pure papers: Sonnet 5 recovered ~75% of the agents' skills
    # (a "what's missing" 2nd pass didn't help); Opus 5.5 recovered 93% at the same 91% precision, ~$0.17/paper.
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--per-call", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--out", help="write to this folder instead (comparison runs)")
    a = ap.parse_args()
    ids = a.paper_ids
    if a.todo:
        ids = [p.stem for p in sorted((PROC / "questions").glob("*.json"))
               if json.loads(p.read_text())["questions"] and not (PROC / "tags_assigned" / p.name).exists()]
    if a.only:
        ids = [i for i in ids if re.search(a.only, i)]
    # batch papers of the same component family together
    fam = lambda p: "pure" if json.loads((PROC / "questions" / f"{p}.json").read_text())["questions"][0].get("component", "pure") == "pure" else "sm"
    batches = []
    for f in ("pure", "sm"):
        group = [p for p in ids if fam(p) == f]
        batches += [group[i:i + a.per_call] for i in range(0, len(group), a.per_call)]
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda b: _safe(b, a.model, Path(a.out) if a.out else None), batches):
            for x in res:
                print(json.dumps(x), flush=True)


def _safe(b, model, out=None):
    try:
        return tag_batch(b, model, out)
    except Exception as e:
        return [{"paper_id": p, "ok": False, "error": f"{type(e).__name__}: {e}"[:300]} for p in b]


if __name__ == "__main__":
    main()
