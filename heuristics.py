from __future__ import annotations
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from models import PathPrimitive, TextSpan, Candidate, PageData, BBox

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


def _bbox_width(bbox: BBox) -> float:
    return abs(bbox[2] - bbox[0])


def _bbox_height(bbox: BBox) -> float:
    return abs(bbox[3] - bbox[1])


def _point_in_bbox(point: tuple[float, float], bbox: BBox) -> bool:
    return bbox[0] <= point[0] <= bbox[2] and bbox[1] <= point[1] <= bbox[3]


DOOR_LEAF_ASPECT_MIN = 4.0   # door leaf is long and thin, not square

def _is_arc_like(path: PathPrimitive) -> bool:
    # "mixed" never appears after path explosion — each item gets its own kind.
    if path.item_type != "c":
        return False
    w = _bbox_width(path.bbox)
    h = _bbox_height(path.bbox)
    if h < 1e-6:
        return False
    aspect = w / h
    size = max(w, h)
    return (
        DOOR_BBOX_ASPECT_MIN <= aspect <= DOOR_BBOX_ASPECT_MAX
        and DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX
    )


def _is_door_leaf(path: PathPrimitive) -> bool:
    """Return True for re/qu primitives shaped like a door leaf (long and thin)."""
    if path.item_type not in ("re", "qu"):
        return False
    w = _bbox_width(path.bbox)
    h = _bbox_height(path.bbox)
    long_side = max(w, h)
    short_side = min(w, h)
    if short_side < 1e-6:
        return False
    return (
        long_side / short_side >= DOOR_LEAF_ASPECT_MIN
        and DOOR_MIN_SIZE_PX <= long_side <= DOOR_MAX_SIZE_PX
    )


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


def _detect_polyline_arc_bboxes(line_paths: list[PathPrimitive]) -> list[dict]:
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
        if 2.0 <= length <= DOOR_POLYLINE_MAX_SEG_PX:
            segs.append((path, p1, p2, length, _line_angle_deg(p1, p2)))

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

        if not (DOOR_POLYLINE_MIN_SEGMENTS <= len(component) <= DOOR_POLYLINE_MAX_SEGMENTS):
            continue

        points = [pt for idx in component for pt in (segs[idx][1], segs[idx][2])]
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
        w = _bbox_width(bbox)
        h = _bbox_height(bbox)
        if h < 1e-6:
            continue
        aspect = w / h
        size = max(w, h)
        if not (0.65 <= aspect <= 1.45 and DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX):
            continue

        angles = [segs[idx][4] for idx in component]
        axis_like = sum(
            1 for angle in angles
            if min(abs(angle - 0.0), abs(angle - 90.0), abs(angle - 180.0)) <= 8.0
        ) / len(angles)
        if axis_like > 0.35:
            continue

        angle_bins = {int(angle // 15.0) for angle in angles}
        if len(angle_bins) < 4:
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
        if len(endpoint_keys) != 2:
            continue

        endpoints = [
            (
                point_sums[pt_key][0] / point_sums[pt_key][2],
                point_sums[pt_key][1] / point_sums[pt_key][2],
            )
            for pt_key in endpoint_keys
        ]
        layers = [segs[idx][0].layer for idx in component if segs[idx][0].layer]

        arc_infos.append({
            "bbox": bbox,
            "segment_count": len(component),
            "axis_like_fraction": round(axis_like, 3),
            "angle_bin_count": len(angle_bins),
            "endpoints": endpoints,
            "component_path_indices": sorted(segs[idx][0].path_index for idx in component),
            "layer": layers[0] if layers else None,
        })

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


def _layer_hint_from_layer(layer: str | None, keywords: list[str]) -> bool:
    tokens = _layer_tokens(layer)
    return bool(tokens and any(kw in tokens for kw in keywords))


def _collect_door_swings(paths: list[PathPrimitive]) -> list[_DoorSwing]:
    arc_paths = [p for p in paths if _is_arc_like(p)]
    line_paths = [p for p in paths if p.item_type == "l"]
    swings: list[_DoorSwing] = []

    for arc in arc_paths:
        radius = max(_bbox_width(arc.bbox), _bbox_height(arc.bbox))
        layer_hint = _layer_hint(arc, DOOR_LAYER_KEYWORDS)
        swings.append(_DoorSwing(
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
            },
        ))

    arc_bboxes = [a.bbox for a in arc_paths]
    for arc_info in _detect_polyline_arc_bboxes(line_paths):
        bbox = arc_info["bbox"]
        if any(_bboxes_overlap(bbox, _bbox_expanded(ab, DOOR_SWING_LINE_DIST_PX)) for ab in arc_bboxes):
            continue

        radius = max(_bbox_width(bbox), _bbox_height(bbox))
        layer = arc_info.get("layer")
        layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)
        swings.append(_DoorSwing(
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
        ))

    return swings


