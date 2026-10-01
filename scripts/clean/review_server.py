"""Local review UI (gate G9) for generated clean-room items.

    .venv/bin/python scripts/clean/review_server.py                    # content/clean/items, port 8766
    .venv/bin/python scripts/clean/review_server.py --items DIR --port 8766 --no-browser

Serves scripts/clean/review.html on http://127.0.0.1:<port> (this machine only) and a small JSON API over the
item files (one item per <id>.json, format in docs/clean-room-pipeline.md, "Item format"):

    GET  /api/items         the review queue: one summary row per item, sorted by risk
    GET  /api/items?paper=P the queue for one mock paper, in question order
    GET  /api/item?id=ID    the full item, plus `scenes` (content/clean/scenes/<id>.json), `playbook`
                            (content/clean/playbooks/<question_type>.json) and `levels_gate` (gate_results.GL)
    GET  /api/mocks         the mock papers (content/clean/mocks/*.json, else assembled from the items' paper/q_num
                            fields and the mock blueprints) with each question's gate status and review decision
    GET  /api/mock?id=P     one paper in question order with each question's full item summary
    GET  /api/meta          reviewer name, reject reason codes, error-code definitions (our own taxonomy)
    POST /api/review        {id, decision: accept|edit|reject, reason_code, notes, minutes, edits?}

A review writes `review: {by, at, decision, reason_code, notes, minutes}` into the item file (atomically: temp
file, then rename). `by` is `git config user.name`. `edits` is a map {field: new text} over a fixed set of text
fields (see EDITABLE); the fields changed are recorded in review.edited_fields, their old text in
review.edited_before, and review.regate_needed is set, since edited text has not been through G1-G8. A previous
review is kept in review_history. Standard library only; reads only our own item files and content/.
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
PAGE = Path(__file__).resolve().parent / "review.html"
GATES = [f"G{i}" for i in range(1, 9)]
DECISIONS = ("accept", "edit", "reject")
REASON_CODES = ["maths-error", "ambiguous", "unfair-marks", "mark-scheme-wrong", "not-exam-style",
                "too-similar-to-real-question", "pitfall-wrong", "too-easy", "too-hard", "other"]
# Editable text fields, as dotted paths into the item. Anything else is refused.
EDITABLE = [re.compile(p) for p in (
    r"parts\.(\d+)\.text",
    r"parts\.(\d+)\.mark_scheme\.(\d+)\.(for|notes)",
    r"parts\.(\d+)\.alternatives\.(\d+)\.marks\.(\d+)\.(for|notes)",
    r"parts\.(\d+)\.hints\.(\d+)",
    r"pitfalls\.(\d+)\.text",
)]
LOCK = threading.Lock()
ITEMS_DIR = ROOT / "content" / "clean" / "items"
SCENES_DIR = ROOT / "content" / "clean" / "scenes"
PLAYBOOKS_DIR = ROOT / "content" / "clean" / "playbooks"
MOCKS_DIR = ROOT / "content" / "clean" / "mocks"
MINUTES_PER_MARK = 1.2  # as chatbot/mock.py: 9MA0 is 100 marks in 120 minutes


def reviewer() -> str:
    try:
        return subprocess.run(["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True,
                              timeout=5).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


REVIEWER = reviewer()


def blueprint_bands() -> dict:
    """blueprint id -> band, from our own blueprints (ids, codes and numbers only)."""
    bands = {}
    for f in (ROOT / "content" / "blueprints").glob("*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                try:
                    bp = json.loads(line)
                except json.JSONDecodeError:
                    continue
                bands[bp.get("id")] = bp.get("band")
    return bands


BANDS = blueprint_bands()


def error_codes() -> dict:
    p = ROOT / "content" / "error_codes.json"
    try:
        return {c["id"]: c.get("definition", "") for c in json.loads(p.read_text())["codes"]}
    except (OSError, ValueError, KeyError):
        return {}


def item_files() -> dict:
    """item id -> path, for every readable item file in ITEMS_DIR."""
    out = {}
    for f in sorted(ITEMS_DIR.glob("*.json")):
        try:
            item = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(item, dict) and isinstance(item.get("parts"), list):
            out[str(item.get("id") or f.stem)] = f
    return out


def load_items() -> dict:
    """item id -> item, for every readable item file (reads each file once)."""
    out = {}
    for iid, path in item_files().items():
        try:
            out[iid] = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
    return out


def read_json(path: Path):
    """The parsed file, or None if it is missing or not (yet) valid JSON (a concurrent run may be writing it)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def scenes_for(iid: str):
    return read_json(SCENES_DIR / f"{iid}.json") if re.fullmatch(r"[\w.-]+", iid or "") else None


