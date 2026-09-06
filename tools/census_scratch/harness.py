"""W-gate census harness: run the stage-5 chain exactly as tools/regress.py
does, with (a) per-constant overrides for ablation and (b) instrumentation
taps that record the populations each gate discriminates.

Self-check: run(page) with no overrides must reproduce the sweep's counts
(findings §4c rule) — see selfcheck().
"""
from __future__ import annotations

import dataclasses
import json
import math
import pickle
import sys
from pathlib import Path

REPO = Path("/Users/danielszweda/Documents/GitHub/UD/agent")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

CACHE = Path(__file__).resolve().parent / "cache"
CACHE.mkdir(exist_ok=True)

import _corpus_page  # noqa: E402
from detection import walls, rooms  # noqa: E402
from detection.doors import constants as dconst  # noqa: E402
from detection import windows as wmod  # noqa: E402
from detection import postprocess as pp  # noqa: E402
from detection.doors.assembly import door_open_leaf_path_indices  # noqa: E402
from detection.doors.detect import detect_doors  # noqa: E402
from detection.windows import detect_windows  # noqa: E402
from detection.walls import detect_wall_network  # noqa: E402
from detection.rooms import detect_rooms  # noqa: E402
from detection.postprocess import (  # noqa: E402
    _cross_validate, _resolve_door_window_conflicts, _suppress,
)
from detection.geometry import _line_length, _line_angle_deg, _angle_diff_mod180  # noqa: E402
from pipeline import OFFLINE_MIN_CONFIDENCE  # noqa: E402
from regression.ground_truth import load_truth  # noqa: E402
from regression.sweep import evaluate_page  # noqa: E402
from regression.matching import match_entities, iou  # noqa: E402

MM_PER_PX_AT_1 = 0.16933  # mm of paper per 150-DPI px

# TRUE scale per sheet / region: the takeoff denominator, never the gate factor.
# Mixed sheets carry a list of (bbox, denominator); features are assigned by
# their centre.
TRUE_SCALE = {
    "s01": 92.2, "s02": 50.0, "s04": 50.0, "s05": 100.0, "s06": 100.0,
    "s07": 100.0, "s08": 50.0, "s10": 50.0, "s11": 100.0, "s12": 100.0,
    "s13": 136.4, "s14": 50.0, "s15": 50.0, "s16": 100.0, "s18": 100.0,
    "s20": 50.0,
    "s03": [((356, 276, 888, 1400), 100.0), ((1056, 480, 1480, 1400), 100.0),
            ((3312, 488, 4208, 2256), 50.0)],
    "s17": [((208, 1068, 1144, 1860), 100.0), ((1276, 1164, 1936, 1644), 100.0),
            ((176, 1860, 2080, 3364), 50.0), ((2344, 2168, 3720, 3124), 50.0)],
}


def denom_at(slug: str, x: float, y: float) -> float | None:
    ts = TRUE_SCALE.get(slug)
    if ts is None:
        return None
    if isinstance(ts, float):
        return ts
    best = None
    for (x0, y0, x1, y1), d in ts:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return d
        # nearest region as fallback
        dx = max(x0 - x, 0, x - x1)
        dy = max(y0 - y, 0, y - y1)
        dist = math.hypot(dx, dy)
        if best is None or dist < best[0]:
            best = (dist, d)
    return best[1] if best else None


def mm(slug: str, px: float, x: float, y: float) -> float | None:
    d = denom_at(slug, x, y)
    return None if d is None else px * MM_PER_PX_AT_1 * d


# ---------------------------------------------------------------------------
# Loading (cached)
# ---------------------------------------------------------------------------
def load(slug: str):
    pk = CACHE / f"{slug}.pkl"
    if pk.exists():
        return pickle.loads(pk.read_bytes())
    pages = _corpus_page.load_detection_pages(slug)
    pk.write_bytes(pickle.dumps(pages))
    return pages


# ---------------------------------------------------------------------------
# Gate overrides
# ---------------------------------------------------------------------------
GATE_CLASSES = {
    "wall": walls.WallGates, "room": rooms.RoomGates, "door": dconst.DoorGates,
    "window": wmod.WindowGates, "cross": pp.CrossGates,
}
_ORIG_AT = {k: cls.at.__func__ for k, cls in GATE_CLASSES.items()}


