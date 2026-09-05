"""Step-10 census of the MATERIAL-SEEKING TAIL as implemented: for every door
the room stage sees on every sheet (at its detection factor; s01 also at
0.542), re-run `_door_plugs` on the exact (bbox, local material, skip edges,
gates) the pipeline passed it, once WITHOUT seek edges (the old rule) and once
WITH `_seek_edges(c)` (the new rule), and print every edge whose plug outcome
differs — with the seek's hit distance in px and mm at the sheet's TRUE scale
and what the material at the hit is.

  .venv/bin/python tools/census_scratch/step9/seek_census.py [slug[@factor] ...]
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
if not args:
    args = ["s01", "s01@0.5423", "s02", "s03", "s04", "s05", "s06", "s07", "s08",
            "s10", "s11", "s12", "s13", "s14", "s15", "s16", "s17", "s18", "s20"]

total_changed = 0
for arg in args:
    slug, _, fac = arg.partition("@")
    factor = float(fac) if fac else None
    page = H.load(slug)[0]
    R = run_tapped(page, factor)
    f = page.scale_factor if factor is None else factor
    gates = rooms.RoomGates.at(f)
    net = R["extras"]["network"]
    seg_geoms = [(s, LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2)) for s in net.segments]
    face_geoms = [(fc, LineString([fc.p1, fc.p2]).buffer(2.0, cap_style=3)) for fc in net.faces]
    print(f"\n=== {slug} f={f:.3f} seal={gates.ROOM_OPENING_SEAL_PX:.2f} seek={gates.ROOM_PLUG_JAMB_SEEK_PX:.2f} "
          f"half={gates.ROOM_PLUG_HALF_WIDTH_PX:.2f} win={gates.ROOM_PLUG_ANCHOR_WIN_PX:.1f}")
    n_doors = n_seeking = n_changed = 0
    for bb, (mat, skip, g, out_new) in R["plug_calls"].items():
        c = R["seals"].get(bb, {}).get("cand")
        if c is None:
            continue
        n_doors += 1
        seeking = rooms._seek_edges(c)
        if seeking:
            n_seeking += 1
        old = rooms._door_plugs(bb, mat, skip, seek_edges=frozenset(), gates=g)
        new = rooms._door_plugs(bb, mat, skip, seek_edges=seeking, gates=g)
        o = {e: k for _, k, e in old}
        n = {e: k for _, k, e in new}
        if o == n:
            continue
        n_changed += 1
        total_changed += 1
        x0, y0, x1, y1 = bb
        edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        mmpx = 0.16933 * (H.denom_at(slug, cx, cy) or 50.0)
        kept = {e: k for _, k, e in R["seals"][bb]["plugs"]}
        print(f"  {c.candidate_id} c{c.confidence:.2f} {c.evidence.get('assembly_type')} bbox=({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) "
              f"hinge={sorted(seeking)} old={o} new={n} kept-in-run={kept} how={R['seals'][bb]['how']}")
        for e in sorted(set(o) | set(n)):
            if o.get(e) == n.get(e):
                continue
            p, q = edges[e]
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
            prof = rooms._edge_profile(p, q, ux, uy, L, g.ROOM_OPENING_SEAL_PX, g.ROOM_OPENING_SEAL_PX, mat, g)
            if prof.anchored_a == prof.anchored_b:
                print(f"     edge{e}: anchored a={prof.anchored_a} b={prof.anchored_b} (no seek)")
                continue
            corner, dx, dy = (q, ux, uy) if prof.anchored_a else (p, -ux, -uy)
            hit = rooms._seek_jamb(corner, dx, dy, g.ROOM_PLUG_JAMB_SEEK_PX, g.ROOM_PLUG_HALF_WIDTH_PX, mat)
            what = []
            if hit is not None:
                pt = Point(corner[0] + dx * (hit + 0.5), corner[1] + dy * (hit + 0.5))
                ang_e = math.degrees(math.atan2(dy, dx))
                for s, gm in seg_geoms:
                    if gm.distance(pt) <= g.ROOM_PLUG_HALF_WIDTH_PX + 0.6:
                        what.append(f"seg th{s.thickness_px:.1f} @{_angle_diff_mod180(_line_angle_deg(s.p1, s.p2), ang_e):.0f}deg")
                for fc, gm in face_geoms:
                    if gm.distance(pt) <= g.ROOM_PLUG_HALF_WIDTH_PX + 0.6:
                        what.append(f"face sw{fc.stroke_width:.2f} L{_line_length(fc.p1, fc.p2):.0f} @{_angle_diff_mod180(_line_angle_deg(fc.p1, fc.p2), ang_e):.0f}deg")
            side = "b" if prof.anchored_a else "a"
            print(f"     edge{e} side {side}: {o.get(e)} -> {n.get(e)}  hit={hit if hit is None else round(hit, 2)}px"
                  f"{'' if hit is None else f'={hit * mmpx:.0f}mm'}  material: {'; '.join(what[:4]) or '?'}")
    print(f"  doors {n_doors}, seeking-eligible {n_seeking}, outcome changed {n_changed}")
print(f"\nTOTAL doors with a changed plug outcome: {total_changed}")
