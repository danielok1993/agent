from __future__ import annotations

import math

from models import Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.geometry import (
    _angle_diff_mod180, _distance, _is_line_path, _line_angle_deg,
    _point_to_segment_distance,
)
from detection.labels import _find_nearby_label
from detection.layers import _layer_hint_from_layer
from detection.walls import _is_background_fill
from detection.doors.sliding import _SlidePanel, _collect_slide_panels, _corners_bbox
from detection.doors.constants import (
    DOOR_FOLD_ANGLE_MAX_DEG, DOOR_FOLD_ANGLE_MIN_DEG, DOOR_FOLD_ASSEMBLY_BASE,
    DOOR_FOLD_HINGE_TOL_PX, DOOR_FOLD_JAMB_ANCHOR_TOL_PX,
    DOOR_FOLD_JAMB_AXIS_TOL_DEG, DOOR_FOLD_JAMB_LINE_MIN_LEN_PX,
    DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN, DOOR_FOLD_LEAF_LINE_OVERLAP_MIN,
    DOOR_FOLD_LEAF_LINE_SEP_MAX_PX, DOOR_FOLD_LEAF_LINE_SEP_MIN_PX,
    DOOR_FOLD_LENGTH_RATIO_TOL, DOOR_FOLD_MIN_CHAIN_LEAVES,
    DOOR_FOLD_OPEN_ANGLE_MAX_DEG, DOOR_FOLD_OPEN_ANGLE_MIN_DEG,
    DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX, DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG,
    DOOR_FOLD_STACK_MIRROR_TOL_DEG, DOOR_FOLD_STACK_PERP_EXTENT_MAX,
    DOOR_FOLD_STACK_SPAN_RATIO_TOL, DOOR_LABEL_PATTERN, DOOR_LABEL_SEARCH_RADIUS_PX,
    DOOR_LAYER_KEYWORDS, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_SLIDE_AXIS_TOL_DEG, DOOR_SLIDE_PANEL_MERGE_TOL_PX,
    DoorGates,
)


def _absorb_hinged_white_rings(
    panels: list[_SlidePanel], paths: list[PathPrimitive]
) -> None:
    """Mark stroked-qu panels white when their coincident fill-ring edges exist.

    Folding leaves are drawn in the same Vectorworks joinery signature as
    sliding panels (white fill ring + stroked qu outline), but hinged leaves
    share ring VERTICES, so `_white_ring_rects` rejects them: the shared hinge
    vertex has degree 4 and the leaves' rings BFS-merge into one non-loop
    component. The leaves therefore arrive from `_collect_slide_panels` as
    stroked-qu panels only. A white `l` segment whose both endpoints land on a
    panel's fitted corners IS that panel's fill-ring edge — absorb its path
    index (so downstream component dedupe sees both representations) and mark
    the panel white once a ring's worth of edges (4+) matched.
    """
    tol = DOOR_SLIDE_PANEL_MERGE_TOL_PX
    white_segs: list[tuple[int, tuple[float, float], tuple[float, float]]] = []
    for path in paths:
        if not _is_background_fill(path.fill):
            continue
        ok, p1, p2 = _is_line_path(path)
        if ok and _distance(p1, p2) > 1.0:
            white_segs.append((path.path_index, p1, p2))

    for panel in panels:
        if panel.white:
            continue
        absorbed = [
            idx
            for idx, p1, p2 in white_segs
            if min(_distance(p1, c) for c in panel.corners) <= tol
            and min(_distance(p2, c) for c in panel.corners) <= tol
        ]
        if len(absorbed) >= 4:
            panel.white = True
            panel.path_indices = sorted(set(panel.path_indices) | set(absorbed))
            panel.sources = sorted(set(panel.sources) | {"white_ring"})


