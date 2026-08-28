# 00 - MASTER DOCUMENTATION INDEX: AI FINANCIAL DATA ANALYST ASSISTANT

Tài liệu này là **Master Index (Mục Mục Chính)** hợp nhất toàn bộ bộ tài liệu dự án **AI Financial Data Analyst Assistant** thành **5 PART chuyên sâu**. Nội dung trong từng PART được bảo toàn **đầy đủ chi tiết 100% (Full Specs)**, được tổ chức theo từng phân hệ logic khoa học.

---

## 🌳 Sơ Đồ Cấu Trúc Bộ Tài Liệu 5 PART

```text
Docx/
│
├── PART_1_OVERVIEW_AND_PROJECT_PLAN.md               # Overview, Architecture Spec, Project Plan, Tech Stack
├── PART_2_DATA_PREPROCESSING_AND_VIFINQA.md           # Phase 1 Preprocessing, Pipeline Execution, ViFinQA Analysis
├── PART_3_RETRIEVAL_AND_REASONING_ENGINE.md           # Phase 2 & 3: Hybrid Retrieval, PoT, Tree Encoding, De-lex, TableRAG
├── PART_4_MULTI_AGENT_DEPLOYMENT_AND_CONTEST.md       # Multi-Agent CLER, SGLang, Submission Format, Contest Compliance
└── PART_5_SYSTEM_DIAGRAMS_AND_ROADMAP.md             # End-to-End Diagrams, Task Status, Multi-hop Plan, Proposals
```

---

## 📚 Chi Tiết Nội Dung Từng PART

### 🟢 [PART 1: Overview, Master Architecture & Project Plan](PART_1_OVERVIEW_AND_PROJECT_PLAN.md)
*Hợp nhất đầy đủ từ các file: `00_MASTER_ARCHITECTURE_SPECIFICATION.md`, `01_Project_Plan.md`, `02_System_Architecture.md`, `03_Technology_Stack.md`*
- **Kiến trúc Superstructure 6 bước**: Từ câu hỏi tự nhiên đến kết quả kiểm định kép.
- **Quyết định thiết kế**: Lý do lựa chọn Text-to-Pandas & Program-of-Thoughts (PoT).
- **Phân rã Multi-Agent Framework**: CLER Framework (Planner, Retriever, Programmer, Critic) & VRAM Budget (80GB).
- **Kế hoạch dự án & Cấu trúc mã nguồn**: Chi tiết quy chuẩn các thư mục và gói `src/financial_text_to_pandas/`.

---

### 🔵 [PART 2: Data Preprocessing, Table Store & ViFinQA Analysis](PART_2_DATA_PREPROCESSING_AND_VIFINQA.md)
*Hợp nhất đầy đủ từ các file: `04_Phase1_Data_Preparation.md`, `16_Phase1_Preprocessing_Execution_Report.md`, `21_ViFinQA_Dataset_Comprehensive_Analysis.md`*
- **Quy trình bóc tách HTML Table & Grid Expansion**: Xử lý ô gộp `rowspan`/`colspan`, căn chỉnh ma trận 2D.
- **Tiêu đề phân cấp & Normalization số liệu**: Flatten tiêu đề `Parent > Child` và parse chuẩn số liệu tiếng Việt.
- **Chi tiết Dataset ViFinQA**: Phân tích 100 mã cổ phiếu và 1.013 câu hỏi kiểm thử.
- **Quản lý chế độ chạy**: Cấu hình chi tiết `config/run_profile.yaml` cho 2 chế độ `sample` và `full`.

---

### 🟣 [PART 3: Retrieval & Reasoning Engine (Text-to-Pandas)](PART_3_RETRIEVAL_AND_REASONING_ENGINE.md)
*Hợp nhất đầy đủ từ các file: `05_Phase2_Data_Retrieval_Core.md`, `06_Phase3_Text_to_Pandas_QA_and_Reasoning.md`, `11_MultiHiertt_Benchmark_and_Hierarchical_Tree_Encoding.md`, `12_De-lexicalization_Pipeline.md`, `13_Chain_of_Table_and_TableRAG.md`*
- **Phase 2 Table Retrieval Core**: Kết hợp BM25 + `Qwen3-Embedding-8B` + `bge-reranker-v2-m3`.
- **Phase 3 Reasoning & Schema-Aware Cell Grounding**: Định vị ô giao điểm chính xác trước khi thực thi code.
- **Khử ảo giác số học (De-lexicalization)**: Quy trình 3 bước thay thế số thực bằng symbol `[NUM_X]`.
- **TableRAG & Chain-of-Table**: Two-Level Retrieval (Schema & Cell-targeted Pointers) và bảng tự tiến hóa.

---

### 🟡 [PART 4: Multi-Agent Architecture, Production Deployment & Contest Compliance](PART_4_MULTI_AGENT_DEPLOYMENT_AND_CONTEST.md)
*Hợp nhất đầy đủ từ các file: `07_Phase4_Deployment_and_Optimization.md`, `09_Production_Grade_Optimization_Plan.md`, `14_Multi_Agent_Architecture_and_Production_Deployment.md`, `15_Contest_Compliance_and_Model_Manifest.md`, `17_Official_Contest_Submission_Format_and_Packaging_Specification.md`, `18_QuickStart_Runbook_A_to_Z.md`*
- **Tuân thủ quy định cuộc thi (Contest Compliance)**: 100% Open-weights LLMs $\le 14B$ (DeepSeek-R1-Distill-Qwen-14B, Qwen2.5-Coder-14B).
- **Phục vụ mô hình (Serving)**: Tối ưu latency với SGLang Engine và RadixAttention KV-Cache sharing.
- **Quy chuẩn nộp bài thi (Submission Packaging Spec)**: Cấu trúc file `submission.zip` & JSON Schema chính thức.
- **QuickStart Runbook A–Z**: Hướng dẫn chạy từng bước từ cài môi trường đến khởi chạy Streamlit Web UI.

---

### 🔴 [PART 5: System Diagrams, Task Status & Future Roadmap](PART_5_SYSTEM_DIAGRAMS_AND_ROADMAP.md)
*Hợp nhất đầy đủ từ các file: `08_Task_Breakdown_and_Status.md`, `19_Multi_Hop_SubQuery_Implementation_Plan.md`, `20_End_to_End_System_Architecture_Diagram.md`, `Optimization_Proposals.md`*
- **Sơ đồ kiến trúc End-to-End**: Trực quan hóa luồng dữ liệu từ Query người dùng đến Verified Answer.
- **Bảng trạng thái công việc (Task Breakdown)**: Tiến độ hoàn thành 4 Phase.
- **Lộ trình nâng cấp Multi-Hop Sub-Query**: Kế hoạch phân rã câu hỏi đa điều kiện và Parallel Retrieval.
- **Đề xuất tối ưu hóa Production**: Quantization strategy, log monitoring và bảo mật AST Sandbox.
