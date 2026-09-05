"""Door / window openings: how wide, and which rooms they belong to.

Width comes from detector evidence when it exists — a swing bbox is roughly
square (leaf + arc) and a sliding/folding bbox is ~2× the opening (parked
panel / stack), so the bbox alone is the wrong measure for most doors. Only
the bare fallback reads the bbox, and then the edge nearest the room
boundary.

A SINGLE swing's `opening_line` is not the opening: assembly.py sets it to
the two swing-arc endpoints, which for a quarter swing stand 90° apart, so
the chord measures r·√2 while the door it closes is r wide (measured on s02:
1.08 m against a 0.762 m leaf). Only a merged pair's `opening_line` — the
farthest-apart endpoints of BOTH halves — spans the opening. Singles are
therefore measured by their arc radius instead.

Assignment is geometric, and capped at two rooms: a door serves at most two
spaces, so when the grown polygons of three or more touch one bbox, only the
two whose boundary lies nearest the bbox centre keep it.

An opening belongs to every room whose standoff-corrected polygon, grown by
the seal reach, touches its bbox — an internal door deducts on both sides, an
external one on one.
"""
from __future__ import annotations

import math
from typing import Optional

from shapely.geometry import Point, Polygon, box

from detection.rooms import ROOM_OPENING_SEAL_PX

# Callers pass standoff-corrected polygons (already +ROOM_WALL_DILATE_PX), so
# only the seal reach is added here: 2 + 15 = 17 px from the detected polygon.
OPENING_ASSIGN_BUFFER_PX = ROOM_OPENING_SEAL_PX

# A door/window separates at most two spaces.
OPENING_MAX_ROOMS = 2

# Door assemblies whose `opening_line` really spans the opening: the merge
# recomputes it across both halves. Everything else with a swing arc is a
# single leaf, whose arc chord overshoots the opening by up to √2.
_MERGED_DOOR_TYPES = frozenset({"double_swing"})
_SINGLE_SWING_TYPES = frozenset({"single", "single_line_leaf"})
_ARCLESS_DOOR_TYPES = frozenset({"sliding", "folding"})


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


def _arc_radius(arc_bbox) -> Optional[float]:
    """The swing radius: the arc's bbox is r × r for a quarter, r × r for a
    half sweep's half-disc too, so the longer side is the radius."""
    try:
        x0, y0, x1, y1 = (float(v) for v in arc_bbox)
    except (TypeError, ValueError):
        return None
    return _positive(max(x1 - x0, y1 - y0))


def _single_swing_width(evidence: dict) -> Optional[tuple[float, str]]:
    """Radius (then leaf length) for a single leaf; None if it is not one."""
    atype = evidence.get("assembly_type")
    if atype not in _SINGLE_SWING_TYPES:
        # Untyped legacy evidence: an arc bbox with no merged/arcless type is
        # a single leaf too.
        if atype in _MERGED_DOOR_TYPES or atype in _ARCLESS_DOOR_TYPES:
            return None
        if not evidence.get("arc_bbox"):
            return None
    r = _arc_radius(evidence.get("arc_bbox"))
    if r is not None:
        return r, "arc_radius"
    leaf = _positive(evidence.get("leaf_line_length_px"))
    if leaf is not None:
        return leaf, "leaf_line_length_px"
    return None


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


def opening_width_px_from_evidence(entity_type: str, evidence: dict):
    """Width from detector evidence alone, or None.

    Separated from opening_width_px because an UNASSIGNED opening has no room
    boundary to measure a bbox edge against, and the page-level opening record
    still wants whatever width the detector did establish.
    """
    evidence = evidence or {}
    if entity_type == "window":
        if evidence.get("orientation") == "diagonal":
            # An angled bay face: the axis-aligned opening width is the
            # glazing run's projection, the run itself is what is built.
            w = _positive(evidence.get("glazing_len_px"))
            if w is not None:
                return w, "glazing_len_px"
        w = _positive(evidence.get("opening_width_px"))
        if w is not None:
            return w, "opening_width_px"
        return None

    single = _single_swing_width(evidence)
    if single is not None:
        return single
    for key in ("opening_line",):
        w = _chord_length(evidence.get(key))
        if w is not None:
            return w, key
    for key in ("opening_span_px", "panel_length_px"):
        w = _positive(evidence.get(key))
        if w is not None:
            return w, key
    return None


def opening_width_px(entity_type: str, bbox, evidence: dict,
                     room_polygon: Polygon) -> tuple[float, str]:
    hit = opening_width_px_from_evidence(entity_type, evidence)
    if hit is not None:
        return hit
    return _bbox_edge_along_boundary(bbox, room_polygon), "bbox_edge"


def assign_openings(room_polygons: dict, openings: list) -> tuple[dict, list, list]:
    """(assigned, unassigned, over_assigned) for the page's openings.

    `over_assigned` records the rooms dropped by the two-room cap as
    (entity_id, [room_id, ...]) — an audit trail for a bbox that reached
    three spaces at once, which means the seal reach or the bbox is too big.
    """
    grown = {rid: poly.buffer(OPENING_ASSIGN_BUFFER_PX) for rid, poly in room_polygons.items()}
    assigned: dict[str, list[str]] = {}
    unassigned: list[str] = []
    over_assigned: list[tuple[str, list[str]]] = []
    for entity_id, _entity_type, bbox in openings:
        b = box(*bbox)
        hits = [rid for rid, poly in grown.items() if poly.intersects(b)]
        if not hits:
            unassigned.append(entity_id)
            continue
        if len(hits) > OPENING_MAX_ROOMS:
            centre = Point((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            nearest = sorted(hits, key=lambda rid: room_polygons[rid].exterior.distance(centre))
            keep = set(nearest[:OPENING_MAX_ROOMS])
            over_assigned.append((entity_id, [rid for rid in hits if rid not in keep]))
            hits = [rid for rid in hits if rid in keep]
        for rid in hits:
            assigned.setdefault(rid, []).append(entity_id)
    return assigned, unassigned, over_assigned
