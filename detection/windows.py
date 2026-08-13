from __future__ import annotations
import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Iterator
from models import BBox, Candidate, PathPrimitive
from detection.geometry import (
    _bbox_union, _interval_overlap, _line_length,
    _line_angle_deg, _angle_diff_mod180, _project_onto_axis, _projected_interval,
)
from detection.layers import _layer_hint, _layer_strong_prior

# ---------------------------------------------------------------------------
# Window detection constants (cap-anchored model)
# ---------------------------------------------------------------------------
# A window opening is drawn as a pair of short perpendicular "cap" lines (the
# jambs) facing each other across the opening width, with one or more parallel
# "glazing" lines (the glass panes) spanning the gap between them. The cap pair
# is the only feature stable across drawing standards — the glazing-line count
# (1-3), spacing, and pane depth all vary by drafting style. So we anchor on the
# facing cap pair and treat the glazing band as confirmation, rather than
# clustering the (variable) glazing first. See
# docs/window-detection-tuning-guide.md for the topology reference and the
# ground truth (floor-plans.pdf + 5-1133-WD03.pdf) behind every constant.

WINDOW_ANGLE_TOL_DEG        = 4.0    # two lines within this are "the same direction"
                                     # (parallel glazing / parallel caps). Real glazing
                                     # bands measure within ~1deg; 4deg absorbs CAD noise
                                     # without merging distinct window angles in one frame.
WINDOW_ANGLE_GRID_DEG       = 2.0    # spacing of the overlapping cap-orientation frames;
                                     # <= tol so any two within-tol caps share a frame.
WINDOW_CAP_MIN_LEN_PX       = 3.0    # tiny caps exist (5-1133 bonus window: ~5px)
WINDOW_CAP_MAX_LEN_PX       = 36.0   # caps are short; longer perpendiculars are walls.
                                     # 5-1133 Window B caps overshoot to 30px; the
                                     # diagonal windows' jamb caps run the full wall
                                     # thickness ~34.7px (idx 6475/2301)
WINDOW_CAP_LEN_RATIO        = 0.60   # the two caps must be of similar length
WINDOW_CAP_ALIGN_OVERLAP    = 0.60   # their perp-extents must overlap (truly facing)
WINDOW_MIN_WIDTH_PX         = 14.0   # opening width (gap between caps); bonus ~20px
WINDOW_MAX_WIDTH_PX         = 280.0  # 5-1133 W8 (three-light frame) is 268px; caps
                                     # wall/decoration runs
WINDOW_GLAZING_THICKNESS_PX = 16.0   # max perp-spread of the glazing band (Window A ~14px)
WINDOW_GLAZING_ADJ_SPACING_PX = 8.5  # max gap between adjacent panes (Window B ~7.6px;
                                     # rejects stair treads / widely-spaced parallels)
WINDOW_GLAZING_DISTINCT_EPS = 1.5    # glazing lines closer than this in perp are one pane
WINDOW_MIN_GLAZING_LINES    = 2      # >=2 distinct parallel panes must span the gap
WINDOW_MIN_WIDTH_CAP_RATIO  = 1.5    # the opening must be wider than the jamb is long.
                                     # A band whose caps outrun its opening is a thin wall
                                     # slot / wall crossing, not a window (5-1133 FP
                                     # window_0006: width 15px vs 33px caps, ratio 0.46;
                                     # every true window has width/cap >= 2.58).
WINDOW_TWO_LINE_MIN_CAP_PX  = 12.0   # a 2-pane opening needs real jamb caps (wall-thickness,
                                     # ~20-30px) to outrank a thin wall / fixture sliver;
                                     # small-cap windows must show >=3 panes (5-1133 bonus)
WINDOW_TIGHT_PAIR_GAP_PX    = 2.75   # a 2-pane band whose panes hug each other closer than
                                     # this is ambiguous: it is either a narrow double
                                     # glazing line (floor-plans true windows: 1.75-2.0px)
                                     # or ONE doubled material edge — outline + fill-edge
                                     # strokes of a wall step, niche box, or detail layer
                                     # boundary (every 5-1133 FP of this shape: 1.6-2.5px).
                                     # The gap alone cannot separate them (the ranges
                                     # overlap), so tight pairs face the interior test
                                     # below. Pairs >= this gap are real pane pairs
                                     # (5-1133 diagonal W 3.5; floor-plans 3.25/3.3) and
                                     # 3-pane bands are exempt entirely — repeated equal
                                     # spacing is already the glazing signature (true
                                     # 3-pane bands run as tight as 1.5px).
WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX = 1.5  # a tight pane pair must run INTERIOR to both jamb
                                     # caps with at least this much cap extending beyond
                                     # the band on BOTH sides: glass sits inside the wall,
                                     # so each jamb overshoots the glass line (floor-plans
                                     # true tight pairs: 4.3-8.6px in every orientation
                                     # frame). A doubled material edge terminates AT its
                                     # box/step corners, so the cap ends exactly at the
                                     # outer stroke — every 5-1133 FP reading measures
                                     # <= 0.0px margin in every frame. Mere overlap can't
                                     # separate the two (a corner-exact cap overlaps the
                                     # band fully); the beyond-band margin can.
