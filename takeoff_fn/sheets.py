"""Turning a finished run_extract output tree into wire sheets.

Only pages the region classifier called a floor_plan become sheets: an
elevation or a title-block page has nothing a reviewer can check. The one
exception is a page with no classification at all, where detection ran over
the whole page and the measurement is genuine — see is_unclassified. Skipped
pages are reported rather than dropped silently, so a wrongly-skipped plan is
diagnosable from run.json.

The three fields injected here — sheet_id, source_file_id, label — are ones
rivet-mind's parser currently synthesises. Theirs derives sheet_id from the
page number alone, which collides across source files; ours is unique.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

# Where a sheet was read from — (page_number, page_dir) — carried on the sheet
# dict so the runner never rebuilds either from the payload's own page_number.
# A takeoff.json missing that key was an unhandled KeyError; one disagreeing
# with its directory name found no files to upload while the sheet still
# advertised a plan_svg_url built from the DIRECTORY number. The page number
# here is the same one svg_path_for was given, so the uploaded object path and
# the advertised one cannot drift apart.
# The runner POPS this before the sheet reaches the response — it is internal.
PAGE_SOURCE_KEY = "_page_source"


def page_dirs(out_dir: str) -> list[tuple[int, str]]:
    pages_root = Path(out_dir) / "pages"
    if not pages_root.is_dir():
        return []
    found: list[tuple[int, str]] = []
    for entry in pages_root.iterdir():
        if not entry.is_dir() or not entry.name.startswith("page_"):
            continue
        try:
            found.append((int(entry.name[len("page_"):]), str(entry)))
        except ValueError:
            continue
    return sorted(found)


def _read_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # ValueError covers both json.JSONDecodeError (a ValueError subclass)
        # and UnicodeDecodeError, which is NOT one of json's exceptions — a
        # file of non-UTF-8 bytes must skip its page, never crash the run.
        return None


def _region_types(document: dict) -> list[str]:
    return [r.get("region_type") for r in document.get("regions", [])
            if isinstance(r, dict)]


def has_floor_plan(page_dir: str) -> bool:
    document = _read_json(Path(page_dir) / "regions.json")
    if not isinstance(document, dict):
        return False
    return "floor_plan" in _region_types(document)


def is_unclassified(document: dict) -> bool:
    """True when nothing on the page carries a classification.

    pipeline.resolve_page_regions has three paths that return UNCLASSIFIED
    regions while detection still runs over the WHOLE page and a real
    takeoff.json is still written: a raster page with no vector ink (an empty
    region list), a REGION_CLASSIFY_PARSE_FAILURE, and offline with no cached
    classification. Reading "no floor_plan region" as "no floor plan" there
    would throw away a genuine measurement — and, when it is the only page,
    fail the takeoff with a message blaming the drawing.

    This is NOT the same as a page whose regions ARE classified and none of
    them is a floor plan (an elevation sheet, a title-block-only page): that
    is a real verdict and stays skipped.
    """
    return all(t in (None, "unclassified") for t in _region_types(document))


def sheet_id(file_index: int, page_number: int) -> str:
    return f"sheet_{file_index:02d}_{page_number:02d}"


def collect_sheets(out_dir: str, file_index: int, file_name: str,
                   svg_path_for: Callable[[int], str]
                   ) -> tuple[list[dict], list[dict]]:
    found: list[dict] = []
    skipped: list[dict] = []

    for page_number, page_dir in page_dirs(out_dir):
        regions = _read_json(Path(page_dir) / "regions.json")
        if not isinstance(regions, dict):
            skipped.append({"page_number": page_number,
                            "reason": "no_regions_document"})
            continue

        unclassified = False
        if not has_floor_plan(page_dir):
            if not is_unclassified(regions):
                skipped.append({"page_number": page_number,
                                "reason": "no_floor_plan_region"})
                continue
            if regions.get("skip_detection"):
                # Nothing classified AND detection was skipped: run_heuristics
                # never ran, so takeoff.json holds nothing to review.
                skipped.append({"page_number": page_number,
                                "reason": "regions_unclassified"})
                continue
            unclassified = True

        payload = _read_json(Path(page_dir) / "takeoff.json")
        if not isinstance(payload, dict):
            skipped.append({"page_number": page_number,
                            "reason": "no_takeoff_document"})
            continue

        sheet = dict(payload)
        if unclassified:
            # Appended, never substituted: the page's own warnings are the
            # reviewer's other evidence. Surfaced here because the sheet is
            # measured from the WHOLE page — elevation and title-block ink
            # included — so its rooms deserve a closer look than a classified
            # floor plan's.
            sheet["warnings"] = list(sheet.get("warnings") or []) + [{
                "warning_code": "TAKEOFF_REGIONS_UNCLASSIFIED",
                "severity": "warning",
                "message": (f"Page {page_number}: no region was classified, so "
                            f"the whole page was measured without floor-plan "
                            f"filtering"),
                "page_number": page_number,
            }]
        sheet[PAGE_SOURCE_KEY] = (page_number, page_dir)
        sheet["sheet_id"] = sheet_id(file_index, page_number)
        sheet["source_file_id"] = f"file_{file_index:02d}"
        sheet["source_file_name"] = file_name
        sheet["label"] = f"{file_name} — page {page_number}"
        sheet["plan_svg_url"] = svg_path_for(page_number)
        found.append(sheet)

    return found, skipped
