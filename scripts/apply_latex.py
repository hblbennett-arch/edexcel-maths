#!/usr/bin/env python3
"""Apply checked LaTeX conversions (Phase 2e; see docs/notation-spec.md).

Reads data/processed/_latex/<paper>_<sitting>.json (units already validated by
`node scripts/check_notation.js`), writes each unit back into its question's
stem / parts, then rebuilds the full question_text and mark_scheme_text from
the converted pieces so parts and full text stay in sync.

    node scripts/check_notation.js && .venv/bin/python scripts/apply_latex.py            # all
    .venv/bin/python scripts/apply_latex.py P1_June2022                                  # one paper

Refuses to run on a paper whose conversion file fails check_notation.js.
Marks each conversion file "_applied": true so reruns skip it.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "data" / "processed" / "questions"
LATEX_DIR = ROOT / "data" / "processed" / "_latex"


def apply(stem: str) -> None:
    latex_path = LATEX_DIR / f"{stem}.json"
    latex = json.loads(latex_path.read_text())
    if latex.get("_applied"):
        print(f"SKIP {stem}: already applied")
        return
    check = subprocess.run(["node", str(ROOT / "scripts" / "check_notation.js"), stem], capture_output=True, text=True)
    if check.returncode != 0:
        raise SystemExit(f"{stem} fails check_notation.js — fix it first:\n{check.stdout}")

    q_path = QUESTIONS_DIR / f"{latex['_paper']}_{latex['_sitting']}.json"
    data = json.loads(q_path.read_text())
    units = latex["units"]
    for q in data["questions"]:
        single_same = (len(q["parts"]) == 1 and q["parts"][0]["label"] is None
                       and q.get("stem") == q["parts"][0]["text"])
        if q.get("stem") and not single_same:
            q["stem"] = units[f"{q['id']}|stem"]
        for p in q["parts"]:
            label = "-" if p["label"] is None else p["label"]
            p["text"] = units[f"{q['id']}|{label}|text"]
            p["mark_scheme"] = units[f"{q['id']}|{label}|ms"]
        if single_same:
            q["stem"] = q["question_text"] = q["parts"][0]["text"]
        else:
            q["question_text"] = "\n".join(([q["stem"]] if q.get("stem") else []) + [p["text"] for p in q["parts"]])
        q["mark_scheme_text"] = "\n".join(p["mark_scheme"] for p in q["parts"])
        q["notation"] = "latex"
    q_path.write_text(json.dumps(data, indent=2) + "\n")
    latex["_applied"] = True
    latex_path.write_text(json.dumps(latex, indent=2, ensure_ascii=False) + "\n")
    print(f"APPLIED {stem}: {len(units)} unit(s)")


def main() -> None:
    stems = sys.argv[1:] or [p.stem for p in sorted(LATEX_DIR.glob("*.json"))]
    for stem in stems:
        apply(stem)


if __name__ == "__main__":
    main()
