"""Sweep correctness that does not require running the real pipeline.

`regression.sweep.sweep()` short-circuits to a `sha_mismatch` SheetResult
before ever calling `run_extract` when the sheet's bytes don't match what's
expected, so that path is exercised directly against a synthetic corpus/truth
tree (the same monkeypatch pattern as test_fetch_fixtures.py). Per-page
scoring is exercised through `score_sheet`, which sweep() calls with the
run's already-materialized `pages` dict — so scoring correctness (including
unscored pages) is tested without invoking the pipeline either.
"""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as fx
import regression.ground_truth as gt
from regression.ground_truth import PageTruth, SheetTruth, TruthItem
from regression.sweep import (PRUNE_PAGE_ENTRIES, _labeled_but_unreviewed,
                              _prune_unread_page_output, score_sheet, sweep)


def entity(kind, bbox, eid="e0"):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": 0.9, "attributes": {}}


class ShaMismatchAgainstTruthTests(unittest.TestCase):
    """Fix: an operator who pastes a fresh hash into the manifest instead of
    adopting a new slug must not silently score stale verdicts against a
    drawing nobody reviewed. sweep() must catch truth.pdf_sha256 diverging
    from the manifest's sha256 BEFORE running the pipeline.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        self._saved_corpus = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = root
        fx.SHEETS_DIR = root / "sheets"
        fx.MANIFEST_PATH = root / "MANIFEST.json"
        self._saved_truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved_corpus
        gt.TRUTH_DIR = self._saved_truth_dir
        self.tmp.cleanup()

    def _write_sheet(self, name, data=b"%PDF-1.4 revised drawing"):
        path = fx.SHEETS_DIR / name
        path.write_bytes(data)
        return fx.sha256_of(path)

    def _write_manifest(self, sheets):
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": sheets}))

    def _write_truth(self, slug, pdf_sha256, reviewed="2026-08-01"):
        gt.TRUTH_DIR.mkdir(parents=True, exist_ok=True)
        (gt.TRUTH_DIR / f"{slug}.json").write_text(json.dumps(
            {"sheet": slug, "pdf_sha256": pdf_sha256, "reviewed": reviewed, "pages": {}}))

    def test_truth_sha_diverging_from_the_manifest_is_a_sha_mismatch(self):
        current_sha = self._write_sheet("s21-revised.pdf")
        self._write_manifest([{"slug": "s21", "file": "s21-revised.pdf",
                               "sha256": current_sha, "pages": 1, "tier": "corpus"}])
        # Ground truth was reviewed against a DIFFERENT sha than what the
        # manifest (and disk) now say — the operator repointed the manifest
        # at a revised file without relabeling.
        self._write_truth("s21", pdf_sha256="0" * 64)

        results = sweep(["s21"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "sha_mismatch")
        self.assertTrue(results[0].is_regression)

    def test_matching_truth_sha_is_not_a_mismatch_by_itself(self):
        # Confirms the new check does not false-positive: when truth and
        # manifest agree, sweep proceeds past the check (would go on to call
        # run_extract, which we don't exercise here — this only proves the
        # guard clause does not fire).
        current_sha = self._write_sheet("s22-clean.pdf")
        self._write_manifest([{"slug": "s22", "file": "s22-clean.pdf",
                               "sha256": current_sha, "pages": 1, "tier": "corpus"}])
        self._write_truth("s22", pdf_sha256=current_sha)

        truth = gt.load_truth("s22")
        entry = fx.sheet_entry("s22")
        self.assertFalse(truth.pdf_sha256 and truth.pdf_sha256 != entry["sha256"])

    def test_a_sheet_with_no_pdf_sha256_recorded_is_never_flagged(self):
        # write_empty_truth-style sheets (freshly adopted, never labeled) have
        # pdf_sha256 set but reviewed=None; a sheet with pdf_sha256 entirely
        # absent (e.g. hand-authored truth predating the field) must not be
        # treated as a mismatch just because the field is missing.
        current_sha = self._write_sheet("s23-unlabeled.pdf")
        self._write_manifest([{"slug": "s23", "file": "s23-unlabeled.pdf",
                               "sha256": current_sha, "pages": 1, "tier": "corpus"}])
        gt.TRUTH_DIR.mkdir(parents=True, exist_ok=True)
        (gt.TRUTH_DIR / "s23.json").write_text(json.dumps(
            {"sheet": "s23", "reviewed": None, "pages": {}}))

        truth = gt.load_truth("s23")
        entry = fx.sheet_entry("s23")
        self.assertIsNone(truth.pdf_sha256)
        self.assertFalse(bool(truth.pdf_sha256) and truth.pdf_sha256 != entry["sha256"])


class LabeledFlagTests(unittest.TestCase):
    """A `"labeled": true` manifest entry is a durable claim that a human has
    recorded verdicts for this sheet. If the ground truth file later vanishes
    (a forgotten commit, a stray `git rm`, a bad merge) or reverts to
    `reviewed: null`, that claim is now contradicted -- a regression-class
    failure, not a silent "unlabeled" line among 19 clean ones.

    The `_labeled_but_unreviewed` cases run entirely against synthetic
    SheetTruth/entry values (no I/O, no pipeline). The two sweep()-level
    cases below it use the same temp-dir monkeypatch as
    ShaMismatchAgainstTruthTests, and are safe to run end-to-end because
    both hit `continue` in sweep() before `run_extract` is ever called.
    """

    def test_flag_set_and_truth_reviewed_is_clean(self):
        entry = {"slug": "s01", "labeled": True}
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        self.assertFalse(_labeled_but_unreviewed(entry, truth))

    def test_flag_set_and_truth_missing_is_flagged(self):
        # load_truth() for a sheet with no file on disk returns this exact
        # shape: SheetTruth(slug=slug) with reviewed defaulting to None.
        entry = {"slug": "s01", "labeled": True}
        truth = SheetTruth(slug="s01")
        self.assertTrue(_labeled_but_unreviewed(entry, truth))

    def test_flag_set_and_truth_present_but_reviewed_null_is_flagged(self):
        entry = {"slug": "s01", "labeled": True}
        truth = SheetTruth(slug="s01", reviewed=None)
        self.assertTrue(_labeled_but_unreviewed(entry, truth))

    def test_flag_absent_and_unlabeled_truth_is_unchanged_behaviour(self):
        entry = {"slug": "s09"}  # no "labeled" key at all
        truth = SheetTruth(slug="s09")
        self.assertFalse(_labeled_but_unreviewed(entry, truth))

    def test_flag_false_and_unlabeled_truth_is_unchanged_behaviour(self):
        entry = {"slug": "s09", "labeled": False}
        truth = SheetTruth(slug="s09")
        self.assertFalse(_labeled_but_unreviewed(entry, truth))


class LabeledFlagSweepIntegrationTests(unittest.TestCase):
    """End-to-end through sweep() for the two failing cases -- both exit via
    `continue` before `run_extract`, so no pipeline runs.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        self._saved_corpus = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = root
        fx.SHEETS_DIR = root / "sheets"
        fx.MANIFEST_PATH = root / "MANIFEST.json"
        self._saved_truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved_corpus
        gt.TRUTH_DIR = self._saved_truth_dir
        self.tmp.cleanup()

    def _write_sheet(self, name, data=b"%PDF-1.4 labeled sheet"):
        path = fx.SHEETS_DIR / name
        path.write_bytes(data)
        return fx.sha256_of(path)

    def test_a_labeled_sheet_with_no_ground_truth_file_fails_the_sweep(self):
        sha = self._write_sheet("s27-x.pdf")
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": [
            {"slug": "s27", "file": "s27-x.pdf", "sha256": sha,
             "pages": 1, "tier": "corpus", "labeled": True},
        ]}))
        # No tests/ground_truth/s27.json written at all.

        results = sweep(["s27"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "labeled_but_unreviewed")
        self.assertTrue(results[0].is_regression)

    def test_a_labeled_sheet_whose_truth_reverted_to_unreviewed_fails_the_sweep(self):
        sha = self._write_sheet("s28-x.pdf")
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": [
            {"slug": "s28", "file": "s28-x.pdf", "sha256": sha,
             "pages": 1, "tier": "corpus", "labeled": True},
        ]}))
        gt.TRUTH_DIR.mkdir(parents=True, exist_ok=True)
        (gt.TRUTH_DIR / "s28.json").write_text(json.dumps(
            {"sheet": "s28", "pdf_sha256": sha, "reviewed": None, "pages": {}}))

        results = sweep(["s28"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "labeled_but_unreviewed")
        self.assertTrue(results[0].is_regression)


class SweepSlugsArgumentTests(unittest.TestCase):
    """`slugs=[]` is a deliberate "sweep nothing" request and must stay
    empty -- `slugs or [...]` would treat it the same as `slugs=None`
    ("sweep everything"), which is not what an empty list means.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        self._saved_corpus = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = root
        fx.SHEETS_DIR = root / "sheets"
        fx.MANIFEST_PATH = root / "MANIFEST.json"
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": [
            {"slug": "s01", "file": "s01-x.pdf", "sha256": "0" * 64,
             "pages": 1, "tier": "corpus"},
        ]}))

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved_corpus
        self.tmp.cleanup()

    def test_an_explicit_empty_list_sweeps_nothing(self):
        self.assertEqual(sweep([]), [])

    def test_none_defaults_to_every_manifest_sheet(self):
        # s01's file is never written to disk in this synthetic corpus, so
        # this exercises the "missing" short-circuit rather than the
        # pipeline -- it only proves slugs=None reaches the manifest sheet
        # at all, which slugs=[] must not.
        results = sweep(None)
        self.assertEqual([r.slug for r in results], ["s01"])
        self.assertEqual(results[0].status, "missing")


class ScoreSheetUnscoredPagesTests(unittest.TestCase):
    """Fix: a page named in ground truth but absent from the run's output
    (hand-edited truth pointing at a page the sheet doesn't have, or a
    trimmed `pages` count) must fail the sweep, not silently score zero
    items on that page as if it were clean.
    """

    def test_a_ground_truth_page_missing_from_the_run_is_unscored(self):
        truth = SheetTruth(slug="s24", reviewed="2026-08-01", pages={
            1: PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))]),
            3: PageTruth(confirmed=[TruthItem("window", (0, 0, 10, 10))]),
        })
        # The run only produced output for page 1 (e.g. a 2-page sheet whose
        # truth file mislabels a "page 3" that doesn't exist).
        pages = {1: [entity("door", (0, 0, 10, 10))]}

        result = score_sheet("s24", truth, pages)

        self.assertEqual(result.unscored_pages, [3])
        self.assertTrue(result.is_regression)
        self.assertEqual(result.status, "regression")
        # Page 1 itself still scores clean.
        self.assertEqual(result.lost, [])

    def test_every_truth_page_present_in_the_run_has_no_unscored_pages(self):
        truth = SheetTruth(slug="s25", reviewed="2026-08-01", pages={
            1: PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))]),
        })
        pages = {1: [entity("door", (0, 0, 10, 10))]}

        result = score_sheet("s25", truth, pages)

        self.assertEqual(result.unscored_pages, [])
        self.assertFalse(result.is_regression)
        self.assertEqual(result.status, "ok")

    def test_a_run_page_with_no_ground_truth_is_not_unscored(self):
        # The reverse direction (run found an extra page truth never labeled)
        # is not a failure — only truth pages absent from the run are.
        truth = SheetTruth(slug="s26", reviewed="2026-08-01", pages={
            1: PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))]),
        })
        pages = {1: [entity("door", (0, 0, 10, 10))], 2: [entity("room", (0, 0, 5, 5))]}

        result = score_sheet("s26", truth, pages)

        self.assertEqual(result.unscored_pages, [])
        self.assertFalse(result.is_regression)


class UnreviewedByPageTests(unittest.TestCase):
    def _entity(self, entity_id, bbox):
        return {"entity_id": entity_id, "entity_type": "door",
                "bbox": list(bbox), "confidence": 0.8, "attributes": {}}

    def test_unreviewed_is_grouped_by_page(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))],
                 2: [self._entity("door_0002", (20, 20, 30, 30)),
                     self._entity("door_0003", (40, 40, 50, 50))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(sorted(result.unreviewed_by_page), [1, 2])
        self.assertEqual(len(result.unreviewed_by_page[1]), 1)
        self.assertEqual(len(result.unreviewed_by_page[2]), 2)

    def test_the_flat_unreviewed_list_still_holds_everything(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))],
                 2: [self._entity("door_0002", (20, 20, 30, 30))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(len(result.unreviewed), 2)

    def test_a_page_with_nothing_unreviewed_gets_no_entry(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        truth.pages[1] = PageTruth(confirmed=[
            TruthItem(type="door", bbox=(0.0, 0.0, 10.0, 10.0))])
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(result.unreviewed_by_page, {})


class PruneUnreadPageOutputTests(unittest.TestCase):
    """A fake run directory stands in for a real extraction (fast tier, no
    pipeline invoked): one page carrying every prunable entry plus every kept
    entry, so a single pass proves both that the unread files are gone and
    that nothing a human or later tooling reads was touched.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "2026-08-06_00-00-00"
        self.page_dir = self.run / "pages" / "page_01"
        self.page_dir.mkdir(parents=True)

        self.pruned_files = ["primitives.json", "candidates.json",
                             "pdfplumber_comparison.json", "regions.json"]
        self.pruned_dirs = ["region_crops"]
        self.kept_files = ["render.png", "overlay.png", "final_entities.json",
                           "review_door.png", "review_room.png"]

        for name in self.pruned_files + self.kept_files:
            (self.page_dir / name).write_text("x", encoding="utf-8")
        for name in self.pruned_dirs:
            d = self.page_dir / name
            d.mkdir()
            (d / "region_0.png").write_bytes(b"x")

        # Run-root files (sibling of pages/, not inside a page dir) must
        # survive untouched -- the prune list is page-level only.
        (self.run / "sweep_meta.json").write_text("{}", encoding="utf-8")
        (self.run / "warnings.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_prune_list_matches_what_the_function_deletes(self):
        # Documents the exact contract PRUNE_PAGE_ENTRIES commits to, so a
        # future edit to the constant is forced to update this test too.
        self.assertEqual(set(PRUNE_PAGE_ENTRIES),
                         set(self.pruned_files) | set(self.pruned_dirs))

    def test_prune_removes_the_unread_files_and_dirs(self):
        _prune_unread_page_output(self.run)

        for name in self.pruned_files:
            self.assertFalse((self.page_dir / name).exists(), name)
        for name in self.pruned_dirs:
            self.assertFalse((self.page_dir / name).exists(), name)

    def test_prune_preserves_everything_review_and_tooling_read(self):
        _prune_unread_page_output(self.run)

        for name in self.kept_files:
            self.assertTrue((self.page_dir / name).exists(), name)
        self.assertTrue((self.run / "sweep_meta.json").exists())
        self.assertTrue((self.run / "warnings.json").exists())

    def test_prune_is_safe_to_call_when_nothing_prunable_is_present(self):
        for name in self.pruned_files:
            (self.page_dir / name).unlink()
        for name in self.pruned_dirs:
            import shutil
            shutil.rmtree(self.page_dir / name)

        _prune_unread_page_output(self.run)  # must not raise

        for name in self.kept_files:
            self.assertTrue((self.page_dir / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
