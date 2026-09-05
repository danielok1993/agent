"""Room detection: rooms are the connected free-space components between walls.

Earlier revisions polygonized the wall-centerline graph directly, which was
fragile on real drawings: every wall run had to pair into a centerline, every
junction had to snap, and a single gap anywhere (thickness jogs, unpaired
party walls, stub jambs) dissolved the whole room loop. This version works
morphologically on the page instead:

1. Barriers: wall solids (centerline segments dilated to their measured
   thickness), thin buffers of ALL merged wall-face linework (this is what
   seals single-line party walls, window glazing runs, and filled-band
   outlines that never pair), and opening seals at the detected doors and
   windows (doors/windows detect first, so they mark the wall gaps). A
   window bbox lies in the wall band and is used as-is; a door bbox covers
   the swing — room floor, not wall — so it is replaced by a thin plug along
   the wall plane (see _door_plug) and the swing area stays inside the room.
2. The barrier union is morphologically closed (+/- ROOM_GAP_CLOSE_PX) to
   seal small residual drafting gaps.
3. Free space = page minus barriers; each connected component is a candidate
   room, filtered by area, page coverage, page-border contact, hole fraction,
   erosion (wall-band slivers), wall-contact ratio (legend tables, dimension
   frames and sheet interiors enclose space but are not wall-bounded), and
   attachment to a major wall mass (a legend box's borders form their own
   tiny "wall" mass, disconnected from the building).

Rooms are emitted as heuristic-only candidates carrying the closed polygon in
evidence.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

from shapely.geometry import LineString, Point, Polygon, box
from shapely.affinity import translate
from shapely.ops import unary_union

from models import BBox, Candidate, TextSpan
from detection.geometry import (
    _angle_diff_mod180, _line_angle_deg, _line_length, _perpendicular_spacing,
)
from detection.walls import (
    WALL_HATCH_MAX_LEN_PX, WALL_MAX_THICKNESS_PX, WALL_MIN_STROKE_WIDTH_PX,
    WALL_PARALLEL_ANGLE_TOL,
    WallGates, WallNetwork,
    _accept_white_walls, _bridge_white_runs, _is_diagonal_hatch_angle,
)

# ---------------------------------------------------------------------------
# Room detection constants
# ---------------------------------------------------------------------------
ROOM_MIN_AREA_PX2           = 2500.0  # 50x50 px — smallest plausible closet at 150 DPI
ROOM_MAX_PAGE_AREA_FRAC     = 0.45    # components bigger than this are the sheet frame
ROOM_HOLE_AREA_FRAC_MAX     = 0.20    # mostly-hole components are frame-minus-building rings
ROOM_WALL_DILATE_PX         = 2.0     # wall-solid dilation; seals sub-4px face cracks
ROOM_LINING_IN_BAND_FRAC    = 0.80    # a stroked ring beside a confident opening is a
                                      # DOOR LINING — wall material — when it is the
                                      # wall band's own continuation: shifted one
                                      # ring-length along the band axis away from the
                                      # opening, at least this fraction of it lands on
                                      # drawn wall material (D). Linings are joinery,
                                      # drawn in the joinery pen (s04: 12.4x14.5px `qu`
                                      # rings in a 0.56px grey pen against a 1.19px
                                      # wall pen, ratio 0.47), so the wall-pen gate the
                                      # jamb-nib rule uses can never admit them; the
                                      # position — sandwiched IN the band between the
                                      # jamb face and the leaf — is the evidence. A
                                      # fixture box hugging a wall's room-side face
                                      # beside a door shifts along the wall onto room
                                      # floor (0 cover); one sandwiched between a door
                                      # and a perpendicular return wall shifts INTO that
                                      # wall but fails the across-span check below.
ROOM_LINING_SPAN_TOL_PX     = 4.0     # slack on the across-band span check: at the
                                      # shifted position the material's span across the
                                      # band axis must not exceed the ring's own depth
                                      # by more than the two 2px dilations plus this
                                      # (P) — the lining fills the band's full depth
                                      # (s04: 14.5px ring in a 14.5px band, dilated
                                      # solid span 18.5 <= 14.5 + 4 + 4), while a
                                      # perpendicular wall the shift lands in spans its
                                      # whole length across the probe.
ROOM_RING_MITRE_LIMIT       = 2.0     # mitre cap for fill-ring dilation (D). Exporters
                                      # triangulate fills, so a wall band arrives as
                                      # two right triangles (s03: 184/184 wall-fill
                                      # rings are triangles; s18: 936/1380 rings
                                      # spike; s02: 7 fill + 15 white rings) and each
                                      # ring is dilated on its own. Shapely's default
                                      # mitre limit (5) lets the join at a 4.8° acute
                                      # vertex run 10px past the ring — a tab in the
                                      # room outline beside every band end and jamb
                                      # nib (s03 corridor room_0014: 8x3.7px tabs at
                                      # 3732,1782). Mitre ratio is 1/sin(θ/2): 1.41 at
                                      # a right angle, 2.0 at 60°, 2.61 at 45°, so
                                      # vertices of 60° and wider keep their sharp
                                      # mitre and anything sharper bevels, overshooting
                                      # by at most the 2px dilation. A thin band's
                                      # triangles split each rectangle corner into
                                      # ~5° + ~85°, so the wide half still mitres the
                                      # band's dilated corner; only a near-square fill
                                      # (45°/45° split) bevels both halves, leaving a
                                      # <=2px corner chamfer. This CAPS the spike;
                                      # walls._fill_ring_components unions seam-sharing
                                      # rings back into their band first, so a band
                                      # dilates as a rectangle and only unshared
                                      # slivers (s18) still reach the bevel.
ROOM_LINE_BARRIER_PX        = 2.0     # half-width of thin line barriers — kept EQUAL
                                      # to ROOM_WALL_DILATE_PX so a face's thin
                                      # buffer and its pair's dilated solid put the
                                      # room boundary at the same standoff from the
                                      # drawn face; a 0.5px mismatch leaves corner
                                      # notches where the two barrier tiers meet,
                                      # and polygon simplification redraws an 83px
                                      # straight pier face as a slow diagonal
                                      # (measured on floor-plans room_0012)
ROOM_BARRIER_STROKE_RATIO   = 0.75    # a lone stroked face becomes a thin barrier only
                                      # at >= this fraction of the paired-wall stroke
                                      # reference — tile grids, furniture outlines and
                                      # symbols are penned lighter than the walls.
                                      # Random-size patio paving joints evade the
                                      # equal-pitch lattice demotion and measure 0.70
                                      # (1.05 vs 1.50 on 5-1133 — they fenced patio
                                      # cells against exterior door plugs into phantom
                                      # door-bearing "rooms"); every real lone barrier
                                      # face on both reference PDFs measures >= 1.00,
                                      # so the gate sits just above the noise band to
                                      # keep headroom for lightly-penned real walls
                                      # (paired pens go down to 0.67 in the sample set)
ROOM_PAIRED_FACE_MIN_FRAC   = 0.5     # a STROKED face penned under the barrier gate
                                      # rides on its pairing alone, and pairing is
                                      # recorded per path index: one 22px sliver that
                                      # paired (two paving joints 14px apart) qualified
                                      # a 230px tile line full-length and fenced patio
                                      # cells against the bay wall (5-1133). Where a
                                      # face truly paired, its SEGMENTS already seal as
                                      # solids, so full-length qualification must be
                                      # earned: segments covering >= this fraction of
                                      # the face run. Noise measures <= 0.36, real
                                      # sub-gate paired faces >= 0.71 (both PDFs).
                                      # UNSTROKED paired faces short of it are CLIPPED
                                      # rather than dropped (_backed_extent): material-
                                      # backed hairline partitions pair legitimately
                                      # over 0.13-0.36 where openings ate the partner
                                      # face (s02's sliding-door tracks GD5/GD9), and
                                      # keep the run beside hatch or under a confident
                                      # door — but the plain remainder of a merged
                                      # hairline run is joinery (s02's "coats" cupboard
                                      # front: 210px of free-space run between two
                                      # wall skins, no marks, no door) and seals nothing
ROOM_WALL_PEN_MIN_FRAC      = 0.15    # a lone stroked face's pen COLOR must carry
                                      # at least this fraction of the network's
                                      # paired-face length to grant lone-barrier
                                      # rights. On width-coded (monochrome)
                                      # drawings all ink shares one pen and this
                                      # is a no-op; on color-coded drawings the
                                      # pen width carries no signal (floor-plans
                                      # pens furniture red and dimensions blue at
                                      # 1.5 — AT the wall width, above the walls'
                                      # own magenta 1.0) and color is the
                                      # hierarchy: wall pens build most of the
                                      # paired network (black 0.50 / magenta 0.34
                                      # of paired length) while annotation pens
                                      # only pair incidentally (red 0.11, blue
                                      # 0.06 — a red worktop line fenced a 34px
                                      # phantom "room" against the utility's
                                      # south wall, and cabinet fronts fenced the
                                      # kitchen's cabinet strips)
ROOM_PLUG_MID_NEAR_PX       = 3.0     # hug distance for the MID emptiness test of
                                      # the interrupted-run profile — tighter than
                                      # ROOM_PLUG_NEAR_PX because "empty middle"
                                      # means empty IN THE OPENING PLANE: a
                                      # perpendicular wall whose end cap floats a
                                      # few px off the plane is not material in it
                                      # (5-1133-style; measured on floor-plans
                                      # door_0008: the bathroom east wall's top
                                      # cap 6px below the doorway plane read as
                                      # mid coverage 0.33 and the true doorway
                                      # edge qualified for NO plug, merging the
                                      # bedroom with the landing corridor).
                                      # Anchors and the full-coverage total keep
                                      # the 8px hug: jambs legitimately anchor
                                      # from beside the plane
ROOM_GAP_CLOSE_PX           = 8.0     # morphological closing: seals drafting gaps up to
                                      # ~2x this; well below door widths so undetected
                                      # doors keep rooms connected (and thus dropped).
                                      # Applied as an OPENING of each free-space
                                      # component (the complement-side equivalent):
                                      # buffering the barrier union directly has
                                      # silently dropped legitimate room-sized holes
                                      # from the giant multi-hole polygon (GEOS
                                      # robustness), losing whole rooms.
ROOM_EROSION_PX             = 6.0     # components that vanish under this are wall slivers
ROOM_BORDER_TOL_PX          = 2.0     # free space touching the page border is "outside"
ROOM_CONTACT_TOL_PX         = 4.0     # boundary-to-wall distance that counts as contact
ROOM_WALL_CONTACT_MIN       = 0.55    # min fraction of boundary on wall solids/openings
ROOM_MAJOR_MASS_FRAC        = 0.15    # wall mass >= this fraction of the largest counts
                                      # as a building (a page can hold several plans)
ROOM_MASS_TOUCH_TOL_PX      = 4.0     # room must lie this close to a building wall mass
ROOM_SIMPLIFY_TOL_PX        = 2.0     # sub-pen-width polygon simplification
ROOM_OPENING_SEAL_PX        = 15.0    # bbox-edge extension when building door plugs, and
                                      # bbox dilation on the plug fallback: bridges the
                                      # clearance between the swing bbox and the jambs so
                                      # free space cannot leak around a detected door.
                                      # 127mm at 1:50 (W-class; 15 -> 7.5px = 150mm at
                                      # 1:100). The jamb gap beyond a swing bbox at
                                      # true scales: s01 8px = 125mm (1:92.2 — the old
                                      # 12 was set on it as if 1:50, so at f=0.542 the
                                      # 6.5px tail stopped short of the hall door's
                                      # jamb and the hall merged with the living room,
                                      # iteration 3 step 3), s17 8px = 135mm (its 1:100
                                      # plan detected at identity), s05/s07 6px at
                                      # f=0.5 = 102mm — exactly the old scaled 6px
                                      # tail, zero headroom. 12 -> 15 on 2026-09-05
                                      # (iteration 3 step 7) after the two mechanisms
                                      # that broke iteration 2's try were removed at
                                      # 12: s15's dash-row barrier across door_0013's
                                      # doorway plane (step 6, _dash_row_indices) and
                                      # s02's plug tails overshooting the section-marker
                                      # bar (step 5, _clip_plug_tails). Measured on the
                                      # corpus at 15 (harness at 13/14/15 on
                                      # s01-s05/s07/s11/s15-s17, then the full sweep):
                                      # no entity appears, vanishes or is lost, no
                                      # recorded FP returns (s03's two return at 18);
                                      # what moves is outline, in three classes — (a)
                                      # the plug-less dilated-bbox FALLBACK stamps
                                      # SEAL in every direction, so at each such door
                                      # the room on the plane side loses 3px more (s01
                                      # door_0015 -447 px2 on the living room, s04
                                      # door_0003 -539 on each flanking room, s17
                                      # door_0001 -547 on the SH/WC whose confirmed
                                      # outline IS that stamp's edge, s16/s18 by 1.5px
                                      # at f=0.5; about -2.9k px2 over 10 doors — the
                                      # stamp's across-plane growth was pure cost, and
                                      # step 8 plane-restricted it: _plane_stamp);
                                      # (b) a tail on CONTINUING material — a jamb
                                      # running on, or a parallel band within the 5px
                                      # half-width the sample-trim reads as touching
                                      # (s17 door_0016) — is 3px longer, and where the
                                      # plug crosses a room corner it notches 3 x
                                      # half-width more (s17 rooms 0001/0002 -25.5 each,
                                      # s15 room_0007, s02 room_0000 -310); (c)
                                      # sampling-phase knife-edges, both ways: s03
                                      # door_0008's leaf-side interrupted plug (1/6
                                      # -> 2/7 mid cover) drops and room_0009 wraps a
                                      # wall stub as an island (+715), s17 door_0001's
                                      # bottom plug qualifies at 14 only (the SH/WC
                                      # regains its swing square there, +9.0k, and not
                                      # at 15), s01 room_0005's fit flip at 13-14 is
                                      # inert at 15. An interrupted plug seals a jamb
                                      # gap of at most SEAL - 1px
                                      # (tests/test_room_detection.py::TestPlugSealReach).
ROOM_PLUG_JAMB_SEEK_PX      = 29.5    # how far past a swing bbox corner a doorway plug's
                                      # tail may SEEK its jamb when the fixed SEAL reach
                                      # finds none there (W-class: 250mm at 1:50, 16px at
                                      # s01's true 1:92.2, 14.8px at 1:100). A doorway is
                                      # cut out of a wall, so its latch jamb is wall
                                      # material the plug has to reach — but the tail's
                                      # reach is fixed in advance while the jamb's
                                      # distance is drawn, and s01 draws its swing
                                      # symbols short of their openings on the latch
                                      # side (a 671mm leaf in an 847mm opening; the
                                      # corpus census of 378 kept doorway ends at true
                                      # scale, iteration 3 step 9: median 0mm, p90 34,
                                      # then s01's four swings at 187–219mm, s05 135,
                                      # s17 110, s18/s08 102, every other sheet <= 51).
                                      # True class within the cap: s01 door_0002's hall
                                      # doorway at 0.542 (the corner jamb block's right
                                      # face, path 278, perpendicular to the doorway,
                                      # 12.3px = 191mm), s18 door_0018's doorway (a 139px
                                      # 90-degree face at 11px = 186mm, plug-less before).
                                      # False class (material_seek_probe.py, every
                                      # un-anchored hinge-edge end of a >= 0.55 single on
                                      # 18 sheets, 172 ends): exactly one within 300mm —
                                      # s14 door_0007's open-leaf tip reaching a
                                      # wall-fill chevron ring at 35px = 296mm, 1.18x
                                      # over the cap; s01 door_0015's garden-pair piers
                                      # at 18px = 281mm are a pair, never a seeking
                                      # single. Only a HINGE edge of a >= 0.55 single
                                      # whose profile anchors at exactly one end seeks,
                                      # and only the interrupted signature may result.
                                      # As implemented (seek_census.py, every door on
                                      # 18 sheets re-profiled with and without the
                                      # seek): four doors change, every hit a
                                      # perpendicular wall — s01 door_0002 at 0.542
                                      # (149mm to the first touching sample), s14
                                      # door_0008 (76mm, inside the fixed reach but
                                      # its anchor window straddled the corner), s17
                                      # door_0004 (121mm; a 0.95 single drawn CLOSED
                                      # in its doorway, whose confirmed room_0018 had
                                      # wrapped under the leaf into the threshold,
                                      # -1,163 px2) and s18 door_0018 (178mm; rooms
                                      # 0002/0003 +695/+30 px2). Corpus sweep
                                      # verdict-identical, s01/s02 untouched at
                                      # f=1.0, 17 sheets polygon-identical.
ROOM_PLUG_NEAR_PX           = 8.0     # a bbox edge "hugs" wall material within this
                                      # distance; the swing bbox lands on the wall faces
                                      # a few px off at most
ROOM_PLUG_SAMPLE_PX         = 4.0     # coverage-profile sample spacing along an edge
ROOM_PLUG_ANCHOR_WIN_PX     = 24.0    # cap on the end-anchor window: a jamb is
                                      # jamb-sized regardless of doorway width, so
                                      # the anchor evidence must not dilute as the
                                      # edge grows (an n//4 quarter of a 165px garden
                                      # doorway is 48px — a 45-degree bay jamb hugs
                                      # the edge line for only ~20px of it and the
                                      # true wall-plane edge failed the 0.5 gate at
                                      # 0.42 while a perpendicular edge crossing the
                                      # angled wall passed; measured on 5-1133 door
                                      # 0121). Never larger than the legacy quarter,
                                      # so narrow doors are unaffected.
ROOM_PLUG_HALF_WIDTH_PX     = 5.0     # half-thickness of the wall-plane plug band; thin
                                      # enough to stay out of the room, thick enough to
                                      # overlap the wall band it stands in for. Scaled
                                      # (half a wall band is world-space) but floored at
                                      # ROOM_LINE_BARRIER_PX in RoomGates.at: the plug
                                      # must never be thinner than the standoff every
                                      # other barrier keeps (W-gate census 2026-09-04,
                                      # row 19 — s13's 1.84px raw product was a
                                      # knife-edge; the floor is 2.0, not 3.0, which
                                      # loses s13's room at (1040,999)-(1079,1085)).
ROOM_PLUG_END_COV_MIN       = 0.5     # min coverage of each end quarter: jambs (or the
                                      # wall the edge runs along) must anchor both ends
ROOM_PLUG_MID_COV_MAX       = 0.25    # mid coverage below this = interrupted wall run
                                      # (an open doorway between two jambs)
ROOM_PLUG_FULL_COV_MIN      = 0.75    # total coverage above this = wall plane drawn
                                      # through the opening (existing-opening sills,
                                      # closed sliding/garage door panels)
ROOM_SLIDE_END_ASPECT_MIN   = 2.0     # bbox aspect above which a sliding door's short-
                                      # end edges are vetoed from plugs: panels lie
                                      # along the wall, so the bbox elongates along the
                                      # slide axis (measured 9.2-24x on both reference
                                      # PDFs) and the short ends CROSS the wall band —
                                      # never a doorway plane. Near-square bboxes
                                      # (diagonal walls) veto nothing.
ROOM_WINDOW_SIDE_MIN_OVERLAP_PX2 = 16.0  # a room "lies on a side" of a window when
                                      # its polygon overlaps that side's probe (the
                                      # bbox pushed WALL_MAX_THICKNESS_PX out from
                                      # the glazing, perpendicular to it) by at
                                      # least this much: a 4x4px touch, so a room
                                      # merely grazing the probe's corner past a
                                      # jamb does not count as facing the window
ROOM_BLIND_WINDOW_MAX_AREA_PX2 = 10000.0  # a closet-scale space whose ONLY opening
                                      # is a window cannot be entered — it is the
                                      # exterior side of that window (a terrace
                                      # pocket fenced by heavy-penned setout lines
                                      # against the bay wall, a lightwell), not a
                                      # room. Measured on 5-1133: the paving pockets
                                      # beside bay windows W11/W13 are 2.7-3.7k px2
                                      # with window-only boundaries, while every real
                                      # window-bearing room on both reference PDFs
                                      # is >= 17k px2 AND carries a door opening.
                                      # Door-less window-LESS spaces stay: interior
                                      # rooms legitimately lose their door to a
                                      # missed detection (floor-plans has real ones
                                      # at 3.3-8.5k px2), but a window on the
                                      # boundary marks the building envelope, and a
                                      # blind envelope sliver is outside it.
ROOM_BASE_CONFIDENCE        = 0.50
ROOM_DOOR_BOUNDARY_BOOST    = 0.15    # a space reachable through a real door is a room
ROOM_WINDOW_BOUNDARY_BOOST  = 0.05
ROOM_CONTACT_WEIGHT         = 0.20    # scales the wall-contact ratio into confidence
ROOM_OPENING_MIN_CONFIDENCE = 0.40    # doors below this are the speculative fallback
                                      # tiers (DOOR_FALLBACK_CONFIDENCE 0.35, capped
                                      # under the offline floor, kept only for Gemini
                                      # arbitration; cross-validation is penalty-only
                                      # for doors, so nothing climbs back over): they
                                      # never get the dilated-bbox fallback, may not
                                      # anchor white walls, and their full-cover plugs
                                      # must lie inside drawn wall material — only the
                                      # interrupted-run profile (the doorway signature)
                                      # is trusted on its own
ROOM_BBOX_SEAL_MIN_CONFIDENCE = 0.55  # floor for the dilated-bbox fallback seal — the
                                      # one seal that carries NO evidence of its own
                                      # (every plug profile qualifies against drawn wall
                                      # material; the bbox stamp is pure trust). Mirrors
                                      # OFFLINE_MIN_CONFIDENCE["door"] in pipeline.py:
                                      # a door the pipeline itself would reject must not
                                      # reshape a room outline (measured on 5-1133: the
                                      # bath-fixture FP at 0.52 — single_line_leaf on a
                                      # toilet pan corner, no_wall, kept only for Gemini
                                      # arbitration — stamped a 68x50px notch into the
                                      # FAMILY BATH room edge; no real door on either
                                      # reference PDF uses this fallback, all seal
                                      # through plugs)
ROOM_PLUG_IN_WALL_FRAC      = 0.80    # min area fraction of a fallback-tier door's
                                      # full-cover plug overlapping drawn wall material:
                                      # such a plug only re-asserts existing barrier
                                      # ("costs nothing" made literal). Annotation boxes
                                      # floating NEAR a wall measure <= ~0.77 while
                                      # on-plane plugs measure 0.84+
ROOM_FOLD_SPAN_TOL          = 0.15    # |wall gap - Σ leaf lengths| / Σ leaf lengths for
                                      # a folding chain's opening (the span law: closed,
                                      # the chain covers its opening exactly). A parked
                                      # chain measures ~0 dev (GD2 on 5-1133: 222px gap
                                      # vs 223px leaf run); a half-open concertina drawn
                                      # across its opening foreshortens by cos of the
                                      # fold half-angle, still inside 15%
ROOM_FOLD_STACK_NEAR_PX     = 24.0    # the chain bbox must lie within this of the gap
                                      # axis: leaves fold flat against the wall run at
                                      # the jamb, so the stack hugs the opening plane
                                      # (jamb scale, cf. ROOM_PLUG_ANCHOR_WIN_PX)
ROOM_FOLD_JAMB_MIN_LEN_PX   = 24.0    # gap rays start only at ends of jamb-scale wall
                                      # segments, not annotation slivers
ROOM_FOLD_GAP_ESCAPE_PX     = 4.0     # ray start offset past the segment end, clearing
                                      # the segment's own flat-capped solid
ROOM_OPENING_TEXT_COVER_MAX = 0.60    # a door bbox covered this much by the text
                                      # written inside it is an annotation box ("WALL
                                      # TYPE 1" tags detected as leaf rectangles), not
                                      # a door — transparent to the room stage. Real
                                      # swing bboxes measure <= ~0.45 even with a room
                                      # label crossing them (text-mask principle, cf.
                                      # WALL_WHITE_TEXT_COVER_FRAC)

ROOM_RECESS_GAP_COVER_MIN   = 0.65    # a door-less, window-less, textless component
                                      # lying IN a wall's plane is a recess in that
                                      # wall — a chimney breast, pier or duct drawn
                                      # as a closed box on the room side of the
                                      # band with its back open to the band — not
                                      # a room. "In the plane": it fills at least
                                      # this much of the gap between two collinear
                                      # segments of the band (no opening bbox in
                                      # the gap: a doorway strip is room floor),
                                      # its back edge lies on the band's OUTER
                                      # line (ROOM_RECESS_BACK_TOL_PX past the
                                      # barrier standoff) and its depth across the
                                      # band is at most ROOM_RECESS_DEPTH_RATIO_MAX
                                      # band thicknesses. Measured on s11/s16: six
                                      # breast pockets in the 17.6px external wall
                                      # cover 0.69-0.85 of their gap, back edge at
                                      # exactly the 2px standoff, depth 1.75-2.4x
                                      # the band, no text; s02's "coats" cupboard
                                      # matches the gap (0.68) and the back edge
                                      # but is 5.2 bands deep and labelled, and
                                      # real rooms beside a band sit >= 3.6px
                                      # inside its outer edge (s01 room_0002,
                                      # s16 room_0009) and carry openings. A named
                                      # space is a space whatever its shape, so
                                      # text inside the component vetoes the rule.
ROOM_RECESS_BACK_TOL_PX     = 1.5
ROOM_RECESS_DEPTH_RATIO_MAX = 3.0

ROOM_ENTRANCE_MIN_CONFIDENCE = ROOM_BBOX_SEAL_MIN_CONFIDENCE
                                      # a door counts as an ENTRANCE — for the
                                      # blind-window drop, the wall-recess and
                                      # band-pocket rules, which all ask "can this
                                      # space be entered?" — only when the pipeline
                                      # itself stands behind it (the offline door
                                      # floor's mirror, as for the bbox seal).
                                      # detect_rooms consumes candidates BEFORE the
                                      # floor, and a rejected candidate can still
                                      # seal through an evidence-bearing plug whose
                                      # tail touches a neighbouring pocket: on s17
                                      # a 0.48 single_line_leaf in the next window's
                                      # reveal (door_0039) and a 0.35 arc_fallback
                                      # sliver in the cavity (door_0042) gave the
                                      # two reveal pockets rooms 0015/0034 a
                                      # door_count of 1 and vetoed both drops.
                                      # Corpus-wide, 16 rooms carry only such doors;
                                      # none is a closet-scale window pocket or a
                                      # recess (s17 room_0018, confirmed, 13.3k px2
                                      # with a window and a 0.35 door, is the
                                      # nearest to the 10k blind cap). Confidence
                                      # and door_openings still count every seal.
ROOM_BAND_POCKET_FACE_COVER_MIN = 0.65  # a door-less, window-less, textless
                                      # component lying INSIDE a wall band's
                                      # thickness is the band's own material — a
                                      # window reveal, a hollow cavity, a blocked
                                      # opening — never floor: its two long edges
                                      # lie on wall faces (at the barrier standoff,
                                      # each face covering at least this much of
                                      # the edge — real pockets measure 1.0; the
                                      # slack mirrors ROOM_RECESS_GAP_COVER_MIN for
                                      # a face a text mask interrupts) spaced at
                                      # most WALL_MAX_THICKNESS_PX apart, i.e. two
                                      # faces that could have paired as one wall.
                                      # Rooms are wider than a wall by definition
                                      # (the lattice rule's premise). Measured on
                                      # s17: the 1.5px-pen cavity wall is drawn
                                      # leaf/cavity/leaf (11.75/12/13.25px, 37px in
                                      # all, over the cap, 0 diagonal marks in the
                                      # band); at each window the two middle lines
                                      # stop, the glazing runs mid-leaf in the
                                      # continuous outer leaf, and the reveal
                                      # between the outer leaf's inner face and the
                                      # wall's inner face — 25.25px, a strong pair
                                      # the far-side rule drops as "paired across
                                      # free space" — came out as a 21px-deep 3.1k
                                      # px2 pocket (rooms 0015/0034, 0.85). The
                                      # collinear-gap recess rule sees 0034 (its
                                      # inner pair resumes on both sides) but not
                                      # 0015 (the next window's reveal adjoins it).
                                      # Corpus-wide the signature matches exactly
                                      # those two; the narrowest confirmed room
                                      # otherwise is s11 room_0018, a 19px-wide
                                      # storage cupboard at f=0.5 whose faces sit
                                      # 21.75px apart against the scaled 18px cap
                                      # (1.2x), and every other confirmed room is
                                      # >= 52px wide at identity.


@dataclass(frozen=True)
class RoomGates:
    """World-space room gates pre-multiplied by the detection factor
    (areas by factor²). Same field-naming rule as WallGates. The two
    walls-owned constants rooms consumes are scaled here identically to
    WallGates so the stages can never disagree about a wall's size."""
    factor: float
    ROOM_MIN_AREA_PX2: float                 # × f²
    ROOM_BLIND_WINDOW_MAX_AREA_PX2: float    # × f²
    ROOM_OPENING_SEAL_PX: float
    ROOM_PLUG_JAMB_SEEK_PX: float
    ROOM_PLUG_ANCHOR_WIN_PX: float
    ROOM_PLUG_HALF_WIDTH_PX: float
    ROOM_FOLD_STACK_NEAR_PX: float
    ROOM_FOLD_JAMB_MIN_LEN_PX: float
    WALL_MAX_THICKNESS_PX: float             # walls-owned, used by rooms
    WALL_HATCH_MAX_LEN_PX: float             # walls-owned, used by rooms

    @classmethod
    def at(cls, factor: float) -> "RoomGates":
        return cls(
            factor=factor,
            ROOM_MIN_AREA_PX2=ROOM_MIN_AREA_PX2 * factor * factor,
            ROOM_BLIND_WINDOW_MAX_AREA_PX2=(
                ROOM_BLIND_WINDOW_MAX_AREA_PX2 * factor * factor),
            ROOM_OPENING_SEAL_PX=ROOM_OPENING_SEAL_PX * factor,
            ROOM_PLUG_JAMB_SEEK_PX=ROOM_PLUG_JAMB_SEEK_PX * factor,
            ROOM_PLUG_ANCHOR_WIN_PX=ROOM_PLUG_ANCHOR_WIN_PX * factor,
            # World-space (half a wall band) with a PAPER floor at the line
            # barrier standoff: a plug thinner than the 2px standoff every
            # other barrier keeps cannot meet its neighbours flush. At s13's
            # f=0.367 the raw product is 1.84px and the room at
            # (1040,999)-(1079,1085) survived only in [1.0, 1.25] of that
            # value (W-gate census 2026-09-04, row 19); the floor is the
            # standoff itself, 2.0 — a 3.0 floor loses the room.
            ROOM_PLUG_HALF_WIDTH_PX=max(
                ROOM_PLUG_HALF_WIDTH_PX * factor, ROOM_LINE_BARRIER_PX),
            ROOM_FOLD_STACK_NEAR_PX=ROOM_FOLD_STACK_NEAR_PX * factor,
            ROOM_FOLD_JAMB_MIN_LEN_PX=ROOM_FOLD_JAMB_MIN_LEN_PX * factor,
            WALL_MAX_THICKNESS_PX=WALL_MAX_THICKNESS_PX * factor,
            WALL_HATCH_MAX_LEN_PX=WALL_HATCH_MAX_LEN_PX * factor,
        )


