# 04 - Phase 1: Preprocessing and CSV Table Store

## 1. Phase Goal
Convert ViFinQA OCR TXT reports into clean CSV tables, linked text files, metadata files, and preprocessing audit logs.

Phase 1 must be deterministic, testable, and reviewable. It must not run the full dataset until a one-report sample has been reviewed.

## 2. Scope
Implement only:
- OCR TXT page splitting;
- report metadata inference;
- HTML table extraction;
- table grid normalization;
- Vietnamese number parsing;
- CSV table output;
- linked text output;
- metadata and audit output;
- sample CLI;
- unit tests.

Do not implement:
- retrieval;
- embedding;
- reranking;
- LLM calls;
- QA reasoning;
- UI/API;
- database code.

## 3. Inputs

```text
ViFinQA/financial_statements/{ticker}/{year}/{document_name}/*.txt
ViFinQA/code_stock.csv
ViFinQA/questions.jsonl
```

## 4. Outputs

```text
<output_root>/tables_csv/{ticker}/{year}/{report_type}/{table_id}.csv
<output_root>/reports_text_linked/{ticker}/{year}/{report_type}/{report_id}.txt
<output_root>/table_metadata.csv
<output_root>/report_metadata.csv
<output_root>/preprocessing_audit.csv
```

## 5. Files to Create

```text
config/run_profile.yaml
src/financial_text_to_pandas/__init__.py
src/financial_text_to_pandas/config.py
src/financial_text_to_pandas/types.py
src/financial_text_to_pandas/preprocessing/__init__.py
src/financial_text_to_pandas/preprocessing/ocr.py
src/financial_text_to_pandas/preprocessing/table_extract.py
src/financial_text_to_pandas/preprocessing/table_clean.py
src/financial_text_to_pandas/preprocessing/number_parser.py
src/financial_text_to_pandas/preprocessing/text_linker.py
src/financial_text_to_pandas/preprocessing/metadata.py
src/financial_text_to_pandas/preprocessing/audit.py
src/financial_text_to_pandas/preprocessing/pipeline.py
tests/test_preprocessing_ocr.py
tests/test_table_extract.py
tests/test_table_clean.py
tests/test_number_parser.py
tests/test_text_linker.py
tests/test_preprocessing_pipeline.py
```

## 6. Data Types

Define these in `types.py` or the closest local module:

```python
Page
ReportMetadata
HtmlTableBlock
HeaderDetection
ParsedNumber
CleanTable
TableMetadata
AuditRow
TableRef
PreprocessingResult
```

Required fields:

```text
Page: page_number, raw_text
ReportMetadata: report_id, ticker, year, report_type, document_name, source_txt_path, file_size_bytes
HtmlTableBlock: table_id, page_number, table_index, html, nearby_text_before, nearby_text_after
ParsedNumber: raw_value, parsed_value, number_type, unit_hint, parse_status
CleanTable: table_id, dataframe, csv_path, row_count, column_count, numeric_cell_count
TableMetadata: table_id, csv_path, ticker, year, report_type, page_number, table_index, unit, title, quality_score, needs_review
AuditRow: table_id, status, raw_shape, clean_shape, numeric_cell_count, quality_score, needs_review, review_reason
```

## 7. Implementation Steps

### Step 1 - Project Skeleton
Create config file, source package, test package, and importable modules. Do not create `<output_root>`.

`config/run_profile.yaml` must be the only place used to switch between sample and full preprocessing runs:

```yaml
# Chế độ chạy hiện tại của pipeline.
# sample = chạy ít để kiểm tra chất lượng đầu ra.
# full = chạy toàn bộ dữ liệu sau khi đã duyệt mẫu.
run_mode: sample

# Thư mục đầu vào chứa các file OCR TXT của ViFinQA.
input_root: ViFinQA/financial_statements

# Thư mục đầu ra chỉ được tạo khi pipeline runtime bắt đầu chạy.
output_root: artifacts/preprocessing

# Danh sách mã cổ phiếu dùng để chạy thử trong chế độ sample.
sample_tickers:
  - AAA

# Giới hạn số báo cáo khi chạy thử lần đầu.
# Sau khi duyệt 1 report, có thể đổi thành null để chạy cả ticker.
sample_limit_reports: 1

# Cần đặt true khi run_mode = full để tránh vô tình chạy toàn bộ dữ liệu.
full_run_confirmed: false

# Khi true, pipeline đọc audit và bỏ qua báo cáo đã xử lý thành công.
resume: true
```

Validation:

```powershell
python -c "import financial_text_to_pandas"
```

### Step 2 - Page Splitting
Implement:

```python
split_pages(raw_text: str) -> list[Page]
```

Rules:
- detect `===== PAGE n =====`;
- preserve page number;
- preserve page text after marker;
- if no marker exists, return page 1.

