"""Recursive XY-cut tests (layout/segmenter.py)."""
import unittest

from models import PageData, PathPrimitive
from layout.occupancy import build_ink_map
from layout.segmenter import _trim, _widest_gap, _clip_cut, _xy_cut

PAGE_W, PAGE_H = 400.0, 400.0
BIN = 4


def block(idx, x0, y0, x1, y1):
    """A solid-ish blob: a horizontal line every 4px so every bin row is inked."""
    return [
        PathPrimitive(
            path_index=idx + i, item_type="l",
            bbox=(x0, y, x1, y), color=(0.0, 0.0, 0.0), fill=None,
            stroke_width=1.5, dashes="", layer=None,
            points=[(x0, y), (x1, y)],
        )
        for i, y in enumerate(range(int(y0), int(y1), 4))
    ]


def page(paths):
    return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H, paths=list(paths))


def cut(page_data, min_gutter_px=20, cut_rows=frozenset(), cut_cols=frozenset()):
    ink = build_ink_map(page_data, bin_px=BIN)
    out = []
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, max(1, min_gutter_px // BIN),
            set(cut_rows), set(cut_cols), 0, out)
    return [(c0 * BIN, r0 * BIN, c1 * BIN, r1 * BIN) for r0, r1, c0, c1 in out]


class TestProfileHelpers(unittest.TestCase):
    def test_trim_strips_leading_and_trailing_zeros(self):
        self.assertEqual(_trim([0, 0, 3, 4, 0], 10), (12, 14))

    def test_widest_gap_finds_the_longest_internal_run_of_zeros(self):
        self.assertEqual(_widest_gap([5, 0, 0, 5, 0, 0, 0, 5], 0, 2), (4, 7))

    def test_widest_gap_ignores_runs_shorter_than_min_bins(self):
        self.assertIsNone(_widest_gap([5, 0, 5], 0, 2))

    def test_widest_gap_ignores_leading_and_trailing_zeros(self):
        self.assertIsNone(_widest_gap([0, 0, 0, 5, 0, 0, 0], 0, 3))

    def test_clip_cut_returns_a_position_with_ink_on_both_sides(self):
        self.assertEqual(_clip_cut([5, 5, 5, 5], 0, {2}), 2)

    def test_clip_cut_rejects_a_position_with_ink_on_one_side_only(self):
        self.assertIsNone(_clip_cut([0, 0, 5, 5], 0, {1}))


class TestXYCut(unittest.TestCase):
    def test_single_blob_yields_one_region(self):
        boxes = cut(page(block(0, 40, 40, 200, 200)))
        self.assertEqual(len(boxes), 1)

    def test_two_blobs_split_by_a_wide_vertical_gutter(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 2)

    def test_two_blobs_split_by_a_wide_horizontal_gutter(self):
        paths = block(0, 40, 40, 200, 140) + block(500, 40, 250, 200, 360)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 2)

    def test_gap_narrower_than_the_threshold_does_not_split(self):
        # 8px gap between the two blobs, threshold 20px
        paths = block(0, 40, 40, 150, 200) + block(500, 158, 40, 300, 200)
        boxes = cut(page(paths))
        self.assertEqual(len(boxes), 1)

    def test_regions_are_trimmed_to_their_ink(self):
        boxes = cut(page(block(0, 100, 100, 200, 200)))
        x0, y0, x1, y1 = boxes[0]
        self.assertGreaterEqual(x0, 96)
        self.assertLessEqual(x1, 208)
        self.assertGreaterEqual(y0, 96)
        self.assertLessEqual(y1, 208)

    def test_clip_edge_splits_when_no_gutter_exists(self):
        # One continuous blob: no gutter anywhere, so only a clip edge can cut it.
        paths = block(0, 40, 40, 360, 200)
        without = cut(page(paths))
        self.assertEqual(len(without), 1)
        with_clip = cut(page(paths), cut_cols={200 // BIN})
        self.assertEqual(len(with_clip), 2)

    def test_gutter_is_preferred_over_a_clip_edge(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        # A clip edge in a silly place must not win over the real gutter: the
        # FIRST cut is the gutter, so no region straddles x=200. Clip edges may
        # still subdivide within a side — that is
        # test_clip_edge_splits_when_no_gutter_exists.
        boxes = cut(page(paths), cut_cols={100 // BIN})
        self.assertTrue(all(b[2] <= 200 or b[0] >= 200 for b in boxes))
        self.assertTrue(any(b[0] >= 200 for b in boxes))


if __name__ == "__main__":
    unittest.main()
