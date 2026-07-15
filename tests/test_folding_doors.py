import math
import unittest

from detection import detect_doors
from detection.doors.folding import _detect_folding_doors
from detection.doors.sliding import _collect_slide_panels
from tests.test_sliding_doors import line, prim, qu_panel, rect_corners, white_ring


def leaf(start_idx, p, q, thickness, white=True):
    """One folding leaf running p -> q, drawn in the Vectorworks joinery
    signature: white fill ring + stroked qu outline (5 prims). Hinged leaves
    share ring vertices, so their rings BFS-merge and are rejected by
    _white_ring_rects — the folding detector recovers the white signature by
    absorbing the ring edges onto the stroked-qu panels."""
    ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
    length = math.dist(p, q)
    center = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    paths = list(white_ring(start_idx, center, length, thickness, ang)) if white else []
    paths.append(qu_panel(start_idx + 4, center, length, thickness, ang))
    return paths


def fold_chain(start_idx, origin, length, thickness, angles_deg, white=True):
    """A concertina run of hinged leaves, leaf k at angles_deg[k]."""
    paths = []
    p = origin
    idx = start_idx
    for ang in angles_deg:
        theta = math.radians(ang)
        q = (p[0] + length * math.cos(theta), p[1] + length * math.sin(theta))
        paths.extend(leaf(idx, p, q, thickness, white=white))
        idx += 5
        p = q
    return paths


def parked_stack(start_idx, hinge, length, thickness, angle_a, angle_b):
    """Two leaves fanned open from one shared hinge (a parked bifold V)."""
    paths = []
    idx = start_idx
    for ang in (angle_a, angle_b):
        theta = math.radians(ang)
        tip = (hinge[0] - length * math.cos(theta), hinge[1] - length * math.sin(theta))
        paths.extend(leaf(idx, tip, hinge, thickness))
        idx += 5
    return paths


def folding_of(candidates):
    return [
        c for c in candidates
        if c.entity_type == "door" and c.evidence.get("assembly_type") == "folding"
    ]


def detect(paths):
    candidates, _ = _detect_folding_doors(paths, [], None, 0)
    return candidates


class FoldChainTests(unittest.TestCase):
    def test_trifold_chain_detected(self):
        # GD2 shape: three equal leaves hinged at deltas of 12 and 20 degrees.
        paths = fold_chain(0, (100.0, 100.0), 74.0, 5.0, [0.0, 12.0, -8.0])
        folds = folding_of(detect(paths))
        self.assertEqual(len(folds), 1)
        self.assertEqual(folds[0].evidence["fold_style"], "chain")
        self.assertEqual(folds[0].evidence["leaf_count"], 3)
        self.assertAlmostEqual(folds[0].confidence, 0.65, places=2)

    def test_rotated_chain_detected(self):
        for base in (37.0, 90.0):
            with self.subTest(base=base):
                paths = fold_chain(
                    0, (100.0, 100.0), 74.0, 5.0,
                    [base, base + 12.0, base - 8.0],
                )
                self.assertEqual(len(folding_of(detect(paths))), 1)

    def test_hinged_rings_recovered_as_white(self):
        # The shared hinge vertex makes _white_ring_rects reject the fill
        # rings (degree-4 vertex); panels must still come out white with the
        # ring indices absorbed alongside the qu outlines.
        paths = fold_chain(0, (100.0, 100.0), 74.0, 5.0, [0.0, 12.0, -8.0])
        folds = folding_of(detect(paths))
        self.assertEqual(folds[0].evidence["component_path_indices"], list(range(15)))
        self.assertEqual(
            folds[0].evidence["leaf_sources"], ["qu+white_ring"] * 3,
        )

    def test_two_leaf_chain_not_emitted(self):
        # A lone parked V (2 leaves) has no partner stack: too weak to emit.
        paths = parked_stack(0, (300.0, 500.0), 100.0, 7.5, 80.0, 100.0)
        self.assertEqual(folding_of(detect(paths)), [])

    def test_stroked_only_chain_rejected(self):
        # Without the white fill signature the panels are generic joinery.
        paths = fold_chain(0, (100.0, 100.0), 74.0, 5.0, [0.0, 12.0, -8.0], white=False)
        self.assertEqual(folding_of(detect(paths)), [])

    def test_parallel_panels_not_folding(self):
        # A sliding pair (parallel, overlapping) is not a fold: the fold-angle
        # window starts above the sliding parallelism gate.
        paths = [
            qu_panel(0, (300.0, 300.0), 90.0, 6.0, 0.0, fill=(1.0, 1.0, 1.0)),
            qu_panel(1, (345.0, 300.0), 90.0, 6.0, 0.0, fill=(1.0, 1.0, 1.0)),
        ]
        self.assertEqual(folding_of(detect(paths)), [])

    def test_perpendicular_corner_joinery_rejected(self):
        # Two equal thin rects meeting at an L-corner (wardrobe/counter run).
        paths = leaf(0, (100.0, 100.0), (174.0, 100.0), 5.0)
        paths += leaf(5, (174.0, 100.0), (174.0, 174.0), 5.0)
        self.assertEqual(folding_of(detect(paths)), [])

    def test_unequal_leaves_rejected(self):
        paths = leaf(0, (100.0, 100.0), (174.0, 100.0), 5.0)
        end = (
            174.0 + 40.0 * math.cos(math.radians(15.0)),
            100.0 + 40.0 * math.sin(math.radians(15.0)),
        )
        paths += leaf(5, (174.0, 100.0), end, 5.0)
        paths += fold_chain(10, (400.0, 400.0), 74.0, 5.0, [0.0])
        self.assertEqual(folding_of(detect(paths)), [])


class ParkedStackPairTests(unittest.TestCase):
    def _stacks(self, gap_center=358.0, base=(300.0, 500.0)):
        left = parked_stack(0, base, 100.0, 7.5, 80.0, 100.0)
        right = parked_stack(
            10, (base[0] + gap_center, base[1]), 100.0, 7.5, 100.0, 80.0,
        )
        return left + right

    def test_stack_pair_detected(self):
        # Outer span between the parked stacks ≈ 4 leaf lengths (span law).
        folds = folding_of(detect(self._stacks()))
        self.assertEqual(len(folds), 1)
        self.assertEqual(folds[0].evidence["fold_style"], "stack_pair")
        self.assertEqual(folds[0].evidence["leaf_count"], 4)

    def test_span_law_mismatch_rejected(self):
        # Stacks too close: unfolded leaves would overshoot the opening.
        self.assertEqual(folding_of(detect(self._stacks(gap_center=150.0))), [])
        # And too far: leaves could never cover the span.
        self.assertEqual(folding_of(detect(self._stacks(gap_center=560.0))), [])

    def test_mirror_violation_rejected(self):
        # Both stacks leaning the SAME way off the wall plane is not a door
        # parked at two jambs (mean angles must mirror about the opening).
        left = parked_stack(0, (300.0, 500.0), 100.0, 7.5, 55.0, 75.0)
        right = parked_stack(10, (658.0, 500.0), 100.0, 7.5, 55.0, 75.0)
        self.assertEqual(folding_of(detect(left + right)), [])


class EndToEndTests(unittest.TestCase):
    def test_detect_doors_dedupes_leaf_fallbacks(self):
        paths = fold_chain(0, (100.0, 100.0), 74.0, 5.0, [0.0, 12.0, -8.0])
        doors = [c for c in detect_doors(paths, []) if c.entity_type == "door"]
        self.assertEqual(len(doors), 1)
        self.assertEqual(doors[0].evidence["assembly_type"], "folding")


if __name__ == "__main__":
    unittest.main()
