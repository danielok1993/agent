"""Extraction puts geometry in the same frame as the declared page size.

page.get_drawings() and page.get_text() return UNROTATED mediabox coordinates,
while page.rect — the source of width_px/height_px — and the render both honour
/Rotate. Region segmentation sizes its grid from width_px/height_px and silently
discards every mark outside it, so a frame mismatch deletes drawing.

page.get_image_bbox() is the exception: it already honours /Rotate, so images
take the scale only. Every test here builds its own rotated PDF in a tempdir —
the checked-out repo carries no rotated sample sheet, so real-sheet coverage
would silently skip everywhere but the machine that wrote it.
"""
import math
import os
import shutil
import tempfile
import unittest

import fitz

from extraction.extractor import (
    SCALE, extract_page, normalize_bbox, normalize_point, page_transform,
    transform_scale,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROTATED_SHEET = os.path.join(REPO, "plans", "PROPOSED_FLOOR_AND_ELEVATIONS-1326086.pdf")

# The synthetic sheet, in unrotated mediabox points.
PAGE_W_PT, PAGE_H_PT = 200.0, 400.0
LINE_A = ((10.0, 20.0), (60.0, 20.0))     # horizontal, length 50
LINE_B = ((30.0, 120.0), (30.0, 200.0))   # vertical, length 80
TEXT_AT = (20.0, 300.0)
IMAGE_RECT = (100.0, 40.0, 160.0, 90.0)   # 60 x 50, deliberately not square
PEN_WIDTH = 2.0


def write_rotated_pdf(directory, rotation):
    """A saved 200x400pt PDF with two lines, a word and an image, rotated.

    Saved and reopened rather than built in memory so the test exercises a real
    /Rotate entry, the way a CAD export delivers one.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
    page.draw_line(fitz.Point(*LINE_A[0]), fitz.Point(*LINE_A[1]), width=PEN_WIDTH)
    page.draw_line(fitz.Point(*LINE_B[0]), fitz.Point(*LINE_B[1]), width=PEN_WIDTH)
    page.insert_text(fitz.Point(*TEXT_AT), "PLAN", fontsize=12)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8))
    pix.set_rect(pix.irect, (200, 30, 30))
    page.insert_image(fitz.Rect(*IMAGE_RECT), pixmap=pix)
    page.set_rotation(rotation)
    path = os.path.join(directory, f"rot{rotation}.pdf")
    doc.save(path)
    doc.close()
    return path


class RotatedPdfTestCase(unittest.TestCase):
    """Builds all four rotations once; each test reopens what it needs."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.paths = {r: write_rotated_pdf(cls.tmp, r) for r in (0, 90, 180, 270)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def page_data(self, rotation):
        doc = fitz.open(self.paths[rotation])
        try:
            self.assertEqual(doc[0].rotation, rotation)
            return extract_page(doc, 0)
        finally:
            doc.close()

    def transform(self, rotation):
        doc = fitz.open(self.paths[rotation])
        try:
            return page_transform(doc[0], SCALE)
        finally:
            doc.close()


class TestPageTransform(RotatedPdfTestCase):
    def test_no_rotation_is_exactly_the_old_scalar_multiply(self):
        t = self.transform(0)
        self.assertEqual(t, (SCALE, 0.0, 0.0, SCALE, 0.0, 0.0))
        # Not merely close: the reference PDFs are rotation 0, and a last-ulp
        # drift would move every coordinate on every unrotated sheet.
        self.assertEqual(normalize_point((123.456, 789.012), t),
                         (123.456 * SCALE, 789.012 * SCALE))

    def test_rotation_is_a_quarter_turn_not_a_resize(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                self.assertAlmostEqual(transform_scale(self.transform(rotation)),
                                       SCALE, places=12)

    def test_a_rotated_bbox_comes_back_normalized(self):
        for rotation in (90, 180, 270):
            with self.subTest(rotation=rotation):
                x0, y0, x1, y1 = normalize_bbox((10.0, 20.0, 60.0, 40.0),
                                                self.transform(rotation))
                self.assertLess(x0, x1)
                self.assertLess(y0, y1)


class TestExtractPageFrame(RotatedPdfTestCase):
    def assert_all_geometry_inside_the_page(self, pd):
        """Every primitive, span AND image must land in the declared frame."""
        self.assertGreater(len(pd.paths), 0)
        for p in pd.paths:
            for x, y in p.points:
                self.assertTrue(-1 <= x <= pd.width_px + 1, f"path x={x} vs {pd.width_px}")
                self.assertTrue(-1 <= y <= pd.height_px + 1, f"path y={y} vs {pd.height_px}")
        self.assertGreater(len(pd.text_spans), 0)
        for s in pd.text_spans:
            self.assertTrue(-1 <= s.bbox[0] and s.bbox[2] <= pd.width_px + 1, f"span {s.bbox}")
            self.assertTrue(-1 <= s.bbox[1] and s.bbox[3] <= pd.height_px + 1, f"span {s.bbox}")
        self.assertGreater(len(pd.images), 0)
        for i in pd.images:
            self.assertTrue(-1 <= i.bbox[0] and i.bbox[2] <= pd.width_px + 1, f"image {i.bbox}")
            self.assertTrue(-1 <= i.bbox[1] and i.bbox[3] <= pd.height_px + 1, f"image {i.bbox}")

    def test_every_rotation_keeps_geometry_inside_the_declared_page(self):
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                pd = self.page_data(rotation)
                self.assert_all_geometry_inside_the_page(pd)
                turned = rotation in (90, 270)
                self.assertAlmostEqual(
                    pd.width_px, (PAGE_H_PT if turned else PAGE_W_PT) * SCALE)
                self.assertAlmostEqual(
                    pd.height_px, (PAGE_W_PT if turned else PAGE_H_PT) * SCALE)

    def test_images_are_scaled_but_never_rotated_twice(self):
        # get_image_bbox already honours /Rotate. Applying the rotation on top
        # sends the box off-page (measured on 1326087, rot 270: the correct
        # (2140.8, 45.3, 2436.3, 299.3) became (45.3, -682.2, 299.3, -386.7)).
        expected_sides = {round((IMAGE_RECT[2] - IMAGE_RECT[0]) * SCALE, 3),
                          round((IMAGE_RECT[3] - IMAGE_RECT[1]) * SCALE, 3)}
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                img = self.page_data(rotation).images[0]
                sides = {round(img.bbox[2] - img.bbox[0], 3),
                         round(img.bbox[3] - img.bbox[1], 3)}
                self.assertEqual(sides, expected_sides)

    def test_rotation_does_not_change_pen_width(self):
        widths = {r: {p.stroke_width for p in self.page_data(r).paths}
                  for r in (0, 90, 180, 270)}
        for rotation, seen in widths.items():
            with self.subTest(rotation=rotation):
                self.assertEqual(seen, {PEN_WIDTH * SCALE})

    def test_bboxes_are_never_inverted(self):
        for rotation in (0, 90, 180, 270):
            pd = self.page_data(rotation)
            with self.subTest(rotation=rotation):
                for p in pd.paths:
                    self.assertLessEqual(p.bbox[0], p.bbox[2])
                    self.assertLessEqual(p.bbox[1], p.bbox[3])
                for s in pd.text_spans:
                    self.assertLessEqual(s.bbox[0], s.bbox[2])
                    self.assertLessEqual(s.bbox[1], s.bbox[3])
                for i in pd.images:
                    self.assertLessEqual(i.bbox[0], i.bbox[2])
                    self.assertLessEqual(i.bbox[1], i.bbox[3])

    def test_lines_keep_their_length_under_every_rotation(self):
        for rotation in (0, 90, 180, 270):
            pd = self.page_data(rotation)
            lengths = sorted(
                round(math.hypot(p.points[-1][0] - p.points[0][0],
                                 p.points[-1][1] - p.points[0][1]), 3)
                for p in pd.paths if p.item_type == "l"
            )
            with self.subTest(rotation=rotation):
                self.assertEqual(lengths, [round(50.0 * SCALE, 3),
                                           round(80.0 * SCALE, 3)])

    def test_point_order_survives_the_transform(self):
        # LINE_A runs left-to-right; a 270 turn makes it vertical running
        # downward-to-upward. Heuristics read points[0]/points[-1], so the
        # endpoints must map in place, never swap.
        pd = self.page_data(270)
        line_a = min((p for p in pd.paths if p.item_type == "l"),
                     key=lambda p: p.bbox[1])
        self.assertEqual(len(line_a.points), 2)
        # (10,20)->(60,20) under x'=y*S, y'=(200-x)*S becomes
        # (20S, 190S)->(20S, 140S): same x, decreasing y.
        self.assertAlmostEqual(line_a.points[0][0], 20.0 * SCALE, places=3)
        self.assertAlmostEqual(line_a.points[0][1], 190.0 * SCALE, places=3)
        self.assertAlmostEqual(line_a.points[-1][0], 20.0 * SCALE, places=3)
        self.assertAlmostEqual(line_a.points[-1][1], 140.0 * SCALE, places=3)

    @unittest.skipUnless(os.path.exists(ROTATED_SHEET), "sample sheet not present")
    def test_real_rotated_sheet_lands_entirely_inside_the_render_frame(self):
        doc = fitz.open(ROTATED_SHEET)
        try:
            self.assertEqual(doc[0].rotation, 270)
            pd = extract_page(doc, 0)
        finally:
            doc.close()
        for p in pd.paths:
            for x, y in p.points:
                self.assertTrue(-1 <= x <= pd.width_px + 1)
                self.assertTrue(-1 <= y <= pd.height_px + 1)
        for i in pd.images:
            self.assertTrue(-1 <= i.bbox[0] and i.bbox[2] <= pd.width_px + 1)
            self.assertTrue(-1 <= i.bbox[1] and i.bbox[3] <= pd.height_px + 1)


if __name__ == "__main__":
    unittest.main()
