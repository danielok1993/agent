"""The verdict writer: selections in, ground truth out.

Everything here is synthetic. No PDF is opened and no sweep is run.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from regression import corpus, ground_truth as gt
from regression import verdicts as verdicts_module
from regression.verdicts import Verdict, record_verdicts


def door(entity_id="door_0007", bbox=(1200.0, 870.0, 1240.0, 900.0)):
    return {"entity_id": entity_id, "entity_type": "door", "bbox": list(bbox),
            "confidence": 0.82, "attributes": {}}


def room(entity_id="room_0002"):
    return {"entity_id": entity_id, "entity_type": "room",
            "bbox": [0.0, 0.0, 100.0, 100.0], "confidence": 0.9,
            "attributes": {"polygon": [[0.0, 0.0], [100.0, 0.0],
                                       [100.0, 100.0], [0.0, 100.0]]}}


class VerdictWriterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self._truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"
        gt.TRUTH_DIR.mkdir()
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._truth_dir))

        self._manifest = corpus.MANIFEST_PATH
        corpus.MANIFEST_PATH = root / "MANIFEST.json"
        corpus.MANIFEST_PATH.write_text(json.dumps({
            "storage": "",
            "sheets": [
                {"slug": "s02", "file": "s02.pdf", "sha256": "bbb", "pages": 1},
                {"slug": "s01", "file": "s01.pdf", "sha256": "aaa", "pages": 1},
            ],
        }, indent=2) + "\n", encoding="utf-8")
        self.addCleanup(lambda: setattr(corpus, "MANIFEST_PATH", self._manifest))

    def _existing_truth(self):
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "aaa", "reviewed": "2026-01-01",
            "pages": {"1": {"confirmed": [
                {"type": "window", "bbox": [10.0, 20.0, 30.0, 40.0],
                 "note": "recorded earlier"}]}},
        }, indent=2) + "\n", encoding="utf-8")

    def _load(self, slug="s01"):
        return json.loads((gt.TRUTH_DIR / f"{slug}.json").read_text(encoding="utf-8"))

    def test_a_correct_verdict_lands_in_confirmed(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        confirmed = self._load()["pages"]["1"]["confirmed"]
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0]["type"], "door")
        self.assertEqual(confirmed[0]["bbox"], [1200.0, 870.0, 1240.0, 900.0])

    def test_a_wrong_verdict_lands_in_false_positives(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=False)],
                        today="2026-08-06")
        page = self._load()["pages"]["1"]
        self.assertNotIn("confirmed", page)
        self.assertEqual(len(page["false_positives"]), 1)

    def test_the_entity_id_is_never_persisted(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        raw = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        self.assertNotIn("door_0007", raw)
        self.assertNotIn("entity_id", raw)

    def test_existing_verdicts_survive_untouched(self):
        self._existing_truth()
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        confirmed = self._load()["pages"]["1"]["confirmed"]
        self.assertEqual(confirmed[0]["type"], "window")
        self.assertEqual(confirmed[0]["note"], "recorded earlier")
        self.assertEqual(confirmed[1]["type"], "door")

    def test_a_room_verdict_stores_its_polygon_and_shape(self):
        record_verdicts("s01", [Verdict(page=1, entity=room(), correct=True,
                                        shape="partial",
                                        note="misses the doorway recess")],
                        today="2026-08-06")
        item = self._load()["pages"]["1"]["confirmed"][0]
        self.assertEqual(len(item["polygon"]), 4)
        self.assertEqual(item["shape"], "partial")
        self.assertEqual(item["note"], "misses the doorway recess")

    def test_a_non_room_entity_stores_no_polygon(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        self.assertNotIn("polygon", self._load()["pages"]["1"]["confirmed"][0])

    def test_reviewed_and_sha_are_set(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        payload = self._load()
        self.assertEqual(payload["reviewed"], "2026-08-06")
        self.assertEqual(payload["pdf_sha256"], "aaa")

    def test_the_manifest_entry_is_flagged_labeled(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        by_slug = {s["slug"]: s for s in sheets}
        self.assertTrue(by_slug["s01"]["labeled"])
        self.assertNotIn("labeled", by_slug["s02"])

    def test_the_manifest_keeps_its_original_order(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        self.assertEqual([s["slug"] for s in sheets], ["s02", "s01"])

    def test_verdicts_across_pages_land_on_their_own_pages(self):
        record_verdicts("s01", [
            Verdict(page=1, entity=door("door_0001"), correct=True),
            Verdict(page=2, entity=door("door_0002"), correct=True),
        ], today="2026-08-06")
        self.assertEqual(set(self._load()["pages"]), {"1", "2"})

    def test_an_unknown_slug_raises_and_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_verdicts("s99", [Verdict(page=1, entity=door(), correct=True)],
                            today="2026-08-06")
        self.assertFalse((gt.TRUTH_DIR / "s99.json").exists())

    def test_an_invalid_shape_raises_before_writing_anything(self):
        self._existing_truth()
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=room(), correct=True,
                                            shape="probably-fine")],
                            today="2026-08-06")
        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_ground_truth_from_another_pdf_raises_and_writes_nothing(self):
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "9" * 64, "reviewed": "2026-01-01",
            "pages": {},
        }, indent=2) + "\n", encoding="utf-8")
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                            today="2026-08-06")

        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        self.assertNotIn("labeled", {s["slug"]: s for s in sheets}["s01"])

    def test_an_empty_verdict_list_writes_nothing(self):
        record_verdicts("s01", [], today="2026-08-06")
        self.assertFalse((gt.TRUTH_DIR / "s01.json").exists())
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        self.assertNotIn("labeled", {s["slug"]: s for s in sheets}["s01"])

    # -- Fix round 1 -----------------------------------------------------

    def test_a_three_element_bbox_raises_and_writes_nothing(self):
        self._existing_truth()
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=door(bbox=(1.0, 2.0, 3.0)),
                                            correct=True)],
                            today="2026-08-06")
        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_an_empty_entity_type_raises_and_writes_nothing(self):
        self._existing_truth()
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        bad = door()
        bad["entity_type"] = ""
        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=bad, correct=True)],
                            today="2026-08-06")
        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_shape_on_a_non_room_entity_raises_and_writes_nothing(self):
        self._existing_truth()
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True,
                                            shape="approved")],
                            today="2026-08-06")
        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_a_non_room_entity_with_a_polygon_attribute_writes_no_polygon(self):
        entity = door()
        entity["attributes"] = {"polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]}
        record_verdicts("s01", [Verdict(page=1, entity=entity, correct=True)],
                        today="2026-08-06")
        self.assertNotIn("polygon", self._load()["pages"]["1"]["confirmed"][0])

    def test_a_dump_truth_failure_still_leaves_the_manifest_flagged_labeled(self):
        def _boom(_truth):
            raise RuntimeError("disk full")

        original = verdicts_module.dump_truth
        verdicts_module.dump_truth = _boom
        self.addCleanup(lambda: setattr(verdicts_module, "dump_truth", original))

        with self.assertRaises(RuntimeError):
            record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                            today="2026-08-06")

        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        by_slug = {s["slug"]: s for s in sheets}
        self.assertTrue(by_slug["s01"]["labeled"])


if __name__ == "__main__":
    unittest.main()
