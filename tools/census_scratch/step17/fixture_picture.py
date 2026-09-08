"""The step-17 pin fixture as a picture: TestWallRecessTabbedByAPerpendicularBand's
cavity wall with s17's junction (the partition's paired segment ending ON the
inner face line, the line drawn from its far flank on) — the drawn paths
(black), the stage's segment solids (blue), the reveal component (red) with
its back runs coloured as the runs reading classes them (green: at the
standoff inside the inner leaf's outer line; orange: on the partition's flat
cap), the candidate gap rect (yellow) and both readings in the caption; and
the tab-less control beside it.

Usage: .venv/bin/python tools/census_scratch/step17/fixture_picture.py OUT_PNG
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tests"))

import recess_census as RC  # noqa: E402
from detection import rooms, detect_wall_network  # noqa: E402
from test_room_detection import (  # noqa: E402
    PAGE_W, PAGE_H, TestWallRecessTabbedByAPerpendicularBand as T, hline,
)

SC = 4.0            # px per drawing px
VIEW = (250, 92, 450, 180)


def stage(paths):
    cap = {"calls": []}
    o_fsc, o_rec = rooms._free_space_components, rooms._is_wall_recess

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        for k in ("cap_lines", "wall_segments", "solid_parts", "network"):
            cap[k] = loc[k]
        cap["opening_boxes"] = ([box(*c.bbox) for c in loc["doors"]]
                                + [box(*c.bbox) for c in loc["windows"]])
        return o_fsc(page, barriers)

    def rec(comp, ws, ob, ts, **kw):
        res = o_rec(comp, ws, ob, ts, **kw)
        cap["calls"].append((comp, res))
        return res

    rooms._free_space_components, rooms._is_wall_recess = fsc, rec
    try:
        with mock.patch.object(rooms, "_is_band_pocket", return_value=False):
            net = detect_wall_network(paths, [])
            out = rooms.detect_rooms(net, [], [], PAGE_W, PAGE_H, [])
    finally:
        rooms._free_space_components, rooms._is_wall_recess = o_fsc, o_rec
    cap["rooms"] = out
    return cap


def panel(paths, title):
    cap = stage(paths)
    x0, y0, x1, y1 = VIEW
    w, h = int((x1 - x0) * SC), int((y1 - y0) * SC)
    plan = Image.new("RGB", (w, h), (255, 255, 255))   # the drawing, clipped to the view
    d = ImageDraw.Draw(plan)

    def P(p):
        return ((p[0] - x0) * SC, (p[1] - y0) * SC)

    n_seg = len(cap["wall_segments"])
    for i, part in enumerate(cap["solid_parts"][:n_seg]):
        d.polygon([P(p) for p in part.exterior.coords], outline=(0, 90, 220), width=2)
    for p in paths:
        pts = [P(q) for q in p.points]
        d.line(pts, fill=(0, 0, 0), width=max(1, int(p.stroke_width * SC / 1.5)))
    reveal = next((c for c, _ in cap["calls"] if c.bounds[1] < 150), None)
    lines = [title]
    if reveal is not None:
        verdict = next(r for c, r in cap["calls"] if c is reveal)
        r = RC.readings(reveal, cap["wall_segments"], cap["opening_boxes"], [], cap["cap_lines"])
        d.polygon([P(p) for p in reveal.exterior.coords], outline=(220, 0, 0), width=3)
        for cd in r["candidates"]:
            a_p1, a_p2, th = cd["a"]
            b_p1, b_p2, _ = cd["b"]
            # the gap rect in a's frame
            import math
            ux = (a_p2[0] - a_p1[0]) / math.hypot(a_p2[0] - a_p1[0], a_p2[1] - a_p1[1])
            uy = (a_p2[1] - a_p1[1]) / math.hypot(a_p2[0] - a_p1[0], a_p2[1] - a_p1[1])
            nx, ny = -uy, ux
            lo, hi = cd["gap"]
            rect = [(a_p1[0] + ux * t + nx * wv, a_p1[1] + uy * t + ny * wv)
                    for t, wv in ((lo, -th / 2), (hi, -th / 2), (hi, th / 2), (lo, th / 2))]
            d.polygon([P(p) for p in rect], outline=(230, 200, 0), width=3)
            for sk, sd in cd["sides"].items():
                for rr in sd["runs"]:
                    col = (0, 200, 0) if rr["on_face"] else (255, 120, 0)
                    d.line([P(rr["run"][0]), P(rr["run"][1])], fill=col, width=8)
            lines.append(f"gap cover {cd['gap_cover']}, depth {cd['depth_bands']}x the leaf")
            lines.append(f"EXTENT reading: back {cd['back']:+.2f} (2 +- 1.5 wanted) -> "
                         f"{'recess' if cd['extent_ok'] else 'NOT a recess'}")
            lines.append(f"RUNS reading: face alone {cd['face_own']:.2f}, with the cap {cd['caps_own']:.2f} of the "
                         f"reveal's extent -> {'recess' if cd['caps_own'] >= 0.65 else 'not'}")
        lines.append(f"reveal {[round(v, 1) for v in reveal.bounds]} area {reveal.area:.0f} px2; shipped verdict {verdict}; "
                     f"rooms emitted with the pocket rule out: {len(cap['rooms'])}")
    else:
        lines.append(f"no reveal call; rooms emitted: {len(cap['rooms'])}")
    img = Image.new("RGB", (w, h + 84), (255, 255, 255))
    img.paste(plan, (0, 0))
    dc = ImageDraw.Draw(img)
    for i, t in enumerate(lines):
        dc.text((4, h + 4 + 14 * i), t[:230], fill=(0, 0, 0))
    return img


def main(out):
    t = T()
    tabbed = t._plan()
    tabless = [p for p in tabbed if p.path_index != 5] + [hline(5, t.PART0, 600.0, t.INNER)]
    a = panel(tabbed, "TABBED (s17's junction): the inner face line drawn from the partition's far flank on; "
                      "its flat cap bounds the reveal at standoff 0 over 31.5px")
    b = panel(tabless, "TAB-LESS control: the inner face line drawn continuously across the junction")
    img = Image.new("RGB", (a.width + b.width + 20, max(a.height, b.height) + 20), (255, 255, 255))
    img.paste(a, (0, 0))
    img.paste(b, (a.width + 20, 0))
    d = ImageDraw.Draw(img)
    d.text((4, img.height - 14),
           "black = drawn paths; blue = segment solids; red = the reveal component; yellow = the collinear gap rect the "
           "recess rule reads; thick green = back run at the standoff inside the line; thick orange = on the partition's flat cap",
           fill=(60, 60, 60))
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
