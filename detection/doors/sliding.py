from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from models import BBox, Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.geometry import (
    _angle_diff_mod180, _bboxes_overlap, _distance, _is_line_path, _line_angle_deg,
)
from detection.labels import _find_nearby_label
from detection.layers import _layer_hint_from_layer
from detection.walls import _is_background_fill
from detection.doors.models import _DoorSwing
from detection.doors.constants import (
    DOOR_LABEL_PATTERN, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LAYER_KEYWORDS,
    DOOR_LEAF_ASPECT_MIN, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX,
    DOOR_SLIDE_ASSEMBLY_BASE, DOOR_SLIDE_AXIS_TOL_DEG,
    DOOR_SLIDE_FLANK_LINE_MIN_LEN_FRAC, DOOR_SLIDE_FLANK_MAX_FRAC,
    DOOR_SLIDE_FLANK_MIN_FRAC, DOOR_SLIDE_FLANK_SIDE_MIN_FRAC,
    DOOR_SLIDE_LATERAL_FACTOR, DOOR_SLIDE_LENGTH_RATIO_TOL,
    DOOR_SLIDE_OVERLAP_MAX_FRAC, DOOR_SLIDE_OVERLAP_MIN_FRAC,
    DOOR_SLIDE_PANEL_MERGE_TOL_PX,
    DOOR_SLIDE_PARK_FACE_COVER_MIN,
    DOOR_SLIDE_PARK_SPAN_RATIO_TOL, DOOR_SLIDE_PROTRUSION_MAX_FRAC,
    DOOR_SLIDE_PROTRUSION_MIN_FRAC, DOOR_SLIDE_RECT_PARALLEL_TOL_DEG,
    DOOR_SLIDE_RECT_PERP_TOL_DEG, DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX,
    DOOR_SLIDE_ZONE_MAX_CROSSERS, DOOR_SLIDE_ZONE_WIDTH_FACTOR,
    DoorGates,
)


@dataclass
class _SlidePanel:
    """An oriented thin rectangle that could be a sliding-door leaf."""
    center: tuple[float, float]
    length: float
    thickness: float
    axis_deg: float            # long-axis direction, mod 180
    corners: list[tuple[float, float]]
    bbox: BBox                 # axis-aligned envelope of the corners
    path_indices: list[int]
    sources: list[str]         # e.g. ["white_ring", "qu"] after representation merge
    white: bool                # any representation is a background-fill (white) rect
    layer: str | None
    layer_hint: bool
    consumed: bool = field(default=False)


