"""Jamb-seek census: for every door edge on every sheet, at EACH end, the
distance from the bbox corner outward to the first sample within the plug
half-width of wall material (the jamb), and the ALONG-LINE extent of material
from there outward: `run_hug` = consecutive 1px samples within
ROOM_PLUG_NEAR_PX, `run_on` = length of the first piece of the edge line's
intersection with the material beyond the jamb. Records the edge's verdict so
the true class (kept interrupted plugs' anchors) and the candidates for an
extension (ends whose jamb lies beyond SEAL) can be separated.

  .venv/bin/python jamb_seek_census.py s01 s02 ... >> jamb_seek.jsonl
"""
import json
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402

REACH = 120.0
RUN_MAX = 300.0
OUTF = "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/jamb_seek.jsonl"


def end_stats(p, ux, uy, mat, half, near):
    """From corner p going OUTWARD (direction -u)."""
    jamb = None
    for k in range(0, int(REACH) + 1):
        if Point(p[0] - ux * k, p[1] - uy * k).distance(mat) <= half:
            jamb = float(k)
            break
    if jamb is None:
        return None, None, None
    run_hug = 0
    for k in range(int(jamb), int(jamb + RUN_MAX)):
        if Point(p[0] - ux * k, p[1] - uy * k).distance(mat) <= near:
            run_hug += 1
        else:
            break
    a = (p[0] - ux * jamb, p[1] - uy * jamb)
    b = (p[0] - ux * (jamb + RUN_MAX), p[1] - uy * (jamb + RUN_MAX))
    inter = LineString([a, b]).intersection(mat.buffer(0.5))
    run_on = 0.0
    if not inter.is_empty:
        pieces = sorted(getattr(inter, "geoms", [inter]), key=lambda g: Point(a).distance(g))
        first = pieces[0]
        if Point(a).distance(first) <= 1.5:
            run_on = first.length
    return jamb, float(run_hug), run_on


out = open(OUTF, "a")
for slug in sys.argv[1:]:
    pages = H.load(slug)
    for page in pages:
        calls = []
        o_plugs, o_restrict = rooms._door_plugs, rooms._restrict_swing_plugs

        def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED):
            res = o_plugs(bbox, wall_material, skip_edges, gates=gates)
            calls.append({"bbox": tuple(bbox), "mat": wall_material, "skip": frozenset(skip_edges), "gates": gates, "out": res, "cand": None, "restricted": None})
            return res

        def tap_restrict(c, plugs):
            res = o_restrict(c, plugs)
            for call in reversed(calls):
                if call["cand"] is None:
                    call["cand"] = c
                    call["restricted"] = res
                    break
            return res

        rooms._door_plugs, rooms._restrict_swing_plugs = tap_plugs, tap_restrict
        try:
            ents, extras = H.run(page)
        finally:
            rooms._door_plugs, rooms._restrict_swing_plugs = o_plugs, o_restrict
        last = {}
        for call in calls:
            if call["cand"] is not None:
                last[call["cand"].candidate_id] = call
        n = 0
        for cid, call in last.items():
            c = call["cand"]
            x0, y0, x1, y1 = call["bbox"]
            edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
            hinge = rooms._swing_hinge_edges(c)
            q = {e: k for _, k, e in call["out"]}
            r = {e: k for _, k, e in (call["restricted"] or [])}
            g = call["gates"]
            half, near = g.ROOM_PLUG_HALF_WIDTH_PX, rooms.ROOM_PLUG_NEAR_PX
            for e, (p, qq) in enumerate(edges):
                if e in call["skip"]:
                    continue
                L = math.hypot(qq[0] - p[0], qq[1] - p[1])
                if L < 1e-6:
                    continue
                ux, uy = (qq[0] - p[0]) / L, (qq[1] - p[1]) / L
                ja, ha, oa = end_stats(p, ux, uy, call["mat"], half, near)
                jb, hb, ob = end_stats(qq, -ux, -uy, call["mat"], half, near)
                cx, cy = (p[0] + qq[0]) / 2, (p[1] + qq[1]) / 2
                d = H.denom_at(slug, cx, cy) or 50.0
                rec = {
                    "slug": slug, "page": page.page_number, "id": cid, "conf": round(c.confidence, 2),
                    "type": c.evidence.get("assembly_type"), "layout": c.evidence.get("swing_layout"),
                    "bbox": [round(v, 1) for v in call["bbox"]], "edge": e, "len": round(L, 1),
                    "hinge": sorted(hinge) if hinge else None, "raw": q.get(e), "kept": r.get(e),
                    "jamb_a": ja, "hug_a": ha, "on_a": None if oa is None else round(oa, 1),
                    "jamb_b": jb, "hug_b": hb, "on_b": None if ob is None else round(ob, 1),
                    "seal": round(g.ROOM_OPENING_SEAL_PX, 2), "half": round(half, 2),
                    "factor": round(page.scale_factor, 3), "denom": d, "mmpx": round(0.16933 * d, 3),
                    "cap": round(g.WALL_MAX_THICKNESS_PX, 1),
                }
                out.write(json.dumps(rec) + "\n")
                n += 1
        out.flush()
        print(slug, page.page_number, "doors", len(last), "edges", n, flush=True)
