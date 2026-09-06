"""UNSIMPLIFIED per-room lost / gained diff between cap x1.0 and cap x40/36
for one sheet (ROOM_SIMPLIFY_TOL_PX 0 in both runs), through the harness.
Usage: .venv/bin/python tools/census_scratch/step4/unsimplified_diff.py sNN"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms
from shapely.geometry import Polygon

rooms.ROOM_SIMPLIFY_TOL_PX = 0.0
slug = sys.argv[1]
p = H.load(slug)[0]

def polys(mult):
    if mult == 1.0:
        ents, _ = H.run(p)
    else:
        with H.overrides(mult={"WALL_MAX_THICKNESS_PX": mult}):
            ents, _ = H.run(p)
    return [(tuple(round(v) for v in e["bbox"]), Polygon(e["evidence"]["polygon"]).buffer(0))
            for e in ents if e["entity_type"] == "room"]

base, after = polys(1.0), polys(40.0 / 36.0)
print(f"{slug}: rooms {len(base)} -> {len(after)}")
used, tl, tg = set(), 0.0, 0.0
for bb, pb in base:
    best, biou = None, 0.0
    for i, (ba, pa) in enumerate(after):
        u = pb.union(pa).area
        iou = pb.intersection(pa).area / u if u else 0.0
        if iou > biou:
            best, biou = i, iou
    if best is None or biou < 0.5:
        print(f"  REMOVED {bb} area {pb.area:.0f}"); continue
    used.add(best)
    ba, pa = after[best]
    lost, gained = pb.difference(pa), pa.difference(pb)
    tl += lost.area; tg += gained.area
    if lost.area > 20 or gained.area > 20 or biou < 0.999:
        print(f"  {bb} -> {ba} iou {biou:.4f} lost {lost.area:.0f} gained {gained.area:.0f}")
        parts = list(lost.geoms) if hasattr(lost, "geoms") else ([lost] if not lost.is_empty else [])
        for g in sorted(parts, key=lambda g: -g.area)[:3]:
            b = g.bounds
            print(f"      lost piece {g.area:.0f} px2 [{b[0]:.0f},{b[1]:.0f}]-[{b[2]:.0f},{b[3]:.0f}] ({b[2]-b[0]:.1f} x {b[3]-b[1]:.1f})")
for i, (ba, pa) in enumerate(after):
    if i not in used:
        print(f"  ADDED {ba} area {pa.area:.0f}")
print(f"  TOTAL lost {tl:.0f} gained {tg:.0f} (matched rooms)")
