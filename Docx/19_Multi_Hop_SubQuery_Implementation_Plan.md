# 19 - MULTI-HOP SUB-QUERY DECOMPOSITION PLAN
**Trạng thái:** Lên kế hoạch (Draft)
**Mục tiêu:** Nâng cấp Planner Agent để tự động nhận diện các câu hỏi phức tạp (chứa nhiều thực thể, nhiều bảng) và bẻ gãy chúng thành các câu hỏi con (Sub-queries), sau đó kích hoạt cơ chế Retrieval song song.

---

## 🏗️ Kiến trúc Đề xuất (Proposed Architecture)

### 1. Nâng cấp cấu trúc Dữ liệu (`types.py`)
- Mở rộng dataclass `Intent` hoặc `QueryHints`:
  - Thêm trường `is_multi_hop: bool`.
  - Thêm trường `sub_queries: List[str]`.

### 2. Nâng cấp Planner Agent (`orchestrator.py` & `llm.py`)
- Thay vì chỉ trích xuất từ khóa bằng Regex (`query_hints.py`), hệ thống sẽ truyền thẳng câu hỏi của người dùng vào **Qwen2.5-Coder (Planner Agent)**.
- **Prompt ép kiểu (System Prompt):**
  Yêu cầu LLM trả về chuẩn JSON. 
  *Ví dụ:* Nếu câu hỏi là "Tổng của Hàng tồn kho và Lợi nhuận sau thuế năm 2022", LLM phải trả về:
  ```json
  {
      "is_multi_hop": true,
      "sub_queries": [
          "Hàng tồn kho năm 2022",
          "Lợi nhuận sau thuế năm 2022"
      ]
  }
  ```

### 3. Nâng cấp Retriever Engine (`multi_hop.py` & `retriever/`)
- Nếu `is_multi_hop = True`, Retriever sẽ không tìm kiếm 1 lần nữa.
- Thay vào đó, nó sẽ khởi tạo 1 vòng lặp (hoặc chạy đa luồng `asyncio.gather`) để gọi hàm `search()` cho từng câu hỏi trong `sub_queries`.
- Thu thập danh sách Bảng ứng viên (Candidates) từ mọi nguồn, sau đó **Gộp (Merge) & Xóa trùng lặp (Deduplicate)**.
- Đẩy danh sách (Bảng A + Bảng B) qua cho **Cross-Encoder Reranker** chấm điểm lại lần cuối trước khi giao cho Programmer Agent.

### 4. Nâng cấp Cell Grounding (`cell_grounding.py`)
- Hệ thống Programmer Agent khi nhận được nhiều bảng biểu sẽ cần dò tìm các "Metrics" độc lập trên từng bảng. Hàm `ground_cells` vốn dĩ đã là một vòng lặp `for df in dfs.values()`, nên nó hoàn toàn tương thích và chỉ cần tinh chỉnh nhỏ để lấy đúng số liệu từ đúng bảng tương ứng.

---

## 🚀 Các Bước Thực Thi (Actionable Steps)
- [ ] **Step 1:** Viết lại System Prompt cho Planner Agent (dùng SGLang JSON Output).
- [ ] **Step 2:** Thêm logic phân nhánh trong `orchestrator.py` `def plan()`.
- [ ] **Step 3:** Mở khóa module `multi_hop.py` (Xóa bỏ code stub cũ, đưa logic Parallel Retrieval vào).
- [ ] **Step 4:** Cập nhật Unit Test với câu hỏi đa điều kiện.
