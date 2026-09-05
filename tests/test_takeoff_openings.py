import unittest

from shapely.geometry import Polygon, box

from takeoff.openings import (
    OPENING_ASSIGN_BUFFER_PX, assign_openings, opening_width_px,
    opening_width_px_from_evidence,
)

ROOM = box(0, 0, 300, 200)   # a 300×200 px room
SQUARE = Polygon([(0, 0), (200, 0), (200, 200), (0, 200)])


class TestOpeningWidth(unittest.TestCase):
    def test_single_swing_uses_arc_radius_not_the_chord(self):
        # a quarter swing: the arc endpoints are 90° apart, so the chord is
        # r·√2 (85 px) while the opening the leaf closes is r (60 px)
        ev = {"assembly_type": "single", "arc_bbox": [100, 140, 160, 200],
              "opening_line": [[100, 200], [160, 140]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "arc_radius")

    def test_single_line_leaf_without_arc_bbox_uses_leaf_line_length(self):
        ev = {"assembly_type": "single_line_leaf", "leaf_line_length_px": 58.0,
              "opening_line": [[100, 200], [141, 159]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 58.0)
        self.assertEqual(src, "leaf_line_length_px")

    def test_merged_pair_uses_opening_line_chord(self):
        ev = {"assembly_type": "double_swing", "swing_layout": "french",
              "opening_line": [[100, 200], [220, 200]]}
        w, src = opening_width_px("door", (100, 140, 220, 206), ev, ROOM)
        self.assertAlmostEqual(w, 120.0)
        self.assertEqual(src, "opening_line")

    def test_untyped_door_with_arc_bbox_is_treated_as_a_single_swing(self):
        ev = {"arc_bbox": [100, 140, 160, 200], "opening_line": [[100, 200], [160, 140]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "arc_radius")

    def test_single_with_no_arc_evidence_falls_through_to_the_chain(self):
        ev = {"assembly_type": "single", "opening_line": [[100, 200], [160, 200]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "opening_line")

    def test_window_uses_opening_width_px(self):
        w, src = opening_width_px("window", (50, -4, 170, 4), {"opening_width_px": 118.0}, ROOM)
        self.assertEqual((w, src), (118.0, "opening_width_px"))

    def test_diagonal_window_uses_glazing_length(self):
        # an angled bay face: the axis-aligned opening_width_px is the bbox
        # projection, the glazing run itself is longer
        ev = {"orientation": "diagonal", "glazing_len_px": 141.0, "opening_width_px": 100.0}
        w, src = opening_width_px("window", (50, 50, 150, 150), ev, ROOM)
        self.assertEqual((w, src), (141.0, "glazing_len_px"))

    def test_straight_window_ignores_glazing_length(self):
        ev = {"orientation": "horizontal", "glazing_len_px": 141.0, "opening_width_px": 118.0}
        w, src = opening_width_px("window", (50, -4, 170, 4), ev, ROOM)
        self.assertEqual((w, src), (118.0, "opening_width_px"))

    def test_sliding_uses_opening_span_not_bbox(self):
        # bbox is 2× the opening (parked panel)
        w, src = opening_width_px("door", (100, 195, 240, 205),
                                  {"assembly_type": "sliding", "opening_span_px": 70.0}, ROOM)
        self.assertEqual((w, src), (70.0, "opening_span_px"))

    def test_folding_falls_to_panel_length(self):
        w, src = opening_width_px("door", (100, 195, 240, 205),
                                  {"assembly_type": "folding", "panel_length_px": 35.0}, ROOM)
        self.assertEqual((w, src), (35.0, "panel_length_px"))

    def test_bbox_fallback_takes_edge_along_room_boundary(self):
        # square-ish bbox on the room's bottom wall: bottom edge (y≈200) is nearest
        w, src = opening_width_px("door", (100, 150, 160, 202), {}, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "bbox_edge")
        # tall bbox on the room's right wall: the vertical edge at x≈300 is nearest
        w, src = opening_width_px("door", (298, 50, 350, 130), {}, ROOM)
        self.assertAlmostEqual(w, 80.0)
        self.assertEqual(src, "bbox_edge")

    def test_bad_evidence_falls_through(self):
        w, src = opening_width_px("door", (100, 150, 160, 202),
                                  {"opening_line": [[0, 0]], "opening_span_px": 0}, ROOM)
        self.assertEqual(src, "bbox_edge")


class TestAssignOpenings(unittest.TestCase):
    def test_partition_door_deducts_from_both_rooms(self):
        rooms = {"room_a": box(0, 0, 300, 200), "room_b": box(310, 0, 600, 200)}
        # door bbox sits in the 10px wall between them
        assigned, unassigned, over = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(assigned, {"room_a": ["door_1"], "room_b": ["door_1"]})
        self.assertEqual(unassigned, [])
        self.assertEqual(over, [])

    def test_third_room_is_dropped_a_door_serves_two_spaces(self):
        # a door at a three-room junction: its grown reach touches all three,
        # but the farthest room boundary loses the seat
        rooms = {"room_a": box(0, 0, 300, 200),
                 "room_b": box(320, 0, 600, 200),
                 "room_c": box(0, 210, 300, 410)}
        assigned, unassigned, over = assign_openings(
            rooms, [("door_1", "door", (302, 190, 308, 250))])
        self.assertEqual(assigned, {"room_a": ["door_1"], "room_c": ["door_1"]})
        self.assertEqual(unassigned, [])
        self.assertEqual(over, [("door_1", ["room_b"])])

    def test_exterior_window_deducts_once(self):
        rooms = {"room_a": box(0, 0, 300, 200), "room_b": box(310, 0, 600, 200)}
        assigned, unassigned, over = assign_openings(rooms, [("win_1", "window", (50, -8, 170, -2))])
        self.assertEqual(assigned, {"room_a": ["win_1"]})
        self.assertEqual(unassigned, [])
        self.assertEqual(over, [])

    def test_free_space_opening_is_unassigned(self):
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, unassigned, over = assign_openings(rooms, [("door_9", "door", (900, 900, 960, 960))])
        self.assertEqual(assigned, {})
        self.assertEqual(unassigned, ["door_9"])
        self.assertEqual(over, [])

    def test_reach_is_seal_only(self):
        # corrected room (already +2 px); reach is ROOM_OPENING_SEAL_PX
        # (OPENING_ASSIGN_BUFFER_PX, 15) more: 214 in, 216 out
        reach = OPENING_ASSIGN_BUFFER_PX
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, _, over = assign_openings(rooms, [("d_in", "door", (100, 200 + reach - 1, 160, 220))])
        self.assertEqual(assigned, {"room_a": ["d_in"]})
        assigned, unassigned, over = assign_openings(rooms, [("d_out", "door", (100, 200 + reach + 1, 160, 220))])
        self.assertEqual(unassigned, ["d_out"])

    def test_room_key_order_is_stable(self):
        rooms = {"room_b": box(310, 0, 600, 200), "room_a": box(0, 0, 300, 200)}
        assigned, _, over = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(list(assigned), ["room_b", "room_a"])


class TestOpeningWidthFromEvidence(unittest.TestCase):
    """Evidence-only opening width — no room polygon needed or consulted."""

    def test_a_window_reads_its_opening_width(self):
        self.assertEqual(
            opening_width_px_from_evidence("window", {"opening_width_px": 54.5}),
            (54.5, "opening_width_px"))

    def test_a_sliding_door_reads_its_panel_length(self):
        self.assertEqual(
            opening_width_px_from_evidence("door", {"panel_length_px": 94.5}),
            (94.5, "panel_length_px"))

    def test_no_evidence_returns_none_rather_than_falling_back(self):
        self.assertIsNone(opening_width_px_from_evidence("door", {}))
        self.assertIsNone(opening_width_px_from_evidence("window", {}))

    def test_the_polygon_form_still_falls_back_to_the_bbox_edge(self):
        w, src = opening_width_px("door", (10, 10, 40, 16), {}, SQUARE)
        self.assertEqual(src, "bbox_edge")
        self.assertGreater(w, 0)

    def test_the_polygon_form_prefers_evidence_over_the_bbox(self):
        self.assertEqual(
            opening_width_px("door", (10, 10, 40, 16), {"panel_length_px": 94.5}, SQUARE),
            (94.5, "panel_length_px"))


if __name__ == "__main__":
    unittest.main()
