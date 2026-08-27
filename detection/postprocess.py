from __future__ import annotations
from dataclasses import dataclass

from models import BBox, Candidate
from detection.geometry import (
    _angle_diff_mod180, _bbox_area, _bbox_center, _bbox_expanded, _bbox_height,
    _bbox_width, _distance, _line_angle_deg,
)
from detection.doors.assembly import _dedupe_door_components
from detection.walls import WALL_PARALLEL_ANGLE_TOL, WallNetwork


# ---------------------------------------------------------------------------
# Cross-element validation (soft: boost/penalize confidence)
# ---------------------------------------------------------------------------

CROSS_WALL_EXPAND_PX  = 20.0   # corridor reach beyond thickness/2 when checking containment
CROSS_NO_WALL_PENALTY = 0.08   # door/window has no wall nearby → penalty
CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY = 0.04
# Single-line-leaf is the weakest leaf evidence (a single anchored line vs. a
# closed rectangle). Without a surrounding wall AND without a nearby door label,
# the assembly is statistically a bath fixture or window decoration, not a
# door. Apply a stronger penalty than the default door_assembly case so these
# fall below the offline confidence floor.
CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY = 0.15
# Doors get NO in-wall boost: the §9 regression baselines pin exact door
# confidences, and wall adjacency is correlated with the door's own linework.
CROSS_OPENING_ENDPOINT_TOL_PX = 12.0  # opening_line endpoints on a centerline → richer context
# Windows DO get a positive boost: a cap pair spanning exactly the thickness of
# the interrupted wall run is the defining property of a real window, and the
# wall network is derived from face pairs — independent of the glazing linework
# the window detector anchors on.
CROSS_WINDOW_ON_WALL_BOOST = 0.08
CROSS_WINDOW_THICKNESS_TOL_PX = 6.0  # frozen P (findings §4e): the mismatch it
                                     # tolerates is cap-ink overshoot beyond the
                                     # wall band — paper-space, measured bimodal
                                     # (~0 or >>6) at every scale tier. NOT a
                                     # CrossGates field; scaling it is pinned
                                     # off by TestCrossWindowToleranceUnscaled.
CROSS_WALL_RUNS_THROUGH_MARGIN_PX = 12.0  # centerline extends past both bbox ends by this


CROSS_WALL_RUNS_THROUGH_BAND_PX = 8.0  # face must lie within the bbox short extent + this


