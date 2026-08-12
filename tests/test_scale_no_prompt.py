"""Unattended runs must never stop to ask for a scale.

sys.stdin.isatty() cannot carry this guarantee on its own: regress.py calls
run_extract in-process and batch_extract spawns a child without redirecting
stdin, so both inherit a real terminal when started from one.
"""
import inspect
import subprocess
import unittest
from unittest import mock

import batch_extract
import regression.sweep as sweep
from pipeline import run_extract


class TestRunExtractDefault(unittest.TestCase):
    def test_prompting_is_on_by_default(self):
        # An interactive `app.py extract` is the one caller that should ask.
        default = inspect.signature(run_extract).parameters["allow_scale_prompt"].default
        self.assertIs(default, True)


class TestSweepNeverPrompts(unittest.TestCase):
    def test_sweep_disables_scale_prompting(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 1, "out", False)
        self.assertIs(fake.call_args.kwargs["allow_scale_prompt"], False)

    def test_sweep_still_runs_offline(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 1, "out", False)
        self.assertIs(fake.call_args.kwargs["skip_gemini"], True)

    def test_sweep_passes_every_page(self):
        with mock.patch.object(sweep, "run_extract") as fake:
            sweep._extract_for_sweep("a.pdf", 3, "out", False)
        self.assertEqual(fake.call_args.args[1], [0, 1, 2])


class TestBatchNeverPrompts(unittest.TestCase):
    def test_the_argv_disables_scale_prompting(self):
        cmd = batch_extract.build_extract_command(
            "a.pdf", enable_windows=True, enable_walls=True, use_gemini=False)
        self.assertIn("--no-scale-prompt", cmd)

    def test_the_flag_is_present_regardless_of_other_options(self):
        cmd = batch_extract.build_extract_command(
            "a.pdf", enable_windows=False, enable_walls=False, use_gemini=True)
        self.assertIn("--no-scale-prompt", cmd)

    def test_the_child_gets_no_stdin(self):
        # Belt and braces: even if a future prompt escapes the flag, a child
        # with no stdin fails the tty gate instead of hanging the batch.
        captured = {}

        class FakeProc:
            returncode = 0

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def communicate(self, timeout=None):
                return ("", "")

        def fake_popen(cmd, **kwargs):
            captured.update(kwargs)
            return FakeProc()

        with mock.patch.object(subprocess, "Popen", fake_popen):
            batch_extract._run_with_group_kill(["true"], 1.0)
        self.assertIs(captured.get("stdin"), subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