def _fit_oriented_rect(points: list[tuple[float, float]]) -> dict | None:
    """Fit an oriented rectangle to a bag of corner points, any rotation.

    Orders unique points by angle around the centroid, drops near-collinear
    vertices (split sides collapse onto their corner-to-corner edge), and
    accepts exactly-4-corner convex outlines whose opposite sides are parallel
    and adjacent sides perpendicular within tolerance.
    """
    uniq: list[tuple[float, float]] = []
    for p in points:
        if all(_distance(p, q) > 1.0 for q in uniq):
            uniq.append(p)
    if len(uniq) < 4:
        return None
    cx = sum(p[0] for p in uniq) / len(uniq)
    cy = sum(p[1] for p in uniq) / len(uniq)
    ordered = sorted(uniq, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

    corners: list[tuple[float, float]] = []
    n = len(ordered)
    for i in range(n):
        prev, cur, nxt = ordered[(i - 1) % n], ordered[i], ordered[(i + 1) % n]
        a_in = _line_angle_deg(prev, cur)
        a_out = _line_angle_deg(cur, nxt)
        if _angle_diff_mod180(a_in, a_out) <= DOOR_SLIDE_RECT_PARALLEL_TOL_DEG:
            continue  # mid-side vertex of a split side
        corners.append(cur)
    if len(corners) != 4:
        return None

    sides = []
    for i in range(4):
        p1, p2 = corners[i], corners[(i + 1) % 4]
        sides.append((_distance(p1, p2), _line_angle_deg(p1, p2)))
    if _angle_diff_mod180(sides[0][1], sides[2][1]) > DOOR_SLIDE_RECT_PARALLEL_TOL_DEG:
        return None
    if _angle_diff_mod180(sides[1][1], sides[3][1]) > DOOR_SLIDE_RECT_PARALLEL_TOL_DEG:
        return None
    if abs(_angle_diff_mod180(sides[0][1], sides[1][1]) - 90.0) > DOOR_SLIDE_RECT_PERP_TOL_DEG:
        return None

    la = (sides[0][0] + sides[2][0]) / 2
    lb = (sides[1][0] + sides[3][0]) / 2
    if la >= lb:
        length, thickness, axis = la, lb, sides[0][1]
    else:
        length, thickness, axis = lb, la, sides[1][1]
    if thickness < 1e-6:
        return None
    ccx = sum(p[0] for p in corners) / 4
    ccy = sum(p[1] for p in corners) / 4
    return {
        "center": (ccx, ccy),
        "length": length,
        "thickness": thickness,
        "axis_deg": axis % 180.0,
        "corners": corners,
    }


def _panel_shape_ok(rect: dict, *, gates: DoorGates) -> bool:
    return (
        gates.DOOR_MIN_SIZE_PX <= rect["length"] <= gates.DOOR_MAX_SIZE_PX
        and rect["length"] / rect["thickness"] >= DOOR_LEAF_ASPECT_MIN
        and gates.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX
        <= rect["thickness"]
        <= gates.DOOR_SLIDE_PANEL_MAX_THICKNESS_PX
    )


def _corners_bbox(corners: list[tuple[float, float]]) -> BBox:
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def _snap_key(point: tuple[float, float], tol: float) -> tuple[int, int]:
    return (round(point[0] / tol), round(point[1] / tol))


def _ring_rects(
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float]]],
    snap_tol: float,
) -> list[tuple[dict, list[int], PathPrimitive]]:
    """Closed 4-8 segment loops among the given `l` segments, as oriented rects."""
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, (_, p1, p2) in enumerate(segs):
        buckets[_snap_key(p1, snap_tol)].append(idx)
        buckets[_snap_key(p2, snap_tol)].append(idx)
    adjacency: list[set[int]] = [set() for _ in segs]
    for ids in buckets.values():
        if len(ids) > 8:
            continue
        for idx in ids:
            adjacency[idx].update(other for other in ids if other != idx)

    rects: list[tuple[dict, list[int], PathPrimitive]] = []
    seen: set[int] = set()
    for start in range(len(segs)):
        if start in seen:
            continue
        stack, component = [start], []
        seen.add(start)
        while stack:
            idx = stack.pop()
            component.append(idx)
            for other in adjacency[idx]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        if not (4 <= len(component) <= 8):
            continue
        degrees: dict[tuple[int, int], int] = defaultdict(int)
        pts: list[tuple[float, float]] = []
        for i in component:
            _, p1, p2 = segs[i]
            degrees[_snap_key(p1, snap_tol)] += 1
            degrees[_snap_key(p2, snap_tol)] += 1
            pts.extend((p1, p2))
        if any(d != 2 for d in degrees.values()):
            continue
        rect = _fit_oriented_rect(pts)
        if rect is None:
            continue
        indices = sorted(segs[i][0].path_index for i in component)
        rects.append((rect, indices, segs[component[0]][0]))
    return rects


def _line_segs(
    paths: list[PathPrimitive], want_white: bool
) -> list[tuple[PathPrimitive, tuple[float, float], tuple[float, float]]]:
    segs = []
    for path in paths:
        if _is_background_fill(path.fill) != want_white:
            continue
        if not want_white and path.fill is not None:
            continue  # colored solid fills are furniture/poche, never a panel outline
        ok, p1, p2 = _is_line_path(path)
        if ok and _distance(p1, p2) > 1.0:
            segs.append((path, p1, p2))
    return segs


