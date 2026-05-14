from __future__ import annotations
import math
import re
from itertools import combinations
from models import PathPrimitive, TextSpan, Candidate, PageData, BBox

# ---------------------------------------------------------------------------
# Door detection constants
# ---------------------------------------------------------------------------
DOOR_BBOX_ASPECT_MIN        = 0.85   # width/height ratio (roughly square arc)
DOOR_BBOX_ASPECT_MAX        = 1.15
DOOR_MIN_SIZE_PX            = 20.0
DOOR_MAX_SIZE_PX            = 200.0
DOOR_SWING_LINE_DIST_PX     = 15.0  # max px from arc corner to nearby line endpoint
DOOR_LABEL_PATTERN          = re.compile(r"(?i)^[A-Z]?[FD]-?\d{1,3}[A-Z]?$")
DOOR_LABEL_SEARCH_RADIUS_PX = 100.0
DOOR_MIN_CONFIDENCE         = 0.40

# ---------------------------------------------------------------------------
# Window detection constants
# ---------------------------------------------------------------------------
WINDOW_MIN_LINES            = 2
WINDOW_MAX_LINES            = 6
WINDOW_PARALLEL_ANGLE_TOL   = 8.0   # degrees
WINDOW_LENGTH_RATIO_MIN     = 0.80
WINDOW_SPACING_MIN_PX       = 3.0
WINDOW_SPACING_MAX_PX       = 50.0
WINDOW_MIN_LENGTH_PX        = 15.0
WINDOW_MAX_LENGTH_PX        = 350.0
WINDOW_GROUPING_GAP_PX      = 8.0
WINDOW_MIN_CONFIDENCE       = 0.35

# ---------------------------------------------------------------------------
# Wall detection constants
# ---------------------------------------------------------------------------
WALL_MIN_LENGTH_PX          = 60.0
WALL_MAX_OFFSET_PX          = 30.0
WALL_PARALLEL_ANGLE_TOL     = 5.0   # degrees
WALL_LENGTH_RATIO_MIN       = 0.85
WALL_MIN_STROKE_WIDTH_PX    = 0.5
WALL_MIN_CONFIDENCE         = 0.50

# ---------------------------------------------------------------------------
# Label detection constants
# ---------------------------------------------------------------------------
LABEL_PATTERN               = re.compile(r"(?i)^[A-Z]{0,3}-?\d{1,4}[A-Z]?$")
LABEL_MAX_FONT_SIZE_PT      = 14.0
LABEL_MIN_FONT_SIZE_PT      = 4.0
LABEL_SEARCH_RADIUS_PX      = 80.0

# ---------------------------------------------------------------------------
# Schedule detection constants
# ---------------------------------------------------------------------------
SCHEDULE_TABLE_MIN_ROWS     = 3
SCHEDULE_TABLE_MIN_COLS     = 2
SCHEDULE_MIN_CELL_DENSITY   = 0.15
SCHEDULE_KEYWORDS           = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|mark|width|height)"
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _bbox_center(bbox: BBox) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _line_length(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return _distance(p1, p2)


def _line_angle_deg(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx)) % 180.0


def _bbox_width(bbox: BBox) -> float:
    return abs(bbox[2] - bbox[0])


def _bbox_height(bbox: BBox) -> float:
    return abs(bbox[3] - bbox[1])


def _is_arc_like(path: PathPrimitive) -> bool:
    if path.item_type not in ("c", "mixed"):
        return False
    w = _bbox_width(path.bbox)
    h = _bbox_height(path.bbox)
    if h < 1e-6:
        return False
    aspect = w / h
    size = max(w, h)
    return (
        DOOR_BBOX_ASPECT_MIN <= aspect <= DOOR_BBOX_ASPECT_MAX
        and DOOR_MIN_SIZE_PX <= size <= DOOR_MAX_SIZE_PX
    )


def _is_line_path(path: PathPrimitive) -> tuple[bool, tuple[float, float], tuple[float, float]]:
    if path.item_type != "l" or len(path.points) < 2:
        return False, (0, 0), (0, 0)
    return True, path.points[0], path.points[-1]


def _arc_corners(arc: PathPrimitive) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = arc.bbox
    return [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]


