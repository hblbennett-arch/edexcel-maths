#!/usr/bin/env python3
"""Deterministic quality and licence gates for generated items (docs/handoff-clean-room.md §6).

    .venv/bin/python scripts/clean/gates.py content/clean/items/*.json      # run, print, store gate_results
    .venv/bin/python scripts/clean/gates.py --dry ITEM.json                 # run and print only

  G1 structure  marks add up; mark codes valid; dM after an M; A marks after an M (or `depends_on` an
                earlier part); ft marks name what they follow; A1* only in show-that parts; labels in order.
  G7 novelty    local only, against the pearson-private pack: word 8-grams (whitelist: stock phrases in
                content/novelty_whitelist.json and maths-only runs), 5-gram Jaccard per source question,
                shared distinctive numbers, shared rare words, bge cosine vs every question/part/note.
                Reject: any non-whitelisted 8-gram, Jaccard > 0.15, >= 3 distinctive numbers shared with one
                source, cosine > 0.85 with a source that has the same marks per part and 5-gram Jaccard
                >= 0.08 with it, or cosine > 0.97.
                Flag for review: any other cosine >= 0.75, >= 3 shared rare words.
                Cosine alone measures topic, not copying: from-scratch originals on common topics reach 0.92
                (eval/gates_selftest.py, 2026-09-29), so it only rejects together with a structural match.
The item format is in docs/clean-room-pipeline.md. Results only name Pearson question ids (facts),
never Pearson text.
"""
import argparse
import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chatbot import pack as packs  # noqa: E402
from chatbot.text import latex_to_plain  # noqa: E402

MARK_CODE = re.compile(r"^(ddM|dM|dB|M|A|B)([1-9])(\*|ft|cso|cao)?$")
LABEL_RE = re.compile(r"^([a-z])(\((i|ii|iii|iv|v|vi)\))?$|^(i|ii|iii|iv|v|vi)$")
ROMAN = ["i", "ii", "iii", "iv", "v", "vi"]


# ---- G1 structure --------------------------------------------------------------------------
def _label_key(label: str | None) -> tuple:
    if label is None:
        return (0, 0)
    m = LABEL_RE.match(label)
    if not m:
        return (-1, -1)
    if m.group(1):
        return (ord(m.group(1)) - 96, ROMAN.index(m.group(3)) + 1 if m.group(3) else 0)
    return (0, ROMAN.index(m.group(4)) + 1)


def _check_marks(marks: list[dict], part: dict, where: str, earlier_labels: set) -> list[str]:
    errs = []
    seen_m = False
    for i, mk in enumerate(marks):
        code = mk.get("code", "")
        m = MARK_CODE.match(code)
        if not m:
            errs.append(f"{where} mark {i + 1}: invalid code {code!r}")
            continue
        base, flag = m.group(1), m.group(3) or ""
        dep = mk.get("depends_on")
        if base in ("dM", "ddM") and not seen_m:
            errs.append(f"{where} {code}: dependent method mark with no earlier M in the part")
        if base == "A" and not seen_m and dep not in earlier_labels:
            errs.append(f"{where} {code}: accuracy mark with no earlier M (or depends_on an earlier part)")
        if flag == "ft" and not mk.get("ft_of"):
            errs.append(f"{where} {code}: ft mark must name what it follows (ft_of)")
        if flag == "*" and part.get("command") != "show-that":
            errs.append(f"{where} {code}: A1* (printed answer) outside a show-that part")
        if not (mk.get("for") or "").strip():
            errs.append(f"{where} {code}: no description of what earns the mark")
        seen_m |= base in ("M", "dM", "ddM")
    total = sum(int(MARK_CODE.match(mk["code"]).group(2)) for mk in marks if MARK_CODE.match(mk.get("code", "")))
    if total != part.get("marks"):
        errs.append(f"{where}: codes add up to {total}, part is worth {part.get('marks')}")
    return errs


