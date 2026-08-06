"""Matching ground-truth items to pipeline output.

Entity ids are ordinal — door_0015 becomes door_0014 the moment an earlier
door stops being detected — so nothing may key on them. Matching is by
entity type plus intersection-over-union, greedily, best pair first, each
side claimed once.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from regression.ground_truth import TruthItem

MIN_IOU = 0.5

BBox = tuple[float, float, float, float]


def iou(a: BBox, b: BBox) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


@dataclass
class MatchResult:
    matched: list[tuple[TruthItem, dict]] = field(default_factory=list)
    unmatched_truth: list[TruthItem] = field(default_factory=list)
    unmatched_actual: list[dict] = field(default_factory=list)


def match_entities(truth: list[TruthItem], actual: list[dict],
                   min_iou: float = MIN_IOU) -> MatchResult:
    pairs = []
    for t_idx, item in enumerate(truth):
        for a_idx, ent in enumerate(actual):
            if ent.get("entity_type") != item.type:
                continue
            score = iou(item.bbox, tuple(ent["bbox"]))
            if score >= min_iou:
                pairs.append((score, t_idx, a_idx))
    pairs.sort(key=lambda p: (-p[0], p[1], p[2]))

    result = MatchResult()
    claimed_truth: set[int] = set()
    claimed_actual: set[int] = set()
    for _score, t_idx, a_idx in pairs:
        if t_idx in claimed_truth or a_idx in claimed_actual:
            continue
        claimed_truth.add(t_idx)
        claimed_actual.add(a_idx)
        result.matched.append((truth[t_idx], actual[a_idx]))
    result.unmatched_truth = [t for i, t in enumerate(truth) if i not in claimed_truth]
    result.unmatched_actual = [a for i, a in enumerate(actual) if i not in claimed_actual]
    return result
