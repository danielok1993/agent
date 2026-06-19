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
                                          [--disable-walls] [--disable-windows]
                                          [--debug]

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
models.py          # shared dataclasses (depended on by everything)

extraction/        # PDF -> normalized primitives + rendering (owns SCALE)
  extractor.py  plumber.py  renderer.py
detection/         # heuristic detection (the split monolith)
  __init__.py      # public facade: run_heuristics + detect_* re-exported
  orchestrator.py  # run_heuristics (named to avoid clash with root pipeline.py)
  geometry.py      # shared primitives (_distance, _line_angle_deg, …)
  windows.py  walls.py  labels.py  schedules.py  postprocess.py
  doors/           # door subpackage, acyclic: constants <- arcs/leaves/shape <- assembly <- detect
gemini/client.py   # Vertex AI client (was gemini_client.py)
debug/             # trace.py (DebugTraceCollector) + renderer.py (HTML viewer)
tools/             # standalone dev scripts (numpy/cv2)
```

Import from the `detection` facade (`from detection import run_heuristics, detect_doors`) rather than reaching into submodules. Tunable constants are co-located with their detector: `DOOR_*` in `detection/doors/constants.py`, `WINDOW_*`/`WALL_*`/`LABEL_*`/`SCHEDULE_*` in the matching `detection/*.py`, cross-validation `CROSS_*` in `detection/postprocess.py`. Tests import internals from their real homes (e.g. `from detection.doors.arcs import _prune_arc_spurs`) — there is no compatibility shim.

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
4. `detection.run_heuristics` (`detection/orchestrator.py`) — deterministic detection of doors / windows / walls / labels / schedules. Each detector lives in its own `detection/*.py` (doors in the `detection/doors/` subpackage); see the Module layout section for where the `*_` tunables live. `--disable-walls` / `--disable-windows` exist because each detector can dominate noise on different drawing styles. Pass a `DebugTraceCollector` (via `--debug`) to record per-primitive reasoning.
5. `gemini.client.call_gemini` — sends the page render + candidate JSON, expects strict JSON matching `REQUIRED_KEYS`. Auto-skipped on raster-heavy pages with zero candidates (`should_skip_gemini`). Parse / schema failures degrade gracefully into warnings, not exceptions.
6. `pipeline.merge_gemini_and_heuristics` — combines results. With Gemini: blended confidence `0.5*heuristic + 0.5*gemini` (or `max` if higher), Gemini-rejected IDs drop out, unaddressed candidates fall back to heuristic-only. Without Gemini: candidates below `OFFLINE_MIN_CONFIDENCE[type]` move to `rejected` and are not promoted to entities.
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
