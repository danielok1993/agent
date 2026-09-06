"""Step 14 — the entrance-RUN gate (ROOM_ENTRANCE_MIN_RUN_PX, `_entrance_run`)
censused AS IMPLEMENTED on all 20 sheets at their factors.

Two runs of the stage-5 chain per page through the harness:

* OFF — `H.overrides(mult={"ROOM_ENTRANCE_MIN_RUN_PX": -1.0})`: the floor is
  -29.5 x f, below any in-contact run (>= -2 x ROOM_CONTACT_TOL_PX = -8px for
  every f > 0.27; the corpus's smallest is s13's 0.367, asserted below), so
  every seal within the contact tolerance counts — the any-touch test the
  tree read until this step, exactly. Out-of-contact seals read -inf and
  never count under either.
* ON — the tree as it stands.

For every room the OFF run EMITS (read off detect_rooms' own locals through
the free-space tap, as step 13's entered_census did: `face_lines`,
`door_barriers`; the rooms list off the `_drop_window_exterior_sides` tap):
the any-touch entrance count, the run-gated count, per touching seal its raw
contact (boundary length within the tolerance of the seal), its run
(`_entrance_run`), whether it lies along or across the room's long axis, the
room's largest run in px and in world mm (harness TRUE_SCALE), the door /
window counts, the ground-truth class — and its FATE under ON (present /
gone, by bbox IoU >= 0.5 against the ON run's rooms). Then both runs scored
against the truth and diffed (gone / new / moved polygons).

Usage: .venv/bin/python tools/census_scratch/step14/entrance_census.py [slugs...]
Writes step14/entrance_census.json (ENTRANCE_CENSUS_OUT to run two jobs).
"""
from __future__ import annotations

import json
import math
import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

from detection import rooms  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("ENTRANCE_CENSUS_OUT",
                          Path(__file__).resolve().parent / "entrance_census.json"))
TOL = rooms.ROOM_CONTACT_TOL_PX


def _mrr_axis(poly):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rect = poly.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        return None, None, None
    c = list(rect.exterior.coords)[:4]
    edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    lens = [_line_length(a, b) for a, b in edges]
    if lens[0] >= lens[1]:
        return _line_angle_deg(*edges[0]), lens[1], lens[0]
    return _line_angle_deg(*edges[1]), lens[0], lens[1]


def _gt_class(slug, page_number, bbox):
    truth = load_truth(slug).page(page_number)
    best = ("unmatched", 0.0, "")
    for cls, items in (("confirmed", truth.confirmed),
                       ("false_positive", truth.false_positives),
                       ("deferred", truth.deferred)):
        for t in items:
            if t.type != "room":
                continue
            v = iou(tuple(bbox), tuple(t.bbox))
            if v >= 0.5 and v > best[1]:
                best = (cls, v, t.note or "")
    return best


