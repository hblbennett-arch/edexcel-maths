#!/usr/bin/env python3
"""Split each question's text and mark scheme into parts (Phase 2b).

A *part* is the smallest unit that carries its own marks. For example
"(a)(i) … (ii) … (3 marks)" is one part labelled "a", while
"(b)(i) … (2) (ii) … (1)" gives parts "b(i)" and "b(ii)". Single-part
questions get one part with label null.

Adds to each question in data/processed/questions/*.json:
    "stem":  text before the first part label (shared preamble)
    "parts": [{"label", "marks", "text", "mark_scheme"}, ...]
question_text / mark_scheme_text are kept unchanged.

Every split is checked: part marks must sum to total_marks, the question
paper and mark scheme must yield the same labels with the same marks, and
labels must follow in order. Questions that fail are left untouched and
listed, so they can be split by hand.

    .venv/bin/python scripts/split_parts.py            # dry run: report only
    .venv/bin/python scripts/split_parts.py --write    # write parts for passing questions

After splitting, every part's text is widened to cover the whole of
question_text / mark_scheme_text with no gaps (see fill_gaps). Question text
between two parts (e.g. "The line l1 is the tangent to C at A.") belongs
to the *next* part. Mark-scheme text between parts (notes, alternative
methods) belongs to the *previous* part. This runs on every question,
including hand-split ones, and is idempotent.
"""
import json
import re
import sys
from pathlib import Path

QUESTIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "processed" / "questions"

LETTERS = "abcdefgh"
ROMANS = ["i", "ii", "iii", "iv", "v"]
# A part label, e.g. "(a)" or "(ii)", not preceded by a letter/digit (so f(a) and g(x) are ignored).
LABEL_RE = re.compile(r"(?<![A-Za-z0-9^_'])\((?P<lab>[a-h]|iv|v|i{1,3})\)")
# Marks, e.g. "(3)", "(3 marks)", "(1 mark)" — but not "(Total for Question 2 is 4 marks)".
MARKS_RE = re.compile(
    r"(?<![A-Za-z0-9^_*/.,=+\-])\((?P<n>\d{1,2}) marks?\)"            # "(3 marks)"
    r"|(?<![A-Za-z0-9^_*/.,=+\-])\((?P<n2>\d{1,2})\)(?=\s*(?:$|\n|\(|[A-Z]|Using|Hence|Given))"  # bare "(3)" ending a part
)
# Words that make a label a cross-reference ("using the answer to (a)") rather than a new part.
REFERENCE_WORDS = {"to", "in", "from", "part", "parts", "of", "and", "or", "with", "for", "using", "than", "&"}


class SplitError(ValueError):
    pass


def find_labels(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, label) for real part labels, skipping cross-references."""
    found, skipping_chain_end = [], -1
    for m in LABEL_RE.finditer(text):
        if m.start() == skipping_chain_end:  # "(a)(ii)" chained onto a skipped reference
            skipping_chain_end = m.end()
            continue
        prev_word = re.findall(r"[A-Za-z&]+", text[max(0, m.start() - 12):m.start()])
        if prev_word and prev_word[-1].lower() in REFERENCE_WORDS and not text[:m.start()].rstrip().endswith((".", ")")):
            skipping_chain_end = m.end()
            continue
        found.append((m.start(), m.end(), m["lab"]))
    return found


def labelled_units(text: str) -> tuple[str, list[dict]]:
    """Split text into (stem, units). Each unit = labels seen since the previous marks token."""
    labels = find_labels(text)
    marks = list(MARKS_RE.finditer(text))
    if not labels:
        return text.strip(), []

    stem = text[:labels[0][0]].strip()
    units, current_letter, pending, unit_start = [], None, [], labels[0][0]
    li = 0
    for mk in marks:
        if mk.start() < labels[0][0]:
            continue  # marks-like token in the stem
        while li < len(labels) and labels[li][0] < mk.start():
            lab = labels[li][2]
            if lab in LETTERS:
                current_letter = lab
                pending.append(lab)
            else:
                pending.append(f"{current_letter}({lab})" if current_letter else lab)
            li += 1
        if not pending:
            raise SplitError(f"marks {mk.group()} with no part label before it")
        units.append({"labels": pending, "marks": int(mk["n"] or mk["n2"]), "text": text[unit_start:mk.end()].strip()})
        pending = []
        unit_start = labels[li][0] if li < len(labels) else mk.end()
    if li < len(labels):
        raise SplitError(f"label(s) {[l[2] for l in labels[li:]]} after the last marks token")
    return stem, units


def merge_label(labels: list[str]) -> str:
    """Labels covered by one marks token -> the part's label ("a(i)","a(ii)" -> "a")."""
    # A bare letter followed by its own sub-parts ("b", "b(i)") is just the sub-part's heading.
    labels = [l for l in labels if not any(o.startswith(l + "(") for o in labels)]
    if len(labels) == 1:
        return labels[0]
    letters = {l.split("(")[0] for l in labels}
    if len(letters) == 1 and all(l[0] in LETTERS for l in labels):
        return letters.pop()
    raise SplitError(f"one marks total covers several parts {labels}")


