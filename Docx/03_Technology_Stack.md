# Công Nghệ Sử Dụng (Technology Stack)

Hệ thống được xây dựng trên các công nghệ tiên tiến nhất hiện nay, tối ưu cho việc xử lý dữ liệu lớn và thiết kế quy trình AI Agent phức tạp.

## 1. Lớp Dữ liệu (Data Storage Layer)
- **Cơ sở dữ liệu quan hệ (Relational DB):** `DuckDB` hoặc `PostgreSQL`.
  - *Mục đích:* Lưu trữ dữ liệu dạng bảng biểu (Fact/Dimension), xử lý các truy vấn SQL siêu tốc đối với hàng triệu bản ghi số liệu tài chính. DuckDB rất phù hợp cho xử lý phân tích (OLAP) cục bộ.
- **Cơ sở dữ liệu Vector (Vector DB):** `Milvus` hoặc `Qdrant`.
  - *Mục đích:* Lưu trữ vector nhúng của các đoạn văn bản (thuyết minh, báo cáo, quản trị rủi ro), hỗ trợ tìm kiếm lai Hybrid Search (kết hợp giữa tìm kiếm ngữ nghĩa Vector và tìm kiếm từ khóa BM25).

## 2. Lớp Trí tuệ Nhân tạo (AI & LLM Layer)
- **Mô hình Ngôn ngữ (LLMs Open-source < 15B):** Sử dụng các mô hình mã nguồn mở tối ưu cao dưới 15 tỷ tham số như `Qwen2.5-14B-Instruct`, `Llama-3.1-8B-Instruct` hoặc `Mistral-Nemo-12B`.
  - *Nhiệm vụ:* Nắm bắt ngữ cảnh câu hỏi, trích xuất Intent (JSON) thông qua kỹ thuật Few-Shot Prompting, và tổng hợp văn bản ngôn ngữ tự nhiên. Do mô hình nhỏ có hạn chế về sinh mã lập trình (code generation), kiến trúc sẽ bù đắp bằng các Function Calling được lập trình sẵn thay vì để LLM tự do sinh mã Python.
- **Mô hình Nhúng (Embedding Models):** OpenAI Embeddings hoặc các mô hình nhúng tiếng Việt đa ngữ chuyên dụng để chuyển đổi văn bản sang Vector.
- **Agent Framework:** `LangGraph`.
  - *Mục đích:* Quản lý vòng đời (State) của các Agent, cho phép tạo các luồng Multi-Agent dạng đồ thị có chu trình (Cyclic graphs), hỗ trợ đắc lực cơ chế tự đánh giá (Self-reflection), tự sửa lỗi (Self-correction) và vòng lặp tương tác với người dùng (Human-in-the-loop).

## 3. Lớp Xử lý & Thực thi (Execution & Backend Layer)
- **Ngôn ngữ Lập trình:** `Python`.
  - Python là ngôn ngữ tiêu chuẩn và phổ biến nhất để xây dựng Data Pipeline và hệ thống AI.
- **Thư viện Xử lý Dữ liệu:** `Pandas`, `NumPy`.
  - *Mục đích:* Thực thi các phép toán tài chính chuyên sâu, tính toán thống kê (như tính tỷ lệ, trung vị, trung bình, CAGR) dựa trên mã Python do Data Analyst Agent sinh ra.
- **Module Khớp lệnh (Fuzzy Matching):** `FuzzyWuzzy` hoặc `RapidFuzz`.
  - *Mục đích:* Đối chiếu linh hoạt tên chỉ tiêu tài chính do người dùng nhập vào với danh mục tiêu chuẩn trong Alias Dictionary để tính toán tỷ lệ chính xác (Confidence Score).
- **Sandbox Environment:** 
  - *Mục đích:* Cung cấp một môi trường cách ly (isolated environment) để thực thi mã Python do LLM sinh ra, đảm bảo an toàn hệ thống, ngăn ngừa rủi ro chạy mã độc hại và kiểm soát tài nguyên thực thi.
