"""
config package — Centralized Configuration and Environment Management.
"""

from financial_text_to_pandas.config.settings import Settings, get_settings
from financial_text_to_pandas.config.profile import RunConfig, load_config

# Global singleton instance for quick access
settings = get_settings()

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "RunConfig",
    "load_config",
]
