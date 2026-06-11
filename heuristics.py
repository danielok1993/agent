from __future__ import annotations
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from models import PathPrimitive, TextSpan, Candidate, PageData, BBox
from debug_trace import DebugTraceCollector

try:
    import cv2 as _cv2
    import numpy as _np
    _HU_AVAILABLE = True
except ImportError:
    _HU_AVAILABLE = False

# ---------------------------------------------------------------------------
# Door detection constants
# ---------------------------------------------------------------------------
DOOR_BBOX_ASPECT_MIN        = 0.85   # width/height ratio (roughly square arc)
DOOR_BBOX_ASPECT_MAX        = 1.15
DOOR_MIN_SIZE_PX            = 20.0
DOOR_MAX_SIZE_PX            = 200.0
DOOR_SWING_LINE_DIST_PX     = 15.0  # max px from arc corner to nearby line endpoint
DOOR_LABEL_PATTERN          = re.compile(r"(?i)^[A-Z]?[FD]-?\d{1,3}[A-Z]?$")
DOOR_LABEL_SEARCH_RADIUS_PX = 100.0
DOOR_MIN_CONFIDENCE         = 0.40
DOOR_POLYLINE_MIN_SEGMENTS  = 4
DOOR_POLYLINE_MAX_SEGMENTS  = 24
DOOR_POLYLINE_MAX_SEG_PX    = 18.0
DOOR_POLYLINE_ENDPOINT_TOL  = 2.0
DOOR_LAYER_KEYWORDS         = ["door", "a-door"]
DOOR_ASSEMBLY_CONNECT_TOL_PX = 15.0
DOOR_LEAF_RADIUS_RATIO_TOL   = 0.20
DOOR_FALLBACK_CONFIDENCE     = 0.35
DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX = 3.0
DOOR_LINEWORK_LEAF_MIN_SEGMENTS    = 4
DOOR_LINEWORK_LEAF_MAX_SEGMENTS    = 8
# Subgraph-fallback bound: components larger than the clean-loop ceiling but still
# small enough to enumerate 4-cycles inside. Captures a leaf rectangle with a few
# attached spurs (typically a threshold line and/or 1-2 wall stubs).
DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS = 14
DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG          = 8.0   # opposite-side ∥ tolerance for thin-rectangle 4-cycle
DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG     = 12.0  # adjacent-side ⟂ tolerance for thin-rectangle 4-cycle
DOOR_THRESHOLD_ENDPOINT_TOL_PX            = 6.0   # threshold endpoint ↔ leaf long-edge corner snap tol
DOOR_THRESHOLD_PARALLEL_TOL_DEG           = 8.0   # threshold direction ‖ leaf long axis
DOOR_THRESHOLD_CONFIDENCE_BOOST           = 0.10  # confirmatory boost when an entrance threshold is found
DOOR_POLYLINE_MAX_ANGLE_BINS              = 7     # quarter-circle spans ≤7 bins of 15°; rejects furniture/appliance curves
DOOR_DOUBLE_LEAF_GAP_PX                  = 12.0  # max gap between leaf long-axis intervals to form a double door
DOOR_DOUBLE_LEAF_OVERLAP_PX              =  5.0  # max overlap tolerated on leaf long-axis intervals
DOOR_DOUBLE_LEAF_CENTER_TOL_PX           =  8.0  # max offset between leaf long-axis centerlines
DOOR_V2_BRIDGE_BUFFER_PX          = 3.0   # max dist from bridge line for an obstructing segment
DOOR_V2_OPENING_CLEAR_BOOST       = 0.07  # confidence boost when verified-clear door opening
DOOR_V2_OPENING_OBSTRUCTED_PENALTY = 0.12  # confidence penalty when opening has crossing lines

