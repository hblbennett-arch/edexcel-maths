#!/usr/bin/env python3
"""Lever B (2026-09-26): decide which questions of a LEGACY (IAL/GCE) paper are in the 9MA0 spec,
before anything is transcribed. One small call per paper, reading the question paper and mark
scheme TEXT (images only when a paper has no usable text layer).

Why a separate step: in the single-call pilot, the extractor judged spec membership too
leniently twice (a "sampling distribution" question, a regression / PMCC-formula question),
while agents that judged part by part got them right. So the judgement gets its own focused
prompt, the spec's explicit exclusions as a checklist (generated from spec_9ma0.json, never
typed by hand), and a required citation per part.

    .venv/bin/python scripts/triage_spec.py IAL2018_WST01_Jan2023 [more ids] [--model claude-sonnet-5]

Writes data/processed/_triage/<paper_id>.json. extract_single.py then transcribes only the kept
questions, and copies the dropped ones (marks + reasons, no text) into excluded_questions.
"""
import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import check_questions
import concept_screen
from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = PROC / "_triage"
METHOD = "triage-v1"
EXCL = re.compile(r"[^.;(]*\b(excluded|not required|not be required|not expected|will not be)\b[^.;)]*", re.I)

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"],
          "properties": {"questions": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["q_num", "total_marks", "parts"],
              "properties": {"q_num": {"type": "string"}, "total_marks": {"type": "integer"},
                             "parts": {"type": "array", "items": {
                                 "type": "object", "additionalProperties": False,
                                 # reason BEFORE the decision: the model writes its reasoning, then commits.
                                 # (With in_spec first, it once wrote "...so this is actually in spec" after in_spec=false.)
                                 "required": ["label", "marks", "technique", "reason", "in_spec", "confidence", "spec_refs"],
                                 "properties": {
                                     "label": {"type": ["string", "null"]}, "marks": {"type": "integer"},
                                     "technique": {"type": "string", "description": "the topic/method the MS requires"},
                                     "reason": {"type": "string", "description": "FIRST reason it through: which statement(s) or exclusion apply, citing them"},
                                     "in_spec": {"type": "boolean", "description": "the conclusion of your reason"},
                                     "confidence": {"enum": ["high", "medium", "low"],
                                                    "description": "high: a statement or explicit exclusion settles it; "
                                                                   "medium: depends on depth or guidance wording; low: borderline"},
                                     "spec_refs": {"type": "array", "items": {"type": "string"}}}}}}}}}}


def exclusions() -> str:
    lines = []
    for s in json.loads((PROC / "spec_9ma0.json").read_text())["statements"]:
        for f in ("text", "guidance"):
            for m in EXCL.finditer(s.get(f) or ""):
                lines.append(f"- {s['ref']}: \"{m.group(0).strip()}\"")
    return "\n".join(lines)


def system_prompt() -> str:
    stmts = json.loads((PROC / "spec_9ma0.json").read_text())["statements"]
    spec = "\n".join(f"{s['ref']} [{s['section_title']}] {s['text']} || guidance: {s.get('guidance') or '-'}" for s in stmts)
    return f"""You decide which parts of an old Edexcel maths exam paper are within the CURRENT UK A Level Mathematics specification (9MA0). Out-of-spec questions are dropped from a revision chatbot, and wrongly dropping an in-spec question loses good practice material, so decide from the statements as written. When it is genuinely borderline, give your best decision and mark confidence medium or low: a human reviews those.

A part is IN spec only if its topic AND every method its mark scheme requires are covered by the statements below, at that depth. Rules:
- Judge ONLY from these statements and their guidance, never from memory of any syllabus.
- A named concept that no statement mentions (e.g. "sampling distribution", "Poisson", "probability density function", "work–energy", "impulse", "centre of mass") makes the part OUT, even if the arithmetic itself would be in spec.
- The EXPLICIT EXCLUSIONS list below overrides everything: e.g. using the PMCC formula from summary statistics, calculations with a regression line, and E(X)/Var(X) of a general discrete random variable are all OUT.
- If the mark scheme offers an alternative in-spec method that can earn FULL marks, the part is IN. A capped special case doesn't count.
- A part that only makes sense after an out-of-spec part (it uses that answer) is OUT.
- For every part, write the reason FIRST (which statements or exclusions apply, and why), then in_spec as its conclusion, then confidence and spec_refs (for in-spec parts; valid refs only). Check the guidance of the relevant statements: it often widens a statement (e.g. M8.4's guidance includes connected particles on an inclined plane) or narrows it (the exclusions).
- Report every question and every part, with the marks printed on the paper (one part per printed mark bracket).
- confidence: "high" when a statement or an explicit exclusion settles it outright; "medium" when it turns on depth or on how a guidance sentence is read; "low" when it's genuinely borderline. Be honest: medium and low decisions go to a human.

EXPLICIT EXCLUSIONS (from the specification's own wording):
{exclusions()}

CONCEPTS NO 9MA0 STATEMENT COVERS (a script checked their key terms are absent from every statement), so any part
that requires one is OUT: {"; ".join(concept_screen.verified_concepts())}.
(Ordinary 9MA0 vector work, i.e. position vectors, magnitude, distance, parallel vectors and geometric problems, is IN.)

9MA0 STATEMENTS:
{spec}
"""


