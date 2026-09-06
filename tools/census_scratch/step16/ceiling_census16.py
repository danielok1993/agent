"""Step 16 — the band-pocket rule AS IMPLEMENTED, with and without the
end-closure exemption (ROOM_BAND_POCKET_END_CLOSURE_MIN), at every candidate
ceiling on every sheet at its factor, for the rule alone: the chain once as
it stands (exemption on, ceiling WALL_MAX_THICKNESS_PX), then per ceiling
with `_is_band_pocket` handed a gates object whose WALL_MAX_THICKNESS_PX is
the ceiling × f, each ceiling twice — exemption ON and OFF (`_end_closures`
patched to read 0 / 0, i.e. the step-15 rule exactly) — rooms diffed
against the as-is run and every run scored against the truth. Every
component the rule drops is listed with its ground-truth class.

Usage: .venv/bin/python tools/census_scratch/step16/ceiling_census16.py [slugs...]
Writes step16/ceiling_census16.json (CEILING16_OUT to run several jobs).
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

OUT = Path(os.environ.get("CEILING16_OUT",
                          Path(__file__).resolve().parent / "ceiling_census16.json"))
CEILINGS = (36.0, 40.0, 41.0, 44.0, 48.0, 56.0)    # px at 1:50, × f


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


def _run_at(p, ceiling_1_50, exempt):
    """The chain with the pocket rule's ceiling at `ceiling_1_50` × f (None =
    as is) and the end-closure exemption on or off; returns (ents, calls)."""
    calls = []
    orig = rooms._is_band_pocket
    orig_closures = rooms._end_closures

    def tap(comp, face_lines, text_spans, *, cap_lines=(), solids=None,
            gates=rooms.ROOM_GATES_UNSCALED):
        g = gates
        if ceiling_1_50 is not None:
            g = dataclasses.replace(gates, WALL_MAX_THICKNESS_PX=ceiling_1_50 * gates.factor)
        res = orig(comp, face_lines, text_spans, cap_lines=cap_lines, solids=solids, gates=g)
        closures = orig_closures_real(comp, solids) if solids is not None else None
        calls.append(([round(v, 1) for v in comp.bounds], bool(res), closures))
        return res

    def orig_closures_real(comp, solids):
        import warnings
        from detection.geometry import _line_length
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            rect = comp.minimum_rotated_rectangle
        if rect.geom_type != "Polygon":
            return None
        c = list(rect.exterior.coords)[:4]
        edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
        lens = [_line_length(a, b) for a, b in edges]
        end_edge = edges[1] if lens[0] >= lens[1] else edges[0]
        return [round(v, 3) for v in orig_closures(comp, end_edge, (rect.centroid.x, rect.centroid.y), solids)]

    rooms._is_band_pocket = tap
    if not exempt:
        rooms._end_closures = lambda *a, **k: (0.0, 0.0)
    try:
        ents, _ = H.run(p)
    finally:
        rooms._is_band_pocket = orig
        rooms._end_closures = orig_closures
    return ents, calls


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        ents0, calls0 = _run_at(p, None, True)
        sc0 = H.score(slug, p.page_number, ents0)
        base_rooms = _rooms(ents0)
        rec = {"slug": slug, "page": p.page_number, "factor": round(f, 4),
               "as_is": {"n_calls": len(calls0),
                         "calls": [{"bbox": b, "dropped": r, "closures": cl} for b, r, cl in calls0],
                         "score": {k: sc0[k] for k in ("counts", "lost", "returned_fps", "unreviewed")}},
               "runs": {}}
        print(f"{slug} p{p.page_number} f={f:.3f}: as-is (exempt on, ceiling 36) calls {len(calls0)} "
              f"dropped {sum(1 for _, r, _ in calls0 if r)} "
              f"score lost={len(sc0['lost'])} fp={len(sc0['returned_fps'])} unrev={len(sc0['unreviewed'])}", flush=True)
        for b, r, cl in calls0:
            print(f"    call {b} dropped={r} closures={cl}")
        for c in CEILINGS:
            for exempt in (True, False):
                ents, calls = _run_at(p, c, exempt)
                sc = H.score(slug, p.page_number, ents)
                moved, gone, new = _room_diff(base_rooms, _rooms(ents))
                dropped = [b for b, r, _ in calls if r]
                as_is_dropped = [b for b, r, _ in calls0 if r]
                newly = [b for b in dropped if b not in as_is_dropped]
                undropped = [b for b in as_is_dropped if b not in dropped]
                newly_cls = [(b, *_gt_class(slug, p.page_number, b)[:2]) for b in newly]
                key = f"{int(c)}_{'on' if exempt else 'off'}"
                rec["runs"][key] = {
                    "ceiling_px": round(c * f, 2), "exempt": exempt, "n_calls": len(calls),
                    "dropped": dropped,
                    "newly_dropped": [{"bbox": b, "gt": g, "gt_iou": round(v, 3)} for b, g, v in newly_cls],
                    "undropped": undropped,
                    "rooms_gone": gone, "rooms_new": new, "rooms_moved": moved,
                    "score": {k: sc[k] for k in ("counts", "lost", "returned_fps", "unreviewed")},
                }
                print(f"    ceiling {int(c)} ({c * f:.1f}px) exempt={'on ' if exempt else 'off'}: "
                      f"newly dropped {len(newly)} undropped {len(undropped)} | rooms gone {len(gone)} new {len(new)} "
                      f"moved {len(moved)} | lost {len(sc0['lost'])}->{len(sc['lost'])} "
                      f"fp {len(sc0['returned_fps'])}->{len(sc['returned_fps'])} "
                      f"unrev {len(sc0['unreviewed'])}->{len(sc['unreviewed'])}", flush=True)
                for b, g, v in newly_cls:
                    print(f"        DROP {b} gt={g} {v:.2f}")
                for b in undropped:
                    print(f"        UNDROPPED {b}")
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
