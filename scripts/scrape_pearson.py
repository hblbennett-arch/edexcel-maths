#!/usr/bin/env python3
"""Catalogue and download Edexcel maths past papers from Pearson's own site.

Pearson's past-papers page (qualifications.pearson.com/.../past-papers.html) is
an Angular app whose document list comes from Pearson's public Algolia search
index. The app ID, search-only key and index name are hidden <input>s in the
page (class algoliaAppId / algoliaAPIKey / algoliaIndexName). Querying that
index directly returns every document's URL, title and tags (qualification
family, specification code, unit, exam series, document type), which is more
complete and reliable than scraping the rendered page.

Scope (confirmed with the user 2026-09-25):
  9MA0      UK A Level 2017 spec: Papers 1, 2, 3 (31 = Stats, 32 = Mech; 03 = the
            combined June 2018 paper)            -> status "current"
  IAL-2018  International A Level 2018 spec: WMA11-14 (P1-P4), WST01-03 (S1-S3),
            WME01-03 (M1-M3)                     -> status "legacy" (extra questions)
  IAL-2013  International A Level 2013 spec: WMA01 (C12), WMA02 (C34), WST01-03,
            WME01-03                             -> "legacy"
  GCE-2008  UK GCE (pre-2017): 6663-6666 (C1-C4), 6683/6684/6691 (S1-S3),
            6677-6679 (M1-M3)                    -> "legacy"
Further Maths (WFM/66xx FP, 9FM0) and Decision (WDM/6689/6690) are out of scope.

    .venv/bin/python scripts/scrape_pearson.py --catalogue   # query index, write manifest (no downloads)
    .venv/bin/python scripts/scrape_pearson.py --download    # + download PDFs, pdftotext, sha1
    .venv/bin/python scripts/scrape_pearson.py --report      # completeness table -> docs/pearson-coverage.md

Files: data/raw/pearson/<qualification>/<series>/<paper_id>_{QP,MS,ER}.pdf/.txt
       data/raw/pearson/manifest.json  (url, local path, qualification, unit, series, doc type, sha1)
Papers from the last ~9 months are "secure" (Edexcel Online login only); they are
catalogued with locked=true and reported as gaps, never downloaded.
"""
import argparse
import collections
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pearson"
MANIFEST = RAW / "manifest.json"
REPORT = ROOT / "docs" / "pearson-coverage.md"

SITE = "https://qualifications.pearson.com"
# Public search-only credentials, as embedded in the past-papers page.
ALGOLIA_APP = "L639T95U5A"
ALGOLIA_KEY = "f79c7a8352e9ffbdaec387bf43612ee6"
ALGOLIA_INDEX = "qualifications-uk_LIVE_master-content"
USER_AGENT = "Mozilla/5.0"
FAMILIES = ["A-Level", "International-Advanced-Level"]
DOC_TYPES = {"Question-paper": "QP", "Mark-scheme": "MS", "Examiner-report": "ER"}

# unit code -> (qualification, component, short name)
UNITS = {
    "9MA0-01": ("9MA0", "pure", "P1"), "9MA0-02": ("9MA0", "pure", "P2"),
    "9MA0-03": ("9MA0", "stats+mech", "P3"),
    "9MA0-31": ("9MA0", "stats", "P3"), "9MA0-32": ("9MA0", "mech", "P3"),
    "WMA11": ("IAL-2018", "pure", "P1"), "WMA12": ("IAL-2018", "pure", "P2"),
    "WMA13": ("IAL-2018", "pure", "P3"), "WMA14": ("IAL-2018", "pure", "P4"),
    "WMA01": ("IAL-2013", "pure", "C12"), "WMA02": ("IAL-2013", "pure", "C34"),
    # WST0n / WME0n codes are shared by both IAL specs: the spec tag decides.
    "WST01": (None, "stats", "S1"), "WST02": (None, "stats", "S2"), "WST03": (None, "stats", "S3"),
    "WME01": (None, "mech", "M1"), "WME02": (None, "mech", "M2"), "WME03": (None, "mech", "M3"),
    "6663": ("GCE-2008", "pure", "C1"), "6664": ("GCE-2008", "pure", "C2"),
    "6665": ("GCE-2008", "pure", "C3"), "6666": ("GCE-2008", "pure", "C4"),
    "6683": ("GCE-2008", "stats", "S1"), "6684": ("GCE-2008", "stats", "S2"),
    "6691": ("GCE-2008", "stats", "S3"),
    "6677": ("GCE-2008", "mech", "M1"), "6678": ("GCE-2008", "mech", "M2"),
    "6679": ("GCE-2008", "mech", "M3"),
}
QUAL_PREFIX = {"IAL-2018": "IAL2018", "IAL-2013": "IAL2013", "GCE-2008": "GCE2008"}
MONTH = {"January": "Jan", "June": "June", "October": "Oct", "November": "Nov", "May": "May"}

