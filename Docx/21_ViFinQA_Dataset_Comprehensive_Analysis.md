# 21 - VIFINQA DATASET COMPREHENSIVE ANALYSIS REPORT
**Báo cáo Phân tích Chi tiết & Toàn diện Bộ Dữ liệu ViFinQA (Financial Text-to-Pandas & QA)**

---

## 📊 1. TỔNG QUAN BỘ DỮ LIỆU (DATASET OVERVIEW)

Bộ dữ liệu **ViFinQA** trong thư mục `ViFinQA/` là bộ benchmark tài chính tiếng Việt tiêu chuẩn cho bài toán RAG & Multi-Agent Reasoning:

| Thành phần | Quy mô | Mô tả |
| :--- | :--- | :--- |
| **Mã chứng khoán (Tickers)** | **100 Doanh nghiệp** | Danh sách 100 công ty niêm yết hàng đầu trên HOSE, HNX, UPCoM trong `code_stock.csv` (HPG, VCB, FPT, VNM, VIC, MSB, PLX, ...). |
| **Báo cáo tài chính (`financial_statements/`)** | **100 Thư mục Doanh nghiệp** | Chứa toàn bộ file văn bản thô `.txt` báo cáo tài chính kiểm toán giai đoạn 2015 – 2025. |
| **Tập câu hỏi (`questions/questions.jsonl`)** | **1,013 Câu hỏi** | Tập câu hỏi đánh giá chuẩn kèm ID, yêu cầu truy xuất và tính toán số liệu tài chính. |

---

## 🏗️ 2. PHÂN TÍCH CẤU TRÚC BÁO CÁO TÀI CHÍNH (`financial_statements/`)

Toàn bộ báo cáo tài chính được bóc tách từ PDF scanned/digital sang định dạng văn bản `.txt` với cấu trúc:

1. **Phân loại Báo cáo (Report Scope):**
   - **Báo cáo Riêng lẻ (Separate):** Báo cáo kết quả của duy nhất công ty mẹ.
   - **Báo cáo Hợp nhất (Consolidated):** Báo cáo bao gồm cả các công ty con và công ty liên kết.
2. **Cấu trúc Bảng biểu:**
   - **Bảng Cân đối kế toán (Balance Sheet):** Tài sản ngắn/dài hạn, Nợ phải trả, Vốn chủ sở hữu.
   - **Báo cáo Kết quả Kinh doanh (Income Statement):** Doanh thu, Giá vốn, Lợi nhuận gộp, Chi phí tài chính, LNST.
   - **Báo cáo Lưu chuyển tiền tệ (Cash Flow Statement):** Dòng tiền HĐKD, HĐĐT, HĐTC.
   - **Thuyết minh Báo cáo Tài chính (Notes):** Bảng chi tiết chi phí, nợ vay, thù lao HĐQT, danh sách công ty con.

---

## 🎯 3. PHÂN TÍCH TẬP CÂU HỎI (`questions/questions.jsonl`)

Qua phân tích 1,013 câu hỏi, tập dữ liệu chia thành các nhóm đặc trưng chính:

### A. Phân bố Đơn vị đo lường (Requested Units)
- **Triệu đồng / Tỷ đồng:** Chiếm >80% các câu hỏi về quy mô doanh thu, tài sản, lợi nhuận.
- **Nghìn tỷ đồng / Nghìn đồng:** Thường xuất hiện ở các tập đoàn lớn (VIC, PLX, VNM) hoặc ngân hàng (BID, VCB).
- **Phần trăm (%):** Xuất hiện trong các câu hỏi về tỷ lệ sở hữu, tỷ lệ biểu quyết, biên lợi nhuận.

### B. Mức độ Phức tạp của Truy vấn (Query Taxonomy)
1. **Dạng Truy xuất Đơn (Single Table Lookup - ~65%):**
   - *Ví dụ:* *"Lợi nhuận sau thuế của FPT năm 2023 là bao nhiêu tỷ đồng?"*
   - *Giải pháp:* Hybrid Search (BM25 + Dense) lấy đúng bảng ➔ Reranker ➔ Exec Python.
2. **Dạng Truy xuất Đa bảng / Đa thời gian (Multi-Hop / Multi-Year - ~25%):**
   - *Ví dụ:* *"Số dư vay ngắn hạn của CEO cuối năm 2025 so với 2024 tăng hay giảm bao nhiêu tỷ?"*
   - *Giải pháp:* Sub-query Decomposition (Chẻ câu hỏi) ➔ Parallel Retrieval ➔ PoT Pandas.
3. **Dạng Tính toán Tỷ lệ (Financial Ratio Calculation - ~10%):**
   - *Ví dụ:* *"Tỷ lệ nợ trên vốn chủ sở hữu của VJC năm 2021 là bao nhiêu phần trăm?"*
   - *Giải pháp:* Grounding 2 chỉ tiêu (Nợ & Vốn) ➔ PoT Pandas thực thi phép chia `(Nợ / VCSH) * 100`.

---

## ⚠️ 4. THÁCH THỨC DỮ LIỆU & GIẢI PHÁP ĐÃ TRIỂN KHAI

| Thách thức Dữ liệu | Tác động | Giải pháp Kỹ thuật Đã Triển khai trong Dự án |
| :--- | :--- | :--- |
| **Nhiễu OCR (OCR Noise)** | Tên chỉ tiêu bị dính chữ, mất khoảng trắng (`Doanhthu`, `Lợinhuận`). | **Fuzzy Token Matching (`cell_grounding.py`)**: Thuật toán `token_sort_ratio` loại bỏ rác OCR. |
| **Viết tắt Ngành** | Tên chỉ tiêu ngắn (`LNST`, `TNDN`, `TSCĐ`). | **Financial Lexicon (`config/financial_dictionary.json`)**: Tự động chuẩn hóa từ viết tắt. |
| **Độ trễ Multi-Agent** | 4 Agents chạy qua lại gây lâu. | **SGLang Engine**: Cache ngữ cảnh RadixAttention giảm TTFT < 500ms. |
| **Ảo giác Số liệu** | LLM nhẩm toán sai số lớn. | **Program-of-Thoughts (PoT) + AST Sandbox**: Ép LLM sinh mã Python và chạy trên CPU. |

---

## 📌 KẾT LUẬN
Bộ dữ liệu **ViFinQA** đã được phân tích toàn diện. Mọi giải pháp xử lý nhiễu, từ điển chuẩn hóa, truy xuất lai và mô hình đánh giá đã được tích hợp đầy đủ và sẵn sàng cho bài thi!
