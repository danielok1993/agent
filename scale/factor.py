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

# The scale every detection constant was tuned at (s01/s02 are 1:50).
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
    source: str  # "floor_plan_regions" | "page" | "unresolved" | "clamped"
    warnings: list = field(default_factory=list)


def _effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY."""
    return info.nominal if info.nominal is not None else info.denominator


def detection_scale(
    page_scales: PageScales,
    regions: list[Region],
    page_number: int,
) -> DetectionScale:
    floor_plans = {r.region_id: r for r in regions
                   if r.region_type == "floor_plan"}

    votes: dict[float, int] = {}
    for rid, info in page_scales.by_region.items():
        reg = floor_plans.get(rid)
        if reg is None:
            continue
        denom = _effective_denominator(info)
        if denom is None:
            continue
        # Gates act on primitives, not blank paper: dominance is ink
        # (path count), not bbox area. max(_, 1) so a zero-count region
        # still casts a vote.
        votes[denom] = votes.get(denom, 0) + max(reg.path_count, 1)

    warnings: list[dict] = []
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
    elif (page_scales.page_scale is not None
          and _effective_denominator(page_scales.page_scale) is not None):
        denom = _effective_denominator(page_scales.page_scale)
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
