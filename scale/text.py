"""Tier 2 — the scale a sheet prints as text.

Three corpus sheets carry no viewport but state a scale in words: s02
("1:50@A3"), s14 ("1:50@A1") and s20 ("1:50  & 1:100"). Two traps:

  * Two sheets print DO NOT SCALE FROM THIS DRAWING. Matching the word
    "scale" turns a warning into an annotation, so only a 1:N ratio counts.
  * The separator is a colon, never a slash. "1/5/2024" would read as 1:5,
    and no corpus sheet writes a scale with a slash.

A span keeps its own bbox, which is what binds "SCALE 1:100" printed beneath a
plan to that plan.

The denominator accepts a decimal part even though no sheet prints one. This
is the SAME grammar the store parses a user-typed scale back with, and the
prompt accepts decimals so a measured value like 1:136.4 can be recorded — an
integer-only pattern here would silently reload that as 1:136.
"""
from __future__ import annotations

import re

from models import PageData, ScaleInfo
from scale.units import PAPER_SPACE_MAX_DENOMINATOR, snap_to_standard

_SCALE_RE = re.compile(r"\b1\s*:\s*(\d{1,4}(?:\.\d+)?)\b")


def scales_in_text(text: str) -> list[float]:
    """Every 1:N denominator stated in one string, in the order written."""
    out: list[float] = []
    for match in _SCALE_RE.finditer(text):
        denominator = float(match.group(1))
        if denominator < PAPER_SPACE_MAX_DENOMINATOR:
            continue
        out.append(denominator)
    return out


def text_scales(page_data: PageData) -> list[ScaleInfo]:
    """Every scale printed on the page, each carrying its span's bbox."""
    out: list[ScaleInfo] = []
    for span in page_data.text_spans:
        for denominator in scales_in_text(span.text):
            out.append(ScaleInfo(
                denominator=denominator,
                source="text",
                bbox=span.bbox,
                raw=span.text.strip(),
                nominal=snap_to_standard(denominator),
            ))
    return out
