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

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from models import BBox, Candidate, TextSpan
from detection.geometry import _line_angle_deg, _line_length
from detection.walls import (
    WALL_HATCH_MAX_LEN_PX, WALL_MIN_STROKE_WIDTH_PX, WallNetwork,
    _accept_white_walls, _bridge_white_runs, _is_diagonal_hatch_angle,
)

# ---------------------------------------------------------------------------
# Room detection constants
# ---------------------------------------------------------------------------
ROOM_MIN_AREA_PX2           = 2500.0  # 50x50 px — smallest plausible closet at 150 DPI
ROOM_MAX_PAGE_AREA_FRAC     = 0.45    # components bigger than this are the sheet frame
ROOM_HOLE_AREA_FRAC_MAX     = 0.20    # mostly-hole components are frame-minus-building rings
ROOM_WALL_DILATE_PX         = 2.0     # wall-solid dilation; seals sub-4px face cracks
ROOM_LINE_BARRIER_PX        = 1.5     # half-width of thin line barriers (~pen width)
ROOM_BARRIER_STROKE_RATIO   = 0.66    # a lone stroked face becomes a thin barrier only
                                      # at >= this fraction of the paired-wall stroke
                                      # reference — tile grids, furniture outlines and
                                      # symbols are penned lighter than the walls
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
ROOM_PLUG_IN_WALL_FRAC      = 0.80    # min area fraction of a fallback-tier door's
                                      # full-cover plug overlapping drawn wall material:
                                      # such a plug only re-asserts existing barrier
                                      # ("costs nothing" made literal). Annotation boxes
                                      # floating NEAR a wall measure <= ~0.77 while
                                      # on-plane plugs measure 0.84+
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


def _door_plugs(bbox, wall_material) -> list[tuple[Polygon, str]]:
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
    free space and notch the room.
    """
    x0, y0, x1, y1 = bbox
    edges = [
        ((x0, y0), (x1, y0)),
        ((x0, y1), (x1, y1)),
        ((x0, y0), (x0, y1)),
        ((x1, y0), (x1, y1)),
    ]
    plugs: list[tuple[Polygon, str]] = []
    for p, q in edges:
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
        covered = [
            edge_line.interpolate(ext_len * i / (n - 1)).distance(wall_material)
            <= ROOM_PLUG_NEAR_PX
            for i in range(n)
        ]
        quarter = n // 4
        start_cov = sum(covered[:quarter]) / quarter
        end_cov = sum(covered[-quarter:]) / quarter
        # Trim the mid window by the hug distance: samples just inside an
        # open doorway still sit within ROOM_PLUG_NEAR_PX of the jamb corner
        # diagonally and must not count as mid coverage.
        trim = quarter + int(math.ceil(ROOM_PLUG_NEAR_PX / ROOM_PLUG_SAMPLE_PX))
        mid = covered[trim:n - trim] or covered[quarter:n - quarter]
        mid_cov = sum(mid) / len(mid)
        total_cov = sum(covered) / n
        if start_cov < ROOM_PLUG_END_COV_MIN or end_cov < ROOM_PLUG_END_COV_MIN:
            continue
        if not (
            total_cov >= ROOM_PLUG_FULL_COV_MIN
            or mid_cov <= ROOM_PLUG_MID_COV_MAX
        ):
            continue
        kind = "interrupted" if mid_cov <= ROOM_PLUG_MID_COV_MAX else "full"
        plugs.append(
            (LineString([a, b]).buffer(ROOM_PLUG_HALF_WIDTH_PX, cap_style=2),
             kind)
        )
    return plugs


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

    solid_parts = [
        LineString([s.p1, s.p2]).buffer(
            s.thickness_px / 2.0 + ROOM_WALL_DILATE_PX, cap_style=2
        )
        for s in network.segments
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

    paired_indices = network.paired_face_indices()
    stroke_ref = network.wall_stroke_reference()
    stroke_gate = max(
        WALL_MIN_STROKE_WIDTH_PX, ROOM_BARRIER_STROKE_RATIO * stroke_ref
    )

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
        if f.indices & paired_indices:
            return True
        return f.stroked and f.stroke_width >= stroke_gate

    line_parts = [
        LineString([f.p1, f.p2]).buffer(ROOM_LINE_BARRIER_PX, cap_style=2)
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
    withheld_leaves: list[tuple[BBox, Polygon]] = []
    if network.white_bands:
        leaf_zones = [
            zb for zb, c in zip(door_zone_bounds, doors)
            if c.confidence >= ROOM_OPENING_MIN_CONFIDENCE
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
    # behind. Fallback-tier doors (label boxes, glazing mullions, symbol
    # clutter — capped under the offline floor, kept only for Gemini
    # arbitration) seal solely through plugs carrying their own evidence:
    # an interrupted wall run (the doorway signature — a sliding door
    # between jambs still splits its rooms) or a drawn-through plane the
    # plug actually LIES IN (>= ROOM_PLUG_IN_WALL_FRAC of its area on drawn
    # wall material, so it only re-asserts existing barrier). Full coverage
    # merely NEAR wall material is how an annotation box hugging a wall
    # would otherwise stamp a free-space notch into the room outline.
    # Window bboxes lie in the wall band, used as-is.
    door_barriers = []
    for zone, c in zip(door_zone_bounds, doors):
        local = wall_material.intersection(
            box(*c.bbox).buffer(
                ROOM_OPENING_SEAL_PX + ROOM_PLUG_NEAR_PX + 4.0, join_style=2
            )
        )
        plugs = _door_plugs(c.bbox, local)
        if c.confidence < ROOM_OPENING_MIN_CONFIDENCE:
            plugs = [
                (p, kind) for p, kind in plugs
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
                plugs = _door_plugs(
                    c.bbox, unary_union([local] + leaves)
                )
        if plugs:
            door_barriers.append(unary_union([p for p, _ in plugs]))
        elif c.confidence >= ROOM_OPENING_MIN_CONFIDENCE:
            door_barriers.append(
                box(*c.bbox).buffer(ROOM_OPENING_SEAL_PX, join_style=2)
            )
    window_barriers = [box(*c.bbox) for c in windows]
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

    rooms: list[tuple[Polygon, dict]] = []
    for comp in components:
        if comp.area < ROOM_MIN_AREA_PX2:
            continue
        if comp.area > ROOM_MAX_PAGE_AREA_FRAC * page_area:
            continue
        if comp.exterior.distance(page.exterior) <= ROOM_BORDER_TOL_PX:
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
            1 for s in network.segments
            if LineString([s.p1, s.p2]).distance(boundary)
            <= s.thickness_px / 2.0 + ROOM_CONTACT_TOL_PX
        )
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
