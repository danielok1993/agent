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


class TruthWriteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._original = gt.TRUTH_DIR
        gt.TRUTH_DIR = Path(self._tmp.name)
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._original))

    def _write(self, slug, payload):
        (gt.TRUTH_DIR / f"{slug}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _write_raw(self, slug, text):
        (gt.TRUTH_DIR / f"{slug}.json").write_text(text, encoding="utf-8")

    def test_a_committed_style_file_round_trips_byte_identically(self):
        # Written in the exact shape the committed corpus uses: bbox arrays
        # stay on ONE line. json.dumps(indent=2) explodes them to one number
        # per line, so a fixture written with the same serializer under test
        # would pass while the real file churned 31 lines into 51. This
        # fixture is a literal on purpose.
        text = (
            '{\n'
            '  "sheet": "s01",\n'
            '  "pdf_sha256": "abc",\n'
            '  "reviewed": "2026-08-06",\n'
            '  "pages": {\n'
            '    "1": {\n'
            '      "confirmed": [\n'
            '        {\n'
            '          "type": "window",\n'
            '          "bbox": [954.7499338785808, 811.4999771118165, '
            '961.2499237060548, 888.4999593098959],\n'
            '          "note": "n"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  }\n'
            '}\n'
        )
        self._write_raw("s01", text)

        gt.dump_truth(gt.load_truth("s01"))

        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         text)

    def test_polygons_also_stay_on_one_line(self):
        text = (
            '{\n'
            '  "sheet": "s07",\n'
            '  "pdf_sha256": "abc",\n'
            '  "reviewed": "2026-08-06",\n'
            '  "pages": {\n'
            '    "1": {\n'
            '      "confirmed": [\n'
            '        {\n'
            '          "type": "room",\n'
            '          "bbox": [0.0, 0.0, 10.0, 10.0],\n'
            '          "polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], '
            '[0.0, 10.0]],\n'
            '          "shape": "partial"\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  }\n'
            '}\n'
        )
        self._write_raw("s07", text)

        gt.dump_truth(gt.load_truth("s07"))

        self.assertEqual((gt.TRUTH_DIR / "s07.json").read_text(encoding="utf-8"),
                         text)

    def test_dumping_is_idempotent(self):
        self._write("s08", {"sheet": "s08", "pdf_sha256": "x", "reviewed": None,
                            "pages": {"1": {"confirmed": [
                                {"type": "door", "bbox": [1.0, 2.0, 3.0, 4.0]}]}}})
        gt.dump_truth(gt.load_truth("s08"))
        once = (gt.TRUTH_DIR / "s08.json").read_text(encoding="utf-8")
        gt.dump_truth(gt.load_truth("s08"))
        self.assertEqual((gt.TRUTH_DIR / "s08.json").read_text(encoding="utf-8"),
                         once)

    def test_polygon_and_shape_round_trip(self):
        payload = {
            "sheet": "s02", "pdf_sha256": "def", "reviewed": "2026-08-06",
            "pages": {"1": {"confirmed": [{
                "type": "room", "bbox": [0.0, 0.0, 10.0, 10.0],
                "polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                "shape": "partial", "note": "misses the bay",
            }]}},
        }
        self._write("s02", payload)
        item = gt.load_truth("s02").page(1).confirmed[0]
        self.assertEqual(item.polygon,
                         [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
        self.assertEqual(item.shape, "partial")

        gt.dump_truth(gt.load_truth("s02"))
        reloaded = gt.load_truth("s02").page(1).confirmed[0]
        self.assertEqual(reloaded.polygon, item.polygon)
        self.assertEqual(reloaded.shape, "partial")
        self.assertEqual(reloaded.note, "misses the bay")

    def test_absent_optional_fields_are_not_written(self):
        payload = {"sheet": "s03", "pdf_sha256": "ghi", "reviewed": None,
                   "pages": {"1": {"confirmed": [
                       {"type": "door", "bbox": [1.0, 2.0, 3.0, 4.0]}]}}}
        self._write("s03", payload)
        gt.dump_truth(gt.load_truth("s03"))
        written = json.loads((gt.TRUTH_DIR / "s03.json").read_text(encoding="utf-8"))
        item = written["pages"]["1"]["confirmed"][0]
        self.assertEqual(set(item), {"type", "bbox"})

    def test_empty_verdict_lists_are_not_written(self):
        truth = gt.SheetTruth(slug="s04", pdf_sha256="jkl", reviewed="2026-08-06")
        truth.pages[1] = gt.PageTruth(confirmed=[
            gt.TruthItem(type="door", bbox=(1.0, 2.0, 3.0, 4.0))])
        gt.dump_truth(truth)
        written = json.loads((gt.TRUTH_DIR / "s04.json").read_text(encoding="utf-8"))
        self.assertEqual(set(written["pages"]["1"]), {"confirmed"})

    def test_an_unknown_shape_value_is_rejected(self):
        self._write("s05", {"sheet": "s05", "pdf_sha256": "x", "reviewed": None,
                            "pages": {"1": {"confirmed": [
                                {"type": "room", "bbox": [0.0, 0.0, 1.0, 1.0],
                                 "shape": "probably-fine"}]}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s05")

    def test_a_malformed_polygon_is_rejected(self):
        self._write("s06", {"sheet": "s06", "pdf_sha256": "x", "reviewed": None,
                            "pages": {"1": {"confirmed": [
                                {"type": "room", "bbox": [0.0, 0.0, 1.0, 1.0],
                                 "polygon": [[0.0, 0.0], [1.0]]}]}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s06")
