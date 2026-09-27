#!/usr/bin/env python3
"""Lever A (2026-09-26): extract a paper with ONE model call instead of a multi-turn agent.

The model sees the trimmed question paper and mark scheme as PDF documents (page image + text
layer) and returns the questions as structured JSON. This script derives everything mechanical
(ids, paper fields, question_text / mark_scheme_text), runs check_questions.py, and if that
fails makes ONE follow-up call that sees its own output plus the error list. The expensive
prefix (instructions + PDFs) is identical, so the retry re-reads it from the cache.

    .venv/bin/python scripts/extract_single.py IAL2018_WST01_Jan2023              # -> _staging/
    .venv/bin/python scripts/extract_single.py P3_June2022_stats --out _trial     # comparison run
    .venv/bin/python scripts/extract_single.py --todo --only '^IAL2018_WMA' --limit 10

Every file it writes carries "extraction_method": "single-call-v1" (agent-built files carry
"agent-v3"), so the two approaches can always be told apart. Cost per call is logged to
logs/llm_calls.jsonl by claude_oneshot.py.
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import check_questions
from claude_oneshot import pdf_block, run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
MANIFEST = ROOT / "data" / "raw" / "pearson" / "manifest.json"
TRIM = Path.home() / ".cache" / "edexcel-maths-devtools" / "trimmed"
METHOD = "single-call-v1"

PART = {"type": "object", "additionalProperties": False,
        "required": ["label", "marks", "text", "mark_scheme", "spec_refs"],
        "properties": {"label": {"type": ["string", "null"]}, "marks": {"type": "integer"},
                       "text": {"type": "string"}, "mark_scheme": {"type": "string"},
                       "spec_refs": {"type": "array", "items": {"type": "string"}}}}
QUESTION = {"type": "object", "additionalProperties": False,
            "required": ["q_num", "total_marks", "component", "uses_large_data_set", "stem", "parts",
                         "qp_pages", "low_confidence", "notes"],
            "properties": {"q_num": {"type": "string"}, "total_marks": {"type": "integer"},
                           "component": {"enum": ["pure", "stats", "mech"]},
                           "uses_large_data_set": {"type": "boolean"}, "stem": {"type": "string"},
                           "parts": {"type": "array", "items": PART},
                           "qp_pages": {"type": "array", "items": {"type": "integer"},
                                        "description": "first and last page of the ORIGINAL question paper (see page map)"},
                           "low_confidence": {"type": "boolean"}, "notes": {"type": "string"}}}
EXCLUDED = {"type": "object", "additionalProperties": False, "required": ["q_num", "total_marks", "parts"],
            "properties": {"q_num": {"type": "string"}, "total_marks": {"type": "integer"},
                           "parts": {"type": "array", "items": {
                               "type": "object", "additionalProperties": False,
                               "required": ["label", "marks", "technique", "reason"],
                               "properties": {"label": {"type": ["string", "null"]}, "marks": {"type": "integer"},
                                              "technique": {"type": "string"}, "reason": {"type": "string"}}}}}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["paper_total", "questions", "excluded_questions", "pearson_errors"],
          "properties": {"paper_total": {"type": "integer"}, "questions": {"type": "array", "items": QUESTION},
                         "excluded_questions": {"type": "array", "items": EXCLUDED},
                         "pearson_errors": {"type": "array", "items": {"type": "string"}}}}


def system_prompt() -> str:
    """Byte-identical for every paper, so it is cached across calls."""
    spec_doc = (ROOT / "docs" / "question-extraction-spec.md").read_text()
    notation = (ROOT / "docs" / "notation-spec.md").read_text()
    notation = notation[notation.find("## The convention"):notation.find("## Validate")]
    stmts = json.loads((PROC / "spec_9ma0.json").read_text())["statements"]
    spec = "\n".join(f"{s['ref']} [{s['section_title']}] {s['text']} || guidance: {s.get('guidance') or '-'}"
                     for s in stmts)
    return f"""You transcribe Edexcel maths exam papers into structured JSON for a revision-tutor chatbot.
