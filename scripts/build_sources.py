#!/usr/bin/env python3
"""Build data/processed/sources.json — a link catalogue for every Edexcel
A Level (9MA0) and AS (8MA0) maths paper PMT lists, so the chatbot can cite
and link the original question paper, mark scheme and examiner report.

Links are scraped from PMT's listing pages (never constructed by guesswork),
plus the Pearson examiner-report URLs recorded in docs/pmt-url-patterns.md.
Each entry's `paper_id` uses the same naming as data/raw/ and
data/processed/questions/ (e.g. P1_June2022, P1_Oct2020, P3_June2019_mech,
ASP2_Nov2021_stats).

    .venv/bin/python scripts/build_sources.py            # scrape + write
    .venv/bin/python scripts/build_sources.py --verify   # also HEAD-check every URL

PMT's own mock papers are skipped (not official Pearson papers). PMT "MA"
files are PMT-written model answers, kept but labelled as unofficial.
"""
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUT_PATH = PROCESSED_DIR / "sources.json"
QUESTIONS_DIR = PROCESSED_DIR / "questions"

LISTING_PAGES = {
    "9MA0": "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers/",
    "8MA0": "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers-as/",
}
PMT_VIEWER = "https://www.physicsandmathstutor.com/pdf-pages/?pdf="
PEARSON_ER = "https://qualifications.pearson.com/content/dam/pdf/A-Level/Mathematics/2017/Exam-materials/"
USER_AGENT = "Mozilla/5.0"

# Verified 2026-09-25 (HTTP 200, application/pdf). Extend when more are confirmed.
PEARSON_ER_FILES = {
    "P1_June2018": "9MA0_01_pef_20180815", "P2_June2018": "9MA0_02_pef_20180815",
    "P1_June2019": "9MA0_01_pef_20190815", "P2_June2019": "9MA0_02_pef_20190815",
    "P1_Oct2020": "9MA0_01_pef_20201217", "P2_Oct2020": "9MA0_02_pef_20201217",
    "P1_Oct2021": "9MA0_01_pef_20211216", "P2_Oct2021": "9MA0_02_pef_20211216",
    "P1_June2022": "9ma0-01-pef-20220818", "P2_June2022": "9ma0-02-pef-20220818",
    "P1_June2023": "9ma0-01-pef-20230817", "P2_June2023": "9ma0-02-pef-20230817",
    "P1_June2024": "9ma0-01-pef-20240815", "P2_June2024": "9ma0-02-pef-20240815",
}

# e.g. .../Edexcel/Paper-3/QP/June 2019 QP (Mech).pdf   .../AS-Paper-1/MS/November 2021 MS.pdf
URL_RE = re.compile(
    r"/Edexcel/(?P<as>AS-)?Paper-(?P<num>\d)/(?P<doc>QP|MS|MA)/"
    r"(?P<session>June|October|November|Sample|Specimen)(?: (?P<year>\d{4}))? (?P=doc)"
    r"(?: \((?P<component>Mech|Stats)\))?\.pdf$"
)
SESSION_SHORT = {"June": "June", "October": "Oct", "November": "Nov", "Sample": "Sample", "Specimen": "Specimen"}
DOC_KEY = {"QP": "question_paper", "MS": "mark_scheme", "MA": "pmt_model_answers"}


def fetch(url: str) -> str:
    # curl (not urllib) so HTTPS uses the macOS system trust store; Python's
    # bundled CAs reject the certificate chain seen on some networks.
    return subprocess.run(["curl", "-sfL", "-A", USER_AGENT, url],
                          capture_output=True, text=True, check=True).stdout


def head_ok(url: str) -> bool:
    """True if the URL serves a PDF (HTTP 200 after redirects)."""
    result = subprocess.run(
        ["curl", "-sL", "-o", "/dev/null", "-A", USER_AGENT, "-w", "%{http_code} %{content_type}", url],
        capture_output=True, text=True)
    status, _, content_type = result.stdout.partition(" ")
    return status == "200" and "pdf" in content_type


def link(url: str) -> dict:
    """Download URL (spaces %-encoded) plus PMT's in-browser viewer URL."""
    encoded = urllib.parse.quote(url, safe=":/")
    entry = {"url": encoded}
    if "physicsandmathstutor.com" in url:
        entry["viewer_url"] = PMT_VIEWER + urllib.parse.quote(url, safe="")
    return entry


PEARSON_MANIFEST = PROCESSED_DIR.parent / "raw" / "pearson" / "manifest.json"
PEARSON_DOC_KEY = {"QP": "question_paper", "MS": "mark_scheme", "ER": "examiner_report"}


