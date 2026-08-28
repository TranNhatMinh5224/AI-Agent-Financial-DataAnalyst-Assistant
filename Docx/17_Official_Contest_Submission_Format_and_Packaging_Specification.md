# 17 - OFFICIAL CONTEST SUBMISSION FORMAT & PACKAGING SPECIFICATION

Tài liệu này quy định chi tiết **Đặc tả Định dạng Nộp bài (Submission Schema)** và **Quy trình Đóng gói Tệp ZIP (`submission.zip`)** nộp lên Hệ thống Dashboard Leaderboard chính thức của cuộc thi (`http://leaderboard.aiguru.com.vn/`).

---

## 📦 1. Cấu Trúc Đóng Gói Tệp `submission.zip`

Bài nộp được đóng gói dưới dạng **1 file ZIP duy nhất** có cấu trúc thư mục ở cấp ngoài cùng (Root level):

```text
submission.zip
├── submission.json              <-- File dự đoán duy nhất (JSON Array)
└── data/                        <-- Thư mục chứa toàn bộ các file CSV được tham chiếu
    ├── table_1.csv
    ├── table_2.csv
    └── ...
```

### ⚠️ Các Lưu Ý Quan Trọng (Strict Constraints):
1. **Không có thư mục cha lồng ngoài**: `submission.json` và thư mục `data/` phải nằm **trực tiếp ở cấp ngoài cùng** của file ZIP. Tuyệt đối không được đặt trong thư mục cha (ví dụ: `submission/submission.json` là KHÔNG HỢP LỆ).
2. **Một file JSON duy nhất**: ZIP chỉ chứa đúng 1 file `.json` tên là `submission.json`.
3. **Đường dẫn tương đối `data/`**: Mọi trường `csv_path` trong tệp JSON phải là đường dẫn tương đối bắt đầu bằng `data/` (ví dụ: `data/AAA_financial_statements_2015_consolidated_table_1.csv`).
4. **Không bỏ sót câu hỏi**: Mọi `id` câu hỏi trong bộ kiểm thử `questions.jsonl` phải xuất hiện đầy đủ trong tệp `submission.json`.

---

## 📜 2. Cấu Trúc Trường Dữ Liệu `submission.json`

Tệp `submission.json` là một **JSON Array** chứa các object dự đoán tương ứng với từng câu hỏi.

```json
[
  {
    "id": 1,
    "question": "Doanh thu thuần của Công ty CP Sữa Việt Nam (VNM) năm 2023 là bao nhiêu?",
    "answer": 63075000000.0,
    "relevant_docs": [
      "AAA_financial_statements_2015_consolidated"
    ],
    "relevant_tables": [
      "AAA_financial_statements_2015_consolidated|350"
    ],
    "evidence": [
      {
        "variable": "df1",
        "csv_path": "data/AAA_financial_statements_2015_consolidated_table_1.csv"
      }
    ],
    "pandas_query": "df1[(df1.company=='VNM') & (df1.year==2023)]['net_revenue'].values[0]"
  }
]
```

### 🔍 Giải Thích Chi Tiết Các Trường:

| Trường | Kiểu Dữ Liệu | Mô Tả & Quy Định |
| :--- | :--- | :--- |
| **`id`** | `integer` | Mã định danh câu hỏi trong tệp `questions.jsonl`. |
| **`question`** | `string` | Nội dung câu hỏi kiểm thử tài chính. |
| **`answer`** | `float` | Kết quả số liệu dự đoán (kiểu số thực). |
| **`relevant_docs`** | `list[str]` | Danh sách mã định danh của các báo cáo có liên quan. Mã báo cáo = Tên tệp báo cáo OCR **bỏ phần mở rộng `.txt`** (Ví dụ: `AAA_financial_statements_2015_consolidated`). |
| **`relevant_tables`** | `list[str]` | Danh sách vị trí bảng biểu liên quan có định dạng `<id_báo_cáo>\|<vị trí dòng bắt đầu trong file txt>` (Ví dụ: `AAA_financial_statements_2015_consolidated\|350`). |
| **`evidence`** | `list[dict]` | Danh sách các bảng dữ liệu CSV sử dụng cho `pandas_query`. Mỗi item gồm:<br>• `variable`: Tên biến DataFrame trong Python (`"df1"`, `"df2"`,...).<br>• `csv_path`: Đường dẫn tương đối dạng `data/<filename>.csv`. |
| **`pandas_query`** | `string` | Câu lệnh Pandas thực thi lại được trên biến `variable` để ra kết quả `answer`. |

---

## 🛠️ 3. Tích Hợp Hệ Thống (`submission.py`)

Hệ thống đã bổ sung module **`financial_text_to_pandas.submission`** chịu trách nhiệm:

1. **`create_submission_item(...)`**: Tạo đối tượng `SubmissionItem` hợp chuẩn.
2. **`export_submission_zip(...)`**: Đóng gói `submission.json` và copy các file CSV liên quan vào đúng vị trí `data/` trong ZIP.
3. **`validate_submission_zip(...)`**: Tự động kiểm tra tính hợp lệ của file ZIP trước khi tải lên Dashboard (kiểm tra root directory, schema JSON, tính tồn tại của các file CSV).

---

## 🧪 4. Bộ Kiểm Thử Đóng Gói (`test_submission.py`)

Bộ kiểm thử đơn vị đã được cập nhật tại `tests/test_submission.py` để đảm bảo:
- Khởi tạo đúng định dạng `relevant_docs` và `relevant_tables`.
- Xuất file `.zip` không chứa thư mục cha lồng ngoài.
- Phát hiện và báo lỗi ngay lập tức nếu file ZIP bị sai cấu trúc hoặc thiếu file CSV.
