from __future__ import annotations
import logging
import time
from contextlib import contextmanager

from models import Candidate, PageData, TextSpan
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

logger = logging.getLogger(__name__)


@contextmanager
def _stage(name: str):
    """Per-stage wall-clock log line. Detection on 100k+-path sheets runs for
    minutes to hours (s16: >58 min pre-rooms, 2026-08-04 findings); these
    lines attribute the time without needing root for a profiler."""
    t0 = time.monotonic()
    yield
    logger.info("%s: %.2fs", name, time.monotonic() - t0)


def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
    disable_walls: bool = False,   # deprecated alias for disable_rooms
    disable_windows: bool = False,
    collector: DebugTraceCollector | None = None,
    disable_rooms: bool = False,
    schedule_text_spans: list[TextSpan] | None = None,
) -> list[Candidate]:
    disable_rooms = disable_rooms or disable_walls

    with _stage("doors"):
        doors = detect_doors(page_data.paths, page_data.text_spans, collector)
    with _stage("windows"):
        windows = [] if disable_windows else detect_windows(page_data.paths)

        # Door symbols share the glazing-pane signature; the reliable door
        # detector suppresses any window candidate sitting on a door (no wall
        # dependency).
        windows = _resolve_door_window_conflicts(doors + windows)
        windows = [c for c in windows if c.entity_type == "window"]

    # Internal wall-centerline network: never emitted as candidates; feeds
    # cross-validation and room polygonization. Text spans disambiguate
    # white fills (text masks vs hollow walls). Swing doors detect first,
    # so their open-leaf linework — wall-pen ink standing parallel to real
    # walls — is excluded from face pairing before it can inflate a band.
    with _stage("wall_network"):
        network = None if disable_rooms else detect_wall_network(
            page_data.paths, page_data.text_spans,
            exclude_path_indices=door_open_leaf_path_indices(
                doors, page_data.paths
            ),
        )

    with _stage("cross_validate"):
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
    with _stage("rooms"):
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
    with _stage("labels"):
        labels = detect_labels(page_data.text_spans, all_geo)

    # Schedules live outside the floor plans, so when the page carries
    # schedule_table regions their text is passed in separately rather than
    # coming from the (floor-plan-filtered) page_data.
    with _stage("schedules"):
        schedules = detect_schedules(
            page_data.text_spans if schedule_text_spans is None else schedule_text_spans,
            plumber_tables,
        )

    return _suppress(all_geo + labels + schedules) + rooms
