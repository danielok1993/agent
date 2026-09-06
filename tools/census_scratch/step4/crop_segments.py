"""Contact sheets for classing what the 40 cap admits (band_census*.json):
one tiled image per slug and mode — every CANDIDATE pair (the base run's
wide_pairs in the 36f–40f band, with its material / through verdicts) or
every ADMITTED segment (final network segments present only at cap x40/36)
— each tile a crop of the baseline sweep's render.png around the pair, the
pair drawn as a half-transparent blue band, rooms it moved / removed /
added boxed (red = gone or before, green = new or after). Pictures go to the
scratch directory given on the command line, never the repo — the report
copies the few it cites under docs/w-gate-iter3-checkpoints/.

Usage: .venv/bin/python tools/census_scratch/step4/crop_segments.py OUT_DIR {cand|new} [slug ...]
"""
from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAD = 150
TILE = 330
COLS = 4


def _render(slug, page):
    runs = sorted(glob.glob(str(REPO / "outputs" / "regress_baseline" / slug / "*")))
    return Image.open(f"{runs[-1]}/pages/page_{page:02d}/render.png").convert("RGBA")


def _band(draw, p1, p2, th, color):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = -(y2 - y1) / L * th / 2, (x2 - x1) / L * th / 2
    draw.polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)],
                 fill=color)


def _tile(img, rec, item, label):
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    _band(d, item["p1"], item["p2"], max(item["th"], 2.0), (40, 90, 255, 110))
    for r in rec["rooms_gone"]:
        d.rectangle(r["bbox"], outline=(220, 0, 0, 255), width=3)
    for r in rec["rooms_moved"]:
        d.rectangle(r["bbox"], outline=(220, 0, 0, 200), width=2)
        d.rectangle(r["after_bbox"], outline=(0, 160, 0, 200), width=2)
    for r in rec["rooms_new"]:
        d.rectangle(r["bbox"], outline=(0, 160, 0, 255), width=3)
    cx, cy = item["mid"]
    box = (max(0, int(cx - PAD)), max(0, int(cy - PAD)),
           min(img.width, int(cx + PAD)), min(img.height, int(cy + PAD)))
    crop = Image.alpha_composite(img, over).crop(box).convert("RGB")
    crop = crop.resize((TILE - 10, TILE - 10))
    tile = Image.new("RGB", (TILE, TILE + 28), (255, 255, 255))
    tile.paste(crop, (5, 5))
    ImageDraw.Draw(tile).text((5, TILE - 2), label, fill=(0, 0, 0))
    return tile


def sheet(slug, records, mode, out_dir):
    tiles = []
    for rec in records:
        if rec["slug"] != slug:
            continue
        img = _render(slug, rec["page"])
        items = rec["candidates"] if mode == "cand" else rec["segments_new"]
        for k, it in enumerate(items):
            if mode == "cand":
                label = (f"c{k} th{it['th']:.1f} len{it['len']:.0f} @{it['mid'][0]},{it['mid'][1]} "
                         f"str={int(bool(it['stroked']))} fill={int(bool(it['fill']))} "
                         f"mat={it.get('material')} thr={it.get('through')}")
            else:
                label = (f"n{k} th{it['th']:.1f} len{it['len']:.0f} @{it['mid'][0]:.0f},{it['mid'][1]:.0f} "
                         f"str={int(it['stroked'])} faces={it['faces'][:3]}")
            tiles.append(_tile(img, rec, it, label))
    if not tiles:
        return None
    rows = (len(tiles) + COLS - 1) // COLS
    board = Image.new("RGB", (COLS * TILE, rows * (TILE + 28)), (255, 255, 255))
    for i, t in enumerate(tiles):
        board.paste(t, ((i % COLS) * TILE, (i // COLS) * (TILE + 28)))
    path = out_dir / f"{slug}_{mode}_sheet.png"
    board.save(path)
    return path, len(tiles)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[2]
    slugs = sys.argv[3:]
    recs = []
    for f in HERE.glob("band_census*.json"):
        recs.extend(json.loads(f.read_text()))
    for slug in slugs or sorted({r["slug"] for r in recs}):
        res = sheet(slug, recs, mode, out)
        if res:
            print(slug, mode, res[1], "tiles ->", res[0])
