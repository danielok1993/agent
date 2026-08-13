"""Scale-aware window gates: WindowGates, threading, and the frozen
classification's behavioral contracts.

Spec: docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md.
The classification is 1 W + 15 P + 11 D: only WINDOW_MIN_WIDTH_PX scales
(the opening's empty-space extent); every other px constant is paper-space
ink and must NOT move with the factor.
"""
import math
import unittest

from detection.windows import (
    WINDOW_MIN_WIDTH_PX, WindowGates, WINDOW_GATES_UNSCALED,
)


class TestWindowGates(unittest.TestCase):
    def test_identity_at_factor_one_is_exact(self):
        g = WindowGates.at(1.0)
        self.assertEqual(g.factor, 1.0)
        self.assertEqual(g.WINDOW_MIN_WIDTH_PX, WINDOW_MIN_WIDTH_PX)
        self.assertEqual(WINDOW_GATES_UNSCALED, g)

    def test_scaling_at_half(self):
        g = WindowGates.at(0.5)
        self.assertEqual(g.WINDOW_MIN_WIDTH_PX, 7.0)

    def test_clamp_domain_bounds_construct(self):
        # The pipeline clamps f to [0.25, 4.0]; both bounds must construct
        # with the raw product (floor inert on the calibrated domain).
        self.assertEqual(WindowGates.at(0.25).WINDOW_MIN_WIDTH_PX, 3.5)
        self.assertEqual(WindowGates.at(4.0).WINDOW_MIN_WIDTH_PX, 56.0)

    def test_floor_engages_below_clamp_domain(self):
        # Backstop only: a sub-pixel width floor is never a window gate.
        self.assertEqual(WindowGates.at(0.05).WINDOW_MIN_WIDTH_PX, 1.0)

    def test_nonpositive_factor_asserts(self):
        with self.assertRaises(AssertionError):
            WindowGates.at(0.0)
        with self.assertRaises(AssertionError):
            WindowGates.at(-1.0)


if __name__ == "__main__":
    unittest.main()
