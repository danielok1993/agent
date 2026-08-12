from __future__ import annotations
from models import PathPrimitive, TextSpan, Candidate
from debug.trace import DebugTraceCollector
from detection.doors.constants import DoorGates
from detection.doors.arcs import _collect_door_swings
from detection.doors.leaves import _collect_door_leaves
from detection.doors.assembly import _pair_door_assemblies, _merge_double_door_assemblies


def detect_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None = None,
    scale_factor: float = 1.0,
) -> list[Candidate]:
    """Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).

    Built once here and threaded down; helpers never default it, so a missing
    argument is a TypeError rather than a silent unscaled run.
    """
    gates = DoorGates.at(scale_factor)
    if collector:
        collector.init_primitives(paths)
    swings = _collect_door_swings(paths, collector, gates=gates)
    leaves = _collect_door_leaves(paths, collector)
    candidates = _pair_door_assemblies(swings, leaves, text_spans, paths, collector)
    return _merge_double_door_assemblies(candidates)
