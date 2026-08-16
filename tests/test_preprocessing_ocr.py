"""tests/test_preprocessing_ocr.py — Unit tests for ocr.split_pages."""

import pytest
from financial_text_to_pandas.preprocessing.ocr import split_pages


def test_two_page_input():
    text = "===== PAGE 1 =====\nContent page 1\n===== PAGE 2 =====\nContent page 2"
    pages = split_pages(text)
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Content page 1" in pages[0].raw_text
    assert pages[1].page_number == 2
    assert "Content page 2" in pages[1].raw_text


def test_missing_marker_returns_page_1():
    text = "Just some text without page markers"
    pages = split_pages(text)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "Just some text" in pages[0].raw_text


def test_extra_whitespace_in_marker():
    text = "=====  PAGE  3  =====\nPage three content"
    pages = split_pages(text)
    assert len(pages) == 1
    assert pages[0].page_number == 3


def test_case_insensitive_marker():
    text = "===== page 1 =====\nLowercase marker content"
    pages = split_pages(text)
    assert len(pages) == 1
    assert pages[0].page_number == 1


def test_empty_input():
    pages = split_pages("")
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].raw_text == ""


def test_three_pages():
    text = (
        "===== PAGE 1 =====\nA\n"
        "===== PAGE 2 =====\nB\n"
        "===== PAGE 3 =====\nC"
    )
    pages = split_pages(text)
    assert len(pages) == 3
    assert [p.page_number for p in pages] == [1, 2, 3]
    assert [p.raw_text for p in pages] == ["A", "B", "C"]


def test_page_text_excludes_marker():
    text = "===== PAGE 5 =====\nActual content here"
    pages = split_pages(text)
    assert "PAGE 5" not in pages[0].raw_text
    assert "Actual content here" in pages[0].raw_text
