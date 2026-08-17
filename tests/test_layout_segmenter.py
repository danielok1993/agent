"""Recursive XY-cut tests (layout/segmenter.py)."""
import unittest

from models import PageData, PathPrimitive, TextSpan, Region
from layout.occupancy import build_ink_map
from layout.segmenter import (
    _trim, _widest_gap, _clip_cut, _xy_cut,
    segment_page, page_fallback_region, _attach_text_spans,
)

PAGE_W, PAGE_H = 400.0, 400.0
CAPTION_PAGE_H = 700.0   # captions in these fixtures sit below y=340
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
    # Bare ints are edges with unbounded perpendicular extent — the tests
    # here exercise cut precedence, not extent gating.
    rows = {c if isinstance(c, tuple) else (c, 0, 10**9) for c in cut_rows}
    cols = {c if isinstance(c, tuple) else (c, 0, 10**9) for c in cut_cols}
    _xy_cut(ink, 0, ink.rows, 0, ink.cols, max(1, min_gutter_px // BIN),
            rows, cols, 0, out)
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
        self.assertEqual(_clip_cut([5, 5, 5, 5], 0, {(2, 0, 100)}, 0, 100), 2)

    def test_clip_cut_rejects_a_position_with_ink_on_one_side_only(self):
        self.assertIsNone(_clip_cut([0, 0, 5, 5], 0, {(1, 0, 100)}, 0, 100))

    def test_clip_cut_rejects_an_edge_whose_rect_misses_the_cell(self):
        # Edge extent 50..100 vs cell perpendicular span 0..40: no overlap.
        self.assertIsNone(_clip_cut([5, 5, 5, 5], 0, {(2, 50, 100)}, 0, 40))


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

    def test_clip_edges_cannot_preempt_the_gutter(self):
        # Six clip columns inside the LEFT blob, enough to exhaust
        # SEGMENT_MAX_DEPTH. An implementation that checked clip edges before
        # gutters would spend its whole depth budget on them and never reach
        # the real gutter, emitting one region spanning x=88..364. Cutting the
        # gutter first leaves the right blob its own region, so nothing
        # straddles x=200. Verified: this fixture fails for a
        # precedence-inverted _xy_cut and passes for this one.
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        boxes = cut(page(paths), cut_cols={12, 14, 16, 18, 20, 22})
        self.assertTrue(all(b[2] <= 200 or b[0] >= 200 for b in boxes))
        self.assertTrue(any(b[0] >= 200 for b in boxes))
        self.assertIn((248, 40, 364, 200), boxes)


class TestSegmentPage(unittest.TestCase):
    def _page_with_caption(self, caption_gap, caption_h):
        paths = block(0, 100, 100, 300, 300)
        y0 = 300.0 + caption_gap
        spans = [TextSpan(text="GROUND FLOOR PLAN", bbox=(120.0, y0, 280.0, y0 + caption_h),
                          font="Helvetica", size=10.0, color=0, block_no=0, line_no=0)]
        return PageData(page_number=1, width_px=PAGE_W, height_px=CAPTION_PAGE_H,
                        paths=paths, text_spans=spans)

    def test_caption_merges_into_its_drawing(self):
        regions = segment_page(self._page_with_caption(caption_gap=40, caption_h=20))
        self.assertEqual(len(regions), 1)
        self.assertGreater(regions[0].bbox[3], 300.0)

    def test_tall_text_block_does_not_merge(self):
        regions = segment_page(self._page_with_caption(caption_gap=40, caption_h=200))
        self.assertEqual(len(regions), 2)

    def test_distant_caption_does_not_merge(self):
        regions = segment_page(self._page_with_caption(caption_gap=200, caption_h=60))
        self.assertEqual(len(regions), 2)

    def test_regions_get_sequential_ids_and_unclassified_type(self):
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths))
        self.assertEqual([r.region_id for r in regions], ["region_0000", "region_0001"])
        self.assertTrue(all(r.region_type == "unclassified" for r in regions))
        self.assertTrue(all(r.source == "whitespace" for r in regions))
        self.assertTrue(all(r.path_count > 0 for r in regions))

    def test_source_records_clip_involvement(self):
        paths = block(0, 40, 40, 360, 200)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths),
                               clip_rects=[(40.0, 40.0, 200.0, 200.0)])
        self.assertTrue(all(r.source == "whitespace+clip" for r in regions))

    def test_clip_edge_only_cuts_cells_its_rect_overlaps(self):
        # Top: one continuous drawing crossing x=204 — no gutter anywhere.
        # Bottom: two drawings 8px apart (too narrow for a gutter), separated
        # only by the left edge of a clip rect hugging the bottom-right one.
        # That edge exists at y 250..360 only: it must cut the bottom pair and
        # must NOT split the top drawing (measured on s20/s11: the
        # location plan's clip edge sliced the floor plans at the top of the
        # sheet into two floor_plan regions each).
        paths = (block(0, 40, 40, 360, 200)
                 + block(500, 40, 250, 196, 360)
                 + block(700, 204, 250, 356, 360))
        regions = segment_page(
            PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                     paths=paths),
            clip_rects=[(204.0, 250.0, 360.0, 360.0)])
        self.assertEqual(len(regions), 3)
        top = [r for r in regions if r.bbox[1] < 240]
        self.assertEqual(len(top), 1)
        self.assertLess(top[0].bbox[0], 204.0)
        self.assertGreater(top[0].bbox[2], 204.0)
        bottom = [r for r in regions if r.bbox[1] >= 240]
        self.assertEqual(len(bottom), 2)

    def test_tiny_path_bearing_regions_fold_instead_of_dropping(self):
        # A sub-min-side leaf with ink folds into the nearest kept region: the
        # region count stays 1 but its bbox must grow to cover the leaf, so
        # filtering keeps the leaf's paths (dropping them is what pushed
        # s11 to 0.655 coverage and suppressed filtering entirely).
        paths = block(0, 40, 40, 200, 200) + block(500, 300, 300, 330, 330)
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths))
        self.assertEqual(len(regions), 1)
        self.assertGreaterEqual(regions[0].bbox[2], 330.0)
        self.assertGreaterEqual(regions[0].bbox[3], 330.0)

    def test_small_leaf_folds_into_the_nearest_kept_region(self):
        # Skinny dense strip between two drawings, nearer the left one
        # (measured on s11: 24px-wide strips holding 8,134 paths were
        # dropped, costing 34.5% of the sheet's coverage). The LEFT region
        # must absorb it; the right one must not stretch toward it.
        drawing = block(0, 40, 40, 200, 200)
        strip = block(500, 240, 40, 264, 200)      # 24px wide, gap 40 left
        second = block(900, 320, 40, 380, 200)     # gap 56 to the right
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=drawing + strip + second)
        regions = segment_page(pd)
        self.assertEqual(len(regions), 2)
        left = min(regions, key=lambda r: r.bbox[0])
        right = max(regions, key=lambda r: r.bbox[0])
        self.assertGreaterEqual(left.bbox[2], 264.0)
        self.assertGreaterEqual(right.bbox[0], 300.0)
        from layout.filter import assigned_path_fraction
        self.assertEqual(assigned_path_fraction(pd, regions), 1.0)

    def test_fold_never_leaks_another_region_into_the_union(self):
        # Leaf nearest to tall region A, but union(A, leaf) would newly cover
        # region B's column — folding there would feed B's ink to whatever A
        # classifies as. The fold must go to the next-nearest non-leaking
        # region (B) instead.
        a = block(0, 40, 40, 100, 340)          # tall left column
        b = block(500, 200, 280, 360, 340)      # bottom-right
        leaf = block(900, 200, 40, 224, 100)    # top-right, 24px wide
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=a + b + leaf))
        self.assertEqual(len(regions), 2)
        left = min(regions, key=lambda r: r.bbox[0])
        right = max(regions, key=lambda r: r.bbox[0])
        self.assertLessEqual(left.bbox[2], 104.0)      # A untouched
        self.assertLessEqual(right.bbox[1], 100.0)     # B grew up over the leaf
        self.assertGreaterEqual(right.bbox[0], 196.0)

    def test_leaf_that_would_leak_everywhere_still_drops(self):
        # A page-wide strip below two side-by-side drawings: union with either
        # would swallow the other, so it must drop exactly as before the fold
        # existed (this is the Rule-5 coverage-guard fixture's shape).
        paths = (block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
                 + block(1000, 40, 300, 350, 348))
        regions = segment_page(PageData(page_number=1, width_px=PAGE_W,
                                        height_px=PAGE_H, paths=paths))
        self.assertEqual(len(regions), 2)
        for r in regions:
            self.assertLessEqual(r.bbox[3], 204.0)

    def test_zero_path_small_leaves_still_drop(self):
        # An unmerged text-only fragment holds no coverage; folding it would
        # grow a region's crop for nothing.
        paths = block(0, 100, 100, 300, 300)
        spans = [TextSpan(text="NOTE", bbox=(120.0, 600.0, 170.0, 640.0),
                          font="Helvetica", size=10.0, color=0,
                          block_no=0, line_no=0)]
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=CAPTION_PAGE_H,
                      paths=paths, text_spans=spans)
        regions = segment_page(pd)
        self.assertEqual(len(regions), 1)
        self.assertLessEqual(regions[0].bbox[3], 400.0)

    def test_page_with_no_paths_yields_no_regions(self):
        self.assertEqual(segment_page(PageData(page_number=1, width_px=PAGE_W,
                                               height_px=PAGE_H)), [])

    def test_page_fallback_region_covers_the_whole_page(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 200, 200))
        r = page_fallback_region(pd)
        self.assertEqual(r.bbox, (0.0, 0.0, PAGE_W, PAGE_H))
        self.assertEqual(r.source, "page-fallback")
        self.assertEqual(r.path_count, len(pd.paths))


