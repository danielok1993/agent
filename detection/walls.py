from __future__ import annotations
import math
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_expanded, _bboxes_overlap, _line_angle_deg, _line_length, _perpendicular_spacing, _point_in_bbox, _project_onto_axis
from detection.layers import _layer_tokens

# ---------------------------------------------------------------------------
# Wall detection constants
# ---------------------------------------------------------------------------
WALL_MIN_LENGTH_PX          = 60.0
WALL_MAX_OFFSET_PX          = 30.0
WALL_PARALLEL_ANGLE_TOL     = 5.0   # degrees
WALL_LENGTH_RATIO_MIN       = 0.85
WALL_MIN_STROKE_WIDTH_PX    = 0.5
WALL_MIN_CONFIDENCE         = 0.50
WALL_HATCH_MIN_SEGMENTS     = 5
WALL_HATCH_MIN_RATIO        = 0.45

# Tolerance for two segments to be considered on the same line.
COLLINEAR_ANGLE_TOL    = 3.0   # degrees
COLLINEAR_OFFSET_TOL   = 4.0   # px perpendicular distance between lines
COLLINEAR_GAP_MAX_PX   = 30.0  # max endpoint gap to bridge (door/window openings)


def _is_diagonal_hatch_angle(angle: float) -> bool:
    return 25.0 <= angle <= 65.0 or 115.0 <= angle <= 155.0


def _wall_material_evidence(paths: list[PathPrimitive], bbox: BBox) -> dict:
    """Measure whether a bbox contains wall-like material fill.

    Many architectural PDFs do not use a PDF fill color for walls. Instead
    they draw diagonal hatch strokes inside the wall band. This helper treats
    dense short diagonal strokes as wall material evidence, while also tracking
    true filled rectangles/quads when the PDF exposes them.
    """
    expanded = _bbox_expanded(bbox, 2.0)
    hatch_count = 0
    short_line_count = 0
    filled_overlap = False

    for path in paths:
        if path.item_type == "l" and len(path.points) >= 2:
            p1, p2 = path.points[0], path.points[-1]
            midpoint = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            if not _point_in_bbox(midpoint, expanded):
                continue
            length = _line_length(p1, p2)
            if not (2.0 <= length <= 45.0):
                continue
            short_line_count += 1
            if _is_diagonal_hatch_angle(_line_angle_deg(p1, p2)):
                hatch_count += 1
        elif path.fill is not None and path.item_type in ("re", "qu"):
            if _bboxes_overlap(path.bbox, expanded):
                filled_overlap = True

    hatch_ratio = hatch_count / short_line_count if short_line_count else 0.0
    return {
        "hatch_count": hatch_count,
        "short_line_count": short_line_count,
        "hatch_ratio": round(hatch_ratio, 3),
        "filled_overlap": filled_overlap,
        "wall_material": bool(
            filled_overlap
            or (
                hatch_count >= WALL_HATCH_MIN_SEGMENTS
                and hatch_ratio >= WALL_HATCH_MIN_RATIO
            )
        ),
    }


def _merge_collinear_segments(
    segs: list[tuple[tuple[float, float], tuple[float, float], str | None]],
) -> list[tuple[tuple[float, float], tuple[float, float], str | None]]:
    """Merge collinear atomic segments into runs.

    Architectural walls are frequently split into short segments at door and
    window openings. After path explosion each segment is atomic, so without
    merging the wall pairing step receives many short stubs that fall below
    WALL_MIN_LENGTH_PX. This pass reconnects segments that share the same
    infinite line and whose gap is small enough to bridge (< COLLINEAR_GAP_MAX_PX).

    Returns merged segments as (p_start, p_end, layer).
    """
    if not segs:
        return []

    merged = list(segs)
    changed = True
    while changed:
        changed = False
        out: list[tuple[tuple[float, float], tuple[float, float], str | None]] = []
        used = [False] * len(merged)

        for i, (a1, a2, la) in enumerate(merged):
            if used[i]:
                continue
            dx = a2[0] - a1[0]
            dy = a2[1] - a1[1]
            length_a = math.hypot(dx, dy)
            if length_a < 1e-6:
                used[i] = True
                continue
            ux, uy = dx / length_a, dy / length_a

            run_pts = [a1, a2]
            run_layer = la

            for j, (b1, b2, lb) in enumerate(merged):
                if j <= i or used[j]:
                    continue
                # Angle compatibility
                bx, by = b2[0] - b1[0], b2[1] - b1[1]
                length_b = math.hypot(bx, by)
                if length_b < 1e-6:
                    continue
                angle_diff = abs(_line_angle_deg(a1, a2) - _line_angle_deg(b1, b2))
                if angle_diff > 90:
                    angle_diff = 180 - angle_diff
                if angle_diff > COLLINEAR_ANGLE_TOL:
                    continue

                # Perpendicular offset from a1 to b's line
                offset = abs((b1[0] - a1[0]) * (-uy) + (b1[1] - a1[1]) * ux)
                if offset > COLLINEAR_OFFSET_TOL:
                    continue

                # Projected positions of b's endpoints onto a's axis
                t_b1 = _project_onto_axis(b1, a1, ux, uy)
                t_b2 = _project_onto_axis(b2, a1, ux, uy)
                t_a1 = 0.0
                t_a2 = _project_onto_axis(a2, a1, ux, uy)

                run_min = min(_project_onto_axis(p, a1, ux, uy) for p in run_pts)
                run_max = max(_project_onto_axis(p, a1, ux, uy) for p in run_pts)
                seg_min = min(t_b1, t_b2)
                seg_max = max(t_b1, t_b2)

                gap = max(seg_min - run_max, run_min - seg_max, 0.0)
                if gap > COLLINEAR_GAP_MAX_PX:
                    continue

                run_pts.extend([b1, b2])
                if lb and not run_layer:
                    run_layer = lb
                used[j] = True
                changed = True

            # Rebuild merged segment from the extreme projected points
            ts = [_project_onto_axis(p, a1, ux, uy) for p in run_pts]
            t_lo, t_hi = min(ts), max(ts)
            new_p1 = (a1[0] + ux * t_lo, a1[1] + uy * t_lo)
            new_p2 = (a1[0] + ux * t_hi, a1[1] + uy * t_hi)
            out.append((new_p1, new_p2, run_layer))
            used[i] = True

        merged = out

    return merged


