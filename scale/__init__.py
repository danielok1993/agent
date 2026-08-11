"""Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan."""
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

__all__ = [
    "AGREEMENT_TOLERANCE",
    "MM_PER_PT",
    "PAPER_SPACE_MAX_DENOMINATOR",
    "canonical_denominators",
    "cluster_denominators",
    "denominator_from_c",
    "format_scale",
    "snap_to_standard",
]
