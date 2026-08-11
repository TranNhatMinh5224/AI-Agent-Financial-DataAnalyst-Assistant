# Chi Tiết Triển Khai Giai Đoạn 3: Tích hợp Multi-Agent & RAG (Multi-Agent Integration)

Giai đoạn 3 là lúc chúng ta "thổi hồn" vào hệ thống bằng cách ráp nối các Module tĩnh (đã xây dựng ở GĐ 1 & 2) thành một quy trình làm việc động (Workflow) thông qua framework **LangGraph**. Tại đây, các AI Agent (với sức mạnh của LLM < 15B) sẽ phối hợp với nhau như một phòng ban phân tích tài chính thu nhỏ.

## 1. Mục tiêu Giai đoạn 3
- Xây dựng luồng công việc (State Graph) quản lý vòng đời của một truy vấn bằng LangGraph.
- Cấu hình 4 Agent chuyên trách: Router, Data Analyst, Researcher, Synthesizer.
- Tích hợp công cụ (Function Calling) toán học lập trình sẵn để bù đắp điểm yếu của LLM nhỏ.
- Tích hợp Vector DB để xử lý các câu hỏi định tính (nguyên nhân, giải trình).

---

## 2. Chi tiết các Bước Thực thi

### Bước 3.1: Xây dựng Bộ Công cụ (Toolkits) cho LLM
Vì chúng ta bị giới hạn ở các mô hình mã nguồn mở < 15B (như Llama-3.1-8B, Qwen2.5-14B), khả năng tự sinh code Pandas phức tạp là không an toàn. Chúng ta phải chuẩn bị sẵn "đồ nghề" cho chúng.

- **Hành động:** Lập trình sẵn các hàm Python thuần túy. LLM chỉ cần gọi hàm (Function Calling).
  - `query_sql(metric_id, company_id, year)`: Gửi SQL template vào DuckDB để lấy số liệu thô.
  - `calculate_growth(value_current, value_previous)`: Tính tốc độ tăng trưởng (%).
  - `calculate_median(list_of_values)`: Tính trung vị.
  - `calculate_proportion(part, total)`: Tính tỷ trọng (%).
  - *Lưu ý:* Bằng cách này, mọi phép tính đều do máy tính thực hiện, đảm bảo độ chính xác toán học 100%.

### Bước 3.2: Lập trình Đội ngũ AI Agent (LangGraph Nodes)

**1. Router Agent (Người Điều Phối)**
- **Đầu vào:** Câu hỏi của người dùng.
- **Nhiệm vụ:** Phân tích xem câu hỏi này thuộc loại gì.
- **Quyết định (Conditional Edges):**
  - Nếu là câu hỏi lấy số liệu (Quantitative): Chuyển cho *Data Analyst Agent*.
  - Nếu là câu hỏi tìm nguyên nhân/diễn giải (Qualitative): Chuyển cho *Researcher Agent*.
  - Nếu câu hỏi tối nghĩa/thiếu thông tin: Trả lại yêu cầu *Clarification* cho người dùng.

**2. Data Analyst Agent (Chuyên Viên Số Liệu)**
- **Nhiệm vụ:** 
  - Kích hoạt lõi truy xuất (Giai đoạn 2) để lấy Intent và Metric ID.
  - Sử dụng các Toolkits (đã tạo ở Bước 3.1) để gọi dữ liệu từ DuckDB và tính toán.
- **Đầu ra:** Bảng số liệu chính xác tuyệt đối kèm theo công thức đã dùng.

**3. Researcher Agent (Chuyên Viên Đọc Hiểu)**
- **Nhiệm vụ:** 
  - Chuyển câu hỏi thành Vector (Embedding).
  - Truy vấn vào **Vector DB (Milvus/Qdrant)** bằng kỹ thuật Hybrid Search (Vector + Từ khóa).
  - Sử dụng Metadata Filtering (chỉ tìm trong báo cáo của Công ty X, Năm Y) để không bị lẫn lộn dữ liệu của công ty khác.
- **Đầu ra:** Trích xuất các đoạn văn bản (Text chunks) liên quan nhất từ Thuyết minh BCTC.

**4. Synthesizer & Validator Agent (Người Tổng Hợp & Kiểm Duyệt)**
- **Nhiệm vụ:** Nhận số liệu từ Data Analyst và văn bản từ Researcher. 
- Dùng LLM để viết lại thành một câu trả lời hoàn chỉnh bằng ngôn ngữ tự nhiên.
- **Bắt buộc:** Phải kèm theo nguồn trích dẫn (Ví dụ: *"Nguồn: Báo cáo tài chính hợp nhất kiểm toán 2023, CTCP FPT, Thuyết minh số V.2"*).

### Bước 3.3: Lắp ráp Luồng Đồ Thị (State Graph)
- **Hành động:** Sử dụng cấu trúc `StateGraph` của LangGraph để định nghĩa trạng thái của hệ thống.
  - Trạng thái (State) sẽ lưu trữ: Câu hỏi gốc, JSON Intent, Kết quả SQL, Văn bản truy xuất, và Câu trả lời nháp.
  - Cài đặt cơ chế Vòng lặp (Human-in-the-loop): Nếu Router Agent hoặc Metric Resolution báo lỗi "Tự tin thấp", LangGraph sẽ tạm dừng (Interrupt), trả về thông báo hỏi người dùng, và chờ người dùng phản hồi để tiếp tục luồng chạy.

---

## 3. Đầu ra mong đợi (Deliverables) của Giai đoạn 3
Hoàn thành Giai đoạn 3, hệ thống cơ bản đã có thể chạy thực tế qua giao diện Terminal (Command Line):
1. **LangGraph Workflow:** Hoàn thiện và chạy mượt mà không bị kẹt luồng (Deadlock).
2. **Cơ sở dữ liệu hoàn chỉnh:** SQL DB cho số liệu và Vector DB cho văn bản.
3. **Log theo dõi (Tracing Trace):** Ghi nhận được toàn bộ hành vi của từng Agent (Nó gọi hàm gì? Nó truy xuất ra sao?) để phục vụ việc debug.

*Kết thúc Giai đoạn 3, hệ thống đã thông minh và chính xác. Giai đoạn 4 cuối cùng sẽ là khoác lên nó một giao diện (UI) và đưa vào môi trường production.*
