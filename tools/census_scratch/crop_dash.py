"""crop_dash.py <slug> <name> X0 Y0 X1 Y1 [...]: crop the latest sweep render
with the BASELINE snapshot's rooms (green), the latest sweep's rooms (red)
and the pieces _dash_row_indices flags (blue) — the step-6 mechanism crop."""
import glob, json, sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
try:
    from detection.walls import _dash_row_indices  # noqa: E402
except ImportError:  # the step-6 rule is held as a patch; nothing to highlight
    def _dash_row_indices(paths, marks=None, **kw):
        return set()
from PIL import Image, ImageDraw  # noqa: E402

OUT = sys.argv[1] if sys.argv[1].endswith("/") else None
args = sys.argv[2:] if OUT else sys.argv[1:]
if OUT is None:
    OUT = "/private/tmp/claude-501/-Users-danielszweda-Documents-GitHub-UD-agent/7245dfa4-9986-438f-b2d2-f0512dd602aa/scratchpad/"
slug = args[0]
boxes = []
i = 1
while i + 4 < len(args) + 0 and i < len(args):
    boxes.append((args[i], tuple(float(v) for v in args[i + 1:i + 5])))
    i += 5
pg = H.load(slug)[0]
flag = _dash_row_indices(pg.page_data.paths)
bdir = sorted(glob.glob(f"/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress_baseline/{slug}/*"))[-1]
adir = sorted(glob.glob(f"/Users/danielszweda/Documents/GitHub/UD/agent/outputs/regress/{slug}/*"))[-1]
be = json.load(open(f"{bdir}/pages/page_01/final_entities.json"))["entities"]
ae = json.load(open(f"{adir}/pages/page_01/final_entities.json"))["entities"]
im = Image.open(f"{adir}/pages/page_01/render.png").convert("RGB")
d = ImageDraw.Draw(im)
for p in pg.page_data.paths:
    if p.path_index in flag:
        d.line([p.points[0], p.points[-1]], fill=(0, 90, 255), width=4)
for e in be:
    if e["entity_type"] == "room":
        poly = e["attributes"]["polygon"]
        d.line([tuple(q) for q in poly] + [tuple(poly[0])], fill=(0, 170, 0), width=3)
        b = e["bbox"]; d.text((b[0] + 3, b[1] + 3), "base " + e["entity_id"][-4:], fill=(0, 120, 0))
for e in ae:
    if e["entity_type"] == "room":
        poly = e["attributes"]["polygon"]
        d.line([tuple(q) for q in poly] + [tuple(poly[0])], fill=(220, 0, 0), width=2)
        b = e["bbox"]; d.text((b[0] + 3, b[3] - 12), "rule " + e["entity_id"][-4:], fill=(180, 0, 0))
for name, (x0, y0, x1, y1) in boxes:
    m = 60
    crop = im.crop((max(0, x0 - m), max(0, y0 - m), x1 + m, y1 + m))
    path = f"{OUT}{slug}_{name}.png"
    crop.save(path)
    print("saved", path, crop.size)
