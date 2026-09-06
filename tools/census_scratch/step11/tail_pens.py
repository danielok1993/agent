"""Per confident door with an INTERRUPTED plug (the doorway signature), per
pen: what the pen's ink does at each of the plug's two tails — the jamb
envelopes the room stage's own final plug reaches (tail polygon = the plug
beyond the bbox corner, i.e. what _clip_plug_tails kept).

Ink classes at a tail, per face of the pen (door-zone faces excluded):
  end   — a face ENDPOINT lies inside the tail envelope (the wall face or a
          perpendicular return stops at the jamb)
  cross — the face passes through the envelope with both endpoints outside
          (a dimension extension line, a furniture edge running past)
  solid — a same-pen paired SEGMENT's solid intersects the envelope

Prints, per sheet, a per-pen summary: doorways where BOTH tails see an
'end' or 'solid' of this pen (owned), one tail (touched), and the number of
doorways where the pen only CROSSES. With -v, a per-door matrix.

Usage: .venv/bin/python tools/census_scratch/step11/tail_pens.py [slug[@factor] ...] [-v]
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9")
from s01_common import *  # noqa: F401,F403
from detection.geometry import _line_length  # noqa: E402
from shapely.geometry import box, LineString, Point  # noqa: E402

DEFAULT = ["s01", f"s01@{F542}", "s02", "s03", "s04", "s08", "s12", "s17"]
BIG = 1e5


def census(slug, factor, verbose=False):
    page = H.load(slug)[0]
    f = page.scale_factor if factor is None else factor
    r = run_tapped(page, factor)
    net = r["extras"]["network"]
    all_geo = r["extras"]["all_geo"]
    doors = [c for c in all_geo if c.entity_type == "door"]
    zones = [(c.bbox[0] - 2, c.bbox[1] - 2, c.bbox[2] + 2, c.bbox[3] + 2) for c in doors]

    def in_zone(a, b):
        return any(zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
                   and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
                   for zx0, zy0, zx1, zy1 in zones)

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
    summary = {p: dict(owned=set(), touched=set(), cross_only=set()) for p in pens}
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
            if e in (0, 1):
                tails = [poly.difference(box(x0 - BIG, y0 - BIG, x0, y1 + BIG)),   # beyond x0 side
                         poly.difference(box(x1, y0 - BIG, x1 + BIG, y1 + BIG))]
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
                    end = cross = solid = False
                    for fc in faces:
                        if fc.pen != pen:
                            continue
                        ln = LineString([fc.p1, fc.p2])
                        if not ln.intersects(env):
                            continue
                        if env.intersects(Point(fc.p1)) or env.intersects(Point(fc.p2)):
                            end = True
                        else:
                            cross = True
                    for p, sp in seg_pen:
                        if p == pen and sp.intersects(t):
                            solid = True
                    cls.append("E" if end else ("S" if solid else ("x" if cross else ".")))
                per_pen[pen] = cls
                hits = sum(1 for k in cls if k in "ES")
                if hits == 2:
                    summary[pen]["owned"].add((bb, e))
                elif hits == 1:
                    summary[pen]["touched"].add((bb, e))
                elif "x" in cls:
                    summary[pen]["cross_only"].add((bb, e))
            rows.append((tuple(round(v) for v in bb), e, {str(p): "".join(v) for p, v in per_pen.items()}))
    print(f"\n=== {slug} f={f:.3f}: interrupted doorway plugs {n_doorways}")
    print(f"{'pen':22} {'owned':>5} {'touch':>5} {'xonly':>5}")
    for pen in pens:
        d = summary[pen]
        print(f"{str(pen):22} {len(d['owned']):5d} {len(d['touched']):5d} {len(d['cross_only']):5d}")
    if verbose:
        for bb, e, m in sorted(rows):
            print("   ", bb, "edge", e, "  ".join(f"{p}:{v}" for p, v in m.items()))
    return {str(p): {k: len(v) for k, v in d.items()} for p, d in summary.items()}


if __name__ == "__main__":
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[1:] if a != "-v"] or DEFAULT
    out = {}
    for a in args:
        slug, _, fac = a.partition("@")
        out[a] = census(slug, float(fac) if fac else None, verbose)
    with open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step11/tail_pens.json", "w") as fh:
        json.dump(out, fh, indent=1)
