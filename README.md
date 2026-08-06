# Architectural PDF Extraction (POC)

Local Python CLI that extracts doors, windows, walls/rooms, labels, and schedules
from CAD-originated architectural PDFs. Detection is a vector-first heuristic
pipeline; Gemini (Vertex AI) is used once per page, to say which parts of the
sheet are floor plans so detection can be run on those and not on the
elevations, site plans and title blocks beside them.

See `CLAUDE.md` for architecture details and `project.md` for the original spec.

## Requirements

- Python 3.13 (developed on 3.13.7; 3.11+ should work)
- A GCP project with Vertex AI enabled — only if you want Gemini region
  classification (otherwise run with `--no-gemini`)

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
# Create the virtual environment (first time only)
python3 -m venv .venv

# Activate it (do this in every new shell)
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

To leave the environment later, run `deactivate`.

### Gemini / GCP auth (optional)

The pipeline calls Gemini through Vertex AI once per page, to classify the
regions the sheet was split into. Authenticate once before running without
`--no-gemini`:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>     # or export GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
# Optional: export GOOGLE_CLOUD_LOCATION=us-central1   # (default)
```

The model is hard-coded to `gemini-2.5-flash`. Each classification is cached
beside the input PDF in `.regions_cache/`, so a page costs one real call ever;
`--no-gemini` reuses that cache and, where there is none, detects on the whole
unfiltered page rather than guessing.

## Usage

Always activate the venv first: `source .venv/bin/activate`.

### Inspect — terminal summary only

Prints a summary of the PDF's vector/text content. No Gemini calls, no files
written.

```bash
python app.py inspect path/to/drawing.pdf
python app.py inspect path/to/drawing.pdf --pages 1,3-5
```

### Extract — full pipeline

Runs the extraction pipeline and writes JSON + PNG outputs to
`outputs/<timestamp>/`.

```bash
python app.py extract path/to/drawing.pdf
```

| Flag | Effect |
| --- | --- |
| `--pages SPEC` | Page selection, e.g. `1` or `1,3-5` (default: all pages) |
| `--out DIR` | Parent directory for output (default: `outputs/`) |
| `--no-gemini` | Skip the region-classification call; use a cached classification if one exists, otherwise detect on the whole page |
| `--refresh-regions` | Ignore any cached region classification and call Gemini again |
| `--disable-rooms` | Skip wall-network + room detection |
| `--disable-walls` | Deprecated alias for `--disable-rooms` |
| `--disable-windows` | Skip window detection |
| `--debug` | Write `debug_trace.json` + `debug_viewer.html` per page (per-primitive detection trace) |

Examples:

```bash
# Heuristics-only, pages 1 and 3-5, no Gemini
python app.py extract path/to/drawing.pdf --pages 1,3-5 --no-gemini

# Focus on doors: skip rooms and windows, write a debug trace
python app.py extract path/to/drawing.pdf --disable-rooms --disable-windows --debug

# Custom output directory
python app.py extract path/to/drawing.pdf --out /tmp/runs
```

The regression corpus lives in `fixtures/sheets/` and is **not** committed: the
sheets are NDA-covered. Download the bundle (see `fixtures/MANIFEST.json`'s
`storage` field for how to get it) and verify it with
`python tools/fetch_fixtures.py`. Sheets are referred to by slug — `s01` and
`s02` are the two primary reference sheets.

### Batch extract

Discovers `fixtures/sheets/*.pdf`, prompts interactively for detection options, and runs
`app.py extract` five at a time (`ProcessPoolExecutor`):

```bash
python batch_extract.py
```

## Output layout

```
outputs/<YYYY-MM-DD_HH-MM-SS>/
├── summary.json              # per-page summaries + totals + PDF metadata
├── warnings.json             # flat list across all pages
└── pages/page_NN/
    ├── render.png            # 150 DPI render
    ├── overlay.png           # entities + rejected + region outlines drawn on render
    ├── primitives.json       # raw PyMuPDF paths/text/images
    ├── pdfplumber_comparison.json
    ├── regions.json          # segmented regions + their Gemini classification
    ├── region_crops/         # classification-call only: the per-region PNGs sent
    │                         # to Gemini (absent on a cache hit or --no-gemini)
    ├── candidates.json       # heuristic output
    ├── final_entities.json   # finalized entities + rejected
    ├── debug_trace.json      # --debug only
    └── debug_viewer.html     # --debug only
```

## Tests

```bash
# Fast tier — synthetic topologies, ~10s
python -m unittest discover tests

# Run a single test
python -m unittest tests.test_door_assembly.TestDoorAssembly.test_<name>

# Regression tier — the 20-sheet corpus vs. committed ground truth, ~3min
python tools/regress.py
```

`tools/regress.py` needs the corpus downloaded (see above). It scores each
sheet's detections against `tests/ground_truth/sNN.json` — geometric matching,
never entity ids — and exits 1 on a lost confirmed detection or a returned
false positive, 2 if sheets are missing, 0 otherwise. New detections never fail
the sweep; they print under `REVIEW` for the user to verdict. See CLAUDE.md's
"Regression testing" section for the full labeling loop.
