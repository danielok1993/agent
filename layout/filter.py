"""Reduce a PageData to the primitives inside a set of regions.

This filters, it does not crop: every coordinate stays in page space and
width_px/height_px stay at full page size. Room detection filters components by
page fraction and by page-border contact, so shrinking the page dimensions
would silently change which rooms survive.
"""
from __future__ import annotations

import copy

from models import BBox, PageData, Region, TextSpan


def _centre_in_any(bbox: BBox, boxes: list[BBox]) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes)


def filter_page_data(page_data: PageData, regions: list[Region]) -> PageData:
    """A copy of page_data holding only primitives whose bbox centre falls in
    one of the regions. Whole primitives are kept or dropped — nothing is
    sliced, because regions are derived from the ink itself."""
    boxes = [r.bbox for r in regions]
    out = copy.copy(page_data)
    out.paths = [p for p in page_data.paths if _centre_in_any(p.bbox, boxes)]
    out.text_spans = [t for t in page_data.text_spans if _centre_in_any(t.bbox, boxes)]
    out.images = [i for i in page_data.images if _centre_in_any(i.bbox, boxes)]
    return out


def region_text_spans(page_data: PageData, regions: list[Region]) -> list[TextSpan]:
    """Text spans inside the given regions. Used to scope schedule detection to
    schedule_table regions without touching geometry detection."""
    boxes = [r.bbox for r in regions]
    return [t for t in page_data.text_spans if _centre_in_any(t.bbox, boxes)]
