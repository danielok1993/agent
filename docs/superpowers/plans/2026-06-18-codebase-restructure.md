# Codebase Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the flat root modules into logical packages and split the 3,679-line `heuristics.py` monolith into a per-concern `detection/` package, with zero behavior change.

**Architecture:** Create packages at root (`extraction/`, `detection/`, `gemini/`, `debug/`, `tools/`); keep thin entry points (`app.py`, `pipeline.py`, `inspector.py`, `models.py`) at root. Decompose door logic into a `detection/doors/` subpackage layered `constants/models ← arcs/leaves/shape ← assembly ← detect`, on top of shared `detection/geometry.py` (generic geometry) and `detection/layers.py` (layer-metadata hints). Move incrementally, keeping `heuristics.py` as a temporary re-export bridge so the 80-test suite stays green at every step; remove the bridge last.

**Tech Stack:** Python 3, PyMuPDF (`fitz`), pdfplumber, Pillow, google-genai, OpenCV/numpy (optional, Hu moments), `unittest`.

## Global Constraints

- **No behavior change.** CLI surface (`python app.py …`) and the `outputs/` JSON contract stay byte-for-byte identical. This is pure code relocation.
- **No logic, no renames, no dead-code removal.** Do not rename functions/constants, rewrite docstrings, edit `docs/`, or delete unused symbols (e.g. the dead `SCHEDULE_KEYWORDS` at line 162 moves verbatim with its module). Move bodies exactly as-is.
- **`models.py` stays at root.** `from models import …` lines never change — root is on `sys.path`. Only imports of *relocated* modules change.
- **Regression gate after every task:** `python -m unittest discover tests` must print `Ran 80 tests` and `OK`.
- **Branch:** work on `cleanup/package-restructure`. Commit messages are plain — **no `Co-Authored-By` trailer.**
- **Activate venv first:** `source .venv/bin/activate`.

This is a refactor, not feature work: there are **no new failing tests to write**. The existing 80-test suite is the regression gate. Each task = perform the moves → run the suite → commit.

**Relocation map (applies throughout):**

| Old import | New import |
|---|---|
| `from extractor import X` | `from extraction.extractor import X` |
| `from plumber import X` | `from extraction.plumber import X` |
| `from renderer import X` | `from extraction.renderer import X` |
| `from debug_trace import X` | `from debug.trace import X` |
| `from debug_renderer import X` | `from debug.renderer import X` |
| `import gemini_client as gc` | `from gemini import client as gc` |
| `from heuristics import X` | `from detection import X` (public) or real submodule (internals) |

---

## Authoritative symbol → module assignment

**This table is the source of truth for which symbols move where (Tasks 5–9).** Every top-level `def`/`class`/constant in `heuristics.py` is assigned to exactly one destination. Line numbers are approximate anchors (`~`) into the live file; move each body **verbatim**. The exact import header each new module needs is given separately in the **Computed module headers** section below — those were derived by AST-walking each moved body and resolving every referenced name to its destination module, so they are complete, not guesses.

### `detection/geometry.py` — generic geometry (deps: `math`, `models`)
`_bbox_center`(171), `_distance`(175), `_line_length`(179), `_line_angle_deg`(183), `_angle_diff_mod180`(188), `_bbox_width`(194), `_bbox_height`(198), `_point_in_bbox`(202), `_is_line_path`(312), `_point_to_segment_distance`(323), `_segments_min_distance`(338), `_bbox_expanded`(1161), `_bboxes_overlap`(1165), `_bbox_union`(1169), `_bbox_area`(3464), `_projected_interval`(2870), `_interval_overlap`(2883), `_perpendicular_spacing`(3030), `_project_onto_axis`(3052)

> **`_bbox_area` moved here (not postprocess) to break a cycle:** `postprocess._cross_validate` calls `_dedupe_door_components` (doors.assembly), and `doors.assembly` calls `_bbox_area`. Leaving `_bbox_area` in postprocess would make postprocess ↔ doors.assembly mutually importing. `_bbox_area` is pure geometry, so relocating it to `geometry.py` makes the graph acyclic.

### `detection/layers.py` — layer-metadata hints (deps: `re`, `models`)
`_LAYER_TOKEN_RE`(1130), `_layer_tokens`(1133), `_layer_hint`(1139), `_layer_strong_prior`(1149), `_layer_hint_from_layer`(1290)

### `detection/walls.py` (deps: `math`, `statistics`, `models`, `geometry`, `layers`)
Constants: `WALL_*`(137–144), `COLLINEAR_ANGLE_TOL`/`COLLINEAR_OFFSET_TOL`/`COLLINEAR_GAP_MAX_PX`(3047–3049)
Funcs: `_is_diagonal_hatch_angle`(263), `_wall_material_evidence`(267), `_merge_collinear_segments`(3062), `detect_walls`(3156), `_stroke_percentile_rank`(3614)

### `detection/windows.py` (deps: `math`, `models`, `geometry`, `layers`)
Constants: `WINDOW_*`(123–132), `WINDOW_HATCH_REJECT_MIN`/`WINDOW_HATCH_REJECT_RATIO`(145–146)
Funcs: `detect_windows`(2887)

