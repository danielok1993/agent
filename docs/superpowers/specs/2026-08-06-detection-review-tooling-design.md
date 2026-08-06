# Detection Review Tooling — Design

**Date:** 2026-08-06
**Status:** Approved, not yet implemented
**Supersedes:** the "Labeling stays manual / no review tooling is being built"
constraint and non-goal of `2026-08-06-regression-corpus-design.md`. The corpus
landed; labeling it is now the binding constraint, so the tooling that spec
deferred is what this one builds.

## Problem

`tools/regress.py` scores 20 sheets against committed ground truth and prints
every unscored detection under REVIEW. Three things make those REVIEW lines
impossible to act on.

**The run output is deleted.** `regression/sweep.py` extracts each sheet into a
`tempfile.TemporaryDirectory()` and reads `final_entities.json` back out before
the block exits. The render, the overlay, and the debug viewer are destroyed
microseconds after they are written. There is nothing left to look at.

**The lines carry no identity.** `regression/report.py` prints
`REVIEW new door @ (1204,883) conf 0.82`. The entity dict it formats already
holds `entity_id`, but the id is dropped. Matching a terminal line to a shape on
a drawing means eyeballing coordinates.

**There is no way to record a verdict.** Ground truth is hand-edited JSON.
Recording ten verdicts means ten hand-written bbox literals copied out of
`final_entities.json`, plus a manual `reviewed` date and a manual
`"labeled": true` in `fixtures/MANIFEST.json`.

The scale of the gap: **one** of twenty sheets has ground truth
(`tests/ground_truth/s01.json`, four windows, nothing else). Nineteen sheets are
entirely unlabeled. This tooling is not primarily for reviewing deltas — it is
the tool the corpus gets labeled with in the first place, across hundreds of
detections.

Rooms carry a fourth problem the other entity types do not. A room can be
detected, match its ground truth by bbox, and still be the wrong shape — 12px
short at a doorway, a chamfered corner, a notch bitten out by a phantom plug. A
correct-by-bbox room is not a correct room, and today nothing records or guards
the difference.

## Goals

1. A sweep leaves behind everything needed to judge its own output.
2. Every REVIEW line names an entity id that is findable on an image.
3. Recording verdicts is interactive selection, never hand-edited JSON.
4. Room geometry is pinned so shape changes are visible, without shape churn
   ever failing the sweep.
5. The same verdict writer serves a human at a terminal and an agent acting on
   the human's behalf. One code path, not two.

## Non-goals

- **No browser or server UI.** Terminal only, decided explicitly. No localhost
  server, no click-to-verdict HTML page, no file:// download round-trip.
- **No per-item crop images.** Context around a detection is what tells you
  whether it is real; a bbox crop throws that away.
- **No semantic descriptions of geometry change.** The sweep may report that a
  polygon changed and by how much. It may not claim *what* changed in drawing
  terms ("gained the doorway recess") — that is not computable from two polygons
  and would be fabrication.
- **No new detection behavior.** Nothing in `detection/` or `pipeline.py`
  changes. This is tooling around an unchanged pipeline.
- **No automated verdicts.** Nothing decides correctness on the user's behalf.
  An agent may *transcribe* the user's verdicts; it never originates one.

## Constraints

1. **Ground truth format stays backward compatible.** `tests/ground_truth/s01.json`
   must keep loading and scoring identically. New fields are optional.
2. **Entity ids are ordinal and unstable across runs.** `door_0015` becomes
   `door_0014` the moment an earlier door stops being detected. Ids may be used
   to identify a detection *within one sweep's output* — the review handoff —
   and must never be persisted into ground truth or used for matching.
   Matching stays geometric.
3. **New detections never fail the sweep.** Unchanged from the corpus design.
   Review is queued, not enforced.
4. **The fast unit tier stays under ~10s.** New tests are synthetic and cheap.
5. **No committed PDFs, no address-bearing text.** Unchanged. Review overlays
   are written under gitignored `outputs/`.

## Design

Six pieces, phased. V1 (pieces 1–5) unblocks labeling. V2 (pieces 6–7) adds
guards over labels that do not exist yet.

### Piece 1 — the sweep persists its output

`regression/sweep.py` currently wraps `run_extract` in a
`tempfile.TemporaryDirectory()`. Replace it with a stable per-slug directory:

```
outputs/regress/<slug>/
├── summary.json
├── warnings.json
└── pages/page_NN/
    ├── render.png
    ├── overlay.png
    ├── final_entities.json
    ├── debug_trace.json        # debug=True
    ├── debug_viewer.html       # debug=True
    └── review_<type>.png       # piece 3
```

The directory is wiped and rewritten for each slug at the start of that slug's
extraction, so it always reflects the most recent sweep and never accumulates.
`outputs/` is already gitignored.

