# W-gate iteration 3 — step 3: the "short-piece material rule" measured; nothing to build, and what actually holds s01 at its true scale

Branch `fix/short-piece-material-inherit` from `fix/hingeless-swing-side-veto`
(d0a4376, which carries steps 1 and 2; main is still `ee0f52f`). Baseline:
that tree's own sweep, re-run in four background groups and snapshotted for
all 20 slugs (71 returned FPs, 0 LOST, 5 unreviewed). 2026-09-04.

**No code was changed in this step.** The tree is byte-identical to d0a4376
apart from prose (this report, the handoff, the `WALL_MAX_THICKNESS_PX`
comment, findings §4/§4f, the CLAUDE.md gate paragraph) and four PNGs.

## s01 rooms — four confirmed rooms lost at f = 0.542

**The brief's premise (third time in this iteration): wrong.** It said the
21–25 px hatched walls pass the thick tier at 0.542 but their ~36 px pieces
between openings carry 3 marks and fail the ≥ 4-marks/span gates, leaking
4 of 12 rooms — and asked for a rule that lets such a piece inherit the
material verdict of the collinear band it continues across an opening.
Tapping `_band_has_wall_material` and the final pairing call in the census
harness (scratch `measure_short_pieces.py`, `leak_finder.py`,
`probe_pairs_box.py`, `force_pair.py`, `plug_diff.py` — not in the repo):

