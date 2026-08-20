# Room Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate every room's `label` in `takeoff.json` and `final_entities.json` with the room name drawn on the plan, using one cached, schema-constrained Gemini call per page.

**Architecture:** A deterministic pre-filter collects the text spans in and around each room polygon. One text-only Gemini call maps room ordinals to names. A code-side grounding check discards any name not present in that room's own spans. The result is written onto the room `Entity.label` in `pipeline.run_extract`, between `finalize_candidates` and `compute_takeoff`, so `takeoff/` and `detection/` need no changes at all. The call is cached exactly like region classification, so `--no-gemini` runs and regression sweeps stay free.

**Tech Stack:** Python 3, `google-genai` (Vertex AI), `shapely`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-20-room-labels-design.md`

## Global Constraints

- All coordinates are 150-DPI pixels, top-left origin, y-down. Never reintroduce point space past `extraction/`.
- Room polygons live at `Entity.attributes["polygon"]` as a list of `[x, y]` pairs.
- Warning dicts use `SCREAMING_SNAKE_CASE` `warning_code`, plus `severity` and `message`. `page_number` is added by the caller.
- Never commit a PDF, and never put address-bearing text into a test fixture or a committed file.
- Git: work on a new branch; never add a `Co-Authored-By` trailer to a commit message.
- Tests run with `source .venv/bin/activate` first. Fast tier: `python -m unittest discover tests`.
- Detection stays pure and offline. No Gemini call may be added to `detection/`.
- Labels must never affect a computed quantity. Nothing in `takeoff/` may branch on a label.

---

### Task 1: Branch and the deterministic span collector

**Files:**
- Create: `gemini/room_labeler.py`
- Test: `tests/test_room_labeler.py`

**Interfaces:**
- Consumes: `models.Entity`, `models.TextSpan`, `detection.labels.LABEL_PATTERN`
- Produces:
  - `ROOM_LABEL_BUFFER_PX: float = 40.0`
  - `ROOM_LABEL_MIN_COVER_FRAC: float = 0.5`
  - `ROOM_LABEL_MAX_SPANS: int = 30`
  - `ROOM_LABEL_MAX_TEXT_LEN: int = 60`
  - `is_noise_span(text: str) -> bool`
  - `collect_room_spans(rooms: list[Entity], text_spans: list[TextSpan]) -> list[list[dict]]`
    returns one list per room, in room order; each dict is
    `{"text": str, "size": float, "inside": bool}`

- [ ] **Step 1: Create the branch**

```bash
cd /Users/nestimate/Documents/GitHub/agent
git checkout main
git pull --ff-only
git checkout -b feat/room-labels
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_room_labeler.py`:

```python
"""Room label span collection and response parsing (gemini/room_labeler.py).

No API calls: the collector is pure, and apply_labels is tested against
recorded response text.
"""
import unittest

