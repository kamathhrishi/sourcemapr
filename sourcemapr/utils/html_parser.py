"""
HTML Processing Utilities for SourcemapR.

Provides utilities for parsing HTML files with proper:
- Page break detection (CSS page-break, HR tags, etc.)
- Character position to page number mapping
- Clean text extraction

Works with any HTML file, including SEC EDGAR filings.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# Common page break patterns in HTML
PAGE_BREAK_PATTERNS = [
    # CSS page-break styles (SEC filings, printed documents)
    re.compile(r'<hr[^>]*style\s*=\s*["\'][^"\']*page-break[^"\']*["\'][^>]*/?\s*>', re.IGNORECASE),
    re.compile(r'<div[^>]*style\s*=\s*["\'][^"\']*page-break[^"\']*["\'][^>]*>', re.IGNORECASE),
    # HTML comments marking pages
    re.compile(r'<!--\s*PAGE\s*(?:BREAK)?\s*-->', re.IGNORECASE),
    re.compile(r'<!--\s*NEW\s*PAGE\s*-->', re.IGNORECASE),
]

# Page break marker for text extraction
PAGE_BREAK_MARKER = "\n\n--- PAGE BREAK ---\n\n"


@dataclass
class HTMLPage:
    """Represents a logical page in an HTML document."""
    page_number: int
    start_pos: int  # Start position in extracted text
    end_pos: int    # End position in extracted text
    text: str       # Page text content


class HTMLParser:
    """
    Processes HTML files to extract structured content with page detection.

    Handles:
    - Page break detection via CSS styles and HTML patterns
    - Clean text extraction with position mapping
    - Page number calculation for any text position

    Usage:
        parser = HTMLParser(html_content)
        text = parser.extracted_text
        page_num = parser.get_page_for_position(char_position)
    """

    def __init__(self, html_content: str, filename: str = None):
        """
        Initialize the HTML parser.

        Args:
            html_content: Raw HTML content
            filename: Optional filename for context
        """
        self.html_content = html_content
        self.filename = filename
        self._pages: Optional[List[HTMLPage]] = None
        self._extracted_text: Optional[str] = None
        self._page_positions: Optional[Dict[int, Tuple[int, int]]] = None

    @property
    def extracted_text(self) -> str:
        """Get the extracted text with page break markers."""
        if self._extracted_text is None:
            self._process()
        return self._extracted_text

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        if self._pages is None:
            self._process()
        return len(self._pages) if self._pages else 1

    @property
    def page_positions(self) -> Dict[int, Tuple[int, int]]:
        """Get mapping of page_num -> (start_pos, end_pos) in extracted text."""
        if self._page_positions is None:
            self._process()
        return self._page_positions

    def _process(self):
        """Process the HTML to extract text and detect pages."""
        # Find all page breaks in the HTML
        page_break_positions = self._find_page_breaks()

        if page_break_positions:
            self._extract_with_page_breaks(page_break_positions)
        else:
            self._extract_single_page()

    def _find_page_breaks(self) -> List[Tuple[int, int]]:
        """Find all page break positions in HTML.

        Returns:
            List of (start, end) positions of page break elements
        """
        breaks = []
        for pattern in PAGE_BREAK_PATTERNS:
            for match in pattern.finditer(self.html_content):
                breaks.append((match.start(), match.end()))

        # Sort by position
        breaks.sort(key=lambda x: x[0])
        return breaks

    def _extract_with_page_breaks(self, page_breaks: List[Tuple[int, int]]):
        """Extract text from HTML with page breaks."""
        try:
            from bs4 import BeautifulSoup
            use_bs = True
        except ImportError:
            use_bs = False

        # Split HTML by page breaks
        html_sections = []
        prev_end = 0
        for start, end in page_breaks:
            html_sections.append(self.html_content[prev_end:start])
            prev_end = end
        # Add final section after last page break
        if prev_end < len(self.html_content):
            html_sections.append(self.html_content[prev_end:])

        # Extract text from each section
        self._pages = []
        self._page_positions = {}
        text_parts = []
        current_pos = 0

        for i, html_section in enumerate(html_sections):
            page_num = i + 1

            # Extract text
            if use_bs:
                section_text = self._extract_text_bs(html_section)
            else:
                section_text = self._extract_text_simple(html_section)

            # Skip empty pages
            if not section_text.strip():
                continue

            # Store page info
            start_pos = current_pos
            end_pos = current_pos + len(section_text)

            self._pages.append(HTMLPage(
                page_number=page_num,
                start_pos=start_pos,
                end_pos=end_pos,
                text=section_text
            ))
            self._page_positions[page_num] = (start_pos, end_pos)

            text_parts.append(section_text)
            current_pos = end_pos

            # Add page break marker (except after last page)
            if i < len(html_sections) - 1:
                text_parts.append(PAGE_BREAK_MARKER)
                current_pos += len(PAGE_BREAK_MARKER)

        self._extracted_text = ''.join(text_parts)

        # Re-number pages if some were skipped
        if self._pages:
            for i, page in enumerate(self._pages):
                page.page_number = i + 1
            self._page_positions = {
                i + 1: (p.start_pos, p.end_pos)
                for i, p in enumerate(self._pages)
            }

    def _extract_single_page(self):
        """Extract text as a single page (no page breaks detected)."""
        try:
            from bs4 import BeautifulSoup
            text = self._extract_text_bs(self.html_content)
        except ImportError:
            text = self._extract_text_simple(self.html_content)

        self._extracted_text = text
        self._pages = [HTMLPage(
            page_number=1,
            start_pos=0,
            end_pos=len(text),
            text=text
        )]
        self._page_positions = {1: (0, len(text))}

    def _extract_text_bs(self, html: str) -> str:
        """Extract text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # Remove script, style, and other non-content tags
        for tag in soup(['script', 'style', 'meta', 'link', 'head']):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator='\n')
        return self._clean_text(text)

    def _extract_text_simple(self, html: str) -> str:
        """Simple HTML to text conversion without BeautifulSoup."""
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode common entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&apos;', "'")
        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text while preserving structure."""
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Clean up leading/trailing whitespace on each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        return text.strip()

    def get_page_for_position(self, position: int) -> int:
        """
        Get the page number for a character position in extracted text.

        Args:
            position: Character index in the extracted text

        Returns:
            Page number (1-indexed)
        """
        if self._page_positions is None:
            self._process()

        for page_num, (start, end) in sorted(self._page_positions.items()):
            if start <= position < end:
                return page_num

        # If position is beyond all pages, return last page
        if self._pages:
            return self._pages[-1].page_number
        return 1

    def get_pages(self) -> List[HTMLPage]:
        """Get all pages in the document."""
        if self._pages is None:
            self._process()
        return self._pages


def extract_text_with_pages(html_content: str, filename: str = None) -> Tuple[str, Dict[int, Tuple[int, int]]]:
    """
    Extract text and page position mapping from HTML.

    Convenience function that creates a parser and returns
    the extracted text and page positions.

    Args:
        html_content: Raw HTML content
        filename: Optional filename for context

    Returns:
        Tuple of (extracted_text, page_positions)
        page_positions maps page_num -> (start_pos, end_pos)
    """
    parser = HTMLParser(html_content, filename)
    return parser.extracted_text, parser.page_positions


def get_page_for_position(
    position: int,
    page_positions: Dict[int, Tuple[int, int]]
) -> int:
    """
    Get page number for a text position.

    Args:
        position: Character position in extracted text
        page_positions: Mapping of page_num -> (start, end)

    Returns:
        Page number (1-indexed)
    """
    for page_num, (start, end) in sorted(page_positions.items()):
        if start <= position < end:
            return page_num

    # Return last page if beyond end
    if page_positions:
        return max(page_positions.keys())
    return 1
