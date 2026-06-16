# Polyline-Arc Spur Pruning — Design

## Problem

The door-detection pipeline misses real doors whose polyline-arc swing has a
small ornamental appendage (door stop, hinge cap) drawn touching the arc's
endpoint.

Evidence from `outputs/2026-06-16_16-11-38/pages/page_01/`:

| Component | Size | Failing check | Real cause |
|---|---|---|---|
| `polyline_884` | 53.25 px, 15 segs | `angle_bin_count = 8 > 7` | 4-segment door stop attached to arc endpoint pushed angle bins from 7 to 8 |
| `polyline_393` | 55.25 px, 14 segs | `axis_like_fraction = 0.429 > 0.35` | Short axis-aligned cap lines pushed the axis fraction from ~0.18 to 0.43 |

Both arcs are otherwise indistinguishable from the four detected ones
(`polyline_465/506/877/881`), which are clean 11-segment chains with
`angle_bin_count ≤ 7` and `axis_like_fraction ≤ 0.27`.

The polluting segments are joined to the arc through a single shared endpoint:
the arc's natural endpoint becomes a degree-3+ junction in the connected
component, and a short tail of axis-aligned segments extends past it.

## Fix

Add a graph-pruning step inside `_detect_polyline_arc_bboxes` (heuristics.py:395)
that removes short leaf-spurs from the connected component before the geometric
checks run.

### Algorithm

A door arc is a simple chain: exactly two degree-1 vertices, all interior
vertices degree-2. A "spur" is a chain of segments that starts at a degree-1
vertex and terminates at a degree-3+ junction, with ≤ `MAX_SPUR_SEGMENTS`
segments along the way.

```
loop:
  rebuild degrees for current component
  candidates = []
  for each degree-1 vertex v:
    walk through degree-2 vertices until first junction or another leaf
    if walk length ≤ DOOR_POLYLINE_SPUR_MAX_SEGMENTS:
      candidates += walk's segment indices
  if no candidates or removing them would drop |component| below
     DOOR_POLYLINE_MIN_SEGMENTS:
    break
  component -= candidates
return component, removed_set
```

Constant: `DOOR_POLYLINE_SPUR_MAX_SEGMENTS = 4`. Chosen so a standard 4-segment
door-stop rectangle is recognised, but anything larger (5+ segments) is left
alone — those are likely real arc structure, not ornament.

### Why iterate

After removing one tier of spurs, a junction may drop from degree-3 to degree-2,
exposing a deeper spur. One pass would leave those. Components are small (≤ ~25
segments after the upstream cap), so iteration cost is negligible.

### Why prune *before* scoring instead of relaxing thresholds

The current thresholds (`axis_like_fraction ≤ 0.35`, `angle_bin_count ∈ [4,7]`)
are deliberately strict to keep wall hatches, lettering, and decorative arcs
out of the door pipeline. Relaxing them would re-admit those false positives.
Removing the polluting segments before scoring keeps the strict thresholds
intact while restoring the real arcs.

### Closed-cycle appendages — out of scope

A door-stop drawn as a closed rectangle attached at exactly one articulation
point would have no degree-1 vertex inside the appendage and won't be touched
by this fix. The current PDF doesn't show this pattern; if a future drawing
exhibits it, add biconnected-component pruning as a follow-up.

## Implementation

### Files changed

- `heuristics.py` — new helper `_prune_arc_spurs`, new constant, modified call
  site in `_detect_polyline_arc_bboxes`.
- `debug_trace.py` — extend `DebugTraceCollector.record_polyline_component`
  (currently a fixed 4-positional-arg signature at debug_trace.py:108) with
  two new optional kwargs `pre_prune_segment_count: int | None = None` and
  `pruned_path_indices: list[int] | None = None`, persisted into the record
  dict alongside `checks`, `result`, `fail_reason`.
- `tests/test_polyline_arc_pruning.py` — new unittest module.

### Constant location

Add next to the existing `DOOR_POLYLINE_*` constants (heuristics.py:30-50):

```python
DOOR_POLYLINE_SPUR_MAX_SEGMENTS = 4
```

### Helper signature

```python
def _prune_arc_spurs(
    component: list[int],
    segs: list[tuple[PathPrimitive, tuple[float, float], tuple[float, float], float, float]],
    key,
) -> tuple[list[int], set[int]]:
    """Remove short leaf-spurs (door stops, cap lines) from an arc component.

    Returns (pruned_component, removed_seg_indices). If pruning would drop the
    component below DOOR_POLYLINE_MIN_SEGMENTS, returns the original component
    unchanged with an empty removed set.
    """
```

