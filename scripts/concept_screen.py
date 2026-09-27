#!/usr/bin/env python3
"""Second spec check for KEPT legacy questions: do they use a named concept that no 9MA0 statement covers?

Why: triage v2 kept ~15-20 IAL P4 questions on vector equations of lines, the scalar product and volumes
of revolution (Further Maths topics), while dropping others like them. A concept list is more reliable
than asking again in general terms. Each concept is only used if the SCRIPT confirms its key terms are
absent from data/processed/spec_9ma0.json (so the list is grounded in the spec, not memory).

    .venv/bin/python scripts/concept_screen.py --only '^IAL|^GCE'          # screen kept questions
    .venv/bin/python scripts/concept_screen.py --only '^IAL' --apply       # mark hits out_of_spec in _staging

Hits are written to data/processed/_concept_screen/<paper_id>.json. With --apply, each hit's parts get an
out_of_spec entry in the staging file, so apply_spec_filter.py drops the question (full text kept in
_excluded/). Run apply_spec_filter.py --all afterwards.
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from claude_oneshot import run, text_block

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = PROC / "_concept_screen"

# concept -> spec terms that must ALL be absent for the concept to count as "not in 9MA0"
CANDIDATES = {
    "vector equation of a line (r = a + λb), intersection of lines, skew lines": ["vector equation", "skew", "intersection of two lines"],
    "scalar (dot) product, including the angle between vectors or lines": ["scalar product", "dot product", "angle between two vectors"],
    "volume of revolution (solid formed by rotating a region about an axis)": ["revolution", "solid of"],
    "cross (vector) product": ["cross product", "vector product"],
    "matrices": ["matrix", "matrices"],
    "complex numbers": ["complex number"],
    "hyperbolic functions (sinh, cosh, tanh)": ["hyperbolic", "sinh", "cosh"],
    "polar coordinates": ["polar"],
    "Maclaurin or Taylor series": ["maclaurin", "taylor"],
    "reduction formulae": [],        # stated as EXCLUDED in P8.5 guidance; checked below
    "proof by induction": ["induction"],
}


def verified_concepts() -> list[str]:
    stmts = json.loads((PROC / "spec_9ma0.json").read_text())["statements"]
    txt = " ".join((s["text"] + " " + (s.get("guidance") or "")) for s in stmts).lower()
    out = []
    for concept, terms in CANDIDATES.items():
        if concept.startswith("reduction formulae"):
            if "excludes reduction formulae" in txt:
                out.append(concept + " (P8.5 guidance: 'excludes reduction formulae')")
            continue
        if terms and all(t not in txt for t in terms):
            out.append(concept)
    return out


# Deterministic screen (runs with the model screen; a question caught by EITHER is dropped). Measured
# 2026-09-26: the model screen alone missed WMA14 June 2024 Q6 (r = i + 2j + 5k + λ(8i − j + 4k)).
REGEX_SCREEN = {
    # Pure questions only; question text only (a scalar product offered as an ALTERNATIVE method in a mark
    # scheme doesn't make a question out of spec). Mechanics position vectors r = a + tb are 9MA0 (M7.3), μ is
    # friction, and "skew" in Statistics is skewness, so none of those count. (First version matched all of
    # them: 18 false positives, now excluded.)
    "vector equation of a line (r = a + λb), intersection of lines, skew lines":
        re.compile(r"\\mathbf\{r\}\s*=[^$]{0,160}\\lambda|vector equation (for|of) (the )?line|lines? \$?l_?\{?\d?\}?\$? (and \$?l_?\{?\d?\}?\$? )?are skew", re.I),
    "scalar (dot) product, including the angle between vectors or lines":
        re.compile(r"scalar product|dot product|angle between (the )?(lines|vectors)", re.I),
    "volume of revolution (solid formed by rotating a region about an axis)":
        re.compile(r"(rotated|rotating|revolved).{0,80}(2\\pi|360|about the [xy][ -]axis).{0,300}(volume|solid)|solid of revolution", re.I | re.S),
}


def regex_hits(pid: str) -> list[dict]:
    out = []
    for q in json.loads((PROC / "questions" / f"{pid}.json").read_text())["questions"]:
        if q.get("component", "pure") != "pure":
            continue
        text = q["question_text"]
        for concept, rx in REGEX_SCREEN.items():
            m = rx.search(text)
            if m:
                out.append({"question_id": q["id"], "parts": [], "concept": concept,
                            "evidence": "text match: " + " ".join(text[max(0, m.start() - 40):m.end() + 40].split()),
                            "source": "regex"})
                break
    return out


SCHEMA = {"type": "object", "additionalProperties": False, "required": ["hits"],
          "properties": {"hits": {"type": "array", "items": {
              "type": "object", "additionalProperties": False,
              "required": ["question_id", "parts", "concept", "evidence"],
              "properties": {"question_id": {"type": "string"},
                             "parts": {"type": "array", "items": {"type": "string"}},
                             "concept": {"type": "string"}, "evidence": {"type": "string"}}}}}}


def screen(pids: list[str], model: str, concepts: list[str]) -> dict:
    lines = []
    for pid in pids:
        for q in json.loads((PROC / "questions" / f"{pid}.json").read_text())["questions"]:
            lines.append(f"### {q['id']}\n" + " ".join(q["question_text"].split())[:1500]
                         + "\nMS: " + " ".join(q["mark_scheme_text"].split())[:900])
    system = ("You check exam questions for specific Further Maths concepts. The concepts listed are NOT in the "
              "UK A Level Mathematics (9MA0) specification (a script confirmed no 9MA0 statement mentions them). "
              "Report a question ONLY if a part genuinely requires one of them (from its wording or mark scheme), "
              "naming the parts and quoting the evidence. Ordinary 9MA0 vector work (position vectors, magnitude, "
              "distance, parallel vectors, geometric problems), Mechanics kinematics with position vectors (r = r0 + vt, "
              "r = ut + 1/2at^2, when/where particles or ships meet: 9MA0 M7.3) and ordinary integration are NOT hits."
              "\n\nCONCEPTS:\n- "
              + "\n- ".join(concepts))
    r = run(system, [text_block("\n\n".join(lines) + "\n\nReturn the hits JSON (empty list if none).")],
            schema=SCHEMA, model=model, step="concept-screen", ref="+".join(pids), thinking_tokens=2000)
    return {"hits": r["result"]["hits"], "cost": r["cost_usd"] or 0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="^(IAL|GCE)")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--per-call", type=int, default=4)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--regex-only", action="store_true", help="add deterministic hits to existing screen files (no model)")
    a = ap.parse_args()
    concepts = verified_concepts()
    print("concepts verified absent from spec_9ma0.json:", concepts)
    pids = [p.stem for p in sorted((PROC / "questions").glob("*.json"))
            if re.search(a.only, p.stem) and json.loads(p.read_text())["questions"]]
    if a.regex_only:
        OUT.mkdir(exist_ok=True)
        for pid in pids:
            f = OUT / f"{pid}.json"
            d = json.loads(f.read_text()) if f.exists() else {"_paper_id": pid, "concepts": concepts, "hits": []}
            seen = {h["question_id"] for h in d["hits"]}
            new = [h for h in regex_hits(pid) if h["question_id"] not in seen]
            d["hits"] += new
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
            for h in new:
                print(f"REGEX HIT {h['question_id']}: {h['concept'][:50]} | {h['evidence'][:110]}")
        return
    if not a.apply:
        batches = [pids[i:i + a.per_call] for i in range(0, len(pids), a.per_call)]
        OUT.mkdir(exist_ok=True)
        total = 0.0
        with ThreadPoolExecutor(max_workers=5) as pool:
            for b, res in zip(batches, pool.map(lambda b: screen(b, a.model, concepts), batches)):
                total += res["cost"]
                for pid in b:
                    hits = [dict(h, source="model") for h in res["hits"] if h["question_id"].startswith(pid + "_Q")]
                    seen = {h["question_id"] for h in hits}
                    hits += [h for h in regex_hits(pid) if h["question_id"] not in seen]
                    (OUT / f"{pid}.json").write_text(json.dumps({"_paper_id": pid, "concepts": concepts, "hits": hits},
                                                                indent=2, ensure_ascii=False) + "\n")
                    for h in hits:
                        print(f"HIT {h['question_id']} {h['parts']}: {h['concept'][:60]} | {h['evidence'][:120]}")
        print(f"screened {len(pids)} papers, cost ${total:.2f}")
        return
    n = 0
    for f in sorted(OUT.glob("*.json")):
        d = json.loads(f.read_text())
        if not d["hits"] or not re.search(a.only, d["_paper_id"]):
            continue
        st = PROC / "_staging" / f"{d['_paper_id']}.json"
        s = json.loads(st.read_text())
        for h in d["hits"]:
            q = next((q for q in s["questions"] if q["id"] == h["question_id"]), None)
            if not q:
                continue
            if q.get("component") == "mech" and "vector equation of a line" in h["concept"]:
                # Position-vector kinematics (r = r0 + vt, meeting ships) is 9MA0 M7.3, not the FM line topic.
                # IAL2013_WME01_Jan2016 Q6 was wrongly dropped this way (2026-09-27).
                print(f"ignored {h['question_id']}: mech kinematics with vectors is 9MA0 M7.3")
                continue
            labels = {p.strip("() ") for p in h["parts"]} or {None}
            for p in q["parts"]:
                if p["label"] in labels or p["label"] is None or not labels - {None}:
                    p["out_of_spec"] = {"reason": f"Uses {h['concept']}, which no 9MA0 statement covers (concept screen; "
                                                  f"terms verified absent from spec_9ma0.json). Evidence: {h['evidence'][:200]}",
                                        "technique": h["concept"], "spec_note": "concept_screen.py"}
            n += 1
        st.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
    print(f"marked {n} question(s) out of spec in _staging; now run apply_spec_filter.py --all")


if __name__ == "__main__":
    main()