def _white_ring_rects(paths: list[PathPrimitive]) -> list[tuple[dict, list[int], PathPrimitive]]:
    """Closed loops of white-filled `l` items — the Vectorworks joinery
    signature: every sliding panel is drawn as a background-fill (white)
    polygon of exploded `l` edges, usually doubled by a stroked `qu` outline
    (merged later by `_collect_slide_panels`)."""
    return _ring_rects(_line_segs(paths, True), DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)


def _stroked_ring_rects(paths: list[PathPrimitive]) -> list[tuple[dict, list[int], PathPrimitive]]:
    """Closed loops of fill-less stroked `l` items — the flattened-PDF drawing
    style (Microsoft Print to PDF strips fills), where a sliding panel is a
    bare 4-segment rectangle. Snapped at CAD precision: the white-ring 3px
    buckets would chain a stroked ring into the adjacent wall linework and
    reject it as an oversized component."""
    return _ring_rects(_line_segs(paths, False), DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX)


def _collect_slide_panels(
    paths: list[PathPrimitive], include_stroked_rings: bool = False,
    *, gates: DoorGates,
) -> list[_SlidePanel]:
    raw: list[_SlidePanel] = []

    for path in paths:
        if path.item_type not in ("re", "qu") or len(path.points) < 4:
            continue
        rect = _fit_oriented_rect(list(path.points))
        if rect is None or not _panel_shape_ok(rect, gates=gates):
            continue
        raw.append(_SlidePanel(
            center=rect["center"], length=rect["length"], thickness=rect["thickness"],
            axis_deg=rect["axis_deg"], corners=rect["corners"],
            bbox=_corners_bbox(rect["corners"]),
            path_indices=[path.path_index], sources=[path.item_type],
            white=_is_background_fill(path.fill),
            layer=path.layer,
            layer_hint=_layer_hint_from_layer(path.layer, DOOR_LAYER_KEYWORDS),
        ))

    for rect, indices, first_path in _white_ring_rects(paths):
        if not _panel_shape_ok(rect, gates=gates):
            continue
        raw.append(_SlidePanel(
            center=rect["center"], length=rect["length"], thickness=rect["thickness"],
            axis_deg=rect["axis_deg"], corners=rect["corners"],
            bbox=_corners_bbox(rect["corners"]),
            path_indices=indices, sources=["white_ring"],
            white=True,
            layer=first_path.layer,
            layer_hint=_layer_hint_from_layer(first_path.layer, DOOR_LAYER_KEYWORDS),
        ))

    # Stroked (fill-less) rings carry none of the joinery fill signature, so
    # they only ever feed the parked_leaf pattern, whose band/jamb/slide-law
    # gates supply the missing evidence — the pair pool excludes them.
    if include_stroked_rings:
        for rect, indices, first_path in _stroked_ring_rects(paths):
            if not _panel_shape_ok(rect, gates=gates):
                continue
            raw.append(_SlidePanel(
                center=rect["center"], length=rect["length"], thickness=rect["thickness"],
                axis_deg=rect["axis_deg"], corners=rect["corners"],
                bbox=_corners_bbox(rect["corners"]),
                path_indices=indices, sources=["stroked_ring"],
                white=False,
                layer=first_path.layer,
                layer_hint=_layer_hint_from_layer(first_path.layer, DOOR_LAYER_KEYWORDS),
            ))

    # Merge coincident representations (white ring + stroked qu of one panel).
    merged: list[_SlidePanel] = []
    for panel in raw:
        for kept in merged:
            if (
                _distance(panel.center, kept.center) <= DOOR_SLIDE_PANEL_MERGE_TOL_PX
                and _angle_diff_mod180(panel.axis_deg, kept.axis_deg) <= 3.0
                and abs(panel.length - kept.length) <= DOOR_SLIDE_PANEL_MERGE_TOL_PX
                and abs(panel.thickness - kept.thickness) <= DOOR_SLIDE_PANEL_MERGE_TOL_PX
            ):
                kept.path_indices = sorted(set(kept.path_indices) | set(panel.path_indices))
                kept.sources = sorted(set(kept.sources) | set(panel.sources))
                kept.white = kept.white or panel.white
                kept.layer = kept.layer or panel.layer
                kept.layer_hint = kept.layer_hint or panel.layer_hint
                break
        else:
            merged.append(panel)
    return merged