| s01 @ 0.542, thick tier | count |
|---|---|
| material-gate calls | 43 thick (12 pass, 31 fail), 1218 weak |
| fails with **0 marks** | 27 — kitchen units (282–317, 864–891), the bath/stair box (808–948, 840–880), the flights |
| fails with marks, span < 0.5 | 3 — the 17 px corner blocks at (1055–1072, 811–814), 4–5 marks each, `n=5 dens 29/100 span 0.24` |
| fails with **3 marks** (the brief's piece) | **1** — (160.5–196, 906.8), th 22, 35.5 px: its faces are paths 3141/3152/3233 in the BLUE dimension pen, i.e. the "6xx" dimension line's extension along the wall; its collinear reference (196.2–389.5, th 22, passes at 34 marks) sits 0.2 px away — a face split at the 8.5 px partition's T-junction, **no opening between them**; inert (the y=906.8 segment still reaches the partition at x=191.8 and nothing lies left of it) |
| **class A** — a failing piece collinear with a same-thickness material-passing band AND a door/window bbox in the gap | **0** |

The convention the brief asked me to state ("a band interrupted by openings
is ONE band, so a piece on a hatched band's own faces with an opening in the
gap inherits its verdict") has **no instance on s01 at 0.542, and none on
s01/s02/s03/s05 at their own factors** in the thick tier (s02 has one: a
51.5 px pair (1869.7–1926.8, 688.9) with 0 marks — inheriting there would
be wrong). In the weak tier the same test admits 5/13/8/0 pieces on
s01/s02/s03/s05, every one with 0–4 marks and span ≤ 0.12 (s02's
(1238.8–1345.3, 836.4) th 14.5: 4 marks clumped in 6 % of a 106 px run —
a symbol, not hatch). s02's stud partitions between doors pass on their own
marks (22 weak passes). So the rule would fix nothing and would admit
unhatched pieces; **it was not built** and there is no synthetic test.

The two genuinely short hatched blocks on s01 — the hall's corner jamb block
(389.8–410 × 905.2–920.8, th 20.5, 15.5 px, **4 marks at 25.8/100 px** — six
times the gate — failing `WALL_WEAK_MIN_RUN_PX` 16.3 and span 0.39; picture
`step3_s01_hall_corner_jamb_block_identity_vs_0542.png`) and the bathroom's
(1055–1072, 811–814) — are the END BLOCKS of a horizontal band turning a
corner (the hatch runs through the corner), perpendicular to it, with no
collinear band on either side. Forcing the hall block through the gate at
0.542 (min-run lifted) changes no room: 8/12, the same four lost.

### What the four rooms are actually lost through (measured)

| lost room (truth note) | barrier at identity | why it is gone at 0.542 |
|---|---|---|
| (1090,699)–(1142,876), the strip beside the bathroom | the flight at y 877–923 is sealed by two STRONG pairs: (1098.1, 877–918) th **35.2** = the bathroom partition's outer face (path 2082, x 1080.5) × the **stair arrow line** (path 3098, x 1115.7, a lone 45.8 px stroke), material TRUE on 8 marks that are the 7.2 px PARTITION's own hatch inside the 35 px band; and (1129.9, 877–923) th **28.2** = the arrow × the exterior wall's inner face (x 1144), **0 marks** | at cap 19.5 the arrow has no wall-spacing partner (`_demote_stair_faces::_paired_with` bounds partners by the scaled cap), so the zone fixpoint absorbs it as stair ink (`stroked False`) — the documented stairs-are-furniture convention — and the flight opens |
| (466,920)–(521,1056), `partial`: "detects stairs as part of the room" | the flight at y 1051–1115 sealed by (509.0, 1051–1115) th 28.0 and (479.7, 1051–1115) th 30.8 — the flight's edge lines and its centre line pairing across the treads | same mechanism |
| (1033,925)–(1142,1134), `partial`: **"This needs to merge with the hallway above and not all stairs are ignored"** | the flight above it (row 1) plus the flights at y 974–1030 (th 26–33, 0 marks) | opens, merges with row 1's room into (1032,697)–(1142,1136) — which is what the note asks for; IoU < 0.5 against both old bboxes, so both count LOST |
| (392,922)–(521,1387), the hall | the door (424,917)–(468,958)'s top-edge interrupted plug, whose tail reaches an 8 px jamb gap (125 mm at 1:92.2) | `ROOM_OPENING_SEAL_PX` alone at 6.5 (= 101 mm) loses exactly this room (`plug_diff.py`: the plug goes `interrupted → None`; the door at (458,1336)–(512,1392) loses its top plug too), and the hall merges with the living room. The flight at 1051–1115 also merges it with room 1, but that alone keeps IoU ≥ 0.5 |

Cap-only at identity (`WALL_MAX_THICKNESS_PX` × 0.542, everything else
unscaled) loses 4 rooms — the ablation's `only:WALL_MAX_THICKNESS_PX lost 4`
line — the three stair rooms plus the living room (the hall/living blob
matches the hall's bbox in that configuration). Forcing the 31 raw pairs at
the three flights back through the gate at 0.542 (including the weak tread
pairs) returns rooms 0 and 1 (10/12); forcing only the thick pairs returns
nothing, because at 0.542 the arrow-line pairs no longer exist.

Pictures (`crop_net.py`: render + network at both factors, segments as
half-transparent bands, room outlines green):
`step3_s01_flight_877_arrow_pairs_identity_vs_0542.png` (the blue solid over
the flight with the arrow's two centerlines; open at 0.542),
`step3_s01_flight_1051_identity_vs_0542.png`,
`step3_s01_landing_rooms_0_3_identity_vs_0542.png` (rooms 0 and 3 split by
the flight at identity, one room at 0.542),
`step3_s01_hall_corner_jamb_block_identity_vs_0542.png`.

### What this means for `_gate_denominator`

`ablate.py s01 s01mode` is unchanged from `final_s01mode.txt` on this tree:
f=0.542 keeps 11/11 doors and 4/4 windows and loses 4/12 rooms with 18
phantoms (`measure_short_pieces.py s01 0.542`: rooms 8/12, unrev 18). The
two solo culprits are the same two constants, now attributed:

- **`WALL_MAX_THICKNESS_PX`** (36 → 19.5): it does not hold any hatched wall
  piece — it holds s01's **stair arrow lines out of the stair zone**, and
  the arrows then pair with real wall faces 28–35 px away into phantom
  bands that seal three flights. Three of s01's twelve confirmed rooms are
  the rooms those phantom bands cut, and the user's own notes on two of
  them say the cut is wrong. At s01's true scale the arrows are stair ink
  and the flights open. That is a ground-truth decision (re-review rooms
  (1090,699)–(1142,876) + (1033,925)–(1142,1134) as one landing, and decide
  whether the CPD cupboard (466,920)–(521,1056) is bounded by the flight),
  not a detection rule — a rule that re-fenced the flights at 0.542 would
  contradict the stairs-are-furniture convention on every other sheet.
- **`ROOM_OPENING_SEAL_PX`** (12 → 6.5): s01's hall door stops 8 px = 125 mm
  short of its jamb (findings §4 already records the 12 as "set on s01 as
  if 1:50"); 102 mm at 1:50 is under it. Reaching it means seal ≥ 15 at
  1:50, which is the step-7 retry, blocked behind steps 5 and 6.

So `_gate_denominator` is NOT narrowed and `SCALE_FACTOR_MEASURED_ONLY`
stays. The path to s01 at its true factor is: steps 5 → 6 → 7 (the seal),
plus the s01 stair-room re-review; only then step 4 (the cap at 40, which
needs s01's 38.5 px kitchen units to become 20.9 px).

## Sweep

No detection code changed; the baseline sweep of this tree IS the result:
0 LOST · 71 returned FPs · 5 REVIEW (byte-identical to step 2's), snapshots
under `outputs/regress_baseline/<slug>/` for all 20 slugs. Fast tier: 1381
tests, only the two InquirerPy import errors. No polygon moved, nothing to
reseed.

## Residue / not in scope (one line each)

- s01's stair arrows are open-headed and have no UP/DN text, so the
  STAIR-ARROW recognizer never sees them; the zone rule catches them only
  when no wall face lies within the cap. A recognizer for open arrowheads
  is its own iteration and would LOSE those three confirmed rooms at
  identity — the ground-truth decision comes first.
- The hall's corner jamb block (15.5 px, 4 marks at 6× the density gate)
  fails the absolute floors at 0.542; inert today (forcing it changes no
  room). A relative floor for hatched end blocks is not worth a rule
  without a measured payoff.
- The seal's world class: s01 needs 125 mm, s17 135 mm at 1:100, the 1:50
  reference is 102 mm — step 7.

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 (no code change) · **next: step 5** (plug tails end AT the material
they shadow), then 6 (dash rows), then 7 (the seal retry); in parallel the
user's decision on s01's three stair-split rooms; `_gate_denominator` and
step 4 wait behind both.

**Decision needed**: accept this as a measurement-only checkpoint (commit
the report, the four PNGs — none shows an address — and the prose notes),
and say whether s01's stair rooms are to be re-reviewed before the true
factor is attempted.
