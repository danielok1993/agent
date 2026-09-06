"""Zoom crops of named boxes with the new (blue) / lost (orange) segments and before (red) / after (green) room boxes."""
import sys, json, glob
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step4")
import attribute_rooms as A
from PIL import Image, ImageDraw
OUT = "/private/tmp/claude-501/-Users-danielszweda-Documents-GitHub-UD-agent/2116b323-5650-47df-b8e3-2c21e926f912/scratchpad/s4crops/"
recs = {}
for f in glob.glob("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step4/band_census*.json"):
    for r in json.load(open(f)):
        recs[r["slug"]] = r
targets = [("s11", (626, 1115, 779, 1290), "porch"), ("s11", (1030, 1330, 1123, 1360), "recess"),
           ("s11", (1099, 1515, 1272, 1713), "utility"), ("s15", (1025, 929, 1441, 1386), "wardrobe"),
           ("s18", (156, 724, 197, 863), "boundary")]
for slug, box, name in targets:
    rec = recs[slug]; img = A._render(slug, rec["page"])
    over = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    for s in rec["segments_lost"]:
        if A._touches(s, box): d.polygon(A._band_poly(s), fill=(255, 150, 0, 120))
    for s in rec["segments_new"]:
        if A._touches(s, box): d.polygon(A._band_poly(s), fill=(40, 90, 255, 120))
    for r in rec["rooms_moved"]:
        if r["bbox"] == list(box):
            d.rectangle(r["bbox"], outline=(220, 0, 0, 255), width=2); d.rectangle(r["after_bbox"], outline=(0, 160, 0, 255), width=2)
    for r in rec["rooms_new"]:
        if r["bbox"] == list(box): d.rectangle(r["bbox"], outline=(0, 160, 0, 255), width=2)
    pad = 40
    cb = (max(0, box[0]-pad), max(0, box[1]-pad), min(img.width, box[2]+pad), min(img.height, box[3]+pad))
    crop = Image.alpha_composite(img, over).crop(cb).convert("RGB")
    w, h = crop.size; sc = min(1400 / w, 1000 / h, 4.0)
    crop = crop.resize((int(w*sc), int(h*sc)), Image.LANCZOS)
    crop.save(OUT + f"zoom_{slug}_{name}.png"); print("wrote", name, crop.size)
