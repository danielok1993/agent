import shutil
import tempfile
import unittest
from pathlib import Path

from takeoff_fn import sources
from takeoff_fn.errors import InvalidArgument, PermissionDenied
from takeoff_fn.records import SourceFile


class FakeBlob:
    def __init__(self, path, payload):
        self.path = path
        self._payload = payload

    def download_to_filename(self, local):
        if self._payload is None:
            raise RuntimeError(f"no such object: {self.path}")
        Path(local).write_bytes(self._payload)


class FakeBucket:
    def __init__(self, objects):
        self._objects = objects
        self.requested = []

    def blob(self, path):
        self.requested.append(path)
        return FakeBlob(path, self._objects.get(path))


class TestParseGsUri(unittest.TestCase):
    def test_a_valid_uri_splits_into_bucket_and_object(self):
        self.assertEqual(
            sources.parse_gs_uri("gs://my-bucket/estimate_images/cus-1/est-1/a.pdf"),
            ("my-bucket", "estimate_images/cus-1/est-1/a.pdf"))

    def test_a_non_gs_scheme_is_invalid(self):
        for uri in ("https://example.com/a.pdf", "estimate_images/cus-1/a.pdf", ""):
            with self.subTest(uri=uri):
                with self.assertRaises(InvalidArgument):
                    sources.parse_gs_uri(uri)

    def test_a_uri_with_no_object_path_is_invalid(self):
        with self.assertRaises(InvalidArgument):
            sources.parse_gs_uri("gs://my-bucket")


class TestCustomerScope(unittest.TestCase):
    def test_a_path_containing_the_customer_segment_is_allowed(self):
        sources.assert_customer_scoped(
            "estimate_images/cus-1/est-1/a.pdf", "cus-1")
        sources.assert_customer_scoped(
            "customers/cus-1/takeoffs/t1/a.pdf", "cus-1")
        sources.assert_customer_scoped(
            "estimate_documents/cus-1/est-1/a.pdf", "cus-1")
        sources.assert_customer_scoped(
            "estimate_videos/cus-1/est-1/a.pdf", "cus-1")

    def test_another_tenants_path_is_denied(self):
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-2/est-1/a.pdf", "cus-1")

    def test_a_prefix_collision_is_denied(self):
        # "cus-10" must not satisfy the boundary for "cus-1".
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-10/est-1/a.pdf", "cus-1")

    def test_a_traversal_segment_is_denied(self):
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-1/../cus-2/a.pdf", "cus-1")

    def test_the_tenant_must_sit_at_the_anchored_position(self):
        # The tenant appearing anywhere is not enough: it has to be the
        # segment immediately after a known prefix, which is the only place
        # rivet-mind ever writes it.
        for path in ("estimate_images/cus-2/est-1/cus-1.pdf",
                     "estimate_images/cus-2/cus-1/a.pdf",
                     "cus-1/est-1/a.pdf",
                     "other_bucket_root/cus-1/a.pdf"):
            with self.subTest(path=path):
                with self.assertRaises(PermissionDenied):
                    sources.assert_customer_scoped(path, "cus-1")

    def test_a_tenant_id_appearing_only_as_a_filename_is_denied(self):
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "estimate_images/cus-2/est-1/cus-1", "cus-1")

    def test_an_unknown_root_is_denied_even_with_a_correct_looking_tenant(self):
        # The allowlist is the point: a root we don't recognise must be
        # denied even when the tenant segment right after it looks correct.
        with self.assertRaises(PermissionDenied):
            sources.assert_customer_scoped(
                "random_bucket_path/cus-1/est-1/a.pdf", "cus-1")


class TestDownloadSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_files_download_to_index_named_paths(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/a.pdf": b"%PDF-1.4 A"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-1/e/a.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(warnings, [])
        self.assertEqual(len(got), 1)
        self.assertEqual(Path(got[0].local_path).read_bytes(), b"%PDF-1.4 A")
        self.assertTrue(Path(got[0].local_path).name.startswith("file_00"))

    def test_a_failed_download_warns_and_the_others_survive(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/b.pdf": b"%PDF-1.4 B"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-1/e/a.pdf"),
             SourceFile(1, "b.pdf", "gs://b/estimate_images/cus-1/e/b.pdf")],
            self.tmp, "cus-1")
        self.assertEqual([s.file_name for s in got], ["b.pdf"])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["warning_code"], "TAKEOFF_SOURCE_UNREADABLE")

    def test_another_tenants_file_warns_rather_than_downloading(self):
        bucket = FakeBucket({"estimate_images/cus-2/e/a.pdf": b"%PDF"})
        got, warnings = sources.download_sources(
            bucket,
            [SourceFile(0, "a.pdf", "gs://b/estimate_images/cus-2/e/a.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(got, [])
        self.assertEqual(warnings[0]["warning_code"], "TAKEOFF_SOURCE_FORBIDDEN")
        self.assertEqual(bucket.requested, [])

    def test_a_pdf_name_is_sanitised_out_of_the_local_path(self):
        bucket = FakeBucket({"estimate_images/cus-1/e/x.pdf": b"%PDF"})
        got, _ = sources.download_sources(
            bucket,
            [SourceFile(0, "../../etc/passwd", "gs://b/estimate_images/cus-1/e/x.pdf")],
            self.tmp, "cus-1")
        self.assertEqual(Path(got[0].local_path).parent, Path(self.tmp))


if __name__ == "__main__":
    unittest.main()
