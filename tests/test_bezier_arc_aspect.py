"""Pins for the Bezier swing-arc bbox-aspect gate (DOOR_BBOX_ASPECT_MIN/MAX).

The gate was widened from [0.85, 1.15] to the polyline path's [0.65, 1.45]
(2026-08-13): a genuine ~77.5deg-sweep swing arc measures bbox aspect 0.804
(mirror 1.244) and the original square-only gate rejected it — measured as
s06's 2-of-10 door recall. The corpus measurement showed the nearest repeated
NON-door family at door scale (fixture/appliance quarter arcs, s02/s05/s12)
sits at aspect >= 1.49, so the upper bound must stay at 1.45.

These tests pin both edges: the newly-admitted band detects, and the fixture
family plus shallow decorative arcs stay rejected.
"""
import math
import unittest

from detection import detect_doors
from detection.doors.arcs import _is_arc_like
from detection.doors.constants import (
    DOOR_ASSEMBLY_LINE_LEAF_BASE, DOOR_BBOX_ASPECT_MAX, DOOR_BBOX_ASPECT_MIN,
    DOOR_GATES_UNSCALED,
)
from models import PathPrimitive


def path(idx: int, item_type: str, points: list[tuple[float, float]]) -> PathPrimitive:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None, fill=None, stroke_width=1.0, dashes="", layer="",
        points=points,
    )


def line(idx: int, p1: tuple[float, float], p2: tuple[float, float]) -> PathPrimitive:
    return path(idx, "l", [p1, p2])


def bezier_arc(idx: int, cx: float, cy: float, r: float,
               start_deg: float, sweep_deg: float,
               scale_x: float = 1.0) -> PathPrimitive:
    """One cubic Bezier approximating a circular arc of the given sweep.

    Standard construction: control-handle length k = (4/3)*tan(sweep/4)*r
    along the endpoint tangents. scale_x != 1 squashes/stretches the arc into
    an ellipse (the fixture/appliance-curve shape measured on s02/s05/s12).
    """
    t0, t1 = math.radians(start_deg), math.radians(start_deg + sweep_deg)
    k = (4.0 / 3.0) * math.tan(math.radians(sweep_deg) / 4.0) * r
    p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
    p3 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
    p1 = (p0[0] - k * math.sin(t0), p0[1] + k * math.cos(t0))
    p2 = (p3[0] + k * math.sin(t1), p3[1] - k * math.cos(t1))
    return path(idx, "c", [(x * scale_x, y) for x, y in (p0, p1, p2, p3)])


def bbox_aspect(p: PathPrimitive) -> float:
    x0, y0, x1, y1 = p.bbox
    return (x1 - x0) / (y1 - y0)


class BezierAspectGateTests(unittest.TestCase):
    def test_partial_sweep_arc_passes_arc_filter(self) -> None:
        # 77.5deg sweep, axis-anchored: aspect 0.803 — the measured s06/s13
        # miss family (real arcs measure 0.804). Rejected by the old
        # [0.85, 1.15] gate; must pass now.
        arc = bezier_arc(0, 100.0, 100.0, 50.0, 0.0, 77.5)
        aspect = bbox_aspect(arc)
        self.assertTrue(DOOR_BBOX_ASPECT_MIN <= aspect < 0.85,
                        f"fixture must sit in the newly-admitted band, got {aspect:.4f}")
        self.assertTrue(_is_arc_like(arc, gates=DOOR_GATES_UNSCALED))

    def test_mirrored_partial_sweep_arc_passes_arc_filter(self) -> None:
        # Same sweep ending on the 90deg axis: bbox transposed, aspect 1.246
        # (the measured 1.244 mirror family on s06/s13).
        arc = bezier_arc(0, 100.0, 100.0, 50.0, 12.5, 77.5)
        aspect = bbox_aspect(arc)
        self.assertTrue(1.15 < aspect <= DOOR_BBOX_ASPECT_MAX,
                        f"fixture must sit in the newly-admitted band, got {aspect:.4f}")
        self.assertTrue(_is_arc_like(arc, gates=DOOR_GATES_UNSCALED))

    def test_partial_sweep_arc_with_leaf_assembles_into_door(self) -> None:
        # End-to-end: the admitted arc + a radius-length leaf line snapped to
        # the arc's endpoint must assemble, exactly like a square quarter arc.
        arc = bezier_arc(0, 100.0, 100.0, 50.0, 0.0, 77.5)
        radius = max(arc.bbox[2] - arc.bbox[0], arc.bbox[3] - arc.bbox[1])
        leaf = line(100, (150.0, 100.0), (150.0 + radius, 100.0))

        doors = detect_doors([arc, leaf], [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies),
                         f"expected 1 assembly, got {[d.evidence.get('method') for d in doors]}")
        self.assertEqual("single_line_leaf", assemblies[0].evidence["assembly_type"])
        self.assertGreaterEqual(assemblies[0].confidence, DOOR_ASSEMBLY_LINE_LEAF_BASE)

    def test_shallow_sweep_arc_still_rejected(self) -> None:
        # A 60deg decorative/furniture arc measures 0.577 — below the widened
        # lower bound. It must stay out, leaf or no leaf.
        arc = bezier_arc(0, 100.0, 100.0, 50.0, 0.0, 60.0)
        aspect = bbox_aspect(arc)
        self.assertLess(aspect, DOOR_BBOX_ASPECT_MIN,
                        f"fixture must sit below the widened bound, got {aspect:.4f}")
        self.assertFalse(_is_arc_like(arc, gates=DOOR_GATES_UNSCALED))

        radius = max(arc.bbox[2] - arc.bbox[0], arc.bbox[3] - arc.bbox[1])
        leaf = line(100, (150.0, 100.0), (150.0 + radius, 100.0))
        doors = detect_doors([arc, leaf], [])
        self.assertEqual([], [d for d in doors if d.evidence.get("method") == "door_assembly"])

    def test_elongated_fixture_arc_still_rejected(self) -> None:
        # The measured non-door family nearest the upper bound: elliptical
        # quarter arcs at door scale (bath/appliance corners; s02 carries
        # ~120 at aspect 1.50-1.76, s05/s12 more at 1.62-1.82, and s12's
        # closest pair sits at 1.494). An x-stretched quarter arc at 1.6 must
        # stay rejected — this is the family that caps DOOR_BBOX_ASPECT_MAX.
        arc = bezier_arc(0, 100.0, 100.0, 50.0, 0.0, 90.0, scale_x=1.6)
        aspect = bbox_aspect(arc)
        self.assertGreater(aspect, DOOR_BBOX_ASPECT_MAX,
                           f"fixture must sit above the widened bound, got {aspect:.4f}")
        self.assertFalse(_is_arc_like(arc, gates=DOOR_GATES_UNSCALED))


if __name__ == "__main__":
    unittest.main()
