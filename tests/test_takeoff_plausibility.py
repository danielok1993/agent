import unittest

from takeoff.plausibility import (
    LEAF_MAX_M, LEAF_MIN_M, check_door_leaves, leaf_width_px,
)

PX_PER_M_50 = 1000.0 / (25.4 / 150 * 50)     # 118.11 px per metre at 1:50


class TestLeafWidth(unittest.TestCase):
    def test_single_swing_uses_arc_radius(self):
        ev = {"assembly_type": "single", "arc_bbox": (0, 0, 90, 90),
              "opening_line": [(0, 0), (90, 90)]}
        self.assertAlmostEqual(leaf_width_px(ev), 90.0)

    def test_double_swing_halves_the_opening_line(self):
        ev = {"assembly_type": "double_swing", "opening_line": [(0, 0), (200, 0)]}
        self.assertAlmostEqual(leaf_width_px(ev), 100.0)

    def test_sliding_and_folding_use_panel_length(self):
        self.assertAlmostEqual(leaf_width_px({"assembly_type": "sliding", "panel_length_px": 95.0,
                                              "opening_span_px": 190.0}), 95.0)
        self.assertAlmostEqual(leaf_width_px({"assembly_type": "folding", "panel_length_px": 40.0,
                                              "leaf_count": 4, "opening_span_px": 160.0}), 40.0)

    def test_bbox_only_door_gives_nothing(self):
        self.assertIsNone(leaf_width_px({}))
        self.assertIsNone(leaf_width_px({"assembly_type": "single"}))


class TestCheckDoorLeaves(unittest.TestCase):
    def test_band_constants(self):
        self.assertEqual((LEAF_MIN_M, LEAF_MAX_M), (0.55, 1.20))

    def test_normal_leaves_are_ok(self):
        leaves = [0.76 * PX_PER_M_50, 0.84 * PX_PER_M_50, 0.90 * PX_PER_M_50]
        v = check_door_leaves(leaves, 50.0)
        self.assertEqual(v.status, "ok")
        self.assertEqual(v.method, "door_leaves")
        self.assertEqual(v.n, 3)
        self.assertAlmostEqual(v.median_m, 0.84, places=2)

    def test_fewer_than_two_doors_is_untested(self):
        v = check_door_leaves([0.80 * PX_PER_M_50], 50.0)
        self.assertEqual(v.status, "untested")
        self.assertEqual(v.n, 1)

    def test_half_size_leaves_flag_and_imply_double_denominator(self):
        # s01: median leaf 0.38 m at 1:50 — really a 1:100 drawing
        leaves = [0.36 * PX_PER_M_50, 0.38 * PX_PER_M_50, 0.42 * PX_PER_M_50]
        v = check_door_leaves(leaves, 50.0)
        self.assertEqual(v.status, "implausible")
        self.assertEqual(v.implied_denominator, 100.0)

    def test_double_size_leaves_imply_half_denominator(self):
        leaves = [1.6 * PX_PER_M_50, 1.7 * PX_PER_M_50]
        v = check_door_leaves(leaves, 50.0)
        self.assertEqual(v.status, "implausible")
        self.assertEqual(v.implied_denominator, 25.0)

    def test_quarter_size_leaves_imply_four_times(self):
        leaves = [0.19 * PX_PER_M_50, 0.21 * PX_PER_M_50]
        v = check_door_leaves(leaves, 50.0)
        self.assertEqual(v.implied_denominator, 200.0)

    def test_median_resists_one_garage_door(self):
        leaves = [0.8 * PX_PER_M_50, 0.85 * PX_PER_M_50, 2.4 * PX_PER_M_50]
        self.assertEqual(check_door_leaves(leaves, 50.0).status, "ok")


if __name__ == "__main__":
    unittest.main()


from models import PathPrimitive, TextSpan
from takeoff.plausibility import (
    DIM_MIN_MATCHES, check_dimensions, dimension_matches, parse_dimension_mm,
)


def _line(idx, a, b, width=1.0, color=(0, 0, 1)):
    return PathPrimitive(path_index=idx, item_type="l",
                         bbox=(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])),
                         color=color, fill=None, stroke_width=width, dashes="[] 0",
                         layer=None, points=[a, b])


def _span(text, bbox):
    return TextSpan(text=text, bbox=bbox, font="Arial", size=9.0, color=0, block_no=0, line_no=0)


