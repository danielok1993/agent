import unittest

from models import ScaleInfo
from takeoff.units import (
    MM_PER_PX_AT_1_1, effective_denominator, mm_per_px, px_to_m, px2_to_m2,
)


class TestUnits(unittest.TestCase):
    def test_one_pixel_is_150dpi_paper(self):
        self.assertAlmostEqual(MM_PER_PX_AT_1_1, 0.16933, places=5)

    def test_mm_per_px_scales_with_denominator(self):
        self.assertAlmostEqual(mm_per_px(50.0), 8.4667, places=3)
        self.assertAlmostEqual(mm_per_px(100.0), 16.933, places=3)

    def test_118px_at_1_50_is_one_metre(self):
        self.assertAlmostEqual(px_to_m(118.11, 50.0), 1.0, places=3)

    def test_13948px2_at_1_50_is_one_square_metre(self):
        self.assertAlmostEqual(px2_to_m2(13948.0, 50.0), 1.0, places=3)

    def test_area_at_1_100_is_four_times_smaller_per_px2(self):
        self.assertAlmostEqual(px2_to_m2(13948.0, 100.0), 4.0, places=2)


class TestEffectiveDenominator(unittest.TestCase):
    def test_nominal_beats_raw(self):
        info = ScaleInfo(denominator=49.8, source="text", nominal=50.0)
        self.assertEqual(effective_denominator(info), 50.0)

    def test_raw_when_no_nominal(self):
        info = ScaleInfo(denominator=136.4, source="viewport", nominal=None)
        self.assertEqual(effective_denominator(info), 136.4)

    def test_unresolved_is_none(self):
        self.assertIsNone(effective_denominator(
            ScaleInfo(denominator=None, source="unresolved")))
        self.assertIsNone(effective_denominator(None))
