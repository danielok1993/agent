# Graph Report - agent  (2026-09-05)

## Corpus Check
- 296 files · ~704,216 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4920 nodes · 12355 edges · 255 communities (179 shown, 76 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 951 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1b34bdeb`
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
- [[_COMMUNITY__check_opening_clear|_check_opening_clear]]
- [[_COMMUNITY_Regression Testing — Working Guide|Regression Testing — Working Guide]]
- [[_COMMUNITY_test_extraction_transform.py|test_extraction_transform.py]]
- [[_COMMUNITY_Detection Review Tooling V1 — Implementation Plan|Detection Review Tooling V1 — Implementation Plan]]
- [[_COMMUNITY_RunDirTests|RunDirTests]]
- [[_COMMUNITY_resolver.py|resolver.py]]
- [[_COMMUNITY__arc|_arc]]
- [[_COMMUNITY_TestAnnotationPenBarriers|TestAnnotationPenBarriers]]
- [[_COMMUNITY_normalize_bbox|normalize_bbox]]
- [[_COMMUNITY_review.py|review.py]]
- [[_COMMUNITY_viewport_bbox_to_px|viewport_bbox_to_px]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_apply_classification|apply_classification]]
- [[_COMMUNITY_MANIFEST.json|MANIFEST.json]]
- [[_COMMUNITY_test_layout_segmenter.py|test_layout_segmenter.py]]
- [[_COMMUNITY_TestRequestShape|TestRequestShape]]
- [[_COMMUNITY_SweepSlugsArgumentTests|SweepSlugsArgumentTests]]
- [[_COMMUNITY_TestSwingHingePlugRestriction|TestSwingHingePlugRestriction]]
- [[_COMMUNITY__double_arc|_double_arc]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
- [[_COMMUNITY_ScaleInfo|ScaleInfo]]
- [[_COMMUNITY_Architecture|Architecture]]
- [[_COMMUNITY_PruneArcSpursTests|PruneArcSpursTests]]
- [[_COMMUNITY_TestWindowTopology|TestWindowTopology]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_transform_scale|transform_scale]]
- [[_COMMUNITY_path|path]]
- [[_COMMUNITY_DoorV2OpeningCheckTests|DoorV2OpeningCheckTests]]
- [[_COMMUNITY_test_layout_golden.py|test_layout_golden.py]]
- [[_COMMUNITY_analyze.py|analyze.py]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_PageTruth|PageTruth]]
- [[_COMMUNITY__vector_text_indices|_vector_text_indices]]
- [[_COMMUNITY_cluster_denominators|cluster_denominators]]
- [[_COMMUNITY_Step 5 — Per-scale-group detection for mixed-scale pages|Step 5 — Per-scale-group detection for mixed-scale pages]]
- [[_COMMUNITY_test_window_detection.py|test_window_detection.py]]
- [[_COMMUNITY_Step 1 — Widen the door Bezier aspect gate|Step 1 — Widen the door Bezier aspect gate]]
- [[_COMMUNITY_Step 2 — Retune the window span-overshoot gate (paper-space FP kill)|Step 2 — Retune the window span-overshoot gate (paper-space FP kill)]]
- [[_COMMUNITY_Step 3 — Diagnose s15's 82 false positives (read-only)|Step 3 — Diagnose s15's 82 false positives (read-only)]]
- [[_COMMUNITY_Step 4 — Recall audit on the 1100 sheets (misses are invisible to ground truth)|Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth)]]
- [[_COMMUNITY_TestXYCut|TestXYCut]]
- [[_COMMUNITY_TestCheckDoorLeaves|TestCheckDoorLeaves]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY_TestLeafWidth|TestLeafWidth]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_TestCrossWindowToleranceUnscaled|TestCrossWindowToleranceUnscaled]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_Handoff W-gate recalibration (the proper fix behind `fixmeasured-scale-detection-factor`)|Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)]]
- [[_COMMUNITY_EntranceDoorTests|EntranceDoorTests]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY__is_light_pen|_is_light_pen]]
- [[_COMMUNITY_TestSheetSize|TestSheetSize]]
- [[_COMMUNITY_File structure|File structure]]
- [[_COMMUNITY_SplitDoubleArcTests|SplitDoubleArcTests]]
- [[_COMMUNITY_HygieneRuleTests|HygieneRuleTests]]
- [[_COMMUNITY_PruneUnreadPageOutputTests|PruneUnreadPageOutputTests]]
- [[_COMMUNITY_parse_answer|parse_answer]]
- [[_COMMUNITY_DoorAssemblyTests|DoorAssemblyTests]]
- [[_COMMUNITY_test_through_hatch_band.py|test_through_hatch_band.py]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_test_sliding_doors.py|test_sliding_doors.py]]
- [[_COMMUNITY_W-gate iteration 3 — step 1 the far-side density rule (was mark-class rule)|W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule")]]
- [[_COMMUNITY_PruneUnreadPageOutputTests|PruneUnreadPageOutputTests]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_denominator_from_c|denominator_from_c]]
- [[_COMMUNITY_test_batch_extract.py|test_batch_extract.py]]
- [[_COMMUNITY_TestFarSidePairs|TestFarSidePairs]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY_TestWindowGates|TestWindowGates]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestFarSidePairs|TestFarSidePairs]]
- [[_COMMUNITY__covers|_covers]]
- [[_COMMUNITY_MainExceptionIsolationTests|MainExceptionIsolationTests]]
- [[_COMMUNITY_TestDashRowDiscriminators|TestDashRowDiscriminators]]
- [[_COMMUNITY_TakeoffRequest|TakeoffRequest]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_W-gate recalibration, iteration 2 — checkpoint Group 2 (thin-margin moves)|W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves)]]
- [[_COMMUNITY_squat_cap_window|squat_cap_window]]
- [[_COMMUNITY_TestMinWidthReference|TestMinWidthReference]]
- [[_COMMUNITY_NotFound|NotFound]]
- [[_COMMUNITY_bezier_arc|bezier_arc]]
- [[_COMMUNITY_TestWindowSpanOvershootRetune|TestWindowSpanOvershootRetune]]
- [[_COMMUNITY_W-gate recalibration — iteration 1 the census (2026-09-04)|W-gate recalibration — iteration 1: the census (2026-09-04)]]
- [[_COMMUNITY_W-gate recalibration, iteration 2 — checkpoint Group 1 (safe reference moves)|W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)]]
- [[_COMMUNITY_attrib_rooms.py|attrib_rooms.py]]
- [[_COMMUNITY_W-gate iteration 3 — step 2 the seal-15 sites measured; the corner door lining (was hinge-less swing-side veto)|W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto")]]
- [[_COMMUNITY_.collect|.collect]]
- [[_COMMUNITY_W-gate iteration 3 — step 3 the short-piece material rule measured; nothing to build, and what actually holds s01 at its true scale|W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale]]
- [[_COMMUNITY_ablate.py|ablate.py]]
- [[_COMMUNITY_resolve_page_regions|resolve_page_regions]]
- [[_COMMUNITY_TestBandPocket|TestBandPocket]]
- [[_COMMUNITY_artifacts.py|artifacts.py]]
- [[_COMMUNITY_mult_summary.py|mult_summary.py]]
- [[_COMMUNITY_render_page_svg|render_page_svg]]
- [[_COMMUNITY_swing_door|swing_door]]
- [[_COMMUNITY_TestWindowGates|TestWindowGates]]
- [[_COMMUNITY_TestCliEquivalence|TestCliEquivalence]]
- [[_COMMUNITY_Takeoff as a Firebase Function — design|Takeoff as a Firebase Function — design]]
- [[_COMMUNITY_migrate-labour-rates-to-groups.ts|migrate-labour-rates-to-groups.ts]]
- [[_COMMUNITY_estimate-pdf-service.ts|estimate-pdf-service.ts]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_auth.tsx|auth.tsx]]
- [[_COMMUNITY_Deploying the takeoff callable|Deploying the takeoff callable]]
- [[_COMMUNITY_FakeBlob|FakeBlob]]
- [[_COMMUNITY_FakeDoc|FakeDoc]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 291 edges
2. `Candidate` - 183 edges
3. `PageData` - 177 edges
4. `TextSpan` - 156 edges
5. `detect_wall_network()` - 139 edges
6. `Region` - 116 edges
7. `PageScales` - 94 edges
8. `ScaleInfo` - 91 edges
9. `rooms_for()` - 85 edges
10. `detect_windows()` - 79 edges

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

## Communities (255 total, 76 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.23
Nodes (5): Path, Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, write_review_overlays(), Review images: one per page per entity type, ids stamped on., ReviewOverlayTests

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.07
Nodes (30): _component_indices(), _dedupe_door_components(), Prefer the strongest door when two candidates use the same primitives., CrossGates, World-space cross-validation gates, pre-multiplied by the factor.      Only the, Drop window candidates that materially sit on a detected door.      Door symbols, True when ``win`` stands beyond ``door``'s hinge-side jamb in the door's     own, _resolve_door_window_conflicts() (+22 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.13
Nodes (16): _attach_text_spans(), page_fallback_region(), Grow paths-only boxes to absorb the text spans beside them.      The tier-2 cut, Split a page into drawing regions. Returns [] for a page with no vector     ink, The whole page as a single region, for sheets too dense to split., segment_page(), PageData, Segment the page, classify its regions, and decide what detection sees.      cla (+8 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.06
Nodes (51): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _draw_regions(), _load_font(), BBox (+43 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.08
Nodes (27): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+19 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.13
Nodes (11): _clip_cut(), Strip empty margins; returns absolute (start, end) bin indices., Widest fully-empty internal run of at least min_bins. Leading and     trailing r, First clip edge lying strictly inside the span with ink on both sides.      An e, _trim(), _widest_gap(), cut(), page() (+3 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.07
Nodes (30): compute_takeoff(), _largest_polygon(), OpeningTakeoff, Polygon, compute_takeoff — the pure core: rooms + scale + heights → metres.  No I/O, no p, A Polygon from whatever shapely returned; MultiPolygon → its largest part., One physical door or window, once. A shared opening carries both room     ids ra, _room_polygon() (+22 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.11
Nodes (19): _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests (+11 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.05
Nodes (41): _collect_fill_rings(), detect_wall_network(), _fill_key(), _fill_seam_indices(), _fill_seams(), Path indices of fill-ring seams — see _fill_seams., (seam path indices, ring-id pairs sharing a seam).      Path indices of fill-rin, Build the internal wall-centerline network for a page.      exclude_path_indices (+33 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.05
Nodes (41): apply_classification(), build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+33 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record whether a line segment passed the polyline-arc length filter., Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+5 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.07
Nodes (28): detect(), fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack(), ParkedStackPairTests (+20 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.08
Nodes (19): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Run extract command for a single PDF.     Returns (pdf_path, success: bool, outp, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive). (+11 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.13
Nodes (16): assigned_path_fraction(), _centre_in_any(), filter_page_data(), BBox, Reduce a PageData to the primitives inside a set of regions.  This filters, it d, A copy of page_data holding only primitives whose bbox centre falls in     one o, Share of the page's paths that any region would keep.      Deliberately the same, Text spans inside the given regions. Used to scope schedule detection to     sch (+8 more)

### Community 17 - "arcs.py"
Cohesion: 0.11
Nodes (8): prim(), quarter_bezier(), A quarter-arc cubic Bezier of radius r, hinged at (cx, cy).      r is a WORLD ex, TestArcGatesThreading, TestDoorGatesConstruction, TestFoldingGatesThreading, TestLeafGatesThreading, TestSlidingGatesThreading

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
Cohesion: 0.09
Nodes (57): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some, Estimate sweep angle of a Bézier arc from its endpoints and estimated center. (+49 more)

### Community 22 - "geometry.py"
Cohesion: 0.08
Nodes (24): apply_labels(), build_request_text(), collect_room_spans(), is_grounded(), is_noise_span(), label_rooms(), The one user part: every room's spans as JSON, keyed by ordinal., True when every word of the label appears in that room's own spans.      This ma (+16 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.16
Nodes (10): load_manifest(), The committed manifest, or an empty corpus when it is absent., Flip a manifest entry's `labeled` flag and write the manifest back.      `labele, set_labeled(), CheckCorpusTests, The corpus verifier classifies each manifest sheet against the disk., check_corpus(), CorpusStatus (+2 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.05
Nodes (25): attrib.py <slug> <x0> <y0> <x1> <y1> FIELD=MULT [FIELD=MULT ...]  Runs the harne, attrib_rooms.py <slug> FIELD=MULT [...]: for each config (each alone on top of t, COLLINEAR_OFFSET_TOL forms, measured with the census harness on top of the curre, crop_dash.py <slug> <name> X0 Y0 X1 Y1 [...]: crop the latest sweep render with, denom_at(), _install_taps(), load(), mm() (+17 more)

### Community 35 - "plumber.py"
Cohesion: 0.14
Nodes (11): Client, init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-, _door_attribute_overlay(), finalize_candidates(), Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, Promote candidates to entities, applying the offline confidence floors.      Gem, cand() (+3 more)

### Community 36 - "_projected_interval"
Cohesion: 0.14
Nodes (7): _hface(), A bare horizontal wall-face _Seg for isolated merge-tolerance tests., Isolates _merge_collinear_segs's offset-tolerance scaling directly —     the exa, TestMergeCollinearOffsetScaling, TestWallGatesConstruction, WALL_THROUGH_HATCH_MAX_PX is 72px — 610mm at 1:50 (W-gate census     2026-09-04), ThroughHatchCapReferenceTests

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.16
Nodes (10): build_ink_map(), NestedFrameTests, page(), path(), Ink occupancy map tests (layout/occupancy.py)., Sheet furniture nested inside the page frame — a drawing frame or a     title-bl, span(), TestBuildInkMap (+2 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.20
Nodes (10): opening_dict(), The whole page as one document., One door or window. `room_ids` is empty when it reached no room;     `dropped_ro, to_document(), _door(), _page(), The takeoff.json document (takeoff/document.py)., _room() (+2 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.09
Nodes (22): _collect_material_marks(), _dash_row_indices(), _is_dashed(), _pen_key(), True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., Path indices of drawn dash lines: annotation, never faces.      A dashed line ty, (midpoint, angle) of every short solid stroke, gathered once per page.      Thes, Quantized stroke color — the pen identity of a drawn line. (+14 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.15
Nodes (12): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 1c. Bay / corner frames — the square corner post (s10 lounge), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf (+4 more)

### Community 44 - "renderer.py"
Cohesion: 0.22
Nodes (15): DetectionPage, load_detection_pages(), One corpus sheet's detection page data, exactly as tools/regress.py sees it.  Sh, Every detected page of the sheet (or only `pages`, 1-based)., sheet_pdf(), dump(), _fmt_face(), _fmt_seg() (+7 more)

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.17
Nodes (10): _layer_annotation_veto(), _layer_classes(), _layer_hint_from_layer(), _layer_strong_prior(), _layer_tokens(), True when the layer name marks its ink as annotation (callouts,     dimensions,, The element classes named by a layer's tokens., Return a high confidence boost when a layer name conclusively names the type. (+2 more)

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.17
Nodes (11): Diagnosis (measured 2026-08-13, this is the evidence the plan argues from), Global Constraints, Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan, Self-Review, Task 0: Branch setup, Task 1: `build_ink_map(include_text=...)`, Task 2: Extract `_boxes_from_cut` (pure refactor), Task 3: `_attach_text_spans` (+3 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.07
Nodes (59): _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg(), _open_v_match() (+51 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.20
Nodes (4): Rect room with a 45px doorway gap in the top wall (240..285)., TestClosedRooms, wall_band_h(), wall_band_v()

### Community 103 - "PathPrimitive"
Cohesion: 0.20
Nodes (11): pending(), Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk., ReviewBlocked, SweepOutputMissing, SweepOutputStale (+3 more)

### Community 104 - "detect_doors"
Cohesion: 0.12
Nodes (24): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+16 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.10
Nodes (15): iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity(), IouTests, MatchTests (+7 more)

### Community 107 - "vline"
Cohesion: 0.06
Nodes (31): _check_opening_clear(), _line_nears_bridge_interior(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, True when some point of segment p1-p2 lies within buffer_px of the bridge     li, detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, One wall centerline segment (pixel space, y-down)., WallSegment (+23 more)

### Community 108 - "_bridge_white_runs"
Cohesion: 0.29
Nodes (13): _along(), analyse_run(), _frame(), _line_offset_at(), main(), _offset(), Measure the collinear merge's ANCHOR on a corpus sheet — the diagnostic behind ", The support population: strong stroked faces and wall-fill outlines. (+5 more)

### Community 109 - "_find_openings"
Cohesion: 0.14
Nodes (14): One fixture per paper-space family (spec §Testing). Each fails if its     named, TestPaperInvariance, hline(), horizontal_window(), A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two, 5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is         fa, Three parallel lines with no perpendicular end-caps (e.g. a run of         dimen, Three parallel lines spaced far apart (e.g. stair treads) exceed the         gla (+6 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.19
Nodes (6): DetectionScale, _door(), room_polys holds unscaled rooms too, so the first assigned room can         be t, Referential integrity must hold in BOTH directions: if the opening         names, _room(), TestComputeTakeoff

### Community 111 - "app.py"
Cohesion: 0.04
Nodes (105): _angle_diff_mod180(), _line_angle_deg(), _line_length(), _perpendicular_spacing(), _project_onto_axis(), _projected_interval(), Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars., Scalar projection of p onto the unit axis (dx, dy) from origin. (+97 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.20
Nodes (10): Path, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door(), The verdict writer: selections in, ground truth out.  Everything here is synthet (+2 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.06
Nodes (41): bind_scale(), binding_texts(), _caption_distance(), _centroid(), _contains(), The scale governing one region, or None.      `viewports` must arrive smallest-b, Resolve a scale for every floor-plan region on one page.      `fallback` is a sc, How far a text span sits from a region, or None if it is not near it.      Horiz (+33 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.13
Nodes (12): clip_cut_positions(), BBox, qualifying_clip_rects_from_boxes(), Native PDF clip rects, used as extra cut hints for the segmenter.  Clip rects ar, Keep only clips that look like real drawing boundaries.      Measured on the sam, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi, Tunable constants for page segmentation.  Values are measured, not guessed — see, dot() (+4 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.16
Nodes (10): _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, ExitCodeTests, Report shaping and exit codes.  The sweep itself (which runs the pipeline over r, RenderTests (+2 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.06
Nodes (32): Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan., The resolution ladder, and how a scale binds to a floor plan.  Binding is what m, _stored_info(), Tier 2 — the scale a sheet prints as text.  Three corpus sheets carry no viewpor, canonical_denominators(), cluster_denominators(), denominator_from_c(), format_scale() (+24 more)

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.08
Nodes (39): _accept_jamb_rings(), _building_masses(), _clip_plug_tails(), _contains_text(), detect_rooms(), _drop_window_exterior_sides(), _folding_chain_gap_plug(), _free_space_components() (+31 more)

### Community 120 - "TestNetworkQueries"
Cohesion: 0.18
Nodes (7): door_candidate(), Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, rooms_for(), TestBboxSealFloor, TestOpeningSeals, TestPhantomDoorSeals

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.16
Nodes (8): Measured scale expectations across the regression corpus.  Every number was meas, s13 is the one corpus sheet whose viewport and printed scale disagree.      It m, The resolver-level assertion: a region sitting inside the measuring         view, read(), TestKnownConflict, TestSheetsWithNoRecoverableScale, TestTextScales, TestViewportScales

### Community 123 - "batch_extract.py"
Cohesion: 0.15
Nodes (12): 1. The hall: it IS the seal — step 8's "the leak is elsewhere" was a misread, 1b. The jamb-seeking tail, measured before building — the COLLINEAR seek refuted, a MATERIAL seek is the rule (corrected after review), 2. The 17 phantoms: s01's furniture pen crosses the wall-pen fraction gate, 3. The three stair-split rooms — unchanged, the user's call, Numbers, Pictures in this directory (none shows an address), Residue / not in scope (one line each), Review (2026-09-05, an independent agent, `step-9-review-prompt.md`) (+4 more)

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.09
Nodes (21): door_open_leaf_path_indices(), Path indices of swing doors' OPEN leaf linework.      A swing door's leaf is dra, Whether a path's segments are DRAWN lines, as opposed to the boundary     of a f, _stroke_is_visible(), detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re, Per-stage wall-clock log line. Detection on 100k+-path sheets runs for     minut, run_heuristics() (+13 more)

### Community 126 - "_segments_min_distance"
Cohesion: 0.11
Nodes (12): _door_plugs(), _open_leaf_edges(), Bbox edges of a garden-layout double door that are room floor, not wall.      A, Thin barrier bands along the wall planes through a detected door.      The door, Interrupted-run plugs need jambs that REACH the plug band and a mid     that is, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto., ROOM_OPENING_SEAL_PX is 15px (127mm at 1:50; W-gate iteration 3 step     7, 2026, Plug extensions end at their supporting material; slide ends veto.      Geometry (+4 more)

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
Cohesion: 0.14
Nodes (19): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, One merged wall-face run with the evidence its members carried., WallFace, continuous_h_wall(), door(), face(), h_wall_with_gap() (+11 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.38
Nodes (10): collect_sheets(), has_floor_plan(), is_unclassified(), page_dirs(), Path, Turning a finished run_extract output tree into wire sheets.  Only pages the reg, True when nothing on the page carries a classification.      pipeline.resolve_pa, _read_json() (+2 more)

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.43
Nodes (7): diff_slug(), _geom(), _iou(), _latest(), _load(), main(), Every-room polygon diff between a compare_sweeps snapshot (outputs/regress_basel

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.12
Nodes (16): bay_corner_post_window(), framed_triple_window(), quad(), Window detection tests.  Ground truth was established interactively on s01 (form, 5-1133 W8: a three-light frame tagged with a single label. Two full-span     rai, s04 BATHROOM 01 outer-wall window (paths 60-65, 0.56px A-DETL): the     opening, A squat frame block (aspect 1.0-1.8, the crosshatch-box range) is a     jamb onl, s10 lounge bay, top frame (paths 11651/11653/11658/11659/11661).      A bay turn (+8 more)

### Community 135 - "DoorAssemblyTests"
Cohesion: 0.22
Nodes (8): 3a — per-band hatch-mark cap, then `WALL_THICK_MATERIAL_MAX_PX` 48 → 56 (shipped), 3b — `COLLINEAR_OFFSET_TOL` as paper-with-ceiling (measured; no code change), 3c — `ROOM_PLUG_HALF_WIDTH_PX` paper floor (shipped), Fast tier, Final iteration — s01mode on the final tree (`tools/census_scratch/ablate.py s01 s01mode`), Numbers, Reseed, W-gate recalibration, iteration 2 — checkpoint: Group 3 (class fixes)

### Community 136 - "client.py"
Cohesion: 0.24
Nodes (4): _prune_unread_page_output(), Delete the page-level files a sweep persists but never uses.      Making sweep o, PruneUnreadPageOutputTests, A fake run directory stands in for a real extraction (fast tier, no     pipeline

### Community 137 - "_dedupe_openings"
Cohesion: 0.12
Nodes (11): qualifying_clip_rects(), Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, Load-bearing golden for SEGMENT_MAX_DEPTH = 7: at 6 the first-floor     plan and, This sheet carries full-page border rules. With the span filter applied     the, s15 measured 2026-08-13: 214 text spans bridge every gutter, so the     text-inc, segment(), TestGoldenSegmentation (+3 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.09
Nodes (15): _collect_wall_faces(), _rate_fill_classes(), Classify each fill color as wall material (True) or furniture (False).      Vect, Return (stroked wall faces, filled-band centerlines)., Annotation arrowhead: a tiny filled triangle or concave dart.          Walls are, fill_ring(), marker_ring(), Filled triangle/dart exploded into chained `l` items (a leader tip). (+7 more)

### Community 140 - "ShaMismatchAgainstTruthTests"
Cohesion: 0.10
Nodes (36): manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, sha256_of(), sheet_entry(), sheet_path() (+28 more)

### Community 141 - "File Structure"
Cohesion: 0.12
Nodes (15): File Structure, Global Constraints, Phase 3 — corpus labeling (not a task), Regression Corpus Implementation Plan, Slug Assignment (authoritative — used by Tasks 2 and 3), Task 10: Seed s01 ground truth and document the labeling loop, Task 1: Corpus loader, Task 2: Migrate the sheets into the fixtures layout (+7 more)

### Community 142 - "Regression Corpus — Design"
Cohesion: 0.12
Nodes (15): Adoption — `tools/add_sheet.py`, Architecture, Constraints, Fixture layout, Ground truth, Naming, Non-goals, Phasing (+7 more)

### Community 143 - "_check_opening_clear"
Cohesion: 0.15
Nodes (13): _band_interior_clutter(), _cap_orientation_frames(), detect_windows(), _frame_axes(), _merge_mullion_chains(), Caps grouped by direction into overlapping frames, each ``(center, caps)``., Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C, Join collinear glazing segments across mullion blocks into logical panes.      A (+5 more)

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.11
Nodes (17): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+9 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.16
Nodes (27): InkMap, bins[row][col] is 1 where drawn ink falls, 0 elsewhere., _boxes_from_cut(), _centre_in(), _chains_across(), _col_profile(), count_paths_in(), _edge_gap_sq() (+19 more)

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 147 - "RunDirTests"
Cohesion: 0.18
Nodes (4): LabeledFlagSweepIntegrationTests, End-to-end through sweep() for the two failing cases -- both exit via     `conti, Fix: an operator who pastes a fresh hash into the manifest instead of     adopti, ShaMismatchAgainstTruthTests

### Community 148 - "resolver.py"
Cohesion: 0.20
Nodes (6): The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si, 5-1133 window_0016/0017: a step in a solid-filled wall block — the         step', floor-plans true windows draw a narrow double glazing line (panes         1.75px, 5-1133 window_0022 (real diagonal 2-pane window): its band sits at         the c, TestWindowTightPairInterior

### Community 149 - "_arc"
Cohesion: 0.05
Nodes (51): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+43 more)

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.18
Nodes (10): hline(), path(), Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, Filled arrowhead triangle (a marker ring) pointing down at `tip`., Stairs are furniture to the room stage: a room polygon runs to the     enclosing, rect_room(), stair_arrowhead(), TestAnnotationPenBarriers (+2 more)

### Community 151 - "normalize_bbox"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Window Gates Implementation Plan, Task 1: `WindowGates` dataclass, Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`, Task 3: The W-row negative control at 50°, Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°, Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it, Task 6: Findings doc — §4e frozen table, §6 entries (+1 more)

### Community 153 - "viewport_bbox_to_px"
Cohesion: 0.10
Nodes (24): _dedupe_by_perp(), _facing_cap_pairs(), _find_openings(), _glaze_index(), World-space window gates, pre-multiplied by the detection factor.      Exactly O, Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Two-axis lookup structure over a frame's glazing pool.      Every cap pair asks (+16 more)

### Community 154 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Scale-Aware Door Detection Gates Implementation Plan, Self-Review, Task 1: `DoorGates` dataclass, Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point, Task 3: Thread gates through `leaves.py`, Task 4: Thread gates through `sliding.py` (+5 more)

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.14
Nodes (13): 1. Intake — extract the brief, 2. Orient — read before touching code, 3. Baseline and locate, 4. Diagnose — measure, don't guess, 5. Fix — test first, then code, then prose, 6. Sweep — target, references, then corpus, 7. CHECKPOINT — report and stop, 8. After the go-ahead (+5 more)

### Community 157 - "apply_classification"
Cohesion: 0.17
Nodes (11): 1. Factor computation (`scale` package), 2. Plumbing, 3. Constant classification, 4. Interactions to preserve (invariants across scales), 5. Testing, 6. Rejected alternatives (full reasoning in findings doc §5), Acceptance criteria, Design (+3 more)

### Community 159 - "test_layout_segmenter.py"
Cohesion: 0.13
Nodes (8): Every 1:N denominator stated in one string, in the order written., Every scale printed on the page, each carrying its span's bbox., scales_in_text(), text_scales(), Reading a 1:N scale out of text spans.  Every string below is copied verbatim fr, span(), TestScalesInText, TestTextScales

### Community 160 - "TestRequestShape"
Cohesion: 0.09
Nodes (21): 1. The premise, verified, 2. Corpus scale census (measured 2026-08-12), 3. Does scale mismatch explain the bad sheets? Partially., 4. Constant classification table, 4b. Measurements (2026-08-12), 4c. Measurement-harness traps (2026-08-13), 4d. Door constant classification table (frozen 2026-08-13), 4e. Window constant classification table (frozen 2026-08-13) (+13 more)

### Community 161 - "SweepSlugsArgumentTests"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Wall/Room Gates Implementation Plan, Self-review notes (already applied), Task 1: `detection_scale()` — the factor computation, Task 2: Measure the uncertain-class constants (no production code), Task 3: `WallGates` — scale the wall-network world-space gates, Task 4: `RoomGates` — scale the room-stage world-space gates, Task 5: Plumb the factor through orchestrator, pipeline, and summary (+1 more)

### Community 162 - "TestSwingHingePlugRestriction"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 163 - "_double_arc"
Cohesion: 0.33
Nodes (3): The function is a transport wrapper: run_extract must be called with     exactly, A new run_extract parameter whose default differs from what app.py         passe, TestExtractionOptions

### Community 165 - "ScaleInfo"
Cohesion: 0.09
Nodes (34): One drawing on a sheet, found by whitespace segmentation.      bbox is 150-DPI p, A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, Region, ScaleInfo, The per-region scale table printed after each page., scale_table(), detection_scale(), _effective_denominator() (+26 more)

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "PruneArcSpursTests"
Cohesion: 0.22
Nodes (12): Constants for the takeoff callable.  Runtime sizing is justified in the design d, _doc(), load_record(), mark_awaiting_review(), mark_awaiting_scale(), mark_failed(), mark_processing(), The takeoffs/{takeoffId} record: reading it, guarding it, moving its status.  Re (+4 more)

### Community 169 - "File Structure"
Cohesion: 0.13
Nodes (14): File Structure, Floor Plan Scale Extraction Implementation Plan, Global Constraints, Self-Review, Task 10: Corpus expectations, Task 1: Units and the `ScaleInfo` model, Task 2: Tier 1 — viewport parsing, Task 3: Tier 2 — text parsing (+6 more)

### Community 170 - "transform_scale"
Cohesion: 0.20
Nodes (9): Baseline comparison — feat/scale-aware-wall-room-gates vs pre-branch (b0e705a), Identity verdict — the four factor-1.0 / 1:50 sheets (s02, s04, s14, s11), s02 (1:50, reference sheet) — LOST confirmed schedule, s04 (1:50) — 2 RETURNED false positives, s06 (1:100, scale-affected) — 1 LOST confirmed room, s06 / s12 verdict, s11 (unresolved → factor 1.0) — 2 new REVIEW doors + 3 RETURNED FPs, s12 (1:100, scale-affected) — 1 LOST confirmed room (+1 more)

### Community 171 - "path"
Cohesion: 0.15
Nodes (12): diagonal_window(), path(), A real window's glazing band is clear glass — nothing between the panes.     An, Control: the bare 2-line capped opening with an empty band interior is         s, 5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two         wall, Insulation hatch drawn with pure line segments (no re/qu/c): the         diagona, Decorations OUTSIDE the pane band (here, well beyond a cap along the         run, Regression (the bug this gate first introduced): a 45-deg window must         no (+4 more)

### Community 173 - "test_layout_golden.py"
Cohesion: 0.08
Nodes (22): probe_box.py <slug> <seal> x0 y0 x1 y1 [door_id ...]  Run the harness at the giv, tap_fsc(), tap_gap(), draw_geom(), panel(), Checkpoint pictures for the _gate_denominator step (s01 identity vs 0.542):   1., print_profile(), profile() (+14 more)

### Community 174 - "analyze.py"
Cohesion: 0.14
Nodes (20): c_anchor_reach(), c_blind_window(), c_bridges(), c_collinear(), c_cross(), c_doors(), c_face_min_len(), c_fill() (+12 more)

### Community 175 - "TestThickMaterialPairs"
Cohesion: 0.08
Nodes (23): Approach, Cache and offline, Cost, Grounding is enforced in code, not just prompted, Out of scope, Pipeline position, Problem, Request and response (+15 more)

### Community 176 - "TestSlugForPath"
Cohesion: 0.22
Nodes (8): Global Constraints, takeoff.json Overlay Document Implementation Plan, Task 1: Move `scale_summary_dict` into `scale/resolver.py`, Task 2: Openings become page-level records, computed once, Task 3: Rooms carry geometry, and unscaled rooms are kept, Task 4: `takeoff/document.py` — the serialiser, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 177 - "_dedupe_openings"
Cohesion: 0.14
Nodes (21): FakeBucket, FakeDb, _make_extract(), A normally measured page: one scale, read off the sheet., A page the resolver could not read a scale for.      Rooms survive with their ge, A file that downloads but will not PARSE must warn and be skipped, the     same, /tmp is tmpfs charged against the 2 GiB memory budget, so peak usage     must be, pages: {page_number: (region_types, takeoff_dict | None)} (+13 more)

### Community 178 - "PageTruth"
Cohesion: 0.40
Nodes (4): Claims to verify, Deliverable, Environment rules (learned the hard way; do not skip), Review prompt — verify the step-9 claims independently

### Community 180 - "cluster_denominators"
Cohesion: 0.09
Nodes (18): _arc_radius(), assign_openings(), _bbox_edge_along_boundary(), _chord_length(), opening_width_px(), opening_width_px_from_evidence(), _positive(), Polygon (+10 more)

### Community 181 - "Step 5 — Per-scale-group detection for mixed-scale pages"
Cohesion: 0.29
Nodes (6): Acceptance (to refine in the spec), Process (binding), Step 5 — Per-scale-group detection for mixed-scale pages, The design sketch to start from (findings §6, verbatim intent), The problem, Why it is NOT a bolt-on (measured hazard)

### Community 182 - "test_window_detection.py"
Cohesion: 0.25
Nodes (14): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), inspect_pdf(), _page_type_styled(), print_candidates_tree(), print_file_header() (+6 more)

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
Cohesion: 0.05
Nodes (51): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., render_page_png(), Polygon, Ask Gemini for the name written inside each detected room.  One text-only call p, _room_polygon(), Entity (+43 more)

### Community 188 - "TestCheckDoorLeaves"
Cohesion: 0.31
Nodes (10): build_parser(), cmd_extract(), cmd_inspect(), main(), parse_page_spec(), positive_metres(), argparse type: a positive, finite height in metres., Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]. (+2 more)

### Community 189 - "TestWindowTightPairInterior"
Cohesion: 0.22
Nodes (6): fill_ring(), Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi, Exporters triangulate fills: a wall band arrives as two right     triangles shar, TestBarrierAllowlist, TestTriangulatedFillRings

### Community 190 - "TestSlugForPath"
Cohesion: 0.07
Nodes (21): parse_measure_viewports(), BBox, Convert a raw /VP bbox into 150-DPI pixel space.      Two steps, in this order., Split a PDF array string into its top-level ``<< >>`` dictionaries.      Depth-c, Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.      The bbox is le, split_pdf_dicts(), viewport_bbox_to_px(), _FakeDoc (+13 more)

### Community 191 - "TestLeafWidth"
Cohesion: 0.18
Nodes (10): Harness pre-check (scratch `precheck.py`, s01/s02/s04/s16/s17/s18 vs the snapshots), Numbers, Pictures in this directory (none shows an address), Residue / not in scope (one line each), Rule (`detection/rooms.py::_plane_stamp`, in the patch), s01's stair rooms at the true factor (the parallel decision, `step8_s01_stair_rooms_identity_vs_true_factor.png`), Sweep (`tools/regress.py`, four background groups, vs the baseline), The LOST room, attributed (`step8_s18_door_0271_patio_strip_lost_before_after.png`) (+2 more)

### Community 192 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Room Labels Implementation Plan, Task 1: Branch and the deterministic span collector, Task 2: Schema, prompt, and the grounded response parser, Task 3: The one-call wrapper, Task 4: The label cache, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 193 - "TestWindowExteriorSide"
Cohesion: 0.06
Nodes (30): assess_scale(), check_dimensions(), check_door_leaves(), dimension_matches(), DimensionMatch, _fmt_scale(), leaf_width_px(), parse_dimension_mm() (+22 more)

### Community 194 - "TestCrossWindowToleranceUnscaled"
Cohesion: 0.13
Nodes (14): Floor and ceiling, Geometry, Heights, Module layout, Openings and wall area, Out of scope (recorded), Output, Problem (+6 more)

### Community 196 - "Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)"
Cohesion: 0.05
Nodes (36): Evidence: what broke at f = 50/92.2 = 0.542 (all measured on the real PDF), Group 1 — safe reference moves, Group 2 — thin-margin moves (three of five tried and reverted), Group 3 — class fixes, Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`), How the ablation was done (reproduce in ~30 min), Outcome — iteration 2 (2026-09-04, branch `recal/w-gate-iter2`), Outcome — iteration 3, step 1 (2026-09-04, branch `fix/section-line-dashes-not-hatch`) (+28 more)

### Community 197 - "EntranceDoorTests"
Cohesion: 0.22
Nodes (4): Bbox short-end edges of a sliding door: across the wall, never wall plane., _sliding_end_edges(), A plug-less door seals along its wall-plane edges only (W-gate     iteration 3 s, TestPlaneRestrictedFallback

### Community 198 - "fill_ring"
Cohesion: 0.33
Nodes (5): By entity type, File map — where everything lives, by detection type, History and open work, Output contract you must not break, Regression corpus and tooling

### Community 199 - "_is_light_pen"
Cohesion: 0.26
Nodes (4): Tier 3: a band that only SHORT annotation ink crosses is still a gutter.      Le, Tier 4: a band that only OVERHANGING long ink enters — every long     crosser te, TestOverhangGutter, TestShortInkGutter

### Community 200 - "TestSheetSize"
Cohesion: 0.13
Nodes (13): DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates, Leaf overlap of 10 px (> DOOR_DOUBLE_LEAF_OVERLAP_PX=5) → two separate candidate, has_threshold, door_subtype, and threshold_path_index carry through from either (+5 more)

### Community 201 - "File structure"
Cohesion: 0.17
Nodes (11): File structure, Global Constraints, Room Quantity Takeoff Implementation Plan, Task 1: Units, Task 2: Heights, Task 3: Per-room scale selection and sheet-size verification, Task 4: Openings — width from evidence, assignment to rooms, Task 5: Quantities — `compute_takeoff` (+3 more)

### Community 202 - "SplitDoubleArcTests"
Cohesion: 0.31
Nodes (3): detect_rooms consumes candidates before the offline floor, so a door     the pip, TestBlindWindowPocket, TestRejectedDoorIsNotAnEntrance

### Community 203 - "HygieneRuleTests"
Cohesion: 0.10
Nodes (25): _bridge_white_runs(), _equivalent_sides(), _FillRing, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      gate, (short, long) of the rectangle with this polygon's area and perimeter.      The, A closed same-fill polygon reconstructed from exploded `l` items., Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, _bridge_white_runs is detect_rooms's ONLY production call site     (detection/ro (+17 more)

### Community 205 - "parse_answer"
Cohesion: 0.11
Nodes (12): can_prompt(), parse_answer(), prompt_for_scale(), Tier 4 input — ask the user, but only when someone is there to answer.  batch_ex, True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream (+4 more)

### Community 206 - "DoorAssemblyTests"
Cohesion: 0.12
Nodes (18): PageTruth, TruthItem, evaluate_page(), Score one sheet's per-page pipeline output against its ground truth.      `pages, Score one page's entities against its three verdict lists., score_sheet(), ClassifyTests, CompareRunsTests (+10 more)

### Community 209 - "test_sliding_doors.py"
Cohesion: 0.05
Nodes (50): _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, _split_double_arc(), _trim_chain_extension_caps() (+42 more)

### Community 210 - "W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule")"
Cohesion: 0.22
Nodes (8): Numbers, Reseed, Rule (`detection/walls.py::_claims_far_side_sparse`, `WALL_FAR_SIDE_DENSITY_RATIO` 0.33, D-class), Sweep 1 — the rule alone (cap 36), The cap-40 retry — harness pre-check on the named sheets, NOT shipped, W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule"), What blocks the cap now, What the measurement said (the brief's premise was wrong)

### Community 211 - "PruneUnreadPageOutputTests"
Cohesion: 0.25
Nodes (7): Net effect (from the crops, my verdicts) — 22 rooms on 6 sheets, all gains, Numbers, Residue / not in scope (one line each), Rule (`detection/rooms.py::_clip_plug_tails`, `_tail_material_end`), Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline), W-gate iteration 3 — step 5: plug tails end AT the material they touch (`_clip_plug_tails`), What the measurement said (`tools/census_scratch/probe_tails.py`)

