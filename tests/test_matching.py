"""Ground truth is matched to output geometrically.

Entity ids (door_0015) are ordinal and shift whenever detection changes, so
matching is by type + IoU. 0.5 is loose enough to survive the few-pixel drift a
tuning change causes and tight enough that two adjacent doors never swap.
"""
import unittest

from regression.ground_truth import TruthItem
from regression.matching import MIN_IOU, iou, match_entities


def entity(kind, bbox, eid="e0"):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": 0.9, "attributes": {}}


class IouTests(unittest.TestCase):
    def test_identical_boxes_score_one(self):
        self.assertAlmostEqual(iou((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)

    def test_disjoint_boxes_score_zero(self):
        self.assertEqual(iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)

    def test_edge_touching_boxes_score_zero(self):
        self.assertEqual(iou((0, 0, 10, 10), (10, 0, 20, 10)), 0.0)

    def test_half_overlap_scores_one_third(self):
        self.assertAlmostEqual(iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)

    def test_a_zero_area_box_scores_zero_via_the_empty_intersection_check(self):
        # A point box's intersection with anything is empty, so this exits
        # through the `ix1 <= ix0 or iy1 <= iy0` early return -- it does not
        # exercise a union-is-zero division guard (there is no reachable
        # input past that early return where union can be zero).
        self.assertEqual(iou((5, 5, 5, 5), (0, 0, 10, 10)), 0.0)


class MatchTests(unittest.TestCase):
    def test_a_drifted_box_still_matches(self):
        truth = [TruthItem("door", (100, 100, 140, 140))]
        actual = [entity("door", (102, 101, 142, 141))]
        result = match_entities(truth, actual)
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(result.unmatched_truth, [])

    def test_a_different_type_never_matches(self):
        truth = [TruthItem("door", (100, 100, 140, 140))]
        result = match_entities(truth, [entity("window", (100, 100, 140, 140))])
        self.assertEqual(len(result.unmatched_truth), 1)
        self.assertEqual(len(result.unmatched_actual), 1)

    def test_a_vanished_detection_is_unmatched_truth(self):
        result = match_entities([TruthItem("door", (0, 0, 10, 10))], [])
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_a_new_detection_is_unmatched_actual(self):
        result = match_entities([], [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(result.unmatched_actual), 1)

    def test_below_threshold_overlap_does_not_match(self):
        truth = [TruthItem("door", (0, 0, 10, 10))]
        result = match_entities(truth, [entity("door", (7, 0, 17, 10))])
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_each_entity_is_claimed_once(self):
        truth = [TruthItem("door", (0, 0, 10, 10)), TruthItem("door", (1, 1, 11, 11))]
        result = match_entities(truth, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(len(result.matched), 1)
        self.assertEqual(len(result.unmatched_truth), 1)

    def test_the_best_overlap_wins_not_the_first(self):
        truth = [TruthItem("door", (0, 0, 10, 10))]
        actual = [entity("door", (2, 0, 12, 10), "far"), entity("door", (1, 0, 11, 10), "near")]
        result = match_entities(truth, actual)
        self.assertEqual(result.matched[0][1]["entity_id"], "near")

    def test_the_default_threshold_is_one_half(self):
        self.assertEqual(MIN_IOU, 0.5)
