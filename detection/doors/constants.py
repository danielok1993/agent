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

# ---------------------------------------------------------------------------
# Sliding-door detection (detection/doors/sliding.py)
# Sliding doors have NO swing arc; the symbol is one or two thin panel
# rectangles lying in the wall plane. Two sub-patterns, calibrated on
# 5-1133-WD03.pdf (GD4/GD5: leaf pairs; GD9: pocketed single leaf) with
# floor-plans.pdf as the zero-detection control:
# - leaf_pair: two parallel near-equal thin panels IN THE SAME BAND (near-zero
#   lateral offset) partially overlapping along their axis. Measured overlaps:
#   0.50 and 0.73. Laterally STACKED equals (offset ≈ one thickness) are wall
#   band plies (the WALL TYPE 4 stack measures d_lat ≈ 1.0×thickness,
#   overlap 0.94) and duplicated fixture symbols measure overlap 1.0 — both
#   excluded by the lateral factor and the overlap ceiling.
# - pocket_leaf: one white panel flanked on BOTH sides by wall-face lines over
#   part of its length (in the pocket) and protruding into clear space (the
#   doorway). An open hinged leaf lying against a wall is flanked on ONE side
#   only (GD7 measures lateral offset ≈ 20px) and additionally overlaps its
#   own swing arc, so pocket candidates overlapping any collected swing are
#   vetoed. Wall cavity strips protrude into hatched wall continuation, which
#   the protrusion-zone crossing-line check rejects.
# All geometry is computed on oriented rectangles (corner fit), so both
# patterns are rotation-independent; scale is bounded by DOOR_MIN/MAX_SIZE_PX.
DOOR_SLIDE_PANEL_MIN_THICKNESS_PX = 3.0   # thinner is a shower screen / glazing strip (measured 2.0-2.5)
DOOR_SLIDE_PANEL_MAX_THICKNESS_PX = 20.0  # panels measure ~6px at 1:50; headroom for larger scales
DOOR_SLIDE_RECT_PARALLEL_TOL_DEG  = 8.0   # opposite-side parallelism for the oriented-rect fit
DOOR_SLIDE_RECT_PERP_TOL_DEG      = 12.0  # adjacent-side perpendicularity for the oriented-rect fit
DOOR_SLIDE_PANEL_MERGE_TOL_PX     = 2.0   # white ring + stroked qu of the SAME panel merge into one
DOOR_SLIDE_AXIS_TOL_DEG           = 6.0   # panel axes must be parallel; folded (bifold) leaves measure 16-20° apart
DOOR_SLIDE_LENGTH_RATIO_TOL       = 0.15  # leaf-pair panels are equal panels of one door (measured 0.00)
DOOR_SLIDE_LATERAL_FACTOR         = 0.75  # max lateral offset as fraction of avg thickness (doors ≈ 0.02×;
                                          # wall plies ≈ 1.0×; GD7 open leaf vs wall face ≈ 3×)
DOOR_SLIDE_OVERLAP_MIN_FRAC       = 0.20  # axial overlap of the pair (collinear abutting wall rects ≈ 0.0)
DOOR_SLIDE_OVERLAP_MAX_FRAC       = 0.90  # duplicated symbols measure 1.0; wall plies 0.94
DOOR_SLIDE_FLANK_GAP_MIN_PX       = 0.5   # flank face just outside the panel edge...
DOOR_SLIDE_FLANK_GAP_MAX_PX       = 12.0  # ...but within a pocket cavity's width (GD9 gaps: 2.9-6.1)
DOOR_SLIDE_FLANK_LINE_MIN_LEN_FRAC = 0.4  # a flank face is a wall line, not a tick (× panel length)
DOOR_SLIDE_FLANK_SIDE_MIN_FRAC    = 0.25  # each side must cover this much of the panel axially
DOOR_SLIDE_FLANK_MIN_FRAC         = 0.35  # both-sides (pocketed) coverage: GD9 measures 0.74;
DOOR_SLIDE_FLANK_MAX_FRAC         = 0.90  # near-total flanking = embedded wall strip, not a leaf
DOOR_SLIDE_PROTRUSION_MIN_FRAC    = 0.08  # leaf tip must stick out of the pocket (GD9: 0.27)
DOOR_SLIDE_PROTRUSION_MAX_FRAC    = 0.65  # mostly-out ⇒ flanking is coincidence, not a pocket
DOOR_SLIDE_ZONE_WIDTH_FACTOR      = 3.0   # protrusion-zone half-width = this × panel half-thickness
DOOR_SLIDE_ZONE_MAX_CROSSERS      = 2     # jamb/end-cap linework in the zone is ≤2 short crossers;
                                          # wall hatch continuation measures ≥3
