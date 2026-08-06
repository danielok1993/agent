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


@dataclass
class TruthItem:
    type: str
    bbox: tuple[float, float, float, float]
    tag: str | None = None
    path_indices: list[int] = field(default_factory=list)
    note: str = ""


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
    return TruthItem(
        type=raw["type"],
        bbox=tuple(float(v) for v in bbox),
        tag=raw.get("tag"),
        path_indices=list(raw.get("path_indices", [])),
        note=raw.get("note", ""),
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
    return SheetTruth(slug=payload.get("sheet", slug),
                      pdf_sha256=payload.get("pdf_sha256"),
                      reviewed=payload.get("reviewed"),
                      pages=pages)


def write_empty_truth(slug: str, sha: str) -> Path:
    """Create the unlabeled ground-truth file for a newly adopted sheet."""
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    path = truth_path(slug)
    path.write_text(json.dumps(
        {"sheet": slug, "pdf_sha256": sha, "reviewed": None, "pages": {}},
        indent=2) + "\n", encoding="utf-8")
    return path
