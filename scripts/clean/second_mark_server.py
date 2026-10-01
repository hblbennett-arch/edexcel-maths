"""Blind hand-marking UI: a human second-marks the scripted answers that marker v2 has already marked, so that an
independent per-mark agreement figure exists (docs/clean-room-pipeline.md "Marker v2"; the current figure was
measured against the G4 marker's own reference, so it is not independent).

    .venv/bin/python scripts/clean/second_mark_server.py                # port 8767, opens the browser
    .venv/bin/python scripts/clean/second_mark_server.py --no-browser --port 8767

Serves scripts/clean/second_mark.html on http://127.0.0.1:<port> (this machine only) and a JSON API:

    GET  /api/meta                    marker name, queue size, output path
    GET  /api/queue                   the queue: one row per (item, script) with a marker v2 vector, blind
                                      (item_id, script_id, done) in marking order
    GET  /api/script?item=I&script=S  the blind payload: question text, scheme lines, the script. No vectors.
    GET  /api/progress                scripts marked, per-mark agreement human vs v2 and human vs G4 reference
    POST /api/submit                  {item_id, script_id, human: {part: [bools]}, seconds}
                                      -> appends one JSON line per part to data/clean_private/second_marking.jsonl
                                         and returns the comparison (human, v2, reference, v2 reason per mark)

Queue order: scripts where marker v2 disagreed with the G4 reference first, then the remaining pitfall scripts,
then everything else, each group shuffled with a fixed seed and interleaved across items so consecutive scripts
come from different questions. The v2 vectors come from logs/marker_eval_cache.json ("v2"); the reference is the
item's G4 record (`agreed` ids -> the response's designed vector, `consistent[id]` -> that vector). Standard
library only; no model calls.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chatbot import marks  # noqa: E402

PAGE = Path(__file__).resolve().parent / "second_mark.html"
ITEMS_DIR = ROOT / "content" / "clean" / "items"
CACHE = ROOT / "logs" / "marker_eval_cache.json"
OUT = ROOT / "data" / "clean_private" / "second_marking.jsonl"
CACHE_KEY = "v2"
SEED = 20260930
LOCK = threading.Lock()
# Keys that must never appear in a blind payload (checked by eval/second_mark_selftest.py)
FORBIDDEN_BLIND_KEYS = {"v2", "reference", "designed", "consistent", "agreed", "awarded", "awarded_second",
                        "decisions", "vectors", "error_code", "kind", "gate_results", "mismatched", "solution",
                        "pitfalls", "reasons"}


def marker_name() -> str:
    try:
        return subprocess.run(["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True,
                              timeout=5).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def part_key(label) -> str:
    return "-" if label in (None, "", "-") else str(label)


def load_item(item_id: str, items_dir: Path | None = None) -> dict | None:
    path = (items_dir or ITEMS_DIR) / f"{item_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_cache(cache: Path | None = None) -> dict:
    path = cache or CACHE
    if not path.exists():
        return {}
    return json.load(open(path)).get(CACHE_KEY, {})


def scheme_lines(item: dict) -> list[dict]:
    """The scheme as the human sees it: [{part, position, code, for, notes}] in marking order."""
    out = []
    for p in item.get("parts") or []:
        for i, m in enumerate(p.get("mark_scheme") or []):
            out.append({"part": part_key(p.get("label")), "position": i, "code": m.get("code"),
                        "for": m.get("for", ""), "notes": m.get("notes", "")})
    return out


def reference_vector(item: dict, script_id: str) -> dict | None:
    """{part: [codes]} from the G4 record, or None when the G4 markers never agreed a vector for this script."""
    g4 = (item.get("gate_results") or {}).get("G4") or {}
    resp = next((r for r in g4.get("responses") or [] if r.get("id") == script_id), None)
    if resp is None:
        return None
    if script_id in (g4.get("agreed") or []):
        return {part_key(d.get("part")): list(d.get("marks") or []) for d in resp.get("designed") or []}
    cons = (g4.get("consistent") or {}).get(script_id)
    if cons:
        return {part_key(d.get("part")): list(d.get("marks") or []) for d in cons}
    return None


def bools(codes: list[str]) -> list[bool]:
    return [bool(marks.try_parse(c) and marks.parse(c).awarded) for c in codes]


def v2_record(cache: dict, item_id: str, script_id: str) -> dict | None:
    """{vectors: {part: [codes]}, decisions: [...], seconds} for one script, or None."""
    rec = (cache.get(item_id) or {}).get(script_id)
    if not rec or not isinstance(rec.get("result"), dict) or not rec["result"].get("vectors"):
        return None
    res = rec["result"]
    return {"vectors": {part_key(k): list(v) for k, v in res["vectors"].items()},
            "decisions": res.get("decisions") or [], "seconds": rec.get("seconds")}


def vectors_disagree(a: dict | None, b: dict | None) -> bool:
    if a is None or b is None:
        return False
    for k in set(a) | set(b):
        if bools(a.get(k, [])) != bools(b.get(k, [])):
            return True
    return False


def build_queue(items_dir: Path | None = None, cache_path: Path | None = None, seed: int = SEED) -> list[dict]:
    """One row per (item, script) with a v2 vector. Internal rows carry `kind` and `priority`; strip with
    blind_row() before sending to the client."""
    cache = load_cache(cache_path)
    rows = []
    for item_id in sorted(cache):
        item = load_item(item_id, items_dir)
        if not item:
            continue
        g4 = (item.get("gate_results") or {}).get("G4") or {}
        responses = {r.get("id"): r for r in g4.get("responses") or []}
        for script_id in sorted(cache[item_id]):
            v2 = v2_record(cache, item_id, script_id)
            resp = responses.get(script_id)
            if v2 is None or resp is None:
                continue
            ref = reference_vector(item, script_id)
            disagree = vectors_disagree(v2["vectors"], ref)
            kind = resp.get("kind") or "unknown"
            priority = 0 if disagree else 1 if kind == "pitfall" else 2
            rows.append({"item_id": item_id, "script_id": script_id, "kind": kind, "priority": priority,
                         "v2_disagrees_with_reference": disagree, "has_reference": ref is not None,
                         "n_marks": sum(len(v) for v in v2["vectors"].values())})
    rng = random.Random(seed)
    ordered = []
    for pr in (0, 1, 2):
        group = [r for r in rows if r["priority"] == pr]
        rng.shuffle(group)
        # interleave across items: round-robin over per-item lists so neighbours differ in question
        by_item: dict[str, list] = {}
        for r in group:
            by_item.setdefault(r["item_id"], []).append(r)
        item_order = list(by_item)
        rng.shuffle(item_order)
        while item_order:
            for iid in list(item_order):
                ordered.append(by_item[iid].pop(0))
                if not by_item[iid]:
                    item_order.remove(iid)
    return ordered


def blind_row(row: dict, done: set) -> dict:
    return {"item_id": row["item_id"], "script_id": row["script_id"], "n_marks": row["n_marks"],
            "done": (row["item_id"], row["script_id"]) in done}


def blind_payload(item_id: str, script_id: str, items_dir: Path | None = None) -> dict:
    """What the marker sees before submitting: question, scheme lines, the script. Nothing about vectors."""
    item = load_item(item_id, items_dir)
    if not item:
        raise LookupError(f"no item {item_id!r}")
    g4 = (item.get("gate_results") or {}).get("G4") or {}
    resp = next((r for r in g4.get("responses") or [] if r.get("id") == script_id), None)
    if resp is None:
        raise LookupError(f"no script {script_id!r} on {item_id!r}")
    return {"item_id": item_id, "script_id": script_id, "stem": item.get("stem"),
            "parts": [{"part": part_key(p.get("label")), "label": p.get("label"), "marks": p.get("marks"),
                       "text": p.get("text"), "scheme": [{"code": m.get("code"), "for": m.get("for", ""),
                                                          "notes": m.get("notes", "")}
                                                         for m in p.get("mark_scheme") or []]}
                      for p in item.get("parts") or []],
            "work": resp.get("work", "")}


def read_log(out: Path | None = None) -> list[dict]:
    path = out or OUT
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def done_set(out: Path | None = None) -> set:
    return {(r.get("item_id"), r.get("script_id")) for r in read_log(out)}


def human_for(item_id: str, script_id: str, out: Path | None = None) -> dict:
    """{part: [bools]} from the latest submission per part."""
    got = {}
    for r in read_log(out):
        if r.get("item_id") == item_id and r.get("script_id") == script_id:
            got[part_key(r.get("part"))] = list(r.get("human") or [])
    return got


def comparison(item_id: str, script_id: str, human: dict, items_dir: Path | None = None,
               cache_path: Path | None = None) -> dict:
    """Per-mark table: human vs marker v2 vs G4 reference, with v2's reason and evidence where stored."""
    item = load_item(item_id, items_dir) or {}
    v2 = v2_record(load_cache(cache_path), item_id, script_id)
    ref = reference_vector(item, script_id)
    dec_by = {}
    for d in (v2 or {}).get("decisions") or []:
        dec_by[(part_key(d.get("part")), d.get("position"))] = d
    table = []
    for line in scheme_lines(item):
        k, i = line["part"], line["position"]
        h = human.get(k)
        v = bools(v2["vectors"].get(k, [])) if v2 else None
        r = bools(ref.get(k, [])) if ref else None
        d = dec_by.get((k, i))
        table.append({"part": k, "position": i, "code": line["code"], "for": line["for"],
                      "human": h[i] if h and i < len(h) else None,
                      "v2": v[i] if v and i < len(v) else None,
                      "reference": r[i] if r and i < len(r) else None,
                      "v2_reason": d.get("reason") if d else None,
                      "v2_evidence": d.get("evidence") if d else None,
                      "v2_confidence": d.get("confidence") if d else None,
                      "v2_stored": d is not None})
    g4 = (item.get("gate_results") or {}).get("G4") or {}
    resp = next((r for r in g4.get("responses") or [] if r.get("id") == script_id), {})
    return {"item_id": item_id, "script_id": script_id, "kind": resp.get("kind"), "error_code": resp.get("error_code"),
            "reference_available": ref is not None, "v2_available": v2 is not None, "marks": table}