# ---------------------------------------------------------------------------
# Hu Moments constants (Step 4 of v2 spec)
# Template derived from 4 confirmed door arcs in floor-plans.pdf page 1.
# 6 moments only — moment 7 flips sign with arc reflection orientation.
# ---------------------------------------------------------------------------
DOOR_HU_CANVAS_SIZE         = 64    # rasterize candidate arc to this square canvas
DOOR_HU_THRESHOLD_VERIFIED  = 0.15  # distance < this → strong shape match
DOOR_HU_THRESHOLD_FAR       = 0.50  # distance > this → penalize
DOOR_HU_VERIFIED_BOOST      = 0.20  # rescues arc_fallback from 0.35 → 0.55
DOOR_HU_PLAUSIBLE_BOOST     = 0.08  # plausible match
DOOR_HU_FAR_PENALTY         = 0.10  # poor match
_DOOR_HU_TEMPLATE_VALUES    = [1.518423, 3.112955, 5.232975, 6.148173, -9.994192, -7.721678]

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
WINDOW_HATCH_REJECT_MIN     = 5
WINDOW_HATCH_REJECT_RATIO   = 0.45

# ---------------------------------------------------------------------------
# Label detection constants
# ---------------------------------------------------------------------------
LABEL_PATTERN               = re.compile(r"(?i)^[A-Z]{1,4}-?\d{1,4}[A-Z]?$")
LABEL_MAX_FONT_SIZE_PT      = 14.0
LABEL_MIN_FONT_SIZE_PT      = 4.0
LABEL_SEARCH_RADIUS_PX      = 80.0

# ---------------------------------------------------------------------------
# Schedule detection constants
# ---------------------------------------------------------------------------
SCHEDULE_TABLE_MIN_ROWS     = 3
SCHEDULE_TABLE_MIN_COLS     = 2
SCHEDULE_MIN_CELL_DENSITY   = 0.15
SCHEDULE_KEYWORDS           = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|mark|width|height)"
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _bbox_center(bbox: BBox) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _line_length(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return _distance(p1, p2)


def _line_angle_deg(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx)) % 180.0


def _angle_diff_mod180(a: float, b: float) -> float:
    """Smaller angular distance between two directions, both already mod 180°."""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _bbox_width(bbox: BBox) -> float:
    return abs(bbox[2] - bbox[0])


def _bbox_height(bbox: BBox) -> float:
    return abs(bbox[3] - bbox[1])


def _point_in_bbox(point: tuple[float, float], bbox: BBox) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


DOOR_LEAF_ASPECT_MIN = 4.0   # door leaf is long and thin, not square

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


def _is_line_path(path: PathPrimitive) -> tuple[bool, tuple[float, float], tuple[float, float]]:
    if path.item_type != "l" or len(path.points) < 2:
        return False, (0, 0), (0, 0)
    return True, path.points[0], path.points[-1]


def _arc_corners(bbox: BBox) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = bbox
    return [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]


