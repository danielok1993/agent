# Graph Report - agent  (2026-09-02)

## Corpus Check
- 1317 files · ~1,373,129 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 11076 nodes · 24885 edges · 511 communities (398 shown, 113 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 651 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2f952167`
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
- [[_COMMUNITY_TestExtractPageFrame|TestExtractPageFrame]]
- [[_COMMUNITY_TestAnnotationPenBarriers|TestAnnotationPenBarriers]]
- [[_COMMUNITY_normalize_bbox|normalize_bbox]]
- [[_COMMUNITY_review.py|review.py]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestBlindWindowPocket|TestBlindWindowPocket]]
- [[_COMMUNITY_apply_classification|apply_classification]]
- [[_COMMUNITY_MANIFEST.json|MANIFEST.json]]
- [[_COMMUNITY_test_layout_segmenter.py|test_layout_segmenter.py]]
- [[_COMMUNITY_TestRequestShape|TestRequestShape]]
- [[_COMMUNITY_SweepSlugsArgumentTests|SweepSlugsArgumentTests]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY__double_arc|_double_arc]]
- [[_COMMUNITY_test_extraction_transform.py|test_extraction_transform.py]]
- [[_COMMUNITY_ScaleInfo|ScaleInfo]]
- [[_COMMUNITY_Architecture|Architecture]]
- [[_COMMUNITY_TestSwingHingePlugRestriction|TestSwingHingePlugRestriction]]
- [[_COMMUNITY_scales_in_text|scales_in_text]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_transform_scale|transform_scale]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
- [[_COMMUNITY_DoorV2OpeningCheckTests|DoorV2OpeningCheckTests]]
- [[_COMMUNITY_test_layout_golden.py|test_layout_golden.py]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY_TestThickMaterialPairs|TestThickMaterialPairs]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_PageTruth|PageTruth]]
- [[_COMMUNITY__FillRing|_FillRing]]
- [[_COMMUNITY_cluster_denominators|cluster_denominators]]
- [[_COMMUNITY_Step 5 — Per-scale-group detection for mixed-scale pages|Step 5 — Per-scale-group detection for mixed-scale pages]]
- [[_COMMUNITY_test_window_detection.py|test_window_detection.py]]
- [[_COMMUNITY_Step 1 — Widen the door Bezier aspect gate|Step 1 — Widen the door Bezier aspect gate]]
- [[_COMMUNITY_Step 2 — Retune the window span-overshoot gate (paper-space FP kill)|Step 2 — Retune the window span-overshoot gate (paper-space FP kill)]]
- [[_COMMUNITY_Step 3 — Diagnose s15's 82 false positives (read-only)|Step 3 — Diagnose s15's 82 false positives (read-only)]]
- [[_COMMUNITY_Step 4 — Recall audit on the 1100 sheets (misses are invisible to ground truth)|Step 4 — Recall audit on the 1:100 sheets (misses are invisible to ground truth)]]
- [[_COMMUNITY_TestXYCut|TestXYCut]]
- [[_COMMUNITY_TestPlumberTableBBox|TestPlumberTableBBox]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY_TestSlugForPath|TestSlugForPath]]
- [[_COMMUNITY_label_rooms|label_rooms]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_TestCrossWindowToleranceUnscaled|TestCrossWindowToleranceUnscaled]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_Handoff W-gate recalibration (the proper fix behind `fixmeasured-scale-detection-factor`)|Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)]]
- [[_COMMUNITY_test_sliding_doors.py|test_sliding_doors.py]]
- [[_COMMUNITY_fill_ring|fill_ring]]
- [[_COMMUNITY__is_light_pen|_is_light_pen]]
- [[_COMMUNITY_TestSheetSize|TestSheetSize]]
- [[_COMMUNITY_File structure|File structure]]
- [[_COMMUNITY_SplitDoubleArcTests|SplitDoubleArcTests]]
- [[_COMMUNITY_HygieneRuleTests|HygieneRuleTests]]
- [[_COMMUNITY_PruneUnreadPageOutputTests|PruneUnreadPageOutputTests]]
- [[_COMMUNITY_parse_answer|parse_answer]]
- [[_COMMUNITY_DoorAssemblyTests|DoorAssemblyTests]]
- [[_COMMUNITY_RunDirTests|RunDirTests]]
- [[_COMMUNITY_TestWindowExteriorSide|TestWindowExteriorSide]]
- [[_COMMUNITY_test_sliding_doors.py|test_sliding_doors.py]]
- [[_COMMUNITY_TestMinWidthNegativeControl|TestMinWidthNegativeControl]]
- [[_COMMUNITY_TestComponentFiltering|TestComponentFiltering]]
- [[_COMMUNITY_TestExtractImagesInstances|TestExtractImagesInstances]]
- [[_COMMUNITY_denominator_from_c|denominator_from_c]]
- [[_COMMUNITY_test_batch_extract.py|test_batch_extract.py]]
- [[_COMMUNITY_viewport_bbox_to_px|viewport_bbox_to_px]]
- [[_COMMUNITY_ParkedLeafTests|ParkedLeafTests]]
- [[_COMMUNITY__scan_striped_runs|_scan_striped_runs]]
- [[_COMMUNITY_TestSlidingScaleBehavior|TestSlidingScaleBehavior]]
- [[_COMMUNITY_TestFoldingScaleBehavior|TestFoldingScaleBehavior]]
- [[_COMMUNITY_bay_corner_post_window|bay_corner_post_window]]
- [[_COMMUNITY_TestSpanFilterIsLoadBearing|TestSpanFilterIsLoadBearing]]
- [[_COMMUNITY__fill_ring_components|_fill_ring_components]]
- [[_COMMUNITY_TakeoffRequest|TakeoffRequest]]
- [[_COMMUNITY_dev-local.ts|dev-local.ts]]
- [[_COMMUNITY_paths.ts|paths.ts]]
- [[_COMMUNITY_12. Refresh — 2026-08-30|12. Refresh — 2026-08-30]]
- [[_COMMUNITY_.error|.error]]
- [[_COMMUNITY_dependencies|dependencies]]
- [[_COMMUNITY_NotFound|NotFound]]
- [[_COMMUNITY_Multimodal Construction Estimation Implementation|Multimodal Construction Estimation Implementation]]
- [[_COMMUNITY_genkit.config.ts|genkit.config.ts]]
- [[_COMMUNITY_MainExceptionIsolationTests|MainExceptionIsolationTests]]
- [[_COMMUNITY_squat_cap_window|squat_cap_window]]
- [[_COMMUNITY_road-access-card.tsx|road-access-card.tsx]]
- [[_COMMUNITY_EstimateGenerationService|EstimateGenerationService]]
- [[_COMMUNITY_TestWindowSpanOvershootRetune|TestWindowSpanOvershootRetune]]
- [[_COMMUNITY_.collect|.collect]]
- [[_COMMUNITY_getStripeClient|getStripeClient]]
- [[_COMMUNITY_Subscription & Licensing System|Subscription & Licensing System]]
- [[_COMMUNITY_transcribe-audio.ts|transcribe-audio.ts]]
- [[_COMMUNITY_cost-zod.ts|cost-zod.ts]]
- [[_COMMUNITY_index.tsx|index.tsx]]
- [[_COMMUNITY_artifacts.py|artifacts.py]]
- [[_COMMUNITY_Schema Optimization for Construction Estimates|Schema Optimization for Construction Estimates]]
- [[_COMMUNITY_FirebaseAuthProvider|FirebaseAuthProvider]]
- [[_COMMUNITY_Virtual Scrolling Implementation for Mobile Estimates|Virtual Scrolling Implementation for Mobile Estimates]]
- [[_COMMUNITY_Wizard Folder Upload — Follow-ups|Wizard Folder Upload — Follow-ups]]
- [[_COMMUNITY_EstimateResponse|EstimateResponse]]
- [[_COMMUNITY_schema-validation-error.ts|schema-validation-error.ts]]
- [[_COMMUNITY_Mobile Estimate Layout Components|Mobile Estimate Layout Components]]
- [[_COMMUNITY_Awin  Travis Perkins Product Feed Pricing Implementation Plan|Awin / Travis Perkins Product Feed Pricing Implementation Plan]]
- [[_COMMUNITY_Awin  Travis Perkins Product Feed Pricing — Design|Awin / Travis Perkins Product Feed Pricing — Design]]
- [[_COMMUNITY_estimate-reaper.ts|estimate-reaper.ts]]
- [[_COMMUNITY_Implementation Guide Enhanced Orchestrator Extraction (Option 1)|Implementation Guide: Enhanced Orchestrator Extraction (Option 1)]]
- [[_COMMUNITY_SpoonKnowledgeIngestion|SpoonKnowledgeIngestion]]
- [[_COMMUNITY_scripts|scripts]]
- [[_COMMUNITY_seed-emulator.ts|seed-emulator.ts]]
- [[_COMMUNITY_utils.ts|utils.ts]]
- [[_COMMUNITY_isEmulatorMode|isEmulatorMode]]
- [[_COMMUNITY_use-sticky-header.ts|use-sticky-header.ts]]
- [[_COMMUNITY_Travis Perkins Alternative-Match Replace UX — Implementation Plan|Travis Perkins Alternative-Match Replace UX — Implementation Plan]]
- [[_COMMUNITY_table.tsx|table.tsx]]
- [[_COMMUNITY_Known-answer acceptance table|Known-answer acceptance table]]
- [[_COMMUNITY_material-quantity-step.ts|material-quantity-step.ts]]
- [[_COMMUNITY_assistant-api.ts|assistant-api.ts]]
- [[_COMMUNITY_xlsx-boq-export.ts|xlsx-boq-export.ts]]
- [[_COMMUNITY_⚙️ Project Standards|⚙️ Project Standards]]
- [[_COMMUNITY_Travis Perkins RAG Categorisation Fix — Implementation Plan|Travis Perkins RAG Categorisation Fix — Implementation Plan]]
- [[_COMMUNITY_QS Agent — NRM2 Material Itemisation with TP Grounding — Implementation Plan|QS Agent — NRM2 Material Itemisation with TP Grounding — Implementation Plan]]
- [[_COMMUNITY_provisioning.ts|provisioning.ts]]
- [[_COMMUNITY_Design decisions, recorded|Design decisions, recorded]]
- [[_COMMUNITY_xlsx-bom-export.ts|xlsx-bom-export.ts]]
- [[_COMMUNITY_E2E Payment System Testing Plan|E2E Payment System Testing Plan]]
- [[_COMMUNITY_export-menu.tsx|export-menu.tsx]]
- [[_COMMUNITY_use-wizard-state.ts|use-wizard-state.ts]]
- [[_COMMUNITY_TestCliEquivalence|TestCliEquivalence]]
- [[_COMMUNITY_Travis Perkins Embed Batch Fix — Implementation Plan|Travis Perkins Embed Batch Fix — Implementation Plan]]
- [[_COMMUNITY_dependencies|dependencies]]
- [[_COMMUNITY_deletion.ts|deletion.ts]]
- [[_COMMUNITY_attachment-download.ts|attachment-download.ts]]
- [[_COMMUNITY_xlsx-timeline-export.ts|xlsx-timeline-export.ts]]
- [[_COMMUNITY_Labour Rate Groups Implementation Plan|Labour Rate Groups Implementation Plan]]
- [[_COMMUNITY_Dashboard Pagination — Design|Dashboard Pagination — Design]]
- [[_COMMUNITY_site-assessment-step.test.ts|site-assessment-step.test.ts]]
- [[_COMMUNITY_set|set]]
- [[_COMMUNITY_Authentication Functions|Authentication Functions]]
- [[_COMMUNITY_1. Prompt Rewrite (`functionssrcaiagentsscope-agent.ts`)|1. Prompt Rewrite (`functions/src/ai/agents/scope-agent.ts`)]]
- [[_COMMUNITY_e2e-run.ts|e2e-run.ts]]
- [[_COMMUNITY_extract_tables_from_html|extract_tables_from_html]]
- [[_COMMUNITY_waitlist.ts|waitlist.ts]]
- [[_COMMUNITY_Takeoff as a Firebase Function — design|Takeoff as a Firebase Function — design]]
- [[_COMMUNITY_Estimate Versioning System|Estimate Versioning System]]
- [[_COMMUNITY_Labour Rate Groups — Design Spec|Labour Rate Groups — Design Spec]]
- [[_COMMUNITY_ClientNameDisplay|ClientNameDisplay]]
- [[_COMMUNITY_materials-orchestrator.test.ts|materials-orchestrator.test.ts]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_HygieneRuleTests|HygieneRuleTests]]
- [[_COMMUNITY_select.tsx|select.tsx]]
- [[_COMMUNITY_pagination.tsx|pagination.tsx]]
- [[_COMMUNITY_Material-Quantity Calculation Resilience — Design|Material-Quantity Calculation Resilience — Design]]
- [[_COMMUNITY_Design QS owns the material list; sub-agent becomes a pure Travis Perkins matcher|Design: QS owns the material list; sub-agent becomes a pure Travis Perkins matcher]]
- [[_COMMUNITY_Project Timeline Export — Design|Project Timeline Export — Design]]
- [[_COMMUNITY_Design|Design]]
- [[_COMMUNITY_5. Verification runs|5. Verification runs]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_QS Material-Quantity Chain Fix Implementation Plan|QS Material-Quantity Chain Fix Implementation Plan]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_devDependencies|devDependencies]]
- [[_COMMUNITY_directives-zod.ts|directives-zod.ts]]
- [[_COMMUNITY_upload-step.tsx|upload-step.tsx]]
- [[_COMMUNITY_project-details-step.tsx|project-details-step.tsx]]
- [[_COMMUNITY_api.ts|api.ts]]
- [[_COMMUNITY_build_ink_map|build_ink_map]]
- [[_COMMUNITY_Decisions taken during planning (all measured — read before Task 1)|Decisions taken during planning (all measured — read before Task 1)]]
- [[_COMMUNITY_api-client.ts|api-client.ts]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Preliminaries as a Separate Cost Summary Line|Preliminaries as a Separate Cost Summary Line]]
- [[_COMMUNITY_TP Pack-Size Pricing — Findings, Progress & Next Steps|TP Pack-Size Pricing — Findings, Progress & Next Steps]]
- [[_COMMUNITY_target.ts|target.ts]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_process-v2.test.ts|process-v2.test.ts]]
- [[_COMMUNITY_estimate-history-layout.tsx|estimate-history-layout.tsx]]
- [[_COMMUNITY_create-comment.ts|create-comment.ts]]
- [[_COMMUNITY_dictation-textarea.tsx|dictation-textarea.tsx]]
- [[_COMMUNITY_Firestore Security Rules Tests|Firestore Security Rules Tests]]
- [[_COMMUNITY_QS-Owns-Materials  TP-Matcher Implementation Plan|QS-Owns-Materials / TP-Matcher Implementation Plan]]
- [[_COMMUNITY_Slim the Materials Sub-Agent input to a minimal matcher projection|Slim the Materials Sub-Agent input to a minimal matcher projection]]
- [[_COMMUNITY_Bill of Materials Export — Design|Bill of Materials Export — Design]]
- [[_COMMUNITY_tenant.ts|tenant.ts]]
- [[_COMMUNITY_migrate-labour-rates-to-groups.ts|migrate-labour-rates-to-groups.ts]]
- [[_COMMUNITY_use-project-markup-editor.ts|use-project-markup-editor.ts]]
- [[_COMMUNITY_use-estimate-history.ts|use-estimate-history.ts]]
- [[_COMMUNITY_estimate-history.tsx|estimate-history.tsx]]
- [[_COMMUNITY_estimate-pdf-service.ts|estimate-pdf-service.ts]]
- [[_COMMUNITY_EstimateTransactionService|EstimateTransactionService]]
- [[_COMMUNITY_Preview Route Template Split Implementation Plan|Preview Route Template Split Implementation Plan]]
- [[_COMMUNITY_Design|Design]]
- [[_COMMUNITY_uploader.py|uploader.py]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_QS `sourceRoomId` Validation + Repair-Wrapper Top-Key Fix — Implementation Plan|QS `sourceRoomId` Validation + Repair-Wrapper Top-Key Fix — Implementation Plan]]
- [[_COMMUNITY_Task Order Rationale|Task Order Rationale]]
- [[_COMMUNITY_Site Access Assessment Implementation Plan|Site Access Assessment Implementation Plan]]
- [[_COMMUNITY_Design|Design]]
- [[_COMMUNITY_TP ingest quota-aware retries and a readable dev run|TP ingest: quota-aware retries and a readable dev run]]
- [[_COMMUNITY_use-estimate-mutation.ts|use-estimate-mutation.ts]]
- [[_COMMUNITY_RemoteConfigService|RemoteConfigService]]
- [[_COMMUNITY_Authentication Provider System|Authentication Provider System]]
- [[_COMMUNITY_Tasks|Tasks]]
- [[_COMMUNITY_Schema-Repair Wrapper (Partial P0) Implementation Plan|Schema-Repair Wrapper (Partial P0) Implementation Plan]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Remove London Weighting & Strengthen NRM2 Guidance|Remove London Weighting & Strengthen NRM2 Guidance]]
- [[_COMMUNITY_Pipeline Checkpointing — Design|Pipeline Checkpointing — Design]]
- [[_COMMUNITY_core-role-card.tsx|core-role-card.tsx]]
- [[_COMMUNITY_AILogger|AILogger]]
- [[_COMMUNITY_package.json|package.json]]
- [[_COMMUNITY_to-estimate-list-row.ts|to-estimate-list-row.ts]]
- [[_COMMUNITY_auth.tsx|auth.tsx]]
- [[_COMMUNITY_xlsx-boq-export.test.ts|xlsx-boq-export.test.ts]]
- [[_COMMUNITY_Deploying the takeoff callable|Deploying the takeoff callable]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Estimate Schema-Validation Resilience Implementation Plan|Estimate Schema-Validation Resilience Implementation Plan]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Materials Sub-Agent Multi-Section Batching — Design|Materials Sub-Agent Multi-Section Batching — Design]]
- [[_COMMUNITY_Bill of Materials — remove VAT from totals|Bill of Materials — remove VAT from totals]]
- [[_COMMUNITY_generate-estimate-pdf.ts|generate-estimate-pdf.ts]]
- [[_COMMUNITY_TableRecord|TableRecord]]
- [[_COMMUNITY_serializer.py|serializer.py]]
- [[_COMMUNITY_page|page]]
- [[_COMMUNITY__widest_gap|_widest_gap]]
- [[_COMMUNITY_Travis Perkins RAG — Investigation & Fix Plan|Travis Perkins RAG — Investigation & Fix Plan]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_backfill-tp-embedding-vector.ts|backfill-tp-embedding-vector.ts]]
- [[_COMMUNITY_invoice-history.tsx|invoice-history.tsx]]
- [[_COMMUNITY_notification.stories.tsx|notification.stories.tsx]]
- [[_COMMUNITY_db.ts|db.ts]]
- [[_COMMUNITY_Changelog|Changelog]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_import-collection-to-live.ts|import-collection-to-live.ts]]
- [[_COMMUNITY_geocode.ts|geocode.ts]]
- [[_COMMUNITY_labour-rate.ts|labour-rate.ts]]
- [[_COMMUNITY_TestWindowTightPairInterior|TestWindowTightPairInterior]]
- [[_COMMUNITY__attach_text_spans|_attach_text_spans]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_Travis Perkins RAG — Categorisation Fix Design|Travis Perkins RAG — Categorisation Fix Design]]
- [[_COMMUNITY_Investigation Timeline|Investigation Timeline]]
- [[_COMMUNITY_run-tp-ingest.ts|run-tp-ingest.ts]]
- [[_COMMUNITY_estimate-status-cell.tsx|estimate-status-cell.tsx]]
- [[_COMMUNITY_failure-handler.test.ts|failure-handler.test.ts]]
- [[_COMMUNITY_complete-google-signup.test.ts|complete-google-signup.test.ts]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_Bill of Materials — Remove VAT Implementation Plan|Bill of Materials — Remove VAT Implementation Plan]]
- [[_COMMUNITY_PR body|PR body]]
- [[_COMMUNITY_QS Agent — NRM2 Material Itemisation with Travis Perkins Grounding|QS Agent — NRM2 Material Itemisation with Travis Perkins Grounding]]
- [[_COMMUNITY_Testing|Testing]]
- [[_COMMUNITY_Workflow — the standard dev loop|Workflow — the standard dev loop]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_package.json|package.json]]
- [[_COMMUNITY_migrate-users-to-credits.ts|migrate-users-to-credits.ts]]
- [[_COMMUNITY_tsconfig.json|tsconfig.json]]
- [[_COMMUNITY_directives-pipeline.integration.test.ts|directives-pipeline.integration.test.ts]]
- [[_COMMUNITY_compilerOptions|compilerOptions]]
- [[_COMMUNITY_assistant.tsx|assistant.tsx]]
- [[_COMMUNITY_FakeBlob|FakeBlob]]
- [[_COMMUNITY_Repository Instructions|Repository Instructions]]
- [[_COMMUNITY_Key Components|Key Components]]
- [[_COMMUNITY_Slim Materials Sub-Agent Input Schema Implementation Plan|Slim Materials Sub-Agent Input Schema Implementation Plan]]
- [[_COMMUNITY_Follow-up PREVENT estimates from getting stuck (root-cause work)|Follow-up: PREVENT estimates from getting stuck (root-cause work)]]
- [[_COMMUNITY_Materials sub-agent|Materials sub-agent]]
- [[_COMMUNITY_Schema changes|Schema changes]]
- [[_COMMUNITY_package.json|package.json]]
- [[_COMMUNITY_packages|packages]]
- [[_COMMUNITY_index.tsx|index.tsx]]
- [[_COMMUNITY_file-converters.ts|file-converters.ts]]
- [[_COMMUNITY_firestore-rules.test.ts|firestore-rules.test.ts]]
- [[_COMMUNITY_FakeDoc|FakeDoc]]
- [[_COMMUNITY_._spy_kwargs|._spy_kwargs]]
- [[_COMMUNITY_Mobile Action Sheet Editing Implementation|Mobile Action Sheet Editing Implementation]]
- [[_COMMUNITY_Global Constraints|Global Constraints]]
- [[_COMMUNITY_Cost engineer changes|Cost engineer changes]]
- [[_COMMUNITY_Main QS agent prompt changes|Main QS agent prompt changes]]
- [[_COMMUNITY_folder-upload.spec.ts|folder-upload.spec.ts]]
- [[_COMMUNITY_verify-pallet-quantity-verdicts.ts|verify-pallet-quantity-verdicts.ts]]
- [[_COMMUNITY_PipelineCheckpointer|PipelineCheckpointer]]
- [[_COMMUNITY_validation.ts|validation.ts]]
- [[_COMMUNITY_estimate-identity.ts|estimate-identity.ts]]
- [[_COMMUNITY_QuadPerimeterTests|QuadPerimeterTests]]
- [[_COMMUNITY_TestSheetIsScaled|TestSheetIsScaled]]
- [[_COMMUNITY_User Experience Features|User Experience Features]]
- [[_COMMUNITY_Implementation Details|Implementation Details]]
- [[_COMMUNITY_Architecture|Architecture]]
- [[_COMMUNITY_Implementation Plan|Implementation Plan]]
- [[_COMMUNITY_pool.ts|pool.ts]]
- [[_COMMUNITY_reset-user-password.ts|reset-user-password.ts]]
- [[_COMMUNITY_EvaluatedConfig|EvaluatedConfig]]
- [[_COMMUNITY_directives-block-wiring.test.ts|directives-block-wiring.test.ts]]
- [[_COMMUNITY_main|main]]
- [[_COMMUNITY_head.tsx|head.tsx]]
- [[_COMMUNITY_estimate-history.test.tsx|estimate-history.test.tsx]]
- [[_COMMUNITY_change-subscription-plan.ts|change-subscription-plan.ts]]
- [[_COMMUNITY_Future Enhancements|Future Enhancements]]
- [[_COMMUNITY_Testing Strategy|Testing Strategy]]
- [[_COMMUNITY_Performance Considerations|Performance Considerations]]
- [[_COMMUNITY_Review stages|Review stages]]
- [[_COMMUNITY_TP retrieval — two tools|TP retrieval — two tools]]
- [[_COMMUNITY_export-emulator-collection.ts|export-emulator-collection.ts]]
- [[_COMMUNITY_firebase-cleanup.test.ts|firebase-cleanup.test.ts]]
- [[_COMMUNITY_firebase-service-paging.test.ts|firebase-service-paging.test.ts]]
- [[_COMMUNITY_1.34.0(httpsgithub.comnestimate-ainestimatecomparev1.33.2...v1.34.0) (2026-07-30)|[1.34.0](https://github.com/nestimate-ai/nestimate/compare/v1.33.2...v1.34.0) (2026-07-30)]]
- [[_COMMUNITY_1.36.0(httpsgithub.comnestimate-ainestimatecomparev1.35.1...v1.36.0) (2026-08-04)|[1.36.0](https://github.com/nestimate-ai/nestimate/compare/v1.35.1...v1.36.0) (2026-08-04)]]
- [[_COMMUNITY_1.38.0(httpsgithub.comnestimate-ainestimatecomparev1.37.0...v1.38.0) (2026-08-04)|[1.38.0](https://github.com/nestimate-ai/nestimate/compare/v1.37.0...v1.38.0) (2026-08-04)]]
- [[_COMMUNITY_1.39.0(httpsgithub.comnestimate-ainestimatecomparev1.38.0...v1.39.0) (2026-08-04)|[1.39.0](https://github.com/nestimate-ai/nestimate/compare/v1.38.0...v1.39.0) (2026-08-04)]]
- [[_COMMUNITY_1.40.0(httpsgithub.comnestimate-ainestimatecomparev1.39.0...v1.40.0) (2026-08-12)|[1.40.0](https://github.com/nestimate-ai/nestimate/compare/v1.39.0...v1.40.0) (2026-08-12)]]
- [[_COMMUNITY_1.42.0(httpsgithub.comnestimate-ainestimatecomparev1.41.0...v1.42.0) (2026-08-26)|[1.42.0](https://github.com/nestimate-ai/nestimate/compare/v1.41.0...v1.42.0) (2026-08-26)]]
- [[_COMMUNITY_1.43.0(httpsgithub.comnestimate-ainestimatecomparev1.42.2...v1.43.0) (2026-09-01)|[1.43.0](https://github.com/nestimate-ai/nestimate/compare/v1.42.2...v1.43.0) (2026-09-01)]]
- [[_COMMUNITY_Configuration|Configuration]]
- [[_COMMUNITY_Integration with Existing System|Integration with Existing System]]
- [[_COMMUNITY_Troubleshooting|Troubleshooting]]
- [[_COMMUNITY_Dependencies|Dependencies]]
- [[_COMMUNITY_Migration Guide|Migration Guide]]
- [[_COMMUNITY_Error handling|Error handling]]
- [[_COMMUNITY_jest.live.config.js|jest.live.config.js]]
- [[_COMMUNITY_backfill-estimate-list-fields.ts|backfill-estimate-list-fields.ts]]
- [[_COMMUNITY_check-prod-data.ts|check-prod-data.ts]]
- [[_COMMUNITY_inspect-embedding.ts|inspect-embedding.ts]]
- [[_COMMUNITY_qs-materials-golden.integration.test.ts|qs-materials-golden.integration.test.ts]]
- [[_COMMUNITY_estimate-transaction-service.test.ts|estimate-transaction-service.test.ts]]
- [[_COMMUNITY_storage-rules.test.ts|storage-rules.test.ts]]
- [[_COMMUNITY_vite-env.d.ts|vite-env.d.ts]]
- [[_COMMUNITY_preview.tsx|preview.tsx]]
- [[_COMMUNITY_README|README.md]]
- [[_COMMUNITY_1.28.0(httpsgithub.comnestimate-ainestimatecomparev1.27.0...v1.28.0) (2026-07-23)|[1.28.0](https://github.com/nestimate-ai/nestimate/compare/v1.27.0...v1.28.0) (2026-07-23)]]
- [[_COMMUNITY_1.29.0(httpsgithub.comnestimate-ainestimatecomparev1.28.1...v1.29.0) (2026-07-23)|[1.29.0](https://github.com/nestimate-ai/nestimate/compare/v1.28.1...v1.29.0) (2026-07-23)]]
- [[_COMMUNITY_1.29.1(httpsgithub.comnestimate-ainestimatecomparev1.29.0...v1.29.1) (2026-07-23)|[1.29.1](https://github.com/nestimate-ai/nestimate/compare/v1.29.0...v1.29.1) (2026-07-23)]]
- [[_COMMUNITY_1.30.0(httpsgithub.comnestimate-ainestimatecomparev1.29.1...v1.30.0) (2026-07-27)|[1.30.0](https://github.com/nestimate-ai/nestimate/compare/v1.29.1...v1.30.0) (2026-07-27)]]
- [[_COMMUNITY_1.32.0(httpsgithub.comnestimate-ainestimatecomparev1.31.0...v1.32.0) (2026-07-29)|[1.32.0](https://github.com/nestimate-ai/nestimate/compare/v1.31.0...v1.32.0) (2026-07-29)]]
- [[_COMMUNITY_1.33.1(httpsgithub.comnestimate-ainestimatecomparev1.33.0...v1.33.1) (2026-07-29)|[1.33.1](https://github.com/nestimate-ai/nestimate/compare/v1.33.0...v1.33.1) (2026-07-29)]]
- [[_COMMUNITY_1.35.0(httpsgithub.comnestimate-ainestimatecomparev1.34.0...v1.35.0) (2026-07-30)|[1.35.0](https://github.com/nestimate-ai/nestimate/compare/v1.34.0...v1.35.0) (2026-07-30)]]
- [[_COMMUNITY_1.35.1(httpsgithub.comnestimate-ainestimatecomparev1.35.0...v1.35.1) (2026-08-04)|[1.35.1](https://github.com/nestimate-ai/nestimate/compare/v1.35.0...v1.35.1) (2026-08-04)]]
- [[_COMMUNITY_1.37.0(httpsgithub.comnestimate-ainestimatecomparev1.36.0...v1.37.0) (2026-08-04)|[1.37.0](https://github.com/nestimate-ai/nestimate/compare/v1.36.0...v1.37.0) (2026-08-04)]]
- [[_COMMUNITY_1.41.0(httpsgithub.comnestimate-ainestimatecomparev1.40.0...v1.41.0) (2026-08-13)|[1.41.0](https://github.com/nestimate-ai/nestimate/compare/v1.40.0...v1.41.0) (2026-08-13)]]
- [[_COMMUNITY_1.42.1(httpsgithub.comnestimate-ainestimatecomparev1.42.0...v1.42.1) (2026-08-26)|[1.42.1](https://github.com/nestimate-ai/nestimate/compare/v1.42.0...v1.42.1) (2026-08-26)]]
- [[_COMMUNITY_1.42.2(httpsgithub.comnestimate-ainestimatecomparev1.42.1...v1.42.2) (2026-08-26)|[1.42.2](https://github.com/nestimate-ai/nestimate/compare/v1.42.1...v1.42.2) (2026-08-26)]]
- [[_COMMUNITY_CLAUDE|CLAUDE.md]]
- [[_COMMUNITY_extract-estimate.py|extract-estimate.py]]
- [[_COMMUNITY_playwright.config.ts|playwright.config.ts]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY_setup-worktree.sh|setup-worktree.sh]]
- [[_COMMUNITY_exceljs-browser.d.ts|exceljs-browser.d.ts]]
- [[_COMMUNITY_getTeams|getTeams]]
- [[_COMMUNITY_getTeamsQueryOptions|getTeamsQueryOptions]]
- [[_COMMUNITY_useTeams|useTeams]]

## God Nodes (most connected - your core abstractions)
1. `cn()` - 181 edges
2. `EstimateResponse` - 163 edges
3. `PathPrimitive` - 145 edges
4. `PageData` - 113 edges
5. `detect_wall_network()` - 109 edges
6. `PageScales` - 91 edges
7. `Candidate` - 87 edges
8. `Button` - 75 edges
9. `detect_windows()` - 72 edges
10. `rooms_for()` - 71 edges

## Surprising Connections (you probably didn't know these)
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` --semantically_similar_to--> `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [INFERRED] [semantically similar]
  5-1133-WD03.pdf → floor-plans.pdf
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` --references--> `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf → 5-1133-WD03.pdf
- `run()` --indirect_call--> `key()`  [INFERRED]
  .review/nestimate-pr-180/functions/scripts/run-tp-ingest.ts → tools/compare_entities.py
- `tokenAppearsOnCodeLine()` --indirect_call--> `seg()`  [INFERRED]
  .review/nestimate-pr-180/functions/scripts/sync-tracks.ts → tests/test_cross_validate.py
- `scanForResidual()` --indirect_call--> `seg()`  [INFERRED]
  .review/nestimate-pr-180/functions/scripts/sync-tracks.ts → tests/test_cross_validate.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **5-1133-WD03 proposed lower ground floor: walls, windows, doors** — 5_1133_wd03, 5_1133_wd03_cavity_walls, 5_1133_wd03_windows, 5_1133_wd03_folding_sliding_doors [EXTRACTED 1.00]
- **floor-plans proposed ground & first floor plans with rooms and rooflights** — floor_plans, floor_plans_ground_floor, floor_plans_first_floor, floor_plans_velux [EXTRACTED 1.00]

## Communities (511 total, 113 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.08
Nodes (45): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _load_font(), BBox, Image, Room entities carry their closed polygon; draw its true shape instead     of the, FreeTypeFont (+37 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.04
Nodes (74): BaseModal(), FormControl, FormDescription, FormFieldContext, FormFieldContextValue, FormItem, FormItemContext, FormItemContextValue (+66 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.04
Nodes (76): ResetPasswordRoute(), Checkbox, CheckboxProps, Error(), ErrorProps, FieldWrapper(), FieldWrapperPassThroughProps, FieldWrapperProps (+68 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.05
Nodes (80): main(), db, db, EstimateAgentStep, complianceAgent, costEngineerAgent, documentAgent, imageAgent (+72 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.14
Nodes (12): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+4 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.17
Nodes (20): applyRewrite(), bail(), buildIdentifierRegex(), confirmContinue(), dirtyTargets(), escapeRegex(), extractCodeSegments(), FilePair (+12 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.05
Nodes (28): _is_arc_like(), CrossGates, World-space cross-validation gates, pre-multiplied by the factor.      Only the, bbox_aspect(), bezier_arc(), BezierAspectGateTests, line(), path() (+20 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.12
Nodes (24): init_client(), Vertex AI client construction.  Per-candidate validation was removed on 2026-07-, getClientDisplayName(), getClientPersonalName(), ClientsTableProps, ClientCard(), ClientCardProps, ClientsList() (+16 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.11
Nodes (19): _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests (+11 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.18
Nodes (6): A doorway whose jamb is a one-wall-thickness nib (s03 door_0018)., Rect room with a 45px doorway gap in the top wall (240..285)., TestClosedRooms, TestJambNib, wall_band_h(), wall_band_v()

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.07
Nodes (25): apply_classification(), Apply a classification response to a region list.      Returns new Region object, _CapturingClient, Stands in for genai.Client, recording the config it was called with., The response must be schema-constrained at decode time.      Plain JSON mode doe, region(), response(), TestApplyClassification (+17 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.12
Nodes (22): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+14 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.12
Nodes (14): leaf_pair_door(), leaf_pair (detection/doors/sliding.py) reads gates.DOOR_SLIDE_PANEL_MIN_THICKNES, Two parallel panel rectangles in-band with partial overlap (sliding.py's     lea, TestSlidingScaleBehavior, detect(), LeafPairTests, ParkedLeafTests, PocketLeafTests (+6 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.15
Nodes (14): _bridge_white_runs(), _equivalent_sides(), _is_dashed(), True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., (short, long) of the rectangle with this polygon's area and perimeter.      The, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      gate, _bridge_white_runs is detect_rooms's ONLY production call site     (detection/ro, TestBridgeWhiteRunsGapScaling (+6 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.08
Nodes (29): SynthesizerOutputSchema, ComplianceOutput, EquipmentItemSchema, EstimateResponse, LabourItem, LabourItemSchema, LatLonSchema, MaterialItemSchema (+21 more)

### Community 17 - "arcs.py"
Cohesion: 0.13
Nodes (19): _cache_file(), _from_dicts(), load_stored(), match_stored(), _merge(), BBox, Path, Tier 4 persistence — where a scale the user typed is kept.  Two back-ends, mirro (+11 more)

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
Nodes (32): _effective_denominator(), _gate_denominator(), One detection factor per page: which scale governs the ink detection sees.  Dete, Nominal beats raw so 1:50 sheets compute factor 1.0 EXACTLY., The denominator allowed to drive gate scaling, or None to abstain.      Only a D, Drawing-scale resolution: read a 1:N scale from the PDF and bind it to a plan., _fallback_info(), The resolution ladder, and how a scale binds to a floor plan.  Binding is what m (+24 more)

### Community 22 - "geometry.py"
Cohesion: 0.08
Nodes (24): apply_labels(), build_request_text(), collect_room_spans(), is_grounded(), is_noise_span(), label_rooms(), The one user part: every room's spans as JSON, keyed by ordinal., True when every word of the label appears in that room's own spans.      This ma (+16 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.06
Nodes (54): getClientSecondaryName(), BaseModalProps, Button, ConfirmationDialogProps, ConfirmationDialog(), ConfirmationDialogProps, Danger, Info (+46 more)

### Community 31 - "README stub"
Cohesion: 0.12
Nodes (15): 1. Sweep, 2. Open the review image, 3. Record the verdicts, After reviewing, Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional) (+7 more)

### Community 34 - "detect_windows"
Cohesion: 0.14
Nodes (10): paving_field(), Four wall bands forming a closed rectangular room (outer faces at the     given, Running-bond paving: continuous course lines, staggered joint lines.      Mirror, Striped fields (paving bonds, tile fields, treads) are not walls., Stroke-color pen identity: pairing, faint-ink demotion, dimension     chains, an, rect_room(), TestLatticeDemotion, TestNetworkAssembly (+2 more)

### Community 35 - "plumber.py"
Cohesion: 0.04
Nodes (51): _component_indices(), _dedupe_door_components(), _merge_double_door_assemblies(), Prefer the strongest door when two candidates use the same primitives., Parse an evidence bbox value defensively; return None on any invalid shape., Merge pairs of adjacent single-door assemblies into double-swing candidates., _safe_bbox(), Drop window candidates that materially sit on a detected door.      Door symbols (+43 more)

### Community 36 - "_projected_interval"
Cohesion: 0.09
Nodes (33): ClientEditModal(), ClientEditModalProps, CustomInput(), CustomTextarea(), ClientEditSheet, ClientEditSheetProps, MobileInput(), MobileTextarea() (+25 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.24
Nodes (6): build_ink_map(), page(), path(), TestBuildInkMap, TestIncludeTextFlag, TestPageSpanning

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.12
Nodes (23): cache_file(), cache_key(), load_labels(), Path, On-disk cache of room labels, keyed by page content AND the room polygons the la, Stable digest of the room outlines a labelling was made against.      A cached l, room_geometry_hash(), save_labels() (+15 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.07
Nodes (35): UploadedFileReference, AttachmentFileCard(), AttachmentFileCardProps, AttachmentPictureTile(), AttachmentPictureTileProps, DesktopStickyHeader(), DesktopStickyHeaderProps, imageLoadCache (+27 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.15
Nodes (12): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 1c. Bay / corner frames — the square corner post (s10 lounge), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf (+4 more)

### Community 44 - "renderer.py"
Cohesion: 0.04
Nodes (92): derivePackLinePrice(), PackLinePrice, PictureMetadata, SourceAttribution, SourceType, set, IconButton, IconButtonProps (+84 more)

### Community 98 - "vline"
Cohesion: 0.12
Nodes (15): 2026-08-04 — Clip-cut region splitting fix + batch timeout investigation, 2026-08-05 addendum — fixes landed, attribution corrected, `batch_extract.py` orphan bug (found, not yet fixed), Bug, Fix, Gemini call-boundedness audit (user asked "no infinite AI calls"), Loop-termination audit (user asked "no infinite loops"), Part 1 — Fix (done): clip edges sliced drawings they never touch (+7 more)

### Community 99 - "wall_band_h"
Cohesion: 0.10
Nodes (30): _accept_jamb_rings(), _building_masses(), detect_rooms(), _drop_window_exterior_sides(), _folding_chain_gap_plug(), _free_space_components(), _is_door_lining(), _is_wall_recess() (+22 more)

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.17
Nodes (11): Diagnosis (measured 2026-08-13, this is the evidence the plan argues from), Global Constraints, Paths-Only Segmentation Retry (s15 Text-Bridged Gutters) Implementation Plan, Self-Review, Task 0: Branch setup, Task 1: `build_ink_map(include_text=...)`, Task 2: Extract `_boxes_from_cut` (pure refactor), Task 3: `_attach_text_spans` (+3 more)

### Community 101 - "TestMarkerRings"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record whether a line segment passed the polyline-arc length filter., Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive. (+5 more)

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.13
Nodes (14): detect(), fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack(), ParkedStackPairTests (+6 more)

### Community 103 - "PathPrimitive"
Cohesion: 0.20
Nodes (11): pending(), Unreviewed detections, keyed by 1-based page then entity type.      Pages and ty, This sheet cannot be reviewed right now. Report it and move on., No persisted sweep output for this slug., The persisted output does not describe the PDF now on disk., ReviewBlocked, SweepOutputMissing, SweepOutputStale (+3 more)

### Community 104 - "detect_doors"
Cohesion: 0.04
Nodes (62): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+54 more)

### Community 105 - "PageData"
Cohesion: 0.21
Nodes (7): getConfiguredStorage(), LogoService, key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.18
Nodes (11): TruthItem, Regression corpus: fixture resolution, ground truth, matching, and the sweep., iou(), match_entities(), MatchResult, BBox, Matching ground-truth items to pipeline output.  Entity ids are ordinal — door_0, entity() (+3 more)

### Community 107 - "vline"
Cohesion: 0.06
Nodes (34): _check_opening_clear(), _line_nears_bridge_interior(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, True when some point of segment p1-p2 lies within buffer_px of the bridge     li, detect_doors(), Detect doors. scale_factor scales the world-space gates (1.0 = 1:50).      Built, _curve(), CurveArcGardenDoorTests (+26 more)

### Community 108 - "_bridge_white_runs"
Cohesion: 0.06
Nodes (28): assess_scale(), check_dimensions(), check_door_leaves(), dimension_matches(), DimensionMatch, _fmt_scale(), leaf_width_px(), parse_dimension_mm() (+20 more)

### Community 109 - "_find_openings"
Cohesion: 0.03
Nodes (94): _dedupe_by_perp(), detect_windows(), _facing_cap_pairs(), _find_openings(), _frame_axes(), _glaze_index(), _merge_mullion_chains(), World-space window gates, pre-multiplied by the detection factor.      Exactly O (+86 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.19
Nodes (6): DetectionScale, _door(), room_polys holds unscaled rooms too, so the first assigned room can         be t, Referential integrity must hold in BOTH directions: if the opening         names, _room(), TestComputeTakeoff

### Community 111 - "app.py"
Cohesion: 0.02
Nodes (241): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some, Estimate sweep angle of a Bézier arc from its endpoints and estimated center. (+233 more)

### Community 112 - "RotatedPdfTestCase"
Cohesion: 0.18
Nodes (11): Path, Turning a human's selections into committed ground truth.  Pure and terminal-fre, One decision about one detection.      `entity` is the raw dict from a run's fin, Append verdicts to a sheet's ground truth and flag it labeled.      Returns the, record_verdicts(), _truth_item(), Verdict, door() (+3 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 114 - "TestAnnotationPenBarriers"
Cohesion: 0.14
Nodes (11): Resolve a scale for every floor-plan region on one page.      `fallback` is a sc, resolve_page_scales(), A suspend_display factory that logs enter/exit, for the tests below., The regression: a live rich Progress torn down on a page that         resolved i, The renumbering hazard, end to end.          A scale stored against what used to, The bottom tier: a scale the user supplied for a sheet that states none., region(), span() (+3 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.06
Nodes (44): createAppRouter(), Clients(), CompanyInfoRoute(), DashboardRoute(), MyBusinessRoute(), UsersRoute(), ContentLayout(), ContentLayoutProps (+36 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 117 - "TestWindowInteriorClutter"
Cohesion: 0.12
Nodes (14): PageTruth, _centre(), exit_code(), Sweep results, their rendering, and the exit-code contract.  Exit codes:   0  cl, render(), SheetResult, evaluate_page(), Score one page's entities against its three verdict lists. (+6 more)

### Community 118 - "qualifying_clip_rects"
Cohesion: 0.04
Nodes (68): CreateCheckoutSessionResponse, CreatePortalSessionRequest, CreatePortalSessionResponse, CreateSetupIntentResponse, InvoiceItem, ValidateCouponRequest, ValidateCouponResponse, buildEstimateStub() (+60 more)

### Community 119 - "qualifying_clip_rects"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 120 - "TestNetworkQueries"
Cohesion: 0.15
Nodes (8): door_candidate(), Fallback-tier door candidates (label boxes, symbol clutter — kept     only for G, The dilated-bbox fallback is the one seal with no evidence of its     own, so it, rooms_for(), TestBboxSealFloor, TestComponentFiltering, TestOpeningSeals, TestPhantomDoorSeals

### Community 121 - "SplitDoubleArcTests"
Cohesion: 0.15
Nodes (15): DeliberateVerdictsTests, EnterWithNothingTickedTests, entity(), _HeadlessReviewSheetTests, Path, tools/review.py's `_pick` / `review_sheet`, driven through the real InquirerPy p, Shared fixture: one fake corpus sheet with a persisted sweep run.      Mirrors t, The C1 regression test.      Against the old `inquirer.fuzzy(multiselect=True)` (+7 more)

### Community 122 - "test_door_assembly.py"
Cohesion: 0.11
Nodes (16): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Run extract command for a single PDF.     Returns (pdf_path, success: bool, outp, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive). (+8 more)

### Community 123 - "batch_extract.py"
Cohesion: 0.15
Nodes (12): detect_wall_network(), _fill_ring_components(), _is_light_pen(), Group ring ids (restricted to `members`) connected by shared seams.      Exporte, Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., hline(), path() (+4 more)

### Community 124 - "2026-08-05 — Gemini region-classification parse failures poison the cache (handoff)"
Cohesion: 0.22
Nodes (8): 2026-08-05 — Gemini region-classification parse failures poison the cache (handoff), Cleanup after the fix lands, Consequence chain (the actual bug), Conventions for this repo, Current implementation facts, Fix A — constrained decoding via `response_schema`, Fix B — never cache a parse-failed classification, The incident (evidence)

### Community 125 - "framed_triple_window"
Cohesion: 0.07
Nodes (36): main(), markRetried(), RETRIED, wasRetried(), downloadFeed(), FeedClientOptions, listFeeds(), parseListCsv() (+28 more)

### Community 126 - "_segments_min_distance"
Cohesion: 0.12
Nodes (17): EndToEndTests, open_v_door(), page(), prim(), End-to-end door scale behavior on FAITHFUL 1:100 fixtures.  A faithful 1:100 exp, Quarter-arc + a double-line leaf, as a faithful export at any scale.      radius, A lone half-open bifold V (folding.py's open_v pattern): two double-line     obl, swing_door() (+9 more)

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
Cohesion: 0.07
Nodes (36): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, BBox, Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox., Max fraction of the bbox long axis covered by one near-collinear centerline., True when the two segments cross at an interior point.      _segments_min_distan (+28 more)

### Community 131 - "test_layout_segmenter.py"
Cohesion: 0.03
Nodes (92): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., _draw_legend(), draw_overlay(), _draw_regions(), Document, MuPDF's own vector redraw of the page, in render.png's coordinate space.      Sa (+84 more)

### Community 132 - "TestProfileHelpers"
Cohesion: 0.12
Nodes (3): LoadTruthTests, Ground-truth files are the durable record of the user's verdicts., TruthWriteTests

### Community 133 - "TestExtractImagesInstances"
Cohesion: 0.05
Nodes (57): RoadAccessRoad, RoadAssessRiskFactor, siteAssessmentAgent, SiteAssessmentInputSchema, SiteAssessmentOutput, SiteAssessmentOutputSchema, buildDeliveryManifest(), DeliveryManifest (+49 more)

### Community 134 - "TestWindowArbitraryAngle"
Cohesion: 0.14
Nodes (7): Every primitive, span AND image must land in the declared frame., A saved 200x400pt PDF with two lines, a word and an image, rotated.      Saved a, Builds all four rotations once; each test reopens what it needs., RotatedPdfTestCase, TestExtractPageFrame, TestPageTransform, write_rotated_pdf()

### Community 135 - "DoorAssemblyTests"
Cohesion: 0.09
Nodes (28): attributes_by_room(), opening_dict(), takeoff.json — the document the web app's overlay and assembly table are both bu, The whole page as one document., One room: geometry, its opening ids, and its quantities.      `quantities` is No, The per-room quantity block mirrored onto Entity.attributes["takeoff"].      Liv, One door or window. `room_ids` is empty when it reached no room;     `dropped_ro, room_dict() (+20 more)

### Community 136 - "client.py"
Cohesion: 0.13
Nodes (18): dump_truth(), dumps_truth(), _inline_number_array(), _inline_point_array(), _item(), _item_payload(), load_truth(), Path (+10 more)

### Community 137 - "_dedupe_openings"
Cohesion: 0.18
Nodes (6): Load-bearing golden for SEGMENT_MAX_DEPTH = 7: at 6 the first-floor     plan and, s15 measured 2026-08-13: 214 text spans bridge every gutter, so the     text-inc, segment(), TestGoldenSegmentation, TestS15PathsOnlyRetry, TestS17PlanElevationSeparation

### Community 138 - "_frame_axes"
Cohesion: 0.12
Nodes (16): Constraints, Design, Detection Review Tooling — Design, Effort, Goals, Non-goals, Open questions, Piece 1 — the sweep persists its output (+8 more)

### Community 139 - "client.py"
Cohesion: 0.09
Nodes (19): Path, The images a human looks at while giving verdicts.  One PNG per page per entity, door_0007 -> d7. Unparseable ids are returned unchanged., Draw one review_<type>.png per entity type present in `unreviewed`.      Returns, short_id(), write_review_overlays(), MainExceptionIsolationTests, tools/review.py's main(): one sheet's unexpected failure must not kill the walk (+11 more)

### Community 140 - "ShaMismatchAgainstTruthTests"
Cohesion: 0.12
Nodes (23): answerWithAssistant(), askAssistant, AskAssistantData, askAssistantHandler(), filterSourcesToCitations(), loadCredential(), makeTitle(), mergeDebugUsage() (+15 more)

### Community 141 - "File Structure"
Cohesion: 0.12
Nodes (15): File Structure, Global Constraints, Phase 3 — corpus labeling (not a task), Regression Corpus Implementation Plan, Slug Assignment (authoritative — used by Tasks 2 and 3), Task 10: Seed s01 ground truth and document the labeling loop, Task 1: Corpus loader, Task 2: Migrate the sheets into the fixtures layout (+7 more)

### Community 142 - "Regression Corpus — Design"
Cohesion: 0.12
Nodes (15): Adoption — `tools/add_sheet.py`, Architecture, Constraints, Fixture layout, Ground truth, Naming, Non-goals, Phasing (+7 more)

### Community 143 - "_check_opening_clear"
Cohesion: 0.04
Nodes (49): CostMaterialItemSchema, EquipmentCategory, EquipmentCategoryEnum, EquipmentItemWithMatch, EquipmentItemWithMatchSchema, SourceAttributionSchema, SupplierAlternativeSchema, LabourItemWithMatch (+41 more)

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
Cohesion: 0.07
Nodes (34): Subscription, CreditsBadge(), CreditsBadgeProps, TrialBanner(), TrialCountdown(), TrialCountdownProps, DOMPurify, MDPreview() (+26 more)

### Community 149 - "TestExtractPageFrame"
Cohesion: 0.04
Nodes (74): ClientReference, BaseEntity, ActiveEstimateStatus, EstimateAIResponse, EstimateStatus, ProjectMarkupConfig, RiskFactor, TimelineAssumptions (+66 more)

### Community 150 - "TestAnnotationPenBarriers"
Cohesion: 0.18
Nodes (10): hline(), path(), Lone thin barriers require a wall pen. On color-coded drawings the     annotatio, Filled arrowhead triangle (a marker ring) pointing down at `tip`., Stairs are furniture to the room stage: a room polygon runs to the     enclosing, rect_room(), stair_arrowhead(), TestAnnotationPenBarriers (+2 more)

### Community 151 - "normalize_bbox"
Cohesion: 0.20
Nodes (9): Global Constraints, Scale-Aware Window Gates Implementation Plan, Task 1: `WindowGates` dataclass, Task 2: Thread `scale_factor` through `detect_windows` → `_find_openings` → `_facing_cap_pairs`, Task 3: The W-row negative control at 50°, Task 4: Paper-invariance battery — one discriminating fixture per P family, all at 50°, Task 5: `CROSS_WINDOW_THICKNESS_TOL_PX` stays unscaled — pin it, Task 6: Findings doc — §4e frozen table, §6 entries (+1 more)

### Community 152 - "review.py"
Cohesion: 0.05
Nodes (43): CANDIDATE_FLOORS, main(), QUERIES, main(), NOTE: the `productType > ''` coverage count is dropped here — it demands, extractDistance(), filterBySimilarity(), RawCandidate (+35 more)

### Community 153 - "fill_ring"
Cohesion: 0.07
Nodes (26): AssistantRoute(), mocks, NavigationItem, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioItem (+18 more)

### Community 154 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Scale-Aware Door Detection Gates Implementation Plan, Self-Review, Task 1: `DoorGates` dataclass, Task 2: Thread gates through `arcs.py` and the `detect_doors` entry point, Task 3: Thread gates through `leaves.py`, Task 4: Thread gates through `sliding.py` (+5 more)

### Community 155 - "TestWindowTightPairInterior"
Cohesion: 0.14
Nodes (13): 1. Intake — extract the brief, 2. Orient — read before touching code, 3. Baseline and locate, 4. Diagnose — measure, don't guess, 5. Fix — test first, then code, then prose, 6. Sweep — target, references, then corpus, 7. CHECKPOINT — report and stop, 8. After the go-ahead (+5 more)

### Community 156 - "TestBlindWindowPocket"
Cohesion: 0.07
Nodes (50): DEFAULT_PROJECT_MARKUP, EstimateTaskPayload, multiAgentEstimateFlowV2, isDev(), isEmulator(), enqueueEstimate, addEstimateEntityIds(), convertImagesToPictureMetadata() (+42 more)

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

### Community 162 - "TestNetworkQueries"
Cohesion: 0.10
Nodes (34): CredentialDocument, getGoogleAccessToken(), exchangeAuthorizationCode(), getGmailProfile(), refreshAccessToken(), revokeGoogleToken(), base64Url(), configuredSecret() (+26 more)

### Community 163 - "_double_arc"
Cohesion: 0.10
Nodes (33): contentCharset(), decodeBase64UrlBuffer(), decodeHeader(), decodeHtmlCodePoint(), decodeHtmlEntities(), decodeTextBytes(), decodeTextPart(), extractParts() (+25 more)

### Community 164 - "test_extraction_transform.py"
Cohesion: 0.03
Nodes (64): devDependencies, autoprefixer, concurrently, cors, eslint, eslint-config-prettier, @eslint/eslintrc, eslint-import-resolver-typescript (+56 more)

### Community 165 - "ScaleInfo"
Cohesion: 0.11
Nodes (22): A drawing scale, and the evidence it came from.      `denominator` 100.0 means 1, ScaleInfo, detection_scale(), PageScales, The scales block written into each page's summary.json entry, and into     takeo, scale_summary_dict(), info(), detection_scale(): PageScales + regions -> one detection factor per page. (+14 more)

### Community 166 - "Architecture"
Cohesion: 0.08
Nodes (23): Architecture, Console output, Constraints, Data model, Evidence, Floor Plan Scale Extraction — Design, Measured coverage, Module layout (+15 more)

### Community 167 - "TestSwingHingePlugRestriction"
Cohesion: 0.15
Nodes (12): bind_scale(), binding_texts(), _caption_distance(), _centroid(), _contains(), The scale governing one region, or None.      `viewports` must arrive smallest-b, How far a text span sits from a region, or None if it is not near it.      Horiz, Every text scale near enough to this region to be about it, nearest first. (+4 more)

### Community 168 - "scales_in_text"
Cohesion: 0.14
Nodes (16): EstimateHeader(), EstimateCard(), EstimateCardProps, ActionsCell(), CellProps, estimateHistoryColumns, EstimateRowActions, EstimateRowActionsContext (+8 more)

### Community 169 - "File Structure"
Cohesion: 0.13
Nodes (14): File Structure, Floor Plan Scale Extraction Implementation Plan, Global Constraints, Self-Review, Task 10: Corpus expectations, Task 1: Units and the `ScaleInfo` model, Task 2: Tier 1 — viewport parsing, Task 3: Tier 2 — text parsing (+6 more)

### Community 170 - "transform_scale"
Cohesion: 0.20
Nodes (9): Baseline comparison — feat/scale-aware-wall-room-gates vs pre-branch (b0e705a), Identity verdict — the four factor-1.0 / 1:50 sheets (s02, s04, s14, s11), s02 (1:50, reference sheet) — LOST confirmed schedule, s04 (1:50) — 2 RETURNED false positives, s06 (1:100, scale-affected) — 1 LOST confirmed room, s06 / s12 verdict, s11 (unresolved → factor 1.0) — 2 new REVIEW doors + 3 RETURNED FPs, s12 (1:100, scale-affected) — 1 LOST confirmed room (+1 more)

### Community 171 - "test_curve_arc_garden_doors.py"
Cohesion: 0.04
Nodes (67): DocumentAgentInput, DocumentAgentInputSchema, DocumentAgentOutput, DocumentAgentOutputSchema, ConditionEnum, ConfidenceEnum, DimensionSourceEnum, DocumentCorrelationSchema (+59 more)

### Community 172 - "DoorV2OpeningCheckTests"
Cohesion: 0.14
Nodes (17): GmailAttachmentContent, GmailBatchResult, GmailMessage, GmailSearchPage, attachmentInputSchema, createGmailToolSession(), detailMessage(), gmailInteractionTools (+9 more)

### Community 173 - "test_layout_golden.py"
Cohesion: 0.04
Nodes (66): stripe, CreateCheckoutSessionRequest, GetPaymentMethodResponse, stripe, SettingsRoute(), SubscriptionTab(), Tab, cancelSubscription() (+58 more)

### Community 174 - "TestNetworkQueries"
Cohesion: 0.03
Nodes (59): scripts, build:dev, build:prod, build:qa, build-storybook, check-types, check-types:app, check-types:e2e (+51 more)

### Community 175 - "TestThickMaterialPairs"
Cohesion: 0.08
Nodes (23): Approach, Cache and offline, Cost, Grounding is enforced in code, not just prompted, Out of scope, Pipeline position, Problem, Request and response (+15 more)

### Community 176 - "TestSlugForPath"
Cohesion: 0.22
Nodes (8): Global Constraints, takeoff.json Overlay Document Implementation Plan, Task 1: Move `scale_summary_dict` into `scale/resolver.py`, Task 2: Openings become page-level records, computed once, Task 3: Rooms carry geometry, and unscaled rooms are kept, Task 4: `takeoff/document.py` — the serialiser, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 177 - "_dedupe_openings"
Cohesion: 0.14
Nodes (24): Exception, Base class. `code` is a Firebase callable error code string., TakeoffFnError, FakeBucket, FakeDb, _make_extract(), A normally measured page: one scale, read off the sheet., A page the resolver could not read a scale for.      Rooms survive with their ge (+16 more)

### Community 178 - "PageTruth"
Cohesion: 0.09
Nodes (18): SheetTruth, _labeled_but_unreviewed(), _prune_unread_page_output(), Delete the page-level files a sweep persists but never uses.      Making sweep o, True when the manifest claims this sheet has been labeled but its     ground tru, Score one sheet's per-page pipeline output against its ground truth.      `pages, score_sheet(), entity() (+10 more)

### Community 179 - "_FillRing"
Cohesion: 0.06
Nodes (56): count(), extractRows(), fetchLeaves(), instrument(), LineRow, main(), MatcherCall, matcherCalls (+48 more)

### Community 180 - "cluster_denominators"
Cohesion: 0.09
Nodes (18): _arc_radius(), assign_openings(), _bbox_edge_along_boundary(), _chord_length(), opening_width_px(), opening_width_px_from_evidence(), _positive(), Polygon (+10 more)

### Community 181 - "Step 5 — Per-scale-group detection for mixed-scale pages"
Cohesion: 0.29
Nodes (6): Acceptance (to refine in the spec), Process (binding), Step 5 — Per-scale-group detection for mixed-scale pages, The design sketch to start from (findings §6, verbatim intent), The problem, Why it is NOT a bolt-on (measured hazard)

### Community 182 - "test_window_detection.py"
Cohesion: 0.09
Nodes (30): detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re, Per-stage wall-clock log line. Detection on 100k+-path sheets runs for     minut, run_heuristics(), _stage(), detect_schedules(), build_plumber_counts(), build_pymupdf_counts() (+22 more)

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
Cohesion: 0.08
Nodes (29): attach_takeoff(), _page_summary_dict(), Mirror the per-room takeoff onto room Entity.attributes["takeoff"]., Heights, parse_height(), _prompt_ceiling(), Wall / opening heights — the one input the plan cannot supply.  0/20 corpus shee, Metres from "2.4", "2.4m", "2400", "2400mm". None to skip. (+21 more)

### Community 188 - "TestPlumberTableBBox"
Cohesion: 0.06
Nodes (60): applyCalculationsToEstimate(), applyTimelinePhaseEdit(), calculateBreakdownFromWorkSections(), calculateCostBreakdownFromWorkSections(), calculateDirectCostCategories(), calculateEquipmentTotal(), calculateItemMarkup(), calculateLaborTotal() (+52 more)

### Community 189 - "TestWindowTightPairInterior"
Cohesion: 0.22
Nodes (6): fill_ring(), Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi, Exporters triangulate fills: a wall band arrives as two right     triangles shar, TestBarrierAllowlist, TestTriangulatedFillRings

### Community 190 - "TestSlugForPath"
Cohesion: 0.07
Nodes (21): parse_measure_viewports(), BBox, Convert a raw /VP bbox into 150-DPI pixel space.      Two steps, in this order., Split a PDF array string into its top-level ``<< >>`` dictionaries.      Depth-c, Every rectilinear measure viewport, as ``(bbox_pt_yup, c)``.      The bbox is le, split_pdf_dicts(), viewport_bbox_to_px(), _FakeDoc (+13 more)

### Community 191 - "label_rooms"
Cohesion: 0.05
Nodes (68): hasRealQuantity(), MatchedPack, MaterialQuantityResolution, resolveMaterialQuantity(), resolveSectionQuantities(), unresolved(), withPackContains(), MaterialItemWithMatch (+60 more)

### Community 192 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Room Labels Implementation Plan, Task 1: Branch and the deterministic span collector, Task 2: Schema, prompt, and the grounded response parser, Task 3: The one-call wrapper, Task 4: The label cache, Task 5: Pipeline wiring, Task 6: Live verification and documentation

### Community 193 - "TestWindowExteriorSide"
Cohesion: 0.06
Nodes (55): ProjectPhase, ProjectTimeline, GanttOverview(), GanttOverviewProps, TimelineCard(), TimelineCardProps, TimelineDetail(), TimelineDetailProps (+47 more)

### Community 194 - "TestCrossWindowToleranceUnscaled"
Cohesion: 0.13
Nodes (14): Floor and ceiling, Geometry, Heights, Module layout, Openings and wall area, Out of scope (recorded), Output, Problem (+6 more)

### Community 196 - "Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`)"
Cohesion: 0.25
Nodes (7): Evidence: what broke at f = 50/92.2 = 0.542 (all measured on the real PDF), Handoff: W-gate recalibration (the proper fix behind `fix/measured-scale-detection-factor`), How the ablation was done (reproduce in ~30 min), Read these first (in order), The problem in one paragraph, The recalibration task (the "proper fix"), Traps

### Community 197 - "test_sliding_doors.py"
Cohesion: 0.11
Nodes (12): _door_plugs(), _open_leaf_edges(), Bbox edges of a garden-layout double door that are room floor, not wall.      A, Bbox short-end edges of a sliding door: across the wall, never wall plane., Thin barrier bands along the wall planes through a detected door.      The door, _sliding_end_edges(), Interrupted-run plugs need jambs that REACH the plug band and a mid     that is, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto. (+4 more)

### Community 198 - "fill_ring"
Cohesion: 0.33
Nodes (5): By entity type, File map — where everything lives, by detection type, History and open work, Output contract you must not break, Regression corpus and tooling

### Community 199 - "_is_light_pen"
Cohesion: 0.26
Nodes (4): Tier 3: a band that only SHORT annotation ink crosses is still a gutter.      Le, Tier 4: a band that only OVERHANGING long ink enters — every long     crosser te, TestOverhangGutter, TestShortInkGutter

### Community 200 - "TestSheetSize"
Cohesion: 0.10
Nodes (15): _contains(), is_verified(), _ratio_pair(), Which drawing scale a room is measured at, and whether it can be trusted.  Pages, Source-level trust, then the drawing's own evidence: a failed     plausibility c, (w_ratio, h_ratio) of page over ISO size, orientation-matched., select_room_scale(), sheet_size_tokens() (+7 more)

### Community 201 - "File structure"
Cohesion: 0.17
Nodes (11): File structure, Global Constraints, Room Quantity Takeoff Implementation Plan, Task 1: Units, Task 2: Heights, Task 3: Per-room scale selection and sheet-size verification, Task 4: Openings — width from evidence, assignment to rooms, Task 5: Quantities — `compute_takeoff` (+3 more)

### Community 203 - "HygieneRuleTests"
Cohesion: 0.19
Nodes (12): Scale-factor behavior of walls/rooms gates: identity at 1.0, shrunk-world at 0.5, Scale coordinates by s, keep stroke widths — a 1:100 export., A closed 400x300 room drawn as four double-line wall bands., room_box_walls(), rooms_for(), shrink(), TestOrchestratorForwardsFactor, TestRoomsScaled (+4 more)

### Community 205 - "parse_answer"
Cohesion: 0.11
Nodes (12): can_prompt(), parse_answer(), prompt_for_scale(), Tier 4 input — ask the user, but only when someone is there to answer.  batch_ex, True only when stdin is a real terminal., The denominator in an answer, accepting "1:100" or "100". None to skip., Ask once for one region's scale. Returns "1:100", or None if skipped.      Asked, FakeStream (+4 more)

### Community 206 - "DoorAssemblyTests"
Cohesion: 0.07
Nodes (39): load_manifest(), manifest_sheets(), Path, Resolution of corpus fixture sheets by slug.  The PDFs are NDA-covered and never, The committed manifest, or an empty corpus when it is absent., Path to a downloaded sheet, or None when it is not on disk., The corpus slug for a PDF path, or None if it is not a corpus sheet.      Compar, Flip a manifest entry's `labeled` flag and write the manifest back.      `labele (+31 more)

### Community 209 - "test_sliding_doors.py"
Cohesion: 0.05
Nodes (50): _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, _split_double_arc(), _trim_chain_extension_caps() (+42 more)

### Community 210 - "TestMinWidthNegativeControl"
Cohesion: 0.16
Nodes (10): _collect_wall_faces(), Return (stroked wall faces, filled-band centerlines)., fill_ring(), marker_ring(), Closed filled rectangle exploded into 4 chained `l` items., Filled triangle/dart exploded into chained `l` items (a leader tip)., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFaceCollection (+2 more)

### Community 211 - "TestComponentFiltering"
Cohesion: 0.05
Nodes (82): EquipmentItem, LaborItem, MaterialItem, PermitItem, WorkItem, WorkSection, MobileShellHeaderContext, MobileShellHeaderContextValue (+74 more)

### Community 213 - "denominator_from_c"
Cohesion: 0.08
Nodes (21): InvalidArgument, PermissionDenied, SourceFile, parse_request(), The supplied scale, or None.      Only a member of SUPPLIABLE_SCALES is accepted, _scale_denominator(), assert_customer_scoped(), download_sources() (+13 more)

### Community 214 - "test_batch_extract.py"
Cohesion: 0.10
Nodes (14): Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, A chimney breast / pier drawn as a closed box on the room side of a     wall ban, A lone stroked, unfilled `qu` item — a joinery-pen box., s04 BATHROOM 01 (room_0000, door_0002): the structural opening is     112px wide, Closed stroked (fill-less) polyline exploded into chained `l` items., s03 corridor room_0014: the jamb nibs beside door_0007/door_0019 are     closed, stroked_box_path(), stroked_ring_path() (+6 more)

### Community 215 - "viewport_bbox_to_px"
Cohesion: 0.08
Nodes (38): canon(), KNOWN_ANSWERS, KnownAnswer, sameProductName(), main(), main(), render(), StoredFact (+30 more)

### Community 216 - "ParkedLeafTests"
Cohesion: 0.08
Nodes (42): PictureUploadProgress, convertToDotNotation(), EstimateEditorAction, estimateEditorReducer(), EstimateEditorState, hasMeaningfulChanges(), initialEstimateEditorState, NOTE: structuredClone ensures deep immutability required by React reducers. (+34 more)

### Community 217 - "_scan_striped_runs"
Cohesion: 0.04
Nodes (76): reviewerAgent, AiReviewerRunner, FinishQualityValidation, PostFanOutReviewContext, UserDirectivesSchema, Room, BenchmarkTotals, BenchmarkTotalsSchema (+68 more)

### Community 218 - "TestSlidingScaleBehavior"
Cohesion: 0.04
Nodes (47): mailersend, db, testVectorSearch(), emulatorTemplatePath(), evaluateTemplateFile(), RemoteConfig, createAuthUser(), createOrResumeAuthUser() (+39 more)

### Community 219 - "TestFoldingScaleBehavior"
Cohesion: 0.07
Nodes (40): AssistantContextInput, AssistantContextMessage, buildAssistantRecoveryInput(), buildAssistantSystemInstruction(), formatHistory(), SYSTEM_PROMPT_PATHS, systemPromptPath(), ACCEPTED_INTERACTION_STATUSES (+32 more)

### Community 220 - "bay_corner_post_window"
Cohesion: 0.18
Nodes (15): allocateSlot(), askSentinel(), findStacks(), publishStripeWebhookSecret(), root, SERVICE_TIMEOUT_MS, StackInfo, DevPorts (+7 more)

### Community 221 - "TestSpanFilterIsLoadBearing"
Cohesion: 0.14
Nodes (14): CheckboxPrimitive, ACCEPTED_FORMATS, CATEGORY_ACCENT, CollapsibleSection, DropZone, UploadStep(), UploadStepProps, FILE_SIZE_LIMITS (+6 more)

### Community 222 - "_fill_ring_components"
Cohesion: 0.15
Nodes (16): CATEGORY_GROUPS, GROUP_ORDER, resolveCategoryGroup(), titleCase(), BillOfMaterialsTemplate(), BomTotals(), BomTotalsProps, MaterialsReport() (+8 more)

### Community 223 - "TakeoffRequest"
Cohesion: 0.08
Nodes (30): CallableRequest, build_response(), error_code(), _measure(), measure_takeoff(), Firebase entry point for the takeoff extraction pipeline.  This module is the on, The handler's real body, with its clients injected so it is testable.      Extra, Measure the drawings on takeoffs/{takeoffId} and return their sheets. (+22 more)

### Community 224 - "dev-local.ts"
Cohesion: 0.08
Nodes (31): answer(), assistantFunctionsOAuthCallbackUrl(), assistantOAuthLoopbackUrl(), cleanup(), cleanupStaleRuntimeFiles(), closeServer(), devServers, errorCode() (+23 more)

### Community 225 - "paths.ts"
Cohesion: 0.19
Nodes (12): { AILogger }, require, { saveCompletedEstimate }, AdminContext, assertSafeTarget(), create(), EMULATOR_HOST_VARS, createEstimate() (+4 more)

### Community 226 - "12. Refresh — 2026-08-30"
Cohesion: 0.04
Nodes (47): 10.1 Nothing has been fixed, 10.2 Fresh prod counts — and the rate §9 asked for, 10.3 Correction to §5 — `materialType` is *not* only a tool-input error, 10.4 §6 reproduced — 3 `$ref`s, and the schema has grown, 10.5 Stale references in §1–§9, 10.6 Do not read the recent quiet as a fix, 10.7 §9 open questions — status, 10. Refresh — 2026-08-20 (+39 more)

### Community 228 - "dependencies"
Cohesion: 0.04
Nodes (46): dependencies, axios, browser-image-compression, class-variance-authority, client-zip, clsx, @dash0/sdk-web, dayjs (+38 more)

### Community 229 - "NotFound"
Cohesion: 0.10
Nodes (20): Constants for the takeoff callable.  Runtime sizing is justified in the design d, FailedPrecondition, NotFound, _doc(), load_record(), mark_awaiting_review(), mark_awaiting_scale(), mark_failed() (+12 more)

### Community 230 - "Multimodal Construction Estimation Implementation"
Cohesion: 0.04
Nodes (44): 1. Advanced Features, 1. Environment Configuration, 1. File Upload Security, 1. Performance Metrics, 1. User Interface Layer, 1. Video Caching, 1. Videos (`.mp4`, `.mov`, `.avi`, `.mkv`), 2. Additional Input Types (+36 more)

### Community 231 - "genkit.config.ts"
Cohesion: 0.14
Nodes (15): ConfigSchema, constructionKnowledgeRetriever, embedder, logger, embedder, logger, MethvinConfigSchema, MethvinDocument (+7 more)

### Community 232 - "MainExceptionIsolationTests"
Cohesion: 0.09
Nodes (35): main(), defaultOrchestratorDeps(), travisPerkinsRetriever, PriceBand, band(), fullDist(), Clause, FakeProduct (+27 more)

### Community 233 - "squat_cap_window"
Cohesion: 0.28
Nodes (6): Scales stated on the sheet, unbound to any drawing.      inspect does not segmen, unbound_scale_lines(), The inspect command's unbound scale listing.  inspect never segments regions, so, TestUnboundScaleLines, text(), viewport()

### Community 234 - "road-access-card.tsx"
Cohesion: 0.08
Nodes (34): RoadAccessLatLon, risk(), dedupe(), deriveCentreline(), NearestRoadsResponse, orderAlongPrincipalAxis(), SAMPLE_OFFSETS_M, sampleGrid() (+26 more)

### Community 235 - "EstimateGenerationService"
Cohesion: 0.10
Nodes (6): EstimateGenerationService, EstimationService, app, FileUploadResult, functions, storage

### Community 236 - "TestWindowSpanOvershootRetune"
Cohesion: 0.20
Nodes (10): BomPreviewLeaf(), decodeOptions(), EstimatePreviewLeaf(), SampleOptions, TimelinePreviewLeaf(), usePdfPreviewData(), BomTemplateOptions, client (+2 more)

### Community 237 - ".collect"
Cohesion: 0.12
Nodes (19): collect_sheets(), has_floor_plan(), is_unclassified(), page_dirs(), Path, Turning a finished run_extract output tree into wire sheets.  Only pages the reg, True when nothing on the page carries a classification.      pipeline.resolve_pa, _read_json() (+11 more)

### Community 238 - "getStripeClient"
Cohesion: 0.08
Nodes (36): CreditPlanType, Credits, CreditTransaction, BillingAddress, FinalizeSubscriptionRequest, FinalizeSubscriptionResponse, PaymentMethodDetails, SubscriptionStatus (+28 more)

### Community 239 - "Subscription & Licensing System"
Cohesion: 0.05
Nodes (41): Access Control, Adding a New License Tier, Backend (Firebase Functions secrets), `changeSubscriptionPlan`, Cloud Functions Reference, `createCheckoutSession`, `createPortalSession`, `createSetupIntent` (+33 more)

### Community 240 - "transcribe-audio.ts"
Cohesion: 0.10
Nodes (16): gemini25FlashLite, getSpeechClient(), recognizeSegment(), SegmentResult, transcribeAudio, TranscribeAudioData, TranscribeAudioResult, TranscribeTimings (+8 more)

### Community 241 - "cost-zod.ts"
Cohesion: 0.08
Nodes (31): CostAgentOutput, CostAgentOutputSchema, CostEquipmentItem, CostEquipmentItemSchema, CostLabourItem, CostLabourItemSchema, CostMaterialItem, CostSection (+23 more)

### Community 242 - "index.tsx"
Cohesion: 0.17
Nodes (15): DefaultEstimateTemplate(), CostSummarySection(), CostSummarySectionProps, PermitsSection(), PermitsSectionProps, WorkSections(), WorkSectionsProps, estimate (+7 more)

### Community 243 - "artifacts.py"
Cohesion: 0.07
Nodes (19): artifact_names(), _content_type(), object_path(), page_prefix(), Path, Uploading a run's outputs to Cloud Storage.  Layout is customers/{customerId}/ta, Upload one page's artefacts. Absent files are skipped, not errors:     page.svg, summary.json and warnings.json live at the run root, and run_extract     writes (+11 more)

### Community 244 - "Schema Optimization for Construction Estimates"
Cohesion: 0.05
Nodes (39): 10. **Integration with Existing System**, 11. **Real-Time Calculation Flow**, 12. **Mobile-Specific Benefits**, 1. **Schema Changes** (`src/lib/prompt-builder.ts`), 1. **Token Reduction**, 1. **Top-Level Totals**, 2. **Calculation Utilities** (`src/lib/estimate-calculations.ts`), 2. **Improved Accuracy** (+31 more)

### Community 245 - "FirebaseAuthProvider"
Cohesion: 0.09
Nodes (17): LoginCredentials, RegisterCredentials, RequestPasswordResetData, RequestPasswordResetResult, validData, validateRegistrationData(), validateRequiredFields(), validateTermsAcceptance() (+9 more)

### Community 246 - "Virtual Scrolling Implementation for Mobile Estimates"
Cohesion: 0.05
Nodes (38): 1. **Advanced Virtualization**, 1. **Height Calculation**, 1. **Virtual Scrolling with React Virtuoso**, 1. **WorkTab Component** (`src/components/estimate-mobile/components/tabs/work-tab.tsx`), 2. **Dynamic Height Handling**, 2. **Mobile Estimate Layout** (`src/components/estimate-mobile/mobile-estimate-layout.tsx`), 2. **Performance Monitoring**, 2. **State Management** (+30 more)

### Community 247 - "Wizard Folder Upload — Follow-ups"
Cohesion: 0.05
Nodes (35): Deferred (do not build), Estimation Wizard — Folder Upload Implementation Plan, Global Constraints, Task 1: Folder traversal module, Task 2: State plumbing — widened signature, scanning flag, dedup, Task 3: Clear handlers and the late-conversion guard, Task 4: Folder-aware drop handler and scanning indicator, Task 5: Files… / Folder… menu on the upload control (+27 more)

### Community 248 - "EstimateResponse"
Cohesion: 0.05
Nodes (37): EstimateResponse, estimate, mocks, PdfPreviewData, UsePdfPreviewDataOptions, ExportReadiness, ClientDetailsCard(), ClientDetailsCardProps (+29 more)

### Community 249 - "schema-validation-error.ts"
Cohesion: 0.11
Nodes (38): mockGenerate, Out, QS_JSON_SCHEMA, Schema, OUTPUT_JSON_SCHEMA, NOTE: `{}` is a plain object, so it passes THIS gate — it is not, buildRepairPrompt(), generateWithSchemaRepair() (+30 more)

### Community 250 - "Mobile Estimate Layout Components"
Cohesion: 0.06
Nodes (35): 1. Touch-First Design, 2. Progressive Disclosure, 3. Clear Visual Hierarchy, 4. Mobile-Optimized Navigation, Accessibility, Adding New Field Types, Browser Support, Components (+27 more)

### Community 251 - "Awin / Travis Perkins Product Feed Pricing Implementation Plan"
Cohesion: 0.06
Nodes (34): Awin / Travis Perkins Product Feed Pricing Implementation Plan, File Map, Post-implementation: prod rollout, Self-review summary (filled in by writing-plans skill), Task 10: CSV parser — specifications extraction, Task 11: CSV parser — row normalizer, Task 12: Category mapper, Task 13: Ingest job — orchestrator (unit test with all collaborators mocked) (+26 more)

### Community 252 - "Awin / Travis Perkins Product Feed Pricing — Design"
Cohesion: 0.06
Nodes (34): Alternative match, Architecture, Awin / Travis Perkins Product Feed Pricing — Design, Backend — Awin/ingestion (`functions/src/awin/`, new directory), Backend integration tests (Firestore emulator), Backend — Lookup layer, Backend — Schema & agent changes, Backend unit tests (Jest, in `functions/src/__tests__/awin/` and existing `functions/src/ai/__tests__/`) (+26 more)

### Community 253 - "estimate-reaper.ts"
Cohesion: 0.09
Nodes (16): execute, groupByCustomer(), main(), projectId, FailedEstimate, firestoreReaperDeps(), HideCandidate, InProgressEstimate (+8 more)

### Community 254 - "Implementation Guide: Enhanced Orchestrator Extraction (Option 1)"
Cohesion: 0.06
Nodes (31): After Implementation, Before Implementation, Context, Deployment Steps, Expected Outcomes, File Checklist, Implementation Guide: Enhanced Orchestrator Extraction (Option 1), Implementation Steps (+23 more)

### Community 255 - "SpoonKnowledgeIngestion"
Cohesion: 0.10
Nodes (18): DoclingDocument, main(), Any, Path, Initialize Vertex AI for embeddings., Initialize Docling converter and chunker., Extract part number from filename.          Args:             filename: e.g., "P, Parse a DOCX file using Docling.          Args:             file_path: Path to D (+10 more)

### Community 256 - "scripts"
Cohesion: 0.06
Nodes (31): scripts, backfill:tp-classifier, backfill:tp-embedding-vector, backfill:tp-normalized-title, backfill:tp-normalized-title:dry, build, build:watch, check-types (+23 more)

### Community 257 - "seed-emulator.ts"
Cohesion: 0.09
Nodes (28): app, auth, bucket, db, ELEANOR_ROAD_ACCESS, ensureSeedEntityIds(), ERITH_GROUND_MOVEMENT, EXTRA_PHASES (+20 more)

### Community 258 - "utils.ts"
Cohesion: 0.11
Nodes (31): env, worker, db, initializeDb(), loadDb(), Model, models, persistDb() (+23 more)

### Community 259 - "isEmulatorMode"
Cohesion: 0.11
Nodes (12): functions, JoinWaitlistInput, JoinWaitlistResponse, PRICING_PLANS, PricingPlan, EmulatorEndpoint, emulatorUrl(), isEmulatorMode() (+4 more)

### Community 260 - "use-sticky-header.ts"
Cohesion: 0.10
Nodes (25): StickyHeaderConfig, useUnifiedStickyHeader(), UseUnifiedStickyHeaderReturn, useDesktopStickyHeader(), UseDesktopStickyHeaderReturn, MobileEstimateActionsMenuProps, StickyHeader(), StickyHeaderProps (+17 more)

### Community 261 - "Travis Perkins Alternative-Match Replace UX — Implementation Plan"
Cohesion: 0.07
Nodes (27): File map, How tests / checks are run, Reading list (skim before starting), Risks and gotchas, Spec reference, Task 10: Final verification, Task 1: Add snapshot fields to the Zod schema + shared types, Task 2: Create `pricing-resolution.ts` with failing tests (+19 more)

### Community 262 - "table.tsx"
Cohesion: 0.06
Nodes (41): SubscriptionEvent, buttonVariants, Pagination(), PaginationContent, PaginationControl(), PaginationControlProps, PaginationEllipsis(), PaginationItem (+33 more)

### Community 263 - "Known-answer acceptance table"
Cohesion: 0.07
Nodes (27): Environment setup (this checkout is not installed), File Structure, Global Constraints, ⛔ HARD DEPENDENCY — PR 2 CANNOT DEPLOY BEFORE PR 1 HAS DEPLOYED **AND** THE NIGHTLY INGEST HAS RUN, Known-answer acceptance table, Open questions for Daniel, Out of scope (explicitly), Part A — stop short-circuiting the AI reviewer (+19 more)

### Community 264 - "material-quantity-step.ts"
Cohesion: 0.17
Nodes (7): createMockFile(), createMockFileReader(), createMockImageWithData(), createMultimodalTestScenarios(), createUser(), mockFileReader(), MultimodalTestScenario

### Community 265 - "assistant-api.ts"
Cohesion: 0.07
Nodes (40): DrawerContent, DrawerContentProps, DrawerDescription, DrawerFooter(), DrawerHeader(), DrawerOverlay, DrawerTitle, drawerVariants (+32 more)

### Community 266 - "xlsx-boq-export.ts"
Cohesion: 0.07
Nodes (43): exportedClientHeader(), loadWorkbook(), makeEquipment(), makeEstimate(), makeLabour(), makeMaterial(), makeSection(), makeWorkItem() (+35 more)

### Community 267 - "⚙️ Project Standards"
Cohesion: 0.07
Nodes (23): Commit and PR conventions, ESLint, Husky, Prettier, ⚙️ Project Standards, TypeScript, What is gated, and where, Backend (`functions/src/`) (+15 more)

### Community 268 - "Travis Perkins RAG Categorisation Fix — Implementation Plan"
Cohesion: 0.07
Nodes (27): Execution Handoff, File structure, How tests are run, Reading list (skim before starting), Self-review, Spec reference, Task 10: Wire production `classifyBatch` + `lookupExistingClassification` into deps, Task 11: Backfill script (+19 more)

### Community 269 - "QS Agent — NRM2 Material Itemisation with TP Grounding — Implementation Plan"
Cohesion: 0.07
Nodes (26): Critical task-ordering update, File Structure, Files to create, Files to modify, Patch table (apply when executing the named task), QS Agent — NRM2 Material Itemisation with TP Grounding — Implementation Plan, Revised execution order, Revision r2 — patches and additions (READ FIRST) (+18 more)

### Community 270 - "provisioning.ts"
Cohesion: 0.14
Nodes (19): setUserClaims(), createFirestoreRecords(), getCustomerStripeId(), getUserData(), updateCustomerStripeId(), updateCustomerSubscription(), ProvisionCustomerData, provisionNewCustomer() (+11 more)

### Community 271 - "Design decisions, recorded"
Cohesion: 0.08
Nodes (25): Design decisions, recorded, File Structure, Global Constraints, Open questions for Daniel, Out of scope (explicitly), ⛔ Preconditions — PR 1 and PR 2 have SHIPPED; this binds to their real API, Task 10: `Coverage: N m2 per board` — a recall loss with the answer sitting in the data, Task 11: Bare-numeric `Pack Coverage`, validated against the row's own geometry (+17 more)

### Community 272 - "xlsx-bom-export.ts"
Cohesion: 0.12
Nodes (22): xlsx, blobToArrayBuffer(), lastDownload(), loadWorkbook(), applyBold(), applyFill(), BomWorkbook, BomWorkbookBody (+14 more)

### Community 273 - "E2E Payment System Testing Plan"
Cohesion: 0.08
Nodes (25): Context, Critical Files to Modify, Current Testing Stack, E2E Payment System Testing Plan, File Structure, Implementation Steps, `payment-3ds-failed.spec.ts`, `payment-3ds-success.spec.ts` (+17 more)

### Community 274 - "export-menu.tsx"
Cohesion: 0.10
Nodes (31): ExportMenu(), ExportMenuProps, baseProps, clientWithBothNames, VatNumberModal(), DEFAULT_EXPORT_OPTIONS, DEFAULT_PDF_EXPORT_OPTIONS, EXPORT_BUTTON_LABELS (+23 more)

### Community 275 - "use-wizard-state.ts"
Cohesion: 0.26
Nodes (12): invalidateEstimateLists(), convertFile, renderWizard(), useWizardState(), categorizeFile(), createFriendlyErrorMessage(), dedupeFiles(), EXTENSION_MAP (+4 more)

### Community 276 - "TestCliEquivalence"
Cohesion: 0.09
Nodes (7): FakeBlob, FakeBucket, FakeDb, FakeDoc, Both pipeline runs happen ONCE for the class.      Each run is a full detection, The CLI arm over the SAME page set the runner passes.          page_indices is d, TestCliEquivalence

### Community 277 - "Travis Perkins Embed Batch Fix — Implementation Plan"
Cohesion: 0.08
Nodes (23): File structure, How tests are run, Reading list (skim before starting), Risks and gotchas, Spec reference, Task 1: Add chunk-boundary unit test (red), Task 2: Bump CHUNK_SIZE to 250 (green), Task 3: Rewrite `embedBatch` to use `ai.embedMany` (+15 more)

### Community 278 - "dependencies"
Cohesion: 0.08
Nodes (25): dependencies, csv-parse, ffmpeg-static, firebase-admin, firebase-functions, genkit, @genkit-ai/firebase, @genkit-ai/google-genai (+17 more)

### Community 279 - "deletion.ts"
Cohesion: 0.12
Nodes (21): hasAssistantAccess(), requireAssistantAccess(), AssistantDeletionResult, assistantUserRef(), conversationRef(), deleteAllAssistantConversationsData(), deleteAssistantConversationData(), deleteAssistantUserData() (+13 more)

### Community 280 - "attachment-download.ts"
Cohesion: 0.12
Nodes (21): assertCustomerScopedPath(), buildContentDisposition(), CreateAttachmentDownloadUrlData, createAttachmentDownloadUrlHandler(), CreateAttachmentDownloadUrlResult, encodeRFC5987ValueChars(), ESTIMATE_ATTACHMENT_PREFIXES, flattenFileReferences() (+13 more)

### Community 281 - "xlsx-timeline-export.ts"
Cohesion: 0.16
Nodes (22): estimate, downloadWorkbookBuffer(), ExcelJSModule, loadExcelJSModule(), buildScaleColumns(), buildTimelineSheet(), buildTimelineWorkbookData(), chartColumnWidth() (+14 more)

### Community 282 - "Labour Rate Groups Implementation Plan"
Cohesion: 0.08
Nodes (23): File Map, Labour Rate Groups Implementation Plan, Task 10: Frontend API — create / update / delete group hooks, Task 11: Frontend component — CoreRoleCard, Task 12: Frontend component — CustomRoleRow, Task 13: Frontend component — GroupPanel, Task 14: Frontend components — GroupSidebar + GroupPillPicker, Task 15: Frontend component — NewGroupModal (+15 more)

### Community 283 - "Dashboard Pagination — Design"
Cohesion: 0.08
Nodes (23): Architecture, Backfill script, Constraint that shapes the design, Count, Dashboard Pagination — Design, Data flow, Data layer, Deferred work (+15 more)

### Community 284 - "site-assessment-step.test.ts"
Cohesion: 0.22
Nodes (5): _hface(), A bare horizontal wall-face _Seg for isolated merge-tolerance tests., Isolates _merge_collinear_segs's offset-tolerance scaling directly —     the exa, TestMergeCollinearOffsetScaling, TestWallGatesConstruction

### Community 285 - "set"
Cohesion: 0.42
Nodes (8): activeClientIds, getResponse(), handleRequest(), IS_MOCKED_RESPONSE, resolveMainClient(), respondWithMock(), sendToClient(), serializeRequest()

### Community 286 - "Authentication Functions"
Cohesion: 0.08
Nodes (23): 1. `validation.ts`, 2. `error-handler.ts`, 3. `auth-operations.ts`, 4. `firestore-operations.ts`, 5. `stripe-operations.ts`, 6. `password-reset.ts`, Authentication Functions, Core Functions (`index.ts`) (+15 more)

### Community 287 - "1. Prompt Rewrite (`functions/src/ai/agents/scope-agent.ts`)"
Cohesion: 0.08
Nodes (23): 1. Prompt Rewrite (`functions/src/ai/agents/scope-agent.ts`), 2. SpecMatchKey Enum Expansion (`functions/src/ai/schemas/scope-zod.ts`), 3. RAG Integration for Scope Agent, 4. Few-Shot Examples in Prompt, 5. Temperature & Model Config, 6. AI Technology Recommendations (Priority Order), A. Role & Identity, AI Agent Key Findings (+15 more)

### Community 288 - "e2e-run.ts"
Cohesion: 0.32
Nodes (13): discoverStack(), delay(), describe(), exited(), hasExited(), interrupt(), signalGroup(), startStack() (+5 more)

### Community 289 - "extract_tables_from_html"
Cohesion: 0.14
Nodes (21): BeautifulSoup, _extract_page_title(), extract_tables_from_html(), _get_header_texts(), _get_table_text(), _parse_breadcrumb(), Path, Tag (+13 more)

### Community 290 - "waitlist.ts"
Cohesion: 0.15
Nodes (16): RFC-5321, ApiResponse, createErrorResponse(), createSuccessResponse(), collection, doc, asTrimmedString(), parseWaitlistInput() (+8 more)

### Community 291 - "Takeoff as a Firebase Function — design"
Cohesion: 0.09
Nodes (22): Accepted limitation: unresolved scale, Context: what rivet-mind already has, Contract, Decisions, Dependencies, Execution flow, Failure handling, Firestore writes (+14 more)

### Community 292 - "Estimate Versioning System"
Cohesion: 0.09
Nodes (22): 1. Top-Level Primitives (string, number, boolean), 2. Nested Object Fields, 3. Array Item Fields, 4. Array Add Operations, 5. Array Delete Operations, Adding a New Editable Field, applyChangesToEstimate(estimate, changes) → EstimateResponse, Architecture Overview (+14 more)

### Community 293 - "Labour Rate Groups — Design Spec"
Cohesion: 0.09
Nodes (22): Backend Changes, Component structure, `CORE_ROLES` constant (shared-lib), Data Model, Document schema, Estimate payload, Firestore path, Firestore rules (+14 more)

### Community 294 - "ClientNameDisplay"
Cohesion: 0.16
Nodes (15): ClientLike, ClientNameDisplay, ClientNameFields, buildClientReference(), onClientUpdated, clientReferenceChanged(), firestorePropagateDeps(), PropagateClientDeps (+7 more)

### Community 295 - "materials-orchestrator.test.ts"
Cohesion: 0.09
Nodes (16): MaterialsMatchSection, captureSection, countCalc, makeSection(), makeSectionWithMaterials(), mockGetFirestore, noPackFactsProduct, pricingBands (+8 more)

### Community 296 - "compilerOptions"
Cohesion: 0.09
Nodes (22): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+14 more)

