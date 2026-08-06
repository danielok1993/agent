"""Resolution of corpus fixture sheets by slug.

The PDFs are NDA-covered and never committed. `fixtures/MANIFEST.json` is
committed and is the authority on corpus membership; `fixtures/sheets/` is
populated by manual download (see tools/fetch_fixtures.py).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
SHEETS_DIR = FIXTURES_DIR / "sheets"
MANIFEST_PATH = FIXTURES_DIR / "MANIFEST.json"


def load_manifest() -> dict:
    """The committed manifest, or an empty corpus when it is absent."""
    if not MANIFEST_PATH.exists():
        return {"storage": "", "sheets": []}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_sheets() -> list[dict]:
    return sorted(load_manifest().get("sheets", []), key=lambda s: s["slug"])


def sheet_entry(slug: str) -> dict | None:
    for entry in manifest_sheets():
        if entry["slug"] == slug:
            return entry
    return None


def sheet_path(slug: str) -> Path | None:
    """Path to a downloaded sheet, or None when it is not on disk."""
    entry = sheet_entry(slug)
    if entry is None:
        return None
    path = SHEETS_DIR / entry["file"]
    return path if path.exists() else None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
