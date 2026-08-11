# Kiến Trúc Hệ Thống (System Architecture)

Dự án áp dụng phương pháp **Kiến trúc Dữ liệu Lai (Hybrid Data Pipeline)** kết hợp **Định tuyến Tham số (Parameterized Routing Multi-Agent)** để đạt độ chính xác tối đa.

## 1. Nguyên lý Thiết kế (Core Principles)
- **Phân tách Dữ liệu:** Số liệu định lượng (Quantitative) lưu vào CSDL Quan hệ (SQL). Văn bản định tính (Qualitative) lưu vào CSDL Vector.
- **Truy vấn Tham số hóa (Parameterized Query):** LLM không được quyền tự viết câu lệnh SQL thô. Thay vào đó, LLM trích xuất tham số (Intent Extraction), và hệ thống tự điền vào các SQL Template đã được chuẩn hóa.
- **Kiểm soát & Xác thực (Sanity Check):** Thiết lập ngưỡng tin cậy (Confidence Threshold). Nếu kết quả ánh xạ chỉ tiêu dưới 95%, hệ thống sẽ kích hoạt cơ chế hỏi lại người dùng (Clarification) thay vì tự đoán và gây ra sai số.

## 2. Đường ống Dữ liệu (Data Pipeline)
- **Nhánh Structured (Bảng biểu):** Dữ liệu đi qua module chuẩn hóa (Python), bóc tách và nạp vào cơ sở dữ liệu SQL theo Lược đồ hình sao (Star Schema). Bao gồm Bảng Fact (chứa số liệu) và Bảng Dimension (chứa mô tả chi tiết công ty, thời gian).
- **Nhánh Unstructured (Văn bản):** Các đoạn thuyết minh được cắt nhỏ (Chunking), mã hóa (Embedding) và lưu vào Vector DB để chạy Hybrid Search (kết hợp Semantic Search và BM25).
- **Alias Dictionary:** Bộ từ điển ánh xạ giúp chuẩn hóa tên các chỉ tiêu tài chính, được phân tách theo Namespace (Ngân hàng, Doanh nghiệp) và có đánh dấu quy tắc toán học (chỉ tiêu ghi âm/dương).

## 3. Kiến Trúc Multi-Agent (LangGraph)
Hệ thống sử dụng Framework LangGraph để tổ chức luồng làm việc của các AI Agent độc lập:

1. **Router Agent (Tầng Điều phối):** Phân tích câu hỏi của người dùng và điều hướng luồng.
    - Trích xuất Intent ra cấu trúc JSON (Mã công ty, Năm, Chỉ tiêu).
    - Phân luồng nhanh (Fast-path) cho câu hỏi lấy số liệu thô hoặc phân luồng sâu (Deep-path) cho câu hỏi tìm nguyên nhân.
2. **Data Analyst Agent (Tầng Số liệu):**
    - Nhận các biến số đã được ánh xạ qua Metric Resolution.
    - Thực thi SQL Template để truy xuất số liệu chính xác từ CSDL SQL.
    - Đối với các câu hỏi phức tạp đòi hỏi logic cao (tính trung vị, phần trăm), thay vì để LLM (< 15B) tự do sinh mã Python (rất dễ sai logic), Agent sẽ được cung cấp bộ **Công cụ Toán học lập trình sẵn (Pre-defined Python Tools)** (ví dụ: `tinh_tang_truong()`, `tinh_trung_vi()`). LLM chỉ làm nhiệm vụ Function Calling truyền đúng tham số vào các hàm này.
3. **Researcher Agent (Tầng Đọc hiểu):**
    - Thực hiện Hybrid Search trên Vector DB.
    - Tìm kiếm nguyên nhân, sự kiện từ các đoạn thuyết minh báo cáo tài chính (Metadata Filtering chặt chẽ theo Mã Công Ty & Năm).
4. **Synthesizer & Validator Agent (Tầng Tổng hợp):**
    - Nhận kết quả thô từ Data Analyst và Researcher.
    - Tổng hợp câu trả lời cuối cùng bằng ngôn ngữ tự nhiên.
    - **Yêu cầu Bắt buộc:** Đính kèm trích dẫn (Citations) chính xác từ file tài liệu/báo cáo gốc.
