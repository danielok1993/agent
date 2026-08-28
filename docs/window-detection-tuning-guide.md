# Window Detection — Tuning Guide

Reference for the architectural window-detection pipeline in `detection/windows.py`
plus the door-overlap cross-exclusion in `detection/postprocess.py`. Mirrors the
structure of `door-detection-tuning-guide.md`.

**Read first if you are about to change window detection.**

---

## 1. The signature (cap-anchored)

A window opening is drawn as a **pair of short perpendicular cap lines** (the
jambs) facing each other across the opening width, with one or more parallel
**glazing** lines (the panes) spanning the gap between them.

```
   cap                                   cap
    │  ╶──────── glazing pane ────────╴  │     ← horizontal window
    │  ╶──────── glazing pane ────────╴  │       (1–3 panes; 5-1133 Window A has 3,
    │  ╶──────── glazing pane ────────╴  │        Window B has 2, no centerline)
```

**The cap pair is the only feature stable across drawing standards.** The
glazing-line count (1–3), spacing (1–8 px) and pane depth all vary by drafting
style, so we anchor on the facing cap pair and treat the glazing band as
confirmation — rather than clustering the (variable) glazing first.

This is the v2 detector. History:
- v0 "group any 2–6 parallel lines 3–50 px apart" — missed real windows, flooded 88 FPs on 5-1133.
- v1 "glazing-rectangle" (cluster ≥3 equal-length parallel lines + caps) — clean 4/4 on floor-plans but **over-fit**: missed *every* 5-1133 window, whose panes are wider-spaced (~7 px), thicker (~14 px), unequal-length, and sometimes only 2.
- v2 cap-anchored (current) — one rule catches floor-plans' 4 and 5-1133's ground-truth windows. Driven by ground truth on both PDFs (see §5).
- v2.1 framed multi-light extension — caps may also be small bar-shaped `re`/`qu`
  **block caps**, and a mullion-segmented center glazing line re-joins across
  mullion blocks (§1b). Adds 5-1133 W8 (three-light frame, one label ⇒ one
  window) without touching the v2 line-cap path.

### 1b. Framed multi-light windows (5-1133 W8)

Some frames draw the jambs and mullions as thin quad/rect OUTLINES instead of
cap lines, and the center glazing line in per-light segments:

```
   █╶────────────────── rail ──────────────────╴█
   █╶── center ──╴██╶── center ──╴██╶── center ╴█    ← 3 lights, one W8 label
   █╶────────────────── rail ──────────────────╴█
    ▲ end cap (qu)    ▲ mullion pair (qu × 2)
```

Two extensions make this a window under the same cap-anchored pairing:

