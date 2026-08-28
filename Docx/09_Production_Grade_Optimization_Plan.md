# 09 - Production-Grade End-to-End Optimization Plan

Tài liệu này bổ sung kế hoạch tối ưu hóa chuẩn sản xuất (Production-Grade End-to-End Architecture) cho hệ thống **AI Financial Data Analyst Assistant** (Text-to-Pandas QA Engine).

---

## 📌 1. Bối cảnh & Mục tiêu Nâng cấp

Dựa trên phân tích đối chiếu hệ thống với mô hình chuẩn End-to-End:
$$\text{Question} \rightarrow \text{Financial Reports} \rightarrow \text{Relevant Tables} \rightarrow \text{Relevant Evidence} \rightarrow \text{Reasoning / Calculation} \rightarrow \text{Answer}$$

Hệ thống đã đạt được nền móng vững chắc về RAG Bảng biểu (Table RAG) và thực thi mã an toàn (Sandboxed Python Engine). Để đạt 100% độ chính xác và tin cậy trong môi trường sản xuất, 5 điểm nâng cấp cốt lõi sau được đưa vào lộ trình tối ưu:

---

## 🚀 2. Chi tiết 5 Điểm Tối Ưu Hóa Cốt Lõi

### 2.1. Self-Correction Loop trong PoT Strategy (Tự chữa lỗi mã Python)
- **Vấn đề**: Khi LLM (`Qwen2.5-Coder:7b`) sinh mã Python có lỗi cú pháp (`SyntaxError`), sai phím (`KeyError`), hoặc quên gán biến `result`, Sandbox ném lỗi làm câu trả lời bị hủy.
- **Giải pháp**: 
  - Đưa vòng lặp Thử lại (Retry loop, tối đa 3 lần) vào `run_pot_strategy()`.
  - Khi Sandbox báo lỗi, bắt lấy Traceback và gửi lại cho LLM với Prompt sửa lỗi (`FIX_POT_PROMPT_TEMPLATE`).

### 2.2. Symbolic Numeric Masking & Schema Linking (`[NUM_X]`)
- **Vấn đề**: Việc truyền chuỗi nhãn tiếng Việt thô dài và phức tạp vào prompt để LLM tự gọi `safe_get_cell` có thể khiến LLM viết sai tên chuỗi.
- **Giải pháp**: 
  - Chuyển đổi các ô dữ liệu đã ground thành các hằng số đại số biểu tượng: `NUM_0 = 1500.0`, `NUM_1 = 1200.0`.
  - Hướng dẫn LLM sinh công thức toán thuần túy: `result = (NUM_0 - NUM_1) / NUM_1 * 100`.
  - Tiêm map `NUM_x` trực tiếp vào globals của `sandbox.py`.

### 2.3. Dual Verification (Kiểm định Kép Bảng - Văn bản)
- **Vấn đề**: Kiểm tra đơn hiện tại mới xác nhận số liệu tồn tại trên bảng, chưa chống được trường hợp Báo cáo tài chính có sự mâu thuẫn giữa Bảng số liệu và Văn bản thuyết minh.
- **Giải pháp**:
  - Triển khai module kiểm định kép trong `verifier.py`.
  - So sánh kết quả tính toán số học với các đoạn văn bản trích xuất từ Thuyết minh BCTC (`linked_text_context`).

### 2.4. Multi-Hop Hybrid RAG (Table + Text Notes / Thuyết minh BCTC)
- **Vấn đề**: Retrieval hiện tại chủ yếu tập trung vào Bảng HTML.
- **Giải pháp**:
  - Phân mảnh đoạn văn Thuyết minh (Unstructured Text Chunks) song song với Table Corpus.
  - Hỗ trợ câu hỏi Multi-hop đòi hỏi truy vết kết hợp giữa Thuyết minh giải trình và Bảng Cân đối / KQKD.

### 2.5. Hierarchical Column Indexing (Xử lý Cột đa tầng)
- **Vấn đề**: Bảng biểu tài chính thường có cột lồng nhau (ví dụ: `Năm 2023 > Quý 4 > Số tiền`).
- **Giải pháp**: Nâng cấp `table_clean.py` để giữ cây tiêu đề cột đầy đủ theo chiều dọc dạng `Cột_Mẹ > Cột_Con`.

---

## 🗓️ 3. Lộ trình Triển khai (Phân chia Pha)

| Pha | Nội dung Công việc | Module ảnh hưởng |
| :--- | :--- | :--- |
| **Pha 1** | Self-Correction Loop & Symbolic Numeric Masking | `reasoning/strategy.py`, `reasoning/llm.py`, `reasoning/prompts.py`, `reasoning/cell_grounding.py`, `reasoning/sandbox.py` |
| **Pha 2** | Dual Verification & Multi-Hop Hybrid RAG | `reasoning/verifier.py`, `retrieval/search.py`, `retrieval/corpus.py`, `preprocessing/pipeline.py` |
| **Pha 3** | Hierarchical Column Headers & Benchmark Evaluation | `preprocessing/table_clean.py`, `evaluation/evaluate.py` |
