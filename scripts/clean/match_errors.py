#!/usr/bin/env python3
"""Error-code frequencies from the Pearson pitfall notes (docs/handoff-clean-room.md §5.2 step 2-3).

    .venv/bin/python scripts/clean/match_errors.py [--threshold 0.70] [--samples]

Local and deterministic. The note text is read only by the local bge embedding model (vectors already in
data/processed/embeddings_*.npz); nothing is sent anywhere and no note text is written to content/.

1. Embed each error-code definition (content/error_codes.json) with the same local model.
2. Match every `pitfall` note to its nearest code, considering only codes whose groups include one of the
   note's part skills' groups (or '*'); keep it if the cosine similarity >= threshold.
3. Count per (skill, code) and per (question type, code), weighted by how the part was answered
   (poorly 2, mixed 1.5, well 1, unknown 1).
4. Cluster the unmatched notes (k-means on the vectors) and report cluster sizes.

Outputs
  content/facts/error_frequency.json      numbers and codes only (checked by check_facts.py)
  data/clean_private/error_match_samples.md   --samples: note text + matched code for the USER to read
                                              (gitignored; never paste it into a model prompt)
"""
import argparse
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chatbot import pack as packs  # noqa: E402

CODES_PATH = ROOT / "content" / "error_codes.json"
OUT = ROOT / "content" / "facts" / "error_frequency.json"
PRIVATE = ROOT / "data" / "clean_private"
MODEL = "BAAI/bge-small-en-v1.5"
RATING_WEIGHT = {"poorly_answered": 2.0, "mixed": 1.5, "well_answered": 1.0}


