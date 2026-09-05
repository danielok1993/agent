# Graph Report - agent  (2026-09-05)

## Corpus Check
- 280 files · ~658,893 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4840 nodes · 12250 edges · 276 communities (199 shown, 77 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 938 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0fe3a1a8`
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
- [[_COMMUNITY_TestRenderPageSvg|TestRenderPageSvg]]
- [[_COMMUNITY_TestMinWidthReference|TestMinWidthReference]]
- [[_COMMUNITY_NotFound|NotFound]]
- [[_COMMUNITY_bezier_arc|bezier_arc]]
- [[_COMMUNITY_TestWindowSpanOvershootRetune|TestWindowSpanOvershootRetune]]
- [[_COMMUNITY_W-gate recalibration — iteration 1 the census (2026-09-04)|W-gate recalibration — iteration 1: the census (2026-09-04)]]
- [[_COMMUNITY_W-gate recalibration, iteration 2 — checkpoint Group 1 (safe reference moves)|W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)]]
- [[_COMMUNITY_attrib_rooms.py|attrib_rooms.py]]
- [[_COMMUNITY_TestMinWidthNegativeControl|TestMinWidthNegativeControl]]
- [[_COMMUNITY_W-gate iteration 3 — step 2 the seal-15 sites measured; the corner door lining (was hinge-less swing-side veto)|W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto")]]
- [[_COMMUNITY_.collect|.collect]]
- [[_COMMUNITY_W-gate iteration 3 — step 3 the short-piece material rule measured; nothing to build, and what actually holds s01 at its true scale|W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_ablate.py|ablate.py]]
- [[_COMMUNITY_resolve_page_regions|resolve_page_regions]]
- [[_COMMUNITY_TestBandPocket|TestBandPocket]]
- [[_COMMUNITY_artifacts.py|artifacts.py]]
- [[_COMMUNITY_probe_plugs.py|probe_plugs.py]]
- [[_COMMUNITY_mult_summary.py|mult_summary.py]]
- [[_COMMUNITY_probe_tails.py|probe_tails.py]]
- [[_COMMUNITY_TestRoomGatesConstruction|TestRoomGatesConstruction]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY_overrides|overrides]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY__stroke_percentile_rank|_stroke_percentile_rank]]
- [[_COMMUNITY_TestFaceCollection|TestFaceCollection]]
- [[_COMMUNITY__plane_stamp|_plane_stamp]]
- [[_COMMUNITY_render_page_svg|render_page_svg]]
- [[_COMMUNITY_swing_door|swing_door]]
- [[_COMMUNITY_test_scale_no_prompt.py|test_scale_no_prompt.py]]
- [[_COMMUNITY_TestWindowGates|TestWindowGates]]
- [[_COMMUNITY_normalize_bbox|normalize_bbox]]
- [[_COMMUNITY__far_wall_network|_far_wall_network]]
- [[_COMMUNITY__is_band_pocket|_is_band_pocket]]
- [[_COMMUNITY_TestPlugSealReach|TestPlugSealReach]]
- [[_COMMUNITY_TestNetworkAssembly|TestNetworkAssembly]]
- [[_COMMUNITY_TestCrossWindowToleranceUnscaled|TestCrossWindowToleranceUnscaled]]
- [[_COMMUNITY__leaf_ink_indices|_leaf_ink_indices]]
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
- `kept_plugs_for()` --indirect_call--> `rooms()`  [INFERRED]
  tools/census_scratch/probe_tails.py → tests/test_room_label_pipeline.py
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` --semantically_similar_to--> `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [INFERRED] [semantically similar]
  5-1133-WD03.pdf → floor-plans.pdf
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` --references--> `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf → 5-1133-WD03.pdf
- `DebugTraceCollector` --uses--> `PathPrimitive`  [INFERRED]
  debug/trace.py → models.py
- `_SlidePanel` --uses--> `DebugTraceCollector`  [INFERRED]
  detection/doors/sliding.py → debug/trace.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **5-1133-WD03 proposed lower ground floor: walls, windows, doors** — 5_1133_wd03, 5_1133_wd03_cavity_walls, 5_1133_wd03_windows, 5_1133_wd03_folding_sliding_doors [EXTRACTED 1.00]
- **floor-plans proposed ground & first floor plans with rooms and rooflights** — floor_plans, floor_plans_ground_floor, floor_plans_first_floor, floor_plans_velux [EXTRACTED 1.00]

## Communities (276 total, 77 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.09
Nodes (19): Path, The images a human looks at while giving verdicts.  One PNG per page per entity, door_0007 -> d7. Unparseable ids are returned unchanged., Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, short_id(), write_review_overlays(), MainExceptionIsolationTests, tools/review.py's main(): one sheet's unexpected failure must not kill the walk (+11 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.10
Nodes (20): Drop window candidates that materially sit on a detected door.      Door symbols, True when ``win`` stands beyond ``door``'s hinge-side jamb in the door's     own, _resolve_door_window_conflicts(), _window_in_door_wall_run(), Candidate, _room_entity(), DoorEvidencePropagationTests, Verify Step 4 — door evidence keys land in Entity.attributes in offline mode. (+12 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.13
Nodes (13): _attach_text_spans(), Grow paths-only boxes to absorb the text spans beside them.      The tier-2 cut, Split a page into drawing regions. Returns [] for a page with no vector     ink, segment_page(), PageData, block(), A solid-ish blob: a horizontal line every 4px so every bin row is inked., span() (+5 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.10
Nodes (36): _load_font(), baseline_dir(), baseline_run(), classify(), compare(), compare_runs(), _crop(), diff_entities() (+28 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.13
Nodes (19): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+11 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.10
Nodes (22): apply_classification(), build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+14 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.12
Nodes (12): _contains(), is_verified(), _ratio_pair(), Which drawing scale a room is measured at, and whether it can be trusted.  Pages, Source-level trust, then the drawing's own evidence: a failed     plausibility c, (w_ratio, h_ratio) of page over ISO size, orientation-matched., select_room_scale(), sheet_size_tokens() (+4 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.16
Nodes (13): _native_curve_chains(), Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), NativeCurveChainsTests, _qu_leaf(), The door_0051 pattern: native curves with shared endpoints group         into a (+5 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.10
Nodes (16): detect_wall_network(), _fill_ring_components(), _is_light_pen(), Group ring ids (restricted to `members`) connected by shared seams.      Exporte, Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., fan_triangulated_band_h(), hline() (+8 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.11
Nodes (20): block(), one_blob_page(), page_with_a_dropped_strip(), parse_failing_classifier(), raster_page(), Region resolution rules (pipeline.resolve_page_regions).  A stub classifier stan, Filtering only pays if the regions hold the sheet's ink., two_blob_page plus a 52px-tall strip of real drawing.      It is its own leaf, b (+12 more)

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
Cohesion: 0.05
Nodes (42): detect(), EndToEndTests, fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack() (+34 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.27
Nodes (12): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Run extract command for a single PDF.     Returns (pdf_path, success: bool, outp, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive). (+4 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.15
Nodes (13): _centre_in_any(), filter_page_data(), BBox, Reduce a PageData to the primitives inside a set of regions.  This filters, it d, A copy of page_data holding only primitives whose bbox centre falls in     one o, Text spans inside the given regions. Used to scope schedule detection to     sch, region_text_spans(), path() (+5 more)

### Community 17 - "arcs.py"
Cohesion: 0.13
Nodes (5): prim(), TestDoorGatesConstruction, TestFoldingGatesThreading, TestLeafGatesThreading, TestSlidingGatesThreading

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
Cohesion: 0.08
Nodes (43): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), _fit_circle_3pt(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some (+35 more)

### Community 22 - "geometry.py"
Cohesion: 0.13
Nodes (13): build_request_text(), is_grounded(), is_noise_span(), Polygon, Ask Gemini for the name written inside each detected room.  One text-only call p, The one user part: every room's spans as JSON, keyed by ordinal., True when every word of the label appears in that room's own spans.      This ma, True for text that can never be a room name: dimension strings, door     and win (+5 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.16
Nodes (9): InvalidArgument, Domain errors, carrying the callable error code they map to.  This module delibe, Unauthenticated, parse_request(), Parsing and validating one callable request.  The tenant is taken from the verif, The supplied scale, or None.      Only a member of SUPPLIABLE_SCALES is accepted, _scale_denominator(), TestParseRequest (+1 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.07
Nodes (18): attrib.py <slug> <x0> <y0> <x1> <y1> FIELD=MULT [FIELD=MULT ...]  Runs the harne, attrib_rooms.py <slug> FIELD=MULT [...]: for each config (each alone on top of t, COLLINEAR_OFFSET_TOL forms, measured with the census harness on top of the curre, crop_dash.py <slug> <name> X0 Y0 X1 Y1 [...]: crop the latest sweep render with, denom_at(), load(), mm(), W-gate census harness: run the stage-5 chain exactly as tools/regress.py does, w (+10 more)

### Community 35 - "plumber.py"
Cohesion: 0.13
Nodes (12): Client, init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-, _door_attribute_overlay(), finalize_candidates(), Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, Promote candidates to entities, applying the offline confidence floors.      Gem, assembly_type must reach Entity.attributes through the pipeline passthrough. (+4 more)

### Community 36 - "_projected_interval"
Cohesion: 0.21
Nodes (5): _hface(), A bare horizontal wall-face _Seg for isolated merge-tolerance tests., Isolates _merge_collinear_segs's offset-tolerance scaling directly —     the exa, TestMergeCollinearOffsetScaling, TestWallGatesConstruction

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.09
Nodes (22): build_ink_map(), is_page_spanning(), _is_unfilled_rect(), nested_frame_indices(), path_length(), Binary ink occupancy map over a page, used to find whitespace gutters., True for sheet furniture: a border rule or column divider that runs the     leng, Path indices of nested sheet furniture: unfilled rectangles with at     least mi (+14 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.19
Nodes (16): cache_file(), cache_key(), load_labels(), Path, On-disk cache of room labels, keyed by page content AND the room polygons the la, Stable digest of the room outlines a labelling was made against.      A cached l, room_geometry_hash(), save_labels() (+8 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.13
Nodes (9): Stick-font text drawn as line strokes (s06/s11/s16/s20: no text     spans, every, HITL' in 14px stick glyphs, cap line y, baseline y + 14., A DRAWN DASH LINE — one line its line type exploded into a periodic     row of s, The two classes the corpus sweep exposed on the first cut of the     rule: a wal, 135-degree strokes from face x0 to face x1, clipped to the band., TestDashRowDiscriminators, TestDashRowExclusion, TestVectorTextExclusion (+1 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.15
Nodes (12): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 1c. Bay / corner frames — the square corner post (s10 lounge), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf (+4 more)

### Community 44 - "renderer.py"
Cohesion: 0.33
Nodes (11): sheet_pdf(), dump(), _fmt_face(), _fmt_seg(), _in_box(), _key(), main(), Path (+3 more)

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.18
Nodes (11): _layer_annotation_veto(), _layer_classes(), _layer_hint_from_layer(), _layer_strong_prior(), _layer_tokens(), True when the layer name marks its ink as annotation (callouts,     dimensions,, The element classes named by a layer's tokens., Return a high confidence boost when a layer name conclusively names the type. (+3 more)

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.17
Nodes (11): Diagnosis (measured 2026-08-13, this is the evidence the plan argues from), Global Constraints, Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan, Self-Review, Task 0: Branch setup, Task 1: `build_ink_map(include_text=...)`, Task 2: Extract `_boxes_from_cut` (pure refactor), Task 3: `_attach_text_spans` (+3 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.06
Nodes (88): _door_fallback_candidate(), _find_threshold_line(), _nearest_pair_distance(), _pair_door_assemblies(), BBox, Find an entrance-door threshold/sill line parallel to the leaf long axis.      T, Parse an evidence bbox value defensively; return None on any invalid shape., _safe_bbox() (+80 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.13
Nodes (6): A doorway whose jamb is a one-wall-thickness nib (s03 door_0018)., Rect room with a 45px doorway gap in the top wall (240..285)., TestClosedRooms, TestJambNib, TestSwingRecessDissolution, wall_band_v()

### Community 103 - "PathPrimitive"
Cohesion: 0.17
Nodes (15): _check_provenance(), _ordered(), pending(), What a persisted sweep still needs verdicts on.  Reads the run output the sweep, Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk. (+7 more)

### Community 104 - "detect_doors"
Cohesion: 0.29
Nodes (12): classify_page(), extract_document(), extract_images(), extract_page(), extract_text(), get_ocg_names(), page_transform(), Document (+4 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.10
Nodes (18): TruthItem, Regression corpus: fixture resolution, ground truth, matching, and the sweep., iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity() (+10 more)

### Community 107 - "vline"
Cohesion: 0.11
Nodes (19): detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, DegenerateCompanionTests, DoorAssemblyTests, EntranceDoorTests, line(), path(), PolylineArcBinCapTests (+11 more)

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
Nodes (126): door_open_leaf_path_indices(), Path indices of swing doors' OPEN leaf linework.      A swing door's leaf is dra, _angle_diff_mod180(), _line_angle_deg(), _line_length(), _perpendicular_spacing(), _project_onto_axis(), _projected_interval() (+118 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.18
Nodes (11): Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door() (+3 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.05
Nodes (43): bind_scale(), binding_texts(), _caption_distance(), _centroid(), _contains(), The scale governing one region, or None.      `viewports` must arrive smallest-b, Resolve a scale for every floor-plan region on one page.      `fallback` is a sc, How far a text span sits from a region, or None if it is not near it.      Horiz (+35 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.18
Nodes (8): BBox, qualifying_clip_rects_from_boxes(), Keep only clips that look like real drawing boundaries.      Measured on the sam, dot(), page_with(), Clip-rect gating tests (layout/clips.py)., TestClipCutPositions, TestClipGating

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.12
Nodes (14): PageTruth, _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, evaluate_page(), Score one page's entities against its three verdict lists. (+6 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.04
Nodes (45): One drawing on a sheet, found by whitespace segmentation.      bbox is 150-DPI p, Region, _effective_denominator(), _gate_denominator(), One detection factor per page: which scale governs the ink detection sees.  Dete, Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY., The denominator allowed to drive gate scaling, or None to abstain.      Only a D, Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan. (+37 more)

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.13
Nodes (28): _accept_jamb_rings(), _building_masses(), detect_rooms(), _drop_window_exterior_sides(), _folding_chain_gap_plug(), _free_space_components(), _is_door_lining(), _is_wall_recess() (+20 more)

### Community 120 - "TestNetworkQueries"
Cohesion: 0.15
Nodes (8): door_candidate(), Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, rooms_for(), TestBboxSealFloor, TestComponentFiltering, TestOpeningSeals, TestPhantomDoorSeals

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.16
Nodes (8): parse_height(), _prompt_ceiling(), Metres from "2.4", "2.4m", "2400", "2400mm". None to skip., A positive, finite number of metres — or ValueError naming the offender., resolve_heights(), valid_height_m(), TestParseHeight, TestResolveHeights

### Community 123 - "batch_extract.py"
Cohesion: 0.16
Nodes (8): paving_field(), Running-bond paving: continuous course lines, staggered joint lines.      Mirror, Striped fields (paving bonds, tile fields, treads) are not walls., Stroke-color pen identity: pairing, faint-ink demotion, dimension     chains, an, Four wall bands forming a closed rectangular room (outer faces at the     given, rect_room(), TestLatticeDemotion, TestPenGates

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.10
Nodes (25): _bbox_area(), _bbox_center(), _bbox_union(), _interval_overlap(), _point_in_bbox(), BBox, Whether a path's segments are DRAWN lines, as opposed to the boundary     of a f, _stroke_is_visible() (+17 more)

### Community 126 - "_segments_min_distance"
Cohesion: 0.12
Nodes (12): _clip_plug_tails(), _door_plugs(), _open_leaf_edges(), Bbox edges of a garden-layout double door that are room floor, not wall.      A, End each bbox-edge plug's tails AT the material they touch.      _door_plugs tri, Thin barrier bands along the wall planes through a detected door.      The door, Interrupted-run plugs need jambs that REACH the plug band and a mid     that is, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto. (+4 more)

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
Cohesion: 0.13
Nodes (21): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor, WallFace, WallNetwork (+13 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.20
Nodes (11): _bridge_white_runs(), _equivalent_sides(), Band-shaped convex hulls closing the gaps in accepted white-ring runs.      gate, (short, long) of the rectangle with this polygon's area and perimeter.      The, _bridge_white_runs is detect_rooms's ONLY production call site     (detection/ro, TestBridgeWhiteRunsGapScaling, Wall-network builder tests (detection/walls.py).  Synthetic PathPrimitive fixtur, Accepted hollow-wall/joinery _FillRing over the given rectangle. (+3 more)

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
Cohesion: 0.20
Nodes (11): _is_arc_like(), bbox_aspect(), bezier_arc(), BezierAspectGateTests, line(), path(), Pins for the Bezier swing-arc bbox-aspect gate (DOOR_BBOX_ASPECT_MIN/MAX).  The, One cubic Bezier approximating a circular arc of the given sweep.      Standard (+3 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.14
Nodes (11): qualifying_clip_rects(), Read scissor rects off a fitz.Page and gate them. Returns [] if the     PDF expo, assigned_path_fraction(), Share of the page's paths that any region would keep.      Deliberately the same, Golden segmentation results on the corpus reference sheets (s01, s02, s11).  Mea, Load-bearing golden for SEGMENT_MAX_DEPTH = 7: at 6 the first-floor     plan and, s15 measured 2026-08-13: 214 text spans bridge every gutter, so the     text-inc, segment() (+3 more)

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.18
Nodes (7): fill_ring(), marker_ring(), Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, Closed filled rectangle exploded into 4 chained `l` items., TestFillClassRating, TestMarkerRings

### Community 140 - "ShaMismatchAgainstTruthTests"
Cohesion: 0.07
Nodes (35): load_manifest(), manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, The committed manifest, or an empty corpus when it is absent., Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, Flip a manifest entry's `labeled` flag and write the manifest back.      `labele (+27 more)

### Community 141 - "File Structure"
Cohesion: 0.12
Nodes (15): File Structure, Global Constraints, Phase 3 — corpus labeling (not a task), Regression Corpus Implementation Plan, Slug Assignment (authoritative — used by Tasks 2 and 3), Task 10: Seed s01 ground truth and document the labeling loop, Task 1: Corpus loader, Task 2: Migrate the sheets into the fixtures layout (+7 more)

### Community 142 - "Regression Corpus — Design"
Cohesion: 0.12
Nodes (15): Adoption — `tools/add_sheet.py`, Architecture, Constraints, Fixture layout, Ground truth, Naming, Non-goals, Phasing (+7 more)

### Community 143 - "_check_opening_clear"
Cohesion: 0.11
Nodes (15): detect_windows(), _frame_axes(), _merge_mullion_chains(), Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C, Join collinear glazing segments across mullion blocks into logical panes.      A, Detect windows as capped openings bridged by a parallel glazing band.      For e, The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si (+7 more)

### Community 144 - "Regression Testing — Working Guide"
Cohesion: 0.11
Nodes (17): 10. The loop when tuning detection, 11. Corpus mechanics, 12. Invariants you must not break, 13. Gotchas, each learned by shipping the bug, 14. Current state (2026-08-06), 15. Where the code lives, 1. Why this exists, 2. Two tiers — know which one you are in (+9 more)

### Community 145 - "test_extraction_transform.py"
Cohesion: 0.08
Nodes (42): clip_cut_positions(), Native PDF clip rects, used as extra cut hints for the segmenter.  Clip rects ar, Convert clip edges to (row, col) cut candidates, in bin indices.      Each candi, Tunable constants for page segmentation.  Values are measured, not guessed — see, Page segmentation: split a sheet into its constituent drawings., InkMap, bins[row][col] is 1 where drawn ink falls, 0 elsewhere., _boxes_from_cut() (+34 more)

### Community 146 - "Detection Review Tooling V1 — Implementation Plan"
Cohesion: 0.14
Nodes (13): Detection Review Tooling V1 — Implementation Plan, Done when, File Structure, Global Constraints, Out of scope, Task 1: Persistent sweep output directory, Task 2: Entity ids in the REVIEW lines, Task 3: Ground truth carries room polygons (+5 more)

### Community 147 - "RunDirTests"
Cohesion: 0.18
Nodes (4): LabeledFlagSweepIntegrationTests, End-to-end through sweep() for the two failing cases -- both exit via     `conti, Fix: an operator who pastes a fresh hash into the manifest instead of     adopti, ShaMismatchAgainstTruthTests

### Community 148 - "resolver.py"
Cohesion: 0.16
Nodes (13): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, _chain(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t (+5 more)

### Community 149 - "_arc"
Cohesion: 0.12
Nodes (22): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+14 more)

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.18
Nodes (10): hline(), path(), Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, Filled arrowhead triangle (a marker ring) pointing down at `tip`., Stairs are furniture to the room stage: a room polygon runs to the     enclosing, rect_room(), stair_arrowhead(), TestAnnotationPenBarriers (+2 more)

### Community 151 - "normalize_bbox"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Window Gates Implementation Plan, Task 1: `WindowGates` dataclass, Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`, Task 3: The W-row negative control at 50°, Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°, Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it, Task 6: Findings doc — §4e frozen table, §6 entries (+1 more)

### Community 152 - "review.py"
Cohesion: 0.25
Nodes (5): _color_tuple(), extract_paths(), Explode each drawing into one PathPrimitive per atomic item (l/c/re/qu).      Py, PDF line width 0 is a pen, not the absence of one.  PDF 32000-1 §8.4.3.2: "A lin, ZeroWidthStrokeTests

### Community 153 - "viewport_bbox_to_px"
Cohesion: 0.10
Nodes (24): _dedupe_by_perp(), _facing_cap_pairs(), _find_openings(), _glaze_index(), World-space window gates, pre-multiplied by the detection factor.      Exactly O, Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Two-axis lookup structure over a frame's glazing pool.      Every cap pair asks (+16 more)

### Community 154 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Scale-Aware Door Detection Gates Implementation Plan, Self-Review, Task 1: `DoorGates` dataclass, Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point, Task 3: Thread gates through `leaves.py`, Task 4: Thread gates through `sliding.py` (+5 more)

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.14
Nodes (13): 1. Intake — extract the brief, 2. Orient — read before touching code, 3. Baseline and locate, 4. Diagnose — measure, don't guess, 5. Fix — test first, then code, then prose, 6. Sweep — target, references, then corpus, 7. CHECKPOINT — report and stop, 8. After the go-ahead (+5 more)

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.16
Nodes (13): Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO (+5 more)

### Community 157 - "apply_classification"
Cohesion: 0.17
Nodes (11): 1. Factor computation (`scale` package), 2. Plumbing, 3. Constant classification, 4. Interactions to preserve (invariants across scales), 5. Testing, 6. Rejected alternatives (full reasoning in findings doc §5), Acceptance criteria, Design (+3 more)

### Community 159 - "test_layout_segmenter.py"
Cohesion: 0.13
Nodes (6): Every 1:N denominator stated in one string, in the order written., scales_in_text(), Reading a 1:N scale out of text spans.  Every string below is copied verbatim fr, span(), TestScalesInText, TestTextScales

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
Cohesion: 0.18
Nodes (13): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _draw_regions(), BBox, Image (+5 more)

### Community 165 - "ScaleInfo"
Cohesion: 0.11
Nodes (26): A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, ScaleInfo, The per-region scale table printed after each page., scale_table(), detection_scale(), _fallback_info(), PageScales, A scale the user supplied for the whole run, as a ladder entry.      `source="us (+18 more)

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "PruneArcSpursTests"
Cohesion: 0.14
Nodes (18): CallableRequest, build_response(), error_code(), _measure(), measure_takeoff(), Firebase entry point for the takeoff extraction pipeline.  This module is the on, The handler's real body, with its clients injected so it is testable.      Extra, Measure the drawings on takeoffs/{takeoffId} and return their sheets. (+10 more)

### Community 168 - "TestWindowTopology"
Cohesion: 0.29
Nodes (8): Name each detected room from the text drawn in it. Returns the full     entity l, resolve_room_labels(), naming(), page(), path(), Room label orchestration rules (pipeline.resolve_room_labels).  No API calls: la, rooms(), TestResolveRoomLabels

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
Cohesion: 0.43
Nodes (7): _best_match(), _latest(), main(), _missing(), Polygon, Before|after crop of ONE room's outline change — the picture behind a `tools/com, _rooms()

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
Cohesion: 0.17
Nodes (13): FakeBucket, FakeDb, _make_extract(), A normally measured page: one scale, read off the sheet., A page the resolver could not read a scale for.      Rooms survive with their ge, /tmp is tmpfs charged against the 2 GiB memory budget, so peak usage     must be, pages: {page_number: (region_types, takeoff_dict | None)}, _record() (+5 more)

### Community 178 - "PageTruth"
Cohesion: 0.20
Nodes (8): effective_denominator(), mm_per_px(), px2_to_m2(), px_to_m(), Pixel ↔ metre conversion.  Everything downstream of extraction/extractor.py is 1, Nominal beats raw so 1:50 sheets compute exactly (scale/factor.py rule)., TestEffectiveDenominator, TestUnits

### Community 179 - "_vector_text_indices"
Cohesion: 0.18
Nodes (6): _check_opening_clear(), _line_nears_bridge_interior(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, True when some point of segment p1-p2 lies within buffer_px of the bridge     li, DoorV2OpeningCheckTests, Tests for v2 bridge-line opening check and arc sweep estimation.

### Community 180 - "cluster_denominators"
Cohesion: 0.09
Nodes (18): _arc_radius(), assign_openings(), _bbox_edge_along_boundary(), _chord_length(), opening_width_px(), opening_width_px_from_evidence(), _positive(), Polygon (+10 more)

### Community 181 - "Step 5 — Per-scale-group detection for mixed-scale pages"
Cohesion: 0.29
Nodes (6): Acceptance (to refine in the spec), Process (binding), Step 5 — Per-scale-group detection for mixed-scale pages, The design sketch to start from (findings §6, verbatim intent), The problem, Why it is NOT a bolt-on (measured hazard)

### Community 182 - "test_window_detection.py"
Cohesion: 0.09
Nodes (40): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), Document (+32 more)

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
Cohesion: 0.06
Nodes (46): attach_takeoff(), _page_summary_dict(), Mirror the per-room takeoff onto room Entity.attributes["takeoff"]., attributes_by_room(), opening_dict(), takeoff.json — the document the web app's overlay and assembly table are both bu, The whole page as one document., One room: geometry, its opening ids, and its quantities.      `quantities` is No (+38 more)

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
Cohesion: 0.06
Nodes (31): Evidence: what broke at f = 50/92.2 = 0.542 (all measured on the real PDF), Group 1 — safe reference moves, Group 2 — thin-margin moves (three of five tried and reverted), Group 3 — class fixes, Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`), How the ablation was done (reproduce in ~30 min), Outcome — iteration 2 (2026-09-04, branch `recal/w-gate-iter2`), Outcome — iteration 3, step 1 (2026-09-04, branch `fix/section-line-dashes-not-hatch`) (+23 more)

### Community 198 - "fill_ring"
Cohesion: 0.33
Nodes (5): By entity type, File map — where everything lives, by detection type, History and open work, Output contract you must not break, Regression corpus and tooling

### Community 199 - "_is_light_pen"
Cohesion: 0.16
Nodes (7): cut(), page(), Tier 3: a band that only SHORT annotation ink crosses is still a gutter.      Le, Tier 4: a band that only OVERHANGING long ink enters — every long     crosser te, TestOverhangGutter, TestShortInkGutter, TestXYCut

### Community 200 - "TestSheetSize"
Cohesion: 0.15
Nodes (14): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates (+6 more)

### Community 201 - "File structure"
Cohesion: 0.17
Nodes (11): File structure, Global Constraints, Room Quantity Takeoff Implementation Plan, Task 1: Units, Task 2: Heights, Task 3: Per-room scale selection and sheet-size verification, Task 4: Openings — width from evidence, assignment to rooms, Task 5: Quantities — `compute_takeoff` (+3 more)

### Community 202 - "SplitDoubleArcTests"
Cohesion: 0.31
Nodes (3): detect_rooms consumes candidates before the offline floor, so a door     the pip, TestBlindWindowPocket, TestRejectedDoorIsNotAnEntrance

### Community 203 - "HygieneRuleTests"
Cohesion: 0.18
Nodes (12): Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, Scale coordinates by s, keep stroke widths — a 1:100 export., A closed 400x300 room drawn as four double-line wall bands., room_box_walls(), rooms_for(), shrink(), TestOrchestratorForwardsFactor, TestRoomsScaled (+4 more)

### Community 205 - "parse_answer"
Cohesion: 0.12
Nodes (11): can_prompt(), parse_answer(), prompt_for_scale(), True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream, The interactive scale prompt.  The prompt must never run in batch_extract (Proce (+3 more)

### Community 206 - "DoorAssemblyTests"
Cohesion: 0.09
Nodes (18): SheetTruth, _labeled_but_unreviewed(), _prune_unread_page_output(), Delete the page-level files a sweep persists but never uses.      Making sweep o, True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages, score_sheet(), entity() (+10 more)

### Community 208 - "TestWindowExteriorSide"
Cohesion: 0.42
Nodes (3): A window is a wall opening between inside and outside. When the space     on one, TestWindowExteriorSide, wall_band_h()

### Community 209 - "test_sliding_doors.py"
Cohesion: 0.13
Nodes (15): Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, _split_double_arc(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca (+7 more)

### Community 210 - "W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule")"
Cohesion: 0.22
Nodes (8): Numbers, Reseed, Rule (`detection/walls.py::_claims_far_side_sparse`, `WALL_FAR_SIDE_DENSITY_RATIO` 0.33, D-class), Sweep 1 — the rule alone (cap 36), The cap-40 retry — harness pre-check on the named sheets, NOT shipped, W-gate iteration 3 — step 1: the far-side density rule (was "mark-class rule"), What blocks the cap now, What the measurement said (the brief's premise was wrong)

### Community 211 - "PruneUnreadPageOutputTests"
Cohesion: 0.25
Nodes (7): Net effect (from the crops, my verdicts) — 22 rooms on 6 sheets, all gains, Numbers, Residue / not in scope (one line each), Rule (`detection/rooms.py::_clip_plug_tails`, `_tail_material_end`), Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline), W-gate iteration 3 — step 5: plug tails end AT the material they touch (`_clip_plug_tails`), What the measurement said (`tools/census_scratch/probe_tails.py`)

### Community 213 - "denominator_from_c"
Cohesion: 0.12
Nodes (15): PermissionDenied, SourceFile, assert_customer_scoped(), download_sources(), DownloadedSource, _local_name(), parse_gs_uri(), Fetching the drawings a takeoff points at.  The tenant boundary here is the same (+7 more)

### Community 214 - "test_batch_extract.py"
Cohesion: 0.15
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
Cohesion: 0.19
Nodes (10): detect_schedules(), extract_plumber_document(), extract_plumber_page(), _normalize_bbox_plumber(), BBox, Schedule detection — tables carry real bboxes.  detect_schedules used to emit bb, extract_plumber_page must surface each table's bbox, normalized to     150-DPI p, _table() (+2 more)

### Community 220 - "_covers"
Cohesion: 0.15
Nodes (8): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, Windows are drawn at any angle, not just axis-aligned. The cap-anchored     mode, 5-1133-WD03.pdf missed window at path idx 6475: three glazing panes         at 1, End-to-end regression: floor-plans.pdf must yield exactly the four     ground-tr, TestFloorPlansRegression, TestWindow51133Topology, TestWindowArbitraryAngle

### Community 221 - "MainExceptionIsolationTests"
Cohesion: 0.18
Nodes (7): band_segments(), hatch(), A band hatched THROUGH — every diagonal stroke ending on both faces — is a drawn, 45° strokes across the band; inset > 0 stops them short of each face., WALL_THROUGH_HATCH_MAX_PX is 72px — 610mm at 1:50 (W-gate census     2026-09-04), ThroughHatchBandTests, ThroughHatchCapReferenceTests

### Community 222 - "TestDashRowDiscriminators"
Cohesion: 0.20
Nodes (9): Minimum distance between two line segments., _segments_min_distance(), BBox, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox., Max fraction of the bbox long axis covered by one near-collinear centerline., True when the two segments cross at an interior point.      _segments_min_distan, Min distance between a segment and an axis-aligned bbox (0 if touching)., _segment_bbox_distance() (+1 more)

### Community 223 - "TakeoffRequest"
Cohesion: 0.09
Nodes (22): Exception, Base class. `code` is a Firebase callable error code string., TakeoffFnError, TakeoffRequest, RunResult, FakeAuth, FakeReq, TestBuildResponse (+14 more)

### Community 225 - "W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves)"
Cohesion: 0.22
Nodes (8): Fixtures moved (all documented in the tests), Numbers, Outcome in one line, Sweep (final tree: cap 36, floor 11, density 2.2, seal 12, corridor 24), Tests (fast tier), The five moves, W-gate recalibration, iteration 2 — checkpoint: Group 2 (thin-margin moves), What each revert measured

### Community 226 - "squat_cap_window"
Cohesion: 0.18
Nodes (7): Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, A filled wall band exported as two triangles (CAD fill triangulation).      Each, s15: the "steel ridge beam" line — a dashed line drawn as a row of     14.8px pi, TestDashRowBarriers, TestEmptyNetwork, TestFillSeams, triangulated_fill_band_v()

### Community 229 - "NotFound"
Cohesion: 0.11
Nodes (19): FailedPrecondition, NotFound, _doc(), load_record(), mark_awaiting_review(), mark_awaiting_scale(), mark_failed(), mark_processing() (+11 more)

### Community 230 - "bezier_arc"
Cohesion: 0.22
Nodes (9): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, The s06 topology: two single-Bezier halves whose closed tips stop         ``gap`, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing (+1 more)

### Community 231 - "TestWindowSpanOvershootRetune"
Cohesion: 0.22
Nodes (8): Change, Measurement first (`tools/census_scratch/harness.py`, seals 12/13/14/15 as multipliers of the tree's value), Numbers, Residue / not in scope (one line each, each its own iteration), Sweep (`tools/regress.py`, full corpus in four background groups, vs the baseline snapshots), The three classes every move falls into (probe_box / probe_boxes on each site), W-gate iteration 3 — step 7: `ROOM_OPENING_SEAL_PX` 12 → 15 (the retry), measured and shipped pending the user's decision, What the constant is, and why 15

### Community 232 - "W-gate recalibration — iteration 1: the census (2026-09-04)"
Cohesion: 0.25
Nodes (7): Method, Proposed iteration-2 groups (for the user's verdict — nothing changed yet), The gates that break s01 at f = 0.542 — refreshed on today's code, THE TABLE, The two worked instances, refreshed, W-gate recalibration — iteration 1: the census (2026-09-04), What the census says

### Community 233 - "W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)"
Cohesion: 0.25
Nodes (7): Numbers, Prose updated, Residue / not in scope, Sweep (four background groups vs. the main snapshots), Tests (fast tier, each proven to bite), The four moves, W-gate recalibration, iteration 2 — checkpoint: Group 1 (safe reference moves)

### Community 235 - "TestMinWidthNegativeControl"
Cohesion: 0.18
Nodes (9): _prune_arc_spurs(), Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun (+1 more)

### Community 236 - "W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto")"
Cohesion: 0.22
Nodes (8): Net effect on s04 (from the crops, my verdicts), Numbers, Residue / not in scope (one line each, each its own iteration), Sweep (`tools/regress.py`, full corpus in four background groups, vs the main baseline), The rule that the measurement supports (`detection/rooms.py::_is_door_lining`), The seal retry — NOT attempted, and why, W-gate iteration 3 — step 2: the seal-15 sites measured; the corner door lining (was "hinge-less swing-side veto"), What the measurement said (the brief's premise was wrong, twice)

### Community 237 - ".collect"
Cohesion: 0.12
Nodes (19): collect_sheets(), has_floor_plan(), is_unclassified(), page_dirs(), Path, Turning a finished run_extract output tree into wire sheets.  Only pages the reg, True when nothing on the page carries a classification.      pipeline.resolve_pa, _read_json() (+11 more)

### Community 238 - "W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale"
Cohesion: 0.25
Nodes (7): Numbers, Residue / not in scope (one line each), s01 rooms — four confirmed rooms lost at f = 0.542, Sweep, W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale, What the four rooms are actually lost through (measured), What this means for `_gate_denominator`

### Community 240 - "ablate.py"
Cohesion: 0.50
Nodes (3): main(), mult_for(), Per-constant ablations.    python ablate.py s01 s01mode   # f=0.542 full, scale-

### Community 241 - "resolve_page_regions"
Cohesion: 0.19
Nodes (8): The uniform scale factor of a rotate+scale transform. hypot is exact for     the, transform_scale(), Extraction puts geometry in the same frame as the declared page size.  page.get_, A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestPageTransform, write_rotated_pdf()

### Community 242 - "TestBandPocket"
Cohesion: 0.19
Nodes (5): A chimney breast / pier drawn as a closed box on the room side of a     wall ban, A window reveal in a cavity wall (s17 rooms 0015/0034): the wall is     drawn as, TestBandPocket, TestWallRecess, text_span()

### Community 243 - "artifacts.py"
Cohesion: 0.07
Nodes (19): artifact_names(), _content_type(), object_path(), page_prefix(), Path, Uploading a run's outputs to Cloud Storage.  Layout is customers/{customerId}/ta, Upload one page's artefacts. Absent files are skipped, not errors:     page.svg, summary.json and warnings.json live at the run root, and run_extract     writes (+11 more)

### Community 244 - "probe_plugs.py"
Cohesion: 0.28
Nodes (4): apply_labels(), Apply a labelling response to a room list.      Returns new Entity objects — the, response(), TestApplyLabels

### Community 245 - "mult_summary.py"
Cohesion: 0.53
Nodes (5): cell(), damage(), load(), main(), Summarise abl/<slug>_mult.jsonl: per field x sheet, the damage at each multiplie

### Community 246 - "probe_tails.py"
Cohesion: 0.33
Nodes (6): axial_extent(), kept_plugs_for(), measure_tail(), probe_tails.py <slug> [SEAL_PX ...] [--all]  W-gate iteration 3 step 5 — how far, ux,uy point OUTWARD from the corner along the edge line., (min, max) projection of every vertex of geom onto the axis u from origin.

### Community 248 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.38
Nodes (5): collect_room_spans(), One span list per room, in room order — the model's whole input.      A span qua, room(), span(), TestCollectRoomSpans

### Community 249 - "TestSlugForPath"
Cohesion: 0.21
Nodes (8): True when a wall FACE line runs unbroken through the bbox span.      A real wind, _wall_runs_through(), TestCrossGates, _clean(), main(), Record, per sheet, the populations each scaled gate discriminates, with world-mm, Annotate each entity with confirmed / fp / unreviewed / deferred., verdicts()

### Community 250 - "overrides"
Cohesion: 0.17
Nodes (4): _alive(), TestBuildExtractCommand, TestCeilingHeightFlag, TestRunWithGroupKill

### Community 251 - "_dedupe_openings"
Cohesion: 0.50
Nodes (4): _area(), _dedupe_openings(), BBox, Suppress overlapping detections from duplicate cap pairs (greedy NMS).      Dupl

### Community 252 - "_stroke_percentile_rank"
Cohesion: 0.33
Nodes (5): label_rooms(), One text-only API call for the whole page. Returns labelled rooms +     warnings, FakeClient, Stands in for google.genai's client — records the call, returns text., TestLabelRooms

### Community 253 - "TestFaceCollection"
Cohesion: 0.22
Nodes (3): A filled wall band the exporter triangulated into two rings that     each carry, TestFaceCollection, triangulated_band_h()

### Community 254 - "_plane_stamp"
Cohesion: 0.25
Nodes (6): _plane_stamp(), Bbox short-end edges of a sliding door: across the wall, never wall plane., The plug-less fallback seal, restricted to the door's wall-plane edges.      A d, How far, along (ux, uy) from corner, the material a plug tail touches runs., _sliding_end_edges(), _tail_material_end()

### Community 255 - "render_page_svg"
Cohesion: 0.43
Nodes (3): MuPDF's own vector redraw of the page, in render.png's coordinate space.      Sa, render_page_svg(), TestRenderPageSvg

### Community 256 - "swing_door"
Cohesion: 0.36
Nodes (4): prim(), Quarter-arc + a double-line leaf, as a faithful export at any scale.      radius, swing_door(), TestFaithfulExportDetection

### Community 257 - "test_scale_no_prompt.py"
Cohesion: 0.25
Nodes (3): Unattended runs must never stop to ask for a scale.  sys.stdin.isatty() cannot c, TestBatchNeverPrompts, TestRunExtractDefault

### Community 259 - "normalize_bbox"
Cohesion: 0.38
Nodes (7): _apply(), _as_transform(), normalize_bbox(), normalize_point(), BBox, Transform an axis-aligned box and re-normalise it.      A 90/270 rotation maps c, Transform

### Community 260 - "_far_wall_network"
Cohesion: 0.29
Nodes (4): _far_wall_network(), Minimal non-empty wall network located far from the doors under test., A single_line_leaf door with no surrounding wall AND no nearby label         is, A single_line_leaf door with no wall but WITH a nearby door label         (e.g.

### Community 261 - "_is_band_pocket"
Cohesion: 0.33
Nodes (6): _contains_text(), _edge_face_cover(), _is_band_pocket(), A text span centred inside comp: a room label, a dimension — the     draughtsper, How much of a component edge lies along a wall face: the largest     projected o, True when comp lies INSIDE a wall band's thickness — see     ROOM_BAND_POCKET_FA

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
- **681 isolated node(s):** `storage`, `sheets`, `What "generic" means here (the rule that overrides all others)`, `What counts as a win`, `1. Intake — extract the brief` (+676 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **77 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `TestMarkerRings` to `swing_door`, `Door Assembly & Heuristics Core`, `EntranceDoorTests`, `Window Detection & Tests`, `test_layout_segmenter.py`, `TestPlugSealReach`, `TestNetworkAssembly`, `client.py`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `client.py`, `Room Polygonization Internals`, `_check_opening_clear`, `Arc Cycle-Cap Pruning Tests`, `test_extraction_transform.py`, `arcs.py`, `resolver.py`, `_fit_circle_3pt`, `_arc`, `TestAnnotationPenBarriers`, `review.py`, `viewport_bbox_to_px`, `TestBlindWindowPocket`, `TestSwingHingePlugRestriction`, `TestWindowArbitraryAngle`, `test_curve_arc_garden_doors.py`, `renderer.py`, `batch_extract.py`, `TestWindowTopology`, `_collect_wall_faces`, `path`, `_vector_text_indices`, `TestWindowTightPairInterior`, `TestWindowExteriorSide`, `EntranceDoorTests`, `_is_light_pen`, `TestSheetSize`, `SplitDoubleArcTests`, `TestWindowExteriorSide`, `test_sliding_doors.py`, `test_batch_extract.py`, `TestFarSidePairs`, `_covers`, `TestFaceCollection`, `TestNetworkQueries`, `squat_cap_window`, `wall_band_h`, `TestMinWidthReference`, `bezier_arc`, `DoorV2OpeningCheckTests`, `detect_doors`, `attrib_rooms.py`, `TestMinWidthNegativeControl`, `vline`, `_find_openings`, `app.py`, `TestThickMaterialPairs`, `TestBandPocket`, `_collect_wall_faces`, `qualifying_clip_rects`, `TestNetworkQueries`, `TestSlugForPath`, `batch_extract.py`, `framed_triple_window`, `_segments_min_distance`?**
  _High betweenness centrality (0.153) - this node is a cross-community bridge._
- **Why does `run_extract()` connect `test_window_detection.py` to `test_scale_no_prompt.py`, `Double-Door Merge & Gemini Client`, `Double-Arc Split Tests`, `ShaMismatchAgainstTruthTests`, `TestCliEquivalence`, `_double_arc`, `plumber.py`, `ScaleInfo`, `PruneArcSpursTests`, `TestWindowTopology`, `TestXYCut`, `TestCheckDoorLeaves`, `TestWindowTightPairInterior`, `TakeoffRequest`, `detect_doors`, `TestAnnotationPenBarriers`, `test_door_assembly.py`, `framed_triple_window`, `render_page_svg`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `Double-Door Merge & Gemini Client` to `Door Assembly & Heuristics Core`, `EntranceDoorTests`, `Window Detection & Tests`, `TestPlugSealReach`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Arc Cycle-Cap Pruning Tests`, `test_extraction_transform.py`, `_fit_circle_3pt`, `geometry.py`, `TestAnnotationPenBarriers`, `test_layout_segmenter.py`, `TestSwingHingePlugRestriction`, `renderer.py`, `TestWindowTopology`, `_vector_text_indices`, `test_window_detection.py`, `TestWindowTightPairInterior`, `TestWindowExteriorSide`, `EntranceDoorTests`, `_is_light_pen`, `TestSheetSize`, `SplitDoubleArcTests`, `TestWindowExteriorSide`, `test_batch_extract.py`, `TestWindowTightPairInterior`, `TestNetworkQueries`, `squat_cap_window`, `TestMarkerRings`, `DoorV2OpeningCheckTests`, `detect_doors`, `vline`, `app.py`, `TestBandPocket`, `TestAnnotationPenBarriers`, `probe_plugs.py`, `qualifying_clip_rects`, `qualifying_clip_rects`, `TestSpanFilterIsLoadBearing`, `_stroke_percentile_rank`, `framed_triple_window`, `_segments_min_distance`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Are the 145 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 145 INFERRED edges - model-reasoned connections that need verification._
- **Are the 91 inferred relationships involving `Candidate` (e.g. with `_SlidePanel` and `CrossGates`) actually correct?**
  _`Candidate` has 91 INFERRED edges - model-reasoned connections that need verification._