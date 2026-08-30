"""
streamlit_app.py — Giao diện Web tương tác trực quan cho AI Financial Data Analyst.
Sử dụng Streamlit để hiển thị toàn bộ pipeline suy luận (Retrieval, Grounding, Code, Answer, Trace).
"""

import sys
import os
import uuid
from pathlib import Path
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load biến môi trường từ file .env nếu có
except ImportError:
    pass

# Thêm src/ vào sys.path để nhận diện package
sys.path.append(str(Path(__file__).parent / "src"))

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.retrieval.search import run_search
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.types import EvidencePackage
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.orchestrator import FinancialQAOrchestrator, OrchestratorConfig, AgentConfig

# Tùy chỉnh giao diện
st.set_page_config(
    page_title="AI Financial Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════
# 1. HỆ THỐNG KHỞI TẠO (CACHE ĐỂ CHẠY NHANH)
# ══════════════════════════════════════════════════════════════

@st.cache_resource
def init_system(
    config_path="config/run_profile.yaml",
    base_url=None,
    api_key=None,
    planner_model=None,
    retriever_model=None,
    programmer_model=None,
    critic_model=None
):
    cfg = load_config(Path(config_path))
    
    # Hàm helper tạo agent config
    def create_agent_config(role, cfg_dict, override_model, env_model_key):
        # Ưu tiên: 1. UI Override -> 2. Biến môi trường -> 3. Config YAML -> 4. Default string
        default_from_env = os.getenv(env_model_key, cfg_dict.get("model_name", override_model))
        model = override_model if override_model else default_from_env
        temp = float(cfg_dict.get("temperature", 0.0))
        agent = AgentConfig(role, model_name=model, temperature=temp)
        agent.base_url = base_url or os.getenv("LLM_BASE_URL", cfg_dict.get("base_url", "http://localhost:11434/v1"))
        agent.api_key = api_key or os.getenv("LLM_API_KEY", cfg_dict.get("api_key", "ollama"))
        return agent

    # Monkey-patch to_llm_config để truyền được base_url
    def to_llm_config_patched(self):
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": getattr(self, "base_url", "http://localhost:11434/v1"),
            "api_key": getattr(self, "api_key", "ollama")
        }
    AgentConfig.to_llm_config = to_llm_config_patched

    orch_cfg = OrchestratorConfig(
        planner=create_agent_config("planner", cfg.llm_planner_config, planner_model, "LLM_PLANNER_MODEL"),
        retriever=create_agent_config("retriever", cfg.llm_retriever_config, retriever_model, "LLM_RETRIEVER_MODEL"),
        programmer=create_agent_config("programmer", cfg.llm_programmer_config, programmer_model, "LLM_PROGRAMMER_MODEL"),
        critic=create_agent_config("critic", cfg.llm_critic_config, critic_model, "LLM_CRITIC_MODEL")
    )
    
    orchestrator = FinancialQAOrchestrator(orch_cfg)
    return cfg, orchestrator