### `detection/labels.py` (deps: `re`, `models`, `geometry`)
Constants: `LABEL_PATTERN`(151), `LABEL_*`(152–154)
Funcs: `_find_nearby_label`(3255), `detect_labels`(3277)

### `detection/schedules.py` (deps: `re`, `models`)
Constants: `SCHEDULE_TABLE_MIN_ROWS`/`SCHEDULE_TABLE_MIN_COLS`/`SCHEDULE_MIN_CELL_DENSITY`(159–161), `SCHEDULE_KEYWORDS`(162, dead but moved verbatim), `SCHEDULE_KEYWORDS_RE`(3333)
Funcs: `detect_schedules`(3338)

### `detection/postprocess.py` (deps: `models`, `geometry`, `doors.assembly`)
Constants: `CROSS_*`(3386–3394), `NMS_IOU_THRESHOLD`(3460), `NMS_CENTER_DIST_PX`(3461), `NMS_PROJ_PERP_MAX_PX`(3510)
Funcs: `_cross_validate`(3399), `_bbox_iou`(3468), `_projected_overlap_1d`(3480), `_suppress`(3513), `_bbox_is_horizontal`(3572), `_resolve_wall_window_conflicts`(3576)  *(`_bbox_area` moved to geometry — see note above)*

### `detection/doors/constants.py` (deps: `re`)
All `DOOR_*`(21–105), `_DOOR_HU_TEMPLATE_VALUES`(118), `DOOR_HU_*`(112–117), `DOOR_LABEL_PATTERN`(26), `DOOR_LEAF_ASPECT_MIN`(206)

### `detection/doors/models.py` (deps: `dataclasses`, `models`)
`_DoorSwing`(1178), `_DoorLeaf`(1197)

### `detection/doors/shape.py` (deps: optional `cv2`/`numpy`, `models`, `doors.constants`)
`_HU_AVAILABLE` import block(11–16), `_rasterize_paths_to_canvas`(1959), `_compute_hu_distance`(1996)

### `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`)
`_is_arc_like`(208), `_arc_corners`(318), `_estimate_arc_sweep_deg`(394), `_prune_arc_spurs`(429), `_prune_arc_cycle_caps`(531), `_split_double_arc`(630), `_trim_chain_extension_caps`(746), `_detect_polyline_arc_bboxes`(861), `_fit_circle_3pt`(1209), `_native_curve_chains`(1235), `_detect_curve_arc_double_partners`(1295), `_collect_door_swings`(1400)

### `detection/doors/leaves.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.arcs`)
`_is_door_leaf`(235), `_snap_key`(1584), `_LinkSeg`(1588), `_try_linework_leaf_clean_loop`(1591), `_find_thin_rectangle_cycle`(1654), `_collect_linework_door_leaves`(1770), `_collect_door_leaves`(1918), `_find_anchored_leaf_line`(2151), `_find_leaf_companion_lines`(2221)

### `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`)
`_check_opening_clear`(353), `_nearest_pair_distance`(2017), `_door_fallback_candidate`(2026), `_component_indices`(2052), `_dedupe_door_components`(2063), `_find_threshold_line`(2091), `_pair_door_assemblies`(2269), `_safe_bbox`(2661), `_merge_double_door_assemblies`(2677)
> Note: assembly imports `_compute_hu_distance` from `doors.shape` and `_find_nearby_label` from `labels` — both lower in the graph, so no cycle. This is why `labels` must be built before `doors` (Task 6 before Task 7).

### `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`)
`detect_doors`(2853)

### `detection/orchestrator.py` (deps: `statistics`, `models`, `debug.trace`, `doors.detect`, `walls`, `windows`, `labels`, `schedules`, `postprocess`)
`run_heuristics`(3628)

**No top-level symbol in `heuristics.py` is left unassigned by this table.**

---

## Computed module headers

Each block below is the **exact** import header for that module, produced by AST-walking the assigned bodies and resolving every referenced name (stdlib, `models` type, `debug.trace`, or another detection symbol) to its source. Paste verbatim as the top of each new file, then move the bodies. Trim only if you intentionally leave a symbol behind; do not add guessed imports.

