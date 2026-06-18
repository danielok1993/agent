from __future__ import annotations
from models import PathPrimitive
from detection.doors.constants import DOOR_HU_CANVAS_SIZE, _DOOR_HU_TEMPLATE_VALUES
try:
    import cv2 as _cv2
    import numpy as _np
    _HU_AVAILABLE = True
except ImportError:
    _HU_AVAILABLE = False


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
