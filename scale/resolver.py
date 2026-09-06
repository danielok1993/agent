"""The resolution ladder, and how a scale binds to a floor plan.

Binding is what makes scenario 3 work: s17 carries 1:50, four 1:100s, 1:500
and 1:1250 on one sheet, and each is only meaningful against the drawing it
covers. Both parsing tiers carry a bbox, so binding is geometric and needs no
model call.

Order, first hit wins: stored, viewport, text, sole page-level candidate,
prompt. Where viewport and text both bind and disagree, the viewport wins and
the loser is recorded — /Measure describes the PDF as it is, the caption
describes what was intended, and on s13 those differ.
"""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Callable, ContextManager, Optional

from models import PageData, Region, ScaleInfo
from scale.prompt import can_prompt, prompt_for_scale
from scale.store import StoredScale, match_stored, save_stored
from scale.text import scales_in_text, text_scales
from scale.units import (
    AGREEMENT_TOLERANCE, canonical_denominators, format_scale, snap_to_standard,
)

# A caption is drawn beneath its plan, outside the viewport that measures it.
# Measured against each sheet's own measuring viewport: s03's SCALE 1:50 sits
# 60px below, s13's SCALE 1:100 sits 191px below. 240px (1.6in at 150 DPI,
# ~41mm on the sheet) clears both with margin and is still far shorter than any
# plan, so a caption cannot reach past its own drawing to the one above.
#
# Set from BOTH measurements deliberately. At 160 the s13 caption falls out of
# reach, and the one viewport/text conflict in the corpus stops being detected.
CAPTION_REACH_PX = 240.0

@dataclass
class PageScales:
    by_region: dict[str, ScaleInfo] = field(default_factory=dict)
    page_scale: Optional[ScaleInfo] = None
    warnings: list[dict] = field(default_factory=list)


def scale_summary_dict(page_scales: PageScales, det_scale: "DetectionScale | None" = None) -> dict:
    """The scales block written into each page's summary.json entry, and into
    takeoff.json's `scale` block.

    Lives here rather than in pipeline.py because it serialises PageScales,
    and takeoff/ needs it too — takeoff/ must never import pipeline.
    The DetectionScale annotation is a string so no import of scale.factor is
    needed; only three attributes are read.
    """
    def one(info):
        return {"denominator": info.denominator, "source": info.source,
                "raw": info.raw, "nominal": info.nominal,
                "conflict": info.conflict,
                "bbox": list(info.bbox) if info.bbox else None}

    out = {
        "by_region": {rid: one(info) for rid, info in page_scales.by_region.items()},
        "page_scale": one(page_scales.page_scale) if page_scales.page_scale else None,
    }
    if det_scale is not None:
        measured = getattr(det_scale, "measured", None)
        out["detection"] = {
            "factor": round(det_scale.factor, 4),
            "denominator": det_scale.denominator,
            "source": det_scale.source,
            # The page's dimension-string scale (scale/dimensions.py), which
            # verified or overrode the claim above — None when the page has
            # too few matched strings to measure one.
            "measured_denominator": None if measured is None else round(measured, 1),
        }
    return out


def _centroid(bbox) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _contains(outer, x: float, y: float) -> bool:
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _caption_distance(region_bbox, span_bbox) -> Optional[float]:
    """How far a text span sits from a region, or None if it is not near it.

    Horizontal overlap is required: a caption belongs to the plan above it,
    not to one beside it.
    """
    if span_bbox[2] < region_bbox[0] or span_bbox[0] > region_bbox[2]:
        return None
    cx, cy = _centroid(span_bbox)
    if _contains(region_bbox, cx, cy):
        return 0.0
    below = span_bbox[1] - region_bbox[3]
    if 0.0 <= below <= CAPTION_REACH_PX:
        return below
    return None


def binding_texts(region: Region, texts: list[ScaleInfo]) -> list[ScaleInfo]:
    """Every text scale near enough to this region to be about it, nearest first.

    Exposed separately from bind_scale so the resolver can see when two
    DIFFERENT denominators both reach one plan. Picking the nearest of those
    silently would be a guess dressed as a measurement.
    """
    scored: list[tuple[float, ScaleInfo]] = []
    for candidate in texts:
        if candidate.bbox is None:
            continue
        distance = _caption_distance(region.bbox, candidate.bbox)
        if distance is None:
            continue
        scored.append((distance, candidate))
    scored.sort(key=lambda pair: pair[0])
    return [candidate for _distance, candidate in scored]


