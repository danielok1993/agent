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
WALL_THICK_MATERIAL_MAX_PX  = 48.0  # locally thickened masonry (chimney breast /
                                    # pier: floor-plans' bedroom pier bulges its
                                    # 19px wall to 39px; a 1:50 400mm band is
                                    # ~47px). Strong-face pairs in the 36-48px
                                    # gap form ONLY when the band between the
                                    # faces carries drawn wall material — an
                                    # unpaired pier encloses its hatch as a
                                    # free-space pocket = phantom room
WALL_PARALLEL_ANGLE_TOL     = 4.0   # degrees, matches WINDOW_ANGLE_TOL_DEG
WALL_BAND_MIN_ASPECT        = 3.0   # filled rect must be band-like, not a fixture block
WALL_PAIR_MIN_OVERLAP_PX    = 12.0  # shorter face-pair overlap is coincidence
WALL_CENTERLINE_MERGE_GAP_PX = 8.0  # dedupe centerlines produced by multiple partner pairs
WALL_JUNCTION_SNAP_PX       = 8.0   # endpoint-to-intersection reach beyond partner thickness/2
WALL_JUNCTION_MIN_ANGLE_DEG = 10.0  # below this, line intersections are unstable (collinear-merge territory)
WALL_NETWORK_MIN_SEGMENTS   = 4     # below this the network is treated as empty everywhere

WALL_LAYER_KEYWORDS = ["wall", "a-wall", "partition", "struct"]

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
WALL_WEAK_CLAIM_OVERLAP_FRAC = 0.5   # the inner pair must cover this fraction of the
                                     # weak pair's run — an inner stub elsewhere along a
                                     # long band says nothing about the material HERE

# Striped-field ("lattice") faces: paving bonds, tile fields, stair treads,
# roof tiling on elevations, table rows. A run of parallel SAME-PEN faces at
# equal wall-like pitch is never wall structure — rooms are wider than
# WALL_MAX_THICKNESS_PX by definition, so real walls cannot stack five deep
# at wall pitch. Pen weight cannot catch these: the open-vestibule paving
# bond on 5-1133 is penned at 1.05 vs the 1.50 wall reference (ratio 0.70,
# above WALL_WEAK_STROKE_RATIO), and the sample set has real wall pens down
# to 0.67 of the reference, so the ratio gate cannot be raised. Demoted
# lattice faces re-enter the weak (material-gated) pipeline, so a hatched
# partition that happens to sit inside a striped field still comes back.
WALL_LATTICE_MIN_RUNGS       = 5     # rungs per run; a 4-face cavity party wall
                                     # (leaf/cavity/leaf at equal width) stays wall
WALL_LATTICE_PITCH_TOL_PX    = 2.0   # rung pitch equality; also accepts one missing
                                     # rung (gap ~= 2x pitch, e.g. eaten by a text
                                     # mask — "VESTIBULE" ate the 1070.8 joint line)
WALL_LATTICE_MIN_RUNG_LEN_PX = 48.0  # total drawn length per rung, above
                                     # WALL_HATCH_MAX_LEN_PX so hatch strokes (which
                                     # are also parallel and equally pitched, one
                                     # short stroke per offset) never form rungs
WALL_LATTICE_TOUCH_GAP_PX    = 8.0   # rung extents must overlap or nearly touch the
                                     # run so far — staggered-bond joints on adjacent
                                     # courses meet end-to-end, while an unrelated
                                     # parallel face far along the axis is no rung
WALL_LATTICE_OFFSET_TOL_PX   = 1.5   # collinear pieces at one offset are one rung
WALL_LATTICE_PEN_TOL         = 0.05  # rungs must share a pen: a field is drawn in
                                     # one pen, while a wall face that happens to
                                     # run parallel nearby is penned as the walls
