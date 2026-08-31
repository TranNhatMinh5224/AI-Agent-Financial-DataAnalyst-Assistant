"""
query_hints.py — Extract metadata hints from natural language questions.

Phase 2, Step 2 & 3.
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

import pandas as pd

from financial_text_to_pandas.types import QueryHints
from financial_text_to_pandas.retrieval.dictionary import normalize_query_language

# ── Keywords & Patterns ───────────────────────────────────────────────────────

# Ticker pattern: 3 alphanumeric characters
_TICKER_RE = re.compile(r"\b[A-Za-z0-9]{3}\b")

# Danh sách 100 mã cổ phiếu chính thức trong cuộc thi ViFinQA
_KNOWN_TICKERS = {
    'AAA', 'ABB', 'ACB', 'ACV', 'ASM', 'BAB', 'BAF', 'BID', 'BSR', 'BVH', 
    'CEO', 'CRE', 'CTG', 'DBC', 'DCM', 'DIG', 'DLG', 'DNH', 'DPM', 'DTK', 
    'DXG', 'DXS', 'EIB', 'EVF', 'FIT', 'FOX', 'FPT', 'FTS', 'GAS', 'GEE', 
    'GEG', 'GEX', 'GVR', 'HAG', 'HBC', 'HDB', 'HDG', 'HHS', 'HHV', 'HND', 
    'HNG', 'HPG', 'HPX', 'HSG', 'HT1', 'HUT', 'IJC', 'KBC', 'KHG', 'KLB', 
    'MBB', 'MBS', 'MCH', 'MML', 'MPC', 'MSB', 'MSN', 'MSR', 'MWG', 'NAB', 
    'NKG', 'NLG', 'NVB', 'NVL', 'OCB', 'OGC', 'PC1', 'PDR', 'PLX', 'PNJ', 
    'POW', 'PRT', 'PVT', 'QNS', 'SAB', 'SAM', 'SCR', 'SGB', 'SHB', 'SJG', 
    'SNZ', 'SSB', 'SSH', 'SSI', 'STB', 'TTF', 'VAB', 'VCB', 'VGC', 'VGT', 
    'VIB', 'VIC', 'VIF', 'VJC', 'VNM', 'VPB', 'VPI', 'VRE', 'VSC', 'VSF'
}

# Year pattern: 4 digits starting with 20 (e.g. 2015..2024)
_YEAR_RE = re.compile(r"\b(20[0-3]\d)\b")

_REPORT_TYPES = {
    "hợp nhất": "consolidated",
    "hop nhat": "consolidated",
    "riêng lẻ": "separate",
    "rieng le": "separate",
    "giải trình": "explanation",
    "giai trinh": "explanation",
    "công ty mẹ": "separate",
    "cong ty me": "separate",
}

# ── Bảng tên công ty → ticker (cho câu hỏi dùng tên đầy đủ thay vì mã CK) ──────────────────
_COMPANY_NAME_TO_TICKER: dict[str, str] = {
    # Câu hỏi sử dụng tên đầy đủ không có mã CK trong ngoặc
    "sài gòn tài lộc":           "SGB",
    "ngoan mục tai loc":           "SGB",
    "tmcp sài gòn tài lộc":       "SGB",
    "sunshine homes":               "SSH",
    "sunshine home":                "SSH",
    "phát triển sunshine":         "SSH",
    "bia rượu nước giải khát sài gòn": "SAB",
    "sabeco":                       "SAB",
    "sài gòn — hà nội":           "SHB",
    "sài gòn hà nội":             "SHB",
    "tmcp sài gòn hà nội":        "SHB",
    "đầu tư và phát triển việt nam": "BID",
    "tmcp đầu tư và phát triển":  "BID",
    "bidv":                         "BID",
    "đầu tư hạ tầng giao thông đèo cả": "HHV",
    "đèo cả":                      "HHV",
    "cao su việt nam":             "GVR",
    "visorutex":                    "GVR",
    "cao su miền nam":             "CSM",
    "việt jet":                   "VJC",
    "vietjet":                      "VJC",
    "hàng không vietjet":          "VJC",
    "hàng không việt jet":         "VJC",
    "á châu":                      "ACB",
    "tmcp á châu":                 "ACB",
    "đầu tư và phát triển hà nội": "HDG",
    "chường khoán fpt":            "FTS",
    "chứng khoán fpt":            "FTS",
    "fpt securities":               "FTS",
    "miền nam vàng":               "PNJ",
    "phú nhuận":                    "PNJ",
    "chứng khoán mb":              "MBS",
    "miền bắc":                   "MBS",
    "bài xuất khẩu":              "VGT",
    "dệt may việt nam":           "VGT",
    "vinatex":                      "VGT",
    "minh phú":                    "MPC",
    "mpc":                         "MPC",
    "điện lực gelex":              "GEE",
    "gelex điện":                  "GEE",
    "gee":                         "GEE",
    "tập đoàn gelex":              "GEX",
    "gelex":                        "GEX",
}


def _lookup_ticker_by_company_name(question: str) -> Optional[str]:
    """Tra tên công ty đầy đủ trong câu hỏi ra mã ticker tương ứng."""
    q = question.lower()
    # Sắp xếp theo độ dài giảm dần để ưu tiên tên càng cụ thể càng được match trước
    for name, ticker in sorted(_COMPANY_NAME_TO_TICKER.items(), key=lambda x: len(x[0]), reverse=True):
        if name in q:
            return ticker
    return None


_STATEMENT_TYPES = {
    "cân đối kế toán": "balance_sheet",
    "can doi ke toan": "balance_sheet",
    "kết quả hoạt động kinh doanh": "income_statement",
    "ket qua kinh doanh": "income_statement",
    "lưu chuyển tiền tệ": "cash_flow",
    "luu chuyen tien": "cash_flow",
    "thuyết minh": "notes",
    "thuyet minh": "notes",
}

_UNITS = ["triệu đồng", "tỷ đồng", "tỷ", "triệu", "vnđ", "vnd", "usd", "%"]

def extract_query_hints(question: str) -> QueryHints:
    """Extract metadata filtering hints from a natural language question.
    
    Args:
        question: The user's query.
        
    Returns:
        QueryHints dataclass containing extracted metadata.
    """
    normalized_q = normalize_query_language(question)
    q_lower = normalized_q.lower()
    
    # 1. Tickers: Quét toàn bộ danh sách mã CK chuẩn có mặt trong câu hỏi
    words = re.findall(r"\b[A-Za-z0-9]+\b", question)
    found_tickers: list[str] = []
    for w in words:
        w_up = w.upper()
        if w_up in _KNOWN_TICKERS and w_up not in found_tickers:
            found_tickers.append(w_up)
            
    if not found_tickers:
        matched = _TICKER_RE.findall(question)
        for m in matched:
            m_up = m.upper()
            if m_up not in found_tickers:
                found_tickers.append(m_up)
                
    if not found_tickers:
        named_ticker = _lookup_ticker_by_company_name(question)
        if named_ticker:
            found_tickers = [named_ticker]
            
    primary_ticker = found_tickers[0] if found_tickers else None
    is_multi_ticker = len(found_tickers) > 1
    
    # 2. Years
    years_str = _YEAR_RE.findall(question)
    years = sorted(list(set(int(y) for y in years_str)))
    
    # 3. Report type
    report_type = None
    for kw, rt in _REPORT_TYPES.items():
        if kw in q_lower:
            report_type = rt
            break
            
    # 4. Statement type
    statement_type = None
    for kw, st in _STATEMENT_TYPES.items():
        if kw in q_lower:
            statement_type = st
            break
            
    # 5. Unit
    unit_requested = None
    for u in _UNITS:
        if u in q_lower:
            unit_requested = u
            break
            
    # 6. Metric terms
    metric_terms = []
    if "của" in q_lower:
        prefix = q_lower.split("của")[0].strip()
        words = prefix.split()
        if len(words) > 0:
            metric_terms = [" ".join(words[-3:])]
    
    # Confidence
    confidence = 0.0
    if found_tickers and years:
        confidence = 0.9
    elif found_tickers or years:
        confidence = 0.5
        
    return QueryHints(
        query_id=str(uuid.uuid4()),
        question=question,
        ticker=primary_ticker,
        tickers=found_tickers,
        company_name=None,
        years=years,
        report_type=report_type,
        statement_type=statement_type,
        metric_terms=metric_terms,
        unit_requested=unit_requested,
        operation=None,
        confidence=confidence,
        is_industry_comparison=is_multi_ticker
    )


def filter_by_metadata(corpus: pd.DataFrame, hints: QueryHints) -> pd.DataFrame:
    """Filter the table corpus based on high-confidence query hints.
    
    Args:
        corpus: The full table_corpus.csv DataFrame.
        hints: The extracted QueryHints.
        
    Returns:
        Filtered DataFrame.
    """
    filtered = corpus.copy()
    
    if hints.confidence >= 0.5:
        # 1. Filter by multiple tickers (e.g. Industry Comparison) or single ticker
        if hints.tickers:
            t_set = {t.upper() for t in hints.tickers}
            filtered = filtered[filtered["ticker"].str.upper().isin(t_set)]
        elif hints.ticker:
            filtered = filtered[filtered["ticker"].str.upper() == hints.ticker.upper()]
            
        # 2. Filter by year if explicit
        if hints.years:
            filtered = filtered[filtered["year"].astype(str).isin([str(y) for y in hints.years])]
            
        # 3. Filter by report type if explicit
        if hints.report_type and not hints.is_industry_comparison:
            filtered = filtered[filtered["report_type"] == hints.report_type]
            
    if filtered.empty and not corpus.empty:
        return corpus
        
    return filtered
