import unittest

from shapely.geometry import box

from takeoff.openings import assign_openings, opening_width_px


ROOM = box(0, 0, 300, 200)   # a 300×200 px room


class TestOpeningWidth(unittest.TestCase):
    def test_swing_door_uses_opening_line_chord(self):
        ev = {"opening_line": [[100, 200], [160, 200]]}
        w, src = opening_width_px("door", (100, 140, 160, 206), ev, ROOM)
        self.assertAlmostEqual(w, 60.0)
        self.assertEqual(src, "opening_line")

    def test_window_uses_opening_width_px(self):
        w, src = opening_width_px("window", (50, -4, 170, 4), {"opening_width_px": 118.0}, ROOM)
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
        assigned, unassigned = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(assigned, {"room_a": ["door_1"], "room_b": ["door_1"]})
        self.assertEqual(unassigned, [])

    def test_exterior_window_deducts_once(self):
        rooms = {"room_a": box(0, 0, 300, 200), "room_b": box(310, 0, 600, 200)}
        assigned, unassigned = assign_openings(rooms, [("win_1", "window", (50, -8, 170, -2))])
        self.assertEqual(assigned, {"room_a": ["win_1"]})
        self.assertEqual(unassigned, [])

    def test_free_space_opening_is_unassigned(self):
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, unassigned = assign_openings(rooms, [("door_9", "door", (900, 900, 960, 960))])
        self.assertEqual(assigned, {})
        self.assertEqual(unassigned, ["door_9"])

    def test_reach_is_seal_only(self):
        # corrected room (already +2 px); reach is 12 px more: 211 in, 213 out
        rooms = {"room_a": box(0, 0, 300, 200)}
        assigned, _ = assign_openings(rooms, [("d_in", "door", (100, 211, 160, 220))])
        self.assertEqual(assigned, {"room_a": ["d_in"]})
        assigned, unassigned = assign_openings(rooms, [("d_out", "door", (100, 213, 160, 220))])
        self.assertEqual(unassigned, ["d_out"])

    def test_room_key_order_is_stable(self):
        rooms = {"room_b": box(310, 0, 600, 200), "room_a": box(0, 0, 300, 200)}
        assigned, _ = assign_openings(rooms, [("door_1", "door", (302, 80, 308, 140))])
        self.assertEqual(list(assigned), ["room_b", "room_a"])
