from __future__ import annotations
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_union, _interval_overlap, _line_length
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

WINDOW_AXIS_TOL_PX          = 1.5    # max off-axis deviation to call a line H or V
WINDOW_CAP_MIN_LEN_PX       = 3.0    # tiny caps exist (5-1133 bonus window: ~5px)
WINDOW_CAP_MAX_LEN_PX       = 34.0   # caps are short; longer perpendiculars are walls
                                     # (5-1133 Window B caps overshoot to 30px)
WINDOW_CAP_LEN_RATIO        = 0.60   # the two caps must be of similar length
WINDOW_CAP_ALIGN_OVERLAP    = 0.60   # their perp-extents must overlap (truly facing)
WINDOW_MIN_WIDTH_PX         = 14.0   # opening width (gap between caps); bonus ~20px
WINDOW_MAX_WIDTH_PX         = 240.0  # 5-1133 Window B is 173px; caps wall/decoration runs
WINDOW_GLAZING_THICKNESS_PX = 16.0   # max perp-spread of the glazing band (Window A ~14px)
WINDOW_GLAZING_ADJ_SPACING_PX = 8.5  # max gap between adjacent panes (Window B ~7.6px;
                                     # rejects stair treads / widely-spaced parallels)
WINDOW_GLAZING_DISTINCT_EPS = 1.5    # glazing lines closer than this in perp are one pane
WINDOW_MIN_GLAZING_LINES    = 2      # >=2 distinct parallel panes must span the gap
WINDOW_TWO_LINE_MIN_CAP_PX  = 12.0   # a 2-pane opening needs real jamb caps (wall-thickness,
                                     # ~20-30px) to outrank a thin wall / fixture sliver;
                                     # small-cap windows must show >=3 panes (5-1133 bonus)
WINDOW_SPAN_COVER_TOL_PX    = 4.0    # a glazing line may fall short of each cap by this
WINDOW_SPAN_OVERSHOOT_PX    = 12.0   # ...and run at most this far PAST each cap (real
                                     # glazing overshoots ~7.5px; walls run hundreds past)
WINDOW_SPAN_PERP_TOL_PX     = 2.0    # glazing perp may sit this far outside the cap extent
WINDOW_MIN_CONFIDENCE       = 0.50


def _axis_lines(paths: list[PathPrimitive]) -> tuple[list[dict], list[dict]]:
    """Split axis-aligned line primitives into horizontal and vertical pools.

    Each record carries: idx, path, len, ``perp`` (the constant coordinate — y
    for horizontal, x for vertical) and ``span`` (lo, hi along the run axis — x
    for horizontal, y for vertical).
    """
    horiz: list[dict] = []
    vert: list[dict] = []
    for p in paths:
        if p.item_type != "l" or len(p.points) < 2:
            continue
        a, b = p.points[0], p.points[-1]
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        length = _line_length(a, b)
        if length < 1e-6:
            continue
        if dy <= WINDOW_AXIS_TOL_PX and dx > dy:
            horiz.append({"idx": p.path_index, "path": p, "len": length,
                          "perp": (a[1] + b[1]) / 2,
                          "span": (min(a[0], b[0]), max(a[0], b[0]))})
        elif dx <= WINDOW_AXIS_TOL_PX and dy > dx:
            vert.append({"idx": p.path_index, "path": p, "len": length,
                         "perp": (a[0] + b[0]) / 2,
                         "span": (min(a[1], b[1]), max(a[1], b[1]))})
    return horiz, vert


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


def detect_windows(paths: list[PathPrimitive]) -> list[Candidate]:
    """Detect windows as capped openings bridged by a parallel glazing band.

    For each orientation, find pairs of short perpendicular caps that face each
    other across a window-width gap, then require >=2 distinct parallel glazing
    lines spanning that gap. Door-overlap suppression happens later in
    postprocess (_resolve_door_window_conflicts) using the reliable door
    detector.
    """
    win_keywords = ["window", "wind", "glaz", "glazing"]
    horiz, vert = _axis_lines(paths)

    # Horizontal window: vertical caps, horizontal glazing.
    # Vertical window:   horizontal caps, vertical glazing.
    oriented = {"H": (vert, horiz), "V": (horiz, vert)}

    raw: list[Candidate] = []
    cand_idx = 0
    for orient, (cap_pool, glaze_pool) in oriented.items():
        for opening in _find_openings(cap_pool, glaze_pool):
            c1, c2, band = opening["c1"], opening["c2"], opening["glaze"]

            cap_len = (c1["len"] + c2["len"]) / 2
            if len(band) < 3 and cap_len < WINDOW_TWO_LINE_MIN_CAP_PX:
                continue  # ambiguous thin-wall / fixture sliver, not a window

            bbox: BBox = c1["path"].bbox
            for r in (c2, *band):
                bbox = _bbox_union(bbox, r["path"].bbox)

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
                    "orientation": "horizontal" if orient == "H" else "vertical",
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
