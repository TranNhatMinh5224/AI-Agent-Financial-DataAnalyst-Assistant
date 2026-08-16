"""
table_extract.py — HTML table extraction from OCR page text.

Phase 1, Step 4.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from financial_text_to_pandas.types import HtmlTableBlock, ReportMetadata

# Number of characters to capture as context before/after a table block
_NEARBY_CHARS = 300

# Regex to find raw <table>...</table> blocks (greedy, handles newlines)
_TABLE_RE = re.compile(r"(<table\b[^>]*>.*?</table>)", re.IGNORECASE | re.DOTALL)


def extract_html_tables(
    page_text: str,
    report_meta: ReportMetadata,
    page_number: int,
) -> List[HtmlTableBlock]:
    """Extract all HTML table blocks from a single page's text.

    Args:
        page_text: Raw text of one page (may contain mixed HTML tables and plain text).
        report_meta: Report-level metadata used to build table_id.
        page_number: Page number (1-indexed).

    Returns:
        List of HtmlTableBlock objects, one per <table> found.
    """
    blocks: List[HtmlTableBlock] = []

    for table_index, match in enumerate(_TABLE_RE.finditer(page_text)):
        html = match.group(1)
        start, end = match.start(), match.end()

        # Capture nearby text (strip HTML tags from nearby text for readability)
        before_raw = page_text[max(0, start - _NEARBY_CHARS) : start]
        after_raw = page_text[end : end + _NEARBY_CHARS]

        nearby_before = _strip_tags(before_raw).strip()[-_NEARBY_CHARS:]
        nearby_after = _strip_tags(after_raw).strip()[:_NEARBY_CHARS]

        table_id = _build_table_id(report_meta, page_number, table_index)

        blocks.append(
            HtmlTableBlock(
                table_id=table_id,
                page_number=page_number,
                table_index=table_index,
                html=html,
                nearby_text_before=nearby_before,
                nearby_text_after=nearby_after,
            )
        )

    return blocks


def _build_table_id(
    report_meta: ReportMetadata,
    page_number: int,
    table_index: int,
) -> str:
    """Build a deterministic table_id from report metadata.

    Format: {ticker}_{year}_{report_type}_page{page_number}_table{table_index}
    """
    return (
        f"{report_meta.ticker}_{report_meta.year}_{report_meta.report_type}"
        f"_page{page_number}_table{table_index}"
    )


def _strip_tags(html: str) -> str:
    """Remove HTML tags, returning plain text."""
    try:
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator=" ")
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
