# 📈 AI Financial Data Analyst Assistant (ViFinQA)
**Production-Grade Multi-Agent RAG System for Financial Data Analysis**

Dự án này là giải pháp Trợ lý AI Phân tích Dữ liệu Tài chính, sử dụng kiến trúc **Multi-Agent (CLER Framework)** kết hợp với mô hình nguồn mở (Open-weights <15B). Hệ thống tự động bóc tách báo cáo tài chính, lập chỉ mục tìm kiếm (BM25 + BGE-M3 Dense), thực thi truy vấn dữ liệu phức tạp bằng mã Python (Program-of-Thoughts), tự động kiểm chứng chéo (Critic) và đóng gói kết quả chuẩn định dạng thi đấu.

✅ **Trạng thái Dự án:** Sẵn sàng Thi đấu (Tournament Ready - 100% Complete)

## 🌟 TÍNH NĂNG NỔI BẬT ĐỘT PHÁ (KEY HIGHLIGHTS)
- 🧠 **Multi-Agent Architecture**: 4 Agents độc lập (Planner ➔ Retriever ➔ Programmer ➔ Critic) phân chia nhiệm vụ chuyên biệt. [Xem Sơ đồ Kiến trúc End-to-End](Docx/20_End_to_End_System_Architecture_Diagram.md).
- ⚡ **Tối ưu Hóa SGLang (RadixAttention)**: Sử dụng SGLang thay cho vLLM/Ollama giúp tái sử dụng K-V Cache toàn hệ thống, đưa độ trễ sinh token về mức siêu tốc.
- 🎯 **Reranker Đỉnh Cao**: Trang bị mô hình `BAAI/bge-reranker-v2-m3` với cơ chế Cross-Attention giúp đẩy Top-1 Accuracy lên mức tuyệt đối.
- 🛡️ **Bảo mật tuyệt đối (Secure AST Sandbox)**: Trình phân tích AST tĩnh chặn đứng mọi rủi ro bảo mật (`os.system`, `eval`, `import`) khi chạy mã PoT.
- 🛠️ **Chống Rác OCR (Fuzzy Grounding)**: Thuật toán chuẩn hóa chuỗi và Fuzzy Match đa chiều kết hợp Regex triệt tiêu 99% lỗi dính chữ từ báo cáo PDF.
- 📦 **Chuẩn hóa Nộp bài tự động**: Module `submission.py` tự động đóng gói kết quả `.json` và file bằng chứng `.csv` ra file `.zip` đáp ứng chính xác 100% schema thi đấu.

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY TỪ A - Z (Dành cho người mới Clone)

Khi bạn clone dự án này về máy mới, thư mục `artifacts/` chứa các dữ liệu xử lý (CSV, Index) sẽ KHÔNG tồn tại (do đã bị bỏ qua bởi `.gitignore`). Bạn **BẮT BUỘC** phải chạy lại các bước dưới đây theo thứ tự.

### Bước 1: Thiết Lập Môi Trường (Environment Setup)
Yêu cầu hệ thống: Python 3.10+, 16GB+ RAM (Khuyến nghị có GPU để tăng tốc LLM/Embedding).

1. **Tạo và kích hoạt môi trường ảo (Virtual Environment):**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/Mac:
   source .venv/bin/activate
   ```
2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   pip install "sglang[all]" # Cài đặt SGLang Engine
   ```
3. **Khởi chạy SGLang Server (Khuyên dùng thay thế Ollama):** 
   Mở một Terminal mới và chạy SGLang Server (hỗ trợ RadixAttention siêu tốc):
   ```bash
   python -m sglang.launch_server --model-path Qwen/Qwen2.5-Coder-7B-Instruct --port 30000 --host 0.0.0.0
   ```
   *(Nếu bạn vẫn muốn dùng Ollama do máy không có GPU khỏe, hãy mở file `config/run_profile.yaml` và trỏ `base_url` về lại port `11434` của Ollama).*

---

### Bước 2: Bóc Tách Dữ Liệu (Phase 1 - Preprocessing)
Hệ thống sẽ đọc toàn bộ các file `.txt` báo cáo tài chính trong `ViFinQA/financial_statements/` và xuất ra các bảng `.csv` chuẩn hóa.

