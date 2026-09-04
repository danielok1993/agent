"""Cross-validation against the wall network (detection/postprocess.py).

The door penalty deltas are pinned by the tuning-guide §9 regression
baselines — these tests guard the exact values.
"""
import unittest

from models import Candidate
from detection import WallNetwork, WallSegment
from detection.walls import WallFace
from detection.postprocess import (
    CROSS_GATES_UNSCALED,
    CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY,
    CROSS_NO_WALL_PENALTY,
    CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY,
    CROSS_WINDOW_ON_WALL_BOOST,
    _cross_validate,
    _wall_runs_through,
)


def seg(p1, p2, thickness=8.0, stroked=True):
    return WallSegment(
        p1=p1, p2=p2, thickness_px=thickness, source="face_pair",
        layer=None, layer_hint=False, face_path_indices=[], stroked=stroked,
    )


def face(p1, p2):
    return WallFace(
        p1=p1, p2=p2, stroked=True, stroke_width=1.5, wall_fill=False,
        layer_hint=False, indices=frozenset(),
    )


def h_wall_with_gap(y=104.0, gap=(200.0, 260.0), thickness=16.0):
    """Horizontal wall run interrupted at the gap (segments AND faces break),
    plus filler segments so the network passes the min-segment gate."""
    t2 = thickness / 2
    return WallNetwork(
        segments=[
            seg((100.0, y), (gap[0], y), thickness),
            seg((gap[1], y), (400.0, y), thickness),
            seg((700.0, 700.0), (800.0, 700.0), thickness),
            seg((700.0, 750.0), (800.0, 750.0), thickness),
        ],
        faces=[
            face((100.0, y - t2), (gap[0], y - t2)), face((100.0, y + t2), (gap[0], y + t2)),
            face((gap[1], y - t2), (400.0, y - t2)), face((gap[1], y + t2), (400.0, y + t2)),
        ],
    )


def continuous_h_wall(y=104.0, thickness=8.0):
    t2 = thickness / 2
    return WallNetwork(
        segments=[
            seg((100.0, y), (400.0, y), thickness),
            seg((700.0, 700.0), (800.0, 700.0), thickness),
            seg((700.0, 750.0), (800.0, 750.0), thickness),
            seg((700.0, 800.0), (800.0, 800.0), thickness),
        ],
        faces=[
            face((100.0, y - t2), (400.0, y - t2)),
            face((100.0, y + t2), (400.0, y + t2)),
        ],
    )


def door(bbox=(150.0, 96.0, 200.0, 150.0), conf=0.65, **evidence):
    return Candidate(
        candidate_id="door_0000", entity_type="door",
        bbox=bbox, confidence=conf, evidence=evidence,
    )


def window(bbox, conf=0.62, **evidence):
    return Candidate(
        candidate_id="window_0000", entity_type="window",
        bbox=bbox, confidence=conf, evidence=evidence,
    )