# ── SIDEBAR CẤU HÌNH LLM ──
with st.sidebar:
    st.header("⚙️ Cấu Hình LLM API")
    st.markdown("Thay đổi Model tức thì không cần sửa code. Các ô này tự động lấy từ biến môi trường hoặc file `.env` (nếu có).")
    
    ui_base_url = st.text_input("Base URL", value=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"))
    ui_api_key = st.text_input("API Key", value=os.getenv("LLM_API_KEY", "ollama"), type="password")
    
    st.subheader("🤖 Gán Model cho từng Agent")
    ui_planner = st.text_input("Planner Model", value=os.getenv("LLM_PLANNER_MODEL", "deepseek-r1:14b"))
    ui_retriever = st.text_input("Retriever Model", value=os.getenv("LLM_RETRIEVER_MODEL", "qwen2.5:7b"))
    ui_programmer = st.text_input("Programmer Model (PoT)", value=os.getenv("LLM_PROGRAMMER_MODEL", "qwen2.5-coder:14b"))
    ui_critic = st.text_input("Critic Model", value=os.getenv("LLM_CRITIC_MODEL", "qwen2.5-coder:3b"))

try:
    cfg, orchestrator = init_system(
        base_url=ui_base_url,
        api_key=ui_api_key,
        planner_model=ui_planner,
        retriever_model=ui_retriever,
        programmer_model=ui_programmer,
        critic_model=ui_critic
    )
except Exception as e:
    st.error(f"Lỗi cấu hình hệ thống: {e}")
    st.stop()


# ══════════════════════════════════════════════════════════════
# 2. GIAO DIỆN (UI)
# ══════════════════════════════════════════════════════════════

st.title("📈 AI Financial Data Analyst Assistant")
st.markdown("Hệ thống giải đáp tự động câu hỏi tài chính sử dụng kiến trúc **Multi-Agent RAG + Program-of-Thoughts (PoT)**.")

# ── INPUT PANEL ──
with st.container():
    query = st.text_input(
        "💬 Nhập câu hỏi tài chính (hỏi về Báo cáo Tài chính của VN):", 
        placeholder="VD: Biên lợi nhuận gộp của FPT năm 2023 là bao nhiêu phần trăm?"
    )
    analyze_btn = st.button("🚀 Thực thi Phân tích", type="primary")

if analyze_btn and query:
    with st.spinner("🤖 Các Agent đang hội ý phân tích dữ liệu... (khoảng 10-30s)"):
        # ----- EXECUTE PIPELINE -----
        # 1. Search (Hybrid -> Fallback BM25)
        try:
            tables = run_search(query, cfg, method="hybrid", top_k=5)
        except Exception as e:
            st.toast(f"Hybrid Search lỗi, tự động chuyển về BM25 ({e})", icon="⚠️")
            tables = run_search(query, cfg, method="bm25", top_k=5, no_reranker=True)
            
        # 2. Intent & Package
        intent = extract_intent(query)
        package = EvidencePackage(
            query_id=str(uuid.uuid4()),
            question=query,
            intent=intent,
            tables=tables,
            linked_text_context=[]
        )
        
        # 3. Load dfs
        output_root = cfg.output_root
        if not output_root.is_absolute():
            output_root = Path.cwd() / output_root
        dfs = load_evidence_tables(package, output_root)
        
        # 4. Orchestrate
        trace = orchestrator.run(query, package, dfs, run_config=cfg, output_root=output_root)
        ans = trace.final_answer

    st.success("✅ Phân tích thành công!")
    st.divider()

    # ── LAYOUT 2 CỘT ──
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        # ── ANSWER PANEL ──
        st.subheader("💡 Kết Quả Cuối Cùng")
        with st.container(border=True):
            if ans and ans.answer is not None:
                # Hiển thị số lớn, có màu sắc
                st.metric("Đáp án số (Numeric Answer)", f"{ans.answer:,.2f} {ans.unit or ''}".strip())
                if ans.verification_status == "verified_dual":
                    st.success("Tình trạng: **Đã kiểm chứng (Verified)**")
                else:
                    st.info(f"Tình trạng: **{ans.verification_status}**")
            else:
                st.warning("Không tính được kết quả (Answer = None).")
                if ans and ans.error_type:
                    st.error(f"Lỗi: {ans.error_type}")

        # ── CODE PANEL ──
        st.subheader("💻 Mã Nguồn Sinh Ra (PoT)")
        with st.container(border=True):
            if ans and ans.code_generated:
                st.code(ans.code_generated, language="python")
            else:
                st.write("*Không có Python code (hoặc dùng Deterministic Lookup)*")

        # ── TRACE PANEL ──
        st.subheader("🕵️ Nhật ký Suy luận (Trace)")
        with st.expander("Xem chi tiết các bước của Multi-Agent", expanded=True):
            st.text(trace.summary())

    with col_right:
        # ── RETRIEVAL PANEL ──
        st.subheader("🔍 Nguồn Dữ Liệu Bảng (Retriever)")
        if tables:
            for i, ev in enumerate(tables, 1):
                c = ev.candidate
                with st.expander(f"📁 Bảng: {c.table_id} (Rank {i})"):
                    st.caption(f"Đường dẫn: `{c.csv_path}`")
                    c_cols = st.columns(3)
                    c_cols[0].metric("BM25", f"{c.bm25_score:.2f}")
                    c_cols[1].metric("Dense", f"{c.dense_score:.2f}")
                    c_cols[2].metric("Rerank", f"{c.reranker_score:.2f}")
        else:
            st.info("Không tìm thấy bảng dữ liệu.")

        # ── GROUNDING PANEL ──
        st.subheader("🎯 Grounded Cells (Bóc tách dữ liệu)")
        if ans and ans.citations:
            for idx, cit in enumerate(ans.citations):
                with st.container(border=True):
                    st.markdown(f"**Biến `NUM_{idx}`**")
                    st.markdown(f"- 📁 **Bảng:** `{cit.table_id}`")
                    st.markdown(f"- 📏 **Hàng:** `{cit.row_label}`")
                    st.markdown(f"- 📐 **Cột:** `{cit.column_label}`")
        else:
            st.info("Không có ô số nào được trích xuất (Grounded).")
