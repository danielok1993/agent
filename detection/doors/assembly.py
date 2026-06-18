from __future__ import annotations
from itertools import combinations
from models import BBox, Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.geometry import _angle_diff_mod180, _bbox_area, _bbox_expanded, _bbox_height, _bbox_union, _bbox_width, _bboxes_overlap, _distance, _is_line_path, _line_angle_deg, _segments_min_distance
from detection.layers import _layer_hint_from_layer
from detection.labels import _find_nearby_label
from detection.doors.models import _DoorLeaf, _DoorSwing
from detection.doors.shape import _compute_hu_distance
from detection.doors.leaves import _find_anchored_leaf_line, _find_leaf_companion_lines
from detection.doors.constants import (
    DOOR_ARC_FALLBACK_MAX, DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_ASSEMBLY_LINE_LEAF_BASE,
    DOOR_DOUBLE_LEAF_CENTER_TOL_PX, DOOR_DOUBLE_LEAF_GAP_PX, DOOR_DOUBLE_LEAF_OVERLAP_PX,
    DOOR_FALLBACK_CONFIDENCE, DOOR_HU_FAR_PENALTY, DOOR_HU_PLAUSIBLE_BOOST, DOOR_HU_THRESHOLD_FAR,
    DOOR_HU_THRESHOLD_VERIFIED, DOOR_HU_VERIFIED_BOOST, DOOR_LABEL_PATTERN, DOOR_LABEL_SEARCH_RADIUS_PX,
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_RADIUS_RATIO_TOL, DOOR_THRESHOLD_CONFIDENCE_BOOST,
    DOOR_THRESHOLD_ENDPOINT_TOL_PX, DOOR_THRESHOLD_PARALLEL_TOL_DEG, DOOR_V2_BRIDGE_BUFFER_PX,
    DOOR_V2_OPENING_CLEAR_BOOST, DOOR_V2_OPENING_OBSTRUCTED_PENALTY,
)


def _check_opening_clear(
    endpoints: list[tuple[float, float]],
    line_paths: list[PathPrimitive],
    exclude_indices: set[int],
    buffer_px: float = DOOR_V2_BRIDGE_BUFFER_PX,
) -> str:
    """Check if the door opening (bridge between arc endpoints) is free of crossing lines.

    Implements the Wall Break Condition from v2 spec: creates a bridge line between
    the two arc attachment points and checks whether any non-assembly line segment
    both (a) comes within buffer_px of the bridge AND (b) has its midpoint projected
    within the interior span (5%–95%) of the bridge length.

    Returns 'clear' (empty opening → door), 'obstructed' (sill/glass lines present →
    likely casement window), or 'unknown' (insufficient endpoint data).
    """
    if len(endpoints) < 2:
        return "unknown"
    a, b = endpoints[0], endpoints[1]
    bridge_len = _distance(a, b)
    if bridge_len < 1e-6:
        return "unknown"
    ux = (b[0] - a[0]) / bridge_len
    uy = (b[1] - a[1]) / bridge_len
    interior_lo = 0.05 * bridge_len
    interior_hi = 0.95 * bridge_len
    for path in line_paths:
        if path.path_index in exclude_indices:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        if _segments_min_distance(a, b, p1, p2) > buffer_px:
            continue
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        t = (mid[0] - a[0]) * ux + (mid[1] - a[1]) * uy
        if interior_lo <= t <= interior_hi:
            return "obstructed"
    return "clear"




def _nearest_pair_distance(
    a_points: list[tuple[float, float]],
    b_points: list[tuple[float, float]],
) -> float:
    if not a_points or not b_points:
        return float("inf")
    return min(_distance(a, b) for a in a_points for b in b_points)


def _door_fallback_candidate(
    candidate_id: str,
    method: str,
    bbox: BBox,
    nearby_label: str | None,
    layer: str | None,
    layer_hint: bool,
    evidence: dict,
    confidence: float | None = None,
) -> Candidate:
    merged_evidence = dict(evidence)
    merged_evidence.update({
        "method": method,
        "nearby_label": nearby_label,
        "layer": layer,
        "layer_hint": layer_hint,
    })
    return Candidate(
        candidate_id=candidate_id,
        entity_type="door",
        bbox=bbox,
        confidence=round(confidence if confidence is not None else DOOR_FALLBACK_CONFIDENCE, 3),
        evidence=merged_evidence,
    )


