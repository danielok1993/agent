from __future__ import annotations
from collections import defaultdict
from models import BBox, PathPrimitive
from debug.trace import DebugTraceCollector
from detection.geometry import _angle_diff_mod180, _bbox_height, _bbox_width, _distance, _interval_overlap, _is_line_path, _line_angle_deg, _line_length, _projected_interval
from detection.layers import _layer_hint, _layer_hint_from_layer
from detection.doors.models import _DoorLeaf, _DoorSwing
from detection.doors.arcs import _arc_corners
from detection.doors.constants import (
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_ASPECT_MIN, DOOR_LEAF_COMPANION_OVERLAP,
    DOOR_LEAF_COMPANION_PERP_PX, DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG, DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG,
    DOOR_LEAF_LINE_AXIS_TOL_DEG, DOOR_LEAF_LINE_ENDPOINT_TOL_PX, DOOR_LEAF_LINE_LENGTH_TOL,
    DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX,
    DOOR_LINEWORK_LEAF_MAX_SEGMENTS, DOOR_LINEWORK_LEAF_MIN_SEGMENTS, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
)


def _is_door_leaf(path: PathPrimitive, collector: DebugTraceCollector | None = None) -> bool:
    """Return True for re/qu primitives shaped like a door leaf (long and thin)."""
    if path.item_type not in ("re", "qu"):
        if collector:
            collector.record_leaf_filter(path, False, "item_type_not_rect")
        return False
    w = _bbox_width(path.bbox)
    h = _bbox_height(path.bbox)
    long_side = max(w, h)
    short_side = min(w, h)
    if short_side < 1e-6:
        if collector:
            collector.record_leaf_filter(path, False, "short_side_degenerate")
        return False
    aspect = long_side / short_side
    if aspect < DOOR_LEAF_ASPECT_MIN:
        if collector:
            collector.record_leaf_filter(path, False, "aspect_ratio", aspect_ratio=aspect, size_px=long_side)
        return False
    if not (DOOR_MIN_SIZE_PX <= long_side <= DOOR_MAX_SIZE_PX):
        if collector:
            collector.record_leaf_filter(path, False, "size_out_of_range", aspect_ratio=aspect, size_px=long_side)
        return False
    if collector:
        collector.record_leaf_filter(path, True, None, aspect_ratio=aspect, size_px=long_side)
    return True


def _snap_key(point: tuple[float, float], tol: float) -> tuple[int, int]:
    return (round(point[0] / tol), round(point[1] / tol))


_LinkSeg = tuple[PathPrimitive, tuple[float, float], tuple[float, float]]