from models import Entity, TextSpan
from gemini.room_labeler import (
    ROOM_LABEL_MAX_SPANS, collect_room_spans, is_noise_span,
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

    def test_each_room_gets_its_own_list_in_room_order(self):
        far = [(500, 500), (700, 500), (700, 700), (500, 700)]
        out = collect_room_spans([room(0, SQUARE), room(1, far)], [
            span("KITCHEN", 50, 50, 120, 65),
            span("BEDROOM 1", 550, 550, 640, 565),
        ])
        self.assertEqual([[s["text"] for s in r] for r in out],
                         [["KITCHEN"], ["BEDROOM 1"]])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gemini.room_labeler'`

- [ ] **Step 4: Write the minimal implementation**

Create `gemini/room_labeler.py`:

```python
"""Ask Gemini for the name written inside each detected room.

One text-only call per page — no image crops, unlike gemini/classifier.py.
Room names are ordinary text spans that no detector emits: detection/labels.py
matches the door and window TAG convention (GD5, W8), not room names.

Labels never feed the quantity maths. Areas, wall m2 and opening assignment
stay deterministic, so a model-authored display string cannot move a number.
That is why a Gemini call is acceptable here when per-candidate validation was
removed on 2026-07-28.
"""
from __future__ import annotations

import re

from shapely.geometry import Polygon, box

from detection.labels import LABEL_PATTERN
from models import Entity, TextSpan

# Names are routinely drawn straddling a wall line, so the polygon is grown
# before spans are collected. Measured 2026-08-20 across the regression
# corpus: rooms reaching any text go 77 -> 92 of ~159 at 40px, for about 20
# extra spans per sheet.
ROOM_LABEL_BUFFER_PX = 40.0
ROOM_LABEL_MIN_COVER_FRAC = 0.5
ROOM_LABEL_MAX_SPANS = 30
ROOM_LABEL_MAX_TEXT_LEN = 60   # longer than this is a construction note


def is_noise_span(text: str) -> bool:
    """True for text that can never be a room name: dimension strings, door
    and window tags, and construction notes."""
    s = text.strip()
    if not s or len(s) > ROOM_LABEL_MAX_TEXT_LEN:
        return True
    if not any(c.isalpha() for c in s):
        return True
    if LABEL_PATTERN.match(s):
        return True
    return False


def _room_polygon(entity: Entity) -> Polygon | None:
    pts = (entity.attributes or {}).get("polygon")
    if not pts or len(pts) < 3:
        return None
    try:
        poly = Polygon([(float(p[0]), float(p[1])) for p in pts])
    except (TypeError, ValueError, IndexError):
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if (not poly.is_empty and poly.area > 0) else None


def collect_room_spans(
    rooms: list[Entity], text_spans: list[TextSpan]
) -> list[list[dict]]:
    """One span list per room, in room order — the model's whole input.

    A span qualifies when at least ROOM_LABEL_MIN_COVER_FRAC of its bbox lies
    inside the room polygon grown by ROOM_LABEL_BUFFER_PX. "inside" reports
    whether the ungrown polygon already held it, which is how the model tells
    a name in this room from one bleeding in past a wall.
    """
    out: list[list[dict]] = []
    boxes = [(t, box(*t.bbox)) for t in text_spans if not is_noise_span(t.text)]
    for entity in rooms:
        poly = _room_polygon(entity)
        if poly is None:
            out.append([])
            continue
        grown = poly.buffer(ROOM_LABEL_BUFFER_PX)
        cx, cy = poly.centroid.x, poly.centroid.y
        found: list[tuple[float, dict]] = []
        for tspan, tbox in boxes:
            area = tbox.area
            if area <= 0 or not grown.intersects(tbox):
                continue
            if tbox.intersection(grown).area / area <= ROOM_LABEL_MIN_COVER_FRAC:
                continue
            inside = tbox.intersection(poly).area / area > ROOM_LABEL_MIN_COVER_FRAC
            sx = (tspan.bbox[0] + tspan.bbox[2]) / 2.0
            sy = (tspan.bbox[1] + tspan.bbox[3]) / 2.0
            dist = ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5
            found.append((dist, {
                "text": tspan.text.strip(),
                "size": round(float(tspan.size), 1),
                "inside": bool(inside),
            }))
        found.sort(key=lambda pair: pair[0])
        out.append([d for _, d in found[:ROOM_LABEL_MAX_SPANS]])
    return out
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: PASS, 13 tests

- [ ] **Step 6: Commit**

```bash
git add gemini/room_labeler.py tests/test_room_labeler.py
git commit -m "feat(labels): collect the text spans in and around each room polygon"
```

---

### Task 2: Schema, prompt, and the grounded response parser

**Files:**
- Modify: `gemini/room_labeler.py`
- Test: `tests/test_room_labeler.py`

**Interfaces:**
- Consumes: `collect_room_spans` from Task 1
- Produces:
  - `MODEL: str = "gemini-2.5-flash"`
  - `PROMPT_VERSION: str = "v1"`
  - `RESPONSE_SCHEMA: types.Schema`
  - `SYSTEM_PROMPT: str`
  - `build_request_text(room_spans: list[list[dict]]) -> str`
  - `is_grounded(label: str, spans: list[dict]) -> bool`
  - `apply_labels(raw_text: str, rooms: list[Entity], room_spans: list[list[dict]]) -> tuple[list[Entity], list[dict]]`
    returns **new** Entity objects (inputs are not mutated) plus warnings

- [ ] **Step 1: Write the failing test**

Append to `tests/test_room_labeler.py`, and extend the existing import of
`gemini.room_labeler` to also bring in `apply_labels`, `build_request_text`
and `is_grounded`:

```python
import json


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: FAIL with `ImportError: cannot import name 'apply_labels'`

- [ ] **Step 3: Write the minimal implementation**

Add to the imports at the top of `gemini/room_labeler.py`:

```python
import dataclasses
import json

from google.genai import types
```

Then append to `gemini/room_labeler.py`:

```python
MODEL = "gemini-2.5-flash"

# Part of the cache key: changing the prompt or the schema must invalidate
# every stored answer rather than silently reuse one made under other rules.
PROMPT_VERSION = "v1"

RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["rooms"],
    properties={
        "rooms": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                # id is the whole matching contract — apply_labels keys
                # responses to rooms by it and ignores items without one.
                required=["id", "label"],
                properties={
                    "id": types.Schema(type=types.Type.INTEGER),
                    "label": types.Schema(type=types.Type.STRING, nullable=True),
                },
            ),
        ),
    },
)

SYSTEM_PROMPT = """\
You are an expert reader of UK architectural floor plans.

A floor plan has been analysed and its rooms detected geometrically. For each
room you receive the text spans found inside it, and just outside it, with the
font size of each and whether it fell inside the room outline.

For EACH room, give the room's name as drawn, or null.

Rules:
- The name MUST come from the spans you were given for that room. Never invent
  a name from the room's size, shape or neighbours. If no span names the room,
  return null. Returning null is the correct answer for many rooms.
- Room names are usually the largest text in the room and are usually set in
  capitals: KITCHEN, BEDROOM 2, HALL, LIVING, WC, EN-SUITE, UTILITY, LANDING.
- Join spans that together form one name: "FAMILY BATH" + "+ UTILITY" is the
  single name "Family Bath + Utility".
- Ignore dimensions and levels (762, 1800, +2.450), construction and site
  notes ("backfill all voids with quilt insulation", "remove load bearing
  wall"), appliance and fitting tags (WM, w/m, drier, boiler, sink, towel
  rail), wall type tags (WALL TYPE 1), section and grid markers (a lone
  letter or number such as A or 1), drawing numbers (1133-WD11), and street
  addresses.
- Prefer a span marked "inside": true. A span marked "inside": false is only
  near the room and may belong to the room next door — use it only when it is
  clearly this room's name and nothing inside names it.
- Output Title Case: "Bedroom 1", not "BEDROOM 1".

Respond ONLY with valid JSON, no markdown fences:
{"rooms": [{"id": <int>, "label": "<name or null>"}]}
"""


def build_request_text(room_spans: list[list[dict]]) -> str:
    """The one user part: every room's spans as JSON, keyed by ordinal."""
    return json.dumps({
        "rooms": [
            {"id": i, "spans": spans} for i, spans in enumerate(room_spans)
        ]
    }, ensure_ascii=False)


_WORD = re.compile(r"[a-z0-9]+")


def is_grounded(label: str, spans: list[dict]) -> bool:
    """True when every word of the label appears in that room's own spans.

    This makes "name it from the text or return null" a property of the code
    rather than a hope about the prompt: a name inferred from area or shape
    has words the drawing never wrote, and is discarded.
    """
    words = _WORD.findall(label.lower())
    if not words:
        return False
    haystack = set()
    for s in spans:
        haystack.update(_WORD.findall(str(s.get("text", "")).lower()))
    return all(w in haystack for w in words)


def apply_labels(
    raw_text: str, rooms: list[Entity], room_spans: list[list[dict]]
) -> tuple[list[Entity], list[dict]]:
    """Apply a labelling response to a room list.

    Returns new Entity objects — the inputs are not mutated. A room the model
    did not address, or whose name is not grounded in its own spans, keeps a
    null label.
    """
    warnings: list[dict] = []
    out = [dataclasses.replace(e) for e in rooms]

    text = re.sub(r"^```(?:json)?", "", raw_text.strip())
    text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        warnings.append({
            "warning_code": "ROOM_LABEL_PARSE_FAILURE",
            "severity": "error",
            "message": f"Room labelling response was not valid JSON: {e}",
            "raw_response_snippet": raw_text[:300],
        })
        return out, warnings

    by_id: dict[int, dict] = {}
    for item in parsed.get("rooms", []) or []:
        try:
            by_id[int(item.get("id"))] = item
        except (TypeError, ValueError):
            continue

    ungrounded: list[str] = []
    for i, entity in enumerate(out):
        item = by_id.get(i)
        if item is None:
            continue
        label = item.get("label")
        if not isinstance(label, str) or not label.strip():
            continue
        label = label.strip()
        spans = room_spans[i] if i < len(room_spans) else []
        if not is_grounded(label, spans):
            ungrounded.append(f"{entity.entity_id}={label!r}")
            continue
        entity.label = label

    if ungrounded:
        warnings.append({
            "warning_code": "ROOM_LABEL_UNGROUNDED",
            "severity": "warning",
            "message": "Room labels discarded — not present in the room's own "
                       "text: " + ", ".join(ungrounded),
        })

    return out, warnings
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: PASS, 26 tests

- [ ] **Step 5: Commit**

```bash
git add gemini/room_labeler.py tests/test_room_labeler.py
git commit -m "feat(labels): schema-constrained room-name response with code-side grounding"
```

---

### Task 3: The one-call wrapper

**Files:**
- Modify: `gemini/room_labeler.py`
- Test: `tests/test_room_labeler.py`

**Interfaces:**
- Consumes: `collect_room_spans`, `build_request_text`, `apply_labels`, `RESPONSE_SCHEMA`, `SYSTEM_PROMPT`, `MODEL`
- Produces: `label_rooms(client, rooms: list[Entity], text_spans: list[TextSpan], model: str = MODEL) -> tuple[list[Entity], list[dict]]`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_room_labeler.py`, extending the module import to also
bring in `label_rooms`:

```python
import types as pytypes


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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: FAIL with `ImportError: cannot import name 'label_rooms'`

- [ ] **Step 3: Write the minimal implementation**

Append to `gemini/room_labeler.py`:

```python
def label_rooms(
    client,
    rooms: list[Entity],
    text_spans: list[TextSpan],
    model: str = MODEL,
) -> tuple[list[Entity], list[dict]]:
    """One text-only API call for the whole page. Returns labelled rooms +
    warnings. Makes no call when no room has any text to name it — five of the
    corpus's sheets outline their text to curves and can never be named."""
    if not rooms:
        return [], []
    room_spans = collect_room_spans(rooms, text_spans)
    if not any(room_spans):
        return [dataclasses.replace(e) for e in rooms], []

    response = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[
            types.Part.from_text(text=build_request_text(room_spans))])],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
        ),
    )
    return apply_labels(response.text, rooms, room_spans)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_labeler -v`
Expected: PASS, 30 tests

- [ ] **Step 5: Commit**

```bash
git add gemini/room_labeler.py tests/test_room_labeler.py
git commit -m "feat(labels): one text-only Gemini call per page for room names"
```

---

### Task 4: The label cache

**Files:**
- Create: `gemini/room_label_cache.py`
- Test: `tests/test_room_label_cache.py`

**Interfaces:**
- Consumes: `gemini.region_cache.page_content_hash`, `gemini.room_labeler.PROMPT_VERSION`
- Produces:
  - `CACHE_DIR_NAME: str = ".room_labels_cache"`
  - `room_geometry_hash(rooms: list[Entity]) -> str`
  - `cache_key(page_data: PageData, rooms: list[Entity]) -> str`
  - `cache_file(pdf_path: str, page_number: int, key: str) -> Path`
  - `load_labels(pdf_path: str, page_number: int, key: str) -> Optional[dict[str, Optional[str]]]`
  - `save_labels(pdf_path: str, page_number: int, key: str, rooms: list[Entity]) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/test_room_label_cache.py`:

```python
"""Room label cache tests (gemini/room_label_cache.py)."""
import shutil
import tempfile
import unittest
from pathlib import Path

from models import Entity, PageData, PathPrimitive
from gemini.room_label_cache import (
    cache_file, cache_key, load_labels, room_geometry_hash, save_labels,
)


def path(idx, x0, y0, x1, y1):
    return PathPrimitive(
        path_index=idx, item_type="l", bbox=(x0, y0, x1, y1),
        color=(0.0, 0.0, 0.0), fill=None, stroke_width=1.5,
        dashes="", layer=None, points=[(x0, y0), (x1, y1)],
    )


def page():
    return PageData(page_number=1, width_px=100.0, height_px=100.0,
                    paths=[path(0, 1, 2, 3, 4)])


def room(i, poly, label=None):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return Entity(
        entity_id=f"room_{i:04d}", entity_type="room",
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        confidence=0.85, source="heuristic", label=label,
        attributes={"polygon": [list(p) for p in poly]},
    )


SQUARE = [(0, 0), (200, 0), (200, 200), (0, 200)]
OTHER = [(0, 0), (300, 0), (300, 200), (0, 200)]


class TestGeometryHash(unittest.TestCase):
    def test_same_polygons_give_the_same_hash(self):
        self.assertEqual(room_geometry_hash([room(0, SQUARE)]),
                         room_geometry_hash([room(0, SQUARE)]))

    def test_a_changed_polygon_gives_a_different_hash(self):
        self.assertNotEqual(room_geometry_hash([room(0, SQUARE)]),
                            room_geometry_hash([room(0, OTHER)]))

    def test_an_extra_room_gives_a_different_hash(self):
        self.assertNotEqual(room_geometry_hash([room(0, SQUARE)]),
                            room_geometry_hash([room(0, SQUARE), room(1, OTHER)]))


class TestCacheKey(unittest.TestCase):
    def test_the_prompt_version_is_part_of_the_key(self):
        import gemini.room_label_cache as rlc
        key_before = cache_key(page(), [room(0, SQUARE)])
        original = rlc.PROMPT_VERSION
        try:
            rlc.PROMPT_VERSION = "v-other"
            self.assertNotEqual(cache_key(page(), [room(0, SQUARE)]), key_before)
        finally:
            rlc.PROMPT_VERSION = original


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdf = str(Path(self.tmp) / "sheet.pdf")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_miss_returns_none(self):
        self.assertIsNone(load_labels(self.pdf, 1, "nokey"))

    def test_labels_survive_a_round_trip(self):
        rooms = [room(0, SQUARE, "Kitchen"), room(1, OTHER, None)]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        self.assertEqual(load_labels(self.pdf, 1, key),
                         {"room_0000": "Kitchen", "room_0001": None})

    def test_the_cache_file_lives_beside_the_pdf(self):
        rooms = [room(0, SQUARE, "Kitchen")]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        self.assertTrue(cache_file(self.pdf, 1, key).exists())
        self.assertEqual(cache_file(self.pdf, 1, key).parent.name,
                         ".room_labels_cache")

    def test_corrupt_cache_content_reads_as_a_miss(self):
        rooms = [room(0, SQUARE, "Kitchen")]
        key = cache_key(page(), rooms)
        save_labels(self.pdf, 1, key, rooms)
        cache_file(self.pdf, 1, key).write_text("{ broken", encoding="utf-8")
        self.assertIsNone(load_labels(self.pdf, 1, key))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_label_cache -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gemini.room_label_cache'`

- [ ] **Step 3: Write the minimal implementation**

Create `gemini/room_label_cache.py`:

```python
"""On-disk cache of room labels, keyed by page content AND the room polygons
the labels were made against, AND the prompt version.

--no-gemini is the normal way this tool is run, and tools/regress.py sweeps 20
sheets. Without a cache, labels would either cost 20 calls a sweep or never be
exercised offline. With it, a page costs one real API call ever.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from gemini.region_cache import page_content_hash
from gemini.room_labeler import PROMPT_VERSION
from models import Entity, PageData

CACHE_DIR_NAME = ".room_labels_cache"


def room_geometry_hash(rooms: list[Entity]) -> str:
    """Stable digest of the room outlines a labelling was made against.

    A cached label belongs to the polygon it was read out of. Re-detecting
    rooms moves those outlines, and a name read from the old one may now sit
    in a different room — so a detection change must be a cache MISS.
    """
    h = hashlib.sha256()
    h.update(f"n={len(rooms)}|".encode())
    for r in rooms:
        h.update(f"{r.entity_id}:".encode())
        for x, y in (r.attributes or {}).get("polygon", []):
            h.update(f"{float(x):.1f},{float(y):.1f};".encode())
        h.update(b"|")
    return h.hexdigest()[:16]


def cache_key(page_data: PageData, rooms: list[Entity]) -> str:
    return (f"{page_content_hash(page_data)}-{room_geometry_hash(rooms)}"
            f"-{PROMPT_VERSION}")


def cache_file(pdf_path: str, page_number: int, key: str) -> Path:
    pdf = Path(pdf_path)
    return pdf.parent / CACHE_DIR_NAME / f"{pdf.stem}_p{page_number:02d}_{key}.json"


def load_labels(
    pdf_path: str, page_number: int, key: str
) -> Optional[dict[str, Optional[str]]]:
    target = cache_file(pdf_path, page_number, key)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        labels = payload["labels"]
        if not isinstance(labels, dict):
            return None
        return labels
    except Exception:
        return None


def save_labels(
    pdf_path: str, page_number: int, key: str, rooms: list[Entity]
) -> None:
    target = cache_file(pdf_path, page_number, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({
            "page_number": page_number,
            "cache_key": key,
            "labels": {r.entity_id: r.label for r in rooms},
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

Note the test patches `rlc.PROMPT_VERSION`, so `cache_key` must read the
module-level name at call time — keep the `f"...{PROMPT_VERSION}"` reference
inside the function body exactly as written above and do not bind it to a
default argument.

- [ ] **Step 4: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_label_cache -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add gemini/room_label_cache.py tests/test_room_label_cache.py
git commit -m "feat(labels): cache room labels by page content, room geometry and prompt version"
```

---

### Task 5: Pipeline wiring

**Files:**
- Modify: `pipeline.py` — imports near line 36, new `resolve_room_labels` after `resolve_page_regions` (ends ~line 460), call site at line 678
- Test: `tests/test_room_label_pipeline.py`

**Interfaces:**
- Consumes: `gemini.room_labeler.label_rooms`, `gemini.room_label_cache.{cache_key, load_labels, save_labels}`
- Produces: `pipeline.resolve_room_labels(pdf_path, page_data, entities, gemini_client, skip_gemini, label_fn=label_rooms) -> tuple[list[Entity], list[dict]]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_room_label_pipeline.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_label_pipeline -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_room_labels' from 'pipeline'`

- [ ] **Step 3: Add the imports to `pipeline.py`**

Beside the existing `from gemini.region_cache import ...` line, add:

```python
from gemini.room_labeler import label_rooms
from gemini.room_label_cache import (
    cache_key as label_cache_key,
    load_labels,
    save_labels,
)
```

- [ ] **Step 4: Write the orchestrator**

Add to `pipeline.py`, directly after `resolve_page_regions` ends:

```python
def resolve_room_labels(
    pdf_path: str,
    page_data: PageData,
    entities: list[Entity],
    gemini_client,
    skip_gemini: bool,
    label_fn=label_rooms,
) -> tuple[list[Entity], list[dict]]:
    """Name each detected room from the text drawn in it. Returns the full
    entity list (rooms replaced, everything else untouched) plus warnings.

    label_fn is injectable so the behaviour rules can be tested without
    credentials. Labels never feed the quantity maths — a null label costs a
    display string, never a number — so every failure path here degrades to
    "no labels" and the run continues.
    """
    pn = page_data.page_number
    warnings: list[dict] = []

    def warn(code, severity, msg):
        warnings.append({"page_number": pn, "warning_code": code,
                         "severity": severity, "message": msg})

    rooms = [e for e in entities if e.entity_type == "room"]
    if not rooms:
        return entities, warnings

    def merged(labelled: list[Entity]) -> list[Entity]:
        by_id = {e.entity_id: e for e in labelled}
        return [by_id.get(e.entity_id, e) for e in entities]

    key = label_cache_key(page_data, rooms)
    cached = load_labels(pdf_path, pn, key)

    if cached is not None:
        out = [dataclasses.replace(e, label=cached.get(e.entity_id))
               for e in rooms]
        return merged(out), warnings

    if skip_gemini or gemini_client is None:
        warn("ROOM_LABEL_NO_GEMINI", "warning",
             f"Page {pn}: no cached room labels and Gemini is disabled — "
             f"rooms are unnamed")
        return entities, warnings

    try:
        out, label_warnings = label_fn(gemini_client, rooms, page_data.text_spans)
    except Exception as e:
        # NOT a parse failure — apply_labels reports those itself, without
        # raising. Anything landing here is auth, network, or a bug.
        warn("ROOM_LABEL_FAILED", "error",
             f"Room labelling failed for page {pn}: {e}")
        return entities, warnings

    for w in label_warnings:
        w.setdefault("page_number", pn)
    warnings.extend(label_warnings)

    # A response that did not parse carries no information, and caching one
    # makes a one-off flake permanent — the same reasoning that keeps
    # REGION_CLASSIFY_PARSE_FAILURE out of the region cache.
    if any(w.get("warning_code") == "ROOM_LABEL_PARSE_FAILURE"
           for w in label_warnings):
        return merged(out), warnings

    # Outside the try: the call above is billed and has already succeeded, so
    # a read-only input directory must not throw its result away.
    try:
        save_labels(pdf_path, pn, key, out)
    except Exception as e:
        warn("ROOM_LABEL_CACHE_WRITE_FAILED", "warning",
             f"Page {pn}: room labelling succeeded but could not be cached "
             f"({e}) — the next run will call the API again")

    return merged(out), warnings
```

`pipeline.py` imports `from dataclasses import dataclass` (line 5) but not the
module, so `dataclasses.replace` above will fail. Change line 5 to:

```python
import dataclasses
from dataclasses import dataclass
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `source .venv/bin/activate && python -m unittest tests.test_room_label_pipeline -v`
Expected: PASS, 7 tests

- [ ] **Step 6: Wire it into `run_extract`**

In `pipeline.py`, replace these two lines (currently at 677-679):

```python
            entities, rejected = finalize_candidates(candidates)
            total_entities += len(entities)
```

with:

```python
            entities, rejected = finalize_candidates(candidates)
            total_entities += len(entities)

            # 5a. Room names — one cached, text-only Gemini call. Must run
            # BEFORE compute_takeoff, which copies Entity.label onto
            # RoomTakeoff.label.
            entities, room_label_warnings = resolve_room_labels(
                pdf_path, page_data, entities, gemini_client, skip_gemini)
```

Then renumber the existing `# 5a. Quantity takeoff` comment below it to
`# 5b. Quantity takeoff`, and fold the new warnings in by adding one line
beside the other `page_warnings.extend(...)` calls (currently 757-759):

```python
            page_warnings.extend(room_label_warnings)
```

- [ ] **Step 7: Run the whole fast tier**

Run: `source .venv/bin/activate && python -m unittest discover tests`
Expected: PASS, no new failures

- [ ] **Step 8: Commit**

```bash
git add pipeline.py tests/test_room_label_pipeline.py
git commit -m "feat(labels): name rooms in run_extract before the takeoff reads Entity.label"
```

---

### Task 6: Live verification and documentation

**Files:**
- Modify: `CLAUDE.md` — the "Gemini / GCP auth" section and the `pipeline.py::run_extract` stage list
- Modify: `docs/regression-testing-guide.md` — only if it enumerates cache directories

**Interfaces:**
- Consumes: everything from Tasks 1-5
- Produces: no code interface; a verified run and updated docs

- [ ] **Step 1: Run the two reference sheets for real**

```bash
source .venv/bin/activate
python app.py extract fixtures/sheets/s02-working-drawing-wd03.pdf --ceiling-height 2.4
```

- [ ] **Step 2: Check the labels landed**

```bash
python -c "
import json, glob
d = sorted(glob.glob('outputs/*/pages/page_01/takeoff.json'))[-1]
for r in json.load(open(d))['rooms']:
    print(f\"{r['room_id']:12} {r['floor_m2']:7.2f} m2  {r['label']}\")
"
```

Expected: at least 8 of the 12 rooms named, including `Kitchen`,
`Bedroom 1`, `Bedroom 2`, `Bedroom 3`, `Hall`, `Living`, `Wc`/`WC`,
`Bath 1`, `Family Bath + Utility`. Rooms whose only text is a construction
note (`backfill all voids…`, `Sloping soffit`, `coats`) may be `null` —
`Coats` is grounded and acceptable, an invented name is not.

If a name you expect is missing, check the warnings before touching the
prompt: `ROOM_LABEL_UNGROUNDED` means the grounding check ate it.

- [ ] **Step 3: Confirm the cache makes the second run free**

```bash
python app.py extract fixtures/sheets/s02-working-drawing-wd03.pdf --no-gemini --ceiling-height 2.4
python -c "
import json, glob
d = sorted(glob.glob('outputs/*/pages/page_01/takeoff.json'))[-1]
print([r['label'] for r in json.load(open(d))['rooms']])
"
```

Expected: the same labels as Step 2, with no `ROOM_LABEL_NO_GEMINI` warning.

- [ ] **Step 4: Confirm the cache directory is gitignored**

```bash
git status --short fixtures/
grep -n "regions_cache\|room_labels_cache" .gitignore
```

Expected: no `.room_labels_cache` entries under `git status`. If
`.regions_cache` is listed in `.gitignore`, add `.room_labels_cache/` beside
it; if `fixtures/` is ignored wholesale, nothing to do.

- [ ] **Step 5: Run the regression sweep**

```bash
python tools/regress.py
```

Expected: exit 0 with no lost `confirmed` entities and no returned false
positives. No sweep verdict reads a label, so any change here is a real
regression from Task 5's wiring, not from labelling.

- [ ] **Step 6: Update `CLAUDE.md`**

In the "Gemini / GCP auth" section, replace the sentence

> Model is hard-coded to `gemini-2.5-flash`, called once per page for region classification (`gemini/classifier.py`)

with

> Model is hard-coded to `gemini-2.5-flash`, called twice per page at most:
> once for region classification (`gemini/classifier.py`, image crops, before
> detection) and once for room labelling (`gemini/room_labeler.py`, text only,
> after `finalize_candidates`). Both are schema-constrained and separately
> cached; `--no-gemini` reuses either cache and warns on a miss
> (`REGION_CACHE_MISS_OFFLINE`, `ROOM_LABEL_NO_GEMINI`).

In the stage-6 paragraph of "Pipeline architecture", after the
`draw_overlay` sentence, add:

> Between finalisation and the takeoff, `pipeline.resolve_room_labels` names
> each room from the text drawn in and within 40px of its polygon — one
> text-only Gemini call per page, cached by page content + room geometry +
> prompt version (`gemini/room_label_cache.py`). A returned name is kept only
> when every word of it appears in that room's own spans
> (`room_labeler.is_grounded`), so a name is read off the drawing or the room
> stays unnamed; five corpus sheets outline their text to curves and can never
> be named. Labels never feed the quantity maths.

In the "Warning codes" list, add `ROOM_LABEL_NO_GEMINI`,
`ROOM_LABEL_FAILED`, `ROOM_LABEL_PARSE_FAILURE`, `ROOM_LABEL_UNGROUNDED` and
`ROOM_LABEL_CACHE_WRITE_FAILED` as emitted from `pipeline.resolve_room_labels`.

In the "Module layout" tree, add under the `gemini/` entries:

```
gemini/room_labeler.py     # room names from in-polygon text (one text-only call)
gemini/room_label_cache.py # label cache, keyed by page + room geometry + prompt version
```

- [ ] **Step 7: Refresh the knowledge graph**

```bash
graphify update .
```

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md graphify-out .gitignore
git commit -m "docs: room labelling — second Gemini call, cache, warning codes"
```

- [ ] **Step 9: Report the outcome**

State plainly how many rooms on s02 came back named, list any
`ROOM_LABEL_UNGROUNDED` entries, and give the `tools/regress.py` exit code.
Do not claim success without pasting the label list from Step 2.