def _point_to_segment_distance(
    p: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    """Minimum distance from point p to line segment ab."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return _distance(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len_sq))
    closest = (a[0] + t * dx, a[1] + t * dy)
    return _distance(p, closest)


def _segments_min_distance(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
) -> float:
    """Minimum distance between two line segments."""
    return min(
        _point_to_segment_distance(a1, b1, b2),
        _point_to_segment_distance(a2, b1, b2),
        _point_to_segment_distance(b1, a1, a2),
        _point_to_segment_distance(b2, a1, a2),
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
                collector.record_polyline_component(comp_path_indices, "rejected", "segment_count_out_of_range", checks)
            continue

        points = [pt for idx in component for pt in (segs[idx][1], segs[idx][2])]
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
        w = _bbox_width(bbox)
        h = _bbox_height(bbox)
        if h < 1e-6:
            if collector:
                collector.record_polyline_component(comp_path_indices, "rejected", "bbox_degenerate", checks)
            continue
        aspect = w / h
        size = max(w, h)
        checks["bbox_aspect"] = {"value": round(aspect, 4), "range": [0.65, 1.45], "passed": 0.65 <= aspect <= 1.45}
        checks["size_px"] = {"value": round(size, 2), "range": [DOOR_MIN_SIZE_PX, DOOR_MAX_SIZE_PX], "passed": DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX}
        if not (0.65 <= aspect <= 1.45 and DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX):
            fail = "bbox_aspect" if not (0.65 <= aspect <= 1.45) else "size_out_of_range"
            if collector:
                collector.record_polyline_component(comp_path_indices, "rejected", fail, checks)
            continue

        angles = [segs[idx][4] for idx in component]
        axis_like = sum(
            1 for angle in angles
            if min(abs(angle - 0.0), abs(angle - 90.0), abs(angle - 180.0)) <= 8.0
        ) / len(angles)
        checks["axis_like_fraction"] = {"value": round(axis_like, 3), "max": 0.35, "passed": axis_like <= 0.35}
        if axis_like > 0.35:
            if collector:
                collector.record_polyline_component(comp_path_indices, "rejected", "axis_like_fraction", checks)
            continue

        angle_bins = {int(angle // 15.0) for angle in angles}
        checks["angle_bin_count"] = {"value": len(angle_bins), "range": [4, DOOR_POLYLINE_MAX_ANGLE_BINS], "passed": 4 <= len(angle_bins) <= DOOR_POLYLINE_MAX_ANGLE_BINS}
        if not (4 <= len(angle_bins) <= DOOR_POLYLINE_MAX_ANGLE_BINS):
            if collector:
                collector.record_polyline_component(comp_path_indices, "rejected", "angle_bin_count", checks)
            continue

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
                collector.record_polyline_component(comp_path_indices, "rejected", "endpoint_count", checks)
            continue

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
        if collector:
            cid = collector.record_polyline_component(comp_path_indices, "collected", None, checks)
            arc_info["component_id"] = cid
        arc_infos.append(arc_info)

    return arc_infos


_LAYER_TOKEN_RE = re.compile(r"[\W_]+")


def _layer_tokens(layer: str | None) -> set[str]:
    if not layer:
        return set()
    return set(_LAYER_TOKEN_RE.split(layer.lower()))


def _layer_hint(path: PathPrimitive, keywords: list[str]) -> bool:
    """Return True if any keyword is an exact token in the layer name.

    Token-splits on non-word characters so "a-wind" matches "wind" but
    "window-frame-notes" does not false-match on bare substring "win".
    """
    tokens = _layer_tokens(path.layer)
    return bool(tokens and any(kw in tokens for kw in keywords))


def _layer_strong_prior(path: PathPrimitive, keywords: list[str]) -> float:
    """Return a high confidence boost when a layer name conclusively names the type.

    Only applied when the layer is non-empty and contains a matching token.
    Returns 0.0 when no layer data is available so it is a no-op on documents
    without OCG layers.
    """
    if not path.layer:
        return 0.0
    return 0.40 if _layer_hint(path, keywords) else 0.0


def _bbox_expanded(bbox: BBox, px: float) -> BBox:
    return (bbox[0] - px, bbox[1] - px, bbox[2] + px, bbox[3] + px)


def _bboxes_overlap(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _bbox_union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


# ---------------------------------------------------------------------------
# Door detection
# ---------------------------------------------------------------------------

@dataclass
class _DoorSwing:
    source: str
    bbox: BBox
    radius: float
    pairing_points: list[tuple[float, float]]
    component_path_indices: list[int]
    layer: str | None
    layer_hint: bool
    evidence: dict
    arc_endpoints: list[tuple[float, float]]   # actual arc start/end points for bridge-line check
    debug_id: str | None = None               # set by DebugTraceCollector when active


@dataclass
class _DoorLeaf:
    source: str
    bbox: BBox
    length: float
    corners: list[tuple[float, float]]
    component_path_indices: list[int]
    layer: str | None
    layer_hint: bool
    evidence: dict
    debug_id: str | None = None               # set by DebugTraceCollector when active


def _layer_hint_from_layer(layer: str | None, keywords: list[str]) -> bool:
    tokens = _layer_tokens(layer)
    return bool(tokens and any(kw in tokens for kw in keywords))


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
        swing = _DoorSwing(
            source="polyline_arc",
            bbox=bbox,
            radius=radius,
            pairing_points=list(arc_info["endpoints"]),
            component_path_indices=list(arc_info["component_path_indices"]),
            layer=layer,
            layer_hint=layer_hint,
            evidence={
                "arc_source": "polyline_arc",
                "segment_count": arc_info["segment_count"],
                "axis_like_fraction": arc_info["axis_like_fraction"],
                "angle_bin_count": arc_info["angle_bin_count"],
                "layer": layer,
                "layer_hint": layer_hint,
            },
            arc_endpoints=list(arc_info["endpoints"]),
        )
        if collector:
            swing.debug_id = collector.record_swing(
                "polyline_arc", list(arc_info["component_path_indices"]),
                radius, None, layer, layer_hint,
                polyline_component_id=arc_info.get("component_id"),
            )
        swings.append(swing)

    return swings


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


def _rasterize_paths_to_canvas(
    paths: list[PathPrimitive],
    canvas_size: int = DOOR_HU_CANVAS_SIZE,
) -> object | None:
    """Rasterize line/curve primitives onto a normalized binary canvas.

    Segments are scaled so their bounding box fills the canvas minus a small
    margin, making the output scale-invariant. Returns a uint8 numpy array
    or None if cv2 is unavailable or the geometry is degenerate.
    """
    if not _HU_AVAILABLE:
        return None
    segs = []
    for path in paths:
        if path.item_type in ("l", "c") and len(path.points) >= 2:
            segs.append((path.points[0], path.points[-1]))
    if not segs:
        return None
    all_pts = [pt for seg in segs for pt in seg]
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    if span < 1e-6:
        return None
    x0, y0 = min(xs), min(ys)
    margin = 4
    scale = (canvas_size - 2 * margin) / span
    img = _np.zeros((canvas_size, canvas_size), dtype=_np.uint8)
    for p1, p2 in segs:
        cx1 = int((p1[0] - x0) * scale) + margin
        cy1 = int((p1[1] - y0) * scale) + margin
        cx2 = int((p2[0] - x0) * scale) + margin
        cy2 = int((p2[1] - y0) * scale) + margin
        _cv2.line(img, (cx1, cy1), (cx2, cy2), 255, 1)
    return img


def _compute_hu_distance(paths: list[PathPrimitive]) -> float | None:
    """Distance between candidate arc paths and the door Hu Moment template.

    Lower values mean the shape is more door-like. Uses the first 6 log-
    transformed Hu Moments (moment 7 is omitted — it flips sign under arc
    reflection and averages to ~0 across orientations).

    Returns None when cv2 is unavailable or rasterization fails.
    """
    if not _HU_AVAILABLE:
        return None
    img = _rasterize_paths_to_canvas(paths)
    if img is None:
        return None
    m = _cv2.moments(img)
    hu = _cv2.HuMoments(m).flatten()
    hu_log = -_np.sign(hu) * _np.log10(_np.abs(hu) + 1e-10)
    template = _np.array(_DOOR_HU_TEMPLATE_VALUES)
    return float(_np.linalg.norm(hu_log[:6] - template))


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
        # v2: bridge-line opening check (Wall Break Condition)
        opening_check = "unknown"
        if swing.arc_endpoints and len(swing.arc_endpoints) == 2:
            opening_check = _check_opening_clear(
                swing.arc_endpoints, line_paths, set(component_path_indices)
            )
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
            "nearby_label": nearby_label,
            "layer": swing.layer or leaf.layer,
            "layer_hint": layer_hint,
            "opening_check": opening_check,
        }
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
            arc_conf = round(min(max(arc_conf, 0.0), 0.95), 3)

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
    """
    import re as _re
    assemblies = [
        (i, c) for i, c in enumerate(candidates)
        if c.entity_type == "door" and c.evidence.get("method") == "door_assembly"
    ]

    scored_pairs: list[tuple[float, int, int]] = []  # (abs_signed_gap, idx_i, idx_j)
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

        scored_pairs.append((abs(signed_gap), pi, pj))

    if not scored_pairs:
        return candidates

    # Greedy one-to-one match: tightest leaf fit wins; each candidate used at most once
    scored_pairs.sort()
    used: set[int] = set()
    merges: list[tuple[int, int]] = []
    for _, pi, pj in scored_pairs:
        if pi in used or pj in used:
            continue
        merges.append((pi, pj))
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

    for pi, pj in merges:
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


def detect_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None = None,
) -> list[Candidate]:
    if collector:
        collector.init_primitives(paths)
    swings = _collect_door_swings(paths, collector)
    leaves = _collect_door_leaves(paths, collector)
    candidates = _pair_door_assemblies(swings, leaves, text_spans, paths, collector)
    return _merge_double_door_assemblies(candidates)


