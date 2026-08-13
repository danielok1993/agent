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


class TestPaperInvariance(unittest.TestCase):
    """One fixture per paper-space family (spec §Testing). Each fails if its
    named constant is wrongly given a WindowGates field."""

    def _detect(self, prims, cx=400.0, cy=400.0):
        return detect_windows(rot_paths(prims, cx, cy, 50), scale_factor=0.5)

    def test_adj_spacing_held_at_paper(self):
        # WINDOW_GLAZING_ADJ_SPACING_PX: s16's 8.25px convention at f=0.5.
        # Scaled (4.25) the band breaks and the window dies.
        prims = [hline(0, 380.0, 420.0, 395.875), hline(1, 380.0, 420.0, 404.125),
                 vline(2, 391.15, 408.85, 380.0), vline(3, 391.15, 408.85, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_band_depth_held_at_paper(self):
        # WINDOW_GLAZING_THICKNESS_PX: s13's 13px-deep 3-pane convention.
        # Scaled (8) the band truncates to its 2-pane suffix — assert on the
        # pane count, since the truncated window can still detect.
        prims = [hline(0, 380.0, 420.0, 393.5), hline(1, 380.0, 420.0, 400.0),
                 hline(2, 380.0, 420.0, 406.5),
                 vline(3, 393.0, 407.0, 380.0), vline(4, 393.0, 407.0, 420.0)]
        wins = self._detect(prims)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)

    def test_cap_length_held_at_paper(self):
        # WINDOW_CAP_MAX_LEN_PX: 22px caps (s01 convention) with a shrunk
        # 40px opening. Scaled (18) the caps leave the pool and nothing pairs.
        prims = [hline(0, 380.0, 420.0, 396.5), hline(1, 380.0, 420.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_two_line_min_cap_not_scaled(self):
        # WINDOW_TWO_LINE_MIN_CAP_PX: a 2-pane sliver with 9px caps must stay
        # REJECTED at f=0.5 (9 < 12). Scaled (6) it would be admitted.
        prims = [hline(0, 390.0, 410.0, 398.5), hline(1, 390.0, 410.0, 401.5),
                 vline(2, 395.5, 404.5, 390.0), vline(3, 395.5, 404.5, 410.0)]
        self.assertEqual(self._detect(prims), [])

    def test_distinct_eps_not_scaled(self):
        # WINDOW_GLAZING_DISTINCT_EPS: a double-struck pane (1.2px apart)
        # must still dedupe to ONE pane at f=0.5. Scaled (0.75) it splits and
        # the pane count inflates to 3.
        prims = [hline(0, 380.0, 420.0, 398.0), hline(1, 380.0, 420.0, 399.2),
                 hline(2, 380.0, 420.0, 402.2),
                 vline(3, 393.0, 407.0, 380.0), vline(4, 393.0, 407.0, 420.0)]
        wins = self._detect(prims)
        self.assertEqual(len(wins), 1)
        self.assertEqual(wins[0].evidence["glazing_lines"], 2)

    def test_tight_pair_gates_not_scaled(self):
        # WINDOW_TIGHT_PAIR_GAP_PX + WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX: a
        # doubled-material-edge FP (2.0px pair, jamb margin 1.0 via the
        # asymmetric caps) must stay rejected at f=0.5. Scaling EITHER gate
        # admits it (gap 2.0 >= 1.375 skips the test; margin 1.0 >= 0.75
        # passes it). Cap span is 14px (not the 12px WINDOW_TWO_LINE_MIN_CAP_PX
        # boundary) so post-rotation float noise can't tip that unrelated gate.
        prims = [hline(0, 380.0, 420.0, 397.0), hline(1, 380.0, 420.0, 399.0),
                 vline(2, 396.0, 410.0, 380.0), vline(3, 396.0, 410.0, 420.0)]
        self.assertEqual(self._detect(prims), [])

    def test_span_overshoot_held_at_paper(self):
        # WINDOW_SPAN_OVERSHOOT_PX: glazing overshooting each cap by 9px
        # (confirmed 1:100 windows reach 9.38) must still span. Scaled (6)
        # the panes are excluded and the window dies.
        prims = [hline(0, 371.0, 429.0, 396.5), hline(1, 371.0, 429.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_span_cover_tol_held_at_paper(self):
        # WINDOW_SPAN_COVER_TOL_PX: glazing falling 3.4px short of each cap
        # (confirmed tiers reach 3.38-3.55) must still span. Scaled (2) it dies.
        prims = [hline(0, 383.4, 416.6, 396.5), hline(1, 383.4, 416.6, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_span_perp_tol_held_at_paper(self):
        # WINDOW_SPAN_PERP_TOL_PX: a pane sitting 2.0px outside the caps'
        # facing extent must still join the band (tol 2.0). Scaled (1.0) it
        # is excluded, the band drops to one pane, and the window dies. 2.0px
        # (not 1.5) leaves margin against the +-4deg angle-grid frames the
        # cap-orientation sweep tries alongside the exact one.
        prims = [hline(0, 380.0, 420.0, 389.0),   # 2.0px above the cap span
                 hline(1, 380.0, 420.0, 396.5),
                 vline(2, 391.0, 408.0, 380.0),   # caps span y 391..408
                 vline(3, 391.0, 408.0, 420.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_interior_band_pad_held_at_paper(self):
        # WINDOW_INTERIOR_BAND_PAD_PX: a hatched wall whose crosshatch quads
        # sit 1.0px outside the pane band must still be REJECTED (pad 1.5
        # sweeps them into the interior scan; 2 shapes > SHAPE_MAX 1).
        # Scaled (0.75) the pad no longer reaches them and the FP is admitted.
        prims = [hline(0, 380.0, 420.0, 396.5), hline(1, 380.0, 420.0, 403.5),
                 vline(2, 389.0, 411.0, 380.0), vline(3, 389.0, 411.0, 420.0),
                 quad(4, 390.0, 404.5, 394.0, 404.7),
                 quad(5, 400.0, 404.5, 404.0, 404.7)]
        self.assertEqual(self._detect(prims), [])

    def test_framed_multi_light_ink_held_at_paper(self):
        # WINDOW_BLOCK_CAP_MAX_THICK_PX + WINDOW_MULLION_GAP_MAX_PX: a
        # half-width three-light frame whose block bars keep their 6px
        # thickness and 11.5px mullion gaps. Scaled (4 / 7) the blocks stop
        # being caps / the chains stop bridging.
        prims = [
            hline(0, 926.2, 1057.2, 267.2),                 # top rail
            hline(1, 926.2, 1057.2, 282.0),                 # bottom rail
            quad(2, 926.2, 267.2, 932.2, 282.0),            # left end cap
            quad(3, 1051.2, 267.2, 1057.2, 282.0),          # right end cap
            quad(4, 968.2, 267.2, 974.2, 282.0),            # mullion pair 1
            quad(5, 974.2, 267.2, 979.7, 282.0),
            quad(6, 1011.2, 267.2, 1017.2, 282.0),          # mullion pair 2
            quad(7, 1017.2, 267.2, 1022.7, 282.0),
            hline(8, 932.2, 968.2, 274.7),                  # center, light 1
            hline(9, 979.7, 1011.2, 274.7),                 # center, light 2
            hline(10, 1022.7, 1051.2, 274.7),               # center, light 3
        ]
        wins = detect_windows(rot_paths(prims, 990.0, 275.0, 50),
                              scale_factor=0.5)
        self.assertEqual(len(wins), 1, f"got {[c.bbox for c in wins]}")
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)
        self.assertEqual(wins[0].evidence["lights"], 3)

    def test_max_width_held_at_paper(self):
        # WINDOW_MAX_WIDTH_PX: a 200px-wide 2-pane window (s18's 210px
        # confirmed window family). Unscaled 280 accepts; wrongly scaled
        # (140) rejects the pair and the window dies.
        prims = [hline(0, 300.0, 500.0, 396.5), hline(1, 300.0, 500.0, 403.5),
                 vline(2, 389.0, 411.0, 300.0), vline(3, 389.0, 411.0, 500.0)]
        self.assertEqual(len(self._detect(prims)), 1)

    def test_cap_min_len_not_scaled(self):
        # WINDOW_CAP_MIN_LEN_PX: cap ink is paper-space, so 2.5px "caps" at
        # f=0.5 are noise, correctly rejected by the unscaled 3.0 floor.
        # Wrongly scaled (1.5) they qualify and a phantom window forms.
        prims = [hline(0, 390.0, 410.0, 397.5), hline(1, 390.0, 410.0, 400.0),
                 hline(2, 390.0, 410.0, 402.5),
                 vline(3, 398.75, 401.25, 390.0), vline(4, 398.75, 401.25, 410.0)]
        self.assertEqual(self._detect(prims), [])


if __name__ == "__main__":
    unittest.main()