def g1_structure(item: dict) -> dict:
    errs = []
    parts = item.get("parts") or []
    if not parts:
        errs.append("no parts")
    labels = [p.get("label") for p in parts]
    if labels and all(l in ROMAN for l in labels):  # top-level (i), (ii), ...: "i" is roman, not the letter i
        keys = [(0, ROMAN.index(l) + 1) for l in labels]
    else:
        keys = [_label_key(l) for l in labels]
    if any(k == (-1, -1) for k in keys):
        errs.append(f"bad part label(s): {[p.get('label') for p in parts]}")
    elif keys != sorted(keys) or len(set(keys)) != len(keys):
        errs.append(f"part labels out of order: {[p.get('label') for p in parts]}")
    if len(parts) > 1 and any(p.get("label") is None for p in parts):
        errs.append("multi-part question with an unlabelled part")
    earlier: set = set()
    for p in parts:
        where = f"part {p.get('label') or '-'}"
        if not isinstance(p.get("marks"), int) or p["marks"] < 1:
            errs.append(f"{where}: marks must be a positive integer")
            continue
        errs += _check_marks(p.get("mark_scheme") or [], p, where, earlier)
        for alt in p.get("alternatives") or []:
            errs += _check_marks(alt.get("marks") or [], p, f"{where} {alt.get('name', 'alt')}", earlier)
        m = re.search(r"\((\d+)\)\s*$", p.get("text", ""))
        if m and int(m.group(1)) != p["marks"]:
            errs.append(f"{where}: text shows ({m.group(1)}) but the part is worth {p['marks']}")
        if p.get("label"):
            earlier.add(p["label"])
    total = sum(p.get("marks", 0) for p in parts if isinstance(p.get("marks"), int))
    if "total_marks" in item and item["total_marks"] != total:
        errs.append(f"total_marks {item['total_marks']} != sum of parts {total}")
    return {"pass": not errs, "errors": errs, "total_marks": total}


# ---- G7 novelty ----------------------------------------------------------------------------
WORD_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?")
MATHS_WORDS = set("""sin cos tan sec cosec cot ln log e exp sqrt frac pi theta alpha beta lambda mu sigma rho
dx dy dt dv dy dx d x y z t n r k a b c p q f g h i j u v w s integral sum lim infinity degrees
cm mm km kg ms ml""".split())
COMMON_NUMBERS = {str(n) for n in range(0, 13)} | {"0.5", "0.1", "0.05", "0.01", "0.025", "0.95", "100", "1000",
                                                    "9.8", "360", "180", "90", "60", "45", "30", "20", "15", "25", "50"}
WHITELIST_PATH = ROOT / "content" / "novelty_whitelist.json"


def words(text: str) -> list[str]:
    return WORD_RE.findall(latex_to_plain(text or "").lower())


def item_text(item: dict) -> str:
    bits = [item.get("stem") or ""]
    for p in item.get("parts") or []:
        marks = list(p.get("mark_scheme") or []) + [m for alt in p.get("alternatives") or [] for m in alt.get("marks") or []]
        bits += [p.get("text", ""), " ".join(m.get("for", "") + " " + (m.get("notes") or "") for m in marks)]
        bits += [s.get("working", "") if isinstance(s, dict) else str(s) for s in p.get("solution") or []]
        bits += list(p.get("hints") or [])
    bits += [pf.get("text", "") for pf in item.get("pitfalls") or []]
    return "\n".join(bits)


def item_fields(item: dict) -> list[tuple[str, str]]:
    """(field name, text) for each piece of an item: where an overlap is, without saying what it is."""
    out = [("stem", item.get("stem") or "")]
    for p in item.get("parts") or []:
        lab = p.get("label") or "-"
        marks = list(p.get("mark_scheme") or []) + [m for alt in p.get("alternatives") or [] for m in alt.get("marks") or []]
        out += [(f"part {lab} text", p.get("text", "")),
                (f"part {lab} mark scheme", " ".join(m.get("for", "") + " " + (m.get("notes") or "") for m in marks)),
                (f"part {lab} solution", " ".join(s.get("working", "") if isinstance(s, dict) else str(s)
                                                  for s in p.get("solution") or [])),
                (f"part {lab} hints", " ".join(p.get("hints") or []))]
    out.append(("pitfalls", " ".join(pf.get("text", "") for pf in item.get("pitfalls") or [])))
    return out


