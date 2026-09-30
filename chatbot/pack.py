"""Content packs: the engine (chatbot/) reads all question content through one pack.

A pack is content/<name>/pack.json plus the files it names (paths relative to that folder):

    {"db": "pack.db", "embeddings_dir": ".", "tags": "tags.json", "commercial": true}

  pearson-private  points at data/processed/ (the Pearson transcriptions). Local personal study and
                   building the fact layer only; never shipped.
  clean            the product pack: original questions only (scripts/clean/check_provenance.py).

Pick one with CONTENT_PACK=<name> (environment or .env); the default is "pearson-private".
"""
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import config  # noqa: F401  (loads .env before CONTENT_PACK is read)

ROOT = Path(__file__).resolve().parent.parent
PACKS_DIR = ROOT / "content"
DEFAULT_PACK = "pearson-private"


@dataclass(frozen=True)
class Pack:
    name: str
    dir: Path
    db: Path
    embeddings_dir: Path
    tags: Path
    commercial: bool


def load(name: str | None = None) -> Pack:
    name = name or os.environ.get("CONTENT_PACK") or DEFAULT_PACK
    folder = PACKS_DIR / name
    manifest = folder / "pack.json"
    if not manifest.exists():
        known = sorted(p.parent.name for p in PACKS_DIR.glob("*/pack.json"))
        raise SystemExit(f"unknown content pack {name!r} (no {manifest}); known: {known}")
    m = json.loads(manifest.read_text())
    return Pack(name=name, dir=folder, db=(folder / m["db"]).resolve(),
                embeddings_dir=(folder / m.get("embeddings_dir", ".")).resolve(),
                tags=(folder / m.get("tags", "tags.json")).resolve(),
                commercial=bool(m.get("commercial", False)))


@lru_cache(maxsize=1)
def current() -> Pack:
    return load()


# ---- pack schema -----------------------------------------------------------------------------
# Every pack database = content/schema.sql + the provenance columns below on each content table
# (docs/handoff-clean-room.md §4). Rows carry them so the licence gate can prove where each came from.
SCHEMA_PATH = PACKS_DIR / "schema.sql"
PROVENANCES = ("original", "ogl", "pearson-private")
COMMERCIAL_PROVENANCES = ("original", "ogl")
REVIEW_DECISIONS = ("accept", "edit", "reject")
PROVENANCE_COLUMNS = (
    f"provenance TEXT CHECK (provenance IN {PROVENANCES})",
    "blueprint_id TEXT",          # content/blueprints/<id>.json the item was generated from
    "generator_model TEXT",       # e.g. "claude-opus-5-5"
    "generated_at TEXT",          # ISO timestamp
    "gate_results TEXT",          # JSON {"G1": {"pass": true, ...}, ...}
    "reviewed_by TEXT",
    "reviewed_at TEXT",
    f"review_decision TEXT CHECK (review_decision IN {REVIEW_DECISIONS})",
    "review_notes TEXT",
)
PROVENANCE_TABLES = ("questions", "question_parts", "pitfalls")
# Our own common-mistake notes (replace examiner_notes in the clean pack). One row per pitfall,
# tied to a part and, where possible, a step of the worked solution and an error code (§5.2).
PITFALLS_DDL = """
CREATE TABLE IF NOT EXISTS pitfalls (
    id TEXT PRIMARY KEY,          -- e.g. "<question_id>_p3"
    question_id TEXT NOT NULL REFERENCES questions(id),
    part_label TEXT,              -- NULL = whole question
    step INTEGER,                 -- step of the worked solution it refers to
    error_code TEXT,              -- content/error_codes.json id
    text TEXT NOT NULL,           -- our own words, using the question's numbers
    says_common INTEGER NOT NULL DEFAULT 0  -- 1 if the text calls it "common" (needs frequency support)
);
"""


def create_schema(conn, provenance: str | None = None) -> None:
    """Create an empty pack database: base schema, pitfalls table and provenance columns.
    `provenance` sets a default for rows inserted later (only build_db.py's pearson-private build
    uses it; clean-pack rows must state their provenance explicitly)."""
    conn.executescript(SCHEMA_PATH.read_text())
    conn.executescript(PITFALLS_DDL)
    for table in PROVENANCE_TABLES:
        for col in PROVENANCE_COLUMNS:
            if provenance and col.startswith("provenance "):
                assert provenance in PROVENANCES, provenance
                col = col.replace("provenance TEXT", f"provenance TEXT DEFAULT '{provenance}'", 1)
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
