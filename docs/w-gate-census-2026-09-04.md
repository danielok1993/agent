# W-gate recalibration — iteration 1: the census (2026-09-04)

Branch `recal/w-gate-census` (from main `f5682fc`). **No constant changed.**
Baseline sweep of main reproduced: 71 returned FPs (23+25+3+20), 0 LOST, 5
unreviewed; snapshots of all 20 slugs in `outputs/regress_baseline/`.

## Method

- Harness (`scratchpad/census/harness.py`): `tools/_corpus_page.load_detection_pages`
  → the exact stage-5 chain of `run_heuristics` (doors → windows → conflicts →
  wall network → cross-validate → suppress → rooms) → `OFFLINE_MIN_CONFIDENCE`
  floors → `regression.sweep.evaluate_page`. Self-check: s01 11/11 · 12/12 · 4/4,
  s02 15/15 · 11/11 · 11/11 (labels/schedules deliberately outside it) — the §4c
  rule is met.
- Populations (`populations.py`, `pop/<slug>.json`): taps on
  `_pair_faces_to_centerlines` (every kept pair + an above-cap probe at 4× the
  caps with the material/through verdicts), `_band_has_wall_material` (density
  per call), `_collect_wall_faces`, `_door_plugs` (jamb gap beyond the bbox at
  1px sampling), `_free_space_components`, `_bridge_white_runs`,
  `_rate_fill_classes`, plus per-entity door/window evidence, the CROSS
  needed-reach (binary search on `near_bbox`), and every entity matched to
  the user's verdicts. Every px converted at the sheet's **true** denominator
  (s01 92.2; s03/s17 per region; s13 136.4), never the applied factor.
- Ablations (`ablate.py`, `abl/*.jsonl`): `WallGates/RoomGates/DoorGates/WindowGates/CrossGates.at`
  wrapped with `dataclasses.replace`. (a) s01 at f=0.542: full, each of the 50
  fields alone, leave-one-out. (b) Multiplier sweep: each field × {0.5, 0.67,
  0.8, 1.25, 1.5, 2.0} (areas ×m², the density ÷m) on s01, s02, s03, s05, s07,
  s12, s13, s17 (all 307 configs) and a key subset on s11, s16, s18. Scored
  by type + IoU ≥ 0.5 against the truth and against the sheet's own baseline.
  `THICK`/`THROUGH` scaled alone trip the ordering asserts below 0.8× / above
  1.25×, so the three caps were also moved together (`CAPS3`).

Factor actually applied today (the handoff's "s03/s17 1:100 plans" run at
**identity**: ink-dominant 1:50): f=1.0 s01 s02 s03 s04 s08 s10 s14 s15 s17
s20; f=0.5 s05 s06 s07 s11 s12 s16 s18; f=0.367 s13.

## The two worked instances, refreshed

