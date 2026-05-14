You are a senior Python engineer building a local terminal POC for architectural PDF extraction.

Create a Python CLI app that runs locally on my PC. The purpose is to test whether CAD-originated architectural PDFs contain useful native data — vector geometry, text coordinates, layers, line weights, curves, fills, image references, and tables/schedules — that can improve door/window/wall extraction compared with a pure vision-only approach.

The POC should use a vector-first, Gemini-assisted workflow:

PDF → native PDF extraction → normalized JSON → geometry heuristics → targeted Gemini analysis → final structured output + debug artifacts.

Core research assumptions:
- Digitally generated architectural PDFs often preserve linework, curves, text objects, coordinates, fonts, colours, layers/optional content groups, and raster image references.
- Reading these PDFs only as images loses valuable information.
- PDF extraction will not recover the original DWG/BIM semantics, but it can recover better primitives than a screenshot-based model sees.
- Door/window detection should start from geometry: arcs, chords, parallel lines, wall gaps, labels, tables, and layer names.
- Gemini should be used after deterministic extraction, not as the first and only reader of the full page.
- The POC should make it easy to inspect what the PDF actually contains.

Use Python.

Use PyMuPDF as the primary extractor:
- vector drawings via page.get_drawings()
- text via page.get_text("rawdict")
- images via page.get_images()
- layer/OCG metadata via doc.get_ocgs(), where available
- page rendering for debug images and candidate crops

Use pdfplumber as a secondary/cross-check extractor:
- text extraction comparison
- table/schedule extraction
- page object inspection: chars, lines, rects, curves, images
- debug comparison against PyMuPDF output

Use pdfminer.six indirectly through pdfplumber unless direct text-layout extraction becomes necessary.

Use Gemini as part of the pipeline to classify or validate extracted candidates. Gemini should receive structured extraction data and, where useful, small rendered crops around candidate symbols. It should return strict JSON.

The CLI should support two main workflows:

1. Inspect a PDF

Example:

python app.py inspect path/to/drawing.pdf

This should print a terminal summary:
- file name
- page count
- PDF metadata
- for each page:
  - page width and height
  - PyMuPDF extraction counts:
    - vector paths
    - lines
    - curves
    - rectangles
    - text spans or characters
    - images
    - layers/OCGs
  - pdfplumber extraction counts:
    - chars
    - lines
    - rects
    - curves
    - images
    - detected tables, if any
  - whether the page appears vector-rich, raster-heavy, mixed, or unknown
  - warnings such as no layers, low text extraction, or possible scanned/raster page

2. Extract a PDF

Example:

python app.py extract path/to/drawing.pdf --out outputs/test_run

This should produce:
- summary.json
- primitives.json
- pdfplumber_comparison.json
- candidates.json
- gemini_result.json
- final_entities.json
- warnings.json
- rendered page images
- simple visual debug overlays showing extracted lines, curves, text boxes, tables, and detected candidates

Extraction requirements:
- Open the PDF with PyMuPDF.
- Extract page dimensions.
- Extract vector drawings using page.get_drawings().
- Extract text using page.get_text("rawdict").
- Extract images using page.get_images().
- Extract OCG/layer metadata using doc.get_ocgs() where available.
- Preserve useful primitive attributes:
  - coordinates
  - stroke width
  - colour
  - fill
  - dash pattern
  - drawing sequence/z-order where available
  - layer/OCG where available
- Normalize extracted data into readable JSON.

pdfplumber requirements:
- Open the same PDF with pdfplumber.
- For each page, extract:
  - chars
  - lines
  - rects
  - curves
  - images
  - tables, if detectable
- Save a pdfplumber_comparison.json file comparing PyMuPDF and pdfplumber counts per page.
- Include tables/schedules in the candidate extraction where they are detected.
- If PyMuPDF and pdfplumber strongly disagree on text or geometry counts, add a warning.

Page classification:
- Mark a page as vector-rich if it has substantial vector paths.
- Mark a page as raster-heavy if it has very few paths but contains large images.
- Mark a page as mixed if it contains both substantial vector data and raster data.
- Include these classifications in summary.json.

Geometry candidate detection:

Detect likely doors:
- Look for arc-like curves.
- Look for nearby straight line segments that may represent a door leaf.
- Score candidates higher when:
  - the curve resembles a swing arc
  - the line endpoint is close to the arc endpoint
  - the line length roughly matches the swing radius
  - nearby text looks like a door tag, such as D01, D1, FD30
  - the layer name contains terms like DOOR or A-DOOR

Detect likely windows:
- Look for groups of short, parallel line segments.
- Score candidates higher when:
  - lines are parallel
  - line lengths are similar
  - spacing is consistent
  - they appear within or across a wall gap
  - nearby layer names contain WINDOW, WIN, GLAZ, GLAZING, A-GLAZ, or A-WIND

