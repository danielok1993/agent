from __future__ import annotations
import math
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from models import Entity, Candidate, Region, BBox

DPI = 150
SCALE = DPI / 72

OVERLAY_COLORS: dict[str, tuple[int, int, int, int]] = {
    "door":     (255, 100,   0, 180),
    "window":   (  0, 150, 255, 180),
    "wall":     (180,   0, 255, 180),
    "label":    (  0, 200,   0, 180),
    "schedule": (255, 215,   0, 180),
    "rejected": (128, 128, 128,  80),
    "unknown":  (200, 200, 200, 120),
}

ROOM_COLORS: list[tuple[int, int, int, int]] = [
    (255, 100, 100, 150),  # red
    (100, 255, 100, 150),  # green
    (100, 100, 255, 150),  # blue
    (255, 255, 100, 150),  # yellow
    (255, 100, 255, 150),  # magenta
    (100, 255, 255, 150),  # cyan
    (255, 180, 100, 150),  # orange
    (180, 100, 255, 150),  # purple
    (100, 255, 180, 150),  # teal
    (255, 150, 150, 150),  # light red
    (150, 255, 150, 150),  # light green
    (150, 150, 255, 150),  # light blue
]

BOX_LINE_WIDTH = 2
FONT_SIZE = 11
FILL_ALPHA_FACTOR = 0.30  # fraction of color alpha used for fill
BORDER_ALPHA_FACTOR = 0.70

# Kept regions are drawn bright, discarded ones muted, so a glance at the
# overlay shows what detection actually saw.
REGION_OUTLINE_COLORS: dict[str, tuple[int, int, int, int]] = {
    "floor_plan":     (255,   0,   0, 220),
    "schedule_table": (255, 165,   0, 200),
    "unclassified":   (120, 120, 120, 160),
    "other":          ( 90, 130, 160, 160),
}
REGION_LINE_WIDTH = 3


def render_page_png(doc: fitz.Document, page_index: int, out_path: str) -> None:
    page = doc[page_index]
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_path)


def render_page_svg(doc: fitz.Document, page_index: int, out_path: str) -> None:
    """MuPDF's own vector redraw of the page, in render.png's coordinate space.

    Same matrix as render_page_png, so the SVG's user units ARE 150-DPI pixels
    and an entity bbox overlays it unchanged; /Rotate is baked in by the SVG
    device exactly as get_pixmap bakes it into the raster. Glyphs come out as
    outlines (text_as_path default) so the file does not depend on the reader
    having the sheet's fonts. This is a redraw of the PDF, not of our extracted
    primitives — it shows what the page looks like, never what detection saw.
    """
    page = doc[page_index]
    svg = page.get_svg_image(matrix=fitz.Matrix(SCALE, SCALE))
    Path(out_path).write_text(svg, encoding="utf-8")


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except Exception:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def _draw_dashed_rect(draw: ImageDraw.ImageDraw, bbox: BBox, color: tuple, width: int, dash: int = 6) -> None:
    x0, y0, x1, y1 = [int(v) for v in bbox]
    segments = [
        ((x0, y0), (x1, y0)),
        ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)),
        ((x0, y1), (x0, y0)),
    ]
    for (sx, sy), (ex, ey) in segments:
        length = math.hypot(ex - sx, ey - sy)
        if length < 1:
            continue
        dx, dy = (ex - sx) / length, (ey - sy) / length
        pos = 0
        drawing = True
        while pos < length:
            end = min(pos + dash, length)
            if drawing:
                draw.line(
                    [(int(sx + dx * pos), int(sy + dy * pos)), (int(sx + dx * end), int(sy + dy * end))],
                    fill=color, width=width,
                )
            pos = end
            drawing = not drawing


def _draw_entity_box(
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    color_rgba: tuple[int, int, int, int],
    label: str,
    dashed: bool = False,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont = None,
) -> None:
    x0, y0, x1, y1 = bbox
    if x0 == x1 == y0 == y1 == 0:
        return  # skip zero-area bboxes (e.g. schedule with no bbox)

    r, g, b, a = color_rgba

    fill_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_layer)
    fill_alpha = int(a * FILL_ALPHA_FACTOR)
    fill_draw.rectangle([x0, y0, x1, y1], fill=(r, g, b, fill_alpha))
    overlay.alpha_composite(fill_layer)

    border_color = (r, g, b, int(a * BORDER_ALPHA_FACTOR))
    if dashed:
        _draw_dashed_rect(draw, bbox, border_color, BOX_LINE_WIDTH)
    else:
        draw.rectangle([x0, y0, x1, y1], outline=border_color, width=BOX_LINE_WIDTH)

    if label and font:
        text_x = x0
        text_y = max(0, y0 - FONT_SIZE - 2)
        draw.text((text_x + 1, text_y + 1), label, fill=(0, 0, 0, 200), font=font)
        draw.text((text_x, text_y), label, fill=(r, g, b, 230), font=font)


