"""Layer-name hints: CAD layer conventions pluralise the class name.

Measured on the corpus (2026-08-25): the layer-hint prior never fired on
s03/s17 ("A325G_INT_DOORS", "EXISTING_WINDOWS", "Windows"), s06/s13
("WINDOWS"), or s04/s08 ("RR_Walls", "RR_New Doors and Windows") because
the keyword lists are singular and the token match was exact. A plural
token names the same class.
"""
import unittest

from detection.layers import _layer_hint_from_layer, _layer_tokens
from detection.doors.constants import DOOR_LAYER_KEYWORDS
from detection.walls import _wall_layer_hint


WIN = ["window", "wind", "glaz", "glazing"]


class TestPluralLayerTokens(unittest.TestCase):
    def test_singular_still_matches(self):
        self.assertTrue(_layer_hint_from_layer("A-DOOR", DOOR_LAYER_KEYWORDS))
        self.assertTrue(_layer_hint_from_layer("a-wind", WIN))

    def test_plural_door_layer(self):
        self.assertTrue(_layer_hint_from_layer("A325G_INT_DOORS", DOOR_LAYER_KEYWORDS))

    def test_plural_window_layer(self):
        self.assertTrue(_layer_hint_from_layer("WINDOWS", WIN))
        self.assertTrue(_layer_hint_from_layer("EXISTING_WINDOWS", WIN))
        self.assertTrue(_layer_hint_from_layer("Windows", WIN))

    def test_plural_wall_layer(self):
        self.assertTrue(_wall_layer_hint("RR_Walls"))
        self.assertTrue(_wall_layer_hint("Partitions"))

    def test_no_substring_match(self):
        # Plural handling must not reopen substring matching.
        self.assertFalse(_layer_hint_from_layer("window-frame-notes", ["win"]))
        self.assertFalse(_layer_hint_from_layer("doorstops", DOOR_LAYER_KEYWORDS))
        self.assertFalse(_layer_hint_from_layer("WINDOWS", DOOR_LAYER_KEYWORDS))
        self.assertFalse(_wall_layer_hint("WINDOWS"))

    def test_short_tokens_not_stemmed(self):
        # "s"/"is"/"as" style tokens have no stem worth adding.
        self.assertNotIn("", _layer_tokens("s"))
        self.assertNotIn("a", _layer_tokens("as"))

    def test_mixed_class_layer_is_conclusive_for_none(self):
        # A layer naming two element classes groups joinery; it says the ink
        # is a door OR a window, never which. Measured on the corpus
        # (2026-08-26): 16 class-naming layers name exactly one class; only
        # s04's "RR_New Doors and Windows" names two, and the door prior fired
        # on its window paths.
        for name in ("RR_New Doors and Windows", "DOORS_WINDOWS", "Walls & Doors"):
            self.assertFalse(_layer_hint_from_layer(name, DOOR_LAYER_KEYWORDS), name)
        self.assertFalse(_layer_hint_from_layer("RR_New Doors and Windows", WIN))
        self.assertFalse(_wall_layer_hint("Walls & Doors"))
        # Single-class layers with an unrelated extra word keep their hint.
        self.assertTrue(_layer_hint_from_layer("RR_New Doors", DOOR_LAYER_KEYWORDS))
        self.assertTrue(_wall_layer_hint("RR_New Walls"))

    def test_empty_layer(self):
        self.assertFalse(_layer_hint_from_layer(None, DOOR_LAYER_KEYWORDS))
        self.assertFalse(_layer_hint_from_layer("", DOOR_LAYER_KEYWORDS))


if __name__ == "__main__":
    unittest.main()
