#!/usr/bin/env python3
"""Visual mark-scheme verification: find maths/value errors in each part's transcribed mark scheme.

Why: the blind Opus audit of 6 Tier 3 papers (2026-09-27) found ~5 value/structure errors in ~1,090 expressions,
all in mark schemes (a root over the wrong span, a dropped root, 12/25 for 13/25, 32/75 for 12/75, x for x/3).
Text layers can't settle fraction or root structure, so one call per paper compares the transcription with the
official MS page images and returns CORRECTIONS only (old -> new).

Deterministic guards (a correction is applied only if all hold):
  - `old` occurs exactly once in that part's mark_scheme, and new != old;
  - words (outside $...$) in `new` that aren't in `old` appear, in order, in the MS text layer;
  - decimals in `new` are in the MS text layer (as check_questions);
  - an integer fraction a/b that `new` introduces is visible in the MS text layout, stacked or inline
    (fraction_in_ms); otherwise the correction is held for review instead of applied.
The fraction check's suspects (fractions in the transcription NOT visible in the MS layout) are also given to the
model as places to look first.

    .venv/bin/python scripts/ms_verify.py <ids> [--src DIR] [--out DIR]    # pilot: read DIR, write copies
    .venv/bin/python scripts/ms_verify.py --todo --only '^(IAL2013|GCE2008)_'
Each paper records "ms_verify_method"; applied fixes go in the question's notes, and the log (accepted /
held / rejected) in data/processed/_ms_verify/<pid>.json.
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
METHOD = "visual-v1"
FRAC = re.compile(r"\\[dt]?frac\{(\d+)\}\{(\d+)\}")
CODE = re.compile(r"(?<![A-Za-z])(?:[dD]{0,3}[MAB]\d(?:ft|\*)?|B\d)(?![A-Za-z\d])")


def strip_codes(t: str) -> str:
    return re.sub(r"\s+", "", CODE.sub("", t))

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["corrections"],
          "properties": {"corrections": {"type": "array", "items": {
              "type": "object", "additionalProperties": False,
              "required": ["question_id", "label", "old", "new", "page", "why"],
              "properties": {"question_id": {"type": "string"},
                             "label": {"type": "string", "description": "part label as in the transcription, '-' for single-part"},
                             "old": {"type": "string", "description": "exact substring of the transcribed mark scheme"},
                             "new": {"type": "string", "description": "the replacement, matching the official page"},
                             "page": {"type": "integer"},
                             "why": {"type": "string"}}}}}}


fraction_in_ms = cq.fraction_in_ms


def suspects(d: dict, lines: list[str], text: str) -> list[str]:
    out = []
    for q in d["questions"]:
        for p in q["parts"]:
            for a, b in sorted(set(FRAC.findall(p["mark_scheme"]))):
                if not fraction_in_ms(a, b, lines, text):
                    out.append(f"{q['id']} ({p['label'] or '-'}): {a}/{b}")
    return out


def verify(pid: str, model: str, src: Path, out_dir: Path | None) -> dict:
    f = src / f"{pid}.json"
    d = json.loads(f.read_text())
    if not d["questions"]:
        return {"paper_id": pid, "skipped": "no transcribed questions"}
    if d.get("ms_verify_method") and out_dir is None:
        return {"paper_id": pid, "skipped": "already done"}
    x = ex.manifest_entry(pid)
    raw = ROOT / "data" / "raw" / "pearson" / x["qualification"] / x["sitting"]
    ms_pdf, kept = ex.trim_pdf(raw / f"{pid}_MS.pdf", "MS")
    ms_txt = (raw / f"{pid}_MS.txt").read_text(errors="ignore")
    if cq.shifted_font(ms_txt):
        ms_txt = cq.decode_shifted(ms_txt)
    usable = cq.usable_text(ms_txt)
    lines = ms_txt.split("\n")
    ms_words = cq.prose_words(ms_txt, source=True) if usable else []
    ms_nums = cq.plain_numbers(ms_txt) if usable else set()
    sus = suspects(d, lines, ms_txt) if usable else []
    current = "\n\n".join(f"### {q['id']}\n" + "\n".join(f"[part {p['label'] or '-'}] {p['mark_scheme']}" for p in q["parts"])
                          for q in d["questions"])
    imgs = []
    for i, img in zip(kept, ex.page_images(ms_pdf, 130)):
        imgs += [text_block(f"MS PAGE {i}"), img]
    system = ("You proofread transcribed Edexcel mark schemes against the official mark scheme page images. Report "
              "ONLY errors where the transcription's maths or values differ from the page: a wrong number, sign, power, "
              "fraction (which value is over which), root (what is under it), bracket, letter or inequality. Mark codes "
              "(M1, A1ft, ...) are checked by a script, so don't report them. Compare every $...$ expression symbol by symbol. For each error give `old` as an "
              "exact substring of the transcription (short, but unique within that part) and `new` as the corrected "
              "text in the same LaTeX style. Do NOT report missing content, wording or formatting differences, notation "
              "choices ($\\dfrac$ vs $\\frac$), or anything you can't see clearly on the page. If the official mark "
              "scheme itself has an error, keep it (the transcription copies the page). Only the questions listed are "
              "in scope; most papers have no errors.")
    hint = ("\n\nFractions in the transcription that a script couldn't find in the MS text layer (the MS may draw them "
            "as graphics, so most are fine; check these first):\n- " + "\n- ".join(sus)) if sus else ""
    r = run(system, [text_block("OFFICIAL MARK SCHEME pages:")] + imgs +
            [text_block("TRANSCRIPTION (per part):\n" + current + hint + "\n\nReturn the corrections JSON (empty list if none).")],
            schema=SCHEMA, model=model, step="ms-verify", ref=pid, thinking_tokens=6000, max_usd=3.0)
    from triage_spec import norm_label
    by_q = {q["id"]: q for q in d["questions"]}
    accepted, held, rejected = [], [], []
    for c in r["result"]["corrections"]:
        q = by_q.get(c["question_id"])
        lab = None if c["label"].strip() in ("-", "") else norm_label(c["label"])
        part = next((p for p in (q["parts"] if q else []) if p["label"] == lab), None)
        why = None
        if not part:
            why = "unknown question/part"
        elif c["old"] == c["new"] or part["mark_scheme"].count(c["old"]) != 1:
            why = f"old found {part['mark_scheme'].count(c['old'])} times in the part (need 1)" if c["old"] != c["new"] else "no change"
        elif usable:
            new_words = [w for w in cq.prose_words(c["new"]) if w not in cq.prose_words(c["old"])]
            if new_words and cq.subsequence_gap(new_words, ms_words, restarts=2) is not None:
                why = "new wording not in the MS text"
            elif (miss := [n for n in cq.plain_numbers(c["new"]) if "." in n and not cq.num_in(n, ms_nums)]):
                why = f"decimals not in the MS text: {miss}"
        if not why and usable and strip_codes(c["old"]) == strip_codes(c["new"]):
            # a mark-code-only change: codes are real text in the MS's Marks column, so if the transcription's code
            # is in the text layer it's right (pilot: the model turned a correct "A1ft" into "A1", S1 Jan 2009 Q5(b))
            if all(re.search(rf"(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])", ms_txt) for k in CODE.findall(c["old"])):
                why = "mark-code-only change, and the existing code is in the MS text layer"
        if why:
            rejected.append({**c, "why_rejected": why})
            continue
        fr_new = set(FRAC.findall(c["new"])) - set(FRAC.findall(c["old"]))
        if usable and any(not fraction_in_ms(a, b, lines, ms_txt) for a, b in fr_new):
            held.append({**c, "held": "introduces a fraction not visible in the MS text layout: review on the page"})
            continue
        accepted.append((q, part, c))
    for q, part, c in accepted:
        part["mark_scheme"] = part["mark_scheme"].replace(c["old"], c["new"], 1)
        q["notes"] = (q.get("notes") or "") + ("\n" if q.get("notes") else "") + \
            f"[ms_verify] ({part['label'] or '-'}) {c['old']!r} -> {c['new']!r} (MS p.{c['page']}: {c['why'][:120]})"
    for q in d["questions"]:
        q["question_text"], q["mark_scheme_text"] = cq.derived(q)
    d["ms_verify_method"] = METHOD
    d["ms_verify_fixed"] = len(accepted)
    target = (out_dir or f.parent) / f"{pid}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    log = (out_dir / "_log" if out_dir else PROC / "_ms_verify") / f"{pid}.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps({"_paper_id": pid, "suspects": sus, "accepted": [c for _, _, c in accepted], "held": held,
                               "rejected": rejected, "cost_usd": r["cost_usd"]}, indent=2, ensure_ascii=False) + "\n")
    errs = [e for e in cq.check(target) if not e.startswith("NOTICE")] if out_dir is None else []
    return {"paper_id": pid, "fixed": len(accepted), "held": len(held), "rejected": len(rejected),
            "check_ok": not errs, "errors": errs[:3], "cost_usd": round(r["cost_usd"] or 0, 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_ids", nargs="*")
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--only")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--src", help="folder to read (default _staging)")
    ap.add_argument("--out")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    src = Path(a.src) if a.src else PROC / "_staging"
    ids = a.paper_ids
    if a.todo:
        ids = [p.stem for p in sorted(src.glob("*.json"))
               if json.loads(p.read_text())["questions"] and not json.loads(p.read_text()).get("ms_verify_method")]
    if a.only:
        ids = [i for i in ids if re.search(a.only, i)]
    with ThreadPoolExecutor(max_workers=min(5, a.parallel)) as pool:
        for res in pool.map(lambda p: _safe(p, a.model, src, Path(a.out) if a.out else None), ids):
            print(json.dumps(res), flush=True)


def _safe(pid, model, src, out):
    try:
        return verify(pid, model, src, out)
    except Exception as e:
        return {"paper_id": pid, "error": f"{type(e).__name__}: {e}"[:300]}


if __name__ == "__main__":
    main()