def _layer_hint(path: PathPrimitive, keywords: list[str]) -> bool:
    if not path.layer:
        return False
    layer_lower = path.layer.lower()
    return any(kw in layer_lower for kw in keywords)


# ---------------------------------------------------------------------------
# Door detection
# ---------------------------------------------------------------------------

def detect_doors(paths: list[PathPrimitive], text_spans: list[TextSpan]) -> list[Candidate]:
    arc_paths = [p for p in paths if _is_arc_like(p)]
    line_paths = [p for p in paths if p.item_type == "l"]

    candidates = []
    for arc_idx, arc in enumerate(arc_paths):
        arc_corners = _arc_corners(arc)
        arc_size = max(_bbox_width(arc.bbox), _bbox_height(arc.bbox))

        swing_line_found = False
        swing_dist = None
        for lp in line_paths:
            ok, p1, p2 = _is_line_path(lp)
            if not ok:
                continue
            line_len = _line_length(p1, p2)
            if line_len < DOOR_MIN_SIZE_PX or line_len > DOOR_MAX_SIZE_PX * 1.5:
                continue
            for corner in arc_corners:
                d1 = _distance(corner, p1)
                d2 = _distance(corner, p2)
                if min(d1, d2) <= DOOR_SWING_LINE_DIST_PX:
                    swing_line_found = True
                    swing_dist = min(d1, d2)
                    break
            if swing_line_found:
                break

        nearby_label = _find_nearby_label(arc.bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN)
        layer_hint = _layer_hint(arc, ["door", "a-door"])

        confidence = 0.50
        if swing_line_found:
            confidence += 0.20
        if nearby_label:
            confidence += 0.20
        if layer_hint:
            confidence += 0.10
        confidence = min(confidence, 0.95)

        if confidence < DOOR_MIN_CONFIDENCE:
            continue

        candidates.append(Candidate(
            candidate_id=f"door_{arc_idx:04d}",
            entity_type="door",
            bbox=arc.bbox,
            confidence=round(confidence, 3),
            evidence={
                "arc_bbox_aspect": round(_bbox_width(arc.bbox) / max(_bbox_height(arc.bbox), 1e-6), 3),
                "arc_size_px": round(arc_size, 1),
                "swing_line_found": swing_line_found,
                "swing_line_dist_px": round(swing_dist, 2) if swing_dist else None,
                "nearby_label": nearby_label,
                "layer": arc.layer,
                "layer_hint": layer_hint,
            },
        ))

    return candidates


# ---------------------------------------------------------------------------
# Window detection
# ---------------------------------------------------------------------------

def detect_windows(paths: list[PathPrimitive]) -> list[Candidate]:
    line_paths = [
        p for p in paths
        if p.item_type == "l" and len(p.points) >= 2
        and WINDOW_MIN_LENGTH_PX <= _line_length(p.points[0], p.points[-1]) <= WINDOW_MAX_LENGTH_PX
    ]

    used = set()
    candidates = []
    cand_idx = 0

    for i, lp in enumerate(line_paths):
        if i in used:
            continue
        p1, p2 = lp.points[0], lp.points[-1]
        angle_i = _line_angle_deg(p1, p2)
        len_i = _line_length(p1, p2)

        group = [lp]
        group_indices = {i}

        for j, lp2 in enumerate(line_paths):
            if j <= i or j in used:
                continue
            q1, q2 = lp2.points[0], lp2.points[-1]
            angle_j = _line_angle_deg(q1, q2)
            len_j = _line_length(q1, q2)

            angle_diff = abs(angle_i - angle_j)
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            if angle_diff > WINDOW_PARALLEL_ANGLE_TOL:
                continue

            if len_j < 1e-6:
                continue
            len_ratio = min(len_i, len_j) / max(len_i, len_j)
            if len_ratio < WINDOW_LENGTH_RATIO_MIN:
                continue

            spacing = _perpendicular_spacing(p1, p2, q1, q2)
            if not (WINDOW_SPACING_MIN_PX <= spacing <= WINDOW_SPACING_MAX_PX):
                continue

            group.append(lp2)
            group_indices.add(j)

            if len(group) >= WINDOW_MAX_LINES:
                break

        if len(group) < WINDOW_MIN_LINES:
            continue

        all_pts = [pt for lp_g in group for pt in [lp_g.points[0], lp_g.points[-1]]]
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        bbox: BBox = (min(xs), min(ys), max(xs), max(ys))

        layer_hint = any(_layer_hint(lp_g, ["window", "win", "glaz", "glazing", "a-glaz", "a-wind"]) for lp_g in group)
        spacing_vals = []
        for lp_g in group[1:]:
            q1, q2 = lp_g.points[0], lp_g.points[-1]
            spacing_vals.append(_perpendicular_spacing(p1, p2, q1, q2))

        confidence = 0.45
        if len(group) >= 3:
            confidence += 0.15
        if layer_hint:
            confidence += 0.15
        if spacing_vals and len(set(round(s, 0) for s in spacing_vals)) == 1:
            confidence += 0.10
        confidence = min(confidence, 0.90)

        if confidence < WINDOW_MIN_CONFIDENCE:
            continue

        for idx in group_indices:
            used.add(idx)

        candidates.append(Candidate(
            candidate_id=f"window_{cand_idx:04d}",
            entity_type="window",
            bbox=bbox,
            confidence=round(confidence, 3),
            evidence={
                "line_count": len(group),
                "avg_length_px": round(sum(_line_length(lp_g.points[0], lp_g.points[-1]) for lp_g in group) / len(group), 1),
                "avg_spacing_px": round(sum(spacing_vals) / len(spacing_vals), 1) if spacing_vals else None,
                "layer_hint": layer_hint,
            },
        ))
        cand_idx += 1

    return candidates


