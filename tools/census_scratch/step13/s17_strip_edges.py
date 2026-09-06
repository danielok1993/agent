"""Where exactly the four s17 strips' long edges lie: every polygon vertex on
the left/right side, and the boundary length at each x offset — is the edge
flush with the face line (standoff 0) or at the 2px barrier standoff?"""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms
from shapely.geometry import LineString

STRIPS = {"room_0013": (911.9, 2173.9, 946.7, 2330.7), "room_0032": (913.9, 2608.7, 948.7, 3060.7),
          "room_0014": (3047.2, 2173.9, 3083.7, 2488.9), "room_0027": (3047.2, 2594.4, 3083.7, 3060.7)}
cap = {}
o = rooms._drop_window_exterior_sides
def drop(rooms_list, windows, **k):
    cap["rooms"] = list(rooms_list)
    return o(rooms_list, windows, **k)
rooms._drop_window_exterior_sides = drop
try:
    p = H.load("s17")[0]
    H.run(p)
finally:
    rooms._drop_window_exterior_sides = o
for name, (x0, y0, x1, y1) in STRIPS.items():
    for poly, info in cap["rooms"]:
        b = poly.bounds
        if all(abs(b[i] - (x0, y0, x1, y1)[i]) <= 2 for i in range(4)):
            coords = list(poly.exterior.coords)
            print(f"== {name} bounds {[round(v,1) for v in b]} vertices {len(coords)}")
            # boundary length per x (vertical runs) — left and right sides
            runs = Counter()
            for a, c in zip(coords, coords[1:]):
                if abs(a[0] - c[0]) < 0.05:
                    runs[round(a[0], 1)] += abs(a[1] - c[1])
            for x, L in sorted(runs.items()):
                print(f"   vertical boundary at x={x}: {L:.1f}px")
            left = [(round(x, 1), round(y, 1)) for x, y in coords if x < x0 + 3]
            print("   left-side vertices:", left[:12])
            right = [(round(x, 1), round(y, 1)) for x, y in coords if x > x1 - 3]
            print("   right-side vertices:", right[:12])
