# Graph Report - agent  (2026-07-07)

## Corpus Check
- 52 files · ~67,628 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 988 nodes · 2359 edges · 111 communities (54 shown, 57 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 108 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1377373c`
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
- [[_COMMUNITY_Wall Layer Hints & Snapping|Wall Layer Hints & Snapping]]
- [[_COMMUNITY_windows.py|windows.py]]
- [[_COMMUNITY_Arc Spur-Pruning Tests|Arc Spur-Pruning Tests]]
- [[_COMMUNITY_Chained-Curve Swing Tests|Chained-Curve Swing Tests]]
- [[_COMMUNITY__fit_circle_3pt|_fit_circle_3pt]]
- [[_COMMUNITY_Candidate|Candidate]]
- [[_COMMUNITY_Hu-Moment Template Tool|Hu-Moment Template Tool]]
- [[_COMMUNITY_hline|hline]]
- [[_COMMUNITY_Extraction Strategy (project.md)|Extraction Strategy (project.md)]]
- [[_COMMUNITY_Spur-Pruning Design Spec|Spur-Pruning Design Spec]]
- [[_COMMUNITY_Package Restructure Design|Package Restructure Design]]
- [[_COMMUNITY_README stub|README stub]]
- [[_COMMUNITY_detect_windows|detect_windows]]
- [[_COMMUNITY_plumber.py|plumber.py]]
- [[_COMMUNITY_extractor.py|extractor.py]]
- [[_COMMUNITY_Polyline-Arc Spur Pruning — Design|Polyline-Arc Spur Pruning — Design]]
- [[_COMMUNITY__resolve_door_window_conflicts|_resolve_door_window_conflicts]]
- [[_COMMUNITY_Batch PDF Extraction Script Design|Batch PDF Extraction Script Design]]
- [[_COMMUNITY__FillRing|_FillRing]]
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
- [[_COMMUNITY__bridge_white_runs|_bridge_white_runs]]
- [[_COMMUNITY_TestWindowInteriorClutter|TestWindowInteriorClutter]]
- [[_COMMUNITY_batch_extract.py|batch_extract.py]]
- [[_COMMUNITY__Seg|_Seg]]
- [[_COMMUNITY_TestMarkerRings|TestMarkerRings]]
- [[_COMMUNITY_app.py|app.py]]
- [[_COMMUNITY_TestNetworkQueries|TestNetworkQueries]]
- [[_COMMUNITY__is_dashed|_is_dashed]]
- [[_COMMUNITY_TestWindowArbitraryAngle|TestWindowArbitraryAngle]]
- [[_COMMUNITY__dedupe_openings|_dedupe_openings]]
- [[_COMMUNITY_TestFloorPlansRegression|TestFloorPlansRegression]]
- [[_COMMUNITY_TextSpan|TextSpan]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 121 edges
2. `Candidate` - 84 edges
3. `detect_windows()` - 50 edges
4. `TextSpan` - 43 edges
5. `detect_doors()` - 41 edges
6. `DebugTraceCollector` - 38 edges
7. `detect_wall_network()` - 37 edges
8. `rooms_for()` - 32 edges
9. `_cross_validate()` - 26 edges
10. `WallNetwork` - 26 edges

## Surprising Connections (you probably didn't know these)
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` --semantically_similar_to--> `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [INFERRED] [semantically similar]
  5-1133-WD03.pdf → floor-plans.pdf
- `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)` --references--> `Door (architectural element)`  [AMBIGUOUS]
  floor-plans.pdf → 5-1133-WD03.pdf
- `DebugTraceCollector` --uses--> `PathPrimitive`  [INFERRED]
  debug/trace.py → models.py
- `_FillRing` --uses--> `PathPrimitive`  [INFERRED]
  detection/walls.py → models.py
- `_FillRing` --uses--> `TextSpan`  [INFERRED]
  detection/walls.py → models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **5-1133-WD03 proposed lower ground floor: walls, windows, doors** — 5_1133_wd03, 5_1133_wd03_cavity_walls, 5_1133_wd03_windows, 5_1133_wd03_folding_sliding_doors [EXTRACTED 1.00]
- **floor-plans proposed ground & first floor plans with rooms and rooflights** — floor_plans, floor_plans_ground_floor, floor_plans_first_floor, floor_plans_velux [EXTRACTED 1.00]

## Communities (111 total, 57 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.08
Nodes (13): DebugTraceCollector, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Record result of the _is_door_leaf check for a primitive., Register a collected swing. Returns swing_id., Pre-populate by_path_index with raw metadata for every PathPrimitive., Record the swing-anchored single-line leaf search outcome.          `result` is (+5 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.21
Nodes (18): _arc_corners(), _estimate_arc_sweep_deg(), BBox, Estimate sweep angle of a Bézier arc from its endpoints and estimated center., _collect_door_leaves(), _collect_linework_door_leaves(), _find_thin_rectangle_cycle(), _is_door_leaf() (+10 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.15
Nodes (14): diagonal_window(), framed_triple_window(), path(), quad(), Window detection tests.  Ground truth was established interactively on floor-pla, Regression (the bug this gate first introduced): a 45-deg window must         no, The gate works in the rotated frame too: a 45-deg insulation-hatched         wal, A horizontal window rotated by `deg` about (cx, cy).      Identical cap-anchored (+6 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.06
Nodes (32): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, detect_doors(), _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli (+24 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.17
Nodes (10): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Output layout, Pipeline architecture (+2 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.16
Nodes (17): _cross_validate(), True when a wall FACE line runs unbroken through the bbox span.      A real wind, Validate doors/windows against the wall-centerline network.      Doors keep the, _wall_runs_through(), continuous_h_wall(), door(), face(), h_wall_with_gap() (+9 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.15
Nodes (19): _building_masses(), detect_rooms(), _door_plugs(), _free_space_components(), Room detection: rooms are the connected free-space components between walls.  Ea, Fraction of a bbox area covered by the text spans lying over it., Thin barrier bands along the wall planes through a detected door.      The door, Connected wall-solid masses that plausibly belong to a building.      Large mass (+11 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.11
Nodes (37): _component_indices(), _dedupe_door_components(), _door_fallback_candidate(), _find_threshold_line(), _nearest_pair_distance(), _pair_door_assemblies(), BBox, Prefer the strongest door when two candidates use the same primitives. (+29 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.11
Nodes (19): _fit_circle_3pt(), _native_curve_chains(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, ChainedCurveSwingDetectionTests, _circle_arc_chain(), _curve(), FitCircle3PtTests (+11 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.11
Nodes (21): door_candidate(), fill_ring(), hline(), path(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, Rect room with a 45px doorway gap in the top wall (240..285)., Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi (+13 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.18
Nodes (13): hline(), marker_ring(), path(), Wall-network builder tests (detection/walls.py).  Synthetic PathPrimitive fixtur, Filled triangle/dart exploded into chained `l` items (a leader tip)., Horizontal wall drawn as two stroked faces., Four wall bands forming a closed rectangular room (outer faces at the     given, rect_room() (+5 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.11
Nodes (13): _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca, Halves of 3 segs each are below DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS.         Bail., A zigzag chain has many 90° breaks. The detector requires         exactly one br (+5 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.12
Nodes (30): _find_leaf_companion_lines(), Find lines forming the same thin-rect leaf as the anchored leaf line.      Door, _angle_diff_mod180(), _interval_overlap(), _line_angle_deg(), _line_length(), _perpendicular_spacing(), _project_onto_axis() (+22 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.21
Nodes (11): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates, Leaf overlap of 10 px (> DOOR_DOUBLE_LEAF_OVERLAP_PX=5) → two separate candidate (+3 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.15
Nodes (11): Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO, A pure cycle has no leaves to walk from. Skipped. (+3 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.12
Nodes (12): _arc(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., Quarter-circle polyline as n_segs short straight lines., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t, A cycle of more than DOOR_POLYLINE_CYCLE_MAX_SEGMENTS segments         exceeds t (+4 more)

### Community 17 - "Wall Layer Hints & Snapping"
Cohesion: 0.25
Nodes (8): _dedupe_by_perp(), _find_openings(), Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.      A gl, Pair facing caps and confirm a glazing band bridges each opening.      ``cap_poo, _spanning_glazing(), _tight_band()

### Community 18 - "windows.py"
Cohesion: 0.15
Nodes (23): _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _is_arc_like(), _prune_arc_cycle_caps(), _prune_arc_spurs(), Remove a small closed-cycle cap attached at a single articulation point.      So, Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The (+15 more)

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.21
Nodes (8): _chain(), PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun, Polyline through the given points: segs from points[0]→points[1] etc.

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (39): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`), 3.4 Polyline arc + Y-junction stop (spur-prunable) (+31 more)

