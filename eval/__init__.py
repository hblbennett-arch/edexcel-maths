"""Evals. Each one calls licence_gate() first: on a commercial content pack (CONTENT_PACK=clean)
it refuses to run unless scripts/clean/check_provenance.py passes."""
import sys
from pathlib import Path


def licence_gate() -> None:
    from chatbot import pack
    p = pack.current()
    print(f"content pack: {p.name}", file=sys.stderr)
    if not p.commercial:
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "clean"))
    import check_provenance
    problems = check_provenance.check(p)
    if problems:
        raise SystemExit(f"licence gate FAILED for pack {p.name!r}: {problems[:5]}")
