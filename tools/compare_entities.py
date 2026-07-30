"""Diff two extraction runs by their final entities.

Usage:
    python tools/compare_entities.py OLD_RUN_DIR NEW_RUN_DIR
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(run_dir: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for page in sorted(Path(run_dir).glob("pages/page_*/final_entities.json")):
        payload = json.loads(page.read_text(encoding="utf-8"))
        out[page.parent.name] = payload.get("entities", [])
    return out


def key(e: dict) -> tuple:
    return (e["entity_type"], e["entity_id"],
            tuple(round(v, 2) for v in e["bbox"]), round(e["confidence"], 3))


def main(old_dir: str, new_dir: str) -> int:
    old, new = load(old_dir), load(new_dir)
    pages = sorted(set(old) | set(new))
    identical = True

    for page in pages:
        a = {key(e) for e in old.get(page, [])}
        b = {key(e) for e in new.get(page, [])}
        counts_a: dict[str, int] = {}
        counts_b: dict[str, int] = {}
        for e in old.get(page, []):
            counts_a[e["entity_type"]] = counts_a.get(e["entity_type"], 0) + 1
        for e in new.get(page, []):
            counts_b[e["entity_type"]] = counts_b.get(e["entity_type"], 0) + 1

        print(f"\n=== {page}")
        for etype in sorted(set(counts_a) | set(counts_b)):
            na, nb = counts_a.get(etype, 0), counts_b.get(etype, 0)
            flag = "" if na == nb else "   <== CHANGED"
            print(f"    {etype:10s} old={na:4d}  new={nb:4d}{flag}")

        only_old, only_new = a - b, b - a
        if only_old or only_new:
            identical = False
            print(f"    {len(only_old)} entities only in OLD, {len(only_new)} only in NEW")
            for k in sorted(only_old)[:8]:
                print(f"      OLD {k[0]:8s} {k[1]:14s} bbox={k[2]} conf={k[3]}")
            for k in sorted(only_new)[:8]:
                print(f"      NEW {k[0]:8s} {k[1]:14s} bbox={k[2]} conf={k[3]}")

    print("\nIDENTICAL" if identical else "\nDIFFERENCES FOUND")
    return 0 if identical else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