def add_pearson(papers: dict[str, dict]) -> None:
    """Merge papers downloaded from Pearson (scripts/scrape_pearson.py). 9MA0 papers keep
    their PMT links and gain any Pearson document PMT lacks (examiner reports); IAL and
    GCE papers are Pearson-only. Locked (Edexcel Online) documents are skipped."""
    if not PEARSON_MANIFEST.exists():
        print("  (no data/raw/pearson/manifest.json — run scripts/scrape_pearson.py for IAL/GCE papers)")
        return
    for d in json.loads(PEARSON_MANIFEST.read_text()):
        if d["locked"] or d["unit"] == "ALL" or not d.get("local_pdf"):
            continue
        entry = papers.get(d["paper_id"])
        if entry is None:
            if d["qualification"] == "9MA0":
                continue                  # PMT lists every 9MA0 paper; don't invent new ids
            entry = papers.setdefault(d["paper_id"], {
                "paper_id": d["paper_id"], "spec": d["qualification"], "paper": d["unit"] + d["variant"],
                "sitting": d["sitting"], "component": d["component"], "official": True})
        entry.setdefault("qualification", d["qualification"])
        entry.setdefault("unit", d["unit"])
        key = PEARSON_DOC_KEY[d["doc_type"]]
        if key not in entry:
            entry[key] = {"url": d["url"], "viewer_url": d["url"], "publisher": "Pearson"}


def main() -> None:
    verify = "--verify" in sys.argv
    papers: dict[str, dict] = {}

    for spec, page in LISTING_PAGES.items():
        urls = sorted(set(re.findall(r'href="(https://pmt\.physicsandmathstutor\.com/download/[^"]+\.pdf)"', fetch(page))))
        for url in urls:
            m = URL_RE.search(url)
            if not m:
                continue  # PMT mocks and anything unrecognised
            is_as = bool(m["as"])
            if (spec == "8MA0") != is_as:
                continue
            paper = f"{'ASP' if is_as else 'P'}{m['num']}"
            sitting = SESSION_SHORT[m["session"]] + (m["year"] or "")
            component = m["component"].lower() if m["component"] else None
            paper_id = f"{paper}_{sitting}" + (f"_{component}" if component else "")
            entry = papers.setdefault(paper_id, {
                "paper_id": paper_id, "spec": spec, "paper": paper, "sitting": sitting,
                "component": component, "official": m["session"] not in ("Sample",),
            })
            entry[DOC_KEY[m["doc"]]] = link(url)

    for paper_id, er_file in PEARSON_ER_FILES.items():
        if paper_id not in papers:
            raise SystemExit(f"Examiner report mapped for {paper_id}, but PMT lists no such paper")
        papers[paper_id]["examiner_report"] = {"url": f"{PEARSON_ER}{er_file}.pdf", "publisher": "Pearson"}

    add_pearson(papers)

    in_kb = {p.stem for p in QUESTIONS_DIR.glob("*.json")}
    missing = in_kb - papers.keys()
    if missing:
        raise SystemExit(f"Knowledge-base papers with no PMT listing: {sorted(missing)}")
    for entry in papers.values():
        entry["in_knowledge_base"] = entry["paper_id"] in in_kb
        if "pmt_model_answers" in entry:
            entry["pmt_model_answers"]["note"] = "Unofficial worked answers written by PMT, not Pearson"

    if verify:
        bad = [(pid, key) for pid, e in papers.items()
               for key in ("question_paper", "mark_scheme", "examiner_report")
               if key in e and not head_ok(e[key]["url"])]
        if bad:
            raise SystemExit(f"Broken links: {bad}")
        print(f"  verified every question paper, mark scheme and examiner report link")

    for e in papers.values():
        e.setdefault("qualification", e["spec"])
    key_order = ["paper_id", "spec", "qualification", "unit", "paper", "sitting", "component", "official",
                 "in_knowledge_base",
                 "question_paper", "mark_scheme", "examiner_report", "pmt_model_answers"]
    ordered = [{k: e[k] for k in key_order if k in e}
               for e in sorted(papers.values(), key=lambda e: (e["spec"], e["paper"], e["component"] or "", e["sitting"]))]
    OUT_PATH.write_text(json.dumps({
        "_generated": date.today().isoformat(),
        "_note": "Generated by scripts/build_sources.py — edit that script, not this file.",
        "papers": ordered,
    }, indent=2) + "\n")
    n_kb = sum(e["in_knowledge_base"] for e in ordered)
    print(f"Wrote {OUT_PATH.relative_to(PROCESSED_DIR.parent.parent)} — {len(ordered)} papers "
          f"({n_kb} in the knowledge base, {sum('examiner_report' in e for e in ordered)} with examiner reports)")


if __name__ == "__main__":
    main()
