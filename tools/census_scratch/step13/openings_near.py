"""Every post-suppression door / window candidate whose bbox lies within
16px of the given room bboxes, with its confidence and whether it counts as an
ENTRANCE (>= ROOM_ENTRANCE_MIN_CONFIDENCE) — the gate that decides whether
_is_band_pocket is ever called on the room. Also the room's own door /
window counts from the harness run.

Usage: .venv/bin/python openings_near.py SLUG name=x0,y0,x1,y1 [name=... ]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms
from shapely.geometry import box

slug = sys.argv[1]
targets = {a.split("=")[0]: tuple(float(v) for v in a.split("=")[1].split(",")) for a in sys.argv[2:]}
p = H.load(slug)[0]
ents, extras = H.run(p)
for c in extras["all_geo"]:
    if c.entity_type not in ("door", "window"):
        continue
    b = c.bbox
    for name, t in targets.items():
        if not (b[2] < t[0] - 16 or b[0] > t[2] + 16 or b[3] < t[1] - 16 or b[1] > t[3] + 16):
            print(f"{name} <- {c.entity_type} {c.candidate_id} {[round(v) for v in b]} conf {c.confidence} "
                  f"entrance={c.confidence >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE} "
                  f"dist_to_bbox={box(*b).distance(box(*t)):.1f} "
                  f"{c.evidence.get('assembly_type')} {c.evidence.get('method')}")
for e in ents:
    if e["entity_type"] != "room":
        continue
    b = [round(v) for v in e["bbox"]]
    for name, t in targets.items():
        if all(abs(b[i] - t[i]) <= 4 for i in range(4)):
            ev = e["evidence"]
            print(name, b, "doors", ev["door_openings"], "windows", ev["window_openings"], "area", ev["area_px2"], "conf", e["confidence"])
