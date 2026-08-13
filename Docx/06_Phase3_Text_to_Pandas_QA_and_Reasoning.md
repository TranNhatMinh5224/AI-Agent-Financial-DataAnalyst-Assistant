# 06 - Phase 3: Text-to-Pandas QA and Reasoning

## 1. Objective
Answer financial questions using retrieved CSV evidence tables and Pandas.

The system must answer from grounded CSV cells and calculation traces, not from model memory.

## 2. Canonical Flow

```text
Question + Evidence Tables
-> Schema-Aware Cell Grounding
-> Selected Tables / Rows / Columns / Cells
-> Reasoning Strategy
-> Direct Lookup / PoT / CoT / Multi-hop
-> Verification
-> Verified Numerical Answer
```

## 3. Inputs

```text
question
top_k evidence tables
table_metadata rows
linked text snippets
```

Evidence tables are loaded into:

```python
dfs: dict[str, pd.DataFrame]
metadata_by_table: dict[str, dict]
```

## 4. Evidence Package Schema

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

## 5. Required Modules

```text
reasoning/evidence.py
reasoning/intent.py
reasoning/cell_grounding.py
reasoning/strategy.py
reasoning/prompts.py
reasoning/sandbox.py
reasoning/tools.py
reasoning/multi_hop.py
reasoning/verifier.py
reasoning/answer.py
```

## 6. Required Functions

```python
load_evidence_tables(package: EvidencePackage) -> dict[str, pd.DataFrame]
build_table_summary(df: pd.DataFrame, metadata: dict) -> TableSummary
extract_intent(question: str) -> Intent
ground_cells(intent: Intent, dfs: dict[str, pd.DataFrame], metadata_by_table: dict[str, dict]) -> CellGroundingResult
choose_reasoning_strategy(intent: Intent, grounding: CellGroundingResult) -> Literal["deterministic", "pot", "cot", "multi_hop"]
run_deterministic_lookup(intent: Intent, grounding: CellGroundingResult) -> ReasoningResult
build_cot_prompt(package: EvidencePackage, grounding: CellGroundingResult) -> str
build_pot_prompt(package: EvidencePackage, grounding: CellGroundingResult) -> str
run_pandas_sandbox(code: str, dfs: dict[str, pd.DataFrame]) -> SandboxResult
run_multi_hop(question: str, initial_package: EvidencePackage) -> ReasoningResult
verify_answer(result: ReasoningResult, grounding: CellGroundingResult, package: EvidencePackage) -> VerificationResult
format_final_answer(result: ReasoningResult, verification: VerificationResult) -> FinalAnswer
```

Use `multi_hop` consistently as the only strategy name for iterative hard-question reasoning.

## 7. Schema-Aware Cell Grounding
Cell grounding is the stage that finds exact evidence cells before reasoning.

Responsibilities:
- select `table_id`;
- select `row_label`;
- select `column_label`;
- extract `raw_value`;
- parse `parsed_value`;
- determine `unit`;
- assign confidence;
- return structured errors.

Grounding priority:

```text
row_label_full
-> row_label_raw
-> fuzzy matching if needed
```

Rules:
- prefer exact schema and metadata matches;
- use fuzzy matching only after exact matching fails;
- require confidence threshold;
- do not let an LLM choose cells freely without schema/context;
- do not start reasoning when required evidence cells cannot be grounded.

Failure mapping:
- missing required table -> `I_INSUFFICIENT_EVIDENCE`;
- row, column, or cell cannot be grounded -> `E_NUMERICAL_EXTRACTION`;
- parse failure from a selected raw value -> `E_NUMERICAL_EXTRACTION`.

Grounded cell schema:

```json
{
  "table_id": "string",
  "csv_path": "string",
  "page_number": 0,
  "row_label": "string",
  "column_label": "string",
  "raw_value": "string",
  "parsed_value": 0.0,
  "unit": "string|null",
  "confidence": 0.0,
  "grounding_method": "exact|row_label_full|row_label_raw|fuzzy",
  "error_type": null
}
```

## 8. Reasoning Strategy

### Direct Deterministic Lookup
Use when:
- there is 1 table;
- there is 1 exact grounded cell;
- no arithmetic is needed.

This is an optimization before complex reasoning.

### Program-of-Thought
Use PoT when:
- arithmetic is needed;
- aggregation is needed;
- multiple values are needed;
- multiple tables are needed;
- Pandas operations are safer than natural-language arithmetic.

Generated code must:
- use only `pd`, `dfs`, grounded cell references, and approved helper functions;
- assign final value to `result`;
- avoid imports;
- avoid file access;
- avoid network access;
- avoid mutation outside local variables;
- keep raw row and column labels unchanged;
- not round intermediate results.

### Chain-of-Thought
Use CoT when:
- code generation is unstable;
- PoT sandbox or code execution fails;
- natural-language reasoning is more reliable for the question;
- the model is too small to generate reliable Pandas code.

CoT output must still include:
- selected `table_id`;
- selected row label;
- selected column label;
- raw value;
- parsed value;
- final numeric answer.

### Adaptive Strategy

```text
Schema-Aware Grounding
-> Direct Lookup if possible
-> Strategy Selection
   -> PoT
   -> CoT
   -> Multi-hop
-> Verification
```

## 9. Multi-hop Flow
Use `multi_hop` for hard questions where an intermediate result determines the next company, table, year, report, or metric.

Minimal flow:

```text
Question
-> retrieve evidence
-> grounding
-> intermediate result
-> determine next retrieval requirement
-> retrieve again
-> grounding again
-> final calculation
```