`key` is the endpoint-snap function already defined inside
`_detect_polyline_arc_bboxes` at heuristics.py:427-431. The helper rebuilds
adjacency from scratch on each iteration over the *current* subset of `segs`
— simpler than threading through the outer `adjacency` list and the components
are tiny.

### Call site change

heuristics.py:463-464, replace:

```python
seg_count = len(component)
```

with:

```python
pre_prune_count = len(component)
component, removed_path_indices = _prune_arc_spurs(component, segs, key)
seg_count = len(component)
```

`removed_path_indices` and `pre_prune_count` flow into the existing
`record_polyline_component` calls so the debug viewer can show them.

### Debug trace

`checks` already includes a `segment_count` entry showing the current value
and range. Add two top-level fields to the polyline-component record:

- `pre_prune_segment_count` — `int`, the count before pruning (equals
  `segment_count.value` when no pruning happened).
- `pruned_path_indices` — `list[int]`, sorted path indices that were removed.

These appear at the same level as `checks` in the per-component record. The
`DebugTraceCollector.record_polyline_component` signature gains two optional
kwargs (default `None`); existing call sites continue to work unchanged, and
the new call site in `_detect_polyline_arc_bboxes` passes both.

## Behavior contract

| Input | Output |
|---|---|
| Clean 11-segment arc (no spurs) | Identical to today. No segments removed. |
| Arc + ≤4-segment spur | Spur removed, remaining checks run on pure arc. |
| Arc + >4-segment "spur" | Nothing removed. Component scored as today. |
| Arc + multiple spurs at one junction | All spurs ≤4 segs removed in successive iterations. |
| Pure cycle (no degree-1 vertex) | Nothing removed (no leaves to walk from). |
| Component that would prune below `DOOR_POLYLINE_MIN_SEGMENTS` | Nothing removed; component falls through unchanged and the existing `segment_count` check rejects it. |
| Large wall network (231 segs) | Nothing meaningful prunable; the existing `segment_count_out_of_range` rejection still fires. |

## Testing

`tests/test_polyline_arc_pruning.py` — `unittest` module, six tests:

1. `test_clean_arc_unchanged` — an 11-segment chain with two degree-1 vertices
   passes through `_prune_arc_spurs` returning the same component and empty
   removed set.
2. `test_single_spur_removed` — an 11-segment arc with a 3-segment spur
   attached at one endpoint → 11 segments remain, the 3 spur indices are in
   the removed set.
3. `test_dual_spurs_at_one_junction` — the `linework_1318` shape (arc + two
   2-segment spurs branching off the same junction) → arc segments preserved,
   both spur tails removed.
4. `test_oversized_spur_kept` — arc + 5-segment "spur" → nothing pruned (5 >
   `DOOR_POLYLINE_SPUR_MAX_SEGMENTS`).
5. `test_pruning_floor` — short component (4 segs total) where any prune would
   drop below `DOOR_POLYLINE_MIN_SEGMENTS` → no prune, original component
   returned.
6. `test_pure_cycle_unchanged` — 4-segment closed loop, no degree-1 vertices →
   nothing pruned.

Each constructs a small synthetic `list[PathPrimitive]` of straight line
segments, runs `_prune_arc_spurs`, asserts on the returned component and
removed set.

End-to-end regression: run `python app.py extract 5-1133-WD03.pdf --no-gemini`
and assert `summary.json` shows at least 6 doors on page 1 (currently 4 +
the two we've identified as recoverable: `linework_1318` arc and
`linework_226` arc).

## Risks and mitigations

- **A real arc whose endpoints happen to be degree-3+ in another way** —
  e.g. an arc that closes a small triangle at one end. The triangle's vertices
  are all degree-2, no leaf exists to walk from, so nothing is pruned. Arc
  fails `endpoint_count` check as today. No regression.

- **Over-pruning** — if `DOOR_POLYLINE_SPUR_MAX_SEGMENTS` were set too high we
  could strip part of a real arc. 4 is conservative; the smallest detected
  arcs in this PDF have 11 segments. The `pre_prune` floor at
  `DOOR_POLYLINE_MIN_SEGMENTS` is a second backstop.

- **Hidden cycles** — a closed-loop appendage attached at one articulation
  point won't be pruned (out of scope, documented above). Affected doors stay
  undetected as today; no regression vs. current behavior.
