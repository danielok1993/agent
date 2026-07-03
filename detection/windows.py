from __future__ import annotations
import math
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
WINDOW_MAX_WIDTH_PX         = 240.0  # 5-1133 Window B is 173px; caps wall/decoration runs
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
WINDOW_SPAN_COVER_TOL_PX    = 4.0    # a glazing line may fall short of each cap by this
WINDOW_SPAN_OVERSHOOT_PX    = 12.0   # ...and run at most this far PAST each cap (real
                                     # glazing overshoots ~7.5px; walls run hundreds past)
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
# NOTE the OTHER page-1 FPs — solid-filled blocks (w17/w18) and the "recess"
# niche (w26) — are NOT caught here: their distinguishing clutter sits at the
# opening ends, exactly where real diagonal windows carry their filled jambs, so
# no interior-geometry gate separates them without killing the diagonals. They
# are left to Gemini validation (the pipeline's design). Colour/fill-brightness
# would separate them but is not uniform across PDFs, so we don't use it.
WINDOW_INTERIOR_BAND_PAD_PX = 1.5  # widen the pane band by this (per side) along v before scanning,
                                   # so a rail drawn a hair outside the band still bounds the hatch.
WINDOW_INTERIOR_SHAPE_MAX   = 1    # non-line primitives (re/qu/c) between the panes: >1 ⇒ crosshatch
                                   # /insulation fill. True windows: <=1 (a stray jamb-corner poke).
WINDOW_INTERIOR_OBLIQUE_MAX = 2    # lines between the panes parallel to neither glazing nor caps:
                                   # line-drawn hatch. True windows: 0 (defends line-only hatch).


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
            "perp": _project_onto_axis(mid, (0.0, 0.0), ux, uy),
            "span": _projected_interval(r["a"], r["b"], vx, vy, (0.0, 0.0))}


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


def _spanning_glazing(glaze_pool: list[dict], c1: dict, c2: dict) -> list[dict]:
    """Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.

    A glazing line qualifies when its perp offset lies within the caps' combined
    facing extent and its run-span covers the gap between the two cap positions
    (so it physically bridges the opening). Returns the tightest pane-deep band
    of de-duplicated offsets.
    """
    ext_lo = min(c1["span"][0], c2["span"][0]) - WINDOW_SPAN_PERP_TOL_PX
    ext_hi = max(c1["span"][1], c2["span"][1]) + WINDOW_SPAN_PERP_TOL_PX
    spanning = [g for g in glaze_pool
                if ext_lo <= g["perp"] <= ext_hi
                and c1["perp"] - WINDOW_SPAN_OVERSHOOT_PX <= g["span"][0] <= c1["perp"] + WINDOW_SPAN_COVER_TOL_PX
                and c2["perp"] - WINDOW_SPAN_COVER_TOL_PX <= g["span"][1] <= c2["perp"] + WINDOW_SPAN_OVERSHOOT_PX]
    return _tight_band(_dedupe_by_perp(spanning))


def _find_openings(cap_pool: list[dict], glaze_pool: list[dict]) -> list[dict]:
    """Pair facing caps and confirm a glazing band bridges each opening.

    ``cap_pool`` runs perpendicular to the opening (the jambs); ``glaze_pool``
    runs along it (the panes). Caps are sorted by position along the run axis so
    the inner loop can break once the opening exceeds the max window width.
    """
    caps = sorted(
        (c for c in cap_pool if WINDOW_CAP_MIN_LEN_PX <= c["len"] <= WINDOW_CAP_MAX_LEN_PX),
        key=lambda c: c["perp"],
    )
    openings: list[dict] = []
    for i, c1 in enumerate(caps):
        for c2 in caps[i + 1:]:
            width = c2["perp"] - c1["perp"]
            if width < WINDOW_MIN_WIDTH_PX:
                continue
            if width > WINDOW_MAX_WIDTH_PX:
                break  # sorted by perp: no farther cap can be closer
            if min(c1["len"], c2["len"]) / max(c1["len"], c2["len"]) < WINDOW_CAP_LEN_RATIO:
                continue
            overlap = _interval_overlap(c1["span"], c2["span"])
            if overlap < WINDOW_CAP_ALIGN_OVERLAP * min(c1["len"], c2["len"]):
                continue
            band = _spanning_glazing(glaze_pool, c1, c2)
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


