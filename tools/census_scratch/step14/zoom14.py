"""Zoom crops for the step-14 report: a room's polygon (red) from the named
sweep run (baseline snapshot or the latest sweep) on that run's render, every
entrance seal the census recorded for it (green, with its run in px) and any
extra boxes (orange — doors, windows). Plan crops only; every target lies
inside a floor plan.

Usage: .venv/bin/python tools/census_scratch/step14/zoom14.py OUT_DIR
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# (slug, name, room bbox, run, extra orange boxes, pad, max scale)
TARGETS = [
    # s04: the recorded-FP box the rule drops — its only entrance seal is
    # door_0000's plug tail running 13.5px along the box's left edge — and the
    # stair flight on the other side of window_0004 that returns in its place
    # (a recorded FP too; it was the door-less side of the window while the
    # box was the door-bearing side).
    ("s04", "box_dropped_tail_run_13px", (1463, 1042, 1558, 1131), "base",
     [((1558, 1047, 1588, 1131), "window_0004 0.62"), ((1371, 957, 1461, 1047), "door_0000 0.67")], 70, 4.0),
    ("s04", "stair_flight_returned_recorded_fp", (1588, 1053, 1762, 1131), "after",
     [((1558, 1047, 1588, 1131), "window_0004 0.62")], 70, 4.0),
    # s17: the four reveal strips — entrance-less now (runs 7-10px), still
    # emitted (their rotated rectangles are pinned by the 31.5px tabs and
    # their 328-343mm spacing is over the cap).
    ("s17", "reveal_strip_0013_now_entrance_less", (912, 2174, 947, 2331), "after", [], 60, 3.0),
    ("s17", "reveal_strip_0014_now_entrance_less", (3047, 2174, 3084, 2489), "after", [], 60, 3.0),
    ("s17", "reveal_strip_0027_now_entrance_less", (3047, 2594, 3084, 3061), "after", [], 60, 3.0),
    ("s17", "reveal_strip_0032_now_entrance_less", (914, 2609, 949, 3061), "after", [], 60, 3.0),
    # The true class's floor: the confirmed entered rooms with the smallest
    # largest-run at f=1.0 (s03, 59.2px) and at f=0.5 (s11, 36.5px).
    ("s03", "true_floor_confirmed_run_59px", (1077, 1011, 1187, 1121), "after", [], 70, 4.0),
    ("s11", "true_floor_confirmed_run_36px_f05", (1980, 1131, 2098, 1217), "after", [], 70, 4.0),
]


def _run_dir(slug, run):
    root = REPO / "outputs" / ("regress_baseline" if run == "base" else "regress") / slug
    return sorted(glob.glob(str(root / "*")))[-1]


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _polygon(run_dir, bbox):
    ents = json.load(open(f"{run_dir}/pages/page_01/final_entities.json"))
    items = ents["entities"] if isinstance(ents, dict) and "entities" in ents else ents
    best = None
    for e in items:
        if e["entity_type"] != "room":
            continue
        v = _iou(tuple(e["bbox"]), bbox)
        if v >= 0.5 and (best is None or v > best[0]):
            attrs = e.get("attributes") or e.get("evidence") or {}
            best = (v, attrs.get("polygon"), e.get("entity_id") or e.get("candidate_id"), e["confidence"])
    return best


def _census_room(slug, bbox):
    for f in HERE.glob("entrance_census_*.json"):
        for r in json.loads(f.read_text()):
            if r["slug"] != slug:
                continue
            for rm in r["rooms"]:
                if _iou(tuple(rm["bbox"]), bbox) >= 0.5:
                    return rm
    return None


def main(out_dir, targets=TARGETS):
    out_dir.mkdir(parents=True, exist_ok=True)
    for slug, name, bbox, run, extras, pad, max_scale in targets:
        rd = _run_dir(slug, run)
        img = Image.open(f"{rd}/pages/page_01/render.png").convert("RGBA")
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        poly = _polygon(rd, bbox)
        if poly and poly[1]:
            d.polygon([tuple(p) for p in poly[1]], outline=(220, 0, 0, 255), width=2)
        else:
            d.rectangle(bbox, outline=(220, 0, 0, 255), width=2)
        rm = _census_room(slug, bbox)
        seal_boxes = []
        if rm:
            for s in rm["seals"]:
                d.rectangle(s["seal_bbox"], outline=(0, 160, 0, 255), width=2)
                seal_boxes.append(s["seal_bbox"])
        for eb, _label in extras:
            d.rectangle(eb, outline=(240, 140, 0, 255), width=2)
        allb = [bbox] + [e for e, _ in extras] + seal_boxes
        x0 = min(b[0] for b in allb) - pad
        y0 = min(b[1] for b in allb) - pad
        x1 = max(b[2] for b in allb) + pad
        y1 = max(b[3] for b in allb) + pad
        cb = (max(0, int(x0)), max(0, int(y0)), min(img.width, int(x1)), min(img.height, int(y1)))
        crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
        w, h = crop.size
        sc = min(1200 / w, 900 / h, max_scale)
        crop = crop.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
        cap = Image.new("RGB", (crop.width, crop.height + 50), (255, 255, 255))
        cap.paste(crop, (0, 0))
        dd = ImageDraw.Draw(cap)
        line = f"{slug} {name} bbox {list(bbox)} ({run} run"
        if poly:
            line += f", {poly[2]} conf {poly[3]}"
        line += ")"
        if rm:
            line += (f"  gt={rm['gt']} area {rm['area']} doors {rm['door_count']} win {rm['window_count']} "
                     f"entrances any-touch {rm['old_entrance_count']} -> run-gated {rm['new_entrance_count']}; "
                     f"largest run {rm['max_run_px']}px")
        line2 = "green = entrance seal: " + "; ".join(
            f"{s['seal_bbox']} conf {s['conf']} contact {s['contact_px']}px run {s['run_px']}px" for s in (rm["seals"] if rm else [])
        )
        for eb, label in extras:
            line2 += f"  orange: {label} {list(eb)}"
        dd.text((4, crop.height + 4), line[:240], fill=(0, 0, 0))
        dd.text((4, crop.height + 18), line2[:240], fill=(0, 100, 0))
        dd.text((4, crop.height + 32), "red = room polygon, green = entrance seals (census), orange = named openings", fill=(90, 90, 90))
        path = out_dir / f"step14_{slug}_{name}.png"
        cap.save(path)
        print("wrote", path, cap.size)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
