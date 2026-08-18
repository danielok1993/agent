import unittest
from unittest import mock

from models import Entity
from pipeline import _page_summary_dict, attach_takeoff
from takeoff.heights import Heights
from takeoff.quantities import RoomTakeoff, TakeoffPage
from takeoff.scale import RoomScale


def _page():
    h = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
    page = TakeoffPage(page_number=1, heights=h)
    page.rooms.append(RoomTakeoff(
        room_id="room_0000", label="HALL", scale=RoomScale(50.0, "viewport", "r1", True),
        mm_per_px=8.467, floor_m2=5.5, ceiling_m2=5.5, perimeter_m=9.4, height_m=2.4,
        height_source="default", wall_gross_m2=22.56, openings=[], wall_net_m2=22.56,
        assumptions=["flat_ceiling"]))
    return page


class TestAttachTakeoff(unittest.TestCase):
    def test_room_entity_gets_takeoff_block(self):
        room = Entity(entity_id="room_0000", entity_type="room", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={"polygon": []})
        door = Entity(entity_id="door_0000", entity_type="door", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={})
        attach_takeoff([room, door], _page())
        self.assertEqual(room.attributes["takeoff"]["floor_m2"], 5.5)
        self.assertNotIn("room_id", room.attributes["takeoff"])
        self.assertNotIn("takeoff", door.attributes)

    def test_unscaled_room_gets_no_block(self):
        room = Entity(entity_id="room_0009", entity_type="room", bbox=(0, 0, 1, 1),
                      confidence=0.9, source="heuristic", attributes={"polygon": []})
        attach_takeoff([room], _page())
        self.assertNotIn("takeoff", room.attributes)


class TestSummaryTotals(unittest.TestCase):
    def test_page_summary_carries_takeoff_totals(self):
        page_data = mock.Mock(page_number=1, page_type="vector", width_px=1000.0,
                              height_px=800.0, paths=[], text_spans=[], images=[])
        from scale.resolver import PageScales
        d = _page_summary_dict(page_data, [], [], [], [], PageScales(), None, takeoff=_page())
        self.assertEqual(d["takeoff"]["rooms_measured"], 1)
        self.assertEqual(d["takeoff"]["floor_m2"], 5.5)

    def test_page_summary_without_takeoff(self):
        page_data = mock.Mock(page_number=1, page_type="vector", width_px=1000.0,
                              height_px=800.0, paths=[], text_spans=[], images=[])
        from scale.resolver import PageScales
        d = _page_summary_dict(page_data, [], [], [], [], PageScales(), None)
        self.assertNotIn("takeoff", d)


class TestRunExtractWiring(unittest.TestCase):
    """End-to-end through run_extract on a synthetic 2-page PDF, with
    compute_takeoff mocked so the assertions are about WIRING (called per
    page, takeoff.json written, warnings reach warnings.json, root totals
    aggregate) and never about detection."""

    def _pdf(self, path):
        import fitz
        doc = fitz.open()
        for _ in range(2):
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(100, 100, 300, 250), color=(0, 0, 0), width=1.5)
            page.insert_text((110, 120), "HALL", fontsize=8)
        doc.save(path)
        doc.close()

    def _canned(self, page_number, floor):
        h = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default", "window": "default"})
        page = TakeoffPage(page_number=page_number, heights=h)
        page.rooms.append(RoomTakeoff(
            room_id="room_0000", label=None, scale=RoomScale(50.0, "text", "r1", False),
            mm_per_px=8.467, floor_m2=floor, ceiling_m2=floor, perimeter_m=1.0, height_m=2.4,
            height_source="default", wall_gross_m2=2.4, openings=[], wall_net_m2=2.4,
            assumptions=[]))
        page.warnings.append({"page_number": page_number, "warning_code": "SCALE_UNVERIFIED",
                              "severity": "info", "message": "canned"})
        return page

    def test_takeoff_is_wired_per_page(self):
        import json
        import tempfile
        from pathlib import Path
        import pipeline

        with tempfile.TemporaryDirectory() as tmp:
            pdf = str(Path(tmp) / "two.pdf")
            self._pdf(pdf)
            calls = []

            def fake_compute(entities, candidates, page_scales, regions, det_scale,
                             heights, page_number, page_text, w_mm, h_mm):
                calls.append((page_number, heights, round(w_mm), round(h_mm)))
                return self._canned(page_number, floor=10.0 * page_number)

            with mock.patch.object(pipeline, "compute_takeoff", side_effect=fake_compute):
                out_dir = pipeline.run_extract(pdf, [0, 1], out_parent=tmp, skip_gemini=True,
                                               allow_scale_prompt=False, ceiling_height=2.7)

            # called once per page, with the resolved heights and the page size in mm
            self.assertEqual([c[0] for c in calls], [1, 2])
            self.assertEqual(calls[0][1].ceiling_m, 2.7)
            self.assertEqual(calls[0][1].sources["ceiling"], "flag")
            self.assertEqual((calls[0][2], calls[0][3]), (210, 297))   # 595x842 pt = A4

            # takeoff.json per page, with the canned totals
            for n in (1, 2):
                d = json.loads((Path(out_dir) / "pages" / f"page_{n:02d}" / "takeoff.json").read_text())
                self.assertEqual(d["totals"]["floor_m2"], 10.0 * n)
                fe = json.loads((Path(out_dir) / "pages" / f"page_{n:02d}" / "final_entities.json").read_text())
                # attach only touches room entities; none detected on the blank page is fine
                self.assertIn("entities", fe)

            # takeoff warnings reach warnings.json
            w = json.loads((Path(out_dir) / "warnings.json").read_text())
            codes = [x["warning_code"] for x in w["warnings"]]
            self.assertEqual(codes.count("SCALE_UNVERIFIED"), 2)

            # root totals aggregate across pages; per-page summary carries its own
            summ = json.loads((Path(out_dir) / "summary.json").read_text())
            self.assertEqual(summ["totals"]["takeoff"]["floor_m2"], 30.0)
            self.assertEqual(summ["totals"]["takeoff"]["rooms_measured"], 2)
            self.assertEqual(summ["pages"][1]["takeoff"]["floor_m2"], 20.0)


