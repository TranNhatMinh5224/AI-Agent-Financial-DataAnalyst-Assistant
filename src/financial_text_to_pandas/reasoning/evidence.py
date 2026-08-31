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
            csv_path = base_dir / "artifacts" / "preprocessing" / cand.csv_path
        if not csv_path.exists() and Path(cand.csv_path).exists():
            csv_path = Path(cand.csv_path)
            
        if not csv_path.exists():
            continue
            
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            dfs[cand.table_id] = df
        except Exception:
            continue
            
    # Also load linked text context for Dual Verification & Multi-hop
    load_linked_text_context(package, base_dir)
    return dfs


def load_linked_text_context(package: EvidencePackage, base_dir: Path) -> list[str]:
    """Load linked text narrative notes corresponding to evidence tables."""
    if package.linked_text_context:
        return package.linked_text_context
        
    linked_texts = []
    linked_dir = base_dir / "linked_text"
    
    for ev_table in package.tables:
        cand = ev_table.candidate
        tid = cand.table_id
        
        # Look for linked text file matching table_id or report
        txt_candidates = list(linked_dir.glob(f"*{tid}*.txt")) if linked_dir.exists() else []
        for txt_file in txt_candidates:
            try:
                content = txt_file.read_text(encoding="utf-8")
                linked_texts.append(content[:1000]) # Take top 1000 chars of narrative note
            except Exception:
                pass
                
    package.linked_text_context = linked_texts
    return linked_texts
