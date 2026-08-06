#!/usr/bin/env python3
# tools/regress.py
"""Run the regression corpus and diff it against the committed ground truth.

Usage:
    python tools/regress.py               # every non-retired manifest sheet
    python tools/regress.py --sheet s07   # one or more slugs
    python tools/regress.py --json        # machine-readable results
    python tools/regress.py --debug       # also write the per-primitive debug
                                           # trace (debug_trace.json +
                                           # debug_viewer.html) per page --
                                           # off by default; it scales with
                                           # primitive count and cost 200-300MB
                                           # per sheet on the corpus's heavier
                                           # sheets (s16, s18)

Exit codes: 0 clean (REVIEW items allowed), 1 regression, 2 incomplete corpus.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regression.report import exit_code, render  # noqa: E402
from regression.sweep import sweep  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", action="append", dest="sheets",
                        help="slug to run (repeatable); default is the whole corpus")
    parser.add_argument("--json", action="store_true", help="emit JSON results")
    parser.add_argument("--debug", action="store_true",
                        help="write the per-primitive debug trace "
                             "(debug_trace.json + debug_viewer.html) per page; "
                             "off by default because it scales with primitive "
                             "count, not page count -- 200-300MB/sheet on the "
                             "corpus's heavier sheets")
    args = parser.parse_args()

    results = sweep(args.sheets, debug_traces=args.debug)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))
    else:
        print(render(results))
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