1. **Block caps** (`_block_cap_records`) — a `re`/`qu` whose long side is
   cap-length, thickness ≤ `WINDOW_BLOCK_CAP_MAX_THICK_PX` and aspect ≥
   `WINDOW_BLOCK_CAP_MIN_ASPECT` is reduced to its long axis (midpoints of its
   short edges, order/rotation-free) and joins the cap pool. A SQUAT block
   (aspect below that, down to ~1.0 — the crosshatch/insulation-box range)
   joins too, flagged `squat`, but pairs only when at least
   `WINDOW_SQUAT_CAP_MIN_PANES` (3) panes terminate on it and never bridges a
   mullion chain: s04's BATHROOM 01 outer-wall window draws its head and sill
   as 9.8×7.1px `qu` blocks (aspect 1.38) with three 4.9px-pitch panes running
   exactly between them, while a hatched wall reads as 2 panes (its faces) and
   a hatch box never has a repeated-pitch band ending on it — aspect alone
   cannot separate the two (corpus census 2026-08-26: squat blocks on 14
   sheets, 91 on s14, 30 on s05; the full sweep added exactly one window,
   s04's, and no other entity changed). For bar-shaped caps the aspect gate
   keeps square-ish crosshatch/insulation boxes out; the cross gate
   (`WINDOW_BLOCK_CAP_CROSS_RATIO`) drops blocks with an X drawn through them —
   a crossed box is a post/column symbol (the 5-1133 bathroom shower-screen
   end post), never a jamb.
2. **Mullion-bridged glazing chains** (`_merge_mullion_chains`) — same-perp
   collinear glazing segments merge across a gap ≤ `WINDOW_MULLION_GAP_MAX_PX`
   **only when a block cap physically occupies the gap** (perp inside it, span
   covering the pane's offset). Requiring the bridge is what keeps dashed
   linework from chaining into phantom glazing. Chains are appended to the pool
   (members stay, so sub-light cap pairs still fail span tests as before); the
   chain's summed length outranks its members in `_dedupe_by_perp`.

The rails span cap-to-cap, the merged center chain spans cap-to-cap, and the
three offsets form a normal tight band — so W8 detects ONCE, end-cap to
end-cap, never per light (rails overshoot every sub-light cap pair by far more
than `WINDOW_SPAN_OVERSHOOT_PX`). The window's own quads (end caps, mullion
blocks) ride in `used_idxs`, so the band-interior clutter gate does not count
the frame's structure against itself; foreign quads still count. Evidence
carries `lights` (chain member count, 3 for W8).

### 1c. Bay / corner frames — the square corner post (s10 lounge)

A glazed frame that turns a corner is closed at that end not by a jamb but by
the SQUARE block standing where the two perpendicular bands meet:

```
    ┌──────────────────── rail ─────────────╴█
    │ post ╶───────────── centre ───────────╴█    ← the frame going right
    ├──┬───────────────── rail ─────────────╴█
    │  │
    │  │  ← the frame going down shares the same post
```

Two facts follow from that drawing, and both had to be read for the frame to
detect (measured on s10's lounge bay, three frames around one bay: the two
short returns and the long face):

1. **The post's side is the band depth.** The band's two outer rails ARE the
   post's faces, so a square block is a corner post exactly when its side
   equals the depth of the band ending on it (s10: 11.75 px against 11.75 px,
   difference 0.00 on all four posts). So a square `re`/`qu` is admitted to the
   cap pool above `WINDOW_BLOCK_CAP_MAX_THICK_PX` when it is square within
   `WINDOW_CORNER_POST_MAX_ASPECT`, and its pairing is then gated on
   `WINDOW_CORNER_POST_DEPTH_TOL_PX` against the band it closed. A hatch or
   fixture box standing at a band's end carries no such identity, and the
   post is squat by aspect, so the 3-pane `WINDOW_SQUAT_CAP_MIN_PANES` rule
   applies on top of it. A square has no long axis — which of the two the
   midpoint reduction picks is an artefact of the exporter's point order — so
   a post enters the pool as BOTH of its axes; it genuinely caps both frames.
2. **Glass stops at the jamb's FACE.** A line cap has no thickness, so its face
   is its axis and `WINDOW_SPAN_COVER_TOL_PX` measures from there; a block cap's
   inner face stands half the block's thickness inside it. s10's centre pane
   runs post face to bar-jamb face and so falls 5.875 px short of the 11.75 px
   post's centre line — past the 4 px cover tolerance from the axis, exactly on
   it from the face — leaving a 2-pane band that then failed the 12 px 2-pane
   jamb gate. `_spanning_glazing` therefore offsets each cap's cover bound by
   that cap's own half-thickness.

Corpus census 2026-08-28 (square `re`/`qu`, side 8–16 px — the class the
thickness relaxation admits): 68 on nine sheets (s02 19, s17 11, s18 10, s04 9,
s15 7, s08 5, s10 4, s14 2, s01 1). The full sweep over both rules changed
exactly two entities on the corpus — s10's two bay returns — and no room,
door or window anywhere else, in shape or verdict.

## 2. Pipeline shape

`detect_windows(paths)` (geometry only, no wall/door dependency):

0. **Visible linework only** (`_line_records` via `geometry._stroke_is_visible`)
   — an `l` item is a candidate cap/pane (or clutter line, or block-cap cross
   stroke) only when it is a DRAWN line. A plain stroke (no fill) always is,
   hairline or heavy. A filled path's `l` items are its polygon boundary, and
   the reader only sees a line there when the stroke contrasts with the fill:
   no stroke colour (fill-only — the Vectorworks polygon signature) or a stroke
   in the fill's own colour (the seam-hiding outline AutoCAD-family exporters
   give solid hatches, whatever its width) is invisible area, not linework.
   Why it matters: exporters TRIANGULATE solid fills, so a wall band's gray
   fill arrives as its two faces, its two end edges AND the triangles' shared
   diagonal — which on a 6–8 px band lies 2–5° off the faces, inside
   `WINDOW_ANGLE_TOL_DEG`. Read as lines, that is two panes + a mid-band third
   pane between two caps: the exact 3-pane signature, once per wall segment
   between crossing walls, all invisible on the page. Measured on s03: 21
   phantom windows (0.67–0.82), every cap and pane an invisible fill edge;
   the same edges also entered real windows' pane bands and cap pools (a
   face edge joining the band drags foreign shapes into the interior scan; a
   fill end-edge pairs as a jamb), so two real s03 glazing frames surfaced
   only once they were gone — one had been read as its 35 px wall opening
   instead (3863,2184–4039,2219 → the 12 px frame at y 2201–2213), one not
   at all (1304,1339–1392,1345). Removing them also cleared 10 recorded FPs
   on s12, 3 on s20 and 1 on s08 with no loss anywhere. The corpus holds NO filled path with a visibly different stroke
   colour, so the visibility rule and a plain "filled ⇒ not linework" rule
   are indistinguishable today; visibility is what the drawing actually shows,
   so it is the rule. `re`/`qu` items are unaffected — a filled bar is a
   visible block and still becomes a block cap.
