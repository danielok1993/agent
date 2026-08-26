"""Window detection tests.

Ground truth was established interactively on s01 (formerly floor-plans.pdf):
exactly four windows, each drawn as a thin glazing rectangle — a tight cluster
of >=3 parallel, equal-length "glazing" lines (glass-pane edges + centerline)
closed at both ends by short perpendicular "cap" lines. See
docs/window-detection-tuning-guide.md for the topology reference.

These tests pin:
  * the two orientations (horizontal W1-style, vertical W4-style) are detected,
  * the documented rejection cases stay rejected (n<3 cluster, no caps, cluster
    too thick), and
  * door entities suppress overlapping window candidates
    (_resolve_door_window_conflicts), and
  * the real s01 yields exactly the four ground-truth windows.
"""
import math
import unittest

from detection import detect_windows
from detection.geometry import _interval_overlap
from detection.postprocess import _resolve_door_window_conflicts
from detection.windows import (
    WINDOW_CAP_ALIGN_OVERLAP, WINDOW_CAP_LEN_RATIO, WINDOW_MAX_WIDTH_PX,
    WINDOW_MIN_WIDTH_PX, WINDOW_SPAN_COVER_TOL_PX, WINDOW_SPAN_OVERSHOOT_PX,
    WINDOW_SPAN_PERP_TOL_PX, WINDOW_GATES_UNSCALED, _dedupe_by_perp,
    _facing_cap_pairs, _glaze_index, _spanning_glazing, _tight_band,
)
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

    def test_narrow_slot_wall_rejected(self):
        """5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is
        far narrower than the caps are long (33px) — a thin wall slot / wall
        crossing, not an opening. A real window's opening is wider than its jamb
        thickness (all true windows: width/cap >= 2.6). Scale-invariant gate."""
        # vertical band: 3 horizontal glazing lines 15px wide, ~33px-long caps
        paths = [
            hline(800, 792.0, 807.0, 960.0),
            hline(801, 792.0, 807.0, 962.0),
            hline(802, 792.0, 807.0, 964.0),
            vline(803, 955.0, 988.0, 792.0),   # cap, 33px (>> 15px opening)
            vline(804, 955.0, 988.0, 807.0),   # cap, 33px
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


class TestWindowInteriorClutter(unittest.TestCase):
    """A real window's glazing band is clear glass — nothing between the panes.
    An insulation-hatched wall, by contrast, gets read as a 2-line band whose
    two "panes" are the wall's two faces, with the crosshatch fill sitting right
    between them. The band-interior gate rejects exactly that: clutter (re/qu/c
    shapes, or oblique line strokes) in the oriented rectangle spanning the gap
    between the caps × across the pane band.

    Crucially this is measured in the rotated (u, v) frame confined to the pane
    band — NOT the axis-aligned bbox — so DIAGONAL windows survive: their loose
    axis bbox would sweep in neighbours, and their gray jamb caps (filled re/qu/c
    shapes) sit at the opening ENDS, outside the band. The solid-filled-block
    (w17/w18) and "recess" (w26) page-1 FPs are NOT rejected here — their clutter
    sits at those same ends, so no interior gate separates them from a diagonal
    window's jambs; they are left to Gemini. See
    docs/window-detection-tuning-guide.md."""

    # Shared valid 2-line capped opening (rails 7px apart, 13px caps) — detects
    # as a window on its own (see the control). Only the band interior differs.
    def _clean_opening(self, base):
        return [
            hline(base + 0, 100.0, 176.0, 386.0),   # rail / glazing pane
            hline(base + 1, 100.0, 176.0, 393.0),   # rail / glazing pane
            vline(base + 2, 383.0, 396.0, 100.0),   # cap (13px jamb)
            vline(base + 3, 383.0, 396.0, 176.0),   # cap
        ]

    def test_clean_two_line_window_still_detected(self):
        """Control: the bare 2-line capped opening with an empty band interior is
        still a window (must not be collateral damage of the clutter gate)."""
        self.assertEqual(len(detect_windows(self._clean_opening(300))), 1)

    def test_hatched_wall_with_interior_shapes_rejected(self):
        """5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two
        wall rails span the caps like a 2-pane band, but the crosshatch fill
        drops re/qu/c shapes BETWEEN the rails — glazing never does."""
        paths = self._clean_opening(400) + [
            path(404, [(110, 389), (118, 391)], item_type="qu"),
            path(405, [(120, 389), (128, 391)], item_type="re"),
            path(406, [(130, 389), (138, 391)], item_type="qu"),
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_hatched_wall_line_only_rejected(self):
        """Insulation hatch drawn with pure line segments (no re/qu/c): the
        diagonal hatch strokes between the rails are parallel to neither the
        glazing nor the caps, so the oblique-line gate rejects the wall."""
        paths = self._clean_opening(500) + [
            path(504, [(108, 389), (114, 391)]),   # diagonal hatch strokes
            path(505, [(120, 389), (126, 391)]),
            path(506, [(132, 389), (138, 391)]),
            path(507, [(144, 389), (150, 391)]),
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_shapes_outside_the_pane_band_are_ignored(self):
        """Decorations OUTSIDE the pane band (here, well beyond a cap along the
        run axis — where real diagonal windows carry their filled jamb blocks)
        must not reject the window. Only clutter BETWEEN the panes counts."""
        paths = self._clean_opening(700) + [
            path(704, [(60.0, 388.0), (64.0, 391.0)], item_type="re"),   # left of left cap
            path(705, [(212.0, 388.0), (216.0, 391.0)], item_type="qu"),  # right of right cap
        ]
        self.assertEqual(len(detect_windows(paths)), 1)

    def test_diagonal_window_with_off_band_shapes_still_detected(self):
        """Regression (the bug this gate first introduced): a 45-deg window must
        not be rejected by shapes that fall inside its loose axis-aligned bbox
        but OUTSIDE the oriented pane band — e.g. the gray jamb fills every real
        diagonal window on 5-1133 carries. The axis-bbox version of the gate
        wrongly rejected all four diagonal windows; the (u, v)-frame gate keeps
        them. (370,430)/(430,370) sit in the bbox but ~42px off the 45-deg band."""
        paths = diagonal_window(800, 45) + [
            path(810, [(369.0, 429.0), (372.0, 432.0)], item_type="re"),
            path(811, [(428.0, 368.0), (431.0, 371.0)], item_type="re"),
        ]
        self.assertEqual(len(detect_windows(paths)), 1,
                         "diagonal window wrongly rejected by off-band shapes")

    def test_diagonal_hatched_wall_rejected(self):
        """The gate works in the rotated frame too: a 45-deg insulation-hatched
        wall (two rails + crosshatch shapes BETWEEN them) is still rejected."""
        c = (400.0, 400.0)
        rails_caps = [
            path(820, [_rot(362, 399, *c, 45), _rot(438, 399, *c, 45)]),   # rail
            path(821, [_rot(362, 401, *c, 45), _rot(438, 401, *c, 45)]),   # rail
            path(822, [_rot(362, 389, *c, 45), _rot(362, 411, *c, 45)]),   # cap
            path(823, [_rot(438, 389, *c, 45), _rot(438, 411, *c, 45)]),   # cap
        ]
        hatch = [
            path(824 + i, [_rot(372 + 12 * i, 399, *c, 45), _rot(378 + 12 * i, 401, *c, 45)],
                 item_type="qu")
            for i in range(3)
        ]
        self.assertEqual(detect_windows(rails_caps + hatch), [])


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


def quad(idx: int, x0: float, y0: float, x1: float, y1: float) -> PathPrimitive:
    return path(idx, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], item_type="qu")


def framed_triple_window(base: int):
    """5-1133 W8: a three-light frame tagged with a single label. Two full-span
    rails ~15px apart, jamb end caps and mullions drawn as small qu blocks, and
    the center glazing line segmented per light by the mullions. Real geometry
    (path_index 3087/3088 etc.)."""
    return [
        hline(base + 0, 926.2, 1188.2, 267.2),         # top rail
        hline(base + 1, 926.2, 1194.2, 282.0),         # bottom rail
        quad(base + 2, 926.2, 267.2, 932.2, 281.7),    # left end cap
        quad(base + 3, 1188.2, 267.2, 1194.2, 282.2),  # right end cap
        quad(base + 4, 1010.2, 267.2, 1016.2, 282.2),  # mullion pair 1
        quad(base + 5, 1016.2, 267.2, 1021.7, 282.2),
        quad(base + 6, 1097.2, 267.2, 1103.2, 282.2),  # mullion pair 2
        quad(base + 7, 1103.2, 267.2, 1108.8, 282.2),
        hline(base + 8, 932.2, 1010.2, 274.7),         # center line, light 1
        hline(base + 9, 1021.7, 1097.2, 274.7),        # center line, light 2
        hline(base + 10, 1108.8, 1188.2, 274.7),       # center line, light 3
    ]


def squat_cap_window(base: int):
    """s04 BATHROOM 01 outer-wall window (paths 60-65, 0.56px A-DETL): the
    opening box, three 4.9px-pitch panes (x 1439.1/1444.0/1448.9) running
    exactly between two 9.8x7.1px qu head/sill blocks — aspect 1.38, inside
    the crosshatch-box range the bar aspect gate rejects."""
    return [
        quad(base + 0, 1426.8, 737.7, 1461.2, 840.5),       # opening box
        vline(base + 1, 744.8, 833.4, 1448.9),
        quad(base + 2, 1439.1, 833.4, 1448.9, 840.5),       # sill block
        quad(base + 3, 1439.1, 737.7, 1448.9, 744.8),       # head block
        vline(base + 4, 744.8, 833.4, 1444.0),
        vline(base + 5, 744.8, 833.4, 1439.1),
    ]


class TestSquatBlockCaps(unittest.TestCase):
    """A squat frame block (aspect 1.0-1.8, the crosshatch-box range) is a
    jamb only when >= 3 panes terminate on it — the repeated-pitch signature
    that square hatch boxes never carry."""

    def test_three_panes_on_squat_blocks_detect(self):
        wins = detect_windows(squat_cap_window(600))
        self.assertEqual(len(wins), 1, [tuple(round(v) for v in c.bbox) for c in wins])
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)
        self.assertTrue(_covers(wins[0].bbox, 1444.0, 790.0))

    def test_two_panes_on_squat_blocks_do_not(self):
        paths = [p for p in squat_cap_window(600) if p.path_index != 604]
        self.assertEqual(len(detect_windows(paths)), 0)


class TestFramedMultiLightWindow(unittest.TestCase):
    """5-1133 W8 topology: block caps (qu jambs/mullions) + mullion-bridged
    center glazing. Labeled as one window (W8), so it must detect as one."""

    def test_triple_window_detected_as_one(self):
        wins = detect_windows(framed_triple_window(500))
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}: "
                         f"{[tuple(round(v) for v in c.bbox) for c in wins]}")
        self.assertTrue(_covers(wins[0].bbox, 1060.0, 274.7))
        self.assertEqual(wins[0].evidence["glazing_lines"], 3)
        self.assertEqual(wins[0].evidence["lights"], 3)

    def test_segments_without_mullion_blocks_do_not_chain(self):
        """Collinear segments merge only across a gap a mullion block occupies —
        that physical-bridge requirement is what keeps dashed linework from
        chaining into phantom glazing. Without the blocks no pane spans
        cap-to-cap (the rails alone are 14.8px apart, wider than a band), so
        the frame is not a window."""
        paths = [p for p in framed_triple_window(500)
                 if not (504 <= p.path_index <= 507)]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 0, f"expected 0 windows, got {len(wins)}")

    def test_crossed_block_is_not_a_cap(self):
        """A block with an X drawn through it is a post/column symbol (the
        5-1133 bathroom shower-screen end post), not a jamb. X-ing the right
        end cap removes it from the cap pool, and the remaining frame has no
        facing cap pair, so nothing is detected."""
        paths = framed_triple_window(500) + [
            path(600, [(1188.2, 267.2), (1194.2, 282.2)]),   # X stroke 1
            path(601, [(1188.2, 282.2), (1194.2, 267.2)]),   # X stroke 2
        ]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 0, f"expected 0 windows, got {len(wins)}: "
                         f"{[tuple(round(v) for v in c.bbox) for c in wins]}")