def bind_scale(
    region: Region,
    viewports: list[ScaleInfo],
    texts: list[ScaleInfo],
) -> Optional[ScaleInfo]:
    """The scale governing one region, or None.

    `viewports` must arrive smallest-bbox-first, which is how
    viewport.viewport_scales returns them — that ordering IS the nesting rule.
    """
    cx, cy = _centroid(region.bbox)

    chosen: Optional[ScaleInfo] = None
    for candidate in viewports:
        if candidate.bbox is not None and _contains(candidate.bbox, cx, cy):
            chosen = candidate
            break

    nearby = binding_texts(region, texts)
    nearest_text = nearby[0] if nearby else None

    if chosen is None:
        return nearest_text

    if (nearest_text is not None
            and nearest_text.denominator is not None
            and chosen.denominator is not None
            and abs(nearest_text.denominator - chosen.denominator)
            > AGREEMENT_TOLERANCE * chosen.denominator):
        return ScaleInfo(
            denominator=chosen.denominator,
            source=chosen.source,
            bbox=chosen.bbox,
            raw=chosen.raw,
            nominal=chosen.nominal,
            conflict=f"text nearby says {format_scale(nearest_text.denominator)}",
        )
    return chosen


def _stored_info(entry: str) -> Optional[ScaleInfo]:
    found = scales_in_text(entry)
    if not found:
        return None
    return ScaleInfo(denominator=found[0], source="user", raw=entry,
                     nominal=snap_to_standard(found[0]))


def _fallback_info(denominator: float) -> ScaleInfo:
    """A scale the user supplied for the whole run, as a ladder entry.

    `source="user"` is load-bearing twice over, and both are wanted:
    takeoff/scale.py's is_verified trusts "user" outright, and
    scale/factor.py's _gate_denominator takes the nominal from any source —
    so the re-run's detection gates are scaled by 50/D rather than running at
    identity, which is the only reason re-running beats rescaling in the
    client.
    """
    return ScaleInfo(denominator=denominator, source="user",
                     raw=f"1:{denominator:g}",
                     nominal=snap_to_standard(denominator))


