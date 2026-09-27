#!/usr/bin/env python3
"""Lever D (2026-09-26): examiner-report notes for one paper with small model calls, not an agent.

v2 design ("classify, don't copy"): the SCRIPT splits the report text (pdftotext -raw, the text
every quote is checked against) into numbered sentences, and the model only CLASSIFIES each one:
which kept question/part it is about, did_well / pitfall / general, skip (boilerplate or about a
dropped question), and whether it continues the previous sentence's note. So:
  - every quote is verbatim by construction (the script slices it; no retyping, no retries);
  - coverage is measurable (every sentence gets a decision);
  - output is small (indices, not text).
A second small call repairs garbled maths (`display`) for the flagged sentences only, seeing just
those report pages as images.

v1 (model copies quotes) measured on P3_June2022_stats: 74 notes / 78% of the report covered / 2
ratings, vs the agent's 103 / 90% / 13, so it was replaced. Measured results for v2 are in
docs/skill-add-papers-pipeline.md.

    .venv/bin/python scripts/notes_single.py P3_June2022_stats [more] [--out DIR] [--model claude-sonnet-5]

Output: data/processed/examiner_notes/<paper_id>.json with "notes_method": "classify-v2".
Validate: .venv/bin/python scripts/check_examiner_notes.py <paper_id>
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import build_db
import extract_single as ex
from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
METHOD = "classify-v2"
HEADING = re.compile(r"^\s*(Question|Q)\s*(\d+)\s*[.:]?\s*(\(.*\))?\s*$", re.I)
SENT_END = re.compile(r"(?<!\be\.g)(?<!\bi\.e)(?<!\betc)(?<!\bvs)(?<=[.!?])\s+(?=[A-Z“\"(‘'•])")

SEG = {"type": "object", "additionalProperties": False,
       "required": ["i", "skip", "q_num", "part_label", "kind", "join_prev", "garbled"],
       "properties": {"i": {"type": "integer"}, "skip": {"type": "boolean"},
                      "q_num": {"type": ["string", "null"], "description": "question number like '5'; null = paper-level"},
                      "part_label": {"type": ["string", "null"]},
                      "kind": {"enum": ["did_well", "pitfall", "general"]},
                      "join_prev": {"type": "boolean", "description": "same point as the previous kept sentence: merge into one note"},
                      "garbled": {"type": "boolean", "description": "maths or spacing visibly garbled by pdftotext"}}}
PERF = {"type": "object", "additionalProperties": False,
        "required": ["q_num", "part_label", "mean_mark", "max_mark", "rating", "evidence_i", "full_marks_pct", "full_marks_pct_i"],
        "properties": {"q_num": {"type": "string"}, "part_label": {"type": ["string", "null"]},
                       "mean_mark": {"type": ["number", "null"]}, "max_mark": {"type": ["integer", "null"]},
                       "rating": {"enum": ["well_answered", "mixed", "poorly_answered", None]},
                       "evidence_i": {"type": ["integer", "null"], "description": "sentence index stating the rating"},
                       "full_marks_pct": {"type": ["number", "null"]}, "full_marks_pct_i": {"type": ["integer", "null"]}}}
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["segments", "performance"],
          "properties": {"segments": {"type": "array", "items": SEG}, "performance": {"type": "array", "items": PERF}}}
DISPLAY = {"type": "object", "additionalProperties": False, "required": ["repairs"],
           "properties": {"repairs": {"type": "array", "items": {
               "type": "object", "additionalProperties": False, "required": ["i", "display"],
               "properties": {"i": {"type": "integer"}, "display": {"type": ["string", "null"]}}}}}}


def segments(text: str) -> list[dict]:
    """Numbered sentences with their page. Headings and bullet lines are their own segments."""
    out, buf, page = [], [], 1
    def flush():
        para = " ".join(" ".join(buf).split())
        for s in SENT_END.split(para) if para else []:
            if s.strip():
                out.append({"text": s.strip(), "page": buf_page[0]})
        buf.clear()
    buf_page = [1]
    for raw_line in text.split("\n"):
        for k, line in enumerate(raw_line.split("\f")):
            if k:
                page += 1
            s = line.strip()
            if not s:
                flush(); buf_page[0] = page
                continue
            if HEADING.match(s) or s.startswith(("•", "\uf0b7", "- ")):
                flush(); buf_page[0] = page
                if HEADING.match(s):
                    out.append({"text": s, "page": page, "heading": True})
                    continue
            if not buf:
                buf_page[0] = page
            buf.append(s)
    flush()
    return out


def system_prompt() -> str:
    spec = (ROOT / "docs" / "examiner-notes-extraction.md").read_text()
    return f"""You classify the sentences of a Pearson examiner report for a revision-tutor chatbot. The report is given as numbered sentences, which a script turns into verbatim notes: you never copy or retype text, only classify.