`run_extract` is called with `debug=True` so the viewer survives. **Open
measurement:** the debug trace's cost in wall time and disk is unknown. It is
measured during implementation on one sheet; if it exceeds +30% wall time or
100MB per sheet, `debug=True` becomes opt-in behind `tools/regress.py --debug`
and the default sweep keeps only render/overlay/entities. The decision is
recorded in the implementation notes either way — not guessed here.

### Piece 2 — ids in the report

`regression/report.py` formats `r.unreviewed`, which holds raw entity dicts
straight from `final_entities.json`. Those dicts already carry `entity_id`.

```
    REVIEW new door_0007  conf 0.82  (1204,883)
```

The same treatment for closed-deferred and drift lines where an id is available.
The id is display-only: it identifies a detection within *this* sweep's output
so the human can find it on the overlay, and is never written to ground truth.

### Piece 3 — per-category review overlays

New module `regression/review_render.py`, called by **the sweep**, not by
`review.py`. The sweep is what computes which items are unreviewed
(`SheetResult.unreviewed`) and it already has `render.png` in hand, so it draws
the overlays immediately after scoring each sheet. `review.py` only reads them.

For each page × entity type that has unreviewed items, draw those items — and
only those items — on a copy of `render.png`, each stamped with a short id
(`door_0007` → `d7`, `window_0003` → `w3`, `room_0002` → `r2`), colour-coded by
type. Write to `outputs/regress/<slug>/pages/page_NN/review_<type>.png`.

Per-category rather than one combined image because the review loop is
per-category: the doors pass should not be cluttered with windows.

Rooms draw the closed polygon from `Entity.attributes["polygon"]`, not the bbox
— the bbox of an L-shaped room is a lie about its extent, and the shape is
precisely what is being judged.

Short ids collide only if two entity types share a prefix letter and the same
ordinal, which they cannot: the prefix comes from the type.

### Piece 4 — `tools/review.py`, the verdict recorder

```bash
python tools/review.py            # every sheet with unreviewed items
python tools/review.py s01        # one sheet
python tools/review.py s01 s07    # several
```

Reads the persisted sweep output under `outputs/regress/<slug>/`. It does **not**
re-run detection — a sweep must have been run first; if the directory is absent
the tool says so and exits.

Walk order: **sheet → page → category**, categories in the fixed order
`door, window, room, label, schedule`. Each category is a self-contained
screen — the image path is printed, then the selection happens, then it moves on.

```
s01 page 1 — DOORS (14 unreviewed)
  open: outputs/regress/s01/pages/page_01/review_door.png

  ? Select CORRECT doors   (type to filter, space to tick, enter to submit)
  ❯ ◉ d7   conf 0.82  (1204,883)
    ◯ d11  conf 0.61  (455,1290)
    ◉ d12  conf 0.79  (1180,640)

  ? Of the remaining 1 — select the ones that are WRONG
    (leave unticked to postpone; they reappear next sweep)
  ❯ ◉ d11  conf 0.61  (455,1290)
```

**Two passes, not one.** A single checkbox forces a binary: ticked correct,
unticked wrong. That is false — "I cannot tell from this image" is a real and
common answer, and forcing it into `false_positives` poisons ground truth
permanently. Pass 1 selects correct → `confirmed`. Pass 2 runs over pass 1's
leftovers and selects wrong → `false_positives`. Anything unticked in both stays
unreviewed and reappears in the next sweep. Deferring costs nothing.

Rooms get one extra prompt per confirmed room: `approved` or `partial`, plus an
optional free-text note. The two axes are independent and both are recorded in
V1 (see piece 5); only V2 scores the `shape` axis.

**Widget:** `InquirerPy` — `prompt_toolkit`-based, pure Python, gives the
filterable checkbox from the reference UX. One line added to `requirements.txt`.
It is a dev-tool dependency only; nothing in `pipeline.py` or `detection/`
imports it.

**Writes.** On submitting a sheet:

- `tests/ground_truth/<slug>.json` — append to `confirmed` / `false_positives`.
  Existing entries are never reordered, rewritten, or dropped. `pdf_sha256` is
  set from the manifest; `reviewed` is set to today.
- `fixtures/MANIFEST.json` — that slug's entry gets `"labeled": true`.

Both writes happen once per sheet, after that sheet's categories are done, so an
interrupted session loses at most the sheet in progress. Ground truth and the
manifest are the only files this tool mutates.

**Failure modes.** A sheet whose sweep output is missing, whose PDF sha no longer
matches the manifest, or whose ground truth is unreadable is reported and
skipped, not partially written.

### Piece 5 — room verdicts carry the polygon

`regression/ground_truth.TruthItem` gains three optional fields:

| Field | Type | Meaning |
|---|---|---|
| `polygon` | `list[[x, y]]` or absent | the reviewed room outline |
| `shape` | `"partial"` \| `"approved"` \| absent | is this polygon the shape you want |
| `note` | `str` or absent | free text, e.g. "doesn't reach the bay window" |

All three are optional; `s01.json` loads unchanged. In V1 `review.py` **writes**
them and nothing **reads** them — matching stays bbox-based for every type.

