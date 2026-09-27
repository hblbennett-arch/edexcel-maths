#!/usr/bin/env python3
"""Apply mark-scheme audit changes (Phase 2d; see docs/ms-audit-spec.md).

Audit agents write data/processed/_ms_audit/<paper>_<sitting>.json listing
changes to mark_scheme_text (default) or question_text ("field": "question_text").
This script validates and applies them to the full field and to the matching
part (parts are slices of the full text, so the same replacement is made in
both; question-text changes inside the stem are applied to the stem).

    .venv/bin/python scripts/apply_ms_audit.py --check P1_June2022   # validate one file
    .venv/bin/python scripts/apply_ms_audit.py --check               # validate all
    .venv/bin/python scripts/apply_ms_audit.py --apply               # apply all (skips applied ones)
    .venv/bin/python scripts/apply_ms_audit.py --report              # write docs/ms-audit-report.md

Rules enforced: each `old` occurs exactly once in its question's
mark_scheme_text; `editorial` changes only wrap text as "[editor: …]";
every question in the paper is listed in `checked`. Applied changes are
recorded in the question's notes, and the audit file is marked applied.
"""
import json
import os
import sys
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
# Overridable so audits of comparison copies (e.g. _trial/) can be checked without touching questions/.
QUESTIONS_DIR = Path(os.environ.get("AUDIT_QUESTIONS_DIR", PROCESSED_DIR / "questions"))
AUDIT_DIR = Path(os.environ.get("AUDIT_DIR", PROCESSED_DIR / "_ms_audit"))
RESPLIT: set[str] = set()  # questions whose parts must be regenerated after --apply


def validate(audit: dict, questions: dict[str, dict]) -> list[str]:
    errors = []
    missing = set(questions) - set(audit.get("checked", []))
    if missing:
        errors.append(f"questions not listed in 'checked': {sorted(missing)}")
    for i, ch in enumerate(audit["changes"]):
        where = f"change {i} ({ch.get('question_id')})"
        q = questions.get(ch.get("question_id"))
        if q is None:
            errors.append(f"{where}: unknown question_id")
            continue
        if ch.get("type") not in ("editorial", "correction"):
            errors.append(f"{where}: type must be 'editorial' or 'correction'")
        field = ch.get("field", "mark_scheme_text")
        if field not in ("mark_scheme_text", "question_text"):
            errors.append(f"{where}: field must be 'mark_scheme_text' or 'question_text'")
            continue
        count = q[field].count(ch["old"])
        if count != 1:
            errors.append(f"{where}: 'old' found {count} times (must be exactly 1): {ch['old'][:70]!r}")
        if ch.get("type") == "editorial" and ch["new"] != f"[editor: {ch['old'].strip('()').strip()}]" \
                and ch["new"] != f"[editor: {ch['old']}]":
            errors.append(f"{where}: editorial 'new' must be '[editor: <old>]' (optionally without its outer brackets)")
        if ch.get("type") == "correction" and not (ch.get("evidence") or "aside" in ch.get("reason", "")):
            errors.append(f"{where}: correction needs 'evidence' (MS line / PDF page)")
    # Overlapping changes within one question would make the result order-dependent.
    by_q: dict[str, list] = {}
    for ch in audit["changes"]:
        q = questions.get(ch.get("question_id"))
        field = ch.get("field", "mark_scheme_text")
        if q and field in q and q[field].count(ch["old"]) == 1:
            start = q[field].index(ch["old"])
            by_q.setdefault((ch["question_id"], field), []).append((start, start + len(ch["old"])))
    for qid, spans in by_q.items():
        spans.sort()
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            errors.append(f"{qid[0]} {qid[1]}: overlapping changes")
    return errors


def apply(audit: dict, questions: dict[str, dict]) -> int:
    n = 0
    for ch in audit["changes"]:
        q = questions[ch["question_id"]]
        field = ch.get("field", "mark_scheme_text")
        part_key = "mark_scheme" if field == "mark_scheme_text" else "text"
        q[field] = q[field].replace(ch["old"], ch["new"], 1)
        in_stem = field == "question_text" and bool(q.get("stem")) and ch["old"] in q["stem"]
        if in_stem:
            q["stem"] = q["stem"].replace(ch["old"], ch["new"], 1)
            if not any(ch["old"] in p[part_key] for p in q["parts"]):
                n += 1
                continue  # stem only (a single-part question's text is both stem and part)
        hits = [p for p in q["parts"] if ch["old"] in p[part_key]]
        if len(hits) != 1:
            # The change crosses a stem/part boundary (e.g. a sentence moved back to where
            # the paper has it): the full field is updated; the parts must be re-split.
            RESPLIT.add(ch["question_id"])
            n += 1
            continue
        hits[0][part_key] = hits[0][part_key].replace(ch["old"], ch["new"], 1)
        n += 1
    counts: dict[str, dict[str, int]] = {}
    for ch in audit["changes"]:
        counts.setdefault(ch["question_id"], {"editorial": 0, "correction": 0})[ch["type"]] += 1
    for qid, c in counts.items():
        q = questions[qid]
        note = (f"MS audit 2026-09-25: {c['editorial']} editorial aside(s) marked [editor: …], "
                f"{c['correction']} correction(s) vs official MS (see docs/ms-audit-report.md).")
        q["notes"] = (q["notes"] + " " if q["notes"] else "") + note
    return n