def _wall_runs_through(
    network: WallNetwork, bbox: BBox, *, gates: CrossGates,
) -> bool:
    """True when a wall FACE line runs unbroken through the bbox span.

    A real window interrupts its wall faces at the jambs (and face merging
    bridges only ~6px gaps, far below any opening width), while a hatched or
    double-struck wall band misread as glazing has faces continuing past both
    bbox ends. Centerlines cannot be used here: a window's glazing-derived
    centerline merges collinearly with the wall run on both sides and would
    make every real window look continuous.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    if max(w, h) < 1e-6:
        return False
    horiz = w >= h
    axis_angle = 0.0 if horiz else 90.0
    lo, hi = (x0, x1) if horiz else (y0, y1)
    margin = gates.CROSS_WALL_RUNS_THROUGH_MARGIN_PX
    band = gates.CROSS_WALL_RUNS_THROUGH_BAND_PX
    for face in network.faces:
        p1, p2 = face.p1, face.p2
        ang = _line_angle_deg(p1, p2)
        if _angle_diff_mod180(ang, axis_angle) > WALL_PARALLEL_ANGLE_TOL:
            continue
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        if horiz:
            if not (y0 - band <= mid[1] <= y1 + band):
                continue
            s_lo, s_hi = sorted((p1[0], p2[0]))
        else:
            if not (x0 - band <= mid[0] <= x1 + band):
                continue
            s_lo, s_hi = sorted((p1[1], p2[1]))
        if s_lo <= lo - margin and s_hi >= hi + margin:
            return True
    return False


def _cross_validate(
    candidates: list[Candidate],
    network: WallNetwork | None,
    *,
    scale_factor: float = 1.0,
) -> list[Candidate]:
    """Validate doors/windows against the wall-centerline network.

    Doors keep the historic penalty-only contract (the §9 door baselines pin
    exact confidences): a door with no wall corridor anywhere close is likely
    a false positive (legend, annotation, bath fixture) and is penalized;
    a door in a wall is left untouched. Windows additionally earn a positive
    boost when their cap pair spans the thickness of the interrupted wall run
    at their location — evidence independent of the glazing linework.

    `scale_factor` defaults to 1.0 (identity): unlike the gates OBJECTS
    threaded between modules elsewhere (never defaulted, so a missing
    hand-off can't silently go unscaled), this entry point builds its own
    `CrossGates` from a scalar whose default is genuinely identity, and it is
    exercised directly by tests that call it unscaled.
    """
    if network is None or network.is_empty():
        return candidates

    gates = CrossGates.at(scale_factor)
    adjusted = []
    for c in candidates:
        if c.entity_type not in ("door", "window"):
            adjusted.append(c)
            continue

        in_wall = network.near_bbox(c.bbox, gates.CROSS_WALL_EXPAND_PX)
        new_evidence = dict(c.evidence)
        delta = 0.0

        if c.entity_type == "door":
            is_assembly = c.evidence.get("method") == "door_assembly"
            is_single_line_no_label = (
                is_assembly
                and c.evidence.get("assembly_type") == "single_line_leaf"
                and not c.evidence.get("nearby_label")
            )
            if is_single_line_no_label:
                penalty = CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY
                # The weakest evidence tier requires STROKED wall corroboration:
                # pure fill-outline geometry also describes the fixtures (tubs,
                # counters) this tier statistically confuses with doors, and a
                # fixture always stands against some wall.
                if in_wall and not network.near_bbox(
                    c.bbox, gates.CROSS_WALL_EXPAND_PX, stroked_only=True
                ):
                    in_wall = False
                    new_evidence["wall_context_note"] = "filled_wall_only"
            elif is_assembly:
                penalty = CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY
            else:
                penalty = CROSS_NO_WALL_PENALTY

            wall_context = "in_wall" if in_wall else "no_wall"
            if in_wall:
                opening = c.evidence.get("opening_line")
                if opening and len(opening) == 2:
                    hits = 0
                    for pt in opening:
                        near = network.nearest_segment((pt[0], pt[1]))
                        if near is not None and near[1] <= gates.CROSS_OPENING_ENDPOINT_TOL_PX:
                            hits += 1
                    if hits == 2:
                        wall_context = "on_wall_centerline"
            else:
                delta = -penalty
            new_evidence["wall_context"] = wall_context

        else:  # window
            if in_wall:
                new_evidence["wall_context"] = "in_wall"
                if not _wall_runs_through(network, c.bbox, gates=gates):
                    center = _bbox_center(c.bbox)
                    near = network.nearest_segment(center)
                    short_side = min(_bbox_width(c.bbox), _bbox_height(c.bbox))
                    if (
                        near is not None
                        and abs(short_side - near[0].thickness_px)
                        <= CROSS_WINDOW_THICKNESS_TOL_PX
                    ):
                        delta = CROSS_WINDOW_ON_WALL_BOOST
                        new_evidence["wall_context"] = "spans_wall_thickness"
                        new_evidence["wall_thickness_px"] = near[0].thickness_px
            else:
                new_evidence["wall_context"] = "no_wall"
                delta = -CROSS_NO_WALL_PENALTY

        new_conf = round(min(max(c.confidence + delta, 0.0), 0.95), 3)
        adjusted.append(Candidate(
            candidate_id=c.candidate_id,
            entity_type=c.entity_type,
            bbox=c.bbox,
            confidence=new_conf,
            evidence=new_evidence,
        ))

    return adjusted


# ---------------------------------------------------------------------------
# Type-specific NMS
# ---------------------------------------------------------------------------

NMS_IOU_THRESHOLD     = 0.50
NMS_CENTER_DIST_PX    = 15.0   # suppress if centers are this close regardless of IoU


def _bbox_iou(a: BBox, b: BBox) -> float:
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    inter = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if inter == 0.0:
        return 0.0
    union = _bbox_area(a) + _bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def _projected_overlap_1d(a: BBox, b: BBox) -> tuple[float, float]:
    """Projected overlap fraction and perpendicular gap on bbox a's dominant axis.

    Returns (overlap_fraction, perp_gap_px):
      overlap_fraction — fraction of the shorter interval covered on dominant axis
      perp_gap_px      — gap between the two bboxes on the *perpendicular* axis
                         (0 if they overlap perpendicularly, positive if separated)
    """
    aw = _bbox_width(a)
    ah = _bbox_height(a)
    bw = _bbox_width(b)
    bh = _bbox_height(b)

    if aw >= ah:   # a is horizontal → dominant axis = x, perpendicular = y
        lo = max(a[0], b[0]); hi = min(a[2], b[2])
        shorter = min(aw, bw)
        perp_lo = max(a[1], b[1]); perp_hi = min(a[3], b[3])
    else:          # a is vertical   → dominant axis = y, perpendicular = x
        lo = max(a[1], b[1]); hi = min(a[3], b[3])
        shorter = min(ah, bh)
        perp_lo = max(a[0], b[0]); perp_hi = min(a[2], b[2])

    overlap = max(0.0, hi - lo)
    frac = overlap / shorter if shorter > 0 else 0.0
    perp_gap = max(0.0, perp_lo - perp_hi)
    return frac, perp_gap


# Max perpendicular separation for the projected-overlap NMS rule to fire.
# Two walls at the same x-range but 500 px apart in y are not duplicates.
NMS_PROJ_PERP_MAX_PX = 40.0


def _suppress(candidates: list[Candidate]) -> list[Candidate]:
    """Type-specific NMS: higher confidence wins when two candidates overlap.

    For skinny wall/window boxes plain IoU can be low even when boxes nearly
    coincide. The projected-overlap rule is applied only when the perpendicular
    gap is small (≤ NMS_PROJ_PERP_MAX_PX), preventing two parallel walls at
    different rows/columns from collapsing into one.
    """
    candidates = _dedupe_door_components(candidates)

    by_type: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_type.setdefault(c.entity_type, []).append(c)

    kept: list[Candidate] = []
    for etype, group in by_type.items():
        group = sorted(group, key=lambda c: c.confidence, reverse=True)
        suppressed = set()

        for i, ci in enumerate(group):
            if i in suppressed:
                continue
            for j, cj in enumerate(group):
                if j <= i or j in suppressed:
                    continue
                iou = _bbox_iou(ci.bbox, cj.bbox)
                center_dist = _distance(_bbox_center(ci.bbox), _bbox_center(cj.bbox))
                proj, perp_gap = _projected_overlap_1d(ci.bbox, cj.bbox)

                directional = etype in ("wall", "window")
                same_orientation = (
                    (_bbox_width(ci.bbox) >= _bbox_height(ci.bbox)) ==
                    (_bbox_width(cj.bbox) >= _bbox_height(cj.bbox))
                )
                # Center distance alone is not enough for directional types:
                # a horizontal wall crossing a vertical wall shares a center
                # but is a distinct element and must not be suppressed.
                center_suppresses = (
                    center_dist <= NMS_CENTER_DIST_PX
                    and (not directional or same_orientation)
                )

                if (
                    iou >= NMS_IOU_THRESHOLD
                    or center_suppresses
                    or (
                        directional
                        and proj >= 0.80
                        and perp_gap <= NMS_PROJ_PERP_MAX_PX
                        and same_orientation
                    )
                ):
                    suppressed.add(j)

        kept.extend(c for k, c in enumerate(group) if k not in suppressed)

    return kept


# ---------------------------------------------------------------------------
# Door / window cross-exclusion
# ---------------------------------------------------------------------------

CROSS_DOOR_EXPAND_PX = 20.0  # dilate REAL door bboxes before testing window overlap
CROSS_DOOR_MIN_WINDOW_COVER = 0.10  # door must cover this fraction of the window's area;
                                    # a mere dilated-corner graze does not suppress it
CROSS_DOOR_MIN_CONFIDENCE = 0.40    # doors at/above this get the full 20px veto reach.
                                    # Fallback-tier doors (DOOR_FALLBACK_CONFIDENCE 0.35 —
                                    # label boxes, glazing mullions, sliding panels, kept
                                    # only for Gemini arbitration) OFTEN ARE window-like
                                    # linework, so a window reading the same ink is
                                    # genuinely ambiguous and still yields to them — but
                                    # only near that ink (reduced dilation below), never
                                    # 20px out: on 5-1133, mullion strips ending 10px
                                    # above W8 projected their veto onto its band.
CROSS_DOOR_FALLBACK_EXPAND_PX = 8.0 # veto reach of a fallback-tier door. Measured on
                                    # 5-1133: the joinery FPs a fallback veto rightly
                                    # kills overlap its ink at <=6px dilation (the recess
                                    # column at (999,890) is the farthest); W8 stays
                                    # clear up to ~17px. 8px sits between with margin.
CROSS_DOOR_WALL_RUN_TOL_PX = 4.0    # frozen P: a window standing BEYOND a swing door's
                                    # hinge-side jamb, IN the door's wall plane, is not
                                    # door ink — it is joinery drawn in the same wall run,
                                    # and the dilation must not reach it. The wall plane
                                    # is a hinge edge of the bbox (rooms._swing_hinge_edges);
                                    # the window's glazing band must contain that edge's
                                    # line within this tolerance, run parallel to it, and
                                    # its undilated bbox must not overlap the door's.
                                    # Measured on s10: door_0009's hinge edge x=229 lies
                                    # exactly on the hall window's inner pane (217-229 x
                                    # 788-864, 4px above the jamb); the 20px dilation
                                    # covered 21% of the 12x76px band and killed the only
                                    # seal of that wall run (hall + kitchen leaked to the
                                    # page exterior). The false class never matches: s01
                                    # door_0015's flanking phantoms (garden pair, no
                                    # derivable hinge) run perpendicular to the wall or
                                    # lie 51px off its plane at the parked leaves' tips;
                                    # door-ink phantoms inside the footprint overlap the
                                    # raw bbox (cover 0.19-1.0). Corpus census 2026-08-27:
                                    # the exemption fires on six windows (s10, s11, s16,
                                    # s17, s18 — each a 2-3 line frame in the wall band
                                    # beside a door's hinge jamb), no other veto changes.


@dataclass(frozen=True)
class CrossGates:
    """World-space cross-validation gates, pre-multiplied by the factor.

    Only the GEOMETRIC constants get fields; the confidence penalties and
    boosts are dimensionless and never scale.

    CROSS_WALL_EXPAND_PX is a door-bbox-to-wall corridor. Measured (findings
    §4d): the reach confirmed doors actually need has p90 9.64px at 1:50 vs
    0.78px at 1:100, and the scaled 10px gate still clears every 1:100
    sheet's p90 need (max 8.12px) with headroom.
    """
    factor: float
    CROSS_WALL_EXPAND_PX: float
    CROSS_OPENING_ENDPOINT_TOL_PX: float
    CROSS_WALL_RUNS_THROUGH_MARGIN_PX: float
    CROSS_WALL_RUNS_THROUGH_BAND_PX: float
    CROSS_DOOR_EXPAND_PX: float
    CROSS_DOOR_FALLBACK_EXPAND_PX: float

    @classmethod
    def at(cls, factor: float) -> "CrossGates":
        assert factor > 0, "scale factor must be positive"
        return cls(
            factor=factor,
            CROSS_WALL_EXPAND_PX=CROSS_WALL_EXPAND_PX * factor,
            CROSS_OPENING_ENDPOINT_TOL_PX=CROSS_OPENING_ENDPOINT_TOL_PX * factor,
            CROSS_WALL_RUNS_THROUGH_MARGIN_PX=CROSS_WALL_RUNS_THROUGH_MARGIN_PX * factor,
            CROSS_WALL_RUNS_THROUGH_BAND_PX=CROSS_WALL_RUNS_THROUGH_BAND_PX * factor,
            CROSS_DOOR_EXPAND_PX=CROSS_DOOR_EXPAND_PX * factor,
            CROSS_DOOR_FALLBACK_EXPAND_PX=CROSS_DOOR_FALLBACK_EXPAND_PX * factor,
        )


CROSS_GATES_UNSCALED = CrossGates.at(1.0)


def _resolve_door_window_conflicts(
    candidates: list[Candidate], *, scale_factor: float = 1.0,
) -> list[Candidate]:
    """Drop window candidates that materially sit on a detected door.

    Door symbols (leaves, single/double swings, garden doors) contain parallel
    linework with short perpendicular caps — the same signature a glazing pane
    has — so they masquerade as windows. Door detection is reliable, so any
    window candidate sitting on a door is a false positive. This does not depend
    on wall detection. Ground truth on floor-plans.pdf: every real window is
    clear of all doors; 14 of 19 window false positives sit on a door.

    Suppression requires the (dilated) door to cover at least
    CROSS_DOOR_MIN_WINDOW_COVER of the window's area — a distant door whose
    dilation merely grazes a window corner is not a conflict (5-1133 Window A).
    Real doors (>= CROSS_DOOR_MIN_CONFIDENCE) veto with the full 20px reach;
    fallback-tier doors veto only windows near their own ink
    (CROSS_DOOR_FALLBACK_EXPAND_PX) — they are frequently glazing-mullion or
    sliding-panel linework, so a window built from the same ink yields to them,
    but their speculative bbox must not project onto separate glazing.

    `scale_factor` defaults to 1.0 (identity), matching `_cross_validate`'s
    own defaulted-scalar entry point: this function builds its own
    `CrossGates` from a scalar whose default is genuine identity, and it is
    called directly by tests.
    """
    gates = CrossGates.at(scale_factor)
    doors = [c for c in candidates if c.entity_type == "door"]
    door_bboxes = [
        (
            c,
            _bbox_expanded(
                c.bbox,
                gates.CROSS_DOOR_EXPAND_PX if c.confidence >= CROSS_DOOR_MIN_CONFIDENCE
                else gates.CROSS_DOOR_FALLBACK_EXPAND_PX,
            ),
        )
        for c in doors
    ]
    if not door_bboxes:
        return candidates

    def sits_on_door(win: Candidate) -> bool:
        wb = win.bbox
        win_area = _bbox_area(wb)
        if win_area <= 0:
            return False
        for door, db in door_bboxes:
            ix = max(0.0, min(wb[2], db[2]) - max(wb[0], db[0]))
            iy = max(0.0, min(wb[3], db[3]) - max(wb[1], db[1]))
            if ix * iy < CROSS_DOOR_MIN_WINDOW_COVER * win_area:
                continue
            if _window_in_door_wall_run(win, door):
                continue  # joinery beyond the hinge jamb, not door ink
            return True
        return False

    return [
        c for c in candidates
        if c.entity_type != "window" or not sits_on_door(c)
    ]


def _window_in_door_wall_run(win: Candidate, door: Candidate) -> bool:
    """True when ``win`` stands beyond ``door``'s hinge-side jamb in the door's
    own wall plane — a window drawn in the same wall run, never door ink.

    Door ink that reads as glazing (leaf edges, the swing's parallel
    linework) lies inside the door's footprint, so it overlaps the raw bbox;
    the dilation exists to catch the ink spilling a few px past it. A window
    whose undilated bbox is clear of the door's, whose glazing runs parallel
    to a hinge edge, and whose band contains that edge's line (within
    CROSS_DOOR_WALL_RUN_TOL_PX) is joinery standing in the wall band the
    doorway interrupts (s10: the hall window 4px above door_0009's jamb).
    Doors without a derivable hinge (pairs, sliding, fallback tiers) keep the
    plain veto.
    """
    from detection.rooms import _swing_hinge_edges  # rooms imports walls, never this module

    hinge_edges = _swing_hinge_edges(door)
    if not hinge_edges:
        return False
    ori = win.evidence.get("orientation")
    wx0, wy0, wx1, wy1 = win.bbox
    x0, y0, x1, y1 = door.bbox
    tol = CROSS_DOOR_WALL_RUN_TOL_PX
    # Undilated bboxes must be clear of each other: beyond the jamb, not on
    # the leaf.
    if min(wx1, x1) - max(wx0, x0) > 0 and min(wy1, y1) - max(wy0, y0) > 0:
        return False
    for edge in hinge_edges:
        if edge in (0, 1):
            if ori != "horizontal":
                continue
            line = y0 if edge == 0 else y1
            if wy0 - tol <= line <= wy1 + tol and (wx1 <= x0 + tol or wx0 >= x1 - tol):
                return True
        else:
            if ori != "vertical":
                continue
            line = x0 if edge == 2 else x1
            if wx0 - tol <= line <= wx1 + tol and (wy1 <= y0 + tol or wy0 >= y1 - tol):
                return True
    return False


# NOTE: there is deliberately no "drop windows that look like wall linework"
# pass anymore. Both formulations tried during the wall-network rebuild
# (centerline runs-through, face runs-through) also matched REAL windows:
# floor-plans-style drawings keep the wall faces continuous and add glazing
# between them, so "the wall runs through the window" is a drafting style,
# not a false-positive signal. Hatched-band FPs are handled by the window
# detector's own interior-clutter gate and by Gemini validation online;
# _wall_runs_through above survives only as the conservative gate on the
# window in-wall confidence boost.
