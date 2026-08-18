# Graph Report - agent  (2026-08-18)

## Corpus Check
- 186 files · ~290,765 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3174 nodes · 7917 edges · 199 communities (132 shown, 67 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 503 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `def54163`
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
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_TestCrossGatesUnscaledStopgapRatchet|TestCrossGatesUnscaledStopgapRatchet]]
- [[_COMMUNITY_TestDoorGatesUnscaledStopgapRatchet|TestDoorGatesUnscaledStopgapRatchet]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY__projected_interval|_projected_interval]]
- [[_COMMUNITY_TestSlidingScaleBehavior|TestSlidingScaleBehavior]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_shape.py|shape.py]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY__is_dashed|_is_dashed]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_TestWindowSpanOvershootRetune|TestWindowSpanOvershootRetune]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 234 edges
2. `PageData` - 153 edges
3. `Candidate` - 134 edges
4. `TextSpan` - 113 edges
5. `Region` - 92 edges
6. `detect_wall_network()` - 77 edges
7. `detect_windows()` - 67 edges
8. `detect_doors()` - 61 edges
9. `TruthItem` - 60 edges
10. `ScaleInfo` - 52 edges

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

## Communities (199 total, 67 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record whether a line segment passed the polyline-arc length filter., Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+5 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.12
Nodes (22): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+14 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.29
Nodes (3): Wall fills exploded into polygon edges are not linework (s03).      s03 draws ea, A wall band as PyMuPDF explodes s03's triangulated fill: two triangles         s, TestWindowInvisibleFillEdges

