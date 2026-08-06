# Graph Report - agent  (2026-08-06)

## Corpus Check
- 124 files · ~184,907 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2280 nodes · 5602 edges · 165 communities (100 shown, 65 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 302 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `44904c0b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Pipeline Orchestration & Extraction|Pipeline Orchestration & Extraction]]
- [[_COMMUNITY_Door Assembly & Heuristics Core|Door Assembly & Heuristics Core]]
- [[_COMMUNITY_Window Detection & Tests|Window Detection & Tests]]
- [[_COMMUNITY_Door Detection & Tests|Door Detection & Tests]]
- [[_COMMUNITY_Pipeline Design Concepts (docs)|Pipeline Design Concepts (docs)]]
- [[_COMMUNITY_Wall Cross-Validation|Wall Cross-Validation]]
- [[_COMMUNITY_Double-Door Merge & Gemini Client|Double-Door Merge & Gemini Client]]
- [[_COMMUNITY_Debug Trace Collector|Debug Trace Collector]]
- [[_COMMUNITY_Arc Detection Primitives|Arc Detection Primitives]]
- [[_COMMUNITY_Room Detection Tests|Room Detection Tests]]
- [[_COMMUNITY_Wall Network Construction & Tests|Wall Network Construction & Tests]]
- [[_COMMUNITY_Architectural PDF Domain (Sample Drawings)|Architectural PDF Domain (Sample Drawings)]]
- [[_COMMUNITY_Double-Arc Split Tests|Double-Arc Split Tests]]
- [[_COMMUNITY_Window Geometry Internals|Window Geometry Internals]]
- [[_COMMUNITY_Room Polygonization Internals|Room Polygonization Internals]]
- [[_COMMUNITY_Arc Cap-Trim Tests|Arc Cap-Trim Tests]]
- [[_COMMUNITY_Arc Cycle-Cap Pruning Tests|Arc Cycle-Cap Pruning Tests]]
- [[_COMMUNITY_arcs.py|arcs.py]]
- [[_COMMUNITY_windows.py|windows.py]]
- [[_COMMUNITY_Arc Spur-Pruning Tests|Arc Spur-Pruning Tests]]
- [[_COMMUNITY_Chained-Curve Swing Tests|Chained-Curve Swing Tests]]
- [[_COMMUNITY__fit_circle_3pt|_fit_circle_3pt]]
- [[_COMMUNITY_geometry.py|geometry.py]]
- [[_COMMUNITY_Hu-Moment Template Tool|Hu-Moment Template Tool]]
- [[_COMMUNITY_hline|hline]]
- [[_COMMUNITY_Extraction Strategy (project.md)|Extraction Strategy (project.md)]]
- [[_COMMUNITY_Spur-Pruning Design Spec|Spur-Pruning Design Spec]]
- [[_COMMUNITY_Package Restructure Design|Package Restructure Design]]
- [[_COMMUNITY_README stub|README stub]]
- [[_COMMUNITY_detect_windows|detect_windows]]
- [[_COMMUNITY_plumber.py|plumber.py]]
- [[_COMMUNITY__projected_interval|_projected_interval]]
- [[_COMMUNITY_Polyline-Arc Spur Pruning — Design|Polyline-Arc Spur Pruning — Design]]
- [[_COMMUNITY_renderer.py|renderer.py]]
- [[_COMMUNITY_Batch PDF Extraction Script Design|Batch PDF Extraction Script Design]]
- [[_COMMUNITY_batch_extract.py|batch_extract.py]]
- [[_COMMUNITY__collect_wall_faces|_collect_wall_faces]]
- [[_COMMUNITY_Codebase Restructure Packages + heuristics.py Split|Codebase Restructure: Packages + heuristics.py Split]]
- [[_COMMUNITY_Window Detection — Tuning Guide|Window Detection — Tuning Guide]]
- [[_COMMUNITY_renderer.py|renderer.py]]
- [[_COMMUNITY_150-DPI pixel-space normalization (SCALE)|150-DPI pixel-space normalization (SCALE)]]
- [[_COMMUNITY_detection package facade (run_heuristics)|detection package facade (run_heuristics)]]
- [[_COMMUNITY_Gemini Vertex AI client|Gemini Vertex AI client]]
- [[_COMMUNITY_merge_gemini_and_heuristics blending|merge_gemini_and_heuristics blending]]
- [[_COMMUNITY_Offline confidence floors (OFFLINE_MIN_CONFIDENCE)|Offline confidence floors (OFFLINE_MIN_CONFIDENCE)]]
- [[_COMMUNITY_Path explosion (one PathPrimitive per atomic item)|Path explosion (one PathPrimitive per atomic item)]]
- [[_COMMUNITY_CLAUDE.md Project Instructions|CLAUDE.md Project Instructions]]
- [[_COMMUNITY_Room detection (free-space components)|Room detection (free-space components)]]
- [[_COMMUNITY_Rooms are heuristic-only (bypass GeminimergeNMS)|Rooms are heuristic-only (bypass Gemini/merge/NMS)]]
- [[_COMMUNITY_Seven-stage per-page pipeline (run_extract)|Seven-stage per-page pipeline (run_extract)]]
- [[_COMMUNITY_Vector-first + Gemini-validation hypothesis|Vector-first + Gemini-validation hypothesis]]
- [[_COMMUNITY_Internal wall-centerline network (WallNetwork)|Internal wall-centerline network (WallNetwork)]]
- [[_COMMUNITY__trim_chain_extension_caps (linear cap trim)|_trim_chain_extension_caps (linear cap trim)]]
- [[_COMMUNITY_curve_arc_chain (3-point circle radius fit)|curve_arc_chain (3-point circle radius fit)]]
- [[_COMMUNITY__detect_curve_arc_double_partners (single-Bezier garden pair)|_detect_curve_arc_double_partners (single-Bezier garden pair)]]
- [[_COMMUNITY__prune_arc_cycle_caps (closed-cycle cap pruning)|_prune_arc_cycle_caps (closed-cycle cap pruning)]]
- [[_COMMUNITY_Debug-trace diagnostic playbook|Debug-trace diagnostic playbook]]
- [[_COMMUNITY_Door Detection Tuning Guide|Door Detection Tuning Guide]]
- [[_COMMUNITY_Door false-positive patterns (bath fixture  bay window)|Door false-positive patterns (bath fixture / bay window)]]
- [[_COMMUNITY__merge_double_door_assemblies (garden composite)|_merge_double_door_assemblies (garden composite)]]
- [[_COMMUNITY_Door offline confidence floor (0.55)|Door offline confidence floor (0.55)]]
- [[_COMMUNITY__pair_door_assemblies (swing-leaf pairing)|_pair_door_assemblies (swing-leaf pairing)]]
- [[_COMMUNITY__detect_polyline_arc_bboxes ordered micro-pipeline|_detect_polyline_arc_bboxes ordered micro-pipeline]]
- [[_COMMUNITY__split_double_arc garden-door split|_split_double_arc garden-door split]]
- [[_COMMUNITY__prune_arc_spurs (Y-junction spur pruning)|_prune_arc_spurs (Y-junction spur pruning)]]
- [[_COMMUNITY_Six door-swing topologies taxonomy|Six door-swing topologies taxonomy]]
- [[_COMMUNITY_Walk-direction tangent break orientation pitfall|Walk-direction tangent break orientation pitfall]]
- [[_COMMUNITY_Wall cross-validation penalty (_cross_validate)|Wall cross-validation penalty (_cross_validate)]]
- [[_COMMUNITY_Batch Extraction Design Spec|Batch Extraction Design Spec]]
- [[_COMMUNITY_Interactive detection-option prompts|Interactive detection-option prompts]]
- [[_COMMUNITY_ProcessPoolExecutor parallel batch execution|ProcessPoolExecutor parallel batch execution]]
- [[_COMMUNITY__band_interior_clutter gate|_band_interior_clutter gate]]
- [[_COMMUNITY_Cap-anchored window signature (v2)|Cap-anchored window signature (v2)]]
- [[_COMMUNITY_Ambiguous windows deferred to Gemini (w17w18w26)|Ambiguous windows deferred to Gemini (w17/w18/w26)]]
- [[_COMMUNITY_detect_windows pipeline|detect_windows pipeline]]
- [[_COMMUNITY_Window detector v0v1v2 evolution|Window detector v0/v1/v2 evolution]]
- [[_COMMUNITY_Window Detection Tuning Guide|Window Detection Tuning Guide]]
- [[_COMMUNITY__resolve_door_window_conflicts (door-overlap exclusion)|_resolve_door_window_conflicts (door-overlap exclusion)]]
- [[_COMMUNITY__find_openings (facing cap pairing)|_find_openings (facing cap pairing)]]
- [[_COMMUNITY_Oriented band vs bbox (diagonal-window preservation)|Oriented band vs bbox (diagonal-window preservation)]]
- [[_COMMUNITY__spanning_glazing  _tight_band|_spanning_glazing / _tight_band]]
- [[_COMMUNITY_2-pane jamb gate|2-pane jamb gate]]
- [[_COMMUNITY_project.md original spec|project.md original spec]]
- [[_COMMUNITY_PyMuPDF primary extractor|PyMuPDF primary extractor]]
- [[_COMMUNITY_google-genai dependency|google-genai dependency]]
- [[_COMMUNITY_pdfplumber dependency|pdfplumber dependency]]
- [[_COMMUNITY_PyMuPDF dependency|PyMuPDF dependency]]
- [[_COMMUNITY_shapely dependency|shapely dependency]]
- [[_COMMUNITY_Codebase Restructure Design|Codebase Restructure Design]]
- [[_COMMUNITY_Arc leaf-spur pruning|Arc leaf-spur pruning]]
- [[_COMMUNITY_Polyline-Arc Spur Pruning Design|Polyline-Arc Spur Pruning Design]]
- [[_COMMUNITY_Vector-first + Gemini-validation pipeline|Vector-first + Gemini-validation pipeline]]
- [[_COMMUNITY_vline|vline]]
- [[_COMMUNITY_wall_band_h|wall_band_h]]
- [[_COMMUNITY_TestWindowInteriorClutter|TestWindowInteriorClutter]]
- [[_COMMUNITY_TestMarkerRings|TestMarkerRings]]
- [[_COMMUNITY_DoorV2OpeningCheckTests|DoorV2OpeningCheckTests]]
- [[_COMMUNITY_PathPrimitive|PathPrimitive]]
- [[_COMMUNITY_detect_doors|detect_doors]]
- [[_COMMUNITY_PageData|PageData]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_vline|vline]]
- [[_COMMUNITY__bridge_white_runs|_bridge_white_runs]]
- [[_COMMUNITY__find_openings|_find_openings]]
- [[_COMMUNITY_EntranceDoorTests|EntranceDoorTests]]
- [[_COMMUNITY_app.py|app.py]]
- [[_COMMUNITY_RotatedPdfTestCase|RotatedPdfTestCase]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_TestAnnotationPenBarriers|TestAnnotationPenBarriers]]
- [[_COMMUNITY__collect_wall_faces|_collect_wall_faces]]
- [[_COMMUNITY_Floor-plan region filtering|Floor-plan region filtering]]
- [[_COMMUNITY_TestWindowInteriorClutter|TestWindowInteriorClutter]]
- [[_COMMUNITY_qualifying_clip_rects|qualifying_clip_rects]]
- [[_COMMUNITY_qualifying_clip_rects|qualifying_clip_rects]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_SplitDoubleArcTests|SplitDoubleArcTests]]
- [[_COMMUNITY_test_door_assembly.py|test_door_assembly.py]]
- [[_COMMUNITY_batch_extract.py|batch_extract.py]]
- [[_COMMUNITY_2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)|2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)]]
- [[_COMMUNITY_framed_triple_window|framed_triple_window]]
- [[_COMMUNITY__segments_min_distance|_segments_min_distance]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_2026-08-05 — detect_windows performance on giant sheets (handoff)|2026-08-05 — detect_windows performance on giant sheets (handoff)]]
- [[_COMMUNITY_segmenter.py|segmenter.py]]
- [[_COMMUNITY_EntranceDoorTests|EntranceDoorTests]]
- [[_COMMUNITY_test_layout_segmenter.py|test_layout_segmenter.py]]
- [[_COMMUNITY_TestProfileHelpers|TestProfileHelpers]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_TestWindowArbitraryAngle|TestWindowArbitraryAngle]]
- [[_COMMUNITY_DoorAssemblyTests|DoorAssemblyTests]]
- [[_COMMUNITY_client.py|client.py]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY__frame_axes|_frame_axes]]
- [[_COMMUNITY__merge_mullion_chains|_merge_mullion_chains]]
- [[_COMMUNITY_ShaMismatchAgainstTruthTests|ShaMismatchAgainstTruthTests]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Regression Corpus — Design|Regression Corpus — Design]]
- [[_COMMUNITY_wall_band_v|wall_band_v]]
- [[_COMMUNITY_Regression Testing — Working Guide|Regression Testing — Working Guide]]
- [[_COMMUNITY_test_extraction_transform.py|test_extraction_transform.py]]
- [[_COMMUNITY_Detection Review Tooling V1 — Implementation Plan|Detection Review Tooling V1 — Implementation Plan]]
- [[_COMMUNITY_RunDirTests|RunDirTests]]
- [[_COMMUNITY_count_paths_in|count_paths_in]]
- [[_COMMUNITY_TestExtractPageFrame|TestExtractPageFrame]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY_normalize_bbox|normalize_bbox]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_apply_classification|apply_classification]]
- [[_COMMUNITY_MANIFEST.json|MANIFEST.json]]
- [[_COMMUNITY_vline|vline]]
- [[_COMMUNITY_TestRequestShape|TestRequestShape]]
- [[_COMMUNITY_SweepSlugsArgumentTests|SweepSlugsArgumentTests]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_TestFloorPlansRegression|TestFloorPlansRegression]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 198 edges
2. `Candidate` - 107 edges
3. `PageData` - 98 edges
4. `TextSpan` - 96 edges
5. `detect_wall_network()` - 70 edges
6. `Region` - 61 edges
7. `detect_windows()` - 52 edges
8. `TruthItem` - 49 edges
9. `detect_doors()` - 45 edges
10. `rooms_for()` - 45 edges

## Surprising Connections (you probably didn't know these)
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` --semantically_similar_to--> `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [INFERRED] [semantically similar]
  5-1133-WD03.pdf → floor-plans.pdf
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` --references--> `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf → 5-1133-WD03.pdf
- `DebugTraceCollector` --uses--> `PathPrimitive`  [INFERRED]
  debug/trace.py → models.py
- `_SlidePanel` --uses--> `DebugTraceCollector`  [INFERRED]
  detection/doors/sliding.py → debug/trace.py
- `PageRegionResult` --uses--> `DebugTraceCollector`  [INFERRED]
  pipeline.py → debug/trace.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **5-1133-WD03 proposed lower ground floor: walls, windows, doors** — 5_1133_wd03, 5_1133_wd03_cavity_walls, 5_1133_wd03_windows, 5_1133_wd03_folding_sliding_doors [EXTRACTED 1.00]
- **floor-plans proposed ground & first floor plans with rooms and rooflights** — floor_plans, floor_plans_ground_floor, floor_plans_first_floor, floor_plans_velux [EXTRACTED 1.00]

## Communities (165 total, 65 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive., Record the swing-anchored single-line leaf search outcome.          `result` is (+5 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.18
Nodes (15): cache_file(), load_regions(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a segmentation's geometry — the boxes and where they     came f, region_geometry_hash(), regions_from_dicts(), regions_to_dicts() (+7 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.15
Nodes (12): diagonal_window(), path(), A real window's glazing band is clear glass — nothing between the panes.     An, Control: the bare 2-line capped opening with an empty band interior is         s, 5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two         wall, Insulation hatch drawn with pure line segments (no re/qu/c): the         diagona, Decorations OUTSIDE the pane band (here, well beyond a cap along the         run, Regression (the bug this gate first introduced): a 45-deg window must         no (+4 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.07
Nodes (27): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, detect_doors(), _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli (+19 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.11
Nodes (25): _cross_validate(), True when a wall FACE line runs unbroken through the bbox span.      A real wind, Validate doors/windows against the wall-centerline network.      Doors keep the, _wall_runs_through(), One wall centerline segment (pixel space, y-down)., One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline. (+17 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.13
Nodes (15): Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, _split_double_arc(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca (+7 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.09
Nodes (58): _nearest_pair_distance(), _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg() (+50 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.20
Nodes (12): build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline, One API call for the whole page. Returns classified regions + warnings. (+4 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.08
Nodes (26): door_candidate(), fill_ring(), hline(), path(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, Rect room with a 45px doorway gap in the top wall (240..285)., Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi (+18 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.11
Nodes (20): block(), one_blob_page(), page_with_a_dropped_strip(), parse_failing_classifier(), raster_page(), Region resolution rules (pipeline.resolve_page_regions).  A stub classifier stan, Filtering only pays if the regions hold the sheet's ink., two_blob_page plus a 52px-tall strip of real drawing.      It is its own leaf, b (+12 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.22
Nodes (18): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), extract_tables(), _normalize_bbox_plumber() (+10 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.08
Nodes (28): detect(), EndToEndTests, fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack() (+20 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.12
Nodes (27): _component_indices(), _dedupe_door_components(), door_open_leaf_path_indices(), Prefer the strongest door when two candidates use the same primitives., Path indices of swing doors' OPEN leaf linework.      A swing door's leaf is dra, _bbox_area(), _bbox_center(), detect_labels() (+19 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.16
Nodes (13): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, _chain(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t (+5 more)

### Community 17 - "arcs.py"
Cohesion: 0.11
Nodes (19): _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests (+11 more)

### Community 18 - "windows.py"
Cohesion: 0.06
Nodes (21): address_match(), Shared address-detection patterns for corpus hygiene checks.  Two callers share, The matched address-like substring in `text`, or None., AdoptTests, make_pdf(), NextSlugTests, Path, Adopting a new sheet into the corpus. (+13 more)

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.16
Nodes (13): Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO (+5 more)

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (43): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.10 Folding/bifold doors — no arc (`detection/doors/folding.py`), 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`) (+35 more)

