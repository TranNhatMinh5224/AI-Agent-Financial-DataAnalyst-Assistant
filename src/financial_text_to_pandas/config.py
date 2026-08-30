"""
config.py — Load and expose RunConfig from run_profile.yaml.

Đây là module duy nhất đọc config file. Các module khác import RunConfig từ đây,
không đọc YAML trực tiếp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

import yaml


@dataclass
class RunConfig:
    """Runtime configuration loaded from run_profile.yaml."""

    run_mode: str  # "sample" | "full"
    input_root: Path
    output_root: Path
    sample_tickers: list[str]
    sample_limit_reports: Optional[int]
    inference_limit_questions: Optional[int]
    full_run_confirmed: bool
    resume: bool
    llm_planner_config: dict[str, str | float] = field(default_factory=dict)
    llm_retriever_config: dict[str, str | float] = field(default_factory=dict)
    llm_programmer_config: dict[str, str | float] = field(default_factory=dict)
    llm_critic_config: dict[str, str | float] = field(default_factory=dict)
    embedding_config: dict[str, Any] = field(default_factory=dict)
    reranker_config: dict[str, Any] = field(default_factory=dict)
    # ── derived ───────────────────────────────────────────────────────────────
    @property
    def is_sample(self) -> bool:
        return self.run_mode == "sample"

    @property
    def is_full(self) -> bool:
        return self.run_mode == "full"


def load_config(config_path: Path) -> RunConfig:
    """Load RunConfig from a YAML file.

    Raises:
        FileNotFoundError: config file does not exist.
        ValueError: run_mode is not 'sample' or 'full'.
        ValueError: run_mode is 'full' but full_run_confirmed is False.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    run_mode = str(raw.get("run_mode", "sample")).strip().lower()
    if run_mode not in {"sample", "full"}:
        raise ValueError(f"run_mode must be 'sample' or 'full', got: {run_mode!r}")

    full_run_confirmed = bool(raw.get("full_run_confirmed", False))
    if run_mode == "full" and not full_run_confirmed:
        raise ValueError(
            "run_mode is 'full' but full_run_confirmed is False. "
            "Set full_run_confirmed: true in config to confirm full-corpus run."
        )

    sample_limit_reports = raw.get("sample_limit_reports")
    if sample_limit_reports is not None:
        sample_limit_reports = int(sample_limit_reports)

    inference_limit_questions = raw.get("inference_limit_questions")
    if inference_limit_questions is not None:
        inference_limit_questions = int(inference_limit_questions)

    return RunConfig(
        run_mode=run_mode,
        input_root=Path(raw.get("input_root", "ViFinQA/financial_statements")),
        output_root=Path(raw.get("output_root", "artifacts/preprocessing")),
        sample_tickers=list(raw.get("sample_tickers", [])),
        sample_limit_reports=sample_limit_reports,
        inference_limit_questions=inference_limit_questions,
        full_run_confirmed=full_run_confirmed,
        resume=bool(raw.get("resume", True)),
        llm_planner_config=raw.get("llm_planner", {}),
        llm_retriever_config=raw.get("llm_retriever", {}),
        llm_programmer_config=raw.get("llm_programmer", {}),
        llm_critic_config=raw.get("llm_critic", {}),
        embedding_config=raw.get("embedding", {}),
        reranker_config=raw.get("reranker", {}),
    )
