#!/usr/bin/env python3
"""Mark-scheme completeness pass: add the official content an extraction left out of each part's mark
scheme (scheme working lines, notes that change marks, special cases, alternative methods).

Why: the blind Opus audit of 6 Tier 2 papers (2026-09-26) found ~4.5 pieces of official MS content missing
per paper, and that was the main quality gap. One call per paper sees the mark-scheme pages and the current
transcription, and returns ADDITIONS only, each attached to a part and copied from the official MS.

Deterministic guard: an addition is accepted only if its words (outside $...$) appear, in order, in the
official mark scheme's text layer (decoded if the font is scrambled). A paper whose MS has no usable text
layer gets its additions accepted but flagged for review. Accepted additions are appended to the part's
mark_scheme in the STAGING file as an "Official notes (completeness pass): ..." block, then derived texts
are rebuilt and check_questions.py re-run.

    .venv/bin/python scripts/ms_complete.py IAL2018_WMA11_Jan2022 ...   [--out DIR to write a copy]
    .venv/bin/python scripts/ms_complete.py --todo --only '^IAL2013'
Each paper records "ms_complete_method": "single-call-v1" and a count of additions.
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import check_questions as cq
import extract_single as ex
from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
METHOD = "single-call-v2"
MARKER = "Official notes (completeness pass):"

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["additions"],
          "properties": {"additions": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["question_id", "label", "kind", "text"],
              "properties": {"question_id": {"type": "string"},
                             "label": {"type": "string", "description": "part label as in the transcription, '-' for single-part"},
                             "kind": {"enum": ["working_line", "note", "special_case", "alternative_method", "other"]},
                             "text": {"type": "string", "description": "copied from the official MS, maths in $...$ LaTeX"}}}}}}


def words(t: str) -> list[str]:
    return cq.prose_words(t)


def unicode_to_latex(t: str) -> str:
    """Unicode maths outside $...$ -> LaTeX, as extract_single.autofix does (√ excepted: it needs its argument).
    A run of symbols becomes ONE span ("α²" -> "$\\alpha^2$"): two touching spans would read as "$$" display maths."""
    t = ex.unicode_prose_to_latex(t)[0]
    # "their" values quoted inside maths: a ' straight after a superscript is a prime to KaTeX ("'4\pi^2'" ->
    # double superscript). Put quotes that close a superscripted value in \text{}.
    return re.sub(r"(\^\{?[\w\\]+\}?)'", r"\1\\text{'}", t)


def verbatim_in_ms(addition: str, ms_words: list[str]) -> bool:
    w = words(addition)
    return not w or cq.subsequence_gap(w, ms_words, restarts=2) is None


def numbers_in_ms(addition: str, ms_nums: set[str]) -> list[str]:
    """Decimals in the addition that aren't in the MS text layer. Maths-only lines (scheme working) have no
    prose for verbatim_in_ms to check, so this is their guard. Decimals only, as in check_questions: integers
    and fractions are too often split or merged by pdftotext."""
    return sorted(n for n in cq.plain_numbers(addition) if "." in n and not cq.num_in(n, ms_nums))


def already_present(addition: str, part_ms: str) -> bool:
    """Its prose AND its numbers are already in the part. Prose alone isn't enough: a working line such as
    "$0.42/0.512=0.8203...$ awrt 0.820" has only the word "awrt", which the part will usually contain."""
    w = " ".join(words(addition))
    part_maths = norm_maths(part_ms)
    return (w in " ".join(words(part_ms)) and cq.plain_numbers(addition) <= cq.plain_numbers(part_ms)
            and all(m in part_maths for m in map(norm_maths, re.findall(r"\$([^$]+)\$", addition)) if len(m) >= 4))


def norm_maths(t: str) -> str:
    """LaTeX with spacing and sizing removed, for comparing one expression with another."""
    t = re.sub(r"\\(left|right|big|Big|bigg|Bigg)\b|\\[,;:! ]|\\q?quad\b|\\displaystyle\b", "", t)
    return re.sub(r"[\s{}$]", "", t).replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")


def complete(pid: str, model: str, out_dir: Path | None) -> dict:
    st = PROC / "_staging" / f"{pid}.json"
    d = json.loads(st.read_text())
    if not d["questions"]:
        return {"paper_id": pid, "skipped": "no transcribed questions"}
    if d.get("ms_complete_method"):
        return {"paper_id": pid, "skipped": "already done"}
    x = ex.manifest_entry(pid)
    raw = ROOT / "data" / "raw" / "pearson" / x["qualification"] / x["sitting"]
    ms_pdf, _ = ex.trim_pdf(raw / f"{pid}_MS.pdf", "MS")
    ms_txt = (raw / f"{pid}_MS.txt").read_text(errors="ignore")
    if cq.shifted_font(ms_txt):
        ms_txt = cq.decode_shifted(ms_txt)
    ms_usable = cq.usable_text(ms_txt)
    ms_words = cq.prose_words(ms_txt, source=True) if ms_usable else []
    ms_nums = cq.plain_numbers(ms_txt) if ms_usable else set()
    current = "\n\n".join(f"### {q['id']}\n" + "\n".join(f"[part {p['label'] or '-'}] {p['mark_scheme']}" for p in q["parts"])
                          for q in d["questions"])
    system = ("You check transcribed Edexcel mark schemes against the official mark scheme pages and list what is "
              "MISSING. Only official content counts: scheme working lines with their mark codes, notes that change "
              "what earns a mark (allow / condone / 'M0 if' / 'send to review'), special cases (SC), and alternative "
              "methods. Copy each addition word for word from the official mark scheme (maths in $...$ LaTeX). Don't "
              "repeat anything already in the transcription, don't paraphrase, don't add commentary, and ignore the "
              "general marking guidance at the front. Only the questions listed are in scope.")
    content = ([text_block("OFFICIAL MARK SCHEME pages:")] + ex.page_images(ms_pdf, 110)
               + [text_block("CURRENT TRANSCRIPTION (per part):\n" + current + "\n\nReturn the additions JSON "
                             "(empty list if nothing official is missing).")])
    r = run(system, content, schema=SCHEMA, model=model, step="ms-complete", ref=pid, thinking_tokens=4000)
    from triage_spec import norm_label
    accepted, rejected = [], []
    by_q = {q["id"]: q for q in d["questions"]}
    for a in r["result"]["additions"]:
        a["text"] = unicode_to_latex(a["text"])
        q = by_q.get(a["question_id"])
        lab = None if a["label"].strip() in ("-", "") else norm_label(a["label"])
        part = next((p for p in (q["parts"] if q else []) if p["label"] == lab), None)
        whole = False
        if not part and q and (len(q["parts"]) == 1 or lab is None):
            part, whole = q["parts"][0], len(q["parts"]) > 1     # a note for the whole question goes on its first part
        if not part:
            rejected.append({**a, "why": "unknown question/part"})
            continue
        if ms_usable and not verbatim_in_ms(a["text"], ms_words):
            rejected.append({**a, "why": "not verbatim in the official MS text"})
            continue
        if ms_usable and (miss := numbers_in_ms(a["text"], ms_nums)):
            rejected.append({**a, "why": f"numbers not in the official MS text: {miss}"})
            continue
        if already_present(a["text"], part["mark_scheme"]):
            rejected.append({**a, "why": "already present"})
            continue
        if whole:
            a = {**a, "text": "(Whole question) " + a["text"].strip()}
        n_same = sum(pp is part and aa["text"].strip() == a["text"].strip() for _, pp, aa in accepted)
        if n_same and (not ms_usable or cq.times_in(a["text"], " ".join(ms_words)) <= n_same):
            rejected.append({**a, "why": "returned twice in this call (the MS doesn't print it that often)"})
            continue
        accepted.append((q, part, a))
    for q, part, a in accepted:
        if MARKER not in part["mark_scheme"]:
            part["mark_scheme"] = part["mark_scheme"].rstrip() + f"\n{MARKER}"
        part["mark_scheme"] += f"\n- {a['text'].strip()}"
    for q in d["questions"]:
        q["question_text"], q["mark_scheme_text"] = cq.derived(q)
    d["ms_complete_method"] = METHOD
    d["ms_complete_added"] = len(accepted)
    d["ms_complete_unverified"] = not ms_usable
    target = (out_dir or st.parent) / f"{pid}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    log = (out_dir / "_log" if out_dir else PROC / "_ms_complete") / f"{pid}.json"
    log.parent.mkdir(exist_ok=True)
    log.write_text(json.dumps({"_paper_id": pid, "accepted": [a for _, _, a in accepted], "rejected": rejected,
                               "ms_text_usable": ms_usable, "cost_usd": r["cost_usd"]}, indent=2, ensure_ascii=False) + "\n")
    errs = [e for e in cq.check(target) if not e.startswith("NOTICE")] if out_dir is None else []
    return {"paper_id": pid, "added": len(accepted), "rejected": len(rejected), "check_ok": not errs,
            "errors": errs[:3], "cost_usd": round(r["cost_usd"] or 0, 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--model", default="claude-opus-5-5")   # 6-paper pilot: Sonnet recalled 3/20 omissions, Opus 20/20
    ap.add_argument("--out")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    ids = a.paper_ids
    if a.todo:
        ids = [p.stem for p in sorted((PROC / "_staging").glob("*.json"))
               if json.loads(p.read_text())["questions"] and not json.loads(p.read_text()).get("ms_complete_method")]
    if a.only:
        ids = [i for i in ids if re.search(a.only, i)]
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda p: _safe(p, a.model, Path(a.out) if a.out else None), ids):
            print(json.dumps(res), flush=True)


def _safe(pid, model, out):
    try:
        return complete(pid, model, out)
    except Exception as e:
        return {"paper_id": pid, "error": f"{type(e).__name__}: {e}"[:300]}


if __name__ == "__main__":
    main()
