#!/usr/bin/env python3
"""One-off (per subject) taxonomy draft: question types + skill groups + skills, from the kept parts
of one component, in ONE model call (lever A applied to step 6). The user reviews the draft
(docs/taxonomy-draft-<component>.md) BEFORE any tagging.

    .venv/bin/python scripts/draft_taxonomy.py --component stats,mech --papers '^P3_' [--model claude-opus-5-5]

Reuses the existing cross-subject groups (exam-technique, algebra, modelling) instead of duplicating
them. Output: data/processed/_taxonomy_draft_<component>.json + docs/taxonomy-draft-<component>.md
"""
import argparse
import json
import re
from pathlib import Path

from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
SHARED_GROUPS = ["exam-technique", "algebraic-manipulation", "quadratics", "modelling-in-context",
                 "basic-differentiation", "basic-integration", "vectors", "trig-identities",
                 "exponentials-and-logarithms", "straight-lines-coordinates"]

SKILL = {"type": "object", "additionalProperties": False, "required": ["id", "title", "group", "description", "formula_booklet", "spec_refs"],
         "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "group": {"type": "string"},
                        "description": {"type": "string"}, "formula_booklet": {"type": ["boolean", "null"],
                        "description": "null = unknown; the orchestrator verifies against the real booklet"},
                        "spec_refs": {"type": "array", "items": {"type": "string"}}}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["topics", "question_types", "skill_groups", "skills", "draft_types", "decisions"],
          "properties": {
              "topics": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                         "required": ["id", "title", "component"], "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "component": {"enum": ["stats", "mech"]}}}},
              "question_types": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                 "required": ["id", "title", "topic", "definition"],
                                 "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "topic": {"type": "string"}, "definition": {"type": "string"}}}},
              "skill_groups": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["id", "title", "topics"], "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "topics": {"type": "array", "items": {"type": "string"}}}}},
              "skills": {"type": "array", "items": SKILL},
              "draft_types": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["question_id", "question_type"],
                              "properties": {"question_id": {"type": "string"}, "question_type": {"type": "string"}}}},
              "decisions": {"type": "array", "items": {"type": "string"}, "description": "choices the human reviewer should make"}}}


def dump(pattern: str) -> str:
    lines = []
    for f in sorted((PROC / "questions").glob("*.json")):
        if not re.search(pattern, f.stem):
            continue
        for q in json.loads(f.read_text())["questions"]:
            lines.append(f"## {q['id']} [{q['component']}, {q['total_marks']} marks] {' '.join((q['stem'] or '').split())[:220]}")
            for p in q["parts"]:
                codes = " ".join(re.findall(r"\b(?:d|D)?[MAB]\d\b", p["mark_scheme"]))
                lines.append(f"- ({p['label'] or '-'}) {p['marks']}m refs={p.get('spec_refs')} | {' '.join(p['text'].split())[:200]} | MS: {' '.join(p['mark_scheme'].split())[:260]} [{codes}]")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--component", default="stats,mech")
    ap.add_argument("--papers", default="^P3_")
    ap.add_argument("--model", default="claude-opus-5-5")
    a = ap.parse_args()
    tags = json.loads((PROC / "tags.json").read_text())
    shared = [s for s in tags["skills"] if s["group"] in SHARED_GROUPS]
    shared_txt = "\n".join(f"- {s['id']} ({s['group']}): {s['title']}" for s in shared)
    old_types = "\n".join(f"- {t['id']}: {t['title']}: {t['definition']}" for t in tags["question_types"][:6])
    stmts = [s for s in json.loads((PROC / "spec_9ma0.json").read_text())["statements"] if s["component"] != "pure"]
    spec = "\n".join(f"{s['ref']} {s['text']} || {s.get('guidance') or ''}" for s in stmts)
    system = f"""You design a two-layer tagging vocabulary for Edexcel A Level Statistics and Mechanics questions (9MA0 Paper 3), for a tutor chatbot that recommends practice.

Layers (same design as the existing Pure vocabulary, which the user reviewed and approved):
- question_types (NARROW): "the same kind of question" — one per whole question, e.g. for Pure 'optimisation-constrained-shape'. Expect roughly 20–35 for Stats+Mech. Each belongs to one topic.
- skills (BROAD): every distinct skill a PART can test, 3–6 per part typically, each in a skill_group (~10–16 new groups). Used to recommend practice for the exact step a student struggled with, ordered easiest first. Skills must be specific and teachable (e.g. 'continuity-correction', 'resolve-forces-on-inclined-plane', 'take-moments-about-a-point', 'state-hypotheses-binomial-test', 'interpret-in-context').
- topics: top-level groupings for Stats and Mech (~5 each), aligned with the spec sections.
REUSE the shared skills listed below (exam technique, algebra, calculus, vectors…) by id instead of creating duplicates; new skills may belong to shared groups when that fits. Ids are kebab-case. Descriptions are one sentence, written for a student.
formula_booklet: true only if the skill's key formula is printed in the 9MA0 formula booklet — if you aren't sure, use null (it is verified against the real booklet afterwards; never guess true).
draft_types: one question_type for EVERY question id in the dump.
decisions: 5–10 real choices the reviewer should make (e.g. one type or two, where a boundary lies).

Existing Pure question types (for style):
{old_types}

Shared skills to reuse:
{shared_txt}

9MA0 Statistics and Mechanics content:
{spec}
"""
    body = dump(a.papers)
    r = run(system, [text_block("QUESTIONS (one line per part):\n" + body + "\n\nReturn the vocabulary JSON.")],
            schema=SCHEMA, model=a.model, step="taxonomy", ref=a.component, thinking_tokens=12000, max_usd=5)
    out = {**r["result"], "_method": "single-call-v1", "_model": a.model, "_cost_usd": r["cost_usd"]}
    comp = a.component.replace(",", "-")
    (PROC / f"_taxonomy_draft_{comp}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: len(v) for k, v in r["result"].items() if isinstance(v, list)}), "cost", r["cost_usd"])


if __name__ == "__main__":
    main()
