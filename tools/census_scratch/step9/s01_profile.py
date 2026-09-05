"""Door_0002 (the hall door) edge profiles at identity and 0.542, plus the
material near its left jamb at both factors, plus every door's seal keyed by bbox."""
import sys
sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa

page = H.load("s01")[0]
R1 = run_tapped(page, None)
R2 = run_tapped(page, F542)

print("=== door seals by bbox (identity | 0.542)")
for bb in sorted(set(R1["seals"]) | set(R2["seals"])):
    a, b = R1["seals"].get(bb), R2["seals"].get(bb)
    c = (a or b)["cand"]
    print(f"  {tuple(round(v) for v in bb)} conf={c.confidence:.2f} {c.evidence.get('assembly_type')}/{c.evidence.get('swing_layout')}"
          f"  identity={a['how'] if a else '(absent)'}  0.542={b['how'] if b else '(absent)'}")

# the hall door: bbox ~ (424,917,467,958)
hall = [bb for bb in R1["seals"] if abs(bb[0] - 424) < 3 and abs(bb[1] - 917) < 3][0]
print(f"\n=== hall door exact bbox {hall}")
for label, R in (("identity", R1), ("0.542", R2)):
    mat, skip, gates, out = R["plug_calls"][hall]
    print(f"\n[{label}] skip={sorted(skip)} raw plugs={[(k, e) for _, k, e in out]} hinge_edges={sorted(rooms._swing_hinge_edges(R['seals'][hall]['cand']) or [])}")
    for e in (0, 3):
        print_profile(label, hall, mat, gates, e)
    # material pieces near the left jamb (x 395..430, y 900..935)
    probe = box(395, 900, 430, 935)
    mi = mat.intersection(probe)
    for g in getattr(mi, "geoms", [mi]):
        if not g.is_empty:
            print(f"      material piece near left jamb bounds={tuple(round(v,2) for v in g.bounds)} area={g.area:.0f}")
    net = R["extras"]["network"]
    for s in net.segments:
        g = LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2)
        if g.intersects(probe):
            print(f"      SEGMENT th={s.thickness_px:.2f} p1={tuple(round(v,2) for v in s.p1)} p2={tuple(round(v,2) for v in s.p2)} weak={getattr(s,'weak',None)} stroked={getattr(s,'stroked',None)}")
    for fc in net.faces:
        g = LineString([fc.p1, fc.p2]).buffer(2.0, cap_style=3)
        if g.intersects(probe):
            print(f"      FACE sw={fc.stroke_width:.2f} stroked={fc.stroked} weak={getattr(fc,'weak',None)} p1={tuple(round(v,2) for v in fc.p1)} p2={tuple(round(v,2) for v in fc.p2)}")
