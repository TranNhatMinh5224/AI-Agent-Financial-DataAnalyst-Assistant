# 08 - Task Breakdown and Status

## Status Legend
- [TODO] Not started
- [WIP] In progress
- [DONE] Done
- [NOT USED] Not used

## Current State
The project is **PLAN-ONLY**.

No source code, tests, notebooks, output folders, model downloads, preprocessing outputs, retrieval indexes, QA traces, or database artifacts should exist at this stage.

Implementation starts only after the documentation review is approved.

## Execution Rule
No phase is allowed to run the full dataset by default.

The sample/full data scope is controlled only by:

```text
config/run_profile.yaml
```

Phase 1 preprocessing is the only phase with data-size review gates:

```text
tests only -> 1 report -> 1 ticker -> 5 tickers or 50 reports -> full run after approval
```

Phase 2, Phase 3, and Phase 4 read artifacts produced from the approved Phase 1 scope. They may limit questions for debugging, but they must not redefine sample/full report scope.

When reporting progress, always include:
- current phase;
- current task;
- current run gate;
- maximum allowed run size;
- outputs generated;
- outputs reviewed;
- whether the next larger run is approved.

## 0. Documentation and Direction
- [DONE] **Task 0.1:** Remove early implementation artifacts from the plan direction.
- [DONE] **Task 0.2:** Remove database direction from the implementation plan.
- [DONE] **Task 0.3:** Set Text-to-Pandas as the core architecture.
- [DONE] **Task 0.4:** Keep project status as PLAN-ONLY.

## 1. Phase 1 - Data Preparation and CSV Table Store

### 1.1 Scaffold
- [DONE] **Task 1.1.1:** Create `config/run_profile.yaml` as the single sample/full switch.
- [DONE] **Task 1.1.2:** Create package layout under `src/financial_text_to_pandas`.
- [DONE] **Task 1.1.3:** Create `types.py` with dataclasses.
- [DONE] **Task 1.1.4:** Create preprocessing modules.
- [DONE] **Task 1.1.5:** Create test files.
- [DONE] **Task 1.1.6:** Verify package import.

### 1.2 OCR and Metadata
- [DONE] **Task 1.2.1:** Implement `split_pages`.
- [DONE] **Task 1.2.2:** Test page splitting variants.
- [DONE] **Task 1.2.3:** Implement `infer_report_metadata`.
- [DONE] **Task 1.2.4:** Test consolidated/separate/explanation path inference.

### 1.3 Table Extraction
- [DONE] **Task 1.3.1:** Implement HTML table extraction.
- [DONE] **Task 1.3.2:** Implement deterministic `table_id`.
- [DONE] **Task 1.3.3:** Capture nearby text.
- [DONE] **Task 1.3.4:** Test malformed HTML.

### 1.4 Table Grid Cleaning
- [DONE] **Task 1.4.1:** Implement `rowspan` expansion.
- [DONE] **Task 1.4.2:** Implement `colspan` expansion.
- [DONE] **Task 1.4.3:** Implement grid alignment.
- [DONE] **Task 1.4.4:** Implement empty row/column removal.
- [DONE] **Task 1.4.5:** Add table grid tests.

### 1.5 Header and Context
- [DONE] **Task 1.5.1:** Implement header row scoring.
- [DONE] **Task 1.5.2:** Implement multi-row header flattening.
- [DONE] **Task 1.5.3:** Implement duplicate column handling.
- [DONE] **Task 1.5.4:** Implement `row_label_raw`.
- [DONE] **Task 1.5.5:** Implement `row_label_full`.
- [DONE] **Task 1.5.6:** Add header/context tests.

### 1.6 Number Parsing
- [DONE] **Task 1.6.1:** Implement Vietnamese number parser.
- [DONE] **Task 1.6.2:** Support thousands separators.
- [DONE] **Task 1.6.3:** Support decimal comma.
- [DONE] **Task 1.6.4:** Support percent.
- [DONE] **Task 1.6.5:** Support parentheses negative.
- [DONE] **Task 1.6.6:** Reject dates and text.
- [DONE] **Task 1.6.7:** Add parser tests.

### 1.7 CSV, Metadata, Audit
- [DONE] **Task 1.7.1:** Implement clean table DataFrame builder.
- [DONE] **Task 1.7.2:** Preserve raw value columns.
- [DONE] **Task 1.7.3:** Add `numeric__*` parsed value columns.
- [DONE] **Task 1.7.4:** Implement CSV writer.
- [DONE] **Task 1.7.5:** Implement CSV reopen validator.
- [DONE] **Task 1.7.6:** Implement table metadata writer.
- [DONE] **Task 1.7.7:** Implement report metadata writer.
- [DONE] **Task 1.7.8:** Implement preprocessing audit writer.
- [DONE] **Task 1.7.9:** Add metadata/audit tests.

