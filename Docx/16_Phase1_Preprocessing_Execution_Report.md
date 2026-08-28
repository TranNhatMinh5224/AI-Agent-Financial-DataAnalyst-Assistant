# 16 - PHASE 1 PREPROCESSING & CSV TABLE STORE EXECUTION REPORT

Tài liệu này tổng kết quy trình thực thi **Phase 1: Preprocessing & CSV Table Store**, bao gồm cấu trúc dữ liệu đầu vào, quy trình bóc tách HTML Table, xử lý ô gộp (`rowspan`/`colspan`), làm phẳng tiêu đề phân cấp và lưu trữ đầu ra.

---

## 📁 1. Cấu Trúc Dữ Liệu Đầu Vào (ViFinQA Dataset)

Dữ liệu đầu vào nằm tại thư mục `ViFinQA/financial_statements/` gồm **100 mã cổ phiếu** (ticker). Mỗi mã cổ phiếu được phân chia theo năm và loại báo cáo:

```text
ViFinQA/financial_statements/
├── AAA/
│   ├── 2023/
│   │   ├── AAA_financial_statements_2023_consolidated/
│   │   │   └── AAA_financial_statements_2023_consolidated_extracted.txt
│   │   └── AAA_financial_statements_2023_separate/
│   │       └── AAA_financial_statements_2023_separate_extracted.txt
│   └── 2024/...
├── FPT/
├── HPG/...
```

### Đặc điểm định dạng văn bản OCR:
- Phân trang dạng `===== PAGE X =====`.
- Bảng biểu được nhúng trực tiếp dưới dạng thẻ HTML `<table>...</table>`.
- Phần văn bản Thuyết minh BCTC nằm xen kẽ giữa các bảng biểu.

---

## 🔄 2. Quy Trình Xử Lý 5 Bước Của Pipeline (`pipeline.py`)

Khi thực thi lệnh:
```bash
python -m financial_text_to_pandas.preprocessing.pipeline --config config/run_profile.yaml
```

Pipeline tự động thực hiện 5 bước khép kín:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 1: Quét file & Infer Report Metadata                               │
│ - Xác định ticker, năm, loại báo cáo (consolidated/separate)            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 2: Phân trang & Extract HTML Tables                                │
│ - Bóc tách các khối <table>...</table> và gán table_id định danh       │
│ - Trích xuất đoạn văn bản trước/sau bảng (nearby_text) để làm context   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 3: Grid Expansion & Clean Grid Alignment                           │
│ - Mở rộng ô gộp rowspan và colspan (`expand_rowspan_colspan`)           │
│ - Căn chỉnh ma trận lưới 2D (`align_grid`), xóa hàng/cột rỗng           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 4: Flatten Tiêu Đề Phân Cấp & Parse Số Học                        │
│ - Chuẩn hóa tiêu đề phân cấp dạng `Parent > Child`                     │
│ - Parse số liệu tiếng Việt (dấu chấm hàng nghìn, ngoặc đơn âm)          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Bước 5: Ghi Lưu Trữ & Kiểm Tra Re-open CSV                              │
│ - Xuất file `.csv` (UTF-8-SIG), `report_metadata.csv`, `audit.csv`      │
│ - Kiểm tra mở lại CSV bằng Pandas để đảm bảo không lỗi format           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🗃️ 3. Cấu Trúc Lưu Trữ Đầu Ra (`artifacts/preprocessing/`)

Sau khi chạy xong, các tệp kết quả được tạo tại `artifacts/preprocessing/`:

```text
artifacts/preprocessing/
├── tables_csv/                              # Kho lưu trữ bảng sạch dạng CSV
│   └── AAA/
│       └── 2023/
│           └── consolidated/
│               ├── AAA_2023_cons_tbl_0.csv
│               ├── AAA_2023_cons_tbl_1.csv
│               └── ...
├── reports_text_linked/                     # Báo cáo dạng text đã thay <table> bằng [TABLE_REF: id]
│   └── AAA/
│       └── 2023/
│           └── consolidated/
│               └── AAA_financial_statements_2023_consolidated.txt
├── table_metadata.csv                       # Tổng hợp metadata toàn bộ bảng biểu
├── report_metadata.csv                      # Tổng hợp metadata báo cáo
└── audit.csv                                # Nhật ký audit trạng thái bóc tách (success/failed/needs_review)
```

---

## ⚙️ 4. Quản Lý Chế Độ Chạy (`config/run_profile.yaml`)

File cấu hình hỗ trợ 2 chế độ:

1. **`run_mode: sample`** (Chế độ Test/Smoke Test):
   - Chỉ xử lý các ticker trong `sample_tickers` (ví dụ: `AAA`).
   - Giới hạn số báo cáo bằng `sample_limit_reports: 5`.
   - Giúp chạy kiểm tra nhanh chỉ trong vài giây.

2. **`run_mode: full`** (Chế độ Production):
   - Quét toàn bộ 100 ticker và ~2.000 báo cáo tài chính trong `ViFinQA/financial_statements`.
   - Hỗ trợ `resume: true` để tự động bỏ qua các bảng biểu đã xử lý thành công trước đó.

---

## 📋 5. Trạng Thái Đánh Giá & Tuân Thủ

- **Tính tương thích**: Pipeline đã chạy thành công kiểm thử đơn vị (Unit Tests) trên toàn bộ các hàm `table_clean.py`, `number_parser.py`, `metadata.py`.
- **Độ chính xác dữ liệu**: Không bỏ sót bảng biểu, lưu trữ đầy đủ cột nguyên bản `raw_value` và cột đã chuẩn hóa `numeric__*`.
