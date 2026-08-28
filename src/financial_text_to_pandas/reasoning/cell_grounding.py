"""
cell_grounding.py — Schema-Aware Cell Grounding.

Phase 3, Step 3.
"""

from __future__ import annotations

from typing import Dict
import pandas as pd
import re
from rapidfuzz import fuzz

from financial_text_to_pandas.types import Intent, GroundedCell, CellGroundingResult


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chuỗi để triệt tiêu rác OCR (OCR Noise Robustness).
    - Xóa khoảng trắng thừa, chuyển thành chữ thường.
    - Xóa các ghi chú trong ngoặc như (1), (V.1), (i).
    - Xóa các ký tự đặc biệt thừa thãi ở cuối chuỗi.
    """
    if not isinstance(text, str):
        return ""
    
    text = text.lower().strip()
    # Xóa các tham chiếu thuyết minh thường gặp dạng (1), (V.2), (vii)
    text = re.sub(r'\([ivx\d\.]+\)', ' ', text)
    # Xóa các ký tự đặc biệt không phải chữ/số (ngoại trừ khoảng trắng)
    text = re.sub(r'[^\w\s]', ' ', text)
    # Rút gọn khoảng trắng
    text = re.sub(r'\s+', ' ', text).strip()
    return text


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
        
    target_metric = intent.metrics[0]
    target_norm = _normalize_text(target_metric)
    
    found_row = False
    
    for table_id, df in dfs.items():
        if "row_label_full" in df.columns:
            row_col = "row_label_full"
        elif "row_label_raw" in df.columns:
            row_col = "row_label_raw"
        else:
            continue
            
        best_match_idx = None
        best_score = 0
        match_method = "fuzzy"
        
        for idx, label in df[row_col].items():
            label_norm = _normalize_text(str(label))
            
            # Exact Match sau khi chuẩn hóa
            if target_norm in label_norm or label_norm in target_norm:
                score = 100
                match_method = "exact_norm"
            else:
                # Fuzzy Match kết hợp partial_ratio và token_sort_ratio để lì lợm với lỗi rớt chữ
                score_partial = fuzz.partial_ratio(target_norm, label_norm)
                score_sort = fuzz.token_sort_ratio(target_norm, label_norm)
                score = max(score_partial, score_sort)
                
            if score > best_score:
                best_score = score
                best_match_idx = idx
                
            # Tránh lặp vô ích nếu đã tìm thấy điểm tuyệt đối
            if best_score == 100:
                break
                
        # Ngưỡng chấp nhận rác OCR giảm xuống 75 (tăng độ bao phủ)
        if best_match_idx is not None and best_score >= 75:
            found_row = True
            row = df.loc[best_match_idx]
            
            # Ground columns (years)
            years_to_find = intent.years if intent.years else []
            if not years_to_find:
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
                    pass
                    
                grounded_cells.append(
                    GroundedCell(
                        table_id=table_id,
                        csv_path="",
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
        
    for idx, cell in enumerate(grounded_cells):
        cell.symbol_name = f"NUM_{idx}"
        
    return CellGroundingResult(grounded_cells, None)
