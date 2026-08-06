# Detection Review Tooling V1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a regression sweep leave behind reviewable images with named entity ids, and let the user record correct/wrong verdicts by ticking a terminal checklist instead of hand-editing JSON.

**Architecture:** The sweep stops extracting into a temp directory and writes to a stable, gitignored `outputs/regress/<slug>/`, drawing one review image per page per entity type with every unreviewed detection stamped with a short id. A new pure verdict writer turns selections into ground-truth entries; a thin `tools/review.py` drives it with `InquirerPy` prompts, walking sheet → page → category. Nothing in `detection/` or `pipeline.py` changes.

**Tech Stack:** Python 3.14, stdlib `unittest`, PyMuPDF/Pillow (already present), `InquirerPy` (new, dev-tool only).

**Spec:** `docs/superpowers/specs/2026-08-06-detection-review-tooling-design.md` — this plan covers V1 (pieces 1–5) only. Pieces 6–7 (room drift scoring, agent flags) are explicitly out of scope.

## Global Constraints

Every task's requirements implicitly include these.

- **Ground truth format stays backward compatible.** `tests/ground_truth/s01.json` must keep loading and scoring identically. Every new field is optional.
- **Entity ids are ordinal and unstable across runs.** Ids may identify a detection *within one sweep's output*. They must never be written into ground truth and never used for matching. Matching stays geometric (type + IoU ≥ 0.5).
- **New detections never fail the sweep.** Nothing in this plan may change `SheetResult.is_regression` or the exit-code contract.
- **The fast unit tier stays under ~10s.** Every test in this plan is synthetic; none opens a corpus PDF.
- **No committed PDFs, no address-bearing text.** All new output goes under `outputs/`, which is already gitignored.
- **No detection changes.** `detection/`, `pipeline.py`, `extraction/` are read-only in this plan, with one exception: `extraction/renderer.py` helpers are *imported*, never modified.
- **Run tests with:** `source .venv/bin/activate && python -m unittest discover tests`
- **Never add a `Co-Authored-By` trailer to a commit.**

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `regression/run_dir.py` | create | Resolve, wipe, and locate the persisted per-slug sweep output directory |
| `regression/report.py` | modify | Print `entity_id` and the review-image directory on REVIEW lines |
| `regression/ground_truth.py` | modify | `polygon`/`shape` fields on `TruthItem`; `dump_truth` writer |
| `regression/corpus.py` | modify | `set_labeled(slug)` — flip a manifest entry's `"labeled"` |
| `regression/verdicts.py` | create | Pure verdict writer: selections → ground truth + manifest. No TTY. |
| `regression/review_render.py` | create | Per-category review overlay PNGs |
| `regression/review_session.py` | create | Read persisted output + truth → what is still unreviewed, per page |
| `regression/sweep.py` | modify | Use the persistent dir, `debug=True`, draw review overlays |
| `tools/review.py` | create | The InquirerPy walk. Thin; all logic lives in the modules above. |
| `requirements.txt` | modify | Add `InquirerPy` |
| `tests/test_run_dir.py` | create | Task 1 |
| `tests/test_regress_report.py` | modify | Task 2 |
| `tests/test_ground_truth.py` | modify | Task 3 |
| `tests/test_verdicts.py` | create | Task 4 |
| `tests/test_review_render.py` | create | Task 5 |
| `tests/test_sweep.py` | modify | Task 6 |
| `tests/test_review_session.py` | create | Task 7 |

The split between `verdicts.py` (writes), `review_session.py` (reads), `review_render.py` (draws) and `tools/review.py` (prompts) is what makes V1 testable without driving a terminal. `tools/review.py` must contain no logic worth testing.

---

## Task 1: Persistent sweep output directory

`regression/sweep.py:152` wraps `run_extract` in `tempfile.TemporaryDirectory()`, destroying the render, overlay, and debug viewer microseconds after they are written. This task builds the replacement directory helper. Task 6 wires it in.

`run_extract(out_parent=...)` creates a *timestamped child* inside `out_parent` and returns that child's path. So `outputs/regress/<slug>/` is wiped before each extraction and ends up holding exactly one timestamped child, which `latest_run` finds.

**Files:**
- Create: `regression/run_dir.py`
- Test: `tests/test_run_dir.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `regression.run_dir.REGRESS_OUT: Path` — `<repo>/outputs/regress`
  - `regression.run_dir.slug_dir(slug: str) -> Path`
  - `regression.run_dir.reset_slug_dir(slug: str) -> Path` — wipes and recreates, returns it
  - `regression.run_dir.latest_run(slug: str) -> Path | None` — the single timestamped child, or None

- [ ] **Step 1: Write the failing test**

Create `tests/test_run_dir.py`:

```python
"""Where a sweep leaves its output, and how review tooling finds it again."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from regression import run_dir


class RunDirTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._original = run_dir.REGRESS_OUT
        run_dir.REGRESS_OUT = Path(self._tmp.name) / "regress"
        self.addCleanup(lambda: setattr(run_dir, "REGRESS_OUT", self._original))

    def test_slug_dir_is_under_the_regress_root(self):
        self.assertEqual(run_dir.slug_dir("s01").parent, run_dir.REGRESS_OUT)
        self.assertEqual(run_dir.slug_dir("s01").name, "s01")

    def test_reset_creates_the_directory(self):
        path = run_dir.reset_slug_dir("s01")
        self.assertTrue(path.is_dir())

    def test_reset_wipes_a_previous_sweep(self):
        stale = run_dir.reset_slug_dir("s01") / "2026-01-01_00-00-00"
        stale.mkdir()
        (stale / "render.png").write_bytes(b"stale")

        run_dir.reset_slug_dir("s01")

        self.assertFalse(stale.exists())
        self.assertEqual(list(run_dir.slug_dir("s01").iterdir()), [])

    def test_latest_run_is_none_before_any_sweep(self):
        self.assertIsNone(run_dir.latest_run("s01"))

    def test_latest_run_finds_the_single_child(self):
        child = run_dir.reset_slug_dir("s01") / "2026-08-06_15-19-08"
        child.mkdir()
        self.assertEqual(run_dir.latest_run("s01"), child)

    def test_latest_run_takes_the_newest_when_several_exist(self):
        # reset_slug_dir normally guarantees at most one child, but an
        # interrupted sweep can leave a stale sibling behind. Newest wins
        # rather than crashing or picking arbitrarily.
        base = run_dir.reset_slug_dir("s01")
        (base / "2026-08-01_09-00-00").mkdir()
        newest = base / "2026-08-06_15-19-08"
        newest.mkdir()
        self.assertEqual(run_dir.latest_run("s01"), newest)

    def test_latest_run_ignores_files(self):
        base = run_dir.reset_slug_dir("s01")
        (base / "notes.txt").write_text("x")
        self.assertIsNone(run_dir.latest_run("s01"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_run_dir -v
```

Expected: `ModuleNotFoundError: No module named 'regression.run_dir'`

- [ ] **Step 3: Write the implementation**

Create `regression/run_dir.py`:

```python
"""Where a sweep leaves its output.

Sweeps used to extract into a `tempfile.TemporaryDirectory()`, which destroyed
the render, the overlay and the debug viewer the moment scoring finished --
leaving REVIEW lines nobody could act on. Output now lands in a stable,
gitignored directory per slug.

`run_extract` creates a timestamped child inside whatever parent it is given
and returns that child. Wiping the slug directory before each extraction keeps
exactly one child there, so `latest_run` is unambiguous rather than a guess
across an accumulating pile of runs.
"""
from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REGRESS_OUT = REPO_ROOT / "outputs" / "regress"


def slug_dir(slug: str) -> Path:
    return REGRESS_OUT / slug


def reset_slug_dir(slug: str) -> Path:
    """Wipe and recreate this slug's output directory."""
    path = slug_dir(slug)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def latest_run(slug: str) -> Path | None:
    """The most recent run directory for this slug, or None.

    Timestamp names sort lexicographically in chronological order
    (YYYY-MM-DD_HH-MM-SS), so `max` is the newest. Files are ignored: only
    run_extract's directories count.
    """
    base = slug_dir(slug)
    if not base.is_dir():
        return None
    children = [p for p in base.iterdir() if p.is_dir()]
    return max(children, key=lambda p: p.name) if children else None
