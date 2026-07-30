"""Page segmentation: split a sheet into its constituent drawings."""
from layout.clips import clip_cut_positions, qualifying_clip_rects
from layout.filter import filter_page_data, region_text_spans
from layout.segmenter import count_paths_in, page_fallback_region, segment_page

__all__ = [
    "clip_cut_positions",
    "count_paths_in",
    "filter_page_data",
    "page_fallback_region",
    "qualifying_clip_rects",
    "region_text_spans",
    "segment_page",
]
