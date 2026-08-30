"""The function must not change detection results.

tools/regress.py guards the CLI path against the ground-truth corpus. If the
deployed callable can drift from that path, the guard means nothing. This test
runs one corpus sheet both ways and compares the takeoff payload field for
field.

Skipped when the NDA corpus is not on disk (see fixtures/MANIFEST.json) or
when Vertex AI is not configured in this environment (run_measurement always
calls run_extract with skip_gemini=False, and gemini.client.init_client()
raises EnvironmentError without a GCP project + ADC credentials) -- gating on
the corpus alone would trade a clean skip for a confusing setup error.

If this test ever fails, the correct response is to fix the function -- NOT
to relax the assertions below. A drift between the callable and the CLI is
exactly the defect this test exists to catch.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from regression import corpus
from takeoff_fn import runner
from takeoff_fn.request import TakeoffRequest

SLUG = "s01"
NOW = 1_700_000_000_000

# Injected by the function; absent from a bare CLI run, so not compared.
INJECTED_KEYS = {"sheet_id", "source_file_id", "source_file_name", "label",
                 "plan_svg_url"}


def _skip_reason():
    """Why this test cannot run here, or None when it can.

    Two independent preconditions: the NDA corpus sheet on disk, and a
    reachable Vertex AI client. run_measurement always runs with
    skip_gemini=False, so a missing corpus sheet is not the only way to be
    unable to run this test -- someone with the corpus but no GCP
    credentials must get a skip reason that says so, not an opaque
    EnvironmentError bubbling out of setUp.
    """
    try:
        sheet = corpus.sheet_path(SLUG)
    except Exception:
        sheet = None
    if sheet is None:
        return (f"corpus sheet {SLUG} is not on disk "
                f"(see fixtures/MANIFEST.json)")
    try:
        from gemini import client as gemini_client
        gemini_client.init_client()
    except Exception as exc:
        return f"Vertex AI is not configured ({exc.__class__.__name__})"
    return None


_SKIP = _skip_reason()


class FakeBlob:
    def __init__(self, path, sink, objects):
        self.path, self._sink, self._objects = path, sink, objects

    def download_to_filename(self, local):
        Path(local).write_bytes(self._objects[self.path])

    def upload_from_filename(self, local, content_type=None):
        self._sink[self.path] = Path(local).stat().st_size

    def upload_from_string(self, data, content_type=None):
        self._sink[self.path] = len(data)


class FakeBucket:
    def __init__(self, objects):
        self.uploaded, self._objects = {}, objects

    def blob(self, path):
        return FakeBlob(path, self.uploaded, self._objects)


class FakeDoc:
    def __init__(self, data):
        self._data, self.updates = data, []

    @property
    def exists(self):
        return True

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


@unittest.skipIf(_SKIP is not None, _SKIP or "")
class TestCliEquivalence(unittest.TestCase):
    """Both pipeline runs happen ONCE for the class.

    Each run is a full detection pass plus a live Vertex AI call, and the
    region cache keys off the PDF's parent directory -- so a per-test tmpdir
    would share nothing and triple the cost. Two runs is the minimum an
    equivalence test can do. Both results are read-only here.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        # BOTH arms run against a copy outside fixtures/, never the corpus
        # sheet in place. scale/store.py resolves a corpus path to its slug
        # (corpus.slug_for_path) and loads the user's stored scale from
        # tests/ground_truth/s01.json -- s01's is a dimension-measured 1:92.2.
        # The function arm downloads into its own working directory, where no
        # slug matches, so it would fall to the viewport/text tier and the two
        # arms would disagree on scale, verified, and every room's quantities
        # for a reason that is not a wrapper defect. Copying also keeps the run
        # from writing .regions_cache/ into fixtures/.
        source = Path(cls.tmp) / "source"
        source.mkdir(parents=True, exist_ok=True)
        cls.pdf = str(shutil.copy2(corpus.sheet_path(SLUG),
                                   source / corpus.sheet_path(SLUG).name))
        cls.fn = cls._function_takeoff()
        cls.cli = cls._cli_takeoff(cls.fn["page_number"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def _cli_takeoff(cls, page_number: int) -> dict:
        """The CLI arm over the SAME page set the runner passes.

        page_indices is derived from the page count exactly as
        run_measurement derives it, rather than hardcoded to [0]: hardcoding
        silently held only because s01 happens to be a single page, and would
        compare different drawings the moment the slug changed.
        """
        from pipeline import run_extract
        from takeoff_fn import sources
        out_parent = str(Path(cls.tmp) / "cli")
        Path(out_parent).mkdir(parents=True, exist_ok=True)
        out_dir = run_extract(
            pdf_path=cls.pdf,
            page_indices=list(range(sources.page_count(cls.pdf))),
            out_parent=out_parent,
            skip_gemini=False, disable_rooms=False, disable_windows=False,
            debug=False, refresh_regions=False, write_svg=True,
            allow_scale_prompt=False, ceiling_height=None,
            door_height=None, window_height=None)
        return json.loads(
            (Path(out_dir) / "pages" / f"page_{page_number:02d}"
             / "takeoff.json").read_text(encoding="utf-8"))

    @classmethod
    def _function_takeoff(cls) -> dict:
        object_path = f"estimate_images/cus-1/est-1/{Path(cls.pdf).name}"
        db = FakeDb({
            "customerId": "cus-1", "status": "queued", "estimateId": "est-1",
            "updatedAt": NOW - 1000,
            "sourceFiles": [{"fileName": Path(cls.pdf).name,
                             "storageUrl": f"gs://b/{object_path}"}]})
        bucket = FakeBucket({object_path: Path(cls.pdf).read_bytes()})
        result = runner.run_measurement(
            TakeoffRequest("t1", "cus-1", "uid-1", debug=False),
            db=db, bucket=bucket, now_fn=lambda: NOW,
            workdir=str(Path(cls.tmp) / "fn"))
        return result.sheets[0]

    def test_the_function_and_the_cli_agree_field_for_field(self):
        self.assertEqual(set(self.fn) - set(self.cli), INJECTED_KEYS,
                         "the function added a field the CLI does not emit")
        for key in self.cli:
            with self.subTest(field=key):
                self.assertEqual(self.fn[key], self.cli[key])

    def test_warnings_stay_structured_dicts(self):
        for warning in self.fn.get("warnings", []):
            self.assertIsInstance(warning, dict)
            self.assertIn("warning_code", warning)


if __name__ == "__main__":
    unittest.main()
