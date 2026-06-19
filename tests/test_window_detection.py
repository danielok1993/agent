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

    def test_two_line_capped_rectangle_detected(self):
        """A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:
        two parallel glazing lines, no centerline, closed by end caps). The old
        n>=3 gate wrongly rejected this; the cap-anchored detector accepts it."""
        top, bot = 376.0, 398.0
        paths = [
            hline(300, 100.0, 176.0, 386.0),
            hline(301, 100.0, 176.0, 388.0),
            vline(302, top, bot, 100.0),
            vline(303, top, bot, 176.0),
        ]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}")

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


class TestWindow51133Topology(unittest.TestCase):
    """Ground truth captured interactively on 5-1133-WD03.pdf (run
    2026-06-19_12-02-48). These windows have wider line spacing (~7px), greater
    pane depth (~14px), and variable glazing-line counts (2 or 3) than
    floor-plans — they motivated the cap-anchored rewrite. Coordinates are the
    real path geometry (150-DPI px); the lines the user clicked are noted."""

    def _window_a(self):
        # Window A: 3 horizontal glazing lines (~7px apart, 13.7px deep) closed
        # by two short vertical caps. User clicked 2926 + caps 2909/2925.
        return [
            hline(2904, 504.7, 618.2, 271.7),
            hline(2926, 508.2, 614.7, 278.7),   # clicked (middle line)
            hline(2905, 500.8, 622.2, 285.4),
            vline(2909, 271.7, 285.2, 508.2),   # cap
            vline(2925, 271.7, 285.7, 614.7),   # cap
        ]

    def _window_b(self):
        # Window B: 2 vertical glazing lines (7.6px apart, no centerline) closed
        # by two horizontal caps. User clicked 2046/2167 + 1951/2267.
        return [
            vline(2046, 761.7, 935.2, 186.7),
            vline(2167, 761.7, 935.2, 194.3),
            hline(1951, 171.6, 201.6, 761.6),   # cap (overshoots the glazing)
            hline(2267, 171.1, 201.1, 935.1),   # cap
        ]

    def _window_bonus(self):
        # Bonus small window: 3 short horizontal glazing lines closed by tiny
        # (~5px) vertical caps. User clicked 2181.
        return [
            hline(2170, 267.2, 297.7, 506.2),
            hline(2181, 272.2, 292.8, 508.7),   # clicked (short middle line)
            hline(2094, 268.8, 296.2, 510.9),
            vline(2096, 506.2, 510.7, 272.2),   # cap
            vline(2295, 506.2, 511.2, 292.8),   # cap
        ]

    def test_window_a_detected(self):
        wins = detect_windows(self._window_a())
        self.assertEqual(len(wins), 1, f"Window A: expected 1, got {len(wins)}")
        self.assertTrue(_covers(wins[0].bbox, 561.5, 278.5))

    def test_window_b_detected(self):
        wins = detect_windows(self._window_b())
        self.assertEqual(len(wins), 1, f"Window B: expected 1, got {len(wins)}")
        self.assertTrue(_covers(wins[0].bbox, 190.5, 848.4))

    def test_window_bonus_detected(self):
        wins = detect_windows(self._window_bonus())
        self.assertEqual(len(wins), 1, f"Bonus: expected 1, got {len(wins)}")
        self.assertTrue(_covers(wins[0].bbox, 282.5, 508.5))

    def test_all_three_independent(self):
        wins = detect_windows(self._window_a() + self._window_b() + self._window_bonus())
        self.assertEqual(len(wins), 3, f"expected 3 windows, got {len(wins)}")

    def test_fixture_hatch_rejected(self):
        """A toilet/sink fixture is a hatch of stacked short segments plus
        collinear duplicate edges — no set of >=2 lines at DISTINCT offsets
        spans the full gap between facing caps, so it must not be a window."""
        paths = [
            # facing horizontal caps (the fixture outline ends)
            hline(900, 200.0, 227.0, 796.5),
            hline(901, 200.0, 227.0, 828.5),
            # two collinear vertical edges at the SAME x (duplicate, not panes)
            vline(902, 752.5, 828.5, 200.0),
            vline(903, 796.5, 828.5, 200.0),
            # stacked short hatch segments (don't span the gap)
            hline(904, 200.0, 207.0, 805.3),
            hline(905, 200.0, 207.0, 811.0),
            hline(906, 200.0, 207.0, 822.3),
        ]
        self.assertEqual(detect_windows(paths), [])


