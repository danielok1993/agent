# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Local Python CLI POC for architectural PDF extraction. The research question is whether CAD-originated PDFs carry enough native vector/text data that a vector-first + Gemini-validation pipeline beats vision-only extraction of doors, windows, walls, labels, and schedules. `project.md` is the original spec — treat it as the source of truth for scope and acceptance criteria.

## Algorithm reference

**Before changing door detection, read `docs/door-detection-tuning-guide.md`.** It catalogs the six known swing topologies (full Bezier, chained Beziers, clean polyline, polyline + Y-junction stop, polyline + cycle cap, polyline + linear cap extension), every tunable constant with rationale, known false-positive patterns, the per-PDF detection state to guard against regressions, and the debug-trace diagnostic playbook for tracing missed/false detections.

## Commands

```bash
# Setup
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Inspect — terminal summary, no Gemini, no files written
python app.py inspect path/to/drawing.pdf [--pages 1,3-5]

# Extract — full pipeline, writes to outputs/<timestamp>/
python app.py extract path/to/drawing.pdf [--pages SPEC] [--out DIR]
                                          [--no-gemini] [--refresh-regions]
                                          [--disable-rooms] [--disable-windows]
                                          [--debug] [--svg]
                                          [--ceiling-height M] [--door-height M]
                                          [--window-height M]
# --disable-walls is a deprecated alias for --disable-rooms (skips the wall
# network + room detection together).
# --refresh-regions ignores the cached region classification for the page
# and calls Gemini again instead of reusing gemini/region_cache.py's entry.
# Heights feed the per-room quantity takeoff (takeoff/). --ceiling-height is
# prompted for on a tty when absent (same gate as the scale prompt); defaults
# 2.4 / 2.1 / 1.2 m.

# Batch extract — discovers fixtures/sheets/*.pdf, prompts for detection options
# interactively, runs `app.py extract` 5-at-a-time (ProcessPoolExecutor)
python batch_extract.py

# Tests (unittest)
python -m unittest discover tests
python -m unittest tests.test_door_assembly.TestDoorAssembly.test_<name>
```

No PDF is committed to this repo. For a quick run, download the regression
corpus (see "Regression testing" below) and point `app.py` at any sheet under
`fixtures/sheets/` — `s01` (formerly `floor-plans.pdf`) and `s02` (formerly
`5-1133-WD03.pdf`) are the two primary references.

`--svg` additionally writes `page.svg` per page — MuPDF's own vector redraw of
the page (`extraction/renderer.render_page_svg`) at the same 150-DPI matrix as
`render.png`, so entity/takeoff bboxes overlay it unchanged and `/Rotate` is
already baked in. It is a redraw of the PDF, not of the extracted primitives, so
it never shows what detection saw. Off by default: measured across the corpus it
costs <=0.2 s/sheet but 0.2-21 MB (image-heavy sheets inline their rasters as
base64).

`--debug` writes `debug_trace.json` + a self-contained `debug_viewer.html` per page (per-primitive detection trace for diagnosing missed/false door detections — see the tuning guide's debug-trace playbook).

## Regression testing

**Before changing detection, read `docs/regression-testing-guide.md`.** It covers
reading the sweep report, the ground-truth file format and the rules for editing
it, adopting/revising sheets, the invariants (no committed PDFs, no
address-bearing text), and the traps that have already shipped bugs here.

Two tiers:

```bash
python -m unittest discover tests   # ~10s — synthetic topologies, run constantly
python tools/regress.py             # ~3min — 20 real sheets vs. committed ground truth
```

The corpus lives in `fixtures/sheets/` and is **not** committed (NDA). Download
the bundle — see `fixtures/MANIFEST.json`'s `storage` field for how to get it —
and verify with `python tools/fetch_fixtures.py`. Sheets are named by slug
(`s01`…`s20`); the two primary references are `s01` (formerly floor-plans.pdf)
and `s02` (the WD03 working drawing).

`tests/ground_truth/sNN.json` holds the user's verdicts and is committed. Three
lists per page: `confirmed` (correct detections), `false_positives` (wrong
detections, matched against emitted entities only), and `deferred` (misses the
user reported that we consciously chose not to fix). Matching is geometric —
type + IoU ≥ 0.5 — because entity ids are ordinal and shift when detection
changes.

`regress.py` exits 1 on a lost `confirmed` entity, a returned false positive, or
a sheet whose bytes no longer match the manifest — plus two more triggers the
guide's §6 table covers in full (an unscored ground-truth page, and a
manifest sheet marked `"labeled": true` whose truth file is missing or
reverted to `reviewed: null`); 2 when sheets are missing from disk; 0
otherwise. **New detections never fail the sweep** — they print under REVIEW
and wait for a verdict.