def reconcile(qp_parts: list, ms_parts: list) -> list:
    """The question paper defines the parts. Where the mark scheme splits one QP
    part more finely (QP "b" 2 marks; MS "b(i)" 1 + "b(ii)" 1), merge those MS
    pieces back together. Only merges when the labels and marks agree exactly."""
    merged, i = [], 0
    for label, marks, _ in qp_parts:
        if i < len(ms_parts) and ms_parts[i][0] == label:
            merged.append(ms_parts[i]); i += 1
            continue
        group, total = [], 0
        while i < len(ms_parts) and ms_parts[i][0].startswith(label + "(") and total < marks:
            group.append(ms_parts[i]); total += ms_parts[i][1]; i += 1
        if not group or total != marks:
            return ms_parts  # can't reconcile — caller reports the mismatch
        merged.append((label, total, " ".join(t for _, _, t in group)))
    return merged + ms_parts[i:]


def split_question(q: dict) -> tuple[str, list[dict]]:
    try:
        stem, qp_units = labelled_units(q["question_text"])
    except SplitError as e:
        raise SplitError(f"QP: {e}")
    if not qp_units:
        return q["question_text"].strip(), [{
            "label": None, "marks": q["total_marks"],
            "text": q["question_text"].strip(), "mark_scheme": q["mark_scheme_text"].strip(),
        }]
    try:
        _, ms_units = labelled_units(q["mark_scheme_text"])
    except SplitError as e:
        raise SplitError(f"MS: {e}")

    qp_parts = [(merge_label(u["labels"]), u["marks"], u["text"]) for u in qp_units]
    ms_parts = [(merge_label(u["labels"]), u["marks"], u["text"]) for u in ms_units]
    ms_parts = reconcile(qp_parts, ms_parts)
    if [(l, m) for l, m, _ in qp_parts] != [(l, m) for l, m, _ in ms_parts]:
        raise SplitError(f"QP parts {[(l, m) for l, m, _ in qp_parts]} != MS parts {[(l, m) for l, m, _ in ms_parts]}")
    if sum(m for _, m, _ in qp_parts) != q["total_marks"]:
        raise SplitError(f"part marks sum to {sum(m for _, m, _ in qp_parts)}, total is {q['total_marks']}")
    if len({l for l, _, _ in qp_parts}) != len(qp_parts):
        raise SplitError(f"duplicate labels {[l for l, _, _ in qp_parts]}")
    return stem, [{"label": l, "marks": m, "text": t, "mark_scheme": ms}
                  for (l, m, t), (_, _, ms) in zip(qp_parts, ms_parts)]


def slice_bounds(full: str, pieces: list[str]) -> list[tuple[int, int]]:
    """Locate each piece in `full`, in order, as (start, end) offsets."""
    bounds, cursor = [], 0
    for piece in pieces:
        start = full.find(piece, cursor)
        if start == -1:
            raise SplitError(f"part text not found in order: {piece[:60]!r}")
        bounds.append((start, start + len(piece)))
        cursor = start + len(piece)
    return bounds


TRAILING_TOTAL_RE = re.compile(r"^\s*(\(Total for Question \d+ is \d+ marks?\))?\s*$")


def fill_gaps(q: dict) -> None:
    """Widen part text/mark_scheme so no text between parts is lost."""
    parts = q["parts"]
    if len(parts) == 1:
        parts[0]["mark_scheme"] = q["mark_scheme_text"].strip()
        if parts[0]["label"] is not None:  # one labelled part, e.g. "(i) (ii) (iii) ... (4)"
            start = q["question_text"].find(parts[0]["text"])
            parts[0]["text"] = q["question_text"][start:].strip()
        return
    qp, ms = q["question_text"], q["mark_scheme_text"]
    qb = slice_bounds(qp, [p["text"] for p in parts])
    # Only each mark-scheme part's start matters (it runs to the next part's start), and a
    # reconciled part may join non-adjacent pieces, so locate by its opening text.
    mb = slice_bounds(ms, [p["mark_scheme"][:40] for p in parts])
    for i, part in enumerate(parts):
        # Question text: start where the previous part ended; last part keeps any real trailing text.
        q_start = qb[0][0] if i == 0 else qb[i - 1][1]
        q_end = qb[i][1]
        if i == len(parts) - 1 and not TRAILING_TOTAL_RE.match(qp[q_end:]):
            q_end = len(qp)
        # Mark scheme: first part takes any preamble; each part runs up to the next part's start.
        m_start = 0 if i == 0 else mb[i][0]
        m_end = mb[i + 1][0] if i + 1 < len(parts) else len(ms)
        part["text"] = qp[q_start:q_end].strip()
        part["mark_scheme"] = ms[m_start:m_end].strip()


def main() -> None:
    write = "--write" in sys.argv
    n_ok = n_single = 0
    failures = []
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        changed = False
        for q in data["questions"]:
            if q.get("parts"):
                continue  # already split (possibly by hand) — never overwrite
            try:
                stem, parts = split_question(q)
            except SplitError as e:
                failures.append((q["id"], str(e)))
                continue
            n_ok += 1
            n_single += parts[0]["label"] is None
            if write:
                q["stem"], q["parts"] = stem, parts
                changed = True
        for q in data["questions"]:
            if q.get("parts"):
                before = json.dumps(q["parts"])
                try:
                    fill_gaps(q)
                except SplitError as e:
                    failures.append((q["id"], f"fill_gaps: {e}"))
                    continue
                changed |= write and json.dumps(q["parts"]) != before
        if changed:
            path.write_text(json.dumps(data, indent=2) + "\n")

    print(f"split OK: {n_ok} question(s) ({n_single} single-part); failed: {len(failures)}")
    for qid, err in failures:
        print(f"  FAIL {qid}: {err}")
    if not write:
        print("(dry run — rerun with --write to save)")


if __name__ == "__main__":
    main()