class overrides:
    """Context manager: multiply named gate fields (any class that has them)
    by the given multiplier, on top of whatever .at(factor) produced."""

    def __init__(self, mult: dict[str, float] | None = None,
                 absolute: dict[str, float] | None = None):
        self.mult = mult or {}
        self.absolute = absolute or {}

    def __enter__(self):
        mult, absolute = self.mult, self.absolute

        def make(cls_key):
            orig = _ORIG_AT[cls_key]

            def at(cls, factor):
                g = orig(cls, factor)
                names = {f.name for f in dataclasses.fields(g)}
                changes = {}
                for k, m in mult.items():
                    if k in names:
                        changes[k] = getattr(g, k) * m
                for k, v in absolute.items():
                    if k in names:
                        changes[k] = v
                return dataclasses.replace(g, **changes) if changes else g
            return classmethod(at)

        for key, cls in GATE_CLASSES.items():
            cls.at = make(key)
        # module-level UNSCALED singletons are built at import; the pipeline
        # always calls .at(factor) at use sites, so nothing else to do.
        return self

    def __exit__(self, *a):
        for key, cls in GATE_CLASSES.items():
            cls.at = classmethod(_ORIG_AT[key])


# ---------------------------------------------------------------------------
# Instrumentation taps
# ---------------------------------------------------------------------------
class Taps:
    def __init__(self):
        self.pairs = []            # every centerline emitted by _pair_faces_to_centerlines (final call)
        self.pairs_interim = []
        self.wide_pairs = []       # above-cap probe: strong pairs 36..200px
        self.material = []         # _band_has_wall_material calls
        self.faces = []            # strong faces from _collect_wall_faces
        self.weak_faces = []
        self.plugs = []            # _door_plugs per edge
        self.components = []       # free-space components
        self.bridges = []          # white-run bridges
        self.fill_classes = {}
        self.rings = []
        self.marks = []
        self.merge_offsets = []    # collinear merge member offsets


