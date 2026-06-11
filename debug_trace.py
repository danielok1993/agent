from __future__ import annotations
from typing import Optional
from models import PathPrimitive


class DebugTraceCollector:
    """Accumulates per-primitive and per-component trace data during door detection.

    Pass an instance to heuristics functions via the collector= kwarg.
    When collector is None the production path runs with zero overhead.
    """

    def __init__(self, page_number: int) -> None:
        self.page_number = page_number
        self._primitives: dict[int, dict] = {}
        self._polyline_components: list[dict] = []
        self._linework_components: list[dict] = []
        self._swings: dict[str, dict] = {}
        self._leaves: dict[str, dict] = {}
        self._candidates: list[dict] = []
        self._swing_idx = 0
        self._leaf_idx = 0
        self._poly_idx = 0
        self._linework_idx = 0

    # ------------------------------------------------------------------ init

    def init_primitives(self, paths: list[PathPrimitive]) -> None:
        """Pre-populate by_path_index with raw metadata for every PathPrimitive."""
        for p in paths:
            self._entry(p)

    def _entry(self, path: PathPrimitive) -> dict:
        idx = path.path_index
        if idx not in self._primitives:
            self._primitives[idx] = {
                "path_index": idx,
                "item_type": path.item_type,
                "bbox": list(path.bbox),
                "layer": path.layer,
                "stroke_width": round(path.stroke_width, 3),
                "color": list(path.color) if path.color else None,
                "arc_filter": None,
                "polyline_eval": None,
                "linework_component_id": None,
                "leaf_filter": None,
                "swing_id": None,
                "leaf_id": None,
                "polyline_component_id": None,
                "candidate_id": None,
            }
        return self._primitives[idx]

    # ------------------------------------------------------------------ arc filter

    def record_arc_filter(
        self,
        path: PathPrimitive,
        passed: bool,
        fail_reason: Optional[str],
        aspect_ratio: Optional[float] = None,
        size_px: Optional[float] = None,
    ) -> None:
        """Record result of the _is_arc_like check for a primitive."""
        entry = self._entry(path)
        is_curve = path.item_type == "c"
        checks: dict = {
            "item_type": {"required": "c", "actual": path.item_type, "passed": is_curve},
        }
        if is_curve:
            checks["aspect_ratio"] = {
                "value": round(aspect_ratio, 4) if aspect_ratio is not None else None,
                "range": [0.85, 1.15],
                "passed": aspect_ratio is not None and 0.85 <= aspect_ratio <= 1.15,
            }
            checks["size_px"] = {
                "value": round(size_px, 2) if size_px is not None else None,
                "range": [20.0, 200.0],
                "passed": size_px is not None and 20.0 <= size_px <= 200.0,
            }
        entry["arc_filter"] = {
            "evaluated": is_curve,
            "passed": passed,
            "fail_reason": fail_reason,
            "checks": checks,
        }

    # ------------------------------------------------------------------ polyline eval

    def record_polyline_length(
        self,
        path: PathPrimitive,
        length: float,
        passed: bool,
        fail_reason: Optional[str] = None,
    ) -> None:
        """Record whether a line segment passed the polyline-arc length filter."""
        entry = self._entry(path)
        entry["polyline_eval"] = {
            "evaluated": True,
            "length_px": round(length, 2),
            "length_range": [2.0, 18.0],
            "passed_length_filter": passed,
            "fail_reason": fail_reason,
            "polyline_component_id": None,
        }

    def record_polyline_component(
        self,
        path_indices: list[int],
        result: str,
        fail_reason: Optional[str],
        checks: dict,
    ) -> str:
        """Record a polyline arc component evaluation. Returns component_id."""
        component_id = f"polyline_{self._poly_idx}"
        self._poly_idx += 1
        self._polyline_components.append({
            "component_id": component_id,
            "path_indices": sorted(path_indices),
            "result": result,
            "fail_reason": fail_reason,
            "checks": checks,
            "swing_id": None,
        })
        for pi in path_indices:
            if pi in self._primitives:
                entry = self._primitives[pi]
                entry["polyline_component_id"] = component_id
                if entry["polyline_eval"] is not None:
                    entry["polyline_eval"]["polyline_component_id"] = component_id
        return component_id

    def link_polyline_swing(self, component_id: str, swing_id: str) -> None:
        for comp in self._polyline_components:
            if comp["component_id"] == component_id:
                comp["swing_id"] = swing_id
                return

    def reject_polyline_component(self, component_id: str, fail_reason: str) -> None:
        """Mark a previously-collected polyline component as rejected post-hoc."""
        for comp in self._polyline_components:
            if comp["component_id"] == component_id:
                comp["result"] = "rejected"
                comp["fail_reason"] = fail_reason
                comp["checks"]["overlaps_native_arc"] = {"overlaps": True, "passed": False}
                return

    # ------------------------------------------------------------------ linework leaf components

    def record_linework_component(
        self,
        path_indices: list[int],
        result: str,
        path_used: Optional[str],
        fail_reason: Optional[str],
        clean_loop_result: Optional[dict],
        subgraph_result: Optional[dict],
    ) -> str:
        """Record a linework leaf component evaluation. Returns component_id.

        clean_loop_result and subgraph_result each contain:
          { tried, passed, fail_reason, checks }
        where checks holds per-check { value, bound/range, passed } dicts.
        """
        component_id = f"linework_{self._linework_idx}"
        self._linework_idx += 1
        self._linework_components.append({
            "component_id": component_id,
            "path_indices": sorted(path_indices),
            "result": result,
            "path_used": path_used,
            "fail_reason": fail_reason,
            "clean_loop_result": clean_loop_result,
            "subgraph_result": subgraph_result,
            "leaf_id": None,
        })
        for pi in path_indices:
            if pi in self._primitives:
                self._primitives[pi]["linework_component_id"] = component_id
        return component_id

    def link_linework_leaf(self, component_id: str, leaf_id: str) -> None:
        for comp in self._linework_components:
            if comp["component_id"] == component_id:
                comp["leaf_id"] = leaf_id
                return

    # ------------------------------------------------------------------ leaf filter

    def record_leaf_filter(
        self,
        path: PathPrimitive,
        passed: bool,
        fail_reason: Optional[str],
        aspect_ratio: Optional[float] = None,
        size_px: Optional[float] = None,
    ) -> None:
        """Record result of the _is_door_leaf check for a primitive."""
        entry = self._entry(path)
        is_rect = path.item_type in ("re", "qu")
        checks: dict = {
            "item_type": {"required": ["re", "qu"], "actual": path.item_type, "passed": is_rect},
        }
        if is_rect:
            checks["aspect_ratio"] = {
                "value": round(aspect_ratio, 4) if aspect_ratio is not None else None,
                "min": 4.0,
                "passed": aspect_ratio is not None and aspect_ratio >= 4.0,
            }
            checks["size_px"] = {
                "value": round(size_px, 2) if size_px is not None else None,
                "range": [20.0, 200.0],
                "passed": size_px is not None and 20.0 <= size_px <= 200.0,
            }
        entry["leaf_filter"] = {
            "evaluated": is_rect,
            "passed": passed,
            "fail_reason": fail_reason,
            "checks": checks,
        }

    # ------------------------------------------------------------------ swings

    def record_swing(
        self,
        source: str,
        path_indices: list[int],
        radius_px: float,
        sweep_est_deg: Optional[float],
        layer: Optional[str],
        layer_hint: bool,
        polyline_component_id: Optional[str] = None,
    ) -> str:
        """Register a collected swing. Returns swing_id."""
        swing_id = f"swing_{self._swing_idx}"
        self._swing_idx += 1
        self._swings[swing_id] = {
            "swing_id": swing_id,
            "source": source,
            "path_indices": sorted(path_indices),
            "radius_px": round(radius_px, 2),
            "sweep_est_deg": round(sweep_est_deg, 1) if sweep_est_deg is not None else None,
            "layer": layer,
            "layer_hint": layer_hint,
            "paired": False,
            "candidate_id": None,
            "hu_eval": None,
            "pairing_attempts": [],
        }
        for pi in path_indices:
            if pi in self._primitives:
                self._primitives[pi]["swing_id"] = swing_id
        if polyline_component_id:
            self.link_polyline_swing(polyline_component_id, swing_id)
        return swing_id

    def record_pairing_attempt(
        self,
        swing_id: str,
        leaf_id: str,
        distance_px: float,
        distance_bound: float,
        radius_ratio: float,
        radius_ratio_bound: float,
        result: str,
        fail_reason: Optional[str] = None,
    ) -> None:
        if swing_id in self._swings:
            self._swings[swing_id]["pairing_attempts"].append({
                "leaf_id": leaf_id,
                "distance_px": round(distance_px, 2),
                "distance_bound": distance_bound,
                "radius_ratio": round(radius_ratio, 4),
                "radius_ratio_bound": radius_ratio_bound,
                "result": result,
                "fail_reason": fail_reason,
            })

    def record_hu_eval(
        self,
        swing_id: str,
        distance: Optional[float],
        threshold_verified: float,
        threshold_far: float,
        result: str,
        boost_applied: float,
        base_confidence: float,
        final_confidence: float,
    ) -> None:
        if swing_id in self._swings:
            self._swings[swing_id]["hu_eval"] = {
                "distance": round(distance, 4) if distance is not None else None,
                "threshold_verified": threshold_verified,
                "threshold_far": threshold_far,
                "result": result,
                "boost_applied": round(boost_applied, 4),
                "base_confidence": round(base_confidence, 4),
                "final_confidence": round(final_confidence, 4),
            }

    # ------------------------------------------------------------------ leaves

    def record_leaf(
        self,
        source: str,
        path_indices: list[int],
        length_px: float,
        width_px: float,
        layer: Optional[str],
        layer_hint: bool,
        linework_component_id: Optional[str] = None,
        linework_eval: Optional[dict] = None,
    ) -> str:
        """Register a collected leaf. Returns leaf_id."""
        leaf_id = f"leaf_{self._leaf_idx}"
        self._leaf_idx += 1
        self._leaves[leaf_id] = {
            "leaf_id": leaf_id,
            "source": source,
            "path_indices": sorted(path_indices),
            "length_px": round(length_px, 2),
            "width_px": round(width_px, 2),
            "aspect_ratio": round(length_px / width_px, 3) if width_px > 1e-6 else None,
            "layer": layer,
            "layer_hint": layer_hint,
            "paired": False,
            "candidate_id": None,
            "linework_eval": linework_eval,
        }
        for pi in path_indices:
            if pi in self._primitives:
                self._primitives[pi]["leaf_id"] = leaf_id
        if linework_component_id:
            self.link_linework_leaf(linework_component_id, leaf_id)
        return leaf_id

    def record_leaf_paired(self, leaf_id: str, candidate_id: str) -> None:
        if leaf_id in self._leaves:
            self._leaves[leaf_id]["paired"] = True
            self._leaves[leaf_id]["candidate_id"] = candidate_id

    # ------------------------------------------------------------------ candidates

    def record_candidate(
        self,
        candidate_id: str,
        method: str,
        confidence: float,
        confidence_breakdown: dict,
        swing_id: Optional[str],
        leaf_id: Optional[str],
    ) -> None:
        """Record a final candidate with its full confidence breakdown."""
        self._candidates.append({
            "candidate_id": candidate_id,
            "method": method,
            "confidence": round(confidence, 4),
            "confidence_breakdown": confidence_breakdown,
            "swing_id": swing_id,
            "leaf_id": leaf_id,
        })
        if swing_id and swing_id in self._swings:
            self._swings[swing_id]["paired"] = True
            self._swings[swing_id]["candidate_id"] = candidate_id
            for pi in self._swings[swing_id]["path_indices"]:
                if pi in self._primitives:
                    self._primitives[pi]["candidate_id"] = candidate_id
        if leaf_id and leaf_id in self._leaves:
            self.record_leaf_paired(leaf_id, candidate_id)
            for pi in self._leaves[leaf_id]["path_indices"]:
                if pi in self._primitives:
                    self._primitives[pi]["candidate_id"] = candidate_id

    # ------------------------------------------------------------------ serialization

    def to_dict(self) -> dict:
        swings = list(self._swings.values())
        leaves = list(self._leaves.values())

        return {
            "page_number": self.page_number,
            "by_path_index": {
                str(k): v for k, v in sorted(self._primitives.items())
            },
            "polyline_components": self._polyline_components,
            "linework_components": self._linework_components,
            "swings": swings,
            "leaves": leaves,
            "candidates": self._candidates,
            "summary": {
                "total_path_primitives": len(self._primitives),
                "arc_filter_evaluated": sum(
                    1 for p in self._primitives.values()
                    if p["arc_filter"] and p["arc_filter"]["evaluated"]
                ),
                "arc_filter_passed": sum(
                    1 for p in self._primitives.values()
                    if p["arc_filter"] and p["arc_filter"]["passed"]
                ),
                "polyline_segments_in_range": sum(
                    1 for p in self._primitives.values()
                    if p["polyline_eval"] and p["polyline_eval"]["passed_length_filter"]
                ),
                "polyline_components_found": len(self._polyline_components),
                "polyline_components_collected": sum(
                    1 for c in self._polyline_components if c["result"] == "collected"
                ),
                "linework_components_found": len(self._linework_components),
                "linework_components_collected": sum(
                    1 for c in self._linework_components if c["result"] == "collected"
                ),
                "leaf_filter_evaluated": sum(
                    1 for p in self._primitives.values()
                    if p["leaf_filter"] and p["leaf_filter"]["evaluated"]
                ),
                "leaf_filter_passed": sum(
                    1 for p in self._primitives.values()
                    if p["leaf_filter"] and p["leaf_filter"]["passed"]
                ),
                "swings_total": len(swings),
                "leaves_total": len(leaves),
                "pairing_attempts_total": sum(len(s["pairing_attempts"]) for s in swings),
                "pairs_formed": sum(1 for c in self._candidates if c["method"] == "door_assembly"),
                "arc_fallbacks": sum(
                    1 for c in self._candidates if c["method"] == "arc_fallback"
                ),
                "leaf_fallbacks": sum(
                    1 for c in self._candidates if c["method"] == "leaf_fallback"
                ),
                "candidates_total": len(self._candidates),
            },
        }