def _perpendicular_spacing(
    p1: tuple[float, float], p2: tuple[float, float],
    q1: tuple[float, float], q2: tuple[float, float],
) -> float:
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return float("inf")
    nx, ny = -dy / length, dx / length
    return abs((q1[0] - p1[0]) * nx + (q1[1] - p1[1]) * ny)


# ---------------------------------------------------------------------------
# Wall detection
# ---------------------------------------------------------------------------

def detect_walls(paths: list[PathPrimitive]) -> list[Candidate]:
    line_paths = [
        p for p in paths
        if p.item_type == "l" and len(p.points) >= 2
        and _line_length(p.points[0], p.points[-1]) >= WALL_MIN_LENGTH_PX
        and p.stroke_width >= WALL_MIN_STROKE_WIDTH_PX
    ]

    used = set()
    candidates = []
    cand_idx = 0

    for i, lp in enumerate(line_paths):
        if i in used:
            continue
        p1, p2 = lp.points[0], lp.points[-1]
        angle_i = _line_angle_deg(p1, p2)
        len_i = _line_length(p1, p2)

        for j, lp2 in enumerate(line_paths):
            if j <= i or j in used:
                continue
            q1, q2 = lp2.points[0], lp2.points[-1]
            angle_j = _line_angle_deg(q1, q2)
            len_j = _line_length(q1, q2)

            angle_diff = abs(angle_i - angle_j)
            if angle_diff > 90:
                angle_diff = 180 - angle_diff
            if angle_diff > WALL_PARALLEL_ANGLE_TOL:
                continue

            if len_j < 1e-6:
                continue
            len_ratio = min(len_i, len_j) / max(len_i, len_j)
            if len_ratio < WALL_LENGTH_RATIO_MIN:
                continue

            spacing = _perpendicular_spacing(p1, p2, q1, q2)
            if spacing > WALL_MAX_OFFSET_PX or spacing < 1.0:
                continue

            all_pts = [p1, p2, q1, q2]
            xs = [p[0] for p in all_pts]
            ys = [p[1] for p in all_pts]
            bbox: BBox = (min(xs), min(ys), max(xs), max(ys))

            layer_hint = _layer_hint(lp, ["wall", "a-wall", "partition", "struct"]) or \
                         _layer_hint(lp2, ["wall", "a-wall", "partition", "struct"])

            confidence = 0.55
            if len_i > 200:
                confidence += 0.15
            if layer_hint:
                confidence += 0.15
            confidence = min(confidence, 0.90)

            if confidence < WALL_MIN_CONFIDENCE:
                continue

            used.add(i)
            used.add(j)

            candidates.append(Candidate(
                candidate_id=f"wall_{cand_idx:04d}",
                entity_type="wall",
                bbox=bbox,
                confidence=round(confidence, 3),
                evidence={
                    "line_length_px": round(len_i, 1),
                    "pair_length_px": round(len_j, 1),
                    "spacing_px": round(spacing, 1),
                    "layer": lp.layer,
                    "layer_hint": layer_hint,
                },
            ))
            cand_idx += 1
            break

    return candidates


