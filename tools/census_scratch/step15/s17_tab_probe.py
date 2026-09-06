"""What bounds each s17 reveal strip's TAB — the 31.5px run at standoff 0
from the strip's face line: which wall segment's solid, where its end line
lies, and which face lines run beside the tab. Read off detect_rooms' own
locals through the free-space tap (wall_segments, solids, wall_material,
face_lines).

Usage: .venv/bin/python tools/census_scratch/step15/s17_tab_probe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import LineString, box  # noqa: E402

from detection import rooms  # noqa: E402
from detection.geometry import _line_length  # noqa: E402

# strip name -> (tab run a, tab run b) from step13/s17_strip_edges.py
TABS = {
    "room_0013": ((911.9, 2173.9), (911.9, 2205.4)),
    "room_0032": ((948.7, 3029.2), (948.7, 3060.7)),
    "room_0014 left": ((3047.2, 2173.9), (3047.2, 2205.4)),
    "room_0014 right": ((3083.7, 2447.9), (3083.7, 2479.4)),
    "room_0027 left": ((3047.2, 3029.2), (3047.2, 3060.7)),
    "room_0027 right": ((3083.7, 3029.2), (3083.7, 3060.7)),
}

cap = {}
o = rooms._free_space_components


def fsc(page, barriers):
    loc = sys._getframe(1).f_locals
    for k in ("wall_segments", "solids", "wall_material", "face_lines"):
        cap[k] = loc[k]
    return o(page, barriers)


rooms._free_space_components = fsc
try:
    H.run(H.load("s17")[0])
finally:
    rooms._free_space_components = o

segs, solids, material, face_lines = (cap["wall_segments"], cap["solids"],
                                      cap["wall_material"], cap["face_lines"])
for name, (a, b) in TABS.items():
    run = LineString([a, b])
    x = a[0]
    ymid = (a[1] + b[1]) / 2.0
    print(f"== {name} tab run {a}-{b} ({_line_length(a, b):.1f}px)")
    # the material on the far side of the tab: probe 1px outside the run
    for dx in (-1.0, 1.0):
        pt_line = LineString([(x + dx, a[1]), (x + dx, b[1])])
        print(f"   material {'left' if dx < 0 else 'right'} of the run (1px): "
              f"solids {pt_line.intersection(solids).length:.1f}px, "
              f"all material {pt_line.intersection(material).length:.1f}px of {run.length:.1f}")
    # segments whose solid boundary lies along the run
    for s in segs:
        L = _line_length(s.p1, s.p2)
        if L < 1e-6:
            continue
        cl = LineString([s.p1, s.p2])
        if cl.distance(run) > 40:
            continue
        # this segment's own dilated solid
        sol = cl.buffer(s.thickness_px / 2.0 + rooms.ROOM_WALL_DILATE_PX, cap_style=2, join_style=2)
        if sol.distance(run) > 0.6:
            continue
        along = sol.exterior.intersection(run.buffer(0.3)).length
        print(f"   SEGMENT {tuple(round(v, 2) for v in s.p1)}-{tuple(round(v, 2) for v in s.p2)} "
              f"th {s.thickness_px:.2f} len {L:.1f}: solid boundary along the tab run {along:.1f}px; "
              f"solid bounds {[round(v, 2) for v in sol.bounds]}")
    # face lines within 6px of the tab run
    for p1, p2 in face_lines:
        fl = LineString([p1, p2])
        if fl.distance(run) <= 6.0:
            print(f"   face line {tuple(round(v, 2) for v in p1)}-{tuple(round(v, 2) for v in p2)} "
                  f"dist {fl.distance(run):.2f}")
