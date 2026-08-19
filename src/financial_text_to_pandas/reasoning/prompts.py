"""
prompts.py — Prompt templates for Reasoning Strategies.

Phase 3, Steps 6 & 7.
"""

POT_PROMPT_TEMPLATE = """
You are a Python data analyst. Write a python script to answer the question below.
You are provided with a dictionary of pandas DataFrames called `dfs`.

Question: {question}

Grounded Cells available to use:
{grounded_cells}

Requirements:
- You must ONLY use the provided `dfs` and grounded cells.
- LƯU Ý QUAN TRỌNG (OCR ERROR AWARENESS): Dữ liệu Grounded Cells được trích xuất từ file scan OCR nên rất hay có lỗi chính tả (VD: "Chỉ phí" thay vì "Chi phí", "Tai sán" thay vì "Tài sản", "Lợi nhuận góp" thay vì "Lợi nhuận gộp", "Lãi suy giám" thay vì "Lãi suy giảm"). Bạn PHẢI dùng chính xác chuỗi ký tự bị lỗi đó (đúng từng dấu cách, dấu câu) đang có trong Grounded Cells để đưa vào hàm `safe_get_cell`. TUYỆT ĐỐI KHÔNG tự ý sửa lỗi chính tả khi query, nếu không code sẽ bị lỗi KeyError.
- Do NOT define `safe_get_cell` or `normalize_unit` yourself; they are already injected into your environment and ready to use.
- You must use the helper function exactly like this: `val = safe_get_cell(dfs, 'table_id_here', 'row_label_here', 'col_label_here')` which returns a float.
- You can use `normalize_unit(val, from_unit, to_unit)` if unit conversion is needed.
- You MUST assign the final calculated numeric answer to the variable `result`.
- Do NOT include `import` statements.
- Do NOT round intermediate results.

### EXAMPLES
Question: "Tổng tài sản ngắn hạn và tài sản dài hạn của công ty ABC năm 2018 là bao nhiêu?"
Logic: BẠN phải đọc phần Grounded Cells để tìm xem chuỗi chữ (string) chính xác của "Tài sản ngắn hạn" và "Tài sản dài hạn" là gì. Sau đó điền chính xác chuỗi đó vào hàm `safe_get_cell`.
Code:
```python
# Thay <CHUỖI_1> bằng tên dòng tài sản ngắn hạn lấy từ Grounded Cells
val_ngan_han = safe_get_cell(dfs, 'ABC_2018_table0', '<CHUỖI_1>', 'numeric__31/12/2018')
# Thay <CHUỖI_2> bằng tên dòng tài sản dài hạn lấy từ Grounded Cells
val_dai_han = safe_get_cell(dfs, 'ABC_2018_table0', '<CHUỖI_2>', 'numeric__31/12/2018')
result = val_ngan_han + val_dai_han
```

Question: "Lợi nhuận gộp năm nay tăng hay giảm bao nhiêu so với năm trước của công ty XYZ?"
Logic: Đọc Grounded Cells để tìm đúng chuỗi tương ứng với "Lợi nhuận gộp", rồi thay vào placeholder.
Code:
```python
val_nam_nay = safe_get_cell(dfs, 'XYZ_table_1', '<CHUỖI_LỢI_NHUẬN>', 'numeric__Năm nay')
val_nam_truoc = safe_get_cell(dfs, 'XYZ_table_1', '<CHUỖI_LỢI_NHUẬN>', 'numeric__Năm trước')
result = val_nam_nay - val_nam_truoc
```

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