def resolve_page_scales(
    page_data: PageData,
    regions: list[Region],
    viewports: list[ScaleInfo],
    stored: list[StoredScale],
    fallback: Optional[float] = None,
    pdf_path: Optional[str] = None,
    crop_fn: Optional[Callable[[Region], Optional[str]]] = None,
    allow_prompt: bool = False,
    suspend_display: Optional[Callable[[], ContextManager]] = None,
) -> PageScales:
    """Resolve a scale for every floor-plan region on one page.

    `fallback` is a scale the user supplied for a sheet the ladder could not
    read. It is consulted last, so it can never displace a stored entry, a
    viewport, a caption, or a sole page-level candidate — it only fills what
    would otherwise be unresolved.
    """
    result = PageScales()
    page_number = page_data.page_number

    def warn(code: str, severity: str, message: str) -> None:
        result.warnings.append({"page_number": page_number,
                                "warning_code": code,
                                "severity": severity,
                                "message": message})

    texts = text_scales(page_data)

    # The sheet-level fallback: one distinct scale stated anywhere, with no
    # geometry tying it to a plan. s02 and s14 resolve here.
    #
    # Clustered, not counted as raw floats — s04's two 1:50 viewports measure
    # 49.995 and 50.001, which as distinct floats would make a single-scale
    # sheet look multi-scale.
    scored_candidates = [info for info in list(viewports) + texts
                         if info.denominator is not None]
    distinct = canonical_denominators(
        info.denominator for info in scored_candidates)
    sole_candidate: Optional[ScaleInfo] = None
    if len(distinct) == 1:
        sole_candidate = scored_candidates[0]
    # page_scale is only ever set when the sheet states ONE scale. A sheet
    # carrying several has no scale "as a whole" — s17 states 1:50, 1:100,
    # 1:500 and 1:1250 at once, and picking any of them for summary.json
    # would publish a number that is wrong for most of the sheet.
    result.page_scale = sole_candidate

    fallback_info = None if fallback is None else _fallback_info(fallback)

    floor_plans = [r for r in regions if r.region_type == "floor_plan"]
    unresolved: list[str] = []
    newly_entered: list[StoredScale] = []

    for region in floor_plans:
        # Matched on geometry, not on region_id: ids are ordinal and renumber
        # when segmentation changes, and a stored value outranks every
        # detected one, so a mis-attached entry would override a correct
        # viewport reading rather than merely being ignored.
        entry = match_stored(region.bbox, stored)
        if entry is not None:
            info = _stored_info(entry.scale)
            if info is not None:
                result.by_region[region.region_id] = info
                continue

        info = bind_scale(region, viewports, texts)

        # Two different printed scales both reaching one plan is ambiguity, not
        # a near miss — refuse it rather than taking whichever sits closer. A
        # viewport binding overrides this, since it beats text outright.
        ambiguous = False
        if info is not None and info.source == "text":
            nearby = canonical_denominators(
                c.denominator for c in binding_texts(region, texts)
                if c.denominator is not None)
            if len(nearby) > 1:
                warn("SCALE_MULTIPLE_UNBOUND", "warning",
                     f"Page {page_number}: {len(nearby)} different scales are "
                     f"printed near {region.region_id} — none chosen")
                info = None
                ambiguous = True

        if info is None and not ambiguous and sole_candidate is not None:
            info = sole_candidate
        if info is None and not ambiguous and len(distinct) > 1:
            # One warning per region, so an ambiguous binding is not reported
            # twice under the same code.
            warn("SCALE_MULTIPLE_UNBOUND", "warning",
                 f"Page {page_number}: {len(distinct)} scales found on the sheet "
                 f"and none binds to {region.region_id}")

        # The bottom tier. Deliberately NOT gated on `ambiguous`: two printed
        # scales both reaching one plan is exactly the case the resolver
        # refuses to guess at, and the user supplying a number is the
        # tiebreaker it was refusing on behalf of.
        if info is None and fallback_info is not None:
            info = fallback_info

        if info is None and allow_prompt and can_prompt():
            # Rendered on demand, not looked up. region_crops/ is written only
            # by the Gemini classification call, so on a cache hit or with
            # --no-gemini the directory is empty and a bare path would send
            # the user to a file that does not exist.
            crop_hint = None
            if crop_fn is not None:
                try:
                    crop_hint = crop_fn(region)
                except Exception:
                    crop_hint = None
            # Entered ONLY here, around the blocking read itself — not around
            # the whole resolve. The caller's live progress display must be
            # torn down for input() to draw on a clean line, but tearing it
            # down whenever a prompt is merely POSSIBLE leaves a frozen
            # half-finished bar on every interactive page that resolves
            # normally, which is every page on a sheet that states its scale.
            with (suspend_display() if suspend_display is not None
                  else nullcontext()):
                typed = prompt_for_scale(region.region_id,
                                         crop_hint or "(no crop available)")
            if typed:
                newly_entered.append(StoredScale(region.bbox, typed))
                info = _stored_info(typed)

        if info is None:
            unresolved.append(region.region_id)
            result.by_region[region.region_id] = ScaleInfo(
                denominator=None, source="unresolved")
            continue

        result.by_region[region.region_id] = info
        if info.conflict:
            warn("SCALE_SOURCE_CONFLICT", "warning",
                 f"Page {page_number}: {region.region_id} measures "
                 f"{format_scale(info.denominator)} but {info.conflict}")

    if not floor_plans and len(distinct) > 1:
        # Nothing above ever ran: the per-region loop only warns about a
        # sheet-wide multiplicity when there IS a region to fail to bind to.
        # A sheet stating several scales with no floor-plan region at all
        # (e.g. --no-gemini against a cold region cache, which collapses
        # regions to whole-page or none) must not resolve in silence.
        warn("SCALE_MULTIPLE_UNBOUND", "warning",
             f"Page {page_number}: {len(distinct)} scales found on the sheet "
             f"but no floor plan region to bind them to")

    # The supplied scale is the PAGE's scale when it is the only one governing
    # the sheet. page_scale is what document.py publishes as `scale.page`, and
    # what rivet-mind reads as `scaleDenominator`; left None, a re-run that
    # resolved every room would still have its sheet dropped at that parse
    # boundary and fail identically to the run that prompted the question.
    #
    # Narrow by design. Where some other tier resolved a region, the sheet
    # states more than one scale and has none "as a whole" — the same reason
    # sole_candidate is only ever a SINGLE distinct denominator.
    # Identity, not `source == "user"`: a stored entry is also sourced "user",
    # and this must mean "the object we just built", nothing else.
    resolved = list(result.by_region.values())
    if (fallback_info is not None
            and result.page_scale is None
            and any(entry is fallback_info for entry in resolved)
            and all(entry is fallback_info or entry.denominator is None
                    for entry in resolved)):
        result.page_scale = fallback_info

    if unresolved:
        warn("SCALE_UNRESOLVED", "warning",
             f"Page {page_number}: no scale resolved for {', '.join(unresolved)}")

    if newly_entered and pdf_path:
        try:
            save_stored(pdf_path, page_number, newly_entered)
        except Exception as e:
            warn("SCALE_STORE_WRITE_FAILED", "warning",
                 f"Page {page_number}: scale entered but not saved ({e})")

    return result
