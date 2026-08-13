# Graph Report - agent  (2026-08-13)

## Corpus Check
- 174 files · ~273,495 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2993 nodes · 7440 edges · 181 communities (119 shown, 62 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 465 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9d1e0ba0`
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
- [[_COMMUNITY_test_scale_units.py|test_scale_units.py]]
- [[_COMMUNITY_scales_in_text|scales_in_text]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_transform_scale|transform_scale]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
- [[_COMMUNITY_TestOpeningSeals|TestOpeningSeals]]
- [[_COMMUNITY_MainExceptionIsolationTests|MainExceptionIsolationTests]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestFloorPlansRegression|TestFloorPlansRegression]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 217 edges
2. `PageData` - 138 edges
3. `Candidate` - 129 edges
4. `TextSpan` - 107 edges
5. `Region` - 90 edges
6. `detect_wall_network()` - 77 edges
7. `detect_windows()` - 59 edges
8. `detect_doors()` - 58 edges
9. `ScaleInfo` - 52 edges
10. `TruthItem` - 49 edges

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

## Communities (181 total, 62 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.17
Nodes (11): detect(), fold_chain(), FoldChainTests, folding_of(), OpenVTests, parked_stack(), ParkedStackPairTests, open_v: a lone bifold drawn half-open as a wide V of stroked     double-line lea (+3 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.12
Nodes (22): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+14 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.11
Nodes (15): _door_plugs(), _open_leaf_edges(), Barrier polygon sealing a window opening.      A horizontal/vertical window's bb, Bbox edges of a garden-layout double door that are room floor, not wall.      A, Thin barrier bands along the wall planes through a detected door.      The door, _window_seal(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto. (+7 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.15
Nodes (11): detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, DoorAssemblyTests, EntranceDoorTests, line(), path(), quarter_arc_lines(), Regression + new-feature tests for entrance-door threshold-line handling.      G (+3 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.07
Nodes (38): _cross_validate(), True when a wall FACE line runs unbroken through the bbox span.      A real wind, Validate doors/windows against the wall-centerline network.      Doors keep the, _wall_runs_through(), BBox, One wall centerline segment (pixel space, y-down)., One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized). (+30 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.14
Nodes (16): A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, ScaleInfo, The per-region scale table printed after each page., The scales block written into each page's summary.json entry., scale_summary_dict(), scale_table(), Scale reporting inside the pipeline: the console table and summary.json., det_scale is resolved before the skip_detection branch in run_extract     (so th (+8 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.08
Nodes (54): _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg(), _open_v_match() (+46 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.07
Nodes (25): DoorGates, World-space door gates, pre-multiplied by the detection factor.      Fields keep, CrossGates, World-space cross-validation gates, pre-multiplied by the factor.      Only the, Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), prim(), _production_cross_gates_unscaled_usages() (+17 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.14
Nodes (12): door_candidate(), Rect room with a 45px doorway gap in the top wall (240..285)., Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, rooms_for(), TestBboxSealFloor, TestClosedRooms, TestOpeningSeals (+4 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.05
Nodes (41): apply_classification(), build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+33 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.19
Nodes (9): paving_field(), Running-bond paving: continuous course lines, staggered joint lines.      Mirror, Striped fields (paving bonds, tile fields, treads) are not walls., Four wall bands forming a closed rectangular room (outer faces at the     given, Stroke-color pen identity: pairing, faint-ink demotion, dimension     chains, an, rect_room(), TestLatticeDemotion, TestPenGates (+1 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.16
Nodes (9): detect(), LeafPairTests, ParkedLeafTests, PocketLeafTests, A panel pocketed at its -axis end, protruding at the +axis end., A closed 4-segment stroked (fill-less) rectangle of `l` items., parked_leaf: a stroked panel parked flush along a wall band that ends     at a j, sliding_of() (+1 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.08
Nodes (48): _component_indices(), _dedupe_door_components(), _door_fallback_candidate(), door_open_leaf_path_indices(), _leaf_ink_indices(), _merge_double_door_assemblies(), _nearest_pair_distance(), _pair_door_assemblies() (+40 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.18
Nodes (10): One fixture per paper-space family (spec §Testing). Each fails if its     named, TestPaperInvariance, hline(), A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two, 5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is         fa, Three parallel lines with no perpendicular end-caps (e.g. a run of         dimen, Three parallel lines spaced far apart (e.g. stair treads) exceed the         gla, floor-plans true windows draw a narrow double glazing line (panes         1.75px (+2 more)

### Community 17 - "arcs.py"
Cohesion: 0.05
Nodes (40): Record result of the _is_door_leaf check for a primitive., Pre-populate by_path_index with raw metadata for every PathPrimitive., Record result of the _is_arc_like check for a primitive., Record whether a line segment passed the polyline-arc length filter., _native_curve_chains(), Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, _compute_hu_distance(), _rasterize_paths_to_canvas() (+32 more)

### Community 18 - "windows.py"
Cohesion: 0.11
Nodes (13): address_match(), Shared address-detection patterns for corpus hygiene checks.  Two callers share, The matched address-like substring in `text`, or None., AdoptTests, make_pdf(), NextSlugTests, Path, Adopting a new sheet into the corpus. (+5 more)

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.10
Nodes (20): 1. The organising rule — the INVERSE of doors, 1. `WindowGates` (mirrors `WallGates`/`RoomGates`/`DoorGates`), 2. Retention vetoes — the confirmed extremes kill every W-candidacy but one, 2. Threading, 3. Classification (frozen; full table to findings §4e), 3. The variant matrix — every verdict exercised end-to-end, 4. Hidden-constant audits (both §4b blind-spot classes), 4. Shrunk-world on s01/s02 — read for what it can and cannot say (+12 more)

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (43): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.10 Folding/bifold doors — no arc (`detection/doors/folding.py`), 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`) (+35 more)

