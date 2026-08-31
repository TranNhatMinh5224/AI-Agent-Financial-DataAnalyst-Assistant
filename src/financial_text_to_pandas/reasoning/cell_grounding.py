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
from financial_text_to_pandas.reasoning.tools import parse_vn_number


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chuỗi để triệt tiêu rác OCR (OCR Noise Robustness).
    - Xóa khoảng trắng thừa, chuyển thành chữ thường.
    - Xóa các ghi chú trong ngoặc như (1), (V.1), (i).
    - Xóa các ký tự đặc biệt thừa thãi ở cuối chuỗi.
    """
    if not isinstance(text, str):
        return ""
    
    text = text.lower().strip()
    _OCR_REPLACEMENTS = {
        "u'u": "ưu",
        "tiên": "tiền",
        "chuyên": "chuyển",
    }
    for wrong, correct in _OCR_REPLACEMENTS.items():
        text = text.replace(wrong, correct)

    # Xóa các tham chiếu thuyết minh thường gặp dạng (1), (V.2), (vii)
    text = re.sub(r'\([ivx\d\.]+\)', ' ', text)
    # Xóa các ký tự đặc biệt không phải chữ/số (ngoại trừ khoảng trắng)
    text = re.sub(r'[^\w\s]', ' ', text)
    # Rút gọn khoảng trắng
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def ground_cells(
    intent: Intent,
    dfs: Dict[str, pd.DataFrame],
    raw_question: str = "",
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

    if not intent.metrics:
        return CellGroundingResult([], "E_NUMERICAL_EXTRACTION")

    grounded_cells = []
    symbol_counter = 0
    found_any_row = False

    # Chuẩn hóa danh sách metrics cần tìm
    # Nếu câu hỏi có tên tổ chức cụ thể (Visorutex,...) thêm vào entity_keywords để match theo row_label
    q_lower = raw_question.lower()
    entity_keywords = []
    
    # ─ Nhận diện tên tổ chức cố định ─
    _ENTITY_TOKENS = ["visorutex", "vinaconex", "vietjet", "sabeco"]
    for token in _ENTITY_TOKENS:
        if token in q_lower:
            entity_keywords.append(token)
    
    # ─ Nhận diện tên người trong câu hỏi (Họ Tên Người Cụ Thể) ─
    # Tìm chuỗi 2-3 từ viết hoa liên tiếp (dạng tên người Việt Nam)
    import re as _re
    _person_matches = _re.findall(
        r'\b([A-ZÁÀẢÃẠĂẮẶẰẲẴÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ][a-záàảãạăắặằẳẵâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]+'  
        r'(?:\s+[A-ZÁÀẢÃẠĂẮẶẰẲẴÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ][a-záàảãạăắặằẳẵâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]+){1,3}'  
        r')\b',
        raw_question
    )
    # Chỉ lấy tên người (>= 2 từ), bỏ qua tên công ty/tổ chức phổ biến
    _SKIP_NAMES = {"Ngân hàng", "Công ty", "Tập đoàn", "CTCP", "TNHH", "Hội đồng"}
    for pname in _person_matches:
        words = pname.split()
        if 2 <= len(words) <= 4 and not any(s in pname for s in _SKIP_NAMES):
            entity_keywords.append(_normalize_text(pname))

    metrics_normalized = [_normalize_text(m) for m in intent.metrics]

    for target_metric in intent.metrics:
        target_norm = _normalize_text(target_metric)

        for table_id, df in dfs.items():
            if "row_label_full" in df.columns:
                row_col = "row_label_full"
            elif "row_label_raw" in df.columns:
                row_col = "row_label_raw"
            else:
                continue

            matches = []
            match_method = "fuzzy"

            for idx, label in df[row_col].items():
                label_norm = _normalize_text(str(label))

                # Exact Match sau khi chuẩn hóa
                if target_norm and (target_norm in label_norm or label_norm in target_norm):
                    score = 100
                    match_method = "exact_norm"
                else:
                    # Fuzzy Match kết hợp partial_ratio và token_sort_ratio
                    score_partial = fuzz.partial_ratio(target_norm, label_norm)
                    score_sort = fuzz.token_sort_ratio(target_norm, label_norm)
                    score = max(score_partial, score_sort)

                if score >= 75:
                    matches.append((score, idx))

            # Ngưỡng 75 để chấp nhận OCR noise
            # ─────────────────────────────────────────────────────────────────
            # Fallback: nếu không match được theo row, thử match theo tên ENTITY trong row_label
            # Ví dụ: Q20 hỏi về Visorutex → row_label chứa 'Visorutex'
            if not matches and entity_keywords:
                for idx, label in df[row_col].items():
                    label_norm = _normalize_text(str(label))
                    if any(ek in label_norm for ek in entity_keywords):
                        matches.append((80, idx))
                        match_method = "entity_match"
                        break
            # ─────────────────────────────────────────────────────────────────
            # Ưu tiên dòng "Cộng/Tổng cộng" hơn sub-items khi score bằng nhau.
            # Chỉ dùng các keyword rõ ràng là dòng tổng (tránh "Ban Tổng GĐ").
            _TOTAL_KEYWORDS = {"cộng", "tổng cộng", "total", "subtotal"}
            _question_asks_total = "tổng" in q_lower or "total" in q_lower
            def _sort_key(item, _df=df, _col=row_col):
                _score, _idx = item
                try:
                    _row_text = _normalize_text(str(_df.loc[_idx, _col]))
                except (KeyError, Exception):
                    _row_text = ""
                _is_explicit_total = any(kw in _row_text for kw in _TOTAL_KEYWORDS)
                # Dòng nan (không có nhãn) thường là dòng tổng không đánh nhãn
                _is_unlabeled = _row_text in ("", "nan", "none")
                _is_total = _is_explicit_total or (_question_asks_total and _is_unlabeled)
                return (_score, 1 if _is_total else 0)

            matches.sort(key=_sort_key, reverse=True)

            
            for score, best_match_idx in matches:
                row = df.loc[best_match_idx]
                has_extracted_any = False

                # Ground columns (years)
                years_to_find = intent.years if intent.years else []
                all_numeric_cols = [c for c in df.columns if c.startswith("numeric__")]
                if not years_to_find:
                    col_cands = all_numeric_cols
                else:
                    col_cands = [
                        c for c in all_numeric_cols
                        if any(str(y) in c for y in years_to_find)
                    ]
                    # BUG-FIX: Fallback khi bảng dùng "Năm nay"/"Năm trước" thay vì ghi năm cụ thể
                    # Phổ biến với báo cáo ngân hàng (SGB, BID, SHB...) — lấy TẤT CẢ numeric__ columns
                    if not col_cands:
                        col_cands = all_numeric_cols

                for col in col_cands:
                    raw_val = str(row[col])
                    if pd.isna(row[col]) or raw_val.strip() in ("", "nan", "None"):
                        continue

                    # BUG-002 FIX: Skip cell nếu không parse được — KHÔNG gán 0.0
                    parsed_val = None
                    try:
                        # Thử parse trực tiếp, sau đó thử bỏ dấu phẩy ngăn cách hàng nghìn
                        parsed_val = float(raw_val)
                    except ValueError:
                        try:
                            parsed_val = float(raw_val.replace(",", "").replace(" ", ""))
                        except ValueError:
                            try:
                                parsed_val = float(raw_val.strip().rstrip("%").replace(",", "").replace(" ", ""))
                            except ValueError:
                                pass

                    if parsed_val is None:
                        # Không parse được số → bỏ qua hoàn toàn, không thêm cell này
                        continue

                    # BUG-021 FIX: symbol_name gán ngay tại đây
                    grounded_cells.append(
                        GroundedCell(
                            table_id=table_id,
                            csv_path="",  # Sẽ được điền bởi evidence loader
                            page_number=0,
                            row_label=str(row[row_col]),
                            column_label=col,
                            raw_value=raw_val,
                            parsed_value=parsed_val,
                            unit=intent.unit_requested,
                            confidence=score / 100.0,
                            grounding_method=match_method,
                            error_type=None,
                            symbol_name=f"NUM_{symbol_counter}",
                        )
                    )
                    symbol_counter += 1
                    has_extracted_any = True
                
                # QUAN TRỌNG: Chỉ break khi đã lấy được số liệu thực sự.
                # Nếu dòng khớp text nhưng tất cả ô đều rỗng (section header),
                # tiếp tục tìm dòng tiếp theo trong danh sách matches.
                if has_extracted_any:
                    found_any_row = True
                    break
                # Nếu has_extracted_any = False → dòng này rỗng → vòng lặp tiếp tục


    # ─── Fallback #2: Column-Name Matching ─────────────────────────────────────
    # Khi metric trùng với TÊN CỘT (ví dụ 'Quyền biểu quyết' là cột trong bảng HHV)
    # thay vì tên hàng, lấy tất cả giá trị hợp lệ trong cột đó từ các dòng tổng hợp.
    if not found_any_row or not grounded_cells:
        for target_metric in intent.metrics:
            target_norm = _normalize_text(target_metric)
            for table_id, df in dfs.items():
                # Tìm cột khớp với metric
                matched_col = None
                for col in df.columns:
                    if not col.startswith("numeric__"):
                        continue
                    col_label_norm = _normalize_text(col.replace("numeric__", ""))
                    if fuzz.partial_ratio(target_norm, col_label_norm) >= 75 or fuzz.partial_ratio(col_label_norm, target_norm) >= 75:
                        matched_col = col
                        break

                if matched_col is None:
                    continue

                # Xác định row_col
                if "row_label_full" in df.columns:
                    row_col = "row_label_full"
                elif "row_label_raw" in df.columns:
                    row_col = "row_label_raw"
                else:
                    continue

                # Ưu tiên row "Cộng" (tổng), nếu không có thì lấy row cuối
                target_row_idx = None
                for idx, lbl in df[row_col].items():
                    if "cong" in _normalize_text(str(lbl)) or "tong" in _normalize_text(str(lbl)):
                        target_row_idx = idx
                if target_row_idx is None and not df.empty:
                    target_row_idx = df.index[-1]

                if target_row_idx is None:
                    continue

                row = df.loc[target_row_idx]
                raw_val = str(row[matched_col])
                if pd.isna(row[matched_col]) or raw_val.strip() in ("", "nan", "None"):
                    continue

                parsed_val = None
                try:
                    parsed_val = float(raw_val)
                except ValueError:
                    try:
                        parsed_val = float(raw_val.strip().rstrip("%").replace(",", ""))
                    except ValueError:
                        pass

                if parsed_val is not None:
                    found_any_row = True
                    grounded_cells.append(
                        GroundedCell(
                            table_id=table_id,
                            csv_path="",
                            page_number=0,
                            row_label=str(row[row_col]),
                            column_label=matched_col,
                            raw_value=raw_val,
                            parsed_value=parsed_val,
                            unit=intent.unit_requested,
                            confidence=0.8,
                            grounding_method="column_name_match",
                            error_type=None,
                            symbol_name=f"NUM_{symbol_counter}",
                        )
                    )
                    symbol_counter += 1

    if not found_any_row or not grounded_cells:
        # Fallback thông minh: Quét các ô số trong các dòng có từ khóa ngữ cảnh từ câu hỏi
        q_tokens = [t for t in _normalize_text(raw_question).split() if len(t) >= 3]
        for var_name, df in dfs.items():
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            table_id = getattr(df, "_table_id", var_name)
            for r_idx, row in df.iterrows():
                row_str = " ".join(str(val) for val in row.values)
                row_norm = _normalize_text(row_str)
                # Kiểm tra xem dòng có chứa từ khóa khớp với câu hỏi không
                if any(t in row_norm for t in q_tokens):
                    for col_name in df.columns:
                        val_str = str(row[col_name]).strip()
                        parsed_val = None
                        try:
                            parsed_val = parse_vn_number(val_str)
                        except Exception:
                            pass
                        if parsed_val is not None:
                            found_any_row = True
                            grounded_cells.append(
                                GroundedCell(
                                    table_id=table_id,
                                    csv_path="",
                                    page_number=0,
                                    row_label=str(row.iloc[0]) if len(row) > 0 else "",
                                    column_label=str(col_name),
                                    raw_value=val_str,
                                    parsed_value=parsed_val,
                                    unit=intent.unit_requested,
                                    confidence=0.6,
                                    grounding_method="fallback_keyword_scan",
                                    error_type=None,
                                    symbol_name=f"NUM_{symbol_counter}",
                                )
                            )
                            symbol_counter += 1
                            if len(grounded_cells) >= 30:
                                break
                    if len(grounded_cells) >= 30:
                        break

    if not found_any_row or not grounded_cells:
        return CellGroundingResult([], "E_NUMERICAL_EXTRACTION")

    return CellGroundingResult(grounded_cells, None)