def playbook_for(qtype) -> dict | None:
    if not isinstance(qtype, str) or not re.fullmatch(r"[\w.-]+", qtype):
        return None
    pb = read_json(PLAYBOOKS_DIR / f"{qtype}.json")
    return pb if isinstance(pb, dict) else None


def full_item(item: dict) -> dict:
    """The item as stored, plus the learn-layer pieces that live beside it."""
    gr = item.get("gate_results") or {}
    return {**item, "scenes": scenes_for(str(item.get("id") or "")), "playbook": playbook_for(item.get("question_type")),
            "levels_gate": gr.get("GL") if isinstance(gr.get("GL"), dict) else None}


def gates_passed(item: dict) -> bool:
    gr = item.get("gate_results") or {}
    return all(isinstance(gr.get(g), dict) and bool(gr[g].get("pass")) for g in GATES)


def mock_blueprints() -> dict:
    """paper id -> [{q_num, blueprint_id, marks, question_type}] from content/blueprints/mocks.jsonl (our own plan)."""
    out = {}
    f = ROOT / "content" / "blueprints" / "mocks.jsonl"
    try:
        lines = f.read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        if not line.strip():
            continue
        try:
            bp = json.loads(line)
        except json.JSONDecodeError:
            continue
        paper = bp.get("mock") or bp.get("paper")
        if paper:
            out.setdefault(str(paper), []).append({"q_num": bp.get("q_num"), "blueprint_id": bp.get("id"),
                                                  "marks": bp.get("total_marks"), "question_type": bp.get("question_type")})
    return out


def mock_papers(items: dict | None = None) -> list[dict]:
    """The mock papers with each question's item status. Papers come from content/clean/mocks/*.json; a paper id seen
    only in the items' `paper` field or the mock blueprints is assembled from those (question order by q_num)."""
    items = load_items() if items is None else items
    by_id = {iid: summary(it) for iid, it in items.items()}
    by_paper_q = {}
    for iid, it in items.items():
        if it.get("paper") is not None:
            by_paper_q.setdefault(str(it["paper"]), {}).setdefault(str(it.get("q_num")), iid)
    by_bp = {str(it.get("blueprint_id")): iid for iid, it in items.items() if it.get("blueprint_id")}
    planned = mock_blueprints()

    def question(q: dict, paper_id: str) -> dict:
        iid = q.get("item_id") or by_paper_q.get(paper_id, {}).get(str(q.get("q_num"))) or by_bp.get(str(q.get("blueprint_id")))
        row = by_id.get(str(iid)) if iid else None
        it = items.get(str(iid)) if iid else None
        return {"q_num": q.get("q_num"), "item_id": iid, "blueprint_id": q.get("blueprint_id") or (it or {}).get("blueprint_id"),
                "marks": q.get("marks") if q.get("marks") is not None else (row or {}).get("total_marks"),
                "question_type": (it or {}).get("question_type") or q.get("question_type"),
                "generated": it is not None, "gates_passed": gates_passed(it) if it else bool(q.get("gates_passed", False)),
                "gates": (row or {}).get("gates"), "risk": (row or {}).get("risk"), "risk_reason": (row or {}).get("risk_reason"),
                "decision": (row or {}).get("decision"), "reason_code": (row or {}).get("reason_code")}

    def finish(paper: dict) -> dict:
        qs = sorted(paper["questions"], key=lambda q: (q.get("q_num") is None, q.get("q_num") or 0, str(q.get("item_id"))))
        paper["questions"] = qs
        declared = paper.get("marks")
        marks = declared if isinstance(declared, (int, float)) else sum(q.get("marks") or 0 for q in qs)
        paper["marks"] = marks
        if not paper.get("minutes"):
            paper["minutes"] = int(round(marks * MINUTES_PER_MARK))
        paper["counts"] = {"questions": len(qs), "generated": sum(1 for q in qs if q["generated"]),
                           "gate_passed": sum(1 for q in qs if q["gates_passed"]),
                           "accepted": sum(1 for q in qs if q["decision"] == "accept"),
                           "reviewed": sum(1 for q in qs if q["decision"]),
                           "marks_generated": sum(q.get("marks") or 0 for q in qs if q["generated"])}
        return paper

    papers, seen = [], set()
    for f in sorted(MOCKS_DIR.glob("*.json")) if MOCKS_DIR.is_dir() else []:
        d = read_json(f)
        if not isinstance(d, dict) or not isinstance(d.get("questions"), list):
            continue
        pid = str(d.get("id") or f.stem)
        seen.add(pid)
        papers.append(finish({"id": pid, "title": d.get("title") or pid, "marks": d.get("marks"), "minutes": d.get("minutes"),
                              "source": "file", "questions": [question(q, pid) for q in d["questions"] if isinstance(q, dict)]}))
    for pid in sorted(set(planned) | set(by_paper_q)):
        if pid in seen:
            continue
        qs = {str(q.get("q_num")): dict(q) for q in planned.get(pid, [])}
        for qn, iid in by_paper_q.get(pid, {}).items():
            qs.setdefault(qn, {"q_num": items[iid].get("q_num")})["item_id"] = iid
        papers.append(finish({"id": pid, "title": pid, "marks": None, "minutes": None,
                              "source": "blueprints+items" if pid in planned else "items",
                              "questions": [question(q, pid) for q in qs.values()]}))
    return papers


