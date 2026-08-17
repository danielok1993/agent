"""tools/compare_sweeps.py — before/after comparison of two sweep runs.

Exercised on synthetic run directories (a tiny render.png plus
final_entities.json per page) so no pipeline runs. Pins:
  * entities are paired across runs geometrically (type + IoU), never by id,
    so a renumbered-but-unchanged entity is "kept" and a same-place bbox
    that shrank below the IoU gate is a removed/added pair;
  * every entity is coloured by the sweep's own verdict classification
    (confirmed > false positive > deferred > unreviewed);
  * the images are written where the summary says they are;
  * --snapshot keeps exactly one baseline per slug.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import regression.compare as cmp_mod
from regression.compare import (classify, compare_runs, diff_entities,
                                render_summary, snapshot)
from regression.ground_truth import PageTruth, SheetTruth, TruthItem


def entity(kind, bbox, eid, conf=0.7):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": conf, "attributes": {}}


def write_run(root: Path, name: str, entities: list[dict], size=(300, 200)) -> Path:
    run = root / name
    page = run / "pages" / "page_01"
    page.mkdir(parents=True)
    Image.new("RGB", size, "white").save(page / "render.png")
    (page / "final_entities.json").write_text(json.dumps({"page_number": 1, "entities": entities}))
    return run


class DiffEntitiesTests(unittest.TestCase):
    def test_pairs_geometrically_not_by_id(self):
        before = [entity("window", (10, 10, 60, 20), "window_0000"),
                  entity("window", (100, 10, 150, 20), "window_0001")]
        # window_0000 vanished; the survivor renumbered to window_0000.
        after = [entity("window", (100, 10, 150, 20), "window_0000")]
        kept, removed, added = diff_entities(before, after)
        self.assertEqual(kept, 1)
        self.assertEqual([e["bbox"] for e in removed], [[10, 10, 60, 20]])
        self.assertEqual(added, [])

    def test_same_place_low_iou_is_a_removed_added_pair(self):
        # s03's wall-opening reading (35px tall) vs the glazing frame (12px):
        # same window, IoU < 0.5 -> reported exactly as the sweep reports it.
        before = [entity("window", (3863, 2184, 4039, 2219), "window_0052")]
        after = [entity("window", (3863, 2201, 4039, 2213), "window_0012")]
        kept, removed, added = diff_entities(before, after)
        self.assertEqual((kept, len(removed), len(added)), (0, 1, 1))

    def test_type_must_match(self):
        before = [entity("window", (10, 10, 60, 20), "window_0000")]
        after = [entity("door", (10, 10, 60, 20), "door_0000")]
        self.assertEqual(diff_entities(before, after)[0], 0)


class ClassifyTests(unittest.TestCase):
    def test_verdict_precedence_matches_the_sweep(self):
        truth = PageTruth(
            confirmed=[TruthItem("window", (10, 10, 60, 20))],
            false_positives=[TruthItem("window", (100, 10, 150, 20))],
            deferred=[TruthItem("door", (10, 100, 60, 150))])
        ents = [entity("window", (10, 10, 60, 20), "window_0000"),
                entity("window", (100, 10, 150, 20), "window_0001"),
                entity("door", (10, 100, 60, 150), "door_0000"),
                entity("door", (200, 100, 260, 150), "door_0001")]
        self.assertEqual(classify(truth, ents), {
            "window_0000": "confirmed", "window_0001": "false_positive",
            "door_0000": "deferred", "door_0001": "unreviewed"})


class CompareRunsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.truth = SheetTruth(slug="sXX", reviewed="2026-01-01", pages={1: PageTruth(
            confirmed=[TruthItem("window", (10, 10, 60, 20))],
            false_positives=[TruthItem("window", (100, 10, 150, 20))])})

    def tearDown(self):
        self.tmp.cleanup()

    def test_changes_and_images(self):
        before = write_run(self.root, "before", [
            entity("window", (10, 10, 60, 20), "window_0000"),
            entity("window", (100, 10, 150, 20), "window_0001"),      # recorded FP
            entity("room", (20, 100, 120, 180), "room_0000")])
        after = write_run(self.root, "after", [
            entity("window", (10, 10, 60, 20), "window_0000"),
            entity("window", (200, 10, 250, 20), "window_0001"),      # new, unreviewed
            entity("room", (20, 100, 120, 180), "room_0000")])
        out = self.root / "out"
        results = compare_runs(before, after, self.truth, out)
        self.assertEqual(len(results), 1)
        page = results[0]
        self.assertEqual(page.kept, 2)
        self.assertEqual([(c.kind, c.entity["entity_id"], c.verdict) for c in page.changes],
                         [("added", "window_0001", "unreviewed"),
                          ("removed", "window_0001", "false_positive")])
        self.assertEqual(sorted(p.name for p in page.images),
                         ["page_01_changes.png", "page_01_side_by_side.png"])
        for image in page.images:
            self.assertTrue(image.exists())
            with Image.open(image) as im:
                self.assertGreater(im.width, 0)
        summary = render_summary("sXX", results, out)
        self.assertIn("1 removed, 1 added", summary)
        self.assertIn("[false_positive]", summary)
        self.assertIn("[unreviewed]", summary)

    def test_type_filter_and_no_changes(self):
        ents = [entity("window", (10, 10, 60, 20), "window_0000"),
                entity("door", (10, 100, 60, 150), "door_0000")]
        before = write_run(self.root, "before", ents)
        after = write_run(self.root, "after", ents[:1])   # door gone
        results = compare_runs(before, after, self.truth, self.root / "out", types={"window"})
        self.assertEqual(results[0].changes, [])
        self.assertEqual(results[0].kept, 1)
        self.assertEqual([p.name for p in results[0].images], ["page_01_side_by_side.png"])
        self.assertIn("no entity added or removed", render_summary("sXX", results, self.root / "out"))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_keeps_one_baseline_per_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run1 = write_run(root / "regress" / "sXX", "2026-01-01_00-00-00", [])
            run2 = write_run(root / "regress" / "sXX", "2026-01-02_00-00-00", [])
            with mock.patch.object(cmp_mod, "BASELINE_OUT", root / "baseline"), \
                    mock.patch.object(cmp_mod, "latest_run", side_effect=[run1, run2, None]):
                first = snapshot("sXX")
                self.assertTrue((first / "pages" / "page_01" / "render.png").exists())
                second = snapshot("sXX")
                self.assertEqual(second.name, run2.name)
                self.assertFalse(first.exists())            # replaced, not accumulated
                self.assertEqual(cmp_mod.baseline_run("sXX"), second)
                with self.assertRaises(FileNotFoundError):
                    snapshot("sXX")                        # no run to snapshot


if __name__ == "__main__":
    unittest.main()