def kmeans(x: np.ndarray, k: int, seed: int = 7, iters: int = 30) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centres = x[rng.choice(len(x), size=k, replace=False)]
    for _ in range(iters):
        labels = np.argmax(x @ centres.T, axis=1)  # cosine (vectors are unit length)
        for j in range(k):
            members = x[labels == j]
            if len(members):
                c = members.mean(axis=0)
                centres[j] = c / np.linalg.norm(c)
    return np.argmax(x @ centres.T, axis=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--samples", action="store_true", help="write the private sample sheet for human review")
    args = ap.parse_args()

    p = packs.load("pearson-private")
    conn = sqlite3.connect(f"file:{p.db}?mode=ro", uri=True)
    codes = json.loads(CODES_PATH.read_text())["codes"]
    from chatbot import search  # the local embedder (fastembed, cached model files)
    code_vecs = search.embed([f"{c['id'].replace('-', ' ')}: {c['definition']}" for c in codes], MODEL)

    data = np.load(p.embeddings_dir / "embeddings_baai-bge-small-en-v1-5.npz", allow_pickle=False)
    row_of = {str(i): n for n, i in enumerate(data["ids"])}
    vecs = data["vecs"]  # load once (each data["vecs"] access re-reads the file)
    group_of = dict(conn.execute("SELECT id, group_id FROM skills"))
    qtype = dict(conn.execute("SELECT question_id, tag_value FROM question_tags WHERE tag_type = 'question_type'"))
    part_skills = defaultdict(list)
    for q, lab, s in conn.execute("SELECT question_id, part_label, tag_value FROM question_tags WHERE tag_type = 'skill'"):
        part_skills[(q, lab)].append(s)
        part_skills[(q, "*")].append(s)
    rating = {(q, lab): r for q, lab, r in conn.execute("SELECT question_id, part_label, rating FROM question_performance")}

    notes = conn.execute("SELECT id, question_id, part_label FROM examiner_notes WHERE kind = 'pitfall' "
                         "AND question_id IS NOT NULL").fetchall()
    skill_err, type_err, by_code = defaultdict(float), defaultdict(float), Counter()
    skill_err_n, type_err_n = Counter(), Counter()
    unmatched, matched_rows, best_scores, all_best = [], [], [], []
    for nid, q, lab in notes:
        vec = vecs[row_of[f"note:{nid}"]]
        skills = part_skills.get((q, lab)) or part_skills.get((q, "*"), [])
        groups = {group_of[s] for s in skills}
        allowed = [i for i, c in enumerate(codes) if "*" in c["groups"] or groups & set(c["groups"])]
        sims = code_vecs[allowed] @ vec
        best = int(np.argmax(sims))
        score, code = float(sims[best]), codes[allowed[best]]
        best_scores.append(score)
        all_best.append((nid, code["id"], score))
        if score < args.threshold:
            unmatched.append(nid)
            continue
        matched_rows.append((nid, code["id"], score))
        w = RATING_WEIGHT.get(rating.get((q, lab)) or rating.get((q, None)), 1.0)
        by_code[code["id"]] += 1
        # Credit the note to the part's skills that the code applies to (all of them for '*' codes).
        for s in skills:
            if "*" in code["groups"] or group_of[s] in code["groups"]:
                skill_err[(s, code["id"])] += w
                skill_err_n[(s, code["id"])] += 1
        if q in qtype:
            type_err[(qtype[q], code["id"])] += w
            type_err_n[(qtype[q], code["id"])] += 1

    clusters = []
    if unmatched:
        x = np.stack([vecs[row_of[f"note:{n}"]] for n in unmatched])
        k = max(2, min(60, len(unmatched) // 60))
        labels = kmeans(x, k)
        sizes = Counter(int(l) for l in labels)
        clusters = [[f"c{j}", n] for j, n in sizes.most_common()]

    out = {
        "model": "bge-small-en-v1-5", "threshold": args.threshold, "n_pitfall_notes": len(notes),
        "n_matched": len(matched_rows),
        "by_error_code": dict(by_code.most_common()),
        "skill_error": sorted([[s, c, round(w, 1), skill_err_n[(s, c)]] for (s, c), w in skill_err.items()],
                              key=lambda r: (r[0], -r[2])),
        "type_error": sorted([[t, c, round(w, 1), type_err_n[(t, c)]] for (t, c), w in type_err.items()],
                             key=lambda r: (r[0], -r[2])),
        "unmatched_clusters": clusters,
    }
    OUT.write_text(json.dumps(out, indent=0))
    bs = np.array(best_scores)
    print(f"pitfall notes {len(notes)} | matched {len(matched_rows)} ({len(matched_rows) / len(notes):.0%}) at >= "
          f"{args.threshold} | codes used {len(by_code)}/{len(codes)} | unmatched clusters {len(clusters)}")
    print("best-score quantiles (10/25/50/75/90%):", np.round(np.quantile(bs, [.1, .25, .5, .75, .9]), 3).tolist())
    print("codes never matched:", len(codes) - len(by_code))

    if args.samples:
        # Human-review sheet: random matches per score band + a few notes per unmatched cluster.
        import random
        rnd = random.Random(3)
        text = dict(conn.execute("SELECT id, COALESCE(display, quote) FROM examiner_notes"))
        defs = {c["id"]: c["definition"] for c in codes}
        PRIVATE.mkdir(parents=True, exist_ok=True)
        lines = ["# Error-code match samples (PRIVATE: Pearson text, never commit, never paste into a model)", "",
                 "Mark each line ✓ (the code fits the note) or ✗. The share of ✓ per band sets the threshold.", ""]
        for lo, hi in ((0.60, 0.65), (0.65, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 1.0)):
            band = [m for m in all_best if lo <= m[2] < hi]
            lines += [f"## nearest-code score {lo:.2f}-{hi:.2f} ({len(band)} notes)", ""]
            for nid, cid, sc in rnd.sample(band, min(15, len(band))):
                lines += [f"- [ ] **{cid}** ({sc:.2f}): {defs[cid]}", f"  > {text[nid]}", ""]
        if unmatched:
            lines += ["## Unmatched clusters: write a new code in your own words if a cluster is a real mistake type", ""]
            members = defaultdict(list)
            for n, l in zip(unmatched, labels):
                members[f"c{int(l)}"].append(n)
            for cid, size in clusters[:25]:
                lines += [f"### {cid} ({size} notes)", ""]
                lines += [f"  > {text[n]}" for n in rnd.sample(members[cid], min(4, size))] + [""]
        (PRIVATE / "error_match_samples.md").write_text("\n".join(lines))
        print(f"wrote {(PRIVATE / 'error_match_samples.md').relative_to(ROOT)} (private, for you to read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
