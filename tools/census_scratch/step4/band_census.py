"""Step 4 census — WALL_MAX_THICKNESS_PX 36 -> 40 AS IMPLEMENTED, every sheet
at its own factor.

Per page, the stage-5 chain runs twice through the census harness (taps on,
network kept): at cap x1.0 and at cap x40/36 (H.overrides mult, so every use
of the cap scales — pairing, the thick tier's lower bound, stair-zone
anchoring, lattice pitch, band pockets, ring sizes). Reported:

  (a) the CANDIDATE population: every strong pair the base run would form
      with the caps 4x wider whose spacing lies in (36f, 40f] — the
      harness's wide_pairs tap, with the pipeline's exact material and
      through-hatch verdicts;
  (b) the ADMITTED set: final network segments present only at x1.111
      (and any lost only at x1.111);
  (c) the ROOM delta: entities gone / new, polygon IoU moves, and the
      ground-truth score (lost / returned FP / unreviewed) at both caps.

Usage: .venv/bin/python tools/census_scratch/step4/band_census.py [slugs...]
Writes step4/band_census.json (one record per page) beside this file.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

import os  # noqa: E402

# BAND_CENSUS_OUT lets two jobs (heavy / light sheets) run at once without
# racing on one file; merge the JSONs afterwards.
OUT = Path(os.environ.get("BAND_CENSUS_OUT",
                          Path(__file__).resolve().parent / "band_census.json"))
MULT = 40.0 / 36.0


def _seg_rec(s):
    p1, p2 = s.p1, s.p2
    return {
        "p1": [round(p1[0], 2), round(p1[1], 2)], "p2": [round(p2[0], 2), round(p2[1], 2)],
        "mid": [round((p1[0] + p2[0]) / 2, 1), round((p1[1] + p2[1]) / 2, 1)],
        # WallSegment (the public dataclass): thickness_px, source,
        # face_path_indices, stroked — no weak/thick flags survive the merge.
        "th": round(float(getattr(s, "thickness_px", getattr(s, "thickness", 0.0))), 2),
        "len": round(math.hypot(p2[0] - p1[0], p2[1] - p1[1]), 1),
        "stroked": bool(getattr(s, "stroked", False)),
        "source": getattr(s, "source", None),
        "faces": sorted(getattr(s, "face_path_indices", []) or [])[:12],
    }


def _match(a, b):
    return (abs(a["mid"][0] - b["mid"][0]) <= 2.0 and abs(a["mid"][1] - b["mid"][1]) <= 2.0
            and abs(a["th"] - b["th"]) <= 0.6 and abs(a["len"] - b["len"]) <= 4.0)


def _seg_diff(base, after):
    used = set()
    new = []
    for s in after:
        hit = None
        for i, b in enumerate(base):
            if i in used:
                continue
            if _match(s, b):
                hit = i
                break
        if hit is None:
            new.append(s)
        else:
            used.add(hit)
    lost = [b for i, b in enumerate(base) if i not in used]
    return new, lost


def _rooms(ents):
    out = []
    for e in ents:
        if e["entity_type"] != "room":
            continue
        poly = Polygon(e["evidence"]["polygon"]).buffer(0)
        out.append({"bbox": [round(v) for v in e["bbox"]], "conf": e["confidence"],
                    "poly": poly, "doors": e["evidence"].get("door_openings"),
                    "windows": e["evidence"].get("window_openings")})
    return out


def _room_diff(base, after):
    used = set()
    moved, gone = [], []
    for b in base:
        best, best_iou = None, 0.0
        for i, a in enumerate(after):
            if i in used:
                continue
            u = b["poly"].union(a["poly"]).area
            iou = b["poly"].intersection(a["poly"]).area / u if u else 0.0
            if iou > best_iou:
                best, best_iou = i, iou
        if best is None or best_iou < 0.5:
            gone.append({"bbox": b["bbox"], "area": round(b["poly"].area)})
            continue
        used.add(best)
        a = after[best]
        if best_iou < 0.9995:
            lost = b["poly"].difference(a["poly"]).area
            gained = a["poly"].difference(b["poly"]).area
            moved.append({"bbox": b["bbox"], "after_bbox": a["bbox"], "iou": round(best_iou, 4),
                          "lost": round(lost), "gained": round(gained)})
    new = [{"bbox": a["bbox"], "area": round(a["poly"].area), "conf": a["conf"],
            "doors": a["doors"], "windows": a["windows"]}
           for i, a in enumerate(after) if i not in used]
    return moved, gone, new


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        lo, hi = 36.0 * f, 40.0 * f
        taps = H.Taps()
        ents, extras = H.run(p, taps=taps, keep_network=True)
        base_segs = [_seg_rec(s) for s in extras["network"].segments]
        cands = [w for w in taps.wide_pairs if lo < w["th"] <= hi + 1e-6]
        with H.overrides(mult={"WALL_MAX_THICKNESS_PX": MULT}):
            taps2 = H.Taps()
            ents2, extras2 = H.run(p, taps=taps2, keep_network=True)
        after_segs = [_seg_rec(s) for s in extras2["network"].segments]
        new, lost = _seg_diff(base_segs, after_segs)
        moved, gone, added = _room_diff(_rooms(ents), _rooms(ents2))
        sc, sc2 = H.score(slug, p.page_number, ents), H.score(slug, p.page_number, ents2)
        rec = {
            "slug": slug, "page": p.page_number, "factor": round(f, 4),
            "band_px": [round(lo, 2), round(hi, 2)],
            "candidates": [{k: (round(v, 2) if isinstance(v, float) else v)
                            for k, v in w.items() if k != "mid"} | {"mid": [round(w["mid"][0]), round(w["mid"][1])]}
                           for w in cands],
            "segments_new": new, "segments_lost": lost,
            "n_segments": [len(base_segs), len(after_segs)],
            "rooms_moved": moved, "rooms_gone": gone, "rooms_new": added,
            "score_base": {k: sc[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
            "score_after": {k: sc2[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
        }
        records.append(rec)
        print(f"{slug} p{p.page_number} f={f:.3f} band ({lo:.1f},{hi:.1f}]: "
              f"candidates {len(cands)} (material {sum(1 for c in cands if c['material'])}, "
              f"through {sum(1 for c in cands if c['through'])}) | segments +{len(new)} -{len(lost)} "
              f"| rooms moved {len(moved)} gone {len(gone)} new {len(added)} | "
              f"score base lost={len(sc['lost'])} fp={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])} "
              f"-> after lost={len(sc2['lost'])} fp={len(sc2['returned_fps'])} unrev={len(sc2['unreviewed'])}",
              flush=True)
        for s in new:
            print(f"    NEW seg th {s['th']} len {s['len']} at {s['mid']} stroked={s['stroked']} src={s['source']} faces={s['faces'][:6]}")
        for s in lost:
            print(f"    LOST seg th {s['th']} len {s['len']} at {s['mid']}")
        for r in gone:
            print(f"    room GONE {r['bbox']} area {r['area']}")
        for r in added:
            print(f"    room NEW {r['bbox']} area {r['area']} conf {r['conf']} doors {r['doors']} windows {r['windows']}")
        for r in moved:
            print(f"    room MOVED {r['bbox']} iou {r['iou']} lost {r['lost']} gained {r['gained']}")
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
