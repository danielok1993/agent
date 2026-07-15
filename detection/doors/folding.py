from __future__ import annotations

import math

from models import Candidate, PathPrimitive, TextSpan
from debug.trace import DebugTraceCollector
from detection.geometry import _angle_diff_mod180, _distance, _is_line_path
from detection.labels import _find_nearby_label
from detection.walls import _is_background_fill
from detection.doors.sliding import _SlidePanel, _collect_slide_panels, _corners_bbox
from detection.doors.constants import (
    DOOR_FOLD_ANGLE_MAX_DEG, DOOR_FOLD_ANGLE_MIN_DEG, DOOR_FOLD_ASSEMBLY_BASE,
    DOOR_FOLD_HINGE_TOL_PX, DOOR_FOLD_LENGTH_RATIO_TOL, DOOR_FOLD_MIN_CHAIN_LEAVES,
    DOOR_FOLD_STACK_MIRROR_TOL_DEG, DOOR_FOLD_STACK_PERP_EXTENT_MAX,
    DOOR_FOLD_STACK_SPAN_RATIO_TOL, DOOR_LABEL_PATTERN, DOOR_LABEL_SEARCH_RADIUS_PX,
    DOOR_SLIDE_PANEL_MERGE_TOL_PX,
)


def _absorb_hinged_white_rings(
    panels: list[_SlidePanel], paths: list[PathPrimitive]
) -> None:
    """Mark stroked-qu panels white when their coincident fill-ring edges exist.

    Folding leaves are drawn in the same Vectorworks joinery signature as
    sliding panels (white fill ring + stroked qu outline), but hinged leaves
    share ring VERTICES, so `_white_ring_rects` rejects them: the shared hinge
    vertex has degree 4 and the leaves' rings BFS-merge into one non-loop
    component. The leaves therefore arrive from `_collect_slide_panels` as
    stroked-qu panels only. A white `l` segment whose both endpoints land on a
    panel's fitted corners IS that panel's fill-ring edge — absorb its path
    index (so downstream component dedupe sees both representations) and mark
    the panel white once a ring's worth of edges (4+) matched.
    """
    tol = DOOR_SLIDE_PANEL_MERGE_TOL_PX
    white_segs: list[tuple[int, tuple[float, float], tuple[float, float]]] = []
    for path in paths:
        if not _is_background_fill(path.fill):
            continue
        ok, p1, p2 = _is_line_path(path)
        if ok and _distance(p1, p2) > 1.0:
            white_segs.append((path.path_index, p1, p2))

    for panel in panels:
        if panel.white:
            continue
        absorbed = [
            idx
            for idx, p1, p2 in white_segs
            if min(_distance(p1, c) for c in panel.corners) <= tol
            and min(_distance(p2, c) for c in panel.corners) <= tol
        ]
        if len(absorbed) >= 4:
            panel.white = True
            panel.path_indices = sorted(set(panel.path_indices) | set(absorbed))
            panel.sources = sorted(set(panel.sources) | {"white_ring"})


def _fold_edges(
    panels: list[_SlidePanel],
) -> dict[tuple[int, int], dict]:
    """Hinge edges between leaf panels: equal lengths, corner contact, and a
    shallow-but-nonzero fold angle between the long axes. Near-parallel panels
    (sliding pairs, wall plies) and near-perpendicular corner joinery both
    fall outside the fold-angle window."""
    edges: dict[tuple[int, int], dict] = {}
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            a, b = panels[i], panels[j]
            delta = _angle_diff_mod180(a.axis_deg, b.axis_deg)
            if not (DOOR_FOLD_ANGLE_MIN_DEG <= delta <= DOOR_FOLD_ANGLE_MAX_DEG):
                continue
            if abs(a.length - b.length) / max(a.length, b.length) > DOOR_FOLD_LENGTH_RATIO_TOL:
                continue
            hinge = min(
                _distance(ca, cb) for ca in a.corners for cb in b.corners
            )
            if hinge > DOOR_FOLD_HINGE_TOL_PX:
                continue
            edges[(i, j)] = {
                "fold_angle_deg": round(delta, 1),
                "hinge_dist_px": round(hinge, 2),
            }
    return edges


