"""
strategy.py — Choose and execute the reasoning strategy.

Phase 3, Steps 4, 5.
"""

from __future__ import annotations

from typing import Literal, Dict
import pandas as pd

from financial_text_to_pandas.types import Intent, CellGroundingResult, ReasoningResult, EvidencePackage
from financial_text_to_pandas.reasoning.sandbox import run_pandas_sandbox


def choose_reasoning_strategy(
    intent: Intent, 
    grounding: CellGroundingResult
) -> Literal["deterministic", "pot", "cot", "multi_hop"]:
    """Select the appropriate reasoning strategy."""
    
    if intent.operation == "multi_hop":
        return "multi_hop"
        
    cells = grounding.grounded_cells
    
    # Direct exact lookup
    if intent.operation == "lookup" and len(cells) == 1:
        return "deterministic"
        
    # Default to PoT for anything involving arithmetic or aggregation
    return "pot"


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


from financial_text_to_pandas.reasoning.prompts import POT_PROMPT_TEMPLATE
from financial_text_to_pandas.reasoning.llm import generate_pot_code

def run_pot_strategy(
    package: EvidencePackage, 
    grounding: CellGroundingResult,
    dfs: Dict[str, pd.DataFrame],
    llm_config: dict[str, str | float]
) -> ReasoningResult:
    """Run PoT reasoning strategy with Self-Correction Loop."""
    
    max_retries = 3
    base_prompt = POT_PROMPT_TEMPLATE.format(
        question=package.question,
        grounded_cells=grounding.grounded_cells
    )
    prompt = base_prompt
    
    last_error = ""
    last_code = ""
    
    for attempt in range(max_retries):
        try:
            # Generate code via LLM
            code = generate_pot_code(prompt, llm_config)
            last_code = code
            
            # Run in sandbox
            sandbox_val = run_pandas_sandbox(code, dfs)
            
            # Parse result
            numeric_val = float(sandbox_val)
            
            return ReasoningResult(
                strategy="pot",
                code_generated=code,
                sandbox_result=sandbox_val,
                numeric_result=numeric_val,
                trace=f"Generated and executed Pandas code successfully after {attempt + 1} attempts.",
                error_type=None
            )
            
        except Exception as e:
            last_error = str(e)
            # Create correction prompt
            prompt = f"{base_prompt}\n\nWARNING: MÃ CODE BẠN VỪA SINH RA BỊ LỖI KHI CHẠY: {last_error}\nCode cũ của bạn:\n```python\n{last_code}\n```\nHãy phân tích lỗi này (đặc biệt chú ý lỗi KeyError do sai chính tả OCR tên dòng/cột) và viết lại mã code Pandas chính xác hơn."
            
    return ReasoningResult(
        strategy="pot",
        code_generated=last_code,
        sandbox_result=None,
        numeric_result=None,
        trace=f"PoT failed after {max_retries} attempts. Last error: {last_error}",
        error_type="C_CALCULATION_ERROR"
    )
