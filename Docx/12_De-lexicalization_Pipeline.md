# 12 - De-lexicalization Pipeline: Quy Trình 3 Bước Triệt tiêu Ảo giác Số học

Tài liệu này mô tả chi tiết thiết kế và triển khai quy trình **De-lexicalization (Chuẩn hóa loại bỏ số)** — giải pháp kỹ thuật cốt lõi để loại bỏ hoàn toàn hiện tượng LLM "bịa" số khi sinh mã tính toán tài chính.

---

## 🧠 1. Vấn đề Cốt lõi: Tại sao LLM lại "bịa" số?

Khi thực hiện **sinh mã nguồn (code generation)** để tính toán tài chính, các mô hình ngôn ngữ lớn (LLM) có hai lỗi nghiêm trọng:

| Loại lỗi | Cơ chế | Ảnh hưởng |
| :--- | :--- | :--- |
| **"Nhớ vẹt" số trong prompt** | LLM copy cứng số từ câu hỏi vào code mà không hiểu ngữ cảnh | Sai khi số trong câu hỏi không phải số cần tính |
| **Tự bịa hằng số ngẫu nhiên** | Bias tích lũy từ pre-training trên dữ liệu internet | Code chứa số không tồn tại trong bảng biểu |

---

## 🔧 2. Quy trình 3 bước De-lexicalization

```
Question + Tables
      │
      ▼
 ┌─────────────────────────────┐
 │  STEP 1: Masking            │  → "Tăng từ 500M lên 650M"
 │  mask_numbers_in_text()     │  → "Tăng từ [NUM_2] lên [NUM_3]"
 └───────────────┬─────────────┘
                 │
      ┌──────────▼──────────────────────┐
      │  STEP 2: Symbolic Generation    │  LLM chỉ thấy placeholders
      │  LLM sinh: result = (NUM_1 -    │  → sinh biểu thức đại số thuần túy
      │            NUM_0) / NUM_0 * 100 │
      └──────────┬──────────────────────┘
                 │
      ┌──────────▼───────────────────────────┐
      │  STEP 3: Deterministic Value Binding  │
      │  symbol_map = {NUM_0: 500, NUM_1: 650}│
      │  Sandbox.exec(code, globals=map)      │
      │  → result = 30.0                      │
      └───────────────────────────────────────┘
```

### Bước 1 — Masking Context & Query
Module: `reasoning/delex.py` → `mask_numbers_in_text(text, start_index)`

Quét và thay thế **toàn bộ số thực** trong câu hỏi VÀ ngữ cảnh bằng placeholder:
```
Input:  "Doanh thu tăng từ 500M lên 650M, tỷ suất lợi nhuận đạt 68.4%"
Output: "Doanh thu tăng từ [NUM_0] lên [NUM_1], tỷ suất lợi nhuận đạt [NUM_2]"
Mapping: {NUM_0: "500M", NUM_1: "650M", NUM_2: "68.4%"}
```

### Bước 2 — Symbolic Program Generation
LLM nhận `masked_question` + `masked_cells_str` (cả số trong bảng đã được mask thành `NUM_0`, `NUM_1`...).  
LLM chỉ sinh biểu thức đại số thuần túy:
```python
result = (NUM_1 - NUM_0) / NUM_0 * 100
```

### Bước 3 — Deterministic Value Binding
`run_pandas_sandbox(code, dfs, symbol_map={NUM_0: 500.0, NUM_1: 650.0})`  
Sandbox tiêm `symbol_map` trực tiếp vào `globals` → thực thi an toàn.

---

## 🏆 3. Lợi ích Thực tế trong Môi trường Sản xuất (Production)

| Lợi ích | Giải thích |
| :--- | :--- |
| **100% Grounding** | Không một số nào có thể bị ảo giác. Code chỉ chứa biến trỏ về ô bảng biểu đã xác thực. |
| **Generalization across Entities** | Cùng logic tính ROE/EBITDA áp dụng cho mọi doanh nghiệp, không bị bias bởi quy mô doanh thu. |
| **Token Space Reduction** | Số thực dài (ví dụ: `1,234,567,890`) chiếm nhiều token và dễ bị split token kỳ dị. Placeholder `NUM_0` tiết kiệm context window. |

---

## 📁 4. Vị trí File và API

| File | Chức năng |
| :--- | :--- |
| `src/financial_text_to_pandas/reasoning/delex.py` | Module De-lexicalization (3 bước) |
| `src/financial_text_to_pandas/reasoning/strategy.py` | Tích hợp pipeline vào `run_pot_strategy()` |
| `src/financial_text_to_pandas/reasoning/sandbox.py` | Tiêm `symbol_map` vào `globals` |
| `tests/test_delex.py` | Unit tests đầy đủ cho cả 3 bước |

### API chính trong `delex.py`

```python
from financial_text_to_pandas.reasoning.delex import (
    mask_numbers_in_text,   # Step 1
    build_delex_context,    # Steps 1+2 combined
    render_audit_trace,     # Audit trail: NUM_X → real value
)

# Step 1: Mask inline numbers in a string
masked, num_map = mask_numbers_in_text("Tăng từ 500 lên 650", start_index=0)

# Step 2: Full context for PoT prompt
ctx = build_delex_context(question, grounded_cells)
# ctx.masked_question: câu hỏi đã mask
# ctx.masked_cells_str: cells với đường dẫn phân cấp đã mask
# ctx.symbol_map: {NUM_0: 500.0, NUM_1: 650.0}

# Step 3: Sandbox execution
sandbox_val = run_pandas_sandbox(code, dfs, symbol_map=ctx.symbol_map)
```

---

## ⚙️ 5. Cấu trúc `DelexContext` Dataclass

```python
@dataclass
class DelexContext:
    masked_question: str        # câu hỏi không chứa số
    masked_cells_str: str       # grounded cells ở dạng đường dẫn phân cấp
    symbol_map: Dict[str, float]  # {NUM_0: 500.0} → inject vào Sandbox
    raw_map: Dict[str, str]       # {NUM_0: "500M"} → audit trail
```

> [!IMPORTANT]
> Quy trình này không chỉ mask số từ bảng biểu mà còn mask **số trong câu hỏi gốc**.  
> Đây là điểm khác biệt so với phương pháp trước — giải quyết triệt để cả hai lỗi "nhớ vẹt" và "bịa số".
