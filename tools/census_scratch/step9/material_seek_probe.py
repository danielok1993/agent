"""Material-seek false-class probe (post-review): for every single-swing door
>= 0.55, each HINGE edge end that is NOT anchored today (no touch within the
seal reach), the distance outward from the corner to the nearest touch
(<= plug half-width) against (a) the LOCAL material _door_plugs sees (clipped
SEAL+NEAR+4 around the bbox) and (b) the FULL barrier union — and what the
material is (a segment / a face, its angle to the edge). Lists every end whose
full-material touch lies within CAP_MM at the sheet's true scale.

  .venv/bin/python tools/census_scratch/step9/material_seek_probe.py s17 s01 ... [--cap-mm 300]
"""
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_angle_deg, _angle_diff_mod180, _line_length  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402
from s01_common import run_tapped  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
cap_mm = 300.0
if "--cap-mm" in sys.argv:
    cap_mm = float(sys.argv[sys.argv.index("--cap-mm") + 1])
REACH = 100.0


def first_touch(corner, ux, uy, geom, half):
    for k in range(0, int(REACH) + 1):
        if Point(corner[0] + ux * k, corner[1] + uy * k).distance(geom) <= half:
            return float(k)
    return None


for arg in args:
    slug, _, fac = arg.partition("@")
    factor = float(fac) if fac else None
    page = H.load(slug)[0]
    R = run_tapped(page, factor)
    f = page.scale_factor if factor is None else factor
    gates = rooms.RoomGates.at(f)
    net = R["extras"]["network"]
    full = R["barriers"]
    seg_geoms = [(s, LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2)) for s in net.segments]
    face_geoms = [(fc, LineString([fc.p1, fc.p2]).buffer(2.0, cap_style=3)) for fc in net.faces]
    print(f"\n=== {slug} f={f:.3f} seal={gates.ROOM_OPENING_SEAL_PX:.2f} half={gates.ROOM_PLUG_HALF_WIDTH_PX:.2f} cap={cap_mm}mm")
    n_ends = n_hit = 0
    for bb, (mat, skip, g, out) in R["plug_calls"].items():
        c = R["seals"].get(bb, {}).get("cand")
        if c is None or c.confidence < 0.55:
            continue
        hinge = rooms._swing_hinge_edges(c)
        if hinge is None:
            continue
        own = R["seals"][bb]["geom"]
        full = R["barriers"] if own is None else R["barriers"].difference(own.buffer(0.5))
        x0, y0, x1, y1 = bb
        edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
        q = {e: k for _, k, e in out}
        kept = {e: k for _, k, e in R["seals"][bb]["plugs"]}
        for e in sorted(hinge):
            if e in skip:
                continue
            p, qq = edges[e]
            L = math.hypot(qq[0] - p[0], qq[1] - p[1])
            ux, uy = (qq[0] - p[0]) / L, (qq[1] - p[1]) / L
            cx, cy = (p[0] + qq[0]) / 2, (p[1] + qq[1]) / 2
            mmpx = 0.16933 * (H.denom_at(slug, cx, cy) or 50.0)
            for side, corner, dx, dy in (("a", p, -ux, -uy), ("b", qq, ux, uy)):
                t_local = first_touch(corner, dx, dy, mat, g.ROOM_PLUG_HALF_WIDTH_PX)
                if t_local is not None and t_local <= g.ROOM_OPENING_SEAL_PX:
                    continue  # anchored today
                n_ends += 1
                t_full = first_touch(corner, dx, dy, full, g.ROOM_PLUG_HALF_WIDTH_PX)
                if t_full is None or t_full * mmpx > cap_mm:
                    continue
                n_hit += 1
                pt = Point(corner[0] + dx * t_full, corner[1] + dy * t_full)
                what = []
                ang_e = math.degrees(math.atan2(dy, dx))
                for s, gm in seg_geoms:
                    if gm.distance(pt) <= g.ROOM_PLUG_HALF_WIDTH_PX + 0.01:
                        what.append(f"seg th{s.thickness_px:.1f} @{_angle_diff_mod180(_line_angle_deg(s.p1, s.p2), ang_e):.0f}deg")
                for fc, gm in face_geoms:
                    if gm.distance(pt) <= g.ROOM_PLUG_HALF_WIDTH_PX + 0.01:
                        what.append(f"face sw{fc.stroke_width:.2f} L{_line_length(fc.p1, fc.p2):.0f} @{_angle_diff_mod180(_line_angle_deg(fc.p1, fc.p2), ang_e):.0f}deg")
                for obb, rec in R["seals"].items():
                    if obb != bb and rec["geom"] is not None and rec["geom"].distance(pt) <= g.ROOM_PLUG_HALF_WIDTH_PX + 0.01:
                        what.append(f"door-seal {tuple(round(v) for v in obb)}")
                other = "anchored" if q.get(e) else "-"
                print(f"  {c.candidate_id} c{c.confidence:.2f} {c.evidence.get('assembly_type')} edge{e} side {side} raw={q.get(e)} kept={kept.get(e)} "
                      f"local_touch={t_local} full_touch={t_full:.0f}px={t_full * mmpx:.0f}mm  hits: {'; '.join(what[:4]) or '?'}")
    print(f"  un-anchored hinge-edge ends: {n_ends}, with full material within {cap_mm:.0f}mm: {n_hit}")
