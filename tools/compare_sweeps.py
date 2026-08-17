#!/usr/bin/env python3
# tools/compare_sweeps.py
"""Show what a detection change did to one sheet, side by side.

The sweep reports verdict deltas (LOST / FALSE POSITIVE RETURNED / REVIEW);
this renders the drawing behind them. Workflow:

    python tools/regress.py --sheet s03                 # baseline sweep
    python tools/compare_sweeps.py s03 --snapshot       # keep it as the baseline
    ... change detection ...
    python tools/regress.py --sheet s03                 # re-sweep
    python tools/compare_sweeps.py s03                  # baseline vs latest run

Writes outputs/compare/<slug>/page_NN_side_by_side.png (both runs, every
entity coloured by its ground-truth verdict: green confirmed, red false
positive, orange deferred, blue unreviewed) and page_NN_changes.png (a zoomed
before|after row for every entity present in only one run), and prints the
same changes as text.

    python tools/compare_sweeps.py s03 --before DIR --after DIR   # explicit run dirs
    python tools/compare_sweeps.py s03 --type window              # one entity type

Baselines live in outputs/regress_baseline/<slug>/ (gitignored, one per slug;
--snapshot replaces the previous one).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regression.compare import compare, render_summary, snapshot  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", help="sheet slug, e.g. s03")
    parser.add_argument("--snapshot", action="store_true",
                        help="copy the slug's latest sweep run aside as its baseline and exit")
    parser.add_argument("--before", type=Path, help="baseline run dir (default: the snapshot)")
    parser.add_argument("--after", type=Path, help="run dir to compare (default: the latest sweep run)")
    parser.add_argument("--out", type=Path, help="output dir (default outputs/compare/<slug>)")
    parser.add_argument("--type", action="append", dest="types",
                        help="entity type to compare (repeatable); default all")
    args = parser.parse_args()

    try:
        if args.snapshot:
            print(f"baseline saved: {snapshot(args.slug)}")
            return 0
        comparisons, out_dir = compare(args.slug, before_dir=args.before, after_dir=args.after,
                                       out_dir=args.out, types=set(args.types) if args.types else None)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(render_summary(args.slug, comparisons, out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
