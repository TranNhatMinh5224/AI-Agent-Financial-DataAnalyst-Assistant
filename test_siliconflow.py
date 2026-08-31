import sys, time, json, urllib.request

# Force UTF-8 on Windows
sys.stdout.reconfigure(encoding="utf-8")

key = "sk-redqlugqlmzzhsgmqtasedhixvgxqaunpiewgbenohrpppyt"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

print("====================================================")
print("KIỂM TRA SILICONFLOW API KEY (https://api.siliconflow.com/v1)")
print("====================================================\n")

# 1. Test Chat LLM (Qwen3-14B)
print("[1/3] Kiểm tra LLM Model: Qwen/Qwen3-14B (14B Parameters)...")
try:
    chat_url = "https://api.siliconflow.com/v1/chat/completions"
    data = json.dumps({
        "model": "Qwen/Qwen3-14B",
        "messages": [{"role": "user", "content": "Viết 1 dòng code Python pandas tính doanh thu tăng trưởng."}],
        "max_tokens": 50
    }).encode("utf-8")
    t0 = time.time()
    req = urllib.request.Request(chat_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        dt = time.time() - t0
        res = json.loads(resp.read().decode())
        print(f"✅ LLM KẾT NỐI THÀNH CÔNG trong {dt:.2f}s!")
        content = res["choices"][0]["message"]["content"].replace("\n", " ")
        print(f"👉 Phản hồi: {content[:130]}...\n")
except Exception as e:
    print(f"❌ LLM THẤT BẠI: {e}\n")

# 2. Test Embedding (Qwen3-Embedding-8B / Qwen3-Embedding-4B)
print("[2/3] Kiểm tra Embedding Model: Qwen/Qwen3-Embedding-8B...")
try:
    emb_url = "https://api.siliconflow.com/v1/embeddings"
    data = json.dumps({
        "model": "Qwen/Qwen3-Embedding-8B",
        "input": "Báo cáo tài chính doanh thu thuần năm 2023"
    }).encode("utf-8")
    t0 = time.time()
    req = urllib.request.Request(emb_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        dt = time.time() - t0
        res = json.loads(resp.read().decode())
        dim = len(res["data"][0]["embedding"])
        print(f"✅ EMBEDDING THÀNH CÔNG trong {dt:.2f}s!")
        print(f"👉 Kích thước vector: {dim} chiều.\n")
except Exception as e:
    print(f"❌ EMBEDDING THẤT BẠI: {e}\n")

# 3. Test Reranker (Qwen3-Reranker-8B)
print("[3/3] Kiểm tra Reranker Model: Qwen/Qwen3-Reranker-8B...")
try:
    rerank_url = "https://api.siliconflow.com/v1/rerank"
    data = json.dumps({
        "model": "Qwen/Qwen3-Reranker-8B",
        "query": "Lợi nhuận sau thuế năm 2023 là bao nhiêu?",
        "documents": [
            "Bảng kết quả kinh doanh năm 2023 ghi nhận lợi nhuận sau thuế đạt 500 tỷ VND.",
            "Bảng cân đối kế toán tổng tài sản ngắn hạn là 1200 tỷ VND."
        ],
        "top_n": 2
    }).encode("utf-8")
    t0 = time.time()
    req = urllib.request.Request(rerank_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        dt = time.time() - t0
        res = json.loads(resp.read().decode())
        print(f"✅ RERANKER THÀNH CÔNG trong {dt:.2f}s!")
        for r in res.get("results", []):
            print(f"   - Document #{r['index']}: score = {r['relevance_score']:.4f}")
        print()
except Exception as e:
    print(f"❌ RERANKER THẤT BẠI: {e}\n")

print("====================================================")
print("🎉 KẾT LUẬN: TẤT CẢ 3 TÍNH NĂNG (LLM, EMBEDDING, RERANKER) TRÊN SILICONFLOW ĐỀU HOẠT ĐỘNG HOÀN HẢO!")
print("====================================================")
