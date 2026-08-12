"""Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5.

A "shrunk world" is a 1:100 export: every COORDINATE halves, every pen
width stays (pens are paper-space). Detection with scale_factor=0.5 must
reproduce the 1:50 result.

Walls half of the suite (Task 3). Task 4 adds the rooms half.
"""
import unittest

from detection import detect_wall_network
from detection.walls import (
    WALL_HATCH_MAX_LEN_PX, WALL_HATCH_MAX_PITCH_PX, WALL_MAX_THICKNESS_PX,
    WALL_MIN_THICKNESS_PX, WALL_WEAK_MATERIAL_PER_100PX, WallGates,
    WALL_GATES_UNSCALED,
)
from tests.test_wall_network import hline, path, vline, wall_band_h, wall_band_v


def shrink(paths, s=0.5):
    """Scale coordinates by s, keep stroke widths — a 1:100 export."""
    out = []
    for p in paths:
        pts = [(x * s, y * s) for (x, y) in p.points]
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
        out.append(type(p)(
            path_index=p.path_index, item_type=p.item_type,
            bbox=(min(xs), min(ys), max(xs), max(ys)),
            color=p.color, fill=p.fill,
            stroke_width=p.stroke_width,      # paper-space: NOT scaled
            dashes=p.dashes, layer=p.layer, points=pts))
    return out


def room_box_walls(thickness=8.0):
    """A closed 400x300 room drawn as four double-line wall bands."""
    t = thickness
    return (wall_band_h(0, 100, 500, 100, t) + wall_band_h(2, 100, 500, 400, t)
            + wall_band_v(4, 100, 100, 400 + t, t)
            + wall_band_v(6, 500, 100, 400 + t, t))


class TestWallGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = WallGates.at(1.0)
        self.assertEqual(g.WALL_MAX_THICKNESS_PX, WALL_MAX_THICKNESS_PX)
        self.assertEqual(g.WALL_MIN_THICKNESS_PX, WALL_MIN_THICKNESS_PX)
        self.assertEqual(g.WALL_HATCH_MAX_LEN_PX, WALL_HATCH_MAX_LEN_PX)
        self.assertEqual(g.WALL_HATCH_MAX_PITCH_PX, WALL_HATCH_MAX_PITCH_PX)
        self.assertEqual(
            g.WALL_WEAK_MATERIAL_PER_100PX, WALL_WEAK_MATERIAL_PER_100PX)
        self.assertEqual(g.WALL_WEAK_MATERIAL_PER_100PX, 3.0)

    def test_world_gates_scale_linearly(self):
        g = WallGates.at(0.5)
        self.assertEqual(g.WALL_MAX_THICKNESS_PX, WALL_MAX_THICKNESS_PX * 0.5)
        self.assertEqual(g.WALL_HATCH_MAX_LEN_PX, WALL_HATCH_MAX_LEN_PX * 0.5)
        self.assertEqual(
            g.WALL_HATCH_MAX_PITCH_PX, WALL_HATCH_MAX_PITCH_PX * 0.5)

    def test_weak_material_density_scales_inversely(self):
        # WALL_WEAK_MATERIAL_PER_100PX is a density (marks per 100 paper-px
        # of band length): world-spaced marks pack 2x tighter per paper-px
        # at f=0.5, so the minimum must RISE, not shrink — divide, not
        # multiply. See docs/scale-normalization-findings.md §4 row.
        g = WallGates.at(0.5)
        self.assertEqual(g.WALL_WEAK_MATERIAL_PER_100PX, 6.0)
        g1 = WallGates.at(1.0)
        self.assertEqual(g1.WALL_WEAK_MATERIAL_PER_100PX, 3.0)

    def test_min_thickness_floored_at_one_pixel(self):
        g = WallGates.at(0.25)   # 2.0 * 0.25 = 0.5 -> floored
        self.assertEqual(g.WALL_MIN_THICKNESS_PX, 1.0)

    def test_ordering_floors_hold_at_clamp_bounds(self):
        for f in (0.25, 0.5, 1.0, 2.0, 4.0):
            g = WallGates.at(f)
            self.assertLess(g.WALL_MIN_THICKNESS_PX, g.WALL_MAX_THICKNESS_PX)
            self.assertLess(g.WALL_MAX_THICKNESS_PX,
                            g.WALL_THICK_MATERIAL_MAX_PX)

    def test_hatch_len_and_rung_floor_stay_equal_at_every_factor(self):
        # Both constants are W and scale by the identical factor, so their
        # 1:50 relationship (currently exactly equal, 48.0 == 48.0) holds
        # unchanged at every scale — no clamp, no collision.
        for f in (0.25, 0.5, 1.0, 2.0, 4.0):
            g = WallGates.at(f)
            self.assertEqual(
                g.WALL_HATCH_MAX_LEN_PX, g.WALL_LATTICE_MIN_RUNG_LEN_PX)


class TestWallNetworkScaled(unittest.TestCase):
    def test_identity_factor_equals_omitted(self):
        paths = room_box_walls()
        base = detect_wall_network(paths)
        same = detect_wall_network(paths, scale_factor=1.0)
        self.assertEqual(len(base.segments), len(same.segments))
        for a, b in zip(base.segments, same.segments):
            self.assertEqual((a.p1, a.p2, a.thickness_px),
                             (b.p1, b.p2, b.thickness_px))

    def test_shrunk_world_reproduces_wall_network(self):
        paths = room_box_walls(thickness=8.0)
        base = detect_wall_network(paths)
        shrunk = detect_wall_network(shrink(paths), scale_factor=0.5)
        self.assertEqual(len(base.segments), len(shrunk.segments))

    def test_shrunk_thick_wall_still_pairs(self):
        # 30px band at 1:50 (under the 36 cap) becomes 15px at 1:100 —
        # trivially under an UNscaled cap too; the discriminating case is
        # the inverse: a 60px band at 1:50 must NOT pair (over cap), and
        # its 30px shrunk twin must ALSO not pair at f=0.5 (over 18px cap).
        wide = wall_band_h(100, 100, 500, 100, thickness=60.0)
        filler = room_box_walls()  # so the network clears WALL_NETWORK_MIN_SEGMENTS
        base = detect_wall_network(filler + wide)
        n_base = len(base.segments)
        shrunk = detect_wall_network(shrink(filler + wide), scale_factor=0.5)
        self.assertEqual(n_base, len(shrunk.segments))

    def test_unscaled_run_on_shrunk_world_differs(self):
        # The negative control: WITHOUT the factor, the 60px-at-1:50 band
        # shrinks to 30px and wrongly pairs under the unscaled 36px cap.
        wide = wall_band_h(100, 100, 500, 100, thickness=60.0)
        filler = room_box_walls()
        base = detect_wall_network(filler + wide)
        blind = detect_wall_network(shrink(filler + wide))  # no factor
        self.assertNotEqual(len(base.segments), len(blind.segments))


if __name__ == "__main__":
    unittest.main()