This is deliberate and is what makes the V1/V2 split safe: rooms labeled during
V1 already carry a baseline polygon, so V2's drift scoring has something to
compare against and no room needs re-reviewing.

### Piece 6 (V2) — room drift scoring

`regression/matching.py` scores a room on **polygon IoU** when the truth item
carries a polygon, falling back to bbox IoU when it does not. Three bands:

| IoU | Outcome | Exit code |
|---|---|---|
| `< 0.5` | LOST — the room is effectively gone | 1 |
| `0.5 ≤ IoU < 0.98` | SHAPE DRIFT — REVIEW only | 0 |
| `≥ 0.98` | unchanged | 0 |

Drift reports measurable facts only:

```
REVIEW room_0002 SHAPE DRIFT (approved)  IoU 0.91  −38px²
       bbox edges moved: bottom +12.0px
REVIEW room_0004 SHAPE DRIFT (partial)   IoU 0.74  +2410px²
       bbox edges moved: left −31.0px, top −4.0px
```

`(approved)` versus `(partial)` is the whole point of the second axis: drift on a
shape the user signed off on is suspicious; drift on a known-incomplete baseline
is the backlog moving. Neither fails the sweep.

`review.py` gains a drift pass per page: a checkbox of drifted rooms, "accept the
NEW shape as the baseline". Accepted → the stored polygon is overwritten with the
current one. Not accepted → the old polygon stays pinned and drift re-reports on
every subsequent sweep until it is resolved. An unaccepted drift is an
unresolved, permanently visible change, not a silently absorbed one.

The `review_room.png` overlay draws a drifted room as the old polygon dashed and
the new one solid.

**The first-run case, resolved.** A room that is real but misshapen is
`confirmed` with `shape: "partial"` and a note. The polygon is stored as a
*baseline to detect change against*, not as an ideal. Later sweeps drift; each
improvement is accepted as the new baseline. When the shape is finally right the
user flips it to `approved`, and from then on drift on it prints as the loud
variant. Accept-then-accept-again is the intended loop.

**Threshold rationale.** 0.98 is a starting value, not a measured one — a real
room of ~40k px² tolerates roughly a 400px² change before flagging, about a 2px
shift on one 200px edge. It is a single named constant
(`ROOM_DRIFT_IOU` in `regression/matching.py`) and is expected to be retuned once
the first few labeled sheets show the real jitter distribution.

### Piece 7 (V2) — the agent path

No new mechanism. `tools/review.py` gains non-interactive flags over the same
writer:

```bash
python tools/review.py s01 --confirm door_0007,window_0003 \
                           --reject door_0011 \
                           --accept-shape room_0004 \
                           --shape room_0002=partial \
                           --note room_0002="doesn't reach the bay window"
```

Ids are resolved against the persisted sweep output for that slug, which is why
they are safe here despite being ordinal: the ids and the entities come from the
same run directory. An id that does not resolve is an error, not a silent no-op.

The agent's role is transcription. It runs `tools/regress.py --json`, reads
`unreviewed`, presents the detections to the user, and records the answers it is
given. It never originates a verdict. The flags exist so the user does not type
them; the user is still the one deciding.

## Testing

Fast tier (`python -m unittest discover tests`), all synthetic — no PDF is read.

1. **Verdict writer appends without clobbering.** Pre-existing `confirmed`
   entries survive byte-identical; new ones are appended; `reviewed` and manifest
   `labeled` are set.
2. **Backward compatibility.** A ground-truth file with no `polygon`/`shape`/
   `note` loads and scores exactly as it does today.
3. **Two-pass deferral.** An item ticked in neither pass appears in neither
   `confirmed` nor `false_positives`, and is still unreviewed on the next sweep.
4. **Interrupted sheet.** Aborting mid-sheet leaves ground truth untouched.
5. **Polygon-IoU band boundaries** (V2) — 0.5 and `ROOM_DRIFT_IOU` on both sides.
6. **Drift report fields** (V2) — carries IoU, signed area delta, and per-edge
   bbox deltas, and no semantic text.
7. **Flags equal interactive** (V2) — the same verdicts via `--confirm/--reject`
   produce a byte-identical ground-truth file.
8. **Unaccepted drift re-reports** (V2) — a drift not accepted still drifts on
   the next sweep.

The interactive prompt layer is kept thin and separated from the verdict writer
so the writer is testable without driving a TTY.

## Effort

- V1 (pieces 1–5): about a day.
- V2 (pieces 6–7): about half a day, after V1 has been used on real sheets.
- Labeling the 19 unlabeled sheets is manual and is the user's time: roughly
  15–40 minutes per sheet depending on detection count.

## Open questions

1. **Debug-trace cost** (piece 1) — measured during implementation, decides
   whether `debug=True` is the sweep default or opt-in.
2. **`ROOM_DRIFT_IOU`** (piece 6) — 0.98 is provisional and retuned against the
   observed jitter of the first labeled sheets.
