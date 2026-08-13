# 07 - Phase 4: Evaluation, UI, and Optimization

## 1. Objective
Build evaluation and user-facing tools that expose evidence, selected cells, calculation trace and verification status.

## 2. Evaluation Artifacts

```text
<eval_root>/golden_questions.csv
<eval_root>/golden_evidence_tables.csv
<eval_root>/golden_answers.csv
<eval_root>/retrieval_eval.csv
<eval_root>/qa_eval.csv
<eval_root>/error_analysis.csv
```

## 3. Error Taxonomy

```text
E_NUMERICAL_EXTRACTION: wrong row, column or cell
I_INSUFFICIENT_EVIDENCE: missing required table
T_TECHNICAL_ERROR: code crash, key error or sandbox error
C_CALCULATION_ERROR: arithmetic error
F_FORMULA_ERROR: wrong financial formula
U_UNVERIFIED: verifier cannot confirm answer
```

## 4. Retrieval Metrics

```text
Recall@10
Recall@50
MRR
missing_evidence_rate
reranker_hit_rate
latency_ms
```

## 5. QA Metrics

```text
exact_numeric_accuracy
tolerance_numeric_accuracy
unit_conversion_accuracy
verified_answer_rate
error_type_distribution
```

## 6. UI Requirements
The UI must show:
- user question;
- extracted intent;
- top evidence tables;
- CSV table preview;
- selected row, column and cell;
- raw values;
- parsed values;
- calculation trace;
- final answer;
- verifier status;
- feedback button.

## 7. API Requirements

```text
POST /preprocess/sample
POST /retrieval/search
POST /qa/answer
GET  /tables/{table_id}
GET  /runs/{run_id}/evidence
POST /feedback
```

## 8. Feedback Log Schema

```text
run_id
question
answer
retrieved_table_ids
selected_cells_json
verifier_status
user_rating
user_comment
error_type
created_at
```

## 9. Optimization Priorities
1. Improve missing evidence rate with metadata filtering, Qwen3-Embedding-8B retrieval and reranker.
2. Improve numerical extraction with stronger cell grounding.
3. Improve technical reliability with sandbox restrictions and CoT fallback.
4. Improve formula correctness with reusable financial calculation tools.

## 10. Implementation Steps

### Step 1 - Golden Eval Files
Create golden files with:
- query_id;
- question;
- required table_ids;
- expected numeric answer;
- expected unit;
- difficulty level.

### Step 2 - Retrieval Eval
Generate `retrieval_eval.csv` with:
- query_id;
- retrieved table ids;
- gold table ids;
- hit@10;
- hit@50;
- reciprocal rank;
- missing evidence flag.

### Step 3 - QA Eval
Generate `qa_eval.csv` with:
- query_id;
- predicted answer;
- expected answer;
- absolute error;
- relative error;
- unit match;
- verification status;
- error type.

### Step 4 - Evidence Viewer UI
UI must display:
- question;
- intent;
- evidence table list;
- selected CSV preview;
- highlighted row/column/cell;
- calculation trace;
- verifier result.

### Step 5 - Feedback Loop
Feedback must write append-only logs. Do not overwrite previous run logs.

## 11. Run Scope Policy
Phase 4 must not define its own sample/full data scope.

Phase 4 displays and evaluates traces produced by Phase 3.

```text
config/run_profile.yaml
-> Phase 1 selected reports
-> Phase 2 selected retrieval index
-> Phase 3 saved QA traces
-> Phase 4 evaluation and UI
```

If the user wants to move from sample demo to full demo, change only `config/run_profile.yaml`, rerun the pipeline, then open the updated evaluation/UI outputs.

Recommended UI development checks:
- first render 1 saved QA run;
- then connect retrieval;
- then connect QA traces;
- then enable feedback logging.

```text
# Ghi chú:
# UI không tự quyết định sample hay full.
# UI chỉ đọc các artifact đã được pipeline tạo ra.
# Muốn đổi sample/full thì đổi duy nhất config/run_profile.yaml.
```

## 12. Review Gate
Phase 4 can move forward only after:
- eval files load correctly;
- retrieval eval runs on sample questions;
- QA eval runs on sample answers;
- UI can show evidence table and selected cell;
- feedback log is created.

## 13. Anti-Patterns
Do not:
- show only final answer without evidence;
- mix retrieval errors and QA errors in one metric;
- overwrite eval history;
- allow feedback without run_id.
