from __future__ import annotations
from pathlib import Path
from typing import Optional
import fitz
import pdfplumber
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box as rich_box
from rich.markup import escape as rich_escape
from models import PageData, ScaleInfo
from extraction.extractor import extract_page, SCALE
from extraction.plumber import extract_plumber_page, build_plumber_counts, build_pymupdf_counts, compare_counts
from detection import run_heuristics
from scale.text import text_scales
from scale.units import cluster_denominators, format_scale
from scale.viewport import viewport_scales

console = Console()

PAGE_TYPE_COLORS = {
    "vector-rich": "green",
    "raster-heavy": "red",
    "mixed": "yellow",
    "unknown": "dim",
}


def _page_type_styled(page_type: str) -> str:
    color = PAGE_TYPE_COLORS.get(page_type, "white")
    return f"[{color}]{page_type}[/{color}]"


def unbound_scale_lines(
    viewports: list[ScaleInfo], texts: list[ScaleInfo]
) -> list[str]:
    """Scales stated on the sheet, unbound to any drawing.

    inspect does not segment regions, so there is nothing to bind to. Repeated
    viewport scales are counted rather than repeated — s17 states 1:100 four
    times, once per plan.
    """
    if not viewports and not texts:
        return ["[dim]Scales: none found in viewports or text[/dim]"]

    lines: list[str] = []

    # Grouped with cluster_denominators, not counted by raw float. s17's four
    # 1:100 viewports measure 99.986, 99.988, 99.993 and 99.995 — keying on
    # the float prints four identical "1:100" lines instead of one "(×4)".
    groups = cluster_denominators(
        info.denominator for info in viewports if info.denominator is not None)
    for group in groups:
        suffix = f" (×{len(group)})" if len(group) > 1 else ""
        lines.append(f"[bold]Scale (viewport):[/bold] "
                     f"{format_scale(group[0])}{suffix}")

    # Keyed on (raw, denominator), not raw alone: one span can state several
    # scales. s20's title block reads "1:50  & 1:100" and text_scales emits
    # two ScaleInfos sharing that raw string — deduping on raw would list
    # 1:50 and silently drop 1:100, on one of only three sheets that resolve
    # by text at all.
    seen: set[tuple[str, Optional[float]]] = set()
    for info in texts:
        if info.denominator is None:
            continue
        raw = (info.raw or "").strip()
        key = (raw.lower(), info.denominator)
        if key in seen:
            continue
        seen.add(key)
        escaped_raw = rich_escape(raw) if raw else ""
        lines.append(f"[bold]Scale (text):[/bold] "
                     f"{format_scale(info.denominator)} — '{escaped_raw}'")
    return lines


def print_file_header(pdf_path: str, doc: fitz.Document) -> None:
    meta = doc.metadata or {}
    info_lines = [
        f"[bold]File:[/bold] {pdf_path}",
        f"[bold]Pages:[/bold] {doc.page_count}",
        f"[bold]Title:[/bold] {meta.get('title', '—')}",
        f"[bold]Author:[/bold] {meta.get('author', '—')}",
        f"[bold]Creator:[/bold] {meta.get('creator', '—')}",
        f"[bold]Producer:[/bold] {meta.get('producer', '—')}",
    ]
    console.print(Panel("\n".join(info_lines), title="PDF Info", expand=False))