```python
# detection/geometry.py
from __future__ import annotations
import math
from models import BBox, PathPrimitive

# detection/layers.py
from __future__ import annotations
import re
from models import PathPrimitive

# detection/walls.py
from __future__ import annotations
import math
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_expanded, _bboxes_overlap, _line_angle_deg, _line_length, _perpendicular_spacing, _point_in_bbox, _project_onto_axis
from detection.layers import _layer_tokens
# NOTE: run_heuristics imports _stroke_percentile_rank/_wall_material_evidence from here; they use `statistics`/`math` already covered.

# detection/windows.py
from __future__ import annotations
from models import BBox, Candidate, PathPrimitive
from detection.geometry import _bbox_height, _bbox_width, _interval_overlap, _line_angle_deg, _line_length, _perpendicular_spacing, _projected_interval
from detection.layers import _layer_hint, _layer_strong_prior

# detection/labels.py
from __future__ import annotations
import re
from models import BBox, Candidate, TextSpan
from detection.geometry import _bbox_center, _distance

# detection/schedules.py
from __future__ import annotations
import re
from models import Candidate, TextSpan

# detection/postprocess.py    (built in Task 8, AFTER doors)
from __future__ import annotations
from models import BBox, Candidate
from detection.geometry import _bbox_area, _bbox_center, _bbox_expanded, _bbox_height, _bbox_width, _bboxes_overlap, _distance
from detection.doors.assembly import _dedupe_door_components

# detection/doors/constants.py
from __future__ import annotations
import re

# detection/doors/models.py
from __future__ import annotations
from dataclasses import dataclass
from models import BBox

# detection/doors/shape.py
from __future__ import annotations
from models import PathPrimitive
from detection.doors.constants import DOOR_HU_CANVAS_SIZE, _DOOR_HU_TEMPLATE_VALUES
try:
    import cv2 as _cv2
    import numpy as _np
    _HU_AVAILABLE = True
except ImportError:
    _HU_AVAILABLE = False

# detection/doors/arcs.py
from __future__ import annotations
import math
from collections import defaultdict
from itertools import combinations
from models import BBox, PathPrimitive
from debug.trace import DebugTraceCollector
from detection.geometry import _bbox_expanded, _bbox_height, _bbox_width, _bboxes_overlap, _distance, _is_line_path, _line_angle_deg, _line_length
from detection.layers import _layer_hint, _layer_hint_from_layer
from detection.doors.models import _DoorSwing
from detection.doors.constants import (
    DOOR_BBOX_ASPECT_MAX, DOOR_BBOX_ASPECT_MIN, DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX,
    DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX, DOOR_CURVE_CHAIN_MIN_CURVES,
    DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS, DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS,
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_RADIUS_RATIO_TOL, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
    DOOR_POLYLINE_CHAIN_DELTA_DEG, DOOR_POLYLINE_CYCLE_MAX_SEGMENTS, DOOR_POLYLINE_ENDPOINT_TOL,
    DOOR_POLYLINE_MAX_ANGLE_BINS, DOOR_POLYLINE_MAX_SEGMENTS, DOOR_POLYLINE_MAX_SEG_PX,
    DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_SPUR_MAX_SEGMENTS, DOOR_SWING_LINE_DIST_PX,
)

# detection/doors/leaves.py
from __future__ import annotations
from collections import defaultdict
from models import BBox, PathPrimitive
from debug.trace import DebugTraceCollector
from detection.geometry import _angle_diff_mod180, _bbox_height, _bbox_width, _distance, _interval_overlap, _is_line_path, _line_angle_deg, _line_length, _projected_interval
from detection.layers import _layer_hint, _layer_hint_from_layer
from detection.doors.models import _DoorLeaf, _DoorSwing
from detection.doors.arcs import _arc_corners
from detection.doors.constants import (
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_ASPECT_MIN, DOOR_LEAF_COMPANION_OVERLAP,
    DOOR_LEAF_COMPANION_PERP_PX, DOOR_LEAF_CYCLE_PARALLEL_TOL_DEG, DOOR_LEAF_CYCLE_PERPENDICULAR_TOL_DEG,
    DOOR_LEAF_LINE_AXIS_TOL_DEG, DOOR_LEAF_LINE_ENDPOINT_TOL_PX, DOOR_LEAF_LINE_LENGTH_TOL,
    DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS, DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX,
    DOOR_LINEWORK_LEAF_MAX_SEGMENTS, DOOR_LINEWORK_LEAF_MIN_SEGMENTS, DOOR_MAX_SIZE_PX, DOOR_MIN_SIZE_PX,
)
# _LinkSeg type alias is defined in this module (moves with the linework leaf helpers).

# detection/doors/assembly.py
from __future__ import annotations
from itertools import combinations
from models import BBox, Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.geometry import _angle_diff_mod180, _bbox_area, _bbox_expanded, _bbox_height, _bbox_union, _bbox_width, _bboxes_overlap, _distance, _is_line_path, _line_angle_deg, _segments_min_distance
from detection.layers import _layer_hint_from_layer
from detection.labels import _find_nearby_label
from detection.doors.models import _DoorLeaf, _DoorSwing
from detection.doors.shape import _compute_hu_distance
from detection.doors.leaves import _find_anchored_leaf_line, _find_leaf_companion_lines
from detection.doors.constants import (
    DOOR_ARC_FALLBACK_MAX, DOOR_ASSEMBLY_CONNECT_TOL_PX, DOOR_ASSEMBLY_LINE_LEAF_BASE,
    DOOR_DOUBLE_LEAF_CENTER_TOL_PX, DOOR_DOUBLE_LEAF_GAP_PX, DOOR_DOUBLE_LEAF_OVERLAP_PX,
    DOOR_FALLBACK_CONFIDENCE, DOOR_HU_FAR_PENALTY, DOOR_HU_PLAUSIBLE_BOOST, DOOR_HU_THRESHOLD_FAR,
    DOOR_HU_THRESHOLD_VERIFIED, DOOR_HU_VERIFIED_BOOST, DOOR_LABEL_PATTERN, DOOR_LABEL_SEARCH_RADIUS_PX,
    DOOR_LAYER_KEYWORDS, DOOR_LEAF_RADIUS_RATIO_TOL, DOOR_THRESHOLD_CONFIDENCE_BOOST,
    DOOR_THRESHOLD_ENDPOINT_TOL_PX, DOOR_THRESHOLD_PARALLEL_TOL_DEG, DOOR_V2_BRIDGE_BUFFER_PX,
    DOOR_V2_OPENING_CLEAR_BOOST, DOOR_V2_OPENING_OBSTRUCTED_PENALTY,
)

# detection/doors/detect.py
from __future__ import annotations
from models import Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.doors.arcs import _collect_door_swings
from detection.doors.leaves import _collect_door_leaves
from detection.doors.assembly import _merge_double_door_assemblies, _pair_door_assemblies

# detection/orchestrator.py
from __future__ import annotations
import statistics
from models import Candidate, PageData
from debug.trace import DebugTraceCollector
from detection.doors.detect import detect_doors
from detection.walls import _stroke_percentile_rank, _wall_material_evidence, detect_walls
from detection.windows import WINDOW_HATCH_REJECT_MIN, WINDOW_HATCH_REJECT_RATIO, detect_windows
from detection.labels import detect_labels
from detection.schedules import detect_schedules
from detection.postprocess import _cross_validate, _resolve_wall_window_conflicts, _suppress
```

