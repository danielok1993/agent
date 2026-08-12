"""Tier 4 input — ask the user, but only when someone is there to answer.

batch_extract.py runs five sheets in parallel through a ProcessPoolExecutor
with no tty, and tools/regress.py sweeps twenty sheets unattended. A blocking
prompt would hang both, so every path here is gated on a real terminal and
every failure mode (EOF, interrupt, nonsense) is a skip rather than a retry.
"""
from __future__ import annotations

import re
import sys
from typing import Optional

from scale.units import PAPER_SPACE_MAX_DENOMINATOR, format_scale

_ANSWER_RE = re.compile(r"^\s*(?:1\s*:\s*)?(\d{1,4}(?:\.\d+)?)\s*$")


def can_prompt(stream=None) -> bool:
    """True only when stdin is a real terminal."""
    stream = sys.stdin if stream is None else stream
    isatty = getattr(stream, "isatty", None)
    if isatty is None:
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


def parse_answer(answer: str) -> Optional[float]:
    """The denominator in an answer, accepting "1:100" or "100". None to skip."""
    match = _ANSWER_RE.match(answer or "")
    if not match:
        return None
    denominator = float(match.group(1))
    if denominator < PAPER_SPACE_MAX_DENOMINATOR:
        return None
    return denominator


def prompt_for_scale(
    region_id: str,
    crop_hint: str,
    input_fn=input,
    output_fn=print,
) -> Optional[str]:
    """Ask once for one region's scale. Returns "1:100", or None if skipped.

    Asked once, not until valid: a user who does not know the scale must be
    able to move on, and the region simply stays unresolved.
    """
    output_fn(f"No scale found for {region_id}.")
    output_fn(f"  Look at: {crop_hint}")
    try:
        answer = input_fn("  Scale (e.g. 1:100, blank to skip): ")
    except (EOFError, KeyboardInterrupt):
        return None
    denominator = parse_answer(answer)
    if denominator is None:
        return None
    return format_scale(denominator)
