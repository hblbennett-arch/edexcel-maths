"""Read-only access to the knowledge base (data/processed/questions.db)."""
import sqlite3
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "questions.db"

# Cross-cutting exam-technique skills appear in a large share of parts, so they
# say little about what a part is *about*. Recommendations down-weight them.
EXAM_TECHNIQUE_GROUP = "exam-technique"


@lru_cache(maxsize=1)
def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found — run .venv/bin/python scripts/build_db.py first")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def rows(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return connect().execute(sql, params).fetchall()


def one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    return connect().execute(sql, params).fetchone()


def part_key(question_id: str, label: str | None) -> str:
    """Stable id for a part: "P1_June2022_Q15:b" ("P1_June2022_Q1:" for a single-part question)."""
    return f"{question_id}:{label or ''}"


def split_part_key(key: str) -> tuple[str, str | None]:
    qid, _, label = key.partition(":")
    return qid, (label or None)
