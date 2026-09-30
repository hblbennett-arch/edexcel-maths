#!/usr/bin/env python3
"""Check the fact layer holds facts only (docs/handoff-clean-room.md §5.1). Deterministic.

    .venv/bin/python scripts/clean/check_facts.py [content/facts/*.json ...]

Every string in the files (keys and values) must be one of:
  - an id from our own vocabularies: skill, skill group, question type, question/part/paper id, unit,
    qualification, paper, component, sitting, performance rating;
  - a code from a whitelist: a mark code (M1, dM1, A1ft, B1, A1*, ...) or a space-separated sequence
    of them, a command-word / answer-form code (scripts/clean/build_facts.py), a code source;
  - a number, or a URL;
  - a field name from FIELD_NAMES.
Anything else (a phrase, a sentence) fails, as does any non-URL string over 40 characters that is not
a mark-code sequence or one of our ids. Exit code 1 on failure.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_facts  # noqa: E402
from chatbot import pack as packs  # noqa: E402

FIELD_NAMES = {
    "parts", "question_perf", "part", "question", "qualification", "unit", "paper", "component", "sitting",
    "index", "n_parts", "marks", "question_marks", "question_type", "skills", "codes", "code_source",
    "commands", "forms", "figure", "perf", "mean_mark", "max_mark", "full_marks_pct", "rating",
    "overall", "by_qualification", "by_question_type", "by_skill", "skill_cooccurrence", "group_cooccurrence",
    "n_questions", "parts_per_question", "question_marks", "marks_per_part", "code_patterns", "figure_share",
    "difficulty", "n_rated", "ratings", "mean_pct_mean", "full_marks_pct_mean", "total_marks", "questions",
    # error-code frequencies (scripts/clean/match_errors.py)
    "by_error_code", "skill_error", "type_error", "n_notes", "weighted", "threshold", "unmatched_clusters",
    "size", "n_matched", "n_pitfall_notes", "model",
    # question mix (build_facts.py)
    "mix_9ma0", "all", "pure", "stats", "mech", *build_facts.MIX_BANDS,
}
MARK_CODE = re.compile(r"^(ddM|dM|dB|M|A|B)[1-9](\*|ft|cso|cao)?$")
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
URL = re.compile(r"^https?://\S+$")
CODE_SOURCES = {f"{s}{x}" for s in ("mark-lines", "note-lines", "all") for x in ("", "-irregular")} | {"unresolved"}
RATINGS = {"well_answered", "mixed", "poorly_answered"}
CLUSTER_ID = re.compile(r"^c\d{1,3}$")  # unmatched-note cluster ids (match_errors.py)
MODELS = {"bge-small-en-v1-5"}


def vocabulary() -> set[str]:
    conn = sqlite3.connect(f"file:{packs.load('pearson-private').db}?mode=ro", uri=True)
    ids = set()
    for sql in ("SELECT id FROM skills", "SELECT id FROM skill_groups", "SELECT id FROM question_types",
                "SELECT id FROM questions", "SELECT DISTINCT paper_id FROM questions",
                "SELECT DISTINCT unit FROM questions", "SELECT DISTINCT qualification FROM questions",
                "SELECT DISTINCT paper FROM questions", "SELECT DISTINCT component FROM questions",
                "SELECT DISTINCT sitting FROM questions",
                "SELECT question_id || ':' || COALESCE(label, '') FROM question_parts"):
        ids |= {r[0] for r in conn.execute(sql) if r[0]}
    ids |= set(build_facts.COMMANDS) | set(build_facts.FORMS) | CODE_SOURCES | RATINGS | FIELD_NAMES | MODELS
    ids |= {f"{t}-{n}" for t in ("dp", "sf") for n in range(1, 10)}
    errors = ROOT / "content" / "error_codes.json"
    if errors.exists():
        ids |= {e["id"] for e in json.loads(errors.read_text())["codes"]}
    return ids


def ok(s: str, vocab: set[str]) -> bool:
    if s in vocab or NUMBER.match(s) or URL.match(s) or CLUSTER_ID.match(s):
        return True
    toks = s.split(" ")
    return all(MARK_CODE.match(t) for t in toks)  # a mark code or a sequence of them


def check_file(path: Path, vocab: set[str]) -> list[str]:
    bad: list[str] = []

    def walk(o, where):
        if isinstance(o, dict):
            for k, v in o.items():
                if not ok(k, vocab):
                    bad.append(f"{where}: key {k[:60]!r}")
                walk(v, f"{where}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{where}[{i}]")
        elif isinstance(o, str):
            if not ok(o, vocab):
                bad.append(f"{where}: {o[:60]!r}")
            elif len(o) > 40 and o not in vocab and not URL.match(o) and not all(MARK_CODE.match(t) for t in o.split(" ")):
                bad.append(f"{where}: too long ({len(o)} chars)")
    walk(json.loads(path.read_text()), path.name)
    return bad


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "facts").glob("*.json"))
    vocab = vocabulary()
    failed = False
    for f in files:
        bad = check_file(f, vocab)
        print(f"{f.name}: {'PASS' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:15]:
            print("   ", line)
        failed |= bool(bad)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
