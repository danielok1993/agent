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
