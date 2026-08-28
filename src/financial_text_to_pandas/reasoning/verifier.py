"""
verifier.py — Verify the reasoning trace and final answer.

Phase 3, Step 10.
"""

from __future__ import annotations

from typing import Dict
import pandas as pd

from financial_text_to_pandas.types import (
    ReasoningResult, 
    CellGroundingResult, 
    EvidencePackage, 
    VerificationResult
)



def verify_against_text_narrative(
    numeric_result: float,
    unit: str | None,
    linked_text_context: list[str],
    question: str,
    llm_config: dict
) -> tuple[str, str]:
    """Verify numeric calculation against linked text notes (Thuyết minh BCTC) using the Critic LLM.
    
    Returns:
        tuple of (verification_status, explanation)
    """
    if not linked_text_context:
        return "verified_single", "Cells exist. Calculation executed successfully (Single Verification - No text narrative available)."
        
    combined_text = " ".join(linked_text_context)
    
    from financial_text_to_pandas.reasoning.llm import call_llm
    from financial_text_to_pandas.reasoning.prompts import DUAL_VERIFY_PROMPT_TEMPLATE
    
    prompt = DUAL_VERIFY_PROMPT_TEMPLATE.format(
        numeric_result=numeric_result,
        unit=unit or "",
        question=question,
        linked_text_context=combined_text
    )
    
    try:
        response = call_llm(prompt, llm_config)
        response_upper = response.upper()
        
        if "VERDICT: CONSISTENT" in response_upper:
            status = "verified_dual"
        elif "VERDICT: CONTRADICTED" in response_upper:
            status = "mismatch_narrative"
        else:
            status = "verified_single"
            
        return status, f"Critic LLM evaluation: {response}"
    except Exception as e:
        return "verified_single", f"Critic LLM failed, fallback to single verification. Error: {str(e)}"


def verify_answer(
    result: ReasoningResult, 
    grounding: CellGroundingResult, 
    package: EvidencePackage,
    dfs: Dict[str, pd.DataFrame],
    llm_config: dict
) -> VerificationResult:
    """Verify the ReasoningResult against grounded cells, raw data, and text notes.
    
    Args:
        result: The ReasoningResult containing the final answer.
        grounding: Grounded cells.
        package: The initial evidence package.
        dfs: The loaded dataframes.
        
    Returns:
        VerificationResult
    """
    if result.error_type is not None:
        return VerificationResult(
            is_valid=False,
            verification_status="invalid",
            error_type=result.error_type,
            checked_cells=grounding.grounded_cells,
            calculation_check="Reasoning failed with error.",
            final_answer=0.0
        )
        
    if result.numeric_result is None:
        return VerificationResult(
            is_valid=False,
            verification_status="invalid",
            error_type="U_UNVERIFIED",
            checked_cells=grounding.grounded_cells,
            calculation_check="No numeric result returned.",
            final_answer=0.0
        )
        
    # Verify cells actually exist in dataframes
    for cell in grounding.grounded_cells:
        if cell.table_id not in dfs:
            return VerificationResult(
                is_valid=False,
                verification_status="invalid",
                error_type="E_NUMERICAL_EXTRACTION",
                checked_cells=grounding.grounded_cells,
                calculation_check=f"Table {cell.table_id} missing from evidence.",
                final_answer=result.numeric_result
            )
            
        df = dfs[cell.table_id]
        if cell.column_label not in df.columns:
            return VerificationResult(
                is_valid=False,
                verification_status="invalid",
                error_type="E_NUMERICAL_EXTRACTION",
                checked_cells=grounding.grounded_cells,
                calculation_check=f"Column {cell.column_label} missing.",
                final_answer=result.numeric_result
            )
            
    # Perform Dual Verification against linked text notes (Thuyết minh BCTC)
    status, check_msg = verify_against_text_narrative(
        result.numeric_result,
        package.intent.unit_requested if package and package.intent else None,
        package.linked_text_context if package else [],
        package.question if package else "",
        llm_config
    )
    
    is_valid = status in {"verified_dual", "verified_single", "valid"}
    
    return VerificationResult(
        is_valid=is_valid,
        verification_status=status,
        error_type=None if is_valid else "U_UNVERIFIED",
        checked_cells=grounding.grounded_cells,
        calculation_check=check_msg,
        final_answer=result.numeric_result
    )
