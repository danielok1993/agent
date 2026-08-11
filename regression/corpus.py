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


def set_labeled(slug: str, value: bool = True) -> None:
    """Flip a manifest entry's `labeled` flag and write the manifest back.

    `labeled: true` is the durable, diffable claim that a human recorded
    verdicts for this sheet -- the sweep fails when a flagged sheet's ground
    truth goes missing (see sweep._labeled_but_unreviewed), so setting it is
    what makes a review session's work impossible to lose silently.

    The manifest's on-disk order is preserved: `load_manifest` reads the file
    as written, unlike `manifest_sheets` which sorts a copy.
    """
    manifest = load_manifest()
    for entry in manifest.get("sheets", []):
        if entry["slug"] == slug:
            entry["labeled"] = value
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n",
                                     encoding="utf-8")
            return
    raise ValueError(f"{slug} is not in {MANIFEST_PATH}")