def _chain(p, gate_off: bool):
    """Run the chain; return (ents, captured locals)."""
    captured = {}
    o_fsc, o_drop = rooms._free_space_components, rooms._drop_window_exterior_sides

    def fsc(page, barriers):
        loc = sys._getframe(1).f_locals
        captured["face_lines"] = list(loc["face_lines"])
        captured["door_barriers"] = list(loc["door_barriers"])
        return o_fsc(page, barriers)

    def drop(rooms_list, windows, **k):
        captured["rooms"] = list(rooms_list)
        return o_drop(rooms_list, windows, **k)

    rooms._free_space_components, rooms._drop_window_exterior_sides = fsc, drop
    try:
        if gate_off:
            with H.overrides(mult={"ROOM_ENTRANCE_MIN_RUN_PX": -1.0}):
                ents, extras = H.run(p)
        else:
            ents, extras = H.run(p)
    finally:
        rooms._free_space_components, rooms._drop_window_exterior_sides = o_fsc, o_drop
    return ents, extras, captured


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        rg = rooms.RoomGates.at(f)
        floor = rg.ROOM_ENTRANCE_MIN_RUN_PX
        assert -floor < -2.0 * TOL, (slug, f, floor)   # OFF is provably any-touch here

        ents_off, _, cap_off = _chain(p, gate_off=True)
        ents_on, _, cap_on = _chain(p, gate_off=False)
        rooms_on = [poly for poly, _ in cap_on.get("rooms", [])]
        emitted_on = [tuple(e["bbox"]) for e in ents_on if e["entity_type"] == "room"]
        emitted_off = [tuple(e["bbox"]) for e in ents_off if e["entity_type"] == "room"]

        entrance = [(conf, g) for conf, g in cap_off.get("door_barriers", [])
                    if conf >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE]
        out_rooms = []
        for poly, info in cap_off.get("rooms", []):
            boundary = poly.exterior
            axis, short, long = _mrr_axis(poly)
            seals = []
            for conf, g in entrance:
                run = rooms._entrance_run(boundary, g)
                if run == -math.inf:
                    continue
                g_axis, _, _ = _mrr_axis(g)
                rel = None if (g_axis is None or axis is None) else _angle_diff_mod180(g_axis, axis)
                seals.append({
                    "conf": conf,
                    "contact_px": round(run + 2.0 * TOL, 1),
                    "run_px": round(run, 1),
                    "counts": run >= floor,
                    "seal_bbox": [round(v, 1) for v in g.bounds],
                    "seal_axis_vs_room": None if rel is None else round(rel, 1),
                    "meets": None if rel is None else ("along" if rel < 45.0 else "across"),
                })
            b = [round(v, 1) for v in poly.bounds]
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            max_run = max([s["run_px"] for s in seals], default=None)
            old_count = len(seals)
            new_count = sum(1 for s in seals if s["counts"])
            # fate under ON: still among the rooms detect_rooms keeps?
            fate = "present" if any(iou(tuple(b), tuple(q.bounds)) >= 0.5 for q in rooms_on) else "gone"
            emitted = any(iou(tuple(b), tuple(q)) >= 0.5 for q in emitted_off)
            cls, v, note = _gt_class(slug, p.page_number, b)
            mm_true = None if max_run is None else H.mm(slug, max_run, cx, cy)
            out_rooms.append({
                "bbox": b, "area": round(poly.area), "short": None if short is None else round(short, 2),
                "old_entrance_count": old_count, "new_entrance_count": new_count,
                "status_flip": old_count > 0 and new_count == 0,
                "max_run_px": max_run,
                "max_run_mm_true": None if mm_true is None else round(mm_true),
                "max_run_mm_at_factor": None if max_run is None else round(max_run * H.MM_PER_PX_AT_1 * 50.0 / f),
                "door_count": info["door_count"], "window_count": info["window_count"],
                "emitted_off": emitted, "fate_on": fate,
                "text": rooms._contains_text(poly, p.page_data.text_spans),
                "gt": cls, "gt_iou": round(v, 3), "gt_note": note[:120],
                "seals": seals,
            })
        sc_off = H.score(slug, p.page_number, ents_off)
        sc_on = H.score(slug, p.page_number, ents_on)
        diff = H.diff_vs_baseline(ents_off, ents_on)
        records.append({
            "slug": slug, "page": p.page_number, "factor": round(f, 4), "floor_px": round(floor, 2),
            "n_rooms_off": len(cap_off.get("rooms", [])), "n_rooms_on": len(rooms_on),
            "n_emitted_off": len(emitted_off), "n_emitted_on": len(emitted_on),
            "score_off": sc_off, "score_on": sc_on, "diff_off_to_on": diff,
            "rooms": out_rooms,
        })
        flips = [r for r in out_rooms if r["status_flip"]]
        print(f"{slug} p{p.page_number} f={f:.3f} floor {floor:.1f}px: rooms OFF {len(cap_off.get('rooms', []))} "
              f"ON {len(rooms_on)}; status flips {len(flips)}; score OFF lost {len(sc_off['lost'])} "
              f"retFP {len(sc_off['returned_fps'])} unrev {len(sc_off['unreviewed'])} | ON lost {len(sc_on['lost'])} "
              f"retFP {len(sc_on['returned_fps'])} unrev {len(sc_on['unreviewed'])}; "
              f"diff gone {len(diff['gone'])} new {len(diff['new'])}", flush=True)
        for r in flips:
            print(f"    FLIP {r['bbox']} area {r['area']} gt={r['gt']} win {r['window_count']} doors {r['door_count']} "
                  f"max run {r['max_run_px']}px ({r['max_run_mm_true']}mm true) -> {r['fate_on']}")
            for s in r["seals"]:
                print(f"        seal {s['seal_bbox']} conf {s['conf']} contact {s['contact_px']} run {s['run_px']} {s['meets']}")
        # the true-class floor on this page
        conf_runs = sorted((r["max_run_px"], r["bbox"]) for r in out_rooms
                           if r["gt"] == "confirmed" and r["max_run_px"] is not None)
        if conf_runs:
            print(f"    confirmed entered rooms: n={len(conf_runs)} smallest max-run {conf_runs[0][0]}px at {conf_runs[0][1]} "
                  f"(floor {floor:.1f}, margin {conf_runs[0][0] / floor:.2f}x)")
    return records


if __name__ == "__main__":
    slugs = sys.argv[1:] or [f"s{i:02d}" for i in range(1, 21)]
    all_recs = []
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    keep = [r for r in existing if r["slug"] not in slugs]
    for slug in slugs:
        try:
            all_recs.extend(census(slug))
        except SystemExit as e:
            print(f"{slug}: skipped ({e})")
    OUT.write_text(json.dumps(keep + all_recs, indent=1, default=str))
    print("wrote", OUT)
