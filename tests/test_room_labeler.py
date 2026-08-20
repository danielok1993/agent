"""Room label span collection and response parsing (gemini/room_labeler.py).

No API calls: the collector is pure, and apply_labels is tested against
recorded response text.
"""
import json
import types as pytypes
import unittest

from models import Entity, TextSpan
from gemini.room_labeler import (
    ROOM_LABEL_MAX_SPANS, apply_labels, build_request_text, collect_room_spans,
    is_grounded, is_noise_span, label_rooms,
)


def room(i, poly, bbox=None):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return Entity(
        entity_id=f"room_{i:04d}",
        entity_type="room",
        bbox=bbox or (min(xs), min(ys), max(xs), max(ys)),
        confidence=0.85,
        source="heuristic",
        attributes={"polygon": [list(p) for p in poly]},
    )


def span(text, x0, y0, x1, y1, size=12.0):
    # TextSpan has no defaults for color/block_no/line_no — see models.py:22
    return TextSpan(text=text, bbox=(x0, y0, x1, y1), font="Helvetica",
                    size=size, color=0, block_no=0, line_no=0)


SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]


class TestIsNoiseSpan(unittest.TestCase):
    def test_pure_numeric_dimension_is_noise(self):
        self.assertTrue(is_noise_span("1800"))
        self.assertTrue(is_noise_span("3,600"))
        self.assertTrue(is_noise_span("4.50"))

    def test_door_and_window_tags_are_noise(self):
        self.assertTrue(is_noise_span("GD5"))
        self.assertTrue(is_noise_span("W8"))
        self.assertTrue(is_noise_span("D-01"))

    def test_long_construction_note_is_noise(self):
        self.assertTrue(is_noise_span(
            "backfill all voids with quilt insulation around the steels "
            "and make good to match existing finishes"))

    def test_a_room_name_is_not_noise(self):
        self.assertFalse(is_noise_span("KITCHEN"))
        self.assertFalse(is_noise_span("BEDROOM 2"))
        self.assertFalse(is_noise_span("WC"))


