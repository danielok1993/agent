"""Before|after crop of ONE room's outline change — the picture behind a
`tools/compare_room_shapes.py` SHAPE line.

Draws the baseline polygon (red) and the latest sweep's polygon (green) on the
page render, twice: zoomed 4x on the symmetric difference, and the whole room.
Baseline = outputs/regress_baseline/<slug> (tools/compare_sweeps.py --snapshot),
after = the latest outputs/regress/<slug> run.

Usage:
    python tools/room_shape_crop.py s03 room_0011 [--page 1]

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


def _room(run_dir: str, page: int, rid: str) -> Polygon:
    d = json.load(open(f"{run_dir}/pages/page_{page:02d}/final_entities.json"))
    for e in d["entities"]:
        if e["entity_id"] == rid:
            return Polygon(e["attributes"]["polygon"])
    raise SystemExit(f"{rid} is not an entity of {run_dir}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("room", help="entity id, e.g. room_0011")
    ap.add_argument("--page", type=int, default=1)
    args = ap.parse_args()

    base = _latest(f"{ROOT}/outputs/regress_baseline/{args.slug}/*")
    after = _latest(f"{ROOT}/outputs/regress/{args.slug}/*")
    if not base or not after:
        raise SystemExit(f"{args.slug}: missing baseline snapshot or latest run")
    pb, pa = _room(base, args.page, args.room), _room(after, args.page, args.room)
    diff = pb.symmetric_difference(pa)
    print(f"{args.slug} {args.room}: area {pb.area:.0f} -> {pa.area:.0f} px^2, "
          f"symmetric difference {diff.area:.0f} px^2 at {[round(v) for v in diff.bounds]}")
    render = Image.open(f"{after}/pages/page_{args.page:02d}/render.png").convert("RGB")
    out_dir = f"{ROOT}/outputs/compare/{args.slug}"
    os.makedirs(out_dir, exist_ok=True)

    def panel(poly: Polygon, colour, bounds, margin: float, scale: int) -> Image.Image:
        x0, y0, x1, y1 = bounds
        x0, y0 = max(0, int(x0 - margin)), max(0, int(y0 - margin))
        x1, y1 = min(render.width, int(x1 + margin)), min(render.height, int(y1 + margin))
        crop = render.crop((x0, y0, x1, y1)).resize(
            ((x1 - x0) * scale, (y1 - y0) * scale), Image.LANCZOS
        )
        ImageDraw.Draw(crop).line(
            [((x - x0) * scale, (y - y0) * scale) for x, y in poly.exterior.coords],
            fill=colour, width=3,
        )
        return crop

    for tag, bounds, margin, scale in (
        ("zoom", diff.bounds, 30, 4), ("room", pb.union(pa).bounds, 20, 1),
    ):
        b = panel(pb, (220, 0, 0), bounds, margin, scale)
        a = panel(pa, (0, 160, 0), bounds, margin, scale)
        img = Image.new("RGB", (b.width + a.width + 10, max(b.height, a.height)), "white")
        img.paste(b, (0, 0))
        img.paste(a, (b.width + 10, 0))
        path = f"{out_dir}/page_{args.page:02d}_shape_{args.room}_{tag}.png"
        img.save(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