def detect_walls(paths: list[PathPrimitive]) -> list[Candidate]:
    wall_keywords = ["wall", "a-wall", "partition", "struct"]

    raw_segs = [
        (p.points[0], p.points[-1], p.layer)
        for p in paths
        if p.item_type == "l" and len(p.points) >= 2
        and p.stroke_width >= WALL_MIN_STROKE_WIDTH_PX
    ]

    merged = _merge_collinear_segments(raw_segs)

    # Filter to segments long enough to be wall candidates
    long_segs = [
        (p1, p2, layer)
        for p1, p2, layer in merged
        if _line_length(p1, p2) >= WALL_MIN_LENGTH_PX
    ]

    used = set()
    candidates = []
    cand_idx = 0

    for i, (p1, p2, layer_i) in enumerate(long_segs):
        if i in used:
            continue
        angle_i = _line_angle_deg(p1, p2)
        len_i = _line_length(p1, p2)

        for j, (q1, q2, layer_j) in enumerate(long_segs):
            if j <= i or j in used:
                continue
            angle_j = _line_angle_deg(q1, q2)
            len_j = _line_length(q1, q2)

            angle_diff = abs(angle_i - angle_j)
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            if angle_diff > WALL_PARALLEL_ANGLE_TOL:
                continue

            if len_j < 1e-6:
                continue
            len_ratio = min(len_i, len_j) / max(len_i, len_j)
            if len_ratio < WALL_LENGTH_RATIO_MIN:
                continue

            spacing = _perpendicular_spacing(p1, p2, q1, q2)
            if spacing > WALL_MAX_OFFSET_PX or spacing < 1.0:
                continue

            all_pts = [p1, p2, q1, q2]
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            bbox: BBox = (min(xs), min(ys), max(xs), max(ys))

            layer_hint = any(
                kw in _layer_tokens(layer_i) or kw in _layer_tokens(layer_j)
                for kw in wall_keywords
            )
            layer_prior = 0.40 if (layer_i or layer_j) and layer_hint else 0.0

            confidence = 0.55
            if len_i > 200:
                confidence += 0.15
            confidence += layer_prior
            if layer_hint and layer_prior == 0.0:
                confidence += 0.10
            confidence = min(confidence, 0.90)

            if confidence < WALL_MIN_CONFIDENCE:
                continue

            used.add(i)
            used.add(j)

            candidates.append(Candidate(
                candidate_id=f"wall_{cand_idx:04d}",
                entity_type="wall",
                bbox=bbox,
                confidence=round(confidence, 3),
                evidence={
                    "line_length_px": round(len_i, 1),
                    "pair_length_px": round(len_j, 1),
                    "spacing_px": round(spacing, 1),
                    "layer": layer_i,
                    "layer_hint": layer_hint,
                },
            ))
            cand_idx += 1
            break

    return candidates


def _stroke_percentile_rank(stroke_width: float, all_widths: list[float]) -> float:
    """Return the fraction of page strokes thinner than this one (0–1).

    Using relative rank rather than an absolute threshold handles PDFs where
    all strokes are 1.5 px (the sample case): a wall at the 90th percentile
    is thicker than annotation lines even if the absolute value is modest.
    Returns 0.5 when there is no width variation to avoid false signal.
    """
    if not all_widths or max(all_widths) - min(all_widths) < 0.1:
        return 0.5
    below = sum(1 for w in all_widths if w < stroke_width)
    return below / len(all_widths)
