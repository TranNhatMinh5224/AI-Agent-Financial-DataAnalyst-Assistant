# 08 - Task Breakdown and Status

## Status Legend
- [TODO] Not started
- [WIP] In progress
- [DONE] Done
- [NOT USED] Not used

## Current State
The project is **plan-only**.

No source code, tests, notebooks, output folders or database artifacts should exist at this stage. Implementation starts only after this specification is approved.

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

Phase 2, Phase 3, and Phase 4 must read artifacts produced from the approved Phase 1 scope. They may limit questions for debugging, but they must not redefine sample/full report scope.

When reporting progress, always include:
- current phase;
- current task;
- current run gate;
- maximum allowed run size;
- outputs generated;
- outputs reviewed;
- whether the next larger run is approved.

## 0. Reset
- [DONE] **Task 0.1:** Remove early implementation artifacts: `src`, `tests`, `notebooks`, `data`, `pyproject.toml`.
- [DONE] **Task 0.2:** Remove database direction from the implementation plan.
- [DONE] **Task 0.3:** Rewrite planning documents as Antigravity-ready implementation specs.

## 1. Phase 1 - Preprocessing Sample Mode

### 1.1 Scaffold
- [TODO] **Task 1.1.1:** Create `config/run_profile.yaml` as the single sample/full switch.
- [TODO] **Task 1.1.2:** Create package layout under `src/financial_text_to_pandas`.
- [TODO] **Task 1.1.3:** Create `types.py` with dataclasses.
- [TODO] **Task 1.1.4:** Create preprocessing modules.
- [TODO] **Task 1.1.5:** Create test files.
- [TODO] **Task 1.1.6:** Verify package import.

### 1.2 OCR and Metadata
- [TODO] **Task 1.2.1:** Implement `split_pages`.
- [TODO] **Task 1.2.2:** Test page splitting variants.
- [TODO] **Task 1.2.3:** Implement `infer_report_metadata`.
- [TODO] **Task 1.2.4:** Test consolidated/separate/explanation path inference.

### 1.3 Table Extraction
- [TODO] **Task 1.3.1:** Implement HTML table extraction.
- [TODO] **Task 1.3.2:** Implement deterministic `table_id`.
- [TODO] **Task 1.3.3:** Capture nearby text.
- [TODO] **Task 1.3.4:** Test malformed HTML.

### 1.4 Table Grid Cleaning
- [TODO] **Task 1.4.1:** Implement `rowspan` expansion.
- [TODO] **Task 1.4.2:** Implement `colspan` expansion.
- [TODO] **Task 1.4.3:** Implement grid alignment.
- [TODO] **Task 1.4.4:** Implement empty row/column removal.
- [TODO] **Task 1.4.5:** Add table grid tests.

### 1.5 Header and Context
- [TODO] **Task 1.5.1:** Implement header row scoring.
- [TODO] **Task 1.5.2:** Implement multi-row header flattening.
- [TODO] **Task 1.5.3:** Implement duplicate column handling.
- [TODO] **Task 1.5.4:** Implement `row_label_full`.
- [TODO] **Task 1.5.5:** Add header/context tests.

### 1.6 Number Parsing
- [TODO] **Task 1.6.1:** Implement Vietnamese number parser.
- [TODO] **Task 1.6.2:** Support thousands separators.
- [TODO] **Task 1.6.3:** Support decimal comma.
- [TODO] **Task 1.6.4:** Support percent.
- [TODO] **Task 1.6.5:** Support parentheses negative.
- [TODO] **Task 1.6.6:** Reject dates and text.
- [TODO] **Task 1.6.7:** Add parser tests.

### 1.7 CSV, Metadata, Audit
- [TODO] **Task 1.7.1:** Implement clean table DataFrame builder.
- [TODO] **Task 1.7.2:** Implement CSV writer.
- [TODO] **Task 1.7.3:** Implement CSV reopen validator.
- [TODO] **Task 1.7.4:** Implement table metadata writer.
- [TODO] **Task 1.7.5:** Implement report metadata writer.
- [TODO] **Task 1.7.6:** Implement preprocessing audit writer.
- [TODO] **Task 1.7.7:** Add metadata/audit tests.

