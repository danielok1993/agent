"""Scale-factor behavior of the door gates: identity at 1.0, linear at 0.5.

A "faithful 1:100 export" scales EXTENTS and keeps PAPER quantities — pen
widths and drawn ink separations — unchanged. See
docs/superpowers/specs/2026-08-12-scale-aware-door-gates-design.md §1/§2.
"""
import unittest

from detection.doors.constants import (
    DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_FOLD_LEAF_LINE_SEP_MAX_PX,
    DOOR_LEAF_COMPANION_PERP_PX, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_SLIDE_PANEL_MIN_THICKNESS_PX, DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
    DOOR_GATES_UNSCALED, DoorGates,
)


class TestDoorGatesConstruction(unittest.TestCase):
    def test_identity_at_one(self):
        g = DoorGates.at(1.0)
        self.assertEqual(g.DOOR_MIN_SIZE_PX, DOOR_MIN_SIZE_PX)
        self.assertEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX)
        self.assertEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_ASSEMBLY_CONNECT_TOL_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX)
        self.assertEqual(g, DOOR_GATES_UNSCALED)

    def test_world_gates_scale_linearly(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_MAX_SIZE_PX, DOOR_MAX_SIZE_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_ASSEMBLY_CONNECT_TOL_PX,
                               DOOR_ASSEMBLY_CONNECT_TOL_PX * 0.5)
        self.assertAlmostEqual(g.DOOR_SLIDE_PANEL_MAX_THICKNESS_PX,
                               DOOR_SLIDE_PANEL_MAX_THICKNESS_PX * 0.5)

    def test_min_size_floored_at_one_pixel(self):
        # Floor is a backstop: at the f=0.25 clamp the raw product is 5.0px,
        # so it is inert on the calibrated domain.
        self.assertAlmostEqual(DoorGates.at(0.25).DOOR_MIN_SIZE_PX,
                               DOOR_MIN_SIZE_PX * 0.25)
        self.assertEqual(DoorGates.at(0.001).DOOR_MIN_SIZE_PX, 1.0)

    def test_rejects_non_positive_factor(self):
        # The ONLY assertion: factor-independent, so a failure is a bug.
        with self.assertRaises(AssertionError):
            DoorGates.at(0.0)
        with self.assertRaises(AssertionError):
            DoorGates.at(-1.0)

    def test_paper_space_constants_have_no_field(self):
        # Absence from the dataclass is what makes "does not scale" reviewable.
        g = DoorGates.at(0.5)
        for name in ("DOOR_LEAF_COMPANION_PERP_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MIN_PX",
                     "DOOR_FOLD_LEAF_LINE_SEP_MAX_PX",
                     "DOOR_POLYLINE_ENDPOINT_TOL",
                     "DOOR_LABEL_SEARCH_RADIUS_PX",
                     "DOOR_FOLD_HINGE_TOL_PX",
                     "DOOR_BBOX_ASPECT_MIN", "DOOR_BBOX_ASPECT_MAX"):
            self.assertFalse(hasattr(g, name), f"{name} is P or D — must not be a gates field")

    def test_cross_class_inversion_is_a_no_op_not_a_crash(self):
        # DOOR_FOLD_LEAF_LINE_SEP_MAX_PX (P, 4.0) vs
        # DOOR_SLIDE_PANEL_MIN_THICKNESS_PX (W, 3.0*f) invert below f=0.75 —
        # every 1:100 sheet. They gate DIFFERENT detectors and are never
        # compared, so nothing may assert or clamp the ordering. This test
        # exists so nobody "fixes" the crossing later.
        g = DoorGates.at(0.5)
        self.assertLess(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                        DOOR_FOLD_LEAF_LINE_SEP_MAX_PX)
        self.assertEqual(g.DOOR_SLIDE_PANEL_MIN_THICKNESS_PX,
                         DOOR_SLIDE_PANEL_MIN_THICKNESS_PX * 0.5)


from detection import detect_doors
from detection.doors.arcs import _collect_door_swings, _is_arc_like
from models import PathPrimitive


def prim(idx, item_type, points, stroke_width=1.0, fill=None):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx, item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=(0, 0, 0), fill=fill, stroke_width=stroke_width,
        dashes=None, layer="", points=points)


def quarter_bezier(idx, cx, cy, r):
    """A quarter-arc cubic Bezier of radius r, hinged at (cx, cy).

    r is a WORLD extent: it halves on a 1:100 export.
    """
    k = 0.5523 * r
    return prim(idx, "c", [(cx + r, cy), (cx + r, cy + k), (cx + k, cy + r), (cx, cy + r)])