# e.g. wma11-01a-que-20260109  WMA11_01_que_20200305  6663_01R_msc_20130815
#      9MA0_31_rms_20190815  9ma0-03-que-2018  6663A_01_msc_20140306
FILE_RE = re.compile(
    r"^(?P<code>9ma0|w[a-z]{2}\d\d|66\d\dA?)[_-](?P<paper>\d{1,2}[a-z]?)[_-]"
    r"(?P<doc>que|qp|msc|rms|ms|pef)[_-](?P<date>\d{4,9})", re.I)
TITLE_CODE_RE = re.compile(r"\(\s*(W[A-Z]{2}\d\d|66\d\dA?)\s*\)")


def algolia(filters: str, page: int = 0, hits: int = 1000, facets=None) -> dict:
    params = f"filters={urllib.parse.quote(filters)}&hitsPerPage={hits}&page={page}"
    if facets:
        params += "&facets=" + urllib.parse.quote(json.dumps(facets)) + "&maxValuesPerFacet=1000"
    for attempt in range(5):                               # transient TLS resets happen on this network
        res = subprocess.run(
            ["curl", "-sf", f"https://{ALGOLIA_APP}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query",
             "-H", f"X-Algolia-API-Key: {ALGOLIA_KEY}", "-H", f"X-Algolia-Application-Id: {ALGOLIA_APP}",
             "-d", json.dumps({"params": params})], capture_output=True, text=True)
        if res.returncode == 0:
            return json.loads(res.stdout)
        time.sleep(2 + 3 * attempt)
    sys.exit(f"Algolia query failed (curl exit {res.returncode})")


def fetch_records() -> list[dict]:
    """Every maths QP/MS/ER record in both families, one query per exam series
    (Algolia caps a result set at 1000 hits)."""
    records = {}
    for fam in FAMILIES:
        base = (f'category:"Pearson-UK:Qualification-Family/{fam}" AND '
                f'category:"Pearson-UK:Qualification-Subject/Mathematics" AND ('
                + " OR ".join(f'category:"Pearson-UK:Document-Type/{t}"' for t in DOC_TYPES) + ")")
        facet = algolia(base, hits=0, facets=["category"])["facets"]["category"]
        for series in sorted(k for k in facet if ":Exam-Series/" in k):
            d = algolia(base + f' AND category:"{series}"')
            if d["nbHits"] != len(d["hits"]):
                sys.exit(f"{series}: {d['nbHits']} hits but only {len(d['hits'])} returned")
            for h in d["hits"]:
                records[h["url"]] = {k: h[k] for k in ("url", "title", "category", "extension", "date") if k in h}
            time.sleep(0.3)
    return list(records.values())


def tag(rec: dict, kind: str) -> list[str]:
    return [c.split(f":{kind}/", 1)[1] for c in rec["category"] if f":{kind}/" in c]


