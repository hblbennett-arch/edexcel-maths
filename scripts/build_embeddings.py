#!/usr/bin/env python3
"""Embed every searchable document (see chatbot/search.py) with a local model.

Writes <pack embeddings_dir>/embeddings_<model>.npz (gitignored; pearson-private: data/processed/,
CONTENT_PACK=clean: content/clean/). Rerun after scripts/build_db.py (or build_pack.py) whenever
questions, tags, examiner notes or pitfalls change — chatbot.search refuses to load a stale file.

    .venv/bin/python scripts/build_embeddings.py                              # default model
    .venv/bin/python scripts/build_embeddings.py --model BAAI/bge-base-en-v1.5
"""
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chatbot import search  # noqa: E402


def main() -> None:
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else search.DEFAULT_MODEL
    docs = search.documents()
    t0 = time.time()
    vecs = search.embed([text for _, _, text in docs], model)
    out = search.embeddings_path(model)
    np.savez_compressed(out, ids=np.array([d[0] for d in docs]), vecs=vecs.astype(np.float32))
    kinds = {}
    for _, kind, _ in docs:
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"embedded {len(docs)} docs {kinds} with {model} in {time.time() - t0:.0f}s -> {out.name}")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)  # skip interpreter teardown: onnxruntime can abort while freeing its thread pool
