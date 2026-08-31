import unittest

from takeoff_fn.errors import InvalidArgument, PermissionDenied, Unauthenticated
from takeoff_fn.request import TakeoffRequest, parse_request


class TestParseRequest(unittest.TestCase):
    def test_a_valid_payload_parses(self):
        req = parse_request(
            {"takeoffId": "t1"}, "uid-1", {"customerId": "cus-1"})
        self.assertEqual(
            req, TakeoffRequest(takeoff_id="t1", customer_id="cus-1",
                                user_id="uid-1", debug=False,
                                scale_denominator=None))

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

    def test_scale_denominator_defaults_to_none(self):
        req = parse_request({"takeoffId": "t1"}, "u", {"customerId": "c"})
        self.assertIsNone(req.scale_denominator)

    def test_every_suppliable_scale_is_accepted(self):
        from scale.units import SUPPLIABLE_SCALES

        for denominator in SUPPLIABLE_SCALES:
            with self.subTest(denominator=denominator):
                req = parse_request(
                    {"takeoffId": "t1", "scaleDenominator": denominator},
                    "u", {"customerId": "c"})
                self.assertEqual(req.scale_denominator, denominator)

    def test_an_integer_scale_is_accepted_as_a_float(self):
        # JSON over the wire gives 50, not 50.0.
        req = parse_request({"takeoffId": "t1", "scaleDenominator": 50},
                            "u", {"customerId": "c"})
        self.assertEqual(req.scale_denominator, 50.0)

    def test_a_scale_outside_the_offered_set_is_invalid(self):
        # 75 is a plausible-looking number that snaps to no standard scale, so
        # it would reach the detector as a measurement and leave the gates at
        # identity — the failure the re-run exists to avoid. The client is not
        # the authority on what the pipeline can act on.
        for value in (75, 1, 500, 0, -50, 100.5):
            with self.subTest(value=value):
                with self.assertRaises(InvalidArgument):
                    parse_request(
                        {"takeoffId": "t1", "scaleDenominator": value},
                        "u", {"customerId": "c"})

    def test_a_non_numeric_scale_is_invalid(self):
        for value in ("1:100", "100", [], {}, True):
            with self.subTest(value=value):
                with self.assertRaises(InvalidArgument):
                    parse_request(
                        {"takeoffId": "t1", "scaleDenominator": value},
                        "u", {"customerId": "c"})


if __name__ == "__main__":
    unittest.main()
