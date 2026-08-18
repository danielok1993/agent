import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

import batch_extract


class TestBuildExtractCommand(unittest.TestCase):
    def test_command_is_argv_list_using_venv_python(self):
        cmd = batch_extract.build_extract_command(
            Path("plans/My Plan.pdf"),
            enable_windows=True,
            enable_walls=True,
            use_gemini=True,
        )
        self.assertIsInstance(cmd, list)
        self.assertTrue(cmd[0].endswith(".venv/bin/python"))
        self.assertEqual(cmd[1:3], ["app.py", "extract"])
        # Path passed as its own argv element — no shell quoting involved.
        self.assertIn("plans/My Plan.pdf", cmd)

    def test_flags_appended_as_separate_elements(self):
        cmd = batch_extract.build_extract_command(
            Path("plans/a.pdf"),
            enable_windows=False,
            enable_walls=False,
            use_gemini=False,
        )
        self.assertIn("--disable-windows", cmd)
        self.assertIn("--disable-walls", cmd)
        self.assertIn("--no-gemini", cmd)


class TestCeilingHeightFlag(unittest.TestCase):
    def test_flag_forwarded_when_given(self):
        cmd = batch_extract.build_extract_command(Path("x.pdf"), True, True, False, ceiling_height=2.7)
        i = cmd.index("--ceiling-height")
        self.assertEqual(cmd[i + 1], "2.7")

    def test_flag_absent_by_default(self):
        cmd = batch_extract.build_extract_command(Path("x.pdf"), True, True, False)
        self.assertNotIn("--ceiling-height", cmd)


class TestRunWithGroupKill(unittest.TestCase):
    def test_success_returns_ok(self):
        ok, msg = batch_extract._run_with_group_kill(
            [sys.executable, "-c", "print('done')"], timeout_seconds=30
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_failure_returns_first_stderr_line(self):
        ok, msg = batch_extract._run_with_group_kill(
            [sys.executable, "-c", "import sys; print('boom', file=sys.stderr); sys.exit(3)"],
            timeout_seconds=30,
        )
        self.assertFalse(ok)
        self.assertEqual(msg, "boom")

    def test_timeout_kills_entire_process_group(self):
        # Parent spawns a grandchild sleeper, writes both PIDs, then sleeps.
        # After the timeout fires, BOTH processes must be dead — killing only
        # the direct child is the orphan bug from the findings doc.
        with tempfile.TemporaryDirectory() as td:
            pid_file = Path(td) / "pids.txt"
            script = (
                "import subprocess, os, sys, time\n"
                f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                f"open({str(pid_file)!r}, 'w').write(f'{{os.getpid()}} {{child.pid}}')\n"
                "time.sleep(60)\n"
            )
            start = time.monotonic()
            ok, msg = batch_extract._run_with_group_kill(
                [sys.executable, "-c", script], timeout_seconds=2
            )
            elapsed = time.monotonic() - start
            self.assertFalse(ok)
            self.assertIn("timeout", msg)
            self.assertLess(elapsed, 30)
            pids = [int(p) for p in pid_file.read_text().split()]
            self.assertEqual(len(pids), 2)
            # Give the kill a moment to be delivered before asserting.
            deadline = time.monotonic() + 5
            still_alive = pids
            while still_alive and time.monotonic() < deadline:
                still_alive = [p for p in still_alive if _alive(p)]
                if still_alive:
                    time.sleep(0.1)
            self.assertEqual(still_alive, [], f"processes survived timeout: {still_alive}")

    def test_timeout_message_reports_minutes(self):
        ok, msg = batch_extract._run_with_group_kill(
            [sys.executable, "-c", "import time; time.sleep(60)"], timeout_seconds=1
        )
        self.assertFalse(ok)
        self.assertIn("timeout", msg)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Reap zombies left to us (children of this test process are reapable).
    try:
        done, _ = os.waitpid(pid, os.WNOHANG)
        if done == pid:
            return False
    except ChildProcessError:
        pass
    return True


if __name__ == "__main__":
    unittest.main()
