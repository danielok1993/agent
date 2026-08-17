"""Before/after comparison of two sweeps of one slug.

The sweep report speaks in verdict deltas — "LOST window @ (3951,2202)",
"REVIEW new window_0012" — which is the right signal for a gate but tells a
human nothing about WHAT changed on the drawing. And a re-sweep wipes the
slug's previous run, so there is normally no "before" left to look at.

This module keeps a baseline (`snapshot`) and renders the two runs against
each other (`compare_runs`):

  * a side-by-side page image, every entity of both runs drawn and coloured
    by its ground-truth verdict (confirmed / false positive / deferred /
    unreviewed), so a glance shows which reds vanished and which greens
    survived;
  * a strip of zoomed before|after crops, one row per entity that exists in
    only one of the runs (matched across runs the same way the sweep matches
    ground truth: same type, IoU >= 0.5), each captioned with its id,
    confidence and verdict — the visual counterpart of the LOST/REVIEW lines;
  * a text summary of the same changes.

Entities are compared geometrically, never by id: ids are ordinal and shift
whenever an earlier detection appears or disappears.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from extraction.renderer import FONT_SIZE, _draw_entity_box, _draw_entity_polygon, _load_font
from regression.ground_truth import PageTruth, SheetTruth, TruthItem, load_truth
from regression.matching import match_entities
from regression.review_render import short_id
from regression.run_dir import REPO_ROOT, latest_run

BASELINE_OUT = REPO_ROOT / "outputs" / "regress_baseline"
COMPARE_OUT = REPO_ROOT / "outputs" / "compare"

# Verdict -> RGBA. Chosen for the question the image answers ("did the reds
# go away, did the greens stay?"), not for the entity type — the caption
# carries the type.
VERDICT_COLORS: dict[str, tuple[int, int, int, int]] = {
    "confirmed":      (0, 170, 0, 200),
    "false_positive": (220, 0, 0, 200),
    "deferred":       (255, 140, 0, 200),
    "unreviewed":     (0, 60, 230, 200),
}

# Zoom-crop geometry: padding around the entity bbox in page pixels, and the
# height every crop is scaled to so rows line up whatever the entity's size.
CROP_PAD_PX = 40
CROP_ROW_HEIGHT_PX = 180
CROP_MAX_WIDTH_PX = 900
SIDE_BY_SIDE_MAX_WIDTH_PX = 4200


@dataclass
class EntityChange:
    page: int
    kind: str            # "removed" (before only) | "added" (after only)
    entity: dict
    verdict: str         # key of VERDICT_COLORS


@dataclass
class PageComparison:
    page: int
    before: list[dict]
    after: list[dict]
    before_verdicts: dict[str, str]   # entity_id -> verdict
    after_verdicts: dict[str, str]
    changes: list[EntityChange] = field(default_factory=list)
    kept: int = 0
    images: list[Path] = field(default_factory=list)


# --------------------------------------------------------------------------
# Baseline bookkeeping
# --------------------------------------------------------------------------

def baseline_dir(slug: str) -> Path:
    return BASELINE_OUT / slug


def baseline_run(slug: str) -> Path | None:
    """The saved baseline run for this slug, or None."""
    base = baseline_dir(slug)
    if not base.is_dir():
        return None
    children = [p for p in base.iterdir() if p.is_dir()]
    return max(children, key=lambda p: p.name) if children else None


def snapshot(slug: str) -> Path:
    """Copy the slug's latest sweep run aside as its baseline.

    Exactly one baseline is kept per slug — a snapshot replaces the previous
    one, mirroring the sweep's one-run-per-slug rule so `baseline_run` is
    never a guess. Raises FileNotFoundError when the slug has no run.
    """
    run = latest_run(slug)
    if run is None:
        raise FileNotFoundError(f"{slug}: no sweep run to snapshot -- run "
                                f"`python tools/regress.py --sheet {slug}` first")
    base = baseline_dir(slug)
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    target = base / run.name
    shutil.copytree(run, target)
    return target


# --------------------------------------------------------------------------
# Diffing
# --------------------------------------------------------------------------

def _entities_by_page(run_dir: Path) -> dict[int, list[dict]]:
    pages: dict[int, list[dict]] = {}
    for path in sorted(run_dir.glob("pages/page_*/final_entities.json")):
        number = int(path.parent.name.split("_")[1])
        pages[number] = json.loads(path.read_text(encoding="utf-8")).get("entities", [])
    return pages


def classify(truth_page: PageTruth, entities: list[dict]) -> dict[str, str]:
    """entity_id -> verdict, using the sweep's own matching order
    (confirmed first, then false positives, then deferred; the rest is
    unreviewed)."""
    verdicts: dict[str, str] = {}
    remaining = entities
    for name, items in (("confirmed", truth_page.confirmed),
                        ("false_positive", truth_page.false_positives),
                        ("deferred", truth_page.deferred)):
        result = match_entities(items, remaining)
        for _item, ent in result.matched:
            verdicts[ent["entity_id"]] = name
        remaining = result.unmatched_actual
    for ent in remaining:
        verdicts[ent["entity_id"]] = "unreviewed"
    return verdicts


def diff_entities(before: list[dict], after: list[dict]) -> tuple[int, list[dict], list[dict]]:
    """(kept, removed, added): `before` entities paired to `after` entities by
    type + IoU >= 0.5, greedily best-first — the sweep's own rule."""
    as_truth = [TruthItem(type=e["entity_type"], bbox=tuple(e["bbox"])) for e in before]
    result = match_entities(as_truth, after)
    matched_before = {id(t) for t, _ in result.matched}
    removed = [e for e, t in zip(before, as_truth) if id(t) not in matched_before]
    return len(result.matched), removed, result.unmatched_actual


