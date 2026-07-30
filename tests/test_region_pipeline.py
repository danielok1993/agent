"""Region resolution rules (pipeline.resolve_page_regions).

A stub classifier stands in for the API so the four behaviour rules are tested
without credentials.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import PageData, PathPrimitive, Region
from pipeline import resolve_page_regions

PAGE_W, PAGE_H = 400.0, 400.0


def block(idx, x0, y0, x1, y1):
    return [
        PathPrimitive(
            path_index=idx + i, item_type="l", bbox=(x0, y, x1, y),
            color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
            dashes="", layer=None, points=[(x0, y), (x1, y)],
        )
        for i, y in enumerate(range(int(y0), int(y1), 4))
    ]


def two_blob_page():
    paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=paths)


def one_blob_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=block(0, 40, 40, 360, 360))


def raster_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    page_type="raster-heavy")


def stub_classifier(types_by_index):
    """Returns a callable matching classify_regions' signature."""
    def _classify(client, page, page_data, regions, crop_dir, **kwargs):
        out = []
        for i, r in enumerate(regions):
            out.append(Region(
                region_id=r.region_id, bbox=r.bbox,
                region_type=types_by_index.get(i, "other"),
                title=None, confidence=1.0, contains_multiple=False,
                path_count=r.path_count, source=r.source,
            ))
        return out, []
    return _classify


class RegionRuleTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "sheet.pdf")
        Path(self.pdf).write_bytes(b"%PDF-1.4")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def resolve(self, page_data, classifier, **kwargs):
        params = dict(
            pdf_path=self.pdf, page=None, page_data=page_data,
            gemini_client=object(), skip_gemini=False, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=classifier, clip_fn=lambda page, pd: [],
        )
        params.update(kwargs)
        return resolve_page_regions(**params)


class TestRuleOneNoFloorPlan(RegionRuleTestCase):
    def test_split_page_with_no_floor_plan_skips_detection(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "elevation", 1: "elevation"}))
        self.assertTrue(result.skip_detection)
        self.assertIn("NO_FLOOR_PLAN_REGION",
                      [w["warning_code"] for w in result.warnings])

    def test_split_page_with_a_floor_plan_filters_to_it(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertFalse(result.skip_detection)
        page_data = two_blob_page()
        self.assertLess(len(result.detection_page_data.paths), len(page_data.paths))
        self.assertGreater(len(result.detection_page_data.paths), 0)

    def test_filtered_page_data_keeps_full_page_dimensions(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertEqual(result.detection_page_data.width_px, PAGE_W)
        self.assertEqual(result.detection_page_data.height_px, PAGE_H)

    def test_two_floor_plans_are_detected_as_one_union(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "floor_plan"}))
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))


class TestRuleTwoWholePageFallback(RegionRuleTestCase):
    def test_unsplit_page_detects_even_when_classified_as_elevation(self):
        result = self.resolve(one_blob_page(), stub_classifier({0: "elevation"}))
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(one_blob_page().paths))

    def test_unsplit_page_records_a_page_fallback_region(self):
        result = self.resolve(one_blob_page(), stub_classifier({0: "floor_plan"}))
        self.assertEqual(len(result.regions), 1)
        self.assertEqual(result.regions[0].source, "page-fallback")


class TestRuleThreeRasterPage(RegionRuleTestCase):
    def test_raster_page_is_not_classified_and_still_detects(self):
        calls = []

        def spy(*args, **kwargs):
            calls.append(1)
            return [], []

        result = self.resolve(raster_page(), spy)
        self.assertEqual(calls, [])
        self.assertFalse(result.skip_detection)
        self.assertEqual(result.regions, [])
        self.assertIn("RASTER_PAGE_NO_VECTOR_INK",
                      [w["warning_code"] for w in result.warnings])


class TestRuleFourOfflineCache(RegionRuleTestCase):
    def test_offline_without_a_cache_does_no_filtering_and_warns(self):
        result = resolve_page_regions(
            pdf_path=self.pdf, page=None, page_data=two_blob_page(),
            gemini_client=None, skip_gemini=True, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=stub_classifier({}), clip_fn=lambda page, pd: [],
        )
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))
        self.assertIn("REGION_CACHE_MISS_OFFLINE",
                      [w["warning_code"] for w in result.warnings])

    def test_offline_reuses_a_cached_classification(self):
        page_data = two_blob_page()
        first = self.resolve(page_data, stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertFalse(first.skip_detection)

        def exploding(*args, **kwargs):
            raise AssertionError("classifier must not be called when cached")

        second = resolve_page_regions(
            pdf_path=self.pdf, page=None, page_data=page_data,
            gemini_client=None, skip_gemini=True, refresh_regions=False,
            crop_dir=str(Path(self.tmp) / "crops"),
            classify_fn=exploding, clip_fn=lambda page, pd: [],
        )
        self.assertEqual([r.region_type for r in second.regions],
                         ["floor_plan", "elevation"])
        self.assertEqual(len(second.detection_page_data.paths),
                         len(first.detection_page_data.paths))

    def test_refresh_regions_bypasses_the_cache(self):
        page_data = two_blob_page()
        self.resolve(page_data, stub_classifier({0: "floor_plan", 1: "elevation"}))
        result = self.resolve(page_data,
                              stub_classifier({0: "elevation", 1: "elevation"}),
                              refresh_regions=True)
        self.assertTrue(result.skip_detection)


class TestScheduleScoping(RegionRuleTestCase):
    def test_schedule_regions_supply_their_own_text_spans(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "schedule_table"}))
        self.assertIsNotNone(result.schedule_spans)

    def test_no_schedule_region_means_no_scoping(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertIsNone(result.schedule_spans)


if __name__ == "__main__":
    unittest.main()
