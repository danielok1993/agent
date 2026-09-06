# step 11 scratch tooling (W-gate iteration 3, 2026-09-05)

The wall-pen census behind `docs/w-gate-iter3-checkpoints/step-11.md`. All
run from the repo root with `.venv/bin/python tools/census_scratch/step11/<script>`,
import `step9/s01_common.py` (`run_tapped`: the stage-5 chain with the room
stage's final plugs tapped per door) and the harness cache under
`tools/census_scratch/cache/`. Nothing here is part of the pipeline.

| script | what it measures | output kept beside it |
|---|---|---|
| `pen_census.py [slug[@factor] ...]` | per stroke pen: paired share, same-pen segments (thickness distribution, `_band_has_wall_material` share, longest), lone-eligible ink, hatch-like ink, loops closed alone, and the LOOSE opening test (the pen's ink touches a plug tail / a window end zone) | `pen_census_out.txt`, `pen_census.json` |
| `render_pens.py slug ...` | each pen's faces coloured over the sweep's render (scratchpad only — s02's render carries the title block) | — |
| `jamb_pens.py [-v]` | strict form: faces COLLINEAR with a plugged edge ending at its jambs (0, 1 or 2 sides), windows likewise | `jamb_pens_out.txt`, `jamb_pens.json` |
| `tail_pens.py [-v]` | per interrupted doorway plug and pen: E (a face endpoint in the tail) / S (same-pen band) / x (crossing) at each tail | `tail_pens_out.txt` |
| `tail_pens2.py [-v]` | the same with C (collinear end) / S (paired or band) / P (lone perpendicular end) / x, under FINAL plugs and under every-pen-as-wall-pen material | `tail_pens2_out.txt`, `tail_pens2.json` |
| `rule_census.py [slug[@factor] ...]` | the rule as it was to be implemented, all 20 sheets: today's share-gated pens, owners per variant (a only / a+b / a+b_tip), whether the set changes | `rule_census_out.txt`, `rule_census.json` |
| `implemented_census.py [slug[@factor] ...]` | the SHIPPED `rooms._doorway_pens` on the room stage's own pass-1 plugs, all 20 sheets: owners, vetoed pens, and the same with the lone-collinear clause off | `implemented_census_out.txt` |
| `crop_step11.py` (under `__main__`) | the two step-11 PNGs (share gate alone vs the veto at s01's true factor; the old rule = `_doorway_pens` patched to name nobody) | `docs/w-gate-iter3-checkpoints/step11_*.png` |
