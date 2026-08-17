"""
tests/test_reasoning_intent.py — Tests for reasoning intent extraction.
"""

from financial_text_to_pandas.reasoning.intent import extract_intent

def test_extract_intent_lookup():
    intent = extract_intent("Doanh thu thuần của AAA năm 2023 là bao nhiêu?")
    assert intent.ticker == "AAA"
    assert intent.years == [2023]
    assert "doanh thu thuần" in intent.metrics[0]
    assert intent.operation == "lookup"

def test_extract_intent_difference():
    intent = extract_intent("Chênh lệch lợi nhuận của VNM giữa 2022 và 2023")
    assert intent.ticker == "VNM"
    assert intent.years == [2022, 2023]
    assert intent.operation == "difference"

def test_extract_intent_growth_rate():
    intent = extract_intent("Tăng trưởng tài sản của FPT")
    assert intent.ticker == "FPT"
    assert intent.operation == "growth_rate"

def test_extract_intent_unit():
    intent = extract_intent("Tổng nợ vay bằng triệu đồng")
    assert intent.unit_requested == "triệu đồng"
    assert intent.operation == "sum"
