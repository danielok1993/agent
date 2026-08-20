import unittest

from models import Candidate, Entity, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.document import attributes_by_room
from takeoff.heights import Heights
from takeoff.quantities import compute_takeoff

PX_PER_M_50 = 1000.0 / (25.4 / 150 * 50)     # 118.11


def _room(rid, x0, y0, x1, y1, label=None):
    poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return Entity(entity_id=rid, entity_type="room", bbox=(x0, y0, x1, y1),
                  confidence=0.9, source="heuristic", label=label,
                  attributes={"polygon": poly, "area_px2": (x1 - x0) * (y1 - y0)})


def _door(did, bbox, evidence=None):
    return (Entity(entity_id=did, entity_type="door", bbox=bbox, confidence=0.8,
                   source="heuristic", attributes={}),
            Candidate(candidate_id=did, entity_type="door", bbox=bbox,
                      confidence=0.8, evidence=evidence or {}))


HEIGHTS = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
DET50 = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")
REGION = Region(region_id="r1", bbox=(0, 0, 2000, 2000), region_type="floor_plan")
SCALES_VP = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0)})


class TestComputeTakeoff(unittest.TestCase):
    def _run(self, entities, candidates=(), page_scales=SCALES_VP, det=DET50,
             regions=(REGION,), text="", w_mm=420.0, h_mm=297.0):
        return compute_takeoff(entities, list(candidates), page_scales, list(regions),
                               det, HEIGHTS, 1, text, w_mm, h_mm)

    def test_square_room_at_1_50(self):
        # 3 m × 4 m room, drawn 2 px inside its walls (barrier standoff)
        w, h = 3 * PX_PER_M_50 - 4, 4 * PX_PER_M_50 - 4
        page = self._run([_room("room_0000", 100, 100, 100 + w, 100 + h, "BED 1")])
        r = page.rooms[0]
        self.assertEqual(r.room_id, "room_0000")
        self.assertEqual(r.label, "BED 1")
        self.assertAlmostEqual(r.floor_m2, 12.0, places=1)
        self.assertEqual(r.ceiling_m2, r.floor_m2)
        self.assertAlmostEqual(r.perimeter_m, 14.0, places=1)
        self.assertAlmostEqual(r.wall_gross_m2, 33.6, places=1)
        self.assertEqual(r.wall_net_m2, r.wall_gross_m2)
        self.assertEqual(r.height_source, "default")
        self.assertAlmostEqual(r.mm_per_px, 8.467, places=3)
        self.assertEqual(r.scale.to_dict(), {
            "denominator": 50.0, "source": "viewport", "region_id": "r1", "verified": True,
            "plausibility": {"status": "untested", "method": "door_leaves", "n": 0}})
        self.assertIn("flat_ceiling", r.assumptions)
        self.assertIn("standoff_corrected_2px", r.assumptions)
        self.assertEqual(page.unscaled_rooms, [])
        self.assertEqual(page.warnings, [])

    def test_partition_door_deducts_from_both_rooms(self):
        s = PX_PER_M_50
        a = _room("room_a", 0, 0, 3 * s, 3 * s)
        b = _room("room_b", 3 * s + 10, 0, 6 * s + 10, 3 * s)
        de, dc = _door("door_0001", (3 * s + 1, s, 3 * s + 9, s + 0.9 * s),
                       {"assembly_type": "double_swing",
                        "opening_line": [[3 * s + 5, s], [3 * s + 5, 1.9 * s]]})
        page = self._run([a, b, de], [dc])
        for r in page.rooms:
            self.assertEqual(len(r.opening_ids), 1)
            op = next(o for o in page.openings if o.opening_id == r.opening_ids[0])
            self.assertAlmostEqual(op.width_m, 0.9, places=2)
            self.assertAlmostEqual(op.area_m2, 0.9 * 2.1, places=2)
            self.assertAlmostEqual(r.wall_net_m2, r.wall_gross_m2 - 0.9 * 2.1, places=2)
        self.assertEqual(page.unassigned_openings, [])

    def test_free_space_door_is_unassigned(self):
        de, dc = _door("door_0007", (1500, 1500, 1560, 1560))
        page = self._run([_room("room_a", 0, 0, 300, 300), de], [dc])
        self.assertEqual(page.unassigned_openings, ["door_0007"])
        self.assertEqual(page.rooms[0].opening_ids, [])

    def test_no_scale_room_is_listed_not_zeroed(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=PageScales(), det=det)
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        self.assertIsNone(page.rooms[0].scale)
        self.assertIsNone(page.rooms[0].floor_m2)
        self.assertEqual(page.unscaled_rooms, ["room_a"])
        self.assertEqual([w["warning_code"] for w in page.warnings], ["TAKEOFF_NO_SCALE"])
        self.assertEqual(page.totals()["rooms_unscaled"], 1)

    def test_opening_on_unscaled_room_is_not_unassigned(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        de, dc = _door("door_0001", (100, 296, 160, 304))
        page = self._run([_room("room_a", 0, 0, 300, 300), de], [dc],
                         page_scales=PageScales(), det=det)
        self.assertEqual(page.unscaled_rooms, ["room_a"])
        self.assertEqual(page.unassigned_openings, [])
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        self.assertIsNone(page.rooms[0].floor_m2)

    def test_holes_are_filled_and_recorded(self):
        page = self._run([_room("room_a", 0, 0, 300, 300)])
        self.assertIn("holes_filled", page.rooms[0].assumptions)

    def test_text_scale_verified_by_sheet_size(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=scales,
                         text="SHEET SIZE: A3", w_mm=420.0, h_mm=297.0)
        self.assertTrue(page.rooms[0].scale.verified)
        self.assertEqual(page.warnings, [])

    def test_text_scale_unverified_warns_once(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300), _room("room_b", 400, 0, 700, 300)],
                         page_scales=scales, text="")
        self.assertFalse(page.rooms[0].scale.verified)
        self.assertEqual([w["warning_code"] for w in page.warnings], ["SCALE_UNVERIFIED"])
        self.assertEqual(page.warnings[0]["severity"], "info")
        self.assertNotIn("printed scale", page.warnings[0]["message"])
        self.assertIn("verified region source", page.warnings[0]["message"])

    def test_resized_sheet_warns(self):
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="text", nominal=50.0)})
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=scales,
                         text="SHEET SIZE: A1", w_mm=420.0, h_mm=297.0)
        codes = sorted(w["warning_code"] for w in page.warnings)
        self.assertEqual(codes, ["SCALE_PRINT_RESIZED", "SCALE_UNVERIFIED"])
        self.assertFalse(page.rooms[0].scale.verified)

    def test_opening_taller_than_ceiling_is_clamped(self):
        low = Heights(2.0, 2.1, 1.2, {"ceiling": "flag", "door": "default", "window": "default"})
        s = PX_PER_M_50
        de, dc = _door("door_0001", (s, 3 * s - 4, 1.9 * s, 3 * s + 4),
                       {"assembly_type": "double_swing",
                        "opening_line": [[s, 3 * s], [1.9 * s, 3 * s]]})
        page = compute_takeoff([_room("room_a", 0, 0, 3 * s, 3 * s), de], [dc], SCALES_VP,
                               [REGION], DET50, low, 1, "", 420.0, 297.0)
        op = page.openings[0]
        self.assertEqual(op.height_m, 2.0)
        self.assertTrue(op.clamped)
        self.assertIn("TAKEOFF_OPENING_TALLER_THAN_CEILING",
                      [w["warning_code"] for w in page.warnings])

    def test_rejected_candidate_never_deducts(self):
        # a door candidate with no matching entity (rejected by the floor)
        s = PX_PER_M_50
        _, dc = _door("door_0001", (s, 3 * s - 4, 1.9 * s, 3 * s + 4))
        page = self._run([_room("room_a", 0, 0, 3 * s, 3 * s)], [dc])
        self.assertEqual(page.rooms[0].opening_ids, [])

    def test_opening_never_serves_more_than_two_rooms(self):
        a = _room("room_a", 0, 0, 300, 200)
        b = _room("room_b", 320, 0, 600, 200)
        c = _room("room_c", 0, 210, 300, 410)
        de, dc = _door("door_0001", (302, 190, 308, 250),
                       {"assembly_type": "double_swing",
                        "opening_line": [[302, 220], [308, 220]]})
        page = self._run([a, b, c, de], [dc])
        served = [r.room_id for r in page.rooms if r.opening_ids]
        self.assertEqual(sorted(served), ["room_a", "room_c"])
        self.assertIn("TAKEOFF_OPENING_MULTI_ROOM",
                      [w["warning_code"] for w in page.warnings])
        self.assertEqual(
            [w["severity"] for w in page.warnings
             if w["warning_code"] == "TAKEOFF_OPENING_MULTI_ROOM"], ["info"])
        self.assertEqual(page.over_assigned_openings,
                         [{"id": "door_0001", "dropped_rooms": ["room_b"]}])

    def test_scale_is_picked_at_a_point_inside_the_room(self):
        # an L-shaped room: its centroid (135.7, 135.7) lies OUTSIDE both the
        # polygon and the region; the representative point (50, 250) is inside
        poly = [[0, 0], [400, 0], [400, 100], [100, 100], [100, 400], [0, 400], [0, 0]]
        room = Entity(entity_id="room_L", entity_type="room", bbox=(0, 0, 400, 400),
                      confidence=0.9, source="heuristic", label=None,
                      attributes={"polygon": poly})
        region = Region(region_id="r1", bbox=(0, 150, 110, 400), region_type="floor_plan")
        scales = PageScales(by_region={
            "r1": ScaleInfo(denominator=100.0, source="viewport", nominal=100.0)})
        page = self._run([room], page_scales=scales, regions=(region,))
        self.assertEqual((page.rooms[0].scale.denominator, page.rooms[0].scale.region_id),
                         (100.0, "r1"))

    def test_bowtie_ring_repairs_to_largest_lobe(self):
        bowtie = Entity(entity_id="room_bowtie", entity_type="room", bbox=(0, 0, 300, 300),
                        confidence=0.9, source="heuristic",
                        attributes={"polygon": [[0, 0], [300, 300], [300, 0], [0, 300], [0, 0]]})
        page = self._run([bowtie])
        self.assertEqual(len(page.rooms), 1)
        self.assertGreater(page.rooms[0].floor_m2, 0)
        # The maths runs on the repaired lobe, but the published ring is the
        # entity's own — takeoff.json overlays final_entities.json's geometry.
        self.assertEqual(page.rooms[0].polygon,
                         [[0, 0], [300, 300], [300, 0], [0, 300], [0, 0]])

    def test_a_shared_door_is_one_opening_with_two_room_ids(self):
        w = 3 * PX_PER_M_50
        left = _room("room_a", 100, 100, 100 + w, 100 + w)
        right = _room("room_b", 100 + w + 8, 100, 100 + 2 * w + 8, 100 + w)
        # A door in the party wall, touching both grown polygons.
        door, cand = _door("door_0000", (100 + w + 1, 300, 100 + w + 7, 300 + 106),
                           {"panel_length_px": 106.0})
        page = self._run([left, right, door], [cand])
        self.assertEqual(len(page.openings), 1)
        op = page.openings[0]
        self.assertEqual(op.opening_id, "door_0000")
        self.assertEqual(sorted(op.room_ids), ["room_a", "room_b"])
        self.assertEqual(op.width_source, "panel_length_px")
        self.assertAlmostEqual(op.width_m, 0.9, places=2)
        for r in page.rooms:
            self.assertEqual(r.opening_ids, ["door_0000"])

    def test_an_unassigned_opening_is_present_with_no_rooms(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0007", (5000, 5000, 5006, 5100),
                           {"panel_length_px": 106.0})
        page = self._run([room, door], [cand])
        ids = [o.opening_id for o in page.openings]
        self.assertIn("door_0007", ids)
        op = next(o for o in page.openings if o.opening_id == "door_0007")
        self.assertEqual(op.room_ids, [])
        self.assertEqual(op.width_px, 106.0)     # evidence survives
        self.assertIsNone(op.width_m)            # no room, so no scale
        self.assertIsNone(op.area_m2)
        self.assertEqual(page.rooms[0].opening_ids, [])

    def test_an_unassigned_opening_without_evidence_has_no_width(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0008", (5000, 5000, 5030, 5006), {})
        page = self._run([room, door], [cand])
        op = next(o for o in page.openings if o.opening_id == "door_0008")
        self.assertIsNone(op.width_px)
        self.assertIsNone(op.width_source)

    def test_the_opening_carries_its_tag_confidence_and_assembly_type(self):
        room = _room("room_a", 100, 100, 400, 400)
        door, cand = _door("door_0000", (100, 200, 106, 306),
                           {"panel_length_px": 106.0})
        door.label = "GD9"
        door.attributes["assembly_type"] = "sliding"
        page = self._run([room, door], [cand])
        op = page.openings[0]
        self.assertEqual(op.tag, "GD9")
        self.assertEqual(op.assembly_type, "sliding")
        self.assertEqual(op.confidence, 0.8)

    def test_a_three_room_overreach_records_the_dropped_rooms(self):
        rooms = [_room("room_a", 100, 100, 200, 200),
                 _room("room_b", 210, 100, 310, 200),
                 _room("room_c", 100, 210, 200, 310)]
        door, cand = _door("door_0000", (195, 195, 215, 215), {"panel_length_px": 20.0})
        page = self._run(rooms + [door], [cand])
        op = page.openings[0]
        self.assertEqual(len(op.room_ids), 2)
        self.assertEqual(len(op.dropped_room_ids), 1)
        self.assertNotIn(op.dropped_room_ids[0], op.room_ids)

    def test_a_room_deducts_the_area_of_each_of_its_openings(self):
        w = 3 * PX_PER_M_50
        room = _room("room_a", 100, 100, 100 + w, 100 + w)
        door, cand = _door("door_0000", (100, 200, 106, 306),
                           {"panel_length_px": 106.0})
        page = self._run([room, door], [cand])
        r = page.rooms[0]
        op = page.openings[0]
        self.assertAlmostEqual(r.wall_net_m2, r.wall_gross_m2 - op.area_m2, places=2)

    def test_a_scaled_room_still_deducts_an_opening_it_shares_with_an_unscaled_room(self):
        """room_polys holds unscaled rooms too, so the first assigned room can
        be the unscaled one. The scaled room must still lose its wall area."""
        w = 3 * PX_PER_M_50
        # The unscaled room is listed FIRST, so entity order puts it at rids[0].
        outside = _room("room_unscaled", 0, 0, 90, 90)
        inside = _room("room_scaled", 100, 100, 100 + w, 100 + w)
        door, cand = _door("door_0000", (92, 100, 98, 206), {"panel_length_px": 106.0})
        page = self._run([outside, inside, door], [cand],
                         regions=(Region(region_id="r1", bbox=(95, 95, 4000, 4000),
                                         region_type="floor_plan"),),
                         det=DetectionScale(factor=1.0, denominator=None,
                                            source="unresolved"))
        self.assertEqual(page.unscaled_rooms, ["room_unscaled"])
        op = page.openings[0]
        self.assertEqual(sorted(op.room_ids), ["room_scaled", "room_unscaled"])
        self.assertIsNotNone(op.area_m2)
        scaled = next(r for r in page.rooms if r.room_id == "room_scaled")
        self.assertAlmostEqual(scaled.wall_net_m2,
                               scaled.wall_gross_m2 - op.area_m2, places=2)

    def test_a_room_carries_its_geometry_and_confidence(self):
        w = 3 * PX_PER_M_50
        page = self._run([_room("room_0000", 100, 100, 100 + w, 100 + w, "BED 1")])
        r = page.rooms[0]
        self.assertEqual(r.confidence, 0.9)
        self.assertEqual(tuple(r.bbox), (100, 100, 100 + w, 100 + w))
        self.assertEqual(r.polygon[0], [100, 100])
        self.assertGreaterEqual(len(r.polygon), 4)

    def test_an_unscaled_room_is_kept_with_geometry_and_no_quantities(self):
        # The file's established idiom for "no scale resolves" — see
        # test_no_scale_room_is_listed_not_zeroed. Do NOT pass det=None.
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 100, 100, 400, 400)],
                         page_scales=PageScales(), det=det, regions=())
        self.assertEqual([r.room_id for r in page.rooms], ["room_a"])
        r = page.rooms[0]
        self.assertIsNone(r.scale)
        self.assertIsNone(r.floor_m2)
        self.assertIsNone(r.wall_net_m2)
        self.assertIsNone(r.mm_per_px)
        self.assertEqual(tuple(r.bbox), (100, 100, 400, 400))   # geometry survives
        self.assertGreaterEqual(len(r.polygon), 4)

    def test_totals_count_only_measured_rooms(self):
        w = 3 * PX_PER_M_50
        scaled = _room("room_a", 100, 100, 100 + w, 100 + w)
        page = self._run([scaled])
        t = page.totals()
        self.assertEqual(t["rooms_measured"], 1)
        self.assertEqual(t["rooms_unscaled"], 0)
        self.assertGreater(t["floor_m2"], 0)

    def test_an_unscaled_room_gets_no_entity_attributes_block(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 100, 100, 400, 400)],
                         page_scales=PageScales(), det=det, regions=())
        self.assertEqual(attributes_by_room(page), {})

    def test_an_unscaled_room_records_the_openings_assigned_to_it(self):
        """Referential integrity must hold in BOTH directions: if the opening
        names the room, the room must name the opening."""
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        door, cand = _door("door_0001", (100, 296, 160, 304))
        page = self._run([_room("room_a", 0, 0, 300, 300), door], [cand],
                         page_scales=PageScales(), det=det, regions=())
        self.assertEqual(page.unscaled_rooms, ["room_a"])
        room = next(r for r in page.rooms if r.room_id == "room_a")
        op = next(o for o in page.openings if o.opening_id == "door_0001")
        self.assertIn("room_a", op.room_ids)
        self.assertIn("door_0001", room.opening_ids)
