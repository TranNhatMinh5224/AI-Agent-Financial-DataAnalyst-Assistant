# PART 4: MULTI-AGENT ARCHITECTURE, PRODUCTION DEPLOYMENT & CONTEST COMPLIANCE

Tài liệu này hợp nhất đầy đủ và chi tiết các tệp thuộc quy trình triển khai và tuân thủ thi đấu: **07_Phase4_Deployment_and_Optimization**, **09_Production_Grade_Optimization_Plan**, **14_Multi_Agent_Architecture_and_Production_Deployment**, **15_Contest_Compliance_and_Model_Manifest**, **17_Official_Contest_Submission_Format_and_Packaging_Specification**, và **18_QuickStart_Runbook_A_to_Z**.

---

# SECTION 1: MULTI-AGENT ARCHITECTURE & SERVING (14)

## 1. Multi-Agent Collaboration (CLER Framework)
- **Planner Agent** (`deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`): Phân rã câu hỏi multi-step.
- **Retriever Agent** (`Qwen/Qwen2.5-7B-Instruct`): Định vị bảng & ô dữ liệu.
- **Programmer Agent** (`Qwen/Qwen2.5-Coder-14B-Instruct`): Sinh mã Python PoT biểu thức đại số.
- **Critic / Verifier Agent** (`Qwen/Qwen2.5-Coder-3B-Instruct`): Kiểm tra logic kế toán & đối chiếu với Thuyết minh BCTC trong Reflection Loop.

## 2. LLM Serving Engine: SGLang & RadixAttention
Sử dụng **SGLang** với cơ chế **RadixAttention** để tái sử dụng KV-Cache prefix cho prompt template lặp lại giữa các Agent, giảm tối đa latency prefill.

## 3. VRAM Budget (80GB NVIDIA GPU)
- Planner: 26 GB (FP16/INT8)
- Programmer: 14 GB (FP16/INT8)
- Retriever: 10 GB (INT8)
- Critic: 6 GB (INT4 quantized)
- Embedding (`BAAI/bge-m3`): 3 GB (**KHÔNG quantize**)
- Reranker (`BAAI/bge-reranker-v2-m3`): 2 GB (**KHÔNG quantize**)
- KV Cache & Overhead: 19 GB
- **Total**: 80 GB

---

# SECTION 2: CONTEST COMPLIANCE & MODEL MANIFEST (15)

## 1. Compliance Matrix
- **Open-Weights Models Only**: 100% mô hình mở trên Hugging Face. Không dùng API mô hình đóng (GPT-4o, Gemini).
- **Model Size Limit**: Tất cả các mô hình $\le 14B$ parameters.
- **Release Cutoff**: Đều được phát hành trước 01/06/2026.

## 2. Model Citation Script
```python
from huggingface_hub import snapshot_download

models = [
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "Qwen/Qwen2.5-Coder-14B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "BAAI/bge-m3",
    "BAAI/bge-reranker-v2-m3",
]
for m in models:
    snapshot_download(repo_id=m)
```

---

# SECTION 3: SUBMISSION PACKAGING SPECIFICATION (17)

## 📦 1. Zip Structure (`submission.zip`)
```text
submission.zip
├── submission.json              <-- JSON Array duy nhất
└── data/                        <-- Chứa toàn bộ các file CSV được tham chiếu
    ├── table_1.csv
    └── ...
```

## 📜 2. Submission Item Schema (`submission.json`)
```json
[
  {
    "id": 1,
    "question": "Doanh thu thuần của VNM năm 2023 là bao nhiêu?",
    "answer": 63075000000.0,
    "relevant_docs": ["VNM_financial_statements_2023_consolidated"],
    "relevant_tables": ["VNM_financial_statements_2023_consolidated|350"],
    "evidence": [
      {
        "variable": "df1",
        "csv_path": "data/VNM_financial_statements_2023_consolidated_table_1.csv"
      }
    ],
    "pandas_query": "df1[(df1.company=='VNM') & (df1.year==2023)]['net_revenue'].values[0]"
  }
]
```

---

# SECTION 4: QUICKSTART RUNBOOK A TO Z (18)

1. **Setup Virtual Environment & Install Dependencies**:
   `python -m venv .venv` -> `.venv\Scripts\activate` -> `pip install -r requirements.txt`
2. **Launch SGLang Engine**:
   `python -m sglang.launch_server --model-path Qwen/Qwen2.5-Coder-7B-Instruct --port 30000`
3. **Phase 1 Preprocessing**:
   `python -m src.financial_text_to_pandas.preprocessing.pipeline`
4. **Phase 2 Indexing & Retrieval**:
   `python -m src.financial_text_to_pandas.retrieval.corpus`
5. **Phase 3 & 4 Evaluation & Package Submission**:
   `python -m src.financial_text_to_pandas.retrieval.evaluate`
6. **Launch Streamlit Web UI**:
   `streamlit run streamlit_app.py`
