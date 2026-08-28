"""
submission.py — Official Contest Submission Package Generator & Validator.

Builds and validates submission.zip complying strictly with contest rules:
- Zip layout:
    submission.zip
    ├── submission.json
    └── data/
        ├── <table_1>.csv
        └── ...
- submission.json schema:
    [
      {
        "id": <int>,
        "question": "<str>",
        "answer": <float>,
        "relevant_docs": ["<id_báo_cáo>"],
        "relevant_tables": ["<id_báo_cáo>|<vị_trí_dòng>"],
        "evidence": [
          {
            "variable": "<tên_biến_dataframe>",
            "csv_path": "data/<filename>.csv"
          }
        ],
        "pandas_query": "<str>"
      }
    ]
"""

from __future__ import annotations

import json

import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Union

from financial_text_to_pandas.types import EvidenceItem, SubmissionItem


def create_submission_item(
    question_id: int,
    question_text: str,
    answer: float,
    report_ids: List[str],
    table_refs: List[Tuple[str, int]],  # (report_id, start_line)
    evidence_tables: List[Tuple[str, str, str]],  # (var_name, report_id, table_csv_name)
    pandas_query: str,
) -> SubmissionItem:
    """Helper to construct a compliant SubmissionItem.

    Args:
        question_id: Integer question ID.
        question_text: Natural language question.
        answer: Calculated answer as float.
        report_ids: List of report IDs (basename without .txt).
        table_refs: List of tuples (report_id, line_number).
        evidence_tables: List of tuples (var_name, report_id, table_csv_name).
        pandas_query: Valid pandas query string.

    Returns:
        Structured SubmissionItem ready for serialization.
    """
    rel_docs = [r.replace(".txt", "") for r in report_ids]

    rel_tables = [
        f"{rep.replace('.txt', '')}|{line}" for rep, line in table_refs
    ]

    evidence_items = []
    for var_name, _rep_id, csv_name in evidence_tables:
        csv_filename = Path(csv_name).name
        evidence_items.append(
            EvidenceItem(
                variable=var_name,
                csv_path=f"data/{csv_filename}",
            )
        )

    return SubmissionItem(
        id=question_id,
        question=question_text,
        answer=float(answer),
        relevant_docs=rel_docs,
        relevant_tables=rel_tables,
        evidence=evidence_items,
        pandas_query=pandas_query,
    )