def _axial_offsets(
    panel: _SlidePanel, point: tuple[float, float]
) -> tuple[float, float]:
    """(along-axis, lateral) offsets of a point from the panel's center."""
    theta = math.radians(panel.axis_deg)
    ux, uy = math.cos(theta), math.sin(theta)
    dx, dy = point[0] - panel.center[0], point[1] - panel.center[1]
    return dx * ux + dy * uy, -dx * uy + dy * ux


def _pair_leaf_panels(panels: list[_SlidePanel]) -> list[tuple[_SlidePanel, _SlidePanel, dict]]:
    """leaf_pair pattern: two parallel near-equal panels, in-band, partial overlap."""
    scored: list[tuple[float, int, int, dict]] = []
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            a, b = panels[i], panels[j]
            if _angle_diff_mod180(a.axis_deg, b.axis_deg) > DOOR_SLIDE_AXIS_TOL_DEG:
                continue
            if abs(a.length - b.length) / max(a.length, b.length) > DOOR_SLIDE_LENGTH_RATIO_TOL:
                continue
            d_ax, d_lat = _axial_offsets(a, b.center)
            d_ax, d_lat = abs(d_ax), abs(d_lat)
            if d_lat > (a.thickness + b.thickness) / 2 * DOOR_SLIDE_LATERAL_FACTOR:
                continue
            overlap_frac = ((a.length + b.length) / 2 - d_ax) / min(a.length, b.length)
            if not (DOOR_SLIDE_OVERLAP_MIN_FRAC <= overlap_frac <= DOOR_SLIDE_OVERLAP_MAX_FRAC):
                continue
            metrics = {
                "overlap_frac": round(overlap_frac, 3),
                "lateral_offset_px": round(d_lat, 2),
            }
            scored.append((d_lat + abs(overlap_frac - 0.5), i, j, metrics))

    pairs: list[tuple[_SlidePanel, _SlidePanel, dict]] = []
    for _, i, j, metrics in sorted(scored, key=lambda t: t[0]):
        if panels[i].consumed or panels[j].consumed:
            continue
        panels[i].consumed = True
        panels[j].consumed = True
        pairs.append((panels[i], panels[j], metrics))
    return pairs


