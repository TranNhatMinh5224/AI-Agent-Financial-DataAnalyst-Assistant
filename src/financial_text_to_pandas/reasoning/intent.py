"""
intent.py — Extract intention from the user's question for Reasoning Phase.

Phase 3, Step 2.

BUG-006 FIX: Nâng cấp metric extraction từ heuristic 3-từ-cứng sang:
  1. Normalize câu hỏi bằng financial dictionary (LNST → lợi nhuận sau thuế).
  2. Match với bảng KNOWN_METRICS (ưu tiên chuỗi dài nhất trước).
  3. Fallback heuristic chỉ dùng khi không match được.

BUG-012 FIX: Thêm operation "sum", "count" vào danh sách xác định.
"""

from __future__ import annotations

import re
from typing import List, Optional

from financial_text_to_pandas.types import Intent
from financial_text_to_pandas.retrieval.query_hints import _TICKER_RE, _YEAR_RE, _REPORT_TYPES
from financial_text_to_pandas.retrieval.dictionary import normalize_query_language


# ── Bảng thuật ngữ tài chính chuẩn (canonical term → display name) ─────────
# Sắp xếp theo độ dài GIẢM DẦN để match chuỗi dài trước (doanh thu thuần > doanh thu).
# Key: chuỗi tìm kiếm sau khi normalize (không dấu cũng cần fallback)
_KNOWN_METRICS: dict[str, str] = {
    # ── Kết quả kinh doanh ───────────────────────────────────────────────────
    "doanh thu thuần":                          "doanh thu thuần",
    "doanh thu bán hàng và cung cấp dịch vụ":  "doanh thu thuần",
    "doanh thu":                                "doanh thu thuần",
    "lợi nhuận gộp về bán hàng và cung cấp dịch vụ": "lợi nhuận gộp",
    "lợi nhuận gộp":                            "lợi nhuận gộp",
    "lợi nhuận thuần từ hoạt động kinh doanh":  "lợi nhuận thuần kinh doanh",
    "lợi nhuận trước thuế thu nhập doanh nghiệp": "lợi nhuận trước thuế",
    "lợi nhuận trước thuế":                     "lợi nhuận trước thuế",
    "lợi nhuận sau thuế thu nhập doanh nghiệp": "lợi nhuận sau thuế",
    "lợi nhuận sau thuế":                       "lợi nhuận sau thuế",
    "chi phí bán hàng":                         "chi phí bán hàng",
    "chi phí quản lý doanh nghiệp":             "chi phí quản lý",
    "chi phí quản lý":                          "chi phí quản lý",
    "chi phí tài chính":                        "chi phí tài chính",
    "chi phí lãi vay":                          "chi phí lãi vay",
    "doanh thu tài chính":                      "doanh thu tài chính",
    # ── Bảng cân đối kế toán ────────────────────────────────────────────────
    "tổng tài sản":                             "tổng tài sản",
    "tổng nguồn vốn":                           "tổng nguồn vốn",
    "tài sản ngắn hạn":                         "tài sản ngắn hạn",
    "tài sản dài hạn":                          "tài sản dài hạn",
    "tài sản cố định":                          "tài sản cố định",
    "hàng tồn kho":                             "hàng tồn kho",
    "tiền và các khoản tương đương tiền":       "tiền và tương đương tiền",
    "tiền và tương đương tiền":                 "tiền và tương đương tiền",
    "tiền":                                     "tiền và tương đương tiền",
    "các khoản phải thu ngắn hạn":              "phải thu ngắn hạn",
    "phải thu ngắn hạn":                        "phải thu ngắn hạn",
    "phải thu khách hàng":                      "phải thu khách hàng",
    "vay và nợ thuê tài chính ngắn hạn":        "vay ngắn hạn",
    "vay ngắn hạn":                             "vay ngắn hạn",
    "vay và nợ thuê tài chính dài hạn":         "vay dài hạn",
    "vay dài hạn":                              "vay dài hạn",
    "nợ ngắn hạn":                              "nợ ngắn hạn",
    "nợ dài hạn":                               "nợ dài hạn",
    "nợ phải trả":                              "nợ phải trả",
    "vốn chủ sở hữu":                           "vốn chủ sở hữu",
    "vốn điều lệ":                              "vốn điều lệ",
    "lợi nhuận sau thuế chưa phân phối":        "lợi nhuận chưa phân phối",
    "lợi nhuận chưa phân phối":                 "lợi nhuận chưa phân phối",
    # ── Lưu chuyển tiền tệ ─────────────────────────────────────────────────
    "lưu chuyển tiền thuần từ hoạt động kinh doanh": "tiền thuần kinh doanh",
    "lưu chuyển tiền thuần từ hoạt động đầu tư":      "tiền thuần đầu tư",
    "lưu chuyển tiền thuần từ hoạt động tài chính":   "tiền thuần tài chính",
    "lưu chuyển tiền thuần trong kỳ":                 "lưu chuyển tiền thuần",
}