### 1.8 Linked Text and CLI
- [DONE] **Task 1.8.1:** Implement `TABLE_REF` replacement.
- [DONE] **Task 1.8.2:** Preserve page boundaries in linked text.
- [DONE] **Task 1.8.3:** Implement pipeline CLI reading `config/run_profile.yaml`.
- [DONE] **Task 1.8.4:** Support `--dry-run`.
- [DONE] **Task 1.8.5:** Support `resume` from audit.
- [DONE] **Task 1.8.6:** Review generated CSV and audit files after sample run.

### 1.9 Phase 1 Progressive Run Gates
- [DONE] **Gate P1.0:** Run preprocessing unit tests only. Maximum run size: 0 reports.
- [DONE] **Gate P1.1:** Run one-report smoke test. Maximum run size: 1 report.
- [TODO] **Gate P1.2:** Run one-ticker review. Maximum run size: 1 ticker.
- [TODO] **Gate P1.3:** Run small portfolio review. Maximum run size: 5 tickers or 50 reports.
- [TODO] **Gate P1.4:** Run full corpus only after explicit approval. Maximum run size: full selected corpus.
- [TODO] **Task 1.9.1:** Record command, report count, table count, output paths, and audit summary for every run.
- [TODO] **Task 1.9.2:** Keep failed tables in audit; never silently drop them.
- [TODO] **Task 1.9.3:** Approve or reject the sample before increasing run size.

## 2. Phase 2 - Retrieval Setup
- [DONE] **Task 2.1:** Implement intent-based pre-filtering (`query_hints.py`).
- [DONE] **Task 2.2:** Build initial naive search_text corpus (`corpus.py` to auto-generate `table_corpus.csv`).
- [DONE] **Task 2.3:** Implement BM25 lexical search baseline (`bm25.py`).
- [DONE] **Task 2.4:** Implement Dense Vector search indexing using BGE-M3 (`embeddings.py`).
- [DONE] **Task 2.5:** Ensure metadata filtering works before sparse/dense retrieval.
- [DONE] **Task 2.6:** Implement Hybrid Search combining BM25 and Dense scores.
- [DONE] **Task 2.7:** Implement cross-encoder reranker step.
- [DONE] **Task 2.8:** Implement fallback retrievers.
- [DONE] **Task 2.9:** Merge and deduplicate candidates.
- [DONE] **Task 2.10:** Implement reranker.
- [DONE] **Task 2.11:** Cache reranker scores.
- [DONE] **Task 2.12:** Add retrieval unit tests.
- [DONE] **Task 2.13:** Log retrieval times to metrics.
- [TODO] **Task 2.14:** Read corpus scope from Phase 1 artifacts, not from a separate retrieval setting.
- [TODO] **Task 2.15:** Support `--limit-questions` only for debugging/evaluation speed.

