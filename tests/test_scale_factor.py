"""detection_scale(): PageScales + regions -> one detection factor per page."""
import unittest

from models import Region, ScaleInfo
from scale.factor import (
    DETECTION_FACTOR_MAX, DETECTION_FACTOR_MIN, DetectionScale, detection_scale,
)
from scale.resolver import PageScales, _fallback_info


def region(rid, region_type="floor_plan", path_count=100):
    return Region(region_id=rid, bbox=(0, 0, 100, 100),
                  region_type=region_type, path_count=path_count)


def info(denominator, nominal=None, source="viewport"):
    return ScaleInfo(denominator=denominator, source=source,
                     nominal=nominal if nominal is not None else denominator)


class TestDetectionScale(unittest.TestCase):
    def test_single_floor_plan_scale_sets_factor(self):
        ps = PageScales(by_region={"region_0000": info(100.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 0.5)
        self.assertEqual(ds.denominator, 100.0)
        self.assertEqual(ds.source, "floor_plan_regions")
        self.assertEqual(ds.warnings, [])

    def test_one_to_fifty_is_exactly_identity(self):
        ps = PageScales(by_region={"region_0000": info(50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 1.0)  # exact, not approx

    def test_nominal_preferred_over_raw_denominator(self):
        # s04: raw viewport 50.0007, nominal snap 50.0 -> factor exactly 1.0
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=50.0007, source="viewport",
                                     nominal=50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 1.0)

    def test_unsnapped_denominator_is_used_raw(self):
        # s13: viewport 136.4, nominal None -> continuous factor, no special case
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=136.4, source="viewport",
                                     nominal=None)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertAlmostEqual(ds.factor, 50.0 / 136.4)

    def test_unverified_nonstandard_scale_does_not_drive_gates(self):
        # A user-stored 1:92.2 (nominal None, not viewport-declared) with NO
        # dimension strings to verify it: a measurement of the plot the
        # takeoff uses but that nothing on the drawing corroborates, so the
        # gates abstain. With dimensions that agree it drives them — see
        # TestDimensionsVerifyTheClaim (s01, W-gate iteration 3 step 12).
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None),
            "region_0001": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None)})
        ds = detection_scale(
            ps, [region("region_0000"), region("region_0001")], page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "measured")
        self.assertEqual(ds.denominator, 92.2)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_MEASURED_ONLY")
        self.assertEqual(ds.warnings[0]["page_number"], 1)

    def test_nominal_user_scale_still_scales_gates(self):
        # A user-typed 1:100 asserts a drafting scale, not a measurement.
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=100.0, source="user",
                                     nominal=100.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 0.5)
        self.assertEqual(ds.warnings, [])

    def test_measured_region_abstains_but_nominal_region_scales(self):
        # Mixed: the nominal region drives the factor; the measured one
        # abstains loudly instead of skewing the vote.
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=100.0, source="viewport",
                                     nominal=100.0),
            "region_0001": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None)})
        regions = [region("region_0000", path_count=100),
                   region("region_0001", path_count=2000)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.factor, 0.5)
        self.assertEqual(ds.source, "floor_plan_regions")
        codes = [w["warning_code"] for w in ds.warnings]
        self.assertIn("SCALE_FACTOR_MEASURED_ONLY", codes)
        self.assertNotIn("SCALE_MIXED_FLOOR_PLANS", codes)

    def test_measured_page_scale_does_not_drive_gates(self):
        # Page-level fallback path: a measured non-standard caption scale
        # behaves like the per-region case — identity, loud warning.
        ps = PageScales(by_region={}, page_scale=ScaleInfo(
            denominator=92.2, source="text", nominal=None))
        ds = detection_scale(ps, [], page_number=2)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "measured")
        self.assertEqual(ds.denominator, 92.2)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_MEASURED_ONLY")
        self.assertEqual(ds.warnings[0]["page_number"], 2)

    def test_mixed_scales_ink_dominant_wins_and_warns(self):
        # s03 shape: two 1:100 regions carry more ink than the 1:50 one
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(100.0),
            "region_0003": info(50.0)})
        regions = [region("region_0000", path_count=800),
                   region("region_0001", path_count=700),
                   region("region_0003", path_count=400)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 100.0)
        self.assertEqual(len(ds.warnings), 1)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_MIXED_FLOOR_PLANS")
        self.assertEqual(ds.warnings[0]["page_number"], 1)

    def test_mixed_scales_minority_ink_loses(self):
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(50.0)})
        regions = [region("region_0000", path_count=100),
                   region("region_0001", path_count=2000)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 50.0)

    def test_non_floor_plan_regions_are_ignored(self):
        # a site-plan region's 1:500 must not influence detection
        ps = PageScales(by_region={
            "region_0000": info(50.0), "region_0001": info(500.0)})
        regions = [region("region_0000"),
                   region("region_0001", region_type="site_plan")]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.warnings, [])   # not "mixed": only one fp scale

    def test_page_scale_fallback(self):
        # s02 shape: no region bindings, page-level caption
        ps = PageScales(by_region={}, page_scale=info(50.0, source="text"))
        ds = detection_scale(ps, [], page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "page")

    def test_unresolved_is_identity_no_new_warning(self):
        ds = detection_scale(PageScales(), [region("region_0000")],
                             page_number=1)
        self.assertEqual(ds.factor, 1.0)
        self.assertIsNone(ds.denominator)
        self.assertEqual(ds.source, "unresolved")
        self.assertEqual(ds.warnings, [])   # resolver already warned

    def test_extreme_factor_clamps_to_identity_with_warning(self):
        ps = PageScales(by_region={"region_0000": info(500.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=3)
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "clamped")
        self.assertEqual(ds.denominator, 500.0)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_CLAMPED")
        self.assertEqual(ds.warnings[0]["page_number"], 3)

    def test_clamp_bounds_are_inclusive(self):
        # denominator 200 -> factor 0.25 == DETECTION_FACTOR_MIN: kept
        ps = PageScales(by_region={"region_0000": info(200.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, DETECTION_FACTOR_MIN)
        self.assertEqual(ds.source, "floor_plan_regions")
        # denominator 12.5 -> factor 4.0 == DETECTION_FACTOR_MAX: kept
        ps = PageScales(by_region={"region_0000": info(12.5)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, DETECTION_FACTOR_MAX)

    def test_tie_breaks_to_smaller_denominator_deterministically(self):
        ps = PageScales(by_region={
            "region_0000": info(100.0), "region_0001": info(50.0)})
        regions = [region("region_0000", path_count=500),
                   region("region_0001", path_count=500)]
        ds = detection_scale(ps, regions, page_number=1)
        self.assertEqual(ds.denominator, 50.0)   # tie -> less aggressive scaling


def dims(implied, n=3, x=50.0, y=50.0):
    """n ticked dimension strings measuring 1:implied, drawn around (x, y)."""
    from scale.dimensions import DimensionMatch

    return [DimensionMatch(value_mm=1000.0,
                           length_px=1000.0 / (implied * 25.4 / 150),
                           implied_denominator=implied,
                           line=((x - 10.0, y), (x + 10.0, y)))
            for _ in range(n)]


class TestDimensionsVerifyTheClaim(unittest.TestCase):
    """The drawing's ticked dimension strings measure its scale (W-gate
    iteration 3 step 12). At least DIM_MIN_MATCHES of them inside a plan
    verify a claimed scale within DIM_AGREE_TOL — and a verified claim drives
    the gates whatever its number — or contradict it past DIM_DISAGREE_TOL,
    in which case the measured scale drives the gates instead."""

    def test_dimension_verified_nonstandard_scale_drives_gates(self):
        # s01: stored 1:92.2, nominal None; 31 dimension strings agree.
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1,
                             dimensions=dims(92.2, n=31))
        self.assertAlmostEqual(ds.factor, 50.0 / 92.2)
        self.assertEqual(ds.denominator, 92.2)
        self.assertEqual(ds.source, "floor_plan_regions")
        self.assertAlmostEqual(ds.measured, 92.2)
        self.assertEqual(ds.warnings, [])

    def test_fewer_than_three_dimensions_verify_nothing(self):
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1,
                             dimensions=dims(92.2, n=2))
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "measured")
        self.assertIsNone(ds.measured)
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_MEASURED_ONLY")

    def test_dimensions_contradicting_the_claim_drive_the_gates(self):
        # A half-size print: the viewport (or caption) says 1:50, the
        # dimension strings measure 1:100. The gates follow the ink; the
        # takeoff keeps the claim and flags it SCALE_IMPLAUSIBLE.
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=50.0, source="viewport",
                                     nominal=50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=4,
                             dimensions=dims(99.6, n=5))
        self.assertEqual(ds.factor, 0.5)          # snapped: exact, like nominal
        self.assertEqual(ds.denominator, 100.0)
        self.assertEqual(ds.source, "dimensions")
        self.assertAlmostEqual(ds.measured, 99.6)
        self.assertEqual([w["warning_code"] for w in ds.warnings],
                         ["SCALE_FACTOR_FROM_DIMENSIONS"])
        self.assertEqual(ds.warnings[0]["page_number"], 4)
        self.assertIn("1:100", ds.warnings[0]["message"])
        self.assertIn("1:50", ds.warnings[0]["message"])

    def test_inconclusive_dimensions_leave_the_claim_alone(self):
        # 8 % off: neither agreement nor contradiction. A nominal claim
        # drives the gates as it always did; an unsnapped one still abstains.
        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=50.0, source="viewport",
                                     nominal=50.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1,
                             dimensions=dims(54.0))
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "floor_plan_regions")
        self.assertEqual(ds.warnings, [])

        ps = PageScales(by_region={
            "region_0000": ScaleInfo(denominator=92.2, source="user",
                                     nominal=None)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1,
                             dimensions=dims(100.0))
        self.assertEqual(ds.factor, 1.0)
        self.assertEqual(ds.source, "measured")
        self.assertEqual(ds.warnings[0]["warning_code"],
                         "SCALE_FACTOR_MEASURED_ONLY")

    def test_dimensions_are_read_per_plan(self):
        # A mixed sheet: a 1:100 viewport plan and a stored-1:92.2 plan.
        # Each plan's own dimension strings judge its own claim, so the
        # 1:92.2 plan is verified by the strings drawn inside it and votes
        # (ink-dominant here) — while strings drawn in the OTHER plan, or in
        # no plan at all, verify nothing for it.
        a = Region(region_id="a", bbox=(0, 0, 100, 100),
                   region_type="floor_plan", path_count=100)
        b = Region(region_id="b", bbox=(200, 0, 300, 100),
                   region_type="floor_plan", path_count=2000)
        ps = PageScales(by_region={
            "a": ScaleInfo(denominator=100.0, source="viewport", nominal=100.0),
            "b": ScaleInfo(denominator=92.2, source="user", nominal=None)})

        ds = detection_scale(ps, [a, b], page_number=1,
                             dimensions=dims(100.0, x=50) + dims(92.2, x=250))
        self.assertEqual(ds.denominator, 92.2)
        codes = [w["warning_code"] for w in ds.warnings]
        self.assertEqual(codes, ["SCALE_MIXED_FLOOR_PLANS"])

        for where in (50.0, 150.0):        # inside a / between the plans
            ds = detection_scale(ps, [a, b], page_number=1,
                                 dimensions=dims(92.2, x=where))
            self.assertEqual(ds.denominator, 100.0)
            self.assertIn("SCALE_FACTOR_MEASURED_ONLY",
                          [w["warning_code"] for w in ds.warnings])

    def test_page_scale_is_verified_by_the_page_dimensions(self):
        ps = PageScales(by_region={}, page_scale=ScaleInfo(
            denominator=92.2, source="text", nominal=None))
        ds = detection_scale(ps, [], page_number=2, dimensions=dims(92.2))
        self.assertAlmostEqual(ds.factor, 50.0 / 92.2)
        self.assertEqual(ds.source, "page")
        self.assertEqual(ds.warnings, [])

    def test_page_scale_contradicted_by_the_page_dimensions(self):
        ps = PageScales(by_region={}, page_scale=ScaleInfo(
            denominator=50.0, source="text", nominal=50.0))
        ds = detection_scale(ps, [], page_number=2, dimensions=dims(100.0))
        self.assertEqual(ds.factor, 0.5)
        self.assertEqual(ds.source, "dimensions")
        self.assertEqual([w["warning_code"] for w in ds.warnings],
                         ["SCALE_FACTOR_FROM_DIMENSIONS"])

    def test_no_dimensions_argument_is_the_old_behaviour(self):
        ps = PageScales(by_region={"region_0000": info(100.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual(ds.factor, 0.5)
        self.assertIsNone(ds.measured)


class TestSuppliedScaleDrivesTheGates(unittest.TestCase):
    def test_every_suppliable_scale_yields_its_own_factor(self):
        from scale.units import SUPPLIABLE_SCALES

        for denominator in SUPPLIABLE_SCALES:
            with self.subTest(denominator=denominator):
                ps = PageScales(
                    by_region={"region_0000": _fallback_info(denominator)})
                ds = detection_scale(ps, [region("region_0000")],
                                     page_number=1)
                self.assertAlmostEqual(ds.factor, 50.0 / denominator)
                self.assertEqual(ds.source, "floor_plan_regions")
                self.assertEqual(ds.denominator, denominator)

    def test_a_supplied_scale_raises_no_measured_only_warning(self):
        # SCALE_FACTOR_MEASURED_ONLY means "resolved, but the gates ignored
        # it" — the identity-factor outcome the re-run exists to avoid. Its
        # presence here would mean the whole re-run is pointless.
        ps = PageScales(by_region={"region_0000": _fallback_info(100.0)})
        ds = detection_scale(ps, [region("region_0000")], page_number=1)
        self.assertEqual([w["warning_code"] for w in ds.warnings], [])


if __name__ == "__main__":
    unittest.main()