def _snap_key(point: tuple[float, float], tol: float) -> tuple[int, int]:
    return (round(point[0] / tol), round(point[1] / tol))


def _collect_linework_door_leaves(line_paths: list[PathPrimitive]) -> list[_DoorLeaf]:
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float]]] = []
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

        if not (DOOR_LINEWORK_LEAF_MIN_SEGMENTS <= len(component) <= DOOR_LINEWORK_LEAF_MAX_SEGMENTS):
            continue

        degrees: dict[tuple[int, int], int] = defaultdict(int)
        points: list[tuple[float, float]] = []
        for idx in component:
            _, p1, p2 = segs[idx]
            points.extend([p1, p2])
            degrees[_snap_key(p1, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1
            degrees[_snap_key(p2, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX)] += 1

        if any(degree > 2 for degree in degrees.values()):
            continue
        if not degrees or any(degree != 2 for degree in degrees.values()):
            continue

        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))
        w = _bbox_width(bbox)
        h = _bbox_height(bbox)
        long_side = max(w, h)
        short_side = min(w, h)
        if short_side < 1e-6:
            continue
        if not (
            long_side / short_side >= DOOR_LEAF_ASPECT_MIN
            and DOOR_MIN_SIZE_PX <= long_side <= DOOR_MAX_SIZE_PX
        ):
            continue

        layers = [segs[idx][0].layer for idx in component if segs[idx][0].layer]
        layer = layers[0] if layers else None
        layer_hint = _layer_hint_from_layer(layer, DOOR_LAYER_KEYWORDS)
        component_path_indices = sorted(segs[idx][0].path_index for idx in component)
        leaves.append(_DoorLeaf(
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
        ))

    return leaves


def _collect_door_leaves(paths: list[PathPrimitive]) -> list[_DoorLeaf]:
    leaves: list[_DoorLeaf] = []
    for leaf in (p for p in paths if _is_door_leaf(p)):
        w = _bbox_width(leaf.bbox)
        h = _bbox_height(leaf.bbox)
        long_side = max(w, h)
        layer_hint = _layer_hint(leaf, DOOR_LAYER_KEYWORDS)
        leaves.append(_DoorLeaf(
            source=leaf.item_type,
            bbox=leaf.bbox,
            length=long_side,
            corners=_arc_corners(leaf.bbox),
            component_path_indices=[leaf.path_index],
            layer=leaf.layer,
            layer_hint=layer_hint,
            evidence={
                "leaf_source": leaf.item_type,
                "leaf_size_px": round(long_side, 1),
                "layer": leaf.layer,
                "layer_hint": layer_hint,
            },
        ))

    line_paths = [p for p in paths if p.item_type == "l"]
    leaves.extend(_collect_linework_door_leaves(line_paths))
    return leaves


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
        confidence=DOOR_FALLBACK_CONFIDENCE,
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