### Community 213 - "denominator_from_c"
Cohesion: 0.08
Nodes (24): InvalidArgument, PermissionDenied, Domain errors, carrying the callable error code they map to.  This module delibe, Unauthenticated, SourceFile, parse_request(), Parsing and validating one callable request.  The tenant is taken from the verif, The supplied scale, or None.      Only a member of SUPPLIABLE_SCALES is accepted (+16 more)

### Community 214 - "test_batch_extract.py"
Cohesion: 0.14
Nodes (8): A lone stroked, unfilled `qu` item — a joinery-pen box., s04 BATHROOM 01 (room_0000, door_0002): the structural opening is     112px wide, Closed stroked (fill-less) polyline exploded into chained `l` items., s03 corridor room_0014: the jamb nibs beside door_0007/door_0019 are     closed, stroked_box_path(), stroked_ring_path(), TestDoorLiningRings, TestJambNibRings

### Community 215 - "TestFarSidePairs"
Cohesion: 0.25
Nodes (7): Numbers, Residue / not in scope (one line each), Rule (`detection/walls.py::_dash_row_indices`, in the patch), Sweep (`tools/regress.py`, four background groups, vs the baseline), The ten LOST rooms, each attributed to its dash row (my read), W-gate iteration 3 — step 6: dash rows are drawn lines, not wall faces (shipped after the user retired ten chunk verdicts), What the measurement said (`tools/census_scratch/dash_rows.py`)

