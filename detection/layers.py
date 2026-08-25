from __future__ import annotations
import re
from models import PathPrimitive


_LAYER_TOKEN_RE = re.compile(r"[\W_]+")

# A token this long or longer that ends in "s" also contributes its singular
# stem. CAD layer conventions pluralise the class name — NBS/Uniclass
# "A325G_INT_DOORS", "RR_Walls", "RR_New Doors and Windows", freehand
# "WINDOWS"/"Windows"/"EXISTING_WINDOWS" — while the keyword lists are
# singular, and an exact-token match never fired on any of them (measured
# 2026-08-25: s03/s17 doors + windows, s06/s13 windows, s04/s08 walls —
# every door/window/wall layer on the six layered corpus sheets is plural;
# the only singular hits are "RR_Wall Hatches" and "Wall Insulation", which
# are NOT wall faces). Stemming keeps exact-token matching (no substring
# match, "doorstops" still misses), and the length floor keeps "as"/"is"
# style tokens from contributing a one-letter stem.
_LAYER_PLURAL_MIN_LEN = 4


def _layer_tokens(layer: str | None) -> set[str]:
    if not layer:
        return set()
    tokens = set(_LAYER_TOKEN_RE.split(layer.lower()))
    tokens |= {
        t[:-1] for t in tokens
        if len(t) >= _LAYER_PLURAL_MIN_LEN and t.endswith("s")
    }
    return tokens


def _layer_hint(path: PathPrimitive, keywords: list[str]) -> bool:
    """Return True if any keyword is an exact token in the layer name.

    Token-splits on non-word characters so "a-wind" matches "wind" but
    "window-frame-notes" does not false-match on bare substring "win".
    """
    tokens = _layer_tokens(path.layer)
    return bool(tokens and any(kw in tokens for kw in keywords))


def _layer_strong_prior(path: PathPrimitive, keywords: list[str]) -> float:
    """Return a high confidence boost when a layer name conclusively names the type.

    Only applied when the layer is non-empty and contains a matching token.
    Returns 0.0 when no layer data is available so it is a no-op on documents
    without OCG layers.
    """
    if not path.layer:
        return 0.0
    return 0.40 if _layer_hint(path, keywords) else 0.0


def _layer_hint_from_layer(layer: str | None, keywords: list[str]) -> bool:
    tokens = _layer_tokens(layer)
    return bool(tokens and any(kw in tokens for kw in keywords))
