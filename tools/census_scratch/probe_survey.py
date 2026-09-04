"""probe_survey.py <slug>... — every KEPT interrupted plug on each sheet at
the default seal, with the two anchor classifications:
  elem: par/perp/obl/--- from the wall elements (segments+faces) the touching
        samples lie on
  across: min over the end window's touching samples of the across-extent of
        the connected material piece through a +-72px probe (half-width 5)
  along: extent of material along the edge line outward from the corner
Prints hinge-less doors first (the class the veto would apply to), then a
distribution over hinge-derived doorway edges (the true class)."""
import math
import sys
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402
from detection import rooms  # noqa: E402
from detection.geometry import _line_angle_deg, _angle_diff_mod180, _line_length  # noqa: E402

PROBE = 72.0


def survey(slug):
    pages = H.load(slug)
    out_lines = []
    for page in pages:
        calls = []
        o_plugs, o_restrict = rooms._door_plugs, rooms._restrict_swing_plugs

        def tap_plugs(bbox, wall_material, skip_edges=frozenset(), *, gates=rooms.ROOM_GATES_UNSCALED):
            out = o_plugs(bbox, wall_material, skip_edges, gates=gates)
            calls.append({"bbox": bbox, "mat": wall_material, "skip": skip_edges, "gates": gates,
                          "out": out, "cand": None, "restricted": None})
            return out

        def tap_restrict(c, plugs):
            out = o_restrict(c, plugs)
            for call in reversed(calls):
                if call["cand"] is None:
                    call["cand"] = c
                    call["restricted"] = out
                    break
            return out

        rooms._door_plugs, rooms._restrict_swing_plugs = tap_plugs, tap_restrict
        try:
            ents, extras = H.run(page, keep_network=True)
        finally:
            rooms._door_plugs, rooms._restrict_swing_plugs = o_plugs, o_restrict
        net = extras["network"]
        segs = list(net.segments)
        faces = list(net.faces)
        seg_geoms = [LineString([s.p1, s.p2]).buffer(s.thickness_px / 2 + 2.0, cap_style=2) for s in segs]
        face_geoms = [LineString([f.p1, f.p2]).buffer(2.0, cap_style=3) for f in faces]
        f = page.scale_factor

        def elem_class(pts, edge_angle):
            hits = []
            for p in pts:
                for s, g in zip(segs, seg_geoms):
                    if g.distance(p) <= 0.01:
                        hits.append(_angle_diff_mod180(_line_angle_deg(s.p1, s.p2), edge_angle))
                for fc, g in zip(faces, face_geoms):
                    if g.distance(p) <= 0.01:
                        hits.append(_angle_diff_mod180(_line_angle_deg(fc.p1, fc.p2), edge_angle))
            if any(a <= 15 for a in hits):
                return "par"
            if any(a >= 75 for a in hits):
                return "perp"
            if hits:
                return "obl"
            return "---"

        def across_extent(pt, ux, uy, mat, half):
            nx, ny = -uy, ux
            probe = LineString([(pt.x - nx * PROBE, pt.y - ny * PROBE),
                                (pt.x + nx * PROBE, pt.y + ny * PROBE)]).buffer(half, cap_style=2)
            hit = probe.intersection(mat)
            if hit.is_empty:
                return 0.0
            best = 0.0
            for g in getattr(hit, "geoms", [hit]):
                if g.distance(pt) > half + 0.01:
                    continue
                bx0, by0, bx1, by1 = g.bounds
                offs = [(cx - pt.x) * nx + (cy - pt.y) * ny
                        for cx, cy in ((bx0, by0), (bx1, by1), (bx0, by1), (bx1, by0))]
                best = max(best, max(offs) - min(offs))
            return best

        def along_extent(corner, ux, uy, mat, half, reach):
            # material along the edge line from the corner OUTWARD (direction -u)
            probe = LineString([corner, (corner[0] - ux * reach, corner[1] - uy * reach)]).buffer(half, cap_style=2)
            hit = probe.intersection(mat)
            if hit.is_empty:
                return 0.0
            return max(abs((cx - corner[0]) * -ux + (cy - corner[1]) * -uy)
                       for g in getattr(hit, "geoms", [hit]) for cx, cy in g.exterior.coords)

        for call in calls:
            c = call["cand"]
            if c is None or not call["restricted"]:
                continue
            kept = {e: k for _, k, e in call["restricted"]}
            if "interrupted" not in kept.values():
                continue
            gates = call["gates"]
            mat = call["mat"]
            hinge = rooms._swing_hinge_edges(c)
            x0, y0, x1, y1 = c.bbox
            edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
            for e, (p, q) in enumerate(edges):
                if kept.get(e) != "interrupted":
                    continue
                length = math.hypot(q[0] - p[0], q[1] - p[1])
                ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
                S = gates.ROOM_OPENING_SEAL_PX
                a = (p[0] - ux * S, p[1] - uy * S)
                b = (q[0] + ux * S, q[1] + uy * S)
                ext = length + 2 * S
                line = LineString([a, b])
                n = max(int(ext / rooms.ROOM_PLUG_SAMPLE_PX), 8) + 1
                pts = [line.interpolate(ext * i / (n - 1)) for i in range(n)]
                d = [pt.distance(mat) for pt in pts]
                quarter = n // 4
                win = min(quarter, int(math.ceil(gates.ROOM_PLUG_ANCHOR_WIN_PX / rooms.ROOM_PLUG_SAMPLE_PX)) + 1)
                half = gates.ROOM_PLUG_HALF_WIDTH_PX
                ta = [pts[i] for i in range(win) if d[i] <= half]
                tb = [pts[i] for i in range(n - win, n) if d[i] <= half]
                ang = _line_angle_deg(p, q)
                ca, cb = elem_class(ta, ang), elem_class(tb, ang)
                xa = min((across_extent(pt, ux, uy, mat, half) for pt in ta), default=-1)
                xb = min((across_extent(pt, ux, uy, mat, half) for pt in tb), default=-1)
                reach = S + gates.WALL_MAX_THICKNESS_PX
                la = along_extent(p, ux, uy, mat, half, reach)
                lb = along_extent(q, -ux, -uy, mat, half, reach)
                tag = "HINGELESS" if hinge is None else ("hinge" if e in hinge else "nonhinge")
                out_lines.append(
                    f"{slug} p{page.page_number} f={f:.2f} {c.candidate_id} conf={c.confidence:.2f} "
                    f"type={c.evidence.get('assembly_type')} layout={c.evidence.get('swing_layout')} "
                    f"bbox={tuple(round(v) for v in c.bbox)} edge={e} L={length:.0f} {tag} "
                    f"elem={ca}/{cb} across={xa:.0f}/{xb:.0f} along={la:.0f}/{lb:.0f}")
    return out_lines


if __name__ == "__main__":
    for slug in sys.argv[1:]:
        for line in survey(slug):
            print(line, flush=True)
