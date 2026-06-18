from __future__ import annotations
import math
from models import BBox, PathPrimitive


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


def _is_line_path(path: PathPrimitive) -> tuple[bool, tuple[float, float], tuple[float, float]]:
    if path.item_type != "l" or len(path.points) < 2:
        return False, (0, 0), (0, 0)
    return True, path.points[0], path.points[-1]


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


def _bbox_expanded(bbox: BBox, px: float) -> BBox:
    return (bbox[0] - px, bbox[1] - px, bbox[2] + px, bbox[3] + px)


def _bboxes_overlap(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _bbox_union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _bbox_area(bbox: BBox) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


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


def _project_onto_axis(
    p: tuple[float, float],
    origin: tuple[float, float],
    dx: float,
    dy: float,
) -> float:
    """Scalar projection of p onto the unit axis (dx, dy) from origin."""
    return (p[0] - origin[0]) * dx + (p[1] - origin[1]) * dy
