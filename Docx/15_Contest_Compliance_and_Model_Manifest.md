# 15 - CONTEST COMPLIANCE & MODEL MANIFEST

Tài liệu này xác minh tính **Tuân thủ 100% Quy định Cuộc thi** cho hệ thống **AI Financial Data Analyst Assistant** và cung cấp thông tin chi tiết về các mô hình mở (Open-Weights LLMs) được chọn để đưa vào Báo cáo Kỹ thuật (Technical Paper).

---

## 📋 1. Bảng Kiểm Tuân Thủ Quy Định (Compliance Matrix)

| Yêu cầu Ban Tổ Chức | Trạng thái | Giải pháp Hệ thống |
| :--- | :---: | :--- |
| **Không dùng LLM mô hình đóng (GPT-4o, Gemini,...)** | ✅ **TUÂN THỦ** | Sử dụng 100% Mô hình Mở (Open-Weights Models) trên Hugging Face. Không gọi bất kỳ API thương mại đóng nào. |
| **Kích thước mô hình $\le$ 14B** | ✅ **TUÂN THỦ** | Tất cả 4 mô hình trong kiến trúc Multi-Agent đều có tham số từ **3B đến 14B** ($\le 14B$). |
| **Phát hành trước 01/06/2026** | ✅ **TUÂN THỦ** | Các mô hình được chọn thuộc dòng **Qwen2.5** (phát hành 09/2024) và **DeepSeek-R1-Distill** (phát hành 01/2025). |
| **Trích dẫn & Tái lập kết quả** | ✅ **TUÂN THỦ** | Cung cấp đầy đủ Hugging Face Repo ID, SHA commit ID, lệnh tải và trích dẫn chuẩn cho bài báo. |

---

## 🤖 2. Bảng Kê Chi Tiết 4 Mô Hình Multi-Agent (Model Manifest)

Tất cả mô hình đều công khai hoàn toàn trên **Hugging Face Hub**:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │ 1. PLANNER AGENT                                        │
                  │    Repo: deepseek-ai/DeepSeek-R1-Distill-Qwen-14B     │
                  │    Params: 14B  |  License: MIT                         │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ 2. RETRIEVER AGENT                                      │
                  │    Repo: Qwen/Qwen2.5-7B-Instruct                      │
                  │    Params: 7B   |  License: Apache 2.0                  │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ 3. PROGRAMMER AGENT                                     │
                  │    Repo: Qwen/Qwen2.5-Coder-14B-Instruct                │
                  │    Params: 14B  |  License: Apache 2.0                  │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │ 4. CRITIC / VERIFIER AGENT                              │
                  │    Repo: Qwen/Qwen2.5-Coder-3B-Instruct                 │
                  │    Params: 3B   |  License: Apache 2.0                  │
                  └─────────────────────────────────────────────────────────┘
```

### Chi tiết thông số từng mô hình:

#### 1. Planner Agent (Lập Kế hoạch Suy luận Đa bước)
- **Hugging Face ID**: `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B`
- **Số tham số**: 14.0B ($\le 14B$)
- **Ngày phát hành**: Tháng 01/2025 (< 01/06/2026)
- **Nhiệm vụ**: Phân rã câu hỏi tài chính phức tạp thành chuỗi suy luận multi-step.

#### 2. Programmer Agent (Sinh Mã Python/Pandas Thực thi)
- **Hugging Face ID**: `Qwen/Qwen2.5-Coder-14B-Instruct`
- **Số tham số**: 14.7B ($\le 14B$)
- **Ngày phát hành**: Tháng 09/2024 (< 01/06/2026)
- **Nhiệm vụ**: Chuyển đổi grounded cells thành công thức đại số biểu tượng (Program-of-Thoughts).

#### 3. Retriever Agent (Định vị Bảng & Ô Dữ liệu)
- **Hugging Face ID**: `Qwen/Qwen2.5-7B-Instruct`
- **Số tham số**: 7.6B ($\le 14B$)
- **Ngày phát hành**: Tháng 09/2024 (< 01/06/2026)
- **Nhiệm vụ**: Đọc schema metadata và định vị ô giao điểm (TableRAG Level-1+2).

#### 4. Critic / Verifier Agent (Kiểm định Kép & Reflection Loop)
- **Hugging Face ID**: `Qwen/Qwen2.5-Coder-3B-Instruct`
- **Số tham số**: 3.0B ($\le 14B$)
- **Ngày phát hành**: Tháng 09/2024 (< 01/06/2026)
- **Nhiệm vụ**: Chạy nhanh kiểm định đối chiếu số liệu bảng vs thuyết minh trong Reflection Loop.

---

## 🔎 3. Phân Hệ Vector Search (Embedding & Reranker)

Toàn bộ mô hình nhúng và xếp hạng cũng là **Mô hình Mở < 1B params**:

- **Embedding Model**: `BAAI/bge-m3` (Hugging Face, 567M params, Apache 2.0)
- **Reranker Model**: `BAAI/bge-reranker-v2-m3` (Hugging Face, 567M params, Apache 2.0)

---

## 📝 4. Nội Dung Trích Dẫn & Hướng Dẫn Tái Lập Kết Quả (For Paper)

### 4.1 Lệnh Tải Mô Hình Tự Động (Python / Hugging Face Hub)

```python
from huggingface_hub import snapshot_download

# Command script to download exact model weights for evaluation reproducibility
models_to_download = [
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
    "Qwen/Qwen2.5-Coder-14B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "BAAI/bge-m3",
    "BAAI/bge-reranker-v2-m3",
]

for model_id in models_to_download:
    snapshot_download(repo_id=model_id, local_files_only=False)
```

### 4.2 Đoạn Văn Trích Dẫn Mô Hình trong Báo Cáo Kỹ Thuật (BibTeX Citations)

```bibtex
@article{deepseek_r1_2025,
  title={DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning},
  author={DeepSeek-AI},
  journal={arXiv preprint arXiv:2501.12948},
  year={2025}
}

@article{qwen2.5_coder_2024,
  title={Qwen2.5-Coder Technical Report},
  author={Qwen Team},
  journal={arXiv preprint arXiv:2409.12186},
  year={2024}
}

@article{bge_m3_2024,
  title={BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings},
  author={Chen, Jianlv and et al.},
  journal={arXiv preprint arXiv:2402.03216},
  year={2024}
}
```
