from __future__ import annotations
import math
from typing import Optional
import fitz  # PyMuPDF
from models import BBox, PathPrimitive, TextSpan, ImageRef, PageData

SCALE = 150 / 72  # PDF points → pixels at 150 DPI

# Page classification thresholds
PAGE_VECTOR_RICH_PATH_MIN = 50
PAGE_RASTER_HEAVY_PATH_MAX = 10
PAGE_LARGE_IMAGE_FRAC = 0.20   # single image > 20% of page area → "large"
PAGE_RASTER_COVERAGE_MIN = 0.20


def normalize_bbox(bbox: tuple, scale: float = SCALE) -> BBox:
    x0, y0, x1, y1 = bbox
    return (x0 * scale, y0 * scale, x1 * scale, y1 * scale)


def normalize_point(pt: tuple, scale: float = SCALE) -> tuple[float, float]:
    return (pt[0] * scale, pt[1] * scale)


def _color_tuple(c) -> Optional[tuple[float, float, float]]:
    if c is None:
        return None
    if isinstance(c, (int, float)):
        v = float(c)
        return (v, v, v)
    if len(c) == 3:
        return (float(c[0]), float(c[1]), float(c[2]))
    if len(c) == 4:
        return (float(c[0]), float(c[1]), float(c[2]))
    return None


def extract_paths(page: fitz.Page, scale: float = SCALE) -> list[PathPrimitive]:
    paths = []
    drawings = page.get_drawings()
    for i, d in enumerate(drawings):
        items = d.get("items", [])
        if not items:
            continue

        all_points: list[tuple[float, float]] = []
        types_seen: set[str] = set()

        for item in items:
            kind = item[0]
            types_seen.add(kind)
            if kind == "l":
                all_points.append(normalize_point(item[1], scale))
                all_points.append(normalize_point(item[2], scale))
            elif kind == "c":
                for pt in item[1:]:
                    all_points.append(normalize_point(pt, scale))
            elif kind == "re":
                r = item[1]
                all_points.append(normalize_point((r.x0, r.y0), scale))
                all_points.append(normalize_point((r.x1, r.y1), scale))
            elif kind == "qu":
                for pt in item[1]:
                    all_points.append(normalize_point(pt, scale))

        if not all_points:
            continue

        if len(types_seen) == 1:
            item_type = next(iter(types_seen))
        else:
            item_type = "mixed"

        raw_rect = d.get("rect")
        if raw_rect:
            bbox = normalize_bbox(raw_rect, scale)
        else:
            xs = [p[0] for p in all_points]
            ys = [p[1] for p in all_points]
            bbox = (min(xs), min(ys), max(xs), max(ys))

        dashes = d.get("dashes", "")
        if dashes is None:
            dashes = ""

        layer = d.get("layer")

        paths.append(PathPrimitive(
            path_index=i,
            item_type=item_type,
            bbox=bbox,
            color=_color_tuple(d.get("color")),
            fill=_color_tuple(d.get("fill")),
            stroke_width=float(d.get("width", 0) or 0) * scale,
            dashes=str(dashes),
            layer=layer,
            points=all_points,
        ))
    return paths


def extract_text(page: fitz.Page, scale: float = SCALE) -> list[TextSpan]:
    spans = []
    raw = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        block_no = block.get("number", 0)
        for line_no, line in enumerate(block.get("lines", [])):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox = normalize_bbox(span["bbox"], scale)
                spans.append(TextSpan(
                    text=text,
                    bbox=bbox,
                    font=span.get("font", ""),
                    size=float(span.get("size", 0)),
                    color=span.get("color", 0),
                    block_no=block_no,
                    line_no=line_no,
                ))
    return spans


def extract_images(page: fitz.Page, doc: fitz.Document, scale: float = SCALE) -> list[ImageRef]:
    page_area = page.rect.width * page.rect.height
    images = []
    for img in page.get_images(full=True):
        xref = img[0]
        try:
            bbox_raw = page.get_image_bbox(img)
            if bbox_raw is None:
                continue
        except Exception:
            continue

        bbox = normalize_bbox(bbox_raw, scale)
        raw_w = bbox_raw.width
        raw_h = bbox_raw.height
        raw_area = raw_w * raw_h
        pixel_area = raw_area / page_area if page_area > 0 else 0.0

        info = doc.extract_image(xref)
        colorspace = info.get("colorspace", 0) if info else 0
        cs_name = {1: "Gray", 3: "RGB", 4: "CMYK"}.get(colorspace, str(colorspace))

        images.append(ImageRef(
            xref=xref,
            bbox=bbox,
            width=info.get("width", 0) if info else 0,
            height=info.get("height", 0) if info else 0,
            colorspace=cs_name,
            pixel_area=pixel_area,
        ))
    return images


def get_ocg_names(doc: fitz.Document) -> list[str]:
    try:
        ocgs = doc.get_ocgs()
        if not ocgs:
            return []
        return [v.get("name", "") for v in ocgs.values() if v.get("name")]
    except Exception:
        return []


def classify_page(
    paths: list[PathPrimitive],
    images: list[ImageRef],
    width_px: float,
    height_px: float,
) -> str:
    n_paths = len(paths)
    large_images = [img for img in images if img.pixel_area >= PAGE_LARGE_IMAGE_FRAC]
    total_img_coverage = sum(img.pixel_area for img in large_images)

    has_vectors = n_paths >= PAGE_VECTOR_RICH_PATH_MIN
    has_raster = bool(large_images) and total_img_coverage >= PAGE_RASTER_COVERAGE_MIN
    is_sparse = n_paths <= PAGE_RASTER_HEAVY_PATH_MAX

    if has_vectors and has_raster:
        return "mixed"
    if has_vectors:
        return "vector-rich"
    if is_sparse and has_raster:
        return "raster-heavy"
    return "unknown"


def extract_page(doc: fitz.Document, page_index: int) -> PageData:
    page = doc[page_index]
    scale = SCALE
    width_px = page.rect.width * scale
    height_px = page.rect.height * scale

    paths = extract_paths(page, scale)
    text_spans = extract_text(page, scale)
    images = extract_images(page, doc, scale)
    ocg_names = get_ocg_names(doc)
    page_type = classify_page(paths, images, width_px, height_px)

    return PageData(
        page_number=page_index + 1,
        width_px=width_px,
        height_px=height_px,
        paths=paths,
        text_spans=text_spans,
        images=images,
        ocg_names=ocg_names,
        page_type=page_type,
    )


def extract_document(pdf_path: str, page_indices: list[int]) -> list[PageData]:
    doc = fitz.open(pdf_path)
    results = []
    for idx in page_indices:
        if 0 <= idx < doc.page_count:
            results.append(extract_page(doc, idx))
    doc.close()
    return results
