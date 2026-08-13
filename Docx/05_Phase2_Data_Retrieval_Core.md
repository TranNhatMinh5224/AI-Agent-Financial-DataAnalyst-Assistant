# 05 - Phase 2: Recall-First Table Retrieval Core

## 1. Objective
Given a financial question, retrieve the top evidence CSV tables required for answering it.

Retrieval is recall-first.

Missing a required table is a critical retrieval failure because cell grounding and reasoning cannot recover evidence that was never retrieved.

## 2. Canonical Flow

```text
Question
-> Query Hints / Metadata Filtering
-> Retriever
-> Candidate Tables
-> Reranker
-> Top-K Evidence Tables
```

Retriever:
- prioritizes recall;
- retrieves a broad candidate set;
- must avoid over-filtering.

Reranker:
- prioritizes precision and ranking quality;
- sorts candidates into final top-k evidence tables.

## 3. Inputs

```text
<output_root>/table_metadata.csv
<output_root>/reports_text_linked/**/*.txt
<output_root>/tables_csv/**/*.csv
ViFinQA/questions.jsonl or <eval_root>/golden_questions.csv
```

Phase 2 reads the artifact scope produced by Phase 1. It must not define a separate sample/full report scope.

## 4. Outputs

```text
<index_root>/table_corpus.csv
<index_root>/bm25_index.pkl
<index_root>/table_embeddings.parquet
<index_root>/retrieval_candidates.csv
<index_root>/retrieval_reranked.csv
<eval_root>/retrieval_eval.csv
```

## 5. Table Corpus Schema

```text
table_id
csv_path
ticker
company_name
year
report_type
statement_type
unit
title
headers_text
row_labels_text
nearby_text
search_text
quality_score
needs_review
```

`search_text` must concatenate:

```text
title
headers_text
row_labels_text
nearby_text
unit
statement_type
ticker
company_name
year
report_type
```

Do not embed full raw CSV content without summarization.

## 6. Query Hints Schema

```text
query_id
question
ticker
company_name
years
report_type
metric_terms
statement_type
unit_requested
operation
confidence
```

Query hints are used for metadata filtering, not final answering.

## 7. Required Functions

```python
build_table_corpus(table_metadata_path: Path, output_path: Path) -> pd.DataFrame
extract_query_hints(question: str) -> QueryHints
filter_by_metadata(corpus: pd.DataFrame, hints: QueryHints) -> pd.DataFrame
build_bm25_index(corpus: pd.DataFrame) -> BM25Index
search_bm25(index: BM25Index, query: str, top_k: int) -> list[Candidate]
embed_tables(corpus: pd.DataFrame, model_name: str, model_version: str) -> EmbeddingStore
embed_query(question: str, model_name: str, model_version: str) -> Vector
search_dense(store: EmbeddingStore, query_vector: Vector, top_k: int) -> list[Candidate]
merge_candidates(*candidate_lists: list[Candidate]) -> list[Candidate]
rerank_candidates(question: str, candidates: list[Candidate], top_k: int) -> list[EvidenceTable]
evaluate_retrieval(predictions: pd.DataFrame, gold: pd.DataFrame) -> RetrievalMetrics
```

## 8. Retrieval Strategy

```text
Step 1: extract query hints
Step 2: metadata filtering
Step 3: BM25 top 50
Step 4: Qwen3-Embedding-8B top 50
Step 5: merge candidates
Step 6: deduplicate by table_id
Step 7: reranker top 10
Step 8: return top-k evidence tables
```

Fallback order:

```text
Qwen3-Embedding-4B
BGE-M3
BM25-only
```

## 9. Embedding Artifact Contract
Embedding artifacts may be cached as Parquet or JSONL files.

Each embedding row must include:

```text
table_id
model_name
model_version
embedding_dim
source_text_checksum
created_at
```

Rules:
- never reuse embeddings when `model_name`, `model_version`, or source checksum differs;
- write model metadata beside the embedding file;
- do not require a vector database.

## 10. Candidate Row Schema

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

## 11. Evaluation Metrics

```text
Recall@10
Recall@50
MRR
missing_evidence_rate
reranker_hit_rate
latency_ms
```

Primary pass/fail metrics:
- `Recall@10`;
- `Recall@50`;
- `MRR`;
- `missing_evidence_rate`.

## 12. Benchmark Targets

```text
BM25                              Recall@10 47.41%
BGE-M3                            Recall@10 53.05%
Qwen3-Embedding-4B                Recall@10 63.90%
Qwen3-Embedding-8B                Recall@10 67.48%
Qwen3-Embedding-4B + Reranker     Recall@10 80.19%
Qwen3-Embedding-8B + Reranker     Recall@10 80.80%
```

