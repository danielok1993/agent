import math
import unittest

from heuristics import (
    CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY,
    DOOR_FALLBACK_CONFIDENCE,
    _cross_validate,
    _dedupe_door_components,
    detect_doors,
)
from models import Candidate, PathPrimitive, TextSpan


def path(
    idx: int,
    item_type: str,
    points: list[tuple[float, float]],
    *,
    layer: str | None = "",
) -> PathPrimitive:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return PathPrimitive(
        path_index=idx,
        item_type=item_type,
        bbox=(min(xs), min(ys), max(xs), max(ys)),
        color=None,
        fill=None,
        stroke_width=1.0,
        dashes="",
        layer=layer,
        points=points,
    )


def line(idx: int, p1: tuple[float, float], p2: tuple[float, float]) -> PathPrimitive:
    return path(idx, "l", [p1, p2])


def rect_lines(
    start_idx: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> list[PathPrimitive]:
    return [
        line(start_idx, (x0, y0), (x1, y0)),
        line(start_idx + 1, (x1, y0), (x1, y1)),
        line(start_idx + 2, (x1, y1), (x0, y1)),
        line(start_idx + 3, (x0, y1), (x0, y0)),
    ]


def quarter_arc_lines(
    start_idx: int,
    radius: float = 80.0,
    segments: int = 8,
) -> list[PathPrimitive]:
    pts = [
        (
            radius * math.cos((math.pi / 2) * i / segments),
            radius * math.sin((math.pi / 2) * i / segments),
        )
        for i in range(segments + 1)
    ]
    return [
        line(start_idx + i, pts[i], pts[i + 1])
        for i in range(segments)
    ]


class DoorAssemblyTests(unittest.TestCase):
    def test_polyline_arc_connected_linework_leaf_base_confidence(self) -> None:
        paths = quarter_arc_lines(0) + rect_lines(100, 80.0, -4.0, 160.0, 4.0)

        doors = detect_doors(paths, [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]

        self.assertEqual(1, len(assemblies))
        self.assertEqual(0.65, assemblies[0].confidence)
        self.assertEqual("polyline_arc", assemblies[0].evidence["arc_source"])
        self.assertEqual("single", assemblies[0].evidence["assembly_type"])

    def test_curve_arc_connected_native_leaf(self) -> None:
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])

        doors = detect_doors([arc, leaf], [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]

        self.assertEqual(1, len(assemblies))
        self.assertEqual(0.65, assemblies[0].confidence)
        self.assertEqual("curve_arc", assemblies[0].evidence["arc_source"])

    def test_nearby_label_boosts_assembled_door(self) -> None:
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])
        label = TextSpan(
            text="D01",
            bbox=(100.0, 20.0, 120.0, 35.0),
            font="Helvetica",
            size=10.0,
            color=0,
            block_no=0,
            line_no=0,
        )

        doors = detect_doors([arc, leaf], [label])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]

        self.assertEqual(1, len(assemblies))
        self.assertEqual(0.85, assemblies[0].confidence)
        self.assertEqual("D01", assemblies[0].evidence["nearby_label"])

    def test_arc_like_clutter_emits_exact_fallback(self) -> None:
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])

        doors = detect_doors([arc], [])

        self.assertEqual(1, len(doors))
        self.assertEqual("arc_fallback", doors[0].evidence["method"])
        self.assertEqual(DOOR_FALLBACK_CONFIDENCE, doors[0].confidence)

    def test_leaf_only_emits_exact_fallback(self) -> None:
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])

        doors = detect_doors([leaf], [])

        self.assertEqual(1, len(doors))
        self.assertEqual("leaf_fallback", doors[0].evidence["method"])
        self.assertEqual(DOOR_FALLBACK_CONFIDENCE, doors[0].confidence)

    def test_duplicate_components_dedupe_to_one_door(self) -> None:
        first = Candidate(
            candidate_id="door_0000",
            entity_type="door",
            bbox=(0.0, 0.0, 80.0, 80.0),
            confidence=0.65,
            evidence={"method": "door_assembly", "component_path_indices": [1, 2, 3]},
        )
        duplicate = Candidate(
            candidate_id="door_0001",
            entity_type="door",
            bbox=(0.0, 0.0, 82.0, 82.0),
            confidence=0.55,
            evidence={"method": "arc_fallback", "component_path_indices": [3, 4]},
        )

        kept = _dedupe_door_components([duplicate, first])

        self.assertEqual(["door_0000"], [c.candidate_id for c in kept])

    def test_assembled_door_without_wall_gets_reduced_penalty(self) -> None:
        door = Candidate(
            candidate_id="door_0000",
            entity_type="door",
            bbox=(0.0, 0.0, 80.0, 80.0),
            confidence=0.65,
            evidence={"method": "door_assembly"},
        )
        far_wall = Candidate(
            candidate_id="wall_0000",
            entity_type="wall",
            bbox=(500.0, 500.0, 600.0, 520.0),
            confidence=0.7,
            evidence={},
        )

        adjusted = _cross_validate([door], [far_wall])

        self.assertEqual(round(0.65 - CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY, 3), adjusted[0].confidence)
        self.assertEqual("no_wall", adjusted[0].evidence["wall_context"])


if __name__ == "__main__":
    unittest.main()
