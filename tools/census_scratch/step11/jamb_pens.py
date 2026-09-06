"""Which PEN's faces are collinear with each confident door's plugged edge and
END at its jambs (the interrupted-run signature per pen), and which pen's
faces run collinear with each confident window's band on both sides.

Per door: for every plugged edge (the room stage's own final plugs), for
every pen: the same-pen stroked faces whose line is within ANG_TOL of the
edge and within OFF_TOL px (perpendicular) of it, that end within REACH px
outward of a bbox corner (nearest endpoint to the corner lies on the
outward side, at most REACH past it) and do NOT cross the doorway (a face
lying across the opening is a drawn-through plane, another signature).
Sides: 0, 1 or 2 (both jambs).

Usage: .venv/bin/python tools/census_scratch/step11/jamb_pens.py [slug[@factor] ...] [-v]
"""
import json
import math
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from detection import walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402

DEFAULT = ["s01", f"s01@{F542}", "s02", "s03", "s04", "s08", "s12", "s17"]
ANG_TOL = 4.0


def edge_pts(bbox, e):
    x0, y0, x1, y1 = bbox
    return [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
            ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))][e]


def collinear_jambs(face, p, q, off_tol, reach):
    """Return (side, dist) when the face lies on the edge line p->q, off the
    doorway, ending within reach of corner p (side 0) or q (side 1)."""
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    ux, uy = (q[0] - p[0]) / L, (q[1] - p[1]) / L
    if _angle_diff_mod180(_line_angle_deg(face.p1, face.p2), _line_angle_deg(p, q)) > ANG_TOL:
        return None
    # perpendicular offset of both face ends from the edge line
    def off(pt):
        return abs((pt[0] - p[0]) * -uy + (pt[1] - p[1]) * ux)
    if max(off(face.p1), off(face.p2)) > off_tol:
        return None
    t1 = (face.p1[0] - p[0]) * ux + (face.p1[1] - p[1]) * uy
    t2 = (face.p2[0] - p[0]) * ux + (face.p2[1] - p[1]) * uy
    lo, hi = min(t1, t2), max(t1, t2)
    # crossing the doorway interior (beyond a small jamb overlap) = through
    inner_lo, inner_hi = 0.15 * L, 0.85 * L
    if lo < inner_lo and hi > inner_hi:
        return ("through", 0.0)
    if hi <= inner_lo and hi >= -reach:      # ends at / before corner p
        return (0, -hi)
    if lo >= inner_hi and lo <= L + reach:   # starts at / after corner q
        return (1, lo - L)
    return None


def census(slug, factor, verbose=False):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    r = run_tapped(page, factor)
    net = r["extras"]["network"]
    gr = rooms.RoomGates.at(f)
    all_geo = r["extras"]["all_geo"]
    doors = [c for c in all_geo if c.entity_type == "door"]
    windows = [c for c in all_geo if c.entity_type == "window"]
    conf_windows = [c for c in windows if c.confidence >= rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE
                    and c.evidence.get("orientation") != "diagonal"]
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

    faces = [fc for fc in net.faces if fc.stroked and fc.pen is not None and not in_zone(fc.p1, fc.p2)]
    pens = sorted({fc.pen for fc in faces}, key=str)
    off_tol = rooms.ROOM_PLUG_NEAR_PX
    reach = gr.ROOM_PLUG_JAMB_SEEK_PX + gr.ROOM_PLUG_HALF_WIDTH_PX
    per_pen = {p: dict(doors2=set(), doors1=set(), through=set(), win2=set(), win1=set()) for p in pens}
    detail = []
    for bb, rec in r["seals"].items():
        c = rec["cand"]
        if c.confidence < rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE or not rec["plugs"]:
            continue
        for poly, kind, e in rec["plugs"]:
            if e is None:
                continue
            p, q = edge_pts(bb, e)
            sides = defaultdict(set)
            for fc in faces:
                hit = collinear_jambs(fc, p, q, off_tol, reach)
                if hit is None:
                    continue
                sides[fc.pen].add(hit[0])
                if verbose:
                    detail.append((slug, tuple(round(v) for v in bb), e, kind, str(fc.pen), hit[0], round(hit[1], 1), round(_line_length(fc.p1, fc.p2))))
            for pen, ss in sides.items():
                if "through" in ss:
                    per_pen[pen]["through"].add(bb)
                n = len(ss - {"through"})
                if n >= 1:
                    per_pen[pen]["doors1"].add(bb)
                if n >= 2:
                    per_pen[pen]["doors2"].add(bb)
    for c in conf_windows:
        x0, y0, x1, y1 = c.bbox
        if (x1 - x0) >= (y1 - y0):
            p, q = (x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)
            half = (y1 - y0) / 2
        else:
            p, q = ((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)
            half = (x1 - x0) / 2
        sides = defaultdict(set)
        for fc in faces:
            hit = collinear_jambs(fc, p, q, half + off_tol, reach)
            if hit is None or hit[0] == "through":
                continue
            sides[fc.pen].add(hit[0])
        for pen, ss in sides.items():
            if len(ss) >= 1:
                per_pen[pen]["win1"].add(tuple(c.bbox))
            if len(ss) >= 2:
                per_pen[pen]["win2"].add(tuple(c.bbox))
    n_plugged = sum(1 for bb, rec in r["seals"].items()
                    if rec["cand"].confidence >= rooms.ROOM_BBOX_SEAL_MIN_CONFIDENCE and rec["plugs"])
    print(f"\n=== {slug} f={f:.3f}: plugged conf doors {n_plugged}, conf straight windows {len(conf_windows)}  "
          f"(off_tol {off_tol}, reach {reach:.1f})")
    print(f"{'pen':22} {'D both':>6} {'D one':>5} {'D thru':>6} {'W both':>6} {'W one':>5}")
    for pen in pens:
        d = per_pen[pen]
        print(f"{str(pen):22} {len(d['doors2']):6d} {len(d['doors1']):5d} {len(d['through']):6d} "
              f"{len(d['win2']):6d} {len(d['win1']):5d}")
    if verbose:
        for row in sorted(detail):
            print("   ", row)
    return {str(p): {k: sorted(map(str, v)) for k, v in d.items()} for p, d in per_pen.items()}


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[1:] if a != "-v"] or DEFAULT
    out = {}
    for a in args:
        slug, _, fac = a.partition("@")
        out[a] = census(slug, float(fac) if fac else None, verbose)
    with open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step11/jamb_pens.json", "w") as fh:
        json.dump(out, fh, indent=1)
