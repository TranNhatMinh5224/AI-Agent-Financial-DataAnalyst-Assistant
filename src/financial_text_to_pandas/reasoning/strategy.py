"""
strategy.py — Choose and execute the reasoning strategy.

Phase 3, Steps 4, 5.
"""

from __future__ import annotations

from typing import Literal, Dict
import pandas as pd

from financial_text_to_pandas.types import Intent, CellGroundingResult, ReasoningResult, EvidencePackage
from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox


# BUG-012 FIX: Explicit mapping cho tất cả operation types.
# Trước đây chỉ có "lookup" và "multi_hop" được xử lý rõ ràng;
# "sum", "count", "difference", "ratio", "mean", "median" đều silently fallback
# về "pot" nhưng không có trong answer.py strategy switch → T_TECHNICAL_ERROR.
_OP_TO_STRATEGY: dict[str, str] = {
    "lookup":       "deterministic",  # Chỉ dung khi có đúng 1 cell
    "growth_rate":  "pot",
    "difference":   "pot",
    "ratio":        "pot",
    "sum":          "pot",
    "count":        "pot",
    "mean":         "pot",
    "median":       "pot",
    "multi_hop":    "multi_hop",
    "unknown":      "pot",
}


def choose_reasoning_strategy(
    intent: Intent,
    grounding: CellGroundingResult
) -> Literal["deterministic", "pot", "cot", "multi_hop"]:
    """Select the appropriate reasoning strategy.
    
    Logic:
    - multi_hop: khi có >= 2 năm hoặc operation == 'multi_hop'
    - deterministic: khi lookup và chính xác 1 cell
    - pot: mọi trường hợp còn lại
    """
    # Multi-hop: ít nhất 2 năm khác nhau trong câu hỏi
    if intent.operation == "multi_hop" or len(intent.years) >= 2:
        return "multi_hop"

    cells = grounding.grounded_cells

    # Direct exact lookup: đúng 1 cell và operation là lookup
    if intent.operation == "lookup" and len(cells) == 1:
        return "deterministic"

    # Mọi trường hợp còn lại → PoT
    return _OP_TO_STRATEGY.get(intent.operation, "pot")


def run_deterministic_lookup(
    intent: Intent, 
    grounding: CellGroundingResult
) -> ReasoningResult:
    """Run direct lookup (no code generation needed)."""
    if not grounding.grounded_cells:
        return ReasoningResult(
            strategy="deterministic",
            code_generated=None,
            sandbox_result=None,
            numeric_result=None,
            trace="No cells available for lookup.",
            error_type="E_NUMERICAL_EXTRACTION"
        )
        
    cell = grounding.grounded_cells[0]
    return ReasoningResult(
        strategy="deterministic",
        code_generated=None,
        sandbox_result=cell.parsed_value,
        numeric_result=cell.parsed_value,
        trace=f"Directly looked up value {cell.parsed_value} from table {cell.table_id}.",
        error_type=None
    )


from financial_text_to_pandas.reasoning.prompts import POT_PROMPT_TEMPLATE, POT_FIX_PROMPT_TEMPLATE
from financial_text_to_pandas.reasoning.llm import generate_pot_code
from financial_text_to_pandas.reasoning.delex import build_delex_context, render_audit_trace

def run_pot_strategy(
    package: EvidencePackage, 
    grounding: CellGroundingResult,
    dfs: Dict[str, pd.DataFrame],
    llm_config: dict[str, str | float],
    max_retries: int = 3
) -> ReasoningResult:
    """Run PoT reasoning strategy with 3-Step De-lexicalization, Self-Correction Loop.

    Steps:
        1. De-lexicalize: Mask all numeric literals in question + grounded cells
           with [NUM_X] placeholders (prevents LLM from "hallucinating" numbers).
        2. Symbolic Program Generation: LLM generates formula using placeholders only.
        3. Deterministic Value Binding: Inject real float values into Sandbox globals
           and execute the symbolic formula deterministically.
    """
    # ── Step 1: De-lexicalization (Masking) ──────────────────────────────────
    ctx = build_delex_context(
        question=package.question,
        grounded_cells=grounding.grounded_cells,
    )
    delex_trace = render_audit_trace(ctx)

    code = ""
    last_error = ""
    trace_steps = [delex_trace]

    # ── Steps 2 + 3: Symbolic Generation → Self-Correction → Sandbox Execution ─
    for attempt in range(1, max_retries + 1):
        try:
            if attempt == 1:
                # Step 2: Symbolic Program Generation on masked input
                prompt = POT_PROMPT_TEMPLATE.format(
                    question=ctx.masked_question,
                    grounded_cells=ctx.masked_cells_str,
                )
                code = generate_pot_code(prompt, llm_config)
                trace_steps.append("Attempt 1: Symbolic code generated on masked prompt.")
            else:
                # Self-Correction: send error back to LLM with masked context
                fix_prompt = POT_FIX_PROMPT_TEMPLATE.format(
                    question=ctx.masked_question,
                    grounded_cells=ctx.masked_cells_str,
                    previous_code=code,
                    error_message=last_error,
                )
                code = generate_pot_code(fix_prompt, llm_config)
                trace_steps.append(f"Attempt {attempt}: Self-Correction fix code generated.")

            # Step 3: Deterministic Value Binding → inject symbol_map into Sandbox
            sandbox_val = run_pandas_sandbox(code, dfs, symbol_map=ctx.symbol_map)
            numeric_val = float(sandbox_val)

            trace_msg = " | ".join(trace_steps) + " | Execution successful."
            return ReasoningResult(
                strategy="pot",
                code_generated=code,
                sandbox_result=sandbox_val,
                numeric_result=numeric_val,
                trace=trace_msg,
                error_type=None,
            )

        except Exception as e:
            last_error = str(e)
            trace_steps.append(f"Attempt {attempt} error: {last_error}")

    return ReasoningResult(
        strategy="pot",
        code_generated=code,
        sandbox_result=None,
        numeric_result=None,
        trace=" | ".join(trace_steps),
        error_type="C_CALCULATION_ERROR",
    )

