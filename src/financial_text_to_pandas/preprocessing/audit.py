"""
audit.py — Write preprocessing audit log.

Phase 1, Step 12.
No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from financial_text_to_pandas.types import AuditRow

_AUDIT_COLUMNS = [
    "report_id", "table_id", "status", "raw_shape", "clean_shape",
    "numeric_cell_count", "quality_score", "needs_review", "review_reason",
    "error_message",
]


def write_audit(rows: List[AuditRow], output_root: Path) -> None:
    """Append audit rows to preprocessing_audit.csv.

    Creates or appends to the file, preserving stable column order.
    Every table — including failed ones — must appear in this log.

    Args:
        rows: List of AuditRow objects.
        output_root: The preprocessing output root directory.
    """
    output_path = output_root / "preprocessing_audit.csv"
    write_header = not output_path.exists()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_AUDIT_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(_to_dict(row))


def load_audit(output_root: Path) -> dict[str, str]:
    """Load audit file and return a mapping of table_id -> status.

    Used by the pipeline to implement resume (skip already processed tables).
    Returns empty dict if audit file does not exist.
    """
    audit_path = output_root / "preprocessing_audit.csv"
    if not audit_path.exists():
        return {}

    result: dict[str, str] = {}
    try:
        with audit_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                table_id = row.get("table_id", "").strip()
                status = row.get("status", "").strip()
                if table_id:
                    result[table_id] = status
    except Exception:
        pass
    return result


def _to_dict(row: AuditRow) -> dict:
    return {
        "report_id": row.report_id,
        "table_id": row.table_id,
        "status": row.status,
        "raw_shape": row.raw_shape,
        "clean_shape": row.clean_shape,
        "numeric_cell_count": row.numeric_cell_count,
        "quality_score": row.quality_score,
        "needs_review": row.needs_review,
        "review_reason": row.review_reason,
        "error_message": row.error_message,
    }