```

Note the module-level `REGRESS_OUT` is read *inside* each function via the module global, so the test's monkeypatch takes effect. Do not bind it to a local at import time.

- [ ] **Step 4: Run the test to verify it passes**

```bash
source .venv/bin/activate && python -m unittest tests.test_run_dir -v
```

Expected: 7 tests, OK

- [ ] **Step 5: Commit**

```bash
git add regression/run_dir.py tests/test_run_dir.py
git commit -m "feat: persistent per-slug sweep output directory"
```

---

## Task 2: Entity ids in the REVIEW lines

`regression/report.py:100` formats raw entity dicts that already carry `entity_id`, then throws the id away. Without it there is nothing to match a terminal line to a shape on a drawing.

**Files:**
- Modify: `regression/report.py:32-36` (add `run_dir` field), `regression/report.py:99-101` (the REVIEW line)
- Test: `tests/test_regress_report.py`

**Interfaces:**
- Consumes: nothing
- Produces: `SheetResult.run_dir: str | None` — printed under the REVIEW block so the user knows where the images are. Task 6 populates it.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_regress_report.py` (match the file's existing import style; add any names it does not already import):

```python
class ReviewLineIdentityTests(unittest.TestCase):
    def _result(self, **kwargs):
        return SheetResult(
            slug="s01",
            unreviewed=[{"entity_id": "door_0007", "entity_type": "door",
                         "bbox": [1200.0, 870.0, 1240.0, 900.0], "confidence": 0.82}],
            **kwargs)

    def test_review_line_names_the_entity_id(self):
        out = render([self._result()])
        self.assertIn("door_0007", out)

    def test_review_line_still_carries_confidence_and_centre(self):
        out = render([self._result()])
        self.assertIn("conf 0.82", out)
        self.assertIn("(1220,885)", out)

    def test_review_line_falls_back_to_the_type_without_an_id(self):
        result = SheetResult(slug="s01",
                             unreviewed=[{"entity_type": "window",
                                          "bbox": [0.0, 0.0, 10.0, 10.0]}])
        out = render([result])
        self.assertIn("REVIEW new window", out)

    def test_run_dir_is_printed_when_there_are_review_items(self):
        out = render([self._result(run_dir="outputs/regress/s01/2026-08-06_15-19-08")])
        self.assertIn("outputs/regress/s01/2026-08-06_15-19-08", out)

    def test_run_dir_is_not_printed_when_nothing_needs_review(self):
        clean = SheetResult(slug="s01", status="ok",
                            run_dir="outputs/regress/s01/2026-08-06_15-19-08")
        self.assertNotIn("outputs/regress", render([clean]))
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_regress_report -v
```

Expected: FAIL — `door_0007` not in output, and `TypeError: SheetResult.__init__() got an unexpected keyword argument 'run_dir'`

- [ ] **Step 3: Write the implementation**

In `regression/report.py`, add the field to `SheetResult` (after `unscored_pages`):

```python
    run_dir: str | None = None
```

Replace the REVIEW-line loop (currently lines 99-101):

```python
        for ent in r.unreviewed:
            # entity_id is display-only: it identifies this detection within
            # THIS sweep's output so the user can find it on the review image.
            # Ids are ordinal and shift between runs, so it is never written
            # to ground truth and never used for matching.
            name = ent.get("entity_id") or f"new {ent['entity_type']}"
            lines.append(f"    REVIEW new {name}  "
                         f"conf {ent.get('confidence', 0):.2f}  {_centre(ent['bbox'])}")
        if r.run_dir and (r.unreviewed or r.closed_deferred):
            lines.append(f"    images: {r.run_dir}/pages/  "
                         f"— then: python tools/review.py {r.slug}")
```

The fallback keeps the pre-existing wording (`REVIEW new window`) for a dict with no id, so a hand-constructed result still reads sensibly.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
source .venv/bin/activate && python -m unittest tests.test_regress_report -v
```

Expected: all tests OK, including the pre-existing ones.

- [ ] **Step 5: Commit**

```bash
git add regression/report.py tests/test_regress_report.py
git commit -m "feat: name the entity and its review images on REVIEW lines"
```

---

## Task 3: Ground truth carries room polygons

`TruthItem` stores a bbox only. A room's bbox is a lie about an L-shaped room's extent, and the shape is exactly what needs judging. V1 *stores* the polygon and the `shape` axis; V2 scores them. Storing now is what makes the phase split safe — rooms labeled in V1 need no re-review when V2 lands.

`ground_truth.py` can currently only read. `dump_truth` is the writer Task 4 needs.

**Files:**
- Modify: `regression/ground_truth.py:25-32` (`TruthItem`), `:60-72` (`_item`), and append `dump_truth`
- Test: `tests/test_ground_truth.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `TruthItem.polygon: list[list[float]] | None`
  - `TruthItem.shape: str | None` — `"approved"` or `"partial"`
  - `regression.ground_truth.SHAPES: tuple[str, str]`
  - `regression.ground_truth.dump_truth(truth: SheetTruth) -> Path`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ground_truth.py`:

```python
import json
import tempfile
from pathlib import Path

from regression import ground_truth as gt


class TruthWriteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._original = gt.TRUTH_DIR
        gt.TRUTH_DIR = Path(self._tmp.name)
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._original))

    def _write(self, slug, payload):
        (gt.TRUTH_DIR / f"{slug}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def test_a_file_without_the_new_fields_round_trips_unchanged(self):
        payload = {
            "sheet": "s01", "pdf_sha256": "abc", "reviewed": "2026-08-06",
            "pages": {"1": {"confirmed": [
                {"type": "window", "bbox": [1.0, 2.0, 3.0, 4.0], "note": "n"}]}},
        }
        self._write("s01", payload)
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")

        gt.dump_truth(gt.load_truth("s01"))

        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_polygon_and_shape_round_trip(self):
        payload = {
            "sheet": "s02", "pdf_sha256": "def", "reviewed": "2026-08-06",
            "pages": {"1": {"confirmed": [{
                "type": "room", "bbox": [0.0, 0.0, 10.0, 10.0],
                "polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]],
                "shape": "partial", "note": "misses the bay",
            }]}},
        }
        self._write("s02", payload)
        item = gt.load_truth("s02").page(1).confirmed[0]
        self.assertEqual(item.polygon,
                         [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
        self.assertEqual(item.shape, "partial")

        gt.dump_truth(gt.load_truth("s02"))
        reloaded = gt.load_truth("s02").page(1).confirmed[0]
        self.assertEqual(reloaded.polygon, item.polygon)
        self.assertEqual(reloaded.shape, "partial")
        self.assertEqual(reloaded.note, "misses the bay")

    def test_absent_optional_fields_are_not_written(self):
        payload = {"sheet": "s03", "pdf_sha256": "ghi", "reviewed": None,
                   "pages": {"1": {"confirmed": [
                       {"type": "door", "bbox": [1.0, 2.0, 3.0, 4.0]}]}}}
        self._write("s03", payload)
        gt.dump_truth(gt.load_truth("s03"))
        written = json.loads((gt.TRUTH_DIR / "s03.json").read_text(encoding="utf-8"))
        item = written["pages"]["1"]["confirmed"][0]
        self.assertEqual(set(item), {"type", "bbox"})

    def test_empty_verdict_lists_are_not_written(self):
        truth = gt.SheetTruth(slug="s04", pdf_sha256="jkl", reviewed="2026-08-06")
        truth.pages[1] = gt.PageTruth(confirmed=[
            gt.TruthItem(type="door", bbox=(1.0, 2.0, 3.0, 4.0))])
        gt.dump_truth(truth)
        written = json.loads((gt.TRUTH_DIR / "s04.json").read_text(encoding="utf-8"))
        self.assertEqual(set(written["pages"]["1"]), {"confirmed"})

    def test_an_unknown_shape_value_is_rejected(self):
        self._write("s05", {"sheet": "s05", "pdf_sha256": "x", "reviewed": None,
                            "pages": {"1": {"confirmed": [
                                {"type": "room", "bbox": [0.0, 0.0, 1.0, 1.0],
                                 "shape": "probably-fine"}]}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s05")

    def test_a_malformed_polygon_is_rejected(self):
        self._write("s06", {"sheet": "s06", "pdf_sha256": "x", "reviewed": None,
                            "pages": {"1": {"confirmed": [
                                {"type": "room", "bbox": [0.0, 0.0, 1.0, 1.0],
                                 "polygon": [[0.0, 0.0], [1.0]]}]}}})
        with self.assertRaises(ValueError):
            gt.load_truth("s06")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_ground_truth -v
```

Expected: FAIL — `AttributeError: module 'regression.ground_truth' has no attribute 'dump_truth'`

- [ ] **Step 3: Write the implementation**

In `regression/ground_truth.py`, add the constant next to `VERDICTS`:

```python
# The second axis on a room verdict. `confirmed` vs `false_positives` says
# whether the room is real; `shape` says whether the stored polygon is the
# outline the user actually wants. A "partial" polygon is a baseline to detect
# change against, not an ideal. V1 records this; drift scoring reads it.
SHAPES = ("approved", "partial")
```

Extend `TruthItem`:

```python
@dataclass
class TruthItem:
    type: str
    bbox: tuple[float, float, float, float]
    tag: str | None = None
    path_indices: list[int] = field(default_factory=list)
    note: str = ""
    polygon: list[list[float]] | None = None
    shape: str | None = None
```

Extend `_item` — insert before the `return`:

```python
    polygon = raw.get("polygon")
    if polygon is not None:
        if (not isinstance(polygon, list) or len(polygon) < 3
                or any(not isinstance(p, list) or len(p) != 2 for p in polygon)):
            raise ValueError(f"{slug}: polygon must be >=3 [x, y] pairs, "
                             f"got {polygon!r}")
        polygon = [[float(x), float(y)] for x, y in polygon]

    shape = raw.get("shape")
    if shape is not None and shape not in SHAPES:
        raise ValueError(f"{slug}: shape must be one of {list(SHAPES)}, "
                         f"got {shape!r}")
```

and add `polygon=polygon, shape=shape,` to the `TruthItem(...)` construction.

Append the writer:

```python
def _item_payload(item: TruthItem) -> dict:
    """Serialize one verdict, omitting everything left at its default.

    Ground truth is read by humans in diffs, so an item carries only the
    fields that were actually set rather than a wall of nulls.
    """
    payload: dict = {"type": item.type, "bbox": [float(v) for v in item.bbox]}
    if item.tag:
        payload["tag"] = item.tag
    if item.path_indices:
        payload["path_indices"] = list(item.path_indices)
    if item.polygon:
        payload["polygon"] = [[float(x), float(y)] for x, y in item.polygon]
    if item.shape:
        payload["shape"] = item.shape
    if item.note:
        payload["note"] = item.note
    return payload


def dump_truth(truth: SheetTruth) -> Path:
    """Write a sheet's verdicts back to tests/ground_truth/<slug>.json.

    Round-trips load_truth: an unmodified file re-serializes byte-identically,
    so a review session's diff shows only the verdicts it actually added.
    """
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    pages: dict[str, dict] = {}
    for number in sorted(truth.pages):
        page = truth.pages[number]
        lists = {v: [_item_payload(i) for i in getattr(page, v)] for v in VERDICTS}
        lists = {name: items for name, items in lists.items() if items}
        if lists:
            pages[str(number)] = lists
    path = truth_path(truth.slug)
    path.write_text(json.dumps({"sheet": truth.slug,
                                "pdf_sha256": truth.pdf_sha256,
                                "reviewed": truth.reviewed,
                                "pages": pages}, indent=2) + "\n",
                    encoding="utf-8")
    return path
```

- [ ] **Step 4: Run the full suite to verify nothing regressed**

```bash
source .venv/bin/activate && python -m unittest discover tests
```

Expected: OK. `tests/test_ground_truth_hygiene.py` and `tests/test_sweep.py` exercise the loader and must stay green.

- [ ] **Step 5: Verify the real ground truth still round-trips**

```bash
source .venv/bin/activate && python -c "
from regression.ground_truth import load_truth, truth_path, _item_payload, VERDICTS
import json
before = truth_path('s01').read_text(encoding='utf-8')
t = load_truth('s01')
pages = {}
for n in sorted(t.pages):
    lists = {v: [_item_payload(i) for i in getattr(t.pages[n], v)] for v in VERDICTS}
    lists = {k: v for k, v in lists.items() if v}
    if lists: pages[str(n)] = lists
after = json.dumps({'sheet': t.slug, 'pdf_sha256': t.pdf_sha256,
                    'reviewed': t.reviewed, 'pages': pages}, indent=2) + '\n'
print('IDENTICAL' if before == after else 'DIFFERS')
"
```

Expected: `IDENTICAL`. This deliberately does not write the file. If it prints `DIFFERS`, diff the two strings and fix `_item_payload` — do not reformat `s01.json` to match the writer.

- [ ] **Step 6: Commit**

```bash
git add regression/ground_truth.py tests/test_ground_truth.py
git commit -m "feat: ground truth carries room polygons and a shape axis"
```

---

## Task 4: The verdict writer

The piece that replaces hand-editing JSON. Pure: no prompts, no terminal, no I/O beyond the two files it owns. This is what both the human path and (in V2) the agent path call.

**Files:**
- Create: `regression/verdicts.py`
- Modify: `regression/corpus.py` (append `set_labeled`)
- Test: `tests/test_verdicts.py`

**Interfaces:**
- Consumes: `ground_truth.load_truth`, `ground_truth.dump_truth`, `ground_truth.SHAPES`, `ground_truth.PageTruth`, `ground_truth.TruthItem`, `corpus.sheet_entry`
- Produces:
  - `regression.corpus.set_labeled(slug: str, value: bool = True) -> None`
  - `regression.verdicts.Verdict(page: int, entity: dict, correct: bool, shape: str | None = None, note: str = "")`
  - `regression.verdicts.record_verdicts(slug: str, verdicts: list[Verdict], today: str | None = None) -> Path | None` — returns None when `verdicts` is empty

- [ ] **Step 1: Write the failing test**

Create `tests/test_verdicts.py`:

```python
"""The verdict writer: selections in, ground truth out.

Everything here is synthetic. No PDF is opened and no sweep is run.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from regression import corpus, ground_truth as gt
from regression.verdicts import Verdict, record_verdicts


def door(entity_id="door_0007", bbox=(1200.0, 870.0, 1240.0, 900.0)):
    return {"entity_id": entity_id, "entity_type": "door", "bbox": list(bbox),
            "confidence": 0.82, "attributes": {}}


def room(entity_id="room_0002"):
    return {"entity_id": entity_id, "entity_type": "room",
            "bbox": [0.0, 0.0, 100.0, 100.0], "confidence": 0.9,
            "attributes": {"polygon": [[0.0, 0.0], [100.0, 0.0],
                                       [100.0, 100.0], [0.0, 100.0]]}}


class VerdictWriterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self._truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"
        gt.TRUTH_DIR.mkdir()
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._truth_dir))

        self._manifest = corpus.MANIFEST_PATH
        corpus.MANIFEST_PATH = root / "MANIFEST.json"
        corpus.MANIFEST_PATH.write_text(json.dumps({
            "storage": "",
            "sheets": [
                {"slug": "s02", "file": "s02.pdf", "sha256": "bbb", "pages": 1},
                {"slug": "s01", "file": "s01.pdf", "sha256": "aaa", "pages": 1},
            ],
        }, indent=2) + "\n", encoding="utf-8")
        self.addCleanup(lambda: setattr(corpus, "MANIFEST_PATH", self._manifest))

    def _existing_truth(self):
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "aaa", "reviewed": "2026-01-01",
            "pages": {"1": {"confirmed": [
                {"type": "window", "bbox": [10.0, 20.0, 30.0, 40.0],
                 "note": "recorded earlier"}]}},
        }, indent=2) + "\n", encoding="utf-8")

    def _load(self, slug="s01"):
        return json.loads((gt.TRUTH_DIR / f"{slug}.json").read_text(encoding="utf-8"))

    def test_a_correct_verdict_lands_in_confirmed(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        confirmed = self._load()["pages"]["1"]["confirmed"]
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0]["type"], "door")
        self.assertEqual(confirmed[0]["bbox"], [1200.0, 870.0, 1240.0, 900.0])

    def test_a_wrong_verdict_lands_in_false_positives(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=False)],
                        today="2026-08-06")
        page = self._load()["pages"]["1"]
        self.assertNotIn("confirmed", page)
        self.assertEqual(len(page["false_positives"]), 1)

    def test_the_entity_id_is_never_persisted(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        raw = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        self.assertNotIn("door_0007", raw)
        self.assertNotIn("entity_id", raw)

    def test_existing_verdicts_survive_untouched(self):
        self._existing_truth()
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        confirmed = self._load()["pages"]["1"]["confirmed"]
        self.assertEqual(confirmed[0]["type"], "window")
        self.assertEqual(confirmed[0]["note"], "recorded earlier")
        self.assertEqual(confirmed[1]["type"], "door")

    def test_a_room_verdict_stores_its_polygon_and_shape(self):
        record_verdicts("s01", [Verdict(page=1, entity=room(), correct=True,
                                        shape="partial",
                                        note="misses the doorway recess")],
                        today="2026-08-06")
        item = self._load()["pages"]["1"]["confirmed"][0]
        self.assertEqual(len(item["polygon"]), 4)
        self.assertEqual(item["shape"], "partial")
        self.assertEqual(item["note"], "misses the doorway recess")

    def test_a_non_room_entity_stores_no_polygon(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        self.assertNotIn("polygon", self._load()["pages"]["1"]["confirmed"][0])

    def test_reviewed_and_sha_are_set(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        payload = self._load()
        self.assertEqual(payload["reviewed"], "2026-08-06")
        self.assertEqual(payload["pdf_sha256"], "aaa")

    def test_the_manifest_entry_is_flagged_labeled(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        by_slug = {s["slug"]: s for s in sheets}
        self.assertTrue(by_slug["s01"]["labeled"])
        self.assertNotIn("labeled", by_slug["s02"])

    def test_the_manifest_keeps_its_original_order(self):
        record_verdicts("s01", [Verdict(page=1, entity=door(), correct=True)],
                        today="2026-08-06")
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        self.assertEqual([s["slug"] for s in sheets], ["s02", "s01"])

    def test_verdicts_across_pages_land_on_their_own_pages(self):
        record_verdicts("s01", [
            Verdict(page=1, entity=door("door_0001"), correct=True),
            Verdict(page=2, entity=door("door_0002"), correct=True),
        ], today="2026-08-06")
        self.assertEqual(set(self._load()["pages"]), {"1", "2"})

    def test_an_unknown_slug_raises_and_writes_nothing(self):
        with self.assertRaises(ValueError):
            record_verdicts("s99", [Verdict(page=1, entity=door(), correct=True)],
                            today="2026-08-06")
        self.assertFalse((gt.TRUTH_DIR / "s99.json").exists())

    def test_an_invalid_shape_raises_before_writing_anything(self):
        self._existing_truth()
        before = (gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            record_verdicts("s01", [Verdict(page=1, entity=room(), correct=True,
                                            shape="probably-fine")],
                            today="2026-08-06")
        self.assertEqual((gt.TRUTH_DIR / "s01.json").read_text(encoding="utf-8"),
                         before)

    def test_an_empty_verdict_list_writes_nothing(self):
        record_verdicts("s01", [], today="2026-08-06")
        self.assertFalse((gt.TRUTH_DIR / "s01.json").exists())
        sheets = json.loads(corpus.MANIFEST_PATH.read_text(encoding="utf-8"))["sheets"]
        self.assertNotIn("labeled", {s["slug"]: s for s in sheets}["s01"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_verdicts -v
```

Expected: `ModuleNotFoundError: No module named 'regression.verdicts'`

- [ ] **Step 3: Add `set_labeled` to `regression/corpus.py`**

Append:

```python
def set_labeled(slug: str, value: bool = True) -> None:
    """Flip a manifest entry's `labeled` flag and write the manifest back.

    `labeled: true` is the durable, diffable claim that a human recorded
    verdicts for this sheet -- the sweep fails when a flagged sheet's ground
    truth goes missing (see sweep._labeled_but_unreviewed), so setting it is
    what makes a review session's work impossible to lose silently.

    The manifest's on-disk order is preserved: `load_manifest` reads the file
    as written, unlike `manifest_sheets` which sorts a copy.
    """
    manifest = load_manifest()
    for entry in manifest.get("sheets", []):
        if entry["slug"] == slug:
            entry["labeled"] = value
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n",
                                     encoding="utf-8")
            return
    raise ValueError(f"{slug} is not in {MANIFEST_PATH}")
```

- [ ] **Step 4: Write `regression/verdicts.py`**

```python
"""Turning a human's selections into committed ground truth.

Pure and terminal-free on purpose. `tools/review.py` collects verdicts by
prompting; a future agent path collects them from flags. Both call
`record_verdicts`, so there is one writer and one set of invariants rather
than two code paths that drift.

The invariant that matters most: an entity id never reaches disk. Ids are
ordinal -- door_0015 becomes door_0014 the moment an earlier door stops being
detected -- so they identify a detection within one sweep's output and nothing
more. Ground truth is matched geometrically.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from regression.corpus import set_labeled, sheet_entry
from regression.ground_truth import (SHAPES, PageTruth, SheetTruth, TruthItem,
                                     dump_truth, load_truth)


@dataclass
class Verdict:
    """One decision about one detection.

    `entity` is the raw dict from a run's final_entities.json. `correct`
    is the reality axis (confirmed vs false positive); `shape` is the rooms-only
    second axis saying whether the stored polygon is the outline the user wants.
    """
    page: int
    entity: dict
    correct: bool
    shape: str | None = None
    note: str = ""


def _truth_item(verdict: Verdict) -> TruthItem:
    entity = verdict.entity
    raw_polygon = (entity.get("attributes") or {}).get("polygon")
    polygon = ([[float(x), float(y)] for x, y in raw_polygon]
               if raw_polygon and len(raw_polygon) >= 3 else None)
    return TruthItem(type=entity["entity_type"],
                     bbox=tuple(float(v) for v in entity["bbox"]),
                     note=verdict.note,
                     polygon=polygon,
                     shape=verdict.shape)


def record_verdicts(slug: str, verdicts: list[Verdict],
                    today: str | None = None) -> Path | None:
    """Append verdicts to a sheet's ground truth and flag it labeled.

    Returns the ground-truth path, or None when there was nothing to record.

    Everything is validated before anything is written: a bad shape value or an
    unknown slug must not leave a half-written file behind, because a review
    session that dies mid-sheet would otherwise corrupt verdicts recorded
    months earlier.
    """
    if not verdicts:
        return None

    entry = sheet_entry(slug)
    if entry is None:
        raise ValueError(f"{slug} is not in fixtures/MANIFEST.json")
    for verdict in verdicts:
        if verdict.shape is not None and verdict.shape not in SHAPES:
            raise ValueError(f"{slug}: shape must be one of {list(SHAPES)}, "
                             f"got {verdict.shape!r}")
        if verdict.page < 1:
            raise ValueError(f"{slug}: page numbers are 1-based, "
                             f"got {verdict.page}")

    truth: SheetTruth = load_truth(slug)
    truth.slug = slug
    truth.pdf_sha256 = truth.pdf_sha256 or entry["sha256"]
    truth.reviewed = today or datetime.date.today().isoformat()

    for verdict in verdicts:
        page = truth.pages.setdefault(verdict.page, PageTruth())
        target = page.confirmed if verdict.correct else page.false_positives
        target.append(_truth_item(verdict))

    path = dump_truth(truth)
    set_labeled(slug, True)
    return path
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
source .venv/bin/activate && python -m unittest tests.test_verdicts -v
```

Expected: 13 tests, OK

- [ ] **Step 6: Run the full suite**

```bash
source .venv/bin/activate && python -m unittest discover tests
```

Expected: OK

- [ ] **Step 7: Commit**

```bash
git add regression/verdicts.py regression/corpus.py tests/test_verdicts.py
git commit -m "feat: verdict writer records selections into ground truth"
```

---

## Task 5: Per-category review images

What the user actually looks at. One image per page per entity type, showing only that type's unreviewed detections, each stamped with a short id that matches the terminal list.

Per-category rather than combined because the review loop is per-category: the doors pass must not be cluttered with windows.

**Files:**
- Create: `regression/review_render.py`
- Test: `tests/test_review_render.py`

**Interfaces:**
- Consumes: `extraction.renderer._load_font`, `._draw_entity_box`, `._draw_entity_polygon`, `.FONT_SIZE`, `.OVERLAY_COLORS`, `.ROOM_COLORS`
- Produces:
  - `regression.review_render.short_id(entity_id: str) -> str`
  - `regression.review_render.write_review_overlays(page_dir: Path, unreviewed: list[dict]) -> list[Path]`

Those renderer helpers are module-private by naming convention. Importing them is deliberate intra-repo reuse — reimplementing dashed boxes, polygon fills and label placement would duplicate ~60 lines and let the review image drift from the overlay the user already knows. Do not modify `extraction/renderer.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_review_render.py`:

```python
"""Review images: one per page per entity type, ids stamped on."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from regression.review_render import short_id, write_review_overlays


class ShortIdTests(unittest.TestCase):
    def test_known_types_get_a_one_letter_prefix(self):
        self.assertEqual(short_id("door_0007"), "d7")
        self.assertEqual(short_id("window_0003"), "w3")
        self.assertEqual(short_id("room_0002"), "r2")
        self.assertEqual(short_id("label_0011"), "l11")
        self.assertEqual(short_id("schedule_0001"), "s1")

    def test_an_unparseable_id_is_returned_whole(self):
        self.assertEqual(short_id("weird"), "weird")
        self.assertEqual(short_id("door_abc"), "door_abc")


class ReviewOverlayTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.page_dir = Path(self._tmp.name)
        Image.new("RGB", (400, 300), "white").save(self.page_dir / "render.png")

    def _door(self, entity_id="door_0007"):
        return {"entity_id": entity_id, "entity_type": "door",
                "bbox": [10.0, 10.0, 60.0, 50.0], "confidence": 0.82,
                "attributes": {}}

    def _window(self):
        return {"entity_id": "window_0003", "entity_type": "window",
                "bbox": [100.0, 10.0, 160.0, 30.0], "confidence": 0.9,
                "attributes": {}}

    def _room(self):
        return {"entity_id": "room_0002", "entity_type": "room",
                "bbox": [0.0, 0.0, 200.0, 200.0], "confidence": 0.9,
                "attributes": {"polygon": [[10.0, 100.0], [190.0, 100.0],
                                           [190.0, 200.0], [10.0, 200.0]]}}

    def test_one_image_per_entity_type(self):
        written = write_review_overlays(
            self.page_dir, [self._door(), self._door("door_0011"), self._window()])
        self.assertEqual([p.name for p in written],
                         ["review_door.png", "review_window.png"])
        for path in written:
            self.assertTrue(path.exists())

    def test_the_image_matches_the_render_size(self):
        written = write_review_overlays(self.page_dir, [self._door()])
        with Image.open(written[0]) as image:
            self.assertEqual(image.size, (400, 300))

    def test_something_is_actually_drawn(self):
        written = write_review_overlays(self.page_dir, [self._door()])
        with Image.open(written[0]).convert("RGB") as image:
            colors = {image.getpixel((x, y))
                      for x in range(0, 400, 4) for y in range(0, 300, 4)}
        self.assertGreater(len(colors), 1, "review image is still blank white")

    def test_a_room_is_drawn_without_crashing_on_its_polygon(self):
        written = write_review_overlays(self.page_dir, [self._room()])
        self.assertEqual([p.name for p in written], ["review_room.png"])

    def test_nothing_unreviewed_writes_nothing(self):
        self.assertEqual(write_review_overlays(self.page_dir, []), [])
        self.assertEqual(sorted(p.name for p in self.page_dir.iterdir()),
                         ["render.png"])

    def test_a_missing_render_is_not_an_error(self):
        (self.page_dir / "render.png").unlink()
        self.assertEqual(write_review_overlays(self.page_dir, [self._door()]), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_review_render -v
```

Expected: `ModuleNotFoundError: No module named 'regression.review_render'`

- [ ] **Step 3: Write the implementation**

Create `regression/review_render.py`:

```python
"""The images a human looks at while giving verdicts.

One PNG per page per entity type, carrying only that type's unreviewed
detections. Per-category rather than one combined image because the review
loop itself is per-category: the doors pass should not be cluttered with
windows.

Each detection is stamped with a short id (door_0007 -> d7) matching the
terminal list, so a line and a shape can be paired by eye without reading
coordinates.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Private by naming convention, imported deliberately: reimplementing dashed
# boxes, polygon fills and label placement would duplicate the drawing code and
# let review images drift from the overlay.png the user already reads.
from extraction.renderer import (FONT_SIZE, OVERLAY_COLORS, ROOM_COLORS,
                                 _draw_entity_box, _draw_entity_polygon,
                                 _load_font)

SHORT_PREFIX = {"door": "d", "window": "w", "room": "r",
                "label": "l", "schedule": "s"}


def short_id(entity_id: str) -> str:
    """door_0007 -> d7. Unparseable ids are returned unchanged."""
    kind, _, ordinal = entity_id.rpartition("_")
    if not kind or not ordinal.isdigit():
        return entity_id
    prefix = SHORT_PREFIX.get(kind, kind[:1])
    return f"{prefix}{int(ordinal)}"


def write_review_overlays(page_dir: Path, unreviewed: list[dict]) -> list[Path]:
    """Draw one review_<type>.png per entity type present in `unreviewed`.

    Returns the paths written, sorted by type. A page with nothing to review
    -- or with no render to draw on, which happens when a sweep was run
    without persisting output -- writes nothing rather than raising: an
    unreviewable page must not take a whole sweep down.
    """
    render = page_dir / "render.png"
    if not unreviewed or not render.exists():
        return []

    by_type: dict[str, list[dict]] = {}
    for entity in unreviewed:
        by_type.setdefault(entity["entity_type"], []).append(entity)

    written: list[Path] = []
    font = _load_font(FONT_SIZE)
    for etype, items in sorted(by_type.items()):
        with Image.open(render) as source:
            image = source.convert("RGBA")
        draw = ImageDraw.Draw(image)
        for index, entity in enumerate(items):
            # Rooms cycle colours so adjacent polygons stay distinguishable;
            # every other type keeps its one overlay colour.
            color = (ROOM_COLORS[index % len(ROOM_COLORS)] if etype == "room"
                     else OVERLAY_COLORS.get(etype, OVERLAY_COLORS["unknown"]))
            label = f"{short_id(entity['entity_id'])} {entity.get('confidence', 0):.2f}"
            polygon = (entity.get("attributes") or {}).get("polygon")
            if polygon and len(polygon) >= 3:
                _draw_entity_polygon(image, draw, polygon, color, label, font=font)
            else:
                _draw_entity_box(image, draw, tuple(entity["bbox"]), color, label,
                                 font=font)
        out = page_dir / f"review_{etype}.png"
        image.convert("RGB").save(out)
        written.append(out)
    return written
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
source .venv/bin/activate && python -m unittest tests.test_review_render -v
```

Expected: 8 tests, OK

- [ ] **Step 5: Commit**

```bash
git add regression/review_render.py tests/test_review_render.py
git commit -m "feat: per-category review images with short entity ids"
```

---

## Task 6: Wire the sweep to persist and draw

Replace the temp directory with the persistent one, keep the debug viewer, and draw the review images. This is the task that makes the previous five visible from `python tools/regress.py`.

**Files:**
- Modify: `regression/sweep.py:9-18` (imports), `:86-116` (`score_sheet`), `:152-158` (the extraction block)
- Modify: `regression/report.py:32-36` (`SheetResult.unreviewed_by_page`)
- Test: `tests/test_sweep.py`

**Interfaces:**
- Consumes: `run_dir.reset_slug_dir`, `run_dir.latest_run`, `review_render.write_review_overlays`, `report.SheetResult.run_dir` (Task 2)
- Produces: `SheetResult.unreviewed_by_page: dict[int, list[dict]]` — unreviewed entities keyed by 1-based page number. `SheetResult.unreviewed` stays the flat list it is today.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sweep.py` (reuse the file's existing imports; add what is missing):

```python
class UnreviewedByPageTests(unittest.TestCase):
    def _entity(self, entity_id, bbox):
        return {"entity_id": entity_id, "entity_type": "door",
                "bbox": list(bbox), "confidence": 0.8, "attributes": {}}

    def test_unreviewed_is_grouped_by_page(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))],
                 2: [self._entity("door_0002", (20, 20, 30, 30)),
                     self._entity("door_0003", (40, 40, 50, 50))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(sorted(result.unreviewed_by_page), [1, 2])
        self.assertEqual(len(result.unreviewed_by_page[1]), 1)
        self.assertEqual(len(result.unreviewed_by_page[2]), 2)

    def test_the_flat_unreviewed_list_still_holds_everything(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))],
                 2: [self._entity("door_0002", (20, 20, 30, 30))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(len(result.unreviewed), 2)

    def test_a_page_with_nothing_unreviewed_gets_no_entry(self):
        truth = SheetTruth(slug="s01", reviewed="2026-08-06")
        truth.pages[1] = PageTruth(confirmed=[
            TruthItem(type="door", bbox=(0.0, 0.0, 10.0, 10.0))])
        pages = {1: [self._entity("door_0001", (0, 0, 10, 10))]}

        result = score_sheet("s01", truth, pages)

        self.assertEqual(result.unreviewed_by_page, {})
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_sweep -v
```

Expected: `AttributeError: 'SheetResult' object has no attribute 'unreviewed_by_page'`

- [ ] **Step 3: Add the field to `regression/report.py`**

In `SheetResult`, after `run_dir`:

```python
    # Unreviewed entities keyed by 1-based page number. `unreviewed` stays the
    # flat list the report prints; this is what review images and the review
    # session need, because an entity means nothing without its page.
    unreviewed_by_page: dict[int, list[dict]] = field(default_factory=dict)
```

- [ ] **Step 4: Fill it in `regression/sweep.py::score_sheet`**

Inside the `for number, entities in sorted(pages.items()):` loop, after
`result.unreviewed += scored["unreviewed"]`:

```python
        if scored["unreviewed"]:
            result.unreviewed_by_page[number] = scored["unreviewed"]
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
source .venv/bin/activate && python -m unittest tests.test_sweep -v
```

Expected: OK

- [ ] **Step 6: Replace the temp directory in `regression/sweep.py::sweep`**

Update the imports at the top:

```python
from regression.review_render import write_review_overlays
from regression.run_dir import latest_run, reset_slug_dir
```

and drop `import tempfile`.

Replace the extraction block (currently lines 152-158):

```python
        # Output is persisted, not thrown away: the render, the overlay and the
        # debug viewer are what the human needs to judge REVIEW items, and a
        # TemporaryDirectory deleted all three microseconds after writing them.
        # reset_slug_dir is called exactly once -- it wipes the previous sweep,
        # so a second call would delete the run that just finished.
        out_parent = reset_slug_dir(slug)
        run_extract(str(path), list(range(entry["pages"])),
                    out_parent=str(out_parent), skip_gemini=True, debug=True)
        run = latest_run(slug)
        pages = _entities_by_page(str(run)) if run else {}
        cache_miss = _cache_missed(str(run)) if run else False

        result = score_sheet(slug, truth, pages, cache_miss=cache_miss)
        if run is not None:
            result.run_dir = str(run)
            for number, unreviewed in result.unreviewed_by_page.items():
                write_review_overlays(run / "pages" / f"page_{number:02d}",
                                      unreviewed)
        results.append(result)
```

The old block ended with `results.append(score_sheet(...))` and was indented
inside a `with tempfile.TemporaryDirectory() as out_parent:` — delete both. The
result is appended above, at the loop's own indentation.

- [ ] **Step 7: Update the module docstring in `regression/sweep.py`**

Replace the first paragraph's temp-directory claim:

```python
"""Run the pipeline over corpus sheets and score the output.

Sheets are extracted with skip_gemini=True: the region-classification cache
ships with the bundle, so a sweep is offline and deterministic. A cache miss
means detection ran over the whole page instead of the floor-plan regions --
which changes what is detected -- so it is surfaced per sheet.

Output is persisted under outputs/regress/<slug>/ (gitignored) rather than a
temp directory, and each sheet is extracted with debug=True: the render, the
overlay, the debug viewer and the per-category review images are what a human
needs in order to act on a REVIEW line, and they used to be deleted the instant
scoring finished.
"""
```

- [ ] **Step 8: Verify end to end on one sheet**

```bash
source .venv/bin/activate && python tools/regress.py --sheet s01; echo "exit=$?"
ls outputs/regress/s01/*/pages/page_01/
```

Expected: exit 0, and the page directory contains `render.png`, `overlay.png`,
`final_entities.json`, `debug_trace.json`, `debug_viewer.html`, and
`review_<type>.png` for each type with unreviewed detections. The report's
REVIEW lines name `door_NNNN` and end with an `images:` line.

- [ ] **Step 9: Measure the debug-trace cost (spec open question 1)**

```bash
source .venv/bin/activate
python - <<'PY'
import time, shutil
from pathlib import Path
from pipeline import run_extract
from regression.corpus import sheet_entry, sheet_path
from regression.run_dir import reset_slug_dir, latest_run

def size_mb(p): return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) / 1e6

for debug in (False, True):
    out = reset_slug_dir("s01-timing")
    t0 = time.perf_counter()
    run_extract(str(sheet_path("s01")), list(range(sheet_entry("s01")["pages"])),
                out_parent=str(out), skip_gemini=True, debug=debug)
    print(f"debug={debug}  {time.perf_counter()-t0:.1f}s  {size_mb(latest_run('s01-timing')):.1f}MB")
shutil.rmtree(Path(out).parent / "s01-timing", ignore_errors=True)
PY
```

**Decision rule from the spec:** if `debug=True` costs more than +30% wall time
or more than 100MB for one sheet, change the `sweep()` call to
`debug=debug_traces` with a `debug_traces: bool = False` parameter, thread a
`--debug` flag through `tools/regress.py`, and record the measured numbers in
the commit message. Otherwise keep `debug=True` unconditional and record the
numbers anyway.

- [ ] **Step 10: Run the full suite**

```bash
source .venv/bin/activate && python -m unittest discover tests
```

Expected: OK

- [ ] **Step 11: Commit**

```bash
git add regression/sweep.py regression/report.py tests/test_sweep.py
git commit -m "feat: sweeps persist their output and draw review images

Measured on s01: debug=False Xs/YMB, debug=True Xs/YMB."
```

Replace the X/Y placeholders with the numbers from step 9. Do not commit the
literal placeholders.

---

## Task 7: `tools/review.py` — the interactive walk

The user-facing command. Sheet → page → category, two selection passes per
category, rooms get a shape prompt. All logic lives in `review_session.py` so
it is testable without a TTY; `tools/review.py` is prompts and printing only.

**Two passes, not one.** A single checkbox forces a binary — ticked correct,
unticked wrong — and "I cannot tell from this image" is a real and common
answer. Forcing it into `false_positives` poisons ground truth permanently.
Pass 1 selects correct; pass 2 runs over pass 1's leftovers and selects wrong;
anything unticked in both stays unreviewed and comes back next sweep.

**Files:**
- Create: `regression/review_session.py`
- Create: `tools/review.py`
- Modify: `requirements.txt`
- Test: `tests/test_review_session.py`

**Interfaces:**
- Consumes: `run_dir.latest_run`, `sweep.evaluate_page`, `sweep._entities_by_page`, `ground_truth.load_truth`, `verdicts.Verdict`, `verdicts.record_verdicts`, `review_render.short_id`
- Produces:
  - `regression.review_session.CATEGORY_ORDER: tuple[str, ...]`
  - `regression.review_session.pending(slug: str) -> dict[int, dict[str, list[dict]]]` — page → entity type → unreviewed entities, types in `CATEGORY_ORDER`
  - `regression.review_session.SweepOutputMissing` — raised when the slug has no persisted run

- [ ] **Step 1: Add the dependency**

Append to `requirements.txt`:

```
InquirerPy>=0.3.4
```

Then:

```bash
source .venv/bin/activate && pip install 'InquirerPy>=0.3.4'
```

`InquirerPy` is a dev-tool dependency: only `tools/review.py` imports it.
Nothing in `pipeline.py`, `detection/` or `extraction/` may import it, so a
production run never needs it installed.

- [ ] **Step 2: Write the failing test**

Create `tests/test_review_session.py`:

```python
"""What is still unreviewed in a persisted sweep, per page and category."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from regression import ground_truth as gt, run_dir
from regression.review_session import (CATEGORY_ORDER, SweepOutputMissing,
                                       pending)


def entity(entity_id, etype, bbox, confidence=0.8, attributes=None):
    return {"entity_id": entity_id, "entity_type": etype, "bbox": list(bbox),
            "confidence": confidence, "attributes": attributes or {}}


class PendingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)

        self._regress_out = run_dir.REGRESS_OUT
        run_dir.REGRESS_OUT = root / "regress"
        self.addCleanup(lambda: setattr(run_dir, "REGRESS_OUT", self._regress_out))

        self._truth_dir = gt.TRUTH_DIR
        gt.TRUTH_DIR = root / "ground_truth"
        gt.TRUTH_DIR.mkdir()
        self.addCleanup(lambda: setattr(gt, "TRUTH_DIR", self._truth_dir))

    def _persist(self, slug, pages: dict[int, list[dict]]):
        run = run_dir.reset_slug_dir(slug) / "2026-08-06_15-19-08"
        for number, entities in pages.items():
            page_dir = run / "pages" / f"page_{number:02d}"
            page_dir.mkdir(parents=True)
            (page_dir / "final_entities.json").write_text(
                json.dumps({"entities": entities, "rejected": []}),
                encoding="utf-8")
        return run

    def test_a_slug_with_no_persisted_run_raises(self):
        with self.assertRaises(SweepOutputMissing):
            pending("s01")

    def test_everything_is_pending_on_an_unlabeled_sheet(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10)),
                                  entity("window_0001", "window", (20, 20, 30, 30))]})
        result = pending("s01")
        self.assertEqual(sorted(result), [1])
        self.assertEqual(sorted(result[1]), ["door", "window"])

    def test_categories_come_back_in_the_review_order(self):
        self._persist("s01", {1: [entity("window_0001", "window", (20, 20, 30, 30)),
                                  entity("room_0001", "room", (0, 0, 50, 50)),
                                  entity("door_0001", "door", (0, 0, 10, 10))]})
        self.assertEqual(list(pending("s01")[1]), ["door", "window", "room"])

    def test_an_already_confirmed_detection_is_not_pending(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "aaa", "reviewed": "2026-08-06",
            "pages": {"1": {"confirmed": [
                {"type": "door", "bbox": [0.0, 0.0, 10.0, 10.0]}]}},
        }, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(pending("s01"), {})

    def test_an_already_rejected_detection_is_not_pending(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))]})
        (gt.TRUTH_DIR / "s01.json").write_text(json.dumps({
            "sheet": "s01", "pdf_sha256": "aaa", "reviewed": "2026-08-06",
            "pages": {"1": {"false_positives": [
                {"type": "door", "bbox": [0.0, 0.0, 10.0, 10.0]}]}},
        }, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(pending("s01"), {})

    def test_pages_with_nothing_pending_are_dropped(self):
        self._persist("s01", {1: [entity("door_0001", "door", (0, 0, 10, 10))],
                              2: []})
        self.assertEqual(sorted(pending("s01")), [1])

    def test_the_category_order_covers_every_detected_type(self):
        self.assertEqual(set(CATEGORY_ORDER),
                         {"door", "window", "room", "label", "schedule"})

    def test_an_unexpected_type_still_comes_back_last(self):
        self._persist("s01", {1: [entity("mystery_0001", "mystery", (0, 0, 5, 5)),
                                  entity("door_0001", "door", (0, 0, 10, 10))]})
        self.assertEqual(list(pending("s01")[1]), ["door", "mystery"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
source .venv/bin/activate && python -m unittest tests.test_review_session -v
```

Expected: `ModuleNotFoundError: No module named 'regression.review_session'`

- [ ] **Step 4: Write `regression/review_session.py`**

```python
"""What a persisted sweep still needs verdicts on.

Reads the run output the sweep left behind and the ground truth recorded so
far, and reports what matched neither -- per page, grouped by entity type in
review order. Deliberately re-scores rather than serializing sweep state: the
sweep and the review session then agree by construction, and a review session
started days later still sees exactly what the report printed.

No detection is re-run. A sweep must have been run first.
"""
from __future__ import annotations

from regression.ground_truth import load_truth
from regression.run_dir import latest_run
from regression.sweep import _entities_by_page, evaluate_page

# Doors first because they are the most numerous and the most often wrong;
# rooms last because judging a room is slower than judging a door and the
# earlier passes warm up the eye on the same drawing.
CATEGORY_ORDER = ("door", "window", "room", "label", "schedule")


class SweepOutputMissing(RuntimeError):
    """No persisted sweep output for this slug."""


def _ordered(types: list[str]) -> list[str]:
    known = [t for t in CATEGORY_ORDER if t in types]
    unknown = sorted(t for t in types if t not in CATEGORY_ORDER)
    return known + unknown


def pending(slug: str) -> dict[int, dict[str, list[dict]]]:
    """Unreviewed detections, keyed by 1-based page then entity type.

    Pages and types with nothing left to review are omitted entirely, so an
    empty return means the sheet is fully reviewed.
    """
    run = latest_run(slug)
    if run is None:
        raise SweepOutputMissing(
            f"no persisted sweep output for {slug} — "
            f"run: python tools/regress.py --sheet {slug}")

    truth = load_truth(slug)
    result: dict[int, dict[str, list[dict]]] = {}
    for number, entities in sorted(_entities_by_page(str(run)).items()):
        unreviewed = evaluate_page(truth.page(number), entities)["unreviewed"]
        if not unreviewed:
            continue
        by_type: dict[str, list[dict]] = {}
        for entity in unreviewed:
            by_type.setdefault(entity["entity_type"], []).append(entity)
        result[number] = {t: by_type[t] for t in _ordered(list(by_type))}
    return result
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
source .venv/bin/activate && python -m unittest tests.test_review_session -v
```

Expected: 8 tests, OK

- [ ] **Step 6: Write `tools/review.py`**

```python
#!/usr/bin/env python3
# tools/review.py
"""Record verdicts on a sweep's new detections, by ticking a list.

Usage:
    python tools/review.py            # every sheet with unreviewed detections
    python tools/review.py s01        # one sheet
    python tools/review.py s01 s07    # several

Reads the output `python tools/regress.py` persisted under
outputs/regress/<slug>/. It never re-runs detection: run the sweep first.

The walk is sheet -> page -> category. Each category prints the path to its
review image, then asks twice: which are CORRECT, then which of the rest are
WRONG. Anything ticked in neither stays unreviewed and comes back next sweep,
so "I cannot tell from this image" costs nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from InquirerPy import inquirer  # noqa: E402
from InquirerPy.base.control import Choice  # noqa: E402

from regression.corpus import manifest_sheets  # noqa: E402
from regression.review_render import short_id  # noqa: E402
from regression.review_session import SweepOutputMissing, pending  # noqa: E402
from regression.run_dir import latest_run  # noqa: E402
from regression.verdicts import Verdict, record_verdicts  # noqa: E402


def _centre(bbox) -> str:
    return f"({round((bbox[0] + bbox[2]) / 2)},{round((bbox[1] + bbox[3]) / 2)})"


def _choice(entity: dict) -> Choice:
    return Choice(entity["entity_id"],
                  name=f"{short_id(entity['entity_id']):<6} "
                       f"conf {entity.get('confidence', 0):.2f}  "
                       f"{_centre(entity['bbox'])}")


def _pick(message: str, entities: list[dict]) -> set[str]:
    """Multi-select over entities; returns the chosen entity ids."""
    if not entities:
        return set()
    chosen = inquirer.fuzzy(
        message=message,
        choices=[_choice(e) for e in entities],
        multiselect=True,
        border=True,
        instruction="(type to filter, tab to tick, enter to submit)",
        transformer=lambda picked: f"{len(picked)} selected",
    ).execute()
    return set(chosen or [])


def _shape_and_note(entity: dict) -> tuple[str, str]:
    shape = inquirer.select(
        message=f"  {short_id(entity['entity_id'])} — is this polygon the "
                f"shape you want?",
        choices=[
            Choice("partial", name="partial  — real room, shape not right yet"),
            Choice("approved", name="approved — this shape is correct"),
        ],
        default="partial",
    ).execute()
    note = inquirer.text(message="  note (optional):").execute()
    return shape, note.strip()


def review_sheet(slug: str) -> int:
    """Walk one sheet's pending detections. Returns how many were recorded."""
    try:
        by_page = pending(slug)
    except SweepOutputMissing as exc:
        print(f"{slug}: {exc}")
        return 0

    if not by_page:
        print(f"{slug}: nothing to review")
        return 0

    run = latest_run(slug)
    verdicts: list[Verdict] = []
    for number, by_type in sorted(by_page.items()):
        page_dir = run / "pages" / f"page_{number:02d}"
        for etype, entities in by_type.items():
            image = page_dir / f"review_{etype}.png"
            print(f"\n{slug} page {number} — {etype.upper()}S "
                  f"({len(entities)} unreviewed)")
            print(f"  open: {image}")

            correct = _pick(f"Select CORRECT {etype}s", entities)
            leftovers = [e for e in entities if e["entity_id"] not in correct]
            wrong = _pick(f"Of the remaining {len(leftovers)} — select the ones "
                          f"that are WRONG (leave unticked to postpone)",
                          leftovers)

            for entity in entities:
                entity_id = entity["entity_id"]
                if entity_id in correct:
                    shape, note = (_shape_and_note(entity)
                                   if etype == "room" else (None, ""))
                    verdicts.append(Verdict(page=number, entity=entity,
                                            correct=True, shape=shape, note=note))
                elif entity_id in wrong:
                    verdicts.append(Verdict(page=number, entity=entity,
                                            correct=False))

    if not verdicts:
        print(f"\n{slug}: nothing recorded — every detection postponed")
        return 0

    # Written once, after the whole sheet: an interrupted session loses at most
    # the sheet in progress rather than half-writing a page.
    path = record_verdicts(slug, verdicts)
    confirmed = sum(1 for v in verdicts if v.correct)
    print(f"\n{slug}: wrote {path} "
          f"(+{confirmed} confirmed, +{len(verdicts) - confirmed} false positives)")
    print(f"  commit: git add {path} fixtures/MANIFEST.json")
    return len(verdicts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*",
                        help="slugs to review; default is every corpus sheet")
    args = parser.parse_args()

    slugs = args.slugs or [s["slug"] for s in manifest_sheets()
                           if s.get("tier") != "retired"]
    for slug in slugs:
        review_sheet(slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 7: Verify the toggle keybinding**

`InquirerPy`'s fuzzy prompt uses the space bar for its search filter, so the
multi-select toggle is a different key. Run:

```bash
source .venv/bin/activate && python tools/review.py s01
```

Tick a couple of entries and confirm the key named in the `instruction=` string
is the one that actually toggles. If it is not `tab`, correct the instruction
string in `_pick` to the real key. **Do not leave a wrong keybinding in the
prompt text** — it is the only instruction the user gets.

Then press Ctrl-C at the first prompt and confirm nothing was written:

```bash
git status --short tests/ground_truth/ fixtures/MANIFEST.json
```

Expected: no changes.

- [ ] **Step 8: Walk one real sheet end to end**

```bash
source .venv/bin/activate
python tools/regress.py --sheet s01
python tools/review.py s01
git diff tests/ground_truth/s01.json fixtures/MANIFEST.json
```

Expected: the diff appends the verdicts just given, `reviewed` updates to
today, `"labeled": true` is present on s01's manifest entry, and no
`entity_id` string appears anywhere in the diff.

- [ ] **Step 9: Confirm the sweep now sees the new verdicts**

```bash
source .venv/bin/activate && python tools/regress.py --sheet s01; echo "exit=$?"
```

Expected: exit 0. Detections confirmed in step 8 now count under `door N/N`;
rejected ones no longer appear as REVIEW; postponed ones still do.

- [ ] **Step 10: Run the full suite**

```bash
source .venv/bin/activate && python -m unittest discover tests
```

Expected: OK, under ~10s.

- [ ] **Step 11: Commit**

```bash
git add regression/review_session.py tools/review.py requirements.txt \
        tests/test_review_session.py
git commit -m "feat: interactive verdict recording with tools/review.py"
```

Commit the ground-truth changes from step 8 separately — a data commit, not a
code commit:

```bash
git add tests/ground_truth/s01.json fixtures/MANIFEST.json
git commit -m "data: verdicts for s01"
```

---

## Task 8: Documentation

`docs/regression-testing-guide.md` describes the old loop — open
`debug_viewer.html`, read off path indices, hand-edit ground truth. That is now
wrong in three places and would send a future session down the deleted path.

**Files:**
- Modify: `docs/regression-testing-guide.md`
- Modify: `CLAUDE.md` (the "Regression testing" section's numbered loop)

**Interfaces:**
- Consumes: everything above
- Produces: nothing

- [ ] **Step 1: Read the current guide**

```bash
source .venv/bin/activate && cat docs/regression-testing-guide.md
```

- [ ] **Step 2: Update the guide**

Replace every description of hand-editing ground truth with the new loop, and
add a section covering:

- Sweep output now lives at `outputs/regress/<slug>/<timestamp>/pages/page_NN/`
  and is wiped per slug on each sweep — copy anything you want to keep.
- `review_<type>.png` is the image to open; short ids (`d7`) on it match the
  terminal list; `debug_viewer.html` is still there for the hard cases.
- `python tools/review.py <slug>` records verdicts. Two passes per category:
  correct, then wrong. Unticked in both = postponed, reappears next sweep.
- Rooms carry a second axis: `shape: partial` means "real room, polygon not
  right yet" and is a baseline, not an ideal; `shape: approved` means signed
  off. V1 records it; drift scoring is V2 and not built yet.
- Ground truth is still committed as a data commit, separate from code.
- Entity ids are ordinal and never appear in ground truth — do not hand-write
  them into it.

- [ ] **Step 3: Update `CLAUDE.md`**

In the "Regression testing" section, replace step 2 and step 3 of the numbered
loop:

```markdown
2. Open `outputs/regress/<slug>/<timestamp>/pages/page_NN/review_<type>.png`
   — every unreviewed detection is stamped with a short id (`d7` = door_0007)
   matching the sweep's REVIEW lines. `debug_viewer.html` sits beside it for
   tracing a specific miss.
3. `python tools/review.py <slug>` — tick the correct detections, then the
   wrong ones; anything ticked in neither is postponed and reappears next
   sweep. It writes `tests/ground_truth/<slug>.json` and sets
   `"labeled": true` in `fixtures/MANIFEST.json`. Commit both as a data commit.
```

- [ ] **Step 4: Verify the guide's commands actually run**

Run every command block quoted in the updated guide and confirm each succeeds.
A guide with a stale command is worse than no guide.

- [ ] **Step 5: Update the knowledge graph**

```bash
graphify update .
```

- [ ] **Step 6: Commit**

```bash
git add docs/regression-testing-guide.md CLAUDE.md graphify-out/
git commit -m "docs: the review-tooling regression loop"
```

---

## Done when

- [ ] `python tools/regress.py --sheet s01` leaves `outputs/regress/s01/<ts>/` on disk with review images and a debug viewer
- [ ] REVIEW lines name `door_NNNN` and point at the image directory
- [ ] `python tools/review.py s01` walks sheet → page → category and records verdicts without any JSON being hand-edited
- [ ] `tests/ground_truth/s01.json` contains no `entity_id`
- [ ] Room verdicts carry `polygon` and `shape`
- [ ] `python -m unittest discover tests` passes in under ~10s
- [ ] The debug-trace measurement from Task 6 step 9 is recorded in a commit message
- [ ] `docs/regression-testing-guide.md` describes the loop that exists

## Out of scope (V2)

Room drift scoring (polygon IoU bands, accept-new-baseline pass) and the agent
flags (`--confirm/--reject/--accept-shape`). Both are guards over labels that do
not exist yet. See pieces 6–7 of the spec.
