import unittest

from takeoff.heights import (
    DEFAULT_CEILING_M, DEFAULT_DOOR_M, DEFAULT_WINDOW_M,
    Heights, parse_height, resolve_heights, valid_height_m,
)


class TestParseHeight(unittest.TestCase):
    def test_metres(self):
        self.assertEqual(parse_height("2.4"), 2.4)
        self.assertEqual(parse_height(" 2.7 m "), 2.7)

    def test_millimetres_are_converted(self):
        self.assertEqual(parse_height("2400"), 2.4)
        self.assertEqual(parse_height("2400mm"), 2.4)

    def test_blank_and_nonsense_and_nonpositive_are_none(self):
        for bad in ("", "   ", "tall", "0", "-2", None):
            self.assertIsNone(parse_height(bad), bad)


class TestResolveHeights(unittest.TestCase):
    def test_flags_win_and_are_recorded(self):
        h = resolve_heights(2.7, 2.0, 1.5, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual((h.ceiling_m, h.door_m, h.window_m), (2.7, 2.0, 1.5))
        self.assertEqual(h.sources, {"ceiling": "flag", "door": "flag", "window": "flag"})

    def test_prompt_only_for_ceiling_when_tty(self):
        asked = []
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda q: asked.append(q) or "2.6",
                            output_fn=lambda *_: None)
        self.assertEqual(len(asked), 1)
        self.assertEqual(h.ceiling_m, 2.6)
        self.assertEqual(h.sources["ceiling"], "prompt")
        self.assertEqual((h.door_m, h.window_m), (DEFAULT_DOOR_M, DEFAULT_WINDOW_M))
        self.assertEqual(h.sources["door"], "default")

    def test_no_prompt_without_tty(self):
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: False,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual(h.ceiling_m, DEFAULT_CEILING_M)
        self.assertEqual(h.sources["ceiling"], "default")

    def test_no_prompt_when_caller_forbids(self):
        h = resolve_heights(None, None, None, allow_prompt=False,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: self.fail("must not prompt"))
        self.assertEqual(h.sources["ceiling"], "default")

    def test_blank_answer_and_eof_fall_to_default(self):
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=lambda _: "", output_fn=lambda *_: None)
        self.assertEqual(h.sources["ceiling"], "default")

        def eof(_):
            raise EOFError
        h = resolve_heights(None, None, None, allow_prompt=True,
                            can_prompt_fn=lambda: True,
                            input_fn=eof, output_fn=lambda *_: None)
        self.assertEqual(h.sources["ceiling"], "default")

    def test_to_dict_shape(self):
        d = Heights(2.4, 2.1, 1.2, {"ceiling": "default", "door": "default",
                                     "window": "default"}).to_dict()
        self.assertEqual(set(d), {"ceiling_m", "door_m", "window_m", "source"})

    def test_invalid_flags_raise(self):
        for bad in (0.0, -2.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                resolve_heights(bad, None, None, allow_prompt=False)
            with self.assertRaises(ValueError):
                resolve_heights(None, bad, None, allow_prompt=False)
            with self.assertRaises(ValueError):
                resolve_heights(None, None, bad, allow_prompt=False)

    def test_valid_height_m(self):
        self.assertEqual(valid_height_m(2.4, "ceiling"), 2.4)
        with self.assertRaises(ValueError):
            valid_height_m(float("nan"), "ceiling")