# ---------------------------------------------------------------------------
# Window detection
# ---------------------------------------------------------------------------

def _projected_interval(
    p1: tuple[float, float],
    p2: tuple[float, float],
    ux: float,
    uy: float,
    origin: tuple[float, float],
) -> tuple[float, float]:
    """Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars."""
    t1 = _project_onto_axis(p1, origin, ux, uy)
    t2 = _project_onto_axis(p2, origin, ux, uy)
    return (min(t1, t2), max(t1, t2))


def _interval_overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


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


def _perpendicular_spacing(
    p1: tuple[float, float], p2: tuple[float, float],
    q1: tuple[float, float], q2: tuple[float, float],
) -> float:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return float("inf")
    nx, ny = -dy / length, dx / length
    return abs((q1[0] - p1[0]) * nx + (q1[1] - p1[1]) * ny)


# ---------------------------------------------------------------------------
# Collinear segment merging (used by wall detection)
# ---------------------------------------------------------------------------

# Tolerance for two segments to be considered on the same line.
COLLINEAR_ANGLE_TOL    = 3.0   # degrees
COLLINEAR_OFFSET_TOL   = 4.0   # px perpendicular distance between lines
COLLINEAR_GAP_MAX_PX   = 30.0  # max endpoint gap to bridge (door/window openings)


