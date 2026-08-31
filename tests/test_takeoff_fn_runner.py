import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from takeoff_fn import config, runner
from takeoff_fn.errors import TakeoffFnError
from takeoff_fn.request import TakeoffRequest

NOW = 1_700_000_000_000


class FakeBlob:
    def __init__(self, path, sink, objects):
        self.path, self._sink, self._objects = path, sink, objects

    def download_to_filename(self, local):
        if self.path not in self._objects:
            raise RuntimeError(f"no such object: {self.path}")
        Path(local).write_bytes(self._objects[self.path])

    def upload_from_filename(self, local, content_type=None):
        self._sink[self.path] = Path(local).read_bytes()

    def upload_from_string(self, data, content_type=None):
        self._sink[self.path] = data.encode("utf-8") if isinstance(data, str) else data


class FakeBucket:
    def __init__(self, objects=None):
        self.uploaded, self._objects = {}, objects or {}

    def blob(self, path):
        return FakeBlob(path, self.uploaded, self._objects)


class FakeDoc:
    def __init__(self, data):
        self._data, self.updates = data, []

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data)

    def get(self):
        return self

    def update(self, patch):
        self.updates.append(patch)
        self._data.update(patch)


class FakeDb:
    def __init__(self, data):
        self.doc = FakeDoc(data)

    def collection(self, _name):
        class _C:
            def __init__(self, doc):
                self._doc = doc

            def document(self, _id):
                return self._doc
        return _C(self.doc)


def _record(source_urls):
    return {
        "customerId": "cus-1", "status": "queued", "estimateId": "est-1",
        "updatedAt": NOW - 1000,
        "sourceFiles": [{"fileName": f"f{i}.pdf", "storageUrl": u}
                        for i, u in enumerate(source_urls)],
    }


def _make_extract(pages):
    """pages: {page_number: (region_types, takeoff_dict | None)}"""
    def _extract(**kwargs):
        out_dir = kwargs["out_parent"] + "/run"
        for number, (types, takeoff) in pages.items():
            page_dir = Path(out_dir) / "pages" / f"page_{number:02d}"
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "regions.json").write_text(json.dumps({
                "page_number": number,
                "regions": [{"region_type": t} for t in types]}), encoding="utf-8")
            (page_dir / "page.svg").write_text("<svg/>", encoding="utf-8")
            if takeoff is not None:
                (page_dir / "takeoff.json").write_text(json.dumps(takeoff),
                                                       encoding="utf-8")
        Path(out_dir, "summary.json").write_text("{}", encoding="utf-8")
        Path(out_dir, "warnings.json").write_text("[]", encoding="utf-8")
        return out_dir
    return _extract


def _takeoff(page_number):
    """A normally measured page: one scale, read off the sheet."""
    return {"schema_version": 1, "page_number": page_number,
            "scale": {"page": {"denominator": 50.0}, "by_region": {}},
            "rooms": [{"room_id": "room_0000", "mm_per_px": 8.47}],
            "openings": [], "warnings": []}


def _unscaled_takeoff(page_number):
    """A page the resolver could not read a scale for.

    Rooms survive with their geometry and no mm_per_px — see
    takeoff/quantities.py, which keeps an unscaled room so it still appears
    on the overlay and still takes part in opening assignment.
    """
    return {"schema_version": 1, "page_number": page_number,
            "scale": {"page": None, "by_region": {}},
            "rooms": [{"room_id": "room_0000", "mm_per_px": None}],
            "openings": [],
            "warnings": [{"warning_code": "TAKEOFF_NO_SCALE",
                          "severity": "warning",
                          "message": "1 room(s) have no resolvable scale",
                          "page_number": page_number}]}


