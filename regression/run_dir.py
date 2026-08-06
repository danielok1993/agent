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