def _merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for lo, hi in sorted(spans):
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def _pocket_leaf_match(
    panel: _SlidePanel,
    line_paths: list[PathPrimitive],
    *, gates: DoorGates,
) -> tuple[dict, list[tuple[float, float]] | None] | None:
    """pocket_leaf pattern: a panel flanked on both sides by wall faces over
    part of its length, protruding into clear space at one end. Returns
    (metrics, opening corridor corners or None) or None."""
    own = set(panel.path_indices)
    half_len = panel.length / 2
    half_th = panel.thickness / 2

    sides: dict[int, list[tuple[float, float]]] = {1: [], -1: []}
    side_gap: dict[int, float] = {}
    crosser_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    all_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for path in line_paths:
        if path.path_index in own:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        line_len = _distance(p1, p2)
        if line_len < 6.0:
            continue
        angle = _line_angle_deg(p1, p2)
        t1, d1 = _axial_offsets(panel, p1)
        t2, d2 = _axial_offsets(panel, p2)
        all_lines.append(((t1, d1), (t2, d2)))
        if _angle_diff_mod180(angle, panel.axis_deg) > DOOR_SLIDE_AXIS_TOL_DEG:
            if _angle_diff_mod180(angle, panel.axis_deg) > 30.0:
                crosser_lines.append(((t1, d1), (t2, d2)))
            continue
        if line_len < DOOR_SLIDE_FLANK_LINE_MIN_LEN_FRAC * panel.length:
            continue
        if abs(d1 - d2) > 3.0:
            continue
        lat = (d1 + d2) / 2
        gap = abs(lat) - half_th
        if not (gates.DOOR_SLIDE_FLANK_GAP_MIN_PX <= gap <= gates.DOOR_SLIDE_FLANK_GAP_MAX_PX):
            continue
        lo, hi = min(t1, t2), max(t1, t2)
        lo, hi = max(lo, -half_len), min(hi, half_len)
        if hi - lo < DOOR_SLIDE_FLANK_SIDE_MIN_FRAC * panel.length:
            continue
        side = 1 if lat > 0 else -1
        sides[side].append((lo, hi))
        side_gap[side] = min(side_gap.get(side, gap), gap)
    if not sides[1] or not sides[-1]:
        return None

    both: list[tuple[float, float]] = []
    for a1, b1 in _merge_spans(sides[1]):
        for a2, b2 in _merge_spans(sides[-1]):
            lo, hi = max(a1, a2), min(b1, b2)
            if hi > lo:
                both.append((lo, hi))
    if not both:
        return None
    flank_frac = sum(hi - lo for lo, hi in both) / panel.length
    if not (DOOR_SLIDE_FLANK_MIN_FRAC <= flank_frac <= DOOR_SLIDE_FLANK_MAX_FRAC):
        return None

    cover_lo = min(lo for lo, _ in both)
    cover_hi = max(hi for _, hi in both)
    protrusion_lo = cover_lo + half_len
    protrusion_hi = half_len - cover_hi
    protrusion = max(protrusion_lo, protrusion_hi)
    if not (
        DOOR_SLIDE_PROTRUSION_MIN_FRAC * panel.length
        <= protrusion
        <= DOOR_SLIDE_PROTRUSION_MAX_FRAC * panel.length
    ):
        return None

    # The protruding end must land in clear space (the doorway). A wall strip
    # "protruding" into the wall's continuation is crossed by hatch/band lines.
    if protrusion_hi >= protrusion_lo:
        z_lo, z_hi = cover_hi, half_len
    else:
        z_lo, z_hi = -half_len, cover_lo
    zone_half_width = half_th * DOOR_SLIDE_ZONE_WIDTH_FACTOR
    crossers = 0
    for (t1, d1), (t2, d2) in crosser_lines:
        if max(t1, t2) < z_lo or min(t1, t2) > z_hi:
            continue
        if min(abs(d1), abs(d2)) > zone_half_width:
            continue
        crossers += 1
    if crossers > DOOR_SLIDE_ZONE_MAX_CROSSERS:
        return None

    metrics = {
        "flank_frac": round(flank_frac, 3),
        "flank_gap_max_px": round(max(side_gap.values()), 2),
        "protrusion_px": round(protrusion, 2),
        "protrusion_frac": round(protrusion / panel.length, 3),
        "zone_crossers": crossers,
    }

    # Far jamb under the slide law: the doorway a pocket leaf serves runs one
    # panel length out of the pocket mouth (the leaf covers it exactly when
    # drawn shut), so the jamb closing the opening — a line ENDING in the
    # corridor or CROSSING it (a pier's end cap spans the whole band, so its
    # endpoints lie outside the leaf's corridor) — sits ~one length away.
    # Found, the corridor joins the emitted bbox so the room stage can plug
    # the doorway the half-drawn leaf never covers (s04 door_0014: panel
    # 91.7px, pier cap 90px out of the mouth; the slide arrow's 45° tick
    # inside the corridor is the one tolerated crosser). Not found (the
    # opening meets another wall obliquely, no jamb drawn), the bbox stays
    # the panel's own, as before.
    mouth, opening_dir = (
        (cover_hi, 1.0) if protrusion_hi >= protrusion_lo else (cover_lo, -1.0)
    )
    lat_lim = half_th + max(side_gap.values()) + 1.0
    best: tuple[float, float] | None = None
    for (t1, d1), (t2, d2) in all_lines:
        at: list[float] = [t for t, d in ((t1, d1), (t2, d2)) if abs(d) <= lat_lim]
        if (d1 < 0.0) != (d2 < 0.0) and abs(d2 - d1) > 1e-6:
            at.append(t1 + (t2 - t1) * (-d1) / (d2 - d1))
        for t in at:
            dist = (t - mouth) * opening_dir
            if dist < half_len + 2.0:
                continue  # inside the panel's own extent
            dev = abs(dist - panel.length) / panel.length
            if dev <= DOOR_SLIDE_PARK_SPAN_RATIO_TOL and (best is None or dev < best[1]):
                best = (dist, dev)
    corridor: list[tuple[float, float]] | None = None
    if best is not None:
        span, dev = best
        far = mouth + opening_dir * span
        o_lo, o_hi = sorted((mouth, far))
        corridor_crossers = 0
        for (t1, d1), (t2, d2) in crosser_lines:
            if max(t1, t2) < o_lo + 1.0 or min(t1, t2) > o_hi - 1.0:
                continue
            if min(abs(d1), abs(d2)) > zone_half_width:
                continue
            corridor_crossers += 1
        if corridor_crossers <= DOOR_SLIDE_ZONE_MAX_CROSSERS:
            theta = math.radians(panel.axis_deg)
            ux, uy = math.cos(theta), math.sin(theta)
            corridor = [
                (panel.center[0] + t * ux - d * uy, panel.center[1] + t * uy + d * ux)
                for t in (mouth, far)
                for d in (half_th + side_gap[1], -(half_th + side_gap[-1]))
            ]
            metrics.update({
                "opening_span_px": round(span, 1),
                "span_ratio_dev": round(dev, 3),
                "corridor_crossers": corridor_crossers,
                "opening_bbox": [round(v, 1) for v in _corners_bbox(corridor)],
            })
    return metrics, corridor


