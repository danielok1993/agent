"""Scale arithmetic: PDF /Measure conversion factors to a 1:N denominator.

Every number here is measured from the regression corpus on 2026-08-11 and
recorded in the design spec. A failure means the conversion changed, not that
the expectations are stale.
"""
import unittest

from models import ScaleInfo
from scale.units import (
    MM_PER_PT,
    PAPER_SPACE_MAX_DENOMINATOR,
    canonical_denominators,
    cluster_denominators,
    denominator_from_c,
    format_scale,
    snap_to_standard,
)


class TestDenominatorFromC(unittest.TestCase):
    def test_mm_per_pt_is_exact(self):
        self.assertAlmostEqual(MM_PER_PT, 25.4 / 72, places=12)

    def test_s17_plan_viewport_is_1_to_100(self):
        self.assertAlmostEqual(denominator_from_c(35.27288), 99.99, places=2)

    def test_s17_plan_viewport_is_1_to_50(self):
        self.assertAlmostEqual(denominator_from_c(17.63849), 50.00, places=2)

    def test_s03_location_inset_is_1_to_500(self):
        self.assertAlmostEqual(denominator_from_c(176.35256), 499.9, places=1)

    def test_s17_location_inset_is_1_to_1250(self):
        self.assertAlmostEqual(denominator_from_c(440.67143), 1249.1, places=1)

    def test_paper_space_viewport_is_1_to_1(self):
        self.assertAlmostEqual(denominator_from_c(0.35279), 1.0, places=2)


class TestSnapToStandard(unittest.TestCase):
    def test_s06_inner_viewport_snaps_to_100(self):
        self.assertEqual(snap_to_standard(99.6), 100.0)

    def test_s17_inset_snaps_to_1250(self):
        self.assertEqual(snap_to_standard(1249.1), 1250.0)

    def test_s03_inset_snaps_to_500(self):
        self.assertEqual(snap_to_standard(499.9), 500.0)

    def test_s13_inner_viewport_snaps_to_nothing(self):
        # 136.4 is 36% from 100 and 32% from 200 — this is the one corpus
        # sheet whose measured scale is not a standard one.
        self.assertIsNone(snap_to_standard(136.4))

    def test_s06_outer_viewport_snaps_to_nothing(self):
        self.assertIsNone(snap_to_standard(146.0))


class TestClusterDenominators(unittest.TestCase):
    """CAD never writes the same scale as the same float, so every value here
    is a real corpus measurement rather than a round number."""

    def test_s04s_two_1_to_50_viewports_form_one_group(self):
        self.assertEqual(len(cluster_denominators([49.995, 50.001])), 1)

    def test_s17s_four_1_to_100_plans_form_one_group_of_four(self):
        groups = cluster_denominators([99.986, 99.988, 99.993, 99.995])
        self.assertEqual([len(g) for g in groups], [4])

    def test_s17s_full_sheet_reduces_to_three_scales(self):
        groups = cluster_denominators(
            [1249.147, 99.986, 99.988, 99.995, 99.993, 49.999])
        self.assertEqual([len(g) for g in groups], [1, 4, 1])

    def test_s03s_full_sheet_reduces_to_three_scales(self):
        self.assertEqual(
            len(cluster_denominators([499.897, 49.99, 99.993, 99.971])), 3)

    def test_genuinely_different_scales_stay_apart(self):
        # s06: an inner 1:99.6 and an outer 1:146 are two real readings.
        self.assertEqual(len(cluster_denominators([99.6, 146.0])), 2)

    def test_an_empty_input_yields_nothing(self):
        self.assertEqual(cluster_denominators([]), [])


class TestCanonicalDenominators(unittest.TestCase):
    def test_one_representative_per_group(self):
        self.assertEqual(
            len(canonical_denominators([99.986, 99.988, 99.993, 99.995])), 1)

    def test_empty_input(self):
        self.assertEqual(canonical_denominators([]), [])


class TestFormatScale(unittest.TestCase):
    def test_whole_number_has_no_decimal(self):
        self.assertEqual(format_scale(100.0), "1:100")

    def test_non_standard_keeps_one_decimal(self):
        self.assertEqual(format_scale(136.4), "1:136.4")


class TestScaleInfoDefaults(unittest.TestCase):
    def test_unresolved_needs_only_a_source(self):
        info = ScaleInfo(denominator=None, source="unresolved")
        self.assertIsNone(info.denominator)
        self.assertIsNone(info.bbox)
        self.assertIsNone(info.raw)
        self.assertIsNone(info.nominal)
        self.assertIsNone(info.conflict)

    def test_paper_space_threshold_excludes_one_to_one(self):
        self.assertLess(1.0, PAPER_SPACE_MAX_DENOMINATOR)
        self.assertGreater(20.0, PAPER_SPACE_MAX_DENOMINATOR)


if __name__ == "__main__":
    unittest.main()