class TestCollectRoomSpans(unittest.TestCase):
    def test_a_span_inside_the_polygon_is_collected_as_inside(self):
        out = collect_room_spans([room(0, SQUARE)],
                                 [span("KITCHEN", 50, 50, 120, 65)])
        self.assertEqual(out, [[{"text": "KITCHEN", "size": 12.0, "inside": True}]])

    def test_a_span_just_outside_is_collected_as_not_inside(self):
        out = collect_room_spans([room(0, SQUARE)],
                                 [span("HALL", 210, 90, 260, 105)])
        self.assertEqual(out[0][0]["inside"], False)

    def test_a_span_beyond_the_buffer_is_dropped(self):
        out = collect_room_spans([room(0, SQUARE)],
                                 [span("GARDEN", 400, 90, 460, 105)])
        self.assertEqual(out, [[]])

    def test_a_span_mostly_outside_the_grown_polygon_is_dropped(self):
        # The square grows to x=240. Only 5px of this 30px-wide span is inside,
        # which is 17% against the 50% gate.
        out = collect_room_spans([room(0, SQUARE)],
                                 [span("LIVING", 235, 90, 265, 105)])
        self.assertEqual(out, [[]])

    def test_a_span_grazing_the_polygon_is_kept_but_not_inside(self):
        # 10% of the bbox is in the polygon, but all of it is in the buffer.
        out = collect_room_spans([room(0, SQUARE)],
                                 [span("LIVING", 198, 90, 218, 105)])
        self.assertEqual(out[0][0]["inside"], False)

    def test_noise_spans_are_dropped(self):
        out = collect_room_spans([room(0, SQUARE)], [
            span("1800", 50, 50, 80, 62),
            span("GD5", 60, 70, 90, 82),
            span("KITCHEN", 50, 90, 120, 105),
        ])
        self.assertEqual([s["text"] for s in out[0]], ["KITCHEN"])

    def test_rooms_without_a_polygon_get_an_empty_list(self):
        e = Entity(entity_id="room_0000", entity_type="room",
                   bbox=(0, 0, 10, 10), confidence=0.8, source="heuristic")
        self.assertEqual(collect_room_spans([e], [span("KITCHEN", 1, 1, 5, 5)]), [[]])

    def test_output_is_capped_and_ordered_nearest_the_centroid_first(self):
        # "ROOM 0", not "NAME0": LABEL_PATTERN matches NAME0 as a door tag,
        # so is_noise_span would drop the whole fixture.
        spans = [span(f"ROOM {i}", 100 + i, 100 + i, 110 + i, 112 + i)
                 for i in range(ROOM_LABEL_MAX_SPANS + 10)]
        out = collect_room_spans([room(0, SQUARE)], spans)
        self.assertEqual(len(out[0]), ROOM_LABEL_MAX_SPANS)
        self.assertEqual(out[0][0]["text"], "ROOM 0")

    def test_capped_ordering_uses_a_point_on_a_concave_room_not_its_centroid(self):
        # This L's notch (x>60, y>60 is cut away) pulls the centroid to
        # (96.67, 96.67) -- inside the notch, i.e. OUTSIDE the polygon
        # (confirmed with shapely: poly.contains(poly.centroid) is False).
        # representative_point() instead returns (30, 180), which is
        # guaranteed inside (in the vertical arm here).
        #
        # Two 16-span clusters -- one hugging the representative point, one
        # hugging the (off-polygon) centroid -- push the total to 32, past
        # ROOM_LABEL_MAX_SPANS (30), so the cap must cut 2 spans from one
        # cluster or the other. Which cluster survives shows which point
        # actually drove the ordering.
        l_shape = [(0, 0), (300, 0), (300, 60), (60, 60), (60, 300), (0, 300)]
        spans = []
        for i in range(16):
            cx, cy = 20 + i * 0.5, 170 + i * 0.5   # near the representative point
            spans.append(span(f"ZONE A{i}", cx - 5, cy - 6, cx + 5, cy + 6))
        for i in range(16):
            cx, cy = 50 - i * 0.3, 50 - i * 0.3    # near the off-polygon centroid
            spans.append(span(f"ZONE B{i}", cx - 5, cy - 6, cx + 5, cy + 6))

        out = collect_room_spans([room(0, l_shape)], spans)
        texts = {s["text"] for s in out[0]}

        self.assertEqual(len(texts), ROOM_LABEL_MAX_SPANS)
        # Ordered from the representative point, the two farthest A-cluster
        # spans survive and the two farthest B-cluster spans are cut --
        # centroid-ordering would keep exactly the reverse pair.
        self.assertIn("ZONE A14", texts)
        self.assertIn("ZONE A15", texts)
        self.assertNotIn("ZONE B14", texts)
        self.assertNotIn("ZONE B15", texts)

    def test_each_room_gets_its_own_list_in_room_order(self):
        far = [(500, 500), (700, 500), (700, 700), (500, 700)]
        out = collect_room_spans([room(0, SQUARE), room(1, far)], [
            span("KITCHEN", 50, 50, 120, 65),
            span("BEDROOM 1", 550, 550, 640, 565),
        ])
        self.assertEqual([[s["text"] for s in r] for r in out],
                         [["KITCHEN"], ["BEDROOM 1"]])


def response(entries):
    return json.dumps({"rooms": entries})


class TestBuildRequestText(unittest.TestCase):
    def test_payload_is_json_with_ordinal_ids(self):
        payload = json.loads(build_request_text([
            [{"text": "KITCHEN", "size": 12.0, "inside": True}],
            [],
        ]))
        self.assertEqual([r["id"] for r in payload["rooms"]], [0, 1])
        self.assertEqual(payload["rooms"][0]["spans"][0]["text"], "KITCHEN")
        self.assertEqual(payload["rooms"][1]["spans"], [])


class TestIsGrounded(unittest.TestCase):
    def test_a_label_built_from_the_spans_is_grounded(self):
        spans = [{"text": "FAMILY BATH", "size": 12.0, "inside": True},
                 {"text": "+ UTILITY", "size": 12.0, "inside": True}]
        self.assertTrue(is_grounded("Family Bath + Utility", spans))

    def test_an_invented_label_is_not_grounded(self):
        spans = [{"text": "Sloping", "size": 6.0, "inside": True},
                 {"text": "soffit", "size": 6.0, "inside": True}]
        self.assertFalse(is_grounded("Under-stair Cupboard", spans))

    def test_grounding_ignores_case_and_punctuation(self):
        spans = [{"text": "BEDROOM 2", "size": 12.0, "inside": True}]
        self.assertTrue(is_grounded("Bedroom 2", spans))

    def test_no_spans_can_ground_nothing(self):
        self.assertFalse(is_grounded("Kitchen", []))


