import json
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import sheets


def _write_page(out_dir, page_number, region_types, takeoff=None,
                skip_detection=False):
    page_dir = Path(out_dir) / "pages" / f"page_{page_number:02d}"
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "regions.json").write_text(json.dumps({
        "page_number": page_number,
        "skip_detection": skip_detection,
        "regions": [{"region_id": f"r{i}", "region_type": t, "bbox": [0, 0, 1, 1]}
                    for i, t in enumerate(region_types)],
    }), encoding="utf-8")
    if takeoff is not None:
        (page_dir / "takeoff.json").write_text(json.dumps(takeoff), encoding="utf-8")
    return str(page_dir)


def _takeoff(page_number):
    return {"schema_version": 1, "page_number": page_number,
            "page_frame": {"width_px": 100, "height_px": 200},
            "rooms": [], "openings": [], "warnings": []}


class SheetsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def collect(self, file_index=0, file_name="plans.pdf"):
        return sheets.collect_sheets(
            self.tmp, file_index, file_name,
            svg_path_for=lambda p: f"prefix/file_{file_index:02d}/page_{p:02d}/page.svg")


class TestPageDiscovery(SheetsTestCase):
    def test_page_dirs_are_returned_in_page_order(self):
        _write_page(self.tmp, 10, ["floor_plan"], _takeoff(10))
        _write_page(self.tmp, 2, ["floor_plan"], _takeoff(2))
        self.assertEqual([n for n, _ in sheets.page_dirs(self.tmp)], [2, 10])

    def test_a_tree_with_no_pages_directory_yields_nothing(self):
        self.assertEqual(sheets.page_dirs(self.tmp), [])


