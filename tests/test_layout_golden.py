"""Golden segmentation results on the corpus reference sheets (s01, s02, s11).

Measured 2026-07-28. A failure here means segmentation behaviour changed on a
real sheet — investigate before touching the expected numbers. The sheets
themselves are NDA-covered and gitignored (fixtures/sheets/); these tests
skip via tests.fixtures.require_sheet when the corpus isn't downloaded.
"""
import unittest

import fitz

from extraction.extractor import extract_page
from layout import qualifying_clip_rects, segment_page
from layout.occupancy import build_ink_map, is_page_spanning
from tests.fixtures import require_sheet


def segment(test_case, slug, page_index=0, use_clips=True):
    path = require_sheet(test_case, slug)
    doc = fitz.open(path)
    page_data = extract_page(doc, page_index)
    clips = qualifying_clip_rects(doc[page_index], page_data) if use_clips else []
    regions = segment_page(page_data, clips)
    doc.close()
    return page_data, regions


class TestGoldenSegmentation(unittest.TestCase):
    def test_floor_plans_splits_into_two_regions(self):
        page_data, regions = segment(self, "s01")
        self.assertEqual(len(regions), 2)

    def test_floor_plans_assigns_every_path(self):
        page_data, regions = segment(self, "s01")
        self.assertEqual(sum(r.path_count for r in regions), len(page_data.paths))

    def test_floor_plans_captions_merged_so_titles_are_inside_regions(self):
        page_data, regions = segment(self, "s01")
        titles = {"PROPOSED GROUND FLOOR PLAN", "PROPOSED FIRST FLOOR PLAN"}
        found = set()
        for span in page_data.text_spans:
            text = span.text.strip()
            if text not in titles:
                continue
            cx = (span.bbox[0] + span.bbox[2]) / 2
            cy = (span.bbox[1] + span.bbox[3]) / 2
            for r in regions:
                if r.bbox[0] <= cx <= r.bbox[2] and r.bbox[1] <= cy <= r.bbox[3]:
                    found.add(text)
        self.assertEqual(found, titles)

    def test_5_1133_is_too_dense_to_split(self):
        _, regions = segment(self, "s02")
        self.assertEqual(len(regions), 1)


class TestSpanFilterIsLoadBearing(unittest.TestCase):
    """This sheet carries full-page border rules. With the span filter applied
    the ink map has no page-spanning rows and the sheet splits into 15 regions
    (13 at SEGMENT_MAX_DEPTH 6; two title-block leaves subdivide at 7).
    The counterfactual — 0 regions with the filter disabled — was measured on
    2026-07-28 but cannot be asserted here: build_ink_map applies the filter
    unconditionally, and adding a production parameter purely for this test
    was rejected as over-building."""

    def _page_data(self):
        doc = fitz.open(require_sheet(self, "s11"))
        page_data = extract_page(doc, 0)
        doc.close()
        return page_data

    def test_sheet_has_page_spanning_primitives(self):
        page_data = self._page_data()
        spanning = [
            p for p in page_data.paths
            if is_page_spanning(p, page_data.width_px, page_data.height_px)
        ]
        self.assertGreater(len(spanning), 0)

    def test_sheet_splits_into_many_regions_with_the_filter(self):
        page_data = self._page_data()
        regions = segment_page(page_data)
        self.assertEqual(len(regions), 15)

    def test_ink_map_has_no_page_spanning_rows(self):
        page_data = self._page_data()
        ink = build_ink_map(page_data)
        spanning_rows = sum(
            1 for r in range(ink.rows) if sum(ink.bins[r]) > 0.9 * ink.cols
        )
        self.assertEqual(spanning_rows, 0,
                         "span filter should have removed full-width border rules")


class TestS15PathsOnlyRetry(unittest.TestCase):
    """s15 measured 2026-08-13: 214 text spans bridge every gutter, so the
    text-inclusive cut yields 1 leaf and the sheet fell back to whole-page
    detection (82 returned FPs, 63 of 72 phantom rooms fenced in elevation
    regions). The paths-only retry splits it into 8 regions with full path
    coverage."""

    def test_s15_splits_into_nine_regions_via_retry(self):
        # 8 at SEGMENT_MAX_DEPTH 6; a notes leaf subdivides at 7 (2026-08-27).
        _, regions = segment(self, "s15")
        self.assertEqual(len(regions), 9)
        self.assertTrue(all(r.source == "paths-only" for r in regions))

    def test_s15_every_path_stays_assigned(self):
        from layout.filter import assigned_path_fraction
        page_data, regions = segment(self, "s15")
        self.assertEqual(assigned_path_fraction(page_data, regions), 1.0)

    def test_s15_floor_plans_and_elevations_split_apart(self):
        # (900, 1400) sits inside the floor-plan column (R0 in the diagnosis
        # mapping, which held all 28 in-plan confirmed entities); (3000, 1400)
        # sits inside an elevation region (R3). The point of the retry is that
        # these end up in DIFFERENT regions; exact grown bboxes are not pinned
        # because _attach_text_spans legitimately widens them.
        _, regions = segment(self, "s15")

        def holder(x, y):
            return next(r for r in regions
                        if r.bbox[0] <= x <= r.bbox[2]
                        and r.bbox[1] <= y <= r.bbox[3])

        self.assertIsNot(holder(900.0, 1400.0), holder(3000.0, 1400.0))


if __name__ == "__main__":
    unittest.main()


class TestS17PlanElevationSeparation(unittest.TestCase):
    """Load-bearing golden for SEGMENT_MAX_DEPTH = 7: at 6 the first-floor
    plan and the front elevation of s17 came out as one leaf
    [1276,960,2808,1644] (the recursion budget ran out before the cell was
    ever offered to the clip edge or the tier-4 gutter that split it)."""

    ELEVATION = (1948.0, 960.0, 2808.0, 1640.0)
    PLAN = (1276.0, 1164.0, 1936.0, 1644.0)
    # Centres of the plan's westmost and eastmost confirmed doors (ground
    # truth s17: bboxes [1418,1323,1465,1370] and [1635,1328,1682,1375]) —
    # both must stay in the plan leaf, so the plan is not cut.
    PLAN_ANCHORS = ((1441.5, 1346.5), (1658.5, 1351.5))

    def _leaf_at(self, regions, x, y):
        for r in regions:
            if r.bbox[0] <= x <= r.bbox[2] and r.bbox[1] <= y <= r.bbox[3]:
                return tuple(r.bbox)
        return None

    def test_plan_and_elevation_are_separate_leaves(self):
        _, regions = segment(self, "s17")
        boxes = {tuple(r.bbox) for r in regions}
        self.assertIn(self.ELEVATION, boxes)
        self.assertIn(self.PLAN, boxes)

    def test_plan_anchors_share_one_leaf(self):
        _, regions = segment(self, "s17")
        leaves = {self._leaf_at(regions, x, y) for x, y in self.PLAN_ANCHORS}
        self.assertEqual(leaves, {self.PLAN})
