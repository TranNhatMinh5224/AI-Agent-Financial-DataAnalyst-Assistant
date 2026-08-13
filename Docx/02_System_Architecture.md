# 02 - System Architecture

## 1. Core Architecture

```text
ViFinQA OCR TXT
-> Preprocessing
-> CSV Table Store
-> Table Retrieval
-> Evidence Package
-> Text-to-Pandas Reasoning
-> Verification
-> Final Answer
```

The core data object is a CSV table loaded as a Pandas DataFrame.

## 2. Preprocessing Layer

Responsibilities:
- split OCR reports by page marker;
- infer report metadata from file paths;
- extract every HTML `<table>`;
- convert HTML tables into rectangular grids;
- expand `rowspan`;
- expand `colspan`;
- normalize whitespace and HTML entities;
- detect header rows;
- flatten multi-row headers;
- propagate financial hierarchy into row labels;
- parse Vietnamese numeric formats;
- write clean CSV files;
- replace HTML table blocks with `TABLE_REF`;
- write metadata and audit files.

Required modules:

```text
preprocessing/ocr.py
preprocessing/table_extract.py
preprocessing/table_clean.py
preprocessing/number_parser.py
preprocessing/text_linker.py
preprocessing/metadata.py
preprocessing/audit.py
preprocessing/pipeline.py
```

## 3. CSV Table Store Layer

Each table must have metadata:

```text
table_id
csv_path
ticker
company_name
year
report_type
statement_type
unit
source_txt_path
page_number
table_index
title
nearby_text_before
nearby_text_after
row_count
column_count
numeric_cell_count
quality_score
needs_review
review_reason
created_at
```

`table_id` format:

```text
{ticker}_{year}_{report_type}_page{page_number}_table{table_index}
```

## 4. Retrieval Layer

Retrieval pipeline:

```text
Question
-> extract query hints
-> filter table_metadata
-> BM25 top 50
-> Qwen3-Embedding-8B top 50
-> merge candidates
-> deduplicate table_id
-> rerank top 10
-> evidence package
```

Candidate outputs must preserve:

```text
table_id
bm25_score
dense_score
reranker_score
retrieval_source
rank
csv_path
metadata_filter_status
```

## 5. Reasoning Layer

Evidence tables are loaded into:

```python
dfs: dict[str, pandas.DataFrame]
metadata_by_table: dict[str, dict]
```

Reasoning strategies:
- `deterministic`: exact lookup with no LLM code;
- `cot`: controlled natural-language reasoning;
- `pot`: generated Pandas code executed in sandbox;
- `multi_step`: iterative planning for hard questions.

## 6. Verification Layer

Verifier input:

```text
question
answer
selected_cells
calculation_trace
evidence_tables
```

Verifier checks:
- selected table exists;
- selected row matches requested metric;
- selected column matches requested period;
- raw value parses to parsed value;
- unit conversion is correct;
- sign convention is correct;
- final rounding is correct;
- final answer is grounded in evidence.

## 7. No Database Rule
Do not create:
- database schemas;
- migration files;
- database connectors;
- database ingestion scripts;
- database inspection scripts;
- Text-to-SQL modules.
