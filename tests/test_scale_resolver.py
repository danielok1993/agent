"""The resolution ladder and how a scale binds to a floor plan.

Region binding is the whole point of scenario 3: one sheet, several plans,
different scales. s17 carries 1:50, four 1:100s, 1:500 and 1:1250 at once.
"""
import unittest

from models import PageData, Region, ScaleInfo, TextSpan
from scale.resolver import bind_scale, binding_texts, resolve_page_scales
from scale.store import StoredScale


def region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


def viewport(denominator, bbox):
    return ScaleInfo(denominator=denominator, source="viewport", bbox=bbox,
                     raw=f"C={denominator:g}", nominal=denominator)


def text(denominator, bbox):
    return ScaleInfo(denominator=denominator, source="text", bbox=bbox,
                     raw=f"SCALE 1:{denominator:g}", nominal=denominator)


def span(text_value, bbox):
    return TextSpan(text=text_value, bbox=bbox, font="Arial", size=10.0,
                    color=0, block_no=0, line_no=0)


class TestBindScale(unittest.TestCase):
    def test_viewport_containing_the_region_centroid_wins(self):
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(50.0, (0.0, 0.0, 100.0, 100.0))], [])
        self.assertEqual(found.denominator, 50.0)

    def test_innermost_viewport_wins_when_they_nest(self):
        # Passed smallest-first, as viewport_scales returns them.
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(100.0, (0.0, 0.0, 50.0, 50.0)),
                            viewport(146.0, (0.0, 0.0, 200.0, 200.0))], [])
        self.assertEqual(found.denominator, 100.0)

    def test_viewport_not_containing_the_centroid_does_not_bind(self):
        found = bind_scale(region("region_0000", (10.0, 10.0, 20.0, 20.0)),
                           [viewport(50.0, (500.0, 500.0, 600.0, 600.0))], [])
        self.assertIsNone(found)

    def test_text_inside_the_region_binds_when_no_viewport_does(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(50.0, (10.0, 80.0, 40.0, 90.0))])
        self.assertEqual(found.denominator, 50.0)
        self.assertEqual(found.source, "text")

    def test_text_just_below_the_region_binds(self):
        # Captions are drawn beneath the plan, outside the region box.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 105.0, 40.0, 115.0))])
        self.assertEqual(found.denominator, 100.0)

    def test_a_caption_191px_below_still_binds(self):
        # Measured on s13, whose SCALE 1:100 sits 191px below its viewport.
        # This is the gap that makes the corpus's one detectable conflict.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 291.0, 40.0, 301.0))])
        self.assertEqual(found.denominator, 100.0)

    def test_a_caption_beyond_reach_does_not_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 400.0, 40.0, 410.0))])
        self.assertIsNone(found)

    def test_far_away_text_does_not_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [], [text(100.0, (10.0, 900.0, 40.0, 910.0))])
        self.assertIsNone(found)

    def test_viewport_beats_text_when_both_bind(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertEqual(found.denominator, 136.4)

    def test_disagreement_beyond_tolerance_records_a_conflict(self):
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertIsNotNone(found.conflict)
        self.assertIn("1:100", found.conflict)

    def test_agreement_within_tolerance_records_no_conflict(self):
        # s06: viewport 99.6, printed 1:100.
        found = bind_scale(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                           [viewport(99.6, (0.0, 0.0, 200.0, 200.0))],
                           [text(100.0, (10.0, 50.0, 40.0, 60.0))])
        self.assertIsNone(found.conflict)


class TestBindingTexts(unittest.TestCase):
    def test_returns_every_candidate_nearest_first(self):
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (10.0, 140.0, 40.0, 150.0)),
                               text(50.0, (10.0, 105.0, 40.0, 115.0))])
        self.assertEqual([f.denominator for f in found], [50.0, 100.0])

    def test_excludes_candidates_out_of_reach(self):
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (10.0, 900.0, 40.0, 910.0))])
        self.assertEqual(found, [])

    def test_excludes_candidates_with_no_horizontal_overlap(self):
        # A caption beside a plan belongs to its neighbour, not to this one.
        found = binding_texts(region("region_0000", (0.0, 0.0, 100.0, 100.0)),
                              [text(100.0, (500.0, 105.0, 540.0, 115.0))])
        self.assertEqual(found, [])


