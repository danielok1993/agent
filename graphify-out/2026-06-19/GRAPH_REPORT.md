# Graph Report - agent  (2026-06-19)

## Corpus Check
- 48 files · ~53,591 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 771 nodes · 1907 edges · 31 communities (30 shown, 1 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 264 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d508fe05`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Geometry Helpers|Geometry Helpers]]
- [[_COMMUNITY_Door Detection Core|Door Detection Core]]
- [[_COMMUNITY_Door Leaf & BBox Primitives|Door Leaf & BBox Primitives]]
- [[_COMMUNITY_PDF Extraction & Normalization|PDF Extraction & Normalization]]
- [[_COMMUNITY_Hu-Moment Shape Matching|Hu-Moment Shape Matching]]
- [[_COMMUNITY_CLI & Rendering|CLI & Rendering]]
- [[_COMMUNITY_Debug Trace Collector|Debug Trace Collector]]
- [[_COMMUNITY_Double-Door Assembly|Double-Door Assembly]]
- [[_COMMUNITY_Sample Drawing Elements|Sample Drawing Elements]]
- [[_COMMUNITY_Arc Swing Detection|Arc Swing Detection]]
- [[_COMMUNITY_Chain-Extension Cap Trim|Chain-Extension Cap Trim]]
- [[_COMMUNITY_Double-Arc Split Tests|Double-Arc Split Tests]]
- [[_COMMUNITY_Cycle-Cap Pruning|Cycle-Cap Pruning]]
- [[_COMMUNITY_Project Docs & Pipeline Concepts|Project Docs & Pipeline Concepts]]
- [[_COMMUNITY_Gemini Client|Gemini Client]]
- [[_COMMUNITY_Arc Spur Pruning|Arc Spur Pruning]]
- [[_COMMUNITY_Arc Pruning Design Docs|Arc Pruning Design Docs]]
- [[_COMMUNITY_Hu Template Tool|Hu Template Tool]]
- [[_COMMUNITY_Codebase Restructure Docs|Codebase Restructure Docs]]
- [[_COMMUNITY_Single-Arc Guard Test|Single-Arc Guard Test]]
- [[_COMMUNITY_README|README]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 92 edges
2. `Candidate` - 82 edges
3. `DebugTraceCollector` - 56 edges
4. `TextSpan` - 47 edges
5. `detect_doors()` - 43 edges
6. `detect_windows()` - 43 edges
7. `PageData` - 31 edges
8. `run_extract()` - 24 edges
9. `run_heuristics()` - 23 edges
10. `_chain()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Door heuristic constants tuning surface` --conceptually_related_to--> `_detect_polyline_arc_bboxes()`  [INFERRED]
  docs/door-detection-tuning-guide.md → detection/doors/arcs.py
- `detect_doors()` --implements--> `Three-stage door detection (collect/pair/validate)`  [INFERRED]
  detection/doors/detect.py → docs/door-detection-tuning-guide.md
- `_prune_arc_cycle_caps()` --implements--> `Arc closed-cycle cap pruning`  [EXTRACTED]
  detection/doors/arcs.py → docs/door-detection-tuning-guide.md
- `_split_double_arc()` --implements--> `Double-arc / garden-door split-emit`  [EXTRACTED]
  detection/doors/arcs.py → docs/door-detection-tuning-guide.md
- `_detect_polyline_arc_bboxes()` --implements--> `Polyline-arc detection micro-pipeline`  [EXTRACTED]
  detection/doors/arcs.py → docs/door-detection-tuning-guide.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Door detection three-stage flow** — doors_arcs_collect_door_swings, doors_leaves_collect_door_leaves, doors_assembly_pair_door_assemblies, detection_postprocess_cross_validate [EXTRACTED 0.90]
- **Polyline-arc micro-pipeline prune/split steps** — doors_arcs_prune_arc_spurs, doors_arcs_prune_arc_cycle_caps, doors_arcs_split_double_arc, doors_arcs_trim_chain_extension_caps, doors_arcs_detect_polyline_arc_bboxes [EXTRACTED 0.90]
- **Seven-stage extraction pipeline stages** — extraction_extractor_extract_page, extraction_renderer_render_page_png, extraction_plumber_extract_plumber_page, detection_orchestrator_run_heuristics, gemini_client_call_gemini, pipeline_merge_gemini_and_heuristics [EXTRACTED 0.90]
- **5-1133-WD03 proposed lower ground floor: walls, windows, doors** — 5_1133_wd03, 5_1133_wd03_cavity_walls, 5_1133_wd03_windows, 5_1133_wd03_folding_sliding_doors [EXTRACTED 1.00]
- **floor-plans proposed ground & first floor plans with rooms and rooflights** — floor_plans, floor_plans_ground_floor, floor_plans_first_floor, floor_plans_velux [EXTRACTED 1.00]

## Communities (31 total, 1 thin omitted)

### Community 0 - "Geometry Helpers"
Cohesion: 0.08
Nodes (50): BBox, Candidate, DebugTraceCollector, _DoorLeaf, _DoorSwing, PathPrimitive, TextSpan, _bbox_area() (+42 more)

### Community 1 - "Door Detection Core"
Cohesion: 0.08
Nodes (24): Candidate, DebugTraceCollector, PathPrimitive, TextSpan, _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, detect_doors(), DoorAssemblyTests (+16 more)

### Community 2 - "Door Leaf & BBox Primitives"
Cohesion: 0.06
Nodes (96): BBox, DebugTraceCollector, DebugTraceCollector, _DoorLeaf, PathPrimitive, _angle_diff_mod180(), _bbox_expanded(), _bbox_height() (+88 more)

### Community 3 - "PDF Extraction & Normalization"
Cohesion: 0.12
Nodes (44): 150-DPI pixel-space coordinate normalization, classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths(), extract_text() (+36 more)

### Community 4 - "Hu-Moment Shape Matching"
Cohesion: 0.06
Nodes (40): 3-point circle fit for chained-Bezier radius recovery, PathPrimitive, PathPrimitive, BBox, Candidate, _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point (+32 more)

### Community 5 - "CLI & Rendering"
Cohesion: 0.11
Nodes (37): cmd_extract(), cmd_inspect(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., _draw_dashed_rect() (+29 more)

### Community 6 - "Debug Trace Collector"
Cohesion: 0.09
Nodes (23): CLAUDE.md project guide, debug_trace.json schema + diagnostic playbook, Three-stage door detection (collect/pair/validate), Door Detection Tuning Guide, Known door false-positive patterns (bath fixture, window arc), Door heuristic constants tuning surface, pdfplumber cross-check + table extraction, Seven-stage per-page extraction pipeline (+15 more)

### Community 7 - "Double-Door Assembly"
Cohesion: 0.10
Nodes (22): curve_arc garden-door partner pairing, _merge_double_door_assemblies(), Parse an evidence bbox value defensively; return None on any invalid shape., Merge pairs of adjacent single-door assemblies into double-swing candidates., _safe_bbox(), Double-arc / garden-door split-emit, Garden door / double-swing assembly, DoorEvidencePropagationTests (+14 more)

### Community 8 - "Sample Drawing Elements"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 9 - "Arc Swing Detection"
Cohesion: 0.05
Nodes (39): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`), 3.4 Polyline arc + Y-junction stop (spur-prunable) (+31 more)