def _install_taps(taps: Taps):
    o_pair = walls._pair_faces_to_centerlines
    o_mat = walls._band_has_wall_material
    o_faces = walls._collect_wall_faces
    o_weak = walls._collect_weak_faces
    o_plugs = rooms._door_plugs
    o_fsc = rooms._free_space_components
    o_bridge = walls._bridge_white_runs
    o_rate = walls._rate_fill_classes
    o_rings = walls._collect_fill_rings
    o_marks = walls._collect_material_marks

    def pair(faces, thick_tier=False, *, gates=walls.WALL_GATES_UNSCALED):
        out = o_pair(faces, thick_tier, gates=gates)
        recs = []
        for c in out:
            recs.append({
                "th": c.thickness, "len": _line_length(c.p1, c.p2),
                "weak": c.weak, "thick": c.thick, "through": c.through,
                "stroked": c.stroked, "fill": c.wall_fill,
                "mid": ((c.p1[0] + c.p2[0]) / 2, (c.p1[1] + c.p2[1]) / 2),
                "pen": c.pen, "sw": c.stroke_width, "p1": c.p1, "p2": c.p2,
                "ang": _line_angle_deg(c.p1, c.p2),
            })
        if thick_tier:
            taps.pairs.extend(recs)
            # Above-cap probe: what would pair if the caps were 4x wider.
            wide = dataclasses.replace(
                gates,
                WALL_MAX_THICKNESS_PX=gates.WALL_MAX_THICKNESS_PX * 4,
                WALL_THICK_MATERIAL_MAX_PX=gates.WALL_THICK_MATERIAL_MAX_PX * 4,
                WALL_THROUGH_HATCH_MAX_PX=gates.WALL_THROUGH_HATCH_MAX_PX * 4,
            )
            strong = [f for f in faces if not f.weak]
            for c in o_pair(strong, False, gates=wide):
                if c.thickness > gates.WALL_MAX_THICKNESS_PX:
                    taps.wide_pairs.append({
                        "th": c.thickness, "len": _line_length(c.p1, c.p2),
                        "stroked": c.stroked, "fill": c.wall_fill,
                        "pen": c.pen, "sw": c.stroke_width,
                        "p1": c.p1, "p2": c.p2,
                        "mid": ((c.p1[0] + c.p2[0]) / 2, (c.p1[1] + c.p2[1]) / 2),
                        "material": o_mat(c, taps._marks, gates=gates) if taps._marks is not None else None,
                        "through": walls._band_has_through_hatch(c, taps._through_marks, gates=gates) if taps._through_marks is not None else None,
                    })
        else:
            taps.pairs_interim.extend(recs)
        return out

    def mat(c, marks, *, gates=walls.WALL_GATES_UNSCALED):
        res = o_mat(c, marks, gates=gates)
        # replicate the count
        length = _line_length(c.p1, c.p2)
        n = 0
        span = 0.0
        if length > 1e-6:
            ux = (c.p2[0] - c.p1[0]) / length
            uy = (c.p2[1] - c.p1[1]) / length
            axis = _line_angle_deg(c.p1, c.p2)
            half = max(c.thickness / 2.0 - walls.WALL_WEAK_MATERIAL_EDGE_PX, c.thickness * 0.25)
            ts = []
            for (mx, my), angle, *_ in marks:
                t = (mx - c.p1[0]) * ux + (my - c.p1[1]) * uy
                if not (-1.0 <= t <= length + 1.0):
                    continue
                if abs((mx - c.p1[0]) * -uy + (my - c.p1[1]) * ux) > half:
                    continue
                d = _angle_diff_mod180(angle, axis)
                if walls.WALL_WEAK_MATERIAL_ANGLE_MIN <= d <= walls.WALL_WEAK_MATERIAL_ANGLE_MAX:
                    ts.append(t)
            n = len(ts)
            span = (max(ts) - min(ts)) / length if ts else 0.0
        taps.material.append({
            "len": length, "th": c.thickness, "weak": c.weak, "thick": c.thick,
            "n": n, "per100": n / (length / 100.0) if length > 0 else 0.0,
            "span": span, "ok": res,
            "mid": ((c.p1[0] + c.p2[0]) / 2, (c.p1[1] + c.p2[1]) / 2),
        })
        return res

    def faces_fn(paths, fill_is_wall, marker_indices, excluded, *, gates):
        faces, bands = o_faces(paths, fill_is_wall, marker_indices, excluded, gates=gates)
        for f in faces:
            taps.faces.append({
                "len": _line_length(f.p1, f.p2), "sw": f.stroke_width,
                "stroked": f.stroked, "fill": f.wall_fill, "pen": f.pen,
                "mid": ((f.p1[0] + f.p2[0]) / 2, (f.p1[1] + f.p2[1]) / 2),
                "idx": tuple(sorted(f.indices)),
                "ang": _line_angle_deg(f.p1, f.p2), "p1": f.p1, "p2": f.p2,
            })
        taps.n_bands = len(bands)
        return faces, bands

    def weak_fn(paths, excluded, *, gates):
        out = o_weak(paths, excluded, gates=gates)
        for f in out:
            taps.weak_faces.append({"len": _line_length(f.p1, f.p2), "sw": f.stroke_width})
        return out

    def plugs_fn(bbox, wall_material, skip_edges=frozenset(), *,
                 seek_edges=frozenset(), gates=rooms.ROOM_GATES_UNSCALED):
        # seek_edges arrived with iteration 3 step 10 (the material-seeking
        # tail); passed through untouched so the tap keeps reproducing the
        # sweep.
        out = o_plugs(bbox, wall_material, skip_edges, seek_edges=seek_edges,
                      gates=gates)
        # Re-derive the per-edge profile at a WIDE seal reach so we can see the
        # true jamb distance regardless of the gate.
        x0, y0, x1, y1 = bbox
        edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)),
                 ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
        qualified = {e: kind for _, kind, e in out}
        from shapely.geometry import LineString
        reach = 60.0
        for e, (p, q) in enumerate(edges):
            length = math.hypot(q[0] - p[0], q[1] - p[1])
            if length < 1e-6:
                continue
            ux, uy = (q[0] - p[0]) / length, (q[1] - p[1]) / length
            a = (p[0] - ux * reach, p[1] - uy * reach)
            b = (q[0] + ux * reach, q[1] + uy * reach)
            ext = length + 2 * reach
            line = LineString([a, b])
            n = int(ext / 1.0) + 1
            d = [line.interpolate(ext * i / (n - 1)).distance(wall_material) for i in range(n)]
            touch = [v <= gates.ROOM_PLUG_HALF_WIDTH_PX for v in d]
            # distance from bbox corner OUTWARD to first touching sample
            # (negative = material already inside the bbox edge extent)
            def first_touch_out(seq):
                for i, t in enumerate(seq):
                    if t:
                        return i
                return None
            # samples 0..reach are outside at start; index reach == bbox corner
            k = int(reach)
            start_out = first_touch_out(list(reversed(touch[:k + 1])))  # from corner going outward
            end_out = first_touch_out(touch[n - 1 - k:])
            # hug length of the touching run at each end (jamb size along the edge)
            def run_len(seq):
                L = 0
                for t in seq:
                    if t:
                        L += 1
                    else:
                        break
                return L
            si = None if start_out is None else k - start_out
            ei = None if end_out is None else n - 1 - k + end_out
            hug_a = run_len(touch[si:]) if si is not None else 0
            hug_b = run_len(list(reversed(touch[:ei + 1]))) if ei is not None else 0
            taps.plugs.append({
                "bbox": bbox, "edge": e, "len": length,
                "qualified": qualified.get(e), "skipped": e in skip_edges,
                "jamb_gap_a": start_out, "jamb_gap_b": end_out,
                "hug_a": hug_a, "hug_b": hug_b,
            })
        return out

    def fsc_fn(page, barriers):
        comps = o_fsc(page, barriers)
        for c in comps:
            mrr = c.minimum_rotated_rectangle
            xs = list(mrr.exterior.coords)
            s1 = math.dist(xs[0], xs[1]); s2 = math.dist(xs[1], xs[2])
            taps.components.append({
                "area": c.area, "short": min(s1, s2), "long": max(s1, s2),
                "bounds": c.bounds, "poly": c,
            })
        return comps

    def bridge_fn(accepted, *, gates):
        out = o_bridge(accepted, gates=gates)
        # record all pairwise gaps between accepted rings (candidate spans)
        polys = [r.poly for r in accepted]
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                g = polys[i].distance(polys[j])
                if g <= gates.WALL_JOINERY_BRIDGE_GAP_PX * 3:
                    taps.bridges.append({"gap": g, "n_out": len(out)})
        taps.n_bridges = len(out)
        return out

    def rate_fn(rings, *, gates):
        res = o_rate(rings, gates=gates)
        ink = {}
        for r in rings:
            ink.setdefault(r.key, []).append(r)
        for k, rs in ink.items():
            taps.fill_classes[str(k)] = {
                "ink": sum(r.poly.exterior.length for r in rs), "n": len(rs),
                "wall": res.get(k), "shorts": [r.short for r in rs],
                "band_like": sum(1 for r in rs if r.is_band(gates)),
            }
        return res

    def marks_fn(paths, *, gates=walls.WALL_GATES_UNSCALED, max_len=None):
        out = o_marks(paths, gates=gates, max_len=max_len)
        # Since the W-gate census the pipeline collects marks ONCE, at the
        # through diagonal, and every band gate filters them to its own cap
        # (_mark_len_cap) — so that one call is both populations.
        taps._marks = out
        taps._through_marks = out
        if max_len is None:
            # also collect an UNCAPPED mark population to see the true hatch length
            taps.marks_uncapped = o_marks(paths, gates=gates, max_len=400.0)
        return out

    taps._marks = None
    taps._through_marks = None
    walls._pair_faces_to_centerlines = pair
    walls._band_has_wall_material = mat
    walls._collect_wall_faces = faces_fn
    walls._collect_weak_faces = weak_fn
    rooms._door_plugs = plugs_fn
    rooms._free_space_components = fsc_fn
    walls._bridge_white_runs = bridge_fn
    rooms._bridge_white_runs = bridge_fn
    walls._rate_fill_classes = rate_fn
    walls._collect_material_marks = marks_fn
    return (o_pair, o_mat, o_faces, o_weak, o_plugs, o_fsc, o_bridge, o_rate, o_marks)


