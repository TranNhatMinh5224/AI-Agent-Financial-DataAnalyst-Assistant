# Kế Hoạch Tối Ưu Hóa Hệ Thống AI Financial Data Analyst Assistant

Tài liệu này phác thảo các chiến lược và phương pháp kỹ thuật nhằm nâng cấp và tối ưu hóa dự án, tập trung vào việc sử dụng một LLM cỡ trung (khoảng 14B parameters) một cách hiệu quả nhất, đảm bảo tính chính xác, ổn định và bảo mật cho hệ thống phân tích dữ liệu tài chính.

---

## 1. Giải quyết Nút Thắt Tiền Xử Lý (Preprocessing Bottlenecks)

Đặc thù bộ dữ liệu ViFinQA là các báo cáo tài chính đã được OCR sẵn thành văn bản phẳng (flat text) với thẻ HTML `<table>` nội suy, đi kèm nhiều rác OCR, header/footer lặp lại và cấu trúc bảng đứt gãy. Việc sử dụng các công cụ xử lý PDF truyền thống (như pdfplumber) không còn phù hợp, thay vào đó cần một Pipeline làm sạch dữ liệu văn bản chuyên biệt.

**Phương pháp tối ưu (Data Cleaning Pipeline 5 Bước):**
*   **Bước 1 - Giảm nhiễu (Noise Reduction):** Dùng Regex lọc bỏ rác OCR, các cụm từ hệ thống (`Signature Not Verified`) và xóa header/footer (tên công ty, số trang `===== PAGE X =====`) lặp lại làm đứt gãy mạch văn bản.
*   **Bước 2 - Tái tạo bảng (Table Reconstruction):** Parse các thẻ HTML `<table>` bằng thư viện `BeautifulSoup`, tự động nối các bảng bị đứt gãy do ngắt trang, xử lý gộp ô (colspan, rowspan) và chuyển đổi bảng về định dạng Markdown chuẩn.
*   **Bước 3 - Chuẩn hóa số liệu (Data Normalization):** Đưa toàn bộ định dạng số tiếng Việt (dấu chấm/phẩy lộn xộn do OCR nhầm) về chuẩn float quốc tế `1234567.89` thống nhất, đồng thời trích xuất và lưu trữ Entity Đơn vị tính (VND, nghìn đồng) vào Metadata.
*   **Bước 4 - Phân mảnh cấu trúc (Document Structuring):** Sử dụng Regex/Heuristics dựa trên mục lục chuẩn để tách file `.txt` lớn thành các Chunk cấu trúc logic (Bảng Cân đối, KQKD, LCTT, Thuyết minh) để phục vụ Retrieval chính xác hơn.
*   **Bước 5 - LLM-Assisted Extraction (Tuỳ chọn):** Đối với các bảng quá nát không thể parse nguyên vẹn bằng HTML/BeautifulSoup, sử dụng một LLM nhỏ lẻ chuyên biệt (như Qwen-2.5-7B) để chuẩn hóa định dạng (Text-to-Markdown) trước khi đưa vào kho Vector DB.

## 2. Tối Ưu Hóa Retrieval (Vượt qua giới hạn BM25)

Việc phụ thuộc hoàn toàn vào BM25 dễ dẫn đến trượt thông tin do tiếng Việt tài chính có nhiều từ đồng nghĩa. Hệ thống đã có khung mã nguồn cho Dense Retrieval nhưng chưa tối ưu.

**Phương pháp tối ưu:**
*   **Kích hoạt Hybrid Search:** Kết hợp BM25 (để bắt từ khóa cứng như "VNM", "2023") và Dense Search (Vector Embeddings) để bắt ngữ nghĩa (Semantic).
*   **Sử dụng Embedding Model tiếng Việt chuyên biệt:** Sử dụng các mô hình nhỏ gọn như `keepitreal/vietnamese-sbert` hoặc `intfloat/multilingual-e5-small` để mã hóa các dòng `row_label_full` thành vector.
*   **Reranking:** Sử dụng Cross-Encoder (ví dụ: `BAAI/bge-reranker-m3`) để chấm điểm lại top 10 bảng kết quả cuối cùng trước khi đưa vào luồng suy luận.

