from __future__ import annotations
import pdfplumber
from models import PlumberCounts, PyMuPDFCounts, PageData, BBox
from extractor import SCALE

LARGE_DELTA_THRESHOLD = 0.50  # warn if counts differ by more than 50%


def _normalize_bbox_plumber(obj: dict, scale: float = SCALE) -> BBox:
    x0 = float(obj.get("x0", 0))
    y0 = float(obj.get("top", obj.get("y0", 0)))
    x1 = float(obj.get("x1", x0))
    y1 = float(obj.get("bottom", obj.get("y1", y0)))
    return (x0 * scale, y0 * scale, x1 * scale, y1 * scale)


def extract_plumber_page(pdf_path: str, page_index: int, scale: float = SCALE) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        if page_index >= len(pdf.pages):
            return {"chars": [], "lines": [], "rects": [], "curves": [], "images": [], "tables": []}
        page = pdf.pages[page_index]

        chars = [
            {
                "text": c.get("text", ""),
                "bbox": _normalize_bbox_plumber(c, scale),
                "font": c.get("fontname", ""),
                "size": c.get("size", 0),
            }
            for c in (page.chars or [])
        ]

        lines = [
            {"bbox": _normalize_bbox_plumber(l, scale), "width": float(l.get("linewidth", 0)) * scale}
            for l in (page.lines or [])
        ]

        rects = [
            {"bbox": _normalize_bbox_plumber(r, scale), "width": float(r.get("linewidth", 0)) * scale}
            for r in (page.rects or [])
        ]

        curves = [
            {"bbox": _normalize_bbox_plumber(c, scale)}
            for c in (page.curves or [])
        ]

        images = [
            {"bbox": _normalize_bbox_plumber(img, scale)}
            for img in (page.images or [])
        ]

        try:
            raw_tables = page.extract_tables()
            tables = raw_tables if raw_tables else []
        except Exception:
            tables = []

        return {
            "chars": chars,
            "lines": lines,
            "rects": rects,
            "curves": curves,
            "images": images,
            "tables": tables,
        }


def extract_plumber_document(pdf_path: str, page_indices: list[int]) -> list[dict]:
    results = []
    for idx in page_indices:
        results.append(extract_plumber_page(pdf_path, idx))
    return results


def build_plumber_counts(plumber_page: dict) -> PlumberCounts:
    return PlumberCounts(
        chars=len(plumber_page.get("chars", [])),
        lines=len(plumber_page.get("lines", [])),
        rects=len(plumber_page.get("rects", [])),
        curves=len(plumber_page.get("curves", [])),
        images=len(plumber_page.get("images", [])),
        tables=len(plumber_page.get("tables", [])),
    )


def build_pymupdf_counts(page_data: PageData) -> PyMuPDFCounts:
    return PyMuPDFCounts(
        paths=len(page_data.paths),
        text_spans=len(page_data.text_spans),
        images=len(page_data.images),
        ocgs=len(page_data.ocg_names),
    )


def _delta_pct(a: int, b: int) -> Optional[float]:
    if a == 0 and b == 0:
        return 0.0
    if a == 0 or b == 0:
        return None
    return abs(a - b) / max(a, b)


def compare_counts(
    pymupdf_counts: PyMuPDFCounts,
    plumber_counts: PlumberCounts,
) -> dict:
    plumber_geometry = plumber_counts["lines"] + plumber_counts["rects"] + plumber_counts["curves"]
    pymupdf_paths = pymupdf_counts["paths"]

    geo_delta = _delta_pct(pymupdf_paths, plumber_geometry)
    text_delta = _delta_pct(pymupdf_counts["text_spans"], plumber_counts["chars"])

    warnings = []
    if geo_delta is not None and geo_delta > LARGE_DELTA_THRESHOLD:
        warnings.append({
            "warning_code": "PLUMBER_LARGE_DELTA",
            "severity": "warning",
            "message": (
                f"PyMuPDF paths ({pymupdf_paths}) vs pdfplumber geometry "
                f"({plumber_geometry}) differ by {geo_delta:.0%}"
            ),
        })

    return {
        "pymupdf": dict(pymupdf_counts),
        "pdfplumber": dict(plumber_counts),
        "deltas": {
            "geometry": {
                "pymupdf_paths": pymupdf_paths,
                "plumber_lines_rects_curves": plumber_geometry,
                "delta_pct": round(geo_delta * 100, 1) if geo_delta is not None else None,
            },
            "text": {
                "pymupdf_spans": pymupdf_counts["text_spans"],
                "plumber_chars": plumber_counts["chars"],
                "note": "spans vs chars — different granularity",
                "delta_pct": round(text_delta * 100, 1) if text_delta is not None else None,
            },
        },
        "comparison_warnings": warnings,
    }


def extract_tables(pdf_path: str, page_index: int) -> list[list[list[str]]]:
    with pdfplumber.open(pdf_path) as pdf:
        if page_index >= len(pdf.pages):
            return []
        try:
            tables = pdf.pages[page_index].extract_tables()
            return tables if tables else []
        except Exception:
            return []


# needed for type hint in compare_counts
from typing import Optional