1. **`_axis_lines`** — split `l` primitives into horizontal / vertical pools
   (within `WINDOW_AXIS_TOL_PX` of an axis). Each record carries `perp` (the
   constant coordinate) and `span` (lo, hi along the run axis). For a horizontal
   window the caps are the vertical pool and the glazing the horizontal pool;
   vice-versa for a vertical window.
2. **`_find_openings`** — sort caps (the short perpendicular pool, length in
   `[WINDOW_CAP_MIN_LEN_PX, WINDOW_CAP_MAX_LEN_PX]`) by position and pair them.
   A pair is an opening when: gap ∈ `[WINDOW_MIN_WIDTH_PX, WINDOW_MAX_WIDTH_PX]`;
   the caps are similar length (`WINDOW_CAP_LEN_RATIO`) and truly facing (their
   perp-extents overlap, `WINDOW_CAP_ALIGN_OVERLAP`); and a glazing band bridges
   the gap (`_spanning_glazing`).
3. **`_spanning_glazing`** — collect glazing lines whose perp sits within the
   caps' combined facing extent (`WINDOW_SPAN_PERP_TOL_PX`) and whose run-span
   covers the gap (reaches within `WINDOW_SPAN_COVER_TOL_PX` of each cap's FACE —
   its axis for a line cap, half a block's thickness inside it for a block cap,
   §1c) without
   overshooting it by more than `WINDOW_SPAN_OVERSHOOT_PX` (this rejects long
   wall lines that merely cross the gap). De-dupe collinear duplicates by perp
   (`WINDOW_GLAZING_DISTINCT_EPS`), then take the tightest **band** via
   `_tight_band` (consecutive panes ≤ `WINDOW_GLAZING_ADJ_SPACING_PX`, total
   depth ≤ `WINDOW_GLAZING_THICKNESS_PX`). Require ≥ `WINDOW_MIN_GLAZING_LINES`
   distinct panes.
4. **2-pane jamb gate** — a 2-pane opening (no centerline) is geometrically a
   thin wall; accept it only when the caps are substantial
   (`cap_len ≥ WINDOW_TWO_LINE_MIN_CAP_PX`). Small-cap windows must show ≥3 panes.
4b. **Band-interior clutter gate** (`_band_interior_clutter`) — a real window's
   glass is clear: nothing sits BETWEEN the panes. An insulation-hatched wall,
   though, gets read as a 2-line band whose two "panes" are the wall's two faces,
   with the crosshatch fill right between them. Reject when the **band interior**
   carries clutter — measured in the oriented rectangle `u ∈ [cap1, cap2]` (the
   gap between caps) × `v` across the pane band (± `WINDOW_INTERIOR_BAND_PAD_PX`),
   excluding the band+cap lines:
   - `shapes` — non-line primitives (`re`/`qu`/`c`) with any point in the region
     (`> WINDOW_INTERIOR_SHAPE_MAX`): crosshatch boxes / insulation arcs.
   - `oblique` — lines in the region parallel to neither glazing nor caps
     (`> WINDOW_INTERIOR_OBLIQUE_MAX`): line-drawn insulation hatch.

   **Why the oriented band, not the bbox** — this is what keeps DIAGONAL windows
   alive (the v1 axis-bbox version killed all four 5-1133 diagonals): a 45°
   window's axis-aligned bbox is a big square that sweeps in neighbouring
   linework, and its gray jamb caps are filled `re`/`qu`/`c` shapes — but those
   sit at the opening ENDS (`u` outside `[cap1, cap2]`), never between the panes.
   Solid-filled blocks (w17/w18) and the recess niche (w26) carry their
   distinguishing clutter at those same ends, so no *interior-clutter* gate can
   reject them without also killing the diagonals — they fall to gate 4c instead.
   Colour / fill-brightness would separate them but is not uniform across PDFs.
