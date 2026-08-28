# 18 - QUICKSTART RUNBOOK A TO Z
**Dành cho người mới clone dự án / Thiết lập môi trường sạch**

Tài liệu này cung cấp các bước thi công thực tế (Actionable Steps) để triển khai dự án từ mã nguồn trắng (không có thư mục artifacts) đến khi hệ thống có thể chạy Benchmark và đưa ra file `submission.zip`.

---

## 🏗️ 1. Cài Đặt Môi Trường (Environment Setup)

1. **Khởi tạo môi trường ảo Python (Virtual Environment):**
   ```bash
   python -m venv .venv
   
   # Trên Windows:
   .venv\Scripts\activate
   # Trên Mac/Linux:
   source .venv/bin/activate
   ```

2. **Cài đặt thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Bao gồm: `pandas`, `beautifulsoup4`, `numpy`, `streamlit`, `pytest`, v.v...)*

3. **Cài đặt & Khởi chạy SGLang Server (Tối ưu RadixAttention cho Multi-Agent):**
   Thay vì dùng Ollama, hệ thống này được thiết kế để chạy tốt nhất với SGLang (giúp tái sử dụng K-V Cache cho các Agent).
   ```bash
   pip install "sglang[all]"
   
   # Mở terminal mới và chạy:
   python -m sglang.launch_server --model-path Qwen/Qwen2.5-Coder-7B-Instruct --port 30000 --host 0.0.0.0
   ```
   *(File cấu hình `config/run_profile.yaml` đã trỏ mặc định cổng `30000` của SGLang. Nếu máy bạn không đủ GPU và phải dùng Ollama, hãy đổi `base_url` trong file config về `11434`)*.

---

## ⚙️ 2. Giai Đoạn 1: Tiền Xử Lý Dữ Liệu (Preprocessing)
Do `.gitignore` loại bỏ các file dung lượng lớn, bạn phải tự "dịch" bộ dữ liệu thô `ViFinQA/financial_statements/*.txt` thành các file CSV.

1. **Điều chỉnh cấu hình (Tùy chọn):** Mở `config/run_profile.yaml` để thiết lập số lượng báo cáo muốn chạy (`sample_limit_reports`).
2. **Khởi chạy Pipeline bóc tách (Extract & Clean):**
   ```bash
   python -m src.financial_text_to_pandas.preprocessing.pipeline
   ```
   **Kết quả mong đợi:** 
   Thư mục `artifacts/preprocessing/` được tạo ra, bên trong có `table_metadata.csv` và hàng loạt thư mục con chứa các file `.csv` của từng bảng biểu.

---

## 🔍 3. Giai Đoạn 2: Lập Chỉ Mục (Indexing & Retrieval)
Chuyển đổi dữ liệu CSV thành các siêu dữ liệu để công cụ tìm kiếm có thể truy vấn nhanh chóng.

1. **Tạo Kho Tìm Kiếm (Corpus Generator):**
   ```bash
   python -m src.financial_text_to_pandas.retrieval.corpus --table-metadata artifacts/preprocessing/table_metadata.csv --output artifacts/retrieval/table_corpus.csv
   ```

2. **Tạo Chỉ mục Từ Khóa (BM25 Index):**
   ```bash
   python -c "import pandas as pd; from pathlib import Path; from financial_text_to_pandas.retrieval.bm25 import build_bm25_index; df = pd.read_csv('artifacts/retrieval/table_corpus.csv'); build_bm25_index(df, Path('artifacts/retrieval/bm25_index.pkl')); print('BM25 Indexing Done!')"
   ```

3. **Tạo Chỉ mục Vector (Dense Embedding):**
   *(Tự động trích xuất bằng BGE-M3 khi chạy hàm đánh giá, hoặc chạy thủ công qua class `EmbeddingStore`)*.

---

## ⚖️ 4. Giai Đoạn 3 & 4: Suy Luận & Kiểm Chứng (Reasoning & Evaluation)

1. **Chạy thử bộ Test QA (Đánh giá Metrics):**
   Sử dụng tập dữ liệu chuẩn ở `tests/golden_questions.json` để đánh giá mức độ chính xác của hệ thống:
   ```bash
   python -m src.financial_text_to_pandas.retrieval.evaluate
   ```

2. **Tạo Gói Nộp Bài Dashboard (Submission Zip):**
   Sau khi hoàn thiện chạy trên toàn bộ tập `ViFinQA/questions.jsonl`, dùng lệnh sau để hệ thống tự động kiểm tra định dạng và đóng gói:
   ```bash
   python -c "from tests.test_submission import test_export_and_validate_submission_zip; import pathlib; test_export_and_validate_submission_zip(pathlib.Path('./artifacts/submission_test')); print('Submission ZIP created successfully!')"
   ```
   File đầu ra `submission.zip` đã chuẩn bị sẵn sàng để up lên Leaderboard!

---

## 🌐 5. Giao Diện Trình Diễn (Web UI Demo)
Để chứng minh năng lực Multi-Agent cho Ban Giám Khảo (hoặc tự test trực quan), hệ thống tích hợp sẵn giao diện Streamlit:

```bash
streamlit run streamlit_app.py
```
> Trình duyệt sẽ tự động mở trang web tại `http://localhost:8501`. Tại đây, bạn có thể gõ các câu hỏi tài chính và theo dõi luồng lập luận chi tiết của từng Agent (Planner, Retriever, Programmer, Critic) như trong một môi trường thực tế.
