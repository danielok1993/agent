"""Native PDF clip rects, used as extra cut hints for the segmenter.

Clip rects are NOT used as regions. They overlap and nest each other (five do
on s17), so feeding them as cut
candidates is what preserves the invariant that segmentation yields a
partition. They are also absent on 13 of 20 sample files, so they can only ever
supplement the whitespace cut.
"""
from __future__ import annotations

from extraction.extractor import SCALE, normalize_bbox, page_transform
from models import BBox, PageData
from layout.constants import CLIP_MAX_PAGE_FRAC, CLIP_MIN_INK_FRAC


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

    # Scissor rects come off the page in the same UNROTATED frame as
    # get_drawings(), so they take the same transform the primitives did.
    transform = page_transform(page, SCALE)

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
        x0, y0, x1, y1 = normalize_bbox((r.x0, r.y0, r.x1, r.y1), transform)
        boxes.append((round(x0), round(y0), round(x1), round(y1)))
    return qualifying_clip_rects_from_boxes(boxes, page_data)


def clip_cut_positions(
    clip_rects: list[BBox], bin_px: int
) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    """Convert clip edges to (row, col) cut candidates, in bin indices.

    Each candidate is (position, perp_lo, perp_hi): the edge coordinate plus
    the donating rect's extent along the perpendicular axis. An edge only
    exists where its rect does — flattening to bare coordinates let the
    location plan's clip edge on s20 slice both floor plans at the top of
    the sheet, drawings the clip never touches."""
    rows: set[tuple[int, int, int]] = set()
    cols: set[tuple[int, int, int]] = set()
    for x0, y0, x1, y1 in clip_rects:
        c_lo, c_hi = int(x0 / bin_px), int(x1 / bin_px)
        r_lo, r_hi = int(y0 / bin_px), int(y1 / bin_px)
        cols.add((c_lo, r_lo, r_hi))
        cols.add((c_hi, r_lo, r_hi))
        rows.add((r_lo, c_lo, c_hi))
        rows.add((r_hi, c_lo, c_hi))
    return rows, cols
