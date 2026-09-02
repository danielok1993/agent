"""Wall-network builder.

Walls are internal-only data: they are never emitted as candidates. The
network of wall centerlines feeds room polygonization (detection/rooms.py)
and door/window cross-validation (detection/postprocess.py).

Pipeline: collect wall faces (long solid strokes + filled bands) -> merge
collinear faces -> pair near-parallel faces into centerlines carrying
thickness -> merge/snap/extend into a connected network -> node with
shapely for downstream polygonization.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from models import BBox, PathPrimitive, TextSpan
from detection.geometry import (
    _angle_diff_mod180,
    _distance,
    _bbox_expanded,
    _bboxes_overlap,
    _line_angle_deg,
    _line_length,
    _perpendicular_spacing,
    _point_in_bbox,
    _point_to_segment_distance,
    _project_onto_axis,
    _projected_interval,
    _segments_min_distance,
)
from detection.layers import (
    LAYER_CLASS_KEYWORDS, _layer_annotation_veto, _layer_hint_from_layer,
)

# ---------------------------------------------------------------------------
# Wall-network constants
# ---------------------------------------------------------------------------
WALL_MIN_STROKE_WIDTH_PX    = 0.5   # filters hairline hatch/dimension strokes
WALL_FACE_MIN_LEN_PX        = 11.0  # min wall piece between adjacent openings:
                                    # a one-thickness jamb nib. 100mm at 1:50
                                    # is 11.8px and s03 draws its nibs at
                                    # 11.75px (viewport 1:49.99) — a 12.0 floor
                                    # excluded the nominal minimum it names,
                                    # dropped the nib faces below door_0018,
                                    # and the doorway plug lost its bottom
                                    # anchor (end_cov 0.29 < 0.5), so the
                                    # dilated-bbox fallback fenced the swing
                                    # square out of the bedroom. Dimension
                                    # ticks (7-13px) already overlap the floor
                                    # and are recognised by their own rule
                                    # (_dimension_line_indices), never by
                                    # length.
WALL_FACE_MERGE_GAP_PX      = 6.0   # drafting artifacts only; door/window openings stay open
WALL_MIN_THICKNESS_PX       = 2.0   # thinnest partition at 150 DPI
WALL_MAX_THICKNESS_PX       = 36.0  # heavy exterior/party walls (a 1:50 blockwork
                                    # band runs ~32px); corridors are far wider
WALL_THICK_MATERIAL_MAX_PX  = 48.0  # locally thickened masonry (chimney breast /
                                    # pier: floor-plans' bedroom pier bulges its
                                    # 19px wall to 39px; a 1:50 400mm band is
                                    # ~47px). Strong-face pairs in the 36-48px
                                    # gap form ONLY when the band between the
                                    # faces carries drawn wall material — an
                                    # unpaired pier encloses its hatch as a
                                    # free-space pocket = phantom room
WALL_THROUGH_HATCH_MAX_PX   = 64.0  # a band hatched THROUGH — diagonal strokes
                                    # ending on BOTH faces, clipped to the band
                                    # by the hatch tool — is cut material at any
                                    # thickness up to this (a 1:50 540mm band).
                                    # Strong-face pairs spaced between
                                    # WALL_THICK_MATERIAL_MAX_PX and this form
                                    # ONLY on through-hatch (_band_has_through_
                                    # hatch): measured on s05 (1:100, f=0.5),
                                    # the first-floor left external wall is a
                                    # 28px band (~475mm; 56px at identity) of
                                    # 104 strokes at 135°, each 39px = 28 × √2,
                                    # at 6.2px pitch — past the scaled 24px
                                    # thick cap, its interior was fenced as a
                                    # 24×468px phantom room. The sheet's other
                                    # bands top out at 17.8px; corpus bands at
                                    # identity reach 39px (s01). A floor pattern
                                    # or fixture hatch is clipped to its own
                                    # boundary, never to two wall-pen faces at
                                    # wall spacing — hatch stopping short of the
                                    # faces is not through-hatch.
WALL_PARALLEL_ANGLE_TOL     = 4.0   # degrees, matches WINDOW_ANGLE_TOL_DEG
WALL_BAND_MIN_ASPECT        = 3.0   # filled rect must be band-like, not a fixture block
WALL_PAIR_MIN_OVERLAP_PX    = 12.0  # shorter face-pair overlap is coincidence
WALL_PAIR_TAPER_MAX_FRAC    = 0.5   # a face pair's spacing may change by at most
    # this fraction of itself between the two ends of the overlap
    # (dimensionless). A wall's two faces are drawn parallel — one band, one
    # thickness — so a real pair's spacing is the same at both ends: on the
    # corpus (2026-09-02) every surviving real pair measures <= 0.30, the
    # widest being s03's tapering rear boundary wall at 0.24-0.27 (15.4 ->
    # 11.7px over 142px), then s17 0.30, s18 0.20, s01 0.16, s02 0.11, the
    # rest <= 0.07. A stroke crossing the band corner to corner lies inside
    # WALL_PARALLEL_ANGLE_TOL of both faces (an aspect-15 cell: 3.9 deg) yet
    # its spacing to either runs from the band's full width to ZERO: ratio
    # 1.0 on all four sheets it was measured on (s03 0 -> 14.8px at 1:50
    # and 0 -> 7.5px at 1:100, s04 0 -> 5.3, s08 0 -> 21.3, s20 0 -> 12).
    # Those corpus strokes were later identified (2026-09-02) as the
    # triangulation SEAMS of filled wall bands — a self-coloured width-0
    # stroke on the shared diagonal (s03 EXISTING_BRICKWORK, s04/s08
    # RR_Wall Hatches carry the wall FILL, not hatch) — and seams are now
    # excluded before pairing (_fill_seams joins the exclusion set in
    # detect_wall_network); this gate stays as the geometric defence for
    # any genuinely stroked chord. _perpendicular_spacing
    # samples ONE endpoint (fj.p1), which for a long merged face may lie
    # hundreds of px past the cell where the chord's line has drifted well
    # beyond the band: s03's 219px chord read 29px against the 992px far
    # face (first endpoint 650px away) and the centerline landed 14.5px on
    # the ROOM side of the chord, its solid fencing a 15-29px strip off the
    # bottom-right corner of BEDROOM rooms 0005 and 0013 (the far-side rule
    # could not catch it: the phantom band overlapped the wall's grey fill
    # by 0.24, past WALL_FAR_SIDE_FILL_COVER_MAX). Interpolating the spacing
    # at both ends of the overlap and rejecting a change over half of itself
    # leaves ~2x margin to each class. The only other corpus pairs above the
    # gate are 12px stubs at 1px spacing on the vector-text sheets s11/s16
    # (glyph strokes, 0.67) — not walls either. Chords pairing with the
    # NEXT cell's face (s04/s20, 0.30-0.49) stay: those centerlines lie
    # inside the wall band and are harmless.
WALL_CENTERLINE_MERGE_GAP_PX = 8.0  # dedupe centerlines produced by multiple partner pairs
WALL_JUNCTION_SNAP_PX       = 8.0   # endpoint-to-intersection reach beyond partner thickness/2
WALL_JUNCTION_MIN_ANGLE_DEG = 10.0  # below this, line intersections are unstable (collinear-merge territory)
WALL_NETWORK_MIN_SEGMENTS   = 4     # below this the network is treated as empty everywhere

WALL_LAYER_KEYWORDS = LAYER_CLASS_KEYWORDS["wall"]

WALL_LIGHT_PEN_MIN_CHANNEL  = 0.70  # stroke colors with EVERY channel at/above
    # this are faint reference ink — the light-grey overhead/hidden pen
    # (RSJ beam lines, VELUX rooflight boxes print at 0.86 grey on
    # floor-plans, IN the wall pen widths, and their double lines pair into
    # phantom partitions spanning the open-plan kitchen). Demoted to the
    # material-gated weak pipeline exactly like sub-gate pen widths: faint
    # ink needs drawn wall material between its faces. Saturated pens (red,
    # blue, magenta) all carry a 0 channel and are unaffected; on drawings
    # that encode hierarchy by width alone (5-1133, all-black), this is a
    # no-op.

# Dimension-chain recognition: an architectural dimension line carries a
# short oblique tick (~45 deg to the line) CENTERED on each of its endpoints
# and straddling it — the universal CAD dimension terminator. Wall faces
# never match: hatch/blocking strokes touch a face from inside the band
# (they do not straddle it), and a tick-like chamfer at a wall corner meets
# the face END-to-end (its midpoint is off the endpoint by half its length).
# Requiring BOTH endpoints ticked keeps a wall that a dimension chain merely
# terminates against (the tick sits mid-run there, not at the wall's ends).
WALL_DIM_TICK_MIN_LEN_PX    = 3.0
WALL_DIM_TICK_MAX_LEN_PX    = 16.0   # measured 7-13px on floor-plans; blocking
                                     # X's of oblong rects are longer and stay
WALL_DIM_TICK_END_TOL_PX    = 3.0    # tick midpoint-to-endpoint distance
                                     # (measured <= 0.3px on floor-plans)
WALL_DIM_TICK_ANGLE_MIN     = 20.0   # tick-vs-line angle window, matching the
WALL_DIM_TICK_ANGLE_MAX     = 70.0   # material-mark diagonal window
WALL_DIM_TICK_STRADDLE_MIN_PX = 1.0  # both tick ends clear the line by this
# The other common terminator is an OPEN ARROWHEAD: two short barbs meeting
# AT the endpoint, one on each side of the line, at a shallow angle to it
# (measured on s16: 9px barbs at ~12deg; an unrecognized "3550" dimension
# and its end bar fenced a 205x38px strip out of a room). Hatch strokes touch
# a face end from INSIDE the band — one side — so a barb pair on opposite
# sides is never wall linework.
WALL_DIM_ARROW_ANGLE_MIN    = 5.0    # barb-vs-line angle window
WALL_DIM_ARROW_ANGLE_MAX    = 45.0

# VECTOR TEXT: sheets whose labels are drawn as stick-font glyphs — every
# letter a cluster of short `l` strokes, no text span at all (s06/s11/s16/
# s20/s13; s06 has 8 spans and 24k glyph strokes). The strokes share the
# wall pen (s06: 0.75px, the wall reference itself) and at 1:100 a 9.5-12px
# glyph stem clears the scaled 5.5px face floor; the parallel stems of an
# H/N/"IL" even pair at 6-10px spacing into mini bands, and the room outline
# is forced around the word wherever the cluster chains to a plug or wall
# (s06 BATH & TOILET / LANDING). The convention: wall linework is CONNECTED —
# a nib meets its band, hatch meets its faces, treads meet the stringer —
# while glyph ink is freestanding and comes in an aligned ROW of
# glyph-sized components (common cap/base line, gaps under one glyph
# height). One freestanding glyph-sized box is a pier/pattern cell, never a
# row (s01's hob rings and sink bowls, s17's trees and RWP symbols do form
# rows and are excluded too: fixture symbols, never wall). Paper-space:
# text height is a drafting convention (measured 8.7-29px across the corpus,
# 2.5mm = 14.8px), not a world length.
WALL_TEXT_GLYPH_MAX_PX      = 30.0  # 5mm text: nothing larger is a glyph, and
                                    # touching anything larger disqualifies
WALL_TEXT_GLYPH_MIN_PX      = 4.0   # a glyph has extent across the line (a
                                    # dash row has none)
WALL_TEXT_TOUCH_PX          = 0.6   # stroke-to-stroke contact tolerance
WALL_TEXT_ALIGN_TOL_PX      = 1.5   # cap OR base line agreement along a row
WALL_TEXT_MIN_GLYPHS        = 3     # row length
WALL_TEXT_MIN_MULTI_STROKE  = 2     # members drawn with >= 2 strokes (hatch
                                    # strokes are single)
WALL_TEXT_ANGLE_DIVERSITY   = 20.0  # degrees between some two strokes of the
                                    # row (a loose hatch row is one angle)

WALL_BACKGROUND_FILL_MIN    = 0.97  # every channel at/above this = page background;
                                    # unstroked white shapes are text masks and
                                    # counter tops, never wall material
WALL_FILL_CLASS_MIN_INK_PX  = 150.0 # rate a fill color only once its closed rings
                                    # carry this much run length; rarer fills keep
                                    # the permissive legacy treatment
WALL_FILL_BLOCK_MAX_SIDE_PX = 72.0  # wall-rated rings up to this equivalent short
                                    # side become barrier polygons (bands, corner
                                    # posts, piers); larger blobs (shaded zones)
                                    # contribute outline faces only
WALL_FILL_MERGE_MIN_FRAC    = 0.5   # a collinear merge keeps wall_fill only when
                                    # fill-outline members cover at least this
                                    # fraction of the merged run: a fill ring's
                                    # short edge stub (a jamb, 17px) collinear
                                    # with a 354px stroke must not launder fill
                                    # evidence over the whole stroke (measured
                                    # on s03: roof-tile stripes over the wall
                                    # band's end stubs became full-height
                                    # wall-fill barriers). A fill outline with
                                    # its own drawn-over stroke covers ~1.0.
WALL_MARKER_MAX_SIDE_PX     = 24.0  # leader/dimension arrowheads are ~2-4mm
                                    # filled triangles (12-24px at 150 DPI) drawn
                                    # in the wall pen; rings this small with a
                                    # triangle or concave-dart outline are
                                    # annotation glyphs, never material
WALL_FILL_CHAIN_REVISIT_TOL_PX = 0.01  # a fill chain that lands back ON its own
                                    # start vertex mid-way is one ring closing
                                    # and the next opening from that vertex —
                                    # a fan's second triangle (s20: triangle 2
                                    # starts at triangle 1's start) or the
                                    # neighbouring cell's first (s03: the
                                    # 16.5px cell beside the band opens on the
                                    # vertex the band's triangle closed on) —
                                    # never one polygon: shapely rejects the
                                    # self-touching ring and both pieces were
                                    # lost. EXACT, not the 2px closing
                                    # tolerance: the exporter re-emits the
                                    # shared vertex bit-for-bit, while a valid
                                    # ring may legitimately pass within 2px of
                                    # its start mid-way (a narrow notch) and
                                    # must not be split there. Measured
                                    # 2026-09-02: 0 valid rings touched on 13
                                    # sheets; recovered s20 19 chains -> 38
                                    # grey band rings, s04/s08 140/144 ->
                                    # 280/288 red slivers, s18 328 -> 434 black
                                    # rings (253 of them glyph outlines), s14
                                    # 77 -> 108, s03 7 -> 11
WALL_FILL_SEAM_PROBE_PX     = 1.0   # _fill_seams proves a coincident edge is a
                                    # seam by finding fill this far either side
                                    # of its midpoint (P: a sub-pen probe) ...
WALL_FILL_SEAM_PROBE_FRAC   = 0.5   # ... or this fraction of the thinnest
                                    # sharing ring's equivalent-rectangle short
                                    # side, whichever is smaller (D). A seam has
                                    # fill on both sides at ANY distance, so the
                                    # probe must stay inside the fill it tests:
                                    # at 1px it left every ring thinner than
                                    # 2px, and a sub-2px sliver's two triangles
                                    # never seam-united — each dilated alone
                                    # and the acute tip's mitre ran to the
                                    # ROOM_RING_MITRE_LIMIT cap, 2px past the
                                    # band's own standoff (s03 room_0007). A
                                    # thin triangle's short IS its inradius,
                                    # and the clearance at its hypotenuse's
                                    # midpoint measures 0.98-1.07 x short on
                                    # every corpus sliver (s03 0.375px halves
                                    # of a 0.75px sliver, s04/s08 0.312 of
                                    # 0.63px, s12 0.625, s17 0.62-0.80, s14
                                    # 0.25-0.87; measured 2026-09-02), so a
                                    # probe AT short lands on the boundary
                                    # (not `contains`) and half of it keeps a
                                    # 2x margin. Recovers s03 19/19, s04 61/61,
                                    # s08 63/63, s12 5/5, s17 80/80, s14 32/36
                                    # two-sided candidates that failed at 1px;
                                    # loses none on those sheets or s02, and
                                    # on s18 only 5 accidental "seams" between
                                    # glyph-outline bars 0.47px apart that the
                                    # 1px probe reached across. Rings >= 2px
                                    # short keep the 1px probe unchanged.

WALL_HATCH_MIN_SEGMENTS     = 5
WALL_HATCH_MIN_RATIO        = 0.45
WALL_HATCH_MAX_LEN_PX       = 48.0  # hatch strokes stay short; matches the 45px cap
                                    # in _wall_material_evidence plus slack. Hatch
                                    # stays IN the network (its face pairs thicken
                                    # wall solids) but is excluded from the rooms'
                                    # thin line barriers (rooms.py).

# Sub-threshold ("weak") wall faces: working drawings often pen new partition
# walls in the same hairline pen as fixtures and sanitary symbols (0.45px on
# the sample set), so pen weight alone cannot admit them without reopening
# every fixture false positive. A hairline face pair is accepted only when
# the band between the faces carries drawn wall MATERIAL — hatch strokes,
# cross-hatch, or the X'd blocking rectangles of stud/cavity partitions: short
# strokes DIAGONAL to the band axis, spread densely along the band. Liner
# lines run parallel and radiator/grille fins perpendicular, so neither
# counts. Density is the discriminator against the other things that pair at
# wall spacing: glazing strips and paving/steps linework measure <=2.6
# marks/100px on the sample set while real partition hatch/blocking measures
# >=4.8.
WALL_WEAK_STROKE_RATIO       = 0.66  # faces penned below this fraction of the
                                     # paired-wall stroke reference are demoted to
                                     # weak (material-gated) even when they clear
                                     # the absolute WALL_MIN_STROKE_WIDTH_PX:
                                     # floor-tile grids are drawn at ~half the wall
                                     # pen (0.75 vs 1.5 on the sample set) and
                                     # otherwise pair with the real wall faces they
                                     # run parallel to, stamping phantom wall bands
                                     # across room interiors. Same 2/3 rationale as
                                     # ROOM_BARRIER_STROKE_RATIO in rooms.py.
WALL_WEAK_MIN_RUN_PX         = 30.0  # min weak-pair centerline length: shorter
                                     # material-dense slivers are dimension-tick and
                                     # mullion clusters, and a real stub that short
                                     # sits between openings whose seals cover it
WALL_WEAK_MATERIAL_MIN_MARKS = 4     # short stubs (corner posts) still need a real X-block
WALL_WEAK_MATERIAL_MIN_SPAN  = 0.5   # marks must spread along the band, not clump at one end
WALL_RECT_MIN_ASPECT         = 2.0   # stroked-rectangle candidate prefilter (long/short):
                                     # NOT a wall discriminator — the s03 infill is 2.5, a
                                     # window frame 2.4, a door leaf 18 — only the material
                                     # gate decides; this just skips square symbol boxes
WALL_WEAK_MATERIAL_PER_100PX = 3.0   # min diagonal marks per 100px of band length
WALL_WEAK_MATERIAL_EDGE_PX   = 2.5   # marks this close to a band face don't count: a
                                     # dimension tick's midpoint lies ON the dimension
                                     # line it crosses, so when two dimension lines pair
                                     # into a band the ticks ride the faces, never the
                                     # interior. Real material (hatch runs, blocking X's)
                                     # has midpoints inside the band. Measured on 5-1133:
                                     # the "3.5 bricks/250" dimension line paired with a
                                     # 1281px setout hairline at wall-like spacing, and
                                     # its 3 ticks + 2 leader-arrowhead barbs passed the
                                     # gate, chopping the kitchen in two at y=365.
WALL_WEAK_MATERIAL_ANGLE_MIN = 20.0  # stroke-vs-band-axis window; wide enough for the
WALL_WEAK_MATERIAL_ANGLE_MAX = 70.0  # ~25deg/~65deg diagonals of oblong blocking rects
WALL_WEAK_CLAIM_MARGIN_PX    = 2.0   # a weak pair is dropped when a KEPT, meaningfully
                                     # tighter (by >= 2x this) parallel pair lies inside
                                     # its band over the same span: the material between
                                     # its faces belongs to that inner wall, not to it.
                                     # Measured on 5-1133: tile-grid line 992 (y=824.2)
                                     # paired with the WC/bath divider's far faces
                                     # (y=843.7) at th 19.5 and passed the material gate
                                     # on the divider's OWN cavity blocking — the true
                                     # divider pair (831.7/843.7, th 12) sits 7.5px
                                     # inside that band. The margin also keeps duplicate
                                     # same-band pairs (shared faces, edges within 2px)
                                     # from claiming each other.
WALL_FAR_SIDE_FILL_COVER_MAX = 0.10  # a strong pair sharing a face with a tighter
                                     # kept pair on the far side of that face is a
                                     # wall face paired across the room; it keeps
                                     # its band only when >= this fraction of the
                                     # band lies on wall-rated fill (or hatch backs
                                     # it) — see _claims_far_side_pair
WALL_WEAK_CLAIM_OVERLAP_FRAC = 0.5   # the inner pair must cover this fraction of the
                                     # weak pair's run — an inner stub elsewhere along a
                                     # long band says nothing about the material HERE

# Striped-field ("lattice") faces: paving bonds, tile fields, stair treads,
# roof tiling on elevations, table rows, balustrades, hatch. A run of
# parallel SAME-PEN faces at equal wall-like pitch is never wall structure —
# rooms are wider than WALL_MAX_THICKNESS_PX by definition, so real walls
# cannot stack five deep at wall pitch. Pen weight cannot catch these: the
# open-vestibule paving bond on 5-1133 is penned at 1.05 vs the 1.50 wall
# reference (ratio 0.70, above WALL_WEAK_STROKE_RATIO), and the sample set
# has real wall pens down to 0.67 of the reference, so the ratio gate cannot
# be raised. Demoted lattice faces re-enter the weak (material-gated)
# pipeline, so a hatched partition that happens to sit inside a striped
# field still comes back. Hatch is the same signature pitched too tightly
# to be walls (measured: both reference PDFs' hatch fields pitch at
# 4.05/4.07px, the tightest real striped field on either at 11.4px); two
# strokes of one field otherwise pair like any parallel pen mates, and at
# an L-corner the phantom diagonal band juts out of the wall (measured on
# floor-plans: strokes 2502/2516 of the 45deg field paired 28.1px apart and
# chamfered room_0000's and room_0001's top-right corners by ~16px).
# There is no length floor on a rung: stair treads (47.7px on s17), a
# ramp balustrade's 12.75px rungs (s18) and the tread pieces beside a
# stair void (43px on s01) are fields of short strokes, and short strokes
# at wall pitch five deep are still never walls.
WALL_LATTICE_MIN_RUNGS       = 5     # rungs per run; a 4-face cavity party wall
                                     # (leaf/cavity/leaf at equal width) stays wall
WALL_LATTICE_PITCH_TOL_PX    = 2.0   # rung pitch equality; also accepts one missing
                                     # rung (gap ~= 2x pitch, e.g. eaten by a text
                                     # mask — "VESTIBULE" ate the 1070.8 joint line)
WALL_LATTICE_TOUCH_GAP_PX    = 8.0   # rung extents must overlap or nearly touch the
                                     # run so far — staggered-bond joints on adjacent
                                     # courses meet end-to-end, while an unrelated
                                     # parallel face far along the axis is no rung.
                                     # Also the extent-cluster gap: collinear
                                     # pieces further apart than this at one offset
                                     # are separate rows (a room's wall face merely
                                     # collinear with a distant field's course is
                                     # not that course — s17's WC top face shared
                                     # its offset with a roof-tile rung 2000px away)
WALL_LATTICE_OFFSET_TOL_PX   = 1.5   # collinear pieces at one offset are one rung
WALL_LATTICE_PEN_TOL         = 0.05  # rungs must share a pen: a field is drawn in
                                     # one pen, while a wall face that happens to
                                     # run parallel nearby is penned as the walls
WALL_LATTICE_FIELD_COVER_FRAC = 0.5  # a rung OUTLASTS the field — keeps its face
WALL_LATTICE_OUTLAST_RATIO    = 3.0  # rights — when it is longer than the whole
                                     # stacked span (where MIN_RUNGS coexist), more
                                     # than OUTLAST_RATIO x the run's shortest rung,
                                     # and under COVER_FRAC of it lies in the span:
                                     # a wall face that a short stack coexists with
                                     # over a fraction of its length is not the
                                     # field's course (s17: four 891px lines of a
                                     # doubled frame at 12px pitch beside a fifth
                                     # parallel line). Hatch strokes staggered along
                                     # the axis coexist only marginally but are all
                                     # of one length; edge fragments of a course
                                     # are shorter than the span — both stay demoted

# Stair symbols: a flight is FURNITURE to the room stage — room/area takeoff
# (RICS GIA) runs the polygon to the enclosing walls straight through the
# stair — yet its ink is drawn in the wall pen (s03: 1.5px, the wall
# reference itself), so treads pass the lone-face gate and pair with each
# other or with the flight's side walls at wall pitch (measured on s03:
# two first-floor treads paired at th 14.8, the ground-floor stringer and
# the balustrade line at th 14.8 — and the hall stopped at the stair edge).
# Three recognizers, each anchored on drawing convention rather than pen:
#   tread run — >= WALL_STAIR_MIN_TREADS parallel same-pen faces at a
#     consistent tread pitch with aligned extents, plus a TRANSVERSE line
#     (section cut, direction arrow, nosing edge) that properly crosses a
#     tread's interior — the discriminator against a cavity party wall
#     drawn leaf/cavity/leaf at equal width, which nothing ever crosses;
#   stair arrow — a same-pen line chain ending on a filled arrowhead
#     (marker ring) with UP/DN text at hand; every face it crosses through
#     the interior is stair ink too (walls are never crossed by wall-pen
#     linework, and a leader crossing a wall has no UP/DN);
#   winder fan — >= 2 long unpaired diagonals sharing an endpoint (risers
#     fanning from the newel; a 45deg bay wall is paired at wall spacing).
# Members are demoted unconditionally; faces lying INSIDE the stair zone
# (bbox of the members) lose their rights too unless a wall face OUTSIDE
# the zone pairs with them at wall spacing — the flight's own side walls
# and the wall it abuts keep every face. Demoted faces re-enter the weak
# pipeline like lattice members: with no material between them they can
# never bound a room again.
WALL_STAIR_MIN_TREADS        = 3     # a flight; 2 parallel lines are a wall
WALL_STAIR_MIN_PITCH_PX      = 6.0   # under this the run is hatch (4.05px)
WALL_STAIR_PITCH_TOL_FRAC    = 0.35  # |pitch - median| / median; s13's cut
                                     # treads pitch 8.7-11.0
WALL_STAIR_END_TOL_PX        = 4.0   # a tread's extent lies within the
                                     # reference tread's extent +/- this
WALL_STAIR_MIN_LEN_FRAC      = 0.5   # ... and covers this much of it (treads
                                     # clipped by the section cut are shorter;
                                     # s03 1:50: 61.5px against 97px siblings —
                                     # a tread stopping mid-flight on a long
                                     # oblique same-pen line is itself the
                                     # cut evidence, even when it is the only
                                     # one the cut clips)
WALL_STAIR_TRANSVERSE_ANGLE  = 8.0   # degrees off the treads to count as a
                                     # transverse (cut/arrow/nosing) line; s17's
                                     # zigzag cuts run 12-15deg off the treads
WALL_STAIR_CROSS_MARGIN_PX   = 2.0   # proper crossing: the crossed face and
                                     # the crosser each extend past the
                                     # intersection by this on both sides
WALL_STAIR_TOUCH_PX          = 2.0   # endpoint contact / zone-inside tolerance
WALL_STAIR_BREAK_GAP_PX      = 24.0  # a break line's two collinear halves lie
                                     # this close end-to-end across the zigzag
                                     # jog (s03: 11.6px; the jog pieces are
                                     # under WALL_FACE_MIN_LEN_PX, so ~2 faces'
                                     # worth of gap is the ceiling)
WALL_STAIR_TEXT_NEAR_PX      = 12.0  # UP/DN text within this of the arrow
WALL_STAIR_TEXT_TOKENS       = frozenset({"UP", "DN", "DOWN"})
WALL_STAIR_FAN_MIN_ANGLE     = 10.0  # degrees between two winders of a fan
WALL_STAIR_MAX_ASPECT        = 10.0  # tread length / pitch: a 2.5m-wide public
                                     # flight at a 250mm going; measured stairs
                                     # 3.3-4 (s03, s13, s17), multi-line walls
                                     # 16-20 (s17)

WALL_JOINERY_BRIDGE_GAP_PX      = 80.0  # max open span between accepted white
                                        # rings of one joinery/hollow-wall run
                                        # (open wardrobe fronts between boxes).
                                        # Defined here (not beside its sibling
                                        # WALL_JOINERY_BRIDGE_SLACK_PX near
                                        # _bridge_white_runs below) so WallGates.at()
                                        # can reference it before that point in the
                                        # module.

# Tolerance for two segments to be considered on the same line.
COLLINEAR_ANGLE_TOL    = 3.0   # degrees
COLLINEAR_OFFSET_TOL   = 4.0   # px perpendicular distance between lines


@dataclass(frozen=True)
class WallGates:
    """World-space wall gates, pre-multiplied by the detection factor.

    Fields keep the exact names of the module constants they scale, so a
    use site reads `gates.WALL_MAX_THICKNESS_PX` where it read the module
    constant. Paper-space constants (pen widths, tick sizes, drafting
    tolerances) deliberately have NO field here — they never scale.
    At factor 1.0 every field equals its constant exactly.
    """
    factor: float
    WALL_FACE_MIN_LEN_PX: float
    WALL_MIN_THICKNESS_PX: float
    WALL_MAX_THICKNESS_PX: float
    WALL_THICK_MATERIAL_MAX_PX: float
    WALL_THROUGH_HATCH_MAX_PX: float
    WALL_PAIR_MIN_OVERLAP_PX: float
    WALL_FILL_CLASS_MIN_INK_PX: float
    WALL_FILL_BLOCK_MAX_SIDE_PX: float
    WALL_WEAK_MIN_RUN_PX: float
    WALL_JOINERY_BRIDGE_GAP_PX: float
    WALL_HATCH_MAX_LEN_PX: float
    WALL_WEAK_MATERIAL_PER_100PX: float
    COLLINEAR_OFFSET_TOL: float

    @classmethod
    def at(cls, factor: float) -> "WallGates":
        assert factor > 0, "scale factor must be positive"
        return cls(
            factor=factor,
            WALL_FACE_MIN_LEN_PX=WALL_FACE_MIN_LEN_PX * factor,
            # Floor: below ~1px the pair search chases pen-width noise.
            WALL_MIN_THICKNESS_PX=max(1.0, WALL_MIN_THICKNESS_PX * factor),
            WALL_MAX_THICKNESS_PX=WALL_MAX_THICKNESS_PX * factor,
            WALL_THICK_MATERIAL_MAX_PX=WALL_THICK_MATERIAL_MAX_PX * factor,
            WALL_THROUGH_HATCH_MAX_PX=WALL_THROUGH_HATCH_MAX_PX * factor,
            WALL_PAIR_MIN_OVERLAP_PX=WALL_PAIR_MIN_OVERLAP_PX * factor,
            WALL_FILL_CLASS_MIN_INK_PX=WALL_FILL_CLASS_MIN_INK_PX * factor,
            WALL_FILL_BLOCK_MAX_SIDE_PX=WALL_FILL_BLOCK_MAX_SIDE_PX * factor,
            WALL_WEAK_MIN_RUN_PX=WALL_WEAK_MIN_RUN_PX * factor,
            WALL_JOINERY_BRIDGE_GAP_PX=WALL_JOINERY_BRIDGE_GAP_PX * factor,
            WALL_HATCH_MAX_LEN_PX=WALL_HATCH_MAX_LEN_PX * factor,
            # Density (marks per 100 PAPER-px of band length), not a length:
            # world-spaced marks pack 2x tighter per paper-px at f=0.5, so
            # the minimum must RISE to keep noise out — divide, not
            # multiply (see docs/scale-normalization-findings.md §4b).
            WALL_WEAK_MATERIAL_PER_100PX=WALL_WEAK_MATERIAL_PER_100PX / factor,
            # Not WALL_-prefixed, so it was missed by the original corpus
            # census and the frozen §4 table — found via TDD (see
            # docs/scale-normalization-findings.md §4 row). It gates the
            # same "is this the same drawn line" judgment as
            # WALL_MIN_THICKNESS_PX: left unscaled, a shrunk-world wall's
            # own face spacing can fall at/under it and the two faces fuse
            # into one line, which then can never pair.
            COLLINEAR_OFFSET_TOL=COLLINEAR_OFFSET_TOL * factor,
        )

    def __post_init__(self):
        # Programming-error asserts (never factor-dependent in [0.25, 4]).
        assert self.WALL_MIN_THICKNESS_PX < self.WALL_MAX_THICKNESS_PX
        assert self.WALL_MAX_THICKNESS_PX < self.WALL_THICK_MATERIAL_MAX_PX
        assert self.WALL_THICK_MATERIAL_MAX_PX < self.WALL_THROUGH_HATCH_MAX_PX


WALL_GATES_UNSCALED = WallGates.at(1.0)


def _pen_key(color) -> tuple | None:
    """Quantized stroke color — the pen identity of a drawn line."""
    if color is None:
        return None
    return tuple(round(c, 2) for c in color)


def _is_light_pen(pen: tuple | None) -> bool:
    """Faint (light-grey/pastel) ink: every channel at/above the light floor."""
    return pen is not None and min(pen) >= WALL_LIGHT_PEN_MIN_CHANNEL


def _pens_compatible(a: tuple | None, b: tuple | None) -> bool:
    """A wall's two faces are drawn by one pen; colorless (fill-outline)
    geometry stays wildcard so monochrome and Vectorworks-style drawings
    keep the legacy behavior."""
    return a is None or b is None or a == b


def _is_diagonal_hatch_angle(angle: float) -> bool:
    return 25.0 <= angle <= 65.0 or 115.0 <= angle <= 155.0


def _is_background_fill(fill) -> bool:
    """True for fills indistinguishable from the page background (white).

    CAD exports mask the drawing under text tags and counter tops with
    unstroked white polygons; their outlines are erasures, not material.
    """
    return fill is not None and len(fill) > 0 and min(fill) >= WALL_BACKGROUND_FILL_MIN


def _fill_key(fill) -> tuple:
    return tuple(round(c, 3) for c in fill)


def _equivalent_sides(poly) -> tuple[float, float]:
    """(short, long) of the rectangle with this polygon's area and perimeter.

    The two roots of x^2 - (P/2)x + A. Unlike a rotated envelope this keeps
    L- and U-shaped wall runs band-like: their thickness is what survives.
    """
    half_p = poly.exterior.length / 2.0
    disc = (half_p / 2.0) ** 2 - poly.area
    root = math.sqrt(max(disc, 0.0))
    return half_p / 2.0 - root, half_p / 2.0 + root


@dataclass
class _FillRing:
    """A closed same-fill polygon reconstructed from exploded `l` items."""
    key: tuple                          # rounded fill color
    poly: Polygon
    short: float                        # equivalent-rectangle sides: the two
    long: float                         # roots of x^2 - (P/2)x + A
    indices: set[int]                   # contributing path indices

    def is_band(self, gates: WallGates) -> bool:
        return (
            self.short <= gates.WALL_MAX_THICKNESS_PX
            and self.long / self.short >= WALL_BAND_MIN_ASPECT
        )

    def is_marker(self) -> bool:
        """Annotation arrowhead: a tiny filled triangle or concave dart.

        Walls are rectilinear — bands, posts, L/U-runs — so a small
        3-vertex ring (or concave 4-vertex kite) sharing the wall pen is a
        leader/dimension tip, not material. Convex quads of the same size
        (jamb stubs, corner posts) stay.
        """
        x0, y0, x1, y1 = self.poly.bounds
        if max(x1 - x0, y1 - y0) > WALL_MARKER_MAX_SIDE_PX:
            return False
        n_vertices = len(self.poly.exterior.coords) - 1
        if n_vertices == 3:
            return True
        return (
            n_vertices == 4
            and self.poly.area < 0.99 * self.poly.convex_hull.area
        )


@dataclass
class _StrokedRing:
    """A small closed STROKED (fill-less) outline in one pen — a jamb-nib /
    door-stop block candidate. Collected here, accepted in rooms.py where
    wall material and opening geometry are both known."""
    poly: Polygon
    stroke_width: float                 # min across members
    pen: tuple | None
    indices: set[int]


def _collect_stroked_rings(
    paths: list[PathPrimitive],
    excluded: frozenset[int] | set[int],
    *, gates: WallGates,
) -> list[_StrokedRing]:
    """Closed fill-less outlines no larger than one wall thickness a side.

    A doorway leaves a JAMB NIB beside each hinge — the last piece of wall,
    often drawn with its door-stop rebate as a closed 4-8 segment outline
    in the wall pen (s03: 12x5.3px and 12x9px L-shapes, paths 15805-15816,
    every edge under WALL_FACE_MIN_LEN_PX), or as a lone stroked `re`/`qu`.
    Such a block has no faces and no fill, so the room outline bulged over
    it to the door plug. The same signature draws small fixture symbols
    (sockets, tiles, cistern boxes), so collection is shape-only; rooms.py
    accepts a ring as wall only when it is penned like the walls AND
    touches both drawn wall material and an opening's bbox — a jamb block
    sits between the band end and the doorway, a fixture box does not.
    """
    cap = gates.WALL_MAX_THICKNESS_PX
    rings: list[_StrokedRing] = []

    def account(pts, idxs: set[int], width: float, pen) -> None:
        if len(pts) < 3 or idxs & set(excluded):
            return
        poly = Polygon(pts)
        if not poly.is_valid or poly.area < 4.0:
            return
        x0, y0, x1, y1 = poly.bounds
        if max(x1 - x0, y1 - y0) > cap:
            return
        rings.append(_StrokedRing(poly=poly, stroke_width=width, pen=pen, indices=idxs))

    chain_pen = None
    chain_pts: list[tuple[float, float]] = []
    chain_idx: set[int] = set()
    chain_w = 0.0

    def flush() -> None:
        nonlocal chain_pen, chain_pts, chain_idx, chain_w
        if (
            chain_pts and 4 <= len(chain_pts) - 1 <= 8
            and _distance(chain_pts[0], chain_pts[-1]) <= 2.0
        ):
            account(chain_pts[:-1], set(chain_idx), chain_w, chain_pen)
        chain_pen, chain_pts, chain_idx, chain_w = None, [], set(), 0.0

    for p in paths:
        stroked = p.fill is None and p.stroke_width > 0 and len(p.points) >= 2
        if stroked and p.item_type == "l":
            pen = _pen_key(p.color)
            a, b = p.points[0], p.points[-1]
            if chain_pts and chain_pen == pen and _distance(chain_pts[-1], a) <= 1.0:
                chain_pts.append(b)
                chain_idx.add(p.path_index)
                chain_w = min(chain_w, p.stroke_width)
                continue
            flush()
            chain_pen, chain_pts = pen, [a, b]
            chain_idx, chain_w = {p.path_index}, p.stroke_width
            continue
        flush()
        if stroked and p.item_type in ("re", "qu") and len(p.points) == 4:
            pts = p.points
            if p.item_type == "qu":
                pts = [pts[0], pts[1], pts[3], pts[2]]
            account(list(pts), {p.path_index}, p.stroke_width, _pen_key(p.color))
    flush()
    return rings


def _collect_fill_rings(paths: list[PathPrimitive]) -> list[_FillRing]:
    """Chain consecutive same-fill `l` items (plus filled re/qu) into rings.

    extract_paths explodes each drawing in order, so a filled polygon's edges
    are consecutive primitives whose endpoints chain; any break in fill color
    or continuity closes the current chain. Background (white) rings are
    collected too — their shape decides mask vs hollow wall later.

    A chain that returns EXACTLY to its own start vertex and then continues
    is two rings drawn back to back, not one: an exporter that triangulates
    a fill as a fan emits triangle 2 from triangle 1's start vertex (or the
    next cell's triangle from the vertex this one closed on), so the six
    edges chain into one self-touching polygon shapely rejects, and both
    triangles — and the seam between them — used to be lost (s20's grey
    wall bands, s04/s08's red demolition slivers, s18's black bands; see
    WALL_FILL_CHAIN_REVISIT_TOL_PX). The ring closes at the return and the
    next chain starts there.
    """
    rings: list[_FillRing] = []

    def account(key: tuple, ring_pts, ring_indices: set[int]) -> None:
        if len(ring_pts) < 3:
            return
        poly = Polygon(ring_pts)
        if not poly.is_valid or poly.area < 4.0:
            return
        short, long_ = _equivalent_sides(poly)
        if long_ < 1e-6 or short < 1e-6:
            return
        rings.append(_FillRing(
            key=key, poly=poly, short=short, long=long_, indices=ring_indices,
        ))

    chain_key: tuple | None = None
    chain_pts: list[tuple[float, float]] = []
    chain_idx: set[int] = set()

    def flush() -> None:
        nonlocal chain_key, chain_pts, chain_idx
        if chain_key is not None and len(chain_pts) >= 4 and _distance(
            chain_pts[0], chain_pts[-1]
        ) <= 2.0:
            account(chain_key, chain_pts[:-1], chain_idx)
        chain_key, chain_pts, chain_idx = None, [], set()

    for p in paths:
        fillable = p.fill is not None and len(p.points) >= 2
        if fillable and p.item_type == "l":
            key = _fill_key(p.fill)
            a, b = p.points[0], p.points[-1]
            if chain_key == key and chain_pts and _distance(chain_pts[-1], a) <= 1.0:
                chain_pts.append(b)
                chain_idx.add(p.path_index)
                if (
                    len(chain_pts) >= 4
                    and _distance(chain_pts[0], b) <= WALL_FILL_CHAIN_REVISIT_TOL_PX
                ):
                    # Back on the start vertex: this ring is closed, the
                    # next one (if any) opens here with the same fill.
                    account(key, chain_pts[:-1], chain_idx)
                    chain_pts, chain_idx = [b], set()
                continue
            flush()
            chain_key, chain_pts = key, [a, b]
            chain_idx = {p.path_index}
            continue
        flush()
        if fillable and p.item_type in ("re", "qu") and len(p.points) == 4:
            pts = p.points
            if p.item_type == "qu":
                pts = [pts[0], pts[1], pts[3], pts[2]]
            account(_fill_key(p.fill), list(pts), {p.path_index})
    flush()

    return rings


def _rate_fill_classes(
    rings: list[_FillRing], *, gates: WallGates = WALL_GATES_UNSCALED
) -> dict[tuple, bool]:
    """Classify each fill color as wall material (True) or furniture (False).

    Vectorworks-style exports draw both walls and furniture as unstroked
    filled polygons that explode into `l` items, so the fill color is the only
    thing separating a wall band from a cabinet block. Rather than hard-coding
    colors, rate each fill class by the shape of its ink: measure whether the
    class's run length lives in thin elongated bands (wall thickness, band
    aspect) or in compact blocks. Classes below WALL_FILL_CLASS_MIN_INK_PX of
    ring length stay unrated and default to wall material (the permissive
    legacy rule), so drawings whose walls are stroked lose nothing.
    """
    stats: dict[tuple, list[float]] = {}  # key -> [band_len, block_len]
    for r in rings:
        if _is_background_fill(r.key):
            continue  # white rings are judged per-ring (_white_wall_rings)
        if r.is_marker():
            continue  # arrowhead glyphs rate as bands and would skew the class
        entry = stats.setdefault(r.key, [0.0, 0.0])
        entry[0 if r.is_band(gates) else 1] += r.long

    return {
        key: band >= block
        for key, (band, block) in stats.items()
        if band + block >= gates.WALL_FILL_CLASS_MIN_INK_PX
    }


WALL_WHITE_TOUCH_TOL_PX     = 4.0   # white ring-to-wall contact distance
WALL_WHITE_SPAN_MIN_FRAC    = 0.6   # contact extent must cover this much of a
                                    # group's extent: walls and built-in runs
                                    # bridge between masses, cabinet fronts
                                    # touch at most one end
WALL_WHITE_TEXT_COVER_FRAC  = 0.3   # contained text covering this much of a
                                    # ring marks a text mask; a small label ON
                                    # a wall band does not disqualify the band


def _white_wall_candidates(
    rings: list[_FillRing], text_spans: list[TextSpan],
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_FillRing]:
    """Background-colored rings that could be hollow walls or built-in runs.

    White fills are ambiguous: CAD exports use them to mask the drawing under
    text tags and counter tops, to draw cabinet fronts, AND to draw hollow
    (unhatched) walls or chained joinery boxes (wardrobe runs that bound a
    room like a partition). Shape and content prune the masks: candidates
    stay wall-thickness-to-post sized, and a ring mostly covered by the text
    written inside it is the text's mask, not material. The caller settles
    walls vs furniture by connectivity (_accept_white_walls).
    """
    candidates = [
        r for r in rings
        if _is_background_fill(r.key)
        and r.short <= gates.WALL_FILL_BLOCK_MAX_SIDE_PX
    ]
    if not candidates:
        return []
    spans = [
        (
            ((t.bbox[0] + t.bbox[2]) / 2.0, (t.bbox[1] + t.bbox[3]) / 2.0),
            max(0.0, (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1])),
        )
        for t in text_spans
    ]
    walls = []
    for r in candidates:
        x0, y0, x1, y1 = r.poly.bounds
        text_area = sum(
            area for (cx, cy), area in spans
            if x0 <= cx <= x1 and y0 <= cy <= y1
            and r.poly.contains(Point(cx, cy))
        )
        if text_area >= WALL_WHITE_TEXT_COVER_FRAC * r.poly.area:
            continue
        walls.append(r)
    return walls


def _accept_white_walls(candidates: list[_FillRing], material) -> list[_FillRing]:
    """Keep white rings attached (directly or chained) to wall material.

    Hollow wall pieces and joinery runs (wardrobe boxes bounding a room)
    touch the wall network — or touch each other in chains that reach it —
    while freestanding white furniture floats in room interiors. Acceptance
    grows outward from the anchored rings so mid-chain pieces qualify
    through their neighbours.
    """
    if material is None or not candidates:
        return []
    accepted: list[_FillRing] = []
    buffered = {
        id(r): r.poly.buffer(WALL_WHITE_TOUCH_TOL_PX) for r in candidates
    }
    pool = list(candidates)
    changed = True
    while changed and pool:
        changed = False
        rest = []
        for r in pool:
            if buffered[id(r)].intersects(material):
                accepted.append(r)
                material = material.union(r.poly)
                changed = True
            else:
                rest.append(r)
        pool = rest
    return accepted


# WALL_JOINERY_BRIDGE_GAP_PX now lives in the top constants block (WallGates
# needs it before this point in the module) — see there for the field.
WALL_JOINERY_BRIDGE_SLACK_PX    = 8.0   # bridge hull may be this much thicker
                                        # than its fattest end ring — thicker
                                        # hulls mean the rings are not aligned


def _bridge_white_runs(accepted: list[_FillRing], *, gates: WallGates) -> list:
    """Band-shaped convex hulls closing the gaps in accepted white-ring runs.

    gates is keyword-only and REQUIRED (no WALL_GATES_UNSCALED default):
    detect_rooms (detection/rooms.py) is this function's only production
    call site, called from a different module than the one that owns
    WALL_JOINERY_BRIDGE_GAP_PX — a default here let that call site silently
    bridge at the unscaled 80px gap on every non-1:50 sheet, invisible to a
    bare-name grep for the constant (see docs/scale-normalization-findings.md
    §4b). A missing gates= at a cross-module call site must now be a
    TypeError, not silent unscaled behavior.

    A wardrobe or joinery run bounds a room like a partition, but is drawn as
    spaced boxes (dividers) with open fronts between them. Bridge nearby
    accepted rings when their joint hull stays band-like — aligned boxes of
    one run produce a thin hull, unrelated boxes across a room corner
    produce a fat one and are skipped.

    A bridge closes an OPEN SPAN, so rings that are already connected —
    touching each other (hollow-wall cavity segments chain contiguously
    around wall corners) or joined by a shorter bridge — are never bridged
    again: between two SMALL rings sitting on perpendicular runs of one
    cavity chain, the redundant hull is thin enough to pass the band test
    and chords diagonally across the room corner, notching the room outline
    around whatever annotation (leader arrows) happens to sit there. Pairs
    are considered shortest gap first, so the span that gets closed is the
    physically nearest one.
    """
    n = len(accepted)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            gap = accepted[i].poly.distance(accepted[j].poly)
            if gap <= WALL_WHITE_TOUCH_TOL_PX:
                parent[find(i)] = find(j)
            elif gap <= gates.WALL_JOINERY_BRIDGE_GAP_PX:
                pairs.append((gap, i, j))

    bridges = []
    for gap, i, j in sorted(pairs):
        if find(i) == find(j):
            continue
        a, b = accepted[i], accepted[j]
        hull = unary_union([a.poly, b.poly]).convex_hull
        short, _long = _equivalent_sides(hull)
        if short <= max(a.short, b.short) + WALL_JOINERY_BRIDGE_SLACK_PX:
            bridges.append(hull)
            parent[find(i)] = find(j)
    return bridges


def _wall_material_evidence(paths: list[PathPrimitive], bbox: BBox) -> dict:
    """Measure whether a bbox contains wall-like material fill.

    Many architectural PDFs do not use a PDF fill color for walls. Instead
    they draw diagonal hatch strokes inside the wall band. This helper treats
    dense short diagonal strokes as wall material evidence, while also tracking
    true filled rectangles/quads when the PDF exposes them.
    """
    expanded = _bbox_expanded(bbox, 2.0)
    hatch_count = 0
    short_line_count = 0
    filled_overlap = False

    for path in paths:
        if path.item_type == "l" and len(path.points) >= 2:
            p1, p2 = path.points[0], path.points[-1]
            midpoint = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            if not _point_in_bbox(midpoint, expanded):
                continue
            length = _line_length(p1, p2)
            if not (2.0 <= length <= 45.0):
                continue
            short_line_count += 1
            if _is_diagonal_hatch_angle(_line_angle_deg(p1, p2)):
                hatch_count += 1
        elif path.fill is not None and path.item_type in ("re", "qu"):
            if _bboxes_overlap(path.bbox, expanded):
                filled_overlap = True

    hatch_ratio = hatch_count / short_line_count if short_line_count else 0.0
    return {
        "hatch_count": hatch_count,
        "short_line_count": short_line_count,
        "hatch_ratio": round(hatch_ratio, 3),
        "filled_overlap": filled_overlap,
        "wall_material": bool(
            filled_overlap
            or (
                hatch_count >= WALL_HATCH_MIN_SEGMENTS
                and hatch_ratio >= WALL_HATCH_MIN_RATIO
            )
        ),
    }


def _stroke_percentile_rank(stroke_width: float, all_widths: list[float]) -> float:
    """Return the fraction of page strokes thinner than this one (0–1).

    Using relative rank rather than an absolute threshold handles PDFs where
    all strokes are 1.5 px (the sample case): a wall at the 90th percentile
    is thicker than annotation lines even if the absolute value is modest.
    Returns 0.5 when there is no width variation to avoid false signal.
    """
    if not all_widths or max(all_widths) - min(all_widths) < 0.1:
        return 0.5
    below = sum(1 for w in all_widths if w < stroke_width)
    return below / len(all_widths)


# ---------------------------------------------------------------------------
# Wall network data model
# ---------------------------------------------------------------------------
@dataclass
class WallSegment:
    """One wall centerline segment (pixel space, y-down)."""
    p1: tuple[float, float]
    p2: tuple[float, float]
    thickness_px: float                 # face spacing / filled-band short side
    source: str                         # "face_pair" | "filled_band"
    layer: str | None
    layer_hint: bool
    face_path_indices: list[int]
    # At least one contributing face was a stroked line (vs pure fill-outline
    # geometry, which is also how Vectorworks draws fixtures/furniture).
    stroked: bool = False


@dataclass
class WallFace:
    """One merged wall-face run with the evidence its members carried."""
    p1: tuple[float, float]
    p2: tuple[float, float]
    stroked: bool
    stroke_width: float                 # max across merged members (0 if unstroked)
    wall_fill: bool                     # outline of a wall-rated fill class
    layer_hint: bool
    indices: frozenset[int]             # contributing path indices
    material_backed: bool = False       # same-pen hatch hugs one flank of the
                                        # run — a hatched band's lone drawn face
                                        # (its partner may be a stub or dashed)
    pen: tuple | None = None            # quantized stroke color (None for fill
                                        # outlines/bands) — rooms' lone-barrier
                                        # gate checks it against the wall pens
    # Weak (hairline/light-pen) faces only: sub-runs of the face, as
    # (t0, t1) px along p1->p2, beside which drawn wall material lies within
    # one band thickness on either flank (_face_material_spans). Rooms clip
    # a partially paired weak face's barrier to its own bands plus these —
    # the plain remainder of a merged hairline run is joinery, not wall.
    backed_spans: tuple[tuple[float, float], ...] = ()


@dataclass
class WallNetwork:
    """Connected wall-centerline network (internal-only, never serialized)."""
    segments: list[WallSegment]
    merged: object | None = None        # shapely geometry: snapped + noded centerlines
    # Merged wall FACE lines (pre-pairing). Face merging bridges only tiny
    # (6px) gaps, so real openings stay visible here even after centerline
    # merging has stitched a window's glazing run into its wall run — this is
    # what "does a wall run unbroken through this bbox" must be asked of.
    faces: list[WallFace] = field(default_factory=list)
    # Closed polygons of wall-rated fill classes (shapely, band/post-sized):
    # true wall area, used by room detection as barrier solids.
    fill_polygons: list = field(default_factory=list)
    # Hollow-wall candidates (white band _FillRings, text-pruned); accepted
    # against opening-aware wall material by rooms.py via _accept_white_walls.
    white_bands: list = field(default_factory=list)
    # Small closed stroked outlines (jamb-nib / door-stop block candidates):
    # rooms.py accepts the ones penned like walls that touch both wall
    # material and an opening bbox (_accept_jamb_rings).
    stroked_rings: list = field(default_factory=list)

    def is_empty(self) -> bool:
        return len(self.segments) < WALL_NETWORK_MIN_SEGMENTS

    def paired_face_indices(self) -> set[int]:
        """Path indices of every face that contributed to a centerline."""
        used: set[int] = set()
        for seg in self.segments:
            used.update(seg.face_path_indices)
        return used

    def wall_stroke_reference(self) -> float:
        """Length-weighted median stroke width of the paired stroked faces.

        Anchors relative pen-weight tests to the pens that actually drew the
        walls, instead of an absolute threshold that breaks across drawings.
        0.0 when the network carries no stroked paired faces (all-fill pages).
        """
        used = self.paired_face_indices()
        entries = sorted(
            (f.stroke_width, _line_length(f.p1, f.p2))
            for f in self.faces
            if f.stroked and f.stroke_width > 0 and f.indices & used
        )
        total = sum(length for _, length in entries)
        if total <= 0:
            return 0.0
        acc = 0.0
        for width, length in entries:
            acc += length
            if acc >= total / 2.0:
                return width
        return entries[-1][0]

    def near_bbox(self, bbox: BBox, expand_px: float, stroked_only: bool = False) -> bool:
        """True when any centerline corridor (dilated by thickness/2 + expand) hits bbox.

        stroked_only restricts the test to segments with stroked-face
        corroboration — pure fill-outline geometry also describes fixtures.
        """
        if self.is_empty():
            return False
        for seg in self.segments:
            if stroked_only and not seg.stroked:
                continue
            reach = seg.thickness_px / 2.0 + expand_px
            if _segment_bbox_distance(seg.p1, seg.p2, bbox) <= reach:
                return True
        return False

    def nearest_segment(
        self, pt: tuple[float, float]
    ) -> tuple[WallSegment, float] | None:
        if not self.segments:
            return None
        best = min(
            self.segments,
            key=lambda s: _point_to_segment_distance(pt, s.p1, s.p2),
        )
        return best, _point_to_segment_distance(pt, best.p1, best.p2)

    def collinear_overlap(self, bbox: BBox, angle_tol_deg: float) -> float:
        """Max fraction of the bbox long axis covered by one near-collinear centerline.

        Used to recognize window candidates whose "glazing" lines are actually
        the two faces of a continuous wall. Only meaningful for axis-aligned
        bbox orientations (diagonal windows have squarish bboxes).
        """
        if self.is_empty():
            return 0.0
        x0, y0, x1, y1 = bbox
        w, h = x1 - x0, y1 - y0
        if max(w, h) < 1e-6:
            return 0.0
        horiz = w >= h
        axis_angle = 0.0 if horiz else 90.0
        lo, hi = (x0, x1) if horiz else (y0, y1)
        span = hi - lo
        best = 0.0
        for seg in self.segments:
            ang = _line_angle_deg(seg.p1, seg.p2)
            if _angle_diff_mod180(ang, axis_angle) > angle_tol_deg:
                continue
            mid = ((seg.p1[0] + seg.p2[0]) / 2, (seg.p1[1] + seg.p2[1]) / 2)
            if horiz:
                if not (y0 - seg.thickness_px <= mid[1] <= y1 + seg.thickness_px):
                    continue
                s_lo, s_hi = sorted((seg.p1[0], seg.p2[0]))
            else:
                if not (x0 - seg.thickness_px <= mid[0] <= x1 + seg.thickness_px):
                    continue
                s_lo, s_hi = sorted((seg.p1[1], seg.p2[1]))
            overlap = min(hi, s_hi) - max(lo, s_lo)
            if overlap > 0:
                best = max(best, overlap / span)
        return best


def _segments_properly_intersect(
    a1: tuple[float, float], a2: tuple[float, float],
    b1: tuple[float, float], b2: tuple[float, float],
) -> bool:
    """True when the two segments cross at an interior point.

    _segments_min_distance only measures endpoint-to-segment distances, so it
    misses proper crossings; touching/collinear cases yield ~0 there anyway.
    """
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1, o2 = orient(a1, a2, b1), orient(a1, a2, b2)
    o3, o4 = orient(b1, b2, a1), orient(b1, b2, a2)
    return o1 * o2 < 0 and o3 * o4 < 0


def _segment_bbox_distance(
    p1: tuple[float, float], p2: tuple[float, float], bbox: BBox
) -> float:
    """Min distance between a segment and an axis-aligned bbox (0 if touching)."""
    if _point_in_bbox(p1, bbox) or _point_in_bbox(p2, bbox):
        return 0.0
    x0, y0, x1, y1 = bbox
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    if any(_segments_properly_intersect(p1, p2, a, b) for a, b in edges):
        return 0.0
    return min(_segments_min_distance(p1, p2, a, b) for a, b in edges)


# ---------------------------------------------------------------------------
# Network construction
# ---------------------------------------------------------------------------
@dataclass
class _Seg:
    """Working segment during network construction."""
    p1: tuple[float, float]
    p2: tuple[float, float]
    layer: str | None = None
    layer_hint: bool = False
    indices: set[int] = field(default_factory=set)
    thickness: float = 0.0
    source: str = "face"
    stroked: bool = False
    stroke_width: float = 0.0           # max stroke width across merged members
    wall_fill: bool = False             # from a wall-rated fill class (band/ring)
    weak: bool = False                  # sub-threshold pen; only material-backed
                                        # pairs survive (never a face on its own)
    thick: bool = False                 # pair spacing beyond WALL_MAX_THICKNESS_PX
                                        # (thickened pier tier); only material-
                                        # backed pairs survive
    through: bool = False               # thick pair spaced beyond
                                        # WALL_THICK_MATERIAL_MAX_PX too; survives
                                        # only on through-hatch
    pen: tuple | None = None            # quantized stroke color; None = wildcard
                                        # (fill outlines, filled bands, centerlines)


def _is_dashed(dashes: str) -> bool:
    """True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"."""
    if not dashes:
        return False
    inner = dashes.split("]")[0].strip("[ ").strip()
    return bool(inner)


