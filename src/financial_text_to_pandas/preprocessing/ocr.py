"""
ocr.py — OCR TXT page splitting.

Phase 1, Step 2.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import re
from typing import List

from financial_text_to_pandas.types import Page

# Matches markers like:
#   ===== PAGE 1 =====
#   =====PAGE 2=====
#   ===== page 3 =====
_PAGE_MARKER_RE = re.compile(
    r"=====\s*PAGE\s+(\d+)\s*=====",
    re.IGNORECASE,
)


def split_pages(raw_text: str) -> List[Page]:
    """Split a raw OCR TXT report into a list of Page objects.

    Rules:
    - Detect '===== PAGE n =====' markers (case-insensitive, flexible whitespace).
    - Preserve page number and all text after the marker (up to next marker).
    - If no marker exists, return a single Page with page_number=1.

    Args:
        raw_text: The full content of an OCR TXT file.

    Returns:
        Ordered list of Page objects.
    """
    if not raw_text:
        return [Page(page_number=1, raw_text="")]

    # Find all marker positions
    markers = list(_PAGE_MARKER_RE.finditer(raw_text))

    if not markers:
        # No page markers found — treat entire text as page 1
        return [Page(page_number=1, raw_text=raw_text.strip())]

    pages: List[Page] = []

    for i, match in enumerate(markers):
        page_number = int(match.group(1))
        # Text starts after the marker line
        text_start = match.end()
        # Text ends at the next marker (or end of file)
        text_end = markers[i + 1].start() if i + 1 < len(markers) else len(raw_text)
        page_text = raw_text[text_start:text_end].strip()
        pages.append(Page(page_number=page_number, raw_text=page_text))

    return pages
