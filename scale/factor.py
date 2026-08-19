"""One detection factor per page: which scale governs the ink detection sees.

Detection runs ONCE over the union of the floor-plan regions, so a page gets
ONE factor. On mixed-scale pages (s03, s17) the ink-dominant floor-plan scale
wins — an interim compromise the SCALE_MIXED_FLOOR_PLANS warning makes loud;
the per-scale-group fix is a follow-up (findings doc §6). Non-floor-plan
regions never reach the detectors, so their scales are ignored here by
construction, not by special-casing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import Region
from scale.resolver import PageScales
from scale.units import format_scale

# The scale every detection constant was tuned at. NOTE (2026-08-19): the
# tuning premise "s01 and s02 are both 1:50" turned out half-false — s01's
# dimension strings measure 1:92.2 (plot metric), though its paper
# conventions are standard — so the constants were calibrated at factor 1.0
# on ink spanning 1:50–1:92.2 world density. That is why _gate_denominator
# refuses to scale gates by measured, non-standard denominators.
DETECTION_REFERENCE_DENOMINATOR = 50.0

# Calibration domain: the corpus evidence spans 1:50–1:136. Beyond
# [1:12.5, 1:200] the drafting convention itself changes (site plans draw
# walls as single lines), and an extreme factor more likely means a resolver
# mis-binding — fall back to identity, loudly.
DETECTION_FACTOR_MIN = 0.25
DETECTION_FACTOR_MAX = 4.0


@dataclass(frozen=True)
class DetectionScale:
    factor: float
    denominator: Optional[float]
    source: str  # "floor_plan_regions" | "page" | "unresolved" | "clamped" | "measured"
    warnings: list = field(default_factory=list)


def _effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY."""
    return info.nominal if info.nominal is not None else info.denominator


def _gate_denominator(info) -> Optional[float]:
    """The denominator allowed to drive gate scaling, or None to abstain.

    Only a DRAFTING scale may scale the world gates: a nominal (standard)
    denominator from any source, or a raw viewport value — /VP declares the
    CAD world-to-paper transform, so its world ink genuinely sits at that
    density under standard paper conventions (s13's 1:136.4).

    A non-nominal denominator from any other source (user-stored, text) is a
    MEASUREMENT of the plot — the mm-per-px truth the takeoff needs — not a
    drafting scale. Feeding it to the gates is how s01 regressed (measured
    2026-08-19): the sheet's paper conventions are standard (wall pen 1.5px
    and hatch pitch 4.05px, identical to s02's 1.5/4.07) while its world ink
    measures 1:92.2, and every W constant was calibrated on that very ink at
    factor 1.0 — so f=50/92.2 pushed s01's own features just outside the
    gates (its 25px party wall past the 19.5px cap, its 30–35px hatch marks
    past the 26px material cap, plugs short of their jambs) and the sweep
    fell from 13/13 rooms to 7/13 with 17 phantoms. Identity is the
    conservative fallback, same as the factor clamp above.
    """
    if info.nominal is not None:
        return info.nominal
    if info.source == "viewport":
        return info.denominator
    return None


def detection_scale(
    page_scales: PageScales,
    regions: list[Region],
    page_number: int,
) -> DetectionScale:
    floor_plans = {r.region_id: r for r in regions
                   if r.region_type == "floor_plan"}

    votes: dict[float, int] = {}
    measured_only: list[float] = []
    for rid, info in page_scales.by_region.items():
        reg = floor_plans.get(rid)
        if reg is None:
            continue
        denom = _gate_denominator(info)
        if denom is None:
            # Resolved but not gate-qualified (measured, non-standard, not
            # viewport-declared): the takeoff still uses it; the gates don't.
            if _effective_denominator(info) is not None:
                measured_only.append(_effective_denominator(info))
            continue
        # Gates act on primitives, not blank paper: dominance is ink
        # (path count), not bbox area. max(_, 1) so a zero-count region
        # still casts a vote.
        votes[denom] = votes.get(denom, 0) + max(reg.path_count, 1)

    warnings: list[dict] = []
    if measured_only:
        warnings.append({
            "page_number": page_number,
            "warning_code": "SCALE_FACTOR_MEASURED_ONLY",
            "severity": "warning",
            "message": (
                "Measured, non-standard scale(s) ("
                + ", ".join(format_scale(d) for d in sorted(set(measured_only)))
                + ") do not drive detection-gate scaling — gates are "
                "calibrated for standard drafting scales and viewport "
                "transforms; the takeoff still uses the measured scale"
            ),
        })
    if votes:
        # Tie-break: smaller denominator (less aggressive scaling), made
        # deterministic by iterating denominators in sorted order.
        denom = max(sorted(votes), key=lambda d: votes[d])
        source = "floor_plan_regions"
        if len(votes) > 1:
            warnings.append({
                "page_number": page_number,
                "warning_code": "SCALE_MIXED_FLOOR_PLANS",
                "severity": "warning",
                "message": (
                    "Floor-plan regions carry different scales ("
                    + ", ".join(format_scale(d) for d in sorted(votes))
                    + f"); detection runs at ink-dominant {format_scale(denom)}"
                ),
            })
    elif measured_only:
        # Every resolved floor-plan scale was measured-only: identity, with
        # the single measured denominator recorded (mirrors "clamped").
        distinct = sorted(set(measured_only))
        return DetectionScale(
            1.0, distinct[0] if len(distinct) == 1 else None,
            "measured", warnings)
    elif (page_scales.page_scale is not None
          and _effective_denominator(page_scales.page_scale) is not None):
        denom = _gate_denominator(page_scales.page_scale)
        if denom is None:
            measured = _effective_denominator(page_scales.page_scale)
            warnings.append({
                "page_number": page_number,
                "warning_code": "SCALE_FACTOR_MEASURED_ONLY",
                "severity": "warning",
                "message": (
                    f"Measured, non-standard page scale "
                    f"{format_scale(measured)} does not drive detection-gate "
                    "scaling — gates are calibrated for standard drafting "
                    "scales and viewport transforms; the takeoff still uses "
                    "the measured scale"
                ),
            })
            return DetectionScale(1.0, measured, "measured", warnings)
        source = "page"
    else:
        return DetectionScale(1.0, None, "unresolved", warnings)

    factor = DETECTION_REFERENCE_DENOMINATOR / denom
    if not (DETECTION_FACTOR_MIN <= factor <= DETECTION_FACTOR_MAX):
        warnings.append({
            "page_number": page_number,
            "warning_code": "SCALE_FACTOR_CLAMPED",
            "severity": "warning",
            "message": (
                f"Resolved scale {format_scale(denom)} gives detection factor "
                f"{factor:.3f}, outside [{DETECTION_FACTOR_MIN}, "
                f"{DETECTION_FACTOR_MAX}] — falling back to 1.0"
            ),
        })
        return DetectionScale(1.0, denom, "clamped", warnings)
    return DetectionScale(factor, denom, source, warnings)
