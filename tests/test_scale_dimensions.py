"""scale/dimensions.py: the drawing's ticked dimension strings as a scale
measurement — the matcher itself is exercised in test_takeoff_plausibility.py
(it moved here from takeoff/plausibility.py unchanged); this file pins the
measurement the detection gates read off it."""
import unittest

from scale.dimensions import (
    DIM_AGREE_TOL, DIM_DISAGREE_TOL, DIM_MIN_MATCHES, DimensionMatch, agreement,
    measured_denominator,
)


def match(implied, x=50.0, y=50.0, line=True):
    return DimensionMatch(value_mm=1000.0,
                          length_px=1000.0 / (implied * 25.4 / 150),
                          implied_denominator=implied,
                          line=((x - 10.0, y), (x + 10.0, y)) if line else None)


class TestMeasuredDenominator(unittest.TestCase):
    def test_needs_min_matches(self):
        self.assertEqual(DIM_MIN_MATCHES, 3)
        self.assertIsNone(measured_denominator([match(50.0)] * 2))
        self.assertEqual(measured_denominator([match(50.0)] * 3), 50.0)

    def test_median_not_mean(self):
        ms = [match(50.0), match(50.2), match(49.9), match(500.0)]   # one mis-pair
        self.assertAlmostEqual(measured_denominator(ms), 50.1)

    def test_region_filter_uses_the_line_midpoint(self):
        inside = [match(92.2, x=250.0)] * 3
        outside = [match(50.0, x=50.0)] * 3
        self.assertAlmostEqual(
            measured_denominator(inside + outside, (200, 0, 300, 100)), 92.2)
        self.assertAlmostEqual(
            measured_denominator(inside + outside, (0, 0, 100, 100)), 50.0)
        self.assertIsNone(measured_denominator(inside, (0, 0, 100, 100)))

    def test_a_match_without_a_line_counts_page_wide_only(self):
        ms = [match(92.2, line=False)] * 3
        self.assertAlmostEqual(measured_denominator(ms), 92.2)
        self.assertIsNone(measured_denominator(ms, (0, 0, 100, 100)))


class TestAgreement(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(DIM_AGREE_TOL, 0.05)
        self.assertEqual(DIM_DISAGREE_TOL, 0.15)
        self.assertEqual(agreement(50.6, 50.0), "ok")
        self.assertEqual(agreement(54.0, 50.0), "inconclusive")
        self.assertEqual(agreement(92.2, 50.0), "implausible")     # s01 typed 1:50
        self.assertEqual(agreement(92.2, 92.2), "ok")              # s01 stored 1:92.2


if __name__ == "__main__":
    unittest.main()
