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
from regression.sweep import score_sheet, sweep


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


if __name__ == "__main__":
    unittest.main()