def classify(rec: dict):
    """-> dict describing one in-scope document, or None if out of scope."""
    fname = rec["url"].rsplit("/", 1)[-1]
    doc_type = next((v for t in tag(rec, "Document-Type") for k, v in DOC_TYPES.items()
                     if t.lower() == k.lower()), None)
    series = tag(rec, "Exam-Series")
    if len(series) > 1:                                    # e.g. tagged June-2016 and October-2016
        series = [x for x in series if x.replace("-", " ") in rec["title"]] or series
    if not doc_type or len(series) != 1 or rec.get("extension") != "PDF":
        return None
    if "modified" in (fname + rec["title"]).lower():  # modified-format (accessibility) versions
        return None
    month, year = series[0].split("-")
    # Old descriptive filenames carry their own date ("13_M1_January_2006.pdf");
    # a few are tagged with the wrong series, so the filename wins.
    fm = re.search(r"(January|June|May|October|November)[_ -](\d{4})", urllib.parse.unquote(fname))
    if fm and not FILE_RE.match(fname):
        month, year = ("June" if fm.group(1) == "May" else fm.group(1)), fm.group(2)
        series = [f"{month}-{year}"]
    m = FILE_RE.match(fname)
    code = paper = None
    if m:
        code, paper = m.group("code").upper(), m.group("paper").upper()
        if code == "9MA0":
            code = f"9MA0-{paper[:2].zfill(2)}"
            paper = "01"
    else:
        codes = [c for c in TITLE_CODE_RE.findall(rec["title"]) if c.rstrip("A") in UNITS]
        fcode = re.match(r"(W[A-Z]{2}\d\d)_", fname, re.I)
        if codes or fcode:
            code = codes[0] if codes else fcode.group(1).upper()
            paper = "01R" if re.search(r"Paper[- ]1R", rec["title"] + fname) else "01"
        elif "Multiple units" in rec["title"]:
            # 2005-2009: one combined report / mark scheme for every GCE unit in the series
            sitting = f"{MONTH[month]}{year}"
            return {"paper_id": f"GCE2008_ALL_{sitting}", "qualification": "GCE-2008", "status": "legacy",
                    "unit": "ALL", "unit_name": "all units", "variant": "", "component": None,
                    "series": series[0], "sitting": sitting, "doc_type": doc_type, "title": rec["title"],
                    "url": SITE + urllib.parse.quote(rec["url"]), "locked": False, "file": fname}
        else:
            return None
    if code is None or code.rstrip("A") not in UNITS:
        return None
    variant, intl = "", False
    if code.endswith("A") and code[:-1] in UNITS:
        # 6663A-6666A (Jan 2014): C1-C4 papers headed "International Advanced Level" and listed by
        # Pearson under the IAL 2013 spec (the separate-unit version of C12/C34). The syllabus is
        # C1-C4, but the qualification is IAL-2013, not the UK GCE.
        code, variant, intl = code[:-1], "A", True
    if code.startswith("9MA0"):
        variant = ""
    else:
        paper = paper.zfill(2) if paper.isdigit() else paper.zfill(3)
        variant = variant or paper[2:]                     # 01R -> R, 01A -> A
    if "unused" in fname.lower():                          # contingency paper Pearson published unsat
        variant = "U"
    qual, component, short = UNITS[code]
    if intl:
        qual = "IAL-2013"
    specs = tag(rec, "Specification-Code")
    if qual is None:
        qual = "IAL-2018" if any("ial18-mathematics" in s for s in specs) else "IAL-2013"
    sitting = f"{MONTH[month]}{year}"
    if qual == "9MA0":
        if sitting == "Nov2021":
            sitting = "Oct2021"                            # our existing naming (report titled Nov)
        comp = {"9MA0-31": "_stats", "9MA0-32": "_mech"}.get(code, "")
        paper_id = f"{short}_{sitting}{comp}"
    else:
        paper_id = f"{QUAL_PREFIX[qual]}_{code}{variant}_{sitting}"
    return {"paper_id": paper_id, "qualification": qual, "status": "current" if qual == "9MA0" else "legacy",
            "unit": code, "unit_name": short, "variant": variant, "component": component,
            "series": series[0], "sitting": sitting, "doc_type": doc_type,
            "title": rec["title"], "url": SITE + urllib.parse.quote(rec["url"]),
            "locked": "/content/dam/secure/" in rec["url"], "file": fname}


def pick(docs: list[dict]) -> dict:
    """Several files for one (paper, doc type): prefer unlocked, a revised mark
    scheme (rms) over msc, then the longest-dated (latest) filename."""
    def score(d):
        f = d["file"].lower()
        return (not d["locked"], "rms" in f, "_" not in f, f)
    return max(docs, key=score)


def catalogue() -> list[dict]:
    recs = fetch_records()
    docs = collections.defaultdict(list)
    for r in recs:
        c = classify(r)
        if c:
            docs[(c["paper_id"], c["doc_type"])].append(c)
    out = []
    for (pid, dt), group in sorted(docs.items()):
        best = dict(pick(group))
        best["alternates"] = sorted(d["url"] for d in group if d is not best and d["url"] != best["url"])
        out.append(best)
    return out


def download(entries: list[dict]) -> None:
    for i, e in enumerate(entries):
        if e["locked"]:
            continue
        d = RAW / e["qualification"] / e["sitting"]
        d.mkdir(parents=True, exist_ok=True)
        pdf = d / f"{e['paper_id']}_{e['doc_type']}.pdf"
        e["local_pdf"] = str(pdf.relative_to(ROOT))
        kind = ""
        # Pearson sometimes lists a dead link next to a working copy under another filename:
        # try the chosen URL, then each alternate, until one really is a PDF.
        for url in [e["url"]] + e.get("alternates", []):
            if not pdf.exists() or pdf.stat().st_size == 0 or e.get("error"):
                subprocess.run(["curl", "-sfL", "--retry", "4", "--retry-all-errors", "-A", USER_AGENT,
                                "-o", str(pdf), url], check=False)
                time.sleep(0.5)
            kind = subprocess.run(["file", "-b", str(pdf)], capture_output=True, text=True).stdout if pdf.exists() else ""
            if kind.startswith("PDF"):
                if url != e["url"]:
                    e["alternates"] = [u for u in [e["url"]] + e["alternates"] if u != url]
                    e["url"] = url
                e.pop("error", None)
                break
            pdf.unlink(missing_ok=True)
            e["error"] = "not a PDF"
        if not kind.startswith("PDF"):
            e["error"] = f"not a PDF: {kind.strip()[:60]}"
            pdf.unlink(missing_ok=True)
            e.pop("local_pdf")
            print("  !!", e["paper_id"], e["doc_type"], e["error"])
            continue
        e["sha1"] = hashlib.sha1(pdf.read_bytes()).hexdigest()
        txt = pdf.with_suffix(".txt")
        if not txt.exists():
            mode = "-raw" if e["doc_type"] == "ER" else "-layout"
            subprocess.run(["pdftotext", mode, str(pdf), str(txt)], check=False)
        e["local_txt"] = str(txt.relative_to(ROOT))
        if i % 50 == 0:
            print(f"  {i}/{len(entries)}")


