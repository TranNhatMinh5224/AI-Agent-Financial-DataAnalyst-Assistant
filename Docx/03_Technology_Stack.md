# 03 - Technology Stack

## 1. Principles
Use the smallest stack that supports:
- high-recall table retrieval;
- schema-aware cell grounding;
- reliable Pandas reasoning;
- strict verification;
- reproducible evaluation.

Do not add technology unless it reduces retrieval error, cell extraction error, reasoning error, verification error, or reproducibility risk.

## 2. Core Libraries

```text
Python
pandas
numpy
beautifulsoup4
lxml
scikit-learn
rapidfuzz
pytest
PyYAML
```

## 3. Preprocessing Libraries
- `beautifulsoup4`: parse and extract HTML tables.
- `lxml`: robust HTML parser.
- `pandas`: DataFrame normalization and CSV output.
- `re`: page markers, numeric strings, units, OCR noise.
- `pathlib`: deterministic path handling.
- `csv` or `pandas.to_csv`: metadata and audit outputs.
- `PyYAML`: read `config/run_profile.yaml`.

Phase 1 uses no LLM, retrieval, embedding, database, or reasoning library.

## 4. Retrieval Libraries

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

Embedding artifact records must include:

```text
table_id
model_name
model_version
embedding_dim
source_text_checksum
created_at
```

No vector database is required. Cached embedding artifacts are enough for the first implementation path.

## 5. Reasoning Libraries
- `pandas`: calculation runtime.
- `ast`: inspect generated code before sandbox execution.
- `math`: safe arithmetic helpers.
- `json`: evidence packages, grounded cells, traces, verification, and answers.
- `rapidfuzz`: row/column matching during cell grounding.
- LLM client: configured later, not required for Phase 1.

## 6. Evaluation Libraries
- `pytest`: unit tests.
- `pandas`: metric reports.
- `numpy`: numeric comparison and tolerance.

## 7. Retrieval Benchmark Targets

```text
BM25                              Recall@10 47.41%
BGE-M3                            Recall@10 53.05%
Qwen3-Embedding-4B                Recall@10 63.90%
Qwen3-Embedding-8B                Recall@10 67.48%
Qwen3-Embedding-4B + Reranker     Recall@10 80.19%
Qwen3-Embedding-8B + Reranker     Recall@10 80.80%
```

Primary retrieval metrics:

```text
Recall@10
Recall@50
MRR
missing_evidence_rate
```

## 8. Shared Error Taxonomy

```text
E_NUMERICAL_EXTRACTION
I_INSUFFICIENT_EVIDENCE
T_TECHNICAL_ERROR
C_CALCULATION_ERROR
F_FORMULA_ERROR
U_UNVERIFIED
```

Use the same codes in reasoning, verification, tests, evaluation, and logs.

## 9. Non-goals
Do not add dependencies for:
- SQL database storage;
- database ORM;
- vector database service;
- distributed job queue;
- Kubernetes;
- microservices;
- complex agent framework;
- UI framework in Phase 1.
