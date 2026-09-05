"""Corpus census of doorway JAMB GAPS in world mm: for every _door_plugs call
on every sheet, every non-skipped edge, the distance along the edge from each
bbox corner OUTWARD to the (dilated) wall material, with the edge's verdict.

  .venv/bin/python jamb_census.py s01 s02 ...  > jamb_census.jsonl
"""
import json
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

REACH = 100.0


def gap_out(p, ux, uy, mat):
    """Distance from corner p outward (direction -u) to the material; None past REACH."""
    for k in range(0, int(REACH) + 1):
        pt = (p[0] - ux * k, p[1] - uy * k)
        from shapely.geometry import Point
        if Point(pt).distance(mat) <= 0.01:
            return float(k)
    return None


def inside_depth(p, ux, uy, mat):
    """How far INTO the bbox edge the material already extends from corner p (material overlapping the edge)."""
    from shapely.geometry import Point
    if Point(p).distance(mat) > 0.01:
        return 0.0
    for k in range(0, int(REACH) + 1):
        pt = (p[0] + ux * k, p[1] + uy * k)
        if Point(pt).distance(mat) > 0.01:
            return float(k)
    return REACH


out = open("/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/jamb_census.jsonl", "a")
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
        # last call per candidate
        last = {}
        for call in calls:
            if call["cand"] is not None:
                last[call["cand"].candidate_id] = call
        for cid, call in last.items():
            c = call["cand"]
            x0, y0, x1, y1 = call["bbox"]
            edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
            hinge = rooms._swing_hinge_edges(c)
            q = {e: k for _, k, e in call["out"]}
            r = {e: k for _, k, e in (call["restricted"] or [])}
            g = call["gates"]
            for e, (p, qq) in enumerate(edges):
                if e in call["skip"]:
                    continue
                L = math.hypot(qq[0] - p[0], qq[1] - p[1])
                if L < 1e-6:
                    continue
                ux, uy = (qq[0] - p[0]) / L, (qq[1] - p[1]) / L
                ga = gap_out(p, ux, uy, call["mat"])
                gb = gap_out(qq, -ux, -uy, call["mat"])
                ia = inside_depth(p, ux, uy, call["mat"])
                ib = inside_depth(qq, -ux, -uy, call["mat"])
                cx, cy = (p[0] + qq[0]) / 2, (p[1] + qq[1]) / 2
                rec = {
                    "slug": slug, "page": page.page_number, "id": cid, "conf": round(c.confidence, 2),
                    "type": c.evidence.get("assembly_type"), "layout": c.evidence.get("swing_layout"),
                    "bbox": [round(v, 1) for v in call["bbox"]], "edge": e, "len": round(L, 1),
                    "hinge": sorted(hinge) if hinge else None, "raw": q.get(e), "kept": r.get(e),
                    "gap_a_px": ga, "gap_b_px": gb, "in_a_px": ia, "in_b_px": ib,
                    "gap_a_mm": None if ga is None else round(H.mm(slug, ga, cx, cy) or -1, 0),
                    "gap_b_mm": None if gb is None else round(H.mm(slug, gb, cx, cy) or -1, 0),
                    "seal_px": round(g.ROOM_OPENING_SEAL_PX, 2), "half_px": round(g.ROOM_PLUG_HALF_WIDTH_PX, 2),
                    "factor": round(page.scale_factor, 3), "denom": H.denom_at(slug, cx, cy),
                }
                out.write(json.dumps(rec) + "\n")
        out.flush()
        print(slug, page.page_number, "doors", len(last), flush=True)