class TestSheetIsScaled(unittest.TestCase):
    def test_a_page_scale_makes_a_sheet_scaled(self):
        self.assertTrue(runner.sheet_is_scaled(
            {"scale": {"page": {"denominator": 50.0}}, "rooms": []}))

    def test_a_region_measured_room_makes_a_sheet_scaled(self):
        # A multi-scale sheet has no page scale and is still measured.
        self.assertTrue(runner.sheet_is_scaled(
            {"scale": {"page": None},
             "rooms": [{"mm_per_px": None}, {"mm_per_px": 8.47}]}))

    def test_no_page_scale_and_no_measured_room_is_unscaled(self):
        self.assertFalse(runner.sheet_is_scaled(
            {"scale": {"page": None},
             "rooms": [{"mm_per_px": None}, {"mm_per_px": None}]}))

    def test_a_sheet_with_no_rooms_at_all_is_unscaled(self):
        self.assertFalse(runner.sheet_is_scaled({"scale": {"page": None},
                                                 "rooms": []}))

    def test_a_malformed_scale_block_is_unscaled_rather_than_raising(self):
        # takeoff.json is read off disk; a sheet must never crash the run.
        for sheet in ({}, {"scale": None}, {"scale": {}},
                      {"scale": {"page": {}}}):
            with self.subTest(sheet=sheet):
                self.assertFalse(runner.sheet_is_scaled(sheet))


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_it(self, db, bucket, extract, **kwargs):
        return runner.run_measurement(
            self.request, db=db, bucket=bucket, extract_fn=extract,
            page_count_fn=lambda _p: 1, now_fn=lambda: NOW,
            workdir=self.tmp, **kwargs)


class TestHappyPath(RunnerTestCase):
    def test_a_floor_plan_page_produces_a_sheet_and_awaiting_review(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))

        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.sheets[0]["sheet_id"], "sheet_00_01")
        statuses = [u["status"] for u in db.doc.updates]
        self.assertEqual(statuses, [config.STATUS_PROCESSING,
                                    config.STATUS_AWAITING_REVIEW])

    def test_the_document_written_to_firestore_is_a_json_string(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({1: (["floor_plan"], _takeoff(1))}))

        raw = db.doc.updates[-1]["document"]
        self.assertIsInstance(raw, str)
        parsed = json.loads(raw)
        self.assertEqual(parsed["schemaVersion"], 1)
        self.assertEqual(len(parsed["sheets"]), 1)

    def test_the_svg_path_on_the_sheet_matches_where_it_was_uploaded(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))
        svg_path = result.sheets[0]["plan_svg_url"]
        self.assertIn(svg_path, bucket.uploaded)

    def test_the_working_directory_is_cleaned_up(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({1: (["floor_plan"], _takeoff(1))}))
        leftovers = list(Path(self.tmp).iterdir())
        self.assertEqual(leftovers, [])

    def test_run_artifacts_are_kept_per_source_file(self):
        # upload_run_files returns fixed key names, so merging every source
        # under one dict silently drops all but the last file's manifest.
        a = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        b = "gs://b/estimate_images/cus-1/est-1/f1.pdf"
        db = FakeDb(_record([a, b]))
        bucket = FakeBucket({
            "estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4",
            "estimate_images/cus-1/est-1/f1.pdf": b"%PDF-1.4",
        })
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))

        self.assertNotIn("_run", result.artifacts["bySheet"],
                         "bySheet is contractually {[sheetId]: {...}}")
        run_files = result.artifacts["run"]
        self.assertEqual(sorted(run_files), ["file_00", "file_01"])
        self.assertIn("summary.json", run_files["file_00"])
        self.assertIn("summary.json", run_files["file_01"])
        self.assertNotEqual(run_files["file_00"]["summary.json"],
                            run_files["file_01"]["summary.json"])


