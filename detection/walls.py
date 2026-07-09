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
from detection.layers import _layer_tokens

# ---------------------------------------------------------------------------
# Wall-network constants
# ---------------------------------------------------------------------------
WALL_MIN_STROKE_WIDTH_PX    = 0.5   # filters hairline hatch/dimension strokes
WALL_FACE_MIN_LEN_PX        = 12.0  # min wall piece between adjacent openings
WALL_FACE_MERGE_GAP_PX      = 6.0   # drafting artifacts only; door/window openings stay open
WALL_MIN_THICKNESS_PX       = 2.0   # thinnest partition at 150 DPI
WALL_MAX_THICKNESS_PX       = 36.0  # heavy exterior/party walls (a 1:50 blockwork
                                    # band runs ~32px); corridors are far wider
WALL_PARALLEL_ANGLE_TOL     = 4.0   # degrees, matches WINDOW_ANGLE_TOL_DEG
WALL_BAND_MIN_ASPECT        = 3.0   # filled rect must be band-like, not a fixture block
WALL_PAIR_MIN_OVERLAP_PX    = 12.0  # shorter face-pair overlap is coincidence
WALL_CENTERLINE_MERGE_GAP_PX = 8.0  # dedupe centerlines produced by multiple partner pairs
WALL_JUNCTION_SNAP_PX       = 8.0   # endpoint-to-intersection reach beyond partner thickness/2
WALL_JUNCTION_MIN_ANGLE_DEG = 10.0  # below this, line intersections are unstable (collinear-merge territory)
WALL_NETWORK_MIN_SEGMENTS   = 4     # below this the network is treated as empty everywhere

WALL_LAYER_KEYWORDS = ["wall", "a-wall", "partition", "struct"]

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
WALL_MARKER_MAX_SIDE_PX     = 24.0  # leader/dimension arrowheads are ~2-4mm
                                    # filled triangles (12-24px at 150 DPI) drawn
                                    # in the wall pen; rings this small with a
                                    # triangle or concave-dart outline are
                                    # annotation glyphs, never material

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
WALL_WEAK_MIN_RUN_PX         = 30.0  # min weak-pair centerline length: shorter
                                     # material-dense slivers are dimension-tick and
                                     # mullion clusters, and a real stub that short
                                     # sits between openings whose seals cover it
WALL_WEAK_MATERIAL_MIN_MARKS = 4     # short stubs (corner posts) still need a real X-block
WALL_WEAK_MATERIAL_MIN_SPAN  = 0.5   # marks must spread along the band, not clump at one end
WALL_WEAK_MATERIAL_PER_100PX = 3.0   # min diagonal marks per 100px of band length
WALL_WEAK_MATERIAL_ANGLE_MIN = 20.0  # stroke-vs-band-axis window; wide enough for the
WALL_WEAK_MATERIAL_ANGLE_MAX = 70.0  # ~25deg/~65deg diagonals of oblong blocking rects

