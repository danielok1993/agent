# Door Detection — Tuning Guide

Reference for fine-tuning the architectural door-detection pipeline in `heuristics.py`. Captures the algorithm's structure, every tunable constant, the failure-mode topologies it handles, known limitations, and the diagnostic methodology that was used to add the four most recent fixes (A–D below).

**Read first if you are about to change door detection.** Skipping the topology reference is the single most common cause of regression.

---

## 1. Pipeline shape

Door detection has three stages, in strict order:

1. **Swing collection** — `_collect_door_swings(paths)` finds arc-like geometry. Three swing sources:
   - `curve_arc` — single native `c` (Bezier) primitive passing `_is_arc_like` (square-ish bbox, ≥20 px).
   - `curve_arc_chain` — **2+ chained native `c` primitives** whose underlying circle (recovered by 3-point fit) has radius ∈ [20, 200].
   - `polyline_arc` — connected `l` segments forming a curve; detected by `_detect_polyline_arc_bboxes`. May emit ONE arc per BFS component, OR TWO arcs when `_split_double_arc` detects a garden-door pair (§3.7).
   After all three sources have produced their swings, `_detect_curve_arc_double_partners` runs as a post-pass to pair `curve_arc` swings that form a single-Bezier garden door (§3.8). This is the analogue of `_split_double_arc` for the case where each half is a standalone native Bezier rather than a BFS-joinable polyline chain.
2. **Leaf collection** — `_collect_door_leaves(paths)` finds:
   - `qu`/`re` (closed rectangle) leaves passing `_is_door_leaf`.
   - `linework_rect` leaves (4–8 line segs forming a closed thin rectangle).
   - `linework_rect_subgraph` (the same with a few attached spurs).
   - Anchored-line leaves (single `l` line near an arc endpoint, length ≈ swing radius).
3. **Pairing** — `_pair_door_assemblies(swings, leaves, …)` matches swings to leaves by:
   - `connection_dist ≤ DOOR_ASSEMBLY_CONNECT_TOL_PX` (15 px between swing pairing-points and leaf corners), AND
   - `radius_ratio = |leaf.length - swing.radius| / swing.radius ≤ DOOR_LEAF_RADIUS_RATIO_TOL` (0.20).

   After arc pairing (and the swing-anchored single-line pass), `_detect_sliding_doors` (`detection/doors/sliding.py`) runs INSIDE `_pair_door_assemblies`, before the fallback passes: sliding doors have no arc at all and are detected from oriented panel-rectangle patterns (§3.9). `_detect_folding_doors` (`detection/doors/folding.py`) runs immediately after it: folding/bifold doors are arc-less too, detected as hinge-connected runs of equal white leaf panels at shallow fold angles (§3.10). Both kinds of candidates carry their `assembly_type` ("sliding" / "folding"), and because their `component_path_indices` contain the panels' primitives, `_dedupe_door_components` retires the 0.35 leaf-fallback candidates the same rectangles used to produce.
4. **Cross-validate** — `_cross_validate(candidates, walls)` applies a `wall_context` penalty when the door has no overlapping wall.

After pairing, `pipeline.finalize_candidates` applies `OFFLINE_MIN_CONFIDENCE["door"] = 0.55` as the floor for being promoted to an `Entity`. That floor is unconditional — Gemini classifies drawing regions, not individual candidates, so it never votes a door up or down.

---

## 2. The `_detect_polyline_arc_bboxes` micro-pipeline

For each BFS-discovered connected component of short `l` segments, the order is **fixed and important**:

```
BFS(component)
  → _prune_arc_spurs
  → _prune_arc_cycle_caps
  → _split_double_arc            ◀── if matched: emit BOTH halves as separate arc_infos, skip _trim_chain_extension_caps
  → _trim_chain_extension_caps   ◀── otherwise
  → scoring
```

Each step shrinks (or splits) the component. Together they can transform a polluted arc (axis_like_fraction = 0.44, angle_bin_count = 8) into a clean arc that passes all checks, or split a 24-seg double-arc into two valid 12-seg arcs.

| Helper | Operates on | Action | Floor-guarded? | Iterates? |
|---|---|---|---|---|
| `_prune_arc_spurs` | any component | removes leaf-spurs of ≤4 segs ending at a degree-3+ junction | yes (≥`DOOR_POLYLINE_MIN_SEGMENTS`) | yes |
| `_prune_arc_cycle_caps` | components with ≥1 degree-3+ junction | removes closed cycles of ≤8 segs sharing one vertex with the rest | yes | yes |
| `_split_double_arc` | 2-leaf simple chains only | **emits TWO sub-components** when a single >45° break separates two arc-like halves (§3.7) | yes (each half ≥ `DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS`) | no — single pass |
| `_trim_chain_extension_caps` | 2-leaf simple chains only, NOT firing when `_split_double_arc` matched | trims runs past a sharp angle break (>45° per seg) | yes | no — single pass |

The order matters because each step can convert a complex topology into a simpler one for the next step. Spur pruning may collapse junctions to degree-2. Cycle pruning may convert junction-attached loops to dangling leaves, AND may strip a 2-seg cycle at a garden-door hinge that would otherwise prevent `_split_double_arc` from running. `_split_double_arc` and `_trim_chain_extension_caps` are mutually exclusive on the same break — split wins when both halves are arc-like; trim wins when one side is a short axis-aligned cap.

---

## 3. Topology reference (the failure-mode taxonomy)

Door swings appear in CAD-extracted PDFs in **six distinct topologies**. Knowing which one is in front of you is the only way to debug intelligently.

### 3.1 Single full-quarter Bezier (`curve_arc`)
```
   ╮
    ╲___
       hinge
```
One `c` path. Bbox aspect within [0.65, 1.45] (a full axis-anchored quarter arc is square; partial sweeps down to ~77.5° skew it to 0.80/1.24), radius = max(w,h). Passes `_is_arc_like` directly.

### 3.2 Chained Beziers — full or partial swing (`curve_arc_chain`)
```
   chain of N short cubic Beziers, each ≤8 px wide
   • Each individually fails _is_arc_like (size & aspect).
   • Combined chain endpoints + 3-point circle fit recovers the TRUE radius.
   • For PARTIAL arcs (e.g., 30° drawn), combined bbox is much smaller than radius.
     Pairing MUST use fitted radius, not bbox.
```
Detected by `_native_curve_chains` + `_fit_circle_3pt`. **Without this, partial-arc doors with the leaf nearby never pair (`radius_ratio` > 1).**

### 3.3 Clean polyline arc (`polyline_arc`)
```
   11 short `l` segs forming a smooth curve from leaf to leaf.
   Two degree-1 endpoints, no junctions, smooth angle progression.
```
All four reference doors on 5-1133-WD03.pdf and three on floor-plans.pdf are this shape.

### 3.4 Polyline arc + Y-junction stop (spur-prunable)
```
              ▲   ◀── two short branches forming a Y-junction
   ╮         ╱╲
    ╲────── ●  ●  ◀── junction (degree 3+)
              ▼
```
Spur pruning walks each ≤4-seg leaf-tail through degree-2 verts to the junction and trims them.

### 3.5 Polyline arc + closed-cycle stop (cycle-prunable)
```
   ╮          ┌──┐
    ╲────── ● │  │  ◀── closed mini-rectangle (cycle) attached at one vertex
              └──┘
```
Cycle pruning walks from each junction along each incident edge; a walk that returns to the same junction within ≤8 segs is the cycle. **Spur pruning cannot fire** here because no degree-1 leaf exists inside the cycle.

### 3.6 Polyline arc + linear cap extension (chain-trim-able)
```
   ╮
    ╲────── ●─────●  ◀── short axis-aligned cap continuing past the arc's
                          natural endpoint (no junction)
```
Topologically a simple 2-leaf chain. Spur pruning can't fire (no junction); cycle pruning can't fire (no cycle). Detected only by angle-monotonicity: the cap segments break the arc's smooth angle progression by ≥45° per seg.

### 3.7 Double arc / garden-door pair (split-emit, then merge)
```
       leaf_L                            leaf_R
        │                                   │
        ╲╱── arc_L ── hinge ── arc_R ───╱╲
        │                                   │
   outer_left                          outer_right
```
Two quarter-arcs SHARE a single hinge endpoint with **antiparallel walk-direction tangents** (a ~180° break at the hinge when walked leaf-to-leaf). BFS joins them into one 2-leaf simple chain. Without the new detector, `_trim_chain_extension_caps` mistreats one half as a cap past the break and discards 12 of the 24 segments.

