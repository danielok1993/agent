import math
import unittest

from heuristics import (
    DOOR_POLYLINE_CHAIN_DELTA_DEG,
    DOOR_POLYLINE_CYCLE_MAX_SEGMENTS,
    DOOR_POLYLINE_MIN_SEGMENTS,
    DOOR_POLYLINE_SPUR_MAX_SEGMENTS,
    _prune_arc_cycle_caps,
    _prune_arc_spurs,
    _trim_chain_extension_caps,
)
from models import PathPrimitive


def _seg(idx: int, p1: tuple[float, float], p2: tuple[float, float]):
    """Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like
    the segs entries inside _detect_polyline_arc_bboxes."""
    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0])) % 180.0
    path = PathPrimitive(
        path_index=idx,
        item_type="l",
        bbox=(min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
        color=None,
        fill=None,
        stroke_width=1.0,
        dashes="",
        layer=None,
        points=[p1, p2],
    )
    return (path, p1, p2, length, angle)


def _arc(start_idx: int, n_segs: int, radius: float = 50.0):
    """Quarter-circle polyline as n_segs short straight lines."""
    pts = [
        (
            radius * math.cos((math.pi / 2) * i / n_segs),
            radius * math.sin((math.pi / 2) * i / n_segs),
        )
        for i in range(n_segs + 1)
    ]
    return [_seg(start_idx + i, pts[i], pts[i + 1]) for i in range(n_segs)]


def _chain(start_idx: int, points: list[tuple[float, float]]):
    """Polyline through the given points: segs from points[0]→points[1] etc."""
    return [
        _seg(start_idx + i, points[i], points[i + 1])
        for i in range(len(points) - 1)
    ]


class PruneArcSpursTests(unittest.TestCase):
    def test_clean_arc_unchanged(self) -> None:
        """An 11-segment polyline arc has two degree-1 endpoints and no
        junction — nothing is prunable."""
        segs = _arc(0, n_segs=11)
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)

    def test_pure_cycle_unchanged(self) -> None:
        """A closed 4-segment loop has every vertex at degree 2 — no leaf
        exists to walk from, so nothing is pruned."""
        # Square loop: (0,0)→(50,0)→(50,50)→(0,50)→(0,0)
        segs = _chain(0, [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0), (0.0, 0.0)])
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)

    def test_short_branches_at_y_junction_removed(self) -> None:
        """11-segment arc whose far endpoint is a degree-3 junction because
        two 1-segment branches connect there. Both branches are short spurs
        and should be pruned, leaving the 11 arc segments."""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Arc's far endpoint: (radius*cos(pi/2), radius*sin(pi/2)) = (0, 50).
        # Two 1-seg branches off that vertex make it degree-3.
        branch_a = _chain(100, [(0.0, 50.0), (-3.0, 53.0)])
        branch_b = _chain(200, [(0.0, 50.0), (3.0, 53.0)])
        segs = arc + branch_a + branch_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # 11 arc segs (path indices 0..10) survive; both branch segs pruned.
        self.assertEqual(list(range(11)), pruned)
        self.assertEqual({100, 200}, removed)

    def test_dual_spurs_at_one_junction(self) -> None:
        """linework_1318 shape: 11-segment arc whose far endpoint becomes a
        degree-3+ junction because two 2-segment spurs branch off it. Both
        spurs (4 segments total) should be pruned."""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Arc's far endpoint is (0, 50). Branch two spurs.
        spur_a = _chain(100, [(0.0, 50.0), (-5.0, 55.0), (-10.0, 60.0)])
        spur_b = _chain(200, [(0.0, 50.0), (5.0, 55.0), (10.0, 60.0)])
        segs = arc + spur_a + spur_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(list(range(11)), pruned)
        self.assertEqual({100, 101, 200, 201}, removed)

    def test_oversized_branch_kept_at_y_junction(self) -> None:
        """A Y-junction with one short branch (2 segs) and one long branch
        (5 segs, > DOOR_POLYLINE_SPUR_MAX_SEGMENTS). The short branch is
        pruned; the long branch's walk exceeds the spur cap and is kept.
        After short-branch removal, the junction collapses to degree 2 and
        the long branch becomes a chain extension of the arc."""
        arc = _arc(0, n_segs=11, radius=50.0)
        short = _chain(100, [(0.0, 50.0), (-3.0, 53.0), (-6.0, 56.0)])  # 2 segs
        long = _chain(200, [
            (0.0, 50.0), (5.0, 55.0), (10.0, 60.0),
            (15.0, 65.0), (20.0, 70.0), (25.0, 75.0),
        ])  # 5 segs, > DOOR_POLYLINE_SPUR_MAX_SEGMENTS
        segs = arc + short + long
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # Guard against constant drift so the test stays meaningful.
        self.assertEqual(DOOR_POLYLINE_SPUR_MAX_SEGMENTS, 4)
        # 11 arc + 5 long-branch segs survive; both short-branch segs removed.
        self.assertEqual(11 + 5, len(pruned))
        self.assertEqual({100, 101}, removed)

    def test_pruning_floor_protects_minimum(self) -> None:
        """A small Y-junction component where every walk fits in the spur
        cap. Pruning all marked walks would drop |component| below
        DOOR_POLYLINE_MIN_SEGMENTS, so the helper must back off and return
        the component unchanged."""
        # 2-segment main chain (0,0)→(10,0)→(10,10) plus two 1-segment
        # branches at (10,10), making it a degree-3 junction. 4 segs total.
        main = _chain(0, [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
        branch_a = _chain(100, [(10.0, 10.0), (15.0, 10.0)])
        branch_b = _chain(200, [(10.0, 10.0), (10.0, 15.0)])
        segs = main + branch_a + branch_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # All three leaf-walks (main 2 segs, each branch 1 seg) are within
        # the spur cap. Marking all 4 would drop the component to 0 segs,
        # well below DOOR_POLYLINE_MIN_SEGMENTS=4 → floor abort, no prune.
        self.assertEqual(DOOR_POLYLINE_MIN_SEGMENTS, 4)  # guard against constant drift
        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)


class TrimChainExtensionCapsTests(unittest.TestCase):
    """Tests for _trim_chain_extension_caps.

    Walks a 2-leaf simple chain (no junctions), finds the longest contiguous
    'arc-like' run (consecutive inter-segment angle deltas all <=
    DOOR_POLYLINE_CHAIN_DELTA_DEG), and trims everything outside that run.
    Components that aren't 2-leaf simple chains fall through unchanged.
    """

    def test_clean_arc_chain_unchanged(self) -> None:
        """An 11-segment quarter arc has only small inter-seg angle deltas
        (~8.2° each). No cap, nothing to trim."""
        segs = _arc(0, n_segs=11)
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_arc_with_perpendicular_cap_at_end_trimmed(self) -> None:
        """The polyline_393 / linework_226 shape: an 11-seg quarter arc
        followed by 2 axis-aligned cap segs (a horizontal then a vertical
        leg that doubles back). The first cap seg breaks the angle
        progression by ~90°; both cap segs get trimmed, the arc survives."""
        radius = 50.0
        arc = _arc(0, n_segs=11, radius=radius)
        # Arc's far endpoint approximately (0, 50). Attach a 2-seg cap that
        # doubles back: (0,50)→(3,50)→(3,44). Direction angles in the walk
        # (after walking through the arc to 90°) become ~0° and ~270° —
        # both 90° away from arc tangent, well above DELTA threshold.
        cap = _chain(100, [(0.0, 50.0), (3.0, 50.0), (3.0, 44.0)])
        segs = arc + cap
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        # 11 arc segs (path indices 0..10) preserved.
        self.assertEqual(11, len(kept))
        self.assertEqual(list(range(11)), sorted(kept))
        # Both cap path indices (100, 101) removed.
        self.assertEqual({100, 101}, removed)

    def test_caps_at_both_ends_trimmed(self) -> None:
        """A symmetric case: 11-seg arc with a 1-seg perpendicular cap at
        each end. Important: the cap direction must actually BREAK the arc
        tangent — a cap parallel to the tangent (going along it) just looks
        like a chain extension of the arc and stays.

        The arc here runs from (radius, 0) to (0, radius). Its tangent at
        the start points roughly +y (~90°), so a perpendicular cap there
        must point ±x. Its tangent at the end points roughly -x (~180°),
        so a perpendicular cap there must point ±y."""
        radius = 50.0
        arc = _arc(0, n_segs=11, radius=radius)
        # Cap A at arc start (radius, 0), going +x (perpendicular to +y tangent).
        cap_a = _chain(100, [(radius, 0.0), (radius + 5.0, 0.0)])
        # Cap B at arc end (0, radius), going +y (perpendicular to -x tangent).
        cap_b = _chain(200, [(0.0, radius), (0.0, radius + 5.0)])
        segs = cap_a + arc + cap_b
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        # Caps removed.
        self.assertEqual({100, 200}, removed)
        # 11 arc segs (path_indices 0..10) survive.
        kept_path_indices = sorted(segs[i][0].path_index for i in kept)
        self.assertEqual(list(range(11)), kept_path_indices)

    def test_component_with_junction_unchanged(self) -> None:
        """A component that still has a degree-3+ junction after spur
        pruning is NOT a simple chain, so chain-cap trimming bails out.
        (Spur pruning is the right tool for junctions; this is the wrong
        tool.)"""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Y-junction at arc end: two short branches.
        branch_a = _chain(100, [(0.0, 50.0), (-3.0, 53.0)])
        branch_b = _chain(200, [(0.0, 50.0), (3.0, 53.0)])
        segs = arc + branch_a + branch_b
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_pure_cycle_unchanged(self) -> None:
        """A pure cycle has no leaves to walk from. Skipped."""
        segs = _chain(
            0,
            [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0), (0.0, 0.0)],
        )
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_irregular_arc_under_threshold_not_over_trimmed(self) -> None:
        """An 8-seg quarter arc has ~11.25°/seg, well below the 45°
        threshold. Even a moderate irregularity (a single seg at 25° delta)
        stays below threshold and the arc survives intact."""
        # 8 segs around a quarter circle, slightly noisy
        segs = _arc(0, n_segs=8, radius=60.0)
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        # Threshold guard so this test stays meaningful if the constant moves.
        self.assertGreaterEqual(DOOR_POLYLINE_CHAIN_DELTA_DEG, 30.0)
        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_trim_would_violate_floor_unchanged(self) -> None:
        """A chain whose arc-like prefix is smaller than DOOR_POLYLINE_MIN_SEGMENTS
        cannot be trimmed without producing a degenerate component. Floor
        guard kicks in and nothing is trimmed."""
        # 3-seg arc + 4-seg cap. Trimming the cap would leave 3 segs,
        # below DOOR_POLYLINE_MIN_SEGMENTS=4 → floor abort.
        arc = _arc(0, n_segs=3, radius=20.0)
        # Cap: 4 short segs going perpendicular at the arc's end (~(0,20)).
        cap = _chain(100, [(0.0, 20.0), (3.0, 20.0), (3.0, 17.0), (6.0, 17.0), (6.0, 14.0)])
        segs = arc + cap
        component = list(range(len(segs)))

        kept, removed = _trim_chain_extension_caps(component, segs)

        self.assertEqual(DOOR_POLYLINE_MIN_SEGMENTS, 4)  # guard
        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)