def _draw_entity_polygon(
    overlay: Image.Image,
    draw: ImageDraw.ImageDraw,
    points: list[tuple[float, float]],
    color_rgba: tuple[int, int, int, int],
    label: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont = None,
) -> None:
    """Room entities carry their closed polygon; draw its true shape instead
    of the bounding rectangle."""
    r, g, b, a = color_rgba
    pts = [(float(x), float(y)) for x, y in points]

    fill_layer = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_layer)
    fill_draw.polygon(pts, fill=(r, g, b, int(a * FILL_ALPHA_FACTOR)))
    overlay.alpha_composite(fill_layer)

    border_color = (r, g, b, int(a * BORDER_ALPHA_FACTOR))
    draw.line(pts + [pts[0]], fill=border_color, width=BOX_LINE_WIDTH)

    if label and font:
        x0 = min(p[0] for p in pts)
        y0 = min(p[1] for p in pts)
        text_y = max(0, y0 - FONT_SIZE - 2)
        draw.text((x0 + 1, text_y + 1), label, fill=(0, 0, 0, 200), font=font)
        draw.text((x0, text_y), label, fill=(r, g, b, 230), font=font)


def _draw_legend(draw: ImageDraw.ImageDraw, used_types: set[str], img_height: int, font) -> None:
    x = 8
    y = img_height - (len(used_types) * (FONT_SIZE + 4)) - 8
    for etype in sorted(used_types):
        if etype == "room":
            draw.text((x + 18, y), "room (multi-colored)", fill=(0, 0, 0, 230), font=font)
            color_x = x
            for i, color in enumerate(ROOM_COLORS[:3]):
                r, g, b, a = color
                draw.rectangle([color_x, y, color_x + 8, y + 12], fill=(r, g, b, 200), outline=(0, 0, 0, 180), width=1)
                color_x += 10
        else:
            color = OVERLAY_COLORS.get(etype, (200, 200, 200, 180))
            r, g, b, a = color
            draw.rectangle([x, y, x + 14, y + 12], fill=(r, g, b, 200), outline=(0, 0, 0, 180), width=1)
            draw.text((x + 18, y), etype, fill=(0, 0, 0, 230), font=font)
        y += FONT_SIZE + 4


def _draw_regions(draw: ImageDraw.ImageDraw, regions: list[Region], font) -> None:
    for region in regions:
        color = REGION_OUTLINE_COLORS.get(
            region.region_type, REGION_OUTLINE_COLORS["other"])
        x0, y0, x1, y1 = [int(v) for v in region.bbox]
        _draw_dashed_rect(draw, (x0, y0, x1, y1), color, REGION_LINE_WIDTH, dash=14)
        if font:
            caption = f"{region.region_id}: {region.region_type}"
            if region.title:
                caption += f" — {region.title[:32]}"
            draw.text((x0 + 5, y0 + 3), caption, fill=(0, 0, 0, 200), font=font)
            draw.text((x0 + 4, y0 + 2), caption, fill=color, font=font)


def draw_overlay(
    render_png_path: str,
    entities: list[Entity],
    rejected: list[dict],
    out_path: str,
    regions: list[Region] | None = None,
) -> None:
    base = Image.open(render_png_path).convert("RGBA")
    overlay = base.copy()
    draw = ImageDraw.Draw(overlay)
    font = _load_font(FONT_SIZE)

    if regions:
        _draw_regions(draw, regions, font)

    used_types: set[str] = set()
    room_index = 0

    for entity in entities:
        etype = entity.entity_type
        if etype == "room":
            color = ROOM_COLORS[room_index % len(ROOM_COLORS)]
            room_index += 1
        else:
            color = OVERLAY_COLORS.get(etype, OVERLAY_COLORS["unknown"])
        used_types.add(etype)
        conf_str = f"{entity.confidence:.2f}"
        label_str = f"{entity.entity_id} {conf_str}"
        if entity.label:
            label_str = f"{entity.label} ({conf_str})"
        polygon = entity.attributes.get("polygon")
        if polygon and len(polygon) >= 3:
            _draw_entity_polygon(overlay, draw, polygon, color, label_str, font=font)
        else:
            _draw_entity_box(overlay, draw, entity.bbox, color, label_str, dashed=False, font=font)

    for rej in rejected:
        color = OVERLAY_COLORS["rejected"]
        used_types.add("rejected")
        cid = rej.get("candidate_id", "?")
        bbox = rej.get("bbox", (0, 0, 0, 0))
        if isinstance(bbox, list):
            bbox = tuple(bbox)
        _draw_entity_box(overlay, draw, bbox, color, cid, dashed=True, font=font)

    if used_types:
        _draw_legend(draw, used_types, overlay.size[1], font)

    final = overlay.convert("RGB")
    final.save(out_path)
