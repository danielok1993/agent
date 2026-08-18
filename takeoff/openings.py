"""Door / window openings: how wide, and which rooms they belong to.

Width comes from detector evidence when it exists — a swing bbox is roughly
square (leaf + arc) and a sliding/folding bbox is ~2× the opening (parked
panel / stack), so the bbox alone is the wrong measure for most doors. Only
the bare fallback reads the bbox, and then the edge that lies along the room
boundary, never the longer side.

Assignment is geometric: an opening belongs to every room whose
standoff-corrected polygon, grown by the seal reach, touches its bbox — an
internal door deducts on both sides, an external one on one.
"""
from __future__ import annotations

import math
from typing import Optional

from shapely.geometry import Point, Polygon, box

from detection.rooms import ROOM_OPENING_SEAL_PX

# Callers pass standoff-corrected polygons (already +ROOM_WALL_DILATE_PX), so
# only the seal reach is added here: 2 + 12 = 14 px from the detected polygon.
OPENING_ASSIGN_BUFFER_PX = ROOM_OPENING_SEAL_PX


def _positive(value) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _chord_length(line) -> Optional[float]:
    try:
        (x0, y0), (x1, y1) = line
    except (TypeError, ValueError):
        return None
    return _positive(math.hypot(x1 - x0, y1 - y0))


def _bbox_edge_along_boundary(bbox, room_polygon: Polygon) -> float:
    x0, y0, x1, y1 = bbox
    edges = [  # (length, midpoint)
        (x1 - x0, ((x0 + x1) / 2.0, y0)),
        (x1 - x0, ((x0 + x1) / 2.0, y1)),
        (y1 - y0, (x0, (y0 + y1) / 2.0)),
        (y1 - y0, (x1, (y0 + y1) / 2.0)),
    ]
    boundary = room_polygon.exterior
    length, _ = min(edges, key=lambda e: boundary.distance(Point(e[1])))
    return float(length)


def opening_width_px(entity_type: str, bbox, evidence: dict, room_polygon: Polygon) -> tuple[float, str]:
    evidence = evidence or {}
    if entity_type == "window":
        w = _positive(evidence.get("opening_width_px"))
        if w is not None:
            return w, "opening_width_px"
    else:
        for key in ("opening_line",):
            w = _chord_length(evidence.get(key))
            if w is not None:
                return w, key
        for key in ("opening_span_px", "panel_length_px"):
            w = _positive(evidence.get(key))
            if w is not None:
                return w, key
    return _bbox_edge_along_boundary(bbox, room_polygon), "bbox_edge"


def assign_openings(room_polygons: dict, openings: list) -> tuple[dict, list]:
    grown = {rid: poly.buffer(OPENING_ASSIGN_BUFFER_PX) for rid, poly in room_polygons.items()}
    assigned: dict[str, list[str]] = {}
    unassigned: list[str] = []
    for entity_id, _entity_type, bbox in openings:
        b = box(*bbox)
        hit = False
        for rid, poly in grown.items():
            if poly.intersects(b):
                assigned.setdefault(rid, []).append(entity_id)
                hit = True
        if not hit:
            unassigned.append(entity_id)
    return assigned, unassigned
