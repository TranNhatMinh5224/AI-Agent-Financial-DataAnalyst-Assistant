"""
evidence.py — Load evidence tables into Pandas DataFrames for Reasoning.

Phase 3, Step 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from financial_text_to_pandas.types import EvidencePackage


def load_evidence_tables(package: EvidencePackage, base_dir: Path) -> Dict[str, pd.DataFrame]:
    """Load all tables from an EvidencePackage into a dictionary of DataFrames.
    
    Args:
        package: The EvidencePackage containing candidate tables.
        base_dir: The root directory where CSVs are stored (usually output_root).
        
    Returns:
        A dictionary mapping table_id to its loaded DataFrame.
        
    Raises:
        FileNotFoundError: If a required CSV file is missing.
    """
    dfs = {}
    
    for ev_table in package.tables:
        cand = ev_table.candidate
        csv_path = base_dir / cand.csv_path
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Evidence CSV missing for table {cand.table_id}: {csv_path}")
            
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            dfs[cand.table_id] = df
        except Exception as e:
            raise RuntimeError(f"Failed to parse CSV for table {cand.table_id}: {e}")
            
    return dfs
