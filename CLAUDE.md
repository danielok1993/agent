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
pip install -r requirements.txt

# Inspect — terminal summary, no Gemini, no files written
python app.py inspect path/to/drawing.pdf [--pages 1,3-5]

# Extract — full pipeline, writes to outputs/<timestamp>/
python app.py extract path/to/drawing.pdf [--pages SPEC] [--out DIR]
                                          [--no-gemini]
                                          [--disable-rooms] [--disable-windows]
                                          [--debug]
# --disable-walls is a deprecated alias for --disable-rooms (skips the wall
# network + room detection together).

# Batch extract — discovers plans/*.pdf, prompts for detection options
# interactively, runs `app.py extract` 5-at-a-time (ProcessPoolExecutor)
python batch_extract.py

# Tests (unittest)
python -m unittest discover tests
python -m unittest tests.test_door_assembly.TestDoorAssembly.test_<name>
```

Sample PDFs `5-1133-WD03.pdf` and `floor-plans.pdf` are checked in for quick runs.

`--debug` writes `debug_trace.json` + a self-contained `debug_viewer.html` per page (per-primitive detection trace for diagnosing missed/false door detections — see the tuning guide's debug-trace playbook).

## Module layout

The root holds thin orchestration entry points; detection and I/O live in packages (the `d61f0e2` refactor split the old flat modules — `heuristics.py`, `extractor.py`, `gemini_client.py`, etc. — and the 3,679-line `heuristics.py` monolith). Code movement only; behavior and the `outputs/` JSON contract are unchanged.

```
app.py             # argparse shell
pipeline.py        # run_extract — the 7-stage orchestrator
inspector.py       # inspect-command logic
batch_extract.py   # interactive parallel batch runner over plans/*.pdf
models.py          # shared dataclasses (depended on by everything)

extraction/        # PDF -> normalized primitives + rendering (owns SCALE)
  extractor.py  plumber.py  renderer.py
detection/         # heuristic detection (the split monolith)
  __init__.py      # public facade: run_heuristics + detect_* re-exported
  orchestrator.py  # run_heuristics (named to avoid clash with root pipeline.py)
  geometry.py      # shared primitives (_distance, _line_angle_deg, …)
  layers.py        # OCG layer-name hints/priors (_layer_hint, _layer_strong_prior)
                   # — confidence boost when a layer name names the element type
  walls.py         # INTERNAL wall-centerline network (WallNetwork) — walls are
                   # never emitted as candidates; feeds rooms.py + postprocess.py
  rooms.py         # detect_rooms — rooms = free-space components between wall
                   # solids (shapely); door/window bboxes seal the openings
  windows.py  labels.py  schedules.py  postprocess.py
  doors/           # door subpackage, acyclic: constants <- arcs/leaves/shape <- assembly <- detect