def norm_label(lab):
    """'(a)' -> 'a', '(b)(i)' -> 'b(i)', '(ii)' -> 'ii': the question files' label style."""
    if not lab:
        return None
    m = re.fullmatch(r"\(?([a-z]+|[ivx]+)\)?\s*(?:\(([a-z]+|[ivx]+)\))?", lab.strip().lower())
    return (m.group(1) + (f"({m.group(2)})" if m.group(2) else "")) if m else lab


IN_WORDS = re.compile(r"\b(is|are|so this is|actually|therefore|thus)\s+(actually\s+)?(in spec|within (the )?spec|covered)\b", re.I)
OUT_WORDS = re.compile(r"\b(not in spec|out of spec|not covered|excluded)\b", re.I)


def neutral(t: str) -> str:
    """Remove phrases that use the decision words about OTHER content, which made ~50 of 144 Tier 2 triage
    files look self-contradictory: "(only binomial and Normal are covered)", "no excluded concept is used",
    "not explicitly stated as excluded", "the exclusion does not apply"."""
    t = re.sub(r"\([^()]*\)", " ", t)                                        # asides in brackets
    t = re.sub(r"\bonly\b[^.;]*?\b(covered|in spec)\b", " ", t, flags=re.I)   # "only X ... are covered"
    t = re.sub(r"\b(no|not|nothing|without|never)\b[^.;]{0,40}?\bexclu\w*", " ", t, flags=re.I)
    t = re.sub(r"\b(none|neither) of which (is|are)\b[^.;]*?\bcovered\b", " not covered ", t, flags=re.I)
    t = re.sub(r"\b(even though|although|while)\b[^,.;]*", " ", t, flags=re.I)           # concessive clauses
    t = re.sub(r"\b(the|from the|distinct from the) excluded\b", " ", t, flags=re.I)       # adjective use
    return t


def contradictions(res: dict) -> list[str]:
    """Parts whose reason's conclusion says the opposite of in_spec (a script check, no model)."""
    out = []
    for q in res["questions"]:
        for p in q["parts"]:
            tail = neutral(p["reason"][-160:])
            if not p["in_spec"] and IN_WORDS.search(tail) and not OUT_WORDS.search(tail):
                out.append(f"Q{q['q_num']}({p['label']}): in_spec=false but reason ends '{tail}'")
            if p["in_spec"] and OUT_WORDS.search(tail) and not IN_WORDS.search(tail):
                out.append(f"Q{q['q_num']}({p['label']}): in_spec=true but reason ends '{tail}'")
    return out


