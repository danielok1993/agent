# Polyline-Arc Spur Pruning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover two doors currently missed on `5-1133-WD03.pdf` page 1 by pruning short graph-leaf appendages (door stops, cap lines) from polyline-arc connected components before geometric scoring runs.

**Architecture:** Add a graph-pruning helper `_prune_arc_spurs` to `heuristics.py` that iteratively removes short walks from degree-1 vertices to the first degree-3+ junction. Call it inside `_detect_polyline_arc_bboxes` between connected-component discovery and the existing axis/angle-bin checks. Persist pre/post counts and removed indices through the debug trace so the change is auditable.

**Tech Stack:** Python, `unittest`, PyMuPDF (transitively, via the existing PathPrimitive model). No new dependencies.

**Spec:** `docs/superpowers/specs/2026-06-16-polyline-arc-spur-pruning-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `heuristics.py` | Modify | Add constant, helper, and wire it into `_detect_polyline_arc_bboxes` |
| `debug_trace.py` | Modify | Extend `record_polyline_component` signature with two optional kwargs |
| `tests/test_polyline_arc_pruning.py` | Create | Unit tests for `_prune_arc_spurs` (6 cases) |

---

### Task 1: Add `_prune_arc_spurs` skeleton + clean-arc and pure-cycle tests

This task adds the constant and a no-op helper. Tests 1 and 6 (clean arc, pure cycle) both express "no pruning should happen" — they pass against the no-op implementation. The real pruning logic lands in Task 2.

**Files:**
- Modify: `heuristics.py` — constants block (~line 32) and below `_detect_polyline_arc_bboxes` (after line ~558)
- Create: `tests/test_polyline_arc_pruning.py`

- [ ] **Step 1: Add the spur-segments constant**

In `heuristics.py`, add right after line 32 (`DOOR_POLYLINE_ENDPOINT_TOL = 2.0`):

```python
DOOR_POLYLINE_SPUR_MAX_SEGMENTS = 4   # max chain length (segments) of a leaf-spur that gets pruned from an arc component
```

- [ ] **Step 2: Add the no-op helper**

In `heuristics.py`, immediately above `def _detect_polyline_arc_bboxes(` (line 395), insert:

```python
def _prune_arc_spurs(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
) -> tuple[list[int], set[int]]:
    """Remove short leaf-spurs (door stops, cap lines) from an arc component.

    A clean door-arc connected component is a simple chain: two degree-1
    endpoints, all interior vertices degree-2. A polluted arc is that chain
    plus a short tail of axis-aligned segments hanging off the arc's
    endpoint, joined through a degree-3+ junction. This walk-and-prune step
    iteratively removes those tails so the existing axis_like_fraction and
    angle_bin_count checks see only the arc itself.

    Returns (pruned_component, removed_seg_path_indices). If pruning would
    drop |component| below DOOR_POLYLINE_MIN_SEGMENTS, returns the original
    component and an empty set.
    """
    return list(component), set()
```

- [ ] **Step 3: Create the test file with clean-arc and pure-cycle tests**

Create `tests/test_polyline_arc_pruning.py`:

```python
import math
import unittest

from heuristics import (
    DOOR_POLYLINE_MIN_SEGMENTS,
    DOOR_POLYLINE_SPUR_MAX_SEGMENTS,
    _prune_arc_spurs,
)
from models import PathPrimitive


def _seg(idx: int, p1: tuple[float, float], p2: tuple[float, float]):
    """Build one (PathPrimitive, p1, p2, length, angle) tuple shaped like
    the segs entries inside _detect_polyline_arc_bboxes."""
    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0])) % 180.0
    path = PathPrimitive(
        path_index=idx,
        item_type="l",
        bbox=(min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])),
        color=None,
        fill=None,
        stroke_width=1.0,
        dashes="",
        layer=None,
        points=[p1, p2],
    )
    return (path, p1, p2, length, angle)


