from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import fitz
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box as rich_box
from rich.markup import escape as rich_escape
from models import PageData, Candidate, Entity, Region, TextSpan
from extraction.extractor import extract_page
from extraction.plumber import (
    extract_plumber_page, build_pymupdf_counts, build_plumber_counts, compare_counts
)
from detection import run_heuristics
from debug.trace import DebugTraceCollector
from debug.renderer import generate_debug_viewer
from extraction.renderer import render_page_png, draw_overlay
from layout import (
    assigned_path_fraction, filter_page_data, page_fallback_region,
    qualifying_clip_rects, region_text_spans, segment_page,
)
from gemini import client as gc
from gemini.classifier import classify_regions, render_region_crop
from gemini.region_cache import cache_key, load_regions, save_regions
from scale.resolver import PageScales, resolve_page_scales
from scale.store import load_stored
from scale.units import format_scale
from scale.viewport import viewport_scales

console = Console()


def make_output_dir(parent: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = Path(parent) / ts
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


def make_page_dir(out_dir: str, page_number: int) -> str:
    p = Path(out_dir) / "pages" / f"page_{page_number:02d}"
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def write_json(path: str, data: dict | list) -> None:
    Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _candidate_to_dict(c: Candidate) -> dict:
    return {
        "candidate_id": c.candidate_id,
        "entity_type": c.entity_type,
        "bbox": list(c.bbox),
        "confidence": c.confidence,
        "evidence": c.evidence,
    }


def _entity_to_dict(e: Entity) -> dict:
    return {
        "entity_id": e.entity_id,
        "entity_type": e.entity_type,
        "bbox": list(e.bbox),
        "confidence": e.confidence,
        "source": e.source,
        "label": e.label,
        "attributes": e.attributes,
    }


# No "wall" entry: walls are internal wall-network data now, never candidates.
# No "room" entry: rooms are heuristic-only and bypass the merge thresholds.
OFFLINE_MIN_CONFIDENCE: dict[str, float] = {
    "door":     0.55,
    "window":   0.50,
    "label":    0.65,
    "schedule": 0.50,
}

# Region filtering only pays if the regions actually hold the sheet's ink.
# Segmentation can drop a leaf (anything under SEGMENT_MIN_REGION_SIDE_PX, or a
# page-spanning primitive that never entered the ink map), and filter_page_data
# then deletes its contents outright — losing real drawing, not page furniture.
# Below this share of the page's paths, record the regions but filter nothing.
# Measured over the 16 vector sample sheets in plans/ (assigned-path fraction,
# after the rotation fix): the two problem sheets sit at 0.65 and 0.85 and a
# third at 0.89, every healthy sheet at 0.94-1.00 — the corpus separates
# cleanly, and 0.90 sits in the gap.
REGION_MIN_COVERAGE_FRAC = 0.90


# Door-only candidate-evidence keys carried through to Entity.attributes so
# downstream consumers of final_entities.json see the entrance-door subtype
# without having to cross-reference candidates.json.
_DOOR_EVIDENCE_PASSTHROUGH = ("has_threshold", "door_subtype", "threshold_path_index", "assembly_type", "swing_layout")


def _door_attribute_overlay(candidate: Optional[Candidate]) -> dict:
    """Selected door-evidence keys to merge into Entity.attributes. {} for None / non-doors."""
    if candidate is None or candidate.entity_type != "door":
        return {}
    return {
        k: candidate.evidence[k]
        for k in _DOOR_EVIDENCE_PASSTHROUGH
        if k in candidate.evidence
    }


# Room-evidence keys carried into Entity.attributes; "polygon" is the closed
# room boundary that overlay drawing and downstream consumers rely on.
_ROOM_EVIDENCE_PASSTHROUGH = (
    "polygon", "area_px2", "perimeter_px", "door_openings", "window_openings",
    "wall_segment_count", "wall_contact",
)


def _room_entity(candidate: Candidate) -> Entity:
    return Entity(
        entity_id=candidate.candidate_id,
        entity_type="room",
        bbox=candidate.bbox,
        confidence=candidate.confidence,
        source="heuristic",
        label=None,
        attributes={
            "heuristic_confidence": candidate.confidence,
            **{
                k: candidate.evidence[k]
                for k in _ROOM_EVIDENCE_PASSTHROUGH
                if k in candidate.evidence
            },
        },
    )


def finalize_candidates(candidates: list[Candidate]) -> tuple[list[Entity], list[dict]]:
    """Promote candidates to entities, applying the offline confidence floors.

    Gemini no longer votes on individual candidates, so these floors always
    apply. Rooms bypass them: they are heuristic-only by design and carry their
    polygon into Entity.attributes.
    """
    rooms = [c for c in candidates if c.entity_type == "room"]
    others = [c for c in candidates if c.entity_type != "room"]

    entities: list[Entity] = []
    rejected_list: list[dict] = []
    for c in others:
        threshold = OFFLINE_MIN_CONFIDENCE.get(c.entity_type, 0.50)
        if c.confidence < threshold:
            rejected_list.append({
                "candidate_id": c.candidate_id,
                "entity_type": c.entity_type,
                "bbox": list(c.bbox),
                "reason": f"offline confidence {c.confidence:.3f} < threshold {threshold}",
                "source": "offline_filter",
            })
            continue
        entities.append(Entity(
            entity_id=c.candidate_id,
            entity_type=c.entity_type,
            bbox=c.bbox,
            confidence=c.confidence,
            source="heuristic",
            label=c.evidence.get("nearby_label") or c.evidence.get("text"),
            attributes={"heuristic_confidence": c.confidence, **_door_attribute_overlay(c)},
        ))

    entities.extend(_room_entity(c) for c in rooms)
    return entities, rejected_list


def collect_warnings(
    page_data: PageData,
    candidates: list[Candidate],
    comparison: dict,
    region_warnings: list[dict],
) -> list[dict]:
    warnings = []
    pn = page_data.page_number

    def warn(code, severity, msg, **extra):
        w = {"page_number": pn, "warning_code": code, "severity": severity, "message": msg}
        w.update(extra)
        warnings.append(w)

    if len(page_data.paths) > 1000:
        warn("HIGH_PATH_COUNT", "info", f"Page {pn} has {len(page_data.paths)} paths — extraction may be slow")

    if len(page_data.paths) == 0 and len(page_data.text_spans) == 0 and len(page_data.images) == 0:
        warn("EMPTY_PAGE", "warning", f"Page {pn} has zero paths, text spans, and images")
    elif len(page_data.paths) == 0 and page_data.page_type != "raster-heavy":
        warn("ZERO_PATHS", "warning", f"Page {pn} has no vector paths but is not classified raster-heavy")

    if not page_data.ocg_names:
        warn("MISSING_OCG_LAYER", "info", f"Page {pn}: no OCG layers found in document")

    if len(candidates) == 0:
        warn("NO_CANDIDATES", "warning", f"Page {pn} produced zero heuristic candidates")
    elif all(c.confidence < 0.40 for c in candidates):
        warn("LOW_HEURISTIC_CONFIDENCE", "info", f"Page {pn}: all candidates have confidence < 0.40")

    for any_img in page_data.images:
        if any_img.pixel_area > 0.80:
            warn("LARGE_IMAGE_COVERAGE", "info",
                 f"Page {pn}: image xref={any_img.xref} covers {any_img.pixel_area:.0%} of page (likely scanned)")

    warnings.extend(comparison.get("comparison_warnings", []))
    warnings.extend(region_warnings)

    return warnings


def scale_table(page_scales: PageScales, regions: list[Region]) -> Table:
    """The per-region scale table printed after each page."""
    types = {r.region_id: r.region_type for r in regions}
    table = Table(title="Scales", box=rich_box.SIMPLE_HEAVY)
    table.add_column("Region")
    table.add_column("Type")
    table.add_column("Scale", justify="right")
    table.add_column("Source")
    table.add_column("Evidence")

    for region_id in sorted(page_scales.by_region):
        info = page_scales.by_region[region_id]
        if info.denominator is None:
            shown, style = "UNKNOWN", "yellow"
        else:
            shown, style = format_scale(info.denominator), "green"
        # info.raw and info.conflict are lifted verbatim from PDF text (e.g.
        # scale/text.py's raw=span.text.strip() keeps the whole span, not just
        # the matched "1:N"), so they can contain bracket sequences Rich would
        # otherwise try to parse as markup — escape before it reaches add_row.
        # shown/style stay unescaped: they are program-controlled and their
        # markup is intentional.
        evidence = rich_escape(info.raw) if info.raw else ""
        if info.conflict:
            evidence = f"CONFLICT — {rich_escape(info.conflict)}"
            style = "red"
        elif info.nominal is not None and info.denominator is not None \
                and abs(info.nominal - info.denominator) > 0.05:
            evidence = f"{evidence} → nearest standard {format_scale(info.nominal)}"
        table.add_row(region_id, types.get(region_id, "—"),
                      f"[{style}]{shown}[/{style}]", info.source, evidence)

    if not page_scales.by_region and page_scales.page_scale is not None:
        info = page_scales.page_scale
        table.add_row("(page)", "—",
                      f"[green]{format_scale(info.denominator)}[/green]",
                      info.source, rich_escape(info.raw) if info.raw else "")
    return table


def scale_summary_dict(page_scales: PageScales) -> dict:
    """The scales block written into each page's summary.json entry."""
    def one(info):
        return {"denominator": info.denominator, "source": info.source,
                "raw": info.raw, "nominal": info.nominal,
                "conflict": info.conflict,
                "bbox": list(info.bbox) if info.bbox else None}

    return {
        "by_region": {rid: one(info) for rid, info in page_scales.by_region.items()},
        "page_scale": one(page_scales.page_scale) if page_scales.page_scale else None,
    }


def _page_summary_dict(
    page_data: PageData,
    candidates: list[Candidate],
    entities: list[Entity],
    page_warnings: list[dict],
    regions: list[Region],
    page_scales: PageScales,
) -> dict:
    return {
        "page_number": page_data.page_number,
        "page_type": page_data.page_type,
        "width_px": round(page_data.width_px, 1),
        "height_px": round(page_data.height_px, 1),
        "path_count": len(page_data.paths),
        "text_span_count": len(page_data.text_spans),
        "image_count": len(page_data.images),
        "candidate_count": len(candidates),
        "entity_count": len(entities),
        "warning_count": len(page_warnings),
        "region_count": len(regions),
        "floor_plan_region_count": sum(1 for r in regions if r.region_type == "floor_plan"),
        "scales": scale_summary_dict(page_scales),
    }


@dataclass
class PageRegionResult:
    regions: list[Region]
    detection_page_data: PageData
    schedule_spans: Optional[list[TextSpan]]
    warnings: list[dict]
    skip_detection: bool


def resolve_page_regions(
    pdf_path: str,
    page,
    page_data: PageData,
    gemini_client,
    skip_gemini: bool,
    refresh_regions: bool,
    crop_dir: str,
    classify_fn=classify_regions,
    clip_fn=qualifying_clip_rects,
) -> PageRegionResult:
    """Segment the page, classify its regions, and decide what detection sees.

    classify_fn and clip_fn are injectable so the behaviour rules can be tested
    without credentials or a real fitz.Page.
    """
    pn = page_data.page_number
    warnings: list[dict] = []

    def warn(code, severity, msg):
        warnings.append({"page_number": pn, "warning_code": code,
                         "severity": severity, "message": msg})

    def unfiltered(regions):
        return PageRegionResult(regions, page_data, None, warnings, False)

    # Rule 3: no vector ink at all — a scanned page. Nothing to segment or
    # classify, and calling Gemini would be a wasted request.
    if not page_data.paths:
        warn("RASTER_PAGE_NO_VECTOR_INK", "info",
             f"Page {pn} has no vector paths — segmentation and classification skipped")
        return unfiltered([])

    clip_rects = clip_fn(page, page_data) if page is not None else []
    regions = segment_page(page_data, clip_rects)
    fallback = len(regions) <= 1
    if fallback:
        regions = [page_fallback_region(page_data)]

    # The key covers the freshly-computed region geometry as well as the page
    # content, so a change to layout/ is a cache MISS rather than a silent
    # reuse of stale bboxes — and region bboxes ARE the filtering contract.
    key = cache_key(page_data, regions)
    cached = None if refresh_regions else load_regions(pdf_path, pn, key)

    if cached is not None:
        regions = cached
    elif skip_gemini or gemini_client is None:
        # Rule 4: offline with no usable cache — record the regions but filter
        # nothing, so an offline run never silently differs from an online one.
        warn("REGION_CACHE_MISS_OFFLINE", "warning",
             f"Page {pn}: no cached region classification and Gemini is disabled — "
             f"no region filtering applied")
        return unfiltered(regions)
    else:
        try:
            regions, classify_warnings = classify_fn(
                gemini_client, page, page_data, regions, crop_dir)
            for w in classify_warnings:
                w.setdefault("page_number", pn)
            warnings.extend(classify_warnings)
        except Exception as e:
            # NOT a parse failure — apply_classification reports those itself,
            # without raising, and they are handled just below. Anything that
            # lands here is auth, network, or a programming error.
            warn("REGION_CLASSIFY_FAILED", "error",
                 f"Region classification failed for page {pn}: {e}")
            return unfiltered(regions)
        # A response that did not parse carries no information: every region
        # stays "unclassified", which Rule 1 reads as "no floor plan" and would
        # skip detection — for this run AND every later one, since caching it
        # makes a one-off flake permanent (measured 2026-08-05 on sheet
        # s11: a mid-stream-corrupted response zeroed the sheet until a
        # --refresh-regions happened to land a parseable reply). So a parse
        # failure degrades exactly like the raising path above: warn (the
        # classifier already did), detect the whole page, cache nothing. A
        # PARTIAL response (REGION_CLASSIFY_INCOMPLETE) is real information and
        # still caches.
        if any(w.get("warning_code") == "REGION_CLASSIFY_PARSE_FAILURE"
               for w in classify_warnings):
            return unfiltered(regions)
        # Outside the try: the call above is billed and has already succeeded,
        # so a read-only input directory must not throw its result away.
        try:
            save_regions(pdf_path, pn, key, regions)
        except Exception as e:
            warn("REGION_CACHE_WRITE_FAILED", "warning",
                 f"Page {pn}: region classification succeeded but could not be "
                 f"cached ({e}) — the next run will call the API again")

    # Rule 2: the page never split. Classify for the record, but always detect.
    if fallback:
        return unfiltered(regions)

    # Rule 5: the regions do not hold enough of the sheet to filter by. Record
    # them, warn, and let detection see the whole page — losing a third of a
    # drawing is strictly worse than the elevation noise filtering removes.
    coverage = assigned_path_fraction(page_data, regions)
    if coverage < REGION_MIN_COVERAGE_FRAC:
        warn("REGION_COVERAGE_TOO_LOW", "warning",
             f"Page {pn}: regions hold only {coverage:.0%} of the page's paths "
             f"(floor is {REGION_MIN_COVERAGE_FRAC:.0%}) — no region filtering applied")
        return unfiltered(regions)

    floor_plans = [r for r in regions if r.region_type == "floor_plan"]
    schedules = [r for r in regions if r.region_type == "schedule_table"]

    # Rule 1: a split page with no floor plan has nothing worth detecting.
    if not floor_plans:
        kinds = sorted({r.region_type for r in regions})
        warn("NO_FLOOR_PLAN_REGION", "warning",
             f"Page {pn}: {len(regions)} regions found, none classified floor_plan "
             f"(saw {kinds}) — detection skipped")
        if schedules:
            # No floor plan, but there IS a schedule to read. Detect with an
            # empty path set: that keeps Rule 1's real purpose (no phantom
            # doors or rooms conjured from elevation linework) while still
            # letting detect_schedules see the schedule region's text.
            return PageRegionResult(
                regions, filter_page_data(page_data, []),
                region_text_spans(page_data, schedules), warnings, False)
        return PageRegionResult(regions, page_data, None, warnings, True)

    detection_page_data = filter_page_data(page_data, floor_plans)
    # Schedules live outside the floor plans. With schedule_table regions we
    # scope to them; without, fall back to the WHOLE page's spans — never the
    # floor-plan-filtered ones, or a mislabelled schedule region would be lost.
    schedule_spans = (region_text_spans(page_data, schedules) if schedules
                      else page_data.text_spans)
    return PageRegionResult(regions, detection_page_data, schedule_spans, warnings, False)


def run_extract(
    pdf_path: str,
    page_indices: list[int],
    out_parent: str = "outputs",
    skip_gemini: bool = False,
    disable_walls: bool = False,   # deprecated alias for disable_rooms
    disable_windows: bool = False,
    debug: bool = False,
    disable_rooms: bool = False,
    refresh_regions: bool = False,
) -> str:
    disable_rooms = disable_rooms or disable_walls
    path = Path(pdf_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {pdf_path}[/red]")
        raise FileNotFoundError(pdf_path)

    gemini_client = None
    if not skip_gemini:
        try:
            gemini_client = gc.init_client()
        except EnvironmentError as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[dim]Tip: run 'gcloud auth application-default login' to authenticate[/dim]")
            raise

    doc = fitz.open(str(path))
    total_pages = doc.page_count
    valid_indices = [i for i in page_indices if 0 <= i < total_pages]

    out_dir = make_output_dir(out_parent)
    console.print(f"[bold]Output directory:[/bold] {out_dir}")

    all_page_summaries = []
    all_warnings: list[dict] = []
    total_candidates = 0
    total_entities = 0

    steps = ["extract", "render", "regions", "scale", "plumber", "heuristics",
             "overlay", "save"]
    n_steps = len(steps)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Processing pages...", total=len(valid_indices) * n_steps)

        for idx in valid_indices:
            page_num = idx + 1
            page_dir = make_page_dir(out_dir, page_num)

            def step(name: str):
                progress.update(task, description=f"Page {page_num}/{total_pages} — {name}", advance=1)

            # 1. PyMuPDF extraction
            step("extract")
            page_data = extract_page(doc, idx)

            # 2. Render PNG
            step("render")
            render_path = str(Path(page_dir) / "render.png")
            render_page_png(doc, idx, render_path)

            # 2a-2c. Segment, classify, filter
            step("regions")
            region_result = resolve_page_regions(
                pdf_path=str(path),
                page=doc[idx],
                page_data=page_data,
                gemini_client=gemini_client,
                skip_gemini=skip_gemini,
                refresh_regions=refresh_regions,
                crop_dir=str(Path(page_dir) / "region_crops"),
            )
            write_json(
                str(Path(page_dir) / "regions.json"),
                {
                    "page_number": page_num,
                    "skip_detection": region_result.skip_detection,
                    "regions": [
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
                        for r in region_result.regions
                    ],
                },
            )

            # 2d. Scale — needs the classified regions to bind against.
            step("scale")

            def scale_crop(region, _page_dir=page_dir, _idx=idx):
                """A crop of one region, rendered if it is not already there.

                region_crops/ is written only by the Gemini classification
                call, so on a cache hit, with --no-gemini, or on a raster page
                the directory is empty. The prompt must not send the user to a
                path that does not exist.
                """
                target = Path(_page_dir) / "region_crops" / f"{region.region_id}.png"
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    render_region_crop(doc[_idx], region.bbox, str(target))
                return str(target)

            page_scales = resolve_page_scales(
                page_data=page_data,
                regions=region_result.regions,
                viewports=viewport_scales(doc, doc[idx]),
                stored=load_stored(str(path), page_num),
                pdf_path=str(path),
                crop_fn=scale_crop,
                # Task 8 replaces this literal with the run_extract parameter.
                # It must NOT stay True: regress.py calls run_extract
                # in-process and would inherit a real terminal.
                allow_prompt=True,
            )

            # 3. pdfplumber
            step("plumber")
            plumber_page = extract_plumber_page(str(path), idx)
            pymupdf_counts = build_pymupdf_counts(page_data)
            plumber_counts = build_plumber_counts(plumber_page)
            comparison = compare_counts(pymupdf_counts, plumber_counts)
            comparison["page_number"] = page_num
            comparison["tables"] = [
                {"rows": len(t), "cols": max((len(r) for r in t), default=0), "sample": str(t[0])[:120]}
                for t in plumber_page.get("tables", [])
            ]
            write_json(str(Path(page_dir) / "pdfplumber_comparison.json"), comparison)

            # 4. Heuristics — one pass over the union of the floor-plan regions
            step("heuristics")
            collector = DebugTraceCollector(page_num) if debug else None
            if region_result.skip_detection:
                candidates = []
            else:
                candidates = run_heuristics(
                    region_result.detection_page_data, plumber_page.get("tables", []),
                    disable_rooms=disable_rooms, disable_windows=disable_windows,
                    collector=collector,
                    schedule_text_spans=region_result.schedule_spans,
                )
            total_candidates += len(candidates)
            write_json(
                str(Path(page_dir) / "candidates.json"),
                {"page_number": page_num, "candidates": [_candidate_to_dict(c) for c in candidates]},
            )
            if collector is not None:
                trace_path = str(Path(page_dir) / "debug_trace.json")
                write_json(trace_path, collector.to_dict())
                generate_debug_viewer(
                    render_path,
                    trace_path,
                    str(Path(page_dir) / "debug_viewer.html"),
                )

            # 5. Finalize + overlay
            step("overlay")
            entities, rejected = finalize_candidates(candidates)
            total_entities += len(entities)

            write_json(
                str(Path(page_dir) / "final_entities.json"),
                {
                    "page_number": page_num,
                    "entities": [_entity_to_dict(e) for e in entities],
                    "rejected": rejected,
                },
            )

            overlay_path = str(Path(page_dir) / "overlay.png")
            draw_overlay(render_path, entities, rejected, overlay_path,
                         regions=region_result.regions)

            # 7. Primitives + warnings
            step("save")
            write_json(
                str(Path(page_dir) / "primitives.json"),
                {
                    "page_number": page_num,
                    "width_px": round(page_data.width_px, 1),
                    "height_px": round(page_data.height_px, 1),
                    "ocg_layers": page_data.ocg_names,
                    "paths": [
                        {
                            "path_index": p.path_index,
                            "item_type": p.item_type,
                            "bbox": list(p.bbox),
                            "color": list(p.color) if p.color else None,
                            "fill": list(p.fill) if p.fill else None,
                            "stroke_width": round(p.stroke_width, 3),
                            "dashes": p.dashes,
                            "layer": p.layer,
                            "points": [list(pt) for pt in p.points[:20]],  # cap for readability
                        }
                        for p in page_data.paths
                    ],
                    "text_spans": [
                        {
                            "text": s.text,
                            "bbox": list(s.bbox),
                            "font": s.font,
                            "size": s.size,
                        }
                        for s in page_data.text_spans
                    ],
                    "images": [
                        {
                            "xref": img.xref,
                            "bbox": list(img.bbox),
                            "width": img.width,
                            "height": img.height,
                            "colorspace": img.colorspace,
                            "pixel_area": round(img.pixel_area, 4),
                        }
                        for img in page_data.images
                    ],
                },
            )

            page_warnings = collect_warnings(
                page_data, candidates, comparison, region_result.warnings,
            )
            page_warnings.extend(page_scales.warnings)
            for w in page_warnings:
                w.setdefault("page_number", page_num)
            all_warnings.extend(page_warnings)

            console.print(scale_table(page_scales, region_result.regions))

            all_page_summaries.append(
                _page_summary_dict(page_data, candidates, entities, page_warnings,
                                   region_result.regions, page_scales)
            )

    doc.close()

    # Root-level aggregate files
    meta = fitz.open(str(path)).metadata
    write_json(
        str(Path(out_dir) / "summary.json"),
        {
            "pdf_path": str(path.resolve()),
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_pages": total_pages,
            "processed_pages": [i + 1 for i in valid_indices],
            "output_dir": out_dir,
            "metadata": meta,
            "pages": all_page_summaries,
            "totals": {
                "total_candidates": total_candidates,
                "total_entities": total_entities,
                "total_warnings": len(all_warnings),
            },
        },
    )

    write_json(
        str(Path(out_dir) / "warnings.json"),
        {"total_warnings": len(all_warnings), "warnings": all_warnings},
    )

    console.print(f"\n[green]Done.[/green] Output: [bold]{out_dir}[/bold]")
    console.print(
        f"  Pages: {len(valid_indices)} | "
        f"Candidates: {total_candidates} | "
        f"Entities: {total_entities} | "
        f"Warnings: {len(all_warnings)}"
    )
    return out_dir
