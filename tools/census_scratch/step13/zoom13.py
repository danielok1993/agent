"""Zoom crops for the step-13 report: named boxes on the baseline render with
the component bbox (red), its minimum rotated rectangle (blue, from the
census JSONs when recorded) and any extra boxes (green — door bboxes,
entrance seals). Plan crops only; every target lies inside a floor plan.

Usage: .venv/bin/python tools/census_scratch/step13/zoom13.py OUT_DIR
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# (slug, name, component bbox, extra green boxes, pad, max scale)
TARGETS = [
    ("s11", "storage_in_utility_confirmed_368mm", (1078, 1597, 1095, 1704),
     [((1102, 1670, 1147, 1715), "door_0009 0.67")], 70, 4.0),
    ("s12", "kitchen_unit_cell_442mm", (1842, 472, 1873, 494), [], 60, 4.0),
    ("s12", "kitchen_unit_cell_470mm", (1842, 530, 1873, 554), [], 60, 4.0),
    ("s16", "bathroom_box_406mm", (2507, 1323, 2527, 1401), [], 60, 4.0),
    ("s18", "kitchen_corner_box_360mm", (2079, 1023, 2096, 1068), [], 60, 4.0),
    ("s07", "cupboard_confirmed_610mm", (454, 190, 486, 290), [], 70, 4.0),
    ("s20", "passage_confirmed_599mm", (554, 2812, 948, 2878), [], 70, 3.0),
    ("s15", "space_confirmed_601mm", (766, 1549, 833, 1669), [], 70, 3.0),
    # s17's reveal strips with the 0.95 doorway seal that touches each one's
    # end (green) — the entrance gate, not the ceiling, holds them out.
    ("s17", "reveal_strip_0013_with_entrance_seal", (912, 2174, 947, 2331),
     [((932, 2331, 942, 2441), "door_0025 seal, contact 18px")], 60, 3.0),
    ("s17", "reveal_strip_0014_with_entrance_seal", (3047, 2174, 3084, 2489),
     [((2934, 2458, 3049, 2465), "door_0002 seal, contact 15px")], 60, 3.0),
]


def _render(slug):
    runs = sorted(glob.glob(str(REPO / "outputs" / "regress_baseline" / slug / "*")))
    return Image.open(f"{runs[-1]}/pages/page_01/render.png").convert("RGBA")


def _mrr_for(slug, bbox):
    for f in HERE.glob("pocket_census*.json"):
        for r in json.loads(f.read_text()):
            if r["slug"] != slug:
                continue
            for c in r["calls"]:
                b = c["bbox"]
                if all(abs(b[i] - bbox[i]) <= 3 for i in range(4)) and c.get("mrr"):
                    return c["mrr"], c
    return None, None


def main(out_dir, targets=TARGETS):
    out_dir.mkdir(parents=True, exist_ok=True)
    for slug, name, bbox, extras, pad, max_scale in targets:
        img = _render(slug)
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        mrr, rec = _mrr_for(slug, bbox)
        if mrr:
            d.polygon([tuple(p) for p in mrr], outline=(40, 90, 255, 255), width=2)
        d.rectangle(bbox, outline=(220, 0, 0, 255), width=1)
        for eb, _label in extras:
            d.rectangle(eb, outline=(0, 160, 0, 255), width=2)
        x0 = min([bbox[0]] + [e[0] for e, _ in extras]) - pad
        y0 = min([bbox[1]] + [e[1] for e, _ in extras]) - pad
        x1 = max([bbox[2]] + [e[2] for e, _ in extras]) + pad
        y1 = max([bbox[3]] + [e[3] for e, _ in extras]) + pad
        cb = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
        crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
        w, h = crop.size
        sc = min(1200 / w, 900 / h, max_scale)
        crop = crop.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        cap = Image.new("RGB", (crop.width, crop.height + 36), (255, 255, 255))
        cap.paste(crop, (0, 0))
        dd = ImageDraw.Draw(cap)
        line = f"{slug} {name} bbox {list(bbox)}"
        if rec:
            line += (f"  short {rec['short']}px spacing {rec['spacing']}px ({rec['spacing_mm']}mm) "
                     f"covers {rec['covers']} gt={rec['gt']}")
        for eb, label in extras:
            line += f"  green: {label} {list(eb)}"
        dd.text((4, crop.height + 4), line[:230], fill=(0, 0, 0))
        dd.text((4, crop.height + 18), "red = component bbox, blue = minimum rotated rectangle", fill=(90, 90, 90))
        path = out_dir / f"step13_{slug}_{name}.png"
        cap.save(path)
        print("wrote", path, cap.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