## Dependency graph (verified acyclic)

Build order respects this DAG (each module imports only from modules to its left):

```
geometry, layers
  └─ walls, windows, labels, schedules        (independent detectors)
       └─ doors.constants, doors.models
            └─ doors.shape, doors.arcs
                 └─ doors.leaves               (needs doors.arcs)
                      └─ doors.assembly        (needs doors.leaves, doors.shape, labels)
                           └─ doors.detect     (needs doors.arcs/leaves/assembly)
                                └─ postprocess  (needs doors.assembly)
                                     └─ orchestrator (needs all detectors + postprocess)
```

Two non-obvious edges, both downward (no cycle): `doors.assembly → labels` (`_find_nearby_label`) and `postprocess → doors.assembly` (`_dedupe_door_components`). These dictate task order: **labels before doors (Task 6 → 7), and postprocess after doors (Task 8).** A cycle check over the full edge set confirms the graph is acyclic.

---

### Task 1: `debug/` package

**Files:**
- Create: `debug/__init__.py` (empty), `debug/trace.py` (from `debug_trace.py`), `debug/renderer.py` (from `debug_renderer.py`)
- Delete: `debug_trace.py`, `debug_renderer.py`
- Modify: `heuristics.py` (line 9), `pipeline.py` (lines 16–17)

**Interfaces:** Produces `debug.trace.DebugTraceCollector`, `debug.renderer.generate_debug_viewer` — unchanged signatures.

- [ ] **Step 1: Create the package and move both files**

```bash
mkdir -p debug && touch debug/__init__.py
git mv debug_trace.py debug/trace.py
git mv debug_renderer.py debug/renderer.py
```

`debug/trace.py` imports only `from models import PathPrimitive` (no change). `debug/renderer.py` is stdlib-only (no change).

- [ ] **Step 2: Update importers**

`heuristics.py` line 9: `from debug_trace import DebugTraceCollector` → `from debug.trace import DebugTraceCollector`
`pipeline.py`: `from debug_trace import DebugTraceCollector` → `from debug.trace import …`; `from debug_renderer import generate_debug_viewer` → `from debug.renderer import …`

- [ ] **Step 3: Gate** — Run `python -m unittest discover tests` → `Ran 80 tests` … `OK`
- [ ] **Step 4: Commit** — `git add -A && git commit -m "refactor: move debug scripts into debug/ package"`

---

### Task 2: `gemini/` package

**Files:** Create `gemini/__init__.py` (empty), `gemini/client.py` (from `gemini_client.py`); Delete `gemini_client.py`; Modify `pipeline.py` (line 19)

**Interfaces:** Produces `gemini.client.*` (incl. `call_gemini`, `should_skip_gemini`) — unchanged signatures.

- [ ] **Step 1: Move** — `mkdir -p gemini && touch gemini/__init__.py && git mv gemini_client.py gemini/client.py` (`gemini/client.py` imports only `from models import …` — no change)
- [ ] **Step 2: Update importer** — `pipeline.py` line 19: `import gemini_client as gc` → `from gemini import client as gc` (all `gc.…` call sites unchanged)
- [ ] **Step 3: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 4: Commit** — `git add -A && git commit -m "refactor: move gemini client into gemini/ package"`

---

### Task 3: `extraction/` package

**Files:** Create `extraction/__init__.py` (empty), `extraction/{extractor,plumber,renderer}.py`; Delete `extractor.py`, `plumber.py`, `renderer.py`; Modify `extraction/plumber.py` (line 4), `pipeline.py` (lines 11–12, 18), `inspector.py` (lines 11–12)

