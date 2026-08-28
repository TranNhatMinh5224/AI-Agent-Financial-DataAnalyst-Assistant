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
result = ((NUM_1 - NUM_0) / NUM_0) * 100
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


