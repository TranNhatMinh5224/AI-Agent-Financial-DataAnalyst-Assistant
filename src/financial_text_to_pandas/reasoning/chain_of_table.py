"""
chain_of_table.py — Chain-of-Table iterative table transformation engine.

Reference: Wang et al., Google DeepMind — ICLR 2024
           "Chain-of-Table: Evolving Tables in the Reasoning Chain for Table Understanding"

Mechanism:
    Instead of feeding the raw table to the LLM once, the table "evolves"
    step by step through a pool of deterministic Pandas operations chosen by
    the LLM. Each iteration produces a smaller, more focused intermediate table
    until only the data needed to answer the question remains.

    Iterative 3-step loop:
        Step 1 — Sample next operation: LLM picks from the Operation Pool.
        Step 2 — Generate arguments:   LLM provides parameters for the op.
        Step 3 — Transform table:      Execute op deterministically in Pandas.
    Repeat until the LLM emits f_final_answer().

Operation Pool (deterministic Pandas wrappers):
    f_select_row    — filter rows by a condition string
    f_select_col    — keep only specified columns
    f_add_col       — add a computed column via eval expression
    f_group_by      — group + aggregate (sum/mean/count/max/min)
    f_sort_by       — sort by column ascending/descending
    f_final_answer  — signal end of chain; LLM reads the resulting table
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Operation result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OperationResult:
    """Result of executing one chain-of-table operation."""
    operation: str
    arguments: Dict[str, Any]
    table_before_shape: Tuple[int, int]
    table_after_shape: Tuple[int, int]
    success: bool
    error: Optional[str] = None


@dataclass
class ChainOfTableTrace:
    """Full audit trace of a Chain-of-Table execution."""
    question: str
    steps: List[OperationResult] = field(default_factory=list)
    final_table: Optional[pd.DataFrame] = None
    finished: bool = False
    error: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Operation Pool — deterministic Pandas transformations
# ─────────────────────────────────────────────────────────────────────────────

OPERATION_POOL = ["f_select_row", "f_select_col", "f_add_col", "f_group_by", "f_sort_by", "f_final_answer"]


def f_select_row(df: pd.DataFrame, condition: str) -> pd.DataFrame:
    """Filter rows matching a boolean condition string.

    Args:
        df: Current intermediate table.
        condition: Pandas query string, e.g. "year == 2023" or "revenue > 1000".

    Returns:
        Filtered DataFrame.
    """
    return df.query(condition, engine="python").reset_index(drop=True)


def f_select_col(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """Keep only the specified columns.

    Args:
        df: Current intermediate table.
        columns: List of column names to retain.

    Returns:
        DataFrame with only the specified columns.
    """
    valid_cols = [c for c in columns if c in df.columns]
    return df[valid_cols].copy()


def f_add_col(df: pd.DataFrame, col_name: str, formula: str) -> pd.DataFrame:
    """Add a new computed column using a Pandas eval expression.

    Args:
        df: Current intermediate table.
        col_name: Name of the new column.
        formula: Expression to evaluate (references existing column names).
                 Example: "revenue - cost"

    Returns:
        DataFrame with the new column appended.
    """
    df = df.copy()
    df[col_name] = df.eval(formula)
    return df


def f_group_by(df: pd.DataFrame, group_col: str, agg_col: str, agg_func: str = "sum") -> pd.DataFrame:
    """Group by a column and aggregate another.

    Args:
        df: Current intermediate table.
        group_col: Column to group by.
        agg_col: Column to aggregate.
        agg_func: Aggregation function: "sum" | "mean" | "count" | "max" | "min".

    Returns:
        Aggregated DataFrame.
    """
    valid_funcs = {"sum", "mean", "count", "max", "min"}
    if agg_func not in valid_funcs:
        raise ValueError(f"agg_func must be one of {valid_funcs}, got '{agg_func}'")
    return df.groupby(group_col, as_index=False)[agg_col].agg(agg_func)


def f_sort_by(df: pd.DataFrame, col: str, ascending: bool = False) -> pd.DataFrame:
    """Sort DataFrame by a column.

    Args:
        df: Current intermediate table.
        col: Column to sort by.
        ascending: True for ascending, False for descending.

    Returns:
        Sorted DataFrame (index reset).
    """
    return df.sort_values(by=col, ascending=ascending).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

_OP_DISPATCH = {
    "f_select_row": lambda df, args: f_select_row(df, args["condition"]),
    "f_select_col": lambda df, args: f_select_col(df, args["columns"]),
    "f_add_col":    lambda df, args: f_add_col(df, args["col_name"], args["formula"]),
    "f_group_by":   lambda df, args: f_group_by(df, args["group_col"], args["agg_col"], args.get("agg_func", "sum")),
    "f_sort_by":    lambda df, args: f_sort_by(df, args["col"], args.get("ascending", False)),
}


def apply_operation(
    df: pd.DataFrame,
    operation: str,
    arguments: Dict[str, Any],
) -> Tuple[pd.DataFrame, OperationResult]:
    """Apply one Chain-of-Table operation to the current DataFrame.

    Args:
        df: Current intermediate table.
        operation: Operation name from OPERATION_POOL.
        arguments: Arguments dict for the operation.

    Returns:
        Tuple of (transformed_df, OperationResult).
    """
    before_shape = df.shape

    if operation == "f_final_answer":
        result = OperationResult(
            operation=operation,
            arguments=arguments,
            table_before_shape=before_shape,
            table_after_shape=before_shape,
            success=True,
        )
        return df, result

    if operation not in _OP_DISPATCH:
        err = f"Unknown operation '{operation}'. Valid: {OPERATION_POOL}"
        return df, OperationResult(
            operation=operation,
            arguments=arguments,
            table_before_shape=before_shape,
            table_after_shape=before_shape,
            success=False,
            error=err,
        )

    try:
        new_df = _OP_DISPATCH[operation](df, arguments)
        return new_df, OperationResult(
            operation=operation,
            arguments=arguments,
            table_before_shape=before_shape,
            table_after_shape=new_df.shape,
            success=True,
        )
    except Exception as e:
        return df, OperationResult(
            operation=operation,
            arguments=arguments,
            table_before_shape=before_shape,
            table_after_shape=before_shape,
            success=False,
            error=str(e),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Chain-of-Table executor (offline / test mode — LLM plan injected externally)
# ─────────────────────────────────────────────────────────────────────────────

def execute_chain(
    df: pd.DataFrame,
    question: str,
    plan: List[Dict[str, Any]],
    max_steps: int = 10,
) -> ChainOfTableTrace:
    """Execute a pre-planned Chain-of-Table operation sequence on a DataFrame.

    In production, `plan` is generated by the LLM. In tests / offline mode,
    it is supplied directly to validate the operation engine.

    Args:
        df: Initial table (may be a slice from TableRAG-level retrieval).
        question: Original user question (for audit trace).
        plan: List of {"operation": str, "arguments": dict} steps.
        max_steps: Safety cap to prevent infinite loops.

    Returns:
        ChainOfTableTrace with all intermediate steps and the final table.
    """
    trace = ChainOfTableTrace(question=question)
    current_df = df.copy()

    for i, step in enumerate(plan[:max_steps]):
        op = step.get("operation", "")
        args = step.get("arguments", {})

        current_df, op_result = apply_operation(current_df, op, args)
        trace.steps.append(op_result)

        if op == "f_final_answer" or not op_result.success:
            trace.finished = (op == "f_final_answer")
            if not op_result.success:
                trace.error = op_result.error
            break
    else:
        trace.error = f"Chain did not reach f_final_answer within {max_steps} steps."

    trace.final_table = current_df
    return trace


def format_trace_for_display(trace: ChainOfTableTrace) -> str:
    """Render a human-readable Chain-of-Table trace for the UI evidence viewer."""
    lines = [f"[Chain-of-Table] Question: {trace.question}"]
    for i, step in enumerate(trace.steps, 1):
        status = "✅" if step.success else "❌"
        args_str = ", ".join(f"{k}={v!r}" for k, v in step.arguments.items())
        lines.append(
            f"  Iter {i}: {status} {step.operation}({args_str})  "
            f"{step.table_before_shape} → {step.table_after_shape}"
        )
        if step.error:
            lines.append(f"           Error: {step.error}")
    if trace.final_table is not None:
        lines.append(f"  Final table shape: {trace.final_table.shape}")
    return "\n".join(lines)
