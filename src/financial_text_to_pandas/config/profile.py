"""
profile.py — Load and parse YAML RunConfig profiles with variable interpolation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

import yaml

from financial_text_to_pandas.config.settings import get_settings

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-(.*?))?\}")


def _resolve_env_vars(data: Any) -> Any:
    """Recursively resolve ${VAR_NAME} or ${VAR_NAME:-default} in loaded YAML structures."""
    settings = get_settings()
    settings_dict = {k: str(v) for k, v in settings.__dict__.items()}

    if isinstance(data, dict):
        return {k: _resolve_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_env_vars(item) for item in data]
    elif isinstance(data, str):
        def _replace_match(match: re.Match) -> str:
            var_name = match.group(1)
            default_val = match.group(2) if match.group(2) is not None else ""
            return settings_dict.get(var_name, default_val)
        return _ENV_VAR_PATTERN.sub(_replace_match, data)
    return data


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

    @property
    def is_sample(self) -> bool:
        return self.run_mode == "sample"

    @property
    def is_full(self) -> bool:
        return self.run_mode == "full"


def load_config(config_path: Path) -> RunConfig:
    """Load RunConfig from a YAML file with environment variable resolution."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    raw = _resolve_env_vars(raw or {})

    run_mode = str(raw.get("run_mode", "sample")).strip().lower()
    if run_mode not in {"sample", "full"}:
        raise ValueError(f"run_mode must be 'sample' or 'full', got: {run_mode!r}")

    full_run_confirmed = bool(raw.get("full_run_confirmed", False))
    if run_mode == "full" and not full_run_confirmed:
        raise ValueError(
            "run_mode is 'full' but full_run_confirmed is False. "
            "Set full_run_confirmed: true in config to confirm full-corpus run."
        )

    # Convert paths
    input_root = Path(raw.get("input_root", "ViFinQA/financial_statements"))
    output_root = Path(raw.get("output_root", "artifacts/preprocessing"))

    # Configs
    llm_planner_cfg = raw.get("llm_planner", {})
    llm_retriever_cfg = raw.get("llm_retriever", {})
    llm_programmer_cfg = raw.get("llm_programmer", {})
    llm_critic_cfg = raw.get("llm_critic", {})
    embedding_cfg = raw.get("embedding", {})
    reranker_cfg = raw.get("reranker", {})

    return RunConfig(
        run_mode=run_mode,
        input_root=input_root,
        output_root=output_root,
        sample_tickers=raw.get("sample_tickers", ["AAA"]),
        sample_limit_reports=raw.get("sample_limit_reports", 5),
        inference_limit_questions=raw.get("inference_limit_questions"),
        full_run_confirmed=full_run_confirmed,
        resume=bool(raw.get("resume", True)),
        llm_planner_config=llm_planner_cfg,
        llm_retriever_config=llm_retriever_cfg,
        llm_programmer_config=llm_programmer_cfg,
        llm_critic_config=llm_critic_cfg,
        embedding_config=embedding_cfg,
        reranker_config=reranker_cfg,
    )
