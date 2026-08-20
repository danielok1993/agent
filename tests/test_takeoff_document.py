"""The takeoff.json document (takeoff/document.py)."""
import unittest

from models import Entity, Candidate, Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.document import SCHEMA_VERSION, to_document
from takeoff.heights import Heights
from takeoff.quantities import TakeoffPage, compute_takeoff

PX_PER_M_50 = 1000.0 / (25.4 / 150 * 50)
HEIGHTS = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
DET50 = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")
REGION = Region(region_id="r1", bbox=(0, 0, 4000, 4000), region_type="floor_plan")
SCALES = PageScales(by_region={"r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0)})


def _room(rid, x0, y0, x1, y1, label=None):
    poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return Entity(entity_id=rid, entity_type="room", bbox=(x0, y0, x1, y1),
                  confidence=0.9, source="heuristic", label=label,
                  attributes={"polygon": poly})


def _door(did, bbox, evidence=None):
    return (Entity(entity_id=did, entity_type="door", bbox=bbox, confidence=0.8,
                   source="heuristic", attributes={}),
            Candidate(candidate_id=did, entity_type="door", bbox=bbox,
                      confidence=0.8, evidence=evidence or {}))


def _page(entities, candidates=()):
    return compute_takeoff(entities, list(candidates), SCALES, [REGION], DET50,
                           HEIGHTS, 1, "", 420.0, 297.0,
                           page_width_px=2480.3, page_height_px=1753.9, page_rotation=0)


class TestDocumentShape(unittest.TestCase):
    def test_top_level_keys(self):
        d = to_document(_page([_room("room_a", 100, 100, 500, 500)]))
        self.assertEqual(set(d), {
            "schema_version", "page_number", "page_frame", "scale", "heights",
            "rooms", "openings", "totals", "warnings"})
        self.assertEqual(d["schema_version"], SCHEMA_VERSION)

    def test_page_frame_records_the_pixel_space(self):
        f = to_document(_page([_room("room_a", 100, 100, 500, 500)]))["page_frame"]
        self.assertEqual(f["width_px"], 2480.3)
        self.assertEqual(f["height_px"], 1753.9)
        self.assertEqual(f["dpi"], 150)
        self.assertEqual(f["origin"], "top-left")
        self.assertEqual(f["y_axis"], "down")
        self.assertEqual(f["rotation"], 0)
        self.assertAlmostEqual(f["pdf_width_pt"], 2480.3 * 72 / 150, places=1)
        self.assertAlmostEqual(f["pdf_height_pt"], 1753.9 * 72 / 150, places=1)

    def test_a_room_carries_geometry_and_grouped_quantities(self):
        w = 3 * PX_PER_M_50
        r = to_document(_page([_room("room_a", 100, 100, 100 + w, 100 + w, "Kitchen")]))["rooms"][0]
        self.assertEqual(r["room_id"], "room_a")
        self.assertEqual(r["label"], "Kitchen")
        self.assertEqual(r["confidence"], 0.9)
        self.assertEqual(len(r["bbox"]), 4)
        self.assertGreaterEqual(len(r["polygon"]), 4)
        self.assertEqual(r["opening_ids"], [])
        self.assertIn("floor_m2", r["quantities"])
        self.assertIn("wall_net_m2", r["quantities"])
        self.assertNotIn("floor_m2", r)          # grouped, not flat

    def test_an_unscaled_room_serialises_null_scale_and_null_quantities(self):
        unresolved = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        page = compute_takeoff([_room("room_a", 100, 100, 500, 500)], [], PageScales(),
                               [], unresolved, HEIGHTS, 1, "", 420.0, 297.0,
                               page_width_px=100.0, page_height_px=100.0)
        r = to_document(page)["rooms"][0]
        self.assertIsNone(r["scale"])
        self.assertIsNone(r["quantities"])
        self.assertGreaterEqual(len(r["polygon"]), 4)

    def test_the_scale_block_carries_page_region_and_evidence(self):
        page_scales = PageScales(
            by_region={"r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0)},
            page_scale=ScaleInfo(denominator=50.0, source="text", nominal=50.0))
        page = compute_takeoff([_room("room_a", 100, 100, 500, 500)], [], page_scales,
                               [REGION], DET50, HEIGHTS, 1, "", 420.0, 297.0,
                               page_width_px=2480.3, page_height_px=1753.9)
        s = to_document(page)["scale"]
        self.assertEqual(set(s), {"page", "by_region", "detection", "evidence"})
        self.assertEqual(s["page"]["source"], "text")          # survived the rename
        self.assertEqual(s["by_region"]["r1"]["denominator"], 50.0)
        self.assertEqual(set(s["evidence"]), {"dimensions", "verdicts"})

    def test_scale_keys_are_stable_for_a_page_not_built_by_compute_takeoff(self):
        # A bare TakeoffPage (e.g. built directly in a test, or any future
        # caller that skips compute_takeoff) leaves scale_block at its {}
        # default. The document must still carry a `by_region` key rather
        # than omitting it — a frontend reading doc.scale.by_region should
        # never see undefined.
        page = TakeoffPage(page_number=1, heights=HEIGHTS)
        s = to_document(page)["scale"]
        self.assertGreaterEqual(set(s), {"page", "by_region", "evidence"})
        self.assertEqual(s["by_region"], {})


class TestReferentialIntegrity(unittest.TestCase):
    def _doc(self):
        w = 3 * PX_PER_M_50
        left = _room("room_a", 100, 100, 100 + w, 100 + w)
        right = _room("room_b", 100 + w + 8, 100, 100 + 2 * w + 8, 100 + w)
        door, cand = _door("door_0000", (100 + w + 1, 300, 100 + w + 7, 300 + 106),
                           {"panel_length_px": 106.0})
        return to_document(_page([left, right, door], [cand]))

    def test_every_opening_id_on_a_room_resolves_to_an_opening(self):
        d = self._doc()
        by_id = {o["opening_id"] for o in d["openings"]}
        seen = 0
        for room in d["rooms"]:
            for oid in room["opening_ids"]:
                self.assertIn(oid, by_id)
                seen += 1
        # Both rooms must name the shared door, or this test proves nothing.
        self.assertEqual(seen, 2)

    def test_every_room_id_on_an_opening_resolves_and_points_back(self):
        d = self._doc()
        rooms = {r["room_id"]: r for r in d["rooms"]}
        op = d["openings"][0]
        self.assertEqual(sorted(op["room_ids"]), ["room_a", "room_b"])
        for rid in op["room_ids"]:
            self.assertIn(rid, rooms)
            self.assertIn(op["opening_id"], rooms[rid]["opening_ids"])

    def test_a_shared_opening_appears_exactly_once(self):
        d = self._doc()
        ids = [o["opening_id"] for o in d["openings"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 1)


if __name__ == "__main__":
    unittest.main()
