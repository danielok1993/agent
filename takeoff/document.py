"""takeoff.json — the document the web app's overlay and assembly table are
both built from.

Rooms and openings are sibling arrays cross-referenced by id: one physical
opening is one record carrying every room it serves, rather than a copy under
each. Geometry is 150-DPI pixels, the same space as final_entities.json and
render.png, with page_frame recording that space explicitly.

Serialisation only — takeoff/quantities.py does the maths.
"""
from __future__ import annotations

import logging
import math

from takeoff.quantities import OpeningTakeoff, RoomTakeoff, TakeoffPage

logger = logging.getLogger(__name__)

# Bumped only on a breaking change to the shape below.
# 2: line_work — the page's wall network, for the review screen's snapping.
SCHEMA_VERSION = 2

# line_work is stored inline in a single Firestore document shared across
# every sheet on the project, capped at 1 MB, and a write over that cap
# raises inside the failure handler after a run that can take 58+ minutes —
# the user gets an opaque Firestore error instead of a diagnosable one. A
# real corpus sheet can carry far more line work than the reference sheet
# s02 (8,542 faces, well under either cap here): docs/2026-08-04-region-
# clip-fix-and-batch-timeout-findings.md records corpus sheets at 127,087
# and 298,603 filtered paths, which at s02's face-to-path ratio is roughly
# 7,500 faces — about 0.7 MB — on a single sheet's `lines` alone. These caps
# bound line_work_dict's output regardless of how large the source drawing
# is. See line_work_dict for how entries are chosen when a list is
# truncated.
LINE_WORK_MAX_LINES = 1000
LINE_WORK_MAX_WALLS = 500


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


def _round_point(p) -> list:
    """An endpoint to 2dp. 0.01 page px is 0.085 mm at 1:50 — far below any
    drawing tolerance — and this block is stored inline in a Firestore
    document capped at 1 MB shared across every sheet, so the full float
    precision detection works in is not worth its bytes on the wire."""
    return [round(p[0], 2), round(p[1], 2)]


def _segment_length(p1, p2) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def line_work_dict(network) -> dict:
    """The page's line work, for the review screen's snapping.

    Two lists, because they are two different things. `walls` is what the
    network concluded: centrelines with a measured thickness. `lines` is what
    it collected before concluding anything — every merged face run, paired or
    not.

    Snapping needs the second to work at all on a plan the detector read
    badly, which is the case it exists for; it needs the first so a believed
    wall outranks a worktop edge. `kind` is stated rather than left to the
    client to re-derive from a stroke width.

    Each list is capped (LINE_WORK_MAX_LINES, LINE_WORK_MAX_WALLS — see their
    definitions for why) by sorting candidates by segment length descending
    and keeping the longest. A long run is a wall or a major edge; what gets
    discarded is jamb nibs and joinery stubs, which are also overwhelmingly
    the ones sitting nearest any given cursor position, so the cut costs
    little for snapping. The client needs no change for a truncated list — a
    shorter line_work payload is still a valid one. Truncation is logged, not
    silent: a run that produced far more geometry than expected is exactly
    the case a reviewer needs to be able to see.

    `network` is None when detection ran with rooms disabled, or when
    pipeline.py skips detection for the page entirely (its skip_detection
    path never calls run_heuristics).
    """
    if network is None:
        return {"walls": [], "lines": []}

    # Path index -> the thickness of the centreline that path helped build.
    # Doubles as the paired/unpaired test, so one pass answers both.
    thickness_by_path: dict[int, float] = {}
    for seg in network.segments:
        for index in seg.face_path_indices:
            thickness_by_path.setdefault(index, seg.thickness_px)

    faces_by_length = sorted(
        network.faces, key=lambda f: _segment_length(f.p1, f.p2), reverse=True
    )
    collected_lines = len(faces_by_length)
    kept_faces = faces_by_length[:LINE_WORK_MAX_LINES]
    if collected_lines > LINE_WORK_MAX_LINES:
        logger.info(
            "line_work: lines truncated to the %d longest of %d collected",
            LINE_WORK_MAX_LINES, collected_lines,
        )

    lines = []
    for face in kept_faces:
        # sorted() so a face spanning two walls of different thickness always
        # reports the same one, run to run.
        thickness = next(
            (thickness_by_path[i] for i in sorted(face.indices)
             if i in thickness_by_path),
            None,
        )
        lines.append({
            "a": _round_point(face.p1),
            "b": _round_point(face.p2),
            "kind": "wall_face" if thickness is not None else "line",
            "thickness_px": thickness,
        })

    segments_by_length = sorted(
        network.segments, key=lambda s: _segment_length(s.p1, s.p2), reverse=True
    )
    collected_walls = len(segments_by_length)
    kept_segments = segments_by_length[:LINE_WORK_MAX_WALLS]
    if collected_walls > LINE_WORK_MAX_WALLS:
        logger.info(
            "line_work: walls truncated to the %d longest of %d collected",
            LINE_WORK_MAX_WALLS, collected_walls,
        )

    return {
        "walls": [
            {
                "centreline": [_round_point(s.p1), _round_point(s.p2)],
                "thickness_px": s.thickness_px,
            }
            for s in kept_segments
        ],
        "lines": lines,
    }


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
        "line_work": line_work_dict(page.wall_network),
    }
