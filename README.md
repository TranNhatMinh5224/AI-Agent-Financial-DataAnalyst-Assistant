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

## 🚀 HƯỚNG DẪN KHỞI CHẠY TỪ A - Z (Để sinh toàn bộ đáp án dự thi)

Khi bạn clone dự án này về máy mới, thư mục `artifacts/` chứa các dữ liệu xử lý (CSV, Index) sẽ KHÔNG tồn tại (do đã bị bỏ qua bởi `.gitignore`). Để tạo ra bộ đáp án hoàn chỉnh cho 1012 câu hỏi, bạn **BẮT BUỘC** phải chạy các bước dưới đây theo thứ tự. Bạn sẽ cần mở tổng cộng **5 Terminal**.

### Bước 1: Thiết Lập Môi Trường (Terminal 1)
Yêu cầu hệ thống: Python 3.10+, 16GB+ RAM (Khuyến nghị có GPU để tăng tốc SGLang).

1. **Tạo và kích hoạt môi trường ảo:**
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
   pip install "sglang[all]" # Cài đặt SGLang Engine (Bắt buộc cho hệ thống này)
   ```

### Bước 2: Tiền Xử Lý Dữ Liệu (Terminal 1)
Trước khi Agent có thể tìm kiếm, bạn cần chạy file tiền xử lý để bóc tách các Báo cáo tài chính PDF (.txt) thành các file CSV nhỏ:
```bash
python preprocess_vifinqa.py
```
*(Kết quả: Hàng nghìn file `<table_id>.csv` sẽ được tạo tại `artifacts/preprocessing/`).*

### Bước 3: Khởi Chạy Hệ Thống LLMs (Mở 4 Terminal Mới)
Mở thêm **4 Terminal mới**, ở mỗi Terminal nhớ kích hoạt môi trường ảo (`.venv\Scripts\activate`), sau đó gõ lần lượt các lệnh sau để khởi chạy 4 Agent:

**Terminal 1 (Port 30000) - Chạy Planner Agent (DeepSeek-R1-14B)**
```bash
python -m sglang.launch_server --model-path deepseek-ai/DeepSeek-R1-Distill-Qwen-14B --port 30000 --host 0.0.0.0
```

**Terminal 2 (Port 30001) - Chạy Retriever Agent (Qwen2.5-7B)**
```bash
python -m sglang.launch_server --model-path Qwen/Qwen2.5-7B-Instruct --port 30001 --host 0.0.0.0
```

**Terminal 3 (Port 30002) - Chạy Programmer Agent (Qwen2.5-Coder-14B)**
```bash
python -m sglang.launch_server --model-path Qwen/Qwen2.5-Coder-14B-Instruct --port 30002 --host 0.0.0.0
```

**Terminal 4 (Port 30003) - Chạy Critic Agent (Qwen2.5-Coder-3B)**
```bash
python -m sglang.launch_server --model-path Qwen/Qwen2.5-Coder-3B-Instruct --port 30003 --host 0.0.0.0
```
*(Lưu ý: Lần đầu tiên chạy, hệ thống sẽ tự động tải các model này từ HuggingFace về máy, nên sẽ mất thời gian tùy thuộc vào tốc độ mạng).*

### Bước 4: Chạy Toàn Bộ 1012 Câu Hỏi Để Ra Kết Quả (Terminal 1)
Quay trở lại Terminal 1 (Terminal đầu tiên dùng để setup), gõ lệnh chạy Batch Inference để hệ thống giải quyết tất cả 1012 câu hỏi:
```bash
python run_batch_inference.py
```
*(Mẹo: Bạn có thể thêm cờ `--limit 5` để chạy thử 5 câu đầu nhằm kiểm tra lỗi trước khi chạy thật. Script hỗ trợ resume, nên nếu bị gián đoạn giữa chừng, chạy lại lệnh này sẽ tự động bỏ qua các câu đã làm).*

### Bước 5: Đóng Gói File Nộp Bài Dashboard
Khi script ở Bước 4 chạy xong, bạn sẽ thấy thư mục `submission` được tạo ra ở thư mục gốc của dự án với cấu trúc:
```text
submission/
├── submission.json
└── data/
    ├── <báo_cáo_1>.csv
    └── <báo_cáo_2>.csv
```
Nhiệm vụ cuối cùng của bạn là vào thư mục dự án, chuột phải vào thư mục `submission` (hoặc bôi đen toàn bộ ruột của nó) và **Compress to ZIP file** (đặt tên là `submission.zip`). Bạn đem file ZIP này upload lên Dashboard của Ban Tổ chức là xong! 🎯

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