def _fold_edges(
    panels: list[_SlidePanel],
) -> dict[tuple[int, int], dict]:
    """Hinge edges between leaf panels: equal lengths, corner contact, and a
    shallow-but-nonzero fold angle between the long axes. Near-parallel panels
    (sliding pairs, wall plies) and near-perpendicular corner joinery both
    fall outside the fold-angle window."""
    edges: dict[tuple[int, int], dict] = {}
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            a, b = panels[i], panels[j]
            delta = _angle_diff_mod180(a.axis_deg, b.axis_deg)
            if not (DOOR_FOLD_ANGLE_MIN_DEG <= delta <= DOOR_FOLD_ANGLE_MAX_DEG):
                continue
            if abs(a.length - b.length) / max(a.length, b.length) > DOOR_FOLD_LENGTH_RATIO_TOL:
                continue
            hinge = min(
                _distance(ca, cb) for ca in a.corners for cb in b.corners
            )
            if hinge > DOOR_FOLD_HINGE_TOL_PX:
                continue
            edges[(i, j)] = {
                "fold_angle_deg": round(delta, 1),
                "hinge_dist_px": round(hinge, 2),
            }
    return edges


def _fold_groups(
    panels: list[_SlidePanel], edges: dict[tuple[int, int], dict]
) -> list[dict]:
    """Connected components of the hinge graph, with per-group stats."""
    adjacency: dict[int, set[int]] = {i: set() for i in range(len(panels))}
    for (i, j) in edges:
        adjacency[i].add(j)
        adjacency[j].add(i)

    groups: list[dict] = []
    seen: set[int] = set()
    for start in range(len(panels)):
        if start in seen or not adjacency[start]:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            idx = stack.pop()
            members.append(idx)
            for other in adjacency[idx]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        members.sort()
        corners = [c for m in members for c in panels[m].corners]
        # Mean axis via unit-vector sum on doubled angles (axes are mod 180).
        sx = sum(math.cos(2 * math.radians(panels[m].axis_deg)) for m in members)
        sy = sum(math.sin(2 * math.radians(panels[m].axis_deg)) for m in members)
        groups.append({
            "members": members,
            "corners": corners,
            "centroid": (
                sum(p[0] for p in corners) / len(corners),
                sum(p[1] for p in corners) / len(corners),
            ),
            "sum_len": sum(panels[m].length for m in members),
            "mean_len": sum(panels[m].length for m in members) / len(members),
            "mean_axis_deg": (math.degrees(math.atan2(sy, sx)) / 2) % 180.0,
            "fold_angles": [
                edges[key]["fold_angle_deg"]
                for key in edges
                if key[0] in members and key[1] in members
            ],
        })
    return groups


def _pair_parked_stacks(groups: list[dict]) -> list[tuple[int, int, dict]]:
    """Pair two 2-leaf V-stacks parked at opposite jambs of one opening.

    The physical gate is the span law: when the door closes, the leaves unfold
    to cover the opening, so the outer span between the stacks along the
    opening axis must equal the summed leaf lengths. The stacks must also fold
    off the same wall plane (mean leaf angles mirror about the opening axis)
    and each stack must stay compact across that axis (a folded stack projects
    at most ~one leaf length perpendicular to the opening).
    """
    scored: list[tuple[float, int, int, dict]] = []
    for gi in range(len(groups)):
        for gj in range(gi + 1, len(groups)):
            g1, g2 = groups[gi], groups[gj]
            if len(g1["members"]) != 2 or len(g2["members"]) != 2:
                continue
            mean_len = (g1["mean_len"] + g2["mean_len"]) / 2
            if (
                abs(g1["mean_len"] - g2["mean_len"]) / max(g1["mean_len"], g2["mean_len"])
                > DOOR_FOLD_LENGTH_RATIO_TOL
            ):
                continue
            dx = g2["centroid"][0] - g1["centroid"][0]
            dy = g2["centroid"][1] - g1["centroid"][1]
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                continue
            ux, uy = dx / dist, dy / dist
            axis_deg = math.degrees(math.atan2(dy, dx)) % 180.0

            projs = [p[0] * ux + p[1] * uy for p in g1["corners"] + g2["corners"]]
            span = max(projs) - min(projs)
            sum_len = g1["sum_len"] + g2["sum_len"]
            span_ratio = abs(span - sum_len) / sum_len
            if span_ratio > DOOR_FOLD_STACK_SPAN_RATIO_TOL:
                continue

            mirror_dev = _angle_diff_mod180(
                g1["mean_axis_deg"] + g2["mean_axis_deg"], 2 * axis_deg,
            )
            if mirror_dev > DOOR_FOLD_STACK_MIRROR_TOL_DEG:
                continue

            perp_ok = True
            for g in (g1, g2):
                perps = [-p[0] * uy + p[1] * ux for p in g["corners"]]
                if max(perps) - min(perps) > DOOR_FOLD_STACK_PERP_EXTENT_MAX * mean_len:
                    perp_ok = False
            if not perp_ok:
                continue

            metrics = {
                "opening_span_px": round(span, 1),
                "leaf_run_px": round(sum_len, 1),
                "span_ratio_dev": round(span_ratio, 3),
                "mirror_dev_deg": round(mirror_dev, 1),
            }
            scored.append((dist, gi, gj, metrics))

    pairs: list[tuple[int, int, dict]] = []
    consumed: set[int] = set()
    for _, gi, gj, metrics in sorted(scored, key=lambda t: t[0]):
        if gi in consumed or gj in consumed:
            continue
        consumed.update((gi, gj))
        pairs.append((gi, gj, metrics))
    return pairs


