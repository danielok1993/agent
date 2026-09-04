"""probe_plugs.py <slug> [SEAL_PX] [--all]

Tap every _door_plugs call of the stage-5 chain (harness), pair it with its
candidate, and for every edge that qualifies classify the two end anchors by
the ORIENTATION of the wall elements (network segments + faces) the touching
samples lie on:
  par  = an element within 15 deg of the edge (collinear jamb / band the edge
         lies in)
  perp = an element >= 75 deg to the edge (a wall crossing the edge line)
  obl  = anything else
  ---  = the touching material is not a segment/face (fill ring, white band,
         jamb ring, ...)
"""
import math
import sys
from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_angle_deg, _angle_diff_mod180, _line_length  # noqa: E402

slug = sys.argv[1]
seal = float(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
show_all = "--all" in sys.argv

pages = H.load(slug)
page = pages[0]

calls = []
o_plugs = rooms._door_plugs
o_restrict = rooms._restrict_swing_plugs


def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED):
    out = o_plugs(bbox, wall_material, skip_edges, gates=gates)
    calls.append({"bbox": bbox, "mat": wall_material, "skip": skip_edges,
                  "gates": gates, "out": out, "cand": None, "restricted": None})
    return out


def tap_restrict(c, plugs):
    out = o_restrict(c, plugs)
    if calls and calls[-1]["cand"] is None:
        calls[-1]["cand"] = c
        calls[-1]["restricted"] = out
    return out


rooms._door_plugs = tap_plugs
rooms._restrict_swing_plugs = tap_restrict
absolute = {"ROOM_OPENING_SEAL_PX": seal} if seal is not None else {}
with H.overrides(absolute=absolute):
    ents, extras = H.run(page, keep_network=True)
rooms._door_plugs = o_plugs
rooms._restrict_swing_plugs = o_restrict

net = extras["network"]
segs = list(net.segments)
faces = list(net.faces)
seg_geoms = [LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2) for s in segs]
face_geoms = [LineString([f.p1, f.p2]).buffer(2.0, cap_style=3) for f in faces]
n_rooms = sum(1 for e in ents if e["entity_type"] == "room")
print(f"{slug} seal={seal or 'default'} f={page.scale_factor:.3f} rooms={n_rooms} door_calls={len(calls)}")


def classify_anchor(pts, edge_angle):
    """Which oriented elements do the touching sample points lie on?"""
    hits = []
    for p in pts:
        for s, g in zip(segs, seg_geoms):
            if g.distance(p) <= 0.01:
                a = _angle_diff_mod180(_line_angle_deg(s.p1, s.p2), edge_angle)
                hits.append(("seg", a, s.thickness_px, _line_length(s.p1, s.p2)))
        for f, g in zip(faces, face_geoms):
            if g.distance(p) <= 0.01:
                a = _angle_diff_mod180(_line_angle_deg(f.p1, f.p2), edge_angle)
                hits.append(("face", a, f.stroke_width, _line_length(f.p1, f.p2)))
    par = [h for h in hits if h[1] <= 15]
    perp = [h for h in hits if h[1] >= 75]
    obl = [h for h in hits if 15 < h[1] < 75]
    if par:
        cls = "par"
    elif perp:
        cls = "perp"
    elif obl:
        cls = "obl"
    else:
        cls = "---"
    return cls, hits


def profile(bbox, mat, gates):
    x0, y0, x1, y1 = bbox
    edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
             ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
    res = {}
    for e, (p, q) in enumerate(edges):
        length = math.hypot(q[0] - p[0], q[1] - p[1])
        if length < 1e-6:
            continue
        ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
        S = gates.ROOM_OPENING_SEAL_PX
        a = (p[0] - ux * S, p[1] - uy * S)
        b = (q[0] + ux * S, q[1] + uy * S)
        ext = length + 2 * S
        line = LineString([a, b])
        n = max(int(ext / rooms.ROOM_PLUG_SAMPLE_PX), 8) + 1
        pts = [line.interpolate(ext * i / (n - 1)) for i in range(n)]
        d = [pt.distance(mat) for pt in pts]
        covered = [v <= rooms.ROOM_PLUG_NEAR_PX for v in d]
        quarter = n // 4
        win = min(quarter, int(math.ceil(gates.ROOM_PLUG_ANCHOR_WIN_PX / rooms.ROOM_PLUG_SAMPLE_PX)) + 1)
        start_cov = sum(covered[:win]) / win
        end_cov = sum(covered[-win:]) / win
        trim = quarter + int(math.ceil(rooms.ROOM_PLUG_NEAR_PX / rooms.ROOM_PLUG_SAMPLE_PX))
        in_plane = [v <= rooms.ROOM_PLUG_MID_NEAR_PX for v in d]
        mid = in_plane[trim:n - trim] or in_plane[quarter:n - quarter]
        mid_cov = sum(mid) / len(mid)
        total_cov = sum(covered) / n
        touch = [v <= gates.ROOM_PLUG_HALF_WIDTH_PX for v in d]
        ta = [pts[i] for i in range(win) if touch[i]]
        tb = [pts[i] for i in range(n - win, n) if touch[i]]
        ang = _line_angle_deg(p, q)
        ca, ha = classify_anchor(ta, ang)
        cb, hb = classify_anchor(tb, ang)
        res[e] = dict(start_cov=start_cov, end_cov=end_cov, mid_cov=mid_cov,
                      total_cov=total_cov, touch_a=bool(ta), touch_b=bool(tb),
                      cls_a=ca, cls_b=cb, hits_a=ha, hits_b=hb, length=length)
    return res


EDGE = {0: "top", 1: "bot", 2: "left", 3: "right"}


def fmt_hits(hits):
    seen = set()
    out = []
    for kind, a, t, L in hits:
        key = (kind, round(a), round(t, 1), round(L))
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{kind}@{a:.0f}°/t{t:.1f}/L{L:.0f}")
    return ",".join(out[:4])


for k, c in enumerate(calls):
    cand = c["cand"]
    bbox = c["bbox"]
    prof = profile(bbox, c["mat"], c["gates"])
    q = {e: kind for _, kind, e in c["out"]}
    r = {e: kind for _, kind, e in (c["restricted"] or [])}
    hinge = rooms._swing_hinge_edges(cand) if cand else None
    if not show_all and not q:
        continue
    bb = tuple(round(v) for v in bbox)
    print(f"\n{cand.candidate_id if cand else '?'} conf={cand.confidence:.2f} type={cand.evidence.get('assembly_type')} "
          f"layout={cand.evidence.get('swing_layout')} bbox={bb} hinge_edges={sorted(hinge) if hinge else hinge} skip={sorted(c['skip'])}")
    for e in range(4):
        if e not in prof:
            continue
        p = prof[e]
        flag = q.get(e, "-")
        kept = "KEPT" if e in r else ("dropped" if e in q else "")
        print(f"   {EDGE[e]:5s} {flag:11s} {kept:7s} L={p['length']:.0f} sc={p['start_cov']:.2f} ec={p['end_cov']:.2f} "
              f"mid={p['mid_cov']:.2f} tot={p['total_cov']:.2f} touch={int(p['touch_a'])}{int(p['touch_b'])} "
              f"anchors={p['cls_a']}/{p['cls_b']}  A[{fmt_hits(p['hits_a'])}] B[{fmt_hits(p['hits_b'])}]")