# ---------------------------------------------------------------------------
# Label detection
# ---------------------------------------------------------------------------

def _find_nearby_label(
    bbox: BBox,
    text_spans: list[TextSpan],
    radius: float,
    pattern: re.Pattern,
) -> str | None:
    cx, cy = _bbox_center(bbox)
    best = None
    best_dist = float("inf")
    for span in text_spans:
        if not pattern.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue
        scx, scy = _bbox_center(span.bbox)
        d = _distance((cx, cy), (scx, scy))
        if d <= radius and d < best_dist:
            best_dist = d
            best = span.text
    return best


def detect_labels(text_spans: list[TextSpan], candidates: list[Candidate]) -> list[Candidate]:
    label_candidates = []
    cand_idx = 0
    for span in text_spans:
        if not LABEL_PATTERN.match(span.text):
            continue
        if not (LABEL_MIN_FONT_SIZE_PT <= span.size <= LABEL_MAX_FONT_SIZE_PT):
            continue

        nearest_id = None
        nearest_dist = float("inf")
        for c in candidates:
            d = _distance(_bbox_center(span.bbox), _bbox_center(c.bbox))
            if d < nearest_dist:
                nearest_dist = d
                nearest_id = c.candidate_id

        label_candidates.append(Candidate(
            candidate_id=f"label_{cand_idx:04d}",
            entity_type="label",
            bbox=span.bbox,
            confidence=0.75,
            evidence={
                "text": span.text,
                "font": span.font,
                "size": span.size,
                "nearest_candidate": nearest_id,
                "nearest_dist_px": round(nearest_dist, 1) if nearest_id else None,
            },
        ))
        cand_idx += 1

    return label_candidates


# ---------------------------------------------------------------------------
# Schedule detection
# ---------------------------------------------------------------------------

SCHEDULE_KEYWORDS_RE = re.compile(
    r"(?i)(door\s+schedule|window\s+schedule|frame|leaf|glazing|fire\s+rating|type|mark)"
)


def detect_schedules(
    text_spans: list[TextSpan],
    plumber_tables: list[list[list[str | None]]],
) -> list[Candidate]:
    candidates = []
    cand_idx = 0

    for table in plumber_tables:
        if len(table) < SCHEDULE_TABLE_MIN_ROWS:
            continue
        max_cols = max((len(row) for row in table), default=0)
        if max_cols < SCHEDULE_TABLE_MIN_COLS:
            continue

        total_cells = sum(len(row) for row in table)
        non_empty = sum(1 for row in table for cell in row if cell and str(cell).strip())
        density = non_empty / total_cells if total_cells > 0 else 0
        if density < SCHEDULE_MIN_CELL_DENSITY:
            continue

        all_text = " ".join(
            str(cell) for row in table for cell in row if cell
        )
        is_schedule = bool(SCHEDULE_KEYWORDS_RE.search(all_text))
        confidence = 0.60 if is_schedule else 0.35

        candidates.append(Candidate(
            candidate_id=f"schedule_{cand_idx:04d}",
            entity_type="schedule",
            bbox=(0, 0, 0, 0),  # pdfplumber tables don't always have bbox
            confidence=round(confidence, 3),
            evidence={
                "rows": len(table),
                "cols": max_cols,
                "cell_density": round(density, 3),
                "is_schedule_keyword": is_schedule,
                "sample_text": all_text[:200],
            },
        ))
        cand_idx += 1

    return candidates


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
) -> list[Candidate]:
    doors = detect_doors(page_data.paths, page_data.text_spans)
    windows = detect_windows(page_data.paths)
    walls = detect_walls(page_data.paths)

    all_geo = doors + windows + walls
    labels = detect_labels(page_data.text_spans, all_geo)
    schedules = detect_schedules(page_data.text_spans, plumber_tables)

    return doors + windows + walls + labels + schedules
