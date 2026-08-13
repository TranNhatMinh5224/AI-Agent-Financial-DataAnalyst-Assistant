# 01 - Project Plan: AI Financial Data Assistant

## 1. Objective
Build an end-to-end Vietnamese financial question-answering system over ViFinQA reports.

The system must:
- retrieve the correct financial report;
- retrieve the correct evidence table;
- identify the exact row, column, and cell used for the answer;
- load evidence CSV files into Pandas;
- calculate with deterministic code when needed;
- verify the answer before returning it;
- return a numeric answer with traceable evidence.

## 2. Architecture Decision
Use **Text-to-Pandas**.

Do not implement:
- Text-to-SQL;
- relational database schema for cleaned financial tables;
- database ingestion for cleaned table data;
- vector database in the first implementation milestone.

Implement:
- OCR TXT preprocessing;
- clean CSV table store;
- linked text files containing `TABLE_REF`;
- table metadata and audit files;
- table retrieval using BM25 + Qwen3-Embedding-8B + reranker;
- Pandas-based reasoning;
- answer verification.

## 3. End-to-End Flow

```text
User question
-> intent extraction and metadata hints
-> table metadata filtering
-> BM25 candidate retrieval
-> Qwen3-Embedding-8B dense candidate retrieval
-> candidate merge and deduplication
-> reranker
-> top-k evidence tables
-> load CSV evidence into Pandas
-> cell grounding
-> deterministic lookup / CoT / PoT
-> verifier
-> final numeric answer + citation
```

## 4. Target Package Layout
Create this layout only when implementation starts:

```text
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
    prompts.py
    sandbox.py
    tools.py
    verifier.py
    answer.py
  eval/
    __init__.py
    golden.py
    metrics.py
tests/
```

Do not create output folders during scaffold. Output folders are created only by runtime commands.

## 5. Runtime Output Contract

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

Phase 3 creates:

```text
<runs_root>/{run_id}/evidence_package.json
<runs_root>/{run_id}/reasoning_trace.json
<runs_root>/{run_id}/verification.json
<runs_root>/{run_id}/answer.json
```

## 6. Retrieval Policy

Default stack:

```text
Lexical baseline: BM25
Dense retriever: Qwen3-Embedding-8B
Fallback dense retriever: Qwen3-Embedding-4B
Fallback multilingual baseline: BGE-M3
Reranker: required
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

## 7. Implementation Rules
- Generate code only after this plan is approved.
- Start with Phase 1 sample mode only.
- Process one report first, not the full dataset.
- Never run a full dataset job by default.
- Every phase must define a small review run before a larger run.
- A larger run starts only after the previous review gate is approved.
- Do not create database code.
- Do not create output folders at scaffold time.
- Every CSV output must be readable by `pd.read_csv`.
- Every table must have a stable `table_id`.
- Every final answer must include evidence metadata.
- Every generated module must have unit tests.

## 8. Run Scope Policy
The sample/full execution switch belongs to **Phase 1 preprocessing**.

Reason:
- Phase 1 is the expensive data-building step.
- Phase 1 determines the quality of CSV tables, linked text, metadata, and audit files.
- Phase 2, Phase 3, and Phase 4 should consume the approved Phase 1 artifacts instead of redefining their own dataset scope.
- A full pipeline run should require changing one central setting only.

### 8.1 Single Source of Truth
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

### 8.2 Scope Resolution
All pipeline stages must read the same resolved scope from `run_profile.yaml`.

```text
run_profile.yaml
-> resolve report scope
-> Phase 1 preprocess selected reports
-> Phase 2 build retrieval corpus from Phase 1 outputs
-> Phase 3 answer from retrieved CSV evidence
-> Phase 4 evaluate and display saved traces
```

### 8.3 Preprocessing Review Gates
Only Phase 1 needs data-size gates:

```text
Gate P1.0: unit tests only, no output data
Gate P1.1: run_mode=sample, sample_limit_reports=1
Gate P1.2: run_mode=sample, sample_tickers=[one ticker], no report limit
Gate P1.3: run_mode=sample, sample_tickers=[5 representative tickers]
Gate P1.4: run_mode=full, full_run_confirmed=true
```

### 8.4 One-Place Full Run Rule
To switch from sample to full, edit only `config/run_profile.yaml`:

```yaml
# Đổi đúng một chỗ này để chạy full.
run_mode: full

# Bắt buộc xác nhận rõ ràng để tránh bấm nhầm.
full_run_confirmed: true
```

No source code should be edited to switch from sample to full.

### 8.5 Gate Output
Every preprocessing gate must report:
- command used;
- current `run_mode`;
- resolved ticker/report scope;
- number of reports processed;
- number of tables extracted;
- number of CSV files written;
- audit success/failure counts;
- sample files to review before increasing scope.

## 9. Code Generation Workflow
Antigravity must generate code phase by phase. Do not generate the whole system in one pass.

Recommended order:

```text
1. Generate Phase 1 package skeleton and dataclasses.
2. Generate Phase 1 pure functions and unit tests.
3. Generate Phase 1 CLI sample command.
4. Run sample on 1 report and review outputs.
5. Only after approval, generate Phase 2 retrieval modules.
6. Only after retrieval eval works, generate Phase 3 QA modules.
7. Only after QA eval works, generate Phase 4 UI/API.
```

Each generated step must include:
- files created or modified;
- tests added;
- command to run;
- expected output;
- maximum run size for that step;
- validation checklist;
- rollback-safe behavior.

## 10. Acceptance Criteria
Phase 1 is acceptable when:
- one report can be converted into clean CSV tables;
- linked text contains valid `TABLE_REF` entries;
- metadata and audit files are generated;
- all generated CSV files reopen with Pandas;
- unit tests pass.

Phase 2 is acceptable when:
- corpus is built from table metadata;
- BM25 baseline works;
- Qwen3-Embedding-8B retrieval interface works;
- reranker produces top-k tables;
- Recall@10 and Recall@50 are reported.

Phase 3 is acceptable when:
- evidence CSV files load into `dfs`;
- direct lookup questions work;
- arithmetic questions work through Pandas;
- verifier catches wrong cell, wrong unit, wrong sign, and rounding errors.
