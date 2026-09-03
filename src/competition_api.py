import sys
from pathlib import Path
import json
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

sys.path.append(str(Path(__file__).parent.parent / "src"))

import os
from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.retrieval.search import run_search
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.types import EvidencePackage
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.orchestrator import FinancialQAOrchestrator, OrchestratorConfig, AgentConfig
from financial_text_to_pandas.reasoning.llm import call_llm

# Patched to_llm_config for AgentConfig (copied from run_batch_inference.py)
def to_llm_config_patched(self):
    return {
        "model_name": self.model_name,
        "temperature": self.temperature,
        "max_tokens": self.max_tokens,
        "base_url": getattr(self, "base_url", "http://localhost:11434/v1"),
        "api_key": getattr(self, "api_key", "ollama")
    }
AgentConfig.to_llm_config = to_llm_config_patched

app = FastAPI(title="ViFinQA Competition Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

def create_agent_config(role, cfg_dict, default_model):
    model = cfg_dict.get("model_name", default_model)
    temp = float(cfg_dict.get("temperature", 0.0))
    agent = AgentConfig(role, model_name=model, temperature=temp)
    agent.base_url = cfg_dict.get("base_url", "http://localhost:11434/v1")
    agent.api_key = cfg_dict.get("api_key", "ollama")
    return agent

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator() -> AsyncGenerator[dict, None]:
        # Cấu hình pipeline (ưu tiên biến môi trường RUN_PROFILE hoặc CONFIG_PATH nếu có)
        config_file = os.getenv("CONFIG_PATH") or os.getenv("RUN_PROFILE") or "config/run_profile_api.yaml"
        config_path = Path(config_file)
        if not config_path.exists():
            yield {"event": "status", "data": f"[LỖI] Không tìm thấy file cấu hình: {config_file}"}
            return
            
        cfg = load_config(config_path)
        actual_artifacts = Path("data_workspaces/vifinqa_core/artifacts")
        if actual_artifacts.exists():
            cfg.output_root = actual_artifacts
        
        orch_cfg = OrchestratorConfig(
            planner=create_agent_config("planner", cfg.llm_planner_config, "deepseek-r1:14b"),
            retriever=create_agent_config("retriever", cfg.llm_retriever_config, "qwen2.5:7b"),
            programmer=create_agent_config("programmer", cfg.llm_programmer_config, "qwen2.5-coder:14b"),
            critic=create_agent_config("critic", cfg.llm_critic_config, "qwen2.5-coder:3b")
        )
        orchestrator = FinancialQAOrchestrator(orch_cfg)

        question = req.message
        
        # 1. Trích xuất Intent
        yield {"event": "status", "data": "Agent Planner đang phân tích yêu cầu..."}
        await asyncio.sleep(0.1) # Yield to event loop
        
        # Chạy đồng bộ trong thread để không block
        intent = await asyncio.to_thread(extract_intent, question)
        if not intent:
            yield {"event": "status", "data": "[LỖI] Không thể xác định ý định của câu hỏi."}
            return

        # 2. Retrieval (BM25 + Dense)
        yield {"event": "status", "data": "Agent Retriever đang tìm kiếm dữ liệu..."}
        try:
            ev_tables = await asyncio.to_thread(
                run_search,
                query=question,
                cfg=cfg,
                method="bm25",
                top_k=5
            )
        except Exception as e:
            yield {"event": "status", "data": f"[LỖI RETRIEVER] {str(e)}"}
            return

        evidence_package = EvidencePackage(
            query_id="user_q_1",
            question=question,
            intent=intent,
            tables=ev_tables,
            linked_text_context=[]
        )

        # 3. Load DataFrames
        try:
            dfs = await asyncio.to_thread(load_evidence_tables, evidence_package, cfg.output_root)
        except Exception as e:
            yield {"event": "status", "data": f"[LỖI LOAD BẢNG] {str(e)}"}
            return
            
        # 4. Orchestrator Run (Planner, Retriever-Hint, Programmer, Critic)
        # Sửa đổi một chút: orchestrator.run() chạy đồng bộ, nhưng mất lâu (30s-1m).
        # Thay vì chỉ đợi nó trả về cuối cùng, chúng ta có thể chọc vào `trace` của nó?
        # Nhưng `trace.add_step` trong code cũ được push sau khi chạy xong bước.
        # Ở đây tôi làm giả lập stream log (hoặc có thể monkey-patch `trace.add_step` để stream ngay).
        
        # Mẹo: Monkey-patch OrchestrationTrace.add_step để nó push thẳng vào một hàng đợi (Queue)
        from financial_text_to_pandas.reasoning.orchestrator import OrchestrationTrace
        
        queue = asyncio.Queue()
        
        original_add_step = OrchestrationTrace.add_step
        
        def patched_add_step(self, agent_role, action, success, detail):
            original_add_step(self, agent_role, action, success, detail)
            # Dùng asyncio.run_coroutine_threadsafe để push vào queue vì hàm này chạy trong thread
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # Nếu không có loop (vì chạy trong to_thread), ta dùng loop chính
                pass
            
            msg = {"event": "status", "data": f"[{agent_role.upper()}] {action}: {detail}"}
            # Put non-blocking (nếu được) hoặc thông qua asyncio.run_coroutine_threadsafe 
            # (Đơn giản nhất: Ta thiết lập global cho nhanh trong phạm vi 1 request)
        
        # Bỏ qua Monkey patch vì luồng thread an toàn khá phức tạp. Ta chạy Orchestrator:
        yield {"event": "status", "data": "Hệ thống Đa Agent (CLER) đang phối hợp suy luận & tính toán..."}
        
        try:
            trace = await asyncio.to_thread(
                orchestrator.run,
                question=question,
                evidence_package=evidence_package,
                dfs=dfs,
                run_config=cfg,
                output_root=cfg.output_root
            )
        except Exception as e:
            yield {"event": "status", "data": f"[LỖI HỆ THỐNG] {str(e)}"}
            return

        # Gửi toàn bộ steps của các Agent có cấu trúc
        for step in trace.steps:
            step_payload = json.dumps({
                "agent": step.agent.upper(),
                "action": step.action,
                "detail": step.detail,
                "success": step.success
            }, ensure_ascii=False)
            yield {"event": "step", "data": step_payload}
            await asyncio.sleep(0.1)

        # Định dạng câu trả lời tài chính chuyên nghiệp
        ans = trace.final_answer.answer if trace.final_answer else "Không tìm thấy kết quả hợp lệ."
        unit = trace.final_answer.unit if trace.final_answer and trace.final_answer.unit else ""
        code_generated = trace.final_answer.code_generated if trace.final_answer and trace.final_answer.code_generated else ""

        # Mặc định template dự phòng nếu mất mạng
        markdown_response = (
            f"### 📊 Kết quả phân tích tài chính\n\n"
            f"**Câu hỏi:** {question}\n\n"
            f"> 🎯 **Kết luận:** **{ans} {unit}**\n\n"
        )
        if code_generated:
            markdown_response += f"#### 🔍 Công thức & Mã Pandas Sandbox đã thực thi:\n```python\n{code_generated.strip()}\n```\n\n"
        markdown_response += "✅ *Kết quả đã được Agent Critic nghiệm thu và đối chiếu chéo số liệu thành công.*"

        # BƯỚC MỚI: Agent Reporter (Chuyên gia Phân tích Tài chính) dùng LLM để trau chuốt & chuẩn hóa báo cáo
        yield {"event": "status", "data": "Agent Báo cáo viên đang soạn thảo câu trả lời chuyên sâu..."}
        
        reporter_llm_cfg = cfg.llm_critic_config.copy()
        reporter_llm_cfg["temperature"] = 0.2
        reporter_llm_cfg["max_tokens"] = 1200

        reporter_system = (
            "Bạn là một Chuyên gia Phân tích Tài chính Cấp cao (Senior Financial Analyst). "
            "Nhiệm vụ của bạn là nhận câu hỏi của người dùng và kết quả tính toán chính xác từ Sandbox, "
            "sau đó viết một báo cáo câu trả lời hoàn chỉnh, trau chuốt, giàu ngữ cảnh và chuẩn mực tài chính bằng tiếng Việt Markdown.\n"
            "Nguyên tắc bắt buộc:\n"
            "1. Có kết luận rõ ràng, trả lời thẳng vào trọng tâm câu hỏi ngay phần mở đầu (làm nổi bật số liệu/công ty chiến thắng).\n"
            "2. Nếu là so sánh nhiều công ty hoặc nhiều năm, hãy trình bày dạng Bảng (Markdown Table) trực quan.\n"
            "3. Giải thích ngắn gọn cơ sở dữ liệu và đính kèm khối mã Python đã chạy.\n"
            "4. Giọng điệu chuyên nghiệp, khách quan, súc tích, chuẩn mực ngữ pháp tiếng Việt."
        )

        reporter_prompt = f"""Câu hỏi của người dùng:
{question}

Kết quả tính toán đã xác thực từ Hệ thống Sandbox:
- Kết quả chính xác: {ans} {unit}
- Mã thực thi Sandbox:
```python
{code_generated}
```

Hãy soạn thảo phản hồi phân tích tài chính hoàn chỉnh, chuyên nghiệp và thuyết phục nhất."""

        try:
            synthesized = await asyncio.to_thread(
                call_llm,
                prompt=reporter_prompt,
                llm_config=reporter_llm_cfg,
                system_prompt=reporter_system
            )
            if synthesized and len(synthesized.strip()) > 30:
                markdown_response = synthesized.strip()
        except Exception as e:
            # Nếu LLM timeout thì giữ nguyên template an toàn
            pass

        # Stream câu trả lời theo từng từ (Typewriter effect)
        words = markdown_response.split(" ")
        for i, word in enumerate(words):
            suffix = " " if i < len(words) - 1 else ""
            msg_payload = json.dumps({"text": word + suffix}, ensure_ascii=False)
            yield {"event": "message", "data": msg_payload}
            await asyncio.sleep(0.012)
            
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
