"""Region classification parsing tests (gemini/classifier.py).

No API calls: apply_classification is tested against recorded response text.
"""
import json
import tempfile
import types as pytypes
import unittest
from pathlib import Path

import fitz

from models import PageData, Region, TextSpan
from gemini.classifier import (
    REGION_TYPES, apply_classification, classify_regions, region_title_text,
)


def region(i):
    return Region(region_id=f"region_{i:04d}", bbox=(0.0, 0.0, 100.0, 100.0))


def response(entries):
    return json.dumps({"regions": entries})


class TestApplyClassification(unittest.TestCase):
    def test_types_titles_and_confidence_are_applied(self):
        regions = [region(0), region(1)]
        raw = response([
            {"id": 0, "type": "floor_plan", "title": "GROUND FLOOR PLAN",
             "confidence": 0.95, "contains_multiple": False, "notes": ""},
            {"id": 1, "type": "elevation", "title": "REAR ELEVATION",
             "confidence": 1.0, "contains_multiple": True, "notes": ""},
        ])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual([r.region_type for r in out], ["floor_plan", "elevation"])
        self.assertEqual(out[0].title, "GROUND FLOOR PLAN")
        self.assertEqual(out[0].confidence, 0.95)
        self.assertTrue(out[1].contains_multiple)
        self.assertEqual(warnings, [])

    def test_markdown_fences_are_stripped(self):
        regions = [region(0)]
        raw = "```json\n" + response(
            [{"id": 0, "type": "floor_plan", "title": None, "confidence": 1.0,
              "contains_multiple": False, "notes": ""}]) + "\n```"
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[0].region_type, "floor_plan")
        self.assertEqual(warnings, [])

    def test_missing_region_id_warns_and_stays_unclassified(self):
        regions = [region(0), region(1)]
        raw = response([{"id": 0, "type": "floor_plan", "title": None,
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[1].region_type, "unclassified")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_INCOMPLETE"])

    def test_invalid_json_warns_and_leaves_everything_unclassified(self):
        regions = [region(0)]
        out, warnings = apply_classification("not json at all", regions)
        self.assertEqual(out[0].region_type, "unclassified")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_PARSE_FAILURE"])
        self.assertEqual(warnings[0]["severity"], "error")

    def test_unknown_type_is_coerced_to_other_with_a_warning(self):
        regions = [region(0)]
        raw = response([{"id": 0, "type": "blueprint", "title": None,
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(out[0].region_type, "other")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["REGION_CLASSIFY_INCOMPLETE"])

    def test_unknown_region_id_in_response_is_ignored(self):
        regions = [region(0)]
        raw = response([
            {"id": 0, "type": "floor_plan", "title": None, "confidence": 1.0,
             "contains_multiple": False, "notes": ""},
            {"id": 99, "type": "elevation", "title": None, "confidence": 1.0,
             "contains_multiple": False, "notes": ""},
        ])
        out, warnings = apply_classification(raw, regions)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].region_type, "floor_plan")

    def test_original_regions_are_not_mutated(self):
        regions = [region(0)]
        raw = response([{"id": 0, "type": "floor_plan", "title": "X",
                         "confidence": 1.0, "contains_multiple": False, "notes": ""}])
        apply_classification(raw, regions)
        self.assertEqual(regions[0].region_type, "unclassified")

    def test_taxonomy_contains_the_types_the_pipeline_consumes(self):
        self.assertIn("floor_plan", REGION_TYPES)
        self.assertIn("schedule_table", REGION_TYPES)
        self.assertIn("other", REGION_TYPES)


class _CapturingClient:
    """Stands in for genai.Client, recording the config it was called with."""

    def __init__(self, text):
        self.models = self
        self.config = None
        self._text = text

    def generate_content(self, *, model, contents, config):
        self.config = config
        return pytypes.SimpleNamespace(text=self._text)


class TestRequestShape(unittest.TestCase):
    """The response must be schema-constrained at decode time.

    Plain JSON mode does not constrain generation: on 2026-08-05 a response for
    sheet s11 started as valid JSON and then degenerated mid-stream into an
    off-topic fragment, breaking the object separator. A response_schema makes
    that structurally impossible.
    """

    def call(self):
        doc = fitz.open()
        doc.new_page(width=400, height=400)
        page_data = PageData(page_number=1, width_px=800.0, height_px=800.0)
        regions = [region(0)]
        client = _CapturingClient(response(
            [{"id": 0, "type": "floor_plan", "title": None, "confidence": 1.0,
              "contains_multiple": False, "notes": ""}]))
        with tempfile.TemporaryDirectory() as tmp:
            out, warnings = classify_regions(
                client, doc[0], page_data, regions, str(Path(tmp) / "crops"))
        doc.close()
        return client.config, out, warnings

    def test_the_request_carries_a_response_schema(self):
        config, _, _ = self.call()
        self.assertIsNotNone(config.response_schema)

    def test_the_schema_constrains_type_to_the_taxonomy(self):
        config, _, _ = self.call()
        item = config.response_schema.properties["regions"].items
        self.assertEqual(list(item.properties["type"].enum), REGION_TYPES)

    def test_the_schema_requires_an_id_for_every_region(self):
        # Region identity is the whole contract — apply_classification matches
        # responses to regions by id and silently ignores items without one.
        config, _, _ = self.call()
        item = config.response_schema.properties["regions"].items
        self.assertIn("id", item.required)

    def test_a_schema_valid_response_still_classifies(self):
        _, out, warnings = self.call()
        self.assertEqual(out[0].region_type, "floor_plan")
        self.assertEqual(warnings, [])


class TestRegionTitleText(unittest.TestCase):
    def test_returns_largest_text_inside_the_box_first(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[
                TextSpan(text="KITCHEN", bbox=(60.0, 60.0, 120.0, 70.0),
                         font="H", size=6.0, color=0, block_no=0, line_no=0),
                TextSpan(text="GROUND FLOOR PLAN", bbox=(60.0, 150.0, 200.0, 170.0),
                         font="H", size=12.0, color=0, block_no=0, line_no=1),
            ],
        )
        got = region_title_text(page, (50.0, 50.0, 300.0, 300.0))
        self.assertEqual(got[0], "GROUND FLOOR PLAN")

    def test_text_outside_the_box_is_excluded(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[TextSpan(text="TITLE BLOCK", bbox=(400.0, 400.0, 480.0, 415.0),
                                 font="H", size=12.0, color=0, block_no=0, line_no=0)],
        )
        self.assertEqual(region_title_text(page, (50.0, 50.0, 300.0, 300.0)), [])

    def test_duplicate_strings_appear_once(self):
        page = PageData(
            page_number=1, width_px=500.0, height_px=500.0,
            text_spans=[
                TextSpan(text="BEDROOM", bbox=(60.0, 60.0, 120.0, 70.0), font="H",
                         size=6.0, color=0, block_no=0, line_no=0),
                TextSpan(text="BEDROOM", bbox=(60.0, 90.0, 120.0, 100.0), font="H",
                         size=6.0, color=0, block_no=0, line_no=1),
            ],
        )
        self.assertEqual(region_title_text(page, (50.0, 50.0, 300.0, 300.0)), ["BEDROOM"])


if __name__ == "__main__":
    unittest.main()
