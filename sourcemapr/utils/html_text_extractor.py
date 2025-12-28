"""
Position-tracking HTML text extractor for SourcemapR.

Extracts text from HTML while building a character-by-character mapping
from extracted text positions to raw HTML positions.

This enables accurate highlighting in the Original HTML view.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TextSegment:
    """A segment of extracted text with its HTML position."""
    text: str
    html_start: int
    html_end: int
    extracted_start: int
    extracted_end: int


class PositionTrackingExtractor:
    """
    Extracts text from HTML while tracking exact character positions.

    Unlike BeautifulSoup's get_text(), this preserves the mapping from
    each character in the extracted text back to its position in the raw HTML.
    """

    def __init__(self, html_content: str):
        self.html_content = html_content
        self._extracted_text: str = ""
        self._segments: List[TextSegment] = []
        self._char_map: Dict[int, int] = {}  # extracted_pos -> html_pos
        self._extract()

    @property
    def extracted_text(self) -> str:
        return self._extracted_text

    @property
    def char_map(self) -> Dict[int, int]:
        return self._char_map

    def _extract(self):
        """Extract text while tracking positions."""
        html = self.html_content
        segments: List[TextSegment] = []

        # Tags to skip entirely (including content)
        skip_tags = {'script', 'style', 'head', 'meta', 'link', 'noscript'}

        # State tracking
        pos = 0
        extracted_pos = 0
        in_skip_tag = None
        skip_depth = 0

        # Regex patterns
        tag_pattern = re.compile(r'<(/?)(\w+)([^>]*)>', re.IGNORECASE)
        entity_pattern = re.compile(r'&(\w+|#\d+|#x[0-9a-fA-F]+);')

        text_parts = []
        current_text_start = None
        current_html_start = None

        while pos < len(html):
            # Check for tag
            if html[pos] == '<':
                # Save any accumulated text
                if current_text_start is not None and text_parts:
                    text = ''.join(text_parts)
                    if text.strip():  # Only save non-empty segments
                        seg = TextSegment(
                            text=text,
                            html_start=current_html_start,
                            html_end=pos,
                            extracted_start=extracted_pos,
                            extracted_end=extracted_pos + len(text)
                        )
                        segments.append(seg)

                        # Build char map for this segment
                        for i, char in enumerate(text):
                            self._char_map[extracted_pos + i] = current_html_start + i

                        extracted_pos += len(text)
                    text_parts = []
                    current_text_start = None

                # Find end of tag
                tag_match = tag_pattern.match(html, pos)
                if tag_match:
                    is_closing = tag_match.group(1) == '/'
                    tag_name = tag_match.group(2).lower()
                    tag_end = tag_match.end()

                    # Handle skip tags
                    if tag_name in skip_tags:
                        if is_closing:
                            if in_skip_tag == tag_name:
                                skip_depth -= 1
                                if skip_depth == 0:
                                    in_skip_tag = None
                        else:
                            if in_skip_tag is None:
                                in_skip_tag = tag_name
                                skip_depth = 1
                            elif in_skip_tag == tag_name:
                                skip_depth += 1

                    # Add space after block-level tags for readability
                    if not in_skip_tag and tag_name in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'td', 'th'):
                        if text_parts and text_parts[-1] != ' ':
                            text_parts.append(' ')

                    pos = tag_end
                    continue
                else:
                    # Not a valid tag, treat < as text
                    pos += 1
                    continue

            # Skip content inside skip tags
            if in_skip_tag:
                pos += 1
                continue

            # Handle text content
            char = html[pos]

            # Start new text segment if needed
            if current_text_start is None:
                current_text_start = extracted_pos
                current_html_start = pos

            # Handle HTML entities
            if char == '&':
                entity_match = entity_pattern.match(html, pos)
                if entity_match:
                    entity = entity_match.group(0)
                    decoded = self._decode_entity(entity)
                    text_parts.append(decoded)
                    pos = entity_match.end()
                    continue

            # Regular character
            # Normalize whitespace
            if char in ' \t\n\r':
                if not text_parts or text_parts[-1] != ' ':
                    text_parts.append(' ')
            else:
                text_parts.append(char)

            pos += 1

        # Save final text segment
        if current_text_start is not None and text_parts:
            text = ''.join(text_parts)
            if text.strip():
                seg = TextSegment(
                    text=text,
                    html_start=current_html_start,
                    html_end=pos,
                    extracted_start=extracted_pos,
                    extracted_end=extracted_pos + len(text)
                )
                segments.append(seg)

                for i, char in enumerate(text):
                    self._char_map[extracted_pos + i] = current_html_start + i

                extracted_pos += len(text)

        self._segments = segments
        self._extracted_text = ''.join(seg.text for seg in segments)

    def _decode_entity(self, entity: str) -> str:
        """Decode HTML entity to character."""
        entity_map = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&#39;': "'",
            '&ndash;': '–',
            '&mdash;': '—',
            '&copy;': '©',
            '&reg;': '®',
            '&trade;': '™',
        }
        if entity in entity_map:
            return entity_map[entity]

        # Numeric entities
        if entity.startswith('&#x'):
            try:
                return chr(int(entity[3:-1], 16))
            except:
                return entity
        elif entity.startswith('&#'):
            try:
                return chr(int(entity[2:-1]))
            except:
                return entity

        return entity

    def get_html_position(self, extracted_start: int, extracted_end: int) -> Tuple[int, int]:
        """
        Map extracted text positions to HTML positions.

        Args:
            extracted_start: Start position in extracted text
            extracted_end: End position in extracted text

        Returns:
            Tuple of (html_start, html_end)
        """
        # Find segments that contain our range
        html_start = None
        html_end = None

        for seg in self._segments:
            # Check if segment overlaps with our range
            if seg.extracted_end > extracted_start and seg.extracted_start < extracted_end:
                # Calculate HTML positions within this segment
                if html_start is None:
                    # Start position
                    offset_in_seg = max(0, extracted_start - seg.extracted_start)
                    html_start = seg.html_start + offset_in_seg

                # End position (keep updating until we find the last overlapping segment)
                offset_in_seg = min(len(seg.text), extracted_end - seg.extracted_start)
                html_end = seg.html_start + offset_in_seg

        # Fallback if no segments found
        if html_start is None:
            html_start = extracted_start
        if html_end is None:
            html_end = extracted_end

        return html_start, html_end


def extract_with_positions(html_content: str) -> PositionTrackingExtractor:
    """
    Extract text from HTML with position tracking.

    Convenience function.
    """
    return PositionTrackingExtractor(html_content)


def find_text_in_html(html_content: str, search_text: str, start_from: int = 0) -> Optional[int]:
    """
    Find text in HTML using fuzzy word matching.
    Only matches visible text (outside of tags).
    Returns the HTML position where the best match starts, or None if not found.
    """
    if not search_text or len(search_text) < 20:
        return None

    import re

    # Extract distinctive words from search text (4+ chars for distinctiveness)
    search_words = [w.lower() for w in re.findall(r'[a-zA-Z]{4,}', search_text)]
    if len(search_words) < 2:
        return None

    # Use first 8 distinctive words
    search_words = search_words[:8]

    # Find word positions in visible text only (skip tag contents)
    html_lower = html_content.lower()

    def find_word_outside_tags(word, start):
        """Find word position only in visible text, not inside < >"""
        pos = start
        while True:
            idx = html_lower.find(word, pos)
            if idx == -1:
                return -1

            # Check if inside a tag by looking for < before and > after
            # Find the nearest < before this position
            last_open = html_lower.rfind('<', 0, idx)
            last_close = html_lower.rfind('>', 0, idx)

            # If last < is after last >, we're inside a tag
            if last_open > last_close:
                pos = idx + 1  # Skip and keep searching
                continue

            return idx

    word_positions = {}
    for word in search_words:
        pos = find_word_outside_tags(word, start_from)
        if pos != -1:
            word_positions[word] = pos

    if len(word_positions) < len(search_words) * 0.3:
        return None  # Too few words found

    # Find the cluster where most words appear close together
    if word_positions:
        positions = sorted(word_positions.values())

        # Find best cluster - look for where words are densest
        best_start = None
        best_count = 0
        window = len(search_text) * 2  # Tighter window

        for pos in positions:
            # Count words within window CENTERED on this position
            count = sum(1 for p in positions if abs(p - pos) <= window)
            if count > best_count:
                best_count = count
                best_start = pos

        # Return the earliest position in the best cluster
        if best_start is not None:
            cluster_positions = [p for p in positions if abs(p - best_start) <= window]
            return min(cluster_positions)

    return None


def get_html_positions_for_chunk(
    html_content: str,
    loader_text: str,
    chunk_start: int,
    chunk_end: int,
    chunk_text: str = None,
    prev_chunk_text: str = None,
    next_chunk_text: str = None
) -> Tuple[int, int]:
    """
    Get HTML positions for a chunk using text-based search with surrounding chunk context.

    Strategy:
    1. Try to find the chunk text directly in HTML
    2. If not found, find surrounding chunks and interpolate position
    3. Fall back to approximate position based on document structure

    Args:
        html_content: Raw HTML content
        loader_text: Text as extracted by loader
        chunk_start: Chunk start position in loader_text
        chunk_end: Chunk end position in loader_text
        chunk_text: The actual chunk text (optional, extracted from loader_text if not provided)
        prev_chunk_text: Text of previous chunk (for context)
        next_chunk_text: Text of next chunk (for context)

    Returns:
        Tuple of (html_start, html_end)
    """
    # Get chunk text if not provided
    if chunk_text is None:
        chunk_text = loader_text[chunk_start:chunk_end]

    chunk_len = len(chunk_text)

    # Strategy 1: Direct text search
    html_start = find_text_in_html(html_content, chunk_text)
    if html_start is not None:
        # Estimate end position (may span more HTML due to tags)
        html_end = html_start + chunk_len * 2  # Rough estimate
        return html_start, min(html_end, len(html_content))

    # Strategy 2: Find surrounding chunks and interpolate
    prev_pos = None
    next_pos = None

    if prev_chunk_text:
        prev_pos = find_text_in_html(html_content, prev_chunk_text)

    if next_chunk_text:
        # Search after prev_pos if we found it
        search_from = prev_pos + len(prev_chunk_text) if prev_pos else 0
        next_pos = find_text_in_html(html_content, next_chunk_text, search_from)

    if prev_pos is not None and next_pos is not None:
        # Chunk is between prev and next
        html_start = prev_pos + len(prev_chunk_text)
        html_end = next_pos
        return html_start, html_end

    if prev_pos is not None:
        # Chunk starts after prev
        html_start = prev_pos + len(prev_chunk_text)
        html_end = html_start + chunk_len * 2
        return html_start, min(html_end, len(html_content))

    if next_pos is not None:
        # Chunk ends before next
        html_end = next_pos
        html_start = max(0, html_end - chunk_len * 2)
        return html_start, html_end

    # Strategy 3: Ratio-based fallback (last resort)
    # Estimate based on position in loader text
    if len(loader_text) > 0:
        ratio = chunk_start / len(loader_text)
        html_start = int(ratio * len(html_content))
        html_end = html_start + chunk_len * 2
        return html_start, min(html_end, len(html_content))

    # Ultimate fallback
    return chunk_start, chunk_end
