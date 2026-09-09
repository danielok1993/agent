# Wall-network rules

Extracted verbatim from CLAUDE.md. The rules of `detection/walls.py` -- the
INTERNAL wall-centerline network, which is never emitted as candidates and
exists to feed `detection/rooms.py`. Every rule here is a drawing convention
backed by margins measured on named sheets; the numbers are the asset. See
`docs/room-detection-rules.md` for what consumes this, and
`docs/scale-normalization-findings.md` §4 for which constants scale with
drawing scale.

## Order and exclusion sets

Room detection: order matters — doors/windows detect first, then
`detect_wall_network(paths, text_spans, exclude_path_indices)` builds the
internal centerline network (text spans disambiguate white fills; paths on an
annotation-named OCG layer — exact tokens `callout`/`dimension`,
`LAYER_ANNOTATION_KEYWORDS`, never a layer that also names an element class —
join the exclusion set BEFORE pairing, alongside dimension chains and open
leaves, because a vetoed line that merely lost barrier rights would still pair,
enter the stroke reference and launder its partner: measured on s04, a
page-wide 1.19px cyan section callout on `Symbols_Dynamic Callouts` — the wall
pen's width, 2273px across the whole sheet — paired over a short subspan and
chopped rooms 0000/0001/0003 at y=767, and the same template layer exists on
s08; `text` is NOT a token — s15's `TEXT` layer is mis-filed building linework,
155 black 1.0px lines up to 1360px, and vetoing it lost 17 of 20 rooms; and
VECTOR TEXT — sheets that draw every label as stick-font glyph strokes with no
text span at all (s06/s11/s16/s20/s13; s06 has 8 spans and ~24k glyph strokes,
in the 0.75px pen that IS its wall stroke reference) — joins the same
pre-pairing exclusion through `_vector_text_indices`: at 1:100 a 9.5–12px glyph
stem clears the scaled 5.5px face floor and the parallel stems of an H/N/"IL"
pair at 6–10px into mini wall bands, so wherever the cluster chained to a door
plug or wall the outline was forced around the word (measured on s06: BATH &
TOILET came out as an 18-vertex polygon notched around both words, LANDING lost
its label block and the flight, 7.5k vs 10.4k px²), while ground-floor labels
merely became holes and vanished; the convention is that wall linework is
CONNECTED (a nib meets its band, hatch meets its faces, treads meet the
stringer) whereas glyph ink is freestanding: a glyph is a touching-stroke
component ≤ `WALL_TEXT_GLYPH_MAX_PX` (30px, 5mm text — paper-space, text height
is a drafting convention: 8.7–29px across the corpus) that touches NO larger
linework, and a text line is a row of ≥ 3 glyphs sharing a cap or base line
(either axis — s20 is rotated) at gaps under one glyph height, ≥ 2 of them
multi-stroke and spanning ≥ 20° between strokes — a freestanding hatched pier
box is one component, never a row, and a loose row of parallel hatch strokes
has neither multi-stroke members nor angle diversity (v1 without the touch rule
flagged every hatched band on s06 as a text line; corpus telemetry after it:
s02/s04/s05/s07/s10/s12/s15 flag nothing, s01/s03/s08/s17 flag only fixture
symbols drawn as freestanding stroke rows — hob rings, sink bowls, bins, RWP/G,
trees — never wall, and the full sweep changed no entity on any sheet) — and so
do DRAWN DASH LINES (`_dash_row_indices`, W-gate iteration 3 step 6: a dashed
line TYPE the exporter explodes into one solid piece per dash — beam-over,
drain, boundary, section and demolition lines, dashed rooflight and unit boxes
— is a periodic row of same-pen pieces at equal gaps ≤ `WALL_DASH_GAP_MAX_PX`
(18px, 3mm paper), plain or chain, its clipped end dashes ≤ one period, never a
row that hatch strokes END on from one side (that is a hatched band's face
drawn dotted, s05) nor a face between touching tick stubs (s17); every piece in
the wall pen was otherwise a strong lone barrier face, and s15's beam lines and
drain run fenced its lounge, vestibule, kitchen zone and garage into twelve
cells — the full rule and its measured margins are in
`docs/w-gate-recalibration-handoff.md` §"Iteration 1–3 summary, moved from
CLAUDE.md (2026-09-09)", step 6), then `detect_rooms` extracts rooms as the
connected free-space components of the page after subtracting barriers. The
exclusion set (`door_open_leaf_path_indices`) keeps single-swing doors'
OPEN-leaf linework out of face collection entirely: a swing leaf is drawn
standing open in the wall pen, parallel to whatever wall it parks beside, and
pairing it inflates that wall's band across the swing side (measured on
floor-plans: door_0000's double-line leaf paired with both faces of the 7px
hallway wall and the collinear merge carried the inflated 18.5px thickness over
the whole inter-door run, fencing an 8px strip out of the hallway); each
excluded path must also lie fully inside its door's zone (bbox ± 2px, the
rooms-stage convention) because the leaf-companion finder serves the opening
check and over-collects — a leaf parked 1.9px off a jamb claims the jamb's own
faces as companions (measured: door_0005's companions were the wardrobe end
panel's two faces, and excluding them dissolved the wardrobe/bedroom split),
while real partitions extend past the swing zone and leaf ink never does.
Merged french pairs are left alone (their leaves are drawn closed IN the wall
plane — legitimate wall evidence), as are sliding/folding panels (they lie in
or seal their wall plane by construction) — but a GARDEN pair's leaves park
OPEN at the outer ends of the opening, perpendicular to their wall and parallel
to the flanking room walls, so the merge preserves both halves' leaf ink
(`leaf_path_indices`) and the exclusion covers garden doubles too (measured on
floor-plans door_0016: each parked double-line leaf paired with the bedroom
side wall ~30px away into a phantom 30.5px band whose solids fenced a 37px-wide
strip of bedroom on each side of the doorway, and a leaf/jamb pair pinched the
doorway tongue to the leaf faces); the in-zone gate drops the halves'
over-collected jamb companions exactly as it does for singles.

## Stroked rectangles as weak faces

A stroked, UNFILLED `re`/`qu` item contributes its two LONG edges as WEAK faces
only (`_collect_stroked_rect_weak_faces`, concatenated with the hairline faces
inside the same collinear merge): a wall segment is sometimes drawn as one
closed box — a window infill, a blocked-up doorway, a pier — that the exporter
emits as a single rectangle operator, and face collection reads only `l` items
(filled rectangles as bands), so the box had no faces at all (measured on s03:
the 83×33px infill left of window_0011, a 1.5px `qu` in the wall pen hatched at
0.25px in the 1:50 plan, never paired and the PROPOSED BEDROOM merged with the
bedroom below it through the infill). But the same geometry is how beds, baths,
basins, shower trays, radiator casings and door LEAVES are drawn (5×90px `re`
items on s17/s20), and exploding every stroked rectangle into STRONG faces
fenced ~40 fixtures into phantom rooms across the corpus and lost five real
rooms — thickness and aspect do not separate the classes (target 33px/aspect
2.5 vs a window-frame box 18px/2.4 vs the 36px cap). The convention: a stroked
atomic rectangle may represent a wall band when its opposite long edges lie at
wall spacing AND the enclosed band carries distributed wall material; so the
edges enter the material-gated weak tier (stroked=False, original pen and path
index kept) — they pair only through `_band_has_wall_material` on runs ≥
`WALL_WEAK_MIN_RUN_PX`, never gain lone-face barrier rights and stay out of the
stroke reference, so a hollow box pairs with nothing. Short ends are omitted: a
pair's wall solid is flat-capped, so the band's ends are implicit once its long
edges pair (s03's explicit `l` closures, paths 15854/20330, are additional
evidence, not the reason omission is safe), and a short end abutting a stair
tread otherwise fuses into the tread's rung, overshoots
`WALL_STAIR_END_TOL_PX`, drops the tread from the run and fences the flight
(measured on s03's 1:100 landing under the strong-edge version). Shape gates
(`WALL_RECT_MIN_ASPECT` 2.0, wall-thickness short side, face-length long side)
are a candidate prefilter, not evidence.

## Face collection and the length floor

Face collection's length floor `WALL_FACE_MIN_LEN_PX` (11px, W-class; the
W-gate census's 9 was tried and reverted on 2026-09-04 — a 7px band's 45° hatch
strokes are 7√2 = 9.9px long and the band-end ones paired on s01 and s02, see
the constant's comment) admits a one-thickness JAMB NIB — the minimum wall
piece a doorway leaves beside its hinge: 100mm at 1:50 is 11.8px, and s03 draws
every nib and band end cap at 11.75px (viewport 1:49.99; 40 wall-pen lines in
the 11.5–12px band, s01 15 / s02 19 in 11–12px), so the previous 12.0 floor
excluded the nominal minimum it names — the hatched 12×12px nib below door_0018
contributed no wall material, the doorway edge's plug lost its bottom anchor
(end_cov 0.29 < 0.5), and the dilated-bbox fallback fenced the swing square out
of the BEDROOM (same failure on s17 doors 0004/0031/0035 and s18 door_0016; at
11px those swings return to their rooms and no entity is added or removed
anywhere on the corpus — the only other geometry deltas are sub-1k px² edge
nibbles at the newly admitted nibs). Length never separated nibs from dimension
ticks (7–13px, their own recogniser `_dimension_line_indices`), and
`WALL_PAIR_MIN_OVERLAP_PX` (12px) still keeps a nib's faces from pairing — they
seal as lone thin barriers at the reference pen. Corpus telemetry: 219
candidate rectangles inside floor_plan regions, 2 pass the material gate — the
s03 infill (25.2 marks/100px, both edges continuing the neighbouring band
faces) and s18 path 19408, a 59×5.5px 1.75px box at 1:100 annotated "Existing
door to be removed and blocked up" (25.5 marks/100px) — every fixture box
measures 0 marks.

## Lattice demotion — striped fields and hatch

Before any pairing, striped-field faces are demoted to the weak
(material-gated) pipeline (`_demote_lattice_faces`): ≥ `WALL_LATTICE_MIN_RUNGS`
(5) parallel SAME-PEN faces at equal wall-like pitch (≤
`WALL_MAX_THICKNESS_PX`, one missing rung tolerated as a 2×-pitch gap — a text
mask can eat a joint line) and rung extents chaining along the run — that is a
drawn surface pattern (paving bonds, tile fields, floorboards, roof joists,
stair treads, balustrades, hatch, table rows), never wall structure, whatever
its pen weight or rung LENGTH: rooms are wider than the max wall pitch by
definition, so real walls cannot stack five deep, and short strokes at wall
pitch five deep are still never walls (there is no rung length floor — s17's
treads measure 47.7px, s18's ramp balustrade 12.75px, and under the old 48px
floor both stayed strong and paired into 13px "walls"). A rung is an
EXTENT-CONNECTED cluster of the collinear pieces at one offset
(`WALL_LATTICE_TOUCH_GAP_PX` along the axis), never every piece on the page at
that offset: a room's wall face merely collinear with a distant field's course
is not that course (measured on s17: the WC's top face at y=1167 shares its
offset with a roof-tile rung 2000px to the right; under offset-only rows the
whole plan's exterior walls on s18 were demoted along with the roof fields they
happened to align with, and the plan detected no rooms), so a row lying apart
from the run along the axis is SKIPPED, never a break (a break left 3 of a
22-rung roof-tile field strong on s03, and they paired into phantom bands), a
same-offset row that does touch the run is the same rung split by a text mask
wider than the touch gap and is absorbed, and every rung seeds a run of its
own. Chained membership alone is NOT enough — the run must also reach a
simultaneous cross-section of ≥ 5 rungs somewhere along its axis
(`_field_span`, sweeping the rungs' extents with ends sorted before starts so
end-to-end staggered courses never count as coexisting): distinct parallel wall
bands at quasi-equal spacing chain too (measured on s07: three 8px wall bands
at 8–9px gaps chained into a 5-rung "ladder" whose envelope glue deleted the
plan's central wall belt and every room with it — their pieces occupy disjoint
spans and never stack deeper than 3). And only the rungs lying IN that stacked
span are demoted (`WALL_LATTICE_FIELD_COVER_FRAC` 0.5 of a rung's extent): a
long wall face that a short equal-pitch stack (a radiator's edge lines drawn
parallel to it) coexists with over a fraction of its length keeps its face
rights. Pen weight alone cannot catch striped fields (measured on 5-1133: the
OPEN GLAZED VESTIBULE's paving bond is penned 1.05 vs the 1.50 wall reference —
ratio 0.70, above the `WALL_WEAK_STROKE_RATIO` demotion gate, and the sample
set has real wall pens down to 0.67 of the reference, so the ratio cannot be
raised; the field paired into phantom 31px wall bands that chopped the open
vestibule into four phantom "rooms", anchored white rooflight rings, and
mis-contexted the glazing-mullion fallback doors 0110–0113 as "in_wall"). Five
rungs (not four) keeps a cavity party wall drawn leaf/cavity/leaf at equal
widths out of the demotion. Hatch is the same signature pitched too tightly to
be walls, and the same scan catches it: two strokes of one field otherwise pair
with each other like any parallel pen mates. Inside a straight band the phantom
pair hides in the real one; at an L-corner the band turns while the hatch angle
does not, and the pair juts out (measured on floor-plans: strokes 2502/2516 of
the 45° magenta field paired 28.1px apart into a diagonal centerline whose
solid chamfered room_0000's and room_0001's top-right corners ~16px, and the
left wall's hatch sawtoothed room_0001's edge into 30 vertices). PITCH is what
proves they are not walls, not their diagonality (a real 45° bay wall pairs at
wall spacing and survives): five hatch courses COEXISTING at ~4px pitch span
~16px, well inside one band's worth of `WALL_MAX_THICKNESS_PX`, so the lines
are that band's material rather than five walls — measured, both reference
PDFs' hatch fields pitch at 4.05/4.07px while the tightest real striped field
on either is 11.4px.

## Stair demotion

Stairs are FURNITURE to the room stage (RICS GIA takeoff runs the room polygon
to the enclosing walls straight through the flight; treads/risers are a
separate structural takeoff), yet stair ink is drawn in the wall pen (s03:
1.5px, the reference itself; s13: 0.75) and paired like walls (s03 FF: two
treads at th 14.8; GF: the stringer and the balustrade line), so
`_demote_stair_faces` runs BEFORE the collinear merge, on one face per PATH (a
landing edge collinear with a wall nib's face merges into it, and demoting the
merged run would cost the nib its face), and sends stair ink to the weak
pipeline like lattice members. Three recognizers keyed on drawing convention,
never on pen: a TREAD RUN — ≥ `WALL_STAIR_MIN_TREADS` (3) parallel same-pen
faces at a consistent pitch (`WALL_STAIR_MIN_PITCH_PX` 6 to
`WALL_THICK_MATERIAL_MAX_PX`, ±`WALL_STAIR_PITCH_TOL_FRAC` of the median —
s13's cut treads pitch 8.7–11; a jamb one wall-width past the last tread splits
the chain instead of killing it), extents inside the median-length member's
±`WALL_STAIR_END_TOL_PX` (the median, never the longest: the long wall face the
flight abuts is one pitch off the last tread and would otherwise be the
reference), each ≥ `WALL_STAIR_MIN_LEN_FRAC` of it (treads clipped by the
section cut are shorter) — both tested per MEMBER of a rung, never on the fused
envelope: collinear pieces at one offset fuse into a rung when they overlap or
merely touch, and a same-pen piece abutting a tread end-to-end on the same axis
(a window-frame edge, a skirting, a wall face) otherwise stretches the envelope
past the end tolerance so the TREAD drops out of the run and stays a strong
face (measured on s03 FF under the rejected strong-edge variant of the
stroked-rectangle rule: tread 1132, 48.5px, fused with a 17.7px frame edge into
66px against 51px siblings, dropped, and fenced the flight off the landing at
(1161,1098); the zone fixpoint cannot rescue it because the cut only reaches
the third tread), so the in-extent members are the tread and the overshooting
piece keeps its own rights, with the length floor met by the UNION of in-extent
members so a tread split in two by a text mask still qualifies, no member
longer than `WALL_STAIR_MAX_ASPECT` (10) pitches (a wall drawn as 4–5 parallel
lines at leaf pitch runs 16–20× its pitch on s17, real flights 3.3–4), no
member a short OBLIQUE stroke (s20's cross-hatch: 20–43px strokes at 15°/135°
and 12–18px pitch is a flight by every other measure), plus EVIDENCE from a
same-pen transverse line within one flight depth: one properly CROSSING a
tread's interior (the direction arrow; both overshoot by
`WALL_STAIR_CROSS_MARGIN_PX`) or an OBLIQUE one that ≥ 2 treads END on (the
section cut clips the treads it passes; a wall's perpendicular end cap closes
its faces' ends too but never obliquely, a hatch stroke's own ends lie on the
faces rather than the faces' ends on it, and s17's orange 'to be removed' ticks
crossing a 5-line cavity wall are another pen), or a long oblique one (>
`WALL_HATCH_MAX_LEN_PX`) that even ONE tread stops on strictly INSIDE the
reference tread's extent (past `WALL_STAIR_END_TOL_PX` from both ends) — a
clipped tread: a wall face stops at a perpendicular jamb cap and a hatch stroke
meets a face's end only at the band's corner, i.e. at the run's extent, never
mid-run (measured on s03's 1:50 plan: the zigzag break line enters the flight
beside the first tread and leaves at the wall face, so only that tread stops on
it — 61.5px against 97px siblings — and its 8–17px zigzag pieces are under the
face floor, so no chain spans the flight either; under the two-tread rule the
run had no evidence, the treads fenced as strong lone barriers and the stair
foot came out as its own room beside the landing); the cut is often a BREAK
LINE — two collinear halves joined by a zigzag jog whose pieces are under the
face floor — so a same-pen oblique face continuing a cut member on the same
line (within `WALL_STAIR_TOUCH_PX` perpendicular) with nearest ends within
`WALL_STAIR_BREAK_GAP_PX` (24px; s03 measures 11.6px across an 8.6/17/8.7px
jog) joins the stair ink even outside the flight bbox, unless a wall face
anchors it (s03: the 58.9px lower half stayed a strong lone face and notched
the merged room) — the discriminator against a cavity party wall drawn
leaf/cavity/leaf at equal width, which nothing crosses; a run whose crossers
include ≥ 3 mutually parallel lines is cross-hatch, not a stair; perpendicular
touching lines (nosing edge, stringer) are stair ink once the evidence is in,
never evidence, so is an END CUT — a same-pen end-to-end chain inside the
flight zone whose near edge lies within one pitch of the first or last tread
and which spans the flight width (s17's shallow zigzag cuts one pitch above the
first and below the last tread touch and cross nothing, and fenced the flight
into its own room between them) — and any transverse a non-member wall face
pairs with (a partition stub alongside the flight) stays; a STAIR ARROW — a
same-pen face chain walked end-to-end away from a marker ring
(`_FillRing.is_marker` arrowhead) with `WALL_STAIR_TEXT_TOKENS` (UP/DN/DOWN)
text within `WALL_STAIR_TEXT_NEAR_PX` of it; the chain and every face it
properly crosses are stair ink (walls are never crossed by wall-pen linework —
s03 GF's arrow crosses the stringer and the balustrade line into the flight —
and a leader crossing a wall has no UP/DN); a WINDER FAN — ≥ 2 unpaired
non-axis faces longer than `WALL_HATCH_MAX_LEN_PX` sharing an endpoint at ≥
`WALL_STAIR_FAN_MIN_ANGLE` (risers fanning from the newel; a 45° bay wall pairs
at wall spacing). Zones (member bboxes, touching zones merged — arrow + winder
box + flight) then absorb the rest of the symbol to a fixpoint: a face inside a
zone joins when it is the collinear end-to-end continuation of a member (the
crossed stringer's lower run) or when every wall-spacing partner it has is
stair ink (the balustrade line pairing with that stringer, the landing edge,
clipped treads, the cut) — a real wall pair inside the zone anchors itself and
stays, which is what kept s20's short-piece wall faces inside its cross-hatch
zones (measured: 840 faces demoted, four rooms lost, before the anchor rule and
the hatch exclusion).

## Pairing — plain, thick and through tiers

Four barrier tiers: (1) wall solids — paired centerline segments dilated to
their measured thickness (`WALL_MAX_THICKNESS_PX` 36px — 305mm at 1:50; the
un-hatched strong-pair distribution ends at 300–305mm on 13 sheets, so the
corpus's standard walls sit ON it at 1.00–1.03×, and the W-gate census's 40 was
tried and reverted on 2026-09-04 because the 36–40px band is full of fixtures
at wall spacing that only material can separate — see the constant's comment —
covers heavy blockwork bands; strong non-demoted faces spaced past the cap up
to `WALL_THICK_MATERIAL_MAX_PX` 56px — a 1:50 475mm band (48 until the W-gate
census: s15/s20's 400mm thick pairs sat at 1.01× under it, and it moved only
together with the per-band mark cap below, because at f=0.5 a 56 cap is 28px
and s05's 475mm wall pairs at exactly 28, falling from the THROUGH tier into
this one) — still pair as a THICK tier gated exactly like weak pairs, on
`_band_has_wall_material` + `_claims_interior_pair`, because a locally
thickened pier otherwise encloses its own hatch as a free-space pocket:
floor-plans' bedroom chimney breast bulges the 19.3px exterior wall to 39.2px
and its hatched interior came out as a 35×96px phantom room; the tier is OFF
for the interim stroke-reference pairing so 36–56px annotation coincidences
cannot skew the pen median, and the 4px collinear-merge offset tolerance plus
the collapse thickness slack keep the local thick segment from carrying its
width onto the main run; and above that cap, up to `WALL_THROUGH_HATCH_MAX_PX`
72px — a 1:50 610mm band — strong faces pair as a THROUGH tier (`_Seg.through`,
gated by `_band_has_through_hatch` on marks collected up to the cap's diagonal
— since the W-gate census the material marks are collected ONCE at that
diagonal and every band gate filters them to its own cap, `_mark_len_cap` =
max(`WALL_HATCH_MAX_LEN_PX` 48px, T√2 + 2): 45° hatch is clipped to the band it
fills, so a cap-thickness band's strokes are 51px and no thick-tier band over
34px could pass its material gate under the fixed cap; a mark longer than the
page-wide cap counts only as through-hatch, both ends on the faces, because the
one other thing that draws a long stroke inside a band is a leader, a section
cut or a stair arrow — s17's stair stringers, 48px apart, hold two arrowhead
barbs, a 54px cut line clipped stringer to stringer and a 49px one touching one
stringer, exactly the 4-mark floor, and without the condition they paired and
fenced the flight out of its hall) only when the band is hatched THROUGH:
diagonal strokes whose two endpoints land on DIFFERENT boundaries of the region
— the two faces, or one face and the run's end line where a perpendicular
return clips the strokes at a corner — at the weak tier's density and spread. A
hatch tool clips its strokes to the region it fills, so strokes ending on both
faces prove the faces bound one filled region, which in plan is cut material; a
floor pattern or a fixture's hatch is clipped to its own boundary and stops
short of at least one face. Measured on s05 (1:100, f=0.5): the first-floor
left external wall is a 28px band (~475mm) of 104 strokes at 135°, each 39px =
28 × √2, two interleaved series at 3.1px, past the scaled 24px thick cap and
the scaled 24px material-mark length cap, so its faces never paired and the
hatch interior came out as a 24×468px phantom room; the sheet's other bands top
out at 17.8px and corpus bands at identity reach 39px (s01). The end-line
boundary matters at corners: the run beside the bay return had 21.7px of
both-face spread over a 44px run against the 22px gate, and its first
band-width is covered by return-clipped strokes);.

## The weak tier and the material gate

Hairline faces (below `WALL_MIN_STROKE_WIDTH_PX` — the 0.45px joinery/fixture
pen new partition walls are often drawn in) also pair, and faces penned under
`WALL_WEAK_STROKE_RATIO` (0.66) of the paired-wall stroke reference are DEMOTED
to the same weak class even when they clear the absolute floor — floor-tile and
paving grids are drawn at ~half the wall pen (0.75 vs 1.5 on 5-1133) and
otherwise pair with the real wall faces they run parallel to at wall-like
spacing, stamping phantom wall bands across room interiors (measured on 5-1133:
a tile-line/wall-face pair ate the WC's toilet strip, and tile lines split
Family Bath+Utility three ways) — but a weak-involved pair survives only when
the band between the faces carries drawn wall MATERIAL
(`_band_has_wall_material`): short strokes DIAGONAL to the band axis (hatch,
cross-hatch, the X's of blocking rectangles — the universal new-partition
signature) at ≥ `WALL_WEAK_MATERIAL_PER_100PX` (2.2/100px since the W-gate
census — the August "real partitions ≥4.8, glazing strips ≤2.6" predates the
mark dedup and s01's 1:92.2 truth scale; at true scales real bands sit at
3.4/100 = 4.1/m (s02) and s16's real hatched wall at 5.4/100 @f=0.5 = 3.2/m
failed the old scaled 6.0, while s02's glazing strip plus ticks is 1.7/100),
spread over ≥ half the run, on runs ≥ `WALL_WEAK_MIN_RUN_PX` (30px — shorter
material-dense slivers are dimension-tick clusters), counting coincident
strokes ONCE (`_collect_material_marks` dedups by location+angle: CAD exports
re-draw each oblique dimension tick in a heavy and a light pen and once per
adjoining dimension run, so 2 tick locations arrived as 6 marks and turned the
"750/800" dimension line into a phantom partition across the bath);
diagonal-only keeps liner lines (parallel) and radiator fins (perpendicular)
out, so plain hairline pairs — wardrobe edges, counter fronts — never become
walls; a weak pair that passes the material gate is still dropped when a KEPT
meaningfully-tighter parallel pair lies inside its band over ≥ half its run
(`_claims_interior_pair`, `WALL_WEAK_CLAIM_MARGIN_PX` 2px) — an over-wide pair
(a room-interior line paired with a real wall's FAR face) encloses the real
wall's band and passes on that inner wall's OWN hatch/blocking (measured on
5-1133: tile line 992 paired with the WC/bath divider's far faces at th 19.5
enclosing the true 12px divider pair, holding the WC's bottom edge ~5px high on
the tile line; killing all its pairs also removes the line's face from the
network, so no thin barrier survives either); and a material-gated pair that
SHARES A FACE with a kept, tighter, hatched strong pair lying on the FAR side
of that face is dropped when its own marks are under
`WALL_FAR_SIDE_DENSITY_RATIO` (0.33) of that wall's density
(`_claims_far_side_sparse`, the weak-tier analogue of the far-side rule below,
which exempts any band with material): a wall's hatch lies on one side of each
face and the hatched side is the wall — measured 2026-09-04 on s02's WC, whose
wall face paired at 38.25px with a hairline basin edge once the cap allowed it
and passed the material gate on two 13px corner X symbols (4 marks/146px =
2.75/100px against the wall's 25/100px, ratio 0.11) while every real corpus
weak pair sharing a hatched far-side face measures ≥ 1.0× (s02 4.2, s01 8.0,
s15 10.4, s18 1.0, s03 1.4, s05 1.6); the mark-shape statistics tried first —
distinct positions, gaps, face-spanning fraction, area coverage,
length/thickness, X size — all overlap real bands drawn with stipple,
insulation dots, inset hatch or two-block partitions — and material-backed weak
faces join `network.faces` as paired faces but stay out of
`wall_stroke_reference` (stroked=False) so hairline members cannot drag the
rooms' pen-weight gate down to fixture territory; on color-coded drawings
pairing itself is additionally gated by pen COLOR at the room stage
(`ROOM_WALL_PEN_MIN_FRAC` 0.15 of the network's paired-face length makes a pen
a wall-pen CANDIDATE): cross-pen pairs never form (`_pens_compatible`), and a
SAME-pen pair whose faces are all plain stroked non-wall-pen ink (no wall fill,
layer hint, or material backing) is furniture coincidence — its segment is
dropped from the barrier solids and its faces get no paired-barrier rights
(measured on floor-plans room_0012: the bed's pillow rectangles paired red-red
at th 24/32px and the solids fenced the pillows plus the ~5px strip to the wall
out of the bedroom, notching the outline around the bed);.

## Wall pens and the doorway veto

Since W-gate iteration 3 step 11 (2026-09-05) the sheet's DOORWAYS decide among
the candidates (`_doorway_pens`, a second barrier pass in `detect_rooms`):
building bands is not proof of walls — 600mm kitchen units, sofa arms and bed
frames pair at wall spacing in the furniture pen at any scale, and s01's red
pen carries 13.7 % of the paired network at identity and 15.2 % at its true
factor (33 thin sofa/bed pairs at th 2.5–4.8px appear at 0.542 while black
loses 700px), a knife-edge on both sides of the share that fenced 17 phantom
rooms (kitchen-unit and cushion cells of 0.24–0.38 m², two slivers, a strip,
two room splits) — while a doorway is proof: it is cut out of a wall, and a
confident (≥ `ROOM_BBOX_SEAL_MIN_CONFIDENCE`) door's INTERRUPTED plug reaches a
jamb at each end. A pen forms a jamb when its ink is what the tail runs into —
a PAIRED face of it intersecting the tail envelope (the band continuing past
the doorway, or the return band of a corner-hung door: s01's magenta partitions
meet its black walls at T-junctions, and the return is the second jamb of two
of magenta's three doorways), or a LONE face of it collinear with the doorway
line (within `WALL_PARALLEL_ANGLE_TOL`, both endpoints within
`ROOM_PLUG_NEAR_PX`) stopping in the jamb window (the tail plus the plug's
first `ROOM_PLUG_NEAR_PX` inside the bbox — a swing symbol overlaps its hinge
jamb by the leaf thickness, 3px on s01); a lone face merely ENDING at the jamb
from another direction is not a jamb (dimension EXTENSION lines end at both
jambs of the opening they dimension — s01's blue pen at one door per factor —
and a fixture's end panel ends at the wall beside a door), and the doorway is
cut into the pen forming BOTH jambs (a unit run drawn up to one jamb names
nothing). A share-gated pen that no doorway is cut into is VETOED — its lone
faces and same-pen pairs lose their rights and the barriers are rebuilt without
them; when the doorways name no pen at all (no confident door with an
interrupted plug) the share gate stands alone. Measured on the pipeline's own
plugs over every multi-pen sheet (`tools/census_scratch/step11/`, the loose
"ink touches a tail" test refuted first — s01 red touched 4 doors at identity
through units and wardrobe ends against the wall): every network-building wall
pen has doorways cut into it (s01 black 6/5 and magenta 2/4 at identity/0.542,
s02 black 1, s03 black 14 and grey 8, s04 3/3, s08 3/3, s12 7/4, s17 27,
single-pen sheets 3–14) and every annotation or furniture pen none (s01 red at
both factors and blue, s02's four annotation pens — its 6.4 % pen is the title
block's logo lettering — s17's orange demolition ticks, the 0 % red pens of
s04/s08/s12/s17); the paired-share, material share (0 % on the unhatched wall
pens of s02/s04/s08/s12), pair thickness (s12's grey wall pen at 6px median,
s04's black at 5.3), longest run and loop closure were each measured and none
separates. Ownership is read off the pass-1 plugs, which qualified against the
share-gated material, so the doorways veto and never promote: s03's 0.73 grey —
which draws the existing rear-extension walls at 10.4 % of the network, not a
non-wall pen — stays out and seals through its grey fills (inert; promotion
needs pen-independent material and is its own iteration). Corpus sweep:
verdict-identical and every sheet entity- and polygon-IDENTICAL (the veto fires
nowhere at the sheets' factors); at s01's true factor the harness reads rooms
9/12 with exactly one unreviewed room, the merged landing, instead of 18;.

## Pairing — taper, redundancy collapse and the far-side rule

Pairing itself demands ONE THICKNESS ALONG THE OVERLAP
(`WALL_PAIR_TAPER_MAX_FRAC` 0.5): the spacing `_perpendicular_spacing` reads is
sampled at the partner's first endpoint, which is the pair's spacing everywhere
only for truly parallel faces, and inside `WALL_PARALLEL_ANGLE_TOL` a stroke
crossing the band corner to corner — the single diagonal of a brick-hatch cell
drawn in the wall pen (s03 `EXISTING_BRICKWORK`, s04/s08 `RR_Wall Hatches`,
s20; an aspect-15 cell puts it 3.9° off both faces) — reads whatever the
divergence is at that one point, possibly hundreds of px past the cell
(measured on s03: the 219px chord against the 992px far-face run whose first
endpoint lies 650px away read 29px, the centerline landed 14.5px on the ROOM
side of the chord and its solid fenced a 15–29px strip off the bottom-right
corner of BEDROOM rooms 0005/0013, on both the 1:50 and the 1:100 plan; the
far-side rule could not catch it because the phantom band overlapped the wall's
grey fill by 0.24, past `WALL_FAR_SIDE_FILL_COVER_MAX`), so the partner's
signed offset is interpolated at both ends of the overlap and a pair whose
spacing changes by more than half of itself is dropped — a chord's runs from
the band's full width to zero (ratio 1.0 on all four sheets, at any scale)
while every surviving real pair on the corpus measures ≤ 0.30, the widest being
s03's tapering rear boundary wall at 0.24–0.27 (15.4 → 11.7px over 142px),
which stays; the redundancy collapse that dedups parallel centerlines absorbs a
shorter "duplicate" only when its thickness stays within
`WALL_REDUNDANT_THICKNESS_SLACK_PX` (4px) of the kept run — a duplicate
re-measures the SAME band, while a wall face pairing with ANOTHER wall's face
across a corridor of wall-like width shares one face with the real run, passes
the collapse offset gate on its own inflated thickness, and absorbing it used
to transfer the corridor width onto the entire run (measured on floor-plans:
the bathroom/landing wall's 7.2px run took th 35.2 from a stair-corridor pair
over a 41px overlap, and the poisoned solid fenced a 16px strip out of the
bathroom and 13px off the landing over the whole 165px run); such a pair stays
a separate segment whose solid is local to its actual overlap; the collinear
centerline merge that runs BEFORE the collapse applies the same slack (a member
differing from the run's thickness by more than 4px is not absorbed) because it
took the max over members — a jamb-scale pier's room-side face pairs with the
wall's OUTER face into a short thick centerline offset within the 4px collinear
tolerance of the band's own, and the max stamped the pier's width onto the
whole run (measured on s03: a 16.5px nib pair at th 13.8 carried onto a 6px
band over 272px, holding the kitchen outline 6px off its wall; s02 (877,314):
th 34.9 over 17px onto a 14px/251px run; s01 (818,907): th 29.2 over 12px onto
a 22px/121px run — while same-band members differ by ≤ 0.3px on all three), so
the pier now stays its own short segment; and a strong pair is dropped outright
when it is a wall face paired ACROSS THE ROOM (`_claims_far_side_pair`): a
kept, meaningfully tighter parallel pair or filled band shares one of its faces
and lies on the FAR side of that face over ≥ half the run, and the band on this
side carries no wall material (fill cover under `WALL_FAR_SIDE_FILL_COVER_MAX`
0.10 and no hatch) — a wall's material lies on exactly one side of each face,
so the material-less band is the room: kitchen counter fronts, wardrobe fronts
and corridor-facing walls are drawn in the wall pen at wall-like spacing
(measured on s03: the worktop outline 35.2px off the kitchen's inner faces,
just under the 36px cap, paired into phantom bands that fenced the counters out
of the KITCHEN and the WDR wardrobe out of its bedroom; on s01 the same rule
stops stringer/wall pairs sealing the stair flights, so the landing, flights
and hall come out as one room — the stairs-are-furniture verdict), while a
cavity wall drawn leaf/cavity/leaf keeps its leaves and, when the cavity is
hatched or filled, the cavity pair too; the dropped pair's PARTNER — paired
with nothing else — is the fixture front itself and is demoted (stroked=False)
so it gets no lone-face barrier rights either, because on pen weight alone the
counter lines re-fenced the same strip as thin barriers (the walkable-area-only
kitchen);.

## Fill rings and class rating

(2) wall-fill polygons — closed rings reconstructed by chaining consecutive
same-fill `l` items (the Vectorworks filled-polygon signature), each fill COLOR
rated by the shape of its ink (`_rate_fill_classes`: run length in thin bands
vs compact blocks, measured with area+perimeter equivalent-rectangle sides so
L/U-shaped runs stay band-like) — wall-rated rings become barrier area (seals
band interiors, corner posts, jamb stubs), furniture-rated classes (cabinet
blocks) are excluded entirely, unrated classes keep the permissive legacy rule;
a fill outline's `wall_fill` flag survives the collinear face merge only when
fill-outline members cover ≥ `WALL_FILL_MERGE_MIN_FRAC` (0.5) of the merged run
— the same laundering guard the merge's one-run-one-pen rule gives annotation
ink, because a wall band's 17px end stub collinear with a 354px stroke
otherwise stamps fill evidence over the whole stroke (measured on s03: grey
roof-tile stripes standing on the wall band's jamb stubs became full-height
wall-fill barriers, exempt from lattice demotion, and their pairs re-fenced the
ground-floor roof into three pseudo-rooms; on s18 a 0.75px tile line laundered
the same way split the en-suite at a grout joint); marker rings — tiny 3-vertex
triangles or concave 4-vertex darts up to `WALL_MARKER_MAX_SIDE_PX` (24px) bbox
side (`_FillRing.is_marker`) — are leader/dimension arrowheads drawn in the
wall pen (walls are rectilinear, so a small triangle is never material) and are
dropped from the class rating, the barrier area, and wall-fill face
qualification, while same-sized convex quads (jamb stubs, corner posts) stay;.

## Fill seams

Fill SEAMS never become faces (`_fill_seam_indices`): exporters triangulate
fills and PyMuPDF chains each triangle into its own ring, so a band arrives as
two triangles that BOTH carry the shared diagonal — an `l` item with fill on
both sides, which no pen ever shows — and abutting same-fill strips share their
joint edges the same way; a coincident edge (same fill, same rounded endpoints,
≥ 2 distinct rings) whose midpoint has fill on both sides is dropped from face
collection — from EVERY face tier, as a member of the pre-pairing exclusion set
beside `_dimension_line_indices`, not merely stripped of its `wall_fill` flag:
the exporter attaches the fill's own colour to the seam as a width-0 stroke,
which the extractor records at 1.0px (`ZERO_WIDTH_STROKE_PX`), so a seam whose
only veto was the fill flag stayed a STROKED 1.0px face — a "chord" across the
band within `WALL_PARALLEL_ANGLE_TOL` of both faces that pairs with the next
cell's face at a ratio under `WALL_PAIR_TAPER_MAX_FRAC` (s04: 7.1 → 12.4px,
0.43), sits in the paired stroke reference, and at aspect ≥ 19 merges
collinearly into the face run (measured 2026-09-02: s03 248 seams were stroked
faces, s04 50 of 50, s08 48 of 48, s12 116, s17 128, every one at 1.0px on the
fill's layer — `EXISTING_BRICKWORK`, `RR_Wall Hatches`; s01 has no fill rings
and s02's 48 seams are fill-only, so the reference sheets carry none; the taper
fix of `a239176` had read these strokes as brick-hatch cell diagonals) — while
an overdrawn ring keeps its outline because those duplicates have fill on one
side only (measured on s03: the bedroom band's diagonal, 17.7px over 336.7px =
3.0° — inside `WALL_PARALLEL_ANGLE_TOL` 4° — paired with the band's own face
into a slanted centerline whose solid stood 18px off the band at one end,
cutting room_0000's right edge 17px short at the top and flush at the bottom,
with rooms 0003–0006 skewed 5–14px the same way; s03 has 234 such duplicated
seams, s07 2,773, s18 32,139, s01 none — its walls are stroked). A seam is
found only when its two triangles chain into two RINGS, and a fill chain that
returns EXACTLY to its own start vertex mid-way and continues is two rings
drawn back to back, never one (`WALL_FILL_CHAIN_REVISIT_TOL_PX` 0.01): an
exporter that fans a fill emits triangle 2 from triangle 1's start vertex
(s20's grey wall bands), or opens the neighbouring cell's triangle on the
vertex this one closed on (s03: the 16.5px cell beside the band under the
bathroom, paths 272–277), so the six edges chained into one self-touching
polygon shapely rejects, `_collect_fill_rings` dropped both triangles, and the
seam went unseen while its fill-only edges kept wall-fill face rights under the
permissive unrated-class rule — s20's chord (552,2892)-(730,2881), the diagonal
of a 177×12px grey band, was an unstroked wall-fill face pairing with the next
band's face at a 0.49 taper ratio; the ring now closes at the exact return and
the next chain opens there. EXACT, not the 2px closing tolerance: the exporter
re-emits the shared vertex bit-for-bit, while a valid ring may legitimately
pass within 2px of its start mid-way (a narrow notch) and must not be split —
an exact return never occurs in a ring that IS valid (measured 2026-09-02,
`tools/probe_fill_seams.py`: 0 valid rings touched on 13 sheets; recovered s20
19 chains → 38 grey rings — 24 band pieces plus 14 ≤ 24px triangles from the
12×12 jamb stubs and 3–9×12 slivers that `is_marker` then excludes, and no s20
room outline changed; s04/s08 140/144 → 280/288 red demolition slivers,
0.63×29.5px, which make red a RATED wall class and 272/280 new barrier polygons
with no entity change, because their long edges were already RR_Walls-hinted
stroked faces and the ±1px seam probe never fits inside a 0.63px sliver; s18
328 → 434 black rings of which 253 are vector-text GLYPH OUTLINES (≥ 8 vertices
inside 16px); s14 77 → 108, s03 7 → 11; the corpus sweep is verdict-identical
to the unmodified tree except s18's recorded false-positive room_0009, which no
longer returns — a 7.1k px² pocket between a parking-bay kerb line and a column
of glyph-outline text that was never fenced by wall evidence (the raw free
space is one page-sized piece in both states), was severed at baseline by the
8px morphological opening, and dissolves now because 28 recovered glyph patches
reshape the eroded core's mitred re-dilation so it bridges back through the
text column, an incidental win — and s03 room_0007, whose corridor edge gained
a 2×4px notch (8 px²; 126 px² once the 2px simplifier redrew the
already-slanted plug/band edge around it): the split recovered the second
triangle (paths 284–286) of a 0.75px-tall grey sliver drawn under the
bathroom's bottom band, x 1075–1195, whose 0.36° tip sits at the corridor
corner (1194.67,1128.67), and each triangle dilated ALONE because `_fill_seams`
proved a seam by sampling 1px either side of the edge midpoint and a 1px probe
leaves a 0.75px sliver — no seam, no union — so the tip's mitre ran to the
`ROOM_RING_MITRE_LIMIT` cap, 4px past the vertex and 2.01px past the band's own
standoff (measured: the dilated tip landed at x=1198.68, the notch at
[1196.67,1126.68]–[1198.67,1130.67]); its twin triangle, valid before the
split, points its tip into the left wall band and never showed). So the probe
STAYS INSIDE THE FILL IT TESTS — a seam has fill on both sides at any distance
— sampling at the smaller of `WALL_FILL_SEAM_PROBE_PX` (1px) and
`WALL_FILL_SEAM_PROBE_FRAC` (0.5) of the thinnest sharing ring's `short` (its
equivalent-rectangle side): a thin triangle's `short` IS its inradius, half the
sliver it halves, and the clearance from its hypotenuse's midpoint to its far
boundary measures 0.98–1.07 × `short` on every corpus sliver (s03 0.375px
halves of the 0.75px sliver, s04/s08 0.312 of 0.63px, s12 0.625, s17 0.62–0.80,
s14 0.25–0.87; measured 2026-09-02 over every candidate edge on
s03/s04/s08/s18/s14/s02/s12/s17), so a probe AT `short` lands on the boundary
(not `contains`) and half of it keeps a 2× margin, while rings ≥ 2px keep the
1px probe unchanged. Recovered: s03 19/19, s04 61/61, s08 63/63, s12 5/5, s17
80/80 and s14 32/36 of the two-sided candidates that failed at 1px (a candidate
is two-sided when its sharing rings' centroids lie on both sides of the edge;
every one-sided candidate — an overdrawn duplicate, s04/s08 219/225 of them,
the twice-drawn red slivers' long edges and 0.62px ends — still fails at ANY
distance, its empty side stays empty); lost nothing on those sheets or s02, and
on s18 only 5 accidental "seams" between glyph-outline bars 0.47px apart that
the 1px probe reached across (s18's 1,633 black rings hold 1,550 sub-2px
pieces, the glyph outlines among them; s14's remaining four half-ratio
candidates are 12–76-vertex glyph junctions — gap (b) below). Corpus telemetry:
seams s03 310 → 348, s04 50 → 398, s08 48 → 408, s12 116 → 126, s17 342 → 502,
s14 212 → 280, s02 48 → 48; `fill_polygons` s04 291 → 111 and s08 299 → 116
(the twice-drawn red slivers union four triangles at a time), s03 76 → 65, s12
48 → 44, s14 141 → 136; faces s04 207 → 181, s08 197 → 170, s17 790 → 773 (the
sliver diagonals leave face collection). The corpus sweep is verdict-identical
on all 20 sheets; the only outlines that move are on s03: room_0007 and
room_0014 return EXACTLY to their pre-Gap-B polygons, and three 1:100-plan
rooms move toward their walls — room_0013 (BEDROOM) gains a 386×3.8px strip
along its bottom band (+1,466 px²): the band's 12px jamb stub at x
3741.67–3753.67 is drawn as a stack of three strips (a 0.75px strip over a
3.75px pair of triangles, paths 15115–15153) whose joint edge at y=1778.42
failed the 1px probe, stayed a 1.0px wall-fill face, and the collinear merge
chained the band's 416px top face (y=1782.17, offset 3.75 < the 4px collinear
tolerance) onto ITS line — the merged face sat 3.8px into the room, the band
pair measured 15.5px instead of its drawn 11.75, and the solid fenced the strip
(an instance of the single-endpoint offset test in `_merge_collinear_segs`, R2
of `docs/hatch-cell-chords-handoff.md`; with the joint a seam the merged face
lies on the band's own face) — room_0015 drops 0.6px onto its band's standoff
(134 px²) and room_0008 (BATHROOM, 1:50) loses a 44 px² slant beside its door
jamb.

## The collinear-merge anchor

And a merged run now LIES ON THE MEMBER LINE THE DRAWN INK AGREES WITH, not its
seed's and not its longest member's: `_merge_collinear_segs` seeds each run
with the first unused segment in path order and projected every member onto
that seed's line, so whichever short piece came first in path order positioned
the whole run — a stub is evidence of a line's EXTENT, never of its POSITION
(measured 2026-09-02 over 4,223 merged runs on s01–s04/s08/s12/s14/s17/s18/s20:
92 runs lay > 1px off their longest member on a seed under half its length, 61
in the strong-face merge, 52 reaching `network.faces` and 41 a paired segment;
the length-weighted least-squares line is NOT the anchor because the stubs pull
it 0.3–2px off the drawn face in most of those runs, onto no drawn line at all;
and the LONGEST member is not either — a window's board line is drawn parallel
to the face a couple of px into the room and spans the whole window, so it
outweighs the face piece beside it that it merges with while only the face's
line continues past the opening: on s03 room_0013's TOP band the 141.8px board
line at y=1238.67 outweighed the 68px face at 1236.42 and the longest-member
form moved the edge 2.25px INTO the room, −877 px², room_0016 −878 the same
way, although the face's line carries ~360px of collinear strong ink inside the
run's extent and ~660px within a door opening of it against the board's own
142). Membership is decided exactly as before — on the seed's line, pass by
pass — and once the passes converge the run is re-projected onto the ORIGINAL
member whose line carries the most collinear STRONG ink (`_support_anchor`:
stroked faces at a real pen width plus wall-fill outlines, never weak/hairline
pieces because a window board can be a hairline, within
`WALL_ANCHOR_LINE_TOL_PX` 0.3px of the line — s02's same-line jitter,
paper-space — counted over the run's extent plus `WALL_ANCHOR_SUPPORT_REACH_PX`
on each side; ties go to the longest member), keeping its own direction.

## Anchor reach and measurement

The reach is ONE DOOR OPENING (120px at f=1.0, 1000mm at 1:50, W-class): the
same face continues past the doorway it stops at, so s01's jamb nib (19.25px at
y=1142.5, merged with a 32.75px stair stringer at 1139.75) is corroborated only
by the 215.7px face continuing its line past a 59px doorway — a 921mm opening
at s01's 1:92 world, detected at identity — and reaches of 0/50 hang it on the
stringer; while page-wide, every window's board/stub line on one wall shares an
offset and outvotes the face — s17's cavity-wall inner face at 2208.92 loses
1116 to 1939 page-wide against 566 to 439 within 100–120px, and 150/200 thin
that to 566 to 530 and add a 714-vs-713 coin flip on a doubled s17 line.
Measured over the same ten sheets with `tools/probe_merge_anchor.py --support`:
the support winner differs from the longest member in
101/219/253/294/313/357/581 runs at reaches 0/50/100/120/150/200/page
(42/53/66/69/75/86/137 of them reaching a paired segment); every known case
(s03 room_0013/0016 top bands → the face, s01 nib → 1142.5, s01 WETROOM top
edge → 917.75, s03 room_0000 left edge → 646.42, s17 inner face → 2208.92)
lands on its drawn line at 100–200, and restricting the vote to pen-compatible
ink moves ~14 of the 253 overturns and no known case, so the vote is not
pen-filtered. The page's strong faces vote for the strong, weak and stair
merges alike (a hairline run is placed by the strong ink it continues, never by
other hairlines); the centerline merge gets no votes and keeps the longest
member (a centerline is derived from faces already placed, and no face lies on
one).

## Rejected anchor variants and sweep

Every stronger variant fused thin walls or flipped rules: seeding longest-first
re-decides membership against the anchor's line and the 4px offset tolerance is
transitive — s01's stair stringer, end to end with a 5.75px jamb nib's face at
mid-thickness, 2.75px off one face and 3.0px off the other, anchored the run
and BOTH faces joined it, the nib could never pair and the door plug beside it
lost its anchor (the swing square was fenced out of the landing, −4,449 px²);
re-anchoring BETWEEN passes fuses them the same way one pass later; and taking
the anchor's direction reversed p1/p2 on runs whose line did not move, which
`_demote_lattice_faces` is sensitive to — on s18, 57 faces were newly
lattice-demoted with identical membership and positions, among them two 1.75px
wall belts (y 800–843 and 1271–1292, x 1841–2578), and 5 confirmed rooms were
lost; with the direction kept, 15 non-wall faces. Corpus sweep of the shipped
form against main: no confirmed entity lost, the same 71 pre-existing returned
false positives, 91 room outlines move by 1–4px strips (s01 WETROOM top edge,
s03 room_0000 left edge and s15 room_0007's bottom edge onto their drawn faces;
s03 room_0013/0016 return EXACTLY to main's polygons; s17 room_0016 loses a
1,600 px² tab into the FIRE EXIT band and s18 room_0008 a 2,912 px² jog into
the entrance side-light), and five new REVIEW rooms: s17 room_0022, the real
SH/WC split off the landing (a win pending the user's verdict); s17 rooms
0015/0034, 21px-deep window-reveal slivers (~3.1k px²) between each window's
seal and the 1.75px cavity wall's true inner face, because that face now
measures 37.0px from the outer one — over `WALL_MAX_THICKNESS_PX` — so the band
no longer pairs across its windows (the stub-hung face measured 35.5; the cap
and the blind-window counting are their own iteration; the third sliver of the
longest-member form, room_0036, no longer appears, nor does the returned s18
legend-box FP at (2126,2532)); s15 room_0016, a 132×43px pocket between two
dash rows: the sheet draws its dashed boundary lines as separate 14.8px strokes
in a 2.0px pen, each a strong face, and ~20 of them collinear within reach
outvote a real 59px wall face (paths 5465/5467, 3.0px) that merged with three
of them, so that face moved 1.75px onto the dash row's line and the pocket
sealed — a collinear row of equal short pieces at equal gaps is a DRAWN DASH
LINE, never a face, and excluding such rows from the vote (and from face
collection) is the next iteration; and s18 room_0000 (0.69), the external ramp
between its balustrades, whose bottom seal is the 70.7px landing edge across
the ramp at y=990.23 (paths 1508/2984/3169): identical geometry in both trees,
LATTICE-DEMOTED on main as a rung of the balustrades' striped field and KEPT on
the branch, because a neighbouring rung moved by the vote broke the equal-pitch
chain — `_demote_lattice_faces` is sensitive to sub-px rung positions as it is
to run direction, the same knife-edge, its own iteration.

## Known gap: glyph-outline fill rings

Known gap, a separate iteration: (b) glyph-outline fill rings — s18's black
class is rated wall by 1,328 of them, their long thin equivalent rectangles
reading as bands — enter the class rating and the barrier area, and a
glyph-ring exclusion is the fill analogue of `_vector_text_indices`; and the
same triangulation means each ring is dilated ON ITS OWN, so the dilation's
mitre join is capped at `ROOM_RING_MITRE_LIMIT` (2.0): shapely's default limit
(5) lets the join at a triangle's acute vertex run 5× the 2px dilation past the
ring — a 10px tab in the room outline beside every band end and jamb nib
(measured on s03 corridor room_0014: 8×3.7px tabs at the party band's end,
184/184 wall-fill rings are triangles; s18 936/1380 rings spike; s02 7 fill +
15 white rings) — while a mitre ratio of 1/sin(θ/2) is 1.41 at a right angle,
2.0 at 60° and 2.61 at 45°, so vertices of 60° and wider keep their mitre and
sharper ones bevel (overshoot ≤ 2px); a thin band's triangles split each
rectangle corner ~5°/~85°, so the wide half still mitres the band's dilated
corner and only a near-square fill (45°/45°) chamfers ≤ 2px — this caps the
spike; and seam-CONNECTED wall-rated rings are unioned back into the polygon
the exporter split before they become `fill_polygons` (`_fill_ring_components`
over the adjacency `_fill_seams` returns alongside the seam indices — only
rings sharing a two-sided-fill seam group, never merely touching same-fill
rings, so an abutting fixture block never merges into a band), so a band
dilates as the rectangle it is and the bevel residue vanishes (s03: 184 rings →
76 polygons, default-mitre spikes 184 → 11 lone/unrated triangles; s02 46 → 44;
s18 1380 → 1357 with 897 still acute — its rings are unshared slivers, which
the cap alone handles);.
