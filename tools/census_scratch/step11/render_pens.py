"""Render each stroke pen's face ink (network.faces, stroked) over the sweep's
render.png, one PNG per sheet, plus the confident doors/windows, so the census
can say what each pen IS. Scratch only — writes to the scratchpad dir.

Usage: .venv/bin/python tools/census_scratch/step11/render_pens.py slug[@factor] ...
"""
import glob
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from PIL import Image, ImageDraw  # noqa: E402

OUT = "/private/tmp/claude-501/-Users-danielszweda-Documents-GitHub-UD-agent/2c09adae-85fa-4154-8008-ba3c8e897eae/scratchpad/pens"
PALETTE = [(255, 0, 0), (0, 120, 255), (0, 170, 0), (255, 140, 0), (170, 0, 255), (0, 190, 190), (200, 200, 0)]


def render(slug, factor, crop=None):
    import os
    os.makedirs(OUT, exist_ok=True)
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    ents, extras = H.run(page, factor=factor, keep_network=True)
    net = extras["network"]
    runs = sorted(glob.glob(f"/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress/{slug}/*/pages/page_01/render.png"))
    im = Image.open(runs[-1]).convert("RGB")
    # fade the render
    im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), 0.6)
    dr = ImageDraw.Draw(im)
    pens = sorted({fc.pen for fc in net.faces if fc.stroked and fc.pen is not None}, key=str)
    legend = []
    for i, pen in enumerate(pens):
        col = PALETTE[i % len(PALETTE)]
        legend.append((pen, col))
        for fc in net.faces:
            if fc.stroked and fc.pen == pen:
                dr.line([fc.p1, fc.p2], fill=col, width=3)
    for e in ents:
        if e["entity_type"] in ("door", "window") and e["confidence"] >= 0.55:
            x0, y0, x1, y1 = e["bbox"]
            dr.rectangle([x0, y0, x1, y1], outline=(0, 0, 0), width=2)
    y = 10
    for pen, col in legend:
        dr.rectangle([10, y, 40, y + 20], fill=col)
        dr.text((50, y + 4), f"pen {pen}", fill=(0, 0, 0))
        y += 26
    if crop:
        im = im.crop(crop)
    tag = f"{slug}_f{f:.3f}"
    im.save(f"{OUT}/{tag}.png")
    print("wrote", f"{OUT}/{tag}.png", im.size, [str(p) for p, _ in legend])


if __name__ == "__main__":
    for a in sys.argv[1:]:
        slug, _, fac = a.partition("@")
        render(slug, float(fac) if fac else None)