class TestHeightPromptGating(unittest.TestCase):
    """--disable-rooms means no rooms, so no takeoff and nothing to prompt for;
    the flags must still validate and takeoff.json must still be written."""

    def _pdf(self, path):
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.draw_rect(fitz.Rect(100, 100, 300, 250), color=(0, 0, 0), width=1.5)
        doc.save(path)
        doc.close()

    def _run(self, disable_rooms):
        import json
        import tempfile
        from pathlib import Path
        import pipeline
        from takeoff.heights import resolve_heights as real_resolve

        calls = []

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return real_resolve(*args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            pdf = str(Path(tmp) / "one.pdf")
            self._pdf(pdf)
            with mock.patch.object(pipeline, "resolve_heights", side_effect=spy):
                out_dir = pipeline.run_extract(pdf, [0], out_parent=tmp, skip_gemini=True,
                                               allow_scale_prompt=True,
                                               disable_rooms=disable_rooms)
            takeoff = json.loads(
                (Path(out_dir) / "pages" / "page_01" / "takeoff.json").read_text())
        return calls, takeoff

    def test_rooms_disabled_never_prompts_but_still_writes_takeoff(self):
        calls, takeoff = self._run(disable_rooms=True)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1]["allow_prompt"], False)
        self.assertEqual(takeoff["rooms"], [])
        self.assertEqual(takeoff["heights"]["ceiling_m"], 2.4)

    def test_rooms_enabled_keeps_the_prompt_gate(self):
        calls, _ = self._run(disable_rooms=False)
        self.assertIs(calls[0][1]["allow_prompt"], True)


class TestRoomEvidencePassthrough(unittest.TestCase):
    def test_holes_is_carried_onto_the_room_entity(self):
        from models import Candidate
        from pipeline import _room_entity
        c = Candidate(candidate_id="room_0000", entity_type="room", bbox=(0, 0, 10, 10),
                      confidence=0.9, evidence={"polygon": [[0, 0]], "holes": 3,
                                                "area_px2": 100.0})
        e = _room_entity(c)
        self.assertEqual(e.attributes["holes"], 3)


class TestCliFlags(unittest.TestCase):
    def test_extract_parser_accepts_height_flags(self):
        import app
        parser = app.build_parser()
        ns = parser.parse_args(["extract", "x.pdf", "--ceiling-height", "2.7",
                                "--door-height", "2.0", "--window-height", "1.5"])
        self.assertEqual((ns.ceiling_height, ns.door_height, ns.window_height), (2.7, 2.0, 1.5))
        ns = parser.parse_args(["extract", "x.pdf"])
        self.assertIsNone(ns.ceiling_height)

    def test_extract_parser_rejects_bad_heights(self):
        import app
        parser = app.build_parser()
        for bad in ("0", "-2", "nan", "inf", "tall"):
            with self.assertRaises(SystemExit):
                with mock.patch("sys.stderr"):
                    parser.parse_args(["extract", "x.pdf", "--ceiling-height", bad])
