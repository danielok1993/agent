"""End-to-end door scale behavior on FAITHFUL 1:100 fixtures.

A faithful 1:100 export scales EXTENTS and holds PAPER quantities fixed —
pen widths AND drawn ink separations. A blanket x0.5 of every coordinate is
NOT faithful: it halves the leaf-companion and fold-line separations that
real 1:100 sheets keep at ~2.6px, and that artifact accounted for all four
of s01's residual shrunk-world misses (spec §1).
"""
import math
import unittest

from detection import detect_doors, run_heuristics
from models import PageData, PathPrimitive
from tests.test_folding_doors import folding_of
from tests.test_sliding_doors import line, qu_panel, sliding_of


def prim(idx, item_type, points, stroke_width=1.0, fill=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0, 0, 0), fill=fill, stroke_width=stroke_width,
        dashes=None, layer="", points=points)


def swing_door(base_idx, cx, cy, radius, leaf_sep=2.5):
    """Quarter-arc + a double-line leaf, as a faithful export at any scale.

    radius is a WORLD extent and scales with the drawing.
    leaf_sep is PAPER ink separation and does NOT scale — that is the whole
    point of this fixture builder.
    """
    k = 0.5523 * radius
    arc = prim(base_idx, "c",
               [(cx + radius, cy), (cx + radius, cy + k),
                (cx + k, cy + radius), (cx, cy + radius)])
    leaf_a = prim(base_idx + 1, "l", [(cx, cy), (cx, cy + radius)])
    leaf_b = prim(base_idx + 2, "l", [(cx - leaf_sep, cy), (cx - leaf_sep, cy + radius)])
    return [arc, leaf_a, leaf_b]


def open_v_door(base_idx, hinge, leaf_len, fold_deg, leaf_sep, jamb_len, far_extra=8.0):
    """A lone half-open bifold V (folding.py's open_v pattern): two double-line
    oblique leaves hinged at `hinge`, mirrored about the tip-to-tip axis. One
    tip is anchored by a jamb line of length jamb_len; the far tip's opening
    span is closed by a far-jamb stub placed exactly at the span-law distance
    (leaf_len * 2) along that axis.

    leaf_len and jamb_len are WORLD extents and scale with the drawing.
    leaf_sep is PAPER ink separation (the double-line gap of one leaf) and
    does NOT scale — modeled on tests/test_folding_doors.py's OpenVTests
    fixture (floor-plans.pdf paths 1739-1742), reused via its `line` builder.
    """
    half = math.radians(fold_deg / 2.0)
    H = hinge

    def leaf_lines(idx, ang):
        ux, uy = math.cos(ang), math.sin(ang)
        nx, ny = -math.sin(ang), math.cos(ang)
        tip = (H[0] + leaf_len * ux, H[1] + leaf_len * uy)
        e2p = (H[0] + leaf_sep * nx, H[1] + leaf_sep * ny)
        e2q = (tip[0] + leaf_sep * nx, tip[1] + leaf_sep * ny)
        return [line(idx, H, tip), line(idx + 1, e2p, e2q)], (nx, ny)

    la, (nxa, nya) = leaf_lines(base_idx, half)
    lb, _ = leaf_lines(base_idx + 2, -half)

    # Effective tips as folding.py computes them (midpoint of the two edges'
    # far corners, i.e. offset by leaf_sep/2 along the leaf's own normal).
    tip_a = (H[0] + leaf_len * math.cos(half) + nxa * leaf_sep / 2,
              H[1] + leaf_len * math.sin(half) + nya * leaf_sep / 2)
    tip_b = (H[0] + leaf_len * math.cos(-half) - nxa * leaf_sep / 2,
              H[1] + leaf_len * math.sin(-half) - nya * leaf_sep / 2)
    tip_span = math.dist(tip_a, tip_b)
    vx, vy = (tip_b[0] - tip_a[0]) / tip_span, (tip_b[1] - tip_a[1]) / tip_span

    # Anchor jamb: starts exactly at tip_a (0 offset — always within the
    # anchor-tolerance gate regardless of factor) and runs AWAY from tip_b.
    idx = base_idx + 4
    jamb_end = (tip_a[0] - jamb_len * vx, tip_a[1] - jamb_len * vy)
    anchor = line(idx, tip_a, jamb_end)
    idx += 1

    # Far jamb stub: one endpoint exactly on-axis at span == leaf_len * 2
    # (the span law: unfolded leaves must cover the opening), well past
    # tip_span so it reads as "beyond the far tip".
    leaf_run = leaf_len * 2
    far_pt = (tip_a[0] + leaf_run * vx, tip_a[1] + leaf_run * vy)
    far_pt2 = (far_pt[0] + far_extra * vx, far_pt[1] + far_extra * vy)
    far = line(idx, far_pt, far_pt2)

    return la + lb + [anchor, far]


