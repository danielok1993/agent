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

# The element classes a layer name can name. The per-detector keyword lists
# (DOOR_LAYER_KEYWORDS, windows' win_keywords, WALL_LAYER_KEYWORDS) are
# these entries, so a class named here is a class the exclusivity rule
# below knows about. A layer naming MORE THAN ONE class is a grouping layer
# — "RR_New Doors and Windows" says the ink is joinery, never which kind —
# and is conclusive for none of them; the hint fires only when the layer
# names exactly one class. Measured on the corpus (2026-08-26): of the 17
# class-naming layers on the six layered sheets, 16 name exactly one class
# (A325G_INT_DOORS, WINDOWS, RR_Walls, RR_Wall Hatches, Wall Insulation…);
# only s04's "RR_New Doors and Windows" names two, and there the door prior
# fired on 3 window paths.
LAYER_CLASS_KEYWORDS: dict[str, list[str]] = {
    "door": ["door", "a-door"],
    "window": ["window", "wind", "glaz", "glazing"],
    "wall": ["wall", "a-wall", "partition", "struct"],
}


# Layers whose NAME says the ink is annotation, not building: section
# callouts, dimension chains, text. The corpus's only such layers (census
# 2026-08-26, six layered sheets) are "Symbols_Dynamic Callouts" on s04/s08
# — 1,057 paths, 21 stroked lines, among them a page-wide 1.19px section
# callout (the wall pen's width) that paired over a short subspan with a
# parallel wall face and chopped s04's rooms 0000/0001/0003 at y=767.
# Tokens are exact (the same tokenizer as the class hints) and only
# corpus-proven ones veto: "text" is NOT one — s15's "TEXT" layer is
# mis-filed building linework (155 black 1.0px lines, 60 of them >= 100px,
# up to 1,360px) and vetoing it lost 17 of the sheet's 20 rooms and 3
# doors; "symbol" is not one ("Symbols_…" carries the callouts only by
# prefix), nor "section" (a section drawing's walls may live on such a
# layer); "dimension" is kept as the layer-name form of the dimension-chain
# exclusion (no corpus layer carries it, so it is zero-effect today). A
# layer that also names an element class ("Wall Dimensions") is a grouping
# layer and is left alone, mirroring the exclusivity rule of the positive
# hints.
LAYER_ANNOTATION_KEYWORDS: list[str] = ["callout", "dimension"]


def _layer_annotation_veto(layer: str | None) -> bool:
    """True when the layer name marks its ink as annotation (callouts,
    dimensions, text) and names no element class."""
    tokens = _layer_tokens(layer)
    if not tokens or _layer_classes(tokens):
        return False
    return any(kw in tokens for kw in LAYER_ANNOTATION_KEYWORDS)


def _layer_tokens(layer: str | None) -> set[str]:
    if not layer:
        return set()
    tokens = set(_LAYER_TOKEN_RE.split(layer.lower()))
    tokens |= {
        t[:-1] for t in tokens
        if len(t) >= _LAYER_PLURAL_MIN_LEN and t.endswith("s")
    }
    return tokens


def _layer_classes(tokens: set[str]) -> set[str]:
    """The element classes named by a layer's tokens."""
    return {
        cls for cls, kws in LAYER_CLASS_KEYWORDS.items()
        if any(kw in tokens for kw in kws)
    }


def _layer_hint(path: PathPrimitive, keywords: list[str]) -> bool:
    """Return True if any keyword is an exact token in the layer name.

    Token-splits on non-word characters so "a-wind" matches "wind" but
    "window-frame-notes" does not false-match on bare substring "win".
    A layer naming more than one element class (LAYER_CLASS_KEYWORDS) is a
    grouping layer and hints at none of them.
    """
    return _layer_hint_from_layer(path.layer, keywords)


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
    if not tokens or not any(kw in tokens for kw in keywords):
        return False
    return len(_layer_classes(tokens)) <= 1
