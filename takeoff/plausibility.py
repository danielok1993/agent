"""Is the resolved scale believable? Two checks that read the drawing itself.

A scale can be wrong however it was obtained: a title-block "1:50" on a sheet
exported at A3 is really 1:100, a viewport can describe a different plan, and
a typed scale can be a typo. Every tier lands here before `verified` is set.

1. Door leaves. A swing leaf is 0.6–0.9 m on every real sheet in the corpus
   (medians 0.64–0.90 m; s01, the mis-declared one, 0.38 m), so the page's
   median leaf at the resolved scale falls outside [LEAF_MIN_M, LEAF_MAX_M]
   only when the scale is off — and off by a print factor, so the implied
   correction is snapped to ×0.25 / ×0.5 / ×2 / ×4 of the current denominator.
   Rooms cannot serve: the smallest room on every sheet is a sub-m² cupboard
   or phantom, and wall thickness never reaches the takeoff. Widths are taken
   from detector evidence only (arc radius, merged pair chord ÷ 2, panel
   length) — a bbox edge is not a leaf.

2. Dimension strings. "3600" written beside a line ticked at both ends IS the
   drawing's scale, measured: value_mm / (length_px × 0.16933). Median over
   ≥ DIM_MIN_MATCHES lines. Agreement within DIM_AGREE_TOL verifies even a
   text-only scale; a disagreement past DIM_DISAGREE_TOL contradicts even a
   typed one. Numbers are never swapped — the verdict only gates `verified`.
   The matcher and the tolerances live in scale/dimensions.py (re-exported
   here unchanged) because the detection gates read the same measurement
   BEFORE detection — a verified non-standard scale drives them, a
   contradicted one is replaced by the measured scale — and scale/ must not
   import takeoff/.

Dimensions decide when they are measurable; door leaves are the fallback.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Optional

from scale.dimensions import (  # noqa: F401 — re-exported, one grammar
    DIM_AGREE_TOL, DIM_DISAGREE_TOL, DIM_LABEL_OFFSET_HEIGHTS, DIM_LABEL_OVERHANG,
    DIM_METRES_MAX, DIM_MIN_MATCHES, DIM_MIN_MM, DimensionMatch, agreement,
    dimension_matches, parse_dimension_mm,
)
from takeoff.units import px_to_m

LEAF_MIN_M = 0.55
LEAF_MAX_M = 1.20
LEAF_TYPICAL_M = 0.80
LEAF_MIN_DOORS = 2
# Print-size corrections only: half/double/quadruple sheets.
CORRECTION_FACTORS = (0.25, 0.5, 2.0, 4.0)

_MERGED = frozenset({"double_swing"})
_ARCLESS = frozenset({"sliding", "folding"})


@dataclass(frozen=True)
class Verdict:
    status: str                        # ok | implausible | untested
    method: Optional[str]              # door_leaves | dimensions | None
    n: int = 0
    median_m: Optional[float] = None   # door_leaves: median leaf width
    implied_denominator: Optional[float] = None

    def to_dict(self) -> dict:
        d = {"status": self.status, "method": self.method, "n": self.n}
        if self.median_m is not None:
            d["median_leaf_m"] = round(self.median_m, 2)
        if self.implied_denominator is not None:
            d["implied_denominator"] = self.implied_denominator
        return d

    def describe(self, denominator: float) -> str:
        """The SCALE_IMPLAUSIBLE message for an implausible verdict."""
        if self.method == "dimensions":
            return (f"Scale {_fmt_scale(denominator)} contradicts the drawing's dimension "
                    f"strings: {self.n} ticked dimension(s) measure as "
                    f"{_fmt_scale(self.implied_denominator)}")
        leaf = self.median_m or 0.0
        at = leaf * self.implied_denominator / denominator
        return (f"Scale {_fmt_scale(denominator)} is implausible: median door leaf "
                f"{leaf:.2f} m over {self.n} door(s) (expected {LEAF_MIN_M:.2f}–"
                f"{LEAF_MAX_M:.2f}); at {_fmt_scale(self.implied_denominator)} it would "
                f"be {at:.2f} m")


def _fmt_scale(d: float) -> str:
    return f"1:{d:g}" if float(d).is_integer() else f"1:{d:.1f}"


UNTESTED = Verdict("untested", None)


def _positive(value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def leaf_width_px(evidence: dict) -> Optional[float]:
    """One leaf's width from detector evidence; None when only a bbox exists."""
    evidence = evidence or {}
    atype = evidence.get("assembly_type")
    if atype in _MERGED:
        try:
            (x0, y0), (x1, y1) = evidence.get("opening_line")
        except (TypeError, ValueError):
            return None
        chord = _positive(math.hypot(x1 - x0, y1 - y0))
        return chord / 2.0 if chord else None
    if atype in _ARCLESS:
        return _positive(evidence.get("panel_length_px"))
    arc = evidence.get("arc_bbox")
    if arc:
        try:
            x0, y0, x1, y1 = (float(v) for v in arc)
        except (TypeError, ValueError):
            return None
        return _positive(max(x1 - x0, y1 - y0))
    return _positive(evidence.get("leaf_line_length_px"))


def snap_correction(median_m: float, denominator: float) -> float:
    """The denominator that would put the median leaf at LEAF_TYPICAL_M,
    snapped to a print-size factor of the current one."""
    raw = LEAF_TYPICAL_M / median_m
    factor = min(CORRECTION_FACTORS, key=lambda f: abs(math.log(f) - math.log(raw)))
    return denominator * factor


def check_door_leaves(leaf_px: list[float], denominator: float) -> Verdict:
    widths = [w for w in leaf_px if w and w > 0]
    if len(widths) < LEAF_MIN_DOORS:
        return Verdict("untested", "door_leaves", n=len(widths))
    median = px_to_m(statistics.median(widths), denominator)
    if LEAF_MIN_M <= median <= LEAF_MAX_M:
        return Verdict("ok", "door_leaves", n=len(widths), median_m=median)
    return Verdict("implausible", "door_leaves", n=len(widths), median_m=median,
                   implied_denominator=snap_correction(median, denominator))


# ---------------------------------------------------------------- dimensions
# The matcher, DimensionMatch and the DIM_* tolerances are scale/dimensions.py's
# (imported above); only the Verdict wrapper is the takeoff's own.

def check_dimensions(matches: list[DimensionMatch], denominator: float) -> Verdict:
    n = len(matches)
    if n < DIM_MIN_MATCHES:
        return Verdict("untested", "dimensions", n=n)
    implied = statistics.median(m.implied_denominator for m in matches)
    return Verdict(agreement(implied, denominator), "dimensions", n=n,
                   implied_denominator=round(implied, 1))


# ---------------------------------------------------------------- combined

def assess_scale(denominator: float, leaf_px: list[float],
                 matches: list[DimensionMatch]) -> Verdict:
    """Dimensions decide when they can; door leaves are the fallback."""
    dims = check_dimensions(matches, denominator)
    if dims.status != "untested":
        return dims          # measured (ok / inconclusive / implausible) beats a band
    return check_door_leaves(leaf_px, denominator)

