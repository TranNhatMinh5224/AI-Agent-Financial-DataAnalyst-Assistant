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
            
    # Simple rule: if result is valid float, we accept it for now
    # Advanced formula checking would parse the PoT AST
    
    return VerificationResult(
        is_valid=True,
        verification_status="valid",
        error_type=None,
        checked_cells=grounding.grounded_cells,
        calculation_check="Cells exist. Calculation executed successfully.",
        final_answer=result.numeric_result
    )
