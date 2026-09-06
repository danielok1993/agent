"""The END runs of the key components (s17's four strips, the 25.25px reveal,
s11's storage): every boundary run parallel to the rectangle's SHORT axis,
its length, its offset from the rectangle centre, its wall-lying stretches
(faces at the standoff / caps) and how much of it has a wall SOLID behind
it at the probe depth — and the union-projection closure per end (the
reading a rule would use), at probe depths 6 and 7 px.

Usage: .venv/bin/python tools/census_scratch/step16/end_runs_probe.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
import backing_census as BC  # noqa: E402
from shapely.geometry import LineString, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_length  # noqa: E402

TARGETS = {
    "s17": [(912, 2174, 947, 2331), (914, 2609, 949, 3061), (3047, 2174, 3084, 2489),
            (3047, 2594, 3084, 3061), (3434, 2186, 3579, 2207)],
    "s11": [(1078, 1597, 1095, 1704)],
    "s18": [(2079, 1023, 2096, 1068), (907, 810, 1079, 833)],
    "s16": [(2507, 1323, 2527, 1401)],
    "s12": [(1842, 472, 1873, 494), (1842, 530, 1873, 554)],
}


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def closure(poly, axis_edge, centre, solids, probe):
    """Per end (runs parallel to axis_edge, classed by side): the union of
    the runs' solid-backed stretches projected on the axis over the axis
    length — the whole run probed, not only its wall-lying stretches."""
    sides, (ux, uy), L = BC._runs_by_side(poly, axis_edge, centre)
    (ax, ay) = axis_edge[0]
    out = []
    for runs in sides:
        ivs = []
        detail = []
        for a, b, (ox, oy) in runs:
            rl = _line_length(a, b)
            rux, ruy = (b[0] - a[0]) / rl, (b[1] - a[1]) / rl
            line = LineString([(a[0] + ox * probe, a[1] + oy * probe), (b[0] + ox * probe, b[1] + oy * probe)])
            hit = line.intersection(solids)
            backed = 0.0
            for piece in getattr(hit, "geoms", [hit]):
                if piece.is_empty or piece.geom_type != "LineString":
                    continue
                ts = sorted(((c[0] - line.coords[0][0]) * rux + (c[1] - line.coords[0][1]) * ruy) for c in piece.coords)
                lo, hi = ts[0], ts[-1]
                backed += hi - lo
                ta = (a[0] + rux * lo - ax) * ux + (a[1] + ruy * lo - ay) * uy
                tb = (a[0] + rux * hi - ax) * ux + (a[1] + ruy * hi - ay) * uy
                ivs.append((max(min(ta, tb), 0.0), min(max(ta, tb), L)))
            detail.append((round(rl, 1), [round(v, 1) for v in a], [round(v, 1) for v in b], round(backed, 1)))
        out.append((round(BC._union_len(ivs) / L, 3) if L > 0 else 0.0, detail))
    return out


def main():
    for slug, boxes in TARGETS.items():
        cap = {"calls": []}
        o_fsc, o_drop, o_pocket = (rooms._free_space_components, rooms._drop_window_exterior_sides,
                                   rooms._is_band_pocket)

        def fsc(page, barriers):
            loc = sys._getframe(1).f_locals
            for k in ("face_lines", "cap_lines", "wall_segments", "solid_parts", "solids"):
                cap[k] = loc[k]
            return o_fsc(page, barriers)

        def drop(rooms_list, windows, **k):
            cap["rooms"] = [poly for poly, _ in rooms_list]
            return o_drop(rooms_list, windows, **k)

        def pocket(comp, face_lines, text_spans, *, cap_lines=(), gates=rooms.ROOM_GATES_UNSCALED):
            res = o_pocket(comp, face_lines, text_spans, cap_lines=cap_lines, gates=gates)
            cap["calls"].append(comp)
            return res

        rooms._free_space_components, rooms._drop_window_exterior_sides, rooms._is_band_pocket = fsc, drop, pocket
        try:
            H.run(H.load(slug)[0])
        finally:
            rooms._free_space_components, rooms._drop_window_exterior_sides, rooms._is_band_pocket = o_fsc, o_drop, o_pocket
        pool = cap["calls"] + cap.get("rooms", [])
        solids = cap["solids"]
        for bbox in boxes:
            poly = max(pool, key=lambda g: _iou(tuple(g.bounds), bbox), default=None)
            if poly is None or _iou(tuple(poly.bounds), bbox) < 0.5:
                print(slug, bbox, "no component")
                continue
            m = BC._mrr(poly)
            print(f"{slug} {[round(v, 1) for v in poly.bounds]} short {m['short']:.2f} long {m['long']:.2f} "
                  f"vertices {len(poly.exterior.coords) - 1}")
            for probe in (6.0, 7.0):
                ends = closure(poly, m["short_edge"], m["centre"], solids, probe)
                sides = closure(poly, m["axis_edge"], m["centre"], solids, probe)
                print(f"   probe {probe}: END closures {[e[0] for e in ends]}   SIDE backing {[s[0] for s in sides]}")
                if probe == 7.0:
                    for i, (frac, detail) in enumerate(ends):
                        for rl, a, b, backed in detail:
                            print(f"      end {i}: run {a}-{b} len {rl} backed {backed}")


if __name__ == "__main__":
    main()
