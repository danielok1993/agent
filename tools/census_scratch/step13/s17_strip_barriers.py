"""What bounds s17's four reveal strips on each long side — the barrier tier
behind the 0.0 face cover: faces (line barriers) near the edge, segment
flanks, wall-fill polygons, white walls, window seals, door seals. Reads
detect_rooms' locals through the free-space tap (as entered_census.py does)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H
from detection import rooms
from shapely.geometry import box, LineString

STRIPS = {"room_0013": (911.9, 2173.9, 946.7, 2330.7), "room_0032": (913.9, 2608.7, 948.7, 3060.7),
          "room_0014": (3047.2, 2173.9, 3083.7, 2488.9), "room_0027": (3047.2, 2594.4, 3083.7, 3060.7)}
cap = {}
o = rooms._free_space_components
def fsc(page, barriers):
    loc = sys._getframe(1).f_locals
    for k in ("face_lines", "door_barriers", "window_barriers", "solid_parts", "line_parts"):
        cap[k] = list(loc[k])
    cap["network"] = loc["network"]
    return o(page, barriers)
rooms._free_space_components = fsc
try:
    p = H.load("s17")[0]
    ents, extras = H.run(p, keep_network=True)
finally:
    rooms._free_space_components = o
net = cap["network"]
for name, (x0, y0, x1, y1) in STRIPS.items():
    vertical = (y1 - y0) > (x1 - x0)
    print(f"== {name} {[round(v,1) for v in (x0,y0,x1,y1)]}")
    for side, probe in (("left/top", box(x0 - 6, y0, x0 + 1, y1) if vertical else box(x0, y0 - 6, x1, y0 + 1)),
                        ("right/bottom", box(x1 - 1, y0, x1 + 6, y1) if vertical else box(x0, y1 - 1, x1, y1 + 6))):
        print(f"  -- {side} probe {[round(v,1) for v in probe.bounds]}")
        for (a, b) in cap["face_lines"]:
            ls = LineString([a, b])
            if ls.intersects(probe):
                print(f"     face_line {[round(v,1) for v in a]}-{[round(v,1) for v in b]} overlap {ls.intersection(probe).length:.1f}")
        for f in net.faces:
            ls = LineString([f.p1, f.p2])
            if ls.intersects(probe):
                print(f"     network face idx {sorted(f.indices)[:4]} {[round(v,1) for v in f.p1]}-{[round(v,1) for v in f.p2]} sw {f.stroke_width} stroked={f.stroked} fill={f.wall_fill} overlap {ls.intersection(probe).length:.1f}")
        for s in net.segments:
            ls = LineString([s.p1, s.p2]).buffer(s.thickness_px / 2)
            if ls.intersects(probe):
                print(f"     segment th {s.thickness_px:.2f} {[round(v,1) for v in s.p1]}-{[round(v,1) for v in s.p2]} src={getattr(s,'source',None)} overlap {ls.intersection(probe).area:.0f}")
        for poly in net.fill_polygons:
            if poly.intersects(probe):
                print(f"     fill_polygon bounds {[round(v,1) for v in poly.bounds]} overlap {poly.intersection(probe).area:.0f}")
        for conf, g in cap["door_barriers"]:
            if g.intersects(probe):
                print(f"     door seal conf {conf} bounds {[round(v,1) for v in g.bounds]} overlap {g.intersection(probe).area:.0f}")
        for g in cap["window_barriers"]:
            if g.intersects(probe):
                print(f"     window seal bounds {[round(v,1) for v in g.bounds]} overlap {g.intersection(probe).area:.0f}")
        n_solid = sum(1 for sp in cap["solid_parts"] if sp.intersects(probe))
        n_line = sum(1 for lp in cap["line_parts"] if lp.intersects(probe))
        print(f"     solid_parts touching {n_solid}, line_parts touching {n_line}")
