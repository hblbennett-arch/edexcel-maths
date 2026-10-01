"""Self-test for chatbot/learn.py and the /learn, /playbooks and /static routes in chatbot/web.py.

    .venv/bin/python -m eval.learn_selftest

No model calls, no network. Checks that item_view works for every gate-passed item (all parts, scheme lines,
standard steps), that every playbook resolves, that the catalogue counts match, and that the static route
refuses path traversal (using the handler's `_static` directly, without binding a port).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import examiner, learn  # noqa: E402

fails: list[str] = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


# ---- item views -----------------------------------------------------------------------------------------
items = examiner.load_items()
check(items, "no gate-passed items found")
n_levels = n_scenes = 0
with_levels, with_scenes = [], []
for it in items:
    v = learn.item_view(it["id"])
    check(v is not None, f"{it['id']}: item_view returned None")
    if not v:
        continue
    json.dumps(v)  # JSON-safe
    check(len(v["parts"]) == len(it["parts"]), f"{it['id']}: parts {len(v['parts'])} != {len(it['parts'])}")
    for p, src in zip(v["parts"], it["parts"]):
        check(len(p["mark_scheme"]) == len(src.get("mark_scheme") or []), f"{it['id']} part {p['label']}: scheme lines")
        check(all(m["code"] and m["for"] for m in p["mark_scheme"]), f"{it['id']} part {p['label']}: empty scheme line")
        check(all(isinstance(m["convention_short"], str) for m in p["mark_scheme"]), f"{it['id']}: convention_short")
        check(len(p["steps"]) == len(src.get("solution") or []), f"{it['id']} part {p['label']}: standard steps")
        check(p["steps"], f"{it['id']} part {p['label']}: no standard solution")
        if p["solution_levels"]:
            lv = p["solution_levels"]
            check(all(s["working"] for s in lv.get("brisk", [])), f"{it['id']}: brisk line without working")
            check(all(s["working"] and s["why"] for s in lv.get("every_step", [])), f"{it['id']}: every_step line without working/why")
            codes = {m["code"] for m in p["mark_scheme"]}
            for s in lv.get("brisk", []):
                check(all(c in codes for c in s["secures"]), f"{it['id']}: brisk secures {s['secures']} not in scheme")
    check(v["title"] and v["question_text"], f"{it['id']}: title/question text")
    check(isinstance(v["scenes"], list), f"{it['id']}: scenes not a list")
    check(v["disclaimer"], f"{it['id']}: disclaimer missing")
    if v["has_levels"]:
        n_levels += 1
        with_levels.append(it["id"])
    if v["scenes"]:
        n_scenes += 1
        with_scenes.append(it["id"])
        for s in v["scenes"]:
            check(s.get("elements") or s.get("steps"), f"{it['id']}: scene without elements/steps")
check(learn.item_view("no-such-item") is None, "item_view of a missing id should be None")
check(learn.item_view("") is None, "item_view('') should be None")

# ---- catalogue ------------------------------------------------------------------------------------------
cat = learn.catalogue()
flat = [e for c in cat["components"] for e in c["items"]]
check(cat["n_items"] == len(items) == len(flat), f"catalogue n_items {cat['n_items']} != {len(items)}")
check(cat["n_levels"] == n_levels, f"catalogue n_levels {cat['n_levels']} != {n_levels}")
check(cat["n_scenes"] == n_scenes, f"catalogue n_scenes {cat['n_scenes']} != {n_scenes}")
check({e["item_id"] for e in flat} == {it["id"] for it in items}, "catalogue ids differ from load_items")
check(all(e["title"] and e["marks"] > 0 for e in flat), "catalogue entry without title/marks")
by_comp = {}
for it in items:
    by_comp[it.get("component") or "other"] = by_comp.get(it.get("component") or "other", 0) + 1
check({c["component"]: len(c["items"]) for c in cat["components"]} == by_comp, "catalogue component counts")

# ---- playbooks ------------------------------------------------------------------------------------------
idx = learn.playbook_index()
n_files = len(list((ROOT / "content" / "clean" / "playbooks").glob("*.json")))
check(len(idx) == n_files, f"playbook_index has {len(idx)} entries, {n_files} files")
check(len(idx) == 73, f"expected 73 playbooks, found {len(idx)}")
check(len({p["id"] for p in idx}) == len(idx), "duplicate playbook ids")
for row in idx:
    check(all(k in row for k in ("id", "title", "topic", "component", "n_leaks", "has_items")), f"{row.get('id')}: index fields")
    pb = learn.playbook(row["id"])
    check(pb is not None, f"{row['id']}: playbook() returned None")
    if not pb:
        continue
    json.dumps(pb)
    check(pb["title"] and pb["what_it_asks"], f"{row['id']}: title/what_it_asks")
    check(len(pb["where_marks_leak"]) == row["n_leaks"], f"{row['id']}: n_leaks mismatch")
    check(all("definition" in l for l in pb["where_marks_leak"]), f"{row['id']}: leak without definition field")
    check(all(s["title"] for s in pb["skills"]), f"{row['id']}: skill without title")
    check(all(r["title"] for r in pb["related_types"]), f"{row['id']}: related type without title")
    check(bool(pb["practice_items"]) == row["has_items"], f"{row['id']}: has_items flag")
    check(all(any(it["id"] == x["item_id"] for it in items) for x in pb["practice_items"]), f"{row['id']}: practice item not gate-passed")
check(learn.playbook("no-such-type") is None, "playbook of a missing id should be None")
check(learn.playbook("../tags") is None, "playbook must refuse traversal")

# ---- static route (handler method, no socket) -----------------------------------------------------------
from chatbot import web  # noqa: E402


class FakeHandler(web.Handler):
    def __init__(self):  # skip BaseHTTPRequestHandler's socket setup
        self.code, self.headers_out, self.wfile = None, {}, io.BytesIO()

    def send_response(self, code, message=None):
        self.code = code

    def send_header(self, k, v):
        self.headers_out[k] = v

    def end_headers(self):
        pass


def static(name):
    h = FakeHandler()
    h._static(name)
    return h.code, h.headers_out.get("Content-Type", ""), h.wfile.getvalue()


for bad in ("../web.py", "..", "../../.env", "sub/dir.js", ".hidden", "", "learn.html/../web.py"):
    code, _, _ = static(bad)
    check(code == 404, f"static({bad!r}) should be 404, got {code}")
code, ctype, body = static("learn.html")
check(code == 200 and ctype.startswith("text/html") and b"renderSceneWhenVisible" in body, "static learn.html")
code, ctype, _ = static("playbooks.html")
check(code == 200 and ctype.startswith("text/html"), "static playbooks.html")
code, ctype, _ = static("scene.js")
check(code in (200, 404), f"static scene.js should be 200 or 404, got {code}")
if code == 200:
    check(ctype.startswith("application/javascript"), "scene.js content type")
check(static("web.py")[0] == 404, "static must not serve .py")

# ---- report ---------------------------------------------------------------------------------------------
print(f"items: {len(items)} gate-passed; {n_levels} with solution_levels; {n_scenes} with scenes")
if with_levels:
    print("  levels:", ", ".join(with_levels))
if with_scenes:
    print("  scenes:", ", ".join(with_scenes))
print(f"catalogue: {cat['n_items']} items in {len(cat['components'])} components "
      f"({', '.join(f'{c['component']} {len(c['items'])}' for c in cat['components'])})")
print(f"playbooks: {len(idx)} indexed, {sum(1 for p in idx if p['has_items'])} with practice items, "
      f"{sum(1 for p in idx if p['thin'])} thin (indicative)")
print(f"static: scene.js -> {static('scene.js')[0]}")
if fails:
    print(f"\nFAIL ({len(fails)}):")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("\nOK: all checks passed")
