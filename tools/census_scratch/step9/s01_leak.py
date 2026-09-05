"""s01 at identity vs f = 50/92.2 on this tree: scores, room lists, every
door's FINAL seal at both factors, and the LEAK pieces — free space at 0.542
lying outside every identity room polygon that touches two or more of them —
each attributed to the identity barrier that used to cover it.

  .venv/bin/python s01_leak.py [x0 y0 x1 y1]   # optional focus box
"""
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from shapely.geometry import box, Polygon, LineString  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

slug = "s01"
pages = H.load(slug)
page = pages[0]
F542 = 50.0 / 92.2
focus = box(*[float(v) for v in sys.argv[1:5]]) if len(sys.argv) >= 5 else None


def run_tapped(factor):
    clipped, stamps, gaps, barriers_seen = [], [], [], []
    o_clip, o_stamp, o_gap, o_fsc = (rooms._clip_plug_tails, rooms._plane_stamp,
                                     rooms._folding_chain_gap_plug, rooms._free_space_components)

    def tap_clip(bbox, plugs, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_clip(bbox, plugs, material, gates=gates)
        clipped.append((tuple(bbox), out, material))
        return out

    def tap_stamp(c, skip_edges, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_stamp(c, skip_edges, material, gates=gates)
        stamps.append((c, out))
        return out

    def tap_gap(c, network, material, *, gates=rooms.ROOM_GATES_UNSCALED):
        out = o_gap(c, network, material, gates=gates)
        gaps.append((c, out))
        return out

    def tap_fsc(page_poly, barriers):
        barriers_seen.append(barriers)
        return o_fsc(page_poly, barriers)

    rooms._clip_plug_tails, rooms._plane_stamp = tap_clip, tap_stamp
    rooms._folding_chain_gap_plug, rooms._free_space_components = tap_gap, tap_fsc
    try:
        ents, extras = H.run(page, factor=factor, keep_network=True)
    finally:
        rooms._clip_plug_tails, rooms._plane_stamp = o_clip, o_stamp
        rooms._folding_chain_gap_plug, rooms._free_space_components = o_gap, o_fsc
    doors = [c for c in extras["all_geo"] if c.entity_type == "door"]
    by_bbox = {tuple(c.bbox): c for c in doors}
    seals = {}
    for bbox, plugs, mat in clipped:
        c = by_bbox.get(bbox)
        if c is None:
            continue
        seals[c.candidate_id] = {"cand": c, "plugs": list(plugs), "mat": mat, "stamp": None}
    for c, g in gaps:
        if g is not None and c.candidate_id in seals:
            seals[c.candidate_id]["plugs"].append((g, "chain_gap", None))
    for c, st in stamps:
        seals.setdefault(c.candidate_id, {"cand": c, "plugs": [], "mat": None, "stamp": None})
        seals[c.candidate_id]["stamp"] = st
    for sid, rec in seals.items():
        if rec["plugs"]:
            rec["geom"] = unary_union([p for p, _, _ in rec["plugs"]])
            rec["how"] = "plugs:" + ",".join(f"{k}@{e}" for _, k, e in rec["plugs"])
        elif rec["stamp"] is not None:
            rec["geom"] = rec["stamp"]
            rec["how"] = "PLANE-STAMP"
        else:
            rec["geom"] = None
            rec["how"] = "none"
    return ents, extras, seals, barriers_seen[-1]


def room_list(ents):
    out = []
    for e in ents:
        if e["entity_type"] != "room":
            continue
        poly = Polygon(e["evidence"]["polygon"])
        out.append({"bbox": tuple(round(v) for v in e["bbox"]), "poly": poly, "area": poly.area,
                    "doors": e["evidence"].get("door_openings"), "windows": e["evidence"].get("window_openings"),
                    "conf": e["confidence"]})
    return out


res = {}
for label, f in (("identity", None), ("f0.542", F542)):
    ents, extras, seals, barriers = run_tapped(f)
    sc = H.score(slug, page.page_number, ents)
    n = {t: sum(1 for e in ents if e["entity_type"] == t) for t in ("door", "window", "room")}
    print(f"\n=== {label}: f={page.scale_factor if f is None else f:.3f} n={n} counts={sc['counts']} "
          f"lost={len(sc['lost'])} retFP={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])}")
    for t in sc["lost"]:
        print("   LOST", t)
    for t in sc["unreviewed"]:
        print("   UNREV", t)
    rl = room_list(ents)
    for r in sorted(rl, key=lambda r: r["bbox"]):
        print(f"   room bbox={r['bbox']} area={r['area']:.0f} doors={r['doors']} windows={r['windows']} conf={r['conf']:.2f}")
    res[label] = {"ents": ents, "extras": extras, "seals": seals, "barriers": barriers, "rooms": rl}

# Door seals at both factors, side by side.
print("\n=== door seals (identity | 0.542)")
s1, s2 = res["identity"]["seals"], res["f0.542"]["seals"]
for sid in sorted(set(s1) | set(s2)):
    a, b = s1.get(sid), s2.get(sid)
    c = (a or b)["cand"]
    bb = tuple(round(v) for v in c.bbox)
    if focus is not None and not box(*c.bbox).buffer(40).intersects(focus):
        continue
    print(f"  {sid} conf={c.confidence:.2f} {c.evidence.get('assembly_type')}/{c.evidence.get('swing_layout')} bbox={bb}")
    print(f"      identity: {a['how'] if a else '(absent)'}")
    print(f"      0.542   : {b['how'] if b else '(absent)'}")

# Leak pieces: 0.542 free space outside every identity room that touches >= 2.
print("\n=== leak pieces (0.542 free space outside the identity rooms, touching >= 2 of them)")
id_rooms = res["identity"]["rooms"]
id_union = unary_union([r["poly"] for r in id_rooms]).buffer(1.0)
B1, B2 = res["identity"]["barriers"], res["f0.542"]["barriers"]
for r2 in res["f0.542"]["rooms"]:
    new_floor = r2["poly"].difference(id_union)
    pieces = list(getattr(new_floor, "geoms", [new_floor]))
    for pc in pieces:
        if pc.is_empty or pc.area < 1.0:
            continue
        touching = [i for i, r in enumerate(id_rooms) if pc.distance(r["poly"]) <= 2.5]
        if len(touching) < 2:
            continue
        if focus is not None and not pc.intersects(focus):
            continue
        print(f"\n  room@0.542 bbox={r2['bbox']} piece bounds={tuple(round(v, 1) for v in pc.bounds)} area={pc.area:.0f} "
              f"touches identity rooms {[id_rooms[i]['bbox'] for i in touching]}")
        # what identity barrier covered it?
        cov = B1.intersection(pc)
        print(f"      identity barrier inside the piece: {cov.area:.0f} px2 of {pc.area:.0f}; 0.542 barrier inside: {B2.intersection(pc).area:.0f}")
        for sid, rec in s1.items():
            if rec["geom"] is not None and rec["geom"].intersects(pc):
                print(f"      identity door seal {sid} ({rec['how']}) overlaps {rec['geom'].intersection(pc).area:.0f} px2")
        net1 = res["identity"]["extras"]["network"]
        for s in net1.segments:
            g = LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2)
            if g.intersects(pc):
                print(f"      identity SEGMENT th={s.thickness_px:.1f} p1={tuple(round(v,1) for v in s.p1)} p2={tuple(round(v,1) for v in s.p2)} "
                      f"weak={getattr(s,'weak',None)} overlaps {g.intersection(pc).area:.0f}")
        for fc in net1.faces:
            g = LineString([fc.p1, fc.p2]).buffer(2.0, cap_style=3)
            if g.intersects(pc):
                print(f"      identity FACE sw={fc.stroke_width:.2f} stroked={fc.stroked} p1={tuple(round(v,1) for v in fc.p1)} p2={tuple(round(v,1) for v in fc.p2)} overlaps {g.intersection(pc).area:.0f}")
