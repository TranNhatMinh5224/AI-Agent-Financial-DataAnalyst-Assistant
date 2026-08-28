# PART 3: RETRIEVAL & REASONING ENGINE (TEXT-TO-PANDAS)

Tài liệu này hợp nhất đầy đủ và chi tiết các tệp thuộc phân hệ Retrieval & Reasoning: **05_Phase2_Data_Retrieval_Core**, **06_Phase3_Text_to_Pandas_QA_and_Reasoning**, **11_MultiHiertt_Benchmark_and_Hierarchical_Tree_Encoding**, **12_De-lexicalization_Pipeline**, và **13_Chain_of_Table_and_TableRAG**.

---

# SECTION 1: PHASE 2 RETRIEVAL CORE (05)

## 1. Objective & Canonical Flow
Retrieve top evidence CSV tables required for answering a financial question using a recall-first approach.

```text
Question -> Query Hints / Metadata Filtering -> BM25 top 50 + Dense top 50 -> Merge & Deduplicate -> Reranker top 10 -> Top-K Evidence Tables
```

Missing a required table is a critical failure because cell grounding and reasoning cannot recover evidence that was never retrieved.

## 2. Table Corpus & Search Text Schema
`search_text` concatenates: `title`, `headers_text`, `row_labels_text`, `nearby_text`, `unit`, `statement_type`, `ticker`, `company_name`, `year`, `report_type`.

## 3. Retrieval Policy & Benchmark Targets
- Baseline: BM25 (`Recall@10 47.41%`)
- Fallback Dense: `BGE-M3` (`Recall@10 53.05%`)
- Recommended Dense: `Qwen3-Embedding-8B` (`Recall@10 67.48%`)
- Dense + Reranker (`bge-reranker-v2-m3`): `Recall@10 80.80%`

---

# SECTION 2: PHASE 3 TEXT-TO-PANDAS REASONING (06)

## 1. Canonical Flow
```text
Question + Evidence Tables -> Schema-Aware Cell Grounding -> Strategy Selection (Direct Lookup / PoT / CoT / Multi-hop) -> Sandbox Execution -> Dual Verification -> Verified Answer
```

## 2. Schema-Aware Cell Grounding
Identifies exact evidence cells before reasoning starts:
- Priority: `row_label_full -> row_label_raw -> fuzzy matching (token_sort_ratio)`
- Threshold check: Grounding confidence must satisfy threshold. If table missing -> `I_INSUFFICIENT_EVIDENCE`. If cell missing -> `E_NUMERICAL_EXTRACTION`.

## 3. Execution Strategies
- **Direct Lookup**: Single table, single exact cell, zero arithmetic.
- **Program-of-Thought (PoT)**: Generates Pandas code evaluated inside secure AST Python Sandbox.
- **Chain-of-Thought (CoT)**: Fallback when code generation is unstable or Sandbox fails.
- **Multi-hop**: Iterative retrieval and grounding for multi-year / multi-company questions.

---

# SECTION 3: MULTIHIERTT BENCHMARK & TREE ENCODING (11)

## 📌 1. Bài học từ MultiHiertt Benchmark (ACL 2022)
Báo cáo tài chính doanh nghiệp thực tế chứa tiêu đề lồng ghép 3–4 tầng (`Năm 2023 > Quý 4 > Phân khúc Cloud`). Mô hình làm phẳng 2D ngây thơ thất bại (<10% EM).

## 🛠️ 2. Coordinate & Header Path Linearization
Mỗi ô $c_{i,j}$ được biểu diễn dưới dạng đường dẫn tọa độ mở rộng:
$$c_{i,j} = \left( \text{RowPath}(i), \text{ColPath}(j), \text{Value} \right)$$
Ví dụ ô `68.4%`:
`[RowPath: Kết quả kinh doanh > Phân khúc Cloud | ColPath: Năm 2023 > Quý 4 | Value: 68.4%]`

---

# SECTION 4: DE-LEXICALIZATION PIPELINE (12)

## 🔧 Quy trình 3 bước Triệt tiêu Ảo giác Số học
1. **Step 1: Masking Context & Query**: Quét và thay toàn bộ số trong câu hỏi VÀ ngữ cảnh bằng `[NUM_0]`, `[NUM_1]`. LLM không nhìn thấy số thực.
2. **Step 2: Symbolic Program Generation**: LLM chỉ sinh công thức logic thuần túy: `result = (NUM_1 - NUM_0) / NUM_0 * 100`.
3. **Step 3: Deterministic Value Binding**: Runtime tiêm `symbol_map = {NUM_0: 500.0, NUM_1: 650.0}` trực tiếp vào Sandbox `globals` để thực thi chính xác 100%.

---

# SECTION 5: CHAIN-OF-TABLE & TABLERAG (13)

## 🔗 1. Chain-of-Table (Google DeepMind - ICLR 2024)
Bảng biểu tự tiến hóa qua **Operation Pool**: `f_select_row`, `f_select_col`, `f_add_col`, `f_group_by`, `f_sort_by`.

## 📚 2. TableRAG (NeurIPS 2024) — Two-Level Retrieval
- **Level 1 (Schema Retrieval)**: Đọc `table_corpus.csv` chọn đúng cột/hàng từ metadata mà không cần nạp cell data (tiết kiệm 99% token).
- **Level 2 (Cell-targeted Pointers)**: Định vị chính xác ô giao điểm $row \times col$ thành snippet cực ngắn (<100 tokens).
