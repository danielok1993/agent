"""s11's storage in utility (1078,1597)-(1095,1704) and door_0009 (0.67):
where the door's seal actually lies, which edges qualified as plugs and how
far the seal is from the storage's boundary — why door_count reads 0."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms
from shapely.geometry import box

STORAGE = box(1077.5, 1597.0, 1095.2, 1704.0)
DOOR = (1102, 1670, 1147, 1715)
cap = {}
o = rooms._free_space_components
def fsc(page, barriers):
    loc = sys._getframe(1).f_locals
    cap["door_barriers"] = list(loc["door_barriers"])
    cap["door_plug_records"] = list(loc["door_plug_records"])
    cap["wall_material"] = loc["wall_material"]
    return o(page, barriers)
rooms._free_space_components = fsc
try:
    p = H.load("s11")[0]
    ents, extras = H.run(p)
finally:
    rooms._free_space_components = o
for c, plugs in cap["door_plug_records"]:
    b = c.bbox
    if all(abs(b[i] - DOOR[i]) <= 3 for i in range(4)):
        print(f"door {c.candidate_id} bbox {[round(v,1) for v in b]} conf {c.confidence} {c.evidence.get('assembly_type')} "
              f"hinge={c.evidence.get('hinge')} leaf={c.evidence.get('leaf_bbox')} open_line={c.evidence.get('opening_line')}")
        for plug, kind, edge in plugs:
            print(f"   plug kind={kind} edge={edge} bounds {[round(v,1) for v in plug.bounds]} "
                  f"dist to storage boundary {plug.distance(STORAGE.exterior):.2f}px")
        if not plugs:
            print("   NO plugs -> plane stamp")
for conf, g in cap["door_barriers"]:
    d = g.distance(STORAGE.exterior)
    if d <= 12:
        print(f"seal conf {conf} bounds {[round(v,1) for v in g.bounds]} dist to storage boundary {d:.2f}px (contact tol {rooms.ROOM_CONTACT_TOL_PX})")
# what material lies between the storage and the door: the partition
probe = box(1094, 1660, 1104, 1704)
print("wall material in the 10px strip right of the storage bottom:", round(cap["wall_material"].intersection(probe).area), "px2 of", round(probe.area))
