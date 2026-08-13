# 06 - Phase 3: Text-to-Pandas QA and Multi-Agent Flow

## 1. Objective
Answer financial questions using retrieved CSV evidence tables and Pandas.

The system must answer from selected CSV cells and calculation traces, not from model memory.

## 2. Inputs

```text
question
top_k evidence tables
table_metadata rows
linked text snippets
```

## 3. Evidence Package Schema

```json
{
  "query_id": "string",
  "question": "string",
  "intent": {
    "ticker": "string|null",
    "company_name": "string|null",
    "years": ["int"],
    "report_type": "consolidated|separate|unknown",
    "metrics": ["string"],
    "unit_requested": "string|null",
    "operation": "lookup|difference|growth_rate|ratio|mean|median|multi_hop|unknown"
  },
  "tables": [
    {
      "table_id": "string",
      "csv_path": "string",
      "metadata": {},
      "retrieval_scores": {}
    }
  ],
  "linked_text_context": ["string"]
}
```

## 4. Required Modules

```text
reasoning/evidence.py
reasoning/intent.py
reasoning/prompts.py
reasoning/sandbox.py
reasoning/tools.py
reasoning/verifier.py
reasoning/answer.py
```

## 5. Required Functions

```python
load_evidence_tables(package: EvidencePackage) -> dict[str, pd.DataFrame]
build_table_summary(df: pd.DataFrame, metadata: dict) -> TableSummary
extract_intent(question: str) -> Intent
choose_reasoning_strategy(intent: Intent, evidence: EvidencePackage) -> Literal["deterministic", "cot", "pot"]
run_deterministic_lookup(intent: Intent, dfs: dict[str, pd.DataFrame]) -> ReasoningResult
build_cot_prompt(package: EvidencePackage) -> str
build_pot_prompt(package: EvidencePackage) -> str
run_pandas_sandbox(code: str, dfs: dict[str, pd.DataFrame]) -> SandboxResult
verify_answer(result: ReasoningResult, package: EvidencePackage) -> VerificationResult
format_final_answer(result: ReasoningResult, verification: VerificationResult) -> FinalAnswer
```

## 6. Pandas Sandbox Contract

Generated code may use:

```text
pd
dfs
parse_vn_number()
normalize_unit()
safe_get_cell()
```

Generated code must:
- assign the final value to `result`;
- avoid imports;
- avoid file access;
- avoid network access;
- avoid mutation outside local variables;
- keep raw row and column labels unchanged;
- not round intermediate values.

## 7. CoT Contract

Use CoT when:
- question is direct lookup;
- evidence table is simple;
- model is not reliable for code generation;
- fallback is needed after sandbox error.

CoT output must include:
- selected table_id;
- selected row label;
- selected column label;
- raw value;
- parsed value;
- final numeric answer.

## 8. PoT Contract

Use PoT when:
- question needs arithmetic;
- question needs grouping;
- question needs multiple tables;
- Pandas operations are safer than natural-language arithmetic.

PoT code pattern:

```python
df = dfs["table_id"]
# locate row and column
# parse value
# calculate
result = ...
```

## 9. Verification Schema

```json
{
  "is_valid": true,
  "error_type": null,
  "checked_cells": [
    {
      "table_id": "string",
      "row_label": "string",
      "column_label": "string",
      "raw_value": "string",
      "parsed_value": 0.0,
      "unit": "string"
    }
  ],
  "calculation_check": "string",
  "final_answer": 0.0
}
```

Error types:

```text
E_NUMERICAL_EXTRACTION
I_INSUFFICIENT_EVIDENCE
T_TECHNICAL_ERROR
C_CALCULATION_ERROR
F_FORMULA_ERROR
U_UNVERIFIED
```

## 10. Final Answer Schema

```json
{
  "answer": 0.0,
  "answer_type": "numeric",
  "unit": "string|null",
  "citations": [
    {
      "table_id": "string",
      "csv_path": "string",
      "page_number": 0,
      "row_label": "string",
      "column_label": "string"
    }
  ],
  "verification_status": "valid|invalid|unverified",
  "error_type": null
}
```

