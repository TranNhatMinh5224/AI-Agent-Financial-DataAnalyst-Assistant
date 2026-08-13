# 07 - Phase 4: Evaluation, UI, and Optimization

## 1. Objective
Build evaluation and user-facing tools that expose:
- retrieved evidence tables;
- grounded cells;
- calculation traces;
- verification status;
- final numerical answer.

The UI and evaluation must make the core flow inspectable:

```text
FIND THE RIGHT TABLE
-> FIND THE RIGHT CELL
-> THEN CALCULATE
```

## 2. Evaluation Artifacts

```text
<eval_root>/golden_questions.csv
<eval_root>/golden_evidence_tables.csv
<eval_root>/golden_cells.csv
<eval_root>/golden_answers.csv
<eval_root>/retrieval_eval.csv
<eval_root>/cell_grounding_eval.csv
<eval_root>/qa_eval.csv
<eval_root>/error_analysis.csv
```

`golden_cells.csv` is needed to evaluate whether the system found the correct row, column, and cell, not only the correct final answer.

## 3. Shared Error Taxonomy
Use exactly these codes:

```text
E_NUMERICAL_EXTRACTION: wrong table, row, column, cell, raw value, parsed value, or unit extraction
I_INSUFFICIENT_EVIDENCE: missing required table or evidence
T_TECHNICAL_ERROR: code crash, key error, sandbox error, or runtime error
C_CALCULATION_ERROR: arithmetic error
F_FORMULA_ERROR: wrong financial formula
U_UNVERIFIED: verifier cannot confirm answer
```

Do not create another taxonomy for logs or evaluation.

## 4. Retrieval Metrics

```text
Recall@10
Recall@50
MRR
missing_evidence_rate
reranker_hit_rate
latency_ms
```

Primary retrieval metrics:
- `Recall@10`;
- `Recall@50`;
- `MRR`;
- `missing_evidence_rate`.

## 5. Cell Grounding Metrics

```text
table_match_rate
row_match_rate
column_match_rate
cell_match_rate
numeric_parse_accuracy
unit_match_rate
grounding_confidence_distribution
```

Cell grounding errors should map mainly to:
- `E_NUMERICAL_EXTRACTION`;
- `I_INSUFFICIENT_EVIDENCE`.

## 6. QA Metrics

```text
exact_numeric_accuracy
tolerance_numeric_accuracy
unit_conversion_accuracy
verified_answer_rate
invalid_answer_rate
error_type_distribution
```

Separate retrieval failures, cell grounding failures, reasoning failures, and verification failures in the error analysis.

## 7. UI Requirements
The UI must show:
- user question;
- extracted intent;
- top evidence tables;
- retrieval scores;
- CSV table preview;
- grounded row, column, and cell;
- raw values;
- parsed values;
- grounding confidence;
- reasoning strategy;
- calculation trace;
- final answer;
- verifier status;
- error type;
- feedback button.

Do not show only the final answer without evidence.

## 8. API Requirements

```text
POST /preprocess/sample
POST /retrieval/search
POST /qa/answer
GET  /tables/{table_id}
GET  /runs/{run_id}/evidence
GET  /runs/{run_id}/cell-grounding
GET  /runs/{run_id}/verification
POST /feedback
```

The API reads artifacts. It does not introduce a database storage layer.

## 9. Feedback Log Schema

```text
run_id
question
answer
retrieved_table_ids
grounded_cells_json
selected_cells_json
reasoning_strategy
verifier_status
user_rating
user_comment
error_type
created_at
```

Feedback logs must be append-only.

## 10. Optimization Priorities
Prioritize fixes in this order:

```text
correctness
-> retrieval recall
-> cell grounding
-> reasoning reliability
-> engineering simplicity
```

Practical priorities:
1. Reduce `missing_evidence_rate` with metadata filtering, Qwen3-Embedding-8B retrieval, and reranker.
2. Improve `cell_match_rate` with stronger schema-aware grounding.
3. Improve numerical extraction with row/column confidence thresholds.
4. Improve technical reliability with sandbox restrictions and CoT fallback.
5. Improve formula correctness with reusable financial calculation tools.

## 11. Implementation Steps

### Step 1 - Golden Eval Files
Create golden files with:
- `query_id`;
- question;
- required table ids;
- expected row labels;
- expected column labels;
- expected raw values when available;
- expected numeric answer;
- expected unit;
- difficulty level.

### Step 2 - Retrieval Eval
Generate `retrieval_eval.csv` with:
- `query_id`;
- retrieved table ids;
- gold table ids;
- hit@10;
- hit@50;
- reciprocal rank;
- missing evidence flag.

### Step 3 - Cell Grounding Eval
Generate `cell_grounding_eval.csv` with:
- `query_id`;
- predicted table id;
- predicted row label;
- predicted column label;
- predicted raw value;
- predicted parsed value;
- predicted unit;
- gold table id;
- gold row label;
- gold column label;
- cell match flag;
- error type.

### Step 4 - QA Eval
Generate `qa_eval.csv` with:
- `query_id`;
- predicted answer;
- expected answer;
- absolute error;
- relative error;
- unit match;
- reasoning strategy;
- verification status;
- error type.

### Step 5 - Error Analysis
Generate `error_analysis.csv` grouped by:
- retrieval failure;
- cell grounding failure;
- reasoning failure;
- verification failure;
- difficulty level;
- report type;
- ticker.

### Step 6 - Evidence Viewer UI
UI must display:
- question;
- intent;
- evidence table list;
- selected CSV preview;
- highlighted row/column/cell;
- calculation trace;
- verifier result.

### Step 7 - Feedback Loop
Feedback must write append-only logs. Do not overwrite previous run logs.

## 12. Run Scope Policy
Phase 4 must not define its own sample/full data scope.

```text
config/run_profile.yaml
-> Phase 1 selected reports
-> Phase 2 selected retrieval index
-> Phase 3 saved QA traces
-> Phase 4 evaluation and UI
```

If the user wants to move from sample demo to full demo, change only `config/run_profile.yaml`, rerun the pipeline, then open the updated evaluation/UI outputs.

```text
# Ghi chú:
# UI không tự quyết định sample hay full.
# UI chỉ đọc các artifact đã được pipeline tạo ra.
# Muốn đổi sample/full thì đổi duy nhất config/run_profile.yaml.
```

## 13. Review Gate
Phase 4 can move forward only after:
- eval files load correctly;
- retrieval eval runs on sample questions;
- cell grounding eval runs on sample questions;
- QA eval runs on sample answers;
- UI can show evidence table and grounded cell;
- feedback log is created.

## 14. Anti-Patterns
Do not:
- show only final answer without evidence;
- mix retrieval errors, grounding errors, and QA errors in one undifferentiated metric;
- overwrite eval history;
- allow feedback without `run_id`;
- add database storage for eval artifacts;
- add complex observability tooling before core errors are measurable.
