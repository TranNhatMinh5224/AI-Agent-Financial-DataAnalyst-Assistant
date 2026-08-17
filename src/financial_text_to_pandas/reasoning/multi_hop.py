"""
multi_hop.py — Multi-hop Reasoning Controller Stub.

Phase 3, Step 9.
"""

from __future__ import annotations

from financial_text_to_pandas.types import EvidencePackage, ReasoningResult

def run_multi_hop(question: str, initial_package: EvidencePackage) -> ReasoningResult:
    """Run iterative multi-hop reasoning.
    
    This is a stub for the initial implementation that falls back
    to a simple failure or simulated result to avoid complex 
    multi-agent setups initially.
    """
    return ReasoningResult(
        strategy="multi_hop",
        code_generated=None,
        sandbox_result=None,
        numeric_result=None,
        trace="Multi-hop controller is a stub for future complex reasoning.",
        error_type="U_UNVERIFIED"
    )
