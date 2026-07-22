import math
import unittest

from models import PathPrimitive
from detection import detect_doors
from detection.doors.models import _DoorSwing
from detection.doors.sliding import (
    _collect_slide_panels, _detect_sliding_doors, _fit_oriented_rect,
)

WHITE = (1.0, 1.0, 1.0)


def prim(idx, item_type, points, fill=None, sw=0.45, layer=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx,
        item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None,
        fill=fill,
        stroke_width=sw,
        dashes="",
        layer=layer,
        points=[tuple(p) for p in points],
    )


def rect_corners(center, length, thickness, angle_deg):
    theta = math.radians(angle_deg)
    ux, uy = math.cos(theta), math.sin(theta)
    nx, ny = -uy, ux
    cx, cy = center
    hl, ht = length / 2, thickness / 2
    return [
        (cx - ux * hl - nx * ht, cy - uy * hl - ny * ht),
        (cx + ux * hl - nx * ht, cy + uy * hl - ny * ht),
        (cx + ux * hl + nx * ht, cy + uy * hl + ny * ht),
        (cx - ux * hl + nx * ht, cy - uy * hl + ny * ht),
    ]


def qu_panel(idx, center, length, thickness, angle_deg, fill=None):
    return prim(idx, "qu", rect_corners(center, length, thickness, angle_deg), fill=fill)


def white_ring(start_idx, center, length, thickness, angle_deg):
    c = rect_corners(center, length, thickness, angle_deg)
    return [
        prim(start_idx + i, "l", [c[i], c[(i + 1) % 4]], fill=WHITE, sw=0.0)
        for i in range(4)
    ]


def line(idx, p1, p2, sw=0.45):
    return prim(idx, "l", [p1, p2], sw=sw)


def sliding_of(candidates):
    return [
        c for c in candidates
        if c.entity_type == "door" and c.evidence.get("assembly_type") == "sliding"
    ]


def detect(paths, swings=()):
    line_paths = [p for p in paths if p.item_type == "l"]
    candidates, _ = _detect_sliding_doors(
        paths, line_paths, list(swings), [], None, 0,
    )
    return candidates


class OrientedRectFitTests(unittest.TestCase):
    def test_fits_rotated_rectangle(self):
        rect = _fit_oriented_rect(rect_corners((50, 50), 80, 6, 30.0))
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["length"], 80.0, delta=0.5)
        self.assertAlmostEqual(rect["thickness"], 6.0, delta=0.5)
        self.assertAlmostEqual(rect["axis_deg"], 30.0, delta=1.0)

    def test_rejects_non_rectangle(self):
        self.assertIsNone(
            _fit_oriented_rect([(0, 0), (60, 0), (80, 30), (0, 12)])
        )


