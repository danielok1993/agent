# Graph Report - agent  (2026-07-30)

## Corpus Check
- 81 files · ~131,749 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1638 nodes · 4240 edges · 121 communities (65 shown, 56 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 240 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `56b17183`
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
- [[_COMMUNITY__find_openings|_find_openings]]
- [[_COMMUNITY_EntranceDoorTests|EntranceDoorTests]]
- [[_COMMUNITY_app.py|app.py]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY__collect_wall_faces|_collect_wall_faces]]
- [[_COMMUNITY_Floor-plan region filtering|Floor-plan region filtering]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
- [[_COMMUNITY_test_door_assembly.py|test_door_assembly.py]]
- [[_COMMUNITY_batch_extract.py|batch_extract.py]]
- [[_COMMUNITY_DoorV2OpeningCheckTests|DoorV2OpeningCheckTests]]
- [[_COMMUNITY__segments_min_distance|_segments_min_distance]]
- [[_COMMUNITY_File Structure|File Structure]]
- [[_COMMUNITY_TestGardenDoorSeals|TestGardenDoorSeals]]
- [[_COMMUNITY_EntranceDoorTests|EntranceDoorTests]]

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 197 edges
2. `Candidate` - 106 edges
3. `TextSpan` - 93 edges
4. `PageData` - 86 edges
5. `detect_wall_network()` - 70 edges
6. `Region` - 59 edges
7. `detect_windows()` - 50 edges
8. `detect_doors()` - 45 edges
9. `rooms_for()` - 45 edges
10. `DebugTraceCollector` - 44 edges

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

## Communities (121 total, 56 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.10
Nodes (9): DebugTraceCollector, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Register a collected swing. Returns swing_id., Record the swing-anchored single-line leaf search outcome.          `result` is, Register a collected leaf. Returns leaf_id., Record a final candidate with its full confidence breakdown. (+1 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.12
Nodes (24): cache_file(), cache_key(), load_regions(), page_content_hash(), Path, On-disk cache of region classifications, keyed by page content AND the segmentat, Stable digest of a page's vector geometry and text. Changes if the PDF     is ed, Stable digest of a segmentation's geometry — the boxes and where they     came f (+16 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.05
Nodes (48): detect_windows(), Detect windows as capped openings bridged by a parallel glazing band.      For e, _covers(), diagonal_window(), framed_triple_window(), hline(), horizontal_window(), path() (+40 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.27
Nodes (6): detect_doors(), line(), quarter_arc_lines(), Swing-anchored single-line leaf check (v3).      A door panel is often drawn as, rect_lines(), SingleLineLeafTests

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.15
Nodes (11): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Other rules, Output layout (+3 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.09
Nodes (29): _cross_validate(), True when a wall FACE line runs unbroken through the bbox span.      A real wind, Validate doors/windows against the wall-centerline network.      Doors keep the, _wall_runs_through(), One wall centerline segment (pixel space, y-down)., One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline. (+21 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.13
Nodes (15): Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, _split_double_arc(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di, A clean 11-seg quarter arc has only ~8° per-seg deltas — well         below the, The §3.6 cap-extension pattern: 11-seg arc + 2-seg perpendicular         axis ca (+7 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.09
Nodes (51): _absorb_hinged_white_rings(), _detect_folding_doors(), _double_line_leaves(), _fold_edges(), _fold_groups(), _leaf_tip(), _mean_axis_deg(), _open_v_match() (+43 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.05
Nodes (43): _bridge_white_runs(), detect_wall_network(), _equivalent_sides(), _is_light_pen(), Build the internal wall-centerline network for a page.      exclude_path_indices, Faint (light-grey/pastel) ink: every channel at/above the light floor., (short, long) of the rectangle with this polygon's area and perimeter.      The, Band-shaped convex hulls closing the gaps in accepted white-ring runs.      A wa (+35 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.08
Nodes (27): door_candidate(), fill_ring(), hline(), path(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, Rect room with a 45px doorway gap in the top wall (240..285)., Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi (+19 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.12
Nodes (18): block(), one_blob_page(), page_with_a_dropped_strip(), raster_page(), Region resolution rules (pipeline.resolve_page_regions).  A stub classifier stan, Filtering only pays if the regions hold the sheet's ink., two_blob_page plus a 52px-tall strip of real drawing.      It is its own leaf, b, Returns a callable matching classify_regions' signature. (+10 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.06
Nodes (57): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., Client, generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces. (+49 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.06
Nodes (32): Authoritative symbol → module assignment, Codebase Restructure Implementation Plan, Computed module headers, Dependency graph (verified acyclic), `detection/doors/arcs.py` (deps: `math`, `models`, `debug.trace`, `geometry`, `layers`, `doors.constants`, `doors.models`), `detection/doors/assembly.py` (deps: `models`, `geometry`, `layers`, `doors.constants`, `doors.models`, `doors.leaves`, `doors.shape`, `labels`), `detection/doors/constants.py` (deps: `re`), `detection/doors/detect.py` (deps: `models`, `debug.trace`, `doors.arcs`, `doors.leaves`, `doors.assembly`) (+24 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.08
Nodes (28): detect(), EndToEndTests, fold_chain(), FoldChainTests, folding_of(), leaf(), OpenVTests, parked_stack() (+20 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.18
Nodes (8): _door_plugs(), Bbox short-end edges of a sliding door: across the wall, never wall plane., Thin barrier bands along the wall planes through a detected door.      The door, _sliding_end_edges(), Plug extensions end at their supporting material; slide ends veto.      Geometry, Interrupted-run plugs need jambs that REACH the plug band and a mid     that is, TestPlugPlaneEvidence, TestPlugTailTrim

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.16
Nodes (13): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, _chain(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t (+5 more)

### Community 17 - "arcs.py"
Cohesion: 0.10
Nodes (22): Record result of the _is_door_leaf check for a primitive., Pre-populate by_path_index with raw metadata for every PathPrimitive., Record result of the _is_arc_like check for a primitive., Record whether a line segment passed the polyline-arc length filter., _native_curve_chains(), Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, _compute_hu_distance(), _rasterize_paths_to_canvas() (+14 more)

### Community 18 - "windows.py"
Cohesion: 0.33
Nodes (5): _collect_material_marks(), _is_dashed(), (midpoint, angle) of every short solid stroke, gathered once per page.      Thes, True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., TestDashDetection

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.16
Nodes (13): Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), _arc(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO (+5 more)

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (43): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.10 Folding/bifold doors — no arc (`detection/doors/folding.py`), 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`) (+35 more)

### Community 21 - "_fit_circle_3pt"
Cohesion: 0.12
Nodes (28): _door_fallback_candidate(), _find_threshold_line(), _leaf_ink_indices(), _nearest_pair_distance(), _pair_door_assemblies(), BBox, Find an entrance-door threshold/sill line parallel to the leaf long axis.      T, Parse an evidence bbox value defensively; return None on any invalid shape. (+20 more)

### Community 22 - "geometry.py"
Cohesion: 0.10
Nodes (43): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), _fit_circle_3pt(), _is_arc_like(), BBox (+35 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "hline"
Cohesion: 0.22
Nodes (12): build_request_parts(), classify_regions(), BBox, Page, Ask Gemini what each segmented region is.  One call per page. Each region goes a, One API call for the whole page. Returns classified regions + warnings., Render one region as its own PNG, scaled so its long edge is about     CROP_TARG, Distinct text inside a region, largest font first. Many CAD exports     outline (+4 more)

### Community 31 - "README stub"
Cohesion: 0.18
Nodes (10): Architectural PDF Extraction (POC), Batch extract, Extract — full pipeline, Gemini / GCP auth (optional), Inspect — terminal summary only, Output layout, Requirements, Setup (+2 more)

### Community 34 - "detect_windows"
Cohesion: 0.29
Nodes (7): Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), BBox, A distant door must not suppress a window it only clips after the         20px d, A DOOR_FALLBACK_CONFIDENCE (0.35) door often IS window-like ink         (glazing, A window candidate sitting ON a fallback door's linework (5-1133:         the jo, TestDoorWindowExclusion

### Community 35 - "plumber.py"
Cohesion: 0.18
Nodes (9): _prune_arc_spurs(), Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun (+1 more)

### Community 36 - "_projected_interval"
Cohesion: 0.13
Nodes (17): assigned_path_fraction(), _centre_in_any(), filter_page_data(), BBox, Reduce a PageData to the primitives inside a set of regions.  This filters, it d, A copy of page_data holding only primitives whose bbox centre falls in     one o, Share of the page's paths that any region would keep.      Deliberately the same, Text spans inside the given regions. Used to scope schedule detection to     sch (+9 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "renderer.py"
Cohesion: 0.08
Nodes (30): Tunable constants for page segmentation.  Values are measured, not guessed — see, build_ink_map(), InkMap, is_page_spanning(), Binary ink occupancy map over a page, used to find whitespace gutters., bins[row][col] is 1 where drawn ink falls, 0 elsewhere., True for sheet furniture: a border rule or column divider that runs the     leng, _clip_cut() (+22 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "batch_extract.py"
Cohesion: 0.15
Nodes (17): _building_masses(), detect_rooms(), _folding_chain_gap_plug(), _free_space_components(), Room detection: rooms are the connected free-space components between walls.  Ea, Fraction of a bbox area covered by the text spans lying over it., Barrier polygon sealing a window opening.      A horizontal/vertical window's bb, Seal the doorway a PARKED folding chain leaves uncovered.      A concertina draw (+9 more)

### Community 41 - "_collect_wall_faces"
Cohesion: 0.15
Nodes (14): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, OpenLeafExclusionTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates (+6 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.17
Nodes (11): 1. The signature (cap-anchored), 1b. Framed multi-light windows (5-1133 W8), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target) (+3 more)

### Community 44 - "renderer.py"
Cohesion: 0.16
Nodes (9): _door_attribute_overlay(), finalize_candidates(), Promote candidates to entities, applying the offline confidence floors.      Gem, Selected door-evidence keys to merge into Entity.attributes. {} for None / non-d, assembly_type must reach Entity.attributes through the pipeline passthrough., cand(), finalize_candidates applies the offline confidence floors unconditionally., TestFinalizeCandidates (+1 more)

### Community 98 - "vline"
Cohesion: 0.32
Nodes (6): apply_classification(), Apply a classification response to a region list.      Returns new Region object, Region classification parsing tests (gemini/classifier.py).  No API calls: apply, region(), response(), TestApplyClassification

### Community 99 - "wall_band_h"
Cohesion: 0.30
Nodes (9): door_open_leaf_path_indices(), Path indices of swing doors' OPEN leaf linework.      A swing door's leaf is dra, detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re, run_heuristics(), detect_schedules(), Candidate, DoorEvidencePropagationTests (+1 more)

### Community 100 - "TestWindowInteriorClutter"
Cohesion: 0.25
Nodes (8): _demote_lattice_faces(), _max_rung_stack(), Split merged faces into (kept, striped-field members).      A striped field is >, Face indices belonging to striped runs under one tier's thresholds.      Rungs s, True when two rungs' extents neither overlap nor nearly touch., Deepest simultaneous rung coverage along the run's axis.      Sweeps the rungs', _rungs_apart(), _scan_striped_runs()

### Community 101 - "TestMarkerRings"
Cohesion: 0.25
Nodes (8): _dedupe_by_perp(), _find_openings(), Collapse near-collinear duplicates (same perp offset) to one record.      A toil, Largest run of panes spaced like glazing, not like stair treads.      Walks the, Distinct parallel glazing lines that connect cap ``c1`` to cap ``c2``.      A gl, Pair facing caps and confirm a glazing band bridges each opening.      ``cap_poo, _spanning_glazing(), _tight_band()

### Community 102 - "DoorV2OpeningCheckTests"
Cohesion: 0.29
Nodes (6): Bbox edges meeting at the hinge corner of a single quarter-swing door.      A sw, Hold a single swing door to plugs on its hinge edges, one plane only.      A qua, _restrict_swing_plugs(), _swing_hinge_edges(), Single swing doors: plugs live on the hinge edges, one wall plane.      Geometry, TestSwingHingePlugRestriction

### Community 103 - "PathPrimitive"
Cohesion: 0.29
Nodes (4): FitCircle3PtTests, Three collinear points have no unique circumscribed circle., Trivial sanity check on the formula: 3 points on a circle of         radius 5 ce, Recover an offset center and radius from a different angular spread.

### Community 104 - "detect_doors"
Cohesion: 0.06
Nodes (45): _apply(), _as_transform(), classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths() (+37 more)

### Community 105 - "PageData"
Cohesion: 0.53
Nodes (5): key(), load(), main(), Diff two extraction runs by their final entities.  Usage:     python tools/compa, rejected_key()

### Community 106 - "TestNetworkQueries"
Cohesion: 0.50
Nodes (4): _line_intersection(), Intersection of the two infinite lines, or None when near-parallel., Snap endpoints onto exact centerline intersection points.      Two centerlines m, _snap_intersections()

### Community 109 - "_find_openings"
Cohesion: 0.10
Nodes (26): _line_angle_deg(), _line_length(), _band_has_wall_material(), _claims_interior_pair(), _dimension_line_indices(), _face_is_material_backed(), True when the band under a centerline carries drawn wall material.      Counts s, True when same-pen hatch strokes hug one flank of the face's run.      A hatched (+18 more)

### Community 110 - "EntranceDoorTests"
Cohesion: 0.19
Nodes (14): _centre_in(), count_paths_in(), _merge_captions(), page_fallback_region(), BBox, Fold zero-path title strips into the drawing they belong to.      A caption is a, Split a page into drawing regions. Returns [] for a page with no vector     ink, The whole page as a single region, for sheets too dense to split. (+6 more)

### Community 111 - "app.py"
Cohesion: 0.14
Nodes (19): _perpendicular_spacing(), _project_onto_axis(), _projected_interval(), Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars., Scalar projection of p onto the unit axis (dx, dy) from origin., _collapse_redundant_centerlines(), _merge_collinear_segs(), _pair_faces_to_centerlines() (+11 more)

### Community 113 - "File Structure"
Cohesion: 0.12
Nodes (16): File Structure, Floor-Plan Region Filtering Implementation Plan, Global Constraints, Self-Review, Task 10: Wire segmentation, classification and filtering into the pipeline, Task 11: Overlay outlines, CLI flag, and docs, Task 12: Regression verification on the reference PDFs, Task 1: Ink occupancy map (+8 more)

### Community 115 - "_collect_wall_faces"
Cohesion: 0.14
Nodes (20): _collect_fill_rings(), _collect_wall_faces(), _collect_weak_faces(), _fill_key(), _FillRing, _pen_key(), _rate_fill_classes(), Wall-network builder.  Walls are internal-only data: they are never emitted as c (+12 more)

### Community 116 - "Floor-plan region filtering"
Cohesion: 0.12
Nodes (15): Approach, Caching, Component: `gemini/classifier.py`, Component: `layout/segmenter.py`, Constants, Data model and outputs, Deletions, Evidence (+7 more)

### Community 121 - "test_curve_arc_garden_doors.py"
Cohesion: 0.27
Nodes (8): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing, The 5-1133-WD03.pdf door_0007 + door_0008 topology, simplified.          Two sta

### Community 122 - "test_door_assembly.py"
Cohesion: 0.19
Nodes (8): DoorAssemblyTests, path(), PolylineArcBinCapTests, 270-degree polyline arc with 16 segments — far wider than a quarter-circle door, Compute 15-degree angle bins for line segments — fixture sanity helper., Tests for the DOOR_POLYLINE_MAX_ANGLE_BINS cap that rejects furniture/appliance, _seg_angle_bins(), wide_arc_lines()

### Community 123 - "batch_extract.py"
Cohesion: 0.31
Nodes (10): build_extract_command(), find_pdfs(), main(), prompt_bool(), Path, Prompt user for a yes/no question, return bool., Find all PDF files in plans_dir (non-recursive)., Build the extract command for a single PDF. (+2 more)

### Community 124 - "DoorV2OpeningCheckTests"
Cohesion: 0.22
Nodes (4): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, DoorV2OpeningCheckTests, Tests for v2 bridge-line opening check and arc sweep estimation.

### Community 126 - "_segments_min_distance"
Cohesion: 0.19
Nodes (10): _point_in_bbox(), BBox, Measure whether a bbox contains wall-like material fill.      Many architectural, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox., Max fraction of the bbox long axis covered by one near-collinear centerline., True when the two segments cross at an interior point.      _segments_min_distan, Min distance between a segment and an axis-aligned bbox (0 if touching)., _segment_bbox_distance() (+2 more)

### Community 127 - "File Structure"
Cohesion: 0.22
Nodes (8): File Structure, Polyline-Arc Spur Pruning Implementation Plan, Self-review notes, Task 1: Add `_prune_arc_spurs` skeleton + clean-arc and pure-cycle tests, Task 2: Implement Y-junction spur pruning, Task 3: Cover multi-spur, oversized, and floor cases, Task 4: Extend `DebugTraceCollector.record_polyline_component` with the two optional kwargs, Task 5: Wire `_prune_arc_spurs` into `_detect_polyline_arc_bboxes`

### Community 128 - "TestGardenDoorSeals"
Cohesion: 0.29
Nodes (4): _open_leaf_edges(), Bbox edges of a garden-layout double door that are room floor, not wall.      A, Wide garden pairs: jamb-scale anchor window + parked-leaf edge veto., TestGardenDoorSeals

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **210 isolated node(s):** `Project purpose`, `Algorithm reference`, `Commands`, `Module layout`, `Gemini / GCP auth` (+205 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `arcs.py` to `Pipeline Orchestration & Extraction`, `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `EntranceDoorTests`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `TestGardenDoorSeals`, `Room Polygonization Internals`, `Arc Cap-Trim Tests`, `Arc Cycle-Cap Pruning Tests`, `windows.py`, `Arc Spur-Pruning Tests`, `_fit_circle_3pt`, `geometry.py`, `detect_windows`, `plumber.py`, `_projected_interval`, `renderer.py`, `batch_extract.py`, `_collect_wall_faces`, `wall_band_h`, `DoorV2OpeningCheckTests`, `PathPrimitive`, `detect_doors`, `_find_openings`, `EntranceDoorTests`, `app.py`, `_collect_wall_faces`, `test_curve_arc_garden_doors.py`, `test_door_assembly.py`, `DoorV2OpeningCheckTests`, `_segments_min_distance`?**
  _High betweenness centrality (0.321) - this node is a cross-community bridge._
- **Why does `Candidate` connect `wall_band_h` to `TestGardenDoorSeals`, `Window Detection & Tests`, `Door Detection & Tests`, `EntranceDoorTests`, `Wall Cross-Validation`, `Debug Trace Collector`, `Room Detection Tests`, `Double-Arc Split Tests`, `Arc Cap-Trim Tests`, `_fit_circle_3pt`, `geometry.py`, `detect_windows`, `batch_extract.py`, `_collect_wall_faces`, `renderer.py`, `DoorV2OpeningCheckTests`, `_find_openings`, `EntranceDoorTests`, `test_door_assembly.py`, `DoorV2OpeningCheckTests`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `TextSpan` connect `hline` to `TestGardenDoorSeals`, `EntranceDoorTests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Debug Trace Collector`, `Arc Detection Primitives`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `Arc Cap-Trim Tests`, `arcs.py`, `_fit_circle_3pt`, `geometry.py`, `_projected_interval`, `renderer.py`, `batch_extract.py`, `_collect_wall_faces`, `vline`, `wall_band_h`, `DoorV2OpeningCheckTests`, `PathPrimitive`, `detect_doors`, `EntranceDoorTests`, `app.py`, `_collect_wall_faces`, `test_door_assembly.py`, `DoorV2OpeningCheckTests`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 84 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_SlidePanel`) actually correct?**
  _`PathPrimitive` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `Candidate` (e.g. with `_SlidePanel` and `PageRegionResult`) actually correct?**
  _`Candidate` has 39 INFERRED edges - model-reasoned connections that need verification._