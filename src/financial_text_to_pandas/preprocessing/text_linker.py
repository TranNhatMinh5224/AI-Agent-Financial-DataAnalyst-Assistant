"""
text_linker.py — Replace HTML table blocks with TABLE_REF markers.

Phase 1, Step 11.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import re
from typing import List

from financial_text_to_pandas.types import TableRef

# Matches raw <table>...</table> blocks (greedy, handles newlines)
_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)


def replace_tables_with_refs(report_text: str, table_refs: List[TableRef]) -> str:
    """Replace HTML table blocks in report_text with TABLE_REF markers.

    Replaces tables in the order they appear in report_text.
    If more tables are found than table_refs, surplus tables are removed silently.
    Page boundary markers (===== PAGE n =====) are preserved.

    Args:
        report_text: Full OCR TXT content (may span multiple pages).
        table_refs: Ordered list of TableRef objects matching the order tables
                    appear in the text.

    Returns:
        Text with HTML table blocks replaced by TABLE_REF markers.
    """
    ref_iter = iter(table_refs)

    def replace_match(match: re.Match) -> str:  # type: ignore[type-arg]
        try:
            ref = next(ref_iter)
            return f"[[TABLE_REF:{ref.table_id}|{ref.csv_path}]]"
        except StopIteration:
            # More tables in text than refs — remove the table block
            return ""

    linked = _TABLE_RE.sub(replace_match, report_text)
    return linked
