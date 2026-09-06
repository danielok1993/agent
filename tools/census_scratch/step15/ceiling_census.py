"""Step 15 — the band-pocket rule AS IMPLEMENTED (the polygon's-own-sides
cover reading) run at each candidate ceiling on every sheet at its factor,
for the rule alone: the chain once as it stands, then once per ceiling with
`_is_band_pocket` handed a gates object whose WALL_MAX_THICKNESS_PX is the
ceiling (scaled by the page factor; nothing else in the room stage sees
it), rooms diffed against the as-is run and both scored against the truth.
Every component the rule DROPS at a ceiling is listed with its ground-truth
class — what each s17 strip does at each ceiling, and what else goes.

Usage: .venv/bin/python tools/census_scratch/step15/ceiling_census.py [slugs...]
Writes step15/ceiling_census.json (CEILING_CENSUS_OUT to run several jobs).
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as H  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

from detection import rooms  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("CEILING_CENSUS_OUT",
                          Path(__file__).resolve().parent / "ceiling_census.json"))
CEILINGS = (40.0, 41.0, 44.0, 48.0, 56.0)    # px at 1:50; 36 is the tree as it stands


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
                    "poly": Polygon(e["evidence"]["polygon"]).buffer(0)})
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


def _run_at(p, ceiling_1_50):
    """The chain with the pocket rule's ceiling at `ceiling_1_50` × f (None = as is);
    returns (ents, [(bbox, spacing, dropped)] for every call)."""
    calls = []
    orig = rooms._is_band_pocket

    def tap(comp, face_lines, text_spans, *, cap_lines=(), gates=rooms.ROOM_GATES_UNSCALED):
        g = gates
        if ceiling_1_50 is not None:
            g = dataclasses.replace(gates, WALL_MAX_THICKNESS_PX=ceiling_1_50 * gates.factor)
        res = orig(comp, face_lines, text_spans, cap_lines=cap_lines, gates=g)
        calls.append(([round(v, 1) for v in comp.bounds], bool(res)))
        return res

    rooms._is_band_pocket = tap
    try:
        ents, _ = H.run(p)
    finally:
        rooms._is_band_pocket = orig
    return ents, calls


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        ents0, calls0 = _run_at(p, None)
        sc0 = H.score(slug, p.page_number, ents0)
        base_rooms = _rooms(ents0)
        rec = {"slug": slug, "page": p.page_number, "factor": round(f, 4),
               "as_is": {"n_calls": len(calls0), "dropped": [b for b, r in calls0 if r],
                         "score": {k: sc0[k] for k in ("counts", "lost", "returned_fps", "unreviewed")}},
               "ceilings": {}}
        print(f"{slug} p{p.page_number} f={f:.3f}: as-is calls {len(calls0)} dropped {sum(1 for _, r in calls0 if r)} "
              f"score lost={len(sc0['lost'])} fp={len(sc0['returned_fps'])} unrev={len(sc0['unreviewed'])}", flush=True)
        for c in CEILINGS:
            ents, calls = _run_at(p, c)
            sc = H.score(slug, p.page_number, ents)
            moved, gone, new = _room_diff(base_rooms, _rooms(ents))
            dropped = [b for b, r in calls if r]
            newly = [b for b in dropped if b not in rec["as_is"]["dropped"]]
            newly_cls = [(b, *_gt_class(slug, p.page_number, b)[:2]) for b in newly]
            rec["ceilings"][str(int(c))] = {
                "ceiling_px": round(c * f, 2), "n_calls": len(calls), "dropped": dropped,
                "newly_dropped": [{"bbox": b, "gt": g, "gt_iou": round(v, 3)} for b, g, v in newly_cls],
                "rooms_gone": gone, "rooms_new": new, "rooms_moved": moved,
                "score": {k: sc[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
            }
            print(f"    ceiling {int(c)} ({c * f:.1f}px): newly dropped {len(newly)} "
                  f"| rooms gone {len(gone)} new {len(new)} moved {len(moved)} | "
                  f"lost {len(sc0['lost'])}->{len(sc['lost'])} fp {len(sc0['returned_fps'])}->{len(sc['returned_fps'])} "
                  f"unrev {len(sc0['unreviewed'])}->{len(sc['unreviewed'])}", flush=True)
            for b, g, v in newly_cls:
                print(f"        DROP {b} gt={g} {v:.2f}")
            for r in new:
                print(f"        room NEW {r['bbox']} area {r['area']} conf {r['conf']}")
            for r in moved:
                print(f"        room MOVED {r['bbox']} iou {r['iou']} lost {r['lost']} gained {r['gained']}")
            if sc["lost"] != sc0["lost"]:
                print(f"        LOST delta: {sc['lost']}")
        records.append(rec)
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