Tests:
- two-page input;
- missing marker;
- extra whitespace in marker;
- lowercase/uppercase marker variants.

### Step 3 - Report Metadata
Implement:

```python
infer_report_metadata(path: Path, dataset_root: Path) -> ReportMetadata
```

Rules:
- infer `ticker` from path segment;
- infer `year` from path segment;
- infer `report_type` from document name;
- generate stable `report_id`;
- store relative source path.

Tests:
- consolidated path;
- separate path;
- explanation path;
- invalid path raises clear error.

### Step 4 - HTML Table Extraction
Implement:

```python
extract_html_tables(page_html: str, report_meta: ReportMetadata, page_number: int) -> list[HtmlTableBlock]
```

Rules:
- use BeautifulSoup;
- extract every `<table>`;
- preserve raw HTML;
- assign deterministic `table_id`;
- capture nearby text before/after table when possible.

Tests:
- one table;
- multiple tables;
- page without table;
- malformed HTML.

### Step 5 - Rowspan/Colspan Expansion
Implement:

```python
expand_rowspan_colspan(table_tag: Tag) -> list[list[str]]
align_grid(rows: list[list[str]]) -> list[list[str]]
drop_empty_rows_and_columns(rows: list[list[str]]) -> list[list[str]]
```

Rules:
- expand `rowspan` downward;
- expand `colspan` rightward;
- normalize whitespace;
- keep all rows rectangular;
- remove empty rows and columns.

Tests:
- rowspan only;
- colspan only;
- both rowspan and colspan;
- empty rows/columns;
- irregular row width.

### Step 6 - Header Detection and Flattening
Implement:

```python
detect_header_rows(grid: list[list[str]]) -> HeaderDetection
flatten_headers(grid: list[list[str]], header_rows: list[int]) -> list[str]
```

Rules:
- score rows using keywords: `chi tieu`, `ma so`, `thuyet minh`, dates, years;
- support multi-row headers;
- flatten with `_`;
- generate stable fallback names for empty columns;
- de-duplicate column names.

Tests:
- single header row;
- two header rows;
- empty header cells;
- duplicated names;
- no obvious header.

### Step 7 - Financial Group Context
Implement:

```python
propagate_group_context(df: pd.DataFrame) -> pd.DataFrame
```

Rules:
- detect section rows without numeric values;
- propagate section labels to child metric rows;
- create `row_label_full`;
- preserve original label in `row_label_raw`.

Tests:
- one-level section;
- nested section;
- rows with numeric values are not treated as pure section headers.

### Step 8 - Vietnamese Number Parser
Implement:

```python
parse_vn_number(value: str) -> ParsedNumber
```

Supported examples:

```text
15.230.000      -> parsed_value=15230000
12,5            -> parsed_value=12.5
12,5%           -> parsed_value=0.125, unit_hint="%"
(500.000)       -> parsed_value=-500000
-500.000        -> parsed_value=-500000
"-"             -> parsed_value=null
""              -> parsed_value=null
31/12/2024      -> parse_status="not_number"
```

Tests:
- thousands separator;
- decimal comma;
- percentage;
- parentheses negative;
- date string;
- text string.

### Step 9 - Clean Table
Implement:

```python
clean_table(grid: list[list[str]], metadata: TableMetadata) -> CleanTable
```

Rules:
- convert grid to DataFrame;
- apply flattened headers;
- add `row_label_full`;
- add numeric columns as `numeric__<column_name>`;
- compute quality score;
- mark `needs_review`.

Tests:
- valid financial table;
- no numeric cells;
- too few rows;
- duplicate headers.

### Step 10 - Write CSV and Validate
Implement:

```python
write_table_csv(clean_table: CleanTable, output_root: Path) -> Path
validate_csv_reopen(path: Path) -> bool
```

Rules:
- write UTF-8 with BOM only if needed for Excel compatibility;
- preserve stable output path;
- reopen with `pd.read_csv`;
- fail loudly on invalid CSV.

Tests:
- CSV path convention;
- CSV reopen success;
- invalid path error.

### Step 11 - Linked Text
Implement:

```python
replace_tables_with_refs(report_text: str, table_refs: list[TableRef]) -> str
```

Rules:
- remove original HTML table blocks;
- insert `[[TABLE_REF:{table_id}|{relative_csv_path}]]`;
- preserve page boundaries;
- preserve non-table text.

Tests:
- one table replacement;
- multiple table replacement;
- no table page unchanged.

### Step 12 - Metadata and Audit
Implement:

```python
write_table_metadata(rows: list[TableMetadata], output_root: Path) -> None
write_report_metadata(rows: list[ReportMetadata], output_root: Path) -> None
write_audit(rows: list[AuditRow], output_root: Path) -> None
```

Rules:
- write CSV;
- stable column order;
- include every processed table;
- include failed tables in audit.

Tests:
- metadata column order;
- audit includes failures;
- empty input behavior.