def _band_interior_clutter(u_lo: float, u_hi: float, v_lo: float, v_hi: float,
                           ux: float, uy: float, vx: float, vy: float,
                           used_idxs: set[int], glaze_angle: float, cap_angle: float,
                           recs: list[dict], paths: list[PathPrimitive]) -> tuple[int, int]:
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
    line and is likewise excluded.
    """
    shapes = oblique = 0
    for p in paths:
        if p.item_type == "l" or len(p.points) < 2:
            continue
        if any(u_lo <= px * ux + py * uy <= u_hi
               and v_lo <= px * vx + py * vy <= v_hi
               for px, py in p.points):
            shapes += 1
    for r in recs:
        if r["path"].path_index in used_idxs:
            continue
        mx = (r["a"][0] + r["b"][0]) / 2
        my = (r["a"][1] + r["b"][1]) / 2
        if not (u_lo <= mx * ux + my * uy <= u_hi
                and v_lo <= mx * vx + my * vy <= v_hi):
            continue
        if (_angle_diff_mod180(r["angle"], cap_angle) > WINDOW_ANGLE_TOL_DEG
                and _angle_diff_mod180(r["angle"], glaze_angle) > WINDOW_ANGLE_TOL_DEG):
            oblique += 1
    return shapes, oblique


def detect_windows(paths: list[PathPrimitive]) -> list[Candidate]:
    """Detect windows as capped openings bridged by a parallel glazing band.

    For each orientation, find pairs of short perpendicular caps that face each
    other across a window-width gap, then require >=2 distinct parallel glazing
    lines spanning that gap. Door-overlap suppression happens later in
    postprocess (_resolve_door_window_conflicts) using the reliable door
    detector.
    """
    win_keywords = ["window", "wind", "glaz", "glazing"]
    recs = _line_records(paths)
    cap_recs = [r for r in recs
                if WINDOW_CAP_MIN_LEN_PX <= r["len"] <= WINDOW_CAP_MAX_LEN_PX]

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
        for opening in _find_openings(caps, glaze_pool):
            c1, c2, band = opening["c1"], opening["c2"], opening["glaze"]

            cap_len = (c1["len"] + c2["len"]) / 2
            if len(band) < 3 and cap_len < WINDOW_TWO_LINE_MIN_CAP_PX:
                continue  # ambiguous thin-wall / fixture sliver, not a window
            if opening["width"] < WINDOW_MIN_WIDTH_CAP_RATIO * cap_len:
                continue  # opening narrower than the jamb is long: a wall slot, not a window

            bbox: BBox = c1["path"].bbox
            for r in (c2, *band):
                bbox = _bbox_union(bbox, r["path"].bbox)

            # A real window's glass is clear: nothing between the panes. A
            # hatched wall read as a 2-line band has its crosshatch right between
            # its two faces. Reject when the pane band's interior carries it.
            # Measured in the oriented (u, v) frame, confined to the band, so a
            # diagonal window's loose axis bbox and its end jamb fills are excluded.
            used_idxs = {c1["idx"], c2["idx"]} | {r["idx"] for r in band}
            perps = [r["perp"] for r in band]
            v_lo = min(perps) - WINDOW_INTERIOR_BAND_PAD_PX
            v_hi = max(perps) + WINDOW_INTERIOR_BAND_PAD_PX
            shapes, oblique = _band_interior_clutter(
                c1["perp"], c2["perp"], v_lo, v_hi, ux, uy, vx, vy,
                used_idxs, glaze_angle, cap_angle, recs, paths)
            if shapes > WINDOW_INTERIOR_SHAPE_MAX or oblique > WINDOW_INTERIOR_OBLIQUE_MAX:
                continue

            group_paths = [c1["path"], c2["path"]] + [r["path"] for r in band]
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
