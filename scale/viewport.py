"""Tier 1 — the scale the PDF states in its own viewport measure dictionaries.

A CAD exporter writes /VP entries (ISO 32000-1 §12.9) so a reader's measure
tool can report real lengths. Ten of the twenty corpus sheets carry them, and
where a sheet also prints its scale the two agree on all but s13.

Two structural rules the corpus forces:

  * A viewport at 1:1 is the sheet of paper. s03, s04, s08 and s17 each have
    one spanning the whole page.
  * Viewports NEST, and the innermost containing a point governs. s06 carries
    an outer 1:146 and an inner 1:99.6; the inner is what its "SCALE 1:100"
    caption refers to.

PyMuPDF cannot index into the array (xref_get_key(xref, "VP[0]") returns null),
so the whole array comes back as one string and is split here. A regex sweeping
the raw string is NOT safe: it will happily pair one viewport's /C with
another's /BBox, which is exactly the error that produced a phantom scale
mismatch on s06 during design research.
"""
from __future__ import annotations

import re
from typing import Optional

from extraction.extractor import page_transform
from models import BBox, ScaleInfo
from scale.units import (
    PAPER_SPACE_MAX_DENOMINATOR,
    denominator_from_c,
    snap_to_standard,
)

_BBOX_RE = re.compile(r"/BBox\s*\[([-\d.\s]+)\]")
# Anchored on /X so the /A (area) and /D (distance) factors, which are both
# C 1 on every corpus sheet, can never be read as the drawing scale.
_X_FACTOR_RE = re.compile(r"/X\s*\[\s*<<[^>]*?/C\s*([-\d.eE+]+)")
_RECTILINEAR_RE = re.compile(r"/Subtype\s*/RL\b")


def split_pdf_dicts(array_text: str) -> list[str]:
    """Split a PDF array string into its top-level ``<< >>`` dictionaries.

    Depth-counted rather than regexed, so a nested /Measure never terminates
    its parent viewport early. Malformed input yields whatever completed
    cleanly rather than raising.
    """
    out: list[str] = []
    depth = 0
    start: Optional[int] = None
    i = 0
    while i < len(array_text) - 1:
        pair = array_text[i:i + 2]
        if pair == "<<":
            if depth == 0:
                start = i
            depth += 1
            i += 2
            continue
        if pair == ">>":
            depth -= 1
            i += 2
            if depth < 0:
                return out
            if depth == 0 and start is not None:
                out.append(array_text[start:i])
                start = None
            continue
        i += 1
    return out


def parse_measure_viewports(
    vp_array_text: str,
) -> list[tuple[tuple[float, float, float, float], float]]:
    """Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.

    The bbox is left in raw PDF coordinates — y-up, bottom-left origin.
    Paper-space (1:1) viewports are dropped here.
    """
    out: list[tuple[tuple[float, float, float, float], float]] = []
    for chunk in split_pdf_dicts(vp_array_text):
        if "/Measure" not in chunk or not _RECTILINEAR_RE.search(chunk):
            continue
        bbox_match = _BBOX_RE.search(chunk)
        factor_match = _X_FACTOR_RE.search(chunk)
        if not (bbox_match and factor_match):
            continue
        numbers = [float(v) for v in bbox_match.group(1).split()]
        if len(numbers) != 4:
            continue
        try:
            c = float(factor_match.group(1))
        except ValueError:
            continue
        if denominator_from_c(c) < PAPER_SPACE_MAX_DENOMINATOR:
            continue
        x0, y0, x1, y1 = numbers
        out.append(((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), c))
    return out


def viewport_bbox_to_px(
    bbox_pt_yup: tuple[float, float, float, float],
    mediabox: tuple[float, float, float, float],
    transform: tuple[float, float, float, float, float, float],
) -> BBox:
    """Convert a raw /VP bbox into 150-DPI pixel space.

    Two steps, in this order. First flip y about the mediabox, because
    xref_get_key returns PDF-native coordinates (y-up, bottom-left) while
    get_drawings() and everything downstream are y-down, top-left. Then apply
    the page transform, which carries SCALE and any /Rotate.
    """
    mx0, _my0, _mx1, my1 = mediabox
    x0 = bbox_pt_yup[0] - mx0
    x1 = bbox_pt_yup[2] - mx0
    y0 = my1 - bbox_pt_yup[3]
    y1 = my1 - bbox_pt_yup[1]

    a, b, c, d, e, f = transform
    corners = [
        (a * px + c * py + e, b * px + d * py + f)
        for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))
    ]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def viewport_scales(doc, page) -> list[ScaleInfo]:
    """Every drawing scale this page's viewports state, smallest bbox first.

    Smallest-first is the nesting rule: the first viewport whose bbox contains
    a point is the innermost one, and that is the scale governing it.
    """
    try:
        kind, value = doc.xref_get_key(page.xref, "VP")
    except Exception:
        return []
    if kind != "array":
        return []

    mediabox = (page.mediabox.x0, page.mediabox.y0,
                page.mediabox.x1, page.mediabox.y1)
    transform = page_transform(page)

    out: list[ScaleInfo] = []
    for bbox_pt, c in parse_measure_viewports(value):
        denominator = denominator_from_c(c)
        out.append(ScaleInfo(
            denominator=denominator,
            source="viewport",
            bbox=viewport_bbox_to_px(bbox_pt, mediabox, transform),
            raw=f"C={c:g}",
            nominal=snap_to_standard(denominator),
        ))
    out.sort(key=lambda s: (s.bbox[2] - s.bbox[0]) * (s.bbox[3] - s.bbox[1]))
    return out