PAPER_ORDER = {"9MA0": 0, "IAL-2018": 1, "IAL-2013": 2, "GCE-2008": 3}


def report(entries: list[dict]) -> str:
    papers = collections.OrderedDict()
    for e in sorted(entries, key=lambda e: (PAPER_ORDER[e["qualification"]], e["unit"], e["variant"],
                                            e["sitting"][-4:], e["sitting"])):
        papers.setdefault(e["paper_id"], {})[e["doc_type"]] = e
    combined = {pid.rsplit("_", 1)[1]: p for pid, p in papers.items() if pid.startswith("GCE2008_ALL_")}

    def cell(pid, p, dt):
        e = p.get(dt)
        if not e and pid.startswith("GCE2008_") and not pid.startswith("GCE2008_ALL_"):
            c = combined.get(pid.rsplit("_", 1)[1], {}).get(dt)
            if c:
                return "✓c" if c.get("local_pdf") else "·c"
        if not e:
            return "—"
        if e["locked"]:
            return "🔒"
        if e.get("error"):
            return "✗"
        return "✓" if e.get("local_pdf") else "·"

    lines = ["# Pearson past-paper coverage", "",
             "Generated by `scripts/scrape_pearson.py --report` from Pearson's own past-papers index "
             "(qualifications.pearson.com). ✓ downloaded · `·` listed, not yet downloaded · ✓c covered by the "
             "series' combined all-units document (GCE 2005–2009) · — not listed by Pearson · 🔒 listed but "
             "secure (Edexcel Online login only: papers from roughly the last nine months) · ✗ download failed.", ""]
    summary = collections.Counter()
    gaps = []
    for pid, p in papers.items():
        if pid.startswith("GCE2008_ALL_"):
            continue
        e = next(iter(p.values()))
        key = (e["qualification"], e["unit_name"] + ("" if e["unit"].startswith("9MA0") else f" ({e['unit']})"))
        state = tuple(cell(pid, p, dt) for dt in ("QP", "MS", "ER"))
        ok = all(x.startswith("✓") for x in state)
        summary[key + ("papers",)] += 1
        summary[key + ("complete",)] += ok
        if not ok:
            gaps.append((pid, state))
    lines += ["## Summary", "", "| Qualification | Unit | Papers listed | QP + MS + ER all downloaded |",
              "|---|---|---|---|"]
    for (q, u, k), n in summary.items():
        if k == "papers":
            lines.append(f"| {q} | {u} | {n} | {summary[(q, u, 'complete')]} |")
    lines += ["", f"## Gaps ({len(gaps)} papers)", "", "| Paper | QP | MS | ER |", "|---|---|---|---|"]
    lines += [f"| {pid} | {' | '.join(st)} |" for pid, st in gaps]
    lines += ["", "## All papers", "", "| Paper | Series | QP | MS | ER |", "|---|---|---|---|---|"]
    for pid, p in papers.items():
        e = next(iter(p.values()))
        lines.append(f"| {pid} | {e['series']} | " + " | ".join(cell(pid, p, dt) for dt in ("QP", "MS", "ER")) + " |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", action="store_true")
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--only", help="regex on paper_id, e.g. '^P3_' (download subset)")
    a = ap.parse_args()
    if a.catalogue or a.download or not MANIFEST.exists():
        entries = catalogue()
        if MANIFEST.exists():                                  # keep download state
            old = {(e["paper_id"], e["doc_type"]): e for e in json.loads(MANIFEST.read_text())}
            for e in entries:
                o = old.get((e["paper_id"], e["doc_type"]))
                if o and o["url"] == e["url"]:
                    for k in ("local_pdf", "local_txt", "sha1", "error"):
                        if k in o:
                            e[k] = o[k]
        print(f"catalogued {len(entries)} documents, {len({e['paper_id'] for e in entries})} papers")
    else:
        entries = json.loads(MANIFEST.read_text())
    if a.download:
        todo = [e for e in entries if not a.only or re.search(a.only, e["paper_id"])]
        download(todo)
    RAW.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(entries, indent=1))
    if a.report or a.download:
        REPORT.write_text(report(entries))
        print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