def summary(item: dict) -> dict:
    gr = item.get("gate_results") or {}
    gates = {g: (bool(gr[g].get("pass")) if isinstance(gr.get(g), dict) and "pass" in gr[g] else None) for g in GATES}
    g3, g4, g7 = gr.get("G3") or {}, gr.get("G4") or {}, gr.get("G7") or {}
    g3_dis = len(g3.get("errors") or []) if g3 and not g3.get("pass") else 0
    g4_dis = (g4.get("n_responses", 0) - len(g4.get("agreed") or [])) if g4 else 0
    if g4 and not g4.get("pass"):
        g4_dis = max(g4_dis, 1)
    g7_flag = bool(g7.get("flag"))
    g3_flags = len(g3.get("flags") or [])  # the solver's "minor" problems: worth a look, not a fail
    if g7_flag or gates["G7"] is False:
        risk, why = 0, "G7 failed" if gates["G7"] is False else "G7 flagged"
    elif g3_dis or g4_dis or g3_flags:
        risk, why = 1, " + ".join(s for s in (g3_dis and "G3 disagrees", g3_flags and not g3_dis and "G3 flagged",
                                              g4_dis and "G4 disagrees") if s)
    elif False in gates.values():
        risk, why = 2, "failed " + ", ".join(g for g, v in gates.items() if v is False)
    else:
        risk, why = 3, "all passed" if all(v for v in gates.values()) else "not fully gated"
    review = item.get("review") or {}
    return {"id": item.get("id"), "kind": item.get("kind"), "component": item.get("component"),
            "band": item.get("band") or BANDS.get(item.get("blueprint_id")), "tier": item.get("tier"),
            "question_type": item.get("question_type"),
            "total_marks": sum(p.get("marks") or 0 for p in item.get("parts") or []),
            "n_parts": len(item.get("parts") or []), "gates": gates,
            "gate_flags": {g: bool((gr.get(g) or {}).get("flag")) for g in GATES if isinstance(gr.get(g), dict)},
            "flags": {"g7_flag": g7_flag, "g7_flags": g7.get("flags") or [], "g3_disagreements": g3_dis,
                      "g3_flags": g3_flags, "g4_disagreements": g4_dis},
            "risk": risk, "risk_reason": why, "decision": review.get("decision"),
            "reason_code": review.get("reason_code"), "reviewed_by": review.get("by"),
            "paper": item.get("paper"), "q_num": item.get("q_num"),
            "levels_gate": (bool(gr["GL"].get("pass")) if isinstance(gr.get("GL"), dict) and "pass" in gr["GL"] else None)}


def _resolve(item: dict, field: str):
    """(container, key) for an editable dotted path, or raise ValueError."""
    if not any(p.fullmatch(field) for p in EDITABLE):
        raise ValueError(f"field not editable: {field}")
    keys = [int(k) if k.isdigit() else k for k in field.split(".")]
    obj = item
    for k in keys[:-1]:
        try:
            obj = obj[k]
        except (KeyError, IndexError, TypeError):
            raise ValueError(f"no such field: {field}") from None
    last = keys[-1]
    if isinstance(obj, list):
        if not isinstance(last, int) or last >= len(obj):
            raise ValueError(f"no such field: {field}")
    elif not isinstance(obj, dict) or (last not in obj and last != "notes"):  # a mark's notes may be new
        raise ValueError(f"no such field: {field}")
    return obj, last


def apply_edits(item: dict, edits) -> tuple[list, dict]:
    if isinstance(edits, list):
        edits = {e.get("field"): e.get("value") for e in edits if isinstance(e, dict)}
    if not isinstance(edits, dict):
        raise ValueError("edits must be a map {field: text}")
    plan = []
    for field, value in edits.items():
        if not isinstance(field, str) or not isinstance(value, str):
            raise ValueError(f"edit {field!r}: the value must be text")
        obj, key = _resolve(item, field)
        before = obj[key] if (isinstance(obj, list) or key in obj) else None
        if before != value:
            plan.append((obj, key, field, before, value))
    for obj, key, _, _, value in plan:  # validate everything first, then apply
        obj[key] = value
    return [f for _, _, f, _, _ in plan], {f: b for _, _, f, b, _ in plan}


