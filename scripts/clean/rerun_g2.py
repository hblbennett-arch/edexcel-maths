#!/usr/bin/env python3
"""Re-run gate G2 (maths) only and store the result under gate_results.G2.

    .venv/bin/python scripts/clean/rerun_g2.py content/clean/items/ITEM.json [...]
    .venv/bin/python scripts/clean/rerun_g2.py --dry ITEM.json        # print only, don't write

Prints before/after pass per item and a summary of flips. Writes atomically (tmp + os.replace).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate_maths  # noqa: E402


def main(argv: list[str]) -> int:
    dry = "--dry" in argv
    paths = [Path(a) for a in argv if a != "--dry"]
    flipped_up, flipped_down = [], []
    for path in paths:
        text = path.read_text()
        item = json.loads(text)
        before = (item.get("gate_results") or {}).get("G2", {}).get("pass")
        res = gate_maths.g2_maths(json.loads(text, parse_float=str))
        after = res["pass"]
        print(f"{path.name}: G2 {before} -> {after}")
        for e in res["errors"]:
            print(f"    {e}")
        if before is not True and after:
            flipped_up.append(path.name)
        elif before is True and not after:
            flipped_down.append(path.name)
        if not dry:
            item["gate_results"] = {**(item.get("gate_results") or {}), "G2": res}
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(item, indent=1, ensure_ascii=False) + "\n")
            os.replace(tmp, path)
    print(f"\n{len(paths)} item(s): {len(flipped_up)} flipped to G2 pass, {len(flipped_down)} flipped to fail")
    for n in flipped_up:
        print(f"  + {n}")
    for n in flipped_down:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