## 11. Tests Required
- evidence loader loads CSV into `dfs`;
- intent parser extracts ticker, year and metric from sample questions;
- deterministic lookup finds exact row and column;
- sandbox blocks imports;
- sandbox blocks file access;
- sandbox returns `result`;
- verifier catches wrong row;
- verifier catches wrong unit;
- verifier catches wrong sign;
- final answer formatter returns numeric-only when required.

## 12. Implementation Steps

### Step 1 - Evidence Loader
Create `reasoning/evidence.py`.

Rules:
- read each CSV path from evidence package;
- load into `dfs[table_id]`;
- fail clearly if CSV path is missing;
- preserve table metadata.

### Step 2 - Intent Parser
Create `reasoning/intent.py`.

Rules:
- extract ticker/company;
- extract year or period;
- extract metric terms;
- extract requested unit;
- classify operation type.

### Step 3 - Strategy Selector
Create strategy selector.

Rules:
- direct lookup -> deterministic first;
- arithmetic with evidence -> PoT;
- sandbox failure -> CoT fallback;
- missing evidence -> return insufficient evidence.

### Step 4 - Deterministic Lookup
Implement exact and fuzzy row/column matching.

Rules:
- use `row_label_full` first;
- fallback to `row_label_raw`;
- use RapidFuzz for row label matching;
- require confidence threshold;
- return selected cell metadata.

### Step 5 - CoT Prompt
Build a prompt that requires:
- selected table_id;
- selected row label;
- selected column label;
- raw value;
- parsed value;
- final numeric answer.

### Step 6 - PoT Prompt
Build a prompt that requires generated code to:
- use only `pd`, `dfs`, and approved helper functions;
- assign final answer to `result`;
- not import modules;
- not read files;
- not round intermediate values.

### Step 7 - Sandbox
Implement AST checks before execution.

Block:
- `import`;
- `open`;
- `exec`;
- `eval`;
- file system access;
- network access;
- dunder access.

### Step 8 - Verifier
Verify:
- table exists;
- selected cell exists;
- raw value parse is consistent;
- unit conversion is consistent;
- formula is consistent;
- final answer matches trace.

### Step 9 - Final Answer
Return:
- numeric answer;
- unit;
- citations;
- verification status;
- error type if invalid.

## 13. Run Scope Policy
Phase 3 must not define its own sample/full data scope.

Phase 3 uses evidence retrieved from Phase 2, and Phase 2 uses artifacts produced by Phase 1.

```text
config/run_profile.yaml
-> Phase 1 selected reports
-> Phase 2 retrieval index over selected CSV tables
-> Phase 3 QA over selected evidence tables
```

If Phase 1 was run on one report, Phase 3 can only answer from that one-report artifact set.

If Phase 1 was run full, Phase 3 can answer from the full artifact set.

Question limits are allowed only for debugging/evaluation speed:

```powershell
python -m financial_text_to_pandas.reasoning.answer --config config/run_profile.yaml --oracle-evidence --strategy deterministic --limit 5
python -m financial_text_to_pandas.reasoning.answer --config config/run_profile.yaml --strategy auto --limit 20 --save-trace
```

```text
# Ghi chú:
# --limit chỉ giới hạn số câu hỏi QA dùng để test.
# Nó không quyết định sample/full dữ liệu báo cáo.
# Sample/full dữ liệu báo cáo chỉ đổi trong config/run_profile.yaml.
```

## 14. Required CLI Controls
Every Phase 3 command must support:
- `--query-id`;
- `--limit`;
- `--oracle-evidence`;
- `--strategy deterministic|cot|pot|auto`;
- `--top-k`;
- `--dry-run`;
- `--save-trace`.

## 15. Review Gate
Phase 3 can move forward only after:
- direct lookup sample works;
- one arithmetic sample works;
- sandbox blocks unsafe code;
- verifier catches intentionally wrong cell;
- final answer has citation.

## 16. Anti-Patterns
Do not:
- let LLM answer without selected cells;
- hide sandbox errors;
- round intermediate values;
- drop citations;
- accept answers when verifier is invalid.