def _fold_groups(
    panels: list[_SlidePanel], edges: dict[tuple[int, int], dict]
) -> list[dict]:
    """Connected components of the hinge graph, with per-group stats."""
    adjacency: dict[int, set[int]] = {i: set() for i in range(len(panels))}
    for (i, j) in edges:
        adjacency[i].add(j)
        adjacency[j].add(i)

    groups: list[dict] = []
    seen: set[int] = set()
    for start in range(len(panels)):
        if start in seen or not adjacency[start]:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            idx = stack.pop()
            members.append(idx)
            for other in adjacency[idx]:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        members.sort()
        corners = [c for m in members for c in panels[m].corners]
        # Mean axis via unit-vector sum on doubled angles (axes are mod 180).
        sx = sum(math.cos(2 * math.radians(panels[m].axis_deg)) for m in members)
        sy = sum(math.sin(2 * math.radians(panels[m].axis_deg)) for m in members)
        groups.append({
            "members": members,
            "corners": corners,
            "centroid": (
                sum(p[0] for p in corners) / len(corners),
                sum(p[1] for p in corners) / len(corners),
            ),
            "sum_len": sum(panels[m].length for m in members),
            "mean_len": sum(panels[m].length for m in members) / len(members),
            "mean_axis_deg": (math.degrees(math.atan2(sy, sx)) / 2) % 180.0,
            "fold_angles": [
                edges[key]["fold_angle_deg"]
                for key in edges
                if key[0] in members and key[1] in members
            ],
        })
    return groups


def _pair_parked_stacks(groups: list[dict]) -> list[tuple[int, int, dict]]:
    """Pair two 2-leaf V-stacks parked at opposite jambs of one opening.

    The physical gate is the span law: when the door closes, the leaves unfold
    to cover the opening, so the outer span between the stacks along the
    opening axis must equal the summed leaf lengths. The stacks must also fold
    off the same wall plane (mean leaf angles mirror about the opening axis)
    and each stack must stay compact across that axis (a folded stack projects
    at most ~one leaf length perpendicular to the opening).
    """
    scored: list[tuple[float, int, int, dict]] = []
    for gi in range(len(groups)):
        for gj in range(gi + 1, len(groups)):
            g1, g2 = groups[gi], groups[gj]
            if len(g1["members"]) != 2 or len(g2["members"]) != 2:
                continue
            mean_len = (g1["mean_len"] + g2["mean_len"]) / 2
            if (
                abs(g1["mean_len"] - g2["mean_len"]) / max(g1["mean_len"], g2["mean_len"])
                > DOOR_FOLD_LENGTH_RATIO_TOL
            ):
                continue
            dx = g2["centroid"][0] - g1["centroid"][0]
            dy = g2["centroid"][1] - g1["centroid"][1]
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                continue
            ux, uy = dx / dist, dy / dist
            axis_deg = math.degrees(math.atan2(dy, dx)) % 180.0

            projs = [p[0] * ux + p[1] * uy for p in g1["corners"] + g2["corners"]]
            span = max(projs) - min(projs)
            sum_len = g1["sum_len"] + g2["sum_len"]
            span_ratio = abs(span - sum_len) / sum_len
            if span_ratio > DOOR_FOLD_STACK_SPAN_RATIO_TOL:
                continue

            mirror_dev = _angle_diff_mod180(
                g1["mean_axis_deg"] + g2["mean_axis_deg"], 2 * axis_deg,
            )
            if mirror_dev > DOOR_FOLD_STACK_MIRROR_TOL_DEG:
                continue

            perp_ok = True
            for g in (g1, g2):
                perps = [-p[0] * uy + p[1] * ux for p in g["corners"]]
                if max(perps) - min(perps) > DOOR_FOLD_STACK_PERP_EXTENT_MAX * mean_len:
                    perp_ok = False
            if not perp_ok:
                continue

            metrics = {
                "opening_span_px": round(span, 1),
                "leaf_run_px": round(sum_len, 1),
                "span_ratio_dev": round(span_ratio, 3),
                "mirror_dev_deg": round(mirror_dev, 1),
            }
            scored.append((dist, gi, gj, metrics))

    pairs: list[tuple[int, int, dict]] = []
    consumed: set[int] = set()
    for _, gi, gj, metrics in sorted(scored, key=lambda t: t[0]):
        if gi in consumed or gj in consumed:
            continue
        consumed.update((gi, gj))
        pairs.append((gi, gj, metrics))
    return pairs


