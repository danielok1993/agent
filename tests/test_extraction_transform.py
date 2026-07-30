"""Extraction puts geometry in the same frame as the declared page size.

page.get_drawings() and page.get_text() return UNROTATED mediabox coordinates,
while page.rect — the source of width_px/height_px — and the render both honour
/Rotate. Region segmentation sizes its grid from width_px/height_px and silently
discards every mark outside it, so a frame mismatch deletes drawing.
"""
import os
import unittest

import fitz

from extraction.extractor import (
    SCALE, extract_page, normalize_bbox, normalize_point, page_transform,
    transform_scale,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTATED_SHEET = os.path.join(REPO, "plans", "PROPOSED_FLOOR_AND_ELEVATIONS-1326086.pdf")


def rotated_doc(rotation):
    """A 200x400pt page with one stroked line and one word, rotated."""
    doc = fitz.open()
    page = doc.new_page(width=200, height=400)
    page.draw_line(fitz.Point(10, 20), fitz.Point(60, 20), width=2.0)
    page.insert_text(fitz.Point(20, 300), "PLAN", fontsize=12)
    page.set_rotation(rotation)
    return doc


class TestPageTransform(unittest.TestCase):
    def test_no_rotation_is_exactly_the_old_scalar_multiply(self):
        doc = rotated_doc(0)
        t = page_transform(doc[0], SCALE)
        doc.close()
        self.assertEqual(t, (SCALE, 0.0, 0.0, SCALE, 0.0, 0.0))
        # Not merely close: the reference PDFs are rotation 0, and a last-ulp
        # drift would move every coordinate on every unrotated sheet.
        self.assertEqual(normalize_point((123.456, 789.012), t),
                         (123.456 * SCALE, 789.012 * SCALE))

    def test_rotation_is_a_quarter_turn_not_a_resize(self):
        doc = rotated_doc(270)
        t = page_transform(doc[0], SCALE)
        doc.close()
        self.assertAlmostEqual(transform_scale(t), SCALE, places=12)

    def test_a_rotated_bbox_comes_back_normalized(self):
        doc = rotated_doc(270)
        t = page_transform(doc[0], SCALE)
        doc.close()
        x0, y0, x1, y1 = normalize_bbox((10.0, 20.0, 60.0, 40.0), t)
        self.assertLess(x0, x1)
        self.assertLess(y0, y1)


class TestExtractPageFrame(unittest.TestCase):
    def assert_all_geometry_inside_the_page(self, doc):
        pd = extract_page(doc, 0)
        self.assertGreater(len(pd.paths), 0)
        for p in pd.paths:
            for x, y in p.points:
                self.assertTrue(-1 <= x <= pd.width_px + 1, f"x={x} vs {pd.width_px}")
                self.assertTrue(-1 <= y <= pd.height_px + 1, f"y={y} vs {pd.height_px}")
        for s in pd.text_spans:
            self.assertTrue(-1 <= s.bbox[0] and s.bbox[2] <= pd.width_px + 1)
            self.assertTrue(-1 <= s.bbox[1] and s.bbox[3] <= pd.height_px + 1)
        return pd

    def test_every_rotation_keeps_geometry_inside_the_declared_page(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                doc = rotated_doc(rotation)
                try:
                    pd = self.assert_all_geometry_inside_the_page(doc)
                    self.assertAlmostEqual(pd.width_px, doc[0].rect.width * SCALE)
                    self.assertAlmostEqual(pd.height_px, doc[0].rect.height * SCALE)
                finally:
                    doc.close()

    def test_rotation_does_not_change_pen_width(self):
        widths = {}
        for rotation in (0, 90, 180, 270):
            doc = rotated_doc(rotation)
            widths[rotation] = extract_page(doc, 0).paths[0].stroke_width
            doc.close()
        self.assertEqual(set(widths.values()), {2.0 * SCALE})

    def test_bboxes_are_never_inverted(self):
        for rotation in (0, 90, 180, 270):
            doc = rotated_doc(rotation)
            pd = extract_page(doc, 0)
            doc.close()
            for p in pd.paths:
                self.assertLessEqual(p.bbox[0], p.bbox[2])
                self.assertLessEqual(p.bbox[1], p.bbox[3])
            for s in pd.text_spans:
                self.assertLessEqual(s.bbox[0], s.bbox[2])
                self.assertLessEqual(s.bbox[1], s.bbox[3])

    def test_point_order_survives_the_transform(self):
        doc = rotated_doc(270)
        pd = extract_page(doc, 0)
        doc.close()
        line = next(p for p in pd.paths if p.item_type == "l")
        # (10,20)->(60,20) under a 270 turn becomes a vertical run; heuristics
        # read points[0]/points[-1], so the endpoints must not swap.
        self.assertEqual(len(line.points), 2)
        self.assertGreater(line.points[0][1], line.points[-1][1])

    @unittest.skipUnless(os.path.exists(ROTATED_SHEET), "sample sheet not present")
    def test_real_rotated_sheet_lands_entirely_inside_the_render_frame(self):
        doc = fitz.open(ROTATED_SHEET)
        self.assertEqual(doc[0].rotation, 270)
        try:
            self.assert_all_geometry_inside_the_page(doc)
        finally:
            doc.close()


if __name__ == "__main__":
    unittest.main()
