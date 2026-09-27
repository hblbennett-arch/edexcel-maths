#!/usr/bin/env python3
"""Write function names upright inside maths, as Edexcel prints them (Phase 2e tidy-up).

Within $...$ spans only: f(x) -> \\mathrm{f}(x), g^{-1} -> \\mathrm{g}^{-1}, f'(x) ->
\\mathrm{f}'(x), and composites fg(2) -> \\mathrm{fg}(2). Letters already inside a command
or braces (\\mathrm{f}, \\frac{..}) are left alone. Rebuilds question_text /
mark_scheme_text from the parts, like scripts/apply_latex.py. Idempotent.

    .venv/bin/python scripts/normalise_function_names.py            # dry run: count changes
    .venv/bin/python scripts/normalise_function_names.py --write
"""
import json
import re
import sys
from pathlib import Path

QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "questions"

# A run of 1-3 of f/g/h used as a function name: followed by "(", "^{-1}", or a prime.
# Not after a letter/backslash/sub-/superscript, and not already inside \mathrm{...} or \text{...}.
# A lone "h" right after a number or "}" is a multiplier (trapezium rule: \frac{1}{2}h(...)), not a function.
FUNC_RE = re.compile(
    r"(?<![\\A-Za-z_^])(?<!\\mathrm\{)(?<!\\text\{)(?<!\\mathbf\{)"
    r"(?!h(?<=[0-9.}]h))"
    r"([fgh]{1,3})(?=\s*(?:\(|\^\{-1\}|\^\{\\prime|'))")
SPAN_RE = re.compile(r"\$[^$]+\$")


def upright(text: str) -> tuple[str, int]:
    count = 0

    def fix_span(m: re.Match) -> str:
        nonlocal count
        new, n = FUNC_RE.subn(r"\\mathrm{\1}", m.group())
        count += n
        return new

    return SPAN_RE.sub(fix_span, text), count


def main() -> None:
    write = "--write" in sys.argv
    total = 0
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        n_file = 0
        for q in data["questions"]:
            single_same = len(q["parts"]) == 1 and q["parts"][0]["label"] is None and q.get("stem") == q["parts"][0]["text"]
            for p in q["parts"]:
                for key in ("text", "mark_scheme"):
                    p[key], n = upright(p[key])
                    n_file += n
            if q.get("stem") and not single_same:
                q["stem"], n = upright(q["stem"])
                n_file += n
            if single_same:
                q["stem"] = q["question_text"] = q["parts"][0]["text"]
            else:
                q["question_text"] = "\n".join(([q["stem"]] if q.get("stem") else []) + [p["text"] for p in q["parts"]])
            q["mark_scheme_text"] = "\n".join(p["mark_scheme"] for p in q["parts"])
        total += n_file
        print(f"  {path.stem}: {n_file} function name(s) made upright")
        if write and n_file:
            path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{total} change(s)" + ("" if write else " (dry run — rerun with --write)"))


if __name__ == "__main__":
    main()