def print_page_summary(
    page_data: PageData,
    plumber_page: dict,
    comparison: dict,
    candidates,
    scale_lines: list[str],
) -> None:
    pymupdf_counts = build_pymupdf_counts(page_data)
    plumber_counts = build_plumber_counts(plumber_page)

    # Main counts table
    table = Table(title=f"Page {page_data.page_number}", box=rich_box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("Metric", style="bold")
    table.add_column("PyMuPDF", justify="right")
    table.add_column("pdfplumber", justify="right")

    table.add_row("Paths / Lines+Rects+Curves",
                  str(pymupdf_counts["paths"]),
                  str(plumber_counts["lines"] + plumber_counts["rects"] + plumber_counts["curves"]))
    table.add_row("Text spans / Chars",
                  str(pymupdf_counts["text_spans"]),
                  str(plumber_counts["chars"]))
    table.add_row("Images",
                  str(pymupdf_counts["images"]),
                  str(plumber_counts["images"]))
    table.add_row("Layers (OCGs)",
                  str(pymupdf_counts["ocgs"]),
                  "—")
    table.add_row("Tables detected",
                  "—",
                  str(plumber_counts["tables"]))
    console.print(table)

    # Page metadata panel
    meta_lines = [
        f"[bold]Size:[/bold] {page_data.width_px:.0f} × {page_data.height_px:.0f} px at 150 DPI",
        f"[bold]Classification:[/bold] {_page_type_styled(page_data.page_type)}",
        f"[bold]Heuristic candidates:[/bold] {len(candidates)}",
    ]

    if page_data.ocg_names:
        meta_lines.append(f"[bold]Layers:[/bold] {', '.join(page_data.ocg_names[:8])}")
    else:
        meta_lines.append("[yellow]Warning:[/yellow] No OCG layers found")

    if page_data.images:
        coverages = [f"{img.pixel_area:.0%}" for img in page_data.images]
        meta_lines.append(f"[bold]Images:[/bold] {len(page_data.images)} (coverage: {', '.join(coverages)})")

    for w in comparison.get("comparison_warnings", []):
        meta_lines.append(f"[yellow]⚠ {w['message']}[/yellow]")

    meta_lines.extend(scale_lines)

    console.print(Panel("\n".join(meta_lines), expand=False))


def print_candidates_tree(candidates) -> None:
    if not candidates:
        console.print("[dim]  No heuristic candidates detected.[/dim]")
        return

    tree = Tree(f"[bold]Candidates ({len(candidates)})[/bold]")
    by_type: dict[str, list] = {}
    for c in candidates:
        by_type.setdefault(c.entity_type, []).append(c)

    type_colors = {
        "door": "red",
        "window": "blue",
        "wall": "magenta",
        "label": "green",
        "schedule": "yellow",
    }
    for etype, cands in sorted(by_type.items()):
        color = type_colors.get(etype, "white")
        branch = tree.add(f"[{color}]{etype}s ({len(cands)})[/{color}]")
        for c in cands[:5]:
            ev_str = ", ".join(f"{k}={v}" for k, v in list(c.evidence.items())[:3])
            branch.add(f"{c.candidate_id} conf={c.confidence:.2f} | {ev_str}")
        if len(cands) > 5:
            branch.add(f"[dim]... and {len(cands) - 5} more[/dim]")

    console.print(tree)


def inspect_pdf(pdf_path: str, page_indices: list[int]) -> None:
    path = Path(pdf_path)
    if not path.exists():
        console.print(f"[red]Error: File not found: {pdf_path}[/red]")
        return

    doc = fitz.open(str(path))
    print_file_header(str(path), doc)

    valid_indices = [i for i in page_indices if 0 <= i < doc.page_count]
    if not valid_indices:
        console.print(f"[red]No valid pages to inspect (total pages: {doc.page_count})[/red]")
        doc.close()
        return

    for idx in valid_indices:
        page_data = extract_page(doc, idx)
        plumber_page = extract_plumber_page(str(path), idx)
        pymupdf_counts = build_pymupdf_counts(page_data)
        plumber_counts = build_plumber_counts(plumber_page)
        comparison = compare_counts(pymupdf_counts, plumber_counts)
        candidates = run_heuristics(page_data, plumber_page.get("tables", []))
        scale_lines = unbound_scale_lines(
            viewport_scales(doc, doc[idx]), text_scales(page_data))
        print_page_summary(page_data, plumber_page, comparison, candidates, scale_lines)
        print_candidates_tree(candidates)
        console.rule()

    doc.close()