def _arc(start_idx: int, n_segs: int, radius: float = 50.0):
    """Quarter-circle polyline as n_segs short straight lines."""
    pts = [
        (
            radius * math.cos((math.pi / 2) * i / n_segs),
            radius * math.sin((math.pi / 2) * i / n_segs),
        )
        for i in range(n_segs + 1)
    ]
    return [_seg(start_idx + i, pts[i], pts[i + 1]) for i in range(n_segs)]


def _chain(start_idx: int, points: list[tuple[float, float]]):
    """Polyline through the given points: segs from points[0]→points[1] etc."""
    return [
        _seg(start_idx + i, points[i], points[i + 1])
        for i in range(len(points) - 1)
    ]


class PruneArcSpursTests(unittest.TestCase):
    def test_clean_arc_unchanged(self) -> None:
        """An 11-segment polyline arc has two degree-1 endpoints and no
        junction — nothing is prunable."""
        segs = _arc(0, n_segs=11)
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)

    def test_pure_cycle_unchanged(self) -> None:
        """A closed 4-segment loop has every vertex at degree 2 — no leaf
        exists to walk from, so nothing is pruned."""
        # Square loop: (0,0)→(50,0)→(50,50)→(0,50)→(0,0)
        segs = _chain(0, [(0.0, 0.0), (50.0, 0.0), (50.0, 50.0), (0.0, 50.0), (0.0, 0.0)])
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Run the tests and verify both pass against the no-op helper**

Run: `python -m unittest tests.test_polyline_arc_pruning -v`
Expected:
```
test_clean_arc_unchanged ... ok
test_pure_cycle_unchanged ... ok
```

- [ ] **Step 5: Run the existing test suite to verify nothing else broke**

Run: `python -m unittest discover tests -v`
Expected: all pre-existing tests pass (the constant and unused helper are inert).

- [ ] **Step 6: Commit**

```bash
git add heuristics.py tests/test_polyline_arc_pruning.py
git commit -m "feat: add _prune_arc_spurs skeleton with no-op behavior

Constant DOOR_POLYLINE_SPUR_MAX_SEGMENTS and the helper signature.
Tests cover the cases where pruning must not change the component:
a clean 11-segment arc (no junction) and a pure 4-segment cycle (no
degree-1 vertex). Pruning logic lands in the next commit."
```

---

### Task 2: Implement Y-junction spur pruning

Adds the walk-and-drop logic. The test creates an 11-seg arc whose far endpoint is a degree-3 **junction** because two short branches attach there. Both branches are spurs and should be pruned, leaving only the 11 arc segments.

Important geometric note: a single linear branch attached at an arc's endpoint only makes the endpoint degree-2 — that's a chain extension, not a spur, and the helper correctly leaves it alone. A *junction* requires at least two extra segments meeting at the same vertex (degree ≥ 3). Door stops and hinge caps naturally produce junctions because they're drawn as multi-edge clusters.

**Files:**
- Modify: `heuristics.py` — body of `_prune_arc_spurs`
- Modify: `tests/test_polyline_arc_pruning.py` — add `test_short_branches_at_y_junction_removed`

- [ ] **Step 1: Add the failing test**

In `tests/test_polyline_arc_pruning.py`, inside `PruneArcSpursTests`, append:

```python
    def test_short_branches_at_y_junction_removed(self) -> None:
        """11-segment arc whose far endpoint is a degree-3 junction because
        two 1-segment branches connect there. Both branches are short spurs
        and should be pruned, leaving the 11 arc segments."""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Arc's far endpoint: (radius*cos(pi/2), radius*sin(pi/2)) = (0, 50).
        # Two 1-seg branches off that vertex make it degree-3.
        branch_a = _chain(100, [(0.0, 50.0), (-3.0, 53.0)])
        branch_b = _chain(200, [(0.0, 50.0), (3.0, 53.0)])
        segs = arc + branch_a + branch_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # 11 arc segs (path indices 0..10) survive; both branch segs pruned.
        self.assertEqual(list(range(11)), pruned)
        self.assertEqual({100, 200}, removed)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m unittest tests.test_polyline_arc_pruning.PruneArcSpursTests.test_short_branches_at_y_junction_removed -v`
