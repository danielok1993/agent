import unittest

from models import Region, ScaleInfo
from scale.factor import DetectionScale
from scale.resolver import PageScales
from takeoff.scale import (
    RoomScale, is_verified, select_room_scale, sheet_size_tokens,
    verify_sheet_size,
)


def _region(rid, bbox, rtype="floor_plan"):
    return Region(region_id=rid, bbox=bbox, region_type=rtype)


class TestSelectRoomScale(unittest.TestCase):
    def setUp(self):
        self.regions = [_region("r1", (0, 0, 500, 500)),
                        _region("r2", (600, 0, 1100, 500)),
                        _region("e1", (0, 600, 500, 1100), rtype="elevation")]
        self.scales = PageScales(by_region={
            "r1": ScaleInfo(denominator=50.0, source="viewport", nominal=50.0),
            "r2": ScaleInfo(denominator=99.0, source="text", nominal=100.0),
            "e1": ScaleInfo(denominator=20.0, source="text", nominal=20.0),
        })
        self.det = DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions")

    def test_room_takes_its_containing_floor_plan_region(self):
        rs = select_room_scale((100, 100), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (50.0, "viewport", "r1"))
        rs = select_room_scale((700, 100), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (100.0, "text", "r2"))

    def test_non_floor_plan_region_is_ignored(self):
        rs = select_room_scale((100, 700), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (50.0, "detection", None))

    def test_outside_every_region_falls_to_detection_scale(self):
        rs = select_room_scale((2000, 2000), self.regions, self.scales, self.det)
        self.assertEqual((rs.denominator, rs.source), (50.0, "detection"))

    def test_unresolved_region_stays_unresolved_never_borrows_detection_scale(self):
        # mixed-scale page: det_scale is the OTHER plan's scale
        scales = PageScales(by_region={"r1": ScaleInfo(denominator=None, source="unresolved"),
                                       "r2": ScaleInfo(denominator=100.0, source="text", nominal=100.0)})
        det = DetectionScale(factor=0.5, denominator=100.0, source="floor_plan_regions")
        rs = select_room_scale((100, 100), self.regions, scales, det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (None, "unresolved", "r1"))

    def test_region_with_no_entry_falls_to_detection_scale(self):
        rs = select_room_scale((100, 100), self.regions, PageScales(), self.det)
        self.assertEqual((rs.denominator, rs.source), (50.0, "detection"))

    def test_nothing_resolves_to_none(self):
        det = DetectionScale(factor=1.0, denominator=None, source="unresolved")
        rs = select_room_scale((2000, 2000), self.regions, PageScales(), det)
        self.assertEqual((rs.denominator, rs.source, rs.region_id), (None, "unresolved", None))
        rs = select_room_scale((2000, 2000), self.regions, PageScales(), None)
        self.assertIsNone(rs.denominator)

    def test_to_dict(self):
        d = RoomScale(50.0, "viewport", "r1", True).to_dict()
        self.assertEqual(d, {"denominator": 50.0, "source": "viewport",
                             "region_id": "r1", "verified": True})


class TestSheetSize(unittest.TestCase):
    def test_tokens_need_a_declaration_context(self):
        self.assertEqual(sheet_size_tokens("SHEET SIZE: A1  DWG A101 CAT5"), {"A1"})
        self.assertEqual(sheet_size_tokens("scale 1:50 @ A3"), {"A3"})
        self.assertEqual(sheet_size_tokens("1:50@A3"), {"A3"})
        self.assertEqual(sheet_size_tokens("As Shown @ A1"), {"A1"})
        self.assertEqual(sheet_size_tokens("SHEET SIZE: A3"), {"A3"})
        self.assertEqual(sheet_size_tokens("PAPER A2"), {"A2"})
        self.assertEqual(sheet_size_tokens("ORIGINAL FORMAT - A0"), {"A0"})
        self.assertEqual(sheet_size_tokens("nothing"), set())

    def test_bare_tokens_are_not_a_sheet_size(self):
        # s20: the sheet size lives inside a drawing number
        self.assertEqual(sheet_size_tokens("18-069-001(A1).A"), set())
        self.assertEqual(sheet_size_tokens("DWG A101 CAT5"), set())
        self.assertEqual(sheet_size_tokens("REV A3 ISSUED"), set())
        self.assertEqual(sheet_size_tokens(""), set())
        self.assertEqual(sheet_size_tokens(None), set())

    def test_matching_size_either_orientation(self):
        self.assertEqual(verify_sheet_size({"A3"}, 420.0, 297.0), (True, False))
        self.assertEqual(verify_sheet_size({"A3"}, 297.0, 420.0), (True, False))
        self.assertEqual(verify_sheet_size({"A1"}, 841.0, 594.0), (True, False))

    def test_half_size_print_is_resized(self):
        # A1 drawing printed half-size on A3 paper (two A-steps): both sides ~halved
        self.assertEqual(verify_sheet_size({"A1"}, 420.0, 297.0), (False, True))
        # A3 drawing blown up to A1
        self.assertEqual(verify_sheet_size({"A3"}, 841.0, 594.0), (False, True))

    def test_no_tokens_or_unrelated_size(self):
        self.assertEqual(verify_sheet_size(set(), 420.0, 297.0), (False, False))
        self.assertEqual(verify_sheet_size({"A0"}, 420.0, 297.0), (False, False))

    def test_is_verified(self):
        self.assertTrue(is_verified(RoomScale(50.0, "viewport", "r1", False), False))
        self.assertTrue(is_verified(RoomScale(50.0, "user", "r1", False), False))
        self.assertTrue(is_verified(RoomScale(50.0, "text", "r1", False), True))
        self.assertFalse(is_verified(RoomScale(50.0, "text", "r1", False), False))
        self.assertFalse(is_verified(RoomScale(50.0, "detection", None, False), True))


class TestScaleSummaryDict(unittest.TestCase):
    def test_page_and_region_scales_serialise(self):
        from models import ScaleInfo
        from scale.factor import DetectionScale
        from scale.resolver import PageScales, scale_summary_dict

        info = ScaleInfo(denominator=50.0, source="text", nominal=50.0)
        out = scale_summary_dict(
            PageScales(by_region={"region_0000": info}, page_scale=info),
            DetectionScale(factor=1.0, denominator=50.0, source="floor_plan_regions"),
        )
        self.assertEqual(out["by_region"]["region_0000"]["denominator"], 50.0)
        self.assertEqual(out["page_scale"]["source"], "text")
        self.assertEqual(out["detection"]["factor"], 1.0)

    def test_no_detection_scale_omits_the_block(self):
        from scale.resolver import PageScales, scale_summary_dict
        out = scale_summary_dict(PageScales())
        self.assertNotIn("detection", out)
        self.assertIsNone(out["page_scale"])
        self.assertEqual(out["by_region"], {})