### Community 297 - "HygieneRuleTests"
Cohesion: 0.11
Nodes (8): CommittedGroundTruthTests, HygieneRuleTests, ManifestHygieneTests, Committed ground truth must not carry property-identifying text.  Ground truth r, fixtures/MANIFEST.json is also tracked, and its `file` values are built     verb, The rules catch what they claim to catch., Every committed ground-truth file obeys the rules., _strings()

### Community 298 - "select.tsx"
Cohesion: 0.04
Nodes (67): args, confirm(), envFlag, isEmulator, LABEL_TO_SLUG, LegacyLabourRate, main(), migrateCustomer() (+59 more)

### Community 299 - "pagination.tsx"
Cohesion: 0.23
Nodes (9): EstimateActionsContext, EstimateActionsContextValue, EstimateActionsProvider(), EstimateActionsState, useEstimateActions(), createTestQueryClient(), HistoryActionProbe(), mockEstimate (+1 more)

### Community 300 - "Material-Quantity Calculation Resilience — Design"
Cohesion: 0.10
Nodes (19): 1. `validateMaterialQuantityInput(input)` — new pure function (`calculation-tools.ts`), 2. `calculateMaterialQuantitiesBatch` — handler rewrite (`batch-calculation-tools.ts`), 3. `calculateMaterialQuantitySingle` — keep throwing, route through validator (`calculation-tools.ts`), 4. Deterministic reviewer (`deterministic-reviewer.ts`), 5. Materials sub-agent prompt (`materials-sub-agent.ts`, Step 4), 6. Tests (`functions/src/ai/__tests__/qs-quantity-tools.test.ts`), Architecture, Components (+11 more)