def span(text, x0, y0, x1, y1):
    return TextSpan(text=text, bbox=(float(x0), float(y0), float(x1), float(y1)),
                    font="Helvetica", size=10.0, color=0, block_no=0, line_no=0)


class TestAttachTextSpans(unittest.TestCase):
    def test_nearby_span_grows_its_nearest_box(self):
        # Caption 40px below box A: within CAPTION_MAX_GAP_PX, attaches.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("GROUND FLOOR PLAN", 60, 240, 180, 260)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 260.0)])

    def test_span_already_inside_a_box_changes_nothing(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("KITCHEN", 100, 100, 140, 112)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 200.0)])

    def test_distant_span_stays_unattached(self):
        # 160px below the box: past CAPTION_MAX_GAP_PX, box must not stretch.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("NOTES", 60, 360, 180, 380)])
        out = _attach_text_spans(pd, [(40.0, 40.0, 200.0, 200.0)])
        self.assertEqual(out, [(40.0, 40.0, 200.0, 200.0)])

    def test_union_never_leaks_another_box(self):
        # Span 50px right of tall box A; union(A, span) would sweep over B's
        # column. B itself is 90px below the span — past the gap cap. The span
        # must attach nowhere and both boxes stay untouched.
        a = (40.0, 40.0, 100.0, 340.0)
        b = (150.0, 150.0, 250.0, 230.0)
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("LABEL", 150, 40, 200, 60)])
        out = _attach_text_spans(pd, [a, b])
        self.assertEqual(out, [a, b])

    def test_tie_breaks_to_first_box_and_does_not_double_attach(self):
        # Span dead-centre in a 100px gutter between two boxes: attaches to
        # exactly one (the first in kept order); the other must not grow.
        boxes = [(40.0, 40.0, 150.0, 200.0), (250.0, 40.0, 360.0, 200.0)]
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      text_spans=[span("BRIDGE", 160, 100, 240, 120)])
        out = _attach_text_spans(pd, boxes)
        grew = [o for o, b in zip(out, boxes) if o != b]
        self.assertEqual(len(grew), 1)