4c. **Tight-pair interior gate** — a 2-pane band whose panes hug closer than
   `WINDOW_TIGHT_PAIR_GAP_PX` (2.75 px) is ambiguous: either a narrow
   double-glazing line (floor-plans true windows: 1.75–2.0 px gaps) or ONE
   material edge drawn as two strokes — a solid-wall step's outline + fill-edge
   (w17/w18), a niche box's side + shelf line (w26), a detail layer boundary, an
   RWP corner square. The gap ranges overlap, so the tie-break is **where the
   band sits in the jambs**: real glass runs INTERIOR to both caps, each jamb
   extending ≥ `WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX` (1.5 px) beyond the band on
   BOTH sides (floor-plans tight pairs: 4.3–8.6 px in every orientation frame);
   a doubled edge terminates AT its box/step corners, so the cap ends exactly on
   the outer stroke (every 5-1133 FP reading: ≤ 0.0 px in every frame). Plain
   overlap can't separate the two — a corner-exact cap still overlaps the band
   fully; only the beyond-band margin does. Pairs ≥ 2.75 px apart are real pane
   pairs (5-1133 diagonal window_0022: 3.5 px, band AT the cap end — exempt) and
   ≥3-pane bands are exempt (repeated equal spacing is already the signature;
   true 3-pane bands run as tight as 1.5 px).
5. bbox = union of caps + glazing band; confidence scored; emit.
6. **`_dedupe_openings`** — greedy NMS over duplicate cap pairs (prefer more
   panes, then tightest bbox; drop a candidate whose center sits inside a kept
   one).

Then, in `run_heuristics` → `_resolve_door_window_conflicts(doors + windows)`:
drop any window the (dilated) door bbox **materially** covers — at least
`CROSS_DOOR_MIN_WINDOW_COVER` of the window's area, so a distant door whose 20 px
dilation merely grazes a window corner is not a conflict. Door detection is
reliable; this is the primary false-positive filter and **does not depend on
walls**.

One exemption (`_window_in_door_wall_run`, `CROSS_DOOR_WALL_RUN_TOL_PX` 4 px):
the door ink that reads as glazing lies *inside* the door's footprint, so a
window whose **undilated** bbox is clear of the door's, whose glazing runs
parallel to one of the door's **hinge edges** (`rooms._swing_hinge_edges` —
the wall plane passes through the hinge) and whose band contains that edge's
line within the tolerance is joinery standing in the same wall run beyond the
jamb, and the dilation must not reach it. Measured on s10: the hall window
(217–229 × 788–864, three panes at 6 px pitch in a 12 px frame) stands 4 px
above door_0009's hinge jamb, whose edge x=229 lies exactly on the inner pane;
the 20 px dilation covered 21 % of the 12×76 px band and killed the wall run's
only seal, so the hall and kitchen leaked to the page exterior and detected no
room. The false class never matches: s01 door_0015's four flanking phantoms
(garden pair, no derivable hinge) run perpendicular to the wall or lie 51 px
off its plane at the parked leaves' tips, and every door-ink phantom inside a
footprint overlaps the raw bbox (cover 0.19–1.0). Corpus census 2026-08-27 at
each sheet's scale factor: the exemption fires on six windows — s10, s11 (WC
window under the utility door's jamb), s16, s17, s18 — each a 2–3 line frame
in the wall band beside a swing door's hinge jamb, and no other veto changes.

## 3. Why both filters are needed (floor-plans.pdf)

23 raw cluster+cap candidates reduce to the 4 real windows via two orthogonal cuts:

| Filter | Removes | Keeps |
|---|---|---|
| `n >= 3` glazing lines | 5 `n==2` fixtures/doors (toilet, sink, cupboard, balcony door) | all 4 windows (`n==3`) |
| no door overlap | 14 door-related (garden/double doors, leaves, a wall on a door) | all 4 windows (clear of doors) |

Neither alone is sufficient; together they give 4/4 windows, 0 false positives.

## 4. The constants

`detection/windows.py`:

