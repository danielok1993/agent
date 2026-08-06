"""run_heuristics emits per-stage wall-clock timings on its module logger.

The 2026-08-04 batch-timeout investigation attributed s16's >58-minute
detection run to "somewhere pre-rooms" only via stack sampling; stage timings
make the attribution reproducible without root.
"""
import unittest

from models import PageData
from detection import run_heuristics


class TestStageTimingLogs(unittest.TestCase):
    def test_each_stage_logs_a_duration(self):
        pd = PageData(page_number=1, width_px=400.0, height_px=400.0)
        with self.assertLogs("detection.orchestrator", level="INFO") as cm:
            run_heuristics(pd, plumber_tables=[])
        logged = "\n".join(cm.output)
        for stage in ("doors", "windows", "wall_network", "cross_validate",
                      "rooms", "labels", "schedules"):
            self.assertIn(stage, logged)
        self.assertIn("s", logged)


if __name__ == "__main__":
    unittest.main()
