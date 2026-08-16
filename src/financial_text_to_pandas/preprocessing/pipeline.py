"""
pipeline.py — Phase 1 preprocessing pipeline CLI.

Usage:
    python -m financial_text_to_pandas.preprocessing.pipeline \\
        --config config/run_profile.yaml

Supports:
    --dry-run       List planned input files without writing any output.
    --config PATH   Path to run_profile.yaml (default: config/run_profile.yaml).

No LLM, no retrieval, no embedding, no database.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd
from bs4 import BeautifulSoup

from financial_text_to_pandas.config import RunConfig, load_config
from financial_text_to_pandas.preprocessing.audit import load_audit, write_audit
from financial_text_to_pandas.preprocessing.metadata import (
    infer_report_metadata,
    lookup_company_name,
    write_report_metadata,
    write_table_metadata,
)
from financial_text_to_pandas.preprocessing.ocr import split_pages
from financial_text_to_pandas.preprocessing.table_clean import (
    align_grid,
    clean_table,
    drop_empty_rows_and_columns,
    expand_rowspan_colspan,
    infer_statement_type,
    infer_unit,
)
from financial_text_to_pandas.preprocessing.table_extract import extract_html_tables
from financial_text_to_pandas.preprocessing.text_linker import replace_tables_with_refs
from financial_text_to_pandas.types import (
    AuditRow,
    CleanTable,
    HtmlTableBlock,
    PreprocessingResult,
    ReportMetadata,
    TableMetadata,
    TableRef,
)


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_report_files(cfg: RunConfig) -> List[Path]:
    """Discover all OCR TXT files to process, filtered by config scope.

    Args:
        cfg: RunConfig loaded from run_profile.yaml.

    Returns:
        Ordered list of absolute paths to OCR TXT files.
    """
    input_root = cfg.input_root
    if not input_root.is_absolute():
        input_root = Path.cwd() / input_root

    all_files: List[Path] = []

    if cfg.is_sample and cfg.sample_tickers:
        tickers = cfg.sample_tickers
    else:
        # Full mode or no sample_tickers specified — discover all tickers
        tickers = sorted([d.name for d in input_root.iterdir() if d.is_dir()])

    for ticker in tickers:
        ticker_dir = input_root / ticker
        if not ticker_dir.is_dir():
            print(f"  [WARN] Ticker directory not found: {ticker_dir}", file=sys.stderr)
            continue
        # Glob all .txt files under the ticker directory
        txt_files = sorted(ticker_dir.rglob("*.txt"))
        all_files.extend(txt_files)

    # Apply sample_limit_reports if set
    if cfg.is_sample and cfg.sample_limit_reports is not None:
        all_files = all_files[: cfg.sample_limit_reports]

    return all_files


# ─────────────────────────────────────────────────────────────────────────────
# Single report processing
# ─────────────────────────────────────────────────────────────────────────────

def process_report(
    txt_path: Path,
    cfg: RunConfig,
    existing_audit: dict[str, str],
    dry_run: bool = False,
) -> PreprocessingResult:
    """Process one OCR TXT report file into CSV tables and linked text.

    Args:
        txt_path: Absolute path to the OCR TXT file.
        cfg: RunConfig.
        existing_audit: Map of table_id -> status from previous audit (for resume).
        dry_run: If True, skip writing any output files.

    Returns:
        PreprocessingResult summary.
    """
    input_root = cfg.input_root
    if not input_root.is_absolute():
        input_root = Path.cwd() / input_root

    output_root = cfg.output_root
    if not output_root.is_absolute():
        output_root = Path.cwd() / output_root

    # ── Infer report metadata ────────────────────────────────────────────────
    try:
        report_meta = infer_report_metadata(txt_path, input_root)
    except Exception as e:
        return PreprocessingResult(
            report_metadata=ReportMetadata(
                report_id=str(txt_path),
                ticker="UNKNOWN",
                year=0,
                report_type="unknown",
                document_name=str(txt_path.parent.name),
                source_txt_path=str(txt_path),
                file_size_bytes=0,
            ),
            clean_tables=[],
            table_metadata_rows=[],
            audit_rows=[],
            linked_text_path=None,
            success=False,
            error_message=f"Failed to infer metadata: {e}",
        )

    company_name = lookup_company_name(report_meta.ticker, input_root)

    # ── Read OCR text ────────────────────────────────────────────────────────
    try:
        raw_text = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return PreprocessingResult(
            report_metadata=report_meta,
            clean_tables=[],
            table_metadata_rows=[],
            audit_rows=[],
            linked_text_path=None,
            success=False,
            error_message=f"Cannot read file: {e}",
        )

    # ── Split pages ──────────────────────────────────────────────────────────
    pages = split_pages(raw_text)

    # ── Extract all HTML tables ───────────────────────────────────────────────
    all_blocks: List[HtmlTableBlock] = []
    for page in pages:
        blocks = extract_html_tables(page.raw_text, report_meta, page.page_number)
        all_blocks.extend(blocks)

    # ── Build output paths ────────────────────────────────────────────────────
    csv_base = (
        output_root
        / "tables_csv"
        / report_meta.ticker
        / str(report_meta.year)
        / report_meta.report_type
    )
    linked_text_dir = (
        output_root
        / "reports_text_linked"
        / report_meta.ticker
        / str(report_meta.year)
        / report_meta.report_type
    )

    # ── Process each table block ──────────────────────────────────────────────
    clean_tables: List[CleanTable] = []
    table_metadata_rows: List[TableMetadata] = []
    audit_rows: List[AuditRow] = []
    table_refs: List[TableRef] = []
    created_at = datetime.now(timezone.utc).isoformat()

    for block in all_blocks:
        # Resume: skip already successfully processed tables
        if cfg.resume and existing_audit.get(block.table_id) == "success":
            print(f"    [SKIP] {block.table_id} (already processed)")
            continue

        raw_shape = ""
        clean_shape = ""
        audit_status = "success"
        error_message = ""
        ct: Optional[CleanTable] = None

        try:
            # Parse HTML → grid
            soup = BeautifulSoup(block.html, "lxml")
            table_tag = soup.find("table")
            if table_tag is None:
                raise ValueError("No <table> tag found in block HTML")

            raw_grid = expand_rowspan_colspan(table_tag)
            raw_grid = align_grid(raw_grid)
            raw_shape = f"{len(raw_grid)}x{len(raw_grid[0]) if raw_grid else 0}"

            clean_grid = drop_empty_rows_and_columns(raw_grid)

            # Build relative CSV path
            rel_csv_path = (
                f"tables_csv/{report_meta.ticker}/{report_meta.year}"
                f"/{report_meta.report_type}/{block.table_id}.csv"
            )
            abs_csv_path = output_root / rel_csv_path

            # Infer statement type and unit from nearby text
            statement_type = infer_statement_type(
                block.nearby_text_before, block.nearby_text_after, []
            )
            unit = infer_unit(block.nearby_text_before, block.nearby_text_after)

            # Build TableMetadata
            tm = TableMetadata(
                table_id=block.table_id,
                csv_path=rel_csv_path,
                ticker=report_meta.ticker,
                company_name=company_name,
                year=report_meta.year,
                report_type=report_meta.report_type,
                statement_type=statement_type,
                unit=unit,
                source_txt_path=report_meta.source_txt_path,
                page_number=block.page_number,
                table_index=block.table_index,
                title=_extract_title(block.nearby_text_before),
                nearby_text_before=block.nearby_text_before,
                nearby_text_after=block.nearby_text_after,
                row_count=0,
                column_count=0,
                numeric_cell_count=0,
                quality_score=0.0,
                needs_review=False,
                review_reason="",
                created_at=created_at,
            )

            # Clean table
            ct = clean_table(clean_grid, tm)

            # Update metadata with clean table stats
            tm.row_count = ct.row_count
            tm.column_count = ct.column_count
            tm.numeric_cell_count = ct.numeric_cell_count
            tm.quality_score = ct.quality_score
            tm.needs_review = ct.needs_review
            tm.review_reason = ct.review_reason

            clean_shape = f"{ct.row_count}x{ct.column_count}"
            audit_status = "needs_review" if ct.needs_review else "success"

            # Write CSV
            if not dry_run:
                abs_csv_path.parent.mkdir(parents=True, exist_ok=True)
                ct.dataframe.to_csv(abs_csv_path, index=False, encoding="utf-8-sig")
                # Validate reopen
                _validate_csv_reopen(abs_csv_path)

            clean_tables.append(ct)
            table_metadata_rows.append(tm)
            table_refs.append(
                TableRef(
                    table_id=block.table_id,
                    csv_path=rel_csv_path,
                    html_snippet=block.html,
                )
            )

        except Exception as exc:
            audit_status = "failed"
            error_message = f"{type(exc).__name__}: {exc}"
            clean_shape = clean_shape or "0x0"
            print(f"    [ERROR] {block.table_id}: {error_message}", file=sys.stderr)

        finally:
            audit_rows.append(
                AuditRow(
                    report_id=report_meta.report_id,
                    table_id=block.table_id,
                    status=audit_status,
                    raw_shape=raw_shape,
                    clean_shape=clean_shape,
                    numeric_cell_count=ct.numeric_cell_count if ct else 0,
                    quality_score=ct.quality_score if ct else 0.0,
                    needs_review=ct.needs_review if ct else False,
                    review_reason=ct.review_reason if ct else "",
                    error_message=error_message,
                )
            )

    # ── Write linked text ─────────────────────────────────────────────────────
    linked_text_path: Optional[Path] = None
    if not dry_run and table_refs:
        try:
            linked_text = replace_tables_with_refs(raw_text, table_refs)
            linked_text_dir.mkdir(parents=True, exist_ok=True)
            linked_text_path = linked_text_dir / f"{report_meta.report_id}.txt"
            linked_text_path.write_text(linked_text, encoding="utf-8")
        except Exception as e:
            print(f"  [WARN] Could not write linked text: {e}", file=sys.stderr)

    return PreprocessingResult(
        report_metadata=report_meta,
        clean_tables=clean_tables,
        table_metadata_rows=table_metadata_rows,
        audit_rows=audit_rows,
        linked_text_path=linked_text_path,
        success=True,
        error_message="",
    )


def _validate_csv_reopen(path: Path) -> bool:
    """Validate that a written CSV can be reopened with pandas.

    Raises:
        RuntimeError: If the CSV cannot be loaded.
    """
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
        return True
    except Exception as e:
        raise RuntimeError(f"CSV reopen validation failed for {path}: {e}") from e


def _extract_title(nearby_before: str) -> str:
    """Extract a short title from nearby-before text (last non-empty line)."""
    lines = [ln.strip() for ln in nearby_before.splitlines() if ln.strip()]
    return lines[-1][:200] if lines else ""


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline orchestration
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(cfg: RunConfig, dry_run: bool = False) -> None:
    """Run the Phase 1 preprocessing pipeline.

    Args:
        cfg: Loaded RunConfig.
        dry_run: List planned files and exit without writing output.
    """
    print(f"\n{'='*60}")
    print(f"  Financial Text-to-Pandas — Phase 1 Preprocessing")
    print(f"{'='*60}")
    print(f"  run_mode          : {cfg.run_mode}")
    print(f"  input_root        : {cfg.input_root}")
    print(f"  output_root       : {cfg.output_root}")
    if cfg.is_sample:
        print(f"  sample_tickers    : {cfg.sample_tickers}")
        print(f"  sample_limit      : {cfg.sample_limit_reports}")
    print(f"  resume            : {cfg.resume}")
    print(f"  dry_run           : {dry_run}")
    print()

    # ── Discover files ────────────────────────────────────────────────────────
    files = discover_report_files(cfg)
    print(f"  Found {len(files)} report file(s) to process.")

    if not files:
        print("  Nothing to process. Check input_root and sample_tickers in config.")
        return

    if dry_run:
        print("\n  [DRY RUN] Planned files:")
        for f in files:
            print(f"    {f}")
        return

    # ── Load existing audit for resume ────────────────────────────────────────
    output_root = cfg.output_root
    if not output_root.is_absolute():
        output_root = Path.cwd() / output_root

    existing_audit = load_audit(output_root) if cfg.resume else {}
    if existing_audit:
        print(f"  Resume: {len(existing_audit)} tables already in audit.")

    # ── Process each report ───────────────────────────────────────────────────
    total_tables = 0
    total_success = 0
    total_failed = 0
    total_review = 0
    all_audit_rows = []
    all_table_metadata = []
    all_report_metadata = []

    for i, txt_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {txt_path.name}")

        result = process_report(txt_path, cfg, existing_audit, dry_run=False)

        # Collect results
        all_audit_rows.extend(result.audit_rows)
        all_table_metadata.extend(result.table_metadata_rows)
        all_report_metadata.append(result.report_metadata)

        # Print summary for this report
        n_tables = len(result.audit_rows)
        n_ok = sum(1 for r in result.audit_rows if r.status == "success")
        n_rev = sum(1 for r in result.audit_rows if r.status == "needs_review")
        n_fail = sum(1 for r in result.audit_rows if r.status == "failed")
        total_tables += n_tables
        total_success += n_ok
        total_review += n_rev
        total_failed += n_fail

        print(f"  -> {n_tables} tables  |  {n_ok} ok  |  {n_rev} review  |  {n_fail} failed")
        if result.linked_text_path:
            print(f"  -> Linked text: {result.linked_text_path}")
        if not result.success:
            print(f"  -> [ERROR] {result.error_message}", file=sys.stderr)

    # ── Write aggregate metadata and audit ─────────────────────────────────────
    print(f"\n  Writing metadata and audit files...")
    write_table_metadata(all_table_metadata, output_root)
    write_report_metadata(all_report_metadata, output_root)
    write_audit(all_audit_rows, output_root)

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Phase 1 Complete")
    print(f"{'='*60}")
    print(f"  Reports processed : {len(files)}")
    print(f"  Tables total      : {total_tables}")
    print(f"  Tables success    : {total_success}")
    print(f"  Tables review     : {total_review}")
    print(f"  Tables failed     : {total_failed}")
    print(f"  Output root       : {output_root}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 1: Financial Text-to-Pandas Preprocessing Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/run_profile.yaml"),
        help="Path to run_profile.yaml (default: config/run_profile.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned input files without writing any output",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"[CONFIG ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        run_pipeline(cfg, dry_run=args.dry_run)
    except Exception as e:
        print(f"\n[PIPELINE ERROR] {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