def write_report() -> None:
    """Human-readable list of every correction (with evidence) and editorial count."""
    audits = [dict(json.loads(p.read_text()), _file=p.stem) for p in sorted(AUDIT_DIR.glob("*.json"))]
    rows, lines = {}, []
    for a in audits:
        key = a.get("_paper_id") or f"{a['_paper']}_{a['_sitting']}"
        r = rows.setdefault(key, {"ms_ed": 0, "ms_corr": 0, "qp_ed": 0, "qp_corr": 0})
        for ch in a["changes"]:
            f = "qp" if ch.get("field") == "question_text" else "ms"
            r[f"{f}_{'ed' if ch['type'] == 'editorial' else 'corr'}"] += 1
    total = {k: sum(r[k] for r in rows.values()) for k in ("ms_ed", "ms_corr", "qp_ed", "qp_corr")}
    lines += ["# Mark Scheme & Question Text Audit Report (Phase 2d)", "",
              "Every transcribed mark scheme and question was compared with the official Pearson PDFs "
              "(rules: `docs/ms-audit-spec.md`; raw change lists: `data/processed/_ms_audit/`).",
              "- **Corrections** fix factual mismatches (wrong numbers, signs, mark codes, missing conditions); "
              "each cites the MS/QP page it was checked against.",
              "- **Editorial** changes wrap extractor-added explanation as `[editor: …]`; nothing was deleted.", "",
              "## Summary", "", "| Paper | MS editorial | MS corrections | Question editorial | Question corrections |",
              "|---|---|---|---|---|"]
    for key, r in sorted(rows.items()):
        lines.append(f"| {key} | {r['ms_ed']} | {r['ms_corr']} | {r['qp_ed']} | {r['qp_corr']} |")
    lines.append(f"| **Total** | {total['ms_ed']} | {total['ms_corr']} | {total['qp_ed']} | {total['qp_corr']} |")
    lines += ["", "## Every correction (please spot-check a few against the PDFs)", ""]
    for a in audits:
        corr = [c for c in a["changes"] if c["type"] == "correction"]
        if not corr:
            continue
        lines.append(f"### {a['_paper']} {a['_sitting']}" + (" (question-text pass)" if a["_file"].endswith("_qp") else ""))
        for c in corr:
            field = "question" if c.get("field") == "question_text" else "MS"
            lines.append(f"- [ ] **{c['question_id']}** ({field}): `{c['old'][:160]}` → `{c['new'][:160]}`  \n"
                         f"  _{c.get('reason', '')}_ — evidence: {c.get('evidence', 'n/a')}")
        lines.append("")
    Path(PROCESSED_DIR.parent.parent / "docs" / "ms-audit-report.md").write_text("\n".join(lines) + "\n")
    print(f"wrote docs/ms-audit-report.md — {total['ms_corr'] + total['qp_corr']} corrections, "
          f"{total['ms_ed'] + total['qp_ed']} editorial")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode == "--report":
        write_report()
        return
    stems = sys.argv[2:] or [p.stem for p in sorted(AUDIT_DIR.glob("*.json"))]
    failed = False
    for stem in stems:
        audit_path = AUDIT_DIR / f"{stem}.json"
        audit = json.loads(audit_path.read_text())
        # Audit files are <paper>_<sitting>.json, or <paper>_<sitting>_qp.json for a
        # separate question-text pass; both apply to the same question file.
        q_path = QUESTIONS_DIR / f"{audit.get('_paper_id') or audit['_paper'] + '_' + audit['_sitting']}.json"
        data = json.loads(q_path.read_text())
        questions = {q["id"]: q for q in data["questions"]}
        if audit.get("_applied"):
            print(f"SKIP {stem}: already applied")
            continue
        errors = validate(audit, questions)
        if errors:
            failed = True
            print(f"FAIL {stem}:")
            for e in errors:
                print(f"    {e}")
            continue
        kinds = [c["type"] for c in audit["changes"]]
        if mode == "--apply":
            n = apply(audit, questions)
            q_path.write_text(json.dumps(data, indent=2) + "\n")
            audit["_applied"] = True
            audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n")
            print(f"APPLIED {stem}: {n} change(s)")
        else:
            print(f"OK   {stem}: {kinds.count('editorial')} editorial, {kinds.count('correction')} correction(s)")
    if RESPLIT:
        print(f"Re-split needed (change crossed a part boundary): {sorted(RESPLIT)}")
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