def record_submission(data: dict, out: Path | None = None, items_dir: Path | None = None,
                      cache_path: Path | None = None, by: str | None = None) -> dict:
    """Validate {item_id, script_id, human: {part: [bools]}, seconds}, append one line per part, return the
    comparison. Raises LookupError / ValueError."""
    out = out or OUT
    item_id, script_id = str(data.get("item_id") or ""), str(data.get("script_id") or "")
    item = load_item(item_id, items_dir)
    if not item:
        raise LookupError(f"no item {item_id!r}")
    human = data.get("human")
    if not isinstance(human, dict):
        raise ValueError("human must be {part: [bools]}")
    expected = {}
    for line in scheme_lines(item):
        expected[line["part"]] = expected.get(line["part"], 0) + 1
    if set(human) != set(expected):
        raise ValueError(f"parts {sorted(human)} do not match the scheme's {sorted(expected)}")
    for k, v in human.items():
        if not isinstance(v, list) or len(v) != expected[k] or not all(isinstance(x, bool) for x in v):
            raise ValueError(f"part {k!r}: need {expected[k]} bools")
    seconds = data.get("seconds")
    seconds = float(seconds) if isinstance(seconds, (int, float)) else None
    at = datetime.now().isoformat(timespec="seconds")
    lines = [json.dumps({"at": at, "by": by or MARKER, "item_id": item_id, "script_id": script_id,
                         "part": None if k == "-" else k, "human": v, "seconds": seconds}) for k, v in human.items()]
    with LOCK:
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a") as f:
            f.write("\n".join(lines) + "\n")
    comp = comparison(item_id, script_id, {k: v for k, v in human.items()}, items_dir, cache_path)
    comp["progress"] = progress(out, items_dir, cache_path)
    return comp