## 3. Phase 3 - Text-to-Pandas QA and Reasoning
- [DONE] **Task 3.1:** Define `EvidencePackage` loading.
- [DONE] **Task 3.2:** Implement question intent parser.
- [DONE] **Task 3.3:** Implement rule-based intent fallbacks.
- [DONE] **Task 3.4:** Implement exact cell grounding matcher.
- [DONE] **Task 3.5:** Implement fuzzy cell grounding matcher.
- [DONE] **Task 3.6:** Implement metadata-assisted cell grounding.
- [DONE] **Task 3.7:** Implement numeric column detection.
- [DONE] **Task 3.8:** Attach confidence scores to grounded cells.
- [DONE] **Task 3.9:** Generate audit trace for cell grounding.
- [DONE] **Task 3.10:** Map missing row/column/cell to `E_NUMERICAL_EXTRACTION`.
- [DONE] **Task 3.11:** Implement adaptive strategy selector.
- [DONE] **Task 3.12:** Implement deterministic direct lookup.
- [DONE] **Task 3.13:** Implement PoT prompt.
- [DONE] **Task 3.14:** Implement CoT prompt and fallback.
- [DONE] **Task 3.15:** Implement Pandas sandbox.
- [DONE] **Task 3.16:** Implement minimal `multi_hop` controller.
- [DONE] **Task 3.17:** Implement financial helper tools.
- [DONE] **Task 3.18:** Implement verifier.
- [DONE] **Task 3.19:** Format final answer.
- [DONE] **Task 3.20:** Add QA, grounding, sandbox, strategy, multi-hop, and verifier tests.
- [DONE] **Task 3.21:** Read evidence scope from Phase 2 artifacts, not from a separate QA setting.
- [DONE] **Task 3.22:** Support `--limit` only for debugging/evaluation speed.
- [DONE] **Task 3.23:** Implement Self-Correction Retry Loop in PoT Strategy (`strategy.py`, `llm.py`, `prompts.py`).
- [DONE] **Task 3.24:** Implement Symbolic Numeric Masking (`[NUM_X]`) in Cell Grounding & PoT Execution (`cell_grounding.py`, `prompts.py`, `sandbox.py`).
- [DONE] **Task 3.25:** Implement Dual Verification (Table vs Text Narrative Alignment) (`verifier.py`, `prompts.py`, `types.py`).
- [DONE] **Task 3.26:** Integrate Multi-Hop Hybrid RAG (Table + Text Notes / Thuyết minh BCTC) (`search.py`, `corpus.py`, `pipeline.py`).
- [DONE] **Task 3.27:** Implement Hierarchical Column Headers (`table_clean.py`).
- [DONE] **Task 3.28:** Enhance Benchmark Evaluation & Error Taxonomy Metrics (`evaluate.py`).
- [DONE] **Task 3.29:** Implement Chain-of-Table Operation Pool & execute_chain (`chain_of_table.py`).
- [DONE] **Task 3.30:** Implement TableRAG Two-Level Schema + Cell Retrieval (`table_rag.py`).
- [DONE] **Task 3.31:** Implement Multi-Agent Orchestrator with Planner/Retriever/Programmer/Critic roles (`orchestrator.py`).

## 4. Phase 4 - Evaluation, UI, and Optimization
- [DONE] **Task 4.1:** Build golden question files (`tests/golden_questions.json`).
- [TODO] **Task 4.2:** Build golden evidence table files.
- [TODO] **Task 4.3:** Build golden cell files.
- [TODO] **Task 4.4:** Build golden answer files.
- [TODO] **Task 4.5:** Implement retrieval eval report.
- [TODO] **Task 4.6:** Implement cell grounding eval report.
- [DONE] **Task 4.7:** Implement QA eval report (`evaluate.py` script ready for execution).
- [TODO] **Task 4.8:** Implement error analysis report.
- [DONE] **Task 4.9:** Implement Streamlit UI / web app (`streamlit_app.py` created).
- [TODO] **Task 4.10:** Implement evidence viewer UI.
- [TODO] **Task 4.11:** Show retrieved tables, grounded cells, calculation trace, and verifier status.
- [TODO] **Task 4.12:** Implement feedback logging.
- [TODO] **Task 4.13:** Read saved traces from Phase 3 artifacts.
- [TODO] **Task 4.14:** Do not add a separate sample/full switch in the UI.

## 5. Official Competition Submission Format & Packaging
- [DONE] **Task 5.1:** Update `types.py` with `EvidenceItem` and `SubmissionItem` matching official competition schema (`id`, `relevant_docs`, `relevant_tables`, `evidence`, `pandas_query`).
- [DONE] **Task 5.2:** Implement `submission.py` with `create_submission_item`, `export_submission_zip`, and `validate_submission_zip`.
- [DONE] **Task 5.3:** Create unit tests in `tests/test_submission.py` verifying ZIP layout, root-level `submission.json`, relative `data/` paths, and schema validation.
- [DONE] **Task 5.4:** Write documentation in `Docx/17_Official_Contest_Submission_Format_and_Packaging_Specification.md`.

## 6. Non-goals
- [NOT USED] Database schema.
- [NOT USED] Database ingestion.
- [NOT USED] Text-to-SQL.
- [NOT USED] Storing cleaned tables in a database.
- [NOT USED] Vector database service.
- [NOT USED] Complex multi-agent orchestration in the first implementation path.
- [NOT USED] Distributed queue.
- [NOT USED] Kubernetes.

## 7. Implementation Milestones Status
- [DONE] Phase 1 Preprocessing Pipeline Execution (AAA sample test & table store verified)
- [DONE] Phase 2 & 3 Multi-Agent Reasoning Chain (CLER Framework & SGLang Serving)
- [DONE] Phase 5 Competition Submission Exporter & ZIP Schema Validator

