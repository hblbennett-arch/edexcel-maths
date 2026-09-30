#!/usr/bin/env python3
"""Blueprints for the clean bank, built from the fact layer only (docs/handoff-clean-room.md §5.3).

    .venv/bin/python scripts/clean/make_blueprints.py [--exam 600] [--seed 1]

Reads content/facts/*.json (ids, numbers, codes), content/clean/tags.json and content/error_codes.json.
It never reads the Pearson pack.

Exam-style blueprints (content/blueprints/exam.jsonl). Each is the consensus of 3 real questions of the
same question type and the same number of parts (9MA0 first, then other Edexcel qualifications). Per
part it takes:
  - the median marks;
  - the skills in at least 2 of the 3 sources (else the commonest);
  - the command word and answer forms in at least 2 of the 3;
  - a mark-code pattern adding up to the marks (from the sources, then the skill's commonest pattern).
A type with fewer than 3 sources draws them from questions sharing its characteristic skills. The
blueprints are then selected so that each component matches the 9MA0 question mix
(aggregates.mix_9ma0: 1 topic short / 1 topic long / 2 topics / 3+ topics) and the 9MA0 question-type
frequencies.

Drill blueprints (content/blueprints/drills.jsonl): 2 per skill (starter, core), one part each, marks and
mark pattern from that skill's distribution.

Every blueprint lists its source question ids (facts) and target error codes. Check with
scripts/clean/check_blueprints.py.
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_facts import MIX_BANDS, SUPPORT_GROUPS  # noqa: E402

FACTS = ROOT / "content" / "facts"
OUT = ROOT / "content" / "blueprints"
COMMAND_PRIORITY = ["prove", "show-that", "hence-or-otherwise", "hence", "sketch", "test", "explain", "deduce",
                    "verify", "solve", "calculate", "estimate", "write-down", "state", "express", "simplify",
                    "differentiate", "integrate", "expand", "factorise", "determine", "evaluate", "find", "use",
                    "describe", "draw", "complete", "comment", "interpret", "suggest", "criticise", "label", "given-that"]
# Our own context themes (no exam scenario words). The generator invents a new scenario within the theme.
THEMES = {
    "pure": ["population", "finance", "medicine", "temperature", "engineering", "sport", "environment",
             "manufacturing", "architecture", "astronomy"],
    "stats": ["health", "sport", "retail", "transport", "education", "agriculture", "environment",
              "quality-control", "games", "technology", "wildlife", "weather"],
    "mech": ["everyday-objects", "sport", "construction", "transport", "playground", "warehouse", "fairground",
             "garden"],
}
LABEL_RE = __import__("re").compile(r"^[a-z](\((i|ii|iii|iv|v|vi)\))?$|^(i|ii|iii|iv|v|vi)$")  # as gates.py G1
MODELLING_GROUPS = {"modelling-in-context", "exponential-modelling", "trig-equations-and-models"}


def load():
    parts = json.loads((FACTS / "parts.json").read_text())
    agg = json.loads((FACTS / "aggregates.json").read_text())
    errors = json.loads((FACTS / "error_frequency.json").read_text())
    tags = json.loads((ROOT / "content" / "clean" / "tags.json").read_text())
    codes = {c["id"]: c for c in json.loads((ROOT / "content" / "error_codes.json").read_text())["codes"]}
    return parts, agg, errors, tags, codes


def _tvd(a: Counter, b: Counter) -> float:
    na, nb = sum(a.values()) or 1, sum(b.values()) or 1
    return 0.5 * sum(abs(a[k] / na - b[k] / nb) for k in set(a) | set(b))


def value(code: str) -> int:
    return int("".join(ch for ch in code if ch.isdigit()) or 0)


def well_formed(codes: list[str]) -> bool:
    seen_m = False
    for c in codes:
        if c.startswith(("A", "dM", "ddM")) and not seen_m:
            return False
        seen_m |= c.startswith(("M", "dM", "ddM"))
    return True


def fit_pattern(candidates: list[list[str]], marks: int, show_that: bool) -> list[str]:
    """First candidate pattern that adds up to `marks` and is well formed; A1* only in show-that parts."""
    for cand in candidates:
        cand = [c.replace("*", "") if not show_that else c for c in cand]
        if sum(map(value, cand)) == marks and well_formed(cand):
            if show_that and not any(c.endswith("*") for c in cand) and cand[-1] == "A1":
                cand = cand[:-1] + ["A1*"]
            return cand
    # generic fallback: B1 for 1 mark, otherwise methods then accuracy
    if marks == 1:
        return ["B1"]
    m = (marks + 1) // 2
    pat = [x for i in range(m) for x in ("M1", "A1")][:marks]
    return pat[:-1] + ["A1*"] if show_that else pat


class Builder:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        parts, self.agg, errors, tags, self.codes = load()
        self.group = {s["id"]: s["group"] for s in tags["skills"]}
        self.skill_title = {s["id"]: s["title"] for s in tags["skills"]}
        self.skill_desc = {s["id"]: s.get("description") for s in tags["skills"]}
        self.qparts: dict[str, list[dict]] = defaultdict(list)
        for p in parts["parts"]:
            self.qparts[p["question"]].append(p)
        for ps in self.qparts.values():
            ps.sort(key=lambda p: p["index"])
        self.qperf = parts["question_perf"]
        self.by_type: dict[str, list[str]] = defaultdict(list)
        for q, ps in self.qparts.items():
            self.by_type[ps[0]["question_type"]].append(q)
        self.skill_err: dict[str, list[tuple]] = defaultdict(list)
        for s, c, w, n in errors["skill_error"]:
            self.skill_err[s].append((c, w, n))

    # ---- helpers ----------------------------------------------------------------------------
    def qual(self, q: str) -> str:
        return self.qparts[q][0]["qualification"]

    def topics(self, skills) -> set[str]:
        return {self.group[s] for s in skills} - SUPPORT_GROUPS

    def band(self, skills, marks: int) -> str:
        t = len(self.topics(skills))
        return MIX_BANDS[0] if t <= 1 and marks <= 5 else MIX_BANDS[1] if t <= 1 else MIX_BANDS[2] if t == 2 else MIX_BANDS[3]

    def difficulty(self, qids: list[str]) -> str | None:
        pcts = []
        for q in qids:
            perf = self.qperf.get(q) or next((p["perf"] for p in self.qparts[q] if p["perf"]), None)
            if perf and perf.get("mean_mark") is not None and perf.get("max_mark"):
                pcts.append(perf["mean_mark"] / perf["max_mark"])
            elif perf and perf.get("rating"):
                pcts.append({"well_answered": 0.8, "mixed": 0.6, "poorly_answered": 0.4}[perf["rating"]])
        if not pcts:
            return None
        m = sum(pcts) / len(pcts)
        return "accessible" if m >= 0.75 else "standard" if m >= 0.55 else "challenging"

    def _vectors(self):
        """Local bge vectors of our own texts: error-code definitions and skill descriptions."""
        if not hasattr(self, "_code_vec"):
            sys.path.insert(0, str(ROOT))
            from chatbot import search
            ids = list(self.codes)
            v = search.embed([f"{c.replace('-', ' ')}: {self.codes[c]['definition']}" for c in ids], search.DEFAULT_MODEL)
            self._code_vec = dict(zip(ids, v))
            sk = list(self.skill_title)
            v = search.embed([f"{self.skill_title[x]}. {self.skill_desc.get(x) or ''}" for x in sk], search.DEFAULT_MODEL)
            self._skill_vec = dict(zip(sk, v))
        return self._code_vec, self._skill_vec

    def error_targets(self, skills: list[str], k: int = 3) -> list[dict]:
        """Up to k error codes for a part: those that apply to its skill groups, ranked by how well the code's
        definition matches the skills (local embeddings of our own texts), then by matched-note frequency."""
        groups = {self.group[s] for s in skills}
        code_vec, skill_vec = self._vectors()
        notes: Counter = Counter()
        for s in skills:
            for c, w, n in self.skill_err.get(s, []):
                notes[c] += n
        cands = [c for c, code in self.codes.items() if groups & set(code["groups"])] or \
                [c for c, code in self.codes.items() if "*" in code["groups"]]
        rel = {c: max(float(code_vec[c] @ skill_vec[s]) for s in skills) for c in cands}
        ranked = sorted(cands, key=lambda c: (-round(rel[c], 2), -notes[c]))
        return [{"code": c, "loses": self.codes[c]["loses"], "n_notes": notes[c]} for c in ranked[:k]]

    def sources_for(self, qtype: str, n_parts: int | None) -> list[str]:
        pool = [q for q in self.by_type.get(qtype, []) if n_parts is None or len(self.qparts[q]) == n_parts]
        pool.sort(key=lambda q: (self.qual(q) != "9MA0", q))
        return pool

    def characteristic_sources(self, qtype: str) -> list[str]:
        """For a type with < 3 sources: questions sharing its two most characteristic skills."""
        own = Counter(s for q in self.by_type[qtype] for p in self.qparts[q] for s in p["skills"]
                      if self.group[s] != "exam-technique")
        key = [s for s, _ in own.most_common(2)]
        comp = self.qparts[self.by_type[qtype][0]][0]["component"]
        return sorted(q for q, ps in self.qparts.items() if ps[0]["component"] == comp and q not in self.by_type[qtype]
                      and set(key) <= {s for p in ps for s in p["skills"]})

    # ---- exam-style blueprints ----------------------------------------------------------------
    def consensus(self, qtype: str, srcs: list[str], idx: int, min_votes: int = 2, marks_rule: str = "median") -> dict:
        shapes = [self.qparts[q] for q in srcs]
        n = len(shapes[0])
        labels = [p["part"].split(":", 1)[1] or None for p in shapes[0]]
        same_labels = all([p["part"].split(":", 1)[1] or None for p in s] == labels for s in shapes)
        if not same_labels or not all(l is None or LABEL_RE.match(l) for l in labels):
            labels = [None] if n == 1 else [chr(97 + i) for i in range(n)]
        bp_parts = []
        for i in range(n):
            col = [s[i] for s in shapes]
            marks = sorted(p["marks"] for p in col)[{"min": 0, "median": 1, "max": 2}[marks_rule]]
            sk = Counter(x for p in col for x in dict.fromkeys(p["skills"]))
            skills = [x for x, c in sk.most_common() if c >= min_votes][:4 if min_votes == 1 else 6] \
                or [sk.most_common(1)[0][0]]
            if all(self.group[x] == "exam-technique" for x in skills):  # every part needs a maths skill
                maths = [x for x, _ in sk.most_common() if self.group[x] != "exam-technique"]
                if not maths:  # fall back to the question's own main maths skill
                    maths = [x for x, _ in Counter(x for s in shapes for p in s for x in p["skills"]
                                                   if self.group[x] != "exam-technique").most_common(1)]
                skills = maths[:1] + skills
            cmds = Counter(c for p in col for c in p["commands"] if c != "given-that")
            majority = [c for c, k in cmds.items() if k >= 2]
            command = next((c for c in COMMAND_PRIORITY if c in majority),
                           next((c for c in COMMAND_PRIORITY if c in cmds), "find"))
            forms = sorted(f for f, k in Counter(f for p in col for f in p["forms"]).items() if k >= 2)
            show = command == "show-that"
            cands = [p["codes"] for p in col if p["codes"]]
            for s in skills:
                cands += [pat.split() for pat in self.agg["by_skill"].get(s, {}).get("code_patterns", {})]
            codes = fit_pattern(cands, marks, show)
            bp_parts.append({"label": labels[i], "skills": skills, "marks": marks, "codes": " ".join(codes),
                             "command": command, "forms": forms,
                             "error_codes": self.error_targets([s for s in skills if self.group[s] != "exam-technique"] or skills)})
        comp = shapes[0][0]["component"]
        skills_all = [s for p in bp_parts for s in p["skills"]]
        needs_context = comp != "pure" or bool({self.group[s] for s in skills_all} & MODELLING_GROUPS)
        total = sum(p["marks"] for p in bp_parts)
        return {
            "id": f"bp-{comp}-{qtype}-{idx:03d}", "kind": "exam", "question_type": qtype, "component": comp,
            "total_marks": total, "band": self.band(skills_all, total), "marks_rule": marks_rule,
            "difficulty": self.difficulty(srcs) or "standard",
            "context_theme": self.rng.choice(THEMES[comp]) if needs_context else "none",
            "no_calc_tech": any("no-calc-tech" in p["forms"] for p in bp_parts),
            "parts": bp_parts, "source_fact_ids": srcs,
            "source_rule": ("same-type-same-shape" if all(q in self.by_type[qtype] for q in srcs) else "shared-skills")
                           + ("" if min_votes >= 2 else "+union"),
        }

    def candidates(self, qtype: str, per_type: int) -> list[dict]:
        out, seen = [], set()
        shapes = Counter(len(self.qparts[q]) for q in self.by_type[qtype])
        for attempt in range(per_type * 12):
            n = self.rng.choices(list(shapes), weights=list(shapes.values()))[0]
            pool = self.sources_for(qtype, n)
            if len(pool) < 3:
                pool = [q for q in self.characteristic_sources(qtype) if len(self.qparts[q]) == n]
            if len(pool) < 3:
                continue
            # 9MA0 sources are preferred: sample from the first ~12 of the (9MA0-first) pool when possible
            head = pool[:max(12, sum(self.qual(q) == "9MA0" for q in pool))]
            srcs = sorted(self.rng.sample(head, 3))
            # consensus (skills in >= 2 of 3 sources) and a union blend (skills in any source, capped)
            # pure sources skew short, stats/mech sources (IAL units) long: vary marks the other way
            alt = "max" if self.qparts[srcs[0]][0]["component"] == "pure" else "min"
            for votes, rule in ((2, "median"), (1, "median"), (2, alt), (1, alt)):
                bp = self.consensus(qtype, srcs, 0, min_votes=votes, marks_rule=rule)
                sig = (tuple(p["marks"] for p in bp["parts"]), tuple(tuple(p["skills"]) for p in bp["parts"]))
                if sig not in seen:
                    seen.add(sig)
                    out.append(bp)
            if len(out) >= per_type:
                break
        return out

    def exam(self, total: int) -> list[dict]:
        mix = self.agg["mix_9ma0"]
        comp_share = {c: sum(v["questions"] for v in mix[c].values()) for c in ("pure", "stats", "mech")}
        n_all = sum(comp_share.values())
        type_freq = Counter(ps[0]["question_type"] for ps in self.qparts.values() if ps[0]["qualification"] == "9MA0")
        chosen = []
        for comp in ("pure", "stats", "mech"):
            quota = round(total * comp_share[comp] / n_all)
            band_q = {b: round(quota * mix[comp].get(b, {"questions": 0})["questions"] / comp_share[comp]) for b in MIX_BANDS}
            types = [t for t in type_freq if self.qparts[self.by_type[t][0]][0]["component"] == comp]
            # candidates per type in proportion to its 9MA0 frequency (at least 3 for coverage)
            pool = []
            for t in types:
                mult = 4 if comp == "pure" else 12  # small components need a bigger pool to match the shape
                pool += self.candidates(t, max(6, round(mult * quota * type_freq[t] / sum(type_freq[x] for x in types))))
            self.rng.shuffle(pool)
            used = Counter()
            per_type_cap = {t: max(3, round(2 * quota * type_freq[t] / sum(type_freq[x] for x in types))) for t in types}
            # consensus blueprints first; union blends only where a band still needs them
            # Greedy: consensus blueprints before union blends; each pick is the one that brings the set's
            # marks-per-question and parts-per-question distributions closest to 9MA0's, within the band
            # quotas and a per-type cap (relaxed on a second pass if a band is still short).
            ref = [(sum(p["marks"] for p in ps), len(ps)) for ps in self.qparts.values()
                   if ps[0]["qualification"] == "9MA0" and ps[0]["component"] == comp]
            ref_m, ref_p = Counter(m // 3 for m, _ in ref), Counter(min(n, 5) for _, n in ref)
            cur_m, cur_p = Counter(), Counter()

            def gap(bp):
                m, n = bp["total_marks"] // 3, min(len(bp["parts"]), 5)
                cur_m[m] += 1; cur_p[n] += 1
                g = _tvd(cur_m, ref_m) + 1.5 * _tvd(cur_p, ref_p) + 0.02 * bp["source_rule"].endswith("+union")
                cur_m[m] -= 1; cur_p[n] -= 1
                return g

            remaining = list(pool)
            for cap_factor in (1, 2):
                while True:
                    ok = [bp for bp in remaining if used[bp["band"]] < band_q[bp["band"]]
                          and used[bp["question_type"]] < cap_factor * per_type_cap[bp["question_type"]]]
                    if not ok:
                        break
                    bp = min(ok, key=gap)
                    remaining.remove(bp)
                    used[bp["band"]] += 1
                    used[bp["question_type"]] += 1
                    cur_m[bp["total_marks"] // 3] += 1
                    cur_p[min(len(bp["parts"]), 5)] += 1
                    chosen.append(bp)
            short = {b: band_q[b] - used[b] for b in MIX_BANDS if used[b] < band_q[b]}
            if short:
                print(f"  {comp}: bands short of quota {short} (pool had too few candidates)")
        counts = Counter()
        for bp in chosen:
            counts[bp["question_type"]] += 1
            bp["id"] = f"bp-{bp['component']}-{bp['question_type']}-{counts[bp['question_type']]:03d}"
        return chosen

    # ---- mock papers ---------------------------------------------------------------------------
    MOCK_SHAPES = (("P1", ["P1_June2024"]), ("P1", ["P1_June2023"]), ("P2", ["P2_June2024"]), ("P2", ["P2_June2023"]),
                   ("P3", ["P3_June2024_stats", "P3_June2024_mech"]), ("P3", ["P3_June2023_stats", "P3_June2023_mech"]))

    def set_marks(self, bp: dict, target: int) -> dict:
        """Adjust a blueprint to exactly `target` marks, one mark at a time on its largest part (adding or
        removing), re-fitting that part's mark pattern."""
        while bp["total_marks"] != target:
            step = 1 if bp["total_marks"] < target else -1
            parts = [p for p in bp["parts"] if step > 0 or p["marks"] > 1]
            if not parts:
                break
            p = max(parts, key=lambda p: p["marks"]) if step > 0 else max(parts, key=lambda p: p["marks"])
            p["marks"] += step
            pats = [c.split() for s in p["skills"] for c in self.agg["by_skill"].get(s, {}).get("code_patterns", {})]
            p["codes"] = " ".join(fit_pattern(pats, p["marks"], p["command"] == "show-that"))
            bp["total_marks"] += step
        bp["band"] = self.band([x for p in bp["parts"] for x in p["skills"]], bp["total_marks"])
        return bp

    def mocks(self, bank_sigs: set) -> list[dict]:
        papers = json.loads((FACTS / "papers.json").read_text())
        out = []
        for n, (paper, shapes) in enumerate(self.MOCK_SHAPES, 1):
            q = 0
            for shape in shapes:
                for q_num, marks, n_parts, qtype in papers[shape]["questions"]:
                    q += 1
                    cands = [c for c in self.candidates(qtype, 12) if (tuple(p["marks"] for p in c["parts"]),
                             tuple(tuple(p["skills"]) for p in c["parts"])) not in bank_sigs] if qtype in self.by_type else []
                    if not cands:
                        comp = papers[shape]["component"]
                        cands = [c for t in self.by_type if self.qparts[self.by_type[t][0]][0]["component"] == comp
                                 for c in self.candidates(t, 2)]
                    best = min(cands, key=lambda c: (abs(len(c["parts"]) - n_parts), abs(c["total_marks"] - marks),
                                                     c["source_rule"].endswith("+union")))
                    bp = self.set_marks(json.loads(json.dumps(best)), marks)
                    bp.update({"id": f"mk-{n}-{paper.lower()}-q{q:02d}", "kind": "mock", "mock": f"mock-{n}-{paper}",
                               "q_num": q})
                    out.append(bp)
        return out

    # ---- drills --------------------------------------------------------------------------------
    def drills(self) -> list[dict]:
        out = []
        tagged = defaultdict(list)
        for q, ps in self.qparts.items():
            for p in ps:
                for s in p["skills"]:
                    tagged[s].append(p)
        for s in sorted(self.group):
            if self.group[s] == "exam-technique" or len({p["question"] for p in tagged[s]}) < 3:
                continue
            stats = self.agg["by_skill"][s]
            hist = {int(k): v for k, v in stats["marks_per_part"].items()}
            qtype = Counter(p["question_type"] for p in tagged[s]).most_common(1)[0][0]
            comp = Counter(p["component"] for p in tagged[s]).most_common(1)[0][0]
            command = next((c for c in COMMAND_PRIORITY if c in stats["commands"] and c not in ("given-that",)), "find")
            pats = [pat.split() for pat in stats["code_patterns"]]
            srcs = sorted({p["question"] for p in tagged[s]})
            for tier, lo, hi in (("starter", 1, 3), ("core", 3, 5)):
                marks = max((m for m in hist if lo <= m <= hi), key=lambda m: hist[m], default=lo + 1)
                show = command == "show-that" and tier == "core"
                out.append({
                    "id": f"dr-{s}-{tier}", "kind": "drill", "question_type": qtype, "component": comp,
                    "total_marks": marks, "band": MIX_BANDS[0], "difficulty": tier,
                    "context_theme": "none" if comp == "pure" else self.rng.choice(THEMES[comp]),
                    "no_calc_tech": False, "marks_rule": "skill-mode",
                    "parts": [{"label": None, "skills": [s], "marks": marks,
                               "codes": " ".join(fit_pattern(pats, marks, show)),
                               "command": "show-that" if show else ("find" if command in ("show-that", "prove") else command),
                               "forms": [], "error_codes": self.error_targets([s])}],
                    "source_fact_ids": self.rng.sample(srcs, min(5, len(srcs))), "source_rule": "skill-parts",
                })
        return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exam", type=int, default=600)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    b = Builder(args.seed)
    exam = b.exam(args.exam)
    drills = b.drills()
    mocks = b.mocks({(tuple(p["marks"] for p in bp["parts"]), tuple(tuple(p["skills"]) for p in bp["parts"])) for bp in exam})
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("exam", exam), ("drills", drills), ("mocks", mocks)):
        (OUT / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    mix = Counter((bp["component"], bp["band"]) for bp in exam)
    per_mock = Counter()
    for bp in mocks:
        per_mock[bp["mock"]] += bp["total_marks"]
    print(f"exam-style blueprints: {len(exam)} | drills: {len(drills)} | mock questions: {len(mocks)} "
          f"({', '.join(f'{m} {t} marks' for m, t in per_mock.items())})")
    for comp in ("pure", "stats", "mech"):
        n = sum(v for (c, _), v in mix.items() if c == comp)
        print(f"  {comp:5s} {n:4d}: " + "  ".join(f"{band} {mix[(comp, band)] / max(n, 1):.0%}" for band in MIX_BANDS))
    print("  question types covered:", len({bp["question_type"] for bp in exam}),
          "| source rules:", dict(Counter(bp["source_rule"] for bp in exam)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
