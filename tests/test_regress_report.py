"""Report shaping and exit codes.

The sweep itself (which runs the pipeline over real sheets) is exercised by
running tools/regress.py; these tests pin the decision logic, which is where
the exit-code contract lives.
"""
import unittest

from regression.ground_truth import PageTruth, TruthItem
from regression.report import (
    EXIT_INCOMPLETE, EXIT_OK, EXIT_REGRESSION, SheetResult, exit_code, render,
)
from regression.sweep import evaluate_page


def entity(kind, bbox, eid="e0"):
    return {"entity_id": eid, "entity_type": kind, "bbox": list(bbox),
            "confidence": 0.9, "attributes": {}}


class EvaluatePageTests(unittest.TestCase):
    def test_a_still_detected_confirmed_entity_is_not_lost(self):
        page = PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(out["lost"], [])
        self.assertEqual(out["counts"]["door"], (1, 1))

    def test_a_vanished_confirmed_entity_is_lost(self):
        page = PageTruth(confirmed=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(len(out["lost"]), 1)

    def test_a_known_false_positive_that_stays_rejected_is_clean(self):
        page = PageTruth(false_positives=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(out["returned_fps"], [])

    def test_a_known_false_positive_promoted_to_an_entity_is_a_regression(self):
        page = PageTruth(false_positives=[TruthItem("door", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("door", (0, 0, 10, 10))])
        self.assertEqual(len(out["returned_fps"]), 1)

    def test_an_entity_matching_no_verdict_is_unreviewed(self):
        out = evaluate_page(PageTruth(), [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(out["unreviewed"]), 1)

    def test_a_deferred_gap_that_now_detects_is_reported_closed(self):
        page = PageTruth(deferred=[TruthItem("room", (0, 0, 10, 10))])
        out = evaluate_page(page, [entity("room", (0, 0, 10, 10))])
        self.assertEqual(len(out["closed_deferred"]), 1)
        self.assertEqual(out["unreviewed"], [],
                         "a closed gap is not also an unreviewed detection")

    def test_a_still_open_deferred_gap_reports_nothing(self):
        page = PageTruth(deferred=[TruthItem("room", (0, 0, 10, 10))])
        out = evaluate_page(page, [])
        self.assertEqual(out["closed_deferred"], [])


class ExitCodeTests(unittest.TestCase):
    def test_a_clean_sweep_exits_zero(self):
        self.assertEqual(exit_code([SheetResult(slug="s01", status="ok")]), EXIT_OK)

    def test_unreviewed_detections_do_not_fail_the_sweep(self):
        r = SheetResult(slug="s01", status="ok",
                        unreviewed=[entity("door", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_OK)

    def test_a_closed_gap_does_not_fail_the_sweep(self):
        r = SheetResult(slug="s01", status="ok",
                        closed_deferred=[TruthItem("room", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_OK)

    def test_a_lost_confirmed_entity_exits_one(self):
        r = SheetResult(slug="s01", status="regression",
                        lost=[TruthItem("door", (0, 0, 10, 10))])
        self.assertEqual(exit_code([r]), EXIT_REGRESSION)

    def test_a_sha_mismatch_exits_one(self):
        self.assertEqual(exit_code([SheetResult(slug="s07", status="sha_mismatch")]),
                         EXIT_REGRESSION)

    def test_a_labeled_but_unreviewed_sheet_exits_one(self):
        self.assertEqual(
            exit_code([SheetResult(slug="s01", status="labeled_but_unreviewed")]),
            EXIT_REGRESSION)

    def test_a_missing_sheet_exits_two(self):
        self.assertEqual(exit_code([SheetResult(slug="s14", status="missing")]),
                         EXIT_INCOMPLETE)

    def test_a_regression_outranks_a_missing_sheet(self):
        results = [SheetResult(slug="s14", status="missing"),
                   SheetResult(slug="s01", status="regression",
                               lost=[TruthItem("door", (0, 0, 10, 10))])]
        self.assertEqual(exit_code(results), EXIT_REGRESSION)


class RenderTests(unittest.TestCase):
    def test_a_lost_entity_is_named_with_its_centre(self):
        r = SheetResult(slug="s01", status="regression",
                        lost=[TruthItem("door", (800, 430, 824, 450))])
        text = render([r])
        self.assertIn("LOST door", text)
        self.assertIn("812", text)

    def test_an_unlabeled_sheet_says_so(self):
        text = render([SheetResult(slug="s09", status="unlabeled",
                                   unreviewed=[entity("door", (0, 0, 10, 10))])])
        self.assertIn("unlabeled", text)
        self.assertIn("every detection is unreviewed", text)

    def test_an_unlabeled_sheet_with_recorded_verdicts_does_not_claim_none_reviewed(self):
        # reviewed: null with populated verdict lists is a real state (a
        # hand-edited ground-truth file, or one written before it was
        # reviewed) -- it must not claim "every detection is unreviewed"
        # when counts/closed_deferred show verdicts were actually scored.
        r = SheetResult(slug="s09", status="unlabeled",
                        counts={"door": (1, 1)},
                        closed_deferred=[TruthItem("room", (0, 0, 10, 10))])
        text = render([r])
        self.assertIn("unlabeled", text)
        self.assertNotIn("every detection is unreviewed", text)

    def test_a_labeled_but_unreviewed_sheet_names_the_file_to_restore(self):
        text = render([SheetResult(slug="s01", status="labeled_but_unreviewed")])
        self.assertIn("labeled", text)
        self.assertIn("tests/ground_truth/s01.json", text)

    def test_a_region_cache_miss_is_surfaced(self):
        text = render([SheetResult(slug="s07", status="ok", region_cache_miss=True)])
        self.assertIn("REGION CACHE MISS", text)


class ReviewLineIdentityTests(unittest.TestCase):
    def _result(self, **kwargs):
        return SheetResult(
            slug="s01",
            unreviewed=[{"entity_id": "door_0007", "entity_type": "door",
                         "bbox": [1200.0, 870.0, 1240.0, 900.0], "confidence": 0.82}],
            **kwargs)

    def test_review_line_names_the_entity_id(self):
        out = render([self._result()])
        self.assertIn("door_0007", out)

    def test_review_line_still_carries_confidence_and_centre(self):
        out = render([self._result()])
        self.assertIn("conf 0.82", out)
        self.assertIn("(1220,885)", out)

    def test_review_line_falls_back_to_the_type_without_an_id(self):
        result = SheetResult(slug="s01",
                             unreviewed=[{"entity_type": "window",
                                          "bbox": [0.0, 0.0, 10.0, 10.0]}])
        out = render([result])
        self.assertIn("REVIEW new window", out)

    def test_run_dir_is_printed_when_there_are_review_items(self):
        out = render([self._result(run_dir="outputs/regress/s01/2026-08-06_15-19-08")])
        self.assertIn("outputs/regress/s01/2026-08-06_15-19-08", out)

    def test_run_dir_is_not_printed_when_nothing_needs_review(self):
        clean = SheetResult(slug="s01", status="ok",
                            run_dir="outputs/regress/s01/2026-08-06_15-19-08")
        self.assertNotIn("outputs/regress", render([clean]))
