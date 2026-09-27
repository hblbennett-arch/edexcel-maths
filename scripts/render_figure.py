#!/usr/bin/env python3
"""Render a question's figure page(s) to PNG so they can be sent to the model
alongside the question text (Phase 2c). Images are cached in
data/cache/figures/ (gitignored, regenerated on demand).

    .venv/bin/python scripts/render_figure.py P1_June2022_Q15      # prints the PNG paths
    .venv/bin/python scripts/render_figure.py --all                # every question with figures

Uses poppler's pdftoppm on data/raw/papers/<paper>_<sitting>_QP.pdf and the
figure_pages found by scripts/find_figures.py.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "data" / "processed" / "questions"
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = ROOT / "data" / "cache" / "figures"
DPI = 110  # legible for the model, ~150 KB per page


def load_question(question_id: str) -> dict:
    paper_file = QUESTIONS_DIR / f"{question_id.rsplit('_', 1)[0]}.json"
    for q in json.loads(paper_file.read_text())["questions"]:
        if q["id"] == question_id:
            return q
    raise SystemExit(f"unknown question id {question_id}")


def render(q: dict) -> list[Path]:
    """Return PNG paths for the question's figure pages, rendering any not yet cached."""
    if not q.get("has_figure"):
        return []
    pdf = RAW_DIR / q["source_qp_file"].replace(".txt", ".pdf")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for page in q["figure_pages"]:
        out = CACHE_DIR / f"{q['id']}_p{page}.png"
        if not out.exists():
            subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-r", str(DPI),
                            "-png", "-singlefile", str(pdf), str(out.with_suffix(""))],
                           check=True, capture_output=True)
        paths.append(out)
    return paths


def main() -> None:
    if sys.argv[1:] == ["--all"]:
        questions = [q for p in sorted(QUESTIONS_DIR.glob("*.json")) for q in json.loads(p.read_text())["questions"]]
    elif len(sys.argv) == 2:
        questions = [load_question(sys.argv[1])]
    else:
        raise SystemExit(__doc__)
    for q in questions:
        for path in render(q):
            print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