## 3. Tăng Cường Bảo Mật & Ổn Định Cho Sandbox (PoT)

Sandbox hiện tại dùng `ast.NodeVisitor` để chặn hàm nguy hiểm, nhưng vẫn có nguy cơ bị lặp vô hạn (Infinite Loop) hoặc tràn bộ nhớ (OOM) do LLM sinh ra vòng lặp `while True` hoặc tạo DataFrame khổng lồ.

**Phương pháp tối ưu:**
*   **Giới hạn thời gian (Timeout):** Đặt mã thực thi (exec) vào một Process riêng biệt (sử dụng `multiprocessing`). Đặt timeout cứng (ví dụ: 5 giây). Nếu quá thời gian, tiến trình sẽ bị huỷ (kill) để bảo vệ server.
*   **Cô lập hoàn toàn (Isolation):** Nếu triển khai thực tế, hãy xem xét dùng **Pyodide** (chạy Python trong môi trường WebAssembly cô lập) hoặc các Docker Container chỉ dùng một lần (ephemeral containers) để xử lý code.

## 4. Tự Động Hóa Pipeline Nạp Dữ Liệu (Ingestion Pipeline)

Người dùng không nên gõ các lệnh Terminal thủ công mỗi khi có báo cáo tài chính mới. Việc nạp dữ liệu cần được tự động hóa hoàn toàn.

**Phương pháp tối ưu:**
*   **Tích hợp Script Tiền xử lý:** Tích hợp trực tiếp module `preprocess_vifinqa.py` (chứa 5 bước làm sạch rác OCR, chuẩn hóa dấu thập phân và nối bảng HTML) vào luồng nạp dữ liệu.
*   **Background Watcher:** Dùng thư viện `watchdog` của Python để giám sát thư mục `financial_statements`. Khi có file `.txt` mới được tải về, script sẽ tự động kích hoạt luồng xử lý (chạy qua Pipeline làm sạch, gộp metadata, sinh index).
*   **Real-time Vector DB:** Thay vì dùng file `.pkl` tĩnh, hãy dùng **LanceDB** hoặc **ChromaDB** chạy local. Khi có file mới, hệ thống tự động `.add()` các chunk và bảng Markdown vào cơ sở dữ liệu mà không cần khởi động lại toàn bộ API Server.

## 5. Nâng Cấp Cell Grounding

Thuật toán `rapidfuzz` với ngưỡng `partial_ratio > 80` hiện tại là quá cứng nhắc để khớp các chỉ tiêu tài chính.

**Phương pháp tối ưu:**
*   **Từ điển đồng nghĩa (Synonym Dictionary - Rule-based):** Xây dựng một file JSON chứa chuẩn mực kế toán Việt Nam (Ví dụ: `{"doanh thu thuần": ["doanh thu bán hàng", "doanh thu thuần về bán hàng"]}`).
*   **Embedding-based Matching:** Trích xuất cột đầu tiên của các bảng Markdown (sau khi parse từ HTML) làm danh sách các chỉ tiêu (Metrics). Nếu không có trong từ điển, sử dụng Cosine Similarity từ Vector Embeddings của câu hỏi và danh sách chỉ tiêu này để tìm ra dòng phù hợp nhất (ngưỡng tin cậy > 85%), tuyệt đối không giao phó việc "chọn dòng" cho LLM sinh từ tự do để tránh ảo giác.

---

## 6. Phân mảnh Prompt (State Machine / Pipeline Pattern)

Thay vì gộp mọi thứ vào 1 prompt khổng lồ, hãy chia luồng xử lý (Phase 3: Reasoning) thành một chuỗi các lệnh gọi LLM (LLM Calls) riêng biệt. Tại mỗi bước, "tiêm" (inject) một System Prompt ép model đóng đúng một vai trò duy nhất:

*   **Bước 1: Intent Extraction (Vai trò: NLP Parser)**
    *   *Prompt:* "Bạn là bộ trích xuất dữ liệu. Chuyển câu hỏi 'Biên lợi nhuận gộp năm 2023?' thành JSON: `{"metric": "biên lợi nhuận gộp", "year": 2023, "operation": "ratio"}`. Chỉ in ra JSON."
