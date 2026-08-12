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
    viewport_scales,
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
            cropbox=(0.0, 0.0, 2384.0, 1684.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[1], (1684.0 - 1519.0) * s, places=3)
        self.assertAlmostEqual(px[3], (1684.0 - 1267.0) * s, places=3)

    def test_x_is_offset_by_the_mediabox_origin(self):
        px = viewport_bbox_to_px(
            (10.0, 0.0, 20.0, 100.0),
            cropbox=(5.0, 0.0, 105.0, 100.0),
            transform=self.IDENTITY,
        )
        s = 150 / 72
        self.assertAlmostEqual(px[0], 5.0 * s, places=3)
        self.assertAlmostEqual(px[2], 15.0 * s, places=3)

    def test_result_is_ordered_x0_y0_x1_y1(self):
        px = viewport_bbox_to_px(
            (10.0, 20.0, 30.0, 40.0),
            cropbox=(0.0, 0.0, 100.0, 100.0),
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
            cropbox=(0.0, 0.0, 100.0, 200.0),
            transform=rot270,
        )
        self.assertLess(px[0], px[2])
        self.assertLess(px[1], px[3])


class _Rect:
    """Just enough of fitz.Rect for viewport_scales: x0/y0/x1/y1 attributes."""

    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1


class _Matrix:
    """Just enough of fitz.Matrix for page_transform: a/b/c/d/e/f attributes."""

    def __init__(self, a, b, c, d, e, f):
        self.a, self.b, self.c, self.d, self.e, self.f = a, b, c, d, e, f


class _FakePage:
    """A page double with no fitz dependency -- no PDF is ever opened.

    Only test_scale_corpus.py is allowed to open a real PDF; viewport_scales
    only touches page.xref, page.cropbox, page.mediabox and
    page.rotation_matrix, all of which this fakes directly.
    """

    def __init__(self, mediabox, cropbox, xref=1):
        self.mediabox = _Rect(*mediabox)
        self.cropbox = _Rect(*cropbox)
        self.rotation_matrix = _Matrix(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # unrotated
        self.xref = xref


class _FakeDoc:
    def __init__(self, vp_array_text):
        self._vp = vp_array_text

    def xref_get_key(self, xref, key):
        assert key == "VP"
        return ("array", self._vp)


class TestViewportScalesUsesTheCropbox(unittest.TestCase):
    """The bug lived here, not in viewport_bbox_to_px's arithmetic: the flip
    formula is unchanged, only which box viewport_scales hands it changed
    from page.mediabox to page.cropbox. Pinned with a page double whose
    cropbox is inset from its mediabox in BOTH origin and extent, since
    every real corpus sheet has cropbox == mediabox and could never catch
    this."""

    def test_bbox_lands_in_the_cropbox_relative_frame(self):
        # mediabox (0,0,600,800); cropbox inset on both origin and extent to
        # (50,100,550,700) -- exactly the shape get_drawings()/get_text()
        # report relative to, per PyMuPDF's own page.transformation_matrix.
        vp = ("[<</Type/Viewport/BBox[100 200 300 400]/Measure<</Type/Measure"
              "/Subtype/RL/X[<</C 35.27546/U( )>>]>>>>]")
        page = _FakePage(mediabox=(0.0, 0.0, 600.0, 800.0),
                         cropbox=(50.0, 100.0, 550.0, 700.0))
        doc = _FakeDoc(vp)

        found = viewport_scales(doc, page)

        self.assertEqual(len(found), 1)
        s = 150 / 72
        expected = ((100.0 - 50.0) * s, (700.0 - 400.0) * s,
                    (300.0 - 50.0) * s, (700.0 - 200.0) * s)
        for got, want in zip(found[0].bbox, expected):
            self.assertAlmostEqual(got, want, places=3)


if __name__ == "__main__":
    unittest.main()
