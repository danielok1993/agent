"""Persistence of a user-supplied scale.

Two back-ends, mirroring the split the repo already uses for verdicts versus
caches: a corpus sheet writes into its committed ground truth, anything else
into a gitignored sidecar. Both are read before the user is ever prompted.
"""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as corpus
import regression.ground_truth as gt
from regression.ground_truth import SheetTruth, dumps_truth, load_truth
from scale.store import StoredScale, load_stored, match_stored, save_stored


class TestGroundTruthCarriesScales(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = gt.TRUTH_DIR
        gt.TRUTH_DIR = Path(self.tmp.name)

    def tearDown(self):
        gt.TRUTH_DIR = self._saved
        self.tmp.cleanup()

    def test_scales_survive_a_load_dump_round_trip(self):
        (gt.TRUTH_DIR / "s09.json").write_text(json.dumps({
            "sheet": "s09", "pdf_sha256": "abc", "reviewed": None,
            "scales": {"1": [{"bbox": [10.0, 20.0, 30.0, 40.0],
                              "scale": "1:100"}]},
            "pages": {},
        }, indent=2) + "\n", encoding="utf-8")
        truth = load_truth("s09")
        self.assertEqual(truth.scales,
                         {1: [{"bbox": [10.0, 20.0, 30.0, 40.0],
                               "scale": "1:100"}]})
        self.assertIn("1:100", dumps_truth(truth))

    def test_a_stored_bbox_stays_on_one_line_in_the_diff(self):
        truth = SheetTruth(slug="s09", pdf_sha256="abc", scales={
            1: [{"bbox": [10.0, 20.0, 30.0, 40.0], "scale": "1:100"}]})
        self.assertIn("[10.0, 20.0, 30.0, 40.0]", dumps_truth(truth))

    def test_a_sheet_without_scales_round_trips_byte_identically(self):
        original = json.dumps({
            "sheet": "s01", "pdf_sha256": "abc", "reviewed": None, "pages": {},
        }, indent=2) + "\n"
        (gt.TRUTH_DIR / "s01.json").write_text(original, encoding="utf-8")
        self.assertEqual(dumps_truth(load_truth("s01")), original)

    def test_empty_scales_block_is_omitted_from_output(self):
        truth = SheetTruth(slug="s01", pdf_sha256="abc")
        self.assertNotIn("scales", dumps_truth(truth))


class TestSlugForPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "sheets" / "s09-floor-plan.pdf").write_bytes(b"%PDF-1.4")
        (root / "MANIFEST.json").write_text(json.dumps(
            {"sheets": [{"slug": "s09", "file": "s09-floor-plan.pdf"}]}),
            encoding="utf-8")
        self._saved = (corpus.FIXTURES_DIR, corpus.SHEETS_DIR, corpus.MANIFEST_PATH)
        corpus.FIXTURES_DIR = root
        corpus.SHEETS_DIR = root / "sheets"
        corpus.MANIFEST_PATH = root / "MANIFEST.json"

    def tearDown(self):
        (corpus.FIXTURES_DIR, corpus.SHEETS_DIR,
         corpus.MANIFEST_PATH) = self._saved
        self.tmp.cleanup()

    def test_corpus_sheet_resolves_to_its_slug(self):
        path = corpus.SHEETS_DIR / "s09-floor-plan.pdf"
        self.assertEqual(corpus.slug_for_path(path), "s09")

    def test_outside_pdf_has_no_slug(self):
        self.assertIsNone(corpus.slug_for_path(Path(self.tmp.name) / "other.pdf"))


class TestLocalCacheBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pdf = Path(self.tmp.name) / "drawing.pdf"
        self.pdf.write_bytes(b"%PDF-1.4")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_cache_reads_as_empty(self):
        self.assertEqual(load_stored(str(self.pdf), 1), [])

    def test_saved_entries_read_back(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        found = load_stored(str(self.pdf), 1)
        self.assertEqual([(e.bbox, e.scale) for e in found],
                         [((0.0, 0.0, 10.0, 10.0), "1:50")])

    def test_pages_are_kept_apart(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 2, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:100")])
        self.assertEqual(load_stored(str(self.pdf), 1)[0].scale, "1:50")
        self.assertEqual(load_stored(str(self.pdf), 2)[0].scale, "1:100")

    def test_save_appends_a_disjoint_region(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 1, [StoredScale((50.0, 50.0, 60.0, 60.0), "1:100")])
        self.assertEqual(len(load_stored(str(self.pdf), 1)), 2)

    def test_save_replaces_an_overlapping_region_rather_than_duplicating(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.2, 10.2), "1:100")])
        found = load_stored(str(self.pdf), 1)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].scale, "1:100")

    def test_cache_lands_in_a_gitignored_sidecar_dir(self):
        save_stored(str(self.pdf), 1, [StoredScale((0.0, 0.0, 10.0, 10.0), "1:50")])
        self.assertTrue((self.pdf.parent / ".scale_cache").is_dir())

    def test_corrupt_cache_reads_as_empty_rather_than_raising(self):
        cache = self.pdf.parent / ".scale_cache"
        cache.mkdir()
        (cache / "drawing_p01.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(load_stored(str(self.pdf), 1), [])


class TestMatchStored(unittest.TestCase):
    """Matching is geometric because region ids are ordinal.

    layout/segmenter.py numbers regions region_0000, region_0001, ... over a
    sorted box list, so any change to segmentation renumbers them. A stored
    scale keyed by id would then attach to a different drawing and, since
    stored values sit at the top of the ladder, override the correct one.
    """

    def test_the_same_region_matches(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertEqual(match_stored((0.0, 0.0, 100.0, 100.0), stored).scale, "1:50")

    def test_a_slightly_shifted_region_still_matches(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNotNone(match_stored((2.0, 2.0, 102.0, 102.0), stored))

    def test_a_different_drawing_does_not_match(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNone(match_stored((500.0, 500.0, 600.0, 600.0), stored))

    def test_a_region_overlapping_below_the_threshold_does_not_match(self):
        # IoU 0.25 -- half-overlap in each axis. Renumbering must not be able
        # to smuggle a stale scale onto a neighbouring drawing.
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50")]
        self.assertIsNone(match_stored((50.0, 50.0, 150.0, 150.0), stored))

    def test_the_best_overlap_wins_when_several_could_match(self):
        stored = [StoredScale((0.0, 0.0, 100.0, 100.0), "1:50"),
                  StoredScale((0.0, 0.0, 104.0, 104.0), "1:100")]
        self.assertEqual(match_stored((0.0, 0.0, 103.0, 103.0), stored).scale,
                         "1:100")

    def test_an_empty_store_matches_nothing(self):
        self.assertIsNone(match_stored((0.0, 0.0, 100.0, 100.0), []))


if __name__ == "__main__":
    unittest.main()