### Step 13 - Sample CLI
Implement:

```powershell
python -m financial_text_to_pandas.preprocessing.pipeline --config config/run_profile.yaml
```

Rules:
- read run scope from `config/run_profile.yaml`;
- process one report first when `run_mode=sample` and `sample_limit_reports=1`;
- create output folders only at runtime;
- print report count and table count;
- never run full dataset by default.
- support `--dry-run` to list planned input files without writing outputs;
- support optional CLI overrides for development, but the documented workflow must use `run_profile.yaml`;
- support `--resume` to skip already completed reports based on audit status;
- support `--recreate` to explicitly delete and rebuild only the selected output scope;
- require `full_run_confirmed=true` in config for full-corpus execution.

## 8. Progressive Run Gates

Phase 1 must be reviewed in stages. Do not jump from unit tests to the full corpus.

All gates use the same command:

```powershell
python -m financial_text_to_pandas.preprocessing.pipeline --config config/run_profile.yaml
```

Only `config/run_profile.yaml` changes between gates.

### Gate P1.0 - Unit Tests Only
Run:

```powershell
pytest tests/test_preprocessing_ocr.py tests/test_table_extract.py tests/test_table_clean.py tests/test_number_parser.py tests/test_text_linker.py
```

Expected result:
- no output folders are created;
- all pure function tests pass;
- table cleaning behavior is validated with synthetic tables.

### Gate P1.1 - One-Report Smoke Run
Set:

```yaml
# Chạy thật nhỏ để xem định dạng CSV, metadata và audit có đúng không.
run_mode: sample
sample_tickers: [AAA]
sample_limit_reports: 1
full_run_confirmed: false
```

Process size:
- exactly 1 report;
- all tables found inside that report;
- no other ticker/year/report should be processed.

Review:
- open the first 5 CSV files;
- verify column names are readable and stable;
- verify `row_label_raw`, `row_label_full`, raw value columns, and numeric columns;
- verify `table_metadata.csv`;
- verify `preprocessing_audit.csv`;
- verify linked text contains valid `TABLE_REF` entries;
- confirm every generated CSV reopens with Pandas.

Approval rule:
- if table shape, headers, row labels, number parsing, and audit are acceptable, move to P1.2;
- if not acceptable, fix preprocessing code and rerun only P1.1.

### Gate P1.2 - One-Ticker Review Run
Set:

```yaml
# Chạy hết một mã cổ phiếu để xem pipeline có ổn qua nhiều năm/loại báo cáo không.
run_mode: sample
sample_tickers: [AAA]
sample_limit_reports: null
full_run_confirmed: false
```

Process size:
- one ticker;
- all available years and report types for that ticker;
- skip completed reports when audit status is successful.

Review:
- inspect per-report table counts;
- inspect at least 20 random CSV tables;
- inspect all failed or `needs_review=true` audit rows;
- compare report metadata against source paths;
- confirm output paths are stable.

Approval rule:
- if quality is stable across years/report types, move to P1.3;
- if failures cluster around a table pattern, improve the cleaner before expanding.

### Gate P1.3 - Small Portfolio Review Run
Set:

```yaml
# Chạy nhiều mã đại diện để bắt các mẫu bảng khác nhau trước khi full.
run_mode: sample
sample_tickers: [AAA, VCB, HPG, FPT, HSG]
sample_limit_reports: 50
full_run_confirmed: false
```

Process size:
- 5 representative tickers or maximum 50 reports;
- include different years and both report types when available.

Review:
- inspect preprocessing success rate;
- inspect numeric parse success rate;
- inspect examples from each ticker;
- confirm metadata can support retrieval filtering by ticker, year, report type, page, and table title;
- confirm no failed table is silently dropped.

Approval rule:
- if the output quality is approved, Phase 1 may run full corpus;
- if not approved, keep improving on the smallest failing sample.

### Gate P1.4 - Full Corpus Run
Set only after approval:

```yaml
# Đổi đúng một chỗ này để pipeline xử lý toàn bộ dữ liệu.
run_mode: full

# Bắt buộc xác nhận để tránh chạy full ngoài ý muốn.
full_run_confirmed: true
```

Process size:
- all selected ViFinQA reports.

Review:
- total report count;
- total table count;
- success/failure counts;
- `needs_review` distribution;
- CSV reopen validation summary;
- final preprocessing audit.

## 9. Review Gate
Phase 1 can move forward only after reviewing:
- first 5 generated CSV tables;
- `table_metadata.csv`;
- `preprocessing_audit.csv`;
- linked text file with `TABLE_REF`;
- unit test results.

## 10. Anti-Patterns
Do not:
- write cleaned tables into a database;
- run full dataset before sample review;
- silently drop failed tables;
- lose raw values;
- create output folders during scaffold;
- use LLM calls in Phase 1.
