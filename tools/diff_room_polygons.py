"""Every-room polygon diff between a compare_sweeps snapshot
(outputs/regress_baseline/<slug>) and the latest sweep (outputs/regress/<slug>).

tools/compare_room_shapes.py prints only rooms whose best match has
IoU < 0.995 — a 44 px^2 or 134 px^2 move on a large room never appears there
(s03 rooms 0008/0015 under the seam-probe fix). This prints EVERY room whose
polygon changed at all (symmetric difference above --min px^2), with the area
delta and the bounds of the changed region, plus entities of every type that
were added, removed (no counterpart at IoU >= 0.5) or whose bbox moved. Run it
corpus-wide after every sweep; a sheet that prints IDENTICAL did not move.

Usage:
    python tools/compare_sweeps.py sNN --snapshot     # before the change
    ... change detection, re-sweep ...
    python tools/diff_room_polygons.py [sNN ...] [--min 0.5]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
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
            return g if g.is_valid and g.area > 0 else g.buffer(0)
        except Exception:  # noqa: BLE001 — fall back to the bbox
            pass
    return box(*e["bbox"])


def _iou(a, b) -> float:
    inter = a.intersection(b).area
    return inter / a.union(b).area if inter > 0 else 0.0


def diff_slug(slug: str, min_symdiff: float) -> tuple[int, int, int]:
    base = _latest(f"{ROOT}/outputs/regress_baseline/{slug}/*")
    after = _latest(f"{ROOT}/outputs/regress/{slug}/*")
    if not base or not after:
        print(f"{slug}: missing baseline snapshot or latest run")
        return 0, 0, 0
    bp, ap_ = _load(base), _load(after)
    lines: list[str] = []
    changed = added = removed = 0
    for page in sorted(set(bp) | set(ap_)):
        be, ae = bp.get(page, []), ap_.get(page, [])
        unmatched = list(ae)
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
                lines.append(f"  p{page} REMOVED {e['entity_type']} {e['entity_id']} "
                             f"bbox={[round(v) for v in e['bbox']]} conf={e.get('confidence')}")
                removed += 1
                continue
            unmatched.remove(best)
            if e["entity_type"] == "room":
                h = _geom(best)
                sd = g.symmetric_difference(h)
                if sd.area > min_symdiff:
                    changed += 1
                    b = sd.bounds
                    lines.append(
                        f"  p{page} SHAPE {e['entity_id']} -> {best['entity_id']} iou={best_iou:.4f} "
                        f"area {g.area:.0f} -> {h.area:.0f} ({h.area - g.area:+.0f} px2) "
                        f"symdiff={sd.area:.0f} px2 at [{b[0]:.0f},{b[1]:.0f}]-[{b[2]:.0f},{b[3]:.0f}] "
                        f"label={e.get('attributes', {}).get('label')!r}->"
                        f"{best.get('attributes', {}).get('label')!r}")
            elif best["bbox"] != e["bbox"]:
                lines.append(f"  p{page} MOVED {e['entity_type']} {e['entity_id']} -> {best['entity_id']} "
                             f"iou={best_iou:.3f} bbox {[round(v) for v in e['bbox']]} -> "
                             f"{[round(v) for v in best['bbox']]}")
        for f in unmatched:
            lines.append(f"  p{page} ADDED {f['entity_type']} {f['entity_id']} "
                         f"bbox={[round(v) for v in f['bbox']]} conf={f.get('confidence')}")
            added += 1
    nb = sum(len(v) for v in bp.values())
    na = sum(len(v) for v in ap_.values())
    print(f"{slug}: base={os.path.basename(base)} after={os.path.basename(after)} "
          f"entities {nb} -> {na}" + ("" if lines else "  IDENTICAL"))
    for ln in lines:
        print(ln)
    return changed, added, removed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slugs", nargs="*", help="default: s01..s20")
    ap.add_argument("--min", type=float, default=0.5,
                    help="symmetric-difference floor in px^2 for a SHAPE line (default 0.5)")
    args = ap.parse_args()
    slugs = args.slugs or [f"s{i:02d}" for i in range(1, 21)]
    tc = ta = tr = 0
    for slug in slugs:
        c, a, r = diff_slug(slug, args.min)
        tc += c
        ta += a
        tr += r
    print(f"\nTOTAL rooms with changed polygon: {tc}; added {ta}; removed {tr}")


if __name__ == "__main__":
    main()
