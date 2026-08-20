"""takeoff.json — the document the web app's overlay and assembly table are
both built from.

Rooms and openings are sibling arrays cross-referenced by id: one physical
opening is one record carrying every room it serves, rather than a copy under
each. Geometry is 150-DPI pixels, the same space as final_entities.json and
render.png, with page_frame recording that space explicitly.

Serialisation only — takeoff/quantities.py does the maths.
"""
from __future__ import annotations

from takeoff.quantities import OpeningTakeoff, RoomTakeoff, TakeoffPage

# Bumped only on a breaking change to the shape below.
SCHEMA_VERSION = 1


def room_dict(room: RoomTakeoff) -> dict:
    """One room: geometry, its opening ids, and its quantities.

    `quantities` is None rather than a dict of nulls when no scale resolved —
    the absence of numbers is the fact, and a caller testing `if
    room["quantities"]` gets the right answer.
    """
    quantities = None
    if room.measured:
        quantities = {
            "floor_m2": room.floor_m2,
            "ceiling_m2": room.ceiling_m2,
            "perimeter_m": room.perimeter_m,
            "height_m": room.height_m,
            "height_source": room.height_source,
            "wall_gross_m2": room.wall_gross_m2,
            "wall_net_m2": room.wall_net_m2,
        }
    return {
        "room_id": room.room_id,
        "label": room.label,
        "confidence": room.confidence,
        "bbox": list(room.bbox),
        "polygon": [list(p) for p in room.polygon],
        "opening_ids": list(room.opening_ids),
        "scale": room.scale.to_dict() if room.scale is not None else None,
        "mm_per_px": room.mm_per_px,
        "quantities": quantities,
        "assumptions": list(room.assumptions),
    }


def attributes_by_room(page: TakeoffPage) -> dict:
    """The per-room quantity block mirrored onto Entity.attributes["takeoff"].

    Lives here, not on TakeoffPage, because it is serialisation: putting it on
    the dataclass forced quantities.py to import document.py at call time,
    which made the dependency run both ways.

    Unmeasured rooms are skipped — the key means "here are the quantities",
    and a room with no scale has none.
    """
    out = {}
    for room in page.rooms:
        if not room.measured:
            continue
        d = room_dict(room)
        d.pop("room_id")
        d.pop("label")
        # Geometry already lives on the Entity this block is attached to —
        # mirroring it here duplicates the polygon byte-for-byte.
        d.pop("bbox")
        d.pop("polygon")
        d.pop("confidence")
        out[room.room_id] = d
    return out


def opening_dict(op: OpeningTakeoff) -> dict:
    """One door or window. `room_ids` is empty when it reached no room;
    `dropped_room_ids` records rooms the two-room cap discarded."""
    d = {
        "opening_id": op.opening_id,
        "type": op.type,
        "assembly_type": op.assembly_type,
        "tag": op.tag,
        "confidence": op.confidence,
        "bbox": [round(v, 1) for v in op.bbox],
        "room_ids": list(op.room_ids),
        "dropped_room_ids": list(op.dropped_room_ids),
        "width_px": op.width_px,
        "width_source": op.width_source,
        "width_m": op.width_m,
        "height_m": op.height_m,
        "area_m2": op.area_m2,
    }
    if op.clamped:
        d["clamped"] = True
    return d


def to_document(page: TakeoffPage) -> dict:
    """The whole page as one document."""
    # Seed the shape: scale_block is empty for a page not built by
    # compute_takeoff, and a missing key is worse for a consumer than an
    # empty one.
    scale = {"by_region": {}, "page_scale": None}
    scale.update(page.scale_block)
    scale["page"] = scale.pop("page_scale", None)
    scale["evidence"] = {
        "dimensions": [m.to_dict() for m in page.dimension_matches],
        "verdicts": {f"{D:g}": v.to_dict() for D, v in page.verdicts.items()},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "page_number": page.page_number,
        "page_frame": page.page_frame.to_dict() if page.page_frame else None,
        "scale": scale,
        "heights": page.heights.to_dict(),
        "rooms": [room_dict(r) for r in page.rooms],
        "openings": [opening_dict(o) for o in page.openings],
        "totals": page.totals(),
        "warnings": [dict(w) for w in page.warnings],
    }
