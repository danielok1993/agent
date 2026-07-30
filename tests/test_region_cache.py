"""Region cache tests (gemini/region_cache.py)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import PageData, PathPrimitive, Region
from gemini.region_cache import (
    cache_file, load_regions, page_content_hash, regions_from_dicts,
    regions_to_dicts, save_regions,
)


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def page(paths):
    return PageData(page_number=1, width_px=100.0, height_px=100.0, paths=list(paths))


def regions():
    return [
        Region(region_id="region_0000", bbox=(0.0, 0.0, 50.0, 50.0),
               region_type="floor_plan", title="GROUND FLOOR", confidence=0.95,
               contains_multiple=False, path_count=12, source="whitespace"),
        Region(region_id="region_0001", bbox=(50.0, 0.0, 100.0, 50.0),
               region_type="elevation", title=None, confidence=1.0,
               contains_multiple=True, path_count=8, source="whitespace+clip"),
    ]


class TestContentHash(unittest.TestCase):
    def test_same_content_gives_the_same_hash(self):
        a, b = page([path(0, 1, 2, 3, 4)]), page([path(0, 1, 2, 3, 4)])
        self.assertEqual(page_content_hash(a), page_content_hash(b))

    def test_different_geometry_gives_a_different_hash(self):
        a, b = page([path(0, 1, 2, 3, 4)]), page([path(0, 1, 2, 3, 9)])
        self.assertNotEqual(page_content_hash(a), page_content_hash(b))

    def test_different_path_count_gives_a_different_hash(self):
        a = page([path(0, 1, 2, 3, 4)])
        b = page([path(0, 1, 2, 3, 4), path(1, 5, 6, 7, 8)])
        self.assertNotEqual(page_content_hash(a), page_content_hash(b))


class TestRoundTrip(unittest.TestCase):
    def test_dict_round_trip_preserves_every_field(self):
        restored = regions_from_dicts(regions_to_dicts(regions()))
        self.assertEqual(restored, regions())

    def test_bbox_survives_as_a_tuple(self):
        restored = regions_from_dicts(regions_to_dicts(regions()))
        self.assertIsInstance(restored[0].bbox, tuple)


class TestCacheFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "drawing.pdf")
        Path(self.pdf).write_bytes(b"%PDF-1.4")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_then_load_returns_the_regions(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertEqual(load_regions(self.pdf, 1, "abc123"), regions())

    def test_load_with_a_different_hash_misses(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertIsNone(load_regions(self.pdf, 1, "different"))

    def test_load_with_a_different_page_misses(self):
        save_regions(self.pdf, 1, "abc123", regions())
        self.assertIsNone(load_regions(self.pdf, 2, "abc123"))

    def test_load_with_no_cache_returns_none(self):
        self.assertIsNone(load_regions(self.pdf, 1, "abc123"))

    def test_cache_lives_beside_the_pdf(self):
        target = cache_file(self.pdf, 1, "abc123")
        self.assertEqual(target.parent.parent, Path(self.tmp))
        self.assertEqual(target.parent.name, ".regions_cache")

    def test_corrupt_cache_file_returns_none_instead_of_raising(self):
        target = cache_file(self.pdf, 1, "abc123")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{ not json", encoding="utf-8")
        self.assertIsNone(load_regions(self.pdf, 1, "abc123"))


if __name__ == "__main__":
    unittest.main()
