"""tests/test_preprocessing_pipeline.py — Integration tests for pipeline."""

import pytest
import tempfile
import pandas as pd
from pathlib import Path

from financial_text_to_pandas.config import RunConfig
from financial_text_to_pandas.preprocessing.pipeline import (
    discover_report_files,
    process_report,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_sample_config(input_root: Path, output_root: Path) -> RunConfig:
    return RunConfig(
        run_mode="sample",
        input_root=input_root,
        output_root=output_root,
        sample_tickers=["AAA"],
        sample_limit_reports=1,
        full_run_confirmed=False,
        resume=False,
    )


SAMPLE_OCR = """===== PAGE 1 =====
Công ty CP ABC

===== PAGE 2 =====
Bảng cân đối kế toán
Đơn vị: triệu đồng

<table>
<tr><th>Chỉ tiêu</th><th>2023</th><th>2022</th></tr>
<tr><td>I. Tài sản ngắn hạn</td><td></td><td></td></tr>
<tr><td>1. Tiền</td><td>15.230</td><td>12.100</td></tr>
<tr><td>2. Phải thu</td><td>8.500</td><td>7.200</td></tr>
<tr><td>Tổng cộng tài sản</td><td>50.000</td><td>45.000</td></tr>
</table>

===== PAGE 3 =====
Ghi chú thuyết minh
"""


def _create_fake_report(base: Path, ticker: str = "AAA", year: int = 2023) -> Path:
    """Create a fake OCR TXT report directory structure."""
    doc_dir = base / ticker / str(year) / f"{ticker}_financial_statements_{year}_consolidated"
    doc_dir.mkdir(parents=True, exist_ok=True)
    txt_path = doc_dir / f"{ticker}_financial_statements_{year}_consolidated_extracted.txt"
    txt_path.write_text(SAMPLE_OCR, encoding="utf-8")
    return txt_path


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_discover_finds_one_file():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        _create_fake_report(input_root)

        cfg = make_sample_config(input_root, tmp_path / "output")
        files = discover_report_files(cfg)
        assert len(files) == 1
        assert files[0].name.endswith(".txt")


def test_process_report_creates_csv():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        assert result.success
        assert len(result.clean_tables) >= 1

        # Each CSV must be reopenable with pandas
        for ct in result.clean_tables:
            abs_csv = output_root / ct.csv_path
            assert abs_csv.exists(), f"CSV not found: {abs_csv}"
            df = pd.read_csv(abs_csv, encoding="utf-8-sig")
            assert isinstance(df, pd.DataFrame)


def test_process_report_has_row_label_columns():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        for ct in result.clean_tables:
            assert "row_label_raw" in ct.dataframe.columns
            assert "row_label_full" in ct.dataframe.columns


def test_process_report_has_numeric_columns():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        for ct in result.clean_tables:
            numeric_cols = [c for c in ct.dataframe.columns if c.startswith("numeric__")]
            assert len(numeric_cols) >= 1, "Expected at least one numeric__ column"


def test_process_report_creates_linked_text():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        assert result.linked_text_path is not None
        linked = result.linked_text_path.read_text(encoding="utf-8")
        assert "TABLE_REF" in linked
        assert "<table>" not in linked


def test_process_report_audit_never_empty():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        # Audit must record every table (success or fail)
        assert len(result.audit_rows) >= 1
        for row in result.audit_rows:
            assert row.status in {"success", "failed", "needs_review"}


def test_metadata_report_populated():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        input_root = tmp_path / "financial_statements"
        output_root = tmp_path / "output"
        txt_path = _create_fake_report(input_root)

        cfg = make_sample_config(input_root, output_root)
        result = process_report(txt_path, cfg, existing_audit={})

        assert result.report_metadata.ticker == "AAA"
        assert result.report_metadata.year == 2023
        assert result.report_metadata.report_type == "consolidated"
