# Chi Tiết Triển Khai Giai Đoạn 4: Đưa vào sử dụng và Tối ưu hóa (Deployment & Optimization)

Giai đoạn 4 là bước cuối cùng trong vòng đời dự án, nhằm chuyển đổi một lõi AI Backend vững chắc thành một ứng dụng hoàn chỉnh, thân thiện với người dùng cuối (Nhà đầu tư, Chuyên viên phân tích) và có khả năng tự cải thiện (Self-improving) theo thời gian.

## 1. Mục tiêu Giai đoạn 4
- Đóng gói (Containerize) toàn bộ hệ thống Multi-Agent và Data Pipeline.
- Xây dựng giao diện người dùng (UI) trực quan, có khả năng hiển thị cả số liệu bảng biểu lẫn văn bản trích dẫn.
- Thiết lập vòng lặp phản hồi (Feedback Loop) để liên tục tối ưu hóa hệ thống mà không cần lập trình lại lõi thuật toán.

---

## 2. Chi tiết các Bước Thực thi

### Bước 4.1: Xây dựng Backend API (FastAPI)
Lõi LangGraph cần được bọc trong một RESTful API hiệu năng cao để có thể giao tiếp với giao diện người dùng.

- **Hành động:**
  - Sử dụng **FastAPI** (Python) để tạo các endpoint API bất đồng bộ (Asynchronous).
  - Đóng gói API dưới dạng giao tiếp WebSocket hoặc Server-Sent Events (SSE) để có thể **Stream (truyền phát) từng bước suy nghĩ của Agent** (Ví dụ: Hiển thị trạng thái *"Đang tìm kiếm dữ liệu công ty VNM năm 2023..."* lên màn hình cho người dùng đỡ sốt ruột).
  - Tích hợp bộ nhớ hội thoại (Conversation Memory) thông qua LangGraph check-pointer để AI có thể nhớ ngữ cảnh của các câu hỏi trước đó trong cùng một phiên chat.

### Bước 4.2: Thiết kế Giao diện Người dùng (UI/UX)
Hệ thống tài chính yêu cầu giao diện phải chuyên nghiệp, minh bạch và có khả năng hiển thị đa phương tiện (Bảng biểu, Biểu đồ, Chú thích).

- **Hành động:**
  - Sử dụng **Streamlit** (để triển khai nhanh) hoặc **Next.js + React** (để có giao diện Web App chuyên nghiệp, chuẩn Enterprise).
  - **Thiết kế tính năng hiển thị:**
    1. **Khung Chat:** Nơi người dùng nhập câu hỏi tự nhiên.
    2. **Khung Data Table:** Tự động render Pandas DataFrame thành bảng số liệu trực quan (có thể sắp xếp, lọc) khi Agent trả về kết quả định lượng.
    3. **Khung Trích dẫn (Citations):** Một thanh side-bar hiển thị đoạn văn bản gốc (kèm ảnh chụp trang báo cáo nếu có) chứng minh cho câu trả lời, giúp người dùng dễ dàng kiểm chứng chéo (Cross-check).

### Bước 4.3: Vòng lặp Phản hồi và Tối ưu (Feedback Loop)
Hệ thống AI không bao giờ hoàn hảo ngay từ ngày đầu. Sẽ có những câu hỏi dùng "tiếng lóng" tài chính mà hệ thống chưa hiểu.

- **Hành động:**
  1. **Ghi log câu hỏi "Hỏi lại" (Clarification Logs):** Khi RapidFuzz không match được tên chỉ tiêu (Confidence Score < 80%) hoặc (80% - 95%), câu hỏi gốc của người dùng sẽ được lưu vào cơ sở dữ liệu Log.
  2. **Làm giàu Alias Dictionary:** Định kỳ (hàng tuần), các Data Engineer sẽ xem lại bảng Log này. Nếu phát hiện một cụm từ lóng (Ví dụ: người dùng hay gõ "Lãi ròng" thay vì "Lợi nhuận sau thuế"), kỹ sư chỉ cần bổ sung từ "Lãi ròng" vào file `Alias_Dictionary.json`.
  3. **Cải tiến mà không cần Code:** Nhờ kiến trúc này, chất lượng hệ thống (Resolution Accuracy) sẽ ngày càng tăng lên chỉ bằng việc thao tác trên file JSON từ điển, hoàn toàn không phải động vào code lõi hay huấn luyện lại LLM.

### Bước 4.4: Bảo mật và Kiểm soát tài nguyên
Với việc dùng Agent sinh mã Python hoặc gọi hàm nội bộ, cần có lớp rào chắn an ninh.

- **Hành động:**
  - Thiết lập **Docker Container** cách ly hoàn toàn (Sandbox) cho các tiến trình chạy code Python (nếu có tính toán động).
  - Cấu hình Timeout nghiêm ngặt cho LangGraph (ví dụ max_steps = 10) để tránh trường hợp Agent bị kẹt trong vòng lặp vô hạn (Infinite loop) làm tốn tài nguyên server.

---

## 3. Tổng kết Dự Án (Project Wrap-up)
Kết thúc Giai đoạn 4, chúng ta đã có một sản phẩm **AI Financial Data Analyst Assistant** hoàn chỉnh.
- **Giá trị cốt lõi mang lại:** Thay vì phải mở hàng chục file PDF dài hàng trăm trang và loay hoay dò tìm từng con số, người dùng (Data Analyst, Nhà đầu tư) chỉ cần đặt một câu hỏi bằng tiếng Việt, và AI Agent sẽ trả về chính xác bảng số liệu, kèm theo phân tích nguyên nhân và trích dẫn minh bạch.
- **Sự bền vững:** Do sử dụng LLM mã nguồn mở (< 15B) chạy Local kết hợp với các thuật toán Deterministic (Fuzzy Match, SQL), hệ thống đảm bảo 100% tính bảo mật dữ liệu công ty và miễn nhiễm hoàn toàn với rủi ro "ảo giác" chết người trong ngành tài chính.
