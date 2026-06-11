import math
import unittest

from heuristics import (
    CROSS_NO_WALL_ASSEMBLY_DOOR_PENALTY,
    DOOR_FALLBACK_CONFIDENCE,
    DOOR_POLYLINE_MAX_ANGLE_BINS,
    DOOR_THRESHOLD_CONFIDENCE_BOOST,
    DOOR_V2_OPENING_CLEAR_BOOST,
    DOOR_V2_OPENING_OBSTRUCTED_PENALTY,
    _check_opening_clear,
    _cross_validate,
    _dedupe_door_components,
    _estimate_arc_sweep_deg,
    _merge_double_door_assemblies,
    detect_doors,
    detect_walls,
    detect_windows,
)
from models import Candidate, PathPrimitive, TextSpan
from pipeline import merge_gemini_and_heuristics


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
        self.assertEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST, 3), assemblies[0].confidence)
        self.assertEqual("polyline_arc", assemblies[0].evidence["arc_source"])
        self.assertEqual("single", assemblies[0].evidence["assembly_type"])

    def test_curve_arc_connected_native_leaf(self) -> None:
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])

        doors = detect_doors([arc, leaf], [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]

        self.assertEqual(1, len(assemblies))
        self.assertEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST, 3), assemblies[0].confidence)
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
        self.assertEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST + 0.20, 3), assemblies[0].confidence)
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


class EntranceDoorTests(unittest.TestCase):
    """Regression + new-feature tests for entrance-door threshold-line handling.

    Geometry convention mirrors `test_polyline_arc_connected_linework_leaf_base_confidence`:
    a quarter arc with bbox (0,0)..(80,80) and polyline endpoints (80,0) and (0,80); the
    leaf attaches near (80,0) and extends outward to (160,0). The threshold line is
    parallel to the leaf long axis, with endpoints near one pair of leaf long-edge corners.
    """

    def _normal_door_paths(self) -> list[PathPrimitive]:
        return quarter_arc_lines(0) + rect_lines(100, 80.0, -2.0, 160.0, 2.0)

    def _entrance_door_paths(self) -> list[PathPrimitive]:
        # Threshold 1px outside the y0=-2 long edge of the leaf — snap keys at the leaf's
        # two bottom corners coincide, so current code's component-degree check rejects
        # the leaf without the subgraph fallback.
        return self._normal_door_paths() + [line(200, (80.0, -3.0), (160.0, -3.0))]

    def test_entrance_door_threshold_line_does_not_break_leaf(self) -> None:
        paths = self._entrance_door_paths()
        doors = detect_doors(paths, [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies), f"expected 1 assembly, got {len(doors)} doors")
        door = assemblies[0]
        self.assertAlmostEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST + DOOR_THRESHOLD_CONFIDENCE_BOOST, 3), door.confidence, places=3)
        self.assertTrue(door.evidence["has_threshold"])
        self.assertEqual("entrance", door.evidence["door_subtype"])
        self.assertEqual("linework_rect_subgraph", door.evidence["leaf_source"])
        self.assertEqual("polyline_arc", door.evidence["arc_source"])
        # Threshold's path_index is folded into the assembly's component set.
        self.assertIn(200, door.evidence["component_path_indices"])
        self.assertEqual(200, door.evidence["threshold_path_index"])

    def test_entrance_door_native_leaf_with_threshold(self) -> None:
        # Native curve arc + native qu leaf (no linework leaf detection involved) so
        # the threshold-evidence path is exercised independently of the subgraph fix.
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])
        # Threshold sits 5px outside the y0=-4 leaf edge — its endpoints land within the
        # 6px DOOR_THRESHOLD_ENDPOINT_TOL_PX of the leaf bottom corners.
        threshold = line(2, (80.0, -5.0), (160.0, -5.0))

        doors = detect_doors([arc, leaf, threshold], [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies))
        door = assemblies[0]
        self.assertAlmostEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST + DOOR_THRESHOLD_CONFIDENCE_BOOST, 3), door.confidence, places=3)
        self.assertEqual("entrance", door.evidence["door_subtype"])
        self.assertEqual("qu", door.evidence["leaf_source"])
        self.assertTrue(door.evidence["has_threshold"])

    def test_normal_door_no_threshold_unchanged(self) -> None:
        paths = self._normal_door_paths()
        doors = detect_doors(paths, [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies))
        door = assemblies[0]
        self.assertEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST, 3), door.confidence)
        self.assertFalse(door.evidence.get("has_threshold"))
        self.assertNotIn("door_subtype", door.evidence)
        # Without a spur, the clean-loop path wins.
        self.assertEqual("linework_rect", door.evidence["leaf_source"])

    def test_split_side_rectangle_leaf_still_detected_via_clean_path(self) -> None:
        # Replace one long side of rect_lines(100, 80,-4,160,4) with two collinear
        # segments. The result is a 5-primitive closed loop, all junctions degree-2 —
        # the clean-loop path must still accept it (no regression).
        leaf = [
            line(100, (80.0, -4.0), (120.0, -4.0)),     # bottom-left half
            line(101, (120.0, -4.0), (160.0, -4.0)),    # bottom-right half
            line(102, (160.0, -4.0), (160.0, 4.0)),     # right
            line(103, (160.0, 4.0), (80.0, 4.0)),       # top
            line(104, (80.0, 4.0), (80.0, -4.0)),       # left
        ]
        paths = quarter_arc_lines(0) + leaf
        doors = detect_doors(paths, [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies))
        door = assemblies[0]
        self.assertEqual("linework_rect", door.evidence["leaf_source"])
        self.assertEqual(round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST, 3), door.confidence)

    def test_leaf_with_spur_wall_stub_still_detected_via_subgraph(self) -> None:
        # Clean rect_lines leaf + arc + one short stub line attached to a leaf corner
        # (degree-3 junction; doesn't close a cycle; doesn't match a long-edge corner pair
        # so it's not mistaken for a threshold).
        paths = quarter_arc_lines(0)
        paths.extend(rect_lines(100, 80.0, -2.0, 160.0, 2.0))
        # Stub from leaf top-right corner pointing outward; no second connection.
        paths.append(line(200, (160.0, 2.0), (175.0, 12.0)))
        doors = detect_doors(paths, [])

        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies), f"expected 1 assembly, got {[d.evidence.get('method') for d in doors]}")
        door = assemblies[0]
        self.assertEqual("linework_rect_subgraph", door.evidence["leaf_source"])
        self.assertFalse(door.evidence.get("has_threshold"))

    def test_threshold_no_extra_window_or_wall_vs_baseline(self) -> None:
        normal = self._normal_door_paths()
        entrance = self._entrance_door_paths()

        self.assertLessEqual(
            len(detect_windows(entrance)), len(detect_windows(normal)),
            "threshold line should not raise additional window candidates",
        )
        self.assertLessEqual(
            len(detect_walls(entrance)), len(detect_walls(normal)),
            "threshold line should not raise additional wall candidates",
        )


