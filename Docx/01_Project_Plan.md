# 01 - Project Plan: Financial Text-to-Pandas

## 1. Objective
Build an end-to-end Vietnamese financial QA system that answers numerical questions from ViFinQA financial reports.

The system must optimize for three core goals:

```text
FIND THE RIGHT TABLE
-> FIND THE RIGHT CELL
-> THEN CALCULATE
```

Every final answer must be grounded in CSV evidence and traceable to:
- `table_id`;
- `csv_path`;
- `page_number`;
- `row_label`;
- `column_label`;
- `raw_value`;
- `parsed_value`;
- `unit`.

## 2. Architecture Decision
Use **Text-to-Pandas**, not Text-to-SQL.

Keep:
- CSV table store;
- `TABLE_REF` linked text;
- metadata files;
- preprocessing audit;
- sample/full run gates in Phase 1;
- BM25;
- dense retrieval;
- reranker;
- Pandas;
- sandbox;
- verification;
- evaluation;
- unit tests.

Do not add:
- database schemas;
- database ingestion;
- ORM;
- vector database service;
- Text-to-SQL;
- distributed queues;
- Kubernetes;
- complex agent framework in the first implementation path.

## 3. Canonical End-to-End Flow
All documents in this project must use this flow:

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

## 4. Phase Summary

### Phase 1 - Data Preparation
Convert OCR TXT reports into reviewable artifacts:
- clean CSV tables;
- linked text with `TABLE_REF`;
- table metadata;
- report metadata;
- preprocessing audit.

Phase 1 contains no LLM, retrieval, embedding, reasoning, database, or Text-to-SQL logic.

### Phase 2 - Recall-First Table Retrieval
Retrieve top evidence tables for a question:

```text
Question
-> Query Hints
-> Metadata Filtering
-> BM25 + Dense Retrieval
-> Candidate Merge
-> Reranker
-> Top-K Evidence Tables
```

Retriever optimizes recall. Reranker optimizes precision and ranking quality.

Missing a required table is a critical retrieval failure.

### Phase 3 - Text-to-Pandas QA and Reasoning
Answer from retrieved CSV evidence:

```text
Question + Evidence Tables
-> Schema-Aware Cell Grounding
-> Strategy Selection
-> Direct Lookup / PoT / CoT / Multi-hop
-> Verification
-> Final Answer
```

Reasoning must not start until grounding identifies evidence cells with acceptable confidence, unless the system returns `I_INSUFFICIENT_EVIDENCE`.

### Phase 4 - Evaluation, UI, and Optimization
Expose and evaluate:
- retrieved tables;
- grounded cells;
- calculation traces;
- verifier results;
- error taxonomy;
- feedback logs.

## 5. Target Package Layout
Create this layout only when implementation starts:

```text
config/
  run_profile.yaml
src/financial_text_to_pandas/
  __init__.py
  config.py
  types.py
  preprocessing/
    __init__.py
    ocr.py
    table_extract.py
    table_clean.py
    number_parser.py
    text_linker.py
    metadata.py
    audit.py
    pipeline.py
  retrieval/
    __init__.py
    corpus.py
    query_hints.py
    bm25.py
    embeddings.py
    reranker.py
    search.py
    evaluate.py
  reasoning/
    __init__.py
    evidence.py
    intent.py
    cell_grounding.py
    strategy.py
    prompts.py
    sandbox.py
    tools.py
    multi_hop.py
    verifier.py
    answer.py
  eval/
    __init__.py
    golden.py
    metrics.py
tests/
```

Do not create output folders during scaffold. Output folders are created only by runtime commands.

## 6. Runtime Artifact Contract

Phase 1 creates:

```text
<output_root>/tables_csv/{ticker}/{year}/{report_type}/{table_id}.csv
<output_root>/reports_text_linked/{ticker}/{year}/{report_type}/{report_id}.txt
<output_root>/table_metadata.csv
<output_root>/report_metadata.csv
<output_root>/preprocessing_audit.csv
```

Phase 2 creates:

```text
<index_root>/table_corpus.csv
<index_root>/bm25_index.pkl
<index_root>/table_embeddings.parquet
<index_root>/retrieval_candidates.csv
<index_root>/retrieval_reranked.csv
<eval_root>/retrieval_eval.csv
```

Every embedding artifact must include:
- `table_id`;
- `model_name`;
- `model_version`;
- `created_at`;
- source corpus checksum or version.

