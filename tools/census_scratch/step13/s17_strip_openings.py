"""Which openings touch s17's four recorded reveal strips (rooms 0013/0014/
0027/0032), and at what confidence — the ENTRANCE gate decides whether
_is_band_pocket is ever called on them."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms

TARGETS = {"room_0013": (912, 2174, 947, 2331), "room_0014": (3047, 2174, 3082, 2489),
           "room_0027": (3047, 2594, 3084, 3061), "room_0032": (914, 2615, 949, 3061)}
p = H.load("s17")[0]
ents, extras = H.run(p)
for c in extras["all_geo"]:
    if c.entity_type not in ("door", "window"):
        continue
    b = c.bbox
    for name, t in TARGETS.items():
        if not (b[2] < t[0] - 16 or b[0] > t[2] + 16 or b[3] < t[1] - 16 or b[1] > t[3] + 16):
            print(f"{name} <- {c.entity_type} {c.candidate_id} {[round(v) for v in b]} conf {c.confidence} "
                  f"entrance={c.confidence >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE} "
                  f"{c.evidence.get('assembly_type')} {c.evidence.get('method')}")
for e in ents:
    if e["entity_type"] != "room":
        continue
    b = [round(v) for v in e["bbox"]]
    for name, t in TARGETS.items():
        if all(abs(b[i] - t[i]) <= 3 for i in range(4)):
            ev = e["evidence"]
            print(name, b, "doors", ev["door_openings"], "windows", ev["window_openings"], "area", ev["area_px2"])