The loop when tuning detection:

1. `python tools/regress.py`
2. Open `outputs/regress/<slug>/<timestamp>/pages/page_NN/review_<type>.png`
   — every unreviewed detection is stamped with a short id (`d7` = door_0007)
   matching the sweep's REVIEW lines. Output persists there (gitignored,
   wiped per slug on that slug's next sweep) precisely so this image exists
   to open; `debug_viewer.html` is opt-in (`regress.py --debug`) for the hard
   cases, not written by default — it cost 200-300MB/sheet on the corpus's
   heaviest sheets.
3. `python tools/review.py <slug>` — ticks the correct detections, then the
   wrong ones (Space to toggle); anything ticked in neither is
   postponed and reappears next sweep. It writes `tests/ground_truth/<slug>.json`
   and sets `"labeled": true` in `fixtures/MANIFEST.json` (absent/false means
   adopted-but-unlabeled, which stays valid for every not-yet-reviewed sheet).
   Once flagged, the sweep exits 1 if that ground truth ever goes missing or
   reverts to `reviewed: null` — a durable, diffable record that the verdicts
   existed, so their loss can't pass silently. Commit both files as a data
   commit.
4. Fix the algorithm, and pin the topology with a synthetic test in the fast tier.
5. `regress.py` again: no lost `confirmed`, no returned false positives. A
   `deferred` entry that flips to CLOSED is confirmed by the user, then promoted
   to `confirmed` by hand — `tools/review.py` only records verdicts on a
   sweep's unreviewed detections, not this promotion.
   To SEE what a change did rather than read verdict deltas:
   `python tools/compare_sweeps.py <slug> --snapshot` after the baseline sweep
   (a re-sweep wipes the slug's previous run), then `python tools/compare_sweeps.py <slug>`
   after the re-sweep — writes `outputs/compare/<slug>/page_NN_side_by_side.png`
   (both runs, entities coloured by verdict) and `page_NN_changes.png` (a
   before|after zoom row per entity present in only one run). Guide §4b.

See `docs/regression-testing-guide.md` §4/§8 for the sweep-output and
review-tooling details, and §6 for the full exit-code table.

A revised drawing is adopted as a **new** slug (`python tools/add_sheet.py`),
never dropped over an existing one — an existing slug's bytes are immutable
because its ground truth is pinned to them.

## Module layout

The root holds thin orchestration entry points; detection and I/O live in packages (the `d61f0e2` refactor split the old flat modules — `heuristics.py`, `extractor.py`, `gemini_client.py`, etc. — and the 3,679-line `heuristics.py` monolith). Code movement only; behavior and the `outputs/` JSON contract are unchanged.

```
app.py             # argparse shell
pipeline.py        # run_extract — the 7-stage orchestrator
inspector.py       # inspect-command logic
batch_extract.py   # interactive parallel batch runner over fixtures/sheets/*.pdf
models.py          # shared dataclasses (depended on by everything)

extraction/        # PDF -> normalized primitives + rendering (owns SCALE)
  extractor.py  plumber.py  renderer.py
detection/         # heuristic detection (the split monolith)
  __init__.py      # public facade: run_heuristics + detect_* re-exported
  orchestrator.py  # run_heuristics (named to avoid clash with root pipeline.py)
  geometry.py      # shared primitives (_distance, _line_angle_deg, …)
  layers.py        # OCG layer-name hints/priors (_layer_hint, _layer_strong_prior)
                   # + the annotation veto (_layer_annotation_veto): ink on a layer
                   # whose name says callout/dimension never becomes a wall face
                   # — confidence boost when a layer name names the element type
                   # (exact token, singular or plural: A325G_INT_DOORS, WINDOWS, RR_Walls;
                   # only when the layer names ONE class — "RR_New Doors and
                   # Windows" is a grouping layer and hints at neither)
  walls.py         # INTERNAL wall-centerline network (WallNetwork) — walls are
                   # never emitted as candidates; feeds rooms.py + postprocess.py
  rooms.py         # detect_rooms — rooms = free-space components between wall
                   # solids (shapely); door/window bboxes seal the openings
  windows.py  labels.py  schedules.py  postprocess.py
  doors/           # door subpackage, acyclic: constants <- arcs/leaves/shape/sliding <- folding <- assembly <- detect
                   # sliding.py: arc-less sliding doors from oriented panel-rectangle
                   # patterns (leaf_pair + pocket_leaf + parked_leaf — the last is the
                   # fill-less tier: a stroked ring parked at a wall-band jamb, slide
                   # law opening ≈ panel length) — see the tuning guide §3.9
                   # folding.py: arc-less folding/bifold doors from hinge-connected
                   # white leaf panels (chain + parked stack_pair) plus open_v — the
                   # fill-less tier: a lone half-open V of double-line stroked leaves,
                   # jamb-anchored + span law — tuning guide §3.10
layout/            # page segmentation — splits a sheet into its drawings
  constants.py  occupancy.py  segmenter.py  clips.py  filter.py
gemini/client.py        # Vertex AI client (was gemini_client.py)
gemini/classifier.py    # region classification (replaced candidate validation)
gemini/region_cache.py  # classification cache, keyed by page content + region geometry
gemini/room_labeler.py     # room names from in-polygon text (one text-only call)
gemini/room_label_cache.py # label cache, keyed by page + room geometry + prompt version
scale/            # drawing-scale resolution: /VP measure viewports, scale text,
                  # a tty-gated prompt, and geometric binding to floor_plan regions;
                  # dimensions.py — the drawing's ticked dimension strings as a scale
                  # MEASUREMENT (verifies or contradicts the resolved scale for the
                  # detection gates in factor.py and for the takeoff's `verified`)
takeoff/           # rooms + scale + heights → floor / ceiling / net wall m² per room
                   # (units, heights, per-room scale + sheet-size verification,
                   # opening assignment, plausibility — dimension strings /
                   # door-leaf band, compute_takeoff). Pure; wired in
                   # pipeline.run_extract after finalize_candidates.
  document.py      # serialisation only — the takeoff.json overlay document
debug/             # trace.py (DebugTraceCollector) + renderer.py (HTML viewer)
tools/             # standalone dev scripts (numpy/cv2)
```

Import from the `detection` facade (`from detection import run_heuristics, detect_doors`) rather than reaching into submodules. Tunable constants are co-located with their detector: `DOOR_*` in `detection/doors/constants.py`, `WINDOW_*`/`WALL_*`/`ROOM_*`/`LABEL_*`/`SCHEDULE_*` in the matching `detection/*.py`, cross-validation `CROSS_*` in `detection/postprocess.py`. Tests import internals from their real homes (e.g. `from detection.doors.arcs import _prune_arc_spurs`) — there is no compatibility shim.

Room detection: order matters — doors/windows detect first, then `detect_wall_network(paths, text_spans, exclude_path_indices)` builds the internal wall-centerline network (walls are never emitted as candidates), and `detect_rooms` extracts rooms as the connected free-space components of the page after subtracting barriers. Barriers are ALLOWLISTED wall evidence, not all linework — room-interior ink (floor-tile grids, furniture outlines, sanitary symbols, text masks) must not chop the free space — in four tiers: wall solids (paired centerline segments dilated to their measured thickness), wall-fill polygons, thin buffers of qualifying faces, and white (background-fill) rings, completed by opening seals at the surviving doors and windows. Rooms are heuristic-only: never sent to Gemini, they bypass the `OFFLINE_MIN_CONFIDENCE` floors and NMS, and carry the closed polygon in `Candidate.evidence["polygon"]` / `Entity.attributes["polygon"]`.

**Before changing wall or room detection, read `docs/wall-network-rules.md` and `docs/room-detection-rules.md`.** They carry every rule, its drawing-convention rationale, its measured margins and the sheets those were measured on — most fixture classes (paving, hatch, tile grids, stairs, counters, wardrobes, radiators, leader arrows) already have a rule, so the correct fix is usually a gap in an existing rule rather than a new one. `docs/wall-network-rules.md` covers the exclusion sets, face collection, lattice and stair demotion, the pairing tiers, the weak tier's material gate, pen gating and the doorway veto, fill rings and seams, and the collinear-merge anchor. `docs/room-detection-rules.md` covers the four barrier tiers, jamb rings and door linings, window seals, door plugs, the free-space filters, the wall-recess / band-pocket / blind-window drops, and the entrance rule.

Wall/room world-space gates (the `W`-classed constants in `docs/scale-normalization-findings.md` §4) scale via a per-page factor threaded from `scale.factor.detection_scale(page_scales, regions, page_number)` into `detect_wall_network` / `detect_rooms` as `scale_factor`: `f = 50 / nominal_denominator`, so f=1.0 (identity, unchanged behavior) at 1:50 and on unresolved-scale pages, f=0.5 at 1:100. Paper-space (`P`) and dimensionless (`D`) constants are left unscaled. **Before touching any gate constant, read `docs/scale-normalization-findings.md` §4** — its table says whether that gate scales with drawing scale, **§4g** carries the full rules for how the factor is resolved and threaded (dimension-string verification, mixed-scale sheets, the warning codes), and §4f records why feeding a measured scale straight to the gates regressed s01.

The W references were re-derived at the sheets' TRUE scales over iterations 1–3. **The census, the per-constant outcomes and the step-by-step log live in `docs/w-gate-census-2026-09-04.md`, `docs/w-gate-recalibration-handoff.md` (start at "Iteration 1–3 summary, moved from CLAUDE.md") and `docs/w-gate-iter3-checkpoints/`.** Read the handoff's outcome sections before moving any W-classed constant: every census row flagged ⚠ ("discriminator, not number") broke the moment its number moved, always by admitting a drawn fixture another gate had been holding out.

## Gemini / GCP auth

`gemini/client.py` uses Vertex AI via `google-genai` (`vertexai=True`). Required before the pipeline can call Gemini:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>           # or set GOOGLE_CLOUD_PROJECT
# Optional: GOOGLE_CLOUD_LOCATION (default us-central1)
```

Model is hard-coded to `gemini-2.5-flash`, called twice per page at most:
once for region classification (`gemini/classifier.py`, image crops, before
detection) and once for room labelling (`gemini/room_labeler.py`, text only,
after `finalize_candidates`). Both are schema-constrained and separately
cached (`gemini/region_cache.py`, keyed by page content + region geometry;
`gemini/room_label_cache.py`, keyed by page content + room geometry + prompt
version). Gemini no longer votes on individual door/window/room/label/schedule
candidates; `pipeline.finalize_candidates` applies the `OFFLINE_MIN_CONFIDENCE`
floors unconditionally regardless of Gemini. `--no-gemini` skips both calls
and reuses whichever cache exists for the page; a miss warns instead of
calling out — `REGION_CACHE_MISS_OFFLINE` falls back to detecting the whole,
unfiltered page, `ROOM_LABEL_NO_GEMINI` just leaves that page's rooms
unnamed. Pass `--refresh-regions` to force a fresh classification call even
when a region cache entry exists; there is no equivalent flag for room
labels, so to force a single page's labels to be recomputed, delete that
page's cache file: `.room_labels_cache/<pdf-stem>_p<NN>_*.json`.

The call is schema-constrained (`classifier.RESPONSE_SCHEMA` passed as `response_schema`, not plain JSON mode): the decoder cannot emit a response that fails to parse or a `type` outside `REGION_TYPES` — measured 2026-08-05 on `LOCATION_PLAN…-s11`, where an unconstrained response started as valid JSON, degenerated mid-stream into an off-topic fragment, and lost an object separator. Should a response still fail to parse, `resolve_page_regions` treats it exactly like the raising failure path — `REGION_CLASSIFY_PARSE_FAILURE`, whole page detected, **no cache write**: an all-`unclassified` region list reads downstream as "no floor plan" (Rule 1) and skips detection, so caching one would make a one-off flake permanent until the next `--refresh-regions`. A *partial* response (`REGION_CLASSIFY_INCOMPLETE` — some regions unaddressed or type-coerced) is real information and still caches.

## Pipeline architecture

`app.py` is a thin argparse shell; the real flow is in `pipeline.py::run_extract`, which loops pages and runs seven stages per page:

1. `extraction.extractor.extract_page` — PyMuPDF `get_drawings()` / `get_text("dict")` / `get_images()` / `get_ocgs()`. **All coordinates are normalized to 150-DPI pixel space via `SCALE = 150/72`** at extraction time. Downstream code (detection, renderer, Gemini bboxes) assumes pixel-space. Don't reintroduce point-space anywhere past `extraction/extractor.py` / `extraction/plumber.py`. The transform is `extractor.page_transform` — SCALE composed with the page's `/Rotate` — because `get_drawings()`/`get_text()` return UNROTATED mediabox coordinates while `page.rect` (the source of `width_px`/`height_px`) and the render both honour rotation; it is exactly `x * SCALE` when rotation is 0. Pen widths take the transform's scale only: a rotation does not change stroke width. A stroked path whose PDF line width is 0 is recorded at `ZERO_WIDTH_STROKE_PX` (1.0 px), not 0.0: PDF 32000-1 §8.4.3.2 defines width 0 as "the thinnest line that can be rendered at device resolution: 1 device pixel wide" — a pen, and in this 150-DPI frame a 1px one. Some CAD exporters plot every lineweight that way (s05: all 12,958 stroked drawings, s12: all 17,168), giving a single-pen sheet like s06 whose render shows 1px linework everywhere; recorded as 0.0 that pen fell under every stroke gate at once (walls.py: strong ≥ 0.5, hairline > 0) and s05 contributed no wall faces — no rooms at all, doors only. Fill-only paths (no stroke colour) keep 0.0; every other width-0 item on the corpus is a self-coloured fill outline (s03 165, s04 416, s08 415, s17 410 — the invisible seam-hiding outline `_stroke_is_visible` already treats as area), which s11/s16 already carry at width > 0.
2. `extraction.renderer.render_page_png` — renders the page PNG at the same 150 DPI used for coordinate normalization, so heuristic bboxes overlay cleanly.
3. `layout.segment_page` + `gemini.classifier.classify_regions` — the page is
   split into drawing regions at its whitespace gutters (deterministic, from the
   vector ink's own coordinates), and one Gemini call classifies every region
   from a per-region crop. A page the cut cannot split at all is retried once
   with text spans excluded from the ink map (text bboxes bridge otherwise-
   generous gutters — measured on s15: 1 leaf with text, 8 regions without),
   and the resulting regions are grown to re-absorb nearby text so
   classification crops keep their captions (source: "paths-only"). **The ink map's construction, the nested sheet-furniture skip and the four gutter tiers are in `docs/page-segmentation.md`.** Detection
   then runs ONCE over the union of the `floor_plan` regions, so elevations,
   location plans and title blocks never reach the detectors. Per-candidate
   Gemini validation was removed on
   2026-07-28 — see docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md.
   Orchestrated by `pipeline.resolve_page_regions`, which caches the classification
   (`gemini/region_cache.py`, keyed by page content AND the region geometry it was
   made against, so a change to `layout/` is a cache miss rather than a silent reuse
   of stale bboxes — `--refresh-regions` bypasses it) and writes `regions.json` +
   `region_crops/`. Filtering is suppressed (regions still recorded, whole page
   detected, `REGION_COVERAGE_TOO_LOW`) when the regions hold less than
   `REGION_MIN_COVERAGE_FRAC` (0.90) of the page's paths: `SEGMENT_MIN_REGION_SIDE_PX`
   discards small leaves and `filter_page_data` would then delete real drawing with
   them (measured across `plans/`: 0.65 on `s11`, 0.85 on `s16`, 0.89 on
   `s05`, 0.94–1.00 on every other sheet).
4. `extraction.plumber.extract_plumber_page` — pdfplumber cross-check (chars/lines/rects/curves/images/tables). `compare_counts` emits `PLUMBER_LARGE_DELTA` warnings when PyMuPDF vs pdfplumber geometry diverges >50%. Tables here feed schedule detection.
5. `detection.run_heuristics` (`detection/orchestrator.py`) — deterministic detection of doors / windows / rooms / labels / schedules, run once over the region-filtered page data from stage 3 (skipped entirely only when a split page has neither a `floor_plan` nor a `schedule_table` region; a schedule-only sheet still runs heuristics over an empty path set so `detect_schedules` can read the schedule). Doors and windows detect first; the internal wall-centerline network (`detection/walls.py::detect_wall_network`, never emitted as candidates) then cross-validates them and feeds `detection/rooms.py::detect_rooms`, which subtracts wall solids, face linework, and opening seals (wall-plane plugs at doors, bboxes at windows) from the page and emits the enclosed free-space components as room polygons. `--disable-rooms` / `--disable-windows` exist because each detector can dominate noise on different drawing styles. Pass a `DebugTraceCollector` (via `--debug`) to record per-primitive reasoning.
6. `pipeline.finalize_candidates` + `renderer.draw_overlay` — Gemini no longer votes on individual candidates, so `finalize_candidates` applies the `OFFLINE_MIN_CONFIDENCE` floors unconditionally: candidates below threshold move to `rejected` and are not promoted to entities. Room candidates bypass the floors — they are heuristic-only by design and always promoted, with the polygon in `Entity.attributes`. `draw_overlay` then draws entities, rejected candidates, and the page's region outlines onto the render. Between finalisation and the takeoff, `pipeline.resolve_room_labels` names each room from the text drawn in and within `ROOM_LABEL_BUFFER_PX` (40px) of its polygon — one text-only Gemini call per page, cached by page content + room geometry + prompt version (`gemini/room_label_cache.py`). A returned name is kept only when every word of it appears in that room's own spans (`room_labeler.is_grounded`), so a name is read off the drawing or the room stays unnamed. Labels never feed the quantity maths.

   After finalisation, `takeoff.compute_takeoff` converts each room polygon
   (buffered out by `ROOM_WALL_DILATE_PX` to undo the barrier standoff) into
   metres at 0.16933 mm/px × the room's denominator (its floor_plan region's
   scale; a region the resolver marked unresolved leaves its rooms UNSCALED —
   the detection scale is borrowed only by rooms in no region / no verdict,
   never across plans on a mixed-scale sheet; else no numbers +
   `TAKEOFF_NO_SCALE`),
   assigns door/window entities to the rooms whose grown polygon touches them
   (widths from `opening_line` / `opening_width_px` / `opening_span_px`, bbox
   edge as last resort), and writes `takeoff.json`; the block is mirrored onto
   the room entity's `attributes["takeoff"]` and totals into `summary.json`.
   `scale.verified` is true for viewport/user scales, or text scales whose
   title-block sheet size matches the mediabox; `SCALE_UNVERIFIED` /
   `SCALE_PRINT_RESIZED` flag the rest. Then `takeoff/plausibility.py` reads
   the drawing itself (one verdict per denominator in use on the page, on
   `scale.plausibility`): ticked dimension lines with a numeric label beside
   them (`3600`, `7,434`, `4.50`; ≥ 3 matches, reusing
   `walls._dimension_line_indices`) measure the scale directly — agreement
   within 5 % verifies even a text-only scale, disagreement past 15 % is
   `SCALE_IMPLAUSIBLE` and unverifies even a typed one (s01: typed 1:50, 31
   dimensions say 1:92.2); otherwise the median door leaf (arc radius / pair
   chord ÷ 2 / panel length, ≥ 2 doors) must fall in 0.55–1.20 m (corpus
   medians 0.64–0.90; s01 0.38) or the verdict is implausible with the
   print-factor correction (×0.25/0.5/2/4) named. Numbers are NEVER swapped —
   the verdict only gates `verified`. Heights: flag → tty prompt → default.

   `takeoff/document.py` then serialises the page into `takeoff.json`. Rooms and
   openings are sibling arrays cross-referenced by id rather than openings nested
   per room, so a door serving two rooms is one record carrying both `room_ids`.
   Geometry is 150-DPI pixels — the same space as `final_entities.json` and
   `render.png` — with a `page_frame` block recording it; `extractor.page_transform`
   has already applied the page's `/Rotate`, so `rotation` is provenance and a
   consumer must not re-apply it. A room whose scale did not resolve is kept, with
   its polygon, `scale: null` and `quantities: null`.
7. JSON dump (`primitives.json`, `candidates.json`, `final_entities.json`, `pdfplumber_comparison.json`) and warning collection.

Aggregate `summary.json` and `warnings.json` are written at the run root once all pages finish.

## Output layout

```
outputs/<YYYY-MM-DD_HH-MM-SS>/
├── summary.json              # per-page summaries + totals + PDF metadata
├── warnings.json             # flat list across all pages
└── pages/page_NN/
    ├── render.png            # 150 DPI render
    ├── page.svg              # --svg only: MuPDF vector redraw, same 150-DPI frame
    ├── overlay.png           # entities + rejected + region outlines drawn on render
    ├── primitives.json       # raw PyMuPDF paths/text/images
    ├── pdfplumber_comparison.json
    ├── regions.json          # segmented regions + their Gemini classification
    ├── region_crops/         # classification-call only: per-region PNG crops sent to
    │                         # Gemini (absent on a cache hit, --no-gemini, or a raster page)
    ├── candidates.json       # heuristic output
    ├── final_entities.json   # finalized entities + rejected
    ├── takeoff.json          # THE overlay document: page_frame (150-DPI px space),
    │                         # scale + evidence, heights, rooms[] (polygon, bbox,
    │                         # label, opening_ids, quantities), openings[] (bbox,
    │                         # type, tag, room_ids, widths), totals, warnings.
    │                         # schema_version 1. Rooms and openings are sibling
    │                         # arrays cross-referenced by id — one physical opening
    │                         # is one record, whichever rooms it serves.
    ├── debug_trace.json      # --debug only: per-primitive detection trace
    └── debug_viewer.html     # --debug only: self-contained trace viewer
```

## Data model

All shared types live in `models.py` as `@dataclass`es: `PathPrimitive`, `TextSpan`, `ImageRef`, `PageData`, `Candidate`, `Entity`. `BBox` is a `(x0, y0, x1, y1)` tuple in **150-DPI pixels, top-left origin, y-down**. Page numbers in serialized output are **1-based**; `page_indices` passed between functions are **0-based**.

Notable extractor behavior: `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful, so do not re-bundle multi-item drawings.

## Warning codes

Warnings are structured dicts with `warning_code`, `severity`, `message`,
`page_number`. The set is intentionally small — when adding a new warning,
follow the existing `SCREAMING_SNAKE_CASE` convention and emit from
`pipeline.collect_warnings`, `extraction.plumber.compare_counts`,
`gemini.client._validate_response`, `scale.resolver.resolve_page_scales`
(which returns them on `PageScales.warnings` for `run_extract` to fold into
the page's warning list — only the resolver knows which tier resolved a
region, so only it can say why one did not), `scale.factor.detection_scale`
(on `DetectionScale.warnings`: `SCALE_FACTOR_MEASURED_ONLY` — a non-standard,
non-viewport scale the drawing's dimension strings do not verify runs the
gates at identity; `SCALE_FACTOR_FROM_DIMENSIONS` — the dimension strings
contradict the resolved scale past 15 %, the gates run at the measured scale
while the takeoff keeps the resolved one; `SCALE_MIXED_FLOOR_PLANS`,
`SCALE_FACTOR_CLAMPED`), or
`takeoff.quantities.compute_takeoff` (same shape, on `TakeoffPage.warnings`:
`TAKEOFF_NO_SCALE` — a room with no resolvable drawing scale gets no
quantities; `SCALE_UNVERIFIED` — a measured room's scale is text-only and
untied to a viewport/user source or a sheet-size confirmation;
`SCALE_PRINT_RESIZED` — the declared title-block sheet size mismatches the
mediabox by ~2× (half-/double-size print); `TAKEOFF_OPENING_TALLER_THAN_CEILING`
— an opening height was clamped to the ceiling; `TAKEOFF_OPENING_MULTI_ROOM`
— an opening reached 3+ rooms and was capped to the two nearest;
`SCALE_IMPLAUSIBLE` — the drawing's dimension strings or door-leaf widths
contradict the resolved scale, `verified` is false, numbers unchanged), or
`pipeline.resolve_room_labels` (`ROOM_LABEL_NO_GEMINI` — no cached labels
and Gemini disabled/unavailable, rooms stay unnamed; `ROOM_LABEL_FAILED` —
the labelling call raised (auth, network, bug); `ROOM_LABEL_PARSE_FAILURE` —
a response that didn't parse, not cached, same reasoning as
`REGION_CLASSIFY_PARSE_FAILURE`; `ROOM_LABEL_UNGROUNDED` — a returned name
failed the grounding check and was dropped; `ROOM_LABEL_CACHE_WRITE_FAILED`
— labelling succeeded but the cache write failed, so the next run calls
Gemini again).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).


# Other rules

- Never add co authered by claude to the git commit