class TestFiltering(RunnerTestCase):
    def test_an_elevation_page_is_skipped_and_recorded(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket, _make_extract({
            1: (["floor_plan"], _takeoff(1)),
            2: (["elevation"], _takeoff(2)),
        }))
        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.run["pagesSkipped"][0]["page_number"], 2)

    def test_a_skipped_page_uploads_no_artifacts(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        self.run_it(db, bucket, _make_extract({
            1: (["floor_plan"], _takeoff(1)),
            2: (["elevation"], _takeoff(2)),
        }))
        self.assertNotIn(
            "customers/cus-1/takeoffs/t1/file_00/page_02/page.svg",
            bucket.uploaded)


class TestPartialFailure(RunnerTestCase):
    def test_one_unreadable_file_warns_and_the_other_still_measures(self):
        good = "gs://b/estimate_images/cus-1/est-1/f1.pdf"
        bad = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([bad, good]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f1.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))

        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)
        codes = [w["warning_code"] for w in result.run["warnings"]]
        self.assertIn("TAKEOFF_SOURCE_UNREADABLE", codes)

    def test_no_readable_files_fails_the_takeoff(self):
        db = FakeDb(_record(["gs://b/estimate_images/cus-1/est-1/f0.pdf"]))
        bucket = FakeBucket({})
        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket, _make_extract({}))
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)

    def test_no_floor_plan_anywhere_fails_the_takeoff(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket,
                        _make_extract({1: (["elevation"], _takeoff(1))}))
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)

    def test_an_extraction_crash_marks_failed_and_keeps_the_cause(self):
        # The crash is now tolerated per-source (a corrupt file must not lose
        # the good plans), so it surfaces as a warning rather than
        # propagating. With only one file nothing survives, the takeoff still
        # fails, and run.json still carries what actually went wrong.
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})

        def _boom(**_kwargs):
            raise RuntimeError("detector exploded")

        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket, _boom)
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)
        manifest = json.loads(
            bucket.uploaded["customers/cus-1/takeoffs/t1/run.json"]
            .decode("utf-8"))
        self.assertIn("detector exploded",
                      manifest["warnings"][0]["message"])
        self.assertEqual(manifest["warnings"][0]["warning_code"],
                         "TAKEOFF_SOURCE_UNREADABLE")

    def test_a_setup_failure_after_mark_processing_still_marks_failed(self):
        # mkdtemp can fail: /tmp on Cloud Functions is tmpfs charged against
        # the memory budget. The record must not be left saying "processing".
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        with mock.patch("takeoff_fn.runner.tempfile.mkdtemp",
                        side_effect=OSError("no space left on device")):
            with self.assertRaises(OSError):
                runner.run_measurement(
                    self.request, db=db, bucket=bucket,
                    extract_fn=_make_extract({1: (["floor_plan"], _takeoff(1))}),
                    page_count_fn=lambda _p: 1, now_fn=lambda: NOW,
                    workdir=None)
        statuses = [u["status"] for u in db.doc.updates]
        self.assertEqual(statuses, [config.STATUS_PROCESSING, config.STATUS_FAILED])
        self.assertIn("no space left", db.doc.updates[-1]["error"])


