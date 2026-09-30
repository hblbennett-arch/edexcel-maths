"""Hybrid search over the knowledge base: BM25 keywords + local embeddings.

Documents (one per row, `kind` in brackets):
  question  — a whole question's plain text (used to recognise pasted questions)
  part      — stem + one part's text + its skill titles (what the part asks and tests)
  skill     — skill title + description + group title
  note      — an examiner-report quote
  qtype     — question-type title + definition

Maths symbols embed poorly, so keyword (BM25) and semantic rankings are merged
with reciprocal-rank fusion (RRF). Vectors are built by scripts/build_embeddings.py
into <pack embeddings_dir>/embeddings_<model>.npz (gitignored; rebuild after build_db.py).
"""
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from . import db, pack
from .text import latex_to_plain, tokens

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
MODEL_CACHE = Path.home() / ".cache" / "edexcel-maths-devtools" / "fastembed"
# bge models expect this prefix on queries (not on documents) for retrieval.
QUERY_PREFIX = {"BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
                "BAAI/bge-base-en-v1.5": "Represent this sentence for searching relevant passages: "}
RRF_K = 60
# Best mode per document kind, chosen by eval/retrieval.py (2026-09-25, bge-small):
# recognising pasted questions is a near-verbatim match -> keywords win (100% vs 93%);
# free-text skill queries are about meaning -> semantic wins (MRR 0.94 vs 0.85 BM25).
DEFAULT_MODE = {"question": "bm25", "skill": "semantic"}


