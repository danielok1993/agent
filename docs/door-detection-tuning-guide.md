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
2. **Leaf collection** — `_collect_door_leaves(paths)` finds:
   - `qu`/`re` (closed rectangle) leaves passing `_is_door_leaf`.
   - `linework_rect` leaves (4–8 line segs forming a closed thin rectangle).
   - `linework_rect_subgraph` (the same with a few attached spurs).
   - Anchored-line leaves (single `l` line near an arc endpoint, length ≈ swing radius).
3. **Pairing** — `_pair_door_assemblies(swings, leaves, …)` matches swings to leaves by:
   - `connection_dist ≤ DOOR_ASSEMBLY_CONNECT_TOL_PX` (15 px between swing pairing-points and leaf corners), AND
   - `radius_ratio = |leaf.length - swing.radius| / swing.radius ≤ DOOR_LEAF_RADIUS_RATIO_TOL` (0.20).
4. **Cross-validate** — `_cross_validate(candidates, walls)` applies a `wall_context` penalty when the door has no overlapping wall.

After pairing, `merge_gemini_and_heuristics` (offline mode) applies `OFFLINE_MIN_CONFIDENCE["door"] = 0.55` as the floor for being promoted to an `Entity`.

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
One `c` path. Bbox square-ish, radius = max(w,h). Passes `_is_arc_like` directly.

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

---

## 4. The constants — every tunable in one table

All in `heuristics.py`. Grouped by stage. Defaults are the *current* values after the four fixes; the "rationale" column tells you *why* it has that value and what regresses if you change it.

### 4.1 Arc shape

| Constant | Value | Rationale |
|---|---|---|
| `DOOR_BBOX_ASPECT_MIN` | 0.85 | A full quarter arc's bbox is square. Don't raise — admits wall hatches. |
| `DOOR_BBOX_ASPECT_MAX` | 1.15 | Symmetric with MIN. |
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
| `DOOR_LAYER_KEYWORDS` | `["door", "a-door"]` | Substring match in layer name. CAD layers are often empty in the test PDFs, so layer_hint rarely fires. |

### 4.9 Confidence boosts and floor

These hardcoded in `_pair_door_assemblies` (heuristics.py:1833+, 1730+):

| Element | Value | Notes |
|---|---|---|
| Single (qu/re leaf) base | 0.65 | The strongest leaf evidence — a closed rectangle. |
| `single_line_leaf` base | 0.60 (`DOOR_ASSEMBLY_LINE_LEAF_BASE`) | Weaker leaf evidence — one anchored line. |
| Label boost | +0.20 | When a `DOOR_LABEL_PATTERN`-matching text span is within `DOOR_LABEL_SEARCH_RADIUS_PX`. |
| Layer hint boost | +0.40 | When layer name contains a `DOOR_LAYER_KEYWORDS` token. Almost never fires on the test PDFs (empty layers). |
| `DOOR_THRESHOLD_CONFIDENCE_BOOST` | 0.10 | When an entrance threshold line is detected across the opening. |
| `DOOR_V2_OPENING_CLEAR_BOOST` | 0.07 | When the bridge between the arc's two endpoints is unobstructed. |
| `DOOR_V2_OPENING_OBSTRUCTED_PENALTY` | 0.12 | When the bridge crosses another line (likely not a real opening). |
| `DOOR_ARC_FALLBACK_MAX` | 0.45 | Cap for arc-only fallback so it stays below the 0.55 offline floor. |
| `DOOR_FALLBACK_CONFIDENCE` | 0.35 | Base for leaf-fallback (leaf without paired arc). Also below the floor. |
| Confidence cap | 0.95 | Hardcoded ceiling. |

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
| Sliding doors (no arc) | Not handled | unobserved in test corpus | Different symbol entirely — would need leaf-only + slide-marker detector. |
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

9 doors: 7 `single_line_leaf` singles (conf 0.67) + 2 `double_swing` / `swing_layout=garden` composites (conf 0.65). All `arc_source = polyline_arc`.

