# Regression Corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn 20 real architectural sheets into regression gates by committing the user's per-sheet detection verdicts and checking every run against them.

**Architecture:** PDFs move out of the repo into a gitignored `fixtures/sheets/` populated by manual download and verified by sha256 against a committed manifest. Human verdicts live in `tests/ground_truth/sNN.json` and are matched against pipeline output geometrically (IoU ≥ 0.5). A new `regression/` package holds the loader, matcher and reporter; `tools/regress.py` is the thin CLI, mirroring the existing root-entry-point-plus-package layout.

**Tech Stack:** Python 3, `unittest` (no pytest in this repo), PyMuPDF (`fitz`), stdlib `json`/`hashlib`/`dataclasses`. No new dependencies.

## Global Constraints

- **Run everything inside the venv:** `source .venv/bin/activate` before any `python` command. Bare `python` is not on PATH.
- **Tests are `unittest`, not pytest.** Run with `python -m unittest tests.test_x.ClassName.test_name`.
- **No PDF may be committed.** `fixtures/sheets/` is gitignored; only `fixtures/MANIFEST.json` and `tests/ground_truth/*.json` are committed.
- **No address-bearing data in git.** Planning-portal application IDs (e.g. `2682241`) resolve to a property address on the public portal and count as address-bearing. They must not appear in any tracked file after Task 3.
- **All coordinates are 150-DPI pixel space, top-left origin, y-down.** `BBox` is `(x0, y0, x1, y1)`. Never reintroduce point-space.
- **Never add a `Co-Authored-By` trailer to commits.**
- **Slug content is immutable.** A revised drawing is adopted as a new slug; an existing slug's bytes never change.
- **The 8-second unit suite stays out of the sweep.** `python -m unittest discover tests` must not run the corpus.
- Spec: `docs/superpowers/specs/2026-08-06-regression-corpus-design.md`

## Slug Assignment (authoritative — used by Tasks 2 and 3)

| Slug | New filename | Former filename | Portal ID |
|---|---|---|---|
| s01 | `s01-floor-plans.pdf` | `floor-plans.pdf` | — |
| s02 | `s02-working-drawing-wd03.pdf` | `5-1133-WD03.pdf` | — |
| s03 | `s03-existing-and-proposed-elevations-and-floor-plans.pdf` | `EXISTING_AND_PROPOSED_ELEVATIONS_AND_FLOOR_PLANS-2557737.pdf` | 2557737 |
| s04 | `s04-existing-first-floor-plan.pdf` | `EXISTING_FIRST_FLOOR_PLAN-4103493.pdf` | 4103493 |
| s05 | `s05-existing-floor-and-elevations.pdf` | `EXISTING_FLOOR_AND_ELEVATIONS-1326087.pdf` | 1326087 |
| s06 | `s06-existing-floor-and-elevation-plan.pdf` | `EXISTING_FLOOR_AND_ELEVATION_PLAN-3055574.pdf` | 3055574 |
| s07 | `s07-existing-floor-plans.pdf` | `EXISTING_FLOOR_PLANS-3228943.pdf` | 3228943 |
| s08 | `s08-existing-ground-floor-plan.pdf` | `EXISTING_GROUND_FLOOR_PLAN-4103495.pdf` | 4103495 |
| s09 | `s09-floor-plan-existing.pdf` | `FLOOR_PLAN_-_EXISTING-3565362.pdf` | 3565362 |
| s10 | `s10-location-plan-and-all-existing-information.pdf` | `LOCATION_PLAN_AND_ALL_EXISTING_INFORMATION-772263.pdf` | 772263 |
| s11 | `s11-location-plan-block-plan-existing-plans-and-elevations.pdf` | `LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241.pdf` | 2682241 |
| s12 | `s12-proposed-floor-and-elevations.pdf` | `PROPOSED_FLOOR_AND_ELEVATIONS-1326086.pdf` | 1326086 |
| s13 | `s13-proposed-floor-and-elevation-plan.pdf` | `PROPOSED_FLOOR_AND_ELEVATION_PLAN-3055578.pdf` | 3055578 |
| s14 | `s14-proposed-floor-plans.pdf` | `PROPOSED_FLOOR_PLANS-574477.pdf` | 574477 |
| s15 | `s15-proposed-floor-plans-and-elevations.pdf` | `PROPOSED_FLOOR_PLANS_AND_ELEVATIONS-3228948.pdf` | 3228948 |
| s16 | `s16-proposed-plans-and-elevations.pdf` | `PROPOSED_PLANS_AND_ELEVATIONS-2710870.pdf` | 2710870 |
| s17 | `s17-rev-b-single-plan-all-information.pdf` | `REV_._B_SINGLE_PLAN_ALL_INFORMATION-3447461.pdf` | 3447461 |
| s18 | `s18-rev-proposed-plans-and-elevations.pdf` | `REV_._PROPOSED_PLANS_AND_ELEVATIONS-1789452.pdf` | 1789452 |
| s19 | `s19-second-floor-plan-roof-existing.pdf` | `SECOND_FLOOR_PLAN_ROOF_-_EXISTING-3565363.pdf` | 3565363 |
| s20 | `s20-single-plan-all-information.pdf` | `SINGLE_PLAN_ALL_INFORMATION-2387826.pdf` | 2387826 |

`s01` and `s02` are `tier: "reference"`; `s03`–`s20` are `tier: "corpus"`. `plans/PROPOSED_GROUND_FLOOR_PLANS_AND_EXTENSION_ELEVATIONS-963191.tif` is a raster TIFF, not a PDF — it is **not** part of the corpus. Leave it in storage, unreferenced.

---

## File Structure

**Created:**
- `regression/corpus.py` — manifest reading, slug → path resolution, hashing
- `tests/fixtures.py` — the `skipTest` helper real-PDF tests use (thin shim over `regression.corpus`)
- `regression/__init__.py` — public facade (`load_truth`, `match_entities`)
- `regression/ground_truth.py` — ground-truth dataclasses, load + validate
- `regression/matching.py` — IoU and greedy type-scoped matching
- `regression/report.py` — per-sheet result rendering + exit-code decision
- `regression/sweep.py` — runs the pipeline per sheet and produces results
- `tools/regress.py` — CLI entry point
- `tools/fetch_fixtures.py` — corpus completeness verifier
- `tools/add_sheet.py` — adopt a new PDF into the corpus
- `tools/migrate_fixtures.py` — one-shot Task 2 migration
- `tests/test_fixtures_loader.py`, `tests/test_ground_truth.py`, `tests/test_matching.py`, `tests/test_regress_report.py`, `tests/test_add_sheet.py`, `tests/test_ground_truth_hygiene.py`
- `fixtures/MANIFEST.json` (committed), `tests/ground_truth/sNN.json` (committed)

**Modified:**
- `.gitignore` — replace `/plans/` with the `fixtures` rules
- `tests/test_layout_golden.py:19-20,30-53,65-66` — slug loader
- `tests/test_window_detection.py:582-584` — slug loader
- `tests/test_extraction_transform.py:29,204` — slug loader
- `batch_extract.py:3,128-138` — discovery directory
- `README.md:99,103` — corpus documentation
- 22 tracked files carrying 128 portal-ID mentions (Task 3)

---

### Task 1: Corpus loader

`regression/corpus.py` owns everything that knows about the corpus; `tests/fixtures.py` is a four-line shim holding only the unittest skip helper. Production-side code never imports from `tests/`.

**Files:**
- Create: `regression/__init__.py`, `regression/corpus.py`, `tests/fixtures.py`
- Test: `tests/test_fixtures_loader.py`

