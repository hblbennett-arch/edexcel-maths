"""Local web UI for testing the tutor, with LaTeX rendered by KaTeX.

    .venv/bin/python -m chatbot.web              # live (Claude via the configured backend)
    .venv/bin/python -m chatbot.web --offline    # no model: official mark scheme step by step
    .venv/bin/python -m chatbot.web --port 8765

Serves chatbot/static/index.html on http://127.0.0.1:<port> (this machine only) and a
small JSON API over chatbot/controller.py, so the browser and the terminal chat behave
the same. Standard library only; a testing harness, not the eventual product UI.
"""
import json
import os
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import config, db, events, examiner, learn, marks, profile, working
from .controller import Conversation

STATIC = Path(__file__).resolve().parent / "static"
MODE = "offline" if "--offline" in sys.argv else "dry-run" if "--dry-run" in sys.argv else "live"
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8765
SESSIONS: dict[str, Conversation] = {}
LOCK = threading.Lock()


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
        if url.path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path in ("/examiner", "/examiner.html"):
            return self._send(200, (STATIC / "examiner.html").read_bytes(), "text/html; charset=utf-8")
        if url.path.startswith("/api/examiner/"):
            return self._examiner_get(url.path, parse_qs(url.query))
        if url.path in ("/mark", "/mark.html"):
            return self._send(200, (STATIC / "mark.html").read_bytes(), "text/html; charset=utf-8")
        if url.path.startswith("/api/mark/"):
            return self._mark_get(url.path, parse_qs(url.query))
        if url.path in ("/learn", "/learn.html"):
            return self._send(200, (STATIC / "learn.html").read_bytes(), "text/html; charset=utf-8")
        if url.path in ("/playbooks", "/playbooks.html"):
            return self._send(200, (STATIC / "playbooks.html").read_bytes(), "text/html; charset=utf-8")
        if url.path.startswith("/api/learn/") or url.path in ("/api/playbooks", "/api/playbook"):
            return self._learn_get(url.path, parse_qs(url.query))
        if url.path in ("/mock", "/mock.html") or url.path.startswith("/api/mock/"):
            return self._mock("GET", url.path, parse_qs(url.query), None)
        if url.path in ("/profile", "/profile.html") or url.path.startswith("/api/profile"):
            return self._profile_get(url.path, parse_qs(url.query))
        # ---- Front door (/start) and "How marks are awarded" (/marks): static pages plus the board profile's glossary ----
        if url.path in ("/start", "/start.html"):
            return self._send(200, (STATIC / "start.html").read_bytes(), "text/html; charset=utf-8")
        if url.path in ("/marks", "/marks.html"):
            return self._send(200, (STATIC / "marks.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/marks/glossary":
            b = marks.profile()
            return self._json(200, {"board": b.qualification, "glossary": marks.glossary(b), "bald_answer_policy": b.bald_answer_policy,
                                    "paper_structure": b.paper_structure, "disclaimer": b.disclaimer})
        if url.path.startswith("/static/"):
            return self._static(url.path[len("/static/"):])
        if url.path == "/api/info":
            return self._json(200, {"mode": MODE, "model": config.MODEL, "backend": config.BACKEND,
                                    "available": MODE != "live" or config.has_credentials()})
        if url.path == "/api/figure":
            q = parse_qs(url.query)
            qid, page = q.get("qid", [""])[0], q.get("page", [""])[0]
            row = db.one("SELECT figure_pages FROM questions WHERE id = ?", (qid,))
            if not row or not page.isdigit() or int(page) not in json.loads(row["figure_pages"] or "[]"):
                return self._send(404, b"not found", "text/plain")
            sys.path.insert(0, str(config.ROOT / "scripts"))
            import render_figure
            for p in render_figure.render(render_figure.load_question(qid)):
                if p.stem.endswith(f"_p{page}"):
                    return self._send(200, p.read_bytes(), "image/png")
            return self._send(404, b"not found", "text/plain")
        self._send(404, b"not found", "text/plain")

    # ---- "Be the examiner" (chatbot/examiner.py): deterministic, no model, no names stored ----
    def _examiner_get(self, path: str, q: dict) -> None:
        user = (q.get("user") or [""])[0].strip()[:64]
        if path == "/api/examiner/glossary":
            b = marks.profile()
            return self._json(200, {"board": b.qualification, "glossary": marks.glossary(b), "disclaimer": b.disclaimer})
        if path == "/api/examiner/next":
            exs = examiner.all_exercises()
            done = {k for k in (q.get("done") or [""])[0].split(",") if k}
            ex = examiner.pick_next(exs, done, (q.get("kind") or [None])[0])
            return self._json(200, {"exercise": examiner.public_view(ex) if ex else None,
                                    "remaining": len([e for e in exs if e["key"] not in done]), "total": len(exs)})
        if path == "/api/examiner/profile":
            if not user:
                return self._json(400, {"error": "user required"})
            return self._json(200, events.leakage_profile(user))
        self._send(404, b"not found", "text/plain")

    def _examiner_submit(self, data: dict) -> None:
        user = str(data.get("user") or "").strip()[:64]
        ex = examiner.find(str(data.get("item_id") or ""), str(data.get("script_id") or ""))
        if not user or not ex:
            return self._json(400, {"error": "user, item_id and script_id required"})
        try:
            fb = examiner.reveal(ex, data.get("judgements"))
            examiner.record(user, ex, data.get("judgements"))
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        self._json(200, {"reveal": fb, "examiner_accuracy": events.leakage_profile(user)["examiner_accuracy"]})

    # ---- Mark-leakage profile (chatbot/profile.py): GET /profile, /api/profile?user=, /api/profile/exercise?key= ----
    def _profile_get(self, path: str, q: dict) -> None:
        if path in ("/profile", "/profile.html"):
            return self._send(200, (STATIC / "profile.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/api/profile":
            user = (q.get("user") or [""])[0].strip()[:64]
            return self._json(200, profile.view(user)) if user else self._json(400, {"error": "user required"})
        if path == "/api/profile/exercise":
            ex = profile.exercise((q.get("key") or [""])[0].strip()[:200])
            return self._json(200, {"exercise": ex}) if ex else self._json(404, {"error": "no such exercise"})
        self._send(404, b"not found", "text/plain")

    # ---- "Learn" viewer and playbooks (chatbot/learn.py): deterministic, no model ----
    def _learn_get(self, path: str, q: dict) -> None:
        if path == "/api/learn/catalogue":
            return self._json(200, learn.catalogue())
        if path == "/api/learn/item":
            item_id = (q.get("id") or [""])[0].strip()
            view = learn.item_view(item_id) if item_id else None
            return self._json(200, view) if view else self._json(404, {"error": "no such item (or it has not passed the gates)"})
        if path == "/api/playbooks":
            b = marks.profile()
            return self._json(200, {"playbooks": learn.playbook_index(), "board": b.qualification, "disclaimer": b.disclaimer})
        if path == "/api/playbook":
            type_id = (q.get("id") or [""])[0].strip()
            pb = learn.playbook(type_id) if type_id else None
            return self._json(200, pb) if pb else self._json(404, {"error": "no such playbook"})
        self._send(404, b"not found", "text/plain")

    STATIC_TYPES = {".js": "application/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                    ".html": "text/html; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml", ".json": "application/json"}

    def _static(self, name: str) -> None:
        """Files in chatbot/static only: one path segment, no traversal, known extensions."""
        if not name or "/" in name or "\\" in name or name.startswith(".") or ".." in name:
            return self._send(404, b"not found", "text/plain")
        target = (STATIC / name)
        try:
            resolved = target.resolve(strict=True)
        except (OSError, RuntimeError):
            return self._send(404, b"not found", "text/plain")
        if resolved.parent != STATIC.resolve() or not resolved.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = self.STATIC_TYPES.get(resolved.suffix.lower())
        if not ctype:
            return self._send(404, b"not found", "text/plain")
        self._send(200, resolved.read_bytes(), ctype)

    # ---- "Mark my working, explained" (chatbot/working.py -> chatbot/marker.py): one model call per submit ----
    def _mark_get(self, path: str, q: dict) -> None:
        user = (q.get("user") or [""])[0].strip()[:64]
        if path == "/api/mark/catalogue":
            b = marks.profile()
            return self._json(200, {"items": working.catalogue(), "board": b.qualification, "disclaimer": b.disclaimer,
                                    "error_code_definitions": working.error_code_definitions()})
        if path == "/api/mark/profile":
            if not user:
                return self._json(400, {"error": "user required"})
            return self._json(200, working.profile(user))
        self._send(404, b"not found", "text/plain")

    def _mark_submit(self, data: dict) -> None:
        user = str(data.get("user") or "").strip()[:64]
        item_id, text = str(data.get("item_id") or ""), str(data.get("text") or "")
        if not user or not item_id or not text.strip():
            return self._json(400, {"error": "user, item_id and text required"})
        part = data.get("part_label")
        kw = {}
        if data.get("transcript_confirmed") is not None:  # photo flow: the student confirmed (maybe edited) the transcript
            kw = {"transcript_confirmed": bool(data["transcript_confirmed"]), "source": "image"}
        out = working.submit(user, item_id, None if part in (None, "", "all") else str(part), text[:20000], **kw)
        self._json(200 if "error" not in out else 502 if "detail" in out else 400, out)

    def _mark_photo(self) -> None:
        """POST /api/mark/photo: a photo of the working -> transcript for the student to confirm (no marking yet).
        Body is either multipart/form-data with a file field `image`, or JSON {"image_base64", "ext"}. 6 MB cap."""
        import base64
        import re
        from email.parser import BytesParser
        from email.policy import HTTP
        length = int(self.headers.get("Content-Length") or 0)
        if length > working.MAX_IMAGE_BYTES * 4 // 3 + 4096:
            self.rfile.read(min(length, 1 << 16))
            return self._json(413, {"error": "That photo is too large. Please keep it under 6 MB."})
        raw = self.rfile.read(length)
        ctype = self.headers.get("Content-Type") or ""
        data, ext = b"", ""
        if ctype.startswith("multipart/form-data"):
            msg = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + ctype.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw)
            for part in msg.iter_parts():
                if part.get_param("name", header="content-disposition") == "image":
                    data = part.get_payload(decode=True) or b""
                    fname = part.get_filename() or ""
                    ext = (Path(fname).suffix or "." + (part.get_content_subtype() or "")).lstrip(".")
                    break
        else:
            try:
                body = json.loads(raw or b"{}")
                b64 = str(body.get("image_base64") or "")
                m = re.match(r"data:image/(\w+);base64,", b64)
                ext = str(body.get("ext") or (m.group(1) if m else ""))
                data = base64.b64decode(b64.split(",", 1)[1] if m else b64, validate=False) if b64 else b""
            except (json.JSONDecodeError, ValueError, AttributeError):
                return self._json(400, {"error": "bad request: send multipart `image` or JSON {image_base64, ext}"})
        out = working.transcribe_upload(data, ext)
        self._json(200 if "error" not in out else 502 if "detail" in out else 400, out)

    # ---- Timed mocks (chatbot/mock.py): GET /mock, /api/mock/papers, /api/mock/paper?id=; POST /api/mock/submit ----
    def _mock(self, method: str, path: str, q: dict, data: dict | None) -> None:
        from . import mock
        if method == "GET" and path in ("/mock", "/mock.html"):
            return self._send(200, (STATIC / "mock.html").read_bytes(), "text/html; charset=utf-8")
        if method == "GET" and path == "/api/mock/papers":
            return self._json(200, {"papers": mock.papers(), "disclaimer": marks.profile().disclaimer})
        if method == "GET" and path == "/api/mock/paper":
            p = mock.paper((q.get("id") or [""])[0].strip())
            return self._json(200, p) if p else self._json(404, {"error": "no such paper"})
        if method == "POST" and path == "/api/mock/submit":
            data = data or {}
            user = str(data.get("user") or "").strip()[:64]
            paper_id = str(data.get("paper_id") or "").strip()
            if not user or not paper_id:
                return self._json(400, {"error": "user and paper_id required"})
            out = mock.submit(user, paper_id, data.get("answers") or {}, data.get("elapsed_seconds") or 0)
            return self._json(200 if "error" not in out else 400, out)
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/mark/photo":
            return self._mark_photo()
        if path not in ("/api/message", "/api/resume", "/api/examiner/submit", "/api/mark/submit", "/api/mock/submit"):
            return self._send(404, b"not found", "text/plain")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad json"})
        if path == "/api/mock/submit":
            return self._mock("POST", path, {}, data if isinstance(data, dict) else {})
        if path == "/api/examiner/submit":
            return self._examiner_submit(data if isinstance(data, dict) else {})
        if path == "/api/mark/submit":
            return self._mark_submit(data if isinstance(data, dict) else {})
        sid = data.get("session") or str(uuid.uuid4())
        with LOCK:
            # defer_explanations: an opened question comes back at once with a "pending" message; the
            # page then calls /api/resume, which runs the slow model call and returns the explanation.
            conv = SESSIONS.setdefault(sid, Conversation(mode=MODE, defer_explanations=True))
        try:
            messages = conv.resume() if path == "/api/resume" else conv.handle(str(data.get("text", "")))
        except RuntimeError as e:
            messages = [{"type": "warning", "md": str(e)}]
        except Exception as e:  # show unexpected errors in the page instead of hanging it
            messages = [{"type": "warning", "md": f"Something went wrong: {type(e).__name__}: {e}"}]
        self._json(200, {"session": sid, "messages": messages})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Tutor UI ({MODE} mode, model {config.MODEL}, backend {config.BACKEND}) at {url}\n"
          "Press Ctrl+C to stop.", flush=True)
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        sys.stdout.flush()
        os._exit(0)  # onnxruntime can abort during interpreter teardown


if __name__ == "__main__":
    main()
