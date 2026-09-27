#!/usr/bin/env python3
"""Repair part structure in a _staging (or questions/) file when check_questions.py reports
"part marks [...] but the QP prints [...]": scripted, so fixes are reproducible and logged.

    fix_parts.py P3_Oct2021_stats merge Q4 "b(i)" "b(ii)" b     # join adjacent parts under one label
    fix_parts.py P3_June2023_stats split Q6 e "e(i)" "e(ii)" "\n(ii)"
                 # split part e before the first occurrence of the separator, in text AND mark scheme;
                 # the first piece's marks come from its trailing "(N)"
    fix_parts.py P3_June2025_stats marks                        # append "\n(N)" to part texts lacking it
    fix_parts.py P3_June2025_stats replace Q1 c text "of the two beads" "of the beads" "QP p.5 says ..."
    add --final to act on data/processed/questions/

Every change appends a provenance line to the question's `notes`, and derived
question_text / mark_scheme_text are rebuilt. Rerun check_questions.py afterwards.
"""
import json
import re
import sys
from pathlib import Path

from check_questions import derived

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
MARK_END = re.compile(r"\((\d+)(?: marks?)?\)\s*$")


def note(q: dict, msg: str) -> None:
    q["notes"] = (q.get("notes") or "").rstrip() + ("\n" if q.get("notes") else "") + f"[fix_parts] {msg}"


def rebuild(q: dict) -> None:
    q["question_text"], q["mark_scheme_text"] = derived(q)


def merge(q: dict, a: str, b: str, new: str) -> None:
    labels = [p["label"] for p in q["parts"]]
    i = labels.index(a)
    if labels[i + 1] != b:
        raise SystemExit(f"{q['id']}: {a} and {b} are not adjacent")
    pa, pb = q["parts"][i], q["parts"][i + 1]
    pa["text"] = MARK_END.sub("", pa["text"]).rstrip() + "\n" + pb["text"]
    pa["mark_scheme"] = pa["mark_scheme"].rstrip() + "\n" + pb["mark_scheme"]
    pa["marks"] += pb["marks"]
    pa["spec_refs"] = list(dict.fromkeys((pa.get("spec_refs") or []) + (pb.get("spec_refs") or [])))
    pa["label"] = new
    del q["parts"][i + 1]
    note(q, f"merged parts {a} + {b} into {new}: the QP prints one mark total for both")


def split(q: dict, lab: str, l1: str, l2: str, sep: str) -> None:
    labels = [p["label"] for p in q["parts"]]
    i = labels.index(lab)
    p = q["parts"][i]
    t1, s, t2 = p["text"].partition(sep)
    m1, s2, m2 = p["mark_scheme"].partition(sep)
    if not s or not s2:
        raise SystemExit(f"{q['id']}({lab}): separator {sep!r} not found in both text and mark scheme")
    mk = MARK_END.search(t1)
    if not mk:
        raise SystemExit(f"{q['id']}({lab}): first piece has no trailing '(N)'")
    first = int(mk.group(1))
    a = {**p, "label": l1, "text": t1.rstrip(), "mark_scheme": m1.rstrip(), "marks": first}
    b = {**p, "label": l2, "text": sep.lstrip("\n") + t2, "mark_scheme": sep.lstrip("\n") + m2,
         "marks": p["marks"] - first}
    q["parts"][i:i + 1] = [a, b]
    note(q, f"split part {lab} into {l1} ({first}) + {l2} ({p['marks'] - first}): the QP prints separate marks")


def add_marks(q: dict) -> int:
    n = 0
    for p in q["parts"]:
        if not MARK_END.search(p["text"]):
            p["text"] = p["text"].rstrip() + f"\n({p['marks']})"
            n += 1
    if n:
        note(q, f"appended the printed '(N)' mark token to {n} part text(s)")
    return n


MARK_LINE = re.compile(r"^\((\d+)(?: marks?)?\)\s*$")