### Community 301 - "Design: QS owns the material list; sub-agent becomes a pure Travis Perkins matcher"
Cohesion: 0.10
Nodes (19): 1. QS material authoring, 2. Mode-keyed default coverage table (new, code), 3. Material matcher (the slimmed sub-agent), 4. Deterministic calc step (calc-after-match), 5. Guards / deterministic reviewer, 6. Cost engineer, Current architecture (before), Data-contract / schema changes (+11 more)

### Community 302 - "Project Timeline Export — Design"
Cohesion: 0.10
Nodes (19): Architecture, Backend, Data, Edge Cases, Estimate template, Files, Follows the BOM pattern exactly, Frontend export wiring (+11 more)

### Community 303 - "Design"
Cohesion: 0.10
Nodes (19): 1. Where it runs, 2. Geocode once, before the agent, 3. The delivery manifest, 4. The agent, 5. The tool, 6. The vehicle catalogue, 7. Merging into the estimate, 8. Failure is silent to the user and loud to Dash0 (+11 more)

### Community 304 - "5. Verification runs"
Cohesion: 0.10
Nodes (19): 1. Problem statement, 2. Agreed redesign direction, 3. Ordered plan (status), 4. Audit results (2026-07-21, read-only, rivet-mind-dev + live Awin feed), 5. Verification runs, 6. Decision log, Classifier error (validates retiring the enum), Cutover verification — 2026-07-22 (Step 5) (+11 more)

