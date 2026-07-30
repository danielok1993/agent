"""Clip-rect gating tests (layout/clips.py)."""
import unittest

from models import PageData, PathPrimitive
from layout.clips import qualifying_clip_rects_from_boxes, clip_cut_positions

PAGE_W, PAGE_H = 1000.0, 1000.0


def dot(idx, x, y):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x, y, x + 1, y + 1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.0,
        dashes="", layer=None, points=[(x, y), (x + 1, y + 1)],
    )


def page_with(paths):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=list(paths))


class TestClipGating(unittest.TestCase):
    def setUp(self):
        # 100 paths: 40 inside the drawing clip, 1 inside the annotation clip,
        # 59 elsewhere.
        paths = [dot(i, 110 + (i % 20), 110 + (i % 20)) for i in range(40)]
        paths += [dot(100, 700, 700)]
        paths += [dot(200 + i, 400 + (i % 30), 800) for i in range(59)]
        self.page = page_with(paths)

    def test_drawing_clip_qualifies(self):
        drawing = (100.0, 100.0, 300.0, 300.0)   # holds 40/100 paths = 40%
        self.assertIn(drawing, qualifying_clip_rects_from_boxes([drawing], self.page))

    def test_annotation_clip_is_rejected_on_ink_share(self):
        annot = (690.0, 690.0, 730.0, 730.0)     # holds 1/100 paths = 1%
        self.assertEqual(qualifying_clip_rects_from_boxes([annot], self.page), [])

    def test_whole_sheet_clip_is_rejected_on_page_area(self):
        sheet = (0.0, 0.0, 950.0, 950.0)         # 90% of the page
        self.assertEqual(qualifying_clip_rects_from_boxes([sheet], self.page), [])

    def test_duplicate_boxes_are_returned_once(self):
        drawing = (100.0, 100.0, 300.0, 300.0)
        got = qualifying_clip_rects_from_boxes([drawing, drawing, drawing], self.page)
        self.assertEqual(len(got), 1)

    def test_degenerate_box_is_rejected(self):
        self.assertEqual(
            qualifying_clip_rects_from_boxes([(100.0, 100.0, 100.0, 300.0)], self.page), [])

    def test_page_with_no_paths_qualifies_nothing(self):
        empty = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H)
        self.assertEqual(
            qualifying_clip_rects_from_boxes([(10.0, 10.0, 200.0, 200.0)], empty), [])


class TestClipCutPositions(unittest.TestCase):
    def test_edges_become_bin_indices_on_both_axes(self):
        rows, cols = clip_cut_positions([(40.0, 80.0, 200.0, 240.0)], bin_px=4)
        self.assertEqual(cols, {10, 50})
        self.assertEqual(rows, {20, 60})


if __name__ == "__main__":
    unittest.main()
