import json
import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import artifacts, config


class FakeBlob:
    def __init__(self, path, sink):
        self.path = path
        self._sink = sink
        self.content_type = None

    def upload_from_filename(self, local, content_type=None):
        self.content_type = content_type
        self._sink[self.path] = Path(local).read_bytes()

    def upload_from_string(self, data, content_type=None):
        self.content_type = content_type
        self._sink[self.path] = data.encode("utf-8") if isinstance(data, str) else data


class FakeBucket:
    def __init__(self):
        self.uploaded = {}
        self.blobs = []

    def blob(self, path):
        blob = FakeBlob(path, self.uploaded)
        self.blobs.append(blob)
        return blob


class TestPaths(unittest.TestCase):
    def test_the_run_prefix_is_customer_scoped(self):
        self.assertEqual(artifacts.run_prefix("cus-1", "t1"),
                         "customers/cus-1/takeoffs/t1")

    def test_page_paths_are_keyed_by_file_and_page(self):
        prefix = artifacts.run_prefix("cus-1", "t1")
        self.assertEqual(
            artifacts.object_path(prefix, 2, 7, "page.svg"),
            "customers/cus-1/takeoffs/t1/file_02/page_07/page.svg")


class TestArtifactSelection(unittest.TestCase):
    def test_standard_run_excludes_the_heavy_trace(self):
        names = artifacts.artifact_names(debug=False)
        self.assertEqual(names, config.STANDARD_ARTIFACTS)
        self.assertNotIn("debug_trace.json", names)

    def test_debug_run_adds_the_trace_and_viewer(self):
        names = artifacts.artifact_names(debug=True)
        self.assertIn("debug_trace.json", names)
        self.assertIn("debug_viewer.html", names)
        for name in config.STANDARD_ARTIFACTS:
            self.assertIn(name, names)


class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bucket = FakeBucket()
        self.prefix = artifacts.run_prefix("cus-1", "t1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _page_dir(self, names):
        page_dir = Path(self.tmp) / "pages" / "page_01"
        page_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            (page_dir / name).write_bytes(b"x")
        return str(page_dir)


class TestUploadPage(UploadTestCase):
    def test_present_standard_artifacts_upload_and_are_mapped(self):
        page_dir = self._page_dir(["page.svg", "takeoff.json", "render.png"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertEqual(
            got["page.svg"],
            "customers/cus-1/takeoffs/t1/file_00/page_01/page.svg")
        self.assertIn("takeoff.json", got)
        self.assertEqual(len(self.bucket.uploaded), 3)

    def test_absent_artifacts_are_skipped_without_error(self):
        page_dir = self._page_dir(["page.svg"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertEqual(list(got), ["page.svg"])

    def test_the_trace_is_not_uploaded_unless_debug_is_set(self):
        page_dir = self._page_dir(["page.svg", "debug_trace.json"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=False)
        self.assertNotIn("debug_trace.json", got)

    def test_the_trace_is_uploaded_when_debug_is_set(self):
        page_dir = self._page_dir(["page.svg", "debug_trace.json"])
        got = artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                                    debug=True)
        self.assertIn("debug_trace.json", got)

    def test_content_types_are_set_so_the_browser_renders_the_svg(self):
        page_dir = self._page_dir(["page.svg", "takeoff.json", "render.png"])
        artifacts.upload_page(self.bucket, page_dir, self.prefix, 0, 1,
                              debug=False)
        by_path = {b.path: b.content_type for b in self.bucket.blobs}
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/page.svg"],
            "image/svg+xml")
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/takeoff.json"],
            "application/json")
        self.assertEqual(
            by_path["customers/cus-1/takeoffs/t1/file_00/page_01/render.png"],
            "image/png")


class TestUploadRunFiles(UploadTestCase):
    def test_run_root_files_upload_under_the_file_prefix(self):
        Path(self.tmp, "summary.json").write_text("{}", encoding="utf-8")
        Path(self.tmp, "warnings.json").write_text("[]", encoding="utf-8")
        got = artifacts.upload_run_files(self.bucket, self.tmp, self.prefix, 1)
        self.assertEqual(got["summary.json"],
                         "customers/cus-1/takeoffs/t1/file_01/summary.json")
        self.assertEqual(len(self.bucket.uploaded), 2)


class TestUploadJson(UploadTestCase):
    def test_a_dict_is_written_as_pretty_json_at_the_run_root(self):
        path = artifacts.upload_json(self.bucket, self.prefix, "run.json",
                                     {"pagesProcessed": 2})
        self.assertEqual(path, "customers/cus-1/takeoffs/t1/run.json")
        self.assertEqual(
            json.loads(self.bucket.uploaded[path].decode("utf-8")),
            {"pagesProcessed": 2})


if __name__ == "__main__":
    unittest.main()