**Interfaces:** Produces `extraction.extractor.{extract_page, SCALE}`, `extraction.plumber.{extract_plumber_page, build_plumber_counts, build_pymupdf_counts, compare_counts}`, `extraction.renderer.{render_page_png, draw_overlay}` — unchanged.

- [ ] **Step 1: Move the three files**

```bash
mkdir -p extraction && touch extraction/__init__.py
git mv extractor.py extraction/extractor.py
git mv plumber.py extraction/plumber.py
git mv renderer.py extraction/renderer.py
```

`extractor.py`/`renderer.py` import only `from models import …` (no change).

- [ ] **Step 2: Fix intra-package import** — `extraction/plumber.py` line 4: `from extractor import SCALE` → `from extraction.extractor import SCALE`
- [ ] **Step 3: Update external importers**

`pipeline.py`: line 11 → `from extraction.extractor import extract_page`; line 12 → `from extraction.plumber import (…)` (keep name list); line 18 → `from extraction.renderer import render_page_png, draw_overlay`
`inspector.py`: line 11 → `from extraction.extractor import extract_page, SCALE`; line 12 → `from extraction.plumber import extract_plumber_page, build_plumber_counts, build_pymupdf_counts, compare_counts`

- [ ] **Step 4: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 5: Commit** — `git add -A && git commit -m "refactor: move extractor/plumber/renderer into extraction/ package"`

---

### Task 4: `tools/` package

Relocate the standalone dev script so the target layout is complete.

**Files:** Create `tools/__init__.py` (empty), `tools/extract_hu_template.py` (from `extract_hu_template.py`); Delete `extract_hu_template.py`

**Interfaces:** None imported by the app — standalone numpy/cv2 script.

- [ ] **Step 1: Move** — `mkdir -p tools && touch tools/__init__.py && git mv extract_hu_template.py tools/extract_hu_template.py`
- [ ] **Step 2: Verify it still imports** — Run `python -c "import ast; ast.parse(open('tools/extract_hu_template.py').read())"` (no importers to fix; it only imports numpy/cv2). Expected: no output.
- [ ] **Step 3: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 4: Commit** — `git add -A && git commit -m "refactor: move extract_hu_template into tools/ package"`

---

### Task 5: Shared `detection/geometry.py` + `detection/layers.py`

Create the `detection` package and extract the two shared foundation modules. `heuristics.py` imports them back so it keeps working.

**Files:** Create `detection/__init__.py` (empty for now), `detection/geometry.py`, `detection/layers.py`; Modify `heuristics.py` (remove moved defs, add back-imports)

- [ ] **Step 1: Create the package** — `mkdir -p detection && touch detection/__init__.py`
- [ ] **Step 2: Create `detection/geometry.py`** — paste the `detection/geometry.py` header from **Computed module headers**, then move every symbol in the **geometry** assignment-table row verbatim. **Includes `_bbox_area`** (relocated from postprocess to break the postprocess↔doors.assembly cycle).
- [ ] **Step 3: Create `detection/layers.py`** — paste the `detection/layers.py` header, then move `_LAYER_TOKEN_RE`, `_layer_tokens`, `_layer_hint`, `_layer_strong_prior`, `_layer_hint_from_layer` verbatim.
- [ ] **Step 4: Back-import into `heuristics.py`**

```python
from detection.geometry import (
    _bbox_center, _distance, _line_length, _line_angle_deg, _angle_diff_mod180,
    _bbox_width, _bbox_height, _point_in_bbox, _is_line_path,
    _point_to_segment_distance, _segments_min_distance,
    _bbox_expanded, _bboxes_overlap, _bbox_union, _bbox_area,
    _projected_interval, _interval_overlap, _perpendicular_spacing, _project_onto_axis,
)
from detection.layers import (
    _LAYER_TOKEN_RE, _layer_tokens, _layer_hint, _layer_strong_prior, _layer_hint_from_layer,
)
```

Remove those definitions from `heuristics.py`.

- [ ] **Step 5: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 6: Commit** — `git add -A && git commit -m "refactor: extract shared geometry + layer helpers into detection/"`

---

### Task 6: Independent detectors (walls, windows, labels, schedules)

Move the four detectors that depend only on `geometry`/`layers`/`models`. **Postprocess is NOT in this task** — it imports `doors.assembly`, so it comes after doors (Task 8). `labels` is here because `doors.assembly` will import `_find_nearby_label` from it.

**Files:** Create `detection/{walls,windows,labels,schedules}.py`; Modify `heuristics.py`

**No cross-detector imports** — windows does not import walls; the previously-shared line helpers now live in `geometry`.

