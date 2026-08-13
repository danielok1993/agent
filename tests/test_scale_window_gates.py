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


from tests.test_window_detection import _rot, hline, path, quad, vline


def rot_paths(prims, cx, cy, deg):
    """Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)."""
    return [path(p.path_index,
                 [_rot(x, y, cx, cy, deg) for x, y in p.points],
                 item_type=p.item_type)
            for p in prims]


class TestMinWidthNegativeControl(unittest.TestCase):
    """The one world-space gate, exercised at a non-grid angle.

    A faithful 1:100 export of a small window: opening width 10px (a 20px
    1:50 window shrunk), ink held at paper values — 3 panes at 2.5px gaps
    (depth 5), 5px caps. Missed at f=1.0 (10 < 14), detected at f=0.5
    (10 >= 7). Fails if the gates threading is removed.
    """

    def _fixture(self, deg=50):
        prims = [
            hline(0, 395.0, 405.0, 397.5),
            hline(1, 395.0, 405.0, 400.0),
            hline(2, 395.0, 405.0, 402.5),
            vline(3, 397.5, 402.5, 395.0),   # cap, 5px
            vline(4, 397.5, 402.5, 405.0),   # cap, 5px
        ]
        return rot_paths(prims, 400.0, 400.0, deg)

    def test_missed_at_identity(self):
        self.assertEqual(detect_windows(self._fixture()), [])

    def test_detected_at_half_scale(self):
        wins = detect_windows(self._fixture(), scale_factor=0.5)
        self.assertEqual(len(wins), 1, f"got {[c.bbox for c in wins]}")
        # Evidence continuity: rooms' _window_seal consumes these (s13 W11).
        from detection.geometry import _angle_diff_mod180
        self.assertEqual(wins[0].evidence["orientation"], "diagonal")
        self.assertLessEqual(
            _angle_diff_mod180(wins[0].evidence["glazing_angle_deg"], 50.0), 4.0)
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)


if __name__ == "__main__":
    unittest.main()
