# 03 - Technology Stack

## 1. Core Libraries

```text
Python
pandas
numpy
beautifulsoup4
lxml
scikit-learn
rapidfuzz
pytest
```

## 2. Preprocessing Libraries
- `beautifulsoup4`: parse and extract HTML tables.
- `lxml`: robust HTML parser.
- `pandas`: table normalization and CSV output.
- `re`: page markers, numeric strings, units, OCR noise.
- `pathlib`: deterministic path handling.
- `csv` or `pandas.to_csv`: metadata and audit outputs.

## 3. Retrieval Libraries

Priority:

```text
1. BM25 baseline
2. Qwen3-Embedding-8B dense retrieval
3. Reranker
```

Fallback:

```text
Qwen3-Embedding-4B
BGE-M3
BM25-only
```

Artifacts:

```text
BM25 index: pickle
Embeddings: parquet or jsonl
Candidates: csv
Reranked results: csv
Eval metrics: csv
```

## 4. Reasoning Libraries
- `pandas`: calculation runtime.
- `ast`: inspect generated code before sandbox execution.
- `math`: safe arithmetic helpers.
- `json`: evidence packages and traces.
- LLM client: configured later, not required for Phase 1.

## 5. Evaluation Libraries
- `pytest`: unit tests.
- `pandas`: metric reports.
- `numpy`: numeric comparison and tolerance.

## 6. Retrieval Benchmark Targets

```text
BM25                              Recall@10 47.41%
BGE-M3                            Recall@10 53.05%
Qwen3-Embedding-4B                Recall@10 63.90%
Qwen3-Embedding-8B                Recall@10 67.48%
Qwen3-Embedding-4B + Reranker     Recall@10 80.19%
Qwen3-Embedding-8B + Reranker     Recall@10 80.80%
```

## 7. Non-goals
Do not add dependencies for:
- SQL database storage;
- database ORM;
- vector database service;
- distributed job queue;
- UI framework in Phase 1.
