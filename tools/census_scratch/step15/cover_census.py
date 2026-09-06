"""Step 15 — `_is_band_pocket`'s COVER READING measured on both populations,
all 20 sheets at their factors, on the pipeline's exact inputs.

The rule reads the cover of each LONG EDGE of the component's minimum
rotated rectangle against `face_lines` at the barrier standoff
(`_edge_face_cover`: the largest single parallel face at standoff
ROOM_LINE_BARRIER_PX ± ROOM_RECESS_BACK_TOL_PX). s17's four reveal strips
carry a 31.5px TAB where a perpendicular band's flat-capped solid ends —
the polygon's edge lies ON the face line there (standoff 0) — so the
rectangle is pinned 2px outside the strip's own long run and the edge's
cover reads 0. Four readings of every component, side by side:

  mrr        the rule as it stands (largest single face, standoff 2 ± 1.5)
  mrr_tol0   the same edges, standoff 0 (≤ 0.5px) tolerated as well
  runs       the polygon's OWN long runs: every boundary segment parallel to
             the rectangle's long axis, classed to a side by the sign of its
             offset from the rectangle's centre; per side the UNION of the
             projected extents of the faces lying beside each run at the
             standoff, over the rectangle's long length
  runs_caps  `runs` with the END CAPS of every paired wall segment admitted
             as lines beside a run (the tab lies along the perpendicular
             band's cap, 2px off the segment's end line exactly like a face)
  runs_max   `runs` with the largest single face per run instead of the
             union (the current helper's semantic, applied per run)

Populations, read off detect_rooms' own locals through the free-space tap
(`face_lines`, `door_barriers`, `wall_segments`) and the
`_drop_window_exterior_sides` tap (the rooms list with its counts):

  calls   every `_is_band_pocket` call (= every entrance-less, window-less
          component past the filters and the recess rule) — the rule's
          population; verdict under each reading at each candidate ceiling
  rooms   every room the stage emits (ENTERED_ALL): the true class the
          rule would see if its entrance did not spare it, with entrance /
          door / window counts as detect_rooms reads them

Usage: .venv/bin/python tools/census_scratch/step15/cover_census.py [slugs...]
Writes step15/cover_census.json (COVER_CENSUS_OUT to run two jobs).
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
from shapely.geometry import Polygon  # noqa: E402

from detection import rooms, walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("COVER_CENSUS_OUT",
                          Path(__file__).resolve().parent / "cover_census.json"))
COVER_MIN = rooms.ROOM_BAND_POCKET_FACE_COVER_MIN
STANDOFF = rooms.ROOM_LINE_BARRIER_PX
BACK_TOL = rooms.ROOM_RECESS_BACK_TOL_PX
ANGLE_TOL = walls.WALL_PARALLEL_ANGLE_TOL
CEILINGS = (36.0, 40.0, 41.0, 44.0, 48.0, 56.0)   # px at 1:50, scaled by f
READINGS = ("mrr", "mrr_tol0", "runs", "runs_caps", "runs_max")


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
        long_edges, short, long = (edges[0], edges[2]), lens[1], lens[0]
    else:
        long_edges, short, long = (edges[1], edges[3]), lens[0], lens[1]
    (ax, ay), (bx, by) = long_edges[0]
    ux, uy = (bx - ax) / long, (by - ay) / long
    cx, cy = rect.centroid.x, rect.centroid.y
    return {
        "long_edges": long_edges, "short": short, "long": long,
        "axis": _line_angle_deg(*long_edges[0]), "corners": c,
        "u": (ux, uy), "n": (-uy, ux), "centre": (cx, cy),
    }


def _accept_standoff(standoff, tol0):
    if abs(standoff - STANDOFF) <= BACK_TOL:
        return True
    return tol0 and standoff <= 0.5


def _edge_cover(edge, lines, tol0=False):
    """The reading the rule used before step 15 (`_edge_face_cover`, since
    replaced): the largest single parallel face at the standoff — read at
    the face's p1 against the edge's midpoint — along a rectangle edge;
    with `tol0`, standoff 0 tolerated as well."""
    (ax, ay), (bx, by) = edge
    length = math.hypot(bx - ax, by - ay)
    if length < 1e-6:
        return 0.0
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    angle = _line_angle_deg((ax, ay), (bx, by))
    best = 0.0
    for p1, p2 in lines:
        if _angle_diff_mod180(angle, _line_angle_deg(p1, p2)) > ANGLE_TOL:
            continue
        standoff = abs((p1[0] - mx) * nx + (p1[1] - my) * ny)
        if not _accept_standoff(standoff, tol0):
            continue
        t1 = (p1[0] - ax) * ux + (p1[1] - ay) * uy
        t2 = (p2[0] - ax) * ux + (p2[1] - ay) * uy
        overlap = min(max(t1, t2), length) - max(min(t1, t2), 0.0)
        best = max(best, overlap / length)
    return best


def _run_cover(run, lines, tol0=False, cap_lines=()):
    """Covered length of one boundary run by the lines lying beside it:
    faces at the barrier standoff, cap lines (wall solids' flat ends) at
    standoff 0 — each within BACK_TOL — as (union px, largest single px).
    The standoff is read at the midpoint of each line's overlap with the
    run (interpolated between the line's endpoint distances), so a line a
    few degrees off reads its true offset where it actually lies beside
    the run. The same reading as the shipped `_run_wall_cover`."""
    (ax, ay), (bx, by) = run
    length = math.hypot(bx - ax, by - ay)
    if length < 1e-6:
        return 0.0, 0.0
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    angle = _line_angle_deg((ax, ay), (bx, by))
    intervals = []
    best = 0.0
    for group, standoff in ((lines, STANDOFF), (cap_lines, 0.0)):
        for p1, p2 in group:
            if _angle_diff_mod180(angle, _line_angle_deg(p1, p2)) > ANGLE_TOL:
                continue
            t1 = (p1[0] - ax) * ux + (p1[1] - ay) * uy
            t2 = (p2[0] - ax) * ux + (p2[1] - ay) * uy
            lo, hi = max(min(t1, t2), 0.0), min(max(t1, t2), length)
            if hi - lo <= 1e-6:
                continue
            d1 = (p1[0] - ax) * nx + (p1[1] - ay) * ny
            d2 = (p2[0] - ax) * nx + (p2[1] - ay) * ny
            tm = (lo + hi) / 2.0
            if abs(t2 - t1) > 1e-9:
                d = d1 + (d2 - d1) * (tm - t1) / (t2 - t1)
            else:
                d = d1
            if standoff == 0.0:
                ok = abs(d) <= BACK_TOL
            else:
                ok = _accept_standoff(abs(d), tol0)
            if not ok:
                continue
            intervals.append((lo, hi))
            best = max(best, hi - lo)
    intervals.sort()
    covered = 0.0
    cur_lo, cur_hi = None, None
    for lo, hi in intervals:
        if cur_hi is None or lo > cur_hi:
            if cur_hi is not None:
                covered += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
        else:
            cur_hi = max(cur_hi, hi)
    if cur_hi is not None:
        covered += cur_hi - cur_lo
    return covered, best


def _side_runs(poly, m):
    """The polygon's boundary runs parallel to the long axis, per side."""
    ux, uy = m["u"]
    nx, ny = m["n"]
    cx, cy = m["centre"]
    sides = ([], [])
    coords = list(poly.exterior.coords)
    for a, b in zip(coords, coords[1:]):
        L = _line_length(a, b)
        if L < 1e-6:
            continue
        if _angle_diff_mod180(m["axis"], _line_angle_deg(a, b)) > ANGLE_TOL:
            continue
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        off = (mx - cx) * nx + (my - cy) * ny
        sides[0 if off < 0 else 1].append((a, b, L, off))
    return sides


def _runs_readings(poly, m, face_lines, cap_lines):
    sides = _side_runs(poly, m)
    long = m["long"]
    out = {"runs": [], "runs_caps": [], "runs_max": [], "side_detail": []}
    for runs in sides:
        cov_u = cov_uc = cov_max = 0.0
        total = 0.0
        detail = []
        for a, b, L, off in runs:
            u_px, max_px = _run_cover((a, b), face_lines)
            uc_px, _ = _run_cover((a, b), face_lines, cap_lines=cap_lines)
            cov_u += u_px
            cov_uc += uc_px
            cov_max += max_px
            total += L
            detail.append({"len": round(L, 1), "offset": round(off, 2),
                           "cov_faces": round(u_px, 1), "cov_with_caps": round(uc_px, 1),
                           "a": [round(v, 1) for v in a], "b": [round(v, 1) for v in b]})
        out["runs"].append(cov_u / long)
        out["runs_caps"].append(cov_uc / long)
        out["runs_max"].append(cov_max / long)
        out["side_detail"].append({"parallel_len": round(total, 1), "n_runs": len(runs),
                                   "runs": detail})
    return out


def _cap_lines(wall_segments):
    """The end lines of every paired segment's solid: the cap a strip's tab
    lies along, 2px off exactly like a face."""
    out = []
    for s in wall_segments:
        length = _line_length(s.p1, s.p2)
        if length < 1e-6:
            continue
        nx = -(s.p2[1] - s.p1[1]) / length
        ny = (s.p2[0] - s.p1[0]) / length
        half = s.thickness_px / 2.0
        for p in (s.p1, s.p2):
            out.append(((p[0] + nx * half, p[1] + ny * half),
                        (p[0] - nx * half, p[1] - ny * half)))
    return out


def _readings(poly, face_lines, cap_lines):
    m = _mrr(poly)
    if m is None:
        return None
    rec = {
        "short": round(m["short"], 2), "long": round(m["long"], 2),
        "spacing": round(m["short"] + 2.0 * STANDOFF, 2),
        "axis_deg": round(m["axis"], 1),
        "mrr": [[round(x, 1), round(y, 1)] for x, y in m["corners"]],
        "n_vertices": len(poly.exterior.coords) - 1,
    }
    covers = {
        "mrr": [_edge_cover(e, face_lines) for e in m["long_edges"]],
        "mrr_tol0": [_edge_cover(e, face_lines, tol0=True) for e in m["long_edges"]],
    }
    rr = _runs_readings(poly, m, face_lines, cap_lines)
    covers["runs"] = rr["runs"]
    covers["runs_caps"] = rr["runs_caps"]
    covers["runs_max"] = rr["runs_max"]
    rec["covers"] = {k: [round(v, 3) for v in sorted(vs)] for k, vs in covers.items()}
    rec["side_detail"] = rr["side_detail"]
    return rec


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


def _verdicts(rec, f, text):
    """drop verdict per reading per ceiling (the rule: spacing ≤ ceiling,
    no text, both covers ≥ COVER_MIN)."""
    out = {}
    sp = rec["spacing"]
    for r in READINGS:
        ok = (not text) and min(rec["covers"][r]) >= COVER_MIN
        out[r] = {str(int(c)): bool(ok and sp <= c * f) for c in CEILINGS}
    return out


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
            captured["face_lines"] = list(loc["face_lines"])
            captured["door_barriers"] = list(loc["door_barriers"])
            captured["wall_segments"] = list(loc["wall_segments"])
            return o_fsc(page, barriers)

        def drop(rooms_list, windows, **k):
            captured["rooms"] = list(rooms_list)
            return o_drop(rooms_list, windows, **k)

        def pocket(comp, face_lines, text_spans, *, cap_lines=(),
                   gates=rooms.ROOM_GATES_UNSCALED):
            # cap_lines arrived with the step-15 reading; passed through so
            # the tap keeps reproducing the stage on either tree.
            kw = {"cap_lines": cap_lines} if cap_lines else {}
            res = o_pocket(comp, face_lines, text_spans, gates=gates, **kw)
            calls.append((comp, bool(res)))
            return res

        rooms._free_space_components = fsc
        rooms._drop_window_exterior_sides = drop
        rooms._is_band_pocket = pocket
        try:
            ents, _ = H.run(p)
        finally:
            rooms._free_space_components = o_fsc
            rooms._drop_window_exterior_sides = o_drop
            rooms._is_band_pocket = o_pocket

        face_lines = captured.get("face_lines", [])
        cap_lines = _cap_lines(captured.get("wall_segments", []))
        entrance = [g for conf, g in captured.get("door_barriers", [])
                    if conf >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE]
        text_spans = p.page_data.text_spans

        def finish(poly, rec):
            b = [round(v, 1) for v in poly.bounds]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            cls, v, note = _gt_class(slug, p.page_number, b)
            text = rooms._contains_text(poly, text_spans)
            rec.update(
                bbox=b, area=round(poly.area), text=text,
                spacing_mm=None if H.mm(slug, rec["spacing"], cx, cy) is None
                else round(H.mm(slug, rec["spacing"], cx, cy)),
                gt=cls, gt_iou=round(v, 3), gt_note=note[:120],
                verdicts=_verdicts(rec, f, text),
            )
            return rec

        call_recs = []
        for comp, res in calls:
            rec = _readings(comp, face_lines, cap_lines)
            if rec is None:
                call_recs.append({"bbox": [round(v, 1) for v in comp.bounds],
                                  "degenerate": True, "res_now": res})
                continue
            rec["res_now"] = res
            call_recs.append(finish(comp, rec))

        room_recs = []
        for poly, info in captured.get("rooms", []):
            rec = _readings(poly, face_lines, cap_lines)
            if rec is None:
                continue
            boundary = poly.exterior
            runs = [rooms._entrance_run(boundary, g) for g in entrance]
            runs = [r for r in runs if r != -math.inf]
            rec.update(
                door_count=info["door_count"], window_count=info["window_count"],
                entrance_count=sum(1 for r in runs if r >= rg.ROOM_ENTRANCE_MIN_RUN_PX),
                max_entrance_run=None if not runs else round(max(runs), 1),
            )
            room_recs.append(finish(poly, rec))

        records.append({
            "slug": slug, "page": p.page_number, "factor": round(f, 4),
            "cap_px": round(rg.WALL_MAX_THICKNESS_PX, 2),
            "n_face_lines": len(face_lines), "n_cap_lines": len(cap_lines),
            "calls": call_recs, "rooms": room_recs,
        })
        n_in56 = [c for c in call_recs if not c.get("degenerate") and c["spacing"] <= 56.0 * f]
        print(f"{slug} p{p.page_number} f={f:.3f} cap {rg.WALL_MAX_THICKNESS_PX:.1f}: "
              f"pocket calls {len(call_recs)} (≤56×f: {len(n_in56)}), rooms {len(room_recs)}, "
              f"face_lines {len(face_lines)}, cap_lines {len(cap_lines)}", flush=True)
        for c in sorted(n_in56, key=lambda c: c["spacing"]):
            cv = c["covers"]
            print(f"    CALL {c['bbox']} sp {c['spacing']} ({c['spacing_mm']}mm) gt={c['gt']} text={c['text']} "
                  f"mrr {cv['mrr']} tol0 {cv['mrr_tol0']} runs {cv['runs']} caps {cv['runs_caps']} "
                  f"max {cv['runs_max']} now_dropped={c['res_now']}")
        conf_narrow = [r for r in room_recs if r["gt"] == "confirmed" and r["spacing"] <= 56.0 * f]
        for r in sorted(conf_narrow, key=lambda r: r["spacing"]):
            cv = r["covers"]
            print(f"    CONFIRMED-NARROW {r['bbox']} sp {r['spacing']} ({r['spacing_mm']}mm) "
                  f"entr {r['entrance_count']} doors {r['door_count']} win {r['window_count']} text={r['text']} "
                  f"mrr {cv['mrr']} runs {cv['runs']} caps {cv['runs_caps']}")
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