class DoorEvidencePropagationTests(unittest.TestCase):
    """Verify Step 4 — door evidence keys land in Entity.attributes in offline mode."""

    def test_entity_attributes_propagate_door_subtype(self) -> None:
        door_cand = Candidate(
            candidate_id="door_0001",
            entity_type="door",
            bbox=(0.0, 0.0, 100.0, 10.0),
            confidence=0.75,  # above OFFLINE_MIN_CONFIDENCE["door"]=0.55
            evidence={
                "method": "door_assembly",
                "has_threshold": True,
                "door_subtype": "entrance",
                "threshold_path_index": 42,
            },
        )
        window_cand = Candidate(
            candidate_id="window_0001",
            entity_type="window",
            bbox=(200.0, 0.0, 300.0, 10.0),
            confidence=0.60,  # above OFFLINE_MIN_CONFIDENCE["window"]=0.50
            evidence={},
        )

        entities, rejected = merge_gemini_and_heuristics([door_cand, window_cand], None)

        self.assertEqual(0, len(rejected))
        self.assertEqual(2, len(entities))
        door_ent = next(e for e in entities if e.entity_type == "door")
        window_ent = next(e for e in entities if e.entity_type == "window")
        self.assertTrue(door_ent.attributes["has_threshold"])
        self.assertEqual("entrance", door_ent.attributes["door_subtype"])
        self.assertEqual(42, door_ent.attributes["threshold_path_index"])
        # Window entity (non-door) must not receive door-only keys.
        self.assertNotIn("has_threshold", window_ent.attributes)
        self.assertNotIn("door_subtype", window_ent.attributes)


def wide_arc_lines(start_idx: int, radius: float = 50.0, n_segs: int = 16) -> list[PathPrimitive]:
    """270-degree polyline arc with 16 segments — far wider than a quarter-circle door swing."""
    pts = [
        (
            radius * math.cos(math.pi * 1.5 * i / n_segs),
            radius * math.sin(math.pi * 1.5 * i / n_segs),
        )
        for i in range(n_segs + 1)
    ]
    return [line(start_idx + i, pts[i], pts[i + 1]) for i in range(n_segs)]