WINDOW_SPAN_COVER_TOL_PX    = 4.0    # a glazing line may fall short of each cap by this
WINDOW_SPAN_OVERSHOOT_PX    = 11.0   # ...and run at most this far PAST each cap (walls run
                                     # hundreds past). Measured 2026-08-13 through the inert
                                     # sweep tap (findings §4e): confirmed windows' overshoot
                                     # tails reach 10.50px (s02 diagonal w) with p90 8.77,
                                     # while the s12/s18/s20 phantom-window families sit at
                                     # 11.75-11.98px — 11.0 splits the gap with margin both
                                     # ways (any value in (10.50, 11.75) behaves identically).
WINDOW_SPAN_PERP_TOL_PX     = 2.0    # glazing perp may sit this far outside the cap extent
WINDOW_MIN_CONFIDENCE       = 0.50

# ---------------------------------------------------------------------------
# Band-interior clutter gate (hatched-wall rejection)
# ---------------------------------------------------------------------------
# A real window's glazing band is clear glass: nothing sits BETWEEN the panes.
# Insulation-hatched walls, on the other hand, get read as a 2-line band whose
# two "panes" are the wall's two faces (rails) — and the crosshatch fill sits
# right between them. So we measure clutter only in the band interior: the
# oriented rectangle spanning u (between the caps) x v (across the pane band).
# This region is the key to not regressing DIAGONAL windows: their loose
# axis-aligned bbox would sweep in neighbouring linework, and their gray jamb
# caps are re/qu/c FILLED shapes — but those sit at the opening ENDS (outside
# the u-span between the caps), not between the panes, so they never count here.
# Anchored on 5-1133 page-1 ground truth: every true window (axis + diagonal)
# scores <=1 shape / 0 oblique between its panes; the hatched-wall FPs score
# 2-7 shapes (crosshatch boxes/arcs) and up to 2 oblique line strokes.
#
# The OTHER page-1 FPs — solid-filled wall steps, the "recess" niche, the
# detail-corner notch and the RWP corner square — carry their distinguishing
# clutter at the opening ends, exactly where real diagonal windows carry their
# filled jambs, so no interior-geometry gate separates them without killing the
# diagonals. They fall instead to the tight-pair interior gate
# (WINDOW_TIGHT_PAIR_GAP_PX / WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX): each reads two
# strokes of ONE material edge as a 2-pane band, and that band terminates at
# the END of its caps (a box corner) instead of running interior to both jambs
# the way a real narrow double-glazing line does. Colour/fill-brightness would
# also separate them but is not uniform across PDFs, so we don't use it.
WINDOW_INTERIOR_BAND_PAD_PX = 1.5  # widen the pane band by this (per side) along v before scanning,
                                   # so a rail drawn a hair outside the band still bounds the hatch.
WINDOW_INTERIOR_SHAPE_MAX   = 1    # non-line primitives (re/qu/c) between the panes: >1 ⇒ crosshatch
                                   # /insulation fill. True windows: <=1 (a stray jamb-corner poke).
WINDOW_INTERIOR_OBLIQUE_MAX = 2    # lines between the panes parallel to neither glazing nor caps:
                                   # line-drawn hatch. True windows: 0 (defends line-only hatch).

# ---------------------------------------------------------------------------
# Framed multi-light windows (block caps + mullion-bridged glazing)
# ---------------------------------------------------------------------------
# Some frames (5-1133 W8, a triple window tagged with one label) draw the jambs
# and mullions as small bar-shaped re/qu OUTLINES instead of cap lines, and the
# center glazing line in per-light segments interrupted by the mullion blocks.
# Block caps are promoted into the cap pool via their oriented long axis; the
# segmented center line is re-joined into one logical pane, but ONLY across a
# gap a mullion block actually occupies — a dashed line's gaps hold nothing, so
# dashes can never chain into phantom glazing.
WINDOW_BLOCK_CAP_MAX_THICK_PX = 8.0   # bar thickness (W8 end caps 6.0, mullions 5.5)
WINDOW_BLOCK_CAP_MIN_ASPECT   = 1.8   # long/short side; square crosshatch/insulation
                                      # boxes (~1.0-1.4) never become caps
WINDOW_MULLION_GAP_MAX_PX     = 14.0  # max glazing-segment gap a mullion may bridge
                                      # (W8 gaps are 11.5px)
WINDOW_BLOCK_CAP_CROSS_RATIO  = 0.75  # a line >= this fraction of the block's diagonal
                                      # with both endpoints inside its bbox is an X
                                      # stroke: the block is a crossed post/column
                                      # symbol (the 5-1133 shower-screen end post),
                                      # never a window jamb


@dataclass(frozen=True)
class WindowGates:
    """World-space window gates, pre-multiplied by the detection factor.

    Exactly ONE field: the frozen classification
    (docs/scale-normalization-findings.md §4e, measured 2026-08-13) found the
    window symbol's internal ink geometry — band depth, pane spacing, cap
    stroke lengths, span overshoots — to be paper-space (the INVERSE of
    doors), leaving the opening's empty-space extent floor as the only
    constant that scales. Paper-space and dimensionless constants
    deliberately have NO field here; absence is the audit trail. At factor
    1.0 the field equals its module constant exactly.
    """
    factor: float
    WINDOW_MIN_WIDTH_PX: float

    @classmethod
    def at(cls, factor: float) -> "WindowGates":
        assert factor > 0, "scale factor must be positive"
        # Floor mirrors DOOR_MIN_SIZE_PX's: raw product 3.5px at the f=0.25
        # clamp bound, so the floor is inert on the calibrated domain.
        return cls(factor=factor,
                   WINDOW_MIN_WIDTH_PX=max(1.0, WINDOW_MIN_WIDTH_PX * factor))