class TestExtractionOptions(RunnerTestCase):
    """The function is a transport wrapper: run_extract must be called with
    exactly the arguments app.py uses, or the deployed detector runs on a
    different code path from the one tools/regress.py validates."""

    def _spy_kwargs(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        seen = {}
        base = _make_extract({1: (["floor_plan"], _takeoff(1))})

        def _spy(**kwargs):
            seen.update(kwargs)
            return base(**kwargs)

        self.run_it(db, bucket, _spy)
        return seen

    def test_every_argument_passed_to_run_extract_is_pinned(self):
        seen = dict(self._spy_kwargs())
        out_parent = seen.pop("out_parent")
        pdf_path = seen.pop("pdf_path")
        self.assertEqual(seen, {
            "page_indices": [0],
            "skip_gemini": False,
            "disable_rooms": False,
            "disable_windows": False,
            "debug": False,
            "refresh_regions": False,
            "write_svg": True,
            "allow_scale_prompt": False,
            "fallback_denominator": None,
            "ceiling_height": None,
            "door_height": None,
            "window_height": None,
        })
        self.assertTrue(Path(out_parent).is_absolute())
        self.assertTrue(pdf_path.endswith(".pdf"))

    def test_debug_is_threaded_through_from_the_request(self):
        self.request = TakeoffRequest("t1", "cus-1", "uid-1", debug=True)
        self.assertTrue(self._spy_kwargs()["debug"])

    def test_no_run_extract_parameter_is_left_unconsidered(self):
        """A new run_extract parameter whose default differs from what app.py
        passes would silently put the callable on another code path. This
        fails the fast tier the moment such a parameter appears."""
        import inspect

        from pipeline import run_extract

        parameters = set(inspect.signature(run_extract).parameters)
        passed = set(self._spy_kwargs())
        # disable_walls is a deprecated alias for disable_rooms; app.py does
        # not pass it either, and run_extract ORs the two.
        deliberately_omitted = {"disable_walls"}
        unconsidered = parameters - passed - deliberately_omitted
        self.assertEqual(
            unconsidered, set(),
            f"run_extract grew parameter(s) {sorted(unconsidered)}. Decide "
            "explicitly what the callable should pass (it must match what "
            "app.py passes) and either pin it in "
            "test_every_argument_passed_to_run_extract_is_pinned or list it "
            "in deliberately_omitted here.")


class TestSourceFailureTolerance(RunnerTestCase):
    """A file that downloads but will not PARSE must warn and be skipped, the
    same as one that will not download. The design's failure handling is
    per-source; aborting the loop discards plans that already measured."""

    def _two_files(self):
        a = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        b = "gs://b/estimate_images/cus-1/est-1/f1.pdf"
        db = FakeDb(_record([a, b]))
        bucket = FakeBucket({
            "estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4",
            "estimate_images/cus-1/est-1/f1.pdf": b"%PDF-1.4",
        })
        return db, bucket

    def test_an_unparseable_pdf_warns_and_the_other_file_still_measures(self):
        db, bucket = self._two_files()
        base = _make_extract({1: (["floor_plan"], _takeoff(1))})

        def _extract(**kwargs):
            if "file_00" in kwargs["pdf_path"]:
                raise RuntimeError("cannot open broken document")
            return base(**kwargs)

        result = self.run_it(db, bucket, _extract)
        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.sheets[0]["source_file_id"], "file_01")
        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)
        unreadable = [w for w in result.run["warnings"]
                      if w["warning_code"] == "TAKEOFF_SOURCE_UNREADABLE"]
        self.assertEqual(len(unreadable), 1)
        self.assertIn("f0.pdf", unreadable[0]["message"])
        self.assertIn("cannot open broken document", unreadable[0]["message"])
        self.assertEqual(unreadable[0]["severity"], "error")
        self.assertIsNone(unreadable[0]["page_number"])

    def test_a_page_count_failure_is_tolerated_the_same_way(self):
        db, bucket = self._two_files()

        def _page_count(path):
            if "file_00" in path:
                raise RuntimeError("password protected")
            return 1

        result = runner.run_measurement(
            self.request, db=db, bucket=bucket,
            extract_fn=_make_extract({1: (["floor_plan"], _takeoff(1))}),
            page_count_fn=_page_count, now_fn=lambda: NOW, workdir=self.tmp)

        self.assertEqual(len(result.sheets), 1)
        self.assertEqual(result.sheets[0]["source_file_id"], "file_01")
        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)
        unreadable = [w for w in result.run["warnings"]
                      if w["warning_code"] == "TAKEOFF_SOURCE_UNREADABLE"]
        self.assertEqual(len(unreadable), 1)
        self.assertIn("f0.pdf", unreadable[0]["message"])
        self.assertIn("password protected", unreadable[0]["message"])

    def test_every_file_failing_still_fails_the_takeoff(self):
        db, bucket = self._two_files()

        def _boom(**_kwargs):
            raise RuntimeError("detector exploded")

        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket, _boom)
        self.assertEqual(db.doc.updates[-1]["status"], config.STATUS_FAILED)


