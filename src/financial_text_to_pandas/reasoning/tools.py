"""
tools.py — Helper functions for the PoT Sandbox.

Phase 3, Step 4.
"""

from __future__ import annotations

import pandas as pd
from typing import Optional, Dict
from financial_text_to_pandas.preprocessing.number_parser import parse_vn_number as preprocess_parse_vn_number

def parse_vn_number(raw_val: str) -> Optional[float]:
    """Parse a Vietnamese number string."""
    parsed = preprocess_parse_vn_number(str(raw_val))
    return parsed.parsed_value

def normalize_unit(val: float, from_unit: Optional[str], to_unit: Optional[str]) -> float:
    """Normalize a value between units (triệu đồng, tỷ đồng, etc.)."""
    if not from_unit or not to_unit:
        return val
        
    from_u = from_unit.lower().replace("đồng", "").strip()
    to_u = to_unit.lower().replace("đồng", "").strip()
    
    multipliers = {
        "vnđ": 1,
        "vnd": 1,
        "nghìn": 10**3,
        "triệu": 10**6,
        "tỷ": 10**9,
        "tỉ": 10**9
    }
    
    from_mult = multipliers.get(from_u, 1)
    to_mult = multipliers.get(to_u, 1)
    
    # Scale to base (VND) then divide by target
    base_val = val * from_mult
    return base_val / to_mult

def safe_get_cell(dfs: Dict[str, pd.DataFrame], table_id: str, row_label: str, col_label: str) -> float:
    """Safely get and parse a cell from the dataframes."""
    if table_id not in dfs:
        raise ValueError(f"Table {table_id} not found in evidence.")
        
    df = dfs[table_id]
    
    row_col = "row_label_full" if "row_label_full" in df.columns else "row_label_raw"
    if row_col not in df.columns:
        raise ValueError(f"Row label column not found in table {table_id}.")
        
    matches = df[df[row_col] == row_label]
    if matches.empty:
        raise ValueError(f"Row '{row_label}' not found in table {table_id}.")
        
    if col_label not in df.columns:
        raise ValueError(f"Column '{col_label}' not found in table {table_id}.")
        
    raw_val = matches.iloc[0][col_label]
    parsed = parse_vn_number(str(raw_val))
    
    if parsed is None:
        raise ValueError(f"Cell value '{raw_val}' could not be parsed as a number.")
        
    return parsed