class TestWindowTightPairInterior(unittest.TestCase):
    """The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /
    WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX), pinned on 5-1133 page-1 ground truth.

    A 2-pane band whose panes hug closer than ~2.75px is either a narrow
    double-glazing line (floor-plans true windows: 1.75-2.0px gaps, jambs
    extending 4.3-8.6px beyond the band) or ONE material edge drawn as two
    strokes — the "recess" niche box, the solid-wall step bumps, the
    detail-corner notch and the RWP corner square all measure 1.6-2.5px gaps
    with the band terminating AT the cap ends (margin <= 0). Only the
    beyond-band jamb margin separates the two: a corner-exact cap still
    overlaps the band fully, so plain overlap can't.
    """

    def test_recess_niche_box_rejected(self):
        """5-1133 window_0020: the "recess" niche — a drawn rectangle whose
        long side plus an inner shelf line 2.5px apart read as a 2-pane band
        terminating at the cap ends (the box corners)."""
        paths = [
            vline(900, 1017.2, 1099.7, 1016.7),  # inner shelf line
            vline(901, 1017.2, 1099.7, 1019.2),  # box long side (outer "pane")
            hline(902, 997.2, 1019.2, 1015.2),   # box end ("cap"), ends AT the pane
            hline(903, 997.2, 1018.7, 1101.7),   # box end ("cap")
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_solid_wall_step_bump_rejected(self):
        """5-1133 window_0016/0017: a step in a solid-filled wall block — the
        step's top edge plus the fill's inner edge 2.5px below form the "band";
        the step sides are the "caps" and the band sits at their very end."""
        paths = [
            hline(910, 167.2, 227.7, 253.2),     # step top edge
            hline(911, 169.7, 225.2, 255.7),     # fill inner edge
            vline(912, 253.2, 266.2, 167.2),     # step side ("cap")
            vline(913, 253.2, 266.2, 227.7),     # step side ("cap")
        ]
        self.assertEqual(detect_windows(paths), [])

    def test_tight_pair_interior_to_jambs_detected(self):
        """floor-plans true windows draw a narrow double glazing line (panes
        1.75px apart) centered INSIDE the wall: both jambs run well past the
        band on both sides. The tight gap alone must not reject these."""
        paths = [
            hline(920, 867.5, 922.8, 906.0),     # glazing pair, 1.75px apart
            hline(921, 867.5, 922.8, 907.75),
            vline(922, 896.0, 918.0, 867.5),     # 22px jamb, band centered in it
            vline(923, 896.0, 918.0, 922.8),
        ]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}")

    def test_wide_pair_at_cap_end_detected(self):
        """5-1133 window_0022 (real diagonal 2-pane window): its band sits at
        the cap ends too — but its panes are 3.5px apart, a real pane pair, so
        the interior test must not fire. Exact page-1 linework."""
        paths = [
            path(930, [(1856.3, 1307.7), (1786.3, 1235.7)]),  # glazing
            path(931, [(1858.8, 1305.2), (1788.7, 1233.2)]),  # glazing
            path(932, [(1836.6, 1326.6), (1858.6, 1305.1)]),  # jamb cap
            path(933, [(1766.7, 1254.7), (1788.7, 1233.2)]),  # jamb cap
        ]
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1, f"expected 1 window, got {len(wins)}")


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

    def test_fallback_tier_door_has_reduced_veto_reach(self):
        """A DOOR_FALLBACK_CONFIDENCE (0.35) door often IS window-like ink
        (glazing mullions, sliding panels), so its veto reach shrinks to near
        its own linework instead of the full 20px dilation. 5-1133 W8 sat 10px
        below mullion strips read as fallback doors; their 20px dilation
        covered 11% of its band and killed it. The same geometry at
        real-detection confidence keeps the full reach."""
        win = self._win((926.0, 267.0, 1194.0, 282.0))       # 5-1133 W8
        fallback = Candidate("door_0108", "door", (1110.0, 81.0, 1115.0, 257.0), 0.35, {})
        self.assertIn(win, _resolve_door_window_conflicts([win, fallback]))
        real = Candidate("door_0108", "door", (1110.0, 81.0, 1115.0, 257.0), 0.55, {})
        self.assertNotIn(win, _resolve_door_window_conflicts([win, real]))

    def test_fallback_door_still_vetoes_window_on_its_own_ink(self):
        """A window candidate sitting ON a fallback door's linework (5-1133:
        the joinery slats at (1072,740) read as both a window band and a
        fallback door) is genuinely ambiguous and yields to the door tier
        even at fallback confidence."""
        win = self._win((1072.0, 740.0, 1082.0, 800.0))
        fallback = Candidate("door_0092", "door", (1075.0, 751.0, 1082.0, 790.0), 0.35, {})
        self.assertNotIn(win, _resolve_door_window_conflicts([win, fallback]))


