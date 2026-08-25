# File map — where everything lives, by detection type

Paths are repo-relative. Read the "Read first" column before diagnosing.

## By entity type

| Type | Detector | Constants (`SCREAMING_*`) | Read first | Synthetic-test file + helpers |
|---|---|---|---|---|
| Doors (swing / sliding / folding) | `detection/doors/` (acyclic: `constants` ← `arcs`/`leaves`/`shape`/`sliding` ← `folding` ← `assembly` ← `detect`) | `detection/doors/constants.py` (`DOOR_*`, ~100) | `docs/door-detection-tuning-guide.md` — §3 topologies, §4 constants table, §5 known FP patterns, **§8 debug playbook**, §7 test-coordinate gotcha | `tests/test_door_assembly.py`, `test_polyline_arc_pruning.py`, `test_chained_curve_arcs.py`, `test_curve_arc_garden_doors.py`, `test_folding_doors.py`, `test_bezier_arc_aspect.py` |
| Windows | `detection/windows.py` | `WINDOW_*` in the same file | `docs/window-detection-tuning-guide.md` — §1 signature, §4 constants, §6 limitations, §7 how to verify | `tests/test_window_detection.py` |
| Walls (internal network, never emitted) | `detection/walls.py` — `detect_wall_network`, `_demote_lattice_faces`, `_demote_stair_faces`, `_band_has_wall_material`, `_claims_interior_pair`, `_claims_far_side_pair`, `_rate_fill_classes` | `WALL_*` in `detection/walls.py` (~70) | CLAUDE.md "Room detection" paragraph (the rules + every measured number); module docstring of `walls.py` | `tests/test_wall_network.py` (`wall_band_h/v`, `rect_room`, `hline/vline`, `path`) |
| Rooms | `detection/rooms.py` — `detect_rooms`, `_free_space_components`, `_door_plugs`, `_window_seal`, `_accept_white_walls`, `_bridge_white_runs`, `_drop_window_exterior_sides` | `ROOM_*` in `detection/rooms.py` (~40) | same as walls, plus `docs/superpowers/specs/2026-08-18-room-takeoff-design.md` if quantities are involved | `tests/test_room_detection.py` (`rooms_for`, `door_candidate`, `text_span`, plus the wall helpers) |
| Labels / schedules | `detection/labels.py`, `detection/schedules.py` | `LABEL_*`, `SCHEDULE_*` in place | `docs/superpowers/specs/2026-08-06-detection-review-tooling-design.md`; schedule bboxes come from pdfplumber `find_tables()` | `tests/test_schedule_detection.py` |
| Cross-validation / confidence floors | `detection/postprocess.py` (`CROSS_*`), `pipeline.py::OFFLINE_MIN_CONFIDENCE` (line ~90), `pipeline.finalize_candidates` | | door guide §4.10–4.11 | `tests/test_cross_validate.py`, `test_merge_offline.py` |
| Scale-dependent gates | `scale/factor.py` (`detection_scale`), `WallGates`/`RoomGates` | classified in `docs/scale-normalization-findings.md` §4 (W = world, scales; P = paper; D = dimensionless) | that §4 table before touching any constant — it says whether a gate scales with drawing scale | `tests/test_scale_gates.py`, `test_scale_door_gates.py`, `test_scale_window_gates.py` |
| Region filtering (elevations leaking into detection) | `layout/` + `gemini/classifier.py`, `pipeline.resolve_page_regions` | `layout/constants.py`, `REGION_MIN_COVERAGE_FRAC` | `docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md` | `tests/test_layout_*.py`, `test_region_*.py` |

Shared geometry: `detection/geometry.py`. Layer hints: `detection/layers.py`.
Orchestration order (doors → windows → wall network → rooms):
`detection/orchestrator.py::run_heuristics`.

## Regression corpus and tooling

| What | Where |
|---|---|
| The guide (read §9, §10, §12, §13 every time) | `docs/regression-testing-guide.md` |
| Corpus membership + sha pins + `labeled` flag | `fixtures/MANIFEST.json` (PDFs in `fixtures/sheets/`, NOT committed) |
| Verdicts (user-owned, never invent) | `tests/ground_truth/sNN.json` — `confirmed` / `false_positives` / `deferred` per page |
| Sweep | `python tools/regress.py [--sheet sNN]... [--json] [--debug]` — exit 1 = lost confirmed / returned FP / broken GT, 2 = missing sheets |
| Sweep output | `outputs/regress/<slug>/<ts>/pages/page_NN/{overlay.png,review_<type>.png,final_entities.json,candidates.json,primitives.json}` (gitignored, wiped per slug on re-sweep) |
| Before/after pictures | `python tools/compare_sweeps.py sNN --snapshot` (before), `python tools/compare_sweeps.py sNN [--type room]` (after) → `outputs/compare/<slug>/page_NN_{side_by_side,changes}.png` |
| Record verdicts (user runs, or asks you to) | `python tools/review.py sNN` |
| Adopt a new sheet | `python tools/add_sheet.py` — new slug always, never overwrite |
| Corpus code | `regression/{corpus,ground_truth,matching,sweep,run_dir,review_render}.py` |
| Single-PDF run with trace | `python app.py extract <pdf> --no-gemini --debug [--disable-windows] [--svg]` → `outputs/<ts>/pages/page_NN/debug_trace.json` + `debug_viewer.html` |

Sheet notes: s01 (`floor-plans`) and s02 (WD03) are the reference tier — every
rule in CLAUDE.md was measured on them, so measure your discriminator there
too. s01 is colour-coded (walls black/magenta, dims blue, furniture red, all
~1.5px) and its typed 1:50 is really 1:92.2, so it runs detection at identity
scale. s09/s19 detect nothing (unexplained, unlabeled).

## History and open work

| What | Where |
|---|---|
| Design specs (one per feature branch) | `docs/superpowers/specs/*.md` |
| Ranked accuracy backlog | `docs/backlog/README.md` + `step-N-*.md` |
| Findings / handoffs | `docs/*-findings.md`, `docs/w-gate-recalibration-handoff.md` |
| Knowledge graph | `graphify query "<q>"`, `graphify explain "<concept>"`, `graphify-out/GRAPH_REPORT.md`; run `graphify update .` after code changes |

## Output contract you must not break

`outputs/` JSON shapes (`primitives.json`, `candidates.json`,
`final_entities.json`, `takeoff.json` schema_version 1) and 150-DPI pixel
space everywhere past `extraction/`. A detection fix never changes these.