# ── Mapping operation keywords ───────────────────────────────────────────────
_OPERATION_PATTERNS: list[tuple[str, str]] = [
    # (keyword, operation) — thứ tự quan trọng: cụ thể trước
    ("tăng trưởng",                 "growth_rate"),
    ("tăng bao nhiêu phần trăm",    "growth_rate"),
    ("tăng bao nhiêu %",            "growth_rate"),
    ("tỷ lệ tăng trưởng",           "growth_rate"),
    ("biến động",                   "growth_rate"),
    ("chênh lệch",                  "difference"),
    ("thay đổi bao nhiêu",          "difference"),
    ("tăng bao nhiêu",              "difference"),
    ("giảm bao nhiêu",              "difference"),
    ("so với",                      "difference"),
    ("tỷ lệ",                       "ratio"),
    ("biên lợi nhuận",              "ratio"),
    ("biên",                        "ratio"),
    ("trung bình",                  "mean"),
    ("trung vị",                    "median"),
    ("tổng cộng",                   "sum"),
    ("tổng của",                    "sum"),
    ("tổng",                        "sum"),
    ("đếm",                         "count"),
    ("bao nhiêu công ty",           "count"),
]


def _extract_metrics_from_question(q_lower: str) -> List[str]:
    """Match câu hỏi với bảng thuật ngữ tài chính chuẩn.
    
    Ưu tiên chuỗi dài nhất trước để tránh match mơ hồ.
    """
    metrics: List[str] = []
    # Sắp xếp theo độ dài key GIẢM DẦN (dài nhất → cụ thể nhất)
    for term, canonical in sorted(_KNOWN_METRICS.items(), key=lambda x: len(x[0]), reverse=True):
        if term in q_lower:
            if canonical not in metrics:
                metrics.append(canonical)
            # Xóa chuỗi đã match để tránh double-match với sub-string
            q_lower = q_lower.replace(term, " ", 1)
    return metrics


def _extract_operation(q_lower: str) -> str:
    """Xác định loại phép tính từ câu hỏi."""
    for keyword, operation in _OPERATION_PATTERNS:
        if keyword in q_lower:
            return operation
    return "lookup"


def extract_intent(question: str) -> Intent:
    """Parse the user's question to extract the reasoning intent.

    Args:
        question: The natural language question.

    Returns:
        Intent dataclass.
    """
    # ── Bước 0: Normalize câu hỏi (LNST → lợi nhuận sau thuế) ───────────────
    normalized_q = normalize_query_language(question)
    q_lower = normalized_q.lower()

    # ── Ticker ──────────────────────────────────────────────────────────────
    tickers = _TICKER_RE.findall(question)
    ticker = tickers[0] if tickers else None

    # ── Years ────────────────────────────────────────────────────────────────
    years_str = _YEAR_RE.findall(question)
    years = sorted(list(set(int(y) for y in years_str)))

    # ── Report type ──────────────────────────────────────────────────────────
    report_type = "unknown"
    for kw, rt in _REPORT_TYPES.items():
        if kw in q_lower:
            report_type = rt
            break

    # ── Operation ────────────────────────────────────────────────────────────
    operation = _extract_operation(q_lower)

    # ── Metrics (BUG-006 FIX) ────────────────────────────────────────────────
    metrics = _extract_metrics_from_question(q_lower)

    if not metrics:
        # Heuristic fallback: lấy chuỗi danh từ trước "của" hoặc 5 từ đầu
        if "của" in q_lower:
            prefix = q_lower.split("của")[0].strip()
            words = prefix.split()
            # Lấy tối đa 5 từ cuối trước "của" để bao phủ tên chỉ số dài
            fallback = " ".join(words[-5:]) if words else ""
        else:
            words = q_lower.split()
            # Bỏ qua từ đặt câu hỏi ở cuối (bao nhiêu, là gì, ...)
            _QUESTION_WORDS = {"bao nhiêu", "là", "gì", "như thế nào", "năm", "trong"}
            clean_words = [w for w in words if w not in _QUESTION_WORDS]
            fallback = " ".join(clean_words[:6])
        if fallback:
            metrics = [fallback]

    # ── Unit ─────────────────────────────────────────────────────────────────
    unit_requested: Optional[str] = None
    _UNITS = ["triệu đồng", "tỷ đồng", "tỷ", "triệu", "vnđ", "vnd", "usd", "%"]
    for u in _UNITS:
        if u in q_lower:
            unit_requested = u
            break

    return Intent(
        ticker=ticker,
        company_name=None,
        years=years,
        report_type=report_type,
        metrics=metrics,
        unit_requested=unit_requested,
        operation=operation,
    )