### Community 305 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compileOnSave, compilerOptions, allowImportingTsExtensions, baseUrl, esModuleInterop, isolatedModules, module, moduleResolution (+11 more)

### Community 306 - "QS Material-Quantity Chain Fix Implementation Plan"
Cohesion: 0.11
Nodes (18): Background — what's wrong today, Execution Handoff, File Structure, Hard Constraint — No LLM Arithmetic, Minimum conversion modes, Per-mode result contract, QS Material-Quantity Chain Fix Implementation Plan, Required tools (+10 more)

### Community 307 - "File Structure"
Cohesion: 0.11
Nodes (18): Dashboard Pagination Implementation Plan, Deploy order, File Structure, Global Constraints, Manual verification, Task 10: Extract the status indicator and mobile card, Task 11: The active estimates section, Task 12: Rewire the history component (+10 more)

### Community 308 - "devDependencies"
Cohesion: 0.11
Nodes (19): devDependencies, eslint, eslint-config-google, eslint-config-prettier, eslint-plugin-import, eslint-plugin-prettier, firebase-functions-test, jest (+11 more)

### Community 309 - "directives-zod.ts"
Cohesion: 0.18
Nodes (11): directivesAgent, Constraint, ConstraintKind, ConstraintKindEnum, ConstraintSchema, EMPTY_DIRECTIVES, Exclusion, ExclusionSchema (+3 more)

