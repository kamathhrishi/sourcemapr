"""SourcemapR utilities."""

from sourcemapr.utils.html_parser import (
    HTMLParser,
    extract_text_with_pages,
    get_page_for_position,
)
from sourcemapr.utils.html_text_extractor import (
    PositionTrackingExtractor,
    extract_with_positions,
    get_html_positions_for_chunk,
)
from sourcemapr.utils.html_position_mapper import (
    HTMLPositionMapper,
    create_position_mapper,
    map_chunk_positions,
)

__all__ = [
    "HTMLParser",
    "extract_text_with_pages",
    "get_page_for_position",
    "PositionTrackingExtractor",
    "extract_with_positions",
    "get_html_positions_for_chunk",
    "HTMLPositionMapper",
    "create_position_mapper",
    "map_chunk_positions",
]
