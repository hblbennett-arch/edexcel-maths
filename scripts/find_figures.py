#!/usr/bin/env python3
"""Find each question's page range and figure pages in its question paper (Phase 2c).

Adds to each question in data/processed/questions/*.json:
    "qp_pages":     [first_page, last_page]  (1-based PDF pages)
    "has_figure":   true if the question text refers to a Figure
    "figure_pages": pages holding its figures (the "Figure N" caption), [] if none

Page numbers come from the form-feed page breaks pdftotext writes into
data/raw/papers/<paper>_<sitting>_QP.txt. Each question starts at the line
"N." and ends at "(Total for Question N is M marks)". The pages let the
chatbot link straight to a question (PDF URL + "#page=N") and attach figure
images (scripts/render_figure.py).

    .venv/bin/python scripts/find_figures.py            # dry run: report only
    .venv/bin/python scripts/find_figures.py --write    # save
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "data" / "processed" / "questions"
RAW_DIR = ROOT / "data" / "raw"
FIGURE_REF_RE = re.compile(r"\bFigure (\d+)\b")
# Statistics papers often print diagrams with no "Figure N" label ("shown on the scatter diagram",
# "the box plot"): those questions get their whole pages attached. (No Pure question matches.)
DIAGRAM_RE = re.compile(r"\b(scatter (diagram|graph)|box (plot|and whisker)|histogram|venn diagram|tree diagram|"
                        r"cumulative frequency (diagram|graph|curve)|stem and leaf|the (diagram|graph|sketch|grid) "
                        r"(below|opposite|shows)|shown (in|on) the (diagram|graph|grid)|diagram (below|shows)|on the grid)\b", re.I)


def page_of(text: str, pos: int) -> int:
    return text.count("\f", 0, pos) + 1


def locate(qp_text: str, q_num: str, search_from: int) -> tuple[int, int, int]:
    """Return (start_pos, end_pos, end_line_end) of question q_num in the QP text."""
    end = re.search(rf"\(Total for Question {q_num} is \d+ marks?\)", qp_text[search_from:])
    if not end:                                     # older GCE / IAL-2013 layout: next "(Total N marks)"
        end = re.search(r"\(Total \d+ marks?\)", qp_text[search_from:])
    if not end:
        raise ValueError(f"no '(Total for Question {q_num} is ...)' line")
    end_pos = search_from + end.start()
    start = None
    for m in re.finditer(rf"(?m)^\s*{q_num}\.(?:\s|$)", qp_text[search_from:end_pos]):
        start = search_from + m.start()
        break
    if start is None:
        # The "N." heading is sometimes drawn as a graphic and missing from the text;
        # fall back to the question's first "(a)".
        first_part = re.search(r"\(a\)", qp_text[search_from:end_pos])
        if not first_part:
            raise ValueError(f"no start line '{q_num}.' or '(a)' before its Total line")
        start = search_from + first_part.start()
    return start, end_pos, search_from + end.end()


def content_pages(pdf: Path, pages: list[int]) -> list[int]:
    """Of a question's pages, those with printed content (question wording, a figure or table), not
    blank answer space: a page with >= 4 lowercase words or a Figure/Diagram/Table label. Scanned PDFs
    (no text) keep every page. Keeps whole-question fallbacks from attaching empty pages."""
    keep = []
    for p_ in pages:
        t = subprocess.run(["pdftotext", "-f", str(p_), "-l", str(p_), "-layout", str(pdf), "-"],
                           capture_output=True, text=True).stdout
        if len(re.findall(r"\b[a-z]{4,}\b", t)) >= 4 or re.search(r"Figure|Diagram|Table", t):
            keep.append(p_)
    return keep or pages


def process_paper(data: dict) -> tuple[list[str], int, int]:
    """Fill qp_pages / has_figure / figure_pages for every question in one paper file (in place).

    Pages come from the QP's text (form feeds). Where the text can't be used (scanned or scrambled
    pages, or a question/figure that can't be found), fall back to the qp_pages the extraction model
    recorded, and use every page of the question as its figure pages, so the tutor still sees the
    diagram. Returns (problems, located, with_figures)."""
    problems, n_q, n_fig = [], 0, 0
    if not data["questions"]:
        return problems, 0, 0                                # every question dropped by the spec filter

    def fallback(q: dict, why: str) -> None:
        figures = bool(FIGURE_REF_RE.search(q["question_text"]))
        q["has_figure"] = figures
        pages = q.get("qp_pages") or []
        if q.get("page_map_source") and q.get("figure_pages"):
            q["has_figure"] = True                       # page_map.py found the figure pages on a scan
            return
        if pages:
            q["figure_pages"] = list(range(pages[0], pages[-1] + 1)) if figures else []
            q["figure_pages_source"] = "model qp_pages (whole question pages)" if figures else None
        else:
            q.setdefault("figure_pages", [])
            if figures:
                problems.append(f"{q['id']}: {why}; no qp_pages to fall back on, so the figure can't be attached")

    qp_text = (RAW_DIR / data["questions"][0]["source_qp_file"]).read_text(errors="ignore")
    pdf = RAW_DIR / data["questions"][0]["source_qp_file"].replace(".txt", ".pdf")
    import check_questions
    if not check_questions.usable_text(qp_text):
        for q in data["questions"]:
            fallback(q, "QP has no usable text layer")
            if not q["has_figure"] and DIAGRAM_RE.search(q["question_text"]) and q.get("qp_pages"):
                q["has_figure"] = True
                q["figure_pages"] = list(range(q["qp_pages"][0], q["qp_pages"][-1] + 1))
                q["figure_pages_source"] = "diagram mentioned (no Figure label): whole question pages"
        return problems, 0, sum(q["has_figure"] for q in data["questions"])
    cursor = 0
    for q in sorted(data["questions"], key=lambda q: int(q["q_num"])):
        prev_end = cursor
        try:
            start, end, cursor = locate(qp_text, q["q_num"], cursor)
        except ValueError as e:
            fallback(q, str(e))
            continue
        first, last = page_of(qp_text, start), page_of(qp_text, end)
        figures = sorted(set(FIGURE_REF_RE.findall(q["question_text"])), key=int)
        fig_pages, missing = [], False
        for fig in figures:
            # Prefer the caption line ("Figure 3" on its own); fall back to any mention.
            # Search from the previous question's end: figures are often laid out above "N.".
            region = qp_text[prev_end:end]
            hits = [m.start() for m in re.finditer(rf"(?m)^\s*Figure {fig}\s*$", region)] or \
                   [m.start() for m in re.finditer(rf"\bFigure {fig}\b", region)]
            if not hits:
                missing = True
                continue
            fig_pages.append(page_of(qp_text, prev_end + hits[0]))
        first = min([first] + fig_pages)  # a figure laid out above "N." starts the question
        n_q += 1
        n_fig += bool(figures)
        q["qp_pages"] = [first, last]
        q["has_figure"] = bool(figures)
        q["figure_pages"] = sorted(set(fig_pages)) if not missing else content_pages(pdf, list(range(first, last + 1)))
        if missing:
            q["figure_pages_source"] = "caption not found in text: whole question pages"
    for q in data["questions"]:
        if not q.get("has_figure") and DIAGRAM_RE.search(q["question_text"]) and q.get("qp_pages"):
            q["has_figure"] = True
            q["figure_pages"] = content_pages(pdf, list(range(q["qp_pages"][0], q["qp_pages"][-1] + 1)))
            q["figure_pages_source"] = "diagram mentioned (no Figure label): whole question pages"
    return problems, n_q, n_fig


def main() -> None:
    write = "--write" in sys.argv
    problems, n_q, n_fig = [], 0, 0
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        raw = path.read_text()
        data = json.loads(raw)
        p, a, b = process_paper(data)
        problems += p
        n_q += a
        n_fig += b
        if write:
            # keep each file's existing escaping (the original Pure files use \u escapes)
            path.write_text(json.dumps(data, indent=2, ensure_ascii="\\u" in raw) + "\n")
    print(f"located {n_q} question(s) in the text, {n_fig} with figures; problems: {len(problems)}")
    for p in problems:
        print(f"  {p}")
    if not write:
        print("(dry run — rerun with --write to save)")


if __name__ == "__main__":
    main()
