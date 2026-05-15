# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Local Python CLI POC for architectural PDF extraction. The research question is whether CAD-originated PDFs carry enough native vector/text data that a vector-first + Gemini-validation pipeline beats vision-only extraction of doors, windows, walls, labels, and schedules. `project.md` is the original spec — treat it as the source of truth for scope and acceptance criteria.

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

# Tests (unittest)
python -m unittest discover tests
python -m unittest tests.test_door_assembly.TestDoorAssembly.test_<name>
```

Sample PDFs `5-1133-WD03.pdf` and `floor-plans.pdf` are checked in for quick runs.

## Gemini / GCP auth

`gemini_client.py` uses Vertex AI via `google-genai` (`vertexai=True`). Required before the pipeline can call Gemini:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>           # or set GOOGLE_CLOUD_PROJECT
# Optional: GOOGLE_CLOUD_LOCATION (default us-central1)
```

Model is hard-coded to `gemini-2.5-flash`. Pass `--no-gemini` to skip Gemini end-to-end (offline mode applies stricter per-type confidence thresholds in `OFFLINE_MIN_CONFIDENCE`).

## Pipeline architecture

`app.py` is a thin argparse shell; the real flow is in `pipeline.py::run_extract`, which loops pages and runs seven stages per page:

1. `extractor.extract_page` — PyMuPDF `get_drawings()` / `get_text("dict")` / `get_images()` / `get_ocgs()`. **All coordinates are normalized to 150-DPI pixel space via `SCALE = 150/72`** at extraction time. Downstream code (heuristics, renderer, Gemini bboxes) assumes pixel-space. Don't reintroduce point-space anywhere past `extractor.py` / `plumber.py`.
2. `renderer.render_page_png` — renders the page PNG at the same 150 DPI used for coordinate normalization, so heuristic bboxes overlay cleanly.
3. `plumber.extract_plumber_page` — pdfplumber cross-check (chars/lines/rects/curves/images/tables). `compare_counts` emits `PLUMBER_LARGE_DELTA` warnings when PyMuPDF vs pdfplumber geometry diverges >50%. Tables here feed schedule detection.
4. `heuristics.run_heuristics` — deterministic detection of doors / windows / walls / labels / schedules. Tuned via the constants at the top of `heuristics.py` (`DOOR_*`, `WINDOW_*`, `WALL_*`, `LABEL_*`, `SCHEDULE_*`). `--disable-walls` / `--disable-windows` exist because each detector can dominate noise on different drawing styles.
5. `gemini_client.call_gemini` — sends the page render + candidate JSON, expects strict JSON matching `REQUIRED_KEYS`. Auto-skipped on raster-heavy pages with zero candidates (`should_skip_gemini`). Parse / schema failures degrade gracefully into warnings, not exceptions.
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
    └── final_entities.json   # merged + rejected
```

## Data model

All shared types live in `models.py` as `@dataclass`es: `PathPrimitive`, `TextSpan`, `ImageRef`, `PageData`, `Candidate`, `Entity`. `BBox` is a `(x0, y0, x1, y1)` tuple in **150-DPI pixels, top-left origin, y-down**. Page numbers in serialized output are **1-based**; `page_indices` passed between functions are **0-based**.

Notable extractor behavior: `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful, so do not re-bundle multi-item drawings.

## Warning codes

Warnings are structured dicts with `warning_code`, `severity`, `message`, `page_number`. The set is intentionally small — when adding a new warning, follow the existing `SCREAMING_SNAKE_CASE` convention and emit from either `pipeline.collect_warnings`, `plumber.compare_counts`, or `gemini_client._validate_response`.
