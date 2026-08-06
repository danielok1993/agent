"""Where a sweep leaves its output, and how review tooling finds it again."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from regression import run_dir


class RunDirTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._original = run_dir.REGRESS_OUT
        run_dir.REGRESS_OUT = Path(self._tmp.name) / "regress"
        self.addCleanup(lambda: setattr(run_dir, "REGRESS_OUT", self._original))

    def test_slug_dir_is_under_the_regress_root(self):
        self.assertEqual(run_dir.slug_dir("s01").parent, run_dir.REGRESS_OUT)
        self.assertEqual(run_dir.slug_dir("s01").name, "s01")

    def test_reset_creates_the_directory(self):
        path = run_dir.reset_slug_dir("s01")
        self.assertTrue(path.is_dir())

    def test_reset_wipes_a_previous_sweep(self):
        stale = run_dir.reset_slug_dir("s01") / "2026-01-01_00-00-00"
        stale.mkdir()
        (stale / "render.png").write_bytes(b"stale")

        run_dir.reset_slug_dir("s01")

        self.assertFalse(stale.exists())
        self.assertEqual(list(run_dir.slug_dir("s01").iterdir()), [])

    def test_latest_run_is_none_before_any_sweep(self):
        self.assertIsNone(run_dir.latest_run("s01"))

    def test_latest_run_finds_the_single_child(self):
        child = run_dir.reset_slug_dir("s01") / "2026-08-06_15-19-08"
        child.mkdir()
        self.assertEqual(run_dir.latest_run("s01"), child)

    def test_latest_run_takes_the_newest_when_several_exist(self):
        # reset_slug_dir normally guarantees at most one child, but an
        # interrupted sweep can leave a stale sibling behind. Newest wins
        # rather than crashing or picking arbitrarily.
        base = run_dir.reset_slug_dir("s01")
        (base / "2026-08-01_09-00-00").mkdir()
        newest = base / "2026-08-06_15-19-08"
        newest.mkdir()
        self.assertEqual(run_dir.latest_run("s01"), newest)

    def test_latest_run_ignores_files(self):
        base = run_dir.reset_slug_dir("s01")
        (base / "notes.txt").write_text("x")
        self.assertIsNone(run_dir.latest_run("s01"))


if __name__ == "__main__":
    unittest.main()
