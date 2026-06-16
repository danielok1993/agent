import math
import unittest

from heuristics import (
    DOOR_POLYLINE_MIN_SEGMENTS,
    DOOR_POLYLINE_SPUR_MAX_SEGMENTS,
    _prune_arc_spurs,
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


if __name__ == "__main__":
    unittest.main()