def _grams(ws: list[str], n: int) -> set[str]:
    return {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def _is_maths(tok: str) -> bool:
    """Maths tokens: symbols, numbers, function names, units, and derivative pieces like ds, dr, dtheta."""
    return tok in MATHS_WORDS or len(tok) == 1 or tok[0].isdigit() or bool(re.fullmatch(r"d(theta|[a-z])", tok))


def _whitelisted(gram: str, whitelist: list[str]) -> bool:
    """At least 6 of the 8 words are maths tokens or lie inside a whitelisted stock phrase (a phrase
    may be cut off by either edge of the 8-word window)."""
    toks = gram.split()
    covered = [_is_maths(t) for t in toks]
    for w in (wl.split() for wl in whitelist):
        for i in range(len(toks)):
            for j in range(len(w)):
                k = 0
                while i + k < len(toks) and j + k < len(w) and toks[i + k] == w[j + k]:
                    k += 1
                whole = j == 0 and k == len(w)
                cut_left = i == 0 and j > 0 and j + k == len(w)          # phrase began before the window
                cut_right = j == 0 and i + k == len(toks) and k >= 2     # phrase runs past the window
                if k and (whole or (k >= 2 and cut_left) or cut_right):
                    covered[i:i + k] = [True] * k
    return sum(covered) >= len(toks) - 2


class Corpus:
    """The pearson-private corpus, read locally: n-gram sets and vectors. Never leaves this process."""

    def __init__(self):
        p = packs.load("pearson-private")
        conn = sqlite3.connect(f"file:{p.db}?mode=ro", uri=True)
        self.q_words: dict[str, list[str]] = {}
        docs: list[str] = []
        for qid, qt, ms in conn.execute("SELECT id, question_text, mark_scheme_text FROM questions"):
            self.q_words[qid] = words(qt)
            docs += [qt, ms]
        docs += [p_ms for (p_ms,) in conn.execute("SELECT mark_scheme FROM question_parts")]
        docs += [q for (q,) in conn.execute("SELECT quote FROM examiner_notes")]
        self.grams8: set[str] = set()
        for d in docs:
            self.grams8 |= _grams(words(d), 8)
        self.q_grams5 = {q: _grams(w, 5) for q, w in self.q_words.items()}
        self.marks_shape: dict[str, list[int]] = defaultdict(list)
        for q, m in conn.execute("SELECT question_id, marks FROM question_parts ORDER BY question_id, part_index"):
            self.marks_shape[q].append(m)
        self.inv5: dict[str, list[str]] = defaultdict(list)
        for q, gs in self.q_grams5.items():
            for g in gs:
                self.inv5[g].append(q)
        df = Counter(w for ws in self.q_words.values() for w in set(ws))
        n = len(self.q_words)
        self.rare = {w for w, c in df.items() if c <= max(3, n // 500) and w.isalpha() and len(w) > 3
                     and w not in MATHS_WORDS}
        self.q_rare = {q: set(ws) & self.rare for q, ws in self.q_words.items()}
        # A number is distinctive when it appears in at most 2% of real questions (500 is in 1%, 14 in 2.3%).
        # A weak, secondary signal: copies are caught by 8-grams (eval/gates_selftest.py, 2026-09-30).
        num_df = Counter(w for ws in self.q_words.values() for w in set(ws) if w[0].isdigit())
        self.common_numbers = COMMON_NUMBERS | {w for w, k in num_df.items() if k > max(5, n // 50)}
        self.q_nums = {q: {w for w in ws if w[0].isdigit() and w not in self.common_numbers}
                       for q, ws in self.q_words.items()}
        data = np.load(p.embeddings_dir / "embeddings_baai-bge-small-en-v1-5.npz", allow_pickle=False)
        ids = [str(x) for x in data["ids"]]
        keep = [i for i, d in enumerate(ids) if d.split(":", 1)[0] in ("question", "part", "note")]
        self.vec_ids = [ids[i] for i in keep]
        self.vecs = data["vecs"][keep]
        self.whitelist = [" ".join(words(s)) for s in json.loads(WHITELIST_PATH.read_text())["phrases"]] \
            if WHITELIST_PATH.exists() else []


@lru_cache(maxsize=1)
def corpus() -> Corpus:
    return Corpus()


def g7_novelty(item: dict) -> dict:
    c = corpus()
    text = item_text(item)
    ws = words(text)
    reasons, flags = [], []
    hits8 = [g for g in _grams(ws, 8) & c.grams8 if not _whitelisted(g, c.whitelist)]
    if hits8:
        reasons.append(f"{len(hits8)} word 8-gram(s) also in the reference corpus (not whitelisted)")
    hit_fields = sorted({name for name, t in item_fields(item) if _grams(words(t), 8) & set(hits8)})
    # 5-gram Jaccard and shared numbers compare like with like: our question text against theirs
    q_ws = words("\n".join([item.get("stem") or ""] + [p.get("text", "") for p in item.get("parts") or []]))
    g5 = _grams(q_ws, 5)
    inter = Counter(q for g in g5 for q in c.inv5.get(g, ()))
    jac = {q: n / (len(g5) + len(c.q_grams5[q]) - n) for q, n in inter.items()}
    max_q, max_j = max(jac.items(), key=lambda kv: kv[1], default=(None, 0.0))
    if max_j > 0.15:
        reasons.append(f"5-gram Jaccard {max_j:.2f} with {max_q}")
    nums = {w for w in q_ws if w[0].isdigit() and w not in c.common_numbers}
    num_q, num_n = max(((q, len(nums & s)) for q, s in c.q_nums.items()), key=lambda kv: kv[1], default=(None, 0))
    if num_n >= 3:
        reasons.append(f"{num_n} distinctive numbers shared with {num_q}")
    rare = set(q_ws) & c.rare
    rare_q, rare_n = max(((q, len(rare & s)) for q, s in c.q_rare.items()), key=lambda kv: kv[1], default=(None, 0))
    if rare_n >= 3:
        flags.append(f"{rare_n} rare words shared with {rare_q}")
    from chatbot import search
    chunks = [t for t in [item.get("stem") or ""] + [p.get("text", "") for p in item.get("parts") or []]
              + [text] if t.strip()]
    sims = c.vecs @ search.embed([latex_to_plain(t) for t in chunks], search.DEFAULT_MODEL).T
    per_doc = sims.max(axis=1)
    best_i = int(np.argmax(per_doc))
    max_cos, cos_id = float(per_doc[best_i]), c.vec_ids[best_i]
    shape = [p.get("marks") for p in item.get("parts") or []]
    # a likely variant: any source above 0.85 with our exact marks per part AND some shared wording (5-gram
    # Jaccard >= 0.08). Shape and topic alone are commonplace: a from-scratch "find dy/dx, stationary points,
    # nature" cubic (2/4/2 marks) matches several real questions at 0.9 (eval/gates_selftest.py, 2026-09-30)
    src = lambda i: c.vec_ids[i].split(":", 1)[1].split(":")[0]
    same = [c.vec_ids[i] for i in np.flatnonzero(per_doc > 0.85)
            if c.marks_shape.get(src(i)) == shape and jac.get(src(i), 0) >= 0.08]
    if max_cos > 0.97:
        reasons.append(f"cosine {max_cos:.3f} with {cos_id}")
    elif same:
        reasons.append(f"cosine > 0.85 with {same[0]}, which has the same marks per part")
    elif max_cos >= 0.75:
        flags.append(f"cosine {max_cos:.3f} with {cos_id}")
    return {"pass": not reasons, "flag": bool(flags), "reasons": reasons, "flags": flags, "hit_fields": hit_fields,
            "n_8gram_hits": len(hits8), "hits8": sorted(hits8)[:5],  # our own text's offending 8-grams, so a retry can reword them
             "max_jaccard": round(max_j, 3), "jaccard_source": max_q,
            "shared_numbers": num_n, "max_cosine": round(max_cos, 3), "cosine_source": cos_id}


GATES = {"G1": g1_structure, "G7": g7_novelty}


def run(item: dict) -> dict:
    return {name: fn(item) for name, fn in GATES.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="+")
    ap.add_argument("--dry", action="store_true", help="don't write gate_results back into the item files")
    args = ap.parse_args()
    failed = 0
    for path in map(Path, args.items):
        item = json.loads(path.read_text())
        res = run(item)
        ok = all(r["pass"] for r in res.values())
        failed += not ok
        print(f"{path.name}: " + "  ".join(f"{g} {'PASS' if r['pass'] else 'FAIL'}{' (flag)' if r.get('flag') else ''}"
                                           for g, r in res.items()))
        for g, r in res.items():
            for line in r.get("errors", []) + r.get("reasons", []) + r.get("flags", []):
                print(f"    {g}: {line}")
        if not args.dry:
            item["gate_results"] = {**(item.get("gate_results") or {}), **res}
            path.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
