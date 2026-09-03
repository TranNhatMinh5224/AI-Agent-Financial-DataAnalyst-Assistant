"""
orchestrator.py — Multi-Agent Orchestration Layer.

Reference: CLER Framework (Deng et al., AAAI 2026)
           "Critique-Loop Evidence Retrieval for Financial QA"

Architecture:
    Four specialized agents collaborate in a controlled pipeline:

    ┌─────────┐   Plan    ┌───────────┐  cells  ┌────────────┐
    │ Planner │ ────────► │ Retriever │ ──────► │ Programmer │
    └─────────┘           └───────────┘         └─────┬──────┘
                                                      │ code
                                                      ▼
                                               ┌─────────────┐
                                               │   Sandbox   │
                                               └──────┬──────┘
                                                      │ result / error
                                            ┌─────────┴──────────┐
                                            │ Error → Self-Correct│
                                            │ OK    → Dual-Verify │
                                            └─────────┬──────────┘
                                                      ▼
                                               ┌─────────────┐
                                               │   Critic /  │
                                               │   Verifier  │
                                               └──────┬──────┘
                                                      │
                                            ┌─────────┴──────────┐
                                            │ Mismatch→Regenerate │
                                            │ OK      →Final Ans  │
                                            └────────────────────┘

Design principles:
    - Planner runs ONCE and must use the strongest available model.
    - Critic runs in the Reflection Loop (N times) → must use smallest/fastest model.
    - Multiple Critics can run in PARALLEL (independent verifications).
    - Embedding & Reranker must NEVER be quantized.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from financial_text_to_pandas.types import (
    EvidencePackage,
    CellGroundingResult,
    ReasoningResult,
    VerificationResult,
    FinalAnswer,
    Citation,
)


# ─────────────────────────────────────────────────────────────────────────────
# Agent role constants
# ─────────────────────────────────────────────────────────────────────────────

ROLE_PLANNER    = "planner"
ROLE_RETRIEVER  = "retriever"
ROLE_PROGRAMMER = "programmer"
ROLE_CRITIC     = "critic"


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration config
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Per-agent LLM configuration."""
    role: str
    model_name: str
    temperature: float = 0.0
    max_tokens: int = 1024
    quantization: Optional[str] = None  # "int4" | "int8" | None

    def to_llm_config(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,         # key 'model' — dùng bởi llm.py call_llm()
            "model_name": self.model_name,    # key 'model_name' — fallback compatibility
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "base_url": "http://localhost:11434/v1",  # default, sẽ bị override bởi run_batch_inference.py
            "api_key": "ollama",
        }


