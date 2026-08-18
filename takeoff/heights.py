"""Wall / opening heights — the one input the plan cannot supply.

0/20 corpus sheets carry a numeric ceiling height (measured 2026-08-18), so
heights come from the user: flag → tty prompt → default. The prompt is asked
once per run for the ceiling only, and shares the scale prompt's tty gate so
batch_extract and regress.py never block. `"drawing"` is a reserved source
value for a future text/section reader; nothing here emits it.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Callable, Optional

from scale.prompt import can_prompt

DEFAULT_CEILING_M = 2.4
DEFAULT_DOOR_M = 2.1
DEFAULT_WINDOW_M = 1.2

_HEIGHT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(m|mm)?\s*$", re.I)


@dataclass(frozen=True)
class Heights:
    ceiling_m: float
    door_m: float
    window_m: float
    sources: dict   # {"ceiling": "flag"|"prompt"|"default", "door": ..., "window": ...}

    def to_dict(self) -> dict:
        return {"ceiling_m": self.ceiling_m, "door_m": self.door_m,
                "window_m": self.window_m, "source": dict(self.sources)}


def parse_height(answer: Optional[str]) -> Optional[float]:
    """Metres from "2.4", "2.4m", "2400", "2400mm". None to skip."""
    m = _HEIGHT_RE.match(answer or "")
    if not m:
        return None
    value = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit == "mm" or (unit == "" and value >= 100):
        value = value / 1000.0
    return value if value > 0 else None


def valid_height_m(value, name: str) -> float:
    """A positive, finite number of metres — or ValueError naming the offender."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = float("nan")
    if not math.isfinite(v) or v <= 0:
        raise ValueError(f"{name} height must be a positive finite number of metres, got {value!r}")
    return v


def _prompt_ceiling(input_fn, output_fn) -> Optional[float]:
    output_fn("No ceiling height on the drawing.")
    try:
        answer = input_fn(f"  Ceiling height in m (blank for {DEFAULT_CEILING_M}): ")
    except (EOFError, KeyboardInterrupt):
        return None
    return parse_height(answer)


def resolve_heights(
    ceiling: Optional[float],
    door: Optional[float],
    window: Optional[float],
    allow_prompt: bool = True,
    can_prompt_fn: Callable[[], bool] = can_prompt,
    input_fn=input,
    output_fn=print,
) -> Heights:
    sources = {}
    if ceiling is not None:
        ceiling, sources["ceiling"] = valid_height_m(ceiling, "ceiling"), "flag"
    else:
        answered = None
        if allow_prompt and can_prompt_fn():
            answered = _prompt_ceiling(input_fn, output_fn)
        if answered is not None:
            ceiling, sources["ceiling"] = answered, "prompt"
        else:
            ceiling, sources["ceiling"] = DEFAULT_CEILING_M, "default"

    if door is not None:
        door, sources["door"] = valid_height_m(door, "door"), "flag"
    else:
        door, sources["door"] = DEFAULT_DOOR_M, "default"

    if window is not None:
        window, sources["window"] = valid_height_m(window, "window"), "flag"
    else:
        window, sources["window"] = DEFAULT_WINDOW_M, "default"

    return Heights(float(ceiling), float(door), float(window), sources)