You are given a question paper (QP) and its mark scheme (MS) as PDF documents; read the page images, not just the text layer (it drops symbols, powers, roots and fraction bars).

Follow these rules exactly. They are the project's extraction spec: the whole of it applies, except that YOU only return the fields in the output schema. A script derives ids, paper fields, question_text and mark_scheme_text, and then validates your output against the QP's own printed marks and text.

<extraction_spec>
{spec_doc}
</extraction_spec>

<latex_convention>
{notation}
</latex_convention>

<spec_9ma0_statements>
The ONLY valid spec_refs, and the only basis for any in/out-of-spec judgement (never your memory of any syllabus):
{spec}
</spec_9ma0_statements>

Output notes:
- One part per printed mark bracket. Each part's text ends with its printed marks, e.g. "... \\n(3)".
- stem = ONLY the preamble printed before the first part label ("" if the question starts with (a)); never copy part text into it or repeat it inside a part. Transcribe every question from the QUESTION PAPER pages; never reconstruct question wording from the mark scheme (if a page seems missing, say so in notes and set low_confidence).
- A single-part question has one part with label null.
- qp_pages: the first and last ORIGINAL page numbers of the question (the user message gives the page map of the trimmed QP).
- pearson_errors: anything wrong or odd in Pearson's own QP/MS (kept verbatim in your transcription).
"""


def trim_pdf(src: Path, kind: str) -> tuple[Path, list[int]]:
    """QP: keep the cover and pages with question text (>= 4 lowercase words); drop answer-space pages.
    MS: drop the generic guidance pages before the first 'Question ... Scheme' page. Scanned PDFs
    (no text) are kept whole. Returns (pdf, original page numbers kept)."""
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(src)], capture_output=True,
                                                          text=True).stdout).group(1))
    texts = [subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(src), "-"],
                            capture_output=True, text=True).stdout for p in range(1, n + 1)]
    if not check_questions.usable_text("".join(texts)):       # scanned / unmappable font: can't judge pages
        return src, list(range(1, n + 1))
    if kind == "QP":
        content = lambda t: (len(re.findall(r"\b[a-z]{4,}\b", t)) >= 4          # question wording
                             or re.search(r"Figure|Diagram|Table|\(Total|^\s*\d+\.\s", t, re.M))  # figure-only pages
        keep = [1] + [i + 1 for i, t in enumerate(texts[1:], 1) if content(t)]
    else:
        first = next((i for i, t in enumerate(texts) if re.search(r"Question\s*(Number)?\s+Scheme", t)), 0)
        keep = list(range(first + 1, n + 1))
    if len(keep) == n:
        return src, keep
    TRIM.mkdir(parents=True, exist_ok=True)
    out = TRIM / f"{src.stem}.pdf"
    parts = []
    for p in keep:
        one = TRIM / f"{src.stem}.p{p}.pdf"
        subprocess.run(["pdfseparate", "-f", str(p), "-l", str(p), str(src), str(one)], check=True)
        parts.append(str(one))
    subprocess.run(["pdfunite", *parts, str(out)], check=True)
    for f in parts:
        Path(f).unlink()
    return out, keep


def page_images(pdf: Path, dpi: int = 110) -> list[dict]:
    """Pages as PNG images: ~22% fewer tokens than PDF document blocks (measured 2026-09-26), and still
    legible for subscripts at 110 dpi. The checker's verbatim/number checks catch misreads."""
    import base64
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), f"{tmp}/p"], check=True)
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.b64encode(f.read_bytes()).decode()}}
                for f in sorted(Path(tmp).glob("p-*.png"))]


def manifest_entry(pid: str) -> dict:
    docs = [d for d in json.loads(MANIFEST.read_text()) if d["paper_id"] == pid]
    qp = next(d for d in docs if d["doc_type"] == "QP")
    return {**qp, "docs": {d["doc_type"]: d for d in docs}}