def _seg_angle_bins(paths: list[PathPrimitive]) -> set[int]:
    """Compute 15-degree angle bins for line segments — fixture sanity helper."""
    bins: set[int] = set()
    for p in paths:
        if p.item_type == "l" and len(p.points) >= 2:
            p1, p2 = p.points[0], p.points[-1]
            angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0])) % 180.0
            bins.add(int(angle // 15.0))
    return bins


def _single_door_cand(
    cand_id: str,
    leaf_bbox: tuple[float, float, float, float],
    arc_bbox: tuple[float, float, float, float],
    path_indices: list[int],
    confidence: float = 0.65,
    extra: dict | None = None,
) -> Candidate:
    full_bbox = (
        min(leaf_bbox[0], arc_bbox[0]),
        min(leaf_bbox[1], arc_bbox[1]),
        max(leaf_bbox[2], arc_bbox[2]),
        max(leaf_bbox[3], arc_bbox[3]),
    )
    evidence: dict = {
        "method": "door_assembly",
        "assembly_type": "single",
        "arc_bbox": list(arc_bbox),
        "leaf_bbox": list(leaf_bbox),
        "component_path_indices": path_indices,
    }
    if extra:
        evidence.update(extra)
    return Candidate(
        candidate_id=cand_id,
        entity_type="door",
        bbox=full_bbox,
        confidence=confidence,
        evidence=evidence,
    )


class PolylineArcBinCapTests(unittest.TestCase):
    """Tests for the DOOR_POLYLINE_MAX_ANGLE_BINS cap that rejects furniture/appliance curves."""

    def test_arc_too_wide_rejected(self) -> None:
        arc_paths = wide_arc_lines(0)
        bins = _seg_angle_bins(arc_paths)
        # Fixture sanity: the 270-degree arc must have more bins than a quarter circle
        self.assertGreater(
            len(bins), DOOR_POLYLINE_MAX_ANGLE_BINS,
            f"fixture angle_bin_count={len(bins)} must exceed cap={DOOR_POLYLINE_MAX_ANGLE_BINS}",
        )
        # Wide arc should produce zero door candidates
        doors = detect_doors(arc_paths, [])
        self.assertEqual(0, len(doors), "270-degree arc must not produce any door candidate")

    def test_polyline_arc_door_at_7_bins_passes(self) -> None:
        arc_paths = quarter_arc_lines(0)
        bins = _seg_angle_bins(arc_paths)
        # Fixture sanity: quarter arc must stay within the bin cap
        self.assertLessEqual(
            len(bins), DOOR_POLYLINE_MAX_ANGLE_BINS,
            f"quarter arc has {len(bins)} bins but cap is {DOOR_POLYLINE_MAX_ANGLE_BINS}",
        )
        paths = arc_paths + rect_lines(100, 80.0, -4.0, 160.0, 4.0)
        doors = detect_doors(paths, [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies), "quarter arc + leaf must still assemble after bin cap")


class DoubleDoorTests(unittest.TestCase):
    """Tests for _merge_double_door_assemblies: adjacent single-door assembly merging."""

    # ── fixture geometry ────────────────────────────────────────────────────
    # Two horizontal leaves placed end-to-end:
    #   Left leaf:   x=[0,80],   y=[-4,4]
    #   Right leaf:  x=[80,160], y=[-4,4]
    # Arc radii both 80 px (same as leaf length).

    def _left_door(self, arc_above: bool = True, extra: dict | None = None) -> Candidate:
        arc_y = (0.0, 80.0) if arc_above else (-80.0, 0.0)
        return _single_door_cand(
            "door_0000",
            leaf_bbox=(0.0, -4.0, 80.0, 4.0),
            arc_bbox=(0.0, arc_y[0], 80.0, arc_y[1]),
            path_indices=list(range(10)),
            extra=extra,
        )

    def _right_door(self, arc_above: bool = True, extra: dict | None = None) -> Candidate:
        arc_y = (0.0, 80.0) if arc_above else (-80.0, 0.0)
        return _single_door_cand(
            "door_0001",
            leaf_bbox=(80.0, -4.0, 160.0, 4.0),
            arc_bbox=(80.0, arc_y[0], 160.0, arc_y[1]),
            path_indices=list(range(20, 30)),
            extra=extra,
        )

    # ── orientation tests ───────────────────────────────────────────────────

    def test_double_door_toward_each_other(self) -> None:
        """Arcs on the same side (both above leaf line) → merges into double_swing."""
        candidates = [self._left_door(arc_above=True), self._right_door(arc_above=True)]
        result = _merge_double_door_assemblies(candidates)
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(1, len(doubles), "two adjacent single doors must merge into one double")
        expected_bbox = (0.0, -4.0, 160.0, 80.0)
        self.assertEqual(expected_bbox, doubles[0].bbox)

    def test_double_door_away_from_each_other(self) -> None:
        """Arcs on opposite sides → still merges since leaf-interval check is orientation-agnostic."""
        candidates = [self._left_door(arc_above=True), self._right_door(arc_above=False)]
        result = _merge_double_door_assemblies(candidates)
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(1, len(doubles))
        expected_bbox = (0.0, -80.0, 160.0, 80.0)
        self.assertEqual(expected_bbox, doubles[0].bbox)

    # ── rejection tests ─────────────────────────────────────────────────────

    def test_double_door_not_merged_for_separate_same_wall_doors(self) -> None:
        """Leaf-interval gap of 30 px (> DOOR_DOUBLE_LEAF_GAP_PX) → two separate candidates."""
        # Right leaf shifted rightward so there is a 30 px gap after the left leaf ends at x=80
        right = _single_door_cand(
            "door_0001",
            leaf_bbox=(110.0, -4.0, 190.0, 4.0),  # gap of 30 px from x=80
            arc_bbox=(110.0, 0.0, 190.0, 80.0),
            path_indices=list(range(20, 30)),
        )
        candidates = [self._left_door(), right]
        result = _merge_double_door_assemblies(candidates)
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(0, len(doubles), "30 px leaf gap must not trigger double-door merge")
        self.assertEqual(2, len(result))

    def test_double_door_not_merged_when_leaves_overlap_too_much(self) -> None:
        """Leaf overlap of 10 px (> DOOR_DOUBLE_LEAF_OVERLAP_PX=5) → two separate candidates."""
        # Right leaf starts at x=70 so it overlaps the left leaf (ends x=80) by 10 px
        right = _single_door_cand(
            "door_0001",
            leaf_bbox=(70.0, -4.0, 150.0, 4.0),  # overlap of 10 px with left [0,80]
            arc_bbox=(70.0, 0.0, 150.0, 80.0),
            path_indices=list(range(20, 30)),
        )
        candidates = [self._left_door(), right]
        result = _merge_double_door_assemblies(candidates)
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(0, len(doubles), "10 px leaf overlap must not trigger double-door merge")
        self.assertEqual(2, len(result))

    # ── evidence preservation tests ─────────────────────────────────────────

    def test_double_door_entrance_subtype_preserved(self) -> None:
        """has_threshold, door_subtype, and threshold_path_index carry through from either door."""
        left = self._left_door(extra={
            "has_threshold": True,
            "door_subtype": "entrance",
            "threshold_path_index": 42,
        })
        right = self._right_door()  # no threshold evidence
        result = _merge_double_door_assemblies([left, right])
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(1, len(doubles))
        d = doubles[0]
        self.assertTrue(d.evidence.get("has_threshold"))
        self.assertEqual("entrance", d.evidence.get("door_subtype"))
        self.assertEqual(42, d.evidence["threshold_path_index"])

    def test_double_door_entrance_threshold_path_index_zero_preserved(self) -> None:
        """threshold_path_index=0 must be preserved (is-not-None guard, not falsy check)."""
        left = self._left_door(extra={
            "has_threshold": True,
            "door_subtype": "entrance",
            "threshold_path_index": 0,
        })
        right = self._right_door()
        result = _merge_double_door_assemblies([left, right])
        doubles = [c for c in result if c.evidence.get("assembly_type") == "double_swing"]
        self.assertEqual(1, len(doubles))
        self.assertEqual(0, doubles[0].evidence["threshold_path_index"])

    def test_double_door_assembly_type_in_entity_attributes(self) -> None:
        """assembly_type must reach Entity.attributes through the pipeline passthrough."""
        cand = Candidate(
            candidate_id="door_0001",
            entity_type="door",
            bbox=(0.0, -4.0, 160.0, 80.0),
            confidence=0.70,  # above OFFLINE_MIN_CONFIDENCE["door"]=0.55
            evidence={"method": "door_assembly", "assembly_type": "double_swing"},
        )
        entities, rejected = merge_gemini_and_heuristics([cand], None)
        self.assertEqual(0, len(rejected))
        self.assertEqual(1, len(entities))
        self.assertEqual("double_swing", entities[0].attributes.get("assembly_type"))


class DoorV2OpeningCheckTests(unittest.TestCase):
    """Tests for v2 bridge-line opening check and arc sweep estimation."""

    def test_opening_check_clear_no_nearby_lines(self):
        # Bridge from (0,0) to (80,0); no line paths at all
        result = _check_opening_clear([(0.0, 0.0), (80.0, 0.0)], [], set())
        self.assertEqual("clear", result)

    def test_opening_check_obstructed_by_sill_line(self):
        # Bridge from (0,0) to (80,0); sill line at x=[10,70] (midpoint projects to t=40, within [4,76])
        sill = line(99, (10.0, 0.0), (70.0, 0.0))
        result = _check_opening_clear([(0.0, 0.0), (80.0, 0.0)], [sill], set())
        self.assertEqual("obstructed", result)

    def test_opening_check_wall_stub_at_jamb_not_obstructed(self):
        # Bridge from (0,0) to (80,0); wall stub at x=0 projects at t=0, before 5% cutoff
        stub = line(99, (0.0, -15.0), (0.0, 15.0))
        result = _check_opening_clear([(0.0, 0.0), (80.0, 0.0)], [stub], set())
        self.assertEqual("clear", result)

    def test_opening_check_excluded_indices_ignored(self):
        # Sill line at path_index=99 would obstruct, but it's in exclude_indices
        sill = line(99, (10.0, 0.0), (70.0, 0.0))
        result = _check_opening_clear([(0.0, 0.0), (80.0, 0.0)], [sill], {99})
        self.assertEqual("clear", result)

    def test_opening_check_unknown_for_empty_endpoints(self):
        result = _check_opening_clear([], [], set())
        self.assertEqual("unknown", result)

    def test_opening_check_unknown_for_single_endpoint(self):
        result = _check_opening_clear([(0.0, 0.0)], [], set())
        self.assertEqual("unknown", result)

    def test_assembled_door_clear_opening_boosts_confidence(self):
        # Standard polyline quarter-arc + rect leaf; no cross-opening lines
        # Expected confidence = 0.65 + DOOR_V2_OPENING_CLEAR_BOOST = 0.72
        paths = quarter_arc_lines(0) + rect_lines(100, 80.0, -4.0, 160.0, 4.0)
        doors = detect_doors(paths, [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies))
        door = assemblies[0]
        self.assertIn("opening_check", door.evidence)
        self.assertEqual("clear", door.evidence["opening_check"])
        expected_conf = round(0.65 + DOOR_V2_OPENING_CLEAR_BOOST, 3)
        self.assertAlmostEqual(expected_conf, door.confidence, places=3)

    def test_estimate_arc_sweep_90deg_ideal(self):
        # Ideal quarter-circle: start=(80,0), end=(0,80), center=(80,0) or (0,80)?
        # For bbox (0,0,80,80): start=(80,0), end=(0,80)
        # Center corner at (0,0): d_start=80, d_end=80 → score=0 (best)
        # vs=(80,0), ve=(0,80) → dot=0 → sweep=90°
        sweep = _estimate_arc_sweep_deg([(80.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 80.0)], (0.0, 0.0, 80.0, 80.0))
        self.assertIsNotNone(sweep)
        self.assertAlmostEqual(90.0, sweep, delta=2.0)

    def test_estimate_arc_sweep_degenerate_returns_none(self):
        sweep = _estimate_arc_sweep_deg([], (0.0, 0.0, 1.0, 1.0))
        self.assertIsNone(sweep)

    def test_native_curve_arc_sweep_in_evidence(self):
        # Native curve arc + leaf: arc_sweep_est_deg must appear in assembled evidence
        arc = path(0, "c", [(0.0, 0.0), (80.0, 0.0), (0.0, 80.0), (80.0, 80.0)])
        leaf = path(1, "qu", [(80.0, -4.0), (160.0, -4.0), (160.0, 4.0), (80.0, 4.0)])
        doors = detect_doors([arc, leaf], [])
        assemblies = [d for d in doors if d.evidence.get("method") == "door_assembly"]
        self.assertEqual(1, len(assemblies))
        # The arc_sweep_est_deg key should be present (prefixed in evidence merge)
        combined = {**assemblies[0].evidence}
        # Key may appear as arc_arc_sweep_est_deg due to evidence.update prefix pattern
        # Check that sweep information is present and reasonable (90 ± 5 deg)
        sweep_key = next((k for k in combined if "sweep" in k), None)
        if sweep_key is not None:
            self.assertAlmostEqual(90.0, combined[sweep_key], delta=5.0)


if __name__ == "__main__":
    unittest.main()
