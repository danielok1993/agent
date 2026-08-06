"""tools/review.py's `_pick` / `review_sheet`, driven through the real
InquirerPy prompts -- headlessly.

This is the test the C1 review finding said was missing: the whole point of
`_pick` is what happens when a labeler presses Enter with nothing ticked
(they cannot judge this screen, so postponing must cost nothing), and that
behavior lives entirely inside `.execute()` calls that `test_review_cli.py`
monkeypatches away. A prompt is not a black box here -- it is driven with
real keystrokes and its real result is asserted on.

No TTY is required. `prompt_toolkit` supports running its `Application` (what
every InquirerPy prompt boils down to) against a `create_pipe_input()` pipe
and a `DummyOutput()`, all inside a `create_app_session(...)` context --
this is documented, standard prompt_toolkit testing machinery, not a hack
specific to this repo.

THE ONE TRICK THAT MAKES IT WORK: feed one chunk of keystrokes per prompt,
from a background thread, with a short pause between chunks. `review_sheet`
opens several `Application`s in sequence (one per `_pick` call, one per
`_shape_and_note` sub-prompt); a single `send_text()` of every keystroke
up front is swallowed whole by the FIRST `Application` before the second
one even exists to read the rest. One chunk per prompt is what lets each
`Application` see only the keystrokes meant for it.

`review_sheet` itself runs on a second thread (`_run_headless`'s "worker"),
because prompt_toolkit's `Application.run()` happily runs outside the main
thread (it just skips installing SIGINT handling there -- see
`Application.run_async`'s own `in_main_thread()` check) and because the test
thread needs to be free to feed keystrokes concurrently. `worker.join(timeout)`
is the guard against a hang: if a chunk sequence under- or over-shoots what a
prompt is waiting for, the join times out and the test fails loudly with an
AssertionError instead of blocking CI forever.

Key chunks used below, in prompt_toolkit's own escape sequences:
  "\\r"          Enter
  " "            Space (checkbox's toggle key, see CLAUDE.md / the guide)
  "\\x1b[B"      Down arrow (move the highlighted choice down one)
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from regression import corpus, ground_truth as gt, run_dir
from tools import review

SHEET_BYTES = b"%PDF-1.4 pretend sheet\n"

# Enter, with nothing ticked.
ENTER = "\r"


def _tick(downs: int) -> str:
    """Down-arrow `downs` times, Space to tick, Enter to submit."""
    return "\x1b[B" * downs + " \r"


def entity(entity_id, etype, bbox, confidence=0.8, attributes=None):
    return {"entity_id": entity_id, "entity_type": etype, "bbox": list(bbox),
            "confidence": confidence, "attributes": attributes or {}}


def _run_headless(target, chunks: list[str], timeout: float = 10.0):
    """Run `target()` inside a headless prompt_toolkit session.

    Feeds `chunks` from a background thread, one `send_text()` call per
    prompt `target()` is expected to open, each after a short pause so the
    prompt that should consume it has actually been created. Raises
    AssertionError (rather than hanging) if `target()` does not finish within
    `timeout` seconds -- an InquirerPy prompt left waiting on a chunk that
    never comes must fail the test, not the CI job.
    """
    with create_pipe_input() as pipe_input:
        box: dict = {}

        def feed():
            for chunk in chunks:
                time.sleep(0.05)
                pipe_input.send_text(chunk)

        def run():
            with create_app_session(input=pipe_input, output=DummyOutput()):
                box["value"] = target()

        worker = threading.Thread(target=run, daemon=True)
        feeder = threading.Thread(target=feed, daemon=True)
        worker.start()
        feeder.start()
        worker.join(timeout)
        if worker.is_alive():
            raise AssertionError(
                f"headless run did not finish within {timeout}s -- an "
                f"InquirerPy prompt is stuck waiting on input (chunks: "
                f"{chunks!r})")
        feeder.join(1.0)
        return box.get("value")


class _HeadlessReviewSheetTests(unittest.TestCase):
    """Shared fixture: one fake corpus sheet with a persisted sweep run.

    Mirrors tests/test_review_session.py's PendingTests setUp -- same
    monkeypatching approach (module attributes, not `from ... import NAME`,
    per CLAUDE.md's regression-testing gotcha table) -- so `review_sheet`'s
    real `pending()` / `record_verdicts()` machinery runs against a temp
    directory, never `tests/ground_truth/` or `fixtures/MANIFEST.json`.
    """

    slug = "s01"

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
        (corpus.SHEETS_DIR / f"{self.slug}.pdf").write_bytes(SHEET_BYTES)
        self.addCleanup(lambda: setattr(corpus, "SHEETS_DIR", self._sheets_dir))

        self.sha = corpus.sha256_of(corpus.SHEETS_DIR / f"{self.slug}.pdf")

        self._manifest = corpus.MANIFEST_PATH
        corpus.MANIFEST_PATH = root / "MANIFEST.json"
        corpus.MANIFEST_PATH.write_text(json.dumps({
            "storage": "",
            "sheets": [{"slug": self.slug, "file": f"{self.slug}.pdf",
                       "sha256": self.sha, "pages": 1}],
        }, indent=2) + "\n", encoding="utf-8")
        self.addCleanup(lambda: setattr(corpus, "MANIFEST_PATH", self._manifest))

    def _persist(self, pages: dict[int, list[dict]]) -> Path:
        run = run_dir.reset_slug_dir(self.slug) / "2026-08-06_15-19-08"
        run.mkdir(parents=True)
        (run / "sweep_meta.json").write_text(json.dumps(
            {"slug": self.slug, "sha256": self.sha}, indent=2) + "\n",
            encoding="utf-8")
        for number, entities in pages.items():
            page_dir = run / "pages" / f"page_{number:02d}"
            page_dir.mkdir(parents=True)
            (page_dir / "final_entities.json").write_text(
                json.dumps({"entities": entities, "rejected": []}),
                encoding="utf-8")
        return run

    def _review(self, chunks: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return _run_headless(lambda: review.review_sheet(self.slug), chunks)


class EnterWithNothingTickedTests(_HeadlessReviewSheetTests):
    """The C1 regression test.

    Against the old `inquirer.fuzzy(multiselect=True)` implementation this
    must FAIL: fuzzy's `_handle_enter` captures the currently-highlighted
    choice when nothing was explicitly toggled, so plain Enter on both passes
    confirms the first door and then rejects the second -- two fabricated
    verdicts from a labeler who never ticked anything. Verified by hand: with
    `_pick` reverted to the old fuzzy call, this test fails with
    `truth.pages == {1: door_0001 confirmed, door_0002 false_positive}`
    instead of `{}`.
    """

    def test_enter_on_every_prompt_records_nothing(self):
        self._persist({1: [entity("door_0001", "door", (0, 0, 10, 10)),
                           entity("door_0002", "door", (20, 20, 30, 30))]})

        recorded = self._review([ENTER, ENTER])

        self.assertEqual(recorded, 0)
        truth = gt.load_truth(self.slug)
        self.assertEqual(truth.pages, {})
        # Nothing was written at all -- not even an empty labeled file.
        self.assertFalse((gt.TRUTH_DIR / f"{self.slug}.json").exists())


class SentinelOverridesOtherTicksTests(_HeadlessReviewSheetTests):
    def test_ticking_the_sentinel_records_nothing_even_with_other_ticks(self):
        self._persist({1: [entity("door_0001", "door", (0, 0, 10, 10)),
                           entity("door_0002", "door", (20, 20, 30, 30))]})

        # Pass 1: tick the sentinel (highlighted by default, index 0) AND
        # door_0001 (one down arrow, index 1) in the same screen.
        # Pass 2: nothing ticked.
        recorded = self._review([" " + _tick(downs=1), ENTER])

        self.assertEqual(recorded, 0)
        truth = gt.load_truth(self.slug)
        self.assertEqual(truth.pages, {})


class DeliberateVerdictsTests(_HeadlessReviewSheetTests):
    def test_pass1_tick_confirms_pass2_tick_rejects_neither_stays_pending(self):
        self._persist({1: [entity("door_0001", "door", (0, 0, 10, 10)),
                           entity("door_0002", "door", (20, 20, 30, 30)),
                           entity("door_0003", "door", (40, 40, 50, 50))]})

        # Pass 1 choices: [sentinel, door_0001, door_0002, door_0003].
        # Tick door_0001 (one down arrow from the sentinel).
        pass1 = _tick(downs=1)
        # Pass 2 choices (leftovers): [sentinel, door_0002, door_0003].
        # Tick door_0002 (one down arrow from the sentinel). door_0003 is
        # left untouched by either pass.
        pass2 = _tick(downs=1)

        recorded = self._review([pass1, pass2])

        self.assertEqual(recorded, 2)
        truth = gt.load_truth(self.slug)
        page = truth.pages[1]
        self.assertEqual(len(page.confirmed), 1)
        self.assertEqual(tuple(page.confirmed[0].bbox), (0.0, 0.0, 10.0, 10.0))
        self.assertEqual(len(page.false_positives), 1)
        self.assertEqual(tuple(page.false_positives[0].bbox), (20.0, 20.0, 30.0, 30.0))
        # door_0003 is in neither list, and still shows up as pending.
        still_pending = review.pending(self.slug)
        pending_bboxes = {tuple(e["bbox"]) for e in still_pending[1]["door"]}
        self.assertEqual(pending_bboxes, {(40.0, 40.0, 50.0, 50.0)})


class SentinelIdentityTests(unittest.TestCase):
    """Not headless -- just the invariant that makes the sentinel safe."""

    def test_sentinel_value_cannot_collide_with_a_real_entity_id(self):
        # Real entity ids are always "<type>_<digits>" (door_0007, room_0012).
        self.assertIsNone(re.fullmatch(r"[a-z]+_\d+", review._SKIP_ALL))


if __name__ == "__main__":
    unittest.main()
