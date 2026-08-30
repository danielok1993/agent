import unittest

from takeoff_fn.errors import InvalidArgument, PermissionDenied, Unauthenticated
from takeoff_fn.request import TakeoffRequest, parse_request


class TestParseRequest(unittest.TestCase):
    def test_a_valid_payload_parses(self):
        req = parse_request(
            {"takeoffId": "t1"}, "uid-1", {"customerId": "cus-1"})
        self.assertEqual(
            req, TakeoffRequest(takeoff_id="t1", customer_id="cus-1",
                                user_id="uid-1", debug=False))

    def test_debug_defaults_false_and_is_honoured_when_true(self):
        self.assertFalse(parse_request(
            {"takeoffId": "t1"}, "u", {"customerId": "c"}).debug)
        self.assertTrue(parse_request(
            {"takeoffId": "t1", "debug": True}, "u", {"customerId": "c"}).debug)

    def test_no_auth_is_unauthenticated(self):
        with self.assertRaises(Unauthenticated):
            parse_request({"takeoffId": "t1"}, None, None)

    def test_a_token_without_a_customer_claim_is_denied(self):
        with self.assertRaises(PermissionDenied):
            parse_request({"takeoffId": "t1"}, "uid-1", {})

    def test_a_missing_or_blank_takeoff_id_is_invalid(self):
        for data in ({}, {"takeoffId": ""}, {"takeoffId": "   "}, None):
            with self.subTest(data=data):
                with self.assertRaises(InvalidArgument):
                    parse_request(data, "uid-1", {"customerId": "cus-1"})

    def test_a_non_string_takeoff_id_is_invalid(self):
        with self.assertRaises(InvalidArgument):
            parse_request({"takeoffId": 7}, "uid-1", {"customerId": "cus-1"})

    def test_a_customer_id_in_the_payload_is_ignored(self):
        # The tenant is the verified claim, never the caller's word for it.
        req = parse_request({"takeoffId": "t1", "customerId": "other"},
                            "uid-1", {"customerId": "cus-1"})
        self.assertEqual(req.customer_id, "cus-1")


if __name__ == "__main__":
    unittest.main()