def _component_indices(candidate: Candidate) -> set[int]:
    raw = candidate.evidence.get("component_path_indices")
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for item in raw:
        if isinstance(item, int):
            out.add(item)
    return out


def _dedupe_door_components(candidates: list[Candidate]) -> list[Candidate]:
    """Prefer the strongest door when two candidates use the same primitives."""
    if not candidates:
        return candidates

    non_doors = [c for c in candidates if c.entity_type != "door"]
    door_candidates = [c for c in candidates if c.entity_type == "door"]
    group = sorted(
        door_candidates,
        key=lambda c: (
            c.confidence,
            1 if c.evidence.get("method") == "door_assembly" else 0,
            _bbox_area(c.bbox),
        ),
        reverse=True,
    )
    kept: list[Candidate] = []
    used_components: set[int] = set()
    for candidate in group:
        components = _component_indices(candidate)
        if components and components.intersection(used_components):
            continue
        kept.append(candidate)
        used_components.update(components)

    return non_doors + kept


def _find_threshold_line(
    line_paths: list[PathPrimitive],
    leaf: _DoorLeaf,
    assembly_bbox: BBox,
    exclude_indices: set[int],
) -> dict | None:
    """Find an entrance-door threshold/sill line parallel to the leaf long axis.

    The threshold runs from one wall jamb to the other (along the closed-door
    direction at the floor), so its endpoints sit near the two corners of one of
    the leaf's long edges. Matching against corner pairs (not long-axis midpoints)
    keeps the fixed endpoint tolerance robust regardless of leaf thickness.

    Returns ``{"path_index": int}`` on match, or ``None``.
    """
    x0, y0, x1, y1 = leaf.bbox
    w = x1 - x0
    h = y1 - y0
    if w >= h:
        long_axis_deg = 0.0
        corner_pairs = [
            ((x0, y0), (x1, y0)),  # one long edge
            ((x0, y1), (x1, y1)),  # the other long edge
        ]
    else:
        long_axis_deg = 90.0
        corner_pairs = [
            ((x0, y0), (x0, y1)),
            ((x1, y0), (x1, y1)),
        ]

    search_zone = _bbox_expanded(assembly_bbox, DOOR_THRESHOLD_ENDPOINT_TOL_PX)
    tol = DOOR_THRESHOLD_ENDPOINT_TOL_PX

    best: tuple[float, dict] | None = None  # (summed_endpoint_dist, payload)
    for path in line_paths:
        if path.path_index in exclude_indices:
            continue
        if not _bboxes_overlap(path.bbox, search_zone):
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        if _angle_diff_mod180(_line_angle_deg(p1, p2), long_axis_deg) > DOOR_THRESHOLD_PARALLEL_TOL_DEG:
            continue
        for c_a, c_b in corner_pairs:
            d_aa = _distance(p1, c_a) + _distance(p2, c_b)
            d_ab = _distance(p1, c_b) + _distance(p2, c_a)
            d_pair = min(d_aa, d_ab)
            # Each individual endpoint must be within tolerance.
            ok_aa = _distance(p1, c_a) <= tol and _distance(p2, c_b) <= tol
            ok_ab = _distance(p1, c_b) <= tol and _distance(p2, c_a) <= tol
            if not (ok_aa or ok_ab):
                continue
            payload = {"path_index": path.path_index}
            if best is None or d_pair < best[0]:
                best = (d_pair, payload)
    return best[1] if best is not None else None



