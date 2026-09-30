#!/usr/bin/env python3
"""G6 tag accuracy: retag each part blind and compare with the blueprint's skills (docs/handoff-clean-room.md §6).

    .venv/bin/python scripts/clean/gate_tags.py content/clean/items/*.json [--dry]

One `claude -p` call per item on Haiku 4.5. It sees the question text (not the mark scheme or our tags) and
the list of skills for the item's component (our taxonomy), and picks 1-4 skills per part. A part agrees
when the retagger picks any of its skills. A part tagged in the same skill group but with different skills is a
flag for the reviewer; only a part with no skill group in common fails. The bank-level target is >= 95% of
parts agreeing at skill level (eval/clean_gates_report.py).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import claude_oneshot  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate_marking import norm_label  # noqa: E402

MODEL = "claude-haiku-4-5"
SYSTEM = """You tag A level Mathematics questions with the skills each part tests. For every part, choose the 1-4
skills from the list that a student must use to answer that part, most important first. Use only ids from the list."""
SCHEMA = {"type": "object", "properties": {"parts": {"type": "array", "items": {"type": "object", "properties": {
    "label": {"type": ["string", "null"]}, "skills": {"type": "array", "items": {"type": "string"}}},
    "required": ["label", "skills"]}}}, "required": ["parts"]}


def skill_list(component: str, tags: dict, facts_parts: list[dict]) -> list[dict]:
    comp_skills = {s for p in facts_parts if p["component"] == component for s in p["skills"]}
    return [s for s in tags["skills"] if s["id"] in comp_skills and s["group"] != "exam-technique"]


def g6_tags(item: dict, tags: dict, skills: list[dict]) -> dict:
    group = {s["id"]: s["group"] for s in tags["skills"]}
    listing = "\n".join(f"- {s['id']}: {s['title']}" for s in skills)
    q = "\n\n".join([item.get("stem") or ""] + [f"Part {p.get('label') or '-'}: {p['text']}" for p in item["parts"]])
    out = claude_oneshot.run(SYSTEM, [claude_oneshot.text_block(f"# Skills\n{listing}\n\n# Question\n{q}")],
                             schema=SCHEMA, model=MODEL, max_usd=0.3, thinking_tokens=2000, step="clean-g6",
                             ref=item["id"])
    got = {norm_label(p.get("label")): p["skills"] for p in out["result"]["parts"]}
    errors, flags, agree = [], [], 0
    for p in item["parts"]:
        mine = [s for s in p.get("skills", []) if group.get(s) != "exam-technique"]
        lab = norm_label(p.get("label"))
        # the retagger may split a part into sub-parts ("b(i)", "b(ii)"): merge them under our label
        theirs = [s for k, v in got.items() if k == lab or (re.fullmatch(r"[a-z]", lab)
                                                              and re.fullmatch(lab + r"(i|ii|iii|iv|v|vi)", k)) for s in v] \
            or (next(iter(got.values()), []) if len(item["parts"]) == 1 else [])
        if mine and set(mine) & set(theirs):
            agree += 1
        elif mine and {group[s] for s in mine} & {group.get(s) for s in theirs}:
            flags.append(f"part {p.get('label') or '-'}: same topic, different skills: tagged {mine}, retagged {theirs}")
        else:
            errors.append(f"part {p.get('label') or '-'}: tagged {mine}, retagged {theirs}")
    return {"pass": not errors, "errors": errors, "flags": flags, "flag": bool(flags),
            "agreement": f"{agree}/{len(item['parts'])}", "model": MODEL,
            "cost_usd": out["cost_usd"], "retagged": got}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    facts = json.loads((ROOT / "content" / "facts" / "parts.json").read_text())["parts"]
    lists = {}
    for f in map(Path, args.items):
        item = json.loads(f.read_text())
        comp = item["component"]
        lists.setdefault(comp, skill_list(comp, tags, facts))
        r = g6_tags(item, tags, lists[comp])
        print(f"{item['id']}: G6 {'PASS' if r['pass'] else 'FAIL'} {r['agreement']} (${r['cost_usd']:.3f})")
        for e in r["errors"]:
            print("    ", e)
        if not args.dry:
            item.setdefault("gate_results", {})["G6"] = r
            f.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
