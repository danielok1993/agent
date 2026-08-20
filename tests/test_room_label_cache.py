"""Room label cache tests (gemini/room_label_cache.py)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import Entity, PageData, PathPrimitive
from gemini.room_label_cache import (
    cache_file, cache_key, load_labels, room_geometry_hash, save_labels,
)


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def page():
    return PageData(page_number=1, width_px=100.0, height_px=100.0,
                    paths=[path(0, 1, 2, 3, 4)])


def room(i, poly, label=None):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return Entity(
        entity_id=f"room_{i:04d}", entity_type="room",
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        confidence=0.85, source="heuristic", label=label,
        attributes={"polygon": [list(p) for p in poly]},
    )


SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]
OTHER = [(0, 0), (300, 0), (300, 200), (0, 200)]


class TestGeometryHash(unittest.TestCase):
    def test_same_polygons_give_the_same_hash(self):
        self.assertEqual(room_geometry_hash([room(0, SQUARE)]),
                         room_geometry_hash([room(0, SQUARE)]))

    def test_a_changed_polygon_gives_a_different_hash(self):
        self.assertNotEqual(room_geometry_hash([room(0, SQUARE)]),
                            room_geometry_hash([room(0, OTHER)]))

    def test_an_extra_room_gives_a_different_hash(self):
        self.assertNotEqual(room_geometry_hash([room(0, SQUARE)]),
                            room_geometry_hash([room(0, SQUARE), room(1, OTHER)]))


class TestCacheKey(unittest.TestCase):
    def test_the_prompt_version_is_part_of_the_key(self):
        import gemini.room_label_cache as rlc
        key_before = cache_key(page(), [room(0, SQUARE)])
        original = rlc.PROMPT_VERSION
        try:
            rlc.PROMPT_VERSION = "v-other"
            self.assertNotEqual(cache_key(page(), [room(0, SQUARE)]), key_before)
        finally:
            rlc.PROMPT_VERSION = original


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "sheet.pdf")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_miss_returns_none(self):
        self.assertIsNone(load_labels(self.pdf, 1, "nokey"))

    def test_labels_survive_a_round_trip(self):
        rooms = [room(0, SQUARE, "Kitchen"), room(1, OTHER, None)]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        self.assertEqual(load_labels(self.pdf, 1, key),
                         {"room_0000": "Kitchen", "room_0001": None})

    def test_the_cache_file_lives_beside_the_pdf(self):
        rooms = [room(0, SQUARE, "Kitchen")]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        self.assertTrue(cache_file(self.pdf, 1, key).exists())
        self.assertEqual(cache_file(self.pdf, 1, key).parent.name,
                         ".room_labels_cache")

    def test_corrupt_cache_content_reads_as_a_miss(self):
        rooms = [room(0, SQUARE, "Kitchen")]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        cache_file(self.pdf, 1, key).write_text("{ broken", encoding="utf-8")
        self.assertIsNone(load_labels(self.pdf, 1, key))


if __name__ == "__main__":
    unittest.main()
