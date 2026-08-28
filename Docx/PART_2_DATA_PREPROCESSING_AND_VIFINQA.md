# PART 2: DATA PREPROCESSING, TABLE STORE & VIFINQA DATASET ANALYSIS

Tài liệu này hợp nhất đầy đủ và chi tiết các tệp thiết kế tiền xử lý dữ liệu và phân tích dataset: **04_Phase1_Data_Preparation**, **16_Phase1_Preprocessing_Execution_Report**, và **21_ViFinQA_Dataset_Comprehensive_Analysis**.

---

# SECTION 1: PHASE 1 DATA PREPARATION (04)

## 1. Phase Goal
Convert ViFinQA OCR TXT reports into clean CSV tables, linked text files, metadata files, and preprocessing audit logs.

Phase 1 creates the data foundation for retrieval, cell grounding, and Pandas reasoning.

## 2. Scope
Implement only:
- OCR TXT page splitting;
- report metadata inference;
- HTML table extraction;
- `rowspan` / `colspan` expansion;
- row alignment;
- whitespace normalization;
- header detection and flattening;
- financial group context propagation;
- Vietnamese number normalization;
- CSV table output;
- `TABLE_REF` linked text output;
- table metadata;
- report metadata;
- preprocessing audit;
- sample/full run gates;
- unit tests.

Phase 1 does not implement LLM calls, retrieval, embedding, reranking, reasoning, cell grounding, database, or Text-to-SQL.

## 3. Inputs & Outputs
Inputs:
```text
ViFinQA/financial_statements/{ticker}/{year}/{document_name}/*.txt
ViFinQA/code_stock.csv
ViFinQA/questions.jsonl
```

Outputs:
```text
<output_root>/tables_csv/{ticker}/{year}/{report_type}/{table_id}.csv
<output_root>/reports_text_linked/{ticker}/{year}/{report_type}/{report_id}.txt
<output_root>/table_metadata.csv
<output_root>/report_metadata.csv
<output_root>/preprocessing_audit.csv
```

## 4. Single Run Profile (`config/run_profile.yaml`)
`config/run_profile.yaml` is the single source of truth for execution scope:
```yaml
run_mode: sample # 'sample' for smoke testing, 'full' for complete corpus
input_root: ViFinQA/financial_statements
output_root: artifacts/preprocessing
sample_tickers:
  - AAA
sample_limit_reports: 1
full_run_confirmed: false
resume: true
```

## 5. Vietnamese Number Parser Rules
- Thousands separator: `15.230.000 -> 15230000`
- Decimal comma: `12,5 -> 12.5`
- Percentage: `12,5% -> 0.125, unit_hint="%"`)
- Parentheses negative: `(500.000) -> -500000`
- Hyphen / Empty: `"-" -> null`

## 6. Progressive Run Gates
- **Gate P1.0**: Unit tests only (0 reports).
- **Gate P1.1**: One-report smoke run (`sample_tickers: [AAA]`, `limit: 1`).
- **Gate P1.2**: One-ticker review run (`sample_tickers: [AAA]`, `limit: null`).
- **Gate P1.3**: Small portfolio review (`sample_tickers: [AAA, VCB, HPG, FPT, HSG]`).
- **Gate P1.4**: Full corpus execution (`run_mode: full`, `full_run_confirmed: true`).

---

# SECTION 2: PREPROCESSING EXECUTION REPORT (16)

## 📁 1. Cấu Trúc Dữ Liệu Đầu Vào (ViFinQA Dataset)
Dữ liệu nằm tại `ViFinQA/financial_statements/` gồm **100 mã cổ phiếu**.
Đặc điểm OCR:
- Phân trang dạng `===== PAGE X =====`.
- Bảng biểu dạng HTML `<table>...</table>`.
- Thuyết minh BCTC nằm xen kẽ giữa các bảng.

## 🔄 2. Quy Trình 5 Bước Của Pipeline (`pipeline.py`)
1. **Bước 1**: Quét file & Infer Report Metadata (`ticker`, `year`, `report_type`).
2. **Bước 2**: Phân trang & Extract HTML Tables.
3. **Bước 3**: Grid Expansion & Clean Grid Alignment (`rowspan`, `colspan`).
4. **Bước 4**: Flatten Tiêu Đề Phân Cấp & Parse Số Học (`Parent > Child`, `numeric__*`).
5. **Bước 5**: Ghi Lưu Trữ & Kiểm Tra Re-open CSV với Pandas.

---

# SECTION 3: VIFINQA DATASET COMPREHENSIVE ANALYSIS (21)

## 📊 1. Tổng Quan Bộ Dữ Liệu
| Thành phần | Quy mô | Mô tả |
| :--- | :--- | :--- |
| **Mã chứng khoán (Tickers)** | **100 Doanh nghiệp** | Top công ty niêm yết HOSE, HNX, UPCoM trong `code_stock.csv`. |
| **Báo cáo tài chính** | **100 Thư mục** | File `.txt` BCTC kiểm toán giai đoạn 2015 – 2025. |
| **Tập câu hỏi** | **1,013 Câu hỏi** | Tập câu hỏi `questions/questions.jsonl` đánh giá chuẩn. |

## 🎯 2. Phân Tích Tập Câu Hỏi (`questions.jsonl`)
- **Đơn vị đo lường**: Triệu đồng / Tỷ đồng (>80%), Nghìn tỷ, Phần trăm (%).
- **Phân loại độ phức tạp**:
  1. **Single Table Lookup (~65%)**: Truy xuất 1 bảng đơn.
  2. **Multi-Hop / Multi-Year (~25%)**: Truy xuất đa bảng/đa thời gian.
  3. **Financial Ratio Calculation (~10%)**: Tính toán tỷ lệ tài chính (% nợ, ROE).

## ⚠️ 3. Thách Thức Dữ Liệu & Giải Pháp Tương Ứng
- **Nhiễu OCR**: Dùng `cell_grounding.py` với thuật toán Fuzzy Matching (`token_sort_ratio`).
- **Từ viết tắt ngành**: Dùng từ điển tài chính `config/financial_dictionary.json` và module `dictionary.py`.
- **Ảo giác số liệu**: Áp dụng Program-of-Thoughts (PoT) + De-lexicalization + AST Sandbox Execution.
