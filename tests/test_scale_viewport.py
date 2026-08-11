"""Parsing /VP -> /Measure viewport dictionaries.

The array strings below are copied verbatim from corpus sheets via
doc.xref_get_key(page.xref, "VP"), so these tests exercise the real byte
shapes -- both the compact form AutoCAD writes and the pretty-printed form
that appears in xref_object output.
"""
import unittest

from scale.viewport import (
    parse_measure_viewports,
    split_pdf_dicts,
    viewport_bbox_to_px,
)

# s06, verbatim. Two nested viewports: the outer measures 1:146, the inner
# 1:99.6 -- and the inner is the one matching the sheet's own "SCALE 1:100".
S06_VP = (
    "[<</Type/Viewport/BBox[30 50 1159 791]/Measure<</Type/Measure/Subtype/RL"
    "/A[<</C 1/U( )>>]/D[<</C 1/U( )>>]/R( )/X[<</C 51.51447/U( )>>]>>>>"
    "<</Type/Viewport/BBox[30 172 1023 790]/Measure<</Type/Measure/Subtype/RL"
    "/A[<</C 1/U( )>>]/D[<</C 1/U( )>>]/R( )/X[<</C 35.13904/U( )>>]>>>>]"
)

# s03, pretty-printed with whitespace, and including its 1:1 paper-space
# viewport spanning the whole sheet.
S03_VP_PRETTY = (
    "[ << /Type /Viewport /BBox [ 34 72 2348 1610 ] /Measure << /Subtype /RL "
    "/A [ << /C 1 /U ( ) >> ] /X [ << /C .35279 /U ( ) >> ] >> >> "
    "<< /Type /Viewport /BBox [ 137 270 1492 891 ] /Measure << /Subtype /RL "
    "/X [ << /C 35.27546 /U ( ) >> ] >> >> ]"
)


class TestSplitPdfDicts(unittest.TestCase):
    def test_splits_two_adjacent_viewports(self):
        self.assertEqual(len(split_pdf_dicts(S06_VP)), 2)

    def test_nested_dicts_do_not_split(self):
        chunks = split_pdf_dicts(S06_VP)
        self.assertIn("/C 51.51447", chunks[0])
        self.assertNotIn("/C 35.13904", chunks[0])

    def test_empty_array_yields_nothing(self):
        self.assertEqual(split_pdf_dicts("[]"), [])

    def test_unbalanced_array_does_not_hang_or_raise(self):
        self.assertEqual(split_pdf_dicts("[<</BBox[1 2 3 4]"), [])


class TestParseMeasureViewports(unittest.TestCase):
    def test_s06_yields_both_viewports(self):
        self.assertEqual(len(parse_measure_viewports(S06_VP)), 2)

    def test_s06_inner_viewport_conversion_factor(self):
        found = {round(c, 5) for _, c in parse_measure_viewports(S06_VP)}
        self.assertEqual(found, {51.51447, 35.13904})

    def test_s06_bboxes_are_kept_with_their_own_factor(self):
        by_c = {round(c, 5): bbox for bbox, c in parse_measure_viewports(S06_VP)}
        self.assertEqual(by_c[35.13904], (30.0, 172.0, 1023.0, 790.0))

    def test_pretty_printed_whitespace_form_parses(self):
        found = {round(c, 5) for _, c in parse_measure_viewports(S03_VP_PRETTY)}
        self.assertIn(35.27546, found)

    def test_paper_space_viewport_is_dropped(self):
        # .35279 is 1:1 -- the sheet, not a drawing.
        found = {round(c, 5) for _, c in parse_measure_viewports(S03_VP_PRETTY)}
        self.assertNotIn(0.35279, found)

    def test_non_rectilinear_subtype_is_ignored(self):
        geo = ("[<</Type/Viewport/BBox[0 0 10 10]/Measure<</Subtype/GEO"
               "/X[<</C 35.0/U( )>>]>>>>]")
        self.assertEqual(parse_measure_viewports(geo), [])

    def test_viewport_without_measure_is_ignored(self):
        plain = "[<</Type/Viewport/BBox[0 0 10 10]>>]"
        self.assertEqual(parse_measure_viewports(plain), [])

    def test_area_factor_is_not_mistaken_for_the_axis_factor(self):
        # /A carries C 1; only /X states the drawing scale.
        by_c = {round(c, 5) for _, c in parse_measure_viewports(S06_VP)}
        self.assertNotIn(1.0, by_c)


class TestViewportBboxToPx(unittest.TestCase):
    """The /VP bbox is raw PDF: y-up, bottom-left origin. Everything else in
    the pipeline is y-down, top-left. Verified by rendering both readings --
    see the spec's "The /VP bbox is y-up" section."""

    IDENTITY = (150 / 72, 0.0, 0.0, 150 / 72, 0.0, 0.0)

    def test_y_is_flipped_about_the_mediabox(self):
        # s17's 1:1250 inset on a 2384x1684pt sheet sits near the TOP.
        px = viewport_bbox_to_px(
            (2100.0, 1267.0, 2296.0, 1519.0),
            mediabox=(0.0, 0.0, 2384.0, 1684.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[1], (1684.0 - 1519.0) * s, places=3)
        self.assertAlmostEqual(px[3], (1684.0 - 1267.0) * s, places=3)

    def test_x_is_offset_by_the_mediabox_origin(self):
        px = viewport_bbox_to_px(
            (10.0, 0.0, 20.0, 100.0),
            mediabox=(5.0, 0.0, 105.0, 100.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[0], 5.0 * s, places=3)
        self.assertAlmostEqual(px[2], 15.0 * s, places=3)

    def test_result_is_ordered_x0_y0_x1_y1(self):
        px = viewport_bbox_to_px(
            (10.0, 20.0, 30.0, 40.0),
            mediabox=(0.0, 0.0, 100.0, 100.0),
            transform=self.IDENTITY,
        )
        self.assertLess(px[0], px[2])
        self.assertLess(px[1], px[3])

    def test_rotated_page_transform_is_applied(self):
        # /Rotate 270 on a 100x200pt page: rotation_matrix maps unrotated
        # coords into the rotated frame, so the box must land inside the
        # rotated page extent rather than the unrotated one.
        rot270 = (0.0, -1.0, 1.0, 0.0, 0.0, 200.0)
        px = viewport_bbox_to_px(
            (10.0, 20.0, 30.0, 40.0),
            mediabox=(0.0, 0.0, 100.0, 200.0),
            transform=rot270,
        )
        self.assertLess(px[0], px[2])
        self.assertLess(px[1], px[3])


if __name__ == "__main__":
    unittest.main()