def _pair_door_assemblies(
    swings: list[_DoorSwing],
    leaves: list[_DoorLeaf],
    text_spans: list[TextSpan],
    paths: list[PathPrimitive],
    collector: DebugTraceCollector | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    used_swings: set[int] = set()
    used_leaves: set[int] = set()
    cand_idx = 0
    line_paths = [p for p in paths if p.item_type == "l"]

    potential_pairs: list[tuple[float, float, int, int]] = []
    for swing_idx, swing in enumerate(swings):
        for leaf_idx, leaf in enumerate(leaves):
            connection_dist = _nearest_pair_distance(swing.pairing_points, leaf.corners)
            if connection_dist > DOOR_ASSEMBLY_CONNECT_TOL_PX:
                continue
            if swing.radius <= 1e-6:
                if collector and swing.debug_id and leaf.debug_id:
                    collector.record_pairing_attempt(
                        swing.debug_id, leaf.debug_id,
                        connection_dist, DOOR_ASSEMBLY_CONNECT_TOL_PX,
                        0.0, DOOR_LEAF_RADIUS_RATIO_TOL,
                        "rejected", "zero_radius",
                    )
                continue
            radius_ratio = abs(leaf.length - swing.radius) / swing.radius
            if radius_ratio > DOOR_LEAF_RADIUS_RATIO_TOL:
                if collector and swing.debug_id and leaf.debug_id:
                    collector.record_pairing_attempt(
                        swing.debug_id, leaf.debug_id,
                        connection_dist, DOOR_ASSEMBLY_CONNECT_TOL_PX,
                        radius_ratio, DOOR_LEAF_RADIUS_RATIO_TOL,
                        "rejected", "radius_ratio_mismatch",
                    )
                continue
            potential_pairs.append((connection_dist, radius_ratio, swing_idx, leaf_idx))

    for connection_dist, radius_ratio, swing_idx, leaf_idx in sorted(potential_pairs):
        swing = swings[swing_idx]
        leaf = leaves[leaf_idx]
        if swing_idx in used_swings or leaf_idx in used_leaves:
            if collector and swing.debug_id and leaf.debug_id:
                collector.record_pairing_attempt(
                    swing.debug_id, leaf.debug_id,
                    connection_dist, DOOR_ASSEMBLY_CONNECT_TOL_PX,
                    radius_ratio, DOOR_LEAF_RADIUS_RATIO_TOL,
                    "rejected", "already_paired",
                )
            continue

        bbox = _bbox_union(swing.bbox, leaf.bbox)
        nearby_label = _find_nearby_label(bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        layer_hint = swing.layer_hint or leaf.layer_hint

        # Base component indices first — _find_threshold_line needs them for exclusion
        # so a leaf side or arc segment is never mistaken for the threshold.
        component_path_indices = sorted(set(swing.component_path_indices + leaf.component_path_indices))

        threshold = _find_threshold_line(
            line_paths, leaf, bbox, set(component_path_indices)
        )

        confidence = 0.65
        label_boost = 0.20 if nearby_label else 0.0
        layer_boost = 0.40 if layer_hint else 0.0
        threshold_boost = DOOR_THRESHOLD_CONFIDENCE_BOOST if threshold is not None else 0.0
        confidence += label_boost + layer_boost + threshold_boost
        confidence = min(confidence, 0.95)
        # v2: bridge-line opening check (Wall Break Condition).
        # Garden-door halves: skip the per-half check. The "bridge" for one
        # half runs from the half's outer endpoint to the shared hinge — that
        # diagonal is NOT the doorway opening, just internal swing geometry,
        # so a wall edge along it isn't a sill. The real opening spans the
        # two OUTER endpoints (computed at merge time, not here).
        opening_check = "unknown"
        if swing.arc_endpoints and len(swing.arc_endpoints) == 2 and not swing.double_arc_partner_paths:
            opening_check = _check_opening_clear(
                swing.arc_endpoints, line_paths, set(component_path_indices),
            )
        elif swing.double_arc_partner_paths:
            opening_check = "deferred_to_merge"
        opening_boost = DOOR_V2_OPENING_CLEAR_BOOST if opening_check == "clear" else 0.0
        opening_penalty = DOOR_V2_OPENING_OBSTRUCTED_PENALTY if opening_check == "obstructed" else 0.0
        confidence += opening_boost - opening_penalty
        confidence = round(min(max(confidence, 0.0), 0.95), 3)

        if threshold is not None:
            component_path_indices = sorted(
                set(component_path_indices) | {threshold["path_index"]}
            )

        candidate_id = f"door_{cand_idx:04d}"
        evidence = {
            "method": "door_assembly",
            "assembly_type": "single",
            "arc_source": swing.source,
            "leaf_source": leaf.source,
            "arc_bbox": list(swing.bbox),
            "leaf_bbox": list(leaf.bbox),
            "connection_dist_px": round(connection_dist, 2),
            "leaf_radius_ratio": round(radius_ratio, 3),
            "component_path_indices": component_path_indices,
            "arc_path_indices": list(swing.component_path_indices),
            "nearby_label": nearby_label,
            "layer": swing.layer or leaf.layer,
            "layer_hint": layer_hint,
            "opening_check": opening_check,
        }
        if swing.double_arc_partner_paths is not None:
            evidence["double_arc_partner_paths"] = list(swing.double_arc_partner_paths)
        if threshold is not None:
            evidence["has_threshold"] = True
            evidence["door_subtype"] = "entrance"
            evidence["threshold_path_index"] = threshold["path_index"]
        evidence.update({f"arc_{k}": v for k, v in swing.evidence.items() if k not in evidence})
        evidence.update({f"leaf_{k}": v for k, v in leaf.evidence.items() if k not in evidence})

        candidates.append(Candidate(
            candidate_id=candidate_id,
            entity_type="door",
            bbox=bbox,
            confidence=confidence,
            evidence=evidence,
        ))
        if collector and swing.debug_id and leaf.debug_id:
            collector.record_pairing_attempt(
                swing.debug_id, leaf.debug_id,
                connection_dist, DOOR_ASSEMBLY_CONNECT_TOL_PX,
                radius_ratio, DOOR_LEAF_RADIUS_RATIO_TOL,
                "paired",
            )
            total_before_cap = 0.65 + label_boost + layer_boost + threshold_boost + opening_boost - opening_penalty
            collector.record_candidate(
                candidate_id, "door_assembly", confidence,
                {
                    "base": 0.65,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": layer_hint,
                    "threshold_boost": threshold_boost, "threshold_found": threshold is not None,
                    "opening_boost": opening_boost, "opening_penalty": opening_penalty,
                    "opening_check": opening_check,
                    "total_before_cap": round(total_before_cap, 4),
                    "cap_applied": total_before_cap > 0.95,
                    "total": confidence,
                },
                swing.debug_id, leaf.debug_id,
            )
        cand_idx += 1
        used_swings.add(swing_idx)
        used_leaves.add(leaf_idx)

    # v3: swing-anchored single-line leaf check.
    # For arcs that didn't pair with any rectangle leaf, look for a single line
    # whose endpoint snaps to an arc endpoint and whose length matches the arc
    # radius. This is the architecturally correct "leaf at end of curve" check
    # — and it's the common case in CAD output where the door panel is one line.
    for swing_idx, swing in enumerate(swings):
        if swing_idx in used_swings:
            continue
        exclude = set(swing.component_path_indices)
        line_leaf = _find_anchored_leaf_line(swing, line_paths, exclude)
        if line_leaf is None:
            continue

        lp1 = line_leaf["p1"]
        lp2 = line_leaf["p2"]
        lx0, ly0 = min(lp1[0], lp2[0]), min(lp1[1], lp2[1])
        lx1, ly1 = max(lp1[0], lp2[0]), max(lp1[1], lp2[1])
        if (lx1 - lx0) >= (ly1 - ly0):
            leaf_bbox: BBox = (lx0, ly0 - 0.5, lx1, ly1 + 0.5)
        else:
            leaf_bbox = (lx0 - 0.5, ly0, lx1 + 0.5, ly1)

        bbox = _bbox_union(swing.bbox, leaf_bbox)
        nearby_label = _find_nearby_label(
            bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN,
        )
        layer_hint = swing.layer_hint or _layer_hint_from_layer(
            line_leaf["layer"], DOOR_LAYER_KEYWORDS,
        )

        # Door panels are often drawn as a thin stroked rectangle — the anchored
        # line is one long edge; the parallel edge would otherwise be flagged
        # as a bridge obstruction. Find the rest of the leaf's outline so the
        # opening check ignores them.
        companion_indices = _find_leaf_companion_lines(
            line_leaf,
            line_paths,
            exclude | {line_leaf["path_index"]},
        )

        component_path_indices = sorted(
            set(swing.component_path_indices)
            | {line_leaf["path_index"]}
            | companion_indices
        )

        confidence = DOOR_ASSEMBLY_LINE_LEAF_BASE
        label_boost = 0.20 if nearby_label else 0.0
        layer_boost = 0.40 if layer_hint else 0.0
        confidence += label_boost + layer_boost
        confidence = min(confidence, 0.95)

        # See companion block in the rect-leaf branch for rationale: for
        # garden-door halves the per-half "bridge" isn't the actual opening,
        # so defer the opening check to merge time (or skip if no merge happens).
        opening_check = "unknown"
        if swing.arc_endpoints and len(swing.arc_endpoints) == 2 and not swing.double_arc_partner_paths:
            opening_check = _check_opening_clear(
                swing.arc_endpoints, line_paths, set(component_path_indices),
            )
        elif swing.double_arc_partner_paths:
            opening_check = "deferred_to_merge"
        opening_boost = DOOR_V2_OPENING_CLEAR_BOOST if opening_check == "clear" else 0.0
        opening_penalty = (
            DOOR_V2_OPENING_OBSTRUCTED_PENALTY if opening_check == "obstructed" else 0.0
        )
        confidence += opening_boost - opening_penalty
        confidence = round(min(max(confidence, 0.0), 0.95), 3)

        candidate_id = f"door_{cand_idx:04d}"
        evidence = {
            "method": "door_assembly",
            "assembly_type": "single_line_leaf",
            "arc_source": swing.source,
            "leaf_source": "anchored_line",
            "arc_bbox": list(swing.bbox),
            "leaf_bbox": list(leaf_bbox),
            "leaf_line_path_index": line_leaf["path_index"],
            "leaf_line_length_px": round(line_leaf["length"], 2),
            "leaf_line_length_ratio": round(line_leaf["length_ratio"], 4),
            "leaf_line_endpoint_dist_px": round(line_leaf["endpoint_dist"], 2),
            "leaf_companion_path_indices": sorted(companion_indices),
            "component_path_indices": component_path_indices,
            "arc_path_indices": list(swing.component_path_indices),
            "nearby_label": nearby_label,
            "layer": swing.layer or line_leaf["layer"],
            "layer_hint": layer_hint,
            "opening_check": opening_check,
        }
        if swing.double_arc_partner_paths is not None:
            evidence["double_arc_partner_paths"] = list(swing.double_arc_partner_paths)
        evidence.update(
            {f"arc_{k}": v for k, v in swing.evidence.items() if k not in evidence}
        )

        candidates.append(Candidate(
            candidate_id=candidate_id,
            entity_type="door",
            bbox=bbox,
            confidence=confidence,
            evidence=evidence,
        ))
        if collector and swing.debug_id:
            total_before_cap = (
                DOOR_ASSEMBLY_LINE_LEAF_BASE
                + label_boost + layer_boost + opening_boost - opening_penalty
            )
            collector.record_anchored_line_check(
                swing.debug_id, line_leaf["path_index"],
                line_leaf["length"], line_leaf["length_ratio"],
                line_leaf["endpoint_dist"], "found",
                candidate_id=candidate_id,
            )
            collector.record_candidate(
                candidate_id, "door_assembly", confidence,
                {
                    "base": DOOR_ASSEMBLY_LINE_LEAF_BASE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": layer_hint,
                    "opening_boost": opening_boost, "opening_penalty": opening_penalty,
                    "opening_check": opening_check,
                    "leaf_line_length_ratio": round(line_leaf["length_ratio"], 4),
                    "leaf_line_endpoint_dist_px": round(line_leaf["endpoint_dist"], 2),
                    "total_before_cap": round(total_before_cap, 4),
                    "cap_applied": total_before_cap > 0.95,
                    "total": confidence,
                },
                swing.debug_id, None,
            )
        cand_idx += 1
        used_swings.add(swing_idx)

    for swing_idx, swing in enumerate(swings):
        if swing_idx in used_swings:
            continue
        nearby_label = _find_nearby_label(swing.bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        evidence = dict(swing.evidence)
        evidence["component_path_indices"] = list(swing.component_path_indices)

        # v2: Hu Moments shape verification for arc_fallback candidates.
        # Only meaningful for polyline arcs (11 segments ≈ quarter-circle shape);
        # native curve arcs are a single Bézier and would rasterize to one line.
        arc_paths = (
            [p for p in paths if p.path_index in set(swing.component_path_indices)]
            if swing.source == "polyline_arc" else []
        )
        hu_dist = _compute_hu_distance(arc_paths)
        arc_conf = DOOR_FALLBACK_CONFIDENCE
        hu_boost = 0.0
        hu_penalty = 0.0
        if hu_dist is not None:
            evidence["hu_distance"] = round(hu_dist, 4)
            if hu_dist < DOOR_HU_THRESHOLD_VERIFIED:
                hu_boost = DOOR_HU_VERIFIED_BOOST
            elif hu_dist < DOOR_HU_THRESHOLD_FAR:
                hu_boost = DOOR_HU_PLAUSIBLE_BOOST
            else:
                hu_penalty = DOOR_HU_FAR_PENALTY
            arc_conf += hu_boost - hu_penalty
            # Cap below OFFLINE_MIN_CONFIDENCE["door"] so arc-only candidates
            # cannot promote without explicit Gemini corroboration. Shape match
            # alone (Hu Moments) is informational, not promotion-determining.
            arc_conf = round(min(max(arc_conf, 0.0), DOOR_ARC_FALLBACK_MAX), 3)

        candidate_id = f"door_{cand_idx:04d}"
        candidates.append(_door_fallback_candidate(
            candidate_id,
            "arc_fallback",
            swing.bbox,
            nearby_label,
            swing.layer,
            swing.layer_hint,
            evidence,
            confidence=arc_conf,
        ))
        if collector and swing.debug_id:
            label_boost = 0.20 if nearby_label else 0.0
            layer_boost = 0.40 if swing.layer_hint else 0.0
            hu_result = (
                "verified" if hu_dist is not None and hu_dist < DOOR_HU_THRESHOLD_VERIFIED else
                "plausible" if hu_dist is not None and hu_dist < DOOR_HU_THRESHOLD_FAR else
                "far" if hu_dist is not None else "unavailable"
            )
            collector.record_hu_eval(
                swing.debug_id, hu_dist,
                DOOR_HU_THRESHOLD_VERIFIED, DOOR_HU_THRESHOLD_FAR,
                hu_result, hu_boost - hu_penalty,
                DOOR_FALLBACK_CONFIDENCE, arc_conf,
            )
            collector.record_candidate(
                candidate_id, "arc_fallback", arc_conf,
                {
                    "base": DOOR_FALLBACK_CONFIDENCE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": swing.layer_hint,
                    "hu_boost": hu_boost, "hu_penalty": hu_penalty,
                    "hu_distance": round(hu_dist, 4) if hu_dist is not None else None,
                    "total": arc_conf,
                },
                swing.debug_id, None,
            )
        cand_idx += 1

    for leaf_idx, leaf in enumerate(leaves):
        if leaf_idx in used_leaves:
            continue
        nearby_label = _find_nearby_label(leaf.bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        evidence = dict(leaf.evidence)
        evidence["component_path_indices"] = list(leaf.component_path_indices)
        candidate_id = f"door_{cand_idx:04d}"
        candidates.append(_door_fallback_candidate(
            candidate_id,
            "leaf_fallback",
            leaf.bbox,
            nearby_label,
            leaf.layer,
            leaf.layer_hint,
            evidence,
        ))
        if collector and leaf.debug_id:
            label_boost = 0.20 if nearby_label else 0.0
            layer_boost = 0.40 if leaf.layer_hint else 0.0
            leaf_conf = DOOR_FALLBACK_CONFIDENCE + label_boost + layer_boost
            collector.record_candidate(
                candidate_id, "leaf_fallback", round(min(leaf_conf, 0.95), 3),
                {
                    "base": DOOR_FALLBACK_CONFIDENCE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": leaf.layer_hint,
                    "total": round(min(leaf_conf, 0.95), 3),
                },
                None, leaf.debug_id,
            )
        cand_idx += 1

    return _dedupe_door_components(candidates)


def _safe_bbox(val: object) -> BBox | None:
    """Parse an evidence bbox value defensively; return None on any invalid shape."""
    if val is None or isinstance(val, (str, bytes)):
        return None
    try:
        seq = list(val)
    except TypeError:
        return None
    if len(seq) != 4:
        return None
    try:
        return (float(seq[0]), float(seq[1]), float(seq[2]), float(seq[3]))
    except (TypeError, ValueError):
        return None


def _merge_double_door_assemblies(candidates: list[Candidate]) -> list[Candidate]:
    """Merge pairs of adjacent single-door assemblies into double-swing candidates.

    Only fully assembled doors (method=door_assembly) participate. Pairing is
    one-to-one — once a candidate joins a double door it cannot merge again.

    Two distinct double-door layouts are handled:
    - **french**: leaves are collinear with a small gap; doors meet in the
      middle of the opening (the classic French-door pattern).
    - **garden**: leaves are at opposite outer ends of the opening; swing
      arcs share a hinge in the middle (a 2-leaf simple chain with a single
      ~180° tangent break — see _split_double_arc). Identified by matching
      ``double_arc_partner_paths`` and given priority over the leaf-collinear
      rule because the partnership is unambiguous.
    """
    import re as _re
    assemblies = [
        (i, c) for i, c in enumerate(candidates)
        if c.entity_type == "door" and c.evidence.get("method") == "door_assembly"
    ]

    scored_pairs: list[tuple[float, int, int, str]] = []  # (sort_key, idx_i, idx_j, layout)

    # Garden-door pass: match by double_arc_partner_paths. The polyline-arc
    # detector produces TWO half-arc candidates from one BFS double-arc; each
    # carries the OTHER half's arc paths. A genuine partnership is when each
    # half's arc paths equal the other's partner_paths.
    for (pi, ci), (pj, cj) in combinations(assemblies, 2):
        partner_i = ci.evidence.get("double_arc_partner_paths")
        partner_j = cj.evidence.get("double_arc_partner_paths")
        if not partner_i or not partner_j:
            continue
        arc_i_paths = ci.evidence.get("arc_path_indices") or []
        arc_j_paths = cj.evidence.get("arc_path_indices") or []
        if set(arc_i_paths) == set(partner_j) and set(arc_j_paths) == set(partner_i):
            # Sort key 0.0 — garden-door pairs win over any french-pair score (>= 0.0).
            scored_pairs.append((0.0, pi, pj, "garden"))

    for (pi, ci), (pj, cj) in combinations(assemblies, 2):
        arc_i = _safe_bbox(ci.evidence.get("arc_bbox"))
        arc_j = _safe_bbox(cj.evidence.get("arc_bbox"))
        leaf_i = _safe_bbox(ci.evidence.get("leaf_bbox"))
        leaf_j = _safe_bbox(cj.evidence.get("leaf_bbox"))
        if arc_i is None or arc_j is None or leaf_i is None or leaf_j is None:
            continue

        ri = max(_bbox_width(arc_i), _bbox_height(arc_i))
        rj = max(_bbox_width(arc_j), _bbox_height(arc_j))
        if ri <= 0 or rj <= 0:
            continue
        if abs(ri - rj) / max(ri, rj) > DOOR_LEAF_RADIUS_RATIO_TOL:
            continue

        # Leaf orientation: horizontal when width >= height
        wi, hi = _bbox_width(leaf_i), _bbox_height(leaf_i)
        wj, hj = _bbox_width(leaf_j), _bbox_height(leaf_j)
        horiz_i = wi >= hi
        horiz_j = wj >= hj
        if horiz_i != horiz_j:
            continue

        if horiz_i:
            # Collinear centerlines along y
            cy_i = (leaf_i[1] + leaf_i[3]) / 2
            cy_j = (leaf_j[1] + leaf_j[3]) / 2
            if abs(cy_i - cy_j) > DOOR_DOUBLE_LEAF_CENTER_TOL_PX:
                continue
            # Signed gap along x: positive = gap, negative = overlap
            signed_gap = max(leaf_i[0], leaf_j[0]) - min(leaf_i[2], leaf_j[2])
        else:
            # Collinear centerlines along x
            cx_i = (leaf_i[0] + leaf_i[2]) / 2
            cx_j = (leaf_j[0] + leaf_j[2]) / 2
            if abs(cx_i - cx_j) > DOOR_DOUBLE_LEAF_CENTER_TOL_PX:
                continue
            # Signed gap along y
            signed_gap = max(leaf_i[1], leaf_j[1]) - min(leaf_i[3], leaf_j[3])

        if not (-DOOR_DOUBLE_LEAF_OVERLAP_PX <= signed_gap <= DOOR_DOUBLE_LEAF_GAP_PX):
            continue

        # +1.0 offset so any french score sorts after every garden pair (sort_key=0.0).
        scored_pairs.append((1.0 + abs(signed_gap), pi, pj, "french"))

    if not scored_pairs:
        return candidates

    # Greedy one-to-one match: tightest leaf fit wins; each candidate used at most once
    scored_pairs.sort()
    used: set[int] = set()
    merges: list[tuple[int, int, str]] = []
    for _, pi, pj, layout in scored_pairs:
        if pi in used or pj in used:
            continue
        merges.append((pi, pj, layout))
        used.add(pi)
        used.add(pj)

    if not merges:
        return candidates

    # Mint new IDs starting after the current maximum numeric door suffix
    _id_re = _re.compile(r"door_(\d+)$")
    max_num = -1
    for c in candidates:
        m = _id_re.match(c.candidate_id)
        if m:
            max_num = max(max_num, int(m.group(1)))
    next_num = max_num + 1

    by_idx = {i: c for i, c in enumerate(candidates)}
    merged_candidates: list[Candidate] = []

    for pi, pj, layout in merges:
        ci = by_idx[pi]
        cj = by_idx[pj]

        arc_i = _safe_bbox(ci.evidence.get("arc_bbox"))
        arc_j = _safe_bbox(cj.evidence.get("arc_bbox"))
        leaf_i = _safe_bbox(ci.evidence.get("leaf_bbox"))
        leaf_j = _safe_bbox(cj.evidence.get("leaf_bbox"))

        merged_bbox = _bbox_union(ci.bbox, cj.bbox)
        confidence = min(0.95, max(ci.confidence, cj.confidence) + 0.05)

        ci_indices = set(ci.evidence.get("component_path_indices") or [])
        cj_indices = set(cj.evidence.get("component_path_indices") or [])

        evidence: dict = {
            "method": "door_assembly",
            "assembly_type": "double_swing",
            "swing_layout": layout,
            "component_path_indices": sorted(ci_indices | cj_indices),
        }

        # Entrance-door fields: only include when truthy / non-None
        _ht = ci.evidence.get("has_threshold") or cj.evidence.get("has_threshold")
        if _ht:
            evidence["has_threshold"] = True
        _ds = ci.evidence.get("door_subtype") or cj.evidence.get("door_subtype")
        if _ds:
            evidence["door_subtype"] = _ds
        _tpi = (
            ci.evidence["threshold_path_index"]
            if ci.evidence.get("threshold_path_index") is not None
            else cj.evidence.get("threshold_path_index")
        )
        if _tpi is not None:
            evidence["threshold_path_index"] = _tpi

        nearby_a = ci.evidence.get("nearby_label")
        nearby_b = cj.evidence.get("nearby_label")
        evidence["nearby_label"] = nearby_a or nearby_b
        evidence["nearby_labels"] = [l for l in [nearby_a, nearby_b] if l]

        evidence["layer_hint"] = ci.evidence.get("layer_hint") or cj.evidence.get("layer_hint")
        evidence["arc_bbox_a"] = list(arc_i) if arc_i else None
        evidence["arc_bbox_b"] = list(arc_j) if arc_j else None
        evidence["leaf_bbox_a"] = list(leaf_i) if leaf_i else None
        evidence["leaf_bbox_b"] = list(leaf_j) if leaf_j else None

        merged_candidates.append(Candidate(
            candidate_id=f"door_{next_num:04d}",
            entity_type="door",
            bbox=merged_bbox,
            confidence=round(confidence, 3),
            evidence=evidence,
        ))
        next_num += 1

    # Preserve unmerged candidates in original order
    result = [c for i, c in enumerate(candidates) if i not in used]
    result.extend(merged_candidates)
    return result
