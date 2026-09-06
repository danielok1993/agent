"""Step 16 — what makes s11's storage cupboard a SPACE when a cavity-wall
reveal strip is not: the candidate discriminators of the brief measured on
both classes, on the pipeline's exact inputs, all 20 sheets at their factors.

Populations, read off detect_rooms' own locals through the free-space tap
(`face_lines`, `cap_lines`, `solid_parts`, `solids`, `wall_segments`,
`network`, `door_barriers`) and the `_drop_window_exterior_sides` tap:

  calls   every `_is_band_pocket` call (= every entrance-less, window-less
          component past the filters and the recess rule) with the rule's
          own verdict — the false class the ceiling would open lies here
  rooms   every room the stage emits (ENTERED_ALL): the true class the rule
          would see if its entrance did not spare it

Per component, beside the shipped reading (spacing, `_side_wall_covers`):

  (a) text     text spans centred inside (the rule's veto) and VECTOR-TEXT
               glyph strokes inside (`walls._vector_text_indices` — the rows
               the wall network already recognises; a stroke counts when its
               midpoint lies in the component)
  (b) backing  per long side, how much of the side's wall-lying length has a
               wall SOLID behind it — a paired segment's band, a wall-rated
               fill, an accepted white wall — read on a probe line
               PROBE_BEHIND_PX outward of the boundary run (past the line
               barrier's own 2px buffer around a lone face) against the
               stage's `solids`; plus the median span of solid behind the
               side (a ray outward from each sample point, the contiguous
               solid it enters first) — the thickness of the wall behind,
               0 when there is none — split into SEGMENT solids and OTHER
               solids (fills, white walls, bridges, jamb rings)
  (c) pens     the pens (quantised colour, max stroke width) of the network
               faces whose lines cover each side, and whether both sides
               share a pen (the "could have paired as one wall" premise)
  (d) ends     the component's SHORT-axis runs read the same way as the long
               sides (cover along wall, backing behind): a cupboard is
               closed by walls at both ends, a reveal ends at an opening
  (e) resume   per long side, whether the face bounding it is a WALL FACE
               WHOSE WALL LIES ON THE POCKET'S SIDE: a reveal / cavity
               closer / blocked opening is a stretch of a wall drawn without
               its leaf line, so the face bounding it pairs — elsewhere
               along its own drawn run, or as the flank of a segment
               resuming beyond the pocket's end — with a partner on the
               pocket's side; a cupboard's faces bound their walls on the
               FAR side (the partition beside it) or bound nothing (its
               front line). Read two ways: `near_face` — the merged network
               face covering the run has a paired segment whose centreline
               lies on the component's side of the face (face identity, no
               reach); `near_seg_gap` — the smallest along-axis gap from the
               component's extent to any paired segment whose flank line is
               collinear with the run (standoff 2 ± 1.5, angle tol) and whose
               centreline lies on the component's side (0 = overlapping)

Usage: .venv/bin/python tools/census_scratch/step16/backing_census.py [slugs...]
Writes step16/backing_census.json (BACKING_CENSUS_OUT to run several jobs).
"""
from __future__ import annotations

import json
import math
import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import LineString, Point, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from detection import rooms, walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("BACKING_CENSUS_OUT",
                          Path(__file__).resolve().parent / "backing_census.json"))
STANDOFF = rooms.ROOM_LINE_BARRIER_PX
BACK_TOL = rooms.ROOM_RECESS_BACK_TOL_PX
ANGLE_TOL = walls.WALL_PARALLEL_ANGLE_TOL
# The probe line behind a boundary run: the run lies at the 2px standoff
# off its face, the lone face's line barrier reaches 2px past the face, so
# anything at > 4px from the run is a SOLID's material (a paired segment's
# band is dilated 2px past its face too and spans its thickness beyond).
PROBE_BEHIND_PX = 7.0
RAY_START_PX = 4.5
RAY_MAX_PX = 120.0
SAMPLE_PX = 2.0


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def _mrr(poly):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rect = poly.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        return None
    c = list(rect.exterior.coords)[:4]
    if len(c) < 4:
        return None
    edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    lens = [_line_length(a, b) for a, b in edges]
    if lens[0] >= lens[1]:
        axis_edge, short_edge, short, long = edges[0], edges[1], lens[1], lens[0]
    else:
        axis_edge, short_edge, short, long = edges[1], edges[0], lens[0], lens[1]
    return {"axis_edge": axis_edge, "short_edge": short_edge, "short": short,
            "long": long, "centre": (rect.centroid.x, rect.centroid.y), "corners": c}