class TestApplyLabels(unittest.TestCase):
    def setUp(self):
        self.rooms = [room(0, SQUARE), room(1, SQUARE)]
        self.spans = [
            [{"text": "KITCHEN", "size": 12.0, "inside": True}],
            [{"text": "FAMILY BATH", "size": 12.0, "inside": True},
             {"text": "+ UTILITY", "size": 12.0, "inside": True}],
        ]

    def test_labels_are_applied_by_ordinal_id(self):
        raw = response([{"id": 0, "label": "Kitchen"},
                        {"id": 1, "label": "Family Bath + Utility"}])
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual([e.label for e in out], ["Kitchen", "Family Bath + Utility"])
        self.assertEqual(warnings, [])

    def test_the_input_entities_are_not_mutated(self):
        raw = response([{"id": 0, "label": "Kitchen"}])
        apply_labels(raw, self.rooms, self.spans)
        self.assertIsNone(self.rooms[0].label)

    def test_a_null_label_stays_none(self):
        raw = response([{"id": 0, "label": None}, {"id": 1, "label": None}])
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual([e.label for e in out], [None, None])
        self.assertEqual(warnings, [])

    def test_an_ungrounded_label_is_discarded_and_warned(self):
        raw = response([{"id": 0, "label": "Utility Cupboard"},
                        {"id": 1, "label": "Family Bath + Utility"}])
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertIsNone(out[0].label)
        self.assertEqual(out[1].label, "Family Bath + Utility")
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["ROOM_LABEL_UNGROUNDED"])

    def test_a_room_the_model_skipped_stays_none_without_a_warning(self):
        raw = response([{"id": 0, "label": "Kitchen"}])
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual([e.label for e in out], ["Kitchen", None])
        self.assertEqual(warnings, [])

    def test_an_unknown_id_is_ignored(self):
        raw = response([{"id": 7, "label": "Kitchen"}])
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual([e.label for e in out], [None, None])

    def test_markdown_fences_are_stripped(self):
        raw = "```json\n" + response([{"id": 0, "label": "Kitchen"}]) + "\n```"
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual(out[0].label, "Kitchen")

    def test_unparseable_json_warns_and_labels_nothing(self):
        out, warnings = apply_labels("not json at all", self.rooms, self.spans)
        self.assertEqual([e.label for e in out], [None, None])
        self.assertEqual([w["warning_code"] for w in warnings],
                         ["ROOM_LABEL_PARSE_FAILURE"])
        self.assertEqual(warnings[0]["severity"], "error")

    def test_valid_json_that_is_not_an_object_reports_a_parse_failure(self):
        for raw in ("null", "5", "[]", '"kitchen"'):
            with self.subTest(raw=raw):
                out, warnings = apply_labels(raw, self.rooms, self.spans)
                self.assertEqual([e.label for e in out], [None, None])
                self.assertEqual([w["warning_code"] for w in warnings],
                                 ["ROOM_LABEL_PARSE_FAILURE"])

    def test_a_non_dict_item_in_the_rooms_array_is_skipped(self):
        raw = json.dumps({"rooms": ["x", 7, None, {"id": 0, "label": "Kitchen"}]})
        out, warnings = apply_labels(raw, self.rooms, self.spans)
        self.assertEqual([e.label for e in out], ["Kitchen", None])
        self.assertEqual(warnings, [])


class FakeClient:
    """Stands in for google.genai's client — records the call, returns text."""

    def __init__(self, text):
        self.text = text
        self.calls = []
        outer = self

        class Models:
            def generate_content(self, **kwargs):
                outer.calls.append(kwargs)
                return pytypes.SimpleNamespace(text=outer.text)

        self.models = Models()


class TestLabelRooms(unittest.TestCase):
    def test_no_rooms_makes_no_call(self):
        client = FakeClient(response([]))
        out, warnings = label_rooms(client, [], [span("KITCHEN", 1, 1, 5, 5)])
        self.assertEqual(out, [])
        self.assertEqual(warnings, [])
        self.assertEqual(client.calls, [])

    def test_no_spans_anywhere_makes_no_call(self):
        client = FakeClient(response([]))
        out, warnings = label_rooms(client, [room(0, SQUARE)], [])
        self.assertEqual([e.label for e in out], [None])
        self.assertEqual(client.calls, [])

    def test_a_labelled_room_comes_back_named(self):
        client = FakeClient(response([{"id": 0, "label": "Kitchen"}]))
        out, warnings = label_rooms(
            client, [room(0, SQUARE)], [span("KITCHEN", 50, 50, 120, 65)])
        self.assertEqual(out[0].label, "Kitchen")
        self.assertEqual(warnings, [])

    def test_the_call_is_schema_constrained_and_deterministic(self):
        client = FakeClient(response([{"id": 0, "label": "Kitchen"}]))
        label_rooms(client, [room(0, SQUARE)], [span("KITCHEN", 50, 50, 120, 65)])
        config = client.calls[0]["config"]
        self.assertEqual(config.temperature, 0.0)
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIsNotNone(config.response_schema)


if __name__ == "__main__":
    unittest.main()