def _wall_layer_hint(layer: str | None) -> bool:
    return _layer_hint_from_layer(layer, WALL_LAYER_KEYWORDS)


def _fill_seam_indices(
    rings: list[_FillRing], paths: list[PathPrimitive]
) -> set[int]:
    """Path indices of fill-ring seams — see _fill_seams."""
    return _fill_seams(rings, paths)[0]


def _fill_ring_components(
    n_rings: int, adjacency: list[tuple[int, int]], members: set[int]
) -> list[list[int]]:
    """Group ring ids (restricted to `members`) connected by shared seams.

    Exporters triangulate fills, so a wall band is two (or more) rings that
    share their joint edges; each dilated on its own, the acute
    triangulation vertices bevel or spike (ROOM_RING_MITRE_LIMIT caps the
    spike but leaves a <= 2px bevel). Unioning a seam-connected group
    restores the polygon the exporter split — a rectangle band dilates
    like a rectangle. Only SEAM-sharing rings group (the same-fill,
    fill-on-both-sides test); merely touching same-fill rings do not, so
    an abutting fixture block never merges into a wall band.
    """
    parent = list(range(n_rings))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in adjacency:
        if a in members and b in members:
            parent[find(a)] = find(b)
    groups: dict[int, list[int]] = {}
    for i in sorted(members):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _fill_seams(
    rings: list[_FillRing], paths: list[PathPrimitive]
) -> tuple[set[int], list[tuple[int, int]]]:
    """(seam path indices, ring-id pairs sharing a seam).

    Path indices of fill-ring edges that are SEAMS, not outline.

    A filled area's visible boundary is the outline of the whole fill.
    Exporters triangulate fills, and PyMuPDF chains each triangle into its
    own ring, so a wall band arrives as two triangles that both carry the
    shared diagonal — an edge drawn once per piece, running through the
    middle of the band. Adjacent same-fill pieces (a band split into strips)
    share their joint edges the same way. Such an edge has fill on BOTH
    sides, so no pen ever shows it; a wall face has fill on exactly one
    side. A triangle's diagonal across a thin band lies within
    WALL_PARALLEL_ANGLE_TOL of the band's own faces (s03: 17.7px over
    336.7px, 3.0 deg) and pairs with one of them into a slanted centerline
    whose solid stands 18px off the band at one end — the bedroom's right
    edge came out 17px short at the top and flush at the bottom (measured
    on s03 room_0000, 818 vs 835; rooms 0003/0004/0005/0006 skewed the
    same way, 5–14px). Only the coincident (same fill, same endpoints
    within 1px) edges of DISTINCT rings are candidates, then the two-sided
    fill test decides: an overdrawn ring (the same rectangle drawn twice)
    duplicates every edge yet keeps its outline, because those edges have
    fill on one side only.

    The probe stays INSIDE the fill it tests: it samples at the smaller of
    WALL_FILL_SEAM_PROBE_PX and WALL_FILL_SEAM_PROBE_FRAC of the thinnest
    sharing ring's `short`. A fixed 1px probe left every ring thinner than
    2px, so a sub-2px sliver's triangles (short = the triangle's inradius,
    half the sliver) never seam-united and each dilated alone — the acute
    tip's capped mitre bit a 2x4px notch out of s03's corridor room_0007.
    A duplicate still fails at any distance: its empty side stays empty.
    """
    path_by_index = {p.path_index: p for p in paths}
    edges: dict[tuple, list[tuple[int, int]]] = {}
    for ri, r in enumerate(rings):
        for pi in r.indices:
            p = path_by_index.get(pi)
            if p is None or p.item_type != "l" or len(p.points) < 2:
                continue
            a, b = p.points[0], p.points[-1]
            key = (r.key, tuple(sorted((
                (round(a[0]), round(a[1])), (round(b[0]), round(b[1]))
            ))))
            edges.setdefault(key, []).append((ri, pi))
    seams: set[int] = set()
    adjacency: list[tuple[int, int]] = []
    for members in edges.values():
        ring_ids = {ri for ri, _ in members}
        if len(ring_ids) < 2:
            continue
        p = path_by_index[members[0][1]]
        (ax, ay), (bx, by) = p.points[0], p.points[-1]
        length = _line_length((ax, ay), (bx, by))
        if length < 1e-6:
            continue
        nx, ny = -(by - ay) / length, (bx - ax) / length
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        union = unary_union([rings[ri].poly for ri in ring_ids])
        probe = min(
            WALL_FILL_SEAM_PROBE_PX,
            WALL_FILL_SEAM_PROBE_FRAC * min(rings[ri].short for ri in ring_ids),
        )
        if all(
            union.contains(Point(mx + s * nx, my + s * ny))
            for s in (probe, -probe)
        ):
            seams.update(pi for _, pi in members)
            ids = sorted(ring_ids)
            adjacency.extend((ids[0], other) for other in ids[1:])
    return seams, adjacency


