# Room detection rules

Extracted verbatim from CLAUDE.md. The rules of `detection/rooms.py` -- rooms
are the connected free-space components left after subtracting barriers. Every
rule here is a drawing convention backed by margins measured on named sheets;
the numbers are the asset. See `docs/wall-network-rules.md` for the network
this consumes, and `docs/scale-normalization-findings.md` §4 for which
constants scale with drawing scale. The four barrier tiers are split across
both documents: tiers (1) wall solids and (2) wall-fill polygons are in
`docs/wall-network-rules.md` under "Pairing — plain, thick and through tiers"
and "Fill rings and class rating"; tiers (3) thin buffers and (4) white rings
are below.

## Barriers are allowlisted — the four tiers

Barriers are ALLOWLISTED wall evidence, not all linework — room-interior ink
(floor-tile grids, furniture outlines, sanitary symbols, text masks) must not
chop the free space.

## Thin buffers and white rings (tiers 3 and 4)

(3) thin buffers of QUALIFYING faces only — paired into a centerline, outlining
a wall-rated fill, wall-layer-hinted, or stroked at ≥
`ROOM_BARRIER_STROKE_RATIO` (0.75; raised from 0.66 — random-size patio paving
joints evade the equal-pitch lattice demotion and measure 0.70 (1.05 vs the
1.50 reference on 5-1133), fencing patio cells against exterior door plugs and
the bay wall into phantom door-bearing "rooms" at 0.81–0.90 confidence, while
every real LONE barrier face on both reference PDFs measures ≥ 1.00; the
lone-face gate can sit above the pen of the lightest real walls because those
pair and seal through their segments) × the length-weighted median stroke of
the paired wall faces (`wall_stroke_reference`); a STROKED face penned under
that gate whose only claim is pairing must additionally have its own segments
cover ≥ `ROOM_PAIRED_FACE_MIN_FRAC` (0.5) of its run — pairing is
path-index-granular, so one 22px sliver pairing two paving joints 14px apart
qualified a 230px tile line full-length and re-fenced the bay-corner patio
after the ratio raise; noise measures ≤ 0.36 paired extent, real sub-gate
paired faces ≥ 0.71; an UNSTROKED face (material-backed hairline partition,
fill outline) short of that fraction is not dropped but CLIPPED to the run
where it bounds wall material (`_backed_extent`): its own segments' bands, the
spans walls.py found hatch/blocking within half a band thickness of either
flank (`WallFace.backed_spans` from `_face_material_spans` — clusters of ≥ 4
diagonal marks at hatch gaps, at the weak-pair density, each padded by its own
median pitch — the band ends one stroke past its last hatch, never a cluster
gap; either flank because s02's plaster-skin hairline runs 3px outside its
hatched core, so the hatch never 'hugs' it; and a mark centred ON the face
within `WALL_WEAK_MATERIAL_EDGE_PX` is a dimension tick straddling its line,
not hatch — s02's '600' ticks stand 48px past each band's last stroke and
otherwise joined the clusters, notching the mouth 80px in at each end), and any
remaining piece a confident (≥ `ROOM_OPENING_MIN_CONFIDENCE`) door overlaps
along the run within `ROOM_OPENING_SEAL_PX` across it — a sliding/garage door
drawn closed is a panel plus a track line across the whole structural opening,
and that line is the in-plane evidence its plug shadows (s02 GD5: 120px panel
in a 200px opening, the 74px of track beyond the panel seals the WC doorway).
The plain remainder is joinery: the collinear merge chains every same-line
hairline piece into one face, and s02's joinery pen draws both the wall skins
and the front of the built-in 'coats' cupboard between them — one 369px face
paired over its two ends (0.38) with 210px of free-space run between, 4 marks
in two dimension-tick pairs 158px apart (1.7/100px, no cluster), no door —
which fenced the cupboard out of the HALL (room_0008 vs room_0005; the merge is
the drawn convention: a built-in wardrobe open to its hall is hall floor);
hatch strokes are excluded unless they outline wall fill (a corner post's short
diagonal edges are material, not hatching), and faces inside a door bbox are
excluded so the open leaf can't slot the swing area; thin buffers use
`ROOM_LINE_BARRIER_PX` = `ROOM_WALL_DILATE_PX` (2.0) with SQUARE caps so a
face's buffer and its pair's dilated solid put the room boundary at the same
standoff and meet flush at corners — a 0.5px standoff mismatch plus flat caps
leaves pen-width corner notches at every barrier-tier transition, which survive
the free-space opening (filling them would be extensive) and which
`ROOM_SIMPLIFY_TOL_PX` then redraws as long shallow diagonals (measured on
floor-plans room_0012: an 83px straight pier face came out as a 2px slant); (4)
white (background-fill) rings — a ring mostly covered by the text written
inside it is a text mask (dropped, `WALL_WHITE_TEXT_COVER_FRAC`); textless
band/post-sized white rings are hollow-wall/joinery candidates, accepted in
rooms.py when they touch wall material INCLUDING door/window bboxes
(`_accept_white_walls` — hollow runs are interrupted by their own openings;
only doors ≥ `ROOM_OPENING_MIN_CONFIDENCE` count as anchors, so a phantom door
detected on a white fixture symbol cannot turn the fixture into wall; and a
ring fully inside a confident door's bbox is the OPEN LEAF drawn in the same
white-rectangle signature — it would anchor on its own door's bbox and notch
the swing out of the room, so it is withheld from candidacy entirely, while
fallback-tier doors get no such veto because they are typically detected ON
white joinery rectangles whose rings ARE the partition, and sliding doors
(`assembly_type` "sliding") are exempt for the same reason — their panels lie
in the wall plane by construction (drawn closed across the opening or parked in
the pocket, never across a swing square), and withholding them deletes the very
partition the run-bridging seals the doorway with (measured on 5-1133 GD5:
parked pair, bbox covers only half the doorway, rooms merged), then bridged
across open spans with band-shaped convex hulls (`_bridge_white_runs`,
wardrobe-divider runs) — but a bridge only closes an OPEN span: touching rings
(hollow-wall cavity segments chain contiguously through corners) union into run
components first, candidate pairs are taken shortest-gap-first, and pairs
already connected never bridge. Between two small cavity segments on
perpendicular runs of one chain, the redundant hull is thin enough to pass the
band test and chords diagonally across the room corner — that chord (not the
arrowhead linework, which never qualifies as faces) was what notched room
outlines around leader arrows. Opening seals at the surviving doors/windows
complete the barrier set.

## Jamb rings and door linings

A JAMB NIB or door-stop block drawn as a small closed STROKED outline — a 4–8
segment fill-less ring or a lone stroked `re`/`qu` no larger than
`WALL_MAX_THICKNESS_PX` a side (`_collect_stroked_rings`, exposed as
`WallNetwork.stroked_rings` like `white_bands`) — is wall material when it sits
where a jamb sits (`_accept_jamb_rings`): penned at or above the lone-barrier
stroke gate in a wall pen, not lying fully inside a door zone (the open leaf
and the threshold share the signature), and touching BOTH drawn wall material
and a confident opening's bbox — no proximity, a block one pixel short of the
band is not a jamb (measured on s03 corridor room_0014: the nibs beside
door_0007/door_0019 are 12×5.3px and 12×9px L-shapes with a door-stop rebate,
paths 15805–15816 in the 1.5px wall pen, every edge under the 11px face floor,
so they had no barrier at all and the corridor edge bulged over them to the
door plug, x=3749 against the nib face at 3740; fixture symbols of the same
shape — sockets, cistern boxes, tiles — float in the room or hug a wall with no
opening, and the corpus sweep changed no entity on any sheet). The pen gate can
never admit a DOOR LINING — the frame block a joiner fits between the jamb and
the leaf, drawn in the joinery pen as the same small stroked ring (s04
door_0002: two 12.4×14.5px `qu` rings at 0.56px grey against a 1.19px black
wall pen, ratio 0.47, on a detail layer) — yet it is the reason the structural
opening is wider than the leaf (s04: 112px opening, 90px arc, a lining each
side), and without it the 12px plug extension reached 1px into the jamb, the
hinge edge's anchor coverage measured 3/7 = 0.43 < 0.5, no plug qualified, and
the dilated-bbox fallback fenced the swing square out of BATHROOM 01 and held
the corridor below 12px short of its own wall. So a ring failing the pen gate
is admitted on POSITION alone (`_is_door_lining`): a confident opening's bbox
lies beside it along one axis (its across-range reaching the ring within the
barrier tolerance — a swing bbox spans the band when the hinge sits on the far
face, and merely abuts it when on the near face), and shifting the ring one
ring-length along that axis AWAY from the opening lands ≥
`ROOM_LINING_IN_BAND_FRAC` (0.80) of it on drawn wall material whose span
across the axis there is at most the ring's own depth plus the two 2px
dilations plus `ROOM_LINING_SPAN_TOL_PX` (4) — the ring continues the band it
stands in (s04: 14.5px ring, 18.5px dilated band span). A fixture box hugging a
wall's room-side face beside a door shifts along the wall onto room floor (0
cover), and one wedged between a door and a perpendicular return wall shifts
INTO that wall, which then spans the whole across probe. The band the ring
continues is not always BEHIND it: a door hung at a wall junction has its jamb
at the corner, so the lining there shifts into the perpendicular band exactly
like the wedged fixture (measured 2026-09-04 on s04 door_0001, the MASTER
BEDROOM door, whose top jamb is the corner where the divider meets BATHROOM
02's bottom band: the 14.2×12.4px lining, path 949, shifted up lands in that
band, 31.3px across against the 22.2px probe, while its twin at the bottom
jamb, path 946, shifts onto the divider — 18.2px — and is accepted; with the
top jamb 12.4px past the leaf bbox the doorway plug's anchor coverage was 3/7 <
0.5, no plug qualified, and the dilated bbox fenced the swing square out of the
bedroom, −10,345 px², and a 10px strip out of the room below). A doorway is cut
OUT of a wall, so the wall resumes beyond the far jamb whatever happens at the
near one: the ring is also a lining when the strip of its own across-range one
to two ring depths past the opening's far edge — past the far jamb's twin
lining — is drawn wall material with the ring's own cross-section (the same
cover and span gates); the wedged fixture's across-range lies on the room side
of the wall plane, and beyond the far jamb that strip is floor. Corpus sweep:
verdict-identical, only s04 rooms 0002/0004 change (+10,745 / +1,127 px²), no
other polygon moves. Before any of this, door candidates whose bbox is mostly
covered by the text written inside it (`ROOM_OPENING_TEXT_COVER_MAX` 0.60 —
"WALL TYPE 1" tag boxes detected as leaf rectangles; same principle as the
white text-mask rule) are dropped from the room stage entirely: no seals, no
white-wall anchoring, no face exclusion under the bbox — real swing bboxes
measure ≤ ~0.45 text cover even with a room label crossing them.