DOOR_SLIDE_ASSEMBLY_BASE          = 0.65  # same tier as the qu/re rect-leaf swing assembly

# parked_leaf sub-pattern: a single thin closed panel parked flush along one
# face of a wall band that ENDS at a jamb, with a clear opening of ~one panel
# length beyond the jamb (the slide law: the panel covers the opening when
# slid along its own axis). This is the fill-less drawing style (Microsoft
# Print to PDF flattens fills away), so the panel may be a closed STROKED
# `l` ring — the white joinery signature is replaced by the band + jamb +
# slide-law evidence. Calibrated on floor-plans.pdf door_0011 (panel 3.0 ×
# 51.25 px hugging the hall jamb band at gap 0.75, opening span 51.25).
DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX = 1.0  # stroked rings snap at CAD precision; the white-ring 3.0px
                                           # buckets chain a stroked ring into the surrounding wall
                                           # linework (measured: ring 954/955 bucket-merges with wall
                                           # face 951 at tol 3, component >8 segs, ring rejected)
DOOR_SLIDE_PARK_GAP_MAX_PX     = 6.0   # panel-to-band-face gap; parked means flush (measured 0.75).
                                       # Tighter than the pocket cavity's 12: no pocket walls here.
DOOR_SLIDE_PARK_FACE_COVER_MIN = 0.80  # the hugged band face runs behind (almost) the whole panel
                                       # (measured 0.94); a short face is a sill/tick, not the band
DOOR_SLIDE_PARK_BAND_MIN_TH_PX = 2.0   # face + partner face = a wall band, not a lone line
DOOR_SLIDE_PARK_BAND_MAX_TH_PX = 20.0  # (measured 7.0); beyond is two unrelated parallel walls
DOOR_SLIDE_PARK_JAMB_TOL_PX    = 8.0   # band end vs panel end alignment (measured 3.0 overhang);
                                       # a parked panel sits AT its jamb, not mid-band
DOOR_SLIDE_PARK_SPAN_RATIO_TOL = 0.15  # slide law: opening span ≈ panel length (measured 0.000);
                                       # a random gap beside a shelf won't match its rect's length

# ---------------------------------------------------------------------------
# Folding/bifold-door detection (detection/doors/folding.py)
# Folding doors have NO swing arc either; the symbol is a run of equal thin
# leaf panels HINGED end-to-end at a shallow fold angle. Calibrated on
# 5-1133-WD03.pdf (GD2 trifold: 3-leaf concertina chain drawn nearly closed;
# the kitchen CL doors and the W9 folding wall: two 2-leaf V-stacks parked at
# opposite jambs of one opening) with floor-plans.pdf as the zero-detection
# control. Panels reuse the sliding collector (white ring + stroked qu), but
# hinged leaves share ring VERTICES, so the closed-loop white-ring
# reconstruction rejects them (degree-4 hinge vertex) — folding.py re-absorbs
# the coincident white `l` edges onto the stroked-qu panels and then REQUIRES
# the white joinery signature on every leaf.
DOOR_FOLD_ANGLE_MIN_DEG    = 8.0   # adjacent-leaf axis delta; below is sliding/collinear territory
                                   # (sliding pairs measure ≤6°, GD2's shallowest fold is 10.1°)
DOOR_FOLD_ANGLE_MAX_DEG    = 30.0  # above is corner joinery / 45° bay glazing, not a fold
                                   # (measured folds: 10.1-20.8°)
