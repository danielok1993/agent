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
| `--svg` | Also write `page.svg` per page — MuPDF's vector redraw of the page in `render.png`'s 150-DPI space (0.2–21 MB/sheet, so off by default) |

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
    ├── page.svg              # --svg only: vector redraw, same frame as render.png
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
the sweep; they print under `REVIEW` for you to verdict.

## Reviewing new detections

A new detection is not a failure — it is a question. The sweep cannot know
whether a door it just found is real, so it prints it under `REVIEW` and waits
for your verdict. Recording that verdict is what turns it into a gate.

```bash
python tools/regress.py --sheet s01     # 1. sweep the sheet
                                        # 2. open the review image it names
python tools/review.py s01              # 3. tick the correct ones, then the wrong ones
```

### 1. Sweep

Every sheet with unreviewed detections prints its id, confidence and centre,
then where to look and what to run next:

```
s01  window 4/4  unreviewed 24
    REVIEW new door_0007  conf 0.67  (485,1364)
    REVIEW new room_0003  conf 0.85  (1056,549)
    …
    images: outputs/regress/s01/2026-08-10_14-13-29/pages/  — then: python tools/review.py s01
```

The entity id (`door_0007`) is **display-only**. Ids are ordinal — `door_0007`
becomes `door_0006` the moment an earlier door stops being detected — so they
are never written to ground truth and never used for matching. They exist so
you can find the box on the image.

### 2. Open the review image

`outputs/regress/<slug>/<timestamp>/pages/page_NN/review_<type>.png` — one per
entity type, with every unreviewed detection stamped with a short id: `d7` is
`door_0007`, `r3` is `room_0003`, matching the `REVIEW` lines above.

That directory persists (it is gitignored) precisely so this image exists to
open. It is **wiped at the start of that slug's next sweep**, so copy out
anything you want to keep. `debug_viewer.html` is opt-in via
`python tools/regress.py --debug` — it costs 200–300MB per sheet on the
corpus's heaviest sheets, so it is for the hard cases, not routine review.

### 3. Record the verdicts

```bash
python tools/review.py              # every sheet with unreviewed detections
python tools/review.py s01          # one sheet
python tools/review.py s01 s07      # several
```

It walks sheet → page → category, printing the path to each review image, then
asking twice: **which are correct**, then **which of the rest are wrong**.
Space toggles a checkbox, Enter confirms; each list ends with a "none of these"
option. Anything you tick in neither list stays unreviewed and comes back next
sweep — "I can't tell from this image" costs nothing.

`review.py` never re-runs detection. It reads what the sweep already persisted,
so run the sweep first.

On finishing a sheet it writes `tests/ground_truth/<slug>.json` and sets
`"labeled": true` on that sheet's `fixtures/MANIFEST.json` entry. Commit both
together as a data commit — no code change belongs in it.

| Exit | Meaning |
| --- | --- |
| 0 | Walk finished, every sheet handled |
| 1 | Walk finished but a sheet failed unexpectedly and was skipped |
| 130 | Ctrl-C — abandons the current sheet (nothing was written for it); sheets completed earlier are already on disk |

### After reviewing

Re-run `python tools/regress.py`. Sheets you just labeled now have real gates:
losing a confirmed detection, or re-emitting one you marked wrong, fails the
sweep. A detection you marked correct that the next algorithm change breaks is
exactly what this whole loop exists to catch.

See `docs/regression-testing-guide.md` for the ground-truth file format, the
rules for editing it by hand, adopting new sheets, and the traps that have
already shipped bugs here.