### 1.8 Linked Text and CLI
- [TODO] **Task 1.8.1:** Implement `TABLE_REF` replacement.
- [TODO] **Task 1.8.2:** Preserve page boundaries in linked text.
- [TODO] **Task 1.8.3:** Implement sample CLI.
- [TODO] **Task 1.8.4:** Run sample command on one report.
- [TODO] **Task 1.8.5:** Review generated CSV and audit files.

### 1.9 Phase 1 Progressive Run Gates
- [TODO] **Gate P1.0:** Run preprocessing unit tests only. Maximum run size: 0 reports.
- [TODO] **Gate P1.1:** Run one-report smoke test. Maximum run size: 1 report.
- [TODO] **Gate P1.2:** Run one-ticker review. Maximum run size: 1 ticker.
- [TODO] **Gate P1.3:** Run small portfolio review. Maximum run size: 5 tickers or 50 reports.
- [TODO] **Gate P1.4:** Run full corpus only after explicit approval. Maximum run size: full selected corpus.
- [TODO] **Task 1.9.1:** Record command, report count, table count, output paths and audit summary for every run.
- [TODO] **Task 1.9.2:** Keep failed tables in audit; never silently drop them.
- [TODO] **Task 1.9.3:** Approve or reject the sample before increasing run size.

## 2. Phase 2 - Table Retrieval
- [TODO] **Task 2.1:** Build `table_corpus.csv`.
- [TODO] **Task 2.2:** Implement query hint extraction.
- [TODO] **Task 2.3:** Implement metadata filtering.
- [TODO] **Task 2.4:** Implement BM25 baseline.
- [TODO] **Task 2.5:** Implement Qwen3-Embedding-8B dense retrieval.
- [TODO] **Task 2.6:** Implement fallback retrievers.
- [TODO] **Task 2.7:** Merge and deduplicate candidates.
- [TODO] **Task 2.8:** Implement reranker.
- [TODO] **Task 2.9:** Export candidates and reranked results.
- [TODO] **Task 2.10:** Evaluate Recall@10, Recall@50, MRR.
- [TODO] **Task 2.11:** Compare benchmark targets.
- [TODO] **Task 2.12:** Read corpus scope from Phase 1 artifacts, not from a separate retrieval setting.
- [TODO] **Task 2.13:** Support `--limit-questions` only for debugging/evaluation speed.

## 3. Phase 3 - Text-to-Pandas QA
- [TODO] **Task 3.1:** Implement evidence package schema.
- [TODO] **Task 3.2:** Load CSV evidence into `dfs`.
- [TODO] **Task 3.3:** Build table summaries.
- [TODO] **Task 3.4:** Parse user intent.
- [TODO] **Task 3.5:** Select reasoning strategy.
- [TODO] **Task 3.6:** Implement deterministic lookup.
- [TODO] **Task 3.7:** Implement CoT prompt.
- [TODO] **Task 3.8:** Implement PoT prompt.
- [TODO] **Task 3.9:** Implement Pandas sandbox.
- [TODO] **Task 3.10:** Implement financial helper tools.
- [TODO] **Task 3.11:** Implement verifier.
- [TODO] **Task 3.12:** Format final answer.
- [TODO] **Task 3.13:** Add QA tests.
- [TODO] **Task 3.14:** Read evidence scope from Phase 2 artifacts, not from a separate QA setting.
- [TODO] **Task 3.15:** Support `--limit` only for debugging/evaluation speed.

## 4. Phase 4 - Evaluation and UI
- [TODO] **Task 4.1:** Build golden eval files.
- [TODO] **Task 4.2:** Implement retrieval eval report.
- [TODO] **Task 4.3:** Implement QA eval report.
- [TODO] **Task 4.4:** Implement error analysis report.
- [TODO] **Task 4.5:** Implement evidence viewer UI.
- [TODO] **Task 4.6:** Implement feedback logging.
- [TODO] **Task 4.7:** Read saved traces from Phase 3 artifacts.
- [TODO] **Task 4.8:** Do not add a separate sample/full switch in the UI.

## 5. Non-goals
- [NOT USED] Database schema.
- [NOT USED] Database ingestion.
- [NOT USED] Text-to-SQL.
- [NOT USED] Storing cleaned tables in a database.

## 6. First Implementation Milestone
After approval, implement only Phase 1 sample mode:

```text
Input: 1 report
Output: clean CSV tables, linked text, table metadata, report metadata, preprocessing audit
Tests: preprocessing unit tests + CSV reopen validation
Maximum run size before review: 1 report
```
