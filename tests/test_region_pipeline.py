"""Region resolution rules (pipeline.resolve_page_regions).

A stub classifier stands in for the API so the four behaviour rules are tested
without credentials.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gemini.classifier import apply_classification
from gemini.region_cache import CACHE_DIR_NAME
from models import PageData, PathPrimitive, Region, TextSpan
from pipeline import REGION_MIN_COVERAGE_FRAC, resolve_page_regions

PAGE_W, PAGE_H = 400.0, 400.0

# Text fixtures for two_blob_page(): one span sits inside each blob, so tests
# can tell "the schedule region's own text" apart from "the whole page's text".
BLOB0_TEXT = "LOUNGE"
BLOB1_TEXT = "DOOR SCHEDULE"


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
    text_spans = [
        TextSpan(text=BLOB0_TEXT, bbox=(60.0, 90.0, 100.0, 100.0), font="Arial",
                 size=10.0, color=0, block_no=0, line_no=0),
        TextSpan(text=BLOB1_TEXT, bbox=(270.0, 90.0, 330.0, 100.0), font="Arial",
                 size=10.0, color=0, block_no=1, line_no=0),
    ]
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=paths, text_spans=text_spans)


def page_with_a_dropped_strip():
    """two_blob_page plus a 52px-tall strip of real drawing.

    It is its own leaf, but shorter than SEGMENT_MIN_REGION_SIDE_PX, so the
    segmenter discards it and filter_page_data would delete its 12 paths —
    13% of the sheet.
    """
    pd = two_blob_page()
    pd.paths = pd.paths + block(1000, 40, 300, 350, 348)
    return pd


def one_blob_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=block(0, 40, 40, 360, 360))


def raster_page():
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    page_type="raster-heavy")


def parse_failing_classifier(calls):
    """A classifier whose response does not parse.

    Runs the REAL apply_classification over corrupt text, so the caller sees
    exactly what the incident produced: every region unclassified, plus a
    REGION_CLASSIFY_PARSE_FAILURE warning, with nothing raised.
    """
    def _classify(client, page, page_data, regions, crop_dir, **kwargs):
        calls.append(1)
        return apply_classification("not json at all", regions)
    return _classify


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

    def test_no_floor_plan_but_schedule_present_still_detects_the_schedule(self):
        # A door/window schedule sheet: no floor plan anywhere, but a
        # schedule_table region exists. Detection must not be skipped
        # wholesale — it should run with an empty path set (no phantom
        # doors/rooms from elevation linework) so detect_schedules still
        # sees the schedule region's own text.
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "elevation", 1: "schedule_table"}))
        self.assertFalse(result.skip_detection)
        self.assertEqual(result.detection_page_data.paths, [])
        self.assertEqual([s.text for s in result.schedule_spans], [BLOB1_TEXT])
        self.assertIn("NO_FLOOR_PLAN_REGION",
                      [w["warning_code"] for w in result.warnings])


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


class TestRuleFiveCoverageGuard(RegionRuleTestCase):
    """Filtering only pays if the regions hold the sheet's ink."""

    def codes(self, result):
        return [w["warning_code"] for w in result.warnings]

    def test_low_coverage_warns_and_filters_nothing(self):
        page_data = page_with_a_dropped_strip()
        result = self.resolve(page_data,
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertIn("REGION_COVERAGE_TOO_LOW", self.codes(result))
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths), len(page_data.paths))

    def test_low_coverage_still_records_the_regions(self):
        result = self.resolve(page_with_a_dropped_strip(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertEqual([r.region_type for r in result.regions],
                         ["floor_plan", "elevation"])

    def test_healthy_coverage_does_not_warn(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertNotIn("REGION_COVERAGE_TOO_LOW", self.codes(result))
        self.assertLess(len(result.detection_page_data.paths),
                        len(two_blob_page().paths))

    def test_the_guard_cannot_fire_on_a_page_fallback_page(self):
        # The fallback region covers the sheet by construction, so it must be
        # unreachable there even at a floor nothing could satisfy.
        with mock.patch("pipeline.REGION_MIN_COVERAGE_FRAC", 1.1):
            result = self.resolve(one_blob_page(), stub_classifier({0: "floor_plan"}))
        self.assertNotIn("REGION_COVERAGE_TOO_LOW", self.codes(result))
        self.assertFalse(result.skip_detection)

    def test_the_guard_cannot_fire_on_a_zero_path_page(self):
        with mock.patch("pipeline.REGION_MIN_COVERAGE_FRAC", 1.1):
            result = self.resolve(raster_page(), stub_classifier({}))
        self.assertNotIn("REGION_COVERAGE_TOO_LOW", self.codes(result))

    # Assigned-path fraction measured over plans/ after the rotation fix, and
    # independently re-measured on re-review. These are the two bands the floor
    # has to separate; asserting the constant's value instead would only detect
    # that somebody changed it.
    MEASURED_FAILING = {"2682241": 0.654, "2710870": 0.853, "1326087": 0.886}
    MEASURED_LOWEST_HEALTHY = 0.943  # 2387826

    def test_the_floor_sits_between_the_measured_bands(self):
        self.assertGreater(REGION_MIN_COVERAGE_FRAC, max(self.MEASURED_FAILING.values()),
                           "floor must reject every sheet measured as losing ink")
        self.assertLess(REGION_MIN_COVERAGE_FRAC, self.MEASURED_LOWEST_HEALTHY,
                        "floor must not suppress filtering on a healthy sheet")


class TestClassificationFailureHandling(RegionRuleTestCase):
    def test_a_raising_classifier_is_not_reported_as_a_parse_failure(self):
        def boom(*args, **kwargs):
            raise RuntimeError("401 unauthenticated")

        result = self.resolve(two_blob_page(), boom)
        codes = [w["warning_code"] for w in result.warnings]
        self.assertIn("REGION_CLASSIFY_FAILED", codes)
        self.assertNotIn("REGION_CLASSIFY_PARSE_FAILURE", codes)
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))

    def cache_files(self):
        return sorted(p.name for p in (Path(self.tmp) / CACHE_DIR_NAME).glob("*.json"))

    def test_a_parse_failure_detects_the_whole_page(self):
        # A response that does not parse leaves every region "unclassified",
        # which reads as "no floor plan" and would skip detection entirely.
        # It carries no information, so it must degrade exactly like the
        # raising path: warn, detect everything.
        result = self.resolve(two_blob_page(), parse_failing_classifier([]))
        self.assertIn("REGION_CLASSIFY_PARSE_FAILURE",
                      [w["warning_code"] for w in result.warnings])
        self.assertFalse(result.skip_detection)
        self.assertEqual(len(result.detection_page_data.paths),
                         len(two_blob_page().paths))

    def test_a_parse_failure_is_never_cached(self):
        self.resolve(two_blob_page(), parse_failing_classifier([]))
        self.assertEqual(self.cache_files(), [])

    def test_a_parse_failure_does_not_poison_the_next_run(self):
        # The incident: the all-unclassified region list was cached, so every
        # later run loaded it and skipped detection without calling the API
        # again. A second resolve must reach the classifier.
        calls = []
        page_data = two_blob_page()
        self.resolve(page_data, parse_failing_classifier(calls))
        second = self.resolve(page_data,
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        self.assertEqual(len(calls), 1, "first run must have called the classifier")
        self.assertEqual([r.region_type for r in second.regions],
                         ["floor_plan", "elevation"])
        self.assertFalse(second.skip_detection)

    def test_an_incomplete_classification_is_still_cached(self):
        # Partial information is real information: region 0 classified, region
        # 1 unaddressed (REGION_CLASSIFY_INCOMPLETE). Only a TOTAL parse
        # failure skips the cache.
        def partial(client, page, page_data, regions, crop_dir, **kwargs):
            return apply_classification(
                '{"regions": [{"id": 0, "type": "floor_plan", "title": null,'
                ' "confidence": 1.0, "contains_multiple": false, "notes": ""}]}',
                regions)

        result = self.resolve(two_blob_page(), partial)
        self.assertIn("REGION_CLASSIFY_INCOMPLETE",
                      [w["warning_code"] for w in result.warnings])
        self.assertEqual(len(self.cache_files()), 1)

    def test_a_failed_cache_write_does_not_discard_the_classification(self):
        # The API call is billed and already succeeded; a read-only input
        # directory must not throw its result away.
        def unwritable(*args, **kwargs):
            raise OSError("Read-only file system")

        with mock.patch("pipeline.save_regions", unwritable):
            result = self.resolve(two_blob_page(),
                                  stub_classifier({0: "floor_plan", 1: "elevation"}))
        codes = [w["warning_code"] for w in result.warnings]
        self.assertIn("REGION_CACHE_WRITE_FAILED", codes)
        self.assertNotIn("REGION_CLASSIFY_FAILED", codes)
        self.assertEqual([r.region_type for r in result.regions],
                         ["floor_plan", "elevation"])
        self.assertLess(len(result.detection_page_data.paths),
                        len(two_blob_page().paths))


class TestScheduleScoping(RegionRuleTestCase):
    def test_schedule_regions_supply_their_own_text_spans(self):
        result = self.resolve(two_blob_page(),
                              stub_classifier({0: "floor_plan", 1: "schedule_table"}))
        # Scoped to the schedule_table region's own text only — not the
        # floor_plan region's text, and not the whole page's.
        self.assertEqual([s.text for s in result.schedule_spans], [BLOB1_TEXT])

    def test_no_schedule_region_means_page_wide_schedule_spans(self):
        page_data = two_blob_page()
        result = self.resolve(page_data,
                              stub_classifier({0: "floor_plan", 1: "elevation"}))
        # No schedule_table region exists, so scoping falls back to the WHOLE
        # page's spans — including the span that sits outside the floor_plan
        # region (region 0), proving this isn't secretly floor-plan-scoped.
        self.assertEqual(result.schedule_spans, page_data.text_spans)
        outside_floor_plan = next(
            s for s in page_data.text_spans if s.text == BLOB1_TEXT)
        self.assertIn(outside_floor_plan, result.schedule_spans)


if __name__ == "__main__":
    unittest.main()