gemini/client.py   # Vertex AI client (was gemini_client.py)
debug/             # trace.py (DebugTraceCollector) + renderer.py (HTML viewer)
tools/             # standalone dev scripts (numpy/cv2)
```

Import from the `detection` facade (`from detection import run_heuristics, detect_doors`) rather than reaching into submodules. Tunable constants are co-located with their detector: `DOOR_*` in `detection/doors/constants.py`, `WINDOW_*`/`WALL_*`/`ROOM_*`/`LABEL_*`/`SCHEDULE_*` in the matching `detection/*.py`, cross-validation `CROSS_*` in `detection/postprocess.py`. Tests import internals from their real homes (e.g. `from detection.doors.arcs import _prune_arc_spurs`) — there is no compatibility shim.

Room detection: order matters — doors/windows detect first, then `detect_wall_network(paths, text_spans)` builds the internal centerline network (text spans disambiguate white fills), then `detect_rooms` extracts rooms as the connected free-space components of the page after subtracting barriers. Barriers are ALLOWLISTED wall evidence, not all linework — room-interior ink (floor-tile grids, furniture outlines, sanitary symbols, text masks) must not chop the free space. Four barrier tiers: (1) wall solids — paired centerline segments dilated to their measured thickness (`WALL_MAX_THICKNESS_PX` 36px covers heavy blockwork bands); hairline faces (below `WALL_MIN_STROKE_WIDTH_PX` — the 0.45px joinery/fixture pen new partition walls are often drawn in) also pair, but a weak-involved pair survives only when the band between the faces carries drawn wall MATERIAL (`_band_has_wall_material`): short strokes DIAGONAL to the band axis (hatch, cross-hatch, the X's of blocking rectangles — the universal new-partition signature) at ≥ `WALL_WEAK_MATERIAL_PER_100PX` (3/100px, real partitions measure ≥4.8 while glazing strips and paving grids measure ≤2.6), spread over ≥ half the run, on runs ≥ `WALL_WEAK_MIN_RUN_PX` (30px — shorter material-dense slivers are dimension-tick clusters); diagonal-only keeps liner lines (parallel) and radiator fins (perpendicular) out, so plain hairline pairs — wardrobe edges, counter fronts — never become walls, and material-backed weak faces join `network.faces` as paired faces but stay out of `wall_stroke_reference` (stroked=False) so hairline members cannot drag the rooms' pen-weight gate down to fixture territory; (2) wall-fill polygons — closed rings reconstructed by chaining consecutive same-fill `l` items (the Vectorworks filled-polygon signature), each fill COLOR rated by the shape of its ink (`_rate_fill_classes`: run length in thin bands vs compact blocks, measured with area+perimeter equivalent-rectangle sides so L/U-shaped runs stay band-like) — wall-rated rings become barrier area (seals band interiors, corner posts, jamb stubs), furniture-rated classes (cabinet blocks) are excluded entirely, unrated classes keep the permissive legacy rule; marker rings — tiny 3-vertex triangles or concave 4-vertex darts up to `WALL_MARKER_MAX_SIDE_PX` (24px) bbox side (`_FillRing.is_marker`) — are leader/dimension arrowheads drawn in the wall pen (walls are rectilinear, so a small triangle is never material) and are dropped from the class rating, the barrier area, and wall-fill face qualification, while same-sized convex quads (jamb stubs, corner posts) stay; (3) thin buffers of QUALIFYING faces only — paired into a centerline, outlining a wall-rated fill, wall-layer-hinted, or stroked at ≥ `ROOM_BARRIER_STROKE_RATIO` (0.66) × the length-weighted median stroke of the paired wall faces (`wall_stroke_reference`); hatch strokes are excluded unless they outline wall fill (a corner post's short diagonal edges are material, not hatching), and faces inside a door bbox are excluded so the open leaf can't slot the swing area; (4) white (background-fill) rings — a ring mostly covered by the text written inside it is a text mask (dropped, `WALL_WHITE_TEXT_COVER_FRAC`); textless band/post-sized white rings are hollow-wall/joinery candidates, accepted in rooms.py when they touch wall material INCLUDING door/window bboxes (`_accept_white_walls` — hollow runs are interrupted by their own openings; only doors ≥ `ROOM_OPENING_MIN_CONFIDENCE` count as anchors, so a phantom door detected on a white fixture symbol cannot turn the fixture into wall; and a ring fully inside a confident door's bbox is the OPEN LEAF drawn in the same white-rectangle signature — it would anchor on its own door's bbox and notch the swing out of the room, so it is withheld from candidacy entirely, while fallback-tier doors get no such veto because they are typically detected ON white joinery rectangles whose rings ARE the partition), then bridged across open spans with band-shaped convex hulls (`_bridge_white_runs`, wardrobe-divider runs) — but a bridge only closes an OPEN span: touching rings (hollow-wall cavity segments chain contiguously through corners) union into run components first, candidate pairs are taken shortest-gap-first, and pairs already connected never bridge. Between two small cavity segments on perpendicular runs of one chain, the redundant hull is thin enough to pass the band test and chords diagonally across the room corner — that chord (not the arrowhead linework, which never qualifies as faces) was what notched room outlines around leader arrows. Opening seals at the surviving doors/windows complete the barrier set. Before any of this, door candidates whose bbox is mostly covered by the text written inside it (`ROOM_OPENING_TEXT_COVER_MAX` 0.60 — "WALL TYPE 1" tag boxes detected as leaf rectangles; same principle as the white text-mask rule) are dropped from the room stage entirely: no seals, no white-wall anchoring, no face exclusion under the bbox — real swing bboxes measure ≤ ~0.45 text cover even with a room label crossing them. A window bbox lies in the wall band and seals as-is; a door bbox covers the swing — room floor, not wall — so it is replaced by thin plugs along its wall-plane edges (`_door_plugs`), keeping the swing inside the room and splitting adjacent rooms exactly at the wall plane. An edge qualifies by the coverage profile of wall material hugging it (sampled along the edge, extended `ROOM_OPENING_SEAL_PX` past the bbox to reach jambs the arc stopped short of): either an interrupted wall run (both end quarters anchored, middle empty — the open-doorway case) or a drawn-through wall plane (near-total coverage — existing-opening sills and closed sliding/garage panels, common on working drawings, where the plug just shadows drawn linework). Doors with no qualifying edge first retry plug qualification with their own withheld leaf rings added as material — a leaf drawn CLOSED lies in the wall plane and may be the door's only evidence there (timber gates in fence lines), so the plug shadows the leaf instead of the dilated bbox stamping the swing square into free space — and only then fall back to the dilated bbox, at confidence ≥ `ROOM_OPENING_MIN_CONFIDENCE` (0.40; doors are penalty-only in cross-validation, so fallback tiers never climb back over). Fallback-tier doors (`DOOR_FALLBACK_CONFIDENCE` 0.35, deliberately capped under the offline floor and kept only for Gemini arbitration — label boxes, glazing mullions, section markers) seal exclusively through plugs that carry their own evidence: the interrupted-run profile (the doorway signature — a real low-confidence sliding door between jambs still splits its rooms), or a drawn-through plane the plug actually LIES IN (≥ `ROOM_PLUG_IN_WALL_FRAC` 0.80 of its area on drawn wall material, so it only re-asserts existing barrier and seals hairline gaps in it — measured phantoms floating NEAR a wall peak at ~0.77 overlap while on-plane plugs measure 0.84+). Full coverage by mere proximity is NOT evidence — that is how an annotation box hugging a wall band would stamp a free-space notch into the room outline — and a phantom door in open space contributes nothing at all. Drafting gaps are sealed by morphologically OPENING each free-space component (`ROOM_GAP_CLOSE_PX`, in `_free_space_components`) — the complement-side equivalent of closing the barrier union, which must NOT be buffered directly: GEOS silently drops legitimate room-sized holes from the giant multi-hole polygon (one 22px sliver closing a ring in the kitchen erased bedrooms 2/3 + hall wholesale); components are filtered by area, page fraction, page-border contact, hole fraction, erosion, wall-contact ratio, and attachment to a major wall mass (kills legend tables / dimension frames). Rooms are heuristic-only: never sent to Gemini, bypass the merge thresholds and NMS, and carry the closed polygon in `Candidate.evidence["polygon"]` / `Entity.attributes["polygon"]`. Curved (Bezier) walls are out of scope — only straight `l` faces and filled `re`/`qu` bands feed the network, so rooms bounded by curved walls leak open and are dropped. Known limitation: hairline-pen partitions WITH material between their faces (hatch/blocking) now bound rooms via the weak-pair material gate, but boundaries drawn ONLY as plain sub-threshold lines (e.g. a fitted-wardrobe run with nothing between the faces, 0.45px — the same pen as sanitary fixtures) still do not, so such spaces come out merged into one oversized room; accepting bare hairline pairs would reopen every fixture false-positive, so that residue belongs to a future room-label/Gemini arbitration layer, not to the barrier rules.

## Gemini / GCP auth

`gemini/client.py` uses Vertex AI via `google-genai` (`vertexai=True`). Required before the pipeline can call Gemini:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>           # or set GOOGLE_CLOUD_PROJECT
# Optional: GOOGLE_CLOUD_LOCATION (default us-central1)
```

Model is hard-coded to `gemini-2.5-flash`. Pass `--no-gemini` to skip Gemini end-to-end (offline mode applies stricter per-type confidence thresholds in `OFFLINE_MIN_CONFIDENCE`).

## Pipeline architecture

`app.py` is a thin argparse shell; the real flow is in `pipeline.py::run_extract`, which loops pages and runs seven stages per page:

1. `extraction.extractor.extract_page` — PyMuPDF `get_drawings()` / `get_text("dict")` / `get_images()` / `get_ocgs()`. **All coordinates are normalized to 150-DPI pixel space via `SCALE = 150/72`** at extraction time. Downstream code (detection, renderer, Gemini bboxes) assumes pixel-space. Don't reintroduce point-space anywhere past `extraction/extractor.py` / `extraction/plumber.py`.
2. `extraction.renderer.render_page_png` — renders the page PNG at the same 150 DPI used for coordinate normalization, so heuristic bboxes overlay cleanly.
3. `extraction.plumber.extract_plumber_page` — pdfplumber cross-check (chars/lines/rects/curves/images/tables). `compare_counts` emits `PLUMBER_LARGE_DELTA` warnings when PyMuPDF vs pdfplumber geometry diverges >50%. Tables here feed schedule detection.
4. `detection.run_heuristics` (`detection/orchestrator.py`) — deterministic detection of doors / windows / rooms / labels / schedules. Doors and windows detect first; the internal wall-centerline network (`detection/walls.py::detect_wall_network`, never emitted as candidates) then cross-validates them and feeds `detection/rooms.py::detect_rooms`, which subtracts wall solids, face linework, and opening seals (wall-plane plugs at doors, bboxes at windows) from the page and emits the enclosed free-space components as room polygons. `--disable-rooms` / `--disable-windows` exist because each detector can dominate noise on different drawing styles. Pass a `DebugTraceCollector` (via `--debug`) to record per-primitive reasoning.
5. `gemini.client.call_gemini` — sends the page render + candidate JSON (rooms excluded — they are heuristic-only), expects strict JSON matching `REQUIRED_KEYS`. Auto-skipped on raster-heavy pages with zero candidates (`should_skip_gemini`). Parse / schema failures degrade gracefully into warnings, not exceptions.
6. `pipeline.merge_gemini_and_heuristics` — combines results. With Gemini: blended confidence `0.5*heuristic + 0.5*gemini` (or `max` if higher), Gemini-rejected IDs drop out, unaddressed candidates fall back to heuristic-only. Without Gemini: candidates below `OFFLINE_MIN_CONFIDENCE[type]` move to `rejected` and are not promoted to entities. Room candidates bypass both paths and are always promoted to heuristic-source entities with the polygon in `attributes`.
7. `renderer.draw_overlay` + JSON dump (`primitives.json`, `candidates.json`, `gemini_result.json`, `final_entities.json`, `pdfplumber_comparison.json`).

Aggregate `summary.json` and `warnings.json` are written at the run root once all pages finish.

## Output layout

```
outputs/<YYYY-MM-DD_HH-MM-SS>/
├── summary.json              # per-page summaries + totals + PDF metadata
├── warnings.json             # flat list across all pages
└── pages/page_NN/
    ├── render.png            # 150 DPI render
    ├── overlay.png           # entities + rejected drawn on render
    ├── primitives.json       # raw PyMuPDF paths/text/images
    ├── pdfplumber_comparison.json
    ├── candidates.json       # heuristic output
    ├── gemini_result.json    # Gemini JSON (or {skipped: true, reason})
    ├── final_entities.json   # merged + rejected
    ├── debug_trace.json      # --debug only: per-primitive detection trace
    └── debug_viewer.html     # --debug only: self-contained trace viewer
```

## Data model

All shared types live in `models.py` as `@dataclass`es: `PathPrimitive`, `TextSpan`, `ImageRef`, `PageData`, `Candidate`, `Entity`. `BBox` is a `(x0, y0, x1, y1)` tuple in **150-DPI pixels, top-left origin, y-down**. Page numbers in serialized output are **1-based**; `page_indices` passed between functions are **0-based**.

Notable extractor behavior: `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful, so do not re-bundle multi-item drawings.

## Warning codes

Warnings are structured dicts with `warning_code`, `severity`, `message`, `page_number`. The set is intentionally small — when adding a new warning, follow the existing `SCREAMING_SNAKE_CASE` convention and emit from either `pipeline.collect_warnings`, `extraction.plumber.compare_counts`, or `gemini.client._validate_response`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
