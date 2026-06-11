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
        disable_walls=args.disable_walls,
        disable_windows=args.disable_windows,
        debug=args.debug,
    )


def main() -> None:
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
        "--disable-walls",
        action="store_true",
        dest="disable_walls",
        help="Skip wall detection (useful when tuning window/door results)",
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
    p_extract.set_defaults(func=cmd_extract)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
