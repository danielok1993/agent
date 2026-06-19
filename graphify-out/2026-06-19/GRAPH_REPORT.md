# Graph Report - .  (2026-06-19)

## Corpus Check
- Corpus is ~48,590 words - fits in a single context window. You may not need a graph.

## Summary
- 559 nodes · 1568 edges · 27 communities (25 shown, 2 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 246 edges (avg confidence: 0.53)
- Token cost: 100,460 input · 17,727 output

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

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 81 edges
2. `Candidate` - 72 edges
3. `DebugTraceCollector` - 56 edges
4. `TextSpan` - 47 edges
5. `detect_doors()` - 43 edges
6. `PageData` - 31 edges
7. `run_extract()` - 24 edges
8. `_chain()` - 23 edges
9. `_pair_door_assemblies()` - 22 edges
10. `_bbox_width()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Door heuristic constants tuning surface` --conceptually_related_to--> `_detect_polyline_arc_bboxes()`  [INFERRED]
  docs/door-detection-tuning-guide.md → detection/doors/arcs.py
- `_pair_door_assemblies()` --conceptually_related_to--> `Offline-mode per-type confidence floors (OFFLINE_MIN_CONFIDENCE)`  [INFERRED]
  detection/doors/assembly.py → docs/door-detection-tuning-guide.md
- `detect_doors()` --implements--> `Three-stage door detection (collect/pair/validate)`  [INFERRED]
  detection/doors/detect.py → docs/door-detection-tuning-guide.md
- `_prune_arc_cycle_caps()` --implements--> `Arc closed-cycle cap pruning`  [EXTRACTED]
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

## Communities (27 total, 2 thin omitted)

### Community 0 - "Geometry Helpers"
Cohesion: 0.08
Nodes (59): _bbox_area(), _bbox_center(), _bbox_expanded(), _bboxes_overlap(), _interval_overlap(), _line_angle_deg(), _line_length(), _perpendicular_spacing() (+51 more)

### Community 1 - "Door Detection Core"
Cohesion: 0.07
Nodes (29): _DoorSwing, Candidate, DebugTraceCollector, TextSpan, BBox, _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, detect_doors() (+21 more)

### Community 2 - "Door Leaf & BBox Primitives"
Cohesion: 0.08
Nodes (51): BBox, BBox, Candidate, _DoorLeaf, PathPrimitive, DebugTraceCollector, _DoorLeaf, PathPrimitive (+43 more)

### Community 3 - "PDF Extraction & Normalization"
Cohesion: 0.12
Nodes (43): 150-DPI pixel-space coordinate normalization, classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths(), extract_text() (+35 more)

### Community 4 - "Hu-Moment Shape Matching"
Cohesion: 0.07
Nodes (32): PathPrimitive, _compute_hu_distance(), _rasterize_paths_to_canvas(), Rasterize line/curve primitives onto a normalized binary canvas.      Segments a, Distance between candidate arc paths and the door Hu Moment template.      Lower, Hu-moment door-shape matching, PathPrimitive, ChainedCurveSwingDetectionTests (+24 more)

### Community 5 - "CLI & Rendering"
Cohesion: 0.11
Nodes (38): cmd_extract(), cmd_inspect(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., _draw_dashed_rect() (+30 more)

### Community 6 - "Debug Trace Collector"
Cohesion: 0.07
Nodes (19): DebugTraceCollector, PathPrimitive, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+11 more)

### Community 7 - "Double-Door Assembly"
Cohesion: 0.14
Nodes (15): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, Candidate, A single_line_leaf door with no surrounding wall AND no nearby label         is, A single_line_leaf door with no wall but WITH a nearby door label         (e.g., Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing. (+7 more)

### Community 8 - "Sample Drawing Elements"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 9 - "Arc Swing Detection"
Cohesion: 0.17
Nodes (21): 3-point circle fit for chained-Bezier radius recovery, curve_arc garden-door partner pairing, DebugTraceCollector, _DoorSwing, PathPrimitive, _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes() (+13 more)

### Community 10 - "Chain-Extension Cap Trim"
Cohesion: 0.15
Nodes (14): Linear cap chain-extension trim, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end. (+6 more)

### Community 11 - "Double-Arc Split Tests"
Cohesion: 0.14
Nodes (14): _chain(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Polyline through the given points: segs from points[0]→points[1] etc., Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca, Halves of 3 segs each are below DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS.         Bail. (+6 more)

### Community 12 - "Cycle-Cap Pruning"
Cohesion: 0.15
Nodes (11): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t, A cycle of more than DOOR_POLYLINE_CYCLE_MAX_SEGMENTS segments         exceeds t (+3 more)

### Community 13 - "Project Docs & Pipeline Concepts"
Cohesion: 0.18
Nodes (13): CLAUDE.md project guide, Three-stage door detection (collect/pair/validate), Door Detection Tuning Guide, Known door false-positive patterns (bath fixture, window arc), Door heuristic constants tuning surface, pdfplumber cross-check + table extraction, Seven-stage per-page extraction pipeline, Polyline-arc detection micro-pipeline (+5 more)

### Community 14 - "Gemini Client"
Cohesion: 0.31
Nodes (12): Client, build_user_message(), call_gemini(), _candidate_to_dict(), encode_image_inline(), init_client(), parse_gemini_response(), Candidate (+4 more)

### Community 15 - "Arc Spur Pruning"
Cohesion: 0.15
Nodes (7): PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun, An 11-segment polyline arc has two degree-1 endpoints and no         junction —

### Community 16 - "Arc Pruning Design Docs"
Cohesion: 0.33
Nodes (6): Arc closed-cycle cap pruning, debug_trace.json schema + diagnostic playbook, Arc leaf-spur pruning, Polyline-Arc Spur Pruning Design, Polyline-Arc Spur Pruning Implementation Plan, DebugTraceCollector.record_polyline_component (debug/trace.py)

### Community 17 - "Hu Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 18 - "Codebase Restructure Docs"
Cohesion: 0.67
Nodes (4): Codebase restructure into packages, detection package acyclic dependency DAG, Codebase Restructure Design, Codebase Restructure Implementation Plan

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` → `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **9 isolated node(s):** `README`, `3-point circle fit for chained-Bezier radius recovery`, `Hu-moment door-shape matching`, `Architectural Working / Construction Drawing`, `Schedule (door/window/finish table)` (+4 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` and `Door (architectural element)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `Hu-Moment Shape Matching` to `Geometry Helpers`, `Door Detection Core`, `Door Leaf & BBox Primitives`, `PDF Extraction & Normalization`, `CLI & Rendering`, `Debug Trace Collector`, `Double-Door Assembly`, `Arc Swing Detection`, `Chain-Extension Cap Trim`, `Double-Arc Split Tests`, `Cycle-Cap Pruning`, `Arc Spur Pruning`?**
  _High betweenness centrality (0.287) - this node is a cross-community bridge._
- **Why does `DebugTraceCollector` connect `Debug Trace Collector` to `Geometry Helpers`, `Door Detection Core`, `Door Leaf & BBox Primitives`, `Hu-Moment Shape Matching`, `CLI & Rendering`, `Arc Swing Detection`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Geometry Helpers` to `Door Detection Core`, `Door Leaf & BBox Primitives`, `PDF Extraction & Normalization`, `CLI & Rendering`, `Debug Trace Collector`, `Double-Door Assembly`, `Gemini Client`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `PathPrimitive`) actually correct?**
  _`PathPrimitive` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `Candidate` (e.g. with `Client` and `BBox`) actually correct?**
  _`Candidate` has 50 INFERRED edges - model-reasoned connections that need verification._