Expected: FAIL — the no-op helper returns the full 13-seg component, but the assertion expects 11.

- [ ] **Step 3: Replace the helper body with the real implementation**

Replace the entire body of `_prune_arc_spurs` in `heuristics.py` (everything after the docstring and before the function's `return` line) with:

```python
    def snap_key(point: tuple[float, float]) -> tuple[int, int]:
        return (
            round(point[0] / DOOR_POLYLINE_ENDPOINT_TOL),
            round(point[1] / DOOR_POLYLINE_ENDPOINT_TOL),
        )

    current = list(component)
    removed_path_indices: set[int] = set()

    while True:
        if len(current) < DOOR_POLYLINE_MIN_SEGMENTS:
            break

        # Build vertex → local-seg-indices map on the current subset.
        endpoint_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
        for local_idx, seg_idx in enumerate(current):
            _, p1, p2, _, _ = segs[seg_idx]
            endpoint_buckets[snap_key(p1)].append(local_idx)
            endpoint_buckets[snap_key(p2)].append(local_idx)

        leaves = [pt for pt, lis in endpoint_buckets.items() if len(lis) == 1]
        if not leaves:
            break  # pure cycle — no spurs to prune

        spur_locals: set[int] = set()
        for leaf in leaves:
            walked: list[int] = []
            visited_vertices: set[tuple[int, int]] = {leaf}
            current_vertex = leaf
            prev_local = -1

            while True:
                neighbours = endpoint_buckets.get(current_vertex, [])
                if current_vertex != leaf and len(neighbours) > 2:
                    break  # hit a junction — spur ends here, candidate for prune
                if current_vertex != leaf and len(neighbours) == 1:
                    # Walked all the way to another leaf — component is a
                    # single open chain, nothing to prune.
                    walked = []
                    break

                next_local = next(
                    (n for n in neighbours if n != prev_local),
                    None,
                )
                if next_local is None:
                    walked = []
                    break

                walked.append(next_local)
                if len(walked) > DOOR_POLYLINE_SPUR_MAX_SEGMENTS:
                    walked = []  # too long to count as a spur
                    break

                _, p1, p2, _, _ = segs[current[next_local]]
                k1, k2 = snap_key(p1), snap_key(p2)
                next_vertex = k2 if k1 == current_vertex else k1

                if next_vertex in visited_vertices:
                    walked = []  # cycle — abort this walk
                    break

                visited_vertices.add(next_vertex)
                prev_local = next_local
                current_vertex = next_vertex

            if walked:
                spur_locals.update(walked)

        if not spur_locals:
            break
        if len(current) - len(spur_locals) < DOOR_POLYLINE_MIN_SEGMENTS:
            break

        new_current: list[int] = []
        for local_idx, seg_idx in enumerate(current):
            if local_idx in spur_locals:
                removed_path_indices.add(segs[seg_idx][0].path_index)
            else:
                new_current.append(seg_idx)
        current = new_current

    return current, removed_path_indices
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m unittest tests.test_polyline_arc_pruning.PruneArcSpursTests.test_short_branches_at_y_junction_removed -v`
Expected: PASS.

- [ ] **Step 5: Re-run the rest of the test module**

Run: `python -m unittest tests.test_polyline_arc_pruning -v`
Expected: all three tests pass (clean arc still unchanged, pure cycle still unchanged, Y-junction branches now pruned).

- [ ] **Step 6: Run the whole project test suite**

Run: `python -m unittest discover tests -v`
Expected: every test passes — the helper isn't wired into `_detect_polyline_arc_bboxes` yet, so existing door-assembly behavior is unchanged.

- [ ] **Step 7: Commit**

```bash
git add heuristics.py tests/test_polyline_arc_pruning.py
git commit -m "feat: implement _prune_arc_spurs leaf-walk pruning

Iteratively finds degree-1 vertices, walks through degree-2 vertices
to the first junction, and drops walks of length
<=DOOR_POLYLINE_SPUR_MAX_SEGMENTS. Stops when a pass marks nothing or
when the floor (DOOR_POLYLINE_MIN_SEGMENTS) would be breached."
```

---

### Task 3: Cover multi-spur, oversized, and floor cases

Three more tests exercise the rest of the contract. They validate the actual behavior on the linework_1318 shape (dual spurs), refuse to prune oversized "spurs", and refuse to prune when the floor would be breached.

**Files:**
- Modify: `tests/test_polyline_arc_pruning.py`

- [ ] **Step 1: Add `test_dual_spurs_at_one_junction`**

Append to `PruneArcSpursTests`:

```python
    def test_dual_spurs_at_one_junction(self) -> None:
        """linework_1318 shape: 11-segment arc whose far endpoint becomes a
        degree-3+ junction because two 2-segment spurs branch off it. Both
        spurs (4 segments total) should be pruned."""
        arc = _arc(0, n_segs=11, radius=50.0)
        # Arc's far endpoint is (0, 50). Branch two spurs.
        spur_a = _chain(100, [(0.0, 50.0), (-5.0, 55.0), (-10.0, 60.0)])
        spur_b = _chain(200, [(0.0, 50.0), (5.0, 55.0), (10.0, 60.0)])
        segs = arc + spur_a + spur_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        self.assertEqual(list(range(11)), pruned)
        self.assertEqual({100, 101, 200, 201}, removed)
```

Run: `python -m unittest tests.test_polyline_arc_pruning.PruneArcSpursTests.test_dual_spurs_at_one_junction -v`
Expected: PASS (the helper's spur loop handles each leaf independently and unions the results).

- [ ] **Step 2: Add `test_oversized_branch_kept_at_y_junction`**

Append:

```python
    def test_oversized_branch_kept_at_y_junction(self) -> None:
        """A Y-junction with one short branch (2 segs) and one long branch
        (5 segs, > DOOR_POLYLINE_SPUR_MAX_SEGMENTS). The short branch is
        pruned; the long branch's walk exceeds the spur cap and is kept.
        After short-branch removal, the junction collapses to degree 2 and
        the long branch becomes a chain extension of the arc."""
        arc = _arc(0, n_segs=11, radius=50.0)
        short = _chain(100, [(0.0, 50.0), (-3.0, 53.0), (-6.0, 56.0)])  # 2 segs
        long = _chain(200, [
            (0.0, 50.0), (5.0, 55.0), (10.0, 60.0),
            (15.0, 65.0), (20.0, 70.0), (25.0, 75.0),
        ])  # 5 segs, > DOOR_POLYLINE_SPUR_MAX_SEGMENTS
        segs = arc + short + long
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # Guard against constant drift so the test stays meaningful.
        self.assertEqual(DOOR_POLYLINE_SPUR_MAX_SEGMENTS, 4)
        # 11 arc + 5 long-branch segs survive; both short-branch segs removed.
        self.assertEqual(11 + 5, len(pruned))
        self.assertEqual({100, 101}, removed)
```

Run: `python -m unittest tests.test_polyline_arc_pruning.PruneArcSpursTests.test_oversized_branch_kept_at_y_junction -v`
Expected: PASS (the helper aborts the long-branch walk once `len(walked) > DOOR_POLYLINE_SPUR_MAX_SEGMENTS`, marks only the short branch, and the second iteration leaves the now-deg-2 chain alone).

- [ ] **Step 3: Add `test_pruning_floor_protects_minimum`**

Append:

```python
    def test_pruning_floor_protects_minimum(self) -> None:
        """A small Y-junction component where every walk fits in the spur
        cap. Pruning all marked walks would drop |component| below
        DOOR_POLYLINE_MIN_SEGMENTS, so the helper must back off and return
        the component unchanged."""
        # 2-segment main chain (0,0)→(10,0)→(10,10) plus two 1-segment
        # branches at (10,10), making it a degree-3 junction. 4 segs total.
        main = _chain(0, [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)])
        branch_a = _chain(100, [(10.0, 10.0), (15.0, 10.0)])
        branch_b = _chain(200, [(10.0, 10.0), (10.0, 15.0)])
        segs = main + branch_a + branch_b
        component = list(range(len(segs)))

        pruned, removed = _prune_arc_spurs(component, segs)

        # All three leaf-walks (main 2 segs, each branch 1 seg) are within
        # the spur cap. Marking all 4 would drop the component to 0 segs,
        # well below DOOR_POLYLINE_MIN_SEGMENTS=4 → floor abort, no prune.
        self.assertEqual(DOOR_POLYLINE_MIN_SEGMENTS, 4)  # guard against constant drift
        self.assertEqual(component, pruned)
        self.assertEqual(set(), removed)
```

Run: `python -m unittest tests.test_polyline_arc_pruning.PruneArcSpursTests.test_pruning_floor_protects_minimum -v`
Expected: PASS (the helper's `if len(current) - len(spur_locals) < DOOR_POLYLINE_MIN_SEGMENTS: break` clause fires).

- [ ] **Step 4: Run the full pruning suite once more**

Run: `python -m unittest tests.test_polyline_arc_pruning -v`
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_polyline_arc_pruning.py
git commit -m "test: cover multi-spur, oversized-spur, and floor cases

Three more cases for _prune_arc_spurs covering the actual linework_1318
shape, the oversized-spur cutoff, and the DOOR_POLYLINE_MIN_SEGMENTS
floor that prevents pruning a small valid component into nothing."
```

---

### Task 4: Extend `DebugTraceCollector.record_polyline_component` with the two optional kwargs

Adds `pre_prune_segment_count` and `pruned_path_indices` to the per-component record so the debug viewer can show what was removed. The existing call sites use the four positional args only — no change there.

**Files:**
- Modify: `debug_trace.py:108-132`

- [ ] **Step 1: Extend the method signature and dict**

Replace the entire `record_polyline_component` method (debug_trace.py:108-132) with:

```python
    def record_polyline_component(
        self,
        path_indices: list[int],
        result: str,
        fail_reason: Optional[str],
        checks: dict,
        pre_prune_segment_count: Optional[int] = None,
        pruned_path_indices: Optional[list[int]] = None,
    ) -> str:
        """Record a polyline arc component evaluation. Returns component_id.

        ``pre_prune_segment_count`` and ``pruned_path_indices`` describe the
        spur-pruning step (see heuristics._prune_arc_spurs). Both default to
        None so existing positional callers keep working unchanged.
        """
        component_id = f"polyline_{self._poly_idx}"
        self._poly_idx += 1
        self._polyline_components.append({
            "component_id": component_id,
            "path_indices": sorted(path_indices),
            "result": result,
            "fail_reason": fail_reason,
            "checks": checks,
            "swing_id": None,
            "pre_prune_segment_count": pre_prune_segment_count,
            "pruned_path_indices": sorted(pruned_path_indices) if pruned_path_indices else [],
        })
        for pi in path_indices:
            if pi in self._primitives:
                entry = self._primitives[pi]
                entry["polyline_component_id"] = component_id
                if entry["polyline_eval"] is not None:
                    entry["polyline_eval"]["polyline_component_id"] = component_id
        return component_id
```

- [ ] **Step 2: Run the entire test suite to confirm no callers broke**

Run: `python -m unittest discover tests -v`
Expected: all tests pass — existing callers in `heuristics.py` still pass four positional args; the new kwargs default to `None`/`[]`.

- [ ] **Step 3: Commit**

```bash
git add debug_trace.py
git commit -m "feat: record_polyline_component accepts pre/post-prune fields

Two new optional kwargs (pre_prune_segment_count, pruned_path_indices)
on DebugTraceCollector.record_polyline_component, persisted into the
per-component record. Existing positional callers unchanged."
```

---

### Task 5: Wire `_prune_arc_spurs` into `_detect_polyline_arc_bboxes`

The behavioral change. After this commit, two doors that were previously rejected at `angle_bin_count` / `axis_like_fraction` will be promoted to candidates and (because the rest of the pipeline already works for them) appear in `final_entities.json`.

**Files:**
- Modify: `heuristics.py` — body of `_detect_polyline_arc_bboxes` (lines ~463-549, the per-component block)

- [ ] **Step 1: Insert the prune step and thread the new debug fields**

In `_detect_polyline_arc_bboxes`, replace the block from line 463 down to (but not including) line 480, which currently reads:

```python
        seg_count = len(component)
        checks: dict = {
            "segment_count": {
                "value": seg_count,
                "range": [DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_MAX_SEGMENTS],
                "passed": DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS,
            },
            "bbox_aspect": None, "size_px": None, "axis_like_fraction": None,
            "angle_bin_count": None, "endpoint_count": None, "overlaps_native_arc": None,
        }
        comp_path_indices = sorted(segs[i][0].path_index for i in component) if collector else []

        if not (DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS):
            if collector:
                collector.record_polyline_component(comp_path_indices, "rejected", "segment_count_out_of_range", checks)
            continue
```

with:

```python
        pre_prune_segment_count = len(component)
        component, pruned_path_indices_set = _prune_arc_spurs(component, segs)
        pruned_path_indices = sorted(pruned_path_indices_set)
        seg_count = len(component)
        checks: dict = {
            "segment_count": {
                "value": seg_count,
                "range": [DOOR_POLYLINE_MIN_SEGMENTS, DOOR_POLYLINE_MAX_SEGMENTS],
                "passed": DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS,
            },
            "bbox_aspect": None, "size_px": None, "axis_like_fraction": None,
            "angle_bin_count": None, "endpoint_count": None, "overlaps_native_arc": None,
        }
        comp_path_indices = sorted(segs[i][0].path_index for i in component) if collector else []

        if not (DOOR_POLYLINE_MIN_SEGMENTS <= seg_count <= DOOR_POLYLINE_MAX_SEGMENTS):
            if collector:
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "segment_count_out_of_range", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
            continue
```

- [ ] **Step 2: Pass the new debug fields to the remaining `record_polyline_component` calls in this function**

Inside `_detect_polyline_arc_bboxes` there are several more calls to `collector.record_polyline_component(...)` along the rejection paths (axis_like_fraction at heuristics.py:509, angle_bin_count at heuristics.py:516, endpoint_count at heuristics.py:532, bbox_degenerate at heuristics.py:489, bbox_aspect/size at heuristics.py:498) and one success path that records via `collector.record_polyline_component(comp_path_indices, "collected", None, checks)` near the end (after the `arc_info` assembly).

For **each** of those calls, add the same two kwargs at the end:

```python
                collector.record_polyline_component(
                    comp_path_indices, "rejected", "<existing reason>", checks,
                    pre_prune_segment_count=pre_prune_segment_count,
                    pruned_path_indices=pruned_path_indices,
                )
```

(and similarly for the success-path `"collected"` call).

Use `grep -n "record_polyline_component" heuristics.py` to enumerate every call site inside `_detect_polyline_arc_bboxes`. There should be one per rejection branch plus one collection branch — six in total at the time of writing. Update each one.

- [ ] **Step 3: Run the full test suite**

Run: `python -m unittest discover tests -v`
Expected: all tests pass, including the existing `test_polyline_arc_connected_linework_leaf_base_confidence` in `test_door_assembly.py` (which uses a clean 8-segment arc with no spurs, so pruning is a no-op for it).

- [ ] **Step 4: End-to-end regression on the sample PDF**

Run:
```bash
python app.py extract 5-1133-WD03.pdf --no-gemini --pages 1
```

This produces a new run under `outputs/<timestamp>/`. Inspect the result:

```bash
ls -t outputs/ | head -1
# Use that timestamp dir:
python3 -c "
import json, sys, glob, os
run_dir = sorted(glob.glob('outputs/*'))[-1]
fe = json.load(open(os.path.join(run_dir, 'pages/page_01/final_entities.json')))
doors = [e for e in fe['entities'] if e['entity_type'] == 'door']
print(f'{run_dir}: {len(doors)} doors detected')
for d in doors:
    x0,y0,x1,y1 = d['bbox']
    print(f'  {d[\"entity_id\"]} bbox=({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) conf={d[\"confidence\"]}')
"
```

Expected: **at least 6 doors** detected on page 1 (up from 4). At minimum, doors at approximately:
- `~(1041, 700)-(1088, 758)` — the previously-missed `linework_1318` arc
- `~(456, 1336)-(514, 1397)` — the previously-missed `linework_226` arc

A 7th, 8th, etc. door is possible if the upstream pipeline picks up additional candidates that benefit from cleaner arc scoring; that's a bonus, not a requirement.

- [ ] **Step 5: Verify the debug trace shows pruning happened**

```bash
run_dir=$(ls -td outputs/* | head -1)
python3 -c "
import json
d = json.load(open('$run_dir/pages/page_01/debug_trace.json'))
pruned = [pc for pc in d['polyline_components'] if pc.get('pruned_path_indices')]
print(f'{len(pruned)} polyline components had spurs pruned')
for pc in pruned[:10]:
    print(f'  {pc[\"component_id\"]} result={pc[\"result\"]} pre={pc[\"pre_prune_segment_count\"]} removed={pc[\"pruned_path_indices\"]}')
"
```

Expected: at least 2 components show pruning (the polyline_884 and polyline_393 successors). Their `result` should be `collected` and their `swing_id` set.

- [ ] **Step 6: Commit**

```bash
git add heuristics.py
git commit -m "feat: prune leaf-spurs from polyline arc components before scoring

Calls _prune_arc_spurs after BFS component discovery in
_detect_polyline_arc_bboxes. Recovers two doors on page 1 of
5-1133-WD03.pdf that were previously rejected because a small door
stop or cap-line cluster attached to the arc pushed angle_bin_count
or axis_like_fraction past the thresholds. The thresholds themselves
are unchanged.

Spec: docs/superpowers/specs/2026-06-16-polyline-arc-spur-pruning-design.md"
```

---

## Self-review notes

Coverage check against the spec:

| Spec requirement | Task |
|---|---|
| New constant `DOOR_POLYLINE_SPUR_MAX_SEGMENTS = 4` | Task 1, Step 1 |
| Helper `_prune_arc_spurs(component, segs)` | Tasks 1–2 (skeleton + body) |
| Floor at `DOOR_POLYLINE_MIN_SEGMENTS` | Task 2 body, Task 3 floor test |
| Iterative until no change | Task 2 body (`while True` loop) |
| Spur length cap | Task 2 body (`walked > MAX` abort), Task 3 oversized test |
| Pure cycle untouched | Task 1, Step 3 (pure-cycle test) |
| `record_polyline_component` accepts the two new fields | Task 4 |
| Wire into `_detect_polyline_arc_bboxes` | Task 5, Step 1 |
| Debug trace carries `pre_prune_segment_count`, `pruned_path_indices` | Tasks 4 + 5 (both ends of the pipe) |
| Six unit tests (clean, cycle, Y-junction-branches, dual 2-seg spurs, oversized-branch, floor) | Tasks 1+2+3 |
| End-to-end ≥6 doors on page 1 of `5-1133-WD03.pdf` | Task 5, Step 4 |
