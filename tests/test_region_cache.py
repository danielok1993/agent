"""Region cache tests (gemini/region_cache.py)."""
import shutil
import tempfile
import unittest
from pathlib import Path

import dataclasses

from models import PageData, PathPrimitive, Region
from gemini.region_cache import (
    cache_file, cache_key, load_regions, page_content_hash, region_geometry_hash,
    regions_from_dicts, regions_to_dicts, save_regions,
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


class TestGeometryIsPartOfTheKey(unittest.TestCase):
    """Region bboxes ARE the filtering contract, and entries are permanent, so a
    changed segmentation must be a cache MISS — never a silent override."""

    def test_same_geometry_gives_the_same_key(self):
        pd = page([path(0, 1, 2, 3, 4)])
        self.assertEqual(cache_key(pd, regions()), cache_key(pd, regions()))

    def test_a_moved_region_changes_the_key(self):
        pd = page([path(0, 1, 2, 3, 4)])
        moved = regions()
        moved[0] = dataclasses.replace(moved[0], bbox=(0.0, 0.0, 60.0, 50.0))
        self.assertNotEqual(cache_key(pd, regions()), cache_key(pd, moved))

    def test_a_different_region_count_changes_the_key(self):
        pd = page([path(0, 1, 2, 3, 4)])
        self.assertNotEqual(cache_key(pd, regions()), cache_key(pd, regions()[:1]))

    def test_a_different_source_changes_the_key(self):
        pd = page([path(0, 1, 2, 3, 4)])
        resourced = regions()
        resourced[0] = dataclasses.replace(resourced[0], source="page-fallback")
        self.assertNotEqual(cache_key(pd, regions()), cache_key(pd, resourced))

    def test_the_classification_itself_is_not_part_of_the_key(self):
        # The cache exists to supply the classification, so it cannot be an
        # input to its own lookup.
        pd = page([path(0, 1, 2, 3, 4)])
        classified = regions()
        classified[0] = dataclasses.replace(classified[0], region_type="elevation",
                                            confidence=0.1, title="X")
        self.assertEqual(region_geometry_hash(regions()),
                         region_geometry_hash(classified))

    def test_the_page_content_still_matters(self):
        a, b = page([path(0, 1, 2, 3, 4)]), page([path(0, 1, 2, 3, 9)])
        self.assertNotEqual(cache_key(a, regions()), cache_key(b, regions()))


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