ROOM_GATES_UNSCALED = RoomGates.at(1.0)


def _text_cover_frac(bbox, text_spans) -> float:
    """Fraction of a bbox area covered by the text spans lying over it."""
    if not text_spans:
        return 0.0
    b = box(*bbox)
    if b.area <= 0:
        return 0.0
    covers = [
        box(*t.bbox) for t in text_spans
        if not (
            t.bbox[2] <= bbox[0] or t.bbox[0] >= bbox[2]
            or t.bbox[3] <= bbox[1] or t.bbox[1] >= bbox[3]
        )
    ]
    if not covers:
        return 0.0
    return unary_union(covers).intersection(b).area / b.area


def _window_seal(candidate, *, gates: RoomGates = ROOM_GATES_UNSCALED) -> Polygon:
    """Barrier polygon sealing a window opening.

    A horizontal/vertical window's bbox IS the wall-band segment it sits in
    and seals as-is. A diagonal window (a 45-degree bay face) breaks that
    premise: its axis-aligned bbox is a square that overhangs the wall plane
    on both sides, stamping barrier into free space — measured on 5-1133,
    bay window W11's square bridged the bay wall to the terrace setout lines
    and fenced a paving pocket into a phantom room. Seal along the drawn
    band instead: the bbox diagonal matching the glazing angle, buffered to
    the band's measured half-thickness (bbox diagonal minus the opening span
    between the end caps), so the seal shadows the window's own ink exactly
    like door plugs shadow the wall plane.
    """
    x0, y0, x1, y1 = candidate.bbox
    if candidate.evidence.get("orientation") != "diagonal":
        return box(x0, y0, x1, y1)
    angle = float(candidate.evidence.get("glazing_angle_deg") or 45.0) % 180.0
    if angle < 90.0:
        band = LineString([(x0, y0), (x1, y1)])  # y-down: descends left-to-right
    else:
        band = LineString([(x0, y1), (x1, y0)])
    opening = float(candidate.evidence.get("opening_width_px") or 0.0)
    half_th = max(gates.ROOM_PLUG_HALF_WIDTH_PX, (band.length - opening) / 2.0)
    return band.buffer(half_th, cap_style=2)