### Community 216 - "fill_ring"
Cohesion: 0.28
Nodes (6): Scales stated on the sheet, unbound to any drawing.      inspect does not segmen, unbound_scale_lines(), The inspect command's unbound scale listing.  inspect never segments regions, so, TestUnboundScaleLines, text(), viewport()

### Community 217 - "TestWindowGates"
Cohesion: 0.32
Nodes (4): Rotate every primitive's points about (cx, cy) by deg (bbox rebuilt)., The one world-space gate, exercised at a non-grid angle.      A faithful 1:100 e, rot_paths(), TestMinWidthNegativeControl

### Community 218 - "TestWindowTightPairInterior"
Cohesion: 0.20
Nodes (10): detect_schedules(), extract_plumber_document(), extract_plumber_page(), _normalize_bbox_plumber(), BBox, Schedule detection — tables carry real bboxes.  detect_schedules used to emit bb, extract_plumber_page must surface each table's bbox, normalized to     150-DPI p, _table() (+2 more)

### Community 220 - "_covers"
Cohesion: 0.15
Nodes (8): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, Windows are drawn at any angle, not just axis-aligned. The cap-anchored     mode, 5-1133-WD03.pdf missed window at path idx 6475: three glazing panes         at 1, End-to-end regression: floor-plans.pdf must yield exactly the four     ground-tr, TestFloorPlansRegression, TestWindow51133Topology, TestWindowArbitraryAngle

