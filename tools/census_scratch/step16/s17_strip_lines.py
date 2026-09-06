"""The drawn structure of s17's cavity wall around reveal strip 0013
(912,2174)-(947,2331): every vertical stroked line within x 880-980 over
y 2100-2500 (path, x, y-extent, pen), the wall segments whose centreline
runs vertical there, and the merged network faces — read off detect_rooms'
own locals. Usage: .venv/bin/python tools/census_scratch/step16/s17_strip_lines.py [x0 x1 y0 y1]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import LineString, box  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_length  # noqa: E402

X0, X1, Y0, Y1 = (float(v) for v in (sys.argv[1:5] or (880, 980, 2100, 2500)))
cap = {}
o = rooms._free_space_components


def fsc(page, barriers):
    loc = sys._getframe(1).f_locals
    for k in ("wall_segments", "network"):
        cap[k] = loc[k]
    return o(page, barriers)


rooms._free_space_components = fsc
try:
    p = H.load("s17")[0]
    H.run(p)
finally:
    rooms._free_space_components = o

probe = box(X0, Y0, X1, Y1)
paired = cap["network"].paired_face_indices()
print("VERTICAL stroked lines (>= 8px) in the probe, by x:")
rows = []
for pth in p.page_data.paths:
    if pth.item_type != "l" or len(pth.points) < 2 or pth.stroke_width <= 0 or pth.fill is not None:
        continue
    a, b = pth.points[0], pth.points[-1]
    if abs(a[0] - b[0]) > 0.5 or abs(a[1] - b[1]) < 8:
        continue
    if not LineString([a, b]).intersects(probe):
        continue
    rows.append((round(a[0], 2), round(min(a[1], b[1]), 1), round(max(a[1], b[1]), 1), pth.path_index,
                 round(pth.stroke_width, 2), pth.path_index in paired))
for r in sorted(rows):
    print(f"  x={r[0]:8.2f}  y {r[1]:7.1f}-{r[2]:7.1f}  path {r[3]}  sw {r[4]}  paired={r[5]}")
print("VERTICAL wall SEGMENTS in the probe (centreline x, y-extent, thickness, flanks):")
for s in cap["wall_segments"]:
    if abs(s.p1[0] - s.p2[0]) > 1.0:
        continue
    if not LineString([s.p1, s.p2]).intersects(probe.buffer(40)):
        continue
    x = (s.p1[0] + s.p2[0]) / 2
    print(f"  cx={x:8.2f}  y {min(s.p1[1], s.p2[1]):7.1f}-{max(s.p1[1], s.p2[1]):7.1f}  th {s.thickness_px:6.2f}  "
          f"flanks {x - s.thickness_px / 2:.2f} / {x + s.thickness_px / 2:.2f}  src {s.source} faces {s.face_path_indices[:4]}")
print("VERTICAL merged network FACES in the probe:")
for f in cap["network"].faces:
    if abs(f.p1[0] - f.p2[0]) > 1.0 or not LineString([f.p1, f.p2]).intersects(probe):
        continue
    print(f"  x={f.p1[0]:8.2f}  y {min(f.p1[1], f.p2[1]):7.1f}-{max(f.p1[1], f.p2[1]):7.1f}  len {_line_length(f.p1, f.p2):6.1f}  "
          f"sw {f.stroke_width:.2f} stroked {f.stroked} idx {sorted(f.indices)[:5]} paired={bool(f.indices & paired)}")