def _dim_chain(idx0, y, x0, x1, label, text_dy=-12):
    """A ticked dimension line from x0 to x1 with its label centred above."""
    paths = [_line(idx0, (x0, y), (x1, y)),
             _line(idx0 + 1, (x0 - 4, y + 4), (x0 + 4, y - 4)),
             _line(idx0 + 2, (x1 - 4, y + 4), (x1 + 4, y - 4))]
    cx = (x0 + x1) / 2.0
    span = _span(label, (cx - 16, y + text_dy - 7, cx + 16, y + text_dy + 7))
    return paths, span


class TestParseDimension(unittest.TestCase):
    def test_millimetre_forms(self):
        self.assertEqual(parse_dimension_mm("3600"), 3600.0)
        self.assertEqual(parse_dimension_mm("7,434"), 7434.0)
        self.assertEqual(parse_dimension_mm(" 300 "), 300.0)

    def test_metre_form(self):
        self.assertEqual(parse_dimension_mm("4.50"), 4500.0)
        self.assertEqual(parse_dimension_mm("0.9"), 900.0)

    def test_rejects_non_dimensions(self):
        for t in ("S1520", "1133-WD03", "20", "1:50", "July 2024", "", "3600mm"):
            self.assertIsNone(parse_dimension_mm(t), t)


class TestDimensionMatches(unittest.TestCase):
    def test_label_beside_ticked_line_gives_implied_denominator(self):
        # 3600 mm drawn 425.2 px long: 3600 / (425.2 × 0.16933) = 50.0
        paths, span = _dim_chain(0, 100, 100, 525.2, "3600")
        m = dimension_matches(paths, [span])
        self.assertEqual(len(m), 1)
        self.assertAlmostEqual(m[0].value_mm, 3600.0)
        self.assertAlmostEqual(m[0].length_px, 425.2)
        self.assertAlmostEqual(m[0].implied_denominator, 50.0, places=1)

    def test_match_records_the_line_and_label_for_debugging(self):
        paths, span = _dim_chain(7, 100, 100, 525.2, "3600")
        m = dimension_matches(paths, [span])[0]
        self.assertEqual(m.path_index, 7)
        self.assertEqual(m.label, "3600")
        self.assertEqual(m.label_bbox, span.bbox)
        self.assertEqual(m.line, ((100.0, 100.0), (525.2, 100.0)))
        d = m.to_dict()
        self.assertEqual((d["path_index"], d["label"]), (7, "3600"))
        self.assertEqual(d["line"], [[100.0, 100.0], [525.2, 100.0]])

    def test_unticked_line_is_not_a_dimension(self):
        paths, span = _dim_chain(0, 100, 100, 525.2, "3600")
        self.assertEqual(dimension_matches(paths[:1], [span]), [])

    def test_label_far_from_the_line_is_not_its_label(self):
        paths, _ = _dim_chain(0, 100, 100, 525.2, "3600")
        far = _span("3600", (296, 30, 328, 44))     # 63 px above the line
        self.assertEqual(dimension_matches(paths, [far]), [])

    def test_label_wider_than_a_short_line_is_not_its_label(self):
        # a 20 px stub with "12,000" beside it: the text belongs to a longer run
        paths, _ = _dim_chain(0, 100, 100, 120, "x")
        wide = _span("12,000", (85, 81, 135, 95))
        self.assertEqual(dimension_matches(paths, [wide]), [])

    def test_each_label_used_once_nearest_line_wins(self):
        a, sa = _dim_chain(0, 100, 100, 525.2, "3600")
        b, sb = _dim_chain(10, 140, 100, 525.2, "3600")
        m = dimension_matches(a + b, [sa, sb])
        self.assertEqual(len(m), 2)


class TestCheckDimensions(unittest.TestCase):
    def _m(self, implied, n=3):
        from takeoff.plausibility import DimensionMatch
        return [DimensionMatch(value_mm=1000.0, length_px=1000.0 / (implied * 25.4 / 150),
                               implied_denominator=implied) for _ in range(n)]

    def test_needs_three_matches(self):
        self.assertEqual(DIM_MIN_MATCHES, 3)
        self.assertEqual(check_dimensions(self._m(50.0, n=2), 50.0).status, "untested")

    def test_agreement_is_ok(self):
        v = check_dimensions(self._m(50.6), 50.0)
        self.assertEqual((v.status, v.method, v.n), ("ok", "dimensions", 3))
        self.assertAlmostEqual(v.implied_denominator, 50.6, places=1)

    def test_print_factor_disagreement_is_implausible(self):
        v = check_dimensions(self._m(92.2), 50.0)      # s01
        self.assertEqual(v.status, "implausible")
        self.assertAlmostEqual(v.implied_denominator, 92.2, places=1)

    def test_small_disagreement_is_inconclusive(self):
        self.assertEqual(check_dimensions(self._m(54.0), 50.0).status, "inconclusive")


