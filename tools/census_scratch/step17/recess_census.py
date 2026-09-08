"""Step 17 — `_is_wall_recess`'s back edge on the tab: the EXTENT reading (as
implemented — min(ws) / max(ws) over every vertex across the band, the extreme
at the barrier standoff inside the band's outer line) against a reading on the
component's OWN boundary runs (the runs parallel to the band lying along its
outer line at the standoff — and, as `_run_wall_cover` admits for the covers,
on a wall solid's flat END at standoff 0 — unioned over the gap), on the
pipeline's exact inputs, all 20 sheets at their factors, classed against the
ground truth:

  calls   every `_is_wall_recess` call (= every entrance-less, window-less
          component past the filters) with the rule's own verdict
  rooms   every room the stage emits: the true class the rule would see if
          its entrance did not spare it

Per component, for every collinear-gap candidate (a, b) that passes the
intersect / opening / gap-cover / depth gates (the candidates the back-edge
test decides), beside the extent reading:

  face    per outer flank, the union over the gap of the runs parallel to the
          band lying ROOM_LINE_BARRIER_PX +- ROOM_RECESS_BACK_TOL_PX inside it
  caps    the same plus the runs lying ON the flank (standoff 0 +- tol) where a
          wall solid's flat end (`cap_lines`) lies on them — the tab
  own     the same two with the COMPONENT's along-extent inside the gap as the
          denominator instead of the gap's length

Then the rule AS IMPLEMENTED with `_is_wall_recess` replaced by each runs
reading at ROOM_RECESS_GAP_COVER_MIN: rooms gone / new / moved, scored.

Usage: .venv/bin/python tools/census_scratch/step17/recess_census.py [slugs...]
Writes step17/recess_census.json (RECESS_CENSUS_OUT to run several jobs).
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import LineString, Polygon, box  # noqa: E402

from detection import rooms, walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from detection.walls import _perpendicular_spacing  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("RECESS_CENSUS_OUT",
                          Path(__file__).resolve().parent / "recess_census.json"))
STANDOFF = rooms.ROOM_LINE_BARRIER_PX
DILATE = rooms.ROOM_WALL_DILATE_PX
BACK_TOL = rooms.ROOM_RECESS_BACK_TOL_PX
ANGLE_TOL = walls.WALL_PARALLEL_ANGLE_TOL
GAP_MIN = rooms.ROOM_RECESS_GAP_COVER_MIN
DEPTH_MAX = rooms.ROOM_RECESS_DEPTH_RATIO_MAX
VARIANTS = ("face_gap", "caps_gap", "face_own", "caps_own")


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


# ---------------------------------------------------------------------------
# the rule's candidates, exactly as _is_wall_recess walks them
# ---------------------------------------------------------------------------
def gap_candidates(comp, wall_segments, opening_boxes):
    """Every (a, b) collinear pair whose gap rect passes the intersect /
    opening / gap-cover / depth gates — what the back-edge test decides."""
    coords = list(comp.exterior.coords)
    out = []
    for i, a in enumerate(wall_segments):
        len_a = _line_length(a.p1, a.p2)
        if len_a < 1e-6:
            continue
        ux = (a.p2[0] - a.p1[0]) / len_a
        uy = (a.p2[1] - a.p1[1]) / len_a
        nx, ny = -uy, ux
        for b in wall_segments[i + 1:]:
            if _line_length(b.p1, b.p2) < 1e-6:
                continue
            if _angle_diff_mod180(
                _line_angle_deg(a.p1, a.p2), _line_angle_deg(b.p1, b.p2)
            ) > ANGLE_TOL:
                continue
            th = max(a.thickness_px, b.thickness_px)
            if _perpendicular_spacing(a.p1, a.p2, b.p1, b.p2) > th / 2.0:
                continue
            tb = sorted(
                (p[0] - a.p1[0]) * ux + (p[1] - a.p1[1]) * uy for p in (b.p1, b.p2)
            )
            if tb[0] > len_a:
                lo, hi = len_a, tb[0]
            elif tb[1] < 0.0:
                lo, hi = tb[1], 0.0
            else:
                continue
            if hi - lo < th:
                continue
            rect = Polygon([
                (a.p1[0] + ux * t + nx * w, a.p1[1] + uy * t + ny * w)
                for t, w in ((lo, -th / 2), (hi, -th / 2), (hi, th / 2), (lo, th / 2))
            ])
            if not rect.intersects(comp):
                continue
            if any(rect.intersects(o) for o in opening_boxes):
                continue
            inter = rect.intersection(comp)
            gap_cover = inter.area / rect.area if rect.area > 0 else 0.0
            if gap_cover < GAP_MIN:
                continue
            ws = [(p[0] - a.p1[0]) * nx + (p[1] - a.p1[1]) * ny for p in coords]
            depth = max(ws) - min(ws)
            if depth > DEPTH_MAX * th:
                continue
            # the component's own along-extent inside the gap
            ts_in = [(p[0] - a.p1[0]) * ux + (p[1] - a.p1[1]) * uy
                     for g in getattr(inter, "geoms", [inter]) if not g.is_empty
                     for p in (g.exterior.coords if g.geom_type == "Polygon" else g.coords)]
            own_lo, own_hi = (max(min(ts_in), lo), min(max(ts_in), hi)) if ts_in else (lo, lo)
            out.append({
                "a": a, "b": b, "ux": ux, "uy": uy, "nx": nx, "ny": ny, "th": th,
                "lo": lo, "hi": hi, "own_lo": own_lo, "own_hi": own_hi,
                "gap_cover": gap_cover, "depth": depth, "ws": ws,
            })
    return out


def back_extent(c):
    back = min(-c["th"] / 2.0 - min(c["ws"]), max(c["ws"]) - c["th"] / 2.0)
    return back, abs(back + DILATE) <= BACK_TOL


def back_runs(c, comp, cap_lines):
    """Per outer flank (s = -1 / +1 across the band): the union over the gap
    of the component's boundary runs parallel to the band that lie at the
    standoff inside the flank (face) and, in addition, ON the flank where a
    cap line lies on them (caps); over the gap's length and over the
    component's own along-extent inside the gap."""
    a = c["a"]
    ux, uy, nx, ny, th = c["ux"], c["uy"], c["nx"], c["ny"], c["th"]
    lo, hi = c["lo"], c["hi"]
    own_lo, own_hi = c["own_lo"], c["own_hi"]
    axis_angle = _line_angle_deg(a.p1, a.p2)
    coords = list(comp.exterior.coords)
    sides = {}
    for s in (-1.0, 1.0):
        face_ivs, cap_ivs = [], []
        runs_detail = []
        for p, q in zip(coords, coords[1:]):
            rl = _line_length(p, q)
            if rl < 1e-6 or _angle_diff_mod180(axis_angle, _line_angle_deg(p, q)) > ANGLE_TOL:
                continue
            mx, my = (p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0
            w = (mx - a.p1[0]) * nx + (my - a.p1[1]) * ny
            tp = (p[0] - a.p1[0]) * ux + (p[1] - a.p1[1]) * uy
            tq = (q[0] - a.p1[0]) * ux + (q[1] - a.p1[1]) * uy
            t0, t1 = max(min(tp, tq), lo), min(max(tp, tq), hi)
            if t1 - t0 <= 1e-6:
                continue
            on_face = abs(w - s * (th / 2.0 - STANDOFF)) <= BACK_TOL
            on_flank = abs(w - s * th / 2.0) <= BACK_TOL
            cap_here = []
            if on_flank:
                rux, ruy = (q[0] - p[0]) / rl, (q[1] - p[1]) / rl
                for clo, chi in rooms._run_wall_cover((p, q), [], cap_lines):
                    ta = (p[0] + rux * clo - a.p1[0]) * ux + (p[1] + ruy * clo - a.p1[1]) * uy
                    tb = (p[0] + rux * chi - a.p1[0]) * ux + (p[1] + ruy * chi - a.p1[1]) * uy
                    c0, c1 = max(min(ta, tb), lo), min(max(ta, tb), hi)
                    if c1 - c0 > 1e-6:
                        cap_here.append((c0, c1))
            if on_face:
                face_ivs.append((t0, t1))
            cap_ivs.extend(cap_here)
            if on_face or cap_here:
                runs_detail.append({
                    "run": [[round(v, 2) for v in p], [round(v, 2) for v in q]],
                    "w": round(w, 2), "t": [round(t0, 1), round(t1, 1)],
                    "on_face": on_face, "on_cap": bool(cap_here),
                })
        gap_len = hi - lo
        own_len = own_hi - own_lo
        face_u = _union_len(face_ivs)
        caps_u = _union_len(face_ivs + cap_ivs)
        own_face = _union_len([(max(l, own_lo), min(h, own_hi)) for l, h in face_ivs if min(h, own_hi) > max(l, own_lo)])
        own_caps = _union_len([(max(l, own_lo), min(h, own_hi)) for l, h in face_ivs + cap_ivs if min(h, own_hi) > max(l, own_lo)])
        sides[int(s)] = {
            "face_gap": face_u / gap_len if gap_len > 0 else 0.0,
            "caps_gap": caps_u / gap_len if gap_len > 0 else 0.0,
            "face_own": own_face / own_len if own_len > 1e-6 else 0.0,
            "caps_own": own_caps / own_len if own_len > 1e-6 else 0.0,
            "runs": runs_detail,
        }
    best = {v: max(sides[-1][v], sides[1][v]) for v in VARIANTS}
    return best, sides


def readings(comp, wall_segments, opening_boxes, text_spans, cap_lines):
    """The rule's verdict under every reading, with each candidate's numbers."""
    text = rooms._contains_text(comp, text_spans)
    cands = []
    verdict = {"extent": False, **{v: False for v in VARIANTS}}
    for c in gap_candidates(comp, wall_segments, opening_boxes):
        back, ok_ext = back_extent(c)
        best, sides = back_runs(c, comp, cap_lines)
        rec = {
            "a": [[round(v, 2) for v in c["a"].p1], [round(v, 2) for v in c["a"].p2], round(c["a"].thickness_px, 2)],
            "b": [[round(v, 2) for v in c["b"].p1], [round(v, 2) for v in c["b"].p2], round(c["b"].thickness_px, 2)],
            "th": round(c["th"], 2), "gap": [round(c["lo"], 1), round(c["hi"], 1)],
            "own": [round(c["own_lo"], 1), round(c["own_hi"], 1)],
            "gap_cover": round(c["gap_cover"], 3), "depth_bands": round(c["depth"] / c["th"], 2),
            "back": round(back, 2), "extent_ok": ok_ext,
            **{v: round(best[v], 3) for v in VARIANTS},
            "sides": {str(k): {vv: round(s[vv], 3) for vv in VARIANTS} | {"runs": s["runs"]}
                      for k, s in sides.items()},
        }
        cands.append(rec)
        if not text:
            verdict["extent"] = verdict["extent"] or ok_ext
            for v in VARIANTS:
                verdict[v] = verdict[v] or best[v] >= GAP_MIN
    return {"text": text, "candidates": cands, "verdict": verdict}


# ---------------------------------------------------------------------------
# the rule with the runs reading, for the as-implemented chain
# ---------------------------------------------------------------------------
# Which reading the shipped rule implements — the verdict the census checks
# its own reading against on every call: "extent" on the step-16 tree,
# "caps_own" on the step-17 tree (RECESS_CENSUS_SHIPPED).
SHIPPED = os.environ.get("RECESS_CENSUS_SHIPPED", "extent")


def make_runs_rule(variant):
    def rule(comp, wall_segments, opening_boxes, text_spans, *, cap_lines=None):
        if rooms._contains_text(comp, text_spans):
            return False
        if cap_lines is None:
            cap_lines = sys._getframe(1).f_locals["cap_lines"]
        for c in gap_candidates(comp, wall_segments, opening_boxes):
            best, _ = back_runs(c, comp, cap_lines)
            if best[variant] >= GAP_MIN:
                return True
        return False
    return rule


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------
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
        captured = {}
        calls = []
        o_fsc, o_drop, o_recess = (rooms._free_space_components,
                                   rooms._drop_window_exterior_sides,
                                   rooms._is_wall_recess)

        def fsc(page, barriers):
            loc = sys._getframe(1).f_locals
            for k in ("face_lines", "cap_lines", "wall_segments", "door_barriers", "solid_parts"):
                captured[k] = list(loc[k])
            captured["solids"] = loc["solids"]
            captured["network"] = loc["network"]
            captured["text_spans"] = list(loc["text_spans"])
            captured["opening_boxes"] = ([box(*c.bbox) for c in loc["doors"]]
                                         + [box(*c.bbox) for c in loc["windows"]])
            return o_fsc(page, barriers)

        def drop(rooms_list, windows, **k):
            captured["rooms"] = list(rooms_list)
            return o_drop(rooms_list, windows, **k)

        def recess(comp, wall_segments, opening_boxes, text_spans, **kw):
            res = o_recess(comp, wall_segments, opening_boxes, text_spans, **kw)
            calls.append((comp, bool(res), wall_segments, opening_boxes, text_spans))
            return res

        rooms._free_space_components = fsc
        rooms._drop_window_exterior_sides = drop
        rooms._is_wall_recess = recess
        try:
            base_ents, _ = H.run(p)
        finally:
            rooms._free_space_components = o_fsc
            rooms._drop_window_exterior_sides = o_drop
            rooms._is_wall_recess = o_recess

        cap_lines = captured.get("cap_lines", [])
        wall_segments = captured.get("wall_segments", [])
        opening_boxes = captured.get("opening_boxes", [])
        text_spans = captured.get("text_spans", [])

        def describe(poly, extra):
            b = [round(v, 1) for v in poly.bounds]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            cls, v, note = _gt_class(slug, p.page_number, b)
            return {"bbox": b, "area": round(poly.area), "gt": cls, "gt_iou": round(v, 3),
                    "gt_note": note[:120], "mm_per_px": H.mm(slug, 1.0, cx, cy), **extra}

        call_recs = []
        for comp, res, ws_, ob_, ts_ in calls:
            # the call's own inputs are the stage's (assert, then read)
            assert len(ws_) == len(wall_segments) and len(ob_) == len(opening_boxes)
            r = readings(comp, ws_, ob_, ts_, cap_lines)
            rec = describe(comp, r)
            rec["res_now"] = res
            assert rec["verdict"][SHIPPED] == res, (slug, rec["bbox"], rec["verdict"], res)
            call_recs.append(rec)

        room_recs = []
        for poly, info in captured.get("rooms", []):
            r = readings(poly, wall_segments, opening_boxes, text_spans, cap_lines)
            rec = describe(poly, r)
            rec.update(door_count=info["door_count"], window_count=info["window_count"])
            room_recs.append(rec)

        # The rule AS IMPLEMENTED with each runs reading in place of the extent
        base_rooms = [e for e in base_ents if e["entity_type"] == "room"]
        base_score = H.score(slug, p.page_number, base_ents)
        variants = {}
        for v in VARIANTS:
            rooms._is_wall_recess = make_runs_rule(v)
            try:
                ents, _ = H.run(p)
            finally:
                rooms._is_wall_recess = o_recess
            rms = [e for e in ents if e["entity_type"] == "room"]
            d = H.diff_vs_baseline(base_rooms, rms)
            moved = []
            for e in rms:
                best = max(base_rooms, key=lambda b: iou(tuple(b["bbox"]), tuple(e["bbox"])), default=None)
                if best is None or iou(tuple(best["bbox"]), tuple(e["bbox"])) < 0.5:
                    continue
                if best["evidence"]["polygon"] != e["evidence"]["polygon"]:
                    moved.append({"bbox": [round(x, 1) for x in e["bbox"]],
                                  "iou": round(iou(tuple(best["bbox"]), tuple(e["bbox"])), 4),
                                  "area_before": best["evidence"]["area_px2"],
                                  "area_after": e["evidence"]["area_px2"]})
            sc = H.score(slug, p.page_number, ents)
            variants[v] = {
                "gone": [{"bbox": list(b), "gt": _gt_class(slug, p.page_number, b)[0]} for _, b in d["gone"]],
                "new": [{"bbox": list(b), "gt": _gt_class(slug, p.page_number, b)[0]} for _, b in d["new"]],
                "moved": moved,
                "score": {"lost": len(sc["lost"]), "returned_fps": len(sc["returned_fps"]),
                          "unreviewed": len(sc["unreviewed"])},
            }

        records.append({
            "slug": slug, "page": p.page_number, "factor": round(f, 4),
            "n_wall_segments": len(wall_segments), "n_cap_lines": len(cap_lines),
            "calls": call_recs, "rooms": room_recs,
            "base_score": {"lost": len(base_score["lost"]), "returned_fps": len(base_score["returned_fps"]),
                           "unreviewed": len(base_score["unreviewed"])},
            "variants": variants,
        })

        # ---- log
        print(f"{slug} p{p.page_number} f={f:.3f}: recess calls {len(call_recs)} "
              f"(dropped now {sum(1 for c in call_recs if c['res_now'])}), rooms {len(room_recs)}, "
              f"base score lost {len(base_score['lost'])} retFP {len(base_score['returned_fps'])} "
              f"unrev {len(base_score['unreviewed'])}", flush=True)

        def _line(tag, c):
            v = c["verdict"]
            print(f"    {tag} {c['bbox']} area {c['area']} gt={c['gt']} text={c['text']} "
                  f"cands {len(c['candidates'])} | extent {v['extent']} "
                  + " ".join(f"{k} {v[k]}" for k in VARIANTS)
                  + (f" now_dropped={c['res_now']}" if "res_now" in c else
                     f" doors {c['door_count']} win {c['window_count']}"))
            for cd in c["candidates"]:
                print(f"        cand a {cd['a']} b {cd['b']} th {cd['th']} gap {cd['gap']} own {cd['own']} "
                      f"gap_cover {cd['gap_cover']} depth {cd['depth_bands']}x back {cd['back']} "
                      f"ext_ok {cd['extent_ok']} | " + " ".join(f"{k} {cd[k]}" for k in VARIANTS))
                for sk, sd in cd["sides"].items():
                    for rr in sd["runs"]:
                        print(f"            side {sk} run {rr['run']} w {rr['w']} t {rr['t']} "
                              f"face={rr['on_face']} cap={rr['on_cap']}")

        for c in call_recs:
            if c["candidates"]:
                _line("CALL", c)
        for c in room_recs:
            if c["candidates"]:
                _line("ROOM", c)
        for v in VARIANTS:
            vr = variants[v]
            if vr["gone"] or vr["new"] or vr["moved"]:
                print(f"    AS-IMPLEMENTED {v}: gone {vr['gone']} new {vr['new']} moved {vr['moved']} "
                      f"score {vr['score']}")
            else:
                print(f"    AS-IMPLEMENTED {v}: identical (score {vr['score']})")
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
        # write after every slug: a killed job keeps what it measured
        OUT.write_text(json.dumps(keep + all_recs, indent=1, default=str))
    print("wrote", OUT)
