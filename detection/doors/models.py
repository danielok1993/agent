from __future__ import annotations
from dataclasses import dataclass
from models import BBox


@dataclass
class _DoorSwing:
    source: str
    bbox: BBox
    radius: float
    pairing_points: list[tuple[float, float]]
    component_path_indices: list[int]
    layer: str | None
    layer_hint: bool
    evidence: dict
    arc_endpoints: list[tuple[float, float]]   # actual arc start/end points for bridge-line check
    debug_id: str | None = None               # set by DebugTraceCollector when active
    # Set when this swing is one half of a garden-door / double-arc split
    # (see _split_double_arc). Carries the OTHER half's path indices so the
    # bridge-line opening check can cross-exclude the partner's arc — without
    # this, each half flags the other as a sill obstruction across its bridge.
    double_arc_partner_paths: list[int] | None = None


@dataclass
class _DoorLeaf:
    source: str
    bbox: BBox
    length: float
    corners: list[tuple[float, float]]
    component_path_indices: list[int]
    layer: str | None
    layer_hint: bool
    evidence: dict
    debug_id: str | None = None               # set by DebugTraceCollector when active
