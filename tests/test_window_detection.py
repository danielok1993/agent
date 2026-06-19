"""Window detection tests.

Ground truth was established interactively on floor-plans.pdf: exactly four
windows, each drawn as a thin glazing rectangle — a tight cluster of >=3
parallel, equal-length "glazing" lines (glass-pane edges + centerline) closed
at both ends by short perpendicular "cap" lines. See
docs/window-detection-tuning-guide.md for the topology reference.

These tests pin:
  * the two orientations (horizontal W1-style, vertical W4-style) are detected,
  * the documented rejection cases stay rejected (n<3 cluster, no caps, cluster
    too thick), and
  * door entities suppress overlapping window candidates
    (_resolve_door_window_conflicts), and
  * the real floor-plans.pdf yields exactly the four ground-truth windows.
"""
import math
import os
import unittest

from detection import detect_windows
from detection.postprocess import _resolve_door_window_conflicts
from models import BBox, Candidate, PathPrimitive


def path(
    idx: int,
    points: list[tuple[float, float]],
    *,
    item_type: str = "l",
    layer: str | None = "",
    stroke_width: float = 1.0,
) -> PathPrimitive:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx,
        item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None,
        fill=None,
        stroke_width=stroke_width,
        dashes="",
        layer=layer,
        points=points,
    )


def hline(idx: int, x0: float, x1: float, y: float, **kw) -> PathPrimitive:
    return path(idx, [(x0, y), (x1, y)], **kw)


def vline(idx: int, y0: float, y1: float, x: float, **kw) -> PathPrimitive:
    return path(idx, [(x, y0), (x, y1)], **kw)


def horizontal_window(base: int, x0: float, x1: float, ymid: float, depth: float = 22.0):
    """A W1-style horizontal window: 3 tight horizontal glazing lines centered
    in a `depth`-tall frame, closed by two vertical caps at the span ends."""
    top, bot = ymid - depth / 2, ymid + depth / 2
    return [
        hline(base + 0, x0, x1, ymid - 1.0),   # glazing edge
        hline(base + 1, x0, x1, ymid),         # centerline (user's "middle line")
        hline(base + 2, x0, x1, ymid + 1.0),   # glazing edge
        vline(base + 3, top, bot, x0),         # cap
        vline(base + 4, top, bot, x1),         # cap
    ]


def vertical_window(base: int, y0: float, y1: float, xmid: float, depth: float = 6.5):
    """A W4-style vertical window: 3 tight vertical glazing lines closed by two
    horizontal caps."""
    left, right = xmid - depth / 2, xmid + depth / 2
    return [
        vline(base + 0, y0, y1, xmid - 3.0),
        vline(base + 1, y0, y1, xmid),
        vline(base + 2, y0, y1, xmid + 3.0),
        hline(base + 3, left, right, y0),
        hline(base + 4, left, right, y1),
    ]


def _covers(b: BBox, cx: float, cy: float, pad: float = 6.0) -> bool:
    return b[0] - pad <= cx <= b[2] + pad and b[1] - pad <= cy <= b[3] + pad


class TestWindowTopology(unittest.TestCase):
    def test_horizontal_window_detected(self):
        paths = horizontal_window(100, 100.0, 176.0, 387.0)
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}")
        self.assertTrue(_covers(wins[0].bbox, 138.0, 387.0))

    def test_vertical_window_detected(self):
        paths = vertical_window(200, 400.0, 477.0, 303.0)
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}")
        self.assertTrue(_covers(wins[0].bbox, 303.0, 438.0))

    def test_two_line_cluster_without_centerline_rejected(self):
        """The fixtures/doors that survived the old detector were n=2 clusters.
        A pane with only two lines (no centerline) must not become a window."""
        top, bot = 376.0, 398.0
        paths = [
            hline(300, 100.0, 176.0, 386.0),
            hline(301, 100.0, 176.0, 388.0),
            vline(302, top, bot, 100.0),
            vline(303, top, bot, 176.0),
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_glazing_without_caps_rejected(self):
        """Three parallel lines with no perpendicular end-caps (e.g. a run of
        dimension lines) is not a closed rectangle → not a window."""
        paths = [
            hline(400, 100.0, 176.0, 386.0),
            hline(401, 100.0, 176.0, 387.0),
            hline(402, 100.0, 176.0, 388.0),
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_loose_cluster_rejected(self):
        """Three parallel lines spaced far apart (e.g. stair treads) exceed the
        glazing-pane thickness and must not group into one window."""
        paths = [
            hline(500, 100.0, 176.0, 380.0),
            hline(501, 100.0, 176.0, 390.0),
            hline(502, 100.0, 176.0, 400.0),
            vline(503, 375.0, 405.0, 100.0),
            vline(504, 375.0, 405.0, 176.0),
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_two_windows_independent(self):
        paths = horizontal_window(600, 100.0, 176.0, 387.0) + vertical_window(700, 400.0, 477.0, 303.0)
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 2)


class TestDoorWindowExclusion(unittest.TestCase):
    def _win(self, bbox: BBox) -> Candidate:
        return Candidate("window_0000", "window", bbox, 0.7, {})

    def _door(self, bbox: BBox) -> Candidate:
        return Candidate("door_0000", "door", bbox, 0.8, {})

    def test_window_overlapping_door_dropped(self):
        win = self._win((1022.0, 1139.0, 1048.0, 1189.0))   # FP #18 door-leaf area
        door = self._door((1036.0, 1139.0, 1090.0, 1189.0))  # door_0005
        out = _resolve_door_window_conflicts([win, door])
        self.assertNotIn(win, out)
        self.assertIn(door, out)

    def test_window_clear_of_doors_kept(self):
        win = self._win((903.0, 1374.0, 980.0, 1400.0))      # real window W1
        door = self._door((458.0, 1337.0, 512.0, 1392.0))    # far-away door
        out = _resolve_door_window_conflicts([win, door])
        self.assertIn(win, out)


class TestFloorPlansRegression(unittest.TestCase):
    """End-to-end regression: floor-plans.pdf must yield exactly the four
    ground-truth windows and none of the documented false positives."""

    GT_WINDOWS = [(958, 850), (895, 903), (1103, 1387), (941, 1387)]  # W4, W3, W2, W1 centers
    FP_CENTERS = [(980, 783), (1053, 812), (980, 936), (1004, 1118)]  # toilet, sink, toilet, door-leaf

    def setUp(self):
        self.pdf = os.path.join(os.path.dirname(__file__), os.pardir, "floor-plans.pdf")
        if not os.path.exists(self.pdf):
            self.skipTest("floor-plans.pdf not present")

    def test_exactly_four_ground_truth_windows(self):
        import fitz
        from extraction.extractor import extract_page
        from detection import run_heuristics

        doc = fitz.open(self.pdf)
        page_data = extract_page(doc, 0)
        cands = run_heuristics(page_data, [], disable_walls=True)
        wins = [c for c in cands if c.entity_type == "window"]

        self.assertEqual(len(wins), 4, f"expected 4 windows, got {len(wins)}: "
                         f"{[tuple(round(v) for v in c.bbox) for c in wins]}")
        for cx, cy in self.GT_WINDOWS:
            self.assertTrue(any(_covers(c.bbox, cx, cy, pad=10) for c in wins),
                            f"ground-truth window near ({cx},{cy}) not detected")
        for cx, cy in self.FP_CENTERS:
            self.assertFalse(any(_covers(c.bbox, cx, cy, pad=4) for c in wins),
                             f"false positive detected near ({cx},{cy})")


if __name__ == "__main__":
    unittest.main()