def _project_onto_axis(
    p: tuple[float, float],
    origin: tuple[float, float],
    dx: float,
    dy: float,
) -> float:
    """Scalar projection of p onto the unit axis (dx, dy) from origin."""
    return (p[0] - origin[0]) * dx + (p[1] - origin[1]) * dy


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


# ---------------------------------------------------------------------------
# Wall detection
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Label detection
# ---------------------------------------------------------------------------

def _find_nearby_label(
    bbox: BBox,
    text_spans: list[TextSpan],
    radius: float,
    pattern: re.Pattern,
) -> str | None:
    cx, cy = _bbox_center(bbox)
    best = None
    best_dist = float("inf")
    for span in text_spans:
        if not pattern.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue
        scx, scy = _bbox_center(span.bbox)
        d = _distance((cx, cy), (scx, scy))
        if d <= radius and d < best_dist:
            best_dist = d
            best = span.text
    return best


def detect_labels(text_spans: list[TextSpan], candidates: list[Candidate]) -> list[Candidate]:
    """Detect architectural labels (e.g. D-01, W-03) near geometric candidates.

    Requires the span to match the label pattern AND to be within
    LABEL_SEARCH_RADIUS_PX of a geometric candidate. Confidence scales with
    proximity: close labels are more likely to tag the adjacent element.
    Spans that match the pattern but have no nearby candidate are dropped to
    avoid promoting dimension callouts (300, 150, etc.) that have no element
    within radius.
    """
    label_candidates = []
    cand_idx = 0
    for span in text_spans:
        if not LABEL_PATTERN.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue

        nearest_id = None
        nearest_dist = float("inf")
        for c in candidates:
            d = _distance(_bbox_center(span.bbox), _bbox_center(c.bbox))
            if d < nearest_dist:
                nearest_dist = d
                nearest_id = c.candidate_id

        # Only emit if a geometric candidate is within the search radius
        if nearest_dist > LABEL_SEARCH_RADIUS_PX:
            continue

        # Confidence: 0.80 at distance 0, falls linearly to 0.50 at radius edge
        proximity = 1.0 - (nearest_dist / LABEL_SEARCH_RADIUS_PX)
        confidence = round(0.50 + 0.30 * proximity, 3)

        label_candidates.append(Candidate(
            candidate_id=f"label_{cand_idx:04d}",
            entity_type="label",
            bbox=span.bbox,
            confidence=confidence,
            evidence={
                "text": span.text,
                "font": span.font,
                "size": span.size,
                "nearest_candidate": nearest_id,
                "nearest_dist_px": round(nearest_dist, 1),
            },
        ))
        cand_idx += 1

    return label_candidates


