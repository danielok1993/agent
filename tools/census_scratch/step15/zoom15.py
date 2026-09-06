"""Zoom crops for the step-15 report: a component's polygon (red) on the
sweep render, its minimum rotated rectangle (blue), and its long-side
boundary runs coloured by the shipped reading — green where the run lies
along a wall face at the barrier standoff, orange where it lies along a
wall solid's flat end (a band's cap, standoff 0), grey where it lies along
neither — with both covers (the rectangle's edges as the rule read them
before, the polygon's own sides as it reads them now) in the caption.
Plan crops only; every target lies inside a floor plan.

The chain is re-run for each sheet through the census harness so the
lines are the pipeline's exact `face_lines` / `cap_lines` off detect_rooms'
own frame, and the runs are read with the shipped helpers.

Usage: .venv/bin/python tools/census_scratch/step15/zoom15.py OUT_DIR
"""
from __future__ import annotations

import glob
import math
import sys
import warnings
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import harness as H  # noqa: E402

from detection import rooms  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from detection.walls import WALL_PARALLEL_ANGLE_TOL  # noqa: E402

# (slug, name, component bbox, pad, max scale)
TARGETS = [
    ("s17", "reveal_strip_0013_tab_on_band_cap", (912, 2174, 947, 2331), 60, 3.0),
    ("s17", "reveal_strip_0014_tabs_at_both_ends", (3047, 2174, 3084, 2489), 60, 2.5),
    ("s17", "reveal_strip_0027_tabs_at_both_ends", (3047, 2594, 3084, 3061), 60, 2.0),
    ("s17", "reveal_strip_0032_tab_at_the_far_end", (914, 2609, 949, 3061), 60, 2.0),
    # s18: the recorded-FP strip under a sofa whose rectangle read 0.14 on one
    # side and whose own runs read 0.90 (a notch pinned the rectangle).
    ("s18", "sofa_strip_recorded_fp_notch_0.14_to_0.90", (907, 810, 1079, 833), 60, 4.0),
    # The true class's narrowest member, 1.0 / 1.0 under every reading.
    ("s11", "storage_in_utility_confirmed_1.0_both_readings", (1078, 1597, 1095, 1704), 60, 4.0),
]


def _run_dir(slug):
    root = REPO / "outputs" / "regress" / slug
    return sorted(glob.glob(str(root / "*")))[-1]


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _capture(slug):
    """Every call the pocket rule receives, plus the emitted rooms, with the
    exact face_lines / cap_lines of the stage."""
    cap = {"calls": []}
    o_fsc, o_drop, o_pocket = (rooms._free_space_components,
                               rooms._drop_window_exterior_sides, rooms._is_band_pocket)

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        cap["face_lines"] = list(loc["face_lines"])
        cap["cap_lines"] = list(loc["cap_lines"])
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
    return cap


def _mrr_edge_cover(edge, lines):
    """The reading the rule used before step 15: the largest single face at
    the standoff along a rectangle edge (the old _edge_face_cover)."""
    (ax, ay), (bx, by) = edge
    length = math.hypot(bx - ax, by - ay)
    if length < 1e-6:
        return 0.0
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    angle = _line_angle_deg((ax, ay), (bx, by))
    best = 0.0
    for p1, p2 in lines:
        if _angle_diff_mod180(angle, _line_angle_deg(p1, p2)) > WALL_PARALLEL_ANGLE_TOL:
            continue
        standoff = abs((p1[0] - mx) * nx + (p1[1] - my) * ny)
        if abs(standoff - rooms.ROOM_LINE_BARRIER_PX) > rooms.ROOM_RECESS_BACK_TOL_PX:
            continue
        t1 = (p1[0] - ax) * ux + (p1[1] - ay) * uy
        t2 = (p2[0] - ax) * ux + (p2[1] - ay) * uy
        best = max(best, (min(max(t1, t2), length) - max(min(t1, t2), 0.0)) / length)
    return best