def _open_leaf_edges(
    candidate, *, gates: RoomGates = ROOM_GATES_UNSCALED
) -> frozenset[int]:
    """Bbox edges of a garden-layout double door that are room floor, not wall.

    A garden pair is drawn OPEN by construction: the two leaves park at
    opposite outer ends of the opening (along two opposite bbox edges), and
    the wall plane is one of the two perpendicular edges. Three of the four
    edges are therefore room/garden floor and must not take a plug:

    - the two parked-leaf edges: on 5-1133 door 0121 the bottom (leaf) edge
      crossed the angled bay wall at one end and clipped terrace linework at
      the other, pattern-matching the interrupted-run doorway signature and
      fencing a phantom paving-pocket "room" outside the bay;
    - the swing-extent edge opposite the doorway, identified as the edge the
      merged opening_line lies along: that chord connects the two arc
      endpoints farthest apart, and for a garden pair those are always the
      parked leaves' open TIPS (tip-to-tip spans the full opening W; a tip
      to a closed-position end near mid-doorway spans only ~0.71 W), so the
      chord edge bounds the swing squares — never the doorway. Measured on
      floor-plans door_0016: the swing-extent edge anchored on the two jamb
      walls continuing past the doorway, pattern-matched an interrupted run,
      and its plug held the bedroom outline 5px short of the doorway (cf.
      _restrict_swing_plugs, the single-swing analog of this veto).

    French pairs are exempt: their collinear leaves are drawn closed IN the
    wall plane, so the leaf edge is exactly the edge that must stay eligible
    (cf. the closed-leaf plug retry and the sliding white-ring exemption).
    A diagonal garden pair's chord matches no axis edge and adds no veto.
    Edge indices follow _door_plugs' order: 0 top, 1 bottom, 2 left, 3 right.
    """
    if candidate.evidence.get("swing_layout") != "garden":
        return frozenset()
    x0, y0, x1, y1 = candidate.bbox
    tol = gates.ROOM_PLUG_HALF_WIDTH_PX
    edges: set[int] = set()
    for key in ("leaf_bbox_a", "leaf_bbox_b"):
        leaf = candidate.evidence.get(key)
        if not leaf:
            continue
        lx0, ly0, lx1, ly1 = leaf
        if lx1 - lx0 >= ly1 - ly0:
            cy = (ly0 + ly1) / 2.0
            if abs(cy - y0) <= tol:
                edges.add(0)
            elif abs(cy - y1) <= tol:
                edges.add(1)
        else:
            cx = (lx0 + lx1) / 2.0
            if abs(cx - x0) <= tol:
                edges.add(2)
            elif abs(cx - x1) <= tol:
                edges.add(3)
    chord = candidate.evidence.get("opening_line")
    if chord and len(chord) == 2:
        (px, py), (qx, qy) = chord
        if abs(py - y0) <= tol and abs(qy - y0) <= tol:
            edges.add(0)
        elif abs(py - y1) <= tol and abs(qy - y1) <= tol:
            edges.add(1)
        elif abs(px - x0) <= tol and abs(qx - x0) <= tol:
            edges.add(2)
        elif abs(px - x1) <= tol and abs(qx - x1) <= tol:
            edges.add(3)
    return frozenset(edges)


def _sliding_end_edges(candidate) -> frozenset[int]:
    """Bbox short-end edges of a sliding door: across the wall, never wall plane.

    A sliding assembly's panels lie along its wall by construction, so the
    bbox elongates along the slide axis and the doorway plane is one of the
    two LONG edges. A short-end edge crosses the wall band, and the only
    profile it can match is a re-assertion of that band (full cover from the
    jamb post it crosses plus flanking faces at loose hug) — but its plug is
    thicker than the linework it shadows and carries SEAL-length tails, so
    it pokes plug-width notches into the rooms on both sides of the wall
    (measured on floor-plans door_0011: the bottom end-edge plug bit a
    12x6px square out of room_0010 and a 7x10px notch out of room_0005 by
    the "110" dimension). Vetoed outright, like a garden pair's parked-leaf
    edges. Near-square sliding bboxes (diagonal walls) veto nothing.
    Edge indices follow _door_plugs' order: 0 top, 1 bottom, 2 left, 3 right.
    """
    if candidate.evidence.get("assembly_type") != "sliding":
        return frozenset()
    x0, y0, x1, y1 = candidate.bbox
    w, h = x1 - x0, y1 - y0
    if max(w, h) < ROOM_SLIDE_END_ASPECT_MIN * min(w, h):
        return frozenset()
    return frozenset({2, 3} if w >= h else {0, 1})


def _swing_hinge_edges(candidate) -> frozenset[int] | None:
    """Bbox edges meeting at the hinge corner of a single quarter-swing door.

    A swing door's wall plane passes through its hinge, so the edge carrying
    the doorway is one of the two edges meeting at the hinge corner; the
    opposite pair bounds the swing square — room floor by construction. The
    hinge is derived from the drawn leaf and the arc chord (opening_line):
    the chord endpoint lying ON the leaf (within ROOM_PLUG_NEAR_PX) is the
    open tip, and the leaf corner farthest from it is the hinge. This holds
    for both drawing conventions — leaf drawn open (perpendicular to the
    wall) or closed (in the wall plane) — because the ink of a quarter swing
    is symmetric between them: only WHICH radius is wall differs, and both
    radii meet at the hinge. Ambiguous geometry (a half-open leaf whose
    hinge floats inside the bbox, a chord touching the leaf at both ends or
    neither) returns None and the caller keeps the status quo.
    Edge indices follow _door_plugs' order: 0 top, 1 bottom, 2 left, 3 right.
    """
    if candidate.evidence.get("assembly_type") not in (
        "single", "single_line_leaf"
    ):
        return None
    chord = candidate.evidence.get("opening_line")
    leaf = candidate.evidence.get("leaf_bbox")
    if not chord or not leaf:
        return None
    lx0, ly0, lx1, ly1 = leaf

    def leaf_dist(pt):
        dx = max(lx0 - pt[0], 0.0, pt[0] - lx1)
        dy = max(ly0 - pt[1], 0.0, pt[1] - ly1)
        return math.hypot(dx, dy)

    on_leaf = [leaf_dist(pt) <= ROOM_PLUG_NEAR_PX for pt in chord]
    if on_leaf[0] == on_leaf[1]:
        return None
    tip = chord[0] if on_leaf[0] else chord[1]
    corners = [(lx0, ly0), (lx1, ly0), (lx0, ly1), (lx1, ly1)]
    hinge = max(corners, key=lambda p: math.hypot(p[0] - tip[0], p[1] - tip[1]))
    x0, y0, x1, y1 = candidate.bbox
    h_edge = 0 if abs(hinge[1] - y0) <= abs(hinge[1] - y1) else 1
    v_edge = 2 if abs(hinge[0] - x0) <= abs(hinge[0] - x1) else 3
    h_off = min(abs(hinge[1] - y0), abs(hinge[1] - y1))
    v_off = min(abs(hinge[0] - x0), abs(hinge[0] - x1))
    if max(h_off, v_off) > ROOM_PLUG_NEAR_PX:
        return None
    return frozenset({h_edge, v_edge})


def _seek_edges(candidate) -> frozenset[int]:
    """Bbox edges whose plug tails may SEEK their jamb beyond the fixed reach.

    Only a single swing's hinge edges (`_swing_hinge_edges`) — the two
    edges its wall plane can lie along — and only when the door carries
    the pipeline's own conviction (>= ROOM_BBOX_SEAL_MIN_CONFIDENCE, the
    floor every trust-based seal shares): a fallback-tier box hugging a
    wall must not reach out for a jamb, and a garden pair or slider pins
    no hinge (s01 door_0015's piers at 281mm stay a plane stamp).
    """
    if candidate.confidence < ROOM_BBOX_SEAL_MIN_CONFIDENCE:
        return frozenset()
    hinge = _swing_hinge_edges(candidate)
    return hinge if hinge is not None else frozenset()


def _restrict_swing_plugs(candidate, plugs):
    """Hold a single swing door to plugs on its hinge edges, one plane only.

    A quarter-swing door has exactly ONE wall plane and it passes through
    the hinge corner (_swing_hinge_edges), so a plug on either far edge is
    phantom: the edge bounds the swing square — room floor — and qualified
    only because perpendicular walls crossed near its extended ends,
    pattern-matching the interrupted-run doorway signature (measured on
    floor-plans door_0000, the main entrance: the top edge anchored on the
    hallway divider at one end and the exterior wall at the other, and its
    plug fenced the swing square out of the hallway — the fenced component
    then dissolved as door floor and the hallway stopped 5px short of the
    door). Among the hinge edges, an interrupted-run plug IS the doorway,
    so a full-cover plug beside it is the other hinge edge hugging a
    parallel wall face within ROOM_PLUG_NEAR_PX (door_0000's left edge,
    5px off the divider band: its plug hung half in free floor and held the
    hallway off the wall) — a genuinely drawn-through plane is its own
    barrier, so dropping the full plug costs nothing. If the restriction
    would leave no plugs where the unrestricted profile found some, the
    unrestricted set stands: a door whose only wall evidence lies on far
    edges is mis-derived or a false positive, and either way losing all
    plugs would promote it to the dilated-bbox fallback — a pure-trust
    stamp into free space, strictly worse than the status quo.
    """
    hinge_edges = _swing_hinge_edges(candidate)
    if hinge_edges is None or not plugs:
        return plugs
    kept = [t for t in plugs if t[2] in hinge_edges]
    if any(kind == "interrupted" for _, kind, _ in kept):
        kept = [t for t in kept if t[1] == "interrupted"]
    return kept or plugs


