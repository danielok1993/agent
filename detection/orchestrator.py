from __future__ import annotations
from models import Candidate, PageData
from debug.trace import DebugTraceCollector
from detection.doors.assembly import door_open_leaf_path_indices
from detection.doors.detect import detect_doors
from detection.walls import detect_wall_network
from detection.rooms import detect_rooms
from detection.windows import detect_windows
from detection.labels import detect_labels
from detection.schedules import detect_schedules
from detection.postprocess import (
    _cross_validate, _resolve_door_window_conflicts, _suppress,
)


def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
    disable_walls: bool = False,   # deprecated alias for disable_rooms
    disable_windows: bool = False,
    collector: DebugTraceCollector | None = None,
    disable_rooms: bool = False,
) -> list[Candidate]:
    disable_rooms = disable_rooms or disable_walls

    doors = detect_doors(page_data.paths, page_data.text_spans, collector)
    windows = [] if disable_windows else detect_windows(page_data.paths)

    # Door symbols share the glazing-pane signature; the reliable door detector
    # suppresses any window candidate sitting on a door (no wall dependency).
    windows = _resolve_door_window_conflicts(doors + windows)
    windows = [c for c in windows if c.entity_type == "window"]

    # Internal wall-centerline network: never emitted as candidates; feeds
    # cross-validation and room polygonization. Text spans disambiguate
    # white fills (text masks vs hollow walls). Swing doors detect first,
    # so their open-leaf linework — wall-pen ink standing parallel to real
    # walls — is excluded from face pairing before it can inflate a band.
    network = None if disable_rooms else detect_wall_network(
        page_data.paths, page_data.text_spans,
        exclude_path_indices=door_open_leaf_path_indices(
            doors, page_data.paths
        ),
    )

    all_geo = _cross_validate(doors + windows, network)
    all_geo = _suppress(all_geo)

    # Rooms are built from the post-suppression doors/windows so opening
    # seals use surviving candidates only; detect_rooms additionally holds
    # fallback-tier doors (< ROOM_OPENING_MIN_CONFIDENCE) to plug profiles
    # that carry their own evidence — never the dilated-bbox seal — and
    # ignores text-covered door bboxes entirely (annotation tags detected
    # as leaf rectangles), so phantom doors cannot reshape room outlines.
    # Text spans feed both the white-fill disambiguation in the network and
    # that annotation veto.
    rooms = detect_rooms(
        network,
        [c for c in all_geo if c.entity_type == "door"],
        [c for c in all_geo if c.entity_type == "window"],
        page_data.width_px,
        page_data.height_px,
        page_data.text_spans,
    )

    # Rooms are deliberately excluded from label attachment (room-sized bboxes
    # would make every dimension callout "near" something) and from NMS
    # (bboxes of adjacent L-shaped rooms overlap even though the polygon faces
    # are disjoint by construction).
    labels = detect_labels(page_data.text_spans, all_geo)
    schedules = detect_schedules(page_data.text_spans, plumber_tables)

    return _suppress(all_geo + labels + schedules) + rooms