def _runs_by_side(poly, axis_edge, centre):
    """The polygon's boundary runs parallel to `axis_edge`, classed to a
    side by the sign of their offset from `centre` (as _side_wall_covers),
    with each run's OUTWARD unit normal (away from the centre)."""
    (ax, ay), (bx, by) = axis_edge
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = -uy, ux
    cx, cy = centre
    angle = _line_angle_deg((ax, ay), (bx, by))
    sides = ([], [])
    coords = list(poly.exterior.coords)
    for a, b in zip(coords, coords[1:]):
        rl = _line_length(a, b)
        if rl < 1e-6 or _angle_diff_mod180(angle, _line_angle_deg(a, b)) > ANGLE_TOL:
            continue
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        off = (mx - cx) * nx + (my - cy) * ny
        side = 0 if off < 0.0 else 1
        out_n = (-nx, -ny) if side == 0 else (nx, ny)
        sides[side].append((a, b, out_n))
    return sides, (ux, uy), L


def _union_len(intervals):
    total = 0.0
    cur_lo = cur_hi = None
    for lo, hi in sorted(intervals):
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None:
                total += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
        elif hi > cur_hi:
            cur_hi = hi
    if cur_hi is not None:
        total += cur_hi - cur_lo
    return total


def _behind(run, out_n, stretches, solids_seg, solids_other):
    """For the wall-lying stretches of one run: the length of the probe
    line PROBE_BEHIND_PX outward that lies in a solid (segment / other),
    and the per-sample span of contiguous solid entered by a ray outward."""
    (ax, ay), (bx, by) = run
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    ox, oy = out_n
    backed_seg = backed_any = 0.0
    spans_seg, spans_any = [], []
    solids_any = unary_union([solids_seg, solids_other]) if not solids_other.is_empty else solids_seg
    # A paired face's barrier extent and its segment's flank both cover the
    # same stretch: union the stretches before probing, as the shipped
    # reading unions them before summing.
    merged = []
    for lo, hi in sorted(stretches):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    for lo, hi in merged:
        if hi - lo <= 1e-6:
            continue
        p = (ax + ux * lo + ox * PROBE_BEHIND_PX, ay + uy * lo + oy * PROBE_BEHIND_PX)
        q = (ax + ux * hi + ox * PROBE_BEHIND_PX, ay + uy * hi + oy * PROBE_BEHIND_PX)
        probe = LineString([p, q])
        backed_seg += probe.intersection(solids_seg).length
        backed_any += probe.intersection(solids_any).length
        n = max(1, int((hi - lo) / SAMPLE_PX))
        for i in range(n + 1):
            t = lo + (hi - lo) * i / n
            sx, sy = ax + ux * t, ay + uy * t
            ray = LineString([(sx + ox * RAY_START_PX, sy + oy * RAY_START_PX),
                              (sx + ox * RAY_MAX_PX, sy + oy * RAY_MAX_PX)])
            for geom, acc in ((solids_seg, spans_seg), (solids_any, spans_any)):
                hit = ray.intersection(geom)
                span = 0.0
                if not hit.is_empty:
                    pieces = [g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "LineString"]
                    pieces.sort(key=lambda g: Point(ray.coords[0]).distance(g))
                    if pieces and Point(ray.coords[0]).distance(pieces[0]) <= 0.75:
                        span = pieces[0].length
                acc.append(span)
    return backed_seg, backed_any, spans_seg, spans_any


