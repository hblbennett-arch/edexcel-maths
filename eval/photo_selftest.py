"""Self-test for the photo path of "Mark my working" (chatbot/working.py transcribe_upload + submit(transcript_confirmed)).
marker.transcribe_image and marker.mark are monkeypatched: no model calls, no network. Events go to a temp database.

    .venv/bin/python -m eval.photo_selftest
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chatbot import events, marker, marks, working  # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


PNG_1x1 = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da"
                        "636000010000050001a5f645400000000049454e44ae426082")
FIXED = {"lines": ["$-x^2+8x-5=x+1$", "$x^2-7x+6=0$ so $x=1, 6$", "Area $=\\frac{125}{6}$"],
         "line_confidence": [0.95, 0.6, 0.9], "confidence": 0.6, "needs_confirmation": True, "source": "image",
         "cost_usd": 0.012, "model": marker.DEFAULT_MODEL}
seen = {}


def fake_transcribe_image(path, *, model=marker.DEFAULT_MODEL, ref=""):
    p = Path(path)
    seen.update(path=p, existed=p.exists(), size=p.stat().st_size if p.exists() else None, suffix=p.suffix, ref=ref)
    return dict(FIXED)


real_ti, marker.transcribe_image = marker.transcribe_image, fake_transcribe_image
try:
    # ---- transcribe_upload: happy path writes then deletes the temp file --------------------------------
    out = working.transcribe_upload(PNG_1x1, "png")
    check("error" not in out, f"upload error {out}")
    check(seen.get("existed") and seen.get("size") == len(PNG_1x1) and seen.get("suffix") == ".png", f"temp file {seen}")
    check(not seen["path"].exists(), "temp file deleted after the call")
    check(out["lines"] == FIXED["lines"] and out["line_confidence"] == FIXED["line_confidence"], f"transcript {out}")
    check(out["needs_confirmation"] is True and out["confidence"] == 0.6 and out["cost_usd"] == 0.012, f"shape {out}")
    check(set(out) >= {"lines", "line_confidence", "confidence", "needs_confirmation", "cost_usd"}, f"keys {set(out)}")
    # extension spellings
    for ext in ("JPG", ".jpeg", "image/webp", "png"):
        check("error" not in working.transcribe_upload(PNG_1x1, ext), f"ext {ext!r} accepted")
    check(seen["suffix"] == ".png" and not seen["path"].exists(), "temp files deleted every time")
    # ---- rejections: heic, unknown type, empty, oversize ----------------------------------------------
    seen.clear()
    e = working.transcribe_upload(PNG_1x1, "heic")
    check(e.get("error") and "HEIC" in e["error"] and not seen, f"heic rejected without a call {e}")
    e = working.transcribe_upload(PNG_1x1, "image/heif")
    check(e.get("error") and "HEIC" in e["error"], f"heif rejected {e}")
    e = working.transcribe_upload(PNG_1x1, "pdf")
    check(e.get("error") and "JPEG" in e["error"] and not seen, f"unknown type rejected {e}")
    e = working.transcribe_upload(b"", "png")
    check(e.get("error") and "empty" in e["error"] and not seen, f"empty rejected {e}")
    e = working.transcribe_upload(b"x" * (working.MAX_IMAGE_BYTES + 1), "jpg")
    check(e.get("error") and "too large" in e["error"] and not seen, f"oversize rejected {e}")
    check("error" not in working.transcribe_upload(b"x" * working.MAX_IMAGE_BYTES, "jpg"), "exactly 6 MB accepted")
    check(not seen["path"].exists(), "temp file deleted for the 6 MB upload")
    # ---- transcriber failure: friendly error, temp file still deleted --------------------------------
    def boom(path, **k):
        seen["boom_path"] = Path(path)
        raise RuntimeError("claude exited 1")
    marker.transcribe_image = boom
    e = working.transcribe_upload(PNG_1x1, "png")
    check(e.get("error") == working.PHOTO_ERROR and "RuntimeError" in e.get("detail", ""), f"failure wrapped {e}")
    check(not seen["boom_path"].exists(), "temp file deleted after a failure")
    marker.transcribe_image = fake_transcribe_image
    stray = [f for f in os.listdir(tempfile.gettempdir()) if f.startswith("mmw-photo-")]
    check(not stray, f"stray temp files {stray}")

    # ---- submit(..., transcript_confirmed=True) records the flag -------------------------------------
    item_id = "cr-area-between-curve-and-line-core"
    item = working.find_item(item_id)
    check(item is not None, f"{item_id} must pass the gates")
    scheme = [m["code"] for m in item["parts"][0]["mark_scheme"]]
    codes = ["M1", "A1", "M1", "dM1", "A1*"]

    def fake_mark(it, part_label, working_, *, facts=None, model=marker.DEFAULT_MODEL, ref="", **k):
        decs = [{"scheme_code": sc, "code": c, "awarded": True, "evidence": f"L{i + 1}", "reason": "earned", "convention": "M",
                 "error_code": None, "rewrite_to_earn": None, "confidence": 0.9, "overridden": False, "part": None,
                 "position": i, "skill": None} for i, (sc, c) in enumerate(zip(scheme, codes))]
        return {"decisions": decs, "summary": {"-": marks.vector_summary(scheme, codes)}, "vectors": {"-": codes},
                "facts": [], "model": model, "cost_usd": 0.03, "seconds": 8.0, "overrides": 0, "total": 5, "earned": 5,
                "lines": marker._lines_of(working_)}

    real_mark, marker.mark = marker.mark, fake_mark
    try:
        with tempfile.TemporaryDirectory() as td:
            conn = events.connect(Path(td) / "events.db")
            text = "\n".join(FIXED["lines"])
            out = working.submit("u-photo", item_id, None, text, transcript_confirmed=True, source="image", conn=conn)
            check("error" not in out, f"confirmed submit error {out.get('error')} {out.get('detail')}")
            check(out["transcript"]["source"] == "image" and out["transcript"]["lines"] == FIXED["lines"], f"transcript view {out['transcript']}")
            out2 = working.submit("u-photo", item_id, None, text, conn=conn)                              # typed, as today
            out3 = working.submit("u-photo", item_id, None, text, transcript_confirmed=None, conn=conn)   # explicit None
            out4 = working.submit("u-photo", item_id, None, text, transcript_confirmed=False, conn=conn)  # explicit False
            check(all("error" not in o for o in (out2, out3, out4)), "other submits fine")
            rows = {r["id"]: r for r in conn.execute("SELECT * FROM marking_events").fetchall()}
            import json
            r1, r2, r3, r4 = (rows[o["event_ids"][0]] for o in (out, out2, out3, out4))
            check(r1["transcript_confirmed"] == 1 and json.loads(r1["meta"])["input"] == "image", f"confirmed event {dict(r1)}")
            check(r2["transcript_confirmed"] == 1 and json.loads(r2["meta"])["input"] == "typed", f"typed event unchanged {dict(r2)}")
            check(r3["transcript_confirmed"] is None, f"explicit None recorded as NULL {dict(r3)}")
            check(r4["transcript_confirmed"] == 0, f"explicit False recorded as 0 {dict(r4)}")
            check(out["transcript"]["needs_confirmation"] is False, "typed/confirmed text needs no further confirmation")
    finally:
        marker.mark = real_mark
finally:
    marker.transcribe_image = real_ti

if fails:
    print("FAIL")
    for f in fails:
        print(" -", f)
    sys.exit(1)
print("OK: transcribe_upload (temp file written+deleted, heic/type/empty/oversize rejected, failure wrapped), "
      "submit(transcript_confirmed=True/None/False) recorded, typed path unchanged")