### Community 310 - "upload-step.tsx"
Cohesion: 0.29
Nodes (5): acquire, collectEntry(), fileFromEntry(), filesFromDataTransfer(), readAllEntries()

### Community 311 - "project-details-step.tsx"
Cohesion: 0.24
Nodes (6): ResultStepProps, EstimateWizard(), EstimateWizardProps, StepMeta, FileUploadResult, InputType

### Community 312 - "api.ts"
Cohesion: 0.04
Nodes (68): createComment(), CreateCommentInput, createCommentInputSchema, useCreateComment(), UseCreateCommentOptions, deleteComment(), useDeleteComment(), UseDeleteCommentOptions (+60 more)

### Community 314 - "Decisions taken during planning (all measured — read before Task 1)"
Cohesion: 0.11
Nodes (17): Decision 1 (mandatory, no discretion): rung `Pack Quantity` fires only when `N > 1`, Decision 2 (FLAGGED — differs from the brief): area outranks the item count, Decision 3 (FLAGGED — scope reduction): the `W x H` geometry rung is deferred to PR 3, Decision 4: parse the RAW `specifications` column, not `attributeSummary`, Decision 5: `source` lives inside the fact, Decisions taken during planning (all measured — read before Task 1), File Structure, Global Constraints (+9 more)

