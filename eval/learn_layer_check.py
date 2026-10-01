"""Integration check for the learn layer (solution levels + interactive scenes) and the product pages.

    .venv/bin/python -m eval.learn_layer_check

No model calls. Runs, and reports PASS/FAIL for:
  1. every product self-test that exists (marks, examiner, marker, working, learn, scene, photo, levels/scenes checks);
  2. G1 and G8 re-run on every gate-passed item (the levels writer adds text to items; G8 scans every string);
  3. gate_levels on every part that has solution_levels (if scripts/clean/gate_levels.py exists);
  4. gate_scene on every scene in content/clean/scenes/ (if scripts/clean/gate_scene.py exists), including that every
     scene's item exists and passes G1-G8;
  5. the licence gate on the clean pack (a rebuild first);
  6. no item lost its review or gate_results fields (schema drift after concurrent writers).
"""
import glob
import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
PY = str(ROOT / ".venv" / "bin" / "python")
GATES = [f"G{i}" for i in range(1, 9)]
results: list[tuple[str, bool, str]] = []


def rec(name, ok, note=""):
    results.append((name, bool(ok), note))


def passed(item):
    g = item.get("gate_results") or {}
    return all((g.get(k) or {}).get("pass") for k in GATES)


# 1. self-tests
for mod in ("marks_selftest", "examiner_selftest", "marker_selftest", "working_selftest", "learn_selftest",
            "scene_selftest", "photo_selftest", "levels_check", "scenes_check", "playbooks_check"):
    if not (ROOT / "eval" / f"{mod}.py").exists():
        rec(f"self-test {mod}", True, "not present (skipped)")
        continue
    r = subprocess.run([PY, "-m", f"eval.{mod}"], cwd=ROOT, capture_output=True, text=True, timeout=600)
    tail = (r.stdout.strip().splitlines() or [""])[-1][:120]
    rec(f"self-test {mod}", r.returncode == 0, tail)

# 2. G1/G8 re-run and 6. field integrity
import gate_style  # noqa: E402
import gates  # noqa: E402

items = {}
g18_bad, drift = [], []
for f in sorted(glob.glob(str(ROOT / "content" / "clean" / "items" / "*.json"))):
    it = json.loads(Path(f).read_text())
    items[it["id"]] = it
    for key in ("gate_results", "review", "parts", "provenance"):
        if key not in it:
            drift.append(f"{it['id']}: missing {key}")
    if not passed(it):
        continue
    g1, g8 = gates.g1_structure(it), gate_style.g8_style(it)
    if not g1["pass"] or not g8["pass"]:
        g18_bad.append(f"{it['id']}: G1 {g1['errors'][:2]} G8 {g8['errors'][:3]}")
gp = [i for i in items.values() if passed(i)]
rec("G1/G8 re-run on gate-passed items", not g18_bad, f"{len(gp)} items; " + ("; ".join(g18_bad)[:300] or "all pass"))
rec("item field integrity", not drift, "; ".join(drift)[:300] or f"{len(items)} items intact")

# 3. levels gate
n_parts = n_levels = 0
lv_bad = []
try:
    gate_levels = importlib.import_module("gate_levels")
    for it in gp:
        n_parts += len(it["parts"])
        if any("solution_levels" in p for p in it["parts"]):
            n_levels += sum("solution_levels" in p for p in it["parts"])
            res = gate_levels.gate_levels(it)
            if not res.get("pass"):
                lv_bad.append(f"{it['id']}: {res.get('errors', [])[:2]}")
    rec("gate_levels on items with levels", not lv_bad, f"{n_levels}/{n_parts} parts have levels; " + ("; ".join(lv_bad)[:300] or "all pass"))
except ModuleNotFoundError:
    rec("gate_levels on items with levels", True, "gate_levels.py not present (skipped)")

# 4. scene gate
sc_files = sorted(glob.glob(str(ROOT / "content" / "clean" / "scenes" / "*.json")))
try:
    gate_scene = importlib.import_module("gate_scene")
    n_scenes = 0
    sc_bad = []
    for f in sc_files:
        d = json.loads(Path(f).read_text())
        it = items.get(d.get("item_id"))
        if it is None or not passed(it):
            sc_bad.append(f"{Path(f).name}: item missing or not gate-passed")
            continue
        for sc in d.get("scenes") or []:
            n_scenes += 1
            res = gate_scene.gate_scene(sc, it, require_guide=True)  # every scene must explain itself (spec §2, Guide)
            if not res.get("pass"):
                sc_bad.append(f"{sc.get('id')}: {res.get('errors', [])[:2]}")
    applicable = sum(1 for f in sc_files if json.loads(Path(f).read_text()).get("applicable"))
    rec("gate_scene on generated scenes", not sc_bad,
        f"{len(sc_files)} scene files, {applicable} applicable, {n_scenes} scenes; " + ("; ".join(sc_bad)[:300] or "all pass"))
except ModuleNotFoundError:
    rec("gate_scene on generated scenes", True, f"gate_scene.py not present (skipped); {len(sc_files)} scene files exist")

# 5. licence gate after a rebuild
r = subprocess.run([PY, "scripts/clean/build_pack.py"], cwd=ROOT, capture_output=True, text=True, timeout=600)
rec("clean pack build + licence gate", r.returncode == 0, (r.stdout.strip().splitlines() or [""])[-1][:120])

ok = all(r[1] for r in results)
print(f"learn-layer integration check: {'PASS' if ok else 'FAIL'}")
for name, good, note in results:
    print(f"  {'OK  ' if good else 'FAIL'} {name}: {note}")
sys.exit(0 if ok else 1)