@dataclass
class OrchestratorConfig:
    """Full Multi-Agent system configuration."""
    planner:    AgentConfig
    retriever:  AgentConfig
    programmer: AgentConfig
    critic:     AgentConfig
    max_reflection_rounds: int = 3      # Self-Correction retry limit
    parallel_critics: int = 1           # How many Critic tasks to run in parallel
    enable_dual_verification: bool = True

    @classmethod
    def for_ollama_local(cls, base_model: str = "qwen2.5-coder:7b") -> "OrchestratorConfig":
        """Default config for local Ollama development (single-model, no GPU budget concern)."""
        return cls(
            planner=AgentConfig(ROLE_PLANNER, base_model, temperature=0.0),
            retriever=AgentConfig(ROLE_RETRIEVER, base_model, temperature=0.0),
            programmer=AgentConfig(ROLE_PROGRAMMER, base_model, temperature=0.0),
            critic=AgentConfig(ROLE_CRITIC, base_model, temperature=0.0),
        )

    @classmethod
    def for_production_gpu(
        cls,
        planner_model: str,
        programmer_model: str,
        critic_model: str,
        retriever_model: str,
    ) -> "OrchestratorConfig":
        """Production config: assign strongest model to Planner, quantized to Critic."""
        return cls(
            planner=AgentConfig(ROLE_PLANNER, planner_model, quantization=None),
            retriever=AgentConfig(ROLE_RETRIEVER, retriever_model, quantization="int8"),
            programmer=AgentConfig(ROLE_PROGRAMMER, programmer_model, quantization=None),
            critic=AgentConfig(ROLE_CRITIC, critic_model, quantization="int4"),
            max_reflection_rounds=3,
            parallel_critics=3,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration trace
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AgentStep:
    """One step in the orchestration trace."""
    agent: str
    action: str
    success: bool
    detail: str = ""


@dataclass
class OrchestrationTrace:
    """Audit trail of the full Multi-Agent pipeline execution."""
    question: str
    steps: List[AgentStep] = field(default_factory=list)
    reflection_count: int = 0
    final_answer: Optional[FinalAnswer] = None
    error: Optional[str] = None

    def add_step(self, agent: str, action: str, success: bool, detail: str = ""):
        self.steps.append(AgentStep(agent, action, success, detail))

    def summary(self) -> str:
        lines = [f"[Orchestration] Question: {self.question[:80]}..."]
        for s in self.steps:
            icon = "✅" if s.success else "❌"
            lines.append(f"  {icon} [{s.agent.upper()}] {s.action} — {s.detail}")
        lines.append(f"  Reflection rounds: {self.reflection_count}")
        if self.error:
            lines.append(f"  Error: {self.error}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class FinancialQAOrchestrator:
    """Multi-Agent orchestrator implementing the CLER-style Reflection Loop.

    Manages Planner → Retriever → Programmer → Sandbox → Critic pipeline
    with self-correction and dual verification.
    """

    def __init__(self, cfg: OrchestratorConfig):
        self.cfg = cfg

    # ── Step 1: Planner ───────────────────────────────────────────────────────

    def plan(self, question: str, trace: OrchestrationTrace) -> str:
        """Planner Agent: decompose question into reasoning steps."""
        from financial_text_to_pandas.reasoning.llm import call_llm
        from financial_text_to_pandas.reasoning.prompts import PLANNER_PROMPT_TEMPLATE

        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        try:
            plan_text = call_llm(prompt, self.cfg.planner.to_llm_config())
            trace.add_step(ROLE_PLANNER, "decompose", True, f"Plan generated ({len(plan_text)} chars)")
            return plan_text
        except Exception as e:
            trace.add_step(ROLE_PLANNER, "decompose", False, f"Failed: {str(e)}")
            return f"Failed to generate plan: {str(e)}"

    # ── Step 2: Retriever ─────────────────────────────────────────────────────

    def retrieve(
        self,
        question: str,
        plan: str,
        evidence_package: EvidencePackage,
        trace: OrchestrationTrace,
        dfs: Dict[str, pd.DataFrame],
    ) -> CellGroundingResult:
        """Retriever Agent: ground cells from evidence tables using LLM and heuristics."""
        from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
        from financial_text_to_pandas.reasoning.llm import call_llm
        from financial_text_to_pandas.reasoning.prompts import RETRIEVER_GROUNDING_PROMPT_TEMPLATE

        if dfs is None:
            dfs = {}

        tables_context = ""
        for ev in evidence_package.tables:
            cand = ev.candidate
            tables_context += f"Table ID: {cand.table_id}\nPath: {cand.csv_path}\n\n"

        # [TỐI ƯU HÓA TURBO] Tắt bước LLM Retriever hint vì kết quả không được sử dụng
        # (ground_cells chạy bằng thuật toán schema-aware trực tiếp trên dfs, không nhận input từ call_llm này).
        # Giúp tiết kiệm 2-3 giây mỗi câu và giảm chi phí token OpenRouter.
        # (Đã khôi phục theo yêu cầu của user)
        prompt = RETRIEVER_GROUNDING_PROMPT_TEMPLATE.format(
            question=question,
            tables_context=tables_context
        )
        try:
            call_llm(prompt, self.cfg.retriever.to_llm_config())
            trace.add_step(ROLE_RETRIEVER, "llm_grounding", True, "LLM Retriever hint generated")
        except Exception as e:
            trace.add_step(ROLE_RETRIEVER, "llm_grounding", False, f"LLM hint skipped: {str(e)}")
        trace.add_step(ROLE_RETRIEVER, "llm_grounding", True, "Fast-path schema grounding (bỏ qua LLM hint thừa)")

        # Schema-aware grounding (cơ chế chính)
        grounding = ground_cells(evidence_package.intent, dfs, raw_question=question)
        success = grounding.error_type is None
        trace.add_step(
            ROLE_RETRIEVER, "ground_cells", success,
            f"{len(grounding.grounded_cells)} cells grounded | error={grounding.error_type}"
        )
        return grounding

    # ── Steps 3+4: Programmer + Sandbox with Self-Correction ─────────────────

    def program_and_execute(
        self,
        package: EvidencePackage,
        grounding: CellGroundingResult,
        dfs: Dict[str, Any],
        trace: OrchestrationTrace,
    ) -> ReasoningResult:
        """Programmer Agent + Sandbox with Self-Correction Retry Loop."""
        from financial_text_to_pandas.reasoning.strategy import run_pot_strategy

        result = run_pot_strategy(
            package=package,
            grounding=grounding,
            dfs=dfs,
            llm_config=self.cfg.programmer.to_llm_config(),
            max_retries=self.cfg.max_reflection_rounds,
        )
        trace.reflection_count = result.trace.count("Self-Correction")
        success = result.error_type is None
        trace.add_step(
            ROLE_PROGRAMMER, "pot_execute", success,
            f"result={result.numeric_result}, strategy={result.strategy}"
        )
        return result

    # ── Step 5: Critic (parallel-capable) ─────────────────────────────────────

    def critique(
        self,
        result: ReasoningResult,
        grounding: CellGroundingResult,
        package: EvidencePackage,
        dfs: Dict[str, Any],
        trace: OrchestrationTrace,
    ) -> VerificationResult:
        """Critic Agent: Dual Verification (table vs narrative text)."""
        from financial_text_to_pandas.reasoning.verifier import verify_answer

        verification = verify_answer(result, grounding, package, dfs, self.cfg.critic.to_llm_config())
        trace.add_step(
            ROLE_CRITIC, "dual_verify", verification.is_valid,
            f"status={verification.verification_status}"
        )
        return verification

    # ── Full pipeline ─────────────────────────────────────────────────────────

    def run(
        self,
        question: str,
        evidence_package: EvidencePackage,
        dfs: Dict[str, Any],
        run_config: Any = None,
        output_root: Any = None,
    ) -> OrchestrationTrace:
        """Execute the full Multi-Agent pipeline synchronously.

        Returns an OrchestrationTrace with the final answer and audit trail.
        """
        trace = OrchestrationTrace(question=question)

        # Step 1: Planner
        plan = self.plan(question, trace)

        # Check Multi-hop condition
        intent = evidence_package.intent
        is_multi_hop = intent and (intent.operation == "multi_hop" or len(intent.years) >= 2)
        fallback = False

        if is_multi_hop and run_config and output_root:
            trace.add_step(ROLE_PLANNER, "route", True, "Routing to Multi-hop Flow")
            from financial_text_to_pandas.reasoning.multi_hop import run_multi_hop
            mh_result, mh_grounding, mh_dfs, evidence_package_mh = run_multi_hop(
                question, intent, run_config, output_root, self.cfg.programmer.to_llm_config()
            )
            if mh_result.error_type is None:
                evidence_package = evidence_package_mh
                dfs = mh_dfs
                result = mh_result
                grounding = mh_grounding
                trace.add_step(
                    ROLE_PROGRAMMER, "multi_hop_execute", True,
                    f"Multi-hop result: {result.numeric_result}"
                )
            else:
                trace.add_step(ROLE_PROGRAMMER, "multi_hop_execute", False, "Multi-hop failed. Falling back to Standard Flow.")
                fallback = True
        
        if not is_multi_hop or fallback:
            # Step 2: Retriever (Standard Flow)
            grounding = self.retrieve(question, plan, evidence_package, trace, dfs)
            if grounding.error_type:
                trace.error = f"Grounding failed: {grounding.error_type}"
                trace.final_answer = FinalAnswer(
                    answer=None,
                    answer_type="numeric",
                    unit=evidence_package.intent.unit_requested if evidence_package.intent else None,
                    citations=[],
                    verification_status="invalid",
                    error_type=grounding.error_type,
                    trace=trace.summary(),
                    code_generated="",
                )
                return trace
            # Steps 3+4: Programmer + Sandbox (with Self-Correction built in)
            result = self.program_and_execute(evidence_package, grounding, dfs, trace)

        # Step 5: Critic / Verifier
        verification = self.critique(result, grounding, evidence_package, dfs, trace)

        # Build final answer
        table_to_csv = {ev.candidate.table_id: ev.candidate.csv_path for ev in evidence_package.tables}
        citations = [
            Citation(
                table_id=c.table_id,
                csv_path=table_to_csv.get(c.table_id, ""),
                page_number=c.page_number,
                row_label=c.row_label,
                column_label=c.column_label,
            )
            for c in grounding.grounded_cells
        ]

        trace.final_answer = FinalAnswer(
            answer=verification.final_answer,
            answer_type="numeric",
            unit=evidence_package.intent.unit_requested if evidence_package.intent else None,
            citations=citations,
            verification_status=verification.verification_status,
            error_type=verification.error_type,
            trace=trace.summary(),
            code_generated=result.code_generated,
        )

        return trace
