"""Orchestration: record -> download -> extract -> filter -> upload -> record.

Every collaborator is injected so the whole flow is unit-testable without
Firestore, Storage, or a PDF. The default extract_fn is pipeline.run_extract
itself — the function is a transport wrapper, and calling anything else would
put the deployed detector on a different code path from the CLI that
tools/regress.py validates.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from takeoff_fn import artifacts, config, records, sheets, sources
from takeoff_fn.errors import FailedPrecondition
from takeoff_fn.request import TakeoffRequest


@dataclass(frozen=True)
class RunResult:
    sheets: list[dict]
    artifacts: dict
    run: dict
    document: dict = field(default_factory=dict)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _document(sheet_list: list[dict]) -> dict:
    """The TakeoffDocument rivet-mind persists.

    `overrides` is seeded empty rather than omitted: their review UI reads it
    unconditionally, and an absent key is worse for a consumer than an empty
    one.
    """
    return {
        "schemaVersion": 1,
        "sheets": sheet_list,
        "overrides": {"rooms": {}, "openings": {}, "addedOpenings": [],
                      "addedRooms": [], "heights": {}},
    }


def sheet_is_scaled(sheet: dict) -> bool:
    """Whether anything on this sheet resolved a drawing scale.

    Two ways to qualify, because they are genuinely different sheets: a page
    scale (one scale stated for the whole sheet), or a room measured against
    its own region's scale (a multi-scale sheet has no page scale and is
    perfectly measurable).

    Total over a payload read off disk — a malformed block answers False
    rather than raising, so one bad page cannot fail a run that measured.
    """
    scale = sheet.get("scale")
    if isinstance(scale, dict):
        page = scale.get("page")
        if isinstance(page, dict) and page.get("denominator") is not None:
            return True
    return any(isinstance(room, dict) and room.get("mm_per_px") is not None
               for room in sheet.get("rooms") or [])


def _measure_source(source, out_parent: str, prefix: str,
                    request: TakeoffRequest, bucket, extract_fn, page_count_fn,
                    all_sheets: list[dict], all_artifacts: dict[str, dict],
                    skipped: list[dict], run_files: dict[str, dict]) -> None:
    """Measure one source PDF and upload its artefacts.

    Extracted so run_measurement can guard the whole per-source body in one
    place: anything raised in here is that FILE's failure, not the run's.
    Results accumulate into the caller's collections, so a later file failing
    cannot undo an earlier one's sheets.
    """
    file_id = f"file_{source.index:02d}"
    Path(out_parent).mkdir(parents=True, exist_ok=True)

    out_dir = extract_fn(
        pdf_path=source.local_path,
        page_indices=list(range(page_count_fn(source.local_path))),
        out_parent=out_parent,
        skip_gemini=False,
        disable_rooms=False,
        disable_windows=False,
        debug=request.debug,
        refresh_regions=False,
        write_svg=True,
        # Without this, an unresolvable scale blocks on input() inside a
        # Cloud Function until the timeout kills the instance.
        allow_scale_prompt=False,
        fallback_denominator=request.scale_denominator,
        ceiling_height=None,
        door_height=None,
        window_height=None,
    )

    def _svg_path_for(page_number: int) -> str:
        return artifacts.object_path(prefix, source.index, page_number,
                                     config.SVG_ARTIFACT)

    found, page_skips = sheets.collect_sheets(
        out_dir, source.index, source.file_name, _svg_path_for)
    skipped.extend({**s, "source_file_id": file_id} for s in page_skips)

    for sheet in found:
        # collect_sheets already knows where it read the page from, and which
        # page number it built plan_svg_url with; popping keeps the internal
        # key out of the response.
        page_number, page_dir = sheet.pop(sheets.PAGE_SOURCE_KEY)
        all_artifacts[sheet["sheet_id"]] = artifacts.upload_page(
            bucket, page_dir, prefix, source.index, page_number, request.debug)

    # Before the run-file upload, so a failure there cannot leave an artifact
    # entry keyed by a sheet_id that never reaches the response.
    all_sheets.extend(found)
    run_files[file_id] = artifacts.upload_run_files(
        bucket, out_dir, prefix, source.index)


def run_measurement(request: TakeoffRequest, *, db, bucket,
                    extract_fn=None, page_count_fn=None, now_fn=None,
                    workdir: Optional[str] = None) -> RunResult:
    if extract_fn is None:
        from pipeline import run_extract as extract_fn  # noqa: N806
    if page_count_fn is None:
        page_count_fn = sources.page_count
    if now_fn is None:
        now_fn = _now_ms

    started_at = now_fn()
    record = records.load_record(db, request.takeoff_id, request.customer_id,
                                 started_at)
    records.mark_processing(db, request.takeoff_id, started_at)

    # Everything from here on is guarded: once the record says "processing",
    # any failure must write mark_failed before it propagates, or the record
    # sits misreporting its state until the reaper sweeps it.
    owns_workdir = workdir is None
    work_root = None

    all_sheets: list[dict] = []
    all_artifacts: dict[str, dict] = {}
    run_files: dict[str, dict] = {}
    skipped: list[dict] = []
    warnings: list[dict] = []

    try:
        work_root = workdir or tempfile.mkdtemp(prefix="takeoff-")
        prefix = artifacts.run_prefix(request.customer_id, request.takeoff_id)

        downloads, download_warnings = sources.download_sources(
            bucket, record.source_files, str(Path(work_root) / "sources"),
            request.customer_id)
        warnings.extend(download_warnings)

        if not downloads:
            raise FailedPrecondition(
                "No source drawing could be read for this takeoff")

        for source in downloads:
            out_parent = str(Path(work_root) / f"out_{source.index:02d}")
            try:
                _measure_source(source, out_parent, prefix, request, bucket,
                                extract_fn, page_count_fn,
                                all_sheets, all_artifacts, skipped, run_files)
            except Exception as exc:  # noqa: BLE001 - per-source, like a download
                # A truncated or password-protected PDF must not discard the
                # plans that already measured. Same shape and code as the
                # download failure sources.py reports.
                warnings.append({
                    "warning_code": "TAKEOFF_SOURCE_UNREADABLE",
                    "severity": "error",
                    "message": f"{source.file_name}: {exc}",
                    "page_number": None})
                traceback.print_exc()
            finally:
                # /tmp is tmpfs charged against the memory budget, so peak
                # usage must be the max over source files, not the sum.
                Path(source.local_path).unlink(missing_ok=True)
                shutil.rmtree(out_parent, ignore_errors=True)

        finished_at = now_fn()
        run_block = {
            "startedAt": started_at,
            "finishedAt": finished_at,
            "durationMs": finished_at - started_at,
            "sourceFiles": len(record.source_files),
            "sourceFilesRead": len(downloads),
            "pagesMeasured": len(all_sheets),
            "pagesSkipped": skipped,
            "warnings": warnings,
            "debug": request.debug,
        }
        # Uploaded BEFORE the no-sheet check: page artefacts may already be in
        # Storage, and a failed run with no manifest beside them cannot be
        # diagnosed.
        run_block["manifest"] = artifacts.upload_json(
            bucket, prefix, "run.json", run_block)

        if not all_sheets:
            raise FailedPrecondition(
                "No floor plan was found in any source drawing")

        document = _document(all_sheets)
        document_json = json.dumps(document, default=str)

        # Two terminal states, not one. A run where NOTHING resolved a scale
        # has measured only geometry — detection ran at identity factor, so
        # even the rooms it found are suspect — and rivet-mind's parse
        # boundary drops every one of those sheets. Reporting that as
        # awaiting_review promises a review that cannot happen; the client
        # then fails the record itself, blaming the drawing.
        #
        # A PARTIALLY unscaled run stays awaiting_review: the scaled pages are
        # reviewable, and blocking them on a question about the others would
        # cost more than the unscaled pages are worth. run.json records what
        # was skipped.
        #
        # A run that was already GIVEN a scale and still resolved nothing is
        # a third case, and it must not park either. The fallback tier only
        # fires inside resolve_page_scales' per-region loop, and only
        # promotes to page_scale when it bound at least one region — a page
        # with no floor_plan region at all (a scanned sheet, a failed Gemini
        # classify or parse) offers the fallback nothing to bind, so a
        # supplied denominator is silently inert on it. Parking again would
        # ask the same question forever: the re-run resolves nothing for the
        # same reason it did the first time. Never park twice on a question
        # the user has already answered — fail honestly instead, exactly as
        # this takeoff would have failed before this feature existed, via
        # the client's existing effect. The alternative, widening the
        # promotion guard to publish page_scale from zero bound regions,
        # would manufacture a "reviewable" sheet with no rooms on it, which
        # is worse than an honest failure.
        if (any(sheet_is_scaled(sheet) for sheet in all_sheets)
                or request.scale_denominator is not None):
            records.mark_awaiting_review(
                db, request.takeoff_id, document_json, finished_at)
        else:
            records.mark_awaiting_scale(
                db, request.takeoff_id, document_json, finished_at)

        return RunResult(sheets=all_sheets,
                         artifacts={"prefix": prefix,
                                    "bySheet": all_artifacts,
                                    # A sibling key, not an entry in bySheet:
                                    # bySheet's contract is {[sheetId]: {...}}
                                    # and a consumer iterating it must not
                                    # meet a non-sheet.
                                    "run": run_files},
                         run=run_block, document=document)

    except Exception as exc:  # noqa: BLE001 - the record must never lie
        records.mark_failed(db, request.takeoff_id, str(exc) or repr(exc),
                            now_fn())
        traceback.print_exc()
        raise
    finally:
        if work_root:
            if owns_workdir:
                shutil.rmtree(work_root, ignore_errors=True)
            else:
                for child in Path(work_root).iterdir():
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
