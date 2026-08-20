"""Room label orchestration rules (pipeline.resolve_room_labels).

No API calls: label_fn is injected.
"""
import dataclasses
import shutil
import tempfile
import unittest
from pathlib import Path

from models import Entity, PageData, PathPrimitive, TextSpan
from pipeline import resolve_room_labels
from gemini.room_label_cache import cache_key, cache_file


def path(idx):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(0.0, 0.0, 10.0, 10.0),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(0.0, 0.0), (10.0, 10.0)],
    )


SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]


def page():
    return PageData(
        page_number=1, width_px=500.0, height_px=500.0, paths=[path(0)],
        text_spans=[TextSpan(text="KITCHEN", bbox=(50.0, 50.0, 120.0, 65.0),
                             font="Helvetica", size=12.0,
                             color=0, block_no=0, line_no=0)],
    )


def rooms():
    return [Entity(entity_id="room_0000", entity_type="room",
                   bbox=(0.0, 0.0, 200.0, 200.0), confidence=0.85,
                   source="heuristic",
                   attributes={"polygon": [list(p) for p in SQUARE]}),
            Entity(entity_id="door_0000", entity_type="door",
                   bbox=(10.0, 10.0, 20.0, 20.0), confidence=0.9,
                   source="heuristic")]


def naming(name):
    def label_fn(client, room_entities, text_spans):
        out = [dataclasses.replace(e) for e in room_entities]
        out[0].label = name
        return out, []
    return label_fn


class TestResolveRoomLabels(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "sheet.pdf")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_successful_call_labels_the_room_and_writes_the_cache(self):
        entities = rooms()
        out, warnings = resolve_room_labels(
            self.pdf, page(), entities, object(), False, label_fn=naming("Kitchen"))
        self.assertEqual(out[0].label, "Kitchen")
        self.assertEqual(warnings, [])
        key = cache_key(page(), [out[0]])
        self.assertTrue(cache_file(self.pdf, 1, key).exists())

    def test_non_room_entities_pass_through_untouched(self):
        out, _ = resolve_room_labels(
            self.pdf, page(), rooms(), object(), False, label_fn=naming("Kitchen"))
        self.assertEqual([e.entity_id for e in out], ["room_0000", "door_0000"])
        self.assertIsNone(out[1].label)

    def test_a_second_run_offline_reuses_the_cache_without_calling(self):
        def explode(*args, **kwargs):
            raise AssertionError("label_fn must not be called on a cache hit")

        resolve_room_labels(self.pdf, page(), rooms(), object(), False,
                            label_fn=naming("Kitchen"))
        out, warnings = resolve_room_labels(
            self.pdf, page(), rooms(), None, True, label_fn=explode)
        self.assertEqual(out[0].label, "Kitchen")
        self.assertEqual(warnings, [])

    def test_a_cache_miss_offline_warns_and_labels_nothing(self):
        out, warnings = resolve_room_labels(
            self.pdf, page(), rooms(), None, True, label_fn=naming("Kitchen"))
        self.assertIsNone(out[0].label)
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["ROOM_LABEL_NO_GEMINI"])

    def test_a_raising_call_warns_labels_nothing_and_caches_nothing(self):
        def boom(*args, **kwargs):
            raise RuntimeError("auth failed")

        out, warnings = resolve_room_labels(
            self.pdf, page(), rooms(), object(), False, label_fn=boom)
        self.assertIsNone(out[0].label)
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["ROOM_LABEL_FAILED"])
        key = cache_key(page(), [out[0]])
        self.assertFalse(cache_file(self.pdf, 1, key).exists())

    def test_a_parse_failure_is_not_cached(self):
        def unparseable(client, room_entities, text_spans):
            return ([dataclasses.replace(e) for e in room_entities],
                    [{"warning_code": "ROOM_LABEL_PARSE_FAILURE",
                      "severity": "error", "message": "bad json"}])

        out, warnings = resolve_room_labels(
            self.pdf, page(), rooms(), object(), False, label_fn=unparseable)
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["ROOM_LABEL_PARSE_FAILURE"])
        key = cache_key(page(), [out[0]])
        self.assertFalse(cache_file(self.pdf, 1, key).exists())

    def test_a_page_with_no_rooms_does_nothing(self):
        entities = [rooms()[1]]
        out, warnings = resolve_room_labels(
            self.pdf, page(), entities, object(), False, label_fn=naming("Kitchen"))
        self.assertEqual(out, entities)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
