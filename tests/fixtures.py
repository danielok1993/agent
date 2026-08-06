"""Skip helper for tests that need a real corpus sheet.

Corpus knowledge lives in regression/corpus.py; this is only the unittest
bridge, so a clone without the downloaded bundle skips loudly rather than
silently passing.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from regression.corpus import SHEETS_DIR, sheet_path

_WARNED = False


def require_sheet(test_case: unittest.TestCase, slug: str) -> Path:
    """Return the sheet's path, or skip the test with an actionable message."""
    global _WARNED
    path = sheet_path(slug)
    if path is None:
        if not _WARNED:
            _WARNED = True
            print(f"\n[fixtures] corpus sheets missing from {SHEETS_DIR} — "
                  f"real-PDF tests will skip. Run: python tools/fetch_fixtures.py")
        test_case.skipTest(f"fixture sheet {slug} not downloaded")
    return path
