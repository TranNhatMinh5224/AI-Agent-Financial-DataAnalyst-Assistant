"""
sandbox.py — Safely execute Pandas code with AST restrictions.

Phase 3, Step 8.
"""

from __future__ import annotations

import ast
from typing import Dict, Any

import pandas as pd

from financial_text_to_pandas.reasoning.tools import parse_vn_number, normalize_unit, safe_get_cell


class SecurityViolation(Exception):
    pass


class SecureASTVisitor(ast.NodeVisitor):
    """AST Visitor to enforce security rules on generated code."""
    
    def visit_Import(self, node):
        raise SecurityViolation("Imports are not allowed in the sandbox.")
        
    def visit_ImportFrom(self, node):
        raise SecurityViolation("Imports are not allowed in the sandbox.")
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            forbidden = {"open", "exec", "eval", "compile", "__import__"}
            if func_name in forbidden:
                raise SecurityViolation(f"Function '{func_name}' is not allowed.")
        self.generic_visit(node)
        
    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            raise SecurityViolation(f"Dunder access '{node.attr}' is not allowed.")
        self.generic_visit(node)


def run_pandas_sandbox(
    code: str, 
    dfs: Dict[str, pd.DataFrame],
    symbol_map: Optional[Dict[str, float]] = None
) -> Any:
    """Run PoT code in a secure sandbox.
    
    Args:
        code: Python source code.
        dfs: Dictionary of dataframes.
        symbol_map: Optional mapping of symbol names (e.g. NUM_0) to float values for Symbolic Masking.
        
    Returns:
        The value assigned to 'result' in the code.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in generated code: {e}")
        
    visitor = SecureASTVisitor()
    visitor.visit(tree)
    
    # Safe globals
    sandbox_globals = {
        "__builtins__": {
            "abs": abs,
            "max": max,
            "min": min,
            "sum": sum,
            "round": round,
            "len": len,
            "float": float,
            "int": int,
            "str": str,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "print": print,
        },
        "pd": pd,
        "dfs": dfs,
        "parse_vn_number": parse_vn_number,
        "normalize_unit": normalize_unit,
        "safe_get_cell": safe_get_cell,
    }
    
    if symbol_map:
        sandbox_globals.update(symbol_map)
    
    sandbox_locals: Dict[str, Any] = {}
    
    # Compile and execute
    compiled = compile(tree, filename="<sandbox>", mode="exec")
    exec(compiled, sandbox_globals, sandbox_locals)
    
    if "result" not in sandbox_locals:
        raise ValueError("Generated code did not assign a value to 'result'.")
        
    return sandbox_locals["result"]
