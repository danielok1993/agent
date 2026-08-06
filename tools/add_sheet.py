#!/usr/bin/env python3
"""Adopt a new PDF into the regression corpus.

The manifest — not the directory — is the authority on corpus membership, so a
PDF dropped into fixtures/sheets/ is ignored by the sweep until it is adopted.

Usage:
    python tools/add_sheet.py ~/Downloads/SOME_PLAN.pdf --desc existing-floor-plans
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # noqa: E402

from regression import corpus as fx  # noqa: E402
from regression.ground_truth import write_empty_truth  # noqa: E402


def next_slug(sheets: list[dict]) -> str:
    highest = 0
    for entry in sheets:
        match = re.fullmatch(r"s(\d+)", entry["slug"])
        if match:
            highest = max(highest, int(match.group(1)))
    return f"s{highest + 1:02d}"


def _kebab(desc: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", desc.lower()).strip("-")


def adopt(source: Path, desc: str) -> dict:
    digest = fx.sha256_of(source)
    for entry in fx.manifest_sheets():
        if entry["sha256"] == digest:
            raise ValueError(f"already in the corpus as {entry['slug']} "
                             f"({entry['file']}) — nothing to do")

    manifest = fx.load_manifest()
    sheets = manifest.get("sheets", [])
    slug = next_slug(sheets)
    filename = f"{slug}-{_kebab(desc)}.pdf"

    fx.SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    target = fx.SHEETS_DIR / filename
    shutil.copy2(source, target)

    doc = fitz.open(target)
    pages = doc.page_count
    doc.close()

    entry = {"slug": slug, "file": filename, "sha256": digest,
             "pages": pages, "tier": "corpus"}
    sheets.append(entry)
    manifest["sheets"] = sorted(sheets, key=lambda s: s["slug"])
    fx.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_empty_truth(slug, digest)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--desc", required=True,
                        help="drawing type only, e.g. existing-floor-plans — "
                             "never a property identifier")
    args = parser.parse_args()

    try:
        entry = adopt(args.pdf, args.desc)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"adopted {entry['slug']} -> fixtures/sheets/{entry['file']} "
          f"({entry['pages']} page(s))")
    print("\nnext:")
    print(f"  1. seed the region cache with one Gemini-enabled run:")
    print(f"       python app.py extract fixtures/sheets/{entry['file']}")
    print(f"  2. upload fixtures/sheets/{entry['file']} and its "
          f".regions_cache/ entry to shared storage")
    print(f"  3. commit fixtures/MANIFEST.json and tests/ground_truth/{entry['slug']}.json")
    print(f"  4. label it: python tools/regress.py --sheet {entry['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