class LeafPairTests(unittest.TestCase):
    def _pair(self, angle_deg, length=90.0, thickness=6.0, overlap_frac=0.5,
              lateral=0.0, fill=None):
        theta = math.radians(angle_deg)
        ux, uy = math.cos(theta), math.sin(theta)
        nx, ny = -uy, ux
        shift = length * (1 - overlap_frac)
        c1 = (300.0, 300.0)
        c2 = (
            c1[0] + ux * shift + nx * lateral,
            c1[1] + uy * shift + ny * lateral,
        )
        return [
            qu_panel(0, c1, length, thickness, angle_deg, fill=fill),
            qu_panel(1, c2, length, thickness, angle_deg, fill=fill),
        ]

    def test_horizontal_pair_detected(self):
        cands = detect(self._pair(0.0))
        sliding = sliding_of(cands)
        self.assertEqual(len(sliding), 1)
        self.assertEqual(sliding[0].evidence["slide_style"], "leaf_pair")
        self.assertAlmostEqual(sliding[0].confidence, 0.65, places=2)

    def test_rotated_pair_detected(self):
        for angle in (30.0, 90.0, 117.0):
            with self.subTest(angle=angle):
                sliding = sliding_of(detect(self._pair(angle)))
                self.assertEqual(len(sliding), 1)

    def test_scaled_pairs_detected(self):
        for length, thickness in ((40.0, 4.0), (180.0, 12.0)):
            with self.subTest(length=length):
                sliding = sliding_of(detect(
                    self._pair(0.0, length=length, thickness=thickness)
                ))
                self.assertEqual(len(sliding), 1)

    def test_lateral_stack_rejected(self):
        # Wall plies: equal rects offset by a full thickness sideways.
        sliding = sliding_of(detect(self._pair(0.0, lateral=6.0)))
        self.assertEqual(sliding, [])

    def test_near_full_overlap_rejected(self):
        # Duplicated symbol: overlap above the 0.90 ceiling.
        sliding = sliding_of(detect(self._pair(0.0, overlap_frac=0.95)))
        self.assertEqual(sliding, [])

    def test_abutting_rects_rejected(self):
        # Collinear wall segments meeting end-to-end barely overlap.
        sliding = sliding_of(detect(self._pair(0.0, overlap_frac=0.05)))
        self.assertEqual(sliding, [])

    def test_folded_bifold_leaves_rejected(self):
        # Bifold pairs measure 16-20 degrees between leaf axes.
        paths = [
            qu_panel(0, (300.0, 300.0), 90.0, 6.0, 80.0),
            qu_panel(1, (322.0, 300.0), 90.0, 6.0, 100.0),
        ]
        self.assertEqual(sliding_of(detect(paths)), [])

    def test_white_ring_and_qu_representations_merge(self):
        # One panel drawn twice (white fill ring + stroked qu outline) must
        # not pair with itself or double-count against its partner.
        paths = (
            white_ring(0, (300.0, 300.0), 90.0, 6.0, 0.0)
            + [qu_panel(4, (300.0, 300.0), 90.0, 6.0, 0.0)]
            + white_ring(5, (345.0, 300.0), 90.0, 6.0, 0.0)
            + [qu_panel(9, (345.0, 300.0), 90.0, 6.0, 0.0)]
        )
        panels = _collect_slide_panels(paths)
        self.assertEqual(len(panels), 2)
        sliding = sliding_of(detect(paths))
        self.assertEqual(len(sliding), 1)
        self.assertEqual(
            sliding[0].evidence["component_path_indices"],
            list(range(10)),
        )

    def test_end_to_end_detect_doors_dedupes_leaf_fallbacks(self):
        paths = self._pair(0.0)
        candidates = detect_doors(paths, [])
        doors = [c for c in candidates if c.entity_type == "door"]
        self.assertEqual(len(doors), 1)
        self.assertEqual(doors[0].evidence["assembly_type"], "sliding")


class PocketLeafTests(unittest.TestCase):
    def _pocket(self, angle_deg=90.0, with_faces=(True, True), face_cover=0.7,
                white=True, extra=()):
        """A panel pocketed at its -axis end, protruding at the +axis end."""
        length, thickness = 100.0, 6.0
        center = (300.0, 300.0)
        theta = math.radians(angle_deg)
        ux, uy = math.cos(theta), math.sin(theta)
        nx, ny = -uy, ux
        paths = list(white_ring(0, center, length, thickness, angle_deg)) if white else [
            qu_panel(0, center, length, thickness, angle_deg)
        ]
        idx = 10
        face_len = 150.0
        cover_end = -length / 2 + face_cover * length  # axial coord where faces stop
        for side, present in zip((1, -1), with_faces):
            if not present:
                continue
            lat = side * (thickness / 2 + 3.0)
            a = (
                center[0] + ux * (cover_end - face_len) + nx * lat,
                center[1] + uy * (cover_end - face_len) + ny * lat,
            )
            b = (
                center[0] + ux * cover_end + nx * lat,
                center[1] + uy * cover_end + ny * lat,
            )
            paths.append(line(idx, a, b))
            idx += 1
        paths.extend(extra)
        return paths, center, (ux, uy), (nx, ny)

    def test_pocketed_leaf_detected(self):
        paths, _, _, _ = self._pocket()
        sliding = sliding_of(detect(paths))
        self.assertEqual(len(sliding), 1)
        self.assertEqual(sliding[0].evidence["slide_style"], "pocket_leaf")

    def test_rotated_pocket_detected(self):
        paths, _, _, _ = self._pocket(angle_deg=37.0)
        self.assertEqual(len(sliding_of(detect(paths))), 1)

    def test_single_sided_flank_rejected(self):
        # An open hinged leaf lying against a wall face: one side only.
        paths, _, _, _ = self._pocket(with_faces=(True, False))
        self.assertEqual(sliding_of(detect(paths)), [])

    def test_fully_embedded_strip_rejected(self):
        # Faces covering the whole panel: a wall cavity strip, not a leaf.
        paths, _, _, _ = self._pocket(face_cover=1.2)
        self.assertEqual(sliding_of(detect(paths)), [])

    def test_non_white_panel_rejected(self):
        paths, _, _, _ = self._pocket(white=False)
        self.assertEqual(sliding_of(detect(paths)), [])

    def test_obstructed_protrusion_rejected(self):
        # Three crossing lines in the protrusion zone: the "leaf" protrudes
        # into wall continuation (hatch), not into an open doorway.
        paths, center, (ux, uy), (nx, ny) = self._pocket()
        extra = []
        for i, t in enumerate((28.0, 36.0, 44.0)):
            a = (center[0] + ux * t + nx * 8.0, center[1] + uy * t + ny * 8.0)
            b = (center[0] + ux * t - nx * 8.0, center[1] + uy * t - ny * 8.0)
            extra.append(line(50 + i, a, b))
        self.assertEqual(sliding_of(detect(paths + extra)), [])

    def test_swing_overlap_vetoed(self):
        paths, center, _, _ = self._pocket()
        swing = _DoorSwing(
            source="curve_arc",
            bbox=(center[0] - 50, center[1] - 50, center[0] + 50, center[1] + 50),
            radius=100.0,
            pairing_points=[],
            component_path_indices=[],
            layer=None,
            layer_hint=False,
            evidence={},
            arc_endpoints=[],
        )
        self.assertEqual(sliding_of(detect(paths, swings=[swing])), [])