Phase 3 creates:

```text
<runs_root>/{run_id}/evidence_package.json
<runs_root>/{run_id}/cell_grounding.json
<runs_root>/{run_id}/reasoning_trace.json
<runs_root>/{run_id}/verification.json
<runs_root>/{run_id}/answer.json
```

## 7. Retrieval Policy

Default stack:

```text
Lexical baseline: BM25
Dense retriever: Qwen3-Embedding-8B
Fallback dense retriever: Qwen3-Embedding-4B
Fallback multilingual baseline: BGE-M3
Reranker: required for final ranking
```

Target retrieval benchmark:

```text
BM25                              Recall@10 47.41%
BGE-M3                            Recall@10 53.05%
Qwen3-Embedding-4B                Recall@10 63.90%
Qwen3-Embedding-8B                Recall@10 67.48%
Qwen3-Embedding-4B + Reranker     Recall@10 80.19%
Qwen3-Embedding-8B + Reranker     Recall@10 80.80%
```

Primary metrics:
- `Recall@10`;
- `Recall@50`;
- `MRR`;
- `missing_evidence_rate`.

## 8. Reasoning Policy
Use adaptive reasoning after cell grounding.

Direct deterministic lookup:
- use when there is 1 table, 1 exact cell, and no arithmetic;
- run before complex reasoning.

PoT:
- use when arithmetic, aggregation, multiple values, multiple tables, or Pandas operations are needed;
- generated code must run in a sandbox.

CoT:
- use when code generation is unstable, sandbox execution fails, or natural-language reasoning is more reliable.

Multi-hop:
- use for hard questions where an intermediate result determines the next company, table, year, report, or metric to retrieve.

## 9. Error Taxonomy
Use the same error codes across Phase 3, Phase 4, tests, evaluation, and logs:

```text
E_NUMERICAL_EXTRACTION
I_INSUFFICIENT_EVIDENCE
T_TECHNICAL_ERROR
C_CALCULATION_ERROR
F_FORMULA_ERROR
U_UNVERIFIED
```

Do not add new error codes unless they solve a recurring evaluation need.

## 10. Run Scope Policy
The sample/full execution switch belongs to Phase 1 preprocessing only.

Create one runtime configuration file when implementation starts:

```text
config/run_profile.yaml
```

Required fields:

```yaml
# Chế độ chạy hiện tại của pipeline.
# sample = chạy ít để xem chất lượng đầu ra.
# full = chạy toàn bộ dữ liệu sau khi đã duyệt mẫu.
run_mode: sample

# Thư mục đầu vào chứa ViFinQA.
input_root: ViFinQA/financial_statements

# Thư mục đầu ra do Phase 1 tạo lúc runtime.
output_root: artifacts/preprocessing

# Khi run_mode = sample, chỉ xử lý các ticker trong danh sách này.
sample_tickers:
  - AAA

# Khi run_mode = sample, giới hạn số báo cáo để kiểm tra nhanh.
sample_limit_reports: 1

# Khi run_mode = full, bắt buộc đặt true để tránh vô tình chạy full.
full_run_confirmed: false

# Khi true, pipeline bỏ qua báo cáo đã xử lý thành công trong audit.
resume: true
```

To switch from sample to full, edit only `config/run_profile.yaml`:

```yaml
# Đổi đúng một chỗ này để chạy full.
run_mode: full

# Bắt buộc xác nhận rõ ràng để tránh bấm nhầm.
full_run_confirmed: true
```

No source code should be edited to switch from sample to full.

## 11. Acceptance Criteria

Phase 1 is acceptable when:
- one report can be converted into clean CSV tables;
- linked text contains valid `TABLE_REF` entries;
- metadata and audit files are generated;
- all generated CSV files reopen with Pandas;
- unit tests pass.

Phase 2 is acceptable when:
- corpus is built from approved Phase 1 artifacts;
- BM25 baseline works;
- dense retrieval interface works;
- reranker returns top-k evidence tables;
- retrieval eval reports Recall@10, Recall@50, MRR, and missing evidence rate.

Phase 3 is acceptable when:
- evidence CSV files load into `dfs`;
- schema-aware grounding returns selected cells with confidence;
- direct lookup questions work;
- arithmetic questions work through Pandas;
- multi-hop flow can request the next retrieval requirement;
- verifier catches wrong table, row, column, cell, unit, sign, formula, and rounding errors.
