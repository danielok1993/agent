"""Record, per sheet, the populations each scaled gate discriminates, with
world-mm conversions at the sheet's TRUE scale. Output: pop/<slug>.json"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import harness as H
from detection.windows import detect_windows
from detection.postprocess import _wall_runs_through, CrossGates
from detection.geometry import _line_length
from shapely.geometry import box, LineString

OUT = Path(__file__).resolve().parent / "pop"
OUT.mkdir(exist_ok=True)


def _clean(v):
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    if hasattr(v, "bounds"):
        return None
    return str(v)


def verdicts(slug, page_number, ents):
    """Annotate each entity with confirmed / fp / unreviewed / deferred."""
    from regression.matching import match_entities
    truth = H.load_truth(slug).page(page_number)
    out = ["unreviewed"] * len(ents)
    idx = {id(e): i for i, e in enumerate(ents)}
    rem = ents
    for name, items in (("confirmed", truth.confirmed), ("fp", truth.false_positives), ("deferred", truth.deferred)):
        m = match_entities(items, rem)
        for _t, e in m.matched:
            out[idx[id(e)]] = name
        rem = m.unmatched_actual
    return out


def main(slug):
    pages = H.load(slug)
    res = {"slug": slug, "pages": []}
    for p in pages:
        taps = H.Taps()
        ents, extras = H.run(p, taps=taps, keep_network=True)
        net = extras["network"]
        pd = p.page_data
        vd = verdicts(slug, p.page_number, ents)
        for e, v in zip(ents, vd):
            e["verdict"] = v
        sc = H.score(slug, p.page_number, ents)
        pg = {"page": p.page_number, "factor": p.scale_factor, "score": sc,
              "width": pd.width_px, "height": pd.height_px}

        def mmv(px, x, y):
            return H.mm(slug, px, x, y)

        # --- entities ---------------------------------------------------
        rooms_out = []
        doors_out = []
        windows_out = []
        for e in ents:
            x0, y0, x1, y1 = e["bbox"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            d = H.denom_at(slug, cx, cy)
            if e["entity_type"] == "room":
                poly = e["evidence"]["polygon"]
                from shapely.geometry import Polygon
                P = Polygon(poly)
                mrr = P.minimum_rotated_rectangle
                xs = list(mrr.exterior.coords)
                s1 = math.dist(xs[0], xs[1]); s2 = math.dist(xs[1], xs[2])
                rooms_out.append({
                    "bbox": e["bbox"], "verdict": e["verdict"], "conf": e["confidence"],
                    "area_px2": P.area, "area_m2": None if d is None else P.area * (H.MM_PER_PX_AT_1 * d) ** 2 / 1e6,
                    "short_px": min(s1, s2), "short_mm": mmv(min(s1, s2), cx, cy),
                    "long_px": max(s1, s2),
                    "doors": e["evidence"].get("door_openings"),
                    "windows": e["evidence"].get("window_openings"),
                    "denom": d,
                })
            elif e["entity_type"] == "door":
                ev = e["evidence"]
                ext = max(x1 - x0, y1 - y0)
                # needed CROSS reach
                need = None
                need_stroked = None
                if net is not None and not net.is_empty():
                    lo, hi = 0.0, 60.0
                    if net.near_bbox(e["bbox"], hi):
                        for _ in range(14):
                            mid = (lo + hi) / 2
                            if net.near_bbox(e["bbox"], mid):
                                hi = mid
                            else:
                                lo = mid
                        need = hi
                    lo, hi = 0.0, 60.0
                    if net.near_bbox(e["bbox"], hi, stroked_only=True):
                        for _ in range(14):
                            mid = (lo + hi) / 2
                            if net.near_bbox(e["bbox"], mid, stroked_only=True):
                                hi = mid
                            else:
                                lo = mid
                        need_stroked = hi
                    # opening endpoint distances
                    op = ev.get("opening_line")
                    op_d = None
                    if op and len(op) == 2:
                        op_d = []
                        for pt in op:
                            near = net.nearest_segment((pt[0], pt[1]))
                            op_d.append(None if near is None else near[1])
                else:
                    op_d = None
                doors_out.append({
                    "bbox": e["bbox"], "verdict": e["verdict"], "conf": e["confidence"],
                    "extent_px": ext, "extent_mm": mmv(ext, cx, cy),
                    "method": ev.get("method"), "assembly": ev.get("assembly_type"),
                    "swing_layout": ev.get("swing_layout"), "fold_style": ev.get("fold_style"),
                    "radius_px": ev.get("radius_px") or ev.get("arc_radius_px") or ev.get("radius"),
                    "opening_width_px": ev.get("opening_width_px") or ev.get("opening_span_px"),
                    "cross_need_px": need, "cross_need_stroked_px": need_stroked,
                    "opening_endpoint_dist": op_d,
                    "wall_context": ev.get("wall_context"),
                    "ev_keys": sorted(k for k in ev.keys()),
                    "ev_small": {k: _clean(v) for k, v in ev.items()
                                 if isinstance(v, (int, float, str, bool)) or v is None},
                    "denom": d,
                })
            elif e["entity_type"] == "window":
                ev = e["evidence"]
                w = max(x1 - x0, y1 - y0); t = min(x1 - x0, y1 - y0)
                rt = None
                if net is not None and not net.is_empty():
                    rt = _wall_runs_through(net, tuple(e["bbox"]), gates=CrossGates.at(p.scale_factor))
                windows_out.append({
                    "bbox": e["bbox"], "verdict": e["verdict"], "conf": e["confidence"],
                    "width_px": ev.get("opening_width_px") or w, "width_mm": mmv(ev.get("opening_width_px") or w, cx, cy),
                    "bbox_long_px": w, "bbox_short_px": t,
                    "runs_through": rt, "wall_context": ev.get("wall_context"),
                    "ev_small": {k: _clean(v) for k, v in ev.items()
                                 if isinstance(v, (int, float, str, bool)) or v is None},
                    "denom": d,
                })
        pg["rooms"] = rooms_out
        pg["doors"] = doors_out
        pg["windows"] = windows_out

        # --- door/window conflict: windows suppressed by doors ------------
        raw_windows = detect_windows(pd.paths, scale_factor=p.scale_factor)
        kept_boxes = {tuple(w.bbox) for w in extras["windows_all"]}
        confident_doors = [dd for dd in extras["doors_all"] if dd.confidence >= 0.40]
        fallback_doors = [dd for dd in extras["doors_all"] if dd.confidence < 0.40]
        supp = []
        for w in raw_windows:
            if tuple(w.bbox) in kept_boxes:
                continue
            wb = box(*w.bbox)
            dmin = min((wb.distance(box(*dd.bbox)) for dd in confident_doors), default=None)
            fmin = min((wb.distance(box(*dd.bbox)) for dd in fallback_doors), default=None)
            supp.append({"bbox": list(w.bbox), "conf": w.confidence, "dist_conf_door": dmin, "dist_fallback_door": fmin})
        pg["suppressed_windows"] = supp
        # distance of every REAL (confirmed) window to nearest confident door bbox
        for w in windows_out:
            wb = box(*w["bbox"])
            w["dist_conf_door"] = min((wb.distance(box(*dd.bbox)) for dd in confident_doors), default=None)
            w["dist_fallback_door"] = min((wb.distance(box(*dd.bbox)) for dd in fallback_doors), default=None)

        # --- walls: pairs / faces / material -----------------------------
        paired = net.paired_face_indices() if net is not None else set()
        stroke_ref = net.wall_stroke_reference() if net is not None else 0.0
        pg["stroke_ref"] = stroke_ref
        pg["pairs"] = [dict(r, th_mm=mmv(r["th"], *r["mid"]), len_mm=mmv(r["len"], *r["mid"]),
                            denom=H.denom_at(slug, *r["mid"]))
                       for r in taps.pairs]
        pg["wide_pairs"] = [dict(r, th_mm=mmv(r["th"], *r["mid"]), denom=H.denom_at(slug, *r["mid"]))
                            for r in taps.wide_pairs]
        pg["material"] = [dict(r, len_mm=mmv(r["len"], *r["mid"]), th_mm=mmv(r["th"], *r["mid"]),
                               per_m=(r["n"] / (mmv(r["len"], *r["mid"]) / 1000.0)) if mmv(r["len"], *r["mid"]) else None,
                               denom=H.denom_at(slug, *r["mid"]))
                          for r in taps.material]
        faces = []
        for r in taps.faces:
            faces.append(dict(r, len_mm=mmv(r["len"], *r["mid"]),
                              paired=bool(set(r["idx"]) & paired),
                              denom=H.denom_at(slug, *r["mid"])))
        pg["faces"] = faces
        pg["weak_faces"] = taps.weak_faces
        # the sub-floor stroke population: solid `l` strokes penned like walls
        gate_ref = 0.66 * stroke_ref if stroke_ref else 0.5
        wg = H.walls.WallGates.at(p.scale_factor)
        sub = []
        for pr in pd.paths:
            if pr.item_type != "l" or len(pr.points) < 2 or pr.fill is not None:
                continue
            if pr.stroke_width < gate_ref or H.walls._is_dashed(pr.dashes):
                continue
            L = _line_length(pr.points[0], pr.points[-1])
            if 2.0 <= L < 40.0:
                a, b = pr.points[0], pr.points[-1]
                ang = H._line_angle_deg(a, b)
                diag = H.walls._is_diagonal_hatch_angle(ang)
                sub.append({"len": L, "sw": pr.stroke_width, "diag": diag,
                            "mid": ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)})
        pg["short_strokes"] = sub
        pg["face_min_len_gate"] = wg.WALL_FACE_MIN_LEN_PX

        # hatch stroke lengths inside kept pairs: uncapped marks whose midpoint
        # lies in a final pair's band and is diagonal to it
        hatch = []
        marks_u = getattr(taps, "marks_uncapped", [])
        for r in taps.pairs:
            pass
        # need endpoints: recompute from network segments instead (thickness known)
        segs = net.segments if net is not None else []
        for s in segs:
            L = _line_length(s.p1, s.p2)
            if L < 1e-6:
                continue
            ux, uy = (s.p2[0] - s.p1[0]) / L, (s.p2[1] - s.p1[1]) / L
            axis = H._line_angle_deg(s.p1, s.p2)
            half = s.thickness_px / 2.0
            for (mx, my), angle, a, b, pen in marks_u:
                t = (mx - s.p1[0]) * ux + (my - s.p1[1]) * uy
                if not (0 <= t <= L):
                    continue
                if abs((mx - s.p1[0]) * -uy + (my - s.p1[1]) * ux) > half:
                    continue
                dang = H._angle_diff_mod180(angle, axis)
                if 20.0 <= dang <= 70.0:
                    ml = _line_length(a, b)
                    hatch.append({"len": ml, "len_mm": mmv(ml, mx, my), "th": s.thickness_px,
                                  "seg_source": s.source, "denom": H.denom_at(slug, mx, my)})
        pg["hatch_in_bands"] = hatch

        # --- rooms: plugs, components, bridges ----------------------------
        door_by_bbox = {tuple(round(v, 3) for v in dd["bbox"]): dd for dd in doors_out}
        plugs = []
        for r in taps.plugs:
            key = tuple(round(v, 3) for v in r["bbox"])
            dd = door_by_bbox.get(key)
            cx = (r["bbox"][0] + r["bbox"][2]) / 2; cy = (r["bbox"][1] + r["bbox"][3]) / 2
            plugs.append(dict(r, verdict=dd["verdict"] if dd else "rejected/other",
                              conf=dd["conf"] if dd else None,
                              assembly=dd["assembly"] if dd else None,
                              jamb_gap_a_mm=mmv(r["jamb_gap_a"], cx, cy) if r["jamb_gap_a"] is not None else None,
                              jamb_gap_b_mm=mmv(r["jamb_gap_b"], cx, cy) if r["jamb_gap_b"] is not None else None,
                              hug_a_mm=mmv(r["hug_a"], cx, cy), hug_b_mm=mmv(r["hug_b"], cx, cy),
                              denom=H.denom_at(slug, cx, cy)))
        pg["plugs"] = plugs
        # components: fate + opening contacts
        conf_doors = [box(*dd.bbox) for dd in extras["all_geo"] if dd.entity_type == "door" and dd.confidence >= 0.55]
        any_doors = [box(*dd.bbox) for dd in extras["all_geo"] if dd.entity_type == "door" and dd.confidence >= 0.40]
        win_boxes = [box(*ww.bbox) for ww in extras["all_geo"] if ww.entity_type == "window"]
        room_polys = []
        from shapely.geometry import Polygon
        for e in ents:
            if e["entity_type"] == "room":
                room_polys.append((Polygon(e["evidence"]["polygon"]), e["verdict"]))
        comps = []
        rg = H.rooms.RoomGates.at(p.scale_factor)
        for c in taps.components:
            P = c["poly"]
            cx, cy = P.centroid.x, P.centroid.y
            fate = "dropped"
            for rp, v in room_polys:
                inter = rp.intersection(P).area
                if inter > 0.5 * min(rp.area, P.area):
                    fate = "room:" + v
                    break
            d = H.denom_at(slug, cx, cy)
            near = lambda geoms, tol: any(g.distance(P) <= tol for g in geoms)
            comps.append({
                "area": c["area"], "area_m2": None if d is None else c["area"] * (H.MM_PER_PX_AT_1 * d) ** 2 / 1e6,
                "short": c["short"], "short_mm": mmv(c["short"], cx, cy), "long": c["long"],
                "bounds": list(c["bounds"]), "fate": fate,
                "touch_conf_door": near(conf_doors, 4.0 + rg.ROOM_OPENING_SEAL_PX),
                "touch_any_door": near(any_doors, 4.0 + rg.ROOM_OPENING_SEAL_PX),
                "touch_window": near(win_boxes, 4.0 + 2.0),
                "denom": d,
            })
        pg["components"] = comps
        pg["bridges"] = taps.bridges
        pg["n_bridges"] = getattr(taps, "n_bridges", None)
        pg["fill_classes"] = taps.fill_classes
        res["pages"].append(pg)
    (OUT / f"{slug}.json").write_text(json.dumps(_clean(res)))
    print("wrote", slug, {k: len(v) if isinstance(v, list) else v for k, v in res["pages"][0].items() if k in ("rooms", "doors", "windows", "pairs", "wide_pairs", "material", "faces", "plugs", "components", "hatch_in_bands")})


if __name__ == "__main__":
    for s in sys.argv[1:]:
        try:
            main(s)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            print("ERR", s, ex)
