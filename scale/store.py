"""Tier 4 persistence — where a scale the user typed is kept.

Two back-ends, mirroring the split this repo already uses for verdicts versus
caches:

  * A corpus sheet writes into tests/ground_truth/<slug>.json, which is
    committed. That is the only place a scale survives a fresh clone, and an
    unattended regress sweep needs it to.
  * Anything else writes a gitignored .scale_cache/ sidecar beside the PDF,
    exactly as gemini/region_cache.py does for classifications.

Values are stored as the literal string the user typed ("1:100") and parsed
back with the tier-2 reader, so there is one scale grammar rather than two.

Entries are keyed by GEOMETRY, never by region_id. Region ids are ordinal
(layout/segmenter.py numbers them over a sorted box list), so a change to
segmentation renumbers them — and a stored scale sits at the TOP of the
resolution ladder, so a mis-attached one would override a correct viewport
reading rather than merely being ignored. tests/ground_truth/ already solves
exactly this for detections by matching on type + IoU instead of entity id;
this follows it, reusing regression.matching.iou.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from models import BBox
from regression import corpus
from regression.ground_truth import dump_truth, load_truth
from regression.matching import iou

CACHE_DIR_NAME = ".scale_cache"

# The same threshold tests/ground_truth/ matches detections at.
STORED_MATCH_MIN_IOU = 0.5


@dataclass
class StoredScale:
    bbox: BBox        # the region this scale was entered for, 150-DPI px
    scale: str        # the literal string the user typed, e.g. "1:100"


def _cache_file(pdf_path: str, page_number: int) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}.json"


def _from_dicts(raw) -> list[StoredScale]:
    out: list[StoredScale] = []
    for item in raw or []:
        bbox = item.get("bbox")
        scale = item.get("scale")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or not scale:
            continue
        out.append(StoredScale(tuple(float(v) for v in bbox), str(scale)))
    return out


def _to_dicts(entries: list[StoredScale]) -> list[dict]:
    return [{"bbox": [float(v) for v in e.bbox], "scale": e.scale}
            for e in entries]


def match_stored(
    region_bbox: BBox, stored: list[StoredScale]
) -> Optional[StoredScale]:
    """The stored entry for this region, matched geometrically. Best overlap
    wins; anything under STORED_MATCH_MIN_IOU is a different drawing."""
    best: Optional[StoredScale] = None
    best_iou = STORED_MATCH_MIN_IOU
    for entry in stored:
        overlap = iou(region_bbox, entry.bbox)
        if overlap >= best_iou:
            best, best_iou = entry, overlap
    return best


def load_stored(pdf_path: str, page_number: int) -> list[StoredScale]:
    """Stored scales for one page.

    A missing or unreadable store reads as empty — an absent scale is a prompt,
    never an error.
    """
    slug = corpus.slug_for_path(pdf_path)
    if slug is not None:
        try:
            return _from_dicts(load_truth(slug).scales.get(page_number, []))
        except Exception:
            return []

    target = _cache_file(pdf_path, page_number)
    if not target.exists():
        return []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return _from_dicts(payload.get("scales"))
    except Exception:
        return []


def _merge(existing: list[StoredScale],
           incoming: list[StoredScale]) -> list[StoredScale]:
    """Add entries, replacing any that describe the same region.

    Overlap-based rather than equality-based: the same plan re-segmented
    shifts its box by a pixel or two, and appending would leave two entries
    competing for one drawing.
    """
    merged = list(existing)
    for entry in incoming:
        previous = match_stored(entry.bbox, merged)
        if previous is not None:
            merged[merged.index(previous)] = entry
        else:
            merged.append(entry)
    return merged


def save_stored(
    pdf_path: str, page_number: int, entries: list[StoredScale]
) -> None:
    """Merge entries into the store for one page. Never touches other pages."""
    if not entries:
        return

    merged = _merge(load_stored(pdf_path, page_number), entries)

    slug = corpus.slug_for_path(pdf_path)
    if slug is not None:
        truth = load_truth(slug)
        truth.scales[page_number] = _to_dicts(merged)
        dump_truth(truth)
        return

    target = _cache_file(pdf_path, page_number)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"page_number": page_number, "scales": _to_dicts(merged)},
                   indent=2),
        encoding="utf-8",
    )
