"""Scale-aware window gates: WindowGates, threading, and the frozen
classification's behavioral contracts.

Spec: docs/superpowers/specs/2026-08-13-scale-aware-window-gates-design.md.
The classification is 1 W + 15 P + 11 D: only WINDOW_MIN_WIDTH_PX scales
(the opening's empty-space extent); every other px constant is paper-space
ink and must NOT move with the factor.
"""
import math
import unittest

from detection import detect_windows
from detection.windows import (
    WINDOW_MIN_WIDTH_PX, WindowGates, WINDOW_GATES_UNSCALED,
    _facing_cap_pairs, _find_openings, _glaze_index,
)
from tests.test_window_detection import (
    diagonal_window, framed_triple_window, horizontal_window, vertical_window,
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


class TestThreading(unittest.TestCase):
    def test_identity_scale_factor_one_equals_omitted(self):
        # Candidate-for-candidate: bbox, confidence AND evidence must match.
        paths = (horizontal_window(100, 100.0, 176.0, 387.0)
                 + vertical_window(200, 400.0, 477.0, 303.0)
                 + diagonal_window(800, 45)
                 + framed_triple_window(500))
        base = detect_windows(paths)
        explicit = detect_windows(paths, scale_factor=1.0)
        self.assertEqual(len(base), len(explicit))
        for a, b in zip(base, explicit):
            self.assertEqual(a.bbox, b.bbox)
            self.assertEqual(a.confidence, b.confidence)
            self.assertEqual(a.evidence, b.evidence)

    def test_gates_are_keyword_only_and_required(self):
        # findings §4b: a missing gates hand-off must be a TypeError, never
        # a silent unscaled fallback.
        caps = [{"idx": 0, "perp": 0.0, "span": (0.0, 20.0), "len": 20.0},
                {"idx": 1, "perp": 50.0, "span": (0.0, 20.0), "len": 20.0}]
        with self.assertRaises(TypeError):
            list(_facing_cap_pairs(caps))
        with self.assertRaises(TypeError):
            _find_openings(caps, _glaze_index([]))


if __name__ == "__main__":
    unittest.main()