### Community 3 - "Door Detection & Tests"
Cohesion: 0.05
Nodes (67): _component_indices(), _dedupe_door_components(), _door_fallback_candidate(), door_open_leaf_path_indices(), _find_threshold_line(), _leaf_ink_indices(), _nearest_pair_distance(), _pair_door_assemblies() (+59 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.09
Nodes (28): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, BBox, One wall centerline segment (pixel space, y-down)., One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor (+20 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.37
Nodes (6): detection_scale(), PageScales, info(), detection_scale(): PageScales + regions -> one detection factor per page., region(), TestDetectionScale

### Community 7 - "Debug Trace Collector"
Cohesion: 0.09
Nodes (49): _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg(), _open_v_match() (+41 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.08
Nodes (20): _collect_slide_panels(), _panel_shape_ok(), CrossGates, World-space cross-validation gates, pre-multiplied by the factor.      Only the, prim(), _production_cross_gates_unscaled_usages(), _production_door_gates_unscaled_usages(), Scale-factor behavior of the door gates: identity at 1.0, linear at 0.5.  A "fai (+12 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.15
Nodes (10): door_candidate(), Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, rect_room(), rooms_for(), TestAnnotationPenBarriers, TestBboxSealFloor (+2 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.10
Nodes (22): Segment the page, classify its regions, and decide what detection sees.      cla, resolve_page_regions(), block(), one_blob_page(), page_with_a_dropped_strip(), parse_failing_classifier(), raster_page(), Region resolution rules (pipeline.resolve_page_regions).  A stub classifier stan (+14 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.20
Nodes (15): latest_run(), Path, Where a sweep leaves its output.  Sweeps used to extract into a `tempfile.Tempor, Wipe and recreate this slug's output directory., The most recent run directory for this slug, or None.      Timestamp names sort, reset_slug_dir(), slug_dir(), _centre() (+7 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.17
Nodes (9): detect(), LeafPairTests, ParkedLeafTests, PocketLeafTests, A panel pocketed at its -axis end, protruding at the +axis end., A closed 4-segment stroked (fill-less) rectangle of `l` items., parked_leaf: a stroked panel parked flush along a wall band that ends     at a j, sliding_of() (+1 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.11
Nodes (20): apply_classification(), build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+12 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.05
Nodes (50): detect_windows(), Detect windows as capped openings bridged by a parallel glazing band.      For e, Scale-aware window gates: WindowGates, threading, and the frozen classification', One fixture per paper-space family (spec §Testing). Each fails if its     named, Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)., The one world-space gate, exercised at a non-grid angle.      A faithful 1:100 e, rot_paths(), TestMinWidthNegativeControl (+42 more)

### Community 17 - "arcs.py"
Cohesion: 0.11
Nodes (17): _native_curve_chains(), Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests, NativeCurveChainsTests, _qu_leaf() (+9 more)

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
Cohesion: 0.17
Nodes (15): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _draw_regions(), BBox, Image (+7 more)

### Community 22 - "geometry.py"
Cohesion: 0.16
Nodes (31): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), _fit_circle_3pt(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some (+23 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.15
Nodes (14): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates (+6 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.10
Nodes (21): detect_wall_network(), Build the internal wall-centerline network for a page.      exclude_path_indices, hline(), path(), paving_field(), Wall-network builder tests (detection/walls.py).  Synthetic PathPrimitive fixtur, Partition wall in the joinery pen: two hairline faces with diagonal     hatch st, Pier tier: strong faces spaced past WALL_MAX_THICKNESS_PX pair only     on drawn (+13 more)

### Community 35 - "plumber.py"
Cohesion: 0.12
Nodes (13): Client, init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-, _door_attribute_overlay(), finalize_candidates(), Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, Promote candidates to entities, applying the offline confidence floors.      Gem, _room_entity() (+5 more)

### Community 36 - "_projected_interval"
Cohesion: 0.13
Nodes (16): _centre_in_any(), filter_page_data(), BBox, Reduce a PageData to the primitives inside a set of regions.  This filters, it d, A copy of page_data holding only primitives whose bbox centre falls in     one o, Text spans inside the given regions. Used to scope schedule detection to     sch, region_text_spans(), ImageRef (+8 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.16
Nodes (12): Tunable constants for page segmentation.  Values are measured, not guessed — see, build_ink_map(), is_page_spanning(), Binary ink occupancy map over a page, used to find whitespace gutters., True for sheet furniture: a border rule or column divider that runs the     leng, page(), path(), Ink occupancy map tests (layout/occupancy.py). (+4 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.17
Nodes (11): detect(), fold_chain(), FoldChainTests, folding_of(), OpenVTests, parked_stack(), ParkedStackPairTests, open_v: a lone bifold drawn half-open as a wide V of stroked     double-line lea (+3 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.14
Nodes (13): clip_cut_positions(), BBox, qualifying_clip_rects(), qualifying_clip_rects_from_boxes(), Native PDF clip rects, used as extra cut hints for the segmenter.  Clip rects ar, Keep only clips that look like real drawing boundaries.      Measured on the sam, Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi (+5 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.17
Nodes (11): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target) (+3 more)

### Community 44 - "renderer.py"
Cohesion: 0.42
Nodes (5): PageTruth, evaluate_page(), Score one page's entities against its three verdict lists., entity(), EvaluatePageTests

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.24
Nodes (5): A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestPageTransform, write_rotated_pdf()

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.17
Nodes (11): Diagnosis (measured 2026-08-13, this is the evidence the plan argues from), Global Constraints, Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan, Self-Review, Task 0: Branch setup, Task 1: `build_ink_map(include_text=...)`, Task 2: Extract `_boxes_from_cut` (pure refactor), Task 3: `_attach_text_spans` (+3 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.26
Nodes (5): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, End-to-end regression: floor-plans.pdf must yield exactly the four     ground-tr, TestFloorPlansRegression, TestWindow51133Topology

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.15
Nodes (9): Path, The images a human looks at while giving verdicts.  One PNG per page per entity, door_0007 -> d7. Unparseable ids are returned unchanged., Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, short_id(), write_review_overlays(), Review images: one per page per entity type, ids stamped on., ReviewOverlayTests (+1 more)

### Community 103 - "PathPrimitive"
Cohesion: 0.19
Nodes (12): pending(), Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk., ReviewBlocked, SweepOutputMissing, SweepOutputStale (+4 more)

### Community 104 - "detect_doors"
Cohesion: 0.16
Nodes (24): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+16 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.17
Nodes (12): SheetTruth, _labeled_but_unreviewed(), True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages, score_sheet(), entity(), LabeledFlagTests, Sweep correctness that does not require running the real pipeline.  `regression. (+4 more)

### Community 107 - "vline"
Cohesion: 0.13
Nodes (11): Tier 1 — the scale the PDF states in its own viewport measure dictionaries.  A C, Every drawing scale this page's viewports state, smallest bbox first.      Small, viewport_scales(), Measured scale expectations across the regression corpus.  Every number was meas, s13 is the one corpus sheet whose viewport and printed scale disagree.      It m, The resolver-level assertion: a region sitting inside the measuring         view, read(), TestKnownConflict (+3 more)

### Community 108 - "_bridge_white_runs"
Cohesion: 0.14
Nodes (22): load_manifest(), manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, The committed manifest, or an empty corpus when it is absent., Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, Flip a manifest entry's `labeled` flag and write the manifest back.      `labele (+14 more)

### Community 109 - "_find_openings"
Cohesion: 0.08
Nodes (24): _dedupe_by_perp(), _facing_cap_pairs(), _find_openings(), _glaze_index(), World-space window gates, pre-multiplied by the detection factor.      Exactly O, Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Two-axis lookup structure over a frame's glazing pool.      Every cap pair asks (+16 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.11
Nodes (18): _effective_denominator(), One detection factor per page: which scale governs the ink detection sees.  Dete, Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY., Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan., The resolution ladder, and how a scale binds to a floor plan.  Binding is what m, _stored_info(), Tier 2 — the scale a sheet prints as text.  Three corpus sheets carry no viewpor, canonical_denominators() (+10 more)

### Community 111 - "app.py"
Cohesion: 0.07
Nodes (56): _line_angle_deg(), _line_length(), _perpendicular_spacing(), _band_has_wall_material(), _claims_interior_pair(), _collapse_redundant_centerlines(), _collect_fill_rings(), _collect_material_marks() (+48 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.18
Nodes (11): Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door() (+3 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.20
Nodes (18): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), _normalize_bbox_plumber(), BBox (+10 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.15
Nodes (11): open_v_door(), page(), prim(), End-to-end door scale behavior on FAITHFUL 1:100 fixtures.  A faithful 1:100 exp, open_v (detection/doors/folding.py::_open_v_match) reads three gates:     gates., Quarter-arc + a double-line leaf, as a faithful export at any scale.      radius, A lone half-open bifold V (folding.py's open_v pattern): two double-line     obl, swing_door() (+3 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (10): _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, ExitCodeTests, Report shaping and exit codes.  The sweep itself (which runs the pipeline over r, RenderTests (+2 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.20
Nodes (11): _is_arc_like(), bbox_aspect(), bezier_arc(), BezierAspectGateTests, line(), path(), Pins for the Bezier swing-arc bbox-aspect gate (DOOR_BBOX_ASPECT_MIN/MAX).  The, One cubic Bezier approximating a circular arc of the given sweep.      Standard (+3 more)

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.05
Nodes (50): _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, _split_double_arc(), _trim_chain_extension_caps() (+42 more)

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.18
Nodes (11): TruthItem, Regression corpus: fixture resolution, ground truth, matching, and the sweep., iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity() (+3 more)

### Community 123 - "batch_extract.py"
Cohesion: 0.13
Nodes (15): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Run extract command for a single PDF.     Returns (pdf_path, success: bool, outp, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive). (+7 more)

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.28
Nodes (6): Scales stated on the sheet, unbound to any drawing.      inspect does not segmen, unbound_scale_lines(), The inspect command's unbound scale listing.  inspect never segments regions, so, TestUnboundScaleLines, text(), viewport()

### Community 126 - "_segments_min_distance"
Cohesion: 0.15
Nodes (11): Barrier polygon sealing a window opening.      A horizontal/vertical window's bb, _window_seal(), hline(), path(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, TestClosedRooms, TestDiagonalWindowSeal, TestEmptyNetwork (+3 more)

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
Nodes (41): bind_scale(), binding_texts(), _caption_distance(), _centroid(), _contains(), Resolve a scale for every floor-plan region on one page., How far a text span sits from a region, or None if it is not near it.      Horiz, Every text scale near enough to this region to be about it, nearest first. (+33 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.13
Nodes (15): assigned_path_fraction(), Share of the page's paths that any region would keep.      Deliberately the same, _attach_text_spans(), Grow paths-only boxes to absorb the text spans beside them.      The tier-2 cut, Split a page into drawing regions. Returns [] for a page with no vector     ink, segment_page(), PageData, block() (+7 more)

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.24
Nodes (10): _fit_oriented_rect(), Fit an oriented rectangle to a bag of corner points, any rotation.      Orders u, EndToEndTests, leaf(), One folding leaf running p -> q, drawn in the Vectorworks joinery     signature:, OrientedRectFitTests, prim(), qu_panel() (+2 more)

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.10
Nodes (7): TestCase, Path, Skip helper for tests that need a real corpus sheet.  Corpus knowledge lives in, Return the sheet's path, or skip the test with an actionable message., require_sheet(), LoaderTests, The corpus loader resolves slugs against the committed manifest.  Every test bui

### Community 135 - "DoorAssemblyTests"
Cohesion: 0.33
Nodes (3): denominator_from_c(), The 1:N denominator for a /Measure /X conversion factor., TestDenominatorFromC

### Community 136 - "client.py"
Cohesion: 0.13
Nodes (18): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+10 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.21
Nodes (10): _bridge_white_runs(), _equivalent_sides(), (short, long) of the rectangle with this polygon's area and perimeter.      The, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      gate, _bridge_white_runs is detect_rooms's ONLY production call site     (detection/ro, TestBridgeWhiteRunsGapScaling, Accepted hollow-wall/joinery _FillRing over the given rectangle., Bridges close OPEN SPANS in accepted white-ring runs; rings already     connecte (+2 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.10
Nodes (36): _load_font(), baseline_dir(), baseline_run(), classify(), compare(), compare_runs(), _crop(), diff_entities() (+28 more)

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
Cohesion: 0.10
Nodes (27): Page segmentation: split a sheet into its constituent drawings., InkMap, bins[row][col] is 1 where drawn ink falls, 0 elsewhere., _boxes_from_cut(), _centre_in(), _clip_cut(), _col_profile(), count_paths_in() (+19 more)

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.11
Nodes (17): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+9 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.44
Nodes (3): cut(), page(), TestXYCut

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 148 - "count_paths_in"
Cohesion: 0.11
Nodes (12): can_prompt(), parse_answer(), prompt_for_scale(), Tier 4 input — ask the user, but only when someone is there to answer.  batch_ex, True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream (+4 more)

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.23
Nodes (4): Rect room with a 45px doorway gap in the top wall (240..285)., TestOpeningSeals, wall_band_h(), wall_band_v()

### Community 151 - "normalize_bbox"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Window Gates Implementation Plan, Task 1: `WindowGates` dataclass, Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`, Task 3: The W-row negative control at 50°, Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°, Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it, Task 6: Findings doc — §4e frozen table, §6 entries (+1 more)

### Community 153 - "fill_ring"
Cohesion: 0.21
Nodes (5): _hface(), Isolates _merge_collinear_segs's offset-tolerance scaling directly —     the exa, A bare horizontal wall-face _Seg for isolated merge-tolerance tests., TestMergeCollinearOffsetScaling, TestWallGatesConstruction

### Community 154 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Scale-Aware Door Detection Gates Implementation Plan, Self-Review, Task 1: `DoorGates` dataclass, Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point, Task 3: Thread gates through `leaves.py`, Task 4: Thread gates through `sliding.py` (+5 more)

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.12
Nodes (23): _building_masses(), detect_rooms(), _drop_window_exterior_sides(), _folding_chain_gap_plug(), _free_space_components(), Room detection: rooms are the connected free-space components between walls.  Ea, World-space room gates pre-multiplied by the detection factor     (areas by fact, Fraction of a bbox area covered by the text spans lying over it. (+15 more)

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.19
Nodes (12): Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, Scale coordinates by s, keep stroke widths — a 1:100 export., A closed 400x300 room drawn as four double-line wall bands., room_box_walls(), rooms_for(), shrink(), TestOrchestratorForwardsFactor, TestRoomsScaled (+4 more)

### Community 157 - "apply_classification"
Cohesion: 0.17
Nodes (11): 1. Factor computation (`scale` package), 2. Plumbing, 3. Constant classification, 4. Interactions to preserve (invariants across scales), 5. Testing, 6. Rejected alternatives (full reasoning in findings doc §5), Acceptance criteria, Design (+3 more)

### Community 159 - "_segments_min_distance"
Cohesion: 0.52
Nodes (6): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., Namespace

### Community 160 - "TestRequestShape"
Cohesion: 0.10
Nodes (20): 1. The premise, verified, 2. Corpus scale census (measured 2026-08-12), 3. Does scale mismatch explain the bad sheets? Partially., 4. Constant classification table, 4b. Measurements (2026-08-12), 4c. Measurement-harness traps (2026-08-13), 4d. Door constant classification table (frozen 2026-08-13), 4e. Window constant classification table (frozen 2026-08-13) (+12 more)

### Community 161 - "SweepSlugsArgumentTests"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Wall/Room Gates Implementation Plan, Self-review notes (already applied), Task 1: `detection_scale()` — the factor computation, Task 2: Measure the uncertain-class constants (no production code), Task 3: `WallGates` — scale the wall-network world-space gates, Task 4: `RoomGates` — scale the room-stage world-space gates, Task 5: Plumb the factor through orchestrator, pipeline, and summary (+1 more)

### Community 162 - "TestNetworkQueries"
Cohesion: 0.24
Nodes (5): Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, s15 measured 2026-08-13: 214 text spans bridge every gutter, so the     text-inc, segment(), TestGoldenSegmentation, TestS15PathsOnlyRetry

### Community 163 - "_double_arc"
Cohesion: 0.26
Nodes (6): detect_schedules(), Schedule detection — tables carry real bboxes.  detect_schedules used to emit bb, extract_plumber_page must surface each table's bbox, normalized to     150-DPI p, _table(), TestDetectSchedulesBBox, TestPlumberTableBBox

### Community 165 - "ScaleInfo"
Cohesion: 0.31
Nodes (6): A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, ScaleInfo, raw is lifted verbatim from PDF text and can contain a bracket         sequence, region(), TestScaleTable, TestScaleInfoDefaults

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "TestSwingHingePlugRestriction"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

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
Cohesion: 0.16
Nodes (10): _collect_wall_faces(), Return (stroked wall faces, filled-band centerlines)., fill_ring(), marker_ring(), Closed filled rectangle exploded into 4 chained `l` items., Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFaceCollection (+2 more)

### Community 172 - "DoorV2OpeningCheckTests"
Cohesion: 0.24
Nodes (4): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, DoorV2OpeningCheckTests, Tests for v2 bridge-line opening check and arc sweep estimation.

### Community 173 - "MainExceptionIsolationTests"
Cohesion: 0.27
Nodes (8): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing, The 5-1133-WD03.pdf door_0007 + door_0008 topology, simplified.          Two sta

### Community 175 - "TestThickMaterialPairs"
Cohesion: 0.12
Nodes (17): Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), Candidate, DoorAssemblyTests, DoorEvidencePropagationTests, _far_wall_network(), Minimal non-empty wall network located far from the doors under test., A single_line_leaf door with no surrounding wall AND no nearby label         is (+9 more)

### Community 176 - "TestSlugForPath"
Cohesion: 0.14
Nodes (15): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., Document, render_page_png(), _candidate_to_dict(), collect_warnings(), _entity_to_dict() (+7 more)

### Community 177 - "_dedupe_openings"
Cohesion: 0.10
Nodes (14): _cache_missed(), _entities_by_page(), _extract_for_sweep(), _prune_unread_page_output(), Path, Run the pipeline over corpus sheets and score the output.  Sheets are extracted, Delete the page-level files a sweep persists but never uses.      Making sweep o, run_extract as the sweep needs it: offline, and never interactive.      allow_sc (+6 more)

### Community 178 - "TestBlindWindowPocket"
Cohesion: 0.14
Nodes (10): _door_plugs(), _open_leaf_edges(), Bbox edges of a garden-layout double door that are room floor, not wall.      A, Thin barrier bands along the wall planes through a detected door.      The door, Interrupted-run plugs need jambs that REACH the plug band and a mid     that is, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto., Plug extensions end at their supporting material; slide ends veto.      Geometry, TestGardenDoorSeals (+2 more)

### Community 179 - "_FillRing"
Cohesion: 0.24
Nodes (9): _FillRing, _is_background_fill(), _rate_fill_classes(), True for fills indistinguishable from the page background (white).      CAD expo, A closed same-fill polygon reconstructed from exploded `l` items., Annotation arrowhead: a tiny filled triangle or concave dart.          Walls are, Classify each fill color as wall material (True) or furniture (False).      Vect, Background-colored rings that could be hollow walls or built-in runs.      White (+1 more)

### Community 180 - "cluster_denominators"
Cohesion: 0.31
Nodes (4): cluster_denominators(), Group near-equal denominators, largest group first in input order.      Lives he, CAD never writes the same scale as the same float, so every value here     is a, TestClusterDenominators

### Community 181 - "Step 5 — Per-scale-group detection for mixed-scale pages"
Cohesion: 0.29
Nodes (6): Acceptance (to refine in the spec), Process (binding), Step 5 — Per-scale-group detection for mixed-scale pages, The design sketch to start from (findings §6, verbatim intent), The problem, Why it is NOT a bolt-on (measured hazard)

### Community 182 - "swing_door"
Cohesion: 0.11
Nodes (16): detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, EntranceDoorTests, line(), path(), PolylineArcBinCapTests, quarter_arc_lines(), Regression + new-feature tests for entrance-door threshold-line handling.      G (+8 more)

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

### Community 188 - "TestCrossGatesUnscaledStopgapRatchet"
Cohesion: 0.33
Nodes (4): fill_ring(), Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi, TestBarrierAllowlist

### Community 189 - "TestDoorGatesUnscaledStopgapRatchet"
Cohesion: 0.19
Nodes (15): One drawing on a sheet, found by whitespace segmentation.      bbox is 150-DPI p, Region, _page_summary_dict(), PageRegionResult, The per-region scale table printed after each page., The scales block written into each page's summary.json entry., scale_summary_dict(), scale_table() (+7 more)

### Community 190 - "TestSlugForPath"
Cohesion: 0.07
Nodes (21): parse_measure_viewports(), BBox, Convert a raw /VP bbox into 150-DPI pixel space.      Two steps, in this order., Split a PDF array string into its top-level ``<< >>`` dictionaries.      Depth-c, Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.      The bbox is le, split_pdf_dicts(), viewport_bbox_to_px(), _FakeDoc (+13 more)

### Community 191 - "_projected_interval"
Cohesion: 0.32
Nodes (8): _project_onto_axis(), _projected_interval(), Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars., Scalar projection of p onto the unit axis (dx, dy) from origin., _cap_record(), _glaze_record(), Record for a glazing line: ``perp`` = depth offset (along v), ``span`` =     ext, Record for a cap line: ``perp`` = position along the opening (u), ``span``     =

### Community 192 - "TestSlidingScaleBehavior"
Cohesion: 0.38
Nodes (4): leaf_pair_door(), leaf_pair (detection/doors/sliding.py) reads gates.DOOR_SLIDE_PANEL_MIN_THICKNES, Two parallel panel rectangles in-band with partial overlap (sliding.py's     lea, TestSlidingScaleBehavior

### Community 194 - "shape.py"
Cohesion: 0.50
Nodes (4): _compute_hu_distance(), _rasterize_paths_to_canvas(), Rasterize line/curve primitives onto a normalized binary canvas.      Segments a, Distance between candidate arc paths and the door Hu Moment template.      Lower

### Community 196 - "_is_dashed"
Cohesion: 0.50
Nodes (3): _is_dashed(), True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., TestDashDetection

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **463 isolated node(s):** `storage`, `sheets`, `Project purpose`, `Algorithm reference`, `Commands` (+458 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **67 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `Debug Trace Collector` to `Pipeline Orchestration & Extraction`, `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `TestExtractImagesInstances`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `_dedupe_openings`, `Room Polygonization Internals`, `wall_band_v`, `Arc Cycle-Cap Pruning Tests`, `arcs.py`, `test_extraction_transform.py`, `geometry.py`, `TestAnnotationPenBarriers`, `hline`, `detect_windows`, `_projected_interval`, `renderer.py`, `TestSwingHingePlugRestriction`, `_collect_wall_faces`, `test_curve_arc_garden_doors.py`, `DoorV2OpeningCheckTests`, `MainExceptionIsolationTests`, `TestNetworkQueries`, `TestThickMaterialPairs`, `TestBlindWindowPocket`, `_FillRing`, `swing_door`, `TestWindowExteriorSide`, `TestCrossGatesUnscaledStopgapRatchet`, `TestSlidingScaleBehavior`, `shape.py`, `_is_dashed`, `TestBlindWindowPocket`, `TestWindowSpanOvershootRetune`, `TestMarkerRings`, `detect_doors`, `_find_openings`, `app.py`, `_collect_wall_faces`, `qualifying_clip_rects`, `qualifying_clip_rects`, `_segments_min_distance`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `Candidate` connect `TestThickMaterialPairs` to `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Arc Cycle-Cap Pruning Tests`, `_fit_circle_3pt`, `geometry.py`, `TestAnnotationPenBarriers`, `hline`, `TestWindowTightPairInterior`, `_double_arc`, `plumber.py`, `TestSwingHingePlugRestriction`, `DoorV2OpeningCheckTests`, `TestSlugForPath`, `TestBlindWindowPocket`, `swing_door`, `TestWindowExteriorSide`, `TestCrossGatesUnscaledStopgapRatchet`, `TestDoorGatesUnscaledStopgapRatchet`, `TestBlindWindowPocket`, `TestWindowSpanOvershootRetune`, `TestMarkerRings`, `_find_openings`, `qualifying_clip_rects`, `_segments_min_distance`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `_projected_interval` to `EntranceDoorTests`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `Debug Trace Collector`, `Room Detection Tests`, `Wall Network Construction & Tests`, `wall_band_v`, `Arc Cap-Trim Tests`, `arcs.py`, `test_extraction_transform.py`, `geometry.py`, `TestAnnotationPenBarriers`, `hline`, `TestWindowTightPairInterior`, `detect_windows`, `_double_arc`, `renderer.py`, `TestSwingHingePlugRestriction`, `scales_in_text`, `DoorV2OpeningCheckTests`, `TestThickMaterialPairs`, `TestSlugForPath`, `TestBlindWindowPocket`, `_FillRing`, `swing_door`, `TestWindowExteriorSide`, `TestCrossGatesUnscaledStopgapRatchet`, `TestDoorGatesUnscaledStopgapRatchet`, `TestBlindWindowPocket`, `detect_doors`, `app.py`, `_segments_min_distance`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 107 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 107 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `PageData` (e.g. with `InkMap` and `PageRegionResult`) actually correct?**
  _`PageData` has 52 INFERRED edges - model-reasoned connections that need verification._