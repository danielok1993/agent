from __future__ import annotations
import re
from models import PathPrimitive


_LAYER_TOKEN_RE = re.compile(r"[\W_]+")


def _layer_tokens(layer: str | None) -> set[str]:
    if not layer:
        return set()
    return set(_LAYER_TOKEN_RE.split(layer.lower()))


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
