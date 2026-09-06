"""Attribute every room the 40 cap moves, removes or adds (band_census*.json)
to the network segments that changed near it: per room, the NEW segments
(blue) and LOST segments (orange) whose band touches the room's bbox grown by
REACH, printed and drawn on a crop of the baseline render with the room's
before box (red) and after box (green). Tiles are paged into contact sheets.

Usage: .venv/bin/python tools/census_scratch/step4/attribute_rooms.py OUT_DIR [slug ...]
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
REACH = 12.0
PAD = 70
TILE = 400
COLS = 3
PER_PAGE = 12


def _render(slug, page):
    runs = sorted(glob.glob(str(REPO / "outputs" / "regress_baseline" / slug / "*")))
    return Image.open(f"{runs[-1]}/pages/page_{page:02d}/render.png").convert("RGBA")


def _band_poly(seg):
    (x1, y1), (x2, y2) = seg["p1"], seg["p2"]
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    th = max(seg["th"], 2.0)
    nx, ny = -(y2 - y1) / L * th / 2, (x2 - x1) / L * th / 2
    return [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]


def _touches(seg, bbox):
    x0, y0, x1, y1 = bbox[0] - REACH, bbox[1] - REACH, bbox[2] + REACH, bbox[3] + REACH
    xs = [p[0] for p in _band_poly(seg)]
    ys = [p[1] for p in _band_poly(seg)]
    return not (max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1)


def attribute(records, out_dir, slugs):
    out_dir.mkdir(parents=True, exist_ok=True)
    for rec in records:
        if slugs and rec["slug"] not in slugs:
            continue
        rooms = ([("GONE", r["bbox"], None, r) for r in rec["rooms_gone"]]
                 + [("NEW", r["bbox"], r["bbox"], r) for r in rec["rooms_new"]]
                 + [("MOVED", r["bbox"], r["after_bbox"], r) for r in rec["rooms_moved"]])
        if not rooms:
            continue
        img = _render(rec["slug"], rec["page"])
        tiles = []
        print(f"== {rec['slug']} p{rec['page']} f={rec['factor']}")
        for kind, before, after, r in rooms:
            box = before if after is None else [min(before[0], after[0]), min(before[1], after[1]),
                                                max(before[2], after[2]), max(before[3], after[3])]
            new = [s for s in rec["segments_new"] if _touches(s, box)]
            lost = [s for s in rec["segments_lost"] if _touches(s, box)]
            extra = (f" lost {r['lost']} gained {r['gained']} iou {r['iou']}" if kind == "MOVED"
                     else f" area {r['area']}" + (f" conf {r['conf']} doors {r['doors']}" if kind == "NEW" else ""))
            print(f"  {kind} {before}{extra}")
            for s in new:
                print(f"      + seg th {s['th']} len {s['len']} at {s['mid']} stroked={s['stroked']} faces={s['faces'][:4]}")
            for s in lost:
                print(f"      - seg th {s['th']} len {s['len']} at {s['mid']}")
            over = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(over)
            for s in lost:
                d.polygon(_band_poly(s), fill=(255, 150, 0, 110))
            for s in new:
                d.polygon(_band_poly(s), fill=(40, 90, 255, 120))
            d.rectangle(before, outline=(220, 0, 0, 255), width=2)
            if after is not None:
                d.rectangle(after, outline=(0, 160, 0, 255), width=2)
            crop_box = (max(0, int(box[0] - PAD)), max(0, int(box[1] - PAD)),
                        min(img.width, int(box[2] + PAD)), min(img.height, int(box[3] + PAD)))
            crop = Image.alpha_composite(img, over).crop(crop_box).convert("RGB")
            w, h = crop.size
            scale = min((TILE - 10) / w, (TILE - 10) / h, 1.0)
            crop = crop.resize((max(1, int(w * scale)), max(1, int(h * scale))))
            tile = Image.new("RGB", (TILE, TILE + 28), (255, 255, 255))
            tile.paste(crop, (5, 5))
            ImageDraw.Draw(tile).text((5, TILE - 2), f"{kind} {before} +{len(new)} -{len(lost)}{extra[:40]}",
                                      fill=(0, 0, 0))
            tiles.append(tile)
        for pg in range(0, len(tiles), PER_PAGE):
            chunk = tiles[pg:pg + PER_PAGE]
            rows = (len(chunk) + COLS - 1) // COLS
            board = Image.new("RGB", (COLS * TILE, rows * (TILE + 28)), (255, 255, 255))
            for i, t in enumerate(chunk):
                board.paste(t, ((i % COLS) * TILE, (i // COLS) * (TILE + 28)))
            path = out_dir / f"{rec['slug']}_rooms_p{pg // PER_PAGE + 1}.png"
            board.save(path)
            print("  wrote", path)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    slugs = set(sys.argv[2:])
    recs = []
    for f in HERE.glob("band_census*.json"):
        recs.extend(json.loads(f.read_text()))
    attribute(recs, out, slugs)
