# Graph Report - agent  (2026-08-26)

## Corpus Check
- 220 files · ~351,014 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3776 nodes · 9626 edges · 216 communities (146 shown, 70 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 702 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2485686`
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
- [[_COMMUNITY_client.py|client.py]]
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
- [[_COMMUNITY_TestAnnotationPenBarriers|TestAnnotationPenBarriers]]
- [[_COMMUNITY_normalize_bbox|normalize_bbox]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_apply_classification|apply_classification]]
- [[_COMMUNITY_MANIFEST.json|MANIFEST.json]]
- [[_COMMUNITY__segments_min_distance|_segments_min_distance]]
- [[_COMMUNITY_TestRequestShape|TestRequestShape]]
- [[_COMMUNITY_SweepSlugsArgumentTests|SweepSlugsArgumentTests]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY__double_arc|_double_arc]]
- [[_COMMUNITY_SplitDoubleArcTests|SplitDoubleArcTests]]
- [[_COMMUNITY_ScaleInfo|ScaleInfo]]
- [[_COMMUNITY_Architecture|Architecture]]
- [[_COMMUNITY_TestSwingHingePlugRestriction|TestSwingHingePlugRestriction]]
- [[_COMMUNITY_scales_in_text|scales_in_text]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_transform_scale|transform_scale]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
- [[_COMMUNITY_DoorV2OpeningCheckTests|DoorV2OpeningCheckTests]]
- [[_COMMUNITY_MainExceptionIsolationTests|MainExceptionIsolationTests]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY__FillRing|_FillRing]]
- [[_COMMUNITY_cluster_denominators|cluster_denominators]]
- [[_COMMUNITY_Step 5 — Per-scale-group detection for mixed-scale pages|Step 5 — Per-scale-group detection for mixed-scale pages]]
- [[_COMMUNITY_swing_door|swing_door]]
- [[_COMMUNITY_Step 1 — Widen the door Bezier aspect gate|Step 1 — Widen the door Bezier aspect gate]]
- [[_COMMUNITY_Step 2 — Retune the window span-overshoot gate (paper-space FP kill)|Step 2 — Retune the window span-overshoot gate (paper-space FP kill)]]
- [[_COMMUNITY_Step 3 — Diagnose s15's 82 false positives (read-only)|Step 3 — Diagnose s15's 82 false positives (read-only)]]
- [[_COMMUNITY_Step 4 — Recall audit on the 1100 sheets (misses are invisible to ground truth)|Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth)]]
- [[_COMMUNITY_TestXYCut|TestXYCut]]
- [[_COMMUNITY_TestPlumberTableBBox|TestPlumberTableBBox]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_TestCrossWindowToleranceUnscaled|TestCrossWindowToleranceUnscaled]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_Handoff W-gate recalibration (the proper fix behind `fixmeasured-scale-detection-factor`)|Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)]]
- [[_COMMUNITY_denominator_from_c|denominator_from_c]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY__is_light_pen|_is_light_pen]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_File structure|File structure]]
- [[_COMMUNITY_SplitDoubleArcTests|SplitDoubleArcTests]]
- [[_COMMUNITY__scan_striped_runs|_scan_striped_runs]]
- [[_COMMUNITY_PruneUnreadPageOutputTests|PruneUnreadPageOutputTests]]
- [[_COMMUNITY_parse_answer|parse_answer]]
- [[_COMMUNITY_check_corpus|check_corpus]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_TestFarSidePairs|TestFarSidePairs]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_MainExceptionIsolationTests|MainExceptionIsolationTests]]
- [[_COMMUNITY_TestWindowSpanOvershootRetune|TestWindowSpanOvershootRetune]]
- [[_COMMUNITY_TestRenderPageSvg|TestRenderPageSvg]]
- [[_COMMUNITY_TestMinWidthNegativeControl|TestMinWidthNegativeControl]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 257 edges
2. `PageData` - 164 edges
3. `Candidate` - 161 edges
4. `TextSpan` - 141 edges
5. `Region` - 111 edges
6. `detect_wall_network()` - 92 edges
7. `PageScales` - 90 edges
8. `ScaleInfo` - 86 edges
9. `Entity` - 70 edges
10. `detect_windows()` - 67 edges

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

## Communities (216 total, 70 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.10
Nodes (40): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), _draw_regions(), _load_font(), BBox, Image (+32 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.12
Nodes (23): cache_file(), cache_key(), load_labels(), Path, On-disk cache of room labels, keyed by page content AND the room polygons the la, Stable digest of the room outlines a labelling was made against.      A cached l, room_geometry_hash(), save_labels() (+15 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.11
Nodes (15): detect_windows(), _frame_axes(), _merge_mullion_chains(), Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C, Join collinear glazing segments across mullion blocks into logical panes.      A, Detect windows as capped openings bridged by a parallel glazing band.      For e, The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si (+7 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.07
Nodes (35): _building_masses(), detect_rooms(), _door_plugs(), _drop_window_exterior_sides(), _folding_chain_gap_plug(), _free_space_components(), _is_wall_recess(), _open_leaf_edges() (+27 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.09
Nodes (27): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor, WallFace, WallNetwork (+19 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.20
Nodes (7): _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, Halves of 3 segs each are below DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS.         Bail., A component with a degree-3+ junction isn't a 2-leaf simple         chain. The d, Two quarter arcs sharing endpoint (0, 0) with antiparallel tangents.      Models, _seg()

### Community 7 - "Debug Trace Collector"
Cohesion: 0.11
Nodes (19): _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests (+11 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.07
Nodes (21): CrossGates, World-space cross-validation gates, pre-multiplied by the factor.      Only the, prim(), _production_cross_gates_unscaled_usages(), _production_door_gates_unscaled_usages(), quarter_bezier(), Scale-factor behavior of the door gates: identity at 1.0, linear at 0.5.  A "fai, Scan detection/**/*.py for PRODUCTION (non-import, non-comment) uses     of the (+13 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.12
Nodes (17): _leaf_ink_indices(), _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., A single-swing candidate's leaf linework, pinned by its evidence:     leaf line, DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing. (+9 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.05
Nodes (43): apply_classification(), build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+35 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.10
Nodes (31): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+23 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.05
Nodes (43): detect(), EndToEndTests, fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack() (+35 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.13
Nodes (14): SheetTruth, _labeled_but_unreviewed(), True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages, score_sheet(), entity(), LabeledFlagTests, Sweep correctness that does not require running the real pipeline.  `regression. (+6 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.20
Nodes (8): One fixture per paper-space family (spec §Testing). Each fails if its     named, TestPaperInvariance, hline(), A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two, 5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is         fa, Three parallel lines spaced far apart (e.g. stair treads) exceed the         gla, A toilet/sink fixture is a hatch of stacked short segments plus         collinea, vline()

### Community 18 - "windows.py"
Cohesion: 0.06
Nodes (21): address_match(), Shared address-detection patterns for corpus hygiene checks.  Two callers share, The matched address-like substring in `text`, or None., AdoptTests, make_pdf(), NextSlugTests, Path, Adopting a new sheet into the corpus. (+13 more)

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.10
Nodes (20): 1. The organising rule — the INVERSE of doors, 1. `WindowGates` (mirrors `WallGates`/`RoomGates`/`DoorGates`), 2. Retention vetoes — the confirmed extremes kill every W-candidacy but one, 2. Threading, 3. Classification (frozen; full table to findings §4e), 3. The variant matrix — every verdict exercised end-to-end, 4. Hidden-constant audits (both §4b blind-spot classes), 4. Shrunk-world on s01/s02 — read for what it can and cannot say (+12 more)

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (43): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.10 Folding/bifold doors — no arc (`detection/doors/folding.py`), 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`) (+35 more)

### Community 21 - "_fit_circle_3pt"
Cohesion: 0.07
Nodes (30): The per-region scale table printed after each page., scale_table(), _effective_denominator(), _gate_denominator(), One detection factor per page: which scale governs the ink detection sees.  Dete, Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY., The denominator allowed to drive gate scaling, or None to abstain.      Only a D, Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan. (+22 more)

### Community 22 - "geometry.py"
Cohesion: 0.07
Nodes (27): apply_labels(), build_request_text(), collect_room_spans(), is_grounded(), is_noise_span(), label_rooms(), Polygon, Ask Gemini for the name written inside each detected room.  One text-only call p (+19 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.08
Nodes (32): _component_indices(), _dedupe_door_components(), door_open_leaf_path_indices(), Prefer the strongest door when two candidates use the same primitives., Path indices of swing doors' OPEN leaf linework.      A swing door's leaf is dra, _bbox_area(), detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re (+24 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.16
Nodes (9): paving_field(), Running-bond paving: continuous course lines, staggered joint lines.      Mirror, Four wall bands forming a closed rectangular room (outer faces at the     given, Striped fields (paving bonds, tile fields, treads) are not walls., Stroke-color pen identity: pairing, faint-ink demotion, dimension     chains, an, rect_room(), TestLatticeDemotion, TestPenGates (+1 more)

### Community 35 - "plumber.py"
Cohesion: 0.14
Nodes (11): Client, init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-, _door_attribute_overlay(), finalize_candidates(), Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, Promote candidates to entities, applying the offline confidence floors.      Gem, cand() (+3 more)

### Community 36 - "_projected_interval"
Cohesion: 0.20
Nodes (8): filter_page_data(), A copy of page_data holding only primitives whose bbox centre falls in     one o, path(), Region filtering tests (layout/filter.py)., region(), span(), TestFilterPageData, TestRegionTextSpans

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.18
Nodes (11): build_ink_map(), is_page_spanning(), Binary ink occupancy map over a page, used to find whitespace gutters., True for sheet furniture: a border rule or column divider that runs the     leng, page(), path(), Ink occupancy map tests (layout/occupancy.py)., span() (+3 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.08
Nodes (37): Entity, attach_takeoff(), _entity_to_dict(), _page_summary_dict(), PageRegionResult, Mirror the per-room takeoff onto room Entity.attributes["takeoff"]., _room_entity(), Heights (+29 more)

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
Cohesion: 0.21
Nodes (7): qualifying_clip_rects(), Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, s15 measured 2026-08-13: 214 text spans bridge every gutter, so the     text-inc, segment(), TestGoldenSegmentation, TestS15PathsOnlyRetry

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.33
Nodes (8): _is_arc_like(), bbox_aspect(), bezier_arc(), BezierAspectGateTests, line(), path(), Pins for the Bezier swing-arc bbox-aspect gate (DOOR_BBOX_ASPECT_MIN/MAX).  The, One cubic Bezier approximating a circular arc of the given sweep.      Standard

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.17
Nodes (11): Diagnosis (measured 2026-08-13, this is the evidence the plan argues from), Global Constraints, Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan, Self-Review, Task 0: Branch setup, Task 1: `build_ink_map(include_text=...)`, Task 2: Extract `_boxes_from_cut` (pure refactor), Task 3: `_attach_text_spans` (+3 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.15
Nodes (14): Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)., rot_paths(), diagonal_window(), path(), A real window's glazing band is clear glass — nothing between the panes.     An, Control: the bare 2-line capped opening with an empty band interior is         s, 5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two         wall, Insulation hatch drawn with pure line segments (no re/qu/c): the         diagona (+6 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.21
Nodes (6): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, Windows are drawn at any angle, not just axis-aligned. The cap-anchored     mode, 5-1133-WD03.pdf missed window at path idx 6475: three glazing panes         at 1, TestWindow51133Topology, TestWindowArbitraryAngle

### Community 103 - "PathPrimitive"
Cohesion: 0.16
Nodes (16): _check_provenance(), _ordered(), pending(), What a persisted sweep still needs verdicts on.  Reads the run output the sweep, Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk. (+8 more)

### Community 104 - "detect_doors"
Cohesion: 0.17
Nodes (22): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+14 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.18
Nodes (11): TruthItem, Regression corpus: fixture resolution, ground truth, matching, and the sweep., iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity() (+3 more)

### Community 107 - "vline"
Cohesion: 0.16
Nodes (10): detect_wall_network(), _is_light_pen(), Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., hline(), path(), Partition wall in the joinery pen: two hairline faces with diagonal     hatch st, TestFaceCollection (+2 more)

### Community 108 - "_bridge_white_runs"
Cohesion: 0.07
Nodes (34): detect_schedules(), build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), _normalize_bbox_plumber() (+26 more)

### Community 109 - "_find_openings"
Cohesion: 0.11
Nodes (21): _dedupe_by_perp(), _facing_cap_pairs(), _find_openings(), _glaze_index(), Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Two-axis lookup structure over a frame's glazing pool.      Every cap pair asks, Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.      A gl (+13 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.13
Nodes (13): Barrier polygon sealing a window opening.      A horizontal/vertical window's bb, _window_seal(), TextSpan, Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, A filled wall band exported as two triangles (CAD fill triangulation).      Each, A chimney breast / pier drawn as a closed box on the room side of a     wall ban, TestDiagonalWindowSeal, TestEmptyNetwork (+5 more)

### Community 111 - "app.py"
Cohesion: 0.04
Nodes (121): _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg(), _open_v_match() (+113 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.18
Nodes (11): Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door() (+3 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.13
Nodes (38): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _estimate_arc_sweep_deg(), BBox, Estimate sweep angle of a Bézier arc from its endpoints and estimated center., Pair single-Bezier `curve_arc` swings that form a garden-door split.      The po, _door_fallback_candidate() (+30 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.12
Nodes (12): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., _candidate_to_dict(), collect_warnings(), make_output_dir(), make_page_dir(), run_extract() (+4 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (9): _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, ExitCodeTests, RenderTests, ReviewLineIdentityTests (+1 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.44
Nodes (3): cut(), page(), TestXYCut

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.15
Nodes (15): attributes_by_room(), opening_dict(), takeoff.json — the document the web app's overlay and assembly table are both bu, The whole page as one document., One room: geometry, its opening ids, and its quantities.      `quantities` is No, The per-room quantity block mirrored onto Entity.attributes["takeoff"].      Liv, One door or window. `room_ids` is empty when it reached no room;     `dropped_ro, room_dict() (+7 more)

### Community 120 - "TestNetworkQueries"
Cohesion: 0.13
Nodes (8): door_candidate(), Rect room with a 45px doorway gap in the top wall (240..285)., Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, TestBboxSealFloor, TestOpeningSeals, TestPhantomDoorSeals, wall_band_v()

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record whether a line segment passed the polyline-arc length filter., Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+5 more)

### Community 123 - "batch_extract.py"
Cohesion: 0.14
Nodes (12): _attach_text_spans(), _clip_cut(), Grow paths-only boxes to absorb the text spans beside them.      The tier-2 cut, Strip empty margins; returns absolute (start, end) bin indices., Widest fully-empty internal run of at least min_bins. Leading and     trailing r, First clip edge lying strictly inside the span with ink on both sides.      An e, _trim(), _widest_gap() (+4 more)

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.16
Nodes (8): Measured scale expectations across the regression corpus.  Every number was meas, s13 is the one corpus sheet whose viewport and printed scale disagree.      It m, The resolver-level assertion: a region sitting inside the measuring         view, read(), TestKnownConflict, TestSheetsWithNoRecoverableScale, TestTextScales, TestViewportScales

### Community 126 - "_segments_min_distance"
Cohesion: 0.18
Nodes (10): diff_entities(), (kept, removed, added): `before` entities paired to `after` entities by     type, ClassifyTests, CompareRunsTests, DiffEntitiesTests, entity(), Path, tools/compare_sweeps.py — before/after comparison of two sweep runs.  Exercised (+2 more)

### Community 127 - "File Structure"
Cohesion: 0.22
Nodes (8): File Structure, Polyline-Arc Spur Pruning Implementation Plan, Self-review notes, Task 1: Add `_prune_arc_spurs` skeleton + clean-arc and pure-cycle tests, Task 2: Implement Y-junction spur pruning, Task 3: Cover multi-spur, oversized, and floor cases, Task 4: Extend `DebugTraceCollector.record_polyline_component` with the two optional kwargs, Task 5: Wire `_prune_arc_spurs` into `_detect_polyline_arc_bboxes`

### Community 128 - "2026-08-05 — detect_windows performance on giant sheets (handoff)"
Cohesion: 0.25
Nodes (7): 2026-08-05 — detect_windows performance on giant sheets (handoff), Constraints and gotchas, Optimization plan (pruning-only, output-identical), Reproduction recipes (self-contained — scratchpad scripts die with the session), Verification gates (all must pass, in this order), Where the time goes, Why this task exists (and why it was deferred)

### Community 129 - "segmenter.py"
Cohesion: 0.09
Nodes (21): 1. `DoorGates` (mirrors `WallGates`/`RoomGates`), 1. The win, isolated (shrunk-world on the references), 2. The organising rule, measured, 2. Threading, 3. Confirmed-door retention on the real 1:100 sheets, 3. `CrossGates`, 4. Classification, 4. `DOOR_SLIDE_PANEL_MIN/MAX_THICKNESS_PX` — the weakest row in the table (+13 more)

### Community 130 - "EntranceDoorTests"
Cohesion: 0.06
Nodes (41): bind_scale(), binding_texts(), _caption_distance(), _centroid(), _contains(), The scale governing one region, or None.      `viewports` must arrive smallest-b, Resolve a scale for every floor-plan region on one page., How far a text span sits from a region, or None if it is not near it.      Horiz (+33 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.15
Nodes (11): page_fallback_region(), Split a page into drawing regions. Returns [] for a page with no vector     ink, The whole page as a single region, for sheets too dense to split., segment_page(), PageData, block(), A solid-ish blob: a horizontal line every 4px so every bin row is inked., TestPathsOnlyRetry (+3 more)

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.17
Nodes (7): draw_overlay(), Document, MuPDF's own vector redraw of the page, in render.png's coordinate space.      Sa, render_page_png(), render_page_svg(), Region outlines on the overlay (extraction/renderer.py)., TestDrawOverlayWithRegions

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.09
Nodes (9): TestCase, Path, Skip helper for tests that need a real corpus sheet.  Corpus knowledge lives in, Return the sheet's path, or skip the test with an actionable message., require_sheet(), LoaderTests, The corpus loader resolves slugs against the committed manifest.  Every test bui, End-to-end regression: floor-plans.pdf must yield exactly the four     ground-tr (+1 more)

### Community 135 - "DoorAssemblyTests"
Cohesion: 0.13
Nodes (12): _chain(), PruneArcCycleCapsTests, A pure cycle has no leaves to walk from. Skipped., Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t, A cycle of more than DOOR_POLYLINE_CYCLE_MAX_SEGMENTS segments         exceeds t (+4 more)

### Community 136 - "client.py"
Cohesion: 0.13
Nodes (18): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+10 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.14
Nodes (16): _bridge_white_runs(), _equivalent_sides(), _FillRing, _rate_fill_classes(), (short, long) of the rectangle with this polygon's area and perimeter.      The, A closed same-fill polygon reconstructed from exploded `l` items., Annotation arrowhead: a tiny filled triangle or concave dart.          Walls are, Classify each fill color as wall material (True) or furniture (False).      Vect (+8 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.14
Nodes (10): _contains(), _ratio_pair(), Which drawing scale a room is measured at, and whether it can be trusted.  Pages, (w_ratio, h_ratio) of page over ISO size, orientation-matched., select_room_scale(), sheet_size_tokens(), verify_sheet_size(), _region() (+2 more)

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
Cohesion: 0.24
Nodes (7): BBox, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox., Max fraction of the bbox long axis covered by one near-collinear centerline., True when the two segments cross at an interior point.      _segments_min_distan, Min distance between a segment and an axis-aligned bbox (0 if touching)., _segment_bbox_distance(), _segments_properly_intersect()

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.11
Nodes (17): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+9 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.15
Nodes (22): clip_cut_positions(), Native PDF clip rects, used as extra cut hints for the segmenter.  Clip rects ar, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi, Tunable constants for page segmentation.  Values are measured, not guessed — see, Page segmentation: split a sheet into its constituent drawings., InkMap, bins[row][col] is 1 where drawn ink falls, 0 elsewhere., _boxes_from_cut() (+14 more)

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 147 - "RunDirTests"
Cohesion: 0.17
Nodes (10): _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO, An 8-seg quarter arc has ~11.25°/seg, well below the 45°         threshold. Even, A chain whose arc-like prefix is smaller than DOOR_POLYLINE_MIN_SEGMENTS (+2 more)

### Community 148 - "count_paths_in"
Cohesion: 0.20
Nodes (15): latest_run(), Path, Where a sweep leaves its output.  Sweeps used to extract into a `tempfile.Tempor, Wipe and recreate this slug's output directory., The most recent run directory for this slug, or None.      Timestamp names sort, reset_slug_dir(), slug_dir(), _centre() (+7 more)

### Community 149 - "TestExtractPageFrame"
Cohesion: 0.19
Nodes (8): The uniform scale factor of a rotate+scale transform. hypot is exact for     the, transform_scale(), Extraction puts geometry in the same frame as the declared page size.  page.get_, A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestPageTransform, write_rotated_pdf()

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.15
Nodes (13): hline(), path(), Filled arrowhead triangle (a marker ring) pointing down at `tip`., Stairs are furniture to the room stage: a room polygon runs to the     enclosing, Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, rect_room(), rooms_for(), stair_arrowhead() (+5 more)

### Community 151 - "normalize_bbox"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Window Gates Implementation Plan, Task 1: `WindowGates` dataclass, Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`, Task 3: The W-row negative control at 50°, Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°, Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it, Task 6: Findings doc — §4e frozen table, §6 entries (+1 more)

### Community 152 - "TestExtractImagesInstances"
Cohesion: 0.32
Nodes (6): PageTruth, evaluate_page(), Score one page's entities against its three verdict lists., entity(), EvaluatePageTests, Report shaping and exit codes.  The sweep itself (which runs the pipeline over r

### Community 153 - "fill_ring"
Cohesion: 0.13
Nodes (13): _merge_collinear_segs(), _pens_compatible(), Merge segments lying on the same infinite line into runs.      Bridges gaps up t, World-space wall gates, pre-multiplied by the detection factor.      Fields keep, A wall's two faces are drawn by one pen; colorless (fill-outline)     geometry s, Background-colored rings that could be hollow walls or built-in runs.      White, WallGates, _white_wall_candidates() (+5 more)

### Community 154 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Scale-Aware Door Detection Gates Implementation Plan, Self-Review, Task 1: `DoorGates` dataclass, Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point, Task 3: Thread gates through `leaves.py`, Task 4: Thread gates through `sliding.py` (+5 more)

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.14
Nodes (13): 1. Intake — extract the brief, 2. Orient — read before touching code, 3. Baseline and locate, 4. Diagnose — measure, don't guess, 5. Fix — test first, then code, then prose, 6. Sweep — target, references, then corpus, 7. CHECKPOINT — report and stop, 8. After the go-ahead (+5 more)

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.14
Nodes (14): Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, Scale coordinates by s, keep stroke widths — a 1:100 export., A closed 400x300 room drawn as four double-line wall bands., room_box_walls(), rooms_for(), shrink(), TestOrchestratorForwardsFactor, TestRoomsScaled (+6 more)

### Community 157 - "apply_classification"
Cohesion: 0.17
Nodes (11): 1. Factor computation (`scale` package), 2. Plumbing, 3. Constant classification, 4. Interactions to preserve (invariants across scales), 5. Testing, 6. Rejected alternatives (full reasoning in findings doc §5), Acceptance criteria, Design (+3 more)

### Community 160 - "TestRequestShape"
Cohesion: 0.09
Nodes (21): 1. The premise, verified, 2. Corpus scale census (measured 2026-08-12), 3. Does scale mismatch explain the bad sheets? Partially., 4. Constant classification table, 4b. Measurements (2026-08-12), 4c. Measurement-harness traps (2026-08-13), 4d. Door constant classification table (frozen 2026-08-13), 4e. Window constant classification table (frozen 2026-08-13) (+13 more)

### Community 161 - "SweepSlugsArgumentTests"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Wall/Room Gates Implementation Plan, Self-review notes (already applied), Task 1: `detection_scale()` — the factor computation, Task 2: Measure the uncertain-class constants (no production code), Task 3: `WallGates` — scale the wall-network world-space gates, Task 4: `RoomGates` — scale the room-stage world-space gates, Task 5: Plumb the factor through orchestrator, pipeline, and summary (+1 more)

### Community 162 - "TestNetworkQueries"
Cohesion: 0.17
Nodes (17): manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, sha256_of(), sheet_entry(), sheet_path() (+9 more)

### Community 163 - "_double_arc"
Cohesion: 0.15
Nodes (7): PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun, An 11-segment polyline arc has two degree-1 endpoints and no         junction —

### Community 164 - "SplitDoubleArcTests"
Cohesion: 0.18
Nodes (6): Path, Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, write_review_overlays(), Review images: one per page per entity type, ids stamped on., ReviewOverlayTests, ShortIdTests

### Community 165 - "ScaleInfo"
Cohesion: 0.12
Nodes (20): A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, ScaleInfo, detection_scale(), PageScales, The scales block written into each page's summary.json entry, and into     takeo, scale_summary_dict(), info(), detection_scale(): PageScales + regions -> one detection factor per page. (+12 more)

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "TestSwingHingePlugRestriction"
Cohesion: 0.20
Nodes (8): effective_denominator(), mm_per_px(), px2_to_m2(), px_to_m(), Pixel ↔ metre conversion.  Everything downstream of extraction/extractor.py is 1, Nominal beats raw so 1:50 sheets compute exactly (scale/factor.py rule)., TestEffectiveDenominator, TestUnits

### Community 168 - "scales_in_text"
Cohesion: 0.13
Nodes (8): Every 1:N denominator stated in one string, in the order written., Every scale printed on the page, each carrying its span's bbox., scales_in_text(), text_scales(), Reading a 1:N scale out of text spans.  Every string below is copied verbatim fr, span(), TestScalesInText, TestTextScales

### Community 169 - "File Structure"
Cohesion: 0.13
Nodes (14): File Structure, Floor Plan Scale Extraction Implementation Plan, Global Constraints, Self-Review, Task 10: Corpus expectations, Task 1: Units and the `ScaleInfo` model, Task 2: Tier 1 — viewport parsing, Task 3: Tier 2 — text parsing (+6 more)

### Community 170 - "transform_scale"
Cohesion: 0.20
Nodes (9): Baseline comparison — feat/scale-aware-wall-room-gates vs pre-branch (b0e705a), Identity verdict — the four factor-1.0 / 1:50 sheets (s02, s04, s14, s11), s02 (1:50, reference sheet) — LOST confirmed schedule, s04 (1:50) — 2 RETURNED false positives, s06 (1:100, scale-affected) — 1 LOST confirmed room, s06 / s12 verdict, s11 (unresolved → factor 1.0) — 2 new REVIEW doors + 3 RETURNED FPs, s12 (1:100, scale-affected) — 1 LOST confirmed room (+1 more)

### Community 171 - "test_curve_arc_garden_doors.py"
Cohesion: 0.22
Nodes (7): fill_ring(), marker_ring(), Closed filled rectangle exploded into 4 chained `l` items., Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFillClassRating, TestMarkerRings

### Community 172 - "DoorV2OpeningCheckTests"
Cohesion: 0.05
Nodes (34): build_parser(), cmd_extract(), cmd_inspect(), main(), parse_page_spec(), positive_metres(), argparse type: a positive, finite height in metres., Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]. (+26 more)

### Community 175 - "TestThickMaterialPairs"
Cohesion: 0.08
Nodes (23): Approach, Cache and offline, Cost, Grounding is enforced in code, not just prompted, Out of scope, Pipeline position, Problem, Request and response (+15 more)

### Community 176 - "TestSlugForPath"
Cohesion: 0.22
Nodes (8): Global Constraints, takeoff.json Overlay Document Implementation Plan, Task 1: Move `scale_summary_dict` into `scale/resolver.py`, Task 2: Openings become page-level records, computed once, Task 3: Rooms carry geometry, and unscaled rooms are kept, Task 4: `takeoff/document.py` — the serialiser, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 177 - "_dedupe_openings"
Cohesion: 0.06
Nodes (30): assess_scale(), check_dimensions(), check_door_leaves(), dimension_matches(), DimensionMatch, _fmt_scale(), leaf_width_px(), parse_dimension_mm() (+22 more)

### Community 178 - "TestBlindWindowPocket"
Cohesion: 0.23
Nodes (7): _layer_classes(), _layer_hint_from_layer(), _layer_tokens(), The element classes named by a layer's tokens., _wall_layer_hint(), Layer-name hints: CAD layer conventions pluralise the class name.  Measured on t, TestPluralLayerTokens

### Community 179 - "_FillRing"
Cohesion: 0.36
Nodes (3): World-space window gates, pre-multiplied by the detection factor.      Exactly O, WindowGates, TestWindowGates

### Community 180 - "cluster_denominators"
Cohesion: 0.09
Nodes (18): _arc_radius(), assign_openings(), _bbox_edge_along_boundary(), _chord_length(), opening_width_px(), opening_width_px_from_evidence(), _positive(), Polygon (+10 more)

### Community 181 - "Step 5 — Per-scale-group detection for mixed-scale pages"
Cohesion: 0.29
Nodes (6): Acceptance (to refine in the spec), Process (binding), Step 5 — Per-scale-group detection for mixed-scale pages, The design sketch to start from (findings §6, verbatim intent), The problem, Why it is NOT a bolt-on (measured hazard)

### Community 182 - "swing_door"
Cohesion: 0.08
Nodes (25): _check_opening_clear(), _line_nears_bridge_interior(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, True when some point of segment p1-p2 lies within buffer_px of the bridge     li, detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, DegenerateCompanionTests, DoorAssemblyTests (+17 more)

### Community 183 - "Step 1 — Widen the door Bezier aspect gate"
Cohesion: 0.33
Nodes (5): Acceptance, Process rules (binding), Step 1 — Widen the door Bezier aspect gate, The problem (measured), What to do

### Community 184 - "Step 2 — Retune the window span-overshoot gate (paper-space FP kill)"
Cohesion: 0.33
Nodes (5): Acceptance, Process rules (binding), Step 2 — Retune the window span-overshoot gate (paper-space FP kill), The problem (measured 2026-08-13, findings §4e/§6), What to do

### Community 185 - "Step 3 — Diagnose s15's 82 false positives (read-only)"
Cohesion: 0.33
Nodes (5): Acceptance, Hard limits, Step 3 — Diagnose s15's 82 false positives (read-only), The problem (baseline 2026-08-13), What to do

### Community 186 - "Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth)"
Cohesion: 0.33
Nodes (5): Acceptance, Hard limits, Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth), The problem, What to do

### Community 187 - "TestXYCut"
Cohesion: 0.21
Nodes (7): TestThreading, horizontal_window(), Three parallel lines with no perpendicular end-caps (e.g. a run of         dimen, A W1-style horizontal window: 3 tight horizontal glazing lines centered     in a, A W4-style vertical window: 3 tight vertical glazing lines closed by two     hor, TestWindowTopology, vertical_window()

### Community 188 - "TestPlumberTableBBox"
Cohesion: 0.18
Nodes (6): DetectionScale, _door(), room_polys holds unscaled rooms too, so the first assigned room can         be t, Referential integrity must hold in BOTH directions: if the opening         names, _room(), TestComputeTakeoff

### Community 189 - "TestWindowTightPairInterior"
Cohesion: 0.33
Nodes (4): fill_ring(), Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi, TestBarrierAllowlist

### Community 190 - "TestSlugForPath"
Cohesion: 0.07
Nodes (21): parse_measure_viewports(), BBox, Convert a raw /VP bbox into 150-DPI pixel space.      Two steps, in this order., Split a PDF array string into its top-level ``<< >>`` dictionaries.      Depth-c, Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.      The bbox is le, split_pdf_dicts(), viewport_bbox_to_px(), _FakeDoc (+13 more)

### Community 191 - "TestThickMaterialPairs"
Cohesion: 0.21
Nodes (8): Scale-aware window gates: WindowGates, threading, and the frozen classification', framed_triple_window(), quad(), 5-1133 W8: a three-light frame tagged with a single label. Two full-span     rai, 5-1133 W8 topology: block caps (qu jambs/mullions) + mullion-bridged     center, Collinear segments merge only across a gap a mullion block occupies —         th, A block with an X drawn through it is a post/column symbol (the         5-1133 b, TestFramedMultiLightWindow

### Community 192 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Room Labels Implementation Plan, Task 1: Branch and the deterministic span collector, Task 2: Schema, prompt, and the grounded response parser, Task 3: The one-call wrapper, Task 4: The label cache, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 193 - "TestWindowExteriorSide"
Cohesion: 0.22
Nodes (9): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, The s06 topology: two single-Bezier halves whose closed tips stop         ``gap`, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing (+1 more)

### Community 194 - "TestCrossWindowToleranceUnscaled"
Cohesion: 0.13
Nodes (14): Floor and ceiling, Geometry, Heights, Module layout, Openings and wall area, Out of scope (recorded), Output, Problem (+6 more)

### Community 196 - "Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)"
Cohesion: 0.25
Nodes (7): Evidence: what broke at f = 50/92.2 = 0.542 (all measured on the real PDF), Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`), How the ablation was done (reproduce in ~30 min), Read these first (in order), The problem in one paragraph, The recalibration task (the "proper fix"), Traps

### Community 197 - "denominator_from_c"
Cohesion: 0.24
Nodes (4): _prune_unread_page_output(), Delete the page-level files a sweep persists but never uses.      Making sweep o, PruneUnreadPageOutputTests, A fake run directory stands in for a real extraction (fast tier, no     pipeline

### Community 198 - "fill_ring"
Cohesion: 0.33
Nodes (5): By entity type, File map — where everything lives, by detection type, History and open work, Output contract you must not break, Regression corpus and tooling

### Community 199 - "_is_light_pen"
Cohesion: 0.08
Nodes (35): _detect_polyline_arc_bboxes(), _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, Detect door-swing arcs approximated by connected short line segments.      Some, Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl (+27 more)

### Community 200 - "_dedupe_openings"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 201 - "File structure"
Cohesion: 0.17
Nodes (11): File structure, Global Constraints, Room Quantity Takeoff Implementation Plan, Task 1: Units, Task 2: Heights, Task 3: Per-room scale selection and sheet-size verification, Task 4: Openings — width from evidence, assignment to rooms, Task 5: Quantities — `compute_takeoff` (+3 more)

### Community 202 - "SplitDoubleArcTests"
Cohesion: 0.20
Nodes (6): Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca, A zigzag chain has many 90° breaks. The detector requires         exactly one br, If the trimmed side were a LONG (≥4 segs) but axis-aligned         line, it woul, SplitDoubleArcTests

### Community 203 - "_scan_striped_runs"
Cohesion: 0.25
Nodes (8): _covered_length(), _field_span(), _merge_rungs(), Face indices belonging to striped runs.      Runs chain while the pitch stays eq, One rung from two same-offset rows (a copy; rows are re-scanned)., Intervals along the axis where >= MIN_RUNGS rungs of the run coexist.      Sweep, Length of the rung's extent lying inside the field span., _scan_striped_runs()

### Community 205 - "parse_answer"
Cohesion: 0.12
Nodes (11): can_prompt(), parse_answer(), prompt_for_scale(), True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream, The interactive scale prompt.  The prompt must never run in batch_extract (Proce (+3 more)

### Community 206 - "check_corpus"
Cohesion: 0.16
Nodes (10): load_manifest(), The committed manifest, or an empty corpus when it is absent., Flip a manifest entry's `labeled` flag and write the manifest back.      `labele, set_labeled(), CheckCorpusTests, The corpus verifier classifies each manifest sheet against the disk., check_corpus(), CorpusStatus (+2 more)

### Community 208 - "TestWindowExteriorSide"
Cohesion: 0.42
Nodes (3): A window is a wall opening between inside and outside. When the space     on one, TestWindowExteriorSide, wall_band_h()

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **537 isolated node(s):** `storage`, `sheets`, `What "generic" means here (the rule that overrides all others)`, `What counts as a win`, `1. Intake — extract the brief` (+532 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **70 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `_is_light_pen` to `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `test_layout_segmenter.py`, `Door Detection & Tests`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `Debug Trace Collector`, `DoorAssemblyTests`, `_dedupe_openings`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `Arc Detection Primitives`, `Room Polygonization Internals`, `TestWindowArbitraryAngle`, `Arc Cycle-Cap Pruning Tests`, `test_extraction_transform.py`, `arcs.py`, `RunDirTests`, `_fit_circle_3pt`, `TestAnnotationPenBarriers`, `hline`, `fill_ring`, `TestBlindWindowPocket`, `detect_windows`, `_double_arc`, `_projected_interval`, `renderer.py`, `_collect_wall_faces`, `test_curve_arc_garden_doors.py`, `TestNetworkQueries`, `_dedupe_openings`, `_FillRing`, `swing_door`, `TestXYCut`, `TestWindowTightPairInterior`, `TestThickMaterialPairs`, `TestWindowExteriorSide`, `_dedupe_openings`, `SplitDoubleArcTests`, `TestWindowExteriorSide`, `TestFarSidePairs`, `TestWindowSpanOvershootRetune`, `TestThickMaterialPairs`, `wall_band_h`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `vline`, `_find_openings`, `EntranceDoorTests`, `app.py`, `TestAnnotationPenBarriers`, `qualifying_clip_rects`, `TestNetworkQueries`, `test_door_assembly.py`, `batch_extract.py`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `Candidate` connect `hline` to `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `TestExtractImagesInstances`, `TestWindowArbitraryAngle`, `Arc Detection Primitives`, `Room Detection Tests`, `Arc Cycle-Cap Pruning Tests`, `arcs.py`, `_fit_circle_3pt`, `TestAnnotationPenBarriers`, `plumber.py`, `batch_extract.py`, `_dedupe_openings`, `_FillRing`, `swing_door`, `TestXYCut`, `TestPlumberTableBBox`, `TestWindowTightPairInterior`, `TestThickMaterialPairs`, `_is_light_pen`, `_dedupe_openings`, `TestWindowExteriorSide`, `TestWindowSpanOvershootRetune`, `TestMinWidthNegativeControl`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `_bridge_white_runs`, `_find_openings`, `EntranceDoorTests`, `app.py`, `TestAnnotationPenBarriers`, `_collect_wall_faces`, `qualifying_clip_rects`, `TestNetworkQueries`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `EntranceDoorTests` to `Door Assembly & Heuristics Core`, `EntranceDoorTests`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `Debug Trace Collector`, `_dedupe_openings`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `arcs.py`, `_fit_circle_3pt`, `geometry.py`, `TestAnnotationPenBarriers`, `hline`, `fill_ring`, `_projected_interval`, `renderer.py`, `batch_extract.py`, `scales_in_text`, `_dedupe_openings`, `swing_door`, `TestWindowTightPairInterior`, `_dedupe_openings`, `TestWindowExteriorSide`, `detect_doors`, `vline`, `_bridge_white_runs`, `app.py`, `TestAnnotationPenBarriers`, `qualifying_clip_rects`, `TestNetworkQueries`, `batch_extract.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 122 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 122 INFERRED edges - model-reasoned connections that need verification._
- **Are the 56 inferred relationships involving `PageData` (e.g. with `InkMap` and `PageRegionResult`) actually correct?**
  _`PageData` has 56 INFERRED edges - model-reasoned connections that need verification._