def compare_runs(before_dir: Path, after_dir: Path, truth: SheetTruth,
                 out_dir: Path, *, types: set[str] | None = None) -> list[PageComparison]:
    """Diff two runs page by page and write the comparison images to out_dir.

    `types` restricts the comparison to those entity types (None = all).
    """
    before_pages = _entities_by_page(before_dir)
    after_pages = _entities_by_page(after_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    comparisons: list[PageComparison] = []
    for page in sorted(set(before_pages) | set(after_pages)):
        b = [e for e in before_pages.get(page, []) if types is None or e["entity_type"] in types]
        a = [e for e in after_pages.get(page, []) if types is None or e["entity_type"] in types]
        truth_page = truth.page(page)
        cmp = PageComparison(page=page, before=b, after=a,
                             before_verdicts=classify(truth_page, b),
                             after_verdicts=classify(truth_page, a))
        cmp.kept, removed, added = diff_entities(b, a)
        cmp.changes = ([EntityChange(page, "removed", e, cmp.before_verdicts[e["entity_id"]]) for e in removed]
                       + [EntityChange(page, "added", e, cmp.after_verdicts[e["entity_id"]]) for e in added])
        cmp.changes.sort(key=lambda c: (c.entity["entity_type"], c.kind, c.entity["bbox"][1], c.entity["bbox"][0]))

        render_before = before_dir / "pages" / f"page_{page:02d}" / "render.png"
        render_after = after_dir / "pages" / f"page_{page:02d}" / "render.png"
        if render_before.exists() and render_after.exists():
            cmp.images.append(_write_side_by_side(cmp, render_before, render_after, out_dir))
            if cmp.changes:
                cmp.images.append(_write_changes_strip(cmp, render_before, render_after, out_dir))
        comparisons.append(cmp)
    return comparisons


def compare(slug: str, *, before_dir: Path | None = None, after_dir: Path | None = None,
            out_dir: Path | None = None, types: set[str] | None = None) -> tuple[list[PageComparison], Path]:
    """Compare a slug's baseline against its latest run (or two explicit run
    dirs). Returns (comparisons, out_dir)."""
    before = before_dir or baseline_run(slug)
    after = after_dir or latest_run(slug)
    if before is None:
        raise FileNotFoundError(f"{slug}: no baseline -- run "
                                f"`python tools/compare_sweeps.py {slug} --snapshot` after a "
                                f"baseline sweep, or pass --before DIR")
    if after is None:
        raise FileNotFoundError(f"{slug}: no sweep run to compare -- run "
                                f"`python tools/regress.py --sheet {slug}` first, or pass --after DIR")
    out = out_dir or (COMPARE_OUT / slug)
    if out.exists():
        shutil.rmtree(out)
    return compare_runs(Path(before), Path(after), load_truth(slug), out, types=types), out


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _draw_entities(image: Image.Image, entities: list[dict], verdicts: dict[str, str]) -> Image.Image:
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    font = _load_font(FONT_SIZE)
    for ent in entities:
        color = VERDICT_COLORS[verdicts[ent["entity_id"]]]
        label = f"{short_id(ent['entity_id'])} {ent.get('confidence', 0):.2f}"
        polygon = (ent.get("attributes") or {}).get("polygon")
        if polygon and len(polygon) >= 3:
            _draw_entity_polygon(image, draw, polygon, color, label, font=font)
        else:
            _draw_entity_box(image, draw, tuple(ent["bbox"]), color, label, font=font)
    return image


def _legend_line(cmp: PageComparison) -> str:
    return (f"page {cmp.page}: before {len(cmp.before)} / after {len(cmp.after)} entities, "
            f"{cmp.kept} unchanged, {sum(c.kind == 'removed' for c in cmp.changes)} removed, "
            f"{sum(c.kind == 'added' for c in cmp.changes)} added   "
            "[green=confirmed  red=false positive  orange=deferred  blue=unreviewed]")


def _write_side_by_side(cmp: PageComparison, render_before: Path, render_after: Path, out_dir: Path) -> Path:
    with Image.open(render_before) as src:
        left = _draw_entities(src, cmp.before, cmp.before_verdicts)
    with Image.open(render_after) as src:
        right = _draw_entities(src, cmp.after, cmp.after_verdicts)
    gutter, header = 30, 40
    canvas = Image.new("RGB", (left.width + right.width + gutter, max(left.height, right.height) + header), "white")
    canvas.paste(left.convert("RGB"), (0, header))
    canvas.paste(right.convert("RGB"), (left.width + gutter, header))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(24)
    draw.text((10, 8), "BEFORE", fill="black", font=font)
    draw.text((left.width + gutter + 10, 8), "AFTER", fill="black", font=font)
    draw.text((140, 12), _legend_line(cmp), fill="black", font=_load_font(16))
    if canvas.width > SIDE_BY_SIDE_MAX_WIDTH_PX:
        scale = SIDE_BY_SIDE_MAX_WIDTH_PX / canvas.width
        canvas = canvas.resize((SIDE_BY_SIDE_MAX_WIDTH_PX, int(canvas.height * scale)), Image.LANCZOS)
    out = out_dir / f"page_{cmp.page:02d}_side_by_side.png"
    canvas.save(out)
    return out


def _crop(image: Image.Image, bbox: tuple[float, float, float, float]) -> Image.Image:
    x0, y0, x1, y1 = bbox
    box = (max(0, int(x0 - CROP_PAD_PX)), max(0, int(y0 - CROP_PAD_PX)),
           min(image.width, int(x1 + CROP_PAD_PX)), min(image.height, int(y1 + CROP_PAD_PX)))
    crop = image.crop(box)
    scale = CROP_ROW_HEIGHT_PX / max(1, crop.height)
    w = min(CROP_MAX_WIDTH_PX, max(1, int(crop.width * scale)))
    return crop.resize((w, CROP_ROW_HEIGHT_PX), Image.LANCZOS)


def _write_changes_strip(cmp: PageComparison, render_before: Path, render_after: Path, out_dir: Path) -> Path:
    """One row per change: caption | before crop | after crop, both crops of
    the same page region so the eye compares like with like."""
    with Image.open(render_before) as src:
        left_full = _draw_entities(src, cmp.before, cmp.before_verdicts).convert("RGB")
    with Image.open(render_after) as src:
        right_full = _draw_entities(src, cmp.after, cmp.after_verdicts).convert("RGB")

    caption_w, gutter, row_gap = 300, 20, 12
    rows = []
    for change in cmp.changes:
        bbox = tuple(change.entity["bbox"])
        rows.append((change, _crop(left_full, bbox), _crop(right_full, bbox)))
    width = caption_w + 2 * CROP_MAX_WIDTH_PX + 2 * gutter
    height = 40 + len(rows) * (CROP_ROW_HEIGHT_PX + row_gap)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    big, small = _load_font(18), _load_font(14)
    draw.text((10, 10), "CHANGES", fill="black", font=big)
    draw.text((caption_w, 12), "BEFORE", fill="black", font=big)
    draw.text((caption_w + CROP_MAX_WIDTH_PX + gutter, 12), "AFTER", fill="black", font=big)
    y = 40
    for change, before_crop, after_crop in rows:
        ent = change.entity
        color = VERDICT_COLORS[change.verdict][:3]
        cx = (ent["bbox"][0] + ent["bbox"][2]) / 2
        cy = (ent["bbox"][1] + ent["bbox"][3]) / 2
        lines = [f"{change.kind.upper()}  {short_id(ent['entity_id'])}",
                 f"{ent['entity_type']}  conf {ent.get('confidence', 0):.2f}",
                 f"verdict: {change.verdict.replace('_', ' ')}",
                 f"centre ({cx:.0f}, {cy:.0f})"]
        for i, line in enumerate(lines):
            draw.text((10, y + 8 + i * 22), line, fill=color if i == 2 else "black", font=small)
        canvas.paste(before_crop, (caption_w, y))
        canvas.paste(after_crop, (caption_w + CROP_MAX_WIDTH_PX + gutter, y))
        y += CROP_ROW_HEIGHT_PX + row_gap
    out = out_dir / f"page_{cmp.page:02d}_changes.png"
    canvas.save(out)
    return out


# --------------------------------------------------------------------------
# Text summary
# --------------------------------------------------------------------------

def render_summary(slug: str, comparisons: list[PageComparison], out_dir: Path) -> str:
    lines = [f"{slug}: baseline vs latest"]
    for cmp in comparisons:
        lines.append("  " + _legend_line(cmp).split("   [")[0])
        for change in cmp.changes:
            ent = change.entity
            cx = (ent["bbox"][0] + ent["bbox"][2]) / 2
            cy = (ent["bbox"][1] + ent["bbox"][3]) / 2
            arrow = "-" if change.kind == "removed" else "+"
            lines.append(f"    {arrow} {change.kind:<7} {ent['entity_type']:<8} {ent['entity_id']:<12} "
                         f"conf {ent.get('confidence', 0):.2f}  @ ({cx:.0f},{cy:.0f})  [{change.verdict}]")
        for image in cmp.images:
            lines.append(f"    image: {image}")
    if not any(c.changes for c in comparisons):
        lines.append("  no entity added or removed")
    lines.append(f"  output: {out_dir}")
    return "\n".join(lines)
