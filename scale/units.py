"""Scale arithmetic shared by every resolution tier.

A PDF /Measure dictionary states its conversion factor /C as real-world units
per PDF point. Every corpus sheet leaves /U blank, but the paper-space viewport
on each of them reads C = 0.35278 — exactly 1 mm/pt — which pins the unit to
millimetres. See the design spec for the measurements.
"""
from __future__ import annotations

from typing import Optional

MM_PER_PT = 25.4 / 72  # 0.352777...

# Everything downstream of extraction/extractor.py is 150-DPI pixel space, so
# a pixel is 25.4/150 mm on paper; a drawing at 1:D puts D real mm in every
# paper mm. Defined here (takeoff/units.py re-exports it) because the
# dimension-string measurement in scale/dimensions.py needs it and scale/ must
# not import takeoff/ — takeoff imports detection.
MM_PER_PX_AT_1_1 = 25.4 / 150.0   # 0.16933 mm of paper per pixel

# A viewport at 1:1 is the sheet of paper, not a drawing. Ten of the corpus
# sheets carry one; s03, s04, s08 and s17 span the whole page with it.
PAPER_SPACE_MAX_DENOMINATOR = 1.5

# UK architectural and OS map scales. Ordered small to large; the first match
# inside tolerance wins, and the bands never overlap at 2%.
STANDARD_SCALES = (1, 20, 25, 50, 100, 200, 500, 1000, 1250, 2500)

# The scales a user may supply for a sheet whose scale nobody could read.
# STANDARD_SCALES restricted to the band scale/factor.py's detection gates are
# calibrated for: a factor of 50/D must land inside [0.25, 4.0]. 1:1 is paper
# space, and 1:500 upward are site plans, where the drafting convention itself
# changes and the factor would be clamped back to identity.
#
# Every member snaps to itself, so a supplied scale always reaches
# _gate_denominator as a nominal and always drives the gates. A value that
# failed to snap would leave the re-run detecting at identity — the exact
# failure the whole scale-input feature exists to remove.
#
# Stated here rather than derived from factor.py's constants because
# scale/factor.py imports scale/resolver.py, and the resolver needs this.
# tests/test_scale_units.py pins it against those constants in both
# directions, so a change to either end is caught.
SUPPLIABLE_SCALES = (20.0, 25.0, 50.0, 100.0, 200.0)

SNAP_TOLERANCE = 0.02

# Two readings of the same drawing closer than this are the same scale written
# differently, not a disagreement. s06 measures 99.6 against a printed 1:100.
AGREEMENT_TOLERANCE = 0.02


def cluster_denominators(
    denominators, tolerance: float = AGREEMENT_TOLERANCE
) -> list[list[float]]:
    """Group near-equal denominators, largest group first in input order.

    Lives here rather than in the resolver because the inspector needs the
    same grouping to count repeats, and two implementations would drift.

    CAD never writes the same scale as the same float: s04's two 1:50
    viewports measure 49.995 and 50.001, and s17's four 1:100 plans measure
    99.986, 99.988, 99.993 and 99.995. Anything keyed on the raw float reads a
    single-scale sheet as multi-scale, or prints one scale four times.
    """
    groups: list[list[float]] = []
    for value in sorted(denominators):
        if groups and abs(value - groups[-1][0]) <= tolerance * groups[-1][0]:
            groups[-1].append(value)
        else:
            groups.append([value])
    return groups


def canonical_denominators(
    denominators, tolerance: float = AGREEMENT_TOLERANCE
) -> list[float]:
    """One representative per cluster — how many DISTINCT scales are present."""
    return [group[0] for group in cluster_denominators(denominators, tolerance)]


def denominator_from_c(c: float) -> float:
    """The 1:N denominator for a /Measure /X conversion factor."""
    return c / MM_PER_PT


def snap_to_standard(
    denominator: float, tolerance: float = SNAP_TOLERANCE
) -> Optional[float]:
    """The nearest standard scale within tolerance, or None.

    None is a real answer, not a failure: s13 measures 1:136.4, and rounding
    that to 1:100 would invent precision the drawing does not have.
    """
    for standard in STANDARD_SCALES:
        if abs(denominator - standard) <= tolerance * standard:
            return float(standard)
    return None


def format_scale(denominator: float) -> str:
    """Render a denominator for display: 1:100, or 1:136.4 when it is not whole."""
    if abs(denominator - round(denominator)) < 0.05:
        return f"1:{int(round(denominator))}"
    return f"1:{denominator:.1f}"
