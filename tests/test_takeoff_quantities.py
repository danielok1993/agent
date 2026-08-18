import unittest

from models import Candidate, Entity, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
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
        self.assertEqual(r.scale.to_dict(), {"denominator": 50.0, "source": "viewport",
                                             "region_id": "r1", "verified": True})
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
            self.assertEqual(len(r.openings), 1)
            self.assertAlmostEqual(r.openings[0]["width_m"], 0.9, places=2)
            self.assertAlmostEqual(r.openings[0]["area_m2"], 0.9 * 2.1, places=2)
            self.assertAlmostEqual(r.wall_net_m2, r.wall_gross_m2 - 0.9 * 2.1, places=2)
        self.assertEqual(page.unassigned_openings, [])

    def test_free_space_door_is_unassigned(self):
        de, dc = _door("door_0007", (1500, 1500, 1560, 1560))
        page = self._run([_room("room_a", 0, 0, 300, 300), de], [dc])
        self.assertEqual(page.unassigned_openings, ["door_0007"])
        self.assertEqual(page.rooms[0].openings, [])

    def test_no_scale_room_is_listed_not_zeroed(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = self._run([_room("room_a", 0, 0, 300, 300)], page_scales=PageScales(), det=det)
        self.assertEqual(page.rooms, [])
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
        self.assertEqual(page.rooms, [])

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
        op = page.rooms[0].openings[0]
        self.assertEqual(op["height_m"], 2.0)
        self.assertTrue(op["clamped"])
        self.assertIn("TAKEOFF_OPENING_TALLER_THAN_CEILING",
                      [w["warning_code"] for w in page.warnings])

    def test_rejected_candidate_never_deducts(self):
        # a door candidate with no matching entity (rejected by the floor)
        s = PX_PER_M_50
        _, dc = _door("door_0001", (s, 3 * s - 4, 1.9 * s, 3 * s + 4))
        page = self._run([_room("room_a", 0, 0, 3 * s, 3 * s)], [dc])
        self.assertEqual(page.rooms[0].openings, [])

    def test_to_dict_and_attributes(self):
        page = self._run([_room("room_a", 0, 0, 300, 300, "HALL")])
        d = page.to_dict()
        self.assertEqual(set(d), {"page_number", "heights", "rooms", "unassigned_openings",
                                  "over_assigned_openings", "unscaled_rooms", "totals"})
        room = d["rooms"][0]
        for k in ("room_id", "label", "scale", "mm_per_px", "floor_m2", "ceiling_m2",
                  "perimeter_m", "height_m", "height_source", "wall_gross_m2",
                  "openings", "wall_net_m2", "assumptions"):
            self.assertIn(k, room)
        self.assertEqual(room["floor_m2"], round(room["floor_m2"], 2))
        attrs = page.attributes_by_room()["room_a"]
        self.assertNotIn("room_id", attrs)
        self.assertIn("floor_m2", attrs)
        self.assertEqual(d["totals"]["rooms_measured"], 1)

    def test_opening_never_serves_more_than_two_rooms(self):
        a = _room("room_a", 0, 0, 300, 200)
        b = _room("room_b", 320, 0, 600, 200)
        c = _room("room_c", 0, 210, 300, 410)
        de, dc = _door("door_0001", (302, 190, 308, 250),
                       {"assembly_type": "double_swing",
                        "opening_line": [[302, 220], [308, 220]]})
        page = self._run([a, b, c, de], [dc])
        served = [r.room_id for r in page.rooms if r.openings]
        self.assertEqual(sorted(served), ["room_a", "room_c"])
        self.assertIn("TAKEOFF_OPENING_MULTI_ROOM",
                      [w["warning_code"] for w in page.warnings])
        self.assertEqual(
            [w["severity"] for w in page.warnings
             if w["warning_code"] == "TAKEOFF_OPENING_MULTI_ROOM"], ["info"])
        self.assertEqual(page.over_assigned_openings,
                         [{"id": "door_0001", "dropped_rooms": ["room_b"]}])
        self.assertEqual(page.to_dict()["over_assigned_openings"],
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
