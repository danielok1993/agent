"""COLLINEAR_OFFSET_TOL forms, measured with the census harness on top of the
current tree:  current (4*f) | unscaled 4.0 | min(4.0, 6.0*f) | (s01 only) 4.1.
Scores vs truth and vs the sheet's own baseline (current form) per config."""
import sys

sys.path.insert(0, "/Users/danielszweda/Documents/GitHub/UD/agent/tools/census_scratch")
import harness as H  # noqa: E402

slug = sys.argv[1]
factor = float(sys.argv[2]) if len(sys.argv) > 2 else None
pages = H.load(slug)
page = pages[0]
f = page.scale_factor if factor is None else factor
forms = {
    "current 4f": 4.0 * f,
    "unscaled 4.0": 4.0,
    "min(4, 6f)": min(4.0, 6.0 * f),
}
if slug == "s01" and factor is not None:
    forms["4.1"] = 4.1

base_ents, _ = H.run(page)   # the sheet's own factor, current form
for name, val in forms.items():
    with H.overrides(absolute={"COLLINEAR_OFFSET_TOL": val}):
        ents, _ = H.run(page, factor=f)
    sc = H.score(slug, page.page_number, ents)
    dv = H.diff_vs_baseline(base_ents, ents)
    print(f"{slug} f={f:.3f} {name:14s} tol={val:.2f}  counts={sc['counts']} lost={len(sc['lost'])} "
          f"retFP={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])} | vs current-form run: gone={dv['gone']} new={dv['new']}",
          flush=True)
