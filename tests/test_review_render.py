"""Review images: one per page per entity type, ids stamped on."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from regression.review_render import short_id, write_review_overlays


class ShortIdTests(unittest.TestCase):
    def test_known_types_get_a_one_letter_prefix(self):
        self.assertEqual(short_id("door_0007"), "d7")
        self.assertEqual(short_id("window_0003"), "w3")
        self.assertEqual(short_id("room_0002"), "r2")
        self.assertEqual(short_id("label_0011"), "l11")
        self.assertEqual(short_id("schedule_0001"), "s1")

    def test_an_unparseable_id_is_returned_whole(self):
        self.assertEqual(short_id("weird"), "weird")
        self.assertEqual(short_id("door_abc"), "door_abc")


class ReviewOverlayTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.page_dir = Path(self._tmp.name)
        Image.new("RGB", (400, 300), "white").save(self.page_dir / "render.png")

    def _door(self, entity_id="door_0007"):
        return {"entity_id": entity_id, "entity_type": "door",
                "bbox": [10.0, 10.0, 60.0, 50.0], "confidence": 0.82,
                "attributes": {}}

    def _window(self):
        return {"entity_id": "window_0003", "entity_type": "window",
                "bbox": [100.0, 10.0, 160.0, 30.0], "confidence": 0.9,
                "attributes": {}}

    def _room(self):
        return {"entity_id": "room_0002", "entity_type": "room",
                "bbox": [0.0, 0.0, 200.0, 200.0], "confidence": 0.9,
                "attributes": {"polygon": [[10.0, 100.0], [190.0, 100.0],
                                           [190.0, 200.0], [10.0, 200.0]]}}

    def test_one_image_per_entity_type(self):
        written = write_review_overlays(
            self.page_dir, [self._door(), self._door("door_0011"), self._window()])
        self.assertEqual([p.name for p in written],
                         ["review_door.png", "review_window.png"])
        for path in written:
            self.assertTrue(path.exists())

    def test_the_image_matches_the_render_size(self):
        written = write_review_overlays(self.page_dir, [self._door()])
        with Image.open(written[0]) as image:
            self.assertEqual(image.size, (400, 300))

    def test_something_is_actually_drawn(self):
        written = write_review_overlays(self.page_dir, [self._door()])
        with Image.open(written[0]).convert("RGB") as image:
            colors = {image.getpixel((x, y))
                      for x in range(0, 400, 4) for y in range(0, 300, 4)}
        self.assertGreater(len(colors), 1, "review image is still blank white")

    def test_a_room_is_drawn_without_crashing_on_its_polygon(self):
        written = write_review_overlays(self.page_dir, [self._room()])
        self.assertEqual([p.name for p in written], ["review_room.png"])

    def test_nothing_unreviewed_writes_nothing(self):
        self.assertEqual(write_review_overlays(self.page_dir, []), [])
        self.assertEqual(sorted(p.name for p in self.page_dir.iterdir()),
                         ["render.png"])

    def test_a_missing_render_is_not_an_error(self):
        (self.page_dir / "render.png").unlink()
        self.assertEqual(write_review_overlays(self.page_dir, [self._door()]), [])


if __name__ == "__main__":
    unittest.main()