WALL_HATCH_MAX_PITCH_PX      = 8.0   # a striped field pitched this tightly is the
                                     # HATCH inside a wall band, and its rungs are
                                     # exempt from WALL_LATTICE_MIN_RUNG_LEN_PX.
                                     # That floor sits above WALL_HATCH_MAX_LEN_PX
                                     # so hatch can never fake a wall-pitch field —
                                     # but it also let real hatch keep FACE rights,
                                     # and two strokes of one field pair with each
                                     # other like any parallel pen mates. Inside a
                                     # straight band the phantom band hides in the
                                     # real one; at an L-corner it juts out (measured
                                     # on floor-plans: strokes 2502/2516 of the 45deg
                                     # field paired 28.1px apart into a diagonal
                                     # centerline that chamfered room_0000's and
                                     # room_0001's top-right corners by ~16px). The
                                     # pitch is what proves they are not walls: five
                                     # courses COEXISTING at <= this pitch span <=
                                     # 32px total, one band's worth
                                     # (WALL_MAX_THICKNESS_PX 36), so the lines are
                                     # that band's material, never five walls.
                                     # Measured: both reference PDFs' hatch fields
                                     # pitch at 4.05/4.07px, while the tightest real
                                     # striped field on either is 11.4px.

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
    WALL_PAIR_MIN_OVERLAP_PX: float
    WALL_FILL_CLASS_MIN_INK_PX: float
    WALL_FILL_BLOCK_MAX_SIDE_PX: float
    WALL_WEAK_MIN_RUN_PX: float
    WALL_LATTICE_MIN_RUNG_LEN_PX: float
    WALL_JOINERY_BRIDGE_GAP_PX: float
    WALL_HATCH_MAX_LEN_PX: float
    WALL_HATCH_MAX_PITCH_PX: float
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
            WALL_PAIR_MIN_OVERLAP_PX=WALL_PAIR_MIN_OVERLAP_PX * factor,
            WALL_FILL_CLASS_MIN_INK_PX=WALL_FILL_CLASS_MIN_INK_PX * factor,
            WALL_FILL_BLOCK_MAX_SIDE_PX=WALL_FILL_BLOCK_MAX_SIDE_PX * factor,
            WALL_WEAK_MIN_RUN_PX=WALL_WEAK_MIN_RUN_PX * factor,
            # WALL_HATCH_MAX_LEN_PX is also W and scales by the identical
            # factor, so the two stay exactly equal at every f (both 48.0
            # at f=1.0) — no cross-class floor needed (see
            # docs/scale-normalization-findings.md §4b).
            WALL_LATTICE_MIN_RUNG_LEN_PX=WALL_LATTICE_MIN_RUNG_LEN_PX * factor,
            WALL_JOINERY_BRIDGE_GAP_PX=WALL_JOINERY_BRIDGE_GAP_PX * factor,
            WALL_HATCH_MAX_LEN_PX=WALL_HATCH_MAX_LEN_PX * factor,
            WALL_HATCH_MAX_PITCH_PX=WALL_HATCH_MAX_PITCH_PX * factor,
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
    thick: bool = False                 # pair spacing beyond WALL_MAX_THICKNESS_PX
                                        # (thickened pier tier); only material-
                                        # backed pairs survive
    pen: tuple | None = None            # quantized stroke color; None = wildcard
                                        # (fill outlines, filled bands, centerlines)


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
    exclude_indices: frozenset[int] | set[int] = frozenset(),
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[list[_Seg], list[_Seg]]:
    """Return (stroked wall faces, filled-band centerlines)."""
    faces: list[_Seg] = []
    bands: list[_Seg] = []

    if fill_is_wall is None:
        rings = _collect_fill_rings(paths)
        fill_is_wall = _rate_fill_classes(rings, gates=gates)
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
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for mid, t1, t2, ang, tpen in grid.get((gx, gy), ()):
                    if tpen != pen:
                        continue
                    if _distance(mid, pt) > WALL_DIM_TICK_END_TOL_PX:
                        continue
                    rel = _angle_diff_mod180(ang, line_angle)
                    if not (
                        WALL_DIM_TICK_ANGLE_MIN <= rel <= WALL_DIM_TICK_ANGLE_MAX
                    ):
                        continue
                    off1 = (t1[0] - origin[0]) * (-uy) + (t1[1] - origin[1]) * ux
                    off2 = (t2[0] - origin[0]) * (-uy) + (t2[1] - origin[1]) * ux
                    if (
                        off1 * off2 < 0
                        and min(abs(off1), abs(off2))
                        >= WALL_DIM_TICK_STRADDLE_MIN_PX
                    ):
                        return True
        return False

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
        if not (2.0 <= _line_length(a, b) <= gates.WALL_HATCH_MAX_LEN_PX):
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


