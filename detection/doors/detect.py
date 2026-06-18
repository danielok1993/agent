from __future__ import annotations
from models import PathPrimitive, TextSpan, Candidate
from debug.trace import DebugTraceCollector
from detection.doors.arcs import _collect_door_swings
from detection.doors.leaves import _collect_door_leaves
from detection.doors.assembly import _pair_door_assemblies, _merge_double_door_assemblies


def detect_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None = None,
) -> list[Candidate]:
    if collector:
        collector.init_primitives(paths)
    swings = _collect_door_swings(paths, collector)
    leaves = _collect_door_leaves(paths, collector)
    candidates = _pair_door_assemblies(swings, leaves, text_spans, paths, collector)
    return _merge_double_door_assemblies(candidates)
