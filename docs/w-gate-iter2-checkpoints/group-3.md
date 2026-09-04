# W-gate recalibration, iteration 2 — checkpoint: Group 3 (class fixes)

Branch `recal/w-gate-iter2`, 2026-09-04, on top of Groups 1–2. Baseline: main
`f5682fc` (71 returned FPs, 0 LOST, 5 unreviewed). Three sub-iterations, each
swept on the full corpus against the main snapshots.

## 3a — per-band hatch-mark cap, then `WALL_THICK_MATERIAL_MAX_PX` 48 → 56 (shipped)

**Rule** (`detection/walls.py::_mark_len_cap`): material marks are collected
once, up to the through-hatch diagonal (`WALL_THROUGH_HATCH_MAX_PX`·√2 + 2);
`_band_has_wall_material` filters them to the band under test — the
page-wide `WALL_HATCH_MAX_LEN_PX` (48 px) or the band's own T√2 + 2,
whichever is larger — and a mark longer than the page-wide cap counts only
as THROUGH-hatch (both ends on the band's faces). The lone-face helpers
(`_face_is_material_backed`, `_face_material_spans`) and the winder/leader
ceilings in `_demote_stair_faces` and rooms' `_barrier_extent` keep 48.

**Convention**: a hatch tool clips its strokes to the region it fills, so
45° hatch across a band of thickness T is T√2 long (census row 11: a
cap-thickness band's strokes are 51 px on s02/s20/s01/s05/s06 — 27–64 % of
in-band strokes exceeded the fixed cap and no thick-tier band over 34 px
could pass its own material gate); the one other thing that draws a long
stroke inside a band is a leader, a section cut or a stair arrow, and those
cross the band freely.

**Measured on the way** (the first sweep, without the through condition):
verdict-identical, but s17 room_0006 lost 27 % (IoU 0.726) —
`diff_wall_network` showed a new 48 px thick pair on the stair flight's two
stringers (paths 362/363/374/375), and a mark probe found exactly four
qualifying marks in that band: two 8 px arrowhead barbs, a 54 px cut line
clipped stringer to stringer, a 49 px cut line touching one stringer —
the 4-mark floor exactly, reachable only because Group 2 lowered the density
to 2.2/100 px (at 3.0 a 141 px band needs 5). The through condition drops
the one-face stroke; the flight stays furniture.
Picture: `g3a_s17_stair_fenced_without_through_condition.png`.

**Thick cap 48 → 56** (475 mm at 1:50; s15/s20's 400 mm thick pairs sat at
1.01× under 48): at f=0.5 the cap is 28 px and s05's 475 mm wall pairs at
exactly 28, falling from the through tier into the thick tier — which now
sees its 39 px strokes. Harness: s05 9/9 rooms.

**Tests** (`tests/test_wall_network.py::TestPerBandMarkCap`,
`tests/test_through_hatch_band.py` now pins the tier above 56 with a 64 px
band): 40 px band with 57 px face-to-face hatch pairs (fails on the page-wide
cap); 59 px oblique stroke is not material for a 12 px band; 50 px band with
short interior hatch pairs in the thick tier (fails at 48: it lands in the
through tier); s17's four-mark stair band does not pair, and does once both
long strokes are clipped face to face.

**Sweep (final)**: 0 lost, 71 returned FPs, 5 REVIEW — byte-identical
verdicts; polygons: s11 room_0003 +144 px² (IoU 0.9935 — two notches on the
porch's left wall gone, `g3a_s11_porch_notches_gone.png`), s13 room_0005
+146 px² (0.995 — the bedroom's top edge reaches its wall face,
`g3a_s13_bedroom_edge.png`). Net phantom delta 0.

## 3b — `COLLINEAR_OFFSET_TOL` as paper-with-ceiling (measured; no code change)

Harness on s11, s16, s13, s02, s03, s18 and s01 at f=0.542, three forms:

| sheet (f) | current 4f | unscaled 4.0 | min(4, 6f) |
|---|---|---|---|
| s11 (0.5) | 16/16 | identical | identical |
| s16 (0.5) | 17/17 | +1 phantom room (1274,1618)–(1427,1727) | identical |
| s13 (0.367) | 11/11 | identical | identical |
| s02, s03 (1.0) | — | identical (tol 4 either way) | identical |
| s18 (0.5) | 14/14 | **LOST 1 confirmed room**, +3 phantoms, −1 FP | **LOST 1 confirmed room** (3.0) |
| s01 (0.542) | rooms 8/12, 18 phantoms | rooms 7/12, 1 phantom | rooms 7/12, 1 phantom (also at 4.1) |

s18's ceiling, measured at 2.25 / 2.5 / 2.75: holds at 2.5, loses the
confirmed room (2267,758)–(2511,802) at 2.75 — its 47 mm partitions drawn at
1:100 fuse. So the world ceiling is 5.5 × f; both proposed paper forms exceed
it, and the widest safe form min(4.0, 5f) changes no corpus sheet and does
not reach the 3.25 px that cuts s01's phantoms at 0.542 (where the four lost
rooms are the thick-tier short-piece issue, not this tolerance). The value
stays 4 × f (1.37× under the ceiling; the paper true class is honoured
wherever f ≥ 0.68). Findings §4's row now reads "P true class, W ceiling,
numerically W"; pinned by
`test_scale_gates.py::…::test_scaled_tolerance_stays_under_the_partition_ceiling`.
As the brief allowed: s01 at 0.542 stays unfixable by this constant — said,
not forced.

## 3c — `ROOM_PLUG_HALF_WIDTH_PX` paper floor (shipped)

`RoomGates.at`: `max(5 × f, ROOM_LINE_BARRIER_PX)` — the floor is the 2 px
standoff (a 3.0 floor loses s13's room at (1040,999)–(1079,1085), per the
census). Harness: s13 11/11. Sweep: verdicts identical; s13's eleven rooms
move by the 0.16 px plug growth (IoU ≥ 0.987); nothing else.

## Fast tier

1376 tests; green except the three pre-existing failures (`test_review_cli`,
`test_review_picker` — InquirerPy missing from the venv;
`test_takeoff_fn_equivalence` field='warnings' — fails on main).

## Reseed

`gcloud auth application-default print-access-token` fails in this session,
so the room-label cache was NOT reseeded. Outlines that changed against main
in the final tree: s11 (room_0003), s13 (all eleven rooms, by ≤ 0.16 px).
After `gcloud auth application-default login`:

```
python app.py extract fixtures/sheets/s11-*.pdf --out <scratch> --ceiling-height 2.4 < /dev/null
python app.py extract fixtures/sheets/s13-*.pdf --out <scratch> --ceiling-height 2.4 < /dev/null
```

## Numbers

lost 0 · returned FPs 71 (unchanged) · new REVIEW lines 0 · net phantom
delta 0 · **next: the final iteration** (s01mode on the final tree — see the
section appended below once it completes).

## Final iteration — s01mode on the final tree (`tools/census_scratch/ablate.py s01 s01mode`)

| config | doors | windows | rooms | phantoms |
|---|---|---|---|---|
| f=1.0 (shipped) | 11/11 | 4/4 | 12/12 | 0 |
| f=0.542, every gate scaled | 11/11 | 4/4 | **8/12** | **18** |

Single fields that break s01 alone at 0.542 (of 50): `WALL_MAX_THICKNESS_PX`
(36 → 19.5: 4 rooms lost, +1 phantom — the census's predicted blocker: the
21–25 px hatched walls pass the thick tier but their 36 px pieces between
openings carry 3 marks and fail the ≥ 4-marks/span gates) and
`ROOM_OPENING_SEAL_PX` (12 → 6.5: 1 room lost — the seal move was reverted
in Group 2). The census's other two solo culprits are fixed:
`DOOR_FOLD_JAMB_ANCHOR_TOL_PX` (10 → 5.4 ≥ the measured 3.6) and
`CROSS_WALL_EXPAND_PX` (24 → 13 ≥ the measured 12) no longer break anything
alone. Leave-one-out: holding `COLLINEAR_OFFSET_TOL`, `WALL_FACE_MIN_LEN_PX`
or `WALL_THROUGH_HATCH_MAX_PX` at identity cuts the 18 phantoms to 1 (with
4–5 rooms still lost).

**Verdict: `_gate_denominator` is NOT narrowed and `SCALE_FACTOR_MEASURED_ONLY`
stays.** s01 at its true factor does not keep its 12 rooms. Next iteration,
as the brief foresaw: a short-piece material rule for the thick tier (a
hatched band's piece between two openings inherits the band's material
verdict), plus a swing-side veto for hinge-less doors (the seal), and the
far-side density rule that gates the 36–40 px cap (shipped in iteration 3
step 1 as `_claims_far_side_sparse`; the mark-shape idea was refuted there). None of them invented here.

Full ablation log: `final_s01mode.txt` beside this report.
