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

import dataclasses
import json
import re

from google.genai import types
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
        # A point ON the room, never its centroid: an L- or U-shaped room's
        # centroid can fall outside the polygon (into the notch), which would
        # order spans from a point that isn't even in the room.
        rep = poly.representative_point()
        cx, cy = rep.x, rep.y
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

    if not isinstance(parsed, dict):
        warnings.append({
            "warning_code": "ROOM_LABEL_PARSE_FAILURE",
            "severity": "error",
            "message": f"Room labelling response was not a JSON object: {type(parsed).__name__}",
            "raw_response_snippet": raw_text[:300],
        })
        return out, warnings

    by_id: dict[int, dict] = {}
    for item in parsed.get("rooms", []) or []:
        if not isinstance(item, dict):
            continue
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