### Community 21 - "_fit_circle_3pt"
Cohesion: 0.15
Nodes (16): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _draw_regions(), _load_font(), BBox (+8 more)

### Community 22 - "geometry.py"
Cohesion: 0.15
Nodes (31): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), _is_arc_like(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some (+23 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.14
Nodes (16): _leaf_ink_indices(), _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., A single-swing candidate's leaf linework, pinned by its evidence:     leaf line, DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing. (+8 more)

### Community 31 - "README stub"
Cohesion: 0.18
Nodes (10): Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional), Inspect — terminal summary only, Output layout, Requirements, Setup (+2 more)

### Community 34 - "detect_windows"
Cohesion: 0.19
Nodes (10): paving_field(), Running-bond paving: continuous course lines, staggered joint lines.      Mirror, Four wall bands forming a closed rectangular room (outer faces at the     given, Striped fields (paving bonds, tile fields, treads) are not walls., Stroke-color pen identity: pairing, faint-ink demotion, dimension     chains, an, rect_room(), TestLatticeDemotion, TestPenGates (+2 more)

### Community 35 - "plumber.py"
Cohesion: 0.18
Nodes (9): _prune_arc_spurs(), Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun (+1 more)

### Community 36 - "_projected_interval"
Cohesion: 0.20
Nodes (9): filter_page_data(), A copy of page_data holding only primitives whose bbox centre falls in     one o, ImageRef, path(), Region filtering tests (layout/filter.py)., region(), span(), TestFilterPageData (+1 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.25
Nodes (9): build_ink_map(), is_page_spanning(), True for sheet furniture: a border rule or column divider that runs the     leng, page(), path(), Ink occupancy map tests (layout/occupancy.py)., span(), TestBuildInkMap (+1 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.42
Nodes (5): PageTruth, evaluate_page(), Score one page's entities against its three verdict lists., entity(), EvaluatePageTests

### Community 41 - "_collect_wall_faces"
Cohesion: 0.18
Nodes (8): BBox, qualifying_clip_rects_from_boxes(), Keep only clips that look like real drawing boundaries.      Measured on the sam, dot(), page_with(), Clip-rect gating tests (layout/clips.py)., TestClipCutPositions, TestClipGating

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.17
Nodes (11): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target) (+3 more)

### Community 44 - "renderer.py"
Cohesion: 0.16
Nodes (20): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., Document, render_page_png(), assigned_path_fraction(), Share of the page's paths that any region would keep.      Deliberately the same, Entity (+12 more)

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.15
Nodes (15): Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), Candidate, DoorEvidencePropagationTests, Verify Step 4 — door evidence keys land in Entity.attributes in offline mode., TestDiagonalWindowSeal, BBox, Windows are drawn at any angle, not just axis-aligned. The cap-anchored     mode (+7 more)

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (9): _door_attribute_overlay(), finalize_candidates(), Promote candidates to entities, applying the offline confidence floors.      Gem, Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, assembly_type must reach Entity.attributes through the pipeline passthrough., cand(), finalize_candidates applies the offline confidence floors unconditionally., TestFinalizeCandidates (+1 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.17
Nodes (10): hline(), horizontal_window(), A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two, 5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is         fa, Three parallel lines with no perpendicular end-caps (e.g. a run of         dimen, Three parallel lines spaced far apart (e.g. stair treads) exceed the         gla, A W1-style horizontal window: 3 tight horizontal glazing lines centered     in a, A W4-style vertical window: 3 tight vertical glazing lines closed by two     hor (+2 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 103 - "PathPrimitive"
Cohesion: 0.19
Nodes (12): pending(), Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk., ReviewBlocked, SweepOutputMissing, SweepOutputStale (+4 more)

### Community 104 - "detect_doors"
Cohesion: 0.18
Nodes (21): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+13 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.17
Nodes (12): SheetTruth, _labeled_but_unreviewed(), True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages, score_sheet(), entity(), LabeledFlagTests, Sweep correctness that does not require running the real pipeline.  `regression. (+4 more)

### Community 107 - "vline"
Cohesion: 0.15
Nodes (16): _bbox_expanded(), _bbox_union(), _bboxes_overlap(), _point_in_bbox(), BBox, Minimum distance between two line segments., _segments_min_distance(), BBox (+8 more)

### Community 108 - "_bridge_white_runs"
Cohesion: 0.15
Nodes (25): Path, Path to a downloaded sheet, or None when it is not on disk., sha256_of(), sheet_entry(), sheet_path(), load_truth(), _check_provenance(), _ordered() (+17 more)

### Community 109 - "_find_openings"
Cohesion: 0.10
Nodes (26): _interval_overlap(), _area(), _dedupe_by_perp(), _dedupe_openings(), _facing_cap_pairs(), _find_openings(), _glaze_index(), BBox (+18 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.08
Nodes (29): _building_masses(), detect_rooms(), _door_plugs(), _folding_chain_gap_plug(), _free_space_components(), _open_leaf_edges(), Room detection: rooms are the connected free-space components between walls.  Ea, Fraction of a bbox area covered by the text spans lying over it. (+21 more)

### Community 111 - "app.py"
Cohesion: 0.06
Nodes (65): _line_angle_deg(), _line_length(), _perpendicular_spacing(), _project_onto_axis(), _projected_interval(), Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars., Scalar projection of p onto the unit axis (dx, dy) from origin., _band_has_wall_material() (+57 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.18
Nodes (11): Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door() (+3 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.42
Nodes (5): block(), cut(), page(), A solid-ish blob: a horizontal line every 4px so every bin row is inked., TestXYCut

### Community 115 - "_collect_wall_faces"
Cohesion: 0.17
Nodes (14): _bridge_white_runs(), _equivalent_sides(), _FillRing, _rate_fill_classes(), (short, long) of the rectangle with this polygon's area and perimeter.      The, A closed same-fill polygon reconstructed from exploded `l` items., Annotation arrowhead: a tiny filled triangle or concave dart.          Walls are, Classify each fill color as wall material (True) or furniture (False).      Vect (+6 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (9): _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, ExitCodeTests, Report shaping and exit codes.  The sweep itself (which runs the pipeline over r, RenderTests (+1 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.24
Nodes (5): DoorAssemblyTests, _far_wall_network(), Minimal non-empty wall network located far from the doors under test., A single_line_leaf door with no surrounding wall AND no nearby label         is, A single_line_leaf door with no wall but WITH a nearby door label         (e.g.

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.31
Nodes (5): qualifying_clip_rects(), Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, segment(), TestGoldenSegmentation

### Community 120 - "TestNetworkQueries"
Cohesion: 0.16
Nodes (12): load_manifest(), manifest_sheets(), Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, The committed manifest, or an empty corpus when it is absent., Flip a manifest entry's `labeled` flag and write the manifest back.      `labele, set_labeled(), CheckCorpusTests, The corpus verifier classifies each manifest sheet against the disk. (+4 more)

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.18
Nodes (11): TruthItem, Regression corpus: fixture resolution, ground truth, matching, and the sweep., iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity() (+3 more)

### Community 123 - "batch_extract.py"
Cohesion: 0.13
Nodes (15): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive)., Build the extract argv for a single PDF (no shell involved). (+7 more)

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.25
Nodes (5): framed_triple_window(), quad(), 5-1133 W8: a three-light frame tagged with a single label. Two full-span     rai, Collinear segments merge only across a gap a mullion block occupies —         th, A block with an X drawn through it is a post/column symbol (the         5-1133 b

### Community 126 - "_segments_min_distance"
Cohesion: 0.52
Nodes (6): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., Namespace

### Community 127 - "File Structure"
Cohesion: 0.22
Nodes (8): File Structure, Polyline-Arc Spur Pruning Implementation Plan, Self-review notes, Task 1: Add `_prune_arc_spurs` skeleton + clean-arc and pure-cycle tests, Task 2: Implement Y-junction spur pruning, Task 3: Cover multi-spur, oversized, and floor cases, Task 4: Extend `DebugTraceCollector.record_polyline_component` with the two optional kwargs, Task 5: Wire `_prune_arc_spurs` into `_detect_polyline_arc_bboxes`

### Community 128 - "2026-08-05 — detect_windows performance on giant sheets (handoff)"
Cohesion: 0.25
Nodes (7): 2026-08-05 — detect_windows performance on giant sheets (handoff), Constraints and gotchas, Optimization plan (pruning-only, output-identical), Reproduction recipes (self-contained — scratchpad scripts die with the session), Verification gates (all must pass, in this order), Where the time goes, Why this task exists (and why it was deferred)

### Community 129 - "segmenter.py"
Cohesion: 0.13
Nodes (24): clip_cut_positions(), Native PDF clip rects, used as extra cut hints for the segmenter.  Clip rects ar, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi, Tunable constants for page segmentation.  Values are measured, not guessed — see, Page segmentation: split a sheet into its constituent drawings., InkMap, Binary ink occupancy map over a page, used to find whitespace gutters., bins[row][col] is 1 where drawn ink falls, 0 elsewhere. (+16 more)

### Community 130 - "EntranceDoorTests"
Cohesion: 0.19
Nodes (6): hline(), path(), Partition wall in the joinery pen: two hairline faces with diagonal     hatch st, TestFaceCollection, TestWeakFacePairs, weak_hatched_band_h()

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.24
Nodes (5): Split a page into drawing regions. Returns [] for a page with no vector     ink, segment_page(), PageData, TestSegmentPage, TestStageTimingLogs

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.17
Nodes (8): Path, door_0007 -> d7. Unparseable ids are returned unchanged., Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, short_id(), write_review_overlays(), Review images: one per page per entity type, ids stamped on., ReviewOverlayTests, ShortIdTests

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.11
Nodes (7): TestCase, Path, Skip helper for tests that need a real corpus sheet.  Corpus knowledge lives in, Return the sheet's path, or skip the test with an actionable message., require_sheet(), LoaderTests, The corpus loader resolves slugs against the committed manifest.  Every test bui

### Community 136 - "client.py"
Cohesion: 0.18
Nodes (16): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), Path, The user's per-sheet verdicts, and how they are read.  One file per sheet under (+8 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.25
Nodes (9): cache_key(), page_content_hash(), Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Cache identity: the page's content AND the segmentation of it.      Region bboxe, page(), path(), Region bboxes ARE the filtering contract, and entries are permanent, so a     ch, TestContentHash (+1 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "_merge_mullion_chains"
Cohesion: 0.14
Nodes (15): _door_fallback_candidate(), _find_threshold_line(), _pair_door_assemblies(), BBox, Find an entrance-door threshold/sill line parallel to the leaf long axis.      T, Parse an evidence bbox value defensively; return None on any invalid shape., _safe_bbox(), _find_anchored_leaf_line() (+7 more)

### Community 140 - "ShaMismatchAgainstTruthTests"
Cohesion: 0.18
Nodes (4): LabeledFlagSweepIntegrationTests, End-to-end through sweep() for the two failing cases -- both exit via     `conti, Fix: an operator who pastes a fresh hash into the manifest instead of     adopti, ShaMismatchAgainstTruthTests

### Community 141 - "File Structure"
Cohesion: 0.12
Nodes (15): File Structure, Global Constraints, Phase 3 — corpus labeling (not a task), Regression Corpus Implementation Plan, Slug Assignment (authoritative — used by Tasks 2 and 3), Task 10: Seed s01 ground truth and document the labeling loop, Task 1: Corpus loader, Task 2: Migrate the sheets into the fixtures layout (+7 more)

### Community 142 - "Regression Corpus — Design"
Cohesion: 0.12
Nodes (15): Adoption — `tools/add_sheet.py`, Architecture, Constraints, Fixture layout, Ground truth, Naming, Non-goals, Phasing (+7 more)

### Community 143 - "wall_band_v"
Cohesion: 0.18
Nodes (8): _clip_cut(), Strip empty margins; returns absolute (start, end) bin indices., Widest fully-empty internal run of at least min_bins. Leading and     trailing r, First clip edge lying strictly inside the span with ink on both sides.      An e, _trim(), _widest_gap(), Recursive XY-cut tests (layout/segmenter.py)., TestProfileHelpers

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.12
Nodes (16): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+8 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.19
Nodes (8): The uniform scale factor of a rotate+scale transform. hypot is exact for     the, transform_scale(), Extraction puts geometry in the same frame as the declared page size.  page.get_, A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestPageTransform, write_rotated_pdf()

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 148 - "count_paths_in"
Cohesion: 0.21
Nodes (8): detect_wall_network(), _is_light_pen(), Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., Horizontal wall drawn as two stroked faces., TestCenterlines, TestNetworkAssembly, wall_band_h()

### Community 150 - "fill_ring"
Cohesion: 0.18
Nodes (10): MainExceptionIsolationTests, tools/review.py's main(): one sheet's unexpected failure must not kill the walk, _centre(), _choice(), main(), _pick(), Walk one sheet's pending detections. Returns how many were recorded.      Handle, Multi-select over entities; returns the chosen entity ids.      Uses `inquirer.c (+2 more)

### Community 151 - "normalize_bbox"
Cohesion: 0.50
Nodes (3): Client, init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-

### Community 153 - "fill_ring"
Cohesion: 0.20
Nodes (7): fill_ring(), marker_ring(), Closed filled rectangle exploded into 4 chained `l` items., Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFillClassRating, TestMarkerRings

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.20
Nodes (6): The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si, 5-1133 window_0016/0017: a step in a solid-filled wall block — the         step', floor-plans true windows draw a narrow double glazing line (panes         1.75px, 5-1133 window_0022 (real diagonal 2-pane window): its band sits at         the c, TestWindowTightPairInterior

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.14
Nodes (13): _band_interior_clutter(), _cap_orientation_frames(), _clutter_grid(), detect_windows(), _frame_axes(), _merge_mullion_chains(), Caps grouped by direction into overlapping frames, each ``(center, caps)``., Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C (+5 more)

### Community 157 - "apply_classification"
Cohesion: 0.37
Nodes (5): apply_classification(), Apply a classification response to a region list.      Returns new Region object, region(), response(), TestApplyClassification

### Community 159 - "vline"
Cohesion: 0.29
Nodes (5): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, A toilet/sink fixture is a hatch of stacked short segments plus         collinea, TestWindow51133Topology, vline()

### Community 160 - "TestRequestShape"
Cohesion: 0.25
Nodes (4): _CapturingClient, Stands in for genai.Client, recording the config it was called with., The response must be schema-constrained at decode time.      Plain JSON mode doe, TestRequestShape

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **303 isolated node(s):** `storage`, `sheets`, `Project purpose`, `Algorithm reference`, `Commands` (+298 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `Debug Trace Collector` to `Pipeline Orchestration & Extraction`, `segmenter.py`, `Door Assembly & Heuristics Core`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `EntranceDoorTests`, `Window Detection & Tests`, `_dedupe_openings`, `Wall Network Construction & Tests`, `_merge_mullion_chains`, `Room Detection Tests`, `Room Polygonization Internals`, `Arc Cap-Trim Tests`, `Arc Cycle-Cap Pruning Tests`, `arcs.py`, `wall_band_v`, `Arc Spur-Pruning Tests`, `count_paths_in`, `geometry.py`, `hline`, `fill_ring`, `TestWindowTightPairInterior`, `TestBlindWindowPocket`, `vline`, `detect_windows`, `plumber.py`, `_projected_interval`, `TestNetworkQueries`, `renderer.py`, `TestThickMaterialPairs`, `TestFloorPlansRegression`, `_collect_wall_faces`, `wall_band_h`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `vline`, `_find_openings`, `EntranceDoorTests`, `app.py`, `TestAnnotationPenBarriers`, `_collect_wall_faces`, `qualifying_clip_rects`, `framed_triple_window`?**
  _High betweenness centrality (0.227) - this node is a cross-community bridge._
- **Why does `Candidate` connect `wall_band_h` to `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Debug Trace Collector`, `Room Detection Tests`, `_merge_mullion_chains`, `Arc Cap-Trim Tests`, `_fit_circle_3pt`, `geometry.py`, `hline`, `TestWindowTightPairInterior`, `TestBlindWindowPocket`, `vline`, `TestFloorPlansRegression`, `renderer.py`, `TestWindowInteriorClutter`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `_find_openings`, `EntranceDoorTests`, `qualifying_clip_rects`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `Arc Cap-Trim Tests` to `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `_merge_mullion_chains`, `wall_band_v`, `arcs.py`, `count_paths_in`, `geometry.py`, `hline`, `apply_classification`, `TestRequestShape`, `_projected_interval`, `renderer.py`, `renderer.py`, `wall_band_h`, `DoorV2OpeningCheckTests`, `detect_doors`, `EntranceDoorTests`, `app.py`, `TestAnnotationPenBarriers`, `_collect_wall_faces`, `qualifying_clip_rects`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 85 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 85 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Candidate` (e.g. with `_SlidePanel` and `PageRegionResult`) actually correct?**
  _`Candidate` has 40 INFERRED edges - model-reasoned connections that need verification._