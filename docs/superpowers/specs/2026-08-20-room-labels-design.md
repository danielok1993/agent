# Room labels — design

**Status:** approved 2026-08-20
**Phase:** 1 of 2. Phase 2 (restructuring `takeoff.json` into a single
parent → child overlay document) is deliberately out of scope here.

## Problem

`takeoff.json` ships every room with `"label": null`. The web app's assembly
table therefore lists `room_0000`, `room_0001`, … instead of *Kitchen*,
*Bedroom 1*. The field is already plumbed end to end — `Candidate.label` →
`Entity.label` → `RoomTakeoff.label` (`takeoff/quantities.py:245`) — and
nothing ever writes it.

The existing `label` **entities** are not room names. `detection/labels.py`
matches `LABEL_PATTERN = ^[A-Z]{1,4}-?\d{1,4}[A-Z]?$`, which is the door and
window tag convention (`GD3`, `W8`). Room names are ordinary text spans that
no detector emits.

## What the corpus supports

Measured 2026-08-20 over the 18 regression sheets that detect rooms, using
each sheet's committed room polygons and the spans from `extract_page`:

| Reality | Sheets |
| --- | --- |
| Zero text spans — CAD outlined all text to vectors | s10, s11, s12, s16, s18 |
| Text present, none inside any room polygon | s07, s14, s20 |
| Room names present as plain text | s01–s04, s08, s13, s15, s17 |

Growing each polygon by 40 px before collecting spans lifts rooms that reach
any text from 77 to 92 of ~159 (+19 %), because names are routinely drawn
straddling a wall line. The extra cost is ~20 spans per sheet.

A purely local pick (largest alphabetic span in the polygon) mispicks on
every sheet measured: `BEDROOM 2` loses to the 13.9 pt section marker `A` on
s02; s04 returns the site address `28 HAYLES STREET`; s08 returns the
appliance tags `WM`, `FF`, `Heating`; unnamed s02 rooms return construction
notes (`backfill all voids with`).

## Approach

One extra Gemini call per page, **text only, no image crops**, schema
constrained, cached — the same shape as `gemini/classifier.py`, minus the
expensive part.

Labels never feed the quantity maths. Areas, wall m² and opening assignment
stay fully deterministic, so a model-authored display string cannot move a
number. This is the reason a Gemini call is acceptable here when
per-candidate validation was removed in 2026-07-28.

The call cannot be folded into the existing region classification: that runs
before detection, when no room exists yet.

### Pipeline position

`pipeline.run_extract`, between `finalize_candidates` and `compute_takeoff`.
Room `Entity.label` is set there, and `compute_takeoff` picks it up through
the assignment it already makes. `takeoff/` changes by zero lines, and
`detection/` stays pure and offline.

### Span pre-filter (deterministic)

For each room entity carrying `attributes["polygon"]`:

- keep spans whose bbox lies ≥ 50 % inside `polygon.buffer(40)`
- drop spans with no alphabetic character (`762`, `1800`)
- drop spans matching `detection.labels.LABEL_PATTERN` (`GD5`, `W8`)
- drop spans longer than 60 characters (construction notes)
- cap at 30 spans per room, nearest the polygon centroid first

### Request and response

Request is one JSON text part:

```json
{"rooms": [{"id": 11, "spans": [
  {"text": "FAMILY BATH", "size": 12.0, "inside": true},
  {"text": "+ UTILITY",   "size": 12.0, "inside": true},
  {"text": "boiler",      "size": 6.0,  "inside": true}]}]}
```

`inside` is true when the span lies in the polygon itself, false when only
the 40 px buffer reached it.

Response is constrained by `types.Schema`, `required: ["id", "label"]`,
`label` a nullable string:

```json
{"rooms": [{"id": 11, "label": "Family Bath + Utility"}]}
```

Output is Title Case. Rooms are addressed by ordinal `id`, matching the
classifier's contract; an item with an unknown or unparseable id is ignored.

### Grounding is enforced in code, not just prompted

A returned label is kept only if every alphabetic token in it appears in that
room's own span texts, compared case-insensitively. `Family Bath + Utility`
passes; a `Cupboard` inferred from area alone does not, and is discarded to
`null` with a `ROOM_LABEL_UNGROUNDED` warning. This makes "text only, never
guess" a property of the code rather than a hope about the prompt.

### Cache and offline

`gemini/room_label_cache.py` mirrors `gemini/region_cache.py`. The key is
`page_content_hash(page_data)` (reused as-is) + a hash of the room polygons
the labels were made against + `PROMPT_VERSION`, so editing the prompt or
changing room detection is a miss rather than a silent stale reuse.

- cache hit → labels apply with no call, including under `--no-gemini`
- miss with `--no-gemini` or no client → all labels `null`, `ROOM_LABEL_NO_GEMINI`
- call raised → all labels `null`, `ROOM_LABEL_FAILED`, **no cache write**
- response did not parse → all labels `null`, `ROOM_LABEL_PARSE_FAILURE`,
  **no cache write** — the same reasoning as `REGION_CLASSIFY_PARSE_FAILURE`
- cache write failed after a billed success → `ROOM_LABEL_CACHE_WRITE_FAILED`

### Cost

~2 k input tokens per page, one call. `tools/regress.py` runs
`skip_gemini=True` (`regression/sweep.py:193`), so a sweep never calls
Gemini — but a sheet whose label cache was seeded at adoption (see the
regression-testing guide's adoption follow-ups) still gets a cache hit and
its rooms come back named; an unseeded sheet emits `ROOM_LABEL_NO_GEMINI`
and stays unnamed. Either way that's intended — the sweep tests detection,
not labelling — and no sweep verdict reads a label, so regression risk is
zero regardless of which outcome a given sheet hits.

## Out of scope

- Naming the five outlined-text sheets (would need image crops)
- Inferring a name from geometry when no text supports it
- Any change to `takeoff.json`'s structure — that is phase 2