## Window seals

A straight window's bbox lies in the wall band and seals as-is, but a DIAGONAL
window (angled bay face) has a square-ish axis bbox that overhangs the wall
plane on both sides, so it seals along its glazing diagonal instead
(`_window_seal`, picking the bbox diagonal matching `glazing_angle_deg`,
buffered to the band's measured half-thickness) — measured on 5-1133, bay
window W11's square seal bridged the bay wall to the terrace setout lines and
fenced a paving pocket into a phantom room.

## Door plugs — qualification and profile

A door bbox covers the swing — room floor, not wall — so it is replaced by thin
plugs along its wall-plane edges (`_door_plugs`), keeping the swing inside the
room and splitting adjacent rooms exactly at the wall plane. An edge qualifies
by the coverage profile of wall material hugging it (sampled along the edge,
extended `ROOM_OPENING_SEAL_PX` past the bbox to reach jambs the arc stopped
short of): either an interrupted wall run (both ends anchored, middle empty —
the open-doorway case) or a drawn-through wall plane (near-total coverage —
existing-opening sills and closed sliding/garage panels, common on working
drawings, where the plug just shadows drawn linework). End anchors are measured
over a jamb-scale window (`ROOM_PLUG_ANCHOR_WIN_PX` 24px, never larger than the
legacy n//4 quarter): a jamb is jamb-sized regardless of doorway width, and on
a 165px garden pair the quarter diluted real 45°-bay jambs to 0.42 (gate 0.5)
while a perpendicular edge crossing the angled wall obliquely PASSED as an
interrupted run (measured on 5-1133 door 0121: the true doorway edge got no
plug, the parked-leaf edge got a phantom one, and the purple bay room leaked
through the doorway while the phantom plug fenced terrace paving into phantom
rooms).

## Vetoed edges — garden pairs and sliders

A garden pair's parked-open leaf edges (`_open_leaf_edges`, keyed on
`swing_layout == "garden"` + `leaf_bbox_a/b` lying along opposite bbox edges)
are vetoed outright — the parked leaf is room/garden floor, never wall plane —
and so is the swing-extent edge the merged `opening_line` lies along: the chord
joins the two arc endpoints farthest apart, which for a garden pair are always
the parked leaves' open TIPS (tip-to-tip spans the full opening W,
tip-to-closed-end only ~0.71 W), so the chord edge bounds the swing squares and
never the doorway (measured on floor-plans door_0016: the swing-extent edge
anchored on the two jamb walls continuing past the doorway, pattern-matched an
interrupted run, and its phantom plug held the bedroom outline 5px short of the
doorway — the garden-pair analog of `_restrict_swing_plugs`; a diagonal garden
pair's chord matches no axis edge and adds no veto) — while french pairs keep
their leaf edge eligible because their collinear leaves are drawn closed IN the
wall plane. A sliding door's short-end edges are vetoed the same way
(`_sliding_end_edges`, aspect-gated at `ROOM_SLIDE_END_ASPECT_MIN` 2.0 —
sliding bboxes elongate along the wall by construction, measured 9.2–24× on
both reference PDFs): the short ends CROSS the wall band, so the only profile
they can match is a full-cover re-assertion of that band, and their plugs are
thicker than the linework they shadow (measured on floor-plans door_0011: the
bottom end-edge plug bit a 12×6px square out of room_0010 and a 7×10px notch
out of room_0005).

## Plug cross-section fit

A qualified plug takes the JAMB'S CROSS-SECTION, not the bbox edge's: its
across-extent is fitted to the dilated wall material at the anchor samples each
tail touches (the widest probe per end — the band body, never the 4px
face-buffer sliver a sample at the jamb's very end grazes — intersected across
the two ends so the plug stays connected to material at both; it only ever
shrinks inside the ±`ROOM_PLUG_HALF_WIDTH_PX` envelope and never below a line
barrier's 4px, falling back to the full envelope when the ends disagree). A
swing leaf hinges at the band's inner FACE, so the hinge-edge plug centred on
that edge with the 5px half-width stood 3px proud of the wall's own 2px
standoff — a step at every such doorway that `ROOM_SIMPLIFY_TOL_PX` (2px)
redrew as a slant across the whole room edge (measured on s03 BATHROOM
room_0008: right edge x=1183.8 beside door_0003 against 1186.7 along the 6px
band below it, simplified into a 110px lean). The fit is shrink-only, so the
far side of a hinge-edge plug still stops ~3px short of the band's outer
barrier line (s03 corridor room_0007 at door_0003, x=1193.8 against 1196.7) —
growing a plug to the jamb's full cross-section is a separate rule, because a
doorway whose both tails cross perpendicular return walls has no narrow probe
to bound it.

## Tail trim and clip

A qualified plug's `ROOM_OPENING_SEAL_PX` end extensions are also TRIMMED back
to the farthest profile sample still touching wall material within the plug
half-width: a tail exists to reach into the jamb the bbox stopped short of, and
one hanging in free space — qualified by the loose hug of a parallel band, or
overshooting a crossed jamb's far face — seals nothing and stamps a plug-width
notch into the adjoining room (measured: door_0002's top-left tail floated at
8.7px and notched room_0005 beside the jamb; the same tails bit the WC edges at
5-1133's leaf_pair sliding doors 0013/0014), while any clearance gap a trimmed
tail no longer bridges is far thinner than the `ROOM_GAP_CLOSE_PX` pinch, so
the rooms it separates still split. And since W-gate iteration 3 step 5
(2026-09-04) the trimmed tail is then CLIPPED to the END of the material it
touches (`_clip_plug_tails`): "touching" is a distance test, so the farthest
touching sample sits up to `ROOM_PLUG_HALF_WIDTH_PX` past the end of an island
or a band the plug shadows, and the tail stamped a plug-width stub into the
free space beyond it — measured on s02 door_0050, the 0.35 fallback door on the
"A" section-marker bar (a filled ring islanded in BEDROOM 2), whose two
full-cover plugs at seal 15 ran 4.8px past each end of the bar and pinched the
20.5px neck to the wall under the 16px free-space opening, wrapping the outline
around the bar column; at seal 12 the sample phase happened to miss the bar,
but 45 of s15's 52 band-end tails, all 6 of s01's and 3 of s02's overshoot
1.0–4.4px, each a stub on a room edge that `ROOM_SIMPLIFY_TOL_PX` then redrew
as a slant (s17 room_0027: a 3.8px stub at the top of a 467px corridor edge
leaned the whole edge, 685 px²). The convention: a tail exists to reach the
jamb the bbox stopped short of, and it ends where the material it touches ends,
never beyond it — material continuing past the reach keeps the whole tail,
material ending inside the reach ends the tail there (`_tail_material_end`, the
farthest material inside the tail's own touch envelope). The clip runs AFTER
the plug is classified — kind, hinge restriction and the fallback tier's
in-wall fraction are all decided on the sample-trimmed plug `_door_plugs`
returns — because the in-wall gate's calibration (phantoms ~0.77, on-plane
0.84+) has the out-of-material tails in its denominator: clipping first raised
the fractions and let 57 more fallback-tier plugs through on s15 (263 → 320),
seven of them cutting 8–38 px² notches into s15 rooms 0006/0010/0014/0020/0021
and s17 rooms 0022/0026 (unsimplified polygons; with the clip after the gate no
room loses any free space). Corpus sweep: verdict-identical (71 returned FPs, 0
lost, 5 unreviewed), 22 room polygons on s01/s02/s03/s11/s15/s17 gain 6–742 px²
each (+3,377 px² in all; s01 +70, s02 +12), nothing added, removed or lost; and
with it s02 is identical to its baseline at seals 13, 14 and 15 — what still
blocks the seal is s15's dash rows at ≥ 14 and s01's plug-fit flip at 13–14.

## The jamb-seeking tail

And since W-gate iteration 3 step 10 (2026-09-05) a doorway plug's tail SEEKS
its jamb when the fixed reach finds none (`_door_plugs` with `seek_edges`,
`_seek_jamb`): a doorway is cut out of a wall, so its latch jamb is wall
material the plug has to reach, but the reach is fixed in advance (bbox ± SEAL)
while the jamb's distance is drawn — s01 draws its swing symbols short of their
openings on the latch side (a 671mm leaf in an 847mm opening; the census of 378
kept doorway ends at true scale: median 0mm, p90 34, then s01's four swings at
187–219mm, s05 135, s17 110, s18/s08 102, every other sheet ≤ 51), so at its
true 1:92.2 factor the hall door's 8.13px tail stopped 4.1px off the corner
jamb block's right face and the hall merged with the living room. On a HINGE
edge of a ≥ `ROOM_BBOX_SEAL_MIN_CONFIDENCE` single (`_seek_edges`; a garden
pair or slider pins no hinge, so s01 door_0015's piers at 281mm stay a plane
stamp) whose profile anchors at exactly ONE end — the other end's window
neither half-covered nor touching — the tail on the failing side looks outward
from its corner for the nearest wall material within `ROOM_PLUG_JAMB_SEEK_PX`
(29.5px = 250mm at 1:50, W-class; the material's outline buffered by the plug
half-width and cut by the edge's ray, so a perpendicular jamb return, a band
end and a fill ring all count while opening seals never do), extends that end's
reach to the material plus the anchor window and re-profiles with asymmetric
reaches; only the interrupted signature may result (a doorway is empty between
its jambs — a sought profile reading "full" is a drawn-through plane the fixed
reach did not assert and the seek must not either), the `local` material clip
is widened to SEEK + anchor window + NEAR + 4 (inert alone: corpus
byte-identical), and `_clip_plug_tails` takes a sought tail's own extent as its
reach so the clip does not cut it back off the jamb. Measured
(`tools/census_scratch/step9/seek_census.py`, every door on 18 sheets at their
factors re-profiled with and without the seek): the plug outcome changes on
exactly four doors, every hit a PERPENDICULAR wall — s01 door_0002's hall
doorway at 0.542 (the block's right face, 9.6px = 149mm to the first touching
sample, 191mm to the face; the hall is matched again, rooms 9/12 with the three
stair verdicts still to retire and the same 18 unreviewed as step 9), s14
door_0008 (an 11.5px band 9px = 76mm out, a touch inside the fixed reach whose
anchor window straddled the corner into the doorway; polygons identical), s17
door_0004 (a 0.95 single drawn CLOSED in its doorway: a 32.5px band 14.25px =
121mm past the latch corner; the confirmed room_0018's outline had wrapped
under the closed leaf into its threshold, −1,163 px², IoU against its recorded
polygon 0.55 → 0.57) and s18 door_0018 (a 139px face 10.5px = 178mm out,
plug-less before; the day room rooms 0002/0003 regain +695/+30 px² of doorway
strip and swing corner); the one false hit within 300mm on the corpus, s14
door_0007's open-leaf tip reaching a wall-fill chevron ring at 296mm, lies
1.18× past the cap and no leaf tip seeks anywhere. Corpus sweep:
verdict-identical (0 lost, 68 returned FPs, 0 REVIEW), s01/s02 at f=1.0 entity-
and polygon-identical, 17 sheets polygon-identical.

## Plane stamp and the bbox fallback

Doors with no qualifying edge first retry plug qualification with their own
withheld leaf rings added as material — a leaf drawn CLOSED lies in the wall
plane and may be the door's only evidence there (timber gates in fence lines),
so the plug shadows the leaf instead of the dilated bbox stamping the swing
square into free space — and only then fall back to the bbox stamp. That stamp
is PLANE-RESTRICTED (`_plane_stamp`, W-gate iteration 3 step 8, 2026-09-05):
`box(bbox) ⊕ SEAL` grew SEAL across the door's plane as well as along it, so
the whole swing square left its room and the room on the far side of the wall
lost a SEAL-deep strip at every plug-less door (measured at seal 15 — 18
plug-less doors corpus-wide, 7 touching a room: s17 door_0001, the 0.83 single
on the confirmed SH/WC whose recorded outline WAS the stamp's L-shaped edge,
8.5k px² of swing square; s01 door_0015's garden pair, 1.4k on the living room;
s04 door_0003's slider, 1.5k on each flanking room; s16 doors 0003/0004 and s18
doors 0018/0271 at f=0.5). A door's wall plane lies along a bbox edge its own
evidence has not ruled out — a single swing's plane passes through its hinge
corner, so it is one of the two hinge edges (`_swing_hinge_edges`; the far
edges bound the swing square, room floor), a slider's long axis IS its wall
(`_sliding_end_edges` vetoes the short ends), a garden pair's parked leaves and
tip chord are vetoed (`_open_leaf_edges`), and a door whose evidence pins
nothing keeps all four (a ring whose interior dissolves as door floor) — and
each remaining edge is stamped as the plug it would have carried had its
profile qualified: the edge line at ±`ROOM_PLUG_HALF_WIDTH_PX`, with a SEAL
tail at each end that is kept as far as wall material HUGS its spine (within
`ROOM_PLUG_NEAR_PX`, the profile's own loose hug — wider than a qualified
plug's touch envelope because no sample proved these jambs are in reach) and
ends where that material ends (`_tail_material_end`): a doorway tail runs into
its jamb, a leaf edge's hinge-end tail crosses the plane and stops at the
band's far face instead of stamping a stub into the far room, and a tail
hugging nothing (the leaf's free tip) is dropped. Measured on the corpus's 181
hinge-derivable plugged singles: the kept plug lies on a hinge edge 177 times,
that edge sits ON its wall face (median 0.0px, max 4.2px off the dilated
material — inside the plug's own cross-section), the interrupted plugs' jambs
sit ≤ 13px past the bbox corner (s01 door_0015's piers at 18px are the
plug-less outlier, reached by the hug envelope and closed by the 16px
free-space pinch), and the leaf-axis "open leaf" convention names the plane
edge 159 times against 5 for the closed-leaf convention — 3% wrong, so the
stamp never picks ONE hinge edge. The stamp is a subset of the old one
everywhere, so a room can only gain floor; what it can do is let two spaces the
old stamp's FAR edges happened to separate merge — on s18 a 0.75m strip of
patio under door_0271's parked bottom leaf, otherwise fenced by the "4200
Overall Extension projection" glyph-outline rings (gap (b),
`docs/wall-network-rules.md` §"Known gap: glyph-outline fill rings"), was a
confirmed `partial` room and vanishes, the one LOST line of the step-8 sweep
and the user's call. The bbox fallback is the one seal with NO evidence of its
own (every plug profile qualifies against drawn wall material; the stamp is
pure trust), so it requires the door to survive the pipeline's own conviction:
`ROOM_BBOX_SEAL_MIN_CONFIDENCE` 0.55, mirroring
`OFFLINE_MIN_CONFIDENCE["door"]` — detect_rooms consumes post-suppression
candidates BEFORE the offline floor, and a door the pipeline itself rejects
must not reshape a room outline (measured on 5-1133: the 0.52 bath-fixture FP —
single_line_leaf on a toilet pan corner, no_wall — stamped a 68×50px notch into
the FAMILY BATH edge, while no real door on either reference PDF uses this
fallback; all seal through plugs). Plug seals stay available from
`ROOM_OPENING_MIN_CONFIDENCE` (0.40; doors are penalty-only in
cross-validation, so fallback tiers never climb back over). Fallback-tier doors
(`DOOR_FALLBACK_CONFIDENCE` 0.35, deliberately capped under the offline floor
and kept only for Gemini arbitration — label boxes, glazing mullions, section
markers) seal exclusively through plugs that carry their own evidence: the
interrupted-run profile (the doorway signature — a real low-confidence sliding
door between jambs still splits its rooms), or a drawn-through plane the plug
actually LIES IN (≥ `ROOM_PLUG_IN_WALL_FRAC` 0.80 of its area on drawn wall
material, so it only re-asserts existing barrier and seals hairline gaps in it
— measured phantoms floating NEAR a wall peak at ~0.77 overlap while on-plane
plugs measure 0.84+). Full coverage by mere proximity is NOT evidence — that is
how an annotation box hugging a wall band would stamp a free-space notch into
the room outline — and a phantom door in open space contributes nothing at all.

## Free-space components and their filters

Drafting gaps are sealed by morphologically OPENING each free-space component
(`ROOM_GAP_CLOSE_PX`, in `_free_space_components`) — the complement-side
equivalent of closing the barrier union, which must NOT be buffered directly:
GEOS silently drops legitimate room-sized holes from the giant multi-hole
polygon (one 22px sliver closing a ring in the kitchen erased bedrooms 2/3 +
hall wholesale); components are filtered by area, page fraction, page-border
contact, hole fraction, erosion, wall-contact ratio, and attachment to a major
wall mass (kills legend tables / dimension frames); a component lying fully
inside a confident (≥ `ROOM_OPENING_MIN_CONFIDENCE`) door's bbox is the
swing/threshold recess fenced by the door's own seals — door floor, dissolved,
not a room (floor-plans' 1800mm garden pairs fenced 105×25px recess strips and
whole swing squares into phantom rooms; folding doors dissolve over a
wall-band-deep zone, bbox ⊕ `WALL_MAX_THICKNESS_PX` instead of ⊕
`ROOM_OPENING_SEAL_PX`, because a parked stack stands off its opening plane by
the threshold depth — the 26px strip between 5-1133's kitchen CL-door stack and
the wall band it serves sat outside the ⊕12 zone, fenced between the band and
the stack's own top plug); and a closet-scale component whose ONLY opening is a
window (`door_openings == 0`, `window_openings > 0`, area <
`ROOM_BLIND_WINDOW_MAX_AREA_PX2` 10k px²) is dropped as the exterior side of
that window — terrace pockets beside 5-1133's bay windows measure 2.7–3.7k px²
while every real window-bearing room on both reference PDFs is ≥ 17k px² and
carries a door; blind window-LESS small rooms stay, floor-plans has real ones
at 3.3–8.5k px² (missed-door cases).

## The wall-recess drop

A door-less, window-less, UNLABELLED component lying IN a wall band's plane is
a WALL RECESS (`_is_wall_recess`) — a chimney breast, pier or duct drawn as a
closed box on the room side of the band with its back open to the band — and is
dropped: it fills ≥ `ROOM_RECESS_GAP_COVER_MIN` (0.65) of the opening-free gap
between two collinear segments of the band, its back edge lies on the band's
OUTER line (within `ROOM_RECESS_BACK_TOL_PX` 1.5 of the barrier standoff) and
it is at most `ROOM_RECESS_DEPTH_RATIO_MAX` (3.0) band thicknesses deep
(measured on s11/s16: six breast pockets in the 17.6px external wall — 46.5px
total, past the scaled thick-tier cap so the front never pairs with the outer
line — cover 0.69–0.85 of their gap, sit exactly at the 2px standoff and run
1.75–2.4 bands deep with no text; s02's "coats" cupboard matches gap and back
edge but is 5.2 bands deep and labelled; real rooms beside a band sit ≥ 3.6px
inside its outer edge (s01 room_0002, s16 room_0009) and carry openings). Text
inside the component vetoes the verdict — a named space is a space whatever its
shape — but sheets whose text is drawn as vector outlines (s11/s16 have zero
text spans) get no such protection, so the geometric gates carry the rule
there. Since W-gate iteration 3 step 17 (2026-09-06) the back edge is read on
the component's OWN boundary runs (`_back_edge_cover`,
`ROOM_RECESS_BACK_COVER_MIN` 0.65), never on its extent: the union, over the
collinear gap, of the runs parallel to the band lying at the barrier standoff
inside either outer line of the band (`ROOM_LINE_BARRIER_PX` ±
`ROOM_RECESS_BACK_TOL_PX`) or ON that line where a wall solid's flat END lies
on the run (`cap_lines`, standoff 0 — exactly as `_run_wall_cover` admits a cap
for the band-pocket covers), over the component's own extent along the gap, the
larger of the two lines'. The extreme-vertex reading (min / max over every
vertex across the band) failed on the step-15 tab: s17's junction — a
perpendicular partition whose paired segment ends ON the band's face line over
its thickness, the face line drawn from its far flank on — puts the component's
boundary on the segment's flat cap at standoff 0 there and 2px inside the line
everywhere else, so the extreme read 0 against the 2 ± 1.5 the test wants and
the tabbed reveal of `TestWallRecessTabbedByAPerpendicularBand` (s17's 35.5px
partition beside an 80px reveal in a 19.25px inner leaf: 31.5px of tab, 0.61 on
the face alone, 1.0 with the cap) read "not a recess" while the same reveal
with the line drawn through read "recess". Measured on every call the rule
receives (72) and every emitted room (236) of all 20 sheets at their factors
(`tools/census_scratch/step17/`): the 14 calls that reach the back edge — the
rule's own population, chimney-breast pockets and piers 0.85–2.94 bands deep in
112–466mm bands, every one dropped today — read the extreme at −2.00 (s10
−2.12) and their runs at 1.00 of their own extent with or without the caps, and
no emitted room reaches the back edge at all (the gap-cover and depth gates
hold the true class out), so the corpus is identical under either reading and
the tab is the runs reading's only instance; over the component's own extent
rather than the gap's length because the gap-cover gate already asks how much
of the gap the component fills (over the gap the same 14 read 0.74–1.00 — the
gates compounded).

## The band-pocket drop

And a component lying INSIDE a band's thickness — not in its plane but between
two of its faces — is the band itself (`_is_band_pocket`): both long SIDES of
the component lie along wall at a spacing of at most
`WALL_THICK_MATERIAL_MAX_PX` (56px = 475mm at 1:50, the thick tier's cap —
`WALL_MAX_THICKNESS_PX` until W-gate iteration 3 step 16, 2026-09-06; its
minimum rotated rectangle's short side plus the two standoffs) — two faces that
could have paired as one wall, plain or thick — so the free space between them
is that wall's material, a window reveal, a hollow cavity, a blocked opening or
a wall drawn hollow, never floor: rooms are wider than a wall by definition,
the lattice rule's premise, and what keeps a real space out of the rule at
thick spacing is enclosure (below), not width. Since W-gate iteration 3 step 15
(2026-09-06) the cover is read on the component's OWN boundary runs, never on
its rectangle's edges (`_side_wall_covers`): the runs parallel to the
rectangle's long axis are classed to a side by their offset from its centre, a
run lies along wall where a face (a segment flank or a barrier-face extent)
runs beside it at the barrier standoff (`ROOM_LINE_BARRIER_PX` ±
`ROOM_RECESS_BACK_TOL_PX`, read where the face actually lies beside the run) OR
where a wall solid's flat END lies on it (`cap_lines` — every paired segment's
end line across its thickness, standoff 0, because a flat-capped solid ends
exactly at its segment's end), and a side's cover is the union of its runs'
wall-lying stretches projected on the axis over the rectangle's length, each
side ≥ `ROOM_BAND_POCKET_FACE_COVER_MIN` 0.65. A rectangle is pinned by the
component's widest point: s17's four reveal strips (rooms 0013/0014/0027/0032)
each end where a perpendicular 35.5px partition meets the cavity wall — the
partition's two faces are drawn unequal (paths 2701/2905), the one at the
strip's end running across the wall to its far face (the strip's end barrier)
and the other stopping at the strip's face line, so the paired segment ends ON
that line, its flat cap forms a 31.5px tab in the strip at standoff 0 and the
leaf's face line is drawn from the partition's far flank on (path 2697) — and
the tab put the rectangle's edge ON the face line the rest of the side lies 2px
inside of, so the edge cover read 0 (0013 [0.0, 1.0], 0032 [0.0, 0.93], 0014
[0.0, 0.04] with tabs at opposite corners tilting the rectangle 0.4°, 0027
[0.0, 0.0]) while the strips' own sides read [0.99, 1.0], [1.0, 1.0], [0.96,
0.99], [1.0, 1.0] — on the face over 0.79–0.93 of the length, on the
partition's cap over the rest (without the caps 0.79–0.93 on the tabbed side).
Measured on every call the rule receives and every emitted room of all 20
sheets at their factors (`tools/census_scratch/step15/`): 58 calls, 11 at or
under the 56px thick ceiling — the four strips, s11's confirmed storage
(1.0/1.0 under every reading), the s12/s16/s18 recorded-FP cells (unchanged)
and s18's recorded-FP sofa-back strip (907,810)–(1079,833), 461mm, whose
rectangle read 0.14 on a notch and whose own sides read 0.90; at the 36 ceiling
the population is one already-dropped s17 reveal under either reading, so the
corpus sweep is verdict-, entity- and polygon-identical (0 LOST / 68 returned
FPs / 0 REVIEW). The strips are now held out by the ceiling ALONE —
38.75/38.75/38.79/40.5px against 36 — and s11's 368mm storage (21.75px at
f=0.5) lies inside the false class's range from a 44px ceiling up (22px at
f=0.5), so the ceiling cannot move until that cupboard is recognised another
way (step 13).

## Band-pocket end closures

Since W-gate iteration 3 step 16 (2026-09-06) a component that wall BANDS close
at BOTH ends is exempt (`_end_closures`, `ROOM_BAND_POCKET_END_CLOSURE_MIN`
0.65 of each end with a wall solid — a paired segment's band, a fill, a white
wall, a jamb block — standing `ROOM_BAND_POCKET_END_PROBE_PX` (7px, paper: past
the line barrier a lone face keeps around itself) behind it, read on the
component's own end runs and unioned over the rectangle's short edge): it is
enclosed by walls on all four sides, a cell of the wall grid, a space whatever
its width, because walls meet at junctions where one STOPS at the other's face
— a wall band never stands across another wall's thickness — while a pocket
inside a wall is closed at its ends by the wall's own interruptions (an
opening's jamb line, a face drawn across the wall, the face of a partition that
meets it). The storage this protects is not "between two walls": s11's
confirmed "storage in utility" (1078,1597)–(1095,1704), 368mm at f=0.5, is a
door-less built-in cupboard whose left side is a 5.7px partition (paths
8387/8388) and whose right side is its FRONT drawn as one 1.5px line (path
8383, the utility behind it — the s02 "coats" class in the wall pen, keeping
its barrier rights because 21.75px is over the 1:100 cap), so "a wall solid
behind both sides" reads 1/2 on it exactly as on s17's dropped 25.25px reveal
(the outer leaf behind one side) and separates nothing; neither does a
vector-text label (s11 draws its labels as glyph rows, 696 strokes, and none
lies inside the storage — `_vector_text_indices` strokes inside read 0 on every
call of the corpus) nor the pen (every face in play is the one black 1.5px
pen); what closes the storage is the 6px band above (paths 8346/8347) and the
17.6px external wall below (8333/8335): end closures 1.0 / 1.0. s17's four
strips are a wall drawn HOLLOW — the 313mm wall as two lines with rooms on both
sides, the existing-wall outline convention, its faces (paths 2697 / 2756)
drawn only along the strip and the inner leaf pair (2753/2754) on the room side
of x=948.67 below the doorway, so no leaf resumes collinear with either face at
any reach — closed at one end by the doorway's jamb line (a jamb block behind a
third of it) and at the other by the partition's top face continuing across:
closures 0.345 / 0.0, 0.338 / 0.201, 0.001 / 0.001, 0.0 / 0.0; the 25.25px
reveal 0.0 / 1.0 (the cavity pair and inner leaf resume at one end only, 2px
past it). 0.65 sits 1.54× under the storage and 1.88× over the strips. Measured
on every call (58) and every emitted room (244) of all 20 sheets at their
factors (`tools/census_scratch/step16/`): the only other enclosed call at
pocket spacing is s16's recorded-FP partition box (2507,1323)–(2527,1401), 1.0
/ 1.0, which stays as today; s18's kitchen-corner box (0.0 / 0.29), s18's
sofa-back strip (0.0 / 0.72) and s12's two unit cells (1.0 / 0.0) are not
enclosed. The exemption recognises the fully WALLED cupboard, not every
door-less space: the corpus's other confirmed door-less spaces — s07's cupboard
(0.06 / 0.06, a box of lone lines with a single front line), s20's passage (0.0
/ 1.0), s15's space (1.0 / 0.5) — sit at 599–610mm and are held out by the
spacing ceiling alone (1.26–1.29× over 475mm; no ceiling clears 1.5× both ways
between the strips' 343mm and their 599mm). Corpus sweep with the exemption at
the 36 ceiling: verdict-, entity- and polygon-identical (0 LOST / 68 returned
FPs / 0 REVIEW), by construction — the rule's population at 36 is the one
reveal. Pinned by `TestBandPocketEnclosedByWallBands` (a 26px cupboard between
a partition and a 6px front panel, closed by 8px bands, stays; the same cell
closed by lines with a 10px jamb nib on each end is dropped; both bite). Pinned
by `TestBandPocketTabbedByAPerpendicularBand` (s17's junction as drawn;
bite-proven) (measured on s17: the 1.5px-pen cavity wall is drawn as four
lines, leaf/cavity/leaf at 11.75/12/13.25px, 37px in all — over the cap (at the
census's tried-and-reverted 40 the outer and inner faces paired as one plain
band and the reveals were solid before the room stage saw them, which removed
four recorded reveal phantoms), 0 diagonal marks in the band, so neither the
thick tier nor the through tier can pair its outer and inner faces — and each
leaf pairs as its own segment; at each window the two middle lines stop, the
glazing runs mid-leaf in the continuous outer leaf, and the reveal between the
outer leaf's inner face and the wall's inner face is a 25.25px strong pair that
`_claims_far_side_pair` drops — the outer-leaf pair shares its face on the far
side and the band carries no fill or hatch — whose docstring's premise, "an
unhatched cavity is a closed sliver the room stage erodes away", holds only
under 2 × `ROOM_GAP_CLOSE_PX`: the 21px-deep reveal survives the 8px opening
and came out as rooms 0015/0034, 3.1k px² at 0.85; the collinear-gap recess
rule sees 0034, whose inner pair resumes on both sides, but not 0015, where the
next window's reveal adjoins it across a 6px jamb block; corpus-wide the
signature matches exactly those two, the narrowest confirmed room otherwise
being s11 room_0018, a 19px-wide "storage in utility" at f=0.5 whose faces sit
21.75px apart against the scaled 18px cap — a 1.2× margin — with every other
confirmed room ≥ 52px wide at identity; the 11 recorded-FP pockets on
s11/s12/s16/s18 at 1.2–2× the scaled cap are the same class one band deeper and
need a second discriminator).

## Entrances

Both drops and the recess rule count ENTRANCES, not seals
(`ROOM_ENTRANCE_MIN_CONFIDENCE` = the offline door floor's mirror
`ROOM_BBOX_SEAL_MIN_CONFIDENCE`): detect_rooms consumes candidates before the
floor, a rejected candidate's evidence-bearing plug still seals — and still
counts toward `door_openings` and confidence — but its tail touching a pocket
cannot vouch that the pocket is entered (s17 door_0039, a 0.48 single_line_leaf
lying in the next reveal, whose full-cover plugs' 12px tails fenced room_0015's
end, and door_0042, a 0.35 arc_fallback sliver in the cavity, gave both pockets
`door_count` 1 and vetoed the blind-window and recess drops; corpus-wide 16
rooms carry only sub-floor doors and none is a closet-scale window pocket or a
recess — the nearest, s17 room_0018 at 13.3k px² with a window and a 0.35 door,
clears the 10k blind cap by 1.33×); and since W-gate iteration 3 step 14
(2026-09-06) an entrance is a seal that RUNS ALONG the space's boundary
(`_entrance_run` ≥ `ROOM_ENTRANCE_MIN_RUN_PX`, 29.5px = 250mm at 1:50,
W-class): a doorway INTO a space is cut through one of its bounding walls, so
its plug lies along that boundary over the doorway's width, while a doorway cut
through the wall a strip lies INSIDE of — its plug collinear with the strip,
meeting the strip's end — or a neighbour's doorway whose tail ends at the
strip's face touches it over the plug's own cross-section only (2 ×
`ROOM_PLUG_HALF_WIDTH_PX`), and the any-touch test (a seal within
`ROOM_CONTACT_TOL_PX`) called that an entrance — s17's four reveal strips
(rooms 0013/0014/0027/0032) each end at a doorway cut through the cavity wall
whose 0.95 plug meets the strip's end, and escaped `_is_band_pocket` on it. The
run is the boundary's length within the contact tolerance of the seal LESS the
tolerance's reach past each end, because the tolerance is paper: a crossing
plug's raw contact is 2 × half-width + 2 × TOL (18px at 1:50, 12px at s13's
1:136 against a 13px scaled floor), so no world floor on the raw contact clears
both classes at every factor, while on the net run the classes are ≥ 59.2px on
every confirmed entered room at f=1.0 (s03), 36–43px at f=0.5, 37.3px at
f=0.367 and 47.3px on s01 at 0.542 against 7–10px for the s17 strips and 13.5px
for s04's recorded-FP box (measured per room as the LARGEST run any entrance
seal makes — a neighbour's tail grazes real rooms over 3.6–15px, so never per
seal) — 250mm sits ≥ 2.0× from both on every sheet. The gate feeds only the
entrance count (the blind-window, wall-recess and band-pocket drops);
`door_openings` and the confidence boost still count every touching seal.
Corpus sweep: verdict-identical in counts, 19 sheets entity- and
polygon-identical, s01/s02 untouched; on s04 the recorded-FP box
(1463,1042)–(1558,1131), entered only by door_0000's tail running 13.5px along
its edge, drops as a blind-window pocket, and the recorded-FP stair flight
(1588,1053)–(1762,1131) on the far side of window_0004 returns because the box
was the door-bearing side `_drop_window_exterior_sides` dropped it against — a
trade, net 0, the flight being the stair class (13.5k px², over the blind cap);
the s17 strips become entrance-less and still stay, pinned by their tabs and
the cap. The uncapped complement (`_drop_window_exterior_sides`): a straight
window's bbox is pushed `WALL_MAX_THICKNESS_PX` out perpendicular to the
glazing on each side, and when one side holds a door-bearing room while the
other holds only door-less components, those door-less components are the
exterior that room looks out over — a lower roof, terrace or lightwell — and
are dropped whatever their size (measured on s03: the ground-floor roof, a
striped field fenced by its outline above the PROPOSED BEDROOM, came out as a
133k px² door-less "room" across the bedroom's window). Two entered rooms
sharing a borrowed light both stay, two door-less sides cannot be told apart
and both stay, and a garage whose garage door reads as a window keeps its
verdict because its far side is open ground, not a room; a room counts as "on a
side" only when its polygon overlaps the probe by ≥
`ROOM_WINDOW_SIDE_MIN_OVERLAP_PX2` (16 px²), so grazing a probe corner past a
jamb is not facing the window.

## Limitations and scope

Rooms are heuristic-only: never sent to Gemini, bypass the
`OFFLINE_MIN_CONFIDENCE` floors and NMS, and carry the closed polygon in
`Candidate.evidence["polygon"]` / `Entity.attributes["polygon"]`. Curved
(Bezier) walls are out of scope — only straight `l` faces and filled `re`/`qu`
bands feed the network, so rooms bounded by curved walls leak open and are
dropped. Known limitation: hairline-pen partitions WITH material between their
faces (hatch/blocking) now bound rooms via the weak-pair material gate, but
boundaries drawn ONLY as plain sub-threshold lines (e.g. a fitted-wardrobe run
with nothing between the faces, 0.45px — the same pen as sanitary fixtures)
still do not, so such spaces come out merged into one oversized room; accepting
bare hairline pairs would reopen every fixture false-positive, so that residue
belongs to a future room-label/Gemini arbitration layer, not to the barrier
rules.