def _parked_leaf_match(
    panel: _SlidePanel,
    line_paths: list[PathPrimitive],
    *, gates: DoorGates,
) -> tuple[dict, list[tuple[float, float]]] | None:
    """parked_leaf pattern: a thin closed panel parked flush along one face of
    a wall band that ends at a jamb, with a clear opening of ~one panel length
    beyond the jamb — the slide law: the panel covers the opening exactly when
    slid along its own axis. This is the evidence tier for fill-less drawings
    (no white joinery signature): band + jamb + slide law replace the fill.
    Returns (metrics, opening corridor corner points) or None."""
    own = set(panel.path_indices)
    half_len = panel.length / 2
    half_th = panel.thickness / 2

    parallels: list[tuple[float, float, float]] = []
    obliques: list[tuple[tuple[float, float], tuple[float, float]]] = []
    endpoints: list[tuple[float, float]] = []
    for path in line_paths:
        if path.path_index in own:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok or _distance(p1, p2) < 4.0:
            continue
        t1, d1 = _axial_offsets(panel, p1)
        t2, d2 = _axial_offsets(panel, p2)
        endpoints.extend(((t1, d1), (t2, d2)))
        delta = _angle_diff_mod180(_line_angle_deg(p1, p2), panel.axis_deg)
        if delta <= DOOR_SLIDE_AXIS_TOL_DEG and abs(d1 - d2) <= 3.0:
            parallels.append(((d1 + d2) / 2, min(t1, t2), max(t1, t2)))
        elif delta > 30.0:
            obliques.append(((t1, d1), (t2, d2)))

    # 1) The hugged band face: flush alongside one long edge, running behind
    #    (almost) the whole panel.
    face = None
    for lat, lo, hi in parallels:
        gap = abs(lat) - half_th
        if not (gates.DOOR_SLIDE_FLANK_GAP_MIN_PX <= gap <= gates.DOOR_SLIDE_PARK_GAP_MAX_PX):
            continue
        cover = (min(hi, half_len) - max(lo, -half_len)) / panel.length
        if cover < DOOR_SLIDE_PARK_FACE_COVER_MIN:
            continue
        if face is None or cover > face[3]:
            face = (lat, lo, hi, cover)
    if face is None:
        return None
    face_lat, face_lo, face_hi, face_cover = face
    side = 1.0 if face_lat > 0 else -1.0

    # 2) The face belongs to a wall band: a partner face farther out on the
    #    same side at band-like spacing, running with it.
    band = None
    for lat, lo, hi in parallels:
        depth = (lat - face_lat) * side
        if not (gates.DOOR_SLIDE_PARK_BAND_MIN_TH_PX <= depth <= gates.DOOR_SLIDE_PARK_BAND_MAX_TH_PX):
            continue
        if min(hi, face_hi) - max(lo, face_lo) < 0.5 * (face_hi - face_lo):
            continue
        if band is None or depth < band[3]:
            band = (lat, lo, hi, depth)
    if band is None:
        return None
    band_lat, band_lo, band_hi, band_th = band

    # 3) The band ends at a jamb aligned with one panel end (both faces end
    #    together there), and runs past the panel's other end.
    jamb = None
    tol = gates.DOOR_SLIDE_PARK_JAMB_TOL_PX
    if (
        abs(face_lo + half_len) <= tol
        and face_hi >= half_len - tol
        and abs(band_lo - face_lo) <= tol / 2
    ):
        jamb = (face_lo, -1.0)
    elif (
        abs(face_hi - half_len) <= tol
        and face_lo <= -half_len + tol
        and abs(band_hi - face_hi) <= tol / 2
    ):
        jamb = (face_hi, 1.0)
    if jamb is None:
        return None
    t_jamb, opening_dir = jamb

    # 4) Slide law: the nearest linework endpoint in the band corridor beyond
    #    the jamb (the far jamb) sits ~one panel length away.
    lat_lo = min(face_lat, band_lat) - 1.0
    lat_hi = max(face_lat, band_lat) + 1.0
    span = None
    for t, d in endpoints:
        if not (lat_lo <= d <= lat_hi):
            continue
        dist = (t - t_jamb) * opening_dir
        if dist < 2.0:
            continue
        if span is None or dist < span:
            span = dist
    if span is None:
        return None
    span_dev = abs(span - panel.length) / panel.length
    if span_dev > DOOR_SLIDE_PARK_SPAN_RATIO_TOL:
        return None

    # 5) The opening corridor is clear (jamb end caps sit on its margins).
    o_lo, o_hi = sorted((t_jamb, t_jamb + opening_dir * span))
    crossers = 0
    for (t1, d1), (t2, d2) in obliques:
        if max(t1, t2) < o_lo + 1.0 or min(t1, t2) > o_hi - 1.0:
            continue
        if max(d1, d2) < lat_lo or min(d1, d2) > lat_hi:
            continue
        crossers += 1
    if crossers > DOOR_SLIDE_ZONE_MAX_CROSSERS:
        return None

    theta = math.radians(panel.axis_deg)
    ux, uy = math.cos(theta), math.sin(theta)

    def to_page(t: float, d: float) -> tuple[float, float]:
        return (
            panel.center[0] + t * ux - d * uy,
            panel.center[1] + t * uy + d * ux,
        )

    far = t_jamb + opening_dir * span
    corridor = [to_page(t, d) for t in (t_jamb, far) for d in (face_lat, band_lat)]
    metrics = {
        "flank_gap_px": round(abs(face_lat) - half_th, 2),
        "face_cover_frac": round(face_cover, 3),
        "band_thickness_px": round(band_th, 1),
        "opening_span_px": round(span, 1),
        "span_ratio_dev": round(span_dev, 3),
        "zone_crossers": crossers,
        "opening_bbox": [round(v, 1) for v in _corners_bbox(corridor)],
    }
    return metrics, corridor


