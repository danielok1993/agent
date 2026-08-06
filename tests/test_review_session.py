"""What is still unreviewed in a persisted sweep, per page and category."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from regression import corpus, ground_truth as gt, run_dir
from regression.review_session import (CATEGORY_ORDER, ReviewBlocked,
                                       SweepOutputMissing, SweepOutputStale,
                                       pending)

SHEET_BYTES = b"%PDF-1.4 pretend sheet\n"


def entity(entity_id, etype, bbox, confidence=0.8, attributes=None):
    return {"entity_id": entity_id, "entity_type": etype, "bbox": list(bbox),
            "confidence": confidence, "attributes": attributes or {}}


class PendingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self._regress_out = run_dir.REGRESS_OUT
        run_dir.REGRESS_OUT = root / "regress"
        self.addCleanup(lambda: setattr(run_dir, "REGRESS_OUT", self._regress_out))

        self._truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"
        gt.TRUTH_DIR.mkdir()
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._truth_dir))

        self._sheets_dir = corpus.SHEETS_DIR
        corpus.SHEETS_DIR = root / "sheets"
        corpus.SHEETS_DIR.mkdir()
        (corpus.SHEETS_DIR / "s01.pdf").write_bytes(SHEET_BYTES)
        self.addCleanup(lambda: setattr(corpus, "SHEETS_DIR", self._sheets_dir))

        # The real sha of the bytes just written, so the fixture cannot drift
        # from a hard-coded literal.
        self.sha = corpus.sha256_of(corpus.SHEETS_DIR / "s01.pdf")

        self._manifest = corpus.MANIFEST_PATH
        corpus.MANIFEST_PATH = root / "MANIFEST.json"
        self._write_manifest(self.sha)
        self.addCleanup(lambda: setattr(corpus, "MANIFEST_PATH", self._manifest))

    def _write_manifest(self, sha):
        corpus.MANIFEST_PATH.write_text(json.dumps({
            "storage": "",
            "sheets": [{"slug": "s01", "file": "s01.pdf", "sha256": sha,
                        "pages": 2}],
        }, indent=2) + "\n", encoding="utf-8")

    def _persist(self, slug, pages: dict[int, list[dict]], swept_sha=None):
        run = run_dir.reset_slug_dir(slug) / "2026-08-06_15-19-08"
        run.mkdir(parents=True)
        (run / "sweep_meta.json").write_text(json.dumps(
            {"slug": slug, "sha256": swept_sha or self.sha}, indent=2) + "\n",
            encoding="utf-8")
        for number, entities in pages.items():
            page_dir = run / "pages" / f"page_{number:02d}"
            page_dir.mkdir(parents=True)
            (page_dir / "final_entities.json").write_text(
                json.dumps({"entities": entities, "rejected": []}),
                encoding="utf-8")
        return run

    def test_a_slug_with_no_persisted_run_raises(self):
        with self.assertRaises(SweepOutputMissing):
            pending("s01")

    def test_a_run_from_a_different_pdf_is_stale(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]},
                      swept_sha="0" * 64)
        with self.assertRaises(SweepOutputStale):
            pending("s01")

    def test_a_pdf_that_no_longer_matches_the_manifest_is_stale(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        self._write_manifest("f" * 64)
        with self.assertRaises(SweepOutputStale):
            pending("s01")

    def test_a_slug_absent_from_the_manifest_is_blocked(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        self._write_manifest(self.sha)
        corpus.MANIFEST_PATH.write_text(
            json.dumps({"storage": "", "sheets": []}, indent=2) + "\n",
            encoding="utf-8")
        with self.assertRaises(ReviewBlocked):
            pending("s01")

    def test_unreadable_ground_truth_is_blocked_not_a_crash(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ReviewBlocked):
            pending("s01")

    def test_invalid_ground_truth_is_blocked_not_a_crash(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "x", "reviewed": None,
            "pages": {"1": {"confirmed": [{"type": "door", "bbox": [1.0]}]}},
        }, indent=2), encoding="utf-8")
        with self.assertRaises(ReviewBlocked):
            pending("s01")

    def test_a_missing_sweep_meta_blocks(self):
        # Unknown provenance is not a tolerable state: there is no way to tell
        # which drawing these images show, and a wrong verdict is permanent.
        run = self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (run / "sweep_meta.json").unlink()
        with self.assertRaises(SweepOutputStale):
            pending("s01")

    def test_an_unreadable_sweep_meta_blocks(self):
        run = self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (run / "sweep_meta.json").write_text("{ not json", encoding="utf-8")
        with self.assertRaises(ReviewBlocked):
            pending("s01")

    def test_ground_truth_reviewed_against_another_pdf_blocks(self):
        # sweep.py already fails this state (status "sha_mismatch", exit 1).
        # Appending here would write verdicts the next sweep refuses to score.
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "9" * 64, "reviewed": "2026-01-01",
            "pages": {},
        }, indent=2) + "\n", encoding="utf-8")
        with self.assertRaises(SweepOutputStale):
            pending("s01")

    def test_ground_truth_with_no_recorded_sha_is_fine(self):
        # An adopted-but-unlabeled sheet: write_empty_truth sets the sha, but a
        # hand-made file may not. Absent is not a mismatch.
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": None, "reviewed": None, "pages": {},
        }, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(sorted(pending("s01")), [1])

    def test_everything_is_pending_on_an_unlabeled_sheet(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10)),
                                  entity("window_0001", "window", (20, 20, 30, 30))]})
        result = pending("s01")
        self.assertEqual(sorted(result), [1])
        self.assertEqual(sorted(result[1]), ["door", "window"])

    def test_categories_come_back_in_the_review_order(self):
        self._persist("s01", {1: [entity("window_0001", "window", (20, 20, 30, 30)),
                                  entity("room_0001", "room", (0, 0, 50, 50)),
                                  entity("door_0001", "door", (0, 0, 10, 10))]})
        self.assertEqual(list(pending("s01")[1]), ["door", "window", "room"])

    def test_an_already_confirmed_detection_is_not_pending(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        # pdf_sha256 must match the manifest's real hash here -- unlike
        # test_verdicts.py's "aaa" placeholder, this suite's setUp writes an
        # actual PDF and _check_provenance hashes it, so a mismatched literal
        # would raise SweepOutputStale before this test ever reaches the
        # already-reviewed filtering it means to exercise.
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": self.sha, "reviewed": "2026-08-06",
            "pages": {"1": {"confirmed": [
                {"type": "door", "bbox": [0.0, 0.0, 10.0, 10.0]}]}},
        }, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(pending("s01"), {})

    def test_an_already_rejected_detection_is_not_pending(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": self.sha, "reviewed": "2026-08-06",
            "pages": {"1": {"false_positives": [
                {"type": "door", "bbox": [0.0, 0.0, 10.0, 10.0]}]}},
        }, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(pending("s01"), {})

    def test_pages_with_nothing_pending_are_dropped(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))],
                              2: []})
        self.assertEqual(sorted(pending("s01")), [1])

    def test_the_category_order_covers_every_detected_type(self):
        self.assertEqual(set(CATEGORY_ORDER),
                         {"door", "window", "room", "label", "schedule"})

    def test_an_unexpected_type_still_comes_back_last(self):
        self._persist("s01", {1: [entity("mystery_0001", "mystery", (0, 0, 5, 5)),
                                  entity("door_0001", "door", (0, 0, 10, 10))]})
        self.assertEqual(list(pending("s01")[1]), ["door", "mystery"])


if __name__ == "__main__":
    unittest.main()