### Community 10 - "Chain-Extension Cap Trim"
Cohesion: 0.15
Nodes (14): Linear cap chain-extension trim, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end. (+6 more)

### Community 11 - "Double-Arc Split Tests"
Cohesion: 0.12
Nodes (16): PathPrimitive, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, _split_double_arc(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the (+8 more)

### Community 12 - "Cycle-Cap Pruning"
Cohesion: 0.16
Nodes (13): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, _chain(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t (+5 more)

### Community 13 - "Project Docs & Pipeline Concepts"
Cohesion: 0.07
Nodes (17): DebugTraceCollector, PathPrimitive, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+9 more)

### Community 14 - "Gemini Client"
Cohesion: 0.31
Nodes (12): Client, build_user_message(), call_gemini(), _candidate_to_dict(), encode_image_inline(), init_client(), parse_gemini_response(), Candidate (+4 more)

### Community 15 - "Arc Spur Pruning"
Cohesion: 0.14
Nodes (12): Arc closed-cycle cap pruning, _prune_arc_spurs(), Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, Arc leaf-spur pruning, Polyline-Arc Spur Pruning Design, PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s (+4 more)

### Community 16 - "Arc Pruning Design Docs"
Cohesion: 0.09
Nodes (26): _covers(), diagonal_window(), hline(), horizontal_window(), path(), PathPrimitive, Window detection tests.  Ground truth was established interactively on floor-pla, A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two (+18 more)

### Community 17 - "Hu Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 18 - "Codebase Restructure Docs"
Cohesion: 0.06
Nodes (35): Codebase restructure into packages, detection package acyclic dependency DAG, Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`) (+27 more)

### Community 19 - "Single-Arc Guard Test"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 27 - "Community 27"
Cohesion: 0.17
Nodes (10): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Output layout, Pipeline architecture (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (10): 1. The signature (cap-anchored), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target), 6. Known limitations / not handled (+2 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` → `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **117 isolated node(s):** `Project purpose`, `Algorithm reference`, `Commands`, `Module layout`, `Gemini / GCP auth` (+112 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` and `Door (architectural element)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `Hu-Moment Shape Matching` to `Geometry Helpers`, `Door Detection Core`, `Door Leaf & BBox Primitives`, `PDF Extraction & Normalization`, `CLI & Rendering`, `Double-Door Assembly`, `Chain-Extension Cap Trim`, `Double-Arc Split Tests`, `Cycle-Cap Pruning`, `Project Docs & Pipeline Concepts`, `Arc Spur Pruning`, `Arc Pruning Design Docs`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Geometry Helpers` to `Door Detection Core`, `Door Leaf & BBox Primitives`, `PDF Extraction & Normalization`, `Hu-Moment Shape Matching`, `CLI & Rendering`, `Double-Door Assembly`, `Gemini Client`, `Arc Pruning Design Docs`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `DebugTraceCollector` connect `Project Docs & Pipeline Concepts` to `Geometry Helpers`, `Door Detection Core`, `Door Leaf & BBox Primitives`, `Hu-Moment Shape Matching`, `CLI & Rendering`, `Double-Arc Split Tests`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Are the 67 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `PathPrimitive`) actually correct?**
  _`PathPrimitive` has 67 INFERRED edges - model-reasoned connections that need verification._
- **Are the 59 inferred relationships involving `Candidate` (e.g. with `Client` and `BBox`) actually correct?**
  _`Candidate` has 59 INFERRED edges - model-reasoned connections that need verification._