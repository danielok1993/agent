"""What bounds s11's storage (1078,1597)-(1095,1704) on each side, read off
detect_rooms' own locals: the wall segments within reach of each long side,
the network faces beside it, and the paths drawn there (pen, kind, extent).

Usage: .venv/bin/python tools/census_scratch/step16/s11_storage_probe.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import LineString, box  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_length  # noqa: E402

STORAGE = (1077.5, 1597.0, 1095.2, 1704.0)
cap = {}
o = rooms._free_space_components


def fsc(page, barriers):
    loc = sys._getframe(1).f_locals
    for k in ("wall_segments", "face_lines", "cap_lines", "solid_parts", "network", "solids"):
        cap[k] = loc[k]
    return o(page, barriers)


rooms._free_space_components = fsc
try:
    p = H.load("s11")[0]
    H.run(p)
finally:
    rooms._free_space_components = o

probe = box(STORAGE[0] - 40, STORAGE[1] - 40, STORAGE[2] + 40, STORAGE[3] + 40)
print("wall SEGMENTS within 40px of the storage:")
for s in cap["wall_segments"]:
    ln = LineString([s.p1, s.p2])
    if ln.intersects(probe):
        print(f"  seg {tuple(round(v, 2) for v in s.p1)}-{tuple(round(v, 2) for v in s.p2)} "
              f"th {s.thickness_px:.2f} src {s.source} stroked {s.stroked} faces {s.face_path_indices[:6]}")
print("network FACES within 40px:")
for f in cap["network"].faces:
    ln = LineString([f.p1, f.p2])
    if ln.intersects(probe):
        print(f"  face {tuple(round(v, 2) for v in f.p1)}-{tuple(round(v, 2) for v in f.p2)} "
              f"len {_line_length(f.p1, f.p2):.1f} sw {f.stroke_width} stroked {f.stroked} fill {f.wall_fill} "
              f"mat {f.material_backed} pen {f.pen} idx {sorted(f.indices)[:6]}")
print("PATHS (stroked l items) within 40px, long enough to matter (>= 8px):")
pd = p.page_data
for pth in pd.paths:
    b = pth.bbox
    if box(*b).intersects(probe) and pth.item_type in ("l", "re", "qu") and max(b[2] - b[0], b[3] - b[1]) >= 8:
        print(f"  path {pth.path_index} {pth.item_type} bbox {tuple(round(v, 1) for v in b)} sw {pth.stroke_width} "
              f"color {pth.color} fill {pth.fill} layer {getattr(pth, 'layer', None)}")
print("SOLIDS boundary pieces within the probe (segment solids first):")
n_seg = len(cap["wall_segments"])
from shapely.ops import unary_union  # noqa: E402
seg_solids = unary_union(cap["solid_parts"][:n_seg])
oth_solids = unary_union(cap["solid_parts"][n_seg:]) if cap["solid_parts"][n_seg:] else None
for name, g in (("segments", seg_solids), ("others", oth_solids)):
    if g is None:
        continue
    inter = g.intersection(probe)
    print(f"  {name}: area in probe {inter.area:.0f} px2; bounds of pieces:")
    for piece in getattr(inter, "geoms", [inter]):
        if not piece.is_empty:
            print(f"     {tuple(round(v, 1) for v in piece.bounds)} area {piece.area:.0f}")
