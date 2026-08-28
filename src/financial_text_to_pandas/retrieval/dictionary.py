"""
dictionary.py — Financial Lexicon & Language Normalizer for ViFinQA.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any

_DEFAULT_DICT_PATH = Path(__file__).resolve().parents[3] / "config" / "financial_dictionary.json"

_FINANCIAL_DICT: Dict[str, Any] = {}


def load_financial_dictionary(dict_path: Path = _DEFAULT_DICT_PATH) -> Dict[str, Any]:
    """Load the JSON financial normalization dictionary."""
    global _FINANCIAL_DICT
    if not _FINANCIAL_DICT:
        if dict_path.exists():
            with open(dict_path, "r", encoding="utf-8") as f:
                _FINANCIAL_DICT = json.load(f)
        else:
            _FINANCIAL_DICT = {
                "acronyms": {},
                "metrics_synonyms": {},
                "report_types": {},
                "units_multiplier": {}
            }
    return _FINANCIAL_DICT


def normalize_query_language(text: str) -> str:
    """Normalize acronyms and synonyms in natural language queries.
    
    Example:
        "LNST của CTCP FPT năm 2023 là bao nhiêu tỷ?" 
        -> "lợi nhuận sau thuế của công ty cổ phần FPT năm 2023 là bao nhiêu tỷ?"
    """
    if not text:
        return ""
        
    lexicon = load_financial_dictionary()
    normalized = text
    
    # 1. Expand Acronyms (case insensitive with word boundaries)
    acronyms = lexicon.get("acronyms", {})
    for acr, full in acronyms.items():
        pattern = re.compile(r"\b" + re.escape(acr) + r"\b", re.IGNORECASE)
        normalized = pattern.sub(full, normalized)
        
    # 2. Standardize Metric Synonyms
    synonyms = lexicon.get("metrics_synonyms", {})
    normalized_lower = normalized.lower()
    for syn, std in synonyms.items():
        if syn in normalized_lower:
            # Replace whole phrase
            pattern = re.compile(re.escape(syn), re.IGNORECASE)
            normalized = pattern.sub(std, normalized)
            
    return normalized
