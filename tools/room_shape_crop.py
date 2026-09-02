"""Before|after crop of ONE room's outline change — the picture behind a
`tools/compare_room_shapes.py` SHAPE line or a `tools/diff_room_polygons.py`
SHAPE / ADDED / REMOVED line.

Draws the baseline polygon (red) and the latest sweep's polygon (green) on the
page render, twice: zoomed 4x on the symmetric difference, and the whole room.
Baseline = outputs/regress_baseline/<slug> (tools/compare_sweeps.py --snapshot),
after = the latest outputs/regress/<slug> run.

Room ids are ordinal and shift between runs, so the counterpart is found by
best IoU unless --after names it. A room present in only one run (an ADDED or
REMOVED line) is drawn alone with --only after / --only before.

Usage:
    python tools/room_shape_crop.py s03 room_0011 [--page 1]
    python tools/room_shape_crop.py s01 room_0007 --after room_0006
    python tools/room_shape_crop.py s17 room_0022 --only after     # an ADDED room
    python tools/room_shape_crop.py s18 room_0004 --only before    # a REMOVED room

Writes outputs/compare/<slug>/page_NN_shape_<room>_{zoom,room}.png. Run it
AFTER tools/compare_sweeps.py <slug> — that tool wipes outputs/compare/<slug>/
before writing its own images.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]


def _latest(pattern: str) -> str | None:
    runs = sorted(glob.glob(pattern))
    return runs[-1] if runs else None


def _rooms(run_dir: str, page: int) -> dict[str, Polygon]:
    d = json.load(open(f"{run_dir}/pages/page_{page:02d}/final_entities.json"))
    return {
        e["entity_id"]: Polygon(e["attributes"]["polygon"])
        for e in d["entities"]
        if e["entity_type"] == "room" and e.get("attributes", {}).get("polygon")
    }


def _best_match(poly: Polygon, candidates: dict[str, Polygon]) -> tuple[str | None, float]:
    best, best_iou = None, 0.0
    for rid, other in candidates.items():
        inter = poly.intersection(other).area
        if inter <= 0:
            continue
        iou = inter / poly.union(other).area
        if iou > best_iou:
            best, best_iou = rid, iou
    return best, best_iou


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("room", help="entity id in the BASELINE run (or the after run with --only after)")
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--after", help="the counterpart's id in the latest run (default: best IoU)")
    ap.add_argument("--only", choices=("before", "after"),
                    help="draw a room present in only one run")
    args = ap.parse_args()

    base = _latest(f"{ROOT}/outputs/regress_baseline/{args.slug}/*")
    after = _latest(f"{ROOT}/outputs/regress/{args.slug}/*")
    if not base or not after:
        raise SystemExit(f"{args.slug}: missing baseline snapshot or latest run")
    rooms_b, rooms_a = _rooms(base, args.page), _rooms(after, args.page)

    pb: Polygon | None = None
    pa: Polygon | None = None
    if args.only == "after":
        pa = rooms_a.get(args.room) or _missing(args.room, after)
    elif args.only == "before":
        pb = rooms_b.get(args.room) or _missing(args.room, base)
    else:
        pb = rooms_b.get(args.room) or _missing(args.room, base)
        if args.after:
            pa = rooms_a.get(args.after) or _missing(args.after, after)
            after_id = args.after
        else:
            after_id, iou = _best_match(pb, rooms_a)
            if after_id is None or iou < 0.5:
                raise SystemExit(f"{args.room}: no counterpart at IoU >= 0.5 in {after} "
                                 f"— a REMOVED room; use --only before")
            pa = rooms_a[after_id]
            if after_id != args.room:
                print(f"{args.room} matched {after_id} in the latest run (IoU {iou:.3f})")

    if pb is not None and pa is not None:
        diff = pb.symmetric_difference(pa)
        zoom_bounds = diff.bounds if not diff.is_empty else pa.bounds
        room_bounds = pb.union(pa).bounds
        print(f"{args.slug} {args.room}: area {pb.area:.0f} -> {pa.area:.0f} px^2, "
              f"symmetric difference {diff.area:.0f} px^2 at {[round(v) for v in diff.bounds]}")
    else:
        only = pb if pb is not None else pa
        zoom_bounds = room_bounds = only.bounds
        print(f"{args.slug} {args.room} ({args.only} only): area {only.area:.0f} px^2, "
              f"bounds {[round(v) for v in only.bounds]}")

    render = Image.open(f"{after}/pages/page_{args.page:02d}/render.png").convert("RGB")
    out_dir = f"{ROOT}/outputs/compare/{args.slug}"
    os.makedirs(out_dir, exist_ok=True)

    def panel(poly: Polygon | None, colour, bounds, margin: float, scale: int) -> Image.Image:
        x0, y0, x1, y1 = bounds
        x0, y0 = max(0, int(x0 - margin)), max(0, int(y0 - margin))
        x1, y1 = min(render.width, int(x1 + margin)), min(render.height, int(y1 + margin))
        crop = render.crop((x0, y0, x1, y1)).resize(
            ((x1 - x0) * scale, (y1 - y0) * scale), Image.LANCZOS
        )
        if poly is not None:
            ImageDraw.Draw(crop).line(
                [((x - x0) * scale, (y - y0) * scale) for x, y in poly.exterior.coords],
                fill=colour, width=3,
            )
        return crop

    for tag, bounds, margin, scale in (
        ("zoom", zoom_bounds, 30, 4), ("room", room_bounds, 20, 1),
    ):
        b = panel(pb, (220, 0, 0), bounds, margin, scale)
        a = panel(pa, (0, 160, 0), bounds, margin, scale)
        img = Image.new("RGB", (b.width + a.width + 10, max(b.height, a.height)), "white")
        img.paste(b, (0, 0))
        img.paste(a, (b.width + 10, 0))
        path = f"{out_dir}/page_{args.page:02d}_shape_{args.room}_{tag}.png"
        img.save(path)
        print("wrote", path)


def _missing(rid: str, run_dir: str):
    raise SystemExit(f"{rid} is not a room of {run_dir}")


if __name__ == "__main__":
    main()