def leaf_pair_door(base_idx, length, thickness, overlap_frac=0.5, angle_deg=0.0):
    """Two parallel panel rectangles in-band with partial overlap (sliding.py's
    leaf_pair pattern), reusing tests/test_sliding_doors.py's `qu_panel`
    builder. length and thickness are both WORLD extents of a drawn
    rectangle — the panel LENGTH and the panel's drawn THICKNESS both scale
    with the drawing."""
    shift = length * (1 - overlap_frac)
    theta = math.radians(angle_deg)
    ux, uy = math.cos(theta), math.sin(theta)
    c1 = (300.0, 300.0)
    c2 = (c1[0] + ux * shift, c1[1] + uy * shift)
    return [
        qu_panel(base_idx, c1, length, thickness, angle_deg),
        qu_panel(base_idx + 1, c2, length, thickness, angle_deg),
    ]


def page(paths):
    return PageData(
        page_number=1, width_px=1000, height_px=1000,
        paths=paths, text_spans=[], images=[], ocg_names=[])


class TestFaithfulExportDetection(unittest.TestCase):
    def test_1to50_door_detected_at_factor_one(self):
        doors = detect_doors(swing_door(0, 200, 200, 50), [], None, scale_factor=1.0)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))

    def test_faithful_1to100_door_detected_at_factor_half(self):
        # Extents halved, leaf_sep held at its paper value. radius=15 (not
        # 25) so the arc trips the unscaled DOOR_MIN_SIZE_PX=20 floor when
        # the negative-control test applies factor=1.0 gates to it — 25 sits
        # above that floor at either factor and detects regardless of
        # threading, which would make the negative control vacuous.
        paths = swing_door(0, 100, 100, 15, leaf_sep=2.5)
        doors = detect_doors(paths, [], None, scale_factor=0.5)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))

    def test_negative_control_same_door_missed_when_unscaled(self):
        # If the threading is removed, this door is invisible. A regression
        # that silently drops gates makes THIS test fail.
        paths = swing_door(0, 100, 100, 15, leaf_sep=2.5)
        doors = detect_doors(paths, [], None, scale_factor=1.0)
        self.assertFalse(any(c.confidence >= 0.55 for c in doors))

    def test_paper_space_invariance_separation_must_not_scale(self):
        # leaf_sep 4.0px is under the unscaled 5.0px companion gate but OVER
        # a wrongly-scaled 2.5px one. Scaling DOOR_LEAF_COMPANION_PERP_PX
        # would break this — it is the s06 wipeout as a unit test.
        paths = swing_door(0, 100, 100, 15, leaf_sep=4.0)
        doors = detect_doors(paths, [], None, scale_factor=0.5)
        self.assertTrue(any(c.confidence >= 0.55 for c in doors))


