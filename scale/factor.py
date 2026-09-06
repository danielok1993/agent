"""One detection factor per page: which scale governs the ink detection sees.

Detection runs ONCE over the union of the floor-plan regions, so a page gets
ONE factor. On mixed-scale pages (s03, s17) the ink-dominant floor-plan scale
wins — an interim compromise the SCALE_MIXED_FLOOR_PLANS warning makes loud;
the per-scale-group fix is a follow-up (findings doc §6). Non-floor-plan
regions never reach the detectors, so their scales are ignored here by
construction, not by special-casing.

The drawing's own dimension strings (scale/dimensions.py) sit beside the
resolved claim: three or more ticked, labelled lines inside a plan VERIFY its
claimed scale or CONTRADICT it, and the gates follow the verified number —
whatever it is — or the measured one. See `_gate_choice`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import Region
from scale.dimensions import DimensionMatch, agreement, measured_denominator
from scale.resolver import PageScales
from scale.units import format_scale, snap_to_standard

# The scale every detection constant was tuned at. NOTE (2026-08-19): the
# tuning premise "s01 and s02 are both 1:50" turned out half-false — s01's
# dimension strings measure 1:92.2 (plot metric), though its paper
# conventions are standard — so the constants were calibrated at factor 1.0
# on ink spanning 1:50–1:92.2 world density. The W references were then
# re-derived at the sheets' true scales (W-gate iterations 2–3, 2026-09-04/05,
# docs/w-gate-recalibration-handoff.md), which is what lets s01's measured
# 1:92.2 drive its gates now (step 12).
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
    # "floor_plan_regions" | "page" | "unresolved" | "clamped" | "measured"
    # | "dimensions" — the last when the drawing's dimension strings
    # contradicted every claim that voted for the chosen denominator.
    source: str
    warnings: list = field(default_factory=list)
    # The page's dimension-string scale — the median implied denominator over
    # ≥ DIM_MIN_MATCHES matched strings — or None when the page carries too
    # few to measure. Recorded whether or not it changed the factor.
    measured: Optional[float] = None


def _effective_denominator(info) -> Optional[float]:
    """Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY."""
    return info.nominal if info.nominal is not None else info.denominator


def _gate_denominator(info) -> Optional[float]:
    """The denominator a claim may drive the gates with ON ITS OWN, or None.

    A DRAFTING scale may: a nominal (standard) denominator from any source,
    or a raw viewport value — /VP declares the CAD world-to-paper transform,
    so its world ink genuinely sits at that density under standard paper
    conventions (s13's 1:136.4).

    A non-nominal denominator from any other source (user-stored, text) is a
    MEASUREMENT of the plot — the mm-per-px truth the takeoff needs — and on
    its own says nothing about the ink density the gates were calibrated
    for; it abstains here and drives the gates only once the drawing's own
    dimension strings verify it (`_gate_choice`). History: feeding s01's
    stored 1:92.2 straight to the gates on 2026-08-19 regressed it from
    13/13 rooms to 7/13 with 17 phantoms, because every W constant had been
    calibrated on that very ink at factor 1.0; with the W references
    re-derived at true scales (iterations 2–3) the same factor keeps 11/11
    doors, 4/4 windows and every non-stair room, so the verified measurement
    is admitted (step 12, 2026-09-06).
    """
    if info.nominal is not None:
        return info.nominal
    if info.source == "viewport":
        return info.denominator
    return None


def _gate_choice(info, measured: Optional[float]) -> tuple[Optional[float], str]:
    """(denominator, how) for one resolved scale against the plan's measured
    scale: the claim VERIFIED by ≥ DIM_MIN_MATCHES dimension strings within
    DIM_AGREE_TOL ("verified" — s01's stored 1:92.2, 31 strings within
    ±0.5 %), the measured scale replacing a claim those strings contradict
    past DIM_DISAGREE_TOL ("dimensions" — a half-size print captioned 1:50
    whose strings measure 1:100; snapped to a standard scale when within
    tolerance so it computes exactly, like a nominal), else the claim on its
    own terms (`_gate_denominator`: "claim", or "abstain" with None).

    A drawing's dimension strings are drawn by the same hand at the same
    world scale as its walls, so they measure exactly the density the gates
    care about; a caption or a stored value is a statement ABOUT the
    drawing. Between the two tolerances the strings are inconclusive and
    the claim stands or abstains as it would without them — the takeoff's
    `verified` reads the same three bands (takeoff/plausibility.py)."""
    claim = _effective_denominator(info)
    if measured is not None and claim is not None:
        status = agreement(measured, claim)
        if status == "ok":
            return claim, "verified"
        if status == "implausible":
            snapped = snap_to_standard(measured)
            return (snapped if snapped is not None else measured), "dimensions"
    denom = _gate_denominator(info)
    return (denom, "claim") if denom is not None else (None, "abstain")


def _measured_only_warning(page_number: int, denominators: list[float],
                           page_level: bool) -> dict:
    what = ("Measured, non-standard page scale "
            if page_level else "Measured, non-standard scale(s) (")
    listed = ", ".join(format_scale(d) for d in sorted(set(denominators)))
    return {
        "page_number": page_number,
        "warning_code": "SCALE_FACTOR_MEASURED_ONLY",
        "severity": "warning",
        "message": (
            what + listed + ("" if page_level else ")")
            + " do" + ("es" if page_level else "")
            + " not drive detection-gate scaling — the drawing's dimension "
            "strings do not verify it (fewer than 3 matched, or "
            "inconclusive); gates are calibrated for standard drafting "
            "scales, viewport transforms and dimension-verified scales; the "
            "takeoff still uses the measured scale"
        ),
    }


def _from_dimensions_warning(page_number: int, measured: float, chosen: float,
                             claims: list[tuple[str, float]]) -> dict:
    where = ", ".join(f"{rid} {format_scale(c)}" for rid, c in claims)
    return {
        "page_number": page_number,
        "warning_code": "SCALE_FACTOR_FROM_DIMENSIONS",
        "severity": "warning",
        "message": (
            f"The drawing's dimension strings measure {format_scale(measured)} "
            f"and contradict the resolved scale ({where}); detection gates run "
            f"at {format_scale(chosen)} — the takeoff keeps the resolved scale "
            "and flags it SCALE_IMPLAUSIBLE"
        ),
    }


def detection_scale(
    page_scales: PageScales,
    regions: list[Region],
    page_number: int,
    dimensions: list[DimensionMatch] = (),
) -> DetectionScale:
    """`dimensions` is the page's ticked-dimension-string matches on the FULL
    page (scale.dimensions.page_dimensions); each floor-plan region is judged
    by the strings drawn inside its own bbox, the page-level fallback by all
    of them. Omitted, the claims stand on their own — the pre-step-12 rule."""
    floor_plans = {r.region_id: r for r in regions
                   if r.region_type == "floor_plan"}
    measured_page = measured_denominator(dimensions)

    votes: dict[float, int] = {}
    claimed: set[float] = set()          # denominators some claim voted for
    overridden: dict[float, list[tuple[str, float]]] = {}
    measured_only: list[float] = []
    for rid, info in page_scales.by_region.items():
        reg = floor_plans.get(rid)
        if reg is None:
            continue
        denom, how = _gate_choice(
            info, measured_denominator(dimensions, reg.bbox))
        if denom is None:
            # Resolved but not gate-qualified (measured, non-standard, not
            # viewport-declared, not verified): the takeoff still uses it;
            # the gates don't.
            if _effective_denominator(info) is not None:
                measured_only.append(_effective_denominator(info))
            continue
        if how == "dimensions":
            overridden.setdefault(denom, []).append(
                (rid, _effective_denominator(info)))
        else:
            claimed.add(denom)
        # Gates act on primitives, not blank paper: dominance is ink
        # (path count), not bbox area. max(_, 1) so a zero-count region
        # still casts a vote.
        votes[denom] = votes.get(denom, 0) + max(reg.path_count, 1)

    warnings: list[dict] = []
    if measured_only:
        warnings.append(_measured_only_warning(page_number, measured_only, False))
    if votes:
        # Tie-break: smaller denominator (less aggressive scaling), made
        # deterministic by iterating denominators in sorted order.
        denom = max(sorted(votes), key=lambda d: votes[d])
        source = "floor_plan_regions"
        if denom in overridden and denom not in claimed:
            source = "dimensions"
        for over, claims in sorted(overridden.items()):
            warnings.append(_from_dimensions_warning(
                page_number, measured_page if measured_page is not None else over,
                over, claims))
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
            "measured", warnings, measured_page)
    elif (page_scales.page_scale is not None
          and _effective_denominator(page_scales.page_scale) is not None):
        denom, how = _gate_choice(page_scales.page_scale, measured_page)
        if denom is None:
            measured = _effective_denominator(page_scales.page_scale)
            warnings.append(_measured_only_warning(page_number, [measured], True))
            return DetectionScale(1.0, measured, "measured", warnings,
                                  measured_page)
        source = "page"
        if how == "dimensions":
            source = "dimensions"
            warnings.append(_from_dimensions_warning(
                page_number, measured_page, denom,
                [("page", _effective_denominator(page_scales.page_scale))]))
    else:
        return DetectionScale(1.0, None, "unresolved", warnings, measured_page)

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
        return DetectionScale(1.0, denom, "clamped", warnings, measured_page)
    return DetectionScale(factor, denom, source, warnings, measured_page)
