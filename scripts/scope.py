"""What gets PROCESSED (extracted, filtered, noted, tagged) — separate from what is scraped/kept on disk.

User decision (2026-09-26): for Statistics and Mechanics only the first units (S1, M1) are processed;
S2/S3/M2/M3 papers stay downloaded in data/raw/pearson/ but are not queued. No Further Maths (never
scraped). 9MA0 is always processed (Paper 3 covers the whole current Stats/Mech content).
Pure units (C1-C4, C12, C34, WMA11-14) are all processed.
"""
import json
from pathlib import Path

NOT_PROCESSED_UNITS = {
    "WST02", "WST03", "WME02", "WME03",      # IAL S2, S3, M2, M3 (2013 and 2018 specs share these codes)
    "6684", "6691", "6678", "6679",          # UK GCE S2, S3, M2, M3
}
# 9MA0 Pure (P1/P2) was built by the original pipeline (data/processed/questions/P1_*.json), and
# June 2025 Pure is held back as the unseen test set, so none of it is re-queued.
NOT_QUEUED_PREFIXES = ("P1_", "P2_")
MANIFEST = Path(__file__).resolve().parent.parent / "data" / "raw" / "pearson" / "manifest.json"


def unit_of(paper_id: str) -> str | None:
    for d in json.loads(MANIFEST.read_text()):
        if d["paper_id"] == paper_id:
            return d["unit"]
    return None


def in_processing_scope(paper_id: str, unit: str | None = None) -> bool:
    unit = unit or unit_of(paper_id)
    return unit not in NOT_PROCESSED_UNITS and not paper_id.startswith(NOT_QUEUED_PREFIXES)
