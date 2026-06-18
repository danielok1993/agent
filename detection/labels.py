from __future__ import annotations
import re
from models import BBox, Candidate, TextSpan
from detection.geometry import _bbox_center, _distance

# ---------------------------------------------------------------------------
# Label detection constants
# ---------------------------------------------------------------------------
LABEL_PATTERN               = re.compile(r"(?i)^[A-Z]{1,4}-?\d{1,4}[A-Z]?$")
LABEL_MAX_FONT_SIZE_PT      = 14.0
LABEL_MIN_FONT_SIZE_PT      = 4.0
LABEL_SEARCH_RADIUS_PX      = 80.0


def _find_nearby_label(
    bbox: BBox,
    text_spans: list[TextSpan],
    radius: float,
    pattern: re.Pattern,
) -> str | None:
    cx, cy = _bbox_center(bbox)
    best = None
    best_dist = float("inf")
    for span in text_spans:
        if not pattern.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue
        scx, scy = _bbox_center(span.bbox)
        d = _distance((cx, cy), (scx, scy))
        if d <= radius and d < best_dist:
            best_dist = d
            best = span.text
    return best


def detect_labels(text_spans: list[TextSpan], candidates: list[Candidate]) -> list[Candidate]:
    """Detect architectural labels (e.g. D-01, W-03) near geometric candidates.

    Requires the span to match the label pattern AND to be within
    LABEL_SEARCH_RADIUS_PX of a geometric candidate. Confidence scales with
    proximity: close labels are more likely to tag the adjacent element.
    Spans that match the pattern but have no nearby candidate are dropped to
    avoid promoting dimension callouts (300, 150, etc.) that have no element
    within radius.
    """
    label_candidates = []
    cand_idx = 0
    for span in text_spans:
        if not LABEL_PATTERN.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue

        nearest_id = None
        nearest_dist = float("inf")
        for c in candidates:
            d = _distance(_bbox_center(span.bbox), _bbox_center(c.bbox))
            if d < nearest_dist:
                nearest_dist = d
                nearest_id = c.candidate_id

        # Only emit if a geometric candidate is within the search radius
        if nearest_dist > LABEL_SEARCH_RADIUS_PX:
            continue

        # Confidence: 0.80 at distance 0, falls linearly to 0.50 at radius edge
        proximity = 1.0 - (nearest_dist / LABEL_SEARCH_RADIUS_PX)
        confidence = round(0.50 + 0.30 * proximity, 3)

        label_candidates.append(Candidate(
            candidate_id=f"label_{cand_idx:04d}",
            entity_type="label",
            bbox=span.bbox,
            confidence=confidence,
            evidence={
                "text": span.text,
                "font": span.font,
                "size": span.size,
                "nearest_candidate": nearest_id,
                "nearest_dist_px": round(nearest_dist, 1),
            },
        ))
        cand_idx += 1

    return label_candidates
