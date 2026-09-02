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

    def test_measured_nonstandard_scale_does_not_drive_gates(self):
        # s01: user-stored 1:92.2 (dimension-measured plot metric, nominal
        # None, not viewport-declared). The takeoff uses it; the gates must
        # not — the W constants were calibrated on this very ink at factor
        # 1.0, and scaling them regressed s01 from 13/13 rooms to 7/13.
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