from models import Candidate, Entity, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.document import to_document
from takeoff.heights import Heights
from takeoff.quantities import compute_takeoff

HEIGHTS = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
DET50 = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")
REGION = Region(region_id="r1", bbox=(0, 0, 3000, 3000), region_type="floor_plan")
SCALES_USER = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="user", nominal=50.0)})
SCALES_TEXT = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})


def _room(rid, x0, y0, x1, y1):
    poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return Entity(entity_id=rid, entity_type="room", bbox=(x0, y0, x1, y1), confidence=0.9,
                  source="heuristic", attributes={"polygon": poly})


def _swing(did, x, y, r):
    """A single swing hinged at (x, y) on a room's top wall, radius r px."""
    bbox = (x, y, x + r, y + r)
    ev = {"assembly_type": "single", "arc_bbox": bbox}
    return (Entity(entity_id=did, entity_type="door", bbox=bbox, confidence=0.8,
                   source="heuristic", attributes={}),
            Candidate(candidate_id=did, entity_type="door", bbox=bbox, confidence=0.8, evidence=ev))


class TestTakeoffPlausibility(unittest.TestCase):
    def _run(self, scales, doors_r_px, paths=(), spans=()):
        room = _room("room_0000", 100, 100, 700, 700)
        ents, cands = [room], []
        for i, r in enumerate(doors_r_px):
            e, c = _swing(f"door_{i:04d}", 120 + i * 150, 100, r)
            ents.append(e)
            cands.append(c)
        return compute_takeoff(ents, cands, scales, [REGION], DET50, HEIGHTS, 1, "", 420, 297,
                               paths=list(paths), text_spans=list(spans))

    def test_normal_doors_keep_user_scale_verified(self):
        page = self._run(SCALES_USER, [0.8 * PX_PER_M_50, 0.9 * PX_PER_M_50])
        sc = page.rooms[0].scale
        self.assertTrue(sc.verified)
        self.assertEqual(sc.to_dict()["plausibility"]["status"], "ok")
        self.assertEqual(sc.to_dict()["plausibility"]["method"], "door_leaves")
        self.assertEqual([w["warning_code"] for w in page.warnings], [])

    def test_half_size_doors_unverify_even_a_typed_scale(self):
        page = self._run(SCALES_USER, [0.38 * PX_PER_M_50, 0.40 * PX_PER_M_50])
        sc = page.rooms[0].scale
        self.assertFalse(sc.verified)
        self.assertEqual(sc.denominator, 50.0)            # no silent swap
        pl = sc.to_dict()["plausibility"]
        self.assertEqual((pl["status"], pl["implied_denominator"]), ("implausible", 100.0))
        codes = [w["warning_code"] for w in page.warnings]
        self.assertIn("SCALE_IMPLAUSIBLE", codes)
        self.assertNotIn("SCALE_UNVERIFIED", codes)       # the stronger warning supersedes
        msg = next(w["message"] for w in page.warnings if w["warning_code"] == "SCALE_IMPLAUSIBLE")
        self.assertIn("1:100", msg)

    def test_one_door_is_untested_and_leaves_verification_alone(self):
        page = self._run(SCALES_TEXT, [0.38 * PX_PER_M_50])
        sc = page.rooms[0].scale
        self.assertFalse(sc.verified)
        self.assertEqual(sc.to_dict()["plausibility"]["status"], "untested")
        self.assertEqual([w["warning_code"] for w in page.warnings], ["SCALE_UNVERIFIED"])

    def test_agreeing_dimensions_verify_a_text_scale_and_outrank_doors(self):
        paths, spans = [], []
        for i in range(3):
            p, s = _dim_chain(100 + i * 10, 900 + i * 40, 100, 525.2, "3600")   # 1:50
            paths += p
            spans.append(s)
        page = self._run(SCALES_TEXT, [0.38 * PX_PER_M_50, 0.40 * PX_PER_M_50], paths, spans)
        sc = page.rooms[0].scale
        self.assertTrue(sc.verified)
        pl = sc.to_dict()["plausibility"]
        self.assertEqual((pl["status"], pl["method"], pl["n"]), ("ok", "dimensions", 3))
        self.assertEqual([w["warning_code"] for w in page.warnings], [])

    def test_precomputed_dimension_matches_are_used_verbatim(self):
        # run_extract matches the page once (for the gates) and passes the
        # list in; compute_takeoff must use it rather than re-matching —
        # here there are no paths at all, so a re-match would find nothing.
        from takeoff.plausibility import DimensionMatch
        matches = [DimensionMatch(value_mm=3600.0, length_px=525.2,
                                  implied_denominator=50.0)] * 3
        room = _room("room_0000", 100, 100, 700, 700)
        e, c = _swing("door_0000", 120, 100, 0.38 * PX_PER_M_50)
        e2, c2 = _swing("door_0001", 270, 100, 0.40 * PX_PER_M_50)
        page = compute_takeoff([room, e, e2], [c, c2], SCALES_TEXT, [REGION], DET50,
                               HEIGHTS, 1, "", 420, 297, dimension_matches=matches)
        self.assertIs(page.dimension_matches, matches)
        pl = page.rooms[0].scale.to_dict()["plausibility"]
        self.assertEqual((pl["status"], pl["method"], pl["n"]), ("ok", "dimensions", 3))

    def test_inconclusive_dimensions_are_not_overruled_by_doors(self):
        # s01 at the user's 1:100: 31 dimensions measure 1:92.2 (7.8% off) —
        # that stays the verdict, with the implied value visible; the coarser
        # door band must not stamp it "ok"
        paths, spans = [], []
        for i in range(3):
            p, s = _dim_chain(100 + i * 10, 900 + i * 40, 100, 560.0, "3600")   # 1:46.2
            paths += p
            spans.append(s)
        page = self._run(SCALES_USER, [0.8 * PX_PER_M_50, 0.9 * PX_PER_M_50], paths, spans)
        sc = page.rooms[0].scale
        pl = sc.to_dict()["plausibility"]
        self.assertEqual((pl["status"], pl["method"], pl["n"]), ("inconclusive", "dimensions", 3))
        self.assertAlmostEqual(pl["implied_denominator"], 46.2, places=1)
        self.assertTrue(sc.verified)            # source-level trust stands
        self.assertEqual([w["warning_code"] for w in page.warnings], [])

    def test_dimension_evidence_is_written_per_page(self):
        paths, spans = [], []
        for i in range(3):
            p, s = _dim_chain(100 + i * 10, 900 + i * 40, 100, 525.2, "3600")
            paths += p
            spans.append(s)
        page = self._run(SCALES_TEXT, [], paths, spans)
        ev = to_document(page)["scale"]["evidence"]
        self.assertEqual(len(ev["dimensions"]), 3)
        self.assertEqual(ev["dimensions"][0]["label"], "3600")
        self.assertEqual(ev["dimensions"][0]["path_index"], 100)
        self.assertEqual(ev["verdicts"], {"50": {"status": "ok", "method": "dimensions", "n": 3,
                                                 "implied_denominator": 50.0}})

    def test_no_dimensions_still_writes_empty_evidence(self):
        page = self._run(SCALES_TEXT, [0.8 * PX_PER_M_50, 0.9 * PX_PER_M_50])
        ev = to_document(page)["scale"]["evidence"]
        self.assertEqual(ev["dimensions"], [])
        self.assertEqual(ev["verdicts"]["50"]["method"], "door_leaves")

    def test_contradicting_dimensions_unverify_a_typed_scale(self):
        paths, spans = [], []
        for i in range(3):
            p, s = _dim_chain(100 + i * 10, 900 + i * 40, 100, 325.2, "3600")   # 1:94.4
            paths += p
            spans.append(s)
        page = self._run(SCALES_USER, [0.8 * PX_PER_M_50, 0.9 * PX_PER_M_50], paths, spans)
        sc = page.rooms[0].scale
        self.assertFalse(sc.verified)
        self.assertEqual(sc.denominator, 50.0)
        pl = sc.to_dict()["plausibility"]
        self.assertEqual((pl["status"], pl["method"]), ("implausible", "dimensions"))
        self.assertAlmostEqual(pl["implied_denominator"], 94.4, places=1)
        self.assertIn("SCALE_IMPLAUSIBLE", [w["warning_code"] for w in page.warnings])
