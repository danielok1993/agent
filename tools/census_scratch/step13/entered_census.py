"""Step 13, second census — the ENTERED narrow rooms: every emitted room whose
minimum-rotated-rectangle spacing (short side + 2 * ROOM_LINE_BARRIER_PX)
lies at or under the scaled WALL_THICK_MATERIAL_MAX_PX with both long-edge
face covers >= ROOM_BAND_POCKET_FACE_COVER_MIN — i.e. the population a raised
band-pocket ceiling would drop IF the entrance gate did not hold it — with
its entrance count replicated exactly as detect_rooms reads it and, per
touching entrance, how that entrance meets the room: the length of the
room boundary within ROOM_CONTACT_TOL_PX of the entrance seal, and the
seal's long axis against the room's long axis (ALONG the boundary = a door
hung in one of the space's bounding walls; ACROSS = a doorway cut through
the wall the strip lies inside — s17's reveal strips end at such doorways).

Read off detect_rooms' own locals: a tap on `_free_space_components` reads
the caller frame's `face_lines` (complete at that point: barrier-face
extents plus both flanks of every segment) and `door_barriers` (every
(confidence, seal) pair), and a tap on `_drop_window_exterior_sides` takes
the rooms list with its door / window counts.

Usage: .venv/bin/python tools/census_scratch/step13/entered_census.py [slugs...]
Writes step13/entered_census.json (ENTERED_CENSUS_OUT to run two jobs).
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
from shapely.geometry import LineString, Polygon  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from detection import rooms, walls  # noqa: E402
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.matching import iou  # noqa: E402

OUT = Path(os.environ.get("ENTERED_CENSUS_OUT",
                          Path(__file__).resolve().parent / "entered_census.json"))
COVER_MIN = rooms.ROOM_BAND_POCKET_FACE_COVER_MIN
STANDOFF = 2.0 * rooms.ROOM_LINE_BARRIER_PX
TOL = rooms.ROOM_CONTACT_TOL_PX
ALL = os.environ.get("ENTERED_ALL") == "1"


def _mrr(comp):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        rect = comp.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        return None
    c = list(rect.exterior.coords)[:4]
    edges = [(c[i], c[(i + 1) % 4]) for i in range(4)]
    lens = [_line_length(a, b) for a, b in edges]
    if lens[0] >= lens[1]:
        return (edges[0], edges[2]), lens[1], lens[0], _line_angle_deg(*edges[0]), c
    return (edges[1], edges[3]), lens[0], lens[1], _line_angle_deg(*edges[1]), c


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


def census(slug):
    records = []
    for p in H.load(slug):
        f = p.scale_factor
        wg = walls.WallGates.at(f)
        cap, thick = wg.WALL_MAX_THICKNESS_PX, wg.WALL_THICK_MATERIAL_MAX_PX
        captured = {}
        o_fsc, o_drop = rooms._free_space_components, rooms._drop_window_exterior_sides

        def fsc(page, barriers):
            # detect_rooms' own locals at the moment it builds the free space:
            # face_lines is complete (barrier-face extents + segment flanks)
            # and door_barriers carries every (confidence, seal) pair.
            loc = sys._getframe(1).f_locals
            captured["face_lines"] = list(loc["face_lines"])
            captured["door_barriers"] = list(loc["door_barriers"])
            return o_fsc(page, barriers)

        def drop(rooms_list, windows, **k):
            captured["rooms"] = list(rooms_list)
            return o_drop(rooms_list, windows, **k)

        rooms._free_space_components, rooms._drop_window_exterior_sides = fsc, drop
        try:
            ents, extras = H.run(p, keep_network=True)
        finally:
            rooms._free_space_components, rooms._drop_window_exterior_sides = o_fsc, o_drop

        face_lines = captured.get("face_lines", [])
        entrance = [(conf, g, None) for conf, g in captured.get("door_barriers", [])
                    if conf >= rooms.ROOM_ENTRANCE_MIN_CONFIDENCE]
        out_rooms = []
        for poly, info in captured.get("rooms", []):
            m = _mrr(poly)
            if m is None:
                continue
            long_edges, short, long, axis, corners = m
            spacing = short + STANDOFF
            covers = sorted(rooms._edge_face_cover(e, face_lines) for e in long_edges)
            if spacing > thick and not ALL:
                continue          # every room at pocket spacing is recorded; cover_ok says
                                  # whether the rule's face test would also pass
                                  # (ENTERED_ALL=1 records every room, for the true
                                  # class's entrance-contact distribution)
            boundary = poly.exterior
            ents_here = []
            for conf, g, b in entrance:
                if g.distance(boundary) > TOL:
                    continue
                near = boundary.intersection(g.buffer(TOL))
                contact = near.length
                gm = _mrr(g)
                g_axis = gm[3] if gm else None
                rel = None if g_axis is None else _angle_diff_mod180(g_axis, axis)
                ents_here.append({
                    "conf": conf,
                    "contact_px": round(contact, 1), "seal_axis_vs_room": None if rel is None else round(rel, 1),
                    "meets": None if rel is None else ("along" if rel < 45.0 else "across"),
                    "seal_bbox": [round(v, 1) for v in g.bounds],
                })
            b = [round(v, 1) for v in poly.bounds]
            cls, v, note = _gt_class(slug, p.page_number, b)
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            out_rooms.append({
                "bbox": b, "area": round(poly.area), "short": round(short, 2), "long": round(long, 2),
                "spacing": round(spacing, 2),
                "spacing_mm": None if H.mm(slug, spacing, cx, cy) is None else round(H.mm(slug, spacing, cx, cy)),
                "covers": [round(c, 3) for c in covers], "cover_ok": covers[0] >= COVER_MIN,
                "axis_deg": round(axis, 1),
                "door_count": info["door_count"], "window_count": info["window_count"],
                "entrance_count": len(ents_here), "entrances": ents_here,
                "text": rooms._contains_text(poly, p.page_data.text_spans),
                "gt": cls, "gt_iou": round(v, 3), "gt_note": note[:120],
                "mrr": [[round(x, 1), round(y, 1)] for x, y in corners],
            })
        records.append({"slug": slug, "page": p.page_number, "factor": round(f, 4),
                        "cap_px": round(cap, 2), "thick_px": round(thick, 2),
                        "n_rooms": len(captured.get("rooms", [])), "n_face_lines": len(face_lines),
                        "rooms": out_rooms})
        print(f"{slug} p{p.page_number} f={f:.3f} thick {thick:.1f}: rooms {len(captured.get('rooms', []))}, "
              f"at-pocket-spacing {len(out_rooms)} (both edges on faces {sum(1 for r in out_rooms if r['cover_ok'])}, "
              f"entered {sum(1 for r in out_rooms if r['entrance_count'])}, "
              f"windowed {sum(1 for r in out_rooms if r['window_count'])})", flush=True)
        for r in sorted(out_rooms, key=lambda r: r["spacing"]):
            print(f"    {r['bbox']} short {r['short']} sp {r['spacing']} ({r['spacing_mm']}mm) cov {r['covers']} "
                  f"doors {r['door_count']} win {r['window_count']} entr {r['entrance_count']} text={r['text']} "
                  f"gt={r['gt']} {r['gt_note'][:40]!r}")
            for e in r["entrances"]:
                print(f"        entrance seal {e['seal_bbox']} conf {e['conf']} contact {e['contact_px']}px "
                      f"axis vs room {e['seal_axis_vs_room']} -> {e['meets']}")
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
