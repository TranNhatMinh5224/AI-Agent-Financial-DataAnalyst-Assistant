"""
test_submission.py — Unit tests for contest submission generator and validator.
"""

import json
import zipfile
from pathlib import Path
import pytest

from financial_text_to_pandas.submission import (
    create_submission_item,
    export_submission_zip,
    validate_submission_zip,
)
from financial_text_to_pandas.types import SubmissionItem, EvidenceItem


def test_create_submission_item():
    """Test building a SubmissionItem with clean document IDs and line numbers."""
    item = create_submission_item(
        question_id=1,
        question_text="Doanh thu thuần VNM năm 2023?",
        answer=63075000000.0,
        report_ids=["AAA_financial_statements_2015_consolidated.txt"],
        table_refs=[("AAA_financial_statements_2015_consolidated", 350)],
        evidence_tables=[("df1", "AAA_financial_statements_2015_consolidated", "AAA_2015_table_1.csv")],
        pandas_query="df1['net_revenue'].values[0]",
    )

    assert item.id == 1
    assert item.question == "Doanh thu thuần VNM năm 2023?"
    assert item.answer == 63075000000.0
    assert item.relevant_docs == ["AAA_financial_statements_2015_consolidated"]
    assert item.relevant_tables == ["AAA_financial_statements_2015_consolidated|350"]
    assert len(item.evidence) == 1
    assert item.evidence[0].variable == "df1"
    assert item.evidence[0].csv_path == "data/AAA_2015_table_1.csv"
    assert item.pandas_query == "df1['net_revenue'].values[0]"


def test_export_and_validate_submission_zip(tmp_path: Path):
    """Test generating a submission ZIP and validating it."""
    # Create sample CSV source file
    csv_dir = tmp_path / "source_csvs"
    csv_dir.mkdir()
    sample_csv = csv_dir / "AAA_2015_table_1.csv"
    sample_csv.write_text("raw_label,numeric__net_revenue\nDoanh thu,63075000000\n", encoding="utf-8")

    item = create_submission_item(
        question_id=1,
        question_text="Doanh thu thuần VNM năm 2023?",
        answer=63075000000.0,
        report_ids=["AAA_financial_statements_2015_consolidated"],
        table_refs=[("AAA_financial_statements_2015_consolidated", 350)],
        evidence_tables=[("df1", "AAA_financial_statements_2015_consolidated", "AAA_2015_table_1.csv")],
        pandas_query="df1['net_revenue'].values[0]",
    )

    table_map = {"AAA_2015_table_1.csv": sample_csv}
    zip_out = tmp_path / "submission.zip"

    res_path = export_submission_zip([item], table_map, zip_out)
    assert res_path.exists()

    # Validate generated ZIP
    is_valid, errors = validate_submission_zip(res_path)
    assert is_valid, f"Validation failed with errors: {errors}"
    assert len(errors) == 0

    # Inspect ZIP structure
    with zipfile.ZipFile(res_path, "r") as zf:
        names = zf.namelist()
        assert "submission.json" in names
        assert "data/AAA_2015_table_1.csv" in names

        # Read JSON
        json_content = json.loads(zf.read("submission.json").decode("utf-8"))
        assert len(json_content) == 1
        assert json_content[0]["id"] == 1
        assert json_content[0]["relevant_tables"] == ["AAA_financial_statements_2015_consolidated|350"]


def test_validation_catches_invalid_zip(tmp_path: Path):
    """Test validator catches bad zip files with wrong layout."""
    bad_zip = tmp_path / "bad_submission.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        # Missing submission.json, puts files in nested folder
        zf.writestr("parent_folder/submission.json", "[]")

    is_valid, errors = validate_submission_zip(bad_zip)
    assert not is_valid
    assert any("submission.json" in err for err in errors)