### Community 21 - "_fit_circle_3pt"
Cohesion: 0.05
Nodes (37): Client, _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _draw_regions(), _load_font() (+29 more)

### Community 22 - "geometry.py"
Cohesion: 0.08
Nodes (36): DebugTraceCollector, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Register a collected swing. Returns swing_id., Record the swing-anchored single-line leaf search outcome.          `result` is, Register a collected leaf. Returns leaf_id., Record a final candidate with its full confidence breakdown. (+28 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.18
Nodes (10): DoubleDoorTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates, Leaf overlap of 10 px (> DOOR_DOUBLE_LEAF_OVERLAP_PX=5) → two separate candidate, has_threshold, door_subtype, and threshold_path_index carry through from either, threshold_path_index=0 must be preserved (is-not-None guard, not falsy check). (+2 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.15
Nodes (11): detect_wall_network(), _is_light_pen(), Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., hline(), path(), Partition wall in the joinery pen: two hairline faces with diagonal     hatch st, TestCenterlines (+3 more)

### Community 35 - "plumber.py"
Cohesion: 0.22
Nodes (11): EndToEndTests, leaf(), One folding leaf running p -> q, drawn in the Vectorworks joinery     signature:, leaf_pair_door(), End-to-end door scale behavior on FAITHFUL 1:100 fixtures.  A faithful 1:100 exp, Two parallel panel rectangles in-band with partial overlap (sliding.py's     lea, OrientedRectFitTests, prim() (+3 more)

### Community 36 - "_projected_interval"
Cohesion: 0.14
Nodes (15): assigned_path_fraction(), _centre_in_any(), filter_page_data(), BBox, Reduce a PageData to the primitives inside a set of regions.  This filters, it d, A copy of page_data holding only primitives whose bbox centre falls in     one o, Share of the page's paths that any region would keep.      Deliberately the same, Text spans inside the given regions. Used to scope schedule detection to     sch (+7 more)

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
Cohesion: 0.15
Nodes (17): _glaze_index(), Two-axis lookup structure over a frame's glazing pool.      Every cap pair asks, Scale-aware window gates: WindowGates, threading, and the frozen classification', Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)., rot_paths(), TestThreading, diagonal_window(), framed_triple_window() (+9 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.18
Nodes (7): clip_cut_positions(), BBox, qualifying_clip_rects_from_boxes(), Keep only clips that look like real drawing boundaries.      Measured on the sam, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi, page_with(), TestClipGating

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.17
Nodes (11): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target) (+3 more)

### Community 44 - "renderer.py"
Cohesion: 0.27
Nodes (8): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing, The 5-1133-WD03.pdf door_0007 + door_0008 topology, simplified.          Two sta

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.30
Nodes (5): BBox, A distant door must not suppress a window it only clips after the         20px d, A DOOR_FALLBACK_CONFIDENCE (0.35) door often IS window-like ink         (glazing, A window candidate sitting ON a fallback door's linework (5-1133:         the jo, TestDoorWindowExclusion

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.11
Nodes (18): Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan., binding_texts(), _caption_distance(), _centroid(), _contains(), The resolution ladder, and how a scale binds to a floor plan.  Binding is what m, How far a text span sits from a region, or None if it is not near it.      Horiz, Every text scale near enough to this region to be about it, nearest first. (+10 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.12
Nodes (14): detect_windows(), _frame_axes(), _merge_mullion_chains(), Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C, Join collinear glazing segments across mullion blocks into logical panes.      A, Detect windows as capped openings bridged by a parallel glazing band.      For e, _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02 (+6 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.21
Nodes (7): hline(), path(), Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, rect_room(), TestAnnotationPenBarriers, TestComponentFiltering, vline()

### Community 103 - "PathPrimitive"
Cohesion: 0.18
Nodes (13): _ordered(), pending(), Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk., ReviewBlocked, SweepOutputMissing (+5 more)

### Community 104 - "detect_doors"
Cohesion: 0.12
Nodes (27): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+19 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.08
Nodes (23): PageTruth, SheetTruth, evaluate_page(), _labeled_but_unreviewed(), _prune_unread_page_output(), Delete the page-level files a sweep persists but never uses.      Making sweep o, True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages (+15 more)

### Community 107 - "vline"
Cohesion: 0.16
Nodes (8): Measured scale expectations across the regression corpus.  Every number was meas, s13 is the one corpus sheet whose viewport and printed scale disagree.      It m, The resolver-level assertion: a region sitting inside the measuring         view, read(), TestKnownConflict, TestSheetsWithNoRecoverableScale, TestTextScales, TestViewportScales

### Community 108 - "_bridge_white_runs"
Cohesion: 0.09
Nodes (38): manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, sha256_of(), sheet_entry(), sheet_path() (+30 more)

### Community 109 - "_find_openings"
Cohesion: 0.12
Nodes (18): _dedupe_by_perp(), _facing_cap_pairs(), _find_openings(), Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.      A gl, Index pairs ``(i, j, width)`` of caps that face each other across an opening., Pair facing caps and confirm a glazing band bridges each opening.      ``cap_poo (+10 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.13
Nodes (12): canonical_denominators(), cluster_denominators(), format_scale(), Scale arithmetic shared by every resolution tier.  A PDF /Measure dictionary sta, Group near-equal denominators, largest group first in input order.      Lives he, One representative per cluster — how many DISTINCT scales are present., Render a denominator for display: 1:100, or 1:136.4 when it is not whole., Scale arithmetic: PDF /Measure conversion factors to a 1:N denominator.  Every n (+4 more)

### Community 111 - "app.py"
Cohesion: 0.04
Nodes (96): _find_threshold_line(), Find an entrance-door threshold/sill line parallel to the leaf long axis.      T, _find_leaf_companion_lines(), Find lines forming the same thin-rect leaf as the anchored leaf line.      Door, _angle_diff_mod180(), _bbox_expanded(), _bbox_union(), _bboxes_overlap() (+88 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.17
Nodes (13): Flip a manifest entry's `labeled` flag and write the manifest back.      `labele, set_labeled(), Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item() (+5 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.16
Nodes (22): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), extract_tables(), _normalize_bbox_plumber() (+14 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.11
Nodes (13): Split a PDF array string into its top-level ``<< >>`` dictionaries.      Depth-c, split_pdf_dicts(), _FakeDoc, _FakePage, _Matrix, Parsing /VP -> /Measure viewport dictionaries.  The array strings below are copi, Just enough of fitz.Rect for viewport_scales: x0/y0/x1/y1 attributes., Just enough of fitz.Matrix for page_transform: a/b/c/d/e/f attributes. (+5 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (10): _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, ExitCodeTests, Report shaping and exit codes.  The sweep itself (which runs the pipeline over r, RenderTests (+2 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.36
Nodes (6): block(), cut(), page(), Recursive XY-cut tests (layout/segmenter.py)., A solid-ish blob: a horizontal line every 4px so every bin row is inked., TestXYCut

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.33
Nodes (3): denominator_from_c(), The 1:N denominator for a /Measure /X conversion factor., TestDenominatorFromC

### Community 120 - "TestNetworkQueries"
Cohesion: 0.19
Nodes (8): load_manifest(), The committed manifest, or an empty corpus when it is absent., CheckCorpusTests, The corpus verifier classifies each manifest sheet against the disk., check_corpus(), CorpusStatus, main(), Verify the downloaded corpus against the committed manifest.  Download is manual

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.07
Nodes (19): CommittedGroundTruthTests, ManifestHygieneTests, fixtures/MANIFEST.json is also tracked, and its `file` values are built     verb, Every committed ground-truth file obeys the rules., _strings(), MainExceptionIsolationTests, tools/review.py's main(): one sheet's unexpected failure must not kill the walk, DeliberateVerdictsTests (+11 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.19
Nodes (10): TruthItem, iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity(), IouTests (+2 more)

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
Cohesion: 0.22
Nodes (5): World-space window gates, pre-multiplied by the detection factor.      Exactly O, WindowGates, The one world-space gate, exercised at a non-grid angle.      A faithful 1:100 e, TestMinWidthNegativeControl, TestWindowGates

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
Nodes (35): bind_scale(), Resolve a scale for every floor-plan region on one page., The scale governing one region, or None.      `viewports` must arrive smallest-b, resolve_page_scales(), _cache_file(), _from_dicts(), load_stored(), match_stored() (+27 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.24
Nodes (5): Split a page into drawing regions. Returns [] for a page with no vector     ink, segment_page(), PageData, TestSegmentPage, TestStageTimingLogs

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.09
Nodes (9): TestCase, Path, Skip helper for tests that need a real corpus sheet.  Corpus knowledge lives in, Return the sheet's path, or skip the test with an actionable message., require_sheet(), LoaderTests, The corpus loader resolves slugs against the committed manifest.  Every test bui, End-to-end regression: floor-plans.pdf must yield exactly the four     ground-tr (+1 more)

### Community 135 - "DoorAssemblyTests"
Cohesion: 0.31
Nodes (3): parse_measure_viewports(), Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.      The bbox is le, TestParseMeasureViewports

### Community 136 - "client.py"
Cohesion: 0.12
Nodes (19): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+11 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.20
Nodes (11): _bridge_white_runs(), _equivalent_sides(), (short, long) of the rectangle with this polygon's area and perimeter.      The, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      gate, _bridge_white_runs is detect_rooms's ONLY production call site     (detection/ro, TestBridgeWhiteRunsGapScaling, Wall-network builder tests (detection/walls.py).  Synthetic PathPrimitive fixtur, Accepted hollow-wall/joinery _FillRing over the given rectangle. (+3 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.18
Nodes (3): HygieneRuleTests, Committed ground truth must not carry property-identifying text.  Ground truth r, The rules catch what they claim to catch.

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
Cohesion: 0.25
Nodes (5): _clip_cut(), Widest fully-empty internal run of at least min_bins. Leading and     trailing r, First clip edge lying strictly inside the span with ink on both sides.      An e, _widest_gap(), TestProfileHelpers

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.12
Nodes (16): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+8 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.14
Nodes (15): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., Document, render_page_png(), _candidate_to_dict(), collect_warnings(), _entity_to_dict() (+7 more)

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 148 - "count_paths_in"
Cohesion: 0.11
Nodes (12): can_prompt(), parse_answer(), prompt_for_scale(), Tier 4 input — ask the user, but only when someone is there to answer.  batch_ex, True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream (+4 more)

### Community 149 - "TestExtractPageFrame"
Cohesion: 0.18
Nodes (6): Every primitive, span AND image must land in the declared frame., A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestExtractPageFrame, write_rotated_pdf()

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.15
Nodes (20): Tunable constants for page segmentation.  Values are measured, not guessed — see, InkMap, Binary ink occupancy map over a page, used to find whitespace gutters., bins[row][col] is 1 where drawn ink falls, 0 elsewhere., _centre_in(), _col_profile(), count_paths_in(), _edge_gap_sq() (+12 more)

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
Cohesion: 0.14
Nodes (12): path(), A real window's glazing band is clear glass — nothing between the panes.     An, Control: the bare 2-line capped opening with an empty band interior is         s, 5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two         wall, Insulation hatch drawn with pure line segments (no re/qu/c): the         diagona, Decorations OUTSIDE the pane band (here, well beyond a cap along the         run, Regression (the bug this gate first introduced): a 45-deg window must         no, The gate works in the rotated frame too: a 45-deg insulation-hatched         wal (+4 more)

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.16
Nodes (13): Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, Scale coordinates by s, keep stroke widths — a 1:100 export., A closed 400x300 room drawn as four double-line wall bands., room_box_walls(), rooms_for(), shrink(), TestOrchestratorForwardsFactor, TestRoomsScaled (+5 more)

### Community 157 - "apply_classification"
Cohesion: 0.17
Nodes (11): 1. Factor computation (`scale` package), 2. Plumbing, 3. Constant classification, 4. Interactions to preserve (invariants across scales), 5. Testing, 6. Rejected alternatives (full reasoning in findings doc §5), Acceptance criteria, Design (+3 more)

### Community 159 - "_segments_min_distance"
Cohesion: 0.33
Nodes (4): fill_ring(), Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi, TestBarrierAllowlist

### Community 160 - "TestRequestShape"
Cohesion: 0.10
Nodes (20): 1. The premise, verified, 2. Corpus scale census (measured 2026-08-12), 3. Does scale mismatch explain the bad sheets? Partially., 4. Constant classification table, 4b. Measurements (2026-08-12), 4c. Measurement-harness traps (2026-08-13), 4d. Door constant classification table (frozen 2026-08-13), 4e. Window constant classification table (frozen 2026-08-13) (+12 more)

### Community 161 - "SweepSlugsArgumentTests"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Wall/Room Gates Implementation Plan, Self-review notes (already applied), Task 1: `detection_scale()` — the factor computation, Task 2: Measure the uncertain-class constants (no production code), Task 3: `WallGates` — scale the wall-network world-space gates, Task 4: `RoomGates` — scale the room-stage world-space gates, Task 5: Plumb the factor through orchestrator, pipeline, and summary (+1 more)

### Community 162 - "TestNetworkQueries"
Cohesion: 0.19
Nodes (7): qualifying_clip_rects(), Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, This sheet carries full-page border rules. With the span filter applied     the, segment(), TestGoldenSegmentation, TestSpanFilterIsLoadBearing

### Community 163 - "_double_arc"
Cohesion: 0.05
Nodes (50): _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, _split_double_arc(), _trim_chain_extension_caps() (+42 more)

### Community 164 - "SplitDoubleArcTests"
Cohesion: 0.24
Nodes (4): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, DoorV2OpeningCheckTests, Tests for v2 bridge-line opening check and arc sweep estimation.

### Community 165 - "ScaleInfo"
Cohesion: 0.22
Nodes (14): One drawing on a sheet, found by whitespace segmentation.      bbox is 150-DPI p, Region, _page_summary_dict(), PageRegionResult, detection_scale(), DetectionScale, _effective_denominator(), One detection factor per page: which scale governs the ink detection sees.  Dete (+6 more)

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "test_scale_units.py"
Cohesion: 0.24
Nodes (6): page(), prim(), Quarter-arc + a double-line leaf, as a faithful export at any scale.      radius, swing_door(), TestFaithfulExportDetection, TestOrchestratorWiring

### Community 168 - "scales_in_text"
Cohesion: 0.21
Nodes (3): Every 1:N denominator stated in one string, in the order written., scales_in_text(), TestScalesInText

### Community 169 - "File Structure"
Cohesion: 0.13
Nodes (14): File Structure, Floor Plan Scale Extraction Implementation Plan, Global Constraints, Self-Review, Task 10: Corpus expectations, Task 1: Units and the `ScaleInfo` model, Task 2: Tier 1 — viewport parsing, Task 3: Tier 2 — text parsing (+6 more)

### Community 170 - "transform_scale"
Cohesion: 0.20
Nodes (9): Baseline comparison — feat/scale-aware-wall-room-gates vs pre-branch (b0e705a), Identity verdict — the four factor-1.0 / 1:50 sheets (s02, s04, s14, s11), s02 (1:50, reference sheet) — LOST confirmed schedule, s04 (1:50) — 2 RETURNED false positives, s06 (1:100, scale-affected) — 1 LOST confirmed room, s06 / s12 verdict, s11 (unresolved → factor 1.0) — 2 new REVIEW doors + 3 RETURNED FPs, s12 (1:100, scale-affected) — 1 LOST confirmed room (+1 more)

### Community 171 - "test_curve_arc_garden_doors.py"
Cohesion: 0.20
Nodes (7): fill_ring(), marker_ring(), Closed filled rectangle exploded into 4 chained `l` items., Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFillClassRating, TestMarkerRings

### Community 172 - "TestOpeningSeals"
Cohesion: 0.31
Nodes (5): BBox, Convert a raw /VP bbox into 150-DPI pixel space.      Two steps, in this order., viewport_bbox_to_px(), The /VP bbox is raw PDF: y-up, bottom-left origin. Everything else in     the pi, TestViewportBboxToPx

### Community 173 - "MainExceptionIsolationTests"
Cohesion: 0.52
Nodes (6): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., Namespace

### Community 175 - "TestThickMaterialPairs"
Cohesion: 0.11
Nodes (20): _building_masses(), detect_rooms(), _folding_chain_gap_plug(), _free_space_components(), Room detection: rooms are the connected free-space components between walls.  Ea, World-space room gates pre-multiplied by the detection factor     (areas by fact, Fraction of a bbox area covered by the text spans lying over it., Bbox short-end edges of a sliding door: across the wall, never wall plane. (+12 more)

### Community 176 - "TestSlugForPath"
Cohesion: 0.38
Nodes (4): open_v_door(), open_v (detection/doors/folding.py::_open_v_match) reads three gates:     gates., A lone half-open bifold V (folding.py's open_v pattern): two double-line     obl, TestFoldingScaleBehavior

### Community 179 - "TestWindowTightPairInterior"
Cohesion: 0.25
Nodes (5): The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si, 5-1133 window_0016/0017: a step in a solid-filled wall block — the         step', 5-1133 window_0022 (real diagonal 2-pane window): its band sits at         the c, TestWindowTightPairInterior

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **432 isolated node(s):** `storage`, `sheets`, `Project purpose`, `Algorithm reference`, `Commands` (+427 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **62 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `arcs.py` to `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `TestExtractImagesInstances`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `_dedupe_openings`, `Double-Arc Split Tests`, `TestWindowArbitraryAngle`, `Room Polygonization Internals`, `Arc Cap-Trim Tests`, `wall_band_v`, `Arc Cycle-Cap Pruning Tests`, `geometry.py`, `TestAnnotationPenBarriers`, `hline`, `TestWindowTightPairInterior`, `TestBlindWindowPocket`, `_segments_min_distance`, `detect_windows`, `_double_arc`, `SplitDoubleArcTests`, `_projected_interval`, `renderer.py`, `plumber.py`, `test_scale_units.py`, `_collect_wall_faces`, `batch_extract.py`, `test_curve_arc_garden_doors.py`, `renderer.py`, `TestNetworkQueries`, `TestThickMaterialPairs`, `TestSlugForPath`, `_dedupe_openings`, `TestBlindWindowPocket`, `TestWindowTightPairInterior`, `TestFloorPlansRegression`, `wall_band_h`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `_find_openings`, `app.py`, `qualifying_clip_rects`, `_segments_min_distance`?**
  _High betweenness centrality (0.150) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Arc Cap-Trim Tests` to `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `TestExtractImagesInstances`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `TestWindowArbitraryAngle`, `Arc Cycle-Cap Pruning Tests`, `test_extraction_transform.py`, `_fit_circle_3pt`, `hline`, `TestWindowTightPairInterior`, `_segments_min_distance`, `SplitDoubleArcTests`, `ScaleInfo`, `batch_extract.py`, `TestThickMaterialPairs`, `TestWindowTightPairInterior`, `TestFloorPlansRegression`, `wall_band_h`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `_find_openings`, `app.py`, `_segments_min_distance`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `Arc Cap-Trim Tests` to `Window Detection & Tests`, `Door Detection & Tests`, `test_layout_segmenter.py`, `Wall Cross-Validation`, `TestExtractImagesInstances`, `Debug Trace Collector`, `EntranceDoorTests`, `Room Detection Tests`, `Wall Network Construction & Tests`, `wall_band_v`, `test_extraction_transform.py`, `arcs.py`, `hline`, `_segments_min_distance`, `detect_windows`, `_projected_interval`, `ScaleInfo`, `SplitDoubleArcTests`, `renderer.py`, `scales_in_text`, `TestThickMaterialPairs`, `TestFloorPlansRegression`, `TestWindowInteriorClutter`, `DoorV2OpeningCheckTests`, `detect_doors`, `app.py`, `qualifying_clip_rects`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 100 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 100 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `PageData` (e.g. with `InkMap` and `PageRegionResult`) actually correct?**
  _`PageData` has 49 INFERRED edges - model-reasoned connections that need verification._