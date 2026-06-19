from __future__ import annotations
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_union, _interval_overlap, _line_length, _projected_interval
from detection.layers import _layer_hint, _layer_strong_prior

# ---------------------------------------------------------------------------
# Window detection constants
# ---------------------------------------------------------------------------
# A window is drawn as a thin glazing rectangle: a tight cluster of parallel,
# equal-length "glazing" lines (the glass-pane edges plus a centerline) closed
# at both ends by short perpendicular "cap" lines. Ground truth on
# floor-plans.pdf showed all four real windows are n>=3 glazing clusters with
# matched caps; every n==2 cluster was a fixture/door (false positive). See
# docs/window-detection-tuning-guide.md for the topology reference.

WINDOW_AXIS_TOL_PX          = 1.5   # max off-axis deviation to call a line H or V
WINDOW_MIN_GLAZING_LEN_PX   = 15.0  # shortest plausible glazing run
WINDOW_MAX_GLAZING_LEN_PX   = 220.0 # longest (caps out decorative / wall runs)
WINDOW_MIN_GLAZING_LINES    = 3     # glass edges + centerline; n==2 are FPs here
WINDOW_MAX_GLAZING_LINES    = 6
WINDOW_GLAZING_ADJ_SPACING_PX = 4.0 # max gap between adjacent lines in a cluster
WINDOW_GLAZING_THICKNESS_PX = 8.0   # max total cluster depth (pane thickness)
WINDOW_GLAZING_LEN_RATIO    = 0.80  # cluster lines must be near-equal length
WINDOW_GLAZING_OVERLAP      = 0.80  # and project onto each other (aligned extents)
WINDOW_CAP_END_TOL_PX       = 4.0   # cap must sit within this of a glazing span end
WINDOW_CAP_MAX_LEN_PX       = 30.0  # caps are short; longer perpendiculars are walls
WINDOW_CAP_CROSS_TOL_PX     = 3.0   # cap must cross the glazing centerline within this
WINDOW_MIN_CONFIDENCE       = 0.50


