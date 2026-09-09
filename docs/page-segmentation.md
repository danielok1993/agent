# Page segmentation — ink map, frames and gutter tiers

Extracted verbatim from CLAUDE.md's pipeline stage 3. Covers `layout/` — how a
sheet is split into its drawings before detection runs. See `CLAUDE.md`
§Pipeline architecture for where this sits in the run.

## Ink map, nested frames and the four gutter tiers

The ink map joins a `qu` item's points in perimeter order `[0, 1, 3, 2]`
(PyMuPDF Quad order is ul, ur, ll, lr — joined sequentially, every quad inked
two diagonals across its interior instead of its top and bottom edges; measured
on s06 the 2344×1544px drawing frame drew two page-wide diagonals through every
drawing, gluing the elevations to the plans — fixed 2026-08-27, only s06's
leaves changed on the corpus), and skips NESTED SHEET FURNITURE
(`nested_frame_indices`): an unfilled rectangle with ≥
`FRAME_NESTED_MIN_CORNERS` (3) corners within `FRAME_CORNER_TOL_PX` (2px) of
the page frame's boundary — the edges of a page-spanning unfilled rect or a
page-spanning rule — is a drawing frame or title-block partition (measured on
s06: the inner frame [63.6,106.5]–[2132.1,1395.0] has three corners 0.00px off
the outer frame and is 0.86 of the page wide, under `SEGMENT_SPAN_FRAC`; it
stacked each elevation on the plan below it in one leaf, which the classifier
called `elevation`, skipping the page). A box hugging one border shares two
corners and stays ink; one level only — nested furniture never seeds further
rectangles or free lines, and there is no "encloses most of the ink" seed (an
unfilled drawing enclosure would match it). A cell that neither a fully-empty
gutter nor a clip edge can split gets a TIER-3 search (`_short_ink_gutter`):
the widest band that is empty on a LONG-ink map (primitives with total drawn
length > `SEGMENT_SHORT_INK_PX` 16px only — leader arrowheads, dimension ticks,
the 6px dashes of a pieced dimension line and vector-text glyph strokes are
annotation, never a drawing's edge) is a gutter unless the short ink inside it
forms an 8-connected chain touching both of the band's edges (`_chains_across`
— a dashed wall drawn as touching pieces is still a wall). The full map is
untouched, so trimming, tier-1 gutters, clip cuts and leaf boxes on every sheet
a real gutter splits are byte-identical; measured, only s12 (1 → 12 leaves,
each drawing its own), s05 (the title block splits) and s20 (a vector-text
notes column separates from the plan it hugs) change; s17's plan+elevation leaf
stays because its crossers are 19px 'to be removed' ticks and 30px dimension
chains. A cell tier 3 cannot split gets a TIER-4 search (`_overhang_gutter`):
the widest band sparse on a PATHS-ONLY long map (≤ `SEGMENT_OVERHANG_MAX_BINS`
6 inked bins per profile line — candidate pruning; text is never a drawing's
edge, and the caption between an elevation and the plan below it otherwise
disqualifies the band) that nothing chains across on the full map (a through
line, short pieces forming one, overhangs from both sides that meet) and that
keeps a sub-run of `SEGMENT_OVERHANG_MIN_GAP_PX` (12px, 3 bins) empty on the
text+long map — short annotation pieces don't count, exactly as in tier 3, but
a caption or a long line does, so neither is sliced; the cut goes through that
sub-run's middle. A drawing's extent and ground lines routinely hang past its
body into the gap beside the next drawing (measured: s13's three elevations end
verticals 15–92px into the 112px band above its plans, 20px clear below the
deepest; s17's front-elevation ground line, drawn 4×, starts 18px into the 64px
band its plan's lines end 3px into), while a plan interior never qualifies —
its exterior walls run through any band across it (s01: two through lines in
the only candidate band; s02: no candidate band at all). Measured on the
corpus: s13 3 → 6 leaves (elevation row, each plan, the right-side elevation)
and s14 4 → 7 (three vector-text notes columns peel off the plan's left edge);
16 sheets byte-identical. The recursion backstop `SEGMENT_MAX_DEPTH` is the
minimum MEASURED budget (7), not proof that the cap exceeds every sheet: a leaf
emitted at the backstop is whatever was left when the recursion stopped, mixed
by construction on a busy sheet — at 6, s17's first-floor plan and front
elevation came out as one leaf although the elevation's own clip edge and the
tier-4 gutter both split that cell when reached, and 142 corpus leaves were
backstop-emitted; at 7 s17 splits exactly and nine sheets change (title-block,
notes and legend subdivisions plus s13's elevation row; every plan's confirmed
entities stay in one leaf), while 8 adds only churn.
