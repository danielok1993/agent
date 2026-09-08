# W-gate iteration 3 — step 17: `_is_wall_recess`'s back edge read on the component's OWN runs (faces at the standoff, wall solids' flat ends on it) — censused both ways on every call and every room, built, swept: corpus identical, the tab fixture closed

Branch `fix/wall-recess-tab-back-edge` from `fix/band-pocket-ceiling-storage`
(acd7157: step 16's two changes plus its graphify chore; main is `83a603c`).
Baseline: that tree's own sweep, re-run in four background groups and
snapshotted for all 20 slugs (`outputs/regress_baseline/<slug>/2026-09-06_19-29-*`
… `19-30-15`) — **0 LOST, 60 returned FPs, 0 REVIEW**, s01 10/10 at its true
factor, the 80 verdict lines byte-identical to step 16's ceiling sweep
(`tools/census_scratch/step17/sweep_base_verdicts.txt`). 2026-09-06.

## The brief

`_is_wall_recess` reads its back edge off the component's EXTENT —
`min(ws)` / `max(ws)` over every vertex across the band — so a tab where a
perpendicular band's flat-capped solid ends (the step-15 fixture's tab) pins
the extent ON the band's outer line, standoff 0 against the 2 ± 1.5 the test
wants, and the verdict flips: a tab-less version of the fixture is a recess,
the tabbed one is not. Census every recess call on the corpus with both
readings — the extent, and the back edge read on the component's own boundary
runs the way `_side_wall_covers` reads the cover — off the free-space tap's
exact inputs, on every emitted room as well, classed against the ground
truth; then the rule as implemented with / without; build only if it changes
a corpus verdict or closes the fixture without moving any confirmed room; pin
it with a test that fails on the unmodified tree; sweep. s01 and s02 must not
change.

## What the extent reading does on the tab (measured, `fixture_probe.py`; picture 1)

On the step-15 fixture as drawn (`TestBandPocketTabbedByAPerpendicularBand`:
the inner leaf's near piece stops at 260, the 32px partition's near face runs
across the cavity wall, its far face stops at the inner face line, the line
is drawn from the far flank on), the stage extracts the reveal as
(302,113.75)–(438,144) with a 28px tab — the polygon
`(302,144) (330,144) (330,142) (438,142) (438,113.75) (302,113.75)`. The recess
rule's one candidate is the gap between the inner leaf's two segments
(th 13.25, gap 260–440): gap cover **0.665**, depth 2.28 bands, and the back
read off the extent `min(-th/2 - min(ws), max(ws) - th/2)` = **0.00** — the
tab's vertices at y = 144 lie ON the leaf's inner flank — so
`|back + 2| = 2 > 1.5` and the rule declines. On the reveal's own runs the
back lies on the face line at the standoff over (330,142)–(438,142) and on the
partition's segment's flat cap over (302,144)–(330,144): 0.60 of the gap on
the face alone, **0.756 with the cap**, 0.79 / **1.0** of the reveal's own
extent. The tab-less version (the inner face line drawn from the partition's
near face on) has no tab and its extent reads −2.00 — but on this fixture it
never reaches the back edge: without the tab's 56 px² the gap cover is
0.6415, under 0.65. Which rule drops the reveal is invisible from outside:
`_is_band_pocket` catches it right after `_is_wall_recess` declines (2 rooms
on both trees), so the pin test takes the pocket rule out of the stage.

## Census 1 — both readings on both populations (`recess_census.py`, all 20 sheets at their factors; `summary17.md`)

