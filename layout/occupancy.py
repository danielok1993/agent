"""Binary ink occupancy map over a page, used to find whitespace gutters."""
from __future__ import annotations

import math
from dataclasses import dataclass

from models import PageData, PathPrimitive
from layout.constants import (
    FRAME_CORNER_TOL_PX, FRAME_NESTED_MIN_CORNERS, SEGMENT_BIN_PX,
    SEGMENT_SPAN_FRAC,
)


@dataclass
class InkMap:
    """bins[row][col] is 1 where drawn ink falls, 0 elsewhere."""
    bins: list[bytearray]
    rows: int
    cols: int
    bin_px: int


def is_page_spanning(
    p: PathPrimitive,
    width_px: float,
    height_px: float,
    span_frac: float = SEGMENT_SPAN_FRAC,
) -> bool:
    """True for sheet furniture: a border rule or column divider that runs the
    length of the page. Tested per-axis, not by area — a 3508x1px border line
    has a negligible bbox area but blocks every vertical gutter."""
    return (
        (p.bbox[2] - p.bbox[0]) > span_frac * width_px
        or (p.bbox[3] - p.bbox[1]) > span_frac * height_px
    )


def _is_unfilled_rect(p: PathPrimitive) -> bool:
    return p.item_type in ("re", "qu") and p.fill is None and len(p.points) == 4


def nested_frame_indices(
    page_data: PageData,
    tol: float = FRAME_CORNER_TOL_PX,
    min_corners: int = FRAME_NESTED_MIN_CORNERS,
) -> set[int]:
    """Path indices of nested sheet furniture: unfilled rectangles with at
    least min_corners corners on the page frame's boundary.

    The page frame is what is_page_spanning already treats as furniture — a
    page-spanning unfilled rectangle contributes its four edges, a
    page-spanning rule contributes itself. A drawing frame or title-block
    partition is drawn against that frame, so three of its corners land on
    it (the fourth is where the partition turns inward); a drawing box that
    merely hugs one border shares two corners and stays content. See
    FRAME_NESTED_MIN_CORNERS for the s06 measurement. One level only — no
    propagation from nested furniture to further rectangles or free lines.
    """
    w, h = page_data.width_px, page_data.height_px
    segs: list[tuple[float, float, float, float]] = []
    for p in page_data.paths:
        if not is_page_spanning(p, w, h) or p.fill is not None:
            continue
        x0, y0, x1, y1 = p.bbox
        if p.item_type in ("re", "qu"):
            segs += [(x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)]
        elif p.item_type == "l" and len(p.points) >= 2:
            (a, b), (c, d) = p.points[0], p.points[-1]
            segs.append((a, b, c, d))
    if not segs:
        return set()

    def on_boundary(x: float, y: float) -> bool:
        for a, b, c, d in segs:
            if abs(a - c) <= tol:        # vertical
                if abs(x - a) <= tol and min(b, d) - tol <= y <= max(b, d) + tol:
                    return True
            elif abs(b - d) <= tol:      # horizontal
                if abs(y - b) <= tol and min(a, c) - tol <= x <= max(a, c) + tol:
                    return True
        return False

    out: set[int] = set()
    for p in page_data.paths:
        if not _is_unfilled_rect(p) or is_page_spanning(p, w, h):
            continue
        x0, y0, x1, y1 = p.bbox
        corners = ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
        if sum(on_boundary(x, y) for x, y in corners) >= min_corners:
            out.add(p.path_index)
    return out


def path_length(p: PathPrimitive) -> float:
    """Total drawn length: the polyline through the points, closed for re/qu."""
    pts = p.points
    if len(pts) < 2:
        return 0.0
    if p.item_type == "qu" and len(pts) == 4:
        pts = [pts[0], pts[1], pts[3], pts[2]]
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    if p.item_type in ("re", "qu") and len(pts) >= 3:
        total += math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    return total


def build_ink_map(
    page_data: PageData,
    bin_px: int = SEGMENT_BIN_PX,
    include_text: bool = True,
    min_path_len: float = 0.0,
) -> InkMap:
    cols = int(page_data.width_px / bin_px) + 1
    rows = int(page_data.height_px / bin_px) + 1
    bins = [bytearray(cols) for _ in range(rows)]

    def plot(x: float, y: float) -> None:
        c, r = int(x / bin_px), int(y / bin_px)
        if 0 <= r < rows and 0 <= c < cols:
            bins[r][c] = 1

    def segment(p0: tuple[float, float], p1: tuple[float, float]) -> None:
        (x0, y0), (x1, y1) = p0, p1
        steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / bin_px) + 1)
        for i in range(steps + 1):
            t = i / steps
            plot(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    nested = nested_frame_indices(page_data)
    for p in page_data.paths:
        if is_page_spanning(p, page_data.width_px, page_data.height_px):
            continue
        if p.path_index in nested:
            continue
        # min_path_len > 0 builds the LONG-ink map for tier-3 gutters
        # (segmenter._short_ink_gutter): annotation pieces up to that length
        # are left out so a band they alone cross reads as empty.
        if min_path_len > 0.0 and path_length(p) <= min_path_len:
            continue
        pts = p.points
        # A `qu` item's points arrive in PyMuPDF Quad order — [ul, ur, ll,
        # lr] — not perimeter order; the perimeter is [0, 1, 3, 2] for every
        # quad, skewed ones included (detection/walls.py reorders the same
        # way before ring-building). Joined sequentially, a quad inked two
        # DIAGONALS across its interior instead of its top and bottom edges:
        # measured on s06, the 2344x1544px drawing frame (path 4849) drew two
        # page-wide diagonals through every drawing on the sheet, and its
        # elevations and plans never split at their gutters.
        if p.item_type == "qu" and len(pts) == 4:
            pts = [pts[0], pts[1], pts[3], pts[2]]
        if len(pts) >= 2:
            for a, b in zip(pts, pts[1:]):
                segment(a, b)
            # `re`/`qu` runs list corners without repeating the first point.
            if p.item_type in ("re", "qu") and len(pts) >= 3:
                segment(pts[-1], pts[0])
        elif pts:
            plot(*pts[0])

    if include_text:
        for t in page_data.text_spans:
            x0, y0, x1, y1 = t.bbox
            for r in range(int(y0 / bin_px), int(y1 / bin_px) + 1):
                for c in range(int(x0 / bin_px), int(x1 / bin_px) + 1):
                    if 0 <= r < rows and 0 <= c < cols:
                        bins[r][c] = 1

    return InkMap(bins=bins, rows=rows, cols=cols, bin_px=bin_px)