### Community 21 - "_fit_circle_3pt"
Cohesion: 0.22
Nodes (18): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), extract_tables(), _normalize_bbox_plumber() (+10 more)

### Community 22 - "Candidate"
Cohesion: 0.20
Nodes (16): Client, build_user_message(), call_gemini(), _candidate_to_dict(), encode_image_inline(), init_client(), parse_gemini_response(), should_skip_gemini() (+8 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.17
Nodes (10): hline(), horizontal_window(), A clean 2-line capped rectangle IS a window on 5-1133 (see Window B:         two, 5-1133 FP window_0006: 3 short parallel lines whose opening (15px) is         fa, Three parallel lines with no perpendicular end-caps (e.g. a run of         dimen, Three parallel lines spaced far apart (e.g. stair treads) exceed the         gla, A W1-style horizontal window: 3 tight horizontal glazing lines centered     in a, A W4-style vertical window: 3 tight vertical glazing lines closed by two     hor (+2 more)

### Community 31 - "README stub"
Cohesion: 0.18
Nodes (10): Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional), Inspect — terminal summary only, Output layout, Requirements, Setup (+2 more)

### Community 34 - "detect_windows"
Cohesion: 0.15
Nodes (12): detect_windows(), _frame_axes(), _merge_mullion_chains(), Unit run-axis u (perpendicular to the caps) and perp-axis v (along caps).      C, Join collinear glazing segments across mullion blocks into logical panes.      A, Detect windows as capped openings bridged by a parallel glazing band.      For e, The tight-pair interior gate (WINDOW_TIGHT_PAIR_GAP_PX /     WINDOW_TIGHT_PAIR_J, 5-1133 window_0020: the "recess" niche — a drawn rectangle whose         long si (+4 more)

### Community 35 - "plumber.py"
Cohesion: 0.21
Nodes (18): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., Document, render_page_png(), Entity, Path, _candidate_to_dict() (+10 more)

### Community 36 - "extractor.py"
Cohesion: 0.26
Nodes (15): classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths(), extract_text(), get_ocg_names() (+7 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "_resolve_door_window_conflicts"
Cohesion: 0.29
Nodes (7): Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), BBox, A distant door must not suppress a window it only clips after the         20px d, A DOOR_FALLBACK_CONFIDENCE (0.35) door often IS window-like ink         (glazing, A window candidate sitting ON a fallback door's linework (5-1133:         the jo, TestDoorWindowExclusion

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "_FillRing"
Cohesion: 0.24
Nodes (9): _FillRing, _is_background_fill(), _rate_fill_classes(), A closed same-fill polygon reconstructed from exploded `l` items., Annotation arrowhead: a tiny filled triangle or concave dart.          Walls are, Classify each fill color as wall material (True) or furniture (False).      Vect, Background-colored rings that could be hollow walls or built-in runs.      White, True for fills indistinguishable from the page background (white).      CAD expo (+1 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.21
Nodes (7): _collect_wall_faces(), _is_dashed(), True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., Return (stroked wall faces, filled-band centerlines)., _wall_layer_hint(), TestDashDetection, TestFaceCollection

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.17
Nodes (11): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target) (+3 more)

### Community 44 - "renderer.py"
Cohesion: 0.33
Nodes (12): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _load_font(), BBox, Room entities carry their closed polygon; draw its true shape instead     of the (+4 more)

### Community 98 - "vline"
Cohesion: 0.29
Nodes (5): _covers(), Ground truth captured interactively on 5-1133-WD03.pdf (run     2026-06-19_12-02, A toilet/sink fixture is a hatch of stacked short segments plus         collinea, TestWindow51133Topology, vline()

### Community 99 - "_bridge_white_runs"
Cohesion: 0.29
Nodes (8): _bridge_white_runs(), _equivalent_sides(), (short, long) of the rectangle with this polygon's area and perimeter.      The, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      A wa, Accepted hollow-wall/joinery _FillRing over the given rectangle., Bridges close OPEN SPANS in accepted white-ring runs; rings already     connecte, TestWhiteRunBridging, white_ring()

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.25
Nodes (6): A real window's glazing band is clear glass — nothing between the panes.     An, Control: the bare 2-line capped opening with an empty band interior is         s, 5-1133 FP w19/w21/w25/w32/w33: an insulation-hatched wall. The two         wall, Insulation hatch drawn with pure line segments (no re/qu/c): the         diagona, Decorations OUTSIDE the pane band (here, well beyond a cap along the         run, TestWindowInteriorClutter

### Community 101 - "batch_extract.py"
Cohesion: 0.29
Nodes (9): build_extract_command(), find_pdfs(), main(), prompt_bool(), Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive)., Build the extract command for a single PDF., Run extract command for a single PDF.     Returns (pdf_path, success: bool, outp (+1 more)

### Community 102 - "_Seg"
Cohesion: 0.22
Nodes (8): _point_to_segment_distance(), Minimum distance from point p to line segment ab., _line_intersection(), Working segment during network construction., Intersection of the two infinite lines, or None when near-parallel., Snap endpoints onto exact centerline intersection points.      Two centerlines m, _Seg, _snap_intersections()

### Community 103 - "TestMarkerRings"
Cohesion: 0.19
Nodes (9): detect_wall_network(), One merged wall-face run with the evidence its members carried., Build the internal wall-centerline network for a page., WallFace, fill_ring(), Closed filled rectangle exploded into 4 chained `l` items., Leader/dimension arrowheads share the wall pen on Vectorworks-style     exports;, TestFillClassRating (+1 more)

### Community 104 - "app.py"
Cohesion: 0.52
Nodes (6): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., Namespace

### Community 106 - "_is_dashed"
Cohesion: 0.17
Nodes (11): BBox, Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox., Max fraction of the bbox long axis covered by one near-collinear centerline., True when the two segments cross at an interior point.      _segments_min_distan, Min distance between a segment and an axis-aligned bbox (0 if touching). (+3 more)

### Community 107 - "TestWindowArbitraryAngle"
Cohesion: 0.40
Nodes (3): Windows are drawn at any angle, not just axis-aligned. The cap-anchored     mode, 5-1133-WD03.pdf missed window at path idx 6475: three glazing panes         at 1, TestWindowArbitraryAngle

### Community 108 - "_dedupe_openings"
Cohesion: 0.50
Nodes (4): _area(), _dedupe_openings(), BBox, Suppress overlapping detections from duplicate cap pairs (greedy NMS).      Dupl

### Community 110 - "TextSpan"
Cohesion: 0.42
Nodes (7): detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re, run_heuristics(), detect_schedules(), One wall centerline segment (pixel space, y-down)., WallSegment, TextSpan

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **143 isolated node(s):** `Project purpose`, `Algorithm reference`, `Commands`, `Module layout`, `Gemini / GCP auth` (+138 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **57 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `windows.py` to `Pipeline Orchestration & Extraction`, `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `Double-Door Merge & Gemini Client`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `Window Geometry Internals`, `Room Polygonization Internals`, `Arc Cap-Trim Tests`, `Arc Cycle-Cap Pruning Tests`, `Arc Spur-Pruning Tests`, `Candidate`, `hline`, `detect_windows`, `extractor.py`, `_resolve_door_window_conflicts`, `_FillRing`, `_collect_wall_faces`, `vline`, `_bridge_white_runs`, `TestWindowInteriorClutter`, `_Seg`, `TestMarkerRings`, `TestNetworkQueries`, `_is_dashed`, `TestWindowArbitraryAngle`, `TestFloorPlansRegression`, `TextSpan`?**
  _High betweenness centrality (0.271) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Candidate` to `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `Debug Trace Collector`, `Room Detection Tests`, `Window Geometry Internals`, `Room Polygonization Internals`, `windows.py`, `hline`, `detect_windows`, `plumber.py`, `_resolve_door_window_conflicts`, `renderer.py`, `vline`, `TestWindowInteriorClutter`, `TestWindowArbitraryAngle`, `_dedupe_openings`, `TestFloorPlansRegression`, `TextSpan`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `detect_windows()` connect `detect_windows` to `Window Detection & Tests`, `Door Detection & Tests`, `vline`, `TestWindowInteriorClutter`, `Debug Trace Collector`, `TestWindowArbitraryAngle`, `_dedupe_openings`, `Window Geometry Internals`, `TextSpan`, `Wall Layer Hints & Snapping`, `windows.py`, `Candidate`, `hline`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 43 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_FillRing`) actually correct?**
  _`PathPrimitive` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `Candidate` (e.g. with `TestDoorPenalties` and `TestEmptyNetwork`) actually correct?**
  _`Candidate` has 25 INFERRED edges - model-reasoned connections that need verification._