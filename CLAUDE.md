# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Local Python CLI POC for architectural PDF extraction. The research question is whether CAD-originated PDFs carry enough native vector/text data that a vector-first + Gemini-validation pipeline beats vision-only extraction of doors, windows, walls, labels, and schedules. `project.md` is the original spec — treat it as the source of truth for scope and acceptance criteria.

## Algorithm reference

**Before changing door detection, read `docs/door-detection-tuning-guide.md`.** It catalogs the six known swing topologies (full Bezier, chained Beziers, clean polyline, polyline + Y-junction stop, polyline + cycle cap, polyline + linear cap extension), every tunable constant with rationale, known false-positive patterns, the per-PDF detection state to guard against regressions, and the debug-trace diagnostic playbook for tracing missed/false detections.

## Commands

```bash
# Setup
source .venv/bin/activate
pip install -r requirements.txt

# Inspect — terminal summary, no Gemini, no files written
python app.py inspect path/to/drawing.pdf [--pages 1,3-5]

# Extract — full pipeline, writes to outputs/<timestamp>/
python app.py extract path/to/drawing.pdf [--pages SPEC] [--out DIR]
                                          [--no-gemini] [--refresh-regions]
                                          [--disable-rooms] [--disable-windows]
                                          [--debug] [--svg]
                                          [--ceiling-height M] [--door-height M]
                                          [--window-height M]
# --disable-walls is a deprecated alias for --disable-rooms (skips the wall
# network + room detection together).
# --refresh-regions ignores the cached region classification for the page
# and calls Gemini again instead of reusing gemini/region_cache.py's entry.
# Heights feed the per-room quantity takeoff (takeoff/). --ceiling-height is
# prompted for on a tty when absent (same gate as the scale prompt); defaults
# 2.4 / 2.1 / 1.2 m.

# Batch extract — discovers fixtures/sheets/*.pdf, prompts for detection options
# interactively, runs `app.py extract` 5-at-a-time (ProcessPoolExecutor)
python batch_extract.py

# Tests (unittest)
python -m unittest discover tests
python -m unittest tests.test_door_assembly.TestDoorAssembly.test_<name>
```

No PDF is committed to this repo. For a quick run, download the regression
corpus (see "Regression testing" below) and point `app.py` at any sheet under
`fixtures/sheets/` — `s01` (formerly `floor-plans.pdf`) and `s02` (formerly
`5-1133-WD03.pdf`) are the two primary references.

`--svg` additionally writes `page.svg` per page — MuPDF's own vector redraw of
the page (`extraction/renderer.render_page_svg`) at the same 150-DPI matrix as
`render.png`, so entity/takeoff bboxes overlay it unchanged and `/Rotate` is
already baked in. It is a redraw of the PDF, not of the extracted primitives, so
it never shows what detection saw. Off by default: measured across the corpus it
costs <=0.2 s/sheet but 0.2-21 MB (image-heavy sheets inline their rasters as
base64).

`--debug` writes `debug_trace.json` + a self-contained `debug_viewer.html` per page (per-primitive detection trace for diagnosing missed/false door detections — see the tuning guide's debug-trace playbook).

## Regression testing

**Before changing detection, read `docs/regression-testing-guide.md`.** It covers
reading the sweep report, the ground-truth file format and the rules for editing
it, adopting/revising sheets, the invariants (no committed PDFs, no
address-bearing text), and the traps that have already shipped bugs here.

Two tiers:

```bash
python -m unittest discover tests   # ~10s — synthetic topologies, run constantly
python tools/regress.py             # ~3min — 20 real sheets vs. committed ground truth
```

The corpus lives in `fixtures/sheets/` and is **not** committed (NDA). Download
the bundle — see `fixtures/MANIFEST.json`'s `storage` field for how to get it —
and verify with `python tools/fetch_fixtures.py`. Sheets are named by slug
(`s01`…`s20`); the two primary references are `s01` (formerly floor-plans.pdf)
and `s02` (the WD03 working drawing).

`tests/ground_truth/sNN.json` holds the user's verdicts and is committed. Three
lists per page: `confirmed` (correct detections), `false_positives` (wrong
detections, matched against emitted entities only), and `deferred` (misses the
user reported that we consciously chose not to fix). Matching is geometric —
type + IoU ≥ 0.5 — because entity ids are ordinal and shift when detection
changes.

`regress.py` exits 1 on a lost `confirmed` entity, a returned false positive, or
a sheet whose bytes no longer match the manifest — plus two more triggers the
guide's §6 table covers in full (an unscored ground-truth page, and a
manifest sheet marked `"labeled": true` whose truth file is missing or
reverted to `reviewed: null`); 2 when sheets are missing from disk; 0
otherwise. **New detections never fail the sweep** — they print under REVIEW
and wait for a verdict.

The loop when tuning detection:

1. `python tools/regress.py`
2. Open `outputs/regress/<slug>/<timestamp>/pages/page_NN/review_<type>.png`
   — every unreviewed detection is stamped with a short id (`d7` = door_0007)
   matching the sweep's REVIEW lines. Output persists there (gitignored,
   wiped per slug on that slug's next sweep) precisely so this image exists
   to open; `debug_viewer.html` is opt-in (`regress.py --debug`) for the hard
   cases, not written by default — it cost 200-300MB/sheet on the corpus's
   heaviest sheets.
3. `python tools/review.py <slug>` — ticks the correct detections, then the
   wrong ones (Space to toggle); anything ticked in neither is
   postponed and reappears next sweep. It writes `tests/ground_truth/<slug>.json`
   and sets `"labeled": true` in `fixtures/MANIFEST.json` (absent/false means
   adopted-but-unlabeled, which stays valid for every not-yet-reviewed sheet).
   Once flagged, the sweep exits 1 if that ground truth ever goes missing or
   reverts to `reviewed: null` — a durable, diffable record that the verdicts
   existed, so their loss can't pass silently. Commit both files as a data
   commit.
