import unittest
from unittest import mock

from takeoff_fn.errors import NotFound, PermissionDenied, TakeoffFnError
from takeoff_fn.request import TakeoffRequest
from takeoff_fn.runner import RunResult


class TestBuildResponse(unittest.TestCase):
    def setUp(self):
        import main
        self.main = main

    def test_the_response_carries_sheets_artifacts_and_run(self):
        request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)
        result = RunResult(
            sheets=[{"sheet_id": "sheet_00_01", "page_number": 1}],
            artifacts={"prefix": "customers/cus-1/takeoffs/t1", "bySheet": {}},
            run={"pagesMeasured": 1})
        body = self.main.build_response(request, result)
        self.assertEqual(body["takeoffId"], "t1")
        self.assertEqual(body["sheets"][0]["sheet_id"], "sheet_00_01")
        self.assertEqual(body["artifacts"]["prefix"],
                         "customers/cus-1/takeoffs/t1")
        self.assertEqual(body["run"]["pagesMeasured"], 1)

    def test_the_response_does_not_leak_the_customer_id(self):
        # The caller already knows its own tenant; echoing it back is noise
        # that also ends up in browser logs.
        request = TakeoffRequest("t1", "cus-1", "uid-1", debug=False)
        body = self.main.build_response(
            request, RunResult(sheets=[], artifacts={}, run={}))
        self.assertNotIn("customerId", body)


class TestErrorMapping(unittest.TestCase):
    def setUp(self):
        import main
        from firebase_functions import https_fn
        self.main, self.https_fn = main, https_fn

    def test_domain_errors_map_to_their_callable_codes(self):
        cases = [
            (NotFound("x"), self.https_fn.FunctionsErrorCode.NOT_FOUND),
            (PermissionDenied("x"),
             self.https_fn.FunctionsErrorCode.PERMISSION_DENIED),
        ]
        for exc, expected in cases:
            with self.subTest(exc=type(exc).__name__):
                self.assertEqual(self.main.error_code(exc), expected)

    def test_an_unknown_domain_error_falls_back_to_internal(self):
        class Weird(TakeoffFnError):
            code = "not-a-real-code"
        self.assertEqual(self.main.error_code(Weird("x")),
                         self.https_fn.FunctionsErrorCode.INTERNAL)


class FakeAuth:
    def __init__(self, uid, token):
        self.uid = uid
        self.token = token


class FakeReq:
    def __init__(self, data, auth):
        self.data = data
        self.auth = auth


class TestHandlerWiring(unittest.TestCase):
    def setUp(self):
        import main
        from firebase_functions import https_fn
        self.main, self.https_fn = main, https_fn
        self.req = FakeReq({"takeoffId": "t1"},
                           FakeAuth("uid-1", {"customerId": "cus-1"}))

    def test_the_handler_passes_the_parsed_request_and_returns_the_response(self):
        from takeoff_fn.runner import RunResult
        seen = {}

        def _fake_run(request, *, db, bucket):
            seen["request"], seen["db"], seen["bucket"] = request, db, bucket
            return RunResult(sheets=[{"sheet_id": "sheet_00_01"}],
                             artifacts={"prefix": "p"}, run={"pagesMeasured": 1})

        with mock.patch.object(self.main, "run_measurement", _fake_run):
            body = self.main._measure(self.req, "DB", "BUCKET")

        self.assertEqual(seen["request"].takeoff_id, "t1")
        self.assertEqual(seen["request"].customer_id, "cus-1")
        self.assertEqual(seen["request"].user_id, "uid-1")
        self.assertEqual((seen["db"], seen["bucket"]), ("DB", "BUCKET"))
        self.assertEqual(body["takeoffId"], "t1")
        self.assertEqual(body["sheets"][0]["sheet_id"], "sheet_00_01")

    def test_an_unauthenticated_request_never_reaches_the_runner(self):
        called = []
        with mock.patch.object(self.main, "run_measurement",
                               lambda *a, **k: called.append(1)):
            with self.assertRaises(self.https_fn.HttpsError) as raised:
                self.main._measure(FakeReq({"takeoffId": "t1"}, None),
                                   "DB", "BUCKET")
        self.assertEqual(raised.exception.code,
                         self.https_fn.FunctionsErrorCode.UNAUTHENTICATED)
        self.assertEqual(called, [])

    def test_a_domain_error_from_the_runner_keeps_its_own_code(self):
        # Regression guard: if the generic `except Exception` were ordered
        # before `except TakeoffFnError`, this would collapse to INTERNAL.
        from takeoff_fn.errors import NotFound

        def _boom(request, *, db, bucket):
            raise NotFound("No such takeoff")

        with mock.patch.object(self.main, "run_measurement", _boom):
            with self.assertRaises(self.https_fn.HttpsError) as raised:
                self.main._measure(self.req, "DB", "BUCKET")
        self.assertEqual(raised.exception.code,
                         self.https_fn.FunctionsErrorCode.NOT_FOUND)

    def test_an_unexpected_error_becomes_internal_and_keeps_its_cause(self):
        def _boom(request, *, db, bucket):
            raise RuntimeError("detector exploded")

        with mock.patch.object(self.main, "run_measurement", _boom):
            with self.assertRaises(self.https_fn.HttpsError) as raised:
                self.main._measure(self.req, "DB", "BUCKET")
        self.assertEqual(raised.exception.code,
                         self.https_fn.FunctionsErrorCode.INTERNAL)
        self.assertIsInstance(raised.exception.__cause__, RuntimeError)
        self.assertIn("detector exploded", str(raised.exception.__cause__))


if __name__ == "__main__":
    unittest.main()