## 13. Tests Required
- corpus creation from metadata;
- query hint extraction;
- metadata filtering by ticker;
- metadata filtering by year;
- metadata filtering by report type;
- metadata filter does not over-filter uncertain hints;
- BM25 exact-match ranking;
- dense search interface with mocked embeddings;
- embedding cache rejects mismatched model/version;
- candidate merge and deduplication;
- reranker top-k ordering with mocked scores;
- Recall@K metrics;
- missing evidence rate.

## 14. Implementation Steps

### Step 1 - Corpus Builder
Create `retrieval/corpus.py`.

Rules:
- read Phase 1 `table_metadata.csv`;
- read CSV headers and row labels;
- read nearby text from linked text if available;
- skip `needs_review=true` tables by default;
- allow `--include-review` flag for analysis only;
- generate `search_text`.

### Step 2 - Query Hints
Create `retrieval/query_hints.py`.

Rules:
- extract ticker symbols if present;
- extract company names when available;
- extract years;
- extract report type keywords;
- extract unit hints;
- extract metric terms;
- keep confidence score.

### Step 3 - Metadata Filtering
Create metadata filters before scoring.

Rules:
- exact ticker filter if confidence is high;
- year filter if year is present;
- report_type filter if explicit;
- do not over-filter when hints are uncertain;
- keep filter status for debugging.

### Step 4 - BM25 Baseline
Create `retrieval/bm25.py`.

Rules:
- tokenize Vietnamese and ASCII text consistently;
- build index from `search_text`;
- return top 50 candidates;
- store `bm25_score`.

### Step 5 - Dense Retrieval
Create `retrieval/embeddings.py`.

Rules:
- model name and version are configurable;
- default model is `Qwen3-Embedding-8B`;
- embeddings are cached as file artifacts;
- query embedding uses same model/version;
- return top 50 candidates with `dense_score`.

### Step 6 - Candidate Merge
Create `retrieval/search.py`.

Rules:
- merge BM25 and dense candidates;
- deduplicate by `table_id`;
- preserve all scores;
- preserve retrieval source labels;
- preserve candidate provenance.

### Step 7 - Reranker
Create `retrieval/reranker.py`.

Rules:
- input is question + candidate table summary;
- output top 10 by default;
- preserve `reranker_score`;
- support mocked reranker for tests.

### Step 8 - Evaluation
Create `retrieval/evaluate.py`.

Rules:
- compute Recall@10;
- compute Recall@50;
- compute MRR;
- compute missing evidence rate;
- export `retrieval_eval.csv`.

## 15. Run Scope Policy
Phase 2 reads artifacts created by Phase 1:

```text
config/run_profile.yaml
-> Phase 1 selected reports
-> Phase 1 tables_csv + metadata
-> Phase 2 retrieval corpus and indexes
```

If Phase 1 was run in sample mode, Phase 2 indexes the sample output.

If Phase 1 was run in full mode, Phase 2 indexes the full output.

Question limits are allowed only for debugging/evaluation speed:

```powershell
python -m financial_text_to_pandas.retrieval.search --config config/run_profile.yaml --method bm25 --limit-questions 10 --top-k 10
python -m financial_text_to_pandas.retrieval.search --config config/run_profile.yaml --method hybrid --limit-questions 10 --top-k 10
```

```text
# Ghi chú:
# --limit-questions chỉ giới hạn số câu hỏi dùng để test retrieval.
# Nó không quyết định sample/full dữ liệu báo cáo.
# Sample/full dữ liệu báo cáo đã được quyết định ở Phase 1.
```

## 16. Required CLI Controls
Every Phase 2 command must support:
- `--config`;
- `--limit-questions`;
- `--query-id`;
- `--top-k`;
- `--method bm25|dense|hybrid`;
- `--model-name`;
- `--model-version`;
- `--mock-embeddings` for tests and offline development;
- `--no-reranker` for ablation only.

## 17. Review Gate
Phase 2 can move forward only after:
- corpus is built from approved Phase 1 artifacts;
- BM25 baseline runs;
- dense retrieval interface runs or is mocked;
- reranker returns top 10;
- retrieval evaluation report is generated;
- at least 10 sample questions are manually inspected;
- missing evidence cases are reviewed.

## 18. Anti-Patterns
Do not:
- embed full raw CSV content without summarization;
- ignore metadata filtering;
- over-filter uncertain hints;
- hardcode model paths;
- overwrite embeddings without model/version metadata;
- treat reranker as optional in final retrieval flow;
- add a vector database.
