from __future__ import annotations
from models import BBox, Candidate
from detection.geometry import _bbox_area, _bbox_center, _bbox_expanded, _bbox_height, _bbox_width, _bboxes_overlap, _distance
from detection.doors.assembly import _dedupe_door_components


# ---------------------------------------------------------------------------
# Cross-element validation (soft: boost/penalize confidence)
# ---------------------------------------------------------------------------

CROSS_WALL_EXPAND_PX  = 20.0   # expand wall bbox when checking containment
CROSS_NO_WALL_PENALTY = 0.08   # door/window has no wall nearby → penalty
CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY = 0.04
# Single-line-leaf is the weakest leaf evidence (a single anchored line vs. a
# closed rectangle). Without a surrounding wall AND without a nearby door label,
# the assembly is statistically a bath fixture or window decoration, not a
# door. Apply a stronger penalty than the default door_assembly case so these
# fall below the offline confidence floor.
CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY = 0.15
# No in-wall boost: wall and window candidates share the same raw linework,
# so overlap is structural correlation, not independent evidence.


def _cross_validate(
    candidates: list[Candidate],
    walls: list[Candidate],
) -> list[Candidate]:
    """Soft-penalize doors/windows that have no nearby wall candidate.

    A door or window with no wall anywhere close is likely a false positive
    (an arc or parallel-line cluster in a legend, annotation, or detail).
    True openings always sit in a wall, so the absence of any overlapping wall
    is a reliable negative signal. We do not apply a positive boost when a wall
    is found because wall and window candidates are derived from the same raw
    linework — overlap is geometric correlation, not independent evidence.
    """
    if not walls:
        return candidates

    wall_bboxes = [_bbox_expanded(w.bbox, CROSS_WALL_EXPAND_PX) for w in walls]

    adjusted = []
    for c in candidates:
        if c.entity_type not in ("door", "window"):
            adjusted.append(c)
            continue

        in_wall = any(_bboxes_overlap(c.bbox, wb) for wb in wall_bboxes)
        is_assembly = (
            c.entity_type == "door"
            and c.evidence.get("method") == "door_assembly"
        )
        is_single_line_no_label = (
            is_assembly
            and c.evidence.get("assembly_type") == "single_line_leaf"
            and not c.evidence.get("nearby_label")
        )
        if is_single_line_no_label:
            penalty = CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY
        elif is_assembly:
            penalty = CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY
        else:
            penalty = CROSS_NO_WALL_PENALTY
        delta = 0.0 if in_wall else -penalty
        new_conf = round(min(max(c.confidence + delta, 0.0), 0.95), 3)

        new_evidence = dict(c.evidence)
        new_evidence["wall_context"] = "in_wall" if in_wall else "no_wall"

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


def _bbox_is_horizontal(bbox: BBox) -> bool:
    return _bbox_width(bbox) >= _bbox_height(bbox)


def _resolve_wall_window_conflicts(candidates: list[Candidate]) -> list[Candidate]:
    """Drop window candidates that are materially the same bbox as a wall.

    Real windows overlap walls, but their detected glazing/slab linework should
    not usually have almost the same bbox as the detected wall band. When that
    happens, especially on hatched wall bands, the window was usually created by
    the generic parallel-line grouping rather than by an actual opening.
    """
    walls = [c for c in candidates if c.entity_type == "wall"]
    if not walls:
        return candidates

    resolved: list[Candidate] = []
    for candidate in candidates:
        if candidate.entity_type != "window" or candidate.evidence.get("layer_hint"):
            resolved.append(candidate)
            continue

        duplicate_wall = False
        for wall in walls:
            if _bbox_is_horizontal(candidate.bbox) != _bbox_is_horizontal(wall.bbox):
                continue
            if _bbox_iou(candidate.bbox, wall.bbox) < 0.45:
                continue
            if wall.evidence.get("wall_material") or wall.confidence >= candidate.confidence:
                duplicate_wall = True
                break

        if not duplicate_wall:
            resolved.append(candidate)

    return resolved