Rules:
- keep each hop traceable;
- store intermediate values;
- store next retrieval requirement;
- verify final answer against all grounded cells;
- do not introduce a complex multi-agent framework for the first implementation.

Multi-hop trace schema:

```json
{
  "hop_index": 0,
  "question_or_subquestion": "string",
  "retrieval_requirement": {},
  "evidence_table_ids": ["string"],
  "grounded_cells": [],
  "intermediate_result": 0.0,
  "next_requirement": {}
}
```

## 10. Pandas Sandbox Contract
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

## 11. Verification Schema

```json
{
  "is_valid": true,
  "verification_status": "valid",
  "error_type": null,
  "checked_cells": [
    {
      "table_id": "string",
      "csv_path": "string",
      "page_number": 0,
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

Verifier checks:
- selected table exists;
- selected row exists;
- selected column exists;
- selected cell exists;
- raw value parses to parsed value;
- unit conversion is correct;
- sign convention is correct;
- formula is correct;
- rounding is final-only;
- final numerical answer matches trace.

Answers with `verification_status = invalid` must not be accepted.

## 12. Shared Error Taxonomy

```text
E_NUMERICAL_EXTRACTION
I_INSUFFICIENT_EVIDENCE
T_TECHNICAL_ERROR
C_CALCULATION_ERROR
F_FORMULA_ERROR
U_UNVERIFIED
```

Use the same codes in Phase 3, Phase 4, tests, evaluation, and logs.

## 13. Final Answer Schema

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

Final answers must be traceable to grounded cells.

## 14. Tests Required
- evidence loader loads CSV into `dfs`;
- intent parser extracts ticker, year, metric, unit, and operation;
- cell grounding prefers `row_label_full`;
- cell grounding falls back to `row_label_raw`;
- fuzzy matching respects confidence threshold;
- grounding returns `I_INSUFFICIENT_EVIDENCE` for missing required table;
- grounding returns `E_NUMERICAL_EXTRACTION` for missing row/column/cell;
- deterministic lookup finds exact grounded cell;
- strategy selector chooses direct lookup for one exact cell;
- strategy selector chooses PoT for arithmetic/multiple values;
- strategy selector chooses CoT fallback after sandbox failure;
- strategy selector supports `multi_hop`;
- sandbox blocks imports;
- sandbox blocks file access;
- sandbox returns `result`;
- verifier catches wrong table;
- verifier catches wrong row;
- verifier catches wrong column;
- verifier catches wrong unit;
- verifier catches wrong sign;
- verifier catches wrong formula;
- final answer formatter returns numeric answer with citation.

## 15. Implementation Steps

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
- classify operation type including `multi_hop`.

### Step 3 - Cell Grounding
Create `reasoning/cell_grounding.py`.

Rules:
- search candidate tables by schema and metadata;
- match row with `row_label_full` first;
- fallback to `row_label_raw`;
- use fuzzy matching only when needed;
- require confidence threshold;
- return grounded cells or structured error.

### Step 4 - Strategy Selector
Create `reasoning/strategy.py`.

Rules:
- direct exact lookup -> `deterministic`;
- arithmetic or multi-value -> `pot`;
- sandbox/code failure -> `cot`;
- intermediate result determines next retrieval -> `multi_hop`;
- insufficient grounded evidence -> stop with error.

### Step 5 - Deterministic Lookup
Use grounded cell values directly when no arithmetic is needed.

### Step 6 - CoT Prompt
Build a prompt that requires grounded evidence and a numeric answer. The prompt cannot allow selecting cells that are not in `CellGroundingResult`.

### Step 7 - PoT Prompt
Build a prompt that requires generated code to use only loaded `dfs`, grounded cells, and approved helper functions.

### Step 8 - Sandbox
Implement AST checks before execution.

Block:
- `import`;
- `open`;
- `exec`;
- `eval`;
- file system access;
- network access;
- dunder access.

### Step 9 - Multi-hop Controller
Create `reasoning/multi_hop.py`.

Rules:
- store each hop;
- create next retrieval requirement;
- call retrieval again through a stable interface;
- ground cells again;
- pass all grounded cells to final reasoning and verification.

### Step 10 - Verifier
Verify table, row, column, cell, raw value, parsed value, unit, sign, formula, rounding, and final answer.

### Step 11 - Final Answer
Return numeric answer, unit, citations, verification status, and error type if invalid.

## 16. Run Scope Policy
Phase 3 must not define its own sample/full report scope.

```text
config/run_profile.yaml
-> Phase 1 selected reports
-> Phase 2 retrieval index over selected CSV tables
-> Phase 3 QA over selected evidence tables
```

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

## 17. Required CLI Controls
Every Phase 3 command must support:
- `--config`;
- `--query-id`;
- `--limit`;
- `--oracle-evidence`;
- `--strategy deterministic|pot|cot|multi_hop|auto`;
- `--top-k`;
- `--dry-run`;
- `--save-trace`.

## 18. Review Gate
Phase 3 can move forward only after:
- cell grounding works on direct lookup examples;
- direct lookup sample works;
- one arithmetic sample works through PoT;
- CoT fallback works after simulated sandbox failure;
- one minimal multi-hop trace is produced;
- sandbox blocks unsafe code;
- verifier catches intentionally wrong cell;
- final answer has citation.

## 19. Anti-Patterns
Do not:
- let LLM answer without grounded cells;
- let LLM freely choose cells outside schema/context;
- hide sandbox errors;
- round intermediate values;
- drop citations;
- accept answers when verifier is invalid;
- introduce complex multi-agent orchestration in the first implementation path.
