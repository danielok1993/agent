from __future__ import annotations
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_height, _bbox_width, _interval_overlap, _line_angle_deg, _line_length, _perpendicular_spacing, _projected_interval
from detection.layers import _layer_hint, _layer_strong_prior

# ---------------------------------------------------------------------------
# Window detection constants
# ---------------------------------------------------------------------------
WINDOW_MIN_LINES            = 2
WINDOW_MAX_LINES            = 6
WINDOW_PARALLEL_ANGLE_TOL   = 8.0   # degrees
WINDOW_LENGTH_RATIO_MIN     = 0.80
WINDOW_SPACING_MIN_PX       = 3.0
WINDOW_SPACING_MAX_PX       = 50.0
WINDOW_MIN_LENGTH_PX        = 15.0
WINDOW_MAX_LENGTH_PX        = 350.0
WINDOW_GROUPING_GAP_PX      = 8.0
WINDOW_MIN_CONFIDENCE       = 0.35
WINDOW_HATCH_REJECT_MIN     = 5
WINDOW_HATCH_REJECT_RATIO   = 0.45


def detect_windows(paths: list[PathPrimitive]) -> list[Candidate]:
    """Detect windows as groups of short parallel lines with aligned extents.

    The previous version only checked parallel angle, length ratio, and spacing.
    That produced false positives from stair treads, hatch patterns, and dimension
    ticks. This version additionally requires:
      - projected endpoint overlap ≥ 70 % of the shorter segment (aligned extents)
      - group bounding box is long and narrow (aspect ≥ 3:1 on the dominant axis)
      - total group width ≤ WINDOW_SPACING_MAX_PX * (WINDOW_MAX_LINES - 1)
    """
    # Keywords must be single tokens (layer "A-WIND" → tokens {"a","wind"}).
    # Multi-token strings like "a-wind" will never appear in the token set.
    win_keywords = ["window", "wind", "glaz", "glazing"]

    line_paths = [
        p for p in paths
        if p.item_type == "l" and len(p.points) >= 2
        and WINDOW_MIN_LENGTH_PX <= _line_length(p.points[0], p.points[-1]) <= WINDOW_MAX_LENGTH_PX
    ]

    used = set()
    candidates = []
    cand_idx = 0

    for i, lp in enumerate(line_paths):
        if i in used:
            continue
        p1, p2 = lp.points[0], lp.points[-1]
        angle_i = _line_angle_deg(p1, p2)
        len_i = _line_length(p1, p2)
        if len_i < 1e-6:
            continue

        dx = (p2[0] - p1[0]) / len_i
        dy = (p2[1] - p1[1]) / len_i
        ref_interval = _projected_interval(p1, p2, dx, dy, p1)

        group = [lp]
        group_indices = {i}

        for j, lp2 in enumerate(line_paths):
            if j <= i or j in used:
                continue
            q1, q2 = lp2.points[0], lp2.points[-1]
            angle_j = _line_angle_deg(q1, q2)
            len_j = _line_length(q1, q2)

            angle_diff = abs(angle_i - angle_j)
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            if angle_diff > WINDOW_PARALLEL_ANGLE_TOL:
                continue

            if len_j < 1e-6:
                continue
            len_ratio = min(len_i, len_j) / max(len_i, len_j)
            if len_ratio < WINDOW_LENGTH_RATIO_MIN:
                continue

            spacing = _perpendicular_spacing(p1, p2, q1, q2)
            if not (WINDOW_SPACING_MIN_PX <= spacing <= WINDOW_SPACING_MAX_PX):
                continue

            # Endpoint projection overlap: lines must be spatially aligned,
            # not just parallel. Reject if overlap < 70 % of the shorter segment.
            cand_interval = _projected_interval(q1, q2, dx, dy, p1)
            overlap = _interval_overlap(ref_interval, cand_interval)
            min_len = min(len_i, len_j)
            if min_len > 0 and overlap / min_len < 0.70:
                continue

            group.append(lp2)
            group_indices.add(j)

            if len(group) >= WINDOW_MAX_LINES:
                break

        if len(group) < WINDOW_MIN_LINES:
            continue

        all_pts = [pt for lp_g in group for pt in [lp_g.points[0], lp_g.points[-1]]]
        xs = [pt[0] for pt in all_pts]
        ys = [pt[1] for pt in all_pts]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))

        bw = _bbox_width(bbox)
        bh = _bbox_height(bbox)
        long_side = max(bw, bh)
        short_side = min(bw, bh)

        # Window opening must be long and narrow.
        if short_side < 1e-6 or long_side / short_side < 3.0:
            continue

        # Total depth must stay within the expected glazing stack thickness.
        max_depth = WINDOW_SPACING_MAX_PX * (WINDOW_MAX_LINES - 1)
        if short_side > max_depth:
            continue

        layer_hint = any(_layer_hint(lp_g, win_keywords) for lp_g in group)
        layer_prior = max(
            (_layer_strong_prior(lp_g, win_keywords) for lp_g in group), default=0.0
        )

        spacing_vals = []
        for lp_g in group[1:]:
            q1, q2 = lp_g.points[0], lp_g.points[-1]
            spacing_vals.append(_perpendicular_spacing(p1, p2, q1, q2))

        confidence = 0.45
        if len(group) >= 3:
            confidence += 0.15
        confidence += layer_prior
        if layer_hint and layer_prior == 0.0:
            confidence += 0.10
        if spacing_vals and len(set(round(s, 0) for s in spacing_vals)) == 1:
            confidence += 0.10
        confidence = min(confidence, 0.90)

        if confidence < WINDOW_MIN_CONFIDENCE:
            continue

        for idx in group_indices:
            used.add(idx)

        candidates.append(Candidate(
            candidate_id=f"window_{cand_idx:04d}",
            entity_type="window",
            bbox=bbox,
            confidence=round(confidence, 3),
            evidence={
                "line_count": len(group),
                "avg_length_px": round(sum(_line_length(lp_g.points[0], lp_g.points[-1]) for lp_g in group) / len(group), 1),
                "avg_spacing_px": round(sum(spacing_vals) / len(spacing_vals), 1) if spacing_vals else None,
                "aspect_ratio": round(long_side / short_side, 2) if short_side > 0 else None,
                "layer_hint": layer_hint,
            },
        ))
        cand_idx += 1

    return candidates
