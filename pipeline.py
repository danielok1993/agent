from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import fitz
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from models import PageData, Candidate, Entity
from extraction.extractor import extract_page
from extraction.plumber import (
    extract_plumber_page, build_pymupdf_counts, build_plumber_counts, compare_counts
)
from detection import run_heuristics
from debug.trace import DebugTraceCollector
from debug.renderer import generate_debug_viewer
from extraction.renderer import render_page_png, draw_overlay
from gemini import client as gc

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


OFFLINE_MIN_CONFIDENCE: dict[str, float] = {
    "door":     0.55,
    "window":   0.50,
    "wall":     0.55,
    "label":    0.65,
    "schedule": 0.50,
}


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


def merge_gemini_and_heuristics(
    candidates: list[Candidate],
    gemini_result: Optional[dict],
) -> tuple[list[Entity], list[dict]]:
    if not gemini_result:
        # Offline path: apply stricter per-type acceptance thresholds.
        # Without Gemini's verification, raw heuristic candidates have poor
        # precision. Candidates below the threshold are saved as rejected for
        # debugging but do not become final entities.
        entities = []
        rejected_list = []
        for c in candidates:
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
        return entities, rejected_list

    candidate_map = {c.candidate_id: c for c in candidates}
    classified_ids: set[str] = set()
    rejected_ids: set[str] = set()
    entities: list[Entity] = []
    rejected_list: list[dict] = []

    for rej in gemini_result.get("rejected_candidates", []):
        cid = rej.get("candidate_id", "")
        rejected_ids.add(cid)
        if cid in candidate_map:
            c = candidate_map[cid]
            rejected_list.append({
                "candidate_id": cid,
                "entity_type": c.entity_type,
                "bbox": list(c.bbox),
                "reason": rej.get("reason", ""),
                "source": "gemini",
            })

    for key, etype in [
        ("doors", "door"),
        ("windows", "window"),
        ("walls", "wall"),
        ("labels", "label"),
        ("schedules", "schedule"),
    ]:
        for item in gemini_result.get(key, []):
            cid = item.get("candidate_id", "")
            if cid in rejected_ids:
                continue
            classified_ids.add(cid)
            base = candidate_map.get(cid)
            bbox = base.bbox if base else (0, 0, 0, 0)
            heuristic_conf = base.confidence if base else 0.0
            gemini_conf = float(item.get("confidence", 0.0))

            label = item.get("label") or item.get("text")

            entities.append(Entity(
                entity_id=cid,
                entity_type=etype,
                bbox=bbox,
                confidence=round(max(gemini_conf, heuristic_conf * 0.5 + gemini_conf * 0.5), 3),
                source="gemini",
                label=label,
                attributes={
                    "heuristic_confidence": heuristic_conf,
                    "gemini_confidence": gemini_conf,
                    "gemini_notes": item.get("notes", ""),
                    "thickness_px": item.get("thickness_px"),
                    "rows": item.get("rows"),
                    "cols": item.get("cols"),
                    **_door_attribute_overlay(base),
                },
            ))

    # Heuristic-only fallback for candidates Gemini didn't address
    for c in candidates:
        if c.candidate_id not in classified_ids and c.candidate_id not in rejected_ids:
            entities.append(Entity(
                entity_id=c.candidate_id,
                entity_type=c.entity_type,
                bbox=c.bbox,
                confidence=c.confidence,
                source="heuristic",
                label=c.evidence.get("nearby_label") or c.evidence.get("text"),
                attributes={"heuristic_confidence": c.confidence, **_door_attribute_overlay(c)},
            ))

    return entities, rejected_list


def collect_warnings(
    page_data: PageData,
    candidates: list[Candidate],
    gemini_result: Optional[dict],
    comparison: dict,
    gemini_skipped: bool,
    gemini_warnings: list[dict],
    skip_gemini_flag: bool = False,
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

    if gemini_skipped:
        if skip_gemini_flag:
            warn("GEMINI_SKIPPED_FLAG", "info", f"Page {pn}: Gemini skipped (--no-gemini flag)")
        else:
            warn("RASTER_HEAVY_SKIPPED", "info", f"Page {pn}: raster-heavy with 0 candidates — Gemini skipped")

    for any_img in page_data.images:
        if any_img.pixel_area > 0.80:
            warn("LARGE_IMAGE_COVERAGE", "info",
                 f"Page {pn}: image xref={any_img.xref} covers {any_img.pixel_area:.0%} of page (likely scanned)")

    warnings.extend(comparison.get("comparison_warnings", []))
    warnings.extend(gemini_warnings)

    return warnings


def _page_summary_dict(
    page_data: PageData,
    candidates: list[Candidate],
    entities: list[Entity],
    gemini_skipped: bool,
    page_warnings: list[dict],
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
        "gemini_skipped": gemini_skipped,
        "entity_count": len(entities),
        "warning_count": len(page_warnings),
    }


def run_extract(
    pdf_path: str,
    page_indices: list[int],
    out_parent: str = "outputs",
    skip_gemini: bool = False,
    disable_walls: bool = False,
    disable_windows: bool = False,
    debug: bool = False,
) -> str:
    path = Path(pdf_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {pdf_path}[/red]")
        raise FileNotFoundError(pdf_path)

    # Initialize Gemini client unless skipped
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
    total_gemini_calls = 0
    total_gemini_skipped = 0

    steps = ["extract", "render", "plumber", "heuristics", "gemini", "overlay", "save"]
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

            # 4. Heuristics
            step("heuristics")
            collector = DebugTraceCollector(page_num) if debug else None
            candidates = run_heuristics(
                page_data, plumber_page.get("tables", []),
                disable_walls=disable_walls, disable_windows=disable_windows,
                collector=collector,
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

            # 5. Gemini
            step("gemini")
            gemini_result = None
            gemini_warnings: list[dict] = []
            gemini_skipped = skip_gemini or gc.should_skip_gemini(page_data, candidates)

            if not gemini_skipped and gemini_client is not None:
                try:
                    gemini_result, gemini_warnings = gc.call_gemini(
                        gemini_client, page_data, candidates, render_path
                    )
                    total_gemini_calls += 1
                except Exception as e:
                    gemini_warnings.append({
                        "page_number": page_num,
                        "warning_code": "GEMINI_CALL_FAILED",
                        "severity": "error",
                        "message": f"Gemini call failed for page {page_num}: {e}",
                    })
                    gemini_skipped = True

            gemini_json: dict
            if gemini_skipped:
                total_gemini_skipped += 1
                reason = "skip_gemini flag" if skip_gemini else "raster-heavy page with zero candidates"
                gemini_json = {"page_number": page_num, "skipped": True, "reason": reason}
            else:
                gemini_json = gemini_result or {}
            write_json(str(Path(page_dir) / "gemini_result.json"), gemini_json)

            # 6. Merge + overlay
            step("overlay")
            entities, rejected = merge_gemini_and_heuristics(candidates, gemini_result if not gemini_skipped else None)
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
            draw_overlay(render_path, entities, rejected, overlay_path)

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
                page_data, candidates, gemini_result,
                comparison, gemini_skipped, gemini_warnings,
                skip_gemini_flag=skip_gemini,
            )
            for w in page_warnings:
                w.setdefault("page_number", page_num)
            all_warnings.extend(page_warnings)

            all_page_summaries.append(
                _page_summary_dict(page_data, candidates, entities, gemini_skipped, page_warnings)
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
                "gemini_calls": total_gemini_calls,
                "gemini_skipped_pages": total_gemini_skipped,
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