class TestArcGatesThreading(unittest.TestCase):
    def test_is_arc_like_requires_gates_keyword(self):
        p = quarter_bezier(0, 100, 100, 50)
        with self.assertRaises(TypeError):
            _is_arc_like(p)          # no gates -> must NOT silently run unscaled

    def test_small_arc_rejected_at_f1_accepted_at_half(self):
        # radius 12 -> size 12px: under the 20px floor at f=1.0, over the
        # scaled 10px floor at f=0.5.
        p = quarter_bezier(0, 100, 100, 12)
        self.assertFalse(_is_arc_like(p, gates=DoorGates.at(1.0)))
        self.assertTrue(_is_arc_like(p, gates=DoorGates.at(0.5)))

    def test_collect_swings_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_swings([quarter_bezier(0, 100, 100, 50)])

    def test_detect_doors_identity_factor_equals_omitted(self):
        paths = [quarter_bezier(0, 100, 100, 50)]
        self.assertEqual(
            [c.bbox for c in detect_doors(paths, [])],
            [c.bbox for c in detect_doors(paths, [], None, scale_factor=1.0)])


from detection.doors.leaves import _collect_door_leaves


class TestLeafGatesThreading(unittest.TestCase):
    def test_collect_leaves_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_door_leaves([])

    def test_short_leaf_rect_rejected_at_f1_accepted_at_half(self):
        # A 12 x 2.5 px leaf rectangle: length under the 20px DOOR_MIN_SIZE_PX
        # floor at f=1.0, over the scaled 10px floor at f=0.5. Aspect 4.8
        # clears DOOR_LEAF_ASPECT_MIN (4.0, dimensionless) at both factors.
        leaf = prim(0, "qu", [(0, 0), (12, 0), (12, 2.5), (0, 2.5)])
        self.assertEqual(_collect_door_leaves([leaf], gates=DoorGates.at(1.0)), [])
        self.assertEqual(len(_collect_door_leaves([leaf], gates=DoorGates.at(0.5))), 1)

    def test_leaf_companion_separation_is_paper_space(self):
        # DOOR_LEAF_COMPANION_PERP_PX is P: it must NOT move with the factor.
        # Measured: real leaf separations hold at ~2.6px on 1:100 sheets
        # (spec §2), so a 4px separation must stay acceptable at f=0.5.
        from detection.doors.constants import DOOR_LEAF_COMPANION_PERP_PX
        self.assertFalse(hasattr(DoorGates.at(0.5), "DOOR_LEAF_COMPANION_PERP_PX"))
        self.assertEqual(DOOR_LEAF_COMPANION_PERP_PX, 5.0)


import ast
from pathlib import Path

_DETECTION_DIR = Path(__file__).resolve().parent.parent / "detection"


def _production_door_gates_unscaled_usages() -> list[tuple[str, str]]:
    """Scan detection/**/*.py for PRODUCTION (non-import, non-comment) uses
    of the DOOR_GATES_UNSCALED name, excluding its own definition line in
    constants.py.

    Returns a list of (repo-relative-path, stripped-line-text) — one entry
    per source line outside an import statement that still mentions the
    name after constants.py's own `DOOR_GATES_UNSCALED = DoorGates.at(1.0)`
    definition and pure-comment lines are excluded.
    """
    findings: list[tuple[str, str]] = []
    for path in sorted(_DETECTION_DIR.rglob("*.py")):
        source = path.read_text()
        if "DOOR_GATES_UNSCALED" not in source:
            continue
        rel = path.relative_to(_DETECTION_DIR.parent).as_posix()
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(path))
        import_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                start = node.lineno
                end = getattr(node, "end_lineno", node.lineno)
                import_lines.update(range(start, end + 1))
        for lineno, raw_line in enumerate(lines, start=1):
            if "DOOR_GATES_UNSCALED" not in raw_line:
                continue
            if lineno in import_lines:
                continue
            stripped = raw_line.strip()
            if stripped.startswith("#"):
                continue
            if rel == "detection/doors/constants.py" and stripped.startswith("DOOR_GATES_UNSCALED ="):
                continue
            findings.append((rel, stripped))
    return findings