def embeddings_path(model: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
    return pack.current().embeddings_dir / f"embeddings_{slug}.npz"


def documents() -> list[tuple[str, str, str]]:
    """(doc_id, kind, text) for everything searchable, built from questions.db."""
    docs = []
    skill_title = {r["id"]: r["title"] for r in db.rows("SELECT id, title FROM skills")}
    part_skills: dict[str, list[str]] = {}
    for r in db.rows("SELECT question_id, part_label, tag_value FROM question_tags WHERE tag_type = 'skill'"):
        part_skills.setdefault(db.part_key(r["question_id"], r["part_label"]), []).append(skill_title[r["tag_value"]])
    for q in db.rows("SELECT id, question_text, stem FROM questions"):
        docs.append((f"question:{q['id']}", "question", latex_to_plain(q["question_text"])))
        for p in db.rows("SELECT label, text FROM question_parts WHERE question_id = ? ORDER BY part_index", (q["id"],)):
            key = db.part_key(q["id"], p["label"])
            stem = q["stem"] if p["label"] is not None and q["stem"] else ""
            text = " ".join([latex_to_plain(stem), latex_to_plain(p["text"]), ". Skills: " + "; ".join(part_skills.get(key, []))])
            docs.append((f"part:{key}", "part", text))
    for s in db.rows("SELECT s.id, s.title, s.description, g.title AS gtitle FROM skills s JOIN skill_groups g ON g.id = s.group_id"):
        # The id is often the everyday name ("second-derivative-test") when the title isn't
        # ("Determine the nature of a stationary point"), so include it in words.
        docs.append((f"skill:{s['id']}", "skill",
                     f"{s['id'].replace('-', ' ')}: {s['title']}. {s['description']} ({s['gtitle']})"))
    for n in db.rows("SELECT id, COALESCE(display, quote) AS t FROM examiner_notes"):
        docs.append((f"note:{n['id']}", "note", latex_to_plain(n["t"])))
    for t in db.rows("SELECT id, title, definition FROM question_types"):
        docs.append((f"qtype:{t['id']}", "qtype", f"{t['id'].replace('-', ' ')}: {t['title']}. {t['definition'] or ''}"))
    return docs


@lru_cache(maxsize=2)
def _embedder(model: str):
    import truststore  # verify HTTPS with the macOS trust store (TLS-inspecting networks)
    truststore.inject_into_ssl()
    from fastembed import TextEmbedding
    return TextEmbedding(model, cache_dir=str(MODEL_CACHE))


def embed(texts: list[str], model: str = DEFAULT_MODEL) -> np.ndarray:
    vecs = np.array(list(_embedder(model).embed(texts)), dtype=np.float32)
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


@lru_cache(maxsize=512)
def embed_query(query: str, model: str = DEFAULT_MODEL) -> np.ndarray:
    """One search query's vector (cached: a practice request is searched against several kinds)."""
    return embed([QUERY_PREFIX.get(model, "") + latex_to_plain(query)], model)[0]


@dataclass
class Hit:
    doc_id: str
    kind: str
    score: float      # fused RRF score (higher = better)
    semantic: float   # cosine similarity, for thresholds
    text: str


class Index:
    def __init__(self, model: str = DEFAULT_MODEL):
        path = embeddings_path(model)
        if not path.exists():
            raise SystemExit(f"{path.name} missing — run .venv/bin/python scripts/build_embeddings.py --model {model}")
        data = np.load(path, allow_pickle=False)
        self.model = model
        self.ids = [str(x) for x in data["ids"]]
        self.vecs = data["vecs"]
        docs = {d[0]: d for d in documents()}
        stale = set(self.ids) ^ set(docs)
        if stale:
            raise SystemExit(f"{path.name} is out of date ({len(stale)} changed docs) — rerun scripts/build_embeddings.py")
        self.kinds = [docs[i][1] for i in self.ids]
        self.texts = [docs[i][2] for i in self.ids]
        self._bm25: dict[str, tuple[BM25Okapi, list[int]]] = {}

    def _bm25_for(self, kind: str) -> tuple[BM25Okapi, list[int]]:
        if kind not in self._bm25:
            rows = [i for i, k in enumerate(self.kinds) if k == kind]
            self._bm25[kind] = (BM25Okapi([tokens(self.texts[i]) or ["_"] for i in rows]), rows)
        return self._bm25[kind]

    def bm25_scores(self, query: str, kind: str) -> tuple[list[str], "np.ndarray"]:
        bm25, rows = self._bm25_for(kind)
        return [self.ids[i] for i in rows], bm25.get_scores(tokens(query) or ["_"])

    def scores(self, query: str, kind: str) -> tuple[list[str], "np.ndarray", "np.ndarray"]:
        """(doc ids, BM25 scores, cosine similarities) for every doc of one kind, unranked."""
        bm25, rows = self._bm25_for(kind)
        return ([self.ids[i] for i in rows], bm25.get_scores(tokens(query) or ["_"]),
                self.vecs[rows] @ embed_query(query, self.model))

    def search(self, query: str, kind: str, k: int = 10, mode: str | None = None) -> list[Hit]:
        """Top-k docs of one kind. mode: 'hybrid', 'semantic' or 'bm25' (default: best per kind)."""
        mode = mode or DEFAULT_MODE.get(kind, "hybrid")
        bm25, rows = self._bm25_for(kind)
        sem = self.vecs[rows] @ embed_query(query, self.model)
        sem_rank = np.argsort(-sem)
        kw = bm25.get_scores(tokens(query) or ["_"])
        kw_rank = np.argsort(-kw)
        fused = np.zeros(len(rows))
        if mode in ("hybrid", "semantic"):
            fused[sem_rank] += 1.0 / (RRF_K + np.arange(1, len(rows) + 1))
        if mode in ("hybrid", "bm25"):
            fused[kw_rank] += 1.0 / (RRF_K + np.arange(1, len(rows) + 1))
        top = np.argsort(-fused)[:k]
        return [Hit(self.ids[rows[i]], kind, float(fused[i]), float(sem[i]), self.texts[rows[i]]) for i in top]


@lru_cache(maxsize=2)
def get_index(model: str = DEFAULT_MODEL) -> Index:
    return Index(model)