class TestFloorPlanFilter(SheetsTestCase):
    def test_a_floor_plan_page_becomes_a_sheet(self):
        _write_page(self.tmp, 1, ["floor_plan", "title_block"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(len(found), 1)
        self.assertEqual(skipped, [])

    def test_an_elevation_only_page_is_skipped_with_a_reason(self):
        _write_page(self.tmp, 1, ["elevation", "title_block"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_floor_plan_region"}])

    def test_a_floor_plan_page_with_no_takeoff_json_is_skipped(self):
        _write_page(self.tmp, 1, ["floor_plan"], takeoff=None)
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_takeoff_document"}])

    def test_a_page_with_no_regions_json_is_skipped(self):
        (Path(self.tmp) / "pages" / "page_01").mkdir(parents=True)
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_regions_document"}])

    def test_a_page_whose_regions_json_is_not_utf8_is_skipped(self):
        # UnicodeDecodeError is a ValueError, not a json.JSONDecodeError —
        # a narrow except would let it crash the whole run instead.
        page_dir = Path(_write_page(self.tmp, 1, ["floor_plan"], _takeoff(1)))
        (page_dir / "regions.json").write_bytes(b"\xff\xfe not utf-8 at all")
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_regions_document"}])

    def test_a_page_whose_takeoff_json_is_malformed_is_skipped(self):
        page_dir = Path(_write_page(self.tmp, 1, ["floor_plan"], _takeoff(1)))
        (page_dir / "takeoff.json").write_text("{not json", encoding="utf-8")
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped, [{"page_number": 1, "reason": "no_takeoff_document"}])


class TestSheetIdentity(SheetsTestCase):
    def test_ids_are_unique_across_source_files(self):
        _write_page(self.tmp, 1, ["floor_plan"], _takeoff(1))
        a, _ = self.collect(file_index=0)
        b, _ = self.collect(file_index=1)
        self.assertEqual(a[0]["sheet_id"], "sheet_00_01")
        self.assertEqual(b[0]["sheet_id"], "sheet_01_01")
        self.assertNotEqual(a[0]["sheet_id"], b[0]["sheet_id"])

    def test_source_file_and_label_and_svg_path_are_injected(self):
        _write_page(self.tmp, 3, ["floor_plan"], _takeoff(3))
        found, _ = self.collect(file_index=2, file_name="WD03.pdf")
        sheet = found[0]
        self.assertEqual(sheet["source_file_id"], "file_02")
        self.assertEqual(sheet["source_file_name"], "WD03.pdf")
        self.assertEqual(sheet["label"], "WD03.pdf — page 3")
        self.assertEqual(sheet["plan_svg_url"], "prefix/file_02/page_03/page.svg")

    def test_the_takeoff_payload_is_preserved_verbatim(self):
        _write_page(self.tmp, 1, ["floor_plan"], _takeoff(1))
        sheet = self.collect()[0][0]
        self.assertEqual(sheet["schema_version"], 1)
        self.assertEqual(sheet["page_number"], 1)
        self.assertEqual(sheet["page_frame"], {"width_px": 100, "height_px": 200})

    def test_structured_warnings_survive_unflattened(self):
        payload = _takeoff(1)
        payload["warnings"] = [{"warning_code": "TAKEOFF_NO_SCALE",
                                "severity": "warning", "message": "no scale",
                                "page_number": 1}]
        _write_page(self.tmp, 1, ["floor_plan"], payload)
        sheet = self.collect()[0][0]
        self.assertEqual(sheet["warnings"][0]["warning_code"], "TAKEOFF_NO_SCALE")


class TestUnclassifiedRegions(SheetsTestCase):
    """pipeline.resolve_page_regions returns UNCLASSIFIED regions on three
    paths where detection still runs unfiltered and a real takeoff.json is
    still written: a raster page with no vector ink, a
    REGION_CLASSIFY_PARSE_FAILURE, and offline-with-no-cache. Skipping those
    pages throws away a genuine measurement and fails the whole takeoff."""

    def test_an_all_unclassified_page_is_admitted_as_a_sheet(self):
        _write_page(self.tmp, 1, ["unclassified", "unclassified"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(len(found), 1)
        self.assertEqual(skipped, [])

    def test_an_admitted_unclassified_page_carries_a_warning(self):
        _write_page(self.tmp, 1, ["unclassified"], _takeoff(1))
        sheet = self.collect()[0][0]
        codes = [w["warning_code"] for w in sheet["warnings"]]
        self.assertIn("TAKEOFF_REGIONS_UNCLASSIFIED", codes)
        warning = next(w for w in sheet["warnings"]
                       if w["warning_code"] == "TAKEOFF_REGIONS_UNCLASSIFIED")
        self.assertEqual(warning["severity"], "warning")
        self.assertEqual(warning["page_number"], 1)

    def test_the_warning_is_appended_not_substituted(self):
        payload = _takeoff(1)
        payload["warnings"] = [{"warning_code": "TAKEOFF_NO_SCALE",
                                "severity": "warning", "message": "no scale",
                                "page_number": 1}]
        _write_page(self.tmp, 1, ["unclassified"], payload)
        sheet = self.collect()[0][0]
        self.assertEqual([w["warning_code"] for w in sheet["warnings"]],
                         ["TAKEOFF_NO_SCALE", "TAKEOFF_REGIONS_UNCLASSIFIED"])

    def test_a_raster_page_with_no_regions_at_all_is_admitted(self):
        # RASTER_PAGE_NO_VECTOR_INK returns an EMPTY region list, and
        # detection still ran over the whole page.
        _write_page(self.tmp, 1, [], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(len(found), 1)
        self.assertIn("TAKEOFF_REGIONS_UNCLASSIFIED",
                      [w["warning_code"] for w in found[0]["warnings"]])

    def test_a_classified_page_with_no_floor_plan_is_still_skipped(self):
        _write_page(self.tmp, 1, ["elevation", "title_block"], _takeoff(1))
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped,
                         [{"page_number": 1, "reason": "no_floor_plan_region"}])

    def test_a_page_detection_was_skipped_on_is_not_admitted(self):
        # skip_detection means run_heuristics never ran: there is nothing in
        # takeoff.json to review.
        _write_page(self.tmp, 1, ["unclassified"], _takeoff(1),
                    skip_detection=True)
        found, skipped = self.collect()
        self.assertEqual(found, [])
        self.assertEqual(skipped,
                         [{"page_number": 1, "reason": "regions_unclassified"}])


class TestPageDirectory(SheetsTestCase):
    def test_each_sheet_carries_where_it_was_read_from(self):
        page_dir = _write_page(self.tmp, 3, ["floor_plan"], _takeoff(3))
        sheet = self.collect()[0][0]
        self.assertEqual(sheet[sheets.PAGE_SOURCE_KEY], (3, page_dir))

    def test_the_page_number_is_the_directorys_not_the_payloads(self):
        # They can disagree. plan_svg_url is built from the DIRECTORY number,
        # so the upload has to use the same one or it writes nowhere the
        # sheet points at.
        payload = _takeoff(1)
        payload["page_number"] = 99
        page_dir = _write_page(self.tmp, 3, ["floor_plan"], payload)
        sheet = self.collect()[0][0]
        self.assertEqual(sheet[sheets.PAGE_SOURCE_KEY], (3, page_dir))
        self.assertEqual(sheet["plan_svg_url"],
                         "prefix/file_00/page_03/page.svg")


if __name__ == "__main__":
    unittest.main()
