from __future__ import annotations
import re

# ---------------------------------------------------------------------------
# Door detection constants
# ---------------------------------------------------------------------------
DOOR_BBOX_ASPECT_MIN        = 0.85   # width/height ratio (roughly square arc)
DOOR_BBOX_ASPECT_MAX        = 1.15
DOOR_MIN_SIZE_PX            = 20.0
DOOR_MAX_SIZE_PX            = 200.0
DOOR_SWING_LINE_DIST_PX     = 15.0  # max px from arc corner to nearby line endpoint
DOOR_LABEL_PATTERN          = re.compile(r"(?i)^[A-Z]?[FD]-?\d{1,3}[A-Z]?$")
DOOR_LABEL_SEARCH_RADIUS_PX = 100.0
DOOR_MIN_CONFIDENCE         = 0.40
DOOR_POLYLINE_MIN_SEGMENTS  = 4
DOOR_POLYLINE_MAX_SEGMENTS  = 24
DOOR_POLYLINE_MAX_SEG_PX    = 18.0
DOOR_POLYLINE_ENDPOINT_TOL  = 2.0
DOOR_POLYLINE_SPUR_MAX_SEGMENTS = 4   # max chain length (segments) of a leaf-spur that gets pruned from an arc component
# Max per-segment angle change (degrees) for a chain to count as "arc-like
# continuity". A 4-seg quarter arc has ~22.5°/seg, so 45° gives headroom for
# jitter while catching the perpendicular angle jump where a flat cap meets the
# arc's natural endpoint (e.g. a 90° break from tangent into a horizontal cap
# line).
DOOR_POLYLINE_CHAIN_DELTA_DEG = 45.0
# Max number of segments in a closed-loop cap (e.g. door stop drawn as a closed
# rectangle) attached at the arc's natural endpoint via a single junction.
# floor-plans.pdf's polyline_856 has a 7-seg cap loop; 8 gives a small margin.
DOOR_POLYLINE_CYCLE_MAX_SEGMENTS = 8
# Double-arc / garden-door split detection. A 2-leaf simple chain that walks
# leaf→hinge→leaf produces ~180° walk-direction break at the hinge between the
# two halves. Distinguishes from §3.6 (linear cap extension), where the trimmed
# side is a short axis-aligned cap. Both halves must clear these floors to
# qualify for split-into-two-swings instead of trim-one-half.
DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS    = 4   # each half must be a viable arc on its own
DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS  = 3   # each half must have curvature (not axis-aligned)
# Endpoint coincidence tolerance for pairing two native `curve_arc` swings
# into a garden-door composite (the §3.7 pattern, but where each half is a
# single Bezier rather than a polyline-arc BFS chain). Tighter than
# DOOR_ASSEMBLY_CONNECT_TOL_PX (15) because we are matching CAD-precise
# curve endpoints, not loose leaf-to-arc snaps; 3 px keeps unrelated nearby
# arcs from being falsely partnered.
DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX = 3.0
# Endpoint snap tolerance for chaining native (`c`) Bezier curves into a
# single logical arc. PDF curves emitted by CAD tools have machine-precise
# endpoints; 1.0 px is generous.
DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX = 1.0
# Minimum number of native `c` primitives in a chain to qualify for the
# chained-arc swing path (rather than each curve being scored individually
# by _is_arc_like). 2+ means the chain is genuinely fragmented across
# multiple Beziers.
DOOR_CURVE_CHAIN_MIN_CURVES = 2
DOOR_LAYER_KEYWORDS         = ["door", "a-door"]
DOOR_ASSEMBLY_CONNECT_TOL_PX = 15.0
DOOR_LEAF_RADIUS_RATIO_TOL   = 0.20
DOOR_FALLBACK_CONFIDENCE     = 0.35
DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX = 3.0
DOOR_LINEWORK_LEAF_MIN_SEGMENTS    = 4
DOOR_LINEWORK_LEAF_MAX_SEGMENTS    = 8
# Subgraph-fallback bound: components larger than the clean-loop ceiling but still
# small enough to enumerate 4-cycles inside. Captures a leaf rectangle with a few
# attached spurs (typically a threshold line and/or 1-2 wall stubs).
DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS = 14
DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG          = 8.0   # opposite-side ∥ tolerance for thin-rectangle 4-cycle
DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG     = 12.0  # adjacent-side ⟂ tolerance for thin-rectangle 4-cycle
DOOR_THRESHOLD_ENDPOINT_TOL_PX            = 6.0   # threshold endpoint ↔ leaf long-edge corner snap tol
DOOR_THRESHOLD_PARALLEL_TOL_DEG           = 8.0   # threshold direction ‖ leaf long axis
DOOR_THRESHOLD_CONFIDENCE_BOOST           = 0.10  # confirmatory boost when an entrance threshold is found
DOOR_POLYLINE_MAX_ANGLE_BINS              = 7     # quarter-circle spans ≤7 bins of 15°; rejects furniture/appliance curves
DOOR_DOUBLE_LEAF_GAP_PX                  = 12.0  # max gap between leaf long-axis intervals to form a double door
DOOR_DOUBLE_LEAF_OVERLAP_PX              =  5.0  # max overlap tolerated on leaf long-axis intervals
DOOR_DOUBLE_LEAF_CENTER_TOL_PX           =  8.0  # max offset between leaf long-axis centerlines
DOOR_V2_BRIDGE_BUFFER_PX          = 3.0   # max dist from bridge line for an obstructing segment
DOOR_V2_OPENING_CLEAR_BOOST       = 0.07  # confidence boost when verified-clear door opening
DOOR_V2_OPENING_OBSTRUCTED_PENALTY = 0.12  # confidence penalty when opening has crossing lines

