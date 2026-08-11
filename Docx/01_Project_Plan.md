# Kế Hoạch Dự Án: AI Agent Financial Data Analyst Assistant

## 1. Tổng quan dự án
Dự án xây dựng một Trợ lý AI Phân tích Dữ liệu Tài chính chuyên nghiệp, có khả năng đọc hiểu, truy xuất và tính toán các chỉ tiêu tài chính từ hàng ngàn báo cáo tài chính của các công ty niêm yết tại Việt Nam.

## 2. Mục tiêu cốt lõi
Hệ thống phải đáp ứng các tiêu chuẩn khắt khe nhất của ngành tài chính:
- **Chính xác tuyệt đối về số liệu:** Tránh tuyệt đối lỗi tính toán.
- **Không có "ảo giác ngầm" (Silent Hallucination):** AI không được tự bịa ra số liệu. Nếu không chắc chắn, phải hỏi lại người dùng.
- **Truy xuất siêu tốc và có nguồn gốc (Traceability):** Mọi kết quả trả về đều phải có trích dẫn nguồn (báo cáo nào, năm nào).

## 3. Lộ trình triển khai (Roadmap)

### Giai đoạn 1: Chuẩn bị và Chuẩn hóa Dữ liệu (Tuần 1 - 3)
- **Xử lý dữ liệu OCR:** Trích xuất và làm sạch dữ liệu từ các file văn bản có chứa HTML Table của bộ ViFinQA.
- **Xây dựng Data Pipeline:** Chuyển đổi dữ liệu bảng biểu (Structured) sang định dạng CSDL quan hệ (Star Schema).
- **Thiết lập Alias Dictionary:** Xây dựng từ điển ánh xạ các chỉ tiêu tài chính theo chuẩn báo cáo (Ngân hàng, Doanh nghiệp).

### Giai đoạn 2: Xây dựng Lõi Truy xuất Số liệu (Tuần 4 - 6)
- **Golden Eval Set:** Tạo bộ dữ liệu kiểm thử (Benchmark) với hàng ngàn câu hỏi mẫu.
- **Phát triển Intent Extraction & Metric Resolution:** Dùng LLM trích xuất tham số và Python Fuzzy Match để ánh xạ chỉ tiêu tự động.
- **Testing:** Chạy thử nghiệm và tinh chỉnh thuật toán đến khi đạt độ chính xác >98%.

### Giai đoạn 3: Tích hợp Multi-Agent & RAG (Tuần 7 - 9)
- **Lập trình LangGraph:** Xây dựng luồng Multi-Agent (Router, Data Analyst, Researcher, Synthesizer).
- **Tích hợp Vector DB:** Đưa các văn bản phi cấu trúc (thuyết minh, rủi ro) vào CSDL Vector để truy vấn lai (Hybrid Search).
- **Tích hợp Python Sandbox:** Xây dựng môi trường an toàn để Data Analyst Agent thực thi mã Python/Pandas cho các phép tính toán thống kê phức tạp.

### Giai đoạn 4: Đưa vào sử dụng & Tối ưu (Tuần 10+)
- **UI/UX:** Thiết kế giao diện tương tác cho người dùng.
- **Feedback Loop:** Theo dõi log hệ thống (đặc biệt là các câu hỏi bị hỏi lại) để liên tục cập nhật và làm giàu Alias Dictionary.
