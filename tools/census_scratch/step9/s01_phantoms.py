"""Every unreviewed room of s01 at 0.542, classed: was it a free-space
COMPONENT at identity too (fenced, but filtered — by which filter?), or is it
fenced by barrier that exists only at 0.542 (which segments/faces)?"""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa
from regression.matching import iou  # noqa

page = H.load("s01")[0]

# tap the free-space components' OUTPUT too
comps_seen = {}
o_fsc = rooms._free_space_components


def make_tap(label):
    def tap(page_poly, barriers):
        out = o_fsc(page_poly, barriers)
        comps_seen[label] = list(out)
        return out
    return tap


results = {}
for label, f in (("identity", None), ("0.542", F542)):
    rooms._free_space_components = make_tap(label)
    try:
        results[label] = run_tapped(page, f)
    finally:
        rooms._free_space_components = o_fsc
    # run_tapped re-wraps _free_space_components; our tap sits under its tap
R1, R2 = results["identity"], results["0.542"]
sc2 = H.score("s01", page.page_number, R2["ents"])
unrev = sc2["unreviewed"]
id_rooms = R1["rooms"]
id_comps = comps_seen.get("identity", [])
print(f"identity components={len(id_comps)} rooms={len(id_rooms)}; 0.542 components={len(comps_seen.get('0.542', []))} rooms={len(R2['rooms'])}")
gates1 = rooms.RoomGates.at(1.0)
gates2 = rooms.RoomGates.at(F542)
print(f"ROOM_MIN_AREA_PX2 identity={gates1.ROOM_MIN_AREA_PX2:.0f} 0.542={gates2.ROOM_MIN_AREA_PX2:.0f}")

B1, B2 = R1["barriers"], R2["barriers"]
net1, net2 = R1["extras"]["network"], R2["extras"]["network"]


def seg_geom(s):
    return LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2)


def face_geom(f):
    return LineString([f.p1, f.p2]).buffer(2.0, cap_style=3)


for (t, bb, conf) in unrev:
    r2 = next(r for r in R2["rooms"] if r["bbox"] == bb)
    poly = r2["poly"]
    # identity component with IoU >= 0.5 (bbox)?
    best = None
    for c in id_comps:
        v = iou(tuple(c.bounds), tuple(poly.bounds))
        if v >= 0.5 and (best is None or v > best[0]):
            best = (v, c)
    # identity ROOM containing it?
    container = [r["bbox"] for r in id_rooms if r["poly"].buffer(2).contains(poly.representative_point())]
    print(f"\n{bb} area={poly.area:.0f} ({poly.area * (0.16933 * 92.2 / 1000) ** 2:.2f} m2 @92.2) conf={conf:.2f} doors={r2['doors']} win={r2['windows']}")
    if best is not None:
        print(f"   identity COMPONENT exists (IoU {best[0]:.2f}, area {best[1].area:.0f}) -> fenced at identity too; filtered "
              f"{'by ROOM_MIN_AREA' if best[1].area < gates1.ROOM_MIN_AREA_PX2 else 'by another filter'}")
    else:
        print(f"   no identity component; lies inside identity room {container}")
        # barrier present at 0.542 but not at identity, inside the containing identity room
        for cb in container:
            cr = next(r for r in id_rooms if r["bbox"] == cb)
            new_bar = B2.difference(B1).intersection(cr["poly"].buffer(-0.5))
            pieces = [g for g in getattr(new_bar, "geoms", [new_bar]) if not g.is_empty and g.area >= 4]
            pieces.sort(key=lambda g: -g.area)
            for g in pieces[:6]:
                print(f"   NEW barrier at 0.542 inside {cb}: bounds={tuple(round(v,1) for v in g.bounds)} area={g.area:.0f}")
                for s in net2.segments:
                    sg = seg_geom(s)
                    if sg.intersection(g).area > 0.3 * g.area:
                        print(f"        SEG@0.542 th={s.thickness_px:.2f} p1={tuple(round(v,1) for v in s.p1)} p2={tuple(round(v,1) for v in s.p2)} "
                              f"weak={getattr(s,'weak',None)} thick={getattr(s,'thick',None)} stroked={getattr(s,'stroked',None)} pen={getattr(s,'pen',None)}")
                for fc in net2.faces:
                    fg = face_geom(fc)
                    if fg.intersection(g).area > 0.3 * g.area:
                        print(f"        FACE@0.542 sw={fc.stroke_width:.2f} stroked={fc.stroked} pen={getattr(fc,'pen',None)} p1={tuple(round(v,1) for v in fc.p1)} p2={tuple(round(v,1) for v in fc.p2)} idx={sorted(fc.indices)[:4]}")
                for bbd, rec in R2["seals"].items():
                    if rec["geom"] is not None and rec["geom"].intersection(g).area > 0.3 * g.area:
                        print(f"        DOOR SEAL@0.542 {tuple(round(v) for v in bbd)} {rec['how']}")
