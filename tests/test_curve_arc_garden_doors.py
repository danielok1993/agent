"""Garden-door detection for native single-Bezier (`curve_arc`) swings.

The polyline-arc detector handles the garden-door pattern via
``_split_double_arc`` when both halves are drawn as `l`-segment chains
joined by BFS. When each half is instead a single native `c` (cubic
Bezier) that individually passes ``_is_arc_like``, the two arcs never
meet in the BFS pipeline — they become independent `curve_arc` swings.
``_collect_door_swings`` post-processes those swings, detects pairs that
share an arc endpoint with antiparallel walk-direction tangents (the
~180° break from §3.7), and stamps ``double_arc_partner_paths`` on each
so the existing garden-pass merge fires unchanged.

This file covers that detection end-to-end via ``detect_doors``.
"""
import math
import unittest

from heuristics import detect_doors
from models import PathPrimitive


# k = (4/3) * tan(pi/8) — the standard "magic constant" for approximating
# a quarter circle with a single cubic Bezier. Each control point sits at
# distance k*r along the tangent from the endpoint.
_BEZIER_QUARTER_K = 0.5522847498


def _curve(idx: int, pts: list[tuple[float, float]]) -> PathPrimitive:
    assert len(pts) == 4
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return PathPrimitive(
        path_index=idx,
        item_type="c",
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None, fill=None, stroke_width=0.75, dashes="",
        layer=None, points=pts,
    )


def _line(idx: int, p1: tuple[float, float], p2: tuple[float, float]) -> PathPrimitive:
    xs = (p1[0], p2[0]); ys = (p1[1], p2[1])
    return PathPrimitive(
        path_index=idx,
        item_type="l",
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None, fill=None, stroke_width=0.75, dashes="",
        layer=None, points=[p1, p2],
    )


def _quarter_arc_bezier(
    idx: int,
    hinge: tuple[float, float],
    free_end: tuple[float, float],
    sweep_end: tuple[float, float],
) -> PathPrimitive:
    """Build a cubic Bezier approximating the 90° quarter circle centered at
    ``hinge`` (the door's pivot) and going from ``free_end`` to ``sweep_end``.

    Both endpoints must be at distance r=|hinge → free_end| = |hinge → sweep_end|.
    The tangent at each endpoint is perpendicular to the radius and oriented
    along the chord direction. Control points sit at distance k*r along
    those tangents.
    """
    hx, hy = hinge
    r = math.hypot(free_end[0] - hx, free_end[1] - hy)
    assert abs(math.hypot(sweep_end[0] - hx, sweep_end[1] - hy) - r) < 1e-6

    # Tangent at free_end (perpendicular to radius, pointing toward sweep_end)
    rx0, ry0 = free_end[0] - hx, free_end[1] - hy
    t0x, t0y = -ry0, rx0  # rotate radius 90° CCW
    # Pick the rotation direction that points toward sweep_end
    if (t0x * (sweep_end[0] - free_end[0]) + t0y * (sweep_end[1] - free_end[1])) < 0:
        t0x, t0y = ry0, -rx0
    n0 = math.hypot(t0x, t0y)
    t0x, t0y = t0x / n0, t0y / n0

    # Tangent at sweep_end (perpendicular to radius, pointing back toward free_end)
    rx1, ry1 = sweep_end[0] - hx, sweep_end[1] - hy
    t1x, t1y = -ry1, rx1
    if (t1x * (free_end[0] - sweep_end[0]) + t1y * (free_end[1] - sweep_end[1])) < 0:
        t1x, t1y = ry1, -rx1
    n1 = math.hypot(t1x, t1y)
    t1x, t1y = t1x / n1, t1y / n1

    c1 = (free_end[0] + _BEZIER_QUARTER_K * r * t0x,
          free_end[1] + _BEZIER_QUARTER_K * r * t0y)
    c2 = (sweep_end[0] + _BEZIER_QUARTER_K * r * t1x,
          sweep_end[1] + _BEZIER_QUARTER_K * r * t1y)

    return _curve(idx, [free_end, c1, c2, sweep_end])


