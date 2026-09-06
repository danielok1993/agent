"""Zoom crops for step 16: a component (red) on the sweep render with the
stage's own barrier evidence overlaid — every wall SEGMENT's solid outline
(blue, its band), every barrier FACE extent (green where the face belongs to
a paired segment, orange where it is a lone face), door seals (magenta) and
window seals (cyan) — so what bounds each side of a pocket can be read off
the picture. Plan crops only; every target lies inside a floor plan.

Usage: .venv/bin/python tools/census_scratch/step16/zoom16.py OUT_DIR [tag]
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import LineString, box

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import harness as H  # noqa: E402

from detection import rooms  # noqa: E402

# (slug, name, component bbox, pad, max scale)
TARGETS = [
    ("s17", "reveal_strip_0013_context", (912, 2174, 947, 2331), 110, 2.5),
    ("s17", "reveal_strip_0032_context", (914, 2609, 949, 3061), 110, 1.6),
    ("s17", "reveal_strip_0014_context", (3047, 2174, 3084, 2489), 110, 1.8),
    ("s17", "reveal_strip_0027_context", (3047, 2594, 3084, 3061), 110, 1.4),
    ("s17", "reveal_25px_dropped_context", (3434, 2186, 3579, 2207), 90, 2.5),
    ("s11", "storage_in_utility_context", (1078, 1597, 1095, 1704), 90, 3.0),
    ("s18", "kitchen_corner_box_context", (2079, 1023, 2096, 1068), 80, 3.0),
    ("s16", "partition_box_context", (2507, 1323, 2527, 1401), 80, 3.0),
    ("s12", "unit_cell_442_context", (1842, 472, 1873, 494), 80, 3.0),
    ("s12", "unit_cell_470_context", (1842, 530, 1873, 554), 80, 3.0),
    ("s18", "sofa_strip_context", (907, 810, 1079, 833), 80, 2.5),
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
    cap = {"calls": []}
    o_fsc, o_drop, o_pocket = (rooms._free_space_components,
                               rooms._drop_window_exterior_sides, rooms._is_band_pocket)

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        for k in ("face_lines", "cap_lines", "wall_segments", "network", "door_barriers",
                  "window_barriers", "solid_parts"):
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
    return cap


def _draw_geom(d, g, colour, width):
    for piece in getattr(g, "geoms", [g]):
        if piece.is_empty:
            continue
        if piece.geom_type == "Polygon":
            d.polygon([tuple(p) for p in piece.exterior.coords], outline=colour, width=width)
        elif piece.geom_type == "LineString":
            d.line([tuple(p) for p in piece.coords], fill=colour, width=width)


def main(out_dir, tag="step16", targets=TARGETS):
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
        d.polygon([tuple(p) for p in poly.exterior.coords], outline=(220, 0, 0, 255), width=3)
        x0, y0 = bbox[0] - pad, bbox[1] - pad
        x1, y1 = bbox[2] + pad, bbox[3] + pad
        cb = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
        crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
        w, h = crop.size
        sc = min(1400 / w, 1000 / h, max_scale)
        crop = crop.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        capt = Image.new("RGB", (crop.width, crop.height + 36), (255, 255, 255))
        capt.paste(crop, (0, 0))
        dd = ImageDraw.Draw(capt)
        b = [round(v) for v in poly.bounds]
        dd.text((4, crop.height + 4), f"{slug} {name} component {b}"[:200], fill=(0, 0, 0))
        dd.text((4, crop.height + 18),
                "red = component; blue = wall SEGMENT solids (light blue: fills / white walls / jamb rings); "
                "green = paired face, orange = lone face; magenta = door seal, cyan = window seal", fill=(60, 60, 60))
        path = out_dir / f"{tag}_{slug}_{name}.png"
        capt.save(path)
        print("wrote", path, capt.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "step16")