def write_atomic(path: Path, item: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def save_review(data: dict) -> dict:
    iid, decision = str(data.get("id") or ""), data.get("decision")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {', '.join(DECISIONS)}")
    reason = data.get("reason_code") or None
    if reason is not None and reason not in REASON_CODES:
        raise ValueError(f"unknown reason_code {reason!r}")
    if decision == "reject" and not reason:
        raise ValueError("a reject needs a reason_code")
    try:
        minutes = round(float(data.get("minutes") or 0), 2)
    except (TypeError, ValueError):
        raise ValueError("minutes must be a number") from None
    notes = data.get("notes") or ""
    if not isinstance(notes, str):
        raise ValueError("notes must be text")
    edits = data.get("edits")
    if edits and decision != "edit":
        raise ValueError("edits need decision 'edit'")
    with LOCK:
        path = item_files().get(iid)
        if path is None:
            raise LookupError(f"no item {iid!r}")
        item = json.loads(path.read_text())
        edited, before = apply_edits(item, edits) if edits else ([], {})
        old = item.get("review") or {}
        if old.get("decision"):
            item.setdefault("review_history", []).append(old)
        review = {"by": REVIEWER, "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "decision": decision,
                  "reason_code": reason, "notes": notes.strip() or None, "minutes": minutes}
        if edited:
            review.update(edited_fields=edited, edited_before=before, regate_needed=True)
        item["review"] = review
        write_atomic(path, item)
    return {"ok": True, "review": review, "summary": summary(item)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html", "/review.html"):
            return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/meta":
            return self._json(200, {"reviewer": REVIEWER, "reason_codes": REASON_CODES, "gates": GATES,
                                    "error_codes": error_codes(), "items_dir": str(ITEMS_DIR)})
        if url.path == "/api/items":
            paper = parse_qs(url.query).get("paper", [""])[0]
            items = load_items()
            if paper:  # one mock paper's questions, in question order (only those generated so far)
                papers = [p for p in mock_papers(items) if p["id"] == paper]
                ids = [q["item_id"] for q in (papers[0]["questions"] if papers else []) if q.get("item_id") in items]
                rows = [summary(items[iid]) for iid in ids]
                return self._json(200, {"items": rows, "paper": papers[0] if papers else None})
            rows = [summary(it) for it in items.values()]
            rows.sort(key=lambda r: (r["risk"], str(r["id"])))
            return self._json(200, {"items": rows})
        if url.path == "/api/item":
            iid = parse_qs(url.query).get("id", [""])[0]
            path = item_files().get(iid)
            if path is None:
                return self._json(404, {"error": f"no item {iid!r}"})
            return self._json(200, full_item(json.loads(path.read_text())))
        if url.path == "/api/mocks":
            return self._json(200, {"papers": mock_papers(), "mocks_dir": str(MOCKS_DIR)})
        if url.path == "/api/mock":
            pid = parse_qs(url.query).get("id", [""])[0]
            items = load_items()
            papers = [p for p in mock_papers(items) if p["id"] == pid]
            if not papers:
                return self._json(404, {"error": f"no mock paper {pid!r}"})
            paper = papers[0]
            for q in paper["questions"]:
                it = items.get(str(q.get("item_id"))) if q.get("item_id") else None
                q["item"] = None if it is None else {**summary(it), "stem": it.get("stem"),
                                                     "parts": [{"label": p.get("label"), "marks": p.get("marks"), "text": p.get("text")}
                                                               for p in it.get("parts") or []]}
            return self._json(200, paper)
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/review":
            return self._send(404, b"not found", "text/plain")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("body must be a JSON object")
            return self._json(200, save_review(data))
        except LookupError as e:
            return self._json(404, {"error": str(e)})
        except ValueError as e:  # includes bad JSON
            return self._json(400, {"error": str(e)})


def main() -> None:
    global ITEMS_DIR
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_DIR), help="folder of item files (default content/clean/items)")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    ITEMS_DIR = Path(args.items).resolve()
    if not ITEMS_DIR.is_dir():
        raise SystemExit(f"no such folder: {ITEMS_DIR}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Review UI for {ITEMS_DIR} ({len(item_files())} items, reviewer {REVIEWER}) at {url}\n"
          "Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