# ---------------------------------------------------------------------------
# Schedule detection
# ---------------------------------------------------------------------------

SCHEDULE_KEYWORDS_RE = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|type|mark)"
)


def detect_schedules(
    text_spans: list[TextSpan],
    plumber_tables: list[list[list[str | None]]],
) -> list[Candidate]:
    candidates = []
    cand_idx = 0

    for table in plumber_tables:
        if len(table) < SCHEDULE_TABLE_MIN_ROWS:
            continue
        max_cols = max((len(row) for row in table), default=0)
        if max_cols < SCHEDULE_TABLE_MIN_COLS:
            continue

        total_cells = sum(len(row) for row in table)
        non_empty = sum(1 for row in table for cell in row if cell and str(cell).strip())
        density = non_empty / total_cells if total_cells > 0 else 0
        if density < SCHEDULE_MIN_CELL_DENSITY:
            continue

        all_text = " ".join(
            str(cell) for row in table for cell in row if cell
        )
        is_schedule = bool(SCHEDULE_KEYWORDS_RE.search(all_text))
        confidence = 0.60 if is_schedule else 0.35

        candidates.append(Candidate(
            candidate_id=f"schedule_{cand_idx:04d}",
            entity_type="schedule",
            bbox=(0, 0, 0, 0),  # pdfplumber tables don't always have bbox
            confidence=round(confidence, 3),
            evidence={
                "rows": len(table),
                "cols": max_cols,
                "cell_density": round(density, 3),
                "is_schedule_keyword": is_schedule,
                "sample_text": all_text[:200],
            },
        ))
        cand_idx += 1

    return candidates


# ---------------------------------------------------------------------------
# Cross-element validation (soft: boost/penalize confidence)
# ---------------------------------------------------------------------------

CROSS_WALL_EXPAND_PX  = 20.0   # expand wall bbox when checking containment
CROSS_NO_WALL_PENALTY = 0.08   # door/window has no wall nearby → penalty
CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY = 0.04
# No in-wall boost: wall and window candidates share the same raw linework,
# so overlap is structural correlation, not independent evidence.


def _cross_validate(
    candidates: list[Candidate],
    walls: list[Candidate],
) -> list[Candidate]:
    """Soft-penalize doors/windows that have no nearby wall candidate.

    A door or window with no wall anywhere close is likely a false positive
    (an arc or parallel-line cluster in a legend, annotation, or detail).
    True openings always sit in a wall, so the absence of any overlapping wall
    is a reliable negative signal. We do not apply a positive boost when a wall
    is found because wall and window candidates are derived from the same raw
    linework — overlap is geometric correlation, not independent evidence.
    """
    if not walls:
        return candidates

    wall_bboxes = [_bbox_expanded(w.bbox, CROSS_WALL_EXPAND_PX) for w in walls]

    adjusted = []
    for c in candidates:
        if c.entity_type not in ("door", "window"):
            adjusted.append(c)
            continue

        in_wall = any(_bboxes_overlap(c.bbox, wb) for wb in wall_bboxes)
        penalty = (
            CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY
            if c.entity_type == "door" and c.evidence.get("method") == "door_assembly"
            else CROSS_NO_WALL_PENALTY
        )
        delta = 0.0 if in_wall else -penalty
        new_conf = round(min(max(c.confidence + delta, 0.0), 0.95), 3)

        new_evidence = dict(c.evidence)
        new_evidence["wall_context"] = "in_wall" if in_wall else "no_wall"

        adjusted.append(Candidate(
            candidate_id=c.candidate_id,
            entity_type=c.entity_type,
            bbox=c.bbox,
            confidence=new_conf,
            evidence=new_evidence,
        ))

    return adjusted


