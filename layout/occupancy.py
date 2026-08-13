"""Binary ink occupancy map over a page, used to find whitespace gutters."""
from __future__ import annotations

from dataclasses import dataclass

from models import PageData, PathPrimitive
from layout.constants import SEGMENT_BIN_PX, SEGMENT_SPAN_FRAC


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


def build_ink_map(
    page_data: PageData,
    bin_px: int = SEGMENT_BIN_PX,
    include_text: bool = True,
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

    for p in page_data.paths:
        if is_page_spanning(p, page_data.width_px, page_data.height_px):
            continue
        pts = p.points
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