def _vector_text_indices(paths: list[PathPrimitive]) -> set[int]:
    """Path indices of stick-font glyph strokes: annotation, never faces.

    A glyph is a connected component of touching same-pen stroked `l`
    items no larger than WALL_TEXT_GLYPH_MAX_PX a side that touches NO
    larger linework (wall ink is connected: a nib meets its band, a hatch
    stroke its faces, a tread its stringer). A text line is a row of >=
    WALL_TEXT_MIN_GLYPHS glyphs sharing a cap or base line (either axis —
    s20 is rotated) with gaps under one glyph height, of which >=
    WALL_TEXT_MIN_MULTI_STROKE are multi-stroke and whose strokes span >=
    WALL_TEXT_ANGLE_DIVERSITY. A lone hatched pier box is one component,
    never a row; a loose row of parallel hatch strokes has neither multi-
    stroke members nor angle diversity.
    """
    from shapely.strtree import STRtree
    from shapely.geometry import box as _box

    gmax, touch = WALL_TEXT_GLYPH_MAX_PX, WALL_TEXT_TOUCH_PX
    big = []
    pieces: list[tuple] = []          # (index, a, b, length, pen)
    for p in paths:
        b = p.bbox
        if max(b[2] - b[0], b[3] - b[1]) > gmax:
            if p.item_type == "l" and len(p.points) >= 2:
                big.append(LineString([p.points[0], p.points[-1]]))
            else:
                big.append(_box(*b).exterior)
            continue
        if (
            p.item_type != "l" or len(p.points) < 2 or p.stroke_width <= 0
            or p.fill is not None or p.color is None
        ):
            continue
        a, c = p.points[0], p.points[-1]
        length = _line_length(a, c)
        if length <= 0:
            continue
        pieces.append((p.path_index, a, c, length, _pen_key(p.color)))
    if len(pieces) < WALL_TEXT_MIN_GLYPHS:
        return set()

    parent = list(range(len(pieces)))

    def _find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid: dict[tuple[int, int], list[int]] = {}
    for i, (_, a, c, _, _) in enumerate(pieces):
        for gx in range(int(min(a[0], c[0]) // gmax), int(max(a[0], c[0]) // gmax) + 1):
            for gy in range(int(min(a[1], c[1]) // gmax), int(max(a[1], c[1]) // gmax) + 1):
                grid.setdefault((gx, gy), []).append(i)
    for members in grid.values():
        for ii in range(len(members)):
            i = members[ii]
            _, ai, bi, _, pi = pieces[i]
            for jj in range(ii + 1, len(members)):
                j = members[jj]
                _, aj, bj, _, pj = pieces[j]
                if pi != pj or _find(i) == _find(j):
                    continue
                if (
                    min(ai[0], bi[0]) - touch > max(aj[0], bj[0])
                    or min(aj[0], bj[0]) - touch > max(ai[0], bi[0])
                    or min(ai[1], bi[1]) - touch > max(aj[1], bj[1])
                    or min(aj[1], bj[1]) - touch > max(ai[1], bi[1])
                ):
                    continue
                if LineString([ai, bi]).distance(LineString([aj, bj])) <= touch:
                    parent[_find(i)] = _find(j)

    comps: dict[int, list[int]] = {}
    for i in range(len(pieces)):
        comps.setdefault(_find(i), []).append(i)
    tree = STRtree(big) if big else None
    glyphs: list[dict] = []
    for members in comps.values():
        xs = [v for m in members for v in (pieces[m][1][0], pieces[m][2][0])]
        ys = [v for m in members for v in (pieces[m][1][1], pieces[m][2][1])]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if max(x1 - x0, y1 - y0) > gmax or max(x1 - x0, y1 - y0) < WALL_TEXT_GLYPH_MIN_PX:
            continue
        if tree is not None and any(
            big[k].distance(seg) <= touch
            for m in members
            for seg in (LineString([pieces[m][1], pieces[m][2]]),)
            for k in tree.query(seg.buffer(touch))
        ):
            continue
        glyphs.append({
            "bbox": (x0, y0, x1, y1), "members": members,
            "pen": pieces[members[0]][4],
            "angles": [_line_angle_deg(pieces[m][1], pieces[m][2]) for m in members],
        })
    if len(glyphs) < WALL_TEXT_MIN_GLYPHS:
        return set()

    def _aligned(g, k, axis) -> bool:
        bg, bk = g["bbox"], k["bbox"]
        if axis == 0:
            (a0, a1, q0, q1), (c0, c1, r0, r1) = (bg[0], bg[2], bg[1], bg[3]), (bk[0], bk[2], bk[1], bk[3])
        else:
            (a0, a1, q0, q1), (c0, c1, r0, r1) = (bg[1], bg[3], bg[0], bg[2]), (bk[1], bk[3], bk[0], bk[2])
        hg, hk = q1 - q0, r1 - r0
        if min(hg, hk) < WALL_TEXT_GLYPH_MIN_PX or not 0.5 <= hg / hk <= 2.0:
            return False
        if (
            abs(q0 - r0) > WALL_TEXT_ALIGN_TOL_PX
            and abs(q1 - r1) > WALL_TEXT_ALIGN_TOL_PX
        ):
            return False
        return max(c0 - a1, a0 - c1) <= max(hg, hk)

    gparent = list(range(len(glyphs)))

    def _gfind(i):
        while gparent[i] != i:
            gparent[i] = gparent[gparent[i]]
            i = gparent[i]
        return i

    cell = 2 * gmax
    ggrid: dict[tuple[int, int], list[int]] = {}
    for i, g in enumerate(glyphs):
        b = g["bbox"]
        ggrid.setdefault((int(b[0] // cell), int(b[1] // cell)), []).append(i)
    for (gx, gy), members in ggrid.items():
        neigh = [
            m for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            for m in ggrid.get((gx + dx, gy + dy), ())
        ]
        for i in members:
            for j in neigh:
                if j <= i or glyphs[i]["pen"] != glyphs[j]["pen"]:
                    continue
                if _aligned(glyphs[i], glyphs[j], 0) or _aligned(glyphs[i], glyphs[j], 1):
                    ri, rj = _gfind(i), _gfind(j)
                    if ri != rj:
                        gparent[ri] = rj

    rows: dict[int, list[int]] = {}
    for i in range(len(glyphs)):
        rows.setdefault(_gfind(i), []).append(i)
    out: set[int] = set()
    for members in rows.values():
        if len(members) < WALL_TEXT_MIN_GLYPHS:
            continue
        gs = [glyphs[m] for m in members]
        if sum(1 for g in gs if len(g["members"]) >= 2) < WALL_TEXT_MIN_MULTI_STROKE:
            continue
        angles = [a for g in gs for a in g["angles"]]
        if not any(_angle_diff_mod180(a, angles[0]) >= WALL_TEXT_ANGLE_DIVERSITY for a in angles):
            continue
        for g in gs:
            out.update(pieces[m][0] for m in g["members"])
    return out


def _collect_wall_faces(
    paths: list[PathPrimitive],
    fill_is_wall: dict[tuple, bool] | None = None,
    marker_indices: frozenset[int] | set[int] = frozenset(),
    exclude_indices: frozenset[int] | set[int] = frozenset(),
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[list[_Seg], list[_Seg]]:
    """Return (stroked wall faces, filled-band centerlines)."""
    faces: list[_Seg] = []
    bands: list[_Seg] = []

    if fill_is_wall is None:
        rings = _collect_fill_rings(paths)
        fill_is_wall = _rate_fill_classes(rings, gates=gates)
        seams = _fill_seam_indices(rings, paths)
        marker_indices = {
            i for r in rings if r.is_marker() for i in r.indices
        } | seams
        # A seam is never a face of any tier — not even a stroked one
        # (detect_wall_network folds seams into its exclusion set the same
        # way; see the note there).
        exclude_indices = frozenset(exclude_indices) | frozenset(seams)

    def _wall_fill(p: PathPrimitive) -> bool:
        # Background (white) fills are masks or hollow walls — hollow walls
        # enter the network as polygons (detect_wall_network), never faces;
        # furniture-rated fill classes are cabinets and fixtures; unrated
        # fills keep the permissive legacy rule. Marker rings (arrowheads)
        # share the wall pen but are annotation — their edges never qualify;
        # nor do fill seams (_fill_seam_indices), which ride in the same set.
        if p.path_index in marker_indices:
            return False
        if p.fill is None or _is_background_fill(p.fill):
            return False
        return fill_is_wall.get(_fill_key(p.fill), True)

    for p in paths:
        # Walls arrive as stroked face lines, or (Vectorworks-style) as filled
        # polygons whose outlines explode into stroke_width-0 "l" items with a
        # fill color — accept those as faces too, when the fill class rates as
        # wall material.
        if p.path_index in exclude_indices:
            continue
        stroked = p.stroke_width >= WALL_MIN_STROKE_WIDTH_PX and not _is_dashed(p.dashes)
        filled_outline = _wall_fill(p)
        if p.item_type == "l" and len(p.points) >= 2 and (stroked or filled_outline):
            a, b = p.points[0], p.points[-1]
            if _line_length(a, b) < gates.WALL_FACE_MIN_LEN_PX:
                continue
            faces.append(_Seg(
                p1=a, p2=b, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
                indices={p.path_index}, stroked=stroked,
                stroke_width=p.stroke_width if stroked else 0.0,
                wall_fill=filled_outline,
                pen=_pen_key(p.color) if stroked else None,
            ))
        elif p.item_type in ("re", "qu") and _wall_fill(p) and len(p.points) == 4:
            pts = p.points
            if p.item_type == "qu":
                # PyMuPDF quads are (ul, ur, ll, lr) — reorder to a sequential ring.
                pts = [pts[0], pts[1], pts[3], pts[2]]
            d01 = _line_length(pts[0], pts[1])
            d12 = _line_length(pts[1], pts[2])
            short, long_ = min(d01, d12), max(d01, d12)
            if not (
                gates.WALL_MIN_THICKNESS_PX <= short <= gates.WALL_MAX_THICKNESS_PX
            ):
                continue
            if long_ < gates.WALL_FACE_MIN_LEN_PX or short < 1e-6:
                continue
            if long_ / short < WALL_BAND_MIN_ASPECT:
                continue
            if d01 < d12:
                # short sides are (0,1) and (2,3)
                c1 = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
                c2 = ((pts[2][0] + pts[3][0]) / 2, (pts[2][1] + pts[3][1]) / 2)
            else:
                c1 = ((pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2)
                c2 = ((pts[3][0] + pts[0][0]) / 2, (pts[3][1] + pts[0][1]) / 2)
            bands.append(_Seg(
                p1=c1, p2=c2, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
                indices={p.path_index}, thickness=short, source="filled_band",
                wall_fill=True,
            ))

    return faces, bands


def _collect_weak_faces(
    paths: list[PathPrimitive],
    exclude_indices: frozenset[int] | set[int] = frozenset(),
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_Seg]:
    """Hairline solid lines long enough to be wall pieces.

    Never faces on their own — detect_wall_network admits a weak pair only
    when the band between the faces carries wall material
    (_band_has_wall_material), so fixture outlines drawn in the same pen
    stay out of the network.
    """
    weak: list[_Seg] = []
    for p in paths:
        if p.path_index in exclude_indices:
            continue
        if p.item_type != "l" or len(p.points) < 2 or p.fill is not None:
            continue
        if not (0.0 < p.stroke_width < WALL_MIN_STROKE_WIDTH_PX):
            continue
        if _is_dashed(p.dashes):
            continue
        a, b = p.points[0], p.points[-1]
        if _line_length(a, b) < gates.WALL_FACE_MIN_LEN_PX:
            continue
        weak.append(_Seg(
            p1=a, p2=b, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
            indices={p.path_index}, stroked=False, stroke_width=0.0,
            pen=_pen_key(p.color),
        ))
    return weak


def _collect_stroked_rect_weak_faces(
    paths: list[PathPrimitive],
    exclude_indices: frozenset[int] | set[int] = frozenset(),
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_Seg]:
    """Virtual long edges of stroked, UNFILLED `re`/`qu` items — weak tier only.

    A wall segment is sometimes drawn as one closed box (a window infill, a
    pier, a new-wall stub) that the exporter emits as a single rectangle
    operator rather than four `l` items; face collection reads only `l`
    items (and FILLED rectangles as bands), so such a box contributes no
    faces at all (measured on s03: the 83x33px infill left of window_0011,
    a 1.5px `qu` in the wall pen hatched at 0.25px, never paired and two
    bedrooms merged through it). But the same geometry is also how beds,
    baths, basins, shower trays, radiator casings and door LEAVES are drawn
    (5x90px `re` items on s17/s20), and exploding every stroked rectangle
    into strong faces fenced ~40 fixtures into phantom rooms across the
    corpus and lost five real rooms — thickness and aspect do not separate
    the classes (target 33px/2.5 vs a window frame 18px/2.4 vs the 36px cap).

    The convention: a stroked atomic rectangle may represent a wall band
    when its opposite long edges lie at wall spacing AND the enclosed band
    carries distributed wall material. So the two long edges enter the
    material-gated WEAK tier (stroked=False, original pen and path index
    kept): they pair only through _band_has_wall_material, never gain
    lone-face barrier rights, and stay out of the stroke reference — a
    hollow box (a leaf, a bed) pairs with nothing. Short ends are omitted:
    a pair's wall solid is flat-capped, so the ends are implicit once the
    long edges pair (s03's explicit `l` closures, paths 15854/20330, are
    extra evidence, not the reason; and before _demote_stair_faces
    qualified rung members on their own intervals, a short end abutting a
    stair tread fused into the tread's rung and disqualified it). The
    shape gates here are a candidate
    prefilter, not evidence: short side within the wall-thickness range,
    long side a face length, aspect >= WALL_RECT_MIN_ASPECT.
    """
    out: list[_Seg] = []
    for p in paths:
        if p.path_index in exclude_indices:
            continue
        if p.item_type not in ("re", "qu") or len(p.points) != 4:
            continue
        if p.fill is not None or p.stroke_width < WALL_MIN_STROKE_WIDTH_PX:
            continue
        if _is_dashed(p.dashes):
            continue
        pts = p.points
        if p.item_type == "qu":
            # PyMuPDF quads are (ul, ur, ll, lr) — reorder to a sequential ring.
            pts = [pts[0], pts[1], pts[3], pts[2]]
        d01 = _line_length(pts[0], pts[1])
        d12 = _line_length(pts[1], pts[2])
        short, long_ = min(d01, d12), max(d01, d12)
        if short < 1e-6 or long_ < gates.WALL_FACE_MIN_LEN_PX:
            continue
        if not (gates.WALL_MIN_THICKNESS_PX <= short <= gates.WALL_MAX_THICKNESS_PX):
            continue
        if long_ / short < WALL_RECT_MIN_ASPECT:
            continue
        if d01 >= d12:
            long_edges = [(pts[0], pts[1]), (pts[2], pts[3])]
        else:
            long_edges = [(pts[1], pts[2]), (pts[3], pts[0])]
        for a, b in long_edges:
            out.append(_Seg(
                p1=a, p2=b, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
                indices={p.path_index}, stroked=False, stroke_width=0.0,
                pen=_pen_key(p.color),
            ))
    return out


def _dimension_line_indices(
    paths: list[PathPrimitive], *, gates: WallGates = WALL_GATES_UNSCALED
) -> set[int]:
    """Path indices of dimension-chain lines: annotation, never wall faces.

    A dimension line ends in a short oblique tick CENTERED on each endpoint
    and straddling the line — the architectural dimension terminator, drawn
    in the dimension pen. Both endpoints must be ticked: a wall that a
    dimension chain terminates against carries the tick mid-run, not at its
    own ends. Wall linework cannot match otherwise either — hatch/blocking
    strokes touch a face from inside the band (both tick ends on one side),
    and a chamfer stub at a wall corner meets the face end-to-end, leaving
    its midpoint half its length away from the endpoint.

    Dimension lines are penned in the wall widths on color-coded drawings
    (floor-plans: blue 1.5 vs walls at 1.0/1.5), so without this the chains
    survive every pen gate and fence room interiors — as lone barrier faces
    even when cross-pen pairing is blocked.
    """
    ticks: list[tuple] = []   # (mid, p1, p2, angle_deg, pen)
    lines: list[PathPrimitive] = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2 or p.stroke_width <= 0:
            continue
        a, b = p.points[0], p.points[-1]
        length = _line_length(a, b)
        if WALL_DIM_TICK_MIN_LEN_PX <= length <= WALL_DIM_TICK_MAX_LEN_PX:
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            ticks.append((mid, a, b, _line_angle_deg(a, b), _pen_key(p.color)))
        if length >= gates.WALL_FACE_MIN_LEN_PX and p.color is not None:
            lines.append(p)
    if not ticks or not lines:
        return set()

    cell = WALL_DIM_TICK_MAX_LEN_PX
    grid: dict[tuple[int, int], list[tuple]] = {}
    for t in ticks:
        key = (int(t[0][0] // cell), int(t[0][1] // cell))
        grid.setdefault(key, []).append(t)

    def _has_end_tick(pt, origin, ux, uy, line_angle, pen) -> bool:
        cx, cy = int(pt[0] // cell), int(pt[1] // cell)
        barb_sides: set[int] = set()
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for mid, t1, t2, ang, tpen in grid.get((gx, gy), ()):
                    if tpen != pen:
                        continue
                    rel = _angle_diff_mod180(ang, line_angle)
                    off1 = (t1[0] - origin[0]) * (-uy) + (t1[1] - origin[1]) * ux
                    off2 = (t2[0] - origin[0]) * (-uy) + (t2[1] - origin[1]) * ux
                    if (
                        _distance(mid, pt) <= WALL_DIM_TICK_END_TOL_PX
                        and WALL_DIM_TICK_ANGLE_MIN <= rel <= WALL_DIM_TICK_ANGLE_MAX
                        and off1 * off2 < 0
                        and min(abs(off1), abs(off2))
                        >= WALL_DIM_TICK_STRADDLE_MIN_PX
                    ):
                        return True
                    # Arrowhead barb: one end at the endpoint (the tip, or
                    # the base of an open head whose tip sits on the line
                    # a barb-length beyond the endpoint — s16 draws them
                    # so), the barb leaning off the line to one side; barbs
                    # on both sides = arrowhead.
                    if (
                        WALL_DIM_ARROW_ANGLE_MIN <= rel <= WALL_DIM_ARROW_ANGLE_MAX
                        and min(_distance(t1, pt), _distance(t2, pt))
                        <= WALL_DIM_TICK_END_TOL_PX
                    ):
                        lean = off1 if abs(off1) >= abs(off2) else off2
                        if abs(lean) >= WALL_DIM_TICK_STRADDLE_MIN_PX:
                            barb_sides.add(1 if lean > 0 else -1)
        return len(barb_sides) == 2

    out: set[int] = set()
    for p in lines:
        a, b = p.points[0], p.points[-1]
        length = _line_length(a, b)
        ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
        angle = _line_angle_deg(a, b)
        pen = _pen_key(p.color)
        if _has_end_tick(a, a, ux, uy, angle, pen) and _has_end_tick(
            b, a, ux, uy, angle, pen
        ):
            out.add(p.path_index)
    return out


def _collect_material_marks(
    paths: list[PathPrimitive], *, gates: WallGates = WALL_GATES_UNSCALED,
    max_len: float | None = None,
) -> list[tuple[tuple[float, float], float]]:
    """(midpoint, angle) of every short solid stroke, gathered once per page.

    These are the strokes wall material is drawn with: hatch, cross-hatch,
    and the X diagonals of blocking rectangles. Which of them are diagonal
    is decided per band in _band_has_wall_material — diagonality is relative
    to the band axis, so angled walls read the same as axis-aligned ones.

    Coincident strokes collapse to one mark: CAD exports re-draw dimension
    tick marks (once heavy, once light, and again per adjoining dimension
    run), and those duplicates inflated 2 tick locations past the ≥4-marks
    material gate, turning dimension lines into phantom partitions. Real
    hatch strokes sit at distinct offsets and are unaffected.
    """
    marks: list[tuple] = []
    seen: set[tuple[int, int, int]] = set()
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2 or p.fill is not None:
            continue
        if _is_dashed(p.dashes):
            continue
        a, b = p.points[0], p.points[-1]
        cap = gates.WALL_HATCH_MAX_LEN_PX if max_len is None else max_len
        if not (2.0 <= _line_length(a, b) <= cap):
            continue
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        angle = _line_angle_deg(a, b)
        key = (
            round(mid[0] / 2.5), round(mid[1] / 2.5), round(angle / 5.0) % 36,
        )
        if key in seen:
            continue
        seen.add(key)
        # Endpoints + pen ride along for the one-sided face-backing test
        # (_face_is_material_backed); the band gate ignores them.
        marks.append((mid, angle, a, b, _pen_key(p.color)))
    return marks


def _band_has_wall_material(
    c: _Seg, marks: list[tuple[tuple[float, float], float]],
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> bool:
    """True when the band under a centerline carries drawn wall material.

    Counts short strokes diagonal to the band axis whose midpoint lies inside
    the band INTERIOR, and requires them dense (WALL_WEAK_MATERIAL_PER_100PX)
    and spread along the band (WALL_WEAK_MATERIAL_MIN_SPAN) — a symbol clumped
    at one end of a long fixture run must not turn the whole run into wall.
    Marks hugging a face (within WALL_WEAK_MATERIAL_EDGE_PX) are annotation
    crossing that face — dimension ticks centred on their dimension line —
    not material between the faces; the interior floor keeps thin bands from
    rejecting their own centred hatch.
    """
    length = _line_length(c.p1, c.p2)
    if length < 1e-6:
        return False
    ux = (c.p2[0] - c.p1[0]) / length
    uy = (c.p2[1] - c.p1[1]) / length
    axis_angle = _line_angle_deg(c.p1, c.p2)
    half = max(
        c.thickness / 2.0 - WALL_WEAK_MATERIAL_EDGE_PX, c.thickness * 0.25
    )
    ts: list[float] = []
    for (mx, my), angle, *_ in marks:
        t = (mx - c.p1[0]) * ux + (my - c.p1[1]) * uy
        if not (-1.0 <= t <= length + 1.0):
            continue
        if abs((mx - c.p1[0]) * -uy + (my - c.p1[1]) * ux) > half:
            continue
        d = _angle_diff_mod180(angle, axis_angle)
        if WALL_WEAK_MATERIAL_ANGLE_MIN <= d <= WALL_WEAK_MATERIAL_ANGLE_MAX:
            ts.append(t)
    if len(ts) < WALL_WEAK_MATERIAL_MIN_MARKS:
        return False
    if len(ts) < (length / 100.0) * gates.WALL_WEAK_MATERIAL_PER_100PX:
        return False
    return (max(ts) - min(ts)) >= WALL_WEAK_MATERIAL_MIN_SPAN * length


def _band_has_through_hatch(
    c: _Seg, marks: list[tuple], *, gates: WallGates = WALL_GATES_UNSCALED,
) -> bool:
    """True when the band is hatched THROUGH: diagonal strokes whose two
    endpoints land on OPPOSITE faces (within WALL_WEAK_MATERIAL_EDGE_PX of
    ±thickness/2), dense and spread like _band_has_wall_material demands.

    The gate for pairs spaced beyond WALL_THICK_MATERIAL_MAX_PX (see
    WALL_THROUGH_HATCH_MAX_PX): a hatch tool clips its strokes to the region
    it fills, so strokes ending on both faces prove the faces bound one
    filled region — cut material in plan. Hatch clipped to some other
    boundary (a floor pattern, a fixture) stops short of at least one face.
    """
    length = _line_length(c.p1, c.p2)
    if length < 1e-6:
        return False
    ux = (c.p2[0] - c.p1[0]) / length
    uy = (c.p2[1] - c.p1[1]) / length
    axis_angle = _line_angle_deg(c.p1, c.p2)
    half = c.thickness / 2.0
    tol = WALL_WEAK_MATERIAL_EDGE_PX

    def perp(pt):
        return (pt[0] - c.p1[0]) * -uy + (pt[1] - c.p1[1]) * ux

    ts: list[float] = []
    for (mx, my), angle, a, b, _pen in marks:
        t = (mx - c.p1[0]) * ux + (my - c.p1[1]) * uy
        if not (-1.0 <= t <= length + 1.0):
            continue
        d = _angle_diff_mod180(angle, axis_angle)
        if not (WALL_WEAK_MATERIAL_ANGLE_MIN <= d <= WALL_WEAK_MATERIAL_ANGLE_MAX):
            continue
        # Each endpoint lands on a boundary of the filled region: one of
        # the two faces, or the run's END line (a perpendicular return
        # clips the strokes at a corner — the first band-width of a run
        # beside a corner is covered by strokes ending on the return, and
        # without them a short corner run fails the spread test; measured
        # on s05: 21.7px of spread over a 44px run, gate 22). The two
        # endpoints must sit on DIFFERENT boundaries, at least one a face.
        sa, sb = perp(a), perp(b)
        ta = (a[0] - c.p1[0]) * ux + (a[1] - c.p1[1]) * uy
        tb = (b[0] - c.p1[0]) * ux + (b[1] - c.p1[1]) * uy

        def boundary(sp, tp):
            if abs(sp - half) <= tol:
                return "hi"
            if abs(sp + half) <= tol:
                return "lo"
            if abs(sp) < half and (abs(tp) <= tol or abs(tp - length) <= tol):
                return "end"
            return None

        ba, bb = boundary(sa, ta), boundary(sb, tb)
        if ba and bb and ba != bb:
            ts.append(t)
    if len(ts) < WALL_WEAK_MATERIAL_MIN_MARKS:
        return False
    if len(ts) < (length / 100.0) * gates.WALL_WEAK_MATERIAL_PER_100PX:
        return False
    return (max(ts) - min(ts)) >= WALL_WEAK_MATERIAL_MIN_SPAN * length


def _face_is_material_backed(
    f: _Seg, marks: list[tuple], *, gates: WallGates = WALL_GATES_UNSCALED,
) -> bool:
    """True when same-pen hatch strokes hug one flank of the face's run.

    A hatched wall band is often drawn with only ONE long face: the outer
    boundary is a short jamb stub, a dashed over-line, or nothing at all
    (floor-plans' dining east wall: a 200px magenta face, a 20px stub, and
    the hatch — the old full-length seal came from pairing with the blue
    "3,119" dimension line, a phantom crutch the pen gates now refuse). The
    face plus ITS OWN hatch is honest wall evidence: diagonal strokes in the
    face's pen whose near endpoint lands ON the face line (real hatch is
    drawn off its boundary; a room-interior line running parallel OUTSIDE a
    hatched band never touches that band's strokes — they end on the band's
    own faces), dense and spread like the weak-pair material gate demands.
    Dimension ticks are centred on their line, so both their ends sit off
    it, past the edge margin.
    """
    length = _line_length(f.p1, f.p2)
    if length < gates.WALL_WEAK_MIN_RUN_PX or f.pen is None:
        return False
    ux = (f.p2[0] - f.p1[0]) / length
    uy = (f.p2[1] - f.p1[1]) / length
    axis_angle = _line_angle_deg(f.p1, f.p2)
    ts: list[float] = []
    for (mx, my), angle, a, b, pen in marks:
        if pen != f.pen:
            continue
        t = (mx - f.p1[0]) * ux + (my - f.p1[1]) * uy
        if not (-1.0 <= t <= length + 1.0):
            continue
        d = _angle_diff_mod180(angle, axis_angle)
        if not (WALL_WEAK_MATERIAL_ANGLE_MIN <= d <= WALL_WEAK_MATERIAL_ANGLE_MAX):
            continue
        near = min(
            abs((a[0] - f.p1[0]) * -uy + (a[1] - f.p1[1]) * ux),
            abs((b[0] - f.p1[0]) * -uy + (b[1] - f.p1[1]) * ux),
        )
        if near > WALL_WEAK_MATERIAL_EDGE_PX:
            continue
        ts.append(t)
    if len(ts) < WALL_WEAK_MATERIAL_MIN_MARKS:
        return False
    if len(ts) < (length / 100.0) * gates.WALL_WEAK_MATERIAL_PER_100PX:
        return False
    return (max(ts) - min(ts)) >= WALL_WEAK_MATERIAL_MIN_SPAN * length


def _face_material_spans(
    f: _Seg, marks: list[tuple], *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[tuple[float, float], ...]:
    """Sub-runs of a weak face beside which wall material is drawn.

    A hairline face bounds wall only where a hatched/blocked band lies
    against it. The collinear merge chains every same-line hairline piece
    into one face, and s02's joinery pen draws BOTH the plaster-skin line
    3px outside each hatched band AND the front of the built-in cupboard
    between two such bands — one 369px face that pairs over its two ends
    (0.38) and runs 210px through free space between them. Diagonal marks
    (hatch, blocking X's) whose midpoint lies within half a band thickness
    of the face — on either flank, so the s02 skin whose hatch ends 3px
    away still counts — are clustered along the run at hatch gaps
    (WALL_HATCH_MAX_LEN_PX); a cluster of >= WALL_WEAK_MATERIAL_MIN_MARKS
    marks at the weak-pair density is material, and its extent (padded by
    the same gap) is a backed span. Measured on s02: the cupboard front's
    230px unpaired run carries 4 marks in two dimension-tick pairs 158px
    apart (1.7/100px) — no cluster; the hatched bands either side carry a
    mark every 4px.
    """
    length = _line_length(f.p1, f.p2)
    if length < 1e-6:
        return ()
    ux = (f.p2[0] - f.p1[0]) / length
    uy = (f.p2[1] - f.p1[1]) / length
    axis_angle = _line_angle_deg(f.p1, f.p2)
    reach = gates.WALL_MAX_THICKNESS_PX / 2.0
    ts: list[float] = []
    for (mx, my), angle, *_ in marks:
        t = (mx - f.p1[0]) * ux + (my - f.p1[1]) * uy
        if not (-1.0 <= t <= length + 1.0):
            continue
        off = abs((mx - f.p1[0]) * -uy + (my - f.p1[1]) * ux)
        # A dimension tick is centred ON its line (both ends off it); hatch
        # midpoints sit inside the band, at least half its width away —
        # the band gate's own edge margin. s02's "600" ticks straddle the
        # cupboard front 48px from each band's last stroke and otherwise
        # joined the clusters, carrying the backed span into the mouth.
        if off <= WALL_WEAK_MATERIAL_EDGE_PX or off > reach:
            continue
        d = _angle_diff_mod180(angle, axis_angle)
        if WALL_WEAK_MATERIAL_ANGLE_MIN <= d <= WALL_WEAK_MATERIAL_ANGLE_MAX:
            ts.append(t)
    if len(ts) < WALL_WEAK_MATERIAL_MIN_MARKS:
        return ()
    ts.sort()
    gap = gates.WALL_HATCH_MAX_LEN_PX
    spans: list[tuple[float, float]] = []
    start = 0
    for i in range(1, len(ts) + 1):
        if i == len(ts) or ts[i] - ts[i - 1] > gap:
            cluster = ts[start:i]
            start = i
            if len(cluster) < WALL_WEAK_MATERIAL_MIN_MARKS:
                continue
            run = max(cluster[-1] - cluster[0], 1.0)
            if len(cluster) < (run / 100.0) * gates.WALL_WEAK_MATERIAL_PER_100PX:
                continue
            # The band ends one pitch past its last stroke: pad by the
            # cluster's own median pitch, never the cluster gap.
            steps = sorted(b - a for a, b in zip(cluster, cluster[1:]))
            pitch = steps[len(steps) // 2]
            spans.append((
                max(0.0, cluster[0] - pitch), min(length, cluster[-1] + pitch),
            ))
    return tuple(spans)


def _claims_interior_pair(c: _Seg, kept: list[_Seg]) -> bool:
    """True when a kept, tighter, parallel pair lies inside c's band.

    The material gate asks "is there drawn wall material between the faces?"
    — but an over-wide pair (a room-interior line paired with a real wall's
    far face) encloses the real wall's band and passes on the real wall's
    OWN hatch/blocking. The tighter pair strictly inside c's band, spanning
    the same run, is the wall that material belongs to; c is a phantom
    claiming it. Duplicate same-band pairs (shared faces, both band edges
    within the margin of c's) are not interior and never claim.
    """
    length = _line_length(c.p1, c.p2)
    if length < 1e-6:
        return False
    ux = (c.p2[0] - c.p1[0]) / length
    uy = (c.p2[1] - c.p1[1]) / length
    hc = c.thickness / 2.0
    for d in kept:
        if d is c:
            continue
        if d.thickness > c.thickness - 2.0 * WALL_WEAK_CLAIM_MARGIN_PX:
            continue
        if _angle_diff_mod180(
            _line_angle_deg(c.p1, c.p2), _line_angle_deg(d.p1, d.p2)
        ) > WALL_PARALLEL_ANGLE_TOL:
            continue
        mx = (d.p1[0] + d.p2[0]) / 2.0 - c.p1[0]
        my = (d.p1[1] + d.p2[1]) / 2.0 - c.p1[1]
        off = mx * -uy + my * ux
        hd = d.thickness / 2.0
        # Both of d's band edges inside c's band (small tolerance), and at
        # least one strictly interior — a coincident duplicate has both
        # edges on c's own edges and stays.
        if off - hd < -hc - 1.0 or off + hd > hc + 1.0:
            continue
        if (
            (off - hd) + hc < WALL_WEAK_CLAIM_MARGIN_PX
            and hc - (off + hd) < WALL_WEAK_CLAIM_MARGIN_PX
        ):
            continue
        t1 = (d.p1[0] - c.p1[0]) * ux + (d.p1[1] - c.p1[1]) * uy
        t2 = (d.p2[0] - c.p1[0]) * ux + (d.p2[1] - c.p1[1]) * uy
        overlap = min(max(t1, t2), length) - max(min(t1, t2), 0.0)
        if overlap < WALL_WEAK_CLAIM_OVERLAP_FRAC * length:
            continue
        return True
    return False


def _band_fill_cover(c: _Seg, fill_union) -> float:
    """Fraction of c's band interior (inset 1px from each face) lying on
    wall-rated fill area. 0.0 when the page has no wall fill."""
    if fill_union is None or fill_union.is_empty:
        return 0.0
    half = c.thickness / 2.0 - 1.0
    if half <= 0.0:
        return 0.0
    band = LineString([c.p1, c.p2]).buffer(half, cap_style=2)
    if band.area <= 0.0:
        return 0.0
    return band.intersection(fill_union).area / band.area


def _claims_far_side_pair(
    c: _Seg, kept: list[_Seg], fill_union, marks: list,
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> bool:
    """True when c is a wall face paired ACROSS FREE SPACE with parallel ink.

    A wall's material lies on exactly one side of each of its faces. When a
    kept, meaningfully tighter pair shares a face with c and its band lies on
    the OTHER side of that face, the shared face is a wall face and c's band
    is the room beside it — a kitchen counter front, a wardrobe front or a
    corridor's far wall drawn in the wall pen at wall-like spacing (measured
    on s03: the worktop outline 35.2px off the kitchen's inner wall faces,
    just under WALL_MAX_THICKNESS_PX, fenced the counters out of the room).
    c survives only when its own band carries drawn wall material — fill
    area or hatch — since a cavity wall drawn leaf/cavity/leaf legitimately
    pairs its leaf faces across the cavity, and an unhatched cavity is a
    closed sliver the room stage erodes away regardless.
    """
    length = _line_length(c.p1, c.p2)
    if length < 1e-6 or not c.indices:
        return False
    ux = (c.p2[0] - c.p1[0]) / length
    uy = (c.p2[1] - c.p1[1]) / length
    hc = c.thickness / 2.0
    for d in kept:
        if d is c or not (c.indices & d.indices):
            continue
        if d.thickness > c.thickness - 2.0 * WALL_WEAK_CLAIM_MARGIN_PX:
            continue
        if _angle_diff_mod180(
            _line_angle_deg(c.p1, c.p2), _line_angle_deg(d.p1, d.p2)
        ) > WALL_PARALLEL_ANGLE_TOL:
            continue
        mx = (d.p1[0] + d.p2[0]) / 2.0 - c.p1[0]
        my = (d.p1[1] + d.p2[1]) / 2.0 - c.p1[1]
        off = abs(mx * -uy + my * ux)
        # d's band must sit beyond c's edge — centred past the shared face,
        # not nested inside c (that is _claims_interior_pair's case).
        if off < hc - 1.0:
            continue
        t1 = (d.p1[0] - c.p1[0]) * ux + (d.p1[1] - c.p1[1]) * uy
        t2 = (d.p2[0] - c.p1[0]) * ux + (d.p2[1] - c.p1[1]) * uy
        overlap = min(max(t1, t2), length) - max(min(t1, t2), 0.0)
        if overlap < WALL_WEAK_CLAIM_OVERLAP_FRAC * length:
            continue
        if _band_fill_cover(c, fill_union) >= WALL_FAR_SIDE_FILL_COVER_MAX:
            return False
        if _band_has_wall_material(c, marks, gates=gates):
            return False
        return True
    return False


def _demote_lattice_faces(
    faces: list[_Seg], *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[list[_Seg], list[_Seg]]:
    """Split merged faces into (kept, striped-field members).

    A striped field is >= WALL_LATTICE_MIN_RUNGS parallel same-pen rungs at
    equal wall-like pitch (one missing rung tolerated as a 2x-pitch gap),
    with rung extents chaining along the run and MIN_RUNGS of them coexisting
    somewhere along the axis. Paving bonds, tile fields, stair treads, roof
    tiling, balustrades, hatch and table rows all match; wall structure
    cannot (rooms are wider than WALL_MAX_THICKNESS_PX). A rung is an
    EXTENT-CONNECTED cluster of collinear pieces, not every piece at that
    offset on the page: a wall face merely collinear with a distant field's
    course is not that course. Members lying in the field's stacked span are
    demoted to the weak pipeline, not dropped: every pair they form — with
    each other or with a real wall's face — then needs drawn material
    between the faces, exactly like the hairline joinery pen.

    Fill outlines and layer-hinted faces carry their own evidence and are
    never demoted (same rule as the relative pen gate).
    """
    candidates = [
        (i, f) for i, f in enumerate(faces)
        if f.stroked and f.stroke_width > 0
        and not f.wall_fill and not f.layer_hint
    ]
    lattice: set[int] = set()

    by_pen: dict[int, list[tuple[int, _Seg]]] = {}
    for i, f in candidates:
        by_pen.setdefault(
            int(round(f.stroke_width / WALL_LATTICE_PEN_TOL)), []
        ).append((i, f))

    for pen_members in by_pen.values():
        if len(pen_members) < WALL_LATTICE_MIN_RUNGS:
            continue
        # Cluster by direction (mod 180): sort by angle, split on gaps wider
        # than the parallel tolerance, and merge the wrap-around clusters.
        angled = sorted(
            (_line_angle_deg(f.p1, f.p2), i, f) for i, f in pen_members
        )
        clusters: list[list[tuple[float, int, _Seg]]] = []
        for entry in angled:
            if clusters and entry[0] - clusters[-1][-1][0] <= WALL_PARALLEL_ANGLE_TOL:
                clusters[-1].append(entry)
            else:
                clusters.append([entry])
        if (
            len(clusters) > 1
            and (angled[0][0] + 180.0) - angled[-1][0] <= WALL_PARALLEL_ANGLE_TOL
        ):
            clusters[0].extend(clusters.pop())

        for cluster in clusters:
            if len(cluster) < WALL_LATTICE_MIN_RUNGS:
                continue
            _, _, ref = max(
                cluster, key=lambda t: _line_length(t[2].p1, t[2].p2)
            )
            ref_len = _line_length(ref.p1, ref.p2)
            if ref_len < 1e-6:
                continue
            ux = (ref.p2[0] - ref.p1[0]) / ref_len
            uy = (ref.p2[1] - ref.p1[1]) / ref_len
            nx, ny = -uy, ux

            # Rungs: faces bucketed by perpendicular offset; collinear pieces
            # at one offset (staggered-bond joints, interrupted joint lines)
            # are one rung. Pieces are kept individually: the field test
            # below needs actual coverage, not envelopes.
            offset_rows: list[dict] = []
            for _, i, f in sorted(
                cluster,
                key=lambda t: (t[2].p1[0] + t[2].p2[0]) * nx / 2.0
                + (t[2].p1[1] + t[2].p2[1]) * ny / 2.0,
            ):
                mx = (f.p1[0] + f.p2[0]) / 2.0
                my = (f.p1[1] + f.p2[1]) / 2.0
                off = mx * nx + my * ny
                lo, hi = _projected_interval(f.p1, f.p2, ux, uy, (0.0, 0.0))
                if (
                    offset_rows
                    and off - offset_rows[-1]["off"] <= WALL_LATTICE_OFFSET_TOL_PX
                ):
                    offset_rows[-1]["pieces"].append((lo, hi, i))
                else:
                    offset_rows.append({"off": off, "pieces": [(lo, hi, i)]})
            # A rung is extent-connected: a room's wall face that merely
            # happens to be collinear with a distant field's course (s17:
            # the WC's top face shares its offset with a roof-tile rung
            # 2000px to the right) is not a member of that rung, so it can
            # not be demoted along with the field. Pieces at one offset are
            # split wherever the along-axis gap exceeds the touch gap.
            rows: list[dict] = []
            for orow in offset_rows:
                for lo, hi, i in sorted(orow["pieces"]):
                    if rows and rows[-1]["off"] == orow["off"] and (
                        lo - rows[-1]["hi"] <= WALL_LATTICE_TOUCH_GAP_PX
                    ):
                        r = rows[-1]
                        r["members"].append(i)
                        r["pieces"].append((lo, hi))
                        r["total"] += hi - lo
                        r["hi"] = max(r["hi"], hi)
                    else:
                        rows.append({
                            "off": orow["off"], "members": [i],
                            "pieces": [(lo, hi)], "total": hi - lo,
                            "lo": lo, "hi": hi,
                        })
            rows.sort(key=lambda r: (r["off"], r["lo"]))
            # One scan: hatch is a striped field like any other, just one
            # pitched too tightly to be walls, and it is caught by the same
            # rule (pitch is what proves the lines are not walls; measured,
            # both reference PDFs' hatch fields pitch at 4.05/4.07px while
            # the tightest real striped field on either is 11.4px).
            lattice |= _scan_striped_runs(
                rows,
                gates.WALL_MAX_THICKNESS_PX + WALL_LATTICE_PITCH_TOL_PX,
                gates=gates,
            )

    kept = [f for i, f in enumerate(faces) if i not in lattice]
    demoted = [f for i, f in enumerate(faces) if i in lattice]
    return kept, demoted


def _scan_striped_runs(
    rows: list[dict],
    max_pitch: float,
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> set[int]:
    """Face indices belonging to striped runs.

    Runs chain while the pitch stays equal (one missing rung tolerated) and
    within max_pitch, and demote only where MIN_RUNGS of them COEXIST along
    the axis — and only the rungs lying in that stacked span.
    """
    demoted: set[int] = set()
    rungs = rows
    if len(rungs) < WALL_LATTICE_MIN_RUNGS:
        return demoted

    start = 0
    while start < len(rungs) - 1:
        # Rows are extent-aware, so a rung lying apart from the run along
        # the axis is unrelated linework at a coincident offset (s17: a
        # 49px stroke 2000px along the axis at an intermediate offset) —
        # it is SKIPPED, never a break: treating it as one left 3 of a
        # 22-rung roof-tile field strong on s03, and they paired into
        # phantom wall bands. A second row at the SAME offset that does
        # touch the run is the same rung split by a text mask wider than
        # the touch gap, and is absorbed into it.
        run = [rungs[start]]
        env_lo, env_hi = rungs[start]["lo"], rungs[start]["hi"]
        pitch: float | None = None
        nxt = start + 1
        while nxt < len(rungs):
            r = rungs[nxt]
            if (
                r["lo"] - env_hi > WALL_LATTICE_TOUCH_GAP_PX
                or env_lo - r["hi"] > WALL_LATTICE_TOUCH_GAP_PX
            ):
                nxt += 1
                continue
            gap = r["off"] - run[-1]["off"]
            if gap <= WALL_LATTICE_OFFSET_TOL_PX:
                run[-1] = _merge_rungs(run[-1], r)
            elif pitch is None:
                if not (gates.WALL_MIN_THICKNESS_PX <= gap <= max_pitch):
                    break
                pitch = gap
                run.append(r)
            elif (
                abs(gap - pitch) > WALL_LATTICE_PITCH_TOL_PX
                and abs(gap - 2.0 * pitch) > WALL_LATTICE_PITCH_TOL_PX
            ):
                break
            else:
                run.append(r)
            env_lo = min(env_lo, r["lo"])
            env_hi = max(env_hi, r["hi"])
            nxt += 1
        # Chained membership is not enough: distinct parallel wall bands
        # stacked at quasi-equal spacing chain too (measured on
        # s07: three 8px wall bands at 8-9px gaps
        # chained into a 5-rung "ladder" and deleted the plan's central wall
        # belt). A drawn FIELD has its courses side by side: somewhere along
        # the axis, MIN_RUNGS rungs coexist. Wall belts never stack that
        # deep — their rungs occupy disjoint spans that only envelopes glue
        # together. And a rung OUTLASTING that stacked span — longer than
        # the whole span, out of scale with the run's shortest rung, and
        # lying mostly outside the span — is not the field's course but a
        # wall face the stack happens to coexist with over a fraction of
        # its length (measured on s17: four 891px lines of a doubled frame
        # at 12px pitch, demoted wholesale by a fifth parallel line beside
        # them); it keeps its face rights. Everything else in the run is
        # the field's own ink: ragged-edge fragments (no longer than the
        # span) and hatch strokes staggered along the axis (all of one
        # length, coexisting only marginally) included.
        if len(run) >= WALL_LATTICE_MIN_RUNGS:
            span = _field_span(run)
            if not span:
                start += 1
                continue
            span_len = sum(b - a for a, b in span)
            shortest = min(r["hi"] - r["lo"] for r in run)
            for r in run:
                extent = r["hi"] - r["lo"]
                outlasts = (
                    extent > span_len
                    and extent > WALL_LATTICE_OUTLAST_RATIO * shortest
                    and _covered_length(r, span)
                    < WALL_LATTICE_FIELD_COVER_FRAC * extent
                )
                if not outlasts:
                    demoted.update(r["members"])
        # Every rung seeds: with skipped (apart) rungs inside a run's index
        # range, jumping to the run's end would deny those rungs — another
        # field's courses at coincident offsets — a run of their own.
        start += 1

    return demoted


def _merge_rungs(a: dict, b: dict) -> dict:
    """One rung from two same-offset rows (a copy; rows are re-scanned)."""
    return {
        "off": a["off"], "members": a["members"] + b["members"],
        "pieces": a["pieces"] + b["pieces"], "total": a["total"] + b["total"],
        "lo": min(a["lo"], b["lo"]), "hi": max(a["hi"], b["hi"]),
    }


def _field_span(run: list[dict]) -> list[tuple[float, float]]:
    """Intervals along the axis where >= MIN_RUNGS rungs of the run coexist.

    Sweeps the rungs' extents; ends sort before starts, so courses meeting
    end-to-end (staggered-bond joints on adjacent courses) never count as
    coexisting.
    """
    events: list[tuple[float, int]] = []
    for r in run:
        events.append((r["lo"], 1))
        events.append((r["hi"], -1))
    events.sort(key=lambda e: (e[0], e[1]))
    span: list[tuple[float, float]] = []
    depth = 0
    open_at: float | None = None
    for x, delta in events:
        depth += delta
        if depth >= WALL_LATTICE_MIN_RUNGS and open_at is None:
            open_at = x
        elif depth < WALL_LATTICE_MIN_RUNGS and open_at is not None:
            span.append((open_at, x))
            open_at = None
    return span


def _covered_length(r: dict, span: list[tuple[float, float]]) -> float:
    """Length of the rung's extent lying inside the field span."""
    return sum(
        max(0.0, min(r["hi"], b) - max(r["lo"], a)) for a, b in span
    )


def _merge_collinear_segs(
    segs: list[_Seg], gap_px: float, *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_Seg]:
    """Merge segments lying on the same infinite line into runs.

    Bridges gaps up to gap_px; keeps the max thickness, unions path indices,
    and ORs layer hints across merged members. wall_fill carries over only
    when fill-outline members cover >= WALL_FILL_MERGE_MIN_FRAC of the run.

    gates.COLLINEAR_OFFSET_TOL gates the same "is this the same drawn line"
    world-space judgment as WALL_MIN_THICKNESS_PX: at f=1.0 the 4.0px offset
    tolerance sits comfortably above WALL_MIN_THICKNESS_PX (2.0), but left
    unscaled it would exceed a shrunk-world wall's own face spacing at
    smaller f and silently fuse a real wall's two faces into one line, which
    then can never pair. Measured via the shrunk-world synthetic test: an
    8px-at-1:50 band shrinks to 4px at f=0.5, exactly the unscaled
    tolerance, and the two faces merged into a single line with zero
    centerlines recovered.
    """
    if not segs:
        return []

    merged = list(segs)
    changed = True
    while changed:
        changed = False
        out: list[_Seg] = []
        used = [False] * len(merged)

        for i, a in enumerate(merged):
            if used[i]:
                continue
            dx = a.p2[0] - a.p1[0]
            dy = a.p2[1] - a.p1[1]
            length_a = math.hypot(dx, dy)
            if length_a < 1e-6:
                used[i] = True
                continue
            ux, uy = dx / length_a, dy / length_a

            run_pts = [a.p1, a.p2]
            run = _Seg(
                p1=a.p1, p2=a.p2, layer=a.layer, layer_hint=a.layer_hint,
                indices=set(a.indices), thickness=a.thickness, source=a.source,
                stroked=a.stroked, stroke_width=a.stroke_width,
                wall_fill=a.wall_fill, pen=a.pen,
            )
            fill_len = length_a if a.wall_fill else 0.0

            for j, b in enumerate(merged):
                if j <= i or used[j]:
                    continue
                if _line_length(b.p1, b.p2) < 1e-6:
                    continue
                # One run, one pen: merging a dimension-line stub into a wall
                # face (or vice versa) launders annotation ink into wall
                # evidence over the whole merged extent.
                if not _pens_compatible(run.pen, b.pen):
                    continue
                if _angle_diff_mod180(
                    _line_angle_deg(a.p1, a.p2), _line_angle_deg(b.p1, b.p2)
                ) > COLLINEAR_ANGLE_TOL:
                    continue
                # One run, one thickness: a centerline meaningfully thicker
                # or thinner than the run measures a DIFFERENT band, not a
                # continuation — a jamb-scale pier's room-side face pairs
                # with the wall's outer face into a short thick centerline
                # offset within COLLINEAR_OFFSET_TOL of the band's own, and
                # taking the max over members stamped the pier's width onto
                # the entire run (measured on s03: a 16.5px nib pair at th
                # 13.8 carried onto a 6px band over 272px, holding the
                # kitchen outline 6px off the wall; same on s02 (877,314):
                # th 34.9 over 17px onto a 14px/251px run; s01 (818,907):
                # th 29.2 over 12px onto a 22px/121px run). Same-band members
                # differ by <= 0.3px on all three sheets, so the redundancy
                # collapse's WALL_REDUNDANT_THICKNESS_SLACK_PX is the gate
                # here too; the thick piece stays its own segment and its
                # solid stays local. Faces carry thickness 0 and are never
                # affected.
                if (
                    abs(b.thickness - run.thickness)
                    > WALL_REDUNDANT_THICKNESS_SLACK_PX
                ):
                    continue

                # Perpendicular offset from a's line to b
                offset = abs((b.p1[0] - a.p1[0]) * (-uy) + (b.p1[1] - a.p1[1]) * ux)
                if offset > gates.COLLINEAR_OFFSET_TOL:
                    continue

                t_b1 = _project_onto_axis(b.p1, a.p1, ux, uy)
                t_b2 = _project_onto_axis(b.p2, a.p1, ux, uy)
                run_ts = [_project_onto_axis(p, a.p1, ux, uy) for p in run_pts]
                gap = max(
                    min(t_b1, t_b2) - max(run_ts),
                    min(run_ts) - max(t_b1, t_b2),
                    0.0,
                )
                if gap > gap_px:
                    continue

                run_pts.extend([b.p1, b.p2])
                run.indices |= b.indices
                run.layer_hint = run.layer_hint or b.layer_hint
                run.stroked = run.stroked or b.stroked
                run.stroke_width = max(run.stroke_width, b.stroke_width)
                if b.wall_fill:
                    fill_len += _line_length(b.p1, b.p2)
                run.thickness = max(run.thickness, b.thickness)
                if run.pen is None:
                    run.pen = b.pen
                if b.layer and not run.layer:
                    run.layer = b.layer
                used[j] = True
                changed = True

            ts = [_project_onto_axis(p, a.p1, ux, uy) for p in run_pts]
            t_lo, t_hi = min(ts), max(ts)
            run.p1 = (a.p1[0] + ux * t_lo, a.p1[1] + uy * t_lo)
            run.p2 = (a.p1[0] + ux * t_hi, a.p1[1] + uy * t_hi)
            # Fill evidence spans the merged run only when the fill-outline
            # members cover most of it (see WALL_FILL_MERGE_MIN_FRAC): the
            # pen rule above keeps annotation ink from laundering into wall
            # evidence, and a fill stub must not launder its flag onto a
            # long stroke either. Members overlapping one another can
            # over-count, which only ever keeps a flag a coincident stroke
            # would have kept anyway.
            run.wall_fill = (
                fill_len >= WALL_FILL_MERGE_MIN_FRAC * max(t_hi - t_lo, 1e-6)
            )
            out.append(run)
            used[i] = True

        merged = out

    return merged


def _pair_faces_to_centerlines(
    faces: list[_Seg], thick_tier: bool = False,
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_Seg]:
    """Every qualifying near-parallel face pair emits a centerline over the
    overlapped extent, carrying the face spacing as thickness.

    Unlike the retired detect_walls: no greedy one-partner pairing and no
    length-ratio gate — one long exterior face legitimately pairs with several
    short interior stubs. Duplicate centerlines collapse in the merge stage.

    thick_tier additionally emits STRONG-face pairs spaced between
    WALL_MAX_THICKNESS_PX and WALL_THICK_MATERIAL_MAX_PX, flagged thick=True
    — a locally thickened masonry pier (chimney breast) exceeds the normal
    cap and its enclosed hatch would otherwise survive as a free-space
    pocket (phantom room). The caller MUST material-gate thick pairs
    (_band_has_wall_material) exactly like weak ones: at pier spacing the
    pair could just as well be a face beside a corridor. The interim
    stroke-reference pairing keeps the tier off so 36-48px annotation
    coincidences cannot skew the pen statistics.
    """
    n_buckets = max(1, int(math.ceil(180.0 / WALL_PARALLEL_ANGLE_TOL)))
    buckets: dict[int, list[int]] = {}
    for idx, f in enumerate(faces):
        b = int(_line_angle_deg(f.p1, f.p2) // WALL_PARALLEL_ANGLE_TOL) % n_buckets
        buckets.setdefault(b, []).append(idx)

    centerlines: list[_Seg] = []
    for b, members in buckets.items():
        # Pairs straddling a bucket boundary are covered by also checking the
        # next bucket (wrapping); buckets are disjoint so each unordered pair
        # is visited exactly once.
        nb = (b + 1) % n_buckets
        neighbor = buckets.get(nb, []) if nb != b else []
        for pos, i in enumerate(members):
            fi = faces[i]
            len_i = _line_length(fi.p1, fi.p2)
            if len_i < 1e-6:
                continue
            ux = (fi.p2[0] - fi.p1[0]) / len_i
            uy = (fi.p2[1] - fi.p1[1]) / len_i
            for j in members[pos + 1:] + neighbor:
                fj = faces[j]
                # A wall's two faces are drawn by one pen: cross-pen pairs
                # (a blue dimension line beside a red cabinet front at
                # wall-like spacing) are annotation coincidence, never wall.
                if not _pens_compatible(fi.pen, fj.pen):
                    continue
                if _angle_diff_mod180(
                    _line_angle_deg(fi.p1, fi.p2), _line_angle_deg(fj.p1, fj.p2)
                ) > WALL_PARALLEL_ANGLE_TOL:
                    continue
                spacing = _perpendicular_spacing(fi.p1, fi.p2, fj.p1, fj.p2)
                if spacing < gates.WALL_MIN_THICKNESS_PX:
                    continue
                thick = spacing > gates.WALL_MAX_THICKNESS_PX
                through = spacing > gates.WALL_THICK_MATERIAL_MAX_PX
                if thick and (
                    not thick_tier
                    or spacing > gates.WALL_THROUGH_HATCH_MAX_PX
                    # Pier faces are drawn in the wall pen; the demoted
                    # tiers (hairline, lattice, light-pen, tile) keep their
                    # tuned <=36px envelope.
                    or fi.weak or fj.weak
                ):
                    continue
                lo_i, hi_i = _projected_interval(fi.p1, fi.p2, ux, uy, fi.p1)
                lo_j, hi_j = _projected_interval(fj.p1, fj.p2, ux, uy, fi.p1)
                lo, hi = max(lo_i, lo_j), min(hi_i, hi_j)
                if hi - lo < gates.WALL_PAIR_MIN_OVERLAP_PX:
                    continue

                # One band, one thickness: `spacing` above is sampled at
                # fj.p1, which is the pair's spacing everywhere only when
                # the faces are truly parallel. Inside the angle tolerance a
                # chord across the band (a brick-hatch cell's diagonal) reads
                # whatever the divergence is at that one point — possibly
                # hundreds of px past the overlap — and its centerline lands
                # on the wrong side. Interpolate fj's signed offset from fi's
                # line at both ends of the overlap; a wall pair's spacing
                # stays put, a chord's runs to zero (WALL_PAIR_TAPER_MAX_FRAC).
                nx, ny = -uy, ux
                s1 = (fj.p1[0] - fi.p1[0]) * nx + (fj.p1[1] - fi.p1[1]) * ny
                s2 = (fj.p2[0] - fi.p1[0]) * nx + (fj.p2[1] - fi.p1[1]) * ny
                t1 = _project_onto_axis(fj.p1, fi.p1, ux, uy)
                t2 = _project_onto_axis(fj.p2, fi.p1, ux, uy)
                if abs(t2 - t1) > 1e-9:
                    s_lo = s1 + (s2 - s1) * (lo - t1) / (t2 - t1)
                    s_hi = s1 + (s2 - s1) * (hi - t1) / (t2 - t1)
                else:
                    s_lo = s_hi = s1
                if abs(s_lo - s_hi) > WALL_PAIR_TAPER_MAX_FRAC * max(
                    abs(s_lo), abs(s_hi), 1e-9
                ):
                    continue

                # Midline: offset half the spacing from fi's line toward fj.
                side = (fj.p1[0] - fi.p1[0]) * nx + (fj.p1[1] - fi.p1[1]) * ny
                off = spacing / 2.0 if side >= 0 else -spacing / 2.0
                c1 = (fi.p1[0] + ux * lo + nx * off, fi.p1[1] + uy * lo + ny * off)
                c2 = (fi.p1[0] + ux * hi + nx * off, fi.p1[1] + uy * hi + ny * off)
                centerlines.append(_Seg(
                    p1=c1, p2=c2,
                    layer=fi.layer or fj.layer,
                    layer_hint=fi.layer_hint or fj.layer_hint,
                    indices=fi.indices | fj.indices,
                    thickness=spacing,
                    source="face_pair",
                    stroked=fi.stroked or fj.stroked,
                    stroke_width=max(fi.stroke_width, fj.stroke_width),
                    wall_fill=fi.wall_fill or fj.wall_fill,
                    weak=fi.weak or fj.weak,
                    thick=thick,
                    through=through,
                ))
    return centerlines


def _line_intersection(
    p1: tuple[float, float], p2: tuple[float, float],
    q1: tuple[float, float], q2: tuple[float, float],
) -> tuple[float, float] | None:
    """Intersection of the two infinite lines, or None when near-parallel."""
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = q2[0] - q1[0], q2[1] - q1[1]
    denom = d1x * d2y - d1y * d2x
    if abs(denom) < 1e-9:
        return None
    t = ((q1[0] - p1[0]) * d2y - (q1[1] - p1[1]) * d2x) / denom
    return (p1[0] + d1x * t, p1[1] + d1y * t)


WALL_REDUNDANT_OFFSET_SLACK_PX = 2.0   # extra reach beyond half-thickness when collapsing
WALL_REDUNDANT_MIN_COVER = 0.80        # fraction of the shorter run covered to call it redundant
WALL_REDUNDANT_THICKNESS_SLACK_PX = 4.0  # an absorbed duplicate may exceed the kept
                                         # run's thickness by at most this much — a
                                         # duplicate measures the SAME band, so only
                                         # hatch-boundary jitter separates the two


def _collapse_redundant_centerlines(segs: list[_Seg]) -> list[_Seg]:
    """Drop near-parallel centerlines that duplicate a longer one.

    Thick hatched walls carry more linework than their two faces (hatch
    boundaries, trim lines), so pairing emits several parallel centerlines a
    few px apart. Those redundant lines fragment the network with dangles and
    enclose thin strip faces that masquerade as rooms. Keep the longest line
    of each overlapping parallel group.

    A "duplicate" meaningfully THICKER than the kept run is a different
    structure, not a re-measurement: a wall face pairing with another wall's
    face across a corridor of wall-like width shares one face with the real
    run, so its centerline sits close enough to pass the offset gate (its own
    inflated thickness buys the reach), and absorbing it would transfer the
    corridor-wide thickness onto the ENTIRE run (measured on floor-plans: the
    bathroom/landing wall's 7.2px run took th 35.2 from a face pairing across
    the stair corridor over a 41px overlap, and the poisoned solid fenced a
    16px strip out of the bathroom and 13px off the landing over the whole
    165px run). Such a pair stays a separate segment — its solid stays local
    to the overlap where the pair actually measured something.
    """
    ordered = sorted(segs, key=lambda s: -_line_length(s.p1, s.p2))
    kept: list[_Seg] = []
    for s in ordered:
        len_s = _line_length(s.p1, s.p2)
        if len_s < 1e-6:
            continue
        redundant = False
        for k in kept:
            if _angle_diff_mod180(
                _line_angle_deg(s.p1, s.p2), _line_angle_deg(k.p1, k.p2)
            ) > WALL_PARALLEL_ANGLE_TOL:
                continue
            offset = _perpendicular_spacing(k.p1, k.p2, s.p1, s.p2)
            if offset > max(k.thickness, s.thickness) / 2.0 + WALL_REDUNDANT_OFFSET_SLACK_PX:
                continue
            len_k = _line_length(k.p1, k.p2)
            ux = (k.p2[0] - k.p1[0]) / len_k
            uy = (k.p2[1] - k.p1[1]) / len_k
            lo_k, hi_k = _projected_interval(k.p1, k.p2, ux, uy, k.p1)
            lo_s, hi_s = _projected_interval(s.p1, s.p2, ux, uy, k.p1)
            covered = max(0.0, min(hi_k, hi_s) - max(lo_k, lo_s))
            if s.thickness > k.thickness + WALL_REDUNDANT_THICKNESS_SLACK_PX:
                continue
            if covered >= WALL_REDUNDANT_MIN_COVER * len_s:
                k.indices |= s.indices
                k.layer_hint = k.layer_hint or s.layer_hint
                k.stroked = k.stroked or s.stroked
                k.stroke_width = max(k.stroke_width, s.stroke_width)
                k.wall_fill = k.wall_fill or s.wall_fill
                k.thickness = max(k.thickness, s.thickness)
                redundant = True
                break
        if not redundant:
            kept.append(s)
    return kept


def _snap_intersections(segs: list[_Seg]) -> None:
    """Snap endpoints onto exact centerline intersection points.

    Two centerlines meeting at a corner both stop half-a-thickness away from
    the true junction (or overshoot it by the face extent); a butting wall's
    centerline ends short of the through-wall's centerline (T-junction). For
    each non-parallel pair whose line intersection lies near both segments,
    endpoints near the intersection are moved exactly onto it — undershoot is
    extended, small overshoot is trimmed, and crossings are left for
    unary_union to node. The per-segment tolerance adapts to the partner's
    thickness (a butting wall stops partner-thickness/2 short).
    """
    for i in range(len(segs)):
        si = segs[i]
        for j in range(i + 1, len(segs)):
            sj = segs[j]
            ang = _angle_diff_mod180(
                _line_angle_deg(si.p1, si.p2), _line_angle_deg(sj.p1, sj.p2)
            )
            if ang < WALL_JUNCTION_MIN_ANGLE_DEG:
                continue
            x = _line_intersection(si.p1, si.p2, sj.p1, sj.p2)
            if x is None:
                continue
            tol_i = sj.thickness / 2.0 + WALL_JUNCTION_SNAP_PX
            tol_j = si.thickness / 2.0 + WALL_JUNCTION_SNAP_PX
            if _point_to_segment_distance(x, si.p1, si.p2) > tol_i:
                continue
            if _point_to_segment_distance(x, sj.p1, sj.p2) > tol_j:
                continue
            for seg, tol in ((si, tol_i), (sj, tol_j)):
                d1 = math.hypot(seg.p1[0] - x[0], seg.p1[1] - x[1])
                d2 = math.hypot(seg.p2[0] - x[0], seg.p2[1] - x[1])
                if min(d1, d2) > tol:
                    continue  # the segment passes through x — a true crossing
                if d1 <= d2:
                    seg.p1 = x
                else:
                    seg.p2 = x


def _demote_stair_faces(
    faces: list[_Seg],
    rings: list[_FillRing],
    text_spans: list[TextSpan],
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[list[_Seg], list[_Seg]]:
    """Split path-level faces into (kept, stair ink).

    Runs BEFORE the collinear merge, on one face per path: a stair's landing
    edge is often collinear with a wall nib's face and merges into it, and
    demoting the merged run would cost the nib its face. See the
    WALL_STAIR_* block for the three recognizers and the zone rule.
    """
    cand = [
        (i, f) for i, f in enumerate(faces)
        if f.stroked and f.stroke_width > 0
        and not f.wall_fill and not f.layer_hint
    ]
    if len(cand) < 2:
        return faces, []
    max_pitch = gates.WALL_THICK_MATERIAL_MAX_PX + WALL_LATTICE_PITCH_TOL_PX
    touch = WALL_STAIR_TOUCH_PX

    def _unit(f):
        L = _line_length(f.p1, f.p2)
        return (f.p2[0] - f.p1[0]) / L, (f.p2[1] - f.p1[1]) / L

    def _cross(f, g):
        """Where segment g meets segment f: (t_f, t_g) params or None."""
        x1, y1 = f.p1; x2, y2 = f.p2
        x3, y3 = g.p1; x4, y4 = g.p2
        d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
        if abs(d) < 1e-9:
            return None
        t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
        u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
        return t, u

    def _proper_crossing(f, g):
        """g passes through f's interior, both overshooting the meeting point."""
        r = _cross(f, g)
        if r is None:
            return False
        t, u = r
        Lf, Lg = _line_length(f.p1, f.p2), _line_length(g.p1, g.p2)
        m = WALL_STAIR_CROSS_MARGIN_PX
        return (
            m <= t * Lf <= Lf - m and m <= u * Lg <= Lg - m
        )

    def _end_on(f, g):
        """An endpoint of f lies on g: a tread clipped by the section cut,
        or landing on the nosing edge — NOT a hatch stroke, whose own
        endpoints lie on the faces it hatches between."""
        return (
            _point_to_segment_distance(f.p1, g.p1, g.p2) <= touch
            or _point_to_segment_distance(f.p2, g.p1, g.p2) <= touch
        )

    def _touches(f, g):
        """Any endpoint contact between f and g."""
        return (
            _end_on(f, g)
            or _point_to_segment_distance(g.p1, f.p1, f.p2) <= touch
            or _point_to_segment_distance(g.p2, f.p1, f.p2) <= touch
        )

    def _fbox(f):
        return (
            min(f.p1[0], f.p2[0]), min(f.p1[1], f.p2[1]),
            max(f.p1[0], f.p2[0]), max(f.p1[1], f.p2[1]),
        )

    def _inside(f, zone):
        b = _fbox(f)
        return (
            b[0] >= zone[0] - touch and b[1] >= zone[1] - touch
            and b[2] <= zone[2] + touch and b[3] <= zone[3] + touch
        )

    def _union(a, b):
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))

    def _parallel(f, g):
        return _angle_diff_mod180(
            _line_angle_deg(f.p1, f.p2), _line_angle_deg(g.p1, g.p2)
        ) <= WALL_PARALLEL_ANGLE_TOL

    def _paired_with(f, g):
        """g lies parallel to f at wall spacing over a pairing-length overlap."""
        if not _parallel(f, g):
            return False
        off = _perpendicular_spacing(f.p1, f.p2, g.p1, g.p2)
        if not (gates.WALL_MIN_THICKNESS_PX <= off <= gates.WALL_MAX_THICKNESS_PX + 1.0):
            return False
        ux, uy = _unit(f)
        a = _projected_interval(f.p1, f.p2, ux, uy, f.p1)
        b = _projected_interval(g.p1, g.p2, ux, uy, f.p1)
        return max(0.0, min(a[1], b[1]) - max(a[0], b[0])) >= gates.WALL_PAIR_MIN_OVERLAP_PX

    members: set[int] = set()          # face indices (into `faces`)
    zones: list[tuple] = []

    provisional: set[int] = set()      # transverse candidates awaiting the test

    def _anchored(i, f):
        """A non-member face pairs with f at wall spacing: f is (or shadows)
        a wall face, wherever it lies. Two real wall faces inside a stair
        zone anchor each other; stair ink pairs only with stair ink."""
        for j, g in enumerate(faces):
            if j == i or j in members or j in provisional:
                continue
            if _paired_with(f, g):
                return True
        return False

    # --- 1. tread runs -----------------------------------------------------
    # Hatch is excluded from tread candidacy by shape: a short OBLIQUE
    # stroke (s20's cross-hatch: 20-43px strokes at 15/135deg, 12-18px
    # pitch, each family crossing the other — a "flight" by every other
    # measure). Treads are drawn square to the flight, i.e. axis-aligned on
    # an orthogonal plan; a short tread on a rotated plan is the price.
    def _short_oblique(f):
        return (
            _line_length(f.p1, f.p2) <= gates.WALL_HATCH_MAX_LEN_PX
            and 8.0 <= (_line_angle_deg(f.p1, f.p2) % 90.0) <= 82.0
        )

    by_pen: dict[tuple, list[tuple[int, _Seg]]] = {}
    for i, f in cand:
        if _short_oblique(f):
            continue
        by_pen.setdefault(
            (f.pen, int(round(f.stroke_width / WALL_LATTICE_PEN_TOL))), []
        ).append((i, f))
    runs: list[tuple[list[int], list[int]]] = []   # (tread idx, transverse idx)
    for pen_members in by_pen.values():
        if len(pen_members) < WALL_STAIR_MIN_TREADS:
            continue
        angled = sorted(
            (_line_angle_deg(f.p1, f.p2), i, f) for i, f in pen_members
        )
        clusters: list[list[tuple[float, int, _Seg]]] = []
        for entry in angled:
            if clusters and entry[0] - clusters[-1][-1][0] <= WALL_PARALLEL_ANGLE_TOL:
                clusters[-1].append(entry)
            else:
                clusters.append([entry])
        if (
            len(clusters) > 1
            and (angled[0][0] + 180.0) - angled[-1][0] <= WALL_PARALLEL_ANGLE_TOL
        ):
            clusters[0].extend(clusters.pop())
        for cluster in clusters:
            if len(cluster) < WALL_STAIR_MIN_TREADS:
                continue
            _, _, ref = max(cluster, key=lambda t: _line_length(t[2].p1, t[2].p2))
            ux, uy = _unit(ref)
            nx, ny = -uy, ux
            rows = []
            for _, i, f in cluster:
                mx = (f.p1[0] + f.p2[0]) / 2.0
                my = (f.p1[1] + f.p2[1]) / 2.0
                rows.append((
                    mx * nx + my * ny,
                    _projected_interval(f.p1, f.p2, ux, uy, (0.0, 0.0)),
                    i, f,
                ))
            rows.sort(key=lambda r: r[0])
            # Rungs: collinear pieces at one offset with overlapping extents
            # are one tread drawn in pieces; pieces at one offset with
            # DISJOINT extents are different lines that happen to align
            # (a wall face far along the page) and stay separate rungs.
            rungs: list[dict] = []
            for off, (lo, hi), i, f in rows:
                merged_into = None
                for r in reversed(rungs):
                    if off - r["off"] > WALL_LATTICE_OFFSET_TOL_PX:
                        break
                    if min(hi, r["hi"]) - max(lo, r["lo"]) >= -touch:
                        merged_into = r
                        break
                if merged_into is not None:
                    merged_into["members"].append(i)
                    merged_into["ivals"].append((i, lo, hi))
                    merged_into["lo"] = min(merged_into["lo"], lo)
                    merged_into["hi"] = max(merged_into["hi"], hi)
                else:
                    rungs.append({
                        "off": off, "lo": lo, "hi": hi,
                        "members": [i], "ivals": [(i, lo, hi)],
                    })
            # Chain rungs at tread pitch with overlapping extents. Every
            # open chain is a candidate predecessor (rungs at one offset with
            # disjoint extents each carry their own chain), so an unrelated
            # collinear piece cannot break a flight's run.
            chains: list[list[dict]] = []
            open_chains: list[list[dict]] = []
            for r in rungs:
                open_chains = [
                    c for c in open_chains if r["off"] - c[-1]["off"] <= max_pitch
                ]
                for c in open_chains:
                    prev = c[-1]
                    d = r["off"] - prev["off"]
                    ov = min(r["hi"], prev["hi"]) - max(r["lo"], prev["lo"])
                    span = min(r["hi"] - r["lo"], prev["hi"] - prev["lo"])
                    if (
                        WALL_STAIR_MIN_PITCH_PX <= d <= max_pitch
                        and ov >= WALL_STAIR_MIN_LEN_FRAC * span
                    ):
                        c.append(r)
                        break
                else:
                    c = [r]
                    chains.append(c)
                    open_chains.append(c)
            for chain in chains:
                if len(chain) < WALL_STAIR_MIN_TREADS:
                    continue
                # Reference tread: the median-length rung — never the long
                # wall face the flight abuts (its extent overshoots).
                by_len = sorted(chain, key=lambda r: r["hi"] - r["lo"])
                ref_row = by_len[len(by_len) // 2]
                rlo, rhi = ref_row["lo"], ref_row["hi"]
                rlen = rhi - rlo
                # Members qualify on their OWN interval, never the fused
                # rung envelope: a same-pen piece abutting a tread end-to-
                # end on the same axis (a window-frame edge, a skirting, a
                # wall face) fuses into the rung and used to push its
                # envelope past the end tolerance, so the TREAD dropped out
                # of the run and stayed a strong face fencing the flight
                # (s03 FF: tread 1132, 48.5px, plus a 17.7px frame edge =
                # 66px against 51px siblings). Now the in-extent members
                # are the tread and the overshooting piece stays strong on
                # its own merits. Length is the UNION of the in-extent
                # members, so a tread split by a text mask into fragments
                # each under half the reference still qualifies.
                tread_rungs = []
                for r in chain:
                    inside = [
                        (i, lo, hi) for i, lo, hi in r["ivals"]
                        if lo >= rlo - WALL_STAIR_END_TOL_PX
                        and hi <= rhi + WALL_STAIR_END_TOL_PX
                    ]
                    if not inside:
                        continue
                    covered, cur_lo, cur_hi = 0.0, None, None
                    for _, lo, hi in sorted(inside, key=lambda t: t[1]):
                        if cur_hi is None or lo > cur_hi:
                            if cur_hi is not None:
                                covered += cur_hi - cur_lo
                            cur_lo, cur_hi = lo, hi
                        else:
                            cur_hi = max(cur_hi, hi)
                    covered += cur_hi - cur_lo
                    if covered < WALL_STAIR_MIN_LEN_FRAC * rlen:
                        continue
                    tread_rungs.append({
                        "off": r["off"],
                        "lo": min(lo for _, lo, _ in inside),
                        "hi": max(hi for _, _, hi in inside),
                        "members": [i for i, _, _ in inside],
                        "ivals": inside,
                    })
                if len(tread_rungs) < WALL_STAIR_MIN_TREADS:
                    continue
                # Consistent pitch: split the chain wherever a gap strays
                # from the median pitch (a jamb line one wall-width past the
                # last tread chains on but is not a riser), keep the
                # sub-runs of MIN_TREADS or more.
                pitches = [
                    b["off"] - a["off"] for a, b in zip(tread_rungs, tread_rungs[1:])
                ]
                med = sorted(pitches)[len(pitches) // 2]
                tol = max(WALL_LATTICE_PITCH_TOL_PX, WALL_STAIR_PITCH_TOL_FRAC * med)
                sub_runs: list[list[dict]] = [[tread_rungs[0]]]
                for r, pitch in zip(tread_rungs[1:], pitches):
                    if abs(pitch - med) <= tol:
                        sub_runs[-1].append(r)
                    else:
                        sub_runs.append([r])
                sub_runs = [sr for sr in sub_runs if len(sr) >= WALL_STAIR_MIN_TREADS]
                if not sub_runs:
                    continue
                tread_rungs = max(sub_runs, key=len)
                offs = [r["off"] for r in tread_rungs]
                # A flight is at most WALL_STAIR_MAX_ASPECT goings wide; a
                # wall drawn as several parallel lines at leaf pitch runs
                # 15-20x its pitch (s17: 238px lines at 11.7px).
                if rlen > WALL_STAIR_MAX_ASPECT * med:
                    continue
                tread_idx = [i for r in tread_rungs for i in r["members"]]
                tread_faces = [faces[i] for i in tread_idx]
                zone = _fbox(tread_faces[0])
                for f in tread_faces[1:]:
                    zone = _union(zone, _fbox(f))
                # Transverse lines live at the flight's own scale: the cut
                # clips the last treads and runs on past them, the nosing
                # edge follows it — allow one flight depth (never less than
                # a wall band) beyond the treads.
                margin = max(gates.WALL_MAX_THICKNESS_PX, offs[-1] - offs[0])
                wide = (zone[0] - margin, zone[1] - margin, zone[2] + margin, zone[3] + margin)
                # Evidence that the run is a flight and not a cavity wall:
                # a transverse line properly CROSSING a tread's interior
                # (the direction arrow), or an OBLIQUE one that >= 2 treads
                # END on (the section cut clips the treads it passes; a
                # wall's perpendicular end cap closes its faces' ends too,
                # but never obliquely, and a hatch stroke's own ends lie on
                # the faces, not the faces' ends on it). Perpendicular
                # touching lines (nosing edge, stringer) are stair ink once
                # the evidence is in, never evidence themselves.
                transverse: list[int] = []
                evidence = False
                ref_angle = _line_angle_deg(ref.p1, ref.p2)

                def _clipped_on(f, g):
                    """An endpoint of tread f lies on g strictly inside the
                    reference tread's extent (past the end tolerance)."""
                    for p in (f.p1, f.p2):
                        if _point_to_segment_distance(p, g.p1, g.p2) > touch:
                            continue
                        s = p[0] * ux + p[1] * uy
                        if rlo + WALL_STAIR_END_TOL_PX < s < rhi - WALL_STAIR_END_TOL_PX:
                            return True
                    return False
                for j, g in cand:
                    if j in tread_idx or not _inside(g, wide):
                        continue
                    diff = _angle_diff_mod180(_line_angle_deg(g.p1, g.p2), ref_angle)
                    if diff < WALL_STAIR_TRANSVERSE_ANGLE:
                        continue
                    n_cross = sum(1 for f in tread_faces if _proper_crossing(f, g))
                    n_end = sum(1 for f in tread_faces if _end_on(f, g))
                    n_touch = sum(1 for f in tread_faces if _touches(f, g))
                    oblique = diff <= 90.0 - WALL_STAIR_TRANSVERSE_ANGLE
                    # Evidence must come from the stair's own pen: the
                    # arrow and cut are part of the symbol. An annotation
                    # stroke in another color crossing a wall's lines (s17's
                    # orange "to be removed" ticks over a 5-line cavity
                    # wall) is not a stair arrow.
                    same_pen = g.pen == ref.pen
                    # A cut that clips only ONE tread (s03 1:50 plan: the
                    # zigzag break line enters the flight beside the first
                    # tread and leaves at the wall, so only that tread
                    # stops on it, 61.5px against 97px siblings) still
                    # reads as a cut when the tread stops in the INTERIOR
                    # of the flight on a long oblique line: a wall face
                    # stops at a perpendicular jamb cap, and a hatch stroke
                    # meets a face's end only at the band's corner — i.e.
                    # at the run's extent, never inside it. Long: a hatch
                    # stroke is capped at WALL_HATCH_MAX_LEN_PX.
                    clipped = (
                        oblique
                        and _line_length(g.p1, g.p2) > gates.WALL_HATCH_MAX_LEN_PX
                        and any(_clipped_on(f, g) for f in tread_faces)
                    )
                    if same_pen and (
                        n_cross >= 1 or (oblique and n_end >= 2) or clipped
                    ):
                        evidence = True
                        transverse.append(j)
                    elif n_touch >= 2 or n_cross >= 1:
                        transverse.append(j)
                if not evidence:
                    continue
                # Cross-hatch: the crossing family is itself a parallel
                # equal-pitch set. A stair is crossed by one arrow and one
                # cut, never by three parallel lines.
                cross_angles = [
                    _line_angle_deg(faces[j].p1, faces[j].p2)
                    for j in transverse
                    if any(_proper_crossing(f, faces[j]) for f in tread_faces)
                ]
                if any(
                    sum(
                        1 for b in cross_angles
                        if _angle_diff_mod180(a, b) <= WALL_PARALLEL_ANGLE_TOL
                    ) >= 3
                    for a in cross_angles
                ):
                    continue
                # End cuts: the section cut (or landing/nosing edge) that
                # lies just OUTSIDE the first or last tread — within one
                # pitch — touches nothing and crosses nothing, yet bounds
                # the flight (s17: shallow zigzag cuts one pitch above the
                # first and below the last tread fenced the flight into its
                # own "room"). A same-pen chain of end-to-end pieces inside
                # the flight zone whose near edge sits within a pitch of a
                # run end and which spans the flight width is stair ink.
                lo_end, hi_end = offs[0], offs[-1]
                reach = med + tol
                for j, g in cand:
                    if j in tread_idx or j in transverse or not _inside(g, wide):
                        continue
                    if g.pen != ref.pen or _parallel(g, ref):
                        continue
                    chain = [j]
                    ends = [g.p1, g.p2]
                    for _ in range(8):
                        grown = False
                        for k, h in cand:
                            if (
                                k in chain or k in tread_idx or h.pen != ref.pen
                                or not _inside(h, wide) or _parallel(h, ref)
                            ):
                                continue
                            if any(_distance(e, q) <= touch for e in ends for q in (h.p1, h.p2)):
                                chain.append(k)
                                ends = [h.p1, h.p2] + ends
                                grown = True
                        if not grown:
                            break
                    pts = [faces[k].p1 for k in chain] + [faces[k].p2 for k in chain]
                    span_lo = min(px * ux + py * uy for px, py in pts)
                    span_hi = max(px * ux + py * uy for px, py in pts)
                    if min(span_hi, rhi) - max(span_lo, rlo) < WALL_STAIR_MIN_LEN_FRAC * rlen:
                        continue
                    off_lo = min(px * nx + py * ny for px, py in pts)
                    off_hi = max(px * nx + py * ny for px, py in pts)
                    near_low = off_lo <= lo_end + touch and off_hi >= lo_end - reach
                    near_high = off_hi >= hi_end - touch and off_lo <= hi_end + reach
                    if near_low or near_high:
                        transverse.extend(k for k in chain if k not in transverse)
                runs.append((tread_idx, transverse))

    for tread_idx, transverse in runs:
        members.update(tread_idx)
        provisional.update(transverse)
    # Transverse lines are stair ink unless a wall face outside the flight
    # pairs with them (a short partition stub alongside the flight). The
    # arrow and the nosing edge of one flight are parallel at wall spacing;
    # neither anchors the other.
    cuts: set[int] = set()             # oblique transverse members (the cuts)
    for tread_idx, transverse in runs:
        zone = None
        for i in tread_idx:
            zone = _fbox(faces[i]) if zone is None else _union(zone, _fbox(faces[i]))
        for j in transverse:
            if not _anchored(j, faces[j]):
                members.add(j)
                zone = _union(zone, _fbox(faces[j]))
                if 8.0 <= (_line_angle_deg(faces[j].p1, faces[j].p2) % 90.0) <= 82.0:
                    cuts.add(j)
        zones.append(zone)

    # --- 2. stair arrows -----------------------------------------------------
    stair_texts = []
    for t in text_spans:
        tokens = {tok.strip(".,:;()").upper() for tok in (t.text or "").split()}
        if tokens & WALL_STAIR_TEXT_TOKENS:
            stair_texts.append(t.bbox)
    if stair_texts:
        heads = [r for r in rings if r.is_marker()]
        cand_idx = [i for i, _ in cand]
        for head in heads:
            hb = head.poly.bounds
            hbox = (hb[0] - touch, hb[1] - touch, hb[2] + touch, hb[3] + touch)
            starts = [
                i for i in cand_idx
                if _point_in_bbox(faces[i].p1, hbox) or _point_in_bbox(faces[i].p2, hbox)
            ]
            for start in starts:
                chain = [start]
                f = faces[start]
                # Walk away from the head along end-to-end connected faces.
                tail = f.p2 if _point_in_bbox(f.p1, hbox) else f.p1
                for _ in range(6):
                    nxt = [
                        j for j in cand_idx
                        if j not in chain and j not in members
                        and (_distance(faces[j].p1, tail) <= touch
                             or _distance(faces[j].p2, tail) <= touch)
                    ]
                    if len(nxt) != 1:
                        break
                    j = nxt[0]
                    chain.append(j)
                    g = faces[j]
                    tail = g.p2 if _distance(g.p1, tail) <= touch else g.p1
                near_text = any(
                    min(
                        _segments_min_distance(
                            faces[i].p1, faces[i].p2, (tb[0], tb[1]), (tb[2], tb[1])
                        ),
                        _segments_min_distance(
                            faces[i].p1, faces[i].p2, (tb[0], tb[3]), (tb[2], tb[3])
                        ),
                        _segments_min_distance(
                            faces[i].p1, faces[i].p2, (tb[0], tb[1]), (tb[0], tb[3])
                        ),
                        _segments_min_distance(
                            faces[i].p1, faces[i].p2, (tb[2], tb[1]), (tb[2], tb[3])
                        ),
                    ) <= WALL_STAIR_TEXT_NEAR_PX
                    or (_point_in_bbox(faces[i].p1, tb) or _point_in_bbox(faces[i].p2, tb))
                    for i in chain for tb in stair_texts
                )
                if not near_text:
                    continue
                zone = (hb[0], hb[1], hb[2], hb[3])
                for i in chain:
                    members.add(i)
                    zone = _union(zone, _fbox(faces[i]))
                for j in cand_idx:
                    if j in chain:
                        continue
                    if any(_proper_crossing(faces[j], faces[i]) for i in chain):
                        members.add(j)
                        zone = _union(zone, _fbox(faces[j]))
                zones.append(zone)

    # --- 3. winder fans ------------------------------------------------------
    diag = [
        (i, f) for i, f in cand
        if _line_length(f.p1, f.p2) > gates.WALL_HATCH_MAX_LEN_PX
        and 8.0 <= (_line_angle_deg(f.p1, f.p2) % 90.0) <= 82.0
    ]
    if len(diag) >= 2:
        for a in range(len(diag)):
            i, f = diag[a]
            for b in range(a + 1, len(diag)):
                j, g = diag[b]
                shared = None
                for pf in (f.p1, f.p2):
                    for pg in (g.p1, g.p2):
                        if _distance(pf, pg) <= touch:
                            shared = pf
                if shared is None:
                    continue
                if _angle_diff_mod180(
                    _line_angle_deg(f.p1, f.p2), _line_angle_deg(g.p1, g.p2)
                ) < WALL_STAIR_FAN_MIN_ANGLE:
                    continue
                # A bay wall's angled face has its pair partner; winders do not.
                if any(_paired_with(f, h) for k, h in enumerate(faces) if k != i) \
                        or any(_paired_with(g, h) for k, h in enumerate(faces) if k != j):
                    continue
                members.update((i, j))
                zones.append(_union(_fbox(f), _fbox(g)))

    if not members:
        return faces, []

    # Merge touching zones (arrow zone + winder box + flight).
    merged_zones: list[tuple] = []
    for z in zones:
        z_cur = z
        changed = True
        while changed:
            changed = False
            for k, m in enumerate(merged_zones):
                if _bboxes_overlap(_bbox_expanded(z_cur, touch), m):
                    z_cur = _union(z_cur, merged_zones.pop(k))
                    changed = True
                    break
        merged_zones.append(z_cur)

    # Zone extras: stair ink inside the flight that no recognizer named —
    # the collinear end-to-end continuation of a crossed stringer, the
    # balustrade line pairing with it, landing edges, cut treads. A face
    # joins when it lies in a zone and its only wall-spacing partners are
    # stair ink (or it has none); iterate to a fixpoint, since a stringer's
    # continuation must join before the line pairing with it can. A real
    # wall pair inside the zone anchors itself and stays.
    def _continues(f, g):
        """g continues f end-to-end on the same line."""
        if not _parallel(f, g):
            return False
        if _perpendicular_spacing(f.p1, f.p2, g.p1, g.p2) > touch:
            return False
        return any(
            _distance(a, b) <= touch for a in (f.p1, f.p2) for b in (g.p1, g.p2)
        )

    def _continues_cut(c, f):
        """f is the far half of a BREAK LINE whose near half c is a cut:
        same line (parallel, within touch perpendicular), nearest ends
        within the zigzag jog. The jog itself is drawn as pieces under
        the face floor, so the halves never touch (s03 1:50: halves
        58.6/58.9px on one line, 0.12px offset, 11.6px apart across an
        8.6/17/8.7px zigzag; the far half lay outside the flight bbox and
        notched the merged room as a strong lone face)."""
        if c.pen != f.pen or not _parallel(c, f):
            return False
        if _perpendicular_spacing(c.p1, c.p2, f.p1, f.p2) > touch:
            return False
        return any(
            _distance(a, b) <= WALL_STAIR_BREAK_GAP_PX
            for a in (c.p1, c.p2) for b in (f.p1, f.p2)
        )

    provisional.clear()
    changed = True
    while changed:
        changed = False
        for i, f in cand:
            if i in members:
                continue
            if any(_continues_cut(faces[c], f) for c in cuts) and not _anchored(i, f):
                members.add(i)
                cuts.add(i)
                merged_zones = [_union(z, _fbox(f)) if _bboxes_overlap(
                    _bbox_expanded(_fbox(f), WALL_STAIR_BREAK_GAP_PX), z) else z
                    for z in merged_zones]
                changed = True
                continue
            if not any(_inside(f, z) for z in merged_zones):
                continue
            if any(_continues(faces[m], f) for m in members) or not _anchored(i, f):
                members.add(i)
                changed = True

    kept = [f for i, f in enumerate(faces) if i not in members]
    demoted = [f for i, f in enumerate(faces) if i in members]
    return kept, demoted


def detect_wall_network(
    paths: list[PathPrimitive], text_spans: list[TextSpan] | None = None,
    exclude_path_indices: set[int] | None = None,
    scale_factor: float = 1.0,
) -> WallNetwork:
    """Build the internal wall-centerline network for a page.

    exclude_path_indices — linework that must never become a wall face:
    the open leaves of detected swing doors (door symbol ink in the wall
    pen, standing parallel to real walls — pairing them inflates the wall
    band across the swing side; see door_open_leaf_path_indices).

    scale_factor — 50 / nominal_denominator (1:100 -> 0.5), pre-multiplies
    the world-space gates (WallGates) so a page's own drawn scale is
    honored instead of assuming every sheet is 1:50. Identity at 1.0.
    """
    gates = WallGates.at(scale_factor)
    # Dimension-chain lines (oblique end ticks on both endpoints) are
    # annotation in wall-strength pens — excluded from face collection
    # entirely, alongside the door open-leaf ink.
    # So is anything drawn on an annotation-named layer (section callouts,
    # dimension/text layers): vetoed BEFORE pairing, never in
    # _is_barrier_face alone, because a paired callout would still create
    # segments, enter the stroke reference and launder its partner into
    # wall evidence (s04's page-wide 1.19px section callout).
    # Stick-font text (s06/s11/s16/s20 draw every label as glyph strokes in
    # the wall pen, no text span) is vetoed the same way: freestanding
    # glyph rows are never wall ink (_vector_text_indices).
    # And so are FILL SEAMS — the shared edges of triangulated / abutting
    # same-fill pieces, fill on both sides (_fill_seams). No pen ever shows
    # such an edge, yet the exporter attaches the fill's own colour to it
    # as a width-0 stroke, which the extractor records at 1.0px
    # (ZERO_WIDTH_STROKE_PX); vetoing the seam's wall_fill flag alone
    # (marker_indices below) left it a STROKED face — a "chord" across the
    # band within WALL_PARALLEL_ANGLE_TOL of both faces that pairs with the
    # next cell's face and merges collinearly into a run (measured
    # 2026-09-02: s03 248, s04 50/50, s08 48/48, s12 116, s17 128 seams
    # were stroked faces; s01 has no fill rings and s02's 48 seams are
    # fill-only, so the reference sheets carry no such face).
    rings = _collect_fill_rings(paths)
    seam_indices, seam_adjacency = _fill_seams(rings, paths)
    excluded = frozenset(exclude_path_indices or ()) | frozenset(
        _dimension_line_indices(paths, gates=gates)
    ) | frozenset(_vector_text_indices(paths)) | frozenset(
        p.path_index for p in paths if _layer_annotation_veto(p.layer)
    ) | frozenset(seam_indices)
    fill_is_wall = _rate_fill_classes(rings, gates=gates)
    # Marker rings (arrowheads) share the wall pen but are never outline:
    # their edges may not qualify as wall-fill faces. Seams ride in the
    # same set for the standalone _collect_wall_faces path; here they are
    # already excluded outright above.
    marker_indices = {
        i for r in rings if r.is_marker() for i in r.indices
    } | seam_indices
    faces, bands = _collect_wall_faces(
        paths, fill_is_wall, marker_indices, excluded, gates=gates
    )
    # Stair symbols (tread runs crossed by a cut/arrow, UP/DN arrows and
    # the lines they cross, winder fans, and the flight-zone ink around
    # them) are furniture in the wall pen: demoted to the weak pipeline
    # BEFORE the collinear merge, at path granularity, so a landing edge
    # collinear with a wall nib's face cannot take the nib down with it.
    faces, stair_faces = _demote_stair_faces(
        faces, rings, text_spans or [], gates=gates
    )
    for f in stair_faces:
        f.stroked = False
        f.stroke_width = 0.0
    merged_faces = _merge_collinear_segs(
        faces, gap_px=WALL_FACE_MERGE_GAP_PX, gates=gates
    )

    # Striped fields (paving bonds, tile fields, stair treads, roof tiling,
    # table rows): >= 5 parallel same-pen faces at equal wall-like pitch are
    # a drawn surface pattern, not wall structure, whatever their pen weight
    # — the vestibule paving bond on 5-1133 is penned ABOVE the relative
    # gate below and paired into phantom 31px wall bands chopping the open
    # vestibule into phantom rooms. Demote members to the material-gated
    # weak pipeline before the pairing statistics, so a large field cannot
    # skew the paired-pen stroke reference either.
    merged_faces, lattice_faces = _demote_lattice_faces(merged_faces, gates=gates)
    for f in lattice_faces:
        f.stroked = False
        f.stroke_width = 0.0

    # Faint-ink pens (light grey overhead/reference lines: RSJ beams, VELUX
    # rooflight boxes — drawn in the wall pen WIDTHS on color-coded
    # drawings) are demoted to the material-gated weak pipeline like
    # sub-gate pen widths: a grey double line spanning a room pairs into a
    # phantom partition otherwise, and no width statistic can catch it.
    # Demoting before the interim pairing keeps faint pens out of the
    # stroke reference too.
    light_faces: list[_Seg] = []
    kept_dark: list[_Seg] = []
    for f in merged_faces:
        if (
            f.stroked and not f.wall_fill and not f.layer_hint
            and _is_light_pen(f.pen)
        ):
            f.stroked = False
            f.stroke_width = 0.0
            light_faces.append(f)
        else:
            kept_dark.append(f)
    merged_faces = kept_dark

    # Relative pen gate: the absolute stroke floor admits light-pen linework
    # (floor-tile grids at half the wall pen) as full wall faces, and any such
    # line running parallel to a real wall face at wall-like spacing pairs
    # into a phantom wall band across the room interior. Anchor the strong/
    # weak boundary to the pens that actually drew the walls: pair the strong
    # faces once, take the length-weighted median stroke of the paired ones,
    # and demote faces penned below WALL_WEAK_STROKE_RATIO of it to weak —
    # their pairs then need drawn material between the faces, exactly like
    # the hairline joinery pen. Fill outlines and layer-hinted faces carry
    # their own evidence and are never demoted.
    interim_paired: set[int] = set()
    for c in _pair_faces_to_centerlines(merged_faces, gates=gates):
        interim_paired |= c.indices
    entries = sorted(
        (f.stroke_width, _line_length(f.p1, f.p2))
        for f in merged_faces
        if f.stroked and f.stroke_width > 0 and f.indices & interim_paired
    )
    total = sum(length for _, length in entries)
    stroke_ref = 0.0
    acc = 0.0
    for width, length in entries:
        acc += length
        if acc >= total / 2.0:
            stroke_ref = width
            break
    demoted: list[_Seg] = []
    if stroke_ref > 0.0:
        gate = WALL_WEAK_STROKE_RATIO * stroke_ref
        kept_strong: list[_Seg] = []
        for f in merged_faces:
            if (
                f.stroked and not f.wall_fill and not f.layer_hint
                and f.stroke_width < gate
            ):
                f.stroked = False
                f.stroke_width = 0.0
                demoted.append(f)
            else:
                kept_strong.append(f)
        merged_faces = kept_strong

    # Sub-threshold (joinery-pen) partition walls: pair hairline faces too,
    # but keep a weak-involved pair only when the band between the faces
    # carries drawn wall material (hatch / cross-hatch / blocking X's). The
    # gate runs on the raw pairs, before centerline merging, so a weak pair
    # can never ride in on a strong run's coattails.
    weak_merged = _merge_collinear_segs(
        _collect_weak_faces(paths, excluded, gates=gates)
        + _collect_stroked_rect_weak_faces(paths, excluded, gates=gates),
        gap_px=WALL_FACE_MERGE_GAP_PX, gates=gates,
    ) + demoted + lattice_faces + light_faces + _merge_collinear_segs(
        stair_faces, gap_px=WALL_FACE_MERGE_GAP_PX, gates=gates
    )
    for f in weak_merged:
        f.weak = True

    marks = _collect_material_marks(paths, gates=gates)
    # Through-hatch strokes span the band's diagonal, past the ordinary
    # hatch length cap; collected separately so the ordinary material gates
    # keep their tuned mark population.
    through_marks = _collect_material_marks(
        paths, gates=gates,
        max_len=gates.WALL_THROUGH_HATCH_MAX_PX * math.sqrt(2.0) + 2.0,
    )
    centerlines = _pair_faces_to_centerlines(
        merged_faces + weak_merged, thick_tier=True, gates=gates,
    )
    if any(c.weak or c.thick for c in centerlines):
        # Weak pairs (sub-threshold pens) and thick pairs (pier-tier spacing
        # beyond WALL_MAX_THICKNESS_PX) survive only on drawn wall material
        # between the faces — otherwise a hairline fixture outline, or a
        # face beside a corridor of pier-like width, becomes a wall band.
        centerlines = [
            c for c in centerlines
            if not (c.weak or c.thick) or (
                _line_length(c.p1, c.p2) >= gates.WALL_WEAK_MIN_RUN_PX
                and (
                    _band_has_through_hatch(c, through_marks, gates=gates)
                    if c.through else
                    _band_has_wall_material(c, marks, gates=gates)
                )
            )
        ]
        # Second pass over the material-kept pairs: an over-wide weak pair
        # whose band encloses a kept tighter pair over the same span passed
        # the material gate on that inner wall's own hatch/blocking (a tile
        # line paired with a real divider's far face) — drop it, so neither
        # its centerline nor its outer face reaches the network. Thick pairs
        # get the same treatment: a face 40px off a real wall would pass on
        # that wall's own hatch.
        material_kept = centerlines
        centerlines = [
            c for c in material_kept
            if not (c.weak or c.thick)
            or not _claims_interior_pair(c, material_kept)
        ]
    # A strong pair can also be a wall face paired across the ROOM: the
    # partner is furniture/joinery drawn in the wall pen (counter fronts,
    # wardrobe fronts) or a facing wall across a narrow corridor, at
    # wall-like spacing. The tighter kept pair on the far side of the shared
    # face is the wall; a material-less band on this side is free space.
    fill_union = unary_union([
        r.poly for r in rings
        if fill_is_wall.get(r.key, False) and not r.is_marker()
    ]) if rings else None
    # Filled bands count as kept pairs here: a fill ring's outline face
    # pairing with a counter front across the room shares its index with
    # the band drawn on the other side of it.
    kept_for_side = centerlines + bands
    far_side_dropped: set[int] = set()
    kept_pairs: list[_Seg] = []
    for c in centerlines:
        if not (c.weak or c.thick) and _claims_far_side_pair(
            c, kept_for_side, fill_union, marks, gates=gates
        ):
            far_side_dropped |= c.indices
        else:
            kept_pairs.append(c)
    centerlines = kept_pairs
    # The partner in a dropped far-side pair — parallel to a wall at
    # wall-like spacing across free space, with nothing else pairing it —
    # is the fixture front itself. Strip its lone-face rights (the rooms
    # stage otherwise keeps it as a thin barrier on pen weight alone and
    # the counter strip still fences off), exactly like a demoted pen.
    if far_side_dropped:
        still_paired: set[int] = set()
        for c in centerlines + bands:
            still_paired |= c.indices
        for f in merged_faces:
            if (
                f.stroked and not f.wall_fill and not f.layer_hint
                and f.indices & far_side_dropped
                and not f.indices & still_paired
            ):
                f.stroked = False
                f.stroke_width = 0.0
    weak_paired: set[int] = set()
    for c in centerlines:
        if c.weak:
            weak_paired |= c.indices

    centerlines += bands
    centerlines = _merge_collinear_segs(
        centerlines, gap_px=WALL_CENTERLINE_MERGE_GAP_PX, gates=gates,
    )
    centerlines = _collapse_redundant_centerlines(centerlines)
    centerlines = [c for c in centerlines if _line_length(c.p1, c.p2) >= 1.0]

    _snap_intersections(centerlines)
    centerlines = [c for c in centerlines if _line_length(c.p1, c.p2) >= 1.0]

    segments = [
        WallSegment(
            p1=c.p1, p2=c.p2,
            thickness_px=round(c.thickness, 2),
            source=c.source if c.source != "face" else "face_pair",
            layer=c.layer,
            layer_hint=c.layer_hint,
            face_path_indices=sorted(c.indices),
            stroked=c.stroked,
        )
        for c in centerlines
    ]

    merged = None
    if len(segments) >= WALL_NETWORK_MIN_SEGMENTS:
        merged = unary_union([LineString([s.p1, s.p2]) for s in segments])

    # Material-backed weak faces join the face list (they ARE the wall's
    # drawn faces — "wall runs through" checks and the rooms' thin barriers
    # need them), but stroked=False / stroke_width=0 keeps them out of
    # wall_stroke_reference: hundreds of hairline members must not drag the
    # relative pen-weight gate down to fixture territory.
    weak_faces_kept = [f for f in weak_merged if f.indices & weak_paired]
    weak_kept_ids = {id(f) for f in weak_faces_kept}
    strong_ids = {id(f) for f in merged_faces}
    face_lines = [
        WallFace(
            p1=f.p1, p2=f.p2, stroked=f.stroked, stroke_width=f.stroke_width,
            wall_fill=f.wall_fill, layer_hint=f.layer_hint,
            indices=frozenset(f.indices),
            # One-sided hatch backing is claimed by STRONG faces only: a
            # demoted (weak/lattice/light-pen) face touching hatch must not
            # ride back in on it.
            material_backed=(
                id(f) in strong_ids
                and f.stroked
                and not f.wall_fill
                and _face_is_material_backed(f, marks, gates=gates)
            ),
            pen=f.pen,
            backed_spans=(
                _face_material_spans(f, marks, gates=gates)
                if id(f) in weak_kept_ids else ()
            ),
        )
        for f in merged_faces + weak_faces_kept + bands
    ]
    # Wall-rated fill rings are wall AREA, not just outlines: the polygons
    # seal band interiors, corner posts and jamb stubs whose sub-minimum
    # edges never became faces. Oversized blobs (shaded zones) stay
    # outline-only; marker rings (arrowheads in the wall pen) are annotation
    # and must not stamp notches into the free space.
    wall_ring_ids = {
        i for i, r in enumerate(rings)
        if fill_is_wall.get(r.key, False)
        and r.short <= gates.WALL_FILL_BLOCK_MAX_SIDE_PX
        and not r.is_marker()
    }
    # Seam-connected rings (the exporter's triangulation of one band) are
    # unioned back into that band so the room stage dilates a rectangle,
    # not two acute triangles (s03: 184/184 wall-fill rings are triangles).
    fill_polygons = []
    for group in _fill_ring_components(len(rings), seam_adjacency, wall_ring_ids):
        merged = unary_union([rings[i].poly for i in group]) if len(group) > 1 else rings[group[0]].poly
        fill_polygons.extend(
            g for g in getattr(merged, "geoms", [merged]) if not g.is_empty
        )

    # Hollow (white) walls and joinery runs are only CANDIDATES here: shape
    # and text content prune the masks, but walls vs cabinet fronts is
    # settled by connectivity to wall material INCLUDING door/window
    # openings — which only room detection has (_accept_white_walls is
    # called from rooms.py, where hollow runs interrupted by windows still
    # anchor on the bboxes).
    white_bands = _white_wall_candidates(rings, text_spans or [], gates=gates)
    stroked_rings = _collect_stroked_rings(paths, excluded, gates=gates)
    return WallNetwork(
        segments=segments, merged=merged, faces=face_lines,
        fill_polygons=fill_polygons, white_bands=white_bands,
        stroked_rings=stroked_rings,
    )
