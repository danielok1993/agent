from __future__ import annotations
import math
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from models import Entity, Candidate, BBox

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

BOX_LINE_WIDTH = 2
FONT_SIZE = 11
FILL_ALPHA_FACTOR = 0.30  # fraction of color alpha used for fill
BORDER_ALPHA_FACTOR = 0.70


def render_page_png(doc: fitz.Document, page_index: int, out_path: str) -> None:
    page = doc[page_index]
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pix.save(out_path)


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


def _draw_legend(draw: ImageDraw.ImageDraw, used_types: set[str], img_height: int, font) -> None:
    x = 8
    y = img_height - (len(used_types) * (FONT_SIZE + 4)) - 8
    for etype in sorted(used_types):
        color = OVERLAY_COLORS.get(etype, (200, 200, 200, 180))
        r, g, b, a = color
        draw.rectangle([x, y, x + 14, y + 12], fill=(r, g, b, 200), outline=(0, 0, 0, 180), width=1)
        draw.text((x + 18, y), etype, fill=(0, 0, 0, 230), font=font)
        y += FONT_SIZE + 4


def draw_overlay(
    render_png_path: str,
    entities: list[Entity],
    rejected: list[dict],
    out_path: str,
) -> None:
    base = Image.open(render_png_path).convert("RGBA")
    overlay = base.copy()
    draw = ImageDraw.Draw(overlay)
    font = _load_font(FONT_SIZE)

    used_types: set[str] = set()

    for entity in entities:
        etype = entity.entity_type
        color = OVERLAY_COLORS.get(etype, OVERLAY_COLORS["unknown"])
        used_types.add(etype)
        conf_str = f"{entity.confidence:.2f}"
        label_str = f"{entity.entity_id} {conf_str}"
        if entity.label:
            label_str = f"{entity.label} ({conf_str})"
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