def _try_linework_leaf_clean_loop(
    component: list[int], segs: list[_LinkSeg]
) -> _DoorLeaf | None:
    """Existing clean-closed-loop linework leaf validation, extracted as a helper.

    Requires 4–8 segments, every junction degree-2 (true closed polygon), thin-rectangle
    bbox. Returns the `_DoorLeaf` or None. Preserved verbatim so split-side rectangles
    (a long edge drawn as 2 collinear segments → 5–8 perimeter primitives, still a
    clean degree-2 loop) continue to be detected exactly as before.
    """
    if not (DOOR_LINEWORK_LEAF_MIN_SEGMENTS <= len(component) <= DOOR_LINEWORK_LEAF_MAX_SEGMENTS):
        return None

    degrees: dict[tuple[int, int], int] = defaultdict(int)
    points: list[tuple[float, float]] = []
    for idx in component:
        _, p1, p2 = segs[idx]
        points.extend([p1, p2])
        degrees[_snap_key(p1, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1
        degrees[_snap_key(p2, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1

    if any(degree > 2 for degree in degrees.values()):
        return None
    if not degrees or any(degree != 2 for degree in degrees.values()):
        return None

    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
    w = _bbox_width(bbox)
    h = _bbox_height(bbox)
    long_side = max(w, h)
    short_side = min(w, h)
    if short_side < 1e-6:
        return None
    if not (
        long_side / short_side >= DOOR_LEAF_ASPECT_MIN
        and DOOR_MIN_SIZE_PX <= long_side <= DOOR_MAX_SIZE_PX
    ):
        return None

    layers = [segs[idx][0].layer for idx in component if segs[idx][0].layer]
    layer = layers[0] if layers else None
    layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)
    component_path_indices = sorted(segs[idx][0].path_index for idx in component)
    return _DoorLeaf(
        source="linework_rect",
        bbox=bbox,
        length=long_side,
        corners=_arc_corners(bbox),
        component_path_indices=component_path_indices,
        layer=layer,
        layer_hint=layer_hint,
        evidence={
            "leaf_source": "linework_rect",
            "leaf_size_px": round(long_side, 1),
            "leaf_segment_count": len(component),
            "layer": layer,
            "layer_hint": layer_hint,
        },
    )


def _find_thin_rectangle_cycle(
    component_segs: list[_LinkSeg],
) -> tuple[BBox, list[int]] | None:
    """Find the best thin-rectangle 4-cycle inside a (possibly messy) component.

    Fallback for door leaves whose connected component is no longer a clean closed
    loop because a threshold/sill line or wall stub touches a leaf corner. The
    rectangle is still present as a 4-cycle of segments inside the component; this
    helper enumerates simple 4-cycles and ranks them by thin-rectangle goodness.

    Tie-break uses bbox short-side (smaller wins): when a threshold attaches at two
    leaf corners, both the true leaf cycle and a "3 leaf sides + threshold" cycle
    pass every shape gate; the threshold-substituted cycle's bbox stretches to
    enclose the threshold, so its bbox short-side is larger. Preferring the
    tighter-fitting cycle keeps the leaf intact and leaves the threshold free for
    Step-3 evidence detection.

    Acknowledged limitation: cycles are enumerated on raw primitives, so a
    split-side rectangle (≥5 perimeter primitives) attached to a threshold won't
    be picked up here. Real PDFs rarely combine both; if it shows up, generalise
    cycle enumeration to merge collinear-chained edges into virtual sides.
    """
    if not (DOOR_LINEWORK_LEAF_MIN_SEGMENTS <= len(component_segs) <= DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS):
        return None

    edge_data: list[tuple[tuple[int, int], tuple[int, int], float, float]] = []
    nodes: dict[tuple[int, int], list[tuple[tuple[int, int], int]]] = defaultdict(list)
    for i, (_, p1, p2) in enumerate(component_segs):
        k1 = _snap_key(p1, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)
        k2 = _snap_key(p2, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)
        edge_data.append((k1, k2, _line_length(p1, p2), _line_angle_deg(p1, p2)))
        if k1 == k2:
            continue  # degenerate edge — can't participate in a cycle
        nodes[k1].append((k2, i))
        nodes[k2].append((k1, i))

    # Enumerate simple 4-cycles via bounded DFS. With ≤14 segments this is trivially cheap.
    seen_cycles: set[frozenset[int]] = set()
    cycles: list[tuple[int, int, int, int]] = []
    for start_node in nodes:
        for n1, e0 in nodes[start_node]:
            for n2, e1 in nodes[n1]:
                if e1 == e0 or n2 == start_node:
                    continue
                for n3, e2 in nodes[n2]:
                    if e2 in (e0, e1) or n3 in (start_node, n1):
                        continue
                    for n4, e3 in nodes[n3]:
                        if e3 in (e0, e1, e2) or n4 != start_node:
                            continue
                        key = frozenset((e0, e1, e2, e3))
                        if key not in seen_cycles:
                            seen_cycles.add(key)
                            cycles.append((e0, e1, e2, e3))

    if not cycles:
        return None

    best_rank: tuple[float, float, float] | None = None
    best_bbox: BBox | None = None
    best_indices: list[int] | None = None

    for cycle in cycles:
        lens = [edge_data[i][2] for i in cycle]
        angles = [edge_data[i][3] for i in cycle]

        xs: list[float] = []
        ys: list[float] = []
        for i in cycle:
            _, p1, p2 = component_segs[i]
            xs.extend([p1[0], p2[0]])
            ys.extend([p1[1], p2[1]])
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
        w = _bbox_width(bbox)
        h = _bbox_height(bbox)
        long_side_bbox = max(w, h)
        short_side_bbox = min(w, h)
        if short_side_bbox < 1e-6:
            continue

        # Bbox-shape gate.
        if not (
            long_side_bbox / short_side_bbox >= DOOR_LEAF_ASPECT_MIN
            and DOOR_MIN_SIZE_PX <= long_side_bbox <= DOOR_MAX_SIZE_PX
        ):
            continue

        # Side-length gate — actual thin-rectangle check, not just bbox aspect.
        # Two shortest = short sides; two longest = long sides; long/short ≥ aspect.
        srt = sorted(lens)
        short_max = srt[1]
        long_min = srt[2]
        if short_max < 1e-6 or long_min / short_max < DOOR_LEAF_ASPECT_MIN:
            continue

        # Opposite-side parallelism (edges 0 ∥ 2, edges 1 ∥ 3 in cycle traversal order).
        if _angle_diff_mod180(angles[0], angles[2]) > DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG:
            continue
        if _angle_diff_mod180(angles[1], angles[3]) > DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG:
            continue
        # Adjacent-side perpendicularity (edges 0 ⟂ 1).
        if abs(_angle_diff_mod180(angles[0], angles[1]) - 90.0) > DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG:
            continue

        aspect = long_side_bbox / short_side_bbox
        rank = (aspect, long_side_bbox, -short_side_bbox)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_bbox = bbox
            best_indices = sorted({component_segs[i][0].path_index for i in cycle})

    if best_bbox is None or best_indices is None:
        return None
    return best_bbox, best_indices


def _collect_linework_door_leaves(
    line_paths: list[PathPrimitive],
    collector: DebugTraceCollector | None = None,
) -> list[_DoorLeaf]:
    segs: list[_LinkSeg] = []
    for path in line_paths:
        ok, p1, p2 = _is_line_path(path)
        if ok and _line_length(p1, p2) > 1.0:
            segs.append((path, p1, p2))

    endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, (_, p1, p2) in enumerate(segs):
        endpoint_buckets[_snap_key(p1, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)].append(idx)
        endpoint_buckets[_snap_key(p2, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)].append(idx)

    adjacency: list[set[int]] = [set() for _ in segs]
    for ids in endpoint_buckets.values():
        if len(ids) > 8:
            continue
        for idx in ids:
            adjacency[idx].update(other for other in ids if other != idx)

    seen: set[int] = set()
    leaves: list[_DoorLeaf] = []
    for start_idx in range(len(segs)):
        if start_idx in seen:
            continue
        stack = [start_idx]
        seen.add(start_idx)
        component: list[int] = []
        while stack:
            idx = stack.pop()
            component.append(idx)
            for other in adjacency[idx]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)

        comp_path_indices = sorted(segs[i][0].path_index for i in component) if collector else []

        # Path A: clean closed loop (4–8 segments, every junction degree exactly 2).
        # Preserves the original behaviour, including split-side rectangles.
        leaf = _try_linework_leaf_clean_loop(component, segs)
        if leaf is not None:
            if collector:
                seg_count = len(component)
                cid = collector.record_linework_component(
                    comp_path_indices, "collected", "clean_loop", None,
                    clean_loop_result={"tried": True, "passed": True, "fail_reason": None,
                                       "segment_count": seg_count},
                    subgraph_result=None,
                )
                leaf.debug_id = collector.record_leaf(
                    leaf.source, leaf.component_path_indices,
                    leaf.length, max(_bbox_width(leaf.bbox), _bbox_height(leaf.bbox)),
                    leaf.layer, leaf.layer_hint,
                    linework_component_id=cid,
                )
            leaves.append(leaf)
            continue

        # Determine clean_loop fail reason for trace (debug only)
        clean_loop_result: dict | None = None
        if collector:
            seg_count = len(component)
            if not (DOOR_LINEWORK_LEAF_MIN_SEGMENTS <= seg_count <= DOOR_LINEWORK_LEAF_MAX_SEGMENTS):
                cl_reason = "segment_count_out_of_range"
            else:
                degs: dict = defaultdict(int)
                for i in component:
                    _, pp1, pp2 = segs[i]
                    degs[_snap_key(pp1, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1
                    degs[_snap_key(pp2, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1
                if any(d != 2 for d in degs.values()):
                    cl_reason = "not_all_degree_2"
                else:
                    cl_reason = "shape_check_failed"
            clean_loop_result = {"tried": True, "passed": False, "fail_reason": cl_reason,
                                  "segment_count": seg_count}

        # Path B: subgraph fallback. The component may be a leaf rectangle with a
        # threshold line and/or a few wall stubs attached (degree-3+ junctions, or
        # 5–14 primitives). Search for a thin-rectangle 4-cycle inside it and emit
        # only the rectangle's 4 primitives so the threshold remains free for the
        # Step-3 threshold-line evidence detection.
        seg_count = len(component)
        if not (DOOR_LINEWORK_LEAF_MIN_SEGMENTS <= seg_count <= DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS):
            if collector:
                collector.record_linework_component(
                    comp_path_indices, "rejected", None, "segment_count_out_of_range",
                    clean_loop_result=clean_loop_result,
                    subgraph_result={"tried": False, "passed": False, "fail_reason": "segment_count_out_of_range", "segment_count": seg_count},
                )
            continue
        component_segs = [segs[i] for i in component]
        result = _find_thin_rectangle_cycle(component_segs)
        if result is None:
            if collector:
                collector.record_linework_component(
                    comp_path_indices, "rejected", None, "no_valid_cycle",
                    clean_loop_result=clean_loop_result,
                    subgraph_result={"tried": True, "passed": False, "fail_reason": "no_valid_cycle", "segment_count": seg_count},
                )
            continue
        bbox, path_indices = result

        long_side = max(_bbox_width(bbox), _bbox_height(bbox))
        short_side = min(_bbox_width(bbox), _bbox_height(bbox))
        cycle_path_index_set = set(path_indices)
        layers = [
            segs[i][0].layer for i in component
            if segs[i][0].path_index in cycle_path_index_set and segs[i][0].layer
        ]
        layer = layers[0] if layers else None
        layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)
        door_leaf = _DoorLeaf(
            source="linework_rect_subgraph",
            bbox=bbox,
            length=long_side,
            corners=_arc_corners(bbox),
            component_path_indices=path_indices,
            layer=layer,
            layer_hint=layer_hint,
            evidence={
                "leaf_source": "linework_rect_subgraph",
                "leaf_size_px": round(long_side, 1),
                "leaf_segment_count": 4,
                "leaf_component_segment_count": len(component),
                "layer": layer,
                "layer_hint": layer_hint,
            },
        )
        if collector:
            cid = collector.record_linework_component(
                comp_path_indices, "collected", "subgraph_fallback", None,
                clean_loop_result=clean_loop_result,
                subgraph_result={"tried": True, "passed": True, "fail_reason": None, "segment_count": seg_count},
            )
            door_leaf.debug_id = collector.record_leaf(
                door_leaf.source, path_indices, long_side,
                short_side if short_side > 1e-6 else long_side,
                layer, layer_hint, linework_component_id=cid,
            )
        leaves.append(door_leaf)

    return leaves


def _collect_door_leaves(
    paths: list[PathPrimitive],
    collector: DebugTraceCollector | None = None,
) -> list[_DoorLeaf]:
    leaves: list[_DoorLeaf] = []
    for path in paths:
        if not _is_door_leaf(path, collector):
            continue
        w = _bbox_width(path.bbox)
        h = _bbox_height(path.bbox)
        long_side = max(w, h)
        short_side = min(w, h)
        layer_hint = _layer_hint(path, DOOR_LAYER_KEYWORDS)
        door_leaf = _DoorLeaf(
            source=path.item_type,
            bbox=path.bbox,
            length=long_side,
            corners=_arc_corners(path.bbox),
            component_path_indices=[path.path_index],
            layer=path.layer,
            layer_hint=layer_hint,
            evidence={
                "leaf_source": path.item_type,
                "leaf_size_px": round(long_side, 1),
                "layer": path.layer,
                "layer_hint": layer_hint,
            },
        )
        if collector:
            door_leaf.debug_id = collector.record_leaf(
                path.item_type, [path.path_index], long_side,
                short_side if short_side > 1e-6 else long_side,
                path.layer, layer_hint,
            )
        leaves.append(door_leaf)

    line_paths = [p for p in paths if p.item_type == "l"]
    leaves.extend(_collect_linework_door_leaves(line_paths, collector))
    return leaves


def _find_anchored_leaf_line(
    swing: _DoorSwing,
    line_paths: list[PathPrimitive],
    exclude_indices: set[int],
) -> dict | None:
    """Search for a single line that could be the door leaf for this arc swing.

    Architecturally a door leaf is rooted at the hinge (the arc's pivot corner)
    and extends out to the arc's other endpoint, with length ≈ arc radius. CAD
    drawings often draw this leaf as one line, not a closed rectangle — the
    rectangle-based collectors miss those entirely. This helper performs a
    swing-local search anchored on the arc's actual endpoints.

    Match criteria for a candidate line:
      - length within DOOR_LEAF_LINE_LENGTH_TOL of swing.radius
      - direction within DOOR_LEAF_LINE_AXIS_TOL_DEG of either bbox axis
        (0° or 90° — closed-door orientation along the wall)
      - one endpoint within DOOR_LEAF_LINE_ENDPOINT_TOL_PX of an arc endpoint

    Returns the best match (minimizing length error + endpoint snap distance)
    or ``None`` when nothing matches.
    """
    if not swing.arc_endpoints or len(swing.arc_endpoints) < 2:
        return None
    radius = swing.radius
    if radius < 1e-6:
        return None

    best: dict | None = None
    best_score = float("inf")
    for path in line_paths:
        if path.path_index in exclude_indices:
            continue
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        length = _line_length(p1, p2)
        if length < 1e-6:
            continue
        length_ratio = abs(length - radius) / radius
        if length_ratio > DOOR_LEAF_LINE_LENGTH_TOL:
            continue
        angle = _line_angle_deg(p1, p2)
        if not (
            _angle_diff_mod180(angle, 0.0) <= DOOR_LEAF_LINE_AXIS_TOL_DEG
            or _angle_diff_mod180(angle, 90.0) <= DOOR_LEAF_LINE_AXIS_TOL_DEG
        ):
            continue
        for arc_end in swing.arc_endpoints:
            for line_end in (p1, p2):
                d = _distance(arc_end, line_end)
                if d > DOOR_LEAF_LINE_ENDPOINT_TOL_PX:
                    continue
                score = length_ratio + d / radius
                if score < best_score:
                    best_score = score
                    best = {
                        "path_index": path.path_index,
                        "length": length,
                        "length_ratio": length_ratio,
                        "endpoint_dist": d,
                        "anchor_arc_endpoint": arc_end,
                        "anchor_line_endpoint": line_end,
                        "p1": p1,
                        "p2": p2,
                        "layer": path.layer,
                    }
    return best


def _find_leaf_companion_lines(
    leaf_line: dict,
    line_paths: list[PathPrimitive],
    exclude_indices: set[int],
) -> set[int]:
    """Find lines forming the same thin-rect leaf as the anchored leaf line.

    Door panels are commonly drawn as a thin stroked rectangle — a pair of
    near-parallel lines a few pixels apart, sometimes plus 2 short caps. The
    anchored-line check locks onto one long edge; without this helper the other
    long edge looks like a wall-like line crossing the arc bridge and the
    opening check downgrades a real door. This walks every line, parallel to
    the leaf within DOOR_LEAF_LINE_AXIS_TOL_DEG, with both endpoints within
    DOOR_LEAF_COMPANION_PERP_PX of the leaf, and projecting onto at least
    DOOR_LEAF_COMPANION_OVERLAP of its own length over the leaf's interval.
    """
    p1, p2 = leaf_line["p1"], leaf_line["p2"]
    leaf_length = leaf_line["length"]
    if leaf_length < 1e-6:
        return set()
    leaf_angle = _line_angle_deg(p1, p2)
    ux = (p2[0] - p1[0]) / leaf_length
    uy = (p2[1] - p1[1]) / leaf_length
    nx, ny = -uy, ux
    ref_interval = _projected_interval(p1, p2, ux, uy, p1)

    companions: set[int] = set()
    for path in line_paths:
        if path.path_index in exclude_indices:
            continue
        ok, q1, q2 = _is_line_path(path)
        if not ok:
            continue
        if _angle_diff_mod180(_line_angle_deg(q1, q2), leaf_angle) > DOOR_LEAF_LINE_AXIS_TOL_DEG:
            continue
        d_q1 = abs((q1[0] - p1[0]) * nx + (q1[1] - p1[1]) * ny)
        d_q2 = abs((q2[0] - p1[0]) * nx + (q2[1] - p1[1]) * ny)
        if max(d_q1, d_q2) > DOOR_LEAF_COMPANION_PERP_PX:
            continue
        cand_interval = _projected_interval(q1, q2, ux, uy, p1)
        overlap = _interval_overlap(ref_interval, cand_interval)
        cand_len = _line_length(q1, q2)
        if cand_len > 0 and overlap / cand_len < DOOR_LEAF_COMPANION_OVERLAP:
            continue
        companions.add(path.path_index)
    return companions