def _demote_lattice_faces(
    faces: list[_Seg], *, gates: WallGates = WALL_GATES_UNSCALED,
) -> tuple[list[_Seg], list[_Seg]]:
    """Split merged faces into (kept, striped-field members).

    A striped field is >= WALL_LATTICE_MIN_RUNGS parallel same-pen rungs at
    equal wall-like pitch (one missing rung tolerated as a 2x-pitch gap),
    each rung carrying enough drawn length to be structural linework rather
    than hatching, with rung extents chaining along the run. Paving bonds,
    tile fields, stair treads, roof tiling and table rows all match; wall
    structure cannot (rooms are wider than WALL_MAX_THICKNESS_PX). Members
    are demoted to the weak pipeline, not dropped: every pair they form —
    with each other or with a real wall's face — then needs drawn material
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
            rows: list[dict] = []
            for _, i, f in sorted(
                cluster,
                key=lambda t: (t[2].p1[0] + t[2].p2[0]) * nx / 2.0
                + (t[2].p1[1] + t[2].p2[1]) * ny / 2.0,
            ):
                mx = (f.p1[0] + f.p2[0]) / 2.0
                my = (f.p1[1] + f.p2[1]) / 2.0
                off = mx * nx + my * ny
                lo, hi = _projected_interval(f.p1, f.p2, ux, uy, (0.0, 0.0))
                if rows and off - rows[-1]["off"] <= WALL_LATTICE_OFFSET_TOL_PX:
                    r = rows[-1]
                    r["members"].append(i)
                    r["pieces"].append((lo, hi))
                    r["total"] += hi - lo
                    r["lo"] = min(r["lo"], lo)
                    r["hi"] = max(r["hi"], hi)
                else:
                    rows.append({
                        "off": off, "members": [i], "pieces": [(lo, hi)],
                        "total": hi - lo, "lo": lo, "hi": hi,
                    })
            # Two tiers over the same rows, scanned independently. The
            # structural tier catches wall-pitch fields and needs the rung
            # length floor to tell a paving course from a wall face. The
            # hatch tier catches fields pitched too tightly to BE walls, and
            # there the floor must not apply — it is precisely what keeps a
            # real hatch field's strokes in the strong pipeline.
            lattice |= _scan_striped_runs(
                rows,
                gates.WALL_LATTICE_MIN_RUNG_LEN_PX,
                gates.WALL_MAX_THICKNESS_PX + WALL_LATTICE_PITCH_TOL_PX,
                gates=gates,
            )
            lattice |= _scan_striped_runs(
                rows, 0.0, gates.WALL_HATCH_MAX_PITCH_PX, gates=gates,
            )

    kept = [f for i, f in enumerate(faces) if i not in lattice]
    demoted = [f for i, f in enumerate(faces) if i in lattice]
    return kept, demoted


def _scan_striped_runs(
    rows: list[dict],
    min_rung_len: float,
    max_pitch: float,
    *, gates: WallGates = WALL_GATES_UNSCALED,
) -> set[int]:
    """Face indices belonging to striped runs under one tier's thresholds.

    Rungs shorter than min_rung_len are ignored outright; runs chain while
    the pitch stays equal (one missing rung tolerated) and within max_pitch,
    and demote only when MIN_RUNGS of them also COEXIST along the axis.
    """
    demoted: set[int] = set()
    rungs = [r for r in rows if r["total"] >= min_rung_len]
    if len(rungs) < WALL_LATTICE_MIN_RUNGS:
        return demoted

    start = 0
    while start < len(rungs) - 1:
        pitch = rungs[start + 1]["off"] - rungs[start]["off"]
        if not (
            gates.WALL_MIN_THICKNESS_PX <= pitch <= max_pitch
        ) or _rungs_apart(rungs[start], rungs[start + 1]):
            start += 1
            continue
        run = [rungs[start], rungs[start + 1]]
        env_lo = min(rungs[start]["lo"], rungs[start + 1]["lo"])
        env_hi = max(rungs[start]["hi"], rungs[start + 1]["hi"])
        nxt = start + 2
        while nxt < len(rungs):
            gap = rungs[nxt]["off"] - run[-1]["off"]
            if (
                abs(gap - pitch) > WALL_LATTICE_PITCH_TOL_PX
                and abs(gap - 2.0 * pitch) > WALL_LATTICE_PITCH_TOL_PX
            ):
                break
            if (
                rungs[nxt]["lo"] - env_hi > WALL_LATTICE_TOUCH_GAP_PX
                or env_lo - rungs[nxt]["hi"] > WALL_LATTICE_TOUCH_GAP_PX
            ):
                break
            run.append(rungs[nxt])
            env_lo = min(env_lo, rungs[nxt]["lo"])
            env_hi = max(env_hi, rungs[nxt]["hi"])
            nxt += 1
        # Chained membership is not enough: distinct parallel wall bands
        # stacked at quasi-equal spacing chain too (measured on
        # s07: three 8px wall bands at 8-9px gaps
        # chained into a 5-rung "ladder" and deleted the plan's central wall
        # belt). A drawn FIELD has its courses side by side: somewhere along
        # the axis, MIN_RUNGS rungs coexist. Wall belts never stack that
        # deep — their rungs occupy disjoint spans that only envelopes glue
        # together.
        if (
            len(run) >= WALL_LATTICE_MIN_RUNGS
            and _max_rung_stack(run) >= WALL_LATTICE_MIN_RUNGS
        ):
            for r in run:
                demoted.update(r["members"])
        start = max(nxt - 1, start + 1)

    return demoted


def _rungs_apart(a: dict, b: dict) -> bool:
    """True when two rungs' extents neither overlap nor nearly touch."""
    return (
        b["lo"] - a["hi"] > WALL_LATTICE_TOUCH_GAP_PX
        or a["lo"] - b["hi"] > WALL_LATTICE_TOUCH_GAP_PX
    )