- **ROOM_BLIND_WINDOW_MAX_AREA_PX2 = 10 000** — 0.72 m² at 1:50, 2.44 m² on s01
  today. The "≥ 17k px²" rationale figure is s02's smallest window room (1.23 m²);
  s01's two window rooms are 35.8k px² = 8.7 m². Measured true class (a
  confirmed room whose only entrance-grade door is missing): s17 0.94 m² —
  1.31× over the gate and LOST at 1.25×. False class: s02's terrace pockets
  0.19–0.27 m² (the rule's target) — but door-less window-only pockets reach
  0.97 m² (s04), 1.3 (s18), 1.7 (s15), 2.1 (s16), 2.6 m² (s11), and two are
  emitted as FP rooms at 2.0 m² (s16, s18). Area does not separate the
  classes; the number only catches the s02 pockets.
- **WALL_MAX_THICKNESS_PX = 36** — 305 mm at 1:50, 562 mm on s01 today. s01's
  real walls at 92.2: exterior 19.3 px = 301 mm, party wall 25 px = 390 mm
  (hatched); its 28–35.5 px "strong pairs" are red-pen furniture (sofa, sink
  unit; crop-verified) that the room stage drops. On 13 sheets the un-hatched
  strong-pair distribution ENDS at the cap: 300–305 mm (s02 295, s03 301, s05
  305, s07 301, s13 300, s15 305, s18 304, s20 301 …) — the cap is binding at
  1.00–1.03× everywhere, i.e. the corpus's standard 300 mm walls sit on it.
  False class: s11's confirmed 300 mm-wide storage slot (lost at 1.25×), s02's
  patio paving joints at 313–340 mm (36.6–40 px; harmless at 1.25× per sweep).

## The gates that break s01 at f = 0.542 — refreshed on today's code

Full f=0.542: 1 door + 6 rooms lost, 18 phantoms (was 10/11, 7/13, 17). One
field at a time (of 50), only **four** break alone:

| field alone at 0.542 | effect | why |
|---|---|---|
| WALL_MAX_THICKNESS_PX 36→19.5 | 4 rooms lost | the 21–25.5 px hatched walls DO pass the thick tier (density 9–26/100px), but the short pieces between openings (36 px, 3 marks) fail its ≥4-marks/span gates and the rooms leak |
| DOOR_FOLD_JAMB_ANCHOR_TOL_PX 6→3.25 | door_0012 + 2 rooms | measured 3.4/3.6 px ON s01 = 53–56 mm at 92.2; the 1:50 value 6 px is only 51 mm |
| ROOM_OPENING_SEAL_PX 12→6.5 | 1 room | s01's swing bbox stops 8 px = 125 mm short of its jamb |
| CROSS_WALL_EXPAND_PX 20→10.8 | 1 door | a single_line_leaf whose nearest paired wall is 12 px = 187 mm away → no_wall penalty → 0.52 < 0.55 |

No longer solo culprits: WALL_HATCH_MAX_LEN_PX (0), WALL_WEAK_MATERIAL_PER_100PX
(0 — s01's material bands measure 7–26/100px, above the 5.5 gate; the August
4.8 figure predates the mark dedup), WALL_FACE_MIN_LEN_PX + COLLINEAR (0),
ROOM_MIN_AREA_PX2 (0). They act through interaction (leave-one-out at 0.542):
COLLINEAR_OFFSET_TOL held at 4 px cuts the phantoms 18→4 (s01's 45° hatch-chain
pieces straddle 3.9–4.1 px — paper-space, the same 4.05 px pitch as s02);
ROOM_MIN_AREA held cuts them 18→8 (the 34×34 px cushion cells = 0.28 m² at
92.2); WALL_FACE_MIN_LEN held: 18→6 phantoms but 10 lost.

## THE TABLE

Columns: **now** = value at 1:50 (mm at 1:50 · mm as applied on s01 today);
**true / false** = the measured world range of the class the gate admits /
excludes (sheet); **headroom** = safe multiplier window from the sweeps per
factor group — f1 (s02 s03 s17), f.5 (s05 s07 s12 s11 s16 s18), f.37 (s13),
s01 (identity) — "[a,b]" means every multiplier in that window left every
sheet of the group unchanged (2.0 = ≥2×), plus **@.542** = does this field
alone break s01 at its true factor; **ref** = proposed value at 1:50 (= mm ÷
8.47) with the margin it leaves; **move** = verdict. ⚠ = a margin under ~1.5×
on the *discriminator itself* — the feature, not the number, is the problem.

| # | constant | class | now | defining features (sheet) | true class (world) | false class (world) | headroom f1 / f.5 / f.37 / s01 · @.542 | ref @1:50 | move? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | WALL_FACE_MIN_LEN_PX | W | 11 px (93 · 172 mm) | s03 nib 11.75 px = 100 mm; s01 15 lines 11–12 px = 172–187 mm | shortest paired faces sit ON the gate on every sheet: 93–104 mm (s02 11.2, s03 11.2, s14 11.0, s05 5.8, s07 5.7, s13 4.5, s18 5.5); s01 min 183 mm | axis-aligned wall-pen strokes 6–11 px: s01 163, s15 609, s12 211, s05 150 — harmless at 0.67× on 9/10 sheets; s07 splits a room at ≤0.67 (62–93 mm strokes) | [0.5,1.0] (s05 loses 2 rooms at 1.25) / [0.8,1.25] (s07 both ways) / [0.5,2] / [0.5,0.8+] · ok | 9 px (76 mm): 1.22× under the 93 mm nib, 1.2× over s07's 7.4 px break ⚠ | **TRIED 9 → REVERTED to 11** (iteration 2, G2): the false class measured here was axis-aligned strokes, but a band's 45° hatch is T√2 long — s01's 7 px partitions hatch at 9.9 px (paths 2914–2925, 1.0 px pen) and the band-end strokes paired (s01 room_0003 edge jogged 4 px, IoU 0.975; s02 room_0004 −55 px²); s18's 4.5 px scaled floor fenced a worktop run (−1 recorded FP, +1 phantom). Revisit with s01's true-scale factor (a 100 mm band's hatch is 16.7 px at 1:50) |
| 2 | WALL_MIN_THICKNESS_PX | W (floor 1) | 2 px (17 · 31 mm) | "thinnest partition" | thinnest strong pairs 4.2 px s01, 4.3 s02, 2.1–2.6 @f.5, 1.8 @s13 — glazing/leaf doublets, not walls; real thinnest wall 75–100 mm | pen doublets ≤1.5 px (paper) | [0.5,2] everywhere · ok | 2 (keep; the 1.0 floor is what protects it) | no |
| 3 | WALL_MAX_THICKNESS_PX | W | 36 px (305 · 562 mm) | s01 blockwork "~32 px" (=500 mm at 92.2!); real s01 walls 301 / 390 mm | un-hatched walls END at the cap on 13 sheets: 300–305 mm (1.00–1.03×); hatched thicker walls only via the material tiers | s11 confirmed 300 mm slot (lost at 1.25×); s02 paving joints 313–340 mm (harmless at 1.25×); s01 furniture 440–554 mm (pen-dropped) | (0.8,1.25] / (0.8,1.5] s07·s12·s16·s18, s11 (0.8,1.0] / (0.8,1.25] / (0.8,1.25] (CAPS3 1.5 loses 1: furniture pairs at 45–54 px = 700–840 mm) · **✗ 4 rooms** | 40 px (339 mm): 1.11× over 305 mm walls, 1.09× under s11's slot (faces 21.75 px @f.5 vs 20) ⚠ | **TRIED 40 → REVERTED to 36** (iteration 2, G2): −5 recorded FP rooms (s17's four 35 px reveal strips in its 37 px = 313 mm cavity walls, s16's striped block) but s02's WC notched 14 % (wall face × hairline basin edge at 38.25 px over two 13 px corner X symbols as "material" — cleared by iteration 3's far-side density rule), s01's hob fenced (kitchen units 38.5 px = 600 mm @92.2 pair and lattice-demote), +1 phantom each on s11 (wall-recess box), s15 (annotation pocket), s18 (tree strip); s16 room_0006 breaks at 38. Thresholds 37.0 / 38.25 / 38.5 — the ⚠ was right: no number in the band is a reference; the far-side density rule (iteration 3 step 1) clears s02's WC at 40, but s01's 38.5 px units still pair and the s11/s15/s18 phantoms return → waits for s01's true-scale factor and the recess/annotation-pocket rules |
| 4 | WALL_THICK_MATERIAL_MAX_PX | W | 48 px (406 · 749 mm) | "s01 pier 19→39 px" = 613 mm at 92.2, not 400 mm; "1:50 400 mm ≈ 47 px" | material-backed thick pairs: s15 377–400 mm, s20 400 mm (47.2–47.3 px = 1.01×), s16 305–336, s01 breast 601–613 (identity 39.2 px) | hatched fixtures/floors with material from 349 mm (s15 261 pairs), 495 (s02), 400+ (s20) — gated by material, not by this cap | alone [0.8,1.25]; CAPS3@1.5: s03 L1, s16/s18 improve, s11 L1 / [0.8,1.25] (s05's "+1" at 1.25 is its 475 mm wall dropping from the THROUGH tier into the THICK tier, whose 24 px mark cap cannot see its 39 px strokes — row 11's defect, not a false-class hit) / [0.8,1.25] / [0.8,1.25] · **✗ (26 < 39.2)** | 56 px (475 mm): 1.19× over the 400 mm walls; s01 breast at 0.542 → 30 < 39.2 still fails ⚠ | **MOVED 48 → 56** (iteration 2, G3a, together with row 11's per-band cap): s05 9/9 rooms at f=0.5 via the thick tier; corpus verdicts identical, two sub-1 % outline improvements (s11 porch, s13 bedroom) |
| 5 | WALL_THROUGH_HATCH_MAX_PX | W | 64 px (540 · 1000 mm) | s05 28 px @1:100 = 475 mm (calibrated at true scale) | s05 475 mm (32/28 = 1.14×) | through-hatched floors/fixtures: s01 from 81.5 px = 1272 mm (identity), s05 66.5–68 px = 1.13–1.15 m, s20 94 px | alone [0.8,2] s03·s07·s12·s13; s05 (0.8,2] (at 0.8 = 51 px its 475 mm wall leaves the tier and its interior returns as the original phantom) / [0.8,2] / [0.8,·] | 72 px (610 mm): 1.28× over s05, 1.13× under s01's first false (identity) | **MOVED 64 → 72** (iteration 2, G1, 2026-09-04): corpus sweep identical on every sheet |
| 6 | WALL_PAIR_MIN_OVERLAP_PX | W | 12 px (102 · 187 mm) | "shorter is coincidence" | shortest kept overlap sits ON the gate: 12.0–12.8 px @f1, 6.0–6.5 @f.5, 4.5 @s13 (100–108 mm); s01 192 mm | sub-gate overlaps | [0.5,2] on 10 sheets · ok | 12 (keep) | no — inert |
| 7 | WALL_FILL_CLASS_MIN_INK_PX | W | 150 px (1.27 m) | "rate a fill class once it carries this much ring length" | smallest wall-rated class 880 px (s02 grey) = 5.9× | rare fills | [0.5,2] · ok | 150 | no — inert |
| 8 | WALL_FILL_BLOCK_MAX_SIDE_PX | W | 72 px (610 mm) | bands/posts vs shaded zones | wall-rated ring short side ≤ 45.6 px = 386 mm (s02), ≤ 16.8 elsewhere | shaded zones 70.7–147 px = 599 mm–1.25 m (s02/s04/s08) — rated non-wall anyway | [0.5,2] · ok | 72 (1.58× / 0.98×, second-line gate) | no |
| 9 | WALL_WEAK_MIN_RUN_PX | W | 30 px (254 · 468 mm) | "shorter slivers are tick/mullion clusters" | shortest material-OK band 263 mm (s02 31 px), 273 (s16), 277 (s17), 284 (s20) — ON the gate (1.03–1.1×) | sub-gate weak pairs: s01 831, s02 348 (material unknown) | [0.5,1.5] (s02 loses 2 rooms at 2.0 = 60 px: its 31–37 px partitions) / [0.5,2] / [0.5,2] / [0.5,2] · ok | 30 (keep; 24 would give 1.3× and is inert too) | no — inert downward: the feared slivers do not exist at 15–30 px |
| 10 | WALL_JOINERY_BRIDGE_GAP_PX | W | 80 px (677 mm) | s02 wardrobe fronts (1:50, true scale) | needed span 40–54 px = 340–457 mm (L1 at 0.5, ok at 0.67); gaps ≤ gate p90 550 mm, max 674 | gaps > 80 px continue from 80.1 (continuous) | s02 [0.67,1.25] (+1/+2 phantom rooms at 1.5/2.0 from over-bridging) · ok | 80 | no |
| 11 | WALL_HATCH_MAX_LEN_PX | W | 48 px (406 · 749 mm) | "hatch stays short; 45 px cap + slack" | 45° through-hatch = T·√2: a cap-thickness band's strokes are 51 px (s02 51.5, s20 50.2 p90, s01 55.7, s05 49.5 @f.5, s06 50.2, s13 35.7 @f.37) — 27–64 % of in-band strokes exceed the cap on s05/s06/s12/s13/s20 | winders/leaders from 58.6 px (s03 stair = 496 mm), s10 102, s17 109 | [0.67,1.0] (s03 loses a room at 1.25+) / [0.67,2] / (0.5,2] (s13 L2 at 0.5) / · · ok | not a number: 0.93× / 1.22× ⚠ | **DONE** (iteration 2, G3a): marks collected once at the through diagonal, `_band_has_wall_material` filters to `_mark_len_cap` = max(48f, T√2 + 2); a mark over the page-wide cap counts only as through-hatch (both ends on faces) — the first sweep without that condition paired s17's stair stringers on two barbs + two cut lines (the 4-mark floor exactly) and fenced the flight; 48 stays the winder/leader ceiling in `_demote_stair_faces`, `_barrier_extent` and the lone-face helpers |
| 12 | WALL_WEAK_MATERIAL_PER_100PX | ÷f | 3.0/100 px (3.54/m · 1.92/m on s01) | "real ≥4.8, noise ≤2.6 on s01/s02" — s01's 4.8 is 3.1/m, s02's 5.7/m | OK bands min 3.4/100 = 4.1/m (s02, 1.13×), 4.4–4.6/m (s15/s17), s01 4.5/m; s16's real hatched wall between two windows (crop-verified) 5.4/100 @f.5 = 3.2/m FAILS (0.9×) | s02 glazing strip + ticks 1.7/100 = 2.0/m; s04 1.4/m | (0.67,1.5] s02 (L3 at 0.67, L5 at 0.5; +1 phantom at 2.0 = gate 1.5 < the 1.7 glazing strip) / [0.67,1.5] s11·s16 / [0.5,2] / [0.5,2] · ok | 2.2/100 px (2.6/m): 1.23× over s16's wall, 1.3× under s02's noise ⚠ | **MOVED 3.0 → 2.2** (iteration 2, G2): inert on the corpus sweep at every entity and polygon (its one visible effect — s02's WC basin edge pairing over two corner X symbols, 2.75/100 px — needed the 40 px cap and the 9 px floor too, both reverted, and is now caught by the far-side density rule) |
| 13 | COLLINEAR_OFFSET_TOL | W (true class is P) | 4 px (34 · 62 mm) | "same drawn line"; s01 hatch chains straddle 3.9–4.1 px | same-line pieces that MUST merge: s02 2.7–3.2 px (L2 at 0.67), s01 3.9–4.1 px — paper-space (s01's hatch pitch 4.05 = s02's) | thinnest real wall spacing that must NOT fuse: 75–100 mm = 8.9–11.8 px @1:50, 5.9 @1:100 (s03's 1:100 plan loses a room at 2.0× = 8 px), 3.2 @s13 | [0.8,1.5] (s02 0.67 ✗, s03 2.0 ✗, s12 1.5 improves) / [0.8,1.5], s17 0.5 ✗, s18 loses 6 at 0.5 and 1 at 2.0 (4 px fuses its 1:100 walls) / [0.5,2] / [0.8,1.5] (s01 loses 6 rooms at 2.0 = 8 px) · **✗ via interaction (18→4)** | 4 px UNSCALED with a W ceiling (never above ½ the thinnest wall: fine for f ≥ 0.45) | **MEASURED, NO CODE CHANGE** (iteration 2, G3b): s18's 47 mm partitions at 1:100 hold at 2.5 px and fuse at 2.75 (confirmed room lost) → ceiling 5.5 × f; unscaled 4.0 loses that room + 3 phantoms on s18 and +1 on s16, min(4, 6f) = 3.0 loses it too; the widest safe form min(4, 5f) changes no sheet and does not reach s01's 3.25 px need at 0.542. Stays 4 × f (1.37× under the ceiling); class row now "P true class, W ceiling, numerically W" |
| 14 | WALL_ANCHOR_SUPPORT_REACH_PX | W | 120 px (1016 · 1873 mm) | "one door opening"; s01's 59 px doorway = 921 mm | door openings: singles 640–950 mm, doubles 1.5–1.7 m, s02 3.3 m | page-wide window-board offsets (s17 vote flips at 150–200) | [0.5,2] on 10 sheets · ok | 120 | no — inert at entity level |
| 15 | ROOM_MIN_AREA_PX2 | ×f² | 2500 px² (0.18 · 0.61 m²) | "smallest closet" | smallest confirmed: s15 0.37 m² (closet, crop-verified; 2.0×), s11 0.54 (3×), s18 0.85, s17 0.88, s01 1.75 | dropped fragments at 1:50 up to 0.15–0.17 m² (s10/s17/s08/s04, 1.1×); s01's cushions 0.28 m² at 92.2 (1.3× under s15's closet) | [1.0,1.5] (s17 phantoms ≤0.8, one dies at 1.5; s12 F-3 at 1.25) / s11 L1 at 2.0, s16 F-2 and s18 F-7 at 2.0 (raising to 0.72 m² kills 15 known FP rooms on s12/s16/s18 for s11's one 0.54 m² room) / [0.5,2] / [0.5,1.5] (s01 loses its 1.75 and 2.25 m² rooms at 2.0 = 2.44 m²) · ok (interaction 18→8) | 2500 (keep) — 3600 (0.26 m², 1.44×) would kill 3–6 s12 FPs ⚠ | no ⚠ area cannot separate a cushion (0.28) from a closet (0.37) |
| 16 | ROOM_BLIND_WINDOW_MAX_AREA_PX2 | ×f² | 10 000 px² (0.72 · 2.44 m²) | worked instance above | s17 0.94 m² (1.31×, lost at 1.25) | s02 pockets 0.19–0.27 m²; other door-less window pockets 0.97–2.6 m², FP rooms at 2.0 m² (s16/s18) | [0.5,1.0] / [0.5,2] (s16 kills an FP at 2.0) / [0.5,2] / · · ok | 10 000 (keep) | no ⚠ classes overlap 0.94–2.6 m² — needs a second discriminator |
| 17 | ROOM_OPENING_SEAL_PX | W | 12 px (102 · 187 mm) | "reach into jambs the arc stopped short of" | jamb gap beyond the swing bbox: s01 8 px = 125 mm, s17 8 px = 135 mm (1:100 plan at identity), s05/s07 6 px @f.5 = 102 mm (1.0×!), s18 4 | tails re-fencing known phantoms: s03 two returned FPs at 1.5× (18 px = 152 mm) | [0.8,1.25] (s03 F2 at 1.5, s17 L1 at 0.67) / [0.8,·] s05·s07 (need = gate) / [0.5,2] / [0.8,·] · **✗** | 15–16 px (127–135 mm): s01@0.542 8.1–8.7 px ≥ 8 (1.0–1.08×); s03 untested between 1.25 and 1.5 ⚠ | **TRIED 15 → REVERTED to 12** (iteration 2, G2): the tail touch reach is SEAL + `ROOM_PLUG_HALF_WIDTH_PX`, and a hinge-less door's SWING-side edge whose ends fall within it of two walls becomes an interrupted plug — at 13–14 s01 room_0005 moves, at 14 s15 rooms 0023/0024 lose their door swings (−5.4k px² each), at 15 s02 BEDROOM 2 is notched around its "A" section marker; only 15 also cleaned s04's bedroom (+10k). Prerequisite: a swing-side veto for hinge-less doors |
| 18 | ROOM_PLUG_ANCHOR_WIN_PX | W | 24 px (203 mm) | s02 door 0121 garden pair (true 1:50) | jamb hug ≥ 0.5 of the window | — | [0.5,2] on 10 sheets · ok | 24 | no |
| 19 | ROOM_PLUG_HALF_WIDTH_PX | W | 5 px (42 · 78 mm) | "half a wall band" | half a thin wall 37–50 mm; at s13 5×0.367 = 1.84 px < the 2 px P standoff | — | [1.0,1.25] ONLY on s13 (room 1040,999 lost at 0.5/0.67/0.8/1.5/2.0), s17 L1 at 0.67 / f1 [0.5,2] / · | 5 with a P floor: max(5f, 3) | **DONE as max(5f, 2.0)** (iteration 2, G3c): the floor is the line-barrier standoff, not 3 (3 loses the s13 room); s13 11/11, verdicts identical, s13's plugs grow 0.16 px |
| 20 | ROOM_FOLD_STACK_NEAR_PX | W | 24 px (203 mm) | s02 folding chains (true 1:50) | — | — | [0.5,2] on 10 sheets incl. s02 · ok | 24 | no |
| 21 | ROOM_FOLD_JAMB_MIN_LEN_PX | W | 24 px (203 mm) | s02 | — | — | [0.5,2] on 10 sheets incl. s02 · ok | 24 | no |
| 22 | DOOR_MIN_SIZE_PX | W (floor 1) | 20 px (169 · 312 mm) | symbol extent, ratio 0.496 | smallest confirmed symbol: s13 36.4 px (841 mm, 5×), s11/s16 37.9 (641 mm, 3.8×), s01 43 (671 mm, 2.15×), s03's 1:100 plans at identity 44.6 (2.2×, lost at 2.0) | sub-16 px arcs → phantoms at ≤0.8 on s03/s17 | [1.0,1.5] / [0.5,2] / [0.5,2] / [0.5,1.5] (s01 loses 3 doors at 2.0 = 40 px: its arcs sit under the 43 px extents) · ok | 20 | no |
| 23 | DOOR_MAX_SIZE_PX | W | 200 px (1.69 · 3.12 m) | largest symbol | s02 double swing 108–110 px (lost at 0.5); s13 8 doors + 4 rooms lost at 0.5 (36.5 px cap); s05/s12 lose 2 rooms each at ≤0.8 (a door part 80–100 px @f.5 = 1.35–1.7 m feeding a plug) | s11 admits a 1.7–2.5 m arc at 1.5× (L1 F2); s18 loses 3 windows + 2 rooms at 1.5× the same way | [1.0,1.25+] / s05·s12 (0.8,1.25], s11·s18 [·,1.25] / [0.67,2] / · · ok | 200 | no ⚠ 1.0–1.25× both sides on s05/s11/s12/s18 |
| 24 | DOOR_SWING_LINE_DIST_PX | W | 15 px (127 mm) | arc corner ↔ line endpoint | — | — | [0.5,2] · ok | 15 | no |
| 25 | DOOR_POLYLINE_MAX_SEG_PX | W | 18 px (152 mm) | r·Δθ | — | — | [0.5,2] · ok | 18 | no |
| 26 | DOOR_ASSEMBLY_CONNECT_TOL_PX | W | 15 px (127 mm) | leaf↔arc reach | — | — | [0.5,2] · ok | 15 | no |
| 27 | DOOR_LEAF_LINE_ENDPOINT_TOL_PX | W | 5 px (42 mm) | leaf-line ↔ arc snap | — | s03 +1 door at 2.0; s17 loses a room at 1.5 (a door re-snaps at 7.5 px) | [0.5,1.25] / [0.5,2] · ok | 5 | no |
| 28 | DOOR_THRESHOLD_ENDPOINT_TOL_PX | W | 6 px (51 mm) | | — | — | [0.5,2] · ok | 6 | no |
| 29 | DOOR_DOUBLE_LEAF_GAP_PX | W | 12 px (102 mm) | | — | — | [0.5,2] · ok | 12 | no |
| 30 | DOOR_DOUBLE_LEAF_OVERLAP_PX | W | 5 px (42 mm) | | — | — | [0.5,2] · ok | 5 | no |
| 31 | DOOR_DOUBLE_LEAF_CENTER_TOL_PX | W | 8 px (68 mm) | | — | — | [0.5,2] · ok | 8 | no |
| 32 | DOOR_SLIDE_PANEL_MIN_THICKNESS_PX | W | 3 px (25 · 47 mm) | "thinner is a shower screen (2.0–2.5)" | panels: s01 parked leaf 3.0 px = 47 mm at 92.2, s02 ~6 px = 51 mm, s12 2.13 @f.5 = 36 mm (1.42×), s11/s16 8.1–8.25 = 137 mm | s02 shower screens 2.0–2.5 px = 17–21 mm → +1 phantom at ≤0.8 (1.2×) | [1.0,1.5] s02 (5 doors lost at 2.0 = 6 px: its panels ARE 6 px) / [0.5,2] / [0.5,2] / [0.5,1.0] (s01's parked leaf is exactly 3.0 px: door_0011 + 2 rooms lost at 1.25) · ok | 3 (keep; true 36 mm vs false 21 mm leaves 1.7× in world terms, but the px value sits 1.0× on s01 and 1.2× off s02's screens) ⚠ | no ⚠ knife-edge both ways |
| 33 | DOOR_SLIDE_PANEL_MAX_THICKNESS_PX | W | 20 px (169 mm) | | ≤ 8.25 px measured | | [0.5,2] · ok | 20 | no |
| 34 | DOOR_SLIDE_FLANK_GAP_MIN_PX | W | 0.5 px (4 · 8 mm) | s01 flank gap 0.75 px | s01 door_0011 (+2 rooms) lost at ≥1.5 (0.75 px floor = its own gap) | | [0.5,1.25] s01 / [0.5,2] elsewhere · ok | 0.5 | no (s01 knife-edge, 1.5×) |
| 35 | DOOR_SLIDE_FLANK_GAP_MAX_PX | W | 12 px (102 mm) | GD9 2.9–6.1 px = 25–52 mm (s02) | 2× | | [0.5,2] · ok | 12 | no |
| 36 | DOOR_SLIDE_POCKET_TIGHT_GAP_PX | W | 2.5 px (21 mm) | s04 1.1/1.2 px = 9–10 mm | 2× | | [0.5,2] · ok | 2.5 | no |
| 37 | DOOR_SLIDE_PARK_GAP_MAX_PX | W | 6 px (51 · 94 mm) | s01 0.75 px = 12 mm | 4–8× | at ≥1.5 (9 px) s01's parked leaf matches a wrong band and door_0011 + 2 rooms are lost | [0.5,1.25] s01 / [0.5,2] elsewhere · ok | 6 | no |
| 38 | DOOR_SLIDE_PARK_BAND_MIN_TH_PX | W | 2 px | | | | [0.5,2] · ok | 2 | no |
| 39 | DOOR_SLIDE_PARK_BAND_MAX_TH_PX | W | 20 px (169 mm) | s01 band 7.0 px = 109 mm | 1.55× | | [0.5,2] · ok | 20 | no |
| 40 | DOOR_SLIDE_PARK_JAMB_TOL_PX | W | 8 px (68 · 125 mm) | s01 overhang 3.0 px = 47 mm | 1.44× in world terms (survives 0.5×: 4 px > 3) | | [0.5,2] · ok | 8 | no |
| 41 | DOOR_FOLD_JAMB_ANCHOR_TOL_PX | W | 6 px (51 · 94 mm) | s01 open_v door_0012: 3.4/3.6 px = **53–56 mm at 92.2** | s01 needs ≥ 3.6 px (L3 at 0.5, ok at 0.67) | nothing up to 12 px on s01 or s02 | s01 [0.67,2] · **✗ (3.25 < 3.4)** | 10 px (85 mm): 1.5× over 56 mm, ≥2× under the first false match | **MOVED 6 → 10** (iteration 2, G1): entity set identical on every sheet; s01 door_0012's bbox top extends 7 px along the jamb (the 1.5 px wall face ending 7.77 px from the tip now anchors too; IoU 0.89, metrics and rooms unchanged) |
| 42 | DOOR_FOLD_JAMB_LINE_MIN_LEN_PX | W | 15 px (127 mm) | | | | [0.5,2] · ok | 15 | no |
| 43 | DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX | W | 6 px (51 · 94 mm) | s01 lateral offsets 1.2–1.8 px = 19–28 mm | 3.3× | | [0.5,2] · ok | 6 | no |
| 44 | WINDOW_MIN_WIDTH_PX | W (floor 1) | 14 px (119 · 219 mm) | "bonus ~20 px" | confirmed widths: s02 20.5 px = 174 mm (1.46×), s03 17.2 (1:100 plan at identity, 291 mm; lost at 1.25×), s16 11.6 @f.5 = 196 mm (1.66×), s18 16.5 = 279 mm | FP windows from 16.4 px = 278 mm (s18) — same width as the real ones | [0.5,1.0] s03, [0.5,1.25] s02 (L1 at 1.5 = 21 px) / [0.5,2] / [0.5,2] / [0.5,2] · ok | 12 px (102 mm): 1.7× (s02), 1.4× (s03 px) | **MOVED 14 → 12** (iteration 2, G1): corpus sweep identical on every sheet |
| 45 | CROSS_WALL_EXPAND_PX | W | 20 px (169 · 312 mm) | p90 need 9.6 px @1:50 | need of single_line_leaf doors (the tier the gate decides): s01 12 px = 187 mm (0.9× in world terms!), s18 7.5 @f.5 = 127 mm (1.33×), s10 47 mm; other tiers survive the penalty (s02 331 mm, s14 311) | no confirmed FP door is no_wall | [0.5,1.5] (s17 +1 phantom door at 2.0 = 40 px) / (0.67,1.5] (s18 loses its 7.5 px-need door at 0.67 = 6.7 px) / [0.5,2] / (0.5,2] · **✗** | 24–28 px (203–237 mm): s01@0.542 13–15 px vs 12 (1.08–1.27×) ⚠ | **MOVED 20 → 24** (iteration 2, G2): inert on the corpus sweep at every entity and polygon; comment records that "need" is the distance to the nearest DETECTED wall |
| 46 | CROSS_OPENING_ENDPOINT_TOL_PX | W | 12 px (102 mm) | opening endpoints on a centerline | sets only the "on_wall_centerline" label — no confidence effect | — | [0.5,2] · ok | 12 | no — inert by construction |
| 47 | CROSS_WALL_RUNS_THROUGH_MARGIN_PX | W | 12 px (102 mm) | boost-only gate | the boost is withheld from 4/4 s01, 11/15 s03, 10/12 s18 real windows | fires on 3/3 s15 FP windows, 3/12 s18 | [0.5,2] · ok | 12 | no — weak, boost-only |
| 48 | CROSS_WALL_RUNS_THROUGH_BAND_PX | W | 8 px (68 mm) | as 47 | | | [0.5,2] · ok | 8 | no |
| 49 | CROSS_DOOR_EXPAND_PX | W | 20 px (169 · 312 mm) | door dilation vetoing windows | phantom windows on door ink lie ≤ 2.8 px from the door (s01), 0 (s15) — 7× under the gate | real windows 2–8 px from doors (s18 2.0, s11/s16 3.6, s10 4.0, s17 7.7) survive only through the 10 % cover rule and the wall-run exemption; s03 loses 1 window at 1.25, 2 at 1.5; s17 1 at 1.5 | [0.5,1.0] s03, [0.5,1.25] s17 / [0.5,2] / [0.5,2] / [0.5,2] · ok | 10 px (85 mm): 3.6× over the true class, halves the exposure of the false one | **MOVED 20 → 16, not 10** (iteration 2, G1): the corpus sweep at 10 uncovered a false class the one-field ablation could not see — s18's 100 mm DOOR LINING box (6×49 px at f=0.5) touching door_0271's hinge corner, covered only diagonally, needs 5.17 px scaled = 10.3 px at 1:50 to reach the 10 % cover rule and came out as a 0.75 window at 10 (attributed by single-field revert: only the reach restores it). 16 = 135 mm: 1.55× over the lining, 1.56× under s03's 25 px loss; at 16 the hinge-jamb exemption decides s10/s17/s18's windows (4.0/7.75/2.0 px), at 10 none |
| 50 | CROSS_DOOR_FALLBACK_EXPAND_PX | W | 8 px (68 mm) | joinery FPs overlap fallback ink at ≤ 6 px (s02) | s02 +1 phantom window at ≤0.67 (5.4 px) → 1.33× | | [0.8,2] s02 · ok | 8 | no |

Rows 24–31, 33–40, 42–43, 46–48: no sheet in the sweep changed at any
multiplier in [0.5, 2.0] — the gate never decides an entity on this corpus,
so their world meaning cannot be measured here; they keep their s01/s02
calibration (s01-measured features listed are 1.84× larger in world terms
than their 1:50 label, e.g. row 40's 47 mm, row 43's 19–28 mm).

## What the census says

1. **Only 7 of 50 fields are load-bearing on the corpus** (rows 1, 3, 11, 12,
   13, 15, 17) plus 4 with one-sheet knife-edges (4, 19, 23, 32). 39 fields
   are inert across [0.5, 2] — the handoff's suspicion that headroom masks
   most of them is confirmed, but for the load-bearing ones the headroom is
   **≤ 1.25× on at least one side**, i.e. they are *censored* by the gate
   (the distribution ends at the gate on many sheets: face length 11.0–11.2 px,
   overlap 12.0, wall thickness 35.5–36.0, weak run 31, hatch length 51 vs 48).
2. **The 1:50 references are mostly right in world terms; s01 is the outlier**
   because its paper conventions are 1:50-standard while its ink is 1:92.2:
   the s01-derived rows (3, 4, 17, 41, 45, 40, 43) carry world values 1.84×
   their label — 390 mm party wall, 613 mm breast, 125 mm jamb gap, 53–56 mm
   fold anchor, 187 mm cross reach. Rows 17, 41, 45 are the ones whose 1:50
   reference is genuinely below s01's world value (0.9–1.0×); rows 3/4 are
   covered at 1:50 by the material tiers.
3. **Six rows are "discriminator, not number"** (⚠): 3 (300 mm wall vs 300 mm
   slot vs 313 mm paving), 11 (global hatch cap vs T·√2), 12 (density follows
   the hatch pitch), 13 (paper true class, world false class), 15/16 (area
   overlaps between rooms and pockets), 17 (tail reach both sides ≤ 1.25×).
4. **Region scale**: s03 and s17 run at identity; their 1:100 plans supply
   several of the borderline cells above (s03 windows 17.2 px, doors 44.6 px,
   5.8 px walls fused at 2×; s17's 8 px jamb gap). The per-region factor
   (findings §6) removes those cases without touching a constant.
5. **s01 at 0.542** cannot be made green by moving references alone: rows 17,
   41, 45 fix with the proposed values; row 3 (MAX_THICKNESS) needs the thick
   tier to accept short hatched pieces (36 px, 3 marks) or a cap of ≥ 47 px
   (400 mm) — which the s11 slot forbids; and row 13 (COLLINEAR) needs the
   paper-space reclassification. So `_gate_denominator`'s abstention stays
   until rows 3/11/13 are restructured.

## Proposed iteration-2 groups (for the user's verdict — nothing changed yet)

- **G1 — safe reference moves (world-correct, ≥1.3× both sides on the sweep):**
  WINDOW_MIN_WIDTH 14→12; CROSS_DOOR_EXPAND 20→10; DOOR_FOLD_JAMB_ANCHOR_TOL
  6→10 (pending s01's upward cells); WALL_THROUGH_HATCH_MAX 64→72;
  WALL_THICK_MATERIAL_MAX 48→56.
- **G2 — s01-correcting moves with thin margins (need the user's call):**
  ROOM_OPENING_SEAL 12→15; CROSS_WALL_EXPAND 20→24; WALL_FACE_MIN_LEN 11→9;
  WALL_WEAK_MATERIAL_PER_100PX 3.0→2.2; WALL_MAX_THICKNESS 36→40.
- **G3 — class fixes, not numbers:** COLLINEAR_OFFSET_TOL → P (4 px unscaled)
  with a W ceiling; ROOM_PLUG_HALF_WIDTH → P floor max(5f, 3); WALL_HATCH_MAX_LEN
  → per-band T·√2 mark cap (keep 48 as the winder ceiling).
- **Leave alone (inert or discriminator-bound):** everything else, incl.
  ROOM_MIN_AREA, ROOM_BLIND_WINDOW, DOOR_MAX_SIZE, DOOR_SLIDE_PANEL_MIN.

All sweeps complete: s01, s02, s03, s05, s07, s12, s13, s17 (307 configs
each) and the key subset on s11, s16, s18 (36 each). On s18 the three caps
moved together remove 2 known FP rooms at 0.8, 1.25 and 1.5 with nothing lost;
its other cells are folded into rows 13, 15, 23 and 45 above.