class TestWorkingSetIsFreedAsItGoes(RunnerTestCase):
    """/tmp is tmpfs charged against the 2 GiB memory budget, so peak usage
    must be the max over source files, not the sum."""

    def _two_files(self):
        a = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        b = "gs://b/estimate_images/cus-1/est-1/f1.pdf"
        db = FakeDb(_record([a, b]))
        bucket = FakeBucket({
            "estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4",
            "estimate_images/cus-1/est-1/f1.pdf": b"%PDF-1.4",
        })
        return db, bucket

    def _snapshot(self):
        return sorted(str(p.relative_to(self.tmp))
                      for p in Path(self.tmp).rglob("*") if p.is_file())

    def test_the_previous_sources_pdf_and_output_tree_are_already_gone(self):
        db, bucket = self._two_files()
        base = _make_extract({1: (["floor_plan"], _takeoff(1))})
        snapshots = []

        def _spy(**kwargs):
            snapshots.append(self._snapshot())
            return base(**kwargs)

        self.run_it(db, bucket, _spy)
        self.assertEqual(len(snapshots), 2)
        self.assertIn("sources/file_00.pdf", snapshots[0])
        # By the second extraction the first source's PDF is deleted and its
        # whole output tree removed.
        self.assertNotIn("sources/file_00.pdf", snapshots[1])
        self.assertEqual([f for f in snapshots[1] if f.startswith("out_00")], [])
        self.assertIn("sources/file_01.pdf", snapshots[1])

    def test_the_source_pdf_is_released_even_when_extraction_fails(self):
        db, bucket = self._two_files()
        base = _make_extract({1: (["floor_plan"], _takeoff(1))})
        snapshots = []

        def _spy(**kwargs):
            snapshots.append(self._snapshot())
            if "file_00" in kwargs["pdf_path"]:
                raise RuntimeError("cannot open broken document")
            return base(**kwargs)

        self.run_it(db, bucket, _spy)
        self.assertNotIn("sources/file_00.pdf", snapshots[1])
        self.assertEqual([f for f in snapshots[1] if f.startswith("out_00")], [])


class TestRunManifest(RunnerTestCase):
    def test_run_json_is_uploaded_even_when_no_sheet_survives(self):
        # Page artefacts may already be in Storage; without run.json there is
        # no manifest to diagnose the failure from.
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        with self.assertRaises(TakeoffFnError):
            self.run_it(db, bucket,
                        _make_extract({1: (["elevation"], _takeoff(1))}))
        manifest = "customers/cus-1/takeoffs/t1/run.json"
        self.assertIn(manifest, bucket.uploaded)
        body = json.loads(bucket.uploaded[manifest].decode("utf-8"))
        self.assertEqual(body["pagesMeasured"], 0)
        self.assertEqual(body["pagesSkipped"][0]["reason"],
                         "no_floor_plan_region")

    def test_the_success_manifest_still_records_its_own_object_path(self):
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))
        self.assertEqual(result.run["manifest"],
                         "customers/cus-1/takeoffs/t1/run.json")
        self.assertEqual(result.run["pagesMeasured"], 1)


class TestSheetPayloadHygiene(RunnerTestCase):
    def test_the_internal_page_directory_key_never_reaches_the_response(self):
        from takeoff_fn import sheets as sheets_module
        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        db = FakeDb(_record([url]))
        bucket = FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"})
        result = self.run_it(db, bucket,
                             _make_extract({1: (["floor_plan"], _takeoff(1))}))
        self.assertNotIn(sheets_module.PAGE_SOURCE_KEY, result.sheets[0])
        document = json.loads(db.doc.updates[-1]["document"])
        self.assertNotIn(sheets_module.PAGE_SOURCE_KEY, document["sheets"][0])


