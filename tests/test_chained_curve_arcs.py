import math
import unittest

from detection import detect_doors
from detection.doors.arcs import _fit_circle_3pt, _native_curve_chains
from detection.doors.constants import DOOR_CURVE_CHAIN_MIN_CURVES, DOOR_MIN_SIZE_PX
from models import PathPrimitive, TextSpan


def _curve(
    idx: int,
    pts: list[tuple[float, float]],
    *,
    layer: str | None = None,
) -> PathPrimitive:
    """Build a native cubic Bezier (`c`) primitive from 4 control points."""
    assert len(pts) == 4, "cubic Bezier requires exactly 4 control points"
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return PathPrimitive(
        path_index=idx,
        item_type="c",
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None,
        fill=None,
        stroke_width=0.75,
        dashes="",
        layer=layer,
        points=pts,
    )


def _qu_leaf(idx: int, x0: float, y0: float, x1: float, y1: float) -> PathPrimitive:
    """Build a `qu` rectangle primitive shaped like a door leaf."""
    return PathPrimitive(
        path_index=idx,
        item_type="qu",
        bbox=(x0, y0, x1, y1),
        color=None,
        fill=None,
        stroke_width=1.0,
        dashes="",
        layer=None,
        points=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
    )


def _circle_arc_chain(
    start_idx: int,
    n_curves: int,
    center: tuple[float, float],
    radius: float,
    start_angle_deg: float,
    end_angle_deg: float,
) -> list[PathPrimitive]:
    """Build `n_curves` cubic Bezier primitives chained end-to-end, each
    spanning an equal angular slice of the circle from start_angle to
    end_angle. Each Bezier's 4 control points are sampled from the actual
    circle so endpoints chain exactly."""
    cx, cy = center
    chain: list[PathPrimitive] = []
    total = end_angle_deg - start_angle_deg
    for i in range(n_curves):
        a0 = math.radians(start_angle_deg + total * i / n_curves)
        a3 = math.radians(start_angle_deg + total * (i + 1) / n_curves)
        a1 = math.radians(start_angle_deg + total * (i + 0.33) / n_curves)
        a2 = math.radians(start_angle_deg + total * (i + 0.67) / n_curves)
        pts = [
            (cx + radius * math.cos(a0), cy + radius * math.sin(a0)),
            (cx + radius * math.cos(a1), cy + radius * math.sin(a1)),
            (cx + radius * math.cos(a2), cy + radius * math.sin(a2)),
            (cx + radius * math.cos(a3), cy + radius * math.sin(a3)),
        ]
        chain.append(_curve(start_idx + i, pts))
    return chain


class FitCircle3PtTests(unittest.TestCase):
    def test_three_axis_aligned_points_on_unit_circle(self) -> None:
        """Trivial sanity check on the formula: 3 points on a circle of
        radius 5 centered at origin recover that center and radius."""
        result = _fit_circle_3pt((5.0, 0.0), (0.0, 5.0), (-5.0, 0.0))
        self.assertIsNotNone(result)
        cx, cy, r = result
        self.assertAlmostEqual(0.0, cx, places=6)
        self.assertAlmostEqual(0.0, cy, places=6)
        self.assertAlmostEqual(5.0, r, places=6)

    def test_three_points_on_offset_circle(self) -> None:
        """Recover an offset center and radius from a different angular spread."""
        cx, cy, r_true = 100.0, 200.0, 80.0
        a1, a2, a3 = 30, 75, 130
        p1 = (cx + r_true * math.cos(math.radians(a1)),
              cy + r_true * math.sin(math.radians(a1)))
        p2 = (cx + r_true * math.cos(math.radians(a2)),
              cy + r_true * math.sin(math.radians(a2)))
        p3 = (cx + r_true * math.cos(math.radians(a3)),
              cy + r_true * math.sin(math.radians(a3)))
        result = _fit_circle_3pt(p1, p2, p3)
        self.assertIsNotNone(result)
        cx_fit, cy_fit, r_fit = result
        self.assertAlmostEqual(cx, cx_fit, places=3)
        self.assertAlmostEqual(cy, cy_fit, places=3)
        self.assertAlmostEqual(r_true, r_fit, places=3)

    def test_collinear_points_return_none(self) -> None:
        """Three collinear points have no unique circumscribed circle."""
        result = _fit_circle_3pt((0.0, 0.0), (5.0, 0.0), (10.0, 0.0))
        self.assertIsNone(result)


class NativeCurveChainsTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        self.assertEqual([], _native_curve_chains([]))

    def test_single_curve_yields_singleton_chain(self) -> None:
        curve = _curve(0, [(0.0, 0.0), (10.0, 5.0), (20.0, 10.0), (30.0, 15.0)])
        chains = _native_curve_chains([curve])
        self.assertEqual(1, len(chains))
        self.assertEqual([0], [c.path_index for c in chains[0]])

    def test_two_curves_sharing_endpoint_join_into_one_chain(self) -> None:
        """The door_0051 pattern: native curves with shared endpoints group
        into a single chain even when they're far apart on the page."""
        # Curve A ends at (50, 30); Curve B starts at the same point.
        a = _curve(0, [(0.0, 0.0), (15.0, 10.0), (35.0, 20.0), (50.0, 30.0)])
        b = _curve(1, [(50.0, 30.0), (65.0, 40.0), (85.0, 55.0), (100.0, 70.0)])
        chains = _native_curve_chains([a, b])
        self.assertEqual(1, len(chains))
        self.assertEqual({0, 1}, {c.path_index for c in chains[0]})

    def test_two_curves_with_disjoint_endpoints_stay_separate(self) -> None:
        a = _curve(0, [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])
        b = _curve(1, [(100.0, 100.0), (101.0, 100.0), (102.0, 100.0), (103.0, 100.0)])
        chains = _native_curve_chains([a, b])
        self.assertEqual(2, len(chains))


class ChainedCurveSwingDetectionTests(unittest.TestCase):
    """End-to-end via detect_doors: a 5-curve chain forming a 30° arc of
    a larger circle, paired with a leaf whose length matches the underlying
    circle's true radius (not the chain's bbox span)."""

    def test_chained_curves_partial_arc_pairs_with_leaf_via_fitted_radius(self) -> None:
        # 81-px radius circle, hinge at (1168, 549). Leaf is the vertical
        # panel from (1166, 468) to (1171, 549) — length 81. The visible
        # arc fragment spans angles 270° to 240° (a 30° slice near the top
        # of the leaf), drawn as a 5-curve chain.
        center = (1168.0, 549.0)
        radius = 81.0
        chain = _circle_arc_chain(
            start_idx=0,
            n_curves=5,
            center=center,
            radius=radius,
            start_angle_deg=270.0,
            end_angle_deg=240.0,
        )
        leaf = _qu_leaf(100, 1166.0, 468.0, 1171.0, 549.0)
        paths = chain + [leaf]

        candidates = detect_doors(paths, [])
        doors = [c for c in candidates if c.entity_type == "door"]

        # At least one door_assembly was emitted — the chain WAS detected
        # as an arc swing despite each curve being <20 px.
        self.assertTrue(
            any(c.evidence.get("method") == "door_assembly" for c in doors),
            f"no door_assembly emitted; got {[c.evidence.get('method') for c in doors]}",
        )
        assembly = next(
            c for c in doors if c.evidence.get("method") == "door_assembly"
        )
        # The arc_source must indicate it came from chained native curves.
        self.assertEqual(
            "curve_arc_chain",
            assembly.evidence.get("arc_source"),
            f"expected curve_arc_chain, got {assembly.evidence.get('arc_source')}",
        )

    def test_singleton_full_quarter_arc_still_uses_existing_path(self) -> None:
        """A single `c` primitive that already passes _is_arc_like (square
        bbox, size >= 20) keeps using the legacy curve_arc path. The new
        chained logic only fires when the chain has >=2 curves OR a single
        curve fails the existing aspect/size filter."""
        # Single big Bezier arc, square bbox, radius 80
        center = (100.0, 100.0)
        radius = 80.0
        chain = _circle_arc_chain(
            start_idx=0,
            n_curves=1,  # single curve
            center=center,
            radius=radius,
            start_angle_deg=0.0,
            end_angle_deg=90.0,
        )
        leaf = _qu_leaf(100, 178.0, 96.0, 182.0, 180.0)  # vertical 4x84 leaf
        paths = chain + [leaf]

        candidates = detect_doors(paths, [])
        doors = [c for c in candidates if c.entity_type == "door"]
        assemblies = [
            c for c in doors if c.evidence.get("method") == "door_assembly"
        ]
        # An assembly was emitted; check it used the legacy single-curve path,
        # not the new chained path.
        self.assertTrue(
            len(assemblies) >= 1,
            "expected a door_assembly from the single-curve quarter arc",
        )
        # All assemblies should report curve_arc (not curve_arc_chain).
        for a in assemblies:
            self.assertEqual("curve_arc", a.evidence.get("arc_source"))


if __name__ == "__main__":
    unittest.main()
