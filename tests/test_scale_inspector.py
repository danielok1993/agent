"""The inspect command's unbound scale listing.

inspect never segments regions, so it cannot bind a scale to a plan. It lists
what the sheet states and stops there -- and it never prompts.
"""
import unittest

from inspector import unbound_scale_lines
from models import ScaleInfo


def viewport(denominator):
    return ScaleInfo(denominator=denominator, source="viewport",
                     bbox=(0.0, 0.0, 10.0, 10.0), raw=f"C={denominator:g}")


def text(denominator, raw):
    return ScaleInfo(denominator=denominator, source="text",
                     bbox=(0.0, 0.0, 10.0, 10.0), raw=raw)


class TestUnboundScaleLines(unittest.TestCase):
    def test_no_scales_says_so(self):
        lines = unbound_scale_lines([], [])
        self.assertEqual(len(lines), 1)
        self.assertIn("none found", lines[0].lower())

    def test_viewport_scales_are_listed(self):
        lines = unbound_scale_lines([viewport(100.0)], [])
        self.assertTrue(any("1:100" in line for line in lines))

    def test_text_scales_are_listed_with_their_span(self):
        lines = unbound_scale_lines([], [text(50.0, "1:50@A3")])
        self.assertTrue(any("1:50@A3" in line for line in lines))

    def test_repeated_viewport_scales_are_counted_not_repeated(self):
        # s17's four 1:100 viewports, at their REAL measured values. CAD never
        # writes a scale as the same float twice, so [viewport(100.0)] * 4
        # would pass while the grouping bug it targets was live.
        lines = unbound_scale_lines(
            [viewport(d) for d in (99.986, 99.988, 99.993, 99.995)], [])
        joined = " ".join(lines)
        self.assertEqual(joined.count("1:100"), 1)
        self.assertIn("4", joined)

    def test_a_span_stating_two_scales_lists_both(self):
        # s20's title block reads "1:50  & 1:100" — text_scales emits two
        # ScaleInfos sharing one raw string, and both must be listed.
        raw = "1:50  & 1:100"
        lines = unbound_scale_lines([], [text(50.0, raw), text(100.0, raw)])
        joined = " ".join(lines)
        self.assertIn("1:50", joined)
        self.assertIn("1:100", joined)

    def test_the_same_scale_repeated_in_one_span_is_listed_once(self):
        raw = "SCALE 1:100"
        lines = unbound_scale_lines([], [text(100.0, raw), text(100.0, raw)])
        self.assertEqual(len(lines), 1)

    def test_both_sources_appear(self):
        lines = unbound_scale_lines([viewport(100.0)], [text(50.0, "1:50@A3")])
        joined = " ".join(lines)
        self.assertIn("1:100", joined)
        self.assertIn("1:50", joined)

    def test_unmatched_closing_tag_in_raw_does_not_crash(self):
        # Regression: raw text containing unmatched closing tags like [/bold]
        # must not crash the function. The escaping should neutralize the brackets.
        # These test cases reproduce the defects found in code review.
        test_cases = [
            "1:50 & 1/100 [/bold] extra",
            "[/nonexistent]",
            "[/]",
        ]
        for raw in test_cases:
            lines = unbound_scale_lines([], [text(50.0, raw)])
            # The function should not crash
            self.assertEqual(len(lines), 1)
            # The escaped bracket text should survive in the output
            # (escaped with backslash so Rich won't parse it)
            self.assertIn("\\[", lines[0])

    def test_text_scale_with_none_denominator_is_skipped(self):
        # Regression: ScaleInfo with None denominator should be skipped, not crash.
        # The viewport branch already guards against this; the text branch must too.
        # When a text scale's denominator is None, it's filtered out during processing.
        lines = unbound_scale_lines([], [text(None, "Some text")])
        # The entry is skipped, producing an empty list
        self.assertEqual(len(lines), 0)


if __name__ == "__main__":
    unittest.main()
