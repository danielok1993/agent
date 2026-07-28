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

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from models import BBox, Candidate, TextSpan
from detection.geometry import _line_angle_deg, _line_length
from detection.walls import (
    WALL_HATCH_MAX_LEN_PX, WALL_MAX_THICKNESS_PX, WALL_MIN_STROKE_WIDTH_PX,
    WallNetwork,
    _accept_white_walls, _bridge_white_runs, _is_diagonal_hatch_angle,
)

# ---------------------------------------------------------------------------
# Room detection constants
# ---------------------------------------------------------------------------
ROOM_MIN_AREA_PX2           = 2500.0  # 50x50 px — smallest plausible closet at 150 DPI
ROOM_MAX_PAGE_AREA_FRAC     = 0.45    # components bigger than this are the sheet frame
ROOM_HOLE_AREA_FRAC_MAX     = 0.20    # mostly-hole components are frame-minus-building rings
ROOM_WALL_DILATE_PX         = 2.0     # wall-solid dilation; seals sub-4px face cracks
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
                                      # UNSTROKED paired faces are exempt — material-
                                      # backed hairline partitions are real walls with
                                      # legitimately partial pairing (0.13-0.36 where
                                      # openings/text ate the partner face)
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
ROOM_OPENING_SEAL_PX        = 12.0    # bbox-edge extension when building door plugs, and
                                      # bbox dilation on the plug fallback: bridges the
                                      # clearance between the swing bbox and the jambs so
                                      # free space cannot leak around a detected door
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
                                      # overlap the wall band it stands in for
ROOM_PLUG_END_COV_MIN       = 0.5     # min coverage of each end quarter: jambs (or the
                                      # wall the edge runs along) must anchor both ends
ROOM_PLUG_MID_COV_MAX       = 0.25    # mid coverage below this = interrupted wall run
                                      # (an open doorway between two jambs)
ROOM_PLUG_FULL_COV_MIN      = 0.75    # total coverage above this = wall plane drawn
                                      # through the opening (existing-opening sills,
                                      # closed sliding/garage door panels)
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


def _window_seal(candidate) -> Polygon:
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
    half_th = max(ROOM_PLUG_HALF_WIDTH_PX, (band.length - opening) / 2.0)
    return band.buffer(half_th, cap_style=2)


def _open_leaf_edges(candidate) -> frozenset[int]:
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
    tol = ROOM_PLUG_HALF_WIDTH_PX
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


