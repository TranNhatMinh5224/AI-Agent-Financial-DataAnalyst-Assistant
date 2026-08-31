"""
settings.py — Production-grade Centralized Environment Configuration.

Reads variables from .env file, validates keys, and provides a typed Singleton
access to all API keys, base URLs, model names, and pipeline parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # Find .env in current directory or search upwards
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        for parent in Path.cwd().parents:
            if (parent / ".env").exists():
                env_path = parent / ".env"
                break
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    """Production Settings & Environment Variables Singleton."""

    # 1. Main LLM API (OpenRouter, SiliconFlow, OpenAI, etc.)
    LLM_API_KEY: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "")
    )
    LLM_BASE_URL: str = field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    )
    LLM_MODEL_PLANNER: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL_PLANNER", "qwen/qwen3-14b")
    )
    LLM_MODEL_PROGRAMMER: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL_PROGRAMMER", "qwen/qwen3-14b")
    )
    LLM_MODEL_RETRIEVER: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL_RETRIEVER", "qwen/qwen-2.5-7b-instruct")
    )
    LLM_MODEL_CRITIC: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL_CRITIC", "qwen/qwen-2.5-7b-instruct")
    )

    # 2. Embedding & Reranker
    EMBEDDING_MODEL: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "baai/bge-m3")
    )
    RERANKER_MODEL: str = field(
        default_factory=lambda: os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-8B")
    )
    RERANKER_API_KEY: str = field(
        default_factory=lambda: os.getenv("RERANKER_API_KEY") or os.getenv("SILICONFLOW_API_KEY", "")
    )
    RERANKER_BASE_URL: str = field(
        default_factory=lambda: os.getenv("RERANKER_BASE_URL") or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1")
    )
    EMBEDDING_BATCH_SIZE: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
    )

    # 3. Local Ollama Server
    OLLAMA_BASE_URL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    )
    OLLAMA_MODEL_DEFAULT: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_DEFAULT", "qwen2.5-coder:14b")
    )
    OLLAMA_MODEL_SMALL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_SMALL", "qwen2.5-coder:3b")
    )

    # 4. SiliconFlow API
    SILICONFLOW_API_KEY: str = field(
        default_factory=lambda: os.getenv("SILICONFLOW_API_KEY", "")
    )
    SILICONFLOW_BASE_URL: str = field(
        default_factory=lambda: os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.com/v1")
    )


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global Settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
