# 14 - Multi-Agent Architecture & Production Deployment

Tài liệu này ghi lại thiết kế **Hệ thống Multi-Agent cộng tác** và hướng dẫn triển khai Production-Grade cho **AI Financial Data Analyst Assistant**, tổng hợp từ nghiên cứu **CLER (Deng et al., AAAI 2026)** và các best practice Production LLM Serving.

---

## 🤝 1. Multi-Agent Collaboration & Reflection

### 1.1 Bốn Agent Chuyên Biệt

| Agent | Vai trò | Chạy | Model gợi ý |
| :--- | :--- | :--- | :--- |
| **Planner** | Nhận câu hỏi phức tạp → phân rã thành multi-step reasoning plan | **1 lần** | Model reasoning mạnh nhất (đắt nhất — quyết định hướng đi toàn cục) |
| **Retriever** | Định vị bảng biểu, footnotes, ô dữ liệu | 1–3 lần | Model vừa/nhỏ |
| **Programmer** | Viết code Python/Pandas từ cells đã grounded | 1–3 lần | Code-generation specialist (`Qwen2.5-Coder`) |
| **Critic / Verifier** | Kiểm tra logic kế toán, đối chiếu chéo số liệu | **Nhiều lần** (Reflection Loop) | Model nhỏ, tốc độ cao (quantized) |

> [!CAUTION]
> **Planner là điểm yếu nhất về chi phí sai lầm.** Nếu Planner lập kế hoạch sai, toàn bộ chuỗi phía sau hỏng hoàn toàn và không Agent nào có thể tự phát hiện hay sửa lại. Đây là vị trí **bắt buộc** đầu tư model mạnh nhất.

### 1.2 Vòng lặp Tự chỉnh sửa (Self-Correction & Dual Verification)

```
User Question
      │
      ▼
  ┌─────────┐     Plan (multi-step)
  │ Planner │ ─────────────────────────────────────────┐
  └─────────┘                                          │
                                                       ▼
                                               ┌──────────────┐
                                               │  Retriever   │ ← TableRAG Level-1+2
                                               └──────┬───────┘
                                                      │ grounded cells
                                                      ▼
                                               ┌──────────────┐
                                               │  Programmer  │ ← De-lexicalization
                                               └──────┬───────┘    + PoT / Chain-of-Table
                                                      │ code
                                                      ▼
                                               ┌──────────────┐
                                               │   Sandbox    │ → exec
                                               └──────┬───────┘
                                                      │ result / error
                                          ┌───────────┴───────────┐
                                          │       Traceback?       │
                                          │   Yes → Self-Correction│──► Programmer (retry)
                                          │   No  → Dual Verify   │
                                          └───────────┬───────────┘
                                                      ▼
                                               ┌──────────────┐
                                               │   Critic /   │ ← Table vs Narrative check
                                               │   Verifier   │
                                               └──────┬───────┘
                                                      │
                                          ┌───────────┴───────────┐
                                          │    Mismatch found?     │
                                          │    Yes → Regenerate   │──► Programmer (retry)
                                          │    No  → Final Answer │
                                          └───────────────────────┘
```

**Tham chiếu: CLER Framework (Deng et al., AAAI 2026)** — Critique-Loop Evidence Retrieval.

---

## ⚡ 2. LLM Serving Engine theo Hạ tầng

### Tại sao cần Serving Engine chuyên dụng?
Nạp model trực tiếp qua PyTorch → GPU **idle trong lúc decode** → lãng phí throughput.

| Engine | Cơ chế tối ưu | Phù hợp |
| :--- | :--- | :--- |
| **vLLM** | PagedAttention + Continuous Batching | Multi-GPU, nhiều model, production scale |
| **TensorRT-LLM** | NVIDIA hardware-level optimization | Latency thấp nhất trên GPU NVIDIA cố định |
| **SGLang** | RadixAttention (tái sử dụng prefix lặp lại) | **Multi-Agent** với prompt template lặp |
| **Ollama / llama.cpp** | Quantization sâu, CPU-friendly | Prototype, máy đơn, không GPU rời |
| **LM Studio** | MLX cho Apple Silicon Unified Memory | Mac M-series, local dev |

> [!TIP]
> **SGLang** là lựa chọn tối ưu nhất cho hệ thống Multi-Agent này vì các Agent lặp lại cùng một system prompt template qua nhiều vòng Reflection Loop → RadixAttention tái sử dụng KV-Cache prefix → tiết kiệm đáng kể thời gian prefill.

