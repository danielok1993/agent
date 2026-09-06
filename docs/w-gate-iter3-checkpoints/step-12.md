# W-gate iteration 3 — step 12: the drawing's DIMENSION STRINGS verify a measured scale for the gates — s01 detects at its true 1:92.2 in the sweep; 19 sheets identical

Branch `recal/gate-denominator-stored-scale` from `fix/wall-pen-discriminator`
(cb5fec8, which carries steps 2, 3, 5–11; main is still `ee0f52f`).
Baseline: that tree's own sweep, re-run in four background groups (s18; s16
s11 s15; s01–s07; the rest) and snapshotted for all 20 slugs
(`outputs/regress_baseline/<slug>/2026-09-06_13-09-*` … `13-10-*`) — **0
LOST, 68 returned FPs, 0 REVIEW**, the 68 verdict lines byte-identical to
step 9's `sweep_base_all.txt`. 2026-09-06. Not committed.

## The decision, and how it was made

The brief: let s01's measured 1:92.2 drive its gates, deciding with the
user what `_gate_denominator` accepts — a user-stored measured denominator,
a dimension-verified one, or both — and what stays excluded.

Evidence put to the user (this tree): harness s01 at 50/92.2 = doors
11/11, windows 4/4, rooms 9/12 (lost exactly the three stair verdicts, one
unreviewed = the merged landing); s01 is the ONLY corpus sheet whose
resolved scale is non-nominal and not viewport-declared (stored 1:92.2,
source `user`; s10/s11/s16/s18/s20 store nominal 1:50/1:100, s13 is a raw
viewport 1:136.4 that already drives); and s01 is the ONLY sheet with any
ticked dimension matches at all (31, agreeing at 1:92.2 — every other
sheet has 0 and its plausibility verdict comes from door leaves), so a
dimension-verified rule has one true instance and no false class on the
corpus. Nothing downstream consumes the `"measured"` detection source.

Asked in plain terms (the user asked for it without jargon: whose word
should the code trust when a scale is an unusual number?), the user
answered: **"I think we should autodetect, if there are numbers to verify
the claim we should use them. Just because we can't verify it today on
other drawings does not mean in the future other users won't upload them.
The current set of PDFs is only training data for this algorithm. Also
some builders who upload the PDF might not know what the scale is. Either
way verify claim if possible."** So the rule is the drawing's own numbers,
built although only s01 exercises it today.

## The rule

**Convention**: a drawing's ticked dimension strings ("3600" beside a line
ticked at both ends) are drawn by the same hand at the same world scale as
its walls, so they measure exactly the ink density the gates were
calibrated on; a caption, a viewport or a stored value is a statement ABOUT
the drawing. Three or more such strings inside a plan VERIFY its claimed
scale (agreement within `DIM_AGREE_TOL` 5 %) or CONTRADICT it (past
`DIM_DISAGREE_TOL` 15 %) — the same three bands the takeoff's `verified`
has read since the plausibility layer shipped; between them they are
inconclusive.

**Fix** (`scale/dimensions.py`, `scale/factor.py::_gate_choice`,
`pipeline.run_extract`, `tools/_corpus_page.py`):

- The matcher (`DimensionMatch`, `dimension_matches`, `parse_dimension_mm`,
  the `DIM_*` tolerances) moved verbatim from `takeoff/plausibility.py`
  into `scale/dimensions.py`, re-exported by the takeoff so nothing else
  changes; `MM_PER_PX_AT_1_1` now lives in `scale/units.py` (takeoff
  re-exports it; the value `25.4 / 150.0` is computed, so it is
  bit-identical) because scale/ must not import takeoff/ (takeoff imports
  detection). New: `measured_denominator(matches, region_bbox=None)` — the
  median implied denominator over ≥ `DIM_MIN_MATCHES` (3) strings, those
  whose line midpoint lies inside the region when one is given (a
  mixed-scale sheet's plans each carry their own strings; a match with no
  line counts page-wide only); `agreement(implied, claimed)`;
  `page_dimensions(page_data)`.
