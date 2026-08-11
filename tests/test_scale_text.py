"""Reading a 1:N scale out of text spans.

Every string below is copied verbatim from a corpus sheet. The negations are
the important cases: two sheets tell the reader NOT to scale from the drawing,
and matching on the word "scale" would turn both into a scale annotation.
"""
import unittest

from models import PageData, TextSpan
from scale.text import scales_in_text, text_scales


def span(text, bbox=(0.0, 0.0, 10.0, 10.0)):
    return TextSpan(text=text, bbox=bbox, font="Arial", size=10.0,
                    color=0, block_no=0, line_no=0)


class TestScalesInText(unittest.TestCase):
    def test_s03_caption(self):
        self.assertEqual(scales_in_text("SCALE 1:100"), [100.0])

    def test_s06_caption_with_padding(self):
        self.assertEqual(scales_in_text("SCALE        1:100"), [100.0])

    def test_s04_paper_size_suffix(self):
        self.assertEqual(scales_in_text("1:50@A3"), [50.0])

    def test_s02_scale_bar_layer_label(self):
        self.assertEqual(scales_in_text("scale bar - metric - 1:50@A3"), [50.0])

    def test_s20_title_block_states_two_scales(self):
        self.assertEqual(scales_in_text("1:50  & 1:100"), [50.0, 100.0])

    def test_s14_negation_is_not_a_scale(self):
        self.assertEqual(scales_in_text("PLEASE DO NOT SCALE FROM THIS DRAWING"), [])

    def test_s15_negation_is_not_a_scale(self):
        self.assertEqual(scales_in_text(
            "3. DO NOT SCALE THIS DRAWING.ANY DISCREPANCIES TO BE REPORTED "
            "TO THE PROJECT CO-ORDINATOR"), [])

    def test_s03_as_shown_states_no_ratio(self):
        self.assertEqual(scales_in_text("As Shown @ A1"), [])

    def test_bare_label_states_no_ratio(self):
        self.assertEqual(scales_in_text("Scale:"), [])

    def test_one_to_one_is_not_a_drawing_scale(self):
        self.assertEqual(scales_in_text("1:1"), [])

    def test_slash_form_is_not_matched_so_dates_cannot_match(self):
        # "1/5/2024" would otherwise read as 1:5. No corpus sheet uses a
        # slash, so the separator stays a colon.
        self.assertEqual(scales_in_text("Issued 1/5/2024"), [])

    def test_room_dimensions_are_not_scales(self):
        self.assertEqual(scales_in_text("3600 x 4200"), [])

    def test_decimal_denominator_survives(self):
        # This grammar also parses stored user answers back. prompt.py accepts
        # decimals, so an integer-only pattern would reload "1:136.4" as 136.
        self.assertEqual(scales_in_text("1:136.4"), [136.4])

    def test_decimal_below_the_paper_space_floor_is_still_rejected(self):
        self.assertEqual(scales_in_text("1:1.2"), [])


class TestTextScales(unittest.TestCase):
    def test_span_bbox_is_carried_through(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("SCALE 1:100", (10.0, 20.0, 60.0, 30.0))])
        found = text_scales(page)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].bbox, (10.0, 20.0, 60.0, 30.0))

    def test_source_is_text_and_raw_is_the_span(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("SCALE 1:100")])
        found = text_scales(page)
        self.assertEqual(found[0].source, "text")
        self.assertEqual(found[0].raw, "SCALE 1:100")

    def test_nominal_is_snapped(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("1:50@A3")])
        self.assertEqual(text_scales(page)[0].nominal, 50.0)

    def test_two_scales_in_one_span_yield_two_results_sharing_a_bbox(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0,
                        text_spans=[span("1:50  & 1:100", (1.0, 2.0, 3.0, 4.0))])
        found = text_scales(page)
        self.assertEqual([f.denominator for f in found], [50.0, 100.0])
        self.assertEqual({f.bbox for f in found}, {(1.0, 2.0, 3.0, 4.0)})

    def test_page_with_no_text_yields_nothing(self):
        page = PageData(page_number=1, width_px=100.0, height_px=100.0)
        self.assertEqual(text_scales(page), [])


if __name__ == "__main__":
    unittest.main()
