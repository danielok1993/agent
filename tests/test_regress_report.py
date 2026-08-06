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

    def test_a_region_cache_miss_is_surfaced(self):
        text = render([SheetResult(slug="s07", status="ok", region_cache_miss=True)])
        self.assertIn("REGION CACHE MISS", text)
