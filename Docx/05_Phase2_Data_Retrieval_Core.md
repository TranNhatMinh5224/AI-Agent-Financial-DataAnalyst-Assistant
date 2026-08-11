# Chi Tiết Triển Khai Giai Đoạn 2: Xây dựng Lõi Truy xuất Số liệu (Data Retrieval Core)

Giai đoạn 2 tập trung vào việc biến đổi câu hỏi tự nhiên của người dùng thành các tham số máy tính có thể hiểu được, đảm bảo độ chính xác tuyệt đối trước khi tiến hành bất kỳ phép tính toán nào. Do rào cản sử dụng LLM mã nguồn mở dưới 15B tham số, trọng tâm của giai đoạn này là kỹ thuật **Few-Shot Prompting** và thuật toán **Khớp lệnh mờ (Fuzzy Matching)**.

## 1. Mục tiêu Giai đoạn 2
- Xây dựng thành công bộ máy trích xuất ý định (Intent Extraction) sử dụng LLM < 15B.
- Ánh xạ chính xác tên chỉ tiêu từ người dùng vào Từ điển Ánh xạ (Metric Resolution) bằng thuật toán truyền thống.
- Thiết lập cơ sở đánh giá (Golden Eval Set) để đo lường tự động độ chính xác của lõi truy xuất.
- Đạt mốc chính xác >98% trên tập test trước khi chuyển sang xây dựng Agent.

---

## 2. Chi tiết các Bước Thực thi

### Bước 2.1: Xây dựng Golden Eval Set (Tập dữ liệu Vàng)
Không thể cải thiện hệ thống nếu không thể đo lường nó. Bộ dữ liệu ViFinQA (file `questions.jsonl`) cung cấp sẵn hơn 1.000 câu hỏi, đây là nguồn lý tưởng để làm Golden Eval Set.

- **Hành động:** 
  1. Trích xuất khoảng 300 câu hỏi ngẫu nhiên từ `questions.jsonl` (tập trung vào các câu hỏi trích xuất số liệu và tính toán cơ bản).
  2. Gán nhãn thủ công (Ground Truth) cho 300 câu hỏi này dưới dạng JSON mong đợi. 
     - *Ví dụ câu hỏi:* "Lãi tiền gửi năm 2018 của công ty mẹ CTCP Hàng không Vietjet (VJC) là bao nhiêu triệu đồng?"
     - *Nhãn (Ground Truth):* `{"company_ticker": "VJC", "year": [2018], "scope": "mẹ", "metric_raw": "Lãi tiền gửi", "action": "extract"}`
  3. Bổ sung các "Câu hỏi bẫy" (thiếu năm, tên công ty sai chính tả) để kiểm tra khả năng bắt lỗi và hỏi lại (Clarification) của hệ thống.

### Bước 2.2: Trích xuất Ý định (Intent Extraction) với LLM < 15B
Các LLM < 15B (như Llama-3.1-8B, Qwen2.5-14B) có thể gặp khó khăn nếu yêu cầu sinh cấu trúc JSON phức tạp bằng Zero-shot. Giải pháp là sử dụng **Few-Shot Prompting** (cung cấp ví dụ mẫu).

- **Hành động:**
  1. Xây dựng một System Prompt mạnh mẽ, quy định rõ schema JSON đầu ra.
  2. Nhúng 5-10 ví dụ (Few-Shot) bao phủ các trường hợp khác nhau trực tiếp vào prompt để "dạy" mô hình cách trích xuất.
  3. Ép kiểu đầu ra thành cấu trúc JSON hợp lệ bằng cách sử dụng các framework hỗ trợ Structured Output (như `Outlines` hoặc cơ chế JSON mode của LLM).
  4. Các tham số cần trích xuất bao gồm: Mã công ty (hoặc tên), Năm/Giai đoạn, Loại báo cáo (Hợp nhất/Riêng lẻ), và Chuỗi chỉ tiêu gốc (`metric_raw`).

### Bước 2.3: Ánh xạ Chỉ tiêu (Metric Resolution)
Không dùng LLM để match tên chỉ tiêu vì tốn thời gian và dễ ảo giác. Chúng ta dùng code Python truyền thống.

- **Hành động:**
  1. Nhận chuỗi `metric_raw` từ Bước 2.2 (VD: "Lợi nhuận ròng").
  2. Sử dụng thư viện `RapidFuzz` (tối ưu tốc độ hơn FuzzyWuzzy) để so khớp chuỗi `metric_raw` với danh sách các chỉ tiêu trong `Alias_Dictionary.json` (được tạo ở Giai đoạn 1).
  3. Tính toán Điểm tự tin (Confidence Score - từ 0 đến 100).
  4. **Logic Xử lý:**
     - Nếu Điểm >= 95: Chấp nhận ánh xạ và lấy `metric_id` tương ứng.
     - Nếu 80 <= Điểm < 95: Hệ thống tự động trả về câu hỏi làm rõ (Clarification Prompt) cho người dùng: *"Ý bạn là 'Lợi nhuận sau thuế' hay 'Lợi nhuận thuần từ hoạt động kinh doanh'?"*
     - Nếu Điểm < 80: Thông báo không tìm thấy chỉ tiêu.

### Bước 2.4: Tự động hóa Kiểm thử và Đánh giá (Evaluation Loop)
Đưa Bước 2.2 và 2.3 vào một luồng chạy tự động để kiểm thử trên Golden Eval Set.

- **Hành động:**
  1. Chạy hàng loạt 300 câu hỏi qua Pipeline.
  2. Đo lường tỷ lệ LLM trích xuất đúng JSON (Format Accuracy).
  3. Đo lường tỷ lệ RapidFuzz ánh xạ đúng chỉ tiêu (Resolution Accuracy).
  4. Nếu tỷ lệ < 98%, tiến hành tinh chỉnh: Thêm ví dụ vào Few-Shot Prompt hoặc cập nhật thêm biến thể từ vựng vào Alias Dictionary. Lặp lại quá trình này (Iterate) đến khi đạt mục tiêu.

---

## 3. Đầu ra mong đợi (Deliverables) của Giai đoạn 1 & 2
Sau khi hoàn thành 2 giai đoạn đầu, kiến trúc ngầm (Backend Core) của hệ thống đã vững chắc:
1. **Module Intent Extractor:** Sẵn sàng chuyển đổi câu hỏi thành JSON chính xác với tốc độ cao.
2. **Module Metric Resolver:** Chức năng đối chiếu và lọc chỉ tiêu cứng cáp, không thể bị qua mặt bởi ảo giác.
3. **Eval Framework:** Script đánh giá tự động, giúp việc nâng cấp LLM (đổi sang model khác) sau này diễn ra an toàn mà không sợ hệ thống bị thoái lui (regression).

*Lõi truy xuất này sẽ đóng vai trò như "Trái tim" của Data Analyst Agent trong việc giao tiếp với cơ sở dữ liệu ở Giai đoạn 3.*