def _pair_door_assemblies(
    swings: list[_DoorSwing],
    leaves: list[_DoorLeaf],
    text_spans: list[TextSpan],
) -> list[Candidate]:
    candidates: list[Candidate] = []
    used_swings: set[int] = set()
    used_leaves: set[int] = set()
    cand_idx = 0

    potential_pairs: list[tuple[float, float, int, int]] = []
    for swing_idx, swing in enumerate(swings):
        for leaf_idx, leaf in enumerate(leaves):
            connection_dist = _nearest_pair_distance(swing.pairing_points, leaf.corners)
            if connection_dist > DOOR_ASSEMBLY_CONNECT_TOL_PX:
                continue
            if swing.radius <= 1e-6:
                continue
            radius_ratio = abs(leaf.length - swing.radius) / swing.radius
            if radius_ratio > DOOR_LEAF_RADIUS_RATIO_TOL:
                continue
            potential_pairs.append((connection_dist, radius_ratio, swing_idx, leaf_idx))

    for connection_dist, radius_ratio, swing_idx, leaf_idx in sorted(potential_pairs):
        if swing_idx in used_swings or leaf_idx in used_leaves:
            continue
        swing = swings[swing_idx]
        leaf = leaves[leaf_idx]
        bbox = _bbox_union(swing.bbox, leaf.bbox)
        nearby_label = _find_nearby_label(bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        layer_hint = swing.layer_hint or leaf.layer_hint

        confidence = 0.65
        if nearby_label:
            confidence += 0.20
        if layer_hint:
            confidence += 0.40
        confidence = min(confidence, 0.95)

        component_path_indices = sorted(set(swing.component_path_indices + leaf.component_path_indices))
        evidence = {
            "method": "door_assembly",
            "assembly_type": "single",
            "arc_source": swing.source,
            "arc_bbox": list(swing.bbox),
            "leaf_bbox": list(leaf.bbox),
            "connection_dist_px": round(connection_dist, 2),
            "leaf_radius_ratio": round(radius_ratio, 3),
            "component_path_indices": component_path_indices,
            "nearby_label": nearby_label,
            "layer": swing.layer or leaf.layer,
            "layer_hint": layer_hint,
        }
        evidence.update({f"arc_{k}": v for k, v in swing.evidence.items() if k not in evidence})
        evidence.update({f"leaf_{k}": v for k, v in leaf.evidence.items() if k not in evidence})

        candidates.append(Candidate(
            candidate_id=f"door_{cand_idx:04d}",
            entity_type="door",
            bbox=bbox,
            confidence=round(confidence, 3),
            evidence=evidence,
        ))
        cand_idx += 1
        used_swings.add(swing_idx)
        used_leaves.add(leaf_idx)

    for swing_idx, swing in enumerate(swings):
        if swing_idx in used_swings:
            continue
        nearby_label = _find_nearby_label(swing.bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        evidence = dict(swing.evidence)
        evidence["component_path_indices"] = list(swing.component_path_indices)
        candidates.append(_door_fallback_candidate(
            f"door_{cand_idx:04d}",
            "arc_fallback",
            swing.bbox,
            nearby_label,
            swing.layer,
            swing.layer_hint,
            evidence,
        ))
        cand_idx += 1

    for leaf_idx, leaf in enumerate(leaves):
        if leaf_idx in used_leaves:
            continue
        nearby_label = _find_nearby_label(leaf.bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        evidence = dict(leaf.evidence)
        evidence["component_path_indices"] = list(leaf.component_path_indices)
        candidates.append(_door_fallback_candidate(
            f"door_{cand_idx:04d}",
            "leaf_fallback",
            leaf.bbox,
            nearby_label,
            leaf.layer,
            leaf.layer_hint,
            evidence,
        ))
        cand_idx += 1

    return _dedupe_door_components(candidates)


def detect_doors(paths: list[PathPrimitive], text_spans: list[TextSpan]) -> list[Candidate]:
    swings = _collect_door_swings(paths)
    leaves = _collect_door_leaves(paths)
    return _pair_door_assemblies(swings, leaves, text_spans)


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
) -> list[Candidate]:
    all_stroke_widths = [p.stroke_width for p in page_data.paths if p.stroke_width > 0]

    doors = detect_doors(page_data.paths, page_data.text_spans)
    windows = detect_windows(page_data.paths)
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
