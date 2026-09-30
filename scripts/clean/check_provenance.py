#!/usr/bin/env python3
"""Licence gate for content packs (docs/handoff-clean-room.md §4). Deterministic, no model calls.

    .venv/bin/python scripts/clean/check_provenance.py                 # every commercial pack
    .venv/bin/python scripts/clean/check_provenance.py --pack clean
    .venv/bin/python scripts/clean/check_provenance.py --pack pearson-private   # must FAIL (self-test)

A commercial pack fails if:
  1. its database lives outside the pack folder (e.g. points at data/processed/);
  2. any row of questions / question_parts / pitfalls has provenance other than original/ogl;
  3. any such row lacks an accept/edit review decision, or a passing G1-G8 in gate_results;
  4. a Pearson-only table (examiner_notes, question_performance) has rows;
  5. any text anywhere in the database or the pack's files contains a banned phrase
     ("examiner report", "Pearson Education", a PMT link, ...).
Exit code 1 on any failure; the evals call check() for commercial packs before running.
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chatbot import pack as packs  # noqa: E402

REQUIRED_GATES = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
PEARSON_TABLES = ("examiner_notes", "question_performance")
BANNED = re.compile("|".join([
    r"examiners?'?\s*reports?", r"principal\s+examiner", r"examiners?\s+(said|say|says|noted|commented|reported|found)",
    r"report\s+on\s+the\s+examination", r"pearson\s+(says|said|education)", r"©\s*pearson", r"copyright\s+pearson",
    r"physicsandmathstutor", r"\bpmt\b", r"official\s+mark\s*scheme", r"general\s+marking\s+guidance",
]), re.I)


def _text_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})") if (r[2] or "").upper() in ("TEXT", "")]


def check(p: packs.Pack) -> list[str]:
    problems: list[str] = []
    if p.dir.resolve() not in p.db.parents:
        problems.append(f"database {p.db} is outside the pack folder {p.dir}")
    if not p.db.exists():
        return problems + [f"database {p.db} not found"]
    conn = sqlite3.connect(f"file:{p.db}?mode=ro", uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]

    for table in packs.PROVENANCE_TABLES:
        if table not in tables:
            problems.append(f"table {table} missing")
            continue
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if "provenance" not in cols:
            problems.append(f"{table}: no provenance column")
            continue
        key = "id" if "id" in cols else "question_id || ':' || COALESCE(label, '')"
        bad = conn.execute(f"SELECT {key}, provenance FROM {table} WHERE provenance IS NULL OR provenance NOT IN "
                           f"{packs.COMMERCIAL_PROVENANCES}").fetchall()
        if bad:
            problems.append(f"{table}: {len(bad)} row(s) not original/ogl, e.g. {bad[:3]}")
        for rid, decision, gates in conn.execute(f"SELECT {key}, review_decision, gate_results FROM {table}"):
            if decision not in ("accept", "edit"):
                problems.append(f"{table} {rid}: review_decision {decision!r} (needs accept/edit)")
            try:
                results = json.loads(gates or "{}")
            except json.JSONDecodeError:
                results = {}
            failed = [g for g in REQUIRED_GATES if not (results.get(g) or {}).get("pass")]
            if failed:
                problems.append(f"{table} {rid}: gates not passed: {','.join(failed)}")

    for table in PEARSON_TABLES:
        if table in tables and conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]:
            problems.append(f"Pearson-only table {table} has rows")

    for table in tables:
        for col in _text_columns(conn, table):
            for rowid, value in conn.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL"):
                m = BANNED.search(str(value))
                if m:
                    problems.append(f"{table}.{col} rowid {rowid}: banned phrase {m.group(0)!r}")

    for f in sorted(p.dir.rglob("*")):
        if f.is_file() and f.suffix in (".json", ".md", ".txt", ".html", ".svg", ".csv"):
            m = BANNED.search(f.read_text(errors="ignore"))
            if m:
                problems.append(f"{f.relative_to(ROOT)}: banned phrase {m.group(0)!r}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", action="append", help="pack name (repeatable); default: every commercial pack")
    args = ap.parse_args()
    names = args.pack or [d.parent.name for d in sorted(packs.PACKS_DIR.glob("*/pack.json"))
                          if json.loads(d.read_text()).get("commercial")]
    failed = False
    for name in names:
        problems = check(packs.load(name))
        print(f"{name}: {'PASS' if not problems else f'FAIL ({len(problems)} problem(s))'}")
        for line in problems[:20]:
            print("   ", line)
        if len(problems) > 20:
            print(f"    ... and {len(problems) - 20} more")
        failed |= bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
