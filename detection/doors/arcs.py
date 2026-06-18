from __future__ import annotations
import math
from collections import defaultdict
from itertools import combinations
from models import BBox, PathPrimitive
from debug.trace import DebugTraceCollector
from detection.geometry import _bbox_expanded, _bbox_height, _bbox_width, _bboxes_overlap, _distance, _is_line_path, _line_angle_deg, _line_length
from detection.layers import _layer_hint, _layer_hint_from_layer
from detection.doors.models import _DoorSwing
from detection.doors.constants import (
    DOOR_BBOX_ASPECT_MAX, DOOR_BBOX_ASPECT_MIN, DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX,
    DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX, DOOR_CURVE_CHAIN_MIN_CURVES,
    DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS, DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS,
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_RADIUS_RATIO_TOL, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_POLYLINE_CHAIN_DELTA_DEG, DOOR_POLYLINE_CYCLE_MAX_SEGMENTS, DOOR_POLYLINE_ENDPOINT_TOL,
    DOOR_POLYLINE_MAX_ANGLE_BINS, DOOR_POLYLINE_MAX_SEGMENTS, DOOR_POLYLINE_MAX_SEG_PX,
    DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_SPUR_MAX_SEGMENTS, DOOR_SWING_LINE_DIST_PX,
)


def _is_arc_like(path: PathPrimitive, collector: DebugTraceCollector | None = None) -> bool:
    # "mixed" never appears after path explosion — each item gets its own kind.
    if path.item_type != "c":
        if collector:
            collector.record_arc_filter(path, False, "item_type_not_curve")
        return False
    w = _bbox_width(path.bbox)
    h = _bbox_height(path.bbox)
    if h < 1e-6:
        if collector:
            collector.record_arc_filter(path, False, "height_degenerate")
        return False
    aspect = w / h
    size = max(w, h)
    if not (DOOR_BBOX_ASPECT_MIN <= aspect <= DOOR_BBOX_ASPECT_MAX):
        if collector:
            collector.record_arc_filter(path, False, "aspect_ratio", aspect_ratio=aspect, size_px=size)
        return False
    if not (DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX):
        if collector:
            collector.record_arc_filter(path, False, "size_out_of_range", aspect_ratio=aspect, size_px=size)
        return False
    if collector:
        collector.record_arc_filter(path, True, None, aspect_ratio=aspect, size_px=size)
    return True


def _arc_corners(bbox: BBox) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = bbox
    return [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]


def _estimate_arc_sweep_deg(
    points: list[tuple[float, float]],
    bbox: BBox,
) -> float | None:
    """Estimate sweep angle of a Bézier arc from its endpoints and estimated center.

    For CAD-exported Bézier curves, points[0] and points[-1] are the actual arc
    start and end. The center is estimated as the bbox corner at distance ≈ radius
    from both endpoints. Returns None when the geometry is degenerate.
    """
    if len(points) < 2:
        return None
    start, end = points[0], points[-1]
    radius = max(_bbox_width(bbox), _bbox_height(bbox))
    if radius < 1e-6:
        return None
    best_corner = None
    best_score = float("inf")
    for corner in _arc_corners(bbox):
        score = abs(_distance(start, corner) - radius) + abs(_distance(end, corner) - radius)
        if score < best_score:
            best_score = score
            best_corner = corner
    if best_corner is None:
        return None
    vs = (start[0] - best_corner[0], start[1] - best_corner[1])
    ve = (end[0] - best_corner[0], end[1] - best_corner[1])
    mag_s = math.hypot(*vs)
    mag_e = math.hypot(*ve)
    if mag_s < 1e-6 or mag_e < 1e-6:
        return None
    cos_a = max(-1.0, min(1.0, (vs[0] * ve[0] + vs[1] * ve[1]) / (mag_s * mag_e)))
    return math.degrees(math.acos(cos_a))