def assemble(pid: str, x: dict, out: dict, model: str) -> dict:
    paper = "P3" if x["unit"].startswith("9MA0-3") else (x["unit_name"] if x["qualification"] == "9MA0"
                                                         else x["unit"] + x["variant"])
    qp_file = f"pearson/{x['qualification']}/{x['sitting']}/{pid}_QP.txt"
    ms_file = f"pearson/{x['qualification']}/{x['sitting']}/{pid}_MS.txt"
    base = {"paper_id": pid, "spec": x["qualification"], "qualification": x["qualification"], "unit": x["unit"],
            "status": x["status"], "paper": paper, "sitting": x["sitting"]}
    qs = []
    for q in out["questions"]:
        q = {**base, "id": f"{pid}_Q{q['q_num']}", **q, "source_qp_file": qp_file, "source_ms_file": ms_file,
             "notation": "latex", "extraction_method": METHOD}
        if len(q["parts"]) == 1 and q["parts"][0]["label"] is None and q.get("stem"):
            st, pt = " ".join(q["stem"].split()), " ".join(q["parts"][0]["text"].split())
            if pt.startswith(st[:60]) or st[:60] in pt:
                q["stem"] = q["parts"][0]["text"]      # single-part convention: stem = the part's text (no duplicate)
        q["question_text"], q["mark_scheme_text"] = check_questions.derived(q)
        qs.append(q)
    return {"_paper_id": pid, "_paper": paper, "_sitting": x["sitting"], "qualification": x["qualification"],
            "unit": x["unit"], "component": x["component"], "status": x["status"],
            "paper_total": out["paper_total"], "source_qp_file": qp_file, "source_ms_file": ms_file,
            "extraction_method": METHOD, "extraction_model": model,
            "pearson_errors": out.get("pearson_errors", []), "questions": qs,
            **({"excluded_questions": out["excluded_questions"]} if out.get("excluded_questions") else {})}


UNICODE_TO_LATEX = {"½": r"\frac{1}{2}", "¼": r"\frac{1}{4}", "¾": r"\frac{3}{4}", "√": r"\sqrt{}", "≤": r"\leqslant",
                    "≥": r"\geqslant", "≠": r"\neq", "±": r"\pm", "×": r"\times", "÷": r"\div", "θ": r"\theta",
                    "π": r"\pi", "μ": r"\mu", "σ": r"\sigma", "λ": r"\lambda", "α": r"\alpha", "β": r"\beta",
                    "²": "^2", "³": "^3", "→": r"\to", "∈": r"\in", "ℝ": r"\mathbb{R}", "∫": r"\int", "∑": r"\sum"}


def norm_qnums(out: dict) -> None:
    """The model sometimes writes "Q1" or "Question 1": normalise before anything filters on q_num."""
    for q in out["questions"] + out.get("excluded_questions", []):
        q["q_num"] = re.sub(r"\D", "", str(q["q_num"])) or q["q_num"]


def unicode_prose_to_latex(t: str) -> tuple[str, int]:
    """Unicode maths outside $...$ / $$...$$ -> LaTeX (except √, which needs its argument). Each run of
    neighbouring symbols becomes one $...$ span, so two conversions never touch and form "$$"."""
    syms = "".join(re.escape(u) for u in UNICODE_TO_LATEX if u != "√")
    pieces, n = re.split(r"(\$\$.*?\$\$|\$[^$]*\$)", t, flags=re.S), 0
    for i in range(0, len(pieces), 2):
        # √ with a number or single-letter argument is safe to convert: "√52" -> $\sqrt{52}$, "3√11" -> $3\sqrt{11}$
        pieces[i], k0 = re.subn(r"(\d*)√(\d+|[a-z]\b)", lambda m: f"${m.group(1)}\\sqrt{{{m.group(2)}}}$", pieces[i])
        n += k0
        pieces[i], k = re.subn(f"[{syms}]+", lambda m: "$" + "".join(UNICODE_TO_LATEX[c] for c in m.group(0)) + "$",
                               pieces[i])
        n += k
    return "".join(pieces), n


