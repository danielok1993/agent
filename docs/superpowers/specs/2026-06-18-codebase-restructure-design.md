# Codebase Restructure: Packages + heuristics.py Split

**Date:** 2026-06-18
**Status:** Approved design, ready for implementation plan

## Goal

Clean up the flat root-level module layout and decompose the 3,679-line
`heuristics.py` monolith into focused, single-responsibility packages. This is
**pure code movement** — zero behavior change. The CLI surface (`python app.py
…`) and the `outputs/` JSON contract stay byte-for-byte identical.

Scope is deliberately minimal: relocate code and fix imports. No logic changes,
no function/constant renames, no docstring rewrites, no `docs/` edits. A
follow-up pass can tackle naming and docs once the structure is in place.

## Context

- Detection accuracy work is mature (80 passing tests, all door-focused).
- `heuristics.py` is 3,679 lines (~150 KB): door logic dominates (~2,650 lines),
  followed by `detect_windows`, `detect_walls`, `detect_labels`,
  `detect_schedules`, and cross-validation/suppression/orchestration.
- All modules currently import siblings by bare name (`from models import …`,
  `from heuristics import …`); `python app.py` runs from root, so root is on
  `sys.path`.
- Tests import ~30 symbols directly from `heuristics`: the public `detect_*`
  functions plus many private helpers and `DOOR_*`/`CROSS_*` constants.
- Only door detection has test coverage. Window/wall/label/schedule code has no
  safety net, so their relocation is verified via an end-to-end smoke run.

## Target layout

Packages are created **at root** (no wrapping `src/` or umbrella package — that
would churn every import for no benefit). Thin orchestration entry points stay
at root where they naturally live.

```
app.py                       # entry — unchanged CLI behavior
models.py                    # shared dataclasses — depended on by everything
pipeline.py                  # 7-stage orchestrator
inspector.py                 # inspect-command logic

extraction/                  # PDF -> normalized primitives + rendering
  __init__.py
  extractor.py               # PyMuPDF, owns SCALE
  plumber.py
  renderer.py

detection/                   # heuristic detection (the split monolith)
  __init__.py                # public facade: re-exports run_heuristics + detect_*
  geometry.py                # shared primitives (_distance, _line_angle_deg, …)
  windows.py                 # detect_windows + WINDOW_*
  walls.py                   # detect_walls + WALL_*
  labels.py                  # detect_labels + LABEL_*
  schedules.py               # detect_schedules + SCHEDULE_*
  postprocess.py             # _cross_validate, _suppress, conflict resolution, CROSS_*
  orchestrator.py            # run_heuristics  (named to avoid clash with root pipeline.py)
  doors/                     # see below

gemini/
  __init__.py
  client.py                  # was gemini_client.py

debug/
  __init__.py
  trace.py                   # was debug_trace.py
  renderer.py                # was debug_renderer.py

tools/
  extract_hu_template.py     # standalone dev script (numpy/cv2)
```

## detection/doors/ subpackage

Door logic split along its natural seams, ordered by dependency. Each layer
imports only from layers above it plus `detection/geometry.py`. Direction is
acyclic: `constants` <- `arcs`/`leaves`/`shape` <- `assembly` <- `detect`.

```
detection/doors/
  __init__.py        # re-exports detect_doors (+ helpers/constants tests reach)
  constants.py       # all DOOR_* tunables, grouped by existing comment banners
  arcs.py            # _is_arc_like, _arc_corners, _estimate_arc_sweep_deg,
                     #   _prune_arc_spurs, _prune_arc_cycle_caps, _split_double_arc,
                     #   _trim_chain_extension_caps, _native_curve_chains, _fit_circle_3pt
  leaves.py          # _is_door_leaf, _collect_door_leaves, _collect_linework_door_leaves,
                     #   _find_anchored_leaf_line, _find_leaf_companion_lines
  shape.py           # _rasterize_paths_to_canvas, _compute_hu_distance
  assembly.py        # _pair_door_assemblies, _merge_double_door_assemblies,
                     #   _find_threshold_line, _dedupe_door_components, _check_opening_clear,
                     #   _door_fallback_candidate, _component_indices
  detect.py          # detect_doors — wires arcs -> leaves -> shape -> assembly
```

### Decisions

- **Constants placement.** All `DOOR_*` live in one `doors/constants.py`, not
  scattered per-module. Many tolerances are read by multiple door submodules,
  and a single constants file keeps the tuning surface in one place — matching
  how `docs/door-detection-tuning-guide.md` treats them.
- **geometry.py ownership.** Generic helpers (`_distance`, `_line_angle_deg`,
  `_point_to_segment_distance`, `_angle_diff_mod180`, bbox helpers) move to
  `detection/geometry.py` since windows/walls use them too. Door-specific
  geometry stays in `doors/`.

## Public facade & test strategy

`detection/__init__.py` re-exports the genuine public API: `run_heuristics`,
`detect_doors`, `detect_windows`, `detect_walls`, `detect_labels`,
`detect_schedules`.

The 4 test files are **updated** to import internals from their real new homes
(e.g. `from detection.doors.arcs import _prune_arc_spurs`, `from
detection.doors.constants import DOOR_MIN_SIZE_PX`). No compatibility shim — the
old `heuristics.py` is deleted. Tests then point honestly at where code lives.

Callers switch import sites:
- `pipeline.py`: `from heuristics import run_heuristics` -> `from detection import run_heuristics`
- `inspector.py`: same; plus `extractor`/`plumber` -> `extraction.*`,
  `debug_*` -> `debug.*`, `gemini_client` -> `gemini.client`.

## Execution plan (incremental — run all 80 tests after each step)

1. **Leaf packages** — `debug/`, `gemini/`, `extraction/`. Move files, fix their
   imports, update `pipeline.py`/`inspector.py`. Run tests.
2. **detection/geometry.py** — extract shared primitives; `heuristics.py`
   imports them back temporarily. Run tests.
3. **Non-door detectors** — `windows.py`, `walls.py`, `labels.py`,
   `schedules.py`, `postprocess.py`. Run tests.
4. **detection/doors/** — split bottom-up: `constants` -> `arcs` -> `leaves` ->
   `shape` -> `assembly` -> `detect`. Run tests after each.
5. **detection/orchestrator.py** + `detection/__init__.py` facade; delete the
   now-empty `heuristics.py`. Run tests.
6. **Update the 4 test files** to import internals from new modules. Run tests.
7. **Smoke test** — `python app.py extract 5-1133-WD03.pdf --no-gemini`
   (exercises untested window/wall/label/schedule paths end-to-end) plus
   `python app.py inspect 5-1133-WD03.pdf`.

## Verification

- 80 unit tests green after every step.
- End-to-end smoke run produces the same entity counts and JSON structure as a
  pre-refactor baseline run.

## Out of scope (this pass)

- No logic or behavior changes.
- No function/constant renaming.
- No docstring or `docs/` edits.
- No new tests for window/wall/label/schedule (tracked as future work).
