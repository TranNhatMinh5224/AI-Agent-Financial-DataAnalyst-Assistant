# 04 - Phase 1: Data Preparation and CSV Table Store

## 1. Phase Goal
Convert ViFinQA OCR TXT reports into clean CSV tables, linked text files, metadata files, and preprocessing audit logs.

Phase 1 creates the data foundation for retrieval, cell grounding, and Pandas reasoning.

## 2. Scope
Implement only:
- OCR TXT page splitting;
- report metadata inference;
- HTML table extraction;
- `rowspan` / `colspan` expansion;
- row alignment;
- whitespace normalization;
- header detection and flattening;
- financial group context propagation;
- Vietnamese number normalization;
- CSV table output;
- `TABLE_REF` linked text output;
- table metadata;
- report metadata;
- preprocessing audit;
- sample/full run gates;
- unit tests.

Do not implement in Phase 1:
- LLM calls;
- retrieval;
- embedding;
- reranking;
- reasoning;
- cell grounding;
- database;
- Text-to-SQL.

## 3. Inputs

```text
ViFinQA/financial_statements/{ticker}/{year}/{document_name}/*.txt
ViFinQA/code_stock.csv
ViFinQA/questions.jsonl
```

`questions.jsonl` is available for later phases. Phase 1 should not answer questions.

## 4. Outputs

```text
<output_root>/tables_csv/{ticker}/{year}/{report_type}/{table_id}.csv
<output_root>/reports_text_linked/{ticker}/{year}/{report_type}/{report_id}.txt
<output_root>/table_metadata.csv
<output_root>/report_metadata.csv
<output_root>/preprocessing_audit.csv
```

CSV tables are the canonical financial data representation for Pandas.

## 5. Files to Create When Implementation Starts

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

Do not create output folders during scaffold. Output folders are created only by runtime commands.

## 6. Single Run Profile
`config/run_profile.yaml` is the only place used to switch between sample and full preprocessing runs.

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

No source code should be edited to switch from sample to full.

## 7. Data Types
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
TableMetadata: table_id, csv_path, ticker, company_name, year, report_type, statement_type, unit, source_txt_path, page_number, table_index, title, nearby_text_before, nearby_text_after, row_count, column_count, numeric_cell_count, quality_score, needs_review, review_reason, created_at
AuditRow: report_id, table_id, status, raw_shape, clean_shape, numeric_cell_count, quality_score, needs_review, review_reason, error_message
```

## 8. Clean CSV Contract
Every cleaned table CSV must preserve both human-readable and machine-parsed values.

Required columns when available:

```text
row_label_raw
row_label_full
<original data columns>
numeric__<original data column>
```

Rules:
- keep raw text values unchanged in original data columns;
- write parsed numeric values into `numeric__*` columns;
- preserve column labels needed for later cell grounding;
- preserve row hierarchy in `row_label_full`;
- do not drop a table silently when cleaning fails.

## 9. Implementation Steps

### Step 1 - Project Skeleton
Create config file, source package, test package, and importable modules. Do not create `<output_root>`.

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
- score rows using keywords such as `chi tieu`, `ma so`, `thuyet minh`, dates, and years;
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
- add `row_label_raw`;
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
- include failed tables in audit;
- preserve enough metadata for Phase 2 filtering and Phase 3 grounding.

Tests:
- metadata column order;
- audit includes failures;
- empty input behavior.

### Step 13 - Pipeline CLI
Implement:

```powershell
python -m financial_text_to_pandas.preprocessing.pipeline --config config/run_profile.yaml
```

Rules:
- read run scope from `config/run_profile.yaml`;
- create output folders only at runtime;
- print report count and table count;
- never run full dataset by default;
- support `--dry-run` to list planned input files without writing outputs;
- support optional CLI overrides for development, but the documented workflow must use `run_profile.yaml`;
- support `resume` from audit;
- require `full_run_confirmed=true` in config for full-corpus execution.

## 10. Progressive Phase 1 Run Gates
All gates use the same command:

```powershell
python -m financial_text_to_pandas.preprocessing.pipeline --config config/run_profile.yaml
```

Only `config/run_profile.yaml` changes between gates.

### Gate P1.0 - Unit Tests Only
Maximum run size: 0 reports.

Expected:
- no output folders are created;
- all pure function tests pass.

### Gate P1.1 - One-Report Smoke Run
Set:

```yaml
# Chạy thật nhỏ để xem định dạng CSV, metadata và audit có đúng không.
run_mode: sample
sample_tickers: [AAA]
sample_limit_reports: 1
full_run_confirmed: false
```

Review:
- first 5 CSV files;
- `row_label_raw` and `row_label_full`;
- raw value columns and `numeric__*` columns;
- `table_metadata.csv`;
- `preprocessing_audit.csv`;
- linked text with `TABLE_REF`;
- CSV reopen validation.

### Gate P1.2 - One-Ticker Review Run
Set:

```yaml
# Chạy hết một mã cổ phiếu để xem pipeline có ổn qua nhiều năm/loại báo cáo không.
run_mode: sample
sample_tickers: [AAA]
sample_limit_reports: null
full_run_confirmed: false
```

Review:
- per-report table counts;
- at least 20 random CSV tables;
- all failed or `needs_review=true` audit rows;
- metadata accuracy across years and report types.

### Gate P1.3 - Small Portfolio Review Run
Set:

```yaml
# Chạy nhiều mã đại diện để bắt các mẫu bảng khác nhau trước khi full.
run_mode: sample
sample_tickers: [AAA, VCB, HPG, FPT, HSG]
sample_limit_reports: 50
full_run_confirmed: false
```

Review:
- preprocessing success rate;
- numeric parse success rate;
- examples from each ticker;
- no failed table is silently dropped.

### Gate P1.4 - Full Corpus Run
Set only after approval:

```yaml
# Đổi đúng một chỗ này để pipeline xử lý toàn bộ dữ liệu.
run_mode: full

# Bắt buộc xác nhận để tránh chạy full ngoài ý muốn.
full_run_confirmed: true
```

Review:
- total report count;
- total table count;
- success/failure counts;
- `needs_review` distribution;
- CSV reopen validation summary;
- final preprocessing audit.

## 11. Review Gate
Phase 1 can move forward only after reviewing:
- generated CSV tables;
- `table_metadata.csv`;
- `report_metadata.csv`;
- `preprocessing_audit.csv`;
- linked text file with `TABLE_REF`;
- unit test results.

## 12. Anti-Patterns
Do not:
- write cleaned tables into a database;
- run full dataset before sample review;
- silently drop failed tables;
- lose raw values;
- create output folders during scaffold;
- use LLM calls in Phase 1;
- perform cell grounding in Phase 1.
