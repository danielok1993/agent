"""The interactive scale prompt.

The prompt must never run in batch_extract (ProcessPoolExecutor, no tty) or
tools/regress.py (unattended sweep of 20 sheets), so the tty gate is the
load-bearing behaviour here.
"""
import io
import unittest

from scale.prompt import can_prompt, parse_answer, prompt_for_scale


class FakeStream(io.StringIO):
    def __init__(self, tty):
        super().__init__()
        self._tty = tty

    def isatty(self):
        return self._tty


class TestCanPrompt(unittest.TestCase):
    def test_tty_allows_prompting(self):
        self.assertTrue(can_prompt(FakeStream(tty=True)))

    def test_pipe_forbids_prompting(self):
        self.assertFalse(can_prompt(FakeStream(tty=False)))

    def test_stream_without_isatty_forbids_prompting(self):
        self.assertFalse(can_prompt(object()))


class TestParseAnswer(unittest.TestCase):
    def test_full_ratio(self):
        self.assertEqual(parse_answer("1:100"), 100.0)

    def test_bare_denominator(self):
        self.assertEqual(parse_answer("100"), 100.0)

    def test_whitespace_is_tolerated(self):
        self.assertEqual(parse_answer("  1 : 50 "), 50.0)

    def test_empty_answer_is_a_skip(self):
        self.assertIsNone(parse_answer(""))

    def test_nonsense_is_a_skip(self):
        self.assertIsNone(parse_answer("dunno"))

    def test_one_to_one_is_rejected(self):
        self.assertIsNone(parse_answer("1:1"))


class TestPromptForScale(unittest.TestCase):
    def test_returns_the_normalised_ratio(self):
        answers = iter(["1:50"])
        result = prompt_for_scale("region_0002", "crop.png",
                                  input_fn=lambda _: next(answers),
                                  output_fn=lambda *_: None)
        self.assertEqual(result, "1:50")

    def test_bare_number_is_normalised_to_a_ratio(self):
        answers = iter(["100"])
        result = prompt_for_scale("region_0002", "crop.png",
                                  input_fn=lambda _: next(answers),
                                  output_fn=lambda *_: None)
        self.assertEqual(result, "1:100")

    def test_empty_answer_skips_without_reprompting(self):
        calls = []

        def record(_):
            calls.append(1)
            return ""

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=record,
                                           output_fn=lambda *_: None))
        self.assertEqual(len(calls), 1)

    def test_the_crop_path_is_shown_so_the_user_can_look(self):
        shown = []
        prompt_for_scale("region_0002", "pages/page_01/region_crops/x.png",
                         input_fn=lambda _: "",
                         output_fn=lambda *a: shown.append(" ".join(str(x) for x in a)))
        self.assertTrue(any("region_crops" in line for line in shown))

    def test_eof_is_a_skip_not_a_crash(self):
        def raise_eof(_):
            raise EOFError

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=raise_eof,
                                           output_fn=lambda *_: None))

    def test_interrupt_is_a_skip_not_a_crash(self):
        def raise_interrupt(_):
            raise KeyboardInterrupt

        self.assertIsNone(prompt_for_scale("region_0002", "crop.png",
                                           input_fn=raise_interrupt,
                                           output_fn=lambda *_: None))


if __name__ == "__main__":
    unittest.main()