def _remove_taps(saved):
    (o_pair, o_mat, o_faces, o_weak, o_plugs, o_fsc, o_bridge, o_rate, o_marks) = saved
    walls._pair_faces_to_centerlines = o_pair
    walls._band_has_wall_material = o_mat
    walls._collect_wall_faces = o_faces
    walls._collect_weak_faces = o_weak
    rooms._door_plugs = o_plugs
    rooms._free_space_components = o_fsc
    walls._bridge_white_runs = o_bridge
    rooms._bridge_white_runs = o_bridge
    walls._rate_fill_classes = o_rate
    walls._collect_material_marks = o_marks


# ---------------------------------------------------------------------------
# The chain
# ---------------------------------------------------------------------------
def run(page, factor: float | None = None, taps: Taps | None = None,
        keep_network: bool = False):
    """Stage-5 chain as run_heuristics does it (labels/schedules omitted),
    then the offline floors. Returns (entities, extras)."""
    f = page.scale_factor if factor is None else factor
    pd = page.page_data
    saved = _install_taps(taps) if taps is not None else None
    try:
        doors = detect_doors(pd.paths, pd.text_spans, None, scale_factor=f)
        windows = detect_windows(pd.paths, scale_factor=f)
        windows = _resolve_door_window_conflicts(doors + windows, scale_factor=f)
        windows = [c for c in windows if c.entity_type == "window"]
        network = detect_wall_network(
            pd.paths, pd.text_spans,
            exclude_path_indices=door_open_leaf_path_indices(doors, pd.paths),
            scale_factor=f,
        )
        all_geo = _cross_validate(doors + windows, network, scale_factor=f)
        all_geo = _suppress(all_geo)
        room_cands = detect_rooms(
            network,
            [c for c in all_geo if c.entity_type == "door"],
            [c for c in all_geo if c.entity_type == "window"],
            pd.width_px, pd.height_px, pd.text_spans, scale_factor=f,
        )
    finally:
        if saved is not None:
            _remove_taps(saved)
    ents = []
    for c in _suppress(all_geo):
        if c.confidence < OFFLINE_MIN_CONFIDENCE.get(c.entity_type, 0.5):
            continue
        ents.append({"entity_type": c.entity_type, "bbox": list(c.bbox),
                     "confidence": c.confidence, "evidence": c.evidence})
    for c in room_cands:
        ents.append({"entity_type": "room", "bbox": list(c.bbox),
                     "confidence": c.confidence, "evidence": c.evidence})
    extras = {"doors_all": doors, "windows_all": windows, "all_geo": all_geo,
              "room_cands": room_cands}
    if keep_network:
        extras["network"] = network
    return ents, extras


