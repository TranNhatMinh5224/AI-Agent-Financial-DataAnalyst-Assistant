# 00 - MASTER ARCHITECTURE SPECIFICATION: AI FINANCIAL DATA ANALYST ASSISTANT

Tài liệu này là **Specification Chuẩn duy nhất (Single Source of Truth)** hợp nhất toàn bộ kiến trúc, thiết kế kỹ thuật, giải pháp tối ưu hóa Production-Grade và lộ trình triển khai của hệ thống **AI Agent Financial Data Analyst Assistant**.

---

## 🏗️ 1. Tổng Quan Kiến Trúc End-to-End (6-Step Superstructure)

Hệ thống tuân theo kiến trúc **Text-to-Pandas & Symbolic Program-of-Thoughts (PoT)** kết hợp **Multi-Agent Collaboration** và **Dual Verification**, đi qua 6 bước siêu cấu trúc khép kín:

```
┌───────────────────────────────────────────────────────────────────────────┐
│ 1. Câu hỏi người dùng (Natural Language Query) + Tập BCTC doanh nghiệp     │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ 2. TableRAG & Hierarchical Indexing (Phase 2 & TableRAG Level-1+2)       │
│    - Metadata & Query Hints Filtering                                     │
│    - Level 1: Schema Retrieval (truy xuất cột/hàng không đọc cell)        │
│    - Level 2: Cell-targeted Pointers (truy xuất ô giao điểm chính xác)   │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ 3. De-lexicalization & Symbolic Masking (Phase 3 & delex.py)              │
│    - Step 1: Masking Context & Query (thay toàn bộ số bằng [NUM_X])       │
│    - Coordinate & Header Path Linearization (Parent > Child)              │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ 4. Symbolic Program Generation (PoT & Chain-of-Table)                      │
│    - Planner Agent phân rã kế hoạch                                       │
│    - Programmer Agent sinh mã Python biểu thức đại số thuần túy           │
│    - Chain-of-Table: Bảng tự tiến hóa (evolving) qua Operation Pool       │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ 5. Secure Sandboxed Execution (sandbox.py & OS-Level Sandbox)             │
│    - Step 3: Deterministic Value Binding (tiêm symbol_map vào globals)    │
│    - Restricted AST Visitor + Cách ly OS (Docker / gVisor / MicroVM)       │
│    - Self-Correction Loop: Traceback → Feedback → Retry (Tối đa 3 lần)    │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ 6. Dual Verification & Final Answer (verifier.py & orchestrator.py)       │
│    - Critic Agent đối chiếu kết quả tính toán với Thuyết minh BCTC        │
│    - Phân loại: verified_dual / verified_single / mismatch_narrative      │
│    - Trả kết quả + Trích dẫn chi tiết (Citations)                         │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 2. Phân Tích Độc Học & Lý Do Thiết Kế (Design Decisions)

### 2.1 Tại sao chọn Text-to-Pandas & Program-of-Thoughts (PoT)?
- **Tránh ảo giác tính toán**: LLM rất kém trong việc tính toán số học trực tiếp trên các chuỗi token. Việc bắt LLM sinh ra mã Python/Pandas để chuyển việc tính toán cho Sandbox giúp đạt độ chính xác 100% về mặt toán học.
- **Tách biệt Suy luận và Thực thi**: LLM đóng vai trò là "Kiến trúc sư logic", còn Python Runtime đóng vai trò là "Máy tính chính xác".

### 2.2 Giới hạn của Bảng Biểu Tài chính & Bài học từ MultiHiertt Benchmark (ACL 2022)
- **Cấu trúc phân cấp 3–4 tầng**: Báo cáo tài chính chứa tiêu đề lồng nhau (`Năm 2023 > Quý 4 > Phân khúc Cloud`). Các mô hình làm phẳng ngây thơ (Flat 2D) chỉ đạt <10% EM.
- **Giải pháp Header Path Linearization**: Mỗi ô được mã hóa kèm đường dẫn phân cấp:  
  `[NUM_0] [RowPath: Kết quả kinh doanh > Phân khúc Cloud | ColPath: Năm 2023 > Quý 4 | Value: 68.4]`

### 2.3 Quy trình 3 bước De-lexicalization (Khử Ảo Giác Số Tuyệt Đối)
1. **Masking Context & Query**: Quét và thay toàn bộ số trong câu hỏi VÀ ngữ cảnh bằng `[NUM_X]`. LLM **không bao giờ nhìn thấy số thực**, triệt tiêu hoàn toàn lỗi "nhớ vẹt" và "bịa số".
2. **Symbolic Program Generation**: LLM chỉ sinh công thức logic dạng `ans = (NUM_1 - NUM_0) / NUM_0 * 100`.
3. **Deterministic Value Binding**: Runtime ánh xạ `symbol_map = {NUM_0: 500.0, NUM_1: 650.0}` và thực thi trong Sandbox.

---

## 🧩 3. Phân Rã Hệ Thống Multi-Agent (CLER Framework - AAAI 2026)

Hệ thống phân rã thành 4 Agent chuyên biệt làm việc trong vòng lặp phản hồi (Reflection Loop):

| Agent | Vai trò cốt lõi | Tần suất chạy | Mô hình đề xuất | Quy tắc Quantization |
| :--- | :--- | :--- | :--- | :--- |
| **Planner Agent** | Phân rã câu hỏi thành chuỗi suy luận multi-step | **1 lần duy nhất** | Model reasoning mạnh nhất (`GPT-4o` / `Qwen2.5-72B`) | **Không quantize** (FP16/INT8 nhẹ) |
| **Retriever Agent** | Định vị bảng biểu, footnotes, và ô dữ liệu | 1–3 lần | Model tầm trung (`Qwen2.5-7b`) | INT8 |
| **Programmer Agent**| Viết mã Python/Pandas biểu thức đại số | 1–3 lần (Self-Correction) | Code Specialist (`Qwen2.5-Coder:7B/14B`) | FP16 / INT8 |
| **Critic / Verifier**| Kiểm định kế toán, đối chiếu số liệu với Thuyết minh | **Nhiều lần** (Loop) | Model nhỏ, tốc độ cao (`Qwen2.5-3b`) | **INT4** (Quantize sâu nhất) |

### 🛑 Quy tắc Quantization & VRAM Budget (NVIDIA 80GB)

```
Planner (26GB) + Programmer (14GB) + Retriever (10GB) + Critic (6GB) 
+ Embedding (3GB) + Reranker (2GB) + KV Cache/Overhead (19GB) = 80GB VRAM
```

> [!CAUTION]
> **NGOẠI LỆ TUYỆT ĐỐI:** Tuyệt đối KHÔNG ĐƯỢC Quantize mô hình **Embedding** và **Reranker**. Đầu ra của 2 mô hình này là tọa độ vector liên tục. Nhiễu lượng tử hóa sẽ làm lệch khoảng cách tương đồng ngữ nghĩa, gây truy xuất sai dữ liệu mà không Critic nào phát hiện lại được.

---

## ⚡ 4. Xử Lý Bảng Biểu Khổng Lồ (TableRAG & Chain-of-Table)

### 4.1 TableRAG (NeurIPS 2024) — Two-Level Retrieval
- **Level 1: Schema Retrieval**: Sử dụng metadata (`table_corpus.csv`) để lọc các cột/hàng liên quan mà **không cần đọc cell data**, tiết kiệm 99% token.
- **Level 2: Cell-targeted Pointers**: Định vị và rút trích chính xác các ô giao điểm `(row_label, column_label)` thành snippet cực ngắn (<100 tokens).

### 4.2 Chain-of-Table (Google DeepMind - ICLR 2024) — Evolving Tables
Đối với các câu hỏi đa bước phức tạp, bảng biểu tự biến đổi qua **Operation Pool**:
- `f_select_row(condition)`: Lọc dòng theo điều kiện.
- `f_select_col(columns)`: Giữ lại cột cần thiết.
- `f_add_col(col_name, formula)`: Thêm cột tính toán mới.
- `f_group_by(group_col, agg_col, agg_func)`: Gom nhóm và tổng hợp.
- `f_sort_by(col, ascending)`: Sắp xếp kết quả.
- `f_final_answer()`: Kết thúc chuỗi biến đổi.

---

## 🔒 5. An Toàn Thực Thi (Sandbox Security)

- **Tầng Ngôn ngữ (Restricted AST Visitor)**: Chặn tất cả các phép import độc hại (`os`, `sys`, `subprocess`), chặn dunder attribute (`__subclasses__`, `__globals__`).
- **Tầng Hệ điều hành (Bắt buộc cho Production)**:
  - `Docker Container`: Namespace & cgroups isolation.
  - `gVisor (Google)`: Chặn syscall và giả lập virtual kernel trong user-space.
  - `Firecracker MicroVM`: Ảo hóa phần cứng mức nhân kernel độc lập cho từng phiên chạy.

---

## 📁 6. Cấu Trúc Mã Nguồn & Module Hoàn Chỉnh

```text
src/financial_text_to_pandas/
├── api/                   # FastAPI endpoints (UI/Integration)
├── config.py              # Configuration manager (run_profile.yaml)
├── types.py               # Dataclasses & Shared Error Taxonomy
├── preprocessing/         # Phase 1: Cleaning, OCR Parsing, Multi-header Flattening
│   ├── table_clean.py     # Hierarchical header flattening (Parent > Child)
│   ├── number_parser.py   # Vietnamese financial number parser
│   └── pipeline.py        # Preprocessing CLI & Audit logger
├── retrieval/             # Phase 2: Recall-First Table Search
│   ├── search.py          # Hybrid BM25 + Dense vector search
│   ├── bm25.py            # BM25 Indexing
│   └── reranker.py        # Cross-Encoder Reranking
├── reasoning/             # Phase 3: Financial Reasoning Engine
│   ├── delex.py           # 3-Step De-lexicalization Pipeline
│   ├── strategy.py        # PoT Strategy & Self-Correction Retry Loop
│   ├── sandbox.py         # Secure AST Python Execution Sandbox
│   ├── verifier.py        # Dual Verification Engine (Table vs Narrative)
│   ├── table_rag.py       # TableRAG Two-Level Retrieval
│   ├── chain_of_table.py  # Chain-of-Table Evolving Engine
│   └── orchestrator.py    # Multi-Agent Collaboration Orchestrator
├── evaluation/            # Phase 4: Benchmark & Error Taxonomy Evaluation
│   ├── metrics.py         # Exact & Tolerance Numeric Accuracy
│   └── evaluator.py       # QA Benchmark evaluator
└── ui/                    # Phase 4: Streamlit / Web UI Dashboard
```

---

## 📜 7. Ba Bài Học Cốt Lõi Cho AI Tài Chính

1. **Cấu trúc là trên hết**: Không bao giờ flatten bảng biểu một cách ngây thơ. Bảo toàn cây phân cấp (`Parent > Child`) và metadata của từng ô.
2. **Tách biệt Suy luận và Tính toán**: Luôn dùng LLM để sinh chương trình biểu tượng (PoT/PAL) và bàn giao toàn bộ việc thực thi cho Sandbox Python.
3. **Triệt tiêu ảo giác bằng Masking & Verification**: De-lexicalize toàn bộ số thực trong cả câu hỏi lẫn ngữ cảnh trước khi sinh code; thiết lập vòng lặp phản hồi tự sửa lỗi và đối chiếu kép trước khi đưa ra câu trả lời cuối cùng.