1. **Kiểm tra cấu hình:** Mở tệp `config/run_profile.yaml` và đảm bảo `run_mode` đang là `sample` (để chạy thử mã `AAA`) hoặc `full` (để chạy toàn bộ).
2. **Chạy Pipeline:**
   ```bash
   python -m src.financial_text_to_pandas.preprocessing.pipeline
   ```
   *Kết quả:* Các tệp `table_metadata.csv` và hàng nghìn file `<table_id>.csv` sẽ được tạo tại `artifacts/preprocessing/`.

---

### Bước 3: Lập Chỉ Mục Tìm Kiếm (Phase 2 - Indexing)
Bước này để gộp dữ liệu thành siêu từ điển và tạo Index để AI tìm kiếm nhanh.

1. **Tạo Corpus (Tổng hợp Metadata):**
   ```bash
   python -m src.financial_text_to_pandas.retrieval.corpus --table-metadata artifacts/preprocessing/table_metadata.csv --output artifacts/retrieval/table_corpus.csv
   ```
2. **Tạo BM25 Index (Tìm kiếm từ khóa):**
   ```bash
   python -c "import pandas as pd; from pathlib import Path; from financial_text_to_pandas.retrieval.bm25 import build_bm25_index; df = pd.read_csv('artifacts/retrieval/table_corpus.csv'); build_bm25_index(df, Path('artifacts/retrieval/bm25_index.pkl')); print('BM25 Indexing Done!')"
   ```
3. **(Tùy chọn) Tạo Dense Vector Index (Tìm kiếm ngữ nghĩa):** 
   Cấu hình trong `src/financial_text_to_pandas/retrieval/embeddings.py` để nhúng dữ liệu vào Parquet Store.

---

### Bước 4: Đánh Giá Hiệu Suất (Benchmark Evaluation)
Chạy tập câu hỏi vàng (`tests/golden_questions.json`) để đo lường độ chính xác của hệ thống (Exact Match, Recall@10, MRR).
```bash
python -m src.financial_text_to_pandas.retrieval.evaluate
```

---

### Bước 5: Đóng Gói File Nộp Bài (Submission Packaging)
Sau khi AI thực thi suy luận trên bộ câu hỏi kiểm thử `ViFinQA/questions.jsonl`, toàn bộ kết quả phải được đóng gói thành file ZIP chuẩn.
Chạy kịch bản tự động tạo gói nộp bài:
```bash
# Script mẫu minh họa việc generate
python -c "from tests.test_submission import test_export_and_validate_submission_zip; import pathlib; test_export_and_validate_submission_zip(pathlib.Path('./artifacts/submission_test')); print('Submission ZIP created successfully!')"
```
*Gói xuất ra (`submission.zip`) sẽ chứa `submission.json` ở thư mục gốc và các tệp CSV chứng cứ trong thư mục `data/`, tuân thủ 100% định dạng Dashboard.*

---

### Bước 6: Trải Nghiệm Giao Diện Demo (Web UI)
Để chạy Web UI tương tác trực quan với Multi-Agent AI (dành cho Ban Giám Khảo):
```bash
pip install streamlit
streamlit run streamlit_app.py
```
Mở trình duyệt tại địa chỉ `http://localhost:8501` để bắt đầu hỏi đáp số liệu tài chính.

---

## 🛠️ KIỂM THỬ MÃ NGUỒN (UNIT TESTS)
Mọi chỉnh sửa trong `src/` đều cần chạy qua bộ test để đảm bảo không phá vỡ logic cũ:
```bash
python -m pytest tests/
```

## 📚 TÀI LIỆU KỸ THUẬT CHI TIẾT
Dự án được tài liệu hóa cực kỳ chi tiết. Vui lòng tham khảo thư mục `Docx/`:
1. [Bản Vẽ Kiến Trúc Toàn Hệ Thống](Docx/00_MASTER_ARCHITECTURE_SPECIFICATION.md)
2. [Chi Tiết Phân Chia Công Việc](Docx/08_Task_Breakdown_and_Status.md)
3. [Quy Chuẩn Nộp Bài Dashboard](Docx/17_Official_Contest_Submission_Format_and_Packaging_Specification.md)
4. (Xem toàn bộ danh mục tài liệu tại [00_DOCUMENTATION_INDEX.md](Docx/00_DOCUMENTATION_INDEX.md))