def stroked_ring(start_idx, x0, y0, x1, y1):
    """A closed 4-segment stroked (fill-less) rectangle of `l` items."""
    return [
        line(start_idx + 0, (x0, y0), (x1, y0)),
        line(start_idx + 1, (x1, y0), (x1, y1)),
        line(start_idx + 2, (x1, y1), (x0, y1)),
        line(start_idx + 3, (x0, y1), (x0, y0)),
    ]


class ParkedLeafTests(unittest.TestCase):
    """parked_leaf: a stroked panel parked flush along a wall band that ends
    at a jamb, with a clear opening of ~one panel length beyond it (the
    floor-plans.pdf door_0011 geometry, round numbers)."""

    def _scene(self, far_jamb_y=53.0, with_band_partner=True):
        # Panel ring 3.0 x 50 at x 40.75-43.75, y 100-150; band faces at
        # x=40 / x=33 ending at the jamb y=103 (3px overhang); opening above
        # y 53-103 terminated by the far jamb stub.
        paths = stroked_ring(0, 40.75, 100.0, 43.75, 150.0)
        paths.append(line(10, (40.0, 103.0), (40.0, 170.0)))
        if with_band_partner:
            paths.append(line(11, (33.0, 103.0), (33.0, 170.0)))
        paths.append(line(12, (40.0, far_jamb_y), (40.0, far_jamb_y - 7.0)))
        return paths

    def test_parked_panel_detected(self):
        cands = sliding_of(detect(self._scene()))
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].evidence["slide_style"], "parked_leaf")
        self.assertEqual(cands[0].evidence["leaf_sources"], ["stroked_ring"])
        self.assertAlmostEqual(cands[0].evidence["span_ratio_dev"], 0.06, delta=0.06)
        # The bbox spans the opening, not just the parked panel.
        self.assertLess(cands[0].bbox[1], 60.0)

    def test_span_mismatch_rejected(self):
        # Far jamb at 20px instead of ~50: the slide law fails.
        self.assertEqual(sliding_of(detect(self._scene(far_jamb_y=83.0))), [])

    def test_lone_face_without_band_rejected(self):
        # A shelf line without a band partner is not a wall band.
        self.assertEqual(
            sliding_of(detect(self._scene(with_band_partner=False))), [],
        )

    def test_mid_band_panel_rejected(self):
        # Faces run past both panel ends: no jamb, not parked at an opening.
        paths = stroked_ring(0, 40.75, 100.0, 43.75, 150.0)
        paths.append(line(10, (40.0, 60.0), (40.0, 170.0)))
        paths.append(line(11, (33.0, 60.0), (33.0, 170.0)))
        paths.append(line(12, (40.0, 53.0), (40.0, 46.0)))
        self.assertEqual(sliding_of(detect(paths)), [])

    def test_stroked_rings_never_leaf_pair(self):
        # Two stroked rings in one band would pass every leaf_pair gate, but
        # stroked-only panels are excluded from the pair pool.
        paths = stroked_ring(0, 40.0, 100.0, 43.0, 150.0)
        paths += stroked_ring(4, 40.5, 130.0, 43.5, 180.0)
        self.assertEqual(sliding_of(detect(paths)), [])


if __name__ == "__main__":
    unittest.main()
