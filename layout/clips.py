"""Native PDF clip rects, used as extra cut hints for the segmenter.

Clip rects are NOT used as regions. They overlap and nest each other (five do
on REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461), so feeding them as cut
candidates is what preserves the invariant that segmentation yields a
partition. They are also absent on 13 of 20 sample files, so they can only ever
supplement the whitespace cut.
"""
from __future__ import annotations

from models import BBox, PageData
from layout.constants import CLIP_MAX_PAGE_FRAC, CLIP_MIN_INK_FRAC

SCALE = 150 / 72


def qualifying_clip_rects_from_boxes(
    boxes_px: list[BBox], page_data: PageData
) -> list[BBox]:
    """Keep only clips that look like real drawing boundaries.

    Measured on the sample set: text and annotation clips hold 0.0-1.3% of the
    page's paths, real drawing clips hold 5.7-62.4%, and whole-sheet clips
    cover 88-97% of the page area. The two gates separate cleanly.
    """
    centres = [
        ((p.bbox[0] + p.bbox[2]) / 2, (p.bbox[1] + p.bbox[3]) / 2)
        for p in page_data.paths
    ]
    total = len(centres)
    if not total:
        return []

    page_area = page_data.width_px * page_data.height_px
    seen: set[BBox] = set()
    out: list[BBox] = []
    for box in boxes_px:
        if box in seen:
            continue
        seen.add(box)
        w, h = box[2] - box[0], box[3] - box[1]
        if w <= 0 or h <= 0:
            continue
        if (w * h) >= CLIP_MAX_PAGE_FRAC * page_area:
            continue
        inside = sum(
            1 for cx, cy in centres
            if box[0] <= cx <= box[2] and box[1] <= cy <= box[3]
        )
        if inside / total >= CLIP_MIN_INK_FRAC:
            out.append(box)
    return out


def qualifying_clip_rects(page, page_data: PageData) -> list[BBox]:
    """Read scissor rects off a fitz.Page and gate them. Returns [] if the
    PDF exposes none, which is the common case."""
    import fitz

    boxes: list[BBox] = []
    try:
        drawings = page.get_drawings(extended=True)
    except Exception:
        return []
    for d in drawings:
        s = d.get("scissor")
        if s is None:
            continue
        r = fitz.Rect(s)
        boxes.append((
            round(r.x0 * SCALE), round(r.y0 * SCALE),
            round(r.x1 * SCALE), round(r.y1 * SCALE),
        ))
    return qualifying_clip_rects_from_boxes(boxes, page_data)


def clip_cut_positions(
    clip_rects: list[BBox], bin_px: int
) -> tuple[set[int], set[int]]:
    """Convert clip edges to (row_bins, col_bins) cut candidates."""
    rows: set[int] = set()
    cols: set[int] = set()
    for x0, y0, x1, y1 in clip_rects:
        cols.add(int(x0 / bin_px))
        cols.add(int(x1 / bin_px))
        rows.add(int(y0 / bin_px))
        rows.add(int(y1 / bin_px))
    return rows, cols
