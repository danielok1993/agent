"""s01 identity vs true factor, UNSIMPLIFIED room polygons: per matched room, lost / gained area and where."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H
from detection import rooms
from shapely.geometry import Polygon
rooms.ROOM_SIMPLIFY_TOL_PX = 0.0
p = H.load("s01")[0]

def polys(f):
    ents, _ = H.run(p, factor=f)
    out = []
    for e in ents:
        if e["entity_type"] != "room":
            continue
        pg = Polygon(e["evidence"]["polygon"]).buffer(0)
        out.append((tuple(round(v) for v in e["bbox"]), pg))
    return out

base, after = polys(1.0), polys(50.0 / 92.2)
print(f"rooms: identity {len(base)}, true factor {len(after)}")
used = set()
tot_lost = tot_gain = 0.0
for bb, pb in base:
    best, best_iou = None, 0.0
    for i, (ba, pa) in enumerate(after):
        u = pb.union(pa).area
        iou = pb.intersection(pa).area / u if u else 0.0
        if iou > best_iou:
            best, best_iou = i, iou
    if best is None or best_iou < 0.5:
        print(f"REMOVED {bb} area {pb.area:.0f}")
        continue
    used.add(best)
    ba, pa = after[best]
    lost, gained = pb.difference(pa), pa.difference(pb)
    tot_lost += lost.area; tot_gain += gained.area
    lb = tuple(round(v) for v in lost.bounds) if not lost.is_empty else None
    print(f"{bb} -> {ba}  iou {best_iou:.4f}  lost {lost.area:.0f} px2 at {lb}  gained {gained.area:.0f} px2")
    if not lost.is_empty and lost.area > 20:
        parts = list(lost.geoms) if hasattr(lost, "geoms") else [lost]
        for g in sorted(parts, key=lambda g: -g.area)[:4]:
            b = g.bounds
            print(f"      lost piece {g.area:.0f} px2  [{b[0]:.1f},{b[1]:.1f}]-[{b[2]:.1f},{b[3]:.1f}]  ({b[2]-b[0]:.1f} x {b[3]-b[1]:.1f})")
for i, (ba, pa) in enumerate(after):
    if i not in used:
        print(f"ADDED {ba} area {pa.area:.0f}")
print(f"TOTAL lost {tot_lost:.0f} px2, gained {tot_gain:.0f} px2 (matched rooms only)")