### Community 315 - "api-client.ts"
Cohesion: 0.31
Nodes (10): build_parser(), cmd_extract(), cmd_inspect(), main(), parse_page_spec(), positive_metres(), argparse type: a positive, finite height in metres., Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]. (+2 more)

### Community 316 - "File Structure"
Cohesion: 0.12
Nodes (16): Client Directives Implementation Plan, Enforcement: prompts only, by decision, File Structure, Global Constraints, Self-Review, Task 10: Show exclusions on the exports, Task 11: Full-stack verification, Task 1: Directives and exclusions schema (+8 more)

### Community 317 - "Preliminaries as a Separate Cost Summary Line"
Cohesion: 0.12
Nodes (16): 1. `isPreliminariesSection` — shared-lib helper, 2. `calculateDirectCostCategories` — shared-lib calculation, 3. `CostBreakdown.prelims` — the marked-up side, 4. Display surfaces, 5. Item markup on the dashboard, Architecture, Build note, Data flow (+8 more)

### Community 318 - "TP Pack-Size Pricing — Findings, Progress & Next Steps"
Cohesion: 0.12
Nodes (16): 1. Root cause, 2. Chunk 1 — SHIPPED (PR #101), 2b. PR 1 shipped, 2c. PR 2 shipped, 3. Dev-run evidence (2026-07-29) — what shipped code actually does, 4. Superseded decisions — DO NOT follow the old ones, 5. The design (agreed with Daniel, 2026-07-29), 5b.1 Secondary, safe-direction finding (PR 3 input) (+8 more)

### Community 319 - "target.ts"
Cohesion: 0.20
Nodes (17): globalSetup(), reportStripeWebhookStatus(), createStripeCustomer(), createStripeSubscription(), readSecretLocal(), recurringPriceId(), resolveSecretKey(), stripeClient() (+9 more)

### Community 320 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowSyntheticDefaultImports, baseUrl, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, lib, module (+8 more)

### Community 321 - "process-v2.test.ts"
Cohesion: 0.12
Nodes (12): mockDeleteVideos, mockFlow, mockHandleFailure, mockIsCompleted, mockIsSuperseded, mockMarkCompleted, mockMarkFailed, mockSaveCompleted (+4 more)

### Community 322 - "estimate-history-layout.tsx"
Cohesion: 0.10
Nodes (30): EstimateRoute(), hasInvalidEstimateHistorySyntax(), positiveInteger(), useEstimateQuery(), useEstimateVersionsQuery(), EstimateHistoryLayout(), EstimateHistoryLayoutProps, changeLabel() (+22 more)

### Community 323 - "create-comment.ts"
Cohesion: 0.24
Nodes (7): TabsContent, TabsList, TabsTrigger, EstimateTabKey, EstimateTabs(), EstimateTabsProps, TabActionTrigger()

### Community 324 - "dictation-textarea.tsx"
Cohesion: 0.18
Nodes (15): blobToBase64(), transcribeAudio(), TranscribeAudioData, TranscribeAudioResult, TranscribeResult, translateText(), TranslateTextData, TranslateTextResult (+7 more)

### Community 325 - "Firestore Security Rules Tests"
Cohesion: 0.12
Nodes (16): Authentication Requirements (2 tests), Customer Isolation (8 tests), Edge Cases (3 tests), Execute Tests, Firestore Security Rules Tests, Key Security Features Tested, Mock Data, Mock Users (+8 more)

### Community 326 - "QS-Owns-Materials / TP-Matcher Implementation Plan"
Cohesion: 0.12
Nodes (15): File Structure, Global Constraints, Notes for the implementer, QS-Owns-Materials / TP-Matcher Implementation Plan, Task 10: Guard placement + end-to-end integration test, Task 11: Cleanup + dead-code sweep, Task 1: Add calc-input fields to the material schema, Task 2: Mode-keyed default coverage table (+7 more)

### Community 327 - "Slim the Materials Sub-Agent input to a minimal matcher projection"
Cohesion: 0.12
Nodes (15): 1. New input schema — `functions/src/ai/schemas/qs-agent-zod.ts`, 2. Orchestrator — `functions/src/ai/flows/materials-orchestrator.ts`, 3. Prompt — `functions/src/ai/agents/materials-sub-agent.ts`, 4. Ripple / cleanup, Acceptance criteria, Approach considered and chosen, Design decisions (confirmed), Field-usage audit (why the fields are droppable) (+7 more)

### Community 328 - "Bill of Materials Export — Design"
Cohesion: 0.12
Nodes (15): Architecture, Bill of Materials Export — Design, Category gap analysis (the "missing categories" check), Data transform (new; frontend-only, no shared-lib change), Edge Cases, Files, Key Decisions, Non-Goals / Future (+7 more)

### Community 329 - "tenant.ts"
Cohesion: 0.17
Nodes (18): E2eFixtures, RegisterIdentity, poolEmail(), qaInbox(), registerEmail(), slotKey(), findUser(), purgeAccount() (+10 more)

### Community 331 - "use-project-markup-editor.ts"
Cohesion: 0.29
Nodes (5): band_segments(), hatch(), A band hatched THROUGH — every diagonal stroke ending on both faces — is a drawn, 45° strokes across the band; inset > 0 stops them short of each face., ThroughHatchBandTests

### Community 332 - "use-estimate-history.ts"
Cohesion: 0.17
Nodes (10): ACTIVE_ESTIMATE_STATUSES, mockGetCollectionCount, mockGetCollectionPage, activeStatusFilter(), baseConstraints(), historyStatusFilter(), PageCursor, RawDoc (+2 more)

### Community 333 - "estimate-history.tsx"
Cohesion: 0.26
Nodes (8): isActiveEstimateStatus(), EstimateHistory(), EstimateHistoryProps, hookResult(), mockHook, mockRealtime, row(), useProcessingRealtime()

### Community 334 - "estimate-pdf-service.ts"
Cohesion: 0.20
Nodes (9): Handoff: hatch-cell chords in the wall network (follow-up to `fix/s03-bedroom-corner-notch`), Prompt for the next agent, R1. Hatch-cell chords are still wall FACES (the proper fix), R2. The single-endpoint offset test in the collinear merge, R3. The corpus baseline is RED on 11 sheets (the user's queue, not yours), Read these first (in order), Residue — the iteration this handoff is for, Tooling that exists now (+1 more)

### Community 335 - "EstimateTransactionService"
Cohesion: 0.44
Nodes (6): callOptions, EnqueueEstimateResult, EstimationProgress, EstimationRequest, EstimationResult, FileUploadResult

### Community 336 - "Preview Route Template Split Implementation Plan"
Cohesion: 0.13
Nodes (14): File Structure, Follow-up (out of scope for this plan), Global Constraints, Preview Route Template Split Implementation Plan, Self-Review, Task 1: BOM template owns its options type, Task 2: Generic `decodeOptions` helper, Task 3: Shared `usePdfPreviewData` hook (+6 more)

### Community 337 - "Design"
Cohesion: 0.13
Nodes (14): 1. Carrier, 2. Extraction, 3. Plumbing, 4. Prompt contract, 5. Output surface, 6. Deterministic enforcement, Design, Estimated effort (+6 more)

### Community 338 - "uploader.py"
Cohesion: 0.18
Nodes (14): _build_firestore_doc(), clear_collection(), generate_embeddings(), init_firebase(), Any, Phase 4: Vertex AI embedding generation + Firestore batch upload., Build the Firestore document dict from a TableRecord + embedding., Upload records with embeddings to Firestore in batches.      Returns the number (+6 more)

### Community 339 - "File Structure"
Cohesion: 0.14
Nodes (13): File Structure, Global Constraints, Self-Review, Takeoff Firebase Function Implementation Plan, Task 1: Scaffold, errors, and request parsing, Task 2: Firestore record access and status transitions, Task 3: Source file download and the tenant path boundary, Task 4: Sheet collection from a finished output tree (+5 more)

### Community 340 - "File Structure"
Cohesion: 0.14
Nodes (13): Deployment & backlog runbook (operator, NOT part of code tasks), File Structure, Global Constraints, Self-Review, Stuck-Estimate Reaper Implementation Plan, Task 1: Shared types — `failedAt` and `hidden`, Task 2: Stamp `failedAt` when marking an estimate failed, Task 3: Reaper core — pure reconcile logic (+5 more)

### Community 341 - "QS `sourceRoomId` Validation + Repair-Wrapper Top-Key Fix — Implementation Plan"
Cohesion: 0.14
Nodes (13): Design decision — material `sourceRoomId` is best-effort bookkeeping, File Structure, Global Constraints, Issue & Diagnosis (for review), QS `sourceRoomId` Validation + Repair-Wrapper Top-Key Fix — Implementation Plan, Reported symptom, Root cause — two independent layers, Scope boundary (accepted limitation) (+5 more)

### Community 342 - "Task Order Rationale"
Cohesion: 0.14
Nodes (13): Both full suites are red on `main` — do not gate on them, Global Constraints, Out of Scope, Project Timeline Export Implementation Plan, Task 1: Project Timeline template, Task 2: Accept the `timeline` report kind in the PDF function, Task 3: Project Timeline preview leaf + route, Task 4: Wire `timeline` through the export path (+5 more)

### Community 343 - "Site Access Assessment Implementation Plan"
Cohesion: 0.14
Nodes (13): After the plan: what a human must do, Deviations from the spec, File Structure, Global Constraints, Site Access Assessment Implementation Plan, Task 1: The vehicle catalogue, Task 2: Split the measurement into a network half and a pure half, Task 3: Report whether the address is a flat (+5 more)

### Community 344 - "Design"
Cohesion: 0.14
Nodes (14): Backfill, Classifier module, Cost-engineer prompt simplification, Daily schedule, Design, Distance-read fix, Downstream guards (Bugs 5 & 6), Firestore indexes (+6 more)

### Community 345 - "TP ingest: quota-aware retries and a readable dev run"
Cohesion: 0.14
Nodes (13): A1. Back off instead of hammering, A2. A new `isQuotaError` helper, A3. Don't split on a quota error, A4. Surface it in the summary, B1. Instrument at the dependency boundary, B2. Intercept the log cascade, B3. The log file, Out of scope (+5 more)

### Community 346 - "use-estimate-mutation.ts"
Cohesion: 0.25
Nodes (7): create, { create: actualCreate, createStore: actualCreateStore }, createStore, createStoreUncurried(), createUncurried(), storeResetFns, zustand

### Community 348 - "Authentication Provider System"
Cohesion: 0.15
Nodes (12): 1. API Auth Provider (`api`), 2. Firebase Auth Provider (`firebase`), Authentication Provider System, Available Providers, Configuration, Creating a New Auth Provider, Environment Variables, Firebase Setup (+4 more)

### Community 349 - "Tasks"
Cohesion: 0.15
Nodes (12): File Structure, Notes, Remove London Weighting & Strengthen NRM2 Guidance Implementation Plan, Success Criteria, Task 1: Remove London Weighting Reference from Cost-Engineer (Line 131), Task 2: Remove London Weighting Section from Cost-Engineer (Lines 194–197), Task 3: Remove London Weighting Reference from Pricing Instructions (Line 347), Task 4: Remove London Weighting Example Note from Cost-Engineer (Line 359) (+4 more)

### Community 350 - "Schema-Repair Wrapper (Partial P0) Implementation Plan"
Cohesion: 0.15
Nodes (12): File Structure, Global Constraints, Out-of-scope follow-ups (tracked, not silently dropped), Relationship to the sibling plan (read first), Schema-Repair Wrapper (Partial P0) Implementation Plan, Scope, Self-Review, Task 1: Pure error-parsing helpers (+4 more)

### Community 351 - "File Structure"
Cohesion: 0.15
Nodes (12): Design decisions baked into this plan (do not re-litigate during execution), File Structure, Global Constraints, Out of scope (explicitly), Task 1: v2 unkeyed candidate-search tool, Task 2: Calibrate the v2 similarity floor, Task 3: v2 matcher prompt (the picker) + flag + selector, Task 4: Leaf-band generic resolution (v2) (+4 more)

### Community 352 - "File Structure"
Cohesion: 0.15
Nodes (12): File Structure, Global Constraints, Out of scope (explicitly), Task 1: `parsePackSize` utility, Task 2: Honest `similarity` — optional, no `?? 1` sentinel, Task 3: `packSize` on every product pick, Task 4: Quantity step — physical size only, never `packQuantity`, Task 5: Orchestrator — price and quantity from the SAME pack size (+4 more)

### Community 353 - "Remove London Weighting & Strengthen NRM2 Guidance"
Cohesion: 0.15
Nodes (12): 1. Cost-Engineer Agent (`functions/src/ai/agents/cost-engineer.ts`), 2. Quantity Surveyor Agent (`functions/src/ai/agents/quantity-surveyor-agent.ts`), 3. Reviewer Agent (`functions/src/ai/agents/reviewer-agent.ts`), Design, Files to modify:, Goals, Implementation, Notes (+4 more)

### Community 354 - "Pipeline Checkpointing — Design"
Cohesion: 0.15
Nodes (12): Checkpointer, Data model, Decisions (made during brainstorming), Error handling, Goals, Out of scope, Pipeline Checkpointing — Design, Problem (+4 more)

### Community 355 - "core-role-card.tsx"
Cohesion: 0.43
Nodes (3): Stick-font text drawn as line strokes (s06/s11/s16/s20: no text     spans, every, HITL' in 14px stick glyphs, cap line y, baseline y + 14., TestVectorTextExclusion

### Community 357 - "package.json"
Cohesion: 0.15
Nodes (12): lint-staged, *.+(ts|tsx), msw, workerDirectory, name, packageManager, private, type (+4 more)

### Community 358 - "to-estimate-list-row.ts"
Cohesion: 0.36
Nodes (4): ActiveEstimates(), ActiveEstimatesProps, EstimateStatusIndicator(), EstimateListRow

### Community 359 - "auth.tsx"
Cohesion: 0.48
Nodes (6): _geom(), _iou(), _latest(), _load(), main(), Entity-level before|after delta between a compare_sweeps snapshot (outputs/regre

### Community 360 - "xlsx-boq-export.test.ts"
Cohesion: 0.33
Nodes (5): currentClient, defaultProps, estimateWithCurrentClient, mutationMocks, otherClient

### Community 361 - "Deploying the takeoff callable"
Cohesion: 0.17
Nodes (11): Deploy, Deploying the takeoff callable, Dry-run result — `rivet-mind-dev`, 2026-08-31, Known limitations, Local verification performed (this repo, no network, no deploy), One-time GCP setup, per project, Prerequisite — create the discovery venv first, REQUIRED MANUAL GATE — read before any deploy command (+3 more)

### Community 362 - "File Structure"
Cohesion: 0.17
Nodes (11): File Structure, Global Constraints, Material-Quantity Calculation Resilience Implementation Plan, Self-Review, Task 1: `classifyParentUnit` helper, Task 2: Validator, unresolved-result builder, and marker widening, Task 3: Route `calculateMaterialQuantitySingle` through the validator, Task 4: Isolating batch tool — permissive schema + flat `ok`/`error` union (+3 more)

### Community 363 - "Estimate Schema-Validation Resilience Implementation Plan"
Cohesion: 0.17
Nodes (11): Error → Task Mapping, Estimate Schema-Validation Resilience Implementation Plan, Follow-up (deferred to its own plan): `(root): must be object / null`, Global Constraints, Self-Review, Task 1: Work-quantity batch — loosen inputs + per-item isolation, Task 2: Material-quantity batch — loosen input `mode` + shared normalizer, Task 3: TP lookup — remove the hidden 50-item cap, chunk internally (+3 more)

### Community 364 - "File Structure"
Cohesion: 0.17
Nodes (11): File Structure, Global Constraints, Out of scope (explicitly), Task 1: Extract pure band math to `travis-perkins-band-math.ts`, Task 2: Extract `rerankCandidates` to `travis-perkins-rerank.ts`, Task 3: Cut the orchestrator, flows, and matcher over to v2-only, Task 4: Delete the v1 tool files, Task 5: Remove keyed retrieval from the retriever and exact lookup (+3 more)

### Community 365 - "Materials Sub-Agent Multi-Section Batching — Design"
Cohesion: 0.17
Nodes (11): 10. Out of scope, 1. Context & motivation, 2. Contract change — schemas evolve in place, 3. Dispatcher batching, 4. Stitching & per-batch validation, 5. Failure handling — split-retry, 6. Prompt & model changes (`materials-sub-agent-v2.ts`), 7. Harness & verification (+3 more)

### Community 366 - "Bill of Materials — remove VAT from totals"
Cohesion: 0.17
Nodes (11): 1. Data — `transform.ts`, 2. PDF — `sections/bom-totals.tsx`, 3. Excel — `xlsx-bom-export.ts`, 4. Tests, Bill of Materials — remove VAT from totals, Design, Problem, Risks (+3 more)

### Community 367 - "generate-estimate-pdf.ts"
Cohesion: 0.23
Nodes (7): generateEstimatePdf, GenerateEstimatePdfData, GenerateEstimatePdfResult, REPORT_FILENAME_PREFIXES, buildPreviewUrl(), REPORT_PATH_SEGMENTS, ReportKind

### Community 368 - "TableRecord"
Cohesion: 0.26
Nodes (11): _build_enriched_text(), enrich_tables(), _format_table_for_prompt(), _parse_llm_response(), Phase 3: Gemini LLM enrichment for natural-language descriptions, aliases, and k, Enrich all TableRecords with LLM-generated descriptions, aliases, keywords., Format a single TableRecord as context for the LLM prompt., Parse LLM JSON response, returning None on failure. (+3 more)

### Community 369 - "serializer.py"
Cohesion: 0.20
Nodes (10): _count_body_rows(), Path, Tag, Phase 2: Docling parse + markdown table serialization with BS4 fallback., Convert a raw <table> HTML string to a markdown pipe table.      This is the BS4, Count the number of <tr> elements in the table body., Add markdown_table to each TableRecord using Docling (with BS4 fallback).      I, serialize_tables_with_docling() (+2 more)

### Community 370 - "page"
Cohesion: 0.36
Nodes (3): cut(), page(), TestXYCut

### Community 371 - "_widest_gap"
Cohesion: 0.19
Nodes (7): _clip_cut(), Strip empty margins; returns absolute (start, end) bin indices., Widest fully-empty internal run of at least min_bins. Leading and     trailing r, First clip edge lying strictly inside the span with ink on both sides.      An e, _trim(), _widest_gap(), TestProfileHelpers

### Community 372 - "Travis Perkins RAG — Investigation & Fix Plan"
Cohesion: 0.18
Nodes (8): Acceptance Criteria, Approach summary, Bugs Identified (Consolidated), Decided Approach, Executive Summary, Out of Scope (Flagged for Follow-up), Travis Perkins RAG — Investigation & Fix Plan, Two design constraints distinguished

### Community 373 - "Global Constraints"
Cohesion: 0.18
Nodes (10): Bill of Materials Export Implementation Plan, Global Constraints, Task 1: Extract shared template table + formatters, add quantity formatter, Task 2: Category consolidation map, Task 3: Materials aggregation transform, Task 4: Bill of Materials template components, Task 5: Wire the 'bom' export format (type, service, routing), Task 6: Render the BOM in the preview route + Cloud Function `report` param (+2 more)

### Community 374 - "File Structure"
Cohesion: 0.18
Nodes (10): File Structure, Global Constraints, Materials Sub-Agent Multi-Section Batching Implementation Plan, Out of scope (explicitly), Task 1: Commit the model swap + fix the `gemnini3flash` typo everywhere, Task 2: Pure batching module — packing + batch-output validation, Task 3: Multi-section schemas + batched dispatch with split-retry, Task 4: Multi-section prompt + tool description (+2 more)

### Community 375 - "backfill-tp-embedding-vector.ts"
Cohesion: 0.29
Nodes (10): ALLOW_INVALID, commitChunk(), Counts, DRY_RUN, isTransactionTooBig(), isValidNumberArray(), log(), main() (+2 more)

### Community 376 - "invoice-history.tsx"
Cohesion: 0.25
Nodes (7): GetInvoicesRequest, GetInvoicesResponse, getInvoices(), useGetInvoices(), formatAmount(), formatDate(), InvoiceHistory()

### Community 377 - "notification.stories.tsx"
Cohesion: 0.20
Nodes (9): icons, Notification(), NotificationProps, Error, Info, meta, Story, Success (+1 more)

### Community 378 - "db.ts"
Cohesion: 0.33
Nodes (4): listeners, SnapshotHandler, subscribeCallCounts, unsubscribes

### Community 379 - "Changelog"
Cohesion: 0.20
Nodes (9): [1.27.0](https://github.com/nestimate-ai/nestimate/compare/v1.26.0...v1.27.0) (2026-07-22), [1.28.1](https://github.com/nestimate-ai/nestimate/compare/v1.28.0...v1.28.1) (2026-07-23), [1.33.0](https://github.com/nestimate-ai/nestimate/compare/v1.32.0...v1.33.0) (2026-07-29), [1.33.2](https://github.com/nestimate-ai/nestimate/compare/v1.33.1...v1.33.2) (2026-07-29), Bug Fixes, Bug Fixes, Changelog, Features (+1 more)

### Community 380 - "File Structure"
Cohesion: 0.20
Nodes (9): File Structure, Global Constraints, Out of scope (explicitly), Task 1: Feed text cleanup utility, Task 2: Attribute-pair parsing and summary, Task 3: New product fields in types + csv-parser, Task 4: buildEmbedText v2 + version stamp, Task 5: Dev re-ingest + verification (+1 more)

### Community 381 - "Global Constraints"
Cohesion: 0.20
Nodes (9): Final verification, Global Constraints, Not in this plan, Task 1: The `isQuotaError` predicate, Task 2: Pack resolver — back off, and never split on a quota error, Task 3: Classifier — back off, and rethrow on a quota error, Task 4: Report quota degradation in the run summary, Task 5: A readable dev run (+1 more)

### Community 382 - "import-collection-to-live.ts"
Cohesion: 0.27
Nodes (9): app, args, clearCollection(), collection, collectionName, db, docs, main() (+1 more)

### Community 383 - "geocode.ts"
Cohesion: 0.29
Nodes (7): geocodeAddress(), GeocodeOutcome, GeocodeResponse, isSiteLevel(), PRECISE_LOCATION_TYPES, SITE_LEVEL_RESULT_TYPES, body()

### Community 384 - "labour-rate.ts"
Cohesion: 0.22
Nodes (9): CreateLabourRateRequest, LabourRate, LabourRatesResponse, RATE_UNIT_LABELS, RATE_UNIT_SELECT_LABELS, RateUnit, SKILL_LEVEL_LABELS, SkillLevel (+1 more)

### Community 385 - "TestWindowTightPairInterior"
Cohesion: 0.53
Nodes (4): FirestoreTimestampLike, hasToDate(), toEstimateListRow(), toMillis()

### Community 387 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Pipeline Checkpointing Implementation Plan, Task 1: PipelineCheckpointer + run-ID plumbing, Task 2: Wire the checkpointer into the v1 flow, Task 3: Invisible retries — failure handler + processor wiring, Task 4: Start a pipeline run at enqueue, Task 5: Frontend — render retrying as processing, Task 6: Final verification sweep

### Community 388 - "Travis Perkins RAG — Categorisation Fix Design"
Cohesion: 0.22
Nodes (9): Acceptance criteria, Architecture decision: symmetric classification, Context, Goals, Non-goals, Out of scope (flagged for follow-up), Rollout, Travis Perkins RAG — Categorisation Fix Design (+1 more)

### Community 389 - "Investigation Timeline"
Cohesion: 0.22
Nodes (9): Investigation Timeline, Step 1 — Verifying both estimate flows invoke the cost engineer, Step 2 — Two silent failure modes in the cost-engineer stack, Step 3 — Locating the real culprit: the Travis Perkins lookup tool, Step 4 — The "Overwriting" log was a red herring, Step 5 — Root cause: pre-filter matches zero documents, Step 6 — Why the Knauf product is mis-categorised, Step 7 — Widening the lens: vocabulary coverage gap (+1 more)

### Community 390 - "run-tp-ingest.ts"
Cohesion: 0.10
Nodes (30): ALLOWED_PROJECTS, main(), confirm(), Env, ENVS, fetchApiKey(), PROJECTS, resolveEnv() (+22 more)

### Community 391 - "estimate-status-cell.tsx"
Cohesion: 0.31
Nodes (5): EstimateProgress, Progress, ProgressProps, EstimateStatusCell(), EstimateStatusCellProps

### Community 392 - "failure-handler.test.ts"
Cohesion: 0.22
Nodes (8): base, logger, mockCreateProgress, mockEmit, mockIsEmulator, mockIsTaskSuperseded, mockMarkTempFilesFailed, mockUpdateEstimateStatus

### Community 393 - "complete-google-signup.test.ts"
Cohesion: 0.22
Nodes (8): auth, createOrResumeAuthUser, getUserByUid, googleUser, provisionNewCustomer, sendPasswordResetRequest, validatePasswordResetRequest, validPayload

### Community 394 - "File Structure"
Cohesion: 0.25
Nodes (7): File Structure, Global Constraints, Out of scope (explicitly), Task 1: Shared band-assembly helpers (refactor, behavior-preserving), Task 2: Leaf distribution with parent rollup, Task 3: Dev verification + record results, TP Leaf Tier Bands (Redesign Step 3) Implementation Plan

### Community 395 - "Bill of Materials — Remove VAT Implementation Plan"
Cohesion: 0.25
Nodes (7): Bill of Materials — Remove VAT Implementation Plan, File Structure, Global Constraints, Manual Verification, Task 1: PDF totals block, Task 2: XLSX totals rows, Task 3: Collapse BomReport to one net total

### Community 396 - "PR body"
Cohesion: 0.25
Nodes (7): Blast radius, ⛔ Deploy order, Known residual, PR body, PR title, Verification, What changes

### Community 397 - "QS Agent — NRM2 Material Itemisation with Travis Perkins Grounding"
Cohesion: 0.25
Nodes (7): Cost and latency, Goal, Non-goals, Out of scope, Problem, QS Agent — NRM2 Material Itemisation with Travis Perkins Grounding, Testing strategy

### Community 398 - "Testing"
Cohesion: 0.25
Nodes (7): E2E — the only level that hits real third parties, Integration / API — no real third party, Isolation and determinism, Never reach production, Testing, Unit — pure logic, no mocking, What not to test

### Community 399 - "Workflow — the standard dev loop"
Cohesion: 0.25
Nodes (7): 1. Worktree — every change, no exceptions, 2. Environment, 3. Iterate until approved, 4. Once approved, 6. Finish, Look for an existing worktree before you create one, Workflow — the standard dev loop

### Community 400 - "compilerOptions"
Cohesion: 0.25
Nodes (7): compilerOptions, module, moduleResolution, noEmit, types, extends, include

### Community 401 - "package.json"
Cohesion: 0.25
Nodes (7): engines, node, main, name, private, volta, node

### Community 402 - "migrate-users-to-credits.ts"
Cohesion: 0.36
Nodes (7): arg, db, ENV_MAP, freeCreditsObject(), logTransaction(), main(), unlimitedCreditsObject()

### Community 403 - "tsconfig.json"
Cohesion: 0.25
Nodes (7): compilerOptions, lib, noEmit, rootDir, exclude, extends, include

### Community 404 - "directives-pipeline.integration.test.ts"
Cohesion: 0.32
Nodes (7): buildQsOutput(), complianceExclusionsForRun, GENERIC_ATTRIBUTION, labourEntry(), material(), RunFlowOpts, runFlowWith()

### Community 405 - "compilerOptions"
Cohesion: 0.25
Nodes (7): compilerOptions, module, moduleResolution, noEmit, types, extends, include

### Community 408 - "Repository Instructions"
Cohesion: 0.29
Nodes (6): Attribution, Design Principle, Project, Repository Instructions, Required References, Temporary Files

### Community 409 - "Key Components"
Cohesion: 0.29
Nodes (7): 1. BaseActionSheet, 2. MaterialEditSheet, 3. LabourEditSheet, 4. WorkSectionEditSheet, Architecture, Component Structure, Key Components

### Community 410 - "Slim Materials Sub-Agent Input Schema Implementation Plan"
Cohesion: 0.29
Nodes (6): File Structure, Global Constraints, Self-Review, Slim Materials Sub-Agent Input Schema Implementation Plan, Task 1: Slim input schema + orchestrator projection + prompt, Task 2: Remove the dead `rooms` plumbing

### Community 411 - "Follow-up: PREVENT estimates from getting stuck (root-cause work)"
Cohesion: 0.29
Nodes (6): Also carried over (non-blocking Minors from the reaper branch), Follow-up: PREVENT estimates from getting stuck (root-cause work), Keep the reaper, Prevention options (highest leverage first), Root cause (confirmed), Why this exists

### Community 412 - "Materials sub-agent"
Cohesion: 0.29
Nodes (7): Identity, Input, Materials sub-agent, NRM2 itemisation tables baked into the prompt, Output, Prompt skeleton, Why Flash-Lite is sufficient

### Community 413 - "Schema changes"
Cohesion: 0.29
Nodes (7): `MaterialItemSchema` (stored estimate) — extended, `MaterialItemWithMatchSchema` — extended, Migration, `pricingAttribution` on `MaterialItemWithMatchSchema`, Schema changes, `SupplierRef` — no schema change, but a contract change, `unitPrice` contract change

### Community 414 - "package.json"
Cohesion: 0.29
Nodes (6): description, license, name, private, scripts, type-check

### Community 415 - "packages"
Cohesion: 0.29
Nodes (6): changelog-path, include-component-in-tag, package-name, packages, release-type, $schema

### Community 416 - "index.tsx"
Cohesion: 0.06
Nodes (25): App(), AppProvider(), AppProviderProps, AppRouter(), convert(), ErrorBoundary(), MainErrorFallback(), DashboardLayout() (+17 more)

### Community 417 - "file-converters.ts"
Cohesion: 0.52
Nodes (6): convertDocxToHtmlText(), convertFile(), CONVERTIBLE_EXTENSIONS, convertXlsxToText(), getFileExtension(), needsConversion()

### Community 418 - "firestore-rules.test.ts"
Cohesion: 0.29
Nodes (6): assistantUserToken, customerAUser2Token, customerAUserToken, customerBUserToken, mockEstimate, mockVersion

### Community 420 - "._spy_kwargs"
Cohesion: 0.43
Nodes (3): The function is a transport wrapper: run_extract must be called with     exactly, A new run_extract parameter whose default differs from what app.py         passe, TestExtractionOptions

### Community 421 - "Mobile Action Sheet Editing Implementation"
Cohesion: 0.33
Nodes (5): Conclusion, Mobile Action Sheet Editing Implementation, Overview, Problem Statement, Solution: Action Sheet-Based Editing

### Community 422 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Global Constraints, Preliminaries as a Separate Cost Summary Line — Implementation Plan, Task 1: `isPreliminariesSection` shared-lib helper, Task 2: `calculateDirectCostCategories`, Task 3: `CostBreakdown.prelims` and `calculateItemMarkup`

### Community 423 - "Cost engineer changes"
Cohesion: 0.33
Nodes (6): Cost engineer changes, Input schema simplification, New materials pricing rule (collapses to one paragraph), Ownership matrix, Removals, What stays

### Community 424 - "Main QS agent prompt changes"
Cohesion: 0.33
Nodes (6): Main QS agent prompt changes, Orchestrator change, QS output schema change, Specific edits, What gets removed, What stays

### Community 425 - "folder-upload.spec.ts"
Cohesion: 0.47
Nodes (3): createUploadTree(), PNG_1X1, UploadTree

### Community 426 - "verify-pallet-quantity-verdicts.ts"
Cohesion: 0.40
Nodes (5): main(), money(), Row, StoredFact, SuspectDoc

### Community 429 - "estimate-identity.ts"
Cohesion: 0.50
Nodes (3): A filled wall band exported as two triangles (CAD fill triangulation).      Each, TestFillSeams, triangulated_fill_band_v()

### Community 432 - "User Experience Features"
Cohesion: 0.40
Nodes (5): 1. Touch-Optimized Interface, 2. Visual Feedback, 3. Accessibility, 4. Performance Optimizations, User Experience Features

### Community 433 - "Implementation Details"
Cohesion: 0.40
Nodes (5): Action Sheet Integration, Field Path System, Form Validation, Implementation Details, Real-Time Calculations

### Community 434 - "Architecture"
Cohesion: 0.40
Nodes (5): Architecture, Current pipeline, Key implications, New pipeline, Why the existing `reviewWorkSections` tool inside the main QS does not cover this

### Community 435 - "Implementation Plan"
Cohesion: 0.40
Nodes (5): Implementation Plan, Phase 1 — Acute fix (closes the symptom), Phase 2 — Backfill existing docs, Phase 3 — Housekeeping (independent of acute fix), Phase 4 — Validation

### Community 437 - "reset-user-password.ts"
Cohesion: 0.60
Nodes (4): auth, generatePassword(), main(), prompt()

### Community 440 - "main"
Cohesion: 0.60
Nodes (4): main(), process_file(), Path, Run Phase 1 (extract) + Phase 2 (serialize) on a single HTML file.

### Community 441 - "head.tsx"
Cohesion: 0.06
Nodes (34): CompleteSignupRoute(), RegisterRoute(), isRegistrationAvailable, isRegistrationAvailable, AuthLayout(), LayoutProps, Head(), HeadProps (+26 more)

### Community 445 - "Future Enhancements"
Cohesion: 0.50
Nodes (4): 1. Advanced Features, 2. Enhanced Validation, 3. Improved UX, Future Enhancements

### Community 446 - "Testing Strategy"
Cohesion: 0.50
Nodes (4): Integration Testing, Testing Strategy, Unit Testing, User Experience Testing

### Community 447 - "Performance Considerations"
Cohesion: 0.50
Nodes (4): Memory Management, Mobile-Specific Optimizations, Performance Considerations, Rendering Optimization

### Community 448 - "Review stages"
Cohesion: 0.50
Nodes (4): AI reviewer (`reviewerAgent`) — extended for post-fan-out, Deterministic reviewer — stage split, Labour-cost share — moved to post-costing, Review stages

### Community 449 - "TP retrieval — two tools"
Cohesion: 0.50
Nodes (4): Tool A — `getTpCategoryPriceDistribution` (new), Tool B — `lookupTravisPerkinsProducts` (extended), TP retrieval — two tools, Why two tools, not one

### Community 452 - "firebase-cleanup.test.ts"
Cohesion: 0.50
Nodes (3): mockApp, mockDb, mockStorage

### Community 455 - "[1.34.0](https://github.com/nestimate-ai/nestimate/compare/v1.33.2...v1.34.0) (2026-07-30)"
Cohesion: 0.67
Nodes (3): [1.34.0](https://github.com/nestimate-ai/nestimate/compare/v1.33.2...v1.34.0) (2026-07-30), Bug Fixes, Features

### Community 456 - "[1.36.0](https://github.com/nestimate-ai/nestimate/compare/v1.35.1...v1.36.0) (2026-08-04)"
Cohesion: 0.67
Nodes (3): [1.36.0](https://github.com/nestimate-ai/nestimate/compare/v1.35.1...v1.36.0) (2026-08-04), Bug Fixes, Features

### Community 457 - "[1.38.0](https://github.com/nestimate-ai/nestimate/compare/v1.37.0...v1.38.0) (2026-08-04)"
Cohesion: 0.67
Nodes (3): [1.38.0](https://github.com/nestimate-ai/nestimate/compare/v1.37.0...v1.38.0) (2026-08-04), Bug Fixes, Features

### Community 458 - "[1.39.0](https://github.com/nestimate-ai/nestimate/compare/v1.38.0...v1.39.0) (2026-08-04)"
Cohesion: 0.67
Nodes (3): [1.39.0](https://github.com/nestimate-ai/nestimate/compare/v1.38.0...v1.39.0) (2026-08-04), Bug Fixes, Features

### Community 459 - "[1.40.0](https://github.com/nestimate-ai/nestimate/compare/v1.39.0...v1.40.0) (2026-08-12)"
Cohesion: 0.67
Nodes (3): [1.40.0](https://github.com/nestimate-ai/nestimate/compare/v1.39.0...v1.40.0) (2026-08-12), Bug Fixes, Features

### Community 460 - "[1.42.0](https://github.com/nestimate-ai/nestimate/compare/v1.41.0...v1.42.0) (2026-08-26)"
Cohesion: 0.67
Nodes (3): [1.42.0](https://github.com/nestimate-ai/nestimate/compare/v1.41.0...v1.42.0) (2026-08-26), Bug Fixes, Features

### Community 461 - "[1.43.0](https://github.com/nestimate-ai/nestimate/compare/v1.42.2...v1.43.0) (2026-09-01)"
Cohesion: 0.67
Nodes (3): [1.43.0](https://github.com/nestimate-ai/nestimate/compare/v1.42.2...v1.43.0) (2026-09-01), Bug Fixes, Features

### Community 462 - "Configuration"
Cohesion: 0.67
Nodes (3): Action Sheet Behavior, Configuration, Validation Rules

### Community 463 - "Integration with Existing System"
Cohesion: 0.67
Nodes (3): Calculation Hook Integration, Integration with Existing System, Responsive Layout

### Community 464 - "Troubleshooting"
Cohesion: 0.67
Nodes (3): Common Issues, Debug Tools, Troubleshooting

### Community 465 - "Dependencies"
Cohesion: 0.67
Nodes (3): Dependencies, Internal Dependencies, Primary Dependencies

### Community 466 - "Migration Guide"
Cohesion: 0.67
Nodes (3): Example Migration, From Inline Editing, Migration Guide

### Community 467 - "Error handling"
Cohesion: 0.67
Nodes (3): Deterministic fallback itemiser, Error handling, `transformQSToWorkSections` must preserve new fields

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **3285 isolated node(s):** `parameters`, `decorators`, `{ create: actualCreate, createStore: actualCreateStore }`, `storeResetFns`, `create` (+3280 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **113 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `app.py` to `test_layout_segmenter.py`, `Double-Door Merge & Gemini Client`, `Arc Detection Primitives`, `Double-Arc Split Tests`, `Arc Cap-Trim Tests`, `TestAnnotationPenBarriers`, `plumber.py`, `renderer.py`, `batch_extract.py`, `QuadPerimeterTests`, `build_ink_map`, `_is_light_pen`, `test_sliding_doors.py`, `TestMinWidthNegativeControl`, `test_batch_extract.py`, `TestMarkerRings`, `detect_doors`, `vline`, `_bridge_white_runs`, `_find_openings`, `batch_extract.py`, `_segments_min_distance`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `AttachmentsDownloadModal()` connect `_collect_wall_faces` to `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `detect_doors`, `renderer.py`, `hline`, `TestSlidingScaleBehavior`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `dot()` connect `detect_doors` to `_collect_wall_faces`, `app.py`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **What connects `parameters`, `decorators`, `{ create: actualCreate, createStore: actualCreateStore }` to the rest of the system?**
  _4044 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Pipeline Orchestration & Extraction` be split into smaller, more focused modules?**
  _Cohesion score 0.08145363408521303 - nodes in this community are weakly interconnected._