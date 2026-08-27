"""PDF line width 0 is a pen, not the absence of one.

PDF 32000-1 §8.4.3.2: "A line width of 0 shall denote the thinnest line that
can be rendered at device resolution: 1 device pixel wide." CAD exporters that
plot every lineweight as the device-minimum line (s05 and s12 are drawn
entirely this way — 12,958 / 17,168 stroked drawings, every one at width 0)
produce a single-pen sheet whose render shows 1px linework everywhere. The
extractor must record that pen at its device width in the 150-DPI space
(1.0 px), not as 0.0 — a 0.0 pen is below every stroke gate at once (walls.py's
strong tier needs >= 0.5, its hairline tier needs > 0), so the whole plan
contributed no wall faces and s05 detected no rooms at all.

A fill-only path (no stroke colour) has no pen and stays at 0.0 — its outline
is a fill boundary, which _stroke_is_visible already treats as area.
"""
import os
import shutil
import tempfile
import unittest

import fitz

from extraction.extractor import SCALE, extract_paths


class ZeroWidthStrokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _page(self):
        # Written as a raw content stream: PyMuPDF's Shape helpers omit the
        # `w` operator for width=0 (so the 1.0 default applies) and cannot
        # produce the `0 w` a CAD exporter writes.
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        fitz.TOOLS._insert_contents(page, (
            b"q 0 w 0 0 0 RG 10 180 m 90 180 l S Q\n"       # zero-width stroke
            b"q 2 w 0 0 0 RG 10 140 m 90 140 l S Q\n"       # 2pt stroke
            b"q 0 w 0 0 0 rg 10 60 80 40 re f Q\n"          # fill only, no pen
        ), 1)
        path = os.path.join(self.tmp, "w0.pdf")
        doc.save(path)
        doc.close()
        return fitz.open(path)[0]

    def test_zero_width_stroke_is_one_device_pixel(self):
        paths = extract_paths(self._page())
        by_y = {round(p.points[0][1] / SCALE): p for p in paths if p.item_type == "l"}
        self.assertAlmostEqual(by_y[20].stroke_width, 1.0, places=6)
        self.assertAlmostEqual(by_y[60].stroke_width, 2.0 * SCALE, places=6)

    def test_fill_only_path_keeps_no_pen(self):
        paths = extract_paths(self._page())
        filled = [p for p in paths if p.fill is not None]
        self.assertTrue(filled)
        for p in filled:
            self.assertIsNone(p.color)
            self.assertEqual(p.stroke_width, 0.0)


if __name__ == "__main__":
    unittest.main()