def _prune_arc_spurs(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
) -> tuple[list[int], set[int]]:
    """Remove short leaf-spurs (door stops, cap lines) from an arc component.

    A clean door-arc connected component is a simple chain: two degree-1
    endpoints, all interior vertices degree-2. A polluted arc is that chain
    plus a short tail of axis-aligned segments hanging off the arc's
    endpoint, joined through a degree-3+ junction. This walk-and-prune step
    iteratively removes those tails so the existing axis_like_fraction and
    angle_bin_count checks see only the arc itself.

    Returns (pruned_component, removed_seg_path_indices). If pruning would
    drop |component| below DOOR_POLYLINE_MIN_SEGMENTS, returns the original
    component and an empty set.
    """
    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    current = list(component)
    removed_path_indices: set[int] = set()

    while True:
        if len(current) < DOOR_POLYLINE_MIN_SEGMENTS:
            break

        # Build vertex → local-seg-indices map on the current subset.
        endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for local_idx, seg_idx in enumerate(current):
            _, p1, p2, _, _ = segs[seg_idx]
            endpoint_buckets[snap_key(p1)].append(local_idx)
            endpoint_buckets[snap_key(p2)].append(local_idx)

        leaves = [pt for pt, lis in endpoint_buckets.items() if len(lis) == 1]
        if not leaves:
            break  # pure cycle — no spurs to prune

        spur_locals: set[int] = set()
        for leaf in leaves:
            walked: list[int] = []
            visited_vertices: set[tuple[int, int]] = {leaf}
            current_vertex = leaf
            prev_local = -1

            while True:
                neighbours = endpoint_buckets.get(current_vertex, [])
                if current_vertex != leaf and len(neighbours) > 2:
                    break  # hit a junction — spur ends here, candidate for prune
                if current_vertex != leaf and len(neighbours) == 1:
                    # Walked all the way to another leaf — component is a
                    # single open chain, nothing to prune.
                    walked = []
                    break

                next_local = next(
                    (n for n in neighbours if n != prev_local),
                    None,
                )
                if next_local is None:
                    walked = []
                    break

                walked.append(next_local)
                if len(walked) > DOOR_POLYLINE_SPUR_MAX_SEGMENTS:
                    walked = []  # too long to count as a spur
                    break

                _, p1, p2, _, _ = segs[current[next_local]]
                k1, k2 = snap_key(p1), snap_key(p2)
                next_vertex = k2 if k1 == current_vertex else k1

                if next_vertex in visited_vertices:
                    walked = []  # cycle — abort this walk
                    break

                visited_vertices.add(next_vertex)
                prev_local = next_local
                current_vertex = next_vertex

            if walked:
                spur_locals.update(walked)

        if not spur_locals:
            break
        if len(current) - len(spur_locals) < DOOR_POLYLINE_MIN_SEGMENTS:
            break

        new_current: list[int] = []
        for local_idx, seg_idx in enumerate(current):
            if local_idx in spur_locals:
                removed_path_indices.add(segs[seg_idx][0].path_index)
            else:
                new_current.append(seg_idx)
        current = new_current

    return current, removed_path_indices


def _prune_arc_cycle_caps(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
) -> tuple[list[int], set[int]]:
    """Remove a small closed-cycle cap attached at a single articulation point.

    Some CAD draftsmen draw a door's latch position as a closed
    mini-rectangle attached at the arc's natural endpoint. Topologically
    this is a closed cycle sharing exactly one vertex with the arc. Spur
    pruning can't fire because there's no degree-1 leaf inside the cycle;
    chain-cap trim can't fire because the junction breaks "2-leaf simple
    chain". This step walks from each junction along each incident edge
    through degree-2 vertices; if the walk returns to the same junction
    within DOOR_POLYLINE_CYCLE_MAX_SEGMENTS steps, the walked edges form
    a closed cycle attached at that junction and they're trimmed.

    Iterates so a multi-tier appendage (cycle inside cycle, or two
    cycles at separate junctions) collapses in successive passes.

    Returns (kept_component, removed_seg_path_indices). Floor-guarded so
    no prune drops the component below DOOR_POLYLINE_MIN_SEGMENTS.
    """
    if len(component) < DOOR_POLYLINE_MIN_SEGMENTS:
        return list(component), set()

    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    current = list(component)
    removed_path_indices: set[int] = set()

    while True:
        endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for local_idx, seg_idx in enumerate(current):
            _, p1, p2, _, _ = segs[seg_idx]
            endpoint_buckets[snap_key(p1)].append(local_idx)
            endpoint_buckets[snap_key(p2)].append(local_idx)

        junctions = [v for v, lis in endpoint_buckets.items() if len(lis) >= 3]
        if not junctions:
            break

        cycle_locals: list[int] | None = None
        for junction in junctions:
            for start_local in endpoint_buckets[junction]:
                walked: list[int] = [start_local]
                seg_idx = current[start_local]
                _, p1, p2, _, _ = segs[seg_idx]
                k1, k2 = snap_key(p1), snap_key(p2)
                cur_vertex = k2 if k1 == junction else k1
                prev_local = start_local

                while len(walked) <= DOOR_POLYLINE_CYCLE_MAX_SEGMENTS:
                    if cur_vertex == junction:
                        cycle_locals = walked
                        break
                    neighbours = endpoint_buckets.get(cur_vertex, [])
                    if len(neighbours) != 2:
                        # leaf (spur), other junction, or empty — not a cycle.
                        break
                    next_local = next(
                        (n for n in neighbours if n != prev_local),
                        None,
                    )
                    if next_local is None:
                        break
                    walked.append(next_local)
                    seg_idx = current[next_local]
                    _, p1, p2, _, _ = segs[seg_idx]
                    k1, k2 = snap_key(p1), snap_key(p2)
                    next_vertex = k2 if k1 == cur_vertex else k1
                    prev_local = next_local
                    cur_vertex = next_vertex

                if cycle_locals is not None:
                    break
            if cycle_locals is not None:
                break

        if cycle_locals is None:
            break
        if len(current) - len(cycle_locals) < DOOR_POLYLINE_MIN_SEGMENTS:
            break

        cycle_set = set(cycle_locals)
        new_current: list[int] = []
        for local_idx, seg_idx in enumerate(current):
            if local_idx in cycle_set:
                removed_path_indices.add(segs[seg_idx][0].path_index)
            else:
                new_current.append(seg_idx)
        current = new_current

    return current, removed_path_indices