def _plane_stamp(
    candidate, skip_edges, wall_material,
    *, gates: RoomGates = ROOM_GATES_UNSCALED,
) -> Polygon:
    """The plug-less fallback seal, restricted to the door's wall-plane edges.

    A door with no qualifying plug used to seal by ``box(bbox) ⊕ SEAL`` —
    a stamp that grows SEAL ACROSS the door's plane as well as along it,
    so the whole swing square left its room and the room on the far side
    of the wall lost a SEAL-deep strip at every such door (measured at
    seal 15: s17 door_0001's 0.83 single on the confirmed SH/WC, whose
    recorded outline WAS the stamp's L-shaped edge, −9.0k px² of swing
    square; s01 door_0015's garden pair −447 on the living room; s04
    door_0003's slider −539 on each flanking room; s16/s18 at f=0.5).

    A door's wall plane lies along a bbox edge its own evidence has not
    ruled out: a single swing's plane passes through its hinge corner, so
    it is one of the two hinge edges (`_swing_hinge_edges`; the far edges
    bound the swing square — room floor); a slider's long axis IS its wall
    (`_sliding_end_edges` vetoes the short ends); a garden pair's parked
    leaves and tip chord are vetoed (`_open_leaf_edges`), leaving its
    wall edge; a door whose evidence pins nothing keeps all four edges (a
    ring whose interior dissolves as door floor). Measured on the
    corpus's 181 hinge-derivable plugged singles (W-gate iteration 3
    step 8, 2026-09-05): the kept plug lies on a hinge edge 177 times,
    and the leaf-axis "open leaf" convention names the plane edge 159
    times against 5 for the closed-leaf convention — 3 % wrong, so the
    fallback never picks ONE hinge edge. The plane edge sits ON its wall
    face: median 0.0 px, max 4.2 px off the dilated material, inside the
    plug's own ±ROOM_PLUG_HALF_WIDTH_PX cross-section.

    Each plane edge is stamped as the plug it would have carried had its
    profile qualified — the edge line at the plug's half-width, with a
    SEAL tail at each end — so the seal is a subset of the old stamp
    everywhere (rooms can only gain floor, never lose it). A tail is the
    old stamp's along-reach and stays trust-based: it is kept as far as
    wall material HUGS its spine (within ROOM_PLUG_NEAR_PX — the loose
    hug the profile itself uses, wider than a qualified plug's touch
    envelope because no sample proved these jambs are in reach; the
    true class's jambs sit ≤ 13 px past the corner, s01 door_0015's piers
    at 18 px are reached and the free-space pinch closes the rest) and
    ends where that material ends (`_tail_material_end`): a doorway
    tail runs into its jamb, a leaf edge's hinge-end tail crosses the
    plane and stops at the band's far face instead of stamping a stub
    into the far room, and a tail hugging nothing — the leaf's free tip —
    is dropped.
    """
    plane = set(range(4)) - set(skip_edges)
    hinge = _swing_hinge_edges(candidate)
    if hinge is not None:
        plane &= hinge
    if not plane:
        plane = set(range(4))
    x0, y0, x1, y1 = candidate.bbox
    edges = [
        ((x0, y0), (x1, y0)),
        ((x0, y1), (x1, y1)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
    ]
    reach = gates.ROOM_OPENING_SEAL_PX
    half = gates.ROOM_PLUG_HALF_WIDTH_PX
    slabs = []
    for edge_idx in sorted(plane):
        p, q = edges[edge_idx]
        length = math.hypot(q[0] - p[0], q[1] - p[1])
        if length < 1e-6:
            continue
        ux = (q[0] - p[0]) / length
        uy = (q[1] - p[1]) / length
        end_a = _tail_material_end(
            p, -ux, -uy, reach, ROOM_PLUG_NEAR_PX, wall_material)
        end_b = _tail_material_end(
            q, ux, uy, reach, ROOM_PLUG_NEAR_PX, wall_material)
        spine = LineString([
            (p[0] - ux * end_a, p[1] - uy * end_a),
            (q[0] + ux * end_b, q[1] + uy * end_b),
        ])
        slabs.append(spine.buffer(half, cap_style=2))
    return unary_union(slabs)


def _tail_material_end(corner, ux, uy, reach, half, wall_material) -> float:
    """How far, along (ux, uy) from corner, the material a plug tail touches runs.

    The envelope is the tail's spine buffered by the plug half-width with
    round caps — exactly the region a tail sample can touch within
    ROOM_PLUG_HALF_WIDTH_PX — and the answer is the farthest axial position
    of wall material inside it, clipped to [0, reach]: material continuing
    past the reach returns reach, an envelope holding none returns 0.
    """
    far = (corner[0] + ux * reach, corner[1] + uy * reach)
    hit = LineString([corner, far]).buffer(half).intersection(wall_material)
    end = 0.0
    stack = [hit]
    while stack:
        g = stack.pop()
        if g.is_empty:
            continue
        if hasattr(g, "geoms"):
            stack.extend(g.geoms)
            continue
        coords = g.exterior.coords if hasattr(g, "exterior") else g.coords
        for cx, cy in coords:
            end = max(end, (cx - corner[0]) * ux + (cy - corner[1]) * uy)
    return min(end, reach)


def _clip_plug_tails(
    bbox, plugs, wall_material, *, gates: RoomGates = ROOM_GATES_UNSCALED,
):
    """End each bbox-edge plug's tails AT the material they touch.

    _door_plugs trims a tail back to the farthest profile SAMPLE touching
    wall material, and "touching" is a distance test, so the tail still
    runs up to ROOM_PLUG_HALF_WIDTH_PX past the END of the material it
    touches — a plug-width stub stamped into the free space beyond an
    island or a band end. Measured on s02 door_0050, the 0.35 fallback
    door on the "A" section-marker bar (a filled ring islanded in BEDROOM
    2): at seal 15 its two full-cover plugs ran 4.8px past each end of
    the bar, narrowing the 20.5px neck to the wall under the 16px
    free-space pinch, and the outline wrapped the bar column (W-gate
    iteration 3 step 2); at seal 12 the sample phase happened to miss the
    bar, while 45 of s15's 52 band-end tails and all 6 of s01's overshoot
    1–4.4px, each a stub or a stub-induced slant on a room edge. The
    convention: a tail exists to reach the jamb the bbox stopped short
    of, and it ends where the material it touches ends, never beyond it —
    material continuing past the tail's reach keeps the whole tail,
    material ending inside the reach ends the tail there
    (_tail_material_end, on the tail's own touch envelope).

    Applied AFTER the caller has classified the plug (kind, hinge
    restriction, the fallback tier's in-wall fraction) on the geometry
    _door_plugs returns: clipping the out-of-material stubs off a plug
    raises its in-material fraction, and gating on the clipped plug let
    57 more fallback-tier plugs through on s15 (263 -> 320), seven of
    them cutting 8–38 px2 notches into rooms 0006/0010/0014/0020/0021 and
    s17 rooms 0022/0026 — the in-wall gate was calibrated with the tails
    in its denominator (phantoms ~0.77, on-plane 0.84+), so it keeps
    them. Each plug is cut to the slab between its two material ends
    along the edge line; the cross-section and lateral position from the
    jamb fit are untouched. Plugs without an edge index (the folding
    chain-gap plug) pass through.
    """
    if not plugs:
        return plugs
    x0, y0, x1, y1 = bbox
    edges = [
        ((x0, y0), (x1, y0)),
        ((x0, y1), (x1, y1)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
    ]
    reach = gates.ROOM_OPENING_SEAL_PX
    half = gates.ROOM_PLUG_HALF_WIDTH_PX
    out = []
    for poly, kind, edge_idx in plugs:
        if edge_idx is None or not (0 <= edge_idx < 4):
            out.append((poly, kind, edge_idx))
            continue
        p, q = edges[edge_idx]
        length = math.hypot(q[0] - p[0], q[1] - p[1])
        if length < 1e-6:
            out.append((poly, kind, edge_idx))
            continue
        ux = (q[0] - p[0]) / length
        uy = (q[1] - p[1]) / length
        # The clip's reach at each end is the tail's own: SEAL for a plug
        # the fixed profile qualified, the plug's actual extent beyond the
        # corner for a tail that SOUGHT its jamb further out (_door_plugs
        # with seek_edges) — clipping that tail at SEAL would cut it back
        # off the very jamb it reached.
        rings = [poly.exterior] if hasattr(poly, "exterior") else [
            g.exterior for g in getattr(poly, "geoms", ()) if hasattr(g, "exterior")
        ]
        proj = [
            (cx - p[0]) * ux + (cy - p[1]) * uy
            for ring in rings for cx, cy in ring.coords
        ]
        reach_a = reach_b = reach
        if proj:
            if -min(proj) > reach + 1e-6:
                reach_a = -min(proj)
            if max(proj) - length > reach + 1e-6:
                reach_b = max(proj) - length
        end_a = _tail_material_end(p, -ux, -uy, reach_a, half, wall_material)
        end_b = _tail_material_end(q, ux, uy, reach_b, half, wall_material)
        slab = LineString([
            (p[0] - ux * end_a, p[1] - uy * end_a),
            (q[0] + ux * end_b, q[1] + uy * end_b),
        ]).buffer(2.0 * half + 2.0, cap_style=2)
        clipped = poly.intersection(slab)
        out.append((poly if clipped.is_empty else clipped, kind, edge_idx))
    return out


@dataclass
class _EdgeProfile:
    """The coverage profile of wall material along one extended bbox edge.

    Samples run from ``reach_a`` beyond the edge's first corner to
    ``reach_b`` beyond its second; ``kind`` is the profile's verdict
    ("interrupted" / "full" / None) and ``anchored_a`` / ``anchored_b`` say
    whether each end window both covers and touches wall material — the
    per-end half of the interrupted signature, which the jamb seek reads.
    """
    edge_line: LineString
    ext_len: float
    n: int
    step: float
    win: int
    reach_a: float
    reach_b: float
    touch: list[bool]
    anchored_a: bool
    anchored_b: bool
    kind: str | None


def _edge_profile(
    p, q, ux, uy, length, reach_a, reach_b, wall_material, gates: RoomGates,
) -> _EdgeProfile:
    a = (p[0] - ux * reach_a, p[1] - uy * reach_a)
    b = (q[0] + ux * reach_b, q[1] + uy * reach_b)
    ext_len = length + (reach_a + reach_b)
    edge_line = LineString([a, b])
    n = max(int(ext_len / ROOM_PLUG_SAMPLE_PX), 8) + 1
    dists = [
        edge_line.interpolate(ext_len * i / (n - 1)).distance(wall_material)
        for i in range(n)
    ]
    covered = [d <= ROOM_PLUG_NEAR_PX for d in dists]
    quarter = n // 4
    # Anchor window: the legacy n//4 quarter, capped at jamb scale — the
    # anchoring jamb does not grow with the doorway, so on wide (double)
    # doorways the quarter dilutes real jamb coverage below the gate.
    win = min(
        quarter,
        int(math.ceil(
            gates.ROOM_PLUG_ANCHOR_WIN_PX / ROOM_PLUG_SAMPLE_PX)) + 1,
    )
    start_cov = sum(covered[:win]) / win
    end_cov = sum(covered[-win:]) / win
    # Trim the mid window by the hug distance: samples just inside an
    # open doorway still sit within ROOM_PLUG_NEAR_PX of the jamb corner
    # diagonally and must not count as mid coverage. Mid coverage itself
    # uses the tighter in-plane hug (ROOM_PLUG_MID_NEAR_PX): the
    # interrupted-run middle must be empty IN the opening plane, and a
    # perpendicular wall's end cap floating a few px off the plane must
    # not fill the doorway gap.
    trim = quarter + int(math.ceil(ROOM_PLUG_NEAR_PX / ROOM_PLUG_SAMPLE_PX))
    in_plane = [d <= ROOM_PLUG_MID_NEAR_PX for d in dists]
    mid = in_plane[trim:n - trim] or in_plane[quarter:n - quarter]
    mid_cov = sum(mid) / len(mid)
    total_cov = sum(covered) / n
    # Interrupted run = jambs in the plane, nothing between them in the
    # plane. Both end windows must actually REACH the plug band (within
    # its half-width — the plug must connect to jamb material, not
    # float); a parallel band hugging the whole edge from beyond that
    # anchors both ends at the loose hug and touches nothing — the
    # profile of an annotation/fixture box beside a wall, not of a
    # doorway (measured: a real jamb solid ends 3.5px off the bbox edge
    # on floor-plans door_0008; the white-fixture phantom's parallel
    # band sits 6px off its bbox edge).
    touch = [d <= gates.ROOM_PLUG_HALF_WIDTH_PX for d in dists]
    anchored_a = start_cov >= ROOM_PLUG_END_COV_MIN and any(touch[:win])
    anchored_b = end_cov >= ROOM_PLUG_END_COV_MIN and any(touch[-win:])
    kind: str | None = None
    if start_cov >= ROOM_PLUG_END_COV_MIN and end_cov >= ROOM_PLUG_END_COV_MIN:
        if mid_cov <= ROOM_PLUG_MID_COV_MAX and anchored_a and anchored_b:
            kind = "interrupted"
        elif total_cov >= ROOM_PLUG_FULL_COV_MIN:
            kind = "full"
    return _EdgeProfile(
        edge_line=edge_line, ext_len=ext_len, n=n, step=ext_len / (n - 1),
        win=win, reach_a=reach_a, reach_b=reach_b, touch=touch,
        anchored_a=anchored_a, anchored_b=anchored_b, kind=kind,
    )


def _seek_jamb(corner, ux, uy, reach, half, wall_material) -> float | None:
    """How far along (ux, uy) from corner a tail sample first touches wall material.

    The first axial position within ``reach`` at which a point on the
    extended edge line lies within ``half`` of wall material — the
    material's own outline buffered by the plug half-width, cut by the
    ray, so a perpendicular jamb return, a collinear band end or a fill
    ring all count, and the answer is phase-free. None when nothing is
    within reach.
    """
    far = (corner[0] + ux * reach, corner[1] + uy * reach)
    hit = LineString([corner, far]).intersection(wall_material.buffer(half))
    if hit.is_empty:
        return None
    best: float | None = None
    stack = [hit]
    while stack:
        g = stack.pop()
        if g.is_empty:
            continue
        if hasattr(g, "geoms"):
            stack.extend(g.geoms)
            continue
        for cx, cy in g.coords:
            pos = (cx - corner[0]) * ux + (cy - corner[1]) * uy
            if best is None or pos < best:
                best = pos
    return None if best is None else max(best, 0.0)


def _door_plugs(
    bbox, wall_material, skip_edges=frozenset(),
    *, seek_edges=frozenset(), gates: RoomGates = ROOM_GATES_UNSCALED,
) -> list[tuple[Polygon, str, int]]:
    """Thin barrier bands along the wall planes through a detected door.

    The door bbox covers the swing area — room floor, not wall — so using it
    directly as a barrier notches the room outline around the door, and when
    the bbox stops short of a jamb, free space leaks through the clearance
    strip and fuses two rooms. Instead, plug the bbox edges that lie on a
    wall plane, judged by the coverage profile of wall material hugging the
    edge (sampled along it, extended past the bbox so the plug reaches jambs
    the swing arc stopped short of). Two profiles qualify:

    - interrupted wall run: both end quarters anchored on jambs, middle
      empty where the leaf swings — the plug seals the open doorway;
    - drawn-through wall plane: near-total coverage — existing-opening
      sills, closed sliding/garage door panels, or a perpendicular wall the
      bbox rests against. The plug coincides with drawn linework, costing
      nothing and sealing hairline gaps in it.

    Middling coverage (annotation clutter, no clear plane) qualifies no
    edge; the caller falls back to the dilated bbox. A qualified plug's
    end extensions are trimmed back to the farthest sample touching wall
    material, so a tail reaches INTO its jamb but never floats past it
    into room floor; the caller then ends each tail AT the material it
    touches with _clip_plug_tails, after classifying the plug on the
    sample-trimmed geometry this function returns.

    Each plug is returned tagged with the profile that qualified it
    ("interrupted" / "full") so the caller can hold fallback-tier doors'
    full-cover plugs to the stricter lies-inside-wall-material test: "near
    total coverage" alone is also satisfied by an annotation box floating
    within ROOM_PLUG_NEAR_PX of a wall band, whose plug would then hang in
    free space and notch the room. The edge index (0 top, 1 bottom, 2 left,
    3 right) rides along so _restrict_swing_plugs can hold single swing
    doors to their hinge edges.

    skip_edges holds indices (0 top, 1 bottom, 2 left, 3 right) of edges the
    door's own evidence rules out as wall plane — a garden pair's parked-open
    leaf edges (_open_leaf_edges) — regardless of coverage profile.

    seek_edges holds the edges whose tails may SEEK their jamb beyond the
    fixed reach (`_seek_edges`: a >= 0.55 single swing's hinge edges). A
    doorway is cut out of a wall, so its latch jamb is wall material the
    plug has to reach — but the reach is fixed in advance while the jamb's
    distance is drawn, and a sheet that draws its swing symbols short of
    their openings on the latch side (s01: a 671mm leaf in an 847mm
    opening, its four swings' latch jambs 187–219mm past the bbox corner
    at its true 1:92.2 against a corpus p90 of 34mm) loses the doorway
    whenever the scaled tail stops short (at f=0.542 the hall door's
    8.13px tail ended 4.1px off the corner jamb block's right face and
    the hall merged with the living room; W-gate iteration 3 step 9). So
    when a seeking edge's profile anchors at exactly ONE end — the other
    end's window neither half-covered nor touching — the tail on the
    failing side looks outward from its corner for the nearest wall
    material within ROOM_PLUG_JAMB_SEEK_PX (`_seek_jamb`: a perpendicular
    jamb return counts, as do a band end and a fill ring; opening seals
    are never in the material this function sees), extends that end's
    reach to the material plus the anchor window, and re-profiles with
    asymmetric reaches. Only the interrupted signature may result: the
    seek exists to find a doorway's jamb, and a doorway is empty between
    its jambs — a sought profile that reads "full" is a drawn-through
    plane the fixed reach did not assert and the seek must not either.
    An end that touches material inside the fixed reach but is not half
    covered (the window straddles the corner into the doorway) seeks the
    same way and finds that material, so a nib 12px out anchors as the
    jamb it is. Measured on the corpus (iteration 3 step 9,
    `tools/census_scratch/step9/material_seek_probe.py`; every un-anchored
    hinge-edge end of a >= 0.55 single on 18 sheets at their factors, 172
    ends): the true class is s18 door_0018's doorway (a 139px
    perpendicular face 11px = 186mm out, plug-less before) and s01's hall
    at its true factor (191mm); the one false hit within 300mm is s14
    door_0007's open-leaf tip reaching a wall-fill chevron ring at 296mm,
    1.18x over the 250mm cap, and every other hit is another opening's
    seal, which is not wall material. As implemented (`seek_census.py`,
    every door on 18 sheets re-profiled with and without the seek) the
    outcome changes on four doors, every hit a perpendicular wall: those
    two, s17 door_0004 (a 0.95 single drawn CLOSED in its doorway, its
    latch jamb a 32.5px band 121mm past the corner) and s14 door_0008 (an
    11.5px band 76mm out — inside the fixed reach, but the anchor window
    straddled the corner into the doorway and read 3/7).
    """
    x0, y0, x1, y1 = bbox
    edges = [
        ((x0, y0), (x1, y0)),
        ((x0, y1), (x1, y1)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
    ]
    plugs: list[tuple[Polygon, str, int]] = []
    for edge_idx, (p, q) in enumerate(edges):
        if edge_idx in skip_edges:
            continue
        length = math.hypot(q[0] - p[0], q[1] - p[1])
        if length < 1e-6:
            continue
        ux = (q[0] - p[0]) / length
        uy = (q[1] - p[1]) / length
        seal = gates.ROOM_OPENING_SEAL_PX
        prof = _edge_profile(
            p, q, ux, uy, length, seal, seal, wall_material, gates)
        if (
            prof.kind is None and edge_idx in seek_edges
            and prof.anchored_a != prof.anchored_b
        ):
            if prof.anchored_a:
                corner, dx, dy = q, ux, uy
            else:
                corner, dx, dy = p, -ux, -uy
            hit = _seek_jamb(
                corner, dx, dy, gates.ROOM_PLUG_JAMB_SEEK_PX,
                gates.ROOM_PLUG_HALF_WIDTH_PX, wall_material,
            )
            if hit is not None:
                reach = hit + gates.ROOM_PLUG_ANCHOR_WIN_PX
                sought = _edge_profile(
                    p, q, ux, uy, length,
                    seal if prof.anchored_a else reach,
                    reach if prof.anchored_a else seal,
                    wall_material, gates,
                )
                if sought.kind == "interrupted":
                    prof = sought
        if prof.kind is None:
            continue
        kind = prof.kind
        edge_line, ext_len, n, step = (
            prof.edge_line, prof.ext_len, prof.n, prof.step)
        win, touch = prof.win, prof.touch
        # Trim each extension to the material that supports it: the tail
        # exists to reach the jamb the bbox stopped short of, so it ends
        # at its farthest sample still touching wall material (within the
        # plug half-width). A tail hanging in free space — qualified by
        # the loose hug of a parallel band, or overshooting a crossed
        # jamb's far face — seals nothing and stamps a plug-width notch
        # into the adjoining room (door_0002's top-left tail on
        # floor-plans floated at 8.7px and notched room_0005 beside the
        # jamb). A clearance gap a trimmed tail no longer bridges is far
        # thinner than the GAP_CLOSE pinch, so the rooms it separates
        # still split.
        tail_n_a = max(int(prof.reach_a / step), 1)
        pos_a = prof.reach_a
        for i in range(min(tail_n_a, n)):
            if touch[i]:
                pos_a = min(i * step, prof.reach_a)
                break
        tail_n_b = max(int(prof.reach_b / step), 1)
        pos_b = ext_len - prof.reach_b
        for i in range(n - 1, max(n - 1 - tail_n_b, -1), -1):
            if touch[i]:
                pos_b = max(i * step, ext_len - prof.reach_b)
                break
        # A tail that still runs PAST the end of the material it touches
        # (the touch test reaches half a plug width beyond it) is cut back
        # by _clip_plug_tails once the caller has classified the plug.
        spine = LineString(
            [edge_line.interpolate(pos_a), edge_line.interpolate(pos_b)]
        )
        # The plug is the wall band continued across the doorway, so it
        # takes the band's cross-section, not the bbox edge's. Fit its
        # across-extent to the (already dilated) wall material at the
        # anchor samples it touches — the intersection over those samples,
        # so the plug stays connected to material at BOTH ends; a
        # perpendicular wall crossing one tail spans the whole probe and
        # constrains nothing, the jamb nib at the other end does. Never
        # wider than the legacy ±half-width (only ever shrinks), never
        # thinner than a line barrier. Without the fit a hinge-edge lying
        # on a band's inner face — where a swing leaf hinges — put the
        # plug's room-side edge half-width (5px) into the room against the
        # wall's own 2px standoff: a 3px step at every such doorway that
        # ROOM_SIMPLIFY_TOL_PX redrew as a slant over the whole room edge
        # (s03 BATHROOM room_0008: right edge 1183.8 at the door, 1186.7
        # below it, simplified to a 110px lean).
        half = gates.ROOM_PLUG_HALF_WIDTH_PX
        nx, ny = -uy, ux
        lo, hi = -half, half
        ends = (
            [i for i in range(n)
             if touch[i] and pos_a <= i * step <= pos_a + win * step],
            [i for i in range(n)
             if touch[i] and pos_b - win * step <= i * step <= pos_b],
        )
        for anchor_idx in ends:
            # Widest cross-section among this end's anchor samples: the
            # band body. A sample at the jamb's very end meets only a face
            # buffer's 4px sliver, and taking the narrowest (or the
            # intersection of all) would collapse the plug onto it.
            best: tuple[float, float] | None = None
            for i in anchor_idx:
                pt = edge_line.interpolate(i * step)
                probe = LineString([
                    (pt.x + nx * -half, pt.y + ny * -half),
                    (pt.x + nx * half, pt.y + ny * half),
                ])
                hit = probe.intersection(wall_material)
                if hit.is_empty:
                    continue
                bx0, by0, bx1, by1 = hit.bounds
                offs = [
                    (cx - pt.x) * nx + (cy - pt.y) * ny
                    for cx, cy in ((bx0, by0), (bx1, by1), (bx0, by1), (bx1, by0))
                ]
                cand = (min(offs), max(offs))
                if best is None or cand[1] - cand[0] > best[1] - best[0]:
                    best = cand
            if best is not None:
                lo, hi = max(lo, best[0]), min(hi, best[1])
        min_w = 2.0 * ROOM_LINE_BARRIER_PX
        if hi - lo < min_w:
            # Anchors disagree (or a corner graze): fall back to the full
            # band rather than a sliver that might not bridge them.
            lo, hi = -half, half
        centre = (lo + hi) / 2.0
        spine = translate(spine, nx * centre, ny * centre)
        plugs.append(
            (spine.buffer((hi - lo) / 2.0, cap_style=2), kind, edge_idx)
        )
    return plugs


def _folding_chain_gap_plug(
    candidate: Candidate, network: WallNetwork, wall_material,
    *, gates: RoomGates = ROOM_GATES_UNSCALED,
) -> Polygon | None:
    """Seal the doorway a PARKED folding chain leaves uncovered.

    A concertina drawn folded against one jamb has a bbox covering only the
    parked stack, never the opening it closes (GD2 on 5-1133: three ~74px
    leaves parked inside the kitchen against the south jamb of a 222px
    doorway — the bbox sits wholly beside the opening plane, so no plug edge
    can ever qualify there and the hallway leaks into the kitchen). The
    opening is recovered by the same span law the stack_pair detector uses:
    walking from a wall-segment end along the segment axis, the free gap
    before the next drawn wall material must equal the chain's total leaf
    run, and the stack must hug that gap axis. Both gap ends anchor on drawn
    wall material by construction — the plug carries the interrupted-run
    evidence the plug tier requires, never a bare stamp into free space.
    """
    ev = candidate.evidence
    leaf_run = ev.get("leaf_count", 0) * ev.get("panel_length_px", 0.0)
    if leaf_run <= 0:
        return None
    door_box = box(*candidate.bbox)
    best: tuple[float, Polygon] | None = None
    for s in network.segments:
        seg_len = _line_length(s.p1, s.p2)
        if seg_len < gates.ROOM_FOLD_JAMB_MIN_LEN_PX:
            continue
        for end, other in ((s.p1, s.p2), (s.p2, s.p1)):
            ux = (end[0] - other[0]) / seg_len
            uy = (end[1] - other[1]) / seg_len
            reach = leaf_run * (1.0 + ROOM_FOLD_SPAN_TOL)
            ray = LineString([
                (end[0] + ux * ROOM_FOLD_GAP_ESCAPE_PX,
                 end[1] + uy * ROOM_FOLD_GAP_ESCAPE_PX),
                (end[0] + ux * reach, end[1] + uy * reach),
            ])
            if ray.distance(door_box) > gates.ROOM_FOLD_STACK_NEAR_PX:
                continue
            hit = ray.intersection(wall_material)
            if hit.is_empty:
                continue
            gap = hit.distance(Point(end))
            dev = abs(gap - leaf_run) / leaf_run
            if dev > ROOM_FOLD_SPAN_TOL:
                continue
            if best is None or dev < best[0]:
                half = s.thickness_px / 2.0 + ROOM_WALL_DILATE_PX
                plug = LineString([
                    end, (end[0] + ux * gap, end[1] + uy * gap)
                ]).buffer(half, cap_style=2)
                best = (dev, plug)
    return best[1] if best else None


def _window_side_probes(
    candidate, *, gates: RoomGates = ROOM_GATES_UNSCALED,
) -> tuple[Polygon, Polygon] | None:
    """The two free-space probes on either side of a straight window.

    A window's bbox lies in its wall band; the spaces it separates start
    somewhere within a wall's thickness of the glazing on each side. Push
    the bbox out perpendicular to the glazing by WALL_MAX_THICKNESS_PX
    (plus the contact tolerance) — one probe per side. Diagonal windows
    have no axis to push along and get None.
    """
    if candidate.evidence.get("orientation") == "diagonal":
        return None
    x0, y0, x1, y1 = candidate.bbox
    reach = gates.WALL_MAX_THICKNESS_PX + ROOM_CONTACT_TOL_PX
    if (x1 - x0) >= (y1 - y0):
        return box(x0, y0 - reach, x1, y0), box(x0, y1, x1, y1 + reach)
    return box(x0 - reach, y0, x0, y1), box(x1, y0, x1 + reach, y1)


def _drop_window_exterior_sides(
    rooms: list[tuple[Polygon, dict]], windows: list[Candidate],
    *, gates: RoomGates = ROOM_GATES_UNSCALED,
) -> list[tuple[Polygon, dict]]:
    """Drop the door-less side of a window whose other side is entered.

    A window is a wall opening between inside and outside. When the space
    on one side of it is a door-bearing room and the space on the other
    side carries no door at all, the door-less side is the exterior the
    room looks out over — a lower roof, a terrace, a lightwell — not a
    room (measured on s03: the ground-floor roof, drawn as a striped field
    fenced by its outline above the PROPOSED BEDROOM, came out as a 133k
    px2 door-less "room" across the bedroom's window; a garage whose
    garage door reads as a window keeps its verdict because the far side
    is open ground, not a room). Two entered rooms sharing a borrowed
    light both stay; two door-less sides cannot be told apart and both
    stay. Complements the blind-window rule, which needs no far-side room
    but is capped to closet-scale pockets.
    """
    if not rooms or not windows:
        return rooms
    drop: set[int] = set()
    for w in windows:
        probes = _window_side_probes(w, gates=gates)
        if probes is None:
            continue
        sides: list[list[int]] = [[], []]
        for i, (poly, _info) in enumerate(rooms):
            hits = [
                k for k, probe in enumerate(probes)
                if poly.intersection(probe).area >= ROOM_WINDOW_SIDE_MIN_OVERLAP_PX2
            ]
            if len(hits) == 1:
                sides[hits[0]].append(i)
        for k in (0, 1):
            here, there = sides[k], sides[1 - k]
            if not here or not there:
                continue
            if any(rooms[j][1]["door_count"] > 0 for j in there):
                drop.update(i for i in here if rooms[i][1]["door_count"] == 0)
    return [r for i, r in enumerate(rooms) if i not in drop]


def _contains_text(comp, text_spans) -> bool:
    """A text span centred inside comp: a room label, a dimension — the
    draughtsperson named the space, so it is a space whatever its shape."""
    for t in text_spans or ():
        cx = (t.bbox[0] + t.bbox[2]) / 2.0
        cy = (t.bbox[1] + t.bbox[3]) / 2.0
        if comp.contains(Point(cx, cy)):
            return True
    return False


def _is_wall_recess(comp, wall_segments, opening_boxes, text_spans) -> bool:
    """True when comp lies in a wall band's plane — see ROOM_RECESS_GAP_COVER_MIN.

    Called only for components with no entrance and no window. Text inside
    the component (a room label, a dimension) marks a named space and vetoes
    the verdict outright.
    """
    if _contains_text(comp, text_spans):
        return False
    coords = list(comp.exterior.coords)
    for i, a in enumerate(wall_segments):
        len_a = _line_length(a.p1, a.p2)
        if len_a < 1e-6:
            continue
        ux = (a.p2[0] - a.p1[0]) / len_a
        uy = (a.p2[1] - a.p1[1]) / len_a
        nx, ny = -uy, ux
        for b in wall_segments[i + 1:]:
            if _line_length(b.p1, b.p2) < 1e-6:
                continue
            if _angle_diff_mod180(
                _line_angle_deg(a.p1, a.p2), _line_angle_deg(b.p1, b.p2)
            ) > WALL_PARALLEL_ANGLE_TOL:
                continue
            th = max(a.thickness_px, b.thickness_px)
            if _perpendicular_spacing(a.p1, a.p2, b.p1, b.p2) > th / 2.0:
                continue
            tb = sorted(
                (p[0] - a.p1[0]) * ux + (p[1] - a.p1[1]) * uy for p in (b.p1, b.p2)
            )
            if tb[0] > len_a:
                lo, hi = len_a, tb[0]
            elif tb[1] < 0.0:
                lo, hi = tb[1], 0.0
            else:
                continue                      # overlapping, not a gap
            if hi - lo < th:
                continue
            rect = Polygon([
                (a.p1[0] + ux * t + nx * w, a.p1[1] + uy * t + ny * w)
                for t, w in ((lo, -th / 2), (hi, -th / 2), (hi, th / 2), (lo, th / 2))
            ])
            if not rect.intersects(comp):
                continue
            if any(rect.intersects(o) for o in opening_boxes):
                continue
            if rect.intersection(comp).area < ROOM_RECESS_GAP_COVER_MIN * rect.area:
                continue
            ws = [(p[0] - a.p1[0]) * nx + (p[1] - a.p1[1]) * ny for p in coords]
            depth = max(ws) - min(ws)
            if depth > ROOM_RECESS_DEPTH_RATIO_MAX * th:
                continue
            # Back edge on the outer line: the component stops at the
            # barrier standoff inside one band edge.
            back = min(-th / 2.0 - min(ws), max(ws) - th / 2.0)
            if abs(back + ROOM_WALL_DILATE_PX) <= ROOM_RECESS_BACK_TOL_PX:
                return True
    return False


def _edge_face_cover(edge, face_lines) -> float:
    """How much of a component edge lies along a wall face: the largest
    projected overlap fraction over the faces parallel to the edge whose
    line sits at the barrier standoff (ROOM_LINE_BARRIER_PX, within
    ROOM_RECESS_BACK_TOL_PX) from it. 0.0 when no face runs beside it."""
    (ax, ay), (bx, by) = edge
    length = math.hypot(bx - ax, by - ay)
    if length < 1e-6:
        return 0.0
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
    angle = _line_angle_deg((ax, ay), (bx, by))
    best = 0.0
    for p1, p2 in face_lines:
        if _angle_diff_mod180(angle, _line_angle_deg(p1, p2)) > WALL_PARALLEL_ANGLE_TOL:
            continue
        standoff = abs((p1[0] - mx) * nx + (p1[1] - my) * ny)
        if abs(standoff - ROOM_LINE_BARRIER_PX) > ROOM_RECESS_BACK_TOL_PX:
            continue
        t1 = (p1[0] - ax) * ux + (p1[1] - ay) * uy
        t2 = (p2[0] - ax) * ux + (p2[1] - ay) * uy
        overlap = min(max(t1, t2), length) - max(min(t1, t2), 0.0)
        best = max(best, overlap / length)
    return best


def _is_band_pocket(
    comp, face_lines, text_spans, *, gates: RoomGates = ROOM_GATES_UNSCALED,
) -> bool:
    """True when comp lies INSIDE a wall band's thickness — see
    ROOM_BAND_POCKET_FACE_COVER_MIN.

    The recess rule's premise extended from "in the band's plane" to "inside
    the band": both long edges of the component's minimum rotated rectangle
    lie on wall faces (segment flanks or barrier faces) whose spacing is at
    most WALL_MAX_THICKNESS_PX — two faces that could have paired as one
    wall — so the free space between them is that wall's material (a window
    reveal, a hollow cavity, a blocked opening), not floor. Called only for
    components with no entrance and no window; text inside vetoes.
    """
    if _contains_text(comp, text_spans):
        return False
    with warnings.catch_warnings():
        # GEOS's oriented envelope divides by zero on some hull edges of an
        # irregular component and numpy reports it; the result is still a
        # valid rectangle (or a degenerate geometry, rejected below).
        warnings.simplefilter("ignore", RuntimeWarning)
        rect = comp.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        return False
    c = list(rect.exterior.coords)[:4]
    if len(c) < 4:
        return False
    edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    lens = [_line_length(a, b) for a, b in edges]
    if lens[0] >= lens[1]:
        long_edges, short = (edges[0], edges[2]), lens[1]
    else:
        long_edges, short = (edges[1], edges[3]), lens[0]
    # Face spacing = pocket width + the standoff on each side.
    if short + 2.0 * ROOM_LINE_BARRIER_PX > gates.WALL_MAX_THICKNESS_PX:
        return False
    return all(
        _edge_face_cover(e, face_lines) >= ROOM_BAND_POCKET_FACE_COVER_MIN
        for e in long_edges
    )


def _is_door_lining(poly: Polygon, material, openings: list[Polygon]) -> bool:
    """A stroked ring that continues the wall band up to an opening's bbox.

    A door LINING (frame block) is drawn as a small closed outline in the
    joinery pen, standing IN the wall band between the jamb face and the
    leaf: the structural opening is the leaf plus a lining each side (s04
    door_0002: 112px opening, 90px arc, 12.4px linings). It fails the
    wall-pen gate by construction, so it is admitted on position alone:
    the opening's bbox lies beside the ring along one axis (overlapping it
    across), and shifting the ring one ring-length along that axis AWAY
    from the opening lands it on drawn wall material whose across-axis
    span there matches the ring's own depth — the band the ring continues.
    A fixture box against a wall's room-side face beside a door shifts
    onto room floor; one wedged between a door and a perpendicular return
    wall shifts into that wall, but the wall spans the whole across probe.

    The band the ring continues is not always BEHIND it: a door hung at a
    wall junction has its jamb at the corner, so the lining there shifts
    into the perpendicular band, which spans the whole across probe exactly
    like the return wall a wedged fixture shifts into (s04 door_0001, the
    MASTER BEDROOM door, whose top jamb is the corner where the divider
    meets BATHROOM 02's bottom band: the 14.2x12.4px lining, path 949,
    shifted up lands in that band, 31.3px across against the 22.2px probe;
    its twin at the bottom jamb, path 946, shifts onto the divider — 18.2px
    — and is accepted; with the jamb 12.4px past the leaf bbox the doorway
    plug's anchor coverage was 3/7 and the dilated bbox fenced the swing
    square, -10,345 px2). A doorway is cut OUT of a wall, so the wall
    resumes beyond the far jamb whatever happens at the near one: the ring
    is a lining when the strip of its own across-range one to two ring
    depths past the opening's far edge — past the far jamb's twin lining —
    is that band, with the ring's own cross-section. The wedged fixture's
    across-range lies on the room side of the wall plane, and beyond the
    far jamb that strip is floor.
    """
    rx0, ry0, rx1, ry1 = poly.bounds
    w, h = rx1 - rx0, ry1 - ry0
    if w <= 0 or h <= 0:
        return False

    def _in_band(probe_poly, across, along_x):
        """probe_poly lies on drawn wall material whose span across the
        ring's axis matches the ring's own depth — the band the ring
        continues, not a wall running across the probe."""
        if probe_poly.intersection(material).area < (
            ROOM_LINING_IN_BAND_FRAC * probe_poly.area
        ):
            return False
        c = probe_poly.centroid
        reach = across + 2.0 * ROOM_WALL_DILATE_PX + ROOM_LINING_SPAN_TOL_PX
        if along_x:
            probe = LineString([(c.x, c.y - reach), (c.x, c.y + reach)])
        else:
            probe = LineString([(c.x - reach, c.y), (c.x + reach, c.y)])
        return probe.intersection(material).length <= reach

    for ob in openings:
        ox0, oy0, ox1, oy1 = ob.bounds
        y_ov = min(oy1, ry1) - max(oy0, ry0)
        x_ov = min(ox1, rx1) - max(ox0, rx0)
        # The opening's across-range must reach the ring: a swing bbox
        # spans the band when the hinge sits on the far face (s04) and
        # merely abuts it when the hinge sits on the near face. Each option
        # carries the shift away from the opening and the strip of the
        # ring's across-range one to two ring depths beyond the opening's
        # far edge.
        options = []
        if y_ov >= -ROOM_LINE_BARRIER_PX:
            options.append((abs(ox0 - rx1), (-w, 0.0), h,
                            box(ox1 + w, ry0, ox1 + 2.0 * w, ry1)))   # opening right
            options.append((abs(ox1 - rx0), (w, 0.0), h,
                            box(ox0 - 2.0 * w, ry0, ox0 - w, ry1)))   # opening left
        if x_ov >= -ROOM_LINE_BARRIER_PX:
            options.append((abs(oy0 - ry1), (0.0, -h), w,
                            box(rx0, oy1 + h, rx1, oy1 + 2.0 * h)))   # opening below
            options.append((abs(oy1 - ry0), (0.0, h), w,
                            box(rx0, oy0 - 2.0 * h, rx1, oy0 - h)))   # opening above
        if not options:
            continue
        gap, (dx, dy), across, far_strip = min(options, key=lambda t: t[0])
        if gap > ROOM_LINE_BARRIER_PX:
            continue
        along_x = bool(dx)
        if _in_band(translate(poly, dx, dy), across, along_x):
            return True
        if _in_band(far_strip, across, along_x):
            return True
    return False


def _accept_jamb_rings(
    rings, material_parts, doors, windows, door_zone_bounds, stroke_gate,
    is_wall_pen,
) -> list[Polygon]:
    """Dilated polygons of the stroked rings that are jamb blocks.

    Gates: penned at or above the lone-barrier stroke gate in a wall pen
    (fixture symbols are drawn lighter / in another colour), not lying
    fully inside a door zone (the open leaf and threshold share the
    small-closed-outline signature), and — the positional evidence —
    touching both drawn wall material and a confident opening's bbox. No
    proximity: a block one pixel short of the band is not a jamb.
    """
    if not rings:
        return []
    openings = [
        box(*c.bbox) for c in doors if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
    ] + [box(*c.bbox) for c in windows]
    if not openings or not material_parts:
        return []
    material = unary_union(material_parts)
    opening_union = unary_union(openings)
    accepted: list[Polygon] = []
    for r in rings:
        rx0, ry0, rx1, ry1 = r.poly.bounds
        if any(
            zx0 <= rx0 and rx1 <= zx1 and zy0 <= ry0 and ry1 <= zy1
            for zx0, zy0, zx1, zy1 in door_zone_bounds
        ):
            continue
        probe = r.poly.buffer(ROOM_LINE_BARRIER_PX)
        if not (probe.intersects(material) and probe.intersects(opening_union)):
            continue
        # Jamb nib: wall-penned. Door lining: joinery-penned, admitted on
        # position alone — it continues the band up to the opening.
        wall_penned = r.stroke_width >= stroke_gate and is_wall_pen(r.pen)
        if not wall_penned and not _is_door_lining(r.poly, material, openings):
            continue
        accepted.append(
            r.poly.buffer(
                ROOM_WALL_DILATE_PX, join_style=2, mitre_limit=ROOM_RING_MITRE_LIMIT,
            )
        )
    return accepted


def _free_space_components(page, barriers) -> list[Polygon]:
    """Free-space polygons of the page, morphologically opened.

    The opening (erode then dilate by ROOM_GAP_CLOSE_PX) removes free-space
    slivers thinner than ~2x the radius — the complement of closing the
    barrier union, computed per component. Opening is anti-extensive, so
    disjoint components can never re-merge; a component pinched thinner than
    the diameter splits, exactly as barrier closing would have sealed it.
    """
    free = page.difference(barriers)
    if free.is_empty:
        return []
    pieces = [free] if free.geom_type == "Polygon" else [
        g for g in free.geoms if g.geom_type == "Polygon"
    ]
    components: list[Polygon] = []
    for piece in pieces:
        opened = piece.buffer(-ROOM_GAP_CLOSE_PX, join_style=2).buffer(
            ROOM_GAP_CLOSE_PX, join_style=2
        )
        if opened.is_empty:
            continue
        if opened.geom_type == "Polygon":
            components.append(opened)
        else:
            components.extend(
                g for g in opened.geoms if g.geom_type == "Polygon"
            )
    return components


def _building_masses(solids, opening_union) -> list:
    """Connected wall-solid masses that plausibly belong to a building.

    Large masses qualify by size (a page can hold several plans). Small
    masses qualify when a detected door/window touches them — patchy solid
    coverage on heavy drawings splits a building's walls into many pieces.
    Legend tables and dimension frames form small, opening-free masses and
    drop out, taking their enclosed pseudo-rooms with them.
    """
    if solids.is_empty:
        return []
    masses = list(solids.geoms) if solids.geom_type == "MultiPolygon" else [solids]
    largest = max(m.area for m in masses)
    return [
        m for m in masses
        if m.area >= ROOM_MAJOR_MASS_FRAC * largest
        or (
            opening_union is not None
            and m.distance(opening_union) <= ROOM_MASS_TOUCH_TOL_PX
        )
    ]


def detect_rooms(
    network: WallNetwork | None,
    doors: list[Candidate],
    windows: list[Candidate],
    page_width_px: float,
    page_height_px: float,
    text_spans: list[TextSpan] | None = None,
    scale_factor: float = 1.0,
) -> list[Candidate]:
    gates = RoomGates.at(scale_factor)
    # WallGates.at(), not just RoomGates.at(): _bridge_white_runs is owned
    # by walls.py and its WALL_JOINERY_BRIDGE_GAP_PX field lives on
    # WallGates, not duplicated onto RoomGates (unlike WALL_MAX_THICKNESS_PX
    # / WALL_HATCH_MAX_LEN_PX, which rooms.py's own barrier-face logic reads
    # directly and so does carry local RoomGates fields) — this is the
    # minimal wiring that gets a scaled gates object to rooms' one call
    # into a walls.py helper.
    wall_gates = WallGates.at(scale_factor)
    if network is None or network.is_empty():
        return []

    # Annotation boxes detected as door leaves ("WALL TYPE 1" tags, note
    # frames) are identified by the text written inside them — the same
    # principle as the white text-mask rule in walls.py — and are fully
    # transparent to the room stage: no seals, no white-wall anchoring, no
    # face exclusion under their bbox.
    doors = [
        c for c in doors
        if _text_cover_frac(c.bbox, text_spans) < ROOM_OPENING_TEXT_COVER_MAX
    ]

    paired_indices = network.paired_face_indices()
    stroke_ref = network.wall_stroke_reference()
    stroke_gate = max(
        WALL_MIN_STROKE_WIDTH_PX, ROOM_BARRIER_STROKE_RATIO * stroke_ref
    )

    # Wall pens: the stroke colors that built the paired network. On
    # color-coded drawings annotation pens match the walls' WIDTH (or beat
    # it), so weight gates alone would admit every furniture and dimension
    # line; a pen whose color barely pairs did not draw the walls. None
    # (colorless/fill-outline geometry) always passes.
    pen_paired_len: dict[tuple, float] = {}
    for f in network.faces:
        if f.stroked and f.pen is not None and (f.indices & paired_indices):
            pen_paired_len[f.pen] = (
                pen_paired_len.get(f.pen, 0.0) + _line_length(f.p1, f.p2)
            )
    total_pen_len = sum(pen_paired_len.values())
    wall_pens = {
        pen for pen, length in pen_paired_len.items()
        if length >= ROOM_WALL_PEN_MIN_FRAC * total_pen_len
    }

    def _is_wall_pen(pen) -> bool:
        return pen is None or not total_pen_len or pen in wall_pens

    # Same-pen pairing in an annotation pen is furniture coincidence, not
    # wall: a pillow rectangle's opposite edges pair at wall-like spacing in
    # the furniture pen, and the resulting solid fences the bed's pillows
    # out of the bedroom (measured on floor-plans room_0012: two red-red
    # pillow-edge pairs, th 24/32px, notched the room outline around the
    # bed). A segment whose contributing faces are ALL plain stroked
    # non-wall-pen ink is dropped from the barrier solids; any wall evidence
    # on a member — wall fill, layer hint, material backing, an unstroked
    # (fill-outline/hairline) face, or merged wall-pen ink — keeps it.
    faces_by_path: dict[int, list] = {}
    for f in network.faces:
        for pi in f.indices:
            faces_by_path.setdefault(pi, []).append(f)

    def _wallish_face(f) -> bool:
        return (
            not f.stroked or _is_wall_pen(f.pen)
            or f.material_backed or f.wall_fill or f.layer_hint
        )

    def _furniture_segment(s) -> bool:
        member_faces = [
            f for pi in s.face_path_indices for f in faces_by_path.get(pi, ())
        ]
        return bool(member_faces) and not any(
            _wallish_face(f) for f in member_faces
        )

    wall_segments = [s for s in network.segments if not _furniture_segment(s)]

    solid_parts = [
        LineString([s.p1, s.p2]).buffer(
            s.thickness_px / 2.0 + ROOM_WALL_DILATE_PX, cap_style=2
        )
        for s in wall_segments
    ]
    # Wall-rated fill polygons are drawn wall area: they seal corner posts,
    # jamb stubs and band interiors that face pairing cannot represent.
    solid_parts += [
        poly.buffer(
            ROOM_WALL_DILATE_PX, join_style=2, mitre_limit=ROOM_RING_MITRE_LIMIT
        )
        for poly in network.fill_polygons
    ]
    # Thin barriers are ALLOWLISTED wall evidence, not all linework: a face
    # qualifies when it paired into a centerline, outlines a wall-rated fill,
    # sits on a wall layer, or is penned at least as heavily as the walls
    # (relative to the paired-wall stroke reference). Everything else — tile
    # grids, furniture outlines, sanitary symbols — is room-interior ink and
    # must not chop the free space. Hatch strokes are excluded even when
    # paired (their face pairs still contribute solids via network.segments),
    # but wall-fill outlines keep their short diagonal edges: a corner post
    # between two openings is wall material, not hatching. Faces fully inside
    # a door bbox — the open leaf, threshold lines — are excluded too: the
    # swing area is room floor and must not be slotted or fenced off.
    door_zone_bounds = [
        (c.bbox[0] - 2.0, c.bbox[1] - 2.0, c.bbox[2] + 2.0, c.bbox[3] + 2.0)
        for c in doors
    ]

    def _in_door_zone(a, b):
        return any(
            zx0 <= a[0] <= zx1 and zy0 <= a[1] <= zy1
            and zx0 <= b[0] <= zx1 and zy0 <= b[1] <= zy1
            for zx0, zy0, zx1, zy1 in door_zone_bounds
        )

    seg_by_path: dict[int, list] = {}
    for s in network.segments:
        for pi in s.face_path_indices:
            seg_by_path.setdefault(pi, []).append(s)
    # Doors that may carry a weak face's run across their opening as a
    # track/threshold line (_backed_extent): the plug-seal tier, never a
    # fallback-tier phantom.
    threshold_door_boxes = [
        box(*c.bbox)
        for c in doors if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
    ]

    def _paired_extent(f):
        """(fraction, bands): how much of the face run its own segments'
        bands cover, and the bands themselves (None when nothing paired)."""
        own = {id(s): s for pi in f.indices for s in seg_by_path.get(pi, ())}
        if not own:
            return 0.0, None
        line = LineString([f.p1, f.p2])
        if line.length <= 0:
            return 1.0, None
        bands = unary_union([
            LineString([s.p1, s.p2]).buffer(
                s.thickness_px / 2.0 + ROOM_WALL_DILATE_PX
            )
            for s in own.values()
        ])
        return line.intersection(bands).length / line.length, bands

    def _backed_extent(f, bands, gates):
        """The face run where it bounds wall material: its own bands, the
        sub-runs walls.py found hatch/blocking beside (backed_spans), and
        any remaining piece a confident door stands on — a sliding/garage
        door drawn closed is a panel plus its track or threshold line
        across the whole structural opening, and that line is the door's
        in-plane evidence the plug shadows (s02 GD5: 120px panel, 200px
        opening; the 74px of track beyond the panel is what seals the
        doorway). A plain remainder with neither — the joinery front of a
        built-in cupboard chained by the collinear merge onto the
        plaster-skin lines of the hatched bands either side (s02 "coats":
        369px face, paired 0.38, 210px of free-space run between the ends,
        no door) — seals nothing. Intervals are kept in 1-D along the face
        (px from p1): shapely's line-line difference does not subtract
        interpolated collinear pieces.
        """
        line = LineString([f.p1, f.p2])
        length = line.length
        if length <= 0:
            return None
        ux = (f.p2[0] - f.p1[0]) / length
        uy = (f.p2[1] - f.p1[1]) / length

        def _t(pt):
            return (pt[0] - f.p1[0]) * ux + (pt[1] - f.p1[1]) * uy

        kept: list[tuple[float, float]] = []
        if bands is not None:
            hit = line.intersection(bands)
            for piece in getattr(hit, "geoms", [hit]):
                if piece.is_empty or piece.geom_type != "LineString":
                    continue
                ts = sorted(_t(c) for c in piece.coords)
                kept.append((ts[0], ts[-1]))
        kept.extend((t0, t1) for t0, t1 in f.backed_spans if t1 > t0)
        kept.sort()
        merged: list[list[float]] = []
        for t0, t1 in kept:
            if merged and t0 <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], t1)
            else:
                merged.append([t0, t1])
        # The remainder: gaps between kept intervals. A piece a confident
        # door overlaps along the run (and lies within the plug-tail reach
        # of across it — the track is in the wall plane, the bbox is the
        # panel) is that door's threshold and is kept whole.
        edges = [0.0] + [t for iv in merged for t in iv] + [length]
        for i in range(0, len(edges), 2):
            t0, t1 = edges[i], edges[i + 1]
            if t1 - t0 <= 1e-6:
                continue
            piece = LineString([line.interpolate(t0), line.interpolate(t1)])
            for b in threshold_door_boxes:
                bt = [_t(c) for c in b.exterior.coords]
                if min(bt) < t1 and max(bt) > t0 and \
                        piece.distance(b) <= gates.ROOM_OPENING_SEAL_PX:
                    merged.append([t0, t1])
                    break
        if not merged:
            return None
        return unary_union([
            LineString([line.interpolate(t0), line.interpolate(t1)])
            for t0, t1 in merged if t1 - t0 > 1e-6
        ])

    def _barrier_extent(f, gates):
        """The part of a face that seals as a thin barrier (a shapely line
        geometry), or None when the face has no barrier rights."""
        line = LineString([f.p1, f.p2])
        if _in_door_zone(f.p1, f.p2):
            return None
        if (
            _line_length(f.p1, f.p2) <= gates.WALL_HATCH_MAX_LEN_PX
            and _is_diagonal_hatch_angle(_line_angle_deg(f.p1, f.p2))
            and not f.wall_fill
        ):
            return None
        if f.wall_fill or f.layer_hint:
            return line
        if f.material_backed:
            # A hatched band's lone drawn face: its own same-pen hatch is the
            # wall evidence (the partner face may be a jamb stub or a dashed
            # over-line, so neither pairing nor the lone pen gate can see it).
            return line
        if f.indices & paired_indices:
            # Same-pen furniture pairing (pillow rectangles, cabinet boxes)
            # grants no barrier rights — mirrors the segment filter above.
            if f.stroked and not _is_wall_pen(f.pen):
                return None
            if f.stroked and f.stroke_width >= stroke_gate:
                return line
            # Pairing is index-granular: a face qualifies even when one tiny
            # sliver of it paired, so a sub-gate face must earn full-length
            # status: its segments — which already seal as solids — covering
            # most of the run (ROOM_PAIRED_FACE_MIN_FRAC). A stroked face
            # (tile/paving pen) that falls short gets nothing. An UNSTROKED
            # face (material-backed hairline partition, fill outline) that
            # falls short keeps the run where it bounds wall material — its
            # bands, and the spans hatch lies beside (the partner face an
            # opening or text mask ate) — and loses the plain remainder.
            frac, bands = _paired_extent(f)
            if frac >= ROOM_PAIRED_FACE_MIN_FRAC:
                return line
            if f.stroked:
                return None
            return _backed_extent(f, bands, gates)
        if f.stroked and f.stroke_width >= stroke_gate and _is_wall_pen(f.pen):
            return line
        return None

    # Square caps: a barrier face's buffer extends half-width past its drawn
    # ends, meeting the perpendicular face or wall solid it butts against
    # flush instead of leaving a pen-width notch at every barrier-tier
    # transition corner (the notches survive the free-space opening — filling
    # them would be extensive — and simplification slants the steps).
    # face_lines: the wall faces a free-space component can lie along —
    # every barrier face's sealing extent, plus (below) both flanks of every
    # paired segment — what _is_band_pocket reads a band's thickness off.
    line_parts = []
    face_lines: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for f in network.faces:
        extent = _barrier_extent(f, gates)
        if extent is not None and not extent.is_empty:
            line_parts.append(extent.buffer(ROOM_LINE_BARRIER_PX, cap_style=3))
            for piece in getattr(extent, "geoms", [extent]):
                if piece.geom_type == "LineString" and len(piece.coords) >= 2:
                    face_lines.append(
                        (tuple(piece.coords[0]), tuple(piece.coords[-1]))
                    )

    # Hollow (white) walls and joinery runs: accept the candidate rings that
    # attach to wall material INCLUDING door/window bboxes — hollow runs are
    # interrupted by their openings, and without the bboxes the chain pieces
    # have nothing to anchor on. Accepted runs are then bridged across their
    # open spans (wardrobe fronts between divider boxes) with band-shaped
    # hulls so a joinery run bounds the room like the partition it is.
    # Fallback-tier doors are NOT anchors: a phantom door detected on a white
    # fixture symbol (a shower head beside a wall) must not turn the fixture
    # into wall and balloon the room outline around it.
    # The open leaf shares the white-rectangle signature: a thin band lying
    # along one edge of the swing bbox, anchored by its own door's bbox and
    # notching the swing area out of the room. A ring fully inside a
    # confident door's bbox is that leaf — real cavity segments run in the
    # wall band and extend past the bbox' wall-plane edge. Fallback-tier
    # doors get no such veto: they are typically detected ON white joinery
    # rectangles (wardrobe dividers), whose rings ARE the partition.
    # Withheld rings are remembered per door: a leaf drawn CLOSED lies in
    # the wall plane and may be the door's only plug evidence there
    # (timber gates in fence lines), so the plug stage gets to re-qualify
    # against it before falling back to the dilated bbox.
    # Sliding doors are exempt from the open-leaf veto: their panels lie in
    # the wall plane by construction (drawn closed across the opening, or
    # parked inside the wall pocket) — there is no swing square to notch out
    # of the room. Withholding them deletes the very partition the white-run
    # bridging seals the doorway with (a parked pair leaves half its doorway
    # outside the door bbox, so no plug can re-assert the missing span).
    withheld_leaves: list[tuple[BBox, Polygon]] = []
    if network.white_bands:
        leaf_zones = [
            zb for zb, c in zip(door_zone_bounds, doors)
            if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
            and c.evidence.get("assembly_type") != "sliding"
        ]

        def _is_open_leaf(r):
            rx0, ry0, rx1, ry1 = r.poly.bounds
            return any(
                zx0 <= rx0 and rx1 <= zx1 and zy0 <= ry0 and ry1 <= zy1
                for zx0, zy0, zx1, zy1 in leaf_zones
            )

        white_bands = []
        for r in network.white_bands:
            if _is_open_leaf(r):
                withheld_leaves.append((r.poly.bounds, r.poly))
            else:
                white_bands.append(r)
        anchor = unary_union(
            solid_parts + line_parts
            + [
                box(*c.bbox) for c in doors
                if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
            ]
            + [box(*c.bbox) for c in windows]
        )
        white_walls = _accept_white_walls(white_bands, anchor)
        solid_parts += [
            r.poly.buffer(
                ROOM_WALL_DILATE_PX, join_style=2,
                mitre_limit=ROOM_RING_MITRE_LIMIT,
            )
            for r in white_walls
        ]
        solid_parts += _bridge_white_runs(white_walls, gates=wall_gates)

    # Jamb nibs / door-stop blocks drawn as small closed STROKED outlines
    # in the wall pen (s03: 12x5px L-shapes with a rebate beside
    # door_0007/door_0019, every edge under the face floor) are wall
    # material when they sit where a jamb sits — touching drawn wall
    # material AND an opening's bbox. A fixture box of the same shape
    # (socket, cistern, tile) floats in the room or hugs a wall without an
    # opening; a ring fully inside a door zone is leaf/threshold ink.
    if network.stroked_rings:
        solid_parts += _accept_jamb_rings(
            network.stroked_rings, solid_parts + line_parts, doors, windows,
            door_zone_bounds, stroke_gate, _is_wall_pen,
        )

    solids = unary_union(solid_parts)
    wall_material = unary_union([solids] + line_parts)

    # Opening seals. Doors get thin plugs along their wall planes so the
    # swing area stays inside the room and neighbouring rooms split exactly
    # at the wall plane; the dilated-bbox fallback still seals when no plug
    # edge qualifies — but only for doors the heuristics themselves stand
    # behind, i.e. at >= ROOM_BBOX_SEAL_MIN_CONFIDENCE (the offline floor):
    # a door in the 0.40-0.55 band whose plug edges found no wall plane has
    # zero wall evidence at the bbox AND would be rejected by the pipeline —
    # it must not stamp free space (the 0.52 bath-fixture FP on 5-1133).
    # Fallback-tier doors (label boxes, glazing mullions, symbol
    # clutter — capped under the offline floor, kept only for Gemini
    # arbitration) seal solely through plugs carrying their own evidence:
    # an interrupted wall run (the doorway signature — a sliding door
    # between jambs still splits its rooms) or a drawn-through plane the
    # plug actually LIES IN (>= ROOM_PLUG_IN_WALL_FRAC of its area on drawn
    # wall material, so it only re-asserts existing barrier). Full coverage
    # merely NEAR wall material is how an annotation box hugging a wall
    # would otherwise stamp a free-space notch into the room outline.
    # Straight-window bboxes lie in the wall band, used as-is; diagonal
    # windows seal along their glazing band (_window_seal) because their
    # square axis bbox overhangs the wall plane on both sides.
    door_barriers = []
    for zone, c in zip(door_zone_bounds, doors):
        # The material a plug profile can read: every sample lies within
        # the tail's reach of the bbox and hugs material within
        # ROOM_PLUG_NEAR_PX. A seeking tail (_door_plugs) samples out to
        # the jamb cap plus its anchor window, so the clip is that far —
        # widening it is inert for every non-seeking rule (their
        # envelopes end at SEAL + NEAR = 23px, inside the old 27px clip).
        local = wall_material.intersection(
            box(*c.bbox).buffer(
                gates.ROOM_PLUG_JAMB_SEEK_PX + gates.ROOM_PLUG_ANCHOR_WIN_PX
                + ROOM_PLUG_NEAR_PX + 4.0,
                join_style=2,
            )
        )
        # A garden pair's parked-open leaves pin down two edges as room/garden
        # floor; those edges never take a plug, whatever their coverage
        # profile happens to pattern-match. A sliding door's short-end edges
        # cross the wall band and are vetoed the same way. Single swing
        # doors are further held to their hinge edges — the wall plane runs
        # through the hinge, so far-edge plugs only ever fence the swing
        # square out of its room.
        leaf_edges = _open_leaf_edges(c, gates=gates) | _sliding_end_edges(c)
        # A confident single swing's hinge-edge tails may seek a jamb the
        # fixed reach stops short of (_door_plugs, seek_edges).
        seeking = _seek_edges(c)
        plug_material = local
        plugs = _restrict_swing_plugs(
            c, _door_plugs(
                c.bbox, local, skip_edges=leaf_edges,
                seek_edges=seeking, gates=gates,
            )
        )
        if c.confidence < ROOM_OPENING_MIN_CONFIDENCE:
            plugs = [
                (p, kind, e) for p, kind, e in plugs
                if kind == "interrupted"
                or p.intersection(local).area >= ROOM_PLUG_IN_WALL_FRAC * p.area
            ]
        if not plugs and c.confidence >= ROOM_OPENING_MIN_CONFIDENCE:
            # No plug edge qualified on drawn wall material alone. Before
            # stamping the dilated bbox into free space, re-qualify with
            # the door's own withheld leaf rings: a leaf drawn closed IS
            # the wall plane (gates, panels), and its plug merely shadows
            # that ink — the swing square stays room floor.
            zx0, zy0, zx1, zy1 = zone
            leaves = [
                poly for (rx0, ry0, rx1, ry1), poly in withheld_leaves
                if zx0 <= rx0 and rx1 <= zx1 and zy0 <= ry0 and ry1 <= zy1
            ]
            if leaves:
                plug_material = unary_union([local] + leaves)
                plugs = _restrict_swing_plugs(c, _door_plugs(
                    c.bbox, plug_material,
                    skip_edges=leaf_edges, seek_edges=seeking, gates=gates,
                ))
        # Every plug is classified by now; end its tails at the material
        # they touch (an island's end, a band end) rather than up to a
        # plug half-width past it.
        plugs = _clip_plug_tails(c.bbox, plugs, plug_material, gates=gates)
        # A folding chain parked at its jamb never spans its own doorway, so
        # bbox-edge plugs cannot seal the opening plane — recover it via the
        # span law (gap between wall ends == total leaf run) and plug across.
        if (
            c.evidence.get("fold_style") == "chain"
            and c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
        ):
            gap_plug = _folding_chain_gap_plug(
                c, network, wall_material, gates=gates)
            if gap_plug is not None:
                plugs = plugs + [(gap_plug, "chain_gap", None)]
        if plugs:
            door_barriers.append((c.confidence, unary_union([p for p, _, _ in plugs])))
        elif c.confidence >= ROOM_BBOX_SEAL_MIN_CONFIDENCE:
            # The fallback stamps the door's wall-PLANE edges only — each
            # as the plug it would have carried, SEAL tails hugging their
            # jambs — never the far edges that bound the swing square, and
            # never SEAL across the plane into the far room (_plane_stamp).
            door_barriers.append((
                c.confidence,
                _plane_stamp(c, leaf_edges, plug_material, gates=gates),
            ))
    window_barriers = [_window_seal(c, gates=gates) for c in windows]
    opening_parts = [g for _, g in door_barriers] + window_barriers

    for s in wall_segments:
        length = _line_length(s.p1, s.p2)
        if length < 1e-6:
            continue
        nx = -(s.p2[1] - s.p1[1]) / length
        ny = (s.p2[0] - s.p1[0]) / length
        half = s.thickness_px / 2.0
        for sign in (1.0, -1.0):
            face_lines.append((
                (s.p1[0] + sign * nx * half, s.p1[1] + sign * ny * half),
                (s.p2[0] + sign * nx * half, s.p2[1] + sign * ny * half),
            ))

    # Drafting-gap sealing happens on the free-space side, inside
    # _free_space_components: buffering this union (one huge polygon with a
    # hole per room) has dropped legitimate holes wholesale (GEOS).
    barriers = unary_union([wall_material] + opening_parts)

    page = box(0.0, 0.0, page_width_px, page_height_px)
    page_area = page_width_px * page_height_px
    components = _free_space_components(page, barriers)

    # Contact/adjacency references. Openings count as wall contact: a door
    # plug sits exactly where the wall is interrupted.
    contact_ref = unary_union([solids] + opening_parts)
    opening_boxes = [box(*c.bbox) for c in doors] + [box(*c.bbox) for c in windows]
    door_geoms = [g for _, g in door_barriers]
    # Entrances: the seals of doors the pipeline stands behind. A rejected
    # candidate's plug still seals (its profile is its own evidence) and
    # still counts toward door_openings / confidence, but cannot vouch that
    # a pocket is entered (ROOM_ENTRANCE_MIN_CONFIDENCE).
    entrance_geoms = [
        g for conf, g in door_barriers if conf >= ROOM_ENTRANCE_MIN_CONFIDENCE
    ]
    window_geoms = window_barriers
    opening_union = unary_union(opening_parts) if opening_parts else None
    masses = _building_masses(solids, opening_union)

    # A free-space component fully inside a confident door's bbox is the
    # swing / threshold recess fenced off by the door's own seals (two
    # parallel plugs, or a plug plus a drawn-through threshold) — door floor
    # area, not a room. Measured on floor-plans: a garden pair in a cavity
    # wall plugs at the outer wall plane, and the 105x25px recess between
    # the cavity's inner face and the threshold line came out as its own
    # component. Fallback-tier doors get no dissolution power, consistent
    # with every other seal privilege.
    # Folding doors get a wall-band-deep zone: a parked stack stands off its
    # opening plane by the threshold depth (slot drain / blind-box zone on
    # 5-1133's kitchen CL doors), so the fenced recess between the stack
    # bbox and the wall band it serves falls outside the ⊕SEAL zone — still
    # doorway floor, never a room.
    swing_zones = [
        box(*c.bbox).buffer(
            gates.WALL_MAX_THICKNESS_PX
            if c.evidence.get("assembly_type") == "folding"
            else gates.ROOM_OPENING_SEAL_PX,
            join_style=2,
        )
        for c in doors
        if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
    ]

    rooms: list[tuple[Polygon, dict]] = []
    for comp in components:
        if comp.area < gates.ROOM_MIN_AREA_PX2:
            continue
        if comp.area > ROOM_MAX_PAGE_AREA_FRAC * page_area:
            continue
        if comp.exterior.distance(page.exterior) <= ROOM_BORDER_TOL_PX:
            continue
        if any(comp.within(z) for z in swing_zones):
            continue

        exterior = Polygon(comp.exterior)  # interior holes (fixtures) filled
        if exterior.area <= 0:
            continue
        hole_frac = (exterior.area - comp.area) / exterior.area
        if hole_frac > ROOM_HOLE_AREA_FRAC_MAX:
            continue
        if exterior.buffer(-ROOM_EROSION_PX).is_empty:
            continue

        boundary = exterior.exterior
        coords = list(boundary.coords)
        on_wall = sum(
            LineString([a, b]).length
            for a, b in zip(coords, coords[1:])
            if LineString([a, b]).distance(contact_ref) <= ROOM_CONTACT_TOL_PX
        )
        contact = on_wall / boundary.length if boundary.length > 0 else 0.0
        if contact < ROOM_WALL_CONTACT_MIN:
            continue
        if masses and all(
            comp.distance(m) > ROOM_MASS_TOUCH_TOL_PX for m in masses
        ):
            continue

        door_count = sum(
            1 for g in door_geoms if g.distance(boundary) <= ROOM_CONTACT_TOL_PX
        )
        entrance_count = sum(
            1 for g in entrance_geoms if g.distance(boundary) <= ROOM_CONTACT_TOL_PX
        )
        window_count = sum(
            1 for g in window_geoms if g.distance(boundary) <= ROOM_CONTACT_TOL_PX
        )
        wall_segment_count = sum(
            1 for s in wall_segments
            if LineString([s.p1, s.p2]).distance(boundary)
            <= s.thickness_px / 2.0 + ROOM_CONTACT_TOL_PX
        )
        # Blind-window pocket: reachable only through its window = the
        # exterior side of that window, not a room (see the constant).
        if (
            entrance_count == 0 and window_count > 0
            and comp.area < gates.ROOM_BLIND_WINDOW_MAX_AREA_PX2
        ):
            continue
        if entrance_count == 0 and window_count == 0:
            # Wall recess: an unentered, window-less, unlabelled pocket lying
            # in a band's plane is the wall's own material (chimney breast,
            # pier) — and one lying INSIDE a band's thickness, between two
            # faces at wall spacing, is the band itself (a window reveal).
            if _is_wall_recess(comp, wall_segments, opening_boxes, text_spans):
                continue
            if _is_band_pocket(exterior, face_lines, text_spans, gates=gates):
                continue
        rooms.append((exterior, {
            "contact": contact,
            "door_count": door_count,
            "window_count": window_count,
            "wall_segment_count": wall_segment_count,
            "holes": len(comp.interiors),
        }))

    rooms = _drop_window_exterior_sides(rooms, windows, gates=gates)
    rooms.sort(key=lambda t: (t[0].bounds[1], t[0].bounds[0]))

    candidates: list[Candidate] = []
    for idx, (poly, info) in enumerate(rooms):
        simplified = poly.simplify(ROOM_SIMPLIFY_TOL_PX, preserve_topology=True)
        exterior = [
            [round(x, 1), round(y, 1)] for x, y in simplified.exterior.coords
        ]

        confidence = ROOM_BASE_CONFIDENCE
        if info["door_count"]:
            confidence += ROOM_DOOR_BOUNDARY_BOOST
        if info["window_count"]:
            confidence += ROOM_WINDOW_BOUNDARY_BOOST
        confidence += ROOM_CONTACT_WEIGHT * info["contact"]
        confidence = round(min(max(confidence, 0.05), 0.95), 3)

        candidates.append(Candidate(
            candidate_id=f"room_{idx:04d}",
            entity_type="room",
            bbox=tuple(round(v, 1) for v in simplified.bounds),
            confidence=confidence,
            evidence={
                "polygon": exterior,
                "area_px2": round(simplified.area, 1),
                "perimeter_px": round(simplified.exterior.length, 1),
                "wall_segment_count": info["wall_segment_count"],
                "door_openings": info["door_count"],
                "window_openings": info["window_count"],
                "wall_contact": round(info["contact"], 3),
                "holes": info["holes"],
            },
        ))

    return candidates
