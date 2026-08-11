# Phân rã Công việc Siêu chi tiết & Trạng thái Thực thi (Granular Task Breakdown & Status)

**Quy ước Trạng thái (Status Indicator):**
- 🔴 **Chưa làm (To Do):** Nhiệm vụ đang trong backlog.
- 🟡 **Đang làm (In Progress):** Đang viết code hoặc tinh chỉnh.
- 🟢 **Đã hoàn thành (Done):** Đã pass test và merge code.

---

## Giai đoạn 1 (Phase 1): Chuẩn bị và Chuẩn hóa Dữ liệu

### 1.1 Khởi tạo dự án & Môi trường
- 🔴 **Task 1.1.1:** Khởi tạo Git repo, thiết lập môi trường ảo (Python `venv` hoặc `conda`).
- 🔴 **Task 1.1.2:** Cài đặt các thư viện lõi (BeautifulSoup, Pandas, DuckDB, scikit-learn).
- 🔴 **Task 1.1.3:** Tạo cấu trúc thư mục (src, data, notebooks, tests).

### 1.2 Pipeline xử lý dữ liệu OCR (ETL)
- 🔴 **Task 1.2.1:** Viết hàm Regex để lọc bỏ các header/footer thừa (`===== PAGE 1 =====`).
- 🔴 **Task 1.2.2:** Viết hàm BeautifulSoup tìm và bóc tách các thẻ `<table>` HTML.
- 🔴 **Task 1.2.3:** Viết hàm làm sạch DataFrame (xử lý gộp ô/merged cells, điền NaN, chuẩn hóa kiểu dữ liệu số).
- 🔴 **Task 1.2.4:** Viết hàm trích xuất phần văn bản (Text) ngoài bảng biểu.
- 🔴 **Task 1.2.5:** Viết hàm Chunking (cắt văn bản thành đoạn 500 từ) và đính kèm Metadata (Mã CK, Năm, Loại báo cáo).

### 1.3 Thiết lập cơ sở dữ liệu DuckDB (Star Schema)
- 🔴 **Task 1.3.1:** Viết script SQL (DDL) tạo bảng `Dim_Company` (company_id, ticker, name).
- 🔴 **Task 1.3.2:** Viết script SQL (DDL) tạo bảng `Dim_Metric` (metric_id, raw_name, standard_name).
- 🔴 **Task 1.3.3:** Viết script SQL (DDL) tạo bảng `Fact_Financial` (id, company_id, metric_id, year, report_type, value).
- 🔴 **Task 1.3.4:** Viết script Python tự động insert dữ liệu từ các DataFrame (ở Task 1.2.3) vào DuckDB.

### 1.4 Xây dựng Từ điển Ánh xạ (Alias Dictionary)
- 🔴 **Task 1.4.1:** Viết query lấy ra danh sách tất cả các `raw_name` (tên chỉ tiêu thô) duy nhất từ DuckDB.
- 🔴 **Task 1.4.2:** Code thuật toán NLP (TF-IDF + K-Means) để gom nhóm (Cluster) các tên chỉ tiêu giống nhau.
- 🔴 **Task 1.4.3:** Viết script gọi API LLM (< 15B) duyệt qua từng Cụm (Cluster) để sinh ra `standard_name` (Tên chuẩn).
- 🔴 **Task 1.4.4:** Xuất kết quả ra file `Alias_Dictionary.json`.
- 🔴 **Task 1.4.5:** Review thủ công file JSON, đánh dấu `math_rule` (Ghi âm/Dương) cho các chỉ tiêu đặc thù.

---

## Giai đoạn 2 (Phase 2): Xây dựng Lõi Truy xuất Số liệu (Retrieval Core)

### 2.1 Xây dựng Golden Eval Set
- 🔴 **Task 2.1.1:** Lọc ngẫu nhiên 300 câu hỏi từ file `questions.jsonl`.
- 🔴 **Task 2.1.2:** Viết file JSON gán nhãn thủ công (Ground Truth) cho 300 câu hỏi này (Tên công ty, Năm, Chỉ tiêu gốc).
- 🔴 **Task 2.1.3:** Bổ sung thủ công 50 câu hỏi bẫy (thiếu năm, sai chính tả) vào tập Eval Set.

### 2.2 Trích xuất Ý định (Intent Extraction)
- 🔴 **Task 2.2.1:** Định nghĩa Pydantic Schema cho output JSON (VD: `class Intent(BaseModel)`).
- 🔴 **Task 2.2.2:** Viết System Prompt đóng vai chuyên gia tài chính.
- 🔴 **Task 2.2.3:** Lựa chọn và nhúng 5 ví dụ mẫu (Few-Shot Examples) vào Prompt.
- 🔴 **Task 2.2.4:** Viết hàm gọi API LLM, ép kiểu JSON output.

### 2.3 Ánh xạ Chỉ tiêu (Metric Resolution)
- 🔴 **Task 2.3.1:** Viết hàm Python load file `Alias_Dictionary.json` vào bộ nhớ.
- 🔴 **Task 2.3.2:** Sử dụng thư viện `RapidFuzz` để tính điểm so khớp (Similarity Score) giữa `metric_raw` và các alias trong từ điển.
- 🔴 **Task 2.3.3:** Code logic chặn ngưỡng: `>= 95` (Pass), `80-94` (Clarify), `< 80` (Fail).

