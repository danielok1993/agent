from __future__ import annotations
import statistics
from models import Candidate, PageData
from debug.trace import DebugTraceCollector
from detection.doors.detect import detect_doors
from detection.walls import _stroke_percentile_rank, _wall_material_evidence, detect_walls
from detection.windows import detect_windows
from detection.labels import detect_labels
from detection.schedules import detect_schedules
from detection.postprocess import (
    _cross_validate, _resolve_door_window_conflicts, _resolve_wall_window_conflicts, _suppress,
)


def run_heuristics(
    page_data: PageData,
    plumber_tables: list[list[list[str | None]]],
    disable_walls: bool = False,
    disable_windows: bool = False,
    collector: DebugTraceCollector | None = None,
) -> list[Candidate]:
    all_stroke_widths = [p.stroke_width for p in page_data.paths if p.stroke_width > 0]

    doors = detect_doors(page_data.paths, page_data.text_spans, collector)
    windows = [] if disable_windows else detect_windows(page_data.paths)
    walls = [] if disable_walls else detect_walls(page_data.paths)

    # Annotate wall candidates with relative stroke-width evidence
    for w in walls:
        material = _wall_material_evidence(page_data.paths, w.bbox)
        w.evidence.update(material)
        if material["wall_material"]:
            w.confidence = round(min(w.confidence + 0.10, 0.90), 3)

        layer = w.evidence.get("layer")
        matching = [
            p for p in page_data.paths
            if p.item_type == "l" and p.layer == layer
        ]
        if matching:
            avg_sw = statistics.mean(p.stroke_width for p in matching)
            w.evidence["stroke_percentile"] = round(
                _stroke_percentile_rank(avg_sw, all_stroke_widths), 3
            )

    # Door symbols share the glazing-pane signature; the reliable door detector
    # suppresses any window candidate sitting on a door (no wall dependency).
    windows = _resolve_door_window_conflicts(doors + windows)
    windows = [c for c in windows if c.entity_type == "window"]

    all_geo = _cross_validate(doors + windows, walls) + walls
    all_geo = _suppress(all_geo)
    all_geo = _resolve_wall_window_conflicts(all_geo)

    labels = detect_labels(page_data.text_spans, all_geo)
    schedules = detect_schedules(page_data.text_spans, plumber_tables)

    return _suppress(_resolve_wall_window_conflicts(all_geo + labels + schedules))