def _split_double_arc(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
) -> tuple[list[int], list[int]] | None:
    """Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.

    The garden-door / double-door pattern: two door panels swing AWAY from
    a shared hinge. Each swing arc is a normal quarter-ish polyline arc;
    the two arcs share one endpoint (the hinge) and their walk-direction
    tangents at the hinge are antiparallel (~180° break). BFS merges the
    two arcs into one 2-leaf simple chain.

    Without this detector, _trim_chain_extension_caps would treat one half
    as a "cap" past the break and trim it, leaving only one of the two
    swings detected. Calling _split_double_arc first preserves both halves
    so each can pair with its own leaf line.

    Returns ``(left_seg_indices, right_seg_indices)`` (both lists of seg
    indices into ``segs``, preserving walk order) when the component is
    a true double-arc: exactly one >DOOR_POLYLINE_CHAIN_DELTA_DEG break,
    each side ≥ DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS, each side has
    ≥ DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS distinct 15° angle bins (i.e.
    is genuinely curved — rules out a §3.6 axis-aligned cap that happens
    to be long).

    Returns ``None`` otherwise so the existing prune/trim chain handles
    the component as today.
    """
    if len(component) < 2 * DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS:
        return None

    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for local_idx, seg_idx in enumerate(component):
        _, p1, p2, _, _ = segs[seg_idx]
        endpoint_buckets[snap_key(p1)].append(local_idx)
        endpoint_buckets[snap_key(p2)].append(local_idx)

    leaves = [pt for pt, lis in endpoint_buckets.items() if len(lis) == 1]
    junctions_present = any(len(lis) > 2 for lis in endpoint_buckets.values())
    if len(leaves) != 2 or junctions_present:
        return None

    # Walk leaf-to-leaf, recording each seg's walk-direction angle in [0, 360).
    walk: list[tuple[int, float]] = []
    current_vertex = leaves[0]
    prev_local = -1
    while True:
        neighbours = endpoint_buckets.get(current_vertex, [])
        next_local = next((n for n in neighbours if n != prev_local), None)
        if next_local is None:
            break
        seg_idx = component[next_local]
        _, p1, p2, _, _ = segs[seg_idx]
        k1, k2 = snap_key(p1), snap_key(p2)
        if k1 == current_vertex:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            next_vertex = k2
        else:
            dx, dy = p1[0] - p2[0], p1[1] - p2[1]
            next_vertex = k1
        angle = math.degrees(math.atan2(dy, dx)) % 360.0
        walk.append((next_local, angle))
        prev_local = next_local
        current_vertex = next_vertex

    if len(walk) != len(component):
        return None

    def signed_delta(a1: float, a2: float) -> float:
        d = (a2 - a1) % 360.0
        if d > 180.0:
            d -= 360.0
        return d

    break_positions = [
        i for i in range(len(walk) - 1)
        if abs(signed_delta(walk[i][1], walk[i + 1][1])) > DOOR_POLYLINE_CHAIN_DELTA_DEG
    ]
    if len(break_positions) != 1:
        return None

    break_idx = break_positions[0]
    left_walk = walk[: break_idx + 1]
    right_walk = walk[break_idx + 1 :]
    if (
        len(left_walk) < DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS
        or len(right_walk) < DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS
    ):
        return None

    def angle_bin_count(walk_slice: list[tuple[int, float]]) -> int:
        bins: set[int] = set()
        for local_idx, _ in walk_slice:
            seg_idx = component[local_idx]
            # segs entries store the undirected angle in [0, 180) at index 4.
            undirected_angle = segs[seg_idx][4]
            bins.add(int(undirected_angle // 15.0))
        return len(bins)

    if (
        angle_bin_count(left_walk) < DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS
        or angle_bin_count(right_walk) < DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS
    ):
        return None

    left_segs = [component[local_idx] for (local_idx, _) in left_walk]
    right_segs = [component[local_idx] for (local_idx, _) in right_walk]
    return left_segs, right_segs


def _trim_chain_extension_caps(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
) -> tuple[list[int], set[int]]:
    """Trim non-arc cap segments off a 2-leaf simple chain.

    Some CAD draftsmen draw a door's latch position as a short axis-aligned
    "cap" attached at the arc's natural endpoint, forming a linear extension
    of the chain (not a branched cluster). Spur pruning can't fire because
    there's no degree-3+ junction — the cap is just a continuation of the
    same chain. This step walks the chain end-to-end, looks at each segment's
    direction angle, and finds the longest contiguous run where consecutive
    inter-segment angle deltas are small (an "arc-like" run). Anything past
    a sharp angle break (> DOOR_POLYLINE_CHAIN_DELTA_DEG) is treated as a
    cap and trimmed.

    Only acts on components that are simple chains: exactly two degree-1
    leaves and zero degree-3+ junctions. Components with junctions or
    cycles fall through unchanged so spur pruning / downstream checks can
    do their job. If trimming would drop the chain below
    DOOR_POLYLINE_MIN_SEGMENTS, no trim is applied.

    Returns (kept_component, removed_seg_path_indices).
    """
    if len(component) < DOOR_POLYLINE_MIN_SEGMENTS:
        return list(component), set()

    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for local_idx, seg_idx in enumerate(component):
        _, p1, p2, _, _ = segs[seg_idx]
        endpoint_buckets[snap_key(p1)].append(local_idx)
        endpoint_buckets[snap_key(p2)].append(local_idx)

    leaves = [pt for pt, lis in endpoint_buckets.items() if len(lis) == 1]
    junctions_present = any(len(lis) > 2 for lis in endpoint_buckets.values())
    if len(leaves) != 2 or junctions_present:
        return list(component), set()

    # Walk from one leaf to the other, recording (local_idx, walk-direction angle).
    walk: list[tuple[int, float]] = []
    current_vertex = leaves[0]
    prev_local = -1
    while True:
        neighbours = endpoint_buckets.get(current_vertex, [])
        next_local = next((n for n in neighbours if n != prev_local), None)
        if next_local is None:
            break
        seg_idx = component[next_local]
        _, p1, p2, _, _ = segs[seg_idx]
        k1, k2 = snap_key(p1), snap_key(p2)
        if k1 == current_vertex:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            next_vertex = k2
        else:
            dx, dy = p1[0] - p2[0], p1[1] - p2[1]
            next_vertex = k1
        angle = math.degrees(math.atan2(dy, dx)) % 360.0
        walk.append((next_local, angle))
        prev_local = next_local
        current_vertex = next_vertex

    # A 2-leaf simple chain should walk every seg exactly once.
    if len(walk) != len(component):
        return list(component), set()

    # Find the longest contiguous run where consecutive direction-deltas are
    # all within DOOR_POLYLINE_CHAIN_DELTA_DEG. A "run" of length k covers
    # k segments (indices [start, start+k-1] in walk order). Single-segment
    # runs are allowed.
    def signed_delta(a1: float, a2: float) -> float:
        d = (a2 - a1) % 360.0
        if d > 180.0:
            d -= 360.0
        return d

    best_start, best_end = 0, 0
    run_start = 0
    for i in range(len(walk) - 1):
        _, a_i = walk[i]
        _, a_next = walk[i + 1]
        if abs(signed_delta(a_i, a_next)) > DOOR_POLYLINE_CHAIN_DELTA_DEG:
            if i - run_start > best_end - best_start:
                best_start, best_end = run_start, i
            run_start = i + 1
    # Close the trailing run.
    final_end = len(walk) - 1
    if final_end - run_start > best_end - best_start:
        best_start, best_end = run_start, final_end

    if best_start == 0 and best_end == len(walk) - 1:
        return list(component), set()  # no break detected; nothing to trim

    new_component_len = best_end - best_start + 1
    if new_component_len < DOOR_POLYLINE_MIN_SEGMENTS:
        return list(component), set()  # floor guard

    kept_walk_indices = set(range(best_start, best_end + 1))
    new_component: list[int] = []
    removed_path_indices: set[int] = set()
    for walk_pos, (local_idx, _) in enumerate(walk):
        seg_idx = component[local_idx]
        if walk_pos in kept_walk_indices:
            new_component.append(seg_idx)
        else:
            removed_path_indices.add(segs[seg_idx][0].path_index)

    return new_component, removed_path_indices


def _detect_polyline_arc_bboxes(
    line_paths: list[PathPrimitive],
    collector: DebugTraceCollector | None = None,
) -> list[dict]:
    """Detect door-swing arcs approximated by connected short line segments.

    Some CAD exports flatten arcs into many tiny line segments, so no PDF curve
    primitive survives extraction. A door swing drawn that way usually appears
    as one open connected component with a near-square bbox and a broad spread
    of segment angles. Closed boxes and hatch strokes are rejected by endpoint
    degree, axis-line fraction, and angle-bin diversity.
    """
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]] = []
    for path in line_paths:
        ok, p1, p2 = _is_line_path(path)
        if not ok:
            continue
        length = _line_length(p1, p2)
        # This length cap also makes this detector immune to threshold/sill lines
        # bridging a door opening — those are longer than a single flattened arc segment
        # and never enter the polyline-arc adjacency graph.
        if 2.0 <= length <= DOOR_POLYLINE_MAX_SEG_PX:
            segs.append((path, p1, p2, length, _line_angle_deg(p1, p2)))
            if collector:
                collector.record_polyline_length(path, length, True)
        elif collector:
            fail = "segment_too_short" if length < 2.0 else "segment_too_long"
            collector.record_polyline_length(path, length, False, fail)

    if not segs:
        return []

    def key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, (_, p1, p2, _, _) in enumerate(segs):
        endpoint_buckets[key(p1)].append(idx)
        endpoint_buckets[key(p2)].append(idx)

    adjacency: list[set[int]] = [set() for _ in segs]
    for ids in endpoint_buckets.values():
        # Very busy junctions are usually hatch/detail clutter, not one door arc.
        if len(ids) > 20:
            continue
        for idx in ids:
            adjacency[idx].update(other for other in ids if other != idx)

    seen: set[int] = set()
    arc_infos: list[dict] = []

    def _process_component(
        component: list[int],
        pre_prune_segment_count: int,
        double_arc_partner_paths: list[int] | None = None,
        pre_pruned_path_indices: set[int] | None = None,
    ) -> None:
        """Run pruning + checks for one component, append arc_info on success.

        ``double_arc_partner_paths`` is set when this component is one half
        of a garden-door / double-arc split (see _split_double_arc). It
        carries the OTHER half's path indices so downstream pairing can
        cross-exclude the partner's arc when running the opening check —
        otherwise each half would see the other as a "sill obstruction"
        across its bridge.

        ``pre_pruned_path_indices`` carries paths trimmed *before* this call
        (spur/cycle prunes done outside) plus the partner half's paths in
        the split case, so the debug record's ``pruned_path_indices`` is a
        complete picture of what the BFS-found ``pre_prune_segment_count``
        component originally contained versus the final collected set.
        """
        component, pruned_path_indices_set = _prune_arc_spurs(component, segs)
        component, cycle_trimmed_set = _prune_arc_cycle_caps(component, segs)
        component, cap_trimmed_set = _trim_chain_extension_caps(component, segs)
        pruned_path_indices = sorted(
            pruned_path_indices_set
            | cycle_trimmed_set
            | cap_trimmed_set
            | (pre_pruned_path_indices or set())
        )
        seg_count = len(component)
        checks: dict = {
            "segment_count": {
                "value": seg_count,
                "range": [DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_MAX_SEGMENTS],
                "passed": DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS,
            },
            "bbox_aspect": None, "size_px": None, "axis_like_fraction": None,
            "angle_bin_count": None, "endpoint_count": None, "overlaps_native_arc": None,
        }
        comp_path_indices = sorted(segs[i][0].path_index for i in component) if collector else []

        if not (DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS):
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "segment_count_out_of_range", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return

        points = [pt for idx in component for pt in (segs[idx][1], segs[idx][2])]
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
        w = _bbox_width(bbox)
        h = _bbox_height(bbox)
        if h < 1e-6:
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "bbox_degenerate", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return
        aspect = w / h
        size = max(w, h)
        checks["bbox_aspect"] = {"value": round(aspect, 4), "range": [0.65, 1.45], "passed": 0.65 <= aspect <= 1.45}
        checks["size_px"] = {"value": round(size, 2), "range": [DOOR_MIN_SIZE_PX, DOOR_MAX_SIZE_PX], "passed": DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX}
        if not (0.65 <= aspect <= 1.45 and DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX):
            fail = "bbox_aspect" if not (0.65 <= aspect <= 1.45) else "size_out_of_range"
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", fail, checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return

        angles = [segs[idx][4] for idx in component]
        axis_like = sum(
            1 for angle in angles
            if min(abs(angle - 0.0), abs(angle - 90.0), abs(angle - 180.0)) <= 8.0
        ) / len(angles)
        checks["axis_like_fraction"] = {"value": round(axis_like, 3), "max": 0.35, "passed": axis_like <= 0.35}
        if axis_like > 0.35:
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "axis_like_fraction", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return

        angle_bins = {int(angle // 15.0) for angle in angles}
        checks["angle_bin_count"] = {"value": len(angle_bins), "range": [4, DOOR_POLYLINE_MAX_ANGLE_BINS], "passed": 4 <= len(angle_bins) <= DOOR_POLYLINE_MAX_ANGLE_BINS}
        if not (4 <= len(angle_bins) <= DOOR_POLYLINE_MAX_ANGLE_BINS):
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "angle_bin_count", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return

        degrees: dict[tuple[int, int], int] = defaultdict(int)
        point_sums: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
        for idx in component:
            for pt in (segs[idx][1], segs[idx][2]):
                pt_key = key(pt)
                degrees[pt_key] += 1
                point_sums[pt_key][0] += pt[0]
                point_sums[pt_key][1] += pt[1]
                point_sums[pt_key][2] += 1.0
        endpoint_keys = [pt_key for pt_key, degree in degrees.items() if degree == 1]
        checks["endpoint_count"] = {"value": len(endpoint_keys), "required": 2, "passed": len(endpoint_keys) == 2}
        if len(endpoint_keys) != 2:
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "endpoint_count", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            return

        endpoints = [
            (
                point_sums[pt_key][0] / point_sums[pt_key][2],
                point_sums[pt_key][1] / point_sums[pt_key][2],
            )
            for pt_key in endpoint_keys
        ]
        layers = [segs[idx][0].layer for idx in component if segs[idx][0].layer]
        # overlaps_native_arc is checked in _collect_door_swings after this returns
        checks["overlaps_native_arc"] = {"overlaps": False, "passed": True}

        component_path_indices = sorted(segs[idx][0].path_index for idx in component)
        arc_info: dict = {
            "bbox": bbox,
            "segment_count": len(component),
            "axis_like_fraction": round(axis_like, 3),
            "angle_bin_count": len(angle_bins),
            "endpoints": endpoints,
            "component_path_indices": component_path_indices,
            "layer": layers[0] if layers else None,
        }
        if double_arc_partner_paths is not None:
            arc_info["double_arc_partner_paths"] = sorted(double_arc_partner_paths)
        if collector:
            cid = collector.record_polyline_component(
                comp_path_indices, "collected", None, checks,
                pre_prune_segment_count=pre_prune_segment_count,
                pruned_path_indices=pruned_path_indices,
            )
            arc_info["component_id"] = cid
        arc_infos.append(arc_info)

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

        pre_prune_segment_count = len(component)

        # Pre-clean spurs and cycles BEFORE attempting the double-arc split.
        # The garden-door pattern often has a tiny closed cycle at the hinge
        # (two near-overlapping vertical segs the CAD tool emitted as both
        # halves' final segs) that registers as a degree-3+ junction and
        # makes _split_double_arc bail out on the "no junctions" check. Spur
        # and cycle pruning leave the double-arc 2-leaf simple chain intact
        # without affecting either half's curvature.
        cleaned, pre_split_spurs = _prune_arc_spurs(component, segs)
        cleaned, pre_split_cycles = _prune_arc_cycle_caps(cleaned, segs)
        pre_split_pruned = pre_split_spurs | pre_split_cycles

        # Garden-door / double-arc detection: a 2-leaf simple chain with two
        # arc halves meeting at a ~180° tangent break (the door hinge). When
        # found, emit BOTH halves as separate components so each can pair
        # with its own leaf line; without this split, _trim_chain_extension_caps
        # would treat one half as a "cap" past the break and trim it.
        split = _split_double_arc(cleaned, segs)
        if split is not None:
            left, right = split
            left_paths = [segs[i][0].path_index for i in left]
            right_paths = [segs[i][0].path_index for i in right]
            _process_component(
                left, pre_prune_segment_count,
                double_arc_partner_paths=right_paths,
                pre_pruned_path_indices=pre_split_pruned | set(right_paths),
            )
            _process_component(
                right, pre_prune_segment_count,
                double_arc_partner_paths=left_paths,
                pre_pruned_path_indices=pre_split_pruned | set(left_paths),
            )
        else:
            # Non-double-arc: existing flow. _process_component's spur/cycle
            # prune passes are no-ops on `cleaned` (already pruned) and the
            # chain-trim still gets to fire on §3.6 cap-extension patterns.
            _process_component(cleaned, pre_prune_segment_count,
                               pre_pruned_path_indices=pre_split_pruned)

    return arc_infos


def _fit_circle_3pt(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> tuple[float, float, float] | None:
    """Fit a circle through 3 points. Returns (cx, cy, radius) or None if
    the points are collinear (no unique circle through them).

    Standard determinant form: the center is at the intersection of the
    perpendicular bisectors of any two chords.
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    d = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return None
    a = x1 * x1 + y1 * y1
    b = x2 * x2 + y2 * y2
    c = x3 * x3 + y3 * y3
    cx = (a * (y2 - y3) + b * (y3 - y1) + c * (y1 - y2)) / d
    cy = (a * (x3 - x2) + b * (x1 - x3) + c * (x2 - x1)) / d
    radius = math.hypot(x1 - cx, y1 - cy)
    return cx, cy, radius


def _native_curve_chains(
    c_paths: list[PathPrimitive],
) -> list[list[PathPrimitive]]:
    """Group native `c` (Bezier) primitives by endpoint adjacency.

    PDF arcs are often emitted as a chain of short cubic Beziers. Each
    individual curve may be too small to pass `_is_arc_like`, but the
    chain as a whole forms a single logical arc. This groups them via
    endpoint snapping at DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX.

    Returns a list of chains, each chain a list of PathPrimitive (one
    chain per connected component). Singletons are included as
    single-element chains.
    """
    if not c_paths:
        return []

    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX),
            round(point[1] / DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX),
        )

    endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, path in enumerate(c_paths):
        if len(path.points) >= 2:
            endpoint_buckets[snap_key(path.points[0])].append(idx)
            endpoint_buckets[snap_key(path.points[-1])].append(idx)

    adjacency: list[set[int]] = [set() for _ in c_paths]
    for ids in endpoint_buckets.values():
        for a in ids:
            for b in ids:
                if a != b:
                    adjacency[a].add(b)

    seen: set[int] = set()
    chains: list[list[PathPrimitive]] = []
    for start in range(len(c_paths)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        comp: list[PathPrimitive] = []
        while stack:
            i = stack.pop()
            comp.append(c_paths[i])
            for j in adjacency[i]:
                if j not in seen:
                    seen.add(j)
                    stack.append(j)
        chains.append(comp)
    return chains


def _detect_curve_arc_double_partners(
    swings: list["_DoorSwing"],
    paths: list[PathPrimitive],
) -> None:
    """Pair single-Bezier `curve_arc` swings that form a garden-door split.

    The polyline-arc detector (§3.7) recognises a garden door when both
    halves are drawn as `l`-segment chains that BFS joins into one
    component — _split_double_arc then emits both halves with cross-pointing
    `double_arc_partner_paths`. When each half is instead a single native
    `c` (cubic Bezier) that individually passes _is_arc_like, the two arcs
    never enter the polyline pipeline and never meet — so the polyline
    helper can't see the pattern. This pass closes that gap with the same
    cross-pointing partnership, in-place on `swings`.

    Match criteria — all must hold for a pair:
    - Both swings are source="curve_arc" with one Bezier path each, and
      neither already has `double_arc_partner_paths` set.
    - Radii match within DOOR_LEAF_RADIUS_RATIO_TOL.
    - One endpoint of each coincides within DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX.
    - Tangent break across the shared endpoint, computed as the angle
      between arc A's incoming walk-direction tangent (non-shared → shared)
      and arc B's outgoing walk-direction tangent (shared → non-shared),
      exceeds DOOR_POLYLINE_CHAIN_DELTA_DEG. This mirrors the antiparallel
      check `_split_double_arc` performs at the hinge of a polyline garden
      pair, and correctly rejects smooth S-curve continuations whose
      incoming + outgoing tangents are nearly equal.

    The orientation matters: comparing both arcs' *outgoing-from-shared*
    tangents would flip one of them and read as parallel (~0°), so the
    pair would never match. Always pair incoming-A with outgoing-B.
    """
    paths_by_index = {p.path_index: p for p in paths}

    eligible: list[tuple[int, _DoorSwing]] = [
        (i, s) for i, s in enumerate(swings)
        if s.source == "curve_arc"
        and s.double_arc_partner_paths is None
        and len(s.component_path_indices) == 1
        and len(s.arc_endpoints) == 2
    ]

    matched: set[int] = set()
    for (i, si), (j, sj) in combinations(eligible, 2):
        if i in matched or j in matched:
            continue

        ri, rj = si.radius, sj.radius
        if ri <= 0 or rj <= 0:
            continue
        if abs(ri - rj) / max(ri, rj) > DOOR_LEAF_RADIUS_RATIO_TOL:
            continue

        # Find a single shared endpoint. arc_endpoints == [points[0], points[-1]],
        # so a_endpoint_idx in {0, 1} maps to Bezier points[0] vs points[3].
        shared: tuple[int, int] | None = None
        for ai, ea in enumerate(si.arc_endpoints):
            for bi, eb in enumerate(sj.arc_endpoints):
                if math.hypot(ea[0] - eb[0], ea[1] - eb[1]) <= DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX:
                    shared = (ai, bi)
                    break
            if shared is not None:
                break
        if shared is None:
            continue

        path_i = paths_by_index.get(si.component_path_indices[0])
        path_j = paths_by_index.get(sj.component_path_indices[0])
        if path_i is None or path_j is None:
            continue
        if len(path_i.points) < 4 or len(path_j.points) < 4:
            # Not a cubic Bezier — this helper only pairs native `c` arcs.
            continue

        # Tangent at the shared endpoint:
        # - Bezier point[0]: derivative direction points toward point[1];
        #   "into the endpoint" (non-shared → shared walk) is point[0]-point[1].
        # - Bezier point[3]: derivative direction points toward point[2];
        #   "into the endpoint" (non-shared → shared walk) is point[3]-point[2].
        # "Out of the endpoint" is the negative of "into".
        def into_tangent(path: PathPrimitive, end_idx: int) -> tuple[float, float]:
            if end_idx == 0:
                return (path.points[0][0] - path.points[1][0],
                        path.points[0][1] - path.points[1][1])
            return (path.points[3][0] - path.points[2][0],
                    path.points[3][1] - path.points[2][1])

        t_in = into_tangent(path_i, shared[0])               # walking arc i into the hinge
        t_out_neg = into_tangent(path_j, shared[1])
        t_out = (-t_out_neg[0], -t_out_neg[1])               # walking arc j out of the hinge
        if (t_in[0] == 0.0 and t_in[1] == 0.0) or (t_out[0] == 0.0 and t_out[1] == 0.0):
            continue

        a_in = math.degrees(math.atan2(t_in[1], t_in[0]))
        a_out = math.degrees(math.atan2(t_out[1], t_out[0]))
        delta = abs(((a_out - a_in) + 180.0) % 360.0 - 180.0)
        if delta < DOOR_POLYLINE_CHAIN_DELTA_DEG:
            continue

        si.double_arc_partner_paths = list(sj.component_path_indices)
        sj.double_arc_partner_paths = list(si.component_path_indices)
        matched.add(i)
        matched.add(j)


def _collect_door_swings(
    paths: list[PathPrimitive],
    collector: DebugTraceCollector | None = None,
) -> list[_DoorSwing]:
    # _is_arc_like records arc_filter for every path (pass/fail) when collector is active
    arc_paths = [p for p in paths if _is_arc_like(p, collector)]
    line_paths = [p for p in paths if p.item_type == "l"]
    swings: list[_DoorSwing] = []

    for arc in arc_paths:
        radius = max(_bbox_width(arc.bbox), _bbox_height(arc.bbox))
        layer_hint = _layer_hint(arc, DOOR_LAYER_KEYWORDS)
        arc_endpoints = [arc.points[0], arc.points[-1]] if len(arc.points) >= 2 else []
        sweep_est = _estimate_arc_sweep_deg(arc.points, arc.bbox) if arc_endpoints else None
        swing = _DoorSwing(
            source="curve_arc",
            bbox=arc.bbox,
            radius=radius,
            pairing_points=_arc_corners(arc.bbox),
            component_path_indices=[arc.path_index],
            layer=arc.layer,
            layer_hint=layer_hint,
            evidence={
                "arc_source": "curve_arc",
                "arc_bbox_aspect": round(_bbox_width(arc.bbox) / max(_bbox_height(arc.bbox), 1e-6), 3),
                "arc_size_px": round(radius, 1),
                "layer": arc.layer,
                "layer_hint": layer_hint,
                "arc_sweep_est_deg": round(sweep_est, 1) if sweep_est is not None else None,
            },
            arc_endpoints=arc_endpoints,
        )
        if collector:
            swing.debug_id = collector.record_swing(
                "curve_arc", [arc.path_index], radius, sweep_est, arc.layer, layer_hint,
            )
        swings.append(swing)

    # Chained native curves: a door swing drawn as multiple short Beziers
    # (each individually too small to pass _is_arc_like) gets stitched into
    # one logical arc. The fitted-circle radius — not the bbox size — is
    # what matches the leaf length for downstream pairing, because the
    # visible chain may only span a small angular slice of the underlying
    # circle.
    already_used = {id(p) for p in arc_paths}
    remaining_c_paths = [
        p for p in paths if p.item_type == "c" and id(p) not in already_used
    ]
    for chain in _native_curve_chains(remaining_c_paths):
        if len(chain) < DOOR_CURVE_CHAIN_MIN_CURVES:
            continue

        # Find the chain's two natural endpoints (degree-1 in the
        # endpoint-adjacency graph) and confirm it's a simple chain.
        def _snap(point: tuple[float, float]) -> tuple[int, int]:
            return (
                round(point[0] / DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX),
                round(point[1] / DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX),
            )

        endpoint_counts: dict[tuple[int, int], int] = defaultdict(int)
        endpoint_to_actual: dict[tuple[int, int], tuple[float, float]] = {}
        for path in chain:
            if len(path.points) >= 2:
                for pt in (path.points[0], path.points[-1]):
                    key = _snap(pt)
                    endpoint_counts[key] += 1
                    endpoint_to_actual[key] = pt
        end_keys = [k for k, c in endpoint_counts.items() if c == 1]
        if len(end_keys) != 2:
            # Not a simple chain (branches or closed loop) — skip.
            continue
        end_endpoints = [endpoint_to_actual[k] for k in end_keys]

        # Pick three well-separated points across the chain's endpoints for
        # the circle fit (greedy farthest-point heuristic).
        all_points = [endpoint_to_actual[k] for k in endpoint_to_actual]
        if len(all_points) < 3:
            continue
        p1 = all_points[0]
        def _sq_dist(a: tuple[float, float], b: tuple[float, float]) -> float:
            return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2
        p2 = max(all_points, key=lambda p: _sq_dist(p, p1))
        p3 = max(
            all_points,
            key=lambda p: min(_sq_dist(p, p1), _sq_dist(p, p2)),
        )
        fit = _fit_circle_3pt(p1, p2, p3)
        if fit is None:
            continue
        cx, cy, radius = fit
        if not (DOOR_MIN_SIZE_PX <= radius <= DOOR_MAX_SIZE_PX):
            continue

        xs = [b for p in chain for b in (p.bbox[0], p.bbox[2])]
        ys = [b for p in chain for b in (p.bbox[1], p.bbox[3])]
        combined_bbox: BBox = (min(xs), min(ys), max(xs), max(ys))

        layers = [p.layer for p in chain if p.layer]
        layer = layers[0] if layers else None
        layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)

        # For pairing, the natural connection point is the chain's actual
        # end-endpoint nearest the leaf — not a bbox corner. Pass both so
        # _nearest_pair_distance can find the best match.
        pairing_points = _arc_corners(combined_bbox) + list(end_endpoints)

        chain_path_indices = [p.path_index for p in chain]
        swing = _DoorSwing(
            source="curve_arc_chain",
            bbox=combined_bbox,
            radius=radius,
            pairing_points=pairing_points,
            component_path_indices=chain_path_indices,
            layer=layer,
            layer_hint=layer_hint,
            evidence={
                "arc_source": "curve_arc_chain",
                "chain_curve_count": len(chain),
                "fitted_radius": round(radius, 1),
                "fitted_center": (round(cx, 1), round(cy, 1)),
                "combined_bbox": list(combined_bbox),
                "layer": layer,
                "layer_hint": layer_hint,
            },
            arc_endpoints=list(end_endpoints),
        )
        if collector:
            swing.debug_id = collector.record_swing(
                "curve_arc_chain", chain_path_indices, radius, None, layer, layer_hint,
            )
        swings.append(swing)

    arc_bboxes = [a.bbox for a in arc_paths]
    for arc_info in _detect_polyline_arc_bboxes(line_paths, collector):
        bbox = arc_info["bbox"]
        if any(_bboxes_overlap(bbox, _bbox_expanded(ab, DOOR_SWING_LINE_DIST_PX)) for ab in arc_bboxes):
            if collector and "component_id" in arc_info:
                collector.reject_polyline_component(arc_info["component_id"], "overlaps_native_arc")
            continue

        radius = max(_bbox_width(bbox), _bbox_height(bbox))
        layer = arc_info.get("layer")
        layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)
        partner_paths = arc_info.get("double_arc_partner_paths")
        evidence = {
            "arc_source": "polyline_arc",
            "segment_count": arc_info["segment_count"],
            "axis_like_fraction": arc_info["axis_like_fraction"],
            "angle_bin_count": arc_info["angle_bin_count"],
            "layer": layer,
            "layer_hint": layer_hint,
        }
        if partner_paths is not None:
            evidence["double_arc_partner_paths"] = list(partner_paths)
        swing = _DoorSwing(
            source="polyline_arc",
            bbox=bbox,
            radius=radius,
            pairing_points=list(arc_info["endpoints"]),
            component_path_indices=list(arc_info["component_path_indices"]),
            layer=layer,
            layer_hint=layer_hint,
            evidence=evidence,
            arc_endpoints=list(arc_info["endpoints"]),
            double_arc_partner_paths=list(partner_paths) if partner_paths is not None else None,
        )
        if collector:
            swing.debug_id = collector.record_swing(
                "polyline_arc", list(arc_info["component_path_indices"]),
                radius, None, layer, layer_hint,
                polyline_component_id=arc_info.get("component_id"),
            )
        swings.append(swing)

    # Garden-door pairing for single-Bezier `curve_arc` swings (§3.7 analogue).
    # The polyline pipeline already pairs polyline halves via _split_double_arc;
    # this covers the case where each half is a standalone native `c` primitive,
    # which the BFS never joins.
    _detect_curve_arc_double_partners(swings, paths)

    return swings