- `run_extract` matches the FULL page once (the takeoff's convention) and
  hands the list to `detection_scale(…, dimensions=)` and
  `compute_takeoff(…, dimension_matches=)`, which no longer re-matches.
  `tools/_corpus_page.py` (the harness and every probe) and the three
  probes that call `detection_scale` directly do the same, so the harness
  reproduces the sweep (findings §4c).
- `_gate_choice(info, measured)`: agreement → the claim drives the gates
  whatever its number (`verified`; the nominal when there is one so 1:50
  computes exactly); contradiction → the measured scale drives them
  (`dimensions`; snapped to a standard scale when within 2 %), with the
  new warning `SCALE_FACTOR_FROM_DIMENSIONS` naming the measured and the
  resolved scales and stating that the takeoff keeps the resolved one and
  flags it `SCALE_IMPLAUSIBLE`; otherwise `_gate_denominator` as before
  (`claim` / `abstain` — `SCALE_FACTOR_MEASURED_ONLY` survives for the
  unverified non-standard claim, its message now saying why). Per-region
  judgement by the strings inside each floor-plan bbox; the page-level
  fallback by all of them. `DetectionScale.measured` and the summary's
  `detection.measured_denominator` record the page's measured scale (None
  under 3 strings).
- What stays excluded: a non-standard claim the drawing cannot verify
  (fewer than 3 matched strings, or inconclusive at 5–15 %) — identity, as
  before.

**Tests** (fast tier 1,422 → 1,438, +16; every one written first and failing for
the stated reason): `tests/test_scale_factor.py::TestDimensionsVerifyTheClaim`
— verified non-standard drives (s01), fewer than three verify nothing,
contradiction overrides with the warning and source, inconclusive leaves
the claim alone (both a nominal and an unsnapped one), strings are read
PER PLAN (strings in the other plan or between plans verify nothing),
page-scale verified / contradicted, no-argument = old behaviour;
`tests/test_scale_dimensions.py` — min matches, median not mean, region
filter by midpoint, line-less matches page-wide only, the three bands;
`test_scale_pipeline.py` — wiring assertions for `run_extract` and
`_corpus_page`; `test_takeoff_plausibility.py` — precomputed matches used
verbatim. **Bite-proof**: with the two dimension branches of `_gate_choice`
disabled (`if False:`), exactly the five rule tests fail
(verified-drives, contradiction, per-plan, page verified, page
contradicted); restored, green. Two pre-existing wiring tests'
`compute_takeoff` stubs gained the new keyword.

## Measured margin

| feature | false class | true class (s01) | other sheets |
|---|---|---|---|
| matched ticked dimension strings per plan | **no corpus instance** — no sheet has ≥ 3 strings whose median lies > 5 % off its true scale (or off a claim) | 24 (ground floor) + 7 (first floor), medians 92.21 / 92.23 against the stored 92.2 (0.01–0.03 % off; 31 within ±0.5 %) | **0 on all 19** (s02–s20; their verdicts are door-leaf) |
| the claim the strings judge | — | user-stored 1:92.2, nominal None, non-viewport | nominal viewport/text/user on 17, raw viewport 1:136.4 on s13, unresolved on s09/s19 |