def progress(out: Path | None = None, items_dir: Path | None = None, cache_path: Path | None = None) -> dict:
    """Scripts marked and running per-mark agreement, human vs v2 and human vs G4 reference."""
    rows = read_log(out)
    cache = load_cache(cache_path)
    scripts = {}
    for r in rows:
        scripts.setdefault((r.get("item_id"), r.get("script_id")), {})[part_key(r.get("part"))] = r.get("human") or []
    n_marks = agree_v2 = n_v2 = agree_ref = n_ref = 0
    items = {}
    for (iid, sid), human in scripts.items():
        if iid not in items:
            items[iid] = load_item(iid, items_dir) or {}
        v2 = v2_record(cache, iid, sid)
        ref = reference_vector(items[iid], sid)
        for k, h in human.items():
            n_marks += len(h)
            if v2 and k in v2["vectors"]:
                v = bools(v2["vectors"][k])
                for a, b in zip(h, v):
                    n_v2 += 1
                    agree_v2 += a == b
            if ref and k in ref:
                rv = bools(ref[k])
                for a, b in zip(h, rv):
                    n_ref += 1
                    agree_ref += a == b
    pct = lambda a, n: round(100.0 * a / n, 1) if n else None  # noqa: E731
    return {"scripts": len(scripts), "marks": n_marks, "vs_v2": {"agree": agree_v2, "n": n_v2, "pct": pct(agree_v2, n_v2)},
            "vs_reference": {"agree": agree_ref, "n": n_ref, "pct": pct(agree_ref, n_ref)}}