def _max_rung_stack(run: list[dict]) -> int:
    """Deepest simultaneous rung coverage along the run's axis.

    Sweeps the rungs' drawn pieces; ends sort before starts, so courses
    meeting end-to-end (staggered-bond joints on adjacent courses) never
    count as coexisting. Pieces within one rung are disjoint by
    construction, so piece coverage equals rung coverage.
    """
    events: list[tuple[float, int]] = []
    for r in run:
        for lo, hi in r["pieces"]:
            events.append((lo, 1))
            events.append((hi, -1))
    events.sort(key=lambda e: (e[0], e[1]))
    depth = deepest = 0
    for _, delta in events:
        depth += delta
        if depth > deepest:
            deepest = depth
    return deepest


def _merge_collinear_segs(
    segs: list[_Seg], gap_px: float, *, gates: WallGates = WALL_GATES_UNSCALED,
) -> list[_Seg]:
    """Merge segments lying on the same infinite line into runs.

    Bridges gaps up to gap_px; keeps the max thickness, unions path indices,
    and ORs layer hints across merged members.

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
                run.wall_fill = run.wall_fill or b.wall_fill
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
                if thick and (
                    not thick_tier
                    or spacing > gates.WALL_THICK_MATERIAL_MAX_PX
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
                    thick=thick,
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
    excluded = frozenset(exclude_path_indices or ()) | frozenset(
        _dimension_line_indices(paths, gates=gates)
    )
    rings = _collect_fill_rings(paths)
    fill_is_wall = _rate_fill_classes(rings, gates=gates)
    marker_indices = {i for r in rings if r.is_marker() for i in r.indices}
    faces, bands = _collect_wall_faces(
        paths, fill_is_wall, marker_indices, excluded, gates=gates
    )
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
        _collect_weak_faces(paths, excluded, gates=gates),
        gap_px=WALL_FACE_MERGE_GAP_PX, gates=gates,
    ) + demoted + lattice_faces + light_faces
    for f in weak_merged:
        f.weak = True

    marks = _collect_material_marks(paths, gates=gates)
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
                and _band_has_wall_material(c, marks, gates=gates)
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
        and r.short <= gates.WALL_FILL_BLOCK_MAX_SIDE_PX
        and not r.is_marker()
    ]

    # Hollow (white) walls and joinery runs are only CANDIDATES here: shape
    # and text content prune the masks, but walls vs cabinet fronts is
    # settled by connectivity to wall material INCLUDING door/window
    # openings — which only room detection has (_accept_white_walls is
    # called from rooms.py, where hollow runs interrupted by windows still
    # anchor on the bboxes).
    white_bands = _white_wall_candidates(rings, text_spans or [], gates=gates)
    return WallNetwork(
        segments=segments, merged=merged, faces=face_lines,
        fill_polygons=fill_polygons, white_bands=white_bands,
    )
