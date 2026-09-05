"""Collinear-face census: for every door edge end on every sheet (at the
sheet's factor, plus s01 at 0.542), the nearest BARRIER face collinear with
the edge (angle <= 4 deg, perpendicular offset <= ROOM_PLUG_NEAR_PX at its
near end) whose near end lies OUTWARD from the corner by g in (−2, 60] px —
the jamb-seek discriminator — with the edge's verdict.

  .venv/bin/python collinear_census.py s01 ... >> collinear.jsonl
"""
import json
import math
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_angle_deg, _angle_diff_mod180, _line_length  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

OUTF = "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch/step9/collinear.jsonl"
ANG = 4.0
SEEK_MAX = 60.0


def nearest_collinear(corner, ux, uy, lines, near):
    """lines: list of (p1, p2, meta). Outward direction is (ux, uy)."""
    best = None
    ang_e = math.degrees(math.atan2(uy, ux))
    for p1, p2, meta in lines:
        if _angle_diff_mod180(_line_angle_deg(p1, p2), ang_e) > ANG:
            continue
        # axial positions of the face ends from the corner along outward u
        t1 = (p1[0] - corner[0]) * ux + (p1[1] - corner[1]) * uy
        t2 = (p2[0] - corner[0]) * ux + (p2[1] - corner[1]) * uy
        tn, tf = (t1, t2) if t1 <= t2 else (t2, t1)
        if tf < -2.0 or tn > SEEK_MAX:
            continue
        # perpendicular offset at the near end
        pn = p1 if t1 <= t2 else p2
        off = abs((pn[0] - corner[0]) * -uy + (pn[1] - corner[1]) * ux)
        if off > near:
            continue
        g = max(tn, 0.0)
        if best is None or g < best[0]:
            best = (g, off, tf - tn, meta)
    return best


out = open(OUTF, "a")
for arg in sys.argv[1:]:
    slug, _, fac = arg.partition("@")
    factor = float(fac) if fac else None
    pages = H.load(slug)
    for page in pages:
        calls = []
        o_plugs, o_restrict = rooms._door_plugs, rooms._restrict_swing_plugs

        def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED):
            res = o_plugs(bbox, wall_material, skip_edges, gates=gates)
            calls.append({"bbox": tuple(bbox), "skip": frozenset(skip_edges), "gates": gates, "out": res, "cand": None, "restricted": None})
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
            ents, extras = H.run(page, factor=factor, keep_network=True)
        finally:
            rooms._door_plugs, rooms._restrict_swing_plugs = o_plugs, o_restrict
        net = extras["network"]
        f = page.scale_factor if factor is None else factor
        gates = rooms.RoomGates.at(f)
        # barrier faces: the ones with a barrier extent — approximate with paired faces + stroked faces at the gate
        paired = net.paired_face_indices()
        ref = net.wall_stroke_reference()
        gate = max(rooms.WALL_MIN_STROKE_WIDTH_PX, rooms.ROOM_BARRIER_STROKE_RATIO * ref) if hasattr(rooms, "WALL_MIN_STROKE_WIDTH_PX") else 0.75 * ref
        lines = []
        for fc in net.faces:
            barrier = bool(fc.indices & paired) or (fc.stroked and fc.stroke_width >= gate) or getattr(fc, "wall_fill", False) or getattr(fc, "material_backed", False)
            if not barrier:
                continue
            lines.append((fc.p1, fc.p2, {"sw": round(fc.stroke_width, 2), "paired": bool(fc.indices & paired), "len": round(_line_length(fc.p1, fc.p2), 1)}))
        for s in net.segments:
            L = _line_length(s.p1, s.p2)
            if L < 1e-6:
                continue
            nx, ny = -(s.p2[1] - s.p1[1]) / L, (s.p2[0] - s.p1[0]) / L
            h = s.thickness_px / 2
            for sign in (1, -1):
                lines.append(((s.p1[0] + sign * nx * h, s.p1[1] + sign * ny * h), (s.p2[0] + sign * nx * h, s.p2[1] + sign * ny * h),
                              {"seg": True, "th": round(s.thickness_px, 1), "len": round(L, 1)}))
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
            for e, (p, qq) in enumerate(edges):
                if e in call["skip"]:
                    continue
                L = math.hypot(qq[0] - p[0], qq[1] - p[1])
                if L < 1e-6:
                    continue
                ux, uy = (qq[0] - p[0]) / L, (qq[1] - p[1]) / L
                ca = nearest_collinear(p, -ux, -uy, lines, rooms.ROOM_PLUG_NEAR_PX)
                cb = nearest_collinear(qq, ux, uy, lines, rooms.ROOM_PLUG_NEAR_PX)
                cx, cy = (p[0] + qq[0]) / 2, (p[1] + qq[1]) / 2
                d = H.denom_at(slug, cx, cy) or 50.0
                rec = {
                    "slug": slug, "factor": round(f, 3), "id": cid, "conf": round(c.confidence, 2),
                    "type": c.evidence.get("assembly_type"), "layout": c.evidence.get("swing_layout"),
                    "bbox": [round(v, 1) for v in call["bbox"]], "edge": e, "len": round(L, 1),
                    "hinge": sorted(hinge) if hinge else None, "raw": q.get(e), "kept": r.get(e),
                    "col_a": None if ca is None else {"g": round(ca[0], 1), "off": round(ca[1], 1), "run": round(ca[2], 1), **ca[3]},
                    "col_b": None if cb is None else {"g": round(cb[0], 1), "off": round(cb[1], 1), "run": round(cb[2], 1), **cb[3]},
                    "seal": round(gates.ROOM_OPENING_SEAL_PX, 2), "half": round(gates.ROOM_PLUG_HALF_WIDTH_PX, 2),
                    "mmpx": round(0.16933 * d, 3),
                }
                out.write(json.dumps(rec) + "\n")
                n += 1
        out.flush()
        print(slug, f, "doors", len(last), "edges", n, flush=True)