def _mean_axis_deg(angles: list[float]) -> float:
    """Circular mean of mod-180 axes via unit-vector sum on doubled angles."""
    sx = sum(math.cos(2 * math.radians(a)) for a in angles)
    sy = sum(math.sin(2 * math.radians(a)) for a in angles)
    return (math.degrees(math.atan2(sy, sx)) / 2) % 180.0


def _double_line_leaves(line_paths: list[PathPrimitive]) -> list[_SlidePanel]:
    """Thin double-line leaves: two near-parallel OBLIQUE lines of near-equal
    length a hair apart — the fill-less drawing of one folding leaf (no white
    ring, no qu outline). Corners are ordered line-major: [a1, a2, b1, b2].
    Oblique-only keeps the page's bulk axis-aligned linework out of the pair
    search; a half-open V off a straight wall is never axis-aligned."""
    lines = []
    for path in line_paths:
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        length = _distance(p1, p2)
        if not (DOOR_MIN_SIZE_PX * 0.7 <= length <= DOOR_MAX_SIZE_PX):
            continue
        angle = _line_angle_deg(p1, p2) % 180.0
        if min(angle % 90.0, 90.0 - angle % 90.0) < DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG:
            continue
        lines.append((path.path_index, p1, p2, length, angle, path.layer))

    scored: list[tuple[float, int, int]] = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            _, pa1, pa2, la, aa, _la_ = lines[i]
            _, pb1, pb2, lb, ab, _lb_ = lines[j]
            if _angle_diff_mod180(aa, ab) > DOOR_SLIDE_AXIS_TOL_DEG:
                continue
            if min(la, lb) / max(la, lb) < DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN:
                continue
            mid_a = ((pa1[0] + pa2[0]) / 2, (pa1[1] + pa2[1]) / 2)
            sep = _point_to_segment_distance(mid_a, pb1, pb2)
            if not (DOOR_FOLD_LEAF_LINE_SEP_MIN_PX <= sep <= DOOR_FOLD_LEAF_LINE_SEP_MAX_PX):
                continue
            axis = _mean_axis_deg([aa, ab])
            theta = math.radians(axis)
            ux, uy = math.cos(theta), math.sin(theta)
            ta = sorted(p[0] * ux + p[1] * uy for p in (pa1, pa2))
            tb = sorted(p[0] * ux + p[1] * uy for p in (pb1, pb2))
            overlap = min(ta[1], tb[1]) - max(ta[0], tb[0])
            if overlap < DOOR_FOLD_LEAF_LINE_OVERLAP_MIN * min(la, lb):
                continue
            scored.append((sep, i, j))

    leaves: list[_SlidePanel] = []
    used: set[int] = set()
    for sep, i, j in sorted(scored, key=lambda t: t[0]):
        if i in used or j in used:
            continue
        used.update((i, j))
        idx_a, pa1, pa2, la, aa, layer_a = lines[i]
        idx_b, pb1, pb2, lb, ab, layer_b = lines[j]
        corners = [pa1, pa2, pb1, pb2]
        layer = layer_a or layer_b
        leaves.append(_SlidePanel(
            center=(
                sum(p[0] for p in corners) / 4,
                sum(p[1] for p in corners) / 4,
            ),
            length=(la + lb) / 2,
            thickness=sep,
            axis_deg=_mean_axis_deg([aa, ab]),
            corners=corners,
            bbox=_corners_bbox(corners),
            path_indices=sorted((idx_a, idx_b)),
            sources=["line_pair"],
            white=False,
            layer=layer,
            layer_hint=_layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS),
        ))
    return leaves


