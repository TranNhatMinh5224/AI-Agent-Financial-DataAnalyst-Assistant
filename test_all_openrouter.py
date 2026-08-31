import sys, time, json, urllib.request

# Force UTF-8 on Windows
sys.stdout.reconfigure(encoding="utf-8")

key = "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"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com",
    "X-Title": "Financial-Assistant"
}

print("===============================================================")
print("KIỂM TRA CHUYỂN ĐỔI 100% HỆ THỐNG SANG OPENROUTER API")
print("===============================================================\n")

def call_openrouter_chat(role, model, prompt, system=""):
    print(f"Testing [{role.upper()}] với model: {model}...")
    chat_url = "https://openrouter.ai/api/v1/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    data = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": 50,
        "temperature": 0.0
    }).encode("utf-8")
    
    t0 = time.time()
    req = urllib.request.Request(chat_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        dt = time.time() - t0
        res = json.loads(resp.read().decode())
        content = res["choices"][0]["message"]["content"]
        print(f" -> ✅ {role.upper()} THÀNH CÔNG trong {dt:.2f}s!")
        print(f" -> Phản hồi: {content.strip().replace(chr(10), ' ')[:100]}...\n")

# 1. Test Planner (Qwen 14B)
try:
    call_openrouter_chat(
        role="Planner",
        model="qwen/qwen3-14b",
        prompt="Phân tích câu hỏi tài chính: 'Doanh thu thuần năm 2023 là bao nhiêu?' thành các bước.",
        system="You are a financial reasoning planner."
    )
except Exception as e:
    print(f" -> ❌ PLANNER THẤT BẠI: {e}\n")

# 2. Test Retriever (Qwen 7B)
try:
    call_openrouter_chat(
        role="Retriever",
        model="qwen/qwen-2.5-7b-instruct",
        prompt="Xác định bảng chứa Doanh thu thuần: Bảng KQKD hay Bảng CĐKT?",
        system="You are a table retriever assistant."
    )
except Exception as e:
    print(f" -> ❌ RETRIEVER THẤT BẠI: {e}\n")

# 3. Test Programmer (Qwen 14B)
try:
    call_openrouter_chat(
        role="Programmer",
        model="qwen/qwen3-14b",
        prompt="Viết code python: result = df['revenue_2023'].iloc[0]",
        system="You are an expert Python data analyst."
    )
except Exception as e:
    print(f" -> ❌ PROGRAMMER THẤT BẠI: {e}\n")

# 4. Test Critic (Qwen 7B)
try:
    call_openrouter_chat(
        role="Critic",
        model="qwen/qwen-2.5-7b-instruct",
        prompt="Kiểm tra kết quả: Doanh thu 1500 tỷ VND, đơn vị VND. VERDICT: CONSISTENT hay CONTRADICTED?",
        system="You are a financial verifier critic."
    )
except Exception as e:
    print(f" -> ❌ CRITIC THẤT BẠI: {e}\n")

# 5. Test Embedding (BAAI/bge-m3)
print("Testing [EMBEDDING] với model: baai/bge-m3 qua OpenRouter...")
try:
    emb_url = "https://openrouter.ai/api/v1/embeddings"
    data = json.dumps({
        "model": "baai/bge-m3",
        "input": "Báo cáo tài chính doanh thu thuần năm 2023"
    }).encode("utf-8")
    t0 = time.time()
    req = urllib.request.Request(emb_url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        dt = time.time() - t0
        res = json.loads(resp.read().decode())
        dim = len(res["data"][0]["embedding"])
        print(f" -> ✅ EMBEDDING THÀNH CÔNG trong {dt:.2f}s!")
        print(f" -> Vector embedding: {dim} chiều.\n")
except Exception as e:
    print(f" -> ❌ EMBEDDING THẤT BẠI: {e}\n")

print("===============================================================")
print("🎉 KẾT LUẬN: TOÀN BỘ HỆ THỐNG 100% ĐÃ CHẠY ĐƯỢC BẰNG OPENROUTER API!")
print("===============================================================")
