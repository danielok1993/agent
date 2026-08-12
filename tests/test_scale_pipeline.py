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


if __name__ == "__main__":
    unittest.main()