def _detect_sliding_doors(
    paths: list[PathPrimitive],
    line_paths: list[PathPrimitive],
    swings: list[_DoorSwing],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None,
    cand_idx: int,
    *, gates: DoorGates,
) -> tuple[list[Candidate], int]:
    """Detect arc-less sliding doors. Returns (candidates, next candidate index).

    Runs after arc-swing pairing inside _pair_door_assemblies. Emitted
    candidates carry method="door_assembly" / assembly_type="sliding" so the
    wall cross-validation applies the assembled-door penalty tier, and their
    component_path_indices contain only the panels' own primitives so
    _dedupe_door_components retires the leaf-fallback candidates that the same
    rectangles would otherwise produce (without ever suppressing neighbours
    that merely share wall linework).
    """
    panels = _collect_slide_panels(paths, include_stroked_rings=True, gates=gates)
    candidates: list[Candidate] = []

    def mint(
        slide_style: str,
        involved: list[_SlidePanel],
        metrics: dict,
        extra_points: list[tuple[float, float]] | None = None,
    ) -> Candidate:
        nonlocal cand_idx
        corners = [c for p in involved for c in p.corners]
        bbox = _corners_bbox(corners + (extra_points or []))
        nearby_label = _find_nearby_label(
            bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN,
        )
        layer = next((p.layer for p in involved if p.layer), None)
        layer_hint = any(p.layer_hint for p in involved)
        label_boost = 0.20 if nearby_label else 0.0
        layer_boost = 0.40 if layer_hint else 0.0
        confidence = round(
            min(DOOR_SLIDE_ASSEMBLY_BASE + label_boost + layer_boost, 0.95), 3,
        )
        component_path_indices = sorted({i for p in involved for i in p.path_indices})
        evidence = {
            "method": "door_assembly",
            "assembly_type": "sliding",
            "slide_style": slide_style,
            "leaf_bboxes": [list(p.bbox) for p in involved],
            "leaf_sources": ["+".join(p.sources) for p in involved],
            "panel_length_px": round(involved[0].length, 1),
            "panel_axis_deg": round(involved[0].axis_deg, 1),
            "component_path_indices": component_path_indices,
            "nearby_label": nearby_label,
            "layer": layer,
            "layer_hint": layer_hint,
            "opening_check": "not_applicable",
        }
        evidence.update(metrics)
        candidate_id = f"door_{cand_idx:04d}"
        cand_idx += 1
        candidate = Candidate(
            candidate_id=candidate_id,
            entity_type="door",
            bbox=bbox,
            confidence=confidence,
            evidence=evidence,
        )
        if collector:
            collector.record_candidate(
                candidate_id, "sliding_assembly", confidence,
                {
                    "base": DOOR_SLIDE_ASSEMBLY_BASE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": layer_hint,
                    "slide_style": slide_style,
                    **metrics,
                    "total": confidence,
                },
                None, None,
            )
        return candidate

    # Stroked-only rings never enter the pair pool: two coincident joinery
    # rectangles carry none of the leaf_pair calibration evidence.
    pairable = [p for p in panels if p.sources != ["stroked_ring"]]
    for panel_a, panel_b, metrics in _pair_leaf_panels(pairable):
        candidates.append(mint("leaf_pair", [panel_a, panel_b], metrics))

    for panel in panels:
        if panel.consumed:
            continue
        # An open hinged leaf lying against a wall face can mimic a pocketed
        # panel; a leaf attached to a swing arc is the swing's business.
        if any(_bboxes_overlap(panel.bbox, swing.bbox) for swing in swings):
            continue
        match = _pocket_leaf_match(panel, line_paths, gates=gates)
        if match is None:
            continue
        metrics, corridor = match
        # A bare stroked/qu panel (no white joinery ring) qualifies only when
        # the cavity hugs it on both sides (DOOR_SLIDE_POCKET_TIGHT_GAP_PX).
        if (
            not panel.white
            and metrics["flank_gap_max_px"] > gates.DOOR_SLIDE_POCKET_TIGHT_GAP_PX
        ):
            continue
        panel.consumed = True
        candidates.append(mint("pocket_leaf", [panel], metrics, corridor))

    for panel in panels:
        if panel.consumed:
            continue
        if any(_bboxes_overlap(panel.bbox, swing.bbox) for swing in swings):
            continue
        match = _parked_leaf_match(panel, line_paths, gates=gates)
        if match is None:
            continue
        metrics, corridor = match
        panel.consumed = True
        candidates.append(mint("parked_leaf", [panel], metrics, corridor))

    return candidates, cand_idx