- [ ] **Step 1: `detection/walls.py`** — paste the `detection/walls.py` header from **Computed module headers**, then move the **walls** assignment-table row verbatim (`WALL_*`, `COLLINEAR_*`, `_is_diagonal_hatch_angle`, `_wall_material_evidence`, `_merge_collinear_segments`, `detect_walls`, `_stroke_percentile_rank`).
- [ ] **Step 2: `detection/windows.py`** — paste the `detection/windows.py` header, then move the **windows** row verbatim (`WINDOW_*`, `WINDOW_HATCH_REJECT_*`, `detect_windows`).
- [ ] **Step 3: `detection/labels.py`** — paste the `detection/labels.py` header, then move the **labels** row verbatim (`LABEL_*`, `_find_nearby_label`, `detect_labels`).
- [ ] **Step 4: `detection/schedules.py`** — paste the `detection/schedules.py` header, then move the **schedules** row verbatim (incl. dead `SCHEDULE_KEYWORDS` at 162 and live `SCHEDULE_KEYWORDS_RE` at 3333).
- [ ] **Step 5: Back-import into `heuristics.py`**

```python
from detection.walls import detect_walls, _wall_material_evidence, _stroke_percentile_rank
from detection.windows import detect_windows, WINDOW_HATCH_REJECT_MIN, WINDOW_HATCH_REJECT_RATIO
from detection.labels import detect_labels, _find_nearby_label
from detection.schedules import detect_schedules
```