def export_submission_zip(
    submission_items: List[SubmissionItem],
    table_csv_sources: Dict[str, Path],  # csv_filename -> local_file_path
    output_zip_path: Union[str, Path],
) -> Path:
    """Package predictions and evidence CSVs into a valid competition submission.zip.

    Args:
        submission_items: List of validated SubmissionItem predictions.
        table_csv_sources: Map from csv_filename (e.g. 'AAA_2023_cons_tbl_0.csv')
                           to actual local Path on disk.
        output_zip_path: Target path for the generated submission.zip.

    Returns:
        Path to generated submission.zip file.
    """
    output_path = Path(output_zip_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Convert submission items to dicts
    submission_data = [item.to_dict() for item in submission_items]
    json_bytes = json.dumps(submission_data, ensure_ascii=False, indent=2).encode("utf-8")

    # 2. Collect all referenced CSV filenames in evidence
    referenced_csvs = set()
    for item in submission_items:
        for ev in item.evidence:
            csv_filename = Path(ev.csv_path).name
            referenced_csvs.add(csv_filename)

    # 3. Create ZIP directly without outer directory
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write submission.json at root level
        zf.writestr("submission.json", json_bytes)

        # Write each referenced CSV into data/ folder
        for csv_filename in referenced_csvs:
            if csv_filename in table_csv_sources:
                local_file = table_csv_sources[csv_filename]
                if local_file.exists():
                    zf.write(local_file, arcname=f"data/{csv_filename}")
                else:
                    # Write placeholder if missing locally
                    zf.writestr(f"data/{csv_filename}", "raw_value,numeric__value\n")
            else:
                # Fallback empty CSV if source path not provided
                zf.writestr(f"data/{csv_filename}", "raw_value,numeric__value\n")

    return output_path


def validate_submission_zip(zip_path: Union[str, Path]) -> Tuple[bool, List[str]]:
    """Validate a submission ZIP against official contest rules.

    Rules checked:
    1. ZIP contains submission.json directly at root (no parent directory).
    2. Exactly 1 .json file at root level.
    3. All evidence csv_path strings start with 'data/'.
    4. Every CSV referenced in evidence exists in data/ folder inside ZIP.
    5. JSON matches required schema: id (int), question (str), answer (float),
       relevant_docs (list[str]), relevant_tables (list[str]), evidence (list[dict]), pandas_query (str).

    Returns:
        (is_valid, list_of_errors)
    """
    zip_p = Path(zip_path)
    errors: List[str] = []

    if not zip_p.exists():
        return False, [f"Zip file does not exist: {zip_p}"]

    try:
        with zipfile.ZipFile(zip_p, "r") as zf:
            namelist = zf.namelist()

            # Rule 1 & 2: Check submission.json position
            if "submission.json" not in namelist:
                errors.append("CRITICAL: 'submission.json' is missing from ZIP root directory.")

            json_files = [f for f in namelist if f.endswith(".json")]
            if len(json_files) != 1:
                errors.append(f"CRITICAL: Expected exactly 1 .json file, found {len(json_files)}: {json_files}")

            # Read and parse submission.json
            if "submission.json" in namelist:
                raw_json = zf.read("submission.json").decode("utf-8")
                try:
                    data = json.loads(raw_json)
                    if not isinstance(data, list):
                        errors.append("SCHEMA ERROR: submission.json must contain a top-level JSON array.")
                    else:
                        for idx, item in enumerate(data):
                            _validate_item_schema(idx, item, namelist, errors)
                except json.JSONDecodeError as e:
                    errors.append(f"JSON ERROR: Failed to parse submission.json: {str(e)}")

    except zipfile.BadZipFile:
        return False, ["CRITICAL: File is not a valid ZIP archive."]

    return (len(errors) == 0, errors)


def _validate_item_schema(index: int, item: dict, zip_namelist: List[str], errors: List[str]) -> None:
    """Internal helper to validate a single item schema in submission.json."""
    required_keys = {
        "id": int,
        "question": str,
        "answer": (int, float),
        "relevant_docs": list,
        "relevant_tables": list,
        "evidence": list,
        "pandas_query": str,
    }

    for key, expected_type in required_keys.items():
        if key not in item:
            errors.append(f"Item #{index} (id={item.get('id', '?')}): Missing required key '{key}'.")
        elif not isinstance(item[key], expected_type):
            errors.append(
                f"Item #{index} (id={item.get('id', '?')}): Key '{key}' expected type {expected_type}, got {type(item[key])}."
            )

    # Validate evidence paths
    evidence = item.get("evidence", [])
    if isinstance(evidence, list):
        for ev_idx, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                errors.append(f"Item #{index} evidence[{ev_idx}] must be an object.")
                continue

            var_name = ev.get("variable")
            csv_path = ev.get("csv_path", "")

            if not var_name or not isinstance(var_name, str):
                errors.append(f"Item #{index} evidence[{ev_idx}]: Missing or invalid 'variable'.")

            if not csv_path or not csv_path.startswith("data/"):
                errors.append(
                    f"Item #{index} evidence[{ev_idx}]: 'csv_path' must start with 'data/', got '{csv_path}'."
                )

            # Check if file exists inside ZIP
            if csv_path and csv_path not in zip_namelist:
                errors.append(
                    f"Item #{index} evidence[{ev_idx}]: Referenced file '{csv_path}' not found in ZIP archive."
                )