def _axis_lines(paths: list[PathPrimitive]) -> tuple[list[dict], list[dict]]:
    """Split axis-aligned line primitives into horizontal and vertical pools.

    Each record carries: idx, path, length, ``perp`` (the constant coordinate —
    y for horizontal, x for vertical) and ``span`` (lo, hi along the run axis —
    x for horizontal, y for vertical).
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


def _aligned(a: dict, b: dict) -> bool:
    """Two parallel lines are near-equal length and project onto each other."""
    lr = min(a["len"], b["len"]) / max(a["len"], b["len"])
    if lr < WINDOW_GLAZING_LEN_RATIO:
        return False
    ov = _interval_overlap(a["span"], b["span"])
    return ov >= WINDOW_GLAZING_OVERLAP * min(a["len"], b["len"])


def _cluster_glazing(lines: list[dict]) -> list[list[dict]]:
    """Greedily group tight, aligned, near-equal-length parallel lines.

    A line joins a cluster when it sits within WINDOW_GLAZING_ADJ_SPACING_PX of a
    member and is aligned with it, provided the cluster's total depth stays under
    WINDOW_GLAZING_THICKNESS_PX. Returns clusters of >= WINDOW_MIN_GLAZING_LINES.
    """
    lines = sorted(lines, key=lambda r: r["perp"])
    used = set()
    clusters: list[list[dict]] = []
    for i, li in enumerate(lines):
        if i in used:
            continue
        group = [i]
        lo = hi = li["perp"]
        for j in range(i + 1, len(lines)):
            if j in used:
                continue
            lj = lines[j]
            if lj["perp"] - hi > WINDOW_GLAZING_ADJ_SPACING_PX:
                break
            if max(hi, lj["perp"]) - min(lo, li["perp"]) > WINDOW_GLAZING_THICKNESS_PX:
                continue
            if any(abs(lj["perp"] - lines[g]["perp"]) <= WINDOW_GLAZING_ADJ_SPACING_PX
                   and _aligned(lj, lines[g]) for g in group):
                group.append(j)
                lo, hi = min(lo, lj["perp"]), max(hi, lj["perp"])
        if len(group) >= WINDOW_MIN_GLAZING_LINES:
            used.update(group)
            clusters.append([lines[g] for g in group])
    return clusters


def _find_cap(perp_pool: list[dict], end: float, centerline: float) -> dict | None:
    """A short perpendicular line sitting at a glazing span end and crossing it.

    ``end`` is the glazing span coordinate to match against the cap's constant
    coordinate; ``centerline`` is the glazing cluster's perpendicular position,
    which the cap's own span must cover.
    """
    for c in perp_pool:
        if c["len"] > WINDOW_CAP_MAX_LEN_PX:
            continue
        if abs(c["perp"] - end) > WINDOW_CAP_END_TOL_PX:
            continue
        if (c["span"][0] - WINDOW_CAP_CROSS_TOL_PX <= centerline
                <= c["span"][1] + WINDOW_CAP_CROSS_TOL_PX):
            return c
    return None


def detect_windows(paths: list[PathPrimitive]) -> list[Candidate]:
    """Detect windows as capped glazing rectangles.

    For each orientation, cluster tight parallel glazing lines, then require a
    short perpendicular cap at each end of the cluster's span (a closed thin
    rectangle). Door-overlap suppression happens later in postprocess
    (_resolve_door_window_conflicts) using the reliable door detector.
    """
    win_keywords = ["window", "wind", "glaz", "glazing"]
    horiz, vert = _axis_lines(paths)

    glazing_pools = {
        "H": [r for r in horiz if WINDOW_MIN_GLAZING_LEN_PX <= r["len"] <= WINDOW_MAX_GLAZING_LEN_PX],
        "V": [r for r in vert if WINDOW_MIN_GLAZING_LEN_PX <= r["len"] <= WINDOW_MAX_GLAZING_LEN_PX],
    }
    cap_pools = {"H": vert, "V": horiz}   # caps run perpendicular to the glazing

    candidates: list[Candidate] = []
    cand_idx = 0
    for orient in ("H", "V"):
        for cluster in _cluster_glazing(glazing_pools[orient]):
            if len(cluster) > WINDOW_MAX_GLAZING_LINES:
                cluster = cluster[:WINDOW_MAX_GLAZING_LINES]
            centerline = sum(r["perp"] for r in cluster) / len(cluster)
            span0 = min(r["span"][0] for r in cluster)
            span1 = max(r["span"][1] for r in cluster)

            cap_lo = _find_cap(cap_pools[orient], span0, centerline)
            cap_hi = _find_cap(cap_pools[orient], span1, centerline)
            if cap_lo is None or cap_hi is None:
                continue

            bbox: BBox = cluster[0]["path"].bbox
            for r in cluster:
                bbox = _bbox_union(bbox, r["path"].bbox)
            bbox = _bbox_union(_bbox_union(bbox, cap_lo["path"].bbox), cap_hi["path"].bbox)

            group_paths = [r["path"] for r in cluster] + [cap_lo["path"], cap_hi["path"]]
            layer_hint = any(_layer_hint(p, win_keywords) for p in group_paths)
            layer_prior = max((_layer_strong_prior(p, win_keywords) for p in group_paths), default=0.0)

            confidence = 0.62
            confidence += 0.05 * (len(cluster) - WINDOW_MIN_GLAZING_LINES)
            confidence += layer_prior
            if layer_hint and layer_prior == 0.0:
                confidence += 0.10
            confidence = min(confidence, 0.90)
            if confidence < WINDOW_MIN_CONFIDENCE:
                continue

            candidates.append(Candidate(
                candidate_id=f"window_{cand_idx:04d}",
                entity_type="window",
                bbox=bbox,
                confidence=round(confidence, 3),
                evidence={
                    "orientation": "horizontal" if orient == "H" else "vertical",
                    "glazing_lines": len(cluster),
                    "glazing_len_px": round(sum(r["len"] for r in cluster) / len(cluster), 1),
                    "cap_len_px": round((cap_lo["len"] + cap_hi["len"]) / 2, 1),
                    "layer_hint": layer_hint,
                },
            ))
            cand_idx += 1

    return candidates