The new helper `_split_double_arc` (heuristics.py, runs BEFORE `_trim_chain_extension_caps` but AFTER spur + cycle pruning) detects this pattern by requiring:
- 2-leaf simple chain (no junctions after cycle prune).
- **Exactly one** >45° break in walk-direction.
- Both halves ≥ `DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS` (4).
- Both halves have ≥ `DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS` (3) distinct 15° angle bins — rules out a §3.6 long axis-aligned cap that happens to be ≥4 segs.

When matched, the BFS component is **split into two arc_infos**. Each half becomes its own `_DoorSwing` carrying `double_arc_partner_paths` (the OTHER half's path indices). Each pairs with its own anchored leaf line; `_merge_double_door_assemblies` then merges the two single-door candidates into one `assembly_type="double_swing"`, `swing_layout="garden"` entity with bbox = union of both halves.

**Opening-check special-case:** for a garden-door half, the per-half bridge runs from the outer endpoint to the hinge — that's *internal* swing geometry, not the actual doorway opening. The per-half check is skipped (`opening_check="deferred_to_merge"`, no boost or penalty applied). The half base confidence stays at 0.60 (DOOR_ASSEMBLY_LINE_LEAF_BASE), the merge bonus (+0.05) lifts the composite to 0.65 — just over the 0.55 offline floor.

**Garden door 2 wrinkle:** sometimes the hinge has a tiny 2-seg closed cycle (two near-overlapping vertical segs the CAD tool emitted as both halves' final segs sharing both endpoints via snap-key collapse). That registers as a degree-3+ junction and makes `_split_double_arc` fail the "no junctions" check. To handle this, spur + cycle pruning runs first; once the 2-cycle is removed, the chain becomes simple and the split detects.

**Not handled here (would need extension):**
- Three-arc chains (e.g., a triple door with two hinges in the middle) — requires multi-break splitting.
- Garden doors with junctions on EITHER half (e.g., a Y-junction on one swing's outer end) — current detector bails on junctions.

### 3.8 Garden door drawn as two single Beziers (curve_arc partner pass)

```
   leaf_A ───── free_A_corner ◀── leaf attaches at the arc's outer endpoint
                       │
                       │ arc_A  (single `c` Bezier, square bbox)
                       │
                       ●  ◀── shared endpoint (both free ends meet here when closed)
                       │
                       │ arc_B  (single `c` Bezier, square bbox)
                       │
   leaf_B ───── free_B_corner
```

Same architectural pattern as §3.7, but each half is drawn as ONE native cubic Bezier (each individually passes `_is_arc_like` with a ~square bbox and size ≥ 20 px). The two halves are emitted as independent `curve_arc` swings by `_collect_door_swings`; the polyline pipeline never sees them, so `_split_double_arc` can't fire.

`_detect_curve_arc_double_partners` (heuristics.py, runs at the end of `_collect_door_swings` after all three sources are collected) closes the gap. It looks for pairs of `curve_arc` swings — each single-Bezier, each carrying `arc_endpoints = [pts[0], pts[3]]` — that:
- have matching radii within `DOOR_LEAF_RADIUS_RATIO_TOL` (0.20),
- share one endpoint within `DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX` (3 px),
- exhibit a >`DOOR_POLYLINE_CHAIN_DELTA_DEG` (45°) **walk-direction tangent break** across the shared endpoint.

When matched, both swings get `double_arc_partner_paths` stamped on them (cross-pointing — each carries the other's `component_path_indices`). Everything downstream then behaves identically to a polyline-arc split: the per-half `opening_check` becomes `"deferred_to_merge"` so the bridge-crossing-the-other-half issue doesn't penalise either confidence, and `_merge_double_door_assemblies`' garden-pass match (§3.7 logic) consumes both candidates and emits one `assembly_type="double_swing"`, `swing_layout="garden"` composite.

**Walk-direction tangent break — the orientation pitfall.** The 45° break check must compare arc A's incoming-walk-direction tangent (the tangent walked *into* the shared endpoint when walked from non-shared → shared) with arc B's outgoing-walk-direction tangent (walked *out of* the shared endpoint, shared → non-shared). For a garden-door pair this gives ~180° (antiparallel — the canonical mirror). For a smooth S-curve continuation it gives ~0° (parallel — correctly rejected).

If you instead compared both arcs' *outgoing-from-shared* tangents (or equivalently both incoming), one of them gets flipped and the pair reads as ~0° / parallel — a true garden door would be missed. The Bezier formulas for the four cases (shared endpoint at `pts[0]` vs `pts[3]`; into vs out) are documented in the helper.

**Not handled here (would need extension):**
- `curve_arc_chain` garden halves (each half drawn as a multi-Bezier chain) — unobserved in the test corpus; would need to expose the outer Beziers of each chain so tangents can be computed at the shared endpoint.
- More than two `curve_arc` swings meeting at one point (a 3-leaf hub) — the current pairing is one-to-one; the first match wins.

### 3.9 Sliding doors — no arc (`detection/doors/sliding.py`)

Sliding doors have **no swing arc**; the symbol is thin panel rectangles lying in the wall plane. Panels are collected as ORIENTED rectangles (corner fit via `_fit_oriented_rect`, so all sub-patterns are rotation-independent) from four representations, merged when coincident (`DOOR_SLIDE_PANEL_MERGE_TOL_PX`): `re`/`qu` primitives, closed 4–8-seg white-filled `l` rings — the Vectorworks joinery signature draws every panel twice (white fill ring + stroked `qu` outline) — and closed 4–8-seg **stroked** (fill-less) `l` rings, the flattened-PDF style (Microsoft Print to PDF strips fills), snapped at `DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX` (1.0 px, CAD precision — the white-ring 3 px buckets chain a stroked ring into adjacent wall linework and reject it as an oversized component). Stroked-only rings feed ONLY the parked_leaf pattern below; they never enter the pair pool. Panel gates: length ∈ [`DOOR_MIN_SIZE_PX`, `DOOR_MAX_SIZE_PX`], aspect ≥ `DOOR_LEAF_ASPECT_MIN`, thickness ∈ [3, 20] px (below 3 px is a shower screen / glazing strip — measured 2.0–2.5 on 5-1133).

Two sub-patterns calibrated on 5-1133-WD03 (GD labels) plus one on floor-plans.pdf:

```
leaf_pair (GD4, GD5):        pocket_leaf (GD9):
  ════════════╗                wall ═══╗ ╔═══ wall faces (both sides)
  ╔═══════════╪═══╗                    ║█║   ◀── panel pocketed 35-90%
  ╚═══════════╪═══╝                    ║█║
  ════════════╝                        ╚█╝
  two equal parallel panels             █    ◀── protruding 8-65% into
  IN THE SAME BAND, partially                    CLEAR space (the doorway)
  overlapping along the axis
```

- **leaf_pair**: axes parallel ≤ `DOOR_SLIDE_AXIS_TOL_DEG` (folded bifold leaves measure 16–20° apart → excluded), lengths equal within `DOOR_SLIDE_LENGTH_RATIO_TOL`, lateral offset ≤ `DOOR_SLIDE_LATERAL_FACTOR` × avg thickness (real pairs measure ~0.02×; laterally-stacked wall plies ~1.0×; an open hinged leaf against a wall face ~3×), axial overlap ∈ [0.20, 0.90] (duplicated fixture symbols measure 1.0; the WALL TYPE 4 ply stack 0.94; abutting collinear wall rects ~0).
- **pocket_leaf**: a WHITE panel flanked on BOTH sides by wall-face lines (gap ∈ [0.5, 12] px beyond the panel edge, each face ≥ 0.4 × panel length, each side covering ≥ 0.25) over 35–90 % of its length, protruding 8–65 % at one end, where the protrusion zone contains ≤ `DOOR_SLIDE_ZONE_MAX_CROSSERS` crossing lines (a wall strip "protrudes" into hatch — ≥3 crossers; a doorway is clear, jamb caps ≤2) AND the panel bbox overlaps no collected swing (an open hinged leaf near its arc is the swing's business). White-ring representation is REQUIRED for this weaker single-panel evidence tier (open hinged leaves on 5-1133 are stroked `qu` only).
- **parked_leaf** (floor-plans door_0011, added 2026-07-21): a single panel (ANY representation — this is the fill-less tier, where band + jamb + slide-law evidence replaces the white signature) parked flush along one face of a wall band that ENDS at a jamb, with a clear opening of ~one panel length beyond the jamb:

  ```
      │ ║        │ ║◀── band face + partner face (band th 2-20 px)
   far jamb ──▶  │ ║
      ─┐ ┌─      │ ║ █ ◀── panel hugging the face: gap ≤ 6 px,
       opening   │ ║ █     face runs behind ≥ 0.80 of the panel
       ≈ panel   │ ║ █
       length    │ ║ █     band END aligned with the panel end
                 └─╨─┘◀──  within ±8 px (measured 3 px overhang)
  ```

  Gates in order: hugging face (gap ∈ [`DOOR_SLIDE_FLANK_GAP_MIN_PX`, `DOOR_SLIDE_PARK_GAP_MAX_PX`], cover ≥ `DOOR_SLIDE_PARK_FACE_COVER_MIN`); band partner face at depth ∈ [2, 20] px running with it; both faces end together at a jamb within `DOOR_SLIDE_PARK_JAMB_TOL_PX` of one panel end while the face runs past the other end; the **slide law** — the nearest linework endpoint in the band corridor beyond the jamb (the far jamb) sits at `|span − panel length|/length ≤ `DOOR_SLIDE_PARK_SPAN_RATIO_TOL` (measured 0.000: panel 51.25 px, opening 51.25 px); corridor clear of >2 crossers; no swing overlap. Runs after leaf_pair/pocket_leaf on unconsumed panels. The emitted bbox spans panel ∪ opening corridor so the room stage can seal the doorway (the parked panel itself lies laterally OFF the opening).

Base confidence `DOOR_SLIDE_ASSEMBLY_BASE` 0.65 (rect-leaf tier) + the usual label/layer boosts; `opening_check="not_applicable"`.

**Room-stage interplay (rooms.py):** sliding candidates are exempt from the open-leaf white-ring veto — a sliding panel lies in the wall plane by construction (drawn closed across the opening, or parked inside the pocket), and withholding its rings deletes the very partition `_bridge_white_runs` seals the doorway with. Measured on 5-1133 GD5: both panels are drawn PARKED in the pocket, so the door bbox covers only half the doorway; with the rings withheld the two adjacent rooms merged.

**Not handled (would need extension):** single-leaf sliders drawn closed as a bare line across the opening (no rectangle), panels without any of the four rect representations. Folding/bifold doors (leaves at alternating ±10–20° angles) were out of scope here until 2026-07-16 — they are now handled by the dedicated folding detector (§3.10).

### 3.10 Folding/bifold doors — no arc (`detection/doors/folding.py`)

Folding doors have no swing arc either; the symbol is a run of equal thin leaf panels **hinged end-to-end at a shallow fold angle** (adjacent leaf axes 10–21° apart on the corpus — exactly the geometry §3.9's `leaf_pair` excludes with its 6° parallelism gate, so the two detectors never compete for the same panel pair). Panels reuse `_collect_slide_panels` (same gates: length ∈ [`DOOR_MIN_SIZE_PX`, `DOOR_MAX_SIZE_PX`], aspect ≥ `DOOR_LEAF_ASPECT_MIN`, thickness 3–20 px), with one wrinkle: hinged leaves share ring VERTICES, so `_white_ring_rects`' closed-loop reconstruction rejects their fill rings (the hinge vertex has degree 4 and the leaves' rings BFS-merge into one non-loop component) and the leaves arrive as stroked-`qu` panels only. `_absorb_hinged_white_rings` recovers the signature: a white `l` segment whose both endpoints land on a panel's fitted corners is that panel's fill-ring edge — its path index is absorbed (so fallback dedupe sees both representations) and the panel turns white once ≥4 edges match. **Every folding leaf must be white** (the weaker no-arc evidence tier requires the Vectorworks joinery signature, mirroring pocket_leaf).

Hinge edges (`_fold_edges`): equal lengths (`DOOR_FOLD_LENGTH_RATIO_TOL`), corner-to-corner contact ≤ `DOOR_FOLD_HINGE_TOL_PX`, axis delta ∈ [`DOOR_FOLD_ANGLE_MIN_DEG`, `DOOR_FOLD_ANGLE_MAX_DEG`]. Connected components are fold groups; two emission patterns (all three reference doors on 5-1133-WD03):

```
chain (GD2 trifold, drawn nearly closed):     stack_pair (kitchen CL doors, W9 folding wall):
                                                ║ V           V ║
   ────────────╲ ___________                    ║╱ ╲   open   ╱ ╲║
   ╲____________╱                               ╱   ╲ ──────>╱   ╲
   3+ leaves zigzag-hinged across               two 2-leaf V-stacks parked at opposite
   the opening (deltas 10.1/20.6°)              jambs; outer span ≈ Σ leaf lengths
```

- **chain**: one group of ≥ `DOOR_FOLD_MIN_CHAIN_LEAVES` (3) leaves → one folding door. A lone 2-leaf V is NEVER emitted (too weak without a partner stack — guards against chance joinery corner contacts).
- **stack_pair**: two 2-leaf groups paired greedily (nearest first) under three gates. The physical one is the **span law**: when the door closes the leaves unfold to cover the opening, so the outer corner span between the stacks along the opening axis must equal Σ leaf lengths within `DOOR_FOLD_STACK_SPAN_RATIO_TOL` (measured 0.015 on the kitchen pair, 0.001 on W9). Plus mirror symmetry (the stacks fold off the SAME wall plane: mean leaf axes mirror about the opening axis within `DOOR_FOLD_STACK_MIRROR_TOL_DEG`; measured ≤0.3°) and compactness (each stack projects ≤ `DOOR_FOLD_STACK_PERP_EXTENT_MAX` × leaf length perpendicular to the opening axis; measured 0.99–1.00×).
- **open_v** (floor-plans paths 1739–1742, added 2026-07-21): a LONE bifold drawn **half-open** as a wide V — the fill-less drawing style, where each leaf is just two near-parallel oblique stroked `l` lines a hair apart (no white ring, no `qu`):

  ```
   ═══╗ ◀── jamb: wall-face lines END at the anchored tip
      ╲╲
       ╲╲  fold angle 40-85° (measured 71.2°;
       ╱╱  capped BELOW 90° so orthogonal
      ╱╱   corner joinery can never match)
     ┄╱ ◀── free tip floats in the opening
      │
   ═══╡ ◀── far jamb: nearest corridor endpoint; span law
  ```

  Leaves come from `_double_line_leaves`: pairs of OBLIQUE lines (≥ `DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG` off both axes — a half-open V off a straight wall is never axis-aligned, and this keeps the page's bulk linework out of the O(n²) search), near-parallel (≤ 6°), lengths within `DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN` (the inner edge is foreshortened at the hinge miter — measured 0.915), separation ∈ [0.8, 4.0] px (45° hatch at the corpus' tightest 5.7 px pitch = 4.03 sep, just outside), axial overlap ≥ 0.6. V gates: equal leaf lengths (`DOOR_FOLD_LENGTH_RATIO_TOL`), hinge corner contact (`DOOR_FOLD_HINGE_TOL_PX`), fold angle ∈ [`DOOR_FOLD_OPEN_ANGLE_MIN_DEG`, `DOOR_FOLD_OPEN_ANGLE_MAX_DEG`] (40–85° — disjoint from chain/stack_pair's 8–30°, so the patterns never compete), tips apart ≥ 0.5 × leaf length (tips together = drawn closed = chain territory), leaf axes MIRROR about the tip-to-tip axis (`DOOR_FOLD_STACK_MIRROR_TOL_DEG`; measured 4.3°). The evidence that replaces the white signature: ≥1 tip anchored on wall-line jamb ENDS running along the tip axis (length ≥ 15 px, endpoint within 6 px of the tip, body away from the opening — at an L-corner of counter joinery the walls run along the strips, never along the diagonal tip axis, so this is the L-corner killer alongside the <90° ceiling), the **span law** — the nearest corridor endpoint beyond the far tip (leaf end caps on leaf corners excluded) sits at `|span − Σ leaf lengths|/Σ ≤ `DOOR_FOLD_STACK_SPAN_RATIO_TOL` (measured 0.159: opening 55.85 px vs Σ 48.05) — and a clear corridor (≤2 crossers; the V's own end cap measures 1). Both tips anchored ⇒ span = tip span (a V drawn closed across the opening). The bbox spans the V ∪ the opening corridor down to the far jamb.

Base confidence `DOOR_FOLD_ASSEMBLY_BASE` 0.65 + the usual label/layer boosts; `opening_check="not_applicable"`. The stack_pair bbox spans the whole opening (both stacks + the open span between them) — the room stage seals it through wall-plane plugs like any swing door; folding candidates get **no** sliding-style room-stage exemption (parked stacks protrude into room space like open leaves).

**Not handled (would need extension):** stacks with 3+ leaves per side (a 6-leaf door parked 3+3 — pairing requires exactly 2+2), a single bifold parked FOLDED at one jamb only (a closed lone V — open_v needs the half-open geometry to measure the mirror/span laws), stroked-only leaves without the white fill signature in the chain/stack_pair patterns (open_v is the only stroked-leaf tier), an open V with an axis-aligned leaf (a bifold off a 45° diagonal wall could fold one leaf onto the horizontal/vertical — the oblique gate would drop it).

---

## 4. The constants — every tunable in one table

All in `heuristics.py`. Grouped by stage. Defaults are the *current* values after the four fixes; the "rationale" column tells you *why* it has that value and what regresses if you change it.

### 4.1 Arc shape

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_BBOX_ASPECT_MIN` | 0.65 | Widened from 0.85 (2026-08-13): a real swing is often swept <90° or anchored off-axis — a 77.5°-sweep arc measures bbox aspect 0.804 (mirror 1.244), and the old square-only gate cost s06 8 of its 10 swings. Bounds now equal the polyline path's aspect gate; both sites share the constants. |
| `DOOR_BBOX_ASPECT_MAX` | 1.45 | Don't raise: the nearest repeated non-door family at door scale — elliptical fixture/appliance quarter arcs — measures aspect 1.494 (s12) and 1.50–1.76 (s02, ~120 arcs), just past the bound. Pinned in `tests/test_bezier_arc_aspect.py`. |
| `DOOR_MIN_SIZE_PX` | 20.0 | Smallest door radius observed across both PDFs is 40 px; 20 gives headroom for tiny utility doors. |
| `DOOR_MAX_SIZE_PX` | 200.0 | Largest detected door is ~125 px; 200 caps decorative arcs / circle floor patterns. |

### 4.2 Polyline-arc detector

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_POLYLINE_MIN_SEGMENTS` | 4 | Below this is ambient noise. Also the floor used by all three pruning helpers. |
| `DOOR_POLYLINE_MAX_SEGMENTS` | 24 | Largest clean arcs have 11 segs; 24 admits modestly over-tessellated arcs while excluding wall networks (which run into hundreds). |
| `DOOR_POLYLINE_MAX_SEG_PX` | 18.0 | **Critical filter** — segments longer than this are excluded from the polyline-arc adjacency graph. This is what keeps long leaf lines and threshold lines from polluting arc components. |
| `DOOR_POLYLINE_ENDPOINT_TOL` | 2.0 | Snap-key divisor for endpoint grouping. The integer snap_key is `(round(x/2.0), round(y/2.0))`. Vertices < 2 px apart in EACH coord may collapse (and in test fixtures often do — see §7). |
| `DOOR_POLYLINE_MAX_ANGLE_BINS` | 7 | The number of distinct 15° angle bins. A clean quarter arc with smooth angle progression fills 6–7. Door-stop appendages bump this past 7. |
| `axis_like_fraction` cutoff | 0.35 (hardcoded at heuristics.py:506) | Fraction of segments within 8° of an axis. A clean curve: 0.18–0.27. Polluted by cap: 0.40+. Don't relax. |

### 4.3 Spur pruning (heuristics.py:402)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_POLYLINE_SPUR_MAX_SEGMENTS` | 4 | The Y-junction door-stop on floor-plans (linework_1318) has 2 branches of 2 segs each. 4 catches stops of up to 4 segs while leaving real arc segments alone. |

### 4.4 Cycle pruning (heuristics.py)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_POLYLINE_CYCLE_MAX_SEGMENTS` | 8 | polyline_856's cap loop is 7 segs. 8 gives small margin while excluding larger decorative loops. |

### 4.5 Chain-extension cap trim

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_POLYLINE_CHAIN_DELTA_DEG` | 45.0 | Max per-segment direction-angle delta for "arc-like continuity". A 4-seg quarter arc has 22.5°/seg; 45° gives headroom for jitter. A perpendicular cap (a horizontal cap meeting a vertical arc tangent) is a 90° break — well above 45°. **Lowering risks splitting real arcs at noise spikes.** Also reused by `_split_double_arc` (§3.7) as the threshold for "the one big break at the hinge". |

### 4.5b Double-arc / garden-door split (§3.7)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_DOUBLE_ARC_MIN_HALF_SEGMENTS` | 4 | Each half must be a viable arc on its own; matches `DOOR_POLYLINE_MIN_SEGMENTS` so each split half can clear the downstream `segment_count` check. A 3+11 split would fail anyway on the 3-seg side. |
| `DOOR_DOUBLE_ARC_MIN_HALF_ANGLE_BINS` | 3 | Each half must show curvature (≥3 distinct 15° bins). Rules out the failure mode where one "half" is actually an axis-aligned cap ≥4 segs long — that side has just 1 angle bin and the existing chain trimmer is the right tool for it. |
| `DOOR_CURVE_ARC_SHARED_HINGE_TOL_PX` | 3.0 | Used by the §3.8 curve_arc partner pass — max distance between one endpoint of each arc to count as "the same hinge". Tighter than the 15 px arc-to-leaf pairing tolerance because the inputs are CAD-precise Bezier endpoints (not loose snap matches). Raising risks falsely partnering unrelated nearby arcs. |

### 4.6 Chained native curves (curve_arc_chain)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX` | 1.0 | Endpoint snap tolerance for chaining `c` primitives. PDF curves have machine-precise endpoints, so 1 px is generous. |
| `DOOR_CURVE_CHAIN_MIN_CURVES` | 2 | Minimum curves in a chain to qualify for chained-arc emission. Singleton `c` primitives still go through the existing `_is_arc_like` path. |

### 4.7 Leaf detection & pairing

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_LEAF_ASPECT_MIN` | 4.0 | Leaf rectangles are long & thin. Below 4:1 is furniture. |
| `DOOR_LEAF_RADIUS_RATIO_TOL` | 0.20 | `|leaf.length − swing.radius| / swing.radius`. **For chained partial arcs, the swing.radius MUST be the fitted-circle radius**, not the combined-bbox radius. Without that, ratio > 1 and pairing always fails. |
| `DOOR_LEAF_LINE_LENGTH_TOL` | 0.20 | Same shape as above but for single-line "anchored" leaves. |
| `DOOR_LEAF_LINE_AXIS_TOL_DEG` | 8.0 | Anchored leaf lines must run within 8° of 0° or 90°. |
| `DOOR_LEAF_LINE_ENDPOINT_TOL_PX` | 5.0 | Snap distance from leaf line's endpoint to arc's natural endpoint. |
| `DOOR_LEAF_COMPANION_PERP_PX` | 5.0 | Max perpendicular distance between a "leaf line" and a companion line forming the panel's other edge. |
| `DOOR_LEAF_COMPANION_OVERLAP` | 0.50 | Min projected overlap fraction for a companion line. |
| `DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX` | 3.0 | Snap tolerance for the linework-leaf clean-loop / subgraph detector. |
| `DOOR_LINEWORK_LEAF_MIN_SEGMENTS` | 4 | A closed leaf rectangle is exactly 4 segs. |
| `DOOR_LINEWORK_LEAF_MAX_SEGMENTS` | 8 | Caps split-side rectangles (a rectangle with each side drawn as 2 short lines = 8 segs). |
| `DOOR_LINEWORK_LEAF_COMPONENT_MAX_SEGMENTS` | 14 | The subgraph fallback ceiling — a leaf rectangle with up to ~10 attached spurs. |
| `DOOR_ASSEMBLY_CONNECT_TOL_PX` | 15.0 | Max distance from swing pairing-points to leaf corners for pairing. |
| `DOOR_SWING_LINE_DIST_PX` | 15.0 | Used in arc-vs-polyline overlap dedup; not the same as the pairing tolerance despite being numerically equal. |

### 4.8 Labels and layers

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_LABEL_PATTERN` | `(?i)^[A-Z]?[FD]-?\d{1,3}[A-Z]?$` | Matches `D01`, `GD6`, `F-12A`, etc. **Project-specific schedule naming convention.** If a project uses `DR-001`, regex must be widened. |
| `DOOR_LABEL_SEARCH_RADIUS_PX` | 100.0 | Search radius around the assembly bbox. Larger = more spurious label matches. |
| `DOOR_LAYER_KEYWORDS` | `["door", "a-door"]` | Exact-token match in the layer name (`detection/layers.py::_layer_tokens`), singular OR plural — a token of ≥ 4 chars ending in `s` also contributes its stem, because CAD conventions pluralise the class name (s03/s17 `A325G_INT_DOORS`, s04 `RR_New Doors and Windows`; every door/window/wall layer on the six layered corpus sheets is plural, and the singular-only match never fired on any of them until 2026-08-25). Still no substring match: `doorstops` misses. 14 of the 20 corpus sheets have no OCG layers at all, so the hint is a no-op there. |

### 4.9 Confidence boosts and floor

These hardcoded in `_pair_door_assemblies` (heuristics.py:1833+, 1730+):

| Element | Value | Notes |
|---|---|---|
| Single (qu/re leaf) base | 0.65 | The strongest leaf evidence — a closed rectangle. |
| `single_line_leaf` base | 0.60 (`DOOR_ASSEMBLY_LINE_LEAF_BASE`) | Weaker leaf evidence — one anchored line. |
| Label boost | +0.20 | When a `DOOR_LABEL_PATTERN`-matching text span is within `DOOR_LABEL_SEARCH_RADIUS_PX`. |
| Layer hint boost | +0.40 | When the layer name carries a `DOOR_LAYER_KEYWORDS` token (singular or plural). Fires on s03/s17 (`A325G_INT_DOORS`); measured effect of enabling plurals: s17 doors 0033/0030/0001 — real swings crossed by orange `_to be removed` linework — rose 0.53 → 0.83 and were emitted; no other corpus entity changed. |
| `DOOR_THRESHOLD_CONFIDENCE_BOOST` | 0.10 | When an entrance threshold line is detected across the opening. |
| `DOOR_V2_OPENING_CLEAR_BOOST` | 0.07 | When the bridge between the arc's two endpoints is unobstructed. |
| `DOOR_V2_OPENING_OBSTRUCTED_PENALTY` | 0.12 | When another line comes within `DOOR_V2_BRIDGE_BUFFER_PX` (3px) of the bridge somewhere in its INTERIOR (5–95% of its length). WHERE along the bridge a line comes close is the discriminator, never where the line's midpoint projects: the jamb wall the arc lands on touches the bridge at its end and runs away (closest approach −0.02..0.04 of the bridge on s02/s03's real doors), while a sill/glazing line drawn through the swing cuts the interior (s02's real interior crossers at 0.20–0.32; the bath-fixture `single_line_leaf` FP door_0012 at 0.17–0.83). The pre-2026-08-25 midpoint projection flagged s03 door_0006's 146px jamb wall (diagonal chord × long wall put its midpoint at 0.82) and dropped the door to 0.53, under the floor; it also passed a long line crossing the opening as clear when its midpoint projected off the bridge's end. `_line_nears_bridge_interior` solves the buffer slab analytically. |
| `DOOR_ARC_FALLBACK_MAX` | 0.45 | Cap for arc-only fallback so it stays below the 0.55 offline floor. |
| `DOOR_FALLBACK_CONFIDENCE` | 0.35 | Base for leaf-fallback (leaf without paired arc). Also below the floor. |
| Confidence cap | 0.95 | Hardcoded ceiling. |

### 4.9b Sliding-door detection (§3.9, `detection/doors/constants.py`)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_SLIDE_PANEL_MIN_THICKNESS_PX` | 3.0 | Thinner rects are shower screens / glazing strips (measured 2.0–2.5 on 5-1133). |
| `DOOR_SLIDE_PANEL_MAX_THICKNESS_PX` | 20.0 | Panels measure ~6 px at 1:50; headroom for larger scales. |
| `DOOR_SLIDE_RECT_PARALLEL_TOL_DEG` | 8.0 | Opposite-side parallelism for the oriented-rect fit; also the collinear-vertex merge threshold (split sides collapse). |
| `DOOR_SLIDE_RECT_PERP_TOL_DEG` | 12.0 | Adjacent-side perpendicularity for the fit. |
| `DOOR_SLIDE_PANEL_MERGE_TOL_PX` | 2.0 | White ring + stroked `qu` of the SAME panel merge into one panel (union of path indices — this is what lets `_dedupe_door_components` retire fallbacks on either representation). |
| `DOOR_SLIDE_AXIS_TOL_DEG` | 6.0 | Pair/flank parallelism. Bifold (folded) leaves measure 16–20° apart — do not raise past ~12. |
| `DOOR_SLIDE_LENGTH_RATIO_TOL` | 0.15 | Pair panels are equal leaves of one door (measured 0.00). |
| `DOOR_SLIDE_LATERAL_FACTOR` | 0.75 | × avg thickness. Real pairs ~0.02×; wall plies ~1.0× (2.7 px margin on WALL TYPE 4); GD7 open leaf vs wall ~3×. |
| `DOOR_SLIDE_OVERLAP_MIN_FRAC` | 0.20 | Abutting collinear wall rects ≈ 0. Measured doors: 0.50, 0.73. |
| `DOOR_SLIDE_OVERLAP_MAX_FRAC` | 0.90 | Duplicated symbols = 1.0; wall ply stack = 0.94. |
| `DOOR_SLIDE_FLANK_GAP_MIN_PX` / `_MAX_PX` | 0.5 / 12.0 | Flank face just outside the panel edge but within a pocket cavity (GD9 gaps: 2.9–6.1). |
| `DOOR_SLIDE_FLANK_LINE_MIN_LEN_FRAC` | 0.4 | A flank is a wall line, not a tick (× panel length). |
| `DOOR_SLIDE_FLANK_SIDE_MIN_FRAC` | 0.25 | Each side must cover this much of the panel axially. |
| `DOOR_SLIDE_FLANK_MIN_FRAC` / `_MAX_FRAC` | 0.35 / 0.90 | Both-sides pocketed coverage (GD9: 0.74). Near-total ⇒ embedded wall strip. |
| `DOOR_SLIDE_PROTRUSION_MIN_FRAC` / `_MAX_FRAC` | 0.08 / 0.65 | Leaf tip must stick out of the pocket (GD9: 0.27); mostly-out ⇒ flanking is coincidence. |
| `DOOR_SLIDE_ZONE_WIDTH_FACTOR` | 3.0 | Protrusion-zone half-width = × panel half-thickness. |
| `DOOR_SLIDE_ZONE_MAX_CROSSERS` | 2 | Jamb/end-cap linework in a doorway ≤ 2 crossers; wall hatch continuation ≥ 3. |
| `DOOR_SLIDE_ASSEMBLY_BASE` | 0.65 | Same tier as the qu/re rect-leaf swing assembly; label (+0.20) / layer (+0.40) boosts apply. |
| `DOOR_SLIDE_STROKED_RING_SNAP_TOL_PX` | 1.0 | Stroked rings snap at CAD precision; the white-ring 3 px buckets chain them into surrounding wall linework (component >8 segs, rejected). |
| `DOOR_SLIDE_PARK_GAP_MAX_PX` | 6.0 | parked_leaf panel-to-band-face gap (measured 0.75). Flush, not a pocket cavity (12). |
| `DOOR_SLIDE_PARK_FACE_COVER_MIN` | 0.80 | The hugged face runs behind the whole panel (measured 0.94); short faces are sills/ticks. |
| `DOOR_SLIDE_PARK_BAND_MIN_TH_PX` / `_MAX_TH_PX` | 2.0 / 20.0 | Face + partner face = a wall band (measured 7.0), not a lone shelf line. |
| `DOOR_SLIDE_PARK_JAMB_TOL_PX` | 8.0 | Band end vs panel end alignment (measured 3.0 overhang); parked means AT the jamb. |
| `DOOR_SLIDE_PARK_SPAN_RATIO_TOL` | 0.15 | Slide law: opening span ≈ panel length (measured 0.000). |

### 4.9c Folding-door detection (§3.10, `detection/doors/constants.py`)

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_FOLD_ANGLE_MIN_DEG` | 8.0 | Adjacent-leaf axis delta floor. Below is sliding/collinear territory (sliding pairs ≤6°); GD2's shallowest fold measures 10.1°. |
| `DOOR_FOLD_ANGLE_MAX_DEG` | 30.0 | Ceiling. Above is corner joinery / 45° bay glazing. Measured folds: 10.1–20.8°. |
| `DOOR_FOLD_LENGTH_RATIO_TOL` | 0.15 | Leaves of one door are equal panels (measured ≤0.005). |
| `DOOR_FOLD_HINGE_TOL_PX` | 6.0 | Corner-to-corner contact at the hinge. Leaves share the ring vertex exactly; qu-vs-ring fit offsets ≤0.3 px. |
| `DOOR_FOLD_MIN_CHAIN_LEAVES` | 3 | A standalone chain needs 3+ leaves (GD2 trifold). A lone 2-leaf V is never emitted. |
| `DOOR_FOLD_STACK_SPAN_RATIO_TOL` | 0.20 | Span law: outer span between parked stacks ≈ Σ leaf lengths (measured deviations 0.015, 0.001). |
| `DOOR_FOLD_STACK_MIRROR_TOL_DEG` | 15.0 | Stacks fold off the same wall plane: mean leaf axes mirror about the opening axis (measured ≤0.3°). |
| `DOOR_FOLD_STACK_PERP_EXTENT_MAX` | 1.25 | Per-stack corner extent perpendicular to the opening axis, × leaf length (measured 0.99–1.00×). |
| `DOOR_FOLD_ASSEMBLY_BASE` | 0.65 | Same tier as sliding / rect-leaf swing assemblies; label/layer boosts apply. |
| `DOOR_FOLD_OPEN_ANGLE_MIN_DEG` | 40.0 | open_v floor: below is the nearly-closed chain/stack territory (10.1–20.8°). |
| `DOOR_FOLD_OPEN_ANGLE_MAX_DEG` | 85.0 | Capped BELOW 90° so orthogonal corner joinery can never match (measured 71.2°). |
| `DOOR_FOLD_OPEN_OBLIQUE_MIN_DEG` | 8.0 | Leaf lines must be oblique to both axes; keeps bulk linework out of the pair search. |
| `DOOR_FOLD_LEAF_LINE_SEP_MIN_PX` / `_MAX_PX` | 0.8 / 4.0 | Double-line leaf separation (measured 1.9–2.5); 45° hatch at 5.7 px pitch = 4.03 sep. |
| `DOOR_FOLD_LEAF_LINE_LEN_RATIO_MIN` | 0.75 | Edge lines of one leaf (measured 0.915 — hinge-miter foreshortening). |
| `DOOR_FOLD_LEAF_LINE_OVERLAP_MIN` | 0.6 | Axial overlap of the edge lines, × shorter length. |
| `DOOR_FOLD_JAMB_ANCHOR_TOL_PX` | 6.0 | Jamb line endpoint to leaf tip (measured 3.4/3.6). |
| `DOOR_FOLD_JAMB_LINE_MIN_LEN_PX` | 15.0 | A jamb anchor is a wall face, not a cap/tick. |
| `DOOR_FOLD_JAMB_AXIS_TOL_DEG` | 15.0 | Jamb faces run along the opening axis (measured 2.2°). |
| `DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX` | 6.0 | Corridor half-width for far-jamb/crosser search (measured lateral offsets 1.2–1.8). |

### 4.10 Wall cross-validation

| Constant | Value | Rationale |
|---|---|---|
| `CROSS_WALL_EXPAND_PX` | 20.0 | Wall bbox is dilated by this for the overlap check. |
| `CROSS_NO_WALL_PENALTY` | 0.08 | Generic no-wall penalty for doors/windows. |
| `CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY` | 0.04 | Reduced penalty for **assembled** doors (already have strong evidence beyond wall context). |
| `CROSS_NO_WALL_SINGLE_LINE_LEAF_PENALTY` | 0.15 | **Strongest penalty.** Applies only when assembly_type == `single_line_leaf` AND `nearby_label is None`. The signature of a bath fixture or a window glazing decoration. Drops base 0.67 → 0.52, below the 0.55 floor. |

### 4.11 Confidence floors (offline mode)

In `pipeline.py`:
```python
OFFLINE_MIN_CONFIDENCE = {
    "door": 0.55,
    # ...
}
```
Below this, candidates move from `entities` to `rejected`. This is the offline-mode safety net; with Gemini enabled, candidates blend 0.5×heuristic + 0.5×Gemini.

---

## 5. Known false-positive patterns

These were confirmed on the test corpus. The single guard rule that catches both is `assembly_type == "single_line_leaf" AND wall_context == "no_wall" AND nearby_label is None`.

| Pattern | Where it appears | Why it looks like a door | What disambiguates |
|---|---|---|---|
| Bathtub / toilet | 5-1133-WD03.pdf, formerly door_0010 | Quarter-arc + perpendicular line (seat edge) is geometrically identical to a small door symbol | No wall around it, no door label nearby |
| Bay/fan window arc | 5-1133-WD03.pdf, formerly door_0007 | Quarter-arc decoration + matching-length line = perfect door geometry | No wall, no label |

`leaf_line_length_ratio` is **NOT** a useful discriminator — it's defined as `|len - radius|/radius` (error fraction). Low values mean *good* radius match. Both false positives have low ratios (0.0023, 0.10).

---

## 6. Known limitations / not currently handled

| Topology | Status | Where it appears | Why deferred |
|---|---|---|---|
| Chain-extension cap inside a component that has junctions | Not handled | rare in observed CAD | `_trim_chain_extension_caps` only acts on 2-leaf simple chains. Adding junction-aware variant requires more state. |
| Adjacent (but unpaired) doors sharing a near-shared hinge endpoint that ISN'T a garden-door pair | Not handled | unobserved | Considered as a follow-up to §3.7: a "cross-exclude paths within 5 px of shared endpoints" rule in `_check_opening_clear` for non-double-arc cases. Garden doors don't need it (both halves are in one assembly via the partner-paths threading); leaving the rule out keeps blast radius small until a real case is observed. |
| Spur > 4 segs | Not handled | observed once on floor-plans | Would need a separate "tail trim" with different criteria. |
| Multiple cycles at one junction | Partial — pruned one at a time | rare | Iteration handles it eventually but tests should add coverage. |
| Sliding doors (no arc) | **Handled** (§3.9) | 5-1133 GD4/GD5/GD9 | `_detect_sliding_doors`: leaf_pair + pocket_leaf oriented-rectangle patterns. |
| Folding/bifold doors (no arc) | **Handled** (§3.10) | 5-1133 GD2 trifold, kitchen CL doors, W9 folding wall | `_detect_folding_doors`: hinged-chain + parked-stack-pair patterns over white leaf panels. Lone 2-leaf stacks and 3+3 parked stacks remain out of scope. |
| Doors with arrow direction indicators | Not handled | unobserved | The arrow would currently be treated as part of the swing component and likely fail axis/angle checks. |
| Curved (non-circular) door panels | Not handled | rare | `_fit_circle_3pt` assumes a circular arc. Elliptical or freeform paths would mis-fit. |
| Differentiating door swing from bath fixture without strong context | Heuristic only | systematic | The geometry is genuinely ambiguous. Resolved only by `wall_context + label`. |

---

## 7. Test fixtures — coordinate gotcha

When writing tests in `tests/test_polyline_arc_pruning.py`, **space coordinates by ≥4 px in each axis** to avoid snap-key collisions:

```python
# snap_key(p) = (round(p[0]/DOOR_POLYLINE_ENDPOINT_TOL), round(p[1]/...))
# DOOR_POLYLINE_ENDPOINT_TOL = 2.0
# So (3.0, 50.0) and (5.0, 50.0) both round to (2, 25) — they MERGE.
```

Symptom of a collision: a closed cycle has fewer effective edges than the test expected. The test fails not because of the algorithm but because the test geometry collapsed. The constants table is footnoted: `DOOR_POLYLINE_ENDPOINT_TOL = 2.0`, `DOOR_LINEWORK_LEAF_ENDPOINT_TOL_PX = 3.0`, `DOOR_CURVE_CHAIN_ENDPOINT_TOL_PX = 1.0`. Use the strictest tolerance for whichever detector you're testing.

---

## 8. Debugging methodology (the diagnostic playbook)

When a door is missed or falsely detected, follow this sequence. **Do not propose fixes until you've identified which stage is failing.**

### 8.1 Run with `--debug`
```bash
python app.py extract <pdf> --no-gemini --debug --disable-windows
```

`--debug` writes `debug_trace.json` and `debug_viewer.html` per page. `--disable-windows` is recommended for door analysis (reduces noise; user preference documented in this session).

### 8.2 The `debug_trace.json` schema

Top-level keys:
- `polyline_components` — every BFS-discovered component, with `result`, `fail_reason`, `pre_prune_segment_count`, `pruned_path_indices`, `checks{}` per check, and `swing_id` if it became a swing.
- `swings` — every collected swing, with `source`, `path_indices`, `paired`, `candidate_id`.
- `leaves` — every collected leaf.
- `candidates` — every candidate that reached scoring, with `confidence_breakdown`.
- `by_path_index` — per-path lineage (which detectors evaluated this path, what result).

### 8.3 Tracing a missed door (in order)

1. **Identify the area** in the overlay (`pages/page_NN/overlay.png`). Note approximate bbox.
2. **Find the swing**:
   - For polyline-arc cases: grep `polyline_components` for components whose `path_indices` cover the area. Look at `fail_reason` and `checks`.
   - For native-curve cases: look for `c` paths in `primitives.json` in the area. If size < 20 or aspect not square, check if they chain (compute endpoint adjacency).
3. **If the swing is collected but no door appears**: check `swings[].paired` and `candidates`. Pairing fails most commonly on `radius_ratio_mismatch` (when fitted radius ≠ leaf length).
4. **If a candidate exists but isn't promoted**: check `final_entities.json:rejected[]` for offline-floor rejections.

### 8.4 Tracing a false positive

Open the candidate's `evidence` block:
- `arc_source`, `leaf_source`, `assembly_type`, `nearby_label`, `wall_context` — the 5 fields that determine which discriminator rules apply.
- `leaf_radius_ratio`, `connection_dist_px` — pairing-quality metrics.
- `confidence` and the `confidence_breakdown` from the debug trace.

### 8.5 Topology-from-debug-trace

Given a `polyline_component`, you can read its topology from `pruned_path_indices`:
- `pre_prune > kept` and pruned paths form short tails: **Y-junction stop** (spur pruning fired).
- `pre_prune > kept` and pruned paths form a closed loop: **cycle cap** (cycle pruning fired).
- `pre_prune == kept` and `result == rejected (axis_like_fraction)` with 2-leaf simple chain topology: **linear cap extension** (chain trim should fire but didn't — bug or threshold needs raising).
- `pre_prune == kept` and `result == rejected (segment_count_out_of_range)` with hundreds of segs: **wall network** (correctly rejected; not a door).

---

## 9. Reference data — current detection state

End-of-session detection counts (offline mode, walls enabled, windows disabled). Use these as regression targets when changing the algorithm.

### 9.1 floor-plans.pdf (1 page, 1240×1754 px, Microsoft Print to PDF)

11 doors: 7 `single_line_leaf` singles (conf 0.67) + 2 `double_swing` / `swing_layout=garden` composites (conf 0.65) + 1 `sliding`/`parked_leaf` + 1 `folding`/`open_v` (both conf 0.65, added 2026-07-21 — this PDF is no longer a full zero-detection control for §3.9/§3.10; it stays the zero-detection control for the leaf_pair, pocket_leaf, chain and stack_pair sub-patterns).

| entity_id | bbox (x0,y0,x1,y1) | size | conf | type | notes |
|---|---|---|---|---|---|
| garden_door_1 | 310, 356 — 420, 410 | 110×54 | 0.65 | double_swing | Recovered by `_split_double_arc` (§3.7). polyline_991 BFS = 24 segs → split 12+12. Replaces the previously-rejected door_0007. |
| garden_door_2 | 1001, 404 — 1111, 458 | 110×55 | 0.65 | double_swing | Recovered by `_split_double_arc` (§3.7). polyline_993 BFS = 24 segs; 2-cycle at hinge stripped by cycle prune; then 11+11 split. Absorbs the area previously detected as door_0008. |
| folding (hall/kitchen) | 388, 956 — 412, 1011 | 24×56 | 0.65 | folding / open_v | Paths 1739–1742: two 24.7/23.4 px double-line stroked leaves folded 71.2°, top tip anchored on the jamb band ends at y=955.5, span law 55.85 vs Σ 48.05 (dev 0.159). Bbox spans the V + opening corridor. |
| sliding (hall) | 388, 1018 — 398, 1118 | 11×100 | 0.65 | sliding / parked_leaf | Paths 945/954/955/1734: a 3.0×51.25 stroked ring parked flush on the jamb band face (gap 0.75, cover 0.94, band 7.0), slide law 51.25 vs 51.25 (dev 0.000). Retires the old door_0011 leaf-fallback on the same ring. Bbox spans panel + opening. |
| door (long-corridor) | 1096, 649 — 1141, 694 | 45×45 | 0.67 | single_line_leaf | Recovered by cycle pruning (polyline_856 / linework_801 area) |
| door (long-corridor) | 1041, 704 — 1086, 749 | 45×45 | 0.67 | single_line_leaf | Recovered by spur pruning (linework_1318) |
| door | 424, 917 — 467, 958 | 43×41 | 0.67 | single_line_leaf | Baseline |
| door | 979, 1064 — 1029, 1117 | 50×54 | 0.67 | single_line_leaf | Baseline |
| door | 1036, 1139 — 1090, 1189 | 54×50 | 0.67 | single_line_leaf | Baseline |
| door | 389, 1185 — 440, 1232 | 51×47 | 0.67 | single_line_leaf | Baseline |
| door | 458, 1337 — 512, 1392 | 54×55 | 0.67 | single_line_leaf | Recovered by chain-extension trim (linework_226 / polyline_393) |

(Entity IDs aren't pinned because the numeric suffix depends on emission order, which shifts when new detectors come online — match by bbox.)

### 9.2 5-1133-WD03.pdf (1 page, Vectorworks output)

15 doors — the 9 swing doors below plus 3 sliding doors (§3.9, added 2026-07-09) plus 3 folding doors (§3.10, added 2026-07-16):

| bbox | conf | type | notes |
|---|---|---|---|
| 1710.2, 480.7 — 1785.7, 523.2 | 0.81 | folding / chain | GD2 trifold (label boost, −0.04 no-wall assembly penalty). Three 74px leaves hinged zigzag at fold deltas 10.1°/20.6°, drawn nearly closed. |
| 1894.2, 571.2 — 2288.2, 671.2 | 0.65 | folding / stack_pair | Kitchen "CL doors". Two 2-leaf V-stacks (100px leaves, folds 19.6°) parked at opposite jambs of the 5400mm opening; span law 394 vs 400px. |
| 2345.2, 126.2 — 2440.2, 510.2 | 0.65 | folding / stack_pair | W9 "folding/sliding doors" wall. Two 2-leaf V-stacks (96px leaves, folds 16.3°/16.6°) parked at opposite jambs; span law 384.1 vs 384.5px. |

| bbox | conf | type | notes |
|---|---|---|---|
| 1183.8, 699.2 — 1303.7, 705.2 | 0.65 | sliding / leaf_pair | GD4 ("position set out by sliding door opening"). Two 94.5×6 white panels overlapping 0.73, drawn CLOSED across the doorway. |
| 1191.2, 834.7 — 1333.3, 841.2 | 0.65 | sliding / leaf_pair | GD5. Two 94.5×6 panels overlapping 0.50, drawn PARKED in the east pocket (door bbox covers only half the doorway — this is why sliding doors are exempt from the room stage's open-leaf veto). |
| 797.7, 787.7 — 803.7, 882.2 | 0.85 | sliding / pocket_leaf | GD9 (label boost). Vertical 94.5×6 white panel, 74 % flanked between hairline wall faces, protruding 25 px into the doorway. |

Non-detections to preserve (verified not doors): the WALL TYPE 4 ply stack at (1786–1807, 552–575) — lateral offset ≈ 1 thickness, overlap 0.94; the duplicated cistern symbol at (992, 924) — overlap 1.0; the 94.5×2.5 shower screen at (1257, 1053) — below min panel thickness; blind-box panels at (2321, 318) and (2092, 530) — no partner, embedded in dotted track bands, no flank profile. (The GD2 trifold and the W9 folding leaves, formerly listed here as out of scope, are the §3.10 folding detections above.)

The 9 swing doors:

| entity_id | bbox | size | conf | type | notes |
|---|---|---|---|---|---|
| door_0006 | 231,105 — 355,229 | 124×124 | 0.72 | qu | Baseline |
| door_0002 | 1311,114 — 1420,224 | 110×110 | 0.83 | qu | Baseline (label) |
| door_0009 | 71,448 — 138,514 | 67×66 | 0.67 | single_line_leaf, in_wall | Baseline |
| door_0004 | 769,459 — 860,549 | 90×90 | 0.83 | qu | Baseline (label) |
| door_0003 | 1088,468 — 1171,550 | 84×81 | 0.83 | curve_arc_chain + qu | Recovered by chained-curve detection. Chain of 16 Beziers, fitted radius 82.4 (vs leaf 81.5). Label GD6. |
| door_0005 | 1329,592 — 1419,682 | 90×90 | 0.83 | qu | Baseline (label) |
| door_0001 | 649,592 — 757,682 | 108×90 | 0.79 | qu | Baseline (label) |
| door_0000 | 1466,711 — 1556,801 | 90×90 | 0.79 | qu | Baseline (label) |
| (garden) | 1884,772 — 1966,937 | 82×165 | 0.61 | double_swing / swing_layout=garden | Recovered by `_detect_curve_arc_double_partners` (§3.8). Two single Beziers (each `curve_arc`, radius 82) sharing endpoint (1883.7, 854.7); paired with horizontal anchored-line leaves at y=772 and y=937. Replaces what used to be ONE false-positive single (door_0008, "window decoration") plus one rejected sub-floor candidate (door_0007). |

One known **false-positive area** suppressed (verified by user):
- (1286, 907)–(1333, 933) — a **bath fixture**. `single_line_leaf + no_wall + no_label`. Confidence 0.67 → 0.52, below floor. Since 2026-07-09 it is also inert in the room stage: `detect_rooms` consumes candidates BEFORE the offline floor, and at 0.52 this FP used to take the dilated-bbox fallback seal and stamp a notch into the FAMILY BATH room outline — the bbox fallback (the one seal with no evidence of its own) now requires `ROOM_BBOX_SEAL_MIN_CONFIDENCE` 0.55 (rooms.py), while plug seals still work from 0.40.

**Baseline update (wall-network rebuild, 2026-07-03):** wall detection was rebuilt as an internal centerline network that also sees Vectorworks-style *filled* walls (fill-outline `l` items with stroke width 0), which the old detector was blind to. Three doors on this sheet were previously penalized `no_wall` only because their (filled) walls were invisible; they now resolve `in_wall` and their confidences rise by the assembly penalty 0.04:
- (649, 592)–(757, 682): 0.79 → **0.83**
- (1466, 711)–(1556, 801): 0.79 → **0.83**
- garden (1884, 772)–(1966, 937): 0.61 → **0.65**

The bath fixture stays rejected at 0.52: it also stands against (filled) bathroom walls, so plain wall adjacency can no longer discriminate it — instead, `single_line_leaf + no_label` doors now require **stroked** wall corroboration (`WallNetwork.near_bbox(..., stroked_only=True)`); pure fill-outline geometry is also how fixtures themselves are drawn. Its evidence carries `wall_context_note: "filled_wall_only"`.

(The previously-reported (1884, 772)–(1966, 855) "window decoration" FP was a misclassification — it was actually the upper half of the garden door now correctly merged above.)

---

## 10. Pipeline-level constraints to honor

- **Coordinate system:** all bboxes are `(x0, y0, x1, y1)` in **150-DPI pixel space, top-left origin, y-down**. `SCALE = 150/72` in `extractor.py`. Don't reintroduce point-space (1/72") anywhere past `extractor.py`/`plumber.py`.
- **Page numbers:** **1-based in serialized output**; `page_indices` between functions are **0-based**.
- **Path explosion:** `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful — do not re-bundle multi-item drawings.
- **Warning codes:** SCREAMING_SNAKE_CASE, emitted from `pipeline.collect_warnings`, `plumber.compare_counts`, or `gemini_client._validate_response`.

---

## 11. How to verify a change won't regress

Before merging any door-detection change:

1. `python -m unittest discover tests` (currently 80 tests).
2. Run the two reference PDFs offline and compare door counts/bboxes to §9:
   ```bash
   python app.py extract floor-plans.pdf --no-gemini --debug --disable-windows
   python app.py extract 5-1133-WD03.pdf --no-gemini --debug --disable-windows
   ```
3. Targets to hit:
   - **floor-plans.pdf**: 11 doors at the bboxes in §9.1 — 7 singles at conf 0.67 + 2 `double_swing`/`swing_layout=garden` at conf 0.65 + the `sliding`/`parked_leaf` at (388,1018)–(398,1118) + the `folding`/`open_v` at (388,956)–(412,1011), both 0.65. NO other sliding/folding doors — this PDF is the zero-detection control for the leaf_pair, pocket_leaf, chain and stack_pair sub-patterns.
   - **5-1133-WD03.pdf**: 15 doors at the bboxes in §9.2 — 8 baseline + 1 `double_swing`/`swing_layout=garden` at (1884,772)–(1966,937) + 3 `sliding` (GD4/GD5/GD9) + 3 `folding` (GD2, kitchen CL doors, W9). Apply the §9.2 baseline update: (649,592) and (1466,711) at 0.83, garden at 0.65.
   - (1286, 907)–(1333, 933) stays rejected (the remaining bath-fixture FP), and the §9.2 sliding non-detections stay out.
   - Room regression on 5-1133 (full run, no flags): 18 rooms (16 predates the 2026-07-16 folding-door detection; 22 predates the 2026-07-15/16 lattice-demotion and bay/garden-door seal fixes in walls.py/rooms.py; 26 predates the 2026-07-09 tile-grid/phantom-wall fixes that merged the fragmented WC and Family Bath+Utility rooms). The folding doors reshape rooms ONLY around themselves: the two phantom strip rooms tiling the W9 doorway at (2332,122)–(2411,364) and (2332,354)–(2442,513) dissolve into the door, the kitchen band room (1890,540)–(2292,662) splits at the CL-door plane, the room south of W9 starts at y≈515 (the door band edge), and small outdoor paving pockets outside the kitchen door emerge as door-bearing rooms. Elsewhere unchanged: a room MERGE across (1082,710)/(1241,846) means the sliding room-stage exemption broke; the WC room (1053,709) bottoms out at y≈829.7 (the divider band edge) and the (1053,845) bath room's right edge runs straight at x≈1342 — a bite around (1286,907) means the bath-fixture FP regained the bbox seal.

Note (wall-network rebuild): "walls enabled" now means the internal wall-centerline network + room detection (`--disable-walls` is a deprecated alias for `--disable-rooms`). `wall_context` in door evidence derives from `WallNetwork` corridor tests in `detection/postprocess.py::_cross_validate`; no wall candidates are emitted anymore. Door penalty constants and tiers are unchanged. If a door's `wall_context` flips after touching `WALL_*` constants, widen the network coverage (face collection / pairing tolerances) — never door constants.

If door counts drop, use the §8 diagnostic playbook to identify which stage is regressing before adjusting thresholds.
