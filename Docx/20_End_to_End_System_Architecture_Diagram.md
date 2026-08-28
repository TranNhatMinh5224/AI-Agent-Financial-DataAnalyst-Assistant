# 20 - END-TO-END SYSTEM ARCHITECTURE (Bản vẽ Kiến trúc Toàn cảnh)
**Tài liệu mô tả chi tiết luồng dữ liệu (Data flow) của hệ thống AI Financial Data Analyst Assistant từ khi User đặt câu hỏi cho đến khi có đáp án cuối cùng.**

---

## 🎨 Sơ đồ Kiến trúc Multi-Agent RAG (End-to-End)

Dưới đây là bản vẽ kỹ thuật luồng đi của hệ thống. Bạn có thể xem trên GitHub hoặc các trình soạn thảo hỗ trợ Markdown (như VS Code).

```mermaid
flowchart TD
    %% Định nghĩa các Style cho Đồ thị
    classDef user fill:#ff9999,stroke:#333,stroke-width:2px,color:#000;
    classDef agent fill:#99ccff,stroke:#333,stroke-width:2px,color:#000;
    classDef engine fill:#ffe699,stroke:#333,stroke-width:2px,color:#000;
    classDef db fill:#c2f0c2,stroke:#333,stroke-width:2px,color:#000;
    classDef secure fill:#ffb366,stroke:#333,stroke-width:2px,color:#000,stroke-dasharray: 5 5;

    %% 1. User Input
    User((🧑 Khách hàng / BTC)):::user
    Query["Câu hỏi Tài chính phức tạp\n(VD: Biên LN gộp AAA 2023?)"]
    
    User --> Query
    
    %% 2. Planner Agent
    subgraph Phase_1[🧠 Giai đoạn 1: Phân tích & Lập kế hoạch]
        Planner["🤖 Planner Agent\n(Qwen2.5-Coder)"]:::agent
        Intent_JSON["📝 Intent JSON\n(Sub-query 1: LN Gộp)\n(Sub-query 2: Doanh thu)"]
        Planner -->|Phân rã câu hỏi\n(Decomposition)| Intent_JSON
    end
    
    Query --> Planner
    
    %% 3. Retrieval & Reranking
    subgraph Phase_2[🔍 Giai đoạn 2: Tìm kiếm & Đánh giá]
        BM25_Dense["⚡ Hybrid Search\n(BM25 + Dense BGE-M3)"]:::engine
        Corpus[("🗄️ Table Corpus\n(Hàng ngàn bảng CSV)")]:::db
        Top50["Danh sách Top 50 Bảng"]
        Reranker["🎯 Cross-Encoder Reranker\n(bge-reranker-v2-m3)"]:::engine
        Top5["Danh sách Top 3-5 Bảng chính xác nhất"]
        
        Intent_JSON --> BM25_Dense
        BM25_Dense <--> Corpus
        BM25_Dense --> Top50
        Top50 --> Reranker
        Reranker -->|Chấm điểm chéo (Cross-Attention)| Top5
    end
    
    %% 4. Cell Grounding & Masking
    subgraph Phase_3[✂️ Giai đoạn 3: Bắt lưới & Khử định danh]
        Grounding["🛠️ Cell Grounding\n(Fuzzy Match + Regex Clean)"]:::engine
        Masking["🎭 Symbolic Masking\n(De-lexicalization)"]:::engine
        Variables["Biến số Python:\nNUM_0 = 135450\nNUM_1 = 498720"]
        
        Top5 --> Grounding
        Grounding -->|Bắt trúng Ô (Cell)| Masking
        Masking --> Variables
    end
    
    %% 5. Programmer & Sandbox
    subgraph Phase_4[💻 Giai đoạn 4: Suy luận Toán học (PoT)]
        Programmer["🤖 Programmer Agent\n(Qwen2.5-Coder)"]:::agent
        Code["📜 Program-of-Thoughts\n(Code Python/Pandas)"]
        Sandbox["🛡️ Secure AST Sandbox\n(Môi trường cách ly)"]:::secure
        Result{"Kết quả tính toán\n(Ví dụ: 27.15%)"}
        
        Variables --> Programmer
        Programmer -->|Sinh Code PoT| Code
        Code --> Sandbox
        Sandbox -->|Thực thi an toàn| Result
        
        %% Self-Correction Loop
        Result -- Lỗi Code (Exception) --> Programmer
    end
    
    %% 6. Critic / Verifier
    subgraph Phase_5[⚖️ Giai đoạn 5: Kiểm duyệt & Chốt đáp án]
        Critic["🤖 Critic Agent\n(Qwen-3B)"]:::agent
        FinalAns["🏆 Dữ liệu nộp bài (submission.json)"]
        
        Result -- Chạy Thành Công --> Critic
        Critic -->|Đối chiếu chéo (Dual Verify)\nLogic Hợp Lệ| FinalAns
        Critic -- Phát hiện ảo giác (Hallucination) --> Programmer
    end
    
    %% Output
    FinalAns --> User
```

---

## 📖 Giải thích 5 Giai đoạn Cốt lõi (The 5 Phases)

1. **Giai đoạn 1 (Planner):** Tiếp nhận câu hỏi "đánh đố" của User. Agent Planner sẽ đóng vai trò như một Kiến trúc sư, tự động chẻ câu hỏi ra thành nhiều câu hỏi con (Sub-queries) để hệ thống đi tìm kiếm độc lập mà không bị sót ý.
2. **Giai đoạn 2 (Retrieval):** Là quá trình cày xới dữ liệu. Đầu tiên dùng lưới quét rộng (Hybrid Search) để vớt lên Top 50. Sau đó dùng Kính lúp (Cross-Encoder Reranker) soi kỹ từng từ một để chốt lại Top 3 Bảng xịn nhất.
3. **Giai đoạn 3 (Grounding):** Bắt đúng con số trong bảng bằng thuật toán `Fuzzy Matching` "lì lợm". Sau đó giấu con số đó đi (Symbolic Masking) thành các biến `NUM_0, NUM_1` để LLM không bị học vẹt hay ảo giác.
4. **Giai đoạn 4 (Programmer & Sandbox):** Programmer Agent (Qwen 14B/7B) chỉ nhìn thấy các biến số, nó sẽ viết phương trình toán học bằng Code (PoT) để giải. Đoạn Code này bị nhốt vào một lồng kính (Secure AST Sandbox) để chạy thật trên CPU, ra đáp án không sai một ly.
5. **Giai đoạn 5 (Critic):** Mọi con số trước khi nộp cho Ban Giám Khảo đều phải được Critic Agent duyệt lại xem có khớp với logic kế toán không. Nếu phát hiện Programmer làm ẩu, nó báo lỗi bắt làm lại (Reflection Loop). Nếu OK, hệ thống đóng gói ra file ZIP nộp bài!
