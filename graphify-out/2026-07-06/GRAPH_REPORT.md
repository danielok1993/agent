# Graph Report - agent  (2026-07-06)

## Corpus Check
- 53 files · ~60,463 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 918 nodes · 2176 edges · 98 communities (42 shown, 56 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 94 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `74c8dfea`
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
- [[_COMMUNITY_Centerline Network Assembly|Centerline Network Assembly]]
- [[_COMMUNITY_Arc Spur-Pruning Tests|Arc Spur-Pruning Tests]]
- [[_COMMUNITY_Chained-Curve Swing Tests|Chained-Curve Swing Tests]]
- [[_COMMUNITY_Circle-Fit Geometry Tests|Circle-Fit Geometry Tests]]
- [[_COMMUNITY_Wall Network Query Tests|Wall Network Query Tests]]
- [[_COMMUNITY_Hu-Moment Template Tool|Hu-Moment Template Tool]]
- [[_COMMUNITY_Dashed-Line Detection|Dashed-Line Detection]]
- [[_COMMUNITY_Extraction Strategy (project.md)|Extraction Strategy (project.md)]]
- [[_COMMUNITY_Spur-Pruning Design Spec|Spur-Pruning Design Spec]]
- [[_COMMUNITY_Package Restructure Design|Package Restructure Design]]
- [[_COMMUNITY_README stub|README stub]]
- [[_COMMUNITY_Candidate|Candidate]]
- [[_COMMUNITY_plumber.py|plumber.py]]
- [[_COMMUNITY_Path|Path]]
- [[_COMMUNITY_Polyline-Arc Spur Pruning — Design|Polyline-Arc Spur Pruning — Design]]
- [[_COMMUNITY_extractor.py|extractor.py]]
- [[_COMMUNITY_Batch PDF Extraction Script Design|Batch PDF Extraction Script Design]]
- [[_COMMUNITY_renderer.py|renderer.py]]
- [[_COMMUNITY_PageData|PageData]]
- [[_COMMUNITY_Codebase Restructure Packages + heuristics.py Split|Codebase Restructure: Packages + heuristics.py Split]]
- [[_COMMUNITY_Window Detection — Tuning Guide|Window Detection — Tuning Guide]]
- [[_COMMUNITY_test_curve_arc_garden_doors.py|test_curve_arc_garden_doors.py]]
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

## God Nodes (most connected - your core abstractions)
1. `PathPrimitive` - 114 edges
2. `Candidate` - 79 edges
3. `detect_doors()` - 41 edges
4. `detect_windows()` - 41 edges
5. `DebugTraceCollector` - 38 edges
6. `detect_wall_network()` - 33 edges
7. `TextSpan` - 33 edges
8. `_cross_validate()` - 26 edges
9. `WallNetwork` - 26 edges
10. `_chain()` - 23 edges

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

## Communities (98 total, 56 thin omitted)

### Community 0 - "Pipeline Orchestration & Extraction"
Cohesion: 0.16
Nodes (19): generate_debug_viewer(), Generate a self-contained HTML debug viewer for door detection traces., Write a single-file HTML viewer embedding the render image and trace JSON., Document, render_page_png(), Entity, _candidate_to_dict(), collect_warnings() (+11 more)

### Community 1 - "Door Assembly & Heuristics Core"
Cohesion: 0.19
Nodes (25): _arc_corners(), _collect_door_swings(), _detect_curve_arc_double_partners(), _detect_polyline_arc_bboxes(), _estimate_arc_sweep_deg(), _is_arc_like(), BBox, Detect door-swing arcs approximated by connected short line segments.      Some (+17 more)

### Community 2 - "Window Detection & Tests"
Cohesion: 0.07
Nodes (35): detect_windows(), Detect windows as capped openings bridged by a parallel glazing band.      For e, _covers(), diagonal_window(), hline(), horizontal_window(), path(), Window detection tests.  Ground truth was established interactively on floor-pla (+27 more)

### Community 3 - "Door Detection & Tests"
Cohesion: 0.07
Nodes (29): _check_opening_clear(), Check if the door opening (bridge between arc endpoints) is free of crossing lin, detect_doors(), One wall centerline segment (pixel space, y-down)., WallSegment, TextSpan, DoorAssemblyTests, DoorEvidencePropagationTests (+21 more)

### Community 4 - "Pipeline Design Concepts (docs)"
Cohesion: 0.17
Nodes (10): Algorithm reference, Commands, Data model, Gemini / GCP auth, graphify, Module layout, Output layout, Pipeline architecture (+2 more)

### Community 5 - "Wall Cross-Validation"
Cohesion: 0.09
Nodes (28): _cross_validate(), Validate doors/windows against the wall-centerline network.      Doors keep the, BBox, One merged wall-face run with the evidence its members carried., Connected wall-centerline network (internal-only, never serialized)., Path indices of every face that contributed to a centerline., Length-weighted median stroke width of the paired stroked faces.          Anchor, True when any centerline corridor (dilated by thickness/2 + expand) hits bbox. (+20 more)

### Community 6 - "Double-Door Merge & Gemini Client"
Cohesion: 0.21
Nodes (11): _merge_double_door_assemblies(), Merge pairs of adjacent single-door assemblies into double-swing candidates., DoubleDoorTests, Tests for _merge_double_door_assemblies: adjacent single-door assembly merging., Arcs on the same side (both above leaf line) → merges into double_swing., Arcs on opposite sides → still merges since leaf-interval check is orientation-a, Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates, Leaf overlap of 10 px (> DOOR_DOUBLE_LEAF_OVERLAP_PX=5) → two separate candidate (+3 more)

### Community 7 - "Debug Trace Collector"
Cohesion: 0.10
Nodes (9): DebugTraceCollector, Record a polyline arc component evaluation. Returns component_id.          ``pre, Mark a previously-collected polyline component as rejected post-hoc., Record a linework leaf component evaluation. Returns component_id.          clea, Register a collected swing. Returns swing_id., Record the swing-anchored single-line leaf search outcome.          `result` is, Register a collected leaf. Returns leaf_id., Record a final candidate with its full confidence breakdown. (+1 more)

### Community 8 - "Arc Detection Primitives"
Cohesion: 0.12
Nodes (18): Record result of the _is_door_leaf check for a primitive., Pre-populate by_path_index with raw metadata for every PathPrimitive., Record result of the _is_arc_like check for a primitive., Record whether a line segment passed the polyline-arc length filter., _native_curve_chains(), Group native `c` (Bezier) primitives by endpoint adjacency.      PDF arcs are of, PathPrimitive, ChainedCurveSwingDetectionTests (+10 more)

### Community 9 - "Room Detection Tests"
Cohesion: 0.14
Nodes (18): door_candidate(), fill_ring(), hline(), path(), Room detection tests (detection/rooms.py).  Fixtures build wall bands as synthet, Rect room with a 45px doorway gap in the top wall (240..285)., Closed filled rectangle exploded into 4 chained `l` items (the     Vectorworks f, Room-interior ink (masks, tile grids, furniture) must not chop rooms;     classi (+10 more)

### Community 10 - "Wall Network Construction & Tests"
Cohesion: 0.09
Nodes (26): _collect_fill_rings(), _collect_wall_faces(), detect_wall_network(), _fill_key(), _is_dashed(), Chain consecutive same-fill `l` items (plus filled re/qu) into rings.      extra, True for a real dash pattern; PyMuPDF encodes solid as "" or "[] 0"., Return (stroked wall faces, filled-band centerlines). (+18 more)

### Community 11 - "Architectural PDF Domain (Sample Drawings)"
Cohesion: 0.11
Nodes (23): 5-1133-WD03 Proposed Lower Ground Floor (Construction Issue), New brick masonry cavity walls (U=0.12), Folding/sliding doors, Room labels (Bedroom 1/3, Hall, Patio), Drawing Ref 1133-WD03 (Scale 1:50@A3), Replacement windows W1-W6, CAD-originated Architectural PDF, Door (architectural element) (+15 more)

### Community 12 - "Double-Arc Split Tests"
Cohesion: 0.13
Nodes (17): Detect a 2-leaf simple chain that is two arc halves meeting at a hinge.      The, _split_double_arc(), _arc(), _double_arc(), Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like     the segs, Quarter-circle polyline as n_segs short straight lines., Tests for _split_double_arc.      Detects the 2-leaf simple chain that is two ar, Two 11-seg quarter arcs sharing a hinge (0, 0) with antiparallel         walk-di (+9 more)

### Community 13 - "Window Geometry Internals"
Cohesion: 0.10
Nodes (27): _interval_overlap(), _project_onto_axis(), _projected_interval(), Project segment (p1, p2) onto a unit axis and return (lo, hi) scalars., Scalar projection of p onto the unit axis (dx, dy) from origin., _area(), _band_interior_clutter(), _cap_orientation_frames() (+19 more)

### Community 14 - "Room Polygonization Internals"
Cohesion: 0.11
Nodes (23): _building_masses(), detect_rooms(), _door_plugs(), _free_space_components(), Room detection: rooms are the connected free-space components between walls.  Ea, Connected wall-solid masses that plausibly belong to a building.      Large mass, Thin barrier bands along the wall planes through a detected door.      The door, _accept_white_walls() (+15 more)

### Community 15 - "Arc Cap-Trim Tests"
Cohesion: 0.15
Nodes (11): Trim non-arc cap segments off a 2-leaf simple chain.      Some CAD draftsmen dra, _trim_chain_extension_caps(), Tests for _trim_chain_extension_caps.      Walks a 2-leaf simple chain (no junct, An 11-segment quarter arc has only small inter-seg angle deltas         (~8.2° e, The polyline_393 / linework_226 shape: an 11-seg quarter arc         followed by, A symmetric case: 11-seg arc with a 1-seg perpendicular cap at         each end., A component that still has a degree-3+ junction after spur         pruning is NO, A pure cycle has no leaves to walk from. Skipped. (+3 more)

### Community 16 - "Arc Cycle-Cap Pruning Tests"
Cohesion: 0.16
Nodes (13): _prune_arc_cycle_caps(), Remove a small closed-cycle cap attached at a single articulation point.      So, _chain(), PruneArcCycleCapsTests, Tests for _prune_arc_cycle_caps.      A 'closed-cycle cap' is a closed loop of s, An arc with no degree-3+ vertices has nothing to prune., 11-seg arc + closed 4-seg rectangle attached at arc end.         The junction is, The polyline_856 shape: 11-seg arc + 7-seg closed cap loop         attached at t (+5 more)

### Community 17 - "Wall Layer Hints & Snapping"
Cohesion: 0.15
Nodes (17): _point_to_segment_distance(), Minimum distance from point p to line segment ab., Minimum distance between two line segments., _segments_min_distance(), _layer_hint(), _layer_strong_prior(), _layer_tokens(), Return True if any keyword is an exact token in the layer name.      Token-split (+9 more)

### Community 18 - "Centerline Network Assembly"
Cohesion: 0.17
Nodes (19): _find_leaf_companion_lines(), Find lines forming the same thin-rect leaf as the anchored leaf line.      Door, _angle_diff_mod180(), _line_angle_deg(), _line_length(), _perpendicular_spacing(), Smaller angular distance between two directions, both already mod 180°., True when a wall FACE line runs unbroken through the bbox span.      A real wind (+11 more)

### Community 19 - "Arc Spur-Pruning Tests"
Cohesion: 0.18
Nodes (9): _prune_arc_spurs(), Remove short leaf-spurs (door stops, cap lines) from an arc component.      A cl, PruneArcSpursTests, A closed 4-segment loop has every vertex at degree 2 — no leaf         exists to, 11-segment arc whose far endpoint is a degree-3 junction because         two 1-s, linework_1318 shape: 11-segment arc whose far endpoint becomes a         degree-, A Y-junction with one short branch (2 segs) and one long branch         (5 segs,, A small Y-junction component where every walk fits in the spur         cap. Prun (+1 more)

### Community 20 - "Chained-Curve Swing Tests"
Cohesion: 0.05
Nodes (39): 10. Pipeline-level constraints to honor, 11. How to verify a change won't regress, 1. Pipeline shape, 2. The `_detect_polyline_arc_bboxes` micro-pipeline, 3.1 Single full-quarter Bezier (`curve_arc`), 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`), 3.3 Clean polyline arc (`polyline_arc`), 3.4 Polyline arc + Y-junction stop (spur-prunable) (+31 more)

### Community 21 - "Circle-Fit Geometry Tests"
Cohesion: 0.28
Nodes (6): _fit_circle_3pt(), Fit a circle through 3 points. Returns (cx, cy, radius) or None if     the point, FitCircle3PtTests, Three collinear points have no unique circumscribed circle., Trivial sanity check on the formula: 3 points on a circle of         radius 5 ce, Recover an offset center and radius from a different angular spread.

### Community 22 - "Wall Network Query Tests"
Cohesion: 0.17
Nodes (20): _door_fallback_candidate(), _find_threshold_line(), _nearest_pair_distance(), _pair_door_assemblies(), BBox, Find an entrance-door threshold/sill line parallel to the leaf long axis.      T, Parse an evidence bbox value defensively; return None on any invalid shape., _safe_bbox() (+12 more)

### Community 23 - "Hu-Moment Template Tool"
Cohesion: 0.47
Nodes (5): hu_log(), main(), rasterize_segments(), Extract Hu Moment template from confirmed door arcs in a pipeline output run., Draw line segments onto a normalized binary canvas.

### Community 24 - "Dashed-Line Detection"
Cohesion: 0.16
Nodes (19): _component_indices(), _dedupe_door_components(), Prefer the strongest door when two candidates use the same primitives., _bbox_area(), _bbox_center(), _bbox_expanded(), _bbox_union(), _bboxes_overlap() (+11 more)

### Community 34 - "Candidate"
Cohesion: 0.23
Nodes (10): detect_labels(), Detect architectural labels (e.g. D-01, W-03) near geometric candidates.      Re, run_heuristics(), Drop window candidates that materially sit on a detected door.      Door symbols, _resolve_door_window_conflicts(), detect_schedules(), Candidate, BBox (+2 more)

### Community 35 - "plumber.py"
Cohesion: 0.22
Nodes (18): build_plumber_counts(), build_pymupdf_counts(), compare_counts(), _delta_pct(), extract_plumber_document(), extract_plumber_page(), extract_tables(), _normalize_bbox_plumber() (+10 more)

### Community 36 - "Path"
Cohesion: 0.20
Nodes (16): cmd_extract(), cmd_inspect(), main(), parse_page_spec(), Parse '1,3-5' into 0-based page indices [0, 2, 3, 4]., build_extract_command(), find_pdfs(), main() (+8 more)

### Community 37 - "Polyline-Arc Spur Pruning — Design"
Cohesion: 0.12
Nodes (16): Algorithm, Behavior contract, Call site change, Closed-cycle appendages — out of scope, Constant location, Debug trace, Files changed, Fix (+8 more)

### Community 38 - "extractor.py"
Cohesion: 0.26
Nodes (15): classify_page(), _color_tuple(), extract_document(), extract_images(), extract_page(), extract_paths(), extract_text(), get_ocg_names() (+7 more)

### Community 39 - "Batch PDF Extraction Script Design"
Cohesion: 0.14
Nodes (13): Batch PDF Extraction Script Design, Environment Setup, Error Handling, File Organization, Implementation Notes, Interactive Prompts (Sequential), Output, Overview (+5 more)

### Community 40 - "renderer.py"
Cohesion: 0.33
Nodes (12): _draw_dashed_rect(), _draw_entity_box(), _draw_entity_polygon(), _draw_legend(), draw_overlay(), _load_font(), BBox, Room entities carry their closed polygon; draw its true shape instead     of the (+4 more)

### Community 41 - "PageData"
Cohesion: 0.30
Nodes (11): Client, build_user_message(), call_gemini(), _candidate_to_dict(), encode_image_inline(), init_client(), parse_gemini_response(), should_skip_gemini() (+3 more)

### Community 42 - "Codebase Restructure: Packages + heuristics.py Split"
Cohesion: 0.18
Nodes (10): Codebase Restructure: Packages + heuristics.py Split, Context, Decisions, detection/doors/ subpackage, Execution plan (incremental — run all 80 tests after each step), Goal, Out of scope (this pass), Public facade & test strategy (+2 more)

### Community 43 - "Window Detection — Tuning Guide"
Cohesion: 0.18
Nodes (10): 1. The signature (cap-anchored), 2. Pipeline shape, 3. Why both filters are needed (floor-plans.pdf), 4. The constants, 5.1 floor-plans.pdf (offline, walls on/off both give 4), 5.2 5-1133-WD03.pdf, 5. Reference data — current detection state (regression target), 6. Known limitations / not handled (+2 more)

### Community 44 - "test_curve_arc_garden_doors.py"
Cohesion: 0.27
Nodes (8): _curve(), CurveArcGardenDoorTests, _line(), _quarter_arc_bezier(), Garden-door detection for native single-Bezier (`curve_arc`) swings.  The polyli, Two arcs sharing an endpoint with continuous tangent (smooth         S-curve) mu, Build a cubic Bezier approximating the 90° quarter circle centered at     ``hing, The 5-1133-WD03.pdf door_0007 + door_0008 topology, simplified.          Two sta

## Ambiguous Edges - Review These
- `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` → `Schedule (door/window/finish table)`  [AMBIGUOUS]
  5-1133-WD03.pdf · relation: references
- `Door (architectural element)` → `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`  [AMBIGUOUS]
  floor-plans.pdf · relation: references

## Knowledge Gaps
- **137 isolated node(s):** `Project purpose`, `Algorithm reference`, `Commands`, `Module layout`, `Gemini / GCP auth` (+132 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **56 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `5-1133-WD03 Proposed Lower Ground Floor (Construction Issue)` and `Schedule (door/window/finish table)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `Door (architectural element)` and `floor-plans Proposed Ground & First Floor Plans (3 Penparcau Road)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `PathPrimitive` connect `Arc Detection Primitives` to `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `Debug Trace Collector`, `Room Detection Tests`, `Wall Network Construction & Tests`, `Double-Arc Split Tests`, `Window Geometry Internals`, `Room Polygonization Internals`, `Arc Cap-Trim Tests`, `Arc Cycle-Cap Pruning Tests`, `Wall Layer Hints & Snapping`, `Centerline Network Assembly`, `Arc Spur-Pruning Tests`, `Circle-Fit Geometry Tests`, `Wall Network Query Tests`, `Dashed-Line Detection`, `Candidate`, `extractor.py`, `test_curve_arc_garden_doors.py`?**
  _High betweenness centrality (0.266) - this node is a cross-community bridge._
- **Why does `Candidate` connect `Candidate` to `Pipeline Orchestration & Extraction`, `Door Assembly & Heuristics Core`, `Window Detection & Tests`, `Door Detection & Tests`, `Wall Cross-Validation`, `Double-Door Merge & Gemini Client`, `renderer.py`, `PageData`, `Room Detection Tests`, `Window Geometry Internals`, `Room Polygonization Internals`, `Wall Network Query Tests`, `Dashed-Line Detection`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `DebugTraceCollector` connect `Debug Trace Collector` to `Pipeline Orchestration & Extraction`, `Door Assembly & Heuristics Core`, `Candidate`, `Door Detection & Tests`, `Arc Detection Primitives`, `Wall Network Query Tests`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 38 inferred relationships involving `PathPrimitive` (e.g. with `DebugTraceCollector` and `_FillRing`) actually correct?**
  _`PathPrimitive` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Candidate` (e.g. with `TestDoorPenalties` and `TestEmptyNetwork`) actually correct?**
  _`Candidate` has 22 INFERRED edges - model-reasoned connections that need verification._