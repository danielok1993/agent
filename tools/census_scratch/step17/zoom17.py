"""Zoom crops for step 17: a `_is_wall_recess` call (red) on the sweep render
with the rule's own evidence overlaid — every wall SEGMENT's solid outline
(blue), the collinear-gap RECT of the candidate the back edge is read against
(yellow), the component's back runs at the standoff inside the band's outer
line (green) and on a wall solid's flat end (orange), plus the paired (green)
and lone (orange) faces and the door / window seals (magenta / cyan) as in
zoom16 — so what the extent reading and the runs reading each see can be
read off the picture. Plan crops only; every target lies inside a floor plan.

Usage: .venv/bin/python tools/census_scratch/step17/zoom17.py OUT_DIR [tag]
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon, box

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import harness as H  # noqa: E402
import recess_census as RC  # noqa: E402

from detection import rooms  # noqa: E402

# (slug, name, component bbox, pad, max scale)
TARGETS = [
    ("s11", "breast_pocket_886_874_recess_both_readings", (886, 874, 976, 917), 90, 3.0),
    ("s11", "breast_pocket_781_1509_recess_both_readings", (781, 1509, 823, 1533), 90, 3.0),
    ("s18", "pier_2096_2506_gap_cover_0.66_recess_both_readings", (2096, 2506, 2157, 2558), 90, 3.0),
    ("s17", "pocket_1548_2766_112mm_band_recess_both_readings", (1548, 2766, 1569, 2910), 90, 2.2),
    ("s10", "recess_497_2935_back_minus_2.12", (497, 2935, 611, 3026), 90, 2.5),
    ("s17", "hollow_wall_strip_0013_no_collinear_gap", (912, 2174, 947, 2331), 110, 2.5),
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
    cap = {"calls": [], "pockets": []}
    o_fsc, o_drop, o_recess, o_pocket = (
        rooms._free_space_components, rooms._drop_window_exterior_sides,
        rooms._is_wall_recess, rooms._is_band_pocket)

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        for k in ("face_lines", "cap_lines", "wall_segments", "network", "door_barriers",
                  "window_barriers", "solid_parts"):
            cap[k] = loc[k]
        cap["opening_boxes"] = ([box(*c.bbox) for c in loc["doors"]]
                                + [box(*c.bbox) for c in loc["windows"]])
        return o_fsc(page, barriers)

    def drop(rooms_list, windows, **k):
        cap["rooms"] = [poly for poly, _ in rooms_list]
        return o_drop(rooms_list, windows, **k)

    def recess(comp, wall_segments, opening_boxes, text_spans, **kw):
        res = o_recess(comp, wall_segments, opening_boxes, text_spans, **kw)
        cap["calls"].append((comp, res))
        return res

    def pocket(comp, face_lines, text_spans, **kw):
        res = o_pocket(comp, face_lines, text_spans, **kw)
        cap["pockets"].append((comp, res))
        return res

    rooms._free_space_components, rooms._drop_window_exterior_sides = fsc, drop
    rooms._is_wall_recess, rooms._is_band_pocket = recess, pocket
    try:
        H.run(H.load(slug)[0])
    finally:
        rooms._free_space_components, rooms._drop_window_exterior_sides = o_fsc, o_drop
        rooms._is_wall_recess, rooms._is_band_pocket = o_recess, o_pocket
    return cap


def _draw_geom(d, g, colour, width):
    for piece in getattr(g, "geoms", [g]):
        if piece.is_empty:
            continue
        if piece.geom_type == "Polygon":
            d.polygon([tuple(p) for p in piece.exterior.coords], outline=colour, width=width)
        elif piece.geom_type == "LineString":
            d.line([tuple(p) for p in piece.coords], fill=colour, width=width)


def main(out_dir, tag="step17", targets=TARGETS):
    out_dir.mkdir(parents=True, exist_ok=True)
    caps = {}
    for slug, name, bbox, pad, max_scale in targets:
        if slug not in caps:
            caps[slug] = _capture(slug)
        cap = caps[slug]
        pool = [c for c, _ in cap["calls"]] + [c for c, _ in cap["pockets"]] + cap.get("rooms", [])
        poly = max(pool, key=lambda g: _iou(tuple(g.bounds), bbox), default=None)
        if poly is None or _iou(tuple(poly.bounds), bbox) < 0.5:
            print("no component for", slug, name)
            continue
        verdict = next((r for c, r in cap["calls"] if c is poly), None)
        r = RC.readings(poly, cap["wall_segments"], cap["opening_boxes"], [], cap["cap_lines"])
        rd = _run_dir(slug)
        img = Image.open(f"{rd}/pages/page_01/render.png").convert("RGBA")
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        view = box(bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
        paired = cap["network"].paired_face_indices()
        n_seg = len(cap["wall_segments"])
        for i, part in enumerate(cap["solid_parts"]):
            if part.intersects(view):
                _draw_geom(d, part, (0, 90, 220, 255) if i < n_seg else (0, 160, 200, 255), 2)
        for f in cap["network"].faces:
            ln = LineString([f.p1, f.p2])
            if ln.intersects(view):
                col = (0, 170, 0, 255) if (f.indices & paired) else (240, 140, 0, 255)
                d.line([f.p1, f.p2], fill=col, width=2)
        for conf, g in cap["door_barriers"]:
            if g.intersects(view):
                _draw_geom(d, g, (200, 0, 200, 255), 2)
        for g in cap["window_barriers"]:
            if g.intersects(view):
                _draw_geom(d, g, (0, 180, 180, 255), 2)
        # the candidate gap rects and the back runs
        cands = RC.gap_candidates(poly, cap["wall_segments"], cap["opening_boxes"])
        for c in cands:
            a = c["a"]
            ux, uy, nx, ny, th, lo, hi = c["ux"], c["uy"], c["nx"], c["ny"], c["th"], c["lo"], c["hi"]
            rect = Polygon([(a.p1[0] + ux * t + nx * w, a.p1[1] + uy * t + ny * w)
                            for t, w in ((lo, -th / 2), (hi, -th / 2), (hi, th / 2), (lo, th / 2))])
            d.polygon([tuple(p) for p in rect.exterior.coords], outline=(230, 200, 0, 255), width=3)
        d.polygon([tuple(p) for p in poly.exterior.coords], outline=(220, 0, 0, 255), width=3)
        for cd in r["candidates"]:
            for sk, sd in cd["sides"].items():
                for rr in sd["runs"]:
                    col = (0, 200, 0, 255) if rr["on_face"] else (255, 120, 0, 255)
                    d.line([tuple(rr["run"][0]), tuple(rr["run"][1])], fill=col, width=6)
        x0, y0 = bbox[0] - pad, bbox[1] - pad
        x1, y1 = bbox[2] + pad, bbox[3] + pad
        cb = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
        crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
        w, h = crop.size
        sc = min(1400 / w, 1000 / h, max_scale)
        crop = crop.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        b = [round(v) for v in poly.bounds]
        lines = [f"{slug} {name} component {b} recess verdict {verdict}"]
        if r["candidates"]:
            cd = r["candidates"][0]
            lines.append(f"recess candidate: band th {cd['th']} gap cover {cd['gap_cover']} depth {cd['depth_bands']}x the band")
            lines.append(f"EXTENT reading: back {cd['back']} (2 +- 1.5 wanted) -> {'recess' if cd['extent_ok'] else 'not a recess'}")
            lines.append(f"RUNS reading: face alone {cd['face_own']}, with caps {cd['caps_own']} of the component's own extent "
                         f"(over the gap {cd['face_gap']} / {cd['caps_gap']})")
        else:
            lines.append("no recess candidate: no collinear segment pair's gap rect passes the")
            lines.append("intersect / opening / gap-cover / depth gates — both readings False")
        lines.append("red = component; yellow = the candidate's gap rect; thick green = back run at the standoff,")
        lines.append("thick orange = on a solid's flat end; blue = segment solids; thin green / orange = paired / lone faces;")
        lines.append("magenta / cyan = door / window seals")
        width = max(crop.width, 700)
        capt = Image.new("RGB", (width, crop.height + 14 * len(lines) + 8), (255, 255, 255))
        capt.paste(crop, (0, 0))
        dd = ImageDraw.Draw(capt)
        for i, t in enumerate(lines):
            dd.text((4, crop.height + 4 + 14 * i), t[:200], fill=(0, 0, 0) if i < len(lines) - 3 else (60, 60, 60))
        path = out_dir / f"{tag}_{slug}_{name}.png"
        capt.save(path)
        print("wrote", path, capt.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "step17")
