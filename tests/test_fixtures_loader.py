"""The corpus loader resolves slugs against the committed manifest.

Every test builds its own temporary fixtures tree and points the module at it,
so the suite passes whether or not the real corpus has been downloaded.
"""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as fx
import tests.fixtures as fixtures_mod
from tests.fixtures import require_sheet


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "sheets" / "s01-floor-plans.pdf").write_bytes(b"%PDF-1.4 fake")
        (root / "MANIFEST.json").write_text(json.dumps({
            "storage": "ask the maintainer",
            "sheets": [
                {"slug": "s01", "file": "s01-floor-plans.pdf",
                 "sha256": "0" * 64, "pages": 1, "tier": "reference"},
                {"slug": "s02", "file": "s02-working-drawing-wd03.pdf",
                 "sha256": "1" * 64, "pages": 1, "tier": "reference"},
            ],
        }))
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = root
        fx.SHEETS_DIR = root / "sheets"
        fx.MANIFEST_PATH = root / "MANIFEST.json"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved
        # test_require_sheet_skips_when_the_file_is_absent trips the one-shot
        # warning flag; reset it so it doesn't stay burned for the rest of
        # the suite (which would silently swallow a genuinely-missing corpus
        # elsewhere) and doesn't print a false alarm about this temp dir.
        fixtures_mod._WARNED = False
        self.tmp.cleanup()

    def test_manifest_sheets_are_returned_in_slug_order(self):
        self.assertEqual([s["slug"] for s in fx.manifest_sheets()], ["s01", "s02"])

    def test_sheet_entry_looks_up_by_slug(self):
        self.assertEqual(fx.sheet_entry("s02")["file"], "s02-working-drawing-wd03.pdf")

    def test_sheet_entry_is_none_for_an_unknown_slug(self):
        self.assertIsNone(fx.sheet_entry("s99"))

    def test_sheet_path_resolves_a_downloaded_sheet(self):
        self.assertTrue(fx.sheet_path("s01").exists())

    def test_sheet_path_is_none_when_the_file_was_never_downloaded(self):
        self.assertIsNone(fx.sheet_path("s02"))

    def test_sha256_of_hashes_file_bytes(self):
        p = fx.sheet_path("s01")
        self.assertEqual(len(fx.sha256_of(p)), 64)
        self.assertEqual(fx.sha256_of(p), fx.sha256_of(p))

    def test_require_sheet_skips_when_the_file_is_absent(self):
        with self.assertRaises(unittest.SkipTest):
            require_sheet(self, "s02")

    def test_require_sheet_returns_the_path_when_present(self):
        self.assertEqual(require_sheet(self, "s01").name, "s01-floor-plans.pdf")

    def test_missing_manifest_reads_as_an_empty_corpus(self):
        fx.MANIFEST_PATH = Path(self.tmp.name) / "nope.json"
        self.assertEqual(fx.manifest_sheets(), [])