def triage(pid: str, model: str) -> dict:
    import extract_single as ex
    x = ex.manifest_entry(pid)
    raw = ROOT / "data" / "raw" / "pearson" / x["qualification"] / x["sitting"]
    content = [text_block(f"Paper {pid}: {x['title']} ({x['qualification']} unit {x['unit']}).")]
    for kind in ("QP", "MS"):
        t = (raw / f"{pid}_{kind}.txt").read_text(errors="ignore")
        if check_questions.usable_text(t):
            content.append(text_block(f"{'QUESTION PAPER' if kind == 'QP' else 'MARK SCHEME'} (text layer; "
                                      f"symbols may be garbled):\n{t}"))
        else:
            pdf, _ = ex.trim_pdf(raw / f"{pid}_{kind}.pdf", kind)
            content += [text_block(f"{'QUESTION PAPER' if kind == 'QP' else 'MARK SCHEME'} pages:")] + ex.page_images(pdf, 90)
    content.append(text_block("Return the triage JSON."))
    r = run(system_prompt(), content, schema=SCHEMA, model=model, step="triage", ref=pid, thinking_tokens=4000)
    clash = contradictions(r["result"])
    if clash:                                  # reason and decision disagree: ask again for those parts only
        ask = ("In your triage these parts' reason contradicts their in_spec value:\n" + "\n".join(clash)
               + "\nReturn the COMPLETE triage JSON again with those parts decided consistently with the spec.")
        r2 = run(system_prompt(), content + [text_block(ask)], schema=SCHEMA, model=model, step="triage-recheck",
                 ref=pid, thinking_tokens=4000)
        r = {"result": r2["result"], "cost_usd": (r["cost_usd"] or 0) + (r2["cost_usd"] or 0)}
    for q in r["result"]["questions"]:
        q["q_num"] = re.sub(r"\D", "", str(q["q_num"])) or q["q_num"]     # "Q1" -> "1"
        for p in q["parts"]:
            p["label"] = norm_label(p["label"])
    out = {"_paper_id": pid, "triage_method": METHOD, "triage_model": model, "cost_usd": r["cost_usd"],
           **r["result"]}
    OUT.mkdir(exist_ok=True)
    (OUT / f"{pid}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    kept = [q["q_num"] for q in out["questions"] if all(p["in_spec"] for p in q["parts"])]
    unsure = sum(p["confidence"] != "high" for q in out["questions"] for p in q["parts"])
    return {"paper_id": pid, "kept": kept, "unsure_parts": unsure, "dropped": [q["q_num"] for q in out["questions"] if q["q_num"] not in kept],
            "cost_usd": round(r["cost_usd"] or 0, 3)}


def review_report() -> str:
    """docs/spec-triage-review.md, prioritised: only decisions whose uncertainty could change the outcome.
    - kept question with any medium/low part: out-of-spec content might reach the chatbot;
    - dropped question whose every out-of-spec part is medium/low: good material might be lost.
    A question dropped for a high-confidence reason can't change, so it isn't listed."""
    kept_rows, drop_rows, n_q, n_unsure = [], [], 0, 0
    for f in sorted(OUT.glob("*.json")):
        t = json.loads(f.read_text())
        for q in t["questions"]:
            n_q += 1
            parts = q["parts"]
            unsure = [p for p in parts if p.get("confidence", "high") != "high"]
            n_unsure += len(unsure)
            outs = [p for p in parts if not p["in_spec"]]
            ref = f"{t['_paper_id']} Q{q['q_num']}"
            fmt = lambda p: (f"({p['label']}) {p['technique']}: *{p['confidence']}*. "
                             f"{p['reason'][:220].replace('|', '/')}")
            if not outs and unsure:
                kept_rows.append(f"| {ref} | " + "<br>".join(fmt(p) for p in unsure) + " |")
            elif outs and all(p.get("confidence", "high") != "high" for p in outs):
                drop_rows.append(f"| {ref} | " + "<br>".join(fmt(p) for p in outs) + " |")
    L = ["# Spec triage: decisions for a human glance", "",
         f"Generated by `scripts/triage_spec.py --report`. {n_q} legacy questions triaged; {n_unsure} parts were "
         "medium/low confidence, but only the decisions below could change what the chatbot contains. "
         "Overrule any with \"keep <paper> Q<n>\" or \"drop <paper> Q<n>\".", "",
         f"## A. Kept, but a part is uncertain ({len(kept_rows)}): is anything here outside 9MA0?", "",
         "| Question | Uncertain part(s) |", "|---|---|", *kept_rows, "",
         f"## B. Dropped only on uncertain grounds ({len(drop_rows)}): is anything here actually in 9MA0?", "",
         "| Question | Out-of-spec part(s) |", "|---|---|", *drop_rows, ""]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--report", action="store_true", help="write docs/spec-triage-review.md")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--parallel", type=int, default=3)
    a = ap.parse_args()
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda p: _safe(p, a.model), a.paper_ids):
            print(json.dumps(res), flush=True)
    if a.report:                                   # after triaging, so new decisions are included
        (ROOT / "docs" / "spec-triage-review.md").write_text(review_report())
        print("wrote docs/spec-triage-review.md")


def _safe(pid, model):
    try:
        return triage(pid, model)
    except Exception as e:
        return {"paper_id": pid, "error": f"{type(e).__name__}: {e}"[:300]}


if __name__ == "__main__":
    main()
