"""Refined per-tail ink classes at each interrupted doorway plug, per pen:

  C — a face of the pen COLLINEAR with the plugged edge (angle <= 4 deg,
      perpendicular offset <= ROOM_PLUG_NEAR_PX) has an endpoint inside the
      tail envelope: the wall face the doorway was cut out of
  S — a same-pen paired SEGMENT's solid intersects the tail: the band
      (collinear or a perpendicular return)
  P — a lone (unpaired) face NOT collinear with the edge ends in the
      envelope: a dimension extension line, a fixture's end panel
  x — faces only cross the envelope (both endpoints outside)

Ownership definitions per doorway:
  CS   — both tails C or S
  CSP  — both tails C, S or P
  any  — both tails any ink incl. x
Two material variants: FINAL (the room stage's own final plugs, wall pens as
today) and ALL (every pen treated as a wall pen — ROOM_WALL_PEN_MIN_FRAC
patched to 0 — the pen-independent material a production rule could use).

Usage: .venv/bin/python tools/census_scratch/step11/tail_pens2.py [slug[@factor] ...] [-v]
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from shapely.geometry import box, LineString, Point  # noqa: E402

DEFAULT = ["s01", f"s01@{F542}", "s02", "s03", "s04", "s08", "s12", "s17"]
BIG = 1e5
EDGE_LINES = lambda bb: [((bb[0], bb[1]), (bb[2], bb[1])), ((bb[0], bb[3]), (bb[2], bb[3])),  # noqa: E731
                         ((bb[0], bb[1]), (bb[0], bb[3])), ((bb[2], bb[1]), (bb[2], bb[3]))]


def classify(r, net, doors, verbose, tag):
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

    paired = net.paired_face_indices()
    faces = [fc for fc in net.faces if fc.stroked and fc.pen is not None and not in_zone(fc.p1, fc.p2)]
    faces_by_path = defaultdict(list)
    for fc in net.faces:
        for pi in fc.indices:
            faces_by_path[pi].append(fc)
    seg_pen = []
    for s in net.segments:
        spens = {fc.pen for pi in s.face_path_indices for fc in faces_by_path.get(pi, ())
                 if fc.stroked and fc.pen is not None}
        if len(spens) == 1:
            seg_pen.append((next(iter(spens)),
                            LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + rooms.ROOM_WALL_DILATE_PX, cap_style=2)))
    pens = sorted({fc.pen for fc in faces}, key=str)
    summ = {p: dict(CS=set(), CSP=set(), any=set(), tails_CS=0) for p in pens}
    rows = []
    n_doorways = 0
    for bb, rec in r["seals"].items():
        c = rec["cand"]
        if c.confidence < rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE:
            continue
        x0, y0, x1, y1 = bb
        for poly, kind, e in rec["plugs"]:
            if kind != "interrupted" or e is None:
                continue
            n_doorways += 1
            p, q = EDGE_LINES(bb)[e]
            eang = _line_angle_deg(p, q)
            L = _line_length(p, q)
            ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
            if e in (0, 1):
                tails = [poly.intersection(box(x0 - BIG, y0 - BIG, x0, y1 + BIG)),
                         poly.intersection(box(x1, y0 - BIG, x1 + BIG, y1 + BIG))]
            else:
                tails = [poly.intersection(box(x0 - BIG, y0 - BIG, x1 + BIG, y0)),
                         poly.intersection(box(x0 - BIG, y1, x1 + BIG, y1 + BIG))]
            per_pen = {}
            for pen in pens:
                cls = []
                for t in tails:
                    if t.is_empty:
                        cls.append("-")
                        continue
                    env = t.buffer(rooms.ROOM_LINE_BARRIER_PX)
                    k = set()
                    for fc in faces:
                        if fc.pen != pen:
                            continue
                        ln = LineString([fc.p1, fc.p2])
                        if not ln.intersects(env):
                            continue
                        ends_in = env.intersects(Point(fc.p1)) or env.intersects(Point(fc.p2))
                        if not ends_in:
                            k.add("x")
                            continue
                        coll = (_angle_diff_mod180(_line_angle_deg(fc.p1, fc.p2), eang) <= 4.0
                                and max(abs((fc.p1[0] - p[0]) * -uy + (fc.p1[1] - p[1]) * ux),
                                        abs((fc.p2[0] - p[0]) * -uy + (fc.p2[1] - p[1]) * ux)) <= rooms.ROOM_PLUG_NEAR_PX)
                        if coll:
                            k.add("C")
                        elif fc.indices & paired:
                            k.add("S")   # a paired non-collinear face ending here: a return band's face
                        else:
                            k.add("P")
                    for pp, sp in seg_pen:
                        if pp == pen and sp.intersects(t):
                            k.add("S")
                    cls.append("C" if "C" in k else "S" if "S" in k else "P" if "P" in k else "x" if "x" in k else ".")
                per_pen[pen] = cls
                cs = sum(1 for v in cls if v in "CS")
                csp = sum(1 for v in cls if v in "CSP")
                anyv = sum(1 for v in cls if v in "CSPx")
                summ[pen]["tails_CS"] += cs
                if cs == 2:
                    summ[pen]["CS"].add((bb, e))
                if csp == 2:
                    summ[pen]["CSP"].add((bb, e))
                if anyv == 2:
                    summ[pen]["any"].add((bb, e))
            rows.append((tuple(round(v) for v in bb), e, {str(p): "".join(v) for p, v in per_pen.items()}))
    print(f"  [{tag}] interrupted doorway plugs {n_doorways}")
    print(f"  {'pen':22} {'CS':>4} {'CSP':>4} {'any':>4} {'tailsCS':>7}")
    for pen in pens:
        d = summ[pen]
        print(f"  {str(pen):22} {len(d['CS']):4d} {len(d['CSP']):4d} {len(d['any']):4d} {d['tails_CS']:7d}")
    if verbose:
        for bb, e, m in sorted(rows):
            print("     ", bb, "edge", e, "  ".join(f"{p}:{v}" for p, v in m.items()))
    return {str(p): {k: (len(v) if isinstance(v, set) else v) for k, v in d.items()} for p, d in summ.items()}


def census(slug, factor, verbose=False):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    print(f"\n=== {slug} f={f:.3f}")
    out = {}
    r = run_tapped(page, factor)
    net = r["extras"]["network"]
    doors = [c for c in r["extras"]["all_geo"] if c.entity_type == "door"]
    out["FINAL"] = classify(r, net, doors, verbose, "FINAL plugs, wall pens as today")
    saved = rooms.ROOM_WALL_PEN_MIN_FRAC
    rooms.ROOM_WALL_PEN_MIN_FRAC = 0.0
    try:
        r2 = run_tapped(page, factor)
    finally:
        rooms.ROOM_WALL_PEN_MIN_FRAC = saved
    net2 = r2["extras"]["network"]
    doors2 = [c for c in r2["extras"]["all_geo"] if c.entity_type == "door"]
    out["ALL"] = classify(r2, net2, doors2, verbose, "ALL pens as wall pens (frac 0)")
    return out


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[1:] if a != "-v"] or DEFAULT
    out = {}
    for a in args:
        slug, _, fac = a.partition("@")
        out[a] = census(slug, float(fac) if fac else None, verbose)
    with open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step11/tail_pens2.json", "w") as fh:
        json.dump(out, fh, indent=1)
