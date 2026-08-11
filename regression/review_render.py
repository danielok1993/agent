"""The images a human looks at while giving verdicts.

One PNG per page per entity type, carrying only that type's unreviewed
detections. Per-category rather than one combined image because the review
loop itself is per-category: the doors pass should not be cluttered with
windows.

Each detection is stamped with a short id (door_0007 -> d7) matching the
terminal list, so a line and a shape can be paired by eye without reading
coordinates.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Private by naming convention, imported deliberately: reimplementing dashed
# boxes, polygon fills and label placement would duplicate the drawing code and
# let review images drift from the overlay.png the user already reads.
from extraction.renderer import (FONT_SIZE, OVERLAY_COLORS, ROOM_COLORS,
                                 _draw_entity_box, _draw_entity_polygon,
                                 _load_font)

SHORT_PREFIX = {"door": "d", "window": "w", "room": "r",
                "label": "l", "schedule": "s"}


def short_id(entity_id: str) -> str:
    """door_0007 -> d7. Unparseable ids are returned unchanged."""
    kind, _, ordinal = entity_id.rpartition("_")
    if not kind or not ordinal.isdigit():
        return entity_id
    prefix = SHORT_PREFIX.get(kind, kind[:1])
    return f"{prefix}{int(ordinal)}"


def write_review_overlays(page_dir: Path, unreviewed: list[dict]) -> list[Path]:
    """Draw one review_<type>.png per entity type present in `unreviewed`.

    Returns the paths written, sorted by type. A page with nothing to review
    -- or with no render to draw on, which happens when a sweep was run
    without persisting output -- writes nothing rather than raising: an
    unreviewable page must not take a whole sweep down.
    """
    render = page_dir / "render.png"
    if not unreviewed or not render.exists():
        return []

    by_type: dict[str, list[dict]] = {}
    for entity in unreviewed:
        by_type.setdefault(entity["entity_type"], []).append(entity)

    written: list[Path] = []
    font = _load_font(FONT_SIZE)
    for etype, items in sorted(by_type.items()):
        with Image.open(render) as source:
            image = source.convert("RGBA")
        draw = ImageDraw.Draw(image)
        for index, entity in enumerate(items):
            # Rooms cycle colours so adjacent polygons stay distinguishable;
            # every other type keeps its one overlay colour.
            color = (ROOM_COLORS[index % len(ROOM_COLORS)] if etype == "room"
                     else OVERLAY_COLORS.get(etype, OVERLAY_COLORS["unknown"]))
            label = f"{short_id(entity['entity_id'])} {entity.get('confidence', 0):.2f}"
            polygon = (entity.get("attributes") or {}).get("polygon")
            if polygon and len(polygon) >= 3:
                _draw_entity_polygon(image, draw, polygon, color, label, font=font)
            else:
                _draw_entity_box(image, draw, tuple(entity["bbox"]), color, label,
                                 font=font)
        out = page_dir / f"review_{etype}.png"
        image.convert("RGB").save(out)
        written.append(out)
    return written
