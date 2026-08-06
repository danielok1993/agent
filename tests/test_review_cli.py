"""tools/review.py's main(): one sheet's unexpected failure must not kill
the walk over the rest, and must not report success either.

No terminal is opened here -- review_sheet is monkeypatched out entirely, so
InquirerPy never actually prompts.
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools import review


class MainExceptionIsolationTests(unittest.TestCase):
    def test_a_non_review_blocked_failure_does_not_stop_the_walk(self):
        calls = []

        def fake_review_sheet(slug):
            calls.append(slug)
            if slug == "s02":
                raise RuntimeError("boom")
            return 0

        with mock.patch.object(review, "review_sheet", side_effect=fake_review_sheet), \
             mock.patch("sys.argv", ["review.py", "s01", "s02", "s03"]):
            exit_code = review.main()

        # The walk reached every slug, including the ones after the failure.
        self.assertEqual(calls, ["s01", "s02", "s03"])
        # But it must not report success: this is a scripted caller's only
        # signal that s02 was silently skipped.
        self.assertEqual(exit_code, review.EXIT_SHEET_FAILED)
        self.assertNotEqual(review.EXIT_SHEET_FAILED, 130)

    def test_a_clean_walk_exits_zero(self):
        with mock.patch.object(review, "review_sheet", return_value=0), \
             mock.patch("sys.argv", ["review.py", "s01", "s02"]):
            exit_code = review.main()
        self.assertEqual(exit_code, 0)

    def test_keyboard_interrupt_still_stops_the_walk_immediately(self):
        # Ctrl-C is not "one sheet failed" -- it is "stop now" -- and must
        # keep its own exit code and stop-the-walk behavior even though a
        # bare RuntimeError no longer does.
        calls = []

        def fake_review_sheet(slug):
            calls.append(slug)
            if slug == "s02":
                raise KeyboardInterrupt
            return 0

        with mock.patch.object(review, "review_sheet", side_effect=fake_review_sheet), \
             mock.patch("sys.argv", ["review.py", "s01", "s02", "s03"]):
            exit_code = review.main()

        self.assertEqual(calls, ["s01", "s02"])
        self.assertEqual(exit_code, 130)


if __name__ == "__main__":
    unittest.main()
