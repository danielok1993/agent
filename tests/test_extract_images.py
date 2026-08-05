"""extract_images characterization: multi-image and multi-display pages.

get_images(full=True) yields one row per image *reference name*, so one xref
displayed twice arrives as two rows with distinct bboxes. The single-pass
get_image_info implementation must preserve that per-instance mapping, not
collapse instances onto their shared xref.
"""
import os
import shutil
import tempfile
import unittest

import fitz

from extraction.extractor import SCALE, extract_images

RECT_A = (10.0, 10.0, 50.0, 40.0)
RECT_B1 = (60.0, 60.0, 100.0, 100.0)
RECT_B2 = (120.0, 200.0, 180.0, 260.0)
PAGE_W_PT, PAGE_H_PT = 200.0, 400.0


class TestExtractImagesInstances(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        doc = fitz.open()
        page = doc.new_page(width=PAGE_W_PT, height=PAGE_H_PT)
        pix_a = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8))
        pix_a.set_rect(pix_a.irect, (200, 30, 30))
        pix_b = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 16, 8))
        pix_b.set_rect(pix_b.irect, (30, 30, 200))
        # keep_proportion=False: the displayed bbox IS the target rect, so the
        # expected constants below don't depend on letterboxing arithmetic.
        page.insert_image(fitz.Rect(*RECT_A), pixmap=pix_a, keep_proportion=False)
        xref_b = page.insert_image(fitz.Rect(*RECT_B1), pixmap=pix_b, keep_proportion=False)
        page.insert_image(fitz.Rect(*RECT_B2), xref=xref_b, keep_proportion=False)
        cls.path = os.path.join(cls.tmp, "multi.pdf")
        doc.save(cls.path)
        doc.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def extract(self):
        doc = fitz.open(self.path)
        try:
            return extract_images(doc[0], doc)
        finally:
            doc.close()

    def test_each_displayed_instance_gets_its_own_bbox(self):
        images = self.extract()
        got = sorted((round(i.bbox[0], 3), round(i.bbox[1], 3),
                      round(i.bbox[2], 3), round(i.bbox[3], 3)) for i in images)
        expected = sorted(tuple(round(v * SCALE, 3) for v in rect)
                          for rect in (RECT_A, RECT_B1, RECT_B2))
        self.assertEqual(got, expected)

    def test_shared_xref_instances_keep_shared_pixel_size(self):
        images = self.extract()
        by_size = sorted((i.width, i.height) for i in images)
        self.assertEqual(by_size, [(8, 8), (16, 8), (16, 8)])

    def test_pixel_area_is_raw_bbox_over_page_area(self):
        images = self.extract()
        page_area = PAGE_W_PT * PAGE_H_PT
        areas = sorted(round(i.pixel_area, 6) for i in images)
        expected = sorted(
            round((r[2] - r[0]) * (r[3] - r[1]) / page_area, 6)
            for r in (RECT_A, RECT_B1, RECT_B2)
        )
        self.assertEqual(areas, expected)


if __name__ == "__main__":
    unittest.main()