class TestResolvePageScales(unittest.TestCase):
    def blank_page(self, spans=()):
        return PageData(page_number=1, width_px=200.0, height_px=200.0,
                        text_spans=list(spans))

    def test_stored_value_beats_every_detected_tier(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")],
        )
        self.assertEqual(result.by_region["region_0000"].denominator, 20.0)
        self.assertEqual(result.by_region["region_0000"].source, "user")

    def test_unresolved_region_emits_a_warning(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertEqual([w["warning_code"] for w in result.warnings],
                         ["SCALE_UNRESOLVED"])

    def test_only_floor_plan_regions_are_bound(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0), "elevation")],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertEqual(result.by_region, {})

    def test_conflict_emits_a_warning(self):
        page = self.blank_page([span("SCALE 1:100", (10.0, 50.0, 40.0, 60.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(136.4, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIn("SCALE_SOURCE_CONFLICT",
                      [w["warning_code"] for w in result.warnings])

    def test_sole_page_candidate_binds_a_region_it_does_not_geometrically_reach(self):
        page = self.blank_page([span("1:50@A3", (900.0, 900.0, 950.0, 910.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 50.0)

    def test_two_unbindable_candidates_warn_rather_than_guess(self):
        page = self.blank_page([span("1:50  & 1:100", (900.0, 900.0, 950.0, 910.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("SCALE_MULTIPLE_UNBOUND",
                      [w["warning_code"] for w in result.warnings])

    def test_page_scale_is_reported_when_there_are_no_regions(self):
        page = self.blank_page([span("1:50@A3", (10.0, 10.0, 60.0, 20.0))])
        result = resolve_page_scales(page_data=page, regions=[],
                                     viewports=[], stored=[])
        self.assertEqual(result.page_scale.denominator, 50.0)

    def test_a_multi_scale_sheet_has_no_page_scale(self):
        # s17 states 1:50, 1:100, 1:500 and 1:1250 at once. No single number
        # describes the sheet, so summary.json must not publish one.
        result = resolve_page_scales(
            page_data=self.blank_page(), regions=[],
            viewports=[viewport(50.0, (0.0, 0.0, 50.0, 50.0)),
                       viewport(100.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIsNone(result.page_scale)

    def test_two_viewports_of_the_same_scale_yield_one_page_scale(self):
        # The REAL floats from s04's two 1:50 viewports. CAD never writes a
        # scale as the same float twice, so 100.0/100.0 would not test this.
        result = resolve_page_scales(
            page_data=self.blank_page(), regions=[],
            viewports=[viewport(49.995, (0.0, 0.0, 50.0, 50.0)),
                       viewport(50.001, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertIsNotNone(result.page_scale)

    def test_a_none_denominator_candidate_does_not_poison_the_sole_candidate(self):
        # A ScaleInfo with no denominator (source="unresolved", say) sitting
        # first in viewports+texts must not become page_scale, and must not
        # block the one real denominator from resolving as the sole candidate.
        page = self.blank_page([span("1:50@A3", (10.0, 10.0, 60.0, 20.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (900.0, 900.0, 950.0, 950.0))],
            viewports=[ScaleInfo(denominator=None, source="unresolved")],
            stored=[])
        self.assertEqual(result.page_scale.denominator, 50.0)
        self.assertEqual(result.by_region["region_0000"].denominator, 50.0)

    def test_s04s_real_floats_do_not_warn_about_multiple_scales(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (10.0, 10.0, 40.0, 40.0))],
            viewports=[viewport(49.995, (0.0, 0.0, 50.0, 50.0)),
                       viewport(50.001, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertNotIn("SCALE_MULTIPLE_UNBOUND",
                         [w["warning_code"] for w in result.warnings])

    def test_two_captions_disagreeing_over_one_plan_resolve_to_nothing(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("SCALE_MULTIPLE_UNBOUND",
                      [w["warning_code"] for w in result.warnings])

    def test_ambiguity_is_reported_once_not_twice(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        codes = [w["warning_code"] for w in result.warnings]
        self.assertEqual(codes.count("SCALE_MULTIPLE_UNBOUND"), 1)

    def test_repeated_captions_of_the_same_scale_are_not_ambiguous(self):
        # s03 prints SCALE 1:100 under every plan; agreement is not conflict.
        page = self.blank_page([span("SCALE 1:100", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (50.0, 105.0, 80.0, 115.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 100.0)

    def test_viewport_binding_overrides_text_ambiguity(self):
        page = self.blank_page([span("SCALE 1:50", (10.0, 105.0, 40.0, 115.0)),
                                span("SCALE 1:100", (10.0, 120.0, 40.0, 130.0))])
        result = resolve_page_scales(
            page_data=page,
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[viewport(50.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[])
        self.assertEqual(result.by_region["region_0000"].denominator, 50.0)

    def test_stored_decimal_scale_round_trips_exactly(self):
        # prompt.py accepts decimals; the stored string must reload unchanged.
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:136.4")])
        self.assertEqual(result.by_region["region_0000"].denominator, 136.4)

    def test_crop_is_rendered_on_demand_before_prompting(self):
        from unittest import mock
        rendered = []
        with mock.patch("scale.resolver.can_prompt", return_value=True), \
             mock.patch("scale.resolver.prompt_for_scale", return_value="1:100"):
            resolve_page_scales(
                page_data=self.blank_page(),
                regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
                viewports=[], stored=[],
                crop_fn=lambda r: rendered.append(r.region_id) or "crop.png",
                allow_prompt=True)
        self.assertEqual(rendered, ["region_0000"])

    def test_a_crop_that_cannot_be_rendered_still_prompts(self):
        from unittest import mock

        def boom(_region):
            raise OSError("cannot render")

        with mock.patch("scale.resolver.can_prompt", return_value=True), \
             mock.patch("scale.resolver.prompt_for_scale",
                        return_value=None) as ask:
            result = resolve_page_scales(
                page_data=self.blank_page(),
                regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
                viewports=[], stored=[], crop_fn=boom, allow_prompt=True)
        self.assertEqual(result.by_region["region_0000"].source, "unresolved")
        self.assertIn("no crop available", ask.call_args[0][1])

    def test_a_stored_scale_for_a_different_drawing_does_not_apply(self):
        """The renumbering hazard, end to end.

        A scale stored against what used to be region_0000 must not attach to
        a re-segmented region_0000 covering a different drawing — stored
        values outrank detected ones, so this would override a correct
        viewport reading, not merely add a wrong one.
        """
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (500.0, 500.0, 600.0, 600.0))],
            viewports=[viewport(100.0, (400.0, 400.0, 700.0, 700.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")])
        self.assertEqual(result.by_region["region_0000"].denominator, 100.0)
        self.assertEqual(result.by_region["region_0000"].source, "viewport")

    def test_a_stored_scale_survives_a_small_region_shift(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0009", (2.0, 2.0, 102.0, 102.0))],
            viewports=[viewport(100.0, (0.0, 0.0, 200.0, 200.0))],
            stored=[StoredScale((0.0, 0.0, 100.0, 100.0), "1:20")])
        self.assertEqual(result.by_region["region_0009"].denominator, 20.0)
        self.assertEqual(result.by_region["region_0009"].source, "user")

    def test_every_warning_carries_the_page_number(self):
        result = resolve_page_scales(
            page_data=self.blank_page(),
            regions=[region("region_0000", (0.0, 0.0, 100.0, 100.0))],
            viewports=[], stored=[])
        self.assertTrue(all(w["page_number"] == 1 for w in result.warnings))


if __name__ == "__main__":
    unittest.main()
