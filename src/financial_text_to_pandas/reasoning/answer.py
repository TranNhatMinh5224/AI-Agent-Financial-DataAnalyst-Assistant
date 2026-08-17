"""
answer.py — Final answer formatting and CLI orchestrator.

Phase 3, Step 11.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from financial_text_to_pandas.config import RunConfig, load_config
from financial_text_to_pandas.types import (
    ReasoningResult, 
    VerificationResult, 
    FinalAnswer, 
    Citation,
    EvidencePackage,
    EvidenceTable,
    Candidate
)
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.cell_grounding import ground_cells
from financial_text_to_pandas.reasoning.strategy import choose_reasoning_strategy, run_deterministic_lookup, run_pot_strategy
from financial_text_to_pandas.reasoning.verifier import verify_answer


def format_final_answer(
    result: ReasoningResult, 
    verification: VerificationResult,
    package: EvidencePackage
) -> FinalAnswer:
    """Format the final answer to return to the user."""
    
    citations = []
    for cell in verification.checked_cells:
        citations.append(
            Citation(
                table_id=cell.table_id,
                csv_path=cell.csv_path,
                page_number=cell.page_number,
                row_label=cell.row_label,
                column_label=cell.column_label
            )
        )
        
    return FinalAnswer(
        answer=verification.final_answer,
        answer_type="numeric",
        unit=package.intent.unit_requested,
        citations=citations,
        verification_status=verification.verification_status,
        error_type=verification.error_type,
        trace=result.trace if result else "",
        code_generated=result.code_generated if result else None
    )


def run_reasoning_pipeline(
    question: str, 
    tables: List[EvidenceTable], 
    base_dir: Path,
    llm_config: dict[str, str | float] = None,
    strategy_override: str = "auto"
) -> FinalAnswer:
    """Run the complete Text-to-Pandas QA pipeline."""
    if llm_config is None:
        llm_config = {}
    
    # 1. Intent Extraction
    intent = extract_intent(question)
    
    package = EvidencePackage(
        query_id="dummy_id",
        question=question,
        intent=intent,
        tables=tables,
        linked_text_context=[]
    )
    
    # 2. Evidence Loader
    try:
        dfs = load_evidence_tables(package, base_dir)
    except Exception as e:
        print(f"DEBUG Error loading evidence: {e}")
        return FinalAnswer(0.0, "numeric", None, [], "invalid", "T_TECHNICAL_ERROR", "Error loading evidence", None)
        
    # 3. Cell Grounding
    grounding = ground_cells(intent, dfs)
    if grounding.error_type:
        return FinalAnswer(0.0, "numeric", None, [], "invalid", grounding.error_type, f"Grounding failed: {grounding.error_type}", None)
        
    # 4. Strategy Selection
    if strategy_override == "auto":
        strategy = choose_reasoning_strategy(intent, grounding)
    else:
        strategy = strategy_override
        
    # 5. Execution
    if strategy == "deterministic":
        result = run_deterministic_lookup(intent, grounding)
    elif strategy == "pot":
        result = run_pot_strategy(package, grounding, dfs, llm_config)
    else:
        # fallback
        result = ReasoningResult(strategy, None, None, None, "Strategy not supported yet.", "T_TECHNICAL_ERROR")
        
    # 6. Verification
    verification = verify_answer(result, grounding, package, dfs)
    
    # 7. Formatting
    final_answer = format_final_answer(result, verification, package)
    
    return final_answer


def main():
    parser = argparse.ArgumentParser(description="Phase 3: Text-to-Pandas QA CLI")
    parser.add_argument("--config", type=Path, default=Path("config/run_profile.yaml"))
    parser.add_argument("--query", type=str, required=True, help="Question to answer")
    parser.add_argument("--oracle-evidence", action="store_true", help="Provide exact csv paths directly")
    parser.add_argument("--csv", type=str, action="append", help="Relative paths to evidence CSVs if using oracle")
    parser.add_argument("--strategy", type=str, choices=["auto", "deterministic", "pot", "cot", "multi_hop"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    cfg = load_config(args.config)
    
    output_root = cfg.output_root
    if not output_root.is_absolute():
        output_root = Path.cwd() / output_root
        
    tables = []
    if args.oracle_evidence and args.csv:
        for csv_path in args.csv:
            tid = Path(csv_path).stem
            cand = Candidate("q1", args.query, tid, 1, 1.0, 1.0, 1.0, "oracle", csv_path, "pass", "oracle", "1", "now")
            tables.append(EvidenceTable(cand))
            
    print(f"Question: {args.query}")
    print(f"Strategy: {args.strategy}")
    print(f"Evidence: {[t.candidate.table_id for t in tables]}")
    print("-" * 50)
    
    if not args.dry_run:
        answer = run_reasoning_pipeline(args.query, tables, output_root, cfg.llm_config, args.strategy)
        print(f"\nDEBUG Grounding/Verification info: checked_cells={len(answer.citations)}")
        print("\nFinal Answer:")
        import json
        import dataclasses
        print(json.dumps(dataclasses.asdict(answer), indent=2, ensure_ascii=False))
        
if __name__ == "__main__":
    main()
