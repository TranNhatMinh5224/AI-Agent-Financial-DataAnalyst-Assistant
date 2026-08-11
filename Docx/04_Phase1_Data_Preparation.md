# Chi Tiết Triển Khai Giai Đoạn 1: Chuẩn bị & Chuẩn hóa Dữ liệu (Data Preparation & Ingestion)

Giai đoạn 1 là chặng đường quan trọng và tốn nhiều công sức nhất của dự án, quyết định trực tiếp đến sự thành bại của hệ thống AI. Khó khăn lớn nhất nằm ở việc biến đổi dữ liệu thô, phân mảnh từ bộ ViFinQA thành cấu trúc dữ liệu tiêu chuẩn (Star Schema) để chuẩn bị cho các bước truy vấn chính xác.

## 1. Mục tiêu Giai đoạn 1
- Trích xuất thành công 100% dữ liệu bảng biểu từ các file báo cáo dạng `.txt` (có chứa HTML Table nội tuyến) của 1.973 báo cáo tài chính.
- Lưu trữ dữ liệu số liệu (Bảng biểu) vào cơ sở dữ liệu quan hệ (DuckDB/PostgreSQL).
- Cắt nhỏ (Chunking) và lưu trữ dữ liệu văn bản (Thuyết minh, Báo cáo rủi ro) vào cơ sở dữ liệu Vector.
- Hoàn thành bộ **Alias Dictionary (Từ điển Ánh xạ)** chuẩn hóa cho các ngành cốt lõi.

---

## 2. Chi tiết các Bước Thực thi

### Bước 1.1: Trích xuất và Tiền xử lý dữ liệu thô (ETL Pipeline)
Dữ liệu của ViFinQA hiện tại không phải là file CSV sạch, mà là các file `.txt` được OCR có lẫn ranh giới trang (`===== PAGE 1 =====`) và các thẻ HTML (`<table>...</table>`).

- **Hành động:** 
  1. Xây dựng một module Python (sử dụng `BeautifulSoup` và Regular Expressions).
  2. Quét qua toàn bộ thư mục `financial_statements/`.
  3. **Phân tách luồng:**
     - Nếu gặp thẻ `<table>`: Trích xuất HTML Table chuyển thành Pandas DataFrame, làm sạch các cột/dòng bị gộp (merged cells) do lỗi OCR, loại bỏ ký tự rác.
     - Nếu là văn bản thường: Nối các dòng lại, cắt thành các Chunk (khoảng 500-1000 từ), thêm siêu dữ liệu (Metadata: Mã CK, Năm, Loại Báo Cáo) và lưu trữ tạm thời để chuẩn bị đưa vào Vector DB.

### Bước 1.2: Thiết kế Lược đồ CSDL Quan hệ (Star Schema)
Để Data Analyst Agent có thể truy vấn số liệu siêu tốc, dữ liệu bảng biểu phải được nạp vào cơ sở dữ liệu quan hệ (khuyến nghị dùng DuckDB để phân tích nhanh).

- **Hành động:** Xây dựng Lược đồ hình sao (Star Schema).
  - **Fact_Financial_Data:** Bảng chứa số liệu trung tâm.
    - Các trường: `id`, `company_id`, `metric_id`, `year`, `value` (kiểu Float), `unit` (Đơn vị: Tỷ, Triệu...).
  - **Dim_Company:** Bảng chứa thông tin công ty.
    - Các trường: `company_id`, `ticker` (Mã CK), `company_name`, `industry` (Ngành nghề).
  - **Dim_Metric:** Bảng chứa định nghĩa chỉ tiêu gốc.
    - Các trường: `metric_id`, `raw_name` (Tên gốc trong báo cáo), `standard_name` (Tên chuẩn).

### Bước 1.3: Tự động hóa xây dựng Từ điển Ánh xạ (Alias Dictionary)
Với hàng ngàn biến thể tên gọi khác nhau do lỗi OCR hoặc cách gọi của từng công ty (VD: "Lợi nhuận sau thuế", "LNST", "Lợi nhuận ròng của công ty mẹ"), việc tự làm bằng tay là bất khả thi.

- **Hành động:**
  1. Xuất danh sách toàn bộ các tên chỉ tiêu (`raw_name`) từ bước 1.1.
  2. Viết script kết hợp các thuật toán NLP truyền thống (TF-IDF + K-Means hoặc thuật toán khoảng cách Levenshtein) để **gom nhóm (Clustering)** sơ bộ các tên gọi này. Sau đó dùng mô hình LLM (< 15B) chạy ngầm (Batch Processing) để duyệt từng cụm và gợi ý Tên chuẩn (Standard Name).
  3. Tạo ra cấu trúc file `Alias_Dictionary.json` phân tách theo Namespace:
     - `Namespace: Ngân Hàng` (Theo chuẩn B02/TCTD-HN)
     - `Namespace: Doanh Nghiệp` (Theo chuẩn B 02-DN/HN)
  4. Đội ngũ phát triển (hoặc chuyên gia tài chính) thực hiện kiểm duyệt (Review) lại file JSON này một lần cuối để đảm bảo độ chuẩn xác.
  5. Đánh dấu (Flag) các chỉ tiêu có tính chất "Ghi âm" (như *Chi phí dự phòng*, *Lỗ tỷ giá*) để đảm bảo hệ thống hiểu đúng bản chất toán học.

---

## 3. Đầu ra mong đợi (Deliverables) của Giai đoạn 1
Kết thúc 3 tuần của Giai đoạn 1, hệ thống phải có sẵn:
1. File cơ sở dữ liệu `financial_data.duckdb` chứa toàn bộ số liệu của 1.973 báo cáo.
2. File `Alias_Dictionary.json` đã được kiểm duyệt.
3. Bộ mã nguồn (Scripts) Python phục vụ cho việc ETL (nhằm tái sử dụng nếu sau này có báo cáo năm 2026, 2027 được đưa vào).
4. Dữ liệu văn bản phi cấu trúc đã sẵn sàng để được Embedding ở Giai đoạn 3.

*Lưu ý: Sự kỹ lưỡng ở Giai đoạn 1 chính là nền móng để Router Agent và Data Analyst Agent tỏa sáng ở các giai đoạn sau.*