def _median(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[len(s) // 2]


def _near_side_segments(run, out_n, ctx):
    """(e) for one boundary run: the merged faces covering it that are
    PAIRED with a segment whose centreline lies on the component's side
    (near_face), and the along-axis gap to the nearest paired segment whose
    flank line is collinear with the run and whose band lies on the
    component's side (near_seg_gap; None when there is none)."""
    (ax, ay), (bx, by) = run
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    ox, oy = out_n                          # outward = away from the component
    angle = _line_angle_deg((ax, ay), (bx, by))
    near_face_len = far_face_len = lone_face_len = 0.0
    for f in _covering_faces(run, ctx["faces"]):
        segs = {id(s): s for pi in f.indices for s in ctx["seg_by_path"].get(pi, ())}
        flen = _line_length(f.p1, f.p2)
        if not segs:
            lone_face_len += flen
            continue
        near = far = False
        for s in segs.values():
            mx, my = (s.p1[0] + s.p2[0]) / 2.0, (s.p1[1] + s.p2[1]) / 2.0
            # the centreline's offset from the run along the OUTWARD normal
            d = (mx - ax) * ox + (my - ay) * oy
            if d < 0:
                near = True
            else:
                far = True
        if near:
            near_face_len += flen
        elif far:
            far_face_len += flen
    best_gap = None
    best = None
    for s in ctx["wall_segments"]:
        sl = _line_length(s.p1, s.p2)
        if sl < 1e-6 or _angle_diff_mod180(angle, _line_angle_deg(s.p1, s.p2)) > ANGLE_TOL:
            continue
        # centreline offset from the run along the outward normal, read at
        # the run's midpoint projected onto the segment's line
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        sux, suy = (s.p2[0] - s.p1[0]) / sl, (s.p2[1] - s.p1[1]) / sl
        t = (mx - s.p1[0]) * sux + (my - s.p1[1]) * suy
        cx, cy = s.p1[0] + sux * t, s.p1[1] + suy * t
        d = (cx - mx) * ox + (cy - my) * oy
        if d >= 0:
            continue                        # band on the far side (or on the run)
        # The band lies on the component's side of the face: its centreline
        # is inward of the run and its OUTWARD flank lies on the face line,
        # STANDOFF outward of the run (the run is the face's standoff line).
        flank = d + s.thickness_px / 2.0
        if abs(flank - STANDOFF) > BACK_TOL:
            continue
        t1 = (s.p1[0] - ax) * ux + (s.p1[1] - ay) * uy
        t2 = (s.p2[0] - ax) * ux + (s.p2[1] - ay) * uy
        lo, hi = min(t1, t2), max(t1, t2)
        gap = max(0.0, lo - L, -hi)
        if best_gap is None or gap < best_gap:
            best_gap, best = gap, s
    return near_face_len, far_face_len, lone_face_len, best_gap, best


def _side_readings(poly, axis_edge, centre, face_lines, cap_lines, solids_seg, solids_other, ctx):
    """Per side: cover (shipped semantics), backed fractions, median spans,
    covering pens, and the (e) readings."""
    faces = ctx["faces"]
    sides, (ux, uy), long = _runs_by_side(poly, axis_edge, centre)
    (ax, ay) = axis_edge[0]
    out = []
    for runs in sides:
        cov_iv, backed_seg, backed_any = [], 0.0, 0.0
        spans_seg, spans_any, pens = [], [], {}
        near_len = far_len = lone_len = 0.0
        seg_gap, seg_best = None, None
        for a, b, out_n in runs:
            rl = _line_length(a, b)
            rux, ruy = (b[0] - a[0]) / rl, (b[1] - a[1]) / rl
            stretches = rooms._run_wall_cover((a, b), face_lines, cap_lines)
            for lo, hi in stretches:
                ta = (a[0] + rux * lo - ax) * ux + (a[1] + ruy * lo - ay) * uy
                tb = (a[0] + rux * hi - ax) * ux + (a[1] + ruy * hi - ay) * uy
                cov_iv.append((max(min(ta, tb), 0.0), min(max(ta, tb), long)))
            bs, ba, ss, sa = _behind((a, b), out_n, stretches, solids_seg, solids_other)
            backed_seg += bs
            backed_any += ba
            spans_seg.extend(ss)
            spans_any.extend(sa)
            for f in _covering_faces((a, b), faces):
                key = (str(f.pen), round(f.stroke_width, 2), f.stroked)
                pens[key] = pens.get(key, 0.0) + _line_length(f.p1, f.p2)
            nl, fl, ll, g, s = _near_side_segments((a, b), out_n, ctx)
            near_len += nl
            far_len += fl
            lone_len += ll
            if g is not None and (seg_gap is None or g < seg_gap):
                seg_gap, seg_best = g, s
        out.append({
            "cover": round(_union_len(cov_iv) / long, 3) if long > 0 else 0.0,
            "backed_seg": round(backed_seg / long, 3) if long > 0 else 0.0,
            "backed_any": round(backed_any / long, 3) if long > 0 else 0.0,
            "span_seg_med": round(_median(spans_seg), 2),
            "span_any_med": round(_median(spans_any), 2),
            "pens": sorted(((k[0], k[1], k[2], round(v, 1)) for k, v in pens.items()),
                           key=lambda t: -t[3])[:4],
            # (e): covering-face length by class (px), and the segment reach
            "near_face_px": round(near_len, 1), "far_face_px": round(far_len, 1),
            "lone_face_px": round(lone_len, 1),
            "near_face": near_len > 0.0,
            "near_seg_gap": None if seg_gap is None else round(seg_gap, 1),
            "near_seg": None if seg_best is None else
            [[round(v, 1) for v in seg_best.p1], [round(v, 1) for v in seg_best.p2],
             round(seg_best.thickness_px, 2)],
        })
    return out


def _covering_faces(run, faces):
    """Network faces whose line lies beside the run at the barrier standoff
    and overlaps it along the run (the faces the cover was read off)."""
    (ax, ay), (bx, by) = run
    L = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / L, (by - ay) / L
    nx, ny = -uy, ux
    angle = _line_angle_deg((ax, ay), (bx, by))
    out = []
    for f in faces:
        if _angle_diff_mod180(angle, _line_angle_deg(f.p1, f.p2)) > ANGLE_TOL:
            continue
        t1 = (f.p1[0] - ax) * ux + (f.p1[1] - ay) * uy
        t2 = (f.p2[0] - ax) * ux + (f.p2[1] - ay) * uy
        lo, hi = max(min(t1, t2), 0.0), min(max(t1, t2), L)
        if hi - lo <= 1e-6:
            continue
        d1 = (f.p1[0] - ax) * nx + (f.p1[1] - ay) * ny
        d2 = (f.p2[0] - ax) * nx + (f.p2[1] - ay) * ny
        tm = (lo + hi) / 2.0
        d = d1 + (d2 - d1) * (tm - t1) / (t2 - t1) if abs(t2 - t1) > 1e-9 else d1
        if abs(abs(d) - STANDOFF) > BACK_TOL:
            continue
        out.append(f)
    return out


def _gt_class(slug, page_number, bbox):
    truth = load_truth(slug).page(page_number)
    best = ("unmatched", 0.0, "")
    for cls, items in (("confirmed", truth.confirmed),
                       ("false_positive", truth.false_positives),
                       ("deferred", truth.deferred)):
        for t in items:
            if t.type != "room":
                continue
            v = iou(tuple(bbox), tuple(t.bbox))
            if v >= 0.5 and v > best[1]:
                best = (cls, v, t.note or "")
    return best


# ---------------------------------------------------------------------------
# the chain
# ---------------------------------------------------------------------------
def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        rg = rooms.RoomGates.at(f)
        captured = {}
        calls = []
        o_fsc, o_drop, o_pocket = (rooms._free_space_components,
                                   rooms._drop_window_exterior_sides,
                                   rooms._is_band_pocket)

        def fsc(page, barriers):
            loc = sys._getframe(1).f_locals
            for k in ("face_lines", "cap_lines", "wall_segments", "door_barriers", "solid_parts"):
                captured[k] = list(loc[k])
            captured["solids"] = loc["solids"]
            captured["network"] = loc["network"]
            return o_fsc(page, barriers)

        def drop(rooms_list, windows, **k):
            captured["rooms"] = list(rooms_list)
            return o_drop(rooms_list, windows, **k)

        def pocket(comp, face_lines, text_spans, *, cap_lines=(),
                   gates=rooms.ROOM_GATES_UNSCALED):
            res = o_pocket(comp, face_lines, text_spans, cap_lines=cap_lines, gates=gates)
            calls.append((comp, bool(res)))
            return res

        rooms._free_space_components = fsc
        rooms._drop_window_exterior_sides = drop
        rooms._is_band_pocket = pocket
        try:
            H.run(p)
        finally:
            rooms._free_space_components = o_fsc
            rooms._drop_window_exterior_sides = o_drop
            rooms._is_band_pocket = o_pocket

        face_lines = captured.get("face_lines", [])
        cap_lines = captured.get("cap_lines", [])
        wall_segments = captured.get("wall_segments", [])
        solid_parts = captured.get("solid_parts", [])
        n_seg = len(wall_segments)
        solids_seg = unary_union(solid_parts[:n_seg]) if solid_parts[:n_seg] else Polygon()
        solids_other = unary_union(solid_parts[n_seg:]) if solid_parts[n_seg:] else Polygon()
        network = captured.get("network")
        faces = list(network.faces) if network is not None else []
        seg_by_path = {}
        for s in wall_segments:
            for pi in s.face_path_indices:
                seg_by_path.setdefault(pi, []).append(s)
        ctx = {"faces": faces, "seg_by_path": seg_by_path, "wall_segments": wall_segments}
        entrance = [g for conf, g in captured.get("door_barriers", [])
                    if conf >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE]
        pd = p.page_data
        text_spans = pd.text_spans
        glyph_idx = walls._vector_text_indices(pd.paths)
        # path_index is the extractor's ordinal, not the position in a
        # region-filtered page's list
        by_index = {pth.path_index: pth for pth in pd.paths}
        glyph_mids = []
        for i in glyph_idx:
            pth = by_index.get(i)
            if pth is None:
                continue
            b = pth.bbox
            glyph_mids.append(Point((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0))

        def reading(poly):
            m = _mrr(poly)
            if m is None:
                return None
            long_sides = _side_readings(poly, m["axis_edge"], m["centre"], face_lines,
                                        cap_lines, solids_seg, solids_other, ctx)
            end_sides = _side_readings(poly, m["short_edge"], m["centre"], face_lines,
                                       cap_lines, solids_seg, solids_other, ctx)
            b = [round(v, 1) for v in poly.bounds]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            cls, v, note = _gt_class(slug, p.page_number, b)
            spacing = m["short"] + 2.0 * STANDOFF
            n_glyph = sum(1 for g in glyph_mids if poly.contains(g))
            pens_l = {t[0] for s in long_sides for t in s["pens"]}
            rec = {
                "bbox": b, "area": round(poly.area),
                "short": round(m["short"], 2), "long": round(m["long"], 2),
                "spacing": round(spacing, 2),
                "spacing_mm": None if H.mm(slug, spacing, cx, cy) is None
                else round(H.mm(slug, spacing, cx, cy)),
                "text": rooms._contains_text(poly, text_spans),
                "glyph_strokes_inside": n_glyph,
                "sides": long_sides, "ends": end_sides,
                "covers": sorted(s["cover"] for s in long_sides),
                "backed_seg": sorted(s["backed_seg"] for s in long_sides),
                "backed_any": sorted(s["backed_any"] for s in long_sides),
                "near_faces": sum(1 for s in long_sides if s["near_face"]),
                "near_seg_gaps": [s["near_seg_gap"] for s in long_sides],
                "same_pen_both_sides": len(pens_l) == 1 and all(s["pens"] for s in long_sides),
                "gt": cls, "gt_iou": round(v, 3), "gt_note": note[:120],
            }
            return rec

        call_recs = []
        for comp, res in calls:
            rec = reading(comp)
            if rec is None:
                call_recs.append({"bbox": [round(v, 1) for v in comp.bounds],
                                  "degenerate": True, "res_now": res})
                continue
            rec["res_now"] = res
            call_recs.append(rec)

        room_recs = []
        for poly, info in captured.get("rooms", []):
            rec = reading(poly)
            if rec is None:
                continue
            boundary = poly.exterior
            runs = [rooms._entrance_run(boundary, g) for g in entrance]
            runs = [r for r in runs if r != -math.inf]
            rec.update(
                door_count=info["door_count"], window_count=info["window_count"],
                entrance_count=sum(1 for r in runs if r >= rg.ROOM_ENTRANCE_MIN_RUN_PX),
            )
            room_recs.append(rec)

        records.append({
            "slug": slug, "page": p.page_number, "factor": round(f, 4),
            "cap_px": round(rg.WALL_MAX_THICKNESS_PX, 2),
            "n_glyph_strokes": len(glyph_idx), "n_text_spans": len(text_spans),
            "calls": call_recs, "rooms": room_recs,
        })
        in56 = [c for c in call_recs if not c.get("degenerate") and c["spacing"] <= 56.0 * f]
        print(f"{slug} p{p.page_number} f={f:.3f} cap {rg.WALL_MAX_THICKNESS_PX:.1f}: "
              f"pocket calls {len(call_recs)} (<=56xf: {len(in56)}), rooms {len(room_recs)}, "
              f"glyph strokes {len(glyph_idx)}, text spans {len(text_spans)}", flush=True)
        def _line(tag, c):
            print(f"    {tag} {c['bbox']} sp {c['spacing']} ({c['spacing_mm']}mm) gt={c['gt']} "
                  f"text={c['text']} glyphs={c['glyph_strokes_inside']} covers {c['covers']} "
                  f"backed_any {c['backed_any']} spans {[s['span_any_med'] for s in c['sides']]} "
                  f"same_pen={c['same_pen_both_sides']} "
                  f"ends cov {[e['cover'] for e in c['ends']]} ends backed {[e['backed_any'] for e in c['ends']]} "
                  f"NEAR faces {c['near_faces']}/2 seg_gaps {c['near_seg_gaps']}"
                  + (f" now_dropped={c['res_now']}" if "res_now" in c else
                     f" entr {c['entrance_count']} doors {c['door_count']} win {c['window_count']}"))
            for s in c["sides"]:
                print(f"        side near {s['near_face_px']} far {s['far_face_px']} lone {s['lone_face_px']} px; "
                      f"near seg {s['near_seg']} gap {s['near_seg_gap']}; pens {s['pens'][:2]}")

        for c in sorted(in56, key=lambda c: c["spacing"]):
            _line("CALL", c)
        narrow = [r for r in room_recs if r["gt"] == "confirmed" and r["spacing"] <= 72.0 * f]
        for r in sorted(narrow, key=lambda r: r["spacing"]):
            _line("CONFIRMED-NARROW", r)
    return records


if __name__ == "__main__":
    slugs = sys.argv[1:] or [f"s{i:02d}" for i in range(1, 21)]
    all_recs = []
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    keep = [r for r in existing if r["slug"] not in slugs]
    for slug in slugs:
        try:
            all_recs.extend(census(slug))
        except SystemExit as e:
            print(f"{slug}: skipped ({e})")
    OUT.write_text(json.dumps(keep + all_recs, indent=1, default=str))
    print("wrote", OUT)
