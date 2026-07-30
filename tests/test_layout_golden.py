"""Golden segmentation results on the checked-in reference PDFs.

Measured 2026-07-28. A failure here means segmentation behaviour changed on a
real sheet — investigate before touching the expected numbers.
"""
import os
import unittest

import fitz

from extraction.extractor import extract_page
from layout import qualifying_clip_rects, segment_page
from layout.occupancy import build_ink_map, is_page_spanning

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def segment(pdf_name, page_index=0, use_clips=True):
    path = os.path.join(REPO, pdf_name)
    doc = fitz.open(path)
    page_data = extract_page(doc, page_index)
    clips = qualifying_clip_rects(doc[page_index], page_data) if use_clips else []
    regions = segment_page(page_data, clips)
    doc.close()
    return page_data, regions


class TestGoldenSegmentation(unittest.TestCase):
    def test_floor_plans_splits_into_two_regions(self):
        page_data, regions = segment("floor-plans.pdf")
        self.assertEqual(len(regions), 2)

    def test_floor_plans_assigns_every_path(self):
        page_data, regions = segment("floor-plans.pdf")
        self.assertEqual(sum(r.path_count for r in regions), len(page_data.paths))

    def test_floor_plans_captions_merged_so_titles_are_inside_regions(self):
        page_data, regions = segment("floor-plans.pdf")
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
        _, regions = segment("5-1133-WD03.pdf")
        self.assertEqual(len(regions), 1)


class TestSpanFilterIsLoadBearing(unittest.TestCase):
    """This sheet carries full-page border rules. With the span filter applied
    the ink map has no page-spanning rows and the sheet splits into 13 regions.
    The counterfactual — 0 regions with the filter disabled — was measured on
    2026-07-28 but cannot be asserted here: build_ink_map applies the filter
    unconditionally, and adding a production parameter purely for this test
    was rejected as over-building."""

    PDF = os.path.join(REPO, "plans",
                       "LOCATION_PLAN__BLOCK_PLAN__EXISTING_PLANS_AND_ELEVATIONS-2682241.pdf")

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_sheet_has_page_spanning_primitives(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        spanning = [
            p for p in page_data.paths
            if is_page_spanning(p, page_data.width_px, page_data.height_px)
        ]
        self.assertGreater(len(spanning), 0)

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_sheet_splits_into_many_regions_with_the_filter(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        regions = segment_page(page_data)
        self.assertEqual(len(regions), 13)

    @unittest.skipUnless(os.path.exists(PDF), "sample sheet not present")
    def test_ink_map_has_no_page_spanning_rows(self):
        doc = fitz.open(self.PDF)
        page_data = extract_page(doc, 0)
        doc.close()
        ink = build_ink_map(page_data)
        spanning_rows = sum(
            1 for r in range(ink.rows) if sum(ink.bins[r]) > 0.9 * ink.cols
        )
        self.assertEqual(spanning_rows, 0,
                         "span filter should have removed full-width border rules")


if __name__ == "__main__":
    unittest.main()
