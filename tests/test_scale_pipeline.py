"""Scale reporting inside the pipeline: the console table and summary.json."""
import unittest

from models import Region, ScaleInfo
from pipeline import scale_summary_dict, scale_table
from scale.resolver import PageScales


def region(rid, rtype="floor_plan"):
    return Region(region_id=rid, bbox=(0.0, 0.0, 10.0, 10.0), region_type=rtype)


class TestScaleTable(unittest.TestCase):
    def render(self, page_scales, regions):
        from rich.console import Console
        console = Console(record=True, width=120)
        console.print(scale_table(page_scales, regions))
        return console.export_text()

    def test_resolved_scale_is_shown_with_its_source(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport", raw="C=35.27546",
            nominal=100.0)})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:100", out)
        self.assertIn("viewport", out)

    def test_unresolved_region_is_shown_as_unknown(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=None, source="unresolved")})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("UNKNOWN", out.upper())

    def test_conflict_is_surfaced_in_the_table(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=136.4, source="viewport",
            conflict="text nearby says 1:100")})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:136.4", out)
        self.assertIn("CONFLICT", out.upper())

    def test_non_standard_measurement_shows_its_nearest_standard(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=99.6, source="viewport", nominal=100.0)})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("1:100", out)

    def test_unmatched_bracket_in_raw_text_does_not_raise(self):
        """raw is lifted verbatim from PDF text and can contain a bracket
        sequence Rich would otherwise try to parse as markup — an unmatched
        closing tag raises rich.errors.MarkupError unless it is escaped."""
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="text", raw="SCALE 1:100 [/see detail]")})
        out = self.render(scales, [region("region_0002")])
        self.assertIn("[/see detail]", out)


class TestScaleSummaryDict(unittest.TestCase):
    def test_shape_is_json_serialisable(self):
        import json
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport", bbox=(1.0, 2.0, 3.0, 4.0),
            raw="C=35.27546", nominal=100.0)})
        json.dumps(scale_summary_dict(scales))

    def test_denominator_and_source_are_recorded(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=100.0, source="viewport")})
        payload = scale_summary_dict(scales)
        self.assertEqual(payload["by_region"]["region_0002"]["denominator"], 100.0)
        self.assertEqual(payload["by_region"]["region_0002"]["source"], "viewport")

    def test_unresolved_records_a_null_denominator(self):
        scales = PageScales(by_region={"region_0002": ScaleInfo(
            denominator=None, source="unresolved")})
        payload = scale_summary_dict(scales)
        self.assertIsNone(payload["by_region"]["region_0002"]["denominator"])


class TestWarningCountIncludesScaleWarnings(unittest.TestCase):
    """warning_count comes from page_warnings, not all_warnings.

    A scale warning appended straight to all_warnings would show up in
    warnings.json but be missing from the per-page count in summary.json.
    """

    def test_scale_warnings_are_counted(self):
        from models import PageData
        from pipeline import _page_summary_dict

        page_data = PageData(page_number=1, width_px=10.0, height_px=10.0)
        scale_warning = {"page_number": 1, "warning_code": "SCALE_UNRESOLVED",
                         "severity": "warning", "message": "no scale"}
        summary = _page_summary_dict(
            page_data, [], [], [scale_warning], [], PageScales())
        self.assertEqual(summary["warning_count"], 1)


class TestSummaryDetectionSurvivesSkipDetection(unittest.TestCase):
    """det_scale is resolved before the skip_detection branch in run_extract
    (so the summary always records the factor), and _page_summary_dict is
    the sole place that turns it into the "detection" block. This pins that
    the summary path is unconditional: calling it with a populated det_scale
    and empty candidates/entities (the skip_detection shape) still produces
    a fully-populated "detection" key — the summary does not depend on
    whether detection actually ran.
    """

    def test_detection_block_populated_when_candidates_are_empty(self):
        from models import PageData
        from pipeline import _page_summary_dict
        from scale.factor import DetectionScale

        page_data = PageData(page_number=1, width_px=10.0, height_px=10.0)
        det_scale = DetectionScale(factor=0.5, denominator=100.0,
                                   source="floor_plan_regions")
        summary = _page_summary_dict(
            page_data, [], [], [], [], PageScales(), det_scale)
        detection = summary["scales"]["detection"]
        self.assertEqual(detection["factor"], 0.5)
        self.assertEqual(detection["denominator"], 100.0)
        self.assertEqual(detection["source"], "floor_plan_regions")


class TestFallbackDenominatorIsThreaded(unittest.TestCase):
    def test_run_extract_passes_its_fallback_to_the_resolver(self):
        import inspect
        import pipeline

        signature = inspect.signature(pipeline.run_extract)
        self.assertIn("fallback_denominator", signature.parameters)
        self.assertIsNone(
            signature.parameters["fallback_denominator"].default)

        # The call site must forward it, not accept and drop it. Read the
        # source rather than running a whole extraction: this is a wiring
        # assertion, and a full run needs a PDF, Gemini and several seconds.
        source = inspect.getsource(pipeline.run_extract)
        self.assertIn("fallback=fallback_denominator", source)


class TestDimensionStringsAreThreadedIntoTheGates(unittest.TestCase):
    def test_run_extract_measures_the_page_once_and_passes_it_on(self):
        # The page's ticked dimension strings are matched ONCE, on the full
        # page (the takeoff's convention), and handed both to detection_scale
        # — so a verified 1:92.2 drives s01's gates — and to compute_takeoff,
        # which must not re-match them. Same wiring assertion as above.
        import inspect
        import pipeline

        source = inspect.getsource(pipeline.run_extract)
        self.assertIn("dimension_matches(page_data.paths, page_data.text_spans)",
                      source)
        self.assertIn("dimensions=dimensions", source)
        self.assertIn("dimension_matches=dimensions", source)

    def test_the_corpus_page_loader_does_the_same(self):
        # tools/_corpus_page.py is what every probe and the census harness
        # run on; findings §4c requires it to reproduce the sweep's factor.
        import inspect

        from tools import _corpus_page

        source = inspect.getsource(_corpus_page.load_detection_pages)
        self.assertIn("dimensions=", source)


if __name__ == "__main__":
    unittest.main()