Detect likely walls:
- Look for long parallel line pairs.
- Score candidates higher when:
  - the lines are long
  - they are close and parallel
  - the layer name contains WALL, A-WALL, PARTITION, or STRUCT

Extract likely labels:
- Return text spans that look like room names, room numbers, door tags, window tags, or schedule labels.
- Include bbox, text, font, size, page number, and nearest candidate entity where possible.

Extract likely schedules/tables:
- Use pdfplumber table extraction where possible.
- Return raw table rows/cells with page number and bbox if available.
- Flag tables that may be door schedules or window schedules based on nearby text such as DOOR SCHEDULE, WINDOW SCHEDULE, TYPE, MARK, WIDTH, HEIGHT, FIRE RATING, GLAZING, FRAME, LEAF, or similar terms.

Gemini step:
- After extracting primitives and generating local candidates, call Gemini.
- Send Gemini:
  - page summary
  - layer names
  - candidate doors/windows/walls/labels/schedules
  - relevant text spans near each candidate
  - relevant pdfplumber table snippets
  - small image crops around candidate areas where useful
- Ask Gemini to classify, validate, or reject candidates.
- Gemini should not invent objects that are not supported by extracted evidence.
- Gemini should return strict JSON only.
- If Gemini is unavailable or fails, still produce all non-Gemini outputs and include a warning.

Gemini output shape:

{
  "doors": [
    {
      "candidate_id": "string",
      "classification": "door",
      "subtype": "single_swing | double_swing | sliding | unknown",
      "label": "string | null",
      "confidence": 0.0,
      "reason": "string"
    }
  ],
  "windows": [
    {
      "candidate_id": "string",
      "classification": "window",
      "subtype": "single | double | glazing | unknown",
      "label": "string | null",
      "confidence": 0.0,
      "reason": "string"
    }
  ],
  "walls": [],
  "labels": [],
  "schedules": [],
  "rejected_candidates": [
    {
      "candidate_id": "string",
      "reason": "string"
    }
  ]
}

Final entity format:

{
  "id": "string",
  "type": "door | window | wall | label | room | schedule | unknown",
  "subtype": "string | null",
  "page_number": 1,
  "bbox": [x0, y0, x1, y1],
  "confidence": 0.0,
  "source": "heuristic | gemini | merged | pdfplumber_table",
  "layer": "string | null",
  "label": "string | null",
  "evidence": {
    "primitive_ids": [],
    "text_span_ids": [],
    "table_ids": [],
    "gemini_reason": "string | null",
    "heuristic_reason": "string | null"
  }
}

Warnings to include:
- No layers found.
- Very low text extraction.
- Possible SHX/vectorized text if there are many tiny line segments but little actual text.
- Raster-heavy page detected.
- PyMuPDF and pdfplumber extraction counts strongly disagree.
- No obvious door/window candidates found.
- No tables/schedules found.
- Gemini unavailable or Gemini call failed.
- Gemini returned invalid JSON.

Debug artifacts:
- Render each page as PNG.
- Create a simple SVG or PNG overlay showing:
  - extracted lines
  - curves
  - rectangles
  - text bounding boxes
  - table regions, if detected
  - door candidates
  - window candidates
  - wall candidates
  - confidence scores
- The debug output should make it easy to visually compare the original PDF against extracted primitives and detected entities.

Acceptance criteria:
- I can run the app from the terminal on a local PDF.
- The inspect command summarizes whether the PDF is vector-rich, raster-heavy, mixed, or unknown.
- The inspect command reports both PyMuPDF and pdfplumber extraction counts where useful.
- The extract command creates readable JSON outputs.
- The app extracts native vector paths and text coordinates from CAD-originated PDFs.
- The app uses pdfplumber as a cross-check and for table/schedule extraction.
- The app detects basic door/window/wall candidates using geometry.
- The app calls Gemini to classify or validate candidates.
- The app creates debug images or overlays that allow quick visual inspection.
- The final output clearly distinguishes:
  - raw PyMuPDF primitives
  - pdfplumber comparison output
  - heuristic candidates
  - Gemini classifications
  - merged final entities
  - warnings and limitations
- The implementation should be simple, readable, and suitable for fast experimentation on a handful of PDFs.

Prioritize:
1. fast local validation
2. clear terminal output
3. readable JSON
4. useful debug overlays
5. simple geometry heuristics
6. pdfplumber cross-checking and table extraction
7. Gemini validation of extracted candidates

The goal is not perfect extraction. The goal is to prove whether PDF-native extraction plus targeted Gemini reasoning is worth pursuing further.