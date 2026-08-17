# AI Financial Data Analyst Assistant

Hệ thống AI phân tích dữ liệu tài chính (Text-to-Pandas QA Engine) tự động đọc, xử lý và phân tích hàng nghìn báo cáo tài chính bằng tiếng Việt. Sử dụng mô hình **Qwen2.5-Coder** chạy hoàn toàn offline (Ollama) kết hợp với công nghệ Retrieval-Augmented Generation (RAG) và Program-of-Thoughts (PoT).

---

## 🚀 CÁCH KHỞI CHẠY HỆ THỐNG (QUICK START)

Trước khi chạy, hãy đảm bảo **Ollama** đang chạy ngầm và đã tải mô hình `qwen2.5-coder:7b`.

### 1. Bật Giao Diện & API Server
Gõ lệnh này vào Terminal để bật hệ thống:
```bash
.venv\Scripts\python -m uvicorn financial_text_to_pandas.api.server:app --reload
```
Sau đó mở trình duyệt truy cập: 👉 **http://localhost:8000/ui/**

### 2. Xử lý Dữ liệu Mới (Chạy Pipeline)
Nếu bạn kéo code về máy mới, hoặc có file báo cáo tài chính mới thả vào thư mục `ViFinQA/financial_statements`, bạn cần phải chạy 3 lệnh dưới đây để AI "học" dữ liệu mới.

*(Mẹo: Bạn có thể vào file `config/run_profile.yaml` chỉnh `run_mode: sample` để chạy nháp cho nhanh trước khi cắm máy chạy `run_mode: full`).*

**Bước 2.1: Bóc tách Báo cáo thành Bảng CSV** (Chạy khá lâu nếu chạy full)
```bash
.venv\Scripts\python src\financial_text_to_pandas\preprocessing\pipeline.py
```

**Bước 2.2: Gộp dữ liệu thành siêu từ điển Tìm kiếm**
```bash
.venv\Scripts\python src\financial_text_to_pandas\retrieval\corpus.py --table-metadata artifacts\preprocessing\table_metadata.csv --output artifacts\preprocessing\indexes\table_corpus.csv
```

**Bước 2.3: Nén vào bộ nhớ BM25 Index**
```bash
.venv\Scripts\python -c "import pandas as pd; from pathlib import Path; from financial_text_to_pandas.retrieval.bm25 import build_bm25_index; df = pd.read_csv('artifacts/preprocessing/indexes/table_corpus.csv', encoding='utf-8-sig'); build_bm25_index(df, Path('artifacts/preprocessing/indexes/bm25_index.pkl')); print('BM25 done!')"
```

> ⚠️ **Lưu ý:** Sau khi chạy xong Bước 2.3, bạn bắt buộc phải **khởi động lại API Server** (ở Bước 1) để nó tải dữ liệu bộ nhớ mới lên!

---

## 🧪 CHẠY KIỂM THỬ (UNIT TESTS)
Để kiểm tra xem source code có bị lỗi hay không (rất hữu ích khi sửa code), hãy chạy lệnh:
```bash
.venv\Scripts\python -m pytest tests/
```