def move_leadins(q: dict) -> int:
    """Old GCE / IAL 2013 layouts print lines BETWEEN parts ("Given that x3 = 7,", "This tangent meets the x-axis
    at (k, 0)."). Extraction tended to attach them to the END of the previous part, after its printed "(N)", and
    autofix then appended a second "(N)" (the blind Tier 3 audit found 11 such stray marks in 6 papers). Move a
    non-last part's trailing lines to the start of the next part; for the last part (a closing instruction such as
    "On each diagram, show ..."), keep them before its mark. A second mark line is dropped only when it equals the
    first and the part's marks."""
    n, ps = 0, q["parts"]
    single = len(ps) == 1 and q.get("stem", "").strip() == ps[0]["text"].strip()   # single-part: stem == part text
    for i, p in enumerate(ps):
        lines = p["text"].rstrip().split("\n")
        idx = [j for j, l in enumerate(lines) if MARK_LINE.match(l.strip())]
        if not idx or idx[0] == len(lines) - 1 or int(MARK_LINE.match(lines[idx[0]].strip()).group(1)) != p["marks"]:
            continue
        first, tail = lines[idx[0]], lines[idx[0] + 1:]
        if tail and MARK_LINE.match(tail[-1].strip()):
            if len(idx) != 2 or tail[-1].strip() != first.strip():
                continue                                   # a different bracket: not ours to guess at
            tail = tail[:-1]
        tail = [t for t in tail if t.strip()] if not any(t.strip() for t in tail) else tail
        moved = "\n".join(tail).strip("\n")
        if not moved:
            p["text"] = "\n".join(lines[:idx[0] + 1]); n += 1
            continue
        if i < len(ps) - 1:
            p["text"] = "\n".join(lines[:idx[0] + 1])
            ps[i + 1]["text"] = moved + "\n" + ps[i + 1]["text"]
            note(q, f"moved lead-in after ({p['label']})'s mark to the start of ({ps[i + 1]['label']}): {moved[:60]!r}")
        else:
            p["text"] = "\n".join(lines[:idx[0]] + [moved, first])
            note(q, f"kept the closing instruction of ({p['label']}) before its mark: {moved[:60]!r}")
        n += 1
    if single and n:
        q["stem"] = ps[0]["text"]
    return n


def main() -> None:
    if sys.argv[1:2] == ["--all-leadins"]:           # every staging file (or --final: questions/)
        folder = PROC / ("questions" if "--final" in sys.argv else "_staging")
        total = 0
        for path in sorted(folder.glob("*.json")):
            d = json.loads(path.read_text())
            k = 0
            for q in d.get("questions", []):
                m = move_leadins(q)
                if m:
                    rebuild(q); k += m
            if k:
                path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); total += k
                print(f"{path.stem}: {k} part(s)")
        print("TOTAL", total)
        return
    args = [a for a in sys.argv[1:] if a != "--final"]
    path = PROC / ("questions" if "--final" in sys.argv else "_staging") / f"{args[0]}.json"
    d = json.loads(path.read_text())
    op = args[1]
    qs = {f"Q{q['q_num']}": q for q in d["questions"]}
    if op == "merge":
        merge(qs[args[2]], args[3], args[4], args[5]); rebuild(qs[args[2]])
    elif op == "split":
        split(qs[args[2]], args[3], args[4], args[5], args[6].encode().decode("unicode_escape")); rebuild(qs[args[2]])
    elif op == "marks":
        print(sum(add_marks(q) for q in d["questions"]), "part text(s) given a mark token")
        for q in d["questions"]:
            rebuild(q)
    elif op == "replace":                  # replace Q label field old new "reason"
        q = qs[args[2]]
        part = next(p for p in q["parts"] if (p["label"] or "-") == args[3])
        field, old, new, why = args[4], args[5], args[6], args[7]
        if part[field].count(old) != 1:
            raise SystemExit(f"{q['id']}({args[3]}) {field}: {old!r} found {part[field].count(old)} times, need exactly 1")
        part[field] = part[field].replace(old, new)
        note(q, f"({args[3]}) {field}: {old!r} -> {new!r} ({why})")
        rebuild(q)
    else:
        raise SystemExit(f"unknown op {op}")
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