class TestOrchestratorWiring(unittest.TestCase):
    def test_run_heuristics_forwards_scale_factor_to_doors(self):
        # radius=15: below the unscaled DOOR_MIN_SIZE_PX=20 floor, so this
        # only detects if run_heuristics actually forwards scale_factor=0.5
        # into detect_doors — the exact wiring this test pins.
        paths = swing_door(0, 100, 100, 15, leaf_sep=2.5)
        got = run_heuristics(page(paths), [], disable_windows=True,
                             disable_rooms=True, scale_factor=0.5)
        self.assertTrue(any(c.entity_type == "door" and c.confidence >= 0.55
                            for c in got))

    def test_run_heuristics_identity_at_one(self):
        paths = swing_door(0, 200, 200, 50)
        a = run_heuristics(page(paths), [], disable_windows=True, disable_rooms=True)
        b = run_heuristics(page(paths), [], disable_windows=True,
                           disable_rooms=True, scale_factor=1.0)
        self.assertEqual([c.bbox for c in a], [c.bbox for c in b])


class TestFoldingScaleBehavior(unittest.TestCase):
    """open_v (detection/doors/folding.py) reads gates.DOOR_FOLD_JAMB_ANCHOR_TOL_PX,
    gates.DOOR_FOLD_JAMB_LINE_MIN_LEN_PX, and gates.DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX
    at their _open_v_match read sites. The fixture is a shrunk (1:100-faithful)
    door: leaf_len=20 and jamb_len=10 are WORLD extents (half of a 40/20
    1:50 reference), leaf_sep=2.0 is a PAPER separation held fixed."""

    def _shrunk_open_v(self):
        return open_v_door(
            0, hinge=(300.0, 300.0), leaf_len=20.0, fold_deg=70.0,
            leaf_sep=2.0, jamb_len=10.0,
        )

    def test_shrunk_open_v_detected_at_factor_half(self):
        doors = detect_doors(self._shrunk_open_v(), [], None, scale_factor=0.5)
        folds = folding_of(doors)
        self.assertEqual(len(folds), 1)
        self.assertEqual(folds[0].evidence["fold_style"], "open_v")
        self.assertGreaterEqual(folds[0].confidence, 0.55)

    def test_shrunk_open_v_missed_when_unscaled(self):
        # jamb_len=10 is below the unscaled DOOR_FOLD_JAMB_LINE_MIN_LEN_PX=15
        # floor but above its factor=0.5 floor of 7.5 — a regression that
        # drops the folding gates threading makes this door invisible again.
        doors = detect_doors(self._shrunk_open_v(), [], None, scale_factor=1.0)
        self.assertEqual(folding_of(doors), [])


class TestSlidingScaleBehavior(unittest.TestCase):
    """leaf_pair (detection/doors/sliding.py) reads gates.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX
    (and gates.DOOR_MIN_SIZE_PX) at _panel_shape_ok, gating _collect_slide_panels
    before leaf_pair pairing ever runs. The fixture is a shrunk (1:100-faithful)
    door: length=30 and thickness=2.5 are both WORLD extents of a drawn
    rectangle (half of a 60/5.0 1:50 reference) — a drawn panel's thickness is
    itself a world dimension, unlike the swing leaf's ink separation."""

    def _shrunk_leaf_pair(self):
        return leaf_pair_door(0, length=30.0, thickness=2.5)

    def test_shrunk_leaf_pair_detected_at_factor_half(self):
        doors = detect_doors(self._shrunk_leaf_pair(), [], None, scale_factor=0.5)
        sliding = sliding_of(doors)
        self.assertEqual(len(sliding), 1)
        self.assertEqual(sliding[0].evidence["slide_style"], "leaf_pair")
        self.assertGreaterEqual(sliding[0].confidence, 0.55)

    def test_shrunk_leaf_pair_missed_when_unscaled(self):
        # thickness=2.5 is below the unscaled DOOR_SLIDE_PANEL_MIN_THICKNESS_PX=3.0
        # floor but above its factor=0.5 floor of 1.5 — a regression that
        # drops the sliding gates threading makes this door invisible again.
        doors = detect_doors(self._shrunk_leaf_pair(), [], None, scale_factor=1.0)
        self.assertEqual(sliding_of(doors), [])


if __name__ == "__main__":
    unittest.main()