# ---------------------------------------------------------------------------
# Type-specific NMS
# ---------------------------------------------------------------------------

NMS_IOU_THRESHOLD     = 0.50
NMS_CENTER_DIST_PX    = 15.0   # suppress if centers are this close regardless of IoU


def _bbox_area(bbox: BBox) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _bbox_iou(a: BBox, b: BBox) -> float:
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter == 0.0:
        return 0.0
    union = _bbox_area(a) + _bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def _projected_overlap_1d(a: BBox, b: BBox) -> tuple[float, float]:
    """Projected overlap fraction and perpendicular gap on bbox a's dominant axis.

    Returns (overlap_fraction, perp_gap_px):
      overlap_fraction — fraction of the shorter interval covered on dominant axis
      perp_gap_px      — gap between the two bboxes on the *perpendicular* axis
                         (0 if they overlap perpendicularly, positive if separated)
    """
    aw = _bbox_width(a)
    ah = _bbox_height(a)
    bw = _bbox_width(b)
    bh = _bbox_height(b)

    if aw >= ah:   # a is horizontal → dominant axis = x, perpendicular = y
        lo = max(a[0], b[0]); hi = min(a[2], b[2])
        shorter = min(aw, bw)
        perp_lo = max(a[1], b[1]); perp_hi = min(a[3], b[3])
    else:          # a is vertical   → dominant axis = y, perpendicular = x
        lo = max(a[1], b[1]); hi = min(a[3], b[3])
        shorter = min(ah, bh)
        perp_lo = max(a[0], b[0]); perp_hi = min(a[2], b[2])

    overlap = max(0.0, hi - lo)
    frac = overlap / shorter if shorter > 0 else 0.0
    perp_gap = max(0.0, perp_lo - perp_hi)
    return frac, perp_gap


# Max perpendicular separation for the projected-overlap NMS rule to fire.
# Two walls at the same x-range but 500 px apart in y are not duplicates.
NMS_PROJ_PERP_MAX_PX = 40.0


def _suppress(candidates: list[Candidate]) -> list[Candidate]:
    """Type-specific NMS: higher confidence wins when two candidates overlap.

    For skinny wall/window boxes plain IoU can be low even when boxes nearly
    coincide. The projected-overlap rule is applied only when the perpendicular
    gap is small (≤ NMS_PROJ_PERP_MAX_PX), preventing two parallel walls at
    different rows/columns from collapsing into one.
    """
    candidates = _dedupe_door_components(candidates)

    by_type: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_type.setdefault(c.entity_type, []).append(c)

    kept: list[Candidate] = []
    for etype, group in by_type.items():
        group = sorted(group, key=lambda c: c.confidence, reverse=True)
        suppressed = set()

        for i, ci in enumerate(group):
            if i in suppressed:
                continue
            for j, cj in enumerate(group):
                if j <= i or j in suppressed:
                    continue
                iou = _bbox_iou(ci.bbox, cj.bbox)
                center_dist = _distance(_bbox_center(ci.bbox), _bbox_center(cj.bbox))
                proj, perp_gap = _projected_overlap_1d(ci.bbox, cj.bbox)

                directional = etype in ("wall", "window")
                same_orientation = (
                    (_bbox_width(ci.bbox) >= _bbox_height(ci.bbox)) ==
                    (_bbox_width(cj.bbox) >= _bbox_height(cj.bbox))
                )
                # Center distance alone is not enough for directional types:
                # a horizontal wall crossing a vertical wall shares a center
                # but is a distinct element and must not be suppressed.
                center_suppresses = (
                    center_dist <= NMS_CENTER_DIST_PX
                    and (not directional or same_orientation)
                )

                if (
                    iou >= NMS_IOU_THRESHOLD
                    or center_suppresses
                    or (
                        directional
                        and proj >= 0.80
                        and perp_gap <= NMS_PROJ_PERP_MAX_PX
                        and same_orientation
                    )
                ):
                    suppressed.add(j)

        kept.extend(c for k, c in enumerate(group) if k not in suppressed)

    return kept


