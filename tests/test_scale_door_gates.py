"""Scale-factor behavior of the door gates: identity at 1.0, linear at 0.5.

A "faithful 1:100 export" scales EXTENTS and keeps PAPER quantities — pen
widths and drawn ink separations — unchanged. See
docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md §1/§2.
"""
import unittest

from detection.doors.constants import (
    DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_FOLD_LEAF_LINE_SEP_MAX_PX,
    DOOR_LEAF_COMPANION_PERP_PX, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_SLIDE_PANEL_MIN_THICKNESS_PX, DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
    DOOR_GATES_UNSCALED, DoorGates,
)


class TestDoorGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = DoorGates.at(1.0)
        self.assertEqual(g.DOOR_MIN_SIZE_PX, DOOR_MIN_SIZE_PX)
        self.assertEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX)
        self.assertEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_ASSEMBLY_CONNECT_TOL_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX)
        self.assertEqual(g, DOOR_GATES_UNSCALED)

    def test_world_gates_scale_linearly(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX,
                               DOOR_ASSEMBLY_CONNECT_TOL_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
                               DOOR_SLIDE_PANEL_MAX_THICKNESS_PX * 0.5)

    def test_min_size_floored_at_one_pixel(self):
        # Floor is a backstop: at the f=0.25 clamp the raw product is 5.0px,
        # so it is inert on the calibrated domain.
        self.assertAlmostEqual(DoorGates.at(0.25).DOOR_MIN_SIZE_PX,
                               DOOR_MIN_SIZE_PX * 0.25)
        self.assertEqual(DoorGates.at(0.001).DOOR_MIN_SIZE_PX, 1.0)

    def test_rejects_non_positive_factor(self):
        # The ONLY assertion: factor-independent, so a failure is a bug.
        with self.assertRaises(AssertionError):
            DoorGates.at(0.0)
        with self.assertRaises(AssertionError):
            DoorGates.at(-1.0)

    def test_paper_space_constants_have_no_field(self):
        # Absence from the dataclass is what makes "does not scale" reviewable.
        g = DoorGates.at(0.5)
        for name in ("DOOR_LEAF_COMPANION_PERP_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MIN_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MAX_PX",
                     "DOOR_POLYLINE_ENDPOINT_TOL",
                     "DOOR_LABEL_SEARCH_RADIUS_PX",
                     "DOOR_FOLD_HINGE_TOL_PX",
                     "DOOR_BBOX_ASPECT_MIN", "DOOR_BBOX_ASPECT_MAX"):
            self.assertFalse(hasattr(g, name), f"{name} is P or D — must not be a gates field")

    def test_cross_class_inversion_is_a_no_op_not_a_crash(self):
        # DOOR_FOLD_LEAF_LINE_SEP_MAX_PX (P, 4.0) vs
        # DOOR_SLIDE_PANEL_MIN_THICKNESS_PX (W, 3.0*f) invert below f=0.75 —
        # every 1:100 sheet. They gate DIFFERENT detectors and are never
        # compared, so nothing may assert or clamp the ordering. This test
        # exists so nobody "fixes" the crossing later.
        g = DoorGates.at(0.5)
        self.assertLess(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                        DOOR_FOLD_LEAF_LINE_SEP_MAX_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX * 0.5)


from detection import detect_doors
from detection.doors.arcs import _collect_door_swings, _is_arc_like
from models import PathPrimitive


def prim(idx, item_type, points, stroke_width=1.0, fill=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0, 0, 0), fill=fill, stroke_width=stroke_width,
        dashes=None, layer="", points=points)


def quarter_bezier(idx, cx, cy, r):
    """A quarter-arc cubic Bezier of radius r, hinged at (cx, cy).

    r is a WORLD extent: it halves on a 1:100 export.
    """
    k = 0.5523 * r
    return prim(idx, "c", [(cx + r, cy), (cx + r, cy + k), (cx + k, cy + r), (cx, cy + r)])


class TestArcGatesThreading(unittest.TestCase):
    def test_is_arc_like_requires_gates_keyword(self):
        p = quarter_bezier(0, 100, 100, 50)
        with self.assertRaises(TypeError):
            _is_arc_like(p)          # no gates -> must NOT silently run unscaled

    def test_small_arc_rejected_at_f1_accepted_at_half(self):
        # radius 12 -> size 12px: under the 20px floor at f=1.0, over the
        # scaled 10px floor at f=0.5.
        p = quarter_bezier(0, 100, 100, 12)
        self.assertFalse(_is_arc_like(p, gates=DoorGates.at(1.0)))
        self.assertTrue(_is_arc_like(p, gates=DoorGates.at(0.5)))

    def test_collect_swings_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_swings([quarter_bezier(0, 100, 100, 50)])

    def test_detect_doors_identity_factor_equals_omitted(self):
        paths = [quarter_bezier(0, 100, 100, 50)]
        self.assertEqual(
            [c.bbox for c in detect_doors(paths, [])],
            [c.bbox for c in detect_doors(paths, [], None, scale_factor=1.0)])


from detection.doors.leaves import _collect_door_leaves


class TestLeafGatesThreading(unittest.TestCase):
    def test_collect_leaves_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_leaves([])

    def test_short_leaf_rect_rejected_at_f1_accepted_at_half(self):
        # A 12 x 2.5 px leaf rectangle: length under the 20px DOOR_MIN_SIZE_PX
        # floor at f=1.0, over the scaled 10px floor at f=0.5. Aspect 4.8
        # clears DOOR_LEAF_ASPECT_MIN (4.0, dimensionless) at both factors.
        leaf = prim(0, "qu", [(0, 0), (12, 0), (12, 2.5), (0, 2.5)])
        self.assertEqual(_collect_door_leaves([leaf], gates=DoorGates.at(1.0)), [])
        self.assertEqual(len(_collect_door_leaves([leaf], gates=DoorGates.at(0.5))), 1)

    def test_leaf_companion_separation_is_paper_space(self):
        # DOOR_LEAF_COMPANION_PERP_PX is P: it must NOT move with the factor.
        # Measured: real leaf separations hold at ~2.6px on 1:100 sheets
        # (spec §2), so a 4px separation must stay acceptable at f=0.5.
        from detection.doors.constants import DOOR_LEAF_COMPANION_PERP_PX
        self.assertFalse(hasattr(DoorGates.at(0.5), "DOOR_LEAF_COMPANION_PERP_PX"))
        self.assertEqual(DOOR_LEAF_COMPANION_PERP_PX, 5.0)
