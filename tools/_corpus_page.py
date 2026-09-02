"""One corpus sheet's detection page data, exactly as tools/regress.py sees it.

Shared by the probes under tools/: extract -> cached regions (offline, no
Gemini) -> scales -> doors -> open-leaf exclusion set, per page. Needs the
sheet under fixtures/sheets/ and its region cache; a page the region
classifier skips is skipped here too.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fitz

from detection.doors.assembly import door_open_leaf_path_indices
from detection.doors.detect import detect_doors
from extraction.extractor import extract_page
from models import PageData
from pipeline import resolve_page_regions
from scale.factor import detection_scale
from scale.resolver import resolve_page_scales
from scale.store import load_stored
from scale.viewport import viewport_scales

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class DetectionPage:
    slug: str
    pdf: str
    page_number: int                 # 1-based, as in every output file
    page_data: PageData              # region-filtered, what the detectors see
    exclude: set[int]                # door open-leaf path indices
    scale_factor: float              # scale.factor.detection_scale(...).factor


def sheet_pdf(slug: str) -> str:
    manifest = json.loads((ROOT / "fixtures" / "MANIFEST.json").read_text())
    entry = next((s for s in manifest["sheets"] if s["slug"] == slug), None)
    if entry is None:
        raise SystemExit(f"{slug}: not in fixtures/MANIFEST.json")
    pdf = ROOT / "fixtures" / "sheets" / entry["file"]
    if not pdf.exists():
        raise SystemExit(f"{slug}: {pdf} is missing (python tools/fetch_fixtures.py)")
    return str(pdf)


def load_detection_pages(slug: str, pages: list[int] | None = None) -> list[DetectionPage]:
    """Every detected page of the sheet (or only `pages`, 1-based)."""
    pdf = sheet_pdf(slug)
    doc = fitz.open(pdf)
    out: list[DetectionPage] = []
    for pno in range(doc.page_count):
        if pages and pno + 1 not in pages:
            continue
        page_data = extract_page(doc, pno)
        rr = resolve_page_regions(
            pdf_path=pdf, page=doc[pno], page_data=page_data, gemini_client=None,
            skip_gemini=True, refresh_regions=False, crop_dir=None,
        )
        if rr.skip_detection:
            continue
        ps = resolve_page_scales(
            page_data=page_data, regions=rr.regions,
            viewports=viewport_scales(doc, doc[pno]),
            stored=load_stored(pdf, pno + 1), fallback=None, pdf_path=pdf,
            crop_fn=None, allow_prompt=False, suspend_display=None,
        )
        det = detection_scale(ps, rr.regions, pno + 1)
        pd = rr.detection_page_data
        doors = detect_doors(pd.paths, pd.text_spans, None, scale_factor=det.factor)
        out.append(DetectionPage(
            slug=slug, pdf=pdf, page_number=pno + 1, page_data=pd,
            exclude=set(door_open_leaf_path_indices(doors, pd.paths)),
            scale_factor=det.factor,
        ))
    return out
