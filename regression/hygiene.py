"""Shared address-detection patterns for corpus hygiene checks.

Two callers share these patterns rather than each keeping its own copy:

  tests/test_ground_truth_hygiene.py — scans committed ground truth AND the
      committed fixtures/MANIFEST.json for leaked address text.
  tools/add_sheet.py — rejects an address-bearing --desc up front, before it
      is ever kebab-cased into a tracked manifest `file` value (the failure
      mode the manifest scan above exists to catch after the fact).
"""
from __future__ import annotations

import re

POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b")

# A raw, human-typed description: "14 Bramble Road" — capitalised word(s)
# separated by whitespace.
STREET_RE = re.compile(
    r"\b\d+[a-z]?\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s+"
    r"(street|road|lane|avenue|close|drive|way|crescent|terrace|court|place)\b",
    re.IGNORECASE)

# The same street-name shape after tools/add_sheet.py's `_kebab()` has run:
# lowercase, hyphen-separated ("14 Bramble Road" -> "14-bramble-road"). This
# is the shape that ends up in fixtures/MANIFEST.json's `file` values, and
# STREET_RE's capitalised-word + whitespace requirement never matches it.
KEBAB_STREET_RE = re.compile(
    r"\b\d+-[a-z0-9]+(-[a-z0-9]+)*-"
    r"(street|road|lane|avenue|close|drive|way|crescent|terrace|court|place)\b",
    re.IGNORECASE)


def address_match(text: str) -> str | None:
    """The matched address-like substring in `text`, or None."""
    for pattern in (POSTCODE_RE, STREET_RE, KEBAB_STREET_RE):
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None
