import re
import tempfile
import unittest
from pathlib import Path

import fitz

from extraction.renderer import render_page_svg, SCALE


class TestRenderPageSvg(unittest.TestCase):
    def _svg(self, page_setup) -> str:
        doc = fitz.open()
        page = doc.new_page(width=400, height=800)
        page.draw_line((10, 10), (100, 10))
        page_setup(page)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "page.svg"
            render_page_svg(doc, 0, str(out))
            return out.read_text(encoding="utf-8")

    def _frame(self, svg: str) -> tuple[float, float]:
        m = re.search(r'width="([\d.]+)" height="([\d.]+)"', svg)
        self.assertIsNotNone(m, svg[:200])
        return float(m.group(1)), float(m.group(2))

    def test_svg_is_written_in_150dpi_pixel_space(self):
        svg = self._svg(lambda page: None)
        self.assertTrue(svg.lstrip().startswith("<svg"))
        # The SVG's user units are render.png's pixels: page points x 150/72.
        w, h = self._frame(svg)
        self.assertAlmostEqual(w, 400 * SCALE, delta=0.01)
        self.assertAlmostEqual(h, 800 * SCALE, delta=0.01)

    def test_page_rotation_is_baked_in_like_the_raster(self):
        # /Rotate 90 swaps the frame, exactly as get_pixmap does — a consumer
        # overlaying takeoff.json bboxes must not re-apply the rotation.
        svg = self._svg(lambda page: page.set_rotation(90))
        w, h = self._frame(svg)
        self.assertAlmostEqual(w, 800 * SCALE, delta=0.01)
        self.assertAlmostEqual(h, 400 * SCALE, delta=0.01)


if __name__ == "__main__":
    unittest.main()
