"""
intent.py — Extract intention from the user's question for Reasoning Phase.

Phase 3, Step 2.
"""

from __future__ import annotations

import re
from typing import Optional

from financial_text_to_pandas.types import Intent
from financial_text_to_pandas.retrieval.query_hints import _TICKER_RE, _YEAR_RE, _REPORT_TYPES

def extract_intent(question: str) -> Intent:
    """Parse the user's question to extract the reasoning intent.
    
    Args:
        question: The natural language question.
        
    Returns:
        Intent dataclass.
    """
    q_lower = question.lower()
    
    # Ticker
    tickers = _TICKER_RE.findall(question)
    ticker = tickers[0] if tickers else None
    
    # Years
    years_str = _YEAR_RE.findall(question)
    years = sorted(list(set(int(y) for y in years_str)))
    
    # Report type
    report_type = "unknown"
    for kw, rt in _REPORT_TYPES.items():
        if kw in q_lower:
            report_type = rt
            break
            
    # Metrics - A basic heuristic extracting nouns/phrases
    metrics = []
    # E.g. "Doanh thu thuần của AAA là bao nhiêu"
    if "của" in q_lower:
        prefix = q_lower.split("của")[0].strip()
        words = prefix.split()
        if len(words) > 0:
            metrics = [" ".join(words[-3:])]
    else:
        # Just grab the first few words as a naive metric
        words = q_lower.split()
        if len(words) >= 3:
            metrics = [" ".join(words[:3])]
            
    # Unit requested
    unit_requested = None
    units = ["triệu đồng", "tỷ đồng", "tỷ", "triệu", "vnđ", "vnd", "usd", "%"]
    for u in units:
        if u in q_lower:
            unit_requested = u
            break
            
    # Operation type
    operation = "lookup"
    if "tăng trưởng" in q_lower or "tăng bao nhiêu phần trăm" in q_lower:
        operation = "growth_rate"
    elif "chênh lệch" in q_lower or "thay đổi bao nhiêu" in q_lower or "tăng bao nhiêu" in q_lower:
        operation = "difference"
    elif "tỷ lệ" in q_lower or "biên" in q_lower:
        operation = "ratio"
    elif "trung bình" in q_lower:
        operation = "mean"
    elif "trung vị" in q_lower:
        operation = "median"
    elif "tổng" in q_lower:
        operation = "sum"
        
    return Intent(
        ticker=ticker,
        company_name=None,
        years=years,
        report_type=report_type,
        metrics=metrics,
        unit_requested=unit_requested,
        operation=operation
    )