class CurveArcGardenDoorTests(unittest.TestCase):
    def test_two_single_beziers_sharing_endpoint_merge_as_garden_door(self) -> None:
        """The 5-1133-WD03.pdf door_0007 + door_0008 topology, simplified.

        Two stacked quarter arcs sharing one endpoint (the meeting point of
        the two free ends), each paired with a horizontal leaf line at the
        opposite outer end. Reference geometry:
            upper hinge at (100, 100) — leaf 100→200 at y=100
            lower hinge at (100, 300) — leaf 100→200 at y=300
            both arcs sweep to the shared point (100, 200).
        """
        # Upper arc: hinge TL=(100,100), leaf attaches at TR=(200,100),
        # sweeps to BL=(100,200) which is the shared point.
        upper = _quarter_arc_bezier(0, hinge=(100, 100),
                                     free_end=(200, 100), sweep_end=(100, 200))
        # Lower arc: hinge BL=(100,300), leaf attaches at BR=(200,300),
        # sweeps to TL=(100,200) which is the same shared point.
        lower = _quarter_arc_bezier(1, hinge=(100, 300),
                                     free_end=(200, 300), sweep_end=(100, 200))

        upper_leaf = _line(2, (100, 100), (200, 100))
        lower_leaf = _line(3, (100, 300), (200, 300))

        candidates = detect_doors([upper, lower, upper_leaf, lower_leaf], [])
        doors = [c for c in candidates if c.entity_type == "door"
                 and c.evidence.get("method") == "door_assembly"]

        # Exactly one merged garden-door candidate; the two halves got
        # consumed by _merge_double_door_assemblies.
        double_swings = [
            c for c in doors
            if c.evidence.get("assembly_type") == "double_swing"
            and c.evidence.get("swing_layout") == "garden"
        ]
        self.assertEqual(
            1, len(double_swings),
            f"expected one garden double_swing, got {len(double_swings)} "
            f"out of door_assembly candidates: "
            f"{[(c.candidate_id, c.evidence.get('assembly_type'), c.evidence.get('swing_layout')) for c in doors]}",
        )

        merged = double_swings[0]
        # Combined bbox should span both halves (y=100 to y=300, x=100 to x=200)
        x0, y0, x1, y1 = merged.bbox
        self.assertAlmostEqual(x0, 100.0, delta=1.0)
        self.assertAlmostEqual(y0, 100.0, delta=1.0)
        self.assertAlmostEqual(x1, 200.0, delta=1.0)
        self.assertAlmostEqual(y1, 300.0, delta=1.0)

        # No leftover single_line_leaf candidates for these arcs (both consumed).
        single_line = [
            c for c in doors
            if c.evidence.get("assembly_type") == "single_line_leaf"
        ]
        self.assertEqual(
            0, len(single_line),
            f"halves should be consumed by the merge, got {len(single_line)} single_line_leaf",
        )

    def test_smooth_s_curve_continuation_not_treated_as_garden(self) -> None:
        """Two arcs sharing an endpoint with continuous tangent (smooth
        S-curve) must NOT be paired as a garden door. The tangent break
        across the shared point is ~0°, well below the 45° threshold.

        Geometry: arc A is the upper-left quarter of the circle centered
        at (100, 0); walking it forward arrives at (100, 100) going
        rightward. Arc B is the upper-right quarter of the circle centered
        at (100, 200); walking it BACKWARD from (100, 100) toward
        (200, 200) departs going rightward as well — a smooth horizontal
        S-curve. The walk-direction tangents at the shared point are
        parallel.

        Critically, this distinguishes the garden-door pattern (mirror,
        antiparallel walk-tangents → ~180° break, MATCH) from a true
        smooth continuation (parallel walk-tangents → ~0° break, NO MATCH).
        """
        arc_a = _quarter_arc_bezier(0, hinge=(100, 0),
                                     free_end=(0, 0), sweep_end=(100, 100))
        arc_b = _quarter_arc_bezier(1, hinge=(100, 200),
                                     free_end=(200, 200), sweep_end=(100, 100))

        # Leaf lines so each arc has a paired assembly (otherwise no
        # candidates are emitted and the negative assertion is vacuous).
        leaf_a = _line(2, (0, 0), (100, 0))         # horizontal at y=0
        leaf_b = _line(3, (200, 200), (100, 200))   # horizontal at y=200

        candidates = detect_doors([arc_a, arc_b, leaf_a, leaf_b], [])
        doors = [c for c in candidates if c.entity_type == "door"
                 and c.evidence.get("method") == "door_assembly"]

        garden = [
            c for c in doors
            if c.evidence.get("assembly_type") == "double_swing"
            and c.evidence.get("swing_layout") == "garden"
        ]
        self.assertEqual(
            0, len(garden),
            f"smooth S-curve must not match as garden, got {len(garden)}: "
            f"{[(c.candidate_id, c.evidence.get('assembly_type'), c.evidence.get('swing_layout')) for c in doors]}",
        )


if __name__ == "__main__":
    unittest.main()
