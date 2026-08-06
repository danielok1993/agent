"""Adopting a new sheet into the corpus."""
import json
import tempfile
import unittest
from pathlib import Path

import fitz

import regression.corpus as fx
import regression.ground_truth as gt
from tools.add_sheet import adopt, next_slug


def make_pdf(path: Path, text: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=200, height=400)
    page.insert_text((20, 40), text)
    doc.save(str(path))
    doc.close()


class NextSlugTests(unittest.TestCase):
    def test_an_empty_corpus_starts_at_s01(self):
        self.assertEqual(next_slug([]), "s01")

    def test_the_next_slug_follows_the_highest_in_use(self):
        self.assertEqual(next_slug([{"slug": "s01"}, {"slug": "s20"}]), "s21")

    def test_gaps_are_not_reused(self):
        self.assertEqual(next_slug([{"slug": "s01"}, {"slug": "s03"}]), "s04")


class AdoptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "sheets").mkdir()
        (root / "truth").mkdir()
        (root / "MANIFEST.json").write_text(json.dumps({"storage": "the bundle",
                                                        "sheets": []}))
        self._saved = (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH, gt.TRUTH_DIR)
        fx.FIXTURES_DIR, fx.SHEETS_DIR = root, root / "sheets"
        fx.MANIFEST_PATH, gt.TRUTH_DIR = root / "MANIFEST.json", root / "truth"
        self.incoming = root / "incoming.pdf"
        make_pdf(self.incoming, "a new sheet")

    def tearDown(self):
        (fx.FIXTURES_DIR, fx.SHEETS_DIR, fx.MANIFEST_PATH, gt.TRUTH_DIR) = self._saved
        self.tmp.cleanup()

    def test_the_file_is_renamed_to_its_slug(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        self.assertEqual(entry["file"], "s01-existing-floor-plans.pdf")
        self.assertTrue((fx.SHEETS_DIR / entry["file"]).exists())

    def test_the_manifest_records_sha_and_page_count(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        self.assertEqual(entry["pages"], 1)
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(fx.manifest_sheets()[0]["slug"], "s01")

    def test_an_empty_ground_truth_file_is_created(self):
        adopt(self.incoming, "existing-floor-plans")
        self.assertFalse(gt.load_truth("s01").is_labeled)

    def test_a_new_sheet_is_tier_corpus(self):
        self.assertEqual(adopt(self.incoming, "existing-floor-plans")["tier"], "corpus")

    def test_re_adopting_the_same_bytes_is_refused(self):
        entry = adopt(self.incoming, "existing-floor-plans")
        # Same bytes arriving under a different path — the sha dedupe must catch it.
        again = fx.FIXTURES_DIR / "again.pdf"
        again.write_bytes((fx.SHEETS_DIR / entry["file"]).read_bytes())
        with self.assertRaises(ValueError) as ctx:
            adopt(again, "duplicate")
        self.assertIn("s01", str(ctx.exception))

    def test_a_description_with_spaces_is_kebab_cased(self):
        entry = adopt(self.incoming, "Existing Floor Plans")
        self.assertEqual(entry["file"], "s01-existing-floor-plans.pdf")
