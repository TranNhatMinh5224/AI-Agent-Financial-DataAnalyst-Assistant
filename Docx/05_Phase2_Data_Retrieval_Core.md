# 05 - Phase 2: Table Retrieval Core

## 1. Objective
Given a financial question, retrieve the top evidence CSV tables required for answering it.

Optimize recall first. Missing a required evidence table should be treated as a critical retrieval failure.

## 2. Inputs

```text
<output_root>/table_metadata.csv
<output_root>/reports_text_linked/**/*.txt
<output_root>/tables_csv/**/*.csv
ViFinQA/questions.jsonl or <eval_root>/golden_questions.csv
```

## 3. Outputs

```text
<index_root>/table_corpus.csv
<index_root>/bm25_index.pkl
<index_root>/table_embeddings.parquet
<index_root>/retrieval_candidates.csv
<index_root>/retrieval_reranked.csv
<eval_root>/retrieval_eval.csv
```

## 4. Table Corpus Schema

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

## 5. Query Hints Schema

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

## 6. Required Functions

```python
build_table_corpus(table_metadata_path: Path, output_path: Path) -> pd.DataFrame
extract_query_hints(question: str) -> QueryHints
filter_by_metadata(corpus: pd.DataFrame, hints: QueryHints) -> pd.DataFrame
build_bm25_index(corpus: pd.DataFrame) -> BM25Index
search_bm25(index: BM25Index, query: str, top_k: int) -> list[Candidate]
embed_tables(corpus: pd.DataFrame, model_name: str) -> EmbeddingStore
embed_query(question: str, model_name: str) -> Vector
search_dense(store: EmbeddingStore, query_vector: Vector, top_k: int) -> list[Candidate]
merge_candidates(*candidate_lists: list[Candidate]) -> list[Candidate]
rerank_candidates(question: str, candidates: list[Candidate], top_k: int) -> list[EvidenceTable]
evaluate_retrieval(predictions: pd.DataFrame, gold: pd.DataFrame) -> RetrievalMetrics
```

## 7. Retrieval Strategy

```text
Step 1: extract query hints
Step 2: metadata filtering
Step 3: BM25 top 50
Step 4: Qwen3-Embedding-8B top 50
Step 5: merge candidates
Step 6: deduplicate by table_id
Step 7: reranker top 10
Step 8: return evidence tables
```

Fallback order:

```text
Qwen3-Embedding-4B
BGE-M3
BM25-only
```

## 8. Benchmark Targets

```text
BM25                              Recall@10 47.41%
BGE-M3                            Recall@10 53.05%
Qwen3-Embedding-4B                Recall@10 63.90%
Qwen3-Embedding-8B                Recall@10 67.48%
Qwen3-Embedding-4B + Reranker     Recall@10 80.19%
Qwen3-Embedding-8B + Reranker     Recall@10 80.80%
```

## 9. Candidate Row Schema

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
created_at
```

## 10. Evaluation Metrics

```text
Recall@10
Recall@50
MRR
missing_evidence_rate
reranker_hit_rate
latency_ms
```

## 11. Tests Required
- corpus creation from metadata;
- query hint extraction;
- metadata filtering by ticker;
- metadata filtering by year;
- metadata filtering by report type;
- BM25 exact-match ranking;
- dense search interface with mocked embeddings;
- candidate merge and deduplication;
- reranker top-k ordering with mocked scores;
- Recall@K metrics.

## 12. Implementation Steps

### Step 1 - Corpus Builder
Create `retrieval/corpus.py`.

Inputs:

```text
table_metadata.csv
tables_csv/**/*.csv
reports_text_linked/**/*.txt
```

Output:

```text
table_corpus.csv
```

Rules:
- skip `needs_review=true` tables by default;
- allow `--include-review` flag;
- read CSV headers and row labels;
- truncate very long row label text safely;
- generate `search_text`.

### Step 2 - Query Hints
Create `retrieval/query_hints.py`.

Rules:
- extract ticker symbols if present;
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
- do not over-filter when hints are uncertain.

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
- model name is configurable;
- default model is `Qwen3-Embedding-8B`;
- embeddings are cached as file artifacts;
- query embedding uses same model;
- return top 50 candidates with `dense_score`.

### Step 6 - Candidate Merge
Create `retrieval/search.py`.

Rules:
- merge BM25 and dense candidates;
- deduplicate by `table_id`;
- preserve all scores;
- preserve retrieval source labels.

### Step 7 - Reranker
Create `retrieval/reranker.py`.

Rules:
- input is question + candidate table summary;
- output top 10;
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

## 13. Run Scope Policy
Phase 2 must not define its own sample/full data scope.

Phase 2 reads the artifacts created by Phase 1:

```text
Phase 1 output_root
-> table_metadata.csv
-> reports_text_linked
-> tables_csv
-> Phase 2 retrieval corpus and indexes
```

If Phase 1 was run in sample mode, Phase 2 automatically builds retrieval artifacts from that sample output.

If Phase 1 was run in full mode, Phase 2 automatically builds retrieval artifacts from the full output.

No retrieval source code should be edited to switch between sample and full data. The only data-scope switch is `config/run_profile.yaml` in Phase 1.

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

## 14. Required CLI Controls
Every Phase 2 command must support:
- `--limit-questions`;
- `--query-id`;
- `--top-k`;
- `--method bm25|dense|hybrid`;
- `--model-name`;
- `--mock-embeddings` for tests and offline development;
- `--no-reranker` for ablation only.

## 15. Review Gate
Phase 2 can move forward only after:
- BM25 baseline runs on sample corpus;
- dense retrieval interface runs or is mocked;
- reranker returns top 10;
- retrieval evaluation report is generated;
- at least 10 sample questions are manually inspected.

## 16. Anti-Patterns
Do not:
- embed full raw CSV content without summarization;
- ignore metadata filtering;
- hardcode model paths;
- overwrite embeddings without model/version metadata;
- treat reranker as optional in final retrieval flow.
