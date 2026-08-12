"""The user's per-sheet verdicts, and how they are read.

One file per sheet under tests/ground_truth/. Three verdict lists per page:

  confirmed        — the user has said this detection is correct
  false_positives  — the user has said this detection is wrong
  deferred         — a miss the user reported that we consciously chose not to
                     fix; never speculative, never a run failure

`reviewed: null` is a valid state: the sheet is adopted but unlabeled, so every
detection on it reads as unreviewed and nothing can fail.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRUTH_DIR = REPO_ROOT / "tests" / "ground_truth"

VERDICTS = ("confirmed", "false_positives", "deferred")

# The second axis on a room verdict. `confirmed` vs `false_positives` says
# whether the room is real; `shape` says whether the stored polygon is the
# outline the user actually wants. A "partial" polygon is a baseline to detect
# change against, not an ideal. V1 records this; drift scoring reads it.
SHAPES = ("approved", "partial")


@dataclass
class TruthItem:
    type: str
    bbox: tuple[float, float, float, float]
    tag: str | None = None
    path_indices: list[int] = field(default_factory=list)
    note: str = ""
    polygon: list[list[float]] | None = None
    shape: str | None = None


@dataclass
class PageTruth:
    confirmed: list[TruthItem] = field(default_factory=list)
    false_positives: list[TruthItem] = field(default_factory=list)
    deferred: list[TruthItem] = field(default_factory=list)


@dataclass
class SheetTruth:
    slug: str
    pdf_sha256: str | None = None
    reviewed: str | None = None
    pages: dict[int, PageTruth] = field(default_factory=dict)
    # page number -> [{"bbox": [...], "scale": "1:100"}, ...].
    #
    # Keyed by the region's geometry, not its id: region ids are ordinal and
    # renumber whenever segmentation changes, and a stored scale outranks
    # every detected one, so a mis-attached entry would override a correct
    # reading. Same reason the verdict lists match on bbox rather than on
    # entity id. Carried through load and dump so tools/review.py cannot
    # erase it when it rewrites a sheet's verdicts.
    scales: dict[int, list[dict]] = field(default_factory=dict)

    @property
    def is_labeled(self) -> bool:
        return bool(self.reviewed)

    def page(self, number: int) -> PageTruth:
        return self.pages.get(number, PageTruth())


def truth_path(slug: str) -> Path:
    return TRUTH_DIR / f"{slug}.json"


def _item(raw: dict, slug: str) -> TruthItem:
    bbox = raw.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"{slug}: bbox must be four numbers, got {bbox!r}")
    if not raw.get("type"):
        raise ValueError(f"{slug}: every ground-truth item needs a type")

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

    return TruthItem(
        type=raw["type"],
        bbox=tuple(float(v) for v in bbox),
        tag=raw.get("tag"),
        path_indices=list(raw.get("path_indices", [])),
        note=raw.get("note", ""),
        polygon=polygon,
        shape=shape,
    )


def load_truth(slug: str) -> SheetTruth:
    path = truth_path(slug)
    if not path.exists():
        return SheetTruth(slug=slug)
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages: dict[int, PageTruth] = {}
    for number, lists in (payload.get("pages") or {}).items():
        unknown = set(lists) - set(VERDICTS)
        if unknown:
            raise ValueError(f"{slug} page {number}: unknown verdict list(s) "
                             f"{sorted(unknown)}; expected {list(VERDICTS)}")
        pages[int(number)] = PageTruth(
            **{v: [_item(r, slug) for r in lists.get(v, [])] for v in VERDICTS})
    scales = {
        int(number): [
            {"bbox": [float(v) for v in item["bbox"]],
             "scale": str(item["scale"])}
            for item in entries
            if isinstance(item.get("bbox"), list) and len(item["bbox"]) == 4
            and item.get("scale")
        ]
        for number, entries in (payload.get("scales") or {}).items()
    }
    return SheetTruth(slug=payload.get("sheet", slug),
                      pdf_sha256=payload.get("pdf_sha256"),
                      reviewed=payload.get("reviewed"),
                      pages=pages,
                      scales=scales)


def write_empty_truth(slug: str, sha: str) -> Path:
    """Create the unlabeled ground-truth file for a newly adopted sheet."""
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    path = truth_path(slug)
    path.write_text(json.dumps(
        {"sheet": slug, "pdf_sha256": sha, "reviewed": None, "pages": {}},
        indent=2) + "\n", encoding="utf-8")
    return path


def _inline_number_array(values, inline: dict[str, str]) -> str:
    """Stash a flat number array as a one-line literal; return its token.

    json.dumps per element rather than a blanket float() cast: `bbox` is
    already floats (load_truth coerces it) and `path_indices` is ints, and
    coercing those to 1.0, 2.0 would rewrite files that use them.
    """
    token = f"@@INLINE{len(inline)}@@"
    inline[token] = "[" + ", ".join(json.dumps(v) for v in values) + "]"
    return token


def _inline_point_array(points, inline: dict[str, str]) -> str:
    """Stash a polygon as a one-line literal; return its token.

    A polygon on one line means a shape change shows up as ONE changed line
    in review, rather than a diff hunk spanning the whole outline.
    """
    token = f"@@INLINE{len(inline)}@@"
    inline[token] = "[" + ", ".join(
        f"[{json.dumps(float(x))}, {json.dumps(float(y))}]" for x, y in points) + "]"
    return token


def _item_payload(item: TruthItem, inline: dict[str, str]) -> dict:
    """Serialize one verdict, omitting everything left at its default.

    Ground truth is read by humans in diffs, so an item carries only the
    fields that were actually set rather than a wall of nulls.
    """
    payload: dict = {"type": item.type,
                     "bbox": _inline_number_array(item.bbox, inline)}
    if item.tag:
        payload["tag"] = item.tag
    if item.path_indices:
        payload["path_indices"] = _inline_number_array(item.path_indices, inline)
    if item.polygon:
        payload["polygon"] = _inline_point_array(item.polygon, inline)
    if item.shape:
        payload["shape"] = item.shape
    if item.note:
        payload["note"] = item.note
    return payload


def dumps_truth(truth: SheetTruth) -> str:
    """Serialize a sheet's verdicts exactly as they are stored on disk.

    Split out from dump_truth so the formatting is testable without touching
    the filesystem.
    """
    inline: dict[str, str] = {}
    pages: dict[str, dict] = {}
    for number in sorted(truth.pages):
        page = truth.pages[number]
        lists = {v: [_item_payload(i, inline) for i in getattr(page, v)]
                 for v in VERDICTS}
        lists = {name: items for name, items in lists.items() if items}
        if lists:
            pages[str(number)] = lists
    payload: dict = {"sheet": truth.slug,
                     "pdf_sha256": truth.pdf_sha256,
                     "reviewed": truth.reviewed}
    # Omitted when empty so every existing ground-truth file re-serializes
    # byte-identically -- the round-trip guarantee dump_truth documents.
    if truth.scales:
        payload["scales"] = {
            str(number): [
                # Same one-line bbox treatment verdict items get, so a
                # re-segmentation shows as one changed line, not four.
                {"bbox": _inline_number_array(item["bbox"], inline),
                 "scale": item["scale"]}
                for item in truth.scales[number]
            ]
            for number in sorted(truth.scales)
        }
    payload["pages"] = pages
    text = json.dumps(payload, indent=2)
    for token, literal in inline.items():
        # json.dumps(token) is the token WITH its quotes, so the replacement
        # swaps the whole JSON string for a bare array literal.
        text = text.replace(json.dumps(token), literal)
    return text + "\n"


def dump_truth(truth: SheetTruth) -> Path:
    """Write a sheet's verdicts back to tests/ground_truth/<slug>.json.

    Round-trips load_truth: an unmodified file re-serializes byte-identically,
    so a review session's diff shows only the verdicts it actually added.
    """
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    path = truth_path(truth.slug)
    path.write_text(dumps_truth(truth), encoding="utf-8")
    return path
