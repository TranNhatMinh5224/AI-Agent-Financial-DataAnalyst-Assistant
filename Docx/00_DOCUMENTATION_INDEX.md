# TẬP TÀI LIỆU KỸ THUẬT DỰ ÁN AI FINANCIAL DATA ANALYST ASSISTANT

Thư mục này chứa bộ tài liệu kỹ thuật hoàn chỉnh và chính xác nhất cho dự án **AI Agent Financial Data Analyst Assistant**.

---

## 🗺️ Danh Mục Tài Liệu

| Tên File | Mô tả nội dung chính |
| :--- | :--- |
| **`00_MASTER_ARCHITECTURE_SPECIFICATION.md`** | **TÀI LIỆU GỐC CHUẨN DUY NHẤT (Master Spec)**: Hợp nhất toàn bộ 6 bước siêu cấu trúc, Multi-Agent, De-lexicalization, TableRAG, Chain-of-Table, và Hạ tầng Production. |
| `01_Project_Plan.md` | Đăng ký mục tiêu dự án, phạm vi PLAN-ONLY, và lộ trình tổng thể 5 Pha. |
| `02_System_Architecture.md` | Kiến trúc hệ thống Text-to-Pandas & sơ đồ luồng dữ liệu. |
| `03_Technology_Stack.md` | Danh mục công nghệ: Python 3.10+, Pandas, RapidFuzz, Qwen2.5-Coder, vLLM/SGLang. |
| `04_Phase1_Data_Preparation.md` | Chi tiết Pha 1: Chuẩn hóa dữ liệu OCR BCTC, bóc tách bảng HTML, xử lý ô gộp và lưu trữ CSV Store. |
| `05_Phase2_Data_Retrieval_Core.md` | Chi tiết Pha 2: Tìm kiếm bảng biểu lai (Hybrid Search: BM25 + Dense Embeddings + Reranker). |
| `06_Phase3_Text_to_Pandas_QA_and_Reasoning.md` | Chi tiết Pha 3: Động cơ suy luận tài chính Text-to-Pandas và Cell Grounding. |
| `07_Phase4_Deployment_and_Optimization.md` | Chi tiết Pha 4: Đánh giá Benchmark (Metrics, Error Taxonomy), Giao diện UI và Tối ưu hóa. |
| `08_Task_Breakdown_and_Status.md` | Bảng theo dõi tiến độ chi tiết theo từng Task và Trạng thái hiện tại. |
| `09_Production_Grade_Optimization_Plan.md` | Kế hoạch nâng cấp Production-Grade (Self-Correction, Symbolic Masking, Dual Verification). |
| `11_MultiHiertt_Benchmark_and_Hierarchical_Tree_Encoding.md` | Phân tích bài báo MultiHiertt Benchmark (ACL 2022) và phương pháp mã hóa đường dẫn phân cấp `Parent > Child`. |
| `12_De-lexicalization_Pipeline.md` | Quy trình 3 bước Khử ảo giác số học (Masking Context & Query → Symbolic Generation → Deterministic Value Binding). |
| `13_Chain_of_Table_and_TableRAG.md` | Kỹ thuật Chain-of-Table (Google DeepMind - ICLR 2024) và TableRAG (NeurIPS 2024) cho bảng biểu triệu token. |
| `14_Multi_Agent_Architecture_and_Production_Deployment.md` | Kiến trúc Multi-Agent (Planner, Retriever, Programmer, Critic), phân bổ VRAM 80GB, Serving SGLang và OS Sandbox. |
| **`15_Contest_Compliance_and_Model_Manifest.md`** | **TUÂN THỦ QUY ĐỊNH CUỘC THI**: Danh mục 100% Mô hình Mở (Hugging Face) $\le$ 14B, phát hành trước 01/06/2026, lệnh tải và BibTeX trích dẫn tái lập kết quả. |
| `16_Phase1_Preprocessing_Execution_Report.md` | Báo cáo thực thi Phase 1 Preprocessing: Cấu trúc ViFinQA, bóc tách 5 bước, cấu hình `run_profile.yaml` và tổ chức CSV Table Store. |
| `17_Official_Contest_Submission_Format_and_Packaging_Specification.md` | **QUY CHUẨN NỘP BÀI DASHBOARD**: Đặc tả schema JSON, đóng gói ZIP và module `submission.py` tự động validate. |
| **`18_QuickStart_Runbook_A_to_Z.md`** | **HƯỚNG DẪN KHỞI CHẠY TỪ A-Z**: Dành cho Developer mới clone repo. Các lệnh tạo môi trường, Preprocessing, Indexing, Test và Web UI. (Nội dung tương tự README.md) |

---

## 🎯 Điểm Bắt Đầu Đọc Khuyên Dùng
- Đối với **Kiến trúc sư / Developer**: Bắt đầu bằng **`00_MASTER_ARCHITECTURE_SPECIFICATION.md`**.
- Đối với **Quản lý Tiến độ / QA**: Bắt đầu bằng **`08_Task_Breakdown_and_Status.md`**.