| Constant | Value | Rationale |
|---|---|---|
| `WINDOW_AXIS_TOL_PX` | 1.5 | Max off-axis deviation to call a line H/V. Glazing/caps are axis-true; diagonal hatch excluded. |
| `WINDOW_CAP_MIN_LEN_PX` | 3.0 | Tiny caps exist (5-1133 bonus window jambs ~5 px). |
| `WINDOW_CAP_MAX_LEN_PX` | 34.0 | Caps are short; longer perpendiculars are walls. 5-1133 Window B caps overshoot to 30 px. |
| `WINDOW_CAP_LEN_RATIO` | 0.60 | The two caps must be of similar length. |
| `WINDOW_CAP_ALIGN_OVERLAP` | 0.60 | Their perp-extents must overlap — truly facing, not two offset stubs. |
| `WINDOW_MIN_WIDTH_PX` | 14.0 | Opening width (gap between caps). Smallest real ≈ 20 px (bonus). |
| `WINDOW_MAX_WIDTH_PX` | 280.0 | 5-1133 W8 (three-light frame) is 268 px; caps out long wall/decoration runs. |
| `WINDOW_BLOCK_CAP_MAX_THICK_PX` | 8.0 | Bar thickness for a `re`/`qu` block cap (W8 end caps 6.0, mullions 5.5). |
| `WINDOW_BLOCK_CAP_MIN_ASPECT` | 1.8 | Long/short side of a block cap; square crosshatch/insulation boxes (~1.0–1.4) never enter the cap pool. |
| `WINDOW_SQUAT_CAP_MIN_PANES` | 3 | A block under the bar aspect (squat, the hatch-box range) pairs only when this many panes terminate on it (s04 outer-wall window: 9.8×7.1px blocks, three 4.9px-pitch panes); squat blocks never bridge mullion chains. |
| `WINDOW_CORNER_POST_MAX_ASPECT` | 1.2 | A block over the bar thickness may still be a jamb as a bay/corner frame's SQUARE corner post (§1c). Two-sided and tight — a post is square by construction; s10's four lounge-bay posts are 11.75×11.75 px, aspect 1.000. It enters the pool as both of its axes and is squat, so the 3-pane rule applies. |
| `WINDOW_CORNER_POST_DEPTH_TOL_PX` | 2.0 | …and its side must EQUAL the depth of the band that ends on it — the band's rails are the post's own faces (s10: 11.75 vs 11.75, difference 0.00 ×4). This is what a hatch/fixture box at a band's end never carries; 2 px absorbs pen rounding. Corpus census of square `re`/`qu` at side 8–16 px: 68 on nine sheets. |
| `WINDOW_BLOCK_CAP_CROSS_RATIO` | 0.75 | A line ≥ this fraction of the block's diagonal with both endpoints inside it is an X stroke → the block is a crossed post/column symbol, not a jamb (killed the 5-1133 shower-screen candidate at the source). |
| `WINDOW_MULLION_GAP_MAX_PX` | 14.0 | Max glazing-segment gap a mullion block may bridge (W8 gaps are 11.5 px). |
| `WINDOW_GLAZING_THICKNESS_PX` | 16.0 | Max perp-spread of the glazing band. Window A ≈ 14 px. |
| `WINDOW_GLAZING_ADJ_SPACING_PX` | 8.5 | Max gap between adjacent panes. Window B ≈ 7.6 px. **Rejects stair treads / widely-spaced parallels.** |
| `WINDOW_GLAZING_DISTINCT_EPS` | 1.5 | Panes closer than this in perp are one pane (collapses collinear duplicates / double-drawn faces). |
| `WINDOW_MIN_GLAZING_LINES` | 2 | ≥2 distinct panes must span the gap. 2 is the minimum real (Window B); single-line openings are too wall-like (see §6). |
| `WINDOW_TWO_LINE_MIN_CAP_PX` | 12.0 | A 2-pane opening needs real jamb caps (~20–30 px) to outrank a thin wall / fixture sliver. **Small-cap windows must show ≥3 panes** (the bonus). |
| `WINDOW_TIGHT_PAIR_GAP_PX` | 2.75 | 2-pane bands tighter than this face the interior test (§2 4c). True tight pairs: floor-plans 1.75–2.0 px; doubled-edge FPs: 1.6–2.5 px (ranges overlap → gap alone can't separate). Pairs ≥ this are real (5-1133 window_0022 3.5 px, floor-plans 3.25/3.3 px). |
| `WINDOW_TIGHT_PAIR_JAMB_MARGIN_PX` | 1.5 | A tight pair must run interior to BOTH caps with this much jamb beyond the band on BOTH sides. True: 4.3–8.6 px; box/step-corner FPs: ≤ 0.0 px in every orientation frame (the cap terminates ON the outer stroke). |
| `WINDOW_SPAN_COVER_TOL_PX` | 4.0 | A glazing line may fall short of each cap's FACE by this and still "span" the gap. A line cap's face is its axis; a block cap's is half its thickness inside it, because glass stops at the jamb face (s10's bay centre pane: 5.875 px short of the 11.75 px post's axis, 0.0 short of its face — §1c). |
| `WINDOW_SPAN_OVERSHOOT_PX` | 11.0 | …and run at most this far PAST each cap. Confirmed windows' overshoot tails reach 10.50 px (corpus-measured 2026-08-13); the s12/s18/s20 phantom families sit at 11.75–11.98; **walls run hundreds past** — this is what stops long wall lines being read as glazing (and inflating bboxes). |
| `WINDOW_SPAN_PERP_TOL_PX` | 2.0 | Glazing perp may sit this far outside the cap facing-extent. |
| `WINDOW_INTERIOR_BAND_PAD_PX` | 1.5 | Widen the pane band by this (per side, along v) before scanning, so a rail drawn a hair outside the band still bounds the hatch. |
| `WINDOW_INTERIOR_SHAPE_MAX` | 1 | Max non-line primitives (`re`/`qu`/`c`) BETWEEN the panes. >1 ⇒ crosshatch / insulation fill. True windows (axis + diagonal): ≤1 (a stray jamb-corner poke); hatched FP: 2–7. |
| `WINDOW_INTERIOR_OBLIQUE_MAX` | 2 | Max lines between the panes parallel to neither glazing nor caps (line-drawn hatch). True windows: 0; hatched FP: up to 2 (caught by shapes), more on line-only hatch. |
| `WINDOW_MIN_CONFIDENCE` | 0.50 | Matches `OFFLINE_MIN_CONFIDENCE["window"]`. |

`detection/postprocess.py`:

| Constant | Value | Rationale |
|---|---|---|
| `CROSS_DOOR_EXPAND_PX` | 20.0 | Dilate door bbox before testing window overlap. Matches `CROSS_WALL_EXPAND_PX`. |
| `CROSS_DOOR_MIN_WINDOW_COVER` | 0.10 | Door must cover ≥10% of the window's area to suppress it. A dilated-corner graze from a distant door is **not** a conflict (was wrongly killing 5-1133 Window A). |
| `CROSS_DOOR_MIN_CONFIDENCE` | 0.40 | Doors at/above this get the full 20 px veto reach. Fallback-tier doors (`DOOR_FALLBACK_CONFIDENCE` 0.35) often ARE window-like ink (glazing mullions, sliding panels, joinery slats), so a window reading the same ink still yields to them — but only near that ink, never 20 px out: on 5-1133, mullion strips ending 10 px above W8 projected their veto onto its band and killed it. |
| `CROSS_DOOR_FALLBACK_EXPAND_PX` | 8.0 | Veto reach of a fallback-tier door. Measured on 5-1133: the joinery FPs a fallback veto rightly kills — (1072,740) slats, (999,890) recess column — overlap its ink at ≤6 px dilation; W8 stays clear up to ~17 px. 8 px sits between with margin both ways. |

Confidence: base `0.62`, `+0.05` per glazing pane beyond 2, `+layer_prior` (or
`+0.10` weak layer hint), capped `0.90`. Layer keywords match exact tokens,
singular or plural (`WINDOWS`, `EXISTING_WINDOWS` on s03/s06/s13/s17 — see
`detection/layers.py`), and only when the layer names exactly one element
class — s04's `RR_New Doors and Windows` names two and hints at neither
(`LAYER_CLASS_KEYWORDS`); at the 0.90 cap the plural fix changed no window
verdict on the corpus. `_cross_validate` subtracts the no-wall
penalty when walls are enabled.

## 5. Reference data — current detection state (regression target)

### 5.1 floor-plans.pdf (offline, walls on/off both give 4)

Exactly **4 windows** under `run_heuristics` (walls on/off both give 4):

| bbox (x0,y0,x1,y1) | orient | notes |
|---|---|---|
| 955, 811 — 961, 889 | V | "W4" — 3 panes, caps 6.5 px (thin wall) |
| 867, 896 — 923, 918 | H | "W3" — panes ~1 px apart → collapse to n=2, caps 22 px |
| 903, 1375 — 980, 1397 | H | "W1" — n=2, caps 22 px |
| 1078, 1375 — 1129, 1397 | H | "W2" — n=2, caps 22 px |

Note W1–W3 panes are ~1 px apart and de-dupe to 2 distinct panes; they survive
the §4 2-pane gate because their jamb caps are ~22 px. The two former FP slivers
(toilet 978,773 and the 373,926 fixture, both n=2 with 4 px caps) are now
rejected by that gate. Doors unchanged (no regression vs door-guide §9.1).
Confirmed false positives that must stay rejected: garden/double doors, door
leaves (door overlap), toilets/sink/cupboard/balcony door.

### 5.2 5-1133-WD03.pdf

**Partially ground-truthed (run 2026-06-19_12-02-48).** Four windows confirmed
by the user, all now detected:

| Window | topology | glazing path idx | cap path idx |
|---|---|---|---|
| A | 3 H panes, ~7 px spacing, 13.7 px deep, 106 px wide | 2904 / 2926 / 2905 | 2909 / 2925 |
| B | 2 V panes, 7.6 px apart, **no centerline**, 173 px tall | 2046 / 2167 | 1951 / 2267 |
| bonus | 3 short H panes, ~2 px spacing, tiny ~5 px caps, 20 px wide | 2170 / 2181 / 2094 | 2096 / 2295 |
| W8 | three-light frame (§1b): 2 rails 14.7 px apart, `qu` block end caps + mullion pairs, per-light center segments; 268 px wide, ONE label ⇒ one window | 3087 / 3088 + chain 3092 / 3131 / 3132 | 3091 / 3089 (mullions 3127–3130) |

A/B/bonus drove the v2 cap-anchored rewrite (v1's `n≥3` + tight-spacing gates
missed all three); W8 drove the v2.1 framed multi-light extension (user
confirmed 2026-07-07).

**Page-1 windows — regression target (user-confirmed on runs 2026-06-19).**
The page carries 10 true windows: 5 axis-aligned (267,506 / 248,283 / 84,285 /
501,272 / 187,762) and **5 diagonal** (1787,1009 / 1783,639 / 200,964 / 200,656 /
1767,1233). All 10 must stay detected — the diagonal ones (clean panes between
gray FILLED jamb caps) are exactly what the band-interior gate must not regress.

The user flagged 8 page-1 FPs, all walls read as a 2-pane band:

| FP | bbox | what it was | status |
|---|---|---|---|
| w19, w21, w25, w32, w33 | (various) | insulation-hatched walls (crosshatch between the rails) | **rejected** by §4b: 2–7 shapes between the panes (true windows ≤1) |
| w17, w18 | 167,253–228,266 / 170,527–230,541 | top edge of a solid-filled block | **rejected** by §4c: step outline + fill edge 2.5/2.0 px apart, band at the step corners (margin ≤0) |
| w26 | 997,1015–1019,1102 | "recess" niche (stud boxes + U-curve at the ends) | **rejected** by §4c: box side + shelf line 2.2 px apart, band at the box corners |

Every *end-clutter* signal that catches w17/w18/w26 also flags the diagonal
windows' jamb fills (verified exhaustively) and colour is out (§4b) — which is
why they were originally deferred to Gemini. The §4c tight-pair interior gate
(2026-07-07) rejects them from a different angle entirely: their 2-pane band is
one doubled material edge terminating at the cap ends, measurably unlike a
narrow double-glazing line running interior to its jambs.

**Post v2.1 (2026-07-07): 16 windows page 1** — exactly the prior 15 plus
**W8** (926,267–1194,282, n=3, `lights=3`). Getting to +1-and-nothing-else
took three coupled fixes, each pinned by a test:

- W8 was raw-detected but then **vetoed by fallback-tier doors** (conf-0.35
  mullion strips whose bboxes end 10 px ABOVE the band; the 20 px
  `CROSS_DOOR_EXPAND_PX` dilation reached down for 11% cover). Fix:
  fallback doors keep a veto only near their own ink
  (`CROSS_DOOR_FALLBACK_EXPAND_PX` 8 px), because fallback doors often ARE
  window-like ink — the joinery slats at (1072,740) and the recess column at
  (999,890) read as both a window band and a fallback door, and those
  windows must keep yielding (a first attempt that ignored fallback doors
  entirely resurfaced them as FPs — user-flagged).
- A **sliding shower screen** at (1239,829) detected once block caps existed
  (two rails + block end caps + X-crossed post; its gray sliding panels sit
  between the INNER rails while the detector locks onto the 3 px top-rail
  pair, invisible to the interior gate). Fix: `WINDOW_BLOCK_CAP_CROSS_RATIO`
  — an X-ed block is a post symbol, not a jamb; the candidate never forms.

No window on either PDF is suppressed by a real (≥ `CROSS_DOOR_MIN_CONFIDENCE`)
door any differently than before; floor-plans is identical (4/4).

**Post v2.2 (2026-07-07, tight-pair interior gate): 11 windows page 1 —
the current regression target.** The user flagged 5 FPs in the 16-window state,
all 2-pane bands whose panes hug ≤ 2.5 px (a doubled material edge, §4c):

| FP (run 2026-07-07_14-04-05) | bbox | what it was | gap px / min jamb margin px |
|---|---|---|---|
| window_0014 | 2329,97–2350,122 | RWP square in a hatched detail-wall corner | 2.0 / −7.0 |
| window_0016, window_0017 | 167,253–228,266 / 170,527–230,541 | solid-wall step bumps (= w17/w18 above) | 2.5 / ≤0.0 · 2.0 / ≤0.0 |
| window_0018 | 2291,515–2330,539 | white notch in a detail-drawing corner | 1.6 / ≤0.0 |
| window_0020 | 997,1015–1019,1102 | the "recess" niche (= w26 above) | 2.2 / ≤0.0 |

All five are gone offline; the **11 true windows** (10 confirmed + W8) are
byte-identical by bbox; floor-plans is identical (4/4 — its true W1/W2/W3 are
themselves tight pairs at 1.75–2.0 px and survive on jamb margin 4.3–8.6 px,
which is exactly why the gate tests margin, not gap). Removing phantom
window_0018's opening seal also freed the adjacent room polygon to extend to
the real wall line (bbox x1 2311 → 2328) — a room-outline correction, not a
regression. Pinned by `TestWindowTightPairInterior` (recess box, wall step,
floor-plans tight pair, window_0022 wide pair at cap end).

## 6. Known limitations / not handled

| Case | Status | Note |
|---|---|---|
| 1-pane windows (single line + 2 caps) | Not detected | `WINDOW_MIN_GLAZING_LINES = 2`; a single line between caps is indistinguishable from a bracket/niche. Needs ground truth before relaxing. |
| Narrow 2-pane window with small caps | Not detected | The §4 2-pane jamb gate (`cap ≥ 12 px`) rejects these as wall/fixture slivers. A real one would need ≥3 panes or bigger caps to surface. |
| Framed multi-light windows (`re`/`qu` block caps + mullions) | **Handled (v2.1, §1b)** | 5-1133 W8. Block caps must be bar-shaped (aspect ≥ 1.8); a mullion-segmented center line re-joins only across a block-occupied gap. |
| Mullions drawn as short cap LINES (not blocks) | Not handled | Chain bridging requires a block — a line-bridged merge would also chain dashed linework / dimension ticks. Needs ground truth before relaxing. |
| Windows on a door (e.g. sidelight) | Suppressed | Door-overlap exclusion drops a window materially covered by a door. Unobserved as a real case. A window BESIDE a swing door in the same wall run (beyond the hinge jamb, in the wall plane) is exempt — §2. |
| Square corner-post block caps (bay frames: 12×12 px `re` at each corner of a 12 px frame, s10 lounge bay) | **Handled (§1c)** | A square block over the bar thickness is a corner post when its side equals the band depth it closes; pane cover is measured from each cap's face. Detects s10's two bay returns. |
| A bay's LONG face (s10 lounge, 299.5 px post-centre to post-centre = 2.54 m at 1:50) | Not detected | Over `WINDOW_MAX_WIDTH_PX` 280, which is what caps long wall/decoration runs pairing as glazing. The two short returns of the same bay detect (§1c); raising the gate needs its own ground truth. |
| Corner glazing with no jamb at the shared corner (s10 porch: two frames meeting at a mitred corner, each ended by the other's rails) | Not detected | Each frame has one block cap; its other end is the perpendicular frame's 200 px rails, far over `WINDOW_CAP_MAX_LEN_PX`. Unlike the lounge bay (§1c) there is no corner post to read — the rails mitre directly, so the cap would have to be synthesized from the crossing band. |
| Diagonal / bay windows | Not handled | Detector is axis-aligned only. |

## 7. How to verify a change won't regress

1. `python -m unittest discover tests` (window tests in `tests/test_window_detection.py`).
2. `python app.py extract floor-plans.pdf --no-gemini` → 4 windows at the §5.1
   bboxes, 9 doors.
3. `python app.py extract 5-1133-WD03.pdf --no-gemini` → 11 windows (§5.2
   post-v2.2 state: the 10 user-confirmed + W8; none of the five doubled-edge
   FPs).
4. The `TestFloorPlansRegression` test pins floor-plans end-to-end; keep it
   green. Diff final windows **by bbox, never by candidate id** (ids shift
   between runs).