### 2.4 Kiểm thử và Tối ưu (Eval Loop)
- 🔴 **Task 2.4.1:** Viết script chạy hàng loạt 350 câu hỏi qua Pipeline (Task 2.2 + 2.3).
- 🔴 **Task 2.4.2:** Viết hàm so sánh output của Pipeline với Ground Truth để tính Accuracy %.
- 🔴 **Task 2.4.3:** Chạy Eval lần 1, phân tích các câu bị sai.
- 🔴 **Task 2.4.4:** Tinh chỉnh Few-Shot Prompt hoặc cập nhật Alias Dictionary dựa trên lỗi ở Task 2.4.3. Lặp lại đến khi > 98%.

---

## Giai đoạn 3 (Phase 3): Tích hợp LangGraph Multi-Agent

### 3.1 Chuẩn bị Công cụ (Toolkits) & State
- 🔴 **Task 3.1.1:** Định nghĩa `AgentState` (TypedDict) chứa các biến: `query`, `intent`, `sql_data`, `context`, `final_answer`.
- 🔴 **Task 3.1.2:** Code Tool `query_duckdb(intent_json)` trả về Pandas DataFrame.
- 🔴 **Task 3.1.3:** Code Tool Toán học `calc_growth()`, `calc_median()`, `compare_metrics()`.

### 3.2 Lập trình các Agent Nodes
- 🔴 **Task 3.2.1:** Code **Router Agent**: Dùng LLM hoặc Regex phân loại câu hỏi (Định lượng/Định tính/Không rõ).
- 🔴 **Task 3.2.2:** Code **Data Analyst Agent**: Luồng xử lý gọi lõi truy xuất (Phase 2), gọi Tools (Task 3.1.2) và trả về dữ liệu.
- 🔴 **Task 3.2.3:** Khởi tạo CSDL Vector (Milvus/Qdrant/Chroma). Embed text chunks từ Task 1.2.5 nạp vào DB.
- 🔴 **Task 3.2.4:** Code **Researcher Agent**: Viết hàm Hybrid Search vào Vector DB kèm bộ lọc Metadata (Công ty, Năm).
- 🔴 **Task 3.2.5:** Code **Synthesizer Agent**: Prompt LLM đọc dữ liệu từ Data Analyst và Researcher, viết câu trả lời cuối, trích xuất nguồn (Citations).

### 3.3 Lắp ráp và Đóng gói LangGraph
- 🔴 **Task 3.3.1:** Khởi tạo `StateGraph`. Định nghĩa các Node (Router, Analyst, Researcher, Synthesizer).
- 🔴 **Task 3.3.2:** Định nghĩa các Cạnh có điều kiện (Conditional Edges) nối từ Router sang các Node khác.
- 🔴 **Task 3.3.3:** Thêm Node hỏi lại (Clarification) khi có lỗi thiếu thông tin. Cấu hình Interrupts (Dừng luồng chờ user).
- 🔴 **Task 3.3.4:** Compile Graph và chạy thử nghiệm bằng Terminal CLI.

---

## Giai đoạn 4 (Phase 4): Đưa vào sử dụng & Tối ưu

### 4.1 Xây dựng Backend API (FastAPI)
- 🔴 **Task 4.1.1:** Khởi tạo FastAPI app. Cấu hình CORS.
- 🔴 **Task 4.1.2:** Viết endpoint `POST /chat` nhận câu hỏi và kích hoạt Graph LangGraph.
- 🔴 **Task 4.1.3:** Implement WebSockets hoặc Server-Sent Events (SSE) để stream log của Agent về Client (VD: "Đang gọi DB...").
- 🔴 **Task 4.1.4:** Tích hợp `MemorySaver` của LangGraph để lưu State lịch sử hội thoại (Session ID).

### 4.2 Thiết kế Frontend (UI)
- 🔴 **Task 4.2.1:** Khởi tạo project Streamlit (hoặc Next.js).
- 🔴 **Task 4.2.2:** Xây dựng component Chat Box cơ bản (lưu lịch sử chat trên UI).
- 🔴 **Task 4.2.3:** Code logic lắng nghe SSE/WebSockets để hiển thị loading state của các Agent.
- 🔴 **Task 4.2.4:** Tích hợp `st.dataframe` hoặc thư viện Grid để hiển thị bảng số liệu gọn gàng.
- 🔴 **Task 4.2.5:** Xây dựng component Cột bên (Sidebar) để hiển thị Text Trích dẫn (Citations) khi người dùng bấm vào nguồn.

### 4.3 Vòng lặp phản hồi (Feedback Loop)
- 🔴 **Task 4.3.1:** Tạo bảng `logs_clarification` trong DB để lưu câu hỏi + metric bị fail (Confidence < 80%).
- 🔴 **Task 4.3.2:** Sửa Backend để mỗi lần RapidFuzz fail, tự động ghi log vào bảng này.
- 🔴 **Task 4.3.3:** Xây dựng 1 trang UI nội bộ (Admin Page) hiển thị danh sách các từ khóa bị fail.
- 🔴 **Task 4.3.4:** Viết hàm cho phép Admin gõ "Tên chuẩn" để map với từ fail, sau đó tự động lưu lại vào `Alias_Dictionary.json`.

### 4.4 Đóng gói và Bảo mật
- 🔴 **Task 4.4.1:** Viết `Dockerfile` cho Backend và `Dockerfile` cho Frontend.
- 🔴 **Task 4.4.2:** Cấu hình `docker-compose.yml` để chạy toàn bộ stack (App, DuckDB, VectorDB).
- 🔴 **Task 4.4.3:** Cài đặt Timeout (giới hạn số bước max_steps trong LangGraph) để chống Infinite Loop.
- 🔴 **Task 4.4.4:** (Tùy chọn) Thêm logic Authentication (Login/Password) cho Admin Page.
