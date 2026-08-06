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