The rules for what a note is, `kind`, part labels and performance ratings are in this spec (ignore its instructions about writing quotes, ids or files):
<spec>
{spec}
</spec>

For EVERY sentence index return one segment:
- skip=true for boilerplate (Pearson info, grade boundaries, headers, footers, page numbers), bare headings, and ANY sentence about a question that is not in QUESTIONS (those questions were removed from the knowledge base and must not influence it).
- Otherwise q_num (the question it's about; null for paper-level remarks), part_label (a part from QUESTIONS, or null for the whole question), and kind.
- Assign the part by CONTENT when the report's wording and the question paper disagree (reports sometimes cite the wrong part letter): match the method described to the part in QUESTIONS.
- join_prev=true when the sentence continues the same point as the previous kept sentence (a note is 1–3 consecutive sentences on one point).
- garbled=true when pdftotext has visibly garbled maths or run words together in it.
Kinds: a sentence that says what candidates DID is did_well (they succeeded, e.g. "most found the correct mean", "usually scored both marks") or pitfall (they failed, erred or omitted something). Use general only for advice, context, or remarks that describe neither. When a sentence has both, choose the main point.
Performance: rate EVERY question and part whose own section characterises how it went, including wording like "a good start to the paper", "generally well answered", "caused more problems", "mixed success", "few scored full marks", "accessible", "discriminating". One row per (question, part), with evidence_i = the index of the sentence that says it. Include mean marks or % full marks only when printed. The question's own section outranks the introduction.
"""


def question_list(qfile: Path) -> tuple[str, dict]:
    d = json.loads(qfile.read_text())
    lines, parts = [], {}
    for q in d["questions"]:
        parts[q["q_num"]] = [p["label"] for p in q["parts"]]
        plines = "; ".join(f"({p['label'] or '-'}) " + re.sub(r"\s+", " ", p["text"])[:110] for p in q["parts"])
        lines.append(f"Q{q['q_num']} ({q['total_marks']} marks): {re.sub(chr(10), ' ', q['stem'] or '')[:120]} | {plines}")
    return "\n".join(lines), parts


def norm_q(q):
    if q is None:
        return None
    m = re.search(r"\d+", str(q))
    return m.group(0) if m else None


def notes(pid: str, model: str, out_dir: Path) -> dict:
    qfile = PROC / "questions" / f"{pid}.json"
    x = ex.manifest_entry(pid)
    rel = f"pearson/{x['qualification']}/{x['sitting']}/{pid}_ER"
    er_txt = (ROOT / "data" / "raw" / f"{rel}.txt").read_text()
    pages = er_txt.split("\f")
    qlist, parts = question_list(qfile)
    if not parts:
        return {"paper_id": pid, "skipped": "no kept questions"}
    segs = segments(er_txt)
    numbered = "\n".join(f"[{i}]{' (HEADING)' if s.get('heading') else ''} {s['text']}" for i, s in enumerate(segs))
    content = [text_block(f"QUESTIONS in the knowledge base ({pid}):\n{qlist}"),
               text_block(f"REPORT SENTENCES:\n{numbered}\n\nClassify every sentence and return the JSON.")]
    r = run(system_prompt(), content, schema=SCHEMA, model=model, step="notes-classify", ref=pid, thinking_tokens=4000)
    cost, res = r["cost_usd"] or 0, r["result"]
    by_i = {s["i"]: s for s in res["segments"] if 0 <= s["i"] < len(segs)}
    missing = [i for i, s in enumerate(segs) if i not in by_i and not s.get("heading")]

    # garbled maths: repair display for flagged sentences, looking only at their pages
    flagged = [i for i, s in by_i.items() if s["garbled"] and not s["skip"]]
    display = {}
    if flagged:
        pdf = ROOT / "data" / "raw" / f"{rel}.pdf"
        pg = sorted({segs[i]["page"] for i in flagged})
        imgs = []
        for p in pg:
            one = ex.TRIM / f"{pid}_ER.p{p}.pdf"
            ex.TRIM.mkdir(parents=True, exist_ok=True)
            import subprocess
            subprocess.run(["pdfseparate", "-f", str(p), "-l", str(p), str(pdf), str(one)], check=True)
            imgs += [text_block(f"Report page {p}:")] + ex.page_images(one, 110)
            one.unlink()
        ask = ("For each sentence below, give `display`: the same sentence with ONLY the garbled maths repaired (in "
               "LaTeX $…$) or run-together words re-spaced, reading the page image. Words must stay the same. null if "
               "you can't tell.\n" + "\n".join(f"[{i}] (page {segs[i]['page']}) {segs[i]['text']}" for i in flagged))
        d = run("You repair pdftotext-garbled maths in examiner-report sentences by reading the page images. Never "
                "change, add or remove words.", imgs + [text_block(ask)], schema=DISPLAY, model=model,
                step="notes-display", ref=pid, thinking_tokens=2000)
        cost += d["cost_usd"] or 0
        display = {x_["i"]: x_["display"] for x_ in d["result"]["repairs"] if x_["i"] in flagged}

    # build notes: merge join_prev runs (max 3 sentences), same question/part/kind
    notes_out, idx_to_id, counters, cur = [], {}, {}, None
    dropped = {"not_kept": 0, "bad_label": 0}
    def close():
        nonlocal cur
        if cur:
            key = cur["qid"] or f"{pid}_G"
            counters[key] = counters.get(key, 0) + 1
            nid = f"{key}_n{counters[key]}"
            quote = " ".join(segs[i]["text"] for i in cur["idx"])
            disp = [display.get(i) for i in cur["idx"]]
            notes_out.append({"id": nid, "question_id": cur["qid"], "part_label": cur["lab"], "kind": cur["kind"],
                              "quote": quote,
                              "display": " ".join(dd or segs[i]["text"] for dd, i in zip(disp, cur["idx"]))
                              if any(disp) else None})
            for i in cur["idx"]:
                idx_to_id[i] = nid
        cur = None
    for i in range(len(segs)):
        s = by_i.get(i)
        if not s or s["skip"] or segs[i].get("heading"):
            continue
        qn = norm_q(s["q_num"])
        if qn is not None and qn not in parts:
            dropped["not_kept"] += 1
            continue
        lab = s["part_label"]
        if lab is not None:
            lab = lab.strip("() ").lower() or None
        if lab is not None and qn is not None and not build_db.part_label_matches(lab, parts[qn]):
            dropped["bad_label"] += 1
            lab = None
        qid = f"{pid}_Q{qn}" if qn else None
        if cur and s["join_prev"] and cur["qid"] == qid and cur["lab"] == lab and cur["kind"] == s["kind"] \
                and len(cur["idx"]) < 3 and cur["idx"][-1] == i - 1:
            cur["idx"].append(i)
        else:
            close()
            cur = {"qid": qid, "lab": lab, "kind": s["kind"], "idx": [i]}
    close()
    perf, seen = [], set()
    for p in res["performance"]:
        qn = norm_q(p["q_num"])
        lab = (p["part_label"] or "").strip("() ").lower() or None
        if qn not in parts or (qn, lab) in seen:
            continue
        seen.add((qn, lab))
        ev, fm = idx_to_id.get(p["evidence_i"]), idx_to_id.get(p["full_marks_pct_i"])
        perf.append({"question_id": f"{pid}_Q{qn}", "part_label": lab, "mean_mark": p["mean_mark"],
                     "max_mark": p["max_mark"], "rating": p["rating"] if ev else None, "evidence_note_id": ev,
                     "full_marks_pct": p["full_marks_pct"] if fm else None, "full_marks_pct_note_id": fm})
    # verbatim guarantee (belt and braces): the quotes are slices, but check exactly as build_db does
    bad = [n["id"] for n in notes_out if build_db.find_quote_page(n["quote"], pages) is None]
    notes_out = [n for n in notes_out if n["id"] not in bad]
    data = {"_paper_id": pid, "_paper": x["unit_name"] if x["qualification"] == "9MA0" else x["unit"],
            "_sitting": x["sitting"], "source_file": f"{rel}.txt", "notes_method": METHOD, "notes_model": model,
            "notes": notes_out, "performance": perf}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{pid}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    kept_chars = sum(len(n["quote"]) for n in notes_out)
    return {"paper_id": pid, "notes": len(notes_out), "performance": len(perf),
            "ratings": sum(1 for p in perf if p["rating"]), "sentences": len(segs), "unclassified": len(missing),
            "displays": sum(1 for n in notes_out if n["display"]), "not_verbatim": len(bad), "dropped": dropped,
            "covered_chars": kept_chars, "cost_usd": round(cost, 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="+")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--out", default=str(PROC / "examiner_notes"))
    ap.add_argument("--parallel", type=int, default=3)
    a = ap.parse_args()
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda p: _safe(p, a.model, Path(a.out)), a.paper_ids):
            print(json.dumps(res), flush=True)


def _safe(pid, model, out):
    try:
        return notes(pid, model, out)
    except Exception as e:
        import traceback
        return {"paper_id": pid, "error": f"{type(e).__name__}: {e}"[:300], "tb": traceback.format_exc()[-600:]}


if __name__ == "__main__":
    main()