Every `_is_wall_recess` call (= every entrance-less, window-less component
past the filters, with the rule's own verdict) and every emitted room, read
off detect_rooms' own `wall_segments` / `cap_lines` / `doors` / `windows` /
`text_spans`: for every collinear-gap candidate that passes the intersect /
opening / gap-cover / depth gates — the candidates the back edge decides —
the extent's `back` and the runs' cover in four variants (the runs at the
standoff inside the band's outer line, `face`; also ON it where a cap line
lies on them, `caps`; over the gap's length or over the component's own
extent inside the gap).

**72 calls corpus-wide, 14 reach the back edge, 236 emitted rooms, none does.**
The 14 (the rule's own population — every one dropped today):

| sheet (f) | component | area px² | ground truth | band | gap cover | depth (bands) | extent back | face / caps over the gap | face / caps over own |
|---|---|---|---|---|---|---|---|---|---|
| s01 (0.542) | (810,980)–(846,1076) | 3393 | unmatched | 19.25px = 301mm | 0.860 | 1.83 | −2.00 | 0.960 / 0.960 | 1.00 / 1.00 |
| s05 (0.5) | (1587,468)–(1622,551) | 2908 | unmatched | 12.00 = 203mm | 0.795 | 2.94 | −2.00 | 0.954 / 0.954 | 1.00 / 1.00 |
| s05 (0.5) | (1569,1264)–(1593,1293) ×3 (1311, 1436) | 693 | unmatched | 27.50 = 466mm | 0.855 | 0.85 | −2.00 | 1.000 / 1.000 | 1.00 / 1.00 |
| s10 (1) | (497,2935)–(611,3026) | 6131 | recorded FP | 32.23 = 273mm | 0.930 | 1.94 | −2.12 | 1.000 / 1.000 | 1.00 / 1.00 |
| s11 (0.5) | (781,1509)–(823,1533) | 1016 | recorded FP | 17.63 = 299mm | 0.760 | 2.39 | −2.00 | 0.858 / 0.858 | 1.00 / 1.00 |
| s11 (0.5) | (886,874)–(976,917) | 3814 | unmatched | 17.63 = 299mm | 0.849 | 2.41 | −2.00 | 0.957 / 0.957 | 1.00 / 1.00 |
| s11 (0.5) | (1930,868)–(2001,899) | 2192 | recorded FP | 17.63 = 299mm | 0.839 | 1.75 | −2.00 | 0.947 / 0.947 | 1.00 / 1.00 |
| s14 (1) | (2608,2022)–(2664,2110) | 4746 | recorded FP | 35.50 = 301mm | 0.940 | 2.48 | −2.00 | 1.000 / 1.000 | 1.00 / 1.00 |
| s16 (0.5) | (1060,955)–(1149,998) | 3798 | unmatched | 17.62 = 298mm | 0.849 | 2.41 | −2.00 | 0.957 / 0.957 | 1.00 / 1.00 |
| s16 (0.5) | (2144,941)–(2215,972) | 2192 | recorded FP | 17.63 = 299mm | 0.839 | 1.75 | −2.00 | 0.947 / 0.947 | 1.00 / 1.00 |
| s17 (1) | (1548,2766)–(1569,2910) | 3034 | unmatched | 13.25 = 112mm | 0.759 | 1.58 | −2.00 | 0.893 / 0.893 | 1.00 / 1.00 |
| s18 (0.5) | (2096,2506)–(2157,2558) | 3183 | recorded FP | 17.75 = 301mm | 0.656 | 2.92 | −2.00 | 0.739 / 0.739 | 1.00 / 1.00 |

("recorded FP" = a recorded false positive the rule already removes, inert
in the sweep; "unmatched" = no verdict, the component is not emitted.) Every
one reads the extreme at the standoff and its back on the line over 1.00 of
its own extent, caps or no caps: the two readings agree on all 72 calls, and
no cap line lies on any corpus back run — **the tab is the runs reading's
only instance**. The other 58 calls have no candidate at all, held out by the
intersect / opening / gap-cover / depth gates (s17's four hollow-wall strips
among them — no collinear segment pair's gap reaches them, picture 6). The
true class never reaches the back edge: of the 236 emitted rooms (187
confirmed), none passes those gates for any segment pair, so no reading of
the back edge can move a room.

Over the gap the same 14 read 0.74–1.00 (s18's pier at 0.656 gap cover reads
0.739): the gap's length as the denominator compounds the gap-cover gate,
which already asks how much of the gap the component fills, so the reading
built is over the component's OWN extent along the gap.

## Census 2 — the rule AS IMPLEMENTED under each runs reading (`recess_census.py`, 20 sheets, rooms diffed and scored)

The chain once as it stands, then once per variant with `_is_wall_recess`
replaced by the runs reading at 0.65: **identical on every sheet under every
variant** — no room gone, new or moved, scores unchanged (0 LOST / 60 returned
FPs / 0 REVIEW in the harness's terms; s02's twelve "lost" are the harness's
omitted labels and schedule, as in every step's census).

## The reading as built

`_back_edge_cover(comp, inter, origin, axis, normal, th, lo, hi, cap_lines)`:
for each outer line of the band — the flank at ±th/2 in the segment's frame
— the union, clipped to the gap, of the component's boundary runs parallel to
the band lying `ROOM_LINE_BARRIER_PX` inside that line (within
`ROOM_RECESS_BACK_TOL_PX`, a drawn face's barrier standoff) and of the runs
lying ON it where a wall solid's flat end lies on them (`cap_lines`, standoff
0 within the same tolerance, exactly as `_run_wall_cover` admits a cap for the
band-pocket covers — the tab IS wall-bounded, by the partition's solid), over
the component's extent along the gap (read off its intersection with the gap
rect), the larger of the two lines'. `_is_wall_recess` takes `cap_lines=` and
returns True when the cover is ≥ `ROOM_RECESS_BACK_COVER_MIN` (0.65, the
family's "mostly" threshold: a text mask across the outer line interrupts the
back run as it interrupts a cover). `detect_rooms` passes the `cap_lines` it
already builds for `_is_band_pocket`; the interval union the two step-15/16
helpers inlined is now `_union_length`, shared. No constant moved.

Why the caps: the tab is the partition's thickness less two standoffs (s17:
31.5px) whatever the pocket's length, so on the face alone a 92px reveal
beside a 40px partition reads 0.61 and a 300px one 0.88 — a length dependence
with no drawing meaning (the step-15 argument). The pin fixture is built
where the cap decides (picture 1): s17's own 35.5px partition beside an 80px
reveal in a 19.25px inner leaf (a 100 / 160 / 163mm cavity wall at 1:50; a
40px partition is over the plain cap, never pairs, and its hollow interior
joins the reveal), the tab 31.5 of the reveal's 80px back — **0.61 on the
face alone, 1.0 with the cap**, gap cover 0.80 with the tab and 0.76 without,
depth 1.88 bands, 2,803 px², extent back +0.00.

Pinned by `TestWallRecessTabbedByAPerpendicularBand` (a subclass of the
step-15 fixture with `_is_band_pocket` taken out of the stage by
`mock.patch.object`, because on the shipped tree it catches the reveal after
the recess rule declines it): the tabbed reveal is a recess (2 rooms), and
the control — the inner face line drawn continuously across the junction —
is a recess on both trees. Bite proven: with `rooms_step17.diff` reverted the
tabbed test fails (the reveal survives as room_0000, (302,113.8)–(382,150))
and the control passes; restored, 3/3. Fast tier: **1452 tests, OK**
(`unittest_full.txt`).

Reading-vs-implemented check on the shipped tree (`recess_census_after_*`,
`RECESS_CENSUS_SHIPPED=caps_own`): the census's own runs reading and the
rule's verdict agree on every call of every sheet.

## The sweep (four background groups, verdicts sorted section-wise)

**0 LOST, 60 returned FPs, 0 REVIEW** — the 80 verdict lines byte-identical
to the baseline's (`sweep_after_verdicts.txt`). `tools/diff_room_polygons.py`:
**all 20 sheets entity- and polygon-IDENTICAL** (s01 at 0.542 and s02 at 1.0
among them), 0 changed polygons, nothing added or removed, so no unsimplified
diff was needed; `compare_sweeps.py s11` / `s17` / `s18`: no entity added or
removed. No before|after pair: the sweep is identical.

## Pictures (this directory, plan crops only, none shows an address)

1. `step17_fixture_tabbed_reveal_extent_vs_runs.png` — the pin fixture and
   its tab-less control: the reveal (red), the candidate gap rect (yellow),
   the back runs coloured by what they lie on (thick green: the face at the
   standoff; thick orange: the partition's flat cap), both readings in the
   caption.
2. `step17_s11_breast_pocket_886_874_recess_both_readings.png` — the rule's
   own class: a chimney-breast pocket in s11's 17.6px external wall, 2.41
   bands deep, back −2.00 / runs 1.00.
3. `step17_s11_breast_pocket_781_1509_recess_both_readings.png` — the same,
   the smallest (1,016 px² at f=0.5).
4. `step17_s18_pier_2096_2506_gap_cover_0.66_recess_both_readings.png` —
   the call nearest the gap-cover gate (0.656), its back still 1.00 on the
   line.
5. `step17_s17_pocket_1548_2766_112mm_band_recess_both_readings.png` — a
   pocket in a 13.25px (112mm) band, the thinnest band the rule fires on.
6. `step17_s10_recess_497_2935_back_minus_2.12.png` — the one extent reading
   off the exact standoff (−2.12: a 32.23px band paired 0.12px wide).
7. `step17_s17_hollow_wall_strip_0013_no_collinear_gap.png` — s17's strip
   0013: the recess rule never reaches its back edge (no collinear segment
   pair's gap intersects it); it is `_is_band_pocket`'s class, dropped by the
   step-16 ceiling.

In 2–7: red = the component; yellow = the candidate's gap rect; thick green /
orange = its back runs at the standoff / on a solid's flat end; blue = wall
SEGMENT solids; thin green = a paired face, thin orange = a lone face;
magenta = a door seal, cyan = a window seal.

## Residue / not in scope (one line each)

- The reading's only instance is the synthetic tab: no corpus back run lies
  on a cap line today, so the change is a consistency fix between the two
  pocket rules (step 15 read the pocket covers this way), not a corpus win.
- The tab-less version of the step-15 fixture (LEAF_END 260) never reaches
  the back edge — its gap cover is 0.6415 — so "a tab-less version is a
  recess" holds for the retuned fixture (0.76), not that one.
- The recess class itself (s11's party-wall box is the neighbour's chimney
  breast, s16's enclosed partition box at 406mm, s10/s14/s18's recorded-FP
  drops that read "unmatched" because the rule already removes them) is
  untouched — its own iteration.
- `_is_wall_recess` and `_is_band_pocket` now overlap: since the step-16
  ceiling every recess pocket up to 3 bands deep in a band ≥ 8px at 1:100,
  or ≤ 17.3px at 1:50, is also a band pocket; the recess rule runs first and
  its own population (31–42px deep in 17.6px bands at f=0.5) lies over the
  scaled 28px pocket ceiling.
- The step-16 census scripts' `_is_band_pocket` taps take the old
  signature (`solids=` arrived in step 16 after they were written); this
  step's `recess_census.py` tap passes `**kw` through and documents both
  trees (`RECESS_CENSUS_SHIPPED`).

## Numbers

lost **0** · returned FPs **60** (unchanged) · new REVIEW lines **0** · net
phantom delta **0** (by construction: the runs reading agrees with the
extent on all 72 calls and 236 rooms of the corpus) · s01 at 0.542 and s02 at
1.0 entity- and polygon-identical · all 20 sheets identical · the tab
fixture closed (0.61 → 1.0 with the cap) · **next**: the fixture-cell rule
for the three cells the pocket ceiling drops for the wrong reason (s12's
unit cells at 0.93 / 0.99×, s18's sofa strip at 0.97× the scaled 28px
ceiling: free space between a wall and a unit front, not wall material),
then the queue (the s04 staircase, `_dimension_line_indices` on s15's
TEXT-layer lines, the s18 blind-window cap at 1:100, …).

**Decision needed**: ship the reading as built (commit code + test + prose +
the seven PNGs + `tools/census_scratch/step17/`), or hold it — its corpus
effect today is nil, and its value is that both pocket rules now read the
component's boundary the same way, so a junction tab can no longer flip
either.