Remove the moved definitions/constants from `heuristics.py`. (`run_heuristics`, `_cross_validate`, and the door code all still live in `heuristics.py` and call these via the back-imports. Tests' `from heuristics import detect_walls, detect_windows` stay resolvable until Task 9.)

- [ ] **Step 6: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 7: Commit** — `git add -A && git commit -m "refactor: split wall/window/label/schedule detectors into detection modules"`

---

### Task 7: `detection/doors/` subpackage

Split the remaining ~2,650 lines of door logic bottom-up so each module imports only from layers below (see the verified DAG). `heuristics.py` keeps back-imports of `detect_doors` plus every door internal/constant the tests use. **Paste each module's header from Computed module headers, move the assigned bodies, then run the gate and commit after each sub-step** so a break is isolated.

**Files:** Create `detection/doors/{__init__,constants,models,shape,arcs,leaves,assembly,detect}.py`; Modify `heuristics.py`

- [ ] **Step 1: Scaffold** — `mkdir -p detection/doors && touch detection/doors/__init__.py`
- [ ] **Step 2: `constants.py`** — header `from __future__ import annotations` + `import re`; move the **doors/constants** row verbatim. Back-import into `heuristics.py` (`from detection.doors.constants import *  # noqa: F401,F403`). Gate → commit.
- [ ] **Step 3: `models.py`** — paste the `detection/doors/models.py` header; move `_DoorSwing`, `_DoorLeaf` verbatim. Back-import into `heuristics.py`. Gate → commit.
- [ ] **Step 4: `shape.py`** — paste the `detection/doors/shape.py` header (incl. the cv2/np try-block); move `_rasterize_paths_to_canvas`, `_compute_hu_distance`. Back-import into `heuristics.py` (incl. `_HU_AVAILABLE`). Gate → commit.
- [ ] **Step 5: `arcs.py`** — paste the `detection/doors/arcs.py` header; move the **doors/arcs** row verbatim (all 12 funcs incl. `_detect_polyline_arc_bboxes`, `_detect_curve_arc_double_partners`, `_collect_door_swings`). Back-import into `heuristics.py`. Gate → commit.
- [ ] **Step 6: `leaves.py`** — paste the `detection/doors/leaves.py` header; move the **doors/leaves** row verbatim (incl. `_snap_key`, the `_LinkSeg` type alias, `_try_linework_leaf_clean_loop`, `_find_thin_rectangle_cycle`). Note it imports `_arc_corners` from `doors.arcs`. Back-import into `heuristics.py`. Gate → commit.
- [ ] **Step 7: `assembly.py`** — paste the `detection/doors/assembly.py` header (note it imports `_find_nearby_label` from `detection.labels` and `_compute_hu_distance` from `detection.doors.shape`); move the **doors/assembly** row verbatim. Back-import into `heuristics.py`. Gate → commit.
- [ ] **Step 8: `detect.py`** — paste the `detection/doors/detect.py` header; move `detect_doors` verbatim. Set `detection/doors/__init__.py` to `from detection.doors.detect import detect_doors`. Replace the door back-imports in `heuristics.py` with `from detection.doors import detect_doors` plus the explicit internals/constants the tests pull (see Task 9). Gate → commit `"refactor: complete detection/doors subpackage"`.
- [ ] **Step 9: Final subpackage gate** — `python -m unittest discover tests` → `OK`. `heuristics.py` now holds only `run_heuristics`, the still-in-place postprocess code, and back-imports.

---

### Task 8: `detection/postprocess.py`

Postprocess is split out **after** doors because `_cross_validate` imports `_dedupe_door_components` from `detection.doors.assembly` (built in Task 7).

**Files:** Create `detection/postprocess.py`; Modify `heuristics.py`

- [ ] **Step 1: Create `detection/postprocess.py`** — paste the `detection/postprocess.py` header from **Computed module headers** (imports `_bbox_area` etc. from `geometry`, `_dedupe_door_components` from `doors.assembly`); move the **postprocess** row verbatim (`CROSS_*`, `NMS_*`, `_cross_validate`, `_bbox_iou`, `_projected_overlap_1d`, `_suppress`, `_bbox_is_horizontal`, `_resolve_wall_window_conflicts`).
- [ ] **Step 2: Back-import into `heuristics.py`**

```python
from detection.postprocess import (
    _cross_validate, _suppress, _resolve_wall_window_conflicts,
    CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY, CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY,
)
```

Remove the moved definitions from `heuristics.py`. Now `heuristics.py` holds only `run_heuristics` + back-imports.

- [ ] **Step 3: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 4: Commit** — `git add -A && git commit -m "refactor: split postprocess into detection/postprocess.py"`

---

### Task 9: `detection` orchestrator + public facade

**Files:** Create `detection/orchestrator.py`; Modify `detection/__init__.py`, `pipeline.py` (line 15), `inspector.py` (line 13), `heuristics.py`

**Interfaces:** Produces `detection.run_heuristics` + `detection.{detect_doors, detect_windows, detect_walls, detect_labels, detect_schedules}`.

- [ ] **Step 1: Create `detection/orchestrator.py`** — paste the `detection/orchestrator.py` header from **Computed module headers**; move `run_heuristics` (line ~3628) verbatim.

- [ ] **Step 2: Write `detection/__init__.py` facade**

```python
from detection.orchestrator import run_heuristics
from detection.doors import detect_doors
from detection.windows import detect_windows
from detection.walls import detect_walls
from detection.labels import detect_labels
from detection.schedules import detect_schedules

__all__ = [
    "run_heuristics", "detect_doors", "detect_windows",
    "detect_walls", "detect_labels", "detect_schedules",
]
```

- [ ] **Step 3: Switch real callers** — `pipeline.py` line 15 & `inspector.py` line 13: `from heuristics import run_heuristics` → `from detection import run_heuristics`

- [ ] **Step 4: Reduce `heuristics.py` to a test bridge**

```python
from detection.orchestrator import run_heuristics  # noqa: F401
from detection.doors.detect import detect_doors  # noqa: F401
from detection.walls import detect_walls  # noqa: F401
from detection.windows import detect_windows  # noqa: F401
from detection.doors.constants import *  # noqa: F401,F403
from detection.doors.arcs import (  # noqa: F401
    _prune_arc_spurs, _prune_arc_cycle_caps, _split_double_arc,
    _trim_chain_extension_caps, _estimate_arc_sweep_deg,
    _native_curve_chains, _fit_circle_3pt,
)
from detection.doors.assembly import (  # noqa: F401
    _check_opening_clear, _dedupe_door_components, _merge_double_door_assemblies,
)
from detection.postprocess import (  # noqa: F401
    _cross_validate, CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY,
    CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY,
)
```

- [ ] **Step 5: Gate** — `python -m unittest discover tests` → `OK`
- [ ] **Step 6: Commit** — `git add -A && git commit -m "refactor: add detection orchestrator + public facade; reduce heuristics.py to bridge"`

---

### Task 10: Repoint tests, delete the bridge

**Files:** Modify the 4 test files; Delete `heuristics.py`

- [ ] **Step 1: `tests/test_curve_arc_garden_doors.py`** — `from heuristics import detect_doors` → `from detection import detect_doors`

- [ ] **Step 2: `tests/test_chained_curve_arcs.py`**

```python
from detection import detect_doors
from detection.doors.arcs import _fit_circle_3pt, _native_curve_chains
from detection.doors.constants import DOOR_CURVE_CHAIN_MIN_CURVES, DOOR_MIN_SIZE_PX
```

- [ ] **Step 3: `tests/test_polyline_arc_pruning.py`**

```python
from detection.doors.arcs import (
    _prune_arc_cycle_caps, _prune_arc_spurs, _split_double_arc, _trim_chain_extension_caps,
)
from detection.doors.constants import (
    DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS, DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS,
    DOOR_POLYLINE_CHAIN_DELTA_DEG, DOOR_POLYLINE_CYCLE_MAX_SEGMENTS,
    DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_SPUR_MAX_SEGMENTS,
)
```

- [ ] **Step 4: `tests/test_door_assembly.py`**

```python
from detection import detect_doors, detect_walls, detect_windows
from detection.doors.arcs import _estimate_arc_sweep_deg
from detection.doors.assembly import (
    _check_opening_clear, _dedupe_door_components, _merge_double_door_assemblies,
)
from detection.postprocess import _cross_validate, CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY
from detection.doors.constants import (
    DOOR_ARC_FALLBACK_MAX, DOOR_ASSEMBLY_LINE_LEAF_BASE, DOOR_FALLBACK_CONFIDENCE,
    DOOR_POLYLINE_MAX_ANGLE_BINS, DOOR_THRESHOLD_CONFIDENCE_BOOST,
    DOOR_V2_OPENING_CLEAR_BOOST, DOOR_V2_OPENING_OBSTRUCTED_PENALTY,
)
```

Also fix the in-body import at `tests/test_door_assembly.py:193`: `from heuristics import CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY` → `from detection.postprocess import CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY`. (The `from pipeline import merge_gemini_and_heuristics` import at line 23 stays — `pipeline.py` is at root, unchanged.)

- [ ] **Step 5: Delete the bridge** — `git rm heuristics.py`
- [ ] **Step 6: Gate** — `python -m unittest discover tests` → `Ran 80 tests` … `OK`. (Any `ImportError` names the symbol whose new home is wrong — fix the path against the assignment table and re-run.)
- [ ] **Step 7: Commit** — `git add -A && git commit -m "refactor: repoint tests to detection package, remove heuristics.py"`

---

### Task 11: End-to-end smoke test + baseline comparison

Verify the untested window/wall/label/schedule paths behave identically end-to-end. Use a throwaway **git worktree** for the baseline so the dirty working tree (currently `CLAUDE.md`) is never touched. The worktree has **no `.venv`** (it isn't tracked), so invoke the main repo's interpreter by absolute path — the same site-packages, just a different working directory.

**Files:** none (verification only).

- [ ] **Step 1: Capture a pre-refactor baseline from a worktree of `main`**

```bash
VENV_PY="/Users/nestimate/Documents/GitHub/agent/.venv/bin/python"
git worktree add /tmp/restructure-baseline main
( cd /tmp/restructure-baseline && "$VENV_PY" app.py extract 5-1133-WD03.pdf --no-gemini --out /tmp/baseline )
```

(Runs the original flat-layout code with the main venv's packages, without disturbing the current branch or working tree.)

- [ ] **Step 2: Run the same extract on the refactored branch**

```bash
source .venv/bin/activate
python app.py extract 5-1133-WD03.pdf --no-gemini --out /tmp/refactored
```

- [ ] **Step 3: Compare entity output (ignoring timestamps)**

```bash
diff <(cat /tmp/baseline/*/pages/*/final_entities.json) \
     <(cat /tmp/refactored/*/pages/*/final_entities.json) && echo "IDENTICAL"
```

Expected: `IDENTICAL`. (Compare `final_entities.json` only; `summary.json` carries timestamps that will differ.)

- [ ] **Step 4: Smoke the inspect command** — Run `python app.py inspect 5-1133-WD03.pdf`. Expected: terminal summary renders without error.

- [ ] **Step 5: Clean up the worktree** — `git worktree remove /tmp/restructure-baseline`

- [ ] **Step 6:** If Step 3 reported any diff, treat it as a regression: locate the symbol moved to the wrong module via the assignment table, fix, re-run the gate and Step 3. No commit needed if there were no discrepancies (verification-only task).

---

## Self-Review

**Spec coverage:** Target layout incl. `tools/` (Tasks 1–4), shared geometry/layers foundation (Task 5), the four independent detectors (Task 6), complete doors subpackage (Task 7), postprocess (Task 8), orchestrator + facade (Task 9), repointed tests with no shim (Task 10), worktree smoke test (Task 11), out-of-scope boundary honored. All spec sections map to a task.

**Completeness:** The assignment table covers **every** top-level `def`/`class`/constant in `heuristics.py` (verified against a full AST census), including the previously-omitted door helpers (`_detect_polyline_arc_bboxes`, `_collect_door_swings`, `_detect_curve_arc_double_partners`, `_try_linework_leaf_clean_loop`, `_find_thin_rectangle_cycle`, `_snap_key`, `_LinkSeg`), the shared layer helpers, and the `COLLINEAR_*`/`NMS_*`/`SCHEDULE_KEYWORDS_RE`/`WINDOW_HATCH_REJECT_*` constants.

**Imports are computed, not guessed:** the **Computed module headers** section was generated by AST-walking each module's assigned bodies and resolving every referenced name (stdlib, `models` type, `debug.trace`, cross-module symbol) to its source. This eliminates the missing-import class of error (e.g. `defaultdict`/`combinations` in `arcs`, `_arc_corners` in `leaves`, `_line_length`/`_bbox_width/_height` in `windows`/`walls`). Optional belt-and-suspenders before the test gate: `pip install pyflakes && python -m pyflakes detection/` flags any remaining undefined name (F821) statically.

**Verified acyclic:** a cycle check over the full cross-module edge set returns none. The two non-obvious edges — `doors.assembly → labels` and `postprocess → doors.assembly` — are both downward; `_bbox_area` was moved to `geometry` specifically to break the only mutual edge. Task order honors the DAG: labels before doors (6→7), postprocess after doors (8).

**Type consistency:** Public names (`run_heuristics`, the five `detect_*`) and shared names (`DebugTraceCollector`, `_DoorSwing`, `_DoorLeaf`, `_LinkSeg`) are used identically across the assignment table, computed headers, bridge, and test-repoint steps.

**Residual judgment call:** `from detection.doors.constants import *` is used inside door submodules as a convenience (the constants are a single cohesive tuning surface); replace with the explicit name lists from the Computed headers if a linter objects.
