"""The corpus verifier classifies each manifest sheet against the disk."""
import json
import tempfile
import unittest
from pathlib import Path

import regression.corpus as fx
from tools.fetch_fixtures import check_corpus


class CheckCorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sheets").mkdir()
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH)
        fx.FIXTURES_DIR = self.root
        fx.SHEETS_DIR = self.root / "sheets"
        fx.MANIFEST_PATH = self.root / "MANIFEST.json"

    def tearDown(self):
        fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH = self._saved
        self.tmp.cleanup()

    def _write(self, name, data=b"%PDF-1.4 real"):
        (self.root / "sheets" / name).write_bytes(data)
        return fx.sha256_of(self.root / "sheets" / name)

    def _manifest(self, sheets):
        fx.MANIFEST_PATH.write_text(json.dumps({"storage": "the bundle", "sheets": sheets}))

    def test_a_matching_sheet_is_present(self):
        digest = self._write("s01-a.pdf")
        self._manifest([{"slug": "s01", "file": "s01-a.pdf", "sha256": digest,
                         "pages": 1, "tier": "reference"}])
        status = check_corpus()
        self.assertEqual(status.present, ["s01"])
        self.assertTrue(status.ok)

    def test_a_sheet_absent_from_disk_is_missing(self):
        self._manifest([{"slug": "s02", "file": "s02-b.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "corpus"}])
        status = check_corpus()
        self.assertEqual(status.missing, ["s02"])
        self.assertFalse(status.ok)

    def test_wrong_bytes_are_mismatched_not_present(self):
        self._write("s03-c.pdf", b"%PDF-1.4 revised")
        self._manifest([{"slug": "s03", "file": "s03-c.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "corpus"}])
        status = check_corpus()
        self.assertEqual(status.mismatched, ["s03"])
        self.assertEqual(status.present, [])

    def test_a_pdf_not_in_the_manifest_is_untracked(self):
        self._write("stray.pdf")
        self._manifest([])
        self.assertEqual(check_corpus().untracked, ["stray.pdf"])

    def test_a_retired_sheet_is_not_reported_missing(self):
        self._manifest([{"slug": "s04", "file": "s04-d.pdf", "sha256": "0" * 64,
                         "pages": 1, "tier": "retired"}])
        status = check_corpus()
        self.assertEqual(status.missing, [])
        self.assertTrue(status.ok)