MARKER = marker_name()
QUEUE: list[dict] = []


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
        q = parse_qs(url.query)
        try:
            if url.path in ("/", "/index.html", "/second_mark.html"):
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/meta":
                return self._json(200, {"marker": MARKER, "queue_size": len(QUEUE), "out": str(OUT),
                                        "items_dir": str(ITEMS_DIR), "cache": str(CACHE)})
            if url.path == "/api/queue":
                done = done_set()
                return self._json(200, {"queue": [blind_row(r, done) for r in QUEUE]})
            if url.path == "/api/script":
                return self._json(200, blind_payload(q.get("item", [""])[0], q.get("script", [""])[0]))
            if url.path == "/api/progress":
                return self._json(200, progress())
            return self._send(404, b"not found", "text/plain")
        except LookupError as e:
            return self._json(404, {"error": str(e)})

    def do_POST(self):
        if urlparse(self.path).path != "/api/submit":
            return self._send(404, b"not found", "text/plain")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if not isinstance(data, dict):
                raise ValueError("body must be a JSON object")
            return self._json(200, record_submission(data))
        except LookupError as e:
            return self._json(404, {"error": str(e)})
        except ValueError as e:
            return self._json(400, {"error": str(e)})


def main() -> None:
    global ITEMS_DIR, CACHE, OUT, QUEUE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", default=str(ITEMS_DIR))
    ap.add_argument("--cache", default=str(CACHE), help="marker eval cache (default logs/marker_eval_cache.json)")
    ap.add_argument("--out", default=str(OUT), help="jsonl to append to (default data/clean_private/second_marking.jsonl)")
    ap.add_argument("--port", type=int, default=8767)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    ITEMS_DIR, CACHE, OUT = Path(args.items).resolve(), Path(args.cache).resolve(), Path(args.out).resolve()
    if not ITEMS_DIR.is_dir():
        raise SystemExit(f"no such folder: {ITEMS_DIR}")
    if not CACHE.exists():
        raise SystemExit(f"no marker eval cache at {CACHE}")
    QUEUE = build_queue()
    done = done_set()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Second marking: {len(QUEUE)} scripts ({sum(1 for r in QUEUE if (r['item_id'], r['script_id']) in done)} done), "
          f"marker {MARKER}, writing {OUT}\n{url}\nPress Ctrl+C to stop.", flush=True)
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