**Interfaces:**
- Consumes: nothing.
- Produces: from `regression.corpus` — `FIXTURES_DIR: Path`, `SHEETS_DIR: Path`, `MANIFEST_PATH: Path`, `load_manifest() -> dict`, `manifest_sheets() -> list[dict]`, `sheet_entry(slug: str) -> dict | None`, `sheet_path(slug: str) -> Path | None`, `sha256_of(path: Path) -> str`; from `tests.fixtures` — `require_sheet(test_case: unittest.TestCase, slug: str) -> Path`. Tasks 2, 4, 7, 9 and the three migrated test files import from these.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixtures_loader.py
"""The corpus loader resolves slugs against the committed manifest.

Every test builds its own temporary fixtures tree and points the module at it,
so the suite passes whether or not the real corpus has been downloaded.
"""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as fx
from tests.fixtures import require_sheet


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "sheets" / "s01-floor-plans.pdf").write_bytes(b"%PDF-1.4 fake")
        (root / "MANIFEST.json").write_text(json.dumps({
            "storage": "ask the maintainer",
            "sheets": [
                {"slug": "s01", "file": "s01-floor-plans.pdf",
                 "sha256": "0" * 64, "pages": 1, "tier": "reference"},
                {"slug": "s02", "file": "s02-working-drawing-wd03.pdf",
                 "sha256": "1" * 64, "pages": 1, "tier": "reference"},
            ],
        }))
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = root
        fx.SHEETS_DIR = root / "sheets"
        fx.MANIFEST_PATH = root / "MANIFEST.json"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved
        self.tmp.cleanup()

    def test_manifest_sheets_are_returned_in_slug_order(self):
        self.assertEqual([s["slug"] for s in fx.manifest_sheets()], ["s01", "s02"])

    def test_sheet_entry_looks_up_by_slug(self):
        self.assertEqual(fx.sheet_entry("s02")["file"], "s02-working-drawing-wd03.pdf")

    def test_sheet_entry_is_none_for_an_unknown_slug(self):
        self.assertIsNone(fx.sheet_entry("s99"))

    def test_sheet_path_resolves_a_downloaded_sheet(self):
        self.assertTrue(fx.sheet_path("s01").exists())

    def test_sheet_path_is_none_when_the_file_was_never_downloaded(self):
        self.assertIsNone(fx.sheet_path("s02"))

    def test_sha256_of_hashes_file_bytes(self):
        p = fx.sheet_path("s01")
        self.assertEqual(len(fx.sha256_of(p)), 64)
        self.assertEqual(fx.sha256_of(p), fx.sha256_of(p))

    def test_require_sheet_skips_when_the_file_is_absent(self):
        with self.assertRaises(unittest.SkipTest):
            require_sheet(self, "s02")

    def test_require_sheet_returns_the_path_when_present(self):
        self.assertEqual(require_sheet(self, "s01").name, "s01-floor-plans.pdf")

    def test_missing_manifest_reads_as_an_empty_corpus(self):
        fx.MANIFEST_PATH = Path(self.tmp.name) / "nope.json"
        self.assertEqual(fx.manifest_sheets(), [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_fixtures_loader -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'regression'`

- [ ] **Step 3: Write the implementation**

`regression/__init__.py` starts as a docstring only; Tasks 5 and 6 add the re-exports as their modules land.

```python
# regression/__init__.py
"""Regression corpus: fixture resolution, ground truth, matching, and the sweep."""
```

```python
# regression/corpus.py
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


```

```python
# tests/fixtures.py
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
```

Note: `require_sheet` reads `sheet_path` through the module import, so a test that
monkeypatches `regression.corpus.SHEETS_DIR` is seen by both modules.

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_fixtures_loader -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add regression/__init__.py regression/corpus.py tests/fixtures.py tests/test_fixtures_loader.py
git commit -m "test: corpus loader resolving fixture sheets by slug"
```

---

### Task 2: Migrate the sheets into the fixtures layout

This task moves files, generates the manifest, and updates every consumer in one commit — the move breaks the three real-PDF tests and `batch_extract.py`, so they must land together.

**Files:**
- Create: `tools/migrate_fixtures.py`, `fixtures/MANIFEST.json` (generated)
- Modify: `.gitignore`, `tests/test_layout_golden.py`, `tests/test_window_detection.py:582-584`, `tests/test_extraction_transform.py:29,204`, `batch_extract.py:3,128-138`, `README.md:99,103`
- Delete from git: `floor-plans.pdf`, `5-1133-WD03.pdf`

- [ ] **Step 1: Capture the pre-migration baseline**

The migration must not change detection output. Snapshot two sheets first:

```bash
source .venv/bin/activate
python app.py extract floor-plans.pdf --no-gemini --out /tmp/premig-s01
python app.py extract plans/EXISTING_FLOOR_PLANS-3228943.pdf --no-gemini --out /tmp/premig-s07
```

Note the two run directory paths printed — they are needed in Step 8.

- [ ] **Step 2: Write the migration script**

```python
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
STORAGE_NOTE = "TODO-STORAGE-LOCATION"

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
```

- [ ] **Step 3: Dry-run, then migrate**

```bash
source .venv/bin/activate
python tools/migrate_fixtures.py --dry-run     # read the 20 planned moves
python tools/migrate_fixtures.py
```

Expected: `wrote …/fixtures/MANIFEST.json with 20 sheets`. Verify:

```bash
ls fixtures/sheets/ | wc -l          # 20 (plus .regions_cache)
python -c "import json;print(len(json.load(open('fixtures/MANIFEST.json'))['sheets']))"
```

- [ ] **Step 4: Update `.gitignore`**

Replace the `/plans/` line. The `/fixtures/*` form (with the star) is required — `/fixtures/` alone excludes the directory itself and git will not reconsider the negation inside it.

```gitignore
__pycache__/

outputs/

.DS_Store

# The corpus sheets are NDA-covered and never committed. Only the manifest is
# tracked; fixtures/sheets/ is populated by manual download —
# see tools/fetch_fixtures.py and docs/superpowers/specs/2026-08-06-regression-corpus-design.md
/fixtures/*
!/fixtures/MANIFEST.json

.regions_cache/

# Subagent-driven-development scratch (ledgers, briefs, review packages)
.superpowers/
```

Verify the negation works before going further:

```bash
git check-ignore -v fixtures/sheets/s01-floor-plans.pdf   # must print a rule
git check-ignore -v fixtures/MANIFEST.json                # must print NOTHING (exit 1)
```

- [ ] **Step 5: Untrack the two reference PDFs**

```bash
git rm --cached floor-plans.pdf 5-1133-WD03.pdf
```

They are already gone from the working tree (moved in Step 3). The blobs remain in history — that is accepted; see the spec's non-goals.

- [ ] **Step 6: Switch the three real-PDF tests to the slug loader**

In `tests/test_layout_golden.py`, replace the module header's `REPO`/`segment` helper and the class constant:

```python
import os
import unittest

import fitz

from extraction.extractor import extract_page
from layout import qualifying_clip_rects, segment_page
from layout.occupancy import build_ink_map, is_page_spanning
from tests.fixtures import require_sheet


def segment(test_case, slug, page_index=0, use_clips=True):
    path = require_sheet(test_case, slug)
    doc = fitz.open(path)
    page_data = extract_page(doc, page_index)
    clips = qualifying_clip_rects(doc[page_index], page_data) if use_clips else []
    regions = segment_page(page_data, clips)
    doc.close()
    return page_data, regions
```

Every call site gains `self` and a slug: `segment("floor-plans.pdf")` → `segment(self, "s01")` (lines 30, 34, 38), `segment("5-1133-WD03.pdf")` → `segment(self, "s02")` (line 53). In `TestSpanFilterIsLoadBearing`, drop the `PDF` constant and the three `@unittest.skipUnless` decorators, and open the sheet through the loader instead:

```python
class TestSpanFilterIsLoadBearing(unittest.TestCase):
    """This sheet carries full-page border rules. With the span filter applied
    the ink map has no page-spanning rows and the sheet splits into 13 regions.
    The counterfactual — 0 regions with the filter disabled — was measured on
    2026-07-28 but cannot be asserted here: build_ink_map applies the filter
    unconditionally, and adding a production parameter purely for this test
    was rejected as over-building."""

    def _page_data(self):
        doc = fitz.open(require_sheet(self, "s11"))
        page_data = extract_page(doc, 0)
        doc.close()
        return page_data
```

Each of the three tests then starts `page_data = self._page_data()`. `require_sheet` skips exactly as `skipUnless` did.

In `tests/test_window_detection.py`, replace `setUp` at lines 582-584:

```python
    def setUp(self):
        from tests.fixtures import require_sheet
        self.pdf = str(require_sheet(self, "s01"))
```

In `tests/test_extraction_transform.py`, delete the `ROTATED_SHEET` constant (line 29) and the `@unittest.skipUnless` at line 204, opening through the loader instead:

```python
    def test_real_rotated_sheet_lands_entirely_inside_the_render_frame(self):
        from tests.fixtures import require_sheet
        doc = fitz.open(require_sheet(self, "s12"))
```

- [ ] **Step 7: Point `batch_extract.py` and `README.md` at the new directory**

`batch_extract.py` line 3 docstring and lines 128-138:

```python
    plans_dir = Path("fixtures/sheets")
    if not plans_dir.exists():
        print("Error: fixtures/sheets/ not found. Run: python tools/fetch_fixtures.py",
              file=sys.stderr)
        sys.exit(1)

    pdfs = find_pdfs(plans_dir)
    if not pdfs:
        print("No PDFs found in fixtures/sheets/. Exiting.")
        sys.exit(0)

    print(f"\nFound {len(pdfs)} PDFs in fixtures/sheets/\n")
```

`README.md` lines 99 and 103 — replace the "Sample PDFs … are checked in" sentence with:

```markdown
The regression corpus lives in `fixtures/sheets/` and is **not** committed: the
sheets are NDA-covered. Download the bundle (location in `fixtures/MANIFEST.json`)
and verify it with `python tools/fetch_fixtures.py`. Sheets are referred to by
slug — `s01` and `s02` are the two primary reference sheets.
```

and the batch section's `plans/*.pdf` → `fixtures/sheets/*.pdf`.

- [ ] **Step 8: Verify nothing about detection changed**

```bash
source .venv/bin/activate
python -m unittest discover tests            # 432 tests, no new skips beyond corpus-absent
python app.py extract fixtures/sheets/s01-floor-plans.pdf --no-gemini --out /tmp/postmig-s01
python app.py extract fixtures/sheets/s07-existing-floor-plans.pdf --no-gemini --out /tmp/postmig-s07
python tools/compare_entities.py /tmp/premig-s01/<run> /tmp/postmig-s01/<run>
python tools/compare_entities.py /tmp/premig-s07/<run> /tmp/postmig-s07/<run>
```

Expected: both comparisons report identical output. If `s07` differs, the region cache did not move with the file — check `fixtures/sheets/.regions_cache/` contains `s07-existing-floor-plans_p01_*.json`.

- [ ] **Step 9: Commit**

```bash
git add -A .gitignore fixtures/MANIFEST.json tools/migrate_fixtures.py \
        tests/test_layout_golden.py tests/test_window_detection.py \
        tests/test_extraction_transform.py batch_extract.py README.md
git commit -m "refactor: move sample sheets into the fixtures corpus

Sheets are renamed to slugs and moved to fixtures/sheets/, which is gitignored
(NDA). Only fixtures/MANIFEST.json is tracked. Real-PDF tests resolve sheets
through tests/fixtures.require_sheet, so a clone without the bundle skips them
cleanly. Detection output verified identical on s01 and s07."
```

- [ ] **Step 10: Hand off the storage upload (human step)**

Report to the user: the 20 renamed files plus `fixtures/sheets/.regions_cache/` need uploading to shared storage under their new names, and the real storage location must replace `TODO-STORAGE-LOCATION` in `fixtures/MANIFEST.json`. Do not proceed to Task 3 without asking whether they want that string filled in now.

---

### Task 3: Scrub portal IDs from the working tree

128 mentions across 22 tracked files. Portal IDs resolve to property addresses on the public planning portal.

**Files:**
- Modify: `CLAUDE.md`, `detection/orchestrator.py`, `detection/walls.py`, `docs/2026-08-04-region-clip-fix-and-batch-timeout-findings.md`, `docs/2026-08-05-gemini-classification-parse-failure.md`, `docs/2026-08-05-windows-detection-optimization.md`, `docs/superpowers/plans/2026-07-28-floor-plan-region-filtering.md`, `docs/superpowers/specs/2026-07-03-batch-extraction-design.md`, `docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md`, `extraction/extractor.py`, `gemini/classifier.py`, `layout/clips.py`, `layout/constants.py`, `layout/segmenter.py`, `pipeline.py`, `tests/test_extraction_transform.py`, `tests/test_layout_golden.py`, `tests/test_layout_segmenter.py`, `tests/test_orchestrator_timing.py`, `tests/test_region_classifier.py`, `tests/test_region_pipeline.py`, `tests/test_wall_network.py`
- Create: nothing

- [ ] **Step 1: Rewrite every portal ID to its slug**

```bash
cd /Users/nestimate/Documents/GitHub/agent
FILES=$(git grep -l -E "2557737|4103493|1326087|3055574|3228943|4103495|3565362|772263|2682241|1326086|3055578|574477|3228948|2710870|3447461|1789452|3565363|2387826" -- '*.py' '*.md' | grep -v graphify-out)
for pair in 2557737:s03 4103493:s04 1326087:s05 3055574:s06 3228943:s07 4103495:s08 \
            3565362:s09 772263:s10 2682241:s11 1326086:s12 3055578:s13 574477:s14 \
            3228948:s15 2710870:s16 3447461:s17 1789452:s18 3565363:s19 2387826:s20; do
  id="${pair%%:*}"; slug="${pair##*:}"
  echo "$FILES" | xargs sed -i '' "s/${id}/${slug}/g"
done
```

- [ ] **Step 2: Read the diff and fix the wreckage**

```bash
git diff --stat
git diff | less
```

Mechanical substitution mangles prose. Fix by hand:
- Full former filenames now read `EXISTING_FLOOR_PLANS-s07.pdf` — rewrite the whole reference to `s07`.
- Sentences like "measured on 2682241" become "measured on s11" — correct, keep.
- The spec written today (`docs/superpowers/specs/2026-08-06-regression-corpus-design.md`) is exempt: it documents the migration and its slug table legitimately pairs IDs with slugs. **Exclude it** — if `git diff` shows it changed, revert that one file with `git checkout -- <path>`.
- `docs/superpowers/plans/2026-08-06-regression-corpus.md` (this plan) is likewise exempt for the same reason.

- [ ] **Step 3: Verify no portal ID survives**

```bash
git grep -n -E "\b(2557737|4103493|1326087|3055574|3228943|4103495|3565362|772263|2682241|1326086|3055578|574477|3228948|2710870|3447461|1789452|3565363|2387826)\b" \
  -- '*.py' '*.md' | grep -v graphify-out | grep -v "2026-08-06-regression-corpus"
```

Expected: no output.

- [ ] **Step 4: Run the suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: 432 tests, OK. Only comments and docstrings changed; a failure means a substitution hit live code.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: refer to corpus sheets by slug, not planning-portal id

Portal application ids resolve to a property address on the public portal.
128 mentions across 22 files rewritten to sNN slugs; the migration spec and
plan keep the mapping table by design."
```

- [ ] **Step 6: Update the memory files (not in git)**

21 files under `/Users/nestimate/.claude/projects/-Users-nestimate-Documents-GitHub-agent/memory/` reference sheets by portal ID or by the old filenames. Apply the same substitutions there, plus `floor-plans` → `s01` and `5-1133` → `s02`, so future sessions recall names that still exist. Read each diff — these are prose notes, and `floor-plans` appears inside sentences.

---

### Task 4: Corpus verifier

**Files:**
- Create: `tools/fetch_fixtures.py`
- Test: `tests/test_fetch_fixtures.py`

**Interfaces:**
- Consumes: `regression.corpus` — `manifest_sheets`, `sha256_of`, `SHEETS_DIR`, `load_manifest`.
- Produces: `check_corpus() -> CorpusStatus` where `CorpusStatus` is a dataclass with `present: list[str]`, `missing: list[str]`, `mismatched: list[str]`, `untracked: list[str]`, and `ok: bool` (true when `missing`, `mismatched` and `untracked` are all empty). This is the user-facing verifier only — `regression/sweep.py` classifies sheets itself so one missing sheet cannot abort the whole run.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_fixtures.py
"""The corpus verifier classifies each manifest sheet against the disk."""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as fx
from tools.fetch_fixtures import check_corpus


class CheckCorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sheets").mkdir()
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = self.root
        fx.SHEETS_DIR = self.root / "sheets"
        fx.MANIFEST_PATH = self.root / "MANIFEST.json"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved
        self.tmp.cleanup()

    def _write(self, name, data=b"%PDF-1.4 real"):
        (self.root / "sheets" / name).write_bytes(data)
        return fx.sha256_of(self.root / "sheets" / name)

    def _manifest(self, sheets):
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": sheets}))

    def test_a_matching_sheet_is_present(self):
        digest = self._write("s01-a.pdf")
        self._manifest([{"slug": "s01", "file": "s01-a.pdf", "sha256": digest,
                         "pages": 1, "tier": "reference"}])
        status = check_corpus()
        self.assertEqual(status.present, ["s01"])
        self.assertTrue(status.ok)

    def test_a_sheet_absent_from_disk_is_missing(self):
        self._manifest([{"slug": "s02", "file": "s02-b.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "corpus"}])
        status = check_corpus()
        self.assertEqual(status.missing, ["s02"])
        self.assertFalse(status.ok)

    def test_wrong_bytes_are_mismatched_not_present(self):
        self._write("s03-c.pdf", b"%PDF-1.4 revised")
        self._manifest([{"slug": "s03", "file": "s03-c.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "corpus"}])
        status = check_corpus()
        self.assertEqual(status.mismatched, ["s03"])
        self.assertEqual(status.present, [])

    def test_a_pdf_not_in_the_manifest_is_untracked(self):
        self._write("stray.pdf")
        self._manifest([])
        self.assertEqual(check_corpus().untracked, ["stray.pdf"])

    def test_a_retired_sheet_is_not_reported_missing(self):
        self._manifest([{"slug": "s04", "file": "s04-d.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "retired"}])
        status = check_corpus()
        self.assertEqual(status.missing, [])
        self.assertTrue(status.ok)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_fetch_fixtures -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.fetch_fixtures'`

- [ ] **Step 3: Write the implementation**

```python
# tools/fetch_fixtures.py
"""Verify the downloaded corpus against the committed manifest.

Download is manual: the sheets are NDA-covered and live in shared storage.
This tool tells you what is missing, what has the wrong bytes, and what is
sitting in fixtures/sheets/ without being part of the corpus.

Usage:  python tools/fetch_fixtures.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regression.corpus import (  # noqa: E402
    SHEETS_DIR, load_manifest, manifest_sheets, sha256_of,
)


@dataclass
class CorpusStatus:
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.mismatched or self.untracked)


def check_corpus() -> CorpusStatus:
    status = CorpusStatus()
    known_files = set()
    for entry in manifest_sheets():
        if entry.get("tier") == "retired":
            known_files.add(entry["file"])
            continue
        path = SHEETS_DIR / entry["file"]
        known_files.add(entry["file"])
        if not path.exists():
            status.missing.append(entry["slug"])
        elif sha256_of(path) != entry["sha256"]:
            status.mismatched.append(entry["slug"])
        else:
            status.present.append(entry["slug"])
    if SHEETS_DIR.is_dir():
        for pdf in sorted(SHEETS_DIR.glob("*.pdf")):
            if pdf.name not in known_files:
                status.untracked.append(pdf.name)
    return status


def main() -> int:
    status = check_corpus()
    storage = load_manifest().get("storage") or "(storage location not recorded)"
    print(f"corpus: {len(status.present)} present, {len(status.missing)} missing, "
          f"{len(status.mismatched)} mismatched, {len(status.untracked)} untracked")
    for slug in status.missing:
        print(f"  MISSING     {slug} — download from {storage}")
    for slug in status.mismatched:
        print(f"  MISMATCH    {slug} — bytes differ from the manifest; "
              f"a revised drawing must be adopted as a NEW slug "
              f"(python tools/add_sheet.py <file>), never dropped over an existing one")
    for name in status.untracked:
        print(f"  UNTRACKED   {name} — adopt it with: python tools/add_sheet.py "
              f"fixtures/sheets/{name} --desc <drawing-type>")
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_fetch_fixtures -v`
Expected: PASS, 5 tests

Then against the real corpus: `python tools/fetch_fixtures.py` → `corpus: 20 present, 0 missing, 0 mismatched, 0 untracked`

- [ ] **Step 5: Commit**

```bash
git add tools/fetch_fixtures.py tests/test_fetch_fixtures.py
git commit -m "feat: corpus verifier for the downloaded fixture bundle"
```

---

### Task 5: Ground-truth schema and loader

**Files:**
- Create: `regression/__init__.py`, `regression/ground_truth.py`
- Test: `tests/test_ground_truth.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `TruthItem` (dataclass: `type: str`, `bbox: tuple[float, float, float, float]`, `tag: str | None`, `path_indices: list[int]`, `note: str`), `PageTruth` (dataclass: `confirmed`, `false_positives`, `deferred` — each `list[TruthItem]`), `SheetTruth` (dataclass: `slug: str`, `pdf_sha256: str | None`, `reviewed: str | None`, `pages: dict[int, PageTruth]`, plus `page(n: int) -> PageTruth` returning an empty `PageTruth` for an unlabeled page and `is_labeled: bool`), `TRUTH_DIR: Path`, `load_truth(slug: str) -> SheetTruth`, `truth_path(slug: str) -> Path`, `write_empty_truth(slug: str, sha: str) -> Path`. Tasks 7, 8 and 9 consume these.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ground_truth.py
"""Ground-truth files are the durable record of the user's verdicts."""
import json
import tempfile
import unittest
from pathlib import Path

import regression.ground_truth as gt


class LoadTruthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = gt.TRUTH_DIR
        gt.TRUTH_DIR = Path(self.tmp.name)

    def tearDown(self):
        gt.TRUTH_DIR = self._saved
        self.tmp.cleanup()

    def _write(self, slug, payload):
        (gt.TRUTH_DIR / f"{slug}.json").write_text(json.dumps(payload))

    def test_a_sheet_with_no_file_loads_as_unlabeled(self):
        truth = gt.load_truth("s09")
        self.assertFalse(truth.is_labeled)
        self.assertEqual(truth.page(1).confirmed, [])

    def test_reviewed_null_means_unlabeled(self):
        self._write("s09", {"sheet": "s09", "pdf_sha256": "a" * 64,
                            "reviewed": None, "pages": {}})
        self.assertFalse(gt.load_truth("s09").is_labeled)

    def test_confirmed_items_parse_into_truth_items(self):
        self._write("s01", {"sheet": "s01", "pdf_sha256": "a" * 64,
                            "reviewed": "2026-08-06", "pages": {"1": {
                                "confirmed": [{"type": "door",
                                               "bbox": [10, 20, 30, 40],
                                               "tag": "GD9",
                                               "path_indices": [1576],
                                               "note": "front entrance"}]}}})
        item = gt.load_truth("s01").page(1).confirmed[0]
        self.assertEqual(item.type, "door")
        self.assertEqual(item.bbox, (10.0, 20.0, 30.0, 40.0))
        self.assertEqual(item.tag, "GD9")
        self.assertEqual(item.path_indices, [1576])

    def test_missing_lists_default_to_empty(self):
        self._write("s01", {"sheet": "s01", "pdf_sha256": "a" * 64,
                            "reviewed": "2026-08-06",
                            "pages": {"1": {"confirmed": []}}})
        page = gt.load_truth("s01").page(1)
        self.assertEqual((page.false_positives, page.deferred), ([], []))

    def test_an_unlabeled_page_of_a_labeled_sheet_is_empty(self):
        self._write("s01", {"sheet": "s01", "pdf_sha256": "a" * 64,
                            "reviewed": "2026-08-06", "pages": {"1": {}}})
        self.assertEqual(gt.load_truth("s01").page(7).confirmed, [])

    def test_a_bbox_that_is_not_four_numbers_is_rejected(self):
        self._write("s01", {"sheet": "s01", "pdf_sha256": "a" * 64,
                            "reviewed": "2026-08-06", "pages": {"1": {
                                "confirmed": [{"type": "door", "bbox": [1, 2, 3]}]}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s01")

    def test_an_unknown_verdict_list_is_rejected(self):
        self._write("s01", {"sheet": "s01", "pdf_sha256": "a" * 64,
                            "reviewed": "2026-08-06",
                            "pages": {"1": {"maybes": []}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s01")

    def test_write_empty_truth_creates_an_unlabeled_file(self):
        path = gt.write_empty_truth("s21", "b" * 64)
        self.assertTrue(path.exists())
        loaded = gt.load_truth("s21")
        self.assertFalse(loaded.is_labeled)
        self.assertEqual(loaded.pdf_sha256, "b" * 64)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_ground_truth -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'regression'`

- [ ] **Step 3: Write the implementation**

Add the ground-truth re-exports to the existing `regression/__init__.py` (matching lands in Task 6):

```python
# regression/__init__.py
"""Regression corpus: fixture resolution, ground truth, matching, and the sweep."""
from regression.ground_truth import SheetTruth, TruthItem, load_truth

__all__ = ["SheetTruth", "TruthItem", "load_truth"]
```

```python
# regression/ground_truth.py
"""The user's per-sheet verdicts, and how they are read.

One file per sheet under tests/ground_truth/. Three verdict lists per page:

  confirmed        — the user has said this detection is correct
  false_positives  — the user has said this detection is wrong
  deferred         — a miss the user reported that we consciously chose not to
                     fix; never speculative, never a run failure

`reviewed: null` is a valid state: the sheet is adopted but unlabeled, so every
detection on it reads as unreviewed and nothing can fail.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRUTH_DIR = REPO_ROOT / "tests" / "ground_truth"

VERDICTS = ("confirmed", "false_positives", "deferred")


@dataclass
class TruthItem:
    type: str
    bbox: tuple[float, float, float, float]
    tag: str | None = None
    path_indices: list[int] = field(default_factory=list)
    note: str = ""


@dataclass
class PageTruth:
    confirmed: list[TruthItem] = field(default_factory=list)
    false_positives: list[TruthItem] = field(default_factory=list)
    deferred: list[TruthItem] = field(default_factory=list)


@dataclass
class SheetTruth:
    slug: str
    pdf_sha256: str | None = None
    reviewed: str | None = None
    pages: dict[int, PageTruth] = field(default_factory=dict)

    @property
    def is_labeled(self) -> bool:
        return bool(self.reviewed)

    def page(self, number: int) -> PageTruth:
        return self.pages.get(number, PageTruth())


def truth_path(slug: str) -> Path:
    return TRUTH_DIR / f"{slug}.json"


def _item(raw: dict, slug: str) -> TruthItem:
    bbox = raw.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"{slug}: bbox must be four numbers, got {bbox!r}")
    if not raw.get("type"):
        raise ValueError(f"{slug}: every ground-truth item needs a type")
    return TruthItem(
        type=raw["type"],
        bbox=tuple(float(v) for v in bbox),
        tag=raw.get("tag"),
        path_indices=list(raw.get("path_indices", [])),
        note=raw.get("note", ""),
    )


def load_truth(slug: str) -> SheetTruth:
    path = truth_path(slug)
    if not path.exists():
        return SheetTruth(slug=slug)
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages: dict[int, PageTruth] = {}
    for number, lists in (payload.get("pages") or {}).items():
        unknown = set(lists) - set(VERDICTS)
        if unknown:
            raise ValueError(f"{slug} page {number}: unknown verdict list(s) "
                             f"{sorted(unknown)}; expected {list(VERDICTS)}")
        pages[int(number)] = PageTruth(
            **{v: [_item(r, slug) for r in lists.get(v, [])] for v in VERDICTS})
    return SheetTruth(slug=payload.get("sheet", slug),
                      pdf_sha256=payload.get("pdf_sha256"),
                      reviewed=payload.get("reviewed"),
                      pages=pages)


def write_empty_truth(slug: str, sha: str) -> Path:
    """Create the unlabeled ground-truth file for a newly adopted sheet."""
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    path = truth_path(slug)
    path.write_text(json.dumps(
        {"sheet": slug, "pdf_sha256": sha, "reviewed": None, "pages": {}},
        indent=2) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_ground_truth -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add regression/__init__.py regression/ground_truth.py tests/test_ground_truth.py
git commit -m "feat: ground-truth schema and loader for the regression corpus"
```

---

### Task 6: Geometric matching

**Files:**
- Create: `regression/matching.py`
- Modify: `regression/__init__.py` — add `from regression.matching import iou, match_entities` and extend `__all__` to `["SheetTruth", "TruthItem", "load_truth", "iou", "match_entities"]`
- Test: `tests/test_matching.py`

**Interfaces:**
- Consumes: `regression.ground_truth.TruthItem`.
- Produces: `iou(a: BBox, b: BBox) -> float`, `MIN_IOU: float = 0.5`, `MatchResult` (dataclass: `matched: list[tuple[TruthItem, dict]]`, `unmatched_truth: list[TruthItem]`, `unmatched_actual: list[dict]`), `match_entities(truth: list[TruthItem], actual: list[dict], min_iou: float = MIN_IOU) -> MatchResult`. `actual` items are raw `final_entities.json` entity dicts with `entity_type` and `bbox` keys. Task 7 consumes `match_entities`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_matching.py
"""Ground truth is matched to output geometrically.

Entity ids (door_0015) are ordinal and shift whenever detection changes, so
matching is by type + IoU. 0.5 is loose enough to survive the few-pixel drift a
tuning change causes and tight enough that two adjacent doors never swap.
"""
import unittest

from regression.ground_truth import TruthItem
from regression.matching import MIN_IOU, iou, match_entities


def entity(kind, bbox, eid="e0"):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": 0.9, "attributes": {}}


class IouTests(unittest.TestCase):
    def test_identical_boxes_score_one(self):
        self.assertAlmostEqual(iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)

    def test_disjoint_boxes_score_zero(self):
        self.assertEqual(iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)

    def test_edge_touching_boxes_score_zero(self):
        self.assertEqual(iou((0, 0, 10, 10), (10, 0, 20, 10)), 0.0)

    def test_half_overlap_scores_one_third(self):
        self.assertAlmostEqual(iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)

    def test_zero_area_boxes_do_not_divide_by_zero(self):
        self.assertEqual(iou((5, 5, 5, 5), (0, 0, 10, 10)), 0.0)


class MatchTests(unittest.TestCase):
    def test_a_drifted_box_still_matches(self):
        truth = [TruthItem("door", (100, 100, 140, 140))]
        actual = [entity("door", (102, 101, 142, 141))]
        result = match_entities(truth, actual)
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(result.unmatched_truth, [])

    def test_a_different_type_never_matches(self):
        truth = [TruthItem("door", (100, 100, 140, 140))]
        result = match_entities(truth, [entity("window", (100, 100, 140, 140))])
        self.assertEqual(len(result.unmatched_truth), 1)
        self.assertEqual(len(result.unmatched_actual), 1)

    def test_a_vanished_detection_is_unmatched_truth(self):
        result = match_entities([TruthItem("door", (0, 0, 10, 10))], [])
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_a_new_detection_is_unmatched_actual(self):
        result = match_entities([], [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(result.unmatched_actual), 1)

    def test_below_threshold_overlap_does_not_match(self):
        truth = [TruthItem("door", (0, 0, 10, 10))]
        result = match_entities(truth, [entity("door", (7, 0, 17, 10))])
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_each_entity_is_claimed_once(self):
        truth = [TruthItem("door", (0, 0, 10, 10)), TruthItem("door", (1, 1, 11, 11))]
        result = match_entities(truth, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_the_best_overlap_wins_not_the_first(self):
        truth = [TruthItem("door", (0, 0, 10, 10))]
        actual = [entity("door", (4, 0, 14, 10), "far"), entity("door", (1, 0, 11, 10), "near")]
        result = match_entities(truth, actual)
        self.assertEqual(result.matched[0][1]["entity_id"], "near")

    def test_the_default_threshold_is_one_half(self):
        self.assertEqual(MIN_IOU, 0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_matching -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'regression.matching'`

- [ ] **Step 3: Write the implementation**

```python
# regression/matching.py
"""Matching ground-truth items to pipeline output.

Entity ids are ordinal — door_0015 becomes door_0014 the moment an earlier
door stops being detected — so nothing may key on them. Matching is by
entity type plus intersection-over-union, greedily, best pair first, each
side claimed once.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from regression.ground_truth import TruthItem

MIN_IOU = 0.5

BBox = tuple[float, float, float, float]


def iou(a: BBox, b: BBox) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


@dataclass
class MatchResult:
    matched: list[tuple[TruthItem, dict]] = field(default_factory=list)
    unmatched_truth: list[TruthItem] = field(default_factory=list)
    unmatched_actual: list[dict] = field(default_factory=list)


def match_entities(truth: list[TruthItem], actual: list[dict],
                   min_iou: float = MIN_IOU) -> MatchResult:
    pairs = []
    for t_idx, item in enumerate(truth):
        for a_idx, ent in enumerate(actual):
            if ent.get("entity_type") != item.type:
                continue
            score = iou(item.bbox, tuple(ent["bbox"]))
            if score >= min_iou:
                pairs.append((score, t_idx, a_idx))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    result = MatchResult()
    claimed_truth: set[int] = set()
    claimed_actual: set[int] = set()
    for _score, t_idx, a_idx in pairs:
        if t_idx in claimed_truth or a_idx in claimed_actual:
            continue
        claimed_truth.add(t_idx)
        claimed_actual.add(a_idx)
        result.matched.append((truth[t_idx], actual[a_idx]))
    result.unmatched_truth = [t for i, t in enumerate(truth) if i not in claimed_truth]
    result.unmatched_actual = [a for i, a in enumerate(actual) if i not in claimed_actual]
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_matching -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add regression/matching.py regression/__init__.py tests/test_matching.py
git commit -m "feat: geometric matching of ground truth to pipeline output"
```

---

### Task 7: The sweep and its report

**Files:**
- Create: `regression/sweep.py`, `regression/report.py`, `tools/regress.py`
- Test: `tests/test_regress_report.py`

**Interfaces:**
- Consumes: `regression.corpus` (`manifest_sheets`, `sheet_path`, `sheet_entry`, `sha256_of`), `regression.ground_truth.load_truth`, `regression.matching.match_entities`, `pipeline.run_extract`.
- Produces: `regression/report.py` → `SheetResult` (dataclass: `slug`, `status: str` one of `"ok" | "regression" | "missing" | "sha_mismatch" | "unlabeled"`, `lost: list[TruthItem]`, `returned_fps: list[TruthItem]`, `unreviewed: list[dict]`, `closed_deferred: list[TruthItem]`, `counts: dict[str, tuple[int, int]]`, `region_cache_miss: bool`), `EXIT_OK = 0`, `EXIT_REGRESSION = 1`, `EXIT_INCOMPLETE = 2`, `render(results: list[SheetResult]) -> str`, `exit_code(results: list[SheetResult]) -> int`. `regression/sweep.py` → `evaluate_page(truth_page, entities) -> dict`, `sweep(slugs: list[str] | None = None) -> list[SheetResult]`.

- [ ] **Step 1: Write the failing test**

The report and the per-page evaluation are tested against synthetic entity dicts; the pipeline is not run in the unit tier.

```python
# tests/test_regress_report.py
"""Report shaping and exit codes.

The sweep itself (which runs the pipeline over real sheets) is exercised by
running tools/regress.py; these tests pin the decision logic, which is where
the exit-code contract lives.
"""
import unittest

from regression.ground_truth import PageTruth, TruthItem
from regression.report import (
    EXIT_INCOMPLETE, EXIT_OK, EXIT_REGRESSION, SheetResult, exit_code, render,
)
from regression.sweep import evaluate_page


def entity(kind, bbox, eid="e0"):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": 0.9, "attributes": {}}


class EvaluatePageTests(unittest.TestCase):
    def test_a_still_detected_confirmed_entity_is_not_lost(self):
        page = PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(out["lost"], [])
        self.assertEqual(out["counts"]["door"], (1, 1))

    def test_a_vanished_confirmed_entity_is_lost(self):
        page = PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(len(out["lost"]), 1)

    def test_a_known_false_positive_that_stays_rejected_is_clean(self):
        page = PageTruth(false_positives=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(out["returned_fps"], [])

    def test_a_known_false_positive_promoted_to_an_entity_is_a_regression(self):
        page = PageTruth(false_positives=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(len(out["returned_fps"]), 1)

    def test_an_entity_matching_no_verdict_is_unreviewed(self):
        out = evaluate_page(PageTruth(), [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(out["unreviewed"]), 1)

    def test_a_deferred_gap_that_now_detects_is_reported_closed(self):
        page = PageTruth(deferred=[TruthItem("room", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(out["closed_deferred"]), 1)
        self.assertEqual(out["unreviewed"], [],
                         "a closed gap is not also an unreviewed detection")

    def test_a_still_open_deferred_gap_reports_nothing(self):
        page = PageTruth(deferred=[TruthItem("room", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(out["closed_deferred"], [])


class ExitCodeTests(unittest.TestCase):
    def test_a_clean_sweep_exits_zero(self):
        self.assertEqual(exit_code([SheetResult(slug="s01", status="ok")]), EXIT_OK)

    def test_unreviewed_detections_do_not_fail_the_sweep(self):
        r = SheetResult(slug="s01", status="ok",
                        unreviewed=[entity("door", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_OK)

    def test_a_closed_gap_does_not_fail_the_sweep(self):
        r = SheetResult(slug="s01", status="ok",
                        closed_deferred=[TruthItem("room", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_OK)

    def test_a_lost_confirmed_entity_exits_one(self):
        r = SheetResult(slug="s01", status="regression",
                        lost=[TruthItem("door", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_REGRESSION)

    def test_a_sha_mismatch_exits_one(self):
        self.assertEqual(exit_code([SheetResult(slug="s07", status="sha_mismatch")]),
                         EXIT_REGRESSION)

    def test_a_missing_sheet_exits_two(self):
        self.assertEqual(exit_code([SheetResult(slug="s14", status="missing")]),
                         EXIT_INCOMPLETE)

    def test_a_regression_outranks_a_missing_sheet(self):
        results = [SheetResult(slug="s14", status="missing"),
                   SheetResult(slug="s01", status="regression",
                               lost=[TruthItem("door", (0, 0, 10, 10))])]
        self.assertEqual(exit_code(results), EXIT_REGRESSION)


class RenderTests(unittest.TestCase):
    def test_a_lost_entity_is_named_with_its_centre(self):
        r = SheetResult(slug="s01", status="regression",
                        lost=[TruthItem("door", (800, 430, 824, 450))])
        text = render([r])
        self.assertIn("LOST door", text)
        self.assertIn("812", text)

    def test_an_unlabeled_sheet_says_so(self):
        text = render([SheetResult(slug="s09", status="unlabeled",
                                   unreviewed=[entity("door", (0, 0, 10, 10))])])
        self.assertIn("unlabeled", text)

    def test_a_region_cache_miss_is_surfaced(self):
        text = render([SheetResult(slug="s07", status="ok", region_cache_miss=True)])
        self.assertIn("REGION CACHE MISS", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_regress_report -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'regression.report'`

- [ ] **Step 3: Write the report module**

```python
# regression/report.py
"""Sweep results, their rendering, and the exit-code contract.

Exit codes:
  0  clean, or REVIEW items only (new detections, closed gaps)
  1  a regression: a confirmed entity vanished, a known false positive came
     back, or a sheet's bytes no longer match the manifest
  2  the corpus is incomplete — some manifest sheets are not downloaded

New detections never fail the sweep. Improving detection must not turn the
suite red; it queues review instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from regression.ground_truth import TruthItem

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_INCOMPLETE = 2


@dataclass
class SheetResult:
    slug: str
    status: str = "ok"
    lost: list[TruthItem] = field(default_factory=list)
    returned_fps: list[TruthItem] = field(default_factory=list)
    unreviewed: list[dict] = field(default_factory=list)
    closed_deferred: list[TruthItem] = field(default_factory=list)
    counts: dict[str, tuple[int, int]] = field(default_factory=dict)
    region_cache_miss: bool = False

    @property
    def is_regression(self) -> bool:
        return bool(self.lost or self.returned_fps) or self.status == "sha_mismatch"


def _centre(bbox) -> str:
    return f"({round((bbox[0] + bbox[2]) / 2)},{round((bbox[1] + bbox[3]) / 2)})"


def render(results: list[SheetResult]) -> str:
    lines = []
    for r in results:
        if r.status == "missing":
            lines.append(f"{r.slug}  SKIPPED — not downloaded")
            continue
        if r.status == "sha_mismatch":
            lines.append(f"{r.slug}  ✗ content changed since ground truth was recorded")
            continue
        counts = "  ".join(f"{kind} {found}/{total}"
                           for kind, (found, total) in sorted(r.counts.items()))
        tail = []
        if r.unreviewed:
            tail.append(f"unreviewed {len(r.unreviewed)}")
        if r.closed_deferred:
            tail.append(f"gaps CLOSED {len(r.closed_deferred)}")
        if r.status == "unlabeled":
            tail.append("unlabeled — every detection is unreviewed")
        lines.append(f"{r.slug}  {counts}  {'  '.join(tail)}".rstrip())
        for item in r.lost:
            lines.append(f"    ✗ LOST {item.type} @ {_centre(item.bbox)}"
                         f"{'  ' + item.note if item.note else ''}")
        for item in r.returned_fps:
            lines.append(f"    ✗ FALSE POSITIVE RETURNED {item.type} @ {_centre(item.bbox)}"
                         f"{'  ' + item.note if item.note else ''}")
        for item in r.closed_deferred:
            lines.append(f"    REVIEW gap closed: {item.type} @ {_centre(item.bbox)} — "
                         f"confirm it, then promote it to `confirmed`")
        for ent in r.unreviewed:
            lines.append(f"    REVIEW new {ent['entity_type']} @ {_centre(ent['bbox'])} "
                         f"conf {ent.get('confidence', 0):.2f}")
        if r.region_cache_miss:
            lines.append("    REGION CACHE MISS — classification fell back to the whole "
                         "page; detection scope differs from the labeled run")
    return "\n".join(lines)


def exit_code(results: list[SheetResult]) -> int:
    if any(r.is_regression for r in results):
        return EXIT_REGRESSION
    if any(r.status == "missing" for r in results):
        return EXIT_INCOMPLETE
    return EXIT_OK
```

- [ ] **Step 4: Write the sweep module**

```python
# regression/sweep.py
"""Run the pipeline over corpus sheets and score the output.

Sheets are extracted with skip_gemini=True: the region-classification cache
ships with the bundle, so a sweep is offline and deterministic. A cache miss
means detection ran over the whole page instead of the floor-plan regions —
which changes what is detected — so it is surfaced per sheet.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pipeline import run_extract
from regression.corpus import manifest_sheets, sha256_of, sheet_entry, sheet_path
from regression.ground_truth import PageTruth, load_truth
from regression.matching import match_entities
from regression.report import SheetResult


def evaluate_page(truth_page: PageTruth, entities: list[dict]) -> dict:
    """Score one page's entities against its three verdict lists."""
    confirmed = match_entities(truth_page.confirmed, entities)
    remaining = confirmed.unmatched_actual

    fps = match_entities(truth_page.false_positives, remaining)
    remaining = fps.unmatched_actual

    gaps = match_entities(truth_page.deferred, remaining)
    remaining = gaps.unmatched_actual

    counts: dict[str, tuple[int, int]] = {}
    for item in truth_page.confirmed:
        found, total = counts.get(item.type, (0, 0))
        counts[item.type] = (found, total + 1)
    for item, _ent in confirmed.matched:
        found, total = counts[item.type]
        counts[item.type] = (found + 1, total)

    return {
        "lost": confirmed.unmatched_truth,
        "returned_fps": [t for t, _ in fps.matched],
        "closed_deferred": [t for t, _ in gaps.matched],
        "unreviewed": remaining,
        "counts": counts,
    }


def _entities_by_page(run_dir: str) -> dict[int, list[dict]]:
    pages: dict[int, list[dict]] = {}
    for path in sorted(Path(run_dir).glob("pages/page_*/final_entities.json")):
        number = int(path.parent.name.split("_")[1])
        pages[number] = json.loads(path.read_text(encoding="utf-8")).get("entities", [])
    return pages


def _cache_missed(run_dir: str) -> bool:
    warnings_path = Path(run_dir) / "warnings.json"
    if not warnings_path.exists():
        return False
    payload = json.loads(warnings_path.read_text(encoding="utf-8"))
    codes = {w.get("warning_code") for w in payload}
    return "REGION_CACHE_MISS_OFFLINE" in codes


def sweep(slugs: list[str] | None = None) -> list[SheetResult]:
    wanted = slugs or [s["slug"] for s in manifest_sheets()
                       if s.get("tier") != "retired"]
    results: list[SheetResult] = []
    for slug in wanted:
        entry = sheet_entry(slug)
        if entry is None:
            results.append(SheetResult(slug=slug, status="missing"))
            continue
        path = sheet_path(slug)
        if path is None:
            results.append(SheetResult(slug=slug, status="missing"))
            continue
        if sha256_of(path) != entry["sha256"]:
            results.append(SheetResult(slug=slug, status="sha_mismatch"))
            continue

        truth = load_truth(slug)
        with tempfile.TemporaryDirectory() as out_parent:
            run_dir = run_extract(str(path), list(range(entry["pages"])),
                                  out_parent=out_parent, skip_gemini=True)
            pages = _entities_by_page(run_dir)
            cache_miss = _cache_missed(run_dir)

        result = SheetResult(slug=slug,
                             status="unlabeled" if not truth.is_labeled else "ok",
                             region_cache_miss=cache_miss)
        for number, entities in sorted(pages.items()):
            scored = evaluate_page(truth.page(number), entities)
            result.lost += scored["lost"]
            result.returned_fps += scored["returned_fps"]
            result.closed_deferred += scored["closed_deferred"]
            result.unreviewed += scored["unreviewed"]
            for kind, (found, total) in scored["counts"].items():
                prev_found, prev_total = result.counts.get(kind, (0, 0))
                result.counts[kind] = (prev_found + found, prev_total + total)
        if result.is_regression:
            result.status = "regression"
        results.append(result)
    return results
```

- [ ] **Step 5: Write the CLI**

```python
#!/usr/bin/env python3
# tools/regress.py
"""Run the regression corpus and diff it against the committed ground truth.

Usage:
    python tools/regress.py               # every non-retired manifest sheet
    python tools/regress.py --sheet s07   # one or more slugs
    python tools/regress.py --json        # machine-readable results

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
    args = parser.parse_args()

    results = sweep(args.sheets)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))
    else:
        print(render(results))
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_regress_report -v`
Expected: PASS, 17 tests

- [ ] **Step 7: Run the real sweep**

```bash
source .venv/bin/activate && time python tools/regress.py; echo "exit=$?"
```

Expected: every sheet reports `unlabeled — every detection is unreviewed` (no ground truth exists yet), `exit=0`, total runtime 2–4 minutes. If any sheet errors, fix the sweep before continuing — an unhandled exception on one sheet must not be reported as a clean run.

- [ ] **Step 8: Commit**

```bash
git add regression/report.py regression/sweep.py tools/regress.py tests/test_regress_report.py
git commit -m "feat: regression sweep over the corpus with ground-truth diffing"
```

---

### Task 8: Ground-truth hygiene guard

**Files:**
- Create: `tests/test_ground_truth_hygiene.py`

**Interfaces:**
- Consumes: `regression.ground_truth.TRUTH_DIR`.
- Produces: nothing importable — this is a guard test over the committed files.

- [ ] **Step 1: Write the test**

It passes trivially today (no ground-truth files exist) and starts biting in Task 10. Both a synthetic case and the real files are checked, so the rules are proven to work rather than merely vacuous.

```python
# tests/test_ground_truth_hygiene.py
"""Committed ground truth must not carry property-identifying text.

Ground truth records geometry. Sheet text is copied only into `tag`, and only
when it is a drawing tag (W11, GD9, D05). Room names, title blocks and schedule
contents are never copied, because they carry addresses — and the sheets are
NDA-covered even though their bboxes are not.
"""
import json
import re
import unittest

from regression.ground_truth import TRUTH_DIR

TAG_RE = re.compile(r"^[A-Z]{0,4}\d{1,3}[A-Z]?$")
POSTCODE_RE = re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}\b")
STREET_RE = re.compile(
    r"\b\d+[a-z]?\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s+"
    r"(street|road|lane|avenue|close|drive|way|crescent|terrace|court|place)\b",
    re.IGNORECASE)
MAX_LEN = {"note": 300}
DEFAULT_MAX_LEN = 60


def _strings(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


class HygieneRuleTests(unittest.TestCase):
    """The rules catch what they claim to catch."""

    def test_a_postcode_is_caught(self):
        self.assertTrue(POSTCODE_RE.search("site at SW1A 1AA today"))

    def test_a_street_address_is_caught(self):
        self.assertTrue(STREET_RE.search("14 Bramble Road"))

    def test_ordinary_prose_is_not_caught(self):
        for phrase in ("the leaf is drawn closed in the wall plane",
                       "the doorway tongue was pinched",
                       "a 45deg bay wall pairs at wall spacing"):
            self.assertIsNone(STREET_RE.search(phrase), phrase)
            self.assertIsNone(POSTCODE_RE.search(phrase), phrase)

    def test_drawing_tags_match_the_tag_pattern(self):
        for tag in ("W11", "GD9", "D05", "W8"):
            self.assertTrue(TAG_RE.match(tag), tag)

    def test_a_room_name_does_not_match_the_tag_pattern(self):
        for text in ("FAMILY BATH", "KITCHEN/DINER", "Flat 2"):
            self.assertFalse(TAG_RE.match(text), text)


class CommittedGroundTruthTests(unittest.TestCase):
    """Every committed ground-truth file obeys the rules."""

    def setUp(self):
        self.files = sorted(TRUTH_DIR.glob("*.json")) if TRUTH_DIR.is_dir() else []

    def test_every_string_is_free_of_addresses(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                self.assertIsNone(POSTCODE_RE.search(text),
                                  f"{path.name} {where}: postcode-like text {text!r}")
                self.assertIsNone(STREET_RE.search(text),
                                  f"{path.name} {where}: address-like text {text!r}")

    def test_every_string_is_within_its_length_budget(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                field = where.rsplit(".", 1)[-1]
                limit = MAX_LEN.get(field, DEFAULT_MAX_LEN)
                self.assertLessEqual(len(text), limit,
                                     f"{path.name} {where}: {len(text)} chars > {limit}")

    def test_every_tag_is_a_drawing_tag(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                if where.rsplit(".", 1)[-1] == "tag":
                    self.assertTrue(TAG_RE.match(text),
                                    f"{path.name} {where}: {text!r} is not a drawing tag")
```

- [ ] **Step 2: Run the test**

Run: `source .venv/bin/activate && python -m unittest tests.test_ground_truth_hygiene -v`
Expected: PASS, 8 tests

- [ ] **Step 3: Prove the guard bites**

Temporarily create `tests/ground_truth/s99.json` containing `{"sheet":"s99","pages":{"1":{"confirmed":[{"type":"door","bbox":[0,0,1,1],"tag":"KITCHEN","note":"at 14 Bramble Road"}]}}}`, re-run, and confirm two failures (`tag` and address). Then delete the file and re-run to confirm PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ground_truth_hygiene.py
git commit -m "test: guard committed ground truth against address-bearing text"
```

---

### Task 9: Adopt new sheets

**Files:**
- Create: `tools/add_sheet.py`
- Test: `tests/test_add_sheet.py`

**Interfaces:**
- Consumes: `regression.corpus` (`SHEETS_DIR`, `MANIFEST_PATH`, `load_manifest`, `manifest_sheets`, `sha256_of`), `regression.ground_truth.write_empty_truth`.
- Produces: `next_slug(sheets: list[dict]) -> str`, `adopt(source: Path, desc: str) -> dict` returning the new manifest entry, raising `ValueError` when the sha is already in the corpus.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_add_sheet.py
"""Adopting a new sheet into the corpus."""
import json
import tempfile
import unittest
from pathlib import Path

import fitz

import regression.corpus as fx
import regression.ground_truth as gt
from tools.add_sheet import adopt, next_slug


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=200, height=400)
    page.insert_text((20, 40), text)
    doc.save(str(path))
    doc.close()


class NextSlugTests(unittest.TestCase):
    def test_an_empty_corpus_starts_at_s01(self):
        self.assertEqual(next_slug([]), "s01")

    def test_the_next_slug_follows_the_highest_in_use(self):
        self.assertEqual(next_slug([{"slug": "s01"}, {"slug": "s20"}]), "s21")

    def test_gaps_are_not_reused(self):
        self.assertEqual(next_slug([{"slug": "s01"}, {"slug": "s03"}]), "s04")


class AdoptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "truth").mkdir()
        (root / "MANIFEST.json").write_text(json.dumps({"storage": "the bundle",
                                                        "sheets": []}))
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH, gt.TRUTH_DIR)
        fx.FIXTURES_DIR, fx.SHEETS_DIR = root, root / "sheets"
        fx.MANIFEST_PATH, gt.TRUTH_DIR = root / "MANIFEST.json", root / "truth"
        self.incoming = root / "incoming.pdf"
        make_pdf(self.incoming, "a new sheet")

    def tearDown(self):
        (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH, gt.TRUTH_DIR) = self._saved
        self.tmp.cleanup()

    def test_the_file_is_renamed_to_its_slug(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        self.assertEqual(entry["file"], "s01-existing-floor-plans.pdf")
        self.assertTrue((fx.SHEETS_DIR / entry["file"]).exists())

    def test_the_manifest_records_sha_and_page_count(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        self.assertEqual(entry["pages"], 1)
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(fx.manifest_sheets()[0]["slug"], "s01")

    def test_an_empty_ground_truth_file_is_created(self):
        adopt(self.incoming, "existing-floor-plans")
        self.assertFalse(gt.load_truth("s01").is_labeled)

    def test_a_new_sheet_is_tier_corpus(self):
        self.assertEqual(adopt(self.incoming, "existing-floor-plans")["tier"], "corpus")

    def test_re_adopting_the_same_bytes_is_refused(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        # Same bytes arriving under a different path — the sha dedupe must catch it.
        again = fx.FIXTURES_DIR / "again.pdf"
        again.write_bytes((fx.SHEETS_DIR / entry["file"]).read_bytes())
        with self.assertRaises(ValueError) as ctx:
            adopt(again, "duplicate")
        self.assertIn("s01", str(ctx.exception))

    def test_a_description_with_spaces_is_kebab_cased(self):
        entry = adopt(self.incoming, "Existing Floor Plans")
        self.assertEqual(entry["file"], "s01-existing-floor-plans.pdf")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_add_sheet -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.add_sheet'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
# tools/add_sheet.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && python -m unittest tests.test_add_sheet -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Run the whole suite**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: OK. The count is now roughly 432 + 69 new tests; runtime still under 15 seconds.

- [ ] **Step 6: Commit**

```bash
git add tools/add_sheet.py tests/test_add_sheet.py
git commit -m "feat: adopt new sheets into the regression corpus"
```

---

### Task 10: Seed s01 ground truth and document the labeling loop

**Files:**
- Create: `tests/ground_truth/s01.json`
- Modify: `CLAUDE.md` (a "Regression testing" section), `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: the first labeled sheet, and the written procedure the next session follows.

- [ ] **Step 1: Seed s01's windows from the ground truth that already exists**

`tests/test_window_detection.py::TestFloorPlansRegression` already carries user-established truth for s01: exactly four windows at centres (958, 850), (895, 903), (1103, 1387), (941, 1387), and four documented false-positive centres (980, 783), (1053, 812), (980, 936), (1004, 1118). Convert them to bboxes by running the sweep and reading the actual boxes:

```bash
source .venv/bin/activate && python tools/regress.py --sheet s01 --json > /tmp/s01.json
```

Write `tests/ground_truth/s01.json` with `reviewed: "<today>"`, the four window entities' real bboxes under `confirmed`, and — only if the sweep emits them as entities — the four FP centres under `false_positives`. A false positive the pipeline already rejects does **not** belong in the file: `evaluate_page` matches `false_positives` against emitted entities only, so recording a rejected one is inert.

- [ ] **Step 2: Verify the seeded sheet scores clean**

```bash
source .venv/bin/activate && python tools/regress.py --sheet s01; echo "exit=$?"
```

Expected: `s01  window 4/4  unreviewed N` and `exit=0`, where N is the doors/rooms/labels/schedules not yet verdicted. Then break it on purpose: change one confirmed bbox to `[0, 0, 1, 1]`, re-run, confirm `✗ LOST window` and `exit=1`, and restore the file.

- [ ] **Step 3: Run the hygiene guard against the real file**

Run: `source .venv/bin/activate && python -m unittest tests.test_ground_truth_hygiene -v`
Expected: PASS — the seeded file must satisfy the tag and length rules.

- [ ] **Step 4: Document the loop in `CLAUDE.md`**

Add after the "Commands" section:

````markdown
## Regression testing

Two tiers:

```bash
python -m unittest discover tests   # ~10s — synthetic topologies, run constantly
python tools/regress.py             # ~3min — 20 real sheets vs. committed ground truth
```

The corpus lives in `fixtures/sheets/` and is **not** committed (NDA). Download
the bundle — location in `fixtures/MANIFEST.json` — and verify with
`python tools/fetch_fixtures.py`. Sheets are named by slug (`s01`…`s20`); the
two primary references are `s01` (formerly floor-plans.pdf) and `s02` (the WD03
working drawing).

`tests/ground_truth/sNN.json` holds the user's verdicts and is committed. Three
lists per page: `confirmed` (correct detections), `false_positives` (wrong
detections, matched against emitted entities only), and `deferred` (misses the
user reported that we consciously chose not to fix). Matching is geometric —
type + IoU ≥ 0.5 — because entity ids are ordinal and shift when detection
changes.

`regress.py` exits 1 on a lost `confirmed` entity, a returned false positive, or
a sheet whose bytes no longer match the manifest; 2 when sheets are missing from
disk; 0 otherwise. **New detections never fail the sweep** — they print under
REVIEW and wait for a verdict.

The loop when tuning detection:

1. `python tools/regress.py`
2. The user opens `debug_viewer.html` and reports path indices of misses and
   false positives.
3. Record the verdicts in `tests/ground_truth/sNN.json` — a data commit.
4. Fix the algorithm, and pin the topology with a synthetic test in the fast tier.
5. `regress.py` again: no lost `confirmed`, no returned false positives. A
   `deferred` entry that flips to CLOSED is confirmed by the user, then promoted
   to `confirmed`.

A revised drawing is adopted as a **new** slug (`python tools/add_sheet.py`),
never dropped over an existing one — an existing slug's bytes are immutable
because its ground truth is pinned to them.
````

- [ ] **Step 5: Run the full suite and commit**

```bash
source .venv/bin/activate && python -m unittest discover tests
git add tests/ground_truth/s01.json CLAUDE.md README.md
git commit -m "test: seed s01 ground truth and document the regression loop"
```

- [ ] **Step 6: Hand the corpus back to the user**

Report: s01's windows are seeded; doors, rooms, labels and schedules on s01 and everything on s02–s20 are unreviewed. Ask which sheet to label first, and run `python tools/regress.py --sheet <slug>` so they can work through it in the debug viewer.

---

## Phase 3 — corpus labeling (not a task)

Labeling is interactive and open-ended: one sheet at a time, driven by the user's
review in `debug_viewer.html`. Each labeling session is a data commit to
`tests/ground_truth/sNN.json` plus, where a fix follows, an algorithm change with
its own synthetic test. There is no end state to plan for — a sheet becomes a
gate the moment its first verdict lands.