class TestDoorPenalties(unittest.TestCase):
    """Exact penalty deltas — pinned by the §9 door regression baselines."""

    def test_door_in_wall_untouched(self):
        network = continuous_h_wall()
        out = _cross_validate([door(method="door_assembly")], network)
        self.assertEqual(out[0].confidence, 0.65)
        self.assertIn(out[0].evidence["wall_context"], ("in_wall", "on_wall_centerline"))

    def test_plain_door_no_wall_default_penalty(self):
        network = continuous_h_wall()
        d = door(bbox=(900.0, 96.0, 950.0, 150.0), conf=0.65)
        out = _cross_validate([d], network)
        self.assertEqual(out[0].confidence, round(0.65 - CROSS_NO_WALL_PENALTY, 3))
        self.assertEqual(out[0].evidence["wall_context"], "no_wall")

    def test_assembly_door_no_wall_reduced_penalty(self):
        network = continuous_h_wall()
        d = door(bbox=(900.0, 96.0, 950.0, 150.0), conf=0.65, method="door_assembly")
        out = _cross_validate([d], network)
        self.assertEqual(
            out[0].confidence, round(0.65 - CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY, 3)
        )

    def test_single_line_leaf_no_wall_strong_penalty(self):
        network = continuous_h_wall()
        d = door(
            bbox=(900.0, 96.0, 950.0, 150.0), conf=0.67,
            method="door_assembly", assembly_type="single_line_leaf",
            nearby_label=None,
        )
        out = _cross_validate([d], network)
        self.assertEqual(
            out[0].confidence, round(0.67 - CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY, 3)
        )

    def test_single_line_leaf_near_fill_only_wall_still_penalized(self):
        # Vectorworks fixtures (tubs, counters) are pure fill-outline geometry
        # standing against fill-outline walls; the weakest door tier needs
        # stroked wall corroboration (the 5-1133 bath-fixture regression).
        network = WallNetwork(segments=[
            seg((100.0, 104.0), (400.0, 104.0), 16.0, stroked=False),
            seg((700.0, 700.0), (800.0, 700.0), stroked=False),
            seg((700.0, 750.0), (800.0, 750.0), stroked=False),
            seg((700.0, 800.0), (800.0, 800.0), stroked=False),
        ])
        d = door(
            conf=0.67, method="door_assembly",
            assembly_type="single_line_leaf", nearby_label=None,
        )
        out = _cross_validate([d], network)
        self.assertEqual(
            out[0].confidence, round(0.67 - CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY, 3)
        )
        self.assertEqual(out[0].evidence["wall_context"], "no_wall")
        self.assertEqual(out[0].evidence["wall_context_note"], "filled_wall_only")

    def test_single_line_leaf_near_stroked_wall_not_penalized(self):
        network = continuous_h_wall()
        d = door(
            conf=0.67, method="door_assembly",
            assembly_type="single_line_leaf", nearby_label=None,
        )
        out = _cross_validate([d], network)
        self.assertEqual(out[0].confidence, 0.67)

    def test_single_line_leaf_26px_from_centerline_is_in_wall(self):
        # CROSS_WALL_EXPAND_PX is 24px — 203mm at 1:50 (W-gate census
        # 2026-09-04, 20 -> 24). "Need" here is the distance from the door
        # bbox to the nearest DETECTED wall corridor — a detection artefact
        # (the network may end short of the jamb), not a built dimension.
        # The tier this gate decides is single_line_leaf (the only one the
        # no_wall penalty pushes under the offline floor): s01's needs 12px
        # = 187mm at its true 1:92.2 (0.9x of the old 169mm), s18's 7.5px at
        # f=0.5 = 127mm (lost at 0.67x = 6.7px), s10 47mm; s17 gains a
        # phantom door only at 40px. 24 sits 1.08x over s01 and 1.67x under
        # s17's break. The 8px wall's corridor reaches 4 + 24 = 28px from its
        # centerline: a bbox 26px off is in_wall (no_wall at 20).
        network = continuous_h_wall()
        d = door(
            bbox=(150.0, 130.0, 200.0, 184.0), conf=0.67,
            method="door_assembly", assembly_type="single_line_leaf",
            nearby_label=None,
        )
        out = _cross_validate([d], network)
        self.assertEqual(out[0].confidence, 0.67)
        self.assertNotEqual(out[0].evidence["wall_context"], "no_wall")

    def test_single_line_leaf_30px_from_centerline_is_no_wall(self):
        network = continuous_h_wall()
        d = door(
            bbox=(150.0, 134.0, 200.0, 188.0), conf=0.67,
            method="door_assembly", assembly_type="single_line_leaf",
            nearby_label=None,
        )
        out = _cross_validate([d], network)
        self.assertEqual(out[0].evidence["wall_context"], "no_wall")

    def test_opening_line_on_centerline_context(self):
        network = h_wall_with_gap()
        d = door(
            bbox=(195.0, 96.0, 265.0, 170.0), conf=0.67,
            method="door_assembly",
            opening_line=[[200.0, 104.0], [260.0, 104.0]],
        )
        out = _cross_validate([d], network)
        self.assertEqual(out[0].confidence, 0.67)
        self.assertEqual(out[0].evidence["wall_context"], "on_wall_centerline")


class TestWindowValidation(unittest.TestCase):
    def test_window_spanning_wall_thickness_boosted(self):
        # Window in the wall gap; bbox short side matches the 16px wall
        # thickness of the interrupted run.
        network = h_wall_with_gap(thickness=16.0)
        w = window((200.0, 96.0, 260.0, 112.0))
        out = _cross_validate([w], network)
        self.assertEqual(out[0].confidence, round(0.62 + CROSS_WINDOW_ON_WALL_BOOST, 3))
        self.assertEqual(out[0].evidence["wall_context"], "spans_wall_thickness")

    def test_window_no_wall_penalized(self):
        network = continuous_h_wall()
        w = window((900.0, 96.0, 960.0, 112.0))
        out = _cross_validate([w], network)
        self.assertEqual(out[0].confidence, round(0.62 - CROSS_NO_WALL_PENALTY, 3))

    def test_window_on_continuous_wall_not_boosted(self):
        # A centerline running unbroken through the candidate span is wall
        # linework context, not an opening — in_wall but no boost.
        network = continuous_h_wall(thickness=16.0)
        w = window((200.0, 96.0, 260.0, 112.0))
        out = _cross_validate([w], network)
        self.assertEqual(out[0].confidence, 0.62)
        self.assertEqual(out[0].evidence["wall_context"], "in_wall")


class TestWallRunsThrough(unittest.TestCase):
    def test_wall_runs_through_helper(self):
        network = continuous_h_wall()
        self.assertTrue(_wall_runs_through(
            network, (200.0, 98.0, 260.0, 110.0), gates=CROSS_GATES_UNSCALED))
        gapped = h_wall_with_gap()
        self.assertFalse(_wall_runs_through(
            gapped, (200.0, 96.0, 260.0, 112.0), gates=CROSS_GATES_UNSCALED))


class TestEmptyNetwork(unittest.TestCase):
    def test_cross_validate_noop(self):
        d = door(conf=0.65, method="door_assembly")
        for network in (None, WallNetwork(segments=[])):
            out = _cross_validate([d], network)
            self.assertEqual(out[0].confidence, 0.65)
            self.assertNotIn("wall_context", out[0].evidence)

if __name__ == "__main__":
    unittest.main()
