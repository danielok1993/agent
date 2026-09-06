"""Pixel ↔ metre conversion.

Everything downstream of extraction/extractor.py is 150-DPI pixel space, so a
pixel is 25.4/150 mm on paper. A drawing at 1:D puts D real mm in every paper
mm. This module knows nothing about pages or rooms — pure arithmetic.
"""
from __future__ import annotations

from typing import Optional

from scale.units import MM_PER_PX_AT_1_1  # noqa: F401 — 0.16933 mm of paper per pixel


def effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute exactly (scale/factor.py rule)."""
    if info is None:
        return None
    if getattr(info, "nominal", None) is not None:
        return float(info.nominal)
    if getattr(info, "denominator", None) is not None:
        return float(info.denominator)
    return None


def mm_per_px(denominator: float) -> float:
    return MM_PER_PX_AT_1_1 * denominator


def px_to_m(px: float, denominator: float) -> float:
    return px * mm_per_px(denominator) / 1000.0


def px2_to_m2(px2: float, denominator: float) -> float:
    side = mm_per_px(denominator) / 1000.0
    return px2 * side * side
