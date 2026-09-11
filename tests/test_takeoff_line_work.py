"""line_work_dict — the page's line work as takeoff.json carries it."""
import unittest

from detection.walls import WallFace, WallNetwork, WallSegment
from takeoff.document import (
    LINE_WORK_MAX_LINES,
    LINE_WORK_MAX_WALLS,
    line_work_dict,
)


def _face(p1, p2, indices):
    return WallFace(p1=p1, p2=p2, stroked=True, stroke_width=1.0,
                    wall_fill=False, layer_hint=False,
                    indices=frozenset(indices))


def _segment(p1, p2, thickness_px, face_path_indices):
    return WallSegment(p1=p1, p2=p2, thickness_px=thickness_px,
                       source="face_pair", layer=None, layer_hint=False,
                       face_path_indices=list(face_path_indices))


class TestLineWork(unittest.TestCase):
    def test_no_network_is_two_empty_lists(self):
        # disable_rooms skips wall detection entirely. A missing key is worse
        # for a consumer than an empty one.
        self.assertEqual(line_work_dict(None), {"walls": [], "lines": []})

    def test_a_centreline_carries_its_measured_thickness(self):
        net = WallNetwork(segments=[_segment((0, 0), (100, 0), 12.5, [1, 2])],
                          faces=[])
        self.assertEqual(line_work_dict(net)["walls"], [
            {"centreline": [[0, 0], [100, 0]], "thickness_px": 12.5},
        ])

    def test_a_paired_face_is_a_wall_face_and_carries_the_thickness(self):
        net = WallNetwork(
            segments=[_segment((0, 6), (100, 6), 12.5, [1, 2])],
            faces=[_face((0, 0), (100, 0), [1])],
        )
        self.assertEqual(line_work_dict(net)["lines"], [
            {"a": [0, 0], "b": [100, 0], "kind": "wall_face",
             "thickness_px": 12.5},
        ])

    def test_an_unpaired_face_is_a_plain_line_with_no_thickness(self):
        # The case the feature exists for: ink the detector could not pair, so
        # it never became a wall — and must still be snappable.
        net = WallNetwork(
            segments=[_segment((0, 6), (100, 6), 12.5, [1, 2])],
            faces=[_face((0, 0), (100, 0), [1]), _face((0, 400), (60, 400), [9])],
        )
        self.assertEqual(line_work_dict(net)["lines"][1], {
            "a": [0, 400], "b": [60, 400], "kind": "line",
            "thickness_px": None,
        })

    def test_coordinates_are_rounded_to_hundredths_of_a_pixel(self):
        # Detection carries full float noise; the block is stored inline in
        # a size-capped Firestore document, so endpoints round to 2dp.
        # thickness_px is untouched — it is already rounded upstream.
        net = WallNetwork(
            segments=[_segment((1034.968606397665, 1133.4826215169392),
                               (1035.5031429632681, 702.9069796635658),
                               12.5, [1])],
            faces=[_face((12.344999, 6.005001), (0.0, 400.9999), [1])],
        )
        d = line_work_dict(net)
        self.assertEqual(d["walls"], [
            {"centreline": [[1034.97, 1133.48], [1035.5, 702.91]],
             "thickness_px": 12.5},
        ])
        self.assertEqual(d["lines"], [
            {"a": [12.34, 6.01], "b": [0.0, 401.0], "kind": "wall_face",
             "thickness_px": 12.5},
        ])

    def test_every_face_survives_whether_or_not_it_was_paired(self):
        net = WallNetwork(
            segments=[_segment((0, 6), (100, 6), 12.5, [1])],
            faces=[_face((0, 0), (100, 0), [1]),
                   _face((0, 400), (60, 400), [9]),
                   _face((0, 800), (60, 800), [11])],
        )
        self.assertEqual(len(line_work_dict(net)["lines"]), 3)

    def test_lines_over_the_cap_keep_the_longest_and_respect_it(self):
        # One face per length from 1..total, each unique so the kept/dropped
        # boundary is unambiguous. total is enough over LINE_WORK_MAX_LINES
        # that truncation must happen.
        total = LINE_WORK_MAX_LINES + 5
        faces = [_face((0, 0), (float(length), 0), [length])
                 for length in range(1, total + 1)]
        net = WallNetwork(segments=[], faces=faces)

        result = line_work_dict(net)["lines"]

        self.assertEqual(len(result), LINE_WORK_MAX_LINES)
        lengths = [line["b"][0] - line["a"][0] for line in result]
        # Emitted longest-first.
        self.assertEqual(lengths, sorted(lengths, reverse=True))
        # The kept set is exactly the longest LINE_WORK_MAX_LINES: the
        # shortest 5 (lengths 1..5) are the ones gone.
        self.assertEqual(set(lengths), set(range(6, total + 1)))

    def test_lines_truncation_is_logged_at_info(self):
        total = LINE_WORK_MAX_LINES + 1
        faces = [_face((0, 0), (float(length), 0), [length])
                 for length in range(1, total + 1)]
        net = WallNetwork(segments=[], faces=faces)

        with self.assertLogs("takeoff.document", level="INFO") as log:
            line_work_dict(net)
        self.assertTrue(any("lines" in m for m in log.output))

    def test_lines_under_the_cap_are_not_truncated_or_logged(self):
        faces = [_face((0, 0), (float(length), 0), [length])
                 for length in range(1, 4)]
        net = WallNetwork(segments=[], faces=faces)

        with self.assertNoLogs("takeoff.document", level="INFO"):
            result = line_work_dict(net)
        self.assertEqual(len(result["lines"]), 3)

    def test_walls_over_the_cap_keep_the_longest_and_respect_it(self):
        total = LINE_WORK_MAX_WALLS + 5
        segments = [_segment((0, 0), (float(length), 0), 12.5, [length])
                    for length in range(1, total + 1)]
        net = WallNetwork(segments=segments, faces=[])

        result = line_work_dict(net)["walls"]

        self.assertEqual(len(result), LINE_WORK_MAX_WALLS)
        lengths = [w["centreline"][1][0] - w["centreline"][0][0] for w in result]
        self.assertEqual(lengths, sorted(lengths, reverse=True))
        self.assertEqual(set(lengths), set(range(6, total + 1)))

    def test_walls_truncation_is_logged_at_info(self):
        total = LINE_WORK_MAX_WALLS + 1
        segments = [_segment((0, 0), (float(length), 0), 12.5, [length])
                    for length in range(1, total + 1)]
        net = WallNetwork(segments=segments, faces=[])

        with self.assertLogs("takeoff.document", level="INFO") as log:
            line_work_dict(net)
        self.assertTrue(any("walls" in m for m in log.output))
