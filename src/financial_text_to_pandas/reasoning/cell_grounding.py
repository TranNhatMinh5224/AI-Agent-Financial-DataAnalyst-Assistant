"""
cell_grounding.py — Schema-Aware Cell Grounding.

Phase 3, Step 3.
"""

from __future__ import annotations

from typing import Dict
import pandas as pd
from rapidfuzz import fuzz

from financial_text_to_pandas.types import Intent, GroundedCell, CellGroundingResult


def ground_cells(
    intent: Intent, 
    dfs: Dict[str, pd.DataFrame]
) -> CellGroundingResult:
    """Find the exact cells matching the user's intent.
    
    Args:
        intent: Parsed Intent.
        dfs: Dictionary of loaded DataFrames.
        
    Returns:
        CellGroundingResult with grounded cells or an error.
    """
    if not dfs:
        return CellGroundingResult([], "I_INSUFFICIENT_EVIDENCE")
        
    grounded_cells = []
    
    if not intent.metrics:
        return CellGroundingResult([], "E_NUMERICAL_EXTRACTION")
        
    target_metric = intent.metrics[0].lower()
    
    # Simple grounding heuristic for the first iteration:
    # 1. Search all tables for a row matching the metric.
    # 2. Extract cells for the requested years.
    
    found_row = False
    
    for table_id, df in dfs.items():
        if "row_label_full" in df.columns:
            row_col = "row_label_full"
        elif "row_label_raw" in df.columns:
            row_col = "row_label_raw"
        else:
            continue
            
        # 1. Exact match
        exact_matches = df[df[row_col].astype(str).str.lower().str.contains(target_metric, na=False)]
        
        # 2. Fuzzy match if no exact
        best_match_idx = None
        best_score = 0
        match_method = "exact"
        
        if not exact_matches.empty:
            best_match_idx = exact_matches.index[0]
            best_score = 100
        else:
            for idx, label in df[row_col].items():
                score = fuzz.partial_ratio(target_metric, str(label).lower())
                if score > best_score:
                    best_score = score
                    best_match_idx = idx
            match_method = "fuzzy"
            
        if best_match_idx is not None and best_score >= 80: # Confidence threshold
            found_row = True
            row = df.loc[best_match_idx]
            
            # Ground columns (years)
            years_to_find = intent.years if intent.years else []
            if not years_to_find:
                # If no year specified, grab all numeric columns
                col_cands = [c for c in df.columns if c.startswith("numeric__")]
            else:
                col_cands = [c for c in df.columns if c.startswith("numeric__") and any(str(y) in c for y in years_to_find)]
                
            for col in col_cands:
                raw_val = str(row[col])
                if pd.isna(row[col]) or raw_val.strip() == "" or raw_val == "nan":
                    continue
                    
                parsed_val = 0.0
                try:
                    parsed_val = float(raw_val)
                except ValueError:
                    pass # Keep 0.0 for now, ideally use parse_vn_number
                    
                grounded_cells.append(
                    GroundedCell(
                        table_id=table_id,
                        csv_path="", # Will be filled later or ignored
                        page_number=0,
                        row_label=str(row[row_col]),
                        column_label=col,
                        raw_value=raw_val,
                        parsed_value=parsed_val,
                        unit=intent.unit_requested,
                        confidence=best_score / 100.0,
                        grounding_method=match_method,
                        error_type=None
                    )
                )
                
    if not found_row or not grounded_cells:
        return CellGroundingResult([], "E_NUMERICAL_EXTRACTION")
        
    return CellGroundingResult(grounded_cells, None)