class TestPathsOnlyRetry(unittest.TestCase):
    def _bridged_page(self, extra_spans=()):
        # Two drawings with a 100px gutter; one span's bbox stamps the ink map
        # across x=160..240, leaving <20px of empty run on each side — tier 1
        # cannot split this page, exactly the measured s15 mechanism.
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        spans = [span("BRIDGING LABEL", 160, 100, 240, 120), *extra_spans]
        return PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                        paths=paths, text_spans=spans)

    def test_text_bridged_gutter_splits_via_retry(self):
        regions = segment_page(self._bridged_page())
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "paths-only" for r in regions))

    def test_retry_reattaches_the_bridging_span_to_one_region(self):
        regions = segment_page(self._bridged_page())
        cx, cy = 200.0, 110.0  # bridging span centre
        holders = [r for r in regions
                   if r.bbox[0] <= cx <= r.bbox[2] and r.bbox[1] <= cy <= r.bbox[3]]
        self.assertEqual(len(holders), 1)

    def test_retry_reattaches_captions_for_classification_crops(self):
        caption = span("GROUND FLOOR PLAN", 50, 240, 140, 260)  # 40px below left blob
        regions = segment_page(self._bridged_page(extra_spans=(caption,)))
        self.assertEqual(len(regions), 2)
        left = min(regions, key=lambda r: r.bbox[0])
        self.assertGreaterEqual(left.bbox[3], 260.0)

    def test_healthy_page_never_retries(self):
        # Splits fine with text included: source must stay "whitespace".
        paths = block(0, 40, 40, 150, 200) + block(500, 250, 40, 360, 200)
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=paths,
                      text_spans=[span("KITCHEN", 60, 100, 100, 112)])
        regions = segment_page(pd)
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "whitespace" for r in regions))

    def test_dense_blob_still_yields_one_region(self):
        # No gutter even without text: tier 2 also finds 1 box, so the result
        # stays a single tier-1 region and the pipeline falls back as today.
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 360, 200),
                      text_spans=[span("ELEVATION", 100, 100, 180, 112)])
        regions = segment_page(pd)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].source, "whitespace")

    def test_textless_page_skips_the_retry(self):
        pd = PageData(page_number=1, width_px=PAGE_W, height_px=PAGE_H,
                      paths=block(0, 40, 40, 360, 200))
        regions = segment_page(pd)
        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0].source, "whitespace")

    def test_retry_source_records_clip_involvement(self):
        # The clip's edges sit at the ink's outer bounds, so its cut positions
        # land where _clip_cut skips them (no ink on both sides) — tier 1
        # still cannot split and the retry runs; source records the clips.
        # (A clip edge BETWEEN the blobs would rescue tier 1 by itself and
        # the retry would never fire — that path is the existing
        # test_clip_edge_splits_when_no_gutter_exists.)
        regions = segment_page(self._bridged_page(),
                               clip_rects=[(40.0, 40.0, 360.0, 200.0)])
        self.assertEqual(len(regions), 2)
        self.assertTrue(all(r.source == "paths-only+clip" for r in regions))


if __name__ == "__main__":
    unittest.main()