class TestFloorPlansRegression(unittest.TestCase):
    """End-to-end regression: floor-plans.pdf must yield exactly the four
    ground-truth windows and none of the documented false positives."""

    GT_WINDOWS = [(958, 850), (895, 903), (1103, 1387), (941, 1387)]  # W4, W3, W2, W1 centers
    FP_CENTERS = [(980, 783), (1053, 812), (980, 936), (1004, 1118)]  # toilet, sink, toilet, door-leaf

    def setUp(self):
        from tests.fixtures import require_sheet
        self.pdf = str(require_sheet(self, "s01"))

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


class TestWindowPruningEquivalence(unittest.TestCase):
    """The spatial pruning inside detect_windows must be output-identical.

    `_facing_cap_pairs` (v-bucketed) and `_spanning_glazing` (perp-indexed) only
    exist to skip work the gates provably reject. These tests pin them against
    brute-force references on synthetic dense data — the same shape of input the
    100k-path sheets produce, where the pruning actually bites.
    """

    @staticmethod
    def _dense_caps(n: int = 400) -> list[dict]:
        """Caps scattered over a page-sized (u, v) field, perp-sorted.

        Deterministic LCG rather than `random` so a failure reproduces exactly.
        Cap lengths straddle the [3, 36] pool bounds and spans are built from
        the length, so the facing gate sees realistic partners.
        """
        caps: list[dict] = []
        seed = 12345
        for i in range(n):
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            u = (seed % 90000) / 100.0            # 0-900 px along the run axis
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            v = (seed % 60000) / 100.0            # 0-600 px along the caps
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            length = 3.0 + (seed % 3400) / 100.0  # 3.0 - 37.0 px
            caps.append({"idx": i, "perp": u, "span": (v, v + length),
                         "len": length, "block": False})
        return sorted(caps, key=lambda c: c["perp"])

    @staticmethod
    def _brute_pairs(caps: list[dict]) -> list[tuple[int, int, float]]:
        """The pre-optimization double loop, verbatim."""
        out: list[tuple[int, int, float]] = []
        for i, c1 in enumerate(caps):
            for j in range(i + 1, len(caps)):
                c2 = caps[j]
                width = c2["perp"] - c1["perp"]
                if width < WINDOW_MIN_WIDTH_PX:
                    continue
                if width > WINDOW_MAX_WIDTH_PX:
                    break
                if min(c1["len"], c2["len"]) / max(c1["len"], c2["len"]) < WINDOW_CAP_LEN_RATIO:
                    continue
                overlap = _interval_overlap(c1["span"], c2["span"])
                if overlap < WINDOW_CAP_ALIGN_OVERLAP * min(c1["len"], c2["len"]):
                    continue
                out.append((i, j, width))
        return out

    def test_facing_cap_pairs_match_brute_force(self):
        caps = self._dense_caps()
        expected = self._brute_pairs(caps)
        self.assertGreater(len(expected), 500, "test data must exercise the pruning")
        self.assertEqual(list(_facing_cap_pairs(caps, gates=WINDOW_GATES_UNSCALED)), expected)

    def test_facing_cap_pairs_survive_negative_and_binned_coordinates(self):
        """Caps straddling 0 and a bin edge — floor() on negatives, adjacency."""
        caps = sorted(
            [{"idx": 0, "perp": 0.0, "span": (-0.5, 19.5), "len": 20.0},
             {"idx": 1, "perp": 40.0, "span": (-20.0, 0.0), "len": 20.0},
             {"idx": 2, "perp": 60.0, "span": (-2.0, 18.0), "len": 20.0},
             {"idx": 3, "perp": 90.0, "span": (39.5, 59.5), "len": 20.0},
             {"idx": 4, "perp": 120.0, "span": (38.0, 58.0), "len": 20.0}],
            key=lambda c: c["perp"])
        self.assertEqual(list(_facing_cap_pairs(caps, gates=WINDOW_GATES_UNSCALED)), self._brute_pairs(caps))

    @staticmethod
    def _dense_glaze(caps: list[dict], n: int = 500) -> list[dict]:
        """Glazing pool in unsorted pool order: field noise + real bridging panes.

        The noise is what the old full-pool scan walked for every pair; the
        panes are seeded off actual cap pairs so bands actually form (random
        spans essentially never satisfy the bridging gate).
        """
        pool: list[dict] = []
        seed = 999331
        for i in range(n):
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            perp = (seed % 60000) / 100.0
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            lo = (seed % 90000) / 100.0
            seed = (seed * 1103515245 + 12345) % (2 ** 31)
            length = 10.0 + (seed % 20000) / 100.0
            pool.append({"idx": i, "path": None, "len": length,
                         "perp": perp, "span": (lo, lo + length)})
        for i, j, width in _facing_cap_pairs(caps, gates=WINDOW_GATES_UNSCALED):
            if i % 5:
                continue
            v_lo = max(caps[i]["span"][0], caps[j]["span"][0])
            for d in (0.5, 2.0, 3.5):
                pool.append({"idx": len(pool), "path": None, "len": width,
                             "perp": v_lo + d,
                             "span": (caps[i]["perp"] + 0.5, caps[j]["perp"] - 0.5)})
        # Exact perp/len ties: _dedupe_by_perp resolves those by POOL ORDER, so
        # a reordered scan would silently swap which record survives.
        pool.append(dict(pool[-1], idx=len(pool)))
        return pool

    @staticmethod
    def _brute_spanning(pool: list[dict], c1: dict, c2: dict) -> list[dict]:
        """The pre-optimization full-pool scan, verbatim."""
        ext_lo = min(c1["span"][0], c2["span"][0]) - WINDOW_SPAN_PERP_TOL_PX
        ext_hi = max(c1["span"][1], c2["span"][1]) + WINDOW_SPAN_PERP_TOL_PX
        spanning = [g for g in pool
                    if ext_lo <= g["perp"] <= ext_hi
                    and c1["perp"] - WINDOW_SPAN_OVERSHOOT_PX <= g["span"][0] <= c1["perp"] + WINDOW_SPAN_COVER_TOL_PX
                    and c2["perp"] - WINDOW_SPAN_COVER_TOL_PX <= g["span"][1] <= c2["perp"] + WINDOW_SPAN_OVERSHOOT_PX]
        return _tight_band(_dedupe_by_perp(spanning))

    def test_spanning_glazing_index_matches_brute_force(self):
        caps = self._dense_caps(120)
        pool = self._dense_glaze(caps)
        index = _glaze_index(pool)
        hits = 0
        for i, j, _width in _facing_cap_pairs(caps, gates=WINDOW_GATES_UNSCALED):
            expected = self._brute_spanning(pool, caps[i], caps[j])
            got = _spanning_glazing(index, caps[i], caps[j])
            self.assertEqual([id(r) for r in got], [id(r) for r in expected],
                             f"band differs for cap pair ({i}, {j})")
            hits += len(expected)
        self.assertGreater(hits, 0, "test data must produce spanning bands")

    def test_spanning_glazing_index_keeps_pool_order_on_exact_ties(self):
        """Two records at the same perp AND len: pool order picks the survivor."""
        first = {"idx": 0, "path": None, "len": 50.0, "perp": 10.0, "span": (0.0, 50.0)}
        second = dict(first, idx=1)
        third = {"idx": 2, "path": None, "len": 50.0, "perp": 14.0, "span": (0.0, 50.0)}
        c1 = {"perp": 0.0, "span": (8.0, 16.0), "len": 8.0}
        c2 = {"perp": 50.0, "span": (8.0, 16.0), "len": 8.0}
        for pool in ([first, second, third], [second, first, third]):
            band = _spanning_glazing(_glaze_index(pool), c1, c2)
            self.assertEqual([r["idx"] for r in band],
                             [r["idx"] for r in self._brute_spanning(pool, c1, c2)])