def _door_plugs(
    bbox, wall_material, skip_edges=frozenset()
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
    edge; the caller falls back to the dilated bbox.

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
        a = (p[0] - ux * ROOM_OPENING_SEAL_PX, p[1] - uy * ROOM_OPENING_SEAL_PX)
        b = (q[0] + ux * ROOM_OPENING_SEAL_PX, q[1] + uy * ROOM_OPENING_SEAL_PX)
        ext_len = length + 2.0 * ROOM_OPENING_SEAL_PX
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
            int(math.ceil(ROOM_PLUG_ANCHOR_WIN_PX / ROOM_PLUG_SAMPLE_PX)) + 1,
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
        if start_cov < ROOM_PLUG_END_COV_MIN or end_cov < ROOM_PLUG_END_COV_MIN:
            continue
        # Interrupted run = jambs in the plane, nothing between them in the
        # plane. Both end windows must actually REACH the plug band (within
        # its half-width — the plug must connect to jamb material, not
        # float); a parallel band hugging the whole edge from beyond that
        # anchors both ends at the loose hug and touches nothing — the
        # profile of an annotation/fixture box beside a wall, not of a
        # doorway (measured: a real jamb solid ends 3.5px off the bbox edge
        # on floor-plans door_0008; the white-fixture phantom's parallel
        # band sits 6px off its bbox edge).
        touch = [d <= ROOM_PLUG_HALF_WIDTH_PX for d in dists]
        interrupted = (
            mid_cov <= ROOM_PLUG_MID_COV_MAX
            and any(touch[:win])
            and any(touch[-win:])
        )
        if not (total_cov >= ROOM_PLUG_FULL_COV_MIN or interrupted):
            continue
        kind = "interrupted" if interrupted else "full"
        plugs.append(
            (LineString([a, b]).buffer(ROOM_PLUG_HALF_WIDTH_PX, cap_style=2),
             kind, edge_idx)
        )
    return plugs


def _folding_chain_gap_plug(
    candidate: Candidate, network: WallNetwork, wall_material,
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
        if seg_len < ROOM_FOLD_JAMB_MIN_LEN_PX:
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
            if ray.distance(door_box) > ROOM_FOLD_STACK_NEAR_PX:
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
) -> list[Candidate]:
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
        poly.buffer(ROOM_WALL_DILATE_PX, join_style=2)
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

    def _paired_extent_frac(f):
        """Fraction of the face run covered by its own segments' bands."""
        own = {id(s): s for pi in f.indices for s in seg_by_path.get(pi, ())}
        if not own:
            return 0.0
        line = LineString([f.p1, f.p2])
        if line.length <= 0:
            return 1.0
        bands = unary_union([
            LineString([s.p1, s.p2]).buffer(
                s.thickness_px / 2.0 + ROOM_WALL_DILATE_PX
            )
            for s in own.values()
        ])
        return line.intersection(bands).length / line.length

    def _is_barrier_face(f):
        if _in_door_zone(f.p1, f.p2):
            return False
        if (
            _line_length(f.p1, f.p2) <= WALL_HATCH_MAX_LEN_PX
            and _is_diagonal_hatch_angle(_line_angle_deg(f.p1, f.p2))
            and not f.wall_fill
        ):
            return False
        if f.wall_fill or f.layer_hint:
            return True
        if f.material_backed:
            # A hatched band's lone drawn face: its own same-pen hatch is the
            # wall evidence (the partner face may be a jamb stub or a dashed
            # over-line, so neither pairing nor the lone pen gate can see it).
            return True
        if f.indices & paired_indices:
            # Same-pen furniture pairing (pillow rectangles, cabinet boxes)
            # grants no barrier rights — mirrors the segment filter above.
            if f.stroked and not _is_wall_pen(f.pen):
                return False
            # Pairing is index-granular: a face qualifies even when one tiny
            # sliver of it paired. Unstroked faces (material-backed hairline
            # partitions, fill outlines) keep that privilege — pairing plus
            # material IS their wall evidence. A stroked face penned under
            # the barrier gate (tile/paving pen) must instead earn full-
            # length status: its segments — which already seal as solids —
            # covering most of the run (ROOM_PAIRED_FACE_MIN_FRAC).
            if not f.stroked or f.stroke_width >= stroke_gate:
                return True
            return _paired_extent_frac(f) >= ROOM_PAIRED_FACE_MIN_FRAC
        return (
            f.stroked and f.stroke_width >= stroke_gate
            and _is_wall_pen(f.pen)
        )

    # Square caps: a barrier face's buffer extends half-width past its drawn
    # ends, meeting the perpendicular face or wall solid it butts against
    # flush instead of leaving a pen-width notch at every barrier-tier
    # transition corner (the notches survive the free-space opening — filling
    # them would be extensive — and simplification slants the steps).
    line_parts = [
        LineString([f.p1, f.p2]).buffer(ROOM_LINE_BARRIER_PX, cap_style=3)
        for f in network.faces
        if _is_barrier_face(f)
    ]

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
            r.poly.buffer(ROOM_WALL_DILATE_PX, join_style=2)
            for r in white_walls
        ]
        solid_parts += _bridge_white_runs(white_walls)

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
        local = wall_material.intersection(
            box(*c.bbox).buffer(
                ROOM_OPENING_SEAL_PX + ROOM_PLUG_NEAR_PX + 4.0, join_style=2
            )
        )
        # A garden pair's parked-open leaves pin down two edges as room/garden
        # floor; those edges never take a plug, whatever their coverage
        # profile happens to pattern-match. Single swing doors are further
        # held to their hinge edges — the wall plane runs through the hinge,
        # so far-edge plugs only ever fence the swing square out of its room.
        leaf_edges = _open_leaf_edges(c)
        plugs = _restrict_swing_plugs(
            c, _door_plugs(c.bbox, local, skip_edges=leaf_edges)
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
                plugs = _restrict_swing_plugs(c, _door_plugs(
                    c.bbox, unary_union([local] + leaves),
                    skip_edges=leaf_edges,
                ))
        # A folding chain parked at its jamb never spans its own doorway, so
        # bbox-edge plugs cannot seal the opening plane — recover it via the
        # span law (gap between wall ends == total leaf run) and plug across.
        if (
            c.evidence.get("fold_style") == "chain"
            and c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
        ):
            gap_plug = _folding_chain_gap_plug(c, network, wall_material)
            if gap_plug is not None:
                plugs = plugs + [(gap_plug, "chain_gap", None)]
        if plugs:
            door_barriers.append(unary_union([p for p, _, _ in plugs]))
        elif c.confidence >= ROOM_BBOX_SEAL_MIN_CONFIDENCE:
            door_barriers.append(
                box(*c.bbox).buffer(ROOM_OPENING_SEAL_PX, join_style=2)
            )
    window_barriers = [_window_seal(c) for c in windows]
    opening_parts = door_barriers + window_barriers

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
    door_geoms = door_barriers
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
            WALL_MAX_THICKNESS_PX
            if c.evidence.get("assembly_type") == "folding"
            else ROOM_OPENING_SEAL_PX,
            join_style=2,
        )
        for c in doors
        if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
    ]

    rooms: list[tuple[Polygon, dict]] = []
    for comp in components:
        if comp.area < ROOM_MIN_AREA_PX2:
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
            door_count == 0 and window_count > 0
            and comp.area < ROOM_BLIND_WINDOW_MAX_AREA_PX2
        ):
            continue
        rooms.append((exterior, {
            "contact": contact,
            "door_count": door_count,
            "window_count": window_count,
            "wall_segment_count": wall_segment_count,
            "holes": len(comp.interiors),
        }))

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
