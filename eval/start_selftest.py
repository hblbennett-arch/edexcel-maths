"""Self-test for the front door (/start) and "How marks are awarded" (/marks): the two static pages exist, link to the
six features and the glossary route, and their inline scripts parse (node --check).

    .venv/bin/python -m eval.start_selftest

No model calls, no network, no server start (the server smoke is a separate curl step).
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import marks, web  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


STATIC = web.STATIC
start = STATIC / "start.html"
marks_page = STATIC / "marks.html"
check(start.is_file(), f"missing {start}")
check(marks_page.is_file(), f"missing {marks_page}")
start_html = start.read_text() if start.is_file() else ""
marks_html = marks_page.read_text() if marks_page.is_file() else ""

# the six feature links, the glossary route and the marks page link on the front door
for href in ("/learn", "/examiner", "/mark", "/playbooks", "/mock", "/profile", "/marks"):
    check(f'href="{href}"' in start_html, f"start.html: no link to {href}")
check("Learn to write answers the way examiners mark them" in start_html, "start.html: positioning line missing")
check("Stop losing marks you already know how to get" in start_html, "start.html: second line missing")
check('PRODUCT_NAME = "[Product name]"' in start_html, "start.html: PRODUCT_NAME constant missing")
check("Every question and mark scheme here is our own." in start_html, "start.html: footer line missing")
check("/api/marks/glossary" in marks_html, "marks.html: does not call /api/marks/glossary")
check('href="/examiner"' in marks_html and 'href="/start"' in marks_html, "marks.html: links to /examiner and /start missing")
check("Lose the second M1 and" in marks_html and "the dM1 and A1* go with it" in marks_html, "marks.html: chain caption missing")
for key in ("M", "A", "B", "dM", "ddM", "ft", "cso", "cao", "awrt", "oe", "isw", "show_that", "dependency", "bald_answer"):
    check(f'"{key}"' in marks_html, f"marks.html: convention order lacks {key}")

# the routes exist in web.py
web_src = Path(web.__file__).read_text()
for route in ('"/start"', '"/marks"', '"/api/marks/glossary"', "marks.glossary("):
    check(route in web_src, f"web.py: {route} route missing")

# the glossary the route will serve: 14 conventions with the four texts each
b = marks.profile()
g = marks.glossary(b)
check(len(g) == 14, f"glossary has {len(g)} conventions (expected 14)")
for c in g:
    check(all(c.get(k) for k in ("key", "name", "short", "explain", "write_to_earn")), f"convention {c.get('key')} incomplete")
check(len(b.paper_structure.get("papers", [])) == 3, "paper_structure: expected three papers")
check(b.bald_answer_policy and b.disclaimer, "profile lacks bald_answer_policy or disclaimer")

# the inline scripts parse
node = shutil.which("node")
if not node:
    print("note: node not found, skipping script syntax check")
else:
    for page, html in (("start.html", start_html), ("marks.html", marks_html)):
        scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, flags=re.S)
        check(scripts, f"{page}: no inline script found")
        for i, body in enumerate(scripts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(body)
                tmp = f.name
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            check(r.returncode == 0, f"{page} script {i}: node --check failed: {r.stderr.strip()[:300]}")
            Path(tmp).unlink(missing_ok=True)

# the JS chain replica agrees with marks.chain() on the worked example
py_chain = marks.chain(["M1", "A1", "M1", "dM1", "A1*"])
check([c["depends_on"] for c in py_chain] == [[], [0], [], [2], [3]], f"marks.chain unexpected: {py_chain}")

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print(f"start_selftest OK: start.html {len(start_html)} bytes, marks.html {len(marks_html)} bytes, "
      f"{len(g)} conventions, {len(b.paper_structure['papers'])} papers, scripts parse")
