"""Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5.

A "shrunk world" is a 1:100 export: every COORDINATE halves, every pen
width stays (pens are paper-space). Detection with scale_factor=0.5 must
reproduce the 1:50 result.

Walls half of the suite (Task 3). Task 4 adds the rooms half.
"""
import unittest

from detection import detect_rooms, detect_wall_network
from detection.rooms import ROOM_MIN_AREA_PX2, ROOM_GATES_UNSCALED, RoomGates
from detection.walls import (
    COLLINEAR_OFFSET_TOL, WALL_HATCH_MAX_LEN_PX, WALL_HATCH_MAX_PITCH_PX,
    WALL_JOINERY_BRIDGE_GAP_PX,
    WALL_MAX_THICKNESS_PX, WALL_MIN_THICKNESS_PX, WALL_WEAK_MATERIAL_PER_100PX,
    WallGates, WALL_GATES_UNSCALED, _Seg, _bridge_white_runs,
    _merge_collinear_segs,
)
from tests.test_wall_network import (
    hline, path, vline, wall_band_h, wall_band_v, white_ring,
)


def _hface(y, x0=0.0, x1=100.0):
    """A bare horizontal wall-face _Seg for isolated merge-tolerance tests."""
    return _Seg(p1=(x0, y), p2=(x1, y), stroked=True, stroke_width=1.5)


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


class TestMergeCollinearOffsetScaling(unittest.TestCase):
    """Isolates _merge_collinear_segs's offset-tolerance scaling directly —
    the exact mechanism behind the shrunk-world wall-fusion bug fixed in
    this branch (see docs/scale-normalization-findings.md's COLLINEAR_OFFSET_TOL
    row). Two parallel faces closer than gates.COLLINEAR_OFFSET_TOL apart
    are treated as pieces of the SAME drawn line and fused into one; the
    gate must scale with the detection factor or a shrunk-world wall's own
    face spacing can fall under it and the wall silently disappears.
    """

    def test_offset_at_tolerance_merges_at_f1(self):
        # Today's (pre-branch) boundary behavior, preserved exactly:
        # offset == COLLINEAR_OFFSET_TOL (4.0) does not exceed the gate, so
        # the two faces merge into one run at f=1.0.
        faces = [_hface(0.0), _hface(COLLINEAR_OFFSET_TOL)]
        merged = _merge_collinear_segs(faces, gap_px=0.0, gates=WALL_GATES_UNSCALED)
        self.assertEqual(len(merged), 1)

    def test_same_offset_does_not_merge_once_scaled_down(self):
        # The fixed mechanism: the SAME 4.0px paper offset as above, but at
        # f=0.5 gates.COLLINEAR_OFFSET_TOL scales to 2.0 — 4.0 > 2.0, so the
        # two faces of a shrunk-world wall correctly stay distinct instead
        # of fusing into a single (unpairable) line.
        faces = [_hface(0.0), _hface(COLLINEAR_OFFSET_TOL)]
        gates = WallGates.at(0.5)
        self.assertEqual(gates.COLLINEAR_OFFSET_TOL, 2.0)
        merged = _merge_collinear_segs(faces, gap_px=0.0, gates=gates)
        self.assertEqual(len(merged), 2)

    def test_offset_within_scaled_tolerance_still_merges(self):
        # Not every close pair at f=0.5 is a real wall: an offset genuinely
        # inside the scaled tolerance (1.0 < 2.0) is still drafting jitter
        # of the same line and merges, same as it would at any factor.
        faces = [_hface(0.0), _hface(1.0)]
        gates = WallGates.at(0.5)
        merged = _merge_collinear_segs(faces, gap_px=0.0, gates=gates)
        self.assertEqual(len(merged), 1)


class TestBridgeWhiteRunsGapScaling(unittest.TestCase):
    """_bridge_white_runs is detect_rooms's ONLY production call site
    (detection/rooms.py, solid_parts += _bridge_white_runs(white_walls)),
    and it used to pass no gates — silently running the bridging at the
    unscaled 80px WALL_JOINERY_BRIDGE_GAP_PX on every non-1:50 sheet. At
    f=0.5 that unscaled gap is double the correctly-scaled reach (40px),
    the over-bridging failure class _bridge_white_runs's own docstring
    warns about. gates is now keyword-only and REQUIRED (finding 2), so a
    future missed gates= at this cross-module call site is a TypeError,
    not silent unscaled behavior.

    A world gap of 90px does not qualify at f=1.0 (90 > WALL_JOINERY_
    BRIDGE_GAP_PX 80) — the base case does not bridge. Its 0.5-shrunk twin
    (45px) must reproduce that SAME outcome under correctly-scaled gates
    (WALL_JOINERY_BRIDGE_GAP_PX * 0.5 = 40; 45 > 40, still no bridge) —
    but bridges incorrectly under the unscaled default (45 < 80), which is
    exactly the bug this branch fixes.
    """

    def test_base_gap_exceeds_unscaled_reach_no_bridge(self):
        a = white_ring(100, 100, 140, 110)
        b = white_ring(230, 100, 270, 110)  # gap = 230 - 140 = 90
        self.assertAlmostEqual(a.poly.distance(b.poly), 90.0)
        self.assertEqual(
            _bridge_white_runs([a, b], gates=WallGates.at(1.0)), []
        )

    def test_shrunk_twin_still_exceeds_scaled_reach_no_bridge(self):
        a = white_ring(50.0, 50.0, 70.0, 55.0)
        b = white_ring(115.0, 50.0, 135.0, 55.0)  # gap = 115 - 70 = 45
        self.assertAlmostEqual(a.poly.distance(b.poly), 45.0)
        gates = WallGates.at(0.5)
        self.assertEqual(gates.WALL_JOINERY_BRIDGE_GAP_PX, 40.0)
        self.assertEqual(_bridge_white_runs([a, b], gates=gates), [])

    def test_blind_shrunk_twin_over_bridges_on_unscaled_gates(self):
        # The negative control: the SAME shrunk-twin rings, but run with
        # the unscaled default (the bug being fixed) — 45 < 80 wrongly
        # qualifies and bridges the gap that should stay open at f=0.5.
        a = white_ring(50.0, 50.0, 70.0, 55.0)
        b = white_ring(115.0, 50.0, 135.0, 55.0)
        bridges = _bridge_white_runs([a, b], gates=WALL_GATES_UNSCALED)
        self.assertEqual(len(bridges), 1)

    def test_gates_is_keyword_only_and_required(self):
        a = white_ring(100, 100, 140, 110)
        b = white_ring(230, 100, 270, 110)
        with self.assertRaises(TypeError):
            _bridge_white_runs([a, b])


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