class TestTerminalStatus(RunnerTestCase):
    URL = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
    OBJECT = {"estimate_images/cus-1/est-1/f0.pdf": b"%PDF-1.4"}

    def test_a_wholly_unscaled_run_parks_at_awaiting_scale(self):
        db = FakeDb(_record([self.URL]))
        self.run_it(db, FakeBucket(self.OBJECT), _make_extract(
            {1: (["floor_plan"], _unscaled_takeoff(1))}))

        self.assertEqual([u["status"] for u in db.doc.updates],
                         [config.STATUS_PROCESSING,
                          config.STATUS_AWAITING_SCALE])
        # The document is still written — the prompt needs the plan SVG.
        self.assertIn("document", db.doc.updates[-1])
        self.assertIsNone(db.doc.updates[-1]["error"])

    def test_a_wholly_unscaled_run_given_a_scale_reaches_awaiting_review(self):
        # A page with no floor_plan region at all (scanned sheet, failed
        # Gemini classify/parse) gives the fallback tier nothing to bind, so
        # a supplied scale is inert and the run still resolves nothing. It
        # must not park at awaiting_scale again — that would ask the same
        # question forever. The client's existing effect fails it honestly.
        self.request = TakeoffRequest(
            "t1", "cus-1", "uid-1", debug=False, scale_denominator=100.0)
        db = FakeDb(_record([self.URL]))
        self.run_it(db, FakeBucket(self.OBJECT), _make_extract(
            {1: (["floor_plan"], _unscaled_takeoff(1))}))

        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)

    def test_a_partially_scaled_run_still_reaches_awaiting_review(self):
        # One page scaled, one not. The scaled page is reviewable, so the
        # takeoff is not blocked on a question about the other.
        db = FakeDb(_record([self.URL]))
        self.run_it(db, FakeBucket(self.OBJECT), _make_extract({
            1: (["floor_plan"], _unscaled_takeoff(1)),
            2: (["floor_plan"], _takeoff(2)),
        }))

        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)

    def test_a_region_measured_page_with_no_page_scale_is_reviewable(self):
        # A multi-scale sheet (s17) states no single scale and is perfectly
        # measured. Reading "no page scale" as "unscaled" would park a
        # finished takeoff on a question it does not need answered.
        sheet = _unscaled_takeoff(1)
        sheet["rooms"] = [{"room_id": "room_0000", "mm_per_px": 8.47}]
        db = FakeDb(_record([self.URL]))
        self.run_it(db, FakeBucket(self.OBJECT),
                    _make_extract({1: (["floor_plan"], sheet)}))

        self.assertEqual(db.doc.updates[-1]["status"],
                         config.STATUS_AWAITING_REVIEW)


class TestSuppliedScaleReachesTheDetector(RunnerTestCase):
    def test_the_request_scale_is_passed_to_run_extract(self):
        self.request = TakeoffRequest(
            "t1", "cus-1", "uid-1", debug=False, scale_denominator=100.0)
        captured = {}
        inner = _make_extract({1: (["floor_plan"], _takeoff(1))})

        def extract(**kwargs):
            captured.update(kwargs)
            return inner(**kwargs)

        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        self.run_it(FakeDb(_record([url])),
                    FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF"}),
                    extract)

        self.assertEqual(captured["fallback_denominator"], 100.0)

    def test_no_supplied_scale_passes_none(self):
        captured = {}
        inner = _make_extract({1: (["floor_plan"], _takeoff(1))})

        def extract(**kwargs):
            captured.update(kwargs)
            return inner(**kwargs)

        url = "gs://b/estimate_images/cus-1/est-1/f0.pdf"
        self.run_it(FakeDb(_record([url])),
                    FakeBucket({"estimate_images/cus-1/est-1/f0.pdf": b"%PDF"}),
                    extract)

        self.assertIsNone(captured["fallback_denominator"])


if __name__ == "__main__":
    unittest.main()
