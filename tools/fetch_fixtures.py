"""Verify the downloaded corpus against the committed manifest.

Download is manual: the sheets are NDA-covered and live in shared storage.
This tool tells you what is missing, what has the wrong bytes, and what is
sitting in fixtures/sheets/ without being part of the corpus.

Usage:  python tools/fetch_fixtures.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import regression.corpus as corpus_module  # noqa: E402
from regression.corpus import (  # noqa: E402
    load_manifest, manifest_sheets, sha256_of,
)


@dataclass
class CorpusStatus:
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.mismatched or self.untracked)


def check_corpus() -> CorpusStatus:
    status = CorpusStatus()
    known_files = set()
    for entry in manifest_sheets():
        if entry.get("tier") == "retired":
            known_files.add(entry["file"])
            continue
        path = corpus_module.SHEETS_DIR / entry["file"]
        known_files.add(entry["file"])
        if not path.exists():
            status.missing.append(entry["slug"])
        elif sha256_of(path) != entry["sha256"]:
            status.mismatched.append(entry["slug"])
        else:
            status.present.append(entry["slug"])
    if corpus_module.SHEETS_DIR.is_dir():
        for pdf in sorted(corpus_module.SHEETS_DIR.glob("*.pdf")):
            if pdf.name not in known_files:
                status.untracked.append(pdf.name)
    return status


def main() -> int:
    status = check_corpus()
    storage = load_manifest().get("storage") or "ask the maintainer for the bundle"
    print(f"corpus: {len(status.present)} present, {len(status.missing)} missing, "
          f"{len(status.mismatched)} mismatched, {len(status.untracked)} untracked")
    if status.missing:
        print(f"\n{len(status.missing)} sheet(s) missing — the sweep is incomplete "
              f"until every sheet is downloaded. {storage}")
    for slug in status.missing:
        print(f"  MISSING     {slug}")
    for slug in status.mismatched:
        print(f"  MISMATCH    {slug} — bytes differ from the manifest; "
              f"a revised drawing must be adopted as a NEW slug "
              f"(python tools/add_sheet.py <file>), never dropped over an existing one")
    for name in status.untracked:
        print(f"  UNTRACKED   {name} — adopt it with: python tools/add_sheet.py "
              f"fixtures/sheets/{name} --desc <drawing-type>")
    return 0 if status.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
