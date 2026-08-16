"""tests/test_number_parser.py — Unit tests for Vietnamese number parser."""

import pytest
from financial_text_to_pandas.preprocessing.number_parser import parse_vn_number


def test_thousands_dot_separator():
    pn = parse_vn_number("15.230.000")
    assert pn.parsed_value == 15230000.0
    assert pn.parse_status == "ok"


def test_decimal_comma():
    pn = parse_vn_number("12,5")
    assert pn.parsed_value == 12.5
    assert pn.parse_status == "ok"
    assert pn.number_type == "decimal"


def test_percent():
    pn = parse_vn_number("12,5%")
    assert abs(pn.parsed_value - 0.125) < 1e-9
    assert pn.number_type == "percent"
    assert pn.unit_hint == "%"
    assert pn.parse_status == "ok"


def test_parentheses_negative():
    pn = parse_vn_number("(500.000)")
    assert pn.parsed_value == -500000.0
    assert pn.parse_status == "ok"


def test_minus_prefix():
    pn = parse_vn_number("-500.000")
    assert pn.parsed_value == -500000.0
    assert pn.parse_status == "ok"


def test_dash_placeholder():
    for dash in ["-", "–", "—"]:
        pn = parse_vn_number(dash)
        assert pn.parsed_value is None
        assert pn.parse_status == "empty"


def test_empty_string():
    pn = parse_vn_number("")
    assert pn.parsed_value is None
    assert pn.parse_status == "empty"


def test_date_string():
    pn = parse_vn_number("31/12/2024")
    assert pn.parsed_value is None
    assert pn.parse_status == "not_number"


def test_text_string():
    pn = parse_vn_number("Tổng cộng")
    assert pn.parsed_value is None
    assert pn.parse_status == "not_number"


def test_plain_integer():
    pn = parse_vn_number("1000")
    assert pn.parsed_value == 1000.0
    assert pn.parse_status == "ok"


def test_mixed_thousands_decimal():
    pn = parse_vn_number("1.234,56")
    assert abs(pn.parsed_value - 1234.56) < 1e-9
    assert pn.parse_status == "ok"


def test_zero():
    pn = parse_vn_number("0")
    assert pn.parsed_value == 0.0
    assert pn.parse_status == "ok"


def test_large_number():
    pn = parse_vn_number("1.234.567.890")
    assert pn.parsed_value == 1234567890.0
    assert pn.parse_status == "ok"
