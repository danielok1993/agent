"""The tabbed fixture (TestBandPocketTabbedByAPerpendicularBand) through the
stage with the recess census's readings: the components, which rule drops
the reveal, and every recess candidate's extent / runs numbers — with the
tab as drawn and with the inner face line drawn continuously (tab-less).

Usage: .venv/bin/python tools/census_scratch/step17/fixture_probe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tests"))

from shapely.geometry import box  # noqa: E402

import recess_census as RC  # noqa: E402
from detection import rooms  # noqa: E402
from detection import detect_wall_network  # noqa: E402
from detection.rooms import detect_rooms  # noqa: E402
from test_room_detection import (  # noqa: E402
    PAGE_W, PAGE_H, TestBandPocketTabbedByAPerpendicularBand as T, hline,
)


def run(paths, pocket_off=False, label=""):
    captured = {}
    calls = []
    pocket_calls = []
    o_fsc, o_recess, o_pocket = (rooms._free_space_components, rooms._is_wall_recess,
                                 rooms._is_band_pocket)

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        for k in ("face_lines", "cap_lines", "wall_segments", "solids"):
            captured[k] = loc[k]
        captured["opening_boxes"] = ([box(*c.bbox) for c in loc["doors"]]
                                     + [box(*c.bbox) for c in loc["windows"]])
        comps = o_fsc(page, barriers)
        captured["components"] = comps
        return comps

    def recess(comp, wall_segments, opening_boxes, text_spans):
        res = o_recess(comp, wall_segments, opening_boxes, text_spans)
        calls.append((comp, res))
        return res

    def pocket(comp, face_lines, text_spans, **kw):
        res = False if pocket_off else o_pocket(comp, face_lines, text_spans, **kw)
        pocket_calls.append((comp, res))
        return res

    rooms._free_space_components, rooms._is_wall_recess, rooms._is_band_pocket = fsc, recess, pocket
    try:
        network = detect_wall_network(paths, [])
        out = detect_rooms(network, [], [], PAGE_W, PAGE_H, [])
    finally:
        rooms._free_space_components, rooms._is_wall_recess, rooms._is_band_pocket = o_fsc, o_recess, o_pocket

    print(f"=== {label} (pocket rule {'OFF' if pocket_off else 'on'})")
    print("  segments:")
    for s in captured["wall_segments"]:
        print(f"    {tuple(round(v, 2) for v in s.p1)}-{tuple(round(v, 2) for v in s.p2)} th {s.thickness_px:.2f}")
    print("  components:", [[round(v, 1) for v in c.bounds] for c in captured["components"]])
    print("  rooms:", [r.bbox for r in out])
    for comp, res in calls:
        r = RC.readings(comp, captured["wall_segments"], captured["opening_boxes"], [],
                        captured["cap_lines"])
        print(f"  RECESS call {[round(v, 2) for v in comp.bounds]} -> {res}; verdicts {r['verdict']}")
        print(f"     polygon {[tuple(round(v, 2) for v in p) for p in comp.exterior.coords]}")
        for cd in r["candidates"]:
            print(f"     cand a {cd['a']} b {cd['b']} th {cd['th']} gap {cd['gap']} own {cd['own']} "
                  f"gap_cover {cd['gap_cover']} depth {cd['depth_bands']}x back {cd['back']} ext_ok {cd['extent_ok']} | "
                  + " ".join(f"{k} {cd[k]}" for k in RC.VARIANTS))
            for sk, sd in cd["sides"].items():
                for rr in sd["runs"]:
                    print(f"        side {sk} run {rr['run']} w {rr['w']} t {rr['t']} face={rr['on_face']} cap={rr['on_cap']}")
    for comp, res in pocket_calls:
        print(f"  POCKET call {[round(v, 2) for v in comp.bounds]} -> {res}")


def main():
    t = T()
    tabbed = t._plan()
    # Tab-less: the inner face line drawn continuously across the junction
    # (path 5 from the partition's NEAR face on), everything else as drawn.
    tabless = [p for p in tabbed if p.path_index != 5] + [hline(5, t.PART0, 600.0, t.INNER)]
    tabless.sort(key=lambda p: p.path_index)
    run(tabbed, False, "tabbed fixture as drawn")
    run(tabbed, True, "tabbed fixture")
    run(tabless, False, "tab-less fixture as drawn")
    run(tabless, True, "tab-less fixture")


if __name__ == "__main__":
    main()