### Community 222 - "TestDashRowDiscriminators"
Cohesion: 0.07
Nodes (26): _point_in_bbox(), _point_to_segment_distance(), Minimum distance from point p to line segment ab., Minimum distance between two line segments., _segments_min_distance(), True when a wall FACE line runs unbroken through the bbox span.      A real wind, _wall_runs_through(), BBox (+18 more)

### Community 223 - "TakeoffRequest"
Cohesion: 0.09
Nodes (28): CallableRequest, Exception, build_response(), error_code(), _measure(), measure_takeoff(), Firebase entry point for the takeoff extraction pipeline.  This module is the on, The handler's real body, with its clients injected so it is testable.      Extra (+20 more)

### Community 225 - "W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves)"
Cohesion: 0.22
Nodes (8): Fixtures moved (all documented in the tests), Numbers, Outcome in one line, Sweep (final tree: cap 36, floor 11, density 2.2, seal 12, corridor 24), Tests (fast tier), The five moves, W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves), What each revert measured

### Community 226 - "squat_cap_window"
Cohesion: 0.11
Nodes (15): TextSpan, Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, A doorway whose jamb is a one-wall-thickness nib (s03 door_0018)., A filled wall band exported as two triangles (CAD fill triangulation).      Each, A chimney breast / pier drawn as a closed box on the room side of a     wall ban, s15: the "steel ridge beam" line — a dashed line drawn as a row of     14.8px pi, TestComponentFiltering, TestDashRowBarriers (+7 more)

