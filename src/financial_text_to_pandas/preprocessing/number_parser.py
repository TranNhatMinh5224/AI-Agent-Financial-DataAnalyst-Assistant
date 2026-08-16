"""
number_parser.py — Vietnamese financial number parser.

Phase 1, Step 8.
Supported formats:
  15.230.000       -> parsed_value=15230000       (thousands dot separator)
  12,5             -> parsed_value=12.5            (decimal comma)
  12,5%            -> parsed_value=0.125           (percent)
  (500.000)        -> parsed_value=-500000         (parentheses negative)
  -500.000         -> parsed_value=-500000         (minus prefix)
  "-"              -> parsed_value=None            (dash placeholder)
  ""               -> parsed_value=None            (empty)
  31/12/2024       -> parse_status="not_number"    (date)
  "abc"            -> parse_status="not_number"    (text)

No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import re
from typing import Optional

from financial_text_to_pandas.types import ParsedNumber

# ── Patterns ──────────────────────────────────────────────────────────────────

# Matches a date string like 31/12/2024 or 2024/12/31
_DATE_RE = re.compile(r"^\d{1,4}[/\-]\d{1,2}[/\-]\d{2,4}$")

# Matches a number optionally wrapped in parentheses (negative)
# Supports dot-as-thousands and comma-as-decimal
_PAREN_RE = re.compile(r"^\(([0-9.,]+)\)$")

# Matches a standalone dash or em-dash placeholder
_DASH_RE = re.compile(r"^[\-–—]+$")

# Characters to strip before parsing (spaces, currency symbols, nbsp)
_STRIP_CHARS = " \t\n\r\xa0"


def parse_vn_number(value: str) -> ParsedNumber:
    """Parse a Vietnamese financial number string into a ParsedNumber.

    Args:
        value: Raw string cell value from a financial table.

    Returns:
        ParsedNumber with parsed_value=None when the value is not numeric.
    """
    raw_value = value  # preserve original

    # ── Empty ─────────────────────────────────────────────────────────────────
    stripped = value.strip(_STRIP_CHARS)
    if stripped == "":
        return ParsedNumber(
            raw_value=raw_value,
            parsed_value=None,
            number_type="empty",
            unit_hint=None,
            parse_status="empty",
        )

    # ── Dash placeholder ──────────────────────────────────────────────────────
    if _DASH_RE.match(stripped):
        return ParsedNumber(
            raw_value=raw_value,
            parsed_value=None,
            number_type="empty",
            unit_hint=None,
            parse_status="empty",
        )

    # ── Date ──────────────────────────────────────────────────────────────────
    if _DATE_RE.match(stripped):
        return ParsedNumber(
            raw_value=raw_value,
            parsed_value=None,
            number_type="not_number",
            unit_hint=None,
            parse_status="not_number",
        )

    # ── Percent ───────────────────────────────────────────────────────────────
    is_percent = stripped.endswith("%")
    if is_percent:
        stripped = stripped[:-1].strip(_STRIP_CHARS)

    # ── Parentheses negative ──────────────────────────────────────────────────
    is_negative = False
    paren_match = _PAREN_RE.match(stripped)
    if paren_match:
        is_negative = True
        stripped = paren_match.group(1)
    elif stripped.startswith("-"):
        is_negative = True
        stripped = stripped[1:].strip(_STRIP_CHARS)

    # ── Normalize Vietnamese number format ───────────────────────────────────
    # Vietnamese: dot = thousands separator, comma = decimal separator
    # We need to convert to Python float format (dot = decimal)
    try:
        normalized = _normalize_vn_numeric(stripped)
        float_val = float(normalized)
    except (ValueError, TypeError):
        # Not a recognizable number
        return ParsedNumber(
            raw_value=raw_value,
            parsed_value=None,
            number_type="not_number",
            unit_hint=None,
            parse_status="not_number",
        )

    if is_negative:
        float_val = -float_val

    if is_percent:
        float_val = float_val / 100.0
        return ParsedNumber(
            raw_value=raw_value,
            parsed_value=float_val,
            number_type="percent",
            unit_hint="%",
            parse_status="ok",
        )

    # Detect integer vs decimal
    number_type = "integer" if float_val == int(float_val) and "," not in value else "decimal"

    return ParsedNumber(
        raw_value=raw_value,
        parsed_value=float_val,
        number_type=number_type,
        unit_hint=None,
        parse_status="ok",
    )


def _normalize_vn_numeric(s: str) -> str:
    """Convert a Vietnamese numeric string to a Python-parseable float string.

    Vietnamese convention:
      - Dot '.' is the thousands separator  → remove
      - Comma ',' is the decimal separator  → replace with '.'

    Edge cases handled:
      - Pure integer with no comma: just remove dots.
      - Number with one comma: last segment after comma is decimals.
    """
    s = s.strip()

    # Count dots and commas
    dot_count = s.count(".")
    comma_count = s.count(",")

    if comma_count == 0 and dot_count == 0:
        # Plain integer, e.g. "15230000"
        return s

    if comma_count == 0 and dot_count >= 1:
        # Dots are thousands separators, e.g. "15.230.000"
        return s.replace(".", "")

    if comma_count == 1 and dot_count == 0:
        # Comma is decimal separator, e.g. "12,5"
        return s.replace(",", ".")

    if comma_count == 1 and dot_count >= 1:
        # Mixed: dots=thousands, comma=decimal, e.g. "1.234,56"
        s = s.replace(".", "")
        s = s.replace(",", ".")
        return s

    # Multiple commas — not a standard VN number
    raise ValueError(f"Cannot normalize: {s!r}")