| entity_id | bbox (x0,y0,x1,y1) | size | conf | type | notes |
|---|---|---|---|---|---|
| garden_door_1 | 310, 356 — 420, 410 | 110×54 | 0.65 | double_swing | Recovered by `_split_double_arc` (§3.7). polyline_991 BFS = 24 segs → split 12+12. Replaces the previously-rejected door_0007. |
| garden_door_2 | 1001, 404 — 1111, 458 | 110×55 | 0.65 | double_swing | Recovered by `_split_double_arc` (§3.7). polyline_993 BFS = 24 segs; 2-cycle at hinge stripped by cycle prune; then 11+11 split. Absorbs the area previously detected as door_0008. |
| door (long-corridor) | 1096, 649 — 1141, 694 | 45×45 | 0.67 | single_line_leaf | Recovered by cycle pruning (polyline_856 / linework_801 area) |
| door (long-corridor) | 1041, 704 — 1086, 749 | 45×45 | 0.67 | single_line_leaf | Recovered by spur pruning (linework_1318) |
| door | 424, 917 — 467, 958 | 43×41 | 0.67 | single_line_leaf | Baseline |
| door | 979, 1064 — 1029, 1117 | 50×54 | 0.67 | single_line_leaf | Baseline |
| door | 1036, 1139 — 1090, 1189 | 54×50 | 0.67 | single_line_leaf | Baseline |
| door | 389, 1185 — 440, 1232 | 51×47 | 0.67 | single_line_leaf | Baseline |
| door | 458, 1337 — 512, 1392 | 54×55 | 0.67 | single_line_leaf | Recovered by chain-extension trim (linework_226 / polyline_393) |

(Entity IDs aren't pinned because the numeric suffix depends on emission order, which shifts when new detectors come online — match by bbox.)

### 9.2 5-1133-WD03.pdf (1 page, Vectorworks output)

8 doors:

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

Two known **false-positive areas** suppressed (verified by user):
- (1884, 772)–(1966, 855) — a **window** decoration. `single_line_leaf + no_wall + no_label`. Confidence 0.67 → 0.52, below floor.
- (1286, 907)–(1333, 933) — a **bath fixture**. Same signature. Same drop.

---

## 10. Pipeline-level constraints to honor

- **Coordinate system:** all bboxes are `(x0, y0, x1, y1)` in **150-DPI pixel space, top-left origin, y-down**. `SCALE = 150/72` in `extractor.py`. Don't reintroduce point-space (1/72") anywhere past `extractor.py`/`plumber.py`.
- **Page numbers:** **1-based in serialized output**; `page_indices` between functions are **0-based**.
- **Path explosion:** `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful — do not re-bundle multi-item drawings.
- **Warning codes:** SCREAMING_SNAKE_CASE, emitted from `pipeline.collect_warnings`, `plumber.compare_counts`, or `gemini_client._validate_response`.

---

## 11. How to verify a change won't regress

Before merging any door-detection change:

1. `python -m unittest discover tests` (currently 71 tests).
2. Run the two reference PDFs offline and compare door counts/bboxes to §9:
   ```bash
   python app.py extract floor-plans.pdf --no-gemini --debug --disable-windows
   python app.py extract 5-1133-WD03.pdf --no-gemini --debug --disable-windows
   ```
3. Targets to hit:
   - **floor-plans.pdf**: 9 doors at the bboxes in §9.1 — 7 singles at conf 0.67 + 2 `double_swing`/`swing_layout=garden` at conf 0.65.
   - **5-1133-WD03.pdf**: 8 doors at the bboxes in §9.2.
   - Neither (1884, 772)–(1966, 855) nor (1286, 907)–(1333, 933) becomes a door (those are the known FPs).

If door counts drop, use the §8 diagnostic playbook to identify which stage is regressing before adjusting thresholds.
