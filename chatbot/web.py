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

from . import config, db
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

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/message", "/api/resume"):
            return self._send(404, b"not found", "text/plain")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad json"})
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
