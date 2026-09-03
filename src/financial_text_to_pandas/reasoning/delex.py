"""
delex.py — 3-Step De-lexicalization Pipeline for Numeric Masking.

Purpose:
    Prevent LLM from "hallucinating" numbers during code generation by fully
    removing raw numeric values from the prompt context, replacing them with
    symbolic placeholders [NUM_X], then restoring real values at execution time.

Pipeline:
    Step 1 — Masking Context & Query:
        Scan the question text and any inline numeric context,
        replace every numeric literal with a placeholder [NUM_X].
        This guarantees the LLM never "sees" raw numbers.

    Step 2 — Symbolic Program Generation:
        LLM receives the masked question + masked grounded cells,
        and only generates algebraic/logic formulas like:
            result = (NUM_1 - NUM_0) / NUM_0 * 100

    Step 3 — Deterministic Value Binding:
        The runtime maps each placeholder back to its real float value
        and executes the code in the secure Sandbox.

References:
    - MultiHiertt Benchmark (Zhao et al., ACL 2022)
    - Program-of-Thoughts (PoT) Prompting paradigm
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ── Numeric pattern covering Vietnamese financial formatting ──────────────────
# Matches: 1,234.56  |  1.234,56  |  500  |  500M  |  68.4%  |  (1,234)
_NUM_PATTERN = re.compile(
    r"""
    (?<!\w)                         # not preceded by a word character
    (?:
        -?                          # optional negative sign
        (?:
            \d{1,3}(?:[.,]\d{3})*   # thousands-separated integer part
            (?:[.,]\d+)?            # optional decimal
            |
            \d+(?:[.,]\d+)?         # simple integer or decimal
        )
        (?:[MBKmb%])?               # optional suffix (M=million, B=billion, %)
    )
    (?!\w)                          # not followed by a word character
    """,
    re.VERBOSE,
)


@dataclass
class DelexResult:
    """Result of the De-lexicalization step (Step 1)."""
    masked_text: str                     # text with [NUM_X] placeholders
    num_map: Dict[str, str]              # {symbol: original_string}  e.g. {"NUM_0": "500M"}


@dataclass
class DelexContext:
    """Full de-lexicalized context passed into the PoT prompt."""
    masked_question: str
    masked_cells_str: str
    # symbol_map holds float values (for sandbox injection)
    symbol_map: Dict[str, float]
    # raw_map holds original string representations (for audit/display)
    raw_map: Dict[str, str]


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Masking
# ─────────────────────────────────────────────────────────────────────────────

def mask_numbers_in_text(text: str, start_index: int = 0) -> Tuple[str, Dict[str, str]]:
    """Step 1: Replace all numeric literals in text with [NUM_X] placeholders.

    Args:
        text: Raw text (question or context string).
        start_index: Starting index for placeholder naming (allows merging maps).

    Returns:
        Tuple of (masked_text, num_map) where num_map = {"NUM_0": "500M", ...}
    """
    num_map: Dict[str, str] = {}
    counter = [start_index]  # mutable for closure

    def replace_match(m: re.Match) -> str:
        raw = m.group(0)
        sym = f"NUM_{counter[0]}"
        num_map[sym] = raw
        counter[0] += 1
        return f"[{sym}]"

    masked = _NUM_PATTERN.sub(replace_match, text)
    return masked, num_map


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Build full De-lex context from question + grounded cells
# ─────────────────────────────────────────────────────────────────────────────

def build_delex_context(
    question: str,
    grounded_cells: list,  # list[GroundedCell]
) -> DelexContext:
    """Build the complete de-lexicalized context for PoT prompt generation.

    This merges:
      - Masked question (numbers in the question replaced with placeholders)
      - Masked grounded cells (already assigned NUM_X symbols from grounding phase)

    Args:
        question: User's raw question string.
        grounded_cells: List of GroundedCell objects (already symbol-assigned).

    Returns:
        DelexContext with masked_question, masked_cells_str, symbol_map, raw_map.
    """
    # Step 1a: Mask question text
    # Start counter after all grounded cell symbols to avoid collisions
    cell_sym_count = sum(1 for c in grounded_cells if c.symbol_name)
    masked_question, question_num_map = mask_numbers_in_text(question, start_index=cell_sym_count)

    # Step 1b: Build symbol_map and cell description from grounded cells
    symbol_map: Dict[str, float] = {}
    raw_map: Dict[str, str] = {}
    cell_lines: List[str] = []

    for cell in grounded_cells:
        if cell.symbol_name:
            symbol_map[cell.symbol_name] = cell.parsed_value
            raw_map[cell.symbol_name] = cell.raw_value
            cell_lines.append(f"- {cell.to_linearized_coordinate_path()}")

    # Step 1c: Add question-level numbers to raw_map and inject parsed float into symbol_map
    from financial_text_to_pandas.reasoning.tools import parse_vn_number
    for sym, raw_str in question_num_map.items():
        raw_map[sym] = raw_str
        parsed = parse_vn_number(raw_str)
        if parsed is not None:
            symbol_map[sym] = parsed

    masked_cells_str = "\n".join(cell_lines) if cell_lines else "(no grounded cells)"

    return DelexContext(
        masked_question=masked_question,
        masked_cells_str=masked_cells_str,
        symbol_map=symbol_map,
        raw_map=raw_map,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Deterministic Value Binding (executed in sandbox.py)
# ─────────────────────────────────────────────────────────────────────────────

def render_audit_trace(ctx: DelexContext) -> str:
    """Render a human-readable audit trace showing the NUM_X → value binding.

    Useful for the UI evidence viewer and for debugging.
    """
    lines = ["[De-lexicalization Binding Table]"]
    for sym, raw in ctx.raw_map.items():
        float_val = ctx.symbol_map.get(sym)
        float_str = f" → {float_val}" if float_val is not None else ""
        lines.append(f"  {sym} = '{raw}'{float_str}")
    return "\n".join(lines)
