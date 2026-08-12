"""Measured scale expectations across the regression corpus.

Every number was measured on 2026-08-11 and is recorded in the design spec. A
failure here means scale reading changed on a real sheet -- investigate before
touching the expectations. The sheets are NDA-covered and gitignored, so these
tests skip when the corpus is not downloaded.
"""
import unittest

import fitz

from extraction.extractor import extract_page
from scale.text import text_scales
from scale.viewport import viewport_scales
from tests.fixtures import require_sheet

# slug -> the set of viewport denominators, rounded, with paper space excluded.
VIEWPORT_EXPECTATIONS = {
    "s03": {100, 50, 500},
    "s04": {50},
    "s05": {100},
    "s06": {100, 146},
    "s07": {100},
    "s08": {50},
    "s12": {100},
    "s13": {136, 146},
    "s15": {50},
    "s17": {100, 50, 1249},
}

# slug -> the set of denominators stated in text.
TEXT_EXPECTATIONS = {
    "s02": {50},
    "s14": {50},
    "s20": {50, 100},
}

# Neither tier resolves these. Six of the seven have zero text spans -- their
# text is outlined to curves -- which is what a future vision tier is for.
NO_SCALE_SLUGS = ["s01", "s09", "s10", "s11", "s16", "s18", "s19"]


def read(test_case, slug):
    path = require_sheet(test_case, slug)
    doc = fitz.open(path)
    page_data = extract_page(doc, 0)
    viewports = viewport_scales(doc, doc[0])
    texts = text_scales(page_data)
    doc.close()
    return viewports, texts


class TestViewportScales(unittest.TestCase):
    def test_measured_viewport_denominators(self):
        for slug, expected in VIEWPORT_EXPECTATIONS.items():
            with self.subTest(slug=slug):
                viewports, _ = read(self, slug)
                found = {int(round(v.denominator)) for v in viewports}
                self.assertEqual(found, expected)

    def test_viewports_are_ordered_smallest_bbox_first(self):
        # The nesting rule depends on this ordering: s06's inner 1:100 must be
        # offered before its outer 1:146.
        viewports, _ = read(self, "s06")
        areas = [(v.bbox[2] - v.bbox[0]) * (v.bbox[3] - v.bbox[1])
                 for v in viewports]
        self.assertEqual(areas, sorted(areas))
        self.assertEqual(int(round(viewports[0].denominator)), 100)

    def test_paper_space_viewport_is_never_reported(self):
        for slug in ("s03", "s04", "s08", "s17"):
            with self.subTest(slug=slug):
                viewports, _ = read(self, slug)
                self.assertTrue(all(v.denominator > 1.5 for v in viewports))


class TestTextScales(unittest.TestCase):
    def test_measured_text_denominators(self):
        for slug, expected in TEXT_EXPECTATIONS.items():
            with self.subTest(slug=slug):
                _, texts = read(self, slug)
                found = {int(round(t.denominator)) for t in texts}
                self.assertEqual(found, expected)

    def test_do_not_scale_notices_are_not_read_as_scales(self):
        for slug in ("s14", "s15"):
            with self.subTest(slug=slug):
                _, texts = read(self, slug)
                self.assertTrue(all("DO NOT SCALE" not in (t.raw or "").upper()
                                    for t in texts))


class TestSheetsWithNoRecoverableScale(unittest.TestCase):
    def test_neither_tier_resolves_them(self):
        for slug in NO_SCALE_SLUGS:
            with self.subTest(slug=slug):
                viewports, texts = read(self, slug)
                self.assertEqual(viewports, [])
                self.assertEqual(texts, [])


class TestKnownConflict(unittest.TestCase):
    """s13 is the one corpus sheet whose viewport and printed scale disagree.

    It measures 1:136.4 but prints SCALE 1:100, and its room geometry is the
    same magnitude as s06's 1:100 plans. Which is right is unresolved; the
    pipeline flags it rather than guessing.

    Both sides are asserted. Pinning only the viewport would let the conflict
    evaporate silently if text parsing regressed and stopped finding the
    caption — the test would still pass while the warning stopped firing.
    """

    def test_s13_viewport_measures_136(self):
        viewports, _ = read(self, "s13")
        self.assertEqual(min(int(round(v.denominator)) for v in viewports), 136)

    def test_s13_prints_1_to_100(self):
        _, texts = read(self, "s13")
        self.assertIn(100, {int(round(t.denominator)) for t in texts})

    def test_the_two_readings_are_far_enough_apart_to_conflict(self):
        from scale.resolver import AGREEMENT_TOLERANCE
        viewports, texts = read(self, "s13")
        measured = min(v.denominator for v in viewports)
        printed = min(t.denominator for t in texts)
        self.assertGreater(abs(measured - printed),
                           AGREEMENT_TOLERANCE * measured)

    def test_binding_a_region_over_the_plan_records_the_conflict(self):
        """The resolver-level assertion: a region sitting inside the measuring
        viewport, with the caption beneath it, must come back flagged."""
        from models import Region
        from scale.resolver import bind_scale

        viewports, texts = read(self, "s13")
        inner = viewports[0]
        x0, y0, x1, y1 = inner.bbox
        probe = Region(region_id="probe",
                       bbox=(x0 + 1.0, y0 + 1.0, x1 - 1.0, y1 - 1.0),
                       region_type="floor_plan")
        found = bind_scale(probe, viewports, texts)
        self.assertIsNotNone(found)
        self.assertEqual(int(round(found.denominator)), 136)
        self.assertIsNotNone(found.conflict)


if __name__ == "__main__":
    unittest.main()