def _rot(px, py, cx, cy, deg):
    r = math.radians(deg)
    dx, dy = px - cx, py - cy
    return (cx + dx * math.cos(r) - dy * math.sin(r),
            cy + dx * math.sin(r) + dy * math.cos(r))


def diagonal_window(base, deg, *, length=76.0, depth=22.0, cx=400.0, cy=400.0):
    """A horizontal window rotated by `deg` about (cx, cy).

    Identical cap-anchored topology to ``horizontal_window`` — three parallel
    glazing lines closed by two perpendicular end caps — but oriented at an
    arbitrary angle. Windows in real CAD drawings sit at any angle (45, 50, 60,
    70 ...), so detection must be orientation-agnostic, not axis-locked.
    """
    x0, x1 = cx - length / 2, cx + length / 2
    top, bot = cy - depth / 2, cy + depth / 2
    raw = [
        (base + 0, [(x0, cy - 1.0), (x1, cy - 1.0)]),
        (base + 1, [(x0, cy),       (x1, cy)]),
        (base + 2, [(x0, cy + 1.0), (x1, cy + 1.0)]),
        (base + 3, [(x0, top), (x0, bot)]),
        (base + 4, [(x1, top), (x1, bot)]),
    ]
    return [path(idx, [_rot(px, py, cx, cy, deg) for px, py in pts]) for idx, pts in raw]


class TestWindowArbitraryAngle(unittest.TestCase):
    """Windows are drawn at any angle, not just axis-aligned. The cap-anchored
    model is orientation-invariant by construction — anchor on a facing
    perpendicular cap pair, confirm a parallel glazing band — so a window
    rotated to 45/50/60/70 deg must detect exactly like its axis-aligned twin."""

    def test_windows_detected_at_arbitrary_angles(self):
        for deg in (30, 45, 50, 60, 70, 115, 135):
            wins = detect_windows(diagonal_window(800, deg))
            self.assertEqual(len(wins), 1, f"angle {deg}: expected 1, got {len(wins)}")
            self.assertTrue(_covers(wins[0].bbox, 400.0, 400.0, pad=12),
                            f"angle {deg}: bbox {wins[0].bbox} off-center")

    def test_real_diagonal_window_5_1133(self):
        """5-1133-WD03.pdf missed window at path idx 6475: three glazing panes
        at 135 deg (idx 6473/6474/6475) closed by two perpendicular ~31px caps
        (idx 1926/1948) only 1.3 deg apart. Real path geometry (150-DPI px) from
        run 2026-06-19_12-44-52 — the axis-only detector could not see it, and a
        disjoint angle-clustering split the two near-parallel caps apart."""
        paths = [
            path(6473, [(211, 723), (268, 667)]),   # glazing
            path(6474, [(216, 729), (273, 673)]),   # glazing
            path(6475, [(222, 734), (278, 678)]),   # glazing
            path(1926, [(257, 656), (278, 678)]),   # cap (perpendicular)
            path(1948, [(222, 734), (200, 712)]),   # cap (perpendicular)
        ]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1, got {len(wins)}")


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

    def test_window_grazing_dilated_door_corner_kept(self):
        """A distant door must not suppress a window it only clips after the
        20px dilation. 5-1133 Window A (500.8-622.2, 271.7-285.7) was wrongly
        dropped by a weak door at y82-255 whose dilated bbox grazed a ~6x4px
        corner. Suppression requires *material* overlap, not a corner touch."""
        win = self._win((500.8, 271.7, 622.2, 285.7))        # 5-1133 Window A
        door = self._door((635.7, 82.2, 660.7, 255.2))       # far door (leaf_fallback)
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
