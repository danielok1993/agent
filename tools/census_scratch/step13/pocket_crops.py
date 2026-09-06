"""Contact sheets of every component the step-13 pocket census recorded
(pocket_census*.json): per slug, one tile per `_is_band_pocket` call — the
component's bbox (red), its minimum rotated rectangle (blue), and a caption
with the short side, the face spacing, both long-edge covers, the ground-truth
class and the census verdict. Tiles are ordered in_band DROP, in_band keep,
under_cap, over_thick, so the population the raised ceiling would remove
comes first. Crops come from the baseline sweep's render
(outputs/regress_baseline/<slug>/<latest>/pages/page_NN/render.png).

Usage: .venv/bin/python tools/census_scratch/step13/pocket_crops.py OUT_DIR [slug ...] [--band in_band,under_cap,...]
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PAD = 60
TILE = 380
COLS = 4
PER_PAGE = 16
ORDER = {"in_band": 0, "under_cap": 1, "over_thick": 2, "degenerate": 3}


def _render(slug, page):
    runs = sorted(glob.glob(str(REPO / "outputs" / "regress_baseline" / slug / "*")))
    return Image.open(f"{runs[-1]}/pages/page_{page:02d}/render.png").convert("RGBA")


def tiles_for(rec, bands):
    img = _render(rec["slug"], rec["page"])
    calls = [c for c in rec["calls"] if c["band"] in bands]
    calls.sort(key=lambda c: (ORDER.get(c["band"], 9), not c["would_drop"], c.get("spacing") or 0))
    out = []
    for c in calls:
        b = c["bbox"]
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        if c.get("mrr"):
            d.polygon([tuple(p) for p in c["mrr"]], outline=(40, 90, 255, 255), width=2)
        d.rectangle(b, outline=(220, 0, 0, 255), width=1)
        crop_box = (max(0, int(b[0] - PAD)), max(0, int(b[1] - PAD)),
                    min(img.width, int(b[2] + PAD)), min(img.height, int(b[3] + PAD)))
        crop = Image.alpha_composite(img, over).crop(crop_box).convert("RGB")
        w, h = crop.size
        scale = min((TILE - 10) / w, (TILE - 10) / h, 2.0)
        crop = crop.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        tile = Image.new("RGB", (TILE, TILE + 44), (255, 255, 255))
        tile.paste(crop, (5, 5))
        dd = ImageDraw.Draw(tile)
        verdict = "DROP" if c["would_drop"] else ("dropped@cap" if c["res_cap"] else "keep")
        cov = c.get("covers")
        dd.text((5, TILE - 2), f"{rec['slug']} {[round(v) for v in b]} {c['band']} {verdict} gt={c['gt']}",
                fill=(0, 0, 0))
        dd.text((5, TILE + 12), f"short {c.get('short')} sp {c.get('spacing')} ({c.get('spacing_mm')}mm) "
                                f"cov {cov} text={c['text']} area {c['area']}", fill=(0, 0, 0))
        dd.text((5, TILE + 26), (c.get("gt_note") or "")[:70], fill=(90, 90, 90))
        out.append(tile)
    return out


def main(out_dir, slugs, bands):
    out_dir.mkdir(parents=True, exist_ok=True)
    recs = []
    for f in HERE.glob("pocket_census*.json"):
        recs.extend(json.loads(f.read_text()))
    for rec in recs:
        if slugs and rec["slug"] not in slugs:
            continue
        tiles = tiles_for(rec, bands)
        if not tiles:
            continue
        for pg in range(0, len(tiles), PER_PAGE):
            chunk = tiles[pg:pg + PER_PAGE]
            rows = (len(chunk) + COLS - 1) // COLS
            board = Image.new("RGB", (COLS * TILE, rows * (TILE + 44)), (255, 255, 255))
            for i, t in enumerate(chunk):
                board.paste(t, ((i % COLS) * TILE, (i // COLS) * (TILE + 44)))
            path = out_dir / f"{rec['slug']}_p{rec['page']}_pockets_{pg // PER_PAGE + 1}.png"
            board.save(path)
            print("wrote", path, len(chunk), "tiles")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--band")]
    band_arg = [a for a in sys.argv[1:] if a.startswith("--band")]
    bands = set(band_arg[0].split("=", 1)[1].split(",")) if band_arg else set(ORDER)
    main(Path(args[0]), set(args[1:]), bands)