The false side of the rule is unmeasurable on this corpus — the user
accepted that explicitly ("the current set of PDFs is only training
data"). The takeoff has run the same matcher with the same tolerances
since the plausibility layer shipped, with s01's 31 strings its only
firing; the gates now read what `verified` already read.

## Rule census as implemented (`tools/census_scratch/step12/rule_census.py`, every sheet, the pipeline's exact inputs: `detection_scale` with and without the dimensions)

| sheet | claim | strings inside each plan → measured | gate choice | factor before → after |
|---|---|---|---|---|
| **s01** | user 92.2 (both plans) | 24 → 92.21; 7 → 92.23 | verified, verified | **1.0 → 0.5423** (`floor_plan_regions`, no warning; was `measured` + `SCALE_FACTOR_MEASURED_ONLY`) |
| s02, s14 | text 50 | 0 | claim | 1.0 (unchanged) |
| s03, s17 | viewport 100/100/50 (mixed) | 0 | claim | 1.0 (unchanged, `SCALE_MIXED_FLOOR_PLANS`) |
| s04, s08, s15 | viewport 50 | 0 | claim | 1.0 |
| s05, s06, s07, s12 | viewport 100 | 0 | claim | 0.5 |
| s10, s20 | user 50 | 0 | claim | 1.0 |
| s11, s16, s18 | user 100 | 0 | claim | 0.5 |
| s13 | viewport 136.4 | 0 | claim | 0.3666 |
| s09, s19 | unresolved | 0 | — | 1.0 |

## Net effect on s01 (from the pictures, my verdicts)

| id (baseline) | what it is | before | after | my read |
|---|---|---|---|---|
| room_0002 (1090,698)–(1142,878) | the strip beside the bathroom, above the top flight | confirmed | gone — merged | **expected retirement** (stair verdict 1: "(1116,787)") |
| room_0005 (466,920)–(521,1051) | the CPD cupboard | confirmed ("detects stairs as part of the room") | gone — merged into the hall through the flight below it | **expected retirement** (stair verdict 2: "(494,988)") |
| room_0008 (1033,923)–(1142,1135) | the landing | confirmed ("needs to merge with the hallway above and not all stairs are ignored") | gone — merged | **expected retirement** (stair verdict 3: "(1088,1030)") |
| new room_0002 (1032,697)–(1142,1136), 0.85 | the strip + landing + both flights as one room | — | **REVIEW** | **real** — the stairs-are-furniture merge the retired notes ask for; to be recorded through `tools/review.py s01` |
| room_0004, the hall (392,920)–(521,1387) | hall | matched | matched, +10,924 px² (the CPD and the flight), IoU 0.7535 vs its verdict | real, as the retirement implies; the confirmed line still matches |
| rooms 0000/0001/0003/0007/0009/0010 | living, bedrooms, bathroom … | matched | matched, +24 … +791 px² each (IoU 0.990–0.997) | outlines move onto their walls at the scaled standoffs; unsimplified loss over ALL matched rooms 143 px² (largest piece 49 px², a 5.6×8.7 px corner of (970,698)–(1081,916) at (970,908)–(975,916); a 3×12 px sliver in the hall at (445,1175)) against 12,624 px² gained |
| door_0012 (folding) | bbox [388,948,412,1011] → [388,956,412,1011] | matched | matched, IoU 0.889 | `DOOR_FOLD_JAMB_ANCHOR_TOL_PX` 10 → 5.4 px at 0.542: the bbox top no longer extends 8 px along the jamb (iteration 2 group 1's identity-scale extension); metrics unchanged |

Net phantoms: **0 → 0** (nothing phantom appears; three chunk verdicts
become one real room). The three LOST lines are the expected retirements:

```
✗ LOST room @ (1116,787)                                  (1090,699)–(1142,876)
✗ LOST room @ (494,988)   detects stairs as part of the room   (466,920)–(521,1056)
✗ LOST room @ (1088,1030) This needs to merge with the hallway above and not all stairs are ignored   (1033,925)–(1142,1134)
REVIEW new room_0002  conf 0.85  (1087,917)               (1032,697)–(1142,1136)
```

**Pictures** (this directory, none shows an address):
`step12_s01_true_factor_rooms_added_removed.png` (compare_sweeps: the
merged landing added, the three chunks removed),
`step12_s01_hall_cpd_flight_merge_identity_vs_0542.png` (room_shape_crop:
the hall stopping at the CPD's wall, then taking the cupboard and the
flight), `step12_s01_merged_landing_identity_vs_0542.png` (the strip,
landing and flights as one room). `outputs/compare/s01/` holds the whole
page and the other crops.

## Sweep (`tools/regress.py`, four background groups, vs the re-run baseline; `diff_room_polygons.py` on all 20 slugs)

| | lost | returned FP | REVIEW | doors/windows | polygons |
|---|---|---|---|---|---|
| baseline | 0 | 68 | 0 | — | — |
| **dimension-verified gate scale** | **3 (s01, the retirements)** | **68** (identical lines) | **1** (s01, the merged landing) | s01 11/11, 4/4 (door_0012 8 px shorter); 19 sheets identical | **19 sheets IDENTICAL**; s01 7 changed (+279, +791, +48, +10,924, +35, +167, +24 px²), 1 added, 3 removed |

s02 at f = 1.0 entity- and polygon-identical, as the rule requires; s01 is
the one sheet that moves, by decision. Harness self-check on s01 with its
stale cache removed reads the same as the sweep (f = 0.542, 11/11, 4/4,
9/12, lost 3, unreviewed 1).

**Retired on the user's go (same day)**: the three `confirmed` entries were
removed from `tests/ground_truth/s01.json` through the repo's own
loader/dumper (round-trip byte-identical first; a 20-line deletion, 24
confirmed remain), and the re-sweep reads **s01 door 11/11, room 9/9,
window 4/4, unreviewed 1, exit 0**. The user then recorded the merged landing
through `tools/review.py s01` (confirmed, `reviewed` 2026-09-06, bbox
(1031.5,697)–(1142,1136.5)) with the note **"more stair at the bottom right
need to be covered. The top left also has a slight notch and does not go
all the way to the wall."** — two outline residues for the stair queue, not
this step. The sweep now reads **s01 door 11/11, room 10/10, window 4/4,
exit 0, nothing unreviewed.**

**Label reseed done** (after the user's `gcloud auth application-default
login`): `app.py extract fixtures/sheets/s01-floor-plans.pdf --out
outputs/reseed_s01 --ceiling-height 2.4` wrote the cache entry for the
new geometry (`s01-floor-plans_p01_…-269f1066870e1eb8-v1.json`); the
offline sweep then names the same four rooms the identity run named
(Dining / Sitting / Kitchen, Bathroom, Wetroom, Utility / Store), the
other six unnamed as before, no `ROOM_LABEL_*` warning.

**Blocked**: s01's room-label cache must be reseeded at the new geometry
(`python app.py extract fixtures/sheets/s01-*.pdf --out <dir>
--ceiling-height 2.4 < /dev/null`); the sweep's s01 run left all ten rooms
unnamed. `gcloud auth application-default print-access-token` reports
"Reauthentication failed. cannot prompt during non-interactive execution"
— the re-login has to happen in the user's prompt first.

## Residue / not in scope (one line each)

- `tests/test_takeoff_fn_equivalence.py`: under the expired credentials it
  failed on this tree AND on the reverted baseline alike (the function
  arm's page came back `TAKEOFF_REGIONS_UNCLASSIFIED`). With credentials
  restored the baseline passes and this tree fails on ONE field — the
  label text of room_0001, "Dining / Sitting & Kitchen" from the function
  arm's live Gemini call against "Dining / Sitting / Kitchen" from the
  CLI arm's — every other field equal. Both arms label live (their PDF
  copies carry no cache), so this is the labeller's nondeterminism on the
  new geometry, the known label-cache flake: two further runs on this
  tree passed (2 of 2, 37–39 s each, live Gemini). Not this change.
- The contradiction branch (`SCALE_FACTOR_FROM_DIMENSIONS`) has no corpus
  instance in either direction; it is pinned by unit tests only.
- A non-standard user-stored scale on a sheet with fewer than 3 dimension
  strings still runs at identity (the user's "verify if possible" read
  strictly); a trust-the-typed-value fallback is one line if ever wanted.
- Dimension strings are assigned to plans by their line midpoint inside the
  region bbox; a chain drawn just outside a plan's segmented box would fall
  to the page-level vote — no corpus instance (s01's 31 all land inside).
- The harness cache pickle for s01 was rebuilt (factor 0.542); other slugs'
  pickles are unaffected (their factors did not change).
- `docs/w-gate-iter2-checkpoints/*.png` (12 untracked PNGs from iteration
  2) were already untracked before this step and are left as found.

## Numbers

lost **3** against the pre-retirement truth (the three stair verdicts,
expected) and **0** against the edited truth · returned FPs **68**
(unchanged, identical lines) · new REVIEW lines **1** (s01 room_0002, the
merged landing — real) · net phantom delta **0** · 19 sheets entity- and
polygon-identical, s01 doors 11/11 / windows 4/4 / rooms 9/9 · **next**: the
user's data commit (the retirement + the landing, both in
`tests/ground_truth/s01.json`) and the code commit; then step 4
(`WALL_MAX_THICKNESS_PX` 36 → 40), with the landing's two outline notes
(bottom-right stair coverage, top-left notch) queued with the stair work.

**Decision needed**: accept and commit (code + tests + prose + the three
PNGs), or revert.