*   **Bước 2: Coder (Vai trò: Python Developer)**
    *   *Prompt:* "Bạn là kỹ sư dữ liệu. Cho schema bảng df: [A, B, C]. Viết code Pandas tính toán biên lợi nhuận gộp dựa trên JSON ở trên. Bắt buộc để code trong tag \`\`\`python."
*   **Bước 3: Tổng hợp (Vai trò: Chuyên viên Tài chính)**
    *   *Prompt:* "Dữ liệu Python trả về kết quả là 15.5%. Hãy trả lời user một cách lịch sự kèm giải thích ngắn gọn."

## 7. Ép cấu trúc đầu ra (Structured Outputs / JSON Enforcement)

Với 1 model đa năng 14B, nó rất thích "nói nhiều". Để code Python (như `sandbox.py` hay `intent.py`) của bạn không bị lỗi parse:

*   Hãy tích hợp thư viện **`instructor`** hoặc dùng **Pydantic** kết hợp với tham số `format="json"` của Ollama.
*   Điều này ép model sinh ra đúng các trường dữ liệu mà `dataclass` của bạn (ví dụ `types.Intent`) yêu cầu, giảm tỷ lệ lỗi parse từ 20% xuống gần 0%.

## 8. "Ăn kiêng" ngữ cảnh (Strict Context Pruning)

Model 14B xử lý context càng dài thì càng chậm và càng dễ "ảo giác" (Lost in the middle).

*   Tuyệt đối **KHÔNG** nhét toàn bộ văn bản báo cáo hoặc bảng Markdown thô dài hàng trăm dòng vào prompt để model tự mò mẫm.
*   Chỉ nhét **Schema của Bảng** (Tên các cột) và **Các dòng dữ liệu liên quan** (đã được lọc ra bởi thuật toán Embedding/BM25 ở Bước Grounding) vào prompt.
*   *Ví dụ:* Thay vì đưa cả Bảng Cân đối kế toán dài 5 trang, chỉ đưa vào prompt: `"Bảng KQKD 2023 - Cột: [Năm 2023, Năm 2022]. Dữ liệu trích xuất: | Doanh thu thuần | 15000.5 | 12000.2 |"`. Model 14B sẽ xử lý thông tin tinh gọn này cực kỳ chính xác.

## 9. Triển khai Semantic Caching (Bộ đệm ngữ nghĩa)

Chạy model 14B tốn tài nguyên và thời gian. Rất nhiều câu hỏi tài chính lặp lại ý nghĩa.

*   **Cách làm:** Dùng Embedding Model để lưu lại câu hỏi của user và kết quả trả lời vào Database (như Redis hoặc SQLite).
*   Nếu user 1 hỏi: *"Lợi nhuận sau thuế của VNM 2023 là bao nhiêu?"* (Model 14B mất 5s để chạy).
*   Nếu user 2 hỏi: *"VNM năm 2023 lãi ròng bao nhiêu?"*. Embedding phát hiện câu này giống 95% câu trước ➡️ Hệ thống trả luôn kết quả đã lưu trong Cache (mất 0.1s) mà **KHÔNG CẦN GỌI MODEL 14B NỮA**.

## 10. Cấp quyền tự sửa sai (Self-Correction Loop) ở Sandbox

Khi bạn chỉ có 1 model, nếu nó viết code Pandas sai (ví dụ sai tên cột, chia cho 0), hãy tận dụng chính nó để sửa lỗi thay vì báo "Hệ thống lỗi" cho người dùng:

*   Khi `sandbox.py` ném ra exception (ví dụ: `KeyError: 'Doanh_thu'`).
*   Bắt lấy exception đó trong code Python, tạo tự động một prompt mới: *"Code bạn vừa viết bị lỗi: KeyError: 'Doanh_thu'. Các cột hiện có là ['Doanh thu thuần', 'Giá vốn']. Hãy viết lại mã code."*
*   Cho phép vòng lặp này chạy tối đa 2 lần. Model 14B cực kỳ xuất sắc trong việc sửa lỗi chính tả code do chính nó tạo ra.
