"""Phase 4 retrieval demo: what the tutor would be given for a student's message.

    .venv/bin/python -m chatbot "2022 paper 1 question 15"
    .venv/bin/python -m chatbot "how do I integrate x e^x?"
    .venv/bin/python -m chatbot "<pasted question text>" --hardest b
    .venv/bin/python -m chatbot "P1 June 2022 Q15" --json          # full bundle as JSON

No model call happens here (that's Phase 5); this shows the retrieved material.
"""
import argparse
import json
import os
import sys

from . import recommend
from .identify import identify, summary
from .retrieve import generic_bundle, question_bundle


def _plain(s: str, n: int = 110) -> str:
    return " ".join(s.split())[:n]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("message")
    ap.add_argument("--hardest", help="part label the student found hardest (e.g. b)")
    ap.add_argument("--json", action="store_true", help="print the full retrieval result as JSON")
    args = ap.parse_args()

    found = identify(args.message)
    out = {"identification": found.__dict__}
    if found.question_id:
        out["bundle"] = question_bundle(found.question_id)
        out["recommendations"] = recommend.refocus(found.question_id, args.hardest or found.part_label)
    elif found.kind in ("generic", "new_question"):
        out["generic"] = generic_bundle(args.message)

    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        f = found
        print(f"\n== identified: {f.kind}" + (f"  {summary(f.question_id)}" if f.question_id else "")
              + (f"  part {f.part_label}" if f.part_label else "") + (f"\n   {f.message}" if f.message else ""))
        if "bundle" in out:
            b = out["bundle"]
            print(f"   type: {b['question_type']['id']} | topics: {', '.join(b['topics'])}")
            print(f"   paper: {b['links']['question_paper_page']}")
            perf = b["performance"]
            if perf:
                print(f"   how students did: {perf.get('rating', '')} {perf.get('mean_mark', '')}/{perf.get('max_mark', '')}")
            for p in b["parts"]:
                print(f"\n   ({p['label'] or '-'}) {p['marks']} marks — skills: {', '.join(s['id'] + ('*' if s['formula_booklet'] else '') for s in p['skills'])}")
                for n in p["examiner_notes"][:3]:
                    print(f"      examiner [{n['kind']}]: {_plain(n['text'])}")
                for n in p["related_pitfalls"][:2]:
                    print(f"      similar-question pitfall ({n['question_id']} {n['part_label']}): {_plain(n['text'], 90)}")
            r = out["recommendations"]
            print(f"\n   practise (focus: part {r['hardest_part'] or 'whole question'}):")
            for s in r["ladder"]:
                print(f"      {s['step']:13} {s['question_id']} {s['part_label'] or ''} ({s['marks']} marks) — {s['reason'][:60]}")
            print(f"      same type: {', '.join(x['question_id'] for x in r['same_type'])}")
            print("   (* = formula in the booklet)")
        if "generic" in out:
            g = out["generic"]
            for s in g["skills"]:
                print(f"\n   skill: {s['id']}{' *' if s['formula_booklet'] else ''} — {s['description'][:80]}")
                for e in s["example_parts"]:
                    print(f"      try: {e['question_id']} {e['part_label'] or ''} ({e['marks']} marks, {e['tier']})")
            for n in g["examiner_notes"][:3]:
                print(f"   examiner [{n['kind']}] {n['question_id']}: {_plain(n['text'])}")
    sys.stdout.flush()
    os._exit(0)  # onnxruntime can abort during interpreter teardown


if __name__ == "__main__":
    main()
