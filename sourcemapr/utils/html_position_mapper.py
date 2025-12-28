"""
HTML Position Mapper for SourcemapR.

Tracks the mapping between raw HTML character positions and extracted text positions.
This enables accurate highlighting in both Original (raw HTML) and Parsed (extracted text) views.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionMapping:
    """Maps a range in extracted text to a range in raw HTML."""
    text_start: int
    text_end: int
    html_start: int
    html_end: int


class HTMLPositionMapper:
    """
    Extracts text from HTML while tracking position mappings.

    This allows us to map any position in the extracted text back to
    the corresponding position in the raw HTML.

    Usage:
        mapper = HTMLPositionMapper(html_content)
        text = mapper.extracted_text

        # Map text position to HTML position
        html_start, html_end = mapper.text_to_html(text_start, text_end)
    """

    def __init__(self, html_content: str):
        self.html_content = html_content
        self._extracted_text: Optional[str] = None
        self._mappings: List[PositionMapping] = []
        self._text_to_html_map: Dict[int, int] = {}  # text_pos -> html_pos
        self._process()

    @property
    def extracted_text(self) -> str:
        return self._extracted_text or ""

    def _process(self):
        """Extract text while tracking positions."""
        try:
            from bs4 import BeautifulSoup
            self._extract_with_bs4()
        except ImportError:
            self._extract_simple()

    def _extract_with_bs4(self):
        """Extract text using BeautifulSoup with position tracking."""
        from bs4 import BeautifulSoup, NavigableString

        soup = BeautifulSoup(self.html_content, 'html.parser')

        # Remove non-content tags
        for tag in soup(['script', 'style', 'meta', 'link', 'head']):
            tag.decompose()

        text_parts = []
        text_pos = 0

        # Walk through all text nodes
        for element in soup.descendants:
            if isinstance(element, NavigableString):
                # Skip empty strings and special types
                if element.strip() and element.parent.name not in ['script', 'style', '[document]']:
                    text = str(element)
                    cleaned = self._clean_text_segment(text)

                    if cleaned:
                        # Find this text in the original HTML
                        # We search for the raw text (not cleaned) to get accurate positions
                        html_pos = self._find_text_in_html(text, element)

                        if html_pos is not None:
                            # Map each character
                            for i, char in enumerate(cleaned):
                                self._text_to_html_map[text_pos + i] = html_pos + i

                            self._mappings.append(PositionMapping(
                                text_start=text_pos,
                                text_end=text_pos + len(cleaned),
                                html_start=html_pos,
                                html_end=html_pos + len(text)
                            ))

                        text_parts.append(cleaned)
                        text_pos += len(cleaned)

                        # Add space between text nodes
                        text_parts.append(' ')
                        text_pos += 1

        self._extracted_text = self._clean_final_text(''.join(text_parts))

    def _find_text_in_html(self, text: str, element) -> Optional[int]:
        """Find the position of text in the original HTML."""
        # Try to find the exact text
        text_stripped = text.strip()
        if not text_stripped:
            return None

        # Search for the text in HTML
        idx = self.html_content.find(text_stripped)
        if idx != -1:
            return idx

        # Try with normalized whitespace
        normalized = re.sub(r'\s+', ' ', text_stripped)
        idx = self.html_content.find(normalized)
        if idx != -1:
            return idx

        # Fallback: search for first few words
        words = text_stripped.split()[:3]
        if words:
            search = ' '.join(words)
            idx = self.html_content.find(search)
            if idx != -1:
                return idx

        return None

    def _extract_simple(self):
        """Simple extraction without BeautifulSoup."""
        # Track positions while removing tags
        text_parts = []
        text_pos = 0
        html_pos = 0

        # Simple regex to find text between tags
        pattern = re.compile(r'>([^<]+)<')

        for match in pattern.finditer(self.html_content):
            content = match.group(1)
            cleaned = self._clean_text_segment(content)

            if cleaned.strip():
                html_start = match.start(1)

                # Map positions
                for i in range(len(cleaned)):
                    self._text_to_html_map[text_pos + i] = html_start + i

                self._mappings.append(PositionMapping(
                    text_start=text_pos,
                    text_end=text_pos + len(cleaned),
                    html_start=html_start,
                    html_end=match.end(1)
                ))

                text_parts.append(cleaned)
                text_parts.append(' ')
                text_pos += len(cleaned) + 1

        self._extracted_text = self._clean_final_text(''.join(text_parts))

    def _clean_text_segment(self, text: str) -> str:
        """Clean a text segment while preserving relative positions."""
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&apos;', "'")

        # Normalize whitespace but keep structure
        text = re.sub(r'[ \t]+', ' ', text)
        return text

    def _clean_final_text(self, text: str) -> str:
        """Final cleanup of extracted text."""
        # Normalize multiple spaces/newlines
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

    def text_to_html(self, text_start: int, text_end: int) -> Tuple[Optional[int], Optional[int]]:
        """
        Map text positions to HTML positions.

        Args:
            text_start: Start position in extracted text
            text_end: End position in extracted text

        Returns:
            Tuple of (html_start, html_end) or (None, None) if not found
        """
        html_start = None
        html_end = None

        # Find mapping that contains the start position
        for mapping in self._mappings:
            if mapping.text_start <= text_start < mapping.text_end:
                # Calculate offset within this mapping
                offset = text_start - mapping.text_start
                html_start = mapping.html_start + offset
                break

        # Find mapping that contains the end position
        for mapping in self._mappings:
            if mapping.text_start < text_end <= mapping.text_end:
                offset = text_end - mapping.text_start
                html_end = mapping.html_start + offset
                break

        # If we found start but not end, estimate end
        if html_start is not None and html_end is None:
            html_end = html_start + (text_end - text_start)

        return html_start, html_end

    def get_html_range_for_text(self, text_start: int, text_end: int) -> Tuple[int, int]:
        """
        Get the HTML range that corresponds to a text range.

        This is a more robust version that finds the encompassing HTML range
        even if the text spans multiple mappings.

        Returns:
            Tuple of (html_start, html_end)
        """
        html_start = None
        html_end = None

        for mapping in self._mappings:
            # Check if this mapping overlaps with our text range
            if mapping.text_end > text_start and mapping.text_start < text_end:
                if html_start is None or mapping.html_start < html_start:
                    html_start = mapping.html_start
                if html_end is None or mapping.html_end > html_end:
                    html_end = mapping.html_end

        # Fallback if no mapping found
        if html_start is None:
            html_start = text_start
        if html_end is None:
            html_end = text_end

        return html_start, html_end

    def find_text_in_html_fuzzy(self, search_text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Find text in HTML using fuzzy matching.

        Useful when exact position mapping isn't available.

        Returns:
            Tuple of (html_start, html_end) or (None, None) if not found
        """
        # Normalize the search text
        search_normalized = re.sub(r'\s+', ' ', search_text.strip())

        # Try exact match first
        idx = self.html_content.find(search_normalized)
        if idx != -1:
            return idx, idx + len(search_normalized)

        # Try with flexible whitespace
        pattern = re.sub(r'\s+', r'\\s+', re.escape(search_normalized))
        try:
            match = re.search(pattern, self.html_content, re.IGNORECASE)
            if match:
                return match.start(), match.end()
        except:
            pass

        # Try matching first few words - find start, then search for end
        words = search_normalized.split()
        if len(words) >= 3:
            # Find start using first 3-5 words
            start_words = words[:min(5, len(words))]
            start_pattern = r'\s+'.join(re.escape(w) for w in start_words)
            try:
                start_match = re.search(start_pattern, self.html_content, re.IGNORECASE)
                if start_match:
                    # Find end using last 3-5 words
                    end_words = words[-min(5, len(words)):]
                    end_pattern = r'\s+'.join(re.escape(w) for w in end_words)
                    # Search for end pattern after start
                    end_match = re.search(end_pattern, self.html_content[start_match.start():], re.IGNORECASE)
                    if end_match:
                        return start_match.start(), start_match.start() + end_match.end()
                    else:
                        # Fallback: use approximate chunk length
                        return start_match.start(), min(start_match.start() + len(search_text), len(self.html_content))
            except:
                pass

        return None, None


def create_position_mapper(html_content: str) -> HTMLPositionMapper:
    """
    Create a position mapper for HTML content.

    Convenience function.
    """
    return HTMLPositionMapper(html_content)


def map_chunk_positions(
    html_content: str,
    chunk_text: str,
    text_start: int,
    text_end: int
) -> Dict[str, Optional[int]]:
    """
    Map chunk positions from extracted text to raw HTML.

    Args:
        html_content: Raw HTML content
        chunk_text: The chunk's text content
        text_start: Chunk start in extracted text
        text_end: Chunk end in extracted text

    Returns:
        Dict with 'html_start' and 'html_end' keys
    """
    mapper = HTMLPositionMapper(html_content)

    # Try position-based mapping first
    html_start, html_end = mapper.text_to_html(text_start, text_end)

    # If that fails, try fuzzy text search
    if html_start is None:
        html_start, html_end = mapper.find_text_in_html_fuzzy(chunk_text)

    return {
        'html_start': html_start,
        'html_end': html_end
    }