---

## 💾 3. VRAM Budget: 4 Agent + Embedding + Reranker trên 1 GPU (80GB)

| Component | VRAM | Ghi chú |
| :--- | :---: | :--- |
| Planner | 26 GB | Model mạnh nhất, FP16 hoặc INT8 nhẹ |
| Programmer | 14 GB | Code-generation specialist |
| Retriever | 10 GB | Vừa |
| Critic | 6 GB | INT4 quantized — chạy lặp nhiều nhất |
| Embedding | 3 GB | **KHÔNG quantize** |
| Reranker | 2 GB | **KHÔNG quantize** |
| KV Cache + Overhead | 19 GB | |
| **Tổng** | **80 GB** | |

### Nguyên tắc Quantization

```
Planner  → INT8 nhẹ hoặc FP16  (chạy 1 lần, sai là hỏng toàn chain)
Critic   → INT4 mạnh nhất       (chạy N lần, nhân trực tiếp chi phí)

Embedding & Reranker → ❌ KHÔNG ĐƯỢC quantize
```

> [!CAUTION]
> **Tuyệt đối không quantize Embedding và Reranker.**  
> Đầu ra là tọa độ vector liên tục. Nhiễu lượng tử hóa làm lệch khoảng cách ngữ nghĩa → sai retrieval → lỗi mà Critic **không thể** phát hiện lại được.

### Multi-LoRA Serving (S-LoRA)
Thay vì load 4 model độc lập → load **1 Base Model** dùng chung + ghép **4 LoRA Adapter** siêu nhẹ theo vai trò:
```
[Base Model - 40GB] + [LoRA_Planner 200MB] + [LoRA_Programmer 200MB]
                    + [LoRA_Retriever 200MB] + [LoRA_Critic 200MB]
→ Tiết kiệm ~40GB VRAM so với 4 model độc lập
```

---

## ⏱️ 4. Latency Budget & Song Song hóa

| Bước | Phụ thuộc | Có thể song song? |
| :--- | :--- | :--- |
| Planner | — | Không (bắt đầu chain) |
| Retriever (multi-table) | Planner plan | **Có** — song song nhiều bảng |
| Programmer | Retriever done | Không |
| Critic × N | Programmer + Sandbox | **Có** — nhiều Critic song song |

**Mẫu Critic song song:**
```python
# Chạy đồng thời 3 Critic độc lập:
import asyncio
critic_tasks = [
    check_accounting_logic(result),
    cross_reference_numbers(result),
    verify_answer_format(result),
]
verdicts = await asyncio.gather(*critic_tasks)
```

---

## 🔒 5. Sandbox Security — 4 Tầng Cách ly

### Tại sao AST-only không đủ?
```
pandas → numpy → numpy.ma.core → inspect → sys → sys.modules → os → os.system("rm -rf /")
```
AST chặn `import os` nhưng không chặn chain truy cập nội bộ → cần **OS-level isolation**.

| Phương pháp | Cơ chế | Mức cách ly |
| :--- | :--- | :---: |
| Chroot + User riêng | Filesystem root + hạn chế quyền | Yếu |
| Docker Container | Linux Namespace + cgroups | Trung bình |
| **gVisor** (Google) | Intercept syscall + kernel ảo trong user-space | Cao |
| **Firecracker MicroVM** | Hardware virtualization, kernel độc lập/phiên | **Cao nhất** |

**Chiến lược 2 tầng cho hệ thống hiện tại:**
```
Tầng 1 (nhanh, rẻ):  SecureASTVisitor → chặn import/exec/dunder
Tầng 2 (cứng):       Docker hoặc gVisor → cách ly OS-level
```

---

## 📚 6. Ba Bài học Cốt lõi cho AI Tài chính

> **Bài học 1 — Cấu trúc là trên hết:**  
> Không bao giờ flatten bảng ngây thơ. Bảo toàn cây phân cấp và metadata của từng ô.

> **Bài học 2 — Tách Suy luận và Tính toán:**  
> LLM sinh chương trình (PoT/PAL). Sandbox Python tính toán. Không để LLM tự tính số.

> **Bài học 3 — Triệt tiêu ảo giác bằng Masking & Verification:**  
> De-lexicalize trước khi sinh code. Reflection Loop tự sửa lỗi. Dual Verification đối chiếu đa tầng.
