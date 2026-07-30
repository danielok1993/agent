"""On-disk cache of region classifications, keyed by page content.

--no-gemini is the normal way this tool is run. Without a cache that flag would
silently disable region filtering, so offline runs would disagree with online
ones. With it, a page costs one real API call ever.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from models import PageData, Region

CACHE_DIR_NAME = ".regions_cache"


def page_content_hash(page_data: PageData) -> str:
    """Stable digest of a page's vector geometry and text. Changes if the PDF
    is edited, so a stale classification is never reused."""
    h = hashlib.sha256()
    h.update(f"{page_data.width_px:.2f}x{page_data.height_px:.2f}".encode())
    h.update(f"|paths={len(page_data.paths)}|spans={len(page_data.text_spans)}|".encode())
    for p in page_data.paths:
        h.update(f"{p.item_type}:{p.bbox[0]:.2f},{p.bbox[1]:.2f},"
                 f"{p.bbox[2]:.2f},{p.bbox[3]:.2f};".encode())
    for t in page_data.text_spans:
        h.update(f"{t.text}@{t.bbox[0]:.1f},{t.bbox[1]:.1f};".encode())
    return h.hexdigest()[:16]


def cache_file(pdf_path: str, page_number: int, content_hash: str) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}_{content_hash}.json"


def regions_to_dicts(regions: list[Region]) -> list[dict]:
    return [
        {
            "region_id": r.region_id,
            "bbox": list(r.bbox),
            "region_type": r.region_type,
            "title": r.title,
            "confidence": r.confidence,
            "contains_multiple": r.contains_multiple,
            "path_count": r.path_count,
            "source": r.source,
        }
        for r in regions
    ]


def regions_from_dicts(data: list[dict]) -> list[Region]:
    return [
        Region(
            region_id=d["region_id"],
            bbox=tuple(d["bbox"]),
            region_type=d.get("region_type", "unclassified"),
            title=d.get("title"),
            confidence=float(d.get("confidence", 0.0)),
            contains_multiple=bool(d.get("contains_multiple", False)),
            path_count=int(d.get("path_count", 0)),
            source=d.get("source", "whitespace"),
        )
        for d in data
    ]


def load_regions(pdf_path: str, page_number: int, content_hash: str) -> Optional[list[Region]]:
    target = cache_file(pdf_path, page_number, content_hash)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return regions_from_dicts(payload["regions"])
    except Exception:
        return None


def save_regions(
    pdf_path: str, page_number: int, content_hash: str, regions: list[Region]
) -> None:
    target = cache_file(pdf_path, page_number, content_hash)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({
            "page_number": page_number,
            "content_hash": content_hash,
            "regions": regions_to_dicts(regions),
        }, indent=2),
        encoding="utf-8",
    )
