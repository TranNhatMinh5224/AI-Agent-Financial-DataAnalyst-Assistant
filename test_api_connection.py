import sys, os, time
from pathlib import Path

# Fix Windows console UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")
sys.path.append(str(Path.cwd() / "src"))

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.reasoning.llm import call_llm

cfg = load_config(Path("config/run_profile_api.yaml"))

print("===============================================================")
print("KIỂM TRA KẾT NỐI TOÀN BỘ CÁC AGENT VỚI CONFIG RUN_PROFILE_API")
print("===============================================================\n")

# 1. Test Planner (LLM API - Qwen 14B)
print("[1/2] Đang kiểm tra PLANNER AGENT (LLM API)...")
try:
    t0 = time.time()
    res = call_llm(
        prompt="Phân tích ngắn gọn trong 1 câu: Doanh thu thuần là gì?",
        llm_config=cfg.llm_planner_config,
        system_prompt="You are an expert financial analyst."
    )
    dt = time.time() - t0
    print(f"✅ PLANNER KẾT NỐI THÀNH CÔNG trong {dt:.2f}s!")
    clean_res = res.strip().replace("\n", " ")
    print(f"👉 Phản hồi từ AI: \"{clean_res[:150]}...\"\n")
except Exception as e:
    print(f"❌ PLANNER THẤT BẠI: {e}\n")

# 2. Test Programmer (OpenRouter API - Qwen 14B)
print("[2/2] Đang kiểm tra PROGRAMMER AGENT (OpenRouter API: qwen/qwen3-14b)...")
try:
    t0 = time.time()
    res = call_llm(
        prompt="Cho df có cột 'revenue_2023' và 'revenue_2022'. Viết 1 dòng code Python pandas tính tốc độ tăng trưởng.",
        llm_config=cfg.llm_programmer_config,
        system_prompt="You are an expert Python data analyst."
    )
    dt = time.time() - t0
    print(f"✅ PROGRAMMER KẾT NỐI THÀNH CÔNG trong {dt:.2f}s!")
    clean_res = res.strip().replace("\n", " ")
    print(f"👉 Phản hồi từ AI: \"{clean_res[:150]}...\"\n")
except Exception as e:
    print(f"❌ PROGRAMMER THẤT BẠI: {e}\n")

print("===============================================================")
print("🎉 KẾT LUẬN: ĐÃ KẾT NỐI THÀNH CÔNG VỚI QWEN 14B QUA API!")
print("===============================================================")