DOOR_FOLD_LENGTH_RATIO_TOL = 0.15  # leaves of one door are equal panels (measured ≤0.005)
DOOR_FOLD_HINGE_TOL_PX     = 6.0   # min corner-to-corner distance at the hinge (leaves share the
                                   # ring vertex exactly; qu-vs-ring fit offsets measure ≤0.3)
DOOR_FOLD_MIN_CHAIN_LEAVES = 3     # a standalone hinged chain needs 3+ leaves (GD2); a lone 2-leaf
                                   # V is not emitted — too weak without a partner stack
DOOR_FOLD_STACK_SPAN_RATIO_TOL  = 0.20  # two parked stacks pair only when the outer span between
                                        # them ≈ Σ leaf lengths (the unfolded leaves must cover the
                                        # opening; measured 0.015 and 0.001)
DOOR_FOLD_STACK_MIRROR_TOL_DEG  = 15.0  # stacks fold off the SAME wall plane: mean leaf angles
                                        # mirror about the opening axis (measured ≤0.3°)
DOOR_FOLD_STACK_PERP_EXTENT_MAX = 1.25  # a folded stack projects ≤ ~one leaf length perpendicular
                                        # to the opening axis (measured 0.99-1.00×)
DOOR_FOLD_ASSEMBLY_BASE    = 0.65  # same tier as sliding / qu-re rect-leaf swing assemblies

# open_v sub-pattern: a lone bifold drawn HALF-OPEN as a wide V of two thin
# double-line stroked leaves (the fill-less drawing style — no white rings,
# no qu rects, each leaf is just two near-parallel `l` lines a hair apart).
# The missing white signature is replaced by physical gates: leaf axes mirror
# about the tip-to-tip axis, at least one tip anchors on wall-line jamb ENDS
# parallel to that axis, and the jamb-to-jamb span obeys the span law
# (≈ Σ leaf lengths). Calibrated on floor-plans.pdf paths 1739-1742 (two
# 24.7/23.4 px leaves folded 71.2°, span 55.85 vs Σ 48.05 → dev 0.162).
DOOR_FOLD_OPEN_ANGLE_MIN_DEG   = 40.0  # below is the nearly-closed territory of chain/stack_pair
                                       # (measured folds there 10.1-20.8°); a half-open V is wide
DOOR_FOLD_OPEN_ANGLE_MAX_DEG   = 85.0  # capped BELOW 90 so orthogonal corner joinery (counter/
                                       # wardrobe L-corners) can never match (measured V: 71.2°)
DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG = 8.0   # leaf lines must be oblique: a half-open V off a straight
                                       # wall is never axis-aligned, and this excludes the page's
                                       # bulk axis-aligned linework from the O(n²) pair search
DOOR_FOLD_LEAF_LINE_SEP_MIN_PX = 0.8   # double-line leaf lateral separation (measured 1.9-2.5);
DOOR_FOLD_LEAF_LINE_SEP_MAX_PX = 4.0   # 45° hatch at the corpus' tightest 5.7px pitch = 4.03 sep
DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN = 0.75  # the two edge lines of one leaf (measured 0.915 — the
                                          # inner edge is foreshortened at the hinge miter)
DOOR_FOLD_LEAF_LINE_OVERLAP_MIN = 0.6  # axial overlap of the edge lines (× shorter length)
DOOR_FOLD_JAMB_ANCHOR_TOL_PX   = 6.0   # jamb line endpoint to leaf tip (measured 3.4/3.6)
DOOR_FOLD_JAMB_LINE_MIN_LEN_PX = 15.0  # a jamb anchor is a wall face, not a cap/tick
DOOR_FOLD_JAMB_AXIS_TOL_DEG    = 15.0  # jamb faces run along the opening axis (measured 2.2°)
DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX = 6.0  # lateral half-width of the opening corridor searched for
                                         # the far jamb endpoint and crossers (band half-thickness
                                         # scale; measured far-jamb lateral offsets 1.2-1.8)