def score(slug: str, page_number: int, ents: list[dict]) -> dict:
    truth = load_truth(slug).page(page_number)
    ev = evaluate_page(truth, ents)
    return {
        "counts": ev["counts"],
        "lost": [(t.type, tuple(round(v) for v in t.bbox)) for t in ev["lost"]],
        "returned_fps": [(t.type, tuple(round(v) for v in t.bbox)) for t in ev["returned_fps"]],
        "unreviewed": [(e["entity_type"], tuple(round(v) for v in e["bbox"]), e["confidence"]) for e in ev["unreviewed"]],
        "closed": len(ev["closed_deferred"]),
    }


def diff_vs_baseline(base: list[dict], ents: list[dict]) -> dict:
    """Type+IoU>=0.5 match of a run against the f-baseline run."""
    from regression.ground_truth import TruthItem
    truth = [TruthItem(type=e["entity_type"], bbox=tuple(e["bbox"])) for e in base]
    m = match_entities(truth, ents)
    return {
        "same": len(m.matched),
        "gone": [(t.type, tuple(round(v) for v in t.bbox)) for t in m.unmatched_truth],
        "new": [(e["entity_type"], tuple(round(v) for v in e["bbox"])) for e in m.unmatched_actual],
    }


def selfcheck(slug: str):
    pages = load(slug)
    for p in pages:
        ents, _ = run(p)
        sc = score(slug, p.page_number, ents)
        print(slug, p.page_number, "f=%.3f" % p.scale_factor, sc["counts"],
              "lost", len(sc["lost"]), "retFP", len(sc["returned_fps"]),
              "unrev", len(sc["unreviewed"]))


if __name__ == "__main__":
    for s in sys.argv[1:]:
        selfcheck(s)
