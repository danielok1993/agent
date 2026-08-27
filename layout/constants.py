"""Tunable constants for page segmentation.

Values are measured, not guessed — see
docs/superpowers/specs/2026-07-28-floor-plan-region-filtering-design.md.
All lengths are 150-DPI pixels.
"""
from __future__ import annotations

# Occupancy resolution. Fine enough to resolve a SEGMENT_MIN_GUTTER_PX gap.
SEGMENT_BIN_PX = 4

# A fully-empty band must be at least this wide to be cut at. Measured
# insensitive: 12px, 20px and 28px give byte-identical splits on every
# reference sheet.
SEGMENT_MIN_GUTTER_PX = 20

# A primitive spanning this fraction of the page in either axis is sheet
# furniture (border rule, column divider), never drawing content. Load-bearing:
# without it a single border line makes every gutter impossible.
SEGMENT_SPAN_FRAC = 0.90

# Backstop against pathological recursion.
SEGMENT_MAX_DEPTH = 6

# Below this on either side a region cannot be a drawing.
SEGMENT_MIN_REGION_SIDE_PX = 60

# A caption is a zero-path strip no taller than this. Measured: real captions
# are 28px; the notes paragraph on s03 is 284px and must NOT merge.
CAPTION_MAX_H_PX = 64

# Vertical gap between a caption and its drawing. Measured 44-48px.
CAPTION_MAX_GAP_PX = 64

# A caption must overlap its drawing by this fraction of the caption's width.
CAPTION_MIN_OVERLAP_FRAC = 0.5

# A clip rect is a real drawing boundary only if it holds this share of the
# page's paths. Measured: text/annotation clips 0.0-1.3%, drawing clips
# 5.7-62.4% — no overlap between the bands.
CLIP_MIN_INK_FRAC = 0.05

# A clip covering this much of the page is the whole-sheet clip, not a drawing.
# Measured whole-sheet clips at 88-97%.
CLIP_MAX_PAGE_FRAC = 0.80

# Nested sheet furniture: an unfilled rectangle with at least this many of
# its corners lying within FRAME_CORNER_TOL_PX of the page frame's boundary
# (a page-spanning rect's edges, or a page-spanning rule) is a drawing frame
# or title-block partition, never drawing content, and must not block a
# gutter. Measured on s06: the inner frame [63.6,106.5]-[2132.1,1395.0] has
# three corners 0.00px off the outer frame and is 0.86 of the page wide —
# under SEGMENT_SPAN_FRAC — and it glued the elevations to the plans below
# them. Three corners, not two: a drawing box hugging one border shares two.
FRAME_NESTED_MIN_CORNERS = 3
FRAME_CORNER_TOL_PX = 2.0

# Tier-3 gutters: a primitive whose total drawn length is at most this is
# annotation ink — a leader arrowhead (1-3px pieces), a dimension tick, a
# dash of a dimension line drawn as pieces, a vector-text glyph stroke — and
# a band that only such ink crosses is still a gutter, unless the pieces
# chain across it (see segmenter._short_ink_gutter). Measured on s12: an
# arrowhead's 7 pieces at x 2112-2136 and 6px dashes at x=624 were the only
# ink in its gutters; on s17 59-181 arrowhead/glyph pieces per gutter, all
# 1-15px, while its 'to be removed' ticks measure 19px and stay blockers.
SEGMENT_SHORT_INK_PX = 16.0