def main(out_dir, targets=TARGETS):
    out_dir.mkdir(parents=True, exist_ok=True)
    caps = {}
    for slug, name, bbox, pad, max_scale in targets:
        if slug not in caps:
            caps[slug] = _capture(slug)
        cap = caps[slug]
        pool = cap["calls"] + cap.get("rooms", [])
        poly = max(pool, key=lambda g: _iou(tuple(g.bounds), bbox), default=None)
        if poly is None or _iou(tuple(poly.bounds), bbox) < 0.5:
            print("no component for", slug, name)
            continue
        face_lines, cap_lines = cap["face_lines"], cap["cap_lines"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            rect = poly.minimum_rotated_rectangle
        c = list(rect.exterior.coords)[:4]
        edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
        lens = [_line_length(a, b) for a, b in edges]
        if lens[0] >= lens[1]:
            long_edges, short, axis_edge = (edges[0], edges[2]), lens[1], edges[0]
        else:
            long_edges, short, axis_edge = (edges[1], edges[3]), lens[0], edges[1]
        old = sorted(_mrr_edge_cover(e, face_lines) for e in long_edges)
        new = sorted(rooms._side_wall_covers(poly, axis_edge, (rect.centroid.x, rect.centroid.y),
                                             face_lines, cap_lines))
        axis = _line_angle_deg(*axis_edge)

        rd = _run_dir(slug)
        img = Image.open(f"{rd}/pages/page_01/render.png").convert("RGBA")
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        d.polygon([tuple(p) for p in rect.exterior.coords], outline=(0, 90, 220, 255), width=1)
        d.polygon([tuple(p) for p in poly.exterior.coords], outline=(220, 0, 0, 255), width=2)
        # the long-side runs, coloured by what they lie along
        coords = list(poly.exterior.coords)
        for a, b in zip(coords, coords[1:]):
            L = _line_length(a, b)
            if L < 1e-6 or _angle_diff_mod180(axis, _line_angle_deg(a, b)) > WALL_PARALLEL_ANGLE_TOL:
                continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            face_iv = rooms._run_wall_cover((a, b), face_lines, [])
            cap_iv = rooms._run_wall_cover((a, b), [], cap_lines)
            d.line([a, b], fill=(150, 150, 150, 255), width=3)
            for ivs, col in ((cap_iv, (240, 140, 0, 255)), (face_iv, (0, 170, 0, 255))):
                for lo, hi in ivs:
                    d.line([(a[0] + ux * lo, a[1] + uy * lo), (a[0] + ux * hi, a[1] + uy * hi)],
                           fill=col, width=3)
        x0, y0 = bbox[0] - pad, bbox[1] - pad
        x1, y1 = bbox[2] + pad, bbox[3] + pad
        cb = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
        crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
        w, h = crop.size
        sc = min(1200 / w, 900 / h, max_scale)
        crop = crop.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        capt = Image.new("RGB", (crop.width, crop.height + 50), (255, 255, 255))
        capt.paste(crop, (0, 0))
        dd = ImageDraw.Draw(capt)
        b = [round(v) for v in poly.bounds]
        spacing = short + 2.0 * rooms.ROOM_LINE_BARRIER_PX
        dd.text((4, crop.height + 4),
                f"{slug} {name} bbox {b} spacing {spacing:.2f}px  covers: rectangle edges (before) "
                f"[{old[0]:.2f}, {old[1]:.2f}]  own sides (now) [{new[0]:.2f}, {new[1]:.2f}]"[:240],
                fill=(0, 0, 0))
        dd.text((4, crop.height + 18),
                "red = component, blue = its minimum rotated rectangle; long-side runs: green = on a face at the "
                "standoff, orange = on a wall solid's flat end (cap), grey = on neither", fill=(60, 60, 60))
        path = out_dir / f"step15_{slug}_{name}.png"
        capt.save(path)
        print("wrote", path, capt.size, "old", [round(v, 3) for v in old], "new", [round(v, 3) for v in new])


if __name__ == "__main__":
    main(Path(sys.argv[1]))