def _leaf_tip(leaf: _SlidePanel, hinge: tuple[float, float]) -> tuple[float, float]:
    """Midpoint of the leaf's short end farthest from the hinge (corners are
    line-major: [a1, a2, b1, b2])."""
    far_a = max(leaf.corners[0:2], key=lambda c: _distance(c, hinge))
    far_b = max(leaf.corners[2:4], key=lambda c: _distance(c, hinge))
    return ((far_a[0] + far_b[0]) / 2, (far_a[1] + far_b[1]) / 2)


def _open_v_match(
    a: _SlidePanel,
    b: _SlidePanel,
    line_paths: list[PathPrimitive],
) -> tuple[dict, list[tuple[float, float]]] | None:
    """open_v pattern: a lone bifold drawn half-open as a wide V. The physical
    gates that replace the white joinery signature: the leaves mirror about
    the tip-to-tip axis, at least one tip anchors on wall-line jamb ENDS
    running along that axis, and the jamb-to-jamb opening span obeys the span
    law (≈ Σ leaf lengths). Orthogonal corner joinery dies on the fold-angle
    ceiling (<90°) and, failing that, on the jamb/span gates: walls run along
    the strips at an L-corner, never along the diagonal tip axis."""
    delta = _angle_diff_mod180(a.axis_deg, b.axis_deg)
    if not (DOOR_FOLD_OPEN_ANGLE_MIN_DEG <= delta <= DOOR_FOLD_OPEN_ANGLE_MAX_DEG):
        return None
    if abs(a.length - b.length) / max(a.length, b.length) > DOOR_FOLD_LENGTH_RATIO_TOL:
        return None
    hinge_dist, ca, cb = min(
        (_distance(pa, pb), pa, pb) for pa in a.corners for pb in b.corners
    )
    if hinge_dist > DOOR_FOLD_HINGE_TOL_PX:
        return None
    hinge = ((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2)
    tips = (_leaf_tip(a, hinge), _leaf_tip(b, hinge))
    tip_span = _distance(tips[0], tips[1])
    mean_len = (a.length + b.length) / 2
    if tip_span < 0.5 * mean_len:
        return None  # tips together = drawn closed; that is chain territory
    axis_deg = _line_angle_deg(tips[0], tips[1])
    if _angle_diff_mod180(a.axis_deg + b.axis_deg, 2 * axis_deg) > DOOR_FOLD_STACK_MIRROR_TOL_DEG:
        return None
    mirror_dev = _angle_diff_mod180(a.axis_deg + b.axis_deg, 2 * axis_deg)

    own = set(a.path_indices) | set(b.path_indices)
    corners = a.corners + b.corners

    # Jamb anchors: wall-face lines running along the tip axis whose endpoint
    # lands on a tip, with the line body running away from the opening.
    anchors: dict[int, list[tuple[float, float]]] = {0: [], 1: []}
    for path in line_paths:
        if path.path_index in own:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok or _distance(p1, p2) < DOOR_FOLD_JAMB_LINE_MIN_LEN_PX:
            continue
        if _angle_diff_mod180(_line_angle_deg(p1, p2), axis_deg) > DOOR_FOLD_JAMB_AXIS_TOL_DEG:
            continue
        for ti, tip in enumerate(tips):
            other = tips[1 - ti]
            for pe, po in ((p1, p2), (p2, p1)):
                if _distance(pe, tip) > DOOR_FOLD_JAMB_ANCHOR_TOL_PX:
                    continue
                away = (
                    (po[0] - tip[0]) * (other[0] - tip[0])
                    + (po[1] - tip[1]) * (other[1] - tip[1])
                )
                if away > 0:
                    continue
                anchors[ti].append(pe)
    anchored = [ti for ti in (0, 1) if anchors[ti]]
    if not anchored:
        return None

    ti = anchored[0]
    tip, other = tips[ti], tips[1 - ti]
    vx, vy = (other[0] - tip[0]) / tip_span, (other[1] - tip[1]) / tip_span
    if len(anchored) == 2:
        # Both tips on jambs: the V is drawn across the whole opening.
        span = tip_span
    else:
        # Far jamb: nearest linework endpoint in the corridor beyond the far
        # tip (leaf end caps sit on leaf corners and are excluded).
        span = None
        for path in line_paths:
            if path.path_index in own:
                continue
            ok, p1, p2 = _is_line_path(path)
            if not ok or _distance(p1, p2) < 4.0:
                continue
            for pe in (p1, p2):
                if min(_distance(pe, c) for c in corners) <= 3.0:
                    continue
                rx, ry = pe[0] - tip[0], pe[1] - tip[1]
                s = rx * vx + ry * vy
                lat = -rx * vy + ry * vx
                if abs(lat) > DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX:
                    continue
                if s < tip_span + 4.0:
                    continue
                if span is None or s < span:
                    span = s
        if span is None:
            return None
    leaf_run = a.length + b.length
    span_dev = abs(span - leaf_run) / leaf_run
    if span_dev > DOOR_FOLD_STACK_SPAN_RATIO_TOL:
        return None

    # The opening corridor is clear apart from the V itself and its end caps.
    crossers = 0
    for path in line_paths:
        if path.path_index in own:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        if _angle_diff_mod180(_line_angle_deg(p1, p2), axis_deg) <= 30.0:
            continue
        if all(min(_distance(pe, c) for c in corners) <= 3.0 for pe in (p1, p2)):
            continue  # the leaf end cap closing the V's outer panel
        ss, lats = [], []
        for pe in (p1, p2):
            rx, ry = pe[0] - tip[0], pe[1] - tip[1]
            ss.append(rx * vx + ry * vy)
            lats.append(-rx * vy + ry * vx)
        if max(ss) < 2.0 or min(ss) > span - 2.0:
            continue
        if min(abs(lats[0]), abs(lats[1])) > DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX:
            continue
        crossers += 1
    if crossers > 2:
        return None

    half_w = max(
        [abs(-(pe[0] - tip[0]) * vy + (pe[1] - tip[1]) * vx) for pe in anchors[ti]]
        + [2.0],
    )
    far_pt = (tip[0] + vx * span, tip[1] + vy * span)
    corridor = list(anchors[ti]) + [
        (far_pt[0] - vy * w, far_pt[1] + vx * w) for w in (-half_w, half_w)
    ]
    metrics = {
        "opening_span_px": round(span, 1),
        "leaf_run_px": round(leaf_run, 1),
        "span_ratio_dev": round(span_dev, 3),
        "mirror_dev_deg": round(mirror_dev, 1),
        "tip_span_px": round(tip_span, 1),
        "anchored_tips": len(anchored),
        "zone_crossers": crossers,
    }
    return metrics, corridor


def _detect_folding_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None,
    cand_idx: int,
    *, gates: DoorGates,
) -> tuple[list[Candidate], int]:
    """Detect arc-less folding/bifold doors. Returns (candidates, next index).

    Runs after `_detect_sliding_doors` inside `_pair_door_assemblies`. Two
    patterns over hinge-connected groups of white leaf panels:
    - chain: one group of 3+ leaves (a concertina drawn across the opening).
    - stack_pair: two 2-leaf V-groups parked at opposite jambs, paired by the
      span law (outer span ≈ Σ leaf lengths). A lone 2-leaf V is never emitted.
    Candidates carry assembly_type="folding" and their component_path_indices
    contain the panels' primitives (qu outlines + absorbed fill-ring edges) so
    `_dedupe_door_components` retires the leaf-fallback candidates the same
    rectangles produce.
    """
    panels = _collect_slide_panels(paths, gates=gates)
    _absorb_hinged_white_rings(panels, paths)
    panels = [p for p in panels if p.white]
    edges = _fold_edges(panels)
    groups = _fold_groups(panels, edges)
    candidates: list[Candidate] = []

    def mint(
        fold_style: str,
        involved: list[_SlidePanel],
        fold_angles: list[float],
        metrics: dict,
        extra_points: list[tuple[float, float]] | None = None,
    ) -> Candidate:
        nonlocal cand_idx
        bbox = _corners_bbox(
            [c for p in involved for c in p.corners] + (extra_points or []),
        )
        nearby_label = _find_nearby_label(
            bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN,
        )
        layer = next((p.layer for p in involved if p.layer), None)
        layer_hint = any(p.layer_hint for p in involved)
        label_boost = 0.20 if nearby_label else 0.0
        layer_boost = 0.40 if layer_hint else 0.0
        confidence = round(
            min(DOOR_FOLD_ASSEMBLY_BASE + label_boost + layer_boost, 0.95), 3,
        )
        fold_angles = sorted(fold_angles)
        component_path_indices = sorted({i for p in involved for i in p.path_indices})
        evidence = {
            "method": "door_assembly",
            "assembly_type": "folding",
            "fold_style": fold_style,
            "leaf_count": len(involved),
            "leaf_bboxes": [list(p.bbox) for p in involved],
            "leaf_sources": ["+".join(p.sources) for p in involved],
            "panel_length_px": round(
                sum(p.length for p in involved) / len(involved), 1,
            ),
            "fold_angles_deg": fold_angles,
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
                candidate_id, "folding_assembly", confidence,
                {
                    "base": DOOR_FOLD_ASSEMBLY_BASE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": layer_hint,
                    "fold_style": fold_style,
                    "leaf_count": len(involved),
                    "fold_angles_deg": fold_angles,
                    **metrics,
                    "total": confidence,
                },
                None, None,
            )
        return candidate

    def group_mint(fold_style: str, member_groups: list[dict], metrics: dict) -> Candidate:
        involved = [panels[m] for g in member_groups for m in g["members"]]
        fold_angles = [a for g in member_groups for a in g["fold_angles"]]
        return mint(fold_style, involved, fold_angles, metrics)

    paired: set[int] = set()
    for gi, gj, metrics in _pair_parked_stacks(groups):
        paired.update((gi, gj))
        candidates.append(group_mint("stack_pair", [groups[gi], groups[gj]], metrics))

    for idx, group in enumerate(groups):
        if idx in paired or len(group["members"]) < DOOR_FOLD_MIN_CHAIN_LEAVES:
            continue
        candidates.append(group_mint("chain", [group], {}))

    # open_v: a lone bifold drawn half-open as a wide V of stroked double-line
    # leaves (the fill-less drawing style). Its fold-angle window (40-85°) is
    # disjoint from chain/stack_pair (8-30°), so the patterns never compete.
    line_paths = [p for p in paths if p.item_type == "l"]
    leaves = _double_line_leaves(line_paths)
    for i in range(len(leaves)):
        for j in range(i + 1, len(leaves)):
            a, b = leaves[i], leaves[j]
            if a.consumed or b.consumed:
                continue
            match = _open_v_match(a, b, line_paths)
            if match is None:
                continue
            metrics, corridor = match
            a.consumed = True
            b.consumed = True
            delta = _angle_diff_mod180(a.axis_deg, b.axis_deg)
            candidates.append(
                mint("open_v", [a, b], [round(delta, 1)], metrics, corridor),
            )

    return candidates, cand_idx
