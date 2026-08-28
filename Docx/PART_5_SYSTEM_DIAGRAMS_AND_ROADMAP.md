# PART 5: SYSTEM DIAGRAMS, TASK STATUS & FUTURE ROADMAP

Tài liệu này hợp nhất đầy đủ và chi tiết các tệp sơ đồ, phân rã công việc và lộ trình phát triển: **08_Task_Breakdown_and_Status**, **19_Multi_Hop_SubQuery_Implementation_Plan**, **20_End_to_End_System_Architecture_Diagram**, và **Optimization_Proposals**.

---

# SECTION 1: END-TO-END SYSTEM DIAGRAM (20)

```text
[Input Query] ---> (Planner Agent: Sub-query Decomposition)
                          |
                          v
         (Retriever Agent: TableRAG Level-1+2)
                          |
                          v
        (Programmer Agent: De-lexicalization + PoT Python Code)
                          |
                          v
        (Sandboxed Execution: AST & OS Isolation)
                          |
                          v
        (Critic Agent: Dual Verification vs Narrative)
                          |
                          v
               [Verified Final Answer]
```

---

# SECTION 2: TASK BREAKDOWN & COMPLETED STATUS (08)

- [x] **Phase 1: Preprocessing & Table Store** — HTML extraction, grid alignment, Vietnamese numeric parsing, CSV store.
- [x] **Phase 2: Recall-First Table Retrieval** — BM25 + Qwen3-Embedding-8B + Cross-Encoder Reranking.
- [x] **Phase 3: Text-to-Pandas QA & Reasoning** — Grounding, De-lexicalization, PoT Sandbox, Dual Verification.
- [x] **Phase 4: Evaluation, Web UI & Contest Packaging** — Metrics evaluation, Contest submission JSON formatter, Streamlit UI.

---

# SECTION 3: MULTI-HOP DECOMPOSITION ROADMAP (19)

1. **Sub-Query Planner**: LLM phân rã câu hỏi phức tạp thành danh sách sub-queries bằng SGLang JSON Mode.
2. **Parallel Retrieval**: Kích hoạt `asyncio.gather()` tìm kiếm bảng biểu song song cho từng sub-query.
3. **Multi-Table Cell Grounding**: Dò tìm và hợp nhất số liệu trên nhiều bảng trước khi tổng hợp bằng PoT Python Code.

---

# SECTION 4: PRODUCTION OPTIMIZATION PROPOSALS

1. **Quantization Optimization**: Giữ FP16 cho Embedding/Reranker, INT8 cho Retriever/Programmer, INT4 cho Critic.
2. **Prefix Caching**: Tối ưu tốc độ phục vụ Multi-Agent bằng RadixAttention của SGLang engine.
3. **Audit Log Monitoring**: Tự động cảnh báo bảng biểu có nhiễu OCR hoặc thiếu cấu trúc phân cấp.