def _detect_folding_doors(
    paths: list[PathPrimitive],
    text_spans: list[TextSpan],
    collector: DebugTraceCollector | None,
    cand_idx: int,
) -> tuple[list[Candidate], int]:
    """Detect arc-less folding/bifold doors. Returns (candidates, next index).

    Runs after `_detect_sliding_doors` inside `_pair_door_assemblies`. Two
    patterns over hinge-connected groups of white leaf panels:
    - chain: one group of 3+ leaves (a concertina drawn across the opening).
    - stack_pair: two 2-leaf V-groups parked at opposite jambs, paired by the
      span law (outer span ≈ Σ leaf lengths). A lone 2-leaf V is never emitted.
    Candidates carry assembly_type="folding" and their component_path_indices
    contain the panels' primitives (qu outlines + absorbed fill-ring edges) so
    `_dedupe_door_components` retires the leaf-fallback candidates the same
    rectangles produce.
    """
    panels = _collect_slide_panels(paths)
    _absorb_hinged_white_rings(panels, paths)
    panels = [p for p in panels if p.white]
    edges = _fold_edges(panels)
    groups = _fold_groups(panels, edges)
    candidates: list[Candidate] = []

    def mint(fold_style: str, member_groups: list[dict], metrics: dict) -> Candidate:
        nonlocal cand_idx
        involved = [panels[m] for g in member_groups for m in g["members"]]
        bbox = _corners_bbox([c for p in involved for c in p.corners])
        nearby_label = _find_nearby_label(
            bbox, text_spans, DOOR_LABEL_SEARCH_RADIUS_PX, DOOR_LABEL_PATTERN,
        )
        layer = next((p.layer for p in involved if p.layer), None)
        layer_hint = any(p.layer_hint for p in involved)
        label_boost = 0.20 if nearby_label else 0.0
        layer_boost = 0.40 if layer_hint else 0.0
        confidence = round(
            min(DOOR_FOLD_ASSEMBLY_BASE + label_boost + layer_boost, 0.95), 3,
        )
        fold_angles = sorted(
            angle for g in member_groups for angle in g["fold_angles"]
        )
        component_path_indices = sorted({i for p in involved for i in p.path_indices})
        evidence = {
            "method": "door_assembly",
            "assembly_type": "folding",
            "fold_style": fold_style,
            "leaf_count": len(involved),
            "leaf_bboxes": [list(p.bbox) for p in involved],
            "leaf_sources": ["+".join(p.sources) for p in involved],
            "panel_length_px": round(
                sum(p.length for p in involved) / len(involved), 1,
            ),
            "fold_angles_deg": fold_angles,
            "component_path_indices": component_path_indices,
            "nearby_label": nearby_label,
            "layer": layer,
            "layer_hint": layer_hint,
            "opening_check": "not_applicable",
        }
        evidence.update(metrics)
        candidate_id = f"door_{cand_idx:04d}"
        cand_idx += 1
        candidate = Candidate(
            candidate_id=candidate_id,
            entity_type="door",
            bbox=bbox,
            confidence=confidence,
            evidence=evidence,
        )
        if collector:
            collector.record_candidate(
                candidate_id, "folding_assembly", confidence,
                {
                    "base": DOOR_FOLD_ASSEMBLY_BASE,
                    "label_boost": label_boost, "label_found": nearby_label,
                    "layer_boost": layer_boost, "layer_hint": layer_hint,
                    "fold_style": fold_style,
                    "leaf_count": len(involved),
                    "fold_angles_deg": fold_angles,
                    **metrics,
                    "total": confidence,
                },
                None, None,
            )
        return candidate

    paired: set[int] = set()
    for gi, gj, metrics in _pair_parked_stacks(groups):
        paired.update((gi, gj))
        candidates.append(mint("stack_pair", [groups[gi], groups[gj]], metrics))

    for idx, group in enumerate(groups):
        if idx in paired or len(group["members"]) < DOOR_FOLD_MIN_CHAIN_LEAVES:
            continue
        candidates.append(mint("chain", [group], {}))

    return candidates, cand_idx
