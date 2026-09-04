"""Per-constant ablations.

  python ablate.py s01 s01mode   # f=0.542 full, scale-one-alone, leave-one-out
  python ablate.py sNN mult      # each field x {0.5,0.67,0.8,1.25,1.5,2.0} at the sheet's own factor

Writes abl/<slug>_<mode>.jsonl, one line per config, incrementally.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import harness as H

OUT = Path(__file__).resolve().parent / "abl"
OUT.mkdir(exist_ok=True)

# class: W = length (x m), A = area (x m^2), D = density (/ m)
FIELDS = {
    "WALL_FACE_MIN_LEN_PX": "W", "WALL_MIN_THICKNESS_PX": "W",
    "WALL_MAX_THICKNESS_PX": "W", "WALL_THICK_MATERIAL_MAX_PX": "W",
    "WALL_THROUGH_HATCH_MAX_PX": "W", "WALL_PAIR_MIN_OVERLAP_PX": "W",
    "WALL_FILL_CLASS_MIN_INK_PX": "W", "WALL_FILL_BLOCK_MAX_SIDE_PX": "W",
    "WALL_WEAK_MIN_RUN_PX": "W", "WALL_JOINERY_BRIDGE_GAP_PX": "W",
    "WALL_HATCH_MAX_LEN_PX": "W", "WALL_WEAK_MATERIAL_PER_100PX": "D",
    "COLLINEAR_OFFSET_TOL": "W", "WALL_ANCHOR_SUPPORT_REACH_PX": "W",
    "ROOM_MIN_AREA_PX2": "A", "ROOM_BLIND_WINDOW_MAX_AREA_PX2": "A",
    "ROOM_OPENING_SEAL_PX": "W", "ROOM_PLUG_ANCHOR_WIN_PX": "W",
    "ROOM_PLUG_HALF_WIDTH_PX": "W", "ROOM_FOLD_STACK_NEAR_PX": "W",
    "ROOM_FOLD_JAMB_MIN_LEN_PX": "W",
    "DOOR_MIN_SIZE_PX": "W", "DOOR_MAX_SIZE_PX": "W", "DOOR_SWING_LINE_DIST_PX": "W",
    "DOOR_POLYLINE_MAX_SEG_PX": "W", "DOOR_ASSEMBLY_CONNECT_TOL_PX": "W",
    "DOOR_LEAF_LINE_ENDPOINT_TOL_PX": "W", "DOOR_THRESHOLD_ENDPOINT_TOL_PX": "W",
    "DOOR_DOUBLE_LEAF_GAP_PX": "W", "DOOR_DOUBLE_LEAF_OVERLAP_PX": "W",
    "DOOR_DOUBLE_LEAF_CENTER_TOL_PX": "W", "DOOR_SLIDE_PANEL_MIN_THICKNESS_PX": "W",
    "DOOR_SLIDE_PANEL_MAX_THICKNESS_PX": "W", "DOOR_SLIDE_FLANK_GAP_MIN_PX": "W",
    "DOOR_SLIDE_FLANK_GAP_MAX_PX": "W", "DOOR_SLIDE_POCKET_TIGHT_GAP_PX": "W",
    "DOOR_SLIDE_PARK_GAP_MAX_PX": "W", "DOOR_SLIDE_PARK_BAND_MIN_TH_PX": "W",
    "DOOR_SLIDE_PARK_BAND_MAX_TH_PX": "W", "DOOR_SLIDE_PARK_JAMB_TOL_PX": "W",
    "DOOR_FOLD_JAMB_ANCHOR_TOL_PX": "W", "DOOR_FOLD_JAMB_LINE_MIN_LEN_PX": "W",
    "DOOR_FOLD_OPEN_CORRIDOR_HALF_W_PX": "W",
    "WINDOW_MIN_WIDTH_PX": "W",
    "CROSS_WALL_EXPAND_PX": "W", "CROSS_OPENING_ENDPOINT_TOL_PX": "W",
    "CROSS_WALL_RUNS_THROUGH_MARGIN_PX": "W", "CROSS_WALL_RUNS_THROUGH_BAND_PX": "W",
    "CROSS_DOOR_EXPAND_PX": "W", "CROSS_DOOR_FALLBACK_EXPAND_PX": "W",
}
GROUPS = {
    "CAPS3": ["WALL_MAX_THICKNESS_PX", "WALL_THICK_MATERIAL_MAX_PX", "WALL_THROUGH_HATCH_MAX_PX"],
}


def mult_for(field, m):
    c = FIELDS[field]
    return m if c == "W" else (m * m if c == "A" else 1.0 / m)


def run_cfg(pages, slug, base, factor, mult):
    t0 = time.time()
    out = []
    try:
        with H.overrides(mult=mult):
            for p in pages:
                ents, _ = H.run(p, factor=factor)
                sc = H.score(slug, p.page_number, ents)
                dv = H.diff_vs_baseline(base[p.page_number], ents)
                out.append({"page": p.page_number, "score": sc, "vs_base": dv,
                            "n": {t: sum(1 for e in ents if e["entity_type"] == t) for t in ("door", "window", "room")}})
    except AssertionError as ex:
        return {"error": "ordering-assert: %s" % ex, "secs": time.time() - t0}
    return {"pages": out, "secs": time.time() - t0}


def main(slug, mode):
    pages = H.load(slug)
    base = {}
    for p in pages:
        ents, _ = H.run(p)
        base[p.page_number] = ents
    fn = OUT / f"{slug}_{mode}.jsonl"
    done = set()
    if fn.exists():
        for line in fn.read_text().splitlines():
            done.add(json.loads(line)["label"])
    f = fn.open("a")

    def emit(label, factor, mult):
        if label in done:
            return
        r = run_cfg(pages, slug, base, factor, mult)
        r["label"] = label
        r["factor"] = factor
        r["mult"] = mult
        f.write(json.dumps(r) + "\n")
        f.flush()
        pg = r.get("pages")
        if pg:
            s = pg[0]["score"]
            print(label, "lost", len(s["lost"]), "retFP", len(s["returned_fps"]), "unrev", len(s["unreviewed"]),
                  "vs_base gone", len(pg[0]["vs_base"]["gone"]), "new", len(pg[0]["vs_base"]["new"]),
                  "%.0fs" % r["secs"], flush=True)
        else:
            print(label, r.get("error"), flush=True)

    if mode == "s01mode":
        f542 = 50.0 / 92.2
        emit("baseline_f1", None, {})
        emit("full_f0.542", f542, {})
        for fld in FIELDS:
            emit(f"only:{fld}", None, {fld: mult_for(fld, f542)})
        for g, members in GROUPS.items():
            emit(f"only:{g}", None, {m: mult_for(m, f542) for m in members})
        for fld in FIELDS:
            emit(f"loo:{fld}", f542, {fld: 1.0 / mult_for(fld, f542)})
        for g, members in GROUPS.items():
            emit(f"loo:{g}", f542, {m: 1.0 / mult_for(m, f542) for m in members})
    elif mode == "mult":
        emit("baseline", None, {})
        for m in (0.5, 0.67, 0.8, 1.25, 1.5, 2.0):
            for fld in FIELDS:
                emit(f"{fld}@{m}", None, {fld: mult_for(fld, m)})
            for g, members in GROUPS.items():
                emit(f"{g}@{m}", None, {x: mult_for(x, m) for x in members})
    elif mode == "mult_key":
        KEY = {
            "CAPS3": (0.8, 1.25, 1.5), "WALL_FACE_MIN_LEN_PX": (0.67, 1.5),
            "WALL_WEAK_MATERIAL_PER_100PX": (0.67, 1.5), "WALL_HATCH_MAX_LEN_PX": (0.67, 1.5),
            "ROOM_MIN_AREA_PX2": (0.5, 2.0), "ROOM_BLIND_WINDOW_MAX_AREA_PX2": (0.5, 2.0),
            "ROOM_OPENING_SEAL_PX": (0.67, 1.5), "WINDOW_MIN_WIDTH_PX": (0.67, 1.5),
            "CROSS_WALL_EXPAND_PX": (0.67, 1.5), "WALL_ANCHOR_SUPPORT_REACH_PX": (0.5, 2.0),
            "COLLINEAR_OFFSET_TOL": (0.5, 2.0), "WALL_WEAK_MIN_RUN_PX": (0.67, 1.5),
            "WALL_PAIR_MIN_OVERLAP_PX": (0.67, 1.5), "ROOM_PLUG_HALF_WIDTH_PX": (0.67, 1.5),
            "DOOR_MIN_SIZE_PX": (0.67, 1.5), "DOOR_MAX_SIZE_PX": (0.67, 1.5),
            "CROSS_DOOR_EXPAND_PX": (0.5, 2.0),
        }
        emit("baseline", None, {})
        for fld, ms in KEY.items():
            for m in ms:
                if fld in GROUPS:
                    emit(f"{fld}@{m}", None, {x: mult_for(x, m) for x in GROUPS[fld]})
                else:
                    emit(f"{fld}@{m}", None, {fld: mult_for(fld, m)})
    elif mode == "mult_fast":
        # only the wall/room/window/cross fields (door fields separately)
        emit("baseline", None, {})
        for m in (0.5, 0.67, 0.8, 1.25, 1.5, 2.0):
            for fld in FIELDS:
                if fld.startswith("DOOR_"):
                    continue
                emit(f"{fld}@{m}", None, {fld: mult_for(fld, m)})
            for g, members in GROUPS.items():
                emit(f"{g}@{m}", None, {x: mult_for(x, m) for x in members})
    f.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
