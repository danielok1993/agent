from __future__ import annotations
from dataclasses import dataclass, field
from typing import TypedDict, Literal, Optional

BBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in pixel-space (top-left origin)


@dataclass
class PathPrimitive:
    path_index: int
    item_type: Literal["l", "c", "re", "qu", "mixed"]
    bbox: BBox
    color: Optional[tuple[float, float, float]]
    fill: Optional[tuple[float, float, float]]
    stroke_width: float
    dashes: str
    layer: Optional[str]
    points: list[tuple[float, float]]


@dataclass
class TextSpan:
    text: str
    bbox: BBox
    font: str
    size: float
    color: int
    block_no: int
    line_no: int


@dataclass
class ImageRef:
    xref: int
    bbox: BBox
    width: int
    height: int
    colorspace: str
    pixel_area: float  # fraction of page area covered


@dataclass
class PageData:
    page_number: int  # 1-based
    width_px: float
    height_px: float
    paths: list[PathPrimitive] = field(default_factory=list)
    text_spans: list[TextSpan] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    ocg_names: list[str] = field(default_factory=list)
    page_type: Literal["vector-rich", "raster-heavy", "mixed", "unknown"] = "unknown"


@dataclass
class Candidate:
    candidate_id: str  # e.g. "door_0001"
    entity_type: Literal["door", "window", "wall", "label", "schedule"]
    bbox: BBox
    confidence: float
    evidence: dict = field(default_factory=dict)


@dataclass
class Entity:
    entity_id: str
    entity_type: str
    bbox: BBox
    confidence: float
    source: Literal["heuristic", "gemini", "merged"]
    label: Optional[str] = None
    attributes: dict = field(default_factory=dict)


class PlumberCounts(TypedDict):
    chars: int
    lines: int
    rects: int
    curves: int
    images: int
    tables: int


class PyMuPDFCounts(TypedDict):
    paths: int
    text_spans: int
    images: int
    ocgs: int
