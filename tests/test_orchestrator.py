"""
tests/test_orchestrator.py — Unit tests for the Multi-Agent Orchestrator.

Tests cover:
    - OrchestratorConfig factory methods
    - AgentConfig.to_llm_config()
    - OrchestrationTrace.add_step / summary
    - FinancialQAOrchestrator.plan / critique
    - Full orchestrator.run() with mock evidence
"""

import pytest
from unittest.mock import patch, MagicMock

from financial_text_to_pandas.reasoning.orchestrator import (
    AgentConfig,
    OrchestratorConfig,
    OrchestrationTrace,
    FinancialQAOrchestrator,
    ROLE_PLANNER,
    ROLE_CRITIC,
)
from financial_text_to_pandas.types import (
    Intent,
    EvidencePackage,
    CellGroundingResult,
    GroundedCell,
    ReasoningResult,
    VerificationResult,
)


# ── Config ────────────────────────────────────────────────────────────────────

def test_agent_config_to_llm_config():
    cfg = AgentConfig(ROLE_PLANNER, "qwen2.5-coder:7b", temperature=0.1, max_tokens=512)
    llm_cfg = cfg.to_llm_config()
    assert llm_cfg["model"] == "qwen2.5-coder:7b"
    assert llm_cfg["temperature"] == 0.1
    assert llm_cfg["max_tokens"] == 512


def test_orchestrator_config_ollama_local():
    cfg = OrchestratorConfig.for_ollama_local("qwen2.5-coder:7b")
    assert cfg.planner.role == ROLE_PLANNER
    assert cfg.critic.role == ROLE_CRITIC
    assert cfg.max_reflection_rounds == 3


def test_orchestrator_config_production_gpu():
    cfg = OrchestratorConfig.for_production_gpu(
        planner_model="gpt-4o",
        programmer_model="qwen2.5-coder:14b",
        critic_model="qwen2.5-coder:3b",
        retriever_model="qwen2.5-coder:7b",
    )
    # Planner should NOT be quantized
    assert cfg.planner.quantization is None
    # Critic should be INT4 (cheapest, runs most often)
    assert cfg.critic.quantization == "int4"


# ── OrchestrationTrace ────────────────────────────────────────────────────────

def test_orchestration_trace_add_and_summary():
    trace = OrchestrationTrace(question="Test question?")
    trace.add_step(ROLE_PLANNER, "decompose", True, "Plan OK")
    trace.add_step(ROLE_CRITIC, "dual_verify", False, "Mismatch detected")

    summary = trace.summary()
    assert "PLANNER" in summary
    assert "CRITIC" in summary
    assert "✅" in summary
    assert "❌" in summary
    assert "Mismatch detected" in summary


# ── Planner ───────────────────────────────────────────────────────────────────

def test_planner_generates_plan():
    cfg = OrchestratorConfig.for_ollama_local()
    orc = FinancialQAOrchestrator(cfg)
    trace = OrchestrationTrace(question="Doanh thu tăng bao nhiêu %?")
    plan = orc.plan("Doanh thu tăng bao nhiêu %?", trace)

    assert isinstance(plan, str)
    assert len(plan) > 10
    assert any(s.agent == ROLE_PLANNER for s in trace.steps)


# ── Critique ──────────────────────────────────────────────────────────────────

def test_critic_passes_valid_result():
    cfg = OrchestratorConfig.for_ollama_local()
    orc = FinancialQAOrchestrator(cfg)
    trace = OrchestrationTrace(question="?")

    import pandas as pd
    dfs = {"T1": pd.DataFrame({"row_label_full": ["Doanh thu"], "C": [100.0]})}
    cell = GroundedCell("T1", "", 1, "Doanh thu", "C", "100", 100.0, None, 1.0, "exact", None)
    grounding = CellGroundingResult([cell], None)
    result = ReasoningResult("pot", "result = 100.0", 100.0, 100.0, "trace", None)
    intent = Intent(None, None, [2023], "unknown", ["doanh thu"], None, "lookup")
    package = EvidencePackage("q1", "?", intent, [], [])

    verification = orc.critique(result, grounding, package, dfs, trace)
    assert verification.is_valid
    assert any(s.agent == ROLE_CRITIC for s in trace.steps)


# ── Full orchestrator.run() ───────────────────────────────────────────────────

def test_orchestrator_run_insufficient_evidence():
    cfg = OrchestratorConfig.for_ollama_local()
    orc = FinancialQAOrchestrator(cfg)

    intent = Intent(None, None, [2023], "unknown", ["doanh thu"], None, "lookup")
    package = EvidencePackage("q1", "Doanh thu là bao nhiêu?", intent, [], [])

    # Empty dfs → grounding will return I_INSUFFICIENT_EVIDENCE
    trace = orc.run("Doanh thu là bao nhiêu?", package, {})
    assert trace.error is not None
    assert "Insufficient evidence" in trace.error


def test_orchestrator_config_parallel_critics():
    """Production config should enable parallel Critics."""
    cfg = OrchestratorConfig.for_production_gpu(
        planner_model="gpt-4o",
        programmer_model="qwen-coder-14b",
        critic_model="qwen-coder-3b",
        retriever_model="qwen-coder-7b",
    )
    assert cfg.parallel_critics == 3