def autofix(out: dict) -> int:
    """Free, deterministic repairs before paying for a retry: Unicode maths outside $…$ -> LaTeX
    (except √, which needs its argument), and a missing trailing '(N)' mark token."""
    n = 0
    def fix(t: str) -> str:
        nonlocal n
        t, k = unicode_prose_to_latex(t)
        n += k
        return t
    for q in out["questions"]:
        q["stem"] = fix(q["stem"])
        for p in q["parts"]:
            p["text"], p["mark_scheme"] = fix(p["text"]), fix(p["mark_scheme"])
            # Only for whole parts: on a sub-part ("b(i)") a missing mark token usually means the paper
            # printed ONE total for (i)+(ii) and the model over-split; adding one would hide that error.
            if "(" not in (p["label"] or "") and not re.search(r"\((\d+)(?: marks?)?\)\s*$", p["text"]):
                p["text"] = p["text"].rstrip() + f"\n({p['marks']})"; n += 1
        # a lead-in printed between parts belongs to the NEXT part, not after this part's mark (Tier 3 audit)
        import fix_parts
        n += fix_parts.move_leadins(q)
    return n


def extract(pid: str, out_dir: str, model: str, pages: str = "png") -> dict:
    x = manifest_entry(pid)
    raw = ROOT / "data" / "raw" / "pearson" / x["qualification"] / x["sitting"]
    qp, qp_pages = trim_pdf(raw / f"{pid}_QP.pdf", "QP")
    if not (raw / f"{pid}_MS.pdf").is_file():            # Pearson never published it (see pearson-coverage.md)
        raise FileNotFoundError(f"{pid}: no mark scheme PDF, so it can't be extracted (--todo skips these)")
    ms, _ = trim_pdf(raw / f"{pid}_MS.pdf", "MS")
    legacy = x["status"] == "legacy"
    target = PROC / out_dir / f"{pid}.json"
    target.parent.mkdir(exist_ok=True)
    excluded, kept = [], None
    if legacy:
        # Lever B: the in/out decision is made by triage_spec.py (its own focused call), not here.
        import triage_spec
        tri_file = PROC / "_triage" / f"{pid}.json"
        if not tri_file.exists():
            triage_spec.triage(pid, model)
        tri = json.loads(tri_file.read_text())
        kept = [q["q_num"] for q in tri["questions"] if all(p["in_spec"] for p in q["parts"])]
        excluded = [{"q_num": q["q_num"], "total_marks": q["total_marks"],
                     "parts": [{"label": p["label"], "marks": p["marks"],
                                "technique": p["technique"] if not p["in_spec"] else "in spec",
                                "reason": p["reason"] if not p["in_spec"] else "question dropped: other parts out of spec"}
                               for p in q["parts"]]}
                    for q in tri["questions"] if q["q_num"] not in kept]
        if not kept:                                    # nothing in spec: no extraction call at all
            empty = {"paper_total": sum(q["total_marks"] for q in tri["questions"]), "questions": [],
                     "excluded_questions": excluded, "pearson_errors": []}
            paper = assemble(pid, x, empty, model)
            paper["triage_method"] = tri["triage_method"]
            target.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n")
            errs = [e for e in check_questions.check(target) if not e.startswith("NOTICE")]
            return {"paper_id": pid, "ok": not errs, "errors": errs[:20], "calls": 0, "cost_usd": 0,
                    "questions": 0, "excluded": len(excluded)}
    ask = (f"Paper {pid}: {x['title']} — qualification {x['qualification']}, unit {x['unit']}, component "
           f"{x['component']}, status {x['status']}.\n"
           f"The QP document holds original pages {qp_pages} in that order.\n"
           + (f"This is a LEGACY paper whose spec triage is already done. Transcribe ONLY questions {kept} "
              "(in full, all parts), and return excluded_questions EMPTY; the script adds the others."
              if legacy else
              "This is a current 9MA0 paper: every question is in spec — transcribe all of them, spec_refs on every "
              "part, excluded_questions empty.")
           + "\nReturn the JSON.")
    if pages == "pdf":
        content = [pdf_block(qp), pdf_block(ms), text_block(ask)]
    else:
        content = ([text_block("QUESTION PAPER pages:")] + page_images(qp) +
                   [text_block("MARK SCHEME pages:")] + page_images(ms) + [text_block(ask)])
    sysp = system_prompt()
    cost, tries = 0.0, 0
    r = run(sysp, content, schema=SCHEMA, model=model, step="extract", ref=pid)
    cost += r["cost_usd"] or 0
    tries += 1
    norm_qnums(r["result"])
    if legacy:
        r["result"]["questions"] = [q for q in r["result"]["questions"] if q["q_num"] in kept]
        r["result"]["excluded_questions"] = excluded
    fixed = autofix(r["result"])
    paper = assemble(pid, x, r["result"], model)
    target.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n")
    errs = [e for e in check_questions.check(target) if not e.startswith("NOTICE")]
    if errs:
        first = r["result"]
        fix = content + [text_block("Your previous output:\n" + json.dumps(first, ensure_ascii=False)
                                    + "\n\nThe validator (which compares against the QP/MS text) reported:\n- "
                                    + "\n- ".join(errs[:60])
                                    + "\n\nRe-read the pages concerned. Return ONLY the question objects (and/or "
                                      "excluded_questions entries) that need changing, each complete, plus paper_total. "
                                      "Omit every question that is already right.")]
        r = run(sysp, fix, schema=SCHEMA, model=model, step="extract-retry", ref=pid)
        cost += r["cost_usd"] or 0
        tries += 1
        patch = r["result"]
        norm_qnums(patch)
        changed = {q["q_num"] for q in patch["questions"]} | {q["q_num"] for q in patch["excluded_questions"]}
        merged = {"paper_total": patch["paper_total"], "pearson_errors": first.get("pearson_errors", []),
                  "questions": sorted([q for q in first["questions"] if q["q_num"] not in changed] + patch["questions"],
                                      key=lambda q: int(q["q_num"])),
                  "excluded_questions": sorted([q for q in first["excluded_questions"] if q["q_num"] not in changed]
                                               + patch["excluded_questions"], key=lambda q: int(q["q_num"]))}
        if legacy:
            merged["questions"] = [q for q in merged["questions"] if q["q_num"] in kept]
            merged["excluded_questions"] = excluded
        fixed += autofix(merged)
        paper = assemble(pid, x, merged, model)
        paper["extraction_retries"] = 1
        paper["pages_input"] = pages
        target.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n")
        errs = [e for e in check_questions.check(target) if not e.startswith("NOTICE")]
    paper["autofixes"] = fixed
    if legacy:
        paper["triage_method"] = "triage-v1"
    target.write_text(json.dumps(paper, indent=2, ensure_ascii=False) + "\n")
    return {"paper_id": pid, "ok": not errs, "autofixes": fixed, "errors": errs[:20], "calls": tries, "cost_usd": round(cost, 3),
            "questions": len(paper["questions"]), "excluded": len(paper.get("excluded_questions", []))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--out", default="_staging", help="folder under data/processed (use _trial for comparisons)")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--parallel", type=int, default=3, help="concurrent calls (the user's cap is 5)")
    ap.add_argument("--pages", choices=["png", "pdf"], default="png")
    a = ap.parse_args()
    ids = a.paper_ids
    if a.todo:
        man = json.loads(MANIFEST.read_text())
        have = {d["paper_id"]: set() for d in man}
        for d in man:
            if d.get("local_pdf"):
                have[d["paper_id"]].add(d["doc_type"])
        from scope import in_processing_scope
        unit = {d["paper_id"]: d["unit"] for d in man}
        ids = sorted(p for p, s in have.items() if {"QP", "MS"} <= s and "_ALL_" not in p
                     and in_processing_scope(p, unit.get(p))             # user scope: S1/M1 only (scope.py)
                     and not (PROC / "_staging" / f"{p}.json").exists())
    if a.only:
        ids = [i for i in ids if re.search(a.only, i)]
    ids = ids[: a.limit] if a.limit else ids
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda p: _safe(p, a.out, a.model, a.pages), ids):
            print(json.dumps(res), flush=True)


def _safe(pid, out, model, pages):
    try:
        return extract(pid, out, model, pages)
    except Exception as e:  # one bad paper must not stop a batch
        return {"paper_id": pid, "ok": False, "errors": [f"{type(e).__name__}: {e}"[:300]]}


if __name__ == "__main__":
    main()
