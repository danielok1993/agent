"""Step 13 census — `_is_band_pocket`'s spacing ceiling, WALL_MAX_THICKNESS_PX
-> WALL_THICK_MATERIAL_MAX_PX, AS IMPLEMENTED on every sheet at its own factor.

Per page the stage-5 chain runs through the census harness with a tap on
rooms._is_band_pocket that records EVERY call — i.e. every entrance-less,
window-less free-space component that survived the area / border / hole /
erosion / contact / mass filters and the recess rule (detect_rooms calls the
pocket rule on nothing else) — with the features the rule reads, replicated
with the rule's own helpers on the pipeline's exact inputs:

  text      rooms._contains_text (vetoes the rule)
  short     the minimum rotated rectangle's short side; spacing = short +
            2 * ROOM_LINE_BARRIER_PX is the distance between the two faces
  cover_lo  rooms._edge_face_cover on each long edge against the exact
  cover_hi  face_lines list (barrier-face extents + both flanks of every
            paired segment); the rule wants both >= ROOM_BAND_POCKET_FACE_COVER_MIN

and the verdict at the current ceiling (the scaled cap) and what it would be
at the thick ceiling (the scaled WALL_THICK_MATERIAL_MAX_PX). The chain then
runs a second time with the ceiling raised for this rule only (the same
function, handed a gates object whose WALL_MAX_THICKNESS_PX is the thick
cap — nothing else in the room stage sees the change) and the two entity
lists are diffed and scored against ground truth. Every recorded component
is classed by bbox IoU >= 0.5 against the page's confirmed / false-positive /
deferred rooms, so the false side (a REAL door-less, window-less space that
narrow) is measured on the same population the rule would drop.

Usage: .venv/bin/python tools/census_scratch/step13/pocket_census.py [slugs...]
Writes step13/pocket_census.json beside this file (POCKET_CENSUS_OUT to
run two jobs at once).
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

from detection import rooms, walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("POCKET_CENSUS_OUT",
                          Path(__file__).resolve().parent / "pocket_census.json"))
COVER_MIN = rooms.ROOM_BAND_POCKET_FACE_COVER_MIN
STANDOFF = 2.0 * rooms.ROOM_LINE_BARRIER_PX


def _features(comp, face_lines, text_spans):
    """The rule's own reading of one component."""
    rec = {"text": rooms._contains_text(comp, text_spans)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rect = comp.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        rec.update(short=None, long=None, covers=None, degenerate=True)
        return rec
    c = list(rect.exterior.coords)[:4]
    edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    lens = [_line_length(a, b) for a, b in edges]
    if lens[0] >= lens[1]:
        long_edges, short, long = (edges[0], edges[2]), lens[1], lens[0]
    else:
        long_edges, short, long = (edges[1], edges[3]), lens[0], lens[1]
    covers = sorted(rooms._edge_face_cover(e, face_lines) for e in long_edges)
    rec.update(
        short=short, long=long, spacing=short + STANDOFF, covers=covers,
        degenerate=False, axis_deg=round(_line_angle_deg(*long_edges[0]), 1),
        mrr=[[round(x, 1), round(y, 1)] for x, y in c],
    )
    return rec


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


def _rooms(ents):
    out = []
    for e in ents:
        if e["entity_type"] != "room":
            continue
        out.append({"bbox": [round(v) for v in e["bbox"]], "conf": e["confidence"],
                    "poly": Polygon(e["evidence"]["polygon"]).buffer(0),
                    "doors": e["evidence"].get("door_openings"),
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
            v = b["poly"].intersection(a["poly"]).area / u if u else 0.0
            if v > best_iou:
                best, best_iou = i, v
        if best is None or best_iou < 0.5:
            gone.append({"bbox": b["bbox"], "area": round(b["poly"].area), "conf": b["conf"]})
            continue
        used.add(best)
        a = after[best]
        if best_iou < 0.9995:
            moved.append({"bbox": b["bbox"], "after_bbox": a["bbox"], "iou": round(best_iou, 4),
                          "lost": round(b["poly"].difference(a["poly"]).area),
                          "gained": round(a["poly"].difference(b["poly"]).area)})
    new = [{"bbox": a["bbox"], "area": round(a["poly"].area), "conf": a["conf"]}
           for i, a in enumerate(after) if i not in used]
    return moved, gone, new


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        wg = walls.WallGates.at(f)
        cap, thick = wg.WALL_MAX_THICKNESS_PX, wg.WALL_THICK_MATERIAL_MAX_PX
        calls = []
        orig = rooms._is_band_pocket

        def tap(comp, face_lines, text_spans, *, gates=rooms.ROOM_GATES_UNSCALED):
            res = orig(comp, face_lines, text_spans, gates=gates)
            rec = _features(comp, face_lines, text_spans)
            b = comp.bounds
            rec.update(
                bbox=[round(v, 1) for v in b], area=round(comp.area),
                res_cap=bool(res), n_faces=len(face_lines),
            )
            calls.append(rec)
            return res

        rooms._is_band_pocket = tap
        try:
            ents, _ = H.run(p)
        finally:
            rooms._is_band_pocket = orig

        def raised(comp, face_lines, text_spans, *, gates=rooms.ROOM_GATES_UNSCALED):
            g2 = dataclasses.replace(
                gates,
                WALL_MAX_THICKNESS_PX=walls.WallGates.at(gates.factor).WALL_THICK_MATERIAL_MAX_PX,
            )
            return orig(comp, face_lines, text_spans, gates=g2)

        rooms._is_band_pocket = raised
        try:
            ents2, _ = H.run(p)
        finally:
            rooms._is_band_pocket = orig

        for rec in calls:
            sp = rec.get("spacing")
            if rec["degenerate"]:
                rec["band"] = "degenerate"
            elif sp <= cap:
                rec["band"] = "under_cap"
            elif sp <= thick:
                rec["band"] = "in_band"
            else:
                rec["band"] = "over_thick"
            rec["cover_ok"] = (not rec["degenerate"]) and rec["covers"][0] >= COVER_MIN
            rec["would_drop"] = (
                rec["band"] == "in_band" and not rec["text"] and rec["cover_ok"]
            )
            cls, v, note = _gt_class(slug, p.page_number, rec["bbox"])
            rec.update(gt=cls, gt_iou=round(v, 3), gt_note=note[:160])
            cx, cy = (rec["bbox"][0] + rec["bbox"][2]) / 2, (rec["bbox"][1] + rec["bbox"][3]) / 2
            rec["spacing_mm"] = None if sp is None else (
                None if H.mm(slug, sp, cx, cy) is None else round(H.mm(slug, sp, cx, cy)))
            rec["short_mm"] = None if rec["short"] is None else (
                None if H.mm(slug, rec["short"], cx, cy) is None else round(H.mm(slug, rec["short"], cx, cy)))
            for k in ("short", "long", "spacing"):
                if rec.get(k) is not None:
                    rec[k] = round(rec[k], 2)
            if rec["covers"] is not None:
                rec["covers"] = [round(v, 3) for v in rec["covers"]]

        moved, gone, new = _room_diff(_rooms(ents), _rooms(ents2))
        sc, sc2 = H.score(slug, p.page_number, ents), H.score(slug, p.page_number, ents2)
        rec = {
            "slug": slug, "page": p.page_number, "factor": round(f, 4),
            "cap_px": round(cap, 2), "thick_px": round(thick, 2),
            "calls": calls,
            "rooms_moved": moved, "rooms_gone": gone, "rooms_new": new,
            "score_base": {k: sc[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
            "score_after": {k: sc2[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
        }
        records.append(rec)
        n_in = [c for c in calls if c["band"] == "in_band"]
        n_drop = [c for c in n_in if c["would_drop"]]
        print(f"{slug} p{p.page_number} f={f:.3f} cap {cap:.1f} thick {thick:.1f}: "
              f"pocket-rule calls {len(calls)} (under_cap {sum(1 for c in calls if c['band']=='under_cap')}, "
              f"already dropped {sum(1 for c in calls if c['res_cap'])}, in_band {len(n_in)}, "
              f"would_drop {len(n_drop)}, over_thick {sum(1 for c in calls if c['band']=='over_thick')}) "
              f"| rooms gone {len(gone)} new {len(new)} moved {len(moved)} | "
              f"score lost={len(sc['lost'])} fp={len(sc['returned_fps'])} unrev={len(sc['unreviewed'])} "
              f"-> lost={len(sc2['lost'])} fp={len(sc2['returned_fps'])} unrev={len(sc2['unreviewed'])}",
              flush=True)
        for c in sorted(n_in, key=lambda c: c["spacing"]):
            print(f"    IN_BAND {'DROP' if c['would_drop'] else 'keep'} bbox {[round(v) for v in c['bbox']]} "
                  f"short {c['short']} spacing {c['spacing']} ({c['spacing_mm']}mm) covers {c['covers']} "
                  f"text={c['text']} area {c['area']} gt={c['gt']} {c['gt_iou']} {c['gt_note'][:60]!r}")
        for r in gone:
            print(f"    room GONE {r['bbox']} area {r['area']} conf {r['conf']}")
        for r in new:
            print(f"    room NEW {r['bbox']} area {r['area']}")
        for r in moved:
            print(f"    room MOVED {r['bbox']} iou {r['iou']} lost {r['lost']} gained {r['gained']}")
        if sc2["lost"] != sc["lost"]:
            print(f"    LOST delta: {sc2['lost']}")
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