class TestDoorGatesUnscaledStopgapRatchet(unittest.TestCase):
    """Ratchet on detection/'s production uses of DOOR_GATES_UNSCALED.

    DOOR_GATES_UNSCALED is a TRANSITIONAL STOPGAP, not a sanctioned pattern.
    The one stopgap that existed — assembly.py's call into
    `_find_anchored_leaf_line` hardcoded to `gates=DOOR_GATES_UNSCALED` — has
    now been retired: `_pair_door_assemblies` is threaded with a real scaled
    `gates` parameter and passes it through instead.

    This is a RATCHET, not a plain "must never appear" guard, so it keeps
    scanning rather than being deleted: EXPECTED_USAGES must stay the empty
    tuple `()` forever now. If it ever finds a usage, that is a regression —
    someone reached for DOOR_GATES_UNSCALED as a shortcut instead of
    threading gates properly — and the test must fail, not be "fixed" by
    re-populating EXPECTED_USAGES.

    Matching is by a stable substring (the calling function's name) plus the
    DOOR_GATES_UNSCALED name itself — never by line number, which shifts as
    the file is edited around it.
    """

    # (repo-relative path, stable substring expected on that usage's line)
    # Must stay empty: the assembly.py stopgap has been retired.
    EXPECTED_USAGES: tuple[tuple[str, str], ...] = ()

    def test_door_gates_unscaled_stopgap_set_is_exactly_known(self):
        findings = _production_door_gates_unscaled_usages()
        self.assertEqual(
            len(findings), len(self.EXPECTED_USAGES),
            "The set of production DOOR_GATES_UNSCALED usages in detection/ "
            "changed size. If a stopgap was just retired by threading real "
            "gates through its call site, update EXPECTED_USAGES to match "
            "(empty once assembly.py is threaded). If this is unexpected, a "
            "new stopgap has crept in — thread gates properly instead.\n"
            f"Found: {findings}\nExpected: {list(self.EXPECTED_USAGES)}",
        )
        for rel_expected, substr in self.EXPECTED_USAGES:
            matches = [
                (rel, line) for rel, line in findings
                if rel == rel_expected and substr in line
            ]
            self.assertEqual(
                len(matches), 1,
                f"Expected exactly one DOOR_GATES_UNSCALED usage in "
                f"{rel_expected} matching {substr!r}; found {matches}.\n"
                f"All findings: {findings}",
            )


from detection.doors.sliding import _collect_slide_panels


class TestSlidingGatesThreading(unittest.TestCase):
    def test_collect_panels_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _collect_slide_panels([])

    def test_thin_short_panel_rejected_at_f1_accepted_at_half(self):
        # 15 x 1.8px panel: length under DOOR_MIN_SIZE_PX (20) and thickness
        # under DOOR_SLIDE_PANEL_MIN_THICKNESS_PX (3.0) at f=1.0; both clear
        # their scaled floors (10.0 / 1.5) at f=0.5. Aspect 8.3 > 4.0.
        panel = prim(0, "qu", [(0, 0), (15, 0), (15, 1.8), (0, 1.8)])
        self.assertEqual(_collect_slide_panels([panel], gates=DoorGates.at(1.0)), [])
        self.assertEqual(len(_collect_slide_panels([panel], gates=DoorGates.at(0.5))), 1)

    def test_panel_thickness_ceiling_scales(self):
        # 60 x 15px panel: inside the 3-20px window at f=1.0, above the scaled
        # 1.5-10px window at f=0.5. Pins that MAX scales, not just MIN.
        panel = prim(0, "qu", [(0, 0), (60, 0), (60, 15), (0, 15)])
        self.assertEqual(len(_collect_slide_panels([panel], gates=DoorGates.at(1.0))), 1)
        self.assertEqual(_collect_slide_panels([panel], gates=DoorGates.at(0.5)), [])


from detection.doors.folding import _double_line_leaves


class TestFoldingGatesThreading(unittest.TestCase):
    def test_double_line_leaves_requires_gates_keyword(self):
        with self.assertRaises(TypeError):
            _double_line_leaves([])

    def test_fold_leaf_line_separation_is_paper_space(self):
        # DOOR_FOLD_LEAF_LINE_SEP_MIN/MAX_PX gate a drawn ink separation (P).
        # Scaling them is what zeroed s06 in the spec's §3 table.
        from detection.doors.constants import (
            DOOR_FOLD_LEAF_LINE_SEP_MAX_PX, DOOR_FOLD_LEAF_LINE_SEP_MIN_PX)
        g = DoorGates.at(0.5)
        self.assertFalse(hasattr(g, "DOOR_FOLD_LEAF_LINE_SEP_MIN_PX"))
        self.assertFalse(hasattr(g, "DOOR_FOLD_LEAF_LINE_SEP_MAX_PX"))
        self.assertEqual((DOOR_FOLD_LEAF_LINE_SEP_MIN_PX,
                          DOOR_FOLD_LEAF_LINE_SEP_MAX_PX), (0.8, 4.0))

    def test_jamb_min_length_scales(self):
        g = DoorGates.at(0.5)
        self.assertAlmostEqual(g.DOOR_FOLD_JAMB_LINE_MIN_LEN_PX, 7.5)
        self.assertAlmostEqual(g.DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX, 3.0)
