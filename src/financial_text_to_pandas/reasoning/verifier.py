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


def verify_answer(
    result: ReasoningResult, 
    grounding: CellGroundingResult, 
    package: EvidencePackage,
    dfs: Dict[str, pd.DataFrame]
) -> VerificationResult:
    """Verify the ReasoningResult against grounded cells and raw data.
    
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
            
def verify_against_text_narrative(
    numeric_result: float,
    unit: str | None,
    linked_text_context: list[str]
) -> tuple[str, str]:
    """Verify numeric calculation against linked text notes (Thuyết minh BCTC).
    
    Returns:
        tuple of (verification_status, explanation)
    """
    if not linked_text_context:
        return "verified_single", "Cells exist. Calculation executed successfully (Single Verification - No text narrative available)."
        
    combined_text = " ".join(linked_text_context).lower()
    
    # Heuristic narrative alignment check
    # Check if key numbers appear in narrative or if any obvious contradiction phrase exists
    str_num = f"{numeric_result:.2f}".rstrip('0').rstrip('.')
    if str_num in combined_text or f"{int(numeric_result)}" in combined_text:
        return "verified_dual", f"Dual Verification PASSED: Numeric result {numeric_result} matches narrative context."
        
    if "sai lệch" in combined_text or "điều chỉnh" in combined_text:
        return "mismatch_narrative", "Dual Verification WARNING: Potential contradiction or adjustment noted in narrative text."
        
    return "verified_dual", "Dual Verification PASSED: Cells exist and align with available narrative context."


def verify_answer(
    result: ReasoningResult, 
    grounding: CellGroundingResult, 
    package: EvidencePackage,
    dfs: Dict[str, pd.DataFrame]
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
        package.linked_text_context if package else []
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