# Tolerance for two segments to be considered on the same line.
COLLINEAR_ANGLE_TOL    = 3.0   # degrees
COLLINEAR_OFFSET_TOL   = 4.0   # px perpendicular distance between lines


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

    def is_band(self) -> bool:
        return (
            self.short <= WALL_MAX_THICKNESS_PX
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


def _collect_fill_rings(paths: list[PathPrimitive]) -> list[_FillRing]:
    """Chain consecutive same-fill `l` items (plus filled re/qu) into rings.

    extract_paths explodes each drawing in order, so a filled polygon's edges
    are consecutive primitives whose endpoints chain; any break in fill color
    or continuity closes the current chain. Background (white) rings are
    collected too — their shape decides mask vs hollow wall later.
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


def _rate_fill_classes(rings: list[_FillRing]) -> dict[tuple, bool]:
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
        entry[0 if r.is_band() else 1] += r.long

    return {
        key: band >= block
        for key, (band, block) in stats.items()
        if band + block >= WALL_FILL_CLASS_MIN_INK_PX
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
        if _is_background_fill(r.key) and r.short <= WALL_FILL_BLOCK_MAX_SIDE_PX
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


WALL_JOINERY_BRIDGE_GAP_PX      = 80.0  # max open span between accepted white
                                        # rings of one joinery/hollow-wall run
                                        # (open wardrobe fronts between boxes)
WALL_JOINERY_BRIDGE_SLACK_PX    = 8.0   # bridge hull may be this much thicker
                                        # than its fattest end ring — thicker
                                        # hulls mean the rings are not aligned


def _bridge_white_runs(accepted: list[_FillRing]) -> list:
    """Band-shaped convex hulls closing the gaps in accepted white-ring runs.

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
            elif gap <= WALL_JOINERY_BRIDGE_GAP_PX:
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


def _is_dashed(dashes: str) -> bool:
    """True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"."""
    if not dashes:
        return False
    inner = dashes.split("]")[0].strip("[ ").strip()
    return bool(inner)


def _wall_layer_hint(layer: str | None) -> bool:
    if not layer:
        return False
    tokens = _layer_tokens(layer)
    return any(kw in tokens for kw in WALL_LAYER_KEYWORDS)


def _collect_wall_faces(
    paths: list[PathPrimitive],
    fill_is_wall: dict[tuple, bool] | None = None,
    marker_indices: frozenset[int] | set[int] = frozenset(),
) -> tuple[list[_Seg], list[_Seg]]:
    """Return (stroked wall faces, filled-band centerlines)."""
    faces: list[_Seg] = []
    bands: list[_Seg] = []

    if fill_is_wall is None:
        rings = _collect_fill_rings(paths)
        fill_is_wall = _rate_fill_classes(rings)
        marker_indices = {
            i for r in rings if r.is_marker() for i in r.indices
        }

    def _wall_fill(p: PathPrimitive) -> bool:
        # Background (white) fills are masks or hollow walls — hollow walls
        # enter the network as polygons (detect_wall_network), never faces;
        # furniture-rated fill classes are cabinets and fixtures; unrated
        # fills keep the permissive legacy rule. Marker rings (arrowheads)
        # share the wall pen but are annotation — their edges never qualify.
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
        stroked = p.stroke_width >= WALL_MIN_STROKE_WIDTH_PX and not _is_dashed(p.dashes)
        filled_outline = _wall_fill(p)
        if p.item_type == "l" and len(p.points) >= 2 and (stroked or filled_outline):
            a, b = p.points[0], p.points[-1]
            if _line_length(a, b) < WALL_FACE_MIN_LEN_PX:
                continue
            faces.append(_Seg(
                p1=a, p2=b, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
                indices={p.path_index}, stroked=stroked,
                stroke_width=p.stroke_width if stroked else 0.0,
                wall_fill=filled_outline,
            ))
        elif p.item_type in ("re", "qu") and _wall_fill(p) and len(p.points) == 4:
            pts = p.points
            if p.item_type == "qu":
                # PyMuPDF quads are (ul, ur, ll, lr) — reorder to a sequential ring.
                pts = [pts[0], pts[1], pts[3], pts[2]]
            d01 = _line_length(pts[0], pts[1])
            d12 = _line_length(pts[1], pts[2])
            short, long_ = min(d01, d12), max(d01, d12)
            if not (WALL_MIN_THICKNESS_PX <= short <= WALL_MAX_THICKNESS_PX):
                continue
            if long_ < WALL_FACE_MIN_LEN_PX or short < 1e-6:
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


def _collect_weak_faces(paths: list[PathPrimitive]) -> list[_Seg]:
    """Hairline solid lines long enough to be wall pieces.

    Never faces on their own — detect_wall_network admits a weak pair only
    when the band between the faces carries wall material
    (_band_has_wall_material), so fixture outlines drawn in the same pen
    stay out of the network.
    """
    weak: list[_Seg] = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2 or p.fill is not None:
            continue
        if not (0.0 < p.stroke_width < WALL_MIN_STROKE_WIDTH_PX):
            continue
        if _is_dashed(p.dashes):
            continue
        a, b = p.points[0], p.points[-1]
        if _line_length(a, b) < WALL_FACE_MIN_LEN_PX:
            continue
        weak.append(_Seg(
            p1=a, p2=b, layer=p.layer, layer_hint=_wall_layer_hint(p.layer),
            indices={p.path_index}, stroked=False, stroke_width=0.0,
        ))
    return weak


def _collect_material_marks(
    paths: list[PathPrimitive],
) -> list[tuple[tuple[float, float], float]]:
    """(midpoint, angle) of every short solid stroke, gathered once per page.

    These are the strokes wall material is drawn with: hatch, cross-hatch,
    and the X diagonals of blocking rectangles. Which of them are diagonal
    is decided per band in _band_has_wall_material — diagonality is relative
    to the band axis, so angled walls read the same as axis-aligned ones.
    """
    marks: list[tuple[tuple[float, float], float]] = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2 or p.fill is not None:
            continue
        if _is_dashed(p.dashes):
            continue
        a, b = p.points[0], p.points[-1]
        if not (2.0 <= _line_length(a, b) <= WALL_HATCH_MAX_LEN_PX):
            continue
        marks.append(
            (((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0), _line_angle_deg(a, b))
        )
    return marks


def _band_has_wall_material(
    c: _Seg, marks: list[tuple[tuple[float, float], float]]
) -> bool:
    """True when the band under a centerline carries drawn wall material.

    Counts short strokes diagonal to the band axis whose midpoint lies inside
    the band, and requires them dense (WALL_WEAK_MATERIAL_PER_100PX) and
    spread along the band (WALL_WEAK_MATERIAL_MIN_SPAN) — a symbol clumped at
    one end of a long fixture run must not turn the whole run into wall.
    """
    length = _line_length(c.p1, c.p2)
    if length < 1e-6:
        return False
    ux = (c.p2[0] - c.p1[0]) / length
    uy = (c.p2[1] - c.p1[1]) / length
    axis_angle = _line_angle_deg(c.p1, c.p2)
    half = c.thickness / 2.0 + 1.0
    ts: list[float] = []
    for (mx, my), angle in marks:
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
    if len(ts) < (length / 100.0) * WALL_WEAK_MATERIAL_PER_100PX:
        return False
    return (max(ts) - min(ts)) >= WALL_WEAK_MATERIAL_MIN_SPAN * length


def _merge_collinear_segs(segs: list[_Seg], gap_px: float) -> list[_Seg]:
    """Merge segments lying on the same infinite line into runs.

    Bridges gaps up to gap_px; keeps the max thickness, unions path indices,
    and ORs layer hints across merged members.
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
                wall_fill=a.wall_fill,
            )

            for j, b in enumerate(merged):
                if j <= i or used[j]:
                    continue
                if _line_length(b.p1, b.p2) < 1e-6:
                    continue
                if _angle_diff_mod180(
                    _line_angle_deg(a.p1, a.p2), _line_angle_deg(b.p1, b.p2)
                ) > COLLINEAR_ANGLE_TOL:
                    continue

                # Perpendicular offset from a's line to b
                offset = abs((b.p1[0] - a.p1[0]) * (-uy) + (b.p1[1] - a.p1[1]) * ux)
                if offset > COLLINEAR_OFFSET_TOL:
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
                run.wall_fill = run.wall_fill or b.wall_fill
                run.thickness = max(run.thickness, b.thickness)
                if b.layer and not run.layer:
                    run.layer = b.layer
                used[j] = True
                changed = True

            ts = [_project_onto_axis(p, a.p1, ux, uy) for p in run_pts]
            t_lo, t_hi = min(ts), max(ts)
            run.p1 = (a.p1[0] + ux * t_lo, a.p1[1] + uy * t_lo)
            run.p2 = (a.p1[0] + ux * t_hi, a.p1[1] + uy * t_hi)
            out.append(run)
            used[i] = True

        merged = out

    return merged


def _pair_faces_to_centerlines(faces: list[_Seg]) -> list[_Seg]:
    """Every qualifying near-parallel face pair emits a centerline over the
    overlapped extent, carrying the face spacing as thickness.

    Unlike the retired detect_walls: no greedy one-partner pairing and no
    length-ratio gate — one long exterior face legitimately pairs with several
    short interior stubs. Duplicate centerlines collapse in the merge stage.
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
                if _angle_diff_mod180(
                    _line_angle_deg(fi.p1, fi.p2), _line_angle_deg(fj.p1, fj.p2)
                ) > WALL_PARALLEL_ANGLE_TOL:
                    continue
                spacing = _perpendicular_spacing(fi.p1, fi.p2, fj.p1, fj.p2)
                if not (WALL_MIN_THICKNESS_PX <= spacing <= WALL_MAX_THICKNESS_PX):
                    continue
                lo_i, hi_i = _projected_interval(fi.p1, fi.p2, ux, uy, fi.p1)
                lo_j, hi_j = _projected_interval(fj.p1, fj.p2, ux, uy, fi.p1)
                lo, hi = max(lo_i, lo_j), min(hi_i, hi_j)
                if hi - lo < WALL_PAIR_MIN_OVERLAP_PX:
                    continue

                # Midline: offset half the spacing from fi's line toward fj.
                nx, ny = -uy, ux
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


def _collapse_redundant_centerlines(segs: list[_Seg]) -> list[_Seg]:
    """Drop near-parallel centerlines that duplicate a longer one.

    Thick hatched walls carry more linework than their two faces (hatch
    boundaries, trim lines), so pairing emits several parallel centerlines a
    few px apart. Those redundant lines fragment the network with dangles and
    enclose thin strip faces that masquerade as rooms. Keep the longest line
    of each overlapping parallel group.
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


def detect_wall_network(
    paths: list[PathPrimitive], text_spans: list[TextSpan] | None = None,
) -> WallNetwork:
    """Build the internal wall-centerline network for a page."""
    rings = _collect_fill_rings(paths)
    fill_is_wall = _rate_fill_classes(rings)
    marker_indices = {i for r in rings if r.is_marker() for i in r.indices}
    faces, bands = _collect_wall_faces(paths, fill_is_wall, marker_indices)
    merged_faces = _merge_collinear_segs(faces, gap_px=WALL_FACE_MERGE_GAP_PX)

    # Sub-threshold (joinery-pen) partition walls: pair hairline faces too,
    # but keep a weak-involved pair only when the band between the faces
    # carries drawn wall material (hatch / cross-hatch / blocking X's). The
    # gate runs on the raw pairs, before centerline merging, so a weak pair
    # can never ride in on a strong run's coattails.
    weak_merged = _merge_collinear_segs(
        _collect_weak_faces(paths), gap_px=WALL_FACE_MERGE_GAP_PX
    )
    for f in weak_merged:
        f.weak = True

    centerlines = _pair_faces_to_centerlines(merged_faces + weak_merged)
    if weak_merged:
        marks = _collect_material_marks(paths)
        centerlines = [
            c for c in centerlines
            if not c.weak or (
                _line_length(c.p1, c.p2) >= WALL_WEAK_MIN_RUN_PX
                and _band_has_wall_material(c, marks)
            )
        ]
    weak_paired: set[int] = set()
    for c in centerlines:
        if c.weak:
            weak_paired |= c.indices

    centerlines += bands
    centerlines = _merge_collinear_segs(
        centerlines, gap_px=WALL_CENTERLINE_MERGE_GAP_PX
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
    face_lines = [
        WallFace(
            p1=f.p1, p2=f.p2, stroked=f.stroked, stroke_width=f.stroke_width,
            wall_fill=f.wall_fill, layer_hint=f.layer_hint,
            indices=frozenset(f.indices),
        )
        for f in merged_faces + weak_faces_kept + bands
    ]
    # Wall-rated fill rings are wall AREA, not just outlines: the polygons
    # seal band interiors, corner posts and jamb stubs whose sub-minimum
    # edges never became faces. Oversized blobs (shaded zones) stay
    # outline-only; marker rings (arrowheads in the wall pen) are annotation
    # and must not stamp notches into the free space.
    fill_polygons = [
        r.poly for r in rings
        if fill_is_wall.get(r.key, False)
        and r.short <= WALL_FILL_BLOCK_MAX_SIDE_PX
        and not r.is_marker()
    ]

    # Hollow (white) walls and joinery runs are only CANDIDATES here: shape
    # and text content prune the masks, but walls vs cabinet fronts is
    # settled by connectivity to wall material INCLUDING door/window
    # openings — which only room detection has (_accept_white_walls is
    # called from rooms.py, where hollow runs interrupted by windows still
    # anchor on the bboxes).
    white_bands = _white_wall_candidates(rings, text_spans or [])
    return WallNetwork(
        segments=segments, merged=merged, faces=face_lines,
        fill_polygons=fill_polygons, white_bands=white_bands,
    )
