"""The doorway-ownership wall-pen rule AS IT WOULD BE IMPLEMENTED, censused
on every sheet at its factor (+ s01 at 0.542), on the pipeline's exact
inputs (harness), against the room stage's FINAL plugs (pass 1 = today's
share rule):

  A confident (>= ROOM_BBOX_SEAL_MIN_CONFIDENCE) door's INTERRUPTED plug on
  edge e has two tails (the plug beyond the bbox corners). A pen P forms the
  jamb at a tail when a stroked face of P (outside every door zone)
    (a) is collinear with e (angle <= 4 deg, both endpoints within
        ROOM_PLUG_NEAR_PX of the edge line) and has an endpoint inside the
        tail envelope (tail buffered by ROOM_LINE_BARRIER_PX)   — the wall
        face the doorway is cut out of; or
    (b) is PAIRED (contributes to a centerline) and intersects the tail
        envelope                                                — the band
        the tail runs into (the wall continuing, or a return)
  The doorway is CUT INTO P when P forms both jambs. owners = pens cut by
  >= 1 doorway. wall_pens = owners when non-empty, else today's share set.

Prints per sheet: today's wall pens, the owners with their doorway counts,
and whether the set CHANGES. Variants: (a) only, (a)+(b).

Usage: .venv/bin/python tools/census_scratch/step11/rule_census.py [slug[@factor] ...]
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from shapely.geometry import box, LineString, Point  # noqa: E402

ALL = [f"s{i:02d}" for i in range(1, 21)]
DEFAULT = ["s01", f"s01@{F542}"] + [s for s in ALL if s != "s01"]
BIG = 1e5


def edge_line(bb, e):
    x0, y0, x1, y1 = bb
    return [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
            ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))][e]


def tails_of(bb, e, poly):
    x0, y0, x1, y1 = bb
    if e in (0, 1):
        return [poly.intersection(box(x0 - BIG, y0 - BIG, x0, y1 + BIG)),
                poly.intersection(box(x1, y0 - BIG, x1 + BIG, y1 + BIG))]
    return [poly.intersection(box(x0 - BIG, y0 - BIG, x1 + BIG, y0)),
            poly.intersection(box(x0 - BIG, y1, x1 + BIG, y1 + BIG))]


def owners_for(r, net, doors, use_b=True, detail=None, tip=False):
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

    paired = net.paired_face_indices()
    faces = [fc for fc in net.faces if fc.stroked and fc.pen is not None and not in_zone(fc.p1, fc.p2)]
    seg_by_path = defaultdict(list)
    for s in net.segments:
        solid = LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + rooms.ROOM_WALL_DILATE_PX, cap_style=2)
        for pi in s.face_path_indices:
            seg_by_path[pi].append(solid)
    owned = defaultdict(set)
    n_doorways = 0
    for bb, rec in r["seals"].items():
        c = rec["cand"]
        if c.confidence < rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE:
            continue
        for poly, kind, e in rec["plugs"]:
            if kind != "interrupted" or e is None:
                continue
            n_doorways += 1
            p, q = edge_line(bb, e)
            eang = _line_angle_deg(p, q)
            L = _line_length(p, q)
            ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
            jamb_pens = []
            for t in tails_of(bb, e, poly):
                pens_here = {}
                if t.is_empty:
                    jamb_pens.append(pens_here)
                    continue
                env = t.buffer(rooms.ROOM_LINE_BARRIER_PX)
                # the tail's tip: the plug end farthest from the bbox along the edge
                tcoords = list(t.exterior.coords) if t.geom_type == "Polygon" else (
                    [cc for g in getattr(t, "geoms", [t]) for cc in (g.exterior.coords if g.geom_type == "Polygon" else g.coords)])
                tip_pt = max((Point(cc) for cc in tcoords),
                             key=lambda pt: abs((pt.x - p[0]) * ux + (pt.y - p[1]) * uy - L / 2))
                tip_env = tip_pt.buffer(rooms.ROOM_LINE_BARRIER_PX + 0.5)
                for fc in faces:
                    ln = LineString([fc.p1, fc.p2])
                    if not ln.intersects(env):
                        continue
                    how = None
                    coll = (_angle_diff_mod180(_line_angle_deg(fc.p1, fc.p2), eang) <= 4.0
                            and max(abs((fc.p1[0] - p[0]) * -uy + (fc.p1[1] - p[1]) * ux),
                                    abs((fc.p2[0] - p[0]) * -uy + (fc.p2[1] - p[1]) * ux)) <= rooms.ROOM_PLUG_NEAR_PX)
                    ends_in = env.intersects(Point(fc.p1)) or env.intersects(Point(fc.p2))
                    if coll and ends_in:
                        how = "a"
                    elif use_b and (fc.indices & paired):
                        if not tip:
                            how = "b"
                        elif any(sol.intersects(tip_env) for pi in fc.indices for sol in seg_by_path.get(pi, ())):
                            how = "b"
                    if how:
                        pens_here[fc.pen] = pens_here.get(fc.pen, "") + how
                jamb_pens.append(pens_here)
            both = set(jamb_pens[0]) & set(jamb_pens[1])
            for pen in both:
                owned[pen].add((bb, e))
            if detail is not None:
                detail.append((tuple(round(v) for v in bb), e,
                               {str(k): v for k, v in jamb_pens[0].items()},
                               {str(k): v for k, v in jamb_pens[1].items()}))
    return owned, n_doorways


def today_pens(net):
    paired = net.paired_face_indices()
    per = {}
    for f in net.faces:
        if f.stroked and f.pen is not None and (f.indices & paired):
            per[f.pen] = per.get(f.pen, 0.0) + _line_length(f.p1, f.p2)
    tot = sum(per.values())
    return {p for p, L in per.items() if L >= rooms.ROOM_WALL_PEN_MIN_FRAC * tot}, per, tot


def census(slug, factor):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    try:
        r = run_tapped(page, factor)
    except IndexError:
        print(f"\n=== {slug} f={f:.3f}: no barriers (nothing detected)")
        return {}
    net = r["extras"]["network"]
    if net is None or net.is_empty():
        print(f"\n=== {slug} f={f:.3f}: empty network")
        return {}
    doors = [c for c in r["extras"]["all_geo"] if c.entity_type == "door"]
    today, per, tot = today_pens(net)
    out = {"slug": slug, "f": f, "today": sorted(map(str, today)),
           "shares": {str(p): (L / tot if tot else 0) for p, L in per.items()}}
    print(f"\n=== {slug} f={f:.3f}: pens {len(per)}, today's wall pens {sorted(map(str, today))}")
    for label, use_b, tip in (("a only", False, False), ("a+b", True, False), ("a+b_tip", True, True)):
        detail = []
        owned, n = owners_for(r, net, doors, use_b=use_b, detail=detail, tip=tip)
        owners = set(owned)
        new = owners if owners else today
        changed = new != today
        print(f"   [{label}] interrupted doorways {n}; owners: "
              + ", ".join(f"{p}={len(v)}" for p, v in sorted(owned.items(), key=lambda kv: str(kv[0])))
              + f"  -> wall pens {'CHANGE' if changed else 'same'}"
              + (f": {sorted(map(str, new))}" if changed else "")
              + ("  (fallback: no owners)" if not owners else ""))
        out[label] = {"owned": {str(p): len(v) for p, v in owned.items()},
                      "new": sorted(map(str, new)), "changed": changed, "n_doorways": n,
                      "detail": detail}
    return out


if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT
    res = {}
    for a in args:
        slug, _, fac = a.partition("@")
        res[a] = census(slug, float(fac) if fac else None)
    with open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step11/rule_census.json", "w") as fh:
        json.dump(res, fh, indent=1, default=str)
