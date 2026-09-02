"""Entity-level before|after delta between a compare_sweeps snapshot
(outputs/regress_baseline/<slug>) and the latest sweep run
(outputs/regress/<slug>) — including ROOM SHAPE changes.

tools/regress.py matches verdicts geometrically at IoU >= 0.5, so a room
that keeps its identity but changes outline (a notch, a leaning edge, a
strip fenced off) never appears in the sweep report, and
tools/compare_sweeps.py only draws entities that were added or removed.
This prints, per page: entities removed / added (no counterpart at IoU 0.5),
and every room whose best match has IoU < 0.995, with the area delta.

Usage:
    python tools/compare_sweeps.py s03 --snapshot   # before the change
    ... change detection, re-sweep ...
    python tools/compare_room_shapes.py s03 [s04 ...]
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[1]


def _latest(pattern: str) -> str | None:
    runs = sorted(glob.glob(pattern))
    return runs[-1] if runs else None


def _load(run_dir: str) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for f in glob.glob(os.path.join(run_dir, "pages", "page_*", "final_entities.json")):
        d = json.load(open(f))
        out[d["page_number"]] = d["entities"]
    return out


def _geom(e: dict):
    poly = e.get("attributes", {}).get("polygon")
    if poly and len(poly) >= 3:
        try:
            g = Polygon(poly)
            if g.is_valid and g.area > 0:
                return g
        except Exception:  # noqa: BLE001 — fall back to the bbox
            pass
    return box(*e["bbox"])


def _iou(a, b) -> float:
    inter = a.intersection(b).area
    return inter / a.union(b).area if inter > 0 else 0.0


def main(slugs: list[str]) -> None:
    for slug in slugs:
        base = _latest(f"{ROOT}/outputs/regress_baseline/{slug}/*")
        after = _latest(f"{ROOT}/outputs/regress/{slug}/*")
        if not base or not after:
            print(f"{slug}: missing baseline snapshot or latest run")
            continue
        before_pages, after_pages = _load(base), _load(after)
        for page in sorted(set(before_pages) | set(after_pages)):
            be, ae = before_pages.get(page, []), after_pages.get(page, [])
            unmatched = list(ae)
            shape_changes, removed = [], []
            for e in be:
                g = _geom(e)
                best, best_iou = None, 0.0
                for f in unmatched:
                    if f["entity_type"] != e["entity_type"]:
                        continue
                    v = _iou(g, _geom(f))
                    if v > best_iou:
                        best, best_iou = f, v
                if best is None or best_iou < 0.5:
                    removed.append(e)
                    continue
                unmatched.remove(best)
                if e["entity_type"] == "room" and best_iou < 0.995:
                    shape_changes.append(
                        (e["entity_id"], best["entity_id"], best_iou, g.area, _geom(best).area))
            print(f"{slug} p{page}: before {len(be)} / after {len(ae)} | removed "
                  f"{len(removed)} | added {len(unmatched)} | room shape changes "
                  f"{len(shape_changes)}")
            for e in removed:
                print(f"   REMOVED {e['entity_id']} {e['entity_type']} "
                      f"conf={e['confidence']} bbox={[round(v) for v in e['bbox']]}")
            for e in unmatched:
                print(f"   ADDED   {e['entity_id']} {e['entity_type']} "
                      f"conf={e['confidence']} bbox={[round(v) for v in e['bbox']]}")
            for bid, aid, v, ab, aa in shape_changes:
                print(f"   SHAPE   {bid} -> {aid} iou={v:.3f} area {ab:.0f} -> {aa:.0f} "
                      f"({(aa - ab) / ab * 100:+.1f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