class TestWindowSpanOvershootRetune(unittest.TestCase):
    """Pins the WINDOW_SPAN_OVERSHOOT_PX = 11.0 retune (measured 2026-08-13).

    Confirmed windows' overshoot tails reach 10.50px (s02's diagonal window;
    p90 8.77 across the corpus), while the s12/s18/s20 phantom-window families
    — wall/paving linework read as a 2-pane band — overshoot at 11.75-11.98px.
    A fixture at each tail pins the gate between them.
    """

    @staticmethod
    def _opening(overshoot: float) -> list[PathPrimitive]:
        # Two 22px caps 40px apart, two panes 7px apart (clear of the
        # tight-pair gate), each pane running `overshoot` past BOTH caps.
        return [
            hline(0, 380.0 - overshoot, 420.0 + overshoot, 396.5),
            hline(1, 380.0 - overshoot, 420.0 + overshoot, 403.5),
            vline(2, 389.0, 411.0, 380.0),
            vline(3, 389.0, 411.0, 420.0),
        ]

    def test_confirmed_tail_overshoot_detects(self):
        # 10.5px = the corpus's confirmed maximum (s02 window_0007) — must
        # stay inside the gate.
        self.assertEqual(len(detect_windows(self._opening(10.5))), 1)

    def test_fp_tail_overshoot_rejected(self):
        # 11.8px = the s12/s18/s20 phantom families (11.75-11.98) — both
        # panes overshoot past the gate, so no band survives.
        self.assertEqual(detect_windows(self._opening(11.8)), [])


