# tools/migrate_fixtures.py
"""One-shot migration of the sample PDFs into fixtures/sheets/.

Renames every sheet to its slug, moves the region caches alongside, and writes
fixtures/MANIFEST.json. Idempotent: sheets already in place are left alone.

Usage:  python tools/migrate_fixtures.py [--dry-run]
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parent.parent
SHEETS = REPO / "fixtures" / "sheets"
MANIFEST = REPO / "fixtures" / "MANIFEST.json"
STORAGE_NOTE = ("the corpus bundle is not public — ask the maintainer for it, "
                "and make sure every sheet is downloaded before sweeping")

# (slug, new filename, source path relative to the repo root, tier)
PLAN = [
    ("s01", "s01-floor-plans.pdf", "floor-plans.pdf", "reference"),
    ("s02", "s02-working-drawing-wd03.pdf", "5-1133-WD03.pdf", "reference"),
    ("s03", "s03-existing-and-proposed-elevations-and-floor-plans.pdf",
     "plans/EXISTING_AND_PROPOSED_ELEVATIONS_AND_FLOOR_PLANS-2557737.pdf", "corpus"),
    ("s04", "s04-existing-first-floor-plan.pdf",
     "plans/EXISTING_FIRST_FLOOR_PLAN-4103493.pdf", "corpus"),
    ("s05", "s05-existing-floor-and-elevations.pdf",
     "plans/EXISTING_FLOOR_AND_ELEVATIONS-1326087.pdf", "corpus"),
    ("s06", "s06-existing-floor-and-elevation-plan.pdf",
     "plans/EXISTING_FLOOR_AND_ELEVATION_PLAN-3055574.pdf", "corpus"),
    ("s07", "s07-existing-floor-plans.pdf",
     "plans/EXISTING_FLOOR_PLANS-3228943.pdf", "corpus"),
    ("s08", "s08-existing-ground-floor-plan.pdf",
     "plans/EXISTING_GROUND_FLOOR_PLAN-4103495.pdf", "corpus"),
    ("s09", "s09-floor-plan-existing.pdf",
     "plans/FLOOR_PLAN_-_EXISTING-3565362.pdf", "corpus"),
    ("s10", "s10-location-plan-and-all-existing-information.pdf",
     "plans/LOCATION_PLAN_AND_ALL_EXISTING_INFORMATION-772263.pdf", "corpus"),
    ("s11", "s11-location-plan-block-plan-existing-plans-and-elevations.pdf",
     "plans/LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241.pdf", "corpus"),
    ("s12", "s12-proposed-floor-and-elevations.pdf",
     "plans/PROPOSED_FLOOR_AND_ELEVATIONS-1326086.pdf", "corpus"),
    ("s13", "s13-proposed-floor-and-elevation-plan.pdf",
     "plans/PROPOSED_FLOOR_AND_ELEVATION_PLAN-3055578.pdf", "corpus"),
    ("s14", "s14-proposed-floor-plans.pdf",
     "plans/PROPOSED_FLOOR_PLANS-574477.pdf", "corpus"),
    ("s15", "s15-proposed-floor-plans-and-elevations.pdf",
     "plans/PROPOSED_FLOOR_PLANS_AND_ELEVATIONS-3228948.pdf", "corpus"),
    ("s16", "s16-proposed-plans-and-elevations.pdf",
     "plans/PROPOSED_PLANS_AND_ELEVATIONS-2710870.pdf", "corpus"),
    ("s17", "s17-rev-b-single-plan-all-information.pdf",
     "plans/REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461.pdf", "corpus"),
    ("s18", "s18-rev-proposed-plans-and-elevations.pdf",
     "plans/REV_._PROPOSED_PLANS_AND_ELEVATIONS-1789452.pdf", "corpus"),
    ("s19", "s19-second-floor-plan-roof-existing.pdf",
     "plans/SECOND_FLOOR_PLAN_ROOF_-_EXISTING-3565363.pdf", "corpus"),
    ("s20", "s20-single-plan-all-information.pdf",
     "plans/SINGLE_PLAN_ALL_INFORMATION-2387826.pdf", "corpus"),
]


def main(dry_run: bool) -> int:
    sys.path.insert(0, str(REPO))
    from regression.corpus import sha256_of

    SHEETS.mkdir(parents=True, exist_ok=True)
    cache_dir = SHEETS / ".regions_cache"
    entries, missing = [], []

    for slug, new_name, source, tier in PLAN:
        target = SHEETS / new_name
        src = REPO / source
        if not target.exists():
            if not src.exists():
                missing.append(source)
                continue
            print(f"{'DRY ' if dry_run else ''}move {source} -> fixtures/sheets/{new_name}")
            if not dry_run:
                shutil.move(str(src), str(target))
                old_cache = src.parent / ".regions_cache"
                if old_cache.is_dir():
                    cache_dir.mkdir(exist_ok=True)
                    for cached in old_cache.glob(f"{src.stem}_p*.json"):
                        shutil.move(str(cached), str(cache_dir / cached.name.replace(
                            src.stem, target.stem)))
        if dry_run or not target.exists():
            continue
        doc = fitz.open(target)
        pages = doc.page_count
        doc.close()
        entries.append({"slug": slug, "file": new_name, "sha256": sha256_of(target),
                        "pages": pages, "tier": tier})

    if missing:
        print(f"\nnot found (already migrated, or absent locally):")
        for m in missing:
            print(f"  {m}")
    if dry_run:
        return 0

    MANIFEST.write_text(json.dumps(
        {"storage": STORAGE_NOTE, "sheets": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {MANIFEST} with {len(entries)} sheets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--dry-run" in sys.argv))