### Community 229 - "NotFound"
Cohesion: 0.15
Nodes (7): FailedPrecondition, FakeCollection, FakeDb, FakeDoc, _record_data(), TestLoadRecord, TestStatusTransitions

### Community 230 - "bezier_arc"
Cohesion: 0.09
Nodes (30): _is_arc_like(), _compute_hu_distance(), _rasterize_paths_to_canvas(), Rasterize line/curve primitives onto a normalized binary canvas.      Segments a, Distance between candidate arc paths and the door Hu Moment template.      Lower, is_page_spanning(), _is_unfilled_rect(), nested_frame_indices() (+22 more)

### Community 231 - "TestWindowSpanOvershootRetune"
Cohesion: 0.22
Nodes (8): Change, Measurement first (`tools/census_scratch/harness.py`, seals 12/13/14/15 as multipliers of the tree's value), Numbers, Residue / not in scope (one line each, each its own iteration), Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline snapshots), The three classes every move falls into (probe_box / probe_boxes on each site), W-gate iteration 3 — step 7: `ROOM_OPENING_SEAL_PX` 12 → 15 (the retry), measured and shipped pending the user's decision, What the constant is, and why 15

### Community 232 - "W-gate recalibration — iteration 1: the census (2026-09-04)"
Cohesion: 0.25
Nodes (7): Method, Proposed iteration-2 groups (for the user's verdict — nothing changed yet), The gates that break s01 at f = 0.542 — refreshed on today's code, THE TABLE, The two worked instances, refreshed, W-gate recalibration — iteration 1: the census (2026-09-04), What the census says

### Community 233 - "W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)"
Cohesion: 0.25
Nodes (7): Numbers, Prose updated, Residue / not in scope, Sweep (four background groups vs. the main snapshots), Tests (fast tier, each proven to bite), The four moves, W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)

### Community 236 - "W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto")"
Cohesion: 0.22
Nodes (8): Net effect on s04 (from the crops, my verdicts), Numbers, Residue / not in scope (one line each, each its own iteration), Sweep (`tools/regress.py`, full corpus in four background groups, vs the main baseline), The rule that the measurement supports (`detection/rooms.py::_is_door_lining`), The seal retry — NOT attempted, and why, W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto"), What the measurement said (the brief's premise was wrong, twice)

### Community 237 - ".collect"
Cohesion: 0.17
Nodes (9): pipeline.resolve_page_regions returns UNCLASSIFIED regions on three     paths wh, SheetsTestCase, _takeoff(), TestFloorPlanFilter, TestPageDirectory, TestPageDiscovery, TestSheetIdentity, TestUnclassifiedRegions (+1 more)

### Community 238 - "W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale"
Cohesion: 0.25
Nodes (7): Numbers, Residue / not in scope (one line each), s01 rooms — four confirmed rooms lost at f = 0.542, Sweep, W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale, What the four rooms are actually lost through (measured), What this means for `_gate_denominator`

### Community 240 - "ablate.py"
Cohesion: 0.50
Nodes (3): main(), mult_for(), Per-constant ablations.    python ablate.py s01 s01mode   # f=0.542 full, scale-

### Community 241 - "resolve_page_regions"
Cohesion: 0.13
Nodes (10): The uniform scale factor of a rotate+scale transform. hypot is exact for     the, transform_scale(), Extraction puts geometry in the same frame as the declared page size.  page.get_, Every primitive, span AND image must land in the declared frame., A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestExtractPageFrame (+2 more)

### Community 243 - "artifacts.py"
Cohesion: 0.07
Nodes (19): artifact_names(), _content_type(), object_path(), page_prefix(), Path, Uploading a run's outputs to Cloud Storage.  Layout is customers/{customerId}/ta, Upload one page's artefacts. Absent files are skipped, not errors:     page.svg, summary.json and warnings.json live at the run root, and run_extract     writes (+11 more)

### Community 245 - "mult_summary.py"
Cohesion: 0.53
Nodes (5): cell(), damage(), load(), main(), Summarise abl/<slug>_mult.jsonl: per field x sheet, the damage at each multiplie

### Community 255 - "render_page_svg"
Cohesion: 0.36
Nodes (4): Document, MuPDF's own vector redraw of the page, in render.png's coordinate space.      Sa, render_page_svg(), TestRenderPageSvg

### Community 256 - "swing_door"
Cohesion: 0.10
Nodes (18): EndToEndTests, leaf_pair_door(), page(), prim(), End-to-end door scale behavior on FAITHFUL 1:100 fixtures.  A faithful 1:100 exp, leaf_pair (detection/doors/sliding.py) reads gates.DOOR_SLIDE_PANEL_MIN_THICKNES, Quarter-arc + a double-line leaf, as a faithful export at any scale.      radius, Two parallel panel rectangles in-band with partial overlap (sliding.py's     lea (+10 more)

### Community 276 - "TestCliEquivalence"
Cohesion: 0.08
Nodes (10): FakeBlob, FakeBucket, FakeDb, FakeDoc, The function must not change detection results.  tools/regress.py guards the CLI, Both pipeline runs happen ONCE for the class.      Each run is a full detection, The CLI arm over the SAME page set the runner passes.          page_indices is d, Why this test cannot run here, or None when it can.      Two independent precond (+2 more)

### Community 291 - "Takeoff as a Firebase Function — design"
Cohesion: 0.09
Nodes (22): Accepted limitation: unresolved scale, Context: what rivet-mind already has, Contract, Decisions, Dependencies, Execution flow, Failure handling, Firestore writes (+14 more)

### Community 330 - "migrate-labour-rates-to-groups.ts"
Cohesion: 0.11
Nodes (7): TestCase, Path, Skip helper for tests that need a real corpus sheet.  Corpus knowledge lives in, Return the sheet's path, or skip the test with an actionable message., require_sheet(), LoaderTests, The corpus loader resolves slugs against the committed manifest.  Every test bui

### Community 334 - "estimate-pdf-service.ts"
Cohesion: 0.11
Nodes (18): Handoff: hatch-cell chords in the wall network (follow-up to `fix/s03-bedroom-corner-notch`), Outcome of the anchor iteration (2026-09-02, `fix/collinear-merge-anchor-line`), Outcome of the collinear-support anchor (2026-09-02, same branch), Outcome of the s17 window-reveal slivers (2026-09-03, branch `fix/s17-cavity-wall-pockets`, not committed), Prompt for the next agent (the collinear-support anchor), Prompt for the next agent (the merged run's anchor line — R2's function), Prompt for the next agent (the s17 window-reveal slivers), Prompt that was executed for Gap C (the seam probe distance) (+10 more)

### Community 339 - "File Structure"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Self-Review, Takeoff Firebase Function Implementation Plan, Task 1: Scaffold, errors, and request parsing, Task 2: Firestore record access and status transitions, Task 3: Source file download and the tenant path boundary, Task 4: Sheet collection from a finished output tree (+5 more)

### Community 359 - "auth.tsx"
Cohesion: 0.48
Nodes (6): _geom(), _iou(), _latest(), _load(), main(), Entity-level before|after delta between a compare_sweeps snapshot (outputs/regre

### Community 361 - "Deploying the takeoff callable"
Cohesion: 0.17
Nodes (11): Deploy, Deploying the takeoff callable, Dry-run result — `rivet-mind-dev`, 2026-08-31, Known limitations, Local verification performed (this repo, no network, no deploy), One-time GCP setup, per project, Prerequisite — create the discovery venv first, REQUIRED MANUAL GATE — read before any deploy command (+3 more)

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **698 isolated node(s):** `storage`, `sheets`, `What "generic" means here (the rule that overrides all others)`, `What counts as a win`, `1. Intake — extract the brief` (+693 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **76 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `bezier_arc` to `swing_door`, `Door Assembly & Heuristics Core`, `EntranceDoorTests`, `Window Detection & Tests`, `Double-Door Merge & Gemini Client`, `TestWindowArbitraryAngle`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `client.py`, `Double-Arc Split Tests`, `Room Polygonization Internals`, `_check_opening_clear`, `Arc Cycle-Cap Pruning Tests`, `test_extraction_transform.py`, `arcs.py`, `resolver.py`, `_fit_circle_3pt`, `_arc`, `TestAnnotationPenBarriers`, `review.py`, `viewport_bbox_to_px`, `TestSwingHingePlugRestriction`, `test_curve_arc_garden_doors.py`, `renderer.py`, `_collect_wall_faces`, `path`, `TestWindowTightPairInterior`, `TestWindowExteriorSide`, `EntranceDoorTests`, `_is_light_pen`, `TestSheetSize`, `SplitDoubleArcTests`, `HygieneRuleTests`, `TestWindowExteriorSide`, `test_sliding_doors.py`, `test_batch_extract.py`, `_covers`, `TestDashRowDiscriminators`, `squat_cap_window`, `wall_band_h`, `TestMinWidthReference`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `attrib_rooms.py`, `vline`, `_find_openings`, `app.py`, `TestBandPocket`, `_collect_wall_faces`, `TestNetworkQueries`, `framed_triple_window`, `_segments_min_distance`?**
  _High betweenness centrality (0.151) - this node is a cross-community bridge._
- **Why does `run_extract()` connect `TestXYCut` to `Window Detection & Tests`, `Door Detection & Tests`, `Debug Trace Collector`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `ShaMismatchAgainstTruthTests`, `Arc Cap-Trim Tests`, `TestCliEquivalence`, `_arc`, `plumber.py`, `_double_arc`, `ScaleInfo`, `batch_extract.py`, `_dedupe_openings`, `test_window_detection.py`, `TestCheckDoorLeaves`, `TestWindowTightPairInterior`, `TakeoffRequest`, `detect_doors`, `TestAnnotationPenBarriers`, `qualifying_clip_rects`, `framed_triple_window`, `render_page_svg`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `squat_cap_window` to `Door Assembly & Heuristics Core`, `EntranceDoorTests`, `Window Detection & Tests`, `Double-Door Merge & Gemini Client`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Arc Cycle-Cap Pruning Tests`, `_fit_circle_3pt`, `geometry.py`, `TestAnnotationPenBarriers`, `review.py`, `_arc`, `test_layout_segmenter.py`, `TestSwingHingePlugRestriction`, `renderer.py`, `TestXYCut`, `TestWindowTightPairInterior`, `TestWindowExteriorSide`, `EntranceDoorTests`, `_is_light_pen`, `TestSheetSize`, `SplitDoubleArcTests`, `HygieneRuleTests`, `TestWindowExteriorSide`, `test_batch_extract.py`, `TestWindowTightPairInterior`, `TestDashRowDiscriminators`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `vline`, `app.py`, `TestBandPocket`, `TestAnnotationPenBarriers`, `qualifying_clip_rects`, `TestNetworkQueries`, `framed_triple_window`, `_segments_min_distance`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 145 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 145 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `Candidate` (e.g. with `_SlidePanel` and `CrossGates`) actually correct?**
  _`Candidate` has 91 INFERRED edges - model-reasoned connections that need verification._