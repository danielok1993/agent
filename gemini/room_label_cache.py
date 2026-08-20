"""On-disk cache of room labels, keyed by page content AND the room polygons
the labels were made against, AND the prompt version.

--no-gemini is the normal way this tool is run, and tools/regress.py sweeps 20
sheets. Without a cache, labels would either cost 20 calls a sweep or never be
exercised offline. With it, a page costs one real API call ever.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from gemini.region_cache import page_content_hash
from gemini.room_labeler import PROMPT_VERSION
from models import Entity, PageData

CACHE_DIR_NAME = ".room_labels_cache"


def room_geometry_hash(rooms: list[Entity]) -> str:
    """Stable digest of the room outlines a labelling was made against.

    A cached label belongs to the polygon it was read out of. Re-detecting
    rooms moves those outlines, and a name read from the old one may now sit
    in a different room — so a detection change must be a cache MISS.
    """
    h = hashlib.sha256()
    h.update(f"n={len(rooms)}|".encode())
    for r in rooms:
        h.update(f"{r.entity_id}:".encode())
        for x, y in (r.attributes or {}).get("polygon", []):
            h.update(f"{float(x):.1f},{float(y):.1f};".encode())
        h.update(b"|")
    return h.hexdigest()[:16]


def cache_key(page_data: PageData, rooms: list[Entity]) -> str:
    return (f"{page_content_hash(page_data)}-{room_geometry_hash(rooms)}"
            f"-{PROMPT_VERSION}")


def cache_file(pdf_path: str, page_number: int, key: str) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}_{key}.json"


def load_labels(
    pdf_path: str, page_number: int, key: str
) -> Optional[dict[str, Optional[str]]]:
    target = cache_file(pdf_path, page_number, key)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        labels = payload["labels"]
        if not isinstance(labels, dict):
            return None
        return labels
    except Exception:
        return None


def save_labels(
    pdf_path: str, page_number: int, key: str, rooms: list[Entity]
) -> None:
    target = cache_file(pdf_path, page_number, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({
            "page_number": page_number,
            "cache_key": key,
            "labels": {r.entity_id: r.label for r in rooms},
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