# ---------------------------------------------------------------------------
# Single-line leaf detection (swing-anchored)
# Many CAD drawings represent the door panel as a single line, not a closed
# rectangle. The clean-loop / subgraph leaf collectors miss those entirely.
# A swing-anchored pass searches around each unpaired arc for a single line
# whose endpoint snaps to an arc endpoint and whose length matches the arc
# radius — the architecturally correct "leaf at end of curve" condition.
# ---------------------------------------------------------------------------
DOOR_LEAF_LINE_ENDPOINT_TOL_PX = 5.0
DOOR_LEAF_LINE_LENGTH_TOL      = 0.20
DOOR_LEAF_LINE_AXIS_TOL_DEG    = 8.0
DOOR_LEAF_COMPANION_PERP_PX    = 5.0    # max perpendicular distance for a parallel companion line
DOOR_LEAF_COMPANION_OVERLAP    = 0.50   # min projected overlap (vs companion length) to count
DOOR_ASSEMBLY_LINE_LEAF_BASE   = 0.60   # one slot below the 0.65 rect-leaf base
DOOR_ARC_FALLBACK_MAX          = 0.45   # cap so arc_fallback stays under OFFLINE_MIN_CONFIDENCE["door"] = 0.55

# ---------------------------------------------------------------------------
# Hu Moments constants (Step 4 of v2 spec)
# Template derived from 4 confirmed door arcs in floor-plans.pdf page 1.
# 6 moments only — moment 7 flips sign with arc reflection orientation.
# ---------------------------------------------------------------------------
DOOR_HU_CANVAS_SIZE         = 64    # rasterize candidate arc to this square canvas
DOOR_HU_THRESHOLD_VERIFIED  = 0.15  # distance < this → strong shape match
DOOR_HU_THRESHOLD_FAR       = 0.50  # distance > this → penalize
DOOR_HU_VERIFIED_BOOST      = 0.20  # rescues arc_fallback from 0.35 → 0.55
DOOR_HU_PLAUSIBLE_BOOST     = 0.08  # plausible match
DOOR_HU_FAR_PENALTY         = 0.10  # poor match
_DOOR_HU_TEMPLATE_VALUES    = [1.518423, 3.112955, 5.232975, 6.148173, -9.994192, -7.721678]

DOOR_LEAF_ASPECT_MIN = 4.0   # door leaf is long and thin, not square
