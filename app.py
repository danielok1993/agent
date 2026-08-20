#!/usr/bin/env python3
"""
Architectural PDF extraction CLI.

Commands:
  inspect <pdf>  -- print a terminal summary of PDF content
  extract <pdf>  -- run full extraction pipeline and write JSON + PNG outputs
"""
from __future__ import annotations
import argparse
import sys


def parse_page_spec(spec: str, total_pages: int) -> list[int]:
    """Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]."""
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            try:
                lo_i, hi_i = int(lo.strip()), int(hi.strip())
                for n in range(lo_i, hi_i + 1):
                    if 1 <= n <= total_pages:
                        indices.add(n - 1)
            except ValueError:
                print(f"Warning: invalid page range '{part}' — skipping", file=sys.stderr)
        else:
            try:
                n = int(part)
                if 1 <= n <= total_pages:
                    indices.add(n - 1)
                else:
                    print(f"Warning: page {n} out of range (1–{total_pages}) — skipping", file=sys.stderr)
            except ValueError:
                print(f"Warning: invalid page number '{part}' — skipping", file=sys.stderr)
    return sorted(indices)


def cmd_inspect(args: argparse.Namespace) -> None:
    import fitz
    from pathlib import Path

    pdf_path = args.pdf
    if not Path(pdf_path).exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(pdf_path)
    total = doc.page_count

    if args.pages:
        page_indices = parse_page_spec(args.pages, total)
        if not page_indices:
            print("Error: no valid pages specified.", file=sys.stderr)
            sys.exit(1)
    else:
        page_indices = list(range(total))

    doc.close()

    from inspector import inspect_pdf
    inspect_pdf(pdf_path, page_indices)


def cmd_extract(args: argparse.Namespace) -> None:
    import fitz
    from pathlib import Path

    pdf_path = args.pdf
    if not Path(pdf_path).exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(pdf_path)
    total = doc.page_count

    if args.pages:
        page_indices = parse_page_spec(args.pages, total)
        if not page_indices:
            print("Error: no valid pages specified.", file=sys.stderr)
            sys.exit(1)
    else:
        page_indices = list(range(total))

    doc.close()

    from pipeline import run_extract
    run_extract(
        pdf_path=pdf_path,
        page_indices=page_indices,
        out_parent=args.out,
        skip_gemini=args.no_gemini,
        disable_rooms=args.disable_rooms,
        disable_windows=args.disable_windows,
        debug=args.debug,
        refresh_regions=args.refresh_regions,
        write_svg=args.write_svg,
        allow_scale_prompt=not args.no_scale_prompt,
        ceiling_height=args.ceiling_height,
        door_height=args.door_height,
        window_height=args.window_height,
    )


def positive_metres(text: str) -> float:
    """argparse type: a positive, finite height in metres."""
    from takeoff.heights import valid_height_m
    try:
        return valid_height_m(float(text), "flag")
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive number of metres, got {text!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Architectural PDF extraction — vector-first, Gemini-assisted",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- inspect ---
    p_inspect = sub.add_parser("inspect", help="Print terminal summary of PDF content")
    p_inspect.add_argument("pdf", help="Path to the PDF file")
    p_inspect.add_argument(
        "--pages",
        metavar="SPEC",
        help="Page selection, e.g. '1' or '1,3-5' (default: all pages)",
    )
    p_inspect.set_defaults(func=cmd_inspect)

    # --- extract ---
    p_extract = sub.add_parser("extract", help="Run full extraction pipeline")
    p_extract.add_argument("pdf", help="Path to the PDF file")
    p_extract.add_argument(
        "--pages",
        metavar="SPEC",
        help="Page selection, e.g. '1' or '1,3-5' (default: all pages)",
    )
    p_extract.add_argument(
        "--out",
        default="outputs",
        metavar="DIR",
        help="Parent directory for output (default: outputs/)",
    )
    p_extract.add_argument(
        "--no-gemini",
        action="store_true",
        dest="no_gemini",
        help="Skip Gemini calls (heuristics-only mode)",
    )
    p_extract.add_argument(
        "--refresh-regions",
        action="store_true",
        dest="refresh_regions",
        help="Ignore the cached region classification and call Gemini again",
    )
    p_extract.add_argument(
        "--disable-rooms",
        action="store_true",
        dest="disable_rooms",
        help="Skip wall-network + room detection (useful when tuning window/door results)",
    )
    p_extract.add_argument(
        "--disable-walls",
        action="store_true",
        dest="disable_rooms",
        help="Deprecated alias for --disable-rooms",
    )
    p_extract.add_argument(
        "--disable-windows",
        action="store_true",
        dest="disable_windows",
        help="Skip window detection (useful when tuning wall/door results)",
    )
    p_extract.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        help="Write debug_trace.json per page with per-primitive detection trace",
    )
    p_extract.add_argument(
        "--svg",
        action="store_true",
        dest="write_svg",
        help="Also write page.svg per page — MuPDF's vector redraw of the page in "
             "render.png's 150-DPI coordinate space (off by default: image-heavy "
             "sheets run to tens of MB)",
    )
    p_extract.add_argument(
        "--no-scale-prompt",
        action="store_true",
        help="Never ask for a drawing scale; record it as unresolved instead. "
             "Set automatically by batch_extract and regress.py, which run "
             "unattended but may still inherit a terminal.",
    )
    p_extract.add_argument(
        "--ceiling-height", type=positive_metres, default=None, metavar="M",
        help="Ceiling height in metres for the wall-area takeoff (default: ask on a tty, else 2.4)",
    )
    p_extract.add_argument(
        "--door-height", type=positive_metres, default=None, metavar="M",
        help="Door opening height in metres (default 2.1)",
    )
    p_extract.add_argument(
        "--window-height", type=positive_metres, default=None, metavar="M",
        help="Window opening height in metres, sill to head (default 1.2)",
    )
    p_extract.set_defaults(func=cmd_extract)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