4. Fix the algorithm, and pin the topology with a synthetic test in the fast tier.
5. `regress.py` again: no lost `confirmed`, no returned false positives. A
   `deferred` entry that flips to CLOSED is confirmed by the user, then promoted
   to `confirmed` by hand — `tools/review.py` only records verdicts on a
   sweep's unreviewed detections, not this promotion.
   To SEE what a change did rather than read verdict deltas:
   `python tools/compare_sweeps.py <slug> --snapshot` after the baseline sweep
   (a re-sweep wipes the slug's previous run), then `python tools/compare_sweeps.py <slug>`
   after the re-sweep — writes `outputs/compare/<slug>/page_NN_side_by_side.png`
   (both runs, entities coloured by verdict) and `page_NN_changes.png` (a
   before|after zoom row per entity present in only one run). Guide §4b.

See `docs/regression-testing-guide.md` §4/§8 for the sweep-output and
review-tooling details, and §6 for the full exit-code table.

A revised drawing is adopted as a **new** slug (`python tools/add_sheet.py`),
never dropped over an existing one — an existing slug's bytes are immutable
because its ground truth is pinned to them.

## Module layout

The root holds thin orchestration entry points; detection and I/O live in packages (the `d61f0e2` refactor split the old flat modules — `heuristics.py`, `extractor.py`, `gemini_client.py`, etc. — and the 3,679-line `heuristics.py` monolith). Code movement only; behavior and the `outputs/` JSON contract are unchanged.

```
app.py             # argparse shell
pipeline.py        # run_extract — the 7-stage orchestrator
inspector.py       # inspect-command logic
batch_extract.py   # interactive parallel batch runner over fixtures/sheets/*.pdf
models.py          # shared dataclasses (depended on by everything)

extraction/        # PDF -> normalized primitives + rendering (owns SCALE)
  extractor.py  plumber.py  renderer.py
detection/         # heuristic detection (the split monolith)
  __init__.py      # public facade: run_heuristics + detect_* re-exported
  orchestrator.py  # run_heuristics (named to avoid clash with root pipeline.py)
  geometry.py      # shared primitives (_distance, _line_angle_deg, …)
  layers.py        # OCG layer-name hints/priors (_layer_hint, _layer_strong_prior)
                   # — confidence boost when a layer name names the element type
  walls.py         # INTERNAL wall-centerline network (WallNetwork) — walls are
                   # never emitted as candidates; feeds rooms.py + postprocess.py
  rooms.py         # detect_rooms — rooms = free-space components between wall
                   # solids (shapely); door/window bboxes seal the openings
  windows.py  labels.py  schedules.py  postprocess.py
  doors/           # door subpackage, acyclic: constants <- arcs/leaves/shape/sliding <- folding <- assembly <- detect
                   # sliding.py: arc-less sliding doors from oriented panel-rectangle
                   # patterns (leaf_pair + pocket_leaf + parked_leaf — the last is the
                   # fill-less tier: a stroked ring parked at a wall-band jamb, slide
                   # law opening ≈ panel length) — see the tuning guide §3.9
                   # folding.py: arc-less folding/bifold doors from hinge-connected
                   # white leaf panels (chain + parked stack_pair) plus open_v — the
                   # fill-less tier: a lone half-open V of double-line stroked leaves,
                   # jamb-anchored + span law — tuning guide §3.10
layout/            # page segmentation — splits a sheet into its drawings
  constants.py  occupancy.py  segmenter.py  clips.py  filter.py
gemini/client.py        # Vertex AI client (was gemini_client.py)
gemini/classifier.py    # region classification (replaced candidate validation)
gemini/region_cache.py  # classification cache, keyed by page content + region geometry
gemini/room_labeler.py     # room names from in-polygon text (one text-only call)
gemini/room_label_cache.py # label cache, keyed by page + room geometry + prompt version
scale/            # drawing-scale resolution: /VP measure viewports, scale text,
                  # a tty-gated prompt, and geometric binding to floor_plan regions
takeoff/           # rooms + scale + heights → floor / ceiling / net wall m² per room
                   # (units, heights, per-room scale + sheet-size verification,
                   # opening assignment, plausibility — dimension strings /
                   # door-leaf band, compute_takeoff). Pure; wired in
                   # pipeline.run_extract after finalize_candidates.
  document.py      # serialisation only — the takeoff.json overlay document
debug/             # trace.py (DebugTraceCollector) + renderer.py (HTML viewer)
tools/             # standalone dev scripts (numpy/cv2)
```

Import from the `detection` facade (`from detection import run_heuristics, detect_doors`) rather than reaching into submodules. Tunable constants are co-located with their detector: `DOOR_*` in `detection/doors/constants.py`, `WINDOW_*`/`WALL_*`/`ROOM_*`/`LABEL_*`/`SCHEDULE_*` in the matching `detection/*.py`, cross-validation `CROSS_*` in `detection/postprocess.py`. Tests import internals from their real homes (e.g. `from detection.doors.arcs import _prune_arc_spurs`) — there is no compatibility shim.

Room detection: order matters — doors/windows detect first, then `detect_wall_network(paths, text_spans, exclude_path_indices)` builds the internal centerline network (text spans disambiguate white fills), then `detect_rooms` extracts rooms as the connected free-space components of the page after subtracting barriers. The exclusion set (`door_open_leaf_path_indices`) keeps single-swing doors' OPEN-leaf linework out of face collection entirely: a swing leaf is drawn standing open in the wall pen, parallel to whatever wall it parks beside, and pairing it inflates that wall's band across the swing side (measured on floor-plans: door_0000's double-line leaf paired with both faces of the 7px hallway wall and the collinear merge carried the inflated 18.5px thickness over the whole inter-door run, fencing an 8px strip out of the hallway); each excluded path must also lie fully inside its door's zone (bbox ± 2px, the rooms-stage convention) because the leaf-companion finder serves the opening check and over-collects — a leaf parked 1.9px off a jamb claims the jamb's own faces as companions (measured: door_0005's companions were the wardrobe end panel's two faces, and excluding them dissolved the wardrobe/bedroom split), while real partitions extend past the swing zone and leaf ink never does. Merged french pairs are left alone (their leaves are drawn closed IN the wall plane — legitimate wall evidence), as are sliding/folding panels (they lie in or seal their wall plane by construction) — but a GARDEN pair's leaves park OPEN at the outer ends of the opening, perpendicular to their wall and parallel to the flanking room walls, so the merge preserves both halves' leaf ink (`leaf_path_indices`) and the exclusion covers garden doubles too (measured on floor-plans door_0016: each parked double-line leaf paired with the bedroom side wall ~30px away into a phantom 30.5px band whose solids fenced a 37px-wide strip of bedroom on each side of the doorway, and a leaf/jamb pair pinched the doorway tongue to the leaf faces); the in-zone gate drops the halves' over-collected jamb companions exactly as it does for singles. Before any pairing, striped-field faces are demoted to the weak (material-gated) pipeline (`_demote_lattice_faces`): ≥ `WALL_LATTICE_MIN_RUNGS` (5) parallel SAME-PEN faces at equal wall-like pitch (≤ `WALL_MAX_THICKNESS_PX`, one missing rung tolerated as a 2×-pitch gap — a text mask can eat a joint line) and rung extents chaining along the run — that is a drawn surface pattern (paving bonds, tile fields, floorboards, roof joists, stair treads, balustrades, hatch, table rows), never wall structure, whatever its pen weight or rung LENGTH: rooms are wider than the max wall pitch by definition, so real walls cannot stack five deep, and short strokes at wall pitch five deep are still never walls (there is no rung length floor — s17's treads measure 47.7px, s18's ramp balustrade 12.75px, and under the old 48px floor both stayed strong and paired into 13px "walls"). A rung is an EXTENT-CONNECTED cluster of the collinear pieces at one offset (`WALL_LATTICE_TOUCH_GAP_PX` along the axis), never every piece on the page at that offset: a room's wall face merely collinear with a distant field's course is not that course (measured on s17: the WC's top face at y=1167 shares its offset with a roof-tile rung 2000px to the right; under offset-only rows the whole plan's exterior walls on s18 were demoted along with the roof fields they happened to align with, and the plan detected no rooms), so a row lying apart from the run along the axis is SKIPPED, never a break (a break left 3 of a 22-rung roof-tile field strong on s03, and they paired into phantom bands), a same-offset row that does touch the run is the same rung split by a text mask wider than the touch gap and is absorbed, and every rung seeds a run of its own. Chained membership alone is NOT enough — the run must also reach a simultaneous cross-section of ≥ 5 rungs somewhere along its axis (`_field_span`, sweeping the rungs' extents with ends sorted before starts so end-to-end staggered courses never count as coexisting): distinct parallel wall bands at quasi-equal spacing chain too (measured on s07: three 8px wall bands at 8–9px gaps chained into a 5-rung "ladder" whose envelope glue deleted the plan's central wall belt and every room with it — their pieces occupy disjoint spans and never stack deeper than 3). And only the rungs lying IN that stacked span are demoted (`WALL_LATTICE_FIELD_COVER_FRAC` 0.5 of a rung's extent): a long wall face that a short equal-pitch stack (a radiator's edge lines drawn parallel to it) coexists with over a fraction of its length keeps its face rights. Pen weight alone cannot catch striped fields (measured on 5-1133: the OPEN GLAZED VESTIBULE's paving bond is penned 1.05 vs the 1.50 wall reference — ratio 0.70, above the `WALL_WEAK_STROKE_RATIO` demotion gate, and the sample set has real wall pens down to 0.67 of the reference, so the ratio cannot be raised; the field paired into phantom 31px wall bands that chopped the open vestibule into four phantom "rooms", anchored white rooflight rings, and mis-contexted the glazing-mullion fallback doors 0110–0113 as "in_wall"). Five rungs (not four) keeps a cavity party wall drawn leaf/cavity/leaf at equal widths out of the demotion. Hatch is the same signature pitched too tightly to be walls, and the same scan catches it: two strokes of one field otherwise pair with each other like any parallel pen mates. Inside a straight band the phantom pair hides in the real one; at an L-corner the band turns while the hatch angle does not, and the pair juts out (measured on floor-plans: strokes 2502/2516 of the 45° magenta field paired 28.1px apart into a diagonal centerline whose solid chamfered room_0000's and room_0001's top-right corners ~16px, and the left wall's hatch sawtoothed room_0001's edge into 30 vertices). PITCH is what proves they are not walls, not their diagonality (a real 45° bay wall pairs at wall spacing and survives): five hatch courses COEXISTING at ~4px pitch span ~16px, well inside one band's worth of `WALL_MAX_THICKNESS_PX`, so the lines are that band's material rather than five walls — measured, both reference PDFs' hatch fields pitch at 4.05/4.07px while the tightest real striped field on either is 11.4px. Stairs are FURNITURE to the room stage (RICS GIA takeoff runs the room polygon to the enclosing walls straight through the flight; treads/risers are a separate structural takeoff), yet stair ink is drawn in the wall pen (s03: 1.5px, the reference itself; s13: 0.75) and paired like walls (s03 FF: two treads at th 14.8; GF: the stringer and the balustrade line), so `_demote_stair_faces` runs BEFORE the collinear merge, on one face per PATH (a landing edge collinear with a wall nib's face merges into it, and demoting the merged run would cost the nib its face), and sends stair ink to the weak pipeline like lattice members. Three recognizers keyed on drawing convention, never on pen: a TREAD RUN — ≥ `WALL_STAIR_MIN_TREADS` (3) parallel same-pen faces at a consistent pitch (`WALL_STAIR_MIN_PITCH_PX` 6 to `WALL_THICK_MATERIAL_MAX_PX`, ±`WALL_STAIR_PITCH_TOL_FRAC` of the median — s13's cut treads pitch 8.7–11; a jamb one wall-width past the last tread splits the chain instead of killing it), extents inside the median-length member's ±`WALL_STAIR_END_TOL_PX` (the median, never the longest: the long wall face the flight abuts is one pitch off the last tread and would otherwise be the reference), each ≥ `WALL_STAIR_MIN_LEN_FRAC` of it (treads clipped by the section cut are shorter), no member longer than `WALL_STAIR_MAX_ASPECT` (10) pitches (a wall drawn as 4–5 parallel lines at leaf pitch runs 16–20× its pitch on s17, real flights 3.3–4), no member a short OBLIQUE stroke (s20's cross-hatch: 20–43px strokes at 15°/135° and 12–18px pitch is a flight by every other measure), plus EVIDENCE from a same-pen transverse line within one flight depth: one properly CROSSING a tread's interior (the direction arrow; both overshoot by `WALL_STAIR_CROSS_MARGIN_PX`) or an OBLIQUE one that ≥ 2 treads END on (the section cut clips the treads it passes; a wall's perpendicular end cap closes its faces' ends too but never obliquely, a hatch stroke's own ends lie on the faces rather than the faces' ends on it, and s17's orange 'to be removed' ticks crossing a 5-line cavity wall are another pen) — the discriminator against a cavity party wall drawn leaf/cavity/leaf at equal width, which nothing crosses; a run whose crossers include ≥ 3 mutually parallel lines is cross-hatch, not a stair; perpendicular touching lines (nosing edge, stringer) are stair ink once the evidence is in, never evidence, so is an END CUT — a same-pen end-to-end chain inside the flight zone whose near edge lies within one pitch of the first or last tread and which spans the flight width (s17's shallow zigzag cuts one pitch above the first and below the last tread touch and cross nothing, and fenced the flight into its own room between them) — and any transverse a non-member wall face pairs with (a partition stub alongside the flight) stays; a STAIR ARROW — a same-pen face chain walked end-to-end away from a marker ring (`_FillRing.is_marker` arrowhead) with `WALL_STAIR_TEXT_TOKENS` (UP/DN/DOWN) text within `WALL_STAIR_TEXT_NEAR_PX` of it; the chain and every face it properly crosses are stair ink (walls are never crossed by wall-pen linework — s03 GF's arrow crosses the stringer and the balustrade line into the flight — and a leader crossing a wall has no UP/DN); a WINDER FAN — ≥ 2 unpaired non-axis faces longer than `WALL_HATCH_MAX_LEN_PX` sharing an endpoint at ≥ `WALL_STAIR_FAN_MIN_ANGLE` (risers fanning from the newel; a 45° bay wall pairs at wall spacing). Zones (member bboxes, touching zones merged — arrow + winder box + flight) then absorb the rest of the symbol to a fixpoint: a face inside a zone joins when it is the collinear end-to-end continuation of a member (the crossed stringer's lower run) or when every wall-spacing partner it has is stair ink (the balustrade line pairing with that stringer, the landing edge, clipped treads, the cut) — a real wall pair inside the zone anchors itself and stays, which is what kept s20's short-piece wall faces inside its cross-hatch zones (measured: 840 faces demoted, four rooms lost, before the anchor rule and the hatch exclusion). Barriers are ALLOWLISTED wall evidence, not all linework — room-interior ink (floor-tile grids, furniture outlines, sanitary symbols, text masks) must not chop the free space. Four barrier tiers: (1) wall solids — paired centerline segments dilated to their measured thickness (`WALL_MAX_THICKNESS_PX` 36px covers heavy blockwork bands; strong non-demoted faces spaced past the cap up to `WALL_THICK_MATERIAL_MAX_PX` 48px — a 1:50 400mm band — still pair as a THICK tier gated exactly like weak pairs, on `_band_has_wall_material` + `_claims_interior_pair`, because a locally thickened pier otherwise encloses its own hatch as a free-space pocket: floor-plans' bedroom chimney breast bulges the 19.3px exterior wall to 39.2px and its hatched interior came out as a 35×96px phantom room; the tier is OFF for the interim stroke-reference pairing so 36–48px annotation coincidences cannot skew the pen median, and the 4px collinear-merge offset tolerance plus the collapse thickness slack keep the local thick segment from carrying its width onto the main run); hairline faces (below `WALL_MIN_STROKE_WIDTH_PX` — the 0.45px joinery/fixture pen new partition walls are often drawn in) also pair, and faces penned under `WALL_WEAK_STROKE_RATIO` (0.66) of the paired-wall stroke reference are DEMOTED to the same weak class even when they clear the absolute floor — floor-tile and paving grids are drawn at ~half the wall pen (0.75 vs 1.5 on 5-1133) and otherwise pair with the real wall faces they run parallel to at wall-like spacing, stamping phantom wall bands across room interiors (measured on 5-1133: a tile-line/wall-face pair ate the WC's toilet strip, and tile lines split Family Bath+Utility three ways) — but a weak-involved pair survives only when the band between the faces carries drawn wall MATERIAL (`_band_has_wall_material`): short strokes DIAGONAL to the band axis (hatch, cross-hatch, the X's of blocking rectangles — the universal new-partition signature) at ≥ `WALL_WEAK_MATERIAL_PER_100PX` (3/100px, real partitions measure ≥4.8 while glazing strips and paving grids measure ≤2.6), spread over ≥ half the run, on runs ≥ `WALL_WEAK_MIN_RUN_PX` (30px — shorter material-dense slivers are dimension-tick clusters), counting coincident strokes ONCE (`_collect_material_marks` dedups by location+angle: CAD exports re-draw each oblique dimension tick in a heavy and a light pen and once per adjoining dimension run, so 2 tick locations arrived as 6 marks and turned the "750/800" dimension line into a phantom partition across the bath); diagonal-only keeps liner lines (parallel) and radiator fins (perpendicular) out, so plain hairline pairs — wardrobe edges, counter fronts — never become walls; a weak pair that passes the material gate is still dropped when a KEPT meaningfully-tighter parallel pair lies inside its band over ≥ half its run (`_claims_interior_pair`, `WALL_WEAK_CLAIM_MARGIN_PX` 2px) — an over-wide pair (a room-interior line paired with a real wall's FAR face) encloses the real wall's band and passes on that inner wall's OWN hatch/blocking (measured on 5-1133: tile line 992 paired with the WC/bath divider's far faces at th 19.5 enclosing the true 12px divider pair, holding the WC's bottom edge ~5px high on the tile line; killing all its pairs also removes the line's face from the network, so no thin barrier survives either) — and material-backed weak faces join `network.faces` as paired faces but stay out of `wall_stroke_reference` (stroked=False) so hairline members cannot drag the rooms' pen-weight gate down to fixture territory; on color-coded drawings pairing itself is additionally gated by pen COLOR at the room stage (`ROOM_WALL_PEN_MIN_FRAC` 0.15 of the network's paired-face length makes a pen a wall pen): cross-pen pairs never form (`_pens_compatible`), and a SAME-pen pair whose faces are all plain stroked non-wall-pen ink (no wall fill, layer hint, or material backing) is furniture coincidence — its segment is dropped from the barrier solids and its faces get no paired-barrier rights (measured on floor-plans room_0012: the bed's pillow rectangles paired red-red at th 24/32px and the solids fenced the pillows plus the ~5px strip to the wall out of the bedroom, notching the outline around the bed); the redundancy collapse that dedups parallel centerlines absorbs a shorter "duplicate" only when its thickness stays within `WALL_REDUNDANT_THICKNESS_SLACK_PX` (4px) of the kept run — a duplicate re-measures the SAME band, while a wall face pairing with ANOTHER wall's face across a corridor of wall-like width shares one face with the real run, passes the collapse offset gate on its own inflated thickness, and absorbing it used to transfer the corridor width onto the entire run (measured on floor-plans: the bathroom/landing wall's 7.2px run took th 35.2 from a stair-corridor pair over a 41px overlap, and the poisoned solid fenced a 16px strip out of the bathroom and 13px off the landing over the whole 165px run); such a pair stays a separate segment whose solid is local to its actual overlap; and a strong pair is dropped outright when it is a wall face paired ACROSS THE ROOM (`_claims_far_side_pair`): a kept, meaningfully tighter parallel pair or filled band shares one of its faces and lies on the FAR side of that face over ≥ half the run, and the band on this side carries no wall material (fill cover under `WALL_FAR_SIDE_FILL_COVER_MAX` 0.10 and no hatch) — a wall's material lies on exactly one side of each face, so the material-less band is the room: kitchen counter fronts, wardrobe fronts and corridor-facing walls are drawn in the wall pen at wall-like spacing (measured on s03: the worktop outline 35.2px off the kitchen's inner faces, just under the 36px cap, paired into phantom bands that fenced the counters out of the KITCHEN and the WDR wardrobe out of its bedroom; on s01 the same rule stops stringer/wall pairs sealing the stair flights, so the landing, flights and hall come out as one room — the stairs-are-furniture verdict), while a cavity wall drawn leaf/cavity/leaf keeps its leaves and, when the cavity is hatched or filled, the cavity pair too; the dropped pair's PARTNER — paired with nothing else — is the fixture front itself and is demoted (stroked=False) so it gets no lone-face barrier rights either, because on pen weight alone the counter lines re-fenced the same strip as thin barriers (the walkable-area-only kitchen); (2) wall-fill polygons — closed rings reconstructed by chaining consecutive same-fill `l` items (the Vectorworks filled-polygon signature), each fill COLOR rated by the shape of its ink (`_rate_fill_classes`: run length in thin bands vs compact blocks, measured with area+perimeter equivalent-rectangle sides so L/U-shaped runs stay band-like) — wall-rated rings become barrier area (seals band interiors, corner posts, jamb stubs), furniture-rated classes (cabinet blocks) are excluded entirely, unrated classes keep the permissive legacy rule; a fill outline's `wall_fill` flag survives the collinear face merge only when fill-outline members cover ≥ `WALL_FILL_MERGE_MIN_FRAC` (0.5) of the merged run — the same laundering guard the merge's one-run-one-pen rule gives annotation ink, because a wall band's 17px end stub collinear with a 354px stroke otherwise stamps fill evidence over the whole stroke (measured on s03: grey roof-tile stripes standing on the wall band's jamb stubs became full-height wall-fill barriers, exempt from lattice demotion, and their pairs re-fenced the ground-floor roof into three pseudo-rooms; on s18 a 0.75px tile line laundered the same way split the en-suite at a grout joint); marker rings — tiny 3-vertex triangles or concave 4-vertex darts up to `WALL_MARKER_MAX_SIDE_PX` (24px) bbox side (`_FillRing.is_marker`) — are leader/dimension arrowheads drawn in the wall pen (walls are rectilinear, so a small triangle is never material) and are dropped from the class rating, the barrier area, and wall-fill face qualification, while same-sized convex quads (jamb stubs, corner posts) stay; and fill SEAMS never become faces (`_fill_seam_indices`): exporters triangulate fills and PyMuPDF chains each triangle into its own ring, so a band arrives as two triangles that BOTH carry the shared diagonal — an `l` item with fill on both sides, which no pen ever shows — and abutting same-fill strips share their joint edges the same way; a coincident edge (same fill, same rounded endpoints, ≥ 2 distinct rings) whose midpoint has fill on both sides is dropped from face collection, while an overdrawn ring keeps its outline because those duplicates have fill on one side only (measured on s03: the bedroom band's diagonal, 17.7px over 336.7px = 3.0° — inside `WALL_PARALLEL_ANGLE_TOL` 4° — paired with the band's own face into a slanted centerline whose solid stood 18px off the band at one end, cutting room_0000's right edge 17px short at the top and flush at the bottom, with rooms 0003–0006 skewed 5–14px the same way; s03 has 234 such duplicated seams, s07 2,773, s18 32,139, s01 none — its walls are stroked); (3) thin buffers of QUALIFYING faces only — paired into a centerline, outlining a wall-rated fill, wall-layer-hinted, or stroked at ≥ `ROOM_BARRIER_STROKE_RATIO` (0.75; raised from 0.66 — random-size patio paving joints evade the equal-pitch lattice demotion and measure 0.70 (1.05 vs the 1.50 reference on 5-1133), fencing patio cells against exterior door plugs and the bay wall into phantom door-bearing "rooms" at 0.81–0.90 confidence, while every real LONE barrier face on both reference PDFs measures ≥ 1.00; the lone-face gate can sit above the pen of the lightest real walls because those pair and seal through their segments) × the length-weighted median stroke of the paired wall faces (`wall_stroke_reference`); a STROKED face penned under that gate whose only claim is pairing must additionally have its own segments cover ≥ `ROOM_PAIRED_FACE_MIN_FRAC` (0.5) of its run — pairing is path-index-granular, so one 22px sliver pairing two paving joints 14px apart qualified a 230px tile line full-length and re-fenced the bay-corner patio after the ratio raise; noise measures ≤ 0.36 paired extent, real sub-gate paired faces ≥ 0.71, and UNSTROKED faces (material-backed hairline partitions, fill outlines) keep full-length qualification since they legitimately pair over as little as 0.13 of their run where openings/text ate the partner face; hatch strokes are excluded unless they outline wall fill (a corner post's short diagonal edges are material, not hatching), and faces inside a door bbox are excluded so the open leaf can't slot the swing area; thin buffers use `ROOM_LINE_BARRIER_PX` = `ROOM_WALL_DILATE_PX` (2.0) with SQUARE caps so a face's buffer and its pair's dilated solid put the room boundary at the same standoff and meet flush at corners — a 0.5px standoff mismatch plus flat caps leaves pen-width corner notches at every barrier-tier transition, which survive the free-space opening (filling them would be extensive) and which `ROOM_SIMPLIFY_TOL_PX` then redraws as long shallow diagonals (measured on floor-plans room_0012: an 83px straight pier face came out as a 2px slant); (4) white (background-fill) rings — a ring mostly covered by the text written inside it is a text mask (dropped, `WALL_WHITE_TEXT_COVER_FRAC`); textless band/post-sized white rings are hollow-wall/joinery candidates, accepted in rooms.py when they touch wall material INCLUDING door/window bboxes (`_accept_white_walls` — hollow runs are interrupted by their own openings; only doors ≥ `ROOM_OPENING_MIN_CONFIDENCE` count as anchors, so a phantom door detected on a white fixture symbol cannot turn the fixture into wall; and a ring fully inside a confident door's bbox is the OPEN LEAF drawn in the same white-rectangle signature — it would anchor on its own door's bbox and notch the swing out of the room, so it is withheld from candidacy entirely, while fallback-tier doors get no such veto because they are typically detected ON white joinery rectangles whose rings ARE the partition, and sliding doors (`assembly_type` "sliding") are exempt for the same reason — their panels lie in the wall plane by construction (drawn closed across the opening or parked in the pocket, never across a swing square), and withholding them deletes the very partition the run-bridging seals the doorway with (measured on 5-1133 GD5: parked pair, bbox covers only half the doorway, rooms merged), then bridged across open spans with band-shaped convex hulls (`_bridge_white_runs`, wardrobe-divider runs) — but a bridge only closes an OPEN span: touching rings (hollow-wall cavity segments chain contiguously through corners) union into run components first, candidate pairs are taken shortest-gap-first, and pairs already connected never bridge. Between two small cavity segments on perpendicular runs of one chain, the redundant hull is thin enough to pass the band test and chords diagonally across the room corner — that chord (not the arrowhead linework, which never qualifies as faces) was what notched room outlines around leader arrows. Opening seals at the surviving doors/windows complete the barrier set. Before any of this, door candidates whose bbox is mostly covered by the text written inside it (`ROOM_OPENING_TEXT_COVER_MAX` 0.60 — "WALL TYPE 1" tag boxes detected as leaf rectangles; same principle as the white text-mask rule) are dropped from the room stage entirely: no seals, no white-wall anchoring, no face exclusion under the bbox — real swing bboxes measure ≤ ~0.45 text cover even with a room label crossing them. A straight window's bbox lies in the wall band and seals as-is, but a DIAGONAL window (angled bay face) has a square-ish axis bbox that overhangs the wall plane on both sides, so it seals along its glazing diagonal instead (`_window_seal`, picking the bbox diagonal matching `glazing_angle_deg`, buffered to the band's measured half-thickness) — measured on 5-1133, bay window W11's square seal bridged the bay wall to the terrace setout lines and fenced a paving pocket into a phantom room. A door bbox covers the swing — room floor, not wall — so it is replaced by thin plugs along its wall-plane edges (`_door_plugs`), keeping the swing inside the room and splitting adjacent rooms exactly at the wall plane. An edge qualifies by the coverage profile of wall material hugging it (sampled along the edge, extended `ROOM_OPENING_SEAL_PX` past the bbox to reach jambs the arc stopped short of): either an interrupted wall run (both ends anchored, middle empty — the open-doorway case) or a drawn-through wall plane (near-total coverage — existing-opening sills and closed sliding/garage panels, common on working drawings, where the plug just shadows drawn linework). End anchors are measured over a jamb-scale window (`ROOM_PLUG_ANCHOR_WIN_PX` 24px, never larger than the legacy n//4 quarter): a jamb is jamb-sized regardless of doorway width, and on a 165px garden pair the quarter diluted real 45°-bay jambs to 0.42 (gate 0.5) while a perpendicular edge crossing the angled wall obliquely PASSED as an interrupted run (measured on 5-1133 door 0121: the true doorway edge got no plug, the parked-leaf edge got a phantom one, and the purple bay room leaked through the doorway while the phantom plug fenced terrace paving into phantom rooms). A garden pair's parked-open leaf edges (`_open_leaf_edges`, keyed on `swing_layout == "garden"` + `leaf_bbox_a/b` lying along opposite bbox edges) are vetoed outright — the parked leaf is room/garden floor, never wall plane — and so is the swing-extent edge the merged `opening_line` lies along: the chord joins the two arc endpoints farthest apart, which for a garden pair are always the parked leaves' open TIPS (tip-to-tip spans the full opening W, tip-to-closed-end only ~0.71 W), so the chord edge bounds the swing squares and never the doorway (measured on floor-plans door_0016: the swing-extent edge anchored on the two jamb walls continuing past the doorway, pattern-matched an interrupted run, and its phantom plug held the bedroom outline 5px short of the doorway — the garden-pair analog of `_restrict_swing_plugs`; a diagonal garden pair's chord matches no axis edge and adds no veto) — while french pairs keep their leaf edge eligible because their collinear leaves are drawn closed IN the wall plane. A sliding door's short-end edges are vetoed the same way (`_sliding_end_edges`, aspect-gated at `ROOM_SLIDE_END_ASPECT_MIN` 2.0 — sliding bboxes elongate along the wall by construction, measured 9.2–24× on both reference PDFs): the short ends CROSS the wall band, so the only profile they can match is a full-cover re-assertion of that band, and their plugs are thicker than the linework they shadow (measured on floor-plans door_0011: the bottom end-edge plug bit a 12×6px square out of room_0010 and a 7×10px notch out of room_0005). A qualified plug's `ROOM_OPENING_SEAL_PX` end extensions are also TRIMMED back to the farthest profile sample still touching wall material within the plug half-width: a tail exists to reach into the jamb the bbox stopped short of, and one hanging in free space — qualified by the loose hug of a parallel band, or overshooting a crossed jamb's far face — seals nothing and stamps a plug-width notch into the adjoining room (measured: door_0002's top-left tail floated at 8.7px and notched room_0005 beside the jamb; the same tails bit the WC edges at 5-1133's leaf_pair sliding doors 0013/0014), while any clearance gap a trimmed tail no longer bridges is far thinner than the `ROOM_GAP_CLOSE_PX` pinch, so the rooms it separates still split. Doors with no qualifying edge first retry plug qualification with their own withheld leaf rings added as material — a leaf drawn CLOSED lies in the wall plane and may be the door's only evidence there (timber gates in fence lines), so the plug shadows the leaf instead of the dilated bbox stamping the swing square into free space — and only then fall back to the dilated bbox. The bbox fallback is the one seal with NO evidence of its own (every plug profile qualifies against drawn wall material; the stamp is pure trust), so it requires the door to survive the pipeline's own conviction: `ROOM_BBOX_SEAL_MIN_CONFIDENCE` 0.55, mirroring `OFFLINE_MIN_CONFIDENCE["door"]` — detect_rooms consumes post-suppression candidates BEFORE the offline floor, and a door the pipeline itself rejects must not reshape a room outline (measured on 5-1133: the 0.52 bath-fixture FP — single_line_leaf on a toilet pan corner, no_wall — stamped a 68×50px notch into the FAMILY BATH edge, while no real door on either reference PDF uses this fallback; all seal through plugs). Plug seals stay available from `ROOM_OPENING_MIN_CONFIDENCE` (0.40; doors are penalty-only in cross-validation, so fallback tiers never climb back over). Fallback-tier doors (`DOOR_FALLBACK_CONFIDENCE` 0.35, deliberately capped under the offline floor and kept only for Gemini arbitration — label boxes, glazing mullions, section markers) seal exclusively through plugs that carry their own evidence: the interrupted-run profile (the doorway signature — a real low-confidence sliding door between jambs still splits its rooms), or a drawn-through plane the plug actually LIES IN (≥ `ROOM_PLUG_IN_WALL_FRAC` 0.80 of its area on drawn wall material, so it only re-asserts existing barrier and seals hairline gaps in it — measured phantoms floating NEAR a wall peak at ~0.77 overlap while on-plane plugs measure 0.84+). Full coverage by mere proximity is NOT evidence — that is how an annotation box hugging a wall band would stamp a free-space notch into the room outline — and a phantom door in open space contributes nothing at all. Drafting gaps are sealed by morphologically OPENING each free-space component (`ROOM_GAP_CLOSE_PX`, in `_free_space_components`) — the complement-side equivalent of closing the barrier union, which must NOT be buffered directly: GEOS silently drops legitimate room-sized holes from the giant multi-hole polygon (one 22px sliver closing a ring in the kitchen erased bedrooms 2/3 + hall wholesale); components are filtered by area, page fraction, page-border contact, hole fraction, erosion, wall-contact ratio, and attachment to a major wall mass (kills legend tables / dimension frames); a component lying fully inside a confident (≥ `ROOM_OPENING_MIN_CONFIDENCE`) door's bbox is the swing/threshold recess fenced by the door's own seals — door floor, dissolved, not a room (floor-plans' 1800mm garden pairs fenced 105×25px recess strips and whole swing squares into phantom rooms; folding doors dissolve over a wall-band-deep zone, bbox ⊕ `WALL_MAX_THICKNESS_PX` instead of ⊕ `ROOM_OPENING_SEAL_PX`, because a parked stack stands off its opening plane by the threshold depth — the 26px strip between 5-1133's kitchen CL-door stack and the wall band it serves sat outside the ⊕12 zone, fenced between the band and the stack's own top plug); and a closet-scale component whose ONLY opening is a window (`door_openings == 0`, `window_openings > 0`, area < `ROOM_BLIND_WINDOW_MAX_AREA_PX2` 10k px²) is dropped as the exterior side of that window — terrace pockets beside 5-1133's bay windows measure 2.7–3.7k px² while every real window-bearing room on both reference PDFs is ≥ 17k px² and carries a door; blind window-LESS small rooms stay, floor-plans has real ones at 3.3–8.5k px² (missed-door cases). The uncapped complement (`_drop_window_exterior_sides`): a straight window's bbox is pushed `WALL_MAX_THICKNESS_PX` out perpendicular to the glazing on each side, and when one side holds a door-bearing room while the other holds only door-less components, those door-less components are the exterior that room looks out over — a lower roof, terrace or lightwell — and are dropped whatever their size (measured on s03: the ground-floor roof, a striped field fenced by its outline above the PROPOSED BEDROOM, came out as a 133k px² door-less "room" across the bedroom's window). Two entered rooms sharing a borrowed light both stay, two door-less sides cannot be told apart and both stay, and a garage whose garage door reads as a window keeps its verdict because its far side is open ground, not a room; a room counts as "on a side" only when its polygon overlaps the probe by ≥ `ROOM_WINDOW_SIDE_MIN_OVERLAP_PX2` (16 px²), so grazing a probe corner past a jamb is not facing the window. Rooms are heuristic-only: never sent to Gemini, bypass the `OFFLINE_MIN_CONFIDENCE` floors and NMS, and carry the closed polygon in `Candidate.evidence["polygon"]` / `Entity.attributes["polygon"]`. Curved (Bezier) walls are out of scope — only straight `l` faces and filled `re`/`qu` bands feed the network, so rooms bounded by curved walls leak open and are dropped. Known limitation: hairline-pen partitions WITH material between their faces (hatch/blocking) now bound rooms via the weak-pair material gate, but boundaries drawn ONLY as plain sub-threshold lines (e.g. a fitted-wardrobe run with nothing between the faces, 0.45px — the same pen as sanitary fixtures) still do not, so such spaces come out merged into one oversized room; accepting bare hairline pairs would reopen every fixture false-positive, so that residue belongs to a future room-label/Gemini arbitration layer, not to the barrier rules.

Wall/room world-space gates (the `W`-classed constants in `docs/scale-normalization-findings.md` §4) scale via a per-page factor threaded from `scale.factor.detection_scale(page_scales, regions, page_number)` into `detect_wall_network`/`detect_rooms` as `scale_factor`: `f = 50 / nominal_denominator`, so f=1.0 (identity, unchanged behavior) at 1:50 and on unresolved-scale pages, f=0.5 at 1:100, etc. Paper-space (`P`) and dimensionless (`D`) constants are left unscaled — see that doc's §4 table for the full per-constant classification and rationale. Only a DRAFTING scale drives the factor — a nominal (standard) denominator from any source, or a raw viewport value (s13's CAD-declared 1:136.4). A measured, non-standard denominator that is not viewport-declared (s01's dimension-measured 1:92.2, stored by the user) feeds the takeoff but NEVER the gates: detection runs identity with `SCALE_FACTOR_MEASURED_ONLY`, because the W constants were calibrated at f=1.0 on ink spanning both reference sheets' true world densities (s01's paper conventions are standard — wall pen 1.5px, hatch pitch 4.05px, same as s02 — while its world ink measures 1:92.2, so scaling the gates by 50/92.2 pushed s01's own calibration features just outside them: the 25px party wall past the 19.5px cap, its 30–35px hatch past the scaled material caps, plugs short of their jambs; rooms fell 13/13 → 7/13 with 17 phantoms — findings doc §4f).

## Gemini / GCP auth

`gemini/client.py` uses Vertex AI via `google-genai` (`vertexai=True`). Required before the pipeline can call Gemini:

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>           # or set GOOGLE_CLOUD_PROJECT
# Optional: GOOGLE_CLOUD_LOCATION (default us-central1)
```

Model is hard-coded to `gemini-2.5-flash`, called twice per page at most:
once for region classification (`gemini/classifier.py`, image crops, before
detection) and once for room labelling (`gemini/room_labeler.py`, text only,
after `finalize_candidates`). Both are schema-constrained and separately
cached (`gemini/region_cache.py`, keyed by page content + region geometry;
`gemini/room_label_cache.py`, keyed by page content + room geometry + prompt
version). Gemini no longer votes on individual door/window/room/label/schedule
candidates; `pipeline.finalize_candidates` applies the `OFFLINE_MIN_CONFIDENCE`
floors unconditionally regardless of Gemini. `--no-gemini` skips both calls
and reuses whichever cache exists for the page; a miss warns instead of
calling out — `REGION_CACHE_MISS_OFFLINE` falls back to detecting the whole,
unfiltered page, `ROOM_LABEL_NO_GEMINI` just leaves that page's rooms
unnamed. Pass `--refresh-regions` to force a fresh classification call even
when a region cache entry exists; there is no equivalent flag for room
labels, so to force a single page's labels to be recomputed, delete that
page's cache file: `.room_labels_cache/<pdf-stem>_p<NN>_*.json`.

The call is schema-constrained (`classifier.RESPONSE_SCHEMA` passed as `response_schema`, not plain JSON mode): the decoder cannot emit a response that fails to parse or a `type` outside `REGION_TYPES` — measured 2026-08-05 on `LOCATION_PLAN…-s11`, where an unconstrained response started as valid JSON, degenerated mid-stream into an off-topic fragment, and lost an object separator. Should a response still fail to parse, `resolve_page_regions` treats it exactly like the raising failure path — `REGION_CLASSIFY_PARSE_FAILURE`, whole page detected, **no cache write**: an all-`unclassified` region list reads downstream as "no floor plan" (Rule 1) and skips detection, so caching one would make a one-off flake permanent until the next `--refresh-regions`. A *partial* response (`REGION_CLASSIFY_INCOMPLETE` — some regions unaddressed or type-coerced) is real information and still caches.

## Pipeline architecture

`app.py` is a thin argparse shell; the real flow is in `pipeline.py::run_extract`, which loops pages and runs seven stages per page:

1. `extraction.extractor.extract_page` — PyMuPDF `get_drawings()` / `get_text("dict")` / `get_images()` / `get_ocgs()`. **All coordinates are normalized to 150-DPI pixel space via `SCALE = 150/72`** at extraction time. Downstream code (detection, renderer, Gemini bboxes) assumes pixel-space. Don't reintroduce point-space anywhere past `extraction/extractor.py` / `extraction/plumber.py`. The transform is `extractor.page_transform` — SCALE composed with the page's `/Rotate` — because `get_drawings()`/`get_text()` return UNROTATED mediabox coordinates while `page.rect` (the source of `width_px`/`height_px`) and the render both honour rotation; it is exactly `x * SCALE` when rotation is 0. Pen widths take the transform's scale only: a rotation does not change stroke width.
2. `extraction.renderer.render_page_png` — renders the page PNG at the same 150 DPI used for coordinate normalization, so heuristic bboxes overlay cleanly.
3. `layout.segment_page` + `gemini.classifier.classify_regions` — the page is
   split into drawing regions at its whitespace gutters (deterministic, from the
   vector ink's own coordinates), and one Gemini call classifies every region
   from a per-region crop. A page the cut cannot split at all is retried once
   with text spans excluded from the ink map (text bboxes bridge otherwise-
   generous gutters — measured on s15: 1 leaf with text, 8 regions without),
   and the resulting regions are grown to re-absorb nearby text so
   classification crops keep their captions (source: "paths-only"). Detection
   then runs ONCE over the union of the `floor_plan` regions, so elevations,
   location plans and title blocks never reach the detectors. Per-candidate
   Gemini validation was removed on
   2026-07-28 — see docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md.
   Orchestrated by `pipeline.resolve_page_regions`, which caches the classification
   (`gemini/region_cache.py`, keyed by page content AND the region geometry it was
   made against, so a change to `layout/` is a cache miss rather than a silent reuse
   of stale bboxes — `--refresh-regions` bypasses it) and writes `regions.json` +
   `region_crops/`. Filtering is suppressed (regions still recorded, whole page
   detected, `REGION_COVERAGE_TOO_LOW`) when the regions hold less than
   `REGION_MIN_COVERAGE_FRAC` (0.90) of the page's paths: `SEGMENT_MIN_REGION_SIDE_PX`
   discards small leaves and `filter_page_data` would then delete real drawing with
   them (measured across `plans/`: 0.65 on `s11`, 0.85 on `s16`, 0.89 on
   `s05`, 0.94–1.00 on every other sheet).
4. `extraction.plumber.extract_plumber_page` — pdfplumber cross-check (chars/lines/rects/curves/images/tables). `compare_counts` emits `PLUMBER_LARGE_DELTA` warnings when PyMuPDF vs pdfplumber geometry diverges >50%. Tables here feed schedule detection.
5. `detection.run_heuristics` (`detection/orchestrator.py`) — deterministic detection of doors / windows / rooms / labels / schedules, run once over the region-filtered page data from stage 3 (skipped entirely only when a split page has neither a `floor_plan` nor a `schedule_table` region; a schedule-only sheet still runs heuristics over an empty path set so `detect_schedules` can read the schedule). Doors and windows detect first; the internal wall-centerline network (`detection/walls.py::detect_wall_network`, never emitted as candidates) then cross-validates them and feeds `detection/rooms.py::detect_rooms`, which subtracts wall solids, face linework, and opening seals (wall-plane plugs at doors, bboxes at windows) from the page and emits the enclosed free-space components as room polygons. `--disable-rooms` / `--disable-windows` exist because each detector can dominate noise on different drawing styles. Pass a `DebugTraceCollector` (via `--debug`) to record per-primitive reasoning.
6. `pipeline.finalize_candidates` + `renderer.draw_overlay` — Gemini no longer votes on individual candidates, so `finalize_candidates` applies the `OFFLINE_MIN_CONFIDENCE` floors unconditionally: candidates below threshold move to `rejected` and are not promoted to entities. Room candidates bypass the floors — they are heuristic-only by design and always promoted, with the polygon in `Entity.attributes`. `draw_overlay` then draws entities, rejected candidates, and the page's region outlines onto the render. Between finalisation and the takeoff, `pipeline.resolve_room_labels` names each room from the text drawn in and within `ROOM_LABEL_BUFFER_PX` (40px) of its polygon — one text-only Gemini call per page, cached by page content + room geometry + prompt version (`gemini/room_label_cache.py`). A returned name is kept only when every word of it appears in that room's own spans (`room_labeler.is_grounded`), so a name is read off the drawing or the room stays unnamed. Labels never feed the quantity maths.

   After finalisation, `takeoff.compute_takeoff` converts each room polygon
   (buffered out by `ROOM_WALL_DILATE_PX` to undo the barrier standoff) into
   metres at 0.16933 mm/px × the room's denominator (its floor_plan region's
   scale; a region the resolver marked unresolved leaves its rooms UNSCALED —
   the detection scale is borrowed only by rooms in no region / no verdict,
   never across plans on a mixed-scale sheet; else no numbers +
   `TAKEOFF_NO_SCALE`),
   assigns door/window entities to the rooms whose grown polygon touches them
   (widths from `opening_line` / `opening_width_px` / `opening_span_px`, bbox
   edge as last resort), and writes `takeoff.json`; the block is mirrored onto
   the room entity's `attributes["takeoff"]` and totals into `summary.json`.
   `scale.verified` is true for viewport/user scales, or text scales whose
   title-block sheet size matches the mediabox; `SCALE_UNVERIFIED` /
   `SCALE_PRINT_RESIZED` flag the rest. Then `takeoff/plausibility.py` reads
   the drawing itself (one verdict per denominator in use on the page, on
   `scale.plausibility`): ticked dimension lines with a numeric label beside
   them (`3600`, `7,434`, `4.50`; ≥ 3 matches, reusing
   `walls._dimension_line_indices`) measure the scale directly — agreement
   within 5 % verifies even a text-only scale, disagreement past 15 % is
   `SCALE_IMPLAUSIBLE` and unverifies even a typed one (s01: typed 1:50, 31
   dimensions say 1:92.2); otherwise the median door leaf (arc radius / pair
   chord ÷ 2 / panel length, ≥ 2 doors) must fall in 0.55–1.20 m (corpus
   medians 0.64–0.90; s01 0.38) or the verdict is implausible with the
   print-factor correction (×0.25/0.5/2/4) named. Numbers are NEVER swapped —
   the verdict only gates `verified`. Heights: flag → tty prompt → default.

   `takeoff/document.py` then serialises the page into `takeoff.json`. Rooms and
   openings are sibling arrays cross-referenced by id rather than openings nested
   per room, so a door serving two rooms is one record carrying both `room_ids`.
   Geometry is 150-DPI pixels — the same space as `final_entities.json` and
   `render.png` — with a `page_frame` block recording it; `extractor.page_transform`
   has already applied the page's `/Rotate`, so `rotation` is provenance and a
   consumer must not re-apply it. A room whose scale did not resolve is kept, with
   its polygon, `scale: null` and `quantities: null`.
7. JSON dump (`primitives.json`, `candidates.json`, `final_entities.json`, `pdfplumber_comparison.json`) and warning collection.

Aggregate `summary.json` and `warnings.json` are written at the run root once all pages finish.

## Output layout

```
outputs/<YYYY-MM-DD_HH-MM-SS>/
├── summary.json              # per-page summaries + totals + PDF metadata
├── warnings.json             # flat list across all pages
└── pages/page_NN/
    ├── render.png            # 150 DPI render
    ├── page.svg              # --svg only: MuPDF vector redraw, same 150-DPI frame
    ├── overlay.png           # entities + rejected + region outlines drawn on render
    ├── primitives.json       # raw PyMuPDF paths/text/images
    ├── pdfplumber_comparison.json
    ├── regions.json          # segmented regions + their Gemini classification
    ├── region_crops/         # classification-call only: per-region PNG crops sent to
    │                         # Gemini (absent on a cache hit, --no-gemini, or a raster page)
    ├── candidates.json       # heuristic output
    ├── final_entities.json   # finalized entities + rejected
    ├── takeoff.json          # THE overlay document: page_frame (150-DPI px space),
    │                         # scale + evidence, heights, rooms[] (polygon, bbox,
    │                         # label, opening_ids, quantities), openings[] (bbox,
    │                         # type, tag, room_ids, widths), totals, warnings.
    │                         # schema_version 1. Rooms and openings are sibling
    │                         # arrays cross-referenced by id — one physical opening
    │                         # is one record, whichever rooms it serves.
    ├── debug_trace.json      # --debug only: per-primitive detection trace
    └── debug_viewer.html     # --debug only: self-contained trace viewer
```

## Data model

All shared types live in `models.py` as `@dataclass`es: `PathPrimitive`, `TextSpan`, `ImageRef`, `PageData`, `Candidate`, `Entity`. `BBox` is a `(x0, y0, x1, y1)` tuple in **150-DPI pixels, top-left origin, y-down**. Page numbers in serialized output are **1-based**; `page_indices` passed between functions are **0-based**.

Notable extractor behavior: `extract_paths` explodes each `get_drawings()` entry into one `PathPrimitive` per atomic item (`l`/`c`/`re`/`qu`). Heuristics rely on `points[0]` / `points[-1]` being meaningful, so do not re-bundle multi-item drawings.

## Warning codes

Warnings are structured dicts with `warning_code`, `severity`, `message`,
`page_number`. The set is intentionally small — when adding a new warning,
follow the existing `SCREAMING_SNAKE_CASE` convention and emit from
`pipeline.collect_warnings`, `extraction.plumber.compare_counts`,
`gemini.client._validate_response`, `scale.resolver.resolve_page_scales`
(which returns them on `PageScales.warnings` for `run_extract` to fold into
the page's warning list — only the resolver knows which tier resolved a
region, so only it can say why one did not), or
`takeoff.quantities.compute_takeoff` (same shape, on `TakeoffPage.warnings`:
`TAKEOFF_NO_SCALE` — a room with no resolvable drawing scale gets no
quantities; `SCALE_UNVERIFIED` — a measured room's scale is text-only and
untied to a viewport/user source or a sheet-size confirmation;
`SCALE_PRINT_RESIZED` — the declared title-block sheet size mismatches the
mediabox by ~2× (half-/double-size print); `TAKEOFF_OPENING_TALLER_THAN_CEILING`
— an opening height was clamped to the ceiling; `TAKEOFF_OPENING_MULTI_ROOM`
— an opening reached 3+ rooms and was capped to the two nearest;
`SCALE_IMPLAUSIBLE` — the drawing's dimension strings or door-leaf widths
contradict the resolved scale, `verified` is false, numbers unchanged), or
`pipeline.resolve_room_labels` (`ROOM_LABEL_NO_GEMINI` — no cached labels
and Gemini disabled/unavailable, rooms stay unnamed; `ROOM_LABEL_FAILED` —
the labelling call raised (auth, network, bug); `ROOM_LABEL_PARSE_FAILURE` —
a response that didn't parse, not cached, same reasoning as
`REGION_CLASSIFY_PARSE_FAILURE`; `ROOM_LABEL_UNGROUNDED` — a returned name
failed the grounding check and was dropped; `ROOM_LABEL_CACHE_WRITE_FAILED`
— labelling succeeded but the cache write failed, so the next run calls
Gemini again).

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).


# Other rules

- Never add co authered by claude to the git commit
