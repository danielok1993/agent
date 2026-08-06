"""Committed ground truth must not carry property-identifying text.

Ground truth records geometry. Sheet text is copied only into `tag`, and only
when it is a drawing tag (W11, GD9, D05). Room names, title blocks and schedule
contents are never copied, because they carry addresses — and the sheets are
NDA-covered even though their bboxes are not.
"""
import json
import re
import unittest

from regression.corpus import MANIFEST_PATH
from regression.ground_truth import TRUTH_DIR
from regression.hygiene import KEBAB_STREET_RE, POSTCODE_RE, STREET_RE

TAG_RE = re.compile(r"^[A-Z]{0,4}\d{1,3}[A-Z]?$")
MAX_LEN = {"note": 300, "pdf_sha256": 64}
DEFAULT_MAX_LEN = 60


def _strings(node, path="$"):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


class HygieneRuleTests(unittest.TestCase):
    """The rules catch what they claim to catch."""

    def test_a_postcode_is_caught(self):
        self.assertTrue(POSTCODE_RE.search("site at SW1A 1AA today"))

    def test_a_street_address_is_caught(self):
        self.assertTrue(STREET_RE.search("14 Bramble Road"))

    def test_a_kebab_cased_street_address_is_caught(self):
        # tools/add_sheet.py kebab-cases --desc into a manifest `file` value
        # ("14 Bramble Road proposed" -> "s21-14-bramble-road-proposed.pdf")
        # before it is lowercase and hyphen-separated, so it no longer has
        # STREET_RE's capitalised-word + whitespace shape at all.
        self.assertIsNone(STREET_RE.search("s21-14-bramble-road-proposed.pdf"),
                          "STREET_RE is not expected to catch the kebab form")
        self.assertTrue(KEBAB_STREET_RE.search("s21-14-bramble-road-proposed.pdf"))

    def test_ordinary_prose_is_not_caught(self):
        for phrase in ("the leaf is drawn closed in the wall plane",
                       "the doorway tongue was pinched",
                       "a 45deg bay wall pairs at wall spacing"):
            self.assertIsNone(STREET_RE.search(phrase), phrase)
            self.assertIsNone(POSTCODE_RE.search(phrase), phrase)

    def test_ordinary_kebab_filenames_are_not_caught(self):
        for name in ("s07-existing-floor-plans.pdf",
                     "s10-location-plan-and-all-existing-information.pdf",
                     "s19-second-floor-plan-roof-existing.pdf"):
            self.assertIsNone(KEBAB_STREET_RE.search(name), name)

    def test_drawing_tags_match_the_tag_pattern(self):
        for tag in ("W11", "GD9", "D05", "W8"):
            self.assertTrue(TAG_RE.match(tag), tag)

    def test_a_room_name_does_not_match_the_tag_pattern(self):
        for text in ("FAMILY BATH", "KITCHEN/DINER", "Flat 2"):
            self.assertFalse(TAG_RE.match(text), text)


class CommittedGroundTruthTests(unittest.TestCase):
    """Every committed ground-truth file obeys the rules."""

    def setUp(self):
        self.files = sorted(TRUTH_DIR.glob("*.json")) if TRUTH_DIR.is_dir() else []

    def test_every_string_is_free_of_addresses(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                self.assertIsNone(POSTCODE_RE.search(text),
                                  f"{path.name} {where}: postcode-like text {text!r}")
                self.assertIsNone(STREET_RE.search(text),
                                  f"{path.name} {where}: address-like text {text!r}")

    def test_every_string_is_within_its_length_budget(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                field = where.rsplit(".", 1)[-1]
                limit = MAX_LEN.get(field, DEFAULT_MAX_LEN)
                self.assertLessEqual(len(text), limit,
                                     f"{path.name} {where}: {len(text)} chars > {limit}")

    def test_every_tag_is_a_drawing_tag(self):
        for path in self.files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for where, text in _strings(payload):
                if where.rsplit(".", 1)[-1] == "tag":
                    self.assertTrue(TAG_RE.match(text),
                                    f"{path.name} {where}: {text!r} is not a drawing tag")


class ManifestHygieneTests(unittest.TestCase):
    """fixtures/MANIFEST.json is also tracked, and its `file` values are built
    verbatim from tools/add_sheet.py's --desc argument with no upstream
    validation beyond kebab-casing — so it needs the same address scan as
    ground truth, not just STREET_RE/POSTCODE_RE but the kebab-cased form
    those never match (see KEBAB_STREET_RE above).
    """

    def setUp(self):
        self.payload = (json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                        if MANIFEST_PATH.is_file() else {})

    def test_every_string_is_free_of_addresses(self):
        for where, text in _strings(self.payload):
            self.assertIsNone(POSTCODE_RE.search(text),
                              f"MANIFEST.json {where}: postcode-like text {text!r}")
            self.assertIsNone(STREET_RE.search(text),
                              f"MANIFEST.json {where}: address-like text {text!r}")
            self.assertIsNone(KEBAB_STREET_RE.search(text),
                              f"MANIFEST.json {where}: kebab-cased address-like "
                              f"text {text!r}")
