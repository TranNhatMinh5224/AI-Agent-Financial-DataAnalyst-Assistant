# 13 - Chain-of-Table & TableRAG: Kiến trúc Xử lý Bảng Biểu Quy mô Lớn

Tài liệu này ghi lại thiết kế và tích hợp hai kỹ thuật tiên tiến nhất năm 2024 vào hệ thống **AI Financial Data Analyst Assistant**:
- **Chain-of-Table** (Wang et al., Google DeepMind — ICLR 2024)
- **TableRAG** (Chen et al., NeurIPS 2024 — xử lý bảng triệu token)

---

## 📌 1. Tại sao các phương pháp cũ thất bại?

| Phương pháp | Vấn đề |
| :--- | :--- |
| **Generic Reasoning** (đọc toàn bộ bảng thô) | Nhiễu ngữ cảnh khi bảng lớn → sai kết quả |
| **Program-aided (SQL/Python thông thường)** | Lỗi khi gặp merged cells, tiêu đề đa tầng |
| **RAG chunking theo hàng** | Mất tiêu đề cột → LLM không hiểu số ở cột nào |
| **Nhét toàn bộ bảng vào Prompt** | Token inflation → vượt context limit → độ trễ cao |

---

## 🔗 2. Chain-of-Table (Google DeepMind — ICLR 2024)

### Ý tưởng cốt lõi
Thay vì đọc bảng thô thụ động một lần, bảng biểu **tự tiến hóa (evolving)** theo từng bước lập luận của mô hình cho đến khi chỉ còn đúng thông tin cần thiết.

### Vòng lặp 3 Bước (Iterative Loop)

```
┌──────────────────────────────────────────────┐
│  Input: Question + Current Table State       │
│                                              │
│  Step 1: Sample next operation               │
│          LLM chọn f_add_col / f_select_row   │
│          / f_group_by / f_sort_by ...        │
│                  │                           │
│  Step 2: Generate arguments                  │
│          LLM xác định tham số cụ thể         │
│                  │                           │
│  Step 3: Transform table                     │
│          Thực thi → Intermediate Table mới   │
│                  │                           │
│  Lặp lại đến khi bảng đủ nhỏ để trả lời     │
└──────────────────────────────────────────────┘
```

### Operation Pool (Tập thao tác)

| Operation | Mô tả | Ví dụ BCTC |
| :--- | :--- | :--- |
| `f_select_row(condition)` | Lọc hàng theo điều kiện | Chọn dòng năm 2023 |
| `f_select_col(cols)` | Giữ lại chỉ cột cần thiết | Giữ cột Doanh thu + Lợi nhuận |
| `f_add_col(name, formula)` | Thêm cột tính toán | Thêm cột "Tỷ suất LN" = LN/DT |
| `f_group_by(col, agg)` | Gom nhóm + tổng hợp | Group by Ticker → Sum doanh thu |
| `f_sort_by(col, ascending)` | Sắp xếp | Sort by Tăng trưởng DT giảm dần |

### Ví dụ Thực tế trên BCTC Việt Nam

**Câu hỏi**: *"Trong 5 công ty có doanh thu lớn nhất ngành Ngân hàng 2023, công ty nào có tỷ suất lợi nhuận ròng cao nhất?"*

```
Iter 1: f_select_row(WHERE ngành = 'Ngân hàng' AND năm = 2023)
        → Bảng còn: 20 dòng

Iter 2: f_add_col('Tỷ suất LN ròng', LNST / Doanh_thu * 100)
        → Bảng còn: 20 dòng + cột mới

Iter 3: f_sort_by('Doanh thu', ascending=False) → f_select_row(TOP 5)
        → Bảng còn: 5 dòng

Iter 4: f_sort_by('Tỷ suất LN ròng', ascending=False)
        → Hàng đầu tiên = câu trả lời ✅
```

---

## 📚 3. TableRAG: Xử lý Bảng Triệu Token

### Two-Level Retrieval

```
Câu hỏi + Schema Index
        │
        ▼
┌──────────────────────────┐
│  Level 1: Schema         │  → Chọn ĐÚNG cột/hàng từ metadata
│  Retrieval               │     (không đọc data rows)
│  (< 1ms)                 │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│  Level 2: Cell-targeted  │  → Lấy chính xác ô tại giao điểm
│  Pointers                │     row × col đã xác định
│  (< 10ms)                │
└───────────┬──────────────┘
            │
            ▼
     Compact evidence snippet
     → Chain-of-Table / PoT
```

### Triển khai trong Hệ thống

| Component | Vai trò |
| :--- | :--- |
| `table_corpus.csv` | Schema index: `table_id, ticker, year, statement_type, column_names` |
| `retrieval/search.py` | Level 1: Filter by metadata → candidate column names |
| `reasoning/cell_grounding.py` | Level 2: Cell-targeted grounding tại `(row_label, column_label)` |
| `reasoning/chain_of_table.py` | Vòng lặp Chain-of-Table trên bảng đã được TableRAG thu hẹp |

---

## 🔗 4. Pipeline Kết hợp Tối ưu

```
Câu hỏi Tài chính
       │
       ▼
TableRAG Level 1: Schema Retrieval     ← lọc metadata
       │  (chọn bảng + cột liên quan)
       ▼
TableRAG Level 2: Cell Grounding       ← lấy ô chính xác
       │  (grounded cells + symbol NUM_X)
       ▼
De-lexicalization                      ← mask số trong question
       │  (build_delex_context)
       ▼
Chain-of-Table (nếu multi-hop)         ← bảng tự tiến hóa
  hoặc PoT Strategy (nếu simple)       ← sinh code đại số
       │
       ▼
Sandbox Execution                      ← Deterministic Value Binding
       │
       ▼
Dual Verification                      ← đối chiếu bảng vs thuyết minh
       │
       ▼
Câu trả lời Cuối cùng ✅
```

> [!IMPORTANT]
> **TableRAG** giải quyết vấn đề **scale** (triệu token).  
> **Chain-of-Table** giải quyết vấn đề **logic** (multi-hop phức tạp).  
> Kết hợp cả hai là công thức cho Production-Grade Financial QA.
