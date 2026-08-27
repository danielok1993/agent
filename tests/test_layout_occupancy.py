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


class TestIncludeTextFlag(unittest.TestCase):
    def _page(self):
        span = TextSpan(text="BRIDGE", bbox=(100.0, 100.0, 180.0, 120.0),
                        font="Helvetica", size=10.0, color=0,
                        block_no=0, line_no=0)
        return PageData(page_number=1, width_px=400.0, height_px=400.0,
                        paths=[], text_spans=[span])

    def test_text_spans_ink_by_default(self):
        ink = build_ink_map(self._page(), bin_px=4)
        self.assertEqual(ink.bins[int(110 / 4)][int(140 / 4)], 1)

    def test_include_text_false_leaves_text_bins_empty(self):
        ink = build_ink_map(self._page(), bin_px=4, include_text=False)
        self.assertEqual(sum(sum(row) for row in ink.bins), 0)



class QuadPerimeterTests(unittest.TestCase):
    """A `qu` item's four points arrive in PyMuPDF Quad order — [ul, ur, ll,
    lr] — NOT perimeter order. Joining them sequentially draws ur->ll and
    lr->ul: two diagonals across the rectangle's interior instead of its top
    and bottom edges. Measured on s06: the 2344x1544px drawing frame (path
    4849) inked two page-wide diagonals through every drawing on the sheet,
    which is part of why its elevations and plans never split. The perimeter
    is [0, 1, 3, 2] for every quad, skewed ones included (detection/walls.py
    already reorders the same way before ring-building)."""

    def _qu(self, pts):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return PathPrimitive(
            path_index=0, item_type="qu",
            bbox=(min(xs), min(ys), max(xs), max(ys)), color=(0.0, 0.0, 0.0),
            fill=None, stroke_width=1.0, dashes="", layer=None, points=list(pts),
        )

    def _ink(self, ink, x, y):
        return ink.bins[int(y / ink.bin_px)][int(x / ink.bin_px)]

    def test_axis_quad_inks_its_edges_not_its_diagonals(self):
        # ul, ur, ll, lr of a 400x200 rectangle at (100,100)
        p = self._qu([(100, 100), (500, 100), (100, 300), (500, 300)])
        ink = build_ink_map(PageData(page_number=1, width_px=800, height_px=600, paths=[p]))
        for x in (150, 300, 450):
            self.assertTrue(self._ink(ink, x, 100), "top edge missing")
            self.assertTrue(self._ink(ink, x, 300), "bottom edge missing")
        self.assertTrue(self._ink(ink, 100, 200) and self._ink(ink, 500, 200))
        # Interior stays empty — no diagonal ink, in particular at the centre.
        self.assertFalse(self._ink(ink, 300, 200), "diagonal ink at the centre")
        self.assertFalse(self._ink(ink, 200, 150) or self._ink(ink, 400, 250))

    def test_skewed_quad_follows_the_same_perimeter(self):
        # A parallelogram: ul, ur, ll, lr with the bottom edge shifted right.
        p = self._qu([(100, 100), (500, 100), (200, 300), (600, 300)])
        ink = build_ink_map(PageData(page_number=1, width_px=800, height_px=600, paths=[p]))
        self.assertTrue(self._ink(ink, 300, 100) and self._ink(ink, 400, 300))
        self.assertTrue(self._ink(ink, 150, 200), "left edge ul->ll missing")
        self.assertTrue(self._ink(ink, 550, 200), "right edge ur->lr missing")
        # The two diagonals' midpoints coincide at the centroid (350, 200).
        self.assertFalse(self._ink(ink, 350, 200), "diagonal ink at the centroid")


class NestedFrameTests(unittest.TestCase):
    """Sheet furniture nested inside the page frame — a drawing frame or a
    title-block partition drawn as an unfilled rectangle with at least
    FRAME_NESTED_MIN_CORNERS corners on the page frame's boundary — must not
    block gutters. Measured on s06: the outer frame (path 4849, 2344x1544px,
    page-spanning) encloses an inner frame (path 4852, [63.6,106.5]-
    [2132.1,1395.0]) whose three corners sit 0.00px off the outer boundary;
    it is 0.86 of the page wide, under SEGMENT_SPAN_FRAC, and glued the
    elevations to the plans below them."""

    W, H = 2480.0, 1754.0

    def _rect(self, idx, x0, y0, x1, y1, fill=None):
        # Real PyMuPDF Quad order: ul, ur, ll, lr.
        return PathPrimitive(
            path_index=idx, item_type="qu", bbox=(x0, y0, x1, y1),
            color=(0.0, 0.0, 0.0), fill=fill, stroke_width=1.0, dashes="",
            layer=None, points=[(x0, y0), (x1, y0), (x0, y1), (x1, y1)],
        )

    def _frame(self):
        return self._rect(0, 60.0, 100.0, 2400.0, 1650.0)   # page-spanning

    def _has_ink(self, ink, x, y):
        return bool(ink.bins[int(y / ink.bin_px)][int(x / ink.bin_px)])

    def _page(self, *paths):
        return PageData(page_number=1, width_px=self.W, height_px=self.H, paths=list(paths))

    def test_nested_frame_with_three_corners_on_the_frame_is_transparent(self):
        inner = self._rect(1, 60.0, 100.0, 2130.0, 1390.0)
        ink = build_ink_map(self._page(self._frame(), inner))
        self.assertFalse(self._has_ink(ink, 1000.0, 1390.0), "inner frame bottom edge inked")
        self.assertFalse(self._has_ink(ink, 2130.0, 800.0), "inner frame right edge inked")

    def test_rect_touching_the_frame_on_one_side_stays_ink(self):
        # Two corners on the frame (a drawing box hugging the left border).
        box = self._rect(1, 60.0, 400.0, 900.0, 900.0)
        ink = build_ink_map(self._page(self._frame(), box))
        self.assertTrue(self._has_ink(ink, 500.0, 400.0))
        self.assertTrue(self._has_ink(ink, 900.0, 650.0))

    def test_filled_rect_never_becomes_furniture(self):
        block = self._rect(1, 60.0, 100.0, 2130.0, 1390.0, fill=(0.9, 0.9, 0.9))
        ink = build_ink_map(self._page(self._frame(), block))
        self.assertTrue(self._has_ink(ink, 1000.0, 1390.0))

    def test_large_drawing_enclosure_off_the_frame_stays_ink(self):
        # A big unfilled rectangle (a room outline, a table border) that does
        # not sit on the frame is content, however much it encloses.
        box = self._rect(1, 200.0, 300.0, 2200.0, 1500.0)
        ink = build_ink_map(self._page(self._frame(), box))
        self.assertTrue(self._has_ink(ink, 1000.0, 300.0))
        self.assertTrue(self._has_ink(ink, 200.0, 900.0))

    def test_corner_tolerance_is_tight(self):
        # Three corners 6px inside the frame: not on its boundary.
        inner = self._rect(1, 66.0, 106.0, 2130.0, 1390.0)
        ink = build_ink_map(self._page(self._frame(), inner))
        self.assertTrue(self._has_ink(ink, 1000.0, 1390.0))

    def test_without_a_page_frame_nothing_is_nested(self):
        inner = self._rect(1, 60.0, 100.0, 2130.0, 1390.0)
        ink = build_ink_map(self._page(inner))
        self.assertTrue(self._has_ink(ink, 1000.0, 1390.0))


if __name__ == "__main__":
    unittest.main()