WINDOW_GATES_UNSCALED = WindowGates.at(1.0)


# Cell size for the two page-wide lookup grids below (the block-cap cross test
# and the band-interior clutter scan). Not a tunable: it only trades cells
# visited against records per cell, never which records pass the exact tests.
_GRID_PX = 64.0


def _line_records(paths: list[PathPrimitive]) -> list[dict]:
    """All straight line primitives with endpoints, length and direction.

    Direction (``angle``, mod 180 deg) lets us group parallel lines and find
    perpendiculars regardless of the page axes — windows are drawn at any angle,
    so detection works in a rotated frame rather than the x/y axes.
    """
    recs: list[dict] = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2:
            continue
        a, b = p.points[0], p.points[-1]
        length = _line_length(a, b)
        if length < 1e-6:
            continue
        recs.append({"path": p, "a": a, "b": b, "len": length,
                     "angle": _line_angle_deg(a, b)})
    return recs


def _block_cap_records(paths: list[PathPrimitive]) -> list[dict]:
    """Cap records from small bar-shaped ``re``/``qu`` primitives.

    Framed windows (5-1133 W8) draw their jamb end caps and mullions as thin
    quad/rect outlines rather than cap lines. Each bar is reduced to its long
    axis — the segment joining the midpoints of its two short edges — so it
    flows through the same orientation frames and pairing as a line cap. The
    short edges are found by pairwise distance (shortest disjoint pairs), so
    point ordering and rotation don't matter. The aspect gate keeps square-ish
    crosshatch/insulation boxes out of the cap pool; the cross gate drops
    X-ed blocks — a crossed box is a post/column symbol (the 5-1133 bathroom
    shower-screen end post), not a jamb.
    """
    # A cross stroke has BOTH endpoints inside the block's bbox +- 1px, so it
    # lies entirely inside a box no wider than the block itself. Bucketing the
    # page's lines by their first endpoint means the cross test only looks at
    # the handful of cells that box touches, instead of walking every path once
    # per bar candidate.
    grid: dict[tuple[int, int], list[tuple[float, float, float, float, float]]] = {}
    for q in paths:
        if q.item_type != "l" or len(q.points) < 2:
            continue
        (ax, ay), (bx, by) = q.points[0], q.points[-1]
        grid.setdefault((int(ax // _GRID_PX), int(ay // _GRID_PX)), []).append(
            (ax, ay, bx, by, _line_length((ax, ay), (bx, by))))

    def crossed(p: PathPrimitive, diag: float) -> bool:
        x0, y0, x1, y1 = p.bbox
        lo_x, hi_x = x0 - 1.0, x1 + 1.0
        lo_y, hi_y = y0 - 1.0, y1 + 1.0
        need = WINDOW_BLOCK_CAP_CROSS_RATIO * diag
        for cx in range(int(lo_x // _GRID_PX), int(hi_x // _GRID_PX) + 1):
            for cy in range(int(lo_y // _GRID_PX), int(hi_y // _GRID_PX) + 1):
                for ax, ay, bx, by, length in grid.get((cx, cy), ()):
                    if (lo_x <= ax <= hi_x and lo_y <= ay <= hi_y
                            and lo_x <= bx <= hi_x and lo_y <= by <= hi_y
                            and length >= need):
                        return True
        return False

    recs: list[dict] = []
    for p in paths:
        if p.item_type not in ("re", "qu") or len(p.points) < 4:
            continue
        pts = p.points[:4]
        i, j = min(((i, j) for i in range(4) for j in range(i + 1, 4)),
                   key=lambda ij: _line_length(pts[ij[0]], pts[ij[1]]))
        k, l = (n for n in range(4) if n not in (i, j))
        thick = (_line_length(pts[i], pts[j]) + _line_length(pts[k], pts[l])) / 2
        a = ((pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2)
        b = ((pts[k][0] + pts[l][0]) / 2, (pts[k][1] + pts[l][1]) / 2)
        length = _line_length(a, b)
        if not (WINDOW_CAP_MIN_LEN_PX <= length <= WINDOW_CAP_MAX_LEN_PX):
            continue
        if thick < 1e-6 or thick > WINDOW_BLOCK_CAP_MAX_THICK_PX:
            continue
        if length / thick < WINDOW_BLOCK_CAP_MIN_ASPECT:
            continue
        if crossed(p, math.hypot(length, thick)):
            continue
        recs.append({"path": p, "a": a, "b": b, "len": length,
                     "angle": _line_angle_deg(a, b), "block": True})
    return recs


def _cap_orientation_frames(cap_recs: list[dict]) -> list[tuple[float, list[dict]]]:
    """Caps grouped by direction into overlapping frames, each ``(center, caps)``.

    Caps (the jambs) run parallel to each other; their shared direction defines
    the opening's coordinate frame. A *disjoint* clustering is fragile: a dense
    spread of cap angles (curves, hatches, fixtures all over a page) chains into
    one cluster that then splits at an arbitrary boundary — and a window's two
    near-parallel caps (e.g. 45.0 deg and 46.3 deg) can land on opposite sides,
    so they never get paired. Instead we sweep fixed grid centers every
    WINDOW_ANGLE_GRID_DEG and assign each cap to every center within
    WINDOW_ANGLE_TOL_DEG. Centers are spaced <= tol, so any two caps within tol
    of each other co-occur in at least one frame; the duplicate openings the
    overlap produces collapse in _dedupe_openings. Frames with <2 caps are
    dropped — an opening needs two facing caps.
    """
    frames: list[tuple[float, list[dict]]] = []
    center = 0.0
    while center < 180.0:
        members = [r for r in cap_recs
                   if _angle_diff_mod180(r["angle"], center) <= WINDOW_ANGLE_TOL_DEG]
        if len(members) >= 2:
            frames.append((center, members))
        center += WINDOW_ANGLE_GRID_DEG
    return frames


def _frame_axes(cap_angle_deg: float) -> tuple[float, float, float, float]:
    """Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).

    Caps run along their own direction; the opening width and the glazing lines
    run perpendicular to the caps. So u = cap_angle + 90 deg, v = cap_angle.
    """
    ur = math.radians(cap_angle_deg + 90.0)
    ux, uy = math.cos(ur), math.sin(ur)
    return ux, uy, -uy, ux  # u, then v = (-uy, ux)


def _glaze_record(r: dict, ux: float, uy: float, vx: float, vy: float) -> dict:
    """Record for a glazing line: ``perp`` = depth offset (along v), ``span`` =
    extent along the opening (u). Glazing runs along u (perpendicular to caps)."""
    mid = ((r["a"][0] + r["b"][0]) / 2, (r["a"][1] + r["b"][1]) / 2)
    return {"idx": r["path"].path_index, "path": r["path"], "len": r["len"],
            "perp": _project_onto_axis(mid, (0.0, 0.0), vx, vy),
            "span": _projected_interval(r["a"], r["b"], ux, uy, (0.0, 0.0))}


def _cap_record(r: dict, ux: float, uy: float, vx: float, vy: float) -> dict:
    """Record for a cap line: ``perp`` = position along the opening (u), ``span``
    = the cap's own extent (along v). Caps run along v (their own direction)."""
    mid = ((r["a"][0] + r["b"][0]) / 2, (r["a"][1] + r["b"][1]) / 2)
    return {"idx": r["path"].path_index, "path": r["path"], "len": r["len"],
            "block": r.get("block", False),
            "perp": _project_onto_axis(mid, (0.0, 0.0), ux, uy),
            "span": _projected_interval(r["a"], r["b"], vx, vy, (0.0, 0.0))}


def _merge_mullion_chains(glaze_pool: list[dict], caps: list[dict]) -> list[dict]:
    """Join collinear glazing segments across mullion blocks into logical panes.

    A multi-light frame (5-1133 W8) draws its center glazing line per light,
    interrupted by mullion blocks — so no single segment spans the opening and
    the window can't anchor. Two same-perp segments chain when the gap between
    their spans is mullion-sized AND a block cap sits in it (perp inside the
    gap, cap span covering the pane's offset). Requiring the physical bridge is
    what keeps dashed linework from chaining. Chains are APPENDED to the pool
    (members stay, so sub-light cap pairs behave as before); the merged record
    carries every member and bridge in ``idxs``/``paths`` so the clutter gate
    and bbox account for them. ``len`` is the summed coverage, which also lets
    _dedupe_by_perp prefer the chain over its own members.
    """
    blocks = [c for c in caps if c.get("block")]
    if not blocks or not glaze_pool:
        return glaze_pool
    pool = sorted(glaze_pool, key=lambda g: (g["perp"], g["span"][0]))
    chains: list[list[dict]] = []
    bridges: list[list[dict]] = []
    cur = [pool[0]]
    cur_bridges: list[dict] = []
    for g in pool[1:]:
        gap_lo, gap_hi = cur[-1]["span"][1], g["span"][0]
        found = ([b for b in blocks
                  if gap_lo - 2.0 <= b["perp"] <= gap_hi + 2.0
                  and b["span"][0] - WINDOW_SPAN_PERP_TOL_PX <= g["perp"] <= b["span"][1] + WINDOW_SPAN_PERP_TOL_PX]
                 if (abs(g["perp"] - cur[-1]["perp"]) <= WINDOW_GLAZING_DISTINCT_EPS
                     and 0.0 < gap_hi - gap_lo <= WINDOW_MULLION_GAP_MAX_PX)
                 else [])
        if found:
            cur.append(g)
            cur_bridges.extend(found)
        else:
            if len(cur) > 1:
                chains.append(cur)
                bridges.append(cur_bridges)
            cur = [g]
            cur_bridges = []
    if len(cur) > 1:
        chains.append(cur)
        bridges.append(cur_bridges)

    merged: list[dict] = []
    for chain, chain_bridges in zip(chains, bridges):
        best = max(chain, key=lambda g: g["len"])
        merged.append({
            "idx": best["idx"], "path": best["path"],
            "idxs": {g["idx"] for g in chain} | {b["idx"] for b in chain_bridges},
            "paths": [g["path"] for g in chain] + [b["path"] for b in chain_bridges],
            "len": sum(g["len"] for g in chain),
            "perp": sum(g["perp"] for g in chain) / len(chain),
            "span": (chain[0]["span"][0], chain[-1]["span"][1]),
            "lights": len(chain),
        })
    return glaze_pool + merged


def _dedupe_by_perp(records: list[dict]) -> list[dict]:
    """Collapse near-collinear duplicates (same perp offset) to one record.

    A toilet/sink hatch and double-drawn wall faces produce many lines at the
    SAME parallel offset; those are one pane, not many. Keeps the longest line
    per offset so the glazing-count gate measures distinct panes.
    """
    records = sorted(records, key=lambda r: (r["perp"], -r["len"]))
    out: list[dict] = []
    for r in records:
        if out and abs(r["perp"] - out[-1]["perp"]) <= WINDOW_GLAZING_DISTINCT_EPS:
            continue  # already kept the longer line at this offset
        out.append(r)
    return out


def _tight_band(records: list[dict]) -> list[dict]:
    """Largest run of panes spaced like glazing, not like stair treads.

    Walks the perp-sorted offsets and grows a run while consecutive panes stay
    within WINDOW_GLAZING_ADJ_SPACING_PX of each other and the run's total depth
    stays under WINDOW_GLAZING_THICKNESS_PX. Returns the longest such run, so a
    stray far-off parallel can neither join the band nor inflate its depth.
    """
    recs = sorted(records, key=lambda r: r["perp"])
    if not recs:
        return []
    best: list[dict] = [recs[0]]
    run: list[dict] = [recs[0]]
    for r in recs[1:]:
        if (r["perp"] - run[-1]["perp"] <= WINDOW_GLAZING_ADJ_SPACING_PX
                and r["perp"] - run[0]["perp"] <= WINDOW_GLAZING_THICKNESS_PX):
            run.append(r)
        else:
            run = [r]
        if len(run) > len(best):
            best = run[:]
    return best


# Bin width for the glazing index below. Not a tunable: it is exactly the width
# of the window _spanning_glazing tests span-starts against, so a query always
# touches at most two bins.
_GLAZE_U_BIN_PX = WINDOW_SPAN_OVERSHOOT_PX + WINDOW_SPAN_COVER_TOL_PX


def _glaze_index(glaze_pool: list[dict]) -> tuple[dict[int, tuple[list[float], list[int]]], list[dict]]:
    """Two-axis lookup structure over a frame's glazing pool.

    Every cap pair asks the same question — "which panes start beside cap 1, end
    beside cap 2, and sit inside the caps' facing extent?" — and answering it by
    scanning the whole pool once per pair is what makes window detection
    quadratic on dense sheets (measured: 88% of the stage on a 51k-path sheet,
    308k pairs x the full pool). Both axes of that question are bounded windows,
    so both can be answered by lookup instead: bucket the pool by span START
    (bins of _GLAZE_U_BIN_PX along the run axis), and sort each bucket by perp so
    the facing-extent window is a bisect.

    Returns ``(buckets, pool)`` where ``buckets[b]`` is ``(perps, positions)`` —
    the bucket's perp offsets in ascending order alongside the matching *pool
    positions*, so the caller can restore pool order. That matters:
    _dedupe_by_perp resolves exact (perp, -len) ties by input order, so a
    reordered scan could otherwise keep a different record. Build this AFTER
    _merge_mullion_chains appends its chains — they are part of the pool the
    pairs must see.
    """
    buckets: dict[int, list[int]] = {}
    for k, g in enumerate(glaze_pool):
        buckets.setdefault(int(g["span"][0] // _GLAZE_U_BIN_PX), []).append(k)
    index: dict[int, tuple[list[float], list[int]]] = {}
    for b, ks in buckets.items():
        ks.sort(key=lambda k: glaze_pool[k]["perp"])
        index[b] = ([glaze_pool[k]["perp"] for k in ks], ks)
    return index, glaze_pool


def _spanning_glazing(glaze_index: tuple[dict[int, tuple[list[float], list[int]]], list[dict]],
                      c1: dict, c2: dict) -> list[dict]:
    """Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.

    A glazing line qualifies when its perp offset lies within the caps' combined
    facing extent and its run-span covers the gap between the two cap positions
    (so it physically bridges the opening). Returns the tightest pane-deep band
    of de-duplicated offsets.

    The span-start and perp tests are answered off ``glaze_index`` rather than by
    scanning the pool; every surviving record still faces the exact comparisons,
    and the survivors are re-sorted into pool order before de-duplication, so the
    result is identical to the full scan, ties included.
    """
    index, pool = glaze_index
    ext_lo = min(c1["span"][0], c2["span"][0]) - WINDOW_SPAN_PERP_TOL_PX
    ext_hi = max(c1["span"][1], c2["span"][1]) + WINDOW_SPAN_PERP_TOL_PX
    s1_lo = c1["perp"] - WINDOW_SPAN_OVERSHOOT_PX
    s1_hi = c1["perp"] + WINDOW_SPAN_COVER_TOL_PX
    s2_lo = c2["perp"] - WINDOW_SPAN_COVER_TOL_PX
    s2_hi = c2["perp"] + WINDOW_SPAN_OVERSHOOT_PX
    hits: list[int] = []
    for b in range(int(s1_lo // _GLAZE_U_BIN_PX), int(s1_hi // _GLAZE_U_BIN_PX) + 1):
        bucket = index.get(b)
        if bucket is None:
            continue
        perps, positions = bucket
        for k in positions[bisect_left(perps, ext_lo):bisect_right(perps, ext_hi)]:
            span = pool[k]["span"]
            if s1_lo <= span[0] <= s1_hi and s2_lo <= span[1] <= s2_hi:
                hits.append(k)
    hits.sort()
    return _tight_band(_dedupe_by_perp([pool[k] for k in hits]))


# Bin width for the cap-pair pruning below. Not a tunable: any value strictly
# greater than WINDOW_CAP_MAX_LEN_PX makes the same-or-adjacent-bin rule exact.
_CAP_V_BIN_PX = WINDOW_CAP_MAX_LEN_PX + 4.0


def _facing_cap_pairs(caps: list[dict], *, gates: WindowGates) -> Iterator[tuple[int, int, float]]:
    """Index pairs ``(i, j, width)`` of caps that face each other across an opening.

    ``caps`` must be sorted by ``perp`` (position along the run axis). Yields in
    the exact order of the brute-force double loop — candidate numbering and NMS
    input order depend on it.

    ``gates`` carries the scaled opening-width floor; keyword-only and required
    (findings §4b).

    The gates below are unchanged; what changes is which pairs get to see them.
    The perp sort alone bounds the pair set along u only (the inner loop breaks
    past WINDOW_MAX_WIDTH_PX), leaving every cap in a 280px slab paired with
    every other, metres apart along v. But the align gate demands
    ``_interval_overlap >= WINDOW_CAP_ALIGN_OVERLAP * min(len)``, and min len is
    at least WINDOW_CAP_MIN_LEN_PX, so partners' v-spans genuinely INTERSECT;
    spans are at most WINDOW_CAP_MAX_LEN_PX long, so two intersecting spans start
    within that of each other and land in the same or adjacent _CAP_V_BIN_PX bin.
    Bucketing by span start therefore drops only pairs the align gate rejects.
    """
    min_width = gates.WINDOW_MIN_WIDTH_PX
    bins: dict[int, list[int]] = {}
    for i, c in enumerate(caps):
        bins.setdefault(int(c["span"][0] // _CAP_V_BIN_PX), []).append(i)

    for i, c1 in enumerate(caps):
        # Bins hold ascending indices, which (caps being perp-sorted) is also
        # ascending perp — so each slice can be cut at the width limit, with a
        # 1px slack so float rounding can never drop a pair the exact
        # comparison below would have kept.
        b = int(c1["span"][0] // _CAP_V_BIN_PX)
        limit = c1["perp"] + WINDOW_MAX_WIDTH_PX + 1.0
        js: list[int] = []
        for k in (b - 1, b, b + 1):
            lst = bins.get(k)
            if not lst:
                continue
            lo = bisect_right(lst, i)
            hi = bisect_right(lst, limit, lo, key=lambda idx: caps[idx]["perp"])
            js.extend(lst[lo:hi])
        js.sort()

        len1, span1 = c1["len"], c1["span"]
        for j in js:
            c2 = caps[j]
            width = c2["perp"] - c1["perp"]
            if width < min_width:
                continue
            if width > WINDOW_MAX_WIDTH_PX:
                break  # sorted by perp: no farther cap can be closer
            len2 = c2["len"]
            shorter, longer = (len1, len2) if len1 < len2 else (len2, len1)
            if shorter / longer < WINDOW_CAP_LEN_RATIO:
                continue
            if _interval_overlap(span1, c2["span"]) < WINDOW_CAP_ALIGN_OVERLAP * shorter:
                continue
            yield i, j, width


def _find_openings(cap_pool: list[dict],
                   glaze_index: tuple[dict[int, tuple[list[float], list[int]]], list[dict]],
                   *, gates: WindowGates) -> list[dict]:
    """Pair facing caps and confirm a glazing band bridges each opening.

    ``cap_pool`` runs perpendicular to the opening (the jambs); the glazing pool
    behind ``glaze_index`` runs along it (the panes). Caps are sorted by position
    along the run axis, which is the frame _facing_cap_pairs enumerates in.
    """
    caps = sorted(
        (c for c in cap_pool if WINDOW_CAP_MIN_LEN_PX <= c["len"] <= WINDOW_CAP_MAX_LEN_PX),
        key=lambda c: c["perp"],
    )
    openings: list[dict] = []
    for i, j, width in _facing_cap_pairs(caps, gates=gates):
        c1, c2 = caps[i], caps[j]
        band = _spanning_glazing(glaze_index, c1, c2)
        if len(band) < WINDOW_MIN_GLAZING_LINES:
            continue
        openings.append({"c1": c1, "c2": c2, "glaze": band, "width": width})
    return openings


def _area(b: BBox) -> float:
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _dedupe_openings(cands: list[Candidate]) -> list[Candidate]:
    """Suppress overlapping detections from duplicate cap pairs (greedy NMS).

    Duplicate / double-drawn caps yield several openings over the same glass.
    Prefer the one with more glazing lines, then the tightest bbox; drop any
    later candidate whose center already sits inside a kept candidate.
    """
    cands = sorted(cands, key=lambda c: (-c.evidence["glazing_lines"], _area(c.bbox)))
    kept: list[Candidate] = []
    for c in cands:
        cx, cy = (c.bbox[0] + c.bbox[2]) / 2, (c.bbox[1] + c.bbox[3]) / 2
        if any(k.bbox[0] <= cx <= k.bbox[2] and k.bbox[1] <= cy <= k.bbox[3] for k in kept):
            continue
        kept.append(c)
    return kept


def _clutter_grid(recs: list[dict], paths: list[PathPrimitive]) -> tuple[
        list[PathPrimitive], dict[tuple[int, int], list[int]], dict[tuple[int, int], list[tuple[dict, float, float]]]]:
    """Page-wide point buckets for _band_interior_clutter.

    The clutter scan asks which primitives have a point (shapes) or a midpoint
    (lines) inside one opening's band — a region a few hundred px across on a
    page that can be metres wide. Walking every path and every line record per
    accepted opening is O(openings x n); bucketing those points ONCE per page
    turns it into a lookup over the cells the band's bbox touches.

    Shapes are indexed under every cell any of their own points falls in (so a
    primitive straddling cells is still found from either side) and carry their
    position in the returned list, which is how the caller counts each shape
    once. Lines are indexed by the single midpoint the scan tests.
    """
    shape_list = [p for p in paths if p.item_type != "l" and len(p.points) >= 2]
    shape_cells: dict[tuple[int, int], list[int]] = {}
    for k, p in enumerate(shape_list):
        for cell in {(int(px // _GRID_PX), int(py // _GRID_PX)) for px, py in p.points}:
            shape_cells.setdefault(cell, []).append(k)
    line_cells: dict[tuple[int, int], list[tuple[dict, float, float]]] = {}
    for r in recs:
        mx = (r["a"][0] + r["b"][0]) / 2
        my = (r["a"][1] + r["b"][1]) / 2
        line_cells.setdefault((int(mx // _GRID_PX), int(my // _GRID_PX)), []).append((r, mx, my))
    return shape_list, shape_cells, line_cells


def _band_interior_clutter(u_lo: float, u_hi: float, v_lo: float, v_hi: float,
                           ux: float, uy: float, vx: float, vy: float,
                           used_idxs: set[int], glaze_angle: float, cap_angle: float,
                           grid: tuple) -> tuple[int, int]:
    """Clutter strictly between the glazing panes — empty for a real window.

    The scan region is the oriented rectangle ``u ∈ [u_lo, u_hi]`` (the run axis,
    between the two caps) × ``v ∈ [v_lo, v_hi]`` (across the pane band). Working
    in this rotated (u, v) frame — not the axis-aligned bbox — and confining v to
    the pane band is what keeps diagonal windows intact: their loose axis bbox
    would sweep in neighbours, and their gray jamb caps are filled re/qu/c shapes
    that sit at the ends (``u`` outside ``[u_lo, u_hi]``), never between panes.

    Returns ``(shapes, oblique)``:
      * ``shapes`` — non-line primitives (re/qu/c) with any point in the region:
        crosshatch boxes / insulation arcs between a hatched wall's two faces.
      * ``oblique`` — straight lines (midpoint in the region) parallel to neither
        glazing nor caps: line-drawn insulation hatch.
    The band lines and caps are excluded via ``used_idxs`` so the panes never
    count as their own clutter; the middle pane of a 3-pane window is a band
    line and is likewise excluded. ``used_idxs`` also carries the window's own
    block-cap quads and mullion-bridge blocks (framed multi-light windows draw
    those BETWEEN the panes), so the frame's structure never rejects itself —
    while foreign quads (crosshatch fill) still count.

    The candidates come from ``grid`` (see _clutter_grid) rather than from the
    whole page: (u, v) is orthonormal, so the region's four corners map straight
    back to page coordinates, and a point inside the oriented rectangle is
    necessarily inside that rectangle's axis-aligned bbox. Every candidate still
    faces the exact (u, v) test, so the counts are unchanged.
    """
    shape_list, shape_cells, line_cells = grid
    xs = [u * ux + v * vx for u in (u_lo, u_hi) for v in (v_lo, v_hi)]
    ys = [u * uy + v * vy for u in (u_lo, u_hi) for v in (v_lo, v_hi)]
    cells = [(cx, cy)
             for cx in range(int(min(xs) // _GRID_PX), int(max(xs) // _GRID_PX) + 1)
             for cy in range(int(min(ys) // _GRID_PX), int(max(ys) // _GRID_PX) + 1)]

    shapes = oblique = 0
    seen: set[int] = set()
    for cell in cells:
        for k in shape_cells.get(cell, ()):
            if k in seen:
                continue  # indexed under several cells; count it once
            seen.add(k)
            p = shape_list[k]
            if p.path_index in used_idxs:
                continue
            if any(u_lo <= px * ux + py * uy <= u_hi
                   and v_lo <= px * vx + py * vy <= v_hi
                   for px, py in p.points):
                shapes += 1
        for r, mx, my in line_cells.get(cell, ()):
            if r["path"].path_index in used_idxs:
                continue
            if not (u_lo <= mx * ux + my * uy <= u_hi
                    and v_lo <= mx * vx + my * vy <= v_hi):
                continue
            if (_angle_diff_mod180(r["angle"], cap_angle) > WINDOW_ANGLE_TOL_DEG
                    and _angle_diff_mod180(r["angle"], glaze_angle) > WINDOW_ANGLE_TOL_DEG):
                oblique += 1
    return shapes, oblique


def detect_windows(paths: list[PathPrimitive], *,
                   scale_factor: float = 1.0) -> list[Candidate]:
    """Detect windows as capped openings bridged by a parallel glazing band.

    For each orientation, find pairs of short perpendicular caps that face each
    other across a window-width gap, then require >=2 distinct parallel glazing
    lines spanning that gap. Door-overlap suppression happens later in
    postprocess (_resolve_door_window_conflicts) using the reliable door
    detector.

    ``scale_factor`` scales the world-space gates (`WindowGates`); 1.0 is exact
    identity. Only the opening-width floor scales — the symbol's internal ink
    gates are paper-space (findings §4e).
    """
    gates = WindowGates.at(scale_factor)
    win_keywords = ["window", "wind", "glaz", "glazing"]
    recs = _line_records(paths)
    cap_recs = [r for r in recs
                if WINDOW_CAP_MIN_LEN_PX <= r["len"] <= WINDOW_CAP_MAX_LEN_PX]
    cap_recs += _block_cap_records(paths)
    clutter_grid = _clutter_grid(recs, paths)

    # Each cap-orientation group fixes a rotated frame (u perpendicular to the
    # caps, v along them). Caps are paired and a glazing band confirmed entirely
    # in (perp, span) scalars, so the opening logic is orientation-free.
    raw: list[Candidate] = []
    cand_idx = 0
    for cap_angle, group in _cap_orientation_frames(cap_recs):
        ux, uy, vx, vy = _frame_axes(cap_angle)
        glaze_angle = (cap_angle + 90.0) % 180.0
        caps = [_cap_record(r, ux, uy, vx, vy) for r in group]
        glaze_pool = [_glaze_record(r, ux, uy, vx, vy) for r in recs
                      if _angle_diff_mod180(r["angle"], glaze_angle) <= WINDOW_ANGLE_TOL_DEG]
        glaze_pool = _merge_mullion_chains(glaze_pool, caps)
        for opening in _find_openings(caps, _glaze_index(glaze_pool), gates=gates):
            c1, c2, band = opening["c1"], opening["c2"], opening["glaze"]

            cap_len = (c1["len"] + c2["len"]) / 2
            if len(band) < 3 and cap_len < WINDOW_TWO_LINE_MIN_CAP_PX:
                continue  # ambiguous thin-wall / fixture sliver, not a window
            band_gap = band[-1]["perp"] - band[0]["perp"]
            if len(band) < 3 and band_gap < WINDOW_TIGHT_PAIR_GAP_PX:
                margin = min(
                    min(band[0]["perp"] - c["span"][0], c["span"][1] - band[-1]["perp"])
                    for c in (c1, c2))
                if margin < WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX:
                    continue  # doubled material edge at a box/step corner, not glazing
            if opening["width"] < WINDOW_MIN_WIDTH_CAP_RATIO * cap_len:
                continue  # opening narrower than the jamb is long: a wall slot, not a window

            bbox: BBox = c1["path"].bbox
            band_paths = [p for r in band for p in r.get("paths", [r["path"]])]
            for p in [c2["path"], *band_paths]:
                bbox = _bbox_union(bbox, p.bbox)

            # A real window's glass is clear: nothing between the panes. A
            # hatched wall read as a 2-line band has its crosshatch right between
            # its two faces. Reject when the pane band's interior carries it.
            # Measured in the oriented (u, v) frame, confined to the band, so a
            # diagonal window's loose axis bbox and its end jamb fills are excluded.
            used_idxs = {c1["idx"], c2["idx"]}
            for r in band:
                used_idxs |= r.get("idxs", {r["idx"]})
            perps = [r["perp"] for r in band]
            v_lo = min(perps) - WINDOW_INTERIOR_BAND_PAD_PX
            v_hi = max(perps) + WINDOW_INTERIOR_BAND_PAD_PX
            shapes, oblique = _band_interior_clutter(
                c1["perp"], c2["perp"], v_lo, v_hi, ux, uy, vx, vy,
                used_idxs, glaze_angle, cap_angle, clutter_grid)
            if shapes > WINDOW_INTERIOR_SHAPE_MAX or oblique > WINDOW_INTERIOR_OBLIQUE_MAX:
                continue

            group_paths = [c1["path"], c2["path"]] + band_paths
            layer_hint = any(_layer_hint(p, win_keywords) for p in group_paths)
            layer_prior = max((_layer_strong_prior(p, win_keywords) for p in group_paths), default=0.0)

            confidence = 0.62
            confidence += 0.05 * (len(band) - WINDOW_MIN_GLAZING_LINES)
            confidence += layer_prior
            if layer_hint and layer_prior == 0.0:
                confidence += 0.10
            confidence = min(confidence, 0.90)
            if confidence < WINDOW_MIN_CONFIDENCE:
                continue

            raw.append(Candidate(
                candidate_id=f"window_{cand_idx:04d}",
                entity_type="window",
                bbox=bbox,
                confidence=round(confidence, 3),
                evidence={
                    "orientation": ("horizontal" if _angle_diff_mod180(glaze_angle, 0.0) <= WINDOW_ANGLE_TOL_DEG
                                    else "vertical" if _angle_diff_mod180(glaze_angle, 90.0) <= WINDOW_ANGLE_TOL_DEG
                                    else "diagonal"),
                    "glazing_angle_deg": round(glaze_angle, 1),
                    "glazing_lines": len(band),
                    "glazing_len_px": round(sum(r["len"] for r in band) / len(band), 1),
                    "cap_len_px": round(cap_len, 1),
                    "opening_width_px": round(opening["width"], 1),
                    "lights": max(r.get("lights", 1) for r in band),
                    "layer_hint": layer_hint,
                },
            ))
            cand_idx += 1

    deduped = _dedupe_openings(raw)
    # Re-number so candidate_ids stay contiguous after NMS.
    return [
        Candidate(f"window_{i:04d}", c.entity_type, c.bbox, c.confidence, c.evidence)
        for i, c in enumerate(deduped)
    ]