class PruneArcCycleCapsTests(unittest.TestCase):
    """Tests for _prune_arc_cycle_caps.

    A 'closed-cycle cap' is a closed loop of segments attached at exactly
    one vertex (the articulation point / junction) to the rest of the
    component. The helper walks from each junction along each incident
    edge through degree-2 vertices and trims any walk that returns to
    the same junction within DOOR_POLYLINE_CYCLE_MAX_SEGMENTS steps.
    """

    def test_clean_arc_no_junctions_unchanged(self) -> None:
        """An arc with no degree-3+ vertices has nothing to prune."""
        segs = _arc(0, n_segs=11)
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_arc_with_4_seg_rect_cycle_removed(self) -> None:
        """11-seg arc + closed 4-seg rectangle attached at arc end.
        The junction is at the arc's natural endpoint; the rectangle
        is a closed cycle. All 4 cycle segs trimmed; arc preserved.

        Coords are spaced by >=4 px so each vertex rounds to a distinct
        snap_key (DOOR_POLYLINE_ENDPOINT_TOL=2.0, so vertices need >=2
        px apart in each coord to avoid bucket collisions)."""
        arc = _arc(0, n_segs=11, radius=50.0)
        rect = _chain(
            100,
            [(0.0, 50.0), (4.0, 50.0), (4.0, 54.0), (0.0, 54.0), (0.0, 50.0)],
        )
        segs = arc + rect
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        kept_path_indices = sorted(segs[i][0].path_index for i in kept)
        self.assertEqual(list(range(11)), kept_path_indices)
        self.assertEqual({100, 101, 102, 103}, removed)

    def test_arc_with_7_seg_cycle_removed(self) -> None:
        """The polyline_856 shape: 11-seg arc + 7-seg closed cap loop
        attached at the arc's natural endpoint. All 7 cycle segs trimmed."""
        arc = _arc(0, n_segs=11, radius=50.0)
        cycle = _chain(
            100,
            [
                (0.0, 50.0), (4.0, 50.0), (8.0, 54.0), (8.0, 58.0),
                (4.0, 62.0), (0.0, 58.0), (0.0, 54.0), (0.0, 50.0),
            ],
        )
        segs = arc + cycle
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        kept_path_indices = sorted(segs[i][0].path_index for i in kept)
        self.assertEqual(list(range(11)), kept_path_indices)
        self.assertEqual(7, len(removed))

    def test_oversized_cycle_kept(self) -> None:
        """A cycle of more than DOOR_POLYLINE_CYCLE_MAX_SEGMENTS segments
        exceeds the cap cutoff and is left alone — assumed too large to
        be a typical door-stop decoration."""
        arc = _arc(0, n_segs=11, radius=50.0)
        cycle = _chain(
            100,
            [
                (0.0, 50.0), (4.0, 50.0), (8.0, 52.0), (12.0, 56.0),
                (12.0, 60.0), (8.0, 64.0), (4.0, 64.0), (0.0, 60.0),
                (0.0, 56.0), (0.0, 50.0),
            ],
        )
        segs = arc + cycle
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        # Guard: oversized cycle must be strictly larger than the threshold.
        self.assertEqual(DOOR_POLYLINE_CYCLE_MAX_SEGMENTS, 8)
        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_pure_cycle_unchanged(self) -> None:
        """A pure cycle (no junction) has nothing to attach to. The helper
        only fires on cycles ATTACHED at an articulation point."""
        segs = _chain(
            0,
            [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0), (0.0, 0.0)],
        )
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_spur_at_junction_not_treated_as_cycle(self) -> None:
        """A Y-junction with leaf-ending branches is a spur configuration,
        not a cycle. Cycle pruning must walk INTO each branch, detect that
        it ends at a leaf (degree 1) rather than looping back, and bail."""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Two 1-seg branches at (0, 50), each ending in a leaf.
        branch_a = _chain(100, [(0.0, 50.0), (-3.0, 53.0)])
        branch_b = _chain(200, [(0.0, 50.0), (3.0, 53.0)])
        segs = arc + branch_a + branch_b
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)

    def test_floor_guard_prevents_excess_pruning(self) -> None:
        """When pruning the cycle would drop the component below
        DOOR_POLYLINE_MIN_SEGMENTS, the helper aborts and returns the
        original component."""
        # 3-seg "arc" chain meeting a 4-seg cycle at one vertex. Pruning
        # the cycle would leave only 3 segs, below the floor of 4.
        arc = _chain(0, [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (10.0, 20.0)])
        rect = _chain(
            100,
            [(10.0, 20.0), (14.0, 20.0), (14.0, 24.0), (10.0, 24.0), (10.0, 20.0)],
        )
        segs = arc + rect
        component = list(range(len(segs)))

        kept, removed = _prune_arc_cycle_caps(component, segs)

        self.assertEqual(DOOR_POLYLINE_MIN_SEGMENTS, 4)  # guard
        self.assertEqual(component, kept)
        self.assertEqual(set(), removed)


if __name__ == "__main__":
    unittest.main()
