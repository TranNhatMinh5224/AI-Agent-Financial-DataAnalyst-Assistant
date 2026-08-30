"""
prompts.py — Prompt templates for Reasoning Strategies.

Phase 3, Steps 6 & 7.
"""

POT_PROMPT_TEMPLATE = """
You are a Python data analyst. Write a python script to answer the question below.
You are provided with a dictionary of pandas DataFrames called `dfs` AND pre-extracted numerical variables (`NUM_0`, `NUM_1`, etc.).

Question: {question}

Grounded Cells available to use:
{grounded_cells}

Requirements:
- You can directly use symbolic variable names like `NUM_0`, `NUM_1` if present in the grounded cells, OR call `safe_get_cell(dfs, 'table_id', 'row_label', 'col_label')`.
- Use `safe_div(a, b)` for division to prevent ZeroDivisionError.
- You MUST assign the final calculated numeric answer to the variable `result`.
- Do NOT include `import` statements.
- Do NOT round intermediate results.

### EXAMPLES

Question: "Doanh thu năm 2023 tăng bao nhiêu phần trăm so với năm 2022?"
Grounded Cells:
- NUM_0 (Doanh thu 2022) = 1000.0
- NUM_1 (Doanh thu 2023) = 1200.0
Code:
```python
result = safe_div(NUM_1 - NUM_0, NUM_0) * 100
```

Question: "Chênh lệch lợi nhuận gộp giữa năm 2023 và năm 2022 là bao nhiêu?"
Grounded Cells:
- NUM_0 (Lợi nhuận gộp 2022) = 500.0
- NUM_1 (Lợi nhuận gộp 2023) = 600.0
Code:
```python
result = NUM_1 - NUM_0
```

Question: "Biên lợi nhuận gộp năm 2023 là bao nhiêu phần trăm?"
Grounded Cells:
- NUM_0 (Lợi nhuận gộp 2023) = 300.0
- NUM_1 (Doanh thu thuần 2023) = 1200.0
Code:
```python
result = safe_div(NUM_0, NUM_1) * 100
```

Question: "Tổng doanh thu 2 năm 2022 và 2023 là bao nhiêu?"
Grounded Cells:
- NUM_0 (Doanh thu 2022) = 1000.0
- NUM_1 (Doanh thu 2023) = 1200.0
Code:
```python
result = NUM_0 + NUM_1
```

Code:
```python
"""

POT_FIX_PROMPT_TEMPLATE = """
You are a Python developer debugging code.
The previous python code you generated failed to execute in the Sandbox.

Question: {question}

Grounded Cells:
{grounded_cells}

Previous Code:
```python
{previous_code}
```

Error Message:
{error_message}

Requirements to Fix:
- Fix the bug described in Error Message.
- Make sure to assign the final numeric answer to `result`.
- Do NOT include `import` statements.
- Return ONLY the corrected python code block inside ```python ... ```.

Code:
```python
"""

COT_PROMPT_TEMPLATE = """
You are a financial analyst. Solve the following question step by step.

Question: {question}

Grounded Cells available as evidence:
{grounded_cells}

Requirements:
- You MUST base your answer ONLY on the provided grounded cells.
- Show your step-by-step arithmetic.
- The final line of your response MUST be exactly: "Final Answer: <number>".
"""

DUAL_VERIFY_PROMPT_TEMPLATE = """
You are an auditor verifying financial calculation results against explanatory text notes (Thuyết minh BCTC).

Calculated Numerical Answer: {numeric_result} {unit}
Question: {question}

Text Notes (Thuyết minh BCTC):
{linked_text_context}

Task:
Determine if the calculated answer is consistent with or contradicted by the text notes.
Answer format:
VERDICT: CONSISTENT | CONTRADICTED | INCONCLUSIVE
REASON: <1 sentence explanation>
"""

PLANNER_PROMPT_TEMPLATE = """
You are a Financial Data Analyst Planner.
Given a complex financial question, your task is to decompose it into a logical multi-step reasoning plan.

Question: {question}

Requirements:
1. Identify the key financial metrics needed.
2. Identify the years or periods involved.
3. Identify the operation required (e.g., lookup, difference, growth_rate, ratio).
4. Output a concise step-by-step plan.
"""

RETRIEVER_GROUNDING_PROMPT_TEMPLATE = """
You are a Financial Data Retriever.
Given a question and a set of candidate tables, your task is to identify the most relevant table and the specific row and column that contain the answer.

Question: {question}

Candidate Tables (with metadata and snippets):
{tables_context}

Requirements:
1. Analyze the candidate tables to find the exact cell that matches the question's intent.
2. If the data is not present in the given tables, state "I_INSUFFICIENT_EVIDENCE".
3. Otherwise, output a JSON object with the following structure:
{{
    "table_id": "<selected_table_id>",
    "row_label": "<matched_row_label>",
    "column_label": "<matched_column_label>"
}}
"""