class TestWindowInvisibleFillEdges(unittest.TestCase):
    """Wall fills exploded into polygon edges are not linework (s03).

    s03 draws each wall as a solid-filled polygon (``EXISTING_BRICKWORK``, gray
    fill) whose PDF stroke is width 0 in the SAME gray — invisible against its
    own fill. The exporter triangulates the fill, so PyMuPDF hands us its two
    long faces, its two end edges AND the shared triangulation diagonal as
    ``l`` items with a fill colour. On a thin band the diagonal runs 2-5 deg
    off the faces — inside WINDOW_ANGLE_TOL_DEG — so it read as a third
    "pane" between the two faces, and every wall segment between two crossing
    walls (end edges = caps, faces = panes) matched the 3-pane window
    signature: 21 phantom windows on s03, all built ENTIRELY from these edges.

    A filled path's boundary is only linework where its stroke is visible
    against its own fill (fill=None ⇒ plain stroke ⇒ linework; a filled path
    with no stroke colour, or a stroke the same colour as its fill, is area).
    """

    GRAY = (0.73, 0.73, 0.73)

    @classmethod
    def _fill_edge(cls, idx: int, a: tuple[float, float], b: tuple[float, float],
                   *, color=GRAY, fill=GRAY, stroke_width: float = 0.0) -> PathPrimitive:
        xs, ys = (a[0], b[0]), (a[1], b[1])
        return PathPrimitive(
            path_index=idx, item_type="l",
            bbox=(min(xs), min(ys), max(xs), max(ys)),
            color=color, fill=fill, stroke_width=stroke_width, dashes="",
            layer="EXISTING_BRICKWORK", points=[a, b],
        )

    @classmethod
    def _filled_band(cls, base: int, x0: float, x1: float, y0: float, y1: float, **kw) -> list[PathPrimitive]:
        """A wall band as PyMuPDF explodes s03's triangulated fill: two triangles
        sharing the (x0,y0)-(x1,y1) diagonal, all edges self-coloured."""
        return [
            cls._fill_edge(base + 0, (x1, y0), (x0, y0), **kw),   # top face
            cls._fill_edge(base + 1, (x0, y0), (x1, y1), **kw),   # diagonal (triangle 1)
            cls._fill_edge(base + 2, (x1, y1), (x1, y0), **kw),   # right end edge
            cls._fill_edge(base + 3, (x0, y0), (x1, y1), **kw),   # diagonal (triangle 2)
            cls._fill_edge(base + 4, (x1, y1), (x0, y1), **kw),   # bottom face
            cls._fill_edge(base + 5, (x0, y1), (x0, y0), **kw),   # left end edge
        ]

    def test_thin_filled_wall_band_is_not_a_window(self):
        # s03 window_0029: 159.5 x 6.0px band, diagonal 2.2 deg off the faces.
        self.assertEqual(detect_windows(self._filled_band(0, 486.9, 646.4, 663.2, 669.2)), [])

    def test_wall_thick_filled_band_is_not_a_window(self):
        # s03 window_0040: 156 x 14.8px band — without the diagonal its two
        # faces would still pair as a 2-pane band over 14.7px caps, so the
        # faces themselves must not be panes either.
        self.assertEqual(detect_windows(self._filled_band(0, 1407.7, 1563.7, 4143.4, 4158.2)), [])

    def test_unstroked_fill_band_is_not_a_window(self):
        # Vectorworks-style fill-only polygons (type "f": no stroke colour).
        band = self._filled_band(0, 486.9, 646.4, 663.2, 669.2, color=None)
        self.assertEqual(detect_windows(band), [])

    def test_stroked_window_inside_a_filled_wall_still_detected(self):
        # A real stroked 3-pane window whose band happens to sit inside a
        # filled wall band: the fill edges are ignored, the ink is not.
        paths = horizontal_window(100, 100.0, 176.0, 387.0)
        paths += self._filled_band(200, 60.0, 216.0, 376.0, 398.0)
        wins = detect_windows(paths)
        self.assertEqual(len(wins), 1)
        self.assertTrue(_covers(wins[0].bbox, 138.0, 387.0))

    @classmethod
    def _capped_rectangle(cls, **kw) -> list[PathPrimitive]:
        # test_two_line_capped_rectangle_detected's geometry (5-1133 Window B:
        # two panes 2px apart between 22px caps), drawn as one filled path.
        return [
            cls._fill_edge(0, (100.0, 386.0), (176.0, 386.0), **kw),
            cls._fill_edge(1, (100.0, 388.0), (176.0, 388.0), **kw),
            cls._fill_edge(2, (100.0, 376.0), (100.0, 398.0), **kw),
            cls._fill_edge(3, (176.0, 376.0), (176.0, 398.0), **kw),
        ]

    def test_visibly_outlined_fill_edges_stay_linework(self):
        # A filled path whose stroke is a DIFFERENT colour from its fill is
        # drawn linework: its edges are as eligible as plain stroked lines.
        wins = detect_windows(self._capped_rectangle(color=(0.0, 0.0, 0.0), fill=self.GRAY))
        self.assertEqual(len(wins), 1)

    def test_self_coloured_fill_edges_are_not_linework(self):
        # ...while the SAME geometry stroked in its own fill colour (or not
        # stroked at all) is invisible area, whatever the pen width says.
        self.assertEqual(detect_windows(self._capped_rectangle(stroke_width=0.0)), [])
        self.assertEqual(detect_windows(self._capped_rectangle(stroke_width=1.5)), [])
        self.assertEqual(detect_windows(self._capped_rectangle(color=None)), [])


if __name__ == "__main__":
    unittest.main()
