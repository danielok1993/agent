"""Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan."""
from models import ScaleInfo
from scale.dimensions import (
    DimensionMatch, dimension_matches, measured_denominator, page_dimensions,
)
from scale.factor import (
    DETECTION_FACTOR_MAX, DETECTION_FACTOR_MIN,
    DETECTION_REFERENCE_DENOMINATOR, DetectionScale, detection_scale,
)
from scale.resolver import PageScales, bind_scale, binding_texts, resolve_page_scales
from scale.text import scales_in_text, text_scales
from scale.units import (
    AGREEMENT_TOLERANCE,
    MM_PER_PT,
    PAPER_SPACE_MAX_DENOMINATOR,
    canonical_denominators,
    cluster_denominators,
    denominator_from_c,
    format_scale,
    snap_to_standard,
)
from scale.viewport import viewport_scales

__all__ = [
    "AGREEMENT_TOLERANCE",
    "DETECTION_FACTOR_MAX",
    "DETECTION_FACTOR_MIN",
    "DETECTION_REFERENCE_DENOMINATOR",
    "DetectionScale",
    "DimensionMatch",
    "MM_PER_PT",
    "PAPER_SPACE_MAX_DENOMINATOR",
    "PageScales",
    "ScaleInfo",
    "bind_scale",
    "binding_texts",
    "canonical_denominators",
    "cluster_denominators",
    "denominator_from_c",
    "detection_scale",
    "dimension_matches",
    "format_scale",
    "measured_denominator",
    "page_dimensions",
    "resolve_page_scales",
    "scales_in_text",
    "snap_to_standard",
    "text_scales",
    "viewport_scales",
]