def rooms_for(paths, scale_factor=1.0, page=(700.0, 600.0)):
    network = detect_wall_network(paths, scale_factor=scale_factor)
    return detect_rooms(network, [], [], page[0], page[1],
                        scale_factor=scale_factor)


class TestRoomGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = RoomGates.at(1.0)
        self.assertEqual(g.ROOM_MIN_AREA_PX2, ROOM_MIN_AREA_PX2)

    def test_areas_scale_by_factor_squared(self):
        g = RoomGates.at(0.5)
        self.assertEqual(g.ROOM_MIN_AREA_PX2, ROOM_MIN_AREA_PX2 * 0.25)

    def test_wall_hatch_max_len_matches_wallgates_scaling(self):
        # RoomGates duplicates the walls-owned constant identically to
        # WallGates so the two stages can never disagree about a wall's
        # size (rooms.py's _is_barrier_face reads it from here).
        g = RoomGates.at(0.5)
        self.assertEqual(g.WALL_HATCH_MAX_LEN_PX, WALL_HATCH_MAX_LEN_PX * 0.5)


class TestRoomsScaled(unittest.TestCase):
    def test_identity_factor_equals_omitted(self):
        paths = room_box_walls()
        a = rooms_for(paths)
        b = rooms_for(paths, scale_factor=1.0)
        self.assertEqual(len(a), len(b))
        self.assertEqual([c.bbox for c in a], [c.bbox for c in b])

    def test_shrunk_world_room_still_detected(self):
        paths = room_box_walls()
        base = rooms_for(paths)
        shrunk = rooms_for(shrink(paths), scale_factor=0.5,
                           page=(350.0, 300.0))
        self.assertEqual(len(base), len(shrunk))
        self.assertEqual(len(shrunk), 1)

    def test_area_floor_applies_at_f_squared(self):
        # A 58x58 interior (3364px² > 2500 floor) detects at 1:50. Its
        # shrunk twin is 29x29 = 841px² — BELOW the unscaled floor, above
        # the f² floor (625). Scale-aware detection keeps it; the blind
        # run is the negative control.
        t = 8.0
        small = (wall_band_h(0, 100, 174 + t, 100, t)
                 + wall_band_h(2, 100, 174 + t, 166, t)
                 + wall_band_v(4, 100, 100, 166 + t, t)
                 + wall_band_v(6, 166, 100, 166 + t, t))
        base = rooms_for(small, page=(300.0, 300.0))
        self.assertEqual(len(base), 1)
        shrunk = rooms_for(shrink(small), scale_factor=0.5,
                           page=(150.0, 150.0))
        self.assertEqual(len(shrunk), 1)
        blind = rooms_for(shrink(small), scale_factor=1.0,
                          page=(150.0, 150.0))
        self.assertEqual(len(blind), 0)   # eaten by the unscaled area floor


class TestOrchestratorForwardsFactor(unittest.TestCase):
    def test_run_heuristics_scale_factor_reaches_rooms(self):
        from detection import run_heuristics
        from models import PageData
        paths = shrink(room_box_walls())
        pd = PageData(page_number=1, width_px=350.0, height_px=300.0,
                      page_type="vector-rich", paths=paths, text_spans=[],
                      images=[])
        scaled = run_heuristics(pd, [], scale_factor=0.5)
        blind = run_heuristics(pd, [])
        rooms_scaled = [c for c in scaled if c.entity_type == "room"]
        rooms_blind = [c for c in blind if c.entity_type == "room"]
        self.assertEqual(len(rooms_scaled), 1)
        # The blind (unscaled) run loses the room entirely: the shrunk
        # walls' 4px face spacing falls at/under the unscaled 4.0px
        # COLLINEAR_OFFSET_TOL and fuses into one unpairable line — proof
        # the factor reaches run_heuristics all the way through to rooms,
        # not just that it changes some intermediate pathway.
        self.assertEqual(len(rooms_blind), 0)


if __name__ == "__main__":
    unittest.main()
