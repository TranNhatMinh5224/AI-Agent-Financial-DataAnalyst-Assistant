# 02 - System Architecture

## 1. Canonical Architecture

```text
Financial Reports
-> OCR TXT + HTML Tables
-> Extract Tables
-> Clean / Normalize Tables
-> CSV Tables + Metadata + Linked Text

Question
-> Query Hints / Metadata Filtering
-> Retriever
-> Candidate Tables
-> Reranker
-> Top-K Evidence Tables

Schema-Aware Cell Grounding
-> Selected Tables / Rows / Columns / Cells

Reasoning Strategy
-> Direct Lookup / PoT / CoT / Multi-hop

Verification
-> Verified Numerical Answer
```

The core financial representation is:

```text
CSV -> pandas.DataFrame
```

## 2. Preprocessing Layer
Responsibilities:
- split OCR reports by page marker;
- infer report metadata from file paths;
- extract every HTML `<table>`;
- convert HTML tables into rectangular grids;
- expand `rowspan`;
- expand `colspan`;
- align irregular rows;
- normalize whitespace and HTML entities;
- detect header rows;
- flatten multi-row headers;
- propagate financial group context into row labels;
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

Phase 1 must not contain LLM, retrieval, embedding, reasoning, database, or Text-to-SQL code.

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
Retrieval is recall-first.

```text
Question
-> Query Hints
-> Metadata Filtering
-> BM25 top 50
-> Dense Retrieval top 50
-> Candidate Merge
-> Deduplicate by table_id
-> Reranker top 10
-> Top-K Evidence Tables
```

Retriever responsibility:
- maximize chance that every required table appears in candidates;
- avoid over-filtering when metadata confidence is low.

Reranker responsibility:
- improve precision and ranking quality among candidates;
- preserve candidate scores and provenance.

Missing a required table is a critical retrieval failure.

Candidate outputs must preserve:

```text
query_id
question
table_id
rank
bm25_score
dense_score
reranker_score
retrieval_source
csv_path
metadata_filter_status
model_name
model_version
created_at
```

## 5. Evidence Package Layer
Top-K evidence tables are packaged for reasoning:

```json
{
  "query_id": "string",
  "question": "string",
  "intent": {},
  "tables": [
    {
      "table_id": "string",
      "csv_path": "string",
      "metadata": {},
      "retrieval_scores": {}
    }
  ],
  "linked_text_context": ["string"]
}
```

Evidence tables are loaded into:

```python
dfs: dict[str, pandas.DataFrame]
metadata_by_table: dict[str, dict]
```

## 6. Schema-Aware Cell Grounding Layer
Cell grounding is a first-class stage between retrieval and reasoning.

Responsibilities:
- identify the relevant `table_id`;
- identify the relevant `row_label`;
- identify the relevant `column_label`;
- extract `raw_value`;
- parse `parsed_value`;
- determine `unit`;
- assign confidence;
- return `I_INSUFFICIENT_EVIDENCE` when required tables are missing;
- return `E_NUMERICAL_EXTRACTION` when the table exists but row/column/cell grounding fails.

Grounding priority:

```text
row_label_full
-> row_label_raw
-> fuzzy matching with confidence threshold
```

Reasoning must not start if required cells cannot be grounded with acceptable confidence.

Grounded cell schema:

```text
table_id
csv_path
page_number
row_label
column_label
raw_value
parsed_value
unit
confidence
grounding_method
error_type
```

## 7. Reasoning Layer
Reasoning strategies:
- `deterministic`: direct lookup with one grounded cell and no arithmetic;
- `pot`: Program-of-Thought, generated Pandas code executed in sandbox;
- `cot`: controlled natural-language reasoning;
- `multi_hop`: iterative retrieval and grounding for hard questions;
- `auto`: strategy selector.

Adaptive strategy:

```text
Schema-Aware Grounding
-> Direct Lookup if one exact cell and no arithmetic
-> Strategy Selection
   -> PoT
   -> CoT fallback
   -> Multi-hop when intermediate result determines next evidence
-> Verification
```

PoT is preferred for arithmetic, aggregation, multiple values, and multiple tables when code generation is reliable.

CoT is used when sandbox/code execution fails, code generation is unstable, or natural-language reasoning is more reliable.

Multi-hop flow:

```text
Question
-> retrieve evidence
-> grounding
-> intermediate result
-> determine next retrieval requirement
-> retrieve again
-> grounding again
-> final calculation
```

This is not a complex multi-agent framework. It is an iterative control flow around retrieval, grounding, and reasoning.

## 8. Verification Layer
Verifier input:

```text
question
answer
grounded_cells
calculation_trace
evidence_tables
```

Verifier checks:
- selected table exists;
- selected row exists;
- selected column exists;
- selected cell exists;
- raw value parses to parsed value;
- unit conversion is correct;
- sign convention is correct;
- formula is correct;
- final rounding is correct;
- final numerical answer matches trace;
- final answer is grounded in evidence.

Answers with `verification_status = invalid` must not be accepted.

## 9. Shared Error Taxonomy

```text
E_NUMERICAL_EXTRACTION
I_INSUFFICIENT_EVIDENCE
T_TECHNICAL_ERROR
C_CALCULATION_ERROR
F_FORMULA_ERROR
U_UNVERIFIED
```

Use these codes consistently in Phase 3, Phase 4, tests, evaluation, and logs.

## 10. No Database Rule
Do not create:
- database schemas;
- migration files;
- database connectors;
- database ingestion scripts;
- database inspection scripts;
- ORM layers;
- Text-to-SQL modules;
- vector database services.
