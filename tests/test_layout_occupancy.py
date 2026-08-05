"""Ink occupancy map tests (layout/occupancy.py)."""
import unittest

from models import PageData, PathPrimitive, TextSpan
from layout.occupancy import InkMap, build_ink_map, is_page_spanning

PAGE_W, PAGE_H = 400.0, 300.0


def path(idx, points, item_type="l"):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=points,
    )


def span(text, bbox):
    return TextSpan(text=text, bbox=bbox, font="Helvetica", size=10.0,
                    color=0, block_no=0, line_no=0)


def page(paths=(), text_spans=()):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                    paths=list(paths), text_spans=list(text_spans))


class TestPageSpanning(unittest.TestCase):
    def test_full_width_hairline_is_page_spanning(self):
        border = path(0, [(0.0, 10.0), (PAGE_W, 10.0)])
        self.assertTrue(is_page_spanning(border, PAGE_W, PAGE_H))

    def test_full_height_hairline_is_page_spanning(self):
        border = path(0, [(10.0, 0.0), (10.0, PAGE_H)])
        self.assertTrue(is_page_spanning(border, PAGE_W, PAGE_H))

    def test_half_width_line_is_not_page_spanning(self):
        wall = path(0, [(0.0, 10.0), (PAGE_W / 2, 10.0)])
        self.assertFalse(is_page_spanning(wall, PAGE_W, PAGE_H))


class TestBuildInkMap(unittest.TestCase):
    def test_map_dimensions_follow_page_and_bin_size(self):
        ink = build_ink_map(page(), bin_px=4)
        self.assertEqual(ink.bin_px, 4)
        self.assertEqual(ink.cols, int(PAGE_W / 4) + 1)
        self.assertEqual(ink.rows, int(PAGE_H / 4) + 1)
        self.assertEqual(len(ink.bins), ink.rows)
        self.assertEqual(len(ink.bins[0]), ink.cols)

    def test_line_marks_bins_along_its_length(self):
        ink = build_ink_map(page([path(0, [(40.0, 100.0), (80.0, 100.0)])]), bin_px=4)
        row = 100 // 4
        self.assertEqual(ink.bins[row][40 // 4], 1)
        self.assertEqual(ink.bins[row][60 // 4], 1)
        self.assertEqual(ink.bins[row][80 // 4], 1)
        self.assertEqual(ink.bins[row][120 // 4], 0)

    def test_page_spanning_primitive_is_excluded_from_the_map(self):
        border = path(0, [(0.0, 100.0), (PAGE_W, 100.0)])
        ink = build_ink_map(page([border]), bin_px=4)
        self.assertEqual(sum(sum(r) for r in ink.bins), 0)

    def test_rect_closing_edge_is_marked(self):
        # points for a "re" run corner-to-corner without repeating the first
        pts = [(40.0, 40.0), (80.0, 40.0), (80.0, 80.0), (40.0, 80.0)]
        ink = build_ink_map(page([path(0, pts, item_type="re")]), bin_px=4)
        # the closing edge is the left side, x=40, between y=40 and y=80
        self.assertEqual(ink.bins[60 // 4][40 // 4], 1)

    def test_text_span_bbox_is_filled(self):
        ink = build_ink_map(page(text_spans=[span("PLAN", (100.0, 200.0, 140.0, 212.0))]),
                            bin_px=4)
        self.assertEqual(ink.bins[204 // 4][120 // 4], 1)

    def test_diagonal_line_is_sampled_not_bbox_filled(self):
        ink = build_ink_map(page([path(0, [(40.0, 40.0), (80.0, 80.0)])]), bin_px=4)
        self.assertEqual(ink.bins[60 // 4][60 // 4], 1)   # on the diagonal
        self.assertEqual(ink.bins[44 // 4][76 // 4], 0)   # bbox corner, off the line


if __name__ == "__main__":
    unittest.main()