def _bbox_is_horizontal(bbox: BBox) -> bool:
    return _bbox_width(bbox) >= _bbox_height(bbox)


def _resolve_wall_window_conflicts(candidates: list[Candidate]) -> list[Candidate]:
    """Drop window candidates that are materially the same bbox as a wall.

    Real windows overlap walls, but their detected glazing/slab linework should
    not usually have almost the same bbox as the detected wall band. When that
    happens, especially on hatched wall bands, the window was usually created by
    the generic parallel-line grouping rather than by an actual opening.
    """
    walls = [c for c in candidates if c.entity_type == "wall"]
    if not walls:
        return candidates

    resolved: list[Candidate] = []
    for candidate in candidates:
        if candidate.entity_type != "window" or candidate.evidence.get("layer_hint"):
            resolved.append(candidate)
            continue

        duplicate_wall = False
        for wall in walls:
            if _bbox_is_horizontal(candidate.bbox) != _bbox_is_horizontal(wall.bbox):
                continue
            if _bbox_iou(candidate.bbox, wall.bbox) < 0.45:
                continue
            if wall.evidence.get("wall_material") or wall.confidence >= candidate.confidence:
                duplicate_wall = True
                break

        if not duplicate_wall:
            resolved.append(candidate)

    return resolved


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

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


def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
    disable_walls: bool = False,
    disable_windows: bool = False,
    collector: DebugTraceCollector | None = None,
) -> list[Candidate]:
    all_stroke_widths = [p.stroke_width for p in page_data.paths if p.stroke_width > 0]

    doors = detect_doors(page_data.paths, page_data.text_spans, collector)
    windows = [] if disable_windows else detect_windows(page_data.paths)
    walls = [] if disable_walls else detect_walls(page_data.paths)

    # Annotate wall candidates with relative stroke-width evidence
    for w in walls:
        material = _wall_material_evidence(page_data.paths, w.bbox)
        w.evidence.update(material)
        if material["wall_material"]:
            w.confidence = round(min(w.confidence + 0.10, 0.90), 3)

        layer = w.evidence.get("layer")
        matching = [
            p for p in page_data.paths
            if p.item_type == "l" and p.layer == layer
        ]
        if matching:
            avg_sw = statistics.mean(p.stroke_width for p in matching)
            w.evidence["stroke_percentile"] = round(
                _stroke_percentile_rank(avg_sw, all_stroke_widths), 3
            )

    filtered_windows: list[Candidate] = []
    for window in windows:
        material = _wall_material_evidence(page_data.paths, window.bbox)
        window.evidence.update(material)
        if (
            not window.evidence.get("layer_hint")
            and material["hatch_count"] >= WINDOW_HATCH_REJECT_MIN
            and material["hatch_ratio"] >= WINDOW_HATCH_REJECT_RATIO
        ):
            continue
        filtered_windows.append(window)
    windows = filtered_windows

    all_geo = _cross_validate(doors + windows, walls) + walls
    all_geo = _suppress(all_geo)
    all_geo = _resolve_wall_window_conflicts(all_geo)

    labels = detect_labels(page_data.text_spans, all_geo)
    schedules = detect_schedules(page_data.text_spans, plumber_tables)

    return _suppress(_resolve_wall_window_conflicts(all_geo + labels + schedules